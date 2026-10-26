# Cron Engine, A.I.M. Badging & Known Edge Cases

This page documents how `CronManager` in `bin/dashboard.py` interacts with the host system's `crontab`, how `CronDashboard` badges AI agent tasks, and the edge cases identified in the current implementation.

## 1. `CronManager` Subprocess & Backup Lifecycle
- **Read (`get_crontab` & `get_crontab_raw`):**
  - Invokes `subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=True)`.
  - If the user has no crontab (`CalledProcessError`), gracefully returns `[]` or `""`.
  - Strips empty lines, detects paused jobs via `line.startswith('#')`, strips leading `#` characters to parse the schedule/command, and translates the schedule via `cron_descriptor.get_description(schedule)` (falling back to the raw schedule string on exception).
  - Pre-pends `[PAUSED] ` to `human_schedule` for commented jobs, which `CronDashboard.refresh_jobs()` renders in `dim` Rich text style.
- **Write & Automatic Backups (`save_crontab`):**
  - Before any mutation (`add_job`, `delete_job`, `toggle_job`), reads the existing raw crontab and, if non-empty, writes a timestamped snapshot to:
    `~/.local/state/aim-cron-dashboard/backups/crontab.bak.<YYYYMMDD_HHMMSS>`
  - Writes the updated line list back to the system crontab via `subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)`.
- **CRUD Operations:**
  - `add_job(schedule, cmd)`: Appends `f"{schedule} {cmd}"` to `get_crontab_raw().splitlines()`.
  - `delete_job(target_raw_line)`: Filters out any line where `line.strip() == target_raw_line.strip()`.
  - `toggle_job(target_raw_line)`: Toggles leading `# ` on matching lines to pause or resume jobs in place without losing schedule position.

## 2. A.I.M. Agent Badging (`format_cmd`)
When `self.show_ai_badges` is `True` (default, toggleable via `ctrl+p -> Dashboard Settings...`), `CronDashboard.format_cmd(cmd)` decorates commands in `#job-table`:
1. **Ephemeral Tmux Agents:** If `"tmux new-session"` appears in `cmd`, prefixes:
   `🤖 [bold cyan][Ephemeral A.I.M. Agent][/bold cyan] `
2. **Known AI CLI Vessels:** If any token in `["agy", "aider", "claude", "grok", "gpt", "agent", "opencode", "gemini", "codex", "antigravity"]` appears in `cmd.lower()`, prefixes:
   `[bold cyan][A.I.][/bold cyan] `

## 3. Detached Force Run & Output Capture (`action_force_run` / `execute_command_capture`)
- Triggered via `ctrl+r` or `ctrl+p -> Cron Actions... -> Force Run Job`.
- Guarded by `ConfirmActionModal` when `self.confirm_force_run` is `True` (default).
- Immediately records `status="RUNNING"` in `self.run_history[cmd]` (displaying `[RUNNING]` in `#job-table` and `#preview-area`) and spawns a daemon worker thread calling `CronManager.execute_command_capture(cmd)`:
  - Runs `subprocess.Popen(cmd, shell=True, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)`.
  - On completion, updates `self.run_history[cmd]` with `status` (`"OK"` or `"FAIL"`), `returncode`, `timestamp`, and captured `output`, and refreshes the UI via `self.call_from_thread(self._on_force_run_complete, cmd, result)`.

## 4. Persistent Settings & Schedule Validation (Issues `#9`–`#13` Resolved)
1. **`@` Nickname & 5-Field Schedule Validation (`CronManager.validate_schedule` & `_parse_cron_line`):**
   - Supports `@reboot`, `@hourly`, `@midnight`, `@daily`, `@weekly`, `@monthly`, `@yearly`, and `@annually` (`maxsplit=1`) as well as standard 5-field schedules (`minute`, `hour`, `day of month`, `month` `1-12`/`JAN-DEC`, `day of week` `0-7`/`SUN-SAT`).
   - Automatically filters out non-cron prose comments (`# ...`) and environment variable assignments (`SHELL=`, `PATH=`, `MAILTO=`).
2. **Line-Index Targeting (`line_index`):**
   - `CronManager.get_crontab()` records the 0-based `line_index` from `crontab -l`, and `edit_job()`, `delete_job()`, and `toggle_job()` target that exact line index so duplicate cron lines do not collide.
3. **Backup Discovery & Restore (`list_backups` & `restore_backup`):**
   - Lists `crontab.bak.*` snapshots in `~/.local/state/aim-cron-dashboard/backups/` sorted newest-first and restores them via `RestoreBackupModal` (`u`).
4. **Persistent UI Settings (`~/.config/aim-cron-dashboard/settings.json`):**
   - `CronManager.load_settings()` and `save_settings()` persist `show_ai_badges`, `confirm_force_run`, `left_panel_size`, `is_horizontal`, and `is_swapped` across restarts.

## Related Pages
- [Core TUI Architecture](architecture.md)
- [Roadmap, Feature Audit & Issue History](roadmap_and_history.md)
