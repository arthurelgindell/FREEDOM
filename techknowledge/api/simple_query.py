#!/usr/bin/env python3
"""
Simple TechKnowledge Query Interface
One-step: query initiation → knowledge served
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from intelligence.knowledge.unified_knowledge_service import UnifiedKnowledgeService


class TechKnowledgeQueryService:
    """Simple query interface for TechKnowledge system"""

    def __init__(self):
        self.unified_service = None
        self._initialized = False

    async def initialize(self):
        """Initialize the service once"""
        if not self._initialized:
            self.unified_service = UnifiedKnowledgeService()
            await self.unified_service.initialize_tech_db()
            self._initialized = True

    async def query(self,
                   question: str,
                   search_type: str = "technical",
                   limit: int = 5) -> Dict[str, Any]:
        """
        One-step query: question → knowledge served

        Args:
            question: Natural language question
            search_type: "technical", "conversational", "mixed"
            limit: Max results to return

        Returns:
            Formatted knowledge response
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Search unified knowledge
            results = await self.unified_service.unified_search(
                query=question,
                search_type=search_type,
                limit=limit
            )

            # Format for simple consumption
            formatted_response = {
                "query": question,
                "knowledge_found": results["total_results"] > 0,
                "total_results": results["total_results"],
                "sources": [],
                "technical_specifications": [],
                "conversational_context": [],
                "best_answer": None
            }

            # Extract technical knowledge
            if "techknowledge" in results["sources"]:
                tech_results = results["sources"]["techknowledge"]["results"]
                for result in tech_results:
                    formatted_response["technical_specifications"].append({
                        "technology": result.get("technology"),
                        "component_type": result.get("component_type"),
                        "component_name": result.get("component_name"),
                        "specification": result.get("specification"),
                        "confidence": result.get("confidence_score", 0),
                        "source": "techknowledge"
                    })
                formatted_response["sources"].append("techknowledge")

            # Extract conversational knowledge
            if "claude" in results["sources"]:
                claude_results = results["sources"]["claude"]["results"]
                for result in claude_results:
                    formatted_response["conversational_context"].append({
                        "summary": result.get("summary"),
                        "content": result.get("content", "")[:500] + "..." if len(result.get("content", "")) > 500 else result.get("content", ""),
                        "message_type": result.get("message_type"),
                        "timestamp": result.get("timestamp"),
                        "source": "claude"
                    })
                formatted_response["sources"].append("claude")

            # Determine best answer
            if formatted_response["technical_specifications"]:
                best_tech = max(formatted_response["technical_specifications"],
                               key=lambda x: x["confidence"])
                formatted_response["best_answer"] = {
                    "type": "technical",
                    "content": best_tech,
                    "confidence": best_tech["confidence"]
                }
            elif formatted_response["conversational_context"]:
                formatted_response["best_answer"] = {
                    "type": "conversational",
                    "content": formatted_response["conversational_context"][0],
                    "confidence": 0.7  # Default for conversational
                }

            return formatted_response

        except Exception as e:
            return {
                "query": question,
                "knowledge_found": False,
                "error": str(e),
                "total_results": 0,
                "sources": [],
                "technical_specifications": [],
                "conversational_context": [],
                "best_answer": None
            }

    async def quick_lookup(self, technology: str, component: str = None) -> Optional[Dict[str, Any]]:
        """
        Quick lookup for specific technology/component

        Args:
            technology: Technology name (e.g., "fastapi", "langgraph")
            component: Optional component name (e.g., "install", "config")

        Returns:
            Direct specification or None
        """
        if not self._initialized:
            await self.initialize()

        try:
            if component:
                query = f"{technology} {component}"
            else:
                query = technology

            results = await self.query(query, search_type="technical", limit=3)

            if results["technical_specifications"]:
                return results["technical_specifications"][0]

            return None

        except Exception:
            return None


# Standalone usage
async def main():
    """Example usage"""
    service = TechKnowledgeQueryService()

    # Test queries
    test_queries = [
        "How do I install LangGraph?",
        "What is FastAPI configuration?",
        "LangGraph agent examples",
        "Slack API endpoints"
    ]

    print("🔍 TechKnowledge Query Service Test")
    print("=" * 50)

    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = await service.query(query)

        if result["knowledge_found"]:
            print(f"✅ Found {result['total_results']} results from {result['sources']}")
            if result["best_answer"]:
                answer = result["best_answer"]
                print(f"🎯 Best Answer ({answer['type']}): {answer['content']}")
        else:
            print("❌ No knowledge found")
            if "error" in result:
                print(f"Error: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())