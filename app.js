const DATA_URL = "data/all_proposal_calls.json";
const MS_PER_DAY = 24 * 60 * 60 * 1000;

const state = {
  today: startOfDay(new Date()),
  visibleMonth: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  calls: [],
  updatedAt: null,
};

const elements = {
  currentTime: document.querySelector("#current-time"),
  monthLabel: document.querySelector("#month-label"),
  monthSummary: document.querySelector("#month-summary"),
  calendarGrid: document.querySelector("#calendar-grid"),
  deadlineTable: document.querySelector("#deadline-table"),
  prevMonth: document.querySelector("#prev-month"),
  nextMonth: document.querySelector("#next-month"),
  todayButton: document.querySelector("#today-button"),
};

elements.prevMonth.addEventListener("click", () => {
  state.visibleMonth = addMonths(state.visibleMonth, -1);
  render();
});

elements.nextMonth.addEventListener("click", () => {
  state.visibleMonth = addMonths(state.visibleMonth, 1);
  render();
});

elements.todayButton.addEventListener("click", () => {
  const now = new Date();
  state.today = startOfDay(now);
  state.visibleMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  render();
});

loadData();
updateClock();
setInterval(updateClock, 1000);

async function loadData() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Unable to load ${DATA_URL}`);
    }
    const payload = await response.json();
    applyPayload(payload);
  } catch (error) {
    if (window.PROPOSAL_DEADLINES) {
      applyPayload(window.PROPOSAL_DEADLINES);
      return;
    }
    elements.calendarGrid.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
    elements.deadlineTable.innerHTML = `
      <tr>
        <td colspan="5">Could not load deadline data. Run the scraper or start a local web server from this folder.</td>
      </tr>
    `;
  }
}

function applyPayload(payload) {
  state.updatedAt = payload.updated_at;
  state.calls = normalizeCalls(payload.proposal_calls || []);
  const nextCall = state.calls.find((call) => call.daysUntil >= 0 && call.deadlineDate);
  if (nextCall) {
    state.visibleMonth = new Date(nextCall.deadlineDate.getFullYear(), nextCall.deadlineDate.getMonth(), 1);
  }
  render();
}

function normalizeCalls(calls) {
  return calls
    .map((call, index) => {
      const deadlineDate = call.deadline_date ? parseLocalDate(call.deadline_date) : null;
      const daysUntil = deadlineDate ? differenceInDays(deadlineDate, state.today) : null;
      return {
        ...call,
        id: `${call.facility}-${call.call_type}-${call.deadline_date || index}`,
        deadlineDate,
        daysUntil,
      };
    })
    .sort((a, b) => {
      const aRank = sortRank(a);
      const bRank = sortRank(b);
      if (aRank !== bRank) return aRank - bRank;
      return (a.deadlineDate?.getTime() || Number.MAX_SAFE_INTEGER) -
        (b.deadlineDate?.getTime() || Number.MAX_SAFE_INTEGER);
    });
}

function sortRank(call) {
  if (!call.deadlineDate) return 3;
  if (call.daysUntil >= 0) return 0;
  return 2;
}

function render() {
  renderHeader();
  renderCalendar();
  renderTable();
}

function renderHeader() {
}

function renderCalendar() {
  const year = state.visibleMonth.getFullYear();
  const month = state.visibleMonth.getMonth();
  const firstOfMonth = new Date(year, month, 1);
  const start = new Date(year, month, 1 - firstOfMonth.getDay());
  const monthCalls = state.calls.filter((call) => {
    return call.deadlineDate &&
      call.deadlineDate.getFullYear() === year &&
      call.deadlineDate.getMonth() === month;
  });

  elements.monthLabel.textContent = firstOfMonth.toLocaleDateString("en", {
    month: "long",
    year: "numeric",
  });
  elements.monthSummary.textContent = `${monthCalls.length} deadline${monthCalls.length === 1 ? "" : "s"} this month`;

  const cells = [];
  for (let offset = 0; offset < 42; offset += 1) {
    const day = addDays(start, offset);
    const dateKey = toDateKey(day);
    const events = state.calls.filter((call) => call.deadline_date === dateKey);
    const classes = [
      "day-cell",
      day.getMonth() !== month ? "outside" : "",
      sameDate(day, state.today) ? "today" : "",
    ].filter(Boolean).join(" ");

    cells.push(`
      <div class="${classes}" role="gridcell" aria-label="${formatDate(day)}">
        <div class="day-number">
          <span>${day.getDate()}</span>
          ${sameDate(day, state.today) ? '<span class="today-pill">Today</span>' : ""}
        </div>
        <div class="deadline-list">
          ${events.map(renderCalendarEvent).join("")}
        </div>
      </div>
    `);
  }

  elements.calendarGrid.innerHTML = cells.join("");
}

function renderCalendarEvent(call) {
  const statusClass = call.status === "open" && call.daysUntil >= 0 ? "open" : "closed";
  const label = `${call.facility}: ${call.title}`;
  return `
    <a class="calendar-event ${statusClass}" href="${call.source_url}" target="_blank" rel="noreferrer" title="${escapeHtml(label)}">
      ${escapeHtml(calendarLabel(call))}
    </a>
  `;
}

function renderTable() {
  if (!state.calls.length) {
    elements.deadlineTable.innerHTML = `<tr><td colspan="5">No deadline data found.</td></tr>`;
    return;
  }

  elements.deadlineTable.innerHTML = state.calls.map((call) => `
    <tr>
      <td>
        <span class="facility">${escapeHtml(call.facility)}</span>
        <span class="call-meta">${escapeHtml(call.call_type)}</span>
      </td>
      <td>
        <a href="${call.source_url}" target="_blank" rel="noreferrer">${escapeHtml(call.title)}</a>
      </td>
      <td>
        <span class="deadline-date">${call.deadlineDate ? formatDate(call.deadlineDate) : "No open deadline"}</span>
        ${call.deadline_text ? `<span class="deadline-text">${escapeHtml(call.deadline_text)}</span>` : ""}
      </td>
      <td>
        <span class="distance ${call.daysUntil !== null && call.daysUntil < 0 ? "past" : ""}">
          ${formatDistance(call)}
        </span>
      </td>
      <td>
        <span class="status-badge ${call.status === "open" && call.daysUntil >= 0 ? "" : "closed"}">
          ${escapeHtml(statusText(call))}
        </span>
      </td>
    </tr>
  `).join("");
}

function updateClock() {
  const now = new Date();
  elements.currentTime.textContent = formatDateTime(now);
}

function statusText(call) {
  if (!call.deadlineDate) return "no open call";
  if (call.daysUntil < 0) return "closed";
  return call.status || "open";
}

function formatDistance(call) {
  if (!call.deadlineDate) return "No DDL";
  if (call.daysUntil === 0) return "Today";
  if (call.daysUntil > 0) return `${call.daysUntil} day${call.daysUntil === 1 ? "" : "s"} left`;
  const daysPast = Math.abs(call.daysUntil);
  return `${daysPast} day${daysPast === 1 ? "" : "s"} ago`;
}

function shortFacility(facility) {
  return facility
    .replace("ANSTO Australian Centre for Neutron Scattering", "ANSTO ACNS")
    .replace("Advanced Photon Source", "APS")
    .replace("ORNL Neutron Sciences", "ORNL")
    .replace("DESY Photon Science", "DESY")
    .replace("ISIS Neutron and Muon Source", "ISIS");
}

function calendarLabel(call) {
  const facility = shortFacility(call.facility);
  if (facility === "SPring-8") {
    if (call.call_type.includes("sixannual")) return "SPring-8 sixannual ddl";
    if (call.call_type.includes("biannual")) return "SPring-8 biannual ddl";
  }
  if (!call.deadlineDate) return `${facility} no open ddl`;
  return `${facility} ddl`;
}

function parseLocalDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function toDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function differenceInDays(target, base) {
  return Math.round((startOfDay(target) - startOfDay(base)) / MS_PER_DAY);
}

function addDays(date, days) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
}

function addMonths(date, months) {
  return new Date(date.getFullYear(), date.getMonth() + months, 1);
}

function sameDate(a, b) {
  return a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();
}

function formatDate(date) {
  return date.toLocaleDateString("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatDateTime(date) {
  return date.toLocaleString("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
