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
let currentSuggestionFilter = 'pending';
const governorToggleBtn = document.getElementById('governorToggleBtn');
const governorBody = document.getElementById('governorBody');
const governorChevron = document.getElementById('governorChevron');
const goalsToggleBtn = document.getElementById('goalsToggleBtn');
const goalsBody = document.getElementById('goalsBody');
const goalsChevron = document.getElementById('goalsChevron');
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
const navObservability = document.getElementById('navObservability');
const navDevCenter = document.getElementById('navDevCenter');
const devCenterPanel = document.getElementById('devCenterPanel');
const navArsenal = document.getElementById('navArsenal');
const arsenalPanel = document.getElementById('arsenalPanel');
const navMemory = document.getElementById('navMemory');
const memoryPanel = document.getElementById('memoryPanel');
const suggestionsGrid = document.getElementById('suggestionsGrid');

// Global State
let lastLogIndex = 0;
let lastBusMessageId = -1;
let logQueue = [];
let isTickerRunning = false;
let isDrawerOpen = false;
let currentConfig = { providers: {}, models: [] };
let currentIntegrationsConfig = {};
let activeConfigTab = 'llms'; // 'llms' or 'integrations'
let observabilityInterval = null;
let neuralGraph = { simulation: null, svg: null, container: null, nodes: [], links: [] };
let isHandsFree = false;
let mediaRecorder = null; // High-level MediaRecorder instance for both modes
let audioChunks = [];
let isRecording = false;
let terminal = null;
let terminalWs = null;
let terminalFitAddon = null;

// Model picker state
let allModelsList = [];      // all models (local + cloud + OR fetched)
let modelPickerFilter = 'all'; // 'all' | 'free' | 'paid'

// --- 1. Message Logic ---

