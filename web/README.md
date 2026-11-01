# Failure Investigator web app

The web app is the evidence-facing part of the prototype. It works without a backend by
using a clearly labelled replay run, then switches to the FastAPI service when
`NEXT_PUBLIC_API_BASE_URL` is available.

## Run locally

```powershell
Copy-Item .env.example .env.local
npm.cmd install
npm.cmd run dev
```

Open [http://localhost:3000](http://localhost:3000). Use `npm.cmd run build` for a
production build, or run it through the root Docker Compose stack.

## Backend contract

The UI consumes the research APIs in the project plan plus these assistant endpoints:

- `POST /api/research/{run_id}/assistant/messages` — returns Server-Sent Events named
  `assistant.text.delta` and `assistant.final`.
- `POST /api/research/{run_id}/assistant/transcriptions` — accepts a maximum 30-second,
  16 kHz mono WAV upload and returns `{ text, language }`.
- `POST /api/research/{run_id}/assistant/speech` — accepts `{ message_id }` and returns
  playable audio.

The assistant panel only displays citations returned by the backend. Replay mode has no
voice service and deliberately keeps typed, cited chat available as the fallback.
