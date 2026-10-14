#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_NAME="arc-memecoin-intel"
SOURCE_DIR="$ROOT_DIR/skills/$SKILL_NAME"
DRY_RUN=0
TARGETS=()
CUSTOM_DEST=""

usage() {
  cat <<'USAGE'
Usage:
  scripts/install.sh [--dry-run] codex|claude|agents|all
  scripts/install.sh [--dry-run] --dest /path/to/skills/arc-memecoin-intel

Targets:
  codex   -> ${CODEX_HOME:-$HOME/.codex}/skills/arc-memecoin-intel
  claude  -> ${CLAUDE_HOME:-$HOME/.claude}/skills/arc-memecoin-intel
  agents  -> ${AGENTS_HOME:-$HOME/.agents}/skills/arc-memecoin-intel
  all     -> codex, claude, and agents

Environment overrides:
  CODEX_HOME   default: $HOME/.codex
  CLAUDE_HOME  default: $HOME/.claude
  AGENTS_HOME  default: $HOME/.agents
USAGE
}

while (($#)); do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --dest)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --dest" >&2
        usage
        exit 2
      fi
      CUSTOM_DEST="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    codex|claude|agents|all)
      TARGETS+=("$1")
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ ! -f "$SOURCE_DIR/SKILL.md" ]]; then
  echo "Skill source not found: $SOURCE_DIR" >&2
  exit 1
fi

if [[ -n "$CUSTOM_DEST" && ${#TARGETS[@]} -gt 0 ]]; then
  echo "Use either --dest or named targets, not both." >&2
  exit 2
fi

if [[ -z "$CUSTOM_DEST" && ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=("codex")
fi

expand_targets() {
  local target
  for target in "$@"; do
    if [[ "$target" == "all" ]]; then
      printf '%s\n' codex claude agents
    else
      printf '%s\n' "$target"
    fi
  done
}

target_dest() {
  case "$1" in
    codex)
      printf '%s/skills/%s\n' "${CODEX_HOME:-$HOME/.codex}" "$SKILL_NAME"
      ;;
    claude)
      printf '%s/skills/%s\n' "${CLAUDE_HOME:-$HOME/.claude}" "$SKILL_NAME"
      ;;
    agents)
      printf '%s/skills/%s\n' "${AGENTS_HOME:-$HOME/.agents}" "$SKILL_NAME"
      ;;
    *)
      echo "Unknown target: $1" >&2
      exit 2
      ;;
  esac
}

install_to() {
  local dest="$1"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Would install $SOURCE_DIR -> $dest"
    return
  fi

  mkdir -p "$dest"
  cp -R "$SOURCE_DIR"/. "$dest"/
  echo "Installed $SKILL_NAME -> $dest"
}

if [[ -n "$CUSTOM_DEST" ]]; then
  install_to "$CUSTOM_DEST"
  exit 0
fi

RESOLVED_TARGETS=()
while IFS= read -r target; do
  RESOLVED_TARGETS+=("$target")
done < <(expand_targets "${TARGETS[@]}" | awk '!seen[$0]++')

for target in "${RESOLVED_TARGETS[@]}"; do
  install_to "$(target_dest "$target")"
done
