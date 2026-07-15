#!/usr/bin/env python3
import subprocess
import os
import sys
import re
from textual.app import App, ComposeResult
from textual import on
from textual.widgets import Header, Footer, DataTable, Static, Input
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
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
                if not line or line.startswith('#'):
                    continue
                # A basic cron line parsing (5 fields for schedule, rest is command)
                parts = line.split(maxsplit=5)
                if len(parts) >= 6:
                    schedule = " ".join(parts[:5])
                    cmd = parts[5]
                    try:
                        human_schedule = cron_descriptor.get_description(schedule)
                    except Exception:
                        human_schedule = schedule
                    jobs.append({
                        "raw_schedule": schedule,
                        "human_schedule": human_schedule,
                        "cmd": cmd
                    })
            return jobs
        except subprocess.CalledProcessError:
            return []

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
            table.add_row(job["raw_schedule"], job["human_schedule"], cmd, key=str(idx))

    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Dynamically filter the session tree as the user types."""
        self.refresh_jobs()

    @on(Input.Submitted, "#search-input")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        """Return focus to the tree when user hits enter in search."""
        self.query_one("#job-table").focus()

    def action_focus_search(self) -> None:
        """Focus the search input when / is pressed."""
        self.query_one("#search-input").focus()

    def action_refresh(self) -> None:
        """Manually refresh the table."""
        self.refresh_jobs()
        self.notify("Jobs refreshed.", title="A.I.M.")

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
                preview_text = f"Raw Schedule: {job['raw_schedule']}\n"
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
