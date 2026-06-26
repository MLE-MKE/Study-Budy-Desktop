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
  const lowerStart = Math.max(padding + 120, height * 0.68);
  const lowerHeight = Math.max(110, height - lowerStart - padding);
  const lanes = Math.max(1, Math.min(3, Math.floor(lowerHeight / 100)));
  const columns = Math.max(1, Math.ceil(count / lanes));
  const gap = (width - padding * 2) / (columns + 1);
  const travel = Math.max(70, Math.min(180, gap * 0.42));
  return Array.from({ length: count }, (_, index) => {
    const lane = index % lanes;
    const column = Math.floor(index / lanes);
    const laneHeight = lowerHeight / lanes;
    return {
      x: padding + gap * (column + 1),
      y: lowerStart + laneHeight * (lane + 0.5),
      travel,
      duration: 7 + (index % 4) * 1.2,
      delay: -(index % 5) * 0.8,
    };
  }).map(point => ({
    ...point,
    x: Math.min(Math.max(point.x, padding + point.travel), width - padding - point.travel),
    y: Math.min(point.y, height - padding),
  }));
}

function avatarElement(viewer, position, appearance) {
  const avatar = document.createElement("div");
  avatar.className = "checkin-avatar";
  avatar.dataset.userId = viewer.user_id;
  updateAvatarElement(avatar, viewer, position, appearance);
  return avatar;
}

function updateAvatarElement(avatar, viewer, position, appearance) {
  avatar.style.left = `${position.x}px`;
  avatar.style.top = `${position.y}px`;
  avatar.style.setProperty("--idle-travel", `${position.travel || 90}px`);
  avatar.style.setProperty("--idle-duration", `${position.duration || 8}s`);
  avatar.style.setProperty("--idle-delay", `${position.delay || 0}s`);
  avatar.style.setProperty("--shape-size", `${viewer.is_streamer ? appearance.streamer_shape_size : appearance.viewer_shape_size}px`);
  avatar.style.setProperty("--shape-color", viewer.color);
  avatar.style.setProperty("--outline-color", appearance.outline_color);
  avatar.style.setProperty("--outline-width", `${appearance.outline_width}px`);
  avatar.style.setProperty("--shape-opacity", appearance.shape_opacity / 100);
  avatar.style.setProperty("--name-size", `${appearance.name_size}px`);
  avatar.style.setProperty("--name-color", appearance.name_color);

  const oldName = avatar.querySelector(".name");
  if (oldName) oldName.remove();
  if (appearance.show_names) {
    const name = document.createElement("div");
    name.className = "name";
    name.append(safeText(viewer.display_name));
    avatar.prepend(name);
  }

  const oldShape = avatar.querySelector(".shape");
  if (oldShape) oldShape.remove();
  const shape = document.createElement("div");
  shape.className = `shape ${viewer.shape}`;
  avatar.append(shape);
}

function render(data) {
  const active = data.active || [];
  const appearance = data.appearance || {};
  const points = slots(active.length, appearance.overlay_padding || 48);
  const activeIds = new Set(active.map(viewer => String(viewer.user_id)));
  known.forEach((avatar, userId) => {
    if (!activeIds.has(userId)) {
      avatar.remove();
      known.delete(userId);
    }
  });
  active.forEach((viewer, index) => {
    const userId = String(viewer.user_id);
    let avatar = known.get(userId);
    if (avatar) {
      updateAvatarElement(avatar, viewer, points[index], appearance);
    } else {
      avatar = avatarElement(viewer, points[index], appearance);
      avatar.classList.add("entering");
      known.set(userId, avatar);
      setTimeout(() => avatar.classList.remove("entering"), 520);
    }
    shapeLayer.append(avatar);
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

function showDance(userId) {
  const avatar = shapeLayer.querySelector(`[data-user-id="${CSS.escape(userId)}"]`);
  if (!avatar) return;
  avatar.classList.add("dancing");
  showBubble(userId, "Dancing!");
  setTimeout(() => avatar.classList.remove("dancing"), 3200);
}

function applyEvents(events) {
  events.forEach(event => {
    if (event.id <= lastEventId) return;
    lastEventId = event.id;
    if (event.type === "checkin_joined") showBubble(event.user_id, event.message || "Ready to study!");
    if (event.type === "checkin_left") showPortal(event.user_id);
    if (event.type === "task_added") showBubble(event.user_id, "Task added!");
    if (event.type === "task_completed") showBubble(event.user_id, "I did it!");
    if (event.type === "checkin_dance") showDance(event.user_id);
  });
}

async function refresh() {
  try {
    const response = await fetch("/api/checkin", { cache: "no-store" });
    render(await response.json());
  } catch {
    shapeLayer.replaceChildren();
    known.clear();
  }
}

refresh();
setInterval(refresh, 1200);
window.addEventListener("resize", refresh);
