"""High-level Claude Code integration facade.

Provides simple interface for bot handlers.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import structlog

from .config import ClaudeConfig
from .exceptions import ClaudeSessionError
from .integration import ClaudeProcessManager, ClaudeResponse, StreamUpdate
from .session import SessionManager

logger = structlog.get_logger()


class ClaudeIntegration:
    """Main integration point for Claude Code.

    Connection pooling best practices:
    - Use async context manager for proper resource management
    - Automatically handles graceful shutdown of processes
    - Cleans up sessions and connections on exit
    - Supports both SDK and subprocess execution modes
    """

    def __init__(
        self,
        config: ClaudeConfig,
        process_manager: Optional[ClaudeProcessManager] = None,
        session_manager: Optional[SessionManager] = None,
        tool_monitor: Optional = None,
    ):
        """Initialize Claude integration facade."""
        self.config = config
        self.process_manager = process_manager or ClaudeProcessManager(config, tool_monitor=None)
        self.session_manager = session_manager

    async def __aenter__(self):
        """Async context manager entry.

        Usage:
            async with ClaudeIntegration(config, ...) as claude:
                response = await claude.run_command(...)
        """
        logger.debug("ClaudeIntegration context entered")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with graceful shutdown.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred

        Returns:
            False to propagate exceptions
        """
        logger.debug("ClaudeIntegration context exiting", exc_type=exc_type.__name__ if exc_type else None)

        # Perform graceful shutdown
        try:
            await self.shutdown()
            logger.info("ClaudeIntegration shutdown completed")
        except Exception as e:
            logger.error("Error during ClaudeIntegration shutdown", error=str(e))

        # Don't suppress exceptions
        return False

    async def run_command(
        self,
        prompt: str,
        working_directory: Path,
        user_id: int,
        session_id: Optional[str] = None,
        on_stream: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> ClaudeResponse:
        """Run Claude Code command with full integration."""
        logger.info(
            "Running Claude command",
            user_id=user_id,
            working_directory=str(working_directory),
            session_id=session_id,
            prompt_length=len(prompt),
        )

        # Get or create session
        session = await self.session_manager.get_or_create_session(
            user_id, working_directory, session_id
        )

        # Execute command
        try:
            # Only continue session if it's not a new session
            should_continue = bool(session_id) and not getattr(
                session, "is_new_session", False
            )

            # For new sessions, don't pass the temporary session_id to Claude Code
            claude_session_id = (
                None
                if getattr(session, "is_new_session", False)
                else session.session_id
            )

            try:
                response = await self.process_manager.execute_command(
                    prompt=prompt,
                    working_directory=working_directory,
                    session_id=claude_session_id,
                    continue_session=should_continue,
                    stream_callback=on_stream,
                )
            except ClaudeSessionError as e:
                logger.warning("Session invalid, creating new session", error=str(e))
                if claude_session_id:
                    await self.session_manager.remove_session(claude_session_id)

                response = await self.process_manager.execute_command(
                    prompt=prompt,
                    working_directory=working_directory,
                    session_id=None,
                    continue_session=False,
                    stream_callback=on_stream,
                )

            # Update session (this may change the session_id for new sessions)
            old_session_id = session.session_id
            await self.session_manager.update_session(session.session_id, response)

            # For new sessions, get the updated session_id from the session manager
            if hasattr(session, "is_new_session") and response.session_id:
                # The session_id has been updated to Claude's session_id
                final_session_id = response.session_id
            else:
                # Use the original session_id for continuing sessions
                final_session_id = old_session_id

            # Ensure response has the correct session_id
            response.session_id = final_session_id

            logger.info(
                "Claude command completed",
                session_id=response.session_id,
                cost=response.cost,
                duration_ms=response.duration_ms,
                num_turns=response.num_turns,
                is_error=response.is_error,
            )

            return response

        except Exception as e:
            logger.error(
                "Claude command failed",
                error=str(e),
                user_id=user_id,
                session_id=session.session_id,
            )
            raise

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        return await self.session_manager.get_session_info(session_id)

    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        sessions = await self.session_manager._get_user_sessions(user_id)
        return [
            {
                "session_id": s.session_id,
                "project_path": str(s.project_path),
                "created_at": s.created_at.isoformat(),
                "last_used": s.last_used.isoformat(),
                "total_cost": s.total_cost,
                "message_count": s.message_count,
                "tools_used": s.tools_used,
                "expired": s.is_expired(self.config.session_timeout_hours),
            }
            for s in sessions
        ]

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        return await self.session_manager.cleanup_expired_sessions()

    async def shutdown(self) -> None:
        """Shutdown integration and cleanup resources."""
        logger.info("Shutting down Claude integration")
        await self.process_manager.kill_all_processes()
        await self.cleanup_expired_sessions()
        logger.info("Claude integration shutdown complete")
