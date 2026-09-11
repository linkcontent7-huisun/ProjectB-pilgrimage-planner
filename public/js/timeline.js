const typeLabels = { holy_site: "성지", mass: "미사", restaurant: "식당", cafe: "카페", lodging: "숙소", transit: "이동", sight: "명소" };
const won = (value) => new Intl.NumberFormat("ko-KR").format(value || 0);
let selectedDay = 0;
export function renderPlan(plan, { onDayChange, onCardHover }) {
  const root = document.querySelector("#timelinePanel"); const days = plan.days || [];
  selectedDay = Math.min(selectedDay, Math.max(days.length - 1, 0)); const day = days[selectedDay]; if (!day) return;
  const cost = plan.estimated_cost_per_person || 0, budget = plan.budget_per_person || 0;
  root.innerHTML = `<div class="plan-head"><h2>${escape(plan.plan_name)}</h2><p>${escape(plan.summary || "맞춤 순례 일정입니다.")}</p><div class="cost">예상 1인 비용 <b>₩${won(cost)}</b> / ₩${won(budget)}</div><div class="budget-bar"><i class="${cost > budget ? "over" : ""}" style="width:${Math.min(100, budget ? cost / budget * 100 : 100)}%"></i></div></div><div class="day-tabs">${days.map((d, i) => `<button data-day="${i}" class="${i === selectedDay ? "selected" : ""}">${d.day}일차 (${d.date})${d.weather ? `<small>${escape(d.weather.summary)} ${d.weather.temp_min}°/${d.weather.temp_max}° ☔${d.weather.precipitation_probability}%</small>` : ""}</button>`).join("")}</div><div class="timeline">${day.places.map((p, i) => `${i ? travel(p.travel_from_previous) : ""}<article class="place-card" data-order="${p.order}"><div class="place-time">${p.start_time}<br>~ ${p.end_time}</div><div class="place-body"><span class="type ${p.type}">${typeLabels[p.type] || p.type}</span><h3>${escape(p.name)}</h3><p>${escape(p.description)}</p>${p.mass_time ? `<p class="meta">⛪ 미사 ${escape(p.mass_time)}</p>` : ""}${p.estimated_cost != null ? `<p class="meta">₩${won(p.estimated_cost)}</p>` : ""}${p.reason ? `<details><summary>선정 근거</summary><p>${escape(p.reason)}</p></details>` : ""}</div></article>`).join("")}</div>`;
  root.querySelectorAll("[data-day]").forEach((button) => button.onclick = () => { selectedDay = Number(button.dataset.day); onDayChange(days[selectedDay], selectedDay); renderPlan(plan, { onDayChange, onCardHover }); });
  root.querySelectorAll(".place-card").forEach((card) => { card.onmouseenter = () => onCardHover?.(Number(card.dataset.order)); card.onmouseleave = () => onCardHover?.(null); });
}
function travel(t) { if (!t) return ""; const icon = { walk: "🚶", car: "🚗", transit: "🚌" }[t.mode] || "↔"; return `<div class="travel">${icon} ${t.duration_min}분 ${t.distance_km}km</div>`; }
function escape(text) { const el = document.createElement("span"); el.textContent = text ?? ""; return el.innerHTML; }
