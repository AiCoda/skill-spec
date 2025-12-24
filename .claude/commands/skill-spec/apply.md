---
name: "Skill-Spec: Apply"
description: "Generate SKILL.md and implementation artifacts from spec.yaml (v1.2 with agentskills.io support)"
---

<!-- SKILL-SPEC:START -->
**Guardrails**
- Validate spec before generating
- Preserve manual blocks (marked with `<!-- skillspec:manual -->`)
- Create scripts/resources only when needed

**Arguments**
- `$ARGUMENTS` contains the skill name to apply

**Steps**

1. **Determine skill name**
   - Extract from `$ARGUMENTS`
   - If not provided, run `skillspec list` and ask user to select

2. **Validate before generating**
   ```bash
   skillspec validate <name> --strict
   ```
   - If fails, suggest: "Fix with /skill-spec:proposal <name>"

3. **Confirm scope**
   ```
   Applying spec: <name>

   Will generate:
   - SKILL.md (main documentation)
   - scripts/ (if steps reference scripts)
   - resources/ (if templates/configs needed)

   Proceed? [y/n]
   ```

4. **Generate SKILL.md**
   ```bash
   skillspec generate <name>
   ```
   - Preserves existing manual blocks

5. **Review generated content**
   Show key sections:
   - ## Purpose
   - ## Decision Criteria
   - ## Edge Cases

6. **Offer enhancements**
   ```
   Would you like me to enhance any sections?
   - Add more examples to Decision Criteria
   - Expand Edge Cases with more detail
   ```

7. **Create implementation artifacts (if needed)**
   Based on spec's `steps` section:

   **scripts/** - Action scripts:
   - Create stub files for step actions (e.g., `validate.py`, `process.sh`)
   - Include input/output types from spec
   - Add docstrings with proper signatures

   **resources/** - Static resources:
   - Templates (e.g., `output_template.md`)
   - Config files (e.g., `config.yaml`)
   - Data files referenced by steps

   **references/** - External documentation:
   - API docs for external tools
   - Links to dependencies
   - Related skill documentation

   Ask user:
   ```
   The spec references these actions:
   - validate_input (step: validate)
   - process_data (step: process)

   Create stub scripts for these? [y/n]
   ```

8. **Run tests**
   ```bash
   skillspec test <name>
   ```

9. **Show completion**
   ```
   Apply complete: skillspec/drafts/<name>/

   Generated:
   - SKILL.md (main documentation)
   - scripts/validate.py (stub)
   - scripts/process.py (stub)
   - resources/config.yaml
   - references/external_api.md

   Directory structure:
   skillspec/drafts/<name>/
   +-- spec.yaml
   +-- SKILL.md
   +-- scripts/
   |   +-- validate.py
   |   +-- process.py
   +-- resources/
   |   +-- config.yaml
   +-- references/
       +-- external_api.md

   Next steps:
   1. Review SKILL.md
   2. Implement script stubs with actual logic
   3. Deploy: /skill-spec:deploy <name>
   ```

**Section Mapping**

| Spec Section | SKILL.md Section |
|--------------|------------------|
| skill.name | YAML frontmatter: name |
| skill.purpose | YAML frontmatter: description |
| skill.license | YAML frontmatter: license (v1.2) |
| skill.compatibility | YAML frontmatter: compatibility (v1.2) |
| skill.allowed_tools | YAML frontmatter: allowed-tools (v1.2) |
| inputs | ## Inputs |
| preconditions | ## Prerequisites |
| non_goals | ## What This Skill Does NOT Do |
| triggers | ## Triggers (v1.1) |
| boundaries | ## Boundaries (v1.1) |
| decision_rules | ## Decision Criteria |
| steps | ## Workflow |
| behavioral_flow | ## Behavioral Flow (v1.1) |
| edge_cases | ## Edge Cases |
| output_contract | ## Output Format |
| failure_modes | ## Error Handling |
| anti_patterns | ## Anti-Patterns (v1.1) |
| context.works_with | ## Works Well With |
| examples | ## Examples |

**Preservation Protocol**

When regenerating SKILL.md, the following rules apply:

1. **Generated blocks** are wrapped in markers:
   ```
   <!-- skillspec:generated:start -->
   ... auto-generated content ...
   <!-- skillspec:generated:end -->
   ```

2. **Manual blocks** can be added and will be preserved:
   ```
   <!-- skillspec:manual:start -->
   ... your custom content ...
   <!-- skillspec:manual:end -->
   ```

3. **Options**:
   - `--force`: Overwrite all content including manual blocks
   - `--no-preserve`: Generate without preservation markers (legacy)

**Diary System (Execution Tracking)**

Track skill execution for compliance and debugging:

1. **Initialize diary**:
   ```bash
   skillspec diary init
   ```

2. **View execution summary**:
   ```bash
   skillspec diary summary <name>
   skillspec diary summary <name> --format json
   ```

3. **List recent events**:
   ```bash
   skillspec diary events <name>
   skillspec diary events <name> --limit 20
   skillspec diary events <name> --type test_run
   skillspec diary events <name> --type production_execution
   ```

4. **Prune old events**:
   ```bash
   skillspec diary prune <name> --keep-days 30
   skillspec diary prune --all --keep-days 90
   ```

**Reference**
- `skillspec show <name>` - view spec
- `skillspec generate <name>` - generate with preservation
- `skillspec generate <name> --force` - overwrite including manual blocks
- `skillspec generate <name> --no-preserve` - generate without markers
- `skillspec check-consistency <name>` - verify generated blocks match spec
- `skillspec check-format <name>` - check SKILL.md format compliance
- `skillspec test <name>` - test implementation against spec
- `skillspec diary init` - initialize diary system
- `skillspec diary summary <name>` - execution summary
- `skillspec diary events <name>` - list recent events
<!-- SKILL-SPEC:END -->
