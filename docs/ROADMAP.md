# A.I.M. Cron Dashboard: Roadmap

`aim-cron-dashboard` (`aim-cron`) is the sister TUI cockpit to `aim-tmux-dashboard` (`~/aim-tmux-dashboard`), sharing the `aim-dark` Textual aesthetic, dynamic split-pane layouts, and nested Command Palette design.

---

## ✅ Completed Milestones (`v0.1.0` – `v0.2.0`)

### Phase 1 & 2: UI Shell & Cron Engine (`#1`, `#2`, `#9`)
* [x] **Textual Split-Pane Cockpit:** `DataTable` job list on the left, detailed status/command preview on the right, and live `/` substring search.
* [x] **System Crontab & Human Translation:** `CronManager.get_crontab()` backed by `crontab -l` and `cron-descriptor`, supporting both 5-field cron expressions and `@shortcut` nicknames (`@reboot`, `@hourly`, `@midnight`, `@daily`, `@weekly`, `@monthly`, `@yearly`, `@annually`).

### Phase 3: Interactive CRUD & Validation (`#3`, `#9`, `#11`)
* [x] **New Job (`n`) & In-Place Edit (`e`):** `NewJobModal` with quick-select schedule presets, side-by-side cron cheatsheet, and `CronManager.validate_schedule()`.
* [x] **Delete (`x`) & Pause/Resume Toggle (`p`):** Line-index-aware crontab updates with confirmation dialogs.

### Phase 4: A.I.M. Polish, Backups & Layouts (`#4`–`#14`)
* [x] **Agent Badging:** Automatic `🤖 [Ephemeral A.I.M. Agent]` (`tmux new-session`) and `[A.I.]` badging.
* [x] **Detached Force Run (`Ctrl+R`):** Background execution with live `[RUNNING]` / `[OK]` / `[FAIL]` badge, exit code, and `stdout`/`stderr` capture (`#13`).
* [x] **Automatic Safety Backups & Time-Machine Restore (`u`):** Timestamped `crontab.bak.<timestamp>` snapshots before every write and `RestoreBackupModal` (`#4`, `#12`).
* [x] **Dynamic Layouts & Persistent Settings:** 4 switchable orientations (`Side-by-Side`, `Stacked`), `[` / `]` pane resizing, nested Command Palette submenus (`#5`–`#7`), and persistent `~/.config/aim-cron-dashboard/settings.json` (`#13`).
