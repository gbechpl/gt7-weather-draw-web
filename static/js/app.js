const ICON_CODES = [
  "S01","S02","S03","S04","S05","S06","S07","S08","S09","S10","S11","S12","S13","S14","S15","S16","S17","S18",
  "C01","C02","C03","C04","C05","C06",
  "R01","R02","R03","R04","R05","R06","R07","R08"
];

const ICON_H = 129;
const SPIN_SPEED = 18;
const RESULT_DELAY_MS = 5200;

const reelsEl = document.getElementById("reels");
const drawBtnEl = document.getElementById("drawBtn");
const copyBtnEl = document.getElementById("copyBtn");
const statusEl = document.getElementById("status");
const resultTextEl = document.getElementById("resultText");
const slotCountEl = document.getElementById("slotCount");
const profileEl = document.getElementById("profile");
const uniqueEl = document.getElementById("unique");

const spriteUrl = window.GT7_DRAW_CONFIG.spriteUrl;
const drawUrl = window.GT7_DRAW_CONFIG.drawUrl;

let reels = [];
let animationFrameId = null;
let finishingTimeoutId = null;
let currentResultText = "";

function randomCode() {
  return ICON_CODES[Math.floor(Math.random() * ICON_CODES.length)];
}

function codeIndex(code) {
  const index = ICON_CODES.indexOf(code);
  return index < 0 ? 0 : index;
}

function createReel(initialCode) {
  const root = document.createElement("article");
  root.className = "reel";

  const slot = document.createElement("div");
  slot.className = "reel-slot";

  const sprite = document.createElement("div");
  sprite.className = "sprite";
  sprite.style.backgroundImage = `url("${spriteUrl}")`;
  slot.appendChild(sprite);

  const code = document.createElement("div");
  code.className = "reel-code";
  code.textContent = initialCode;

  root.appendChild(slot);
  root.appendChild(code);

  return {
    root,
    sprite,
    codeEl: code,
    currentCode: initialCode,
    targetCode: initialCode,
    offset: -(codeIndex(initialCode) * ICON_H),
    spinning: false,
    direction: Math.random() < 0.5 ? 1 : -1,
  };
}

function updateSpritePosition(reel) {
  reel.sprite.style.backgroundPosition = `0px ${Math.round(reel.offset)}px`;
}

function ensureReels(count) {
  while (reels.length < count) {
    const reel = createReel(randomCode());
    updateSpritePosition(reel);
    reels.push(reel);
    reelsEl.appendChild(reel.root);
  }

  while (reels.length > count) {
    const reel = reels.pop();
    reel.root.remove();
  }
}

function renderStoppedCodes(codes) {
  ensureReels(codes.length);
  codes.forEach((code, index) => {
    const reel = reels[index];
    reel.currentCode = code;
    reel.targetCode = code;
    reel.spinning = false;
    reel.offset = -(codeIndex(code) * ICON_H);
    reel.codeEl.textContent = code;
    updateSpritePosition(reel);
  });
}

function tick() {
  let stillSpinning = false;

  reels.forEach((reel) => {
    if (!reel.spinning) {
      return;
    }

    stillSpinning = true;
    reel.offset -= SPIN_SPEED * reel.direction;
    const minOffset = -(ICON_CODES.length * ICON_H);

    if (reel.offset <= minOffset) {
      reel.offset += ICON_CODES.length * ICON_H;
    }
    if (reel.offset > 0) {
      reel.offset -= ICON_CODES.length * ICON_H;
    }

    updateSpritePosition(reel);
  });

  if (stillSpinning) {
    animationFrameId = window.requestAnimationFrame(tick);
  } else {
    animationFrameId = null;
  }
}

function stopAnimation(codes) {
  reels.forEach((reel, index) => {
    const code = codes[index];
    reel.spinning = false;
    reel.currentCode = code;
    reel.targetCode = code;
    reel.offset = -(codeIndex(code) * ICON_H);
    reel.codeEl.textContent = code;
    updateSpritePosition(reel);
  });
}

function buildResultText(codes, profile, unique) {
  const lines = [
    `Profil: ${profile}`,
    `Unique: ${unique ? "tak" : "nie"}`,
    ""
  ];

  codes.forEach((code, index) => {
    lines.push(`Slot ${index + 1}: ${code}`);
  });

  return lines.join("\n");
}

function startClientAnimation(finalCodes) {
  ensureReels(finalCodes.length);

  reels.forEach((reel) => {
    reel.spinning = true;
    reel.direction = Math.random() < 0.5 ? 1 : -1;
    reel.currentCode = randomCode();
    reel.codeEl.textContent = "SPIN";
  });

  if (animationFrameId === null) {
    animationFrameId = window.requestAnimationFrame(tick);
  }

  window.clearTimeout(finishingTimeoutId);
  finishingTimeoutId = window.setTimeout(() => {
    stopAnimation(finalCodes);
  }, RESULT_DELAY_MS);
}

async function runDraw() {
  drawBtnEl.disabled = true;
  statusEl.textContent = "Losowanie trwa...";

  try {
    const response = await fetch(drawUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        slot_count: Number(slotCountEl.value || 9),
        profile: String(profileEl.value || "mixed"),
        unique: Boolean(uniqueEl.checked)
      })
    });

    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.detail || data.error || "draw_failed");
    }

    startClientAnimation(data.codes);
    currentResultText = buildResultText(data.codes, data.profile, data.unique);
    resultTextEl.textContent = "Animacja trwa...";

    window.setTimeout(() => {
      resultTextEl.textContent = currentResultText;
      statusEl.textContent = "Losowanie zakończone";
    }, RESULT_DELAY_MS);
  } catch (error) {
    statusEl.textContent = "Nie udało się wykonać losowania";
    resultTextEl.textContent = String(error.message || error);
  } finally {
    window.setTimeout(() => {
      drawBtnEl.disabled = false;
    }, 500);
  }
}

async function copyResult() {
  if (!currentResultText) {
    return;
  }

  try {
    await navigator.clipboard.writeText(currentResultText);
    statusEl.textContent = "Wynik skopiowany";
  } catch (_error) {
    statusEl.textContent = "Nie udało się skopiować wyniku";
  }
}

drawBtnEl.addEventListener("click", runDraw);
copyBtnEl.addEventListener("click", copyResult);
renderStoppedCodes(["S01", "C01", "R01", "S05", "R07", "C03", "S12", "S17", "R02"]);
