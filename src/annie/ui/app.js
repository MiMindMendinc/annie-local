"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const el = {
  main: $("#main"),
  stream: $("#sessionStream"),
  composer: $("#composer"),
  input: $("#input"),
  send: $("#send"),
  mic: $("#mic"),
  stop: $("#stopBtn"),
  orb: $("#orb"),
  voicePill: $("#voicePill"),
  voiceStateText: $("#voiceStateText"),
  presenceCopy: $("#presenceCopy"),
  messageAnnouncement: $("#messageAnnouncement"),
  modelStatus: $("#modelStatus"),
  memoryStatus: $("#memoryStatus"),
  networkStatus: $("#networkStatus"),
  modelDetail: $("#modelDetail"),
  memoryDetail: $("#memoryDetail"),
  networkDetail: $("#networkDetail"),
  voiceDetail: $("#voiceDetail"),
  menuBtn: $("#menuBtn"),
  modelBtn: $("#modelBtn"),
  exportBtn: $("#exportBtn"),
  cfgBtn: $("#cfgBtn"),
  openMemoryBtn: $("#openMemoryBtn"),
  clearBtn: $("#clearBtn"),
  menuDialog: $("#menuDialog"),
  settingsDialog: $("#settingsDialog"),
  memoryDialog: $("#memoryDialog"),
  authDialog: $("#authDialog"),
  authForm: $("#authForm"),
  authEmail: $("#authEmail"),
  authPassword: $("#authPassword"),
  authError: $("#authError"),
  authSubmit: $("#authSubmit"),
  authAccount: $("#authAccount"),
  accountEmail: $("#accountEmail"),
  logoutBtn: $("#logoutBtn"),
  settingsForm: $("#settingsForm"),
  model: $("#model"),
  ollamaUrl: $("#ollamaUrl"),
  voiceUrl: $("#voiceUrl"),
  speakToggle: $("#speakToggle"),
  toolsToggle: $("#toolsToggle"),
  temp: $("#temp"),
  tempVal: $("#tempVal"),
  sys: $("#sys"),
  resetSys: $("#resetSys"),
  memBody: $("#memBody"),
};

const PHASE_VIEW = {
  idle: { label: "Ready", copy: "Here when you’re ready. What’s on your mind?" },
  listening: { label: "Listening", copy: "Browser voice input is active; locality is not verified." },
  thinking: { label: "Thinking", copy: "The configured model is working on your request." },
  speaking: { label: "Speaking", copy: "Voice output is playing. Use Stop at any time." },
  offline: { label: "Model offline", copy: "The app is open, but the configured model is unavailable." },
  error: { label: "Error", copy: "The last operation failed. Details are in the session." },
};

let settings = {
  model: null,
  ollama_url: "http://127.0.0.1:11434",
  voice_url: "http://127.0.0.1:8123",
  temperature: 0.7,
  tools_enabled: true,
  default_doctrine: "",
};
let messages = [];
let abortController = null;
let voiceAbortController = null;
let audioEl = null;
let audioUrl = null;
let finishAudio = null;
let finishSpeech = null;
let activeWaveform = null;
let recognition = null;
let recognitionActive = false;
let recognitionBase = "";
let micSupported = false;
let authRequired = false;
let companion = null;
const dialogReturnTargets = new WeakMap();

