# A.I.M. Cron Dashboard ⏱️

A beautiful, fully-featured Terminal User Interface (TUI) for managing and monitoring your system's cron jobs. Built natively for the terminal using Python and the [Textual](https://github.com/Textualize/textual) framework.

## Features ✨

- **Modern TUI Dashboard:** Navigate your cron jobs with a sleek, responsive, and dark-themed terminal interface.
- **Human-Readable Cron:** Automatically translates complex cron syntax into plain English using `cron_descriptor`.
- **Command Palette:** Quick-access nested menus and actions directly from the keyboard.
- **Data Tables:** Easily sort, filter, and view execution histories or active schedules.

## Prerequisites 🛠️

- **Python 3.10+**
- A standard Linux/Unix environment

## Installation 🚀

1. **Clone the repository:**
   ```bash
   git clone https://github.com/BrianV1981/aim-cron-dashboard.git
   cd aim-cron-dashboard
   ```

2. **Set up the virtual environment:**
   The dashboard runs safely inside its own isolated Python environment.
   ```bash
   python3 -m venv venv
   ./venv/bin/pip install --upgrade pip
   ./venv/bin/pip install textual cron-descriptor
   ```

3. **Install Globally (Optional):**
   To launch the dashboard from anywhere on your system, create a symlink to your local bin directory:
   ```bash
   mkdir -p ~/.local/bin
   ln -sf $(pwd)/bin/aim-cron ~/.local/bin/aim-cron
   ```

## Usage 💻

Simply run the launcher script from the repository:

```bash
./bin/aim-cron
```

Or, if you created the global symlink in the previous step:

```bash
aim-cron
```

## Contributing 🤝

Contributions, issues, and feature requests are welcome! Currently tracking open UI/UX refactor tickets (see [Issue #7](https://github.com/BrianV1981/aim-cron-dashboard/issues/7)).
