"""
TechKnowledge Version Tracker
Maintains current + 2 previous versions with auto-update detection
"""

import re
import httpx
import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import feedparser
import logging
from packaging import version as pkg_version

from ..core.database import get_db
from ..core.config import TechKnowledgeConfig
from ..core.models import Technology, Version

logger = logging.getLogger(__name__)


class VersionTracker:
    """Track and manage technology versions"""
    
    def __init__(self):
        """Initialize with database connection"""
        self.db = get_db()
        self.github_headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'TechKnowledge-VersionTracker'
        }
        if TechKnowledgeConfig.GITHUB_TOKEN:
            self.github_headers['Authorization'] = f'token {TechKnowledgeConfig.GITHUB_TOKEN}'
    
    async def check_all_versions(self) -> Dict[str, List[Dict]]:
        """
        Check for new versions of all tracked technologies
        
        Returns:
            Dictionary with 'updated' and 'failed' lists
        """
        # Get technologies due for version check
        query = """
            SELECT 
                t.id,
                t.name,
                t.github_repo,
                t.release_feed_url,
                v.version_current,
                v.next_check
            FROM technologies t
            JOIN versions v ON t.id = v.technology_id
            WHERE v.next_check <= NOW()
            OR v.next_check IS NULL
            ORDER BY v.next_check ASC
        """
        
        technologies = self.db.execute_query(query)
        
        results = {
            'updated': [],
            'failed': [],
            'no_change': []
        }
        
        for tech in technologies:
            try:
                update_info = await self._check_technology_version(tech)
                
                if update_info['new_version_found']:
                    results['updated'].append(update_info)
                else:
                    results['no_change'].append(update_info)
                    
            except Exception as e:
                logger.error(f"Failed to check version for {tech['name']}: {e}")
                results['failed'].append({
                    'technology': tech['name'],
                    'error': str(e)
                })
        
        return results
    
    async def _check_technology_version(self, tech: Dict) -> Dict[str, Any]:
        """Check for new version of a specific technology"""
        
        tech_name = tech['name']
        current_version = tech['version_current']
        
        # Try multiple sources for version information
        latest_version = None
        version_info = {}
        
        # 1. Check GitHub releases if available
        if tech['github_repo']:
            github_version = await self._check_github_releases(tech['github_repo'])
            if github_version:
                latest_version = github_version['version']
                version_info = github_version
        
        # 2. Check RSS/Atom feed if available
        if not latest_version and tech['release_feed_url']:
            feed_version = await self._check_release_feed(tech['release_feed_url'])
            if feed_version:
                latest_version = feed_version['version']
                version_info = feed_version
        
        # 3. Technology-specific checkers
        if not latest_version:
            specific_version = await self._check_technology_specific(tech_name)
            if specific_version:
                latest_version = specific_version['version']
                version_info = specific_version
        
        # Compare versions
        new_version_found = False
        if latest_version and latest_version != current_version:
            try:
                # Use packaging library for proper version comparison
                if pkg_version.parse(latest_version) > pkg_version.parse(current_version):
                    new_version_found = True
            except Exception:
                # Fallback to string comparison
                new_version_found = latest_version != current_version
        
        # Update database
        if new_version_found:
            await self._update_version_info(
                tech['id'], 
                latest_version, 
                current_version,
                version_info
            )
        
        # Update next check time
        self._update_next_check(tech['id'])
        
        return {
            'technology': tech_name,
            'current_version': current_version,
            'latest_version': latest_version,
            'new_version_found': new_version_found,
            'version_info': version_info,
            'checked_at': datetime.now().isoformat()
        }
    
    async def _check_github_releases(self, repo: str) -> Optional[Dict[str, Any]]:
        """Check GitHub releases for latest version"""
        
        # Parse repo URL
        if 'github.com' in repo:
            parts = repo.replace('https://github.com/', '').strip('/').split('/')
            owner, repo_name = parts[0], parts[1].replace('.git', '')
        else:
            owner, repo_name = repo.split('/')
        
        url = f"https://api.github.com/repos/{owner}/{repo_name}/releases/latest"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.github_headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract version from tag name
                    tag = data.get('tag_name', '')
                    version = self._extract_version_from_tag(tag)
                    
                    if version:
                        return {
                            'version': version,
                            'released_at': data.get('published_at'),
                            'release_url': data.get('html_url'),
                            'release_notes_url': data.get('body'),
                            'source': 'github_releases'
                        }
                        
        except Exception as e:
            logger.warning(f"Failed to check GitHub releases for {repo}: {e}")
        
        return None
    
    async def _check_release_feed(self, feed_url: str) -> Optional[Dict[str, Any]]:
        """Check RSS/Atom feed for latest version"""
        
        try:
            # Parse feed
            feed = feedparser.parse(feed_url)
            
            if feed.entries:
                # Look for version in first entry
                latest_entry = feed.entries[0]
                
                # Try to extract version from title or link
                title = latest_entry.get('title', '')
                version = self._extract_version_from_text(title)
                
                if version:
                    return {
                        'version': version,
                        'released_at': latest_entry.get('published', ''),
                        'release_url': latest_entry.get('link', ''),
                        'source': 'release_feed'
                    }
                    
        except Exception as e:
            logger.warning(f"Failed to check release feed {feed_url}: {e}")
        
        return None
    
    async def _check_technology_specific(self, tech_name: str) -> Optional[Dict[str, Any]]:
        """Technology-specific version checkers"""
        
        # Define specific checkers for major technologies
        checkers = {
            'python': self._check_python_version,
            'node': self._check_node_version,
            'redis': self._check_redis_version,
            'postgresql': self._check_postgres_version,
            'react': self._check_npm_package_version,
            'vue': self._check_npm_package_version,
            'django': self._check_pypi_package_version,
            'flask': self._check_pypi_package_version
        }
        
        checker = checkers.get(tech_name.lower())
        if checker:
            return await checker(tech_name)
        
        return None
    
    async def _check_python_version(self, tech_name: str) -> Optional[Dict[str, Any]]:
        """Check Python.org for latest version"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get('https://www.python.org/downloads/')
                
                if response.status_code == 200:
                    # Extract version from page
                    match = re.search(r'Python (\d+\.\d+\.\d+)', response.text)
                    if match:
                        return {
                            'version': match.group(1),
                            'source': 'python.org'
                        }
        except Exception as e:
            logger.warning(f"Failed to check Python version: {e}")
        
        return None
    
    async def _check_node_version(self, tech_name: str) -> Optional[Dict[str, Any]]:
        """Check Node.js for latest version"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get('https://nodejs.org/dist/index.json')
                
                if response.status_code == 200:
                    versions = response.json()
                    if versions:
                        latest = versions[0]
                        return {
                            'version': latest['version'].lstrip('v'),
                            'released_at': latest.get('date'),
                            'source': 'nodejs.org'
                        }
        except Exception as e:
            logger.warning(f"Failed to check Node version: {e}")
        
        return None
    
    async def _check_redis_version(self, tech_name: str) -> Optional[Dict[str, Any]]:
        """Check Redis for latest version"""
        
        return await self._check_github_releases('redis/redis')
    
    async def _check_postgres_version(self, tech_name: str) -> Optional[Dict[str, Any]]:
        """Check PostgreSQL for latest version"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get('https://www.postgresql.org/versions.json')
                
                if response.status_code == 200:
                    data = response.json()
                    # Get latest stable version
                    for version_info in data:
                        if version_info.get('current', False):
                            return {
                                'version': version_info['major'],
                                'released_at': version_info.get('released'),
                                'eol_date': version_info.get('eol'),
                                'source': 'postgresql.org'
                            }
        except Exception as e:
            logger.warning(f"Failed to check PostgreSQL version: {e}")
        
        return None
    
    async def _check_npm_package_version(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Check npm registry for package version"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'https://registry.npmjs.org/{package_name.lower()}/latest'
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'version': data.get('version'),
                        'source': 'npm'
                    }
        except Exception as e:
            logger.warning(f"Failed to check npm package {package_name}: {e}")
        
        return None
    
    async def _check_pypi_package_version(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Check PyPI for package version"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'https://pypi.org/pypi/{package_name.lower()}/json'
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'version': data['info']['version'],
                        'released_at': data['info'].get('release_date'),
                        'source': 'pypi'
                    }
        except Exception as e:
            logger.warning(f"Failed to check PyPI package {package_name}: {e}")
        
        return None
    
    def _extract_version_from_tag(self, tag: str) -> Optional[str]:
        """Extract version number from git tag"""
        
        # Common patterns
        patterns = [
            r'v?(\d+\.\d+\.\d+)',  # v1.2.3 or 1.2.3
            r'v?(\d+\.\d+)',       # v1.2 or 1.2
            r'release-(\d+\.\d+\.\d+)',  # release-1.2.3
            r'(\d+\.\d+\.\d+)-\w+',     # 1.2.3-stable
        ]
        
        for pattern in patterns:
            match = re.search(pattern, tag)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_version_from_text(self, text: str) -> Optional[str]:
        """Extract version number from arbitrary text"""
        
        # Look for semantic version patterns
        match = re.search(r'(\d+\.\d+\.\d+)', text)
        if match:
            return match.group(1)
        
        # Try simpler pattern
        match = re.search(r'(\d+\.\d+)', text)
        if match:
            return match.group(1)
        
        return None
    
    async def _update_version_info(
        self,
        tech_id: str,
        new_version: str,
        old_version: str,
        version_info: Dict[str, Any]
    ):
        """Update version information in database"""
        
        # Get current version record
        current_record = self.db.execute_one(
            """
            SELECT version_previous, version_legacy, current_released
            FROM versions
            WHERE technology_id = %s
            """,
            (tech_id,)
        )
        
        # Shift versions: current -> previous -> legacy
        update_query = """
            UPDATE versions
            SET version_current = %s,
                version_previous = %s,
                version_legacy = %s,
                current_released = %s,
                previous_released = %s,
                legacy_released = %s,
                last_checked = NOW()
            WHERE technology_id = %s
        """
        
        # Parse release date if available
        release_date = None
        if version_info.get('released_at'):
            try:
                release_date = datetime.fromisoformat(
                    version_info['released_at'].replace('Z', '+00:00')
                ).date()
            except:
                release_date = date.today()
        else:
            release_date = date.today()
        
        self.db.execute_query(
            update_query,
            (
                new_version,
                old_version,  # Current becomes previous
                current_record['version_previous'],  # Previous becomes legacy
                release_date,
                current_record['current_released'],
                current_record.get('previous_released'),
                tech_id
            )
        )
        
        logger.info(f"Updated version for technology {tech_id}: {old_version} -> {new_version}")
    
    def _update_next_check(self, tech_id: str):
        """Update next version check time"""
        
        # Calculate next check based on update frequency
        # More frequent for rapidly changing technologies
        next_check = datetime.now() + timedelta(days=TechKnowledgeConfig.VERSION_CHECK_INTERVAL_DAYS)
        
        self.db.execute_query(
            "UPDATE versions SET next_check = %s WHERE technology_id = %s",
            (next_check, tech_id)
        )
    
    def get_version_history(self, technology: str) -> Dict[str, Any]:
        """Get version history for a technology"""
        
        query = """
            SELECT 
                v.*,
                t.name as technology_name,
                t.github_repo,
                COUNT(DISTINCT s.id) as specs_per_version
            FROM versions v
            JOIN technologies t ON v.technology_id = t.id
            LEFT JOIN specifications s ON s.technology_id = t.id
            WHERE t.name = %s
            GROUP BY v.id, t.name, t.github_repo
        """
        
        result = self.db.execute_one(query, (technology,))
        
        if not result:
            return {'error': f'Technology {technology} not found'}
        
        # Calculate time between versions
        time_calculations = {}
        if result['current_released'] and result['previous_released']:
            days_between = (result['current_released'] - result['previous_released']).days
            time_calculations['current_to_previous_days'] = days_between
        
        return {
            'technology': result['technology_name'],
            'versions': {
                'current': {
                    'version': result['version_current'],
                    'released': result['current_released'].isoformat() if result['current_released'] else None,
                    'eol': result['current_eol'].isoformat() if result['current_eol'] else None
                },
                'previous': {
                    'version': result['version_previous'],
                    'released': result['previous_released'].isoformat() if result['previous_released'] else None
                },
                'legacy': {
                    'version': result['version_legacy'],
                    'released': result['legacy_released'].isoformat() if result['legacy_released'] else None
                }
            },
            'update_pattern': {
                'frequency': result['update_frequency'],
                'last_checked': result['last_checked'].isoformat() if result['last_checked'] else None,
                'next_check': result['next_check'].isoformat() if result['next_check'] else None
            },
            'time_calculations': time_calculations,
            'github_repo': result['github_repo']
        }
    
    async def force_version_check(self, technology: str) -> Dict[str, Any]:
        """Force an immediate version check for a technology"""
        
        # Get technology info
        tech = self.db.execute_one(
            """
            SELECT t.*, v.version_current
            FROM technologies t
            JOIN versions v ON t.id = v.technology_id
            WHERE t.name = %s
            """,
            (technology,)
        )
        
        if not tech:
            return {'error': f'Technology {technology} not found'}
        
        # Perform version check
        result = await self._check_technology_version(tech)
        
        return result

