# Skill-Spec Instructions

Instructions for AI assistants creating skills using spec-driven development.

## TL;DR Quick Checklist

- Read this file before creating any skill
- **Use `/skill-spec:proposal <name>` to start interactive creation**
- AI collects requirements through conversation, then generates and validates spec.yaml
- Apply: `/skill-spec:apply <name>` to generate SKILL.md
- Test: `skillspec test <name>`
- Deploy: `/skill-spec:deploy <name>` to publish

## Slash Commands (Recommended)

| Command | Purpose |
|---------|---------|
| `/skill-spec:proposal <name>` | Interactive skill creation - AI collects requirements, generates and validates spec.yaml |
| `/skill-spec:apply <name>` | Generate SKILL.md from validated spec |
| `/skill-spec:deploy <name>` | Publish skill from drafts/ to skills/ directory |
| `/skill-spec:migrate <path>` | Migrate existing SKILL.md to spec.yaml |

## When to Use Skill-Spec

Use the Skill-Spec workflow when:
- Creating any new skill
- Modifying existing skill behavior
- Adding new capability to a skill

**Triggers (examples):**
- "Help me create a skill for X"
- "I need a skill that does Y"
- "Create a new skill to handle Z"

**Loose matching:**
- Contains: `skill`, `create`, `new`
- With purpose description

## Section Taxonomy v1.0

### Required Sections

**Core Sections (8 required):**
1. `skill` - Metadata (name, version, purpose, owner)
2. `inputs` - Input contract with domain support
3. `preconditions` - Prerequisites that must be true
4. `non_goals` - What this skill explicitly does NOT do
5. `decision_rules` - Explicit decision criteria with priority
6. `steps` - Execution flow
7. `output_contract` - Verifiable output schema
8. `failure_modes` - Designed failure scenarios

**Coverage Sections (1 required):**
9. `edge_cases` - Boundary conditions and edge cases

**Context Sections (1 optional):**
10. `context` - Collaboration info (works_with, prerequisites, scenarios)

## Three-Stage Workflow

### Stage 1: Drafting

Create spec when you need to add or modify a skill.

**Workflow:**
1. Run `skillspec init <name>` to scaffold
2. Fill spec.yaml with all 9 required sections
3. Run `skillspec validate <name> --strict`
4. Do NOT proceed to implementation until validation passes

### Stage 2: Implementing

Track these steps as TODOs:
1. Read spec.yaml - Understand what's being built
2. Create SKILL.md - Map spec sections to SKILL.md structure
3. Create scripts/ - Implement required scripts
4. Create references/ - Add reference documentation
5. Run `skillspec test <name>` - Verify implementation matches spec

### Stage 3: Publishing

After testing:
- Run `skillspec publish <name>` to move from drafts/ to skills/
- Old versions archived to archive/YYYY-MM-DD-<name>/

## Spec.yaml Required Sections

### 1. skill (Metadata)

```yaml
skill:
  name: "kebab-case-verb-object"  # e.g., "extract-api-contract"
  version: "1.0.0"
  purpose: "Single sentence, third-party can repeat without distortion"
  owner: "team-name"
```

### 2. inputs (Input Contract)

```yaml
inputs:
  - name: input_name                    # snake_case, pattern: ^[a-z][a-z0-9_]*$
    type: string                        # string | number | boolean | object | array
    required: true                      # boolean
    constraints:                        # optional
      - not_empty                       # simple: not_empty, not_null, positive, non_negative
      - max_length: 500                 # extended: max_length, min_length, max_value, min_value, pattern, enum
    domain:                             # optional, for coverage analysis
      type: enum                        # enum | range | pattern_set | boolean | any
      values: ["A", "B", "C"]           # for enum
      # min: 0                          # for range
      # max: 100                        # for range
      # patterns: ["*.py"]              # for pattern_set
    description: "Precise semantic definition"  # optional
    tags: ["pii", "sensitive"]          # optional, data classification
```

**Constraint Options:**
- Simple: `not_empty`, `not_null`, `positive`, `non_negative`
- Extended: `{max_length: N}`, `{min_length: N}`, `{max_value: N}`, `{min_value: N}`, `{pattern: "regex"}`, `{enum: ["a","b"]}`

**Domain Types:**
- `enum`: discrete values, requires `values: [...]`
- `range`: numeric range, requires `min` and `max`
- `pattern_set`: string patterns, requires `patterns: [...]`
- `boolean`: true/false only
- `any`: no specific domain (default)

### 3. preconditions (Prerequisites)

```yaml
preconditions:
  - "Input is pre-validated"
  - "User has required permissions"
```

### 4. non_goals (Boundaries)

