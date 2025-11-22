"""Configuration for Claude CLI integration."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ClaudeConfig:
    """Configuration for Claude CLI integration.

    This is a minimal config dataclass that can be used standalone
    or integrated into larger config systems (Pydantic Settings, etc).
    """

    # Claude CLI binary path
    claude_binary_path: str = "claude"

    # Timeout settings
    claude_timeout_seconds: int = 300  # 5 minutes

    # Claude behavior
    claude_max_turns: int = 50
    claude_allowed_tools: Optional[List[str]] = None

    # Session management
    session_timeout_hours: int = 24
    max_sessions_per_user: int = 5

    # SDK vs subprocess
    use_sdk: bool = False  # Use claude-code-sdk if True, subprocess if False

    # SDK-specific settings
    claude_cli_path: Optional[str] = None  # Alternative path to Claude CLI (for SDK)
    anthropic_api_key_str: Optional[str] = None  # API key for SDK authentication

    # Redis storage settings
    redis_enabled: bool = False  # Enable Redis for session storage
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_max_connections: int = 10
    redis_socket_timeout: float = 5.0
    redis_socket_connect_timeout: float = 5.0
    redis_default_ttl: int = 3600  # 1 hour
    redis_key_prefix: str = "claude_cli:session:"
    redis_enable_fallback: bool = True  # Fallback to in-memory on Redis failure

    # Rate limiting settings
    rate_limit_enabled: bool = True  # Enable rate limiting
    rate_limit_per_minute: int = 20  # Requests per minute per user for /api/v1/chat
    rate_limit_sessions_per_minute: int = 30  # Requests per minute for /api/v1/sessions/*
    rate_limit_global: int = 100  # Global requests per minute across all users

    # Cache settings
    cache_enabled: bool = True  # Enable response caching
    cache_ttl_seconds: int = 60  # Default TTL for cache entries
    cache_max_size: int = 1000  # Maximum number of cached entries

    # Debug and monitoring settings
    debug_mode: bool = False  # Enable debug endpoints and verbose logging
    slow_request_threshold_seconds: float = 5.0  # Threshold for slow request detection
    log_all_requests: bool = False  # Log all requests (if False, only non-200 or slow)

    # Background tasks settings
    background_tasks_enabled: bool = True  # Enable background tasks
    cleanup_interval_seconds: int = 300  # Session cleanup interval (5 minutes)
    metrics_aggregation_interval_seconds: int = 30  # Metrics aggregation interval
    rate_limiter_cleanup_interval_seconds: int = 300  # Rate limiter cleanup interval (5 minutes)
    shutdown_timeout_seconds: int = 30  # Maximum time to wait for graceful shutdown

    def __post_init__(self):
        """Set default allowed tools if not specified."""
        if self.claude_allowed_tools is None:
            self.claude_allowed_tools = [
                "Read",
                "Write",
                "Edit",
                "Bash",
                "Glob",
                "Grep",
                "Task",
                "WebFetch",
                "WebSearch",
                "TodoWrite",
                "MultiEdit",
                "NotebookRead",
                "NotebookEdit",
                "LS",
            ]


# Mapping of config field names to their default values
_CONFIG_DEFAULTS = {
    "claude_binary_path": "claude",
    "claude_timeout_seconds": 300,
    "claude_max_turns": 50,
    "claude_allowed_tools": None,
    "session_timeout_hours": 24,
    "max_sessions_per_user": 5,
    "use_sdk": False,
    "claude_cli_path": None,
    "anthropic_api_key_str": None,
    "redis_enabled": False,
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,
    "redis_password": None,
    "redis_max_connections": 10,
    "redis_socket_timeout": 5.0,
    "redis_socket_connect_timeout": 5.0,
    "redis_default_ttl": 3600,
    "redis_key_prefix": "claude_cli:session:",
    "redis_enable_fallback": True,
    "rate_limit_enabled": True,
    "rate_limit_per_minute": 20,
    "rate_limit_sessions_per_minute": 30,
    "rate_limit_global": 100,
    "cache_enabled": True,
    "cache_ttl_seconds": 60,
    "cache_max_size": 1000,
    "debug_mode": False,
    "slow_request_threshold_seconds": 5.0,
    "log_all_requests": False,
    "background_tasks_enabled": True,
    "cleanup_interval_seconds": 300,
    "metrics_aggregation_interval_seconds": 30,
    "rate_limiter_cleanup_interval_seconds": 300,
    "shutdown_timeout_seconds": 30,
}


def _extract_config_values(source_obj, value_getter) -> dict:
    """Extract config values from a source object using a getter function.

    Args:
        source_obj: Source object to extract values from
        value_getter: Function to get value from source (field_name, default) -> value

    Returns:
        Dictionary of field names to values
    """
    return {
        field_name: value_getter(source_obj, field_name, default_value)
        for field_name, default_value in _CONFIG_DEFAULTS.items()
    }


# Example: Integration with Pydantic Settings
def from_pydantic_settings(settings_obj) -> ClaudeConfig:
    """Convert Pydantic Settings object to ClaudeConfig.

    Usage:
        from pydantic_settings import BaseSettings

        class Settings(BaseSettings):
            claude_binary_path: str = "claude"
            # ... other fields

        settings = Settings()
        config = from_pydantic_settings(settings)
    """
    values = _extract_config_values(
        settings_obj,
        lambda obj, field, default: getattr(obj, field, default)
    )
    return ClaudeConfig(**values)


# Type converters for environment variables
_ENV_TYPE_CONVERTERS = {
    "claude_timeout_seconds": int,
    "claude_max_turns": int,
    "session_timeout_hours": int,
    "max_sessions_per_user": int,
    "redis_port": int,
    "redis_db": int,
    "redis_max_connections": int,
    "redis_socket_timeout": float,
    "redis_socket_connect_timeout": float,
    "redis_default_ttl": int,
    "rate_limit_per_minute": int,
    "rate_limit_sessions_per_minute": int,
    "rate_limit_global": int,
    "cache_ttl_seconds": int,
    "cache_max_size": int,
    "slow_request_threshold_seconds": float,
    "cleanup_interval_seconds": int,
    "metrics_aggregation_interval_seconds": int,
    "rate_limiter_cleanup_interval_seconds": int,
    "shutdown_timeout_seconds": int,
}

# Environment variable name mapping (field_name -> ENV_VAR_NAME)
_ENV_VAR_NAMES = {
    "claude_binary_path": "CLAUDE_BINARY_PATH",
    "claude_timeout_seconds": "CLAUDE_TIMEOUT_SECONDS",
    "claude_max_turns": "CLAUDE_MAX_TURNS",
    "claude_allowed_tools": "CLAUDE_ALLOWED_TOOLS",
    "session_timeout_hours": "CLAUDE_SESSION_TIMEOUT_HOURS",
    "max_sessions_per_user": "CLAUDE_MAX_SESSIONS_PER_USER",
    "use_sdk": "CLAUDE_USE_SDK",
    "claude_cli_path": "CLAUDE_CLI_PATH",
    "anthropic_api_key_str": "ANTHROPIC_API_KEY",
    "redis_enabled": "REDIS_ENABLED",
    "redis_host": "REDIS_HOST",
    "redis_port": "REDIS_PORT",
    "redis_db": "REDIS_DB",
    "redis_password": "REDIS_PASSWORD",
    "redis_max_connections": "REDIS_MAX_CONNECTIONS",
    "redis_socket_timeout": "REDIS_SOCKET_TIMEOUT",
    "redis_socket_connect_timeout": "REDIS_SOCKET_CONNECT_TIMEOUT",
    "redis_default_ttl": "REDIS_DEFAULT_TTL",
    "redis_key_prefix": "REDIS_KEY_PREFIX",
    "redis_enable_fallback": "REDIS_ENABLE_FALLBACK",
    "rate_limit_enabled": "RATE_LIMIT_ENABLED",
    "rate_limit_per_minute": "RATE_LIMIT_PER_MINUTE",
    "rate_limit_sessions_per_minute": "RATE_LIMIT_SESSIONS_PER_MINUTE",
    "rate_limit_global": "RATE_LIMIT_GLOBAL",
    "cache_enabled": "CACHE_ENABLED",
    "cache_ttl_seconds": "CACHE_TTL_SECONDS",
    "cache_max_size": "CACHE_MAX_SIZE",
    "debug_mode": "DEBUG_MODE",
    "slow_request_threshold_seconds": "SLOW_REQUEST_THRESHOLD_SECONDS",
    "log_all_requests": "LOG_ALL_REQUESTS",
    "background_tasks_enabled": "BACKGROUND_TASKS_ENABLED",
    "cleanup_interval_seconds": "CLEANUP_INTERVAL_SECONDS",
    "metrics_aggregation_interval_seconds": "METRICS_AGGREGATION_INTERVAL_SECONDS",
    "rate_limiter_cleanup_interval_seconds": "RATE_LIMITER_CLEANUP_INTERVAL_SECONDS",
    "shutdown_timeout_seconds": "SHUTDOWN_TIMEOUT_SECONDS",
}


def _get_env_value(field_name: str, default_value):
    """Get value from environment variable with proper type conversion.

    Args:
        field_name: Config field name
        default_value: Default value if env var not set

    Returns:
        Converted value from environment or default
    """
    import os

    env_var_name = _ENV_VAR_NAMES.get(field_name, field_name.upper())
    env_value = os.getenv(env_var_name)

    if env_value is None:
        return default_value

    # Special handling for specific fields
    if field_name == "claude_allowed_tools":
        return [t.strip() for t in env_value.split(",")]
    elif field_name in ("use_sdk", "redis_enabled", "redis_enable_fallback", "rate_limit_enabled", "cache_enabled", "debug_mode", "log_all_requests", "background_tasks_enabled"):
        return env_value.lower() == "true"

    # Apply type converter if available
    converter = _ENV_TYPE_CONVERTERS.get(field_name)
    if converter:
        return converter(env_value)

    return env_value


# Example: Create from environment variables
def from_env() -> ClaudeConfig:
    """Create config from environment variables.

    Environment variables:
        CLAUDE_BINARY_PATH - Path to Claude CLI binary
        CLAUDE_TIMEOUT_SECONDS - Timeout in seconds
        CLAUDE_MAX_TURNS - Maximum conversation turns
        CLAUDE_ALLOWED_TOOLS - Comma-separated list of allowed tools
        CLAUDE_USE_SDK - Use SDK instead of subprocess (true/false)
        REDIS_ENABLED - Enable Redis storage (true/false)
        RATE_LIMIT_ENABLED - Enable rate limiting (true/false)
        ... (see _ENV_VAR_NAMES for full list)
    """
    values = {
        field_name: _get_env_value(field_name, default_value)
        for field_name, default_value in _CONFIG_DEFAULTS.items()
    }
    return ClaudeConfig(**values)
