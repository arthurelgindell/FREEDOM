#!/usr/bin/env python3
"""
FREEDOM Unified Knowledge Service
Bridges Claude Knowledge System with TechKnowledge System for comprehensive knowledge access
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import asyncpg

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import both knowledge systems
from intelligence.knowledge.claude_knowledge_integration import FreedomKnowledgeService
from techknowledge.core.database import TechKnowledgeAsyncDB
from core.truth_engine.truth_engine import TruthEngine, ClaimType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - UnifiedKnowledge - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedKnowledgeService:
    """
    Unified knowledge service combining Claude conversational knowledge
    with TechKnowledge technical specifications
    """

    def __init__(self,
                 claude_db_path: str = None,
                 truth_engine: TruthEngine = None):
        """Initialize unified knowledge service"""

        self.truth_engine = truth_engine or TruthEngine()

        # Initialize Claude Knowledge Service
        self.claude_service = FreedomKnowledgeService(
            knowledge_db_path=claude_db_path,
            truth_engine=self.truth_engine
        )

        # Initialize TechKnowledge Service
        self.tech_db = TechKnowledgeAsyncDB()
        self.tech_initialized = False

        # Knowledge source priorities
        self.search_priorities = {
            "technical": ["techknowledge", "claude"],
            "conversational": ["claude", "techknowledge"],
            "mixed": ["claude", "techknowledge"]
        }

        logger.info("Unified Knowledge Service initialized")

    async def initialize_tech_db(self):
        """Initialize TechKnowledge database connection"""
        try:
            await self.tech_db.initialize()
            self.tech_initialized = True
            logger.info("TechKnowledge database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize TechKnowledge database: {e}")
            self.tech_initialized = False

    async def get_unified_stats(self) -> Dict[str, Any]:
        """Get statistics from both knowledge systems"""

        # Get Claude knowledge stats
        claude_stats = self.claude_service.get_stats()

        # Get TechKnowledge stats
        tech_stats = {"error": "Not available"}
        if self.tech_initialized:
            try:
                tech_results = await self.tech_db.execute_query("""
                    SELECT
                        (SELECT COUNT(*) FROM technologies) as technologies,
                        (SELECT COUNT(*) FROM specifications) as specifications,
                        (SELECT COUNT(DISTINCT component_type) FROM specifications) as component_types
                """)

                if tech_results:
                    tech_stats = tech_results[0]
                    tech_stats["available"] = True

            except Exception as e:
                tech_stats = {"error": str(e), "available": False}

        return {
            "claude_knowledge": claude_stats,
            "tech_knowledge": tech_stats,
            "unified_status": {
                "claude_available": claude_stats.get("available", False),
                "tech_available": tech_stats.get("available", False),
                "cross_search_enabled": (
                    claude_stats.get("available", False) and
                    tech_stats.get("available", False)
                )
            }
        }

    async def unified_search(self,
                           query: str,
                           search_type: str = "mixed",
                           limit: int = 10) -> Dict[str, Any]:
        """
        Search across both knowledge systems with intelligent routing

        Args:
            query: Search query
            search_type: "technical", "conversational", or "mixed"
            limit: Number of results per system
        """

        results = {
            "query": query,
            "search_type": search_type,
            "sources": {},
            "unified_results": [],
            "total_results": 0
        }

        # Get search order based on type
        search_order = self.search_priorities.get(search_type, ["claude", "techknowledge"])

        # Search Claude Knowledge
        if "claude" in search_order and self.claude_service.available:
            try:
                claude_results = self.claude_service.search_knowledge(query, limit)
                results["sources"]["claude"] = {
                    "count": len(claude_results),
                    "results": claude_results,
                    "source_type": "conversational"
                }

                # Add to unified results with source annotation
                for result in claude_results:
                    unified_result = {
                        **result,
                        "knowledge_source": "claude",
                        "source_type": "conversational",
                        "relevance_score": self._calculate_claude_relevance(result, query)
                    }
                    results["unified_results"].append(unified_result)

            except Exception as e:
                logger.error(f"Claude search failed: {e}")
                results["sources"]["claude"] = {"error": str(e)}

        # Search TechKnowledge
        if "techknowledge" in search_order and self.tech_initialized:
            try:
                tech_results = await self._search_tech_knowledge(query, limit)
                results["sources"]["techknowledge"] = {
                    "count": len(tech_results),
                    "results": tech_results,
                    "source_type": "technical"
                }

                # Add to unified results with source annotation
                for result in tech_results:
                    unified_result = {
                        **result,
                        "knowledge_source": "techknowledge",
                        "source_type": "technical",
                        "relevance_score": self._calculate_tech_relevance(result, query)
                    }
                    results["unified_results"].append(unified_result)

            except Exception as e:
                logger.error(f"TechKnowledge search failed: {e}")
                results["sources"]["techknowledge"] = {"error": str(e)}

        # Sort unified results by relevance and search type priority
        results["unified_results"] = self._rank_unified_results(
            results["unified_results"],
            search_type
        )

        results["total_results"] = len(results["unified_results"])

        # Record unified search in Truth Engine
        self.truth_engine.submit_claim(
            source_id="unified_knowledge_service",
            claim_text=f"Unified search performed: {query} ({search_type})",
            claim_type=ClaimType.BEHAVIORAL,
            evidence={
                "query": query,
                "search_type": search_type,
                "claude_results": results["sources"].get("claude", {}).get("count", 0),
                "tech_results": results["sources"].get("techknowledge", {}).get("count", 0),
                "total_unified": results["total_results"]
            }
        )

        return results

    async def _search_tech_knowledge(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search TechKnowledge system for technical specifications"""

        search_query = """
            SELECT DISTINCT
                t.name as technology,
                s.component_type,
                s.component_name,
                s.specification,
                s.extracted_at,
                s.confidence_score
            FROM technologies t
            JOIN specifications s ON t.id = s.technology_id
            WHERE
                t.name ILIKE $1 OR
                s.component_name ILIKE $1 OR
                s.specification::text ILIKE $1 OR
                s.component_type ILIKE $1
            ORDER BY s.confidence_score DESC, s.extracted_at DESC
            LIMIT $2
        """

        search_term = f"%{query}%"
        results = await self.tech_db.execute_query(search_query, (search_term, limit))

        return results

    def _calculate_claude_relevance(self, result: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for Claude knowledge results"""
        score = 0.5  # Base score

        query_lower = query.lower()
        content_lower = result.get("content", "").lower()
        summary_lower = result.get("summary", "").lower()

        # Exact matches in content
        if query_lower in content_lower:
            score += 0.3

        # Matches in summary
        if query_lower in summary_lower:
            score += 0.2

        # Recent conversations get slight boost
        if result.get("message_type") == "assistant":
            score += 0.1

        return min(score, 1.0)

    def _calculate_tech_relevance(self, result: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for TechKnowledge results"""
        score = 0.5  # Base score

        query_lower = query.lower()

        # Technology name match
        if query_lower in result.get("technology", "").lower():
            score += 0.4

        # Component name match
        if query_lower in result.get("component_name", "").lower():
            score += 0.3

        # Specification content match
        if query_lower in result.get("specification", "").lower():
            score += 0.2

        # Use existing confidence score
        confidence = result.get("confidence_score", 0.5)
        score = (score + confidence) / 2

        return min(score, 1.0)

    def _rank_unified_results(self,
                            results: List[Dict[str, Any]],
                            search_type: str) -> List[Dict[str, Any]]:
        """Rank unified results based on search type and relevance"""

        def sort_key(item):
            base_score = item.get("relevance_score", 0.5)

            # Apply search type weighting
            if search_type == "technical" and item["source_type"] == "technical":
                base_score += 0.2
            elif search_type == "conversational" and item["source_type"] == "conversational":
                base_score += 0.2

            return base_score

        return sorted(results, key=sort_key, reverse=True)

    async def get_technology_context(self, technology: str) -> Dict[str, Any]:
        """Get comprehensive context for a specific technology from both systems"""

        context = {
            "technology": technology,
            "claude_context": {},
            "tech_specifications": {},
            "unified_insights": []
        }

        # Get Claude conversational context
        if self.claude_service.available:
            claude_context = self.claude_service.get_context_for_topic(technology)
            context["claude_context"] = claude_context

        # Get TechKnowledge specifications
        if self.tech_initialized:
            try:
                tech_query = """
                    SELECT
                        s.component_type,
                        s.component_name,
                        s.specification,
                        s.confidence_score,
                        s.extracted_at
                    FROM technologies t
                    JOIN specifications s ON t.id = s.technology_id
                    WHERE t.name ILIKE $1
                    ORDER BY s.confidence_score DESC, s.component_type
                """

                tech_specs = await self.tech_db.execute_query(
                    tech_query,
                    (f"%{technology}%",)
                )

                # Group by component type
                grouped_specs = {}
                for spec in tech_specs:
                    comp_type = spec["component_type"]
                    if comp_type not in grouped_specs:
                        grouped_specs[comp_type] = []
                    grouped_specs[comp_type].append(spec)

                context["tech_specifications"] = grouped_specs

            except Exception as e:
                logger.error(f"Failed to get tech specifications: {e}")
                context["tech_specifications"] = {"error": str(e)}

        # Generate unified insights
        context["unified_insights"] = self._generate_unified_insights(
            context["claude_context"],
            context["tech_specifications"],
            technology
        )

        return context

    def _generate_unified_insights(self,
                                 claude_context: Dict[str, Any],
                                 tech_specs: Dict[str, Any],
                                 technology: str) -> List[str]:
        """Generate insights by combining both knowledge sources"""

        insights = []

        # Check for conversational patterns about the technology
        claude_topics = claude_context.get("related_topics", [])
        if claude_topics:
            insights.append(f"Frequently discussed in {len(claude_topics)} conversation contexts")

        # Check for technical specification coverage
        if isinstance(tech_specs, dict) and not tech_specs.get("error"):
            spec_count = sum(len(specs) for specs in tech_specs.values())
            component_types = len(tech_specs.keys())
            insights.append(f"Technical documentation: {spec_count} specifications across {component_types} component types")

        # Cross-reference insights
        claude_memory = claude_context.get("context_memory", [])
        for memory in claude_memory:
            if memory.get("context_type") == "code" and tech_specs:
                insights.append("Both conversational experience and technical specs available")
                break

        return insights

    async def record_unified_interaction(self, interaction_data: Dict[str, Any]):
        """Record an interaction in both knowledge systems"""

        # Record in Claude knowledge
        claude_success = self.claude_service.record_freedom_interaction(interaction_data)

        # Record relevant technical aspects in TechKnowledge if applicable
        tech_success = True
        if self.tech_initialized and "technology" in interaction_data:
            try:
                # This would require extending TechKnowledge to accept interaction logs
                # For now, we'll just log the attempt
                logger.info(f"Technology interaction logged: {interaction_data.get('technology')}")
            except Exception as e:
                logger.error(f"Failed to record tech interaction: {e}")
                tech_success = False

        return {
            "claude_recorded": claude_success,
            "tech_recorded": tech_success,
            "unified_success": claude_success and tech_success
        }


# Standalone testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FREEDOM Unified Knowledge Service")
    parser.add_argument("--stats", action="store_true", help="Show unified stats")
    parser.add_argument("--search", type=str, help="Search both systems")
    parser.add_argument("--search-type", type=str, default="mixed",
                       choices=["technical", "conversational", "mixed"],
                       help="Search type preference")
    parser.add_argument("--tech-context", type=str, help="Get technology context")

    args = parser.parse_args()

    async def main():
        # Initialize service
        unified_service = UnifiedKnowledgeService()
        await unified_service.initialize_tech_db()

        if args.stats:
            stats = await unified_service.get_unified_stats()
            print(json.dumps(stats, indent=2, default=str))

        elif args.search:
            results = await unified_service.unified_search(
                args.search,
                args.search_type
            )
            print(f"🔍 Unified search results for '{args.search}' ({args.search_type}):")
            print(f"Total results: {results['total_results']}")

            for i, result in enumerate(results["unified_results"][:5], 1):
                source = result["knowledge_source"]
                score = result["relevance_score"]
                print(f"{i}. [{source}] (score: {score:.2f})")
                if source == "claude":
                    print(f"   {result.get('summary', 'No summary')}")
                else:
                    print(f"   {result.get('technology')} - {result.get('component_name')}")

        elif args.tech_context:
            context = await unified_service.get_technology_context(args.tech_context)
            print(json.dumps(context, indent=2, default=str))

    # Run async main
    asyncio.run(main())