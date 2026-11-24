"use strict";

/* =========================================================
   Productivity Manager - website version
   Same features and the same task file format as the desktop app.
   Tasks are saved in this browser (localStorage).
   ========================================================= */

const PRIORITIES = ["Low", "Medium", "High"];
const CATEGORIES = ["School", "Personal", "Work", "Other"];
const SORT_MODES = ["Deadline", "Priority", "Title (A-Z)"];
const PRIORITY_ORDER = { High: 0, Medium: 1, Low: 2 };

const STORAGE_KEY = "productivity-manager-tasks";
const THEME_KEY = "pm-theme";
const DAY_MS = 86400000;


/* =========================================================
   TASK LOGIC (no page code in this part)
   ========================================================= */

function pad(number) {
  return String(number).padStart(2, "0");
}

function newId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    try { return crypto.randomUUID(); } catch (e) { /* fall through */ }
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

// ----- dates -----

function makeDate(year, month, day) {
  const date = new Date(year, month - 1, day);
  const valid =
    date.getFullYear() === year &&
    date.getMonth() === month - 1 &&
    date.getDate() === day;
  return valid ? date : null;
}

// Stored format (same as the desktop app): YYYY-MM-DD
function parseStoredDate(text) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(text || "").trim());
  return m ? makeDate(+m[1], +m[2], +m[3]) : null;
}

// Typed and shown format: DD-MM-YYYY
function parseDisplayDate(text) {
  const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(String(text || "").trim());
  return m ? makeDate(+m[3], +m[2], +m[1]) : null;
}

function isValidDate(text) {
  const value = String(text || "").trim();
  return value === "" || parseDisplayDate(value) !== null;
}

function toDisplay(stored) {
  const d = parseStoredDate(stored);
  return d ? `${pad(d.getDate())}-${pad(d.getMonth() + 1)}-${d.getFullYear()}` : "";
}

function toStorage(display) {
  const d = parseDisplayDate(display);
  return d ? `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` : "";
}

// Keeps only digits and adds the dashes: 24122026 -> 24-12-2026
function formatDateTyping(text) {
  const digits = String(text || "").replace(/\D/g, "").slice(0, 8);
  return [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4)]
    .filter(Boolean)
    .join("-");
}

function today() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

// Moves a typed DD-MM-YYYY date by some days. An empty or unfinished date starts from today.
function shiftDisplayDate(text, days) {
  const base = parseDisplayDate(text) || today();
  base.setDate(base.getDate() + days);
  return `${pad(base.getDate())}-${pad(base.getMonth() + 1)}-${base.getFullYear()}`;
}

// ----- times of day (HH:MM, 24 hour clock) -----

function parseTime(text) {
  const m = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(String(text || "").trim());
  return m ? { h: +m[1], m: +m[2] } : null;
}

// A time is optional. If it is filled in, it must be HH:MM.
function isValidTime(text) {
  const value = String(text || "").trim();
  return value === "" || parseTime(value) !== null;
}

function cleanTime(value) {
  const text = String(value ?? "").trim();
  return isValidTime(text) ? text : "";
}

// Keeps only digits and adds the colon: 0830 -> 08:30. Typing 8 gives 08.
function formatTimeTyping(text) {
  let digits = String(text || "").replace(/\D/g, "");

  if (digits && digits[0] > "2") digits = "0" + digits;
  if (digits.length >= 3 && digits[2] > "5") digits = digits.slice(0, 2) + "0" + digits.slice(2);

  digits = digits.slice(0, 4);

  return digits.length > 2 ? `${digits.slice(0, 2)}:${digits.slice(2)}` : digits;
}

// ----- deadlines and reminders -----

// The moment a task expires. Without an "expires at" time that is the end of the day.
function dueDateTime(task) {
  const d = parseStoredDate(task.due_date);
  if (!d) return null;

  const t = parseTime(task.end_time);

  return t
    ? new Date(d.getFullYear(), d.getMonth(), d.getDate(), t.h, t.m, 0)
    : new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59);
}

