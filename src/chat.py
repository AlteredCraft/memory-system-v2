#!/usr/bin/env python3
"""
Memory System v2: Companion App for "The Memory Illusion v2"

Demonstrates Claude's autonomous memory management using the Memory Tool.
Unlike v1 with explicit !remember commands, Claude now decides when to save/recall.

Article: https://alteredcraft.com/p/the-memory-illusion-teaching-your
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic
from anthropic.types.beta import BetaMemoryTool20250818ViewCommand

from memory_tool import LocalFilesystemMemoryTool


# Load environment variables
load_dotenv()


def setup_logging(debug: bool = False) -> None:
    """Configure logging based on debug flag."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def print_welcome():
    """Display welcome message and instructions."""
    print("\n" + "="*70)
    print("Memory System v2: Claude with Autonomous Memory")
    print("="*70)
    print("\nClaude now manages its own memory - no !remember commands needed!")
    print("Just chat naturally. Claude will decide what's worth remembering.\n")
    print("Commands:")
    print("  /quit          - Exit the program")
    print("  /memory_view   - View all stored memories")
    print("  /clear         - Clear all memories and start fresh")
    print("  /debug         - Toggle debug logging")
    print("="*70 + "\n")


def conversation_loop():
    """
    Main conversation loop with Claude.

    This is remarkably simple compared to v1:
    - No parsing of !remember commands
    - No manual prompt injection of memory content
    - Just ~20 lines to handle the entire conversation + memory
    """
    # Setup
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in environment")
        print("Create a .env file with: ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    debug = os.getenv("DEBUG", "false").lower() == "true"
    setup_logging(debug)
    logger = logging.getLogger(__name__)

    # Initialize client and memory tool
    client = Anthropic(api_key=api_key)
    memory_tool = LocalFilesystemMemoryTool()

    # System prompt: Guide Claude to manage memory autonomously
    system_prompt = """You are a helpful assistant with persistent memory capabilities.

Key behaviors:
- Autonomously decide what information is worth remembering (names, preferences, project details, etc.)
- Use your memory tool to save important facts without being explicitly asked
- Keep memories organized and up-to-date - remove outdated info, consolidate related facts
- Recall relevant memories when they help provide better responses

You have complete authority over your memory. Manage it wisely."""

    print_welcome()
    logger.info("Starting conversation loop")

    # Conversation state
    messages = []
    debug_mode = debug

    # Track cumulative token usage
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_read_tokens = 0
    total_cache_write_tokens = 0

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input == "/quit":
                print("\nGoodbye!\n")
                break

            elif user_input == "/memory_view":
                print("\n--- Memory Contents ---")
                view_command = BetaMemoryTool20250818ViewCommand(command="view", path="/memories")
                print(memory_tool.view(view_command))
                print("--- End Memory ---\n")
                continue

            elif user_input == "/clear":
                confirm = input("Clear all memories? (yes/no): ").strip().lower()
                if confirm == "yes":
                    result = memory_tool.clear_all_memory()
                    messages = []  # Reset conversation
                    # Reset token counters
                    total_input_tokens = 0
                    total_output_tokens = 0
                    total_cache_read_tokens = 0
                    total_cache_write_tokens = 0
                    print(f"\n{result}\n")
                continue

            elif user_input == "/debug":
                debug_mode = not debug_mode
                setup_logging(debug_mode)
                status = "enabled" if debug_mode else "disabled"
                print(f"\nDebug logging {status}\n")
                continue

            # Add user message to conversation
            messages.append({"role": "user", "content": user_input})

            # Call Claude with memory tool
            # The magic happens here: tool_runner automatically executes memory operations
            logger.debug("Sending request to Claude with memory tool")

            runner = client.beta.messages.tool_runner(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2048,
                system=system_prompt,
                tools=[memory_tool],
                messages=messages,
                betas=["context-management-2025-06-27"]
            )

            # Consume the runner stream to get the final message
            response = runner.until_done()

            # Extract response text
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text = block.text
                    break

            # Display response
            print(f"\nClaude: {response_text}\n")

            # Add assistant response to conversation
            messages.append({"role": "assistant", "content": response_text})

            # Display token usage
            usage = response.usage
            last_input = usage.input_tokens
            last_output = usage.output_tokens
            last_cache_read = getattr(usage, 'cache_read_input_tokens', 0)
            last_cache_write = getattr(usage, 'cache_creation_input_tokens', 0)

            # Update cumulative totals
            total_input_tokens += last_input
            total_output_tokens += last_output
            total_cache_read_tokens += last_cache_read
            total_cache_write_tokens += last_cache_write

            # Log both last request and cumulative totals
            logger.info(
                f"Last Request Tokens - Input: {last_input}, "
                f"Output: {last_output}, "
                f"Cache read: {last_cache_read}, "
                f"Cache write: {last_cache_write}"
            )
            logger.info(
                f"Total Tokens - Input: {total_input_tokens}, "
                f"Output: {total_output_tokens}, "
                f"Cache read: {total_cache_read_tokens}, "
                f"Cache write: {total_cache_write_tokens}"
            )

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type /quit to exit or continue chatting.\n")
            continue

        except Exception as e:
            logger.error(f"Error in conversation loop: {e}", exc_info=debug_mode)
            print(f"\nError: {str(e)}\n")
            print("Try again or type /quit to exit.\n")


if __name__ == "__main__":
    conversation_loop()
