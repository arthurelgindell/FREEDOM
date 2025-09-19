"""
TechKnowledge Auto-Refresh System
Automatically updates technical specifications based on usage patterns
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import logging

from ..core.database import get_db
from ..core.config import TechKnowledgeConfig
from ..extraction.crawler import TechnicalCrawler
from ..github.source_validator import GitHubSourceValidator
from .aging import AgingManager
from .version_tracker import VersionTracker

logger = logging.getLogger(__name__)


class RefreshManager:
    """Manages automatic refresh of technical specifications"""
    
    def __init__(self):
        """Initialize with required components"""
        self.db = get_db()
        self.crawler = TechnicalCrawler()
        self.validator = GitHubSourceValidator()
        self.aging_manager = AgingManager()
        self.version_tracker = VersionTracker()
    
    async def auto_refresh_cycle(self) -> Dict[str, Any]:
        """
        Execute complete auto-refresh cycle
        
        Steps:
        1. Check for new versions
        2. Identify specifications needing refresh
        3. Re-crawl and validate
        4. Update database
        
        Returns:
            Summary of refresh operations
        """
        start_time = datetime.now()
        results = {
            'started_at': start_time.isoformat(),
            'version_updates': {},
            'specifications_refreshed': {},
            'validation_results': {},
            'errors': []
        }
        
        try:
            # Step 1: Check for new versions
            logger.info("Checking for new versions...")
            version_results = await self.version_tracker.check_all_versions()
            results['version_updates'] = version_results
            
            # Step 2: Identify specifications needing refresh
            refresh_targets = self._identify_refresh_targets()
            logger.info(f"Found {len(refresh_targets)} specifications needing refresh")
            
            # Step 3: Refresh specifications
            for target in refresh_targets:
                try:
                    refresh_result = await self._refresh_specification(target)
                    
                    tech_name = target['technology']
                    if tech_name not in results['specifications_refreshed']:
                        results['specifications_refreshed'][tech_name] = []
                    
                    results['specifications_refreshed'][tech_name].append(refresh_result)
                    
                except Exception as e:
                    logger.error(f"Failed to refresh {target['technology']}: {e}")
                    results['errors'].append({
                        'specification': target,
                        'error': str(e)
                    })
            
            # Step 4: Validate refreshed specifications
            validation_tasks = []
            for tech_name in results['specifications_refreshed'].keys():
                validation_tasks.append(
                    self.validator.validate_technology(tech_name)
                )
            
            if validation_tasks:
                validation_results = await asyncio.gather(
                    *validation_tasks, 
                    return_exceptions=True
                )
                
                for i, tech_name in enumerate(results['specifications_refreshed'].keys()):
                    if isinstance(validation_results[i], Exception):
                        results['errors'].append({
                            'technology': tech_name,
                            'error': f"Validation failed: {validation_results[i]}"
                        })
                    else:
                        results['validation_results'][tech_name] = validation_results[i]
            
            # Step 5: Clean up old data
            cleanup_result = self.aging_manager.optimize_storage()
            results['cleanup'] = cleanup_result
            
        except Exception as e:
            logger.error(f"Auto-refresh cycle failed: {e}")
            results['errors'].append({
                'phase': 'cycle',
                'error': str(e)
            })
        
        results['completed_at'] = datetime.now().isoformat()
        results['duration_seconds'] = (datetime.now() - start_time).total_seconds()
        
        return results
    
    def _identify_refresh_targets(self) -> List[Dict[str, Any]]:
        """Identify specifications that need refresh"""
        
        targets = []
        
        # 1. Hot specifications needing refresh
        hot_specs = self.aging_manager.refresh_hot_specifications()
        targets.extend(hot_specs)
        
        # 2. Failed verifications
        failed_query = """
            SELECT DISTINCT
                s.id as specification_id,
                s.source_url,
                s.component_type,
                s.version,
                t.name as technology,
                t.id as technology_id
            FROM specifications s
            JOIN technologies t ON s.technology_id = t.id
            WHERE s.verification_status = 'failed'
            AND s.last_verified > NOW() - INTERVAL '7 days'
            LIMIT 20
        """
        
        failed_specs = self.db.execute_query(failed_query)
        for spec in failed_specs:
            targets.append({
                'specification_id': str(spec['specification_id']),
                'technology': spec['technology'],
                'technology_id': str(spec['technology_id']),
                'version': spec['version'],
                'component_type': spec['component_type'],
                'source_url': spec['source_url'],
                'reason': 'failed_verification'
            })
        
        # 3. Specifications with new versions available
        version_query = """
            SELECT DISTINCT
                s.source_url,
                s.component_type,
                v.version_current as new_version,
                s.version as old_version,
                t.name as technology,
                t.id as technology_id
            FROM specifications s
            JOIN technologies t ON s.technology_id = t.id
            JOIN versions v ON t.id = v.technology_id
            WHERE s.version != v.version_current
            AND t.active = true
            GROUP BY s.source_url, s.component_type, v.version_current, 
                     s.version, t.name, t.id
            LIMIT 30
        """
        
        version_specs = self.db.execute_query(version_query)
        for spec in version_specs:
            targets.append({
                'technology': spec['technology'],
                'technology_id': str(spec['technology_id']),
                'version': spec['new_version'],
                'old_version': spec['old_version'],
                'component_type': spec['component_type'],
                'source_url': spec['source_url'],
                'reason': 'version_update'
            })
        
        # 4. Stale specifications
        stale_specs = self.aging_manager.identify_stale_specifications()
        for spec in stale_specs[:10]:  # Limit to avoid overload
            targets.append({
                'specification_id': spec['specification_id'],
                'technology': spec['technology'],
                'version': spec['version'],
                'component_type': spec['component'].split(':')[0],
                'reason': 'stale_content'
            })
        
        # Deduplicate by technology + component_type
        seen = set()
        unique_targets = []
        for target in targets:
            key = (target['technology'], target.get('component_type', ''))
            if key not in seen:
                seen.add(key)
                unique_targets.append(target)
        
        return unique_targets
    
    async def _refresh_specification(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh a single specification"""
        
        technology = target['technology']
        version = target.get('version', 'current')
        component_type = target.get('component_type')
        source_url = target.get('source_url')
        
        # If no source URL, get from technology
        if not source_url:
            tech_info = self.db.execute_one(
                "SELECT documentation_url FROM technologies WHERE name = %s",
                (technology,)
            )
            source_url = tech_info['documentation_url'] if tech_info else None
        
        if not source_url:
            raise Exception(f"No source URL for {technology}")
        
        # Crawl the documentation
        logger.info(f"Refreshing {technology} {component_type} from {source_url}")
        
        extraction_result = await self.crawler.extract_technical_specs(
            url=source_url,
            technology=technology,
            version=version,
            component_filter=component_type
        )
        
        # Update verification status
        if 'specification_id' in target:
            self.db.execute_query(
                """
                UPDATE specifications 
                SET last_verified = NOW(),
                    verification_status = 'unverified'
                WHERE id = %s
                """,
                (target['specification_id'],)
            )
        
        return {
            'technology': technology,
            'version': version,
            'component_type': component_type,
            'specifications_extracted': len(extraction_result.get('specifications', {})),
            'source_url': source_url,
            'refresh_reason': target.get('reason', 'unknown'),
            'refreshed_at': datetime.now().isoformat()
        }
    
    async def refresh_technology(
        self, 
        technology: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Refresh all specifications for a technology
        
        Args:
            technology: Technology name
            force: Force refresh even if recently updated
            
        Returns:
            Summary of refresh operation
        """
        # Get technology info
        tech_query = """
            SELECT 
                t.id,
                t.documentation_url,
                t.github_repo,
                v.version_current
            FROM technologies t
            JOIN versions v ON t.id = v.technology_id
            WHERE t.name = %s
        """
        
        tech_info = self.db.execute_one(tech_query, (technology,))
        
        if not tech_info:
            return {'error': f'Technology {technology} not found'}
        
        # Get all source URLs for this technology
        source_query = """
            SELECT DISTINCT source_url, component_type
            FROM specifications
            WHERE technology_id = %s
        """
        
        if not force:
            source_query += " AND last_verified < NOW() - INTERVAL '7 days'"
        
        sources = self.db.execute_query(source_query, (tech_info['id'],))
        
        # Refresh each source
        results = {
            'technology': technology,
            'version': tech_info['version_current'],
            'sources_refreshed': [],
            'errors': []
        }
        
        for source in sources:
            try:
                extraction_result = await self.crawler.extract_technical_specs(
                    url=source['source_url'],
                    technology=technology,
                    version=tech_info['version_current'],
                    component_filter=source['component_type']
                )
                
                results['sources_refreshed'].append({
                    'url': source['source_url'],
                    'component_type': source['component_type'],
                    'specifications': len(extraction_result.get('specifications', {}))
                })
                
            except Exception as e:
                results['errors'].append({
                    'url': source['source_url'],
                    'error': str(e)
                })
        
        # Validate after refresh
        if results['sources_refreshed']:
            validation_result = await self.validator.validate_technology(
                technology, tech_info['version_current']
            )
            results['validation'] = validation_result
        
        return results
    
    def schedule_refresh(
        self,
        technology: str,
        component_type: Optional[str] = None,
        priority: str = 'normal'
    ) -> Dict[str, Any]:
        """
        Schedule a specification for refresh
        
        Args:
            technology: Technology name
            component_type: Specific component to refresh
            priority: 'high', 'normal', or 'low'
            
        Returns:
            Scheduling confirmation
        """
        # This would integrate with a task queue in production
        # For now, we'll update the next_check time to trigger sooner
        
        priority_intervals = {
            'high': timedelta(hours=1),
            'normal': timedelta(days=1),
            'low': timedelta(days=7)
        }
        
        next_check = datetime.now() + priority_intervals.get(priority, timedelta(days=1))
        
        update_query = """
            UPDATE specifications s
            SET last_verified = last_verified - INTERVAL '8 days'
            FROM technologies t
            WHERE s.technology_id = t.id
            AND t.name = %s
        """
        
        params = [technology]
        if component_type:
            update_query += " AND s.component_type = %s"
            params.append(component_type)
        
        affected = self.db.execute_query(update_query, tuple(params))
        
        return {
            'technology': technology,
            'component_type': component_type,
            'priority': priority,
            'scheduled_for': next_check.isoformat(),
            'specifications_scheduled': len(affected) if affected else 0
        }
    
    def get_refresh_status(self) -> Dict[str, Any]:
        """Get current refresh system status"""
        
        # Get refresh statistics
        stats_query = """
            SELECT 
                COUNT(*) FILTER (WHERE last_verified > NOW() - INTERVAL '1 day') as refreshed_today,
                COUNT(*) FILTER (WHERE last_verified > NOW() - INTERVAL '7 days') as refreshed_week,
                COUNT(*) FILTER (WHERE last_verified < NOW() - INTERVAL '30 days') as stale_month,
                COUNT(*) FILTER (WHERE verification_status = 'failed') as failed_verifications,
                AVG(EXTRACT(EPOCH FROM (NOW() - last_verified)) / 86400)::int as avg_days_since_refresh
            FROM specifications
        """
        
        stats = self.db.execute_one(stats_query)
        
        # Get pending refreshes
        pending_query = """
            SELECT 
                t.name as technology,
                COUNT(*) as specs_needing_refresh
            FROM specifications s
            JOIN technologies t ON s.technology_id = t.id
            WHERE s.last_verified < NOW() - INTERVAL '7 days'
            OR s.verification_status = 'failed'
            GROUP BY t.name
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """
        
        pending = self.db.execute_query(pending_query)
        
        return {
            'statistics': {
                'refreshed_today': stats['refreshed_today'],
                'refreshed_this_week': stats['refreshed_week'],
                'stale_over_month': stats['stale_month'],
                'failed_verifications': stats['failed_verifications'],
                'average_age_days': stats['avg_days_since_refresh']
            },
            'pending_refreshes': [
                {
                    'technology': p['technology'],
                    'specifications': p['specs_needing_refresh']
                }
                for p in pending
            ],
            'refresh_health': self._calculate_refresh_health(stats)
        }
    
    def _calculate_refresh_health(self, stats: Dict) -> str:
        """Calculate overall refresh system health"""
        
        avg_age = stats['avg_days_since_refresh']
        failed_pct = stats['failed_verifications'] / max((stats['refreshed_week'] + stats['stale_month']), 1)
        
        if avg_age < 14 and failed_pct < 0.05:
            return 'excellent'
        elif avg_age < 30 and failed_pct < 0.1:
            return 'good'
        elif avg_age < 60 and failed_pct < 0.2:
            return 'fair'
        else:
            return 'poor'

