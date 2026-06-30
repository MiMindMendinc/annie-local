"use strict";

const $ = (selector) => document.querySelector(selector);
const el = {
  stream: $("#stream"),
  main: $("#main"),
  herald: $("#herald"),
  input: $("#input"),
  send: $("#send"),
  scanner: $("#scanner"),
  model: $("#model"),
  mic: $("#mic"),
  engineDot: $("#engineDot"),
  engineTxt: $("#engineTxt"),
  voiceDot: $("#voiceDot"),
  voiceTxt: $("#voiceTxt"),
  voiceBtn: $("#voiceBtn"),
  memBtn: $("#memBtn"),
  cfgBtn: $("#cfgBtn"),
  clearBtn: $("#clearBtn"),
  scrimCfg: $("#scrimCfg"),
  drawerCfg: $("#drawerCfg"),
  cfgClose: $("#cfgClose"),
  ollamaUrl: $("#ollamaUrl"),
  voiceUrl: $("#voiceUrl"),
  temp: $("#temp"),
  tempVal: $("#tempVal"),
  sys: $("#sys"),
  saveCfg: $("#saveCfg"),
  resetSys: $("#resetSys"),
  swVoice: $("#swVoice"),
  swMem: $("#swMem"),
  scrimMem: $("#scrimMem"),
  drawerMem: $("#drawerMem"),
  memClose: $("#memClose"),
  memBody: $("#memBody"),
};

const store = {
  get(key, fallback) {
    return window.AnnieState ? AnnieState.get(key) ?? fallback : fallback;
  },
  set(key, value) {
    if (window.AnnieState) AnnieState.set(key, value);
  },
};

let ui = (window.AnnieState?.get("ui")) || { speak: false, memory: true };
let settings = {
  model: null,
  ollama_url: "http://127.0.0.1:11434",
  voice_url: "http://127.0.0.1:8123",
  temperature: 0.7,
  tools_enabled: true,
  default_doctrine: "",
};
let busy = false;
let abortController = null;
let audioEl = null;

function esc(text) {
  return String(text).replace(/[&<>]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[char]));
}

function format(text) {
  const parts = text.split(/```/);
  let out = "";
  for (let i = 0; i < parts.length; i += 1) {
    if (i % 2 === 1) {
      out += `<pre><code>${esc(parts[i].replace(/^[a-zA-Z0-9_-]*\n/, ""))}</code></pre>`;
    } else {
      out += esc(parts[i]).replace(/`([^`\n]+)`/g, "<code>$1</code>");
    }
  }
  return out;
}

const clock = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const toBottom = () => {
  el.main.scrollTop = el.main.scrollHeight;
};

function setBusy(on) {
  busy = on;
  el.scanner.classList.toggle("live", on);
  el.send.textContent = on ? "Stop" : "Send";
  el.send.classList.toggle("stop", on);
  el.input.disabled = on;
}

function showHerald() {
  el.stream.innerHTML = "";
  const herald = document.createElement("div");
  herald.className = "herald";
  herald.id = "herald";
  herald.innerHTML = `
    <div class="l1"><b>ANNIE-5</b> resident. weights local. no wire out.</div>
    <div class="l2">i keep what matters to you, and i'm in your corner.</div>
    <div class="l3">say something<span class="cursor"></span></div>`;
  el.stream.appendChild(herald);
  toBottom();
}

function addTurn(role, content) {
  $("#herald")?.remove();
  const turn = document.createElement("div");
  turn.className = `turn ${role === "user" ? "user" : "bot"}`;
  turn.innerHTML = `<div class="who">${role === "user" ? "you" : "annie"}</div><div class="bubble"></div>`;
  const bubble = turn.querySelector(".bubble");
  if (content) {
    bubble.innerHTML = format(content);
    bubble.dataset.raw = content;
  }
  el.stream.appendChild(turn);
  toBottom();
  return bubble;
}

function toolLine(bubble, text, ok) {
  const line = document.createElement("div");
  line.className = "tool";
  line.innerHTML = `▸ <b>${esc(text)}</b>${ok ? ' <span class="ok">✓</span>' : ""}`;
  bubble.parentElement.insertBefore(line, bubble);
  toBottom();
}

