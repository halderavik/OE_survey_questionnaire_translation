# Survey Question Translator MVP

A professional web application built with Flask that enables researchers and survey professionals to translate survey questions from multiple languages into English using DeepSeek AI. Features real-time progress tracking and live processing analysis.

## Features

- **Simple File Upload**: Drag-and-drop Excel file upload (.xlsx, .xls)
- **AI-Powered Processing**: Automatic language detection and translation using DeepSeek AI
- **Real-Time Progress Tracking**: Live updates showing current question processing status
- **Live Processing Analysis**: Real-time display of language detection, confidence scores, and translation progress
- **Professional Results**: Clean, organized results with confidence scoring
- **Excel Export**: One-click download of formatted results
- **Responsive Design**: Works on desktop and tablet devices
- **Comprehensive Error Handling**: Graceful handling of API errors and processing failures

## Technology Stack

- **Backend**: Flask 2.3+
- **File Processing**: pandas, openpyxl, xlrd
- **AI Integration**: DeepSeek API
- **Real-Time Updates**: Server-Sent Events (SSE)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Deployment**: Gunicorn

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/halderavik/OE_survey_questionnaire_translation.git
   cd OE_survey_questionnaire_translation
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   
   **Windows:**
   ```bash
   venv\Scripts\activate
   ```
   
   **macOS/Linux:**
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables**
   
   Copy the example environment file and configure it:
   ```bash
   cp .env.example .env
   ```
   
   Edit the `.env` file with your configuration:
   ```bash
   # DeepSeek API Configuration
   DEEPSEEK_API_KEY=your_api_key_here
   
   # Flask Configuration
   SECRET_KEY=your_secret_key_here
   FLASK_ENV=development
   FLASK_DEBUG=True
   
   # Application Configuration
   MAX_FILE_SIZE=2097152  # 2MB in bytes
   MAX_QUESTIONS=1000
   
   # Test Mode (set to true to bypass API calls for testing)
   TEST_MODE=false
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   
   Open your web browser and navigate to: `http://localhost:5000`

## Usage

### Step 1: Upload Excel File
1. Visit the application homepage
2. Drag-and-drop or click to upload an Excel file (.xlsx or .xls)
3. The file should contain survey questions in a single column
4. Preview the first 5 questions for confirmation
5. Click "Process Questions" to continue

### Step 2: Real-Time AI Processing
1. **Live Progress Bar**: Shows overall processing progress
2. **Real-Time Analysis Window**: Displays current processing details:
   - Current question number and row being processed
   - Detected language and confidence score
   - Translation progress and API response times
   - Processing time for each question
3. **Automatic Language Detection**: AI detects the language of each question
4. **Confidence Scoring**: Calculates confidence scores for language detection
5. **English Translation**: Translates all questions to English

### Step 3: View Results & Download
1. Results are displayed in a professional table format
2. Color-coded confidence indicators (green/yellow/red)
3. Sortable columns for easy analysis
4. Click "Download Excel" to get formatted results
5. Option to process another file immediately

## File Requirements

### Input Format
- **File Type**: Excel files (.xlsx or .xls)
- **Structure**: Single column containing survey questions
- **Size Limit**: Maximum 2MB
- **Question Limit**: Up to 1000 questions per file

### Output Format
- **File Type**: Excel file (.xlsx)
- **Columns**:
  - Original Question
  - Detected Language
  - Confidence (%)
  - English Translation
- **Additional Info**: Processing timestamp

## API Endpoints

### POST /upload
Upload and process Excel file with survey questions.

**Request**: Multipart form data with Excel file
**Response**: JSON with processing results

### GET /progress
Stream real-time progress updates using Server-Sent Events (SSE).

**Response**: Event stream with JSON progress data

### POST /download
Generate and download Excel file with results.

**Request**: JSON with results data
**Response**: Excel file download

### GET /test
Health check endpoint to verify application status.

**Response**: JSON with application status

## Real-Time Progress System

