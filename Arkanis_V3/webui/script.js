// Arkanis V3.1 - Master Control Script (Elite UI Edition)

// --- Onboarding Check ---
async function checkOnboardingStatus() {
    try {
        const response = await fetch('/onboarding/status');
        const data = await response.json();
        if (!data.setup_complete && !window.location.pathname.includes('onboarding.html')) {
            window.location.href = '/onboarding.html';
        }
    } catch (e) {
        console.warn('Failed to check onboarding status:', e);
    }
}
// Run immediately
checkOnboardingStatus();

// Core Elements
const chatDisplay = document.getElementById('chatDisplay');
const welcomeScreen = document.getElementById('welcomeScreen');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const voiceBtn = document.getElementById('voiceBtn');
const voiceIndicator = document.getElementById('voiceIndicator');

// Status Panel Elements
const statusBadge = document.getElementById('statusBadge');
const statusText = document.getElementById('statusText');
const agentModeText = document.getElementById('agentModeText');
const agentCycleText = document.getElementById('agentCycleText');

// Ticker Elements
const tickerContainer = document.getElementById('activityTickerContainer');
const tickerText = document.getElementById('activityTickerText');
const logToggleBtn = document.getElementById('logToggleBtn');

// Drawer Elements
const logDrawer = document.getElementById('logDrawer');
const logDrawerContent = document.getElementById('logDrawerContent');
const closeLogDrawer = document.getElementById('closeLogDrawer');

// Navigation
const navProviders = document.getElementById('navProviders');
const providersPanel = document.getElementById('providersPanel');
const providerCardsContainer = document.getElementById('providerCardsContainer');
const modelsListTable = document.getElementById('modelsListTable');
const saveConfigBtn = document.getElementById('saveConfigBtn');

const tabLlmsBtn = document.getElementById('tabLlmsBtn');
const tabIntegrationsBtn = document.getElementById('tabIntegrationsBtn');
const tabLlmsContent = document.getElementById('tabLlmsContent');
const tabIntegrationsContent = document.getElementById('tabIntegrationsContent');
const integrationCardsContainer = document.getElementById('integrationCardsContainer');

// Task Engine Elements
const navTasks = document.getElementById('navTasks');
const tasksPanel = document.getElementById('tasksPanel');
const createTaskBtn = document.getElementById('createTaskBtn');
const tasksListContainer = document.getElementById('tasksListContainer');
const newTaskDesc = document.getElementById('newTaskDesc');
const newTaskType = document.getElementById('newTaskType');
const newTaskInterval = document.getElementById('newTaskInterval');
const newTaskCondition = document.getElementById('newTaskCondition');
const newTaskGoalId = document.getElementById('newTaskGoalId');
const busLogsContainer = document.getElementById('busLogsContainer');
const goalsListContainer = document.getElementById('goalsListContainer');
const showCreateGoalModalBtn = document.getElementById('showCreateGoalModalBtn');
const governorContainer = document.getElementById('governorContainer');
const navLogs = document.getElementById('navLogs');
const navChat = document.getElementById('navChat');
const navHistory = document.getElementById('navHistory');
const navAnalyses = document.getElementById('navAnalyses');

// Global State
let lastLogIndex = 0;
let lastBusMessageId = -1;
let logQueue = [];
let isTickerRunning = false;
let isDrawerOpen = false;
let currentConfig = { providers: {}, models: [] };
let currentIntegrationsConfig = {};
let activeConfigTab = 'llms'; // 'llms' or 'integrations'

// Model picker state
let allModelsList = [];      // all models (local + cloud + OR fetched)
let modelPickerFilter = 'all'; // 'all' | 'free' | 'paid'

// Voice Recording State
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// --- 1. Message Logic ---

async function sendMessage(textOverride = null) {
    const text = textOverride || userInput.value.trim();
    if (!text) return;

    // Reset UI
    if (welcomeScreen && !welcomeScreen.classList.contains('hidden')) {
        welcomeScreen.classList.add('hidden');
        chatDisplay.innerHTML = '<div class="max-w-4xl mx-auto space-y-10" id="messageArea"></div>';
    }

    const messageArea = document.getElementById('messageArea');
    
    // Add User Message
    if (!textOverride) {
        addUserMessage(text);
        userInput.value = '';
        adjustTextArea();
    }

    // Add Thinking UI
    const thinkingId = 'thinking-' + Date.now();
    addBotMessage('<div class="flex items-center gap-2"><span class="animate-pulse">Analyzing...</span></div>', thinkingId);

    try {
        const response = await fetch('/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        
        const data = await response.json();
        const thinkingMsg = document.getElementById(thinkingId);
        if (thinkingMsg) {
            thinkingMsg.innerHTML = formatResponse(data.response);
        }
    } catch (error) {
        console.error('Error sending message:', error);
        document.getElementById(thinkingId).innerText = "Erro ao conectar com o Arkanis.";
    }
}

// --- 2. Voice/Audio Logic ---

async function toggleRecording() {
    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            sendVoiceMessage(audioBlob);
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        isRecording = true;
        updateVoiceUI(true);

    } catch (err) {
        console.error("Microphone access denied or error:", err);
        alert("Erro ao acessar microfone. Verifique as permissões.");
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        updateVoiceUI(false);
    }
}

function updateVoiceUI(recording) {
    if (recording) {
        voiceIndicator.classList.remove('hidden');
        voiceIndicator.classList.add('flex');
        userInput.classList.add('hidden');
        voiceBtn.classList.add('text-primary');
    } else {
        voiceIndicator.classList.add('hidden');
        voiceIndicator.classList.remove('flex');
        userInput.classList.remove('hidden');
        voiceBtn.classList.remove('text-primary');
    }
}