function esc(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function formatMessage(text) {
  const parts = String(text).split(/```/);
  let output = "";
  for (let index = 0; index < parts.length; index += 1) {
    if (index % 2 === 1) {
      output += `<pre><code>${esc(parts[index].replace(/^[a-zA-Z0-9_-]*\n/, ""))}</code></pre>`;
    } else {
      output += esc(parts[index]).replace(/`([^`\n]+)`/g, "<code>$1</code>");
    }
  }
  return output;
}

function announce(message) {
  el.messageAnnouncement.textContent = "";
  window.setTimeout(() => {
    el.messageAnnouncement.textContent = message;
  }, 20);
}

function scrollToLatest() {
  window.requestAnimationFrame(() => {
    el.main.scrollTop = el.main.scrollHeight;
  });
}

function formatClock(value) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatLatency(value) {
  if (!Number.isFinite(Number(value))) return "— latency";
  const ms = Number(value);
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

function metricValue(value, suffix) {
  return Number.isFinite(Number(value)) ? `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })} ${suffix}` : `— ${suffix}`;
}

function setBadge(button, text, tone, detail) {
  button.textContent = text;
  button.dataset.tone = tone;
  button.title = detail;
}

function renderRuntime(runtime) {
  const model = runtime.model || {};
  const memory = runtime.memory || {};
  const voice = runtime.voice || {};
  const network = runtime.network || {};

  let modelLabel = "Model: checking";
  let modelTone = "neutral";
  if (model.availability === "unavailable") {
    modelLabel = "Model: offline";
    modelTone = "bad";
  } else if (model.availability === "ready") {
    const labels = {
      device: "Model: local",
      local_container: "Model: container",
      local_network: "Model: LAN route",
      remote: "Model: remote",
      unknown: "Model: ready",
    };
    modelLabel = labels[model.locality] || "Model: ready";
    modelTone = ["device", "local_container"].includes(model.locality) ? "ok" : model.locality === "remote" ? "bad" : "warn";
  }
  const modelDetail = model.availability === "ready"
    ? `${model.name || "Configured model"} is available through a ${model.route || "unknown"} route.`
    : model.reason || "The configured model endpoint is not currently ready.";
  setBadge(el.modelStatus, modelLabel, modelTone, modelDetail);
  el.modelDetail.textContent = modelDetail;

  let memoryLabel = "Memory: checking";
  let memoryTone = "neutral";
  if (memory.backend === "jsonl" && memory.location === "device") {
    memoryLabel = "Memory: local JSONL";
    memoryTone = "ok";
  } else if (memory.backend === "postgresql") {
    memoryLabel = memory.location === "remote" ? "Memory: remote DB" : "Memory: PostgreSQL";
    memoryTone = ["device", "local_container"].includes(memory.location) ? "ok" : memory.location === "remote" ? "bad" : "warn";
  }
  const memoryDetail = memory.backend === "jsonl"
    ? `Conversation history persists in a device file. Knowledge tools are ${memory.knowledge_tools || "unknown"}.`
    : `Conversation history uses PostgreSQL; service location is ${memory.location || "unknown"}. Knowledge tools are ${memory.knowledge_tools || "unknown"}.`;
  setBadge(el.memoryStatus, memoryLabel, memoryTone, memoryDetail);
  el.memoryDetail.textContent = memoryDetail;

  const remoteConfigured = network.claim === "remote_configured";
  const networkLabel = remoteConfigured ? "Network: remote route" : "Network: not verified";
  setBadge(el.networkStatus, networkLabel, remoteConfigured ? "bad" : "warn", network.reason || "Offline operation has not been verified.");
  el.networkDetail.textContent = network.reason || "Offline operation has not been verified.";

  const inputLabel = voice.input === "browser_managed_unverified" ? "browser-managed input (locality unverified)" : voice.input || "unknown input";
  const outputLabels = {
    local_bridge: "local voice bridge",
    local_network_bridge: "local-network voice bridge",
    remote_bridge: "remote voice bridge",
    bridge_unverified: "configured voice bridge (locality unverified)",
    browser_managed_unverified: "browser-managed output (locality unverified)",
  };
  el.voiceDetail.textContent = `Input: ${inputLabel}. Output: ${outputLabels[voice.output] || voice.output || "unknown"}.`;
}

function renderState(state) {
  const session = state.session;
  const phase = PHASE_VIEW[session.phase] ? session.phase : "error";
  const view = PHASE_VIEW[phase];
  el.orb.dataset.phase = phase;
  el.voicePill.dataset.phase = phase;
  el.voiceStateText.textContent = view.label;
  el.voicePill.setAttribute("aria-label", `Annie state: ${view.label}`);
  el.presenceCopy.textContent = session.error?.detail || view.copy;
  el.stop.disabled = authRequired || !session.canStop;
  el.send.disabled = authRequired || phase === "thinking";
  el.input.disabled = authRequired || phase === "thinking";
  el.mic.disabled = authRequired || !micSupported || ["thinking", "speaking"].includes(phase);
  el.modelBtn.disabled = authRequired;
  el.cfgBtn.disabled = authRequired;
  el.openMemoryBtn.disabled = authRequired;
  el.clearBtn.disabled = authRequired;
  el.mic.setAttribute("aria-pressed", phase === "listening" ? "true" : "false");
  el.mic.setAttribute("aria-label", phase === "listening" ? "Stop browser voice input" : "Start browser voice input");
  if (activeWaveform) activeWaveform.classList.toggle("active", phase === "speaking");
  const auth = AnnieState.get("auth");
  el.authAccount.hidden = !auth?.token;
  el.accountEmail.textContent = auth?.user?.email || "Authenticated account";
  renderRuntime(session.runtime);
  companion?.setRuntime(session.runtime);
  companion?.setLocked(authRequired || phase === "thinking");
}

function footerMarkup(metrics, model) {
  return `
    <span>${esc(formatClock(metrics?.completed_at))}</span>
    <span>${esc(metricValue(metrics?.tokens_per_second, "tok/s"))}</span>
    <span>${esc(formatLatency(metrics?.latency_ms))}</span>
    <span>${esc(metricValue(metrics?.token_count, "tok"))}</span>
    <span>${esc(model || "configured model")}</span>`;
}

function addMessage(role, content, options = {}) {
  $("#welcomeCard")?.remove();
  const article = document.createElement("article");
  article.className = `message-card ${role === "user" ? "user" : "assistant"}`;
  article.dataset.raw = content;
  const author = role === "user" ? "You" : "Annie";
  article.innerHTML = `
    <div class="message-head">
      <span class="message-author">${author}</span>
      <button class="copy-button" type="button" aria-label="Copy ${author} message"><svg aria-hidden="true"><use href="#i-copy"></use></svg></button>
    </div>
    <div class="message-content">${formatMessage(content)}</div>
    ${options.toolEvents?.length ? `<div class="tool-events">${options.toolEvents.map((event) => `${event.startsWith("Skipped ") ? "↳" : "✓"} ${esc(event)}`).join("<br>")}</div>` : ""}
    ${role === "assistant" ? '<div class="waveform" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>' : ""}
    <div class="message-footer">${role === "assistant" ? footerMarkup(options.metrics, options.model) : `<span>${esc(formatClock())}</span>`}</div>`;
  $(".copy-button", article).addEventListener("click", async (event) => {
    const button = event.currentTarget;
    try {
      await navigator.clipboard.writeText(content);
      button.setAttribute("aria-label", "Message copied");
      announce("Message copied");
    } catch {
      announce("Copy is unavailable in this browser");
    }
  });
  el.stream.appendChild(article);
  const waveform = $(".waveform", article);
  if (waveform) activeWaveform = waveform;
  messages.push({
    role,
    content,
    created_at: options.metrics?.completed_at || new Date().toISOString(),
    model: options.model || null,
    metrics: options.metrics || null,
    tool_events: options.toolEvents || [],
  });
  scrollToLatest();
  return article;
}

function addSystemMessage(text) {
  const card = document.createElement("div");
  card.className = "system-card";
  card.textContent = text;
  el.stream.appendChild(card);
  scrollToLatest();
  announce(text);
}

function addErrorCard(title, detail) {
  companion?.showView("chat");
  const card = document.createElement("div");
  card.className = "error-card";
  card.innerHTML = `<b>${esc(title)}</b><span>${esc(detail)}</span>`;
  el.stream.appendChild(card);
  scrollToLatest();
  announce(`${title}. ${detail}`);
}

function autosize() {
  el.input.style.height = "auto";
  el.input.style.height = `${Math.min(el.input.scrollHeight, 150)}px`;
}

function openDialog(dialog, focusTarget) {
  const returnTarget = document.activeElement;
  if (returnTarget instanceof HTMLElement && returnTarget !== document.body) {
    dialogReturnTargets.set(dialog, returnTarget);
  }
  if (!dialog.open) dialog.showModal();
  window.setTimeout(() => (focusTarget || $("button, input, select, textarea", dialog))?.focus(), 20);
}

function closeDialog(dialog) {
  if (dialog.open) dialog.close();
  const returnTarget = dialogReturnTargets.get(dialog);
  dialogReturnTargets.delete(dialog);
  if (returnTarget?.isConnected && !returnTarget.disabled) returnTarget.focus();
}

function showAuthGate(message = "Sign in to continue.") {
  authRequired = true;
  el.authError.textContent = message;
  el.authError.hidden = !message;
  renderState({ session: AnnieState.get("session") });
  if (!el.authDialog.open) el.authDialog.showModal();
  window.setTimeout(() => el.authEmail.focus(), 20);
}

async function signIn(email, password) {
  el.authSubmit.disabled = true;
  el.authError.hidden = true;
  try {
    await AnnieApi.login(email, password);
    await loadSettings();
    authRequired = false;
    fillSettings();
    await refreshEngine();
    await companion?.refresh().catch(() => {});
    closeDialog(el.authDialog);
    el.authPassword.value = "";
    renderState({ session: AnnieState.get("session") });
    addSystemMessage("Signed in. This access token will be cleared when the browser session ends.");
    el.input.focus();
  } catch (error) {
    showAuthGate(error.message || "Sign-in failed. Check the account details and try again.");
  } finally {
    el.authSubmit.disabled = false;
  }
}

function downloadJson(filename, value) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function exportSession() {
  const safeDate = new Date().toISOString().replace(/[:.]/g, "-");
  downloadJson(`annie-research-session-${safeDate}.json`, {
    format: "annie-research-session/v1",
    title: "Research Session",
    exported_at: new Date().toISOString(),
    runtime_status: AnnieState.get("session").runtime,
    messages,
  });
  announce("Research session exported");
}

async function loadSettings() {
  settings = await AnnieApi.getSettings();
  AnnieState.set("settings", settings);
}

function fillSettings() {
  el.ollamaUrl.value = settings.ollama_url || "";
  el.voiceUrl.value = settings.voice_url || "";
  el.ollamaUrl.disabled = Boolean(settings.operator_managed_routes);
  el.voiceUrl.disabled = Boolean(settings.operator_managed_routes);
  el.temp.value = settings.temperature ?? 0.7;
  el.tempVal.textContent = Number(el.temp.value).toFixed(2);
  el.sys.value = settings.system_prompt || settings.default_doctrine || "";
  el.toolsToggle.checked = Boolean(settings.tools_enabled);
  el.speakToggle.checked = Boolean(AnnieState.get("prefs")?.speak);
}

function fallbackRuntime(data) {
  const backendReady = Boolean(data.backend?.ok);
  return {
    api: "ready",
    model: {
      availability: backendReady ? "ready" : "unavailable",
      name: settings.model,
      route: "unknown",
      locality: "unknown",
    },
    memory: {
      backend: "unknown",
      location: "unknown",
      conversation_persistence: "enabled",
      knowledge_tools: settings.tools_enabled ? "enabled" : "disabled",
    },
    voice: {
      input: "browser_managed_unverified",
      output: data.voice?.bridge_ok ? "unknown_bridge" : "browser_managed_unverified",
      bridge_available: Boolean(data.voice?.bridge_ok),
      route: "unknown",
    },
    assets: { source: "bundled", remote_dependencies: false },
    network: { claim: "not_verified", reason: "This server does not expose route verification.", offline_verified: false },
  };
}

function modelKey(value) {
  return String(value || "").trim().toLowerCase().replace(/:latest$/, "");
}

function runtimeForSettings(data) {
  const runtime = data.runtime_status || fallbackRuntime(data);
  const names = Array.isArray(data.backend?.model_names) ? data.backend.model_names : [];
  const endpointAvailable = Boolean(data.backend?.ok);
  const installed = names.some((name) => modelKey(name) === modelKey(settings.model));
  const ready = endpointAvailable && installed;
  return {
    ...runtime,
    model: {
      ...(runtime.model || {}),
      name: settings.model,
      availability: ready ? "ready" : "unavailable",
      endpoint_available: endpointAvailable,
      installed,
      reason: ready
        ? "The selected model is available."
        : endpointAvailable
          ? "The selected model is not listed by the endpoint."
          : "The model endpoint is unavailable.",
    },
    memory: {
      ...(runtime.memory || {}),
      knowledge_tools: settings.tools_enabled ? "enabled" : "disabled",
    },
  };
}

async function refreshEngine() {
  try {
    const data = await AnnieApi.health();
    const names = data.backend?.model_names || [];
    const previous = el.model.value;
    el.model.innerHTML = "";
    if (!names.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No model found — pull llama3.2";
      el.model.appendChild(option);
    } else {
      for (const name of names) {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        el.model.appendChild(option);
      }
      const selectedName = names.find((name) => modelKey(name) === modelKey(settings.model));
      if (selectedName) el.model.value = selectedName;
      else if (previous && names.includes(previous)) el.model.value = previous;
      else el.model.value = names[0];
    }
    AnnieState.dispatch("HEALTH_OK", runtimeForSettings(data));
  } catch {
    el.model.innerHTML = '<option value="">Start Ollama to continue</option>';
    AnnieState.dispatch("HEALTH_LOST");
  }
}

function cleanVoiceText(text) {
  return String(text).replace(/```[\s\S]*?```/g, "").replace(/\s+/g, " ").trim().slice(0, 420);
}

function clearAudioResources() {
  if (audioEl) {
    audioEl.onplay = null;
    audioEl.onended = null;
    audioEl.onerror = null;
    audioEl.pause();
    audioEl = null;
  }
  if (audioUrl) {
    URL.revokeObjectURL(audioUrl);
    audioUrl = null;
  }
  if (finishAudio) {
    finishAudio();
    finishAudio = null;
  }
}

function playBridgeAudio(payload) {
  return new Promise((resolve, reject) => {
    clearAudioResources();
    let settled = false;
    const finish = (error) => {
      if (settled) return;
      settled = true;
      if (error) reject(error);
      else resolve();
    };
    finishAudio = () => finish();
    audioUrl = URL.createObjectURL(new Blob([payload.buffer], { type: payload.contentType }));
    audioEl = new Audio(audioUrl);
    audioEl.onplay = () => AnnieState.dispatch("SPEECH_STARTED");
    audioEl.onended = () => {
      AnnieState.dispatch("SPEECH_ENDED");
      finish();
      clearAudioResources();
    };
    audioEl.onerror = () => {
      finish(new Error("voice bridge audio could not play"));
      clearAudioResources();
    };
    audioEl.play().catch((error) => {
      finish(error);
      clearAudioResources();
    });
  });
}

function speakInBrowser(text) {
  return new Promise((resolve) => {
    if (!("speechSynthesis" in window)) {
      AnnieState.dispatch("RESPONSE_RENDERED");
      resolve();
      return;
    }
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      finishSpeech = null;
      AnnieState.dispatch("SPEECH_ENDED");
      resolve();
    };
    finishSpeech = finish;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.96;
    utterance.pitch = 0.72;
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find((voice) => /Daniel|Arthur|Moira|Irish/i.test(voice.name)) || voices[0];
    if (preferred) utterance.voice = preferred;
    utterance.onstart = () => AnnieState.dispatch("SPEECH_STARTED");
    utterance.onend = finish;
    utterance.onerror = finish;
    window.speechSynthesis.speak(utterance);
  });
}

async function speakReply(text) {
  const clip = cleanVoiceText(text);
  if (!clip || !AnnieState.get("prefs")?.speak) {
    AnnieState.dispatch("RESPONSE_RENDERED");
    return;
  }
  voiceAbortController = new AbortController();
  try {
    const payload = await AnnieApi.speak(clip, voiceAbortController.signal);
    await playBridgeAudio(payload);
  } catch (error) {
    if (error.name === "AbortError") return;
    AnnieState.dispatch("VOICE_FALLBACK");
    announce("Using browser-managed voice; locality is unverified");
    await speakInBrowser(clip);
  } finally {
    voiceAbortController = null;
  }
}

function stopCurrentActivity() {
  abortController?.abort();
  voiceAbortController?.abort();
  if (recognitionActive) {
    try { recognition?.abort(); } catch { /* browser owns recognizer lifecycle */ }
  }
  clearAudioResources();
  if (finishSpeech) finishSpeech();
  try { window.speechSynthesis?.cancel(); } catch { /* optional browser API */ }
  if (activeWaveform) activeWaveform.classList.remove("active");
  AnnieState.dispatch("STOPPED");
}

async function sendMessage(mode = "chat") {
  if (AnnieState.get("session").phase === "thinking") return;
  const text = el.input.value.trim();
  if (!text) return;
  companion?.showView("chat");
  if (!el.model.value) {
    const detail = "Start Ollama and install a model such as llama3.2, then retry.";
    addErrorCard("No model available", detail);
    AnnieState.dispatch("FAILED", { title: "No model available", detail });
    return;
  }

  addMessage("user", text);
  el.input.value = "";
  autosize();
  AnnieState.dispatch("REQUEST_STARTED");
  abortController = new AbortController();

  try {
    const data = await AnnieApi.chat(text, abortController.signal, mode);
    const reply = data.reply?.trim();
    if (!reply) throw new Error("The model returned no answer. Try again or choose another installed model.");
    AnnieState.dispatch("RESPONSE_READY", { metrics: data.metrics || null });
    addMessage("assistant", reply, {
      metrics: data.metrics,
      model: data.model,
      toolEvents: data.tool_events || [],
    });
    announce("Annie replied");
    companion?.refresh().catch(() => {});
    await speakReply(reply);
    if (data.restart) addSystemMessage("The local session was restarted by Annie's grounding policy. Structured knowledge was kept.");
  } catch (error) {
    if (error.name === "AbortError") {
      addSystemMessage("Output stopped. The local model may finish its current non-streaming request in the background.");
      AnnieState.dispatch("STOPPED");
    } else {
      const detail = error.message || "The configured model did not return a response.";
      addErrorCard("Model request failed", detail);
      AnnieState.dispatch("FAILED", { title: "Model request failed", detail });
      await refreshEngine();
    }
  } finally {
    abortController = null;
    if (AnnieState.get("session").phase === "thinking") AnnieState.dispatch("RESPONSE_RENDERED");
    el.input.focus();
  }
}

function memoryGroup(title, items, render) {
  const rows = items.length ? items.map(render).join("") : '<div class="mem-empty">Nothing stored here yet.</div>';
  return `<section class="mem-group"><h3>${esc(title)}</h3>${rows}</section>`;
}

async function renderMemory() {
  el.memBody.innerHTML = '<p class="memory-note">Loading stored knowledge…</p>';
  try {
    const memory = await AnnieApi.getKnowledge();
    const status = AnnieState.get("session").runtime.memory;
    let html = `<p class="memory-note">Conversation history uses <b>${esc(status.backend || "configured storage")}</b>. The items below are structured knowledge; the Knowledge tools switch does not disable conversation persistence.</p>`;
    html += memoryGroup("Profile", memory.profile ? [{ id: "", text: memory.profile }] : [], (item) =>
      `<div class="mem-item"><span>${esc(item.text).replace(/\n/g, "<br>")}</span><button class="delete-memory" type="button" data-kind="profile" aria-label="Delete stored profile">×</button></div>`);
    html += memoryGroup("Goals", memory.goals || [], (item) =>
      `<div class="mem-item ${item.done ? "done" : ""}"><span>${esc(item.text)}</span><button class="delete-memory" type="button" data-kind="goal" data-id="${esc(item.id)}" aria-label="Delete goal">×</button></div>`);
    html += memoryGroup("Remembered facts", memory.facts || [], (item) =>
      `<div class="mem-item"><span>${esc(item.text)}</span><button class="delete-memory" type="button" data-kind="fact" data-id="${esc(item.id)}" aria-label="Delete remembered fact">×</button></div>`);
    html += memoryGroup("Journal", memory.journal || [], (item) =>
      `<div class="mem-item"><span>${esc(item.entry)}</span><button class="delete-memory" type="button" data-kind="journal" data-id="${esc(item.id)}" aria-label="Delete journal entry">×</button></div>`);
    html += '<div class="memory-actions"><button class="secondary-button" id="memExport" type="button">Export knowledge</button><button class="danger-button" id="memWipe" type="button">Wipe structured knowledge</button></div>';
    el.memBody.innerHTML = html;

    $$(".delete-memory", el.memBody).forEach((button) => button.addEventListener("click", async () => {
      await AnnieApi.deleteKnowledgeItem(button.dataset.kind, button.dataset.id || null);
      await renderMemory();
      await companion?.refresh().catch(() => {});
    }));
    $("#memExport", el.memBody).addEventListener("click", () => downloadJson("annie-structured-knowledge.json", memory));
    $("#memWipe", el.memBody).addEventListener("click", async () => {
      if (window.confirm("Wipe all structured knowledge? Conversation history is separate.")) {
        await AnnieApi.deleteKnowledge();
        await renderMemory();
        await companion?.refresh().catch(() => {});
      }
    });
  } catch (error) {
    el.memBody.innerHTML = `<div class="error-card"><b>Memory unavailable</b><span>${esc(error.message || "Could not read memory")}</span></div>`;
  }
}

async function saveSettings() {
  const payload = {
    model: el.model.value || settings.model,
    ollama_url: el.ollamaUrl.value.trim(),
    voice_url: el.voiceUrl.value.trim(),
    temperature: Number.parseFloat(el.temp.value),
    tools_enabled: el.toolsToggle.checked,
    system_prompt: el.sys.value.trim(),
  };
  const errors = AnnieValidators.validateSettings(payload);
  if (errors.length) {
    addErrorCard("Settings are invalid", errors.join("; "));
    announce("Settings could not be saved");
    return;
  }
  settings = await AnnieApi.updateSettings(payload);
  AnnieState.set("settings", settings);
  AnnieState.setPrefs({ speak: el.speakToggle.checked });
  closeDialog(el.settingsDialog);
  await refreshEngine();
  announce("Settings saved");
}

function setupRecognition() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    micSupported = false;
    el.mic.disabled = true;
    el.mic.setAttribute("aria-label", "Browser voice input is not supported");
    el.mic.title = "Browser voice input is not supported";
    return;
  }
  micSupported = true;
  recognition = new Recognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "en-US";
  recognition.onstart = () => {
    recognitionActive = true;
    recognitionBase = el.input.value.trim();
    AnnieState.dispatch("MIC_STARTED");
  };
  recognition.onresult = (event) => {
    let transcript = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      transcript += event.results[index][0].transcript;
    }
    el.input.value = [recognitionBase, transcript].filter(Boolean).join(" ");
    autosize();
  };
  recognition.onerror = (event) => {
    if (event.error !== "aborted") {
      const detail = `Browser voice input reported: ${event.error || "unknown error"}.`;
      addErrorCard("Voice input failed", detail);
      AnnieState.dispatch("FAILED", { title: "Voice input failed", detail });
    }
  };
  recognition.onend = () => {
    recognitionActive = false;
    AnnieState.dispatch("MIC_ENDED");
    el.input.focus();
  };
}

