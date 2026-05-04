# Annie Local UI Target: Research Session Interface

This document captures the visual and product direction for Annie Local based on a dark mobile research-session style interface.

## Design Goal

Build Annie Local into a polished private local AI interface that feels like a serious research console, not a generic chat page.

The interface should communicate:

- local AI is active
- voice state is visible
- memory/session context is present
- model performance is measurable
- user controls are simple and touch-friendly
- the product feels modern, private, and emotionally calm

## Target Visual Direction

### Overall Feel

- dark navy / black background
- subtle grid or circuit-map layer
- soft blue and orange glow accents
- futuristic but readable UI
- mobile-first layout
- calm, high-trust energy

### Top Bar

Target elements:

- hamburger/menu button on the left
- title: `Research Session`
- stop button with orange outline and speaker/mute icon
- model/brain icon button
- download/export button
- settings/sliders button

Purpose:

- makes the app feel like a controlled AI session
- gives visible exit/stop control for voice output
- hints at model, export, and settings features

### Voice State Pill

Target element:

```text
● 🔊 Speaking...
```

States to support:

- `Idle`
- `Listening...`
- `Thinking...`
- `Speaking...`
- `Offline`
- `Error`

Behavior:

- color changes by state
- pulsing dot while active
- screen-reader label for accessibility

### Orb / Core Visual

Target:

- large glowing orb centered near the top
- orange/red active state for speaking
- blue/cyan idle/listening state
- animated concentric rings
- small tick marks or waveform ring around orb

Purpose:

- gives Annie a visible “presence” without pretending to be human
- makes local AI feel alive and responsive
- creates a memorable demo moment

### Message Card

Target elements:

- rounded message bubble
- small avatar/icon to the left
- message preview text
- mini audio waveform inside bubble when voice is active
- metadata line under bubble

Example metadata:

```text
1:01 AM · 105.7 tok/s · 3.2s · 72 tok
```

Metrics to support:

- timestamp
- tokens per second
- response latency
- token count
- model name if useful
- local/remote routing badge

### Input Bar

Target controls:

- rounded text field: `Message Annie...`
- attachment button
- microphone button
- send button with paper-plane icon

Behavior:

- touch-friendly mobile layout
- keyboard-safe spacing
- mic button toggles voice capture when implemented
- send button is visually strong but not distracting

### Session Controls

Target controls:

- up/down navigation row for previous/next messages or search hits
- large check/confirm button
- optional transcript navigation

Possible uses:

- reviewing local memory
- stepping through research notes
- confirming a saved memory
- moving between search results

## Product Requirements

### Must Have

- mobile-first responsive layout
- visible local/offline status
- visible model state: idle/listening/thinking/speaking
- glowing orb state animation
- chat input and send button
- local memory indicator
- token/speed/latency metrics where available
- clear stop button for speech output

### Should Have

- export/download session button
- settings panel for model, memory, voice, and safety
- session title field
- avatar slot or project logo slot
- waveform animation for speaking/listening
- keyboard-safe mobile behavior

### Could Have

- research mode toggle
- memory search navigation
- attach file/image for future local RAG
- local transcript export
- theme variants: Michigan night, farm-grid, cyber-blue, ember-orange

## Safety and Privacy Requirements

The UI must make privacy clear without overclaiming.

Recommended badges:

- `Local model`
- `Memory: local`
- `Network: offline` when verified
- `Network: online` when any remote dependency is active

Do not show `fully offline` unless model routing, browser assets, voice components, and memory are verified local.

Crisis / emotional safety boundary should be available from settings or footer:

> Annie Local is not a therapist or emergency service. If someone may be in immediate danger, contact local emergency services. In the United States, call or text 988 for the Suicide & Crisis Lifeline.

## Implementation Notes

Suggested frontend components:

- `TopBar`
- `VoiceStatePill`
- `OrbCore`
- `MessageCard`
- `MetricsRow`
- `Composer`
- `SessionNav`
- `PrivacyBadge`
- `SettingsDrawer`

Suggested API fields:

```json
{
  "session_title": "Research Session",
  "state": "speaking",
  "model": "llama3.2",
  "routing": "local",
  "memory_mode": "local_jsonl",
  "last_latency_seconds": 3.2,
  "last_tokens_per_second": 105.7,
  "last_token_count": 72,
  "network_status": "offline_verified"
}
```

## Acceptance Criteria

- [ ] UI opens at `http://127.0.0.1:8787`
- [ ] dark mobile-first layout renders cleanly on iPhone-sized screen
- [ ] top bar includes title, stop, model, export, and settings controls
- [ ] orb changes state for idle/listening/thinking/speaking
- [ ] message card displays text preview and optional waveform
- [ ] metrics row displays timestamp, latency, tokens/sec, and token count when available
- [ ] input bar includes text field, attachment, mic, and send controls
- [ ] local/offline status is visible and truthful
- [ ] no remote dependency is hidden behind offline wording
- [ ] accessibility labels exist for voice state, stop, mic, send, and settings controls

## Build Priority

1. Static HTML/CSS mock matching this target
2. Wire mock to existing Annie Local API state
3. Add orb animation state changes
4. Add metrics display from chat responses
5. Add local/offline status badge
6. Add settings drawer
7. Add voice loop integration later, only after STT/TTS are actually wired