async function sendVoiceMessage(blob) {
    // 1. Prepare UI
    if (welcomeScreen && !welcomeScreen.classList.contains('hidden')) {
        welcomeScreen.classList.add('hidden');
        chatDisplay.innerHTML = '<div class="max-w-4xl mx-auto space-y-10" id="messageArea"></div>';
    }

    addUserMessage("🎙️ [Áudio Enviado]");
    
    const thinkingId = 'thinking-' + Date.now();
    addBotMessage('<div class="flex items-center gap-2"><span class="animate-pulse">Transcrevendo áudio...</span></div>', thinkingId);

    // 2. Upload to backend
    const formData = new FormData();
    formData.append('file', blob, 'web_audio.wav');

    try {
        const response = await fetch('/voice_message', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        const thinkingMsg = document.getElementById(thinkingId);
        
        if (thinkingMsg) {
            if (data.transcription) {
                // Update with transcription + response
                thinkingMsg.innerHTML = `
                    <div class="mb-4 p-2 bg-primary/5 border-l-2 border-primary text-[11px] italic text-slate-400">
                        " ${data.transcription} "
                    </div>
                    ${formatResponse(data.response)}
                `;
            } else {
                thinkingMsg.innerHTML = formatResponse(data.response);
            }
        }
    } catch (error) {
        console.error('Error sending voice message:', error);
        document.getElementById(thinkingId).innerText = "Erro ao processar áudio.";
    }
}

function addUserMessage(text) {
    const area = document.getElementById('messageArea');
    const wrap = document.createElement('div');
    wrap.className = 'flex justify-end mb-6';
    wrap.innerHTML = `<div class="bg-blue-600 text-white px-6 py-4 rounded-2xl rounded-br-none max-w-[80%] shadow-lg shadow-blue-900/20 text-sm font-body leading-relaxed">${text}</div>`;
    area.appendChild(wrap);
    scrollDown();
}

function addBotMessage(text, id = null) {
    const area = document.getElementById('messageArea');
    const wrap = document.createElement('div');
    wrap.className = 'flex justify-start items-start gap-4 mb-8';
    if (id) wrap.id = id;
    
    wrap.innerHTML = `
        <div class="w-8 h-8 rounded-lg bg-blue-500/20 flex-shrink-0 flex items-center justify-center border border-blue-500/20">
            <span class="material-symbols-outlined text-blue-400 text-sm" style="font-variation-settings: 'FILL' 1;">bolt</span>
        </div>
        <div class="bg-slate-900/50 text-slate-200 px-8 py-6 rounded-2xl rounded-bl-none max-w-[85%] border border-white/5 shadow-xl">
            <div id="bot-content-${id || Date.now()}" class="space-y-4 font-body leading-relaxed text-sm">${text}</div>
            <div class="pt-4 flex gap-2 opacity-50 hover:opacity-100 transition-opacity">
                <button class="px-2 py-1 rounded hover:bg-white/5 text-[10px] uppercase font-bold tracking-tighter">Copiar</button>
                <button class="px-2 py-1 rounded hover:bg-white/5 text-[10px] uppercase font-bold tracking-tighter">Regenerar</button>
            </div>
        </div>
    `;
    area.appendChild(wrap);
    scrollDown();
}

function formatResponse(text) {
    return text.replace(/\n/g, '<br>').replace(/`([^`]+)`/g, '<code class="bg-blue-500/10 text-blue-400 px-1 rounded">$1</code>');
}

function scrollDown() {
    chatDisplay.scrollTo({ top: chatDisplay.scrollHeight, behavior: 'smooth' });
}

// --- 2. Activity Ticker Logic ---

async function pollLogs() {
    try {
        const response = await fetch(`/logs?since=${lastLogIndex}`);
        const data = await response.json();

        if (data.logs && data.logs.length > 0) {
            data.logs.forEach(log => {
                logQueue.push(log);
                addLogToDrawer(log);
                lastLogIndex++;
            });
            
            if (!isTickerRunning) {
                runTicker();
            }
        }
    } catch (e) {
        console.warn('Log polling failed');
    }
}

async function runTicker() {
    if (logQueue.length === 0) {
        isTickerRunning = false;
        return;
    }
    
    isTickerRunning = true;
    const log = logQueue.shift();
    
    // Animate Fade
    tickerText.classList.remove('fade');
    void tickerText.offsetWidth; // Trigger reflow
    tickerText.classList.add('fade');
    
    tickerText.textContent = `[${log.type.toUpperCase()}] ${log.message}`;
    
    // Wait for animation duration (4s in CSS) or slightly less to queue next
    setTimeout(runTicker, 4000);
}

function addLogToDrawer(log) {
    const entry = document.createElement('div');
    entry.className = `log-entry log-${log.type}`;
    entry.innerHTML = `<span class="opacity-30 mr-2">[${log.time}]</span> <span class="uppercase font-bold mr-2">${log.type}:</span> ${log.message}`;
    logDrawerContent.appendChild(entry);
    if (!isDrawerOpen) logDrawerContent.scrollTop = logDrawerContent.scrollHeight;
}

// --- 3. Status Polling ---

async function pollStatus() {
    try {
        const response = await fetch('/status');
        const data = await response.json();

        if (statusBadge) {
            statusBadge.classList.remove('bg-green-500', 'bg-yellow-500', 'bg-red-500', 'bg-blue-500');
            if (data.status === 'running') statusBadge.classList.add('bg-yellow-500');
            else if (data.status === 'idle') statusBadge.classList.add('bg-green-500');
            else if (data.status === 'failed') statusBadge.classList.add('bg-red-500');
            else statusBadge.classList.add('bg-blue-500');
        }

        if (statusText) statusText.textContent = data.status.toUpperCase();
        if (agentModeText) agentModeText.textContent = `MODE: ${data.mode.toUpperCase()}`;
        if (agentCycleText) agentCycleText.textContent = `CYCLE: ${data.current_cycle}/5`;

        // Sync auto strategy state visually
        const toggle = document.getElementById('autoStrategyToggle');
        if (toggle && toggle.checked !== data.auto_strategy) {
            toggle.checked = data.auto_strategy;
        }
        
        // Update model button text correctly
        if (data.auto_strategy && currentModelName) {
            const prefix = data.active_tier ? `(AUTO - ${data.active_tier})` : '(AUTO)';
            // Check if the current name label matches
            if (!currentModelName.textContent.startsWith(prefix)) {
                 const modelId = data.active_model.split('/').pop() || data.active_model;
                 currentModelName.textContent = `${prefix} ${modelId.toUpperCase()}`;
            }
        }

    } catch (error) {
        console.warn('Status polling failed');
    }
}

// --- 4. Model Selector Logic ---

const activeModelBtn = document.getElementById('activeModelBtn');
const modelDropdown = document.getElementById('modelDropdown');
const currentModelName = document.getElementById('currentModelName');
const cloudModelsList = document.getElementById('cloudModelsList');
const localModelsList = document.getElementById('localModelsList');

async function fetchModels() {
    try {
        const response = await fetch('/models');
        const data = await response.json();

        // Merge into allModelsList (local + cloud), preserving OR fetched models
        const baseModels = [
            ...(data.local || []).map(m => ({ ...m, _source: 'local', _free: false, _cost: null })),
            ...(data.cloud || []).map(m => ({ ...m, _source: 'cloud', _free: m.id.includes(':free'), _cost: null })),
        ];
        // Keep any OR-fetched models that aren't already in base
        const baseIds = new Set(baseModels.map(m => m.id));
        const orOnly = allModelsList.filter(m => m._source === 'openrouter' && !baseIds.has(m.id));
        allModelsList = [...baseModels, ...orOnly];

        renderModelPicker();

        // Sync active model name from status
        const statusRes = await fetch('/status');
        const statusData = await statusRes.json();
        const active = allModelsList.find(m => m.id === statusData.active_model);
        if (active) {
            const isFree = active._free || active.id.includes(':free');
            const provLabel = active._source === 'local' ? 'ollama' : (active.provider || 'openrouter');
            if (statusData.auto_strategy) {
                const prefix = statusData.active_tier ? `(AUTO·${statusData.active_tier})` : '(AUTO)';
                updateModelSelectorUI(`${prefix} ${active.name}`, provLabel, isFree);
            } else {
                updateModelSelectorUI(active.name, provLabel, isFree);
            }
        }

        // Setup Auto Strategy toggle once
        const toggleBtn = document.getElementById('autoStrategyToggle');
        if (toggleBtn && !toggleBtn._bound) {
            toggleBtn._bound = true;
            toggleBtn.onchange = async (e) => {
                try {
                    await fetch('/strategy/toggle', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({enabled: e.target.checked}) });
                    await fetchModels();
                } catch (err) { console.error('Failed to toggle strategy:', err); }
            };
        }
    } catch (e) {
        console.warn('Failed to fetch models');
    }
}

async function fetchOpenRouterModels() {
    const btn = document.getElementById('refreshModelsBtn');
    if (btn) { btn.innerHTML = '<span class="material-symbols-outlined text-[13px] animate-spin">sync</span>Buscando...'; btn.disabled = true; }
    try {
        const res = await fetch('/models/openrouter/fetch');
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        // Merge fetched models into allModelsList
        const existingIds = new Set(allModelsList.map(m => m.id));
        const newFree = (data.free || []).map(m => ({
            id: m.id, name: m.name, provider: 'openrouter',
            _source: 'openrouter', _free: true, _cost: null,
            context: m.context
        })).filter(m => !existingIds.has(m.id));
        const newPaid = (data.paid || []).map(m => ({
            id: m.id, name: m.name, provider: 'openrouter',
            _source: 'openrouter', _free: false, _cost: m.cost || null,
            context: m.context
        })).filter(m => !existingIds.has(m.id));

        allModelsList = [...allModelsList, ...newFree, ...newPaid];
        renderModelPicker();

        const total = newFree.length + newPaid.length;
        if (btn) btn.innerHTML = `<span class="material-symbols-outlined text-[13px]">check</span>${data.free.length} free · ${data.paid.length} pagos`;
    } catch (e) {
        if (btn) btn.innerHTML = '<span class="material-symbols-outlined text-[13px]">error</span>Erro';
        console.error('Failed to fetch OR models:', e);
    } finally {
        setTimeout(() => {
            if (btn) { btn.innerHTML = '<span class="material-symbols-outlined text-[13px]">cloud_download</span>Atualizar OR'; btn.disabled = false; }
        }, 4000);
    }
}

function renderModelPicker() {
    const container = document.getElementById('modelListContainer');
    if (!container) return;

    const search = (document.getElementById('modelSearchInput')?.value || '').toLowerCase().trim();

    let models = allModelsList.filter(m => {
        if (modelPickerFilter === 'free' && !m._free) return false;
        if (modelPickerFilter === 'paid' && m._free) return false;
        if (search && !m.name.toLowerCase().includes(search) && !m.id.toLowerCase().includes(search)) return false;
        return true;
    });

    if (models.length === 0) {
        container.innerHTML = `<div class="text-center py-8 text-slate-600 text-xs">${search ? 'Nenhum modelo encontrado.' : 'Clique em "Atualizar OR" para buscar modelos.'}</div>`;
        return;
    }

    // Group: local → cloud (configured) → openrouter free → openrouter paid
    const groups = [
        { label: 'Local', icon: 'terminal', items: models.filter(m => m._source === 'local') },
        { label: 'Cloud (Configurado)', icon: 'cloud', items: models.filter(m => m._source === 'cloud') },
        { label: 'OpenRouter · Free', icon: null, free: true, items: models.filter(m => m._source === 'openrouter' && m._free) },
        { label: 'OpenRouter · Pagos', icon: null, free: false, paid: true, items: models.filter(m => m._source === 'openrouter' && !m._free) },
    ].filter(g => g.items.length > 0);

    container.innerHTML = '';
    groups.forEach(group => {
        const header = document.createElement('div');
        header.className = 'px-2 pt-3 pb-1.5 flex items-center gap-1.5';
        const labelClass = group.free ? 'text-emerald-500' : group.paid ? 'text-amber-500' : 'text-slate-500';
        header.innerHTML = `<span class="text-[9px] font-bold uppercase tracking-widest ${labelClass}">${group.label}</span><span class="text-[9px] text-slate-700 font-medium">(${group.items.length})</span>`;
        container.appendChild(header);

        group.items.forEach(model => {
            const btn = document.createElement('button');
            btn.className = 'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 text-left transition-all group border border-transparent hover:border-white/5';
            const ctxK = model.context ? (model.context >= 1000 ? Math.round(model.context/1000)+'k' : model.context) : '';
            const costBadge = model._free
                ? `<span class="text-[9px] font-bold px-1.5 py-0.5 rounded-sm bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 shrink-0">FREE</span>`
                : model._cost
                    ? `<span class="text-[9px] font-semibold text-amber-400 shrink-0">$${model._cost}</span>`
                    : `<span class="text-[9px] text-slate-600 shrink-0">pago</span>`;
            btn.innerHTML = `
                <div class="flex-1 min-w-0">
                    <div class="text-[12px] font-semibold text-slate-200 truncate group-hover:text-white">${model.name}</div>
                    <div class="text-[9px] text-slate-600 truncate">${model.id}${ctxK ? ' · '+ctxK+' ctx' : ''}</div>
                </div>
                ${costBadge}
            `;
            btn.onclick = (e) => {
                e.stopPropagation();
                const provLabel = model._source === 'local' ? 'ollama' : 'openrouter';
                selectModel(model.id, model.name, provLabel, model._free);
            };
            container.appendChild(btn);
        });
    });
}

// Model search input handler
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('modelSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', () => renderModelPicker());
        searchInput.addEventListener('click', e => e.stopPropagation());
    }
    // Filter buttons
    document.querySelectorAll('.model-filter').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            modelPickerFilter = btn.dataset.filter;
            document.querySelectorAll('.model-filter').forEach(b => {
                b.className = 'model-filter px-2.5 py-1 rounded-full text-[10px] font-bold bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10 transition-all';
            });
            btn.className = 'model-filter active px-2.5 py-1 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30';
            renderModelPicker();
        });
    });

    // Collapsible toggles for Governor and Goals
    function setupToggle(btnId, bodyId, chevronId) {
        const btn = document.getElementById(btnId);
        const body = document.getElementById(bodyId);
        const chevron = document.getElementById(chevronId);
        if (!btn || !body) return;
        btn.addEventListener('click', () => {
            const open = !body.classList.contains('hidden');
            body.classList.toggle('hidden', open);
            if (chevron) chevron.style.transform = open ? '' : 'rotate(180deg)';
        });
    }
    setupToggle('governorToggleBtn', 'governorBody', 'governorChevron');
    setupToggle('goalsToggleBtn', 'goalsBody', 'goalsChevron');
});

// --- 5. Configuration Panel Management ---

async function loadProvidersConfig() {
    try {
        const response = await fetch('/providers');
        currentConfig = await response.json();
        renderProviders();
    } catch (e) {
        console.error('Failed to load providers config');
    }
}

function renderProviders() {
    if (!providerCardsContainer) return;
    providerCardsContainer.innerHTML = '';
    
    Object.entries(currentConfig.providers).forEach(([id, cfg]) => {
        const card = document.createElement('div');
        card.className = 'bg-slate-800/40 rounded-2xl border border-white/5 p-5 flex flex-col gap-4 hover:border-blue-500/30 transition-all';
        card.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                        <span class="material-symbols-outlined text-primary text-xl">${getProviderIcon(id)}</span>
                    </div>
                    <div>
                        <h4 class="font-bold text-slate-100 text-sm">${cfg.name}</h4>
                        <span id="badge-${id}" class="text-[8px] font-bold uppercase py-0.5 px-2 rounded-full ${cfg.enabled ? 'bg-green-500/20 text-green-400' : 'bg-slate-500/20 text-slate-400'}">
                            ${cfg.enabled ? 'Ativo' : 'Inativo'}
                        </span>
                    </div>
                </div>
                <label class="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" id="toggle-${id}" class="sr-only peer" ${cfg.enabled ? 'checked' : ''} onchange="toggleProvider('${id}')">
                    <div class="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
            </div>
            
            <div class="space-y-3 mt-2">
                ${cfg.api_key !== undefined ? `
                    <div>
                        <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">API Key</label>
                        <input type="password" value="${cfg.api_key}" id="key-${id}" class="w-full bg-slate-900 border border-white/5 rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none" placeholder="sk-...">
                    </div>
                ` : ''}
                <div>
                    <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">Endpoint URL</label>
                    <input type="text" value="${cfg.endpoint}" id="url-${id}" class="w-full bg-slate-900 border border-white/5 rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none" placeholder="http://...">
                </div>
            </div>

            <div class="flex items-center gap-2 mt-auto">
                <button onclick="testProvider('${id}')" class="flex-1 bg-white/5 hover:bg-white/10 text-slate-300 text-[11px] font-bold py-2 rounded-lg transition-all border border-white/5">
                    Testar Conexão
                </button>
            </div>
        `;
        providerCardsContainer.appendChild(card);
    });

    renderModelsTable();
}

