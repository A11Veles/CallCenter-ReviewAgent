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
    print("Warning: OPENAI_API_KEY environment variable is not set. Recommendation agent will fail if used.")

# Initialize OpenAI client if key is available
client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

OUTPUTS_DIR = "outputs"
if not os.path.exists(OUTPUTS_DIR):
    os.makedirs(OUTPUTS_DIR)

RECOMMENDATION_SYSTEM_PROMPT = """
You are the Recommendation Agent in a Call Center Evaluation Framework. Your task is to analyze a customer service call based on two inputs:
1) The raw transcription of the call
2) The structured Evaluation Report, which contains assessments for:
   a) Satisfaction
   b) Clarity
   c) Tone
   d) Complaint Detection

Your Goal: Suggest Improvements
Based on these two inputs, your objective is to suggest clear, actionable communication improvements in Arabic Language that the Call Center Personnel could have said or done to increase the quality of the call.

Important things to note: 
You are not grading or repeating the evaluation. Instead, you are proactively identifying better responses, missed opportunities, or helpful questions that would improve:
a) The customer's satisfaction
b) The clarity of the conversation
c) The agent's tone and empathy
d) The ability to acknowledge and handle complaints

Your Recommendations Should:
1) Be specific to the context of the call.
2) Include example phrases the agent could have used.
3) Be positive and constructive, not critical or judgmental.
4) Focus only on raising the quality of the call, not generic training advice.
5) If the call was already excellent in all areas, acknowledge that and say no major improvements are needed.
"""

def run_recommendation_generation(transcript_file_path: str, evaluation_json_path: Optional[str] = None, audio_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates recommendations based on a call transcript and its evaluation report.

    Args:
        transcript_file_path: Path to the transcript text file.
        evaluation_json_path: Optional path to the JSON evaluation report file. If None, recommendations
                             will be generated based on the transcript only.
# ... (rest of file omitted for brevity, but will be uploaded in full) ...
