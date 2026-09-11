import { getConfig, createPlan, getPlan, revisePlan, openStream } from "./api.js";
import { initLog, appendLog, clearLog, setStatus } from "./log.js";
import { loadNaverMaps, createMap, renderDay, highlight } from "./map.js";
import { renderPlan } from "./timeline.js";

const state = { planId: null, plan: null, currentDay: 0, map: null, stream: null, mock: new URLSearchParams(location.search).get("mock") === "1" };
const $ = (selector) => document.querySelector(selector);

// 날짜 기본값과 클릭 동작을 준비합니다.
function setupPage() {
  const date = new Date(); date.setDate(date.getDate() + 7); $("[name=start_date]").value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  $("[name=nights]").oninput = updateDuration; updateDuration(); initLog();
  $("#planForm").onsubmit = submitPlan; $("#reviseButton").onclick = submitRevision;
  $("#jsonButton").onclick = () => { $("#jsonContent").textContent = JSON.stringify(state.plan, null, 2); $("#jsonModal").showModal(); };
  $("#closeJson").onclick = () => $("#jsonModal").close();
  $("#copyJson").onclick = async () => { await navigator.clipboard.writeText(JSON.stringify(state.plan, null, 2)); toast("JSON을 복사했습니다"); };
}
function updateDuration() { const nights = Number($("[name=nights]").value || 0); $("#durationLabel").textContent = `${nights}박 ${nights + 1}일`; }
function setRunning(running) { $("#submitButton").disabled = running; $("#reviseButton").disabled = running || !state.plan; }
function requestBody() { const data = Object.fromEntries(new FormData($("#planForm")).entries()); return { ...data, nights: Number(data.nights), party_size: Number(data.party_size), budget_per_person: Number(data.budget_per_person) }; }
function showError(message) { $("#formError").textContent = message || ""; }
function toast(message) { const el = $("#toast"); el.textContent = message; el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 2600); }

async function bootstrap() {
  setupPage();
  if (state.mock) { await loadMockConfig(); return; }
  try {
    const config = await getConfig(); fillPersonas(config.personas || []); await setupMap(config.naver_map_client_id);
    const saved = localStorage.getItem("pilgrimage-plan-id"); if (saved) await restorePlan(saved);
  } catch (error) { showError(`초기 설정을 불러오지 못했습니다: ${error.message}`); }
}
function fillPersonas(personas) { const select = $("#personaSelect"); if (!personas.length) return; select.replaceChildren(...personas.map((p) => new Option(p.label, p.key))); }
async function setupMap(clientId) { try { await loadNaverMaps(clientId); state.map = createMap($("#map")); } catch { $("#map").innerHTML = '<div class="map-empty">지도 로딩 실패 - Client ID / Web 서비스 URL 확인</div>'; } }
async function restorePlan(id) { try { const saved = await getPlan(id); state.planId = id; if (saved.status === "done" && saved.plan) completePlan(saved.plan, false); else if (saved.status === "error") setStatus(null, saved.error || "이전 일정 생성에 실패했습니다.", "error"); } catch { localStorage.removeItem("pilgrimage-plan-id"); } }

async function submitPlan(event) {
  event.preventDefault(); showError(""); clearLog(); setRunning(true); setStatus("collect", "순례 후보를 모으고 있습니다", "running");
  try { if (state.mock) return playMock(); const reply = await createPlan(requestBody()); state.planId = reply.plan_id; localStorage.setItem("pilgrimage-plan-id", state.planId); connectStream(reply.plan_id); }
  catch (error) { showError(error.message); fail(error.message); }
}
function connectStream(id, revised = false) { state.stream?.close(); state.stream = openStream(id, { status: (e) => setStatus(e.stage, e.message, "running"), log: appendLog, result: (plan) => { completePlan(plan); if (revised) toast("일정을 다시 계산했습니다"); }, error: (e) => fail(e.message) }); }
function fail(message) { setStatus(null, message || "일정 생성 중 오류가 발생했습니다.", "error"); setRunning(false); }
function completePlan(plan, announce = true) {
  state.plan = plan; state.currentDay = 0; setStatus("finalize", "일정이 완성되었습니다", "done"); setRunning(false); $("#revisePanel").classList.remove("hidden"); $("#pdfLink").href = `/api/plans/${encodeURIComponent(state.planId)}/pdf`; drawPlan(); if (announce) toast("순례 일정을 완성했습니다");
}
function drawPlan() { renderPlan(state.plan, { onDayChange(day, index) { state.currentDay = index; drawMap(day.places); }, onCardHover(order) { highlight(order); } }); drawMap(state.plan.days[state.currentDay].places); }
function drawMap(places) { if (state.map) renderDay(state.map, places, { onMarkerHover(order) { document.querySelectorAll(".place-card").forEach((card) => card.classList.toggle("marker-hover", Number(card.dataset.order) === order)); } }); }
async function submitRevision() {
  const instruction = $("#reviseInstruction").value.trim(); if (!instruction || !state.planId) return; clearLog(); setRunning(true); setStatus("compose", "수정 요청을 반영하고 있습니다", "running");
  try { if (state.mock) { await playMock(); toast("일정을 다시 계산했습니다"); return; } const reply = await revisePlan(state.planId, instruction); connectStream(reply.plan_id, true); } catch (error) { fail(error.message); }
}

// 목업은 같은 이벤트 순서로 화면을 시험합니다.
async function loadMockConfig() { fillPersonas([{ key: "mass_centered", label: "미사 참례 중심" }, { key: "walking", label: "도보 순례" }, { key: "frugal", label: "짠내 순례" }]); $("#map").innerHTML = '<div class="map-empty">목업 모드에서는 지도 SDK를 불러오지 않습니다.<br>일정과 로그 흐름을 확인해 주세요.</div>'; }
async function playMock() { state.planId = "mock-plan"; const mock = await fetch("dev/mock-plan.json").then((r) => r.json()); const events = [ ["status", { stage: "collect", message: "대전·당진 성지 후보를 모으는 중" }], ["log", { kind: "thinking", message: "미사 시간과 이동 거리를 함께 고려합니다." }], ["log", { kind: "tool_call", tool: "web_search", args: { query: "당진 솔뫼 성지 미사 시간" } }], ["status", { stage: "research", message: "성지 미사 시간과 날씨를 조사 중" }], ["log", { kind: "tool_output", tool: "web_search", summary: "주일 미사 및 방문 정보를 확인했습니다." }], ["status", { stage: "compose", message: "하루별 순례 동선을 작성 중" }], ["log", { kind: "decision", message: "첫날은 대전 도보 동선, 둘째 날은 당진 성지를 묶었습니다." }], ["status", { stage: "finalize", message: "이동 시간과 예산을 계산 중" }] ];
  for (const [type, data] of events) { await delay(300); type === "status" ? setStatus(data.stage, data.message, "running") : appendLog(data); } await delay(300); completePlan(mock);
}
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
bootstrap();
