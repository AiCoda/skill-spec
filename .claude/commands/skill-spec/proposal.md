---
name: "Skill-Spec: Proposal"
description: "Create a new skill spec through interactive requirements gathering and validation"
---

<!-- SKILL-SPEC:START -->
**Guardrails**
- Always read `skillspec/SKILL_AGENTS.md` first for conventions
- Collect requirements through conversation before generating spec.yaml
- Do NOT create empty templates - generate complete, valid specs
- Always validate with `skillspec validate --strict` before completing
- Use kebab-case for skill names (e.g., `extract-api-contract`)

**Arguments**
- `$ARGUMENTS` contains the skill name provided by the user

**Steps**

1. **Parse skill name**
   - Extract from `$ARGUMENTS`, validate kebab-case format
   - If no name provided, ask user for one

2. **Check existing skill**
   - Run `skillspec list` to see existing skills
   - Check if `skillspec/drafts/<name>` or `skillspec/skills/<name>` exists

3. **Collect: skill (Metadata)**
   ```
   What should '<name>' do? (one sentence, 10-200 chars)
   Who owns this skill?
   ```

4. **Collect: inputs**
   ```
   What inputs does this skill need?
   - name: snake_case
   - type: string | number | boolean | object | array
   - required: true | false
   - constraints: not_empty, max_length, pattern, enum...
   ```

5. **Collect: preconditions**
   ```
   What must be true before this skill runs?
   ```

6. **Collect: non_goals**
   ```
   What should this skill explicitly NOT do?
   ```

7. **Collect: decision_rules**
   ```
   What decisions does this skill make?
   - What conditions trigger different behaviors?
   - What's the default behavior?
   ```
   - MUST have one rule with `is_default: true`

8. **Collect: steps**
   ```
   What's the execution flow?
   ```

9. **Collect: output_contract**
   ```
   What format should output be? (json | text | markdown | yaml)
   ```

10. **Collect: failure_modes**
    ```
    What error scenarios? (code: UPPER_SNAKE_CASE, retryable: bool)
    ```

11. **Collect: edge_cases**
    ```
    What edge cases? (empty input, malformed data, boundary values...)
    ```
    Generate for each:
    - case: descriptive name
    - expected: {status, code}
    - input_example: concrete input (optional but recommended)
    - covers_rule: which decision_rule this tests
    - covers_failure: which failure_mode this tests

12. **Collect: context (Optional)**
    ```
    Does this skill work with other skills?
    - works_with: [{skill: "other-skill", reason: "why"}]
    - prerequisites: what user needs to do first
    - scenarios: typical usage scenarios
    ```

13. **Collect: examples (Optional)**
    ```
    Want to add usage examples?
    - name, input, output, explanation
    ```

14. **Generate and Review**
    - Generate complete spec.yaml with all collected info
    - Include `spec_version: "skill-spec/1.0"`
    - Show spec to user in code block
    - Ask: "Does this look correct? Any adjustments?"
    - Make adjustments if requested

15. **Write spec.yaml**
    - Create directory: `skillspec/drafts/<name>/`
    - Write spec.yaml to the directory

16. **Run strict validation**
    ```bash
    skillspec validate <name> --strict
    ```

17. **Parse and explain validation results**
    For each error/warning, explain which layer:
    - **Layer 1 (Schema)**: Missing required fields, type mismatches
    - **Layer 2 (Quality)**: Forbidden patterns, vague language
    - **Layer 3 (Coverage)**: Uncovered failure modes, missing edge cases
    - **Layer 4 (Consistency)**: Cross-reference issues, broken step chains
    - **Layer 5 (Compliance)**: Policy violations (if configured)

18. **Provide fix suggestions**
    For each issue, suggest specific fixes:
    ```
    ERROR: Forbidden pattern "try to" detected

    Current:
      action: "Try to validate the input"

    Suggested fix:
      decision_rules:
        - id: validate_input
          when: "input != null"
          then: {action: validate}

    Apply this fix? [y/n]
    ```

19. **Auto-fix common issues**
    - Missing `is_default: true` on fallback rule
    - Missing edge cases for defined failure modes
    - Missing required sections with sensible defaults

20. **Re-validate until passing**
    - If fixes applied, re-run validation
    - Repeat until all errors resolved

