const API = "http://localhost:5000/api";

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────
let isConnected = false;
let isLoading = false;

// ─────────────────────────────────────────────
// Sidebar toggle
// ─────────────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  sidebar.style.width = sidebar.style.width === "0px" ? "300px" : "0px";
}

// ─────────────────────────────────────────────
// Tab switching (MySQL / SQLite)
// ─────────────────────────────────────────────
function switchTab(type) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  event.target.classList.add("active");
  document.getElementById("mysql-form").classList.toggle("hidden", type !== "mysql");
  document.getElementById("sqlite-form").classList.toggle("hidden", type !== "sqlite");
}

// ─────────────────────────────────────────────
// Connection
// ─────────────────────────────────────────────
function setStatus(state, text) {
  const el = document.getElementById("connection-status");
  el.className = `status-badge ${state}`;
  el.textContent = text;
}

async function connectMySQL() {
  setStatus("connecting", "⟳ Connecting...");
  try {
    const res = await fetch(`${API}/connect/mysql`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        host: document.getElementById("host").value,
        port: document.getElementById("port").value,
        username: document.getElementById("username").value,
        password: document.getElementById("password").value,
        database: document.getElementById("database").value
      })
    });

    const data = await res.json();
    if (res.ok) {
      isConnected = true;
      setStatus("connected", `● Connected · ${data.database}`);
      clearWelcome();
      appendSystemMsg(`✅ Connected to MySQL database: <strong>${data.database}</strong>`);
      loadHistory();
    } else {
      setStatus("disconnected", "● Disconnected");
      appendSystemMsg(`❌ Connection failed: ${data.error}`, true);
    }
  } catch (e) {
    setStatus("disconnected", "● Disconnected");
    appendSystemMsg(`❌ Could not reach backend: ${e.message}`, true);
  }
}

async function connectSQLite() {
  setStatus("connecting", "⟳ Connecting...");
  try {
    const res = await fetch(`${API}/connect/sqlite`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filepath: document.getElementById("sqlite-path").value })
    });

    const data = await res.json();
    if (res.ok) {
      isConnected = true;
      setStatus("connected", `● Connected · SQLite`);
      clearWelcome();
      appendSystemMsg(`✅ Connected to SQLite: <strong>${data.filepath}</strong>`);
      loadHistory();
    } else {
      setStatus("disconnected", "● Disconnected");
      appendSystemMsg(`❌ Connection failed: ${data.error}`, true);
    }
  } catch (e) {
    setStatus("disconnected", "● Disconnected");
    appendSystemMsg(`❌ Could not reach backend: ${e.message}`, true);
  }
}

// ─────────────────────────────────────────────
// Ask question
// ─────────────────────────────────────────────
function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    askQuestion();
  }
}

