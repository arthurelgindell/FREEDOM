#!/usr/bin/env python3
"""
FREEDOM UI Server - FastAPI backend for Flutter UI
Provides parallel interface to Slack integration
"""

import os
import asyncio
import json
import logging
import importlib.util
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
import aiohttp
import redis.asyncio as redis
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Pydantic models
class MessageRequest(BaseModel):
    content: str
    model: str = "claude"  # claude, gpt4, gemini, qwen
    session_id: Optional[str] = None

class MessageResponse(BaseModel):
    id: str
    content: str
    model: str
    timestamp: str
    session_id: str

class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    message_count: int

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

# Dynamic AI handler loading
def load_ai_handlers():
    """Dynamically load AI handlers from control_tower"""
    control_tower_path = Path(__file__).parent.parent / "control_tower"
    spec = importlib.util.spec_from_file_location("ai_handlers", control_tower_path / "ai_handlers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load AI handlers module
try:
    ai_handlers_module = load_ai_handlers()
    ClaudeHandler = ai_handlers_module.ClaudeHandler
    GPT4Handler = ai_handlers_module.GPT4Handler
    GeminiHandler = ai_handlers_module.GeminiHandler
    QwenHandler = ai_handlers_module.QwenHandler
except Exception as e:
    logger.error(f"Failed to load AI handlers: {e}")
    raise

# Global instances
_redis_client: Optional[redis.Redis] = None
_aiohttp_session: Optional[aiohttp.ClientSession] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    global _redis_client, _aiohttp_session
    
    # Startup
    try:
        # Initialize Redis
        _redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True
        )
        await _redis_client.ping()
        logger.info("Redis connection established")
        
        # Initialize aiohttp session
        _aiohttp_session = aiohttp.ClientSession()
        logger.info("aiohttp session created")
        
        # Start WebSocket cleanup task
        asyncio.create_task(manager.cleanup_dead_connections())
        logger.info("WebSocket cleanup task started")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        # Clean up AI handlers
        if _ai_handlers:
            for handler in _ai_handlers.values():
                if hasattr(handler, 'cleanup'):
                    await handler.cleanup()
        
        if _redis_client:
            await _redis_client.close()
        if _aiohttp_session:
            await _aiohttp_session.close()
        logger.info("Cleanup completed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")

# FastAPI app with lifespan management
app = FastAPI(
    title="FREEDOM UI API",
    description="API for FREEDOM Flutter UI - Parallel to Slack integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware with secure configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Authentication functions
def create_access_token(data: dict):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token"""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    return token_data

# Optional auth dependency - use verify_token for protected endpoints
async def optional_verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Optional token verification for public endpoints"""
    if credentials:
        return await verify_token(credentials)
    return None

# AI Handlers with lazy initialization
_ai_handlers = None

def get_ai_handlers():
    """Get or create AI handlers"""
    global _ai_handlers
    if _ai_handlers is None:
        _ai_handlers = {
            "claude": ClaudeHandler(),
            "gpt4": GPT4Handler(),
            "gemini": GeminiHandler(),
            "qwen": QwenHandler()
        }
    return _ai_handlers

# Session Manager using Redis
class SessionManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.session_ttl = 3600  # 1 hour
    
    async def save_session(self, session_id: str, data: dict):
        """Save session data to Redis"""
        await self.redis.setex(
            f"session:{session_id}",
            self.session_ttl,
            json.dumps(data)
        )
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data from Redis"""
        data = await self.redis.get(f"session:{session_id}")
        return json.loads(data) if data else None
    
    async def add_message(self, session_id: str, message: dict):
        """Add message to session history"""
        session_data = await self.get_session(session_id) or {"messages": []}
        session_data["messages"].append(message)
        await self.save_session(session_id, session_data)

# Enhanced WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._cleanup_task = None
        self._connection_metadata: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self._connection_metadata[session_id] = {
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        logger.info(f"WebSocket connected for session {session_id}")
    
    async def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self._connection_metadata:
            del self._connection_metadata[session_id]
        logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_personal_message(self, message: str, session_id: str):
        """Send message to specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to {session_id}: {e}")
                await self.disconnect(session_id)
    
    async def broadcast(self, message: str, exclude_session: Optional[str] = None):
        """Broadcast message to all connected sessions"""
        dead_connections = []
        
        for session_id, connection in self.active_connections.items():
            if session_id == exclude_session:
                continue
                
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {session_id}: {e}")
                dead_connections.append(session_id)
        
        # Clean up dead connections
        for session_id in dead_connections:
            await self.disconnect(session_id)
    
    async def cleanup_dead_connections(self):
        """Periodic cleanup of dead connections"""
        while True:
            await asyncio.sleep(60)  # Check every minute
            dead_connections = []
            
            for session_id, connection in self.active_connections.items():
                try:
                    # Send ping message
                    await connection.send_json({"type": "ping"})
                    if session_id in self._connection_metadata:
                        self._connection_metadata[session_id]["last_ping"] = datetime.utcnow()
                except Exception:
                    dead_connections.append(session_id)
            
            # Remove dead connections
            for session_id in dead_connections:
                await self.disconnect(session_id)
            
            if dead_connections:
                logger.info(f"Cleaned up {len(dead_connections)} dead connections")

manager = ConnectionManager()

@app.get("/")
async def root():
    return {
        "message": "FREEDOM UI API Server",
        "status": "running",
        "available_models": list(ai_handlers.keys()),
        "parallel_to_slack": True
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/message", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    token_data: Optional[TokenData] = Depends(optional_verify_token)
):
    """Send a message to the specified AI model"""
    try:
        session_id = request.session_id or f"session_{datetime.now().timestamp()}"
        
        # Get the appropriate handler
        ai_handlers = get_ai_handlers()
        if request.model not in ai_handlers:
            raise HTTPException(status_code=400, detail=f"Unknown model: {request.model}")
        
        handler = ai_handlers[request.model]
        
        # Generate response
        response_content = await handler.generate_response(request.content)
        
        # Create response
        message_id = f"msg_{datetime.now().timestamp()}"
        response = MessageResponse(
            id=message_id,
            content=response_content,
            model=request.model,
            timestamp=datetime.now().isoformat(),
            session_id=session_id
        )
        
        # Store in Redis session
        if _redis_client:
            session_mgr = SessionManager(_redis_client)
            
            # Add user message
            await session_mgr.add_message(session_id, {
                "id": message_id,
                "content": request.content,
                "model": request.model,
                "timestamp": datetime.now().isoformat(),
                "is_user": True,
                "user": token_data.username if token_data else "anonymous"
            })
            
            # Add AI response
            await session_mgr.add_message(session_id, {
                "id": message_id,
                "content": response_content,
                "model": request.model,
                "timestamp": datetime.now().isoformat(),
                "is_user": False
            })
        
        logger.info(f"Message processed for {request.model} in session {session_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/sessions/{session_id}")
async def get_session(
    session_id: str,
    token_data: Optional[TokenData] = Depends(optional_verify_token)
):
    """Get session history"""
    if not _redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    session_mgr = SessionManager(_redis_client)
    session_data = await session_mgr.get_session(session_id)
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "messages": session_data.get("messages", []),
        "message_count": len(session_data.get("messages", []))
    }

