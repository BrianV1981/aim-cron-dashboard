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
        background: $background 50%;
    }
    #new-job-dialog {
        width: 60;
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
            ("Refresh Table", "Reload the cronjob list from system", app.action_refresh),
            ("Force Run Job", "Execute the selected job in background", app.action_force_run),
            ("Delete Job", "Delete the selected job", app.action_delete_job),
            ("Toggle Pause/Resume", "Pause or resume the selected job", app.action_toggle_job),
        ]
        for name, description, action in commands:
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
        Binding("x", "delete_job", "Delete"),
        Binding("p", "toggle_job", "Pause/Resume"),
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
        table = self.query_one("#job-table", DataTable)
        table.add_columns("Schedule", "Human Readable", "Command")
        self.jobs = []
        self.refresh_jobs()
        table.focus()

    def format_cmd(self, cmd: str) -> str:
        """Add a high-visibility badge to known AI agent processes."""
        if not self.show_ai_badges:
            return cmd
            
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

    def action_toggle_badges(self) -> None:
        self.show_ai_badges = not self.show_ai_badges
        self.refresh_jobs()
        self.notify(f"A.I.M. Badges {'enabled' if self.show_ai_badges else 'disabled'}.")

    def action_toggle_force_run_warning(self) -> None:
        self.confirm_force_run = not self.confirm_force_run
        self.notify(f"Force Run Warning {'enabled' if self.confirm_force_run else 'disabled'}.")

    def action_show_resize_help(self) -> None:
        self.push_screen(HelpModal())

    def action_set_layout(self, orientation: str, swapped: bool) -> None:
        self.is_horizontal = (orientation == "horizontal")
        self.is_swapped = swapped
        
        container = self.query_one("#app-container")
        container.styles.layout = orientation
        
        left = self.query_one("#left-panel")
        right = self.query_one("#main-panel")
        
        if swapped:
            container.move_child(left, after=right)
        else:
            container.move_child(left, before=right)
            
        self.apply_layout()
        self.notify(f"Layout changed.")

    def action_resize_left(self) -> None:
        self.left_panel_size = max(10, self.left_panel_size - 5)
        self.apply_layout()

    def action_resize_right(self) -> None:
        self.left_panel_size = min(90, self.left_panel_size + 5)
        self.apply_layout()

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
