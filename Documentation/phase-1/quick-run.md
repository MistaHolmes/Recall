## Quick run & common checks

Activate virtualenv and run the bot (development):

```bash
source venv/bin/activate
python bot.py
```

Kill and restart (if running in background):

```bash
pkill -f "python bot.py" || true
python bot.py &
```

Smoke checks:
- Verify bot logs into Discord and registers guild slash commands.
- Upload a PDF via `/upload` and verify indexing message (e.g. 127 chunks indexed).
- Run `/ask` for a simple question about the uploaded PDF and observe an answer.

Common troubleshooting:
- If the bot fails to generate answers, check LLM provider config in `.env` and `config.py`.
- If `_pool is None` errors occur, ensure `init_db()` is called in `setup_hook()` (already present).
