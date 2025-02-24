# CoCo Backend - Multi-Agent Data Consultant API

This is the backend for **CoCo**, a multi-agent data consultant system. It powers the core functionality of the accompanying voice agent by exposing FastAPI endpoints for various agents, research agent, presentation generation model, and live presentation edit model. The backend integrates advanced AI tools to collect voice input, conduct deep research, generate presentations, and enable real-time edits.

---

## Features

- **API Endpoints**: Exposes endpoints for voice processing, research, presentation generation, and live editing.
- **Multi-Agent System**: Manages a team of agents for data collection, research, and content creation.
- **Presentation Generation**: Creates Reveal.js-based presentations with factual content and resources.
- **Real-Time Editing**: Allows dynamic edits to presentations via API calls.

---

## Tech Stack

### Backend
- **[FastAPI](https://fastapi.tiangolo.com/)**: High-performance Python framework for building APIs.
- **[smolagents](https://github.com/smol-ai/agents)**: Multi-agent framework including `CodeAgents`, `DuckDuckGoSearchTool`, and `ToolCallingAgent`.
- **[GPT-4o-mini](https://openai.com/)**: Lightweight, powerful AI model for natural language processing.
- **[Ngrok](https://ngrok.com/)**: Secure tunneling to expose local servers to the internet.
- **[Reveal.js](https://revealjs.com/)**: Framework for creating interactive presentations.
- **[ElevenLabs](https://elevenlabs.io/)**: Conversational AI powered by Gemini 1.5 Flash for realistic voice interactions.

---

## How It Works

The backend uses FastAPI to provide endpoints that:
1. **Research**: Utilizes `smolagents` tools (e.g., `DuckDuckGoSearchTool`) and `CodeAgents` to perform deep research.
2. **Generate Presentations**: Leverages `GPT-4o-mini` and Reveal.js to create detailed, editable presentations.
3. **Enable Live Edits**: Supports real-time modifications to presentations via direct API calls.

---

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/dotvignesh/researchAgentAPI
   cd researchAgentAPI
   ```

2. **Install Requirements**
   - Set up a virtual environment and install dependencies:
     ```bash
     python -m venv venv
     source venv/bin/activate  
     pip install fastapi smolagents pydantic python-dotenv openai pyngrok uvicorn elevenlabs
     ```

3. **Configure Environment**
   - Create a `.env` file in the root directory and add the following:
     ```
     OPENAI_API_KEY=your_openai_api_key
     NGROK_AUTH_TOKEN=your_ngrok_auth_token
     ```

4. **Run the Server**
   - Start the FastAPI server with ngrok:
     ```bash
     python app.py
     ```
---

Checkout the frontend repo and instrunctions here: https://github.com/rameshsam02/CoCo
