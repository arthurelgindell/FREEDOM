"""
TechKnowledge Aging System
12-month lifecycle management with usage-based refresh
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

from ..core.database import get_db
from ..core.config import TechKnowledgeConfig

logger = logging.getLogger(__name__)


class AgingManager:
    """Manage specification lifecycle with tiered aging"""
    
    def __init__(self):
        """Initialize with database and aging configuration"""
        self.db = get_db()
        
        # Aging tiers in days
        self.hot_tier = TechKnowledgeConfig.HOT_TIER_DAYS    # 90 days
        self.warm_tier = TechKnowledgeConfig.WARM_TIER_DAYS  # 180 days
        self.cold_tier = TechKnowledgeConfig.COLD_TIER_DAYS  # 365 days
        self.purge_after = TechKnowledgeConfig.PURGE_AFTER_DAYS  # 365 days
    
    def analyze_specification_age(self) -> Dict[str, List[Dict]]:
        """
        Analyze all specifications and categorize by age tier
        
        Returns:
            Dictionary with keys: 'hot', 'warm', 'cold', 'expired'
        """
        now = datetime.now()
        
        # Query all specifications with usage data
        query = """
            SELECT 
                s.id,
                s.technology_id,
                s.component_type,
                s.component_name,
                s.version,
                s.extracted_at,
                s.last_verified,
                t.name as technology_name,
                MAX(u.accessed_at) as last_accessed,
                COUNT(u.id) as access_count,
                AVG(CASE WHEN u.was_useful THEN 1 ELSE 0 END) as usefulness_score
            FROM specifications s
            JOIN technologies t ON s.technology_id = t.id
            LEFT JOIN usage_tracking u ON s.id = u.specification_id
            GROUP BY s.id, s.technology_id, s.component_type, 
                     s.component_name, s.version, s.extracted_at, 
                     s.last_verified, t.name
        """
        
        specs = self.db.execute_query(query)
        
        # Categorize by age and usage
        tiers = {
            'hot': [],      # Recently accessed, high usage
            'warm': [],     # Moderate age/usage
            'cold': [],     # Old, low usage
            'expired': []   # Ready for purge
        }
        
        for spec in specs:
            age_days = (now - spec['extracted_at']).days
            last_access = spec['last_accessed']
            days_since_access = (now - last_access).days if last_access else age_days
            
            spec_info = {
                'id': str(spec['id']),
                'technology': spec['technology_name'],
                'component': f"{spec['component_type']}:{spec['component_name']}",
                'version': spec['version'],
                'age_days': age_days,
                'days_since_access': days_since_access,
                'access_count': spec['access_count'],
                'usefulness': float(spec['usefulness_score']) if spec['usefulness_score'] else 0
            }
            
            # Determine tier based on age and usage
            if days_since_access <= self.hot_tier and spec['access_count'] > 0:
                tiers['hot'].append(spec_info)
            elif days_since_access <= self.warm_tier or age_days <= self.warm_tier:
                tiers['warm'].append(spec_info)
            elif days_since_access <= self.cold_tier or age_days <= self.cold_tier:
                tiers['cold'].append(spec_info)
            else:
                tiers['expired'].append(spec_info)
        
        return tiers
    
    def refresh_hot_specifications(self) -> List[Dict]:
        """
        Identify hot specifications that need refresh
        
        Returns specifications that are:
        - Frequently accessed (hot tier)
        - Haven't been verified recently
        - High usefulness score
        """
        query = """
            SELECT DISTINCT
                s.id,
                s.technology_id,
                s.version,
                s.component_type,
                s.source_url,
                t.name as technology_name,
                COUNT(u.id) as recent_accesses,
                AVG(CASE WHEN u.was_useful THEN 1 ELSE 0 END) as usefulness
            FROM specifications s
            JOIN technologies t ON s.technology_id = t.id
            JOIN usage_tracking u ON s.id = u.specification_id
            WHERE u.accessed_at > NOW() - INTERVAL '%s days'
            AND s.last_verified < NOW() - INTERVAL '7 days'
            GROUP BY s.id, s.technology_id, s.version, 
                     s.component_type, s.source_url, t.name
            HAVING COUNT(u.id) >= 5  -- At least 5 accesses
            AND AVG(CASE WHEN u.was_useful THEN 1 ELSE 0 END) >= 0.7  -- 70% useful
            ORDER BY recent_accesses DESC
        """
        
        specs = self.db.execute_query(query, (self.hot_tier,))
        
        return [
            {
                'specification_id': str(spec['id']),
                'technology': spec['technology_name'],
                'version': spec['version'],
                'component_type': spec['component_type'],
                'source_url': spec['source_url'],
                'recent_accesses': spec['recent_accesses'],
                'usefulness_score': float(spec['usefulness'])
            }
            for spec in specs
        ]
    
    def identify_stale_specifications(self) -> List[Dict]:
        """
        Identify specifications that are stale and need refresh
        
        Criteria:
        - Not accessed in warm tier period
        - Low usefulness scores
        - Failed verification
        """
        query = """
            SELECT 
                s.id,
                s.technology_id,
                s.version,
                s.component_type,
                s.component_name,
                s.verification_status,
                s.last_verified,
                t.name as technology_name,
                MAX(u.accessed_at) as last_accessed,
                COUNT(u.id) as total_accesses,
                AVG(CASE WHEN u.was_useful THEN 1 ELSE 0 END) as usefulness
            FROM specifications s
            JOIN technologies t ON s.technology_id = t.id
            LEFT JOIN usage_tracking u ON s.id = u.specification_id
            WHERE s.verification_status IN ('failed', 'outdated')
            OR s.last_verified < NOW() - INTERVAL '%s days'
            GROUP BY s.id, s.technology_id, s.version, s.component_type,
                     s.component_name, s.verification_status, s.last_verified, t.name
            HAVING MAX(u.accessed_at) < NOW() - INTERVAL '%s days'
            OR MAX(u.accessed_at) IS NULL
            OR AVG(CASE WHEN u.was_useful THEN 1 ELSE 0 END) < 0.3
        """
        
        specs = self.db.execute_query(query, (self.warm_tier, self.warm_tier))
        
        return [
            {
                'specification_id': str(spec['id']),
                'technology': spec['technology_name'],
                'component': f"{spec['component_type']}:{spec['component_name']}",
                'version': spec['version'],
                'verification_status': spec['verification_status'],
                'days_since_verified': (datetime.now() - spec['last_verified']).days if spec['last_verified'] else None,
                'days_since_accessed': (datetime.now() - spec['last_accessed']).days if spec['last_accessed'] else None,
                'total_accesses': spec['total_accesses'],
                'usefulness_score': float(spec['usefulness']) if spec['usefulness'] else 0
            }
            for spec in specs
        ]
    
    def purge_expired_specifications(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Purge specifications that have expired
        
        Args:
            dry_run: If True, only return what would be purged
            
        Returns:
            Summary of purged specifications
        """
        # Find specifications to purge
        purge_query = """
            SELECT 
                s.id,
                s.technology_id,
                s.component_type,
                s.component_name,
                s.version,
                t.name as technology_name,
                s.extracted_at,
                MAX(u.accessed_at) as last_accessed
            FROM specifications s
            JOIN technologies t ON s.technology_id = t.id
            LEFT JOIN usage_tracking u ON s.id = u.specification_id
            GROUP BY s.id, s.technology_id, s.component_type,
                     s.component_name, s.version, t.name, s.extracted_at
            HAVING MAX(u.accessed_at) < NOW() - INTERVAL '%s days'
            OR (MAX(u.accessed_at) IS NULL AND s.extracted_at < NOW() - INTERVAL '%s days')
        """
        
        specs_to_purge = self.db.execute_query(
            purge_query, 
            (self.purge_after, self.purge_after)
        )
        
        summary = {
            'total_to_purge': len(specs_to_purge),
            'dry_run': dry_run,
            'purged_specs': [],
            'by_technology': {}
        }
        
        # Group by technology
        for spec in specs_to_purge:
            tech = spec['technology_name']
            if tech not in summary['by_technology']:
                summary['by_technology'][tech] = 0
            summary['by_technology'][tech] += 1
            
            summary['purged_specs'].append({
                'id': str(spec['id']),
                'technology': tech,
                'component': f"{spec['component_type']}:{spec['component_name']}",
                'version': spec['version'],
                'age_days': (datetime.now() - spec['extracted_at']).days
            })
        
        if not dry_run and specs_to_purge:
            # Perform actual deletion
            spec_ids = [spec['id'] for spec in specs_to_purge]
            
            # Delete in correct order due to foreign keys
            delete_queries = [
                "DELETE FROM usage_tracking WHERE specification_id = ANY(%s)",
                "DELETE FROM github_validations WHERE specification_id = ANY(%s)",
                "DELETE FROM specifications WHERE id = ANY(%s)"
            ]
            
            for query in delete_queries:
                self.db.execute_query(query, (spec_ids,))
            
            logger.info(f"Purged {len(spec_ids)} expired specifications")
        
        return summary
    
    def optimize_storage(self) -> Dict[str, Any]:
        """
        Optimize storage by removing redundant specifications
        
        Returns:
            Summary of optimization performed
        """
        # Find duplicate specifications (same tech, version, component, checksum)
        duplicate_query = """
            WITH duplicates AS (
                SELECT 
                    technology_id,
                    version,
                    component_type,
                    component_name,
                    source_checksum,
                    COUNT(*) as duplicate_count,
                    MIN(extracted_at) as oldest,
                    MAX(confidence_score) as best_confidence
                FROM specifications
                WHERE source_checksum IS NOT NULL
                GROUP BY technology_id, version, component_type, 
                         component_name, source_checksum
                HAVING COUNT(*) > 1
            )
            SELECT 
                s.id,
                s.technology_id,
                s.version,
                s.component_type,
                s.component_name,
                s.confidence_score,
                s.extracted_at,
                d.duplicate_count
            FROM specifications s
            JOIN duplicates d ON 
                s.technology_id = d.technology_id
                AND s.version = d.version
                AND s.component_type = d.component_type
                AND s.component_name = d.component_name
                AND s.source_checksum = d.source_checksum
            WHERE s.extracted_at != d.oldest  -- Keep oldest
            OR s.confidence_score != d.best_confidence  -- Keep best confidence
        """
        
        duplicates = self.db.execute_query(duplicate_query)
        
        # Remove duplicates keeping the best version
        removed_count = 0
        if duplicates:
            dup_ids = [dup['id'] for dup in duplicates]
            
            # Delete associated records first
            self.db.execute_query(
                "DELETE FROM usage_tracking WHERE specification_id = ANY(%s)",
                (dup_ids,)
            )
            self.db.execute_query(
                "DELETE FROM github_validations WHERE specification_id = ANY(%s)",
                (dup_ids,)
            )
            self.db.execute_query(
                "DELETE FROM specifications WHERE id = ANY(%s)",
                (dup_ids,)
            )
            
            removed_count = len(dup_ids)
        
        # Vacuum analyze for performance
        with self.db.get_connection() as conn:
            conn.set_isolation_level(0)  # AUTOCOMMIT
            with conn.cursor() as cur:
                cur.execute("VACUUM ANALYZE specifications")
        
        return {
            'duplicates_removed': removed_count,
            'storage_optimized': True,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_aging_report(self) -> Dict[str, Any]:
        """Generate comprehensive aging report"""
        
        # Get tier breakdown
        tiers = self.analyze_specification_age()
        
        # Get refresh candidates
        refresh_needed = self.refresh_hot_specifications()
        
        # Get stale specifications
        stale_specs = self.identify_stale_specifications()
        
        # Get purge candidates
        purge_summary = self.purge_expired_specifications(dry_run=True)
        
        # Calculate storage metrics
        storage_query = """
            SELECT 
                COUNT(*) as total_specs,
                SUM(pg_column_size(specification)) as total_size,
                AVG(pg_column_size(specification)) as avg_size,
                COUNT(DISTINCT technology_id) as technologies,
                COUNT(DISTINCT version) as versions
            FROM specifications
        """
        
        storage = self.db.execute_one(storage_query)
        
        return {
            'report_date': datetime.now().isoformat(),
            'tier_distribution': {
                'hot': len(tiers['hot']),
                'warm': len(tiers['warm']),
                'cold': len(tiers['cold']),
                'expired': len(tiers['expired'])
            },
            'action_required': {
                'refresh_needed': len(refresh_needed),
                'stale_specs': len(stale_specs),
                'ready_to_purge': purge_summary['total_to_purge']
            },
            'storage_metrics': {
                'total_specifications': storage['total_specs'],
                'total_size_bytes': storage['total_size'],
                'average_size_bytes': float(storage['avg_size']) if storage['avg_size'] else 0,
                'unique_technologies': storage['technologies'],
                'unique_versions': storage['versions']
            },
            'recommendations': self._generate_recommendations(
                tiers, refresh_needed, stale_specs, purge_summary
            )
        }
    
    def _generate_recommendations(
        self,
        tiers: Dict,
        refresh_needed: List,
        stale_specs: List,
        purge_summary: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        # Hot tier recommendations
        if len(tiers['hot']) > 100:
            recommendations.append(
                f"High activity: {len(tiers['hot'])} specifications in hot tier. "
                "Consider increasing refresh frequency."
            )
        
        # Refresh recommendations
        if len(refresh_needed) > 20:
            recommendations.append(
                f"Refresh needed: {len(refresh_needed)} frequently-used specifications "
                "haven't been verified recently."
            )
        
        # Stale content
        if len(stale_specs) > 50:
            recommendations.append(
                f"Stale content: {len(stale_specs)} specifications are outdated "
                "or have low usefulness scores."
            )
        
        # Storage recommendations
        if purge_summary['total_to_purge'] > 100:
            recommendations.append(
                f"Storage cleanup: {purge_summary['total_to_purge']} expired "
                "specifications can be purged to free space."
            )
        
        return recommendations

