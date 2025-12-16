---
name: "extract-api-contract"
description: "Extract structured API contract information from source code, documentation, or OpenAPI specifications. Use when: generating API docs | starting contract-first development | creating client SDKs"
---

# Extract API Contract

## Description

This skill extracts structured API contract information from various sources including source code, documentation, and OpenAPI/Swagger specifications. It analyzes the input and produces a normalized API contract that can be used for documentation generation, client SDK creation, or API validation.

**Supported source types:**
- **OpenAPI/Swagger**: Parses and normalizes OpenAPI 3.x or Swagger 2.x specifications
- **Code**: Extracts API patterns from source code (REST endpoints, function signatures)
- **Documentation**: Parses structured API documentation to extract contract information

**Output formats:**
- **openapi3**: Full OpenAPI 3.0 specification
- **json-schema**: JSON Schema for request/response validation
- **summary**: Simplified endpoint listing

## When to Use

Use this skill when:
- Generating API documentation from existing code
- Starting contract-first development for a new API service
- Creating client SDKs from API specifications
- Validating API implementations against expected contracts
- Migrating between API specification formats

Do NOT use this skill for:
- Generating implementation code from contracts
- Validating API implementations against contracts
- Performing security analysis on API endpoints
- Handling authentication or authorization logic

## Instructions

### Input Requirements

1. **source_content** (required): The source material to analyze
   - Must be valid text (not binary)
   - Maximum 50,000 characters
   - For OpenAPI/Swagger: valid YAML or JSON

2. **source_type** (required): Type of source content
   - `openapi`: OpenAPI 3.x specification
   - `swagger`: Swagger 2.x specification
   - `code`: Source code with API endpoints
   - `documentation`: API documentation text

3. **output_format** (optional): Desired output format
   - `openapi3` (default): Full OpenAPI 3.0 spec
   - `json-schema`: JSON Schema format
   - `summary`: Simplified endpoint listing

### Execution Flow

1. Validate source content is non-empty and parseable
2. Detect specific format within source type
3. Extract API endpoint definitions (methods, paths, parameters)
4. Extract data schemas and models
5. Assemble complete API contract
6. Convert to requested output format

### Output Format

```json
{
  "status": "success | partial | error",
  "contract": {
    "title": "API Title",
    "version": "1.0.0",
    "endpoints": [
      {
        "method": "GET",
        "path": "/resource",
        "summary": "Description of endpoint"
      }
    ],
    "schemas": {}
  },
  "warnings": ["Optional warnings about extraction issues"],
  "error": "Error message if status is error"
}
```

## Examples

### Example 1: Simple OpenAPI Extraction

**Input:**
```yaml
source_content: |
  openapi: 3.0.0
  info:
    title: Pet Store API
    version: 1.0.0
  paths:
    /pets:
      get:
        summary: List all pets
        responses:
          '200':
            description: A list of pets
    /pets/{id}:
      get:
        summary: Get pet by ID
        parameters:
          - name: id
            in: path
            required: true
source_type: "openapi"
output_format: "summary"
```

**Output:**
```json
{
  "status": "success",
  "contract": {
    "title": "Pet Store API",
    "version": "1.0.0",
    "endpoints": [
      {
        "method": "GET",
        "path": "/pets",
        "summary": "List all pets"
      },
      {
        "method": "GET",
        "path": "/pets/{id}",
        "summary": "Get pet by ID"
      }
    ]
  }
}
```

### Example 2: Code Extraction with Partial Results

**Input:**
```json
{
  "source_content": "# API endpoints defined somewhere\n# No clear patterns",
  "source_type": "code"
}
```

**Output:**
```json
{
  "status": "partial",
  "contract": {
    "endpoints": []
  },
  "warnings": ["No API endpoints found in source"]
}
```

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Empty source content | Return error with code `INVALID_SOURCE` |
| Malformed OpenAPI YAML | Return error with code `INVALID_SOURCE` |
| No endpoints found in code | Return partial with warning |
| Some endpoints unparseable | Return partial with extracted endpoints and warnings |
| Unsupported source type | Return error with code `UNSUPPORTED_SOURCE` |

## Limitations

1. **Static Analysis Only**: Extracts from source text; cannot execute code or make HTTP calls
2. **Language Support**: Best extraction from Python, JavaScript, TypeScript, Java; other languages may have limited support
3. **No Implementation Validation**: Does not verify that implementations match extracted contracts
4. **No Security Analysis**: Does not identify security vulnerabilities in API design
5. **Size Limits**: Source content limited to 50,000 characters

## Error Codes

| Code | Retryable | Description |
|------|-----------|-------------|
| `INVALID_SOURCE` | No | Source content is not valid or parseable |
| `UNSUPPORTED_SOURCE` | No | Source type is not supported |
| `EXTRACTION_FAILED` | Yes | Failed to extract API information from source |
| `FORMAT_ERROR` | No | Failed to convert to requested output format |

## Related Skills

- **generate-api-client**: Use extracted contract to generate client SDKs
- **validate-api-implementation**: Verify implementation matches contract
- **document-generator**: Generate full API documentation from contract
