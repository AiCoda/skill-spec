---
name: "Skill-Spec: Migrate"
description: "Migrate an existing SKILL.md to spec.yaml format"
---

<!-- SKILL-SPEC:START -->
**Guardrails**
- Preserve original SKILL.md content
- Generate TODO items for sections that need manual review
- Validate migrated spec before completing

**Arguments**
- `$ARGUMENTS` contains the path to the SKILL.md file or directory

**Steps**

1. **Determine source path**
   - Extract from `$ARGUMENTS`
   - If directory provided, look for `SKILL.md` inside
   - If not provided, ask user for path

2. **Validate source exists**
   - Check file exists
   - If not found: "SKILL.md not found at <path>"

3. **Analyze existing SKILL.md**
   Read the file and identify:
   - Frontmatter (name, description)
   - Sections present (Purpose, Inputs, etc.)
   - Decision logic
   - Edge cases mentioned
   - Error handling

4. **Show migration preview**
   ```
   Migrating: <path>/SKILL.md

   Detected sections:
   - Purpose: Found
   - Inputs: Found (3 inputs)
   - Decision Criteria: Found (2 rules)
   - Edge Cases: Found (4 cases)
   - Error Handling: Missing

   Will generate:
   - spec.yaml with extracted data
   - TODO items for missing/incomplete sections

   Proceed? [y/n]
   ```

5. **Run migration**
   ```bash
   skillspec migrate <path>
   ```

6. **Review migration result**
   Show the generated spec.yaml and highlight:
   - Successfully extracted sections
   - Sections with TODO markers
   - Warnings about ambiguous content

7. **Interactive refinement**
   For each TODO item:
   ```
   TODO: failure_modes section is incomplete

   Original content:
     "Returns error on invalid input"

   Suggested spec:
     failure_modes:
       - code: INVALID_INPUT
         retryable: false
         description: "Input validation failed"

   Accept this suggestion? [y/n/edit]
   ```

8. **Validate migrated spec**
   ```bash
   skillspec validate <name> --strict
   ```

9. **Fix validation errors**
   - Apply same fix workflow as proposal command
   - Re-validate until passing

10. **Show completion**
    ```
    Migration complete: skillspec/drafts/<name>/

    Generated:
    - spec.yaml (migrated from SKILL.md)

    TODO items resolved: 5/5

    Original SKILL.md preserved at: <original-path>

    Next steps:
    1. Review spec.yaml
    2. Generate new SKILL.md: /skill-spec:apply <name>
    3. Compare with original and verify
    4. Deploy: /skill-spec:deploy <name>
    ```

**Section Extraction Mapping**

| SKILL.md Section | Spec Section |
|------------------|--------------|
| Frontmatter: name | skill.name |
| Frontmatter: description | skill.purpose |
| ## Purpose | skill.purpose |
| ## Inputs | inputs |
| ## Prerequisites | preconditions |
| ## What This Skill Does NOT Do | non_goals |
| ## Decision Criteria | decision_rules |
| ## Workflow | steps |
| ## Edge Cases | edge_cases |
| ## Output Format | output_contract |
| ## Error Handling | failure_modes |
| ## Works Well With | context.works_with |
| ## Examples | examples |

**Common Migration Issues**

| Issue | Resolution |
|-------|------------|
| Vague decision rules | Convert to explicit when/then structure |
| Missing error codes | Generate UPPER_SNAKE_CASE codes |
| Implicit edge cases | Extract from prose to structured format |
| No input constraints | Infer from description or ask user |
| Mixed content language | Set `_meta.content_language` appropriately |

**Reference**
- `skillspec migrate <path>` - CLI migrate command
- `skillspec migrate <path> -o <output>` - specify output path
- `skillspec migrate <path> --force` - overwrite existing spec.yaml
- `skillspec migrate <path> --format json` - output as JSON
- `skillspec validate <name> --strict` - validate after migration
<!-- SKILL-SPEC:END -->
