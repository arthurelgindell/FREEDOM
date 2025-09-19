"""
GitHub Source Validator
Validates documentation against actual source code
Pure technical verification - no opinions
"""

import os
import re
import httpx
import base64
import asyncio
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime
import json
from urllib.parse import urlparse

from ..core.database import get_db
from ..core.config import TechKnowledgeConfig
from ..core.models import GitHubValidation, Specification


class GitHubSourceValidator:
    """Validate documentation against actual source code"""
    
    def __init__(self):
        """Initialize with GitHub API configuration"""
        self.github_token = TechKnowledgeConfig.GITHUB_TOKEN
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'TechKnowledge-Validator'
        }
        if self.github_token:
            self.headers['Authorization'] = f'token {self.github_token}'
        
        self.db = get_db()
        self.api_base = 'https://api.github.com'
    
    async def validate_against_source(
        self,
        technology: str,
        repo_url: str,
        specification: Dict[str, Any],
        spec_id: str
    ) -> Dict[str, Any]:
        """
        Compare documentation claims against actual source code
        
        Args:
            technology: Technology name
            repo_url: GitHub repository URL
            specification: Technical specification to validate
            spec_id: Specification ID in database
            
        Returns:
            Validation results with match status
        """
        # Parse repository information
        owner, repo = self._parse_repo_url(repo_url)
        
        validations = []
        
        # Validate different types of specifications
        if 'apis' in specification:
            for api in specification.get('apis', []):
                validation = await self._validate_api_in_source(
                    owner, repo, api, spec_id
                )
                validations.append(validation)
        
        if 'configurations' in specification:
            for config in specification.get('configurations', []):
                validation = await self._validate_config_in_source(
                    owner, repo, config, spec_id
                )
                validations.append(validation)
        
        if 'types' in specification:
            for type_def in specification.get('types', []):
                validation = await self._validate_type_in_source(
                    owner, repo, type_def, spec_id
                )
                validations.append(validation)
        
        # Calculate summary
        total = len(validations)
        matched = sum(1 for v in validations if v.get('matches', False))
        
        return {
            'technology': technology,
            'repository': f"{owner}/{repo}",
            'validations': validations,
            'summary': {
                'total_validated': total,
                'matched': matched,
                'mismatched': total - matched,
                'match_percentage': (matched / total * 100) if total > 0 else 0
            },
            'validated_at': datetime.now().isoformat()
        }
    
    def _parse_repo_url(self, repo_url: str) -> Tuple[str, str]:
        """Extract owner and repo name from GitHub URL"""
        # Handle various GitHub URL formats
        if 'github.com' in repo_url:
            parts = repo_url.replace('https://', '').replace('http://', '')
            parts = parts.replace('github.com/', '').strip('/')
            parts = parts.split('/')
            return parts[0], parts[1].replace('.git', '')
        else:
            # Assume format: owner/repo
            parts = repo_url.split('/')
            return parts[0], parts[1]
    
    async def _validate_api_in_source(
        self, 
        owner: str, 
        repo: str, 
        api: Dict[str, Any],
        spec_id: str
    ) -> Dict[str, Any]:
        """Search for API definition in source code"""
        
        # Extract searchable elements
        endpoint = api.get('endpoint', '')
        method_name = api.get('method', api.get('name', ''))
        
        # Build search query
        search_terms = []
        if endpoint:
            # Extract route pattern
            route = endpoint.replace('{', '').replace('}', '')
            search_terms.append(f'"{route}"')
        if method_name:
            search_terms.append(method_name)
        
        if not search_terms:
            return self._create_validation_result(
                'api', endpoint or method_name, False, 
                "No searchable identifiers", spec_id
            )
        
        # Search in repository
        search_results = await self._search_code(owner, repo, ' '.join(search_terms))
        
        if search_results['total_count'] > 0:
            # Found matches - validate details
            file_validations = []
            
            for item in search_results['items'][:3]:  # Check top 3 results
                file_content = await self._get_file_content(
                    owner, repo, item['path']
                )
                
                if file_content:
                    validation = self._validate_api_details(
                        api, file_content, item['path']
                    )
                    file_validations.append(validation)
            
            # Determine overall match
            matches = any(v['matches'] for v in file_validations)
            
            return self._create_validation_result(
                'api',
                endpoint or method_name,
                matches,
                file_validations,
                spec_id,
                search_results['items'][0]['sha'] if matches else None,
                search_results['items'][0]['path'] if matches else None
            )
        
        return self._create_validation_result(
            'api', endpoint or method_name, False, 
            "Not found in source", spec_id
        )
    
    async def _validate_config_in_source(
        self,
        owner: str,
        repo: str,
        config: Dict[str, Any],
        spec_id: str
    ) -> Dict[str, Any]:
        """Validate configuration option in source"""
        
        config_name = config.get('name', '')
        if not config_name:
            return self._create_validation_result(
                'config', 'unnamed', False, 
                "No config name specified", spec_id
            )
        
        # Search for configuration definition
        search_results = await self._search_code(
            owner, repo, f'"{config_name}"'
        )
        
        if search_results['total_count'] > 0:
            # Check if default value matches
            for item in search_results['items'][:3]:
                file_content = await self._get_file_content(
                    owner, repo, item['path']
                )
                
                if file_content:
                    validation = self._validate_config_details(
                        config, file_content, item['path']
                    )
                    
                    if validation['matches']:
                        return self._create_validation_result(
                            'config',
                            config_name,
                            True,
                            validation,
                            spec_id,
                            item['sha'],
                            item['path']
                        )
            
            # Found but details don't match
            return self._create_validation_result(
                'config',
                config_name,
                False,
                "Found but details mismatch",
                spec_id
            )
        
        return self._create_validation_result(
            'config', config_name, False, 
            "Not found in source", spec_id
        )
    
    async def _validate_type_in_source(
        self,
        owner: str,
        repo: str,
        type_def: Dict[str, Any],
        spec_id: str
    ) -> Dict[str, Any]:
        """Validate type definition in source"""
        
        type_name = type_def.get('name', '')
        if not type_name:
            return self._create_validation_result(
                'type', 'unnamed', False, 
                "No type name specified", spec_id
            )
        
        # Search for type definition
        kind = type_def.get('kind', 'type')
        search_query = f"{kind} {type_name}" if kind else type_name
        
        search_results = await self._search_code(owner, repo, search_query)
        
        if search_results['total_count'] > 0:
            # Validate type structure
            for item in search_results['items'][:3]:
                file_content = await self._get_file_content(
                    owner, repo, item['path']
                )
                
                if file_content:
                    validation = self._validate_type_details(
                        type_def, file_content, item['path']
                    )
                    
                    if validation['matches']:
                        return self._create_validation_result(
                            'type',
                            type_name,
                            True,
                            validation,
                            spec_id,
                            item['sha'],
                            item['path']
                        )
            
            return self._create_validation_result(
                'type',
                type_name,
                False,
                "Structure mismatch",
                spec_id
            )
        
        return self._create_validation_result(
            'type', type_name, False, 
            "Not found in source", spec_id
        )
    
    async def _search_code(
        self, 
        owner: str, 
        repo: str, 
        query: str
    ) -> Dict[str, Any]:
        """Search for code in GitHub repository"""
        
        search_query = f"{query} repo:{owner}/{repo}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.api_base}/search/code',
                params={'q': search_query, 'per_page': 10},
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                # Rate limited
                await asyncio.sleep(60)  # Wait a minute
                return {'total_count': 0, 'items': []}
            else:
                return {'total_count': 0, 'items': []}
    
    async def _get_file_content(
        self, 
        owner: str, 
        repo: str, 
        path: str
    ) -> Optional[str]:
        """Get file content from GitHub"""
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.api_base}/repos/{owner}/{repo}/contents/{path}',
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('content'):
                    # Decode base64 content
                    content = base64.b64decode(data['content']).decode('utf-8')
                    return content
            
            return None
    
    def _validate_api_details(
        self, 
        api_spec: Dict[str, Any], 
        source_content: str,
        file_path: str
    ) -> Dict[str, Any]:
        """Validate API details against source code"""
        
        validations = {
            'file': file_path,
            'matches': True,
            'details': {}
        }
        
        # Check parameters
        if 'parameters' in api_spec:
            for param in api_spec['parameters']:
                param_name = param.get('name', '')
                param_type = param.get('type', '')
                
                # Look for parameter in source
                param_pattern = rf'\b{param_name}\b.*?:\s*{param_type}'
                if not re.search(param_pattern, source_content, re.IGNORECASE):
                    validations['matches'] = False
                    validations['details'][f'param_{param_name}'] = 'Not found'
                else:
                    validations['details'][f'param_{param_name}'] = 'Found'
        
        # Check return type
        if 'returns' in api_spec:
            return_type = api_spec['returns'].get('type', '')
            if return_type:
                return_pattern = rf'returns?.*?{return_type}|:\s*{return_type}\s*[{{]?'
                if not re.search(return_pattern, source_content, re.IGNORECASE):
                    validations['matches'] = False
                    validations['details']['return_type'] = 'Mismatch'
        
        return validations
    
    def _validate_config_details(
        self,
        config_spec: Dict[str, Any],
        source_content: str,
        file_path: str
    ) -> Dict[str, Any]:
        """Validate configuration details against source"""
        
        config_name = config_spec.get('name', '')
        default_value = config_spec.get('default')
        config_type = config_spec.get('type', '')
        
        validations = {
            'file': file_path,
            'matches': False,
            'details': {}
        }
        
        # Look for configuration definition
        config_patterns = [
            rf'{config_name}\s*[=:]\s*{re.escape(str(default_value))}' if default_value else None,
            rf'"{config_name}".*?default.*?{re.escape(str(default_value))}' if default_value else None,
            rf'{config_name}.*?{config_type}' if config_type else None,
        ]
        
        for pattern in config_patterns:
            if pattern and re.search(pattern, source_content, re.IGNORECASE):
                validations['matches'] = True
                validations['details']['pattern'] = pattern
                break
        
        return validations
    
    def _validate_type_details(
        self,
        type_spec: Dict[str, Any],
        source_content: str,
        file_path: str
    ) -> Dict[str, Any]:
        """Validate type definition against source"""
        
        type_name = type_spec.get('name', '')
        type_kind = type_spec.get('kind', '')
        properties = type_spec.get('properties', {})
        
        validations = {
            'file': file_path,
            'matches': False,
            'details': {}
        }
        
        # Look for type definition
        type_patterns = [
            rf'{type_kind}\s+{type_name}',
            rf'type\s+{type_name}',
            rf'interface\s+{type_name}',
            rf'class\s+{type_name}',
            rf'struct\s+{type_name}'
        ]
        
        type_found = False
        for pattern in type_patterns:
            if re.search(pattern, source_content, re.IGNORECASE):
                type_found = True
                validations['details']['definition'] = 'Found'
                break
        
        if type_found and properties:
            # Validate properties
            props_found = 0
            for prop_name in properties.keys():
                if re.search(rf'\b{prop_name}\b', source_content):
                    props_found += 1
            
            prop_percentage = (props_found / len(properties)) * 100
            validations['details']['properties_match'] = f"{prop_percentage:.0f}%"
            validations['matches'] = prop_percentage >= 80  # 80% threshold
        else:
            validations['matches'] = type_found
        
        return validations
    
    def _create_validation_result(
        self,
        validation_type: str,
        name: str,
        matches: bool,
        details: Any,
        spec_id: str,
        commit_sha: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create standardized validation result"""
        
        result = {
            'type': validation_type,
            'name': name,
            'matches': matches,
            'details': details,
            'specification_id': spec_id
        }
        
        if commit_sha:
            result['commit_sha'] = commit_sha
        if file_path:
            result['file_path'] = file_path
        
        # Store in database
        if file_path and commit_sha:
            self._store_validation(
                spec_id, validation_type, matches,
                details, commit_sha, file_path
            )
        
        return result
    
    def _store_validation(
        self,
        spec_id: str,
        validation_type: str,
        matches: bool,
        details: Any,
        commit_sha: str,
        file_path: str
    ):
        """Store validation result in database"""
        
        query = """
            INSERT INTO github_validations 
            (specification_id, github_url, file_path, commit_sha,
             validation_type, matches, discrepancies)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        github_url = f"https://github.com/{file_path}"
        discrepancies = None if matches else json.dumps(details)
        
        self.db.execute_query(
            query,
            (spec_id, github_url, file_path, commit_sha,
             validation_type, matches, discrepancies)
        )
    
    async def validate_technology(
        self,
        technology_name: str,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate all specifications for a technology"""
        
        # Get technology info
        tech_query = """
            SELECT t.id, t.name, t.github_repo
            FROM technologies t
            WHERE t.name = %s
        """
        
        tech = self.db.execute_one(tech_query, (technology_name,))
        if not tech or not tech['github_repo']:
            return {
                'error': f"Technology {technology_name} not found or no GitHub repo"
            }
        
        # Get specifications to validate
        spec_query = """
            SELECT s.id, s.component_type, s.component_name, s.specification
            FROM specifications s
            WHERE s.technology_id = %s
            AND s.verification_status != 'failed'
        """
        
        params = [tech['id']]
        if version:
            spec_query += " AND s.version = %s"
            params.append(version)
        
        specs = self.db.execute_query(spec_query, tuple(params))
        
        # Validate each specification
        all_validations = []
        for spec in specs:
            validation = await self.validate_against_source(
                technology_name,
                tech['github_repo'],
                spec['specification'],
                str(spec['id'])
            )
            all_validations.append(validation)
        
        # Update verification status
        for validation in all_validations:
            if validation['summary']['match_percentage'] >= 80:
                status = 'verified'
            elif validation['summary']['match_percentage'] >= 50:
                status = 'partial'
            else:
                status = 'failed'
            
            self.db.execute_query(
                """
                UPDATE specifications 
                SET verification_status = %s, last_verified = NOW()
                WHERE id = %s
                """,
                (status, validation['specification_id'])
            )
        
        return {
            'technology': technology_name,
            'version': version,
            'total_specifications': len(specs),
            'validations': all_validations,
            'summary': {
                'verified': sum(1 for v in all_validations 
                              if v['summary']['match_percentage'] >= 80),
                'partial': sum(1 for v in all_validations 
                             if 50 <= v['summary']['match_percentage'] < 80),
                'failed': sum(1 for v in all_validations 
                            if v['summary']['match_percentage'] < 50)
            }
        }