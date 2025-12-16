---
name: "document-generator"
description: "Generate technical documentation automatically from code, API specs, or design documents. Use when: creating README | updating API docs | publishing release notes"
---

# Document Generator

## Description

This skill automatically generates technical documentation from various source materials including source code, API specifications, and design documents. It supports multiple document types and can produce output in Chinese, English, or bilingual formats.

**Supported source types:**
- **code**: Source code with comments and docstrings
- **api_spec**: OpenAPI or similar API specifications
- **design_doc**: Design documents and architecture descriptions
- **changelog**: Git logs or change records

**Supported document types:**
- **api_reference**: API reference documentation
- **user_guide**: User guides with installation and usage instructions
- **readme**: Project README files
- **changelog**: Version-organized change logs
- **architecture**: System architecture documentation

## When to Use

Use this skill when:
- Initializing a new project that needs README documentation
- API interfaces have changed and documentation needs updating
- Preparing release notes for a new version
- Converting source code comments to formal documentation
- Creating bilingual documentation for international teams

Do NOT use this skill for:
- Translating existing documentation
- Generating marketing or sales materials
- Creating legal or compliance documents
- Generating user interface text

## Instructions

### Input Requirements

1. **source_content** (required): Source material for documentation
   - Valid text format (not binary)
   - Maximum 100,000 characters

2. **source_type** (required): Type of source material
   - `code`: Source code with comments
   - `api_spec`: API specification files
   - `design_doc`: Design documents
   - `changelog`: Change records

3. **doc_type** (required): Type of document to generate
   - `api_reference`: API endpoint documentation
   - `user_guide`: Installation and usage guide
   - `readme`: Project overview and quick start
   - `changelog`: Version-organized changes
   - `architecture`: System design documentation

4. **output_language** (optional): Output language
   - `zh` (default): Chinese
   - `en`: English
   - `zh-en`: Bilingual

5. **include_examples** (optional): Include code examples
   - `true` (default): Include examples
   - `false`: Omit examples

6. **detail_level** (optional): Documentation detail level
   - `brief`: Concise overview
   - `standard` (default): Normal detail
   - `detailed`: Comprehensive documentation

### Execution Flow

1. Parse source content, extract structured information
2. Analyze structure, determine document outline
3. Extract metadata (version, author, date)
4. Generate document sections
5. Add examples (if enabled)
6. Apply Markdown formatting
7. Translate if bilingual output requested

### Output Format

```json
{
  "status": "success | partial | error",
  "document": {
    "title": "Document Title",
    "content": "Generated Markdown content",
    "format": "markdown | html",
    "sections": [
      {"title": "Section Name", "level": 1}
    ],
    "word_count": 500
  },
  "warnings": ["Optional warnings"],
  "metadata": {
    "generation_time_ms": 1200,
    "source_type": "code"
  }
}
```

## Examples

### Example 1: Simple README Generation

**Input:**
```python
source_content: |
  def hello(name: str) -> str:
      """Say hello to a user.

      Args:
          name: User name

      Returns:
          Greeting string
      """
      return f"Hello, {name}!"

source_type: "code"
doc_type: "readme"
output_language: "zh"
detail_level: "brief"
```

**Output:**
```json
{
  "status": "success",
  "document": {
    "title": "Project Documentation",
    "content": "# Project Documentation\n\n## Features\n\nProvides user greeting functionality.\n\n## Usage\n\n```python\nresult = hello(\"World\")\n# Output: Hello, World!\n```",
    "format": "markdown"
  }
}
```

### Example 2: API Reference from Specification

**Input:**
```json
{
  "source_content": "openapi: 3.0.0\ninfo:\n  title: User API\npaths:\n  /users:\n    get:\n      summary: List users",
  "source_type": "api_spec",
  "doc_type": "api_reference",
  "output_language": "en",
  "detail_level": "standard"
}
```

**Output:**
```json
{
  "status": "success",
  "document": {
    "title": "User API Reference",
    "content": "# User API Reference\n\n## Endpoints\n\n### GET /users\n\nList all users in the system.\n\n**Response:**\n- 200: Success",
    "format": "markdown",
    "sections": [
      {"title": "User API Reference", "level": 1},
      {"title": "Endpoints", "level": 2}
    ]
  }
}
```

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Empty source | Return error with code `PARSE_ERROR` |
| Minimal source | Return partial with template content warning |
| Mixed language source | Process successfully for bilingual output |
| No examples extractable | Return partial with warning |
| Unsupported doc type | Return error with code `UNSUPPORTED_DOC_TYPE` |
| Large source content | May truncate with warning |

## Limitations

1. **Source Quality Dependent**: Output quality depends on source code comments and documentation
2. **No Semantic Understanding**: Cannot infer intent beyond what's explicitly documented
3. **Language Detection**: May struggle with heavily mixed Chinese/English content
4. **No External Access**: Cannot fetch related files or dependencies
5. **Template-Based**: Some sections may use generic templates when source is insufficient
6. **Translation Quality**: Bilingual output relies on translation quality

## Error Codes

| Code | Retryable | Description |
|------|-----------|-------------|
| `PARSE_ERROR` | No | Cannot parse source content |
| `UNSUPPORTED_DOC_TYPE` | No | Requested document type not supported |
| `GENERATION_FAILED` | Yes | Error during document generation |
| `TRANSLATION_ERROR` | Yes | Error during bilingual translation |

## Related Skills

- **code-analyzer**: Analyze code structure before generating documentation
- **markdown-formatter**: Format and beautify generated documents
- **extract-api-contract**: Extract API specifications as input for documentation
