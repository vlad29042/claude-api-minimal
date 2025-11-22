"""Minimal FastAPI server for Claude CLI - Free Version.

Simple HTTP API with session ID support only.

Usage:
    pip install fastapi uvicorn python-dotenv
    python minimal_server.py

API:
    POST /api/v1/chat - Send prompt with optional session_id
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from claude_cli import (
    ClaudeConfig,
    ClaudeIntegration,
    ClaudeProcessManager,
    InMemorySessionStorage,
    SessionManager,
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

# Global service instance
claude_service: Optional[ClaudeIntegration] = None

# Simple API key auth
security = HTTPBearer()
API_KEY = os.getenv("CLAUDE_API_KEY", "change-me-in-production")


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify API key."""
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


class ChatRequest(BaseModel):
    """Chat request with prompt and optional session_id."""
    prompt: str = Field(..., description="User prompt", min_length=1)
    session_id: Optional[str] = Field(None, description="Session ID to continue")
    user_id: int = Field(..., description="User ID", gt=0)


class ChatResponse(BaseModel):
    """Chat response with content and session info."""
    content: str
    session_id: str
    cost: float
    duration_ms: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    global claude_service

    logger.info("Starting minimal Claude service")

    config = ClaudeConfig(
        claude_binary_path=os.getenv("CLAUDE_BINARY_PATH", "claude"),
        claude_timeout_seconds=int(os.getenv("CLAUDE_TIMEOUT_SECONDS", "300")),
        claude_max_turns=int(os.getenv("CLAUDE_MAX_TURNS", "50")),
        session_timeout_hours=24,
        max_sessions_per_user=10,
        use_sdk=False,
    )

    storage = InMemorySessionStorage()
    session_manager = SessionManager(config=config, storage=storage)
    process_manager = ClaudeProcessManager(config=config, tool_monitor=None)

    claude_service = ClaudeIntegration(
        config=config,
        process_manager=process_manager,
        session_manager=session_manager,
        tool_monitor=None,
    )

    logger.info("Service ready")
    yield

    logger.info("Shutting down")
    if claude_service:
        await claude_service.shutdown()


app = FastAPI(
    title="Minimal Claude API",
    description="Simple HTTP API for Claude with session support",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key)
) -> ChatResponse:
    """Send message to Claude."""
    if not claude_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # Create simple working directory
        work_dir = Path(f"/tmp/claude_user_{request.user_id}")
        work_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Processing request",
            user_id=request.user_id,
            has_session=bool(request.session_id),
        )

        # Execute command
        response = await claude_service.run_command(
            prompt=request.prompt,
            working_directory=work_dir,
            user_id=request.user_id,
            session_id=request.session_id,
        )

        # Create response object before logging (uvicorn bug workaround)
        chat_response = ChatResponse(
            content=response.content,
            session_id=response.session_id,
            cost=response.cost,
            duration_ms=response.duration_ms,
        )

        logger.info(
            "Request completed",
            user_id=request.user_id,
            session_id=response.session_id,
            cost=response.cost,
            duration_ms=response.duration_ms,
        )

        return chat_response

    except Exception as e:
        logger.error("Request failed", error=str(e), user_id=request.user_id)
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")


@app.get("/health")
async def health():
    """Health check."""
    if not claude_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return {"status": "ok"}


def main():
    """Run server."""
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info("Starting server", host=host, port=port)

    uvicorn.run(
        "minimal_server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