function addMeta(bubble, label) {
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.innerHTML = `${esc(label || "")} · ${clock()} · <button type="button">copy</button>`;
  meta.querySelector("button").onclick = () => {
    navigator.clipboard?.writeText(bubble.dataset.raw || bubble.innerText);
    meta.querySelector("button").textContent = "copied";
    window.setTimeout(() => {
      meta.querySelector("button").textContent = "copy";
    }, 1200);
  };
  bubble.parentElement.appendChild(meta);
}

function showError(title, detail) {
  $("#herald")?.remove();
  const error = document.createElement("div");
  error.className = "errline";
  error.innerHTML = `<b>${esc(title)}</b><span>${esc(detail)}</span>`;
  el.stream.appendChild(error);
  toBottom();
}

async function typeOut(bubble, text) {
  const total = text.length;
  const step = Math.max(1, Math.ceil(total / 220));
  let index = 0;
  while (index < total) {
    if (abortController?.signal.aborted) {
      break;
    }
    index = Math.min(total, index + step);
    bubble.textContent = text.slice(0, index);
    toBottom();
    await new Promise((resolve) => window.setTimeout(resolve, 8));
  }
  bubble.innerHTML = format(text);
  bubble.dataset.raw = text;
}

async function loadSettings() {
  settings = await AnnieApi.getSettings();
}

async function refreshEngine() {
  try {
    const data = await AnnieApi.health();
    const backendOk = data.backend?.ok;
    const names = data.backend?.model_names || [];
    el.engineDot.className = backendOk ? "dot on" : "dot off";
    el.engineTxt.textContent = backendOk ? "engine online" : "engine offline";

    const previous = el.model.value;
    el.model.innerHTML = "";
    if (!names.length) {
      el.model.innerHTML = '<option value="">no models — ollama pull llama3.2</option>';
    } else {
      for (const name of names) {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        el.model.appendChild(option);
      }
      if (settings.model && names.includes(settings.model)) {
        el.model.value = settings.model;
      } else if (previous && names.includes(previous)) {
        el.model.value = previous;
      }
    }
    refreshVoice(data.voice);
  } catch {
    el.engineDot.className = "dot off";
    el.engineTxt.textContent = "engine offline";
    el.model.innerHTML = '<option value="">start Ollama →</option>';
  }
}

function refreshVoice(voice) {
  if (!ui.speak) {
    el.voiceDot.className = "dot";
    el.voiceTxt.textContent = "voice off";
    return;
  }
  if (voice?.bridge_ok) {
    el.voiceDot.className = "dot on";
    el.voiceTxt.textContent = "WOPR voice";
  } else {
    el.voiceDot.className = "dot on";
    el.voiceTxt.textContent = "browser voice";
  }
}

async function speak(text) {
  if (!ui.speak || !text) {
    return;
  }
  const clip = text.replace(/```[\s\S]*?```/g, "").replace(/\s+/g, " ").trim().slice(0, 420);
  if (!clip) {
    return;
  }
  try {
    const response = await fetch("/api/voice/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: clip }),
    });
    if (response.ok) {
      const buffer = await response.arrayBuffer();
      const url = URL.createObjectURL(new Blob([buffer], { type: "audio/wav" }));
      if (audioEl) {
        audioEl.pause();
      }
      audioEl = new Audio(url);
      audioEl.play().catch(() => {});
      audioEl.onended = () => URL.revokeObjectURL(url);
      return;
    }
  } catch {
    /* fallback */
  }
  try {
    if (!("speechSynthesis" in window)) {
      return;
    }
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(clip);
    utterance.rate = 0.94;
    utterance.pitch = 0.55;
    const voices = speechSynthesis.getVoices();
    const pick = voices.find((voice) => /Daniel|Arthur|male/i.test(voice.name)) || voices[0];
    if (pick) {
      utterance.voice = pick;
    }
    speechSynthesis.speak(utterance);
  } catch {
    /* ignore */
  }
}

function stop() {
  if (abortController) {
    abortController.abort();
  }
  if (audioEl) {
    audioEl.pause();
  }
  try {
    speechSynthesis.cancel();
  } catch {
    /* ignore */
  }
}