async function sendMessage(textOverride = null) {
    const text = textOverride || userInput.value.trim();
    if (!text && uploadedImagesArr.length === 0) return;

    // Reset UI for the first message
    if (welcomeScreen && !welcomeScreen.classList.contains('hidden')) {
        welcomeScreen.classList.add('hidden');
        chatDisplay.innerHTML = `
            <div class="max-w-4xl mx-auto space-y-8 pb-12" id="messageArea">
                <div class="flex justify-center py-4 opacity-10 select-none">
                    <img src="assets/logo.png" class="h-10 object-contain filter grayscale invert" alt="Arkanis Logo">
                </div>
                <!-- Dynamic Content Here -->
                <div class="h-[400px] w-full pointer-events-none opacity-0" id="bottomSpacer"></div>
            </div>`;
    }

    const messageArea = document.getElementById('messageArea');
    
    // Snapshot images and files before clearing
    const imagesToSend = [...uploadedImagesArr];
    const filesToSend = [...uploadedFilesArr];

    // Add User Message (with image previews if any)
    if (!textOverride) {
        // Updated to handle both images and general files
        addUserMessageWithAttachments(text, imagesToSend, filesToSend);
        userInput.value = '';
        adjustTextArea();
        clearAttachments(); // clear after snapshot
    }

    // Add Thinking UI
    const thinkingId = 'thinking-' + Date.now();
    addBotMessage('<div class="flex items-center gap-2"><span class="animate-pulse">Analisando...</span></div>', thinkingId);

    try {
        const payload = { text: text || '' };
        if (imagesToSend.length > 0) payload.images = imagesToSend;
        if (filesToSend.length > 0) payload.files = filesToSend;

        const response = await fetch('/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        const thinkingMsg = document.getElementById(thinkingId);
        if (thinkingMsg) {
            // Use the typewriter effect for a natural feel
            const contentDiv = thinkingMsg.querySelector('[id^="bot-content-"]');
            if (contentDiv) {
                contentDiv.innerHTML = ""; // Clear "Analisando..."
                await typeWriter(contentDiv, formatResponse(data.response));
            } else {
                thinkingMsg.innerHTML = formatResponse(data.response);
            }
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
        chatDisplay.innerHTML = `
            <div class="max-w-4xl mx-auto space-y-8 pb-12" id="messageArea">
                <div class="flex justify-center py-4 opacity-10 select-none">
                    <img src="assets/logo.png" class="h-10 object-contain filter grayscale invert" alt="Arkanis Logo">
                </div>
                <!-- Dynamic Content Here -->
                <div class="h-[400px] w-full pointer-events-none opacity-0" id="bottomSpacer"></div>
            </div>`;
    }

    addUserMessage("🎙️ [Áudio Enviado]");
    
    const thinkingId = 'thinking-' + Date.now();
    addBotMessage('<div class="flex items-center gap-2"><span class="animate-pulse">Transcrevendo áudio...</span></div>', thinkingId);

    // 2. Upload to backend
    try {
        // Send raw binary to avoid python-multipart dependency
        const response = await fetch('/voice_message', { 
            method: 'POST', 
            body: blob,
            headers: { 'Content-Type': 'audio/webm' }
        });
        
        const data = await response.json();
        const thinkingMsg = document.getElementById(thinkingId);
        
        if (thinkingMsg) {
            const contentDiv = thinkingMsg.querySelector('[id^="bot-content-"]');
            if (contentDiv) {
                contentDiv.innerHTML = ""; // Clear "Transcrevendo..."
                
                if (data.transcription) {
                    const transcriptionHtml = `
                        <div class="mb-4 p-2 bg-primary/5 border-l-2 border-primary text-[11px] italic text-slate-400">
                            " ${data.transcription} "
                        </div>
                    `;
                    contentDiv.innerHTML = transcriptionHtml;
                }
                
                await typeWriter(contentDiv, formatResponse(data.response), true); // Append mode
            } else {
                thinkingMsg.innerHTML = formatResponse(data.response);
            }
        }
    } catch (error) {
        console.error('Error sending voice message:', error);
        document.getElementById(thinkingId).innerText = "Erro ao processar áudio.";
    }
}

function addUserMessage(text, timestamp = null) {
    const area = document.getElementById('messageArea');
    if (!area) return;
    const timeStr = timestamp || new Date().toLocaleString('pt-BR', {day: '2-digit', month: '2-digit', hour: '2-digit', minute:'2-digit'});
    const wrap = document.createElement('div');
    wrap.className = 'flex justify-end mb-6';
    wrap.innerHTML = `<div class="bubble-glass bubble-user text-white px-6 py-4 rounded-3xl rounded-br-none max-w-[85%] text-[15px] font-body leading-relaxed">
        <div>${text}</div>
        <div class="text-[9px] text-white/50 text-right mt-1">${timeStr}</div>
    </div>`;
    area.appendChild(wrap);
    scrollDown();
}

function addUserMessageWithAttachments(text, images = [], files = [], timestamp = null) {
    const area = document.getElementById('messageArea');
    if (!area) return;
    const timeStr = timestamp || new Date().toLocaleString('pt-BR', {day: '2-digit', month: '2-digit', hour: '2-digit', minute:'2-digit'});
    const wrap = document.createElement('div');
    wrap.className = 'flex justify-end mb-8 animate-in slide-in-from-right-4 duration-500';

    let attachmentsHtml = '';
    
    // Render Image Previews
    if (images && images.length > 0) {
        const imgThumbs = images.map(src => `
            <div class="w-24 h-24 rounded-xl overflow-hidden border border-white/10 shadow-lg group">
                <img src="${src}" class="w-full h-full object-cover transition-transform group-hover:scale-110" />
            </div>
        `).join('');
        attachmentsHtml += `<div class="flex flex-wrap gap-2 mb-3">${imgThumbs}</div>`;
    }

    // Render General File Chips
    if (files && files.length > 0) {
        const fileChips = files.map(file => `
            <div class="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-full text-slate-300">
                <span class="material-symbols-outlined text-blue-400 text-[16px]">description</span>
                <span class="text-[11px] font-bold truncate max-w-[150px]">${file.name}</span>
            </div>
        `).join('');
        attachmentsHtml += `<div class="flex flex-wrap gap-2 mb-3">${fileChips}</div>`;
    }

    wrap.innerHTML = `
        <div class="flex flex-col items-end max-w-[85%] gap-2">
            <div class="bubble-glass bubble-user text-white px-6 py-4 rounded-3xl rounded-br-none text-[15px] font-body leading-relaxed shadow-2xl relative">
                ${attachmentsHtml}
                ${text ? `<div>${text.replace(/\n/g, '<br>')}</div>` : ''}
                <div class="text-[9px] text-white/50 text-right mt-1">${timeStr}</div>
                <div class="absolute -bottom-6 right-2 text-[9px] text-slate-500 font-bold uppercase tracking-[0.2em] opacity-40">Enviado</div>
            </div>
        </div>`;

    area.appendChild(wrap);
    scrollDown();
}

function addBotMessage(text, id = null, timestamp = null) {
    const area = document.getElementById('messageArea');
    if (!area) return;
    const timeStr = timestamp || new Date().toLocaleString('pt-BR', {day: '2-digit', month: '2-digit', hour: '2-digit', minute:'2-digit'});
    const wrap = document.createElement('div');
    wrap.className = 'flex justify-start items-start gap-4 mb-8';
    if (id) wrap.id = id;
    
    const contentId = `bot-content-${id || Date.now()}`;
    
    wrap.innerHTML = `
        <div class="w-10 h-10 rounded-xl bg-slate-900 flex-shrink-0 flex items-center justify-center border border-white/10 shadow-lg p-1">
            <img src="assets/mascot.png" class="w-full h-full object-contain" alt="A">
        </div>
        <div class="bubble-glass bubble-bot text-slate-200 px-8 py-6 rounded-3xl rounded-bl-none max-w-[88%] shadow-2xl relative">
            <div id="${contentId}" class="space-y-4 font-body leading-relaxed text-[15px]">${text}</div>
            <div class="pt-5 flex gap-4 opacity-30 hover:opacity-100 transition-opacity">
                <button class="flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-[0.2em] hover:text-blue-400 transition-colors" onclick="copyToClipboard('${contentId}')">
                    <span class="material-symbols-outlined text-sm">content_copy</span> Copiar
                </button>
                <button class="flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-[0.2em] hover:text-blue-400 transition-colors">
                    <span class="material-symbols-outlined text-sm">refresh</span> Regenerar
                </button>
            </div>
            <div class="absolute -bottom-6 left-2 text-[9px] text-slate-500 font-bold uppercase tracking-[0.2em] opacity-40">${timeStr}</div>
        </div>
    `;
    area.appendChild(wrap);
    scrollDown();
}

/**
 * Typewriter effect with human-like cadence and reflection pauses.
 */
async function typeWriter(element, html, append = false) {
    if (!append) element.innerHTML = "";
    
    // Split HTML into tags and text nodes
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const nodes = Array.from(tempDiv.childNodes);
    
    for (const node of nodes) {
        if (node.nodeType === Node.TEXT_NODE) {
            const text = node.textContent;
            for (let i = 0; i < text.length; i++) {
                const char = text[i];
                element.innerHTML += char;
                scrollDown();
                
                // Human-like cadence
                let delay = 15 + Math.random() * 20;
                
                // Reflection Pauses (periods, commas, etc.)
                if (char === '.' || char === '!' || char === '?') delay += 400;
                else if (char === ',' || char === ':' || char === ';') delay += 200;
                
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        } else {
            // For HTML tags, inject them instantly but recurse if they have children
            const clone = node.cloneNode(true);
            element.appendChild(clone);
            scrollDown();
            await new Promise(resolve => setTimeout(resolve, 50));
        }
    }
}

function formatResponse(text) {
    return text.replace(/\n/g, '<br>').replace(/`([^`]+)`/g, '<code class="bg-blue-500/10 text-blue-400 px-1 rounded">$1</code>');
}

function scrollDown() {
    if (!chatDisplay) return;
    
    // Physical fix: Always ensure the spacer is at the end
    const spacer = document.getElementById('bottomSpacer');
    const area = document.getElementById('messageArea');
    if (spacer && area && area.lastElementChild !== spacer) {
        area.appendChild(spacer);
    }

    setTimeout(() => {
        chatDisplay.style.scrollBehavior = 'auto'; 
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
        
        // Minor secondary adjustment for late-rendering images
        setTimeout(() => {
            chatDisplay.scrollTop = chatDisplay.scrollHeight;
            chatDisplay.style.scrollBehavior = 'smooth';
        }, 150);
    }, 50);
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
    const feed = document.getElementById('sysLogFeed');
    if (!feed) return;
    
    // Auto limit to prevent memory bloat
    if (feed.children.length > 500) {
        feed.removeChild(feed.firstChild);
    }

    const tClass = log.type === 'error' ? 'text-rose-400 font-bold bg-rose-500/5' : 
                   (log.type === 'planner' || log.type === 'system' ? 'text-blue-300' : 
                   (log.type === 'critic' ? 'text-purple-300' : 'text-emerald-300'));

    const entry = document.createElement('div');
    entry.className = `log-line log-slide-in flex gap-3 ${tClass}`;
    entry.innerHTML = `
        <span class="opacity-40 whitespace-nowrap Shrink-0">[${log.time || new Date().toLocaleTimeString()}]</span> 
        <span class="uppercase tracking-widest font-black opacity-80 shrink-0 w-20">${log.type}:</span> 
        <span class="flex-1 break-words">${log.message}</span>
    `;

    feed.appendChild(entry);
    
    // Auto-scroll
    feed.scrollTop = feed.scrollHeight;
    
    // Update counters if visible
    const totCount = document.getElementById('sysLogTotalCount');
    if (totCount) totCount.textContent = feed.children.length;
    if (log.type === 'error') {
        const errCount = document.getElementById('sysLogErrCount');
        if (errCount) errCount.textContent = (parseInt(errCount.textContent) || 0) + 1;
    }
}

// Ensure clear terminal globally works
window.clearSystemLogs = function() {
    const feed = document.getElementById('sysLogFeed');
    if (feed) feed.innerHTML = '';
    const totCount = document.getElementById('sysLogTotalCount');
    if (totCount) totCount.textContent = '0';
    const errCount = document.getElementById('sysLogErrCount');
    if (errCount) errCount.textContent = '0';
};

// --- 3. Status Polling ---

let _statusFailCount = 0;

async function pollStatus() {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 5000); // 5s timeout
    try {
        const response = await fetch('/status', { signal: ctrl.signal });
        clearTimeout(timer);
        const data = await response.json();
        _statusFailCount = 0; // Reset fail counter on success

        // Remove offline banner if present
        const offlineBanner = document.getElementById('offlineBanner');
        if (offlineBanner) offlineBanner.remove();

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
            if (!currentModelName.textContent.startsWith(prefix)) {
                 const modelId = data.active_model.split('/').pop() || data.active_model;
                 currentModelName.textContent = `${prefix} ${modelId.toUpperCase()}`;
            }
        }

    } catch (error) {
        clearTimeout(timer);
        _statusFailCount++;
        console.warn(`Status polling failed (${_statusFailCount}x):`, error.name);
        
        // Show offline banner after 3 consecutive failures
        if (_statusFailCount >= 3 && !document.getElementById('offlineBanner')) {
            const banner = document.createElement('div');
            banner.id = 'offlineBanner';
            banner.className = 'fixed top-0 left-0 right-0 z-50 bg-red-600 text-white text-center text-sm font-bold py-2 px-4';
            banner.innerHTML = '⚠️ Servidor não está respondendo. O agente pode estar processando uma tarefa longa. <button onclick="location.reload()" class="ml-4 underline">Recarregar</button>';
            document.body.prepend(banner);
        }
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
    
    // Neural Map is NOT initialized here — it needs the panel to be visible for D3 dimension calculations.
    // It will be initialized by showObservability() when the panel opens.

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

    // TheSportsDB
    const tsdb = currentIntegrationsConfig.thesportsdb || {enabled: false, api_key: ''};
    integrationCardsContainer.appendChild(createIntegrationCard('thesportsdb', 'TheSportsDB API', 'sports_soccer', tsdb, [
        { key: 'api_key', label: 'API Key', type: 'password', value: tsdb.api_key, placeholder: '123' }
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
    ['telegram', 'supabase', 'tavily', 'thesportsdb'].forEach(id => {
        if (!currentIntegrationsConfig[id]) currentIntegrationsConfig[id] = { enabled: false };
        
        if (id === 'telegram') {
            currentIntegrationsConfig[id].token = document.getElementById(`int-${id}-token`)?.value || '';
        } else if (id === 'supabase') {
            currentIntegrationsConfig[id].url = document.getElementById(`int-${id}-url`)?.value || '';
            currentIntegrationsConfig[id].anon_key = document.getElementById(`int-${id}-anon_key`)?.value || '';
            currentIntegrationsConfig[id].service_role_key = document.getElementById(`int-${id}-service_role_key`)?.value || '';
        } else if (id === 'tavily' || id === 'thesportsdb') {
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
    console.log(`🎯 [Elite Nav] Toggling Panel: ${panelId}`);
    
    // Add transitioning class for Hyper-OS cinematic reveal
    document.body.classList.add('panel-transitioning');
    setTimeout(() => document.body.classList.remove('panel-transitioning'), 400);

    const panels = {
        'chat': { el: chatDisplay, nav: navChat, showFooter: true },
        'history': { el: document.getElementById('historyPanel'), nav: navHistory, showFooter: false },
        'observability': { el: document.getElementById('observabilityPanel'), nav: navObservability, showFooter: false },
        'tasks': { el: document.getElementById('tasksPanel'), nav: navTasks, showFooter: false },
        'memory': { el: document.getElementById('memoryPanel'), nav: navMemory, showFooter: false },
        'arsenal': { el: document.getElementById('arsenalPanel'), nav: navArsenal, showFooter: false },
        'nerveFusion': { el: document.getElementById('nerveFusionPanel'), nav: navLogs, showFooter: false },
        'devCenter': { el: document.getElementById('devCenterPanel'), nav: navDevCenter, showFooter: false },
        'providers': { el: document.getElementById('providersPanel'), nav: navProviders, showFooter: false }
    };

    // Reset all panels and nav items
    Object.values(panels).forEach(p => {
        if (p.el) p.el.classList.add('hidden');
        if (p.nav) {
            p.nav.classList.remove('active', 'text-white', 'bg-white/10');
            p.nav.classList.add('text-slate-400');
        }
    });

    const active = panels[panelId];
    if (active && active.el) {
        active.el.classList.remove('hidden');
        if (active.nav) {
            active.nav.classList.add('active', 'text-white', 'bg-white/10');
            active.nav.classList.remove('text-slate-400');
        }
        // Apply reveal animation
        active.el.style.animation = 'none';
        active.el.offsetHeight; // trigger reflow
        active.el.style.animation = 'fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
    } else {
        console.warn(`⚠️ [Elite Nav] Panel not found: ${panelId}`);
    }

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
        footer.classList.toggle('hidden', active && !active.showFooter);
    }
    
    // Smooth reflow hack
    window.dispatchEvent(new Event('resize'));
}

// ============================================================
// HYPER-OS: FOCUS MODE CONTROLLER
// ============================================================
function toggleFocusMode() {
    const isFocus = document.body.classList.toggle('focus-mode');
    const btn = document.getElementById('focusToggleBtn');
    if (btn) {
        const icon = btn.querySelector('.material-symbols-outlined');
        const text = btn.querySelector('span:not(.material-symbols-outlined)');
        if (icon) icon.textContent = isFocus ? 'visibility' : 'visibility_off';
        if (text) text.textContent = isFocus ? 'ELITE' : 'FOCUS';
    }
    
    // Notify the system
    console.log(`👁️ [Hyper-OS] Focus Mode: ${isFocus ? 'ON' : 'OFF'}`);
    if (typeof addSystemLog === 'function') {
        addSystemLog(`Modo Foco ${isFocus ? 'Ativado' : 'Desativado'}`, isFocus ? 'system' : 'info');
    }
}

// Global Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
    // Alt + F to Toggle Focus
    if (e.altKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        toggleFocusMode();
    }
});


function initSidebarNav() {
    const navActions = [
        { id: 'navChat',         action: () => setActivePanel('chat') },
        { id: 'navHistory',      action: () => showHistory() },
        { id: 'navObservability',action: () => showObservability() },
        { id: 'navTasks',        action: () => showTasks() },
        { id: 'navMemory',       action: () => showMemory() },
        { id: 'navArsenal',      action: () => showArsenal() },
        { id: 'navLogs',         action: () => showNerveFusion() },
        { id: 'navDevCenter',    action: () => showDevCenter() },
        { id: 'navProviders',    action: () => showProviders() },
    ];

    navActions.forEach(item => {
        const el = document.getElementById(item.id);
        if (el) {
            el.onclick = (e) => {
                e.preventDefault();
                item.action();
            };
        }
    });
}

// Alias for developer comfort/compatibility
const showPanel = setActivePanel;

function showChat() { setActivePanel('chat'); }
function showSystemLogs() { setActivePanel('systemLogs'); }
function showDevCenter() { 
    setActivePanel('devCenter'); 
    loadSuggestions(); 
    fetchObservabilityData();
    if (observabilityInterval) clearInterval(observabilityInterval);
    observabilityInterval = setInterval(fetchObservabilityData, 3000);
}
function showArsenal() {
    setActivePanel('arsenal');
    fetchToolsArsenal();
}

// --- Archive History Loader ---
function showHistory() {
    setActivePanel('history');
    loadHistory();
}

async function loadHistory() {
    const list = document.getElementById('historyList');
    const counter = document.getElementById('historyTotalCount');
    if (!list) return;

    list.innerHTML = `<div class="flex flex-col items-center justify-center py-16 text-center opacity-40">
        <span class="material-symbols-outlined animate-spin text-3xl text-slate-600 mb-3">sync</span>
        <p class="text-slate-500 text-xs font-bold uppercase tracking-widest">Sincronizando com a rede neural...</p>
    </div>`;

    try {
        const res = await fetch('/chat/history');
        const data = await res.json();
        const history = data.history || [];
        
        if (counter) counter.textContent = history.length;

        if (history.length === 0) {
            list.innerHTML = `
                <div class="flex flex-col items-center justify-center py-24 text-center">
                    <div class="w-20 h-20 rounded-3xl bg-slate-900/60 border border-white/5 flex items-center justify-center mb-5 shadow-xl">
                        <span class="material-symbols-outlined text-4xl text-slate-600">auto_stories</span>
                    </div>
                    <p class="text-slate-400 font-black text-sm uppercase tracking-widest">Nenhuma intera&#231;&#227;o arquivada</p>
                    <p class="text-slate-600 text-xs mt-2">Inicie uma conversa no Neural Chat para criar o primeiro registro.</p>
                </div>`;
            return;
        }

        list.innerHTML = history.map((item, idx) => {
            const num = idx + 1;
            const userSnippet = (item.user || '').substring(0, 120);
            const agentSnippet = (item.agent || '').substring(0, 160);
            const isLast = idx === history.length - 1;
            return `
            <div class="group p-5 bg-slate-900/30 hover:bg-slate-900/60 border border-white/5 hover:border-indigo-500/20 rounded-xl transition-all duration-200 cursor-pointer" onclick="restoreHistory(${idx})">
                <div class="flex items-start gap-4">
                    <div class="w-9 h-9 shrink-0 rounded-lg ${isLast ? 'bg-indigo-500/20 border-indigo-500/30' : 'bg-slate-800 border-white/5'} border flex items-center justify-center">
                        <span class="text-[11px] font-black ${isLast ? 'text-indigo-400' : 'text-slate-500'}">${num}</span>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-2">
                            <span class="text-[9px] font-black text-slate-500 uppercase tracking-widest">VOC&#202;</span>
                        </div>
                        <p class="text-[12px] text-slate-300 font-medium truncate mb-3">${userSnippet || '(mensagem vazia)'}</p>
                        <div class="flex items-center gap-2 mb-1.5">
                            <span class="text-[9px] font-black text-indigo-400 uppercase tracking-widest">ARKANIS</span>
                            ${isLast ? '<span class="px-1.5 py-0.5 bg-indigo-500/15 text-indigo-400 text-[8px] font-black rounded uppercase tracking-widest">&#218;ltima</span>' : ''}
                        </div>
                        <p class="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">${agentSnippet || '(sem resposta)'}</p>
                    </div>
                    <span class="material-symbols-outlined text-slate-700 group-hover:text-indigo-500 transition-colors text-sm shrink-0 mt-1">chevron_right</span>
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        list.innerHTML = `
            <div class="col-span-3 flex flex-col items-center justify-center py-16 text-rose-500/60 border border-rose-500/10 bg-rose-500/5 rounded-xl">
                <span class="material-symbols-outlined text-3xl mb-2">cloud_off</span>
                <p class="text-xs font-bold">Falha ao sincronizar o arquivo: ${e.message}</p>
            </div>`;
    }
}

function restoreHistory(idx) {
    // Navigate to chat and show a toast that history viewing is in read-only summary mode
    setActivePanel('chat');
    showToast(`Exibindo contexto #${idx + 1} — para reativar, inicie uma nova mensagem.`, 'indigo');
}

// --- Terminal CLI (Nerve Fusion) ---
let _nerveFusionInitialized = false;

function showNerveFusion() {
    setActivePanel('nerveFusion');
    if (!_nerveFusionInitialized) {
        _nerveFusionInitialized = true;
        initNerveFusion();
    }
}

function initNerveFusion() {
    const container = document.getElementById('terminalContainer');
    const loader = document.getElementById('terminalLoader');
    const statusBadge = document.getElementById('terminalStatusBadge');
    const statusText = document.getElementById('terminalStatusText');
    if (!container || typeof Terminal === 'undefined') {
        console.warn('[NerveFusion] Xterm.js not ready or container missing.');
        return;
    }

    // Create Xterm.js instance
    terminal = new Terminal({
        cursorBlink: true,
        fontFamily: '"JetBrains Mono", "Fira Code", monospace',
        fontSize: 13,
        lineHeight: 1.5,
        theme: {
            background: '#020617',
            foreground: '#cbd5e1',
            cursor: '#60a5fa',
            selectionBackground: 'rgba(59,130,246,0.3)',
            black: '#0f172a',
            red: '#f43f5e',
            green: '#34d399',
            yellow: '#fbbf24',
            blue: '#60a5fa',
            magenta: '#a78bfa',
            cyan: '#22d3ee',
            white: '#e2e8f0',
        },
        allowTransparency: true,
    });

    // FitAddon for responsive sizing
    // The CDN xterm-addon-fit exports FitAddon directly (not FitAddon.FitAddon)
    try {
        if (typeof FitAddon !== 'undefined') {
            const AddonClass = typeof FitAddon.FitAddon !== 'undefined' ? FitAddon.FitAddon : FitAddon;
            terminalFitAddon = new AddonClass();
            terminal.loadAddon(terminalFitAddon);
        }
    } catch(e) {
        console.warn('[NerveFusion] FitAddon not available:', e);
    }

    terminal.open(container);
    if (terminalFitAddon) terminalFitAddon.fit();

    terminal.writeln('\x1b[1;34m  ARKANIS NERVE FUSION v1.0 — Unified Terminal Interconnect\x1b[0m');
    terminal.writeln('\x1b[90m  Connecting to kernel shell...\x1b[0m');
    terminal.writeln('');

    // WebSocket connection
    const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProto}://${window.location.host}/terminal/ws`;
    terminalWs = new WebSocket(wsUrl);

    terminalWs.onopen = () => {
        if (loader) loader.classList.add('opacity-0', 'pointer-events-none');
        setTimeout(() => loader && loader.classList.add('hidden'), 500);
        if (statusBadge) { statusBadge.className = 'w-2 h-2 bg-emerald-400 rounded-full shadow-[0_0_8px_rgba(52,211,153,0.7)]'; }
        if (statusText) statusText.textContent = 'CONNECTED';
        terminal.writeln('\x1b[1;32m  ✓ Nerve Link established. Shell ready.\x1b[0m');
        terminal.writeln('');
        // Resize to inform the backend
        if (terminalFitAddon) terminalFitAddon.fit();
        terminalWs.send(JSON.stringify({ type: 'resize', rows: terminal.rows, cols: terminal.cols }));
    };

    terminalWs.onmessage = (event) => {
        terminal.write(event.data);
    };

    terminalWs.onerror = (err) => {
        terminal.writeln('\x1b[1;31m  ✗ Nerve Link error. Check server connection.\x1b[0m');
        if (statusBadge) statusBadge.className = 'w-2 h-2 bg-rose-500 rounded-full';
        if (statusText) statusText.textContent = 'ERROR';
    };

    terminalWs.onclose = () => {
        terminal.writeln('\x1b[33m  Nerve Link disconnected. Reconnecting in 3s...\x1b[0m');
        if (statusBadge) statusBadge.className = 'w-2 h-2 bg-amber-400 rounded-full';
        if (statusText) statusText.textContent = 'DISCONNECTED';
        _nerveFusionInitialized = false; // Allow re-init on next open
    };

    // Forward user input to backend
    terminal.onData((data) => {
        if (terminalWs && terminalWs.readyState === WebSocket.OPEN) {
            terminalWs.send(JSON.stringify({ type: 'input', data }));
        }
    });

    // Resize observer
    const resizeObs = new ResizeObserver(() => {
        if (terminalFitAddon) {
            terminalFitAddon.fit();
            if (terminalWs && terminalWs.readyState === WebSocket.OPEN) {
                terminalWs.send(JSON.stringify({ type: 'resize', rows: terminal.rows, cols: terminal.cols }));
            }
        }
    });
    resizeObs.observe(container);
}

