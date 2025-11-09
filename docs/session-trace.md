# Session Trace Feature

## Overview

The session trace feature provides a structured JSON recording of all LLM interactions during a conversation session. Unlike logging (which is for development and debugging), traces are designed for **analysis, replay, and understanding LLM behavior**.

## Purpose

Session traces capture:
- **User inputs**: Every message the user sends
- **LLM decisions**: What tools the LLM chooses to use and why
- **Tool operations**: All memory tool calls with parameters and results
- **LLM responses**: Text responses sent back to the user
- **Token usage**: Both per-request and cumulative token statistics
- **Errors**: Any errors that occur during the session

## Storage

Traces are stored in the `sessions/` directory (git-ignored) with timestamped filenames:

```
sessions/session_20251109_143414_a1b2c3d4.json
```

Format: `session_YYYYMMDD_HHMMSS_<unique-id>.json`

## JSON Schema

Each trace file contains:

```json
{
  "session_id": "20251109_143414_a1b2c3d4",
  "start_time": "2025-11-09T14:34:14.123456",
  "end_time": "2025-11-09T14:45:30.789012",
  "model": "claude-sonnet-4-5-20250929",
  "system_prompt": "You are a helpful assistant...",
  "events": [
    {
      "timestamp": "2025-11-09T14:34:20.123456",
      "event_type": "user_input",
      "content": "hello"
    },
    {
      "timestamp": "2025-11-09T14:34:20.234567",
      "event_type": "llm_request",
      "messages_count": 1,
      "tools": ["memory"]
    },
    {
      "timestamp": "2025-11-09T14:34:22.345678",
      "event_type": "tool_call",
      "tool_name": "memory",
      "command": "view",
      "parameters": {
        "path": "/memories"
      }
    },
    {
      "timestamp": "2025-11-09T14:34:22.456789",
      "event_type": "tool_result",
      "tool_name": "memory",
      "command": "view",
      "result": "Directory: /memories\n- user_preferences.txt",
      "success": true,
      "result_length": 45
    },
    {
      "timestamp": "2025-11-09T14:34:25.567890",
      "event_type": "llm_response",
      "content": "Hello! How are you doing?"
    },
    {
      "timestamp": "2025-11-09T14:34:25.678901",
      "event_type": "token_usage",
      "last_request": {
        "input_tokens": 150,
        "output_tokens": 20,
        "cache_read_tokens": 0,
        "cache_write_tokens": 100
      },
      "cumulative": {
        "total_input_tokens": 150,
        "total_output_tokens": 20,
        "total_cache_read_tokens": 0,
        "total_cache_write_tokens": 100
      }
    }
  ]
}
```

## Event Types

### 1. `user_input`
Records a user message.

```json
{
  "timestamp": "2025-11-09T14:34:20.123456",
  "event_type": "user_input",
  "content": "hello"
}
```

### 2. `llm_request`
Records when a request is sent to the LLM.

```json
{
  "timestamp": "2025-11-09T14:34:20.234567",
  "event_type": "llm_request",
  "messages_count": 1,
  "tools": ["memory"]
}
```

### 3. `tool_call`
Records the LLM's decision to use a tool.

```json
{
  "timestamp": "2025-11-09T14:34:22.345678",
  "event_type": "tool_call",
  "tool_name": "memory",
  "command": "view",
  "parameters": {
    "path": "/memories",
    "view_range": null
  }
}
```

### 4. `tool_result`
Records the result of tool execution.

```json
{
  "timestamp": "2025-11-09T14:34:22.456789",
  "event_type": "tool_result",
  "tool_name": "memory",
  "command": "view",
  "result": "Directory: /memories...",
  "success": true,
  "result_length": 45
}
```

For errors:
```json
{
  "timestamp": "2025-11-09T14:34:22.456789",
  "event_type": "tool_result",
  "tool_name": "memory",
  "command": "view",
  "result": "",
  "success": false,
  "error": "File not found: /memories/nonexistent.txt"
}
```

### 5. `llm_response`
Records the LLM's text response to the user.

```json
{
  "timestamp": "2025-11-09T14:34:25.567890",
  "event_type": "llm_response",
  "content": "Hello! How are you doing?"
}
```

### 6. `token_usage`
Records token usage statistics.

