import os
import sys
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File

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
from core.goal_manager import goal_manager
from core.goal_planner import goal_planner
from core.cost_governor import governor
from pydantic import BaseModel
import requests

app = FastAPI(title="ARKANIS V3 API")

@app.middleware("http")
async def add_cache_control_headers(request, call_next):
    """Ensure the browser never caches outdated Arkanis UI components."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Shared agent instance
agent = ArkanisAgent()

class MessageRequest(BaseModel):
    text: str

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


class StrategyToggleRequest(BaseModel):
    enabled: bool


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

@app.post("/strategy/toggle")
async def toggle_strategy(request: StrategyToggleRequest):
    """Enable or disable Auto Model Strategy."""
    router.set_auto_strategy(request.enabled)
    return {"status": "success", "auto_strategy": router.auto_strategy}

@app.post("/message")
async def handle_message(request: MessageRequest):
    # ... (remains the same)
    """Router for messages to the agent."""
    try:
        # Clear logs before a new major request to keep the feed fresh
        if not request.text.startswith("status"):
            agent.logs = []
            
        response = agent.handle_input(request.text)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice_message")
async def handle_voice_message(file: UploadFile = File(...)):
    """Transcribes an uploaded audio file and processes it as an agent command."""
    import uuid
    import json
    from tools.registry import registry
    
    # 1. Save uploaded file to temp
    ext = file.filename.split(".")[-1] if "." in file.filename else "ogg"
    tmp_path = os.path.join("V3", "data", f"web_voice_{uuid.uuid4().hex[:8]}.{ext}")
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    
    try:
        with open(tmp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 2. Transcribe via Tool (now using the async variant)
        stt_tool = registry.get_tool("speech_to_text")
        if not stt_tool:
            raise HTTPException(status_code=500, detail="STT Tool not registered.")
        
        # Use execute_async to prevent blocking the worker thread
        result_json = await stt_tool.execute_async(audio_path=tmp_path)
        res = json.loads(result_json)
        
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
        if "error" in res:
            raise HTTPException(status_code=500, detail=res["error"])
        
        text = res.get("text", "")
        if not text:
            # Check if it was just silence caught by VAD
            if res.get("status") == "success":
                return {"response": "Não detectei fala no áudio.", "transcription": ""}
            return {"response": "Não consegui entender o áudio.", "transcription": ""}
        
        # 3. Process text via Agent
        agent.logs = []
        # handle_input is still sync, but we already unblocked the STT part
        response = agent.handle_input(text)
        
        return {
            "response": response,
            "transcription": text,
            "metrics": res.get("metrics", {})
        }
        
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))

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
        
    # Update runtime env
    for k, v in updated_keys.items():
        os.environ[k] = v
        
    return {"status": "success"}

# Serving the static UI (assuming it's in V3/webui/)
webui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webui")
if os.path.exists(webui_path):
    app.mount("/", StaticFiles(directory=webui_path, html=True), name="webui")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
