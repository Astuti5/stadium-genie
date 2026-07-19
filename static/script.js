// script.js
// Vanilla JS (no build step) so the app stays lightweight and dependency-free.
// All user/AI text is inserted via textContent (never innerHTML) to prevent XSS.

const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sectionInput = document.getElementById("section-input");
const accessibilityCheckbox = document.getElementById("accessibility-checkbox");
const statusLine = document.getElementById("status-line");

const contrastToggle = document.getElementById("contrast-toggle");
const fontsizeToggle = document.getElementById("fontsize-toggle");
const speakToggle = document.getElementById("speak-toggle");

let speakEnabled = false;

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text; // safe: never use innerHTML with untrusted content
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function speak(text) {
  if (!speakEnabled || !("speechSynthesis" in window)) return;
  const utterance = new SpeechSynthesisUtterance(text);
  window.speechSynthesis.speak(utterance);
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;

  addMessage(message, "user");
  messageInput.value = "";
  messageInput.disabled = true;
  statusLine.textContent = "StadiumGenie is thinking…";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        section: sectionInput.value.trim() || null,
        accessibility: accessibilityCheckbox.checked,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      addMessage(data.error || "Something went wrong. Please try again.", "error");
    } else {
      addMessage(data.reply, "assistant");
      speak(data.reply);
    }
  } catch (err) {
    addMessage("Network error — please check your connection and try again.", "error");
  } finally {
    statusLine.textContent = "";
    messageInput.disabled = false;
    messageInput.focus();
  }
});

contrastToggle.addEventListener("click", () => {
  const enabled = document.body.classList.toggle("high-contrast");
  contrastToggle.setAttribute("aria-pressed", String(enabled));
});

fontsizeToggle.addEventListener("click", () => {
  const enabled = fontsizeToggle.getAttribute("aria-pressed") !== "true";
  document.documentElement.style.setProperty("--font-scale", enabled ? "1.25" : "1");
  fontsizeToggle.setAttribute("aria-pressed", String(enabled));
});

speakToggle.addEventListener("click", () => {
  speakEnabled = !speakEnabled;
  speakToggle.setAttribute("aria-pressed", String(speakEnabled));
});