function getProviderIcon(id) {
    const icons = {
        'openrouter': 'hub',
        'ollama': 'terminal',
        'openai': 'bolt',
        'anthropic': 'psychology',
        'google': 'language',
        'xai': 'rocket_launch',
        'mistral': 'Cyclone',
        'qwen': 'cloud',
        'glm': 'smart_toy',
        'moonshot': 'nightlight',
        'minimax': 'speed',
        'venice': 'water',
        'copilot': 'code_blocks'
    };
    return icons[id] || 'dns';
}

function renderModelsTable() {
    if (!modelsListTable) return;
    modelsListTable.innerHTML = '';
    
    // Group models by provider
    const groupedModels = {};
    currentConfig.models.forEach((model, index) => {
        const prov = model.provider || 'outros';
        if (!groupedModels[prov]) groupedModels[prov] = [];
        groupedModels[prov].push({ model, index });
    });

    // Render each group
    Object.keys(groupedModels).sort().forEach(providerName => {
        // Provider Header
        const header = document.createElement('div');
        header.className = 'text-xs font-bold uppercase text-slate-500 mt-4 mb-2 flex items-center gap-2 border-b border-white/5 pb-1';
        header.innerHTML = `<span class="material-symbols-outlined text-[14px]">${getProviderIcon(providerName)}</span> Modelos ${providerName}`;
        modelsListTable.appendChild(header);

        // Render models
        groupedModels[providerName].forEach(({ model, index }) => {
            const row = document.createElement('div');
            row.className = 'flex items-center justify-between p-3 hover:bg-white/5 rounded-xl transition-all border border-transparent hover:border-white/5 group ml-2';
            row.innerHTML = `
                <div class="flex items-center gap-3">
                    <span class="material-symbols-outlined text-slate-600 group-hover:text-primary transition-colors">smart_toy</span>
                    <div>
                        <div class="text-sm font-bold text-on-surface">${model.name}</div>
                        <div class="text-[10px] text-slate-500 font-mono">${model.id}</div>
                    </div>
                </div>
                <label class="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" class="sr-only peer" ${model.enabled ? 'checked' : ''} onchange="toggleModel(${index})">
                    <div class="w-9 h-5 bg-slate-700 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-400 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-500"></div>
                </label>
            `;
            modelsListTable.appendChild(row);
        });
    });
}

