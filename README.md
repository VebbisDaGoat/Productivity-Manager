# Productivity Manager

A simple, good-looking task manager. Organize tasks with priorities, categories and deadlines, and stay on top of what's overdue.

It comes in two versions that use the same task file format:

- **Website / installable app** – opens in any browser and can be installed on a computer or phone.
- **Windows desktop app** – a Python program, downloadable as an `.exe`.

## Features

- Add, edit, complete and delete tasks
- Priorities (Low, Medium, High) with colored labels
- Categories: School, Personal, Work, Other
- Deadlines in `DD-MM-YYYY` – the dashes are added automatically as you type
- `-1 day` and `+1 day` buttons (and the Up and Down arrow keys) to change the date quickly
- Optional times of day: **Remind at** (when the reminder appears) and **Expires at** (when the task counts as overdue). Type `0830` and the colon is added for you
- Reminders that pop up on the deadline date at the time you chose
- Overdue and due-today highlighting
- Search, filter by status and category, and sort by deadline, priority or title
- Statistics and a progress bar
- Light and dark mode
- Export and import your tasks as a `.json` file, so you can back them up or move them between devices and between the two versions

## How reminders work

A reminder appears on the task's deadline date at the **Remind at** time. It only appears while the app (or the web page) is open. If the app was closed at that time, the reminder shows up the next time you open it.

- **Desktop app:** a message window pops up.
- **Website:** a pop-up appears in the page, and the browser can also show a notification if you allow notifications when asked. Notifications are not sent while the browser is closed.

If **Expires at** is empty, a task stays on time until the end of its deadline day.

## Use the website

Open the site: **https://vebbisdagoat.github.io/Productivity-Manager/**

To install it as an app:

- **Computer (Chrome or Edge):** click the **Install app** button at the top of the page, or the install icon in the address bar.
- **Android:** open the browser menu and choose **Install app**.
- **iPhone:** tap **Share**, then **Add to Home Screen**.

Your tasks are saved in your own browser on your own device. They are not uploaded anywhere, and they are not shared between devices. Use **Export** and **Import** to move them.

## Download the Windows app

1. Open the **Releases** section on the right side of this page.
2. Download `Productivity Manager.exe` from the latest release.
3. Double-click to run it.

Windows may show "Windows protected your PC" because the app is not signed. Click **More info → Run anyway**.

Tasks are saved in `%APPDATA%\ProductivityManager\tasks.json`.

## Run or build the desktop version from the code

You need Python 3.10 or newer.

```
pip install customtkinter
python main.py
```

To build the `.exe`:

```
pip install pyinstaller
pyinstaller --noconsole --onefile --name "Productivity Manager" --icon icon.ico --collect-all customtkinter main.py
```

The result is in the `dist` folder.

## Project files

| File | What it does |
| --- | --- |
| `main.py` | The desktop window and design |
| `task_manager.py` | Task logic: dates, sorting, filtering, statistics |
| `storage.py` | Saving, loading, export and import |
| `docs/` | The website version (`index.html`, `style.css`, `app.js` and the files that make it installable) |

## Backup and moving tasks

Use **Export** to save a `tasks-DATE.json` file and **Import** to load it again. Importing never overwrites or deletes your existing tasks; it only adds tasks that aren't already in your list.
