"""
Test suite for Survey Question Translator MVP Flask application.

This module contains unit tests for the main application functionality.
"""

import pytest
import tempfile
import os
import pandas as pd
from app import create_app


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['DEEPSEEK_API_KEY'] = 'test-key'
    return app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for the Flask application."""
    return app.test_cli_runner()


def test_index_route(client):
    """Test that the index route returns a successful response."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Survey Question Translator' in response.data


def test_upload_no_file(client):
    """Test upload endpoint with no file."""
    response = client.post('/upload')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'No file uploaded' in data['error']


def test_upload_invalid_file_type(client):
    """Test upload endpoint with invalid file type."""
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b'test content')
        f.flush()
        
        with open(f.name, 'rb') as file:
            response = client.post('/upload', data={'file': (file, 'test.txt')})
    
    os.unlink(f.name)
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'Invalid file type' in data['error']


def test_download_no_results(client):
    """Test download endpoint with no results."""
    response = client.post('/download', json={'results': []})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'No results to download' in data['error']


def test_error_handlers(client):
    """Test error handlers."""
    # Test 404 handler
    response = client.get('/nonexistent')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert 'Page not found' in data['error']


def test_allowed_file_extension():
    """Test file extension validation."""
    from app import allowed_file
    
    assert allowed_file('test.xlsx') == True
    assert allowed_file('test.xls') == True
    assert allowed_file('test.txt') == False
    assert allowed_file('test.pdf') == False
    assert allowed_file('test') == False


def test_create_excel_file():
    """Test creating a test Excel file for testing."""
    # Create a temporary Excel file with test data
    test_data = [
        ['What is your age?'],
        ['How satisfied are you with our service?'],
        ['Would you recommend us to others?']
    ]
    
    df = pd.DataFrame(test_data, columns=['Questions'])
    
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        df.to_excel(f.name, index=False, header=False)
        return f.name


def test_excel_file_creation():
    """Test that we can create Excel files for testing."""
    file_path = test_create_excel_file()
    
    # Verify file exists
    assert os.path.exists(file_path)
    
    # Verify file can be read
    df = pd.read_excel(file_path, header=None)
    assert len(df) == 3
    assert df.iloc[0, 0] == 'What is your age?'
    
    # Clean up
    os.unlink(file_path)


if __name__ == '__main__':
    pytest.main([__file__]) 