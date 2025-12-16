# Skill-Spec Project Conventions

This document defines project-level conventions for skill development.

## Directory Structure

```
skillspec/
├── SKILL_AGENTS.md      # AI guidance (read first)
├── project.md           # This file
├── schema/
│   └── skill_spec_v1.json
├── templates/
│   ├── spec.yaml
│   └── messages/
│       ├── en.yaml
│       └── zh.yaml
├── patterns/
│   ├── violation_categories.yaml
│   ├── forbidden_patterns_en.yaml
│   ├── forbidden_patterns_zh.yaml
│   └── scan_scope.yaml
├── taxonomy/
│   └── data-classification-v1.yaml
├── policies/
│   └── enterprise-security-v1.yaml
├── drafts/              # Stage 1: Drafts
│   └── <skill-name>/
│       └── spec.yaml
├── skills/              # Stage 2-3: Implemented
│   └── <skill-name>/
│       ├── spec.yaml    # Source spec
│       ├── SKILL.md     # Generated + manual content
│       ├── scripts/
│       ├── references/
│       └── assets/
└── archive/             # Old versions
    └── YYYY-MM-DD-<name>/
```

## Naming Conventions

### Skill Names
- Use kebab-case: `extract-api-contract`, `code-review-assistant`
- Start with a verb: `extract-`, `analyze-`, `generate-`, `validate-`
- Be specific: `extract-api-contract` not `api-helper`

### File Names
- spec.yaml (always lowercase)
- SKILL.md (uppercase, matches Claude convention)
- Scripts: snake_case.py

## Version Scheme

Use semantic versioning: `MAJOR.MINOR.PATCH`

- MAJOR: Breaking changes to inputs/outputs
- MINOR: New features, backward compatible
- PATCH: Bug fixes

## Language Configuration

### Content Language

Spec content can be written in:
- `en` - English
- `zh` - Chinese
- `auto` - Auto-detect (uses union strategy)

```yaml
_meta:
  content_language: "zh"
  mixed_language_strategy: "union"
```

### Report Language

CLI reports can be generated in different languages:

```bash
skillspec report <name> --locale=en
skillspec report <name> --locale=zh
```

## String Constraints

### Default Length Mode

Project-wide default for string constraints:

```yaml
# In project.yaml
constraints:
  default_length_mode: "chars"  # chars | tokens | info_units
```

- `chars` - Character count (default)
- `tokens` - Token count (for LLM context)
- `info_units` - Normalized information units (CJK = 2, Latin = 1)

Override in individual specs with `override_reason`:

```yaml
inputs:
  - name: description
    constraints:
      - max_length:
          value: 500
          mode: tokens
          override_reason: "LLM context window limit"
```

## Quality Standards

### Required Validation

All skills must pass:
1. Schema validation (structure)
2. Quality validation (no forbidden patterns)
3. Coverage validation (edge cases covered)
4. Consistency validation (cross-references valid)

### Strict Mode

`--strict` adds:
- Anthropic format compliance
- Enterprise policy compliance (if configured)
- Tag taxonomy validation

## Integration

### With skill-creator

skill-creator calls skillspec commands:
1. `skillspec init <name>` during scaffolding
2. `skillspec validate --strict` before packaging
3. `skillspec generate` for SKILL.md creation

### With CI/CD

```yaml
# .github/workflows/skill-validation.yaml
- name: Validate skills
  run: skillspec validate --all --strict

- name: Generate coverage report
  run: skillspec report --all --coverage --format=json
```

## Policies

### Default Policy

Configure default policy in project.yaml:

```yaml
compliance:
  default_policy: "policies/enterprise-security-v1.yaml"
```

This policy is automatically applied in `--strict` mode.

### Policy Composition

Multiple policies can be combined:

```bash
skillspec validate <name> --policy=security.yaml --policy=gdpr.yaml
```

## Archive Policy

Old versions are archived to `archive/YYYY-MM-DD-<name>/` when:
- A new version is published
- A skill is explicitly archived

Archive retention: Indefinite (manual cleanup)
