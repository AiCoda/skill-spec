# Skill-Spec

Spec-driven skill development framework for building high-quality, reliable AI skills.

规范驱动的技能开发框架，用于构建高质量、可靠的 AI 技能。

---

## Quick Start / 快速开始

### Installation / 安装

```bash
pip install skillspec
```

### Setup in Your Project / 在项目中初始化

```bash
cd my-project
skillspec setup
```

This command automatically:
- Detects your AI tools (Claude Code, Cursor, Cline, Codex)
- Creates `skillspec/` directory structure
- Installs slash commands for interactive skill creation
- Creates `project.yaml` for configuration

此命令自动完成：
- 检测你的 AI 工具（Claude Code、Cursor、Cline、Codex）
- 创建 `skillspec/` 目录结构
- 安装斜杠命令用于交互式技能创建
- 创建 `project.yaml` 配置文件

### Create Your First Skill / 创建第一个技能

In Claude Code (or your AI tool), type:

在 Claude Code（或你的 AI 工具）中输入：

```
/skill-spec:proposal my-skill
```

The AI will:
1. Ask about purpose, inputs, decision rules, edge cases
2. Generate complete `spec.yaml` from your answers
3. Validate with `--strict` and save to `skillspec/drafts/my-skill/`

AI 将会：
1. 询问目的、输入、决策规则、边界情况
2. 根据你的回答生成完整的 `spec.yaml`
3. 使用 `--strict` 验证并保存到 `skillspec/drafts/my-skill/`

---

## How It Works / 工作流程

```
skillspec setup              # Initialize project / 初始化项目
       |
       v
/skill-spec:proposal <name>  # AI-assisted creation + validation / AI 辅助创建+验证
       |
       v
/skill-spec:apply <name>     # Generate SKILL.md / 生成 SKILL.md
       |
       v
/skill-spec:deploy <name>    # Publish skill / 发布技能
```

---

## Slash Commands (AI-Assisted) / 斜杠命令（AI 辅助）

| Command | Description | 说明 |
|---------|-------------|------|
| `/skill-spec:proposal <name>` | Interactive skill creation + validation | 交互式创建技能+验证 |
| `/skill-spec:apply <name>` | Generate SKILL.md from spec | 从规范生成 SKILL.md |
| `/skill-spec:deploy <name>` | Publish skill to skills/ | 发布技能到 skills/ |
| `/skill-spec:migrate <path>` | Migrate existing skill | 迁移现有技能 |

---

## Main CLI Commands / 主要命令

| Command | Description | 说明 |
|---------|-------------|------|
| `skillspec setup` | Initialize project | 初始化项目 |
| `skillspec list` | List all skills | 列出所有技能 |
| `skillspec validate <name> --strict` | Validate spec | 验证规范 |
| `skillspec generate <name>` | Generate SKILL.md | 生成 SKILL.md |
| `skillspec publish <name>` | Publish to skills/ | 发布技能 |
| `skillspec report <name>` | Quality report (text output) | 质量报告 (文本输出) |
| `skillspec report <name> --format json` | Quality report (JSON output) | 质量报告 (JSON 输出) |
| `skillspec report <name> --format markdown` | Quality report (Markdown output) | 质量报告 (Markdown 输出) |
| `skillspec convert-report <json>` | Convert JSON report to Markdown | JSON 报告转 Markdown |

---

## Directory Structure / 目录结构

```
my-project/
+-- .claude/commands/skill-spec/   # Slash commands / 斜杠命令
+-- skillspec/
|   +-- SKILL_AGENTS.md            # AI guidance / AI 指导文件
|   +-- schema/                    # JSON Schema
|   +-- templates/                 # Templates / 模板
|   +-- patterns/                  # Forbidden patterns / 禁用模式
|   +-- drafts/                    # Work in progress / 草稿
|   +-- skills/                    # Published / 已发布
|   +-- archive/                   # Archived / 已归档
+-- project.yaml                   # Configuration / 配置
```

---

## Design Goals / 设计目标

### Level 1: Platform Quality / 平台质量

- **Mandatory Section Taxonomy**: 8 Core + 1 Coverage sections
- **Forbidden Pattern Detection**: Catches vague language
- **Coverage Analysis**: Ensures complete specification
- **Consistency Validation**: Cross-references all components

强制的章节结构、禁用模式检测、覆盖率分析、一致性验证

### Level 2: User Quality / 用户质量

- **Structured Templates**: Pre-defined spec.yaml templates
- **Clear Validation Feedback**: Actionable error messages
- **Quality Reports**: Structural and behavioral coverage scores
- **Migration Tools**: Convert existing SKILL.md files

结构化模板、清晰的验证反馈、质量报告、迁移工具

### Level 3: Enterprise Quality / 企业质量

- **Custom Policy Rules**: Organization-specific requirements
- **Tag Taxonomy**: Data classification (PII, financial, auth)
- **Compliance Validation**: GDPR, security rules
- **Audit Evidence**: Diary system for compliance audits

自定义策略规则、标签分类、合规验证、审计证据

---

## Section Taxonomy v1.0 / 

### Core Sections (8 required) / 核心章节（8 个必需）

| Section | Purpose | 用途 |
|---------|---------|------|
| `skill` | Metadata | 元数据 |
| `inputs` | Input contract | 输入契约 |
| `preconditions` | Prerequisites | 前提条件 |
| `non_goals` | Explicit boundaries | 明确边界 |
| `decision_rules` | Decision logic | 决策逻辑 |
| `steps` | Execution flow | 执行流程 |
| `output_contract` | Output schema | 输出模式 |
| `failure_modes` | Error handling | 错误处理 |

### Coverage Section (1 required) / 覆盖章节（1 个必需）

| Section | Purpose | 用途 |
|---------|---------|------|
| `edge_cases` | Boundary conditions | 边界条件 |

### Optional Sections / 可选章节

| Section | Purpose | 用途 |
|---------|---------|------|
| `context` | Collaboration info | 协作信息 |
| `examples` | Usage examples | 使用示例 |

---

## Validation Layers / 验证层级

```
spec.yaml
    |
    v
Layer 1: Schema       # Structure, required fields / 结构、必填字段
    |
    v
Layer 2: Quality      # Forbidden patterns / 禁用模式
    |
    v
Layer 3: Coverage     # Edge cases, decision rules / 边界情况、决策规则
    |
    v
Layer 4: Consistency  # Cross-references / 交叉引用
    |
    v
Layer 5: Compliance   # Enterprise policies (optional) / 企业策略（可选）
```

---

## Multi-Language Support / 多语言支持

```bash
# Chinese output / 中文输出
skillspec --locale=zh validate my-skill

# Chinese patterns / 中文禁用模式
skillspec --patterns=zh validate my-skill

# Combined patterns (strictest) / 组合模式（最严格）
skillspec --patterns=union validate my-skill
```

Configuration in `project.yaml` / 在 `project.yaml` 中配置:

```yaml
skill_spec:
  report_locale: en        # en | zh
  patterns_locale: union   # en | zh | union
  template_locale: en      # en | zh
```

---

## Development / 开发

```bash
# Install from source / 从源码安装
pip install -e ./backend

# Run tests / 运行测试
pytest tests/

# Type checking / 类型检查
mypy backend/skillspec/
```

---

## License

MIT