function toggleProvider(id) {
    currentConfig.providers[id].enabled = document.getElementById(`toggle-${id}`).checked;
    const badge = document.getElementById(`badge-${id}`);
    if (currentConfig.providers[id].enabled) {
        badge.className = 'text-[9px] font-bold uppercase py-0.5 px-2 rounded-full bg-green-500/20 text-green-400';
        badge.textContent = 'Ativo';
    } else {
        badge.className = 'text-[9px] font-bold uppercase py-0.5 px-2 rounded-full bg-slate-500/20 text-slate-400';
        badge.textContent = 'Inativo';
    }
}

function toggleModel(index) {
    currentConfig.models[index].enabled = !currentConfig.models[index].enabled;
}

async function testProvider(id) {
    const key = document.getElementById(`key-${id}`)?.value || "";
    const url = document.getElementById(`url-${id}`).value;
    
    // Feedback visual imediato
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Testando...';
    btn.disabled = true;

    try {
        const response = await fetch('/providers/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider_id: id, api_key: key, endpoint: url })
        });
        const data = await response.json();
        
        if (data.status === 'connected') {
            btn.className = 'flex-1 bg-green-500/20 text-green-400 text-[11px] font-bold py-2 rounded-lg transition-all border border-green-500/20';
            btn.textContent = 'Conectado!';
        } else {
            btn.className = 'flex-1 bg-red-500/20 text-red-400 text-[11px] font-bold py-2 rounded-lg transition-all border border-red-500/20';
            btn.textContent = 'Erro de Conexão';
            alert(`Falha no teste: ${data.detail}`);
        }
    } catch (e) {
        btn.textContent = 'Falha no Teste';
    } finally {
        setTimeout(() => {
            btn.textContent = originalText;
            btn.className = 'flex-1 bg-white/5 hover:bg-white/10 text-slate-300 text-[11px] font-bold py-2 rounded-lg transition-all border border-white/5';
            btn.disabled = false;
        }, 3000);
    }
}

