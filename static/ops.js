// ops.js — StadiumGenie Ops dashboard logic.
// Same safety rule as script.js: all dynamic text uses textContent, never innerHTML.

const gateInput = document.getElementById("ops-gate-input");
const crowdList = document.getElementById("crowd-density-list");
const incidentForm = document.getElementById("incident-form");
const incidentStatus = document.getElementById("incident-status");
const incidentListEl = document.getElementById("incident-list");
const opsChatForm = document.getElementById("ops-chat-form");
const opsMessageInput = document.getElementById("ops-message-input");
const opsChatWindow = document.getElementById("ops-chat-window");
const opsStatusLine = document.getElementById("ops-status-line");

const CROWD_DATA = { A: 0.35, B: 0.78, C: 0.91, D: 0.22 }; // mirrors stadium_data.py mock feed

function renderCrowdDensity() {
  crowdList.textContent = "";
  const list = document.createElement("ul");
  list.style.listStyle = "none";
  list.style.padding = "0";
  Object.entries(CROWD_DATA).forEach(([gate, density]) => {
    const li = document.createElement("li");
    const pct = Math.round(density * 100);
    li.textContent = `Gate ${gate}: ${pct}% capacity${density >= 0.85 ? " — ⚠️ ALERT" : ""}`;
    list.appendChild(li);
  });
  crowdList.appendChild(list);
}

function addOpsMessage(text, role) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  opsChatWindow.appendChild(div);
  opsChatWindow.scrollTop = opsChatWindow.scrollHeight;
}

async function loadIncidents() {
  const gate = gateInput.value.trim();
  const url = gate ? `/api/ops/incidents?gate=${encodeURIComponent(gate)}&unresolved_only=true`
                    : "/api/ops/incidents?unresolved_only=true";
  try {
    const res = await fetch(url);
    const data = await res.json();
    incidentListEl.textContent = "";
    if (!data.incidents || data.incidents.length === 0) {
      incidentListEl.textContent = "No active incidents.";
      return;
    }
    const list = document.createElement("ul");
    list.style.listStyle = "none";
    list.style.padding = "0";
    data.incidents.forEach((inc) => {
      const li = document.createElement("li");
      li.textContent = `[${inc.severity.toUpperCase()}] Gate ${inc.gate} — ${inc.category}: ${inc.description}`;
      list.appendChild(li);
    });
    incidentListEl.appendChild(list);
  } catch {
    incidentListEl.textContent = "Could not load incidents.";
  }
}

incidentForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  incidentStatus.textContent = "Logging…";
  try {
    const res = await fetch("/api/ops/incidents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        gate: document.getElementById("incident-gate").value.trim(),
        category: document.getElementById("incident-category").value,
        severity: document.getElementById("incident-severity").value,
        description: document.getElementById("incident-description").value.trim(),
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      incidentStatus.textContent = data.error || "Failed to log incident.";
    } else {
      incidentStatus.textContent = "Incident logged.";
      incidentForm.reset();
      loadIncidents();
    }
  } catch {
    incidentStatus.textContent = "Network error.";
  }
});

opsChatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = opsMessageInput.value.trim();
  if (!message) return;
  addOpsMessage(message, "user");
  opsMessageInput.value = "";
  opsMessageInput.disabled = true;
  opsStatusLine.textContent = "Thinking…";

  try {
    const res = await fetch("/api/ops/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, gate: gateInput.value.trim() || null }),
    });
    const data = await res.json();
    if (!res.ok) {
      addOpsMessage(data.error || "Something went wrong.", "error");
    } else {
      addOpsMessage(data.reply, "assistant");
    }
  } catch {
    addOpsMessage("Network error — please retry.", "error");
  } finally {
    opsStatusLine.textContent = "";
    opsMessageInput.disabled = false;
    opsMessageInput.focus();
  }
});

gateInput.addEventListener("input", loadIncidents);

renderCrowdDensity();
loadIncidents();
