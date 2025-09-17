# Multi-Model Validation API Documentation

## Overview

The Multi-Model Validation API provides endpoints for managing and querying AI model validations with consensus calculation capabilities. This system allows multiple AI models to independently validate Response Awareness (RA) tags, providing diverse perspectives and consensus analysis for assumption validation.

## Base URL

```
https://your-domain.com/api/assumptions
```

## Authentication

Currently, no authentication is required for API access. In production environments, implement appropriate authentication mechanisms.

## Rate Limiting

- **Standard endpoints**: 100 requests per minute per IP
- **Multi-model endpoints**: 50 requests per minute per IP (due to computational complexity)
- **Models endpoint**: 200 requests per minute per IP (lightweight operation)

## Response Format

All API responses follow this standardized format:

```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2025-09-17T12:30:00.000Z",
  "cached": false
}
```

Error responses:
```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "2025-09-17T12:30:00.000Z"
}
```

## Multi-Model Validation Endpoints

### 1. Get Multi-Model View

Retrieve all validations for a specific RA tag across different models with consensus analysis.

**Endpoint:** `GET /api/assumptions/multi-model/{task_id}/{ra_tag_id}`

**Parameters:**
- `task_id` (integer, required): ID of the task containing the RA tag
- `ra_tag_id` (string, required): Unique identifier of the RA tag

**Example Request:**
```bash
curl -X GET "https://your-domain.com/api/assumptions/multi-model/123/ra_tag_abc123"
```

**Example Response:**
```json
{
  "consensus": {
    "consensus": 0.847,
    "outcome": "validated",
    "agreement_level": "STRONG",
    "model_disagreement": false,
    "total_validations": 3
  },
  "validations": [
    {
      "id": 1,
      "task_id": 123,
      "ra_tag_id": "ra_tag_abc123",
      "outcome": "validated",
      "confidence": 88,
      "validator_id": "claude-sonnet-3.5",
      "notes": "Implementation assumption appears valid based on code analysis",
      "validated_at": "2025-09-17T10:15:30.000Z",
      "model_name": "Claude Sonnet 3.5",
      "model_version": "3.5",
      "model_category": "large_language_model"
    },
    {
      "id": 2,
      "task_id": 123,
      "ra_tag_id": "ra_tag_abc123",
      "outcome": "validated",
      "confidence": 92,
      "validator_id": "gpt-4-turbo",
      "notes": "Agrees with implementation approach",
      "validated_at": "2025-09-17T10:20:45.000Z",
      "model_name": "GPT-4 Turbo",
      "model_version": "turbo",
      "model_category": "large_language_model"
    },
    {
      "id": 3,
      "task_id": 123,
      "ra_tag_id": "ra_tag_abc123",
      "outcome": "partial",
      "confidence": 75,
      "validator_id": "gemini-pro-1.0",
      "notes": "Implementation valid but suggests additional error handling",
      "validated_at": "2025-09-17T10:25:12.000Z",
      "model_name": "Gemini Pro",
      "model_version": "1.0",
      "model_category": "large_language_model"
    }
  ],
  "model_count": 3,
  "task_name": "Implement user authentication API",
  "ra_tag_text": "#COMPLETION_DRIVE_IMPL: Using JWT tokens for stateless authentication",
  "generated_at": "2025-09-17T12:30:00.000Z",
  "cached": false
}
```

Note on empty data:
- When an RA tag has no validations, `agreement_level` is `"no_data"`, `consensus` is `0.0`, and `model_count` is `0`.
  Clients should treat this as “no data yet” rather than low agreement.

**Error Responses:**
- `404`: Task not found or RA tag not found
- `422`: Invalid task ID format
- `500`: Internal server error

### 2. Get Task Consensus Summary

Retrieve consensus summary for all RA tags within a specific task.

**Endpoint:** `GET /api/assumptions/consensus/{task_id}`

**Parameters:**
- `task_id` (integer, required): ID of the task to get consensus for

**Example Request:**
```bash
curl -X GET "https://your-domain.com/api/assumptions/consensus/123"
```

