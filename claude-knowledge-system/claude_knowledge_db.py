#!/usr/bin/env python3
"""
Claude Code Knowledge Database
Optimizes fragmented conversations by creating a searchable DuckDB knowledge base
"""

import json
import os
import glob
import duckdb
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import re

class ClaudeKnowledgeDB:
    def __init__(self, db_path="claude_knowledge.db", claude_dir="~/.claude"):
        self.db_path = db_path
        self.claude_dir = Path(claude_dir).expanduser()
        self.conn = duckdb.connect(self.db_path)
        self.init_schema()
    
    def init_schema(self):
        """Initialize DuckDB schema for conversation storage"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR PRIMARY KEY,
                session_id VARCHAR NOT NULL UNIQUE,
                timestamp TIMESTAMP,
                summary TEXT,
                total_messages INTEGER,
                created_at TIMESTAMP DEFAULT NOW(),
                file_path VARCHAR
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id VARCHAR PRIMARY KEY,
                session_id VARCHAR NOT NULL,
                parent_uuid VARCHAR,
                message_uuid VARCHAR NOT NULL,
                message_type VARCHAR NOT NULL, -- 'user' or 'assistant'
                content TEXT,
                model VARCHAR,
                timestamp TIMESTAMP,
                token_usage JSON,
                tool_calls JSON,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER,
                session_id VARCHAR NOT NULL,
                topic VARCHAR NOT NULL,
                keywords TEXT[],
                relevance_score FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS context_memory (
                id INTEGER,
                topic VARCHAR NOT NULL,
                context_type VARCHAR, -- 'code', 'config', 'discussion', 'decision'
                summary TEXT,
                relevant_sessions VARCHAR[],
                confidence_score FLOAT DEFAULT 1.0,
                last_referenced TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create indexes for better performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_content ON messages (content)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_session ON topics (session_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_topic ON topics (topic)")
        
    def parse_jsonl_conversation(self, file_path):
        """Parse a JSONL conversation file from Claude Code"""
        conversation_data = {
            'messages': [],
            'session_id': None,
            'summary': None,
            'timestamps': []
        }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                try:
                    data = json.loads(line.strip())
                    
                    if data.get('type') == 'summary':
                        conversation_data['summary'] = data.get('summary')
                    elif data.get('type') in ['user', 'assistant']:
                        session_id = data.get('sessionId')
                        if not conversation_data['session_id']:
                            conversation_data['session_id'] = session_id
                            
                        message = {
                            'session_id': session_id,
                            'parent_uuid': data.get('parentUuid'),
                            'message_uuid': data.get('uuid'),
                            'message_type': data.get('type'),
                            'timestamp': data.get('timestamp'),
                            'content': self.extract_content(data.get('message', {})),
                            'model': data.get('message', {}).get('model'),
                            'token_usage': data.get('message', {}).get('usage'),
                            'tool_calls': self.extract_tool_calls(data.get('message', {}))
                        }
                        
                        conversation_data['messages'].append(message)
                        if message['timestamp']:
                            conversation_data['timestamps'].append(message['timestamp'])
                            
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num + 1} in {file_path}: {e}")
                except Exception as e:
                    print(f"Unexpected error on line {line_num + 1} in {file_path}: {e}")
        
        return conversation_data
    
    def extract_content(self, message):
        """Extract text content from message structure"""
        if not message:
            return ""
            
        content = message.get('content', [])
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
                elif isinstance(item, str):
                    text_parts.append(item)
            return ' '.join(text_parts)
        elif isinstance(content, str):
            return content
        
        return str(content)
    
    def extract_tool_calls(self, message):
        """Extract tool call information from message"""
        content = message.get('content', [])
        tool_calls = []
        
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'tool_use':
                    tool_calls.append({
                        'name': item.get('name'),
                        'input': item.get('input', {}),
                        'id': item.get('id')
                    })
        
        return tool_calls if tool_calls else None
    
    def extract_topics_and_keywords(self, content, summary=None):
        """Extract topics and keywords from conversation content"""
        topics = set()
        keywords = set()
        
        # Common technical keywords that indicate topics
        tech_patterns = {
            'database': r'\b(database|db|sql|duckdb|sqlite|postgresql|mysql)\b',
            'claude_code': r'\b(claude[\s-]?code|anthropic|ai|llm|model)\b',
            'programming': r'\b(python|javascript|rust|go|java|function|class|api)\b',
            'gui': r'\b(gui|interface|ui|frontend|claudia|desktop)\b',
            'configuration': r'\b(config|settings|environment|setup|install)\b',
            'git': r'\b(git|commit|push|pull|branch|repository|github)\b'
        }
        
        text = f"{content or ''} {summary or ''}".lower()
        
        for topic, pattern in tech_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                topics.add(topic)
                # Extract specific keywords matching the pattern
                matches = re.findall(pattern, text, re.IGNORECASE)
                keywords.update(matches)
        
        # Extract quoted strings and code blocks as potential keywords
        quoted_strings = re.findall(r'"([^"]+)"', text)
        code_blocks = re.findall(r'`([^`]+)`', text)
        keywords.update(quoted_strings[:5])  # Limit to first 5
        keywords.update(code_blocks[:5])
        
        return list(topics), list(keywords)
    
    def ingest_conversation(self, file_path):
        """Ingest a single conversation file into the database"""
        conv_data = self.parse_jsonl_conversation(file_path)
        
        if not conv_data['session_id'] or not conv_data['messages']:
            print(f"Skipping {file_path}: No session ID or messages found")
            return False
        
        session_id = conv_data['session_id']
        
        # Check if already ingested
        existing = self.conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE session_id = ?", 
            [session_id]
        ).fetchone()
        
        if existing[0] > 0:
            print(f"Session {session_id} already ingested, skipping")
            return False
        
        # Insert conversation record
        min_timestamp = min(conv_data['timestamps']) if conv_data['timestamps'] else None
        self.conn.execute("""
            INSERT INTO conversations (id, session_id, timestamp, summary, total_messages, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            session_id,
            session_id, 
            min_timestamp,
            conv_data['summary'],
            len(conv_data['messages']),
            str(file_path)
        ])
        
        # Insert messages
        for msg in conv_data['messages']:
            msg_id = f"{session_id}_{msg['message_uuid']}"
            self.conn.execute("""
                INSERT INTO messages (id, session_id, parent_uuid, message_uuid, message_type, 
                                    content, model, timestamp, token_usage, tool_calls)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                msg_id,
                msg['session_id'],
                msg['parent_uuid'],
                msg['message_uuid'],
                msg['message_type'],
                msg['content'],
                msg['model'],
                msg['timestamp'],
                json.dumps(msg['token_usage']) if msg['token_usage'] else None,
                json.dumps(msg['tool_calls']) if msg['tool_calls'] else None
            ])
        
        # Extract and insert topics
        all_content = ' '.join([msg['content'] for msg in conv_data['messages'] if msg['content']])
        topics, keywords = self.extract_topics_and_keywords(all_content, conv_data['summary'])
        
        for topic in topics:
            self.conn.execute("""
                INSERT INTO topics (session_id, topic, keywords)
                VALUES (?, ?, ?)
            """, [session_id, topic, keywords])
        
        print(f"✅ Ingested session {session_id} with {len(conv_data['messages'])} messages")
        return True
    
    def ingest_all_conversations(self):
        """Ingest all conversation files from Claude directory"""
        projects_dir = self.claude_dir / "projects"
        if not projects_dir.exists():
            print(f"Claude projects directory not found: {projects_dir}")
            return
        
        jsonl_files = list(projects_dir.rglob("*.jsonl"))
        print(f"Found {len(jsonl_files)} conversation files")
        
        ingested_count = 0
        for file_path in jsonl_files:
            try:
                if self.ingest_conversation(file_path):
                    ingested_count += 1
            except Exception as e:
                print(f"Error ingesting {file_path}: {e}")
        
        print(f"\n🎉 Successfully ingested {ingested_count} conversations")
        self.build_context_memory()
    
    def build_context_memory(self):
        """Build context memory from ingested conversations"""
        # Group related conversations by topics
        topic_sessions = self.conn.execute("""
            SELECT topic, array_agg(session_id) as sessions, 
                   count(*) as frequency
            FROM topics 
            GROUP BY topic
            HAVING count(*) >= 2  -- Only topics with multiple sessions
        """).fetchall()
        
        for topic, sessions, frequency in topic_sessions:
            # Get representative content for this topic
            sample_content = self.conn.execute("""
                SELECT content FROM messages 
                WHERE session_id = ANY(?) AND content LIKE '%' || ? || '%'
                ORDER BY LENGTH(content) DESC
                LIMIT 3
            """, [sessions, topic]).fetchall()
            
            context_summary = f"Topic '{topic}' discussed across {frequency} sessions. " + \
                            "Key points: " + ". ".join([c[0][:200] + "..." for c in sample_content[:2]])
            
            # Check if topic already exists in context memory
            existing = self.conn.execute(
                "SELECT id FROM context_memory WHERE topic = ?", [topic]
            ).fetchone()
            
            if existing:
                # Update existing context memory
                self.conn.execute("""
                    UPDATE context_memory 
                    SET summary = ?, relevant_sessions = ?, confidence_score = ?, last_referenced = NOW()
                    WHERE topic = ?
                """, [
                    context_summary,
                    sessions,
                    min(1.0, frequency / 5.0),
                    topic
                ])
            else:
                # Insert new context memory
                self.conn.execute("""
                    INSERT INTO context_memory (topic, context_type, summary, relevant_sessions, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    topic, 
                    'discussion',
                    context_summary,
                    sessions,
                    min(1.0, frequency / 5.0)  # Confidence based on frequency
                ])
        
        print(f"Built context memory for {len(topic_sessions)} topics")
    
    def search_conversations(self, query, limit=10):
        """Search conversations using pattern matching"""
        results = self.conn.execute("""
            SELECT DISTINCT c.session_id, c.summary, c.timestamp, 
                   m.content, m.message_type, m.model,
                   (CASE 
                    WHEN LOWER(m.content) LIKE LOWER(?) THEN 10
                    WHEN LOWER(c.summary) LIKE LOWER(?) THEN 8
                    ELSE 5
                   END) as relevance
            FROM conversations c
            JOIN messages m ON c.session_id = m.session_id
            WHERE LOWER(m.content) LIKE LOWER(?) 
               OR LOWER(c.summary) LIKE LOWER(?)
            ORDER BY relevance DESC, c.timestamp DESC
            LIMIT ?
        """, [f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit]).fetchall()
        
        return results
    
    def get_context_for_topic(self, topic):
        """Get context memory for a specific topic"""
        context = self.conn.execute("""
            SELECT summary, relevant_sessions, confidence_score, last_referenced
            FROM context_memory 
            WHERE topic ILIKE '%' || ? || '%'
            ORDER BY confidence_score DESC, last_referenced DESC
        """, [topic]).fetchall()
        
        return context
    
    def generate_claude_md_knowledge_section(self):
        """Generate knowledge section for CLAUDE.md"""
        # Get top topics and recent conversations
        top_topics = self.conn.execute("""
            SELECT topic, count(*) as frequency
            FROM topics 
            GROUP BY topic 
            ORDER BY frequency DESC 
            LIMIT 10
        """).fetchall()
        
        recent_conversations = self.conn.execute("""
            SELECT session_id, summary, timestamp, total_messages
            FROM conversations 
            WHERE summary IS NOT NULL
            ORDER BY timestamp DESC 
            LIMIT 5
        """).fetchall()
        
        knowledge_section = f"""
# Claude Code Knowledge Base

## Database Info
- **Database**: {self.db_path}
- **Last Updated**: {datetime.now().isoformat()}
- **Total Conversations**: {self.conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]}
- **Total Messages**: {self.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]}

## Key Topics Discussed
{chr(10).join([f"- **{topic}**: {freq} conversations" for topic, freq in top_topics])}

## Recent Conversations
{chr(10).join([f"- **{summary}** ({total_messages} messages) - {timestamp}" for _, summary, timestamp, total_messages in recent_conversations if summary])}

## Usage
To search previous conversations: `python claude_knowledge_db.py search "your query"`
To get context for a topic: `python claude_knowledge_db.py context "topic"`

---
*This knowledge base allows Claude to maintain context across sessions by referencing previous conversations and decisions.*
"""
        return knowledge_section
    
    def stats(self):
        """Get database statistics"""
        stats = {}
        stats['conversations'] = self.conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        stats['messages'] = self.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        stats['topics'] = self.conn.execute("SELECT COUNT(DISTINCT topic) FROM topics").fetchone()[0]
        stats['context_memory'] = self.conn.execute("SELECT COUNT(*) FROM context_memory").fetchone()[0]
        
        return stats

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Claude Code Knowledge Database')
    parser.add_argument('action', choices=['ingest', 'search', 'context', 'stats', 'generate-md'])
    parser.add_argument('query', nargs='?', help='Search query or topic')
    parser.add_argument('--db', default='claude_knowledge.db', help='Database path')
    parser.add_argument('--claude-dir', default='~/.claude', help='Claude directory path')
    
    args = parser.parse_args()
    
    kb = ClaudeKnowledgeDB(args.db, args.claude_dir)
    
    if args.action == 'ingest':
        kb.ingest_all_conversations()
    elif args.action == 'search':
        if not args.query:
            print("Search query required")
            return
        results = kb.search_conversations(args.query)
        print(f"\n🔍 Search results for '{args.query}':")
        for result in results:
            session_id, summary, timestamp, content, msg_type, model, relevance = result
            print(f"\n📝 Session: {session_id[:8]}... ({timestamp})")
            print(f"Summary: {summary or 'No summary'}")
            print(f"Content snippet: {content[:200]}...")
            print(f"Relevance: {relevance:.2f}")
    elif args.action == 'context':
        if not args.query:
            print("Topic required")
            return
        context = kb.get_context_for_topic(args.query)
        print(f"\n🧠 Context for '{args.query}':")
        for summary, sessions, confidence, last_ref in context:
            print(f"\nSummary: {summary}")
            print(f"Sessions: {len(sessions)} conversations")
            print(f"Confidence: {confidence:.2f}")
            print(f"Last referenced: {last_ref}")
    elif args.action == 'stats':
        stats = kb.stats()
        print(f"\n📊 Database Statistics:")
        print(f"Conversations: {stats['conversations']}")
        print(f"Messages: {stats['messages']}")
        print(f"Unique Topics: {stats['topics']}")
        print(f"Context Memory Items: {stats['context_memory']}")
    elif args.action == 'generate-md':
        md_content = kb.generate_claude_md_knowledge_section()
        print(md_content)

if __name__ == "__main__":
    main()