// When the reminder should appear, or null if no reminder is set.
function reminderDateTime(task) {
  const d = parseStoredDate(task.due_date);
  const t = parseTime(task.reminder_time);

  return d && t ? new Date(d.getFullYear(), d.getMonth(), d.getDate(), t.h, t.m, 0) : null;
}

// Tasks whose reminder time has arrived and that were not reminded yet.
function pendingReminders(tasks, now = new Date()) {
  return tasks.filter((task) => {
    if (task.completed || task.reminded) return false;

    const when = reminderDateTime(task);
    return when !== null && now >= when;
  });
}

function daysBetween(due, now) {
  return Math.round((startOfDay(due) - startOfDay(now)) / DAY_MS);
}

function dueStatus(task, now = new Date()) {
  if (task.completed) return "done";

  const due = dueDateTime(task);

  if (!due) return "none";
  if (now > due) return "overdue";

  const days = daysBetween(due, now);

  if (days === 0) return "today";
  if (days <= 3) return "soon";
  return "later";
}

function dueLabel(task, now = new Date()) {
  const due = dueDateTime(task);

  if (!due) return "No deadline";

  const pretty = toDisplay(task.due_date);
  const at = parseTime(task.end_time) ? ` at ${task.end_time}` : "";

  if (task.completed) return `Due ${pretty}${at}`;

  const days = daysBetween(due, now);

  if (now > due) {
    if (days === 0) return `Expired today${at} · ${pretty}`;

    const over = -days;
    return `Overdue by ${over} ${over === 1 ? "day" : "days"} · ${pretty}${at}`;
  }

  if (days === 0) return `Due today${at} · ${pretty}`;
  if (days === 1) return `Due tomorrow${at} · ${pretty}`;
  return `Due in ${days} days · ${pretty}${at}`;
}

// ----- tasks -----

// Makes sure every task has all fields, so old or incomplete data never breaks the app.
function normalizeTask(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;

  const title = String(raw.title ?? "").trim();
  if (!title) return null;

  return {
    id: String(raw.id || newId()),
    title,
    description: String(raw.description ?? ""),
    due_date: String(raw.due_date ?? ""),
    priority: PRIORITIES.includes(raw.priority) ? raw.priority : "Medium",
    category: CATEGORIES.includes(raw.category) ? raw.category : "Other",
    completed: raw.completed === true,
    reminder_time: cleanTime(raw.reminder_time),
    end_time: cleanTime(raw.end_time),
    reminded: raw.reminded === true,
  };
}

function createTask({ title, description, due_date, priority, category, reminder_time = "", end_time = "" }) {
  return {
    id: newId(), title, description, due_date, priority, category,
    completed: false, reminder_time, end_time, reminded: false,
  };
}

function updateTask(tasks, id, changes) {
  const allowed = ["title", "description", "due_date", "priority", "category", "reminder_time", "end_time"];

  // Changing the date or the reminder time means the reminder should appear again
  const watched = ["due_date", "reminder_time"];

  return tasks.map((task) => {
    if (task.id !== id) return task;

    const updated = { ...task };

    for (const key of allowed) {
      if (!(key in changes)) continue;
      if (watched.includes(key) && updated[key] !== changes[key]) updated.reminded = false;
      updated[key] = changes[key];
    }

    return updated;
  });
}

function deleteTask(tasks, id) {
  return tasks.filter((task) => task.id !== id);
}

function toggleTask(tasks, id) {
  return tasks.map((task) =>
    task.id === id ? { ...task, completed: !task.completed } : task
  );
}

function clearCompleted(tasks) {
  return tasks.filter((task) => !task.completed);
}

// Adds imported tasks that are not already in the list (matched by id).
function mergeTasks(existing, incoming) {
  const known = new Set(existing.map((task) => task.id));
  const fresh = incoming.filter((task) => !known.has(task.id));
  return { tasks: [...existing, ...fresh], added: fresh.length };
}

