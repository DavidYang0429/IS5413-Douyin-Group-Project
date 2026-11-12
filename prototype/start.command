#!/bin/zsh
set -e
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
if [[ ! -f .local/connection.json ]]; then
  print 'Database credentials are not configured. Follow prototype/README.md to provision a fresh project.'
  exit 1
fi
exec .venv/bin/python app.py
