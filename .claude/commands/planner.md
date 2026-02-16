# Planner — Planning Document Review

Review a planning document (BPD, SDD, or FSD) for completeness, clarity, and feasibility.

## Instructions

### Step 1: Identify Target Document

- If the user specifies a document, use that.
- If not, check `docs/` for the most recently modified planning document.
- Valid targets: `docs/BPD.md`, `docs/SDD.md`, `docs/FSD/*.md`

### Step 2: Launch Review Sub-Agent

Use the Task tool with subagent_type="general-purpose" to run the review.
The sub-agent must read the full document and evaluate against the checklist below.

### Step 3: Review Checklist

**For BPD.md:**
- [ ] Problem statement is specific and measurable
- [ ] Target users are clearly defined (not "everyone")
- [ ] Market analysis has concrete data points
- [ ] Business model has revenue mechanics
- [ ] MVP scope is bounded (not a wish list)
- [ ] Success metrics are quantifiable

**For SDD.md:**
- [ ] Information architecture matches BPD scope
- [ ] User flows cover happy path AND error paths
- [ ] Screen specs have enough detail to implement
- [ ] Data model handles all entities from user flows
- [ ] API design covers all screen interactions
- [ ] Tech stack choices are justified

**For FSD/*.md:**
- [ ] User stories follow "As a [user], I want [action], so that [benefit]"
- [ ] Input/output specs are complete (types, validation, formats)
- [ ] Business logic rules have no ambiguity
- [ ] Exception handling is specified
- [ ] API endpoints match SDD design
- [ ] Edge cases are listed

### Step 4: Output

```markdown
## Plan Review Result — {document name}

**Verdict**: PASS / NEEDS IMPROVEMENT

### Improvement Suggestions
1. {specific, actionable suggestion with section reference}
2. ...

### Questions (Ambiguous Areas)
1. {question about unclear requirement}
2. ...

### Missing Items
1. {item that should exist but doesn't}
2. ...
```

## Rules
- Be specific — reference section headers and line numbers.
- Don't nitpick formatting — focus on substance.
- "PASS" means ready for development, not perfect.
- Always find at least one improvement suggestion (nothing is perfect).
- Sub-agent must NOT modify any files.
