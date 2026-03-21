// API base (defined in auth.js too but kept here for clarity)
// const API = "http://localhost:5000/api";

let isConnected = false;
let isLoading   = false;

// ─────────────────────────────────────────────
// DB tab switching
// ─────────────────────────────────────────────
function switchDbTab(type) {
  document.querySelectorAll(".db-tab-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.type === type)
  );
  document.getElementById("mysql-form").style.display  = type === "mysql"  ? "flex" : "none";
  document.getElementById("sqlite-form").style.display = type === "sqlite" ? "flex" : "none";
}

// ─────────────────────────────────────────────
// Connect MySQL
// ─────────────────────────────────────────────
async function connectMySQL() {
  const btn = document.getElementById("mysql-connect-btn");
  btn.textContent = "Connecting...";
  btn.disabled    = true;
  setConnStatus("connecting", "Connecting...");

  try {
    const res  = await fetch(`${API}/connect/mysql`, {
      method:  "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        host:     document.getElementById("db-host").value,
        port:     document.getElementById("db-port").value,
        username: document.getElementById("db-user").value,
        password: document.getElementById("db-pass").value,
        database: document.getElementById("db-name").value
      })
    });
    const data = await res.json();

    if (res.ok) {
      isConnected = true;
      setConnStatus("online", `${data.database}`);
      pushSystemMsg(`✓ Connected to <strong>${data.database}</strong>`, "success");
      loadHistory();
    } else {
      setConnStatus("offline", "Failed");
      pushSystemMsg(`✗ ${data.error}`, "error");
    }
  } catch (e) {
    setConnStatus("offline", "Error");
    pushSystemMsg(`✗ ${e.message}`, "error");
  }

  btn.textContent = "Connect";
  btn.disabled    = false;
}

// ─────────────────────────────────────────────
// Connect SQLite
// ─────────────────────────────────────────────
async function connectSQLite() {
  const btn = document.getElementById("sqlite-connect-btn");
  btn.textContent = "Connecting...";
  btn.disabled    = true;
  setConnStatus("connecting", "Connecting...");

  try {
    const res  = await fetch(`${API}/connect/sqlite`, {
      method:  "POST",
      headers: authHeaders(),
      body: JSON.stringify({ filepath: document.getElementById("sqlite-path").value })
    });
    const data = await res.json();

    if (res.ok) {
      isConnected = true;
      setConnStatus("online", "SQLite");
      pushSystemMsg(`✓ Connected to SQLite database`, "success");
      loadHistory();
    } else {
      setConnStatus("offline", "Failed");
      pushSystemMsg(`✗ ${data.error}`, "error");
    }
  } catch (e) {
    setConnStatus("offline", "Error");
    pushSystemMsg(`✗ ${e.message}`, "error");
  }

  btn.textContent = "Connect";
  btn.disabled    = false;
}

// ─────────────────────────────────────────────
// Connection status indicator
// ─────────────────────────────────────────────
function setConnStatus(state, text) {
  const dot  = document.getElementById("conn-status-dot");
  const label = document.getElementById("conn-status-text");
  dot.className       = `status-dot ${state}`;
  label.textContent   = text;
}

// ─────────────────────────────────────────────
// Ask question
// ─────────────────────────────────────────────
function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendQuestion();
  }
}

async function sendQuestion() {
  if (isLoading) return;
  const input    = document.getElementById("chat-input");
  const question = input.value.trim();
  if (!question) return;

  if (!isConnected) {
    pushSystemMsg("⚠ Connect to a database first.", "warning");
    return;
  }

  input.value       = "";
  input.style.height = "auto";
  isLoading         = true;
  document.getElementById("send-btn").disabled = true;

  pushUserBubble(question);
  const loaderId = pushLoader();

  try {
    const res  = await fetch(`${API}/ask`, {
      method:  "POST",
      headers: authHeaders(),
      body: JSON.stringify({ question })
    });
    const data = await res.json();

    removeLoader(loaderId);

    if (res.ok && data.success) pushAIResponse(data);
    else                         pushAIError(data);

    loadHistory();
  } catch (e) {
    removeLoader(loaderId);
    pushSystemMsg(`✗ ${e.message}`, "error");
  }

  isLoading = false;
  document.getElementById("send-btn").disabled = false;
  scrollBottom();
}

// ─────────────────────────────────────────────
// Chat rendering
// ─────────────────────────────────────────────
function scrollBottom() {
  const c = document.getElementById("chat-messages");
  c.scrollTop = c.scrollHeight;
}

function removeWelcome() {
  const w = document.getElementById("chat-welcome");
  if (w) w.remove();
}

function pushUserBubble(text) {
  removeWelcome();
  const c   = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "msg-row user-row";
  div.innerHTML = `
    <div class="bubble user-bubble">
      <span>${escHtml(text)}</span>
    </div>`;
  c.appendChild(div);
  scrollBottom();
}

