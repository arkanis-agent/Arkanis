import os
import sys
import anyio
import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from api.terminal_manager import TerminalManager

# Load .env before any module imports so singletons (router, config_manager) pick up env vars
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r") as _f:
        for _line in _f:
            if _line.strip() and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.strip().split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Ensure the kernel is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kernel.agent import ArkanisAgent
from core.llm_router import router
from core.config_manager import config_manager
from core.task_engine import task_engine
from core.agent_bus import agent_bus
from core.watcher import watcher as arkanis_watcher
from core.goal_manager import goal_manager
from core.goal_planner import goal_planner
from core.cost_governor import governor
from interfaces.telegram import TelegramInterface
import threading
from pydantic import BaseModel
import requests

import asyncio
import concurrent.futures

logger = logging.getLogger("uvicorn")
app = FastAPI(title="ARKANIS V3 API")

# Dedicated executor for long-running agent tasks.
# This prevents blocking Uvicorn's internal threadpool that handles polling.
_agent_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="arkanis-agent"
)

import functools

async def run_agent(fn, *args, timeout: float = 120.0, **kwargs):
    """Run a blocking agent function in the dedicated executor with a timeout."""
    loop = asyncio.get_event_loop()
    # Use partial to pass both *args and **kwargs to the executor
    func = functools.partial(fn, *args, **kwargs)
    future = loop.run_in_executor(_agent_executor, func)
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Agent task timed out after {timeout}s")
        raise HTTPException(status_code=504, detail="O agente demorou demais para responder. Tente novamente.")

@app.middleware("http")
async def add_cache_control_headers(request, call_next):
    """Ensure the browser never caches outdated Arkanis UI components."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Managed singleton for the core ArkanisAgent
agent: ArkanisAgent = ArkanisAgent()

class MessageRequest(BaseModel):
    text: str
    images: Optional[List[str]] = None
    files: Optional[List[Dict[str, str]]] = None

class ModelSelectRequest(BaseModel):
    model_id: str

class ControlRequest(BaseModel):
    command: str

class ProviderConfigRequest(BaseModel):
    config: Dict[str, Any]

class IntegrationsConfigRequest(BaseModel):
    config: Dict[str, Any]

class TestProviderRequest(BaseModel):
    provider_id: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None

class AgentStatusResponse(BaseModel):
    mode: str
    status: str
    current_cycle: int
    goal: str | None
    active_model: str
    auto_strategy: bool
    active_tier: Optional[str] = None

class GoalUpdateData(BaseModel):
    goal_id: str
    status: str

class SuggestionActionRequest(BaseModel):
    action: str


class StrategyToggleRequest(BaseModel):
    enabled: bool

class CreateAgentRequest(BaseModel):
    agent_id: str
    role: str
    persona: str = ""
    allowed_tools: list = []

# =========================================================================
#  AGENT CONTROL CENTER ENDPOINTS
# =========================================================================

@app.get("/agents")
async def list_agents():
    """List all agents with full state for the Control Center."""
    data = agent_bus.get_observability_data()
    return data

@app.post("/agents/create")
async def create_agent(request: CreateAgentRequest):
    """Create a new custom agent with a specific role and toolset."""
    from core.custom_agent import CustomAgent
    try:
        new_agent = CustomAgent.create(
            agent_id=request.agent_id,
            role=request.role,
            persona=request.persona,
            allowed_tools=request.allowed_tools,
        )
        return {"status": "success", "agent": new_agent.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/{agent_id}/pause")
async def pause_agent(agent_id: str):
    """Pause a running agent."""
    success = agent_bus.pause_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado ou não suporta pause.")
    return {"status": "paused", "agent_id": agent_id}

@app.post("/agents/{agent_id}/resume")
async def resume_agent(agent_id: str):
    """Resume a paused agent.""" 
    success = agent_bus.resume_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado.")
    return {"status": "resumed", "agent_id": agent_id}

@app.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Stop and remove a custom agent, or reset a core agent."""
    success = agent_bus.stop_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado.")
    return {"status": "stopped", "agent_id": agent_id}

