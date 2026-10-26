#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "Setting up aim-cron-dashboard virtual environment..."
cd "$DIR"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create symlink
echo "Creating symlink in ~/.local/bin..."
mkdir -p ~/.local/bin
ln -sf "$DIR/bin/aim-cron" ~/.local/bin/aim-cron

echo "aim-cron-dashboard installed successfully."
echo "Make sure ~/.local/bin is in your PATH."
