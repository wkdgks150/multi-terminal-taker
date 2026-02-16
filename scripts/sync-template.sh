#!/bin/bash
# sync-template.sh
# Selectively sync latest changes from service-project-template into the current project.
#
# Usage: bash scripts/sync-template.sh
#
# Sync targets (shared workflow files):
#   - docs/FSD/_TEMPLATE.md
#   - scripts/sync-template.sh (itself)
#   - .claude/settings.json
#   - .claude/commands/*.md (skill files)
#
# NOT synced (project-customized):
#   - CLAUDE.md (project-specific)
#   - docs/BPD.md, SDD.md, CHANGELOG.md, DECISIONS.md (project content)
#   - docs/FSD/*.md (except _TEMPLATE.md)
#   - src/, tests/ (project code)
#   - .claude/handoffs/ (session-specific)

set -euo pipefail

TEMPLATE_DIR="/Applications/GitHub/service-project-template"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Files to sync (individual files)
SYNC_FILES=(
  "docs/FSD/_TEMPLATE.md"
  "scripts/sync-template.sh"
  ".claude/settings.json"
)

# Directories to sync (all .md files within)
SYNC_DIRS=(
  ".claude/commands"
)

echo "=== Template Sync ==="
echo "Template: $TEMPLATE_DIR"
echo "Project:  $PROJECT_DIR"
echo ""

for file in "${SYNC_FILES[@]}"; do
  template_file="$TEMPLATE_DIR/$file"
  project_file="$PROJECT_DIR/$file"

  if [ ! -f "$template_file" ]; then
    echo "[SKIP] $file - not found in template"
    continue
  fi

  if [ ! -f "$project_file" ]; then
    echo "[NEW]  $file - copying new file"
    mkdir -p "$(dirname "$project_file")"
    cp "$template_file" "$project_file"
    continue
  fi

  if diff -q "$template_file" "$project_file" > /dev/null 2>&1; then
    echo "[OK]   $file - already up to date"
  else
    echo ""
    echo "[DIFF] $file - changes found:"
    diff --color=auto "$project_file" "$template_file" || true
    echo ""
    read -p "  Update this file? (y/n/d=detailed diff): " choice
    case "$choice" in
      y|Y)
        cp "$template_file" "$project_file"
        echo "  -> Updated"
        ;;
      d|D)
        diff -u "$project_file" "$template_file" || true
        read -p "  Update? (y/n): " choice2
        if [ "$choice2" = "y" ] || [ "$choice2" = "Y" ]; then
          cp "$template_file" "$project_file"
          echo "  -> Updated"
        else
          echo "  -> Skipped"
        fi
        ;;
      *)
        echo "  -> Skipped"
        ;;
    esac
  fi
done

# Sync directories (all .md files)
for dir in "${SYNC_DIRS[@]}"; do
  template_dir_path="$TEMPLATE_DIR/$dir"
  project_dir_path="$PROJECT_DIR/$dir"

  if [ ! -d "$template_dir_path" ]; then
    echo "[SKIP] $dir/ - not found in template"
    continue
  fi

  mkdir -p "$project_dir_path"

  for template_file in "$template_dir_path"/*.md; do
    [ -f "$template_file" ] || continue
    filename=$(basename "$template_file")
    project_file="$project_dir_path/$filename"

    if [ ! -f "$project_file" ]; then
      echo "[NEW]  $dir/$filename - copying new file"
      cp "$template_file" "$project_file"
      continue
    fi

    if diff -q "$template_file" "$project_file" > /dev/null 2>&1; then
      echo "[OK]   $dir/$filename - already up to date"
    else
      echo ""
      echo "[DIFF] $dir/$filename - changes found:"
      diff --color=auto "$project_file" "$template_file" || true
      echo ""
      read -p "  Update this file? (y/n): " choice
      if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
        cp "$template_file" "$project_file"
        echo "  -> Updated"
      else
        echo "  -> Skipped"
      fi
    fi
  done
done

echo ""
echo "=== Sync complete ==="
