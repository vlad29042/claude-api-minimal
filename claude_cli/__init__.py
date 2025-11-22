"""Claude CLI Integration - Minimal Version

This library provides a high-level interface for integrating Claude Code CLI
into Python applications with session management and streaming support.
"""

from .config import ClaudeConfig, from_env, from_pydantic_settings
from .exceptions import (
    ClaudeError,
    ClaudeParsingError,
    ClaudeProcessError,
    ClaudeSessionError,
    ClaudeTimeoutError,
)
from .facade import ClaudeIntegration
from .integration import ClaudeProcessManager, ClaudeResponse, StreamUpdate
from .parser import OutputParser
from .session import (
    ClaudeSession,
    InMemorySessionStorage,
    SessionManager,
    SessionStorage,
)

__version__ = "0.1.0-minimal"

__all__ = [
    # Config
    "ClaudeConfig",
    "from_env",
    "from_pydantic_settings",
    # Exceptions
    "ClaudeError",
    "ClaudeTimeoutError",
    "ClaudeProcessError",
    "ClaudeParsingError",
    "ClaudeSessionError",
    # Main integration
    "ClaudeIntegration",
    # Core components
    "ClaudeProcessManager",
    "ClaudeResponse",
    "StreamUpdate",
    # Session Management
    "ClaudeSession",
    "SessionStorage",
    "InMemorySessionStorage",
    "SessionManager",
    # Parsing
    "OutputParser",
]