function sendTerminalCommand(cmd) {
    if (terminalWs && terminalWs.readyState === WebSocket.OPEN) {
        terminalWs.send(JSON.stringify({ type: 'input', data: cmd + '\n' }));
    }
}

function clearTerminal() {
    if (terminal) terminal.clear();
}

async function fetchToolsArsenal() {
    const grid = document.getElementById('arsenalGrid');
    if (!grid) return;
    try {
        grid.innerHTML = '<div class="col-span-3 text-center py-10 text-slate-500">Montando Arsenal... <span class="material-symbols-outlined animate-spin text-sm ml-2">sync</span></div>';
        const res = await fetch('/tools/available');
        if(!res.ok) throw new Error("Erro ao buscar ferramentas.");
        const data = await res.json();
        
        if(!data.tools || data.tools.length === 0) {
            grid.innerHTML = '<div class="col-span-3 text-center py-10 text-slate-500">Nenhuma ferramenta encontrada no Registry.</div>';
            return;
        }
        
        let html = '';
        data.tools.forEach(t => {
            const isOffensive = t.name.includes("bash") || t.name.includes("shell") || t.name.includes("exe");
            const iconColor = isOffensive ? 'text-amber-500' : 'text-blue-400';
            const iconBg = isOffensive ? 'bg-amber-500/10 border-amber-500/20' : 'bg-blue-500/10 border-blue-500/20';
            const iconName = isOffensive ? 'warning' : 'build';
            
            html += `
                <div class="p-6 bg-slate-900/40 rounded-2xl border border-white/5 backdrop-blur-sm shadow-xl hover:bg-slate-800/60 transition-all group relative overflow-hidden">
                    <div class="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
                        <span class="material-symbols-outlined text-8xl ${iconColor}">${iconName}</span>
                    </div>
                    <div class="flex items-center gap-4 mb-4 relative z-10">
                        <div class="w-12 h-12 rounded-xl ${iconBg} flex items-center justify-center border group-hover:scale-110 transition-transform">
                            <span class="material-symbols-outlined ${iconColor}">${iconName}</span>
                        </div>
                        <div>
                            <h3 class="text-white font-bold text-sm tracking-wide ${iconColor}">${t.name}</h3>
                            <span class="px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-widest ${isOffensive ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'} border mt-1 inline-block">
                                ${isOffensive ? 'Restrita' : 'Standard'}
                            </span>
                        </div>
                    </div>
                    <p class="text-slate-400 text-xs leading-relaxed relative z-10 font-body">${t.description}</p>
                </div>
            `;
        });
        grid.innerHTML = html;
        
    } catch (e) {
        grid.innerHTML = `<div class="col-span-3 text-center py-10 text-rose-500">Falha ao carregar Arsenal: ${e.message}</div>`;
    }
}
function showMemory() {
    setActivePanel('memory');
    fetchMemoryVault();
}
async function fetchMemoryVault() {
    const grid = document.getElementById('memoryGrid');
    if (!grid) return;
    try {
        grid.innerHTML = '<div class="col-span-3 text-center py-10 text-slate-500">Acessando Rede Neural... <span class="material-symbols-outlined animate-spin text-sm ml-2">sync</span></div>';
        const res = await fetch('/memory/long-term');
        if(!res.ok) throw new Error("Erro de conexão com o Kernel.");
        const data = await res.json();
        
        // Handle case where memory object might be nested or empty
        const mem = data.memory || {};
        
        const categories = [
            { id: 'preferences', label: 'Preferências', icon: 'favorite', color: 'text-pink-400', bg: 'bg-pink-500/10 border-pink-500/20' },
            { id: 'facts', label: 'Fatos & Rede Neural', icon: 'lightbulb', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
            { id: 'recurrent_tasks', label: 'Rotinas Ativas', icon: 'update', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' }
        ];

        let html = '';
        categories.forEach(cat => {
            const items = mem[cat.id] || [];
            let itemsHtml = items.length > 0 
                ? items.map((text, idx) => `
                    <li class="flex items-start gap-3 p-3 bg-slate-800/20 rounded-xl border border-white/5 text-xs text-slate-300 font-body mb-3 transition-all hover:bg-slate-800/40 group/item">
                        <span class="material-symbols-outlined text-[16px] ${cat.color} shrink-0 mt-0.5">adjust</span>
                        <span class="flex-1">${text}</span>
                        <div class="flex gap-2 opacity-0 group-hover/item:opacity-100 transition-opacity">
                            <button onclick="editMemory('${cat.id}', ${idx}, '${text.replace(/'/g, "\\'")}')" class="text-slate-500 hover:text-blue-400 transition-colors">
                                <span class="material-symbols-outlined text-sm">edit</span>
                            </button>
                            <button onclick="removeMemory('${cat.id}', ${idx})" class="text-slate-500 hover:text-rose-500 transition-colors">
                                <span class="material-symbols-outlined text-sm">delete</span>
                            </button>
                        </div>
                    </li>`).join('')
                : `<li class="text-xs text-slate-600 italic px-2">Este setor da rede neural está vazio.</li>`;
            
            html += `
                <div class="p-6 bg-slate-900/40 rounded-2xl border border-white/5 backdrop-blur-md shadow-2xl flex flex-col max-h-[500px] group transition-all hover:border-white/10">
                    <div class="flex items-center gap-4 mb-5 border-b border-white/5 pb-4">
                        <div class="w-12 h-12 rounded-2xl ${cat.bg} flex items-center justify-center border shadow-inner transition-transform group-hover:scale-110">
                            <span class="material-symbols-outlined ${cat.color} text-xl">${cat.icon}</span>
                        </div>
                        <div>
                            <h3 class="text-white font-bold tracking-wide text-sm">${cat.label}</h3>
                            <p class="text-[10px] text-slate-500 uppercase font-black tracking-tighter">Sector Active</p>
                        </div>
                    </div>
                    <ul class="flex-1 overflow-y-auto custom-scrollbar pr-3 space-y-1">
                        ${itemsHtml}
                    </ul>
                </div>
            `;
        });
        
        grid.innerHTML = html;
    } catch(e) {
        grid.innerHTML = `<div class="col-span-3 text-center py-16 bg-rose-500/10 border border-rose-500/20 rounded-2xl">
            <div class="relative inline-block mb-4">
                <span class="material-symbols-outlined text-rose-500 text-6xl">cloud_off</span>
                <span class="absolute top-0 right-0 w-3 h-3 bg-rose-500 rounded-full animate-ping"></span>
            </div>
            <div class="text-rose-400 font-black text-lg tracking-tight uppercase">Memory Vault Offline</div>
            <div class="text-rose-500/60 text-xs mt-2 font-mono">${e.message}</div>
            <button onclick="fetchMemoryVault()" class="mt-6 px-6 py-2.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all border border-rose-500/30">Re-Sync Memory Base</button>
        </div>`;
    }
}

// --- Memory CRUD Logic ---
async function editMemory(category, index, oldText) {
    const newText = prompt(`Editar memória (${category}):`, oldText);
    if (newText === null || newText === oldText) return;
    
    try {
        const res = await fetch('/memory/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, index, content: newText })
        });
        if (res.ok) fetchMemoryVault();
    } catch (e) {
        console.error("Falha ao editar memória:", e);
    }
}

async function removeMemory(category, index) {
    if (!confirm("Tem certeza que deseja remover esta memória? Ela será deletada permanentemente da rede neural.")) return;
    
    try {
        const res = await fetch('/memory/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, index })
        });
        if (res.ok) fetchMemoryVault();
    } catch (e) {
        console.error("Falha ao remover memória:", e);
    }
}

// --- Hands-Free Voice Logic ---
async function toggleHandsFree() {
    const btn = document.getElementById('voiceControl');
    const status = document.getElementById('voiceStatus');
    const indicator = document.getElementById('voiceIndicator');
    
    if (isHandsFree) {
        isHandsFree = false;
        stopRecording();
        btn.classList.remove('bg-amber-500/30', 'border-amber-500/50', 'animate-pulse');
        status.classList.replace('bg-emerald-500', 'bg-slate-500');
        indicator.classList.add('hidden');
    } else {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            isHandsFree = true;
            startRecording(stream);
            btn.classList.add('bg-amber-500/30', 'border-amber-500/50', 'animate-pulse');
            status.classList.replace('bg-slate-500', 'bg-emerald-500');
            indicator.classList.remove('hidden');
        } catch (err) {
            console.error("Mic access denied:", err);
            alert("Acesso ao microfone negado.");
        }
    }
}

async function addMemoryPrompt() {
    const category = prompt("Selecione a Categoria (preferences, facts, recurrent_tasks):", "preferences");
    if (!['preferences', 'facts', 'recurrent_tasks'].includes(category)) return alert("Categoria inválida.");
    const content = prompt("Digite o conteúdo da memória:");
    if (!content) return;
    
    try {
        const res = await fetch('/memory/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, content })
        });
        if (res.ok) fetchMemoryVault();
    } catch (e) {
        console.error("Falha ao adicionar memória:", e);
    }
}

function startRecording(stream) {
    // Correct mimeType for most browsers supporting Opus
    const options = { mimeType: 'audio/webm;codecs=opus' };
    if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options.mimeType = 'audio/webm';
    }
    
    mediaRecorder = new MediaRecorder(stream, options);
    audioChunks = [];
    
    mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
            audioChunks.push(event.data);
        }
    };
    
    mediaRecorder.onstop = async () => {
        if (audioChunks.length === 0) return;
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        sendVoiceMessage(audioBlob);
        
        // Stop all tracks to release the microphone after recording stops
        stream.getTracks().forEach(track => track.stop());
    };
    
    // Start with a timeslice to ensure dataavailable fires often and fills audioChunks
    mediaRecorder.start(1000); 
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }
}

async function sendVoiceMessage(blob) {
    if (!blob || blob.size === 0) return;
    
    // UI Visual feedback
    const btn = document.getElementById('voiceControl');
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<span class="material-symbols-outlined animate-spin text-amber-400">sync</span>';
    
    try {
        const res = await fetch('/voice_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/octet-stream' }, // Send as binary stream
            body: blob 
        });
        
        const data = await res.json();
        if (data.transcription) {
            userInput.value = data.transcription;
            // Pulse the input to show it received text
            userInput.classList.add('ring-2', 'ring-blue-500');
            setTimeout(() => userInput.classList.remove('ring-2', 'ring-blue-500'), 1000);
            
            if (data.transcription.length > 5) sendMessage();
        }
    } catch (e) {
        console.error("Voice sync failed:", e);
    } finally {
        btn.innerHTML = originalContent;
    }
}


function showProviders() {
    setActivePanel('providers');
    loadProvidersConfig();
}
function showIntegrations() {
    setActivePanel('integrations');
    loadIntegrationsConfig();
}
function showTasks() { 
    setActivePanel('tasks'); 
    loadTasks();
    loadGoals();
    loadCustomAgents();
}
function showObservability() { 
    setActivePanel('observability'); 
    // Ensure Map is initialized with correct dimensions when shown,
    // then immediately populate with live data (or seed fallback).
    setTimeout(() => {
        initNeuralMap();
        fetch('/observability')
            .then(r => r.json())
            .then(data => {
                if (data.graph && data.graph.nodes && data.graph.nodes.length > 0) {
                    updateNeuralMap(data.graph);
                } else {
                    updateNeuralMap({ nodes: [{ id: 'Arkanis', status: 'running' }, { id: 'Orchestrator', status: 'idle' }], links: [{ source: 'Arkanis', target: 'Orchestrator', last_interaction: 'boot', last_interaction_ms: Date.now() }], task_holder: 'Arkanis' });
                }
            })
            .catch(() => {
                updateNeuralMap({ nodes: [{ id: 'Arkanis', status: 'running' }], links: [], task_holder: 'Arkanis' });
            });
    }, 120);

    fetchObservabilityData();
    fetchSystemLogs();
    fetchTimeline();

    // Start polling
    if (observabilityInterval) clearInterval(observabilityInterval);
    observabilityInterval = setInterval(() => {
        fetchObservabilityData();
        fetchSystemLogs();
        fetchTimeline();
    }, 3000);
}

// Stop polling when leaving observability
function stopObservabilityPolling() {
    if (observabilityInterval) {
        clearInterval(observabilityInterval);
        observabilityInterval = null;
    }
}

// Intercept setActivePanel to manage polling and UI refreshes
const originalSetActivePanel = setActivePanel;
setActivePanel = function(panelId) {
    if (panelId !== 'observability' && panelId !== 'devCenter') stopObservabilityPolling();
    
    // UI FIX: Restart Neural Map if switching to observability
    if (panelId === 'observability') {
        if (!neuralGraph.simulation) {
            initNeuralMap();
        } else {
            neuralGraph.simulation.alpha(1).restart();
            // Force a tiny delay then trigger resize event to fix D3 container sizing
            setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
        }
    }
    
    originalSetActivePanel(panelId);
};

async function loadTasks() {
    try {
        const response = await fetch('/tasks');
        const data = await response.json();
        renderTasks(data.tasks);
    } catch (e) {
        console.error('Failed to load tasks', e);
    }
}

