import uuid
from datetime import date, datetime, timedelta

PRIORITIES = ["Low", "Medium", "High"]
CATEGORIES = ["School", "Personal", "Work", "Other"]
SORT_MODES = ["Deadline", "Priority", "Title (A-Z)"]

PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
DATE_FORMAT = "%Y-%m-%d"          # how dates are stored in tasks.json
DISPLAY_FORMAT = "%d-%m-%Y"       # how dates are typed and shown in the app
TIME_FORMAT = "%H:%M"             # times are stored and shown the same way


# -------------------------
# DATES
# -------------------------

def parse_date(text):
    """Return a date object, or None if the text is empty or invalid."""
    try:
        return datetime.strptime(text.strip(), DATE_FORMAT).date()
    except (ValueError, AttributeError):
        return None


def parse_display_date(text):
    """Parse a typed DD-MM-YYYY date. Returns None if it is incomplete or invalid."""
    text = (text or "").strip()

    if len(text) != 10:
        return None

    try:
        return datetime.strptime(text, DISPLAY_FORMAT).date()
    except ValueError:
        return None


def is_valid_date(text):
    """An empty deadline is allowed. Anything else must be DD-MM-YYYY."""
    text = (text or "").strip()
    return text == "" or parse_display_date(text) is not None


def to_display(stored_text):
    """Stored date (YYYY-MM-DD) -> text shown in the app (DD-MM-YYYY)."""
    due = parse_date(stored_text)
    return due.strftime(DISPLAY_FORMAT) if due else ""


def to_storage(display_text):
    """Typed date (DD-MM-YYYY) -> stored date (YYYY-MM-DD)."""
    due = parse_display_date(display_text)
    return due.strftime(DATE_FORMAT) if due else ""


def format_date_typing(text):
    """Keep only digits and insert the dashes automatically: 24122026 -> 24-12-2026."""
    digits = "".join(ch for ch in (text or "") if ch.isdigit())[:8]
    parts = [digits[:2], digits[2:4], digits[4:]]
    return "-".join(part for part in parts if part)


def shift_display_date(text, days):
    """Move a typed DD-MM-YYYY date by some days. An empty or unfinished date starts from today."""
    base = parse_display_date(text) or date.today()
    return (base + timedelta(days=days)).strftime(DISPLAY_FORMAT)


# -------------------------
# TIMES OF DAY (HH:MM, 24 hour clock)
# -------------------------

def parse_time(text):
    """Return a datetime.time, or None if the text is empty or not exactly HH:MM."""
    text = (text or "").strip()

    if len(text) != 5:
        return None

    try:
        return datetime.strptime(text, TIME_FORMAT).time()
    except ValueError:
        return None


def is_valid_time(text):
    """A time is optional. If it is filled in, it must be HH:MM."""
    text = (text or "").strip()
    return text == "" or parse_time(text) is not None


def format_time_typing(text):
    """Keep only digits and add the colon: 0830 -> 08:30. Typing 8 gives 08."""
    digits = "".join(ch for ch in (text or "") if ch.isdigit())

    if digits and digits[0] > "2":
        digits = "0" + digits

    if len(digits) >= 3 and digits[2] > "5":
        digits = digits[:2] + "0" + digits[2:]

    digits = digits[:4]

    if len(digits) > 2:
        return digits[:2] + ":" + digits[2:]

    return digits


# -------------------------
# DEADLINES AND REMINDERS
# -------------------------

def days_until_due(task):
    due = parse_date(task["due_date"])
    if due is None:
        return None
    return (due - date.today()).days


def due_datetime(task):
    """The moment a task expires. Without an 'expires at' time, that is the end of the day."""
    due = parse_date(task["due_date"])

    if due is None:
        return None

    at = parse_time(task.get("end_time", ""))

    if at is None:
        return datetime.combine(due, datetime.max.time().replace(microsecond=0))

    return datetime.combine(due, at)


def reminder_datetime(task):
    """When the reminder should appear, or None if no reminder is set."""
    due = parse_date(task["due_date"])
    at = parse_time(task.get("reminder_time", ""))

    if due is None or at is None:
        return None

    return datetime.combine(due, at)


def pending_reminders(tasks, now=None):
    """Tasks whose reminder time has arrived and that were not reminded yet."""
    now = now or datetime.now()

    result = []

    for task in tasks:
        if task["completed"] or task.get("reminded"):
            continue

        when = reminder_datetime(task)

        if when is not None and now >= when:
            result.append(task)

    return result