@app.get("/agents/{agent_id}/logs")
async def get_agent_logs(agent_id: str):
    """Get full log history for a specific agent."""
    detail = agent_bus.get_agent_detail(agent_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' não encontrado.")
    agent_instance = agent_bus.get_agent(agent_id)
    full_logs = getattr(agent_instance, "logs", []) if agent_instance else []
    return {"agent_id": agent_id, "logs": full_logs}

@app.get("/tools/available")
async def list_available_tools():
    """List all registered tools for agent creation UI."""
    from tools.registry import registry as tool_registry
    tools = tool_registry.list_tools()
    return {"tools": [{"name": k, "description": v} for k, v in tools.items()]}


@app.get("/models")
async def get_models():
    """List available local and cloud models."""
    return router.get_models()

@app.get("/models/openrouter/fetch")
async def fetch_openrouter_models():
    """Fetch and return free+paid models from OpenRouter API."""
    cfg = config_manager.load_config()
    api_key = cfg.get("providers", {}).get("openrouter", {}).get("api_key", "") or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured.")
    try:
        r = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        r.raise_for_status()
        all_models = r.json().get("data", [])

        def has_endpoint(m):
            # Only include models that have at least one active provider (top_provider set)
            return bool(m.get("top_provider") or m.get("per_request_limits"))

        def fmt_cost(m):
            """Return cost per 1M prompt tokens as formatted string, or None if free."""
            try:
                p = float(m.get("pricing", {}).get("prompt", "0") or "0")
                if p == 0:
                    return None
                per_m = p * 1_000_000
                return f"{per_m:.2f}/1M" if per_m >= 0.01 else f"{per_m:.4f}/1M"
            except Exception:
                return None

        free = [
            {"id": m["id"], "name": m.get("name", m["id"]),
             "context": m.get("context_length", 0), "cost": None}
            for m in all_models
            if ":free" in m.get("id", "") and has_endpoint(m)
        ]
        paid = [
            {"id": m["id"], "name": m.get("name", m["id"]),
             "context": m.get("context_length", 0), "cost": fmt_cost(m)}
            for m in all_models
            if ":free" not in m.get("id", "") and m.get("id") and has_endpoint(m)
        ]
        return {"free": free[:80], "paid": paid[:80]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/model/select")
async def select_model(request: ModelSelectRequest):
    """Switch the active LLM model."""
    success = router.set_model(request.model_id)
    if not success:
        raise HTTPException(status_code=400, detail="Modelo inválido.")
    return {"status": "success", "active_model": router.active_model}

@app.get("/chat/history")
async def get_chat_history():
    """Returns the chronological conversation history to rebuild the UI after a page refresh."""
    from modules.memory.short_term import session_memory
    history = []
    for inter in session_memory.interactions:
        history.append({
            "user": inter.get("user_input", ""),
            "agent": inter.get("result", "")
        })
    return {"history": history}

@app.get("/memory/long-term")
async def get_long_term_memory():
    """Returns the persistent neural memory vault data."""
    from modules.memory.long_term import long_term_memory
    return {"memory": long_term_memory.data}

@app.post("/memory/update")
async def update_long_term_memory(request: Request):
    """Updates a specific memory entry."""
    from modules.memory.long_term import long_term_memory
    try:
        body = await request.json()
        category = body.get("category")
        index = body.get("index")
        content = body.get("content")
        
        if success := long_term_memory.update_memory(category, index, content):
            return {"status": "success"}
        raise HTTPException(status_code=400, detail="Failed to update memory.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/delete")
async def delete_long_term_memory(request: Request):
    """Deletes a specific memory entry."""
    from modules.memory.long_term import long_term_memory
    try:
        body = await request.json()
        category = body.get("category")
        index = body.get("index")
        
        if success := long_term_memory.delete_memory(category, index):
            return {"status": "success"}
        raise HTTPException(status_code=400, detail="Failed to delete memory.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/strategy/toggle")
async def toggle_strategy(request: StrategyToggleRequest):
    """Enable or disable Auto Model Strategy."""
    router.set_auto_strategy(request.enabled)
    return {"status": "success", "auto_strategy": router.auto_strategy}

@app.post("/message")
async def handle_message(request: MessageRequest):
    """Router for messages to the agent."""
    try:
        # Clear logs before a new major request to keep the feed fresh
        if not request.text.startswith("status"):
            agent.logs = []
            
        # Run in dedicated agent executor — never blocks uvicorn polling threads
        # Propagate text, images and universal file attachments
        response = await run_agent(agent.handle_input, request.text, images=request.images, files=request.files)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice_message")
async def handle_voice_message(request: Request):
    """Transcribes an uploaded raw audio body and processes it as an agent command."""
    import uuid
    import json
    from tools.registry import registry
    
    # 1. Save raw body to temp
    # Browsers typically send webm from MediaRecorder
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp_path = os.path.join(app_root, "data", f"web_voice_{uuid.uuid4().hex[:8]}.webm")
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    
    try:
        content = await request.body()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio content.")
            
        with open(tmp_path, "wb") as f:
            f.write(content)
        
        # 2. Transcribe via Tool
        stt_tool = registry.get_tool("speech_to_text")
        if not stt_tool:
            raise HTTPException(status_code=500, detail="STT Tool not registered.")
        
        # stt_tool.execute_async returns a JSON string or dict
        stt_result_raw = await stt_tool.execute_async(temp_input=tmp_path)
        
        if isinstance(stt_result_raw, str):
            try:
                stt_result = json.loads(stt_result_raw)
            except:
                stt_result = {"text": stt_result_raw, "status": "success"}
        else:
            stt_result = stt_result_raw

        text = stt_result.get("text", "")
        if not text:
            # Check if it was just silence caught by VAD
            if stt_result.get("status") == "success":
                return {"response": "Não detectei fala no áudio.", "transcription": ""}
            return {"response": "Não consegui entender o áudio.", "transcription": ""}
        
        # 3. Process text via Agent (in dedicated executor, 120s timeout)
        agent.logs = []
        response = await run_agent(agent.handle_input, text)
        
        return {
            "response": response,
            "transcription": text,
            "metrics": stt_result.get("metrics", {})
        }
        
    except Exception as e:
        logger.error(f"Error in handle_voice_message: {str(e)}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass

@app.get("/status", response_model=AgentStatusResponse)
async def get_status():
    """Poll the agent's current state."""
    return {
        "mode": agent.mode,
        "status": agent.status,
        "current_cycle": agent.current_cycle,
        "goal": agent.goal,
        "active_model": router.active_model,
        "auto_strategy": router.auto_strategy,
        "active_tier": getattr(router, "active_tier", None)
    }

@app.get("/logs")
async def get_logs(since: int = 0):
    """Fetch logs starting from index 'since'."""
    return {"logs": agent.logs[since:]}

@app.post("/control")
async def handle_control(request: ControlRequest):
    """Handle Pause, Resume, Stop commands."""
    try:
        response = agent.handle_input(request.command)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/providers")
async def get_providers():
    """Retrieve current providers configuration."""
    return config_manager.load_config()

@app.post("/providers/update")
async def update_providers(request: ProviderConfigRequest):
    """Update and persist providers configuration."""
    success = config_manager.save_config(request.config)
    if not success:
        raise HTTPException(status_code=500, detail="Erro ao salvar configuração.")
    # Reload router config
    router._load_config()
    return {"status": "success"}

@app.post("/providers/test")
async def test_provider(request: TestProviderRequest):
    """Test connection to a provider with a minimal request."""
    # This is a simplified test. In a real scenario, we'd send a real minimal request.
    # For now, we'll try a HEAD or simple GET if it's an HTTP endpoint, 
    # or a dummy model list request.
    
    url = request.endpoint
    headers = {}
    if request.api_key:
        headers["Authorization"] = f"Bearer {request.api_key}"
        
    try:
        # Generic test: try to reach the endpoint or a known sub-path
        # For Ollama: /api/tags
        # For OpenAI/OpenRouter: /v1/models
        test_url = url
        if "openrouter" in url or "openai" in url or "/v1" in url:
            if not url.endswith("/models"):
                test_url = url.replace("/chat/completions", "/models")
        
        response = requests.get(test_url, headers=headers, timeout=5)
        if response.status_code == 200:
            return {"status": "connected"}
        else:
            return {"status": "error", "detail": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/integrations")
async def get_integrations():
    """Returns the current integrations configuration."""
    return config_manager.load_integrations()

@app.post("/integrations/update")
async def update_integrations(request: IntegrationsConfigRequest):
    """Updates the integrations configuration."""
    if not config_manager.save_integrations(request.config):
        raise HTTPException(status_code=500, detail="Erro ao salvar integrações.")
    return {"status": "success"}

class StartTaskRequest(BaseModel):
    description: str
    type: str # "interval", "condition"
    interval: int = 300
    condition: Optional[str] = ""
    goal_id: Optional[str] = None

class StopTaskRequest(BaseModel):
    task_id: str

class CreateGoalRequest(BaseModel):
    description: str
    priority: str = "medium"

class UpdateGoalRequest(BaseModel):
    goal_id: str
    status: Optional[str] = None
    progress: Optional[int] = None
    note: str = ""

@app.get("/tasks")
async def get_tasks():
    """List all continuous tasks."""
    return {"tasks": task_engine.list_tasks()}

@app.post("/tasks/start")
async def start_task(request: StartTaskRequest):
    """Start a new continuous task."""
    task = task_engine.start_task(
        request.description, 
        request.type, 
        request.interval, 
        request.condition,
        request.goal_id
    )
    return {"status": "success", "task_id": task.id}

@app.post("/tasks/stop")
async def stop_task(request: StopTaskRequest):
    """Stop a continuous task."""
    success = task_engine.stop_task(request.task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return {"status": "success"}



# --- Governor Endpoints ---
@app.get("/governor/state")
def api_get_governor_state():
    return governor.get_state()

@app.get("/bus/logs")
async def get_bus_logs():
    """Get the latest agent communication logs."""
    return {"messages": agent_bus.message_history}

@app.get("/observability")
async def get_system_observability():
    """Get full system monitoring data (agents + stats + history)."""
    return agent_bus.get_observability_data()

@app.get("/goals")
async def get_goals():
    """List all active and past global goals."""
    return {"goals": goal_manager.list_goals()}

@app.post("/goals/create")
async def create_goal(request: CreateGoalRequest):
    g = goal_manager.create_goal(request.description, request.priority)
    return {"status": "success", "goal_id": g.id}

@app.post("/goals/update")
async def update_goal(request: UpdateGoalRequest):
    if request.status:
        goal_manager.update_status(request.goal_id, request.status)
    if request.progress is not None:
        goal_manager.update_progress(request.goal_id, request.progress, request.note)
    return {"status": "success"}

class OnboardingFinalizeRequest(BaseModel):
    telegram_token: Optional[str] = None
    model_id: Optional[str] = None

@app.get("/onboarding/status")
async def get_onboarding_status():
    """Check if the initial setup is complete."""
    setup_complete = os.getenv("SETUP_COMPLETE", "false").lower() == "true"
    return {"setup_complete": setup_complete}

@app.post("/onboarding/finalize")
async def finalize_onboarding(request: OnboardingFinalizeRequest):
    """Finalizes onboarding by saving configuration to .env."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            env_lines = f.readlines()
            
    # Maintain existing keys but update specific ones
    updated_keys = {"SETUP_COMPLETE": "true"}
    if request.telegram_token:
        updated_keys["TELEGRAM_BOT_TOKEN"] = request.telegram_token
    if request.model_id:
        updated_keys["ARKANIS_MODEL"] = request.model_id
        
    new_lines = []
    found_keys = set()
    for line in env_lines:
        if "=" in line:
            k = line.split("=")[0].strip()
            if k in updated_keys:
                new_lines.append(f"{k}={updated_keys[k]}\n")
                found_keys.add(k)
                continue
        new_lines.append(line)
        
    for k, v in updated_keys.items():
        if k not in found_keys:
            new_lines.append(f"{k}={v}\n")
            
    with open(env_path, "w") as f:
        f.writelines(new_lines)

@app.get("/system/metrics")
async def get_system_metrics():
    """Fetch real-time metrics for the System Watch panel."""
    from tools.registry import registry
    tool = registry.get_tool("system_monitor")
    if tool:
        # Get detailed metrics
        return tool.execute(detailed=True)
    return {"status": "degraded", "error": "System Monitor Tool not found."}
        
    # Update runtime env
    for k, v in updated_keys.items():
        os.environ[k] = v
        
    return {"status": "success"}

@app.get("/system/logs")
async def get_system_logs(lines: int = 50):
    """Returns the last N lines of the human-readable system log."""
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "arkanis.log")
    try:
        if not os.path.exists(log_path):
            return {"logs": ["Arquivo de log ainda não criado."]}
            
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            # Return last N lines, stripped
            return {"logs": [l.strip() for l in all_lines[-lines:]]}
    except Exception as e:
        return {"logs": [f"Erro ao ler logs: {str(e)}"]}

@app.get("/system/timeline")
async def get_auto_heal_timeline():
    """Returns a list of all suggestions that have been 'applied'."""
    try:
        # Check both potential agents
        agent_instance = agent_bus.get_agent("architect_agent") or agent_bus.get_agent("dev_agent")
        if not agent_instance:
             return {"timeline": []}
             
        all_suggestions = agent_instance.get_suggestions()
        timeline = [s for s in all_suggestions if s.get("status") == "applied"]
        return {"timeline": timeline}
    except Exception as e:
        logger.error(f"Erro ao carregar timeline: {e}")
        return {"timeline": []}

# --- System Management Endpoints ---

@app.post("/system/stop")
async def stop_system():
    """Immediately terminates the Arkanis process."""
    logger.warning("System shutdown initiated via WebUI.")
    # Delayed exit to allow response to return
    def shutdown():
        import time
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=shutdown).start()
    return {"status": "stopping", "message": "Arkanis encerrando em 1 segundo..."}

@app.post("/system/restart")
async def restart_system():
    """Restart the Arkanis process."""
    logger.warning("System restart initiated via WebUI.")
    def restart():
        import time
        import sys
        time.sleep(1)
        os.execv(sys.executable, ['python3'] + sys.argv)
    threading.Thread(target=restart).start()
    return {"status": "restarting", "message": "Arkanis reiniciando..."}

@app.get("/system/doctor")
async def system_doctor():
    """Perform a health check on the system components."""
    from tools.registry import registry
    report = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "kernel": "online",
            "voice_engine": "online" if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "libs", "whisper.cpp", "build", "bin", "whisper-cli")) else "offline",
            "memory_vault": "online" if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "long_term_memory.json")) else "degraded",
            "tools_registered": len(registry.list_tools())
        }
    }
    return report

@app.get("/history/timeline")
async def get_history_timeline():
    """Retrieve the event history for the HUD timeline."""
    agent_instance = agent_bus.get_agent("dev_agent") or agent_bus.get_agent("architect_agent")
    if not agent_instance:
        return {"timeline": []}
         
    all_suggestions = agent_instance.get_suggestions()
    timeline = [s for s in all_suggestions if s.get("status") == "applied"]
    return {"timeline": timeline}

@app.get("/suggestions")
async def get_suggestions(filter: str = "pending"):
    """Fetch system improvements with stats."""
    agent_instance = agent_bus.get_agent("dev_agent") or agent_bus.get_agent("architect_agent")
    if not agent_instance:
        return {"suggestions": [], "stats": {"pending": 0, "applied": 0, "rejected": 0, "total": 0}}
        
    suggestions = agent_instance.get_suggestions()
    
    # Calculate stats
    stats = {
        "pending": len([s for s in suggestions if s.get("status") == "pending"]),
        "applied": len([s for s in suggestions if s.get("status") == "applied"]),
        "rejected": len([s for s in suggestions if s.get("status") == "rejected"]),
        "total": len(suggestions)
    }
    
    # Filter
    filtered = [s for s in suggestions if s.get("status") == filter]
    return {"suggestions": filtered, "stats": stats}

@app.get("/logs/evolution")
async def get_evolution_logs():
    """Read the last 100 lines of the evolution log."""
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "evolution.log")
    if not os.path.exists(log_path):
        return {"content": "Nenhum log de evolução encontrado ainda."}
    
    with open(log_path, "r") as f:
        lines = f.readlines()
        content = "".join(lines[-100:])
    return {"content": content}

@app.post("/config/evolution")
async def update_evolution_config(config: Dict[str, Any]):
    """Update evolution cycle configuration."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "evolution.json")
    
    # Load current
    current = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            current = json.load(f)
            
    # Update
    current.update(config)
    
    # Persist
    with open(config_path, "w") as f:
        json.dump(current, f, indent=4)
        
    logger.info(f"Evolution config updated: {current}")
    return {"status": "success", "config": current}

def start_evolution_worker():
    """Background worker that periodically triggers autonomous evolution."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "evolution.json")
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "autonomous_evolution.py")
    
    def worker_loop():
        import json
        import subprocess
        import time
        
        while True:
            try:
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        conf = json.load(f)
                    
                    if conf.get("enabled"):
                        interval = conf.get("interval_seconds", 1800)
                        limit = conf.get("limit_per_cycle", 3)
                        
                        logger.info(f"Worker: Starting autonomous evolution cycle (limit={limit})...")
                        # Run the script as a subprocess to ensure it's isolated
                        subprocess.run([sys.executable, script_path, "--limit", str(limit)], check=False)
                        
                        logger.info(f"Worker: Cycle complete. Sleeping for {interval}s")
                        time.sleep(interval)
                    else:
                        time.sleep(60) # Check config again in a minute
                else:
                    time.sleep(60)
            except Exception as e:
                logger.error(f"Evolution Worker Error: {e}")
                time.sleep(300) # Wait 5m on error
                
    threading.Thread(target=worker_loop, daemon=True, name="ArkanisEvolution").start()

# Start the worker on app start
@app.on_event("startup")
async def startup_event():
    logger.info("ARKANIS V3: System starting up...")
    start_evolution_worker()


# --- Multi-Channel Background Services ---
def start_telegram():
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        try:
            if agent:
                tg = TelegramInterface(agent)
                agent.log("Telegram Background Service Online.", "system")
                tg.start_loop()
        except Exception as e:
            agent.log(f"Failed to start Telegram service: {e}", "error")

@app.on_event("startup")
async def startup_event():
    # Start Telegram in a daemon thread ONLY if explicitly enabled to prevent conflicts with main.py --telegram
    if os.environ.get("AUTOSTART_TELEGRAM", "false").lower() == "true":
        threading.Thread(target=start_telegram, daemon=True).start()
    else:
        logger.info("Nerve: Telegram daemon thread desativado por padrão (use AUTOSTART_TELEGRAM=true para ligar no server).")
    
    # ARKANIS V4 ALPHA: Start the Visual Nervous System (Watcher)
    arkanis_watcher.start()

@app.get("/suggestions")
async def get_dev_suggestions():
    """Retrieve all suggestions generated by the DevAgent."""
    agent_instance = agent_bus.get_agent("dev_agent")
    if not agent_instance:
        return {"suggestions": []}
    return {"suggestions": agent_instance.get_suggestions()}

@app.post("/suggestions/{sug_id}/action")
async def handle_suggestion_action(sug_id: str, req: SuggestionActionRequest):
    """Approve or reject a suggestion. If approved, applies the code changes."""
    action = req.action
    # Find in either dev_agent or architect_agent (they share the file)
    agent_instance = agent_bus.get_agent("architect_agent") or agent_bus.get_agent("dev_agent")
    
    if not agent_instance:
        raise HTTPException(status_code=404, detail="Nenhum agente de desenvolvimento ativo.")
    
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Ação inválida. Use 'approve' ou 'reject'.")
    
    # 1. Update status in JSON
    final_status = "approved" if action == "approve" else "rejected"
    agent_instance.update_suggestion_status(sug_id, final_status)
    
    # 2. If approved, APPLY the code
    if action == "approve":
        suggestions = agent_instance.get_suggestions()
        target = next((s for s in suggestions if s["id"] == sug_id), None)
        if target and target.get("proposed_code") and target.get("file_path"):
            from tools.registry import registry
            tool = registry.get_tool("write_full_file")
            if tool:
                result = tool.execute(path=target["file_path"], content=target["proposed_code"])
                logger.info(f"Suggestion {sug_id} applied: {result}")
                # Optional: update status to 'applied'
                agent_instance.update_suggestion_status(sug_id, "applied")
    
    return {"status": "success", "suggestion_id": sug_id, "new_status": action}


@app.websocket("/terminal/ws")
async def terminal_websocket(websocket: WebSocket):
    """
    ARKANIS NERVE: Interactive Pseudo-Terminal Bridge.
    Syncs the WebUI Xterm.js with the local bash shell.
    """
    logger.info("Nerve: Incoming terminal WebSocket connection...")
    await websocket.accept()
    logger.info("Nerve: Terminal WebSocket accepted.")
    
    # Callback to send terminal output to front-end
    async def send_to_frontend(data: bytes):
        try:
            # We must use anyio/base-task to handle sending from background thread
            text = data.decode("utf-8", errors="replace")
            await websocket.send_text(text)
        except Exception:
            pass

    # Wrap the async send for the sync manager
    import asyncio
    loop = asyncio.get_event_loop()
    def sync_send(data):
        asyncio.run_coroutine_threadsafe(websocket.send_text(data.decode("utf-8", errors="replace")), loop)

    terminal = TerminalManager(on_output=sync_send)
    terminal.start()
    
    try:
        while True:
            # Wait for data from frontend
            data = await websocket.receive_text()
            try:
                import json
                msg = json.loads(data)
                if msg.get("type") == "input":
                    terminal.write(msg["data"])
                elif msg.get("type") == "resize":
                    terminal.resize(msg["rows"], msg["cols"])
            except:
                # If not JSON, it's raw input
                terminal.write(data)
    except WebSocketDisconnect:
        logger.info("Nerve: Terminal WebSocket disconnected.")
    finally:
        terminal.stop()

webui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webui")
if os.path.exists(webui_path):
    app.mount("/", StaticFiles(directory=webui_path, html=True), name="webui")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
