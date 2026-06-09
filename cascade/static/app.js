(() => {
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// State
let ws = null;
let currentPath = ".";
let openFiles = {}; // path -> {content, modified}
let activeFile = null;
let chatHistory = [];
let isStreaming = false;

// Init
function init() {
  loadFiles();
  addTab("chat", "💬 Chat", true);
  setupResizers();
  setupShortcuts();
  connectWS();
  setupChatInput();
}

// WebSocket
function connectWS() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${location.host}/ws`);
  ws.onopen = () => setStatus("Connected");
  ws.onclose = () => {
    setStatus("Disconnected - reconnecting...");
    setTimeout(connectWS, 2000);
  };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "token") appendToken(msg.content);
    else if (msg.type === "done") finishStream();
    else if (msg.type === "error") showError(msg.message);
    else if (msg.type === "cleared") chatHistory = [];
  };
}

function wsSend(obj) {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj));
}

// File tree
async function loadFiles(path = ".") {
  currentPath = path;
  try {
    const res = await fetch(`/api/files?path=${encodeURIComponent(path)}`);
    const data = await res.json();
    renderTree(data.entries, data.cwd);
  } catch (e) {
    termPrint(`Error loading files: ${e}\n`);
  }
}

function renderTree(entries, cwd) {
  const tree = $("#file-tree");
  tree.innerHTML = "";
  if (cwd !== ".") {
    const up = document.createElement("div");
    up.className = "file-entry";
    up.innerHTML = `<span class="icon">📁</span><span class="name">..</span>`;
    up.onclick = () => loadFiles(cwd.split("/").slice(0, -1).join("/") || ".");
    tree.appendChild(up);
  }
  entries.forEach((e) => {
    const div = document.createElement("div");
    div.className = "file-entry";
    const icon = e.is_dir ? "📁" : getFileIcon(e.name);
    div.innerHTML = `<span class="icon">${icon}</span><span class="name">${e.name}</span>${!e.is_dir ? `<span class="size">${fmtSize(e.size)}</span>` : ""}`;
    div.onclick = () => e.is_dir ? loadFiles(e.path) : openFile(e.path);
    tree.appendChild(div);
  });
}

function getFileIcon(name) {
  if (name.endsWith(".py")) return "🐍";
  if (name.endsWith(".js")) return "📜";
  if (name.endsWith(".html")) return "🌐";
  if (name.endsWith(".css")) return "🎨";
  if (name.endsWith(".md")) return "📝";
  if (name.endsWith(".json")) return "📋";
  if (name.endsWith(".txt")) return "📄";
  return "📄";
}

function fmtSize(n) {
  if (n < 1024) return n + "B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + "KB";
  return (n / (1024 * 1024)).toFixed(1) + "MB";
}

// Tabs
function addTab(id, title, isChat = false) {
  const tabs = $("#tabs");
  if (tabs.querySelector(`[data-id="${id}"]`)) {
    activateTab(id);
    return;
  }
  const tab = document.createElement("div");
  tab.className = "tab";
  tab.dataset.id = id;
  tab.innerHTML = `<span>${title}</span>${!isChat ? `<span class="close" onclick="closeTab('${id}',event)">×</span>` : ""}`;
  tab.onclick = (e) => { if (!e.target.classList.contains("close")) activateTab(id); };
  tabs.appendChild(tab);
  activateTab(id);
}

function activateTab(id) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.id === id));
  if (id === "chat") {
    $("#chat-panel").classList.remove("hidden");
    $("#code-editor").classList.remove("active");
  } else {
    $("#chat-panel").classList.add("hidden");
    $("#code-editor").classList.add("active");
    activeFile = id;
    $("#editor-textarea").value = openFiles[id]?.content || "";
    $("#editor-path").textContent = id;
    $("#editor-lang").textContent = getLang(id);
  }
}

function closeTab(id, ev) {
  if (ev) ev.stopPropagation();
  const tab = $(`.tab[data-id="${id}"]`);
  if (tab) tab.remove();
  delete openFiles[id];
  if (activeFile === id) {
    activeFile = null;
    const remaining = $$(".tab:not([data-id='chat'])");
    if (remaining.length) activateTab(remaining[0].dataset.id);
    else activateTab("chat");
  }
}

function getLang(path) {
  if (path.endsWith(".py")) return "Python";
  if (path.endsWith(".js")) return "JavaScript";
  if (path.endsWith(".html")) return "HTML";
  if (path.endsWith(".css")) return "CSS";
  if (path.endsWith(".json")) return "JSON";
  return "Text";
}

// Editor
async function openFile(path) {
  try {
    const res = await fetch(`/api/file?path=${encodeURIComponent(path)}`);
    const data = await res.json();
    openFiles[path] = { content: data.content, modified: false };
    addTab(path, path.split("/").pop());
  } catch (e) {
    termPrint(`Error opening file: ${e}\n`);
  }
}

function newFile() {
  const name = prompt("New file name:");
  if (!name) return;
  const path = currentPath === "." ? name : `${currentPath}/${name}`;
  openFiles[path] = { content: "", modified: false };
  addTab(path, name);
}

async function saveFile() {
  if (!activeFile || activeFile === "chat") return;
  const content = $("#editor-textarea").value;
  try {
    await fetch("/api/file", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: activeFile, content }),
    });
    openFiles[activeFile].content = content;
    openFiles[activeFile].modified = false;
    setStatus(`Saved ${activeFile}`);
    loadFiles(currentPath);
  } catch (e) {
    termPrint(`Error saving: ${e}\n`);
  }
}

$("#editor-textarea").addEventListener("input", () => {
  if (activeFile && openFiles[activeFile]) openFiles[activeFile].modified = true;
});

// Chat
function setupChatInput() {
  const input = $("#chat-input");
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  });
}

function sendChat() {
  if (isStreaming) return;
  const input = $("#chat-input");
  const text = input.value.trim();
  if (!text) return;
  const provider = $("#cfg-provider").value;
  const apiKey = $("#cfg-apikey").value;
  if (!apiKey && provider !== "ollama") {
    addMessage("assistant", "**Please enter your API key** in the Config panel on the right before chatting.");
    return;
  }
  input.value = "";
  input.style.height = "auto";
  addMessage("user", text);
  isStreaming = true;
  $("#send-btn").disabled = true;
  startAssistantMessage();
  wsSend({
    action: "chat",
    message: text,
    config: {
      provider: $("#cfg-provider").value,
      model: $("#cfg-model").value,
      api_key: $("#cfg-apikey").value,
      api_base: $("#cfg-apibase").value,
      temperature: parseFloat($("#cfg-temp").value),
    },
  });
}

function addMessage(role, content) {
  chatHistory.push({ role, content });
  const container = $("#chat-messages");
  const div = document.createElement("div");
  div.className = `message ${role}`;
  const icon = role === "user" ? "👤" : "🤖";
  const html = marked.parse(content, { breaks: true });
  div.innerHTML = `<div class="meta">${icon} ${role}</div><div class="content">${html}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  if (role === "assistant") div.querySelectorAll("pre code").forEach((b) => Prism.highlightElement(b));
}

let streamDiv = null;
let streamContent = "";

function startAssistantMessage() {
  const container = $("#chat-messages");
  streamDiv = document.createElement("div");
  streamDiv.className = "message assistant";
  streamDiv.innerHTML = `<div class="meta">🤖 assistant<span class="loading-dot"></span></div><div class="content"></div>`;
  container.appendChild(streamDiv);
  container.scrollTop = container.scrollHeight;
  streamContent = "";
}

function appendToken(text) {
  streamContent += text;
  if (streamDiv) {
    streamDiv.querySelector(".content").innerHTML = marked.parse(streamContent, { breaks: true });
    const container = $("#chat-messages");
    container.scrollTop = container.scrollHeight;
  }
}

function finishStream() {
  isStreaming = false;
  $("#send-btn").disabled = false;
  if (streamDiv) {
    streamDiv.querySelector(".meta").innerHTML = "🤖 assistant";
    streamDiv.querySelectorAll("pre code").forEach((b) => Prism.highlightElement(b));
    wsSend({ action: "append_assistant", content: streamContent });
    chatHistory.push({ role: "assistant", content: streamContent });
  }
  streamDiv = null;
  streamContent = "";
}

function showError(msg) {
  isStreaming = false;
  $("#send-btn").disabled = false;
  addMessage("assistant", `**Error:** ${msg}`);
}

function clearChat() {
  $("#chat-messages").innerHTML = "";
  chatHistory = [];
  wsSend({ action: "clear" });
}

// Terminal
async function runTerminal() {
  const input = $("#terminal-input");
  const cmd = input.value.trim();
  if (!cmd) return;
  input.value = "";
  termPrint(`$ ${cmd}\n`);
  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: cmd }),
    });
    const data = await res.json();
    if (data.stdout) termPrint(data.stdout);
    if (data.stderr) termPrint(data.stderr, true);
    if (data.returncode !== 0) termPrint(`[exit ${data.returncode}]\n`, true);
    else termPrint("\n");
    if (cmd.startsWith("cd ") && data.returncode === 0) {
      const newPath = cmd.slice(3).trim();
      loadFiles(newPath);
    }
  } catch (e) {
    termPrint(`Error: ${e}\n`, true);
  }
}

