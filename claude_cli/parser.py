"""Parse Claude Code output formats.

Features:
- JSON parsing
- Stream parsing
- Error detection
- Tool extraction
"""

import json
import re
from typing import Any, Dict, List

import structlog

from .exceptions import ClaudeParsingError

logger = structlog.get_logger()


class OutputParser:
    """Parse various Claude Code output formats."""

    @staticmethod
    def parse_json_output(output: str) -> Dict[str, Any]:
        """Parse single JSON output."""
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON output", output=output[:200], error=str(e)
            )
            raise ClaudeParsingError(f"Failed to parse JSON output: {e}")

    @staticmethod
    def parse_stream_json(lines: List[str]) -> List[Dict[str, Any]]:
        """Parse streaming JSON output."""
        messages = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
                messages.append(msg)
            except json.JSONDecodeError:
                logger.warning("Skipping invalid JSON line", line=line)
                continue

        return messages

    @staticmethod
    def extract_code_blocks(content: str) -> List[Dict[str, str]]:
        """Extract code blocks from response."""
        code_blocks = []
        pattern = r"```(\w+)?\n(.*?)```"

        for match in re.finditer(pattern, content, re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2).strip()

            code_blocks.append({"language": language, "code": code})

        logger.debug("Extracted code blocks", count=len(code_blocks))
        return code_blocks

    @staticmethod
    def extract_file_operations(messages: List[Dict]) -> List[Dict[str, Any]]:
        """Extract file operations from tool calls."""
        file_ops = []

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            message = msg.get("message", {})
            for block in message.get("content", []):
                if block.get("type") != "tool_use":
                    continue

                tool_name = block.get("name", "")
                tool_input = block.get("input", {})

                # Check for file-related tools
                if tool_name in [
                    "create_file",
                    "edit_file",
                    "read_file",
                    "Write",
                    "Edit",
                    "Read",
                ]:
                    file_ops.append(
                        {
                            "operation": tool_name,
                            "path": tool_input.get("path")
                            or tool_input.get("file_path"),
                            "content": tool_input.get("content")
                            or tool_input.get("new_string"),
                            "old_content": tool_input.get("old_string"),
                            "timestamp": msg.get("timestamp"),
                        }
                    )

        logger.debug("Extracted file operations", count=len(file_ops))
        return file_ops

    @staticmethod
    def extract_shell_commands(messages: List[Dict]) -> List[Dict[str, Any]]:
        """Extract shell commands from tool calls."""
        shell_commands = []

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            message = msg.get("message", {})
            for block in message.get("content", []):
                if block.get("type") != "tool_use":
                    continue

                tool_name = block.get("name", "")
                tool_input = block.get("input", {})

                # Check for shell/bash tools
                if tool_name in ["bash", "shell", "Bash"]:
                    shell_commands.append(
                        {
                            "operation": tool_name,
                            "command": tool_input.get("command"),
                            "description": tool_input.get("description"),
                            "timestamp": msg.get("timestamp"),
                        }
                    )

        logger.debug("Extracted shell commands", count=len(shell_commands))
        return shell_commands

    @staticmethod
    def extract_response_text(messages: List[Dict]) -> str:
        """Extract all text content from assistant messages."""
        text_parts = []

        for msg in messages:
            if msg.get("type") != "assistant":
                continue

            message = msg.get("message", {})
            for block in message.get("content", []):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

        return "\n".join(text_parts)

    @staticmethod
    def extract_tool_results(messages: List[Dict]) -> List[Dict[str, Any]]:
        """Extract tool results from tool_result messages."""
        tool_results = []

        for msg in messages:
            if msg.get("type") == "tool_result":
                result = msg.get("result", {})
                tool_results.append(
                    {
                        "tool_use_id": msg.get("tool_use_id"),
                        "content": result.get("content"),
                        "is_error": result.get("is_error", False),
                        "timestamp": msg.get("timestamp"),
                    }
                )

        logger.debug("Extracted tool results", count=len(tool_results))
        return tool_results

    @staticmethod
    def detect_errors(messages: List[Dict]) -> List[Dict[str, Any]]:
        """Detect errors in message stream."""
        errors = []

        for msg in messages:
            # Check for error messages
            if msg.get("is_error") or msg.get("type") == "error":
                errors.append(
                    {
                        "type": msg.get("type", "unknown"),
                        "subtype": msg.get("subtype"),
                        "message": msg.get("message", str(msg)),
                        "timestamp": msg.get("timestamp"),
                    }
                )

            # Check for tool result errors
            if msg.get("type") == "tool_result":
                result = msg.get("result", {})
                if result.get("is_error"):
                    errors.append(
                        {
                            "type": "tool_error",
                            "tool_use_id": msg.get("tool_use_id"),
                            "message": result.get("content", "Tool execution failed"),
                            "timestamp": msg.get("timestamp"),
                        }
                    )

        logger.debug("Detected errors", count=len(errors))
        return errors

    @staticmethod
    def summarize_session(messages: List[Dict]) -> Dict[str, Any]:
        """Create a summary of the session."""
        summary = {
            "total_messages": len(messages),
            "assistant_messages": 0,
            "user_messages": 0,
            "tool_calls": 0,
            "tool_results": 0,
            "errors": 0,
            "code_blocks": 0,
            "file_operations": 0,
            "shell_commands": 0,
        }

        full_text = ""

        for msg in messages:
            msg_type = msg.get("type")

            if msg_type == "assistant":
                summary["assistant_messages"] += 1

                # Extract text for analysis
                message = msg.get("message", {})
                for block in message.get("content", []):
                    if block.get("type") == "text":
                        full_text += block.get("text", "") + "\n"
                    elif block.get("type") == "tool_use":
                        summary["tool_calls"] += 1

            elif msg_type == "user":
                summary["user_messages"] += 1

            elif msg_type == "tool_result":
                summary["tool_results"] += 1

            elif msg.get("is_error") or msg_type == "error":
                summary["errors"] += 1

        # Analyze extracted content
        summary["code_blocks"] = len(OutputParser.extract_code_blocks(full_text))
        summary["file_operations"] = len(OutputParser.extract_file_operations(messages))
        summary["shell_commands"] = len(OutputParser.extract_shell_commands(messages))

        return summary
