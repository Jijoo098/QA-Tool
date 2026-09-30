// Talks to the FastAPI routes on this same server. No secrets live here.

const state = {
  projects: [],
  projectId: null,
  requirements: [],
  requirementId: null,
  testCases: [],
  editingCaseId: null,
};

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------

function errorText(data) {
  if (!data) return "Request failed";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        const field = (item.loc || []).filter((part) => part !== "body").join(".");
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join(" ");
  }
  return "Request failed";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(errorText(data));
  }
  return data;
}

function showMessage(text, isError) {
  const box = $("message");
  box.hidden = !text;
  box.textContent = text || "";
  box.className = isError ? "message error" : "message ok";
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

async function loadProjects() {
  state.projects = await api("/projects");
  renderProjects();
}

function renderProjects() {
  const list = $("project-list");
  list.replaceChildren();
  if (state.projects.length === 0) {
    const note = document.createElement("p");
    note.className = "empty-note";
    note.textContent = "No projects yet.";
    list.append(note);
    return;
  }
  for (const project of state.projects) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "item" + (project.id === state.projectId ? " active" : "");
    const title = document.createElement("span");
    title.className = "item-title";
    title.textContent = project.name;
    button.append(title);
    if (project.description) {
      const meta = document.createElement("span");
      meta.className = "item-meta";
      meta.textContent = project.description;
      button.append(meta);
    }
    button.addEventListener("click", () => selectProject(project.id));
    item.append(button);
    list.append(item);
  }
}

async function selectProject(projectId) {
  state.projectId = projectId;
  state.requirementId = null;
  state.testCases = [];
  showMessage("");
  renderProjects();
  const project = state.projects.find((item) => item.id === projectId);
  $("welcome").hidden = true;
  $("project-view").hidden = false;
  $("cases-panel").hidden = true;
  $("project-title").textContent = project ? project.name : "";
  $("project-description").textContent = project && project.description ? project.description : "";
  await loadRequirements();
}

