const ICON_CODES = [
  "S01","S02","S03","S04","S05","S06","S07","S08","S09","S10","S11","S12","S13","S14","S15","S16","S17","S18",
  "C01","C02","C03","C04","C05","C06",
  "R01","R02","R03","R04","R05","R06","R07","R08"
];

const ICON_H = 129;
const SPIN_SPEED = 18;
const INITIAL_STOP_DELAY_MS = 1800;
const STOP_INTERVAL_MS = 600;
const STOP_EASE_DURATION_MS = 650;

const reelsEl = document.getElementById("reels");
const drawBtnEl = document.getElementById("drawBtn");
const copyBtnEl = document.getElementById("copyBtn");
const statusEl = document.getElementById("status");
const resultTextEl = document.getElementById("resultText");
const slotCountEl = document.getElementById("slotCount");
const profileEl = document.getElementById("profile");
const themeSelectEl = document.getElementById("themeSelect");
const uniqueEl = document.getElementById("unique");

const spriteUrl = window.GT7_DRAW_CONFIG.spriteUrl;
const drawUrl = window.GT7_DRAW_CONFIG.drawUrl;

let reels = [];
let animationFrameId = null;
let finishingTimeoutIds = [];
let currentResultText = "";
const THEME_STORAGE_KEY = "gt7-draw-theme";
const customSelects = new Map();

function closeCustomSelects(exceptSelect = null) {
  customSelects.forEach((customSelect, select) => {
    if (select === exceptSelect) {
      return;
    }
    customSelect.root.dataset.open = "false";
    customSelect.trigger.setAttribute("aria-expanded", "false");
  });
}

function syncCustomSelect(select) {
  const customSelect = customSelects.get(select);
  if (!customSelect) {
    return;
  }

  const selectedOption = select.options[select.selectedIndex];
  customSelect.triggerLabel.textContent = selectedOption?.text || "";

  customSelect.options.forEach((optionButton) => {
    const isSelected = optionButton.dataset.value === select.value;
    optionButton.dataset.selected = isSelected ? "true" : "false";
    optionButton.setAttribute("aria-selected", isSelected ? "true" : "false");
  });
}

function createCustomSelect(select) {
  const root = document.createElement("div");
  root.className = "custom-select";
  root.dataset.open = "false";

  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "custom-select-trigger";
  trigger.setAttribute("aria-expanded", "false");

  const triggerLabel = document.createElement("span");
  triggerLabel.className = "custom-select-label";

  const triggerArrow = document.createElement("span");
  triggerArrow.className = "custom-select-arrow";
  triggerArrow.setAttribute("aria-hidden", "true");
  triggerArrow.textContent = "▾";

  trigger.appendChild(triggerLabel);
  trigger.appendChild(triggerArrow);

  const menu = document.createElement("div");
  menu.className = "custom-select-menu";

  const optionButtons = Array.from(select.options).map((option) => {
    const optionButton = document.createElement("button");
    optionButton.type = "button";
    optionButton.className = "custom-select-option";
    optionButton.textContent = option.text;
    optionButton.dataset.value = option.value;
    optionButton.setAttribute("role", "option");

    optionButton.addEventListener("click", () => {
      if (select.value !== option.value) {
        select.value = option.value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
      } else {
        syncCustomSelect(select);
      }
      closeCustomSelects();
    });

    menu.appendChild(optionButton);
    return optionButton;
  });

  trigger.addEventListener("click", () => {
    const isOpen = root.dataset.open === "true";
    if (isOpen) {
      closeCustomSelects();
      return;
    }
    closeCustomSelects(select);
    root.dataset.open = "true";
    trigger.setAttribute("aria-expanded", "true");
  });

  root.appendChild(trigger);
  root.appendChild(menu);

  select.classList.add("native-select");
  select.setAttribute("tabindex", "-1");
  select.setAttribute("aria-hidden", "true");
  select.insertAdjacentElement("afterend", root);

  const customSelect = {
    root,
    trigger,
    triggerLabel,
    options: optionButtons,
  };

  customSelects.set(select, customSelect);
  select.addEventListener("change", () => {
    syncCustomSelect(select);
  });
  syncCustomSelect(select);
}

function initCustomSelects() {
  [slotCountEl, profileEl, themeSelectEl].forEach((select) => {
    if (select) {
      createCustomSelect(select);
    }
  });

  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      closeCustomSelects();
      return;
    }

    const clickedInside = Array.from(customSelects.values()).some(({ root }) => root.contains(event.target));
    if (!clickedInside) {
      closeCustomSelects();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeCustomSelects();
    }
  });
}

