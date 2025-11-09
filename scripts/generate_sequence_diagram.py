#!/usr/bin/env python3
"""
Generate Mermaid sequence diagrams from session trace files.

This script parses a session trace JSON file and generates a Mermaid sequence diagram
that visualizes the interactions between User, Host App, LLM, and Memory System.

Usage:
    python scripts/generate_sequence_diagram.py <trace_file> [--output <output_file>]

Example:
    python scripts/generate_sequence_diagram.py sessions/session_20251109_143414_a1b2c3d4.json
    python scripts/generate_sequence_diagram.py sessions/session_20251109_143414_a1b2c3d4.json --output diagram.md
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Any, Dict, List


def truncate_text(text: str, max_length: int = 60) -> str:
    """Truncate text for display in diagrams."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def escape_diagram_text(text: str) -> str:
    """Escape special characters for Mermaid diagrams."""
    # Replace newlines with <br/> for proper rendering
    text = text.replace("\n", "<br/>")
    # Escape quotes
    text = text.replace('"', '\\"')
    return text


def format_parameters(params: Dict[str, Any], max_params: int = 2) -> str:
    """Format tool call parameters for diagram display."""
    if not params:
        return ""

    # Show only first few parameters
    items = list(params.items())[:max_params]
    formatted = ", ".join(f"{k}={repr(v)[:30]}" for k, v in items)

    if len(params) > max_params:
        formatted += "..."

    return formatted


