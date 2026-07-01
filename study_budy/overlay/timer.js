const root = document.getElementById("timer-root");
const display = document.getElementById("timer-display");

let latest = null;
let localReceivedAt = Date.now() / 1000;
let lastAppearanceEventId = null;

async function sendHeartbeat() {
  try {
    await fetch("/api/overlay-clients/timer/heartbeat", { method: "POST", cache: "no-store" });
  } catch {
    // OBS may briefly pause Browser Source networking while scenes change.
  }
}

function formatDuration(seconds) {
  const safe = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const secs = safe % 60;
  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }
  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function validColor(value, fallback) {
  return /^#[0-9A-Fa-f]{6}$/.test(value || "") ? value : fallback;
}

function clampNumber(value, min, max, fallback) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.max(min, Math.min(max, number));
}

function hexAlpha(percent) {
  const value = Math.round(Math.max(0, Math.min(100, Number(percent))) * 2.55);
  return value.toString(16).padStart(2, "0");
}

function applyAppearance(appearance) {
  if (!appearance || typeof appearance !== "object") return;
  const horizontal = appearance.horizontal_align || "center";
  const vertical = appearance.vertical_align || "center";
  root.style.justifyContent = horizontal === "left" ? "flex-start" : horizontal === "right" ? "flex-end" : "center";
  root.style.alignItems = vertical === "top" ? "flex-start" : vertical === "bottom" ? "flex-end" : "center";
  root.style.padding = `${clampNumber(appearance.padding, 0, 200, 8)}px`;

  const font = String(appearance.font_family || "Segoe UI").replace(/["\\]/g, "");
  const textColor = validColor(appearance.text_color, "#FFFFFF");
  const opacity = clampNumber(appearance.text_opacity, 0, 100, 100) / 100;
  const padding = clampNumber(appearance.padding, 0, 200, 8);
  const radius = clampNumber(appearance.corner_radius, 0, 100, 8);
  root.style.setProperty("--timer-font-family", `"${font}"`);
  root.style.setProperty("--timer-font-size", `${clampNumber(appearance.font_size, 16, 300, 96)}px`);
  root.style.setProperty("--timer-font-weight", `${clampNumber(appearance.font_weight, 100, 900, 700)}`);
  root.style.setProperty("--timer-text-color", textColor);
  root.style.setProperty("--timer-text-opacity", `${opacity}`);
  root.style.setProperty("--timer-letter-spacing", `${clampNumber(appearance.letter_spacing, -10, 30, 0)}px`);
  root.style.setProperty("--timer-padding", `${padding}px`);
  root.style.setProperty("--timer-corner-radius", `${radius}px`);
  if (appearance.background_enabled) {
    root.style.setProperty("--timer-background-color", `${validColor(appearance.background_color, "#000000")}${hexAlpha(appearance.background_opacity ?? 0)}`);
  } else {
    root.style.setProperty("--timer-background-color", "transparent");
  }

  const outlineWidth = clampNumber(appearance.outline_width, 0, 12, 0);
  const outlineMode = appearance.outline_mode || "black";
  const outlineColor = outlineMode === "white" ? "#FFFFFF" : outlineMode === "black" ? "#000000" : validColor(appearance.outline_color, "#000000");
  if (outlineMode === "none" || outlineWidth <= 0) {
    root.style.setProperty("--timer-outline-width", "0px");
    root.style.setProperty("--timer-outline-color", "transparent");
    display.style.webkitTextStroke = "0 transparent";
    display.style.textShadow = "none";
  } else {
    root.style.setProperty("--timer-outline-width", `${outlineWidth}px`);
    root.style.setProperty("--timer-outline-color", outlineColor);
    display.style.webkitTextStroke = `${outlineWidth}px ${outlineColor}`;
    display.style.textShadow = `0 0 ${outlineWidth + 1}px ${outlineColor}`;
  }
}

function currentRemaining() {
  if (!latest) return 0;
  if (latest.state !== "running") return latest.remaining_seconds || 0;
  const elapsed = Date.now() / 1000 - localReceivedAt;
  return Math.max(0, (latest.remaining_seconds || 0) - elapsed);
}

function render() {
  const appearance = latest?.appearance || {};
  const remaining = currentRemaining();
  const inactive = remaining <= 0 && latest?.state !== "complete" && appearance.hide_when_inactive;
  display.textContent = inactive ? "" : formatDuration(remaining);
  display.className = "";
  if (latest?.state === "complete") {
    display.classList.add("complete");
    const animation = appearance.completion_animation || "pulse";
    if (animation !== "none") display.classList.add(animation.replace("fade out", "fade"));
  }
}

async function refresh() {
  try {
    const response = await fetch("/api/timer", { cache: "no-store" });
    latest = await response.json();
    localReceivedAt = Date.now() / 1000;
    const event = latest.appearance_event || {};
    if (event.event_id !== lastAppearanceEventId || latest.appearance) {
      applyAppearance(event.appearance || latest.appearance || {});
      lastAppearanceEventId = event.event_id;
    }
    render();
  } catch (error) {
    // Keep the last known state visible if OBS briefly disconnects.
  }
}

refresh();
sendHeartbeat();
setInterval(refresh, 1000);
setInterval(render, 250);
setInterval(sendHeartbeat, 2000);
