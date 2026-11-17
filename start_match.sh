#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
exec "${PYTHON:-python3}" start_match.py "$@"
