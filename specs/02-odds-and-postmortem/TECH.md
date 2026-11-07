# Completion odds and end-of-game post-mortem — tech
Back to [PRODUCT.md](PRODUCT.md)

## Approach
A new engine module `mahjong/odds.py` estimates completion odds by Monte Carlo
simulation over the human's unseen pool, using **common random numbers**: one set of
seeded shuffles is drawn per call and reused for every hand and every candidate discard,
so comparisons between them are not distorted by sampling noise. To stay fast in pure
Python, each candidate binding is reduced once to its "missing list" (tile, count,
joker OK), so a simulated run only counts a handful of tile codes. Only bindings that
are feasible and need no more tiles than draws left are simulated, capped at the
nearest ~40 by tiles away. The coach facts (Hint, pass/discard suggestion, feedback)
switch from `0.5 ** needed` to these odds. `Game` records each human decision with a
compact snapshot and the odds computed at that moment (computed once, reused by feedback),
and a pure function turns that record into the post-mortem after the game ends.

Rejected:
- **Closed-form (hypergeometric) odds**: exact for one tile type, but jokers and multiple
  simultaneous needs make it wrong in ways hard to see; simulation handles both directly.
- **Recompute the whole post-mortem at game end from snapshots**: ~60 decisions × odds
  ≈ 20 s at the end; storing odds at decision time spreads the cost (<1 s per move) and
  the discard feedback needs those numbers anyway.

Deviations made during implementation (code proved the plan wrong):
- **Recording lives in `mahjong/review.py`, called by `app.py`, not inside `Game.act()`.**
  Inside the engine it would run for the simulator's autopilot too and make
  `sim.py --games 1000` take hours. The engine is unchanged; `history` is still part of
  the stored game state.
- **Post-mortem renders in the coach panel**, not under the score table: the action bar is
  one row high and a long review there pushes the rack off screen.
- **Missed switch also requires the discard to cost the most likely hand >= 1 point**, so a
  harmless discard that happens to tie between hands is not flagged.

## Prior art
- id=6957 ✓ — `_uses` check in `coach_facts.py` stopped contradictory advice; keep it for
  the "why" text and missed-switch attribution.
- Spec 01 rule 16 (engine facts only) and rule 17 (Hint never uses the LLM) are kept and
  extended to the post-mortem.

## Changes
- **New `mahjong/odds.py`**: `unseen_pool(view)`, `draws_left(view)`,
  `hand_odds(card, holding, visible, draws, seed, runs)` → list of (odds, needed,
  binding); `discard_odds(...)` → {tile: total odds of top hands after removing it}.
  Seed derived from the view (rack, discards count, wall count) so repeated Hints agree.
  Runs: ~1000 (tuned in phase 1 to meet the 1.5 s bound).
- **`mahjong/coach_facts.py`**: `closest_hands` ranks by odds and adds `odds` and
  per-tile `unseen`; `hint_facts` uses `discard_odds` for pass/discard; `move_feedback`
  takes the stored before-odds and uses the 1-point threshold; `facts_text` prints odds,
  unseen counts and the draw-only caveat. Keep the `_uses` reasons.
- **`mahjong/matcher.py`**: unchanged API; bots keep `choose_discards`/`ranked`.
- **New `mahjong/review.py`** (see deviations): before applying a human action, append to
  `game.history` {turn, prompt type, action, snapshot (rack, own exposures, visible
  counts, wall count), top-hand odds, discard odds when discarding, hidden locations of
  the top hand's missing tiles}. After the action, fill the after-odds. `view_for` never
  includes `history`.
- **New `mahjong/postmortem.py`**: `build(card, history, result, names)` → {key_moments,
  timeline, hindsight} applying PRODUCT rules 14–19. Pure function, no I/O.
- **`app.py`**: action endpoint reuses the recorded odds for feedback; new
  `GET /api/game/<id>/postmortem` returns 409 while the game is in progress, else the
  post-mortem (cached in game state after first build).
- **`static/game.js` / `app.css`**: on `over`, fetch and render the post-mortem under the
  result box (Key moments list, collapsible `<details>` timeline, Hindsight box); show
  odds and unseen counts in Hint text (already plain text from the engine).
- **Tests**: new `tests/test_odds.py`, `tests/test_postmortem.py`; additions to
  `test_api.py` for the 409/no-leak rules.
- **Schema/config/dependencies**: none. Game state JSON gains `history` and
  `postmortem`; old in-progress games load with `history` defaulting to empty.

## Phases
1. **Odds engine**: `odds.py` + tests. Verify: `pytest tests/test_odds.py -q` → all pass,
   including timing bound.
2. **Coach on odds**: Hint, suggestions and feedback use odds. Verify: `pytest -q` → all
   pass (existing coach tests updated where they asserted the old wording).
3. **Recording**: `Game.history` + no-leak tests. Verify: `pytest -q` → pass;
   `python sim.py --games 1000 --difficulty normal` and `easy` → 0 exceptions, 0 violations.
4. **Post-mortem**: `postmortem.py`, endpoint, tests with a scripted game. Verify:
   `pytest -q` → pass.
5. **UI**: render odds and post-mortem. Verify: run the app, play a game to the end
   in a browser (or headless script hitting the API + screenshot), post-mortem visible.

## Autonomy contract
- May do without asking: edit files on `secmain`, create a virtualenv and install
  `requirements-dev.txt`, add/modify tests, run the simulator, start a local dev server,
  commit and push to `secmain` once a phase's verification passes.
- Must stop and ask: adding or bumping anything in `requirements.txt`, touching `main`,
  force-push, changing bot strategy.
- Stop conditions: a Done-when check fails twice the same way; the 1.5 s Hint bound
  cannot be met without a new dependency (e.g. numpy); an assumption in PRODUCT.md
  turns out false.

## Risks
- **Speed**: pure-Python simulation too slow on the server → phase 1 timing test; fall
  back to fewer runs or a smaller binding cap before asking about numpy.
- **Noise**: odds jitter could produce feedback after following the Hint → common random
  numbers + seeded runs + 1-point threshold; covered by the "following the Hint never
  triggers feedback" test.
- **Optimism**: the simulation assumes the player keeps every useful draw; odds are
  upper-bound-ish for the draw-only model. Acceptable for teaching; stated in the caveat.
- **State size**: history adds ~1 KB per decision to stored JSON; fine for SQLite.
