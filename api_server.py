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

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_audio():
    print("[API_SERVER] Entered analyze_audio route") # Log 1
    if request.method == 'OPTIONS':
        print("[API_SERVER] Handling OPTIONS request") # Log 2
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    audio_path = None # Initialize for potential cleanup in error handling
    try:
        print("[API_SERVER] Inside TRY block of analyze_audio") # Log 3
        
        print(f"[API_SERVER] Request headers: {request.headers}") # Log 4
        print(f"[API_SERVER] Request content type: {request.content_type}") # Log 5
        
        if not request.is_json:
            print("[API_SERVER] Error: Request is not JSON (Content-Type is not application/json)") # Log 6
            return jsonify({'status': 'error', 'message': 'Request content type must be application/json'}), 400

        data = request.json
        print(f"[API_SERVER] Request JSON data: {data}") # Log 7

        if data is None:
            print("[API_SERVER] Error: request.json is None (failed to parse JSON or no data sent)") # Log 8
            return jsonify({'status': 'error', 'message': 'Failed to parse JSON data or no JSON data sent.'}), 400

        drive_link = data.get('driveLink')
        file_type = data.get('fileType', 'mp3') # Default to 'mp3' if not provided
        prompt = data.get('prompt')
        print(f"[API_SERVER] Extracted from JSON - drive_link: {drive_link}, file_type: {file_type}, prompt: {prompt}") # Log 9

        if not drive_link:
            print("[API_SERVER] Error: 'driveLink' is missing from JSON payload") # Log 10
            return jsonify({'status': 'error', 'message': 'driveLink is required in JSON payload'}), 400

        print("[API_SERVER] Attempting to extract file ID from drive_link") # Log 11
        file_id = extract_google_drive_file_id(drive_link)
        if not file_id:
            print(f"[API_SERVER] Error: Could not extract file ID from drive_link: {drive_link}") # Log 12
            return jsonify({'status': 'error', 'message': 'Invalid Google Drive link or unable to extract file ID.'}), 400
        print(f"[API_SERVER] Extracted file_id: {file_id}") # Log 13

        # Map front-end modes to proper file extension
        allowed_extensions = ['mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac']
        if file_type.lower() in ['single', 'folder', None, '']:
            # "single" means a single audio file but we don't know the ext – default to wav
            inferred_ext = 'wav'
        else:
            inferred_ext = file_type.lower() if file_type.lower() in allowed_extensions else 'wav'
        
        is_folder_mode = file_type.lower() == 'folder'
        print(f"[API_SERVER] Using inferred extension '.{inferred_ext}' for temp file (is_folder_mode={is_folder_mode})")

        print("[API_SERVER] Preparing temporary file for download") # Log 14
        # Create a temporary file to store the downloaded audio with correct extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{inferred_ext}") as tmpfile:
            audio_path = tmpfile.name
        print(f"[API_SERVER] Temporary file created: {audio_path}") # Log 15
        
        print(f"[API_SERVER] Starting download with gdown: link='{drive_link}', output='{audio_path}'") # Log 16
        output_path = gdown.download(url=drive_link, output=audio_path, quiet=False, fuzzy=True)
        print(f"[API_SERVER] gdown.download finished. Returned output_path: {output_path}") # Log 17

        if output_path is None:
            print(f"[API_SERVER] Error: gdown.download returned None. Download failed. audio_path: {audio_path}") # Log 18
            if audio_path and os.path.exists(audio_path): os.remove(audio_path) # Clean up failed download
            return jsonify({'status': 'error', 'message': 'File download failed (gdown returned None).'}), 500
        
        if not os.path.exists(audio_path):
            print(f"[API_SERVER] Error: audio_path does not exist after download: {audio_path}") # Log 19
            return jsonify({'status': 'error', 'message': 'File download failed (file not found after download attempt).'}), 500

        if os.path.getsize(audio_path) == 0:
            print(f"[API_SERVER] Error: Downloaded file is empty. audio_path: {audio_path}") # Log 20
            if audio_path and os.path.exists(audio_path): os.remove(audio_path) # Clean up empty file
            return jsonify({'status': 'error', 'message': 'Downloaded file is empty.'}), 500
        
        print(f"[API_SERVER] Download successful. File at: {audio_path}, size: {os.path.getsize(audio_path)} bytes") # Log 21
        
        # Build the master graph
        print("[API_SERVER] Building master graph...")
        master_graph = build_master_graph()
        
        print(f"[API_SERVER] Creating initial state with local_path: {audio_path}, drive_link: {drive_link}, prompt: {prompt}")
        initial_state = MasterAgentState(
            initial_google_drive_link=drive_link,
            current_local_audio_path=audio_path,
            is_folder=False,
            user_prompt=prompt if prompt else "Analyze this call for quality and customer satisfaction."
        )
        
        print(f"[API_SERVER] Invoking master_graph with initial_state: {initial_state.model_dump_json(indent=2)}")
        graph_final_state = None # Initialize for clarity
        try:
            graph_final_state = master_graph.invoke(initial_state)
            # The final state from invoke() is a dictionary
            final_status = graph_final_state.get('overall_status') if isinstance(graph_final_state, dict) else 'N/A'
            print(f"[API_SERVER] Master graph completed. Final state status: {final_status}")
        except Exception as graph_exc:
            print(f"[API_SERVER] EXCEPTION during master_graph.invoke: {str(graph_exc)}")
            print(f"[API_SERVER] Traceback for master_graph.invoke exception: {traceback.format_exc()}")
            if audio_path and os.path.exists(audio_path): os.remove(audio_path) # Clean up on graph error
            return jsonify({
                'status': 'error',
                'message': 'Error during backend processing graph execution.',
                'details': str(graph_exc)
            }), 500

        master_json_path = 'master_processing_log.json'
        print(f"[API_SERVER] Looking for results in {master_json_path}")
        
        if not os.path.exists(master_json_path):
            print(f"[API_SERVER] Error: {master_json_path} not found after processing.")
            if audio_path and os.path.exists(audio_path): os.remove(audio_path) # Clean up if log is missing
            return jsonify({'status': 'error', 'message': 'Processing log not found.'}), 500

        with open(master_json_path, 'r') as f:
            log_data = json.load(f)
        
        current_file_identifier = get_audio_file_identifier(drive_link, audio_path)
        print(f"[API_SERVER] Current file identifier for log lookup: {current_file_identifier}")

        # Find the specific entry for the processed file
        file_result = next((item for item in log_data.get("audio_files", []) if item["file_identifier"] == current_file_identifier), None)

        if not file_result:
            print(f"[API_SERVER] Error: No result found in log for identifier {current_file_identifier}")
            # Don't delete audio_path here, as it might be a valid file master_agent just didn't log for some reason
            return jsonify({'status': 'error', 'message': f'No processing result found for the file in {master_json_path}.'}), 500

        print(f"[API_SERVER] Successfully found result for {current_file_identifier} in log.")
        # If we reach here, processing was successful and logged.
        # The audio_path should NOT be deleted by api_server, as master_agent might still need it or have moved it.
        return jsonify({
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'analysis': {
                'audio_files': [file_result]
            },
            'message': 'Audio processed successfully.'
        }), 200

    except Exception as e:
        error_traceback = traceback.format_exc()
        error_message = str(e)
        print(f"[API_SERVER] EXCEPTION in analyze_audio (outer try-except): {error_message}")
        print(f"[API_SERVER] Traceback: {error_traceback}")
        
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"[API_SERVER] Cleaned up temp file on error: {audio_path}")
            except OSError as oe:
                print(f"[API_SERVER] Error cleaning up temp file {audio_path} on error: {oe}")
        
        # Determine appropriate status code based on error type if possible
        # For now, defaulting to 500 for unexpected server errors
        return jsonify({
            'status': 'error',
            'message': f'An unexpected error occurred on the server: {error_message}',
            'details': error_traceback 
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'CallCenter ReviewAgent API'
    })

@app.route('/', methods=['GET'])
def serve_frontend():
    # This route serves the index.html file
    return app.send_static_file('index.html')

if __name__ == '__main__':
    # Check if Flask static folder is set correctly
    if not os.path.exists('static'):
        os.makedirs('static', exist_ok=True)
        
    # Create a symlink to index.html in the static folder if it doesn't exist
    static_index_path = os.path.join('static', 'index.html')
    if not os.path.exists(static_index_path):
        try:
            # On Unix-like systems
            os.symlink(os.path.abspath('index.html'), static_index_path)
        except (OSError, AttributeError):
            # On Windows or if symlink fails
            import shutil
            shutil.copy2('index.html', static_index_path)
    
    print("Starting CallCenter ReviewAgent API server on port 5001")
    app.run(debug=True, host='0.0.0.0', port=5001)