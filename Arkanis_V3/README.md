# ARKANIS V3.1 — AI Agent Operating System

ARKANIS is an autonomous AI agent system that runs locally or via cloud APIs. It thinks, plans, executes actions with real tools, and evaluates its own results — all without human supervision.

---

## Key Features

- **Autonomous agents** — Plan → Execute → Self-critique loop (up to 5 cycles per objective)
- **Real execution** — File I/O, HTTP requests, browser automation (Playwright), Speech-to-Text (whisper.cpp)
- **Multi-provider LLM** — Ollama (local), OpenRouter, OpenAI, Anthropic, Mistral, Gemini, and more
- **Agent Bus** — Multi-agent communication for collaborative task execution
- **Long-term memory** — Persistent facts, preferences, and recurring tasks
- **Goal Manager** — Track and update complex multi-step objectives
- **CLI control** — Full terminal interface with `arkanis` command
- **Web UI** — Browser-based dashboard for real-time monitoring and configuration

---

## Installation

### Requirements

- Python 3.10+
- `git`, `make`, `cmake`, `g++` (for Speech-to-Text)
- `ffmpeg` (for audio processing)
- [Ollama](https://ollama.com) (for local LLM — installed automatically if RAM ≥ 8 GB)

### One-command setup

```bash
git clone https://github.com/arkanis-agent/arkanis.git
cd arkanis
sudo bash install.sh
```

The installer will:
1. Detect your hardware (RAM, GPU, disk)
2. Install and configure Ollama automatically (if capable)
3. Pull the recommended local model
4. Generate your `.env` configuration
5. Register the `arkanis` command globally
6. Launch the onboarding Web UI

---

## Configuration

Copy the environment template and edit as needed:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `ARKANIS_MODE` | `local` (Ollama) or `api` (cloud) |
| `ARKANIS_MODEL` | Default model ID |
| `OPENROUTER_API_KEY` | OpenRouter API key (api mode only) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (optional) |

Provider API keys can also be configured via the Web UI at `http://localhost:8000`.

---

## Usage

### CLI

```bash
arkanis start        # Start in CLI mode
arkanis start --web  # Start the Web UI at http://localhost:8000
arkanis doctor       # Run system diagnostics
arkanis logs         # Show recent logs
```

Or run directly:

```bash
python main.py            # CLI mode
python main.py --web      # Web mode
python main.py --telegram # Telegram bot mode
```

### CLI commands (inside the agent)

| Command | Action |
|---|---|
| `auto: <goal>` | Start autonomous mode for a complex objective |
| `status` | Show current agent status |
| `pause` / `resume` | Pause or resume auto mode |
| `stop` | Stop current task |
| `help` | List available tools |

---

## Speech-to-Text (Optional)

Install the local whisper.cpp engine for audio transcription:

```bash
bash scripts/install_whisper.sh
```

Requires: `git`, `cmake`, `make`, `g++`, `ffmpeg`

---

## Web UI Onboarding

After starting with `--web`, open `http://localhost:8000` in your browser.

The onboarding wizard guides you through:
1. Choosing your LLM provider (local Ollama or cloud API)
2. Entering API keys
3. Selecting a default model
4. Enabling integrations (Telegram, Supabase, Tavily)

---

## Architecture

```
arkanis/
├── main.py              # Entry point
├── install.sh           # One-command installer
├── kernel/              # Core agent logic
│   ├── agent.py         # Main agent orchestrator
│   ├── planner.py       # LLM-powered planning
│   ├── executor.py      # Tool execution with result piping
│   └── critic.py        # Self-evaluation layer
├── core/                # Infrastructure
│   ├── llm_router.py    # Multi-provider LLM abstraction
│   ├── config_manager.py
│   ├── agent_bus.py     # Multi-agent communication
│   └── goal_manager.py  # Objective tracking
├── tools/               # Executable capabilities
│   ├── system_tools.py  # File I/O, memory, messaging
│   ├── network_tools.py # HTTP, URL fetching
│   ├── browser_tools.py # Playwright browser automation
│   └── audio_tools.py   # Speech-to-text via whisper.cpp
├── modules/memory/      # Short and long-term memory
├── interfaces/          # CLI and Telegram interfaces
├── api/                 # FastAPI REST server
├── webui/               # Browser dashboard
└── scripts/             # Installer helpers
```

---

## License

MIT
