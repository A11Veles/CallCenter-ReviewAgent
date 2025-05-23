# CallCenter-ReviewAgent

AI-powered Call Center Review & Analysis Tool

---

## Overview
CallCenter-ReviewAgent is an advanced AI-driven solution for analyzing call center audio recordings. It automatically transcribes, evaluates, and summarizes calls, providing actionable insights and recommendations for quality improvement. The tool features a modern, visually appealing UI and supports both English and Arabic (with full RTL support).

---

## Features

- **Automatic Transcription**: Converts call audio to text using state-of-the-art AI models.
- **Noise & Quality Analysis**: Detects background noise and evaluates audio clarity.
- **Comprehensive Evaluation**: Scores call quality and agent performance with detailed metrics.
- **Summaries & Recommendations**: Generates concise summaries and actionable recommendations.
- **Full Transcript Display**: View the entire conversation transcript, not just snippets.
- **Arabic & RTL Support**: Properly formats and displays Arabic text with right-to-left orientation.
- **Modern UI**: Results are shown in a card-based, visually appealing layout for easy review.

---

## Demo
![UI Screenshot](screenshot.png)

---

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js (for UI, if applicable)
- Required Python packages (see `requirements.txt`)

### Installation
```bash
# Clone the repository
git clone https://github.com/A11Veles/CallCenter-ReviewAgent.git
cd CallCenter-ReviewAgent

# Install Python dependencies
pip install -r requirements.txt

# (Optional) Install frontend dependencies
cd frontend
npm install
```

### Usage
```bash
# Run the backend API server
python api_server.py

# (Optional) Run the frontend
cd frontend
npm start
```

Open your browser and navigate to the provided local address to access the UI.

---

## Project Structure
```
CallCenter-ReviewAgent/
├── api_server.py           # Backend API for processing
├── master_agent.py         # Main processing logic
├── index.html              # Main UI page
├── requirements.txt        # Python dependencies
├── frontend/               # (Optional) Frontend app
├── ...
```

---

## Contributing
Pull requests and issues are welcome! Please open an issue to discuss your ideas or report bugs.

---

## License
MIT License

---

## Acknowledgements
- OpenAI for transcription models
- Community contributors

---

For more details, see the code and documentation inside the repository.