async function saveProvidersConfig() {
    // Atualizar keys e URLs do objeto global antes de enviar
    Object.keys(currentConfig.providers).forEach(id => {
        const keyInput = document.getElementById(`key-${id}`);
        const urlInput = document.getElementById(`url-${id}`);
        if (keyInput) currentConfig.providers[id].api_key = keyInput.value;
        if (urlInput) currentConfig.providers[id].endpoint = urlInput.value;
    });

    saveConfigBtn.textContent = 'Salvando...';
    saveConfigBtn.disabled = true;

    try {
        const response = await fetch('/providers/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config: currentConfig })
        });
        const data = await response.json();
        if (data.status === 'success') {
            saveConfigBtn.textContent = 'Salvo com Sucesso!';
            saveConfigBtn.classList.replace('bg-primary', 'bg-green-600');
            
            // Refresh model selector in UI
            fetchModels();
            
            setTimeout(() => {
                saveConfigBtn.textContent = 'Salvar Configuração';
                saveConfigBtn.classList.replace('bg-green-600', 'bg-primary');
                saveConfigBtn.disabled = false;
            }, 2000);
        }
    } catch (e) {
        console.error('Save config failed');
        const originalText = saveConfigBtn.innerHTML;
        saveConfigBtn.innerHTML = '<span class="material-symbols-outlined text-sm">error</span> Erro ao Salvar';
        saveConfigBtn.classList.add('bg-red-500');
        setTimeout(() => {
            saveConfigBtn.innerHTML = originalText;
            saveConfigBtn.classList.remove('bg-red-500');
        }, 2000);
    }
}

async function loadIntegrationsConfig() {
    try {
        const response = await fetch('/integrations');
        currentIntegrationsConfig = await response.json();
        renderIntegrations();
    } catch (e) {
        console.error('Failed to load integrations config');
    }
}

function renderIntegrations() {
    if (!integrationCardsContainer) return;
    integrationCardsContainer.innerHTML = '';
    
    // Telegram
    const telegram = currentIntegrationsConfig.telegram || {enabled: false, token: ''};
    integrationCardsContainer.appendChild(createIntegrationCard('telegram', 'Telegram Bot', 'send', telegram, [
        { key: 'token', label: 'Bot Token', type: 'password', value: telegram.token, placeholder: '123456789:ABCDEF...' }
    ]));
    
    // Supabase
    const supabase = currentIntegrationsConfig.supabase || {enabled: false, url: '', anon_key: '', service_role_key: ''};
    integrationCardsContainer.appendChild(createIntegrationCard('supabase', 'Supabase', 'database', supabase, [
        { key: 'url', label: 'Project URL', type: 'text', value: supabase.url, placeholder: 'https://xxx.supabase.co' },
        { key: 'anon_key', label: 'Anon Key', type: 'password', value: supabase.anon_key, placeholder: 'eyJh...' },
        { key: 'service_role_key', label: 'Service Role Key', type: 'password', value: supabase.service_role_key, placeholder: 'eyJh...' }
    ]));
    
    // Tavily
    const tavily = currentIntegrationsConfig.tavily || {enabled: false, api_key: ''};
    integrationCardsContainer.appendChild(createIntegrationCard('tavily', 'Tavily Search', 'search', tavily, [
        { key: 'api_key', label: 'API Key', type: 'password', value: tavily.api_key, placeholder: 'tvly-...' }
    ]));
}

