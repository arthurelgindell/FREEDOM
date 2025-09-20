#!/usr/bin/env bash
# ChatGPT Pro Desktop Audit (macOS)
# Verifies app version, local feature flags, and macOS permission grants.
# Author: Operator
# Usage: bash cgpt_pro_audit.sh [-v|--verbose]

set -euo pipefail

VERBOSE=0
if [[ "${1:-}" == "-v" || "${1:-}" == "--verbose" ]]; then VERBOSE=1; fi

log() { printf "%s\n" "$*"; }
vlog() { [[ $VERBOSE -eq 1 ]] && printf "%s\n" "$*" || true; }

divider() { printf "%s\n" "------------------------------------------------------------------"; }

ok()   { printf "✅ %s\n" "$*"; }
warn() { printf "⚠️  %s\n" "$*"; }
err()  { printf "❌ %s\n" "$*"; }

# 1) Locate ChatGPT app
APP_PATHS=(
  "/Applications/ChatGPT.app"
  "$HOME/Applications/ChatGPT.app"
)

APP=""
for p in "${APP_PATHS[@]}"; do
  if [[ -d "$p" ]]; then APP="$p"; break; fi
done

divider
log "1) App Discovery"
if [[ -z "$APP" ]]; then
  err "ChatGPT.app not found in /Applications or ~/Applications"
  log "   If installed elsewhere, set APP env var: APP=/path/to/ChatGPT.app bash $0"
  exit 2
else
  ok "Found ChatGPT app at: $APP"
fi

# 2) Read version & build
divider
log "2) Version Check"
INFO_PLIST="$APP/Contents/Info.plist"
if [[ ! -f "$INFO_PLIST" ]]; then
  err "Info.plist not found at expected path: $INFO_PLIST"
  exit 3
fi

VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$INFO_PLIST" 2>/dev/null || true)"
BUILD="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$INFO_PLIST" 2>/dev/null || true)"

if [[ -z "$VERSION" ]]; then
  VERSION="$(defaults read "$APP/Contents/Info" CFBundleShortVersionString 2>/dev/null || true)"
fi
if [[ -z "$BUILD" ]]; then
  BUILD="$(defaults read "$APP/Contents/Info" CFBundleVersion 2>/dev/null || true)"
fi

if [[ -n "$VERSION" ]]; then ok "App version: $VERSION"; else warn "Could not read CFBundleShortVersionString"; fi
if [[ -n "$BUILD" ]];   then ok "App build:   $BUILD";   else warn "Could not read CFBundleVersion"; fi

# Minimum reference for latest Pro features (heuristic; adjust if needed)
MIN_VER="1.2025.250"