$("#terminal-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") runTerminal();
});

function termPrint(text, isErr = false) {
  const out = $("#terminal-output");
  const span = document.createElement("span");
  if (isErr) span.style.color = "var(--danger)";
  span.textContent = text;
  out.appendChild(span);
  out.scrollTop = out.scrollHeight;
}

// Resizers
function setupResizers() {
  makeResizer("#sidebar-resizer", "#sidebar", true, 180, 400);
  makeResizer("#right-resizer", "#right", true, 260, 500, true);
  makeRowResizer("#editor-resizer", "#terminal", 80, 400);
}

function makeResizer(sel, targetSel, isLeft, minW, maxW, invert = false) {
  const resizer = $(sel);
  const target = $(targetSel);
  let startX = 0;
  let startW = 0;
  resizer.addEventListener("mousedown", (e) => {
    startX = e.clientX;
    startW = target.offsetWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const move = (ev) => {
      const delta = invert ? startX - ev.clientX : ev.clientX - startX;
      const newW = Math.max(minW, Math.min(maxW, startW + delta));
      target.style.width = newW + "px";
      target.style.flex = "none";
    };
    const up = () => {
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", move);
    document.addEventListener("mouseup", up);
  });
}

function makeRowResizer(sel, targetSel, minH, maxH) {
  const resizer = $(sel);
  const target = $(targetSel);
  let startY = 0;
  let startH = 0;
  resizer.addEventListener("mousedown", (e) => {
    startY = e.clientY;
    startH = target.offsetHeight;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
    const move = (ev) => {
      const delta = startY - ev.clientY;
      const newH = Math.max(minH, Math.min(maxH, startH + delta));
      target.style.height = newH + "px";
      target.style.flex = "none";
    };
    const up = () => {
      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", move);
    document.addEventListener("mouseup", up);
  });
}

// Shortcuts
function setupShortcuts() {
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "s") {
      e.preventDefault();
      saveFile();
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      $("#terminal-output").innerHTML = "";
    }
  });
}

// Utils
function setStatus(text) {
  $("#status-text").textContent = text;
}

function testConnection() {
  setStatus("Testing connection...");
  setTimeout(() => setStatus("Ready (manual test required)"), 500);
}

// Expose globals for onclick handlers
window.newFile = newFile;
window.saveFile = saveFile;
window.sendChat = sendChat;
window.clearChat = clearChat;
window.runTerminal = runTerminal;
window.loadFiles = loadFiles;
window.openFile = openFile;
window.closeTab = closeTab;
window.testConnection = testConnection;

init();
})();
