# Project Wiki Index

Persistent knowledge base for **aim-cron-dashboard** (`aim-cron`), a Python and Textual Terminal User Interface (TUI) for viewing, scheduling, pausing, and testing system `crontab` jobs and scheduled A.I.M. agents.

## Core Concepts
- [Cron Engine, A.I.M. Badging & Known Edge Cases](pages/ai_agent_and_cron_engine.md) — `crontab` parsing, `cron-descriptor` translation, timestamped backups, `[Ephemeral A.I.M. Agent]` / `[A.I.]` badging, detached Force Run execution, and audited parser/installer edge cases.

## Architecture
- [Core TUI Architecture](pages/architecture.md) — Structural breakdown of `bin/dashboard.py` and `bin/aim-cron`, including `CronDashboard`, `CronManager`, `NewJobModal`, `ConfirmActionModal`, dynamic pane resizing (`[` / `]`), structural layout switching, and nested Command Palette providers.

## Roadmap & Audit
- [Roadmap, Feature Audit & Issue History](pages/roadmap_and_history.md) — Completed milestones across Phases 1–6 (Issues `#1`–`#8`), sister-cockpit parity with `aim-tmux-dashboard`, and unimplemented v0.2+ wishlist items from `docs/AIM_CRON_FEATURE_AUDIT.md`.

## Operations Log
- [Memory Log](log.md) — Chronological record of wiki bootstrap and session ingestion events.
