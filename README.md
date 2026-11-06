# 🀄 Woodlands Mahjong Society — Practice Table

A web page where a player who has learned American Mahjong plays full games against
three computer opponents, with a coach panel beside the table. The coach answers rules
questions, gives hints, and flags costly discards. Everything it states about hands and
tiles comes from the game engine, not from the LLM.

Spec: [`specs/01-mahjong-practice-game/`](specs/01-mahjong-practice-game/PRODUCT.md).

## What's in the game
- 152 tiles, Charleston (first, optional second, blind passes, courtesy), calling with
  priority, exposures, jokers, joker swaps, dead hands, wall games, scoring.
- An **original practice card** (`cards/practice_card.json`, 34 hands) with the same
  categories as a real card. The NMJL card is copyrighted and is not served.
- Easy / Normal bots that only see what a player at the table could see.
- Coach: Hint button (engine facts + a short LLM explanation), typed questions (filtered
  to Mahjong topics), automatic notes when a discard breaks one of your closest hands.
  Capped at 40 coach messages per game; without an LLM, hints still work.

## Run locally
```bash
python3 -m venv venv
venv/bin/pip install -r requirements-dev.txt
cp .env.example .env           # fill in GROQ_API_KEY and FLASK_SECRET_KEY
venv/bin/flask --app app run --port 8080
```
Open http://127.0.0.1:8080. With no `GROQ_API_KEY`, the coach answers with engine facts only.

## Tests and simulation
```bash
venv/bin/python -m pytest -q                              # engine, API and coach tests
venv/bin/python sim.py --games 1000 --difficulty normal   # bot-only games + invariant checks
```

## Layout
| Path | What |
|---|---|
| `mahjong/` | Engine: tiles, card loader, hand matcher, game state machine, bots, coach facts |
| `cards/practice_card.json` | The practice card (data; swap with `CARD_FILE`) |
| `rules/practice_rules.md` | Rules summary used by the coach prompt |
| `app.py` | Flask app: page, game API, coach endpoint |
| `coach.py` | Coach prompt and LLM call with engine-facts fallback |
| `store.py` | SQLite storage of games (24 h expiry, anonymous session cookie) |
| `static/` | Page, styles, SVG tiles, `brand.css` + `brand/logo.svg` (branding), `config.js` (tile skin) |
| `content_filter.py`, `security.py` | Mahjong-only question filter, request filtering and rate limits |

## Branding and tiles
- `static/brand.css` and `static/brand/logo.svg` hold **placeholder** Society colors and
  mark. Replace them with the official files; nothing else needs to change.
- Tiles are drawn as SVG in code. To use the Society's Joy tile art, add one image per tile
  code to `static/skins/joy/` and set `tileSkin` in `static/config.js`.

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/card` | Card listing |
| POST | `/api/game` | New game `{difficulty: "easy"\|"normal"}` |
| GET | `/api/game/<id>` | Current view (refresh) |
| POST | `/api/game/<id>/action` | Human action (`pass`, `vote`, `courtesy`, `discard`, `swap`, `call`, `pass_call`, `mahjong`) |
| POST | `/api/game/<id>/coach` | `{kind: "hint"}` or `{kind: "question", text}` |

Deployment: see [README-deployment.md](README-deployment.md).
