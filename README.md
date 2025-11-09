# Memory System v2

Companion app for the article **"The Memory Illusion v2: From Explicit Commands to Implicit Trust"**

This demonstrates Claude's autonomous memory management using Anthropic's Memory Tool. Unlike v1 where users typed `!remember` commands, Claude now decides what to remember on its own.

**Article:** [The Memory Illusion: Teaching Your LLM to Remember](https://alteredcraft.com/p/the-memory-illusion-teaching-your)
**Original v1 App:** [simple_llm_memory_poc](https://github.com/AlteredCraft/simple_llm_memory_poc)

---

## Quick Start

### 1. Install Dependencies

```bash
# Install dependencies with uv
uv sync

# If you don't have uv installed:
# curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Configure API Key

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your Anthropic API key
# Get your key from: https://console.anthropic.com/settings/keys
```

### 3. Run the App

```bash
uv run src/chat.py
```

---

## What This App Does

**The Key Difference from v1:**

- **v1 (Explicit):** You typed `!remember My name is Alex` → App parsed it → Saved to file
- **v2 (Implicit):** You say "My name is Alex" → Claude decides to remember it → Uses memory tool automatically

Claude now has **authority** to manage its own memory. No command parsing in your code. No manual prompt injection. Just ~20 lines for the entire conversation loop.

---

## How It Works

1. You chat naturally with Claude
2. Claude decides what's worth remembering (names, preferences, project details, etc.)
3. Claude autonomously calls memory tool operations (`create`, `view`, `str_replace`, etc.)
4. Memory persists across conversations in `./memories/` directory

**Example conversation:**

```
You: Hi, I'm Alex. My son Leo turns 5 next Tuesday.

Claude: Hi Alex! Nice to meet you. That's exciting - happy early 5th birthday to Leo!

[Behind the scenes: Claude created /memories/user_profile.txt]
```

Later:
```
You: What gift ideas do you have?

Claude: For Leo's 5th birthday, here are some age-appropriate gift ideas...

[Behind the scenes: Claude recalled the memory about Leo]
```

---

## Available Commands

- `/quit` - Exit the program
- `/memory_view` - View all stored memories (useful for debugging)
- `/clear` - Clear all memories and start fresh
- `/debug` - Toggle debug logging to see memory operations
- `/dump` - Display the current context window (system prompt + conversation history)

---

## Where Memories Are Stored

All memories are saved as plain text files in:
```
./memories/
├── user_profile.txt
├── preferences.txt
└── project_notes.txt
```

Claude creates and organizes these files autonomously. You can inspect them directly - they're just text files!

---

## System Prompt Selection

On startup, you can choose which system prompt to use from a catalog of available prompts in the `prompts/` directory.

**How it works:**
1. When you run the app, it scans `prompts/` for all `.txt` files
2. If multiple prompts are found, you'll see a numbered list:
   ```
   ======================================================================
   Available System Prompts:
   ======================================================================
     1. concise_assistant
     2. system_prompt
     3. verbose_memory_assistant
   ======================================================================

   Select a prompt (1-3):
   ```
3. Choose the prompt that fits your needs
4. If only one prompt exists, it's auto-selected

**Included prompts:**
- `system_prompt.txt` - Default autonomous memory management (balanced)
- `concise_assistant.txt` - Minimal, straightforward assistant
- `verbose_memory_assistant.txt` - Detailed memory management with explanations

You can create your own custom prompts by adding `.txt` files to the `prompts/` directory!

---

## Session Trace

Every conversation is automatically recorded in a detailed session trace file stored in `./sessions/`.

**What's captured:**
- Session metadata (timestamp, model, system prompt)
- All user inputs and assistant responses
- LLM request/response cycles
- Memory tool operations (tool calls and results)
- Token usage statistics (input, output, cache read/write)
- Errors and debugging information

**Trace file format:**
```
./sessions/
└── session_20250109_143022_abc123.json
```

**What you can do with traces:**
- Analyze conversation patterns and memory usage
- Debug unexpected behavior
- Review token consumption over time
- Audit what information was stored in memory
- Reproduce issues by examining the exact sequence of events

Session traces are finalized when you `/quit` or `/clear`, and the file path is displayed in the console.

### Generating Sequence Diagrams from Traces

You can visualize your session traces as Mermaid sequence diagrams using the included script:

```bash
# Generate diagram for a specific trace file
python scripts/generate_sequence_diagram.py sessions/session_20251109_143414_abc123.json

# Save diagram to a file
python scripts/generate_sequence_diagram.py sessions/session_20251109_143414_abc123.json --output my_diagram.md

# Process the most recent session
python scripts/generate_sequence_diagram.py $(ls -t sessions/*.json | head -1)
```

The generated diagram includes:
- Visual representation of User ↔ Host App ↔ LLM ↔ Memory System interactions
- All tool calls and their results
- User inputs and LLM responses
- Summary statistics (event counts, token usage, tool command usage)

The output is in Mermaid format and can be viewed in:
- GitHub/GitLab markdown files (automatic rendering)
- VS Code with Mermaid extensions
- Online tools like [mermaid.live](https://mermaid.live/)

---

## The Teaching Point

Compare the code complexity:

**v1 (Explicit - Manual Control):**
```python
if user_input.startswith("!remember"):
    fact = user_input.split("!remember", 1)[1].strip()
    with open(memory_file, "a") as f:
        f.write(f"\n- {fact}")
    return "OK, I'll remember that."

# Manual prompt injection
system_prompt = f"Memories:\n{read_memory(memory_file)}\n..."
```

**v2 (Implicit - Claude Controls):**
```python
response = client.beta.messages.tool_runner(
    model="claude-sonnet-4-5-20250929",
    tools=[memory_tool],  # Just provide the tool
    messages=messages
)
```

The shift from v1 to v2 is about **authority**. We've moved from micromanaging the LLM to trusting it with autonomy.

---

## Technical Details

**Package Manager:** [uv](https://docs.astral.sh/uv/) (fast Python package installer)
**Model:** `claude-sonnet-4-5-20250929` (latest Sonnet with memory support)
**SDK:** Anthropic Python SDK (`anthropic>=0.40.0`)
**Memory Backend:** Local filesystem (files in `./memories/`)
**Memory Operations:** `view`, `create`, `str_replace`, `insert`, `delete`, `rename`
**Session Tracking:** JSON trace files in `./sessions/` (implemented in `src/session_trace.py`)

For production deployments with security considerations (path validation, rate limiting, etc.), see:
📚 [Anthropic Memory Tool Documentation](https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool)

---

## Troubleshooting

**Import errors or "anthropic.types.beta" could not be resolved**
- Make sure you've run `uv sync` to install dependencies
- The error will disappear once dependencies are installed

**"ANTHROPIC_API_KEY not found"**
- Make sure you created `.env` file (copy from `.env.example`)
- Add your API key from https://console.anthropic.com/settings/keys

**Don't have uv installed?**
- Install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Or use pip: `pip install -r requirements.txt` (traditional method)

**Want to see what's happening under the hood?**
- Type `/debug` to enable detailed logging
- Type `/memory_view` to inspect current memories
- Type `/dump` to see the exact context being sent to Claude (system prompt + all messages)

**Claude isn't remembering things**
- Try being more explicit: "Remember that I prefer Python over JavaScript"
- Check `/memory_view` to see what's actually stored
- Enable debug mode to see memory tool operations

**Start over fresh**
- Type `/clear` to delete all memories
- Or manually delete the `./memories/` directory

---

## Learn More

- **Article:** [The Memory Illusion v2](https://alteredcraft.com/p/the-memory-illusion-teaching-your)
- **Anthropic Docs:** [Memory Tool](https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool)
- **Claude Agent SDK:** [Overview](https://docs.claude.com/en/api/agent-sdk/overview)
- **Original v1 Implementation:** [simple_llm_memory_poc](https://github.com/AlteredCraft/simple_llm_memory_poc)

---

## License

MIT