function applyTheme(themeName) {
  const selectedTheme = themeName === "mono-red" ? "mono-red" : "ocean";
  document.body.dataset.theme = selectedTheme;
  if (themeSelectEl) {
    themeSelectEl.value = selectedTheme;
    syncCustomSelect(themeSelectEl);
  }
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, selectedTheme);
  } catch (_error) {
    // Ignore storage failures and keep the current theme in memory only.
  }
}

function initTheme() {
  let savedTheme = "ocean";
  try {
    savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY) || "ocean";
  } catch (_error) {
    savedTheme = "ocean";
  }
  applyTheme(savedTheme);
}

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

function resetSpriteTransition(reel) {
  reel.sprite.style.transition = "none";
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
    resetSpriteTransition(reel);
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

function stopReel(index, code) {
  const reel = reels[index];
  if (!reel) {
    return;
  }

  reel.spinning = false;
  reel.currentCode = code;
  reel.targetCode = code;
  reel.codeEl.textContent = code;

  const targetOffset = -(codeIndex(code) * ICON_H);
  const loopHeight = ICON_CODES.length * ICON_H;
  let easedOffset = reel.offset;

  if (reel.direction >= 0) {
    while (easedOffset <= targetOffset) {
      easedOffset += loopHeight;
    }
  } else {
    while (easedOffset >= targetOffset) {
      easedOffset -= loopHeight;
    }
  }

  reel.offset = easedOffset;
  resetSpriteTransition(reel);
  updateSpritePosition(reel);

  window.requestAnimationFrame(() => {
    reel.sprite.style.transition = `background-position ${STOP_EASE_DURATION_MS}ms cubic-bezier(0.18, 0.84, 0.32, 1)`;
    reel.offset = targetOffset;
    updateSpritePosition(reel);
    window.setTimeout(() => {
      resetSpriteTransition(reel);
    }, STOP_EASE_DURATION_MS + 30);
  });
}

function clearPendingStops() {
  finishingTimeoutIds.forEach((timeoutId) => {
    window.clearTimeout(timeoutId);
  });
  finishingTimeoutIds = [];
}

function buildResultText(codes, profile, unique) {
  const selectedProfileLabel =
    profileEl ?
      Array.from(profileEl.options).find((option) => option.value === profile)?.text || profile
      : profile;
  const lines = [
    `Profil: ${selectedProfileLabel}`,
    `Unikalne wyniki: ${unique ? "tak" : "nie"}`,
    ""
  ];

  codes.forEach((code, index) => {
    lines.push(`Pole ${index + 1}: ${code}`);
  });

  return lines.join("\n");
}

function startClientAnimation(finalCodes) {
  ensureReels(finalCodes.length);
  clearPendingStops();

  reels.forEach((reel) => {
    reel.spinning = true;
    reel.direction = Math.random() < 0.5 ? 1 : -1;
    reel.currentCode = randomCode();
    reel.codeEl.textContent = "LOS";
    resetSpriteTransition(reel);
  });

  if (animationFrameId === null) {
    animationFrameId = window.requestAnimationFrame(tick);
  }

  finalCodes.forEach((code, index) => {
    const timeoutId = window.setTimeout(() => {
      stopReel(index, code);
    }, INITIAL_STOP_DELAY_MS + (index * STOP_INTERVAL_MS));
    finishingTimeoutIds.push(timeoutId);
  });
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

    const totalAnimationMs =
      INITIAL_STOP_DELAY_MS +
      ((data.codes.length - 1) * STOP_INTERVAL_MS) +
      STOP_EASE_DURATION_MS;

    window.setTimeout(() => {
      resultTextEl.textContent = currentResultText;
      statusEl.textContent = "Losowanie zakończone";
      drawBtnEl.disabled = false;
    }, totalAnimationMs);
  } catch (error) {
    statusEl.textContent = "Nie udało się wykonać losowania";
    resultTextEl.textContent = String(error.message || error);
    drawBtnEl.disabled = false;
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
if (themeSelectEl) {
  themeSelectEl.addEventListener("change", (event) => {
    applyTheme(event.target.value);
  });
}
initCustomSelects();
initTheme();
renderStoppedCodes(["S01", "C01", "R01", "S05", "R07", "C03", "S12", "S17", "R02"]);
