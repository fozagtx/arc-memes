#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="arc-memecoin-intel"
REPO_URL="${ARC_MEMES_REPO:-https://github.com/fozagtx/arc-memes.git}"
REPO_REF="${ARC_MEMES_REF:-main}"

# Works two ways: run from a clone (./scripts/install.sh), or piped from curl
# (curl -fsSL .../install.sh | bash), in which case we git clone into a temp dir first.
SCRIPT_PATH="${BASH_SOURCE[0]:-}"
if [[ -n "$SCRIPT_PATH" && -f "$(dirname "$SCRIPT_PATH")/../skills/$SKILL_NAME/SKILL.md" ]]; then
  ROOT_DIR="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
else
  command -v git >/dev/null || { echo "git is required: install git, then re-run." >&2; exit 1; }
  ROOT_DIR="$(mktemp -d)"
  trap 'rm -rf "$ROOT_DIR"' EXIT
  echo "Cloning $REPO_URL ($REPO_REF)..."
  git clone --quiet --depth 1 --branch "$REPO_REF" "$REPO_URL" "$ROOT_DIR"
fi
SOURCE_DIR="$ROOT_DIR/skills/$SKILL_NAME"
DRY_RUN=0
TARGETS=()
CUSTOM_DEST=""

usage() {
  cat <<'USAGE'
Usage:
  curl -fsSL https://raw.githubusercontent.com/fozagtx/arc-memes/main/scripts/install.sh | bash
  curl -fsSL .../install.sh | bash -s -- all
  scripts/install.sh [--dry-run] codex|claude|agents|all
  scripts/install.sh [--dry-run] --dest /path/to/skills/arc-memecoin-intel

Targets:
  codex   -> ${CODEX_HOME:-$HOME/.codex}/skills/arc-memecoin-intel
  claude  -> ${CLAUDE_HOME:-$HOME/.claude}/skills/arc-memecoin-intel
  agents  -> ${AGENTS_HOME:-$HOME/.agents}/skills/arc-memecoin-intel
  all     -> codex, claude, and agents

Default target (no args): claude

Environment overrides:
  ARC_MEMES_REF  branch/tag to install when piped from curl (default: main)
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
  TARGETS=("claude")
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
  chmod +x "$dest/scripts/arc_scan.py" 2>/dev/null || true
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

if ! command -v python3 >/dev/null; then
  echo "Note: the scanner needs Python 3 (preinstalled on macOS/Linux). Install it from python.org if missing." >&2
fi
[[ "$DRY_RUN" -eq 1 ]] || echo "Done. Restart your agent, then ask: \"use arc-memecoin-intel to scan 0x...\""
