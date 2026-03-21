let isConnected   = false;
let isLoading     = false;
let isDarkMode    = true;
let chartInstances = {};

// ─────────────────────────────────────────────
// DB Tab switching
// ─────────────────────────────────────────────
function switchDbTab(type) {
  document.querySelectorAll(".db-tab-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.type === type)
  );
  document.getElementById("mysql-form").style.display   = type === "mysql"  ? "flex" : "none";
  document.getElementById("sqlite-form").style.display  = type === "sqlite" ? "flex" : "none";
  document.getElementById("upload-form").style.display  = type === "upload" ? "flex" : "none";
}

// ─────────────────────────────────────────────
// Connect MySQL
// ─────────────────────────────────────────────
async function connectMySQL() {
  const btn = document.getElementById("mysql-connect-btn");
  btn.textContent = "Connecting..."; btn.disabled = true;
  setConnStatus("connecting", "Connecting...");
  try {
    const res  = await fetch(`${API}/connect/mysql`, {
      method: "POST", headers: authHeaders(),
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
      setConnStatus("online", data.database);
      pushSystemMsg(`✓ Connected to <strong>${data.database}</strong> · ${data.tables_indexed} tables indexed`, "success");
      loadHistory(); loadSchemaExplorer(); loadSuggestions();
    } else { setConnStatus("offline", "Failed"); pushSystemMsg(`✗ ${data.error}`, "error"); }
  } catch (e) { setConnStatus("offline", "Error"); pushSystemMsg(`✗ ${e.message}`, "error"); }
  btn.textContent = "Connect"; btn.disabled = false;
}

// ─────────────────────────────────────────────
// Connect SQLite
// ─────────────────────────────────────────────
async function connectSQLite() {
  const btn = document.getElementById("sqlite-connect-btn");
  btn.textContent = "Connecting..."; btn.disabled = true;
  setConnStatus("connecting", "Connecting...");
  try {
    const res  = await fetch(`${API}/connect/sqlite`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({ filepath: document.getElementById("sqlite-path").value })
    });
    const data = await res.json();
    if (res.ok) {
      isConnected = true;
      setConnStatus("online", "SQLite");
      pushSystemMsg(`✓ Connected to SQLite · ${data.tables_indexed} tables indexed`, "success");
      loadHistory(); loadSchemaExplorer(); loadSuggestions();
    } else { setConnStatus("offline", "Failed"); pushSystemMsg(`✗ ${data.error}`, "error"); }
  } catch (e) { setConnStatus("offline", "Error"); pushSystemMsg(`✗ ${e.message}`, "error"); }
  btn.textContent = "Connect"; btn.disabled = false;
}