async function send() {
  if (busy) {
    stop();
    return;
  }
  const text = el.input.value.trim();
  if (!text) {
    return;
  }
  if (!el.model.value) {
    showError("no model loaded", "Start Ollama and pull a tool-capable model, then reopen.");
    return;
  }

  addTurn("user", text);
  el.input.value = "";
  autosize();
  const bubble = addTurn("bot", "");
  setBusy(true);
  abortController = new AbortController();

  try {
    const data = await AnnieApi.chat(text, abortController.signal);
    for (const event of data.tool_events || []) {
      toolLine(bubble, event, true);
    }
    const reply = data.reply || "[no output]";
    await typeOut(bubble, reply);
    addMeta(bubble, data.model || "local");
    speak(reply);

    if (data.restart) {
      await new Promise((resolve) => window.setTimeout(resolve, 1400));
      await AnnieApi.restartSession();
      showHerald();
    }
  } catch (error) {
    if (error.name === "AbortError") {
      if (!(bubble.textContent || bubble.dataset.raw)) {
        bubble.parentElement.remove();
      }
    } else {
      bubble.parentElement.remove();
      showError("engine error", error.message || "unknown error");
      refreshEngine();
    }
  } finally {
    setBusy(false);
    abortController = null;
    el.input.focus();
  }
}

function autosize() {
  el.input.style.height = "auto";
  el.input.style.height = `${Math.min(el.input.scrollHeight, 180)}px`;
}

async function renderMem() {
  const mem = await AnnieApi.getKnowledge();
  const group = (title, items, render) => {
    let html = `<div class="memgroup"><h3>${title}</h3>`;
    if (!items.length) {
      html += '<div class="memempty">— nothing yet —</div>';
    } else {
      html += items.map(render).join("");
    }
    return `${html}</div>`;
  };

  let html = '<div class="memgroup"><h3>Profile</h3>';
  html += mem.profile
    ? `<div class="memitem"><span class="x" data-clr="profile">✕</span><span>${esc(mem.profile).replace(/\n/g, "<br>")}</span></div>`
    : '<div class="memempty">— no profile yet —</div>';
  html += "</div>";
  html += group("Goals", mem.goals || [], (item) =>
    `<div class="memitem ${item.done ? "done" : ""}"><span class="x" data-kind="goal" data-id="${item.id}">✕</span><span>${esc(item.text)}</span></div>`);
  html += group("Remembered facts", mem.facts || [], (item) =>
    `<div class="memitem"><span class="x" data-kind="fact" data-id="${item.id}">✕</span><span>${esc(item.text)}</span></div>`);
  html += group("Journal", mem.journal || [], (item) =>
    `<div class="memitem"><span class="x" data-kind="journal" data-id="${item.id}">✕</span><span>${esc(item.entry)}</span></div>`);
  html += `<div class="mem-actions">
    <button class="ghostbtn" id="memExport" type="button">Export JSON</button>
    <button class="ghostbtn danger" id="memWipe" type="button">Wipe all</button>
  </div>`;
  el.memBody.innerHTML = html;

  el.memBody.querySelectorAll(".x").forEach((button) => {
    button.onclick = async () => {
      if (button.dataset.clr === "profile") {
        await AnnieApi.deleteKnowledgeItem("profile");
      } else {
        await AnnieApi.deleteKnowledgeItem(button.dataset.kind, button.dataset.id);
      }
      renderMem();
    };
  });

  $("#memExport").onclick = () => {
    const blob = new Blob([JSON.stringify(mem, null, 2)], { type: "application/json" });
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(blob);
    anchor.download = "annie-memory.json";
    anchor.click();
  };
  $("#memWipe").onclick = async () => {
    if (confirm("Wipe everything Annie remembers? This cannot be undone.")) {
      await AnnieApi.deleteKnowledge();
      renderMem();
    }
  };
}

function openCfg() {
  el.ollamaUrl.value = settings.ollama_url || "";
  el.voiceUrl.value = settings.voice_url || "";
  el.temp.value = settings.temperature ?? 0.7;
  el.tempVal.textContent = Number(el.temp.value).toFixed(2);
  el.sys.value = settings.system_prompt || settings.default_doctrine || "";
  el.swVoice.classList.toggle("on", ui.speak);
  el.swMem.classList.toggle("on", ui.memory);
  el.scrimCfg.classList.add("open");
  el.drawerCfg.classList.add("open");
  el.drawerCfg.setAttribute("aria-hidden", "false");
}

