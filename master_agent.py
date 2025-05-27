import os
import argparse
import json
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
import gdown
import tempfile
from datetime import datetime

# Attempt to import Google API client libraries
try:
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("WARNING: Google API client libraries not found. Folder processing will be limited.")

from utils import (
    initialize_master_json, 
    save_master_json, 
    get_audio_file_identifier,
    add_agent_output_to_master_json,
    extract_google_drive_file_id,
    scrape_google_drive_folder,
    MASTER_JSON_FILE
)

# Placeholder for refactored agents - these will be imported later
from transcription_diarization_agent import process_audio_for_transcription_diarization
from evaluation_agent_refactored import run_evaluation_analysis
from noise_analysis_agent import run_noise_analysis
from recommendation_agent_refactored import run_recommendation_generation
from summary_agent_refactored import run_summary_generation

# --- Master Agent State ---
class MasterAgentState(BaseModel):
    master_json_data: Dict[str, Any] = Field(default_factory=initialize_master_json)
    initial_google_drive_link: Optional[str] = None # The original link provided by the user
    current_processing_link: Optional[str] = None # Link of the file currently being processed
    current_file_identifier: Optional[str] = None
    current_local_audio_path: Optional[str] = None
    user_prompt: Optional[str] = None
    is_folder: bool = False # Flag to indicate if the link is a folder
    files_to_process_queue: List[Dict[str, str]] = Field(default_factory=list) # Queue of {'link': str, 'identifier': str}
    processed_files_count: int = 0
    total_files_to_process: int = 0
    overall_status: str = "pending"
    error_message: Optional[str] = None