// ─────────────────────────────────────────────
// Upload file
// ─────────────────────────────────────────────
async function uploadFile() {
  const fileInput = document.getElementById("file-upload");
  const btn       = document.getElementById("upload-connect-btn");
  if (!fileInput.files.length) { pushSystemMsg("⚠ Please select a file first.", "warning"); return; }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  btn.textContent = "Uploading..."; btn.disabled = true;
  setConnStatus("connecting", "Uploading...");

  try {
    const res  = await fetch(`${API}/connect/upload`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${getToken()}` },
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      isConnected = true;
      setConnStatus("online", data.original_name || "Uploaded DB");
      pushSystemMsg(`✓ Uploaded <strong>${data.original_name}</strong> · ${data.tables_indexed} tables indexed`, "success");
      loadHistory(); loadSchemaExplorer(); loadSuggestions();
    } else { setConnStatus("offline", "Failed"); pushSystemMsg(`✗ ${data.error}`, "error"); }
  } catch (e) { setConnStatus("offline", "Error"); pushSystemMsg(`✗ ${e.message}`, "error"); }
  btn.textContent = "Upload & Connect"; btn.disabled = false;
}

// ─────────────────────────────────────────────
// Connection status
// ─────────────────────────────────────────────
function setConnStatus(state, text) {
  document.getElementById("conn-status-dot").className    = `status-dot ${state}`;
  document.getElementById("conn-status-text").textContent = text;
}

// ─────────────────────────────────────────────
// Schema Explorer
// ─────────────────────────────────────────────
async function loadSchemaExplorer() {
  try {
    const res   = await fetch(`${API}/schema/explorer`, { headers: authHeaders() });
    const data  = await res.json();
    if (!data.tables) return;
    const panel = document.getElementById("schema-explorer");
    panel.innerHTML = data.tables.map(t => `
      <div class="explorer-table">
        <div class="explorer-table-header" onclick="toggleTable('${t.name}', this)">
          <span class="table-icon">⊞</span>
          <span class="table-name">${escHtml(t.name)}</span>
          <span class="table-col-count">${t.columns.length} cols</span>
          <span class="expand-arrow">›</span>
        </div>
        <div class="explorer-table-body hidden" id="table-${t.name}">
          ${t.columns.map(c => `
            <div class="explorer-col">
              <span class="col-name">${escHtml(c.name)}</span>
              <span class="col-type">${escHtml(c.type)}</span>
            </div>`).join("")}
          <button class="sample-btn" onclick="loadSampleRows('${t.name}')">Show sample rows</button>
          <div id="sample-${t.name}" class="sample-rows"></div>
        </div>
      </div>`).join("");
  } catch (e) { /* silent */ }
}

function toggleTable(name, header) {
  const body  = document.getElementById(`table-${name}`);
  const arrow = header.querySelector(".expand-arrow");
  body.classList.toggle("hidden");
  arrow.textContent = body.classList.contains("hidden") ? "›" : "⌄";
}

async function loadSampleRows(tableName) {
  const container = document.getElementById(`sample-${tableName}`);
  container.innerHTML = `<p class="empty-hint">Loading...</p>`;
  try {
    const res  = await fetch(`${API}/schema/sample/${tableName}`, { headers: authHeaders() });
    const data = await res.json();
    if (data.columns && data.rows) {
      const ths = data.columns.map(c => `<th>${escHtml(c)}</th>`).join("");
      const trs = data.rows.map(r =>
        `<tr>${r.map(v => `<td>${escHtml(v === null ? "NULL" : String(v))}</td>`).join("")}</tr>`
      ).join("");
      container.innerHTML = `
        <div class="sample-table-wrap">
          <table class="sample-table">
            <thead><tr>${ths}</tr></thead>
            <tbody>${trs}</tbody>
          </table>
        </div>`;
    }
  } catch (e) { container.innerHTML = `<p class="empty-hint">Failed to load</p>`; }
}

// ─────────────────────────────────────────────
// Query suggestions
// ─────────────────────────────────────────────
async function loadSuggestions() {
  if (!isConnected) return;
  try {
    const res  = await fetch(`${API}/suggestions`, { headers: authHeaders() });
    const data = await res.json();
    if (data.suggestions) {
      const chips = document.getElementById("suggestion-chips");
      if (chips) {
        chips.innerHTML = data.suggestions.map(q =>
          `<button class="chip" onclick="fillAndSend('${escHtml(q).replace(/'/g, "\\'")}')">${escHtml(q)}</button>`
        ).join("");
      }
    }
  } catch (e) { /* silent */ }
}

function fillAndSend(q) {
  document.getElementById("chat-input").value = q;
  sendQuestion();
}

// ─────────────────────────────────────────────
// Ask question
// ─────────────────────────────────────────────
function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendQuestion(); }
}

async function sendQuestion() {
  if (isLoading) return;
  const input    = document.getElementById("chat-input");
  const question = input.value.trim();
  if (!question) return;
  if (!isConnected) { pushSystemMsg("⚠ Connect to a database first.", "warning"); return; }

  input.value = ""; input.style.height = "auto";
  isLoading   = true;
  document.getElementById("send-btn").disabled = true;

  removeWelcome();
  pushUserBubble(question);
  const loaderId = pushLoader();

  try {
    const res  = await fetch(`${API}/ask`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({ question })
    });
    const data = await res.json();
    removeLoader(loaderId);
    if (res.ok && data.success) pushAIResponse(data);
    else                         pushAIError(data);
    loadHistory();
  } catch (e) { removeLoader(loaderId); pushSystemMsg(`✗ ${e.message}`, "error"); }

  isLoading = false;
  document.getElementById("send-btn").disabled = false;
  scrollBottom();
}

