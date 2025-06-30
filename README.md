# 🀄 Mahjong AI Tutor

An AI-powered Mahjong tutor that analyzes board states through images and provides strategic guidance to help players improve their skills. Built with FastAPI and Ollama for cost-effective, self-hosted AI tutoring.

## Features

- 📸 **Image Analysis**: Upload photos of your Mahjong tiles for AI analysis
- 🎯 **Strategic Advice**: Get personalized move recommendations with explanations
- 💬 **Chat Interface**: Interactive web-based chat for seamless tutoring experience
- 🤖 **Vision AI**: Uses advanced vision models to understand tile arrangements
- 💰 **Cost-Effective**: Self-hosted solution using Ollama (no API costs)

## Prerequisites

- **macOS** (tested on macOS 14+)
- **Python 3.8+**
- **Ollama** (for running AI models locally)

## Installation

### 1. Install Ollama

First, install Ollama on your macOS system:

```bash
# Using Homebrew (recommended)
brew install ollama

# Or download directly from ollama.com
curl -fsSL https://ollama.com/install.sh | sh
```

After installation, start the Ollama service:

```bash
# Start Ollama (it will run on localhost:11434)
ollama serve
```

### 2. Download Required AI Model

Download the vision-capable model needed for image analysis:

```bash
# This will download the MiniCPM-V model (~5.5GB)
ollama pull minicpm-v:latest
```

**Note**: The model download may take 10-15 minutes depending on your internet connection.

### 3. Clone and Set Up the Project

```bash
# Clone the repository
git clone https://github.com/carlosatFroom/mahjong_alex.git
cd mahjong_alex

# Create a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Verify Installation

Check that Ollama is running and the model is available:

```bash
# Test Ollama connection
curl http://localhost:11434/api/tags

# You should see minicpm-v:latest in the response
```

## Usage

### 1. Start the Application

```bash
# Make sure you're in the project directory with venv activated
source venv/bin/activate
python main.py
```

The server will start on `http://localhost:8000`

### 2. Use the Chat Interface

1. Open your web browser and go to `http://localhost:8000`
2. Take a photo of your Mahjong tiles and board state
3. Upload the image using the 📷 button
4. Ask questions like:
   - "What should I discard next?"
   - "How can I improve this hand?"
   - "What's my best winning strategy?"
5. Get AI-powered strategic advice with explanations

### 3. Example Queries

- **Strategic Analysis**: "Analyze my current hand and suggest the best discard"
- **Learning**: "Explain why this move is better than alternatives"
- **Pattern Recognition**: "What winning patterns can I pursue with these tiles?"

## Troubleshooting

### Ollama Connection Issues

If you see "❌ Ollama connection failed":

```bash
# Check if Ollama is running
ollama serve

# Verify the service is on port 11434
curl http://localhost:11434/api/tags
```

### Model Not Found

If the model isn't available:

```bash
# Re-download the model
ollama pull minicpm-v:latest

# List available models
ollama list
```

### Python Dependencies

If you encounter package issues:

```bash
# Update pip and reinstall
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

## Technical Architecture

- **Backend**: FastAPI with Ollama integration
- **Frontend**: Responsive HTML/CSS/JavaScript chat interface
- **AI Model**: MiniCPM-V (vision-capable model for tile recognition)
- **Image Processing**: Base64 encoding for image uploads

## Development

### Project Structure

```
mahjong_alex/
├── main.py           # FastAPI backend server
├── index.html        # Chat interface frontend
├── requirements.txt  # Python dependencies
├── PRD.md           # Product Requirements Document
└── README.md        # This file
```

### API Endpoints

- `GET /` - Serve the chat interface
- `POST /api/chat` - Chat with AI (supports image uploads)
- `GET /api/health` - Health check for Ollama connection
- `GET /api/models` - List available Ollama models

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgments

- Built for Alex's non-profit Mahjong community
- Uses [Ollama](https://ollama.com) for local AI model hosting
- Powered by [MiniCPM-V](https://github.com/OpenBMB/MiniCPM-V) vision model