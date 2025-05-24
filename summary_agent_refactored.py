import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
import datetime

from utils import get_audio_file_identifier # Assuming utils.py is accessible

# Load environment variables
load_dotenv()

# Get OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY environment variable is not set. Summary agent will fail if used.")

# Initialize OpenAI client if key is available
client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

OUTPUTS_DIR = "outputs"
if not os.path.exists(OUTPUTS_DIR):
    os.makedirs(OUTPUTS_DIR)

SUMMARY_SYSTEM_PROMPT = """
You are the Format/Summary Agent in a Call Center Evaluation Framework. You receive the raw audio transcription of a customer service call. Your job is to:

a) Summarize the call professionally and clearly in Arabic language.
b) Focus on the **main purpose** of the call, the **key events**, and the **final outcome**.
c) Ensure the summary is understandable without listening to the original call or seeing the full transcript.
d) Avoid speculation or opinion — use only what is explicitly present in the transcript.
e) Maintain a neutral and professional tone suitable for stakeholders, team leads, or quality control analysts.

Summary Guidelines:
a) Keep it concise but comprehensive
b) Use bullet points or structured formatting to enhance readability when possible.
c) Do **not mimic the flow of the conversation**; instead, extract **issues**, **resolutions**, and **noteworthy moments**.
d) Highlight any products/services mentioned, customer frustrations, or special requests. If none exist, don't mention them

Please provide the summary in Arabic as requested.
"""

def run_summary_generation(transcript_file_path: str, audio_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates a summary for a given call transcript.

    Args:
        transcript_file_path: Path to the transcript text file.
        audio_url: Optional URL of the original audio for context and naming outputs.

    Returns:
        A dictionary containing the status, path to the output summary file,
        and any error messages.
    """
    if not client:
        return {
            "status": "error",
            "error_message": "OpenAI client not initialized. OPENAI_API_KEY might be missing.",
            "output_files": {}
        }

    file_identifier = get_audio_file_identifier(audio_url=audio_url, local_path=transcript_file_path)
    print(f"--- SUMMARY AGENT: Starting for {file_identifier} ---")
# ... (rest of file omitted for brevity, but will be uploaded in full) ...