**Example Response:**
```json
{
  "task_id": 123,
  "task_name": "Implement user authentication API",
  "overall_consensus": {
    "consensus": 0.823,
    "agreement_level": "STRONG",
    "total_tags": 5,
    "total_validations": 12
  },
  "ra_tag_summaries": [
    {
      "ra_tag_id": "ra_tag_abc123",
      "ra_tag_text": "#COMPLETION_DRIVE_IMPL: Using JWT tokens for stateless authentication",
      "consensus": {
        "consensus": 0.847,
        "outcome": "validated",
        "agreement_level": "STRONG",
        "model_disagreement": false,
        "total_validations": 3
      },
      "top_models": ["claude-sonnet-3.5", "gpt-4-turbo", "gemini-pro-1.0"]
    },
    {
      "ra_tag_id": "ra_tag_def456",
      "ra_tag_text": "#SUGGEST_ERROR_HANDLING: Add rate limiting for login attempts",
      "consensus": {
        "consensus": 0.912,
        "outcome": "validated",
        "agreement_level": "STRONG",
        "model_disagreement": false,
        "total_validations": 2
      },
      "top_models": ["claude-sonnet-3.5", "gpt-4-turbo"]
    }
  ],
  "contentious_tags": [],
  "high_confidence_tags": ["ra_tag_def456"],
  "generated_at": "2025-09-17T12:30:00.000Z"
}
```

**Error Responses:**
- `404`: Task not found
- `422`: Invalid task ID format
- `500`: Internal server error

### 3. Get Available Models

Retrieve list of all available AI models for validation with their configurations and capabilities.

**Endpoint:** `GET /api/assumptions/models`

**Example Request:**
```bash
curl -X GET "https://your-domain.com/api/assumptions/models"
```

**Example Response:**
```json
{
  "models": [
    {
      "id": "claude-sonnet-3.5",
      "name": "Claude Sonnet 3.5",
      "version": "3.5",
      "provider": "anthropic",
      "category": "large_language_model",
      "capabilities": ["code_analysis", "assumption_validation", "error_detection"],
      "weight": 1.0,
      "active": true,
      "description": "Advanced language model optimized for code analysis and reasoning"
    },
    {
      "id": "gpt-4-turbo",
      "name": "GPT-4 Turbo",
      "version": "turbo",
      "provider": "openai",
      "category": "large_language_model",
      "capabilities": ["code_analysis", "assumption_validation", "pattern_recognition"],
      "weight": 1.0,
      "active": true,
      "description": "OpenAI's advanced model with enhanced reasoning capabilities"
    },
    {
      "id": "gemini-pro-1.0",
      "name": "Gemini Pro",
      "version": "1.0",
      "provider": "google",
      "category": "large_language_model",
      "capabilities": ["code_analysis", "multimodal_analysis", "assumption_validation"],
      "weight": 0.9,
      "active": true,
      "description": "Google's advanced multimodal language model"
    },
    {
      "id": "codellama-34b",
      "name": "CodeLlama 34B",
      "version": "34b",
      "provider": "meta",
      "category": "code_specialized_model",
      "capabilities": ["code_analysis", "bug_detection"],
      "weight": 0.8,
      "active": true,
      "description": "Meta's code-specialized large language model"
    }
  ],
  "total_models": 4,
  "active_models": 4,
  "last_updated": "2025-09-17T12:00:00.000Z"
}
```

## Consensus Calculation

### Agreement Levels

The system calculates agreement levels based on consensus scores:

- **STRONG** (≥80%): High confidence in the consensus outcome
- **MODERATE** (60-79%): Reasonable agreement with some dissent
- **WEAK** (<60%): Significant disagreement among models

### Consensus Scoring

Consensus scores are calculated using weighted averages:

1. **Outcome Weights**: `validated=1.0`, `partial=0.5`, `rejected=0.0`
2. **Model Weights**: Applied based on model reliability and specialization
3. **Confidence Scaling**: Model confidence scores influence the final calculation

### Model Disagreement Detection

The system flags `model_disagreement: true` when:
- Consensus score is below 75%
- Models have conflicting outcomes (validated vs rejected)
- Large confidence variance (>30 points) between models

## Error Handling

### HTTP Status Codes

- **200 OK**: Successful request
- **400 Bad Request**: Invalid request parameters
- **404 Not Found**: Resource not found (task, RA tag)
- **422 Unprocessable Entity**: Invalid data format
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Temporary service unavailability

### Error Code Reference

| Code | Description | Action |
|------|-------------|--------|
| `TASK_NOT_FOUND` | Task ID does not exist | Verify task ID |
| `RA_TAG_NOT_FOUND` | RA tag ID not found in task | Check RA tag existence |
| `INVALID_TASK_ID` | Task ID format invalid | Use numeric task ID |
| `CONSENSUS_CALCULATION_ERROR` | Error calculating consensus | Check validation data |
| `CACHE_ERROR` | Caching system error | Retry request |
| `DATABASE_ERROR` | Database connection error | Retry after delay |

## Performance Characteristics

### Response Times (P95)

- **Multi-model view**: <500ms (cached: <100ms)
- **Consensus summary**: <300ms (cached: <50ms)
- **Available models**: <50ms (cached: <10ms)

