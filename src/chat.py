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


def setup_logging(log_level: str = "INFO", log_file: str|None = None) -> None:
    """Configure logging based on log level and optional file output.

    In DEBUG mode:
    - Show DEBUG logs from our app (src.*, __main__, memory_tool)
    - Show INFO+ from dependencies (anthropic, httpx, etc.)
    - Show detailed memory operations and LLM interactions
    """
    # Convert string level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # Default for all loggers

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Configure handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    )
    handlers.append(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
        )
        handlers.append(file_handler)

    # Add handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)

    # In DEBUG mode, filter dependency logging to reduce noise
    if level == logging.DEBUG:
        # Set DEBUG level for our application loggers only
        logging.getLogger('src').setLevel(logging.DEBUG)
        logging.getLogger('__main__').setLevel(logging.DEBUG)
        logging.getLogger('memory_tool').setLevel(logging.DEBUG)

        # Keep dependencies at INFO level to reduce noise
        logging.getLogger('anthropic').setLevel(logging.INFO)
        logging.getLogger('httpx').setLevel(logging.INFO)
        logging.getLogger('httpcore').setLevel(logging.INFO)
    else:
        # Apply the specified level to our app loggers
        logging.getLogger('src').setLevel(level)
        logging.getLogger('__main__').setLevel(level)
        logging.getLogger('memory_tool').setLevel(level)


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

    # Configure logging from environment
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_TO_FILE")
    setup_logging(log_level, log_file)
    logger = logging.getLogger(__name__)

    # Get model from environment with default to Sonnet 4.5
    model = os.getenv("ANTHROPIC_MODEL", "").strip()
    if not model:
        print("Error: ANTHROPIC_MODEL not found in environment")
        print("Create a .env file with: ANTHROPIC_MODEL=your_desired_model_here")
        sys.exit(1)

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
    logger.info(f"Starting conversation loop with model: {model}")

    # Conversation state
    messages = []
    current_log_level = log_level

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
                # Toggle between DEBUG and the original log level
                if current_log_level == "DEBUG":
                    current_log_level = log_level
                    status = "disabled"
                else:
                    current_log_level = "DEBUG"
                    status = "enabled"
                setup_logging(current_log_level, log_file)
                print(f"\nDebug logging {status}\n")
                continue

            # Add user message to conversation
            messages.append({"role": "user", "content": user_input})

            # Call Claude with memory tool
            # The magic happens here: tool_runner automatically executes memory operations
            logger.debug("="*60)
            logger.debug("SENDING REQUEST TO LLM")
            logger.debug("="*60)
            logger.debug(f"Model: claude-sonnet-4-5-20250929")
            logger.debug(f"System prompt: {system_prompt}")
            logger.debug(f"Messages ({len(messages)} total):")
            for idx, msg in enumerate(messages):
                role = msg['role']
                content = msg['content']
                # Truncate very long messages for readability
                if len(content) > 500:
                    content_preview = content[:500] + f"... ({len(content)} chars total)"
                else:
                    content_preview = content
                logger.debug(f"  [{idx+1}] {role}: {content_preview}")
            logger.debug("="*60)

            runner = client.beta.messages.tool_runner(
                model=model,
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
            logger.error(f"Error in conversation loop: {e}", exc_info=(current_log_level == "DEBUG"))
            print(f"\nError: {str(e)}\n")
            print("Try again or type /quit to exit.\n")


if __name__ == "__main__":
    conversation_loop()