// ─────────────────────────────────────────────
// Chat rendering
// ─────────────────────────────────────────────
function scrollBottom() { const c = document.getElementById("chat-messages"); c.scrollTop = c.scrollHeight; }
function removeWelcome() { const w = document.getElementById("chat-welcome"); if (w) w.remove(); }

function pushUserBubble(text) {
  const c = document.getElementById("chat-messages");
  const d = document.createElement("div");
  d.className = "msg-row user-row";
  d.innerHTML = `<div class="bubble user-bubble"><span>${escHtml(text)}</span></div>`;
  c.appendChild(d); scrollBottom();
}

function pushSystemMsg(html, type = "info") {
  removeWelcome();
  const c = document.getElementById("chat-messages");
  const d = document.createElement("div");
  d.className = "msg-row system-row";
  d.innerHTML = `<div class="system-msg ${type}">${html}</div>`;
  c.appendChild(d); scrollBottom();
}

function pushLoader() {
  const c  = document.getElementById("chat-messages");
  const id = "loader-" + Date.now();
  const d  = document.createElement("div");
  d.id = id; d.className = "msg-row ai-row";
  d.innerHTML = `
    <div class="ai-avatar">Q</div>
    <div class="bubble ai-bubble loader-bubble">
      <span class="dot-flashing"></span>
    </div>`;
  c.appendChild(d); scrollBottom();
  return id;
}

function removeLoader(id) { const el = document.getElementById(id); if (el) el.remove(); }