async function loadCustomAgents() {
    try {
        const response = await fetch('/agents');
        const data = await response.json();
        const customAgentsContainer = document.getElementById('customAgentsListContainer');
        if (!customAgentsContainer) return;
        
        // Filter out system agents if you want, or show them visually distinct. 
        // For now, let's just show all custom created from the registry.
        const agents = data.agents || {};
        
        let html = '';
        for (let aId in agents) {
            const a = agents[aId];
            if (a.id === 'auto_heal_agent' || a.id === 'architect_agent' || a.id === 'dev_agent' || a.id === 'telemetry_agent') continue; // core agents
            
            html += `
                <div class="bg-gradient-to-br from-[#0c051a] to-slate-900/40 p-5 rounded-2xl border border-purple-500/20 shadow-lg relative group overflow-hidden flex flex-col gap-3">
                    <div class="absolute inset-0 bg-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <div class="flex items-start justify-between relative z-10">
                        <div class="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center shrink-0">
                            <span class="material-symbols-outlined text-purple-400">smart_toy</span>
                        </div>
                        <div class="flex flex-col items-end">
                            <span class="px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-widest ${a.status === 'RUNNING' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : (a.status === 'PAUSED' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : 'bg-slate-500/20 text-slate-400 border-slate-500/30')} border inline-block">
                                ${a.status}
                            </span>
                            <div class="flex items-center gap-1 mt-1">
                                <button onclick="controlCustomAgent('${a.id}', 'pause')" class="text-slate-500 hover:text-amber-400 p-1 transition-colors" title="Pause"><span class="material-symbols-outlined text-[14px]">pause</span></button>
                                <button onclick="controlCustomAgent('${a.id}', 'resume')" class="text-slate-500 hover:text-emerald-400 p-1 transition-colors" title="Resume"><span class="material-symbols-outlined text-[14px]">play_arrow</span></button>
                                <button onclick="controlCustomAgent('${a.id}', 'stop')" class="text-slate-500 hover:text-rose-400 p-1 transition-colors" title="Stop"><span class="material-symbols-outlined text-[14px]">stop</span></button>
                            </div>
                        </div>
                    </div>
                    <div class="relative z-10">
                        <h4 class="text-white font-bold text-sm tracking-wide truncate" title="${a.id}">${a.id}</h4>
                        <p class="text-purple-300 text-[10px] font-bold uppercase tracking-widest mt-0.5">${a.role || 'Agent'}</p>
                    </div>
                </div>
            `;
        }
        
        if (html === '') {
            html = '<div class="col-span-3 text-slate-500 text-sm py-4 border border-white/5 rounded-xl text-center border-dashed font-mono">Nenhum agente customizado forjado.</div>';
        }
        
        customAgentsContainer.innerHTML = html;
        
    } catch(e) {
        console.error('Failed to load custom agents', e);
    }
}

async function controlCustomAgent(agentId, action) {
    try {
        await fetch(`/agents/${agentId}/${action}`, { method: 'POST' });
        loadCustomAgents();
    } catch(e) {
         console.error('Failed to control agent', e);
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

window.applyBlueprint = function(type) {
    const desc = document.getElementById('newTaskDesc');
    const interval = document.getElementById('newTaskInterval');
    const condition = document.getElementById('newTaskCondition');
    
    if (type === 'web_monitor') {
        desc.value = "Abra uma aba de navegador, vá no Google, pesquise as últimas notícias de Inteligência Artificial e coloque um summary no log. Use o terminal para logar as descobertas.";
        interval.value = "600";
        condition.value = "Finalizar se houver erro absurdo no site";
    } else if (type === 'system_audit') {
        desc.value = "Audite o código do sistema e as interações recentes para sugerir melhorias de arquitetura, coloque a resposta no sistema de sugestões.";
        interval.value = "1800";
        condition.value = "Nunca parar";
    } else if (type === 'custom') {
        desc.value = "";
        interval.value = "300";
        condition.value = "";
    }
};

function renderTasks(tasks) {
    if (!tasksListContainer) return;
    tasksListContainer.innerHTML = '';
    
    if (tasks.length === 0) {
        tasksListContainer.innerHTML = '<div class="text-[10px] text-slate-500 italic p-4 bg-[#02050A] border border-white/5 rounded-xl col-span-full text-center">Engine is idle. No routines are currently executing.</div>';
        return;
    }
    
    tasks.forEach(task => {
        const card = document.createElement('div');
        card.className = 'group flex flex-col relative bg-[#02050A] rounded-2xl border border-white/5 hover:border-blue-500/30 transition-all p-5 shadow-lg overflow-hidden';
        
        let statusColor = 'text-blue-400 bg-blue-500/10 border-blue-500/20';
        let statusIcon = 'memory';
        let statusPulse = '';
        
        if (task.status === 'running') {
            statusColor = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
            statusIcon = 'autorenew';
            statusPulse = '<span class="absolute -top-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full animate-ping opacity-75"></span><span class="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full"></span>';
            card.classList.add('shadow-[0_0_15px_rgba(16,185,129,0.1)]');
        } else if (task.status === 'stopped') {
            statusColor = 'text-slate-400 bg-slate-500/10 border-slate-500/20';
            statusIcon = 'stop_circle';
        }
        
        let logsHtml = '';
        if (task.recent_logs && task.recent_logs.length > 0) {
            logsHtml = '<div class="mt-4 bg-[#050B14] rounded-lg p-3 border border-white/5 shadow-inner">';
            logsHtml += '<div class="text-[8px] uppercase tracking-widest text-slate-500 mb-2 font-bold select-none flex items-center justify-between"><span>Live Process Output</span><span>' + task.run_count + ' ITER</span></div>';
            logsHtml += '<div class="text-[10px] font-mono text-slate-400 space-y-1 h-16 overflow-y-auto custom-scrollbar pr-2">';
            task.recent_logs.forEach(l => {
                logsHtml += `<div><span class="text-blue-500 opacity-60 mr-1">[${l.time}]</span> <span class="text-blue-200/80">${l.message}</span></div>`;
            });
            logsHtml += '</div></div>';
        }

        card.innerHTML = `
            <div class="absolute inset-0 bg-gradient-to-b from-white/[0.02] to-transparent pointer-events-none"></div>
            ${statusPulse}
            
            <div class="flex items-start justify-between relative z-10">
                <div class="flex-1 pr-4">
                    <h4 class="font-bold text-white text-xs leading-tight mb-2 tracking-wide font-headline">
                        ${task.description}
                    </h4>
                    <div class="flex flex-wrap items-center gap-2 mb-3">
                        <span class="px-1.5 py-0.5 rounded text-[8px] uppercase tracking-widest font-black ${statusColor} border flex items-center gap-1"><span class="material-symbols-outlined text-[10px]">${statusIcon}</span> ${task.status}</span>
                        ${task.auto_generated ? '<span class="px-1.5 py-0.5 rounded text-[8px] uppercase tracking-widest font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">Auto</span>' : ''}
                        <span class="px-1.5 py-0.5 rounded text-[8px] uppercase tracking-widest font-bold bg-slate-500/10 text-slate-400 border border-slate-500/20">${task.interval}s Cooldown</span>
                    </div>
                </div>
                <div class="flex items-center">
                    ${task.status !== 'stopped' ? `<button onclick="stopTask('${task.id}')" class="w-8 h-8 flex items-center justify-center rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500 hover:text-white transition-all shadow-md group-hover:scale-105" title="Kill Task"><span class="material-symbols-outlined text-sm">power_settings_new</span></button>` : ''}
                </div>
            </div>
            
            <div class="grid grid-cols-2 gap-2 text-[9px] uppercase tracking-wider text-slate-500 font-bold border-t border-white/5 pt-3 mt-auto relative z-10">
                <div>LAST: <span class="text-slate-300 font-mono">${task.last_run ? task.last_run.split(' ')[1] : 'PENDING'}</span></div>
                <div class="text-right">NEXT: <span class="text-slate-300 font-mono">${task.next_run ? task.next_run.split(' ')[1] : 'PENDING'}</span></div>
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
        newTaskGoalId.innerHTML = '<option value="">Sem vínculo matricial superior</option>';
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
        goalsListContainer.innerHTML = '<div class="text-[10px] text-slate-500 italic p-4 bg-[#02050A] border border-white/5 rounded-xl col-span-full">No active global goals.</div>';
        return;
    }

    goals.forEach(goal => {
        const card = document.createElement('div');
        card.className = 'group relative overflow-hidden bg-gradient-to-b from-slate-900/60 to-[#02050A] rounded-2xl border border-white/5 hover:border-blue-500/20 transition-all p-5 shadow-lg';
        
        let statusColor = 'text-emerald-400';
        let statusBg = 'bg-emerald-500';
        let icon = 'flag_circle';
        
        if (goal.status === 'paused') {
            statusColor = 'text-amber-400';
            statusBg = 'bg-amber-500';
            icon = 'pause_circle';
        }
        if (goal.status === 'completed') {
            statusColor = 'text-blue-400';
            statusBg = 'bg-blue-500';
            icon = 'check_circle';
        }

        card.innerHTML = `
            <div class="absolute inset-0 bg-[#050B14] opacity-50 z-0"></div>
            
            <div class="flex items-start justify-between relative z-10 mb-4">
                <div class="flex-1 pr-6">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="material-symbols-outlined text-sm ${statusColor}">${icon}</span>
                        <h4 class="font-bold text-white text-sm tracking-wide">${goal.description}</h4>
                    </div>
                    <div class="text-[9px] uppercase tracking-widest font-bold text-slate-500 flex items-center gap-3">
                        <span class="flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-slate-600"></span> ID: ${goal.id.substring(0,6)}</span>
                        <span class="flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full ${statusBg}"></span> ${goal.status}</span>
                        <span class="text-purple-400 border border-purple-500/30 px-1 rounded">LVL: ${goal.priority}</span>
                    </div>
                </div>
                ${goal.status !== 'completed' ? `<button onclick="updateGoalStatus('${goal.id}', 'completed')" class="opacity-0 group-hover:opacity-100 transition-opacity bg-blue-600/10 text-blue-400 hover:bg-blue-600 border border-blue-600/30 hover:text-white px-2 py-1 rounded-lg text-[9px] font-bold tracking-widest uppercase">Seal</button>` : ''}
            </div>
            
            <div class="relative z-10 bg-black/40 p-3 rounded-xl border border-white/5">
                <div class="flex justify-between text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">
                    <span>Progression Matrix</span>
                    <span class="text-white">${goal.progress}%</span>
                </div>
                <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-blue-600 to-cyan-400 shadow-[0_0_10px_rgba(56,189,248,0.5)] transition-all duration-1000" style="width: ${goal.progress}%"></div>
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
        showNerveFusion();
    });
}

if (navDevCenter) {
    navDevCenter.addEventListener('click', (e) => {
        e.preventDefault();
        showDevCenter();
    });
}

if (navArsenal) {
    navArsenal.addEventListener('click', (e) => {
        e.preventDefault();
        showArsenal();
    });
}

if (navMemory) {
    navMemory.addEventListener('click', (e) => {
        e.preventDefault();
        showMemory();
    });
}

if (createTaskBtn) {
    createTaskBtn.addEventListener('click', startTask);
}

if (showCreateGoalModalBtn) {
    showCreateGoalModalBtn.addEventListener('click', createGoal);
}

const showAgentForgeModalBtn = document.getElementById('showAgentForgeModalBtn');
const closeAgentForgeModalBtn = document.getElementById('closeAgentForgeModalBtn');
const agentForgeModal = document.getElementById('agentForgeModal');
const agentForgeForm = document.getElementById('agentForgeForm');

if (showAgentForgeModalBtn) {
    showAgentForgeModalBtn.addEventListener('click', async () => {
        // Load tools list for checkboxes
        const toolsList = document.getElementById('forgeAgentToolsList');
        if(toolsList) {
            toolsList.innerHTML = '<span class="text-xs text-slate-500">Montando...</span>';
            try {
                const res = await fetch('/tools/available');
                const data = await res.json();
                if(data.tools) {
                    let html = '';
                    data.tools.forEach(t => {
                        html += `
                            <label class="flex items-center gap-2 bg-black/40 border border-white/5 rounded-lg px-2 py-1.5 cursor-pointer hover:bg-white/5 transition-colors">
                                <input type="checkbox" value="${t.name}" class="forge-tool-cb rounded text-purple-600 focus:ring-purple-500 focus:ring-1 bg-black border-white/20">
                                <span class="text-[10px] text-white font-mono">${t.name}</span>
                            </label>
                        `;
                    });
                    toolsList.innerHTML = html;
                }
            } catch(e) {
                toolsList.innerHTML = `<span class="text-xs text-rose-500">Erro: ${e.message}</span>`;
            }
        }
        
        agentForgeModal.classList.remove('hidden');
        setTimeout(() => {
            agentForgeModal.classList.remove('opacity-0');
            document.getElementById('agentForgeModalContent').classList.remove('scale-95');
        }, 10);
    });
}

if (closeAgentForgeModalBtn) {
    closeAgentForgeModalBtn.addEventListener('click', () => {
        agentForgeModal.classList.add('opacity-0');
        document.getElementById('agentForgeModalContent').classList.add('scale-95');
        setTimeout(() => agentForgeModal.classList.add('hidden'), 300);
    });
}

if (agentForgeForm) {
    agentForgeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const agent_id = document.getElementById('forgeAgentId').value.trim();
        const role = document.getElementById('forgeAgentRole').value.trim();
        const persona = document.getElementById('forgeAgentPersona').value.trim();
        
        const cbs = document.querySelectorAll('.forge-tool-cb:checked');
        const allowed_tools = Array.from(cbs).map(cb => cb.value);
        
        const btn = agentForgeForm.querySelector('button[type="submit"]');
        const origText = btn.innerHTML;
        btn.innerHTML = '<span class="material-symbols-outlined animate-spin text-[14px]">sync</span>';
        btn.disabled = true;
        
        try {
            const res = await fetch('/agents/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ agent_id, role, persona, allowed_tools })
            });
            const data = await res.json();
            
            if(!res.ok) throw new Error(data.detail || "Erro desconhecido");
            
            agentForgeForm.reset();
            closeAgentForgeModalBtn.click();
            loadCustomAgents(); // Refresh the list
            
        } catch(err) {
            alert("Falha: " + err.message);
        } finally {
            btn.innerHTML = origText;
            btn.disabled = false;
        }
    });
}


