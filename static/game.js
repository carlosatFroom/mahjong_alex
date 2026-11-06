(function () {
  const T = window.MJTiles;
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "wms-practice-game";
  const SIZE_NAMES = { 3: "pung", 4: "kong", 5: "quint", 6: "sextet" };

  const state = { gameId: null, view: null, selected: [], blind: 0, busy: false, lastHand: [] };

  // ---------------------------------------------------------------- helpers
  function save(id) { try { localStorage.setItem(STORAGE_KEY, id); } catch (e) { /* private mode */ } }
  function saved() { try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; } }

  async function api(path, body) {
    const opts = body === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    };
    const res = await fetch(path, { credentials: "same-origin", ...opts });
    let data = {};
    try { data = await res.json(); } catch (e) { /* empty body */ }
    return { ok: res.ok, status: res.status, data };
  }

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function tile(code, size) {
    const n = el("span", "tile" + (size ? " " + size : ""));
    n.innerHTML = T.svg(code);
    n.title = T.name(code);
    n.setAttribute("aria-label", T.name(code));
    return n;
  }

  function backs(count, size) {
    const wrap = el("div", "backs");
    for (let i = 0; i < count; i++) {
      const n = el("span", "tile " + size);
      n.innerHTML = T.back();
      wrap.appendChild(n);
    }
    wrap.setAttribute("aria-label", `${count} hidden tiles`);
    return wrap;
  }

  function exposureRow(exps, size) {
    const row = el("span", "exposures");
    exps.forEach((e) => {
      const g = el("span", "exposure");
      e.tiles.forEach((t) => g.appendChild(tile(t, size)));
      row.appendChild(g);
    });
    return row;
  }

  const rel = (offset) => (state.view.seat + offset) % 4;
  const nameOf = (seat) => (seat === state.view.seat ? "You" : state.view.names[seat]);

  // ----------------------------------------------------------------- render
  function render() {
    const v = state.view;
    if (!v) return;
    [["seat-right", 1], ["seat-across", 2], ["seat-left", 3]].forEach(([id, off]) => renderSeat($(id), rel(off)));
    $("me-name").textContent = `You · ${v.seat_wind}` + (v.dead ? " · dead hand" : "");
    const myExp = $("me-exposures");
    myExp.replaceChildren(...exposureRow(v.exposures[v.seat], "sm").childNodes);
    renderStatus();
    renderDiscards();
    renderLog();
    renderRack();
    renderActions();
  }

  function renderSeat(node, seat) {
    const v = state.view;
    node.replaceChildren();
    node.classList.toggle("active", v.phase === "play" && v.current === seat);
    node.appendChild(el("span", "seat-name", `${v.names[seat]} · ${v.winds[seat]}`));
    const size = node.id === "seat-across" ? "sm" : "xs";
    if (v.reveal) {
      const r = el("div", "reveal");
      v.reveal[seat].forEach((t) => r.appendChild(tile(t, "xs")));
      node.appendChild(r);
    } else {
      node.appendChild(backs(v.rack_counts[seat], size));
    }
    node.appendChild(exposureRow(v.exposures[seat], "xs"));
  }

  function renderStatus() {
    const v = state.view, p = v.prompt || {};
    const s = $("status");
    s.replaceChildren();
    const msg = {
      pass: `Charleston (${p.charleston}): choose 3 tiles to pass <b>${p.direction}</b>.`,
      vote: "First Charleston done. Do you want a second Charleston?",
      courtesy: `Courtesy pass: the player across offers ${p.max} tile(s). Choose up to ${p.max} to swap.`,
      discard: "Your turn: pick a tile to discard, or declare Mahjong.",
      call: p.tile ? `${nameOf(p.from)} discarded <b>${T.name(p.tile)}</b>. Call it?` : "",
      over: "Game over.",
    }[p.type] || "Waiting…";
    const span = el("span");
    span.innerHTML = msg;  // prompt text is built from fixed strings and tile names only
    s.appendChild(span);
    const info = el("span", "muted", ` · Wall: ${v.wall_count}`);
    info.style.color = "rgba(255,255,255,.7)";
    s.appendChild(info);
  }

  function renderDiscards() {
    const v = state.view;
    const d = $("discards");
    d.replaceChildren();
    v.discards.forEach((x, i) => {
      const t = tile(x.tile, "");
      t.title = `${T.name(x.tile)} — ${nameOf(x.seat)}`;
      if (i === v.discards.length - 1) t.classList.add("last");
      d.appendChild(t);
    });
  }

  function renderLog() {
    const log = $("log");
    log.replaceChildren(...state.view.log.slice(-14).map((line) => el("li", "", line)));
    log.scrollTop = log.scrollHeight;
  }

  function renderRack() {
    const v = state.view, p = v.prompt || {};
    const rack = $("rack");
    rack.replaceChildren();
    const selectable = ["pass", "courtesy", "discard"].includes(p.type);
    const newTiles = diffNew(state.lastHand, v.hand);
    v.hand.forEach((code, i) => {
      const b = el("button", "tile");
      b.type = "button";
      b.innerHTML = T.svg(code);
      b.title = T.name(code);
      b.setAttribute("aria-label", T.name(code));
      if (state.selected.includes(i)) b.classList.add("selected");
      if (newTiles.has(i)) b.style.filter = "drop-shadow(0 0 4px var(--brand-accent))";
      b.disabled = !selectable || state.busy;
      b.addEventListener("click", () => toggle(i));
      b.addEventListener("dblclick", () => { if (p.type === "discard") { state.selected = [i]; discard(); } });
      rack.appendChild(b);
    });
  }

  function diffNew(oldHand, newHand) {
    // Highlight tiles that arrived since the last render (draws, received passes).
    const pool = [...oldHand];
    const out = new Set();
    if (!oldHand.length) return out;
    newHand.forEach((t, i) => {
      const j = pool.indexOf(t);
      if (j >= 0) pool.splice(j, 1); else out.add(i);
    });
    return out;
  }

  function limit() {
    const p = state.view.prompt || {};
    if (p.type === "pass") return 3 - state.blind;
    if (p.type === "courtesy") return p.max;
    if (p.type === "discard") return 1;
    return 0;
  }

  function toggle(i) {
    const p = state.view.prompt || {};
    if (state.view.hand[i] === "J" && (p.type === "pass" || p.type === "courtesy")) {
      coachNote("Jokers can never be passed.");
      return;
    }
    const at = state.selected.indexOf(i);
    if (at >= 0) state.selected.splice(at, 1);
    else {
      if (limit() === 1) state.selected = [];
      if (state.selected.length < limit()) state.selected.push(i);
    }
    renderRack();
    renderActions();
  }

  function button(label, cls, fn, disabled) {
    const b = el("button", cls, label);
    b.type = "button";
    b.disabled = !!disabled || state.busy;
    b.addEventListener("click", fn);
    return b;
  }

  function renderActions() {
    const v = state.view, p = v.prompt || {};
    const a = $("actions");
    a.replaceChildren();
    const picked = state.selected.length;
    if (p.type === "pass") {
      if (p.blind_allowed) {
        const lab = el("label", "", "Blind pass:");
        const sel = el("select");
        [0, 1, 2, 3].forEach((n) => {
          const o = el("option", "", n ? `${n} unseen` : "none");
          o.value = n;
          if (n === state.blind) o.selected = true;
          sel.appendChild(o);
        });
        sel.addEventListener("change", () => {
          state.blind = +sel.value;
          state.selected = state.selected.slice(0, 3 - state.blind);
          render();
        });
        lab.appendChild(sel);
        a.appendChild(lab);
      }
      const need = 3 - state.blind;
      a.appendChild(button(`Pass ${need ? picked + "/" + need + " " : ""}${p.direction}`, "accent",
        () => send({ type: "pass", tiles: selectedCodes(), blind: state.blind }), picked !== need));
    } else if (p.type === "vote") {
      a.appendChild(button("Yes, second Charleston", "accent", () => send({ type: "vote", continue: true })));
      a.appendChild(button("No, stop", "ghost", () => send({ type: "vote", continue: false })));
    } else if (p.type === "courtesy") {
      a.appendChild(button(`Swap ${picked} tile(s) across`, "accent",
        () => send({ type: "courtesy", tiles: selectedCodes() })));
    } else if (p.type === "discard") {
      a.appendChild(button("Discard", "accent", discard, picked !== 1));
      a.appendChild(button("Mahjong!", "primary", () => send({ type: "mahjong" }), !p.can_mahjong));
      (p.swaps || []).forEach((s) => {
        a.appendChild(button(`Swap ${T.name(s.tile)} for ${nameOf(s.seat) === "You" ? "your" : nameOf(s.seat) + "'s"} joker`,
          "ghost", () => send({ type: "swap", seat: s.seat, index: s.index })));
      });
    } else if (p.type === "call") {
      a.appendChild(tile(p.tile, ""));
      (p.sizes || []).forEach((n) => a.appendChild(button(`Call for ${SIZE_NAMES[n]}`, "accent",
        () => send({ type: "call", size: n }))));
      a.appendChild(button("Mahjong!", "primary", () => send({ type: "mahjong" })));
      a.appendChild(button("Pass", "ghost", () => send({ type: "pass_call" })));
    } else if (p.type === "over") {
      a.appendChild(resultBox());
      a.appendChild(button("Play again", "accent", openNew));
    }
  }

  function resultBox() {
    const v = state.view, r = v.result;
    const box = el("div", "result");
    if (r.wall_game) {
      box.appendChild(el("h3", "", "Wall game — no winner"));
    } else {
      const who = nameOf(r.winner);
      box.appendChild(el("h3", "", `${who} won with ${r.hand} (${r.hand_id})`));
      const how = r.self_drawn ? "Self-drawn" : `On ${nameOf(r.discarder)}'s discard`;
      box.appendChild(el("p", "", `${how}${r.jokerless ? " · jokerless (doubled)" : ""} · card value ${r.points}`));
    }
    const t = el("table");
    r.payments.forEach((p, s) => {
      const tr = el("tr");
      tr.appendChild(el("td", "", nameOf(s)));
      tr.appendChild(el("td", "", (p > 0 ? "+" : "") + p));
      t.appendChild(tr);
    });
    box.appendChild(t);
    return box;
  }

  const selectedCodes = () => state.selected.map((i) => state.view.hand[i]);

  function discard() {
    if (state.selected.length !== 1) return;
    send({ type: "discard", tile: selectedCodes()[0] });
  }

  // ---------------------------------------------------------------- actions
  async function send(action) {
    if (state.busy) return;
    state.busy = true;
    render();
    const res = await api(`/api/game/${state.gameId}/action`, action);
    state.busy = false;
    if (!res.ok) {
      coachNote(res.data.error || "Something went wrong.", "engine");
      if (res.status === 404) openNew();
      render();
      return;
    }
    update(res.data.view);
    if (res.data.feedback) coachNote(res.data.feedback, "engine");
  }

  function update(view) {
    state.lastHand = state.view ? state.view.hand : [];
    state.view = view;
    state.selected = [];
    state.blind = 0;
    render();
  }

  async function startGame(difficulty) {
    const res = await api("/api/game", { difficulty });
    if (!res.ok) { coachNote(res.data.error || "Could not start a game.", "engine"); return; }
    state.gameId = res.data.game_id;
    save(state.gameId);
    state.view = null;
    $("coach-log").replaceChildren();
    coachNote("New game dealt. Ask me anything, or press Hint when you're unsure.", "coach-msg");
    update(res.data.view);
  }

  async function resume() {
    const id = saved();
    if (!id) return false;
    const res = await api(`/api/game/${id}`);
    if (!res.ok) return false;
    state.gameId = id;
    update(res.data.view);
    coachNote("Welcome back — your game is where you left it.", "note");
    return true;
  }

  // ------------------------------------------------------------------ coach
  function coachNote(text, cls = "note", source) {
    const m = el("div", "msg " + cls, text);
    if (source) m.appendChild(el("span", "src", source));
    const log = $("coach-log");
    log.appendChild(m);
    log.scrollTop = log.scrollHeight;
  }

  async function askCoach(kind, text) {
    if (!state.gameId) return;
    if (kind === "question") coachNote(text, "you");
    const wait = el("div", "msg note", "Coach is thinking…");
    $("coach-log").appendChild(wait);
    const res = await api(`/api/game/${state.gameId}/coach`, { kind, text });
    wait.remove();
    if (!res.ok) { coachNote(res.data.error || "The coach is unavailable.", "engine"); return; }
    if (res.data.facts) coachNote(res.data.facts, "engine", "engine facts");
    const src = res.data.source === "engine" ? "engine facts" : "coach";
    coachNote(res.data.text, res.data.source === "engine" ? "engine" : "coach-msg", src);
    if (res.data.note) coachNote(res.data.note, "note");
  }

  // ----------------------------------------------------------------- dialogs
  function openNew() { $("dlg-new").showModal(); }

  async function openCard() {
    const res = await api("/api/card");
    const list = $("card-list");
    list.replaceChildren();
    $("card-title").textContent = res.data.name || "Practice card";
    let cat = null;
    (res.data.hands || []).forEach((h) => {
      if (h.category !== cat) { cat = h.category; list.appendChild(el("div", "card-cat", cat)); }
      const row = el("div", "card-hand");
      row.appendChild(el("span", "id", h.id));
      const mid = el("span");
      mid.appendChild(el("code", "", h.display));
      if (h.note) mid.appendChild(el("span", "note", h.note));
      row.appendChild(mid);
      row.appendChild(el("span", "", `${h.concealed ? "C" : "X"} ${h.points}`));
      list.appendChild(row);
    });
    $("dlg-card").showModal();
  }

  function wire() {
    $("btn-new").addEventListener("click", openNew);
    $("btn-card").addEventListener("click", openCard);
    $("btn-rules").addEventListener("click", () => $("dlg-rules").showModal());
    document.querySelectorAll("[data-close]").forEach((b) =>
      b.addEventListener("click", () => b.closest("dialog").close()));
    $("dlg-new").addEventListener("close", () => {
      if ($("dlg-new").returnValue === "start") {
        const d = document.querySelector('input[name="difficulty"]:checked').value;
        startGame(d);
      }
    });
    $("btn-hint").addEventListener("click", () => askCoach("hint"));
    $("coach-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const input = $("coach-input");
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      askCoach("question", text);
    });
  }

  wire();
  resume().then((ok) => { if (!ok) openNew(); });
})();
