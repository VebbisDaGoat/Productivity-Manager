import json
import os
import sys
import uuid
from pathlib import Path

from task_manager import PRIORITIES, CATEGORIES

APP_FOLDER_NAME = "ProductivityManager"


def _data_dir():
    """A per-user folder that survives updates and works inside a packaged app."""

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    folder = base / APP_FOLDER_NAME
    folder.mkdir(parents=True, exist_ok=True)

    return folder


FILE = _data_dir() / "tasks.json"

# Old location (next to the script). It is read once if the new file does not exist yet.
LEGACY_FILE = Path(__file__).with_name("tasks.json")


def _normalize(raw):
    """Make sure every task has all fields, so old files never crash the app."""

    if not isinstance(raw, dict):
        return None

    title = str(raw.get("title", "")).strip()

    if not title:
        return None

    priority = raw.get("priority")
    category = raw.get("category")

    return {
        "id": str(raw.get("id") or uuid.uuid4()),
        "title": title,
        "description": str(raw.get("description", "") or ""),
        "due_date": str(raw.get("due_date", "") or ""),
        "priority": priority if priority in PRIORITIES else "Medium",
        "category": category if category in CATEGORIES else "Other",
        "completed": bool(raw.get("completed", False)),
    }


def load_tasks():

    if FILE.exists():
        source = FILE
    elif LEGACY_FILE.exists():
        source = LEGACY_FILE
    else:
        return []

    try:
        with open(source, "r", encoding="utf-8") as file:
            data = json.load(file)

    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(data, list):
        return []

    tasks = (_normalize(item) for item in data)

    return [task for task in tasks if task is not None]


def export_tasks(tasks, path):
    """Save a copy of all tasks to a file the person chose."""

    with open(path, "w", encoding="utf-8") as file:
        json.dump(tasks, file, indent=4, ensure_ascii=False)


def read_import_file(path):
    """Read tasks from a backup file. Raises ValueError with a friendly message."""

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
        raise ValueError("That file could not be read as a task list.") from error

    if not isinstance(data, list):
        raise ValueError("That file does not look like a task backup.")

    tasks = [_normalize(item) for item in data]
    tasks = [task for task in tasks if task is not None]

    if not tasks:
        raise ValueError("No tasks were found in that file.")

    return tasks


def save_tasks(tasks):
    """Write to a temporary file first, so a crash can never corrupt tasks.json."""

    temp_file = FILE.with_name(FILE.name + ".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(tasks, file, indent=4, ensure_ascii=False)

    os.replace(temp_file, FILE)