function createIntegrationCard(id, title, icon, data, fields) {
    const card = document.createElement('div');
    card.className = 'bg-slate-800/40 rounded-2xl border border-white/5 p-6 flex flex-col gap-4 hover:border-blue-500/30 transition-all';
    
    let fieldsHtml = '';
    fields.forEach(f => {
        fieldsHtml += `
            <div>
                <label class="text-[10px] font-bold text-slate-500 uppercase ml-1">${f.label}</label>
                <input type="${f.type}" value="${f.value}" id="int-${id}-${f.key}" class="w-full bg-slate-900 border border-white/5 rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none" placeholder="${f.placeholder}">
            </div>
        `;
    });

    card.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                    <span class="material-symbols-outlined text-primary text-xl">${icon}</span>
                </div>
                <div>
                    <h4 class="font-bold text-slate-100 text-sm">${title}</h4>
                    <span id="badge-int-${id}" class="text-[8px] font-bold uppercase py-0.5 px-2 rounded-full ${data.enabled ? 'bg-green-500/20 text-green-400' : 'bg-slate-500/20 text-slate-400'}">
                        ${data.enabled ? 'Ativo' : 'Inativo'}
                    </span>
                </div>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" id="toggle-int-${id}" class="sr-only peer" ${data.enabled ? 'checked' : ''} onchange="toggleIntegration('${id}')">
                <div class="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
            </label>
        </div>
        <div class="space-y-3 mt-2 flex-grow">
            ${fieldsHtml}
        </div>
    `;
    return card;
}

function toggleIntegration(id) {
    if (!currentIntegrationsConfig[id]) {
        currentIntegrationsConfig[id] = { enabled: false };
    }
    currentIntegrationsConfig[id].enabled = !currentIntegrationsConfig[id].enabled;
    const badge = document.getElementById(`badge-int-${id}`);
    if (currentIntegrationsConfig[id].enabled) {
        badge.className = 'text-[8px] font-bold uppercase py-0.5 px-2 rounded-full bg-green-500/20 text-green-400';
        badge.textContent = 'Ativo';
    } else {
        badge.className = 'text-[8px] font-bold uppercase py-0.5 px-2 rounded-full bg-slate-500/20 text-slate-400';
        badge.textContent = 'Inativo';
    }
}

async function saveIntegrationsConfig() {
    saveConfigBtn.innerHTML = '<span class="material-symbols-outlined animate-spin">sync</span> Salvando...';
    
    // Update config object from UI
    ['telegram', 'supabase', 'tavily'].forEach(id => {
        if (!currentIntegrationsConfig[id]) currentIntegrationsConfig[id] = { enabled: false };
        
        if (id === 'telegram') {
            currentIntegrationsConfig[id].token = document.getElementById(`int-${id}-token`)?.value || '';
        } else if (id === 'supabase') {
            currentIntegrationsConfig[id].url = document.getElementById(`int-${id}-url`)?.value || '';
            currentIntegrationsConfig[id].anon_key = document.getElementById(`int-${id}-anon_key`)?.value || '';
            currentIntegrationsConfig[id].service_role_key = document.getElementById(`int-${id}-service_role_key`)?.value || '';
        } else if (id === 'tavily') {
            currentIntegrationsConfig[id].api_key = document.getElementById(`int-${id}-api_key`)?.value || '';
        }
    });

    try {
        const response = await fetch('/integrations/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config: currentIntegrationsConfig })
        });

        if (response.ok) {
            saveConfigBtn.innerHTML = '<span class="material-symbols-outlined text-sm">check</span> Salvo!';
            saveConfigBtn.classList.add('bg-green-500');
            setTimeout(() => {
                saveConfigBtn.innerHTML = '<span class="material-symbols-outlined text-sm">save</span> Salvar Alterações';
                saveConfigBtn.classList.remove('bg-green-500');
            }, 2000);
        } else {
            throw new Error('Save failed');
        }
    } catch (e) {
        console.error('Save integrations failed');
        const originalText = saveConfigBtn.innerHTML;
        saveConfigBtn.innerHTML = '<span class="material-symbols-outlined text-sm">error</span> Erro';
        saveConfigBtn.classList.add('bg-red-500');
        setTimeout(() => {
            saveConfigBtn.innerHTML = originalText;
            saveConfigBtn.classList.remove('bg-red-500');
        }, 2000);
    }
}


/**
 * CORE NAVIGATION ENGINE (Elite UI)
 * Manages all panel switching and sidebar states consistently.
 */
function setActivePanel(panelId) {
    const panels = {
        'chat': { element: chatDisplay, nav: navChat, showFooter: true },
        'providers': { element: providersPanel, nav: navProviders, showFooter: false },
        'tasks': { element: tasksPanel, nav: navTasks, showFooter: false }
    };

    // Close log drawer when switching to deep configuration
    if (panelId !== 'chat' && isDrawerOpen) {
        logDrawer.classList.add('hidden');
        logDrawer.classList.add('translate-y-full');
        isDrawerOpen = false;
    }

    // Toggle Panels Visibility
    Object.keys(panels).forEach(id => {
        const p = panels[id];
        if (id === panelId) {
            p.element.classList.remove('hidden');
            if (p.nav) {
                p.nav.classList.replace('text-slate-500', 'text-blue-400');
                p.nav.classList.replace('dark:text-slate-400', 'dark:text-blue-400');
                p.nav.classList.add('bg-slate-800/80');
            }
        } else {
            p.element.classList.add('hidden');
            if (p.nav) {
                p.nav.classList.replace('text-blue-400', 'text-slate-500');
                p.nav.classList.replace('dark:text-blue-400', 'dark:text-slate-400');
                p.nav.classList.remove('bg-slate-800/80');
            }
        }
    });

    // Special Case: Welcome Screen & Chat State
    if (panelId === 'chat') {
        const messageArea = document.getElementById('messageArea');
        const hasMessages = messageArea && messageArea.children.length > 0;
        
        if (hasMessages) {
            welcomeScreen.classList.add('hidden');
        } else {
            welcomeScreen.classList.remove('hidden');
        }
        userInput.focus();
        adjustTextArea();
    } else {
        welcomeScreen.classList.add('hidden');
    }

    // Toggle Footer (Input Area)
    const footer = document.querySelector('footer');
    if (footer) {
        footer.classList.toggle('hidden', !panels[panelId].showFooter);
    }
    
    // Smooth reflow hack
    window.dispatchEvent(new Event('resize'));
}

function showChat() {
    setActivePanel('chat');
}

function showProviders() {
    setActivePanel('providers');
    loadProvidersConfig();
    loadIntegrationsConfig();
}

function showTasks() {
    setActivePanel('tasks');
    loadTasks();
}

async function loadTasks() {
    try {
        const response = await fetch('/tasks');
        const data = await response.json();
        renderTasks(data.tasks);
    } catch (e) {
        console.error('Failed to load tasks', e);
    }
}

async function loadBusLogs() {
    try {
        const response = await fetch('/bus/logs');
        const data = await response.json();
        renderBusLogs(data.messages);
    } catch (e) {
        console.error('Failed to load bus logs', e);
    }
}

function renderBusLogs(messages) {
    if (!busLogsContainer) return;
    if (messages.length === 0) {
        busLogsContainer.innerHTML = '<div class="text-slate-500 italic">No communication yet.</div>';
        return;
    }
    
    // Only re-render if there's a new message to prevent scrolling issues
    if (messages.length > 0 && messages[messages.length - 1].id <= lastBusMessageId) {
        return; 
    }
    lastBusMessageId = messages[messages.length - 1].id;
    
    busLogsContainer.innerHTML = '';
    messages.forEach(msg => {
        const row = document.createElement('div');
        row.className = 'border-l-2 pl-2 border-primary/30';
        let labelColor = msg.type === 'broadcast' ? 'text-purple-400' : 'text-blue-400';
        row.innerHTML = `
            <div>
                <span class="text-slate-500">[${msg.timestamp}]</span>
                <span class="font-bold uppercase ${labelColor}">${msg.type}</span>
                <span class="text-white ml-2">${msg.from} &rarr; ${msg.to}</span>
            </div>
            <div class="text-slate-400 mt-1 pl-4 break-words">"${msg.content}"</div>
        `;
        busLogsContainer.appendChild(row);
    });
    busLogsContainer.scrollTop = busLogsContainer.scrollHeight;
}

function renderTasks(tasks) {
    if (!tasksListContainer) return;
    tasksListContainer.innerHTML = '';
    
    if (tasks.length === 0) {
        tasksListContainer.innerHTML = '<div class="text-sm text-slate-500 italic">Nenhuma tarefa ativa no momento.</div>';
        return;
    }
    
    tasks.forEach(task => {
        const card = document.createElement('div');
        card.className = 'bg-slate-800/40 rounded-xl border border-white/5 p-4 relative';
        
        let statusColor = 'bg-blue-500/20 text-blue-400';
        if (task.status === 'running') statusColor = 'bg-green-500/20 text-green-400';
        if (task.status === 'stopped') statusColor = 'bg-slate-500/20 text-slate-400';
        
        let logsHtml = '';
        if (task.recent_logs && task.recent_logs.length > 0) {
            logsHtml = '<div class="mt-3 bg-black/30 rounded p-2 text-[10px] font-mono text-slate-400 space-y-1">';
            task.recent_logs.forEach(l => {
                logsHtml += `<div><span class="text-blue-400">[${l.time}]</span> ${l.message}</div>`;
            });
            logsHtml += '</div>';
        }

        card.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1 pr-4">
                    <h4 class="font-bold text-slate-200 text-sm flex items-center gap-2">
                        ${task.description}
                        ${task.auto_generated ? '<span class="px-1.5 py-0.5 rounded-sm bg-purple-500/20 text-purple-400 text-[9px] uppercase tracking-wider font-bold border border-purple-500/30">Auto-Generated</span>' : ''}
                    </h4>
                    <div class="text-[10px] text-slate-500 mt-1 flex flex-wrap items-center gap-2">
                        <span class="uppercase tracking-widest font-bold border border-white/10 px-1 rounded-sm">${task.type}</span>
                        <span>Interval: ${task.interval}s</span>
                        ${task.condition ? `<span>Cond: ${task.condition}</span>` : ''}
                        ${task.goal_id ? `<span class="text-primary border-primary/20 border px-1 rounded-sm">Goal: ${task.goal_id}</span>` : ''}
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-[10px] font-bold uppercase py-0.5 px-2 rounded-full ${statusColor}">${task.status} (${task.agent_status})</span>
                    ${task.status !== 'stopped' ? `<button onclick="stopTask('${task.id}')" class="text-red-400 hover:text-red-300 p-1"><span class="material-symbols-outlined text-sm">stop_circle</span></button>` : ''}
                </div>
            </div>
            
            <div class="mt-3 grid grid-cols-2 gap-4 text-[11px] text-slate-400">
                <div>Última execução: <span class="text-slate-200">${task.last_run || 'Pendente'}</span></div>
                <div>Próxima execução: <span class="text-slate-200">${task.next_run || 'Pendente'}</span></div>
                <div>Contagem: <span class="text-slate-200">${task.run_count}</span></div>
            </div>
            ${logsHtml}
        `;
        tasksListContainer.appendChild(card);
    });
}