if (saveConfigBtn) {
    saveConfigBtn.addEventListener('click', () => {
        saveProvidersConfig();
    });
}

if (saveIntegrationsBtn) {
    saveIntegrationsBtn.addEventListener('click', () => {
        saveIntegrationsConfig();
    });
}

// --- Elite UI Sidebar Navigation Listeners ---
const sidebarLinks = [
    { id: 'navChat',          action: showChat,             topNav: 'chat' },
    { id: 'navHistory',       action: showHistory,          topNav: null },
    { id: 'navObservability', action: showObservability,    topNav: null },
    { id: 'navTasks',         action: showTasks,            topNav: null },
    { id: 'navMemory',        action: showMemory,           topNav: null },
    { id: 'navArsenal',       action: showArsenal,          topNav: null },
    { id: 'navLogs',          action: showNerveFusion,      topNav: null },
    { id: 'navDevCenter',     action: showDevCenter,        topNav: null },
    { id: 'navProviders',     action: showProviders,        topNav: 'integrations' }
];

sidebarLinks.forEach(link => {
    const el = document.getElementById(link.id);
    if (el) {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            link.action();
            if (link.topNav) updateTopNav(link.topNav);
            // Close mobile drawer if needed (not implemented yet but good for future)
        });
    }
});

const topNavChat = document.getElementById('topNavChat');
const topNavIntegrations = document.getElementById('topNavIntegrations');

if (topNavChat) {
    topNavChat.addEventListener('click', () => {
        showChat();
        updateTopNav('chat');
    });
}

if (topNavIntegrations) {
    topNavIntegrations.addEventListener('click', () => {
        showIntegrations();
        updateTopNav('integrations');
    });
}

