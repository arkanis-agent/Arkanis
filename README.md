# 🤖 Arkanis V3.1 - AI Agent Operating System

Arkanis is a next-generation, multi-agent AI assistant designed for deep research, autonomous execution, and personal automation. Built with a modular kernel and a "Soul" personality engine, it provides a unified interface across Web, CLI, and Telegram.

## 🚀 Key Features

- **Multi-Agent Orchestration**: Specialized agents for planning, execution, and research.
- **Web Intelligence**: Real-time internet access with multi-motor search and browser automation.
- **Soul Engine**: A unique personality layer that makes interactions feel human and proactive.
- **Cross-Platform**: Seamlessly switch between WebUI, Telegram bot, and Terminal.
- **Observability**: Live "System Watch" dashboard for monitoring agent communications.

## 📂 Repository Structure

The project is now organized at the root level for production readiness:

- `api/` - FastAPI server and endpoints.
- `core/` - Core logic, model routing, and task engine.
- `interfaces/` - Web, CLI, and Telegram UI layers.
- `kernel/` - The brain: Planner, Executor, and Agent logic.
- `tools/` - Extensive library of system, network, and AI tools.
- `webui/` - Modern frontend interface.
- `main.py` - The main entry point.

## 🛠️ Installation

Arkanis uses a virtual environment for isolated execution.

### Prerequisites
- Python 3.10+
- Internet connection (for model APIs and search)

### Quick Start
1. Clone the repository.
2. Run the installer:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
3. After installation, launch Arkanis:
   ```bash
   ./run.sh
   ```

## 🎮 Usage

### Launch Options
- **Web UI (Default)**: Just run `./run.sh`. Access at `http://localhost:8000`.
- **CLI Mode**: 
  ```bash
  python3 main.py --cli
  ```
- **Telegram Bot**:
  ```bash
  python3 main.py --telegram
  ```

## 📜 Configuration
Settings are managed via the `.env` file or the WebUI settings panel. Ensure your `OPENROUTER_API_KEY` is configured for full capability.

---
*Built with ❤️ for the Arkanis community.*