```yaml
non_goals:
  - "Does not infer missing data"
  - "Does not call external APIs"
  - "Does not modify source files"
```

### 5. decision_rules (Explicit Decisions)

```yaml
decision_rules:
  _config:
    match_strategy: first_match     # first_match | priority | all_match
    conflict_resolution: error      # error | warn | first_wins

  - id: rule_empty_input            # snake_case, pattern: ^[a-z][a-z0-9_]*$
    priority: 10                    # int >= 0, higher = checked first
    when: "len(input) == 0"         # string | boolean | object (JSON Logic)
    then:                           # action to take
      status: error                 # success | error | skip | delegate
      code: EMPTY_INPUT             # optional, error code
      # action: "do_something"      # optional, action name
      # path: "error_path"          # optional, execution path
      # log: warning                # optional, debug | info | warning | error

  - id: rule_low_confidence
    priority: 5
    when: "input.type == 'A' AND confidence < 0.7"
    then: {status: error, code: INSUFFICIENT_CONFIDENCE}

  - id: rule_default
    priority: 0
    is_default: true                # REQUIRED: one rule must have this
    when: true                      # default rule uses `when: true`
    then: {status: success, path: default}
```

**Rule Fields:**
- `id`: snake_case identifier (required)
- `priority`: int >= 0 (default: 0, higher = checked first)
- `is_default`: boolean (default: false, one rule MUST be default)
- `when`: condition expression (string, boolean, or JSON Logic object)
- `then`: action object with `status`, `code`, `action`, `path`, `log`

**Allowed operators:** AND, OR, NOT, ==, !=, <, >, <=, >=
**Allowed functions:** len(), contains(), matches(), is_empty(), is_null()

### 6. steps (Execution Flow)

```yaml
steps:
  - id: validate                    # snake_case, pattern: ^[a-z][a-z0-9_]*$
    action: validate_input          # required, what to do
    output: validated_input         # optional, variable name for result
  - id: process
    action: apply_decision_rules
    output: decision_result
    based_on: [validated_input]     # optional, inputs from previous steps
    condition: "validated_input.valid == true"  # optional, when to execute
  - id: render
    action: generate_output
    based_on: [decision_result]
```

**Step Fields:**
- `id`: snake_case identifier (required)
- `action`: string describing what to do (required)
- `output`: variable name for step result (optional)
- `based_on`: list of outputs from previous steps (optional)
- `condition`: expression for conditional execution (optional)

### 7. output_contract (Verifiable Output)

```yaml
output_contract:
  format: json                      # json | text | markdown | yaml | binary
  schema:                           # JSON Schema object
    type: object
    required: [status]
    properties:
      status: {enum: [success, error]}
      result: {type: object}
      error_code: {type: string}
```

**Output Format Options:**
- `json`: JSON object output
- `text`: Plain text output
- `markdown`: Markdown formatted output
- `yaml`: YAML formatted output
- `binary`: Binary data output

### 8. failure_modes (Failure Design)

```yaml
failure_modes:
  - code: INVALID_INPUT             # UPPER_SNAKE_CASE, pattern: ^[A-Z][A-Z0-9_]*$
    retryable: false                # can this error be retried?
    description: "Input validation failed"  # optional, human-readable
    recovery_hint: "Check input format"     # optional, how to fix
  - code: AMBIGUOUS_CASE
    retryable: true
    description: "Multiple rules matched"
    recovery_hint: "Provide more specific input"
```

**Failure Mode Fields:**
- `code`: UPPER_SNAKE_CASE error code (required)
- `retryable`: boolean (required)
- `description`: human-readable explanation (optional)
- `recovery_hint`: suggestion for how to fix (optional)

### 9. edge_cases (Coverage - Required)

```yaml
edge_cases:
  - case: empty_input               # descriptive name (required)
    expected:                       # expected behavior (required)
      status: error
      code: EMPTY_INPUT
    input_example: ""               # optional, concrete input that triggers this
    covers_failure: EMPTY_INPUT     # optional, which failure_mode this tests
    covers_rule: rule_empty_input   # optional, which decision_rule this tests
  - case: conflicting_signals
    expected: {action: prefer_rule_1, log: warning}
    input_example: {type: "A", confidence: 0.5}
  - case: unicode_input
    expected: {status: success, normalized: true}
    input_example: "Hello world"
```

**Edge Case Fields:**
- `case`: descriptive name for the edge case (required)
- `expected`: object describing expected behavior (required)
- `input_example`: concrete input that triggers this case (optional but recommended)
- `covers_rule`: which decision_rule id this tests (optional)
- `covers_failure`: which failure_mode code this tests (optional)

