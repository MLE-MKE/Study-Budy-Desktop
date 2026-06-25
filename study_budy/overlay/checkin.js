const root = document.getElementById("checkin-root");
const shapeLayer = document.getElementById("shape-layer");
const portalLayer = document.getElementById("portal-layer");
let known = new Map();
let lastEventId = 0;

function safeText(value) {
  return document.createTextNode(String(value || ""));
}

function slots(count, padding) {
  const width = window.innerWidth || 1280;
  const height = window.innerHeight || 720;
  const cols = Math.max(3, Math.floor((width - padding * 2) / 160));
  return Array.from({ length: count }, (_, index) => {
    if (index === 0) return { x: padding + 90, y: padding + 110 };
    const viewerIndex = index - 1;
    return {
      x: padding + 110 + (viewerIndex % cols) * 150,
      y: padding + 250 + Math.floor(viewerIndex / cols) * 140,
    };
  }).map(point => ({ x: Math.min(point.x, width - padding), y: Math.min(point.y, height - padding) }));
}

function avatarElement(viewer, position, appearance) {
  const avatar = document.createElement("div");
  avatar.className = "checkin-avatar";
  avatar.dataset.userId = viewer.user_id;
  avatar.style.left = `${position.x}px`;
  avatar.style.top = `${position.y}px`;
  avatar.style.setProperty("--shape-size", `${viewer.is_streamer ? appearance.streamer_shape_size : appearance.viewer_shape_size}px`);
  avatar.style.setProperty("--shape-color", viewer.color);
  avatar.style.setProperty("--outline-color", appearance.outline_color);
  avatar.style.setProperty("--outline-width", `${appearance.outline_width}px`);
  avatar.style.setProperty("--shape-opacity", appearance.shape_opacity / 100);
  avatar.style.setProperty("--name-size", `${appearance.name_size}px`);
  avatar.style.setProperty("--name-color", appearance.name_color);

  if (appearance.show_names) {
    const name = document.createElement("div");
    name.className = "name";
    name.append(safeText(viewer.display_name));
    avatar.append(name);
  }

  const shape = document.createElement("div");
  shape.className = `shape ${viewer.shape}`;
  avatar.append(shape);
  return avatar;
}

function render(data) {
  const active = data.active || [];
  const appearance = data.appearance || {};
  const points = slots(active.length, appearance.overlay_padding || 48);
  shapeLayer.replaceChildren();
  active.forEach((viewer, index) => {
    shapeLayer.append(avatarElement(viewer, points[index], appearance));
  });
  applyEvents(data.events || []);
}

function showBubble(userId, message) {
  const avatar = shapeLayer.querySelector(`[data-user-id="${CSS.escape(userId)}"]`);
  if (!avatar) return;
  const old = avatar.querySelector(".bubble");
  if (old) old.remove();
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.append(safeText(message));
  avatar.append(bubble);
  setTimeout(() => bubble.remove(), 4200);
}

function showPortal(userId) {
  const avatar = shapeLayer.querySelector(`[data-user-id="${CSS.escape(userId)}"]`);
  if (!avatar) return;
  const rect = avatar.getBoundingClientRect();
  const portal = document.createElement("div");
  portal.className = "portal";
  portal.style.left = `${rect.left + rect.width / 2 + 40}px`;
  portal.style.top = `${rect.top + rect.height / 2}px`;
  portalLayer.append(portal);
  avatar.classList.add("leaving");
  setTimeout(() => portal.remove(), 950);
}

function applyEvents(events) {
  events.forEach(event => {
    if (event.id <= lastEventId) return;
    lastEventId = event.id;
    if (event.type === "checkin_joined") showBubble(event.user_id, event.message || "Ready to study!");
    if (event.type === "checkin_left") showPortal(event.user_id);
    if (event.type === "task_added") showBubble(event.user_id, "Task added!");
    if (event.type === "task_completed") showBubble(event.user_id, "I did it!");
  });
}

async function refresh() {
  try {
    const response = await fetch("/api/checkin", { cache: "no-store" });
    render(await response.json());
  } catch {
    shapeLayer.replaceChildren();
  }
}

refresh();
setInterval(refresh, 1200);
window.addEventListener("resize", refresh);
