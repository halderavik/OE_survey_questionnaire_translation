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
    """Stream real-time progress updates with Heroku timeout handling."""
    def generate():
        start_time = time.time()
        last_progress = None
        
        while True:
            # Check for timeout (15 seconds to be safe on Heroku)
            if time.time() - start_time > 15:
                # Send a keepalive message and break
                yield f"data: {json.dumps({'status': 'timeout', 'message': 'Connection timeout - please reconnect'})}\n\n"
                break
            
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
                
                # Only send if data has changed or it's been more than 0.5 seconds
                current_time = time.time()
                if (last_progress != progress_data or 
                    current_time - start_time > 0.5):
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    last_progress = progress_data.copy()
                    
                    # If processing is complete, break the connection
                    if progress_data.get('status') in ['completed', 'error']:
                        break
            
            # Shorter sleep for more responsive updates
            time.sleep(0.2)
    
    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',  # Disable Nginx buffering
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )

@app.route('/progress-simple', methods=['GET'])
def progress_simple():
    """Simple progress endpoint for polling (fallback when SSE fails)."""
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
        
        return jsonify(progress_data)
    else:
        return jsonify({
            'status': 'waiting',
            'message': 'No processing in progress',
            'current_question': 0,
            'total_questions': 0,
            'current_row': 0,
            'detected_language': '',
            'confidence': 0,
            'translation': '',
            'processing_time': '',
            'api_response_time': ''
        })

@app.route('/continue-batch', methods=['POST'])
def continue_batch():
    """Continue processing the next batch of questions."""
    try:
        print("\n" + "="*50)
        print("🔄 CONTINUE BATCH PROCESSING")
        print("="*50)
        
        # Check if there are pending questions
        if not hasattr(app, 'pending_questions') or not hasattr(app, 'current_batch_start'):
            return jsonify({'error': 'No pending questions to process'}), 400
        
        total_questions = len(app.pending_questions)
        current_batch_start = app.current_batch_start
        
        if current_batch_start >= total_questions:
            return jsonify({'error': 'All questions have been processed'}), 400
        
        print(f"📊 Continuing from question {current_batch_start + 1}")
        print(f"📊 Remaining questions: {total_questions - current_batch_start}")
        
        # Create a temporary file path for the batch processing
        # Since we don't have the original file, we'll use a dummy path
        # The actual questions are stored in app.pending_questions
        dummy_filepath = "/tmp/batch_continuation.xlsx"
        
        # Process the next batch
        result = process_excel_file_with_timeout(dummy_filepath)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error continuing batch: {str(e)}")
        return jsonify({'error': f'Batch continuation error: {str(e)}'}), 500