el.composer.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage();
});
el.input.addEventListener("input", autosize);
el.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !$("dialog[open]") && AnnieState.get("session").canStop) {
    event.preventDefault();
    stopCurrentActivity();
  }
});
el.stop.addEventListener("click", stopCurrentActivity);
el.mic.addEventListener("click", () => {
  if (!recognition) return;
  if (recognitionActive) {
    recognition.stop();
    return;
  }
  try {
    recognition.start();
  } catch {
    // Browsers throw if start is called twice during a lifecycle transition.
  }
});
el.menuBtn.addEventListener("click", () => openDialog(el.menuDialog));
el.cfgBtn.addEventListener("click", () => {
  fillSettings();
  openDialog(el.settingsDialog);
});
el.modelBtn.addEventListener("click", () => {
  fillSettings();
  openDialog(el.settingsDialog, el.model);
});
el.exportBtn.addEventListener("click", exportSession);
[el.modelStatus, el.memoryStatus, el.networkStatus].forEach((button) => button.addEventListener("click", () => openDialog(el.menuDialog)));
el.openMemoryBtn.addEventListener("click", async () => {
  closeDialog(el.menuDialog);
  openDialog(el.memoryDialog);
  await renderMemory();
});
el.clearBtn.addEventListener("click", async () => {
  if (!window.confirm("Restart this session and clear conversation history? Structured knowledge will be kept.")) return;
  stopCurrentActivity();
  await AnnieApi.restartSession();
  messages = [];
  el.stream.innerHTML = "";
  addSystemMessage("New research session started. Structured knowledge was kept.");
  closeDialog(el.menuDialog);
});
$$('[data-close]').forEach((button) => button.addEventListener("click", () => closeDialog(document.getElementById(button.dataset.close))));
el.settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await saveSettings();
  } catch (error) {
    addErrorCard("Settings could not be saved", error.message || "Unknown settings error");
  }
});
el.authDialog.addEventListener("cancel", (event) => event.preventDefault());
el.authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await signIn(el.authEmail.value.trim(), el.authPassword.value);
});
el.logoutBtn.addEventListener("click", () => {
  AnnieState.set("auth", { token: null, user: null });
  window.location.reload();
});
window.addEventListener("annie:auth-required", (event) => {
  AnnieState.set("auth", { token: null, user: null });
  if (event.detail?.hadToken) {
    window.location.reload();
    return;
  }
  showAuthGate("This protected deployment requires a valid account.");
});
el.temp.addEventListener("input", () => {
  el.tempVal.textContent = Number(el.temp.value).toFixed(2);
});
el.resetSys.addEventListener("click", async () => {
  settings = await AnnieApi.resetDoctrine();
  AnnieState.set("settings", settings);
  el.sys.value = settings.system_prompt || settings.default_doctrine || "";
  announce("Default doctrine restored");
});

AnnieState.subscribe(renderState);

companion = AnnieCompanion.init({
  openDialog, closeDialog, announce, autosize,
  requestPlan: () => sendMessage("plan"),
  connectModel: () => { fillSettings(); openDialog(el.settingsDialog, el.model); },
  inspectMemory: () => { openDialog(el.memoryDialog); renderMemory(); },
});

async function boot() {
  setupRecognition();
  renderState({ session: AnnieState.get("session") });
  try {
    await loadSettings();
  } catch (error) {
    if (error.status === 401) {
      showAuthGate("This protected deployment requires a valid account.");
    } else {
      addErrorCard("Settings unavailable", error.message || "The local API did not return settings.");
    }
  }
  fillSettings();
  await refreshEngine();
  if (!authRequired) await companion.refresh().catch(() => {});
  window.setInterval(() => {
    if (!AnnieState.get("session").canStop) refreshEngine();
  }, 10_000);
  if ("speechSynthesis" in window) window.speechSynthesis.getVoices();
}

boot();
