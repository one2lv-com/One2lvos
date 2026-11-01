# Quick install

```bash
cd ai-lobby
npm install
npm start
```

Then open **http://localhost:8787** in your browser.

Admin login: set `LOBBY_ADMIN_USER` and `LOBBY_ADMIN_PASSWORD` in `.env` (see `.env.example`). With no password set, admin login is disabled.

First-time sign-in unlocks Settings (API keys, models, system prompt), File Manager, and Terminal. The chat lobby, skills, and memory are open to anyone on the local machine.

To verify the four NVIDIA models work end-to-end:

```bash
node test-smoke.mjs   # plain chat
node test-tools.mjs   # agentic tool call (web_scrape)
```

See `README.md` for the full reference.
