"use strict";

const $ = (selector) => document.querySelector(selector);
const el = {
  stream: $("#stream"),
  main: $("#main"),
  herald: $("#herald"),
  input: $("#input"),
  send: $("#send"),
  scanner: $("#scanner"),
  engineDot: $("#engineDot"),
  engineTxt: $("#engineTxt"),
  clearBtn: $("#clearBtn"),
  form: $("#chat-form"),
};

let busy = false;
let abortController = null;

function esc(text) {
  return text.replace(/[&<>]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[char]));
}

function clock() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function toBottom() {
  el.main.scrollTop = el.main.scrollHeight;
}

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
    bubble.textContent = content;
  }
  el.stream.appendChild(turn);
  toBottom();
  return bubble;
}

function addMeta(bubble, label) {
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = `${label} · ${clock()}`;
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
    await new Promise((resolve) => setTimeout(resolve, 8));
  }
  bubble.textContent = text;
}

async function refreshEngine() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("health failed");
    }
    const data = await response.json();
    const backendOk = data.backend?.ok;
    el.engineDot.className = backendOk ? "dot on" : "dot off";
    el.engineTxt.textContent = backendOk ? "engine online" : "engine offline";
  } catch {
    el.engineDot.className = "dot off";
    el.engineTxt.textContent = "engine offline";
  }
}

async function sendMessage(text) {
  abortController = new AbortController();
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text }),
    signal: abortController.signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed with ${response.status}`);
  }

  return response.json();
}

function stop() {
  if (abortController) {
    abortController.abort();
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

  addTurn("user", text);
  el.input.value = "";
  autosize();

  const bubble = addTurn("bot", "");
  setBusy(true);

  try {
    const data = await sendMessage(text);
    const reply = data.reply || "[no output]";
    await typeOut(bubble, reply);
    addMeta(bubble, data.model || "local");

    if (data.restart) {
      await new Promise((resolve) => setTimeout(resolve, 1200));
      showHerald();
    }
  } catch (error) {
    if (error.name === "AbortError") {
      if (!bubble.textContent) {
        bubble.parentElement.remove();
      }
    } else {
      bubble.parentElement.remove();
      showError(
        "engine error",
        error.message || "unknown error"
      );
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

el.form.addEventListener("submit", (event) => {
  event.preventDefault();
  send();
});

el.clearBtn.addEventListener("click", () => {
  if (busy) {
    stop();
  }
  showHerald();
});

refreshEngine();
setInterval(() => {
  if (!busy) {
    refreshEngine();
  }
}, 8000);

el.input.focus();
