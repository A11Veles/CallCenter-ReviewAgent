import os
import json
from typing import Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
import re

from utils import get_audio_file_identifier # Assuming utils.py is in the same directory or accessible

# Load environment variables
load_dotenv()

# Get Google API key from environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    # This should ideally not stop the import, but rather be checked at runtime if agent is used
    print("Warning: GOOGLE_API_KEY environment variable is not set. Evaluation agent will fail if used.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

OUTPUTS_DIR = "outputs"
if not os.path.exists(OUTPUTS_DIR):
    os.makedirs(OUTPUTS_DIR)

EVALUATION_SYSTEM_PROMPT = """
You are the Evaluation Agent (Analyst) in a Call Center Evaluation Framework. Your role is to analyze the text transcription of a recorded customer support call and produce an objective, structured evaluation based on the following four core criteria:

1) Satisfaction (Most Important Point):
   - Determine if the caller's main request or concern (the "Most Important Point") was addressed.
   - Indicate whether the customer seems satisfied with the outcome.
   - Use context and language cues to infer emotional satisfaction.

2) Clarity (Not Ambiguous)
   - Assess whether the agent communicated clearly and avoided ambiguity.
   - Identify any confusing, vague, or contradictory statements.
   - Comment on the structure and coherence of the agent's explanations.

3) Tone (Friendliness / No Rudeness)
   - Evaluate the overall tone of the agent during the interaction.
   - Was the agent polite, professional, empathetic, and friendly?
   - Flag any instances of rudeness, dismissiveness, or passive aggression.

4) Complaint Detection
   - Identify whether the customer issued a complaint — explicit or implicit.
   - If a complaint is detected, provide its summary and severity level (Low / Medium / High).
   - Flag this for routing to the Complaints Database.
"""

def run_evaluation_analysis(transcript_file_path: str, audio_url: Optional[str] = None) -> Dict[str, Any]:
    load_dotenv()
    # Ensure OUTPUTS_DIR exists
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    file_identifier = get_audio_file_identifier(transcript_file_path, audio_url)
    print(f"--- EVALUATION AGENT: Starting for {file_identifier} ---")

    output_data: Dict[str, Any] = {
        "status": "error", # Default to error
        "file_identifier": file_identifier,
        "error_message": None,
        "output_files": {},
# ... (rest of file omitted for brevity, but will be uploaded in full) ...
