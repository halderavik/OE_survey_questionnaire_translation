# API Documentation

## Overview

The Survey Question Translator MVP provides a RESTful API for translating survey questions from multiple languages to English using DeepSeek AI. The API supports real-time progress tracking through Server-Sent Events (SSE).

## Base URL

- **Development**: `http://localhost:5000`
- **Production**: `https://your-domain.com`

## Authentication

Currently, the API does not require authentication. However, a valid DeepSeek API key must be configured in the environment variables.

## Endpoints

### 1. Health Check

**GET** `/test`

Check if the application is running and healthy.

#### Response

```json
{
  "status": "ok",
  "message": "Flask app is running",
  "timestamp": "2025-08-03T08:46:00.499482"
}
```

#### Example

```bash
curl http://localhost:5000/test
```

### 2. File Upload and Processing

**POST** `/upload`

Upload an Excel file containing survey questions for processing.

#### Request

- **Content-Type**: `multipart/form-data`
- **Body**: Form data with file field

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Yes | Excel file (.xlsx or .xls) containing survey questions |

#### File Requirements

- **Format**: Excel (.xlsx or .xls)
- **Structure**: Single column with survey questions
- **Size Limit**: 2MB maximum
- **Question Limit**: 1000 questions maximum

#### Response

```json
{
  "success": true,
  "results": [
    {
      "question_number": 1,
      "row_number": 2,
      "original_question": "¿Cuál es tu color favorito?",
      "detected_language": "Spanish",
      "confidence": 95,
      "english_translation": "What is your favorite color?"
    }
  ],
  "total_questions": 1,
  "processed_at": "2025-08-03T08:46:00.499482"
}
```

#### Error Responses

**400 Bad Request**
```json
{
  "error": "No file uploaded"
}
```

**400 Bad Request**
```json
{
  "error": "Invalid file type. Please upload an Excel file (.xlsx or .xls)"
}
```

**413 Payload Too Large**
```json
{
  "error": "File too large. Maximum size is 2MB."
}
```

**500 Internal Server Error**
```json
{
  "error": "File processing error: [error details]"
}
```

#### Example

```bash
curl -X POST \
  -F "file=@survey_questions.xlsx" \
  http://localhost:5000/upload
```

### 3. Real-Time Progress Tracking

**GET** `/progress`

Stream real-time progress updates using Server-Sent Events (SSE).

#### Response

Event stream with JSON data:

```
data: {"status":"reading_file","message":"Reading Excel file...","current_question":0,"total_questions":0,"current_row":0,"detected_language":"","confidence":0,"translation":"","processing_time":"","api_response_time":""}

data: {"status":"processing","message":"Starting API processing for 5 questions...","current_question":0,"total_questions":5,"current_row":0,"detected_language":"","confidence":0,"translation":"","processing_time":"","api_response_time":""}

data: {"status":"processing_question","message":"Processing question 1/5 (Row 2)","current_question":1,"total_questions":5,"current_row":2,"detected_language":"Analyzing...","confidence":0,"translation":"Waiting for language detection...","processing_time":"1/5 questions processed","api_response_time":"Language detection in progress..."}
```

#### Progress Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | String | Current processing status |
| `message` | String | Human-readable status message |
| `current_question` | Integer | Current question number being processed |
| `total_questions` | Integer | Total number of questions to process |
| `current_row` | Integer | Excel row number being processed |
| `detected_language` | String | Detected language or status |
| `confidence` | Integer | Confidence score (0-100) |
| `translation` | String | Current translation or status |
| `processing_time` | String | Processing time information |
| `api_response_time` | String | API response time information |

#### Status Values

- `reading_file`: Reading Excel file
- `processing`: Starting API processing
- `processing_question`: Processing individual question
- `completed`: Processing completed successfully
- `error`: Error occurred during processing

#### Example

```javascript
const eventSource = new EventSource('/progress');

eventSource.onmessage = function(event) {
  const progressData = JSON.parse(event.data);
  console.log('Progress:', progressData);
  
  if (progressData.status === 'completed') {
    eventSource.close();
  }
};
```

### 4. Download Results

**POST** `/download`

Generate and download an Excel file with processing results.

#### Request

- **Content-Type**: `application/json`
- **Body**: JSON with results data

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `results` | Array | Yes | Array of processing results |

#### Response

- **Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Content-Disposition**: `attachment; filename=survey_translation_results_YYYYMMDD_HHMMSS.xlsx`

#### Example

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"results":[{"original_question":"¿Cuál es tu color favorito?","detected_language":"Spanish","confidence":95,"english_translation":"What is your favorite color?"}]}' \
  http://localhost:5000/download \
  --output results.xlsx
```

## Error Handling

### HTTP Status Codes

- **200 OK**: Request successful
- **400 Bad Request**: Invalid request parameters
- **413 Payload Too Large**: File size exceeds limit
- **500 Internal Server Error**: Server error

### Error Response Format

```json
{
  "error": "Error message description"
}
```

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting for production use.

## CORS

The API includes CORS headers for cross-origin requests:

```
Access-Control-Allow-Origin: *
```

## Security Considerations

1. **File Upload Security**: Validate file types and sizes
2. **API Key Security**: Store DeepSeek API key securely
3. **Input Validation**: Validate all input parameters
4. **Error Information**: Avoid exposing sensitive information in error messages

## Testing

### Test Mode

Set `TEST_MODE=true` in your `.env` file to bypass actual API calls and return mock data for testing.

### Example Test File

Use the provided test files:
- `test_questions.xlsx` - Sample English questions
- `test_spanish_questions.xlsx` - Sample Spanish questions

## Performance

- **Processing Speed**: ~50 questions per minute
- **API Timeout**: 15 seconds per API call
- **Progress Updates**: 500ms refresh rate
- **File Size Limit**: 2MB
- **Question Limit**: 1000 questions per file

## Support

For API support and questions, please refer to the project documentation or create an issue in the repository. 