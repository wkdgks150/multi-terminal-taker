# Sync Time — Post-Implementation Document Sync

Synchronize planning documents with implementation reality after feature completion.

## Instructions

### Step 1: Read Unsynced Changelog Entries

Read `docs/CHANGELOG.md` and find entries that are NOT marked `[synced]`.
If all entries are synced, inform the user and stop.

### Step 2: Categorize Changes

For each unsynced entry, determine:
- Which FSD file it relates to (noted in the changelog entry)
- Whether it affects SDD.md (architecture, data model, API changes)
- The nature of the change (addition, modification, removal, deviation)

### Step 3: Update FSD Files

For each affected FSD file in `docs/FSD/`:
1. Read the current FSD content
2. Update the specific sections that deviated
3. Update the `Last modified` date and version
4. Do NOT delete or rename section headers

### Step 4: Update SDD.md (if needed)

If changes affect architecture-level concerns:
1. Update relevant SDD sections (data model, API design, user flows)
2. Update the `Last modified` date and version
3. Keep changes minimal — only what actually changed

### Step 5: Mark as Synced

In `docs/CHANGELOG.md`, append `[synced]` to each processed entry:
```
- [2026-02-15] Added pagination to club list (related FSD: club-list.md) [synced]
```

### Step 6: Commit & Push

```bash
git add docs/
git commit -m "docs: sync planning documents with implementation"
git push
```

### Step 7: Dashboard Sync

Run the dashboard sync script if it exists:
```bash
node /Applications/GitHub/project-dashboard/scripts/sync-projects-yaml.mjs
```

If the script doesn't exist, skip this step silently.

### Step 8: Report

```markdown
## Sync Time Report

### Entries Processed
1. {changelog entry} → {FSD file updated}
2. ...

### Documents Updated
- {list of files modified}

### Dashboard Sync
- {success / skipped / error}
```

## Rules
- Only process unsynced entries — don't re-process.
- Preserve document structure — update content within sections only.
- If a changelog entry is ambiguous, ask the user before syncing.
- Commit doc updates separately from code commits.
