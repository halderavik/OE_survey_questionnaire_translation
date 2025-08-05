"""
Survey Question Translator MVP - Main Flask Application

This module contains the main Flask application for the Survey Question Translator MVP.
It provides a web interface for uploading Excel files containing survey questions
and translating them using DeepSeek AI.
"""

import os
import time
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

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to check if Flask is running."""
    return jsonify({
        'status': 'ok',
        'message': 'Flask app is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/progress', methods=['GET'])
def progress_stream():
    """Stream real-time progress updates."""
    def generate():
        while True:
            # Get the latest progress from global state
            if hasattr(app, 'current_progress'):
                progress_data = app.current_progress.copy()
                
                # Convert numpy types to standard Python types for JSON serialization
                if 'current_question' in progress_data:
                    progress_data['current_question'] = int(progress_data['current_question'])
                if 'total_questions' in progress_data:
                    progress_data['total_questions'] = int(progress_data['total_questions'])
                if 'current_row' in progress_data:
                    progress_data['current_row'] = int(progress_data['current_row'])
                if 'confidence' in progress_data:
                    progress_data['confidence'] = int(progress_data['confidence'])
                
                yield f"data: {json.dumps(progress_data)}\n\n"
            time.sleep(0.5)  # Update every 500ms
    
    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and process survey questions."""
    print("\n" + "="*60)
    print("🚀 UPLOAD REQUEST RECEIVED")
    print("="*60)
    
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            print("❌ No file in request.files")
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        print(f"✅ File received: {file.filename}")
        print(f"✅ File size: {len(file.read())} bytes")
        file.seek(0)  # Reset file pointer
        
        # Check if file was selected
        if file.filename == '':
            print("❌ No file selected")
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            print(f"❌ Invalid file type: {file.filename}")
            return jsonify({'error': 'Invalid file type. Please upload an Excel file (.xlsx or .xls)'}), 400
        
        print(f"✅ File type validated: {file.filename}")
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(f"✅ File saved to: {filepath}")
        
        try:
            # Process the file
            print("🔄 Starting file processing...")
            result = process_excel_file(filepath)
            print("✅ File processing completed successfully")
            return jsonify(result)
        except Exception as e:
            print(f"❌ Error processing file {filename}: {str(e)}")
            return jsonify({'error': f'File processing error: {str(e)}'}), 500
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"✅ Temporary file cleaned up: {filepath}")
            except Exception as e:
                print(f"⚠️ Error cleaning up file {filepath}: {str(e)}")
        
    except Exception as e:
        print(f"❌ Error in upload_file: {str(e)}")
        return jsonify({'error': f'Upload error: {str(e)}'}), 500

