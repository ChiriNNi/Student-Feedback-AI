(() => {
  "use strict";

  const adminWorkspace = $("adminOperationsWorkspace");
  const actionsWorkspace = $("actionsSection");
  const dialog = $("workflowDialog");
  const fields = $("workflowFields");
  const errorBox = $("workflowError");
  const saveButton = $("workflowSave");
  const surveyStatuses = { draft: "Draft", open: "Published", closed: "Closed" };
  const actionStatuses = { planned: "Planned", in_progress: "In progress", done: "Done" };
  const tones = { positive: "Positive", neutral: "Neutral", negative: "Negative" };
  const surveyKinds = { course: "Course evaluation", service: "Service review", survey: "General survey" };
  const defaultPrompt = "What did you like, and what should be improved?";
  const h = escapeHtml;

  let adminView = null;
  let adminData = [];
  let adminQuery = "";
  let adminRequest = 0;
  let actions = [];
  let actionFilter = "";
  let actionsRequest = 0;
  let editorRequest = 0;
  let saveEditor = null;

  function roleIs(role) {
    return currentSession?.user?.role === role;
  }

  async function request(path, options = {}) {
    const token = currentSession?.token;
    if (!token) throw Error("Sign in to continue.");
    const { ok, data, status, network } = await api(path, { ...options, token });
    if (token !== currentSession?.token) throw Error("The session has changed.");
    if (status === 401) return sessionRevoked(), Promise.reject(Error("Sign in to continue."));
    if (ok) return data;
    const detail = data?.detail;
    const validation = Array.isArray(detail) ? detail.map(entry => entry.msg).join(". ") : "";
    throw Error(network ? "Cannot reach the server." : typeof detail === "string" ? detail
      : validation || "Could not complete the request. Try again.");
  }

  const options = (entries, selected) => entries.map(([value, label]) =>
    `<option value="${h(String(value))}"${value === selected ? " selected" : ""}>${h(label)}</option>`).join("");
  const select = (name, label, entries, value, attrs = "") =>
    `<label>${h(label)}<select name="${name}" ${attrs}>${options(entries, value)}</select></label>`;
  const input = (name, label, value = "", attrs = "") =>
    `<label>${h(label)}<input name="${name}" value="${h(value)}" ${attrs}></label>`;
  const textarea = (name, label, value, maxlength) =>
    `<label class="workflow-wide">${h(label)}<textarea name="${name}" rows="3" maxlength="${maxlength}">${h(value || "")}</textarea></label>`;
  const badge = (key, labels) => `<span class="workflow-badge is-${key}">${h(labels[key] || key)}</span>`;
  const primary = (type, label) => `<button class="btn-sm workflow-primary" type="button" data-workflow-new="${type}">${label}</button>`;

  function setEditorError(message = "") {
    errorBox.textContent = message;
    errorBox.hidden = !message;
  }

  function openEditor(title, body, save, submitLabel = "Save changes") {
    $("workflowDialogTitle").textContent = title;
    fields.innerHTML = body;
    saveEditor = save;
    saveButton.textContent = submitLabel;
    saveButton.disabled = false;
    setEditorError();
    if (!dialog.open) dialog.showModal();
  }

  dialog.addEventListener("click", event => {
    if (event.target.closest("[data-workflow-close]") && !saveButton.disabled) dialog.close();
  });
  dialog.addEventListener("cancel", event => {
    if (saveButton.disabled) event.preventDefault();
  });
  dialog.addEventListener("close", () => {
    // A scope lookup can finish after the editor has been dismissed.
    editorRequest += 1;
  });
  $("workflowForm").addEventListener("submit", async event => {
    event.preventDefault();
    if (!saveEditor || saveButton.disabled) return;
    const token = currentSession?.token;
    setEditorError();
    saveButton.disabled = true;
    try {
      const result = await saveEditor(new FormData(event.currentTarget));
      if (result === false || token !== currentSession?.token) return;
      dialog.close();
      if (typeof result === "function") result();
    } catch (error) {
      if (token === currentSession?.token) setEditorError(error.message);
    } finally {
      saveButton.disabled = false;
    }
  });

  function renderError(root, message, retry) {
    root.innerHTML = `<div class="workflow-empty"><p>${h(message)}</p>
      <button type="button" class="btn-sm" data-workflow-retry="${retry}">Try again</button></div>`;
  }

  function adminHeading() {
    return adminView === "surveys"
      ? ["Surveys", "Create evaluation forms, publish them for students and close completed surveys.", "New survey"]
      : ["Topic categories", "Manage the words and phrases used to classify new feedback.", "New topic"];
  }

  function surveyRow(survey) {
    const lifecycle = { draft: "Publish", open: "Close survey", closed: "Reopen" }[survey.status];
    return `<article class="workflow-row">
      <div class="workflow-row-main">
        <div class="workflow-row-title"><h2>${h(survey.title)}</h2>${badge(survey.status, surveyStatuses)}</div>
        <p>${h(surveyKinds[survey.kind] || survey.kind)} · ${h(survey.semester)} · ${plural(survey.responses, "response")}</p>
      </div>
      <div class="workflow-row-actions">
        <button type="button" class="btn-sm" data-workflow-edit="${survey.id}">Edit</button>
        <button type="button" class="btn-sm" data-survey-lifecycle="${survey.id}">${lifecycle}</button>
      </div>
    </article>`;
  }

  function topicRow(topic) {
    return `<article class="workflow-row">
      <div class="workflow-row-main">
        <div class="workflow-row-title"><span class="workflow-color" style="--topic-color:${h(/^#[0-9a-f]{6}$/i.test(topic.color) ? topic.color : "#8b5cff")}" aria-hidden="true"></span>
          <h2>${h(topic.name)}</h2>${badge(topic.is_active ? "active" : "inactive", { active: "Active", inactive: "Inactive" })}</div>
        <ul class="workflow-keywords">${(topic.keywords || []).slice(0, 6).map(word => `<li>${h(word)}</li>`).join("")}
          ${topic.keywords?.length > 6 ? `<li>+${topic.keywords.length - 6}</li>` : ""}</ul>
      </div>
      <button type="button" class="btn-sm" data-workflow-edit="${topic.id}">Edit</button>
    </article>`;
  }

  function renderAdminRows() {
    const list = $("workflowAdminRows");
    if (!list) return;
    const q = adminQuery.trim().toLowerCase();
    const records = adminData.filter(item => [item.title, item.name, item.semester, ...(item.keywords || [])]
      .filter(Boolean).some(value => value.toLowerCase().includes(q)));
    list.innerHTML = records.length ? records.map(adminView === "surveys" ? surveyRow : topicRow).join("")
      : `<p class="workflow-empty">${q ? "No results match your search." : adminView === "surveys" ? "No surveys yet." : "No topic categories yet."}</p>`;
  }

  async function loadAdminWorkspace(view, preserveSearch = false) {
    if (!roleIs("admin")) return;
    if (!preserveSearch) adminQuery = "";
    adminView = view;
    adminData = [];
    const revision = ++adminRequest;
    $("adminUsersWorkspace").hidden = true;
    adminWorkspace.hidden = false;
    $("adminApp").querySelector('[data-nav="admin"]').removeAttribute("aria-current");
    $("adminApp").querySelectorAll("[data-admin-workspace]").forEach(button => {
      if (button.dataset.adminWorkspace === view) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    const [title, description, create] = adminHeading();
    adminWorkspace.innerHTML = `<header class="adm-head"><div><h1>${title}</h1><p>${description}</p></div>${primary(view, create)}</header>
      <section class="workflow-surface" aria-label="${title}">
        <div class="workflow-toolbar">${input("workflowSearch", "Search", adminQuery, 'type="search" autocomplete="off"')}</div>
        <div id="workflowAdminRows" aria-live="polite"><p class="workflow-empty">Loading…</p></div>
      </section>`;
    try {
      const data = await request(`/admin/${view}`);
      if (revision !== adminRequest || adminWorkspace.hidden) return;
      adminData = view === "surveys" ? data.items : data;
      renderAdminRows();
    } catch (error) {
      if (revision === adminRequest && !adminWorkspace.hidden) renderError($("workflowAdminRows"), error.message, view);
    }
  }

  function questionRow(question = {}) {
    return `<div class="workflow-question">
      ${input("questionLabel", "Short label", question.label, 'required maxlength="40"')}
      ${input("questionText", "Rating statement", question.text, 'required maxlength="300"')}
      <button type="button" class="btn-sm" data-remove-question>Remove</button>
    </div>`;
  }

  function openSurveyEditor(survey = null) {
    const locked = Boolean(survey?.form_locked);
    const readOnly = locked ? " disabled" : "";
    const questions = survey?.questions || [{ label: "", text: "" }];
    const semester = survey?.semester || [...adminData].find(s => s.status === "open")?.semester || "";
    openEditor(survey ? "Edit survey" : "New survey", `<div class="workflow-fields">
      ${input("title", "Survey title", survey?.title, 'required minlength="3" maxlength="200"')}
      ${input("semester", "Semester", semester, 'required maxlength="24" placeholder="Fall 2026"' + readOnly)}
      ${select("kind", "Form type", Object.entries(surveyKinds), survey?.kind || "course", readOnly)}
      ${input("question", "Comment prompt", survey?.question || defaultPrompt, 'required maxlength="300"' + readOnly)}
      ${textarea("description", "Description for students", survey?.description, 2000)}
    </div>
    <fieldset class="workflow-questions"${readOnly}>
      <legend>Rating questions</legend>
      <p class="workflow-help">${locked ? "This form is published or has responses. You can edit its title and description." : "Students rate each statement from 1 to 5. A general survey can use a written response only."}</p>
      <div id="workflowQuestions">${questions.map(questionRow).join("")}</div>
      ${locked ? "" : '<button type="button" class="btn-sm" data-add-question>Add question</button>'}
    </fieldset>`, async data => {
      const labels = data.getAll("questionLabel");
      const statements = data.getAll("questionText");
      const body = {
        title: data.get("title"), description: data.get("description"),
        kind: locked ? survey.kind : data.get("kind"),
        semester: locked ? survey.semester : data.get("semester"),
        question: locked ? survey.question : data.get("question"),
        ...(locked ? {} : { questions: labels.map((label, i) => ({ label, text: statements[i] })) }),
      };
      await request(`/admin/surveys${survey ? "/" + survey.id : ""}`, { method: survey ? "PUT" : "POST", body });
      return () => { toast(survey ? "Survey saved." : "Draft survey created."); loadAdminWorkspace("surveys", true); };
    }, survey ? "Save changes" : "Create draft");
  }

  function openSurveyLifecycle(survey) {
    const closing = survey.status === "open";
    const label = closing ? "Close survey" : survey.status === "closed" ? "Reopen survey" : "Publish survey";
    openEditor(label, `<p><strong>${h(survey.title)}</strong></p>
      <p class="workflow-help">${closing ? "Students will stop seeing this form. Existing responses stay available."
        : "Students will see this form in Give feedback. Its questions will be locked while it is published."}</p>`, async () => {
      await request(`/admin/surveys/${survey.id}/status`, { method: "PATCH", body: { status: closing ? "closed" : "open" } });
      return () => { toast(closing ? "Survey closed." : "Survey published."); loadAdminWorkspace("surveys", true); };
    }, label);
  }

  function openTopicEditor(topic = null) {
    openEditor(topic ? "Edit topic category" : "New topic category", `<div class="workflow-fields">
      ${input("name", "Category name", topic?.name, 'required minlength="2" maxlength="80"')}
      ${input("color", "Chart color", topic?.color || "#8b5cff", 'type="color"')}
      ${textarea("keywords", "Keywords and phrases", (topic?.keywords || []).join("\n"), 8000)}
      <p class="workflow-help workflow-wide">Separate terms with commas or line breaks. Include terms in the languages students use.</p>
      <label class="workflow-check workflow-wide"><input type="checkbox" name="is_active"${topic?.is_active === false ? "" : " checked"}>Active in new analysis</label>
    </div>`, async data => {
      const body = { name: data.get("name"), color: data.get("color"), is_active: data.has("is_active"),
        keywords: data.get("keywords").split(/[\n,]/).map(word => word.trim()).filter(Boolean) };
      await request(`/admin/topics${topic ? "/" + topic.id : ""}`, { method: topic ? "PUT" : "POST", body });
      rspState.meta = null;
      return () => { toast("Topic category saved."); loadAdminWorkspace("topics", true); };
    });
  }

  $("adminApp").addEventListener("click", event => {
    const nav = event.target.closest("[data-admin-workspace]");
    if (nav) loadAdminWorkspace(nav.dataset.adminWorkspace);
  });
  adminWorkspace.addEventListener("input", event => {
    if (event.target.name === "workflowSearch") {
      adminQuery = event.target.value;
      if (adminData.length) renderAdminRows();
    }
  });
  adminWorkspace.addEventListener("click", event => {
    const button = event.target.closest("button");
    if (!button || !roleIs("admin")) return;
    if (button.dataset.workflowRetry) return loadAdminWorkspace(adminView, true);
    if (button.dataset.workflowNew) {
      return adminView === "surveys" ? openSurveyEditor() : openTopicEditor();
    }
    const item = adminData.find(record => record.id === Number(button.dataset.workflowEdit || button.dataset.surveyLifecycle));
    if (!item) return;
    if (button.dataset.surveyLifecycle) return openSurveyLifecycle(item);
    return adminView === "surveys" ? openSurveyEditor(item) : openTopicEditor(item);
  });

  function showCorrection(feedback, categories) {
    const chosen = new Map((feedback.topics || []).map(topic => [topic, tones[feedback.aspects?.[topic]] ? feedback.aspects[topic] : toneOf(feedback.sentiment)]));
    openEditor("Correct analysis", `<div class="workflow-feedback"><b>${h(feedback.target)}</b>
      ${feedback.comment ? `<p class="rsp-text">${highlightPh(feedback.comment)}</p>` : "<p>No written comment, ratings only.</p>"}</div>
      <div class="workflow-fields">
        ${select("sentiment", "Overall sentiment", Object.entries(tones), toneOf(feedback.sentiment))}
        <div class="workflow-wide"><h3>Topic labels</h3><div id="workflowTopicLabels"></div>
        ${select("addTopic", "Add category", [["", "Choose a topic"]], "")}</div>
        ${textarea("reason", "Reason for correction (optional)", "", 300)}
      </div>`, async data => {
      await request(`/admin/feedback/${feedback.id}/analysis`, { method: "PATCH", body: {
        sentiment: data.get("sentiment"), topics: [...chosen.keys()], aspects: Object.fromEntries(chosen), reason: data.get("reason"),
      } });
      return () => { toast("Analysis saved."); loadResponses(); };
    });
    const picker = fields.querySelector('[name="addTopic"]');
    const render = () => {
      $("workflowTopicLabels").innerHTML = [...chosen].map(([topic, tone], i) => `<div class="workflow-label-row">
        <span>${h(topic)}</span>${select(`topicTone${i}`, "Topic sentiment", Object.entries(tones), tone)}
        <button type="button" class="btn-sm" data-remove-topic="${i}">Remove</button></div>`).join("");
      picker.innerHTML = options([["", "Choose a topic"], ...categories.filter(c => c.is_active && !chosen.has(c.name))
        .map(c => [c.name, c.name])], "");
      picker.disabled = picker.options.length < 2;
    };
    fields.querySelector("#workflowTopicLabels").addEventListener("change", event => {
      const index = Number(event.target.name.replace("topicTone", ""));
      chosen.set([...chosen.keys()][index], event.target.value);
    });
    fields.querySelector("#workflowTopicLabels").addEventListener("click", event => {
      const button = event.target.closest("[data-remove-topic]");
      if (!button) return;
      chosen.delete([...chosen.keys()][Number(button.dataset.removeTopic)]);
      render();
      picker.focus();
    });
    picker.addEventListener("change", () => {
      if (picker.value) chosen.set(picker.value, fields.querySelector('[name="sentiment"]').value);
      render();
    });
    render();
  }

  const actionTarget = action => action.course_id ? `course:${action.course_id}` : action.service_id
    ? `service:${action.service_id}` : action.department_id ? `department:${action.department_id}` : "";
  const targetParams = target => {
    const [kind, id] = target.split(":");
    return id ? { [`${kind}_id`]: Number(id) } : {};
  };

  function actionRow(action) {
    return `<article class="workflow-row workflow-action-row">
      <div class="workflow-row-main">
        <div class="workflow-row-title"><h2>${h(action.title)}</h2>${badge(action.status, actionStatuses)}</div>
        <p>${h([action.topic || "Unlinked action", action.target, action.owner].filter(Boolean).join(" · "))}</p>
        ${action.description ? `<p class="workflow-description">${h(action.description)}</p>` : ""}
        ${action.due_date ? `<p class="${action.overdue ? "workflow-overdue" : ""}">${action.overdue ? "Overdue" : "Due"} · <time datetime="${h(action.due_date)}">${h(action.due_date)}</time></p>` : ""}
      </div>
      <div class="workflow-row-actions">
        <label class="fx-sr" for="action-status-${action.id}">Action status</label>
        <select class="workflow-status-select" id="action-status-${action.id}" data-action-status="${action.id}">${options(Object.entries(actionStatuses), action.status)}</select>
        <button type="button" class="btn-sm" data-edit-action="${action.id}">Edit</button>
      </div>
    </article>`;
  }

  function renderActions() {
    const filters = [["", "All actions"], ...Object.entries(actionStatuses)];
    const visible = actions.filter(action => !actionFilter || action.status === actionFilter);
    actionsWorkspace.innerHTML = `<header class="adm-head"><div><h1>Improvement actions</h1>
      <p>Assign follow-up work to recurring feedback problems and track its status.</p></div>${primary("action", "New action")}</header>
      <div class="workflow-segments" role="group" aria-label="Filter by status">${filters.map(([value, label]) => `
        <button type="button" class="btn-sm" data-action-filter="${value}" aria-pressed="${actionFilter === value}">
          ${label} <b>${actions.filter(action => !value || action.status === value).length}</b></button>`).join("")}</div>
      <div class="workflow-surface" aria-live="polite">${visible.length ? visible.map(actionRow).join("")
        : '<p class="workflow-empty">No actions in this view.</p>'}</div>`;
  }

  async function loadActions() {
    if (!roleIs("manager")) return;
    const revision = ++actionsRequest;
    actionsWorkspace.innerHTML = '<h1 class="workflow-heading">Improvement actions</h1><p class="workflow-empty">Loading…</p>';
    try {
      const data = await request("/actions");
      if (revision !== actionsRequest) return;
      actions = data;
      renderActions();
    } catch (error) {
      if (revision === actionsRequest) renderError(actionsWorkspace, error.message, "actions");
    }
  }

  async function openActionEditor(action = null, context = {}) {
    const chosenTarget = action ? actionTarget(action) : context.target || "";
    const revision = ++editorRequest;
    let meta;
    try {
      meta = rspState.meta || await request("/meta");
    } catch (error) {
      if (revision === editorRequest) toast(error.message);
      return;
    }
    if (revision !== editorRequest || !roleIs("manager")) return;
    const targets = [["", currentSession.user.department_id ? "My department" : "University-wide"],
      ...meta.departments.map(d => [`department:${d.id}`, d.name]),
      ...meta.courses.map(c => [`course:${c.id}`, `${c.code} — ${c.title}`]),
      ...meta.services.map(s => [`service:${s.id}`, s.name])];
    openEditor(action ? "Edit improvement action" : "New improvement action", `<div class="workflow-fields">
      ${input("title", "Action title", action?.title, 'required minlength="3" maxlength="200"')}
      ${select("target", "Action scope", targets, chosenTarget)}
      ${select("topic", "Recurring feedback problem", [["", "Choose a problem"]], "", 'required disabled')}
      ${input("owner", "Assigned to", action?.owner, 'maxlength="160"')}
      ${input("due_date", "Due date", action?.due_date || "", 'type="date"')}
      ${select("status", "Status", Object.entries(actionStatuses), action?.status || "planned")}
      ${textarea("description", "What will be done?", action?.description, 2000)}
      <p class="workflow-help workflow-wide" id="workflowProblemHint" aria-live="polite"></p>
    </div>`, async data => {
      const topic = data.get("topic");
      if (!topic) return setEditorError("Choose a recurring feedback problem."), false;
      const body = { title: data.get("title"), topic, owner: data.get("owner"), status: data.get("status"),
        due_date: data.get("due_date") || null, description: data.get("description"), ...targetParams(data.get("target")) };
      await request(`/actions${action ? "/" + action.id : ""}`, { method: action ? "PUT" : "POST", body });
      return () => {
        actionFilter = "";
        toast(action ? "Action saved." : "Improvement action created.");
        selectManagerView("actions");
      };
    }, action ? "Save changes" : "Create action");
    const target = fields.querySelector('[name="target"]');
    const topic = fields.querySelector('[name="topic"]');
    const hint = $("workflowProblemHint");
    let lookup = 0;
    const loadProblems = async (selected = "") => {
      const seq = ++lookup;
      topic.disabled = true;
      topic.innerHTML = options([["", "Loading…"]], "");
      hint.textContent = "";
      try {
        const problems = await request(`/actions/problems${queryString(targetParams(target.value))}`);
        if (seq !== lookup || revision !== editorRequest || !dialog.open) return;
        const available = problems.map(p => [p.topic, `${p.topic} · ${plural(p.negative, "negative mention")}`]);
        if (action?.topic && target.value === chosenTarget && !available.some(([v]) => v === action.topic)) {
          available.push([action.topic, action.topic]);
        }
        topic.innerHTML = options([["", "Choose a problem"], ...available], selected);
        topic.disabled = !available.length;
        hint.textContent = available.length ? "" : "No recurring negative themes in this scope. Choose a different scope.";
      } catch (error) {
        if (seq === lookup && revision === editorRequest && dialog.open) {
          topic.innerHTML = options([["", "Choose a problem"]], "");
          hint.textContent = error.message;
        }
      }
    };
    target.addEventListener("change", () => loadProblems());
    loadProblems(action?.topic || context.topic);
  }

  actionsWorkspace.addEventListener("click", event => {
    const button = event.target.closest("button");
    if (!button || !roleIs("manager")) return;
    if (button.dataset.workflowRetry) return loadActions();
    if (button.hasAttribute("data-action-filter")) {
      actionFilter = button.dataset.actionFilter;
      renderActions();
      actionsWorkspace.querySelector(`[data-action-filter="${actionFilter}"]`).focus();
    } else if (button.dataset.workflowNew) openActionEditor();
    else if (button.dataset.editAction) openActionEditor(actions.find(action => action.id === Number(button.dataset.editAction)));
  });
  actionsWorkspace.addEventListener("change", async event => {
    const select = event.target.closest("[data-action-status]");
    if (!select || !roleIs("manager")) return;
    const action = actions.find(item => item.id === Number(select.dataset.actionStatus));
    if (!action) return;
    select.disabled = true;
    try {
      const updated = await request(`/actions/${action.id}/status`, { method: "PATCH", body: { status: select.value } });
      actions = actions.map(item => item.id === updated.id ? updated : item);
      if (!actionsWorkspace.hidden) {
        renderActions();
        (actionsWorkspace.querySelector(`[data-action-status="${updated.id}"]`)
          || actionsWorkspace.querySelector(`[data-action-filter="${actionFilter}"]`)).focus();
      }
      toast("Action status updated.");
    } catch (error) {
      select.value = action.status;
      toast(error.message);
    } finally {
      select.disabled = false;
    }
  });

  fields.addEventListener("click", event => {
    const button = event.target.closest("button");
    if (button?.hasAttribute("data-add-question")) {
      const list = $("workflowQuestions");
      if (list.children.length >= 30) return;
      list.insertAdjacentHTML("beforeend", questionRow());
      list.lastElementChild.querySelector("input").focus();
    } else if (button?.hasAttribute("data-remove-question")) {
      button.closest(".workflow-question").remove();
      fields.querySelector("[data-add-question]").focus();
    }
  });
  responsesApp.addEventListener("click", async event => {
    const problem = event.target.closest("[data-action-topic]");
    if (problem && roleIs("manager")) {
      const context = { topic: problem.dataset.actionTopic,
        target: rspState.target || (rspState.department_id ? `department:${rspState.department_id}` : "") };
      return openActionEditor(null, context);
    }
    const button = event.target.closest("[data-correct-feedback]");
    if (!button || !roleIs("admin")) return;
    const feedback = rspState.data?.items.find(item => item.id === Number(button.dataset.correctFeedback));
    if (!feedback) return;
    const revision = ++editorRequest;
    button.disabled = true;
    try {
      const categories = await request("/admin/topics");
      if (revision === editorRequest && roleIs("admin")) showCorrection(feedback, categories);
    } catch (error) {
      if (revision === editorRequest) toast(error.message);
    } finally {
      button.disabled = false;
    }
  });
  document.addEventListener("workflow-actions-open", loadActions);
  document.addEventListener("workflow-reset", () => {
    adminRequest += 1;
    actionsRequest += 1;
    editorRequest += 1;
    adminData = actions = [];
    adminQuery = actionFilter = "";
    adminWorkspace.replaceChildren();
    actionsWorkspace.replaceChildren();
    if (dialog.open) dialog.close();
  });
})();
