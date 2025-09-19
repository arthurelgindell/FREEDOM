# FREEDOM Platform Runbooks

## Overview
This directory contains comprehensive operational documentation for the FREEDOM platform. These runbooks follow the core principle: **"If it doesn't run, it doesn't exist"** - every procedure is executable with no hidden steps.

## Available Runbooks

### 1. [Cold Start Runbook](cold-start-runbook.md)
**Complete setup from clean environment**
- Clone → compose up → ingest → query workflow
- Environment variable setup and API key configuration
- Service startup verification and troubleshooting
- **Target Time**: 15-30 minutes
- **Use Case**: New deployments, fresh installations, disaster recovery

### 2. [Rollback Runbook](rollback-runbook.md)
**Emergency rollback to graveyard/pre-reset state**
- Service backup and restore procedures
- Data migration and recovery steps
- Emergency procedures for service failures
- **Target Time**: 10-20 minutes for rollback
- **Use Case**: Critical failures, security incidents, deployment failures

### 3. [MLX Models Management](mlx-models-management.md)
**Complete MLX model lifecycle management**
- Adding new MLX models to the system
- Model switching and performance optimization
- Apple Silicon optimization procedures
- Model health monitoring and maintenance
- **Target Audience**: ML Engineers, Operations team
- **Use Case**: Model updates, performance tuning, troubleshooting

### 4. [Operations Manual](operations-manual.md)
**Daily operational procedures and monitoring**
- Daily health check procedures
- Performance monitoring and alerting
- Log analysis and troubleshooting
- Scaling and capacity planning
- **Target Audience**: Operations team, SREs
- **Use Case**: Day-to-day operations, monitoring, maintenance

## Quick Reference

### Emergency Commands
```bash
# Full system restart
cd /Volumes/DATA/FREEDOM && docker-compose down && docker-compose up -d

# Health check all services
cd /Volumes/DATA/FREEDOM && make health

# Emergency rollback
cd /Volumes/DATA/FREEDOM && git checkout graveyard/pre-reset && docker-compose up -d
```

### Daily Operations
```bash
# Morning health check
cd /Volumes/DATA/FREEDOM && make health

# Check logs for errors
cd /Volumes/DATA/FREEDOM && docker-compose logs --since=24h | grep -i error

# Performance verification
cd /Volumes/DATA/FREEDOM && make verify
```

## Runbook Usage Guidelines

### Before Using Any Runbook
1. **Verify prerequisites** - Check system requirements
2. **Understand the impact** - Know what the procedure will change
3. **Have rollback plan** - Know how to undo changes if needed
4. **Test in development** - When possible, test procedures first

### During Runbook Execution
1. **Follow exactly** - Don't skip steps or make assumptions
2. **Verify each step** - Check success criteria before continuing
3. **Document deviations** - Note any issues or modifications needed
4. **Monitor continuously** - Watch for unexpected behavior

### After Runbook Completion
1. **Verify success criteria** - Ensure all objectives met
2. **Run health checks** - Confirm system stability
3. **Update documentation** - Note any improvements needed
4. **Communicate status** - Inform relevant stakeholders

## Service Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Castle GUI    │    │   API Gateway   │    │  MLX Server     │
│  (Port 3000)    │◄──►│  (Port 8080)    │◄──►│  (Port 8001)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        │
                       ┌─────────────────┐               │
                       │  KB Service     │               │
                       │  (Port 8000)    │               │
                       └─────────────────┘               │
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PostgreSQL    │    │  Model Storage  │
                       │  (Port 5432)    │    │    /models/     │
                       └─────────────────┘    └─────────────────┘
```

## Key Directories and Files

### Configuration
- `/Volumes/DATA/FREEDOM/docker-compose.yml` - Main service configuration
- `/Volumes/DATA/FREEDOM/.env` - Environment variables
- `/Volumes/DATA/FREEDOM/Makefile` - Development commands

### Services
- `/Volumes/DATA/FREEDOM/services/api/` - API Gateway service
- `/Volumes/DATA/FREEDOM/services/kb/` - Knowledge Base service
- `/Volumes/DATA/FREEDOM/services/mlx/` - MLX Model service

### Data
- `/Volumes/DATA/FREEDOM/models/` - MLX model storage
- `/Volumes/DATA/FREEDOM/logs/` - Application logs
- `postgres_data` volume - Database data

### Scripts
- `/Volumes/DATA/FREEDOM/scripts/` - Operational automation scripts
- `/Volumes/DATA/FREEDOM/tests/` - Test and verification scripts

## Health Check Commands

### Quick Health Check
```bash
cd /Volumes/DATA/FREEDOM
make health
```

### Detailed Health Check
```bash
cd /Volumes/DATA/FREEDOM

# Service status
docker-compose ps

# Individual service health
curl -f http://localhost:8080/health  # API Gateway
curl -f http://localhost:8000/health  # KB Service
curl -f http://localhost:8001/health  # MLX Server
curl -f http://localhost:3000         # Castle GUI

# Database health
docker-compose exec postgres pg_isready -U freedom -d freedom_kb
```

### Performance Verification
```bash
cd /Volumes/DATA/FREEDOM

# Run comprehensive tests
make verify

# Quick performance test
python -c "
import time, requests
start = time.time()
response = requests.post('http://localhost:8001/v1/chat/completions',
  json={'messages': [{'role': 'user', 'content': 'Health check'}], 'max_tokens': 10})
print(f'MLX response time: {time.time()-start:.2f}s')
print(f'Status: {response.status_code}')
"
```

## Troubleshooting Decision Tree

```
System Issue?
├── Services not responding?
│   ├── Check: docker-compose ps
│   ├── Action: docker-compose restart [service]
│   └── Escalate: Use Rollback Runbook
├── Slow performance?
│   ├── Check: MLX Models Management Runbook
│   ├── Action: Performance tuning procedures
│   └── Monitor: Operations Manual procedures
├── Data issues?
│   ├── Check: Database connectivity
│   ├── Action: Rollback Runbook recovery procedures
│   └── Restore: From backup if needed
└── New deployment?
    ├── Use: Cold Start Runbook
    ├── Verify: All success criteria
    └── Monitor: Operations Manual procedures
```

## Success Metrics

### System Health
- ✅ All 5 services showing "healthy" status
- ✅ Response times <3 seconds average
- ✅ MLX inference >30 tokens/sec
- ✅ Database queries <100ms average
- ✅ 99.9% uptime target

### Operational Excellence
- ✅ Zero-downtime deployments
- ✅ Automated health monitoring
- ✅ Proactive alerting
- ✅ Complete audit trail
- ✅ Rapid incident response

## Contact and Escalation

### Runbook Issues
- Update runbooks based on operational experience
- Document any deviations or improvements needed
- Test procedures regularly to ensure accuracy

### System Issues
1. **Level 1**: Use appropriate runbook procedures
2. **Level 2**: Escalate to Rollback Runbook if runbook fails
3. **Level 3**: Emergency shutdown and manual recovery

---

**Documentation Version**: 1.0
**Last Updated**: 2025-09-19
**Covers Platform Version**: All FREEDOM platform releases
**Tested On**: Apple Silicon macOS, Docker Desktop 4.x
**Runbook Completion Rate**: 100% (4/4 runbooks implemented)