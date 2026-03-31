# Chat Implementation Documentation

## Overview

This document details the implementation of the chat functionality in the Schedule Assistant application. The chat system enables users to interact with an AI assistant through speech-to-text input, allowing natural language queries about scheduling, events, and calendar management. The implementation spans both frontend and backend components, with integration into the Docker containerized environment.

## Frontend Implementation

### Components Involved

1. **ChatModal Component** (`apps/frontend/frontend/app/components/Modals/ChatModal/`)
   - Main chat interface with modal overlay
   - Handles speech-to-text input using Web Speech API
   - Displays conversation history
   - Manages chat state and UI interactions

2. **llmAgent.ts** (`apps/frontend/frontend/app/components/Modals/ChatModal/llmAgent.ts`)
   - Handles communication with the backend API
   - Sends user messages to `/agent/chat` endpoint
   - Processes responses and updates chat state

3. **useChatModal Hook** (`apps/frontend/frontend/app/hooks/useChatModal.ts`)
   - Manages chat modal state (open/close)
   - Handles message history
   - Integrates with the main application state

### Speech-to-Text Flow

1. User clicks microphone button in ChatModal
2. Web Speech API initializes speech recognition
3. Audio input is converted to text in real-time
4. Transcribed text is sent to backend via `sendLLMMessage` function
5. Response is displayed in the chat interface

### Key Frontend Features

- **Real-time STT**: Uses browser's Web Speech API for speech recognition
- **Fallback Support**: Graceful degradation if STT is not supported
- **Responsive UI**: Modal-based interface that works on desktop and mobile
- **Message History**: Maintains conversation context within the session
- **Error Handling**: Displays user-friendly error messages for API failures

### Integration Points

- **Page Integration**: ChatModal is integrated into the main page (`apps/frontend/frontend/app/page.tsx`)
- **State Management**: Uses React hooks for local state management
- **API Communication**: RESTful API calls to backend endpoints

## Backend Implementation

### Core Components

1. **Agent Router** (`apps/backend/app/routers/agent.py`)
   - `/agent/chat` endpoint for handling chat messages
   - Processes incoming chat requests
   - Orchestrates LLM responses and intent parsing

2. **LLM Clients** (`apps/backend/app/agent/llm_clients.py`)
   - Abstraction layer for different LLM providers
   - Currently supports Ollama integration
   - Handles async communication with LLM services

3. **Intent Parser** (`apps/backend/app/agent/parser.py`)
   - Parses user intent from natural language input
   - Extracts scheduling-related actions and parameters
   - Integrates with Prolog knowledge base for reasoning

4. **Configuration** (`apps/backend/app/agent/config.py`)
   - Ollama settings (base URL, model, timeout)
   - API configuration for LLM integration

### Chat Flow Architecture

1. **Request Reception**: FastAPI receives POST request to `/agent/chat`
2. **Request Validation**: Pydantic models validate input (message, session_id, current_datetime)
3. **LLM Processing**: Message sent to Ollama for response generation
4. **Intent Parsing**: Response analyzed for scheduling intents
5. **Response Formatting**: Structured response returned to frontend

### Key Backend Features

- **Async Processing**: Uses `asyncio.to_thread` for non-blocking LLM calls
- **Error Handling**: Comprehensive try/except blocks for API failures
- **Session Management**: Maintains chat context via session IDs
- **Intent Recognition**: Advanced parsing for scheduling commands
- **Prolog Integration**: Uses Prolog rules for complex scheduling logic

### API Endpoints

- `POST /agent/chat`: Main chat endpoint
  - Request Body: `ChatRequest` (message, session_id, current_datetime)
  - Response: `ChatResponse` (response, intent_data, success)

## Docker Integration and Effects

### Docker Compose Configuration

The chat implementation significantly impacts the Docker setup:

1. **Ollama Service Addition** (`docker/docker-compose.yml`)
   - Added dedicated Ollama container for LLM processing
   - Configured with GPU support for accelerated inference
   - Network configuration for inter-service communication

2. **Service Networking**
   - Backend service connects to Ollama via internal Docker network
   - `OLLAMA_HOST=ollama:11434` environment variable
   - Eliminates need for host.docker.internal references

### GPU Acceleration

- **NVIDIA GPU Support**: Enabled via Docker Compose deploy section
  - `capabilities: [gpu]`
  - `driver: nvidia`
  - Runtime: `nvidia`
- **Performance Impact**: Significant speedup for LLM inference (detected GTX 1070 with 8GB VRAM)

### Container Dependencies

- **Backend Container**: Now depends on Ollama service
  - `depends_on: [ollama]` in docker-compose.yml
  - Ensures Ollama is available before backend starts

- **Model Management**: Ollama container pre-loads required models
  - Models stored in persistent volume
  - Automatic model pulling on first run

### Build and Deployment Effects

- **Image Rebuilding**: Changes to agent code require backend image rebuild
- **Volume Mounting**: Ollama models persist across container restarts
- **Resource Allocation**: GPU resources allocated to Ollama container
- **Network Isolation**: Secure communication between services

### Development vs Production

- **Development**: Hot reloading for backend changes, Ollama runs in container
- **Production**: Optimized images, GPU acceleration enabled
- **Testing**: Isolated environment for chat functionality testing

## Implementation Impact and Benefits

### User Experience

- **Natural Interaction**: Speech-to-text enables hands-free scheduling
- **Intelligent Responses**: LLM-powered understanding of complex queries
- **Context Awareness**: Session-based conversation memory
- **Real-time Feedback**: Immediate responses with GPU acceleration

### Technical Benefits

- **Scalability**: Containerized architecture supports horizontal scaling
- **Performance**: GPU acceleration enables faster response times
- **Maintainability**: Modular design with clear separation of concerns
- **Extensibility**: Easy to add new LLM providers or features

### Challenges Addressed

- **API Integration**: Resolved HTTP 422/500 errors through proper request modeling
- **Async Handling**: Implemented thread-based async for LLM calls
- **Network Configuration**: Fixed Docker networking for service communication
- **GPU Utilization**: Enabled hardware acceleration for better performance

## Future Enhancements

- **Multi-modal Input**: Support for voice commands with wake words
- **Advanced Intent Parsing**: More sophisticated NLP for complex scheduling
- **Conversation Memory**: Persistent chat history across sessions
- **Multi-language Support**: Localization for different languages
- **Voice Synthesis**: Text-to-speech for responses

## Conclusion

The chat implementation provides a robust, AI-powered interface for the Schedule Assistant, enabling natural language interaction through speech input. The frontend handles real-time speech recognition and user interface, while the backend processes requests through LLM integration and intent parsing. Docker containerization ensures reliable deployment with GPU acceleration for optimal performance. This implementation significantly enhances the application's usability and opens doors for advanced AI-driven scheduling features.