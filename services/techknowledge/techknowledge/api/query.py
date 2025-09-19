"""
TechKnowledge Query API
Interface for AI agents to access pure technical knowledge
Sub-100ms response time target
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import time
from functools import lru_cache
import hashlib

from ..core.database import get_db
from ..core.models import TechnicalQuery, TechnicalResponse
from ..core.config import TechKnowledgeConfig


class TechKnowledgeQuery:
    """Query interface for AI agents to access technical knowledge"""
    
    def __init__(self):
        """Initialize with database connection"""
        self.db = get_db()
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 3600  # 1 hour cache
    
    def get_specification(
        self,
        technology: str,
        component: Optional[str] = None,
        version: Optional[str] = 'current',
        include_validations: bool = False,
        include_usage_stats: bool = False
    ) -> TechnicalResponse:
        """
        Retrieve pure technical specifications
        
        Args:
            technology: Name of the technology (e.g., 'redis', 'postgresql')
            component: Specific component ('api', 'config', 'types', 'limits', 'protocols')
            version: Version to retrieve ('current', 'previous', 'legacy', or specific)
            include_validations: Include GitHub validation results
            include_usage_stats: Include usage statistics
        
        Returns:
            Technical specifications with zero human contamination
        """
        start_time = time.time()
        
        # Create query object
        query = TechnicalQuery(
            technology=technology,
            component=component,
            version=version,
            include_validations=include_validations,
            include_usage_stats=include_usage_stats
        )
        
        # Check cache first
        cache_key = query.cache_key()
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                query_time = (time.time() - start_time) * 1000
                cached_data.query_time_ms = query_time
                return cached_data
        
        # Get version information
        version_info = self._get_version_info(technology)
        if not version_info:
            return self._error_response(
                f"Technology {technology} not found",
                technology, version, component, start_time
            )
        
        # Resolve version alias
        target_version = self._resolve_version(version, version_info)
        
        # Query specifications
        specifications = self._query_specifications(
            technology, target_version, component,
            include_validations, include_usage_stats
        )
        
        # Track usage
        self._track_usage(technology, target_version, component, len(specifications))
        
        # Build response
        response = TechnicalResponse(
            technology=technology,
            version=target_version,
            component=component,
            specifications=specifications,
            metadata={
                'version_info': {
                    'current': version_info['version_current'],
                    'previous': version_info['version_previous'],
                    'legacy': version_info['version_legacy']
                },
                'query_timestamp': datetime.now().isoformat(),
                'result_count': len(specifications),
                'cache_hit': False
            },
            query_time_ms=(time.time() - start_time) * 1000
        )
        
        # Cache the response
        self._cache[cache_key] = (time.time(), response)
        
        return response
    
    def _get_version_info(self, technology: str) -> Optional[Dict[str, Any]]:
        """Get version information for a technology"""
        query = """
            SELECT 
                v.version_current,
                v.version_previous,
                v.version_legacy,
                v.current_released,
                v.current_eol,
                v.update_frequency
            FROM versions v
            JOIN technologies t ON v.technology_id = t.id
            WHERE t.name = %s
            ORDER BY v.last_checked DESC
            LIMIT 1
        """
        
        return self.db.execute_one(query, (technology,))
    
    def _resolve_version(
        self, 
        version_alias: str, 
        version_info: Dict[str, Any]
    ) -> str:
        """Resolve version alias to actual version"""
        if version_alias == 'current':
            return version_info['version_current']
        elif version_alias == 'previous':
            return version_info['version_previous'] or version_info['version_current']
        elif version_alias == 'legacy':
            return version_info['version_legacy'] or version_info['version_previous'] or version_info['version_current']
        else:
            return version_alias
    
    def _query_specifications(
        self,
        technology: str,
        version: str,
        component: Optional[str],
        include_validations: bool,
        include_usage_stats: bool
    ) -> List[Dict[str, Any]]:
        """Query specifications from database"""
        
        # Base query
        query = """
            SELECT 
                s.id,
                s.component_type,
                s.component_name,
                s.specification,
                s.source_url,
                s.source_type,
                s.confidence_score,
                s.last_verified,
                s.verification_status,
                s.extracted_at
            FROM specifications s
            JOIN technologies t ON s.technology_id = t.id
            WHERE t.name = %s 
            AND s.version = %s
            AND s.verification_status != 'failed'
        """
        
        params = [technology, version]
        
        # Add component filter if specified
        if component:
            query += " AND s.component_type = %s"
            params.append(component)
        
        # Order by confidence and verification
        query += """
            ORDER BY 
                s.confidence_score DESC,
                s.last_verified DESC
        """
        
        # Execute query
        specs = self.db.execute_query(query, tuple(params))
        
        # Format specifications
        formatted_specs = []
        for spec in specs:
            formatted = {
                'id': str(spec['id']),
                'type': spec['component_type'],
                'name': spec['component_name'],
                'specification': spec['specification'],
                'source': {
                    'url': spec['source_url'],
                    'type': spec['source_type']
                },
                'confidence': spec['confidence_score'],
                'verification': {
                    'status': spec['verification_status'],
                    'last_checked': spec['last_verified'].isoformat() if spec['last_verified'] else None
                },
                'extracted': spec['extracted_at'].isoformat() if spec['extracted_at'] else None
            }
            
            # Add optional data
            if include_validations:
                formatted['validations'] = self._get_validations(spec['id'])
            
            if include_usage_stats:
                formatted['usage'] = self._get_usage_stats(spec['id'])
            
            formatted_specs.append(formatted)
        
        return formatted_specs
    
    def _get_validations(self, spec_id: str) -> List[Dict[str, Any]]:
        """Get GitHub validations for a specification"""
        query = """
            SELECT 
                github_url,
                file_path,
                commit_sha,
                validation_type,
                matches,
                discrepancies,
                validated_at
            FROM github_validations
            WHERE specification_id = %s
            ORDER BY validated_at DESC
            LIMIT 5
        """
        
        validations = self.db.execute_query(query, (spec_id,))
        
        return [
            {
                'github_url': v['github_url'],
                'file': v['file_path'],
                'commit': v['commit_sha'],
                'type': v['validation_type'],
                'matches': v['matches'],
                'issues': json.loads(v['discrepancies']) if v['discrepancies'] else None,
                'checked': v['validated_at'].isoformat() if v['validated_at'] else None
            }
            for v in validations
        ]
    
    def _get_usage_stats(self, spec_id: str) -> Dict[str, Any]:
        """Get usage statistics for a specification"""
        stats_query = """
            SELECT 
                COUNT(*) as total_accesses,
                COUNT(DISTINCT accessed_by) as unique_users,
                MAX(accessed_at) as last_accessed,
                AVG(CASE WHEN was_useful THEN 1 ELSE 0 END) as usefulness_score
            FROM usage_tracking
            WHERE specification_id = %s
            AND accessed_at > NOW() - INTERVAL '30 days'
        """
        
        stats = self.db.execute_one(stats_query, (spec_id,))
        
        return {
            'accesses_30d': stats['total_accesses'],
            'unique_users': stats['unique_users'],
            'last_accessed': stats['last_accessed'].isoformat() if stats['last_accessed'] else None,
            'usefulness': float(stats['usefulness_score']) if stats['usefulness_score'] else None
        }
    
    def _track_usage(
        self, 
        technology: str, 
        version: str, 
        component: Optional[str],
        result_count: int
    ):
        """Record usage for aging/refresh decisions"""
        # Get specification IDs that were accessed
        spec_query = """
            SELECT s.id
            FROM specifications s
            JOIN technologies t ON s.technology_id = t.id
            WHERE t.name = %s AND s.version = %s
        """
        
        params = [technology, version]
        if component:
            spec_query += " AND s.component_type = %s"
            params.append(component)
        
        spec_query += " LIMIT 10"  # Track top 10 specs
        
        specs = self.db.execute_query(spec_query, tuple(params))
        
        # Insert usage tracking records
        if specs:
            tracking_data = [
                (
                    spec['id'],
                    'ai_agent',  # TODO: Get actual agent name from context
                    'query',
                    f"component:{component}" if component else "general"
                )
                for spec in specs
            ]
            
            insert_query = """
                INSERT INTO usage_tracking 
                (specification_id, accessed_by, access_type, access_context)
                VALUES (%s, %s, %s, %s)
            """
            
            self.db.execute_many(insert_query, tracking_data)
    
    def _error_response(
        self,
        error_message: str,
        technology: str,
        version: str,
        component: Optional[str],
        start_time: float
    ) -> TechnicalResponse:
        """Create error response"""
        return TechnicalResponse(
            technology=technology,
            version=version,
            component=component,
            specifications=[],
            metadata={
                'error': error_message,
                'query_timestamp': datetime.now().isoformat()
            },
            query_time_ms=(time.time() - start_time) * 1000
        )
    
    def search_specifications(
        self,
        search_term: str,
        technology: Optional[str] = None,
        component_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across specifications
        
        Args:
            search_term: Text to search for
            technology: Filter by technology
            component_type: Filter by component type
            limit: Maximum results to return
            
        Returns:
            List of matching specifications
        """
        start_time = time.time()
        
        # Build search query using PostgreSQL full-text search
        query = """
            SELECT 
                s.id,
                s.component_type,
                s.component_name,
                s.specification,
                s.version,
                t.name as technology_name,
                ts_rank(to_tsvector('english', s.specification::text), 
                       plainto_tsquery('english', %s)) as rank
            FROM specifications s
            JOIN technologies t ON s.technology_id = t.id
            WHERE to_tsvector('english', s.specification::text) @@ 
                  plainto_tsquery('english', %s)
            AND s.verification_status != 'failed'
        """
        
        params = [search_term, search_term]
        
        if technology:
            query += " AND t.name = %s"
            params.append(technology)
        
        if component_type:
            query += " AND s.component_type = %s"
            params.append(component_type)
        
        query += " ORDER BY rank DESC LIMIT %s"
        params.append(limit)
        
        results = self.db.execute_query(query, tuple(params))
        
        # Format results
        formatted_results = [
            {
                'id': str(r['id']),
                'technology': r['technology_name'],
                'version': r['version'],
                'type': r['component_type'],
                'name': r['component_name'],
                'relevance_score': float(r['rank']),
                'preview': self._extract_preview(
                    r['specification'], search_term
                )
            }
            for r in results
        ]
        
        query_time = (time.time() - start_time) * 1000
        
        return {
            'search_term': search_term,
            'results': formatted_results,
            'count': len(formatted_results),
            'query_time_ms': query_time
        }
    
    def _extract_preview(
        self, 
        specification: Dict[str, Any], 
        search_term: str,
        max_length: int = 200
    ) -> str:
        """Extract preview snippet around search term"""
        spec_text = json.dumps(specification, indent=2)
        
        # Find search term in text (case-insensitive)
        lower_text = spec_text.lower()
        lower_term = search_term.lower()
        
        pos = lower_text.find(lower_term)
        if pos == -1:
            # Not found, return beginning
            return spec_text[:max_length] + "..."
        
        # Extract context around match
        start = max(0, pos - max_length // 2)
        end = min(len(spec_text), pos + len(search_term) + max_length // 2)
        
        preview = spec_text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            preview = "..." + preview
        if end < len(spec_text):
            preview = preview + "..."
        
        return preview
    
    def get_technology_summary(
        self, 
        technology: str
    ) -> Dict[str, Any]:
        """Get summary of available technical knowledge for a technology"""
        
        summary_query = """
            SELECT 
                t.id,
                t.name,
                t.category,
                t.official_url,
                t.github_repo,
                COUNT(DISTINCT s.component_type) as component_types,
                COUNT(DISTINCT s.version) as versions,
                COUNT(*) as total_specs,
                MAX(s.extracted_at) as last_updated,
                AVG(s.confidence_score) as avg_confidence
            FROM technologies t
            LEFT JOIN specifications s ON t.id = s.technology_id
            WHERE t.name = %s
            GROUP BY t.id, t.name, t.category, t.official_url, t.github_repo
        """
        
        summary = self.db.execute_one(summary_query, (technology,))
        
        if not summary:
            return {'error': f'Technology {technology} not found'}
        
        # Get component breakdown
        component_query = """
            SELECT 
                component_type,
                COUNT(*) as count,
                AVG(confidence_score) as avg_confidence
            FROM specifications
            WHERE technology_id = %s
            GROUP BY component_type
            ORDER BY count DESC
        """
        
        components = self.db.execute_query(component_query, (summary['id'],))
        
        # Get version information
        version_info = self._get_version_info(technology)
        
        return {
            'technology': summary['name'],
            'category': summary['category'],
            'sources': {
                'documentation': summary['official_url'],
                'github': summary['github_repo']
            },
            'coverage': {
                'component_types': summary['component_types'],
                'versions': summary['versions'],
                'total_specifications': summary['total_specs'],
                'average_confidence': float(summary['avg_confidence']) if summary['avg_confidence'] else 0
            },
            'components': [
                {
                    'type': c['component_type'],
                    'count': c['count'],
                    'confidence': float(c['avg_confidence'])
                }
                for c in components
            ],
            'versions': version_info if version_info else {},
            'last_updated': summary['last_updated'].isoformat() if summary['last_updated'] else None
        }
    
    def provide_feedback(
        self,
        specification_id: str,
        was_useful: bool,
        accessed_by: str = 'ai_agent',
        context: Optional[str] = None
    ):
        """Provide feedback on specification usefulness"""
        
        # Update the most recent usage tracking entry
        update_query = """
            UPDATE usage_tracking
            SET was_useful = %s
            WHERE specification_id = %s
            AND accessed_by = %s
            ORDER BY accessed_at DESC
            LIMIT 1
        """
        
        self.db.execute_query(
            update_query,
            (was_useful, specification_id, accessed_by)
        )