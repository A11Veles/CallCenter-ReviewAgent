import re
import os
import json
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
from datetime import datetime

MASTER_JSON_FILE = "master_processing_log.json"

def extract_google_drive_file_id(url: str) -> Optional[str]:
    """Extracts the file ID from a Google Drive URL."""
    # Pattern for /d/ format (standard file URLs)
    match = re.search(r'/d/([^/]+)', url)
    if match:
        return match.group(1)
    
    # Pattern for /folders/ format (folder URLs)
    match_folder = re.search(r'/folders/([^/?]+)', url)
    if match_folder:
        return match_folder.group(1)
    
    # Pattern for id= format (alternate URLs)
    match_uc = re.search(r'id=([^&]+)', url)
    if match_uc:
        return match_uc.group(1)
    
    return None
# ... (rest of file omitted for brevity, but will be uploaded in full) ...
