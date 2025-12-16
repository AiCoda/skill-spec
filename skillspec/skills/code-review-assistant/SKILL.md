---
name: "code-review-assistant"
description: "Provide intelligent code review feedback focusing on quality, security, and maintainability. Use when: reviewing pull requests | pre-commit checks | code quality audits"
---

# Code Review Assistant

## Description

This skill provides comprehensive code review feedback by analyzing code diffs and changes. It examines code for security vulnerabilities, performance issues, style violations, testing gaps, and documentation completeness. The review produces actionable findings with severity levels and specific suggestions for improvement.

**Review focus areas:**
- **Security**: Sensitive data exposure, injection vulnerabilities, hardcoded credentials
- **Performance**: Inefficient algorithms, resource leaks, blocking operations
- **Style**: Code formatting, naming conventions, consistency
- **Testing**: Test coverage, assertion quality, edge case handling
- **Documentation**: Comment completeness, docstring quality, README accuracy

**Review outcomes:**
- `approved`: Code meets quality standards
- `changes_requested`: Issues found that should be addressed
- `needs_discussion`: Complex issues requiring human judgment

## When to Use

Use this skill when:
- Reviewing pull requests before merging
- Performing pre-commit quality checks
- Conducting periodic code quality audits
- Onboarding new team members with review standards
- Validating code changes before deployment

Do NOT use this skill for:
- Automatically fixing code issues (use auto-fix-suggestions instead)
- Running or executing the code
- Accessing external repositories or services
- Persisting review history
- Generating unit tests

## Instructions

### Input Requirements

1. **code_diff** (required): Git diff or code changes to review
   - Unified diff format or raw code
   - Maximum 100,000 characters

2. **file_path** (required): Path of the file being reviewed
   - Used for language detection and context

3. **language** (optional): Programming language
   - `python`, `javascript`, `typescript`, `java`, `go`, `rust`
   - `auto` (default): Detect from file extension

4. **review_focus** (optional): Areas to focus on
   - Array of: `security`, `performance`, `style`, `testing`, `documentation`
   - `all` (default): Review all areas

5. **severity_threshold** (optional): Minimum severity to report
   - `info`, `warning`, `error`, `critical`
   - Default: `info` (report all findings)

6. **context_files** (optional): Additional files for context
   - Interfaces, base classes, related modules
   - Helps understand inheritance and dependencies

### Execution Flow

1. Parse diff into structured change representation
2. Detect or confirm programming language
3. Apply decision rules (security-critical, test files, config files, large changes)
4. Analyze each focus area (security, performance, style, testing, documentation)
5. Aggregate findings and apply severity filter
6. Generate executive summary

### Output Format

```json
{
  "status": "approved | changes_requested | needs_discussion",
  "review": {
    "summary": "Executive summary of review findings",
    "findings": [
      {
        "severity": "info | warning | error | critical",
        "category": "security | performance | style | testing | documentation | logic",
        "message": "Description of the issue",
        "line": 42,
        "suggestion": "How to fix the issue"
      }
    ],
    "stats": {
      "total_findings": 5,
      "by_severity": {"error": 1, "warning": 3, "info": 1},
      "by_category": {"security": 1, "style": 3, "documentation": 1}
    }
  },
  "metadata": {
    "language": "python",
    "lines_reviewed": 150,
    "review_duration_ms": 1200
  }
}
```

## Examples

### Example 1: Python Security Issue

**Input:**
```json
{
  "code_diff": "+import os\n+\n+def get_config():\n+    return {\n+        \"api_key\": os.environ.get(\"API_KEY\", \"default-key-123\"),\n+        \"debug\": True\n+    }",
  "file_path": "src/config.py",
  "language": "python",
  "review_focus": ["security"]
}
```

**Output:**
```json
{
  "status": "changes_requested",
  "review": {
    "summary": "Security concerns found: hardcoded default credentials and debug mode enabled",
    "findings": [
      {
        "severity": "error",
        "category": "security",
        "message": "Hardcoded default API key - use proper secret management",
        "line": 5,
        "suggestion": "Remove default value or use a placeholder that fails fast"
      },
      {
        "severity": "warning",
        "category": "security",
        "message": "Debug mode should not be enabled by default",
        "line": 6,
        "suggestion": "Set debug default to False"
      }
    ],
    "stats": {
      "total_findings": 2,
      "by_severity": {"error": 1, "warning": 1},
      "by_category": {"security": 2}
    }
  }
}
```

### Example 2: Test File Review

**Input:**
```json
{
  "code_diff": "+def test_user_creation():\n+    user = create_user(\"test\")\n+    assert user",
  "file_path": "tests/test_user.py",
  "review_focus": ["testing"]
}
```

**Output:**
```json
{
  "status": "changes_requested",
  "review": {
    "summary": "Test has minimal assertions - consider adding more specific checks",
    "findings": [
      {
        "severity": "warning",
        "category": "testing",
        "message": "Single boolean assertion provides weak verification",
        "line": 3,
        "suggestion": "Assert specific properties: assert user.name == 'test'"
      }
    ]
  }
}
```

### Example 3: Binary File

**Input:**
```json
{
  "code_diff": "Binary files differ",
  "file_path": "assets/logo.png"
}
```

**Output:**
```json
{
  "status": "approved",
  "review": {
    "summary": "Binary file change - manual review recommended",
    "findings": []
  }
}
```

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Empty diff | Return error with code `PARSE_ERROR` |
| Binary file | Return approved with manual review note |
| Deleted file | Return approved with dependency check note |
| Hardcoded credentials | Trigger security-critical review path |
| Large change (>5000 chars) | Break into focused review sections |
| Test file | Skip style checks, focus on testing quality |
| Config file | Skip testing/documentation checks |

## Limitations

1. **Static Analysis Only**: Cannot execute code or verify runtime behavior
2. **No Auto-Fix**: Reports issues but does not automatically fix them
3. **Language Support**: Best support for Python, JavaScript, TypeScript, Java, Go, Rust
4. **No External Access**: Cannot fetch dependencies or related files from repositories
5. **No History**: Does not track review history or learn from previous reviews
6. **Context Limitations**: May miss issues requiring full codebase context

## Error Codes

| Code | Retryable | Description |
|------|-----------|-------------|
| `PARSE_ERROR` | No | Failed to parse code diff |
| `UNSUPPORTED_LANGUAGE` | No | Programming language not supported for review |
| `ANALYSIS_TIMEOUT` | Yes | Review analysis exceeded time limit |
| `CONTEXT_ERROR` | No | Failed to load or parse context files |

## Related Skills

- **auto-fix-suggestions**: Apply automated fixes based on review findings
- **pr-summarizer**: Generate PR summary including review highlights
- **detect-layer-violation**: Check for architectural layer violations