### Caching

All endpoints implement intelligent caching:

- **TTL**: 5 minutes for consensus calculations
- **Invalidation**: Automatic on new validations
- **Cache warming**: Pre-calculation for active tasks

### Rate Limiting

Rate limits are enforced per endpoint and client IP:
- Standard operations: 100 req/min
- Multi-model operations: 50 req/min
- Model listing: 200 req/min

## Integration Examples

### JavaScript/TypeScript

```javascript
class MultiModelValidationClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async getMultiModelView(taskId, raTagId) {
    const response = await fetch(
      `${this.baseUrl}/api/assumptions/multi-model/${taskId}/${raTagId}`
    );

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  }

  async getTaskConsensus(taskId) {
    const response = await fetch(
      `${this.baseUrl}/api/assumptions/consensus/${taskId}`
    );

    return await response.json();
  }

  async getAvailableModels() {
    const response = await fetch(
      `${this.baseUrl}/api/assumptions/models`
    );

    return await response.json();
  }
}
```

### Python

```python
import requests
from typing import Dict, List, Optional

class MultiModelValidationClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get_multi_model_view(self, task_id: int, ra_tag_id: str) -> Dict:
        response = requests.get(
            f"{self.base_url}/api/assumptions/multi-model/{task_id}/{ra_tag_id}"
        )
        response.raise_for_status()
        return response.json()

    def get_task_consensus(self, task_id: int) -> Dict:
        response = requests.get(
            f"{self.base_url}/api/assumptions/consensus/{task_id}"
        )
        response.raise_for_status()
        return response.json()

    def get_available_models(self) -> Dict:
        response = requests.get(
            f"{self.base_url}/api/assumptions/models"
        )
        response.raise_for_status()
        return response.json()
```

### cURL Examples

```bash
# Get multi-model view with error handling
curl -X GET "https://your-domain.com/api/assumptions/multi-model/123/ra_tag_abc123" \
  -H "Accept: application/json" \
  -w "Status: %{http_code}\nTime: %{time_total}s\n" \
  --fail-with-body

# Get consensus with caching headers
curl -X GET "https://your-domain.com/api/assumptions/consensus/123" \
  -H "Accept: application/json" \
  -H "Cache-Control: max-age=300"

# List models with compression
curl -X GET "https://your-domain.com/api/assumptions/models" \
  -H "Accept: application/json" \
  -H "Accept-Encoding: gzip, deflate"
```

## WebSocket Real-time Updates

### Connection

Connect to the WebSocket endpoint for real-time validation updates:

```
ws://your-domain.com/ws/updates
```

### Multi-Model Events

The system broadcasts these events for multi-model operations:

```javascript
// Validation added event
{
  "type": "multi_model.validation_added",
  "timestamp": "2025-09-17T12:30:00.000Z",
  "context": {
    "task_id": "123",
    "ra_tag_id": "ra_tag_abc123"
  },
  "data": {
    "validation": { /* validation data */ },
    "model": { /* model information */ },
    "action": "validation_created"
  }
}

// Consensus updated event
{
  "type": "multi_model.consensus_updated",
  "timestamp": "2025-09-17T12:30:00.000Z",
  "context": {
    "task_id": "123",
    "ra_tag_id": "ra_tag_abc123"
  },
  "data": {
    "consensus": { /* new consensus data */ },
    "trigger": { /* what triggered the update */ },
    "action": "consensus_recalculated"
  }
}
```

## Troubleshooting

### Common Issues

**Q: API returns 404 for valid task ID**
A: Ensure the task contains RA tags. Tasks without RA tags won't appear in multi-model endpoints.

**Q: Consensus calculation seems incorrect**
A: Check that all models have completed validation. Partial results may show different consensus.

**Q: Performance is slower than expected**
A: Verify caching is enabled and check for expired cache entries. Consider cache warming for frequently accessed data.

**Q: WebSocket events not received**
A: Check WebSocket connection stability and ensure client is listening for correct event types.

### Debug Information

Add `?debug=true` to API requests for additional debugging information:

```json
{
  "debug": {
    "query_time_ms": 45,
    "cache_hit": true,
    "models_queried": 3,
    "consensus_calculation_time_ms": 12
  }
}
```

## Changelog

### Version 1.0.0 (2025-09-17)
- Initial release of Multi-Model Validation API
- Support for 10+ AI models
- Real-time WebSocket updates
- Comprehensive consensus calculation
- Performance optimizations (P95 < 500ms)

---

**Support**: For technical support and feature requests, contact the development team or create an issue in the project repository.