function pushSystemMsg(html, type = "info") {
  removeWelcome();
  const c   = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "msg-row system-row";
  div.innerHTML = `<div class="system-msg ${type}">${html}</div>`;
  c.appendChild(div);
  scrollBottom();
}

function pushLoader() {
  const c   = document.getElementById("chat-messages");
  const id  = "loader-" + Date.now();
  const div = document.createElement("div");
  div.id        = id;
  div.className = "msg-row ai-row";
  div.innerHTML = `
    <div class="ai-avatar">Q</div>
    <div class="bubble ai-bubble loader-bubble">
      <span class="dot-flashing"></span>
    </div>`;
  c.appendChild(div);
  scrollBottom();
  return id;
}

function removeLoader(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function pushAIResponse(data) {
  removeWelcome();
  const c   = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "msg-row ai-row";

  // Table
  let tableHtml = "";
  if (data.rows && data.rows.length > 0) {
    const ths = data.columns.map(col => `<th>${escHtml(String(col))}</th>`).join("");
    const trs = data.rows.map(row =>
      `<tr>${row.map(cell =>
        `<td>${escHtml(cell === null ? "NULL" : String(cell))}</td>`
      ).join("")}</tr>`
    ).join("");
    tableHtml = `
      <div class="result-table-wrap">
        <table class="result-table">
          <thead><tr>${ths}</tr></thead>
          <tbody>${trs}</tbody>
        </table>
      </div>`;
  } else {
    tableHtml = `<p class="zero-rows">No rows returned.</p>`;
  }

  const sqlId = "sql-" + Date.now();

  div.innerHTML = `
    <div class="ai-avatar">Q</div>
    <div class="bubble ai-bubble">

      <div class="sql-card">
        <div class="sql-card-header">
          <span class="sql-tag">SQL</span>
          <button class="copy-btn" onclick="copyText('${sqlId}', this)">Copy</button>
        </div>
        <code id="${sqlId}" class="sql-body">${escHtml(data.sql)}</code>
      </div>

      <p class="explain-text">${escHtml(data.explanation)}</p>

      <div class="result-meta-row">
        <span class="tag tag-success">✓ ${data.row_count} row${data.row_count !== 1 ? "s" : ""}</span>
        ${data.corrected ? `<span class="tag tag-warn">⚡ Auto-corrected</span>` : ""}
      </div>

      ${tableHtml}
    </div>`;

  c.appendChild(div);
  scrollBottom();
}

function pushAIError(data) {
  removeWelcome();
  const c   = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "msg-row ai-row";

  const sqlSection = data.sql ? `
    <div class="sql-card">
      <div class="sql-card-header"><span class="sql-tag">SQL</span></div>
      <code class="sql-body">${escHtml(data.sql)}</code>
    </div>` : "";

  const note = data.blocked
    ? `<p class="explain-text">🛡 Blocked by safety guardrail.</p>`
    : data.corrected_attempted
    ? `<p class="explain-text">⚡ Auto-correction attempted but failed.</p>`
    : "";

  div.innerHTML = `
    <div class="ai-avatar">Q</div>
    <div class="bubble ai-bubble">
      ${sqlSection}
      ${note}
      <div class="result-meta-row">
        <span class="tag tag-error">✗ Failed</span>
      </div>
      <div class="error-box">${escHtml(data.error || "Unknown error")}</div>
    </div>`;

  c.appendChild(div);
  scrollBottom();
}

// ─────────────────────────────────────────────
// History
// ─────────────────────────────────────────────
async function loadHistory() {
  try {
    const res  = await fetch(`${API}/history`, {
      headers: { "Authorization": `Bearer ${getToken()}` }
    });
    const data = await res.json();
    renderHistory(data);
  } catch (e) { /* silent */ }
}

function renderHistory(entries) {
  const list = document.getElementById("history-list");
  if (!entries || entries.length === 0) {
    list.innerHTML = `<p class="empty-hint">No queries yet</p>`;
    return;
  }
  list.innerHTML = entries.map(e => `
    <div class="history-item ${e.success ? "" : "failed"}"
         onclick="fillInput('${escHtml(e.question).replace(/'/g, "\\'")}')">
      <div class="h-q">${escHtml(e.question)}</div>
      <div class="h-meta">${e.timestamp.split(" ")[1]} · ${e.success ? e.row_count + " rows" : "failed"}</div>
    </div>`).join("");
}

async function clearHistory() {
  await fetch(`${API}/history/clear`, { method: "POST", headers: authHeaders() });
  loadHistory();
}

function fillInput(q) {
  const input = document.getElementById("chat-input");
  input.value = q;
  input.focus();
}

// ─────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function copyText(id, btn) {
  const text = document.getElementById(id)?.textContent || "";
  await navigator.clipboard.writeText(text);
  btn.textContent = "Copied!";
  setTimeout(() => btn.textContent = "Copy", 2000);
}

// Auto-resize textarea
document.addEventListener("DOMContentLoaded", () => {
  const ta = document.getElementById("chat-input");
  if (ta) {
    ta.addEventListener("input", () => {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
    });
  }
  initAuth();
});