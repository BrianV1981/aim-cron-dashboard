# Core TUI Architecture

`aim-cron-dashboard` (`aim-cron`) is built as a single-file Python [Textual](https://github.com/Textualize/textual) application at `bin/dashboard.py`, launched via the `bin/aim-cron` shell wrapper. It is designed as the sister cockpit to `aim-tmux-dashboard` (`aim-dash`), sharing the `aim-dark` cyan/charcoal visual language, keyboard navigation conventions, and nested Command Palette architecture.

## 1. Entrypoint & Environment (`bin/aim-cron`)
- Resolves symlinks via `readlink -f "${BASH_SOURCE[0]}"` so global symlinks (e.g., `~/.local/bin/aim-cron`) locate the repository root and isolated `venv/`.
- Executes `"$PROJECT_ROOT/venv/bin/python" "$DIR/dashboard.py" "$@"` with dependencies `textual` and `cron-descriptor` (`requirements.txt`).

## 2. Theme & Main Screen Layout (`CronDashboard`)
- **Theme (`aim_theme`):** Registers `aim-dark` (`primary="#00ffff"`, `secondary="#0088ff"`, `accent="#00ffff"`, `background="#121212"`, `surface="#1e1e1e"`, `panel="#2e2e2e"`).
- **Split-Pane Container (`#app-container`):**
  - **Left Panel (`#left-panel`, default 60% width):** Holds `#search-input` (`Input` for real-time substring filtering across `cmd` and `human_schedule`) and `#job-table` (`DataTable` with `cursor_type="row"` and columns `Schedule`, `Human Readable`, `Command`).
  - **Main Preview Panel (`#main-panel`, default 40% width):** Holds `#preview-area` (`Static`), which updates on `DataTable.RowHighlighted` (`update_preview()`) to display `Status` (`ACTIVE` in green or `PAUSED` in red), `Raw Schedule`, `Human Readable`, and full `Command`.

## 3. Keyboard Bindings
| Key | Action | Description |
|-----|--------|-------------|
| `q` | `action_quit` | Exit `aim-cron` |
| `r` | `action_refresh` | Reload system crontab into `#job-table` |
| `/` | `action_focus_search` | Focus `#search-input` (`Enter` returns focus to `#job-table`) |
| `n` | `action_new_job` | Open `NewJobModal` to create and append a cron job |
| `e` | `action_edit_job` | Open `NewJobModal` pre-populated with the highlighted job to edit in place |
| `x` | `action_delete_job` | Open `ConfirmActionModal` to remove the highlighted job |
| `p` | `action_toggle_job` | Open `ConfirmActionModal` to comment (`# `) or uncomment the highlighted job |
| `u` | `action_restore_backup` | Open `RestoreBackupModal` to browse, preview, and restore a `crontab.bak.*` snapshot |
| `ctrl+r` | `action_force_run` | Execute the highlighted job's command in a background session and capture `stdout`/`stderr` + exit code |
| `[` / `]` | `action_resize_left` / `action_resize_right` | Shrink or expand `#left-panel` by 5% increments (clamped between `10%` and `90%`) |
| `?` | `action_show_resize_help` | Open `HelpModal` explaining pane resizing and layout presets |
| `ctrl+p` | Command Palette | Open Textual's system command palette with custom nested submenus |

## 4. Modal Screens
1. **`NewJobModal` (`ModalScreen[tuple]`):**
   - Two-column horizontal layout (`#form-area` on the left, `#help-area` on the right).
   - Accepts optional `initial_schedule`, `initial_cmd`, and `title` parameters so it serves both **New Job (`n`)** and **Edit Job (`e`)** workflows.
   - Validates schedule syntax via `CronManager.validate_schedule(schedule)` before dismissing, displaying an inline error notification if invalid.
   - Quick-action preset buttons (`@hourly`, `@midnight`, `@daily`, `@weekly`, `*/5 * * * *`) populate `#schedule-input` and advance focus to `#cmd-input`.
   - Right-hand static cheatsheet displays the 5-field cron diagram (`minute`, `hour`, `day of month`, `month`, `day of week`), common examples, and `@` shortcuts.
2. **`RestoreBackupModal` (`ModalScreen[Path | None]`):**
   - Split-pane dialog with `#backup-table` (`Timestamp`, `Jobs`, `File`) on the left and `#backup-preview` on the right showing the snapshot's raw crontab lines.
   - Restores the selected snapshot via `CronManager.restore_backup()` while backing up the current state first.
3. **`ConfirmActionModal` (`ModalScreen[bool]`):**
   - Reusable confirmation dialog parameterized by `title`, `prompt`, `action_name`, and button `variant` (`error`, `warning`, `success`).
   - Used for job deletion (`x`), pause/resume toggling (`p`), and force-run execution (`ctrl+r` when `confirm_force_run` is `True`).
4. **`HelpModal` (`ModalScreen`):**
   - Displays keyboard resizing instructions (`[` / `]`) and `ctrl+p` layout switching tips.

## 5. Nested Command Palette Architecture (Issues `#6` & `#7`)
- `CronDashboard.get_system_commands(screen)` yields 4-tuples `(name, help, callback, discover=True)` for:
  - `Cron Actions...` -> pushes `CommandPalette(providers=[CronCommandProvider])`
  - `Dashboard Settings...` -> pushes `CommandPalette(providers=[SettingCommandProvider])`
  - `UI Layouts...` -> pushes `CommandPalette(providers=[LayoutCommandProvider])`
- **Empty-Query Matcher Fix (`0405961` / Issue `#7`):** Each custom `Provider` implements `discover()` by delegating to `search("")`, and inside `search(query)` explicitly checks `if not query: yield Hit(1.0, ...)` before calling `matcher.match(...)`. This auto-populates all submenu options immediately upon opening the nested palette and avoids Textual's empty-query `ValueError`.
- **Structural Layout Switching (`action_set_layout`):** Supports four orientations in `LayoutCommandProvider`:
  - `Side-by-Side (List Left)` (`horizontal`, `swapped=False`)
  - `Side-by-Side (List Right)` (`horizontal`, `swapped=True`)
  - `Stacked (List Top)` (`vertical`, `swapped=False`)
  - `Stacked (List Bottom)` (`vertical`, `swapped=True`)
  - Uses `container.move_child(left, after=right)` / `before=right` (`38214a4`) and recalculates width/height percentages in `apply_layout()`.

## Related Pages
- [Cron Engine, A.I.M. Badging & Known Edge Cases](ai_agent_and_cron_engine.md)
- [Roadmap, Feature Audit & Issue History](roadmap_and_history.md)
