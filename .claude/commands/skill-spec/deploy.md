---
name: "Skill-Spec: Deploy"
description: "Publish skill from drafts/ to skills/ directory"
---

<!-- SKILL-SPEC:START -->
**Directory Structure**
```
skillspec/drafts/<name>/   - Development (spec.yaml + SKILL.md)
skillspec/skills/<name>/   - Published archive (spec.yaml + SKILL.md)
<user-specified>/          - Runtime target (SKILL.md + resources only)
```

**Guardrails**
- Always validate before deploying
- Confirm with user before moving files
- Archive old version if exists
- Runtime deployment excludes spec.yaml (only SKILL.md + resources)

**Arguments**
- `$ARGUMENTS` contains: `<skill-name> [--target <path>]`

**Steps**

1. **Determine skill name and target**
   - Extract skill name from `$ARGUMENTS`
   - Extract `--target` path if provided
   - If skill name not provided, run `skillspec list --drafts` and ask user to select

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

   Old version will be archived to:
   skillspec/archive/YYYY-MM-DD-<name>/

   Proceed? [y/n]
   ```

5. **Confirm publish (drafts → skills)**
   ```
   Ready to publish: <name>

   From: skillspec/drafts/<name>/
   To:   skillspec/skills/<name>/

   This will move the complete skill package:
   - spec.yaml (for version control)
   - SKILL.md (generated skill)
   - resources/ and scripts/ if present

   Proceed? [y/n]
   ```

6. **Execute publish**
   ```bash
   skillspec publish <name>
   ```

7. **Deploy to runtime target (if --target specified)**
   If target path provided:
   ```
   Deploy to runtime: <target>/<name>/

   Files to copy (spec.yaml excluded):
   - SKILL.md
   - resources/ (if present)
   - scripts/ (if present)

   Proceed? [y/n]
   ```

   Copy only runtime files:
   ```bash
   mkdir -p <target>/<name>
   cp skillspec/skills/<name>/SKILL.md <target>/<name>/
   # Copy resources/ and scripts/ if present
   ```

8. **Verify**
   ```bash
   skillspec list
   ```

9. **Show completion**
   ```
   Published: skillspec/skills/<name>/
   ```
   If target was specified:
   ```
   Deployed: <target>/<name>/ (SKILL.md + resources only)
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
