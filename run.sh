#!/usr/bin/env bash
set -euo pipefail

# Resolve project root (script location)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

echo "Project root: $ROOT_DIR"

# Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
	echo "Creating virtual environment at $VENV_DIR..."
	python -m venv "$VENV_DIR"
fi

# Activate venv (support POSIX and Git Bash on Windows)
if [ -f "$VENV_DIR/bin/activate" ]; then
	# shellcheck disable=SC1090
	source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
	# Git Bash / MSYS
	# shellcheck disable=SC1090
	source "$VENV_DIR/Scripts/activate"
else
	echo "Warning: could not find activate script in $VENV_DIR"
fi

echo "Using Python: $(python -V 2>&1)"

# Ensure pip and install requirements if present
python -m pip install --upgrade pip
if [ -f "$ROOT_DIR/requirements.txt" ]; then
	pip install -r "$ROOT_DIR/requirements.txt"
fi

echo "Starting uvicorn..."
exec uvicorn api.main:app --reload

