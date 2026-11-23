import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import date, timedelta

import task_manager as tm
from storage import load_tasks, save_tasks, export_tasks, read_import_file


# -------------------------
# DESIGN SETTINGS
# -------------------------

FONT = "Segoe UI"

ACCENT = "#4F46E5"
ACCENT_HOVER = "#4338CA"
SUCCESS = "#16A34A"
SUCCESS_HOVER = "#15803D"
DANGER = "#DC2626"
DANGER_HOVER = "#B91C1C"

# Colors given as (light mode, dark mode)
APP_BG = ("#F3F4F6", "#18181B")
CARD_BG = ("#FFFFFF", "#27272A")
BORDER = ("#E5E7EB", "#3F3F46")
MUTED = ("#6B7280", "#A1A1AA")
CHIP_BG = ("#E5E7EB", "#3F3F46")
CHIP_TEXT = ("#374151", "#E4E4E7")
SECONDARY_BTN = ("#E5E7EB", "#3F3F46")
SECONDARY_HOVER = ("#D1D5DB", "#52525B")
SECONDARY_TEXT = ("#111827", "#F4F4F5")

PRIORITY_COLORS = {
    "High": "#DC2626",
    "Medium": "#F59E0B",
    "Low": "#16A34A",
}

STATUS_COLORS = {
    "overdue": "#DC2626",
    "today": "#D97706",
    "soon": "#2563EB",
    "later": MUTED,
    "none": MUTED,
    "done": MUTED,
}


# -------------------------
# REUSABLE TASK FORM FIELDS
# (used by the sidebar and the edit window)
# -------------------------

class TaskFields(ctk.CTkFrame):

    def __init__(self, parent, task=None):
        super().__init__(parent, fg_color="transparent")

        self.title_entry = ctk.CTkEntry(
            self,
            placeholder_text="Task title...",
            height=38
        )
        self.title_entry.pack(fill="x", pady=(0, 8))

        self.description_box = ctk.CTkTextbox(
            self,
            height=80,
            border_width=2,
            border_color=BORDER
        )
        self.description_box.pack(fill="x", pady=(0, 8))

        # Deadline row
        self.date_entry = ctk.CTkEntry(
            self,
            placeholder_text="Deadline (DD-MM-YYYY)",
            height=38
        )
        self.date_entry.pack(fill="x")

        # Dashes are added automatically while typing
        self.date_entry.bind("<KeyRelease>", self._auto_format_date)

        quick = ctk.CTkFrame(self, fg_color="transparent")
        quick.pack(fill="x", pady=(6, 8))

        for label, days in (("Today", 0), ("Tomorrow", 1), ("+1 week", 7)):
            ctk.CTkButton(
                quick,
                text=label,
                width=70,
                height=26,
                font=ctk.CTkFont(FONT, 12),
                fg_color=SECONDARY_BTN,
                hover_color=SECONDARY_HOVER,
                text_color=SECONDARY_TEXT,
                command=lambda d=days: self._set_date(d)
            ).pack(side="left", padx=(0, 6))

        # Priority
        ctk.CTkLabel(
            self,
            text="Priority",
            font=ctk.CTkFont(FONT, 12, "bold"),
            text_color=MUTED
        ).pack(anchor="w")

        self.priority = ctk.CTkSegmentedButton(
            self,
            values=tm.PRIORITIES,
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER
        )
        self.priority.pack(fill="x", pady=(2, 8))
        self.priority.set("Medium")

        # Category
        ctk.CTkLabel(
            self,
            text="Category",
            font=ctk.CTkFont(FONT, 12, "bold"),
            text_color=MUTED
        ).pack(anchor="w")

        self.category = ctk.CTkOptionMenu(
            self,
            values=tm.CATEGORIES,
            fg_color=ACCENT,
            button_color=ACCENT_HOVER,
            button_hover_color=ACCENT_HOVER
        )
        self.category.pack(fill="x", pady=(2, 8))

        # Inline error message
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            text_color=DANGER,
            font=ctk.CTkFont(FONT, 12),
            wraplength=280,
            justify="left"
        )
        self.error_label.pack(anchor="w")

        if task:
            self.load(task)

    def _auto_format_date(self, event=None):
        current = self.date_entry.get()
        formatted = tm.format_date_typing(current)

        if formatted != current:
            self.date_entry.delete(0, "end")

            if formatted:
                self.date_entry.insert(0, formatted)
                self.date_entry.icursor("end")

    def _set_date(self, days):
        self.date_entry.delete(0, "end")
        self.date_entry.insert(
            0,
            (date.today() + timedelta(days=days)).strftime(tm.DISPLAY_FORMAT)
        )

    def load(self, task):
        self.title_entry.insert(0, task["title"])
        self.description_box.insert("1.0", task["description"])
        self.date_entry.insert(0, tm.to_display(task["due_date"]))
        self.priority.set(task["priority"])
        self.category.set(task["category"])

    def show_error(self, message):
        self.error_label.configure(text=message)

    def values(self):
        """Return the validated form data, or None if something is wrong."""

        title = self.title_entry.get().strip()
        due = self.date_entry.get().strip()

        if not title:
            self.show_error("Please enter a task title.")
            return None

        if not tm.is_valid_date(due):
            self.show_error("Deadline must look like 24-12-2026.")
            return None

        self.show_error("")

        return {
            "title": title,
            "description": self.description_box.get("1.0", "end").strip(),
            "due_date": tm.to_storage(due),
            "priority": self.priority.get(),
            "category": self.category.get(),
        }

    def clear(self):
        self.title_entry.delete(0, "end")
        self.description_box.delete("1.0", "end")
        self.date_entry.delete(0, "end")
        self.priority.set("Medium")
        self.show_error("")


