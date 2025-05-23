import os
import json
import wave
import numpy as np
import librosa
from typing import List, Dict, Any, Optional, Tuple
from json import JSONEncoder

from utils import get_audio_file_identifier # Assuming utils.py is accessible

# Custom JSON encoder to handle NumPy types
class NumpyEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

OUTPUTS_DIR = "outputs"
if not os.path.exists(OUTPUTS_DIR):
    os.makedirs(OUTPUTS_DIR)

AGENT_SPEAKER_ID_PATTERN = "SPEAKER_00" # Default assumption for agent speaker ID

def _calculate_snr(segment_audio: np.ndarray, sr: int, noise_threshold_factor=0.1) -> Optional[float]:
    """Calculates Signal-to-Noise Ratio (SNR) for an audio segment."""
    try:
        # Simplified SNR: energy of signal vs. energy of estimated noise
        # Estimate noise as parts of signal below a threshold of max amplitude
        max_amp = np.max(np.abs(segment_audio))
        noise_threshold = max_amp * noise_threshold_factor
        
        signal_power = np.mean(segment_audio**2)
        noise_segments = segment_audio[np.abs(segment_audio) < noise_threshold]
        
        if len(noise_segments) > 0:
            noise_power = np.mean(noise_segments**2)
        else:
            # If no noise segments found (e.g., constant loud signal), SNR might be very high or undefined
            # For simplicity, if noise_power is zero or too small, return a high SNR or handle as per requirement
            noise_power = 1e-10 # Avoid division by zero, implies very low noise
            
        if noise_power == 0: return 100.0 # Effectively infinite SNR if no noise detected
        snr = 10 * np.log10(signal_power / noise_power)
        return float(snr) if not np.isinf(snr) and not np.isnan(snr) else None
    except Exception:
        return None
# ... (rest of file omitted for brevity, but will be uploaded in full) ...
