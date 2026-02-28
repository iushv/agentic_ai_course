#!/usr/bin/env bash
# validate.sh — Pre-publish checks for the agentic-ai-skills package.
# Usage: ./validate.sh                    # Full validation (all targets)
#        ./validate.sh --tools cursor     # Only check Cursor target + canonical skills
#        ./validate.sh --tools all        # Same as no flag (default)
# Exit 0 = all checks pass. Exit 1 = issues found.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
ERRORS=0
WARNINGS=0
CHECK_NUM=0
TOTAL_CHECKS=9

# --- Parse CLI flags ---
TOOLS="all"
while [ $# -gt 0 ]; do
  case "$1" in
    --tools) TOOLS="$2"; shift 2 ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

tool_enabled() {
  [ "$TOOLS" = "all" ] && return 0
  echo ",$TOOLS," | grep -q ",$1,"
}

# Root detection (same logic as sync-rules.sh)
PROJECT_ROOT="$(git -C "$ROOT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "")"
if [ -z "$PROJECT_ROOT" ] || [ "$PROJECT_ROOT" = "$ROOT_DIR" ]; then
  PROJECT_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
fi

pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1" >&2; ERRORS=$((ERRORS + 1)); }
warn() { echo "  WARN: $1"; WARNINGS=$((WARNINGS + 1)); }

echo "=== Agentic AI Skills — Validation ==="
echo ""

# --- Check 1: AGENTS.md line count ≤ 180 ---
CHECK_NUM=$((CHECK_NUM + 1))
echo "[$CHECK_NUM/$TOTAL_CHECKS] AGENTS.md line count"
AGENTS_LINES="$(wc -l < "$ROOT_DIR/AGENTS.md" | tr -d ' ')"
if [ "$AGENTS_LINES" -le 180 ]; then
  pass "AGENTS.md is $AGENTS_LINES lines (limit: 180)"
else
  fail "AGENTS.md is $AGENTS_LINES lines (limit: 180)"
fi

# --- Check 2: SKILL.md line counts ≤ 500 ---
CHECK_NUM=$((CHECK_NUM + 1))
echo "[$CHECK_NUM/$TOTAL_CHECKS] SKILL.md line counts"
while IFS= read -r skill_file; do
  SKILL_LINES="$(wc -l < "$skill_file" | tr -d ' ')"
  SKILL_NAME="$(basename "$(dirname "$skill_file")")"
  if [ "$SKILL_LINES" -le 500 ]; then
    pass "$SKILL_NAME/SKILL.md is $SKILL_LINES lines (limit: 500)"
  else
    fail "$SKILL_NAME/SKILL.md is $SKILL_LINES lines (limit: 500)"
  fi
done < <(find "$ROOT_DIR/skills" -name "SKILL.md" -type f 2>/dev/null)

# --- Check 3: SKILL.md frontmatter validation ---
CHECK_NUM=$((CHECK_NUM + 1))
echo "[$CHECK_NUM/$TOTAL_CHECKS] SKILL.md frontmatter validation"
while IFS= read -r skill_file; do
  SKILL_NAME="$(basename "$(dirname "$skill_file")")"

  if [ "$(head -1 "$skill_file")" != "---" ]; then
    fail "$SKILL_NAME/SKILL.md does not start with --- (no frontmatter)"
    continue
  fi

  FRONTMATTER="$(sed -n '2,/^---$/{ /^---$/d; p; }' "$skill_file")"

  if ! sed -n '2,$p' "$skill_file" | grep -qm1 "^---$"; then
    fail "$SKILL_NAME/SKILL.md frontmatter has no closing ---"
    continue
  fi

  BAD_LINES="$(echo "$FRONTMATTER" | grep -vnE '^$|^[a-zA-Z_][a-zA-Z0-9_-]*:' || true)"
  if [ -n "$BAD_LINES" ]; then
    fail "$SKILL_NAME/SKILL.md frontmatter has malformed YAML: $BAD_LINES"
    continue
  fi

  HAS_NAME=0; HAS_DESC=0
  echo "$FRONTMATTER" | grep -q "^name:" && HAS_NAME=1
  echo "$FRONTMATTER" | grep -q "^description:" && HAS_DESC=1
  if [ "$HAS_NAME" -eq 1 ] && [ "$HAS_DESC" -eq 1 ]; then
    pass "$SKILL_NAME/SKILL.md has valid frontmatter with name and description"
  else
    [ "$HAS_NAME" -eq 0 ] && fail "$SKILL_NAME/SKILL.md missing 'name' in frontmatter"
    [ "$HAS_DESC" -eq 0 ] && fail "$SKILL_NAME/SKILL.md missing 'description' in frontmatter"
  fi
