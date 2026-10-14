#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="$ROOT_DIR/skills/arc-memecoin-intel"

required_files=(
  "SKILL.md"
  "scripts/arc_scan.py"
  "references/arc-network.md"
  "references/bundle-detection.md"
  "references/scoring.md"
  "references/report-template.md"
  "references/suite-blueprint.md"
)

missing=0
for path in "${required_files[@]}"; do
  if [[ ! -f "$SKILL_DIR/$path" ]]; then
    echo "Missing required file: $path" >&2
    missing=1
  fi
done
[[ "$missing" -eq 0 ]] || exit 1

grep -q '^name: arc-memecoin-intel$' "$SKILL_DIR/SKILL.md" || { echo "SKILL.md missing name" >&2; exit 1; }
grep -q '^description: ' "$SKILL_DIR/SKILL.md" || { echo "SKILL.md missing description" >&2; exit 1; }

for ref in $(grep -o 'references/[a-z-]*\.md' "$SKILL_DIR/SKILL.md" | sort -u); do
  [[ -f "$SKILL_DIR/$ref" ]] || { echo "SKILL.md links missing file: $ref" >&2; exit 1; }
done

python3 -m py_compile "$SKILL_DIR/scripts/arc_scan.py"
python3 "$SKILL_DIR/scripts/arc_scan.py" --help >/dev/null

echo "Skill package verified: $SKILL_DIR"
