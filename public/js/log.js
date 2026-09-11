const labels = { thinking: "Thinking", tool_call: "Tool Call", tool_output: "Tool Output", decision: "Decision" };
let logEl;
export function initLog() { logEl = document.querySelector("#logEntries"); document.querySelector("#clearLog").onclick = clearLog; }
export function appendLog(event) {
  const line = document.createElement("div"); line.className = `log-line ${event.kind || "thinking"}`;
  const body = event.kind === "tool_call" ? `${event.tool || "도구"}(${JSON.stringify(event.args || {})})` : event.summary || event.message || "기록 없음";
  line.innerHTML = `<span class="log-tag">[${labels[event.kind] || "Log"}]</span><span></span>`; line.lastElementChild.textContent = body;
  logEl.append(line); logEl.scrollTop = logEl.scrollHeight;
}
export function clearLog() { if (logEl) logEl.replaceChildren(); }
export function setStatus(stage, message, state = "running") {
  const badge = document.querySelector("#progressBadge"); badge.className = `progress ${state}`; badge.textContent = `${state === "running" ? "◌ " : state === "done" ? "✓ " : state === "error" ? "! " : ""}${message}`;
  document.querySelectorAll(".stepper span").forEach((el) => el.classList.toggle("active", state === "running" && el.dataset.stage === stage));
}
