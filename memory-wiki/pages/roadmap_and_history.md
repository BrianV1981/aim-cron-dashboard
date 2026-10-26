# Roadmap, Feature Audit & Issue History

## 1. Completed Milestones (Issues `#1`–`#8`)
All 8 initial GitHub issues in `BrianV1981/aim-cron-dashboard` have been resolved and closed on `main`:

| Issue / Phase | Commit(s) | Summary | Status |
|---------------|-----------|---------|--------|
| **#1 — Phase 1: UI Shell Clone** | `f94fe71`, `6a7a842` | Cloned Textual cockpit structure from `~/aim-tmux-dashboard`, stripped `TmuxManager`, and replaced session tree with cron `DataTable`. | ✅ CLOSED |
| **#2 — Phase 2: Cron Engine (Read-Only)** | `f94fe71` | Implemented `CronManager.get_crontab()` wrapping `crontab -l` and `cron-descriptor` human-readable schedule descriptions. | ✅ CLOSED |
| **#3 — Phase 3: Interactive CRUD** | `c2745ab`, `503fef9`, `ce7cea7` | Added `NewJobModal` (`n`) with cron cheatsheet, examples, and `@hourly`/`@midnight`/`@daily`/`@weekly`/`*/5` preset buttons; Delete (`x`); and Pause/Resume (`p`) `#` commenting. | ✅ CLOSED |
| **#4 — Phase 4: A.I.M. Polish (v0.2)** | `0aeb8bb`, `2b4117c` | Added `🤖 [Ephemeral A.I.M. Agent]` (`tmux new-session`) and `[A.I.]` badging, detached Force Run (`ctrl+r`) with confirmation modal, and automatic `crontab.bak.<timestamp>` backups in `~/.local/state/aim-cron-dashboard/backups/`. | ✅ CLOSED |
| **#5 — Phase 5: UI Aesthetic Facelift** | `c32c383`, `bcf9ff9`, `d6e82ab` | Rounded cyan/accent focus borders, floating dialog styling, and custom Command Palette actions/settings. | ✅ CLOSED |
| **#6 — Phase 6: Layout Management & Themes** | `7e67f52`, `891d5c8`, `38214a4` | Registered `aim-dark` theme, added `[` / `]` dynamic pane resizing with `HelpModal` (`?`), and structural layout switching (`Side-by-Side` & `Stacked`) via `container.move_child`. | ✅ CLOSED |
| **#7 — Command Palette Submenus & Matcher Fix** | `1eff1c6`, `db1809c`, `0405961` | Refactored Command Palette to native nested submenus (`get_system_commands` 4-tuple) and bypassed Textual's empty-query `ValueError` by yielding `Hit(1.0, ...)` when `query` is empty. | ✅ CLOSED |
| **Packaging & Docs** | `12a45ba`, `759ed1f` | Renamed launcher from `bin/aim-dash` to `bin/aim-cron`, updated `.gitignore`, and authored `README.md`. | ✅ SHIPPED |
| **#8 — Shareability Path Scrub** | `efc65df` | Replaced hardcoded `/home/kingb/aim-tmux-dashboard` path with `~/aim-tmux-dashboard` in `docs/ROADMAP.md`. | ✅ CLOSED |

## 2. Unimplemented Feature Wishlist (`docs/AIM_CRON_FEATURE_AUDIT.md`)
From the master feature audit comparing `aim-cron-dashboard` against Cronboard, Crontab-UI, Cronmaster, Cronpilot, and Cronn, the following capabilities remain candidates for future releases:

1. **In-Place Job Editing (`e` hotkey):** Pre-populate `NewJobModal` (or an `EditJobModal`) with the highlighted job's schedule and command to modify an existing entry in place.
2. **Backup Undo / Restore Modal:** TUI modal to browse `~/.local/state/aim-cron-dashboard/backups/crontab.bak.*` and restore a previous crontab snapshot with one key.
3. **Syntax Validation:** Validate 5-field cron expressions and `@` nicknames before writing to `crontab -` so invalid schedules cannot cause `crontab` subprocess errors.
4. **Live Logging & Execution History:** Optional wrapper or log viewer modal to inspect `stdout`/`stderr` and exit status badges (`[OK]` / `[FAIL]`) of recent cron runs.
5. **Persistent Dashboard Settings:** Persist `show_ai_badges`, `confirm_force_run`, `left_panel_size`, and layout orientation to `~/.config/aim-cron-dashboard/config.json` (or `~/.aim_cron_dashboard.json`).
6. **Agy / J.O.S.H.U.A. Bridge & Remote SSH Orchestration:** Cross-referencing system cron jobs with internal daemon schedules or managing remote crontabs over SSH.

## Related Pages
- [Core TUI Architecture](architecture.md)
- [Cron Engine, A.I.M. Badging & Known Edge Cases](ai_agent_and_cron_engine.md)
