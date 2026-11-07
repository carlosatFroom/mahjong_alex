# Completion odds and end-of-game post-mortem
Status: implemented    ·    Date: 2026-11-07

## Problem
The coach ranks hands by "tiles away", so a hand needing 2 tiles with 1 copy left
unseen ranks the same as one needing 2 tiles with 7 copies left. Learners chase hands
the table has already made nearly impossible and never learn to count tiles. When the
game ends there is no review, so the player cannot tell bad luck from a bad decision.

## Outcome
The Hint ranks hands by the chance of finishing them, computed from every tile the
player can see, and shows how many copies of each needed tile are still unseen. When a
game ends, the player gets a post-mortem: the 3 key moments first (where a hand
collapsed and why, where they should have switched hands, costly discards), a full
turn-by-turn list below, and a clearly separate hindsight section showing where their
missing tiles really were.

## Behavior

### Odds
1. The **unseen pool** is the 152-tile set minus the human's concealed rack, the human's
   exposures, every discard, and every other player's exposures. It never uses hidden
   information (bot racks, wall order).
2. **Draws left** is the number of wall tiles the human will draw if no more calls
   happen, counted in turn order from the current state.
3. A hand's **completion odds** are estimated by simulation: shuffle the unseen pool,
   give the human the first *draws left* tiles, and check whether the rack plus those
   tiles completes the hand (jokers drawn or held fill groups of 3+ only, as the matcher
   already enforces). Repeat a fixed number of times; odds = completions ÷ runs.
4. Odds count the human's own draws only, not tiles they could call from discards. The
   Hint says so in one line ("Odds count your own draws only; calling discards can
   improve exposed hands").
5. Simulation is seeded from the game state, so pressing Hint twice on the same turn
   shows the same numbers.
6. A hand already complete has odds 100%. A hand whose needed tiles are all visible has
   odds 0% and is not listed (current `feasible()` behaviour, kept).
7. The Hint lists the 3 hands with the **highest odds**, most likely first; ties go to the
   higher point value. Each line shows: hand, points, concealed/exposed, odds as a
   percentage, tiles away, the concrete version, and each needed tile with its unseen
   count, e.g. "2× 5 Dot (joker OK) · 3 unseen".
8. The suggested discard and suggested Charleston pass pick the tile whose removal keeps
   the highest total odds across the top hands.
9. Automatic discard feedback uses the same scoring as the Hint. It appears only when the
   chosen discard lowered the total odds by at least 1 percentage point more than the
   best discard would have, and names the odds of both. Following the Hint never
   triggers it.
10. Bots keep their current tiles-away scoring; bot behaviour and difficulty are unchanged.

### Recording
11. At each human decision (Charleston pass, courtesy pass, discard, call, declining a call)
    the game records what the human could see at that moment, the action taken, and the
    engine's odds for the top hands before and after the action.
12. The record also stores, server-side only, where each tile missing from the human's
    top hand actually was at that moment (a bot's rack or the wall). This is never sent
    to the browser while the game is in progress.

### Post-mortem
13. When the game ends (win by anyone, or wall game), the page shows a post-mortem as a
    "Game review" message in the coach panel (the score stays in the table area). It is written entirely by the engine; it never calls the LLM.
14. **Collapse**: when the odds of the hand that was most likely at the previous decision
    drop by half or more and by at least 5 points before the next decision, the
    post-mortem names the turn and the newly visible tiles that caused it ("Hazel
    discarded the 4th 2 Dot on turn 11; Like Numbers fell from 18% to 2%").
15. **Missed switch**: when the human's discard protected a hand whose odds were less
    than half those of the most likely hand, the post-mortem flags the first turn of each
    such streak and names both hands with their odds.
16. **Costly discard**: every discard that triggered feedback (rule 9) appears, with the
    odds lost.
17. The 3 moments with the largest odds impact are shown first under "Key moments".
    The full turn-by-turn list (turn, action, top hand and its odds) is collapsed below.
18. A separate section titled "Hindsight — you couldn't have known this" shows, for
    the hand the human was building at game end, where its missing tiles were (which
    bot's rack, or the wall). It appears only after the game is over.
19. A game where the human made no recorded decision shows "Nothing to review yet."

## Done when
1. `pytest` passes and includes tests for: unseen pool excludes rack, exposures and
   discards and never reads bot racks or the wall; a hand needing tiles with 0 unseen
   copies is excluded; with all needed copies unseen and many draws left, odds are higher
   than with 1 copy unseen; the same view gives identical odds twice; the Hint lists hands
   in descending odds; following the suggested discard never produces feedback; the
   in-progress game view and API response contain no post-mortem or hindsight data; a
   scripted game produces a collapse, a missed switch and a costly discard in the
   post-mortem; a game with no decisions returns "Nothing to review yet."
2. `python sim.py --games 1000 --difficulty normal` and `--difficulty easy` still finish
   with 0 exceptions and 0 invariant violations.
3. A Hint request on the dev machine returns in under 1.5 s (test with a timing assert,
   generous bound).
4. With `flask run`, a browser game played to the end shows odds in the Hint and a
   post-mortem with Key moments, the turn-by-turn list and the Hindsight section.
5. `requirements.txt` is unchanged.

## Non-goals
- Counting tiles that could be called from discards (odds are draw-only for now).
- Ranking by expected score (odds × points); may come later as a toggle.
- A board-wide tile counter panel.
- LLM-written post-mortem.
- Changing bot strategy or difficulty.
- Saving post-mortems or game history beyond the existing 24-hour game expiry.