### 10. context (Optional)

```yaml
context:
  works_with:                       # optional, related skills
    - skill: code-analyzer          # skill name (required in item)
      reason: "Provides code analysis results as input"  # reason (required in item)
  prerequisites:                    # optional, what user needs to do first
    - "Codebase has been indexed"
    - "User has required permissions"
  scenarios:                        # optional, typical usage scenarios
    - name: "code-review-workflow"  # scenario name (required in item)
      description: "Use after code-analyzer in review flow"  # (required in item)
```

**Context Fields:**
- `works_with`: list of related skills, each with `skill` and `reason`
- `prerequisites`: list of things user needs to do first
- `scenarios`: list of usage scenarios, each with `name` and `description`

### 11. examples (Optional, recommended for Anthropic format)

```yaml
examples:
  - name: "Basic usage"             # example name (required)
    input:                          # example input values (required)
      user_input: "test value"
    output:                         # expected output (required)
      status: success
      result: {processed: true}
    explanation: "Shows basic successful processing"  # optional
```

**Example Fields:**
- `name`: descriptive example name (required)
- `input`: example input values (required)
- `output`: expected output (required)
- `explanation`: explanation of what happens (optional)

### _meta (Optional, for i18n)

```yaml
_meta:
  content_language: en              # en | zh | auto
  mixed_language_strategy: union    # union | segment_detect | primary
```

**Meta Config:**
- `content_language`: primary content language
- `mixed_language_strategy`: how to handle mixed language validation

## Forbidden Patterns

These patterns indicate missing decision criteria. **Never use:**

| Category | English Examples | Chinese Examples |
|----------|------------------|------------------|
| VAGUE_CONDITION | as needed, if appropriate, when necessary | as needed, if appropriate |
| VAGUE_ACTION | try to, help, assist, attempt to | try to, help, assist |
| VAGUE_DEGREE | generally, typically, usually, often | generally, typically |
| HEDGE_WORDS | might, could, should consider, may | might, could |
| WEAK_VERBS | consider, support, ensure | consider, ensure |

**Always replace with explicit decision_rules.**

Bad:
```yaml
steps:
  - action: "Try to extract the API contract if appropriate"
```

Good:
```yaml
decision_rules:
  - id: extract_api
    when: "file.extension == '.py' AND contains(content, 'def ')"
    then: {action: extract_functions}
```

## CLI Commands

```bash
skillspec list                    # List all skills (drafts + published)
skillspec init <name>             # Scaffold new skill in drafts/
skillspec show <name>             # Display skill spec
skillspec validate <name>         # Validate spec (basic)
skillspec validate <name> --strict # Validate spec (all layers)
skillspec generate <name>         # Generate SKILL.md from spec
skillspec test <name>             # Test implementation against spec
skillspec publish <name>          # Move from drafts/ to skills/
skillspec migrate <path>          # Migrate existing SKILL.md to spec
skillspec report <name>           # Full quality report
skillspec deploy <name> --target  # Deploy to target directory
```

## Spec to SKILL.md Mapping

| Spec Section | SKILL.md Section |
|--------------|------------------|
| skill.name | YAML frontmatter: name |
| skill.purpose + triggers | YAML frontmatter: description |
| skill.purpose | ## Purpose |
| inputs | ## Inputs |
| non_goals | ## What This Skill Does NOT Do |
| preconditions | ## Prerequisites |
| decision_rules | ## Decision Criteria / ## When to Use |
| steps | ## Workflow |
| edge_cases | ## Edge Cases |
| output_contract | ## Output Format |
| failure_modes | ## Error Handling |
| context.works_with | ## Works Well With |

## Interactive Creation Flow (via /skill-spec:proposal)

When AI receives `/skill-spec:proposal <name>`, it should:

### Phase 1: Purpose Discovery
```
AI: "What should the '<name>' skill do? Describe its main purpose in one sentence."
User: "It should extract API contracts from OpenAPI specs"
AI: "Got it. So the purpose is: 'Extract and validate API contracts from OpenAPI specification files.'"
```

### Phase 2: Input Collection
```
AI: "What inputs does this skill need? For each input, tell me:
     - Name (snake_case)
     - Type (string, number, object, array, boolean)
     - Required or optional
     - Any constraints (not_empty, max_length, etc.)"
User: "It needs an openapi_spec (string, required, must be valid JSON/YAML)"
AI: "Added input: openapi_spec (string, required). Any more inputs?"
```

