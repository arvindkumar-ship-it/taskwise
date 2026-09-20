const API = "/api";

// ---------- navigation ----------

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("is-active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("is-active"));
    btn.classList.add("is-active");
    document.getElementById(`view-${btn.dataset.view}`).classList.add("is-active");
    if (btn.dataset.view === "tasks") loadTasks();
    if (btn.dataset.view === "act") loadApprovals();
  });
});

// ---------- health check ----------

async function checkHealth() {
  const dot = document.getElementById("health-dot");
  const label = document.getElementById("health-label");
  try {
    const res = await fetch("/health");
    if (!res.ok) throw new Error();
    dot.classList.add("ok");
    label.textContent = "server connected";
  } catch {
    dot.classList.add("bad");
    label.textContent = "server unreachable";
  }
}
checkHealth();

// ---------- helpers ----------

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

async function postJSON(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

// ---------- ingest ----------

const ingestForm = document.getElementById("ingest-form");
const ingestResult = document.getElementById("ingest-result");

ingestForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("ingest-file");
  const textInput = document.getElementById("ingest-text");
  const submitBtn = ingestForm.querySelector("button");

  if (!fileInput.files.length && !textInput.value.trim()) {
    alert("Add a file or paste some text first.");
    return;
  }

  const formData = new FormData();
  if (fileInput.files.length) formData.append("file", fileInput.files[0]);
  if (textInput.value.trim()) formData.append("text", textInput.value.trim());

  submitBtn.disabled = true;
  submitBtn.textContent = "Ingesting…";
  try {
    const res = await fetch(`${API}/ingest`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Ingest failed");

    ingestResult.hidden = false;
    const taskLines = data.tasks.length
      ? data.tasks.map((t) => `<div class="action-item"><span class="action-label">${escapeHtml(t.title)}</span><span class="status-tag">${t.priority}${t.deadline ? " · " + t.deadline : ""}</span></div>`).join("")
      : `<p class="empty-state">No actionable tasks found in this content.</p>`;

    ingestResult.innerHTML = `
      <h3>${escapeHtml(data.filename)}</h3>
      <p class="status-tag">${data.chunks_indexed} chunks indexed · ${data.tasks_extracted} tasks extracted</p>
      <div style="margin-top:0.8rem">${taskLines}</div>
    `;
    ingestForm.reset();
  } catch (err) {
    alert(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Ingest";
  }
});

// ---------- ask ----------

const askForm = document.getElementById("ask-form");
const askThread = document.getElementById("ask-thread");

askForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("ask-input");
  const question = input.value.trim();
  if (!question) return;

  const submitBtn = askForm.querySelector("button");
  submitBtn.disabled = true;
  input.value = "";

  try {
    const data = await postJSON("/ask", { question });
    const confidencePct = Math.round((data.confidence ?? 0) * 100);
    const sourcesHtml = (data.sources || [])
      .map((s) => `<div class="source-item"><strong>${escapeHtml(s.filename)}</strong> — ${escapeHtml(s.excerpt)}…</div>`)
      .join("");

    const item = document.createElement("div");
    item.className = "qa-item";
    item.innerHTML = `
      <div class="qa-question">${escapeHtml(question)}</div>
      <div class="qa-answer">${escapeHtml(data.answer)}</div>
      <div class="qa-meta">
        <span class="badge ${data.grounded ? "ok" : "warn"}">${data.grounded ? "grounded" : "ungrounded"}</span>
        <span class="confidence-bar"><span class="confidence-fill" style="width:${confidencePct}%"></span></span>
        <span>${confidencePct}% confidence</span>
      </div>
      ${sourcesHtml ? `<div class="sources">${sourcesHtml}</div>` : ""}
    `;
    askThread.prepend(item);
  } catch (err) {
    alert(err.message);
  } finally {
    submitBtn.disabled = false;
  }
});

// ---------- tasks ----------

