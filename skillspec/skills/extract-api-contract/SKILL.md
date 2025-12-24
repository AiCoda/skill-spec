---
name: "extract-api-contract"
description: "Extract structured API contract information from source code, documentation, or OpenAPI specifications Use when: source_type == 'openapi' or source_type == 'swagger' | source_type == 'code' | source_type == 'documentation'"
---

<!-- skillspec:generated:start -->
# Extract Api Contract

## Purpose

Extract structured API contract information from source code, documentation, or OpenAPI specifications

## Inputs

- **source_content** (string, required)
  Source code, documentation, or OpenAPI spec content to analyze
  Constraints: not_empty, max_length_50000
- **source_type** (string, required)
  Type of source content
  Constraints: not_empty
- **output_format** (string, optional)
  Desired output format for the contract

## What This Skill Does NOT Do

- Generate implementation code from contracts
- Validate API implementations against contracts
- Perform security analysis on API endpoints
- Handle authentication or authorization logic

## Prerequisites

- Source content must be valid text (not binary)
- For code sources, the programming language must be identifiable
- For OpenAPI/Swagger, the specification must be parseable YAML or JSON

## Decision Criteria

### rule_openapi_source
- **When**: `source_type == 'openapi' or source_type == 'swagger'`
- **Then**: `{'status': 'success', 'path': 'parse_openapi', 'action': 'Parse and normalize OpenAPI specification'}`

### rule_code_source
- **When**: `source_type == 'code'`
- **Then**: `{'status': 'success', 'path': 'analyze_code', 'action': 'Extract API patterns from source code'}`

### rule_doc_source
- **When**: `source_type == 'documentation'`
- **Then**: `{'status': 'success', 'path': 'parse_documentation', 'action': 'Extract structured information from documentation'}`

### rule_default
- **When**: `True`
- **Then**: `{'status': 'error', 'code': 'UNSUPPORTED_SOURCE'}`

## Workflow

1. **Validate source content is non-empty and parseable** -> `validated_content`
2. **Detect specific format within source type** -> `detected_format`
3. **Extract API endpoint definitions** -> `endpoints`
4. **Extract data schemas and models** -> `schemas`
5. **Assemble complete API contract** -> `api_contract`
6. **Convert contract to requested output format** -> `formatted_contract`

## Edge Cases

- **empty_input**: `{'status': 'error', 'code': 'INVALID_SOURCE'}`
- **malformed_openapi**: `{'status': 'error', 'code': 'INVALID_SOURCE'}`
- **no_endpoints_found**: `{'status': 'partial', 'warnings': ['No API endpoints found in source']}`
- **partial_extraction**: `{'status': 'partial', 'warnings': ['Some endpoints could not be fully parsed']}`

## Output Format

Format: `json`

```json
{
  "type": "object",
  "required": [
    "status",
    "contract"
  ],
  "properties": {
    "status": {
      "type": "string",
      "enum": [
        "success",
        "partial",
        "error"
      ]
    },
    "contract": {
      "type": "object",
      "properties": {
        "title": {
          "type": "string"
        },
        "version": {
          "type": "string"
        },
        "endpoints": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "method": {
                "type": "string"
              },
              "path": {
                "type": "string"
              },
              "summary": {
                "type": "string"
              }
            }
          }
        },
        "schemas": {
          "type": "object"
        }
      }
    },
    "warnings": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "error": {
      "type": "string"
    }
  }
}
```

## Error Handling

- **INVALID_SOURCE**: Non-retryable
  Source content is not valid or parseable
- **UNSUPPORTED_SOURCE**: Non-retryable
  Source type is not supported
- **EXTRACTION_FAILED**: Retryable
  Failed to extract API information from source
- **FORMAT_ERROR**: Non-retryable
  Failed to convert to requested output format

## Works Well With

- **generate-api-client**: Use extracted contract to generate client SDKs
- **validate-api-implementation**: Verify implementation matches contract

<!-- skillspec:generated:end -->