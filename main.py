"""
Interactive Voice Assistant Agent - Backend REST API Service
Main Entrypoint with FastAPI, CORS, OpenAPI Docs, and Routing.
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.routes import router as api_router

app = FastAPI(
    title="Interactive Voice Assistant Agent API",
    description="""
    ## Overview
    An intelligent voice agent backend designed for classification, structured action planning, 
    and tool execution based on voice commands.
    
    ### Core Capabilities:
    * 🎙️ **Voice & Audio Ingestion**: Ingests spoken audio files or base64 streams (WAV, MP3, WEBM).
    * 🏷️ **Intent Classification**: Identifies user intent and extracts entity parameters with confidence metrics.
    * 📋 **Action Planning**: Generates step-by-step sequential or composite execution plans.
    * ⚙️ **Tool Execution**: Executes system tools, mathematical calculators, weather forecasts, notes, and timers.
    * 🔊 **Text-to-Speech (TTS)**: Returns synthesized audio responses ready for UI playback.
    
    ### Reference & Architecture:
    Open-source inspired architecture based on standards from **Pipecat**, **Home Assistant Assist**, and **ReAct / Plan-and-Solve Agent** pipelines under MIT License.
    """,
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for external frontends (React, Vue, Svelte, Flutter, Next.js, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)


@app.get("/", summary="Root Endpoint")
def root():
    return {
        "service": "Interactive Voice Assistant Agent API",
        "version": settings.version,
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "health": "GET /api/health",
            "model_config": "GET /api/config/model",
            "update_model_config": "POST /api/config/model",
            "conversational_chat": "POST /api/conversation/chat",
            "process_audio_file": "POST /api/voice/process-file",
            "process_audio_base64": "POST /api/voice/process-base64",
            "execute_command": "POST /api/command",
            "classify_intent": "POST /api/classify",
            "create_action_plan": "POST /api/plan",
            "text_to_speech": "POST /api/tts",
            "domain_knowledge": "GET /api/knowledge",
            "query_domain_knowledge": "POST /api/knowledge/query",
            "list_tools": "GET /api/tools",
            "active_timers": "GET /api/timers",
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "main.py:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
