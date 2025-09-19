# TechKnowledge System - Complete Functional Workflow

## Overview

The TechKnowledge system is a comprehensive technical documentation and specification management platform that automatically crawls, processes, validates, and serves technical knowledge for software technologies.

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│   Processing    │───▶│    Storage      │
│                 │    │   Pipeline      │    │                 │
│ • GitHub APIs   │    │ • Crawlers      │    │ • PostgreSQL    │
│ • Web Scraping  │    │ • Extractors    │    │ • Specifications│
│ • Manual Input  │    │ • Validators    │    │ • Technologies  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Integration   │◀───│      APIs       │◀───│   Management    │
│                 │    │                 │    │                 │
│ • Claude AI     │    │ • Query API     │    │ • Version       │
│ • FREEDOM       │    │ • REST Endpoints│    │ • Validation    │
│ • External Apps │    │ • Search        │    │ • Aging/Refresh │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## STEP-BY-STEP FUNCTIONAL WORKFLOW

### PHASE 1: TECHNOLOGY INITIALIZATION

#### Step 1.1: Technology Registration
```bash
# Method 1: Manual CLI registration
python3 techknowledge/cli.py add-tech --name "fastapi" --url "https://fastapi.tiangolo.com"

# Method 2: Database direct insert
psql -d techknowledge -c "INSERT INTO technologies (name, description) VALUES ('fastapi', 'Modern Python web framework');"
```

**Database Action:**
- Creates entry in `technologies` table
- Assigns unique ID and timestamps
- Initializes processing status

#### Step 1.2: Source Configuration
```sql
-- Automatic crawl source creation for known patterns
INSERT INTO crawl_sources (technology_id, source_type, source_url, priority) VALUES
(tech_id, 'github_api', 'https://api.github.com/repos/tiangolo/fastapi', 1),
(tech_id, 'docs_website', 'https://fastapi.tiangolo.com/docs/', 2),
(tech_id, 'github_readme', 'https://github.com/tiangolo/fastapi', 3);
```

**Result:** Technology ready for processing with multiple source endpoints.

---

### PHASE 2: AUTOMATED CRAWLING & EXTRACTION

#### Step 2.1: Pipeline Orchestration
```python
# Triggered by CLI or scheduled task
pipeline = TechKnowledgePipeline()
await pipeline.process_technology("fastapi")
```

**Internal Process:**
1. **Source Discovery**: Identifies all configured crawl sources
2. **Priority Scheduling**: Orders sources by priority and last_crawled timestamp
3. **Rate Limiting**: Respects API limits and crawl delays
4. **Parallel Execution**: Processes multiple sources concurrently

#### Step 2.2: Content Extraction
```python
# For each source type:
extractors = {
    'github_api': GitHubAPIExtractor(),
    'docs_website': WebDocExtractor(),
    'github_readme': ReadmeExtractor()
}

for source in crawl_sources:
    extractor = extractors[source.source_type]
    content = await extractor.extract(source.source_url)
```

**Extraction Types:**
- **GitHub API**: README, releases, issues, package.json, setup.py
- **Documentation Sites**: Installation guides, API docs, tutorials
- **Package Repositories**: PyPI, npm, cargo metadata

#### Step 2.3: Specification Parsing
```python
# AI-powered specification extraction
specifications = await ai_extractor.parse_content(
    content=raw_content,
    technology="fastapi",
    extraction_patterns=[
        "installation_commands",
        "configuration_examples",
        "api_endpoints",
        "code_samples"
    ]
)
```

**AI Processing:**
- Uses local LM Studio models (Qwen preferred)
- Extracts structured specifications from unstructured content
- Categorizes by component_type: api, command, config, code
- Assigns confidence scores based on source reliability

---

### PHASE 3: VALIDATION & QUALITY ASSURANCE

#### Step 3.1: Multi-Layer Validation
```python
validators = [
    SyntaxValidator(),      # Code syntax validation
    LinkValidator(),        # URL accessibility checks
    SchemaValidator(),      # JSON/YAML structure validation
    CrossReferenceValidator() # Internal consistency checks
]

for spec in specifications:
    validation_results = await run_validators(spec, validators)
    spec.confidence_score *= validation_results.confidence_multiplier
```

**Validation Checks:**
- **Syntax**: Code blocks must be valid for their language
- **Links**: All URLs must be accessible (with retry logic)
- **Schema**: JSON configurations must validate against known schemas
- **Cross-Reference**: Commands must exist in official documentation

#### Step 3.2: Decontamination Process
```sql
-- Log suspicious or invalid content
INSERT INTO decontamination_log (
    technology_id, issue_type, description, severity, resolved
) VALUES (
    tech_id, 'broken_link', 'Installation URL returns 404', 'medium', false
);
```

**Quality Filters:**
- Removes deprecated commands and configurations
- Flags potentially harmful code patterns
- Validates against known security best practices
- Cross-checks with official source truth

---

### PHASE 4: DATABASE STORAGE & INDEXING

#### Step 4.1: Specification Storage
```sql
INSERT INTO specifications (
    technology_id,
    component_type,     -- 'api', 'command', 'config', 'code'
    component_name,     -- 'install', 'configuration', 'start_server'
    specification,      -- JSONB structured data
    confidence_score,   -- 0.0 to 1.0 reliability score
    source_url,         -- Original source reference
    extracted_at,       -- Processing timestamp
    version            -- Technology version compatibility
) VALUES (...);
```

#### Step 4.2: Version Management
```python
# Automatic version tracking
version_tracker = VersionTracker()
await version_tracker.track_changes(
    technology_id=tech_id,
    old_specs=previous_specifications,
    new_specs=current_specifications
)
```

**Version Control Features:**
- Tracks specification changes over time
- Maintains backward compatibility information
- Flags breaking changes in new versions
- Preserves historical specification data

