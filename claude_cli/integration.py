"""Claude Code subprocess management.

Features:
- Async subprocess execution
- Stream handling
- Timeout management
- Error recovery
"""

import asyncio
import json
import uuid
from asyncio.subprocess import Process
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import structlog

from .config import ClaudeConfig
from .exceptions import (
    ClaudeParsingError,
    ClaudeProcessError,
    ClaudeSessionError,
    ClaudeTimeoutError,
)

logger = structlog.get_logger()


@dataclass
class ClaudeResponse:
    """Response from Claude Code."""

    content: str
    session_id: str
    cost: float
    duration_ms: int
    num_turns: int
    is_error: bool = False
    error_type: Optional[str] = None
    tools_used: List[Dict[str, Any]] = field(default_factory=list)
    http_calls: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StreamUpdate:
    """Enhanced streaming update from Claude with richer context."""

    type: str  # 'assistant', 'user', 'system', 'result', 'tool_result', 'error', 'progress'
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None

    # Enhanced fields for better tracking
    timestamp: Optional[str] = None
    session_context: Optional[Dict] = None
    progress: Optional[Dict] = None
    error_info: Optional[Dict] = None

    # Execution tracking
    execution_id: Optional[str] = None
    parent_message_id: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this update represents an error."""
        return self.type == "error" or (
            self.metadata and self.metadata.get("is_error", False)
        )

    def get_tool_names(self) -> List[str]:
        """Extract tool names from tool calls."""
        if not self.tool_calls:
            return []
        return [call.get("name") for call in self.tool_calls if call.get("name")]

    def get_progress_percentage(self) -> Optional[int]:
        """Get progress percentage if available."""
        if self.progress:
            return self.progress.get("percentage")
        return None

    def get_error_message(self) -> Optional[str]:
        """Get error message if this is an error update."""
        if self.error_info:
            return self.error_info.get("message")
        elif self.is_error() and self.content:
            return self.content
        return None


class ClaudeProcessManager:
    """Manage Claude Code subprocess execution with memory optimization."""

    def __init__(self, config: ClaudeConfig, tool_monitor=None):
        """Initialize process manager with configuration."""
        self.config = config
        self.active_processes: Dict[str, Process] = {}
        self.tool_monitor = tool_monitor

        # Memory optimization settings
        self.max_message_buffer = 1000  # Limit message history
        self.streaming_buffer_size = (
            65536  # 64KB streaming buffer for large JSON messages
        )

    async def execute_command(
        self,
        prompt: str,
        working_directory: Path,
        session_id: Optional[str] = None,
        continue_session: bool = False,
        stream_callback: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> ClaudeResponse:
        """Execute Claude Code command."""
        # Build command
        cmd = self._build_command(prompt, session_id, continue_session)

        # Create process ID for tracking
        process_id = str(uuid.uuid4())

        logger.info(
            "Starting Claude Code process",
            process_id=process_id,
            working_directory=str(working_directory),
            session_id=session_id,
            continue_session=continue_session,
        )

        try:
            # Start process
            process = await self._start_process(cmd, working_directory)
            self.active_processes[process_id] = process

            # Handle output with timeout
            result = await asyncio.wait_for(
                self._handle_process_output(process, stream_callback, working_directory),
                timeout=self.config.claude_timeout_seconds,
            )

            logger.info(
                "Claude Code process completed successfully",
                process_id=process_id,
                cost=result.cost,
                duration_ms=result.duration_ms,
            )

            return result

        except asyncio.TimeoutError:
            # Kill process on timeout
            if process_id in self.active_processes:
                self.active_processes[process_id].kill()
                await self.active_processes[process_id].wait()

            logger.error(
                "Claude Code process timed out",
                process_id=process_id,
                timeout_seconds=self.config.claude_timeout_seconds,
            )

            raise ClaudeTimeoutError(
                f"Claude Code timed out after {self.config.claude_timeout_seconds}s"
            )

        except Exception as e:
            logger.error(
                "Claude Code process failed",
                process_id=process_id,
                error=str(e),
            )
            raise

        finally:
            # Clean up
            if process_id in self.active_processes:
                del self.active_processes[process_id]

    def _build_command(
        self, prompt: str, session_id: Optional[str], continue_session: bool
    ) -> List[str]:
        """Build Claude Code command with arguments."""
        cmd = [self.config.claude_binary_path or "claude"]

        if continue_session and not prompt:
            # Continue existing session without new prompt
            cmd.extend(["--continue"])
            if session_id:
                cmd.extend(["--resume", session_id])
        elif session_id and prompt and continue_session:
            # Follow-up message in existing session - use resume with new prompt
            cmd.extend(["--resume", session_id, "-p", prompt])
        elif prompt:
            # New session with prompt (including new sessions with session_id)
            cmd.extend(["-p", prompt])
        else:
            # This shouldn't happen, but fallback to new session
            cmd.extend(["-p", ""])

        # Always use streaming JSON for real-time updates
        cmd.extend(["--output-format", "stream-json"])

        # stream-json requires --verbose when using --print mode
        cmd.extend(["--verbose"])

        # Add safety limits
        cmd.extend(["--max-turns", str(self.config.claude_max_turns)])

        # Add allowed tools if configured
        if (
            hasattr(self.config, "claude_allowed_tools")
            and self.config.claude_allowed_tools
        ):
            cmd.extend(["--allowedTools", ",".join(self.config.claude_allowed_tools)])

        # ⚠️ КРИТИЧЕСКИ ВАЖНО: Флаг --dangerously-skip-permissions ОБЯЗАТЕЛЕН для работы hooks!
        # Без него hooks НЕ БУДУТ СРАБАТЫВАТЬ (архитектурное требование EVA Platform)
        cmd.extend(["--dangerously-skip-permissions"])

        logger.debug("Built Claude Code command", command=cmd)
        return cmd

    async def _start_process(self, cmd: List[str], cwd: Path) -> Process:
        """Start Claude Code subprocess with proper environment and config."""
        import os
        import json
        import shutil

        # Copy credentials from config to session .claude folder
        credentials_source = Path(__file__).parent.parent / "config" / "credentials" / ".credentials.json"
        credentials_target = cwd / ".claude" / ".credentials.json"

        if credentials_source.exists():
            try:
                shutil.copy2(credentials_source, credentials_target)
                logger.info(f"Copied credentials to {credentials_target}")
            except Exception as e:
                logger.error(f"Failed to copy credentials: {e}")

        # Create .claude.json with pre-approved permissions AND hooks registration
        claude_config = cwd / ".claude.json"
        if not claude_config.exists():
            # Check if hooks exist in .claude/hooks/
            hooks_dir = cwd / ".claude" / "hooks"
            hooks_list = []

            if hooks_dir.exists():
                # Register session-isolation hook
                if (hooks_dir / "session-isolation.py").exists():
                    hooks_list.append({
                        "name": "session-isolation",
                        "path": ".claude/hooks/session-isolation.py",
                        "events": ["PreToolUse"]
                    })

                # Register external-knowledge hook
                if (hooks_dir / "external_knowledge_hook.py").exists():
                    hooks_list.append({
                        "name": "external-knowledge",
                        "path": ".claude/hooks/external_knowledge_hook.py",
                        "events": ["UserPromptSubmit", "PreToolUse", "Stop"]
                    })

            config_data = {
                "installMethod": "agentapi",
                "autoUpdates": False,
                "projects": {
                    str(cwd): {
                        "allowedTools": [
                            "Task", "Bash", "Glob", "Grep", "LS",
                            "Read", "Edit", "MultiEdit", "Write",
                            "NotebookRead", "NotebookEdit",
                            "WebFetch", "TodoWrite", "WebSearch",
                            "SlashCommand", "BashOutput"
                        ],
                        "hasTrustDialogAccepted": True,
                        "projectOnboardingSeenCount": 1,
                        "hooks": hooks_list  # ← КРИТИЧЕСКИ ВАЖНО: регистрируем hooks!
                    }
                },
                "bypassPermissionsModeAccepted": True,
                "hasCompletedOnboarding": True
            }
            with open(claude_config, 'w') as f:
                json.dump(config_data, f, indent=2)

        # Set up environment with critical variables
        env = os.environ.copy()
        env['CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR'] = 'true'
        env['CLAUDE_PROJECT_DIR'] = str(cwd)

        return await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=env,  # ← CRITICAL FIX
            # Limit memory usage
            limit=1024 * 1024 * 512,  # 512MB
        )

    async def _handle_process_output(
        self, process: Process, stream_callback: Optional[Callable], working_directory: Path
    ) -> ClaudeResponse:
        """Memory-optimized output handling with bounded buffers."""
        message_buffer = deque(maxlen=self.max_message_buffer)
        result = None
        parsing_errors = []

        async for line in self._read_stream_bounded(process.stdout):
            try:
                msg = json.loads(line)

                # Enhanced validation
                if not self._validate_message_structure(msg):
                    parsing_errors.append(f"Invalid message structure: {line[:100]}")
                    continue

                message_buffer.append(msg)

                # Process immediately to avoid memory buildup
                update = self._parse_stream_message(msg)
                if update and stream_callback:
                    try:
                        await stream_callback(update)
                    except Exception as e:
                        logger.warning(
                            "Stream callback failed",
                            error=str(e),
                            update_type=update.type,
                        )

                # Check for final result
                if msg.get("type") == "result":
                    result = msg

            except json.JSONDecodeError as e:
                parsing_errors.append(f"JSON decode error: {e}")
                logger.warning(
                    "Failed to parse JSON line", line=line[:200], error=str(e)
                )
                continue

        # Enhanced error reporting
        if parsing_errors:
            logger.warning(
                "Parsing errors encountered",
                count=len(parsing_errors),
                errors=parsing_errors[:5],
            )

        # Wait for process to complete
        return_code = await process.wait()

        if return_code != 0:
            stderr = await process.stderr.read()
            error_msg = stderr.decode("utf-8", errors="replace")
            logger.error(
                "Claude Code process failed",
                return_code=return_code,
                stderr=error_msg,
            )

            # Check for specific error types
            import re

            # 1. Authentication errors
            if any(phrase in error_msg.lower() for phrase in [
                "not authenticated",
                "authentication failed",
                "please run 'claude setup-token'",
                "no valid token found"
            ]):
                user_friendly_msg = (
                    f"🔐 **Claude Authentication Required**\n\n"
                    f"Claude CLI is not authenticated.\n\n"
                    f"**How to fix:**\n"
                    f"1. Run: `claude setup-token`\n"
                    f"2. Follow the authentication flow\n"
                    f"3. Try your request again\n\n"
                    f"**For servers/automation:**\n"
                    f"• Set ANTHROPIC_API_KEY environment variable\n"
                    f"• Or authenticate once and Claude will remember"
                )
                raise ClaudeProcessError(user_friendly_msg)

            # 2. Invalid/expired session errors
            if any(phrase in error_msg.lower() for phrase in [
                "session not found",
                "invalid session",
                "session expired",
                "could not resume"
            ]):
                user_friendly_msg = (
                    f"🔄 **Claude Session Invalid**\n\n"
                    f"The requested session is no longer available.\n\n"
                    f"**Possible reasons:**\n"
                    f"• Session was deleted\n"
                    f"• Session ID is incorrect\n"
                    f"• Claude's session storage was cleared\n\n"
                    f"**Solution:**\n"
                    f"A new session will be created automatically for your next request."
                )
                raise ClaudeSessionError(user_friendly_msg)

            # 3. Usage limit errors
            if "usage limit reached" in error_msg.lower():
                # Extract reset time if available
                time_match = re.search(
                    r"reset at (\d+[apm]+)", error_msg, re.IGNORECASE
                )
                timezone_match = re.search(r"\(([^)]+)\)", error_msg)

                reset_time = time_match.group(1) if time_match else "later"
                timezone = timezone_match.group(1) if timezone_match else ""

                user_friendly_msg = (
                    f"⏱️ **Claude AI Usage Limit Reached**\n\n"
                    f"You've reached your Claude AI usage limit for this period.\n\n"
                    f"**When will it reset?**\n"
                    f"Your limit will reset at **{reset_time}**"
                    f"{f' ({timezone})' if timezone else ''}\n\n"
                    f"**What you can do:**\n"
                    f"• Wait for the limit to reset automatically\n"
                    f"• Try again after the reset time\n"
                    f"• Use simpler requests that require less processing\n"
                    f"• Contact support if you need a higher limit"
                )

                raise ClaudeProcessError(user_friendly_msg)

            # Generic error handling for other cases
            raise ClaudeProcessError(
                f"Claude Code exited with code {return_code}: {error_msg}"
            )

        if not result:
            logger.error("No result message received from Claude Code")
            raise ClaudeParsingError("No result message received from Claude Code")

        return self._parse_result(result, list(message_buffer), working_directory)

    async def _read_stream(self, stream) -> AsyncIterator[str]:
        """Read lines from stream."""
        while True:
            line = await stream.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace").strip()

    async def _read_stream_bounded(self, stream) -> AsyncIterator[str]:
        """Read stream with memory bounds to prevent excessive memory usage."""
        buffer = b""

        while True:
            chunk = await stream.read(self.streaming_buffer_size)
            if not chunk:
                break

            buffer += chunk

            # Process complete lines
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                yield line.decode("utf-8", errors="replace").strip()

        # Process remaining buffer
        if buffer:
            yield buffer.decode("utf-8", errors="replace").strip()

    def _parse_stream_message(self, msg: Dict) -> Optional[StreamUpdate]:
        """Enhanced parsing with comprehensive message type support."""
        msg_type = msg.get("type")

        # Add support for more message types
        if msg_type == "assistant":
            return self._parse_assistant_message(msg)
        elif msg_type == "tool_result":
            return self._parse_tool_result_message(msg)
        elif msg_type == "user":
            return self._parse_user_message(msg)
        elif msg_type == "system":
            return self._parse_system_message(msg)
        elif msg_type == "error":
            return self._parse_error_message(msg)
        elif msg_type == "progress":
            return self._parse_progress_message(msg)

        # Unknown message type - log and continue
        logger.debug("Unknown message type", msg_type=msg_type, msg=msg)
        return None

    def _parse_assistant_message(self, msg: Dict) -> StreamUpdate:
        """Parse assistant message with enhanced context."""
        message = msg.get("message", {})
        content_blocks = message.get("content", [])

        # Get text content
        text_content = []
        tool_calls = []

        for block in content_blocks:
            if block.get("type") == "text":
                text_content.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    {
                        "name": block.get("name"),
                        "input": block.get("input", {}),
                        "id": block.get("id"),
                    }
                )

        return StreamUpdate(
            type="assistant",
            content="\n".join(text_content) if text_content else None,
            tool_calls=tool_calls if tool_calls else None,
            timestamp=msg.get("timestamp"),
            session_context={"session_id": msg.get("session_id")},
            execution_id=msg.get("id"),
        )

    def _parse_tool_result_message(self, msg: Dict) -> StreamUpdate:
        """Parse tool execution results."""
        result = msg.get("result", {})
        content = result.get("content") if isinstance(result, dict) else str(result)

        return StreamUpdate(
            type="tool_result",
            content=content,
            metadata={
                "tool_use_id": msg.get("tool_use_id"),
                "is_error": (
                    result.get("is_error", False) if isinstance(result, dict) else False
                ),
                "execution_time_ms": (
                    result.get("execution_time_ms")
                    if isinstance(result, dict)
                    else None
                ),
            },
            timestamp=msg.get("timestamp"),
            session_context={"session_id": msg.get("session_id")},
            error_info={"message": content} if result.get("is_error", False) else None,
        )

    def _parse_user_message(self, msg: Dict) -> StreamUpdate:
        """Parse user message."""
        message = msg.get("message", {})
        content = message.get("content", "")

        # Handle both string and block format content
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            content = "\n".join(text_parts)

        return StreamUpdate(
            type="user",
            content=content if content else None,
            timestamp=msg.get("timestamp"),
            session_context={"session_id": msg.get("session_id")},
        )

    def _parse_system_message(self, msg: Dict) -> StreamUpdate:
        """Parse system messages including init and other subtypes."""
        subtype = msg.get("subtype")

        if subtype == "init":
            # Initial system message with available tools
            return StreamUpdate(
                type="system",
                metadata={
                    "subtype": "init",
                    "tools": msg.get("tools", []),
                    "mcp_servers": msg.get("mcp_servers", []),
                    "model": msg.get("model"),
                    "cwd": msg.get("cwd"),
                    "permission_mode": msg.get("permissionMode"),
                },
                session_context={"session_id": msg.get("session_id")},
            )
        else:
            # Other system messages
            return StreamUpdate(
                type="system",
                content=msg.get("message", str(msg)),
                metadata={"subtype": subtype},
                timestamp=msg.get("timestamp"),
                session_context={"session_id": msg.get("session_id")},
            )

    def _parse_error_message(self, msg: Dict) -> StreamUpdate:
        """Parse error messages."""
        error_message = msg.get("message", msg.get("error", str(msg)))

        return StreamUpdate(
            type="error",
            content=error_message,
            error_info={
                "message": error_message,
                "code": msg.get("code"),
                "subtype": msg.get("subtype"),
            },
            timestamp=msg.get("timestamp"),
            session_context={"session_id": msg.get("session_id")},
        )

    def _parse_progress_message(self, msg: Dict) -> StreamUpdate:
        """Parse progress update messages."""
        return StreamUpdate(
            type="progress",
            content=msg.get("message", msg.get("status")),
            progress={
                "percentage": msg.get("percentage"),
                "step": msg.get("step"),
                "total_steps": msg.get("total_steps"),
                "operation": msg.get("operation"),
            },
            timestamp=msg.get("timestamp"),
            session_context={"session_id": msg.get("session_id")},
        )

    def _validate_message_structure(self, msg: Dict) -> bool:
        """Validate message has required structure."""
        required_fields = ["type"]
        return all(field in msg for field in required_fields)

    def _parse_result(self, result: Dict, messages: List[Dict], working_directory: Path) -> ClaudeResponse:
        """Parse final result message."""
        # Extract tools used from messages with full details
        tools_used = []
        tool_results = {}  # Map tool_use_id -> result
        tool_names = {}    # Map tool_use_id -> tool_name (for debugging)

        # Extract HTTP calls if tool_monitor is available
        http_calls = []
        if self.tool_monitor:
            http_calls = self.tool_monitor.get_http_calls(working_directory)

        # DEBUG: Count message types
        msg_types = {}
        for msg in messages:
            msg_type = msg.get("type", "unknown")
            msg_types[msg_type] = msg_types.get(msg_type, 0) + 1
        logger.debug("Message types in result", msg_types=msg_types)

        # DEBUG: Dump all messages for Task debugging
        import json
        task_found = any(msg.get("type") == "assistant" and
                        any(b.get("type") == "tool_use" and b.get("name") == "Task"
                            for b in msg.get("message", {}).get("content", []))
                        for msg in messages)
        if task_found:
            with open("/tmp/full_messages.json", "w") as f:
                json.dump(messages, f, indent=2)
            logger.debug("Full messages dump saved to /tmp/full_messages.json")

        # First, collect tool names from tool_use blocks
        for msg in messages:
            if msg.get("type") == "assistant":
                message = msg.get("message", {})
                for block in message.get("content", []):
                    if block.get("type") == "tool_use":
                        tool_id = block.get("id")
                        tool_name = block.get("name")
                        if tool_id:
                            tool_names[tool_id] = tool_name
                            if tool_name == "Task":
                                logger.debug("Found Task tool_use", tool_id=tool_id, tool_input=block.get("input", {}))

        # First pass: collect tool results
        # tool_result comes as type: "user" messages with tool_result blocks inside content
        for msg in messages:
            if msg.get("type") == "user":
                message = msg.get("message", {})
                for block in message.get("content", []):
                    if block.get("type") == "tool_result":
                        tool_use_id = block.get("tool_use_id")
                        result_raw = block.get("content", "")

                        # Extract content - may be string or list of content blocks
                        if isinstance(result_raw, list):
                            # Extract text from content blocks (for Task tool results)
                            text_parts = []
                            for item in result_raw:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                            result_content = "\n".join(text_parts) if text_parts else str(result_raw)
                        else:
                            result_content = result_raw

                        tool_name = tool_names.get(tool_use_id, "unknown")
                        logger.debug("Found tool_result in user message",
                                   tool_use_id=tool_use_id[:20] if tool_use_id else None,
                                   tool_name=tool_name,
                                   result_preview=str(result_content)[:100] if result_content else None)

                        # DEBUG: Log Task tool results
                        if tool_name == "Task":
                            logger.debug("Task tool result found!",
                                       tool_use_id=tool_use_id[:20],
                                       result_content_preview=str(result_content)[:200])

                        tool_results[tool_use_id] = result_content

        # Second pass: collect tool uses with their results
        # For Task tool, also collect text content from next assistant message as fallback result
        task_tool_summary = {}  # Map tool_id -> text summary from next message

        for i, msg in enumerate(messages):
            if msg.get("type") == "assistant":
                message = msg.get("message", {})
                # Check if previous message had a Task tool_use
                if i > 0:
                    prev_msg = messages[i-1]
                    if prev_msg.get("type") == "assistant":
                        prev_content = prev_msg.get("message", {}).get("content", [])
                        for prev_block in prev_content:
                            if prev_block.get("type") == "tool_use" and prev_block.get("name") == "Task":
                                # Found Task tool, now extract text from current message
                                task_id = prev_block.get("id")
                                for block in message.get("content", []):
                                    if block.get("type") == "text":
                                        task_tool_summary[task_id] = block.get("text", "")
                                        logger.debug("Found Task summary in next message", task_id=task_id[:20], summary_preview=block.get("text", "")[:100])
                                        break

        for msg in messages:
            if msg.get("type") == "assistant":
                message = msg.get("message", {})
                for block in message.get("content", []):
                    # DEBUG: Check if there's any result embedded in content blocks
                    if block.get("type") not in ["tool_use", "text"]:
                        logger.debug("Unknown content block type", block_type=block.get("type"), block_keys=list(block.keys()))

                    if block.get("type") == "tool_use":
                        tool_id = block.get("id")
                        tool_name = block.get("name")
                        tool_entry = {
                            "name": tool_name,
                            "input": block.get("input", {}),
                            "id": tool_id,
                            "timestamp": msg.get("timestamp"),
                        }
                        # Add result if available
                        if tool_id and tool_id in tool_results:
                            tool_entry["result"] = tool_results[tool_id]
                        # Fallback for Task tool: use summary from next message
                        elif tool_name == "Task" and tool_id in task_tool_summary:
                            tool_entry["result"] = task_tool_summary[tool_id]
                            logger.debug("Using Task summary as result", tool_id=tool_id[:20])

                        tools_used.append(tool_entry)

        return ClaudeResponse(
            content=result.get("result", ""),
            session_id=result.get("session_id", ""),
            cost=result.get("cost_usd", 0.0),
            duration_ms=result.get("duration_ms", 0),
            num_turns=result.get("num_turns", 0),
            is_error=result.get("is_error", False),
            error_type=result.get("subtype") if result.get("is_error") else None,
            tools_used=tools_used,
            http_calls=http_calls,
        )

    async def kill_all_processes(self) -> None:
        """Kill all active processes."""
        logger.info(
            "Killing all active Claude processes", count=len(self.active_processes)
        )

        for process_id, process in self.active_processes.items():
            try:
                process.kill()
                await process.wait()
                logger.info("Killed Claude process", process_id=process_id)
            except Exception as e:
                logger.warning(
                    "Failed to kill process", process_id=process_id, error=str(e)
                )

        self.active_processes.clear()

    def get_active_process_count(self) -> int:
        """Get number of active processes."""
        return len(self.active_processes)
