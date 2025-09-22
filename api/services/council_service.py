"""
AI Council Service
Business logic layer for AI Council operations with caching and optimization
"""

import asyncio
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
import redis.asyncio as redis
from contextlib import asynccontextmanager

from core.orchestration.graphs.council import AICouncil
from api.models.requests import CouncilQueryRequest, DirectAgentRequest
from api.models.responses import (
    CouncilResponse, DirectAgentResponse, AgentResponse,
    ConversationHistory, AgentInfo, AgentStatus
)

# Import Castle for Slack integration
try:
    from control_tower.castle import Castle
    CASTLE_AVAILABLE = True
except ImportError:
    CASTLE_AVAILABLE = False
    Castle = None

logger = logging.getLogger("freedom.council_service")


class CouncilService:
    """High-performance service layer for AI Council operations"""

    def __init__(self, council: AICouncil, redis_client: redis.Redis = None, castle: Castle = None):
        self.council = council
        self.redis_client = redis_client
        self.castle = castle
        self.cache_ttl = 3600  # 1 hour default cache
        self._active_requests: Dict[str, asyncio.Task] = {}
        self._request_semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

    @asynccontextmanager
    async def _request_context(self, request_id: str):
        """Context manager for tracking active requests"""
        async with self._request_semaphore:
            try:
                yield
            finally:
                if request_id in self._active_requests:
                    del self._active_requests[request_id]

    async def process_query(self, request: CouncilQueryRequest) -> CouncilResponse:
        """Process a query through the AI Council with performance optimization"""

        start_time = time.time()
        conversation_id = request.conversation_id or str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        async with self._request_context(request_id):
            # Check cache first
            if self.redis_client:
                try:
                    cache_key = f"query:{hash(request.query)}"
                    cached_result = await self.redis_client.get(cache_key)
                    if cached_result and not request.conversation_id:  # Don't use cache for conversations
                        return CouncilResponse.parse_raw(cached_result)
                except Exception as e:
                    logger.warning(f"Cache read error: {e}")

            try:
                # Execute council query
                result = await self.council.process_request(
                    request.query,
                    conversation_id
                )

                # Transform to API response format
                agent_responses = []
                for agent_name, response_text in result.get("responses", {}).items():
                    agent_responses.append(AgentResponse(
                        agent_name=agent_name,
                        response=response_text,
                        processing_time=0.5,  # TODO: Track actual processing time
                        tokens_used=int(len(response_text.split()) * 1.3)  # Rough estimate as integer
                    ))

                council_response = CouncilResponse(
                    conversation_id=result["conversation_id"],
                    query=request.query,
                    agent_responses=agent_responses,
                    consensus=result.get("consensus", "No consensus reached"),
                    final_response=result.get("final_response", ""),
                    total_processing_time=time.time() - start_time,
                    participating_agents=len(agent_responses),
                    metadata={
                        "cache_hit": False,
                        "agent_count": result.get("agent_count", len(agent_responses))
                    }
                )

                # Cache successful results
                if self.redis_client and not request.conversation_id:
                    try:
                        await self.redis_client.setex(
                            cache_key,
                            self.cache_ttl,
                            council_response.json()
                        )
                    except Exception as e:
                        logger.warning(f"Cache write error: {e}")

                return council_response

            except Exception as e:
                # Log error and return structured error response
                logger.error(f"Council query error: {e}")
                return CouncilResponse(
                    conversation_id=conversation_id,
                    query=request.query,
                    agent_responses=[],
                    consensus="Error occurred during processing",
                    final_response=f"Sorry, I encountered an error: {str(e)}",
                    total_processing_time=time.time() - start_time,
                    participating_agents=0,
                    metadata={"error": str(e)}
                )

    async def direct_agent_query(
        self,
        agent_name: str,
        request: DirectAgentRequest
    ) -> DirectAgentResponse:
        """Query a specific agent directly"""

        start_time = time.time()

        try:
            # Get the specific agent
            agent = self.council.agents.get(agent_name)
            if not agent:
                raise ValueError(f"Agent '{agent_name}' not available")

            # Execute direct query
            response = await agent.generate_response(request.query, request.context)

            return DirectAgentResponse(
                agent_name=agent_name,
                query=request.query,
                response=response,
                processing_time=time.time() - start_time,
                tokens_used=int(len(response.split()) * 1.3),  # Rough estimate as integer
                model_info={
                    "model": agent.config.model,
                    "temperature": request.temperature or agent.config.temperature,
                    "max_tokens": agent.config.max_tokens
                }
            )

        except Exception as e:
            return DirectAgentResponse(
                agent_name=agent_name,
                query=request.query,
                response=f"Error: {str(e)}",
                processing_time=time.time() - start_time,
                model_info={"error": str(e)}
            )

    async def stream_council_response(
        self,
        request: CouncilQueryRequest
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream AI Council responses in real-time"""

        conversation_id = request.conversation_id or str(uuid.uuid4())
        request_id = str(uuid.uuid4())
        tasks = []

        async with self._request_context(request_id):
            try:
                yield {
                    "type": "session_started",
                    "data": {
                        "conversation_id": conversation_id,
                        "query": request.query,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }

                # Stream individual agent responses
                agent_results = {}
                
                # Create tasks for all agents
                for agent_name, agent in self.council.agents.items():
                    task = asyncio.create_task(
                        self._stream_agent_response(agent_name, agent, request.query, request.context)
                    )
                    tasks.append((agent_name, task))
                    self._active_requests[f"{request_id}:{agent_name}"] = task

                # Yield results as they complete
                for agent_name, task in tasks:
                    try:
                        response = await task
                        agent_results[agent_name] = response

                        yield {
                            "type": "agent_response",
                            "data": {
                                "agent_name": agent_name,
                                "response": response,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }
                    except asyncio.CancelledError:
                        logger.info(f"Agent task cancelled: {agent_name}")
                        raise
                    except Exception as e:
                        logger.error(f"Agent {agent_name} error: {e}")
                        yield {
                            "type": "agent_error",
                            "data": {
                                "agent_name": agent_name,
                                "error": str(e),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }
                    finally:
                        # Clean up task reference
                        task_key = f"{request_id}:{agent_name}"
                        if task_key in self._active_requests:
                            del self._active_requests[task_key]

                # Final consensus
                if agent_results:
                    # Simple consensus: longest response
                    best_response = max(agent_results.items(), key=lambda x: len(x[1]))
                    consensus = f"Selected {best_response[0]}'s approach"

                    yield {
                        "type": "consensus",
                        "data": {
                            "consensus": consensus,
                            "final_response": best_response[1],
                            "participating_agents": len(agent_results),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }

                yield {
                    "type": "session_completed",
                    "data": {
                        "conversation_id": conversation_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                
            except asyncio.CancelledError:
                # Cancel all active tasks for this request
                for task in tasks:
                    if not task[1].done():
                        task[1].cancel()
                raise
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield {
                    "type": "error",
                    "data": {
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }

    async def _stream_agent_response(
        self,
        agent_name: str,
        agent,
        query: str,
        context: Dict[str, Any]
    ) -> str:
        """Helper method to get individual agent response with timeout"""
        try:
            # Add timeout to prevent hanging
            response = await asyncio.wait_for(
                agent.generate_response(query, context),
                timeout=30.0  # 30 second timeout per agent
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"Agent {agent_name} timed out")
            return f"Error from {agent_name}: Request timed out"
        except Exception as e:
            logger.error(f"Agent {agent_name} error: {e}")
            return f"Error from {agent_name}: {str(e)}"

    async def get_conversation_history(
        self,
        conversation_id: str
    ) -> Optional[ConversationHistory]:
        """Retrieve conversation history"""

        try:
            conv_state = self.council.state_manager.load_state(conversation_id)
            if not conv_state:
                return None

            return ConversationHistory(
                conversation_id=conversation_id,
                messages=conv_state.messages,
                participants=list(conv_state.participants),
                created_at=conv_state.created_at,
                last_activity=conv_state.last_activity or conv_state.created_at,
                message_count=len(conv_state.messages),
                consensus_history=[conv_state.consensus] if conv_state.consensus else []
            )

        except Exception:
            return None

    async def get_agent_status(self) -> List[AgentInfo]:
        """Get status of all agents"""

        agent_infos = []
        
        # Check agents concurrently
        status_tasks = []
        for agent_name, agent in self.council.agents.items():
            task = asyncio.create_task(self._check_agent_status(agent_name, agent))
            status_tasks.append(task)
        
        # Wait for all status checks
        results = await asyncio.gather(*status_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Status check error: {result}")
            else:
                agent_infos.append(result)
        
        return agent_infos
    
    async def _check_agent_status(self, agent_name: str, agent) -> AgentInfo:
        """Check individual agent status"""
        try:
            # Test agent responsiveness
            test_response = await asyncio.wait_for(
                agent.generate_response("ping", {}),
                timeout=5.0
            )
            status = AgentStatus.ACTIVE if test_response else AgentStatus.ERROR

        except asyncio.TimeoutError:
            status = AgentStatus.ERROR
        except Exception:
            status = AgentStatus.INACTIVE

        return AgentInfo(
            name=agent_name,
            model=agent.config.model,
            status=status,
            capabilities=agent.config.capabilities,
            temperature=agent.config.temperature,
            max_tokens=agent.config.max_tokens,
            last_active=datetime.utcnow()
        )

    async def clear_cache(self, pattern: str = "*") -> int:
        """Clear Redis cache entries"""
        if not self.redis_client:
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0
    
    async def cancel_active_requests(self):
        """Cancel all active requests"""
        for request_id, task in list(self._active_requests.items()):
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled request: {request_id}")
        self._active_requests.clear()