# Roadmap, Feature Audit & Issue History

## 1. Completed Milestones (Issues `#1`–`#13`)
All 13 GitHub issues in `BrianV1981/aim-cron-dashboard` have been resolved and closed on `main`:

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
| **#9 — `@shortcut` Parser, Comment Filter & Validation** | `c54af8e` | Added `@shortcut` 2-token schedule parsing, prose comment & `ENV=val` filtering, `CronManager.validate_schedule()` bounds checking, and unit test suite (`tests/test_cron_manager.py`). | ✅ CLOSED |
| **#10 — Installer Symlink & Venv Hint Fix** | `73c7f62` | Updated `install.sh` to symlink `bin/aim-cron -> ~/.local/bin/aim-cron`, updated `bin/aim-cron` setup hint to `./install.sh`, and added `tests/test_install_scripts.py`. | ✅ CLOSED |
| **#11 — In-Place Job Editing (`e`) & Line-Index Targeting** | `e15e431` | Added `CronManager.edit_job()`, `line_index` targeting for edit/delete/toggle, pre-populated `NewJobModal`, and hotkey `e` (`Edit Job`). | ✅ CLOSED |
| **#12 — Backup Restore Modal (`u`)** | `50aaa18` | Added `CronManager.list_backups()`, `CronManager.restore_backup()`, and `RestoreBackupModal` (`u` hotkey & Command Palette). | ✅ CLOSED |
| **#13 — Persistent Settings & Force Run Output Capture** | `49ea549` | Added `~/.config/aim-cron-dashboard/settings.json` persistence and background `Force Run` output/exit-code capture with `[RUNNING]` / `[OK]` / `[FAIL]` badges. | ✅ CLOSED |

## 2. Remaining Optional Wishlist Items (`docs/AIM_CRON_FEATURE_AUDIT.md`)
From the master feature audit comparing `aim-cron-dashboard` against Cronboard, Crontab-UI, Cronmaster, Cronpilot, and Cronn, only advanced distributed/webhook items remain optional candidates for future versions:

1. **Conditional Execution (Resource Gating):** Optional wrapper to check CPU/RAM thresholds before firing a heavy cron job.
2. **Webhook / Push Notifications:** Optional Discord, Slack, or `ntfy` webhook integration on non-zero cron exit codes.
3. **Remote SSH Crontab Orchestration:** Connect to remote hosts over SSH to view/edit remote crontabs from the local TUI.
4. **Agy / J.O.S.H.U.A. Bridge:** Cross-reference system cron jobs with internal daemon schedules.

## Related Pages
- [Core TUI Architecture](architecture.md)
- [Cron Engine, A.I.M. Badging & Known Edge Cases](ai_agent_and_cron_engine.md)
