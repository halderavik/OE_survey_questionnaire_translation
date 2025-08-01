# Survey Question Translator MVP - Technical Stack & Architecture

## Technology Stack

### Backend Framework
- **Flask 2.3+**: Lightweight Python web framework
  - **Rationale**: Simple, flexible, perfect for MVP scope
  - **Benefits**: Fast development, extensive ecosystem, easy deployment
- **Python 3.9+**: Core programming language
  - **Features**: Strong library ecosystem, excellent for AI/ML integration

### Backend Libraries & Dependencies
```python
# Core Flask & Web
Flask==2.3.2
Flask-WTF==1.1.1          # Forms and CSRF protection
Werkzeug==2.3.6           # WSGI utilities and file handling

# File Processing
pandas==2.0.3             # Excel/CSV data manipulation
openpyxl==3.1.2           # Excel file read/write (.xlsx)
xlrd==2.0.1               # Legacy Excel support (.xls)

# API & HTTP
requests==2.31.0          # HTTP client for DeepSeek API

# Utilities
python-dotenv==1.0.0      # Environment variable management
gunicorn==21.2.0          # Production WSGI server