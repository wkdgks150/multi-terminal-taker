# Tester — Test Review & Execution

Review test coverage and run tests for the implemented feature.

## Instructions

### Step 1: Identify Scope

- If the user specifies a feature, find its test files.
- If not, use `git diff` to find changed source files, then locate corresponding test files.
- Test file patterns: `tests/`, `__tests__/`, `*.test.*`, `*.spec.*`

### Step 2: Read the FSD

Read the relevant FSD file from `docs/FSD/` to understand expected behavior.

### Step 3: Launch Test Sub-Agent

Use the Task tool with subagent_type="general-purpose".
The sub-agent reviews test files and runs the test suite.

### Step 4: Review Checklist

**Test Existence:**
- [ ] Test file exists for the implemented feature
- [ ] Test file follows project naming conventions

**Coverage:**
- [ ] Happy path covered (normal expected behavior)
- [ ] Error path covered (invalid inputs, failures)
- [ ] Edge cases covered (empty, null, boundary values)
- [ ] Integration points tested (API calls, DB queries) if applicable

**Test Quality:**
- [ ] Tests are independent (no order dependency)
- [ ] Test descriptions clearly state what is being tested
- [ ] Assertions are specific (not just "no error thrown")
- [ ] Mocks/stubs are used appropriately for external dependencies

### Step 5: Run Tests

Execute the project's test command:
- Check `package.json` scripts for test command (npm/yarn/pnpm)
- Check for `pytest`, `go test`, or other language-specific runners
- Run only the relevant test file(s) first, then full suite

### Step 6: Output

```markdown
## Test Review Result

### Test Run
- **Command**: {command used}
- **Result**: PASS / FAIL
- **Summary**: {N passed, M failed, K skipped}
- **Failed tests**: {list if any}

### Coverage Analysis
- Happy path: {COVERED / MISSING}
- Error path: {COVERED / MISSING}
- Edge cases: {COVERED / MISSING}

### Missing Test Cases
1. {description of test that should exist — expected input → expected output}
2. ...

### Suggestions
1. {actionable improvement}
2. ...
```

## Rules
- Always run tests — don't just review code.
- If tests fail, report the failure clearly with error messages.
- If no test runner is configured, report that as the first finding.
- Sub-agent may run tests but must NOT modify source code or test files.
- Keep missing test case suggestions to 3-5 max (most impactful ones).
