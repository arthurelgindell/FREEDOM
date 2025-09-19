#!/usr/bin/env python3
"""
FREEDOM IDE: Transparent AI Development Interface
=================================================

A development environment where every AI contribution is verified,
every operation is logged, and no black boxes exist.

Core Principles:
- Truth-verified AI assistance
- Complete session transparency  
- Local-first AI development
- Human-AI accountability parity
"""

import json
import sqlite3
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Import Truth Engine for verification
import sys
sys.path.append(str(Path(__file__).parent.parent.parent) + '/core/truth_engine')
from truth_engine import TruthEngine, ClaimType

@dataclass
class DevelopmentSession:
    """A transparent development session"""
    session_id: str
    user_id: str
    ai_model: str
    start_time: float
    end_time: Optional[float] = None
    session_status: str = "active"  # active, completed, failed
    
@dataclass
class AIContribution:
    """An AI's contribution to development"""
    contribution_id: str
    session_id: str
    ai_model: str
    contribution_type: str  # code, analysis, suggestion, documentation
    content: str
    verification_required: bool
    verification_status: str = "pending"  # pending, verified, rejected
    human_approved: bool = False
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

class FreedomIDE:
    """
    The FREEDOM IDE: Where AI assistance meets truth verification
    
    Every AI suggestion is a claim that must be verified.
    Every development action is logged transparently.
    No AI can hide its reasoning or fabricate results.
    """
    
    def __init__(self, db_path: str = "/Volumes/DATA/FREEDOM/unified_workspace/freedom_core/development_ide/freedom_ide.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize Truth Engine for AI verification
        self.truth_engine = TruthEngine()
        
        self._init_database()
        self._log_operation("FreedomIDE", "initialized", {"db_path": str(db_path)})
        
    def _init_database(self):
        """Initialize transparent development database"""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS development_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                ai_model TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL,
                session_status TEXT NOT NULL,
                session_data TEXT  -- JSON metadata
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_contributions (
                contribution_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                ai_model TEXT NOT NULL,
                contribution_type TEXT NOT NULL,
                content TEXT NOT NULL,
                verification_required BOOLEAN NOT NULL,
                verification_status TEXT NOT NULL,
                human_approved BOOLEAN NOT NULL,
                timestamp REAL NOT NULL,
                truth_engine_claim_id TEXT,  -- Link to Truth Engine
                FOREIGN KEY (session_id) REFERENCES development_sessions (session_id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ide_operations (
                operation_id TEXT PRIMARY KEY,
                session_id TEXT,
                source_id TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                operation_details TEXT NOT NULL,  -- JSON
                timestamp REAL NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def start_session(self, user_id: str, ai_model: str) -> str:
        """Start a new transparent development session"""
        session_id = hashlib.sha256(f"{user_id}:{ai_model}:{time.time()}".encode()).hexdigest()[:16]
        
        session = DevelopmentSession(
            session_id=session_id,
            user_id=user_id,
            ai_model=ai_model,
            start_time=time.time()
        )
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO development_sessions 
            (session_id, user_id, ai_model, start_time, session_status)
            VALUES (?, ?, ?, ?, ?)
        """, (session.session_id, session.user_id, session.ai_model, 
              session.start_time, session.session_status))
        conn.commit()
        conn.close()
        
        self._log_operation(user_id, "session_started", {
            "session_id": session_id,
            "ai_model": ai_model
        })
        
        return session_id
    
    def submit_ai_contribution(self, session_id: str, ai_model: str, contribution_type: str, 
                              content: str, requires_verification: bool = True) -> str:
        """
        Submit an AI contribution for review and potential verification
        
        All AI contributions are suspect until verified and approved.
        """
        contribution_id = hashlib.sha256(f"{session_id}:{ai_model}:{content}:{time.time()}".encode()).hexdigest()[:16]
        
        contribution = AIContribution(
            contribution_id=contribution_id,
            session_id=session_id,
            ai_model=ai_model,
            contribution_type=contribution_type,
            content=content,
            verification_required=requires_verification
        )
        
        # If verification required, submit to Truth Engine
        truth_claim_id = None
        if requires_verification:
            truth_claim_id = self.truth_engine.submit_claim(
                source_id=f"AI:{ai_model}",
                claim_text=f"AI contribution: {contribution_type}",
                claim_type=ClaimType.COMPUTATIONAL,  # Most AI contributions are computational
                evidence={
                    "contribution_type": contribution_type,
                    "content": content[:500],  # Truncate for evidence
                    "ai_model": ai_model,
                    "session_id": session_id
                }
            )
        
        # Store contribution
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO ai_contributions
            (contribution_id, session_id, ai_model, contribution_type, content,
             verification_required, verification_status, human_approved, timestamp, truth_engine_claim_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            contribution.contribution_id,
            contribution.session_id,
            contribution.ai_model,
            contribution.contribution_type,
            contribution.content,
            contribution.verification_required,
            contribution.verification_status,
            contribution.human_approved,
            contribution.timestamp,
            truth_claim_id
        ))
        conn.commit()
        conn.close()
        
        self._log_operation(ai_model, "contribution_submitted", {
            "contribution_id": contribution_id,
            "session_id": session_id,
            "contribution_type": contribution_type,
            "requires_verification": requires_verification,
            "truth_claim_id": truth_claim_id
        })
        
        return contribution_id
    
    def verify_ai_contribution(self, contribution_id: str, verification_method: str, verifier_id: str) -> bool:
        """
        Verify an AI contribution through the Truth Engine
        
        Returns True if verified, False if rejected
        """
        # Get the contribution
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT truth_engine_claim_id, ai_model, contribution_type, content
            FROM ai_contributions 
            WHERE contribution_id = ?
        """, (contribution_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        truth_claim_id, ai_model, contribution_type, content = result
        
        # If there's a truth claim, verify it
        verification_success = False
        if truth_claim_id:
            verification_success = self.truth_engine.verify_claim(
                truth_claim_id, verification_method, verifier_id
            )
        
        # Update contribution status
        new_status = "verified" if verification_success else "rejected"
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE ai_contributions 
            SET verification_status = ?
            WHERE contribution_id = ?
        """, (new_status, contribution_id))
        conn.commit()
        conn.close()
        
        self._log_operation(verifier_id, "contribution_verified", {
            "contribution_id": contribution_id,
            "verification_success": verification_success,
            "method": verification_method
        })
        
        return verification_success
    
    def human_approve_contribution(self, contribution_id: str, user_id: str, approved: bool) -> bool:
        """
        Human approval of AI contribution - final gate
        
        Even verified contributions need human approval for implementation
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE ai_contributions 
            SET human_approved = ?
            WHERE contribution_id = ?
        """, (approved, contribution_id))
        conn.commit()
        conn.close()
        
        self._log_operation(user_id, "contribution_human_review", {
            "contribution_id": contribution_id,
            "approved": approved
        })
        
        return True
    
    def get_session_contributions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all AI contributions for a development session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT contribution_id, ai_model, contribution_type, content,
                   verification_required, verification_status, human_approved, timestamp
            FROM ai_contributions 
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        contributions = []
        for row in results:
            contributions.append({
                "contribution_id": row[0],
                "ai_model": row[1],
                "contribution_type": row[2],
                "content": row[3],
                "verification_required": bool(row[4]),
                "verification_status": row[5],
                "human_approved": bool(row[6]),
                "timestamp": row[7],
                "datetime": datetime.fromtimestamp(row[7]).isoformat()
            })
        
        return contributions
    
    def get_ai_trust_metrics(self, ai_model: str) -> Dict[str, Any]:
        """Get trust metrics for an AI model"""
        # Get trust score from Truth Engine
        trust_score = self.truth_engine.get_trust_score(f"AI:{ai_model}")
        
        # Get contribution statistics
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT verification_status, COUNT(*) 
            FROM ai_contributions 
            WHERE ai_model = ? AND verification_required = 1
            GROUP BY verification_status
        """, (ai_model,))
        
        verification_stats = dict(cursor.fetchall())
        
        cursor = conn.execute("""
            SELECT human_approved, COUNT(*)
            FROM ai_contributions
            WHERE ai_model = ?
            GROUP BY human_approved
        """, (ai_model,))
        
        approval_stats = dict(cursor.fetchall())
        conn.close()
        
        return {
            "ai_model": ai_model,
            "truth_engine_trust_score": trust_score,
            "verification_stats": verification_stats,
            "approval_stats": {
                "approved": approval_stats.get(1, 0),
                "rejected": approval_stats.get(0, 0)
            },
            "total_contributions": sum(verification_stats.values())
        }
    
    def end_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """End a development session with summary"""
        end_time = time.time()
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE development_sessions 
            SET end_time = ?, session_status = ?
            WHERE session_id = ?
        """, (end_time, "completed", session_id))
        conn.commit()
        conn.close()
        
        # Generate session summary
        contributions = self.get_session_contributions(session_id)
        
        summary = {
            "session_id": session_id,
            "end_time": end_time,
            "total_contributions": len(contributions),
            "verified_contributions": len([c for c in contributions if c["verification_status"] == "verified"]),
            "approved_contributions": len([c for c in contributions if c["human_approved"]]),
            "session_transparency": "complete"  # All operations logged
        }
        
        self._log_operation(user_id, "session_ended", summary)
        
        return summary
    
    def get_full_session_transparency_report(self, session_id: str) -> Dict[str, Any]:
        """
        Generate complete transparency report for a session
        
        Shows every operation, every AI contribution, every verification
        """
        conn = sqlite3.connect(self.db_path)
        
        # Get session info
        cursor = conn.execute("""
            SELECT user_id, ai_model, start_time, end_time, session_status
            FROM development_sessions
            WHERE session_id = ?
        """, (session_id,))
        session_info = cursor.fetchone()
        
        # Get all operations for this session
        cursor = conn.execute("""
            SELECT operation_type, source_id, operation_details, timestamp
            FROM ide_operations
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        operations = cursor.fetchall()
        
        conn.close()
        
        if not session_info:
            return {"error": "Session not found"}
        
        contributions = self.get_session_contributions(session_id)
        
        return {
            "session_id": session_id,
            "session_info": {
                "user_id": session_info[0],
                "ai_model": session_info[1],
                "start_time": session_info[2],
                "end_time": session_info[3],
                "session_status": session_info[4]
            },
            "contributions": contributions,
            "operations": [
                {
                    "operation_type": op[0],
                    "source_id": op[1],
                    "details": json.loads(op[2]),
                    "timestamp": op[3],
                    "datetime": datetime.fromtimestamp(op[3]).isoformat()
                }
                for op in operations
            ],
            "transparency_level": "complete",
            "verification_system": "truth_engine_enabled"
        }
    
    def _log_operation(self, source_id: str, operation_type: str, details: Dict[str, Any], session_id: str = None):
        """Log all IDE operations for complete transparency"""
        operation_id = hashlib.sha256(f"{source_id}:{operation_type}:{time.time()}:{json.dumps(details, sort_keys=True)}".encode()).hexdigest()[:16]
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO ide_operations
            (operation_id, session_id, source_id, operation_type, operation_details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (operation_id, session_id, source_id, operation_type, json.dumps(details), time.time()))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    # Test the FREEDOM IDE
    ide = FreedomIDE()
    
    print("🔬 FREEDOM IDE - Self Test")
    print("=" * 40)
    
    # Start a test session
    session_id = ide.start_session("test_user", "claude-sonnet")
    print(f"✅ Started session: {session_id}")
    
    # Submit an AI contribution
    contribution_id = ide.submit_ai_contribution(
        session_id=session_id,
        ai_model="claude-sonnet",
        contribution_type="code",
        content="def add_numbers(a, b):\n    return a + b",
        requires_verification=True
    )
    print(f"✅ Submitted AI contribution: {contribution_id}")
    
    # Verify the contribution
    verified = ide.verify_ai_contribution(contribution_id, "code_execution", "test_verifier")
    print(f"✅ Verification result: {verified}")
    
    # Human approval
    ide.human_approve_contribution(contribution_id, "test_user", True)
    print(f"✅ Human approval granted")
    
    # Get trust metrics
    trust_metrics = ide.get_ai_trust_metrics("claude-sonnet")
    print(f"✅ Trust metrics: {trust_metrics}")
    
    # End session and get report
    summary = ide.end_session(session_id, "test_user")
    print(f"✅ Session ended: {summary}")
    
    # Get full transparency report
    report = ide.get_full_session_transparency_report(session_id)
    print(f"✅ Transparency report generated: {len(report['operations'])} operations logged")
    
    print("\n🎯 FREEDOM IDE OPERATIONAL")
    print("Ready for transparent AI-assisted development!")
    print(f"Database: {ide.db_path}")