---

### PHASE 5: REAL-TIME ACCESS & QUERYING

#### Step 5.1: API Query Interface
```python
# Direct database query
query_api = TechKnowledgeQuery()
results = await query_api.search_specifications(
    technology="fastapi",
    component_type="command",
    search_term="install"
)

# Unified knowledge search (via FREEDOM)
unified_service = UnifiedKnowledgeService()
results = await unified_service.unified_search(
    query="fastapi installation",
    search_type="technical"
)
```

#### Step 5.2: REST API Access
```bash
# Get technology overview
curl http://localhost:8000/api/v1/unified/technology-context/fastapi

# Search specifications
curl "http://localhost:8000/api/v1/unified/search/fastapi%20install?search_type=technical"

# Get insights
curl http://localhost:8000/api/v1/unified/insights/fastapi
```

---

## OPERATIONAL PROCEDURES

### Daily Operations

#### 1. Automated Processing
```bash
# Scheduled via cron or systemd timer
0 2 * * * cd /Volumes/DATA/FREEDOM && python3 techknowledge/cli.py process-all
```

#### 2. Manual Technology Update
```bash
# Force refresh of specific technology
python3 techknowledge/cli.py process-tech --name "fastapi" --force-refresh

# Add new technology
python3 techknowledge/cli.py add-tech --name "pydantic" --url "https://docs.pydantic.dev"
```

#### 3. System Health Check
```bash
# Database status
python3 techknowledge/cli.py status

# Validation report
python3 techknowledge/cli.py validate-all

# Performance metrics
python3 techknowledge/cli.py metrics
```

### Maintenance Operations

#### 1. Data Quality Management
```sql
-- Find low-confidence specifications
SELECT t.name, s.component_type, s.confidence_score
FROM specifications s
JOIN technologies t ON s.technology_id = t.id
WHERE s.confidence_score < 0.7
ORDER BY s.confidence_score;

-- Clean up old versions
DELETE FROM specifications
WHERE extracted_at < NOW() - INTERVAL '90 days'
AND confidence_score < 0.5;
```

#### 2. Source Management
```bash
# Add new crawl source
python3 techknowledge/cli.py add-source --tech "fastapi" --type "docs_website" --url "https://fastapi.tiangolo.com/tutorial/"

# Disable broken source
python3 techknowledge/cli.py disable-source --url "https://old-domain.com/docs"
```

#### 3. Performance Optimization
```sql
-- Rebuild indexes
REINDEX TABLE specifications;

-- Update statistics
ANALYZE specifications;

-- Clean up logs
DELETE FROM decontamination_log WHERE created_at < NOW() - INTERVAL '30 days';
```

---

## INTEGRATION PATTERNS

### With FREEDOM Platform
```python
# Automatic integration via unified knowledge service
unified_service = UnifiedKnowledgeService()

# Technology context combines both systems
context = await unified_service.get_technology_context("crush")
# Returns: Claude conversations + TechKnowledge specifications

# Intelligent search routing
results = await unified_service.unified_search("python web framework", "technical")
# Returns: Prioritized technical specifications
```

### With External Systems
```python
# API integration example
import requests

# Get all FastAPI specifications
response = requests.get("http://localhost:8000/api/v1/unified/technology-context/fastapi")
fastapi_data = response.json()

# Use in external documentation systems
for spec in fastapi_data["tech_specifications"]["command"]:
    external_system.add_command_help(spec["component_name"], spec["specification"])
```

### With Claude AI Sessions
```python
# Session initialization with TechKnowledge context
session_context = await unified_service.generate_session_context()
# Provides: Recent conversations + Available technical knowledge

# Context-aware assistance
if "fastapi" in user_query:
    tech_context = await unified_service.get_technology_context("fastapi")
    ai_response = generate_response_with_context(user_query, tech_context)
```

---

## SUCCESS METRICS & MONITORING

### Key Performance Indicators
- **Coverage**: 22 technologies, 665 specifications across 4 component types
- **Quality**: Average confidence score > 0.8 for production specs
- **Freshness**: 95% of specs updated within 30 days
- **Availability**: 99.9% uptime for query API
- **Integration**: Seamless access via FREEDOM unified search

### Monitoring Commands
```bash
# System status
python3 intelligence/knowledge/unified_knowledge_service.py --stats

# Search performance test
python3 intelligence/knowledge/unified_knowledge_service.py --search "fastapi" --search-type technical

# Database health
psql -d techknowledge -c "SELECT COUNT(*) as total_specs, AVG(confidence_score) as avg_confidence FROM specifications;"
```

---

## TROUBLESHOOTING GUIDE

### Common Issues

#### 1. Low Confidence Scores
**Symptom**: Specifications have confidence < 0.6
**Solution**:
```bash
# Re-validate specific technology
python3 techknowledge/cli.py validate-tech --name "fastapi"

# Check source availability
python3 techknowledge/cli.py check-sources --tech "fastapi"
```

#### 2. Outdated Information
**Symptom**: Specifications reference old versions
**Solution**:
```bash
# Force refresh from sources
python3 techknowledge/cli.py process-tech --name "fastapi" --force-refresh

# Update version tracking
python3 techknowledge/cli.py update-versions --tech "fastapi"
```

#### 3. Missing Technologies
**Symptom**: Technology not found in search
**Solution**:
```bash
# Check if technology exists
psql -d techknowledge -c "SELECT * FROM technologies WHERE name ILIKE '%fastapi%';"

# Add if missing
python3 techknowledge/cli.py add-tech --name "fastapi" --auto-discover
```

---

**TechKnowledge System Status: 🔧 FULLY OPERATIONAL**
*Providing persistent, validated technical knowledge to the FREEDOM Platform ecosystem.*