vercmp () {
  # lexical compare for dotted numeric strings of equal length segments
  # pads shorter one with zeros to 4 segments
  IFS='.' read -r -a A <<< "$1"
  IFS='.' read -r -a B <<< "$2"
  for i in 0 1 2 3; do
    a="${A[i]:-0}"; b="${B[i]:-0}"
    if ((10#$a > 10#$b)); then echo 1; return; fi
    if ((10#$a < 10#$b)); then echo -1; return; fi
  done
  echo 0
}

if [[ -n "$VERSION" ]]; then
  cmp="$(vercmp "$VERSION" "$MIN_VER")"
  if [[ "$cmp" -ge 0 ]]; then
    ok "Version meets or exceeds reference $MIN_VER"
  else
    warn "Version appears older than $MIN_VER — some features may be hidden"
  fi
fi

# 3) Cache / feature flags
divider
log "3) Feature Flags & Cache Scan"

CACHE_DIR="$HOME/Library/Application Support/com.openai.chat"
PREF_PLIST="$HOME/Library/Preferences/com.openai.chat.plist"

if [[ -d "$CACHE_DIR" ]]; then
  ok "Found cache dir: $CACHE_DIR"
else
  warn "Cache dir not found: $CACHE_DIR (will be created after login or first run)"
fi

if [[ -f "$PREF_PLIST" ]]; then
  ok "Found preferences plist: $PREF_PLIST"
else
  warn "Preferences plist not found (not always present)"
fi

# Candidate flag files (heuristic names; we’ll scan broadly)
CANDIDATES=()
if [[ -d "$CACHE_DIR" ]]; then
  while IFS= read -r -d '' f; do CANDIDATES+=("$f"); done < <(find "$CACHE_DIR" -type f \( -name "*.json" -o -name "*.plist" -o -name "*.bin" \) -print0 | head -n 2000 | tr '\n' '\0')
fi

declare -A FOUND
KEYWORDS=(
  "codex" "agent" "work_with_apps" "sora" "video" "features" "entitlement" "flag" "gpt-5" "pro_reasoning"
)

if [[ ${#CANDIDATES[@]} -gt 0 ]]; then
  for kw in "${KEYWORDS[@]}"; do
    if LC_ALL=C grep -Iir --exclude-dir=.git -m 1 -E "\"?$kw\"?" "${CACHE_DIR}" >/dev/null 2>&1; then
      FOUND["$kw"]="yes"
    else
      FOUND["$kw"]="no"
    fi
  done
  ok "Scanned cache for feature keywords."
else
  warn "No candidate files to scan in cache."
fi

log "   Feature keyword hits (heuristic):"
for kw in "${KEYWORDS[@]}"; do
  if [[ "${FOUND[$kw]:-no}" == "yes" ]]; then ok "   $kw: present somewhere in cache"; else warn "   $kw: not detected in cache"; fi
done

# 4) macOS TCC permissions (Accessibility, Screen Recording, Full Disk Access)
divider
log "4) macOS Permissions (TCC database)"
TCC_DB="$HOME/Library/Application Support/com.apple.TCC/TCC.db"
BUNDLE_ID="com.openai.chat"

if ! command -v sqlite3 >/dev/null 2>&1; then
  warn "sqlite3 not found; cannot query TCC. Install Command Line Tools or Homebrew sqlite."
else
  if [[ -r "$TCC_DB" ]]; then
    vlog "Querying $TCC_DB for $BUNDLE_ID"
    RESULT="$(sqlite3 "$TCC_DB" "SELECT service,allowed,auth_value,prompt_count FROM access WHERE client='$BUNDLE_ID' ORDER BY service;" || true)"
    if [[ -n "$RESULT" ]]; then
      ok "TCC entries for $BUNDLE_ID:"
      printf "%s\n" "$RESULT" | awk -F'|' 'BEGIN { printf "   %-28s %-7s %-10s %-12s\n", "service","allowed","auth_value","prompt_count"; print "   -----------------------------------------------------------" } { printf "   %-28s %-7s %-10s %-12s\n", $1,$2,$3,$4 }'
    else
      warn "No TCC rows found for $BUNDLE_ID in user DB. This can be normal before first prompt/approval."
    fi
  else
    warn "Cannot read $TCC_DB (likely requires Full Disk Access). Grant Terminal Full Disk Access to enable this check."
  fi
fi

log "   Services of interest:"
log "     - kTCCServiceAccessibility      → UI control (Work With Apps, IDE overlay)"
log "     - kTCCServiceScreenCapture      → screen recording (overlays/previews)"
log "     - kTCCServiceSystemPolicyAllFiles → Full Disk Access (broad file ops)"
log "     - Files & Folders per-app dirs will not appear as single service rows"

# 5) Summary
divider
log "5) Summary"

STATUS_OK=1

if [[ -n "$VERSION" ]]; then
  cmp="$(vercmp "$VERSION" "$MIN_VER")"
  if [[ "$cmp" -ge 0 ]]; then
    log "Version:          ✅ $VERSION (>= $MIN_VER)"
  else
    log "Version:          ⚠️  $VERSION (< $MIN_VER)"
    STATUS_OK=0
  fi
else
  log "Version:          ❌ unknown"
  STATUS_OK=0
fi

if [[ -d "$CACHE_DIR" ]]; then
  log "Cache dir:        ✅ $CACHE_DIR"
else
  log "Cache dir:        ❌ missing"
  STATUS_OK=0
fi

if [[ "${FOUND[codex]:-no}" == "yes" ]]; then
  log "Codex flag:       ✅ detected (heuristic)"
else
  log "Codex flag:       ⚠️  not detected (may still be server-side only)"
fi

if [[ "${FOUND[sora]:-no}" == "yes" ]]; then
  log "Sora flag:        ✅ detected (heuristic)"
else
  log "Sora flag:        ⚠️  not detected (may still be server-side only)"
fi

if [[ "${FOUND[work_with_apps]:-no}" == "yes" ]]; then
  log "Work-With-Apps:   ✅ detected (heuristic)"
else
  log "Work-With-Apps:   ⚠️  not detected (may still be server-side only)"
fi

divider
log "Exit codes: 0=PASS (version ok; cache present); 1=PASS with warnings; 2+=FAIL"
divider

# Exit policy
if [[ $STATUS_OK -eq 1 ]]; then
  exit 0
else
  exit 1
fi