def group_conversation_turns(events: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Group events into conversation turns.
    Each turn starts with a user_input and ends with an llm_response.
    """
    turns = []
    current_turn = []

    for event in events:
        event_type = event.get("event_type")

        if event_type == "user_input":
            # Start a new turn
            if current_turn:
                turns.append(current_turn)
            current_turn = [event]
        else:
            current_turn.append(event)

    # Add the last turn
    if current_turn:
        turns.append(current_turn)

    return turns


def generate_diagram_for_turn(turn_number: int, events: List[Dict[str, Any]]) -> List[str]:
    """Generate diagram lines for a single conversation turn."""
    lines = []

    # Determine turn color (cycle through colors)
    colors = [
        "rgb(200, 220, 255)",  # Blue
        "rgb(220, 255, 220)",  # Green
        "rgb(255, 220, 220)",  # Red
        "rgb(255, 240, 200)",  # Yellow
        "rgb(230, 200, 255)",  # Purple
    ]
    color = colors[(turn_number - 1) % len(colors)]

    # Start turn block
    lines.append(f"    rect {color}")

    # Find user input for turn label
    user_input = next((e for e in events if e.get("event_type") == "user_input"), None)
    if user_input:
        user_text = truncate_text(user_input.get("content", ""), 50)
        lines.append(f'        Note over User,MemorySystem: TURN {turn_number}: "{user_text}"')
        lines.append("")

    # Process events in the turn
    for event in events:
        event_type = event.get("event_type")

        if event_type == "user_input":
            content = truncate_text(event.get("content", ""))
            content = escape_diagram_text(content)
            lines.append(f'        User->>HostApp: "{content}"')
            lines.append("        HostApp->>HostApp: messages.append(user)")
            lines.append("")

        elif event_type == "llm_request":
            tools = event.get("tools", [])
            tools_str = ", ".join(tools)
            lines.append(f"        HostApp->>LLM: POST /messages<br/>tools: [{tools_str}]<br/>messages: [history]")
            lines.append("")

        elif event_type == "tool_call":
            tool_name = event.get("tool_name", "unknown")
            command = event.get("command", "unknown")
            params = event.get("parameters", {})

            # Add a note about what the LLM is doing
            lines.append(f"        Note over LLM: Calling {tool_name}.{command}()")
            lines.append("")

            # Format parameters
            params_str = format_parameters(params)
            if params_str:
                lines.append(f"        LLM->>MemorySystem: {command}(<br/>  {params_str}<br/>)")
            else:
                lines.append(f"        LLM->>MemorySystem: {command}()")
            lines.append("        activate MemorySystem")

        elif event_type == "tool_result":
            tool_name = event.get("tool_name", "unknown")
            command = event.get("command", "unknown")
            success = event.get("success", True)
            error = event.get("error")
            result = event.get("result", "")

            if success:
                # Truncate result for display
                result_preview = truncate_text(result, 40)
                result_preview = escape_diagram_text(result_preview)
                lines.append(f'        MemorySystem-->>LLM: ✓ {result_preview}')
            else:
                error_msg = escape_diagram_text(error or "Error")
                lines.append(f'        MemorySystem-->>LLM: ✗ ERROR<br/>{error_msg}')

            lines.append("        deactivate MemorySystem")
            lines.append("")

        elif event_type == "llm_response":
            content = truncate_text(event.get("content", ""), 50)
            content = escape_diagram_text(content)
            lines.append(f'        LLM-->>HostApp: "{content}"')
            lines.append("        HostApp->>HostApp: messages.append(assistant)")
            lines.append("        HostApp-->>User: Display response")
            lines.append("")

    # End turn block
    lines.append("    end")
    lines.append("")

    return lines


def generate_sequence_diagram(trace_data: Dict[str, Any]) -> str:
    """Generate a Mermaid sequence diagram from trace data."""
    lines = [
        "# Session Trace Sequence Diagram",
        "",
        "## Session Information",
        "",
        f"- **Session ID**: {trace_data.get('session_id', 'N/A')}",
        f"- **Model**: {trace_data.get('model', 'N/A')}",
        f"- **Start Time**: {trace_data.get('start_time', 'N/A')}",
        f"- **End Time**: {trace_data.get('end_time', 'N/A')}",
        "",
        "## Sequence Diagram",
        "",
        "```mermaid",
        "sequenceDiagram",
        "    participant User",
        "    participant HostApp as Host App<br/>(chat.py)",
        "    participant LLM as Claude LLM",
        "    participant MemorySystem as Memory System<br/>(memory_tool)",
        "",
    ]

    # Group events into conversation turns
    events = trace_data.get("events", [])
    turns = group_conversation_turns(events)

    # Generate diagram for each turn
    for turn_number, turn_events in enumerate(turns, start=1):
        turn_lines = generate_diagram_for_turn(turn_number, turn_events)
        lines.extend(turn_lines)

    # Close diagram
    lines.append("```")
    lines.append("")

    # Add summary statistics
    lines.extend([
        "## Summary Statistics",
        "",
    ])

    # Count events by type
    event_counts = {}
    for event in events:
        event_type = event.get("event_type")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    lines.append("### Event Counts")
    lines.append("")
    for event_type, count in sorted(event_counts.items()):
        lines.append(f"- **{event_type}**: {count}")
    lines.append("")

    # Extract token usage from last token_usage event
    token_events = [e for e in events if e.get("event_type") == "token_usage"]
    if token_events:
        last_token_event = token_events[-1]
        cumulative = last_token_event.get("cumulative", {})

        lines.append("### Token Usage (Cumulative)")
        lines.append("")
        lines.append(f"- **Input Tokens**: {cumulative.get('total_input_tokens', 0):,}")
        lines.append(f"- **Output Tokens**: {cumulative.get('total_output_tokens', 0):,}")
        lines.append(f"- **Cache Read Tokens**: {cumulative.get('total_cache_read_tokens', 0):,}")
        lines.append(f"- **Cache Write Tokens**: {cumulative.get('total_cache_write_tokens', 0):,}")
        lines.append("")

    # Count tool calls by command
    tool_calls = [e for e in events if e.get("event_type") == "tool_call"]
    if tool_calls:
        command_counts = {}
        for tool_call in tool_calls:
            command = tool_call.get("command")
            command_counts[command] = command_counts.get(command, 0) + 1

        lines.append("### Memory Tool Commands Used")
        lines.append("")
        for command, count in sorted(command_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- **{command}**: {count}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Mermaid sequence diagrams from session trace files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate diagram and print to stdout
    python scripts/generate_sequence_diagram.py sessions/session_20251109_143414_a1b2c3d4.json

    # Save diagram to file
    python scripts/generate_sequence_diagram.py sessions/session_20251109_143414_a1b2c3d4.json --output diagram.md

    # Process latest session
    python scripts/generate_sequence_diagram.py $(ls -t sessions/*.json | head -1)
        """
    )

    parser.add_argument(
        "trace_file",
        type=str,
        help="Path to the session trace JSON file"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path (default: print to stdout)"
    )

    args = parser.parse_args()

    # Load trace file
    trace_path = Path(args.trace_file)
    if not trace_path.exists():
        print(f"Error: Trace file not found: {trace_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(trace_path, 'r', encoding='utf-8') as f:
            trace_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in trace file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading trace file: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate diagram
    diagram = generate_sequence_diagram(trace_data)

    # Output
    if args.output:
        output_path = Path(args.output)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(diagram)
            print(f"Sequence diagram saved to: {output_path}")
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(diagram)


if __name__ == "__main__":
    main()
