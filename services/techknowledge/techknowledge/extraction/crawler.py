"""
Technical Documentation Crawler
Firecrawl integration for extracting pure technical specifications
"""

import os
import asyncio
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import hashlib
from urllib.parse import urlparse

from .decontaminator import TechnicalDecontaminator
from ..core.models import Technology, Specification, CrawlSource
from ..core.config import TechKnowledgeConfig
from ..core.database import get_db, store_specification


class TechnicalCrawler:
    """Firecrawl integration for technical documentation extraction"""
    
    def __init__(self):
        """Initialize with API configuration"""
        self.api_key = TechKnowledgeConfig.FIRECRAWL_API_KEY
        self.base_url = 'https://api.firecrawl.dev/v0'
        self.decontaminator = TechnicalDecontaminator()
        self.db = get_db()
        
        # HTTP client configuration
        self.timeout = httpx.Timeout(TechKnowledgeConfig.CRAWL_TIMEOUT_SECONDS)
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    async def extract_technical_specs(
        self, 
        url: str, 
        technology: str,
        version: Optional[str] = None,
        component_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract pure technical specifications from a URL
        
        Args:
            url: Documentation URL to crawl
            technology: Technology name (e.g., 'redis', 'postgresql')
            version: Specific version to extract
            component_filter: Filter for specific components ('api', 'config', etc.)
            
        Returns:
            Extracted technical specifications
        """
        # Build extraction prompt for Firecrawl
        extraction_prompt = self._build_extraction_prompt(technology, version, component_filter)
        
        # Configure Firecrawl extraction
        extraction_config = {
            'url': url,
            'mode': 'extract',
            'extractorOptions': {
                'mode': 'llm-extraction',
                'extractionPrompt': extraction_prompt,
                'extractionSchema': self._get_extraction_schema()
            },
            'pageOptions': {
                'onlyMainContent': True,
                'removeNav': True,
                'removeCookieBanners': True
            }
        }
        
        try:
            # Call Firecrawl API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/scrape',
                    headers=self.headers,
                    json=extraction_config
                )
                
                if response.status_code != 200:
                    raise Exception(f"Firecrawl API error: {response.status_code} - {response.text}")
                
                raw_data = response.json()
                
                # Extract and decontaminate content
                if 'data' in raw_data and 'llm_extraction' in raw_data['data']:
                    extracted = raw_data['data']['llm_extraction']
                    cleaned_specs = await self._process_extracted_data(
                        extracted, url, technology, version
                    )
                    
                    return {
                        'url': url,
                        'technology': technology,
                        'version': version,
                        'specifications': cleaned_specs,
                        'extracted_at': datetime.now().isoformat(),
                        'source_type': 'official_docs',
                        'metadata': {
                            'crawl_timestamp': raw_data.get('timestamp'),
                            'content_length': len(str(extracted))
                        }
                    }
                else:
                    # Fallback to markdown content
                    markdown_content = raw_data.get('data', {}).get('markdown', '')
                    if markdown_content:
                        return await self._extract_from_markdown(
                            markdown_content, url, technology, version
                        )
                    
                    raise Exception("No extractable content found")
                    
        except httpx.TimeoutException:
            raise Exception(f"Timeout crawling {url}")
        except Exception as e:
            raise Exception(f"Failed to extract from {url}: {str(e)}")
    
    def _build_extraction_prompt(
        self, 
        technology: str, 
        version: Optional[str],
        component_filter: Optional[str]
    ) -> str:
        """Build extraction prompt for Firecrawl"""
        version_str = f"version {version}" if version else "latest version"
        component_str = f"focusing on {component_filter}" if component_filter else ""
        
        return f"""
        Extract ONLY technical specifications for {technology} {version_str} {component_str}.
        
        EXTRACT ONLY:
        - API endpoints, methods, and signatures
        - Function/method definitions with exact parameters and return types
        - Configuration options with types, defaults, and constraints
        - Type definitions, interfaces, and data structures
        - Protocol specifications and formats
        - Technical limits, constraints, and requirements
        - Error codes and status codes
        - Version compatibility and deprecation notices
        
        EXCLUDE COMPLETELY:
        - Any recommendations or best practices
        - Tutorial content or examples
        - Explanatory text or guides
        - Marketing language
        - Community discussions
        - Personal opinions
        - Comparative statements
        
        Return ONLY verifiable technical facts that can be validated against source code.
        """
    
    def _get_extraction_schema(self) -> Dict[str, Any]:
        """Get JSON schema for structured extraction"""
        return {
            'type': 'object',
            'properties': {
                'apis': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'endpoint': {'type': 'string'},
                            'method': {'type': 'string'},
                            'parameters': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'name': {'type': 'string'},
                                        'type': {'type': 'string'},
                                        'required': {'type': 'boolean'},
                                        'default': {'type': ['string', 'null']}
                                    }
                                }
                            },
                            'returns': {
                                'type': 'object',
                                'properties': {
                                    'type': {'type': 'string'},
                                    'description': {'type': 'string'}
                                }
                            },
                            'errors': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'code': {'type': ['string', 'integer']},
                                        'condition': {'type': 'string'}
                                    }
                                }
                            }
                        }
                    }
                },
                'configurations': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'type': {'type': 'string'},
                            'default': {'type': ['string', 'number', 'boolean', 'null']},
                            'required': {'type': 'boolean'},
                            'constraints': {
                                'type': 'object',
                                'properties': {
                                    'min': {'type': ['number', 'null']},
                                    'max': {'type': ['number', 'null']},
                                    'pattern': {'type': ['string', 'null']},
                                    'enum': {'type': ['array', 'null']}
                                }
                            }
                        }
                    }
                },
                'types': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'kind': {'type': 'string'},  # 'interface', 'class', 'enum', etc.
                            'properties': {'type': 'object'},
                            'methods': {'type': 'array'}
                        }
                    }
                },
                'limits': {
                    'type': 'object',
                    'properties': {
                        'rate_limits': {'type': 'object'},
                        'size_limits': {'type': 'object'},
                        'connection_limits': {'type': 'object'},
                        'performance_characteristics': {'type': 'object'}
                    }
                },
                'protocols': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'version': {'type': 'string'},
                            'format': {'type': 'string'},
                            'specifications': {'type': 'object'}
                        }
                    }
                },
                'version_info': {
                    'type': 'object',
                    'properties': {
                        'current': {'type': 'string'},
                        'supported_versions': {'type': 'array'},
                        'deprecated_features': {'type': 'array'},
                        'breaking_changes': {'type': 'array'}
                    }
                }
            }
        }
    
    async def _process_extracted_data(
        self,
        extracted: Dict[str, Any],
        url: str,
        technology: str,
        version: Optional[str]
    ) -> Dict[str, Any]:
        """Process and decontaminate extracted data"""
        cleaned_data = {}
        
        # Get technology record
        tech = self.db.execute_one(
            "SELECT id FROM technologies WHERE name = %s",
            (technology,)
        )
        
        if not tech:
            raise Exception(f"Technology {technology} not found in registry")
        
        tech_id = tech['id']
        
        # Process each component type
        for component_type, data in extracted.items():
            if isinstance(data, list):
                # Process array of specifications
                cleaned_items = []
                for item in data:
                    if isinstance(item, dict):
                        # Decontaminate any string values
                        cleaned_item = self._decontaminate_dict(item)
                        if cleaned_item:
                            cleaned_items.append(cleaned_item)
                
                if cleaned_items:
                    cleaned_data[component_type] = cleaned_items
                    
                    # Store each specification
                    for item in cleaned_items:
                        await self._store_specification(
                            tech_id, version or 'latest',
                            component_type, item, url
                        )
                        
            elif isinstance(data, dict):
                # Process dictionary specifications
                cleaned_dict = self._decontaminate_dict(data)
                if cleaned_dict:
                    cleaned_data[component_type] = cleaned_dict
                    
                    # Store specification
                    await self._store_specification(
                        tech_id, version or 'latest',
                        component_type, cleaned_dict, url
                    )
        
        return cleaned_data
    
    def _decontaminate_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively decontaminate dictionary values"""
        cleaned = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Decontaminate string values
                result = self.decontaminator.decontaminate(value)
                if result.cleaned_text.strip():
                    cleaned[key] = result.cleaned_text
            elif isinstance(value, dict):
                # Recurse into nested dictionaries
                cleaned_nested = self._decontaminate_dict(value)
                if cleaned_nested:
                    cleaned[key] = cleaned_nested
            elif isinstance(value, list):
                # Process lists
                cleaned_list = []
                for item in value:
                    if isinstance(item, str):
                        result = self.decontaminator.decontaminate(item)
                        if result.cleaned_text.strip():
                            cleaned_list.append(result.cleaned_text)
                    elif isinstance(item, dict):
                        cleaned_item = self._decontaminate_dict(item)
                        if cleaned_item:
                            cleaned_list.append(cleaned_item)
                    else:
                        cleaned_list.append(item)
                if cleaned_list:
                    cleaned[key] = cleaned_list
            else:
                # Keep non-string values as-is (numbers, booleans, etc.)
                cleaned[key] = value
        
        return cleaned
    
    async def _extract_from_markdown(
        self,
        markdown: str,
        url: str,
        technology: str,
        version: Optional[str]
    ) -> Dict[str, Any]:
        """Extract technical specs from markdown content"""
        # Decontaminate the markdown
        result = self.decontaminator.decontaminate(markdown)
        
        # Extract technical sections
        sections = self.decontaminator.extract_technical_sections(result.cleaned_text)
        
        # Structure the extracted data
        specifications = {
            'raw_technical': sections,
            'decontamination_stats': result.stats
        }
        
        return {
            'url': url,
            'technology': technology,
            'version': version,
            'specifications': specifications,
            'extracted_at': datetime.now().isoformat(),
            'source_type': 'markdown_extraction'
        }
    
    async def _store_specification(
        self,
        tech_id: str,
        version: str,
        component_type: str,
        spec_data: Dict[str, Any],
        source_url: str
    ) -> Optional[str]:
        """Store a specification in the database"""
        # Generate component name from spec data
        component_name = (
            spec_data.get('name') or 
            spec_data.get('endpoint') or 
            spec_data.get('method') or
            f"{component_type}_{hashlib.md5(json.dumps(spec_data, sort_keys=True).encode()).hexdigest()[:8]}"
        )
        
        # Calculate checksum
        checksum = self.decontaminator.calculate_checksum(json.dumps(spec_data, sort_keys=True))
        
        # Check if specification already exists
        existing = self.db.execute_one(
            """
            SELECT id FROM specifications 
            WHERE technology_id = %s 
            AND version = %s 
            AND component_type = %s 
            AND component_name = %s
            AND source_checksum = %s
            """,
            (tech_id, version, component_type, component_name, checksum)
        )
        
        if existing:
            # Update last_verified timestamp
            self.db.execute_query(
                "UPDATE specifications SET last_verified = NOW() WHERE id = %s",
                (existing['id'],)
            )
            return str(existing['id'])
        
        # Store new specification
        return store_specification(
            technology_id=tech_id,
            version=version,
            component_type=component_type,
            component_name=component_name,
            specification=spec_data,
            source_url=source_url,
            source_type='official_docs',
            confidence_score=1.0
        )
    
    async def crawl_technology_docs(
        self,
        technology: str,
        base_url: str,
        version: Optional[str] = None,
        max_pages: int = 10
    ) -> Dict[str, Any]:
        """
        Crawl multiple pages of documentation for a technology
        
        Args:
            technology: Technology name
            base_url: Base documentation URL
            version: Specific version to crawl
            max_pages: Maximum number of pages to crawl
            
        Returns:
            Aggregated extraction results
        """
        # Use Firecrawl's crawl endpoint for multi-page extraction
        crawl_config = {
            'url': base_url,
            'mode': 'crawl',
            'crawlerOptions': {
                'maxDepth': TechKnowledgeConfig.MAX_CRAWL_DEPTH,
                'limit': max_pages,
                'includes': ['/api/', '/reference/', '/docs/'],
                'excludes': ['/blog/', '/community/', '/examples/']
            },
            'pageOptions': {
                'onlyMainContent': True
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Start crawl job
                response = await client.post(
                    f'{self.base_url}/crawl',
                    headers=self.headers,
                    json=crawl_config
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to start crawl: {response.text}")
                
                job_data = response.json()
                job_id = job_data.get('jobId')
                
                # Poll for results
                results = await self._poll_crawl_job(client, job_id)
                
                # Process all crawled pages
                all_specs = {}
                for page_data in results:
                    page_url = page_data.get('url', '')
                    if page_url:
                        specs = await self.extract_technical_specs(
                            page_url, technology, version
                        )
                        # Merge specifications
                        for key, value in specs.get('specifications', {}).items():
                            if key not in all_specs:
                                all_specs[key] = []
                            if isinstance(value, list):
                                all_specs[key].extend(value)
                            else:
                                all_specs[key].append(value)
                
                return {
                    'technology': technology,
                    'version': version,
                    'base_url': base_url,
                    'pages_crawled': len(results),
                    'specifications': all_specs,
                    'crawled_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            raise Exception(f"Crawl failed for {technology}: {str(e)}")
    
    async def _poll_crawl_job(
        self, 
        client: httpx.AsyncClient, 
        job_id: str,
        max_wait: int = 300
    ) -> List[Dict[str, Any]]:
        """Poll Firecrawl job status until complete"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < max_wait:
            response = await client.get(
                f'{self.base_url}/crawl/status/{job_id}',
                headers=self.headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get job status: {response.text}")
            
            status_data = response.json()
            status = status_data.get('status')
            
            if status == 'completed':
                return status_data.get('data', [])
            elif status == 'failed':
                raise Exception(f"Crawl job failed: {status_data.get('error')}")
            
            # Wait before next poll
            await asyncio.sleep(2)
        
        raise Exception(f"Crawl job timeout after {max_wait} seconds")