function updateTopNav(activeId) {
    if (!topNavChat || !topNavIntegrations) return;
    
    const activeClasses = ['text-blue-600', 'dark:text-blue-400', 'border-b-2', 'border-blue-600', 'dark:border-blue-400', 'pb-1'];
    const inactiveClasses = ['text-slate-500', 'dark:text-slate-400', 'hover:text-slate-800', 'dark:hover:text-slate-200', 'transition-colors'];

    if (activeId === 'chat') {
        topNavChat.classList.add(...activeClasses);
        topNavChat.classList.remove(...inactiveClasses);
        topNavIntegrations.classList.remove(...activeClasses);
        topNavIntegrations.classList.add(...inactiveClasses);
        topNavChat.classList.remove('cursor-pointer');
        topNavIntegrations.classList.add('cursor-pointer');
    } else {
        topNavIntegrations.classList.add(...activeClasses);
        topNavIntegrations.classList.remove(...inactiveClasses);
        topNavChat.classList.remove(...activeClasses);
        topNavChat.classList.add(...inactiveClasses);
        topNavIntegrations.classList.remove('cursor-pointer');
        topNavChat.classList.add('cursor-pointer');
    }
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
    const newHeight = Math.min(userInput.scrollHeight, 192); // 192px is roughly max-h-48
    userInput.style.height = newHeight + 'px';
    userInput.style.overflowY = (userInput.scrollHeight > 192) ? 'auto' : 'hidden';
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

// Legacy log drawer toggle and close buttons removed

// Collapsible Panels (Agentes & Tarefas)
if (governorToggleBtn) {
    governorToggleBtn.addEventListener('click', () => {
        governorBody.classList.toggle('hidden');
        governorChevron.classList.toggle('rotate-180');
    });
}

if (goalsToggleBtn) {
    goalsToggleBtn.addEventListener('click', () => {
        goalsBody.classList.toggle('hidden');
        goalsChevron.classList.toggle('rotate-180');
    });
}

// Suggestions
document.querySelectorAll('.suggestion-card').forEach(card => {
    card.addEventListener('click', () => {
        const action = card.getAttribute('data-action');
        sendMessage(action);
    });
});

// --- 11. Observability (Agent Control Center) Logic ---

// Track previous stats for pop animation
let _prevStats = { total: -1, active: -1, idle: -1, paused: -1, errors: -1 };

async function fetchObservabilityData() {
    try {
        const response = await fetch('/observability');
        const data = await response.json();
        renderObservability(data);
        fetchSystemMetrics(); // Get real hardware metrics
        
        // Update Dev Center Hero if elements exist
        const devLiveAction = document.getElementById('devLiveAction');
        const devHealthPct = document.getElementById('devHealthPct');
        const devAnalysesCount = document.getElementById('devAnalysesCount');
        const devTotalImprovements = document.getElementById('devTotalImprovements');
        const devTimeSaved = document.getElementById('devTimeSaved');

        if (devLiveAction && data.agents) {
            const devAgent = data.agents.find(a => a.id === 'dev_agent');
            if (devAgent) {
                devLiveAction.textContent = devAgent.current_action || "Aguardando escaneamento...";
                if (devAnalysesCount) devAnalysesCount.textContent = devAgent.current_cycle || "...";
                
                // Update Dev Agent Toggle Icon
                const devToggleIcon = document.getElementById('devAgentToggleIcon');
                if (devToggleIcon) {
                    devToggleIcon.textContent = devAgent.status === 'paused' ? 'play_arrow' : 'pause';
                }
            }
        }
        
        // Mocked or derived stats for 'incredible' feel
        if (devHealthPct) {
            const currentHealth = 98.4 + (Math.random() * 0.2); // Just for micro-vibrancy
            devHealthPct.textContent = currentHealth.toFixed(1);
            const bar = document.getElementById('devHealthBar');
            if (bar) bar.style.width = `${currentHealth}%`;
        }
        
        if (devTimeSaved) {
            const totalSugs = (data.agents && data.agents.length > 0) ? 
                data.agents.reduce((acc, a) => acc + (a.current_cycle || 0), 0) : 0;
            devTimeSaved.textContent = (totalSugs * 0.05).toFixed(1); // 3 mins per cycle saved
        }

    } catch (e) {
        console.error("Failed to fetch observability data:", e);
    }
}

async function fetchSystemLogs() {
    try {
        const response = await fetch('/system/logs?lines=40');
        const data = await response.json();
        renderSystemLogs(data.logs);
    } catch (e) { console.error("Logs error:", e); }
}

async function fetchSystemMetrics() {
    try {
        const response = await fetch('/system/metrics');
        const metrics = await response.json();
        if (metrics.status === 'degraded') return;

        // Update CPU
        const cpuPct = metrics.cpu.usage_percent || 0;
        document.getElementById('guardianCpuPercent').textContent = `${cpuPct}%`;
        document.getElementById('guardianCpuBar').style.width = `${cpuPct}%`;
        document.getElementById('guardianCpuModel').textContent = `${metrics.cpu.cores} Cores @ ${metrics.cpu.frequency}MHz`;

        // Update RAM
        const ramPct = metrics.memory.used_percent || 0;
        document.getElementById('guardianRamPercent').textContent = `${ramPct}%`;
        document.getElementById('guardianRamBar').style.width = `${ramPct}%`;
        document.getElementById('guardianRamText').textContent = `${metrics.memory.available_gb}GB / ${metrics.memory.total_gb}GB Avail`;

        // Update Disk
        const diskPct = metrics.disk.used_percent || 0;
        document.getElementById('guardianDiskPercent').textContent = `${diskPct}%`;
        document.getElementById('guardianDiskBar').style.width = `${diskPct}%`;
        document.getElementById('guardianDiskText').textContent = `${metrics.disk.free_gb}GB Free Space`;

        // Update Network & OS
        document.getElementById('guardianNetIn').textContent = `${metrics.network.recv_mb} MB`;
        document.getElementById('guardianNetOut').textContent = `${metrics.network.sent_mb} MB`;
        document.getElementById('guardianOsInfo').textContent = `${metrics.os.system} ${metrics.os.machine}`;

    } catch (e) { console.error("Metrics error:", e); }
}

async function fetchTimeline() {
    try {
        const response = await fetch('/system/timeline');
        const data = await response.json();
        renderAutoHealTimeline(data.timeline);
    } catch (e) { console.error("Timeline error:", e); }
}

function renderSystemLogs(logs) {
    const term = document.getElementById('systemTerminalLogs');
    if (!term || !logs) return;
    
    // Simple diff-based render to avoid flickering
    const currentLines = term.children.length;
    if (logs.length > currentLines - 2) {
        term.innerHTML = ''; // Full refresh for simplicity initially
        logs.forEach(l => {
            const line = document.createElement('div');
            // Basic color coding for terminal
            if (l.includes('[ERROR]')) line.className = 'text-rose-500';
            else if (l.includes('[SUCCESS]')) line.className = 'text-emerald-400';
            else if (l.includes('[WARNING]')) line.className = 'text-amber-400';
            else line.className = 'text-slate-300';
            line.textContent = l;
            term.appendChild(line);
        });
        // Auto-scroll
        const container = term.parentElement;
        container.scrollTop = container.scrollHeight;
    }
}

function renderAutoHealTimeline(timeline) {
    const container = document.getElementById('autoHealTimeline');
    if (!container) return;
    
    if (!timeline || timeline.length === 0) {
        container.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full text-slate-600 opacity-50">
                <span class="material-symbols-outlined text-2xl mb-2">construction</span>
                <p class="text-[10px]">Aguardando intervenções autônomas...</p>
            </div>
        `;
        return;
    }

    container.innerHTML = '<div class="space-y-6 relative ml-2 border-l border-white/5 pl-6">';
    timeline.forEach(item => {
        const div = document.createElement('div');
        div.className = 'relative';
        div.innerHTML = `
            <span class="absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]"></span>
            <div class="text-[10px] text-slate-500 font-mono mb-1">${item.timestamp}</div>
            <div class="text-[11px] text-white font-bold">${item.title}</div>
            <div class="text-[10px] text-slate-400 mt-1 line-clamp-2 italic">${item.description}</div>
            <div class="mt-2 flex items-center gap-2">
                <span class="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[8px] font-bold uppercase tracking-tighter">Fix: ${item.file_path.split('/').pop()}</span>
            </div>
        `;
        container.firstChild.appendChild(div);
    });
}

function getStatusConfig(status) {
    const map = {
        running: { color: 'blue', bg: 'bg-blue-500', text: 'text-blue-400', border: 'border-blue-500/20', bgBadge: 'bg-blue-500/15 text-blue-400', icon: 'play_arrow', label: 'EXECUTANDO' },
        idle:    { color: 'slate', bg: 'bg-slate-500', text: 'text-slate-400', border: 'border-slate-500/20', bgBadge: 'bg-slate-500/15 text-slate-400', icon: 'pause_circle', label: 'IDLE' },
        paused:  { color: 'amber', bg: 'bg-amber-500', text: 'text-amber-400', border: 'border-amber-500/20', bgBadge: 'bg-amber-500/15 text-amber-400', icon: 'pause', label: 'PAUSADO' },
        error:   { color: 'rose', bg: 'bg-rose-500', text: 'text-rose-400', border: 'border-rose-500/20', bgBadge: 'bg-rose-500/15 text-rose-400', icon: 'error', label: 'ERRO' },
    };
    return map[status] || map.idle;
}

function animateStatIfChanged(elId, newValue, key) {
    const el = document.getElementById(elId);
    if (!el) return;
    const prev = _prevStats[key];
    el.innerText = newValue;
    if (prev !== -1 && prev !== newValue) {
        el.classList.remove('stat-pop');
        void el.offsetWidth;
        el.classList.add('stat-pop');
    }
    _prevStats[key] = newValue;
}

function renderObservability(data) {
    // Update Stats with animations
    animateStatIfChanged('obsTotalAgents', data.stats.total, 'total');
    animateStatIfChanged('obsActiveAgents', data.stats.active, 'active');
    animateStatIfChanged('obsIdleAgents', data.stats.idle, 'idle');
    animateStatIfChanged('obsPausedAgents', data.stats.paused, 'paused');
    animateStatIfChanged('obsErrorAgents', data.stats.errors, 'errors');

    // Update Dev Center specific live banner if it exists in DOM
    const devAgent = data.agents.find(a => a.id === 'dev_agent');
    const devStatusContainer = document.getElementById('devAgentStatusContainer');
    const devLiveStatus = document.getElementById('devAgentLiveStatus');
    const devPulse = document.getElementById('devAgentPulse');
    const devControls = document.getElementById('devAgentControls');
    
    if (devAgent && devStatusContainer && devLiveStatus && devPulse) {
        devStatusContainer.classList.remove('hidden');
        if (devControls) devControls.classList.remove('hidden');
        devLiveStatus.textContent = devAgent.current_action || 'Idle';
        devLiveStatus.title = `Detalhes: Ciclo ${devAgent.cycle} | Status: ${devAgent.status.toUpperCase()}`;
        
        if (devAgent.status === 'paused') {
            devPulse.className = 'w-2 h-2 rounded-full bg-amber-500';
            devLiveStatus.className = 'text-xs font-mono text-amber-400 max-w-[250px] truncate animate-none';
            devStatusContainer.className = 'bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-2 flex items-center gap-3 transition-colors';
        } else if (devAgent.status === 'idle') {
            devPulse.className = 'w-2 h-2 rounded-full bg-emerald-500';
            devLiveStatus.className = 'text-xs font-mono text-emerald-400 max-w-[250px] truncate animate-none';
            devStatusContainer.className = 'bg-emerald-500/10 border border-emerald-500/30 rounded-xl px-4 py-2 flex items-center gap-3 transition-colors';
        } else {
            devPulse.className = 'w-2 h-2 rounded-full bg-indigo-500 animate-pulse';
            devLiveStatus.className = 'text-xs font-mono text-indigo-400 max-w-[250px] truncate';
            devStatusContainer.className = 'bg-indigo-500/10 border border-indigo-500/30 rounded-xl px-4 py-2 flex items-center gap-3 transition-colors';
        }
    }

    // Render Rich Agent Cards
    const grid = document.getElementById('obsAgentsGrid');
    grid.innerHTML = '';

    if (data.agents.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full flex flex-col items-center justify-center py-16 text-slate-600">
                <span class="material-symbols-outlined text-4xl mb-3 text-slate-700">smart_toy</span>
                <p class="text-sm font-medium">Nenhum agente registrado</p>
                <p class="text-xs mt-1">Clique em "Novo Agente" para criar um.</p>
            </div>
        `;
    }
    
    data.agents.forEach((agent, i) => {
        const sc = getStatusConfig(agent.status);
        const isActive = agent.status === 'running';
        const isPaused = agent.status === 'paused';
        const isCustom = agent.is_custom;

        // Tool badges HTML
        const toolsHtml = (agent.allowed_tools && agent.allowed_tools.length > 0)
            ? agent.allowed_tools.slice(0, 5).map(t => `<span class="tool-badge">${t}</span>`).join('')
              + (agent.allowed_tools.length > 5 ? `<span class="tool-badge" style="opacity:.5">+${agent.allowed_tools.length - 5}</span>` : '')
            : '<span class="text-[8px] text-slate-600 italic">Todas as ferramentas</span>';

        // Mini-log feed
        const logsHtml = (agent.logs && agent.logs.length > 0)
            ? agent.logs.map(l => {
                const logType = (l.type || 'system').toLowerCase();
                return `<div class="log-line ${logType}"><span class="text-slate-600 mr-1">${l.time || ''}</span> ${l.message || l}</div>`;
              }).join('')
            : '<div class="text-[9px] text-slate-700 italic px-1">Sem atividade recente</div>';

        // Lifecycle control buttons
        let controlsHtml = '';
        if (isActive) {
            controlsHtml = `
                <button class="agent-ctrl-btn pause" title="Pausar agente" onclick="agentPause('${agent.id}')">
                    <span class="material-symbols-outlined text-amber-500 text-[15px]">pause</span>
                </button>
            `;
        } else if (isPaused) {
            controlsHtml = `
                <button class="agent-ctrl-btn resume" title="Retomar agente" onclick="agentResume('${agent.id}')">
                    <span class="material-symbols-outlined text-emerald-500 text-[15px]">play_arrow</span>
                </button>
            `;
        }
        if (isCustom) {
            controlsHtml += `
                <button class="agent-ctrl-btn stop" title="Parar e remover agente" onclick="agentStop('${agent.id}')">
                    <span class="material-symbols-outlined text-rose-500 text-[15px]">stop</span>
                </button>
            `;
        }

        const card = document.createElement('div');
        card.className = `agent-card group bg-slate-900/40 border border-white/5 rounded-3xl relative overflow-hidden transition-all hover:bg-slate-900/60 hover:border-blue-500/20 backdrop-blur-xl hover:shadow-[0_0_30px_rgba(59,130,246,0.1)]`;
        card.style.animationDelay = `${i * 80}ms`;

        card.innerHTML = `
            <!-- Top Status Glow -->
            <div class="absolute top-0 left-0 right-0 h-[3px] z-10 ${isActive ? 'bg-gradient-to-r from-transparent via-blue-500 to-transparent animate-shimmer' : isPaused ? 'bg-gradient-to-r from-transparent via-amber-500/50 to-transparent' : 'bg-transparent'}"></div>

            <div class="p-6 space-y-5">
                <!-- Header: Icon + ID + Status -->
                <div class="flex items-start justify-between gap-4">
                    <div class="flex items-center gap-4 min-w-0">
                        <div class="w-11 h-11 rounded-2xl ${isActive ? 'bg-blue-600/10 border-blue-600/30' : isPaused ? 'bg-amber-600/10 border-amber-600/30' : 'bg-slate-800/40 border-white/5'} border-2 flex items-center justify-center flex-shrink-0 transition-colors">
                            <span class="material-symbols-outlined ${sc.text} text-[20px]" style="font-variation-settings: 'FILL' 1;">${sc.icon}</span>
                        </div>
                        <div class="min-w-0">
                            <h4 class="text-sm font-black text-white/90 truncate uppercase tracking-widest">${agent.id}</h4>
                            <p class="text-[10px] text-slate-500 font-black uppercase tracking-tighter">${agent.role || 'Neural Architecture'}</p>
                        </div>
                    </div>
                </div>

                <!-- Action Tracker -->
                <div class="space-y-3">
                    <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined text-[12px] opacity-40">bolt</span>
                        <p class="text-xs font-bold text-slate-300 truncate">${agent.current_action || 'Standby Mode'}</p>
                    </div>
                    
                    <!-- Progress (simulated live sync) -->
                    <div class="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                        <div class="h-full rounded-full ${isActive ? 'bg-blue-500 w-3/4 animate-shimmer' : isPaused ? 'bg-amber-500/30 w-1/2' : 'w-0'}" style="transition: width 0.8s ease-in-out;"></div>
                    </div>
                </div>

                <!-- Metrics Grid -->
                <div class="grid grid-cols-2 gap-3">
                    <div class="p-2.5 bg-black/20 rounded-xl border border-white/5">
                        <p class="text-[8px] font-black text-slate-600 uppercase tracking-widest mb-1">Compute State</p>
                        <span class="text-[10px] font-bold ${sc.text} uppercase">${sc.label}</span>
                    </div>
                    <div class="p-2.5 bg-black/20 rounded-xl border border-white/5">
                        <p class="text-[8px] font-black text-slate-600 uppercase tracking-widest mb-1">Process Cycle</p>
                        <span class="text-[10px] font-bold text-slate-300 uppercase">${agent.cycle}/5</span>
                    </div>
                </div>

                <!-- Footer: Controls + Diagnostics -->
                <div class="flex items-center justify-between pt-4 border-t border-white/5">
                    <div class="flex items-center gap-1.5 opacity-60 hover:opacity-100 transition-opacity">
                        ${controlsHtml}
                        <button class="w-8 h-8 rounded-lg hover:bg-white/5 text-slate-500 hover:text-white flex items-center justify-center transition-all" onclick="showAgentFullLog('${agent.id}')" title="Audit Logs">
                            <span class="material-symbols-outlined text-base">analytics</span>
                        </button>
                    </div>
                    <div class="flex items-center gap-2 text-[9px] font-black text-slate-600 uppercase tracking-tighter">
                        Visto: ${agent.last_seen}
                        <div class="w-2 h-2 rounded-full ${isActive ? 'bg-blue-500 animate-pulse' : 'bg-slate-700'}"></div>
                    </div>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });

    // Render Events Table
    const tableBody = document.getElementById('obsEventsTable');
    if (data.history.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="px-6 py-12 text-center text-slate-600 italic">Nenhum evento registrado ainda.</td></tr>';
    } else {
        tableBody.innerHTML = '';
        // Show latest first, only reverse a copy
        [...data.history].reverse().forEach(msg => {
            const row = document.createElement('tr');
            row.className = "hover:bg-white/2 transition-colors";
            row.innerHTML = `
                <td class="px-6 py-4 font-mono text-slate-500">${msg.timestamp}</td>
                <td class="px-6 py-4"><span class="bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded text-[10px] font-bold">${msg.from}</span></td>
                <td class="px-6 py-4 font-medium">${msg.type === 'broadcast' ? '📣 Broadcast' : '📨 Direct Message'}</td>
                <td class="px-6 py-4 text-slate-400 max-w-xs truncate">${msg.content}</td>
            `;
            tableBody.appendChild(row);
        });
    }

    // Update Neural Map — only if simulation is ready
    if (data.graph && neuralGraph.simulation) {
        updateNeuralMap(data.graph);
    }
}

// --- Agent Lifecycle Controls ---

async function agentPause(agentId) {
    try {
        const r = await fetch(`/agents/${agentId}/pause`, { method: 'POST' });
        if (r.ok) { 
            fetchObservabilityData();
            showToast(`Agente "${agentId}" pausado.`, 'amber');
        }
    } catch (e) { console.error('Pause failed:', e); }
}

async function agentResume(agentId) {
    try {
        const r = await fetch(`/agents/${agentId}/resume`, { method: 'POST' });
        if (r.ok) { 
            fetchObservabilityData();
            showToast(`Agente "${agentId}" retomado.`, 'emerald');
        }
    } catch (e) { console.error('Resume failed:', e); }
}

async function agentStop(agentId) {
    if (!confirm(`Tem certeza que deseja parar e remover o agente "${agentId}"?`)) return;
    try {
        const r = await fetch(`/agents/${agentId}/stop`, { method: 'POST' });
        if (r.ok) { 
            fetchObservabilityData();
            showToast(`Agente "${agentId}" removido.`, 'rose');
        }
    } catch (e) { console.error('Stop failed:', e); }
}

// Inline toast notification
function showToast(msg, color = 'blue') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-6 right-6 z-[70] flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-bold text-${color}-400 bg-${color}-500/10 border border-${color}-500/20 shadow-2xl backdrop-blur-xl`;
    toast.style.animation = 'cardReveal 0.3s ease-out';
    toast.innerHTML = `<span class="material-symbols-outlined text-sm">check_circle</span> ${msg}`;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, 3000);
}

// Expanded Agent Log Modal
async function showAgentFullLog(agentId) {
    try {
        const r = await fetch(`/agents/${agentId}/logs`);
        const data = await r.json();
        const logs = data.logs || [];

        const overlay = document.createElement('div');
        overlay.className = 'agent-log-overlay';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

        const logsContent = logs.length > 0
            ? logs.map(l => {
                const t = (l.type || 'system').toLowerCase();
                return `<div class="log-line ${t}" style="font-size:11px;padding:3px 8px;"><span class="text-slate-600 mr-2">[${l.time || ''}]</span><span class="uppercase font-bold mr-2 text-[10px]">${t}</span>${l.message || l}</div>`;
              }).join('')
            : '<p class="text-slate-600 italic text-center py-8">Nenhum log disponível.</p>';

        overlay.innerHTML = `
            <div class="bg-slate-900 border border-white/10 rounded-2xl w-full max-w-2xl mx-4 max-h-[75vh] flex flex-col shadow-2xl">
                <div class="flex items-center justify-between px-6 py-4 border-b border-white/5">
                    <div class="flex items-center gap-3">
                        <span class="material-symbols-outlined text-blue-400">terminal</span>
                        <h3 class="text-sm font-bold text-white">Logs — ${agentId}</h3>
                        <span class="text-[9px] font-bold text-slate-500 bg-white/5 px-2 py-0.5 rounded">${logs.length} entradas</span>
                    </div>
                    <button onclick="this.closest('.agent-log-overlay').remove()" class="text-slate-500 hover:text-white transition-colors">
                        <span class="material-symbols-outlined">close</span>
                    </button>
                </div>
                <div class="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-0.5 bg-black/30">${logsContent}</div>
            </div>
        `;
        document.body.appendChild(overlay);
    } catch (e) {
        console.error('Failed to fetch agent logs:', e);
    }
}

// --- Create Agent Modal Logic ---

const createAgentModal = document.getElementById('createAgentModal');
const openCreateAgentBtn = document.getElementById('openCreateAgentModal');
const closeCreateAgentBtn = document.getElementById('closeCreateAgentModal');
const submitCreateAgentBtn = document.getElementById('submitCreateAgent');
const createAgentErr = document.getElementById('createAgentError');

async function loadAvailableTools() {
    const container = document.getElementById('toolCheckboxes');
    if (!container) return;
    try {
        const r = await fetch('/tools/available');
        const data = await r.json();
        const tools = data.tools || [];
        if (tools.length === 0) {
            container.innerHTML = '<p class="text-slate-500 text-xs italic col-span-2">Nenhuma ferramenta registrada.</p>';
            return;
        }
        container.innerHTML = tools.map(t => `
            <label class="flex items-center gap-2 p-1.5 rounded-lg hover:bg-white/5 transition-colors cursor-pointer group">
                <input type="checkbox" value="${t.name}" class="tool-checkbox rounded border-white/10 bg-slate-900 text-blue-500 focus:ring-blue-500 focus:ring-offset-0 w-3.5 h-3.5" />
                <div class="min-w-0">
                    <span class="text-[11px] font-bold text-slate-300 group-hover:text-white">${t.name}</span>
                    <p class="text-[8px] text-slate-600 truncate">${t.description || ''}</p>
                </div>
            </label>
        `).join('');
    } catch (e) {
        container.innerHTML = '<p class="text-rose-400 text-xs col-span-2">Erro ao carregar ferramentas.</p>';
    }
}

function openCreateAgentModalFn() {
    if (!createAgentModal) return;
    loadAvailableTools();
    createAgentModal.classList.remove('hidden');
    createAgentModal.classList.add('flex');
    // Reset form
    document.getElementById('newAgentId').value = '';
    document.getElementById('newAgentRole').value = '';
    document.getElementById('newAgentPersona').value = '';
    if (createAgentErr) createAgentErr.classList.add('hidden');
}

function closeCreateAgentModalFn() {
    if (!createAgentModal) return;
    createAgentModal.classList.add('hidden');
    createAgentModal.classList.remove('flex');
}

async function submitCreateAgentFn() {
    const agentId = document.getElementById('newAgentId').value.trim();
    const role = document.getElementById('newAgentRole').value.trim();
    const persona = document.getElementById('newAgentPersona').value.trim();
    const selectedTools = Array.from(document.querySelectorAll('.tool-checkbox:checked')).map(cb => cb.value);

    if (!agentId || !role) {
        if (createAgentErr) {
            createAgentErr.textContent = 'ID e Função são obrigatórios.';
            createAgentErr.classList.remove('hidden');
        }
        return;
    }

    // Disable button while creating
    submitCreateAgentBtn.disabled = true;
    submitCreateAgentBtn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">sync</span> Criando...';

    try {
        const r = await fetch('/agents/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_id: agentId, role: role, persona: persona, allowed_tools: selectedTools })
        });
        const data = await r.json();
        if (r.ok && data.status === 'success') {
            closeCreateAgentModalFn();
            fetchObservabilityData();
            showToast(`Agente "${agentId}" criado com sucesso!`, 'emerald');
        } else {
            throw new Error(data.detail || 'Erro ao criar agente');
        }
    } catch (e) {
        if (createAgentErr) {
            createAgentErr.textContent = e.message || 'Erro ao criar agente.';
            createAgentErr.classList.remove('hidden');
        }
    } finally {
        submitCreateAgentBtn.disabled = false;
        submitCreateAgentBtn.innerHTML = '<span class="material-symbols-outlined text-sm">rocket_launch</span> Criar e Ativar';
    }
}

// Wire modal buttons
if (openCreateAgentBtn) openCreateAgentBtn.addEventListener('click', openCreateAgentModalFn);
if (closeCreateAgentBtn) closeCreateAgentBtn.addEventListener('click', closeCreateAgentModalFn);
if (submitCreateAgentBtn) submitCreateAgentBtn.addEventListener('click', submitCreateAgentFn);
// Close on backdrop click
if (createAgentModal) {
    createAgentModal.addEventListener('click', (e) => {
        if (e.target === createAgentModal) closeCreateAgentModalFn();
    });
}

// Initial Listeners
navObservability.addEventListener('click', (e) => { 
    e.preventDefault(); 
    showObservability(); 
    updateTopNav('obs');
});
document.getElementById('refreshObservabilityBtn').addEventListener('click', fetchObservabilityData);

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
    const sysLogsPan = document.getElementById('systemLogsPanel');
    if (sysLogsPan && !sysLogsPan.classList.contains('hidden')) {
        loadAuditInsights();
    }
}, 3000);

