"""Automatic Claude CLI authentication management.

Handles automatic detection and copying of Claude credentials
to prevent authentication failures.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()


class AuthManager:
    """Manages Claude CLI authentication credentials."""

    def __init__(self):
        self.home = Path.home()
        self.claude_dir = self.home / ".claude"
        self.credentials_file = self.claude_dir / ".credentials.json"
        self._retry_count = 0
        self._max_retries = 2

    def ensure_credentials(self) -> bool:
        """
        Ensure Claude credentials exist for current user.

        Returns:
            True if credentials are available, False otherwise
        """
        # Check if credentials already exist
        if self.credentials_file.exists():
            logger.debug("Credentials found", path=str(self.credentials_file))
            return True

        # Try to find and copy credentials
        logger.info("Credentials not found, searching for credentials to copy")
        return self._try_copy_credentials()

    def handle_auth_error(self) -> bool:
        """
        Handle authentication error by trying to recover credentials.

        Returns:
            True if recovery was attempted and might have succeeded, False if max retries reached
        """
        self._retry_count += 1

        if self._retry_count > self._max_retries:
            logger.error(
                "Max authentication retry attempts reached",
                retry_count=self._retry_count,
                max_retries=self._max_retries
            )
            return False

        logger.warning(
            "Authentication failed, attempting recovery",
            retry_count=self._retry_count,
            max_retries=self._max_retries
        )

        # Remove potentially corrupted credentials
        if self.credentials_file.exists():
            logger.info("Removing potentially corrupted credentials")
            self.credentials_file.unlink()

        # Try to find fresh credentials
        return self._try_copy_credentials()

    def _try_copy_credentials(self) -> bool:
        """
        Try to copy credentials from common locations.

        Returns:
            True if credentials were found and copied, False otherwise
        """
        # List of potential credential locations to check
        search_paths = [
            Path("/root/.claude/.credentials.json"),
            Path("/home/root/.claude/.credentials.json"),
        ]

        # Also check other user directories if running as specific user
        current_user = os.environ.get("USER") or os.environ.get("USERNAME")
        if current_user and current_user != "root":
            search_paths.append(Path(f"/home/{current_user}/.claude/.credentials.json"))

        for source_path in search_paths:
            if source_path.exists() and source_path != self.credentials_file:
                try:
                    logger.info(
                        "Found credentials, copying",
                        source=str(source_path),
                        dest=str(self.credentials_file)
                    )

                    # Create .claude directory if it doesn't exist
                    self.claude_dir.mkdir(parents=True, exist_ok=True)

                    # Copy credentials
                    shutil.copy2(source_path, self.credentials_file)

                    # Set proper permissions
                    self.credentials_file.chmod(0o600)

                    logger.info("Credentials successfully copied")
                    return True

                except Exception as e:
                    logger.warning(
                        "Failed to copy credentials",
                        source=str(source_path),
                        error=str(e)
                    )
                    continue

        logger.warning("No valid credentials found in any location")
        return False

    def get_auth_instructions(self) -> str:
        """
        Get user-friendly instructions for authentication.

        Returns:
            Instructions string
        """
        return (
            "Claude CLI is not authenticated. Please authenticate using one of these methods:\n"
            "  1. Run 'claude' in terminal and use '/login' command\n"
            "  2. Set ANTHROPIC_API_KEY environment variable\n"
            f"  3. Place credentials file at: {self.credentials_file}"
        )
