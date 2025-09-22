# GitHub Context Transfer for FREEDOM Claude Instances
Date: 2025-09-22
Repository: github-freedom:arthurelgindell/FREEDOM.git

## Critical GitHub Configuration

### Repository Setup
- **Remote**: `git@github-freedom:arthurelgindell/FREEDOM.git`
- **Default Branch**: main
- **SSH Config**: Using `github-freedom` host alias (custom SSH key)
- **Authentication**: Personal Access Token (PAT) configured

### GitHub Actions Workflow Deployed

#### Workflow File: `.github/workflows/claude-session-persistence.yml`
**Status**: ✅ Active and tested (2 successful pushes)
**Purpose**: Automatic session state capture on every push

#### Key Configuration:
```yaml
name: Claude Session Persistence
on:
  push:
    branches: [main, feature/*, session/*]
  pull_request:
    branches: [main]
  workflow_dispatch:  # Manual trigger enabled

jobs:
  capture-session:
    runs-on: macos-latest  # Uses macOS runner for compatibility
```

#### What It Does:
1. Triggers automatically on push to specified branches
2. Captures git state (commits, changes, status)
3. Documents expected services configuration
4. Creates recovery scripts
5. Generates session artifacts
6. Uploads artifacts with 30-day retention

### GitHub Integration Attempts

#### `/install-github-app` Command Issue
- **Attempted**: Using Claude's built-in GitHub App installation
- **Result**: Failed with "Couldn't install GitHub App: Failed to access repository"
- **Resolution**: Using Personal Access Token (PAT) instead of OAuth
- **Status**: PAT approach working successfully

### Personal Access Token (PAT) Configuration
- **Setup Method**: Long-term token created manually
- **Scope**: Repository access for FREEDOM project
- **Usage**: Embedded in git remote configuration
- **Alternative**: Can be added as GitHub Secret for Actions

### GitHub CLI (gh) Status
- **Installed**: Yes (via Homebrew presumably)
- **Authenticated**: No (not required for current workflow)
- **Command to authenticate** (if needed):
```bash
gh auth login
# OR with token:
gh auth login --with-token < token-file.txt
```

### Recent GitHub Activity

#### Commits Pushed (Session Context):
1. **a78c1943**: "Add comprehensive session persistence system"
   - Created GitHub Actions workflow
   - Added recovery and save scripts
   - Full documentation

2. **5637194b**: "Document session persistence system in README"
   - Updated README with new section
   - Added test report
   - Created session checkpoint

#### Workflow Runs:
- **First Run**: Triggered by session persistence implementation
- **Second Run**: Triggered by documentation update
- **Status Check**: https://github.com/arthurelgindell/FREEDOM/actions

### Platform Considerations

#### Runner Selection Rationale:
- **Why macOS-latest**: Matches local development environment
- **Why not ubuntu-latest**:
  - No MLX support
  - Path incompatibilities (/Volumes/DATA/)
  - Docker Desktop differences
- **Cost**: macOS runners are 10x more expensive than Ubuntu
- **Alternative**: Self-hosted runners possible but not configured

#### Docker Container Option (Considered but Rejected):
- **Reason**: Would add complexity to existing 10+ container setup
- **Current Approach**: Direct workflow on GitHub runners
- **Benefit**: Simpler, no additional container management

### How to Use in New Claude Instance

#### 1. Verify GitHub Connection:
```bash
cd /Volumes/DATA/FREEDOM
git remote -v
# Should show: github-freedom:arthurelgindell/FREEDOM.git
```

#### 2. Check Workflow Status:
```bash
# If gh CLI authenticated:
gh run list --workflow=claude-session-persistence.yml

# Otherwise visit:
# https://github.com/arthurelgindell/FREEDOM/actions
```

#### 3. Download Latest Artifacts:
```bash
# If gh authenticated:
gh run download [run-id]

# Artifacts contain:
# - .freedom/sessions/* (state files)
# - .github/session-artifacts/* (summaries)
```

#### 4. Push Changes to Trigger Workflow:
```bash
git add -A
git commit -m "Your message"
git push origin main
# Workflow triggers automatically
```

### Important Notes

1. **No OAuth Required**: PAT setup bypasses OAuth complexity
2. **Automatic Triggers**: Every push creates recovery artifacts
3. **Manual Trigger Available**: Can run workflow from GitHub UI
4. **Artifact Retention**: 30 days (configurable in workflow)
5. **Branch Strategy**: Works on main, feature/*, session/* branches

### Recovery Integration

The GitHub Actions workflow works in conjunction with local scripts:
- **Push**: Triggers cloud backup automatically
- **Local Save**: `./freedom-save` (can push to trigger workflow)
- **Recovery**: `./freedom-recover` (can download artifacts if gh authenticated)

### Security Considerations

- **Never commit tokens**: Use GitHub Secrets or SSH keys
- **PAT is configured**: Via SSH alias, not exposed in repo
- **Workflow uses**: `${{ secrets.GITHUB_TOKEN }}` (default token)
- **For API access**: Would need to add PAT as secret: `GH_PAT` or `PERSONAL_ACCESS_TOKEN`

### Summary for New Instance

When starting a new Claude Code instance for FREEDOM:

1. **GitHub Actions are already deployed** - No setup needed
2. **Workflows trigger automatically** - On every push
3. **Artifacts are available** - 30-day history on GitHub
4. **PAT is configured** - Via SSH, working successfully
5. **Recovery is automated** - Just run `./freedom-recover`

The GitHub infrastructure is fully operational and requires no additional configuration unless you want to:
- Authenticate gh CLI for artifact downloads
- Modify workflow triggers or retention
- Add self-hosted runners for local access

---
*This GitHub context ensures new Claude instances understand the complete CI/CD setup and can immediately leverage the cloud-based persistence system.*