async function createProject(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const body = {
    name: data.get("name"),
    description: data.get("description"),
  };
  try {
    const project = await api("/projects", {
      method: "POST",
      body: JSON.stringify(body),
    });
    form.reset();
    form.hidden = true;
    await loadProjects();
    await selectProject(project.id);
    showMessage("Project saved.");
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function deleteProject() {
  const project = state.projects.find((item) => item.id === state.projectId);
  if (!project) return;
  const ok = window.confirm(
    `Delete "${project.name}" and all of its requirements and test cases?`
  );
  if (!ok) return;
  try {
    await api(`/projects/${project.id}`, { method: "DELETE" });
    state.projectId = null;
    state.requirementId = null;
    $("project-view").hidden = true;
    $("welcome").hidden = false;
    await loadProjects();
    showMessage("Project deleted.");
  } catch (error) {
    showMessage(error.message, true);
  }
}

// ---------------------------------------------------------------------------
// Requirements
// ---------------------------------------------------------------------------

async function loadRequirements() {
  state.requirements = await api(`/requirements?project_id=${state.projectId}`);
  renderRequirements();
}

function renderRequirements() {
  const list = $("requirement-list");
  list.replaceChildren();
  if (state.requirements.length === 0) {
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "No requirements yet.";
    list.append(note);
    return;
  }
  for (const requirement of state.requirements) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "item" + (requirement.id === state.requirementId ? " active" : "");
    const title = document.createElement("span");
    title.className = "item-title";
    title.textContent = requirement.title;
    button.append(title);
    if (requirement.description) {
      const meta = document.createElement("span");
      meta.className = "item-meta";
      meta.textContent = requirement.description;
      button.append(meta);
    }
    button.addEventListener("click", () => selectRequirement(requirement.id));
    item.append(button);
    list.append(item);
  }
}

async function selectRequirement(requirementId) {
  state.requirementId = requirementId;
  const requirement = state.requirements.find((item) => item.id === requirementId);
  $("cases-panel").hidden = false;
  $("requirement-title").textContent = requirement ? requirement.title : "";
  renderRequirements();
  await loadTestCases();
}

async function createRequirement(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const body = {
    project_id: state.projectId,
    title: data.get("title"),
    description: data.get("description"),
  };
  try {
    const requirement = await api("/requirements", {
      method: "POST",
      body: JSON.stringify(body),
    });
    form.reset();
    form.hidden = true;
    await loadRequirements();
    await selectRequirement(requirement.id);
    showMessage("Requirement saved.");
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function deleteRequirement() {
  const requirement = state.requirements.find((item) => item.id === state.requirementId);
  if (!requirement) return;
  const ok = window.confirm(
    `Delete "${requirement.title}" and all of its test cases?`
  );
  if (!ok) return;
  try {
    await api(`/requirements/${requirement.id}`, { method: "DELETE" });
    state.requirementId = null;
    $("cases-panel").hidden = true;
    await loadRequirements();
    showMessage("Requirement deleted.");
  } catch (error) {
    showMessage(error.message, true);
  }
}

// ---------------------------------------------------------------------------
// Test cases
// ---------------------------------------------------------------------------

function filterQuery() {
  const params = new URLSearchParams();
  params.set("requirement_id", String(state.requirementId));
  const type = $("filter-type").value;
  const priority = $("filter-priority").value;
  const status = $("filter-status").value;
  if (type) params.set("type", type);
  if (priority) params.set("priority", priority);
  if (status) params.set("status", status);
  return params.toString();
}

async function loadTestCases() {
  state.testCases = await api(`/testcases?${filterQuery()}`);
  renderTestCases();
}

function badge(text, kind) {
  const span = document.createElement("span");
  span.className = `badge ${kind}`;
  span.textContent = text;
  return span;
}

function renderTestCases() {
  const rows = $("case-rows");
  rows.replaceChildren();
  const filtered =
    $("filter-type").value || $("filter-priority").value || $("filter-status").value;
  $("cases-empty").hidden = state.testCases.length !== 0;
  $("cases-empty").textContent = filtered
    ? "No test cases match these filters."
    : "No test cases yet.";
  for (const testCase of state.testCases) {
    const row = document.createElement("tr");
    const idCell = document.createElement("td");
    idCell.textContent = String(testCase.id);
    const titleCell = document.createElement("td");
    titleCell.textContent = testCase.title;
    const typeCell = document.createElement("td");
    typeCell.append(badge(testCase.type, testCase.type));
    const priorityCell = document.createElement("td");
    priorityCell.append(badge(testCase.priority, testCase.priority.toLowerCase()));
    const statusCell = document.createElement("td");
    statusCell.append(badge(testCase.status, testCase.status.toLowerCase()));

    const actions = document.createElement("td");
    actions.className = "actions";
    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn btn-small";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", () => openCaseModal(testCase));
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "btn btn-small";
    deleteBtn.textContent = "Delete";
    deleteBtn.addEventListener("click", () => deleteTestCase(testCase));
    actions.append(editBtn, deleteBtn);

    row.append(idCell, titleCell, typeCell, priorityCell, statusCell, actions);
    rows.append(row);
  }
}

function openCaseModal(testCase) {
  const form = $("case-form");
  form.reset();
  state.editingCaseId = testCase ? testCase.id : null;
  $("case-modal-title").textContent = testCase ? "Edit test case" : "Add test case";
  if (testCase) {
    form.title.value = testCase.title;
    form.type.value = testCase.type;
    form.priority.value = testCase.priority;
    form.status.value = testCase.status;
    form.preconditions.value = testCase.preconditions || "";
    form.steps.value = testCase.steps || "";
    form.expected_result.value = testCase.expected_result || "";
  }
  $("case-modal").hidden = false;
  form.title.focus();
}

function closeCaseModal() {
  $("case-modal").hidden = true;
  state.editingCaseId = null;
}

async function saveTestCase(event) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const body = {
    requirement_id: state.requirementId,
    title: data.get("title"),
    type: data.get("type"),
    priority: data.get("priority"),
    status: data.get("status"),
    preconditions: data.get("preconditions"),
    steps: data.get("steps"),
    expected_result: data.get("expected_result"),
  };
  const path = state.editingCaseId ? `/testcases/${state.editingCaseId}` : "/testcases";
  const method = state.editingCaseId ? "PUT" : "POST";
  try {
    await api(path, { method, body: JSON.stringify(body) });
    closeCaseModal();
    await loadTestCases();
    showMessage("Test case saved.");
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function deleteTestCase(testCase) {
  const ok = window.confirm(`Delete test case "${testCase.title}"?`);
  if (!ok) return;
  try {
    await api(`/testcases/${testCase.id}`, { method: "DELETE" });
    await loadTestCases();
    showMessage("Test case deleted.");
  } catch (error) {
    showMessage(error.message, true);
  }
}

function exportExcel() {
  if (!state.projectId) return;
  // The browser downloads the .xlsx from the export route.
  window.location.href = `/export/${state.projectId}`;
}

// ---------------------------------------------------------------------------
// Wire up the page
// ---------------------------------------------------------------------------

$("show-project-form").addEventListener("click", () => {
  $("project-form").hidden = false;
  $("project-form").name.focus();
});
$("cancel-project").addEventListener("click", () => {
  $("project-form").reset();
  $("project-form").hidden = true;
});
$("project-form").addEventListener("submit", createProject);
$("delete-project-btn").addEventListener("click", deleteProject);

$("show-requirement-form").addEventListener("click", () => {
  $("requirement-form").hidden = false;
  $("requirement-form").title.focus();
});
$("cancel-requirement").addEventListener("click", () => {
  $("requirement-form").reset();
  $("requirement-form").hidden = true;
});
$("requirement-form").addEventListener("submit", createRequirement);
$("delete-requirement-btn").addEventListener("click", deleteRequirement);

$("add-case-btn").addEventListener("click", () => openCaseModal(null));
$("cancel-case").addEventListener("click", closeCaseModal);
$("case-form").addEventListener("submit", saveTestCase);
$("case-modal").addEventListener("click", (event) => {
  if (event.target === $("case-modal")) closeCaseModal();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeCaseModal();
});

for (const id of ["filter-type", "filter-priority", "filter-status"]) {
  $(id).addEventListener("change", () => {
    loadTestCases().catch((error) => showMessage(error.message, true));
  });
}

$("export-btn").addEventListener("click", exportExcel);

loadProjects().catch((error) => showMessage(error.message, true));