### Phase 3: Decision Rules
```
AI: "What decisions does this skill make? Think about:
     - What conditions trigger different behaviors?
     - What should happen when something is invalid?
     - Are there priority rules?"
User: "If spec is invalid JSON, return error. If missing required fields, return warning..."
AI: "I'll create these rules:
     - rule_invalid_json: when parsing fails -> error INVALID_JSON
     - rule_missing_fields: when required fields missing -> warning
     - rule_default: process normally"
```

### Phase 4: Edge Cases
```
AI: "What edge cases should be handled?
     - Empty input?
     - Malformed data?
     - Boundary conditions?"
User: "Empty spec should error, circular refs should warn..."
AI: "Added edge cases: empty_input, circular_reference, oversized_spec"
```

### Phase 5: Non-Goals & Failure Modes
```
AI: "What should this skill explicitly NOT do?"
User: "It shouldn't modify the original file or make network calls"
AI: "Added non_goals. What error codes should we define?"
```

### Phase 6: Generation & Validation
```
AI: "Based on our conversation, here's the complete spec.yaml:
     [Shows generated spec]

     Does this look correct? Any adjustments needed?"
User: "Looks good!" / "Change X to Y"
AI: [Writes spec.yaml to drafts/<name>/spec.yaml]
AI: [Runs: skillspec validate <name> --strict]
AI: "Validation passed! Next steps:
     1. Apply: /skill-spec:apply <name>  (generates SKILL.md)
     2. Review the generated SKILL.md
     3. Deploy: /skill-spec:deploy <name>  (publishes to skills/)"
```

## Quality Checklist

### Draft -> Implement

- [ ] All 9 required sections filled (8 Core + 1 Coverage)
- [ ] No forbidden patterns detected
- [ ] decision_rules cover all input combinations
- [ ] edge_cases cover boundary conditions
- [ ] `skillspec validate --strict` passes

### Implement -> Publish

- [ ] SKILL.md follows spec structure
- [ ] All scripts tested and working
- [ ] References complete
- [ ] `skillspec test` passes

## Validation Layers

The `--strict` flag runs all validation layers:

1. **Schema Validation** - Structure and required fields
2. **Quality Validation** - Forbidden patterns, expression parsing
3. **Coverage Validation** - Decision rules coverage, edge cases
4. **Consistency Validation** - Cross-reference checks
5. **Compliance Validation** - Enterprise policies (if configured)

## Examples

### Minimal Valid Spec (All Required Fields)

```yaml
spec_version: "skill-spec/1.0"

# Optional: i18n configuration
# _meta:
#   content_language: en
#   mixed_language_strategy: union

skill:
  name: "hello-world"               # kebab-case
  version: "1.0.0"                  # semver
  purpose: "Greet the user with their name"  # 10-200 chars
  owner: "demo-team"

inputs:
  - name: user_name                 # snake_case
    type: string
    required: true
    constraints: [not_empty]
    # domain: {type: any}           # optional
    # description: "User's name"    # optional
    # tags: []                      # optional

preconditions:
  - "User name is provided"

non_goals:
  - "Does not validate name format"
  - "Does not store greetings"

decision_rules:
  _config:
    match_strategy: first_match
    conflict_resolution: error

  - id: rule_empty_name
    priority: 10
    when: "is_empty(user_name)"
    then: {status: error, code: EMPTY_NAME}

  - id: rule_default
    priority: 0
    is_default: true                # REQUIRED: one rule must have this
    when: true
    then: {status: success, action: generate_greeting}

steps:
  - id: validate
    action: validate_input
    output: validated_name
  - id: greet
    action: generate_greeting
    output: greeting_message
    based_on: [validated_name]
    # condition: "validated_name != null"  # optional

output_contract:
  format: text                      # json | text | markdown | yaml | binary
  schema:
    type: string
    pattern: "^Hello, .+!$"

failure_modes:
  - code: EMPTY_NAME                # UPPER_SNAKE_CASE
    retryable: false
    description: "User name was empty"
    # recovery_hint: "Provide a non-empty name"  # optional

edge_cases:
  - case: empty_name
    expected: {status: error, code: EMPTY_NAME}
    input_example: ""               # optional but recommended
    covers_failure: EMPTY_NAME      # optional
    covers_rule: rule_empty_name    # optional
  - case: long_name
    expected: {status: success, truncated: false}
    input_example: "A very long name that exceeds normal length"

# Optional sections
# context:
#   works_with:
#     - skill: name-validator
#       reason: "Can validate names before greeting"
#   prerequisites:
#     - "User input is available"
#   scenarios:
#     - name: "welcome-flow"
#       description: "Used in user welcome workflow"

# examples:
#   - name: "Basic greeting"
#     input: {user_name: "Alice"}
#     output: "Hello, Alice!"
#     explanation: "Simple greeting with valid name"
```
