const orb = document.getElementById("orb");
const statusText = document.getElementById("status");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("messages");
const healthButton = document.getElementById("health-button");
const healthOutput = document.getElementById("health-output");

function setState(state) {
  orb.classList.remove("idle", "listening", "thinking", "speaking");
  orb.classList.add(state);
  statusText.textContent = state.charAt(0).toUpperCase() + state.slice(1);
}

function addMessage(role, content) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = content;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
}

async function sendMessage(message) {
  setState("thinking");
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed with ${response.status}`);
  }

  return response.json();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  input.value = "";
  input.disabled = true;
  form.querySelector("button").disabled = true;
  addMessage("user", message);

  try {
    const data = await sendMessage(message);
    setState("speaking");
    addMessage("assistant", data.reply || "No reply returned.");
    window.setTimeout(() => setState("idle"), 850);
  } catch (error) {
    setState("idle");
    addMessage("assistant", `Local backend error: ${error.message}\n\nTip: run 'ollama pull llama3.2' and make sure Ollama is running.`);
  } finally {
    input.disabled = false;
    form.querySelector("button").disabled = false;
    input.focus();
  }
});

input.addEventListener("focus", () => setState("listening"));
input.addEventListener("blur", () => setState("idle"));

healthButton.addEventListener("click", async () => {
  setState("thinking");
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    healthOutput.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    healthOutput.textContent = `Health check failed: ${error.message}`;
  } finally {
    setState("idle");
  }
});

setState("idle");
