# Mahjong Practice Table (American rules, with AI coach)
Status: approved    ·    Date: 2026-11-05

## Problem
The current product is a chatbot that asks players to photograph their tiles and type
questions. Players who have just learned American Mahjong need *table time* to practice,
not a chat box: they have no game to practice in unless they gather three other people.
The result is that nobody uses the tool.

## Outcome
A player opens a Woodlands Mahjong Society–branded web page and plays a complete
American Mahjong game against 3 computer opponents, at any hour, alone. A coach panel
beside the table answers rules questions, gives hints on request, and points out
costly moves, using facts computed by the game engine (never guesses).

## Behavior

### Game
1. The game uses 152 tiles: 3 suits (Dots, Bams, Craks) × 9 numbers × 4, 16 winds,
   12 dragons, 8 flowers, 8 jokers.
2. One human seat plus 3 bot seats. East (dealer) receives 14 tiles and discards first;
   the others receive 13. Seat assignment is random each game.
3. The Charleston is enforced: the first Charleston (right, across, left) is mandatory;
   the second (left, across, right) is optional and stops if any player declines; then an
   optional courtesy pass of 0–3 tiles across. Blind passing is allowed on the last pass
   of each Charleston. Jokers can never be passed.
4. Play proceeds counter-clockwise: draw, then discard. Any player may call the latest
   discard to complete an exposure (pung, kong, quint, or more) or to declare Mahjong;
   a Mahjong call beats an exposure call; among equal calls, the next player in turn wins.
   Calling a tile for a pair is only allowed when it completes Mahjong.
5. Jokers substitute in groups of 3 or more identical tiles, never in singles or pairs.
   A discarded joker is dead and cannot be called.
6. On their turn, a player may swap the real tile for a joker in any player's exposure.
7. A player declares Mahjong only when their 14 tiles match one hand on the active card,
   respecting concealed (C) vs exposed (X) requirements. The engine validates the claim;
   an invalid claim by the human is rejected with the reason.
8. When the human's exposures can no longer form any hand on the card, the human's hand
   is declared dead and the human plays out the game without being able to win. Bots
   never declare each other dead.
9. When the wall runs out with no winner, the game ends as a wall game (draw).
10. Scoring: the winner receives the hand's card value from each player (double from the
    discarder if won on a discard; double from everyone on a self-drawn win; ×2 more if
    the hand contains no jokers, except singles-and-pairs hands). The scores are shown
    at game end.

### Card
11. The engine plays from a card stored as a data file. The default card is an
    **original practice card** (~35 hands, same categories as the real card, different
    patterns) written for this project. The real NMJL card is never served publicly;
    it may be loaded only by local configuration for private use, or publicly once Alex
    has written NMJL permission.

### Bots
12. The human chooses difficulty at game start: *Easy* or *Normal*, for the whole table.
    Easy bots pick a target hand after the Charleston, discard tiles outside it, and
    only call to win. Normal bots re-evaluate targets, call exposures, swap jokers, and
    avoid discarding tiles that complete an opponent's visible exposure.
13. Bots never see hidden information (other players' concealed tiles, the wall order).

### Coach
14. The coach panel is always visible next to the table. It offers:
    a) free-text rules questions at any time;
    b) a "Hint" button: suggests what to pass (Charleston) or discard (play), with the
       3 closest hands and the tiles each still needs;
    c) automatic short feedback after a move that reduces the human's best-hand options
       (e.g. "that 5 Bam was in 2 of your 3 closest hands").
15. The coach sees only what the human can see: their own rack, all exposures, all
    discards, the card. It never reveals or uses bots' hidden tiles or the wall.
16. Every hand name, tile count, and "tiles needed" figure the coach states comes from
    the engine, not from the LLM.
17. The coach is capped at 40 LLM messages per game; existing per-IP rate limits stay.
    When the cap is reached or the LLM provider fails, the Hint button still works and
    shows the engine facts as plain text, without LLM wording.
18. Free-text questions pass through the existing content filter (Mahjong topics only).
    Hint and automatic feedback do not (they carry no user text).

### Page
19. Served by Flask as a standalone page, embeddable in the Society's website with an
    iframe or a link. Laid out for desktop and tablet landscape; on a phone it loads but
    is not optimized.
20. Branded with the Woodlands Mahjong Society look (logo, colors, fonts) via one
    stylesheet of CSS variables and one logo file, so official assets swap in with a
    single change. Footer: "Woodlands Mahjong Society practice table", with links to
    the club's website and Instagram. No fundraising text.
21. Tile faces are original SVG generated in code by default. Tile art is a swappable
    "skin" folder so the Society's own "Joy" tile artwork can replace it once Alex
    supplies the image files (permission is covered: it is the Society's set). Tile
    backs use the brand colors.
22. No login. A game survives a page refresh (stored server-side under an anonymous
    session cookie) and expires after 24 hours. No stats or history.
23. Photo upload and image analysis are removed.

## Done when
1. `pytest` passes and includes: tile set is exactly 152 with the counts in rule 1;
   Charleston sequence and stop rules; jokers rejected in singles/pairs and in passes;
   for **every** practice-card hand, one winning example that validates and one near
   miss that does not; joker swap; call priority; dead-hand detection; scoring cases.
2. `python sim.py --games 1000 --difficulty normal` and `--difficulty easy` both finish
   with 0 exceptions and 0 invariant violations (tile conservation = 152 every turn,
   no illegal exposure, no player holding a passed joker), and print win/wall-game counts.
3. With `flask run`, a browser session plays one full game as the human through to
   Mahjong or a wall game, including the Charleston, at least one call, and at least one
   coach Hint whose reply names engine-computed closest hands.
4. A coach request with the LLM provider disabled returns the plain engine-facts hint
   (HTTP 200), and the 41st coach message in a game is refused with a clear message.
5. A coach request for a game returns no tile that is concealed in a bot's rack
   (test asserts the prompt payload contains only the human-visible state).
6. `/scan-vulnerabilities` reports no known vulnerabilities in `requirements.txt`.
7. `git ls-files` no longer contains `main.py`, `image_quality.py`, and the vision code
   path; `requirements.txt` contains no `fastapi`, `uvicorn`, `python-multipart`.
8. The served page has the brand CSS-variable file and logo, and the footer links.

## Non-goals
- RAG / vector database for the rules (rules + card fit in the prompt).
- Multiplayer between humans, accounts, stats, game history.
- End-of-game replay review by the coach.
- Phone-optimized layout.
- Publicly serving the real NMJL card without permission.
- A second paid LLM provider.
- Fundraising/charity content.
- Third-party tile artwork (the Joy tiles are the Society's own, not third-party).