def process_excel_file(filepath):
    """Process Excel file and return translation results."""
    print("\n" + "="*50)
    print("📊 EXCEL FILE PROCESSING")
    print("="*50)
    
    try:
        # Initialize progress tracking
        app.current_progress = {
            'status': 'reading_file',
            'message': 'Reading Excel file...',
            'current_question': 0,
            'total_questions': 0,
            'current_row': 0,
            'detected_language': '',
            'confidence': 0,
            'translation': '',
            'processing_time': '',
            'api_response_time': ''
        }
        
        # Read Excel file
        print(f"📖 Reading Excel file: {filepath}")
        df = pd.read_excel(filepath, header=None)
        print(f"✅ Excel file read successfully")
        print(f"📊 DataFrame shape: {df.shape}")
        
        # Extract questions from first column
        questions = df.iloc[:, 0].dropna().tolist()
        print(f"📝 Extracted {len(questions)} questions from first column")
        
        if not questions:
            print("❌ No questions found in Excel file")
            raise ValueError("No questions found in the Excel file")
        
        if len(questions) > app.config['MAX_QUESTIONS']:
            print(f"❌ Too many questions: {len(questions)} > {app.config['MAX_QUESTIONS']}")
            raise ValueError(f"Maximum {app.config['MAX_QUESTIONS']} questions allowed per file")
        
        print(f"✅ Question count validated: {len(questions)} questions")
        
        # Update progress for processing start
        app.current_progress.update({
            'status': 'processing',
            'message': f'Starting API processing for {len(questions)} questions...',
            'total_questions': len(questions)
        })
        
        # Process questions with DeepSeek API
        results = []
        total_questions = len(questions)
        
        print(f"\n🔄 Starting API processing for {total_questions} questions...")
        print("="*50)
        
        for i, question in enumerate(questions):
            # Find the actual row number in the Excel file
            row_number = df[df.iloc[:, 0] == question].index[0] + 1 if len(df[df.iloc[:, 0] == question]) > 0 else i + 1
            # Convert to standard Python int to avoid JSON serialization issues
            row_number = int(row_number)
            
            # Update progress for current question
            app.current_progress.update({
                'status': 'processing_question',
                'message': f'Processing question {i+1}/{total_questions} (Row {row_number})',
                'current_question': i + 1,
                'current_row': row_number,
                'detected_language': 'Analyzing...',
                'confidence': 0,
                'translation': 'Waiting for language detection...',
                'processing_time': f'{i+1}/{total_questions} questions processed',
                'api_response_time': 'Language detection in progress...'
            })
            
            print(f"\n--- Question {i+1}/{total_questions} (Row {row_number}) ---")
            print(f"📝 Original: {question[:100]}{'...' if len(question) > 100 else ''}")
            
            try:
                result = process_question(question, i + 1, row_number)
                results.append(result)
                
                # Update progress with results
                app.current_progress.update({
                    'detected_language': result['detected_language'],
                    'confidence': result['confidence'],
                    'translation': result['english_translation'][:100] + ('...' if len(result['english_translation']) > 100 else ''),
                    'api_response_time': 'Translation completed'
                })
                
                print(f"✅ Question {i+1} (Row {row_number}) processed successfully")
                print(f"   Language: {result['detected_language']}")
                print(f"   Confidence: {result['confidence']}%")
                print(f"   Translation: {result['english_translation'][:50]}{'...' if len(result['english_translation']) > 50 else ''}")
                
                # Small delay to ensure progress updates are sent
                time.sleep(0.1)
            except Exception as e:
                print(f"❌ Error processing question {i+1} (Row {row_number}): {str(e)}")
                # Add error result but continue processing
                results.append({
                    'question_number': i + 1,
                    'row_number': row_number,
                    'original_question': question,
                    'detected_language': 'Error',
                    'confidence': 0,
                    'english_translation': f'Processing error: {str(e)}'
                })
                
                # Update progress with error
                app.current_progress.update({
                    'detected_language': 'Error',
                    'confidence': 0,
                    'translation': f'Processing error: {str(e)}',
                    'api_response_time': 'Error occurred'
                })
        
        # Update progress for completion
        app.current_progress.update({
            'status': 'completed',
            'message': 'Processing completed successfully!',
            'current_question': total_questions,
            'detected_language': 'Multiple languages detected',
            'confidence': 0,
            'translation': 'All questions translated to English',
            'processing_time': f'Total: {total_questions} questions processed',
            'api_response_time': 'All translations completed'
        })
        
        # Small delay to ensure completion status is sent
        time.sleep(0.5)
        
        print("\n" + "="*50)
        print("✅ ALL QUESTIONS PROCESSED")
        print(f"📊 Total processed: {len(results)}")
        print(f"📊 Successful: {len([r for r in results if r['detected_language'] != 'Error'])}")
        print(f"📊 Errors: {len([r for r in results if r['detected_language'] == 'Error'])}")
        print("="*50)
        
        return {
            'success': True,
            'results': results,
            'total_questions': len(questions),
            'processed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Excel processing error: {str(e)}")
        # Update progress with error
        app.current_progress.update({
            'status': 'error',
            'message': f'Error: {str(e)}',
            'detected_language': 'Error',
            'confidence': 0,
            'translation': f'Processing failed: {str(e)}',
            'api_response_time': 'Error occurred'
        })
        raise Exception(f"Error processing Excel file: {str(e)}")

def process_question(question, question_number, row_number=None):
    """Process a single question using DeepSeek API."""
    row_info = f" (Row {row_number})" if row_number else ""
    print(f"  🔍 Processing question {question_number}{row_info}...")
    
    try:
        # Test mode - return mock results
        if app.config.get('TEST_MODE', False):
            print(f"  🧪 TEST MODE: Returning mock results")
            return {
                'question_number': question_number,
                'original_question': question,
                'detected_language': 'English',
                'confidence': 95,
                'english_translation': f'[TEST MODE] {question}'
            }
        
        # Check if API key is configured
        if not app.config.get('DEEPSEEK_API_KEY'):
            print(f"  ❌ DeepSeek API key not configured")
            raise Exception("DeepSeek API key not configured")
        
        print(f"  ✅ API key configured: {app.config['DEEPSEEK_API_KEY'][:10]}...")
        
        # Prepare API request for language detection and translation
        headers = {
            'Authorization': f'Bearer {app.config["DEEPSEEK_API_KEY"]}',
            'Content-Type': 'application/json'
        }
        
        # First, detect language
        language_prompt = f"""
        Analyze the following text and provide the detected language, confidence score, and a detailed explanation for the confidence level.
        
        Text: "{question}"
        
        Respond with ONLY a valid JSON object in this exact format (no markdown, no code blocks):
        {{
            "language": "detected_language_name",
            "confidence": confidence_score,
            "confidence_reason": "Detailed explanation of why this specific confidence score was assigned, including both positive indicators AND reasons why it's not 100% (e.g., 'Clear Hindi vocabulary and script patterns, but some words may have multiple language origins or the text contains formatting that could affect detection', 'Strong French grammar indicators, though some technical terms or abbreviations might be from other languages', 'Mixed language indicators present with some words clearly from one language but others ambiguous')"
        }}
        
        The confidence_reason should explain:
        1. What positive indicators support the detected language
        2. Why the confidence is not 100% (what factors create uncertainty)
        3. What specific elements might be causing the uncertainty
        
        Be specific about the reasons for uncertainty, not just positive indicators.
        """
        
        language_data = {
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': language_prompt}],
            'temperature': 0.1
        }
        
        try:
            print(f"  🌐 Making language detection API call...")
            print(f"  📡 URL: {app.config['DEEPSEEK_API_URL']}")
            print(f"  ⏱️  Timeout: 15 seconds")
            
            # Update progress for language detection
            if hasattr(app, 'current_progress'):
                app.current_progress.update({
                    'detected_language': 'Detecting language...',
                    'confidence': 0,
                    'api_response_time': 'Language detection API call in progress...'
                })
            
            start_time = datetime.now()
            language_response = requests.post(
                app.config['DEEPSEEK_API_URL'],
                headers=headers,
                json=language_data,
                timeout=15  # Reduced timeout for faster feedback
            )
            end_time = datetime.now()
            api_time = (end_time - start_time).total_seconds()
            
            print(f"  ⏱️  API call completed in {api_time:.2f} seconds")
            print(f"  📊 Response status: {language_response.status_code}")
            
            if language_response.status_code != 200:
                print(f"  ❌ API Error: {language_response.status_code} - {language_response.text}")
                raise Exception(f"Language detection API error: {language_response.status_code} - {language_response.text}")
            
            print(f"  ✅ API call successful")
            language_result = language_response.json()
            
            # Handle potential JSON parsing issues in API response
            try:
                print(f"  🔍 Parsing language detection response...")
                language_content = language_result['choices'][0]['message']['content']
                print(f"  📝 Raw API response: {language_content}")
                
                # Clean up the response - remove markdown code blocks if present
                if language_content.startswith('```json'):
                    language_content = language_content.replace('```json', '').replace('```', '').strip()
                    print(f"  🧹 Cleaned JSON response: {language_content}")
                elif language_content.startswith('```'):
                    language_content = language_content.replace('```', '').strip()
                    print(f"  🧹 Cleaned response: {language_content}")
                
                language_info = json.loads(language_content)
                print(f"  ✅ JSON parsed successfully: {language_info}")
                
                # Ensure confidence is an integer percentage (0-100)
                if 'confidence' in language_info:
                    confidence_value = language_info['confidence']
                    # Handle both decimal (0.95) and percentage (95) formats
                    if isinstance(confidence_value, float) and confidence_value <= 1.0:
                        # Convert decimal to percentage (0.95 -> 95)
                        language_info['confidence'] = int(confidence_value * 100)
                    else:
                        # Already a percentage, just convert to int
                        language_info['confidence'] = int(confidence_value)
                    print(f"  📊 Confidence converted to percentage: {language_info['confidence']}%")
                
                # Update progress with detected language and confidence
                if hasattr(app, 'current_progress'):
                    app.current_progress.update({
                        'detected_language': language_info.get('language', 'Unknown'),
                        'confidence': language_info.get('confidence', 0),
                        'api_response_time': 'Language detection completed'
                    })
                    
            except (KeyError, json.JSONDecodeError) as e:
                # Fallback: assume English if parsing fails
                print(f"  ❌ JSON parsing error: {e}")
                print(f"  📝 Raw content: {language_content}")
                language_info = {"language": "English", "confidence": 90}
                print(f"  🔄 Using fallback: {language_info}")
                
                # Update progress with fallback values
                if hasattr(app, 'current_progress'):
                    app.current_progress.update({
                        'detected_language': language_info['language'],
                        'confidence': language_info['confidence'],
                        'api_response_time': 'Language detection completed (fallback)'
                    })
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during language detection: {str(e)}")
        
        # Then, translate to English
        translation_prompt = f"""
        Translate the following text to English. Maintain the original meaning and tone.
        If the text is already in English, return it unchanged.
        Preserve any HTML tags like <i>, <em>, <strong>, etc.
        
        Text: "{question}"
        
        Provide only the English translation, nothing else.
        """
        
        translation_data = {
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': translation_prompt}],
            'temperature': 0.1
        }
        
        try:
            print(f"  🌐 Making translation API call...")
            print(f"  ⏱️  Timeout: 15 seconds")
            
            # Update progress for translation
            if hasattr(app, 'current_progress'):
                app.current_progress.update({
                    'translation': 'Translating to English...',
                    'api_response_time': 'Translation API call in progress...'
                })
            
            start_time = datetime.now()
            translation_response = requests.post(
                app.config['DEEPSEEK_API_URL'],
                headers=headers,
                json=translation_data,
                timeout=15  # Reduced timeout for faster feedback
            )
            end_time = datetime.now()
            api_time = (end_time - start_time).total_seconds()
            
            print(f"  ⏱️  Translation API call completed in {api_time:.2f} seconds")
            print(f"  📊 Response status: {translation_response.status_code}")
            
            if translation_response.status_code != 200:
                print(f"  ❌ Translation API Error: {translation_response.status_code} - {translation_response.text}")
                raise Exception(f"Translation API error: {translation_response.status_code} - {translation_response.text}")
            
            print(f"  ✅ Translation API call successful")
            translation_result = translation_response.json()
            english_translation = translation_result['choices'][0]['message']['content'].strip()
            print(f"  📝 Translation result: {english_translation[:50]}{'...' if len(english_translation) > 50 else ''}")
            
            # Update progress with translation result
            if hasattr(app, 'current_progress'):
                app.current_progress.update({
                    'translation': english_translation[:100] + ('...' if len(english_translation) > 100 else ''),
                    'api_response_time': 'Translation completed'
                })
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during translation: {str(e)}")
        
        result = {
            'question_number': question_number,
            'original_question': question,
            'detected_language': language_info.get('language', 'Unknown'),
            'confidence': language_info.get('confidence', 0),
            'confidence_reason': language_info.get('confidence_reason', 'No explanation available'),
            'english_translation': english_translation
        }
        
        if row_number:
            result['row_number'] = row_number
            
        return result
        
    except Exception as e:
        row_info = f" (Row {row_number})" if row_number else ""
        print(f"Error processing question {question_number}{row_info}: {str(e)}")
        result = {
            'question_number': question_number,
            'original_question': question,
            'detected_language': 'Error',
            'confidence': 0,
            'confidence_reason': 'Processing error occurred',
            'english_translation': f'Translation error: {str(e)}'
        }
        
        if row_number:
            result['row_number'] = row_number
            
        return result

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
        df = df[['original_question', 'detected_language', 'confidence', 'confidence_reason', 'english_translation']]
        df.columns = ['Original Question', 'Detected Language', 'Confidence (%)', 'Confidence Reason', 'English Translation']
        
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