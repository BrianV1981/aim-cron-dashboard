#!/usr/bin/env python3
import subprocess
import os
import sys
import re
import datetime
from pathlib import Path
from textual.app import App, ComposeResult
from textual import on
from textual.widgets import Header, Footer, DataTable, Static, Input, Button, Label
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.screen import ModalScreen
from rich.text import Text
import cron_descriptor

class CronManager:
    """Wrapper for crontab commands."""

    @staticmethod
    def get_crontab():
        """Returns a list of dicts representing cron jobs."""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True, text=True, check=True
            )
            jobs = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Check if paused
                is_paused = line.startswith('#')
                active_line = line.lstrip('#').strip()
                
                parts = active_line.split(maxsplit=5)
                if len(parts) >= 6:
                    schedule = " ".join(parts[:5])
                    cmd = parts[5]
                    try:
                        human_schedule = cron_descriptor.get_description(schedule)
                    except Exception:
                        human_schedule = schedule
                        
                    if is_paused:
                        human_schedule = f"[PAUSED] {human_schedule}"
                        
                    jobs.append({
                        "raw_line": line,
                        "raw_schedule": schedule,
                        "human_schedule": human_schedule,
                        "cmd": cmd,
                        "is_paused": is_paused
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
    def save_crontab(lines: list[str]) -> None:
        """Saves a list of strings as the new crontab, backing up the old one first."""
        current_content = CronManager.get_crontab_raw()
        if current_content.strip():
            backup_dir = Path.home() / ".local" / "state" / "aim-cron-dashboard" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"crontab.bak.{timestamp}"
            backup_file.write_text(current_content)

        new_crontab = "\n".join(lines) + "\n"
        subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)
        
    @staticmethod
    def add_job(schedule: str, cmd: str) -> None:
        current_lines = CronManager.get_crontab_raw().splitlines()
        current_lines.append(f"{schedule} {cmd}")
        CronManager.save_crontab(current_lines)

    @staticmethod
    def delete_job(target_raw_line: str) -> None:
        current_lines = CronManager.get_crontab_raw().splitlines()
        new_lines = [line for line in current_lines if line.strip() != target_raw_line.strip()]
        CronManager.save_crontab(new_lines)
            
    @staticmethod
    def toggle_job(target_raw_line: str) -> None:
        current_lines = CronManager.get_crontab_raw().splitlines()
        new_lines = []
        for line in current_lines:
            if line.strip() == target_raw_line.strip():
                if line.startswith('#'):
                    new_lines.append(line.lstrip('#').lstrip())
                else:
                    new_lines.append(f"# {line}")
            else:
                new_lines.append(line)
        CronManager.save_crontab(new_lines)


class NewJobModal(ModalScreen[tuple]):
    """Modal dialog to add a new cron job."""
    
    CSS = """
    NewJobModal {
        align: center middle;
    }
    #new-job-dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $primary 80%;
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
        with Vertical(id="new-job-dialog"):
            yield Label("New Cron Job")
            yield Input(id="schedule-input", placeholder="Schedule (e.g. 0 4 * * *)")
            yield Input(id="cmd-input", placeholder="Command (e.g. /path/to/script.sh)")
            with Horizontal(classes="buttons"):
                yield Button("Save", variant="success", id="btn-save")
                yield Button("Cancel", variant="primary", id="btn-cancel")
                
    def on_mount(self) -> None:
        self.query_one("#schedule-input").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            schedule = self.query_one("#schedule-input", Input).value.strip()
            cmd = self.query_one("#cmd-input", Input).value.strip()
            if schedule and cmd:
                self.dismiss((schedule, cmd))
            else:
                self.app.notify("Schedule and Command cannot be empty.", title="Error", severity="error")
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
    }
    #confirm-action-dialog {
        width: 50;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $primary 80%;
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


class CronDashboard(App):
    """A Textual TUI to manage cron jobs."""

    CSS = """
    Screen {
        background: $surface;
    }
    #left-panel {
        width: 60%;
        border-right: solid $primary;
        height: 100%;
    }
    #main-panel {
        width: 40%;
        height: 100%;
        padding: 1 2;
        overflow-y: scroll;
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
        Binding("x", "delete_job", "Delete"),
        Binding("p", "toggle_job", "Pause/Resume"),
        Binding("ctrl+r", "force_run", "Force Run"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="left-panel"):
                yield Input(id="search-input", placeholder="Filter jobs (/)")
                yield DataTable(id="job-table", cursor_type="row")
            with Vertical(id="main-panel"):
                yield Static("Select a cronjob on the left to preview.", id="preview-area")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "A.I.M. Sovereign Orchestrator"
        self.sub_title = "Cron Dashboard"
        table = self.query_one("#job-table", DataTable)
        table.add_columns("Schedule", "Human Readable", "Command")
        self.jobs = []
        self.refresh_jobs()
        table.focus()

    def format_cmd(self, cmd: str) -> str:
        """Add a high-visibility badge to known AI agent processes."""
        if "tmux new-session" in cmd:
            return f"🤖 [bold cyan][Ephemeral A.I.M. Agent][/bold cyan] {cmd}"
            
        agents = ["agy", "aider", "claude", "grok", "gpt", "agent", "opencode", "gemini", "codex", "antigravity"]
        if any(agent in cmd.lower() for agent in agents):
            return f"[bold cyan][A.I.][/bold cyan] {cmd}"
        return cmd

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
                CronManager.add_job(schedule, cmd)
                self.refresh_jobs()
                self.notify("Job added.", title="Success")
        self.push_screen(NewJobModal(), check_new_job)

    def action_delete_job(self) -> None:
        table = self.query_one("#job-table", DataTable)
        if table.cursor_row is not None:
            try:
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
                job = self.jobs[int(row_key)]
                
                def check_delete(confirm: bool) -> None:
                    if confirm:
                        CronManager.delete_job(job["raw_line"])
                        self.refresh_jobs()
                        self.notify("Job deleted.", title="Success")
                        
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
                        subprocess.Popen(cmd, shell=True, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self.notify(f"Dispatched background task:\n{cmd}", title="Force Run Initiated")

                modal = ConfirmActionModal(
                    title="Force Run Job",
                    prompt=f"Are you sure you want to instantly run this job in the background?\n\n{cmd}",
                    action_name="Yes (Run)",
                    variant="warning"
                )
                self.push_screen(modal, check_run)
            except Exception:
                self.notify("Error selecting job for force run.", severity="error")

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
                        CronManager.toggle_job(job["raw_line"])
                        self.refresh_jobs()
                        self.notify(f"Job {action_str.lower()}d.", title="Success")
                        
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
                preview_area.update(preview_text)
            except Exception:
                preview_area.update("Select a cronjob to preview.")
        else:
            preview_area.update("Select a cronjob to preview.")


if __name__ == "__main__":
    app = CronDashboard()
    app.run()