async function loadTasks() {
  const container = document.getElementById("tasks-list");
  container.innerHTML = `<p class="empty-state">Loading…</p>`;
  try {
    const res = await fetch(`${API}/tasks`);
    const data = await res.json();
    if (!data.tasks.length) {
      container.innerHTML = `<p class="empty-state">No tasks yet — ingest something to get started.</p>`;
      return;
    }
    container.innerHTML = data.tasks
      .map(
        (t) => `
      <div class="task-row">
        <span class="task-priority ${t.priority}"></span>
        <div class="task-body">
          <div class="task-title">${escapeHtml(t.title)}</div>
          <div class="task-meta">
            ${t.deadline ? `due ${escapeHtml(t.deadline)} · ` : ""}${Math.round(t.confidence * 100)}% confidence
            ${t.entities.length ? " · " + t.entities.map(escapeHtml).join(", ") : ""}
          </div>
        </div>
      </div>`
      )
      .join("");
  } catch {
    container.innerHTML = `<p class="empty-state">Couldn't load tasks.</p>`;
  }
}

// ---------- act: plan ----------

const planForm = document.getElementById("plan-form");
const planResult = document.getElementById("plan-result");

planForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("plan-input");
  const goal = input.value.trim();
  if (!goal) return;

  const submitBtn = planForm.querySelector("button");
  submitBtn.disabled = true;
  submitBtn.textContent = "Planning…";

  try {
    const data = await postJSON("/plan", { goal });
    planResult.hidden = false;

    const actionsHtml = data.actions.length
      ? data.actions
          .map((a) => {
            const statusLabel =
              a.status === "pending_approval" ? "awaiting approval" : a.status === "executed" ? "done" : a.status;
            return `<div class="action-item"><span class="action-label"><code>${a.tool}</code> ${escapeHtml(JSON.stringify(a.params))}</span><span class="status-tag">${statusLabel}</span></div>`;
          })
          .join("")
      : `<p class="empty-state">No tool calls proposed — see the reply below.</p>`;

    planResult.innerHTML = `
      <h3>Plan for: ${escapeHtml(goal)}</h3>
      ${data.reply ? `<p>${escapeHtml(data.reply)}</p>` : ""}
      <div style="margin-top:0.8rem">${actionsHtml}</div>
    `;
    input.value = "";
    if (data.actions.some((a) => a.requires_approval)) loadApprovals();
  } catch (err) {
    alert(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Plan";
  }
});

// ---------- act: approvals ----------

async function loadApprovals() {
  const container = document.getElementById("approvals-list");
  container.innerHTML = `<p class="empty-state">Loading…</p>`;
  try {
    const res = await fetch(`${API}/approvals`);
    const data = await res.json();
    const pending = data.approvals.filter((a) => a.status === "pending");

    if (!pending.length) {
      container.innerHTML = `<p class="empty-state">Nothing waiting on you right now.</p>`;
      return;
    }

    container.innerHTML = pending
      .map(
        (a) => `
      <div class="approval-card" data-id="${a.id}">
        <div class="approval-top">
          <div>
            <strong>${escapeHtml(a.action_type)}</strong>
            <div class="approval-params">
              ${Object.entries(a.params)
                .map(([k, v]) => `<div>${escapeHtml(k)}: ${escapeHtml(typeof v === "object" ? JSON.stringify(v) : v)}</div>`)
                .join("")}
            </div>
          </div>
        </div>
        <div class="approval-actions">
          <button class="btn btn-ghost btn-sm" data-action="approve">Approve</button>
          <button class="btn btn-reject btn-sm" data-action="reject">Reject</button>
        </div>
      </div>`
      )
      .join("");

    container.querySelectorAll(".approval-card").forEach((card) => {
      const id = card.dataset.id;
      card.querySelector('[data-action="approve"]').addEventListener("click", () => decideApproval(id, "approve"));
      card.querySelector('[data-action="reject"]').addEventListener("click", () => decideApproval(id, "reject"));
    });
  } catch {
    container.innerHTML = `<p class="empty-state">Couldn't load approvals.</p>`;
  }
}

async function decideApproval(id, decision) {
  try {
    const res = await fetch(`${API}/approvals/${id}/${decision}`, { method: "POST" });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Failed");
    }
    loadApprovals();
  } catch (err) {
    alert(err.message);
  }
}
