# A.I.M. Cron Dashboard: Feature Audit & Wishlist

This document serves as the master feature audit for a potential `aim-cron-dashboard` TUI project. It aggregates features from the top open-source cron managers (Cronboard, Crontab-UI, Cronmaster, Cronpilot, Cronn) to define every possible capability we might want to implement.

## 1. Core Crontab Management (The Baseline)
*   **Visual Grid/List:** Display all jobs in a clear, interactive Textual `DataTable` or `ListView`.
*   **CRUD Operations:** Add, Edit, Delete cron jobs without touching the raw text file.
*   **Pause / Resume (Toggle):** A one-key toggle (e.g., `p`) to instantly comment out a job in the crontab and pause it, or uncomment it to resume.
*   **Human-Readable Translation:** Automatically parse raw cron syntax (`0 4 * * *`) into plain English ("Runs every day at 4:00 AM") using a library like `cron-descriptor`.

## 2. Advanced Execution & Monitoring
*   **Ad-Hoc Execution (Force Run):** A hotkey to manually trigger a cron job *right now*, regardless of its schedule, to test if the script actually works.
*   **Live Logging:** Capture `stdout` and `stderr` of the cron jobs. Provide a "View Logs" modal to see the real-time output of a job as it runs (similar to Cronmaster).
*   **Execution History:** Track the Success/Failure (exit codes) of the last N runs, displaying a green `[OK]` or red `[FAIL]` badge next to the job.
*   **Conditional Execution (Resource Gating):** *Inspired by Cronn.* Before a job fires, check system resources. e.g., "Only run if CPU < 50% and RAM < 80%." If the server is struggling, skip the job to prevent a crash.

## 3. Remote & Distributed Orchestration
*   **Remote SSH Management:** *Inspired by Cronboard.* The ability to connect the dashboard to remote servers via SSH, parse their crontabs, and manage them from a single local TUI.
*   **Multi-Server Sync:** Push a specific cron job template to multiple remote nodes simultaneously.

## 4. Safety & Administration
*   **Automated Backups:** Every time a user adds, edits, or deletes a job via the UI, automatically save a timestamped backup of the `crontab` file (e.g., `crontab.bak.2026-07-14`).
*   **Undo/Restore:** A one-key rollback to instantly restore the crontab to the previous backup state if a mistake is made.
*   **Syntax Validation:** Prevent the user from saving a job if the cron expression or bash command contains severe syntax errors.

## 5. Alerts & Notifications
*   **Push Notifications:** *Inspired by Cronpilot & Healthchecks.* Native integration with lightweight Webhooks (like Discord, Slack, or ntfy) to ping the user's phone if a critical scheduled agent fails to report in.
*   **Silent Mode:** Ability to mute specific noisy jobs from sending execution alerts.

## 6. A.I.M. Specific Integrations (The Secret Sauce)
*   **Agent Badging:** Allow the user to assign custom Emojis or Tags (e.g., 🤖, 🕷️, ⏰) to specific cronjobs for visual organization.
*   **Tmux-Awareness:** A visual indicator that detects if a cronjob's command contains `tmux new-session`. If it does, automatically badge it as an "Ephemeral Agent."
*   **Agy Bridge (Optional):** A hidden feature to read the `.gemini/antigravity-cli` logs to cross-reference system cron jobs with internal Antigravity daemon tasks.

---

### Implementation Strategy
We will not build all of these for v0.1.0 to avoid scope creep. 
The recommended path is to clone the `aim-tmux-dashboard` UI shell, strip out Tmux, and implement **Section 1 (Core)** and the **Pause/Resume Toggle** as the Minimum Viable Product (MVP).
