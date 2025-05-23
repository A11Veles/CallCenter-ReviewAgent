from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import json
from datetime import datetime
from pathlib import Path
import tempfile
import gdown
import traceback

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from master_agent import main as master_process # This import is unused and causes an error
from utils import extract_google_drive_file_id, get_audio_file_identifier
from master_agent import MasterAgentState, build_master_graph # Keep these essential imports

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

def download_from_gdrive(drive_link, file_type):
    """Download a file from Google Drive"""
    try:
        # Extract the file ID from the Google Drive link
        file_id = extract_google_drive_file_id(drive_link)
        if not file_id:
            raise ValueError(f"Invalid Google Drive link: {drive_link}")
            
        # Create a temporary file with the appropriate extension
        fd, temp_path = tempfile.mkstemp(suffix=f'.{file_type}')
        os.close(fd)
        
        # Download the file
        output = gdown.download(id=file_id, output=temp_path, quiet=False)
        if output is None:
            raise RuntimeError(f"Failed to download file from {drive_link}")
            
        return output
    except Exception as e:
        raise Exception(f"Error downloading from Google Drive: {str(e)}")

def validate_audio_file(file_path, allowed_extensions=None):
    """Validate that the file exists and is an audio file"""
    if not allowed_extensions:
        allowed_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac']
        
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in allowed_extensions:
        raise ValueError(f"Invalid file type: {ext}. Allowed types: {', '.join(allowed_extensions)}")
    
    # Check file size (example: max 100MB)
    max_size = 100 * 1024 * 1024  # 100MB in bytes
    if os.path.getsize(file_path) > max_size:
        raise ValueError(f"File too large. Maximum size: 100MB")
        
    return True

# ... (rest of file omitted for brevity, but will be uploaded in full) ...
