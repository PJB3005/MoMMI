#!/usr/bin/env bash
# Get dir containing script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
source venv/bin/activate
python3 main.py
