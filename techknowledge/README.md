# TechKnowledge System

Pure technical knowledge system for FREEDOM. Maintains absolute, uncontaminated technical truth about all technologies used in the project.

## Core Principles

1. **Technical Purity**: Extracts ONLY technical facts - no opinions, recommendations, or human perspectives
2. **Source Authority**: Trusts only official docs, source code, and API specs
3. **Version Intelligence**: Tracks current + 2 previous versions with auto-update detection
4. **Auto-Refresh**: 12-month aging with usage-based refresh triggers
5. **GitHub Validation**: Cross-references documentation with actual source code

## System Architecture

```
techknowledge/
├── core/               # Database connection, models, configuration
├── extraction/         # Crawling and decontamination
├── github/            # Source code validation
├── management/        # Aging, refresh, version tracking
├── api/               # Query interface for AI agents
└── tests/             # Test suite
```

## Key Components

### Technical Decontaminator
Removes all human behavioral elements from documentation:
- Opinion indicators (should, recommend, prefer)
- Personal experiences and judgments
- Tutorial/guide language
- Marketing content

Preserves only:
- API definitions and signatures
- Configuration parameters
- Type definitions
- Technical constraints
- Error codes
- Performance characteristics

### Database Schema
PostgreSQL database with:
- Technologies registry
- Version tracking (3-version window)
- Pure technical specifications
- GitHub validation results
- Usage tracking for intelligent aging
- Decontamination audit logs

### Query API
Sub-100ms response interface for AI agents:
```python
response = query_api.get_specification(
    technology='redis',
    component='api',
    version='current'
)
```

## Setup

1. **Database Setup**
```bash
# Run setup script
python techknowledge/setup_techknowledge.py
```

2. **Environment Configuration**
Create `.env` file:
```
FIRECRAWL_API_KEY=your_key_here
GITHUB_TOKEN=optional_for_rate_limits
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
```

3. **Install Dependencies**
```bash
pip install psycopg2-binary httpx sqlalchemy python-dotenv feedparser
```

## Usage

### Query Technical Specifications
```python
from techknowledge.api.query import TechKnowledgeQuery

query = TechKnowledgeQuery()
specs = query.get_specification('postgresql', component='config')
```

### Validate Against Source
```python
from techknowledge.github.source_validator import GitHubSourceValidator

validator = GitHubSourceValidator()
result = await validator.validate_technology('redis')
```

### Check Aging Status
```python
from techknowledge.management.aging import AgingManager

aging = AgingManager()
report = aging.get_aging_report()
```

## Testing

Run test suite:
```bash
python scripts/test_techknowledge.py
```

## Performance Targets

- Query response: < 100ms
- Decontamination: > 70% technical content
- Validation accuracy: > 80% source match
- Storage efficiency: Automatic deduplication

## Integration Points

- **Truth Engine**: Validates all implementations
- **AI Council**: Primary consumer via Query API
- **Analytics**: Tracks performance metrics

## Maintenance

The system self-maintains through:
- Automatic version checking (daily)
- Usage-based refresh triggers
- 12-month aging lifecycle
- Storage optimization (deduplication)

## Success Criteria

1. **Technical Purity**: Zero human opinion in stored specifications
2. **Source Verification**: All specs validated against GitHub source
3. **Version Tracking**: Current + 2 previous versions maintained
4. **Performance**: Sub-100ms query response time
5. **Automation**: Self-updating when new versions detected