function pushAIResponse(data) {
  const c      = document.getElementById("chat-messages");
  const d      = document.createElement("div");
  d.className  = "msg-row ai-row";
  const sqlId  = "sql-"   + Date.now();
  const chartId = "chart-" + Date.now();

  // Table
  let tableHtml = "";
  if (data.rows && data.rows.length > 0) {
    const ths = data.columns.map(c => `<th>${escHtml(String(c))}</th>`).join("");
    const trs = data.rows.map(r =>
      `<tr>${r.map(v => `<td>${escHtml(v === null ? "NULL" : String(v))}</td>`).join("")}</tr>`
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

  // Chart toggle button
  const hasChart  = data.chart_data && Object.keys(data.chart_data).length > 0;
  const chartToggle = hasChart ? `
    <button class="chart-toggle-btn" onclick="toggleChart('${chartId}', this)">📊 Show Chart</button>
    <div id="${chartId}" class="chart-container hidden">
      <canvas id="canvas-${chartId}"></canvas>
    </div>` : "";

  // Save + Share buttons
  const actionBtns = `
    <div class="response-actions">
      <button class="action-btn" onclick="openSaveModal('${escHtml(data.question).replace(/'/g, "\\'")}', '${escHtml(data.sql).replace(/'/g, "\\'")}')">💾 Save</button>
      <button class="action-btn" onclick="shareQuery('${escHtml(data.question).replace(/'/g, "\\'")}', '${escHtml(data.sql).replace(/'/g, "\\'")}', ${JSON.stringify(data.columns)}, ${JSON.stringify(data.rows)}, ${data.row_count})">🔗 Share</button>
      <button class="action-btn thumb-up"   onclick="submitFeedback(1, '${escHtml(data.question).replace(/'/g, "\\'")}', '${escHtml(data.sql).replace(/'/g, "\\'")}', this)">👍</button>
      <button class="action-btn thumb-down" onclick="submitFeedback(0, '${escHtml(data.question).replace(/'/g, "\\'")}', '${escHtml(data.sql).replace(/'/g, "\\'")}', this)">👎</button>
    </div>`;

  d.innerHTML = `
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
      ${chartToggle}
      ${actionBtns}
    </div>`;

  c.appendChild(d);

  // Render chart if available
  if (hasChart) {
    setTimeout(() => renderChart(chartId, data.chart_data), 100);
  }

  scrollBottom();
}

function pushAIError(data) {
  const c = document.getElementById("chat-messages");
  const d = document.createElement("div");
  d.className = "msg-row ai-row";

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

  d.innerHTML = `
    <div class="ai-avatar">Q</div>
    <div class="bubble ai-bubble">
      ${sqlSection}${note}
      <div class="result-meta-row"><span class="tag tag-error">✗ Failed</span></div>
      <div class="error-box">${escHtml(data.error || "Unknown error")}</div>
    </div>`;
  c.appendChild(d); scrollBottom();
}

// ─────────────────────────────────────────────
// Chart rendering
// ─────────────────────────────────────────────
function toggleChart(chartId, btn) {
  const container = document.getElementById(chartId);
  container.classList.toggle("hidden");
  btn.textContent = container.classList.contains("hidden") ? "📊 Show Chart" : "📊 Hide Chart";
}

function renderChart(chartId, chartData) {
  const canvas = document.getElementById(`canvas-${chartId}`);
  if (!canvas || !window.Chart) return;
  if (chartInstances[chartId]) {
    chartInstances[chartId].destroy();
  }
  Chart.defaults.color = "#7a8aaa";
  Chart.defaults.borderColor = "rgba(255,255,255,0.06)";
  chartInstances[chartId] = new Chart(canvas, chartData);
}

// ─────────────────────────────────────────────
// History
// ─────────────────────────────────────────────
async function loadHistory() {
  try {
    const res  = await fetch(`${API}/history`, { headers: { "Authorization": `Bearer ${getToken()}` } });
    const data = await res.json();
    renderHistory(data);
  } catch (e) { /* silent */ }
}

function renderHistory(entries) {
  const list = document.getElementById("history-list");
  if (!entries || entries.length === 0) { list.innerHTML = `<p class="empty-hint">No queries yet</p>`; return; }
  list.innerHTML = entries.map(e => `
    <div class="history-item ${e.success ? "" : "failed"}"
         onclick="fillInput('${escHtml(e.question).replace(/'/g, "\\'")}')">
      <div class="h-q">${escHtml(e.question)}</div>
      <div class="h-meta">${e.timestamp ? e.timestamp.split(" ")[1] : ""} · ${e.success ? e.row_count + " rows" : "failed"}</div>
    </div>`).join("");
}

async function clearHistory() {
  await fetch(`${API}/history/clear`, { method: "POST", headers: authHeaders() });
  loadHistory();
}

function fillInput(q) {
  document.getElementById("chat-input").value = q;
  document.getElementById("chat-input").focus();
}

// ─────────────────────────────────────────────
// Save query modal
// ─────────────────────────────────────────────
let _pendingSave = {};

function openSaveModal(question, sql) {
  _pendingSave = { question, sql };
  document.getElementById("save-modal").classList.add("active");
  document.getElementById("save-name").value       = question.slice(0, 40);
  document.getElementById("save-collection").value = "General";
}

function closeSaveModal() {
  document.getElementById("save-modal").classList.remove("active");
}

async function confirmSave() {
  const name       = document.getElementById("save-name").value.trim();
  const collection = document.getElementById("save-collection").value.trim() || "General";
  if (!name) return;

  try {
    const res = await fetch(`${API}/saved/save`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({ name, collection, question: _pendingSave.question, sql: _pendingSave.sql })
    });
    if (res.ok) {
      closeSaveModal();
      pushSystemMsg(`💾 Saved as <strong>${name}</strong>`, "success");
      loadSavedQueries();
    }
  } catch (e) { /* silent */ }
}

async function loadSavedQueries() {
  try {
    const res  = await fetch(`${API}/saved/list`, { headers: authHeaders() });
    const data = await res.json();
    renderSavedQueries(data);
  } catch (e) { /* silent */ }
}

function renderSavedQueries(entries) {
  const list = document.getElementById("saved-queries-list");
  if (!list) return;
  if (!entries || entries.length === 0) { list.innerHTML = `<p class="empty-hint">No saved queries</p>`; return; }

  const grouped = {};
  entries.forEach(e => {
    if (!grouped[e.collection]) grouped[e.collection] = [];
    grouped[e.collection].push(e);
  });

  list.innerHTML = Object.entries(grouped).map(([col, items]) => `
    <div class="saved-collection">
      <div class="collection-label">${escHtml(col)}</div>
      ${items.map(item => `
        <div class="saved-item">
          <div class="saved-item-name" onclick="fillInput('${escHtml(item.question).replace(/'/g, "\\'")}')">
            ${escHtml(item.name)}
          </div>
          <button class="del-saved-btn" onclick="deleteSaved(${item.id})">✕</button>
        </div>`).join("")}
    </div>`).join("");
}

