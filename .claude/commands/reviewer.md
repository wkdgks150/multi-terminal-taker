# Reviewer — Code Review

Review implemented code for bugs, security issues, and spec compliance.

## Instructions

### Step 1: Identify Scope

- If the user specifies files, review those.
- If not, use `git diff main` or `git diff HEAD~1` to find changed files.
- Focus on source code (src/, lib/, app/) — skip config, docs, tests.

### Step 2: Read the Relevant FSD

Before reviewing code, read the FSD file for the feature being implemented.
Check `docs/FSD/` for the matching feature spec.
If no FSD exists, review against general best practices only.

### Step 3: Launch Review Sub-Agent

Use the Task tool with subagent_type="general-purpose".
The sub-agent reads all changed files and the FSD, then evaluates.

### Step 4: Review Checklist

**Bug Potential:**
- [ ] Null/undefined access without guards
- [ ] Off-by-one errors in loops and slicing
- [ ] Race conditions in async code
- [ ] Unhandled promise rejections
- [ ] Type coercion surprises

**Spec Compliance:**
- [ ] Implementation matches FSD user stories
- [ ] All FSD business rules are implemented
- [ ] API request/response matches FSD spec
- [ ] Edge cases from FSD are handled

**Security:**
- [ ] No SQL/NoSQL injection vectors
- [ ] No XSS vectors (unsanitized user input in HTML)
- [ ] No SSRF vectors (user-controlled URLs)
- [ ] No hardcoded secrets or credentials
- [ ] Auth/authz checks on protected routes

**Architecture:**
- [ ] No circular dependencies introduced
- [ ] Error handling at system boundaries only
- [ ] No unnecessary abstraction layers

### Step 5: Output

```markdown
## Code Review Result

**Verdict**: PASS / FAIL

### [BLOCKER] Must-Fix Items
1. {file:line — description — why it's a blocker}

### [WARNING] Recommended Fixes
1. {file:line — description — risk if not fixed}

### [INFO] Notes
1. {observation that doesn't need action}

### Spec Compliance
- {FSD file}: {ALIGNED / DEVIATED — description of deviation}
```

## Rules
- FAIL if any BLOCKER exists. PASS otherwise.
- Don't flag code style issues (linters handle that).
- Don't suggest refactoring unless there's a concrete bug risk.
- Reference specific file:line for every finding.
- Sub-agent must NOT modify any files.
- If spec deviation found, note it for CHANGELOG.md entry.
