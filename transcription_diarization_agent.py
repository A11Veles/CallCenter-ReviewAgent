import os
import json
import wave
import numpy as np
import torch
from openai import OpenAI
from dotenv import load_dotenv
from pyannote.audio import Pipeline
from pyannote.core import Segment
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import tempfile

from utils import get_audio_file_identifier

# Load API keys from .env
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
hf_token = os.getenv("HUGGINGFACE_TOKEN")

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

OUTPUTS_DIR = "outputs"
if not os.path.exists(OUTPUTS_DIR):
    os.makedirs(OUTPUTS_DIR)

class TranscriptionDiarizationState(BaseModel):
    local_audio_path: str
    audio_url: Optional[str] = None # For context and naming
    file_identifier: str
    audio_duration: Optional[float] = None
    speaker_turns: Optional[List[Dict[str, Any]]] = None
    transcript: Optional[str] = None
    formatted_transcript: Optional[str] = None
    formatted_transcript_path: Optional[str] = None
    has_valid_hf_token: bool = True
    error: Optional[str] = None
# ... (rest of file omitted for brevity, but will be uploaded in full) ...
