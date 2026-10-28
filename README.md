# ⏱️ aim-cron-dashboard (`aim-cron`)

## 📖 Overview

A modern, terminal-based dashboard for managing, inspecting, and testing your system's `crontab` schedules and scheduled AI agents. Built with Python [Textual](https://github.com/Textualize/textual) and [`cron-descriptor`](https://github.com/Salamek/cron-descriptor), it serves as the sister TUI cockpit to **[aim-tmux-dashboard](https://github.com/BrianV1981/aim-tmux-dashboard)**.

## ✨ Features

* **Human-Readable Cron Translation:** Automatically translates 5-field cron expressions and `@shortcut` nicknames (`@reboot`, `@hourly`, `@midnight`, `@daily`, `@weekly`, `@monthly`, `@yearly`, `@annually`) into plain English.
* **Interactive CRUD & Schedule Validation:** Create (`n`), edit in place (`e`), pause/resume (`p`), and delete (`x`) cron jobs with built-in syntax validation, quick-select preset buttons, and a side-by-side cron cheatsheet.
* **Automatic Crontab Backups & Time-Machine Restore (`u`):** Automatically snapshots your crontab to `~/.local/state/aim-cron-dashboard/backups/crontab.bak.<timestamp>` before every write, with an interactive split-pane modal (`u`) to preview and restore past snapshots.
* **Detached Force Run with Live Output Capture (`Ctrl+R`):** Execute any highlighted cron command on demand in a detached background session and view its live `[RUNNING]` / `[OK]` / `[FAIL]` badge, exit code, and `stdout`/`stderr` output right in the preview panel.
* **AI Agent Badging:** Automatically detects scheduled A.I.M. / `tmux` agent jobs (`🤖 [Ephemeral A.I.M. Agent]`) and AI CLI vessels (`[A.I.]` for `agy`, `grok`, `codex`, `claude`, `aider`, `gemini`, `opencode`).
* **Customizable Layouts & Persistent Settings:** Switch between 4 structural orientations (`Side-by-Side Left/Right`, `Stacked Top/Bottom`), dynamically resize split panes (`[` / `]`), and toggle UI preferences persisted in `~/.config/aim-cron-dashboard/settings.json`.

## 🛠️ Prerequisites

* **Python 3.10+**
* A standard Linux/Unix environment with `crontab`

## 🚀 Installation

### Quick Install (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/BrianV1981/aim-cron-dashboard.git
   cd aim-cron-dashboard
   ```
2. Run the installer script (creates `venv`, installs `requirements.txt`, and symlinks `aim-cron` to `~/.local/bin/aim-cron`):
   ```bash
   ./install.sh
   ```
3. Launch the dashboard from any terminal:
   ```bash
   aim-cron
   ```
   *(Or run directly from the repo with `./bin/aim-cron`.)*

### Manual Setup

```bash
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
mkdir -p ~/.local/bin
ln -sf "$(pwd)/bin/aim-cron" ~/.local/bin/aim-cron
```

## ⌨️ Usage & Keybindings

### Main Dashboard Shortcuts

| Keybinding | Action |
| :--- | :--- |
| `n` | Open **New Cron Job** modal (with schedule presets and cron syntax cheatsheet) |
| `e` | **Edit** the highlighted cron job in place |
| `p` | **Pause / Resume** the highlighted cron job (`#` toggle) |
| `x` | **Delete** the highlighted cron job (with confirmation dialog) |
| `u` | Open **Restore Crontab Backup** modal to preview and restore a saved snapshot |
| `Ctrl+R` | **Force Run** the highlighted job in the background and capture `stdout`/`stderr` + exit code |
| `/` | Focus the live search input to filter jobs (`Enter` returns focus to the table) |
| `[` / `]` | Shrink / expand the job list split pane (`10%`–`90%`) |
| `r` | Reload the system `crontab` into the table |
| `?` | Open the panel resizing and layout help dialog |
| `Ctrl+P` | Open the **Command Palette** (`Cron Actions...`, `Dashboard Settings...`, `UI Layouts...`) |
| `q` | Quit dashboard |

### Command Palette (`Ctrl+P`) Submenus

| Submenu | Options |
| :--- | :--- |
| **Cron Actions...** | `New Job`, `Edit Job`, `Restore Backup`, `Refresh Table`, `Force Run Job`, `Delete Job`, `Toggle Pause/Resume` |
| **Dashboard Settings...** | `Toggle A.I.M. Badges [ON/OFF]`, `Toggle Force Run Warning [ON/OFF]`, `Help: How to resize panels` |
| **UI Layouts...** | `Side-by-Side (List Left)`, `Side-by-Side (List Right)`, `Stacked (List Top)`, `Stacked (List Bottom)` |

## 🗂️ Local Storage Paths

* **Crontab Backups:** `~/.local/state/aim-cron-dashboard/backups/crontab.bak.<YYYYMMDD_HHMMSS>`
* **UI Settings:** `~/.config/aim-cron-dashboard/settings.json`

---

### 🧬 The A.I.M. Ecosystem

For the up-to-date map of the A.I.M. Ecosystem, please visit the **[aim-ecosystem](https://github.com/BrianV1981/aim-ecosystem)** repository or the flagship OS, **[aim-joshua](https://github.com/BrianV1981/aim-joshua)**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
☕ **Support the project:** [Buy Me a Coffee](https://buymeacoffee.com/brianv1981)
