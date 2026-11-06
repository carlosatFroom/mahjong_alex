# Mahjong Practice Table — tech
Back to [PRODUCT.md](PRODUCT.md)

## Approach
A deterministic Python game engine (`mahjong/` package) owns all rules and state. Flask
exposes it as a small JSON API and serves a plain-JS, no-build frontend. Bots are code
heuristics built on the same hand matcher the engine uses for validation. The coach is
the existing Groq provider with a new prompt: system prompt = original rules summary +
active card (whole, no retrieval), user turn = the human-visible game state plus
"engine facts" (closest hands, tiles needed, joker eligibility, what the last move broke).
The LLM only phrases; numbers and hand names come from the engine. Game state is stored
as JSON in SQLite keyed by an anonymous session id.

Rejected:
- **RAG over the rulebook**: content is a few thousand tokens, fits in the prompt whole;
  retrieval would add a vector DB and the risk of missing rules, for no gain.
- **LLM-driven bots / LLM referee**: slow, costly per turn, and unreliable at joker and
  "any suit" matching; would produce illegal moves.
- **In-browser JS engine**: cheaper hosting, but splits rules across two languages and
  loses pytest coverage; the coach would have to trust client-sent state.

## Prior art
- id=1549 ✓ — loading the card from `year2025.txt` into the system prompt worked; keep the
  "whole card in prompt" approach, but move the card to structured JSON so the engine can
  use it too.
- id=1536 / id=1546 ✓ — Groq-only provider and the Mahjong content filter are kept and
  reused as-is for free-text questions.
- README knowledge mentioning FastAPI + Ollama is stale: the code moved to Flask + Groq
  (`app.py`); `main.py` (FastAPI) is removed.

## Changes

### New: `mahjong/` package (engine, no Flask imports)
- `tiles.py` — tile model and the 152-tile set; stable string codes (e.g. `5B`, `NW`,
  `GD`, `F`, `J`) shared with the frontend.
- `card.py` — load a card JSON; hand = list of groups, each with size, tile kind
  (number / wind / dragon / flower / year digit), suit variable (A/B/C, "any", "opposite"),
  number variable with offsets (for consecutive runs) or fixed numbers, plus `concealed`
  flag and point value.
- `matcher.py` — for a rack + exposures and one hand: enumerate suit/number bindings,
  compute missing tiles with jokers allowed only in groups ≥ 3; returns exact match or
  distance and needed tiles. Used for Mahjong validation, dead-hand checks, bots, hints.
- `charleston.py` — pass sequence state machine (first mandatory, second optional with
  stop vote, courtesy 0–3, blind pass on last pass).
- `game.py` — game state machine: deal, Charleston, draw/discard, call window with
  priority resolution, exposures, joker swap, Mahjong claim, dead hand, wall game,
  scoring. `view_for(seat)` returns only what that seat may see (used by API, bots, coach).
- `bots.py` — Easy and Normal policies, each only receiving `view_for(seat)`.
- `coach_facts.py` — builds the engine-facts block for the coach from the human view.

### New data
- `cards/practice_card.json` — original ~35-hand card (categories: year, 2468, like
  numbers, quints, consecutive runs, 13579, winds & dragons, 369, singles & pairs).
- `rules/practice_rules.md` — original concise rules summary used in the coach prompt.
- `year2025.txt` stays in the repo but is not loaded by default; an optional env var
  `CARD_FILE` selects another card JSON for private use.

### New: storage
- `store.py` — SQLite (stdlib `sqlite3`) table `games(id, session_id, state_json,
  coach_count, updated_at)`; deletes rows older than 24 h on write. DB path from env var.

### `app.py` (Flask)
- Keep `/api/health`, rate limiting, security middleware, content filter, Groq provider.
- Replace `/api/chat` with:
  - `POST /api/game` — new game (difficulty) → human view.
  - `GET /api/game/<id>` — current human view (refresh).
  - `POST /api/game/<id>/action` — human action (pass, discard, call, pass-on-call,
    expose, swap joker, declare Mahjong, Charleston stop/continue); engine runs bot
    turns until the human must act again; returns new view + events log.
  - `POST /api/game/<id>/coach` — `{kind: hint|question|feedback, text?}`; enforces
    40/game cap; falls back to plain engine facts on cap or LLM error.
