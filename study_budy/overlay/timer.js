const root = document.getElementById("timer-root");
const display = document.getElementById("timer-display");

let latest = null;
let localServerTimestamp = 0;
let localReceivedAt = Date.now() / 1000;

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

function hexAlpha(percent) {
  const value = Math.round(Math.max(0, Math.min(100, Number(percent))) * 2.55);
  return value.toString(16).padStart(2, "0");
}

function applyAppearance(appearance) {
  const horizontal = appearance.horizontal_align || "center";
  const vertical = appearance.vertical_align || "center";
  root.style.justifyContent = horizontal === "left" ? "flex-start" : horizontal === "right" ? "flex-end" : "center";
  root.style.alignItems = vertical === "top" ? "flex-start" : vertical === "bottom" ? "flex-end" : "center";
  root.style.padding = `${Number(appearance.padding || 0)}px`;

  display.style.fontFamily = `"${appearance.font_family || "Press Start 2P"}", Consolas, monospace`;
  display.style.fontSize = `${Number(appearance.font_size || 96)}px`;
  display.style.fontWeight = appearance.font_weight || "700";
  display.style.color = appearance.text_color || "#ffffff";
  display.style.opacity = String(Math.max(0, Math.min(100, Number(appearance.text_opacity ?? 100))) / 100);
  display.style.letterSpacing = `${Number(appearance.letter_spacing || 0)}px`;
  display.style.padding = `${Number(appearance.padding || 0)}px`;
  display.style.borderRadius = `${Number(appearance.corner_radius || 0)}px`;
  if (appearance.background_enabled) {
    display.style.backgroundColor = `${appearance.background_color || "#000000"}${hexAlpha(appearance.background_opacity ?? 45)}`;
  } else {
    display.style.backgroundColor = "transparent";
  }

  const outlineWidth = Number(appearance.outline_width || 0);
  const outlineMode = appearance.outline_mode || "black";
  const outlineColor = outlineMode === "white" ? "#ffffff" : outlineMode === "black" ? "#000000" : appearance.outline_color || "#000000";
  if (outlineMode === "none" || outlineWidth <= 0) {
    display.style.webkitTextStroke = "0 transparent";
    display.style.textShadow = "none";
  } else {
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
    localServerTimestamp = latest.server_timestamp || 0;
    localReceivedAt = Date.now() / 1000;
    applyAppearance(latest.appearance || {});
    render();
  } catch (error) {
    // Keep the last known state visible if OBS briefly disconnects.
  }
}

refresh();
setInterval(refresh, 5000);
setInterval(render, 250);