done < <(find "$ROOT_DIR/skills" -name "SKILL.md" -type f 2>/dev/null)

# --- Check 4: No local paths in tracked files ---
CHECK_NUM=$((CHECK_NUM + 1))
echo "[$CHECK_NUM/$TOTAL_CHECKS] No local paths"
LOCAL_PATH_REGEX='(/Users/|/home/|C:\\)'
FOUND_PATHS=0
while IFS= read -r file; do
  case "$file" in
    "$ROOT_DIR/validate.sh"|"$ROOT_DIR/scripts/"*) continue ;;
  esac
  if grep -qE "$LOCAL_PATH_REGEX" "$file" 2>/dev/null; then
    fail "Local path found in $(basename "$file"): $(grep -nE "$LOCAL_PATH_REGEX" "$file" | head -1)"
    FOUND_PATHS=1
  fi
done < <(find "$ROOT_DIR" -type f \( -name "*.md" -o -name "*.mdc" -o -name "*.sh" -o -name "*.yaml" -o -name "*.yml" \) ! -path "*/.git/*" 2>/dev/null)
if [ "$FOUND_PATHS" -eq 0 ]; then
  pass "No local paths found in any tracked file"
fi

# --- Check 5: Generated file parity (delegates to sync-rules.sh --check) ---
CHECK_NUM=$((CHECK_NUM + 1))
echo "[$CHECK_NUM/$TOTAL_CHECKS] Generated file parity"
SYNC_ARGS="--check"
if [ "$TOOLS" != "all" ]; then
  SYNC_ARGS="--check --tools $TOOLS"
fi
if bash "$ROOT_DIR/scripts/sync-rules.sh" $SYNC_ARGS >/dev/null 2>&1; then
  pass "All generated files match canonical source"
else
  fail "Generated files out of sync — run scripts/sync-rules.sh"
fi

# --- Check 6: Skill mirror parity (byte-identical cmp) ---
CHECK_NUM=$((CHECK_NUM + 1))
echo "[$CHECK_NUM/$TOTAL_CHECKS] Skill mirror parity"
MIRROR_OK=1
while IFS= read -r skill_file; do
  SKILL_NAME="$(basename "$(dirname "$skill_file")")"

  if tool_enabled "claude"; then
    CLAUDE_MIRROR="$PROJECT_ROOT/.claude/skills/$SKILL_NAME/SKILL.md"
    if [ -f "$CLAUDE_MIRROR" ]; then
      if cmp -s "$skill_file" "$CLAUDE_MIRROR"; then
        pass "$SKILL_NAME: canonical == .claude/skills/ mirror"
      else
        fail "$SKILL_NAME: .claude/skills/ mirror is NOT byte-identical"
        MIRROR_OK=0
      fi
    else
      fail "$SKILL_NAME: .claude/skills/ mirror missing"
      MIRROR_OK=0
    fi
  fi

  if tool_enabled "codex"; then
    CODEX_MIRROR="$PROJECT_ROOT/.agents/skills/$SKILL_NAME/SKILL.md"
    if [ -f "$CODEX_MIRROR" ]; then
      if cmp -s "$skill_file" "$CODEX_MIRROR"; then
        pass "$SKILL_NAME: canonical == .agents/skills/ mirror"
      else
        fail "$SKILL_NAME: .agents/skills/ mirror is NOT byte-identical"
        MIRROR_OK=0
      fi
    else
      fail "$SKILL_NAME: .agents/skills/ mirror missing"
      MIRROR_OK=0
    fi
  fi