// Audit System Handlers
async function loadAuditInsights() {
    const container = document.getElementById('sysLogCriticalEvents');
    if (!container) return;
    try {
        const response = await fetch('/suggestions');
        const data = await response.json();
        const suggestions = data.suggestions || [];
        const applied = suggestions.filter(s => s.status !== 'pending').slice(0, 50);
        
        if (applied.length === 0) {
            container.innerHTML = `<div class="p-3 rounded-lg bg-black/40 border border-white/5"><div class="text-[10px] text-slate-500 italic">Nenhum evento auditável aprovado/rejeitado.</div></div>`;
            return;
        }

        container.innerHTML = applied.map(s => `
            <div class="p-3 rounded-xl bg-slate-900/40 border border-white/10 hover:border-emerald-500/30 transition-all group backdrop-blur-md">
                <div class="flex justify-between items-start mb-1">
                    <span class="text-[10px] font-bold text-white tracking-wide">${s.title}</span>
                    <span class="text-[8px] font-bold px-1.5 py-0.5 rounded ${s.status === 'applied' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-500/20 text-slate-400 border border-slate-500/30'} uppercase">${s.status}</span>
                </div>
                <p class="text-[9px] text-slate-400 opacity-80 line-clamp-2">${s.description}</p>
            </div>
        `).join('');
    } catch (e) {
        // Silent fail for polling
    }
}

document.addEventListener('click', (e) => {
    if (e.target.closest('.sys-log-filter')) {
        const btn = e.target.closest('.sys-log-filter');
        const filter = btn.dataset.filter;
        
        document.querySelectorAll('.sys-log-filter').forEach(b => {
             b.classList.remove('bg-blue-600', 'text-white', 'shadow-md', 'shadow-blue-500/20');
             b.classList.add('text-slate-400', 'bg-transparent');
        });
        
        btn.classList.remove('text-slate-400', 'bg-transparent');
        btn.classList.add('bg-blue-600', 'text-white', 'shadow-md', 'shadow-blue-500/20');
        
        const feed = document.getElementById('sysLogFeed');
        if (feed) {
            Array.from(feed.children).forEach(line => {
                if (filter === 'all') {
                    line.style.display = 'flex';
                } else if (filter === 'error') {
                    line.style.display = line.classList.contains('log-error') ? 'flex' : 'none';
                } else if (filter === 'system') {
                    line.style.display = (line.classList.contains('log-system') || line.classList.contains('log-planner')) ? 'flex' : 'none';
                }
            });
        }
    }
});

// --- History Logic ---
async function loadChatHistory() {
    try {
        const response = await fetch('/chat/history');
        const data = await response.json();
        if (data.history && data.history.length > 0) {
            if (welcomeScreen && !welcomeScreen.classList.contains('hidden')) {
                welcomeScreen.classList.add('hidden');
                chatDisplay.innerHTML = `
                    <div class="max-w-4xl mx-auto space-y-8 pb-96" id="messageArea">
                        <div class="flex justify-center py-4 opacity-30 select-none">
                            <img src="assets/logo.png" class="h-8 object-contain filter grayscale invert" alt="Arkanis Logo">
                        </div>
                    </div>`;
            }
            const messageArea = document.getElementById('messageArea') || chatDisplay;

            // Clear previous placeholder if exists
            if (messageArea.id === 'messageArea') {
                 messageArea.innerHTML = '';
            }

            for (const msg of data.history) {
                if (msg.user) addUserMessage(msg.user);
                
                if (msg.agent) {
                    const id = 'hist-' + Date.now() + Math.floor(Math.random() * 1000);
                    const html = `
                        <div class="flex items-start gap-4">
                            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-indigo-500/20">
                                <span class="material-symbols-outlined text-white text-[20px]">bolt</span>
                            </div>
                            <div class="flex-1 min-w-0 pt-1">
                                <h4 class="font-bold text-slate-200 mb-1 flex items-center gap-2">Arkanis <span class="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full border border-indigo-500/20">AGENT</span></h4>
                                <div class="bot-message prose prose-invert max-w-none text-slate-300 text-sm" id="bot-content-${id}">
                                    ${formatResponse(msg.agent)}
                                </div>
                            </div>
                        </div>
                    `;
                    if (messageArea.id === 'messageArea') {
                        messageArea.insertAdjacentHTML('beforeend', html);
                    }
                }
            }
            
            setTimeout(() => {
                chatDisplay.scrollTop = chatDisplay.scrollHeight;
            }, 100);
        }
    } catch (e) {
        console.error('Failed to load chat history', e);
    }
}

// Init
pollStatus();
pollLogs();
fetchModels();
fetchOpenRouterModels();
loadGoals();
loadGovernorState();
loadChatHistory();

// --- Dev Center Logic ---

async function loadSuggestions() {
    if (!suggestionsGrid) return;
    try {
        const response = await fetch('/suggestions');
        const data = await response.json();
        renderSuggestions(data.suggestions || []);
    } catch (e) {
        console.error('Failed to load suggestions', e);
    }
}

