# Survey Question Translator MVP

A professional web application built with Flask that enables researchers and survey professionals to translate survey questions from multiple languages into English using DeepSeek AI.

## Features

- **Simple File Upload**: Drag-and-drop Excel file upload (.xlsx, .xls)
- **AI-Powered Processing**: Automatic language detection and translation
- **Professional Results**: Clean, organized results with confidence scoring
- **Excel Export**: One-click download of formatted results
- **Responsive Design**: Works on desktop and tablet devices

## Technology Stack

- **Backend**: Flask 2.3+
- **File Processing**: pandas, openpyxl, xlrd
- **AI Integration**: DeepSeek API
- **Frontend**: HTML5, CSS3, JavaScript
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

### Step 2: AI Processing
1. The system automatically detects the language of each question
2. Calculates confidence scores for language detection
3. Translates all questions to English
4. Real-time progress bar shows processing status

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

### POST /download
Generate and download Excel file with results.

**Request**: JSON with results data
**Response**: Excel file download

## Error Handling

The application includes comprehensive error handling for:
- Invalid file types
- File size limits
- Empty files
- API errors
- Network issues
- Processing failures

## Security & Privacy

- **No Data Storage**: Files processed in memory only
- **Automatic Cleanup**: Memory cleared after each session
- **Secure Transit**: HTTPS encryption for all communications
- **API Security**: Secure DeepSeek API key management
- **Privacy**: No user tracking or data collection

## Performance

- **Processing Speed**: ~50 questions per minute
- **Response Time**: Results within 60 seconds for 100 questions
- **File Size**: Maximum 2MB Excel files
- **Question Limit**: Up to 1000 questions per file

## Development

### Project Structure
```
OE_survey_questionnaire_translation/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
├── .gitignore           # Git ignore rules
├── README.md            # Project documentation
├── templates/
│   └── index.html       # Main application template
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
```

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure virtual environment is activated
2. **API Error**: Verify DeepSeek API key in .env file
3. **File Upload Error**: Check file format and size limits
4. **Memory Error**: Reduce number of questions in file

### Logs
Check console output for detailed error messages and debugging information.

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

### Version 1.0.0 (MVP)
- Initial release with core functionality
- Excel file upload and processing
- DeepSeek AI integration
- Professional web interface
- Excel export functionality 