done < <(find "$ROOT_DIR/skills" -name "SKILL.md" -type f 2>/dev/null)

# --- Check 7: Mirror frontmatter integrity ---
CHECK_NUM=$((CHECK_NUM + 1))
echo "[$CHECK_NUM/$TOTAL_CHECKS] Mirror frontmatter integrity"
INTEGRITY_OK=1
for mirror_root in "$PROJECT_ROOT/.claude/skills" "$PROJECT_ROOT/.agents/skills"; do
  if [ -d "$mirror_root" ]; then
    while IFS= read -r mirror_file; do
      MIRROR_NAME="$(basename "$(dirname "$mirror_file")")"
      if [ "$(head -1 "$mirror_file")" = "---" ]; then
        pass "$mirror_root/$MIRROR_NAME/SKILL.md starts with ---"
      else
        fail "$mirror_root/$MIRROR_NAME/SKILL.md does not start with --- (frontmatter broken)"
        INTEGRITY_OK=0
      fi
    done < <(find "$mirror_root" -name "SKILL.md" -type f 2>/dev/null)
  fi
done

# --- Check 8: Generated rule frontmatter schema ---
CHECK_NUM=$((CHECK_NUM + 1))
echo "[$CHECK_NUM/$TOTAL_CHECKS] Generated rule frontmatter schema"

if tool_enabled "cursor"; then
  CURSOR_FILE="$PROJECT_ROOT/.cursor/rules/agentic-ai.mdc"
  if [ -f "$CURSOR_FILE" ]; then
    if grep -q "alwaysApply: false" "$CURSOR_FILE"; then
      pass "Cursor .mdc has alwaysApply: false"
    else
      fail "Cursor .mdc missing alwaysApply: false"
    fi
  else
    fail "Cursor .mdc not found at $CURSOR_FILE"
  fi
fi

if tool_enabled "windsurf"; then
  WINDSURF_FILE="$PROJECT_ROOT/.windsurf/rules/agentic-ai.md"
  if [ -f "$WINDSURF_FILE" ]; then
    if grep -q "trigger: model_decision" "$WINDSURF_FILE"; then
      pass "Windsurf rule has trigger: model_decision"
    else
      fail "Windsurf rule missing trigger: model_decision"
    fi
  else
    fail "Windsurf rule not found at $WINDSURF_FILE"
  fi
fi

if tool_enabled "copilot"; then
  COPILOT_FILE="$PROJECT_ROOT/.github/instructions/agentic-ai.instructions.md"
  if [ -f "$COPILOT_FILE" ]; then
    if grep -q "applyTo:" "$COPILOT_FILE"; then
      pass "Copilot instructions has applyTo"
    else
      fail "Copilot instructions missing applyTo"
    fi
  else
    fail "Copilot instructions not found at $COPILOT_FILE"
  fi
fi

# --- Check 9: CLAUDE.md safety audit ---
CHECK_NUM=$((CHECK_NUM + 1))
echo "[$CHECK_NUM/$TOTAL_CHECKS] CLAUDE.md safety audit"
SYNC_SCRIPT="$ROOT_DIR/scripts/sync-rules.sh"
# The sync script must never reference the root CLAUDE.md
# We check for patterns that would write/read/target root CLAUDE.md
# Exclude comment lines and this check pattern itself
CLAUDE_REFS="$(grep -n 'CLAUDE\.md' "$SYNC_SCRIPT" | grep -v '^#' | grep -v '# ' || true)"
if [ -z "$CLAUDE_REFS" ]; then
  pass "sync-rules.sh has no CLAUDE.md references"
else
  fail "sync-rules.sh references CLAUDE.md: $CLAUDE_REFS"
fi

# --- Summary ---
echo ""
echo "=== Results ==="
TOTAL=$((ERRORS + WARNINGS))
if [ "$ERRORS" -eq 0 ]; then
  echo "ALL CHECKS PASSED ($WARNINGS warning(s))"
  exit 0
else
  echo "FAILED: $ERRORS error(s), $WARNINGS warning(s)"
  exit 1
fi