# -------------------------
# EDIT WINDOW
# -------------------------

class EditDialog(ctk.CTkToplevel):

    def __init__(self, parent, task, on_save):
        super().__init__(parent)

        self.on_save = on_save

        self.title("Edit task")
        self.geometry("420x590")
        self.resizable(False, False)
        self.configure(fg_color=APP_BG)
        self.transient(parent)

        ctk.CTkLabel(
            self,
            text="Edit task",
            font=ctk.CTkFont(FONT, 20, "bold")
        ).pack(anchor="w", padx=24, pady=(22, 10))

        self.fields = TaskFields(self, task)
        self.fields.pack(fill="x", padx=24)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=(10, 20))

        ctk.CTkButton(
            buttons,
            text="Save changes",
            height=38,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=self.save
        ).pack(side="right")

        ctk.CTkButton(
            buttons,
            text="Cancel",
            height=38,
            width=90,
            fg_color=SECONDARY_BTN,
            hover_color=SECONDARY_HOVER,
            text_color=SECONDARY_TEXT,
            command=self.destroy
        ).pack(side="right", padx=(0, 10))

        # The window must be visible before it can grab focus
        self.after(150, self._focus_window)

    def _focus_window(self):
        try:
            self.lift()
            self.focus()
            self.grab_set()
        except Exception:
            pass

    def save(self):
        changes = self.fields.values()

        if changes is None:
            return

        self.on_save(changes)
        self.destroy()


# -------------------------
# MAIN APPLICATION
# -------------------------

class TaskApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("Productivity Manager")
        self.geometry("1100x780")
        self.minsize(900, 640)
        self.configure(fg_color=APP_BG)

        self.tasks = load_tasks()

        self._build_header()
        self._build_stats()
        self._build_body()

        self.refresh()

    # ---------- layout ----------

    def _build_header(self):

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(24, 6))

        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.pack(side="left")

        ctk.CTkLabel(
            titles,
            text="My Productivity",
            font=ctk.CTkFont(FONT, 30, "bold")
        ).pack(anchor="w")

        self.subtitle = ctk.CTkLabel(
            titles,
            text="",
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 13)
        )
        self.subtitle.pack(anchor="w")

        self.theme_switch = ctk.CTkSwitch(
            header,
            text="Dark mode",
            progress_color=ACCENT,
            command=self.toggle_theme
        )
        self.theme_switch.pack(side="right")

        for label, command in (
            ("Import", self.import_from_file),
            ("Export", self.export_to_file),
        ):
            ctk.CTkButton(
                header,
                text=label,
                width=76,
                height=32,
                fg_color=SECONDARY_BTN,
                hover_color=SECONDARY_HOVER,
                text_color=SECONDARY_TEXT,
                command=command
            ).pack(side="right", padx=(0, 14))

    def _build_stats(self):

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=30, pady=(10, 4))

        self.stat_values = {}

        cards = (
            ("total", "Total", ACCENT),
            ("pending", "Pending", "#2563EB"),
            ("completed", "Completed", SUCCESS),
            ("overdue", "Overdue", DANGER),
        )

        for column, (key, caption, color) in enumerate(cards):
            stats.grid_columnconfigure(column, weight=1, uniform="stats")

            card = ctk.CTkFrame(
                stats,
                corner_radius=12,
                fg_color=CARD_BG,
                border_width=1,
                border_color=BORDER
            )
            card.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 8, 0)
            )

            value = ctk.CTkLabel(
                card,
                text="0",
                text_color=color,
                font=ctk.CTkFont(FONT, 28, "bold")
            )
            value.pack(anchor="w", padx=16, pady=(10, 0))

            ctk.CTkLabel(
                card,
                text=caption,
                text_color=MUTED,
                font=ctk.CTkFont(FONT, 12)
            ).pack(anchor="w", padx=16, pady=(0, 10))

            self.stat_values[key] = value

        self.progress = ctk.CTkProgressBar(
            self,
            height=8,
            progress_color=SUCCESS
        )
        self.progress.pack(fill="x", padx=30, pady=(10, 0))
        self.progress.set(0)

    def _build_body(self):

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=(14, 24))

        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._build_sidebar(body)
        self._build_main_panel(body)

    def _build_sidebar(self, parent):

        sidebar = ctk.CTkFrame(
            parent,
            width=320,
            corner_radius=14,
            fg_color=CARD_BG,
            border_width=1,
            border_color=BORDER
        )
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="New task",
            font=ctk.CTkFont(FONT, 20, "bold")
        ).pack(anchor="w", padx=18, pady=(18, 10))

        self.fields = TaskFields(sidebar)
        self.fields.pack(fill="x", padx=18)

        ctk.CTkButton(
            sidebar,
            text="Add task",
            height=40,
            font=ctk.CTkFont(FONT, 14, "bold"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=self.add_task
        ).pack(fill="x", padx=18, pady=(4, 8))

        ctk.CTkButton(
            sidebar,
            text="Clear completed",
            height=34,
            fg_color=SECONDARY_BTN,
            hover_color=SECONDARY_HOVER,
            text_color=SECONDARY_TEXT,
            command=self.clear_completed
        ).pack(fill="x", padx=18, pady=(0, 18))

        # Press Enter in the title field to add the task
        self.fields.title_entry.bind("<Return>", lambda event: self.add_task())

    def _build_main_panel(self, parent):

        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid(row=0, column=1, sticky="nsew")

        controls = ctk.CTkFrame(panel, fg_color="transparent")
        controls.pack(fill="x")
        controls.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            controls,
            placeholder_text="Search title or description...",
            height=38
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda event: self.refresh())

        self.status_filter = self._make_menu(
            controls, ["All", "Pending", "Completed"], 1
        )
        self.category_filter = self._make_menu(
            controls, ["All"] + tm.CATEGORIES, 2
        )
        self.sort_menu = self._make_menu(controls, tm.SORT_MODES, 3)

        self.count_label = ctk.CTkLabel(
            panel,
            text="",
            text_color=MUTED,
            font=ctk.CTkFont(FONT, 12)
        )
        self.count_label.pack(anchor="w", pady=(10, 0))

        self.task_list = ctk.CTkScrollableFrame(
            panel,
            fg_color="transparent"
        )
        self.task_list.pack(fill="both", expand=True, pady=(4, 0))

    def _make_menu(self, parent, values, column):

        menu = ctk.CTkOptionMenu(
            parent,
            values=values,
            width=120,
            height=38,
            fg_color=SECONDARY_BTN,
            button_color=SECONDARY_HOVER,
            button_hover_color=SECONDARY_HOVER,
            text_color=SECONDARY_TEXT,
            command=lambda value: self.refresh()
        )
        menu.grid(row=0, column=column, padx=(0, 8) if column < 3 else 0)

        return menu

    # ---------- task cards ----------

    def _chip(self, parent, text, background, text_color="white"):

        return ctk.CTkLabel(
            parent,
            text=f"  {text}  ",
            fg_color=background,
            text_color=text_color,
            corner_radius=8,
            height=22,
            font=ctk.CTkFont(FONT, 11, "bold")
        )

    def _build_card(self, task):

        done = task["completed"]
        status = tm.due_status(task)

        card = ctk.CTkFrame(
            self.task_list,
            corner_radius=12,
            fg_color=CARD_BG,
            border_width=1,
            border_color=BORDER
        )
        card.pack(fill="x", padx=2, pady=6)
        card.grid_columnconfigure(1, weight=1)

        # Colored stripe on the left shows the priority
        ctk.CTkFrame(
            card,
            width=6,
            corner_radius=3,
            fg_color=MUTED if done else PRIORITY_COLORS[task["priority"]]
        ).grid(row=0, column=0, sticky="ns", padx=(10, 0), pady=12)

        # Main content
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=0, column=1, sticky="ew", padx=12, pady=10)

        ctk.CTkLabel(
            body,
            text=task["title"],
            anchor="w",
            font=ctk.CTkFont(FONT, 16, "bold", overstrike=done),
            text_color=MUTED if done else ("#111827", "#F4F4F5")
        ).pack(anchor="w")

        chips = ctk.CTkFrame(body, fg_color="transparent")
        chips.pack(anchor="w", pady=(4, 0))

        if not done:
            self._chip(
                chips,
                task["priority"].upper(),
                PRIORITY_COLORS[task["priority"]]
            ).pack(side="left", padx=(0, 6))

        self._chip(
            chips,
            task["category"],
            CHIP_BG,
            CHIP_TEXT
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            chips,
            text=tm.due_label(task),
            text_color=STATUS_COLORS[status],
            font=ctk.CTkFont(
                FONT, 12, "bold" if status in ("overdue", "today") else "normal"
            )
        ).pack(side="left")

        if task["description"]:
            ctk.CTkLabel(
                body,
                text=task["description"],
                text_color=MUTED,
                wraplength=430,
                justify="left",
                anchor="w",
                font=ctk.CTkFont(FONT, 13)
            ).pack(anchor="w", pady=(6, 0))

        # Buttons
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=0, column=2, padx=(0, 12))

        if done:
            ctk.CTkButton(
                actions,
                text="Undo",
                width=88,
                height=30,
                fg_color=SECONDARY_BTN,
                hover_color=SECONDARY_HOVER,
                text_color=SECONDARY_TEXT,
                command=lambda t=task: self.toggle(t)
            ).pack(pady=3)
        else:
            ctk.CTkButton(
                actions,
                text="Complete",
                width=88,
                height=30,
                fg_color=SUCCESS,
                hover_color=SUCCESS_HOVER,
                command=lambda t=task: self.toggle(t)
            ).pack(pady=3)

        ctk.CTkButton(
            actions,
            text="Edit",
            width=88,
            height=30,
            fg_color=SECONDARY_BTN,
            hover_color=SECONDARY_HOVER,
            text_color=SECONDARY_TEXT,
            command=lambda t=task: self.edit_task(t)
        ).pack(pady=3)

        ctk.CTkButton(
            actions,
            text="Delete",
            width=88,
            height=30,
            fg_color=DANGER,
            hover_color=DANGER_HOVER,
            command=lambda t=task: self.remove_task(t)
        ).pack(pady=3)

    # ---------- refresh ----------

    def refresh(self):

        for widget in self.task_list.winfo_children():
            widget.destroy()

        stats = tm.get_stats(self.tasks)

        for key, label in self.stat_values.items():
            label.configure(text=str(stats[key]))

        if stats["total"]:
            self.progress.set(stats["completed"] / stats["total"])
        else:
            self.progress.set(0)

        if stats["pending"] == 0:
            self.subtitle.configure(
                text="You're all caught up." if stats["total"]
                else "Add your first task to get started."
            )
        elif stats["pending"] == 1:
            self.subtitle.configure(text="1 task left to finish.")
        else:
            self.subtitle.configure(
                text=f"{stats['pending']} tasks left to finish."
            )

        visible = tm.search_tasks(self.tasks, self.search_entry.get())
        visible = tm.filter_tasks(
            visible,
            self.status_filter.get(),
            self.category_filter.get()
        )
        visible = tm.sort_tasks(visible, self.sort_menu.get())

        self.count_label.configure(
            text=f"Showing {len(visible)} of {len(self.tasks)} tasks"
        )

        if not visible:
            message = (
                "Nothing here yet. Add your first task on the left."
                if not self.tasks
                else "No tasks match your search or filters."
            )

            ctk.CTkLabel(
                self.task_list,
                text=message,
                text_color=MUTED,
                font=ctk.CTkFont(FONT, 14)
            ).pack(pady=50)

            return

        for task in visible:
            self._build_card(task)

    # ---------- actions ----------

    def _persist(self):

        try:
            save_tasks(self.tasks)
        except OSError as error:
            messagebox.showerror(
                "Could not save",
                f"Your tasks could not be saved:\n{error}"
            )

    def add_task(self):

        data = self.fields.values()

        if data is None:
            return

        task = tm.create_task(
            data["title"],
            data["description"],
            data["due_date"],
            data["priority"],
            data["category"]
        )

        self.tasks.append(task)
        self._persist()

        self.fields.clear()
        self.fields.title_entry.focus()

        self.refresh()

    def toggle(self, task):

        tm.toggle_task(self.tasks, task["id"])
        self._persist()
        self.refresh()

    def edit_task(self, task):

        EditDialog(
            self,
            task,
            lambda changes: self._apply_edit(task["id"], changes)
        )

    def _apply_edit(self, task_id, changes):

        tm.update_task(self.tasks, task_id, **changes)
        self._persist()
        self.refresh()

    def remove_task(self, task):

        confirm = messagebox.askyesno(
            "Delete task",
            f'Are you sure you want to delete "{task["title"]}"?'
        )

        if not confirm:
            return

        self.tasks[:] = tm.delete_task(self.tasks, task["id"])
        self._persist()
        self.refresh()

    def clear_completed(self):

        count = sum(1 for task in self.tasks if task["completed"])

        if count == 0:
            messagebox.showinfo(
                "Nothing to clear",
                "You have no completed tasks."
            )
            return

        confirm = messagebox.askyesno(
            "Clear completed",
            f"Delete all {count} completed tasks?"
        )

        if not confirm:
            return

        self.tasks[:] = tm.clear_completed(self.tasks)
        self._persist()
        self.refresh()

    def export_to_file(self):

        if not self.tasks:
            messagebox.showinfo("Nothing to export", "You have no tasks yet.")
            return

        path = filedialog.asksaveasfilename(
            title="Export tasks",
            defaultextension=".json",
            initialfile=f"tasks-{date.today().isoformat()}.json",
            filetypes=[("Task backup", "*.json")]
        )

        if not path:
            return

        try:
            export_tasks(self.tasks, path)
        except OSError as error:
            messagebox.showerror(
                "Could not export",
                f"The file could not be saved:\n{error}"
            )
            return

        messagebox.showinfo(
            "Exported",
            f"Saved {len(self.tasks)} tasks to:\n{path}"
        )

    def import_from_file(self):

        path = filedialog.askopenfilename(
            title="Import tasks",
            filetypes=[("Task backup", "*.json"), ("All files", "*.*")]
        )

        if not path:
            return

        try:
            incoming = read_import_file(path)
        except ValueError as error:
            messagebox.showerror("Could not import", str(error))
            return

        merged, added = tm.merge_tasks(self.tasks, incoming)

        self.tasks[:] = merged
        self._persist()
        self.refresh()

        skipped = len(incoming) - added

        messagebox.showinfo(
            "Import finished",
            f"Added {added} new tasks.\n"
            f"Skipped {skipped} that were already in your list."
        )

    def toggle_theme(self):

        ctk.set_appearance_mode(
            "dark" if self.theme_switch.get() else "light"
        )


# -------------------------
# START APPLICATION
# -------------------------

if __name__ == "__main__":
    TaskApp().mainloop()
