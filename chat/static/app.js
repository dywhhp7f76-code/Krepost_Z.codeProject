(() => {
  const agentListEl = document.getElementById("agentList");
  const searchEl = document.getElementById("search");
  const hubStatus = document.getElementById("hubStatus");
  const emptyState = document.getElementById("emptyState");
  const dialogActive = document.getElementById("dialogActive");
  const messagesEl = document.getElementById("messages");
  const peerAvatar = document.getElementById("peerAvatar");
  const peerName = document.getElementById("peerName");
  const peerStatus = document.getElementById("peerStatus");
  const form = document.getElementById("form");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("send");
  const modal = document.getElementById("agentModal");
  const agentForm = document.getElementById("agentForm");
  const modalTitle = document.getElementById("modalTitle");
  const btnNew = document.getElementById("btnNew");
  const btnEdit = document.getElementById("btnEdit");
  const btnCancel = document.getElementById("btnCancel");
  const btnDelete = document.getElementById("btnDelete");
  const fId = document.getElementById("fId");
  const fName = document.getElementById("fName");
  const fUrl = document.getElementById("fUrl");
  const fSubtitle = document.getElementById("fSubtitle");
  const fMode = document.getElementById("fMode");

  const HISTORY_KEY = "krepost.hub.history.v1";
  const ACTIVE_KEY = "krepost.hub.active";
  const MODE_KEY = "krepost.hub.modes";

  /** @type {Array<any>} */
  let agents = [];
  /** @type {any|null} */
  let active = null;
  /** @type {Record<string, boolean|null>} */
  let onlineMap = {};
  /** @type {Record<string, string>} */
  let modes = JSON.parse(localStorage.getItem(MODE_KEY) || "{}");
  /** @type {Record<string, Array<any>>} */
  let history = JSON.parse(localStorage.getItem(HISTORY_KEY) || "{}");

  function saveHistory() {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  }
  function saveModes() {
    localStorage.setItem(MODE_KEY, JSON.stringify(modes));
  }
  function sessionFor(agentId) {
    const key = `krepost.hub.session.${agentId}`;
    let s = localStorage.getItem(key);
    if (!s) {
      s = crypto.randomUUID();
      localStorage.setItem(key, s);
    }
    return s;
  }
  function initials(name) {
    const parts = String(name || "?").trim().split(/\s+/).slice(0, 2);
    return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "?";
  }
  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function formatText(text) {
    const parts = String(text ?? "").split(/```/);
    return parts
      .map((part, i) => {
        if (i % 2 === 1) {
          const nl = part.indexOf("\n");
          const code = nl >= 0 ? part.slice(nl + 1) : part;
          return `<span class="code">${escapeHtml(code.replace(/\n$/, ""))}</span>`;
        }
        return escapeHtml(part);
      })
      .join("");
  }
  function lastPreview(agentId) {
    const list = history[agentId] || [];
    if (!list.length) return "Нет сообщений";
    const last = list[list.length - 1];
    const prefix = last.role === "user" ? "Вы: " : "";
    return (prefix + (last.text || "")).replace(/\s+/g, " ").slice(0, 64);
  }
  function lastTime(agentId) {
    const list = history[agentId] || [];
    if (!list.length) return "";
    const t = list[list.length - 1].ts;
    if (!t) return "";
    const d = new Date(t);
    return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  }

  async function loadAgents() {
    const res = await fetch("/api/agents", { cache: "no-store" });
    const data = await res.json();
    agents = data.agents || [];
    hubStatus.textContent = `${agents.length} агент(ов)`;
    renderList();
    const saved = localStorage.getItem(ACTIVE_KEY);
    const pick = agents.find((a) => a.id === saved) || agents[0] || null;
    if (pick) selectAgent(pick.id);
    else showEmpty();
    pingAll();
  }

  function renderList() {
    const q = (searchEl.value || "").trim().toLowerCase();
    agentListEl.innerHTML = "";
    const filtered = agents.filter((a) => {
      if (!q) return true;
      return (
        a.name.toLowerCase().includes(q) ||
        (a.subtitle || "").toLowerCase().includes(q) ||
        (a.url || "").toLowerCase().includes(q)
      );
    });
    for (const a of filtered) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "agent-item" + (active?.id === a.id ? " is-active" : "");
      btn.setAttribute("role", "listitem");
      const on = onlineMap[a.id];
      btn.innerHTML = `
        <div class="avatar" style="background:${escapeHtml(a.color || "#5288c1")}">${escapeHtml(initials(a.name))}</div>
        <div class="agent-meta">
          <div class="agent-top">
            <div class="agent-name">${escapeHtml(a.name)}</div>
            <div class="agent-time">${escapeHtml(lastTime(a.id))}</div>
          </div>
          <div class="agent-sub"><span class="dot-online ${on ? "" : "off"}"></span>${escapeHtml(lastPreview(a.id))}</div>
        </div>`;
      btn.addEventListener("click", () => selectAgent(a.id));
      agentListEl.appendChild(btn);
    }
  }

  function showEmpty() {
    active = null;
    emptyState.classList.remove("hidden");
    dialogActive.classList.add("hidden");
  }

  function selectAgent(id) {
    const a = agents.find((x) => x.id === id);
    if (!a) return;
    active = a;
    localStorage.setItem(ACTIVE_KEY, id);
    emptyState.classList.add("hidden");
    dialogActive.classList.remove("hidden");
    peerAvatar.textContent = initials(a.name);
    peerAvatar.style.background = a.color || "#5288c1";
    peerName.textContent = a.name;
    const on = onlineMap[a.id];
    peerStatus.textContent =
      on === true ? "в сети" : on === false ? "нет связи · " + a.url : "проверка…";
    const mode = modes[a.id] || a.defaultMode || "agent";
    document.querySelectorAll(".mode-btn").forEach((b) => {
      b.classList.toggle("is-active", b.dataset.mode === mode);
    });
    renderMessages();
    renderList();
    input.focus();
    pingOne(a.id);
  }

  function renderMessages() {
    messagesEl.innerHTML = "";
    const list = history[active.id] || [];
    for (const m of list) appendBubble(m, false);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function appendBubble(m, scroll = true) {
    const wrap = document.createElement("article");
    wrap.className = `msg ${m.role}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (m.pending) {
      bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
    } else {
      bubble.innerHTML = formatText(m.text);
      const foot = document.createElement("div");
      foot.className = "msg-foot";
      if (m.verdict) {
        const b = document.createElement("span");
        b.className = `badge ${String(m.verdict).toLowerCase()}`;
        b.textContent = m.verdict;
        foot.appendChild(b);
      }
      const t = document.createElement("span");
      t.textContent = m.meta || "";
      foot.appendChild(t);
      bubble.appendChild(foot);
    }
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    if (scroll) messagesEl.scrollTop = messagesEl.scrollHeight;
    return { wrap, bubble };
  }

  async function pingOne(id) {
    try {
      const res = await fetch(`/api/agents/${id}/health`, { cache: "no-store" });
      onlineMap[id] = res.ok;
    } catch {
      onlineMap[id] = false;
    }
    if (active?.id === id) {
      peerStatus.textContent = onlineMap[id]
        ? "в сети"
        : "нет связи · " + active.url;
    }
    renderList();
  }

  async function pingAll() {
    await Promise.all(agents.map((a) => pingOne(a.id)));
  }

  searchEl.addEventListener("input", renderList);

  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!active) return;
      modes[active.id] = btn.dataset.mode;
      saveModes();
      document.querySelectorAll(".mode-btn").forEach((b) => {
        b.classList.toggle("is-active", b.dataset.mode === btn.dataset.mode);
      });
    });
  });

  function openModal(agent) {
    if (agent) {
      modalTitle.textContent = "Агент";
      fId.value = agent.id;
      fName.value = agent.name || "";
      fUrl.value = agent.url || "";
      fSubtitle.value = agent.subtitle || "";
      fMode.value = agent.defaultMode || "query";
      btnDelete.classList.remove("hidden");
    } else {
      modalTitle.textContent = "Новый агент";
      fId.value = "";
      fName.value = "";
      fUrl.value = "http://";
      fSubtitle.value = "";
      fMode.value = "agent";
      btnDelete.classList.add("hidden");
    }
    modal.showModal();
    fName.focus();
  }

  btnNew.addEventListener("click", () => openModal(null));
  btnEdit.addEventListener("click", () => active && openModal(active));
  btnCancel.addEventListener("click", () => modal.close());

  btnDelete.addEventListener("click", async () => {
    const id = fId.value;
    if (!id) return;
    if (!confirm("Удалить агента из списка?")) return;
    await fetch(`/api/agents/${id}`, { method: "DELETE" });
    delete history[id];
    saveHistory();
    modal.close();
    await loadAgents();
  });

  agentForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      name: fName.value.trim(),
      url: fUrl.value.trim(),
      subtitle: fSubtitle.value.trim(),
      defaultMode: fMode.value,
    };
    if (fId.value) {
      await fetch(`/api/agents/${fId.value}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      const res = await fetch("/api/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.agent) localStorage.setItem(ACTIVE_KEY, data.agent.id);
    }
    modal.close();
    await loadAgents();
  });

  function autosize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  }
  input.addEventListener("input", autosize);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!active || sendBtn.disabled) return;
    const text = input.value.trim();
    if (!text) return;

    history[active.id] = history[active.id] || [];
    const userMsg = { role: "user", text, ts: Date.now() };
    history[active.id].push(userMsg);
    appendBubble(userMsg);
    input.value = "";
    autosize();
    saveHistory();
    renderList();

    const pending = { role: "bot", pending: true, ts: Date.now() };
    history[active.id].push(pending);
    const ui = appendBubble(pending);
    sendBtn.disabled = true;

    const mode = modes[active.id] || active.defaultMode || "agent";
    const started = performance.now();
    try {
      async function call(kind) {
        const res = await fetch(`/api/agents/${active.id}/${kind}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, session_id: sessionFor(active.id) }),
        });
        const data = await res.json().catch(() => ({}));
        return { res, data };
      }
      let kind = mode === "agent" ? "agent" : "query";
      let { res, data } = await call(kind);
      if (kind === "agent" && (res.status === 404 || res.status === 405)) {
        ({ res, data } = await call("query"));
      }
      const elapsed = Math.round(performance.now() - started);
      if (!res.ok && !data.output) throw new Error(data.detail || `HTTP ${res.status}`);

      const out = data.output || data.detail || "(пустой ответ)";
      const verdict = data.verdict || null;
      const metaBits = [`${elapsed} мс`];
      if (data.route) metaBits.push(data.route);
      if (data.diagnostics?.violation_layer) metaBits.push(data.diagnostics.violation_layer);

      const finalMsg = {
        role: "bot",
        text: out,
        verdict,
        meta: metaBits.join(" · "),
        ts: Date.now(),
      };
      history[active.id][history[active.id].length - 1] = finalMsg;
      ui.bubble.innerHTML = formatText(finalMsg.text);
      const foot = document.createElement("div");
      foot.className = "msg-foot";
      if (verdict) {
        const b = document.createElement("span");
        b.className = `badge ${String(verdict).toLowerCase()}`;
        b.textContent = verdict;
        foot.appendChild(b);
      }
      const t = document.createElement("span");
      t.textContent = finalMsg.meta;
      foot.appendChild(t);
      ui.bubble.appendChild(foot);
      onlineMap[active.id] = true;
    } catch (err) {
      const finalMsg = {
        role: "bot",
        text: `Ошибка: ${err.message || err}`,
        verdict: "RED",
        meta: "error",
        ts: Date.now(),
      };
      history[active.id][history[active.id].length - 1] = finalMsg;
      ui.bubble.textContent = finalMsg.text;
      onlineMap[active.id] = false;
      pingOne(active.id);
    } finally {
      saveHistory();
      renderList();
      sendBtn.disabled = false;
      input.focus();
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  });

  // ─── Настройки ─────────────────────────────────────────────
  const settingsModal = document.getElementById("settingsModal");
  const settingsForm = document.getElementById("settingsForm");
  const sTarget = document.getElementById("sTarget");
  const sApi = document.getElementById("sApi");
  const sChat = document.getElementById("sChat");
  const sLocal = document.getElementById("sLocal");
  const sApplyAll = document.getElementById("sApplyAll");
  const sStatus = document.getElementById("sStatus");

  async function openSettings() {
    const res = await fetch("/api/settings", { cache: "no-store" });
    const s = await res.json();
    sTarget.value = s.default_target || "studio";
    sApi.value = s.api_url || "http://10.0.0.1:8000";
    sChat.value = s.chat_url || "http://10.0.0.1:8000/chat";
    sLocal.value = s.local_url || "http://127.0.0.1:8000";
    sApplyAll.checked = s.apply_to_all_agents !== false;
    const bits = [];
    if (s.studio_ok) bits.push("боевой OK");
    else bits.push("боевой нет связи");
    if (s.local_ok) bits.push("localhost OK");
    sStatus.textContent = bits.join(" · ") + (s.upstream ? ` · сейчас ${s.upstream}` : "");
    sStatus.className = "settings-status " + (s.studio_ok || s.local_ok ? "ok" : "bad");
    settingsModal.showModal();
  }

  document.getElementById("btnSettings").addEventListener("click", openSettings);
  document.getElementById("btnSettingsFoot").addEventListener("click", openSettings);
  document.getElementById("btnEmptySettings")?.addEventListener("click", openSettings);
  document.getElementById("btnSettingsCancel").addEventListener("click", () => settingsModal.close());

  function syncChatFromApi() {
    const base = sApi.value.trim().replace(/\/$/, "");
    if (!base) return;
    if (!sChat.value || sChat.value.endsWith("/chat") || sChat.value.includes(base)) {
      sChat.value = base + "/chat";
    }
  }

  sTarget.addEventListener("change", () => {
    if (sTarget.value === "local") {
      sApi.value = sLocal.value.trim() || "http://127.0.0.1:8000";
    } else if (sTarget.value === "studio") {
      if (!sApi.value || sApi.value.includes("127.0.0.1") || sApi.value.includes("localhost")) {
        sApi.value = "http://10.0.0.1:8000";
      }
    }
    syncChatFromApi();
  });

  sApi.addEventListener("change", syncChatFromApi);
  sApi.addEventListener("input", () => {
    // при наборе API — держим /chat в синхроне, если пользователь не правил chat вручную
    if (sChat.dataset.manual !== "1") syncChatFromApi();
  });
  sChat.addEventListener("input", () => {
    sChat.dataset.manual = "1";
  });

  document.getElementById("btnTestApi").addEventListener("click", async () => {
    const target = sTarget.value;
    let url = sApi.value.trim();
    if (target === "local") url = sLocal.value.trim() || "http://127.0.0.1:8000";
    sStatus.textContent = "проверка…";
    sStatus.className = "settings-status";
    const res = await fetch("/api/settings/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();
    sStatus.textContent = data.ok ? `OK · ${data.url}` : `Нет связи · ${data.url}`;
    sStatus.className = "settings-status " + (data.ok ? "ok" : "bad");
  });

  document.getElementById("btnOpenCombat").addEventListener("click", () => {
    const url = sChat.value.trim() || "http://10.0.0.1:8000/chat";
    window.open(url, "_blank");
  });

  document.getElementById("btnResetAgents").addEventListener("click", async () => {
    if (!confirm("Загрузить 7 агентов из репо? Текущий список будет заменён.")) return;
    const res = await fetch("/api/agents/reset", { method: "POST" });
    if (!res.ok) {
      alert("Не удалось сбросить список агентов");
      return;
    }
    history = {};
    saveHistory();
    localStorage.removeItem(ACTIVE_KEY);
    await loadAgents();
    sStatus.textContent = "Список агентов восстановлен (7)";
    sStatus.className = "settings-status ok";
  });

  settingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      api_url: sApi.value.trim(),
      chat_url: sChat.value.trim(),
      local_url: sLocal.value.trim() || "http://127.0.0.1:8000",
      default_target: sTarget.value,
      apply_to_all_agents: sApplyAll.checked,
    };
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      alert(data.detail || "Не сохранилось");
      return;
    }
    hubStatus.textContent = "API → " + (data.upstream || payload.api_url);
    settingsModal.close();
    await loadAgents();
    if (active) pingOne(active.id);
  });

  loadAgents().catch((e) => {
    hubStatus.textContent = "ошибка загрузки";
    console.error(e);
  });
  // подтянуть статус из настроек
  fetch("/api/settings")
    .then((r) => r.json())
    .then((s) => {
      hubStatus.textContent = s.upstream
        ? `API → ${s.upstream}`
        : "настройки";
    })
    .catch(() => {});
  setInterval(pingAll, 30000);
})();
