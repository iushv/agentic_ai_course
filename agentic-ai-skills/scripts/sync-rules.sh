#!/usr/bin/env bash
# sync-rules.sh — Generate tool-specific rule files and skill mirrors from AGENTS.md
# Usage: ./scripts/sync-rules.sh                       # All targets (default)
#        ./scripts/sync-rules.sh --check               # Diff-only mode (exit 1 if out of sync)
#        ./scripts/sync-rules.sh --tools claude         # Only Claude Code mirrors
#        ./scripts/sync-rules.sh --tools cursor,codex   # Comma-separated subset
#        ./scripts/sync-rules.sh --clean-stale          # Remove old generated files with markers
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CANONICAL="$PKG_DIR/AGENTS.md"
MARKER="agentic-ai-skills:auto-generated"

# Root detection: prefer git rev-parse for monorepo/worktree correctness.
# If git root equals the package dir (package is its own repo), use parent instead.
PROJECT_ROOT="$(git -C "$PKG_DIR" rev-parse --show-toplevel 2>/dev/null || echo "")"
if [ -z "$PROJECT_ROOT" ] || [ "$PROJECT_ROOT" = "$PKG_DIR" ]; then
  PROJECT_ROOT="$(cd "$PKG_DIR/.." && pwd)"
fi

if [ ! -f "$CANONICAL" ]; then
  echo "ERROR: $CANONICAL not found" >&2
  exit 1
fi

# --- Parse CLI flags ---
MODE="write"
TOOLS="all"
CLEAN_STALE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --check)      MODE="check"; shift ;;
    --tools)      TOOLS="$2"; shift 2 ;;
    --clean-stale) CLEAN_STALE=1; shift ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

# Normalize comma-separated tools into a space-separated set for matching
tool_enabled() {
  [ "$TOOLS" = "all" ] && return 0
  echo ",$TOOLS," | grep -q ",$1,"
}

CANONICAL_CONTENT="$(cat "$CANONICAL")"
ERRORS=0

# --- Stale cleanup mode ---
if [ "$CLEAN_STALE" -eq 1 ]; then
  STALE_TARGETS=(
    "$PROJECT_ROOT/.windsurfrules"
    "$PROJECT_ROOT/.github/copilot-instructions.md"
    "$PROJECT_ROOT/.codex/AGENTS.md"
  )
  for target in "${STALE_TARGETS[@]}"; do
    if [ -f "$target" ] && grep -q "$MARKER" "$target" 2>/dev/null; then
      rm "$target"
      echo "REMOVED (stale): $target"
    elif [ -f "$target" ]; then
      echo "SKIPPED (no marker): $target"
    fi
  done
  exit 0
fi

# --- Helper: write or check a generated file ---
generate() {
  local target="$1"
  local content="$2"

  if [ "$MODE" = "check" ]; then
    if [ ! -f "$target" ]; then
      echo "MISSING: $target" >&2
      ERRORS=$((ERRORS + 1))
      return
    fi
    if ! diff -q <(printf '%s\n' "$content") "$target" >/dev/null 2>&1; then
      echo "OUT OF SYNC: $target" >&2
      diff --unified=3 <(printf '%s\n' "$content") "$target" >&2 || true
      ERRORS=$((ERRORS + 1))
    else
      echo "OK: $target"
    fi
  else
    mkdir -p "$(dirname "$target")"
    printf '%s\n' "$content" > "$target"
    echo "WROTE: $target"
  fi
}

# --- Helper: copy skill mirror (byte-identical) ---
mirror_skill() {
  local src="$1"
  local dest="$2"

  if [ "$MODE" = "check" ]; then
    if [ ! -f "$dest" ]; then
      echo "MISSING: $dest" >&2
      ERRORS=$((ERRORS + 1))
      return
    fi
    if ! cmp -s "$src" "$dest"; then
      echo "OUT OF SYNC (not byte-identical): $dest" >&2
      ERRORS=$((ERRORS + 1))
    else
      echo "OK: $dest"
    fi
  else
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
    echo "WROTE: $dest"
  fi
}

# =========================================================================
# Target 1: Cursor — .cursor/rules/agentic-ai.mdc
# =========================================================================
if tool_enabled "cursor"; then
  CURSOR_CONTENT="---
# ${MARKER} — do not edit directly
description: >
  Agentic AI production rules — architecture levels, tool design, safety
  guardrails, reliability, observability, cost control, and testing strategy.
  USE WHEN building, reviewing, or debugging AI agents, tool schemas,
  guardrail pipelines, or multi-agent systems.
alwaysApply: false
---

${CANONICAL_CONTENT}"
  generate "$PROJECT_ROOT/.cursor/rules/agentic-ai.mdc" "$CURSOR_CONTENT"
fi

# =========================================================================
# Target 2: Windsurf — .windsurf/rules/agentic-ai.md
# =========================================================================
if tool_enabled "windsurf"; then
  WINDSURF_CONTENT="---
trigger: model_decision
description: >
  Agentic AI production rules — architecture levels, tool design, safety
  guardrails, reliability, observability, cost control, and testing strategy.
  Use when building, reviewing, or debugging AI agents.
---
<!-- ${MARKER} — do not edit directly -->

${CANONICAL_CONTENT}"
  generate "$PROJECT_ROOT/.windsurf/rules/agentic-ai.md" "$WINDSURF_CONTENT"
fi

# =========================================================================
# Target 3: Copilot — .github/instructions/agentic-ai.instructions.md
# =========================================================================
if tool_enabled "copilot"; then
  COPILOT_CONTENT="---
applyTo: '**/agent*,**/tool*,**/guardrail*,**/react*loop*,**/skills/**'
---
<!-- ${MARKER} — do not edit directly -->

${CANONICAL_CONTENT}"
  generate "$PROJECT_ROOT/.github/instructions/agentic-ai.instructions.md" "$COPILOT_CONTENT"
fi

# =========================================================================
# Target 4: Claude Code skill mirrors — .claude/skills/*/SKILL.md
# =========================================================================
if tool_enabled "claude"; then
  for skill_dir in "$PKG_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    src="$skill_dir/SKILL.md"
    if [ -f "$src" ]; then
      mirror_skill "$src" "$PROJECT_ROOT/.claude/skills/$skill_name/SKILL.md"
    fi
  done
fi

# =========================================================================
# Target 5: Codex skill mirrors — .agents/skills/*/SKILL.md
# =========================================================================
if tool_enabled "codex"; then
  for skill_dir in "$PKG_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    src="$skill_dir/SKILL.md"
    if [ -f "$src" ]; then
      mirror_skill "$src" "$PROJECT_ROOT/.agents/skills/$skill_name/SKILL.md"
    fi
  done
fi

# --- Summary ---
if [ "$MODE" = "check" ]; then
  if [ "$ERRORS" -gt 0 ]; then
    echo ""
    echo "FAIL: $ERRORS file(s) out of sync. Run scripts/sync-rules.sh to fix." >&2
    exit 1
  else
    echo ""
    echo "PASS: All generated files are in sync."
  fi
fi