21. **Show completion summary**
    ```
    Validation Summary:
    - Schema: PASS
    - Quality: PASS
    - Coverage: PASS
    - Consistency: PASS

    Proposal complete: skillspec/drafts/<name>/

    Next steps:
    1. Apply (generate SKILL.md): /skill-spec:apply <name>
    2. Deploy (publish): /skill-spec:deploy <name>
    ```

**Field Reference**

```yaml
spec_version: "skill-spec/1.0"
_meta:                              # optional
  content_language: en | zh | auto
  mixed_language_strategy: union | segment_detect | primary

skill:                              # required
  name: kebab-case                  # ^[a-z][a-z0-9]*(-[a-z0-9]+)*$
  version: "1.0.0"                  # semver
  purpose: string                   # 10-200 chars
  owner: string

inputs:                             # required, min 1
  - name: snake_case                # ^[a-z][a-z0-9_]*$
    type: string|number|boolean|object|array
    required: boolean
    constraints: [...]              # optional: not_empty, max_length, pattern, enum
    domain: {...}                   # optional: {type: enum|range|pattern_set|boolean|any}
    description: string             # optional
    tags: [...]                     # optional: pii, sensitive, etc.

preconditions: [string]             # required, min 1
non_goals: [string]                 # required, min 1

decision_rules:                     # required
  _config:
    match_strategy: first_match|priority|all_match
    conflict_resolution: error|warn|first_wins
  - id: snake_case
    priority: int >= 0
    is_default: boolean             # one rule MUST be default
    when: string|boolean|object
    then: {status, code, action, path, log}

steps:                              # required, min 1
  - id: snake_case
    action: string
    output: string                  # optional
    based_on: [string]              # optional
    condition: string               # optional

output_contract:                    # required
  format: json|text|markdown|yaml|binary
  schema: {...}                     # JSON Schema

failure_modes:                      # required, min 1
  - code: UPPER_SNAKE_CASE          # ^[A-Z][A-Z0-9_]*$
    retryable: boolean
    description: string             # optional
    recovery_hint: string           # optional

edge_cases:                         # required, min 1
  - case: string
    expected: {status, code}
    input_example: any              # optional
    covers_rule: string             # optional
    covers_failure: string          # optional

context:                            # optional
  works_with: [{skill, reason}]
  prerequisites: [string]
  scenarios: [{name, description}]

examples:                           # optional
  - name: string
    input: any
    output: any
    explanation: string             # optional
```

**Validation Layers Reference**

| Layer | What it checks | Common errors |
|-------|----------------|---------------|
| Layer 1: Schema | Structure, required fields, types | Missing sections, wrong types |
| Layer 2: Quality | Forbidden patterns, vague language | "try to", "as needed", "appropriate" |
| Layer 3: Coverage | Edge cases, failure mode coverage | Uncovered failure modes |
| Layer 4: Consistency | Cross-references, step chains | Broken based_on references |
| Layer 5: Compliance | Enterprise policies | Policy-specific violations |

**Quality Reports**

Generate detailed quality reports for analysis and auditing:

```bash
# Summary report (default)
skillspec report <name>
skillspec report <name> --summary

# Specific report types
skillspec report <name> --quality      # forbidden patterns, vague language
skillspec report <name> --coverage     # structural/behavioral coverage scores
skillspec report <name> --tags         # tag taxonomy analysis (pii, sensitive, etc.)
skillspec report <name> --compliance   # enterprise policy compliance
skillspec report <name> --consistency  # cross-reference consistency

# With evidence from diary
skillspec report <name> --with-evidence

# Output options
skillspec report <name> --format json
skillspec report <name> --output-dir ./reports  # generates both Markdown + JSON

# Compliance with custom policy
skillspec report <name> --compliance --policy ./policies/enterprise.yaml
```

**Reference**
- `skillspec list` - check existing skills
- `skillspec show <name>` - view spec
- `skillspec validate <name> --strict` - validate
- `skillspec validate <name> --strict --format json` - machine-readable output
- `skillspec validate <name> --strict --policy <path>` - with enterprise policy
- `skillspec report <name>` - quality report (summary)
- `skillspec report <name> --quality` - quality analysis
- `skillspec report <name> --coverage` - coverage analysis
- `skillspec report <name> --compliance` - compliance report
- `skillspec report <name> --with-evidence` - include diary evidence
<!-- SKILL-SPEC:END -->