async function loadGovernorState() {
    if (!governorContainer) return;
    try {
        const response = await fetch('/governor/state');
        const data = await response.json();
        
        let llmColor = "text-green-400";
        if (data.current_llm_calls_pm > data.max_llm_calls_per_minute * 0.8) llmColor = "text-yellow-400";
        if (data.fallback_active) llmColor = "text-red-400 animate-pulse";
        
        governorContainer.innerHTML = `
            <div class="bg-black/30 border border-white/5 p-3 rounded-lg flex items-center justify-between w-64">
                <span class="text-slate-400">LLM Calls (pm)</span>
                <span class="font-bold text-lg ${llmColor}">${data.current_llm_calls_pm} <span class="text-xs text-slate-600">/ ${data.max_llm_calls_per_minute}</span></span>
            </div>
            <div class="bg-black/30 border border-white/5 p-3 rounded-lg flex items-center justify-between w-64">
                <span class="text-slate-400">Auto Fallback</span>
                <span class="font-bold text-sm ${data.fallback_active ? 'text-red-400' : 'text-slate-500'}">${data.fallback_active ? 'ATIVE - LIMIT HIT' : 'STANDBY'}</span>
            </div>
            <div class="bg-black/30 border border-white/5 p-3 rounded-lg flex items-center justify-between w-64">
                <span class="text-slate-400">Max Tasks Global</span>
                <span class="font-bold text-lg text-primary">${data.max_tasks_global}</span>
            </div>
        `;
    } catch (e) {
        console.error('Failed to load governor state', e);
    }
}

async function loadGoals() {
    try {
        const response = await fetch('/goals');
        const data = await response.json();
        renderGoals(data.goals);
    } catch (e) {
        console.error('Failed to load goals', e);
    }
}

