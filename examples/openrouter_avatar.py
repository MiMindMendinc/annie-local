from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip() or "openrouter/free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = os.getenv(
    "AVATAR_SYSTEM_PROMPT",
    "You are Annie, a warm, practical AI companion. Be concise, truthful, curious, and useful. "
    "Never pretend you ran tools or accessed systems unless the application actually provided them. "
    "This is a cloud-backed demo using OpenRouter; say so plainly if asked where you run.",
)

app = FastAPI(title="Annie OpenRouter Voice Avatar", version="0.1.0")


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "provider": "openrouter",
        "model": OPENROUTER_MODEL,
        "api_key_configured": bool(OPENROUTER_API_KEY),
    }


@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict[str, Any]:
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY is not configured")

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend({"role": m.role, "content": m.content} for m in req.messages)

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.65,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-OpenRouter-Title": "Annie Local Voice Avatar",
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:800]
        raise HTTPException(status_code=502, detail=f"OpenRouter error: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenRouter request failed: {exc}") from exc

    try:
        reply = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="OpenRouter returned an unexpected response") from exc

    if not isinstance(reply, str) or not reply.strip():
        raise HTTPException(status_code=502, detail="OpenRouter returned an empty response")

    return {
        "reply": reply.strip(),
        "model": data.get("model", OPENROUTER_MODEL),
        "provider": "openrouter",
        "usage": data.get("usage"),
    }


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
<title>Annie Voice Avatar</title>
<style>
:root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
* { box-sizing: border-box; }
body { margin:0; min-height:100vh; background:linear-gradient(180deg,#eef8ff,#f8fff4); color:#102030; }
main { width:min(880px,100%); margin:0 auto; padding:24px 16px 40px; }
.hero { display:grid; place-items:center; gap:12px; margin:10px 0 22px; text-align:center; }
.avatar { width:156px; height:156px; border-radius:50%; background:radial-gradient(circle at 38% 32%,#ffffff 0 7%,#68d391 8% 25%,#1fa968 26% 54%,#0b6650 55% 100%); box-shadow:0 18px 55px rgba(20,100,80,.25), inset 0 0 30px rgba(255,255,255,.35); position:relative; transition:.2s transform,.2s box-shadow; }
.avatar.listening { transform:scale(1.04); box-shadow:0 18px 70px rgba(20,130,100,.4),0 0 0 14px rgba(40,200,140,.12); }
.avatar.thinking { animation:pulse 1.15s infinite ease-in-out; }
.avatar.speaking { animation:speak .55s infinite alternate ease-in-out; }
@keyframes pulse { 50% { transform:scale(.96); opacity:.8; } }
@keyframes speak { to { transform:scale(1.035); box-shadow:0 18px 70px rgba(20,130,100,.42),0 0 0 12px rgba(40,200,140,.10); } }
.status { font-weight:700; letter-spacing:.02em; }
.sub { font-size:.92rem; opacity:.68; }
.chat { background:rgba(255,255,255,.84); border:1px solid rgba(20,60,80,.09); border-radius:22px; min-height:310px; max-height:52vh; overflow:auto; padding:16px; box-shadow:0 14px 45px rgba(40,80,100,.10); }
.msg { max-width:82%; margin:9px 0; padding:11px 13px; border-radius:16px; white-space:pre-wrap; line-height:1.42; }
.user { margin-left:auto; background:#dff6ff; border-bottom-right-radius:5px; }
.bot { background:#e9fbe9; border-bottom-left-radius:5px; }
.controls { display:grid; grid-template-columns:auto 1fr auto; gap:10px; margin-top:12px; }
button,input { font:inherit; }
button { border:0; border-radius:15px; padding:12px 15px; font-weight:800; cursor:pointer; }
#mic { background:#0e7c5b; color:#fff; min-width:52px; }
#send { background:#173d55; color:#fff; }
#text { width:100%; border:1px solid #cbdde7; border-radius:15px; padding:12px 14px; background:#fff; outline:none; }
#text:focus { border-color:#4e9bb8; box-shadow:0 0 0 3px rgba(78,155,184,.12); }
.note { font-size:.78rem; opacity:.62; text-align:center; margin-top:10px; }
@media(max-width:600px){ .avatar{width:128px;height:128px}.controls{grid-template-columns:54px 1fr}.controls #send{grid-column:1/-1}.chat{max-height:46vh} }
</style>
</head>
<body>
<main>
  <section class="hero">
    <div id="avatar" class="avatar" aria-label="Annie avatar"></div>
    <div id="status" class="status">Ready</div>
    <div id="model" class="sub">OpenRouter · loading model…</div>
  </section>
  <section id="chat" class="chat" aria-live="polite"></section>
  <div class="controls">
    <button id="mic" title="Talk">🎙️</button>
    <input id="text" autocomplete="off" placeholder="Type or tap the mic…" />
    <button id="send">Send</button>
  </div>
  <div class="note">Cloud demo: prompts are sent to OpenRouter and the selected upstream model.</div>
</main>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('text');
const mic = document.getElementById('mic');
const send = document.getElementById('send');
const avatar = document.getElementById('avatar');
const statusEl = document.getElementById('status');
const modelEl = document.getElementById('model');
const history = [];

function setState(s, label) {
  avatar.classList.remove('listening','thinking','speaking');
  if (s) avatar.classList.add(s);
  statusEl.textContent = label || 'Ready';
}
function add(role, text) {
  const d=document.createElement('div');
  d.className='msg '+(role==='user'?'user':'bot');
  d.textContent=text;
  chat.appendChild(d); chat.scrollTop=chat.scrollHeight;
}
function speak(text) {
  if (!('speechSynthesis' in window)) { setState('', 'Ready'); return; }
  speechSynthesis.cancel();
  const u=new SpeechSynthesisUtterance(text);
  u.rate=.98; u.pitch=1.02;
  const voices=speechSynthesis.getVoices();
  const preferred=voices.find(v => /en-GB/i.test(v.lang) && /female|serena|kate|samantha|victoria/i.test(v.name)) || voices.find(v => /en-GB/i.test(v.lang)) || voices.find(v => /^en/i.test(v.lang));
  if (preferred) u.voice=preferred;
  u.onstart=()=>setState('speaking','Speaking');
  u.onend=()=>setState('','Ready');
  u.onerror=()=>setState('','Ready');
  speechSynthesis.speak(u);
}
async function ask(text) {
  text=text.trim(); if(!text) return;
  add('user',text); history.push({role:'user',content:text}); input.value='';
  setState('thinking','Thinking'); send.disabled=true; mic.disabled=true;
  try {
    const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:history.slice(-24)})});
    const data=await r.json();
    if(!r.ok) throw new Error(data.detail || 'Request failed');
    add('assistant',data.reply); history.push({role:'assistant',content:data.reply});
    modelEl.textContent='OpenRouter · '+(data.model||'model');
    speak(data.reply);
  } catch(e) {
    add('assistant','I could not reach the model: '+e.message);
    setState('','Connection error');
  } finally { send.disabled=false; mic.disabled=false; }
}
send.onclick=()=>ask(input.value);
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask(input.value)}});

const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SR){
  const rec=new SR(); rec.lang='en-US'; rec.interimResults=false; rec.continuous=false;
  mic.onclick=()=>{ try{ speechSynthesis.cancel(); rec.start(); }catch(_){} };
  rec.onstart=()=>setState('listening','Listening');
  rec.onresult=e=>{ const t=e.results[0][0].transcript; input.value=t; ask(t); };
  rec.onerror=e=>setState('', 'Mic: '+e.error);
  rec.onend=()=>{ if(!avatar.classList.contains('thinking')&&!avatar.classList.contains('speaking'))setState('','Ready'); };
}else{
  mic.disabled=true; mic.title='Speech recognition is not supported in this browser';
}
fetch('/health').then(r=>r.json()).then(d=>{modelEl.textContent='OpenRouter · '+d.model+(d.api_key_configured?'':' · key missing')}).catch(()=>{});
add('assistant','Hey — I’m online. Tap the mic or type something and talk to me.');
</script>
</body>
</html>'''


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8787"))
    uvicorn.run("openrouter_avatar:app", host="0.0.0.0", port=port, reload=False)
