const API = "http://localhost:5000/api";

// ─────────────────────────────────────────────
// Token management
// ─────────────────────────────────────────────
function getToken()       { return localStorage.getItem("qm_token"); }
function setToken(t)      { localStorage.setItem("qm_token", t); }
function clearToken()     { localStorage.removeItem("qm_token"); localStorage.removeItem("qm_user"); }
function setUser(u)       { localStorage.setItem("qm_user", JSON.stringify(u)); }
function getUser()        { const u = localStorage.getItem("qm_user"); return u ? JSON.parse(u) : null; }
function isLoggedIn()     { return !!getToken(); }
function authHeaders()    { return { "Content-Type": "application/json", "Authorization": `Bearer ${getToken()}` }; }

// ─────────────────────────────────────────────
// Modal controls
// ─────────────────────────────────────────────
function showAuthModal(tab = "login") {
  document.getElementById("auth-modal").classList.add("active");
  switchAuthTab(tab);
}

function hideAuthModal() {
  document.getElementById("auth-modal").classList.remove("active");
  clearAuthErrors();
}

function switchAuthTab(tab) {
  document.getElementById("login-form").style.display  = tab === "login"    ? "flex" : "none";
  document.getElementById("register-form").style.display = tab === "register" ? "flex" : "none";
  document.querySelectorAll(".auth-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === tab);
  });
}

function clearAuthErrors() {
  document.querySelectorAll(".auth-error").forEach(e => e.textContent = "");
}

// ─────────────────────────────────────────────
// Register
// ─────────────────────────────────────────────
async function register() {
  const name     = document.getElementById("reg-name").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value.trim();
  const errorEl  = document.getElementById("register-error");
  const btn      = document.getElementById("register-btn");

  errorEl.textContent = "";
  if (!name || !email || !password) { errorEl.textContent = "All fields are required."; return; }

  btn.textContent = "Creating...";
  btn.disabled    = true;

  try {
    const res  = await fetch(`${API}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password })
    });
    const data = await res.json();

    if (res.ok) {
      setToken(data.token);
      setUser(data.user);
      hideAuthModal();
      onLoginSuccess(data.user);
    } else {
      errorEl.textContent = data.error || "Registration failed.";
    }
  } catch (e) {
    errorEl.textContent = "Could not connect to server.";
  }

  btn.textContent = "Create Account";
  btn.disabled    = false;
}

// ─────────────────────────────────────────────
// Login
// ─────────────────────────────────────────────
async function login() {
  const email    = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value.trim();
  const errorEl  = document.getElementById("login-error");
  const btn      = document.getElementById("login-submit-btn");

  errorEl.textContent = "";
  if (!email || !password) { errorEl.textContent = "Email and password are required."; return; }

  btn.textContent = "Signing in...";
  btn.disabled    = true;

  try {
    const res  = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (res.ok) {
      setToken(data.token);
      setUser(data.user);
      hideAuthModal();
      onLoginSuccess(data.user);
    } else {
      errorEl.textContent = data.error || "Login failed.";
    }
  } catch (e) {
    errorEl.textContent = "Could not connect to server.";
  }

  btn.textContent = "Sign In";
  btn.disabled    = false;
}

// ─────────────────────────────────────────────
// Google OAuth
// ─────────────────────────────────────────────
function loginWithGoogle() {
  window.location.href = `${API}/auth/google`;
}

function handleOAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const token  = params.get("token");
  const error  = params.get("error");

  if (error) {
    showAuthModal("login");
    document.getElementById("login-error").textContent = `Google login failed: ${error}`;
    return;
  }

  if (token) {
    setToken(token);
    fetch(`${API}/auth/me`, { headers: { "Authorization": `Bearer ${token}` } })
      .then(r => r.json())
      .then(user => {
        setUser(user);
        onLoginSuccess(user);
        window.history.replaceState({}, document.title, window.location.pathname);
      });
  }
}

// ─────────────────────────────────────────────
// Logout
// ─────────────────────────────────────────────
function logout() {
  clearToken();
  document.getElementById("app-container").classList.remove("visible");
  document.getElementById("landing-screen").classList.add("visible");
  resetAppState();
}

// ─────────────────────────────────────────────
// On login success
// ─────────────────────────────────────────────
function onLoginSuccess(user) {
  // Update avatar & name
  const initials = user.name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
  document.getElementById("user-avatar").textContent  = initials;
  document.getElementById("user-name-display").textContent = user.name.split(" ")[0];

  // Show app, hide landing
  document.getElementById("landing-screen").classList.remove("visible");
  document.getElementById("app-container").classList.add("visible");
  document.getElementById("auth-modal").classList.remove("active");
}

function resetAppState() {
  document.getElementById("chat-messages").innerHTML = "";
  document.getElementById("conn-status-dot").className = "status-dot offline";
  document.getElementById("conn-status-text").textContent = "Not connected";
  document.getElementById("history-list").innerHTML = `<p class="empty-hint">No queries yet</p>`;
}

// ─────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────
async function initAuth() {
  handleOAuthCallback();

  if (!isLoggedIn()) {
    document.getElementById("landing-screen").classList.add("visible");
    return;
  }

  try {
    const res = await fetch(`${API}/auth/me`, {
      headers: { "Authorization": `Bearer ${getToken()}` }
    });

    if (res.ok) {
      const user = await res.json();
      setUser(user);
      onLoginSuccess(user);
    } else {
      clearToken();
      document.getElementById("landing-screen").classList.add("visible");
    }
  } catch (e) {
    document.getElementById("landing-screen").classList.add("visible");
  }
}