def due_status(task, now=None):
    """One of: done, none, overdue, today, soon, later."""
    now = now or datetime.now()

    if task["completed"]:
        return "done"

    due = due_datetime(task)

    if due is None:
        return "none"
    if now > due:
        return "overdue"

    days = (due.date() - now.date()).days

    if days == 0:
        return "today"
    if days <= 3:
        return "soon"
    return "later"


def due_label(task, now=None):
    """Human friendly deadline text for the task card."""
    now = now or datetime.now()

    due = due_datetime(task)

    if due is None:
        return "No deadline"

    pretty = to_display(task["due_date"])
    end = (task.get("end_time") or "").strip()
    at = f" at {end}" if parse_time(end) else ""

    if task["completed"]:
        return f"Due {pretty}{at}"

    days = (due.date() - now.date()).days

    if now > due:
        if days == 0:
            return f"Expired today{at}  ·  {pretty}"

        over = -days
        unit = "day" if over == 1 else "days"
        return f"Overdue by {over} {unit}  ·  {pretty}{at}"

    if days == 0:
        return f"Due today{at}  ·  {pretty}"
    if days == 1:
        return f"Due tomorrow{at}  ·  {pretty}"
    return f"Due in {days} days  ·  {pretty}{at}"


# -------------------------
# CREATE / UPDATE / DELETE
# -------------------------

def create_task(title, description, due_date, priority, category,
                reminder_time="", end_time=""):

    task = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "due_date": due_date,
        "priority": priority,
        "category": category,
        "completed": False,
        "reminder_time": reminder_time,
        "end_time": end_time,
        "reminded": False
    }

    return task


def update_task(tasks, task_id, **changes):

    allowed = {
        "title", "description", "due_date", "priority", "category",
        "reminder_time", "end_time"
    }

    # Changing the date or the reminder time means the reminder should appear again
    watched = {"due_date", "reminder_time"}

    for task in tasks:
        if task["id"] == task_id:
            for key, value in changes.items():
                if key in allowed:
                    if key in watched and task.get(key) != value:
                        task["reminded"] = False
                    task[key] = value

    return tasks


def delete_task(tasks, task_id):

    return [
        task for task in tasks
        if task["id"] != task_id
    ]


def toggle_task(tasks, task_id):

    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = not task["completed"]

    return tasks


def clear_completed(tasks):

    return [task for task in tasks if not task["completed"]]


def merge_tasks(existing, incoming):
    """Add imported tasks that are not already in the list (matched by id).

    Returns (merged_list, number_added). Nothing existing is changed or removed.
    """

    known_ids = {task["id"] for task in existing}
    new_tasks = [task for task in incoming if task["id"] not in known_ids]

    return existing + new_tasks, len(new_tasks)


# -------------------------
# SEARCH, FILTER, SORT
# -------------------------

def search_tasks(tasks, query):

    query = query.strip().lower()

    if not query:
        return list(tasks)

    return [
        task for task in tasks
        if query in task["title"].lower()
        or query in task["description"].lower()
    ]


def filter_tasks(tasks, status="All", category="All"):

    result = tasks

    if status == "Completed":
        result = [task for task in result if task["completed"]]
    elif status == "Pending":
        result = [task for task in result if not task["completed"]]

    if category != "All":
        result = [task for task in result if task["category"] == category]

    return list(result)


def _date_key(task):
    return due_datetime(task) or datetime.max


def sort_tasks(tasks, mode="Deadline"):
    """Pending tasks always come before completed ones."""

    if mode == "Priority":
        def key(task):
            return (
                task["completed"],
                PRIORITY_ORDER.get(task["priority"], 1),
                _date_key(task),
            )

    elif mode == "Title (A-Z)":
        def key(task):
            return (task["completed"], task["title"].lower())

    else:
        def key(task):
            return (
                task["completed"],
                _date_key(task),
                PRIORITY_ORDER.get(task["priority"], 1),
            )

    return sorted(tasks, key=key)


# -------------------------
# STATISTICS
# -------------------------

def get_stats(tasks, now=None):

    total = len(tasks)
    completed = sum(1 for task in tasks if task["completed"])
    overdue = sum(1 for task in tasks if due_status(task, now) == "overdue")

    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "overdue": overdue,
    }
