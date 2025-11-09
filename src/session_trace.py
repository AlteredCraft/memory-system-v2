"""
Session Trace: Records LLM interactions for analysis and debugging

This module provides a JSON-based trace system that captures:
- User inputs
- LLM decisions (tool calls)
- Tool execution results
- LLM responses
- Token usage statistics

Each session is stored in a separate timestamped JSON file in the sessions/ directory.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


logger = logging.getLogger(__name__)


class SessionTrace:
    """
    Manages session trace recording for LLM interactions.

    Each trace includes:
    - Session metadata (ID, start time, model, system prompt)
    - Chronological events (user inputs, tool calls, responses)
    - Token usage tracking
    """

    def __init__(self, base_path: str = "./sessions", model: str = "", system_prompt: str = ""):
        """
        Initialize a new session trace.

        Args:
            base_path: Directory for storing session trace files
            model: Claude model version being used
            system_prompt: System prompt for this session
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True, parents=True)

        # Generate session ID with timestamp and unique suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid4().hex[:8]
        self.session_id = f"{timestamp}_{unique_id}"

        # Initialize trace structure
        self.trace: Dict[str, Any] = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "model": model,
            "system_prompt": system_prompt,
            "events": []
        }

        # Determine trace file path
        self.trace_file = self.base_path / f"session_{self.session_id}.json"

        logger.info(f"[TRACE] Session started: {self.session_id}")
        logger.debug(f"[TRACE] Trace file: {self.trace_file}")

        # Write initial trace file
        self._save()

    def _save(self) -> None:
        """Save the current trace to disk."""
        try:
            with open(self.trace_file, 'w', encoding='utf-8') as f:
                json.dump(self.trace, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[TRACE] Failed to save trace file: {e}")

    def _add_event(self, event_type: str, **kwargs) -> None:
        """
        Add an event to the trace.

        Args:
            event_type: Type of event (user_input, llm_request, tool_call, etc.)
            **kwargs: Event-specific data
        """
        event: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
        }
        event.update(kwargs)

        self.trace["events"].append(event)
        self._save()

        logger.debug(f"[TRACE] Event recorded: {event_type}")

    def log_user_input(self, content: str) -> None:
        """
        Record a user input event.

        Args:
            content: The user's message
        """
        self._add_event(
            event_type="user_input",
            content=content
        )

    def log_llm_request(self, messages_count: int, tools: List[str]) -> None:
        """
        Record an LLM request event.

        Args:
            messages_count: Number of messages in the conversation history
            tools: List of tools available to the LLM
        """
        self._add_event(
            event_type="llm_request",
            messages_count=messages_count,
            tools=tools
        )

    def log_tool_call(self, tool_name: str, command: str, parameters: Dict[str, Any]) -> None:
        """
        Record a tool call decision by the LLM.

        Args:
            tool_name: Name of the tool being called
            command: Command/operation being executed
            parameters: Parameters passed to the tool
        """
        self._add_event(
            event_type="tool_call",
            tool_name=tool_name,
            command=command,
            parameters=parameters
        )

    def log_tool_result(self, tool_name: str, command: str, result: str, success: bool = True, error: Optional[str] = None) -> None:
        """
        Record the result of a tool execution.

        Args:
            tool_name: Name of the tool that was called
            command: Command/operation that was executed
            result: Result returned by the tool (truncated if too long)
            success: Whether the tool call succeeded
            error: Error message if tool call failed
        """
        # Truncate very long results for readability
        result_data = result
        if len(result) > 1000:
            result_data = result[:1000] + f"... (truncated, total length: {len(result)} chars)"

        event_data = {
            "tool_name": tool_name,
            "command": command,
            "result": result_data,
            "success": success,
            "result_length": len(result)
        }

        if error:
            event_data["error"] = error

        self._add_event(event_type="tool_result", **event_data)

    def log_llm_response(self, content: str) -> None:
        """
        Record an LLM text response.

        Args:
            content: The LLM's response to the user
        """
        self._add_event(
            event_type="llm_response",
            content=content
        )

    def log_token_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
        total_cache_read_tokens: int = 0,
        total_cache_write_tokens: int = 0
    ) -> None:
        """
        Record token usage statistics.

        Args:
            input_tokens: Input tokens for last request
            output_tokens: Output tokens for last request
            cache_read_tokens: Cache read tokens for last request
            cache_write_tokens: Cache write tokens for last request
            total_input_tokens: Cumulative input tokens for session
            total_output_tokens: Cumulative output tokens for session
            total_cache_read_tokens: Cumulative cache read tokens for session
            total_cache_write_tokens: Cumulative cache write tokens for session
        """
        self._add_event(
            event_type="token_usage",
            last_request={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_write_tokens": cache_write_tokens
            },
            cumulative={
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_cache_read_tokens": total_cache_read_tokens,
                "total_cache_write_tokens": total_cache_write_tokens
            }
        )

    def log_error(self, error_type: str, message: str, traceback: Optional[str] = None) -> None:
        """
        Record an error event.

        Args:
            error_type: Type of error
            message: Error message
            traceback: Optional traceback information
        """
        event_data = {
            "error_type": error_type,
            "message": message
        }

        if traceback:
            event_data["traceback"] = traceback

        self._add_event(event_type="error", **event_data)

    def finalize(self) -> str:
        """
        Finalize the session trace.

        Returns:
            Path to the trace file
        """
        self.trace["end_time"] = datetime.now().isoformat()
        self._save()

        logger.info(f"[TRACE] Session finalized: {self.session_id}")
        return str(self.trace_file)
