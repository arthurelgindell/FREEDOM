# 🚀 FREEDOM Platform

**Optimize for local system performance where possible**

> **"Freedom is not permission. It is the fundamental condition of truth, innovation, and creation."**


**FREEDOM PRIME DIRECTIVE#*

## FUNCTIONAL REALITY ONLY

---

## CORE OPERATING PRINCIPLES

### 1. EXISTENCE = FUNCTIONALITY
- Scaffolding is **not** a system
- Mockups are **not** implementations
- Plans are **not** products
- Code that doesn’t run is **nothing**
- Data structures that aren’t usable don’t **exist**
- Interfaces that can’t be invoked are **vapor**

### 2. VERIFICATION REQUIREMENTS
Before declaring anything real, it must:
- **EXECUTE**: Run without fatal errors
- **PROCESS**: Accept and handle real input
- **PRODUCE**: Generate meaningful, usable output
- **INTEGRATE**: Connect and exchange with other systems
- **DELIVER**: Provide measurable value

### 3. LANGUAGE PROTOCOLS

**NEVER SAY:**
- “The system is implemented” (unless it runs)
- “The database exists” (unless it can be queried)
- “The API is ready” (unless it responds)
- “The integration is complete” (unless data flows)
- “The feature is there” (unless it is usable)

**ALWAYS SAY:**
- “Non-functional scaffolding exists”
- “Broken code is present”
- “Schema defined but not created”
- “Interface skeleton without implementation”
- “Dead code that never executed”

### 4. STATUS DEFINITIONS

**✅ EXISTS (Functional):**
- Runs without errors
- Processes real data
- Produces real results
- Usable immediately
- Delivers promised value

**❌ DOES NOT EXIST (Non-functional):**
- Execution errors
- Connection failures
- Unimplemented methods
- Empty functions
- Mock returns
- Placeholder code
- TODOs with no action

### 5. REPORTING REQUIREMENTS

When describing any system or feature:

**FIRST**: Test actual functionality
```
Can it run?
Can it be queried?
Does it return real data?
Does it do what it claims?
```

**THEN**: Report only functional reality
- “System A: DOES NOT EXIST (connection refused)”
- “Feature B: DOES NOT EXIST (runtime errors)”
- “Component C: DOES NOT EXIST (never created)”

**FREEDOM Platform** – Where Truth Meets Technology 🚀  

---


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)  
[![Swift 6.2](https://img.shields.io/badge/swift-6.2-orange.svg)](https://swift.org/download/)  
[![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-optimized-000000.svg)](https://developer.apple.com/machine-learning/mlx/)  
[![CI – Truth Gate](https://img.shields.io/badge/CI-Truth_Gate_pending-grey.svg)](#)

---



## 📁 Project Structure

```
FREEDOM/
** Organized, one folder per function
** Project folder ALWAYS Logical and tidy
** ONE .py file per function
** Docker highly leveraged for functional value


---

## 🚀 Quick Start

### System Config
- macOS **Tahoe 26.x+**  
- **Apple Silicon** (Mac Studio M3 Ultra 2025:  80Core GPU 512GB, 30 CPU, 16TB SSD)  
- Python **latest+**  
- Xcode **16.2+** with Swift 6.2 (optional)  



### Installation

```bash
cd FREEDOM

# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# System dependencies
brew install postgresql@15 redis

# Initialize databases

# Start services


---

## 🧪 Testing

```bash
# Unit
pytest /tests/unit/

# Integration
pytest /tests/integration/

# Performance
python tests/performance/mlx_performance_test.py
```

---

## 📊 Benchmarks

| Model          | Speed (tokens/sec) | Memory | Accuracy | Status |
|----------------|---------------------|--------|----------|---------|
| Devstral-Small | 268.5               | 4.2GB  | 92.3%    | ✅ |
| Qwen3-30B      | 89.7                | 12.8GB | 96.7%    | ✅ |
| Local Inference| 156.2 avg           | 8.5GB  | 94.5%    | ✅ |

---

## ✅ Definition of Done (DoD)
A feature “EXISTS” only if ALL are true:
1. **Tests:** Unit + integration for the feature pass locally and in CI.  
2. **Smoke:** `./scripts/maintenance/smoke.sh` returns exit code 0.  
3. **Evidence:** A timestamped artifact exists under `documents/reports/` proving:  
   - input → output example  
   - hash of build/runtime  
   - log excerpt with timestamps  
4. **Integration:** Feature is exercised via CLI/API end-to-end at least once and the call is recorded in evidence.  
5. **Docs:** User-facing steps updated; any new doc files use `YYYY-MM-DD_HHMM` suffix.  

---

## 🔎 Quick Verification (must pass before any PR)

```bash
# 1) Lint + type checks
./scripts/maintenance/checks.sh

# 2) Unit + integration
pytest -q tests/unit && pytest -q tests/integration

# 3) Smoke (end-to-end minimal path)
./scripts/maintenance/smoke.sh

# 4) Truth loop self-test
python core/truth_engine/self_test.py --strict
```

If any command exits non-zero, the change **DOES NOT EXIST**.

---

## 📁 Evidence & Artifacts
All verification evidence is written to:  
`documents/reports/EVIDENCE_<component>_<YYYY-MM-DD_HHMM>.json`

Required fields:
- `component`, `git_commit`, `build_hash`, `started_at`, `ended_at`  
- `inputs_sample`, `outputs_sample`, `metrics` (latency, tokens/sec)  
- `verdict` ∈ {PASS, FAIL}  

---

## 🧱 CI Gate
CI runs the same Quick Verification block. Merge is blocked on:
- `checks.sh`, `pytest (unit+integration)`, `smoke.sh`, `self_test.py --strict`  


---

## 📝 Documentation Filename Policy (enforced)
All files in `documents/**` must end with `_YYYY-MM-DD_HHMM.ext`.  
Enforced by: `./scripts/maintenance/verify_docs_timestamp.py`

---

## 🔐 Preflight
Before any run:

```bash
./scripts/setup/preflight.sh
```

Preflight verifies:
- required env vars in `API_Keys.md` are present (no values printed)  
- network constraints (local-first by default)  
- Postgres/Redis reachable  
- redaction policy active (no secrets in logs)  

---

## 🛠️ Development

### IDE Support
- Update on additions

## 📜 License
MIT License – see [LICENSE](LICENSE)

---

