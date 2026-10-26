#!/usr/bin/env python3
import subprocess
import os
import sys
import re
import json
import threading
import datetime
from pathlib import Path
from textual.app import App, ComposeResult
from textual import on
from textual.widgets import Header, Footer, DataTable, Static, Input, Button, Label
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.command import Provider, Hit, DiscoveryHit
from textual.theme import Theme
from rich.text import Text
import cron_descriptor

aim_theme = Theme(
    name="aim-dark",
    primary="#00ffff", 
    secondary="#0088ff",
    accent="#00ffff",
    foreground="#ffffff",
    background="#121212",
    surface="#1e1e1e",
    panel="#2e2e2e",
    dark=True,
)

class HelpModal(ModalScreen):
    """Modal dialog to show help instructions."""
    CSS = """
    HelpModal {
        align: center middle;
        background: $background 50%;
    }
    #help-dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $primary;
    }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Label("[bold cyan]Panel Resizing Guide[/bold cyan]\n")
            yield Label("You can dynamically resize the split panes using your keyboard:")
            yield Label("• Press [bold][[/bold] to shrink the left panel by 5%.")
            yield Label("• Press [bold]][/bold] to expand the left panel by 5%.\n")
            yield Label("Alternatively, press [bold]ctrl+p[/bold] and search for 'Layout' to select a preset split (50/50, 60/40, etc).")
            yield Button("Got it", variant="primary", id="btn-ok")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def action_cancel(self) -> None:
        self.dismiss()

class CronManager:
    """Wrapper for crontab commands."""

    SPECIAL_SCHEDULES = {
        "@reboot": "At system startup (reboot)",
        "@hourly": "Every hour (at minute 0)",
        "@midnight": "Every day at midnight (00:00)",
        "@daily": "Every day at midnight (00:00)",
        "@weekly": "Every Sunday at midnight (00:00)",
        "@monthly": "On day 1 of the month at midnight",
        "@yearly": "On January 1 at midnight",
        "@annually": "On January 1 at midnight",
    }

    MONTH_NAMES = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    }

    DOW_NAMES = {
        "SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6,
    }

    ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*=")

    @classmethod
    def _parse_field_value(cls, token: str, min_val: int, max_val: int, names: dict[str, int] | None) -> int | None:
        upper = token.upper()
        if names and upper in names:
            return names[upper]
        if re.fullmatch(r"\d+", token):
            val = int(token)
            if min_val <= val <= max_val:
                return val
        return None

    @classmethod
    def _validate_cron_field(cls, field: str, min_val: int, max_val: int, names: dict[str, int] | None = None) -> bool:
        if not field:
            return False
        for part in field.split(","):
            if not part:
                return False
            if "/" in part:
                range_part, step_part = part.split("/", 1)
                if not re.fullmatch(r"\d+", step_part):
                    return False
                step = int(step_part)
                if step <= 0 or step > (max_val - min_val + 1):
                    return False
            else:
                range_part = part

            if range_part == "*":
                continue
            elif "-" in range_part:
                bounds = range_part.split("-", 1)
                if len(bounds) != 2:
                    return False
                start = cls._parse_field_value(bounds[0], min_val, max_val, names)
                end = cls._parse_field_value(bounds[1], min_val, max_val, names)
                if start is None or end is None or start > end:
                    return False
            else:
                val = cls._parse_field_value(range_part, min_val, max_val, names)
                if val is None:
                    return False
        return True

    @classmethod
    def validate_schedule(cls, schedule: str) -> tuple[bool, str]:
        """Validates a 5-field cron schedule or @shortcut nickname."""
        sched = schedule.strip()
        if not sched:
            return False, "Schedule cannot be empty."

        if sched.startswith("@"):
            if sched.lower() in cls.SPECIAL_SCHEDULES:
                return True, ""
            valid_shortcuts = ", ".join(cls.SPECIAL_SCHEDULES.keys())
            return False, f"Unknown shortcut '{sched}'. Valid shortcuts: {valid_shortcuts}"

        fields = sched.split()
        if len(fields) != 5:
            return False, f"Cron schedule must have 5 fields (minute hour day month weekday) or a valid @shortcut, got {len(fields)}."

        specs = [
            ("minute (0-59)", fields[0], 0, 59, None),
            ("hour (0-23)", fields[1], 0, 23, None),
            ("day of month (1-31)", fields[2], 1, 31, None),
            ("month (1-12 or JAN-DEC)", fields[3], 1, 12, cls.MONTH_NAMES),
            ("day of week (0-7 or SUN-SAT)", fields[4], 0, 7, cls.DOW_NAMES),
        ]
        for label, value, min_v, max_v, name_map in specs:
            if not cls._validate_cron_field(value, min_v, max_v, name_map):
                return False, f"Invalid {label} field: '{value}'."

        return True, ""

    @classmethod
    def describe_schedule(cls, schedule: str) -> str:
        sched = schedule.strip()
        if sched.lower() in cls.SPECIAL_SCHEDULES:
            return cls.SPECIAL_SCHEDULES[sched.lower()]
        try:
            return cron_descriptor.get_description(sched)
        except Exception:
            return sched

    @classmethod
    def _parse_cron_line(cls, active_line: str) -> tuple[str, str] | None:
        if not active_line or cls.ENV_ASSIGNMENT_RE.match(active_line):
            return None
        if active_line.startswith("@"):
            parts = active_line.split(maxsplit=1)
            if len(parts) < 2:
                return None
            schedule, cmd = parts[0], parts[1].strip()
        else:
            parts = active_line.split(maxsplit=5)
            if len(parts) < 6:
                return None
            schedule = " ".join(parts[:5])
            cmd = parts[5].strip()

        if not cmd:
            return None
        is_valid, _ = cls.validate_schedule(schedule)
        if not is_valid:
            return None
        return schedule, cmd

    @staticmethod
    def get_crontab():
        """Returns a list of dicts representing cron jobs."""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True, text=True, check=True
            )
            jobs = []
            for line_index, raw_line in enumerate(result.stdout.splitlines()):
                line = raw_line.strip()
                if not line:
                    continue

                is_paused = line.startswith('#')
                active_line = line.lstrip('#').strip()

                parsed = CronManager._parse_cron_line(active_line)
                if parsed is None:
                    continue

                schedule, cmd = parsed
                human_schedule = CronManager.describe_schedule(schedule)
                if is_paused:
                    human_schedule = f"[PAUSED] {human_schedule}"

                jobs.append({
                    "raw_line": line,
                    "raw_schedule": schedule,
                    "human_schedule": human_schedule,
                    "cmd": cmd,
                    "is_paused": is_paused,
                    "line_index": line_index,
                })
            return jobs
        except subprocess.CalledProcessError:
            return []

    @staticmethod
    def get_crontab_raw() -> str:
        try:
            return subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        except subprocess.CalledProcessError:
            return ""

    @staticmethod
    def get_backup_dir() -> Path:
        return Path.home() / ".local" / "state" / "aim-cron-dashboard" / "backups"

    DEFAULT_SETTINGS = {
        "show_ai_badges": True,
        "confirm_force_run": True,
        "left_panel_size": 60,
        "is_horizontal": True,
        "is_swapped": False,
    }

    @staticmethod
    def get_settings_path() -> Path:
        return Path.home() / ".config" / "aim-cron-dashboard" / "settings.json"

    @classmethod
    def load_settings(cls) -> dict:
        settings = dict(cls.DEFAULT_SETTINGS)
        path = cls.get_settings_path()
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    for key, default_val in cls.DEFAULT_SETTINGS.items():
                        if key in loaded and isinstance(loaded[key], type(default_val)):
                            settings[key] = loaded[key]
            except Exception:
                pass
        return settings

    @classmethod
    def save_settings(cls, settings: dict) -> None:
        path = cls.get_settings_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            merged = dict(cls.DEFAULT_SETTINGS)
            merged.update(settings)
            path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def execute_command_capture(cmd: str) -> dict:
        """Executes a command in a detached session while capturing stdout/stderr and exit code."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            stdout, _ = proc.communicate()
            returncode = proc.returncode
            status = "OK" if returncode == 0 else "FAIL"
            output = (stdout or "").strip() or "(no output)"
        except Exception as exc:
            returncode = -1
            status = "FAIL"
            output = str(exc)
        return {
            "status": status,
            "returncode": returncode,
            "timestamp": timestamp,
            "output": output,
        }

    @staticmethod
    def save_crontab(lines: list[str]) -> None:
        """Saves a list of strings as the new crontab, backing up the old one first."""
        current_content = CronManager.get_crontab_raw()
        if current_content.strip():
            backup_dir = CronManager.get_backup_dir()
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"crontab.bak.{timestamp}"
            backup_file.write_text(current_content)

        new_crontab = "\n".join(lines) + "\n"
        subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)

    @staticmethod
    def list_backups() -> list[dict]:
        """Returns available crontab backups sorted newest-first."""
        backup_dir = CronManager.get_backup_dir()
        if not backup_dir.exists():
            return []
        backups = []
        for path in sorted(backup_dir.glob("crontab.bak.*"), key=lambda p: p.name, reverse=True):
            if not path.is_file():
                continue
            raw_ts = path.name.removeprefix("crontab.bak.")
            try:
                dt = datetime.datetime.strptime(raw_ts, "%Y%m%d_%H%M%S")
                ts_label = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                ts_label = raw_ts
            content = path.read_text(encoding="utf-8", errors="replace")
            job_count = sum(
                1
                for line in content.splitlines()
                if line.strip() and CronManager._parse_cron_line(line.strip().lstrip("#").strip()) is not None
            )
            backups.append({
                "path": path,
                "name": path.name,
                "timestamp": ts_label,
                "job_count": job_count,
                "content": content,
            })
        return backups

    @staticmethod
    def restore_backup(backup_path: Path | str) -> None:
        """Restores a crontab snapshot file into the active crontab."""
        target = Path(backup_path)
        if not target.is_file():
            raise FileNotFoundError(f"Backup file not found: {target}")
        content = target.read_text(encoding="utf-8", errors="replace")
        CronManager.save_crontab(content.splitlines())
        
    @staticmethod
    def add_job(schedule: str, cmd: str) -> None:
        is_valid, err = CronManager.validate_schedule(schedule)
        if not is_valid:
            raise ValueError(err)
        current_lines = CronManager.get_crontab_raw().splitlines()
        current_lines.append(f"{schedule.strip()} {cmd.strip()}")
        CronManager.save_crontab(current_lines)

    @staticmethod
    def edit_job(
        target_raw_line: str,
        new_schedule: str,
        new_cmd: str,
        line_index: int | None = None,
        is_paused: bool = False,
    ) -> None:
        is_valid, err = CronManager.validate_schedule(new_schedule)
        if not is_valid:
            raise ValueError(err)
        prefix = "# " if is_paused else ""
        replacement = f"{prefix}{new_schedule.strip()} {new_cmd.strip()}"
        current_lines = CronManager.get_crontab_raw().splitlines()
        if (
            line_index is not None
            and 0 <= line_index < len(current_lines)
            and current_lines[line_index].strip() == target_raw_line.strip()
        ):
            current_lines[line_index] = replacement
        else:
            for idx, line in enumerate(current_lines):
                if line.strip() == target_raw_line.strip():
                    current_lines[idx] = replacement
                    break
        CronManager.save_crontab(current_lines)

    @staticmethod
    def delete_job(target_raw_line: str, line_index: int | None = None) -> None:
        current_lines = CronManager.get_crontab_raw().splitlines()
        if (
            line_index is not None
            and 0 <= line_index < len(current_lines)
            and current_lines[line_index].strip() == target_raw_line.strip()
        ):
            new_lines = current_lines[:line_index] + current_lines[line_index + 1:]
        else:
            new_lines = [line for line in current_lines if line.strip() != target_raw_line.strip()]
        CronManager.save_crontab(new_lines)
            
    @staticmethod
    def toggle_job(target_raw_line: str, line_index: int | None = None) -> None:
        current_lines = CronManager.get_crontab_raw().splitlines()

        def _toggle_line(line: str) -> str:
            if line.strip().startswith('#'):
                return line.strip().lstrip('#').lstrip()
            return f"# {line.strip()}"

        if (
            line_index is not None
            and 0 <= line_index < len(current_lines)
            and current_lines[line_index].strip() == target_raw_line.strip()
        ):
            current_lines[line_index] = _toggle_line(current_lines[line_index])
            CronManager.save_crontab(current_lines)
            return

        new_lines = []
        for line in current_lines:
            if line.strip() == target_raw_line.strip():
                new_lines.append(_toggle_line(line))
            else:
                new_lines.append(line)
        CronManager.save_crontab(new_lines)


