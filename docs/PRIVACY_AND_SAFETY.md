# Privacy and Safety Notes

Annie Local is designed around local-first AI interaction. The project should make it easy for users to understand where their data goes, where memory is stored, and what safety boundaries apply.

## Privacy Principles

- Prefer local model routing.
- Keep memory local and visible to the user.
- Avoid hidden remote calls.
- Avoid unnecessary logging.
- Use synthetic examples in tests and documentation.
- Clearly disclose any dependency that needs internet access.

## Local Memory Principles

Local memory should be treated as sensitive because it may contain user prompts, emotional context, private notes, or personal preferences.

Before using Annie Local with sensitive data, verify:

- where memory is stored
- whether memory can be deleted
- whether memory is encrypted
- whether logs duplicate memory content
- whether other local users can read the memory file

## Offline-First Verification

Before claiming a deployment is fully offline, verify:

- [ ] model endpoint is local
- [ ] browser assets load locally
- [ ] no analytics are enabled
- [ ] no remote fonts/scripts/CDNs are required
- [ ] STT/TTS components, if enabled, run locally
- [ ] network access is not required for core operation after setup

## Safety Principles

- Annie Local may provide supportive conversation, but it is not a therapist.
- It should not present itself as a clinician, emergency service, or medical tool.
- Emotional-support behavior should include clear boundaries.
- Crisis language should route users toward trusted humans and emergency resources.

## Crisis Boundary

Annie Local is not a crisis service. It cannot guarantee detection or response.

If someone may be in immediate danger, contact local emergency services. In the United States, call or text **988** for the Suicide & Crisis Lifeline.

## What Not To Do

Do not use Annie Local as the only support for serious emotional distress, medical decisions, legal decisions, child safety decisions, or emergency response.
