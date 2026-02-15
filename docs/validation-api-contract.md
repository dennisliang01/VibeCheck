# Validation API Contract

This document describes the JSON schema expected from the Python validation backend. When the Python scripts are integrated, they should produce output matching this contract.

## Output Location (Phase 2)

The Next.js API will check for validation data in one of these locations:

- `workspaces/[projectId]/validation_report.json` – single file with both scores and feedback
- Or split files: `validation_scores.json` and `validation_feedback.json`

## Schema

### ValidationReport (single file)

```json
{
  "scores": {
    "performance": 0-100,
    "security": 0-100,
    "codeQuality": 0-100,
    "architecture": 0-100
  },
  "feedback": [
    {
      "id": "string",
      "title": "string",
      "severity": "high" | "medium" | "low",
      "filePath": "string (optional – enables Jump to file)",
      "recommendation": "string"
    }
  ]
}
```

### Scores

| Field        | Type   | Range   |
| ------------ | ------ | ------- |
| performance  | number | 0–100   |
| security     | number | 0–100   |
| codeQuality  | number | 0–100   |
| architecture | number | 0–100   |

### Feedback Item

| Field         | Type     | Required | Notes                                    |
| ------------- | -------- | -------- | ---------------------------------------- |
| id            | string   | yes      | Unique identifier                        |
| title         | string   | yes      | Short title for the finding              |
| severity      | string   | yes      | `"high"` \| `"medium"` \| `"low"`        |
| filePath      | string   | no       | Relative path within project; enables "Jump to file" |
| recommendation| string   | yes      | Human-readable recommendation text       |

## API Endpoint

`GET /api/project/[id]/validation` returns the same shape. The frontend fetches this endpoint; the API will read from workspace JSON (when present) or fall back to mock data.
