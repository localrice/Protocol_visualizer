const state = { events: [], current: -1, timer: null };
const $ = (selector) => document.querySelector(selector);

function setStatus(message, active = false) {
  $("#status").textContent = message;
  $(".status-dot").classList.toggle("is-active", active);
}
function showError(message = "") { const box = $("#error"); box.textContent = message; box.hidden = !message; }
function messageLabel(item) { const labels = { query: "Query", response: "Response", request: "Request", command: "Command", data: "Message data", connect: "Connection", handshake: "TLS handshake", note: "Encrypted data" }; return labels[item.type] || item.type; }
function displayMessage(item) {
  if (item.protocol === "DNS" && item.type === "query") return `A ${item.fields?.Name || "hostname"}`;
  if (item.protocol === "DNS" && item.type === "response") return "NOERROR";
  return item.message;
}
function visibleFields(item) {
  const allowed = {
    DNS: item.type === "query" ? [] : ["Answer"],
    HTTP: item.type === "request" ? ["Host"] : ["Content-Type", "Content-Length", "Server", "Location"],
    HTTPS: item.type === "request" ? ["Host"] : ["Content-Type", "Content-Length", "Server", "Location"],
    SMTP: item.type === "response" ? ["Capabilities"] : [],
    MANIFEST: ["Representation", "Resource"],
    SEGMENT: ["Representation", "Resource"],
    TCP: ["Destination"],
    TLS: ["Visibility"],
  };
  const keys = allowed[item.protocol] || [];
  return Object.entries(item.fields || {}).filter(([key]) => keys.includes(key)).map(([key, value]) => {
    if (key === "Answer") return [key, String(value).split(",")[0]];
    if (key === "Content-Length") return ["Size", `${value} bytes`];
    return [key, value];
  });
}
function renderExchange() {
  const view = $("#exchange-view"); view.replaceChildren();
  if (!state.events.length) { view.innerHTML = '<p class="empty-state">Run an activity to populate the exchange.</p>'; return; }
  const groups = [];
  state.events.forEach((item, index) => { const key = item.protocol; let group = groups[groups.length - 1]; if (!group || group.key !== key) { group = { key, items: [] }; groups.push(group); } group.items.push({ item, index }); });
  groups.forEach((group) => { const section = document.createElement("section"); section.className = "exchange-group"; const resolver = group.key === "DNS" ? group.items[0].item.fields?.Resolver : ""; const context = resolver ? `<p class="exchange-context">Client → ${escapeHtml(resolver)}</p>` : ""; section.innerHTML = `<h3 class="exchange-group-title">${escapeHtml(group.key)}</h3>${context}`; const list = document.createElement("div"); list.className = "exchange-events"; group.items.forEach(({ item, index }) => { const message = document.createElement("article"); message.className = `exchange-message ${index === state.current ? "is-current" : index < state.current ? "is-complete" : ""}`; const fields = visibleFields(item).map(([key, value]) => `<span class="field"><b>${escapeHtml(key)}:</b> ${escapeHtml(String(value))}</span>`).join(""); message.innerHTML = `<div class="message-side"><span class="message-kind">${escapeHtml(messageLabel(item))}</span><strong>${escapeHtml(displayMessage(item))}</strong>${fields ? `<div class="message-fields">${fields}</div>` : ""}</div>`; list.append(message); }); section.append(list); view.append(section); });
  const current = view.querySelector(".is-current"); if (current) current.scrollIntoView({ block: "nearest", behavior: "smooth" });
}
function showEvent(index) { if (!state.events.length) return; state.current = Math.max(0, Math.min(index, state.events.length - 1)); renderExchange(); scheduleNext(); }
function escapeHtml(value) { const div = document.createElement("div"); div.textContent = value; return div.innerHTML; }
function scheduleNext() { clearTimeout(state.timer); if (state.current >= state.events.length - 1) return; state.timer = setTimeout(() => showEvent(state.current + 1), state.events[state.current]?.delay || 800); }
function loadEvents(data) { clearTimeout(state.timer); state.events = data.events || []; state.current = -1; showEvent(0); }
async function postJson(url, payload) { const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); const data = await response.json(); if (!response.ok || !data.success) throw new Error(data.error || "Request failed"); return data; }

$(".activity-tabs").addEventListener("click", (event) => { const tab = event.target.closest(".tab"); if (!tab) return; document.querySelectorAll(".tab").forEach((button) => { const active = button === tab; button.classList.toggle("is-active", active); button.setAttribute("aria-selected", active); }); document.querySelectorAll(".activity-view").forEach((view) => view.classList.toggle("is-hidden", view.dataset.view !== tab.dataset.activity)); showError(); setStatus("Ready for an activity."); });

$("#browse-form").addEventListener("submit", async (event) => { event.preventDefault(); showError(); setStatus("Resolving hostname and requesting URL...", true); try { const data = await postJson("/api/browse", { url: $("#url").value }); loadEvents(data); setStatus("Browse exchange complete."); } catch (error) { setStatus("Browse failed."); showError(error.message); } });
$("#mail-form").addEventListener("submit", async (event) => { event.preventDefault(); showError(); setStatus("Building simulated SMTP conversation...", true); try { const data = await postJson("/api/mail", { to: $("#to").value, subject: $("#subject").value, body: $("#body").value }); loadEvents(data); setStatus("SMTP simulation ready."); } catch (error) { setStatus("Mail simulation failed."); showError(error.message); } });
$("#stream-play").addEventListener("click", async () => { showError(); setStatus("Preparing adaptive streaming trace...", true); try { const data = await postJson("/api/stream", { quality: $("#quality").value }); loadEvents(data); setStatus("Streaming simulation ready."); } catch (error) { setStatus("Streaming simulation failed."); showError(error.message); } });