function parseImport(text) {
  let data;

  try {
    data = JSON.parse(String(text).replace(/^﻿/, ""));
  } catch (e) {
    throw new Error("That file could not be read as a task list.");
  }

  if (!Array.isArray(data)) {
    throw new Error("That file does not look like a task backup.");
  }

  const tasks = data.map(normalizeTask).filter(Boolean);

  if (tasks.length === 0) {
    throw new Error("No tasks were found in that file.");
  }

  return tasks;
}

// ----- search, filter, sort -----

function searchTasks(tasks, query) {
  const q = String(query || "").trim().toLowerCase();

  if (!q) return [...tasks];

  return tasks.filter(
    (task) =>
      task.title.toLowerCase().includes(q) ||
      task.description.toLowerCase().includes(q)
  );
}

function filterTasks(tasks, status = "All", category = "All") {
  let result = tasks;

  if (status === "Completed") result = result.filter((t) => t.completed);
  else if (status === "Pending") result = result.filter((t) => !t.completed);

  if (category !== "All") result = result.filter((t) => t.category === category);

  return [...result];
}

function dateValue(task) {
  const d = dueDateTime(task);
  return d ? d.getTime() : Infinity;
}

function compare(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

// Pending tasks always come before completed ones.
function sortTasks(tasks, mode = "Deadline") {
  const priority = (t) => PRIORITY_ORDER[t.priority] ?? 1;

  const comparators = {
    "Priority": (a, b) => compare(priority(a), priority(b)) || compare(dateValue(a), dateValue(b)),
    "Title (A-Z)": (a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: "base" }),
    "Deadline": (a, b) => compare(dateValue(a), dateValue(b)) || compare(priority(a), priority(b)),
  };

  const inner = comparators[mode] || comparators["Deadline"];

  return [...tasks].sort((a, b) =>
    a.completed !== b.completed ? (a.completed ? 1 : -1) : inner(a, b)
  );
}

function getStats(tasks, now = new Date()) {
  const total = tasks.length;
  const completed = tasks.filter((t) => t.completed).length;
  const overdue = tasks.filter((t) => dueStatus(t, now) === "overdue").length;

  return { total, completed, pending: total - completed, overdue };
}

// ----- saving in the browser -----

function loadTasks() {
  let raw = null;

  try {
    raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return [];

    return data.map(normalizeTask).filter(Boolean);
  } catch (e) {
    // Unreadable data: keep a copy so nothing is silently lost.
    try { if (raw) localStorage.setItem(STORAGE_KEY + "-backup", raw); } catch (e2) { /* ignore */ }
    return [];
  }
}

function saveTasks(tasks) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
    return true;
  } catch (e) {
    return false;
  }
}


/* =========================================================
   PAGE CODE (only runs in a browser)
   ========================================================= */

