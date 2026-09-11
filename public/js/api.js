// 백엔드와 통신하는 부분을 한 곳에 모았습니다.
async function request(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(typeof data.detail === "string" ? data.detail : data.detail?.msg || data.message || "요청에 실패했습니다."), { status: response.status, data });
  return data;
}
export const getConfig = () => request("/api/config");
export const createPlan = (body) => request("/api/plans", { method: "POST", body: JSON.stringify(body) });
export const getPlan = (id) => request(`/api/plans/${encodeURIComponent(id)}`);
export const revisePlan = (id, instruction) => request(`/api/plans/${encodeURIComponent(id)}/revise`, { method: "POST", body: JSON.stringify({ instruction }) });
export function openStream(id, handlers) {
  const source = new EventSource(`/api/plans/${encodeURIComponent(id)}/stream`);
  ["status", "log", "result", "error"].forEach((name) => source.addEventListener(name, (event) => {
    try { handlers[name]?.(JSON.parse(event.data)); } catch { handlers.error?.({ message: "서버 응답을 읽지 못했습니다." }); }
    if (name === "result" || name === "error") source.close();
  }));
  source.onerror = () => { if (source.readyState === EventSource.CLOSED) return; handlers.error?.({ message: "연결이 끊겼습니다." }); source.close(); };
  return source;
}