function closeCfg() {
  el.scrimCfg.classList.remove("open");
  el.drawerCfg.classList.remove("open");
  el.drawerCfg.setAttribute("aria-hidden", "true");
}

async function saveCfg() {
  const payload = {
    model: el.model.value || settings.model,
    ollama_url: el.ollamaUrl.value.trim(),
    voice_url: el.voiceUrl.value.trim(),
    temperature: parseFloat(el.temp.value),
    tools_enabled: el.swMem.classList.contains("on"),
    system_prompt: el.sys.value.trim(),
  };
  const errors = AnnieValidators.validateSettings(payload);
  if (errors.length) {
    showError("settings invalid", errors.join("; "));
    return;
  }
  settings = await AnnieApi.updateSettings(payload);
  ui.speak = el.swVoice.classList.contains("on");
  ui.memory = el.swMem.classList.contains("on");
  store.set("ui", ui);
  el.voiceBtn.classList.toggle("active", ui.speak);
  closeCfg();
  refreshEngine();
}

el.input.addEventListener("input", autosize);
el.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    send();
  }
  if (event.key === "Escape" && busy) {
    event.preventDefault();
    stop();
  }
});
el.send.addEventListener("click", send);
el.clearBtn.addEventListener("click", async () => {
  if (busy) {
    stop();
  }
  await AnnieApi.restartSession();
  showHerald();
});
el.voiceBtn.addEventListener("click", () => {
  ui.speak = !ui.speak;
  store.set("ui", ui);
  el.voiceBtn.classList.toggle("active", ui.speak);
  refreshEngine();
});
el.cfgBtn.addEventListener("click", openCfg);
el.cfgClose.addEventListener("click", closeCfg);
el.scrimCfg.addEventListener("click", closeCfg);
el.temp.addEventListener("input", () => {
  el.tempVal.textContent = Number(el.temp.value).toFixed(2);
});
el.swVoice.addEventListener("click", () => el.swVoice.classList.toggle("on"));
el.swMem.addEventListener("click", () => el.swMem.classList.toggle("on"));
el.resetSys.addEventListener("click", async () => {
  settings = await AnnieApi.resetDoctrine();
  el.sys.value = settings.default_doctrine || "";
});
el.saveCfg.addEventListener("click", saveCfg);
el.model.addEventListener("change", async () => {
  await AnnieApi.updateSettings({ model: el.model.value });
});
el.memBtn.addEventListener("click", async () => {
  await renderMem();
  el.scrimMem.classList.add("open");
  el.drawerMem.classList.add("open");
  el.drawerMem.setAttribute("aria-hidden", "false");
});
el.memClose.addEventListener("click", () => {
  el.scrimMem.classList.remove("open");
  el.drawerMem.classList.remove("open");
  el.drawerMem.setAttribute("aria-hidden", "true");
});
el.scrimMem.addEventListener("click", () => {
  el.scrimMem.classList.remove("open");
  el.drawerMem.classList.remove("open");
  el.drawerMem.setAttribute("aria-hidden", "true");
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  let recording = false;
  const recog = new SpeechRecognition();
  recog.continuous = false;
  recog.interimResults = true;
  recog.lang = "en-US";
  recog.onresult = (event) => {
    let transcript = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      transcript += event.results[i][0].transcript;
    }
    el.input.value = transcript;
    autosize();
  };
  recog.onend = () => {
    recording = false;
    el.mic.classList.remove("rec");
  };
  el.mic.addEventListener("click", () => {
    if (recording) {
      recog.stop();
      return;
    }
    try {
      recog.start();
      recording = true;
      el.mic.classList.add("rec");
    } catch {
      /* ignore */
    }
  });
} else {
  el.mic.title = "Voice input not supported in this browser";
  el.mic.style.opacity = "0.4";
}

async function boot() {
  try {
    await loadSettings();
  } catch {
    /* offline shell still works */
  }
  el.voiceBtn.classList.toggle("active", ui.speak);
  refreshEngine();
  window.setInterval(() => {
    if (!busy) {
      refreshEngine();
    }
  }, 8000);
  if ("speechSynthesis" in window) {
    speechSynthesis.getVoices();
    speechSynthesis.onvoiceschanged = () => {};
  }
}

boot();