async function deleteSaved(id) {
  await fetch(`${API}/saved/${id}`, { method: "DELETE", headers: authHeaders() });
  loadSavedQueries();
}

// ─────────────────────────────────────────────
// Share query
// ─────────────────────────────────────────────
async function shareQuery(question, sql, columns, rows, row_count) {
  try {
    const res  = await fetch(`${API}/share/create`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({ question, sql, columns, rows, row_count })
    });
    const data = await res.json();
    if (data.share_url) {
      await navigator.clipboard.writeText(data.share_url);
      pushSystemMsg(`🔗 Share link copied to clipboard!`, "success");
    }
  } catch (e) { pushSystemMsg("Failed to create share link", "error"); }
}

// ─────────────────────────────────────────────
// Feedback
// ─────────────────────────────────────────────
async function submitFeedback(rating, question, sql, btn) {
  try {
    await fetch(`${API}/feedback`, {
      method: "POST", headers: authHeaders(),
      body: JSON.stringify({ rating, question, sql })
    });
    btn.style.opacity = "0.4";
    btn.disabled      = true;
    loadFeedbackStats();
  } catch (e) { /* silent */ }
}

async function loadFeedbackStats() {
  try {
    const res  = await fetch(`${API}/feedback/stats`, { headers: authHeaders() });
    const data = await res.json();
    const el   = document.getElementById("feedback-stats");
    if (el && data.total > 0) {
      el.textContent = `${data.positive_rate}% positive · ${data.total} rated`;
    }
  } catch (e) { /* silent */ }
}

// ─────────────────────────────────────────────
// Dark / Light mode
// ─────────────────────────────────────────────
function toggleTheme() {
  isDarkMode = !isDarkMode;
  document.body.classList.toggle("light-mode", !isDarkMode);
  const btn = document.getElementById("theme-toggle");
  btn.textContent = isDarkMode ? "☀️" : "🌙";
  localStorage.setItem("qm_theme", isDarkMode ? "dark" : "light");
}

function initTheme() {
  const saved = localStorage.getItem("qm_theme");
  if (saved === "light") {
    isDarkMode = false;
    document.body.classList.add("light-mode");
    const btn = document.getElementById("theme-toggle");
    if (btn) btn.textContent = "🌙";
  }
}

// ─────────────────────────────────────────────
// Sidebar panel switching
// ─────────────────────────────────────────────
function switchSidebarPanel(panel) {
  document.querySelectorAll(".sidebar-panel").forEach(p =>
    p.classList.toggle("hidden", p.id !== `panel-${panel}`)
  );
  document.querySelectorAll(".sidebar-nav-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.panel === panel)
  );
}

// ─────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

async function copyText(id, btn) {
  const text = document.getElementById(id)?.textContent || "";
  await navigator.clipboard.writeText(text);
  btn.textContent = "Copied!";
  setTimeout(() => btn.textContent = "Copy", 2000);
}

// ─────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initTheme();

  const ta = document.getElementById("chat-input");
  if (ta) {
    ta.addEventListener("input", () => {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
    });
  }

  initAuth();
});