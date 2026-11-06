// Tile faces drawn as SVG in code (original art). A skin set in config.js
// (window.MJ_CONFIG.tileSkin = {base: "/static/skins/joy/", ext: "png"}) replaces
// the faces with image files named by tile code, e.g. 5B.png, GD.png, J.png.
(function () {
  const SUIT = { B: "Bam", C: "Crak", D: "Dot" };
  const WIND = { N: "North", E: "East", W: "West", S: "South" };
  const DRAGON = { GD: "Green Dragon", RD: "Red Dragon", WD: "Soap" };

  function name(code) {
    if (/^[1-9][BCD]$/.test(code)) return `${code[0]} ${SUIT[code[1]]}`;
    if (WIND[code]) return WIND[code];
    if (DRAGON[code]) return DRAGON[code];
    return code === "F" ? "Flower" : code === "J" ? "Joker" : code;
  }

  // Pip positions on a 40x56 face for dots and bams.
  const PIPS = {
    1: [[20, 30]], 2: [[20, 18], [20, 42]], 3: [[11, 16], [20, 30], [29, 44]],
    4: [[12, 18], [28, 18], [12, 42], [28, 42]],
    5: [[12, 16], [28, 16], [20, 30], [12, 44], [28, 44]],
    6: [[12, 16], [28, 16], [12, 30], [28, 30], [12, 44], [28, 44]],
    7: [[10, 13], [20, 18], [30, 23], [12, 34], [28, 34], [12, 46], [28, 46]],
    8: [[12, 12], [28, 12], [12, 24], [28, 24], [12, 36], [28, 36], [12, 48], [28, 48]],
    9: [[10, 14], [20, 14], [30, 14], [10, 30], [20, 30], [30, 30], [10, 46], [20, 46], [30, 46]],
  };
  const DOT_COLORS = ["#1f5fa8", "#b8322a", "#2f7d4f"];

  function dots(n) {
    const r = n === 1 ? 9 : n <= 4 ? 6 : n <= 6 ? 5.2 : 4.4;
    return PIPS[n].map(([x, y], i) => {
      const c = DOT_COLORS[(i + n) % 3];
      return `<circle cx="${x}" cy="${y + 2}" r="${r}" fill="none" stroke="${c}" stroke-width="2"/>` +
        `<circle cx="${x}" cy="${y + 2}" r="${r * 0.45}" fill="${c}"/>`;
    }).join("");
  }

  function bams(n) {
    if (n === 1) {
      return `<rect x="17" y="12" width="6" height="36" rx="3" fill="#2f7d4f"/>` +
        `<rect x="15" y="21" width="10" height="2.4" fill="#1d5235"/>` +
        `<rect x="15" y="37" width="10" height="2.4" fill="#1d5235"/>` +
        `<circle cx="20" cy="12" r="4" fill="#b8322a"/>`;
    }
    const h = n <= 4 ? 18 : 10;
    return PIPS[n].map(([x, y], i) => {
      const c = i % 4 === 3 ? "#b8322a" : "#2f7d4f";
      return `<rect x="${x - 2.6}" y="${y + 2 - h / 2}" width="5.2" height="${h}" rx="2.4" fill="${c}"/>` +
        `<rect x="${x - 3.4}" y="${y + 1}" width="6.8" height="1.6" fill="#1d5235"/>`;
    }).join("");
  }

  function crak(n) {
    return `<text x="20" y="27" font-size="20" text-anchor="middle" fill="#1f3a5f" font-weight="700" font-family="Georgia, serif">${n}</text>` +
      `<text x="20" y="50" font-size="19" text-anchor="middle" fill="#b8322a" font-family="'Songti SC','SimSun','Noto Serif CJK SC',serif">萬</text>`;
  }

  function face(code) {
    if (/^[1-9][BCD]$/.test(code)) {
      const n = +code[0];
      const body = code[1] === "D" ? dots(n) : code[1] === "B" ? bams(n) : crak(n);
      return corner(code[0], "#1f3a5f") + body;
    }
    if (WIND[code]) {
      const ch = { N: "北", E: "東", W: "西", S: "南" }[code];
      return corner(code, "#1f3a5f") +
        `<text x="20" y="40" font-size="24" text-anchor="middle" fill="#1f3a5f" font-family="'Songti SC','SimSun',serif">${ch}</text>`;
    }
    if (code === "RD") {
      return corner("R", "#b8322a") + `<text x="20" y="41" font-size="25" text-anchor="middle" fill="#b8322a" font-family="'Songti SC','SimSun',serif">中</text>`;
    }
    if (code === "GD") {
      return corner("G", "#2f7d4f") + `<text x="20" y="41" font-size="25" text-anchor="middle" fill="#2f7d4f" font-family="'Songti SC','SimSun',serif">發</text>`;
    }
    if (code === "WD") {
      return corner("0", "#1f5fa8") +
        `<rect x="9" y="16" width="22" height="30" rx="2" fill="none" stroke="#1f5fa8" stroke-width="2.4"/>` +
        `<rect x="13" y="20" width="14" height="22" rx="1" fill="none" stroke="#1f5fa8" stroke-width="1.2"/>`;
    }
    if (code === "F") {
      const petals = [0, 72, 144, 216, 288].map(a =>
        `<ellipse cx="20" cy="22" rx="5" ry="9" fill="#e07a9b" transform="rotate(${a} 20 31)"/>`).join("");
      return corner("F", "#b04a6f") + petals + `<circle cx="20" cy="31" r="4" fill="#e9b949"/>`;
    }
    if (code === "J") {
      return `<text x="20" y="20" font-size="10" text-anchor="middle" fill="#7a5b12" font-weight="800" letter-spacing="0.5" font-family="Georgia, serif">JOKER</text>` +
        `<path d="M20 25 l3.5 7.5 8 .9 -6 5.4 1.8 7.9 -7.3-4.2 -7.3 4.2 1.8-7.9 -6-5.4 8-.9z" fill="var(--brand-accent, #c9a24a)" stroke="#7a5b12" stroke-width="1"/>`;
    }
    return "";
  }

  function corner(label, color) {
    return `<text x="4" y="10" font-size="8" fill="${color}" font-weight="700" font-family="system-ui, sans-serif">${label}</text>`;
  }

  function svg(code) {
    const skin = (window.MJ_CONFIG || {}).tileSkin;
    if (skin) {
      return `<img src="${skin.base}${code}.${skin.ext || "png"}" alt="${name(code)}" draggable="false">`;
    }
    return `<svg viewBox="0 0 40 56" aria-hidden="true">` +
      `<rect x="0.75" y="0.75" width="38.5" height="54.5" rx="5" fill="var(--tile-face, #fbf8f0)" stroke="var(--tile-edge, #cfc6b1)" stroke-width="1.5"/>` +
      face(code) + `</svg>`;
  }

  function back() {
    return `<svg viewBox="0 0 40 56" aria-hidden="true"><rect x="0.75" y="0.75" width="38.5" height="54.5" rx="5" fill="var(--tile-back, #2f5d50)" stroke="var(--tile-back-edge, #1e3d34)" stroke-width="1.5"/>` +
      `<rect x="6" y="6" width="28" height="44" rx="3" fill="none" stroke="var(--brand-primary, #2f5d50)" stroke-width="1" opacity="0.6"/></svg>`;
  }

  window.MJTiles = { svg, back, name };
})();