@app.route('/auto-continue-batch', methods=['POST'])
def auto_continue_batch():
    """Automatically continue processing batches until completion."""
    try:
        print("\n" + "="*50)
        print("🤖 AUTO BATCH PROCESSING")
        print("="*50)
        
        # Check if there are pending questions
        if not hasattr(app, 'pending_questions') or not hasattr(app, 'current_batch_start'):
            return jsonify({'error': 'No pending questions to process'}), 400
        
        total_questions = len(app.pending_questions)
        current_batch_start = app.current_batch_start
        
        if current_batch_start >= total_questions:
            return jsonify({'error': 'All questions have been processed'}), 400
        
        print(f"📊 Auto-continuing from question {current_batch_start + 1}")
        print(f"📊 Remaining questions: {total_questions - current_batch_start}")
        
        # Process batches automatically until completion
        batch_count = 0
        
        while current_batch_start < total_questions:
            batch_count += 1
            print(f"\n🔄 Processing auto-batch {batch_count}")
            
            # Calculate batch end
            batch_size = 3  # Same as in process_excel_file_with_timeout
            batch_end = min(current_batch_start + batch_size, total_questions)
            
            # Process the current batch
            batch_results = []
            start_time = time.time()
            
            for i, question in enumerate(app.pending_questions[current_batch_start:batch_end]):
                # Check for Heroku timeout (25 seconds)
                if time.time() - start_time > 25:
                    print(f"⚠️ Heroku timeout approaching, stopping batch {batch_count}")
                    # Mark remaining questions in this batch as pending
                    for j in range(i, batch_end - current_batch_start):
                        batch_results.append({
                            'question_number': current_batch_start + j + 1,
                            'row_number': current_batch_start + j + 1,
                            'original_question': app.pending_questions[current_batch_start + j],
                            'detected_language': 'Pending (timeout)',
                            'confidence': 0,
                            'english_translation': 'Processing stopped due to timeout'
                        })
                    break
                
                # Process the question
                global_question_index = current_batch_start + i
                row_number = global_question_index + 1
                
                # Update progress for current question
                app.current_progress.update({
                    'status': 'processing_question',
                    'message': f'Processing question {global_question_index + 1}/{total_questions} (Row {row_number})',
                    'current_question': global_question_index + 1,
                    'current_row': row_number,
                    'detected_language': 'Analyzing...',
                    'confidence': 0,
                    'translation': 'Waiting for language detection...',
                    'processing_time': f'{global_question_index + 1}/{total_questions} questions processed',
                    'api_response_time': 'Language detection in progress...'
                })
                
                # Force a small delay to ensure progress is updated
                time.sleep(0.1)
                
                print(f"\n--- Question {global_question_index + 1}/{total_questions} (Row {row_number}) ---")
                print(f"📝 Original: {question[:100]}{'...' if len(question) > 100 else ''}")
                
                try:
                    result = process_question(question, global_question_index + 1, row_number)
                    batch_results.append(result)
                    
                    # Update progress with results
                    app.current_progress.update({
                        'detected_language': result['detected_language'],
                        'confidence': result['confidence'],
                        'translation': result['english_translation'][:100] + ('...' if len(result['english_translation']) > 100 else ''),
                        'api_response_time': 'Translation completed'
                    })
                    
                    # Force a small delay to ensure progress is updated
                    time.sleep(0.1)
                    
                    print(f"✅ Question {global_question_index + 1} (Row {row_number}) processed successfully")
                    print(f"   Language: {result['detected_language']}")
                    print(f"   Confidence: {result['confidence']}%")
                    print(f"   Translation: {result['english_translation'][:50]}{'...' if len(result['english_translation']) > 50 else ''}")
                except Exception as e:
                    print(f"❌ Error processing question {global_question_index + 1} (Row {row_number}): {str(e)}")
                    # Add error result but continue processing
                    batch_results.append({
                        'question_number': global_question_index + 1,
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
            
            # Add batch results to processed results
            app.processed_results.extend(batch_results)
            
            # Update batch start for next batch
            app.current_batch_start = batch_end
            
            # Check if all questions are processed
            if batch_end >= total_questions:
                # All questions processed
                processed_count = len([r for r in app.processed_results if r['detected_language'] not in ['Error', 'Pending (timeout)']])
                pending_count = len([r for r in app.processed_results if r['detected_language'] == 'Pending (timeout)'])
                
                completion_message = f'Processing completed! {processed_count}/{total_questions} questions processed'
                if pending_count > 0:
                    completion_message += f' ({pending_count} pending due to timeout)'
                
                app.current_progress.update({
                    'status': 'completed',
                    'message': completion_message,
                    'current_question': total_questions,
                    'detected_language': 'Multiple languages detected',
                    'confidence': 0,
                    'translation': f'{processed_count}/{total_questions} questions translated to English',
                    'processing_time': f'Total: {processed_count} questions processed',
                    'api_response_time': 'Processing completed'
                })
                
                # Clear session data
                delattr(app, 'pending_questions')
                delattr(app, 'processed_results')
                delattr(app, 'current_batch_start')
                
                print(f"✅ All batches completed after {batch_count} iterations")
                break
            
            # Small delay between batches to prevent overwhelming the system
            time.sleep(0.5)
        
        # Return final results
        final_result = {
            'success': True,
            'results': app.processed_results,
            'total_questions': total_questions,
            'processed_at': datetime.now().isoformat(),
            'batch_complete': True,
            'auto_processed': True,
            'batches_processed': batch_count
        }
        
        return jsonify(final_result)
        
    except Exception as e:
        print(f"❌ Error in auto batch processing: {str(e)}")
        return jsonify({'error': f'Auto batch processing error: {str(e)}'}), 500

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
            # Process the file with timeout handling
            print("🔄 Starting file processing...")
            result = process_excel_file_with_timeout(filepath)
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

def process_excel_file_with_timeout(filepath):
    """Process Excel file with batch processing to handle Heroku timeout limits."""
    print("\n" + "="*50)
    print("📊 EXCEL FILE PROCESSING (BATCH-AWARE)")
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
        
        # Store questions in session for batch processing
        if not hasattr(app, 'pending_questions'):
            app.pending_questions = questions
            app.processed_results = []
            app.current_batch_start = 0
        
        # Get current batch info
        batch_size = 3  # Process 3 questions per batch
        total_questions = len(app.pending_questions)
        current_batch_start = getattr(app, 'current_batch_start', 0)
        
        # Calculate batch end
        batch_end = min(current_batch_start + batch_size, total_questions)
        current_batch_questions = app.pending_questions[current_batch_start:batch_end]
        
        print(f"\n🔄 Processing batch {current_batch_start//batch_size + 1}: questions {current_batch_start + 1}-{batch_end}")
        print(f"📊 Batch size: {len(current_batch_questions)} questions")
        print(f"📊 Total progress: {len(app.processed_results)}/{total_questions} completed")
        print("="*50)
        
        # Update progress for batch start
        app.current_progress.update({
            'status': 'processing_batch',
            'message': f'Processing batch {current_batch_start//batch_size + 1}: questions {current_batch_start + 1}-{batch_end}',
            'total_questions': total_questions,
            'current_question': current_batch_start + 1
        })
        
        # Process current batch
        batch_results = []
        start_time = time.time()
        
        for i, question in enumerate(current_batch_questions):
            # Check if we're approaching Heroku's 30-second timeout (use 25 seconds to be safe)
            if time.time() - start_time > 25:
                print(f"⚠️ Approaching Heroku timeout, stopping batch at question {current_batch_start + i + 1}")
                # Add remaining questions in this batch as pending
                for j in range(i, len(current_batch_questions)):
                    global_question_index = current_batch_start + j
                    row_number = df[df.iloc[:, 0] == app.pending_questions[global_question_index]].index[0] + 1 if len(df[df.iloc[:, 0] == app.pending_questions[global_question_index]]) > 0 else global_question_index + 1
                    row_number = int(row_number)
                    
                    batch_results.append({
                        'question_number': global_question_index + 1,
                        'row_number': row_number,
                        'original_question': app.pending_questions[global_question_index],
                        'detected_language': 'Pending (timeout)',
                        'confidence': 0,
                        'english_translation': 'Processing stopped due to timeout'
                    })
                break
            
            # Find the actual row number in the Excel file
            global_question_index = current_batch_start + i
            row_number = df[df.iloc[:, 0] == question].index[0] + 1 if len(df[df.iloc[:, 0] == question]) > 0 else global_question_index + 1
            row_number = int(row_number)
            
            # Update progress for current question
            app.current_progress.update({
                'status': 'processing_question',
                'message': f'Processing question {global_question_index + 1}/{total_questions} (Row {row_number})',
                'current_question': global_question_index + 1,
                'current_row': row_number,
                'detected_language': 'Analyzing...',
                'confidence': 0,
                'translation': 'Waiting for language detection...',
                'processing_time': f'{global_question_index + 1}/{total_questions} questions processed',
                'api_response_time': 'Language detection in progress...'
            })
            
            # Force a small delay to ensure progress is updated
            time.sleep(0.1)
            
            print(f"\n--- Question {global_question_index + 1}/{total_questions} (Row {row_number}) ---")
            print(f"📝 Original: {question[:100]}{'...' if len(question) > 100 else ''}")
            
            try:
                result = process_question(question, global_question_index + 1, row_number)
                batch_results.append(result)
                
                # Update progress with results
                app.current_progress.update({
                    'detected_language': result['detected_language'],
                    'confidence': result['confidence'],
                    'translation': result['english_translation'][:100] + ('...' if len(result['english_translation']) > 100 else ''),
                    'api_response_time': 'Translation completed'
                })
                
                # Force a small delay to ensure progress is updated
                time.sleep(0.1)
                
                print(f"✅ Question {global_question_index + 1} (Row {row_number}) processed successfully")
                print(f"   Language: {result['detected_language']}")
                print(f"   Confidence: {result['confidence']}%")
                print(f"   Translation: {result['english_translation'][:50]}{'...' if len(result['english_translation']) > 50 else ''}")
            except Exception as e:
                print(f"❌ Error processing question {global_question_index + 1} (Row {row_number}): {str(e)}")
                # Add error result but continue processing
                batch_results.append({
                    'question_number': global_question_index + 1,
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
        
        # Add batch results to processed results
        app.processed_results.extend(batch_results)
        
        # Update batch start for next batch
        app.current_batch_start = batch_end
        
        # Check if all questions are processed
        if batch_end >= total_questions:
            # All questions processed
            processed_count = len([r for r in app.processed_results if r['detected_language'] not in ['Error', 'Pending (timeout)']])
            pending_count = len([r for r in app.processed_results if r['detected_language'] == 'Pending (timeout)'])
            
            completion_message = f'Processing completed! {processed_count}/{total_questions} questions processed'
            if pending_count > 0:
                completion_message += f' ({pending_count} pending due to timeout)'
            
            app.current_progress.update({
                'status': 'completed',
                'message': completion_message,
                'current_question': total_questions,
                'detected_language': 'Multiple languages detected',
                'confidence': 0,
                'translation': f'{processed_count}/{total_questions} questions translated to English',
                'processing_time': f'Total: {processed_count} questions processed',
                'api_response_time': 'Processing completed'
            })
            
            # Clear session data
            delattr(app, 'pending_questions')
            delattr(app, 'processed_results')
            delattr(app, 'current_batch_start')
            
            print("\n" + "="*50)
            print("✅ ALL BATCHES COMPLETED")
            print(f"📊 Total questions: {len(app.processed_results)}")
            print(f"📊 Successfully processed: {len([r for r in app.processed_results if r['detected_language'] not in ['Error', 'Pending (timeout)']])}")
            print(f"📊 Errors: {len([r for r in app.processed_results if r['detected_language'] == 'Error'])}")
            print(f"📊 Pending (timeout): {len([r for r in app.processed_results if r['detected_language'] == 'Pending (timeout)'])}")
            print("="*50)
            
            return {
                'success': True,
                'results': app.processed_results,
                'total_questions': total_questions,
                'processed_at': datetime.now().isoformat(),
                'batch_complete': True
            }
        else:
            # More batches to process
            processed_count = len([r for r in app.processed_results if r['detected_language'] not in ['Error', 'Pending (timeout)']])
            
            batch_completion_message = f'Batch {current_batch_start//batch_size + 1} completed! {processed_count}/{total_questions} questions processed so far'
            
            app.current_progress.update({
                'status': 'batch_completed',
                'message': batch_completion_message,
                'current_question': batch_end,
                'detected_language': 'Batch completed',
                'confidence': 0,
                'translation': f'{processed_count}/{total_questions} questions translated to English',
                'processing_time': f'Batch {current_batch_start//batch_size + 1} completed',
                'api_response_time': 'Ready for next batch'
            })
            
            print("\n" + "="*50)
            print(f"✅ BATCH {current_batch_start//batch_size + 1} COMPLETED")
            print(f"📊 Questions processed in this batch: {len(batch_results)}")
            print(f"📊 Total progress: {len(app.processed_results)}/{total_questions}")
            print(f"📊 Next batch: questions {batch_end + 1}-{min(batch_end + batch_size, total_questions)}")
            print("="*50)
            
            return {
                'success': True,
                'results': app.processed_results,
                'total_questions': total_questions,
                'processed_at': datetime.now().isoformat(),
                'batch_complete': False,
                'next_batch_start': batch_end,
                'remaining_questions': total_questions - batch_end,
                'batch_message': f'Batch {current_batch_start//batch_size + 1} completed. {total_questions - batch_end} questions remaining.'
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
        Analyze the following text and provide the detected language and confidence score.
        
        Text: "{question}"
        
        Respond with ONLY a valid JSON object in this exact format (no markdown, no code blocks):
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
                timeout=10  # Further reduced timeout for Heroku
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
                timeout=10  # Further reduced timeout for Heroku
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
    # Get port from environment variable (Heroku sets PORT)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 