- `GET /` serves the game page.
- Existing `/api/stats` and `/api/ip-stats/<ip>` routes stay unchanged.

### Frontend: `static/`
- `index.html`, `game.js` (render + API calls), `tiles.js` (SVG tile faces, skin loader),
  `brand.css` (CSS variables: colors, fonts), `brand/logo.*`, `skins/default/`.
- Brand values extracted from woodlandsmahjongsociety.com as placeholders, replaced
  when Alex sends official files.

### Removed
- `main.py`, `image_quality.py`, vision branches in `llm_providers.py` / `content_filter.py`
  that only serve image input, `mahjong-tutor-widget.js`, `test-widget.html`, old
  `index.html`. README.md / README-deployment.md rewritten for the new app.

### Dependencies
- `requirements.txt`: remove `fastapi`, `uvicorn`, `python-multipart`. No new runtime
  dependencies (SQLite is stdlib). Existing pins kept unless the vulnerability scan flags
  them.
- `requirements-dev.txt` (pinned): `pytest`. Browser test via Claude-in-Chrome, no new
  dependency.

## Phases
1. **Cleanup**: remove FastAPI/vision/widget files and deps. Verify:
   `git ls-files | grep -E 'main.py|image_quality|widget'` → empty; `flask run` + `curl
   /api/health` → 200.
2. **Tiles + card + matcher**: Verify: `pytest tests/test_tiles.py tests/test_matcher.py`
   → pass, including win/near-miss pair for every hand in `practice_card.json`.
3. **Game state machine + Charleston + scoring**: Verify: `pytest tests/test_game.py
   tests/test_charleston.py tests/test_scoring.py` → pass.
4. **Bots + simulator**: Verify: `python sim.py --games 1000 --difficulty easy` and
   `normal` → 0 exceptions, 0 invariant violations.
5. **API + SQLite store**: Verify: `pytest tests/test_api.py` → new game, refresh
   returns same state, action loop reaches human turn, expired game → 404.
6. **Coach**: Verify: `pytest tests/test_coach.py` → payload has no bot-concealed tiles;
   LLM-down fallback returns 200 with facts; 41st message refused.
7. **Frontend + branding**: Verify: Done-when #3 and #8 in a real browser session.
8. **Docs + scan**: Verify: `/scan-vulnerabilities` clean; README describes new app.

## Autonomy contract
- May do without asking: work on branch `secmain`; edit/create/delete files listed in
  Changes; create a venv and install pinned deps; run tests, the simulator and local
  Flask servers; drive a local browser; commit and push to `secmain`.
- Must stop and ask: deploying anywhere; merging to `main`; adding any paid service or
  second LLM provider; adding a runtime dependency not listed here; using any third-party
  tile art (the Society's own Joy tiles are allowed once Alex sends the files); serving the real NMJL card.
- Stop conditions: a Done-when check fails twice the same way; a PRODUCT.md rule turns
  out ambiguous in code (e.g. a scoring or call-priority edge case not covered).

## Risks
- **Matcher correctness** (jokers, "any/opposite suit", consecutive numbers, year hands)
  is the core risk → Phase 2 requires a win/near-miss pair for every card hand.
- **Rule details from memory may be slightly off** (scoring multipliers, call priority) →
  rules are centralized in `practice_rules.md` + tests, so a correction from Alex is one
  edit; ask Alex to review that file and the card before launch.
- **Bot strength** may feel too weak/strong → sim prints win rates per difficulty;
  tune before the browser test.
- **Groq model retirement** (has happened twice) → model name stays in env config;
  engine-facts fallback keeps hints working.
- **Brand placeholders** scraped from the public site may be low resolution → isolated
  in `brand.css` + one logo file for a single swap.
