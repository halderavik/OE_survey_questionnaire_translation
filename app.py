"""
Survey Question Translator MVP - Main Flask Application

This module contains the main Flask application for the Survey Question Translator MVP.
It provides a web interface for uploading Excel files containing survey questions
and translating them using DeepSeek AI.
"""

import os
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pandas as pd
import requests
from dotenv import load_dotenv
import tempfile
import json
from datetime import datetime

# Load environment variables
load_dotenv()

def create_app():
    """Create and configure the Flask application."""
    
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE', 2 * 1024 * 1024))  # 2MB max file size
    app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
    app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls'}
    app.config['MAX_QUESTIONS'] = int(os.getenv('MAX_QUESTIONS', 1000))
    
    # DeepSeek API configuration
    app.config['DEEPSEEK_API_KEY'] = os.getenv('DEEPSEEK_API_KEY')
    app.config['DEEPSEEK_API_URL'] = 'https://api.deepseek.com/v1/chat/completions'
    
    # Test mode configuration
    app.config['TEST_MODE'] = os.getenv('TEST_MODE', 'false').lower() == 'true'
    
    return app

app = create_app()

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and process survey questions."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload an Excel file (.xlsx or .xls)'}), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Process the file
            result = process_excel_file(filepath)
            return jsonify(result)
        except Exception as e:
            print(f"Error processing file {filename}: {str(e)}")
            return jsonify({'error': f'File processing error: {str(e)}'}), 500
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print(f"Error cleaning up file {filepath}: {str(e)}")
        
    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        return jsonify({'error': f'Upload error: {str(e)}'}), 500

def process_excel_file(filepath):
    """Process Excel file and return translation results."""
    try:
        # Read Excel file
        df = pd.read_excel(filepath, header=None)
        
        # Extract questions from first column
        questions = df.iloc[:, 0].dropna().tolist()
        
        if not questions:
            raise ValueError("No questions found in the Excel file")
        
        if len(questions) > app.config['MAX_QUESTIONS']:
            raise ValueError(f"Maximum {app.config['MAX_QUESTIONS']} questions allowed per file")
        
        # Process questions with DeepSeek API
        results = []
        for i, question in enumerate(questions):
            result = process_question(question, i + 1)
            results.append(result)
        
        return {
            'success': True,
            'results': results,
            'total_questions': len(questions),
            'processed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise Exception(f"Error processing Excel file: {str(e)}")

def process_question(question, question_number):
    """Process a single question using DeepSeek API."""
    try:
        # Test mode - return mock results
        if app.config.get('TEST_MODE', False):
            return {
                'question_number': question_number,
                'original_question': question,
                'detected_language': 'English',
                'confidence': 95,
                'english_translation': f'[TEST MODE] {question}'
            }
        
        # Check if API key is configured
        if not app.config.get('DEEPSEEK_API_KEY'):
            raise Exception("DeepSeek API key not configured")
        
        # Prepare API request for language detection and translation
        headers = {
            'Authorization': f'Bearer {app.config["DEEPSEEK_API_KEY"]}',
            'Content-Type': 'application/json'
        }
        
        # First, detect language
        language_prompt = f"""
        Analyze the following text and provide:
        1. The detected language (language name in English)
        2. A confidence score (0-100)
        
        Text: "{question}"
        
        Respond in JSON format:
        {{
            "language": "detected_language_name",
            "confidence": confidence_score
        }}
        """
        
        language_data = {
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': language_prompt}],
            'temperature': 0.1
        }
        
        try:
            language_response = requests.post(
                app.config['DEEPSEEK_API_URL'],
                headers=headers,
                json=language_data,
                timeout=30
            )
            
            if language_response.status_code != 200:
                raise Exception(f"Language detection API error: {language_response.status_code} - {language_response.text}")
            
            language_result = language_response.json()
            
            # Handle potential JSON parsing issues in API response
            try:
                language_content = language_result['choices'][0]['message']['content']
                language_info = json.loads(language_content)
            except (KeyError, json.JSONDecodeError) as e:
                # Fallback: assume English if parsing fails
                language_info = {"language": "English", "confidence": 90}
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during language detection: {str(e)}")
        
        # Then, translate to English
        translation_prompt = f"""
        Translate the following text to English. Maintain the original meaning and tone.
        If the text is already in English, return it unchanged.
        
        Text: "{question}"
        
        Provide only the English translation, nothing else.
        """
        
        translation_data = {
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': translation_prompt}],
            'temperature': 0.1
        }
        
        try:
            translation_response = requests.post(
                app.config['DEEPSEEK_API_URL'],
                headers=headers,
                json=translation_data,
                timeout=30
            )
            
            if translation_response.status_code != 200:
                raise Exception(f"Translation API error: {translation_response.status_code} - {translation_response.text}")
            
            translation_result = translation_response.json()
            english_translation = translation_result['choices'][0]['message']['content'].strip()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during translation: {str(e)}")
        
        return {
            'question_number': question_number,
            'original_question': question,
            'detected_language': language_info.get('language', 'Unknown'),
            'confidence': language_info.get('confidence', 0),
            'english_translation': english_translation
        }
        
    except Exception as e:
        print(f"Error processing question {question_number}: {str(e)}")
        return {
            'question_number': question_number,
            'original_question': question,
            'detected_language': 'Error',
            'confidence': 0,
            'english_translation': f'Translation error: {str(e)}'
        }

@app.route('/download', methods=['POST'])
def download_results():
    """Generate and download Excel file with results."""
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({'error': 'No results to download'}), 400
        
        # Create DataFrame for Excel export
        df = pd.DataFrame(results)
        df = df[['original_question', 'detected_language', 'confidence', 'english_translation']]
        df.columns = ['Original Question', 'Detected Language', 'Confidence (%)', 'English Translation']
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        temp_file.close()
        
        # Write to Excel
        with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Translation Results', index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Translation Results']
            
            # Add timestamp
            worksheet['F1'] = 'Processed At'
            worksheet['F2'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f'survey_translation_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    return jsonify({'error': 'File too large. Maximum size is 2MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({'error': 'Page not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True) 