# Practice Table — Deployment

One Flask app serves the page, the game API and the coach. State lives in a SQLite file.

## Configuration
All settings come from environment variables (or `.env`, never committed). See
`.env.example`. Required in production:

- `FLASK_SECRET_KEY`: long random string (signs the session cookie).
- `GROQ_API_KEY`: coach LLM. Optional: without it, hints use engine facts only.
- `GAME_DB_PATH`: a writable path for the SQLite file.
- `COOKIE_SAMESITE=None` **only** when the page is embedded in an iframe on another site
  (requires HTTPS). Leave `Lax` for a direct link.

## Serve
```bash
pip install -r requirements.txt
gunicorn -w 2 -b 127.0.0.1:8080 app:app
```
Put it behind a reverse proxy with HTTPS (e.g. Nginx + Let's Encrypt), proxying `/` to the
gunicorn port and forwarding `X-Forwarded-For` so rate limits see real client IPs.

Notes:
- Rate limits and the content filter's IP reputation are in memory, per worker.
- Games expire after `GAME_TTL_HOURS` (default 24); expired rows are deleted on write.

## Embedding on the Society's site
Either link to the page, or embed it:
```html
<iframe src="https://<practice-table-host>/" style="width:100%;height:860px;border:0"
        title="Mahjong practice table"></iframe>
```
For the iframe, set `COOKIE_SAMESITE=None` and serve over HTTPS.

## Security
- Request filtering and per-IP rate limits (`security.py`): game moves 240/min, coach
  20/min, everything else 20/min.
- Typed coach questions pass a two-stage Mahjong-only filter (`content_filter.py`).
- The coach is capped per game (`COACH_MAX_MESSAGES`, default 40).
- The coach only receives what the human player can see.

## Checks
```bash
curl https://<practice-table-host>/api/health
```
`coach` in the response is `llm` when the Groq key is configured, `engine-only` otherwise.