@app.get("/api/sessions")
async def list_sessions(
    token_data: TokenData = Depends(verify_token)  # Protected endpoint
):
    """List all active sessions (requires authentication)"""
    if not _redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    # Get all session keys from Redis
    session_keys = await _redis_client.keys("session:*")
    sessions = []
    
    for key in session_keys:
        session_id = key.replace("session:", "")
        session_data = await _redis_client.get(key)
        
        if session_data:
            data = json.loads(session_data)
            messages = data.get("messages", [])
            sessions.append({
                "session_id": session_id,
                "message_count": len(messages),
                "last_activity": messages[-1]["timestamp"] if messages else None
            })
    
    return {"sessions": sessions}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
                continue
                
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "error": "Invalid JSON format"
                })
                continue
            
            # Process message
            try:
                request = MessageRequest(**message_data)
                
                # Generate response using the message handler
                response = await send_message(request, None)  # No auth for WebSocket yet
                
                # Send response back
                await manager.send_personal_message(
                    json.dumps(response.dict()), 
                    session_id
                )
                
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                await websocket.send_json({
                    "error": f"Processing error: {str(e)}"
                })
            
    except WebSocketDisconnect:
        await manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(session_id)

@app.post("/api/auth/token", response_model=Token)
async def login_for_access_token(username: str, password: str):
    """Generate access token (simplified for demo)"""
    # In production, verify credentials against database
    # For now, accept demo credentials
    if username != "demo" or password != "demo":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": username})
    return Token(access_token=access_token)

@app.get("/api/models")
async def get_available_models(
    token_data: Optional[TokenData] = Depends(optional_verify_token)
):
    """Get list of available AI models"""
    models = [
        {
            "id": "claude",
            "name": "Claude 3 Opus",
            "description": "Anthropic's most capable model for complex reasoning",
            "provider": "Anthropic"
        },
        {
            "id": "gpt4",
            "name": "GPT-4 Turbo",
            "description": "OpenAI's advanced model for problem-solving",
            "provider": "OpenAI"
        },
        {
            "id": "gemini",
            "name": "Gemini 1.5 Pro",
            "description": "Google's multimodal AI model",
            "provider": "Google"
        },
        {
            "id": "qwen",
            "name": "Qwen (Local)",
            "description": "Local execution specialist via LM Studio",
            "provider": "Local"
        }
    ]
    
    # Add usage stats if authenticated
    if token_data:
        for model in models:
            model["available"] = True
            model["usage_limit"] = 1000
    
    return {"models": models}

@app.get("/api/status")
async def get_system_status(
    token_data: Optional[TokenData] = Depends(optional_verify_token)
):
    """Get system status and health"""
    status_data = {
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(manager.active_connections),
        "available_models": list(get_ai_handlers().keys()),
        "parallel_interfaces": {
            "flutter_ui": True,
            "slack_integration": True
        }
    }
    
    # Add detailed info for authenticated users
    if token_data:
        status_data["redis_connected"] = _redis_client is not None
        if _redis_client:
            try:
                session_count = len(await _redis_client.keys("session:*"))
                status_data["active_sessions"] = session_count
            except:
                status_data["active_sessions"] = 0
    
    return status_data

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Start server
    uvicorn.run(
        "freedom_ui_server:app",
        host="0.0.0.0",
        port=8001,  # Different port from main API
        reload=True,
        log_level="info"
    )