```json
{
  "timestamp": "2025-11-09T14:34:25.678901",
  "event_type": "token_usage",
  "last_request": {
    "input_tokens": 150,
    "output_tokens": 20,
    "cache_read_tokens": 0,
    "cache_write_tokens": 100
  },
  "cumulative": {
    "total_input_tokens": 150,
    "total_output_tokens": 20,
    "total_cache_read_tokens": 0,
    "total_cache_write_tokens": 100
  }
}
```

### 7. `error`
Records errors that occur during the session.

```json
{
  "timestamp": "2025-11-09T14:34:30.123456",
  "event_type": "error",
  "error_type": "ValueError",
  "message": "Invalid input provided"
}
```

## Trace vs. Logging

| Feature | Trace | Logging |
|---------|-------|---------|
| **Purpose** | Session recording & analysis | Development & debugging |
| **Format** | Structured JSON | Text logs |
| **Audience** | Analysts, researchers | Developers |
| **Storage** | `sessions/` directory | Console / log files |
| **Lifecycle** | Permanent session record | Temporary, rotated |
| **Content** | LLM decisions & interactions | System events & debugging |

## Usage

### Automatic Tracing

Traces are automatically created for every session. When you exit the chat:

```
You: /quit

Session trace saved to: sessions/session_20251109_143414_a1b2c3d4.json

Goodbye!
```

### Analyzing Traces

You can analyze traces using standard JSON tools:

```bash
# Pretty print a trace
cat sessions/session_20251109_143414_a1b2c3d4.json | jq

# Count events by type
cat sessions/session_20251109_143414_a1b2c3d4.json | jq '.events | group_by(.event_type) | map({type: .[0].event_type, count: length})'

# Extract all tool calls
cat sessions/session_20251109_143414_a1b2c3d4.json | jq '.events[] | select(.event_type == "tool_call")'

# Calculate total tokens used
cat sessions/session_20251109_143414_a1b2c3d4.json | jq '.events[] | select(.event_type == "token_usage") | .cumulative' | tail -1
```

### Python Analysis

```python
import json
from pathlib import Path

# Load a trace
with open('sessions/session_20251109_143414_a1b2c3d4.json') as f:
    trace = json.load(f)

# Analyze tool usage
tool_calls = [e for e in trace['events'] if e['event_type'] == 'tool_call']
print(f"Total tool calls: {len(tool_calls)}")

# Count by command
from collections import Counter
commands = Counter(tc['command'] for tc in tool_calls)
print(f"Commands used: {commands}")

# Check for errors
errors = [e for e in trace['events'] if e['event_type'] == 'error']
if errors:
    print(f"Errors occurred: {len(errors)}")
```

## Implementation Details

### Module: `session_trace.py`

The `SessionTrace` class manages trace recording:

```python
from session_trace import SessionTrace

# Create a trace
trace = SessionTrace(model="claude-sonnet-4-5", system_prompt="...")

# Log events
trace.log_user_input("hello")
trace.log_llm_request(messages_count=1, tools=["memory"])
trace.log_tool_call("memory", "view", {"path": "/memories"})
trace.log_tool_result("memory", "view", "result...", success=True)
trace.log_llm_response("Hello!")
trace.log_token_usage(100, 20, 0, 50, 100, 20, 0, 50)

# Finalize
trace_file = trace.finalize()
```

### Integration Points

1. **chat.py** (line 162): Initialize trace at session start
2. **chat.py** (line 227): Log user input
3. **chat.py** (line 249): Log LLM request
4. **chat.py** (line 274): Log LLM response
5. **chat.py** (line 307): Log token usage
6. **memory_tool.py**: Tool calls and results logged automatically

## Benefits

1. **Reproducibility**: Replay exactly what happened in a session
2. **Analysis**: Understand LLM decision-making patterns
3. **Debugging**: Trace issues without verbose console logs
4. **Optimization**: Identify token usage patterns and optimize prompts
5. **Auditing**: Maintain a record of all LLM interactions
6. **Research**: Analyze autonomous behavior over multiple sessions

## Related Documentation

- [Data Flow Sequence Diagram](./data-flow-sequence.md) - Shows how data flows through the system
- [Memory Tool Documentation](https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool) - Official Claude memory tool docs
