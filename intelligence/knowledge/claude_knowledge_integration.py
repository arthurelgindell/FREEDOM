#!/usr/bin/env python3
"""
FREEDOM Platform Claude Knowledge Integration
Integrates the Claude Knowledge System with FREEDOM Platform services
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Add claude-knowledge-system to path
sys.path.append(str(Path(__file__).parent.parent.parent / "claude-knowledge-system"))

try:
    from claude_knowledge_db import ClaudeKnowledgeDB
    KNOWLEDGE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_AVAILABLE = False
    ClaudeKnowledgeDB = None

from core.truth_engine.truth_engine import TruthEngine, Claim, ClaimType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - KnowledgeIntegration - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FreedomKnowledgeService:
    """FREEDOM Platform knowledge service with Claude Code integration"""

    def __init__(self,
                 knowledge_db_path: str = None,
                 truth_engine: TruthEngine = None):
        """Initialize FREEDOM knowledge service"""

        self.truth_engine = truth_engine or TruthEngine()

        # Set knowledge database path
        if knowledge_db_path:
            self.db_path = knowledge_db_path
        else:
            # Default to claude-knowledge-system directory
            self.db_path = str(Path(__file__).parent.parent.parent /
                             "claude-knowledge-system" / "claude_knowledge.db")

        # Initialize Claude Knowledge DB
        if KNOWLEDGE_AVAILABLE:
            try:
                self.knowledge_db = ClaudeKnowledgeDB(db_path=self.db_path)
                self.available = True
                logger.info(f"Claude Knowledge DB initialized: {self.db_path}")
            except Exception as e:
                logger.error(f"Failed to initialize Claude Knowledge DB: {e}")
                self.knowledge_db = None
                self.available = False
        else:
            logger.warning("Claude Knowledge DB not available - missing dependencies")
            self.knowledge_db = None
            self.available = False

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge database statistics"""
        if not self.available:
            return {"error": "Knowledge system not available"}

        try:
            # Get basic stats from knowledge DB
            conversations = self.knowledge_db.conn.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0]

            messages = self.knowledge_db.conn.execute(
                "SELECT COUNT(*) FROM messages"
            ).fetchone()[0]

            topics = self.knowledge_db.conn.execute(
                "SELECT COUNT(DISTINCT topic) FROM topics"
            ).fetchone()[0]

            context_items = self.knowledge_db.conn.execute(
                "SELECT COUNT(*) FROM context_memory"
            ).fetchone()[0]

            return {
                "conversations": conversations,
                "messages": messages,
                "topics": topics,
                "context_items": context_items,
                "database_path": self.db_path,
                "available": True
            }

        except Exception as e:
            logger.error(f"Error getting knowledge stats: {e}")
            return {"error": str(e), "available": False}

    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search knowledge base for relevant information"""
        if not self.available:
            return []

        try:
            # Search in message content
            results = self.knowledge_db.conn.execute("""
                SELECT DISTINCT
                    m.session_id,
                    c.summary,
                    m.content,
                    m.message_type,
                    m.timestamp,
                    c.timestamp as session_timestamp
                FROM messages m
                JOIN conversations c ON m.session_id = c.session_id
                WHERE m.content ILIKE '%' || ? || '%'
                ORDER BY m.timestamp DESC
                LIMIT ?
            """, [query, limit]).fetchall()

            formatted_results = []
            for row in results:
                formatted_results.append({
                    "session_id": row[0],
                    "summary": row[1],
                    "content": row[2][:500] + "..." if len(row[2]) > 500 else row[2],
                    "message_type": row[3],
                    "timestamp": row[4],
                    "session_timestamp": row[5]
                })

            # Record search as claim in Truth Engine
            self.truth_engine.submit_claim(
                source_id="freedom_knowledge_service",
                claim_text=f"Search performed for query: {query}",
                claim_type=ClaimType.BEHAVIORAL,
                evidence={
                    "query": query,
                    "results_count": len(formatted_results),
                    "search_timestamp": datetime.now().isoformat()
                }
            )

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    def get_context_for_topic(self, topic: str) -> Dict[str, Any]:
        """Get contextual information for a specific topic"""
        if not self.available:
            return {}

        try:
            # Get context memory for topic
            context_result = self.knowledge_db.conn.execute("""
                SELECT
                    topic,
                    context_type,
                    summary,
                    relevant_sessions,
                    confidence_score,
                    last_referenced
                FROM context_memory
                WHERE topic ILIKE '%' || ? || '%'
                ORDER BY confidence_score DESC, last_referenced DESC
            """, [topic]).fetchall()

            # Get related topics
            topic_result = self.knowledge_db.conn.execute("""
                SELECT DISTINCT
                    t.topic,
                    t.keywords,
                    t.relevance_score,
                    c.summary
                FROM topics t
                JOIN conversations c ON t.session_id = c.session_id
                WHERE t.topic ILIKE '%' || ? || '%'
                ORDER BY t.relevance_score DESC
                LIMIT 5
            """, [topic]).fetchall()

            return {
                "topic": topic,
                "context_memory": [
                    {
                        "topic": row[0],
                        "context_type": row[1],
                        "summary": row[2],
                        "relevant_sessions": row[3],
                        "confidence_score": row[4],
                        "last_referenced": row[5]
                    } for row in context_result
                ],
                "related_topics": [
                    {
                        "topic": row[0],
                        "keywords": row[1],
                        "relevance_score": row[2],
                        "conversation_summary": row[3]
                    } for row in topic_result
                ]
            }

        except Exception as e:
            logger.error(f"Error getting context for topic: {e}")
            return {}

    def get_recent_context(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent conversation context for session continuity"""
        if not self.available:
            return []

        try:
            # Get recent conversations
            results = self.knowledge_db.conn.execute(f"""
                SELECT
                    c.session_id,
                    c.summary,
                    c.timestamp,
                    c.total_messages,
                    array_agg(DISTINCT t.topic) as topics
                FROM conversations c
                LEFT JOIN topics t ON c.session_id = t.session_id
                WHERE c.timestamp >= current_timestamp - INTERVAL '{days} days'
                GROUP BY c.session_id, c.summary, c.timestamp, c.total_messages
                ORDER BY c.timestamp DESC
                LIMIT 10
            """).fetchall()

            return [
                {
                    "session_id": row[0],
                    "summary": row[1],
                    "timestamp": row[2],
                    "total_messages": row[3],
                    "topics": row[4] if row[4] else []
                } for row in results
            ]

        except Exception as e:
            logger.error(f"Error getting recent context: {e}")
            return []

    def record_freedom_interaction(self, interaction_data: Dict[str, Any]):
        """Record FREEDOM platform interactions in knowledge base"""
        if not self.available:
            return False

        try:
            # Create a synthetic session for FREEDOM interactions
            session_id = f"freedom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Insert as conversation
            self.knowledge_db.conn.execute("""
                INSERT INTO conversations
                (id, session_id, timestamp, summary, total_messages, file_path)
                VALUES (?, ?, NOW(), ?, 1, 'freedom_platform')
            """, [
                session_id,
                session_id,
                interaction_data.get("summary", "FREEDOM Platform Interaction")
            ])

            # Insert as message
            message_id = f"msg_{session_id}"
            self.knowledge_db.conn.execute("""
                INSERT INTO messages
                (id, session_id, message_uuid, message_type, content,
                 model, timestamp, tool_calls)
                VALUES (?, ?, ?, 'assistant', ?, 'freedom_platform', NOW(), ?)
            """, [
                message_id,
                session_id,
                message_id,
                json.dumps(interaction_data),
                json.dumps(interaction_data.get("tools_used", []))
            ])

            logger.info(f"Recorded FREEDOM interaction: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error recording FREEDOM interaction: {e}")
            return False

    def generate_session_context(self) -> str:
        """Generate context summary for new Claude Code sessions"""
        if not self.available:
            return "Knowledge system not available."

        try:
            stats = self.get_stats()
            recent_context = self.get_recent_context(days=3)

            context_summary = f"""
🧠 **FREEDOM Knowledge System Status**
- {stats.get('conversations', 0)} conversations analyzed
- {stats.get('messages', 0)} messages indexed
- {stats.get('topics', 0)} topics tracked

📚 **Recent Context** (last 3 days):
"""

            for ctx in recent_context[:3]:
                context_summary += f"- {ctx['summary'][:100]}... ({ctx['total_messages']} messages)\n"

            context_summary += f"\n🔍 Use search commands to explore accumulated knowledge."

            return context_summary.strip()

        except Exception as e:
            logger.error(f"Error generating session context: {e}")
            return "Error generating knowledge context."


# Standalone testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FREEDOM Knowledge Service")
    parser.add_argument("--stats", action="store_true", help="Show knowledge stats")
    parser.add_argument("--search", type=str, help="Search knowledge base")
    parser.add_argument("--context", type=str, help="Get context for topic")
    parser.add_argument("--recent", action="store_true", help="Show recent context")

    args = parser.parse_args()

    # Initialize service
    knowledge_service = FreedomKnowledgeService()

    if args.stats:
        stats = knowledge_service.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.search:
        results = knowledge_service.search_knowledge(args.search)
        print(f"🔍 Found {len(results)} results for '{args.search}':")
        for result in results:
            print(f"- {result['summary']}")
            print(f"  Content: {result['content']}")
            print()

    elif args.context:
        context = knowledge_service.get_context_for_topic(args.context)
        print(json.dumps(context, indent=2, default=str))

    elif args.recent:
        recent = knowledge_service.get_recent_context()
        print("📚 Recent conversations:")
        for ctx in recent:
            print(f"- {ctx['summary']} ({ctx['total_messages']} messages)")

    else:
        print(knowledge_service.generate_session_context())