"""
TechKnowledge Configuration
Technical facts only - zero behavioral guidance
"""

import os
from pathlib import Path
from typing import List, Set
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


class TechKnowledgeConfig:
    """Configuration for pure technical knowledge extraction"""
    
    # Database Configuration
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', '5432'))
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    
    # API Keys
    FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY', '')
    FIRECRAWL_API_URL = 'https://api.firecrawl.dev/v0'  # Firecrawl API endpoint
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')  # Optional for rate limits
    
    # Crawl Sources - Official documentation only
    OFFICIAL_DOCS_DOMAINS = os.getenv(
        'OFFICIAL_DOCS_DOMAINS',
        'docs.python.org,redis.io,postgresql.org,reactjs.org,nodejs.org'
    ).split(',')
    
    GITHUB_REPOS = os.getenv(
        'GITHUB_REPOS',
        'redis/redis,postgres/postgres,facebook/react,nodejs/node'
    ).split(',')
    
    # Decontamination Settings
    CONTAMINATION_THRESHOLD = float(os.getenv('CONTAMINATION_THRESHOLD', '0.4'))
    TECHNICAL_MINIMUM = float(os.getenv('TECHNICAL_MINIMUM', '0.5'))
    
    # Aging Settings (in days)
    HOT_TIER_DAYS = int(os.getenv('HOT_TIER_DAYS', '90'))
    WARM_TIER_DAYS = int(os.getenv('WARM_TIER_DAYS', '180'))
    COLD_TIER_DAYS = int(os.getenv('COLD_TIER_DAYS', '365'))
    PURGE_AFTER_DAYS = int(os.getenv('PURGE_AFTER_DAYS', '365'))
    
    # Version Management
    VERSIONS_TO_TRACK = 3  # Current + 2 previous
    VERSION_CHECK_INTERVAL_DAYS = 1
    
    # Component Types - Technical only
    VALID_COMPONENT_TYPES = {
        'api',        # API endpoints and methods
        'config',     # Configuration parameters
        'types',      # Type definitions and interfaces
        'limits',     # Technical limitations and constraints
        'protocols'   # Protocol specifications
    }
    
    # Source Types - Authoritative only
    VALID_SOURCE_TYPES = {
        'official_docs',   # Official documentation
        'github_source',   # Actual source code
        'api_spec',        # OpenAPI/Swagger specs
        'rfc'              # RFC specifications
    }
    
    # Technology Categories
    VALID_CATEGORIES = {
        'language',
        'framework',
        'database',
        'tool',
        'protocol'
    }
    
    # Extraction Settings
    MAX_CRAWL_DEPTH = 3
    CRAWL_TIMEOUT_SECONDS = 30
    MAX_RETRIES = 3
    
    # Performance Settings
    BATCH_SIZE = 100
    MAX_PARALLEL_CRAWLS = 5
    QUERY_TIMEOUT_MS = 100  # Target sub-100ms responses
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        
        if not cls.FIRECRAWL_API_KEY:
            errors.append("FIRECRAWL_API_KEY not set")
        
        if cls.CONTAMINATION_THRESHOLD >= 1.0:
            errors.append("CONTAMINATION_THRESHOLD must be less than 1.0")
        
        if cls.TECHNICAL_MINIMUM <= 0:
            errors.append("TECHNICAL_MINIMUM must be greater than 0")
        
        if cls.HOT_TIER_DAYS >= cls.WARM_TIER_DAYS:
            errors.append("HOT_TIER_DAYS must be less than WARM_TIER_DAYS")
        
        return errors