# --- Helper Functions ---
def get_files_in_folder(folder_id: str) -> List[Dict[str, str]]:
    """Returns a list of files in a Google Drive folder.
    Uses dynamic scraping to find all files without requiring OAuth.
    """
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    print(f"Dynamically scanning folder contents for: {folder_url}")
    
    # Use the scrape_google_drive_folder function to get all files in the folder
    files = scrape_google_drive_folder(folder_url)
    
    # Filter for audio files if needed (optional)
    audio_extensions = [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"]
    audio_files = []
    
    for file in files:
        file_name = file.get('name', '')
        # Check if this is an audio file based on extension
        if any(file_name.lower().endswith(ext) for ext in audio_extensions):
            audio_files.append(file)
        else:
            # Keep non-audio files too, but log them
            print(f"Note: Found non-audio file in folder: {file_name}")
            audio_files.append(file)  # Include all files for now
    
    if not audio_files:
        print(f"Warning: No files found in folder with ID: {folder_id}")
        print("Please check that the folder exists and is publicly accessible.")
    else:
        print(f"Found {len(audio_files)} files in the folder.")
        
    return audio_files

# --- Node Functions for Master Agent Workflow ---

def initialize_processing_node(state: MasterAgentState) -> MasterAgentState:
    print("--- MASTER AGENT: Initializing Processing ---")
    state.master_json_data = initialize_master_json() # Ensure it's loaded/re-initialized
    state.files_to_process_queue = []
    state.processed_files_count = 0
    state.total_files_to_process = 0

    if not state.initial_google_drive_link and not state.current_local_audio_path:
        state.error_message = "No Google Drive link or local file path provided."
        state.overall_status = "failed_initialization"
        print(state.error_message)
        return state

    link_to_process = state.initial_google_drive_link
    print(f"Initial link: {link_to_process if link_to_process else 'N/A (local file provided)'}")
    print(f"Initial local path: {state.current_local_audio_path if state.current_local_audio_path else 'N/A'}")

    if state.is_folder:
        if not link_to_process: # Folder processing requires a drive link
            state.error_message = "Folder processing requires a Google Drive link."
            state.overall_status = "failed_initialization"
            print(state.error_message)
            return state
        print(f"Processing as folder link: {link_to_process}")
        folder_id = extract_google_drive_file_id(link_to_process)
        if not folder_id:
            state.error_message = f"Could not extract folder ID from {link_to_process}"
            state.overall_status = "failed_initialization"
            print(state.error_message)
            return state
        # Get files in the folder using our dynamic folder scanning approach
        files_in_folder = get_files_in_folder(folder_id)
        if not files_in_folder:
            state.error_message = f"No audio files found in folder {folder_id} or folder ID not recognized."
            state.overall_status = "no_files_found"
            print(state.error_message)
        else:
            for f_item in files_in_folder:
                file_id = f_item.get('identifier')
                if file_id:
                    queue_item = {
                        'link': f_item['link'],
                        'identifier': file_id,
                        'name': f_item.get('name', file_id)
                    }
                    
                    # If the file was already downloaded locally by the folder scanner,
                    # include the local path to skip the download step
                    if 'local_path' in f_item and os.path.exists(f_item['local_path']):
                        queue_item['local_path'] = f_item['local_path']
                        print(f"Using pre-downloaded file: {f_item['local_path']}")
                    
                    state.files_to_process_queue.append(queue_item)
                else:
                    print(f"Warning: Missing file ID for {f_item.get('name', 'unknown file')}")

    else: # Single file link or local path
        identifier = None
        queue_item = {}

        if state.current_local_audio_path and os.path.exists(state.current_local_audio_path):
            print(f"Processing pre-downloaded local file: {state.current_local_audio_path}")
            # Use filename or a hash of the path as identifier if no drive link
            identifier = get_audio_file_identifier(local_path=state.current_local_audio_path, audio_url=link_to_process)
            queue_item = {
                'link': link_to_process, # Can be None if only local path was given
                'identifier': identifier,
                'name': os.path.basename(state.current_local_audio_path),
                'local_path': state.current_local_audio_path
            }
        elif link_to_process: # Single file link, needs download
            print(f"Processing as single file link (will download): {link_to_process}")
            identifier = get_audio_file_identifier(audio_url=link_to_process)
            if identifier:
                queue_item = {'link': link_to_process, 'identifier': identifier, 'name': identifier}
        
        if identifier and queue_item:
            state.files_to_process_queue.append(queue_item)
        else:
            state.error_message = f"Could not get identifier for single file. Link: {link_to_process}, Local Path: {state.current_local_audio_path}"
            state.overall_status = "failed_initialization"
            print(state.error_message)
            return state

    state.total_files_to_process = len(state.files_to_process_queue)
    if state.total_files_to_process > 0:
        print(f"Initialized. Found {state.total_files_to_process} file(s) to process.")
        state.overall_status = "initialized"
    else:
        print("No files found to process after initialization.")
        state.overall_status = "no_files_found"
    save_master_json(state.master_json_data) # Save initial state of master_json
    return state

def select_next_file_node(state: MasterAgentState) -> MasterAgentState:
    print(f"--- MASTER AGENT: Selecting Next File ({state.processed_files_count + 1} of {state.total_files_to_process}) ---")
    state.current_local_audio_path = None # Reset from previous file
    state.error_message = None # Reset from previous file's potential errors

    if not state.files_to_process_queue:
        print("No more files in the queue.")
        state.current_processing_link = None
        state.current_file_identifier = None
        return state

    next_file_info = state.files_to_process_queue.pop(0)
    state.current_processing_link = next_file_info['link']
    state.current_file_identifier = next_file_info['identifier']
    # If a local path was provided during initialization (e.g., from api_server or folder scan), set it now
    state.current_local_audio_path = next_file_info.get('local_path') 
    
    print(f"Next file to process: {next_file_info.get('name', state.current_file_identifier)} (Link: {state.current_processing_link}, Local: {state.current_local_audio_path})")
    
    # Add this file to the master_json if not already there
    if state.current_file_identifier not in state.master_json_data.get('files', {}):
        state.master_json_data.setdefault('files', {})[state.current_file_identifier] = {
            'identifier': state.current_file_identifier,
            'link': state.current_processing_link,
            'status': 'selected',
            'timestamp': datetime.now().isoformat(),
            'processing_steps': {}
        }
        save_master_json(state.master_json_data)
    
    return state

def download_audio_node(state: MasterAgentState) -> MasterAgentState:
    print(f"--- MASTER AGENT: Downloading Audio for {state.current_file_identifier} ---")
    
    # If we already have a local path from initialization, skip download
    if state.current_local_audio_path and os.path.exists(state.current_local_audio_path):
        print(f"Using pre-downloaded file: {state.current_local_audio_path}")
        # Update the master JSON with the download status
        if state.current_file_identifier in state.master_json_data.get('files', {}):
            state.master_json_data['files'][state.current_file_identifier]['status'] = 'downloaded'
            state.master_json_data['files'][state.current_file_identifier]['local_path'] = state.current_local_audio_path
            save_master_json(state.master_json_data)
        return state
    
    # If no link, we can't download
    if not state.current_processing_link:
        state.error_message = "No link provided for download."
        if state.current_file_identifier in state.master_json_data.get('files', {}):
            state.master_json_data['files'][state.current_file_identifier]['status'] = 'download_failed'
            state.master_json_data['files'][state.current_file_identifier]['error'] = state.error_message
            save_master_json(state.master_json_data)
        print(state.error_message)
        return state
    
    try:
        # Extract the file ID from the Google Drive link
        file_id = extract_google_drive_file_id(state.current_processing_link)
        if not file_id:
            raise ValueError(f"Invalid Google Drive link: {state.current_processing_link}")
        
        # Create a temporary file with a proper audio extension
        # Important: Use a real audio extension, not .single, for OpenAI to recognize the format
        audio_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac']
        # Try to guess extension from link, default to .mp3 if can't determine
        extension = '.mp3'  # Default
        for ext in audio_extensions:
            if state.current_processing_link.lower().endswith(ext):
                extension = ext
                break
        
        fd, temp_path = tempfile.mkstemp(suffix=extension)
        os.close(fd)
        
        print(f"Downloading file ID {file_id} to {temp_path}")
        output = gdown.download(id=file_id, output=temp_path, quiet=False)
        
        if output is None:
            raise RuntimeError(f"Failed to download file from {state.current_processing_link}")
        
        state.current_local_audio_path = output
        print(f"Successfully downloaded to {state.current_local_audio_path}")
        
        # Update the master JSON with the download status
        if state.current_file_identifier in state.master_json_data.get('files', {}):
            state.master_json_data['files'][state.current_file_identifier]['status'] = 'downloaded'
            state.master_json_data['files'][state.current_file_identifier]['local_path'] = state.current_local_audio_path
            save_master_json(state.master_json_data)
        
    except Exception as e:
        state.error_message = f"Error downloading audio: {str(e)}"
        if state.current_file_identifier in state.master_json_data.get('files', {}):
            state.master_json_data['files'][state.current_file_identifier]['status'] = 'download_failed'
            state.master_json_data['files'][state.current_file_identifier]['error'] = state.error_message
            save_master_json(state.master_json_data)
        print(state.error_message)
    
    return state

def run_all_processing_node(state: MasterAgentState) -> MasterAgentState:
    """Run the full processing pipeline for the currently-selected audio file.
    
    This orchestrates calls to all specialised agents and records their
    outputs to the master JSON via ``add_agent_output_to_master_json``.
    The node is intentionally robust – a failure in one step will be
    recorded but will not abort subsequent steps, allowing us to collect
    as many insights as possible for each file.
    """
    print(f"--- MASTER AGENT: Running All Processing for {state.current_file_identifier} ---")
    
    if not state.current_local_audio_path or not os.path.exists(state.current_local_audio_path):
        state.error_message = "No local audio file available for processing."
        if state.current_file_identifier in state.master_json_data.get('files', {}):
            state.master_json_data['files'][state.current_file_identifier]['status'] = 'processing_failed'
            state.master_json_data['files'][state.current_file_identifier]['error'] = state.error_message
            save_master_json(state.master_json_data)
        print(state.error_message)
        return state
    
    # Update file status to processing
    if state.current_file_identifier in state.master_json_data.get('files', {}):
        state.master_json_data['files'][state.current_file_identifier]['status'] = 'processing'
        save_master_json(state.master_json_data)
    
    # Step 1: Transcription & Diarization
    print("Running Transcription & Diarization...")
    try:
        transcription_result = process_audio_for_transcription_diarization(
            state.current_local_audio_path,
            state.current_file_identifier
        )
        add_agent_output_to_master_json(
            state.master_json_data,
            state.current_file_identifier,
            'transcription',
            transcription_result
        )
        print("Transcription & Diarization completed successfully.")
    except Exception as e:
        error_msg = f"Transcription & Diarization failed: {str(e)}"
        print(error_msg)
        add_agent_output_to_master_json(
            state.master_json_data,
            state.current_file_identifier,
            'transcription',
            {'error': error_msg, 'status': 'failed'}
        )
    
    # Step 2: Noise Analysis
    print("Running Noise Analysis...")
    try:
        noise_result = run_noise_analysis(
            state.current_local_audio_path,
            state.current_file_identifier
        )
        add_agent_output_to_master_json(
            state.master_json_data,
            state.current_file_identifier,
            'noise_analysis',
            noise_result
        )
        print("Noise Analysis completed successfully.")
    except Exception as e:
        error_msg = f"Noise Analysis failed: {str(e)}"
        print(error_msg)
        add_agent_output_to_master_json(
            state.master_json_data,
            state.current_file_identifier,
            'noise_analysis',
            {'error': error_msg, 'status': 'failed'}
        )
    
    # Step 3: Evaluation Analysis
    print("Running Evaluation Analysis...")
    try:
        # Get the transcript from the master JSON if available
        transcript_data = state.master_json_data.get('files', {}).get(
            state.current_file_identifier, {}).get(
            'processing_steps', {}).get('transcription', {})
        
        if not transcript_data or 'error' in transcript_data:
            raise ValueError("Cannot run evaluation without a valid transcript")
            
        evaluation_result = run_evaluation_analysis(
            transcript_data,
            state.current_file_identifier,
            state.user_prompt
        )
        add_agent_output_to_master_json(
            state.master_json_data,
            state.current_file_identifier,
            'evaluation',
            evaluation_result
        )
        print("Evaluation Analysis completed successfully.")
    except Exception as e:
        error_msg = f"Evaluation Analysis failed: {str(e)}"
        print(error_msg)
        add_agent_output_to_master_json(
            state.master_json_data,
            state.current_file_identifier,
            'evaluation',
            {'error': error_msg, 'status': 'failed'}
        )
    
    # Step 4: Summary Generation
    print("Running Summary Generation...")
    try:
        # Get the transcript from the master JSON
        transcript_data = state.master_json_data.get('files', {}).get(
            state.current_file_identifier, {}).get(
            'processing_steps', {}).get('transcription', {})
        
        if not transcript_data or 'error' in transcript_data:
            raise ValueError("Cannot generate summary without a valid transcript")
            
        summary_result = run_summary_generation(
            transcript_data,
            state.current_file_identifier
        )
        add_agent_output_to_master_json(
            state.master_json_data,
            state.current_file_identifier,
            'summary',
            summary_result
        )
        print("Summary Generation completed successfully.")
    except Exception as e:
        error_msg = f"Summary Generation failed: {str(e)}"
        print(error_msg)
        add_agent_output_to_master_json(
            state.master_json_data,
            state.current_file_identifier,
            'summary',
            {'error': error_msg, 'status': 'failed'}
        )
    
    # Step 5: Recommendation Generation
    print("Running Recommendation Generation...")
    try:
        # Get necessary data from master JSON
        file_data = state.master_json_data.get('files', {}).get(state.current_file_identifier, {})
        transcript_data = file_data.get('processing_steps', {}).get('transcription', {})
        evaluation_data = file_data.get('processing_steps', {}).get('evaluation', {})
        
        if not transcript_data or 'error' in transcript_data:
            raise ValueError("Cannot generate recommendations without a valid transcript")
            
        recommendation_result = run_recommendation_generation(
            transcript_data,
            evaluation_data,
            state.current_file_identifier
        )
        add_agent_output_to_master_json(
            state.master_json_data,
            state.current_file_identifier,
            'recommendations',
            recommendation_result
        )
        print("Recommendation Generation completed successfully.")
    except Exception as e:
        error_msg = f"Recommendation Generation failed: {str(e)}"
        print(error_msg)
        add_agent_output_to_master_json(
            state.master_json_data,
            state.current_file_identifier,
            'recommendations',
            {'error': error_msg, 'status': 'failed'}
        )
    
    # Update file status to processed
    if state.current_file_identifier in state.master_json_data.get('files', {}):
        state.master_json_data['files'][state.current_file_identifier]['status'] = 'processed'
        state.master_json_data['files'][state.current_file_identifier]['completed_at'] = datetime.now().isoformat()
        save_master_json(state.master_json_data)
    
    # Increment the processed files count
    state.processed_files_count += 1
    print(f"Completed processing file {state.processed_files_count} of {state.total_files_to_process}")
    
    return state

def finalize_processing_node(state: MasterAgentState) -> MasterAgentState:
    """Finalize the processing session.
    Updates overall metadata and determines a consolidated session status.
    """
    print("--- MASTER AGENT: Finalizing Processing ---")
    
    # Update the master JSON with overall metadata
    state.master_json_data['metadata'] = {
        'total_files_processed': state.processed_files_count,
        'total_files_attempted': state.total_files_to_process,
        'completed_at': datetime.now().isoformat()
    }
    
    # Determine overall status
    if state.processed_files_count == 0:
        if state.error_message:
            state.overall_status = "failed"
            state.master_json_data['metadata']['status'] = "failed"
            state.master_json_data['metadata']['error'] = state.error_message
        else:
            state.overall_status = "no_files_processed"
            state.master_json_data['metadata']['status'] = "no_files_processed"
    elif state.processed_files_count < state.total_files_to_process:
        state.overall_status = "partially_completed"
        state.master_json_data['metadata']['status'] = "partially_completed"
    else:
        state.overall_status = "completed"
        state.master_json_data['metadata']['status'] = "completed"
    
    # Save the final state of the master JSON
    save_master_json(state.master_json_data)
    print(f"Processing finalized. Status: {state.overall_status}")
    
    return state

# --- Graph Definition --- 
def build_master_graph():
    """Build the master agent workflow graph."""
    # Define the workflow graph
    workflow = StateGraph(MasterAgentState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_processing_node)
    workflow.add_node("select_next_file", select_next_file_node)
    workflow.add_node("download_audio", download_audio_node)
    workflow.add_node("run_all_processing", run_all_processing_node)
    workflow.add_node("finalize", finalize_processing_node)
    
    # Define edges
    workflow.add_edge("initialize", "select_next_file")
    
    # Conditional edge: if no files in queue after initialization, go straight to finalize
    workflow.add_conditional_edges(
        "select_next_file",
        lambda state: "download_audio" if state.current_file_identifier else "finalize"
    )
    
    workflow.add_edge("download_audio", "run_all_processing")
    
    # After processing a file, check if there are more files to process
    workflow.add_conditional_edges(
        "run_all_processing",
        lambda state: "select_next_file" if state.files_to_process_queue else "finalize"
    )
    
    # Set the entry point
    workflow.set_entry_point("initialize")
    
    # Finalize is the end state
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


# --- Main Execution (currently commented out as api_server.py drives the process) ---
# def main():
#     parser = argparse.ArgumentParser(description="Master Agent for Call Center Review Processing.")
#     parser.add_argument("--link", type=str, help="Google Drive link to the audio file or folder.")
#     parser.add_argument("--local", type=str, help="Local path to an audio file.")
#     parser.add_argument("--folder", action="store_true", help="Process as a folder of files.")
#     parser.add_argument("--prompt", type=str, help="Optional user prompt for evaluation context.")
#     args = parser.parse_args()
    
#     # Initialize state
#     state = MasterAgentState(
#         initial_google_drive_link=args.link,
#         current_local_audio_path=args.local if args.local and os.path.exists(args.local) else None,
#         is_folder=args.folder,
#         user_prompt=args.prompt
#     )
    
#     # Build and run the graph
#     master_graph = build_master_graph()
#     final_state = master_graph.invoke(state)
    
#     # Print final status
#     print(f"\nProcessing completed with status: {final_state.overall_status}")
#     if final_state.error_message:
#         print(f"Error: {final_state.error_message}")
#     print(f"Processed {final_state.processed_files_count} out of {final_state.total_files_to_process} files.")
#     print(f"Results saved to {MASTER_JSON_FILE}")
    
# if __name__ == "__main__":
#     main()