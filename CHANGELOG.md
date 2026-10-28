# Changelog

## [v0.2.0] - 2026-10-28
### Added
- **In-Place Job Editing (`e`):** Pre-populates `NewJobModal` with the highlighted job and updates the targeted line index without colliding on duplicate cron entries (`#11`).
- **Backup Browser & Restore Modal (`u`):** Added `RestoreBackupModal`, `CronManager.list_backups()`, and `CronManager.restore_backup()` to preview and restore `~/.local/state/aim-cron-dashboard/backups/crontab.bak.*` snapshots (`#12`).
- **Force Run Output Capture & Persistent Settings:** Captures `stdout`/`stderr`, exit code, and `[RUNNING]`/`[OK]`/`[FAIL]` status during `Ctrl+R` Force Run, and persists UI preferences (`~/.config/aim-cron-dashboard/settings.json`, `#13`).
- **Schedule Validation & `@shortcut` Support:** Added support for `@reboot`, `@hourly`, `@midnight`, `@daily`, `@weekly`, `@monthly`, `@yearly`, `@annually`, filtered prose comments and `ENV=val` lines, and added `CronManager.validate_schedule()` (`#9`).
- **Command Palette Submenus & Layouts:** Added nested `CronCommandProvider`, `SettingCommandProvider`, and `LayoutCommandProvider` (`Side-by-Side` and `Stacked` orientations) with `[` / `]` pane resizing (`#5`, `#6`, `#7`).
- **A.I.M. Agent Badging & Safety Backups:** Added `🤖 [Ephemeral A.I.M. Agent]` and `[A.I.]` badging, detached Force Run (`Ctrl+R`), and automatic `crontab.bak.<timestamp>` snapshots before writes (`#4`).

### Fixed
- Fixed `install.sh` symlink target (`~/.local/bin/aim-cron`) and setup hint in `bin/aim-cron` (`#10`).
- Fixed empty-query `ValueError` in nested Command Palette providers (`#7`).
- Sanitized hardcoded paths in documentation for open-source readiness (`#8`, `#14`).

## [v0.1.0] - 2026-08-10
### Added
- Initial Textual UI cockpit (`bin/dashboard.py`), `CronManager.get_crontab()` with `cron-descriptor` human translation, and interactive CRUD (`NewJobModal`, delete `x`, pause/resume `#` toggle `p`, `#1`–`#3`).