# Contamination patterns to remove
HUMAN_CONTAMINATION_PATTERNS = [
    # Opinion indicators
    r'\b(should|shouldn\'t|recommend|prefer|suggest|best practice)\b',
    r'\b(better|worse|easier|harder|simpler|complex)\b',
    r'\b(beautiful|ugly|clean|dirty|elegant|messy)\b',
    
    # Personal pronouns and experience
    r'\b(I|we|our|my|you should|you might want)\b',
    r'\b(in my experience|I think|I believe|IMHO|IMO)\b',
    
    # Comparative judgments
    r'\b(more efficient than|less efficient|faster than|slower than)\b',
    r'\b(preferred over|instead of using|avoid using)\b',
    
    # Tutorial/guide language
    r'\b(let\'s|we\'ll|you\'ll|going to show you)\b',
    r'\b(in this tutorial|in this guide|we will learn)\b',
    
    # Recommendation language
    r'\b(it\'s recommended|we recommend|you may want to)\b',
    r'\b(consider using|might be useful|could be helpful)\b',
    
    # Marketing/promotional
    r'\b(powerful|revolutionary|game-changing|cutting-edge)\b',
    r'\b(seamless|effortless|intuitive|user-friendly)\b'
]

# Technical patterns to preserve
TECHNICAL_PRESERVATION_PATTERNS = [
    # API/Function definitions
    r'(function|method|class|interface|type|struct)\s+\w+',
    r'(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+/[\w/\-{}]+',

    # Configuration and parameters
    r'(parameter|argument|option|flag):\s*[\w\-]+',
    r'(required|optional|default:\s*[\w\d\-\.]+)',
    r'(type:\s*[\w\[\]<>]+|returns:\s*[\w\[\]<>]+)',

    # Version and compatibility
    r'(version|v?)\d+\.?\d*\.?\d*[\w\-]*',
    r'(deprecated|removed in|added in|since)\s+v?\d+',
    r'(breaking change|backwards compatible)',

    # Constraints and limits
    r'(minimum|maximum|limit|constraint):\s*\d+[\w]*',
    r'(must be|cannot be|only accepts|requires)',
    r'(valid values|accepted formats|allowed range)',

    # Technical specifications
    r'(implements|extends|inherits from|conforms to)',
    r'(protocol|interface|abstract|concrete)',
    r'(synchronous|asynchronous|blocking|non-blocking)',

    # Error codes and states
    r'(error code|status code|exit code):\s*\d+',
    r'(throws|raises|returns error|fails with)',

    # Performance metrics
    r'(latency|throughput|bandwidth|memory usage):\s*\d+[\w]*',
    r'(time complexity|space complexity):\s*O\([^\)]+\)',

    # AI/ML Framework patterns
    r'\b(framework|library|toolkit|platform|engine)\b',
    r'\b(agent|agents|model|models|workflow|workflows)\b',
    r'\b(stateful|stateless|persistent|durable|execution)\b',
    r'\b(orchestration|deployment|infrastructure|scalable)\b',
    r'\b(memory|debugging|observability|monitoring)\b',
    r'\b(integration|component|ecosystem|prebuilt)\b',

    # Programming language constructs
    r'\b(def|class|import|from|return)\s+\w+',
    r'\b(pip|npm|yarn|cargo|composer)\s+(install|add|update)',
    r'(install|setup|configure|initialize)\s+(via|using|with)',
    r'```\w*\s*\n.*?\n```',  # Code blocks
    r'`[^`]+`',  # Inline code

    # Package and module references
    r'[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*',  # module.submodule
    r'"[a-zA-Z0-9\-_:\.\/]+"\s*[:,]',  # String configuration values
    r"'[a-zA-Z0-9\-_:\.\/]+'\s*[:,]",  # String configuration values

    # Technical architecture terms
    r'\b(API|REST|GraphQL|JSON|YAML|XML|HTTP|HTTPS|WebSocket)\b',
    r'\b(database|storage|cache|queue|stream|pipeline)\b',
    r'\b(authentication|authorization|security|encryption)\b',
    r'\b(container|docker|kubernetes|deployment|scaling)\b',

    # Documentation structure indicators
    r'^#+\s+\w+',  # Markdown headers
    r'^\s*[-*+]\s+\*\*\w+\*\*:',  # Bullet points with bold labels
    r'^\s*\d+\.\s+',  # Numbered lists
    r'Example\s+(of|usage|implementation):',  # Example indicators
]
