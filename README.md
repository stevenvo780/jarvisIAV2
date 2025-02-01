# Jarvis AI Assistant V2

A sophisticated AI virtual assistant with advanced voice and text processing capabilities, calendar integration, and multi-model intelligence.

## Features

### Voice Interaction
- Voice activation with "Hey Jarvis" wake word
- Natural language processing
- Text-to-Speech (TTS) responses
- Voice command recognition
- Multiple sound effects for different interactions

### Multi-Model Intelligence
- OpenAI GPT integration
- Google Gemini AI integration
- Local LLama model for offline processing
- Automatic model selection based on query complexity
- Contextual understanding and memory retention

### Calendar Integration
- Google Calendar synchronization
- Natural language event creation
- Intelligent time prediction for events
- Event listing and management
- Smart reminders and notifications

### System Commands
- Calculator access
- Web browser control
- Music player integration
- System monitoring
- Resource management

### Smart Features
- Context-aware responses
- Conversation history tracking
- User profile adaptation
- Multi-cultural understanding
- Difficulty-based model routing
- Memory management system

## Project Structure

```
jarvisIAV2/
├── src/
│   ├── assets/         # Sound effects and resources
│   ├── config/         # Configuration files
│   ├── data/           # User data and conversation history
│   ├── modules/        # Core functionality modules
│   └── utils/          # Utility functions
├── tests/              # Test suite
└── main.py            # Application entry point
```

## Prerequisites

### System Dependencies
```bash
# Update package list
sudo apt-get update

# Install system dependencies
sudo apt-get install -y \
    python3-pip \
    python3-pyaudio \
    libasound2-dev \
    portaudio19-dev

# Install audio dependencies
sudo apt-get install -y \
    alsa-utils \
    pulseaudio \
    python3-pygame

# Add user to audio group
sudo usermod -a -G audio $USER
```

### Python Dependencies
```bash
# Install Python requirements
pip install -r requirements.txt
```

## Configuration

### API Keys Setup
Create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your_openai_key
GOOGLE_IA_API_KEY=your_google_key
```

### Google Calendar Integration
1. Visit Google Cloud Console
2. Create a new project
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Download credentials as `google_calendar_credentials.json`
6. Place in `src/config/credentials/`

### Local Model Setup
```bash
# Create models directory
mkdir -p ~/.local/share/jarvis/models
cd ~/.local/share/jarvis/models

# Download LLama model (requires HuggingFace account)
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf
```

## Usage

### Starting Jarvis
```bash
python main.py
```

### Voice Commands
- "Hey Jarvis" - Wake word
- "Remember to [task]" - Create calendar event
- "What's on my schedule?" - List events
- "Open calculator" - Launch system calculator
- "Play music" - Start music player
- "Stop" - Interrupt current action

### Text Commands
- `config tts on/off` - Toggle text-to-speech
- `config effects on/off` - Toggle sound effects
- `exit/quit` - Close application
- `help` - Show available commands

### Calendar Commands
- Natural language event creation
- Automatic time detection
- Intelligent scheduling
- Event listing and management

## Troubleshooting

### Audio Issues
- Check microphone permissions
- Verify audio group membership
- Run `arecord -l` to list devices
- Adjust device index in settings

### Model Problems
- Verify API keys
- Check internet connection
- Monitor system resources
- Review logs in `logs/jarvis.log`

### Calendar Integration
- Verify OAuth credentials
- Check calendar permissions
- Ensure valid token refresh
- Review authentication logs

## System Requirements

- Minimum 8GB RAM
- CPU with AVX2 support (most CPUs from 2017+)
- 4GB free disk space
- Python 3.8+
- Internet connection for API models
- Microphone and speakers

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
