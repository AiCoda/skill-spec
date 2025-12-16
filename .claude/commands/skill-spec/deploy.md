---
name: "Skill-Spec: Deploy"
description: "Publish skill from drafts/ to skills/ directory"
---

<!-- SKILL-SPEC:START -->
**Guardrails**
- Always validate before deploying
- Confirm with user before moving files
- Archive old version if exists

**Arguments**
- `$ARGUMENTS` contains the skill name to deploy

**Steps**

1. **Determine skill name**
   - Extract from `$ARGUMENTS`
   - If not provided, run `skillspec list --drafts` and ask user to select

2. **Validate skill exists**
   - Check `skillspec/drafts/<name>/` exists
   - If not found: "No draft found. Use /skill-spec:proposal <name> to create one."

3. **Run validation**
   ```bash
   skillspec validate <name> --strict
   ```
   - If fails, show errors and stop
   - Suggest: "Fix with /skill-spec:proposal <name>"

4. **Check for existing version**
   If `skillspec/skills/<name>/` exists:
   ```
   Existing version: 1.0.0
   New version: 1.1.0

   Changes:
   - Added 2 new inputs
   - Modified 3 decision rules
   - Added 1 edge case

   Old version will be archived to:
   skillspec/archive/YYYY-MM-DD-<name>/

   Proceed? [y/n]
   ```

5. **Confirm deployment**
   ```
   Ready to deploy: <name>

   From: skillspec/drafts/<name>/
   To:   skillspec/skills/<name>/

   This will:
   - Move spec.yaml to skills/
   - Move SKILL.md to skills/
   - Move scripts/ and resources/ if present

   Proceed? [y/n]
   ```

6. **Execute deployment**
   ```bash
   skillspec publish <name>
   ```

7. **Verify deployment**
   ```bash
   skillspec list
   skillspec validate <name> --strict
   ```

8. **Show completion**
   ```
   Deploy complete: skillspec/skills/<name>/

   The skill is now published and available for use.

   To deploy to another project:
     skillspec deploy bundle <name>
     skillspec deploy preflight <name> --target=/path/to/project

   To view the deployed skill:
     skillspec show <name>
   ```

**Deployment Commands**

After publishing to skills/, you can deploy to other projects:

1. **Create bundle** (portable package):
   ```bash
   skillspec deploy bundle <name>
   skillspec deploy bundle <name> --include-optional  # include tests/examples
   skillspec deploy bundle <name> -o /path/to/output
   ```

2. **Pre-flight check** (verify before deploy):
   ```bash
   skillspec deploy preflight <name>
   skillspec deploy preflight <name> --target=production
   ```

3. **Manage targets**:
   ```bash
   skillspec deploy target list
   skillspec deploy target add <name> --url <url> --auth api_key
   skillspec deploy target remove <name>
   ```

4. **Check status**:
   ```bash
   skillspec deploy status <name>
   ```

**Reference**
- `skillspec list` - see all skills
- `skillspec show <name>` - inspect skill
- `skillspec publish <name>` - CLI publish command
- `skillspec archive <name>` - archive published skill
- `skillspec deploy bundle <name>` - create deployment bundle
- `skillspec deploy preflight <name>` - run pre-flight checks
- `skillspec deploy target list` - list deployment targets
- `skillspec deploy status <name>` - check deployment status
<!-- SKILL-SPEC:END -->