function renderSuggestions(suggestions) {
    if (!suggestionsGrid) return;
    
    // Update 'Melhorias' counter in Hero
    const totalImp = document.getElementById('devTotalImprovements');
    if (totalImp) {
        totalImp.textContent = suggestions.filter(s => s.status === 'applied').length;
    }

    // Apply Filter logic
    let filtered = suggestions;
    if (currentSuggestionFilter === 'pending') {
        filtered = suggestions.filter(s => s.status === 'pending');
    } else if (currentSuggestionFilter === 'applied') {
        filtered = suggestions.filter(s => s.status === 'applied' || s.status === 'approved');
    } else if (currentSuggestionFilter === 'rejected') {
        filtered = suggestions.filter(s => s.status === 'rejected');
    }
    
    if (filtered.length === 0) {
        const emptyMsg = {
            'pending': 'Nenhum ponto crítico detectado. O Arkanis está operando em conformidade total de elite.',
            'applied': 'Nenhuma melhoria aplicada ainda. Comece a evoluir o sistema hoje!',
            'rejected': 'Nenhuma sugestão foi descartada. O Maestro aprova sua visão.'
        };
        suggestionsGrid.innerHTML = `
            <div class="col-span-full py-32 text-center text-slate-600 italic flex flex-col items-center gap-6 animate-pulse">
                <span class="material-symbols-outlined text-6xl opacity-10">smart_toy</span>
                <div class="max-w-xs">
                    <p class="text-sm font-bold uppercase tracking-widest text-slate-500 mb-1">Câmara Silenciosa</p>
                    <p class="text-[11px] opacity-60">${emptyMsg[currentSuggestionFilter] || 'Sem dados nesta categoria.'}</p>
                </div>
            </div>
        `;
        return;
    }

    suggestionsGrid.innerHTML = filtered.map(s => {
        const isArch = s.type === 'arch';
        const typeLabel = isArch ? 'MAESTRO' : 'ELITE DEV';
        const typeColor = isArch ? 'text-blue-400 bg-blue-500/10 border-blue-500/20' : 'text-purple-400 bg-purple-500/10 border-purple-500/20';
        const icon = isArch ? 'architecture' : (s.type === 'feature' ? 'rocket_launch' : s.type === 'bug' ? 'bug_report' : 'bolt');
        const iconColor = isArch ? 'text-blue-400' : 'text-purple-400';
        
        // Impact Gauge Logic
        const impact = s.priority === 'high' ? 'Crítico' : 'Otimização';
        const impactColor = s.priority === 'high' ? 'text-rose-400' : 'text-sky-400';
        const impactIcon = s.priority === 'high' ? 'exclamation' : 'trending_up';

        return `
            <div class="evolution-card rounded-3xl p-7 flex flex-col gap-5 relative group overflow-hidden">
                <!-- Sparkle Glow -->
                <div class="absolute -top-12 -right-12 w-24 h-24 bg-blue-500/10 blur-3xl group-hover:bg-blue-500/20 transition-all pointer-events-none"></div>
                
                <div class="flex items-start justify-between relative z-10">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-center group-hover:border-blue-500/30 transition-all">
                            <span class="material-symbols-outlined ${iconColor} text-2xl">${icon}</span>
                        </div>
                        <div>
                            <div class="flex items-center gap-2 mb-0.5">
                                <h4 class="font-black text-white text-sm tracking-tight">${s.title}</h4>
                            </div>
                            <span class="text-[9px] font-black ${typeColor} px-2 py-0.5 rounded border uppercase tracking-wider">${typeLabel}</span>
                        </div>
                    </div>
                    <div class="flex flex-col items-end gap-1">
                         <span class="text-[8px] font-mono text-slate-600">MOD: ${s.id.substring(0,6)}</span>
                         <div class="flex items-center gap-1 ${impactColor} text-[9px] font-bold uppercase tracking-tighter">
                             <span class="material-symbols-outlined text-[10px]">${impactIcon}</span>
                             ${impact}
                         </div>
                    </div>
                </div>

                <p class="text-[12px] text-slate-400 leading-relaxed font-medium line-clamp-3">${s.description}</p>

                <!-- Premium Code Block -->
                <div class="code-preview-glass rounded-2xl p-4 border border-white/5 group-hover:border-white/10 transition-all">
                    <pre class="text-[10px] text-blue-300/80 font-mono overflow-x-auto custom-scrollbar-thin"><code>${s.code_preview ? s.code_preview.replace(/</g, '&lt;').replace(/>/g, '&gt;') : '// Analisando lógica complexa...'}</code></pre>
                </div>

                <div class="flex items-center gap-3 mt-2">
                    <button onclick="applyImprovement(event, '${s.id}')" class="flex-[2] bg-white text-slate-950 text-[11px] font-black py-2.5 rounded-xl transition-all hover:bg-blue-400 hover:text-white shadow-lg active:scale-95 flex items-center justify-center gap-2">
                        <span class="material-symbols-outlined text-sm">auto_fix_high</span>
                        APLICAR EVOLUÇÃO
                    </button>
                    <button onclick="suggestionAction('${s.id}', 'reject')" class="flex-1 bg-white/5 hover:bg-white/10 text-slate-400 text-[11px] font-bold py-2.5 rounded-xl transition-all border border-white/5 flex items-center justify-center gap-1">
                        DESCARTE
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Wrapper for extra feedback
async function applyImprovement(event, id) {
    const btn = event.currentTarget;
    if (btn.disabled) return;
    
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="material-symbols-outlined text-sm animate-spin">sync</span> PROCESSANDO...`;
    btn.classList.add('opacity-50', 'cursor-not-allowed');

    showToast('Iniciando Evolução de Sistema...', 'blue');
    
    try {
        await suggestionAction(id, 'approve');
    } finally {
        // Only restore if it's still in the DOM (though loadSuggestions usually replaces it)
        if (document.body.contains(btn)) {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }
}

async function suggestionAction(id, action) {
    try {
        const response = await fetch(`/suggestions/${id}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action })
        });
        const data = await response.json();
        if (data.status === 'success') {
            showToast(action === 'approve' ? 'Melhoria aplicada com sucesso!' : 'Sugestão ignorada.', action === 'approve' ? 'emerald' : 'slate');
            setTimeout(loadSuggestions, 500); // Small delay for visual comfort
        } else {
            showToast('Erro: ' + (data.detail || 'Falha na operação'), 'rose');
        }
    } catch (e) {
        console.error('Failed to act on suggestion', e);
        showToast('Erro ao processar sugestão.', 'rose');
    }
}

function setSuggestionFilter(filter) {
    currentSuggestionFilter = filter;
    
    // Update active button state
    ['Pending', 'Applied', 'Rejected'].forEach(f => {
        const btn = document.getElementById(`filterBtn${f}`);
        if (!btn) return;
        if (f.toLowerCase() === filter) {
            btn.classList.add('bg-blue-500', 'text-white', 'shadow-lg', 'shadow-blue-500/20');
            btn.classList.remove('text-slate-400', 'hover:text-white', 'hover:bg-white/5');
        } else {
            btn.classList.remove('bg-blue-500', 'text-white', 'shadow-lg', 'shadow-blue-500/20');
            btn.classList.add('text-slate-400', 'hover:text-white', 'hover:bg-white/5');
        }
    });
    
    loadSuggestions();
}

// --- 6. Neural Map (D3 Graph Visualization) ---

function initNeuralMap() {
    const container = document.getElementById('neuralMapContainer');
    if (!container) return;

    // getBoundingClientRect is more reliable than clientWidth during CSS transitions
    const rect = container.getBoundingClientRect();
    const width = rect.width > 0 ? rect.width : (container.offsetWidth || 900);
    const height = rect.height > 0 ? rect.height : (container.offsetHeight || 450);

    // Reset container to avoid duplication
    container.innerHTML = '';

    neuralGraph.svg = d3.select("#neuralMapContainer")
        .append("svg")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("viewBox", [0, 0, width, height])
        .attr("style", "max-width: 100%; height: auto;");

    // Add arrowhead markers for links
    neuralGraph.svg.append("defs").append("marker")
        .attr("id", "arrowhead")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 20)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "#3b82f6");

    neuralGraph.container = neuralGraph.svg.append("g");

    // Zoom/Pan
    neuralGraph.svg.call(d3.zoom()
        .extent([[0, 0], [width, height]])
        .scaleExtent([0.5, 4])
        .on("zoom", ({transform}) => {
            neuralGraph.container.attr("transform", transform);
        }));

    neuralGraph.simulation = d3.forceSimulation()
        .force("link", d3.forceLink().id(d => d.id).distance(150))
        .force("charge", d3.forceManyBody().strength(-400))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("x", d3.forceX(width / 2).strength(0.1))
        .force("y", d3.forceY(height / 2).strength(0.1))
        .alphaTarget(0.02); // Keep nodes slightly moving (not fully static)

    // Start demo bubble animation (only once per page load)
    if (!window._neuralDemoStarted) {
        window._neuralDemoStarted = true;
        setTimeout(startNeuralMapDemo, 2000);
    }
}

function updateNeuralMap(graphData) {
    if (!neuralGraph.simulation) return;

    const { nodes: newNodes, links: newLinks } = graphData;

    // 1. Update Nodes: Preserve positions and velocities
    const nodeMap = new Map(neuralGraph.nodes.map(n => [n.id, n]));
    neuralGraph.nodes = newNodes.map(d => {
        const old = nodeMap.get(d.id);
        if (old) {
            return Object.assign(old, d);
        }
        // Initialize new node position near center to avoid "jumps"
        const container = document.getElementById('neuralMapContainer');
        const width = container ? container.clientWidth : 800;
        const height = container ? container.clientHeight : 400;
        d.x = (width / 2) + (Math.random() - 0.5) * 100;
        d.y = (height / 2) + (Math.random() - 0.5) * 100;
        return d;
    });

    // 2. Update Links
    neuralGraph.links = newLinks.map(l => ({
        source: l.source,
        target: l.target,
        last_interaction: l.last_interaction,
        last_interaction_ms: l.last_interaction_ms
    }));

    const link = neuralGraph.container.selectAll(".link")
        .data(neuralGraph.links, d => `${d.source}-${d.target}`)
        .join("line")
        .attr("class", "link")
        .attr("stroke", "#374151")
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", 2)
        .attr("marker-end", "url(#arrowhead)");

    // 3. NODE UPDATE — D3 enter/update/exit pattern (no html('') wipe)
    const nodeUpdate = neuralGraph.container.selectAll(".node")
        .data(neuralGraph.nodes, d => d.id);

    // EXIT: remove nodes that no longer exist
    nodeUpdate.exit().remove();

    // ENTER: create new node groups only for truly new nodes
    const nodeEnter = nodeUpdate.enter()
        .append("g")
        .attr("class", "node")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    nodeEnter.append("circle")
        .attr("r", 15)
        .attr("fill", d => d.id === 'ALL' ? '#8b5cf6' : (d.status === 'running' ? '#3b82f6' : '#1e293b'))
        .attr("stroke", d => d.status === 'running' ? '#60a5fa' : '#334155')
        .attr("stroke-width", 2)
        .attr("class", "node-circle");

    // ARKANIS SWARM: Active Token Pulse
    nodeEnter.append("circle")
        .attr("r", 15)
        .attr("fill", "none")
        .attr("stroke", "#3b82f6")
        .attr("stroke-width", 0)
        .attr("class", "swarm-token-pulse")
        .style("pointer-events", "none");

    nodeEnter.append("text")
        .attr("dy", "0.35em")
        .attr("text-anchor", "middle")
        .attr("font-family", "Material Symbols Outlined")
        .attr("font-size", "14px")
        .attr("fill", "#fff")
        .text(d => d.id === 'ALL' ? 'hub' : 'smart_toy');

    nodeEnter.append("text")
        .attr("dy", "30px")
        .attr("text-anchor", "middle")
        .attr("font-size", "10px")
        .attr("font-weight", "bold")
        .attr("fill", "#94a3b8")
        .text(d => d.id);

    // UPDATE: refresh colors only, no structural rebuild
    const nodeMerged = nodeEnter.merge(nodeUpdate);
    nodeMerged.select(".node-circle")
        .attr("fill", d => d.id === 'ALL' ? '#8b5cf6' : (d.status === 'running' ? '#3b82f6' : '#1e293b'))
        .attr("stroke", d => d.status === 'running' ? '#60a5fa' : '#334155');

    // ARKANIS SWARM: Update Task Holder Animation
    const taskHolder = graphData.task_holder;
    nodeMerged.select(".swarm-token-pulse")
        .transition().duration(500)
        .attr("stroke-width", d => d.id === taskHolder ? 4 : 0)
        .attr("r", d => d.id === taskHolder ? 22 : 15)
        .style("opacity", d => d.id === taskHolder ? 1 : 0)
        .on("end", function repeat() {
            if (d3.select(this).datum().id === taskHolder) {
                d3.select(this)
                    .transition().duration(1000)
                    .attr("r", 30)
                    .style("opacity", 0)
                    .transition().duration(0)
                    .attr("r", 15)
                    .style("opacity", 1)
                    .on("end", repeat);
            }
        });

    // 4. Pulse active links
    newLinks.forEach(l => {
        const isFresh = (Date.now() - l.last_interaction_ms) < 4000;
        if (isFresh) {
            triggerThoughtTrace(l);
        }

        const line = neuralGraph.container.selectAll(".link")
            .filter(d => (d.source === l.source && d.target === l.target) ||
                         (d.source.id === l.source && d.target.id === l.target));
        
        line.transition().duration(200).attr("stroke", "#60a5fa").attr("stroke-width", 4)
            .transition().duration(1000).attr("stroke", "#374151").attr("stroke-width", 2);
    });

    // 5. Only restart simulation physics if truly new nodes were added
    const existingIds = new Set(nodeMap.keys());
    const hasNewNodes = newNodes.some(n => !existingIds.has(n.id));

    neuralGraph.simulation.nodes(neuralGraph.nodes);
    neuralGraph.simulation.force("link").links(neuralGraph.links);

    if (hasNewNodes) {
        // New topology → warm restart to settle new nodes
        neuralGraph.simulation.alpha(0.6).restart();
    } else {
        // Just sync positions in one silent tick — no physics bounce
        neuralGraph.simulation.tick();
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
        nodeMerged.attr("transform", d => `translate(${d.x},${d.y})`);
    }

    neuralGraph.simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
        nodeMerged.attr("transform", d => `translate(${d.x},${d.y})`);
    });
}

const traceTracking = new Set();
function triggerThoughtTrace(linkData) {
    const key = `${linkData.source}-${linkData.target}-${linkData.last_interaction_ms}`;
    if (traceTracking.has(key)) return;
    traceTracking.add(key);

    const sourceNode = neuralGraph.nodes.find(n => n.id === linkData.source);
    const targetNode = neuralGraph.nodes.find(n => n.id === linkData.target);
    if (!sourceNode || !targetNode) return;

    // Get the current zoom transform applied to the container
    const containerEl = neuralGraph.svg.select("g").node();
    const transform = containerEl ? d3.zoomTransform(neuralGraph.svg.node()) : d3.zoomIdentity;

    // Convert simulation coords → screen coords using current zoom transform
    const sx = transform.applyX(sourceNode.x);
    const sy = transform.applyY(sourceNode.y);
    const tx = transform.applyX(targetNode.x);
    const ty = transform.applyY(targetNode.y);

    // Append particle directly to SVG root (not to zoomed container) so coords match
    const particle = neuralGraph.svg.append("circle")
        .attr("r", 5)
        .attr("fill", "#60a5fa")
        .attr("cx", sx)
        .attr("cy", sy)
        .style("filter", "drop-shadow(0 0 6px #3b82f6)")
        .style("pointer-events", "none");

    // Glow ring
    const ring = neuralGraph.svg.append("circle")
        .attr("r", 8)
        .attr("fill", "none")
        .attr("stroke", "#60a5fa")
        .attr("stroke-width", 1.5)
        .attr("stroke-opacity", 0.5)
        .attr("cx", sx)
        .attr("cy", sy)
        .style("pointer-events", "none");

    particle.transition()
        .duration(1000)
        .ease(d3.easeCubicInOut)
        .attr("cx", tx)
        .attr("cy", ty)
        .on("end", () => particle.remove());

    ring.transition()
        .duration(1000)
        .ease(d3.easeCubicInOut)
        .attr("cx", tx)
        .attr("cy", ty)
        .style("stroke-opacity", 0)
        .on("end", () => ring.remove());

    // Cleanup tracking set
    if (traceTracking.size > 100) {
        traceTracking.delete(Array.from(traceTracking)[0]);
    }
}

// Demo: spawn a bubble between nodes periodically so it always looks alive
function startNeuralMapDemo() {
    setInterval(() => {
        if (neuralGraph.nodes.length < 2) return;
        const links = neuralGraph.links;
        if (links.length === 0) return;
        const randomLink = links[Math.floor(Math.random() * links.length)];
        const src = typeof randomLink.source === 'object' ? randomLink.source.id : randomLink.source;
        const tgt = typeof randomLink.target === 'object' ? randomLink.target.id : randomLink.target;
        triggerThoughtTrace({
            source: src,
            target: tgt,
            last_interaction_ms: Date.now()
        });
    }, 2000);
}


function dragstarted(event) {
    if (!event.active) neuralGraph.simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
}

function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
}

function dragended(event) {
    if (!event.active) neuralGraph.simulation.alphaTarget(0.02);
    event.subject.fx = null;
    event.subject.fy = null;
}

// --- Vision Support (Images) ---

let uploadedImagesArr = []; // Explicitly named to avoid confusion
let uploadedFilesArr = []; // New: universal file attachments

function handleImageSelect(files) {
    if (!files) return;
    Array.from(files).forEach(file => {
        if (!file.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result;
            uploadedImagesArr.push(base64);
            renderImagePreviews();
        };
        reader.readAsDataURL(file);
    });
}

function handleFileSelect(files) {
    if (!files) return;
    Array.from(files).forEach(file => {
        const reader = new FileReader();
        reader.onload = (e) => {
            uploadedFilesArr.push({
                name: file.name,
                type: file.type,
                content: e.target.result // Base64
            });
            renderFilePreviews();
        };
        reader.readAsDataURL(file);
    });
}

function renderImagePreviews() {
    const container = document.getElementById('imagePreviews');
    if (!container) return;
    if (uploadedImagesArr.length > 0) container.classList.remove('hidden');
    else container.classList.add('hidden');
    
    container.innerHTML = uploadedImagesArr.map((src, idx) => `
        <div class="relative w-16 h-16 rounded-lg overflow-hidden border border-white/10 group animate-in fade-in zoom-in duration-200">
            <img src="${src}" class="w-full h-full object-cover" />
            <button onclick="removeImage(${idx})" class="absolute top-0 right-0 p-0.5 bg-black/60 text-white hover:text-rose-400 transition-colors opacity-0 group-hover:opacity-100">
                <span class="material-symbols-outlined text-[14px]">close</span>
            </button>
        </div>
    `).join('');
}

function renderFilePreviews() {
    const container = document.getElementById('filePreviews');
    if (!container) return;
    if (uploadedFilesArr.length > 0) container.classList.remove('hidden');
    else container.classList.add('hidden');

    container.innerHTML = uploadedFilesArr.map((file, idx) => `
        <div class="flex items-center gap-2 px-3 py-1.5 bg-slate-800/80 border border-white/5 rounded-full group animate-in fade-in slide-in-from-left-2 duration-200">
            <span class="material-symbols-outlined text-blue-400 text-[14px]">description</span>
            <span class="text-[11px] text-slate-300 font-bold truncate max-w-[120px]">${file.name}</span>
            <button onclick="removeFile(${idx})" class="text-slate-500 hover:text-rose-400 transition-colors">
                <span class="material-symbols-outlined text-[14px]">close</span>
            </button>
        </div>
    `).join('');
}

function removeImage(idx) {
    uploadedImagesArr.splice(idx, 1);
    renderImagePreviews();
}

function removeFile(idx) {
    uploadedFilesArr.splice(idx, 1);
    renderFilePreviews();
}

function clearAttachments() {
    uploadedImagesArr = [];
    uploadedFilesArr = [];
    renderImagePreviews();
    renderFilePreviews();
}

// --- 10. Robust Elite UI Initialization ---

function initEliteUI() {
    console.log("🚀 [Elite UI] Executing Robust Initialization...");
    
    const attBtn = document.getElementById('attachBtn');
    const imgBtn = document.getElementById('imageBtn');
    const fInput = document.getElementById('fileInput');
    const iInput = document.getElementById('imageInput');

    if (attBtn && fInput) {
        attBtn.onclick = (e) => {
            e.preventDefault();
            console.trace("📎 [Elite UI] Attach button clicked");
            fInput.click();
        };
        fInput.onchange = (e) => handleFileSelect(e.target.files);
    }

    if (imgBtn && iInput) {
        imgBtn.onclick = (e) => {
            e.preventDefault();
            console.trace("🖼️ [Elite UI] Image button clicked");
            iInput.click();
        };
        iInput.onchange = (e) => handleImageSelect(e.target.files);
    }
    
    // ARKANIS V4 ALPHA: Focus Mode Toggle
    const focusBtn = document.getElementById('focusToggleBtn');
    if (focusBtn) {
        focusBtn.onclick = (e) => {
            e.preventDefault();
            toggleFocusMode();
        };
    }
    
    // Navigation
    initSidebarNav();

    // Neural Map Re-init only if container was wiped
    const mapContainer = document.getElementById('neuralMapContainer');
    if (typeof initNeuralMap === 'function' && mapContainer && mapContainer.innerHTML.trim() === '') {
        initNeuralMap();
    }

    console.log("✅ [Elite UI] Bindings Secured.");
}

// Global execution
document.addEventListener('DOMContentLoaded', initEliteUI);
// Frequent re-check to fix any DOM replacement by other agents
if (!window.eliteInitInterval) {
    window.eliteInitInterval = setInterval(initEliteUI, 5000);
}

// Paste support
document.addEventListener('paste', (e) => {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (const item of items) {
        if (item.type.indexOf('image') !== -1) {
            const blob = item.getAsFile();
            if (typeof handleImageSelect === 'function') handleImageSelect([blob]);
        }
    }
});