The application features a sophisticated real-time progress tracking system:

### Frontend Features
- **Live Progress Bar**: Updates in real-time showing processing percentage
- **Analysis Window**: Displays current question details, language detection, and translation status
- **Status Indicators**: Color-coded status updates (uploading, processing, completed, error)
- **Timeout Handling**: Automatic timeout warnings for long-running processes

### Backend Features
- **Server-Sent Events (SSE)**: Real-time data streaming from backend to frontend
- **Global Progress State**: Centralized progress tracking across all processing stages
- **Detailed Logging**: Comprehensive terminal output for debugging and monitoring
- **Error Recovery**: Graceful handling of individual question failures

## Error Handling

The application includes comprehensive error handling for:
- Invalid file types
- File size limits
- Empty files
- API errors and timeouts
- Network issues
- Processing failures
- JSON parsing errors
- Memory management

## Security & Privacy

- **No Data Storage**: Files processed in memory only
- **Automatic Cleanup**: Memory cleared after each session
- **Secure Transit**: HTTPS encryption for all communications
- **API Security**: Secure DeepSeek API key management
- **Privacy**: No user tracking or data collection
- **Input Validation**: Comprehensive file and data validation

## Performance

- **Processing Speed**: ~50 questions per minute
- **Response Time**: Results within 60 seconds for 100 questions
- **Real-Time Updates**: 500ms refresh rate for progress updates
- **API Timeouts**: 15-second timeout per API call for responsive feedback
- **File Size**: Maximum 2MB Excel files
- **Question Limit**: Up to 1000 questions per file

## Development

### Project Structure
```
OE_survey_questionnaire_translation/
├── app.py                 # Main Flask application with SSE support
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
├── .gitignore           # Git ignore rules
├── README.md            # Project documentation
├── templates/
│   └── index.html       # Main application template with real-time UI
├── planning.md          # Technical planning document
├── prd.md              # Product requirements document
├── task.md             # Development tasks
└── tests/
    └── test_app.py      # Unit tests
```

### Running Tests
```bash
# Install test dependencies
pip install pytest

# Run tests
pytest
```

### Code Style
- Follow PEP8 guidelines
- Use type hints
- Include docstrings for all functions
- Format with black

### Development Features
- **Debug Mode**: Detailed logging and error messages
- **Test Mode**: Bypass API calls for development testing
- **Hot Reload**: Automatic server restart on code changes
- **Comprehensive Logging**: Detailed terminal output for debugging

## Deployment

### Production Deployment with Gunicorn
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Environment Variables for Production
```bash
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your_secure_secret_key
DEEPSEEK_API_KEY=your_deepseek_api_key
MAX_FILE_SIZE=2097152
MAX_QUESTIONS=1000
TEST_MODE=false
```

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure virtual environment is activated
2. **API Error**: Verify DeepSeek API key in .env file
3. **File Upload Error**: Check file format and size limits
4. **Memory Error**: Reduce number of questions in file
5. **Progress Not Updating**: Check browser console for SSE connection errors
6. **JSON Serialization Error**: Ensure all numeric values are standard Python types

### Logs
Check console output for detailed error messages and debugging information. The application provides comprehensive logging for:
- File upload and validation
- Excel file processing
- API calls and responses
- Progress tracking
- Error handling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please refer to the project documentation or create an issue in the repository.

## Changelog

### Version 1.1.0 (Current)
- **Real-Time Progress Tracking**: Added Server-Sent Events (SSE) for live progress updates
- **Live Processing Analysis**: Real-time display of current question processing details
- **Enhanced Error Handling**: Improved error recovery and user feedback
- **Performance Optimizations**: Reduced API timeouts and improved response times
- **Comprehensive Logging**: Detailed backend logging for debugging and monitoring
- **JSON Serialization Fixes**: Resolved numpy type serialization issues

### Version 1.0.0 (MVP)
- Initial release with core functionality
- Excel file upload and processing
- DeepSeek AI integration
- Professional web interface
- Excel export functionality 