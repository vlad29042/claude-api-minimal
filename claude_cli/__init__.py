"""Claude CLI Integration - Python library for Claude Code CLI.

This library provides a high-level interface for integrating Claude Code CLI
into Python applications with session management, streaming support, and
tool validation.
"""

from .config import ClaudeConfig, from_env, from_pydantic_settings
from .exceptions import (
    ClaudeError,
    ClaudeParsingError,
    ClaudeProcessError,
    ClaudeSessionError,
    ClaudeTimeoutError,
    ClaudeToolValidationError,
)
from .facade import ClaudeIntegration
from .integration import ClaudeProcessManager, ClaudeResponse, StreamUpdate
from .monitor import ToolMonitor
from .parser import OutputParser
from .sdk_integration import ClaudeSDKManager
from .session import (
    ClaudeSession,
    InMemorySessionStorage,
    SessionManager,
    SessionStorage,
)
from .storage import RedisSessionStorage
from .metrics import MetricsRegistry, get_metrics, PROMETHEUS_AVAILABLE
from .background_tasks import BackgroundTaskManager, BackgroundTask

__version__ = "0.1.0"

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
    "ClaudeToolValidationError",
    # Main integration
    "ClaudeIntegration",
    # Core components
    "ClaudeProcessManager",
    "ClaudeSDKManager",
    "ClaudeResponse",
    "StreamUpdate",
    # Session Management
    "ClaudeSession",
    "SessionStorage",
    "InMemorySessionStorage",
    "RedisSessionStorage",
    "SessionManager",
    # Monitoring
    "ToolMonitor",
    # Parsing
    "OutputParser",
    # Metrics
    "MetricsRegistry",
    "get_metrics",
    "PROMETHEUS_AVAILABLE",
    # Background Tasks
    "BackgroundTaskManager",
    "BackgroundTask",
]