function renderGoals(goals) {
    if (!goalsListContainer) return;
    goalsListContainer.innerHTML = '';
    
    if (newTaskGoalId) {
        // Keep the first option
        newTaskGoalId.innerHTML = '<option value="">Nenhum Objetivo</option>';
        goals.forEach(g => {
            if (g.status !== 'completed') {
                const opt = document.createElement('option');
                opt.value = g.id;
                opt.textContent = `${g.description}`;
                newTaskGoalId.appendChild(opt);
            }
        });
    }

    if (goals.length === 0) {
        goalsListContainer.innerHTML = '<div class="text-sm text-slate-500 italic">Nenhum objetivo global cadastrado.</div>';
        return;
    }

    goals.forEach(goal => {
        const card = document.createElement('div');
        card.className = 'bg-slate-800/40 rounded-xl border border-white/5 p-4';
        
        let statusColor = 'text-green-400';
        if (goal.status === 'paused') statusColor = 'text-yellow-400';
        if (goal.status === 'completed') statusColor = 'text-blue-400';

        card.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <h4 class="font-bold text-slate-200 text-sm">${goal.description}</h4>
                    <div class="text-[10px] text-slate-500 flex items-center gap-2 mt-1">
                        <span>ID: ${goal.id}</span>
                        <span>• Status: <b class="${statusColor} uppercase">${goal.status}</b></span>
                        <span>• Prioridade: <b class="uppercase">${goal.priority}</b></span>
                    </div>
                </div>
                <div class="ml-4 w-32 flex flex-col items-end">
                    <div class="w-full bg-slate-700 rounded-full h-1.5 mb-1 relative overflow-hidden">
                        <div class="bg-primary h-1.5 rounded-full" style="width: ${goal.progress}%"></div>
                    </div>
                    <span class="text-[10px] font-bold text-slate-300">${goal.progress}% Progresso</span>
                </div>
                <div class="flex ml-4 gap-2">
                    ${goal.status !== 'completed' ? `<button onclick="updateGoalStatus('${goal.id}', 'completed')" class="text-[10px] text-blue-400 bg-blue-400/10 px-2 py-1 rounded hover:bg-blue-400/20">Finalizar</button>` : ''}
                </div>
            </div>
        `;
        goalsListContainer.appendChild(card);
    });
}

async function createGoal() {
    const desc = prompt("Descrição do novo Objetivo Global:");
    if (!desc) return;
    const priority = prompt("Prioridade (high, medium, low):", "medium");
    try {
        await fetch('/goals/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description: desc, priority: priority || "medium" })
        });
        loadGoals();
    } catch(e) {
        console.error('Failed to create goal', e);
    }
}

async function updateGoalStatus(id, status) {
    if (!confirm(`Deseja alterar o status para ${status}?`)) return;
    try {
        await fetch('/goals/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ goal_id: id, status: status })
        });
        loadGoals();
    } catch(e) {
        console.error('Failed to update goal', e);
    }
}

async function startTask() {
    const desc = newTaskDesc.value.trim();
    if (!desc) { alert("Descrição obrigatória"); return; }
    
    createTaskBtn.disabled = true;
    createTaskBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">sync</span>Iniciando...';
    
    let gId = newTaskGoalId ? newTaskGoalId.value : null;

    try {
        const response = await fetch('/tasks/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: desc,
                type: newTaskType.value,
                interval: parseInt(newTaskInterval.value) || 300,
                condition: newTaskCondition.value.trim(),
                goal_id: gId || null
            })
        });
        
        if(response.ok) {
            newTaskDesc.value = '';
            newTaskCondition.value = '';
            loadTasks();
            loadGoals();
        }
    } catch(e) {
        console.error('Failed to start task', e);
    } finally {
        createTaskBtn.disabled = false;
        createTaskBtn.innerHTML = '<span class="material-symbols-outlined text-sm">play_arrow</span>Iniciar Tarefa';
    }
}

async function stopTask(id) {
    if (!confirm("Deseja parar a execução desta tarefa?")) return;
    try {
        await fetch('/tasks/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: id })
        });
        loadTasks();
    } catch(e) {
        console.error('Failed to stop task', e);
    }
}

function renderModelList(models, container, isFree = false) {
    if (!container) return;
    container.innerHTML = '';
    models.forEach(model => {
        const btn = document.createElement('button');
        btn.className = 'w-full text-left px-3 py-1.5 text-[11px] font-medium text-slate-300 hover:bg-white/5 hover:text-blue-300 rounded transition-all flex items-center gap-2 group';
        const shortId = model.id.split('/').pop().replace(':free','');
        btn.innerHTML = `
            <span class="flex-1 truncate">${model.name}</span>
            ${isFree ? '<span class="text-[8px] font-bold px-1 py-0.5 rounded-sm bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 shrink-0">FREE</span>' : ''}
            <span class="text-[9px] text-slate-600 group-hover:text-slate-500 shrink-0 hidden group-hover:inline">${shortId}</span>
        `;
        btn.onclick = (e) => {
            e.stopPropagation();
            selectModel(model.id, model.name, isFree ? 'openrouter' : model.provider, isFree);
        };
        container.appendChild(btn);
    });
}

async function selectModel(modelId, name, provider = 'openrouter', isFree = false) {
    try {
        const response = await fetch('/model/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_id: modelId })
        });
        const data = await response.json();
        if (data.status === 'success') {
            updateModelSelectorUI(name, provider, isFree);
            modelDropdown.classList.add('hidden');
            logQueue.push({type: 'system', message: `Modelo: ${name}`, time: new Date().toLocaleTimeString()});
            if (!isTickerRunning) runTicker();
        }
    } catch (e) {
        console.error('Erro ao trocar modelo.');
    }
}

function updateModelSelectorUI(name, provider, isFree) {
    const nameEl = document.getElementById('currentModelName');
    const provEl = document.getElementById('currentModelProvider');
    const badgeEl = document.getElementById('modelFreeBadge');
    if (nameEl) nameEl.textContent = name.toUpperCase();
    if (provEl) provEl.textContent = provider ? provider.toUpperCase() : '--';
    if (badgeEl) {
        if (isFree) { badgeEl.classList.remove('hidden'); }
        else { badgeEl.classList.add('hidden'); }
    }
}

if (activeModelBtn) {
    activeModelBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        modelDropdown.classList.toggle('hidden');
    });
}

document.addEventListener('click', (e) => {
    const btn = document.getElementById('refreshModelsBtn');
    if (btn && (e.target === btn || btn.contains(e.target))) {
        e.stopPropagation();
        fetchOpenRouterModels();
        return;
    }
    // Close dropdown on outside click
    const dropdown = document.getElementById('modelDropdown');
    const activeBtn = document.getElementById('activeModelBtn');
    if (dropdown && !dropdown.contains(e.target) && activeBtn && !activeBtn.contains(e.target)) {
        dropdown.classList.add('hidden');
    }
});

// dropdown close handled by the unified listener above

// also handle OR models not yet added to providers.json — select directly via router
async function selectOrModel(modelId, name, isFree) {
    // Temporarily add to router's models list via model/select
    // The router fallback returns "openrouter" for unknown models, which is correct
    await selectModel(modelId, name, 'OpenRouter', isFree);
}

// --- 6. Event Listeners ---

if (navProviders) {
    navProviders.addEventListener('click', (e) => {
        e.preventDefault();
        showProviders();
    });
}

if (navTasks) {
    navTasks.addEventListener('click', (e) => {
        e.preventDefault();
        showTasks();
    });
}

if (navLogs) {
    navLogs.addEventListener('click', (e) => {
        e.preventDefault();
        // First make sure chat is visible
        showChat();
        // Then toggle the drawer
        const opening = logDrawer.classList.contains('hidden');
        logDrawer.classList.toggle('hidden', !opening);
        logDrawer.classList.toggle('translate-y-full', !opening);
        isDrawerOpen = opening;
    });
}

if (createTaskBtn) {
    createTaskBtn.addEventListener('click', startTask);
}

if (showCreateGoalModalBtn) {
    showCreateGoalModalBtn.addEventListener('click', createGoal);
}

if (tabLlmsBtn && tabIntegrationsBtn) {
    tabLlmsBtn.addEventListener('click', () => {
        activeConfigTab = 'llms';
        tabLlmsBtn.className = 'py-3 text-sm font-bold text-blue-400 border-b-2 border-primary transition-all';
        tabIntegrationsBtn.className = 'py-3 text-sm font-bold text-slate-500 border-b-2 border-transparent hover:text-slate-300 transition-all';
        tabLlmsContent.classList.remove('hidden');
        tabLlmsContent.classList.add('block');
        tabIntegrationsContent.classList.remove('block');
        tabIntegrationsContent.classList.add('hidden');
    });

    tabIntegrationsBtn.addEventListener('click', () => {
        activeConfigTab = 'integrations';
        tabIntegrationsBtn.className = 'py-3 text-sm font-bold text-blue-400 border-b-2 border-primary transition-all';
        tabLlmsBtn.className = 'py-3 text-sm font-bold text-slate-500 border-b-2 border-transparent hover:text-slate-300 transition-all';
        tabIntegrationsContent.classList.remove('hidden');
        tabIntegrationsContent.classList.add('block');
        tabLlmsContent.classList.remove('block');
        tabLlmsContent.classList.add('hidden');
    });
}

if (saveConfigBtn) {
    saveConfigBtn.addEventListener('click', () => {
        if (activeConfigTab === 'llms') {
            saveProvidersConfig();
        } else {
            saveIntegrationsConfig();
        }
    });
}

// New unified sidebar listeners
if (navChat) {
    navChat.addEventListener('click', (e) => {
        e.preventDefault();
        showChat();
    });
}

const newChatBtn = document.querySelector('aside nav a'); // Fallback for the lightning bolt logo or generic links
if (newChatBtn && !newChatBtn.id) {
    newChatBtn.addEventListener('click', (e) => {
        e.preventDefault();
        showChat();
    });
}

userInput.addEventListener('input', adjustTextArea);

function adjustTextArea() {
    userInput.style.height = 'auto';
    userInput.style.height = (userInput.scrollHeight) + 'px';
}

if (sendBtn) {
    sendBtn.addEventListener('click', () => sendMessage());
}

if (voiceBtn) {
    voiceBtn.addEventListener('click', toggleRecording);
}
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

logToggleBtn.addEventListener('click', () => {
    logDrawer.classList.toggle('hidden');
    // Ensure it shows up above the footer
    logDrawer.classList.toggle('translate-y-full');
    isDrawerOpen = !logDrawer.classList.contains('hidden');
});

closeLogDrawer.addEventListener('click', () => {
    logDrawer.classList.add('hidden');
    logDrawer.classList.add('translate-y-full');
    isDrawerOpen = false;
});

// Suggestions
document.querySelectorAll('.suggestion-card').forEach(card => {
    card.addEventListener('click', () => {
        const action = card.getAttribute('data-action');
        sendMessage(action);
    });
});

// Intervals
setInterval(pollStatus, 2000);
setInterval(pollLogs, 1000);
setInterval(() => {
    if (tasksPanel && !tasksPanel.classList.contains('hidden')) {
        loadTasks(); // Auto refresh tasks when panel is open
        loadBusLogs(); // Auto refresh bus logs
        loadGoals(); // Auto refresh goals 
        loadGovernorState(); // Auto refresh governor
    }
}, 3000);

// Init
pollStatus();
pollLogs();
fetchModels();
loadGoals();
loadGovernorState();
