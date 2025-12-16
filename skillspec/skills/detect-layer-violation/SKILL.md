---
name: "detect-layer-violation"
description: "Analyze codebase to detect cross-layer reverse dependencies that violate architectural layering principles. Use when: reviewing PR changes | architecture health checks | pre-merge validation"
---

# Detect Layer Violation

## Description

This skill analyzes source code to identify architectural violations in layered systems. It detects when lower layers incorrectly depend on higher layers, which breaks the fundamental principle of clean architecture where dependencies should only flow inward (from outer layers to inner layers).

**Supported violation types:**
- **Reverse Dependency**: A lower layer imports from a higher layer (e.g., Domain importing from API)
- **Skip Layer**: A layer bypasses intermediate layers (e.g., API directly importing from Infrastructure)
- **Forbidden Dependency**: Any import from explicitly blacklisted modules

## When to Use

Use this skill when:
- Reviewing pull requests that modify import statements
- Running periodic architecture health checks
- Validating code before merging feature branches
- Setting up CI/CD pipelines for architectural governance
- Onboarding new team members to understand layer boundaries

Do NOT use this skill for:
- Analyzing runtime or dynamic dependencies
- Detecting circular dependencies within the same layer
- Validating business logic correctness
- Checking for unused imports or dead code

## Instructions

### Input Requirements

1. **source_files** (required): Array of source files to analyze
   ```json
   {
     "path": "src/domain/user_service.py",
     "content": "from api.auth import get_current_user\n...",
     "language": "python"
   }
   ```

2. **layer_config** (required): Layer hierarchy definition
   ```yaml
   layers:
     - name: "api"
       patterns: ["src/api/**", "src/handlers/**"]
     - name: "domain"
       patterns: ["src/domain/**", "src/services/**"]
     - name: "infra"
       patterns: ["src/infra/**", "src/repository/**"]

   allowed_dependencies:
     api: ["domain"]      # API can import from Domain
     domain: ["infra"]    # Domain can import from Infra
     infra: []            # Infra cannot import from any layer
   ```

3. **ignore_patterns** (optional): File patterns to exclude
   - Default: `["**/test/**", "**/__test__/**", "**/mock/**"]`

4. **strict_mode** (optional): Treat warnings as errors
   - Default: `false`

### Execution Flow

1. Parse and validate layer configuration
2. Classify each source file into its architectural layer
3. Extract import statements from each file
4. Resolve imports to actual files and their layers
5. Check each dependency against allowed rules
6. Generate detailed violation report

### Output Format

```json
{
  "status": "clean | violations_found | error",
  "analysis": {
    "files_analyzed": 15,
    "layers_detected": ["api", "domain", "infra"],
    "violations": [
      {
        "source_file": "src/domain/user_service.py",
        "source_layer": "domain",
        "target_file": "src/api/auth.py",
        "target_layer": "api",
        "violation_type": "reverse_dependency",
        "severity": "error",
        "line_number": 3,
        "import_statement": "from api.auth import get_current_user",
        "suggestion": "Inject authentication via dependency inversion"
      }
    ],
    "summary": {
      "total_violations": 1,
      "by_type": {"reverse_dependency": 1},
      "by_layer": {"domain": 1},
      "most_violated_layer": "domain"
    }
  }
}
```

## Examples

### Example 1: Clean Architecture Check

**Input:**
```json
{
  "source_files": [
    {
      "path": "src/api/user_controller.py",
      "content": "from domain.user_service import UserService\n\nclass UserController:\n    def __init__(self):\n        self.service = UserService()",
      "language": "python"
    },
    {
      "path": "src/domain/user_service.py",
      "content": "from infra.user_repository import UserRepository\n\nclass UserService:\n    pass",
      "language": "python"
    }
  ],
  "layer_config": {
    "layers": [
      {"name": "api", "patterns": ["src/api/**"]},
      {"name": "domain", "patterns": ["src/domain/**"]},
      {"name": "infra", "patterns": ["src/infra/**"]}
    ],
    "allowed_dependencies": {
      "api": ["domain"],
      "domain": ["infra"],
      "infra": []
    }
  }
}
```

**Output:**
```json
{
  "status": "clean",
  "analysis": {
    "files_analyzed": 2,
    "layers_detected": ["api", "domain"],
    "violations": [],
    "summary": {"total_violations": 0}
  }
}
```

All dependencies flow correctly: API -> Domain -> Infra.

### Example 2: Reverse Dependency Detected

**Input:**
```json
{
  "source_files": [
    {
      "path": "src/domain/user_service.py",
      "content": "from api.auth import get_current_user  # VIOLATION!\nfrom infra.user_repository import UserRepository\n\nclass UserService:\n    def get_user(self, user_id):\n        current = get_current_user()\n        return self.repo.find(user_id)",
      "language": "python"
    }
  ],
  "layer_config": {
    "layers": [
      {"name": "api", "patterns": ["src/api/**"]},
      {"name": "domain", "patterns": ["src/domain/**"]},
      {"name": "infra", "patterns": ["src/infra/**"]}
    ],
    "allowed_dependencies": {
      "api": ["domain"],
      "domain": ["infra"],
      "infra": []
    }
  }
}
```

**Output:**
```json
{
  "status": "violations_found",
  "analysis": {
    "files_analyzed": 1,
    "violations": [
      {
        "source_file": "src/domain/user_service.py",
        "source_layer": "domain",
        "target_layer": "api",
        "violation_type": "reverse_dependency",
        "severity": "error",
        "line_number": 1,
        "import_statement": "from api.auth import get_current_user",
        "suggestion": "Move authentication logic to domain layer or inject via dependency inversion"
      }
    ],
    "summary": {
      "total_violations": 1,
      "by_type": {"reverse_dependency": 1}
    }
  }
}
```

The domain layer incorrectly imports from the API layer. Fix by injecting authentication as a dependency.

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Empty source files | Return error with code `NO_SOURCE_FILES` |
| Single layer config | Return error with code `INVALID_LAYER_CONFIG` |
| File not matching any layer | Log warning, skip file in analysis |
| Binary file in source | Skip with info message |
| Circular import within same layer | Not detected (out of scope) |
| Dynamic imports (`importlib`) | Not detected (runtime only) |

## Limitations

1. **Static Analysis Only**: Cannot detect runtime or dynamic imports (e.g., `importlib.import_module()`)
2. **No Auto-Fix**: Reports violations but does not automatically refactor code
3. **Language Support**: Best support for Python, JavaScript/TypeScript; other languages may have limited import parsing
4. **Same-Layer Cycles**: Does not detect circular dependencies within the same architectural layer
5. **Performance**: Large codebases (>10,000 files) may require chunked analysis

## Error Codes

| Code | Retryable | Description |
|------|-----------|-------------|
| `NO_SOURCE_FILES` | No | No source files provided |
| `INVALID_LAYER_CONFIG` | No | Layer configuration invalid or incomplete |
| `PARSE_ERROR` | No | Failed to parse source file |
| `UNCLASSIFIED_FILE` | No | File doesn't match any layer pattern |
| `ANALYSIS_TIMEOUT` | Yes | Analysis exceeded time limit |

## Related Skills

- **generate-architecture-diagram**: Visualize layer structure and violations
- **code-review-assistant**: Include layer checks in PR reviews
- **refactor-suggestion**: Suggest fixes for detected violations