async function askQuestion() {
  if (isLoading) return;
  const input = document.getElementById("question-input");
  const question = input.value.trim();
  if (!question) return;

  if (!isConnected) {
    appendSystemMsg("⚠️ Please connect to a database first.", true);
    return;
  }

  input.value = "";
  input.style.height = "auto";
  isLoading = true;
  document.getElementById("send-btn").disabled = true;

  // Show user message
  appendUserMsg(question);

  // Show loading indicator
  const loaderId = appendLoader();

  try {
    const res = await fetch(`${API}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });

    const data = await res.json();
    removeLoader(loaderId);

    if (res.ok && data.success) {
      appendAIResponse(data);
    } else {
      appendAIError(data);
    }

    loadHistory();
  } catch (e) {
    removeLoader(loaderId);
    appendSystemMsg(`❌ Request failed: ${e.message}`, true);
  }

  isLoading = false;
  document.getElementById("send-btn").disabled = false;
  scrollToBottom();
}

// ─────────────────────────────────────────────
// Chat rendering helpers
// ─────────────────────────────────────────────
function clearWelcome() {
  const welcome = document.querySelector(".welcome-msg");
  if (welcome) welcome.remove();
}

function scrollToBottom() {
  const cw = document.getElementById("chat-window");
  cw.scrollTop = cw.scrollHeight;
}

function appendUserMsg(text) {
  const cw = document.getElementById("chat-window");
  const div = document.createElement("div");
  div.className = "msg";
  div.innerHTML = `<div class="msg-user">${escapeHtml(text)}</div>`;
  cw.appendChild(div);
  scrollToBottom();
}

function appendSystemMsg(html, isError = false) {
  const cw = document.getElementById("chat-window");
  const div = document.createElement("div");
  div.className = "msg";
  div.innerHTML = `<div class="${isError ? 'error-msg' : 'explanation'}">${html}</div>`;
  cw.appendChild(div);
  scrollToBottom();
}

function appendLoader() {
  const cw = document.getElementById("chat-window");
  const id = "loader-" + Date.now();
  const div = document.createElement("div");
  div.className = "msg";
  div.id = id;
  div.innerHTML = `
    <div class="msg-ai">
      <div class="msg-ai-inner">
        <div class="loader-msg">
          <div class="spinner"></div>
          Generating SQL query...
        </div>
      </div>
    </div>`;
  cw.appendChild(div);
  scrollToBottom();
  return id;
}

function removeLoader(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function appendAIResponse(data) {
  const cw = document.getElementById("chat-window");
  const div = document.createElement("div");
  div.className = "msg";

  // Build table HTML
  let tableHtml = "";
  if (data.rows && data.rows.length > 0) {
    const headers = data.columns.map(c => `<th>${escapeHtml(String(c))}</th>`).join("");
    const rows = data.rows.map(row =>
      `<tr>${row.map(cell => `<td>${escapeHtml(cell === null ? "NULL" : String(cell))}</td>`).join("")}</tr>`
    ).join("");
    tableHtml = `
      <div class="table-wrapper">
        <table>
          <thead><tr>${headers}</tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  } else {
    tableHtml = `<div class="explanation">Query returned 0 rows.</div>`;
  }

  const correctedBadge = data.corrected
    ? `<span class="badge corrected">⚡ Auto-corrected</span>`
    : "";

  div.innerHTML = `
    <div class="msg-ai">
      <div class="msg-ai-inner">
        <div class="sql-block">
          <div class="sql-label">
            Generated SQL
            <button class="copy-sql-btn" onclick="copySQL(this, \`${escapeAttr(data.sql)}\`)">Copy</button>
          </div>
          <div class="sql-code">${escapeHtml(data.sql)}</div>
        </div>
        <div class="explanation">${escapeHtml(data.explanation)}</div>
        <div class="result-meta">
          <span class="badge success">✓ Success</span>
          ${correctedBadge}
          <span>${data.row_count} row${data.row_count !== 1 ? "s" : ""} returned</span>
        </div>
        ${tableHtml}
      </div>
    </div>`;

  cw.appendChild(div);
  scrollToBottom();
}

function appendAIError(data) {
  const cw = document.getElementById("chat-window");
  const div = document.createElement("div");
  div.className = "msg";

  const sqlSection = data.sql ? `
    <div class="sql-block">
      <div class="sql-label">Generated SQL</div>
      <div class="sql-code">${escapeHtml(data.sql)}</div>
    </div>` : "";

  const blockedNote = data.blocked
    ? `<div class="explanation">🛡️ This query was blocked by the safety guardrail.</div>`
    : data.corrected_attempted
    ? `<div class="explanation">⚡ Auto-correction was attempted but the query still failed.</div>`
    : "";

  div.innerHTML = `
    <div class="msg-ai">
      <div class="msg-ai-inner">
        ${sqlSection}
        ${blockedNote}
        <div class="result-meta"><span class="badge error">✗ Failed</span></div>
        <div class="error-msg">${escapeHtml(data.error || "Unknown error")}</div>
      </div>
    </div>`;

  cw.appendChild(div);
  scrollToBottom();
}

// ─────────────────────────────────────────────
// History
// ─────────────────────────────────────────────
async function loadHistory() {
  try {
    const res = await fetch(`${API}/history`);
    const data = await res.json();
    renderHistory(data);
  } catch (e) {
    console.error("Failed to load history", e);
  }
}

function renderHistory(entries) {
  const list = document.getElementById("history-list");
  if (!entries || entries.length === 0) {
    list.innerHTML = `<p class="empty-msg">No queries yet.</p>`;
    return;
  }

  list.innerHTML = entries.map(e => `
    <div class="history-item ${e.success ? "" : "failed"}" onclick="fillQuestion(${JSON.stringify(escapeHtml(e.question))})">
      <div class="h-question">${escapeHtml(e.question)}</div>
      <div class="h-meta">${e.timestamp} · ${e.success ? e.row_count + " rows" : "failed"}</div>
    </div>
  `).join("");
}

async function clearHistory() {
  await fetch(`${API}/history/clear`, { method: "POST" });
  loadHistory();
}

function fillQuestion(question) {
  document.getElementById("question-input").value = question;
  document.getElementById("question-input").focus();
}

// ─────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(str) {
  return String(str).replace(/`/g, "\\`").replace(/\$/g, "\\$");
}

async function copySQL(btn, sql) {
  await navigator.clipboard.writeText(sql);
  btn.textContent = "Copied!";
  setTimeout(() => btn.textContent = "Copy", 2000);
}

// Auto-resize textarea
document.addEventListener("DOMContentLoaded", () => {
  const ta = document.getElementById("question-input");
  ta.addEventListener("input", () => {
    ta.style.height = "auto";
    ta.style.height = ta.scrollHeight + "px";
  });

  // Check if backend is already up
  fetch(`${API}/health`)
    .then(r => r.json())
    .then(d => {
      if (d.connected) {
        isConnected = true;
        setStatus("connected", "● Connected");
        clearWelcome();
        loadHistory();
      }
    })
    .catch(() => {});
});