class NewJobModal(ModalScreen[tuple]):
    """Modal dialog to add or edit a cron job."""

    def __init__(
        self,
        initial_schedule: str = "",
        initial_cmd: str = "",
        title: str = "New Cron Job",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.initial_schedule = initial_schedule
        self.initial_cmd = initial_cmd
        self.dialog_title = title
    
    CSS = """
    NewJobModal {
        align: center middle;
        background: $background 50%;
    }
    #new-job-dialog {
        width: 80;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $primary;
    }
    #form-and-help {
        height: auto;
    }
    #form-area {
        width: 1fr;
        padding-right: 2;
    }
    #help-area {
        width: 1fr;
        border-left: solid $primary-muted;
        padding-left: 2;
    }
    .buttons {
        width: 100%;
        layout: horizontal;
        align: center middle;
        margin-top: 1;
    }
    Button {
        margin: 0 1;
    }
    .preset-btn {
        min-width: 10;
        height: 1;
        border: none;
        padding: 0 1;
        margin: 0 1;
        background: $primary-muted;
    }
    .preset-btn:hover {
        background: $primary;
    }
    #quick-actions {
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
        align: center middle;
    }
    """
    
    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="new-job-dialog"):
            yield Label(f"[b]{self.dialog_title}[/b]\n")
            
            with Horizontal(id="form-and-help"):
                with Vertical(id="form-area"):
                    yield Label("Cron Schedule:")
                    yield Input(value=self.initial_schedule, id="schedule-input", placeholder="e.g. 0 4 * * *, @daily")
                    
                    with Horizontal(id="quick-actions"):
                        yield Button("@hourly", id="preset-hourly", classes="preset-btn")
                        yield Button("@midnight", id="preset-midnight", classes="preset-btn")
                        yield Button("@daily", id="preset-daily", classes="preset-btn")
                        yield Button("@weekly", id="preset-weekly", classes="preset-btn")
                        yield Button("*/5 * * * *", id="preset-5m", classes="preset-btn")
                    
                    yield Label("Command to execute:")
                    yield Input(value=self.initial_cmd, id="cmd-input", placeholder="/path/to/script.sh")
                    
                    with Horizontal(classes="buttons"):
                        yield Button("Save", variant="success", id="btn-save")
                        yield Button("Cancel", variant="primary", id="btn-cancel")
                        
                with Vertical(id="help-area"):
                    cheatsheet = (
                        "[b]Cron Format:[/b]\n"
                        "[cyan]* * * * *[/cyan]\n"
                        "┬ ┬ ┬ ┬ ┬\n"
                        "│ │ │ │ └ Day of week (0-7, 0=Sun)\n"
                        "│ │ │ └── Month (1-12)\n"
                        "│ │ └──── Day of month (1-31)\n"
                        "│ └────── Hour (0-23)\n"
                        "└──────── Minute (0-59)\n\n"
                        "[b]Examples:[/b]\n"
                        "[cyan]0 4 * * *[/cyan]    : Daily at 4:00 AM\n"
                        "[cyan]*/15 * * * *[/cyan] : Every 15 minutes\n"
                        "[cyan]0 0 * * 1-5[/cyan]  : Midnight on weekdays\n\n"
                        "[b]Shortcuts:[/b]\n"
                        "[cyan]@reboot[/cyan]   : Run at startup\n"
                        "[cyan]@hourly[/cyan]   : Run every hour\n"
                        "[cyan]@midnight[/cyan] : Run every midnight\n"
                        "[cyan]@daily[/cyan]    : Run every midnight\n"
                        "[cyan]@weekly[/cyan]   : Run every Sunday\n"
                        "[cyan]@monthly[/cyan]  : Run once a month\n"
                    )
                    yield Static(cheatsheet)
                
    def on_mount(self) -> None:
        self.query_one("#schedule-input").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            schedule = self.query_one("#schedule-input", Input).value.strip()
            cmd = self.query_one("#cmd-input", Input).value.strip()
            if not schedule or not cmd:
                self.app.notify("Schedule and Command cannot be empty.", title="Error", severity="error")
                return
            is_valid, err = CronManager.validate_schedule(schedule)
            if not is_valid:
                self.app.notify(err, title="Invalid Cron Schedule", severity="error")
                return
            self.dismiss((schedule, cmd))
        elif event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id and event.button.id.startswith("preset-"):
            sched_input = self.query_one("#schedule-input", Input)
            if event.button.id == "preset-hourly":
                sched_input.value = "@hourly"
            elif event.button.id == "preset-midnight":
                sched_input.value = "@midnight"
            elif event.button.id == "preset-daily":
                sched_input.value = "@daily"
            elif event.button.id == "preset-weekly":
                sched_input.value = "@weekly"
            elif event.button.id == "preset-5m":
                sched_input.value = "*/5 * * * *"
            self.query_one("#cmd-input").focus()
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmActionModal(ModalScreen[bool]):
    """Modal dialog to confirm an action (e.g., delete)."""

    def __init__(self, title: str, prompt: str, action_name: str, variant: str = "error", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dialog_title = title
        self.prompt = prompt
        self.action_name = action_name
        self.variant = variant

    CSS = """
    ConfirmActionModal {
        align: center middle;
        background: $background 50%;
    }
    #confirm-action-dialog {
        width: 50;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $primary;
    }
    .buttons {
        width: 100%;
        layout: horizontal;
        align: center middle;
        margin-top: 1;
    }
    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-action-dialog"):
            yield Label(f"[bold]{self.dialog_title}[/bold]")
            yield Label(self.prompt)
            with Horizontal(classes="buttons"):
                yield Button(self.action_name, variant=self.variant, id="btn-yes")
                yield Button("Cancel", variant="primary", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class RestoreBackupModal(ModalScreen[Path | None]):
    """Modal dialog to browse and restore crontab backups."""

    def __init__(self, backups: list[dict], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backups = backups

    CSS = """
    RestoreBackupModal {
        align: center middle;
        background: $background 50%;
    }
    #restore-backup-dialog {
        width: 90;
        height: 28;
        padding: 1 2;
        background: $surface;
        border: round $primary;
    }
    #backup-body {
        height: 1fr;
    }
    #backup-list-pane {
        width: 50%;
        height: 100%;
        padding-right: 1;
    }
    #backup-preview-pane {
        width: 50%;
        height: 100%;
        border-left: solid $primary-muted;
        padding-left: 2;
        overflow-y: scroll;
    }
    #backup-table {
        height: 100%;
    }
    .buttons {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
        margin-top: 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="restore-backup-dialog"):
            yield Label("[b]Restore Crontab Backup[/b]\n")
            with Horizontal(id="backup-body"):
                with Vertical(id="backup-list-pane"):
                    yield DataTable(id="backup-table", cursor_type="row")
                with Vertical(id="backup-preview-pane"):
                    yield Static("Select a backup to preview.", id="backup-preview")
            with Horizontal(classes="buttons"):
                yield Button("Restore Selected", variant="warning", id="btn-restore")
                yield Button("Cancel", variant="primary", id="btn-cancel")

    def on_mount(self) -> None:
        table = self.query_one("#backup-table", DataTable)
        table.add_columns("Timestamp", "Jobs", "File")
        for idx, b in enumerate(self.backups):
            table.add_row(b["timestamp"], str(b["job_count"]), b["name"], key=str(idx))
        table.focus()
        self._update_backup_preview()

    @on(DataTable.RowHighlighted, "#backup-table")
    def on_backup_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._update_backup_preview()

    def _get_selected_backup(self) -> dict | None:
        table = self.query_one("#backup-table", DataTable)
        if table.cursor_row is not None and self.backups:
            try:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
                return self.backups[int(row_key)]
            except Exception:
                return None
        return None

    def _update_backup_preview(self) -> None:
        preview = self.query_one("#backup-preview", Static)
        selected = self._get_selected_backup()
        if selected:
            preview.update(
                f"[bold cyan]{selected['name']}[/bold cyan]\n"
                f"Snapshot Time: {selected['timestamp']} ({selected['job_count']} jobs)\n\n"
                f"{selected['content']}"
            )
        else:
            preview.update("No backup selected.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-restore":
            selected = self._get_selected_backup()
            if selected:
                self.dismiss(selected["path"])
            else:
                self.dismiss(None)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class CronCommandProvider(Provider):
    async def discover(self) -> Hit:
        matcher = self.matcher("")
        async for hit in self.search(""):
            yield hit

    async def search(self, query: str) -> Hit:
        matcher = self.matcher(query)
        app = self.app
        commands = [
            ("New Job", "Create a new cronjob", app.action_new_job),
            ("Edit Job", "Edit the selected cronjob in place", app.action_edit_job),
            ("Restore Backup", "Browse and restore a previous crontab snapshot", app.action_restore_backup),
            ("Refresh Table", "Reload the cronjob list from system", app.action_refresh),
            ("Force Run Job", "Execute the selected job in background", app.action_force_run),
            ("Delete Job", "Delete the selected job", app.action_delete_job),
            ("Toggle Pause/Resume", "Pause or resume the selected job", app.action_toggle_job),
        ]
        for name, description, action in commands:
            if not query:
                yield Hit(1.0, name, action, help=description)
                continue
            score = matcher.match(name)
            if score > 0:
                yield Hit(score, matcher.highlight(name), action, help=description)

class SettingCommandProvider(Provider):
    async def discover(self) -> Hit:
        matcher = self.matcher("")
        async for hit in self.search(""):
            yield hit

    async def search(self, query: str) -> Hit:
        matcher = self.matcher(query)
        app = self.app
        commands = [
            (f"Toggle A.I.M. Badges [{'ON' if app.show_ai_badges else 'OFF'}]", "Show or hide AI agent icons", app.action_toggle_badges),
            (f"Toggle Force Run Warning [{'ON' if app.confirm_force_run else 'OFF'}]", "Enable or disable safety popup", app.action_toggle_force_run_warning),
            ("Help: How to resize panels", "View keyboard shortcuts for panel resizing", app.action_show_resize_help),
        ]
        for name, description, action in commands:
            if not query:
                yield Hit(1.0, name, action, help=description)
                continue
            score = matcher.match(name)
            if score > 0:
                yield Hit(score, matcher.highlight(name), action, help=description)

class LayoutCommandProvider(Provider):
    async def discover(self) -> Hit:
        matcher = self.matcher("")
        async for hit in self.search(""):
            yield hit

    async def search(self, query: str) -> Hit:
        matcher = self.matcher(query)
        app = self.app
        layouts = [
            ("Side-by-Side (List Left)", "horizontal", False),
            ("Side-by-Side (List Right)", "horizontal", True),
            ("Stacked (List Top)", "vertical", False),
            ("Stacked (List Bottom)", "vertical", True),
        ]
        for layout_name, orientation, swapped in layouts:
            action = lambda o=orientation, s=swapped: app.action_set_layout(o, s)
            if not query:
                yield Hit(1.0, layout_name, action, help=f"Switch to {layout_name}")
                continue
            score = matcher.match(layout_name)
            if score > 0:
                yield Hit(score, matcher.highlight(layout_name), action, help=f"Switch to {layout_name}")

class CronDashboard(App):
    """A Textual TUI to manage cron jobs."""

    COMMANDS = App.COMMANDS

    def get_system_commands(self, screen):
        yield from super().get_system_commands(screen)
        yield ("Cron Actions...", "Manage scheduled tasks", self.action_search_jobs, True)
        yield ("Dashboard Settings...", "Configure application preferences", self.action_search_settings, True)
        yield ("UI Layouts...", "Switch structural window layouts", self.action_search_layouts, True)

    def action_search_jobs(self) -> None:
        from textual.command import CommandPalette
        self.push_screen(CommandPalette(providers=[CronCommandProvider], placeholder="Search Cron Actions..."))

    def action_search_settings(self) -> None:
        from textual.command import CommandPalette
        self.push_screen(CommandPalette(providers=[SettingCommandProvider], placeholder="Search Settings..."))

    def action_search_layouts(self) -> None:
        from textual.command import CommandPalette
        self.push_screen(CommandPalette(providers=[LayoutCommandProvider], placeholder="Search Layouts..."))

    show_ai_badges = True
    confirm_force_run = True
    left_panel_size = 60
    is_horizontal = True
    is_swapped = False

    CSS = """
    Screen {
        background: $surface;
    }
    #app-container {
        layout: horizontal;
        width: 100%;
        height: 100%;
    }
    #left-panel {
        width: 60%;
        border: round $primary;
        height: 100%;
        margin: 1;
    }
    #left-panel:focus-within {
        border: round $accent;
    }
    #main-panel {
        width: 40%;
        border: round $primary;
        height: 100%;
        padding: 1 2;
        margin: 1 1 1 0;
        overflow-y: scroll;
    }
    #main-panel:focus-within {
        border: round $accent;
    }
    #preview-area {
        width: 100%;
        height: auto;
    }
    DataTable {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("/", "focus_search", "Search"),
        Binding("n", "new_job", "New Job"),
        Binding("e", "edit_job", "Edit Job"),
        Binding("x", "delete_job", "Delete"),
        Binding("p", "toggle_job", "Pause/Resume"),
        Binding("u", "restore_backup", "Restore Backup"),
        Binding("ctrl+r", "force_run", "Force Run"),
        Binding("[", "resize_left", "Shrink Pane"),
        Binding("]", "resize_right", "Expand Pane"),
        Binding("?", "show_resize_help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="app-container"):
            with Vertical(id="left-panel"):
                yield Input(id="search-input", placeholder="Filter jobs (/)")
                yield DataTable(id="job-table", cursor_type="row")
            with Vertical(id="main-panel"):
                yield Static("Select a cronjob on the left to preview.", id="preview-area")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(aim_theme)
        self.theme = "aim-dark"
        self.title = "A.I.M. Sovereign Orchestrator"
        self.sub_title = "Cron Dashboard"
        self.jobs = []
        self.run_history: dict[str, dict] = {}
        saved = CronManager.load_settings()
        self.show_ai_badges = saved["show_ai_badges"]
        self.confirm_force_run = saved["confirm_force_run"]
        self.left_panel_size = max(10, min(90, saved["left_panel_size"]))
        self.is_horizontal = saved["is_horizontal"]
        self.is_swapped = saved["is_swapped"]
        table = self.query_one("#job-table", DataTable)
        table.add_columns("Schedule", "Human Readable", "Command")
        self._apply_saved_layout_structure()
        self.refresh_jobs()
        table.focus()

    def _save_current_settings(self) -> None:
        CronManager.save_settings({
            "show_ai_badges": self.show_ai_badges,
            "confirm_force_run": self.confirm_force_run,
            "left_panel_size": self.left_panel_size,
            "is_horizontal": self.is_horizontal,
            "is_swapped": self.is_swapped,
        })

    def _apply_saved_layout_structure(self) -> None:
        orientation = "horizontal" if self.is_horizontal else "vertical"
        container = self.query_one("#app-container")
        container.styles.layout = orientation
        left = self.query_one("#left-panel")
        right = self.query_one("#main-panel")
        if self.is_swapped:
            container.move_child(left, after=right)
        else:
            container.move_child(left, before=right)
        self.apply_layout()

    def format_cmd(self, cmd: str) -> str:
        """Add a high-visibility badge to known AI agent processes and recent force-run status."""
        run_badge = ""
        history = getattr(self, "run_history", {}).get(cmd)
        if history:
            st = history.get("status")
            if st == "RUNNING":
                run_badge = "[bold yellow][RUNNING][/bold yellow] "
            elif st == "OK":
                run_badge = "[bold green][OK][/bold green] "
            elif st == "FAIL":
                run_badge = "[bold red][FAIL][/bold red] "

        if not self.show_ai_badges:
            return f"{run_badge}{cmd}"
            
        if "tmux new-session" in cmd:
            return f"{run_badge}🤖 [bold cyan][Ephemeral A.I.M. Agent][/bold cyan] {cmd}"
            
        agents = ["agy", "aider", "claude", "grok", "gpt", "agent", "opencode", "gemini", "codex", "antigravity"]
        if any(agent in cmd.lower() for agent in agents):
            return f"{run_badge}[bold cyan][A.I.][/bold cyan] {cmd}"
        return f"{run_badge}{cmd}"

    def refresh_jobs(self) -> None:
        table = self.query_one("#job-table", DataTable)
        search_query = self.query_one("#search-input", Input).value.lower()
        
        table.clear()
        self.jobs = CronManager.get_crontab()
        
        for idx, job in enumerate(self.jobs):
            if search_query and search_query not in job['cmd'].lower() and search_query not in job['human_schedule'].lower():
                continue
                
            cmd = self.format_cmd(job["cmd"])
            
            # Dim the row if paused
            if job['is_paused']:
                schedule_display = Text(job["raw_schedule"], style="dim")
                human_display = Text(job["human_schedule"], style="dim")
                cmd_display = Text(cmd, style="dim")
            else:
                schedule_display = job["raw_schedule"]
                human_display = job["human_schedule"]
                cmd_display = cmd
                
            table.add_row(schedule_display, human_display, cmd_display, key=str(idx))

    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Dynamically filter the session tree as the user types."""
        self.refresh_jobs()

    @on(Input.Submitted, "#search-input")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        """Return focus to the table when user hits enter in search."""
        self.query_one("#job-table").focus()

    def action_toggle_badges(self) -> None:
        self.show_ai_badges = not self.show_ai_badges
        self._save_current_settings()
        self.refresh_jobs()
        self.notify(f"A.I.M. Badges {'enabled' if self.show_ai_badges else 'disabled'}.")

    def action_toggle_force_run_warning(self) -> None:
        self.confirm_force_run = not self.confirm_force_run
        self._save_current_settings()
        self.notify(f"Force Run Warning {'enabled' if self.confirm_force_run else 'disabled'}.")

    def action_show_resize_help(self) -> None:
        self.push_screen(HelpModal())

    def action_set_layout(self, orientation: str, swapped: bool) -> None:
        self.is_horizontal = (orientation == "horizontal")
        self.is_swapped = swapped
        self._apply_saved_layout_structure()
        self._save_current_settings()
        self.notify("Layout changed.")

    def action_resize_left(self) -> None:
        self.left_panel_size = max(10, self.left_panel_size - 5)
        self.apply_layout()
        self._save_current_settings()

    def action_resize_right(self) -> None:
        self.left_panel_size = min(90, self.left_panel_size + 5)
        self.apply_layout()
        self._save_current_settings()

    def apply_layout(self) -> None:
        left = self.query_one("#left-panel")
        right = self.query_one("#main-panel")
        if self.is_horizontal:
            left.styles.width = f"{self.left_panel_size}%"
            left.styles.height = "100%"
            right.styles.width = f"{100 - self.left_panel_size}%"
            right.styles.height = "100%"
        else:
            left.styles.width = "100%"
            left.styles.height = f"{self.left_panel_size}%"
            right.styles.width = "100%"
            right.styles.height = f"{100 - self.left_panel_size}%"

    def action_focus_search(self) -> None:
        """Focus the search input when / is pressed."""
        self.query_one("#search-input").focus()

    def action_refresh(self) -> None:
        """Manually refresh the table."""
        self.refresh_jobs()
        self.notify("Jobs refreshed.", title="A.I.M.")

    def action_new_job(self) -> None:
        def check_new_job(result: tuple | None) -> None:
            if result is not None:
                schedule, cmd = result
                try:
                    CronManager.add_job(schedule, cmd)
                    self.refresh_jobs()
                    self.notify("Job added.", title="Success")
                except (ValueError, subprocess.CalledProcessError) as err:
                    self.notify(f"Failed to save job: {err}", title="Error", severity="error")
        self.push_screen(NewJobModal(), check_new_job)

    def action_restore_backup(self) -> None:
        backups = CronManager.list_backups()
        if not backups:
            self.notify("No crontab backups found in ~/.local/state/aim-cron-dashboard/backups/.", title="Backups")
            return

        def check_restore(selected_path: Path | None) -> None:
            if selected_path is not None:
                try:
                    CronManager.restore_backup(selected_path)
                    self.refresh_jobs()
                    self.update_preview()
                    self.notify(f"Restored backup: {selected_path.name}", title="Success")
                except (OSError, subprocess.CalledProcessError) as err:
                    self.notify(f"Failed to restore backup: {err}", title="Error", severity="error")

        self.push_screen(RestoreBackupModal(backups), check_restore)

    def action_edit_job(self) -> None:
        table = self.query_one("#job-table", DataTable)
        if table.cursor_row is not None:
            try:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
                job = self.jobs[int(row_key)]

                def check_edit_job(result: tuple | None) -> None:
                    if result is not None:
                        schedule, cmd = result
                        try:
                            CronManager.edit_job(
                                job["raw_line"],
                                schedule,
                                cmd,
                                line_index=job.get("line_index"),
                                is_paused=job["is_paused"],
                            )
                            self.refresh_jobs()
                            self.update_preview()
                            self.notify("Job updated.", title="Success")
                        except (ValueError, subprocess.CalledProcessError) as err:
                            self.notify(f"Failed to update job: {err}", title="Error", severity="error")

                modal = NewJobModal(
                    initial_schedule=job["raw_schedule"],
                    initial_cmd=job["cmd"],
                    title="Edit Cron Job",
                )
                self.push_screen(modal, check_edit_job)
            except Exception:
                self.notify("Error selecting job to edit.", severity="error")

    def action_delete_job(self) -> None:
        table = self.query_one("#job-table", DataTable)
        if table.cursor_row is not None:
            try:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
                job = self.jobs[int(row_key)]
                
                def check_delete(confirm: bool) -> None:
                    if confirm:
                        try:
                            CronManager.delete_job(job["raw_line"], line_index=job.get("line_index"))
                            self.refresh_jobs()
                            self.update_preview()
                            self.notify("Job deleted.", title="Success")
                        except subprocess.CalledProcessError as err:
                            self.notify(f"Failed to delete job: {err}", title="Error", severity="error")
                        
                modal = ConfirmActionModal(
                    title="Delete Job",
                    prompt=f"Are you sure you want to delete this job?\n\n{job['cmd']}",
                    action_name="Yes (Delete)",
                    variant="error"
                )
                self.push_screen(modal, check_delete)
            except Exception as e:
                self.notify("Error selecting job.", severity="error")

    def action_force_run(self) -> None:
        table = self.query_one("#job-table", DataTable)
        if table.cursor_row is not None:
            try:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
                job = self.jobs[int(row_key)]
                cmd = job["cmd"]
                
                def check_run(confirm: bool) -> None:
                    if confirm:
                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.run_history[cmd] = {
                            "status": "RUNNING",
                            "returncode": None,
                            "timestamp": now_str,
                            "output": "Executing in background...",
                        }
                        self.refresh_jobs()
                        self.update_preview()
                        self.notify(f"Dispatched background task:\n{cmd}", title="Force Run Initiated")

                        def _worker() -> None:
                            result = CronManager.execute_command_capture(cmd)
                            self.run_history[cmd] = result
                            try:
                                self.call_from_thread(self._on_force_run_complete, cmd, result)
                            except Exception:
                                pass

                        threading.Thread(target=_worker, daemon=True).start()

                if self.confirm_force_run:
                    modal = ConfirmActionModal(
                        title="Force Run Job",
                        prompt=f"Are you sure you want to instantly run this job in the background?\n\n{cmd}",
                        action_name="Yes (Run)",
                        variant="warning"
                    )
                    self.push_screen(modal, check_run)
                else:
                    check_run(True)
            except Exception:
                self.notify("Error selecting job for force run.", severity="error")

    def _on_force_run_complete(self, cmd: str, result: dict) -> None:
        self.refresh_jobs()
        self.update_preview()
        if result["status"] == "OK":
            self.notify(f"Completed (exit 0):\n{cmd}", title="Force Run OK")
        else:
            self.notify(
                f"Failed (exit {result['returncode']}):\n{cmd}",
                title="Force Run Failed",
                severity="error",
            )

    def action_toggle_job(self) -> None:
        table = self.query_one("#job-table", DataTable)
        if table.cursor_row is not None:
            try:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
                job = self.jobs[int(row_key)]
                
                action_str = "Resume" if job["is_paused"] else "Pause"
                variant_str = "success" if job["is_paused"] else "warning"
                
                def check_toggle(confirm: bool) -> None:
                    if confirm:
                        try:
                            CronManager.toggle_job(job["raw_line"], line_index=job.get("line_index"))
                            self.refresh_jobs()
                            self.update_preview()
                            self.notify(f"Job {action_str.lower()}d.", title="Success")
                        except subprocess.CalledProcessError as err:
                            self.notify(f"Failed to {action_str.lower()} job: {err}", title="Error", severity="error")
                        
                modal = ConfirmActionModal(
                    title=f"{action_str} Job",
                    prompt=f"Are you sure you want to {action_str.lower()} this job?\n\n{job['cmd']}",
                    action_name=f"Yes ({action_str})",
                    variant=variant_str
                )
                
                self.push_screen(modal, check_toggle)
            except Exception:
                self.notify("Error selecting job.", severity="error")

    @on(DataTable.RowHighlighted, "#job-table")
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Instantly update the preview when the user highlights a row."""
        self.update_preview()

    def update_preview(self) -> None:
        """Fetch and render the pane contents for the currently highlighted node."""
        table = self.query_one("#job-table", DataTable)
        preview_area = self.query_one("#preview-area", Static)

        if table.cursor_row is not None:
            try:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
                job = self.jobs[int(row_key)]
                
                status = "[bold red]PAUSED[/bold red]" if job['is_paused'] else "[bold green]ACTIVE[/bold green]"
                
                preview_text = f"Status: {status}\n\n"
                preview_text += f"Raw Schedule: {job['raw_schedule']}\n"
                preview_text += f"Human Readable: {job['human_schedule']}\n\n"
                preview_text += f"Command:\n{job['cmd']}"

                history = getattr(self, "run_history", {}).get(job["cmd"])
                if history:
                    st = history["status"]
                    if st == "RUNNING":
                        badge = "[bold yellow]RUNNING[/bold yellow]"
                    elif st == "OK":
                        badge = f"[bold green]OK (exit {history['returncode']})[/bold green]"
                    else:
                        badge = f"[bold red]FAIL (exit {history['returncode']})[/bold red]"
                    preview_text += (
                        f"\n\n[bold cyan]Last Force Run:[/bold cyan] {badge} at {history['timestamp']}\n"
                        f"Output:\n{history['output']}"
                    )
                preview_area.update(preview_text)
            except Exception:
                preview_area.update("Select a cronjob to preview.")
        else:
            preview_area.update("Select a cronjob to preview.")


if __name__ == "__main__":
    app = CronDashboard()
    app.run()
