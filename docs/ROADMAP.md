# A.I.M. Cron Dashboard: Roadmap

**ATTENTION INCOMING AGENT:** 
You are building `aim-cron-dashboard`. This is a "sister project" to the Operator's existing tool, `aim-tmux-dashboard` (located at `/home/kingb/aim-tmux-dashboard`). 
**DO NOT build a UI from scratch.** Your very first action must be to copy the Textual UI shell, CSS, and aesthetic design from `aim-tmux-dashboard`. We want both tools to feel like identical twin cockpits in the A.I.M. ecosystem.

---

## Phase 1: The UI Shell Clone (MVP Foundation)
1. **Scaffold the Repo:** Copy `bin/dashboard.py` and the surrounding package structure from `/home/kingb/aim-tmux-dashboard`.
2. **Rip and Replace:** Delete the `TmuxManager` class. Delete the tree view that renders tmux sessions.
3. **The Base UI:** Replace the left tree with a `DataTable` or `ListView` designed to hold cronjobs. Keep the cyan `[A.I.]` color palette and dark mode aesthetics.

## Phase 2: The Cron Engine (Read-Only)
1. **System Crontab:** Build a `CronManager` class that uses `subprocess.run(["crontab", "-l"])` to read the current user's system cron.
2. **Human Translation:** Add `cron-descriptor` to the `requirements.txt`. Use it to translate raw syntax (`0 4 * * *`) into human-readable strings ("Runs every day at 4:00 AM") in the UI.
3. **Display:** Render the parsed cron jobs cleanly into the UI grid.

## Phase 3: Interactive Management (CRUD)
1. **New Job Modal (Hotkey `n`):** Build a Textual Modal that asks for a schedule string and a bash command. Use `subprocess` to securely append it to the crontab.
2. **Delete Job (Hotkey `x`):** Allow the user to highlight a job and delete it from the system crontab.
3. **Pause/Resume Toggle (Hotkey `p`):** When pressed, edit the `crontab` file to prepend a `#` (comment) to the job, effectively pausing it. Pressing `p` again removes the `#` to resume it.

## Phase 4: A.I.M. Polish (v0.2 Features)
*Refer to `AIM_CRON_FEATURE_AUDIT.md` for full details.*
1. **Agent Badging:** If a cronjob command contains `tmux new-session`, badge it in the UI with a 🤖 or ⏰ emoji to denote an "Ephemeral A.I.M. Agent."
2. **Force Run (Hotkey `r`):** Instantly execute the highlighted job's command in the background for testing.
3. **Safety Backups:** Before performing any writes to the crontab, save a backup copy (e.g., `crontab.bak.<timestamp>`).

---
**CRITICAL DIRECTIVE:** Do not attempt to build Phase 3 or Phase 4 until Phase 1 and Phase 2 are empirically proven to work. Stay focused on the MVP.
