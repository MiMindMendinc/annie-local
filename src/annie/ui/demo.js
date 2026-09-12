"use strict";

function createDemoClient(fetcher) {
  // The capability stays in this page's memory: no shared cookie, URL, or
  // browser storage that could connect separate tabs or later visitors.
  let token = null;
  async function request(path, method = "GET", body, signal) {
    const response = await fetcher(path, {
      method, credentials: "omit", cache: "no-store", signal,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) {
      if (response.status === 401) token = null;
      const error = new Error("The demo request failed. Please try again.");
      error.status = response.status;
      const payload = await response.json().catch(() => ({}));
      if (typeof payload.detail === "string") error.message = payload.detail;
      throw error;
    }
    return response;
  }
  return {
    hasSession: () => Boolean(token),
    health: async () => (await request("/api/health")).json(),
    async start() {
      if (token) return;
      const data = await (await request("/api/session", "POST", {})).json();
      token = data.token;
    },
    async end() {
      if (!token) return;
      try { await request("/api/session", "DELETE", {}); }
      catch (error) { if (error.status !== 401) throw error; }
      token = null;
    },
    async chat(message) {
      if (!token) throw new Error("Start a new demo conversation.");
      return (await request("/api/chat", "POST", { message })).json();
    },
    async speak(text, signal) {
      if (!token) throw new Error("Start a new demo conversation.");
      return (await request("/api/voice/speak", "POST", { text }, signal)).blob();
    },
  };
}

if (typeof module !== "undefined") module.exports = { createDemoClient };

if (typeof document !== "undefined") {
  const client = createDemoClient(window.fetch.bind(window));
  const el = Object.fromEntries(["newChat", "endChat", "message", "send", "chatForm", "messages", "notice", "modelStatus", "network", "readAloud", "voiceStatus"].map((id) => [id, document.getElementById(id)]));
  let busy = false;
  let ready = false;
  let voiceReady = false;
  let voiceController = null;
  let audio = null;
  let audioUrl = null;

  function controls() {
    el.newChat.disabled = busy || !ready;
    el.newChat.textContent = client.hasSession() ? "New chat" : "Start chat";
    el.endChat.disabled = busy || !client.hasSession();
    el.send.disabled = busy || !ready || !client.hasSession();
    el.message.disabled = busy || !client.hasSession();
  }

  function stopVoice() {
    voiceController?.abort();
    voiceController = null;
    audio?.pause();
    audio = null;
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    audioUrl = null;
  }

  function addMessage(who, text) {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${who === "You" ? "user" : "assistant"}`;
    const label = document.createElement("strong");
    label.textContent = who;
    bubble.append(label, document.createTextNode(text));
    el.messages.append(bubble);
    bubble.scrollIntoView({ block: "nearest" });
  }

  async function refresh() {
    try {
      const data = await client.health();
      const runtime = data.runtime_status;
      ready = runtime.model.availability === "ready";
      el.modelStatus.textContent = ready ? "Model ready" : "Model offline";
      const places = { device: "this demo host", local_container: "a container on the demo host", local_network: "the operator’s local network", remote: "a remote service", unknown: "an unverified service" };
      el.network.textContent = `Messages go to a model on ${places[runtime.model.locality] || places.unknown}.`;
      voiceReady = runtime.voice.bridge_available;
      const voicePlaces = { local_bridge: "this demo host", local_network_bridge: "the operator’s local network", remote_bridge: "a remote voice service" };
      el.voiceStatus.textContent = voiceReady ? `Read aloud sends reply text to ${voicePlaces[runtime.voice.output] || "an unverified voice service"}.` : "Read aloud is unavailable. Text chat is available when the model is ready.";
      if (!client.hasSession()) el.notice.textContent = ready ? "Select Start chat to begin your own conversation." : "The operator needs to reconnect the model. You can retry shortly.";
    } catch {
      ready = false;
      el.modelStatus.textContent = "Demo unavailable";
      if (!busy) el.notice.textContent = "The demo could not connect. Retrying shortly…";
    }
    controls();
  }

  el.newChat.addEventListener("click", async () => {
    if (busy) return;
    busy = true; controls(); stopVoice();
    try {
      await client.end();
      el.messages.replaceChildren();
      await client.start();
      el.notice.textContent = "Your temporary conversation is ready.";
    } catch (error) { el.notice.textContent = error.message; }
    finally { busy = false; controls(); if (client.hasSession()) el.message.focus(); }
  });

  el.endChat.addEventListener("click", async () => {
    if (busy) return;
    busy = true; controls(); stopVoice();
    try {
      await client.end();
      el.messages.replaceChildren();
      el.message.value = "";
      el.notice.textContent = "Conversation cleared. You can start a new chat.";
    } catch (error) { el.notice.textContent = error.message; }
    finally { busy = false; controls(); el.newChat.focus(); }
  });

  el.chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = el.message.value.trim();
    if (busy || !ready || !message || !client.hasSession()) return;
    busy = true; controls(); stopVoice();
    el.notice.textContent = "Annie is thinking…";
    let reply = null;
    try {
      const data = await client.chat(message);
      if (data.restart) el.messages.replaceChildren();
      addMessage("You", message);
      addMessage("Annie", data.reply);
      el.message.value = "";
      reply = data.reply;
      el.notice.textContent = data.restart ? "The conversation was reset by the grounding policy." : "Ready for your next thought.";
    } catch (error) { el.notice.textContent = error.message; }
    finally { busy = false; controls(); if (client.hasSession()) el.message.focus(); }
    if (reply && el.readAloud.checked && voiceReady) {
      const controller = new AbortController();
      voiceController = controller;
      try {
        const clip = await client.speak(reply.slice(0, 420), controller.signal);
        if (controller.signal.aborted) return;
        audioUrl = URL.createObjectURL(clip);
        audio = new Audio(audioUrl);
        audio.onended = () => {
          if (voiceController === controller) {
            stopVoice();
            el.voiceStatus.textContent = "Read aloud complete.";
          }
        };
        await audio.play();
        if (!controller.signal.aborted) el.voiceStatus.textContent = "Reading reply aloud…";
      } catch (error) {
        if (error.name !== "AbortError") el.voiceStatus.textContent = "Read aloud could not play. Your reply is above.";
      }
    }
  });
  el.readAloud.addEventListener("change", () => { if (!el.readAloud.checked) stopVoice(); });
  window.addEventListener("pagehide", stopVoice);
  refresh();
  window.setInterval(() => { if (!busy) refresh(); }, 30000);
}