function startApp() {
  const $ = (selector, root = document) => root.querySelector(selector);

  // Small helper that builds elements. User text is always set as text,
  // never as HTML, so a task title can never inject code.
  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);

    for (const [key, value] of Object.entries(attrs)) {
      if (value === null || value === undefined || value === false) continue;

      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    }

    for (const child of children.flat()) {
      if (child !== null && child !== undefined && child !== false) node.append(child);
    }

    return node;
  }

  const state = { tasks: loadTasks(), editingId: null, signature: "" };

  const ui = {
    subtitle: $("#subtitle"),
    statTotal: $("#statTotal"),
    statPending: $("#statPending"),
    statCompleted: $("#statCompleted"),
    statOverdue: $("#statOverdue"),
    progress: $("#progress"),
    progressBar: $("#progressBar"),
    search: $("#search"),
    statusFilter: $("#statusFilter"),
    categoryFilter: $("#categoryFilter"),
    sortMenu: $("#sortMenu"),
    countLabel: $("#countLabel"),
    taskList: $("#taskList"),
    taskForm: $("#taskForm"),
    editForm: $("#editForm"),
    editDialog: $("#editDialog"),
    confirmDialog: $("#confirmDialog"),
    reminderDialog: $("#reminderDialog"),
    toast: $("#toast"),
  };

  // ---------- small helpers ----------

  let toastTimer = null;

  function toast(message) {
    ui.toast.textContent = message;
    ui.toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => ui.toast.classList.remove("show"), 2800);
  }

  function persist() {
    if (!saveTasks(state.tasks)) {
      toast("Could not save. Your browser may be blocking storage.");
    }
  }

  function askConfirm(title, text, okLabel) {
    return new Promise((resolve) => {
      $("#confirmTitle").textContent = title;
      $("#confirmText").textContent = text;
      $("#confirmOk").textContent = okLabel;

      ui.confirmDialog.returnValue = "";
      ui.confirmDialog.addEventListener(
        "close",
        () => resolve(ui.confirmDialog.returnValue === "ok"),
        { once: true }
      );
      ui.confirmDialog.showModal();
    });
  }

  // ---------- form fields (shared by "New task" and "Edit task") ----------

  function mountFields(container) {
    container.replaceChildren($("#fieldsTemplate").content.cloneNode(true));
  }

  const field = (form, name) => $(`[name="${name}"]`, form);

  function showError(form, message) {
    $(".form-error", form).textContent = message;
  }

  function fillForm(form, task) {
    field(form, "title").value = task.title;
    field(form, "description").value = task.description;
    field(form, "due").value = toDisplay(task.due_date);
    field(form, "reminder").value = task.reminder_time || "";
    field(form, "end").value = task.end_time || "";
    field(form, "category").value = task.category;
    $(`input[name="priority"][value="${task.priority}"]`, form).checked = true;
    showError(form, "");
  }

  function resetForm(form) {
    field(form, "title").value = "";
    field(form, "description").value = "";
    field(form, "due").value = "";
    field(form, "reminder").value = "";
    field(form, "end").value = "";
    field(form, "category").selectedIndex = 0;
    $('input[name="priority"][value="Medium"]', form).checked = true;
    showError(form, "");
  }

  // Returns the checked form data, or null if something is wrong.
  function readForm(form) {
    const title = field(form, "title").value.trim();
    const due = field(form, "due").value.trim();

    if (!title) {
      showError(form, "Please enter a task title.");
      field(form, "title").focus();
      return null;
    }

    if (!isValidDate(due)) {
      showError(form, "Deadline must look like 24-12-2026.");
      field(form, "due").focus();
      return null;
    }

    const reminder = field(form, "reminder").value.trim();
    const end = field(form, "end").value.trim();

    if (!isValidTime(reminder) || !isValidTime(end)) {
      showError(form, "Times must look like 08:30 (24 hour clock).");
      field(form, !isValidTime(reminder) ? "reminder" : "end").focus();
      return null;
    }

    if ((reminder || end) && !due) {
      showError(form, "Add a deadline date to use a reminder or expiry time.");
      field(form, "due").focus();
      return null;
    }

    showError(form, "");

    return {
      title,
      description: field(form, "description").value.trim(),
      due_date: toStorage(due),
      priority: $('input[name="priority"]:checked', form).value,
      category: field(form, "category").value,
      reminder_time: reminder,
      end_time: end,
    };
  }

  function wireForm(form) {
    // Dashes are added automatically while typing the deadline.
    form.addEventListener("input", (event) => {
      const name = event.target.name;

      // The colon is added automatically while typing a time
      if (name === "reminder" || name === "end") {
        const formatted = formatTimeTyping(event.target.value);
        if (formatted !== event.target.value) event.target.value = formatted;
        return;
      }

      if (name !== "due") return;

      let value = event.target.value;

      // A pasted YYYY-MM-DD date is converted to DD-MM-YYYY.
      if (/^\d{4}-\d{2}-\d{2}$/.test(value)) value = toDisplay(value) || value;

      const formatted = formatDateTyping(value);
      if (formatted !== event.target.value) event.target.value = formatted;
    });

    // Today / Tomorrow / +1 week buttons
    form.addEventListener("click", (event) => {
      const input = field(form, "due");

      // Today / Tomorrow / +1 week count from today
      const jump = event.target.closest("[data-days]");
      if (jump) {
        input.value = shiftDisplayDate("", Number(jump.dataset.days));
        return;
      }

      // -1 day / +1 day move the date that is already typed (or start from today)
      const step = event.target.closest("[data-shift]");
      if (step) {
        input.value = shiftDisplayDate(input.value, Number(step.dataset.shift));
      }
    });

    // The Up and Down arrow keys also change the date by one day
    form.addEventListener("keydown", (event) => {
      if (event.target.name !== "due") return;
      if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;

      event.preventDefault();
      event.target.value = shiftDisplayDate(
        event.target.value,
        event.key === "ArrowUp" ? 1 : -1
      );
    });
  }

  // ---------- drawing the list ----------

  function buildCard(task) {
    const done = task.completed;
    const status = dueStatus(task);

    return el(
      "li",
      { class: `task-card${done ? " done" : ""}`, "data-priority": task.priority, "data-status": status },
      el("div", { class: "stripe" }),

      el(
        "div",
        { class: "task-body" },
        el("h3", { class: "task-title", text: task.title }),
        el(
          "div",
          { class: "chips" },
          done ? null : el("span", { class: "chip chip-priority", "data-p": task.priority, text: task.priority.toUpperCase() }),
          el("span", { class: "chip chip-category", text: task.category }),
          el("span", { class: `due due-${status}`, text: dueLabel(task) }),
          task.reminder_time && !done
            ? el("span", { class: "due", text: `Reminder ${task.reminder_time}` })
            : null
        ),
        task.description ? el("p", { class: "task-desc", text: task.description }) : null
      ),

      el(
        "div",
        { class: "task-actions" },
        el("button", {
          type: "button",
          class: done ? "btn btn-secondary btn-small" : "btn btn-success btn-small",
          "aria-label": `${done ? "Mark as not done" : "Complete"}: ${task.title}`,
          text: done ? "Undo" : "Complete",
          onclick: () => onToggle(task.id),
        }),
        el("button", {
          type: "button",
          class: "btn btn-secondary btn-small",
          "aria-label": `Edit: ${task.title}`,
          text: "Edit",
          onclick: () => openEdit(task),
        }),
        el("button", {
          type: "button",
          class: "btn btn-danger btn-small",
          "aria-label": `Delete: ${task.title}`,
          text: "Delete",
          onclick: () => onDelete(task),
        })
      )
    );
  }

  function statusSignature(now = new Date()) {
    return state.tasks.map((task) => dueStatus(task, now)).join(",");
  }

  function render() {
    state.signature = statusSignature();

    const stats = getStats(state.tasks);

    ui.statTotal.textContent = stats.total;
    ui.statPending.textContent = stats.pending;
    ui.statCompleted.textContent = stats.completed;
    ui.statOverdue.textContent = stats.overdue;

    const percent = stats.total ? Math.round((stats.completed / stats.total) * 100) : 0;
    ui.progressBar.style.width = `${percent}%`;
    ui.progress.setAttribute("aria-valuenow", String(percent));

    if (stats.pending === 0) {
      ui.subtitle.textContent = stats.total
        ? "You're all caught up."
        : "Add your first task to get started.";
    } else if (stats.pending === 1) {
      ui.subtitle.textContent = "1 task left to finish.";
    } else {
      ui.subtitle.textContent = `${stats.pending} tasks left to finish.`;
    }

    let visible = searchTasks(state.tasks, ui.search.value);
    visible = filterTasks(visible, ui.statusFilter.value, ui.categoryFilter.value);
    visible = sortTasks(visible, ui.sortMenu.value);

    ui.countLabel.textContent = `Showing ${visible.length} of ${state.tasks.length} tasks`;

    if (visible.length === 0) {
      ui.taskList.replaceChildren(
        el("li", {
          class: "empty",
          text: state.tasks.length
            ? "No tasks match your search or filters."
            : "Nothing here yet. Add your first task.",
        })
      );
      return;
    }

    ui.taskList.replaceChildren(...visible.map(buildCard));
  }

  // ---------- actions ----------

  function onAdd(event) {
    event.preventDefault();

    const data = readForm(ui.taskForm);
    if (!data) return;

    state.tasks = [...state.tasks, createTask(data)];
    persist();
    askNotificationPermission(data);

    resetForm(ui.taskForm);
    field(ui.taskForm, "title").focus();

    render();
    toast("Task added");
  }

  function onToggle(id) {
    state.tasks = toggleTask(state.tasks, id);
    persist();
    render();
  }

  function openEdit(task) {
    state.editingId = task.id;
    fillForm(ui.editForm, task);
    ui.editDialog.showModal();
    field(ui.editForm, "title").focus();
  }

  function onEditSave(event) {
    event.preventDefault();

    const data = readForm(ui.editForm);
    if (!data) return;

    state.tasks = updateTask(state.tasks, state.editingId, data);
    persist();
    askNotificationPermission(data);

    ui.editDialog.close();
    render();
    toast("Task updated");
  }

  async function onDelete(task) {
    const ok = await askConfirm("Delete task", `Delete "${task.title}"?`, "Delete");
    if (!ok) return;

    state.tasks = deleteTask(state.tasks, task.id);
    persist();
    render();
    toast("Task deleted");
  }

  async function onClearCompleted() {
    const count = state.tasks.filter((t) => t.completed).length;

    if (count === 0) {
      toast("You have no completed tasks.");
      return;
    }

    const ok = await askConfirm(
      "Clear completed",
      `Delete all ${count} completed ${count === 1 ? "task" : "tasks"}?`,
      "Delete"
    );
    if (!ok) return;

    state.tasks = clearCompleted(state.tasks);
    persist();
    render();
  }

  // ---------- reminders ----------

  // Asks the browser for permission to show notifications the first time a reminder is set.
  function askNotificationPermission(data) {
    if (!data.reminder_time) return;
    if (!("Notification" in window) || Notification.permission !== "default") return;

    try { Notification.requestPermission(); } catch (e) { /* not critical */ }
  }

  async function notify(task) {
    if (!("Notification" in window) || Notification.permission !== "granted") return;

    const title = `Reminder: ${task.title}`;
    const options = { body: dueLabel(task), icon: "icon-192.png", tag: task.id };

    try {
      const registration = "serviceWorker" in navigator
        ? await navigator.serviceWorker.getRegistration()
        : null;

      if (registration && registration.showNotification) {
        await registration.showNotification(title, options);
      } else {
        new Notification(title, options);
      }
    } catch (e) { /* not critical */ }
  }

  function showReminders(tasks) {
    const items = tasks.map((task) => el("li", { text: `${task.title} · ${dueLabel(task)}` }));

    if (ui.reminderDialog.open) $("#reminderList").append(...items);
    else $("#reminderList").replaceChildren(...items);

    if (!ui.reminderDialog.open) ui.reminderDialog.showModal();

    tasks.forEach(notify);
  }

  // Runs every 15 seconds while the app is open
  function fireReminders() {
    const now = new Date();
    const due = pendingReminders(state.tasks, now);

    if (due.length > 0) {
      const ids = new Set(due.map((task) => task.id));

      state.tasks = state.tasks.map((task) => (ids.has(task.id) ? { ...task, reminded: true } : task));
      persist();
      render();
      showReminders(due);
    } else if (state.signature !== statusSignature(now)) {
      // A deadline passed or a day changed: update colors and the Overdue count
      render();
    }
  }

  // ---------- export and import ----------

  function onExport() {
    if (state.tasks.length === 0) {
      toast("You have no tasks to export yet.");
      return;
    }

    const now = new Date();
    const stamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;

    const blob = new Blob([JSON.stringify(state.tasks, null, 4)], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const link = el("a", { href: url, download: `tasks-${stamp}.json` });
    document.body.append(link);
    link.click();
    link.remove();

    setTimeout(() => URL.revokeObjectURL(url), 1000);

    toast(`Exported ${state.tasks.length} tasks`);
  }

  async function onImportFile(event) {
    const file = event.target.files[0];
    event.target.value = "";

    if (!file) return;

    try {
      const incoming = parseImport(await file.text());
      const { tasks, added } = mergeTasks(state.tasks, incoming);

      state.tasks = tasks;
      persist();
      render();

      const skipped = incoming.length - added;
      toast(`Added ${added} new ${added === 1 ? "task" : "tasks"}. Skipped ${skipped} already in your list.`);
    } catch (error) {
      toast(error.message || "Could not import that file.");
    }
  }

  // ---------- theme ----------

  function currentTheme() {
    return (
      document.documentElement.dataset.theme ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    );
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    $("#themeBtn").textContent = theme === "dark" ? "Light mode" : "Dark mode";

    try { localStorage.setItem(THEME_KEY, theme); } catch (e) { /* ignore */ }
  }

  // ---------- start ----------

  mountFields($("#newFields"));
  mountFields($("#editFields"));
  wireForm(ui.taskForm);
  wireForm(ui.editForm);

  ui.taskForm.addEventListener("submit", onAdd);
  ui.editForm.addEventListener("submit", onEditSave);
  $("#editCancel").addEventListener("click", () => ui.editDialog.close());

  // Clicking the dark area around a window closes it
  ui.editDialog.addEventListener("click", (event) => {
    if (event.target === ui.editDialog) ui.editDialog.close();
  });
  ui.confirmDialog.addEventListener("click", (event) => {
    if (event.target === ui.confirmDialog) ui.confirmDialog.close("cancel");
  });

  $("#clearBtn").addEventListener("click", onClearCompleted);
  $("#exportBtn").addEventListener("click", onExport);
  $("#importBtn").addEventListener("click", () => $("#importFile").click());
  $("#importFile").addEventListener("change", onImportFile);
  $("#themeBtn").addEventListener("click", () =>
    applyTheme(currentTheme() === "dark" ? "light" : "dark")
  );

  ui.search.addEventListener("input", render);
  [ui.statusFilter, ui.categoryFilter, ui.sortMenu].forEach((menu) =>
    menu.addEventListener("change", render)
  );

  // Keep several open tabs in sync, and refresh "overdue" after midnight
  window.addEventListener("storage", (event) => {
    if (event.key === STORAGE_KEY) {
      state.tasks = loadTasks();
      render();
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      fireReminders();
      render();
    }
  });

  // "Install app" button (shown only when the browser allows installing)
  let installPrompt = null;
  const installBtn = $("#installBtn");

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installPrompt = event;
    installBtn.hidden = false;
  });

  installBtn.addEventListener("click", async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
    installBtn.hidden = true;
  });

  window.addEventListener("appinstalled", () => {
    installBtn.hidden = true;
  });

  // Works offline after the first visit
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    navigator.serviceWorker.register("sw.js").catch(() => { /* not critical */ });
  }

  applyTheme(currentTheme());
  render();

  // Check for reminders now (shows ones missed while the app was closed) and then every 15 seconds
  setTimeout(fireReminders, 800);
  setInterval(fireReminders, 15000);
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startApp);
  } else {
    startApp();
  }
}

// Lets the logic be tested outside a browser
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    parseStoredDate, parseDisplayDate, isValidDate, toDisplay, toStorage,
    formatDateTyping, shiftDisplayDate, parseTime, isValidTime, formatTimeTyping,
    dueDateTime, reminderDateTime, pendingReminders,
    dueStatus, dueLabel, normalizeTask, createTask,
    updateTask, deleteTask, toggleTask, clearCompleted, mergeTasks,
    parseImport, searchTasks, filterTasks, sortTasks, getStats,
  };
}
