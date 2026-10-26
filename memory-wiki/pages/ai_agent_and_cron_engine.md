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

## 3. Detached Force Run (`action_force_run`)
- Triggered via `ctrl+r` or `ctrl+p -> Cron Actions... -> Force Run Job`.
- Guarded by `ConfirmActionModal` when `self.confirm_force_run` is `True` (default).
- Launches the command asynchronously in a new process session with output redirected to `/dev/null` so the TUI never blocks:
  ```python
  subprocess.Popen(
      cmd,
      shell=True,
      start_new_session=True,
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
  )
  ```

## 4. Audited Edge Cases & Technical Debt (Candidates for Next Issues)
1. **`@` Nickname Parsing Bug in `CronManager.get_crontab()` (`bin/dashboard.py:84-87`):**
   - `NewJobModal` offers preset buttons and cheatsheet entries for `@hourly`, `@midnight`, `@daily`, `@weekly`, `@monthly`, and `@reboot`.
   - However, `CronManager.get_crontab()` parses lines using `parts = active_line.split(maxsplit=5)` and requires `len(parts) >= 6`, assuming all schedules have 5 whitespace-separated fields (`m h dom mon dow`).
   - If a user saves `@daily /path/to/script.sh` (only 2 whitespace-separated tokens), `len(parts)` is `2 < 6` and the job is silently omitted from the UI table. If the command itself has 5+ spaces, the first 4 tokens of the command are erroneously absorbed into `schedule`.
   - **Fix Pattern:** Check if `active_line.startswith("@")`; if so, split with `maxsplit=1` (`schedule, cmd = active_line.split(maxsplit=1)`), otherwise split with `maxsplit=5`. Also skip non-cron comment headers (lines starting with `#` whose uncommented body does not match a valid 5-field cron expression or `@` nickname, or environment variable assignments like `SHELL=/bin/bash`).
2. **`install.sh` Entrypoint Symlink Drift (`install.sh:16`):**
   - Commit `12a45ba` renamed `bin/aim-dash` to `bin/aim-cron`, and `README.md` documents `ln -sf $(pwd)/bin/aim-cron ~/.local/bin/aim-cron`.
   - However, `install.sh` line 16 still runs `ln -sf "$DIR/bin/aim-dash" ~/.local/bin/aim-cron-dashboard`, creating a broken symlink.
3. **`bin/aim-cron` Missing-Venv Error Message (`bin/aim-cron:12`):**
   - If `venv/bin/python` is missing, `bin/aim-cron` prints `Please run: ./scripts/setup.sh` (inherited from `aim-tmux-dashboard`) instead of `./install.sh`.
4. **Identical Duplicate Lines in `delete_job` / `toggle_job`:**
   - Matching by `line.strip() == target_raw_line.strip()` will delete or toggle all identical copies if two identical cron lines exist in `crontab`.

## Related Pages
- [Core TUI Architecture](architecture.md)
- [Roadmap, Feature Audit & Issue History](roadmap_and_history.md)
