"""
TechKnowledge Data Models
Pure technical specifications - no opinions
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from uuid import UUID
import json


@dataclass
class Technology:
    """Technology registry entry"""
    id: Optional[UUID] = None
    name: str = ""
    category: str = ""  # 'language', 'framework', 'database', 'tool', 'protocol'
    official_url: str = ""
    github_repo: Optional[str] = None
    documentation_url: Optional[str] = None
    api_spec_url: Optional[str] = None
    release_feed_url: Optional[str] = None
    crawl_config: Optional[Dict[str, Any]] = None
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': str(self.id) if self.id else None,
            'name': self.name,
            'category': self.category,
            'official_url': self.official_url,
            'github_repo': self.github_repo,
            'documentation_url': self.documentation_url,
            'api_spec_url': self.api_spec_url,
            'release_feed_url': self.release_feed_url,
            'crawl_config': json.dumps(self.crawl_config) if self.crawl_config else None,
            'active': self.active
        }


@dataclass
class Version:
    """Version tracking with 3-version window"""
    id: Optional[UUID] = None
    technology_id: UUID = None
    version_current: str = ""
    version_previous: Optional[str] = None
    version_legacy: Optional[str] = None
    current_released: Optional[date] = None
    previous_released: Optional[date] = None
    legacy_released: Optional[date] = None
    current_eol: Optional[date] = None
    update_frequency: Optional[str] = None  # PostgreSQL interval
    last_checked: datetime = field(default_factory=datetime.now)
    next_check: datetime = field(default_factory=datetime.now)


@dataclass
class Specification:
    """Pure technical specification"""
    id: Optional[UUID] = None
    technology_id: UUID = None
    version: str = ""
    component_type: str = ""  # 'api', 'config', 'types', 'limits', 'protocols'
    component_name: str = ""
    specification: Dict[str, Any] = field(default_factory=dict)
    source_url: str = ""
    source_type: str = ""  # 'official_docs', 'github_source', 'api_spec', 'rfc'
    source_checksum: Optional[str] = None
    confidence_score: float = 1.0
    extracted_at: datetime = field(default_factory=datetime.now)
    last_verified: datetime = field(default_factory=datetime.now)
    verification_status: str = 'unverified'  # 'verified', 'failed', 'outdated'
    
    def is_valid(self) -> bool:
        """Check if specification is valid and verified"""
        return (
            self.verification_status in ('verified', 'unverified') and
            self.confidence_score >= 0.8 and
            bool(self.specification)
        )


@dataclass
class CrawlSource:
    """Documentation source for crawling"""
    id: Optional[UUID] = None
    technology_id: UUID = None
    url: str = ""
    url_pattern: Optional[str] = None
    crawl_frequency: str = '7 days'  # PostgreSQL interval
    last_crawled: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = 0
    extracted_specs_count: int = 0
    decontamination_stats: Optional[Dict[str, Any]] = None
    active: bool = True


@dataclass
class GitHubValidation:
    """Source code validation result"""
    id: Optional[UUID] = None
    specification_id: UUID = None
    github_url: str = ""
    file_path: str = ""
    commit_sha: str = ""
    validation_type: Optional[str] = None  # 'source_match', 'implementation_example', 'config_default'
    matches: Optional[bool] = None
    discrepancies: Optional[Dict[str, Any]] = None
    validated_at: datetime = field(default_factory=datetime.now)


@dataclass
class UsageTracking:
    """Track specification usage for aging"""
    id: Optional[UUID] = None
    specification_id: UUID = None
    accessed_by: str = ""  # Agent or system name
    access_type: str = ""  # 'query', 'reference', 'implementation'
    access_context: Optional[str] = None
    accessed_at: datetime = field(default_factory=datetime.now)
    was_useful: Optional[bool] = None


@dataclass
class DecontaminationLog:
    """Audit trail for content cleaning"""
    id: Optional[UUID] = None
    crawl_source_id: UUID = None
    original_size: int = 0
    cleaned_size: int = 0
    removed_patterns: Dict[str, Any] = field(default_factory=dict)
    extracted_technical: Dict[str, Any] = field(default_factory=dict)
    contamination_score: float = 0.0
    processed_at: datetime = field(default_factory=datetime.now)
    
    @property
    def reduction_percentage(self) -> float:
        """Calculate size reduction percentage"""
        if self.original_size == 0:
            return 0.0
        return ((self.original_size - self.cleaned_size) / self.original_size) * 100


@dataclass
class TechnicalQuery:
    """Query request for technical specifications"""
    technology: str
    component: Optional[str] = None
    version: str = 'current'  # 'current', 'previous', 'legacy', or specific version
    include_validations: bool = False
    include_usage_stats: bool = False
    
    def cache_key(self) -> str:
        """Generate cache key for this query"""
        return f"{self.technology}:{self.version}:{self.component or 'all'}"


@dataclass
class TechnicalResponse:
    """Response containing pure technical data"""
    technology: str
    version: str
    component: Optional[str]
    specifications: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    query_time_ms: float
    
    def to_json(self) -> str:
        """Convert to JSON for API response"""
        return json.dumps({
            'technology': self.technology,
            'version': self.version,
            'component': self.component,
            'specifications': self.specifications,
            'metadata': self.metadata,
            'query_time_ms': self.query_time_ms
        }, default=str)
