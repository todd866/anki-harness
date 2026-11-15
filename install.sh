#!/bin/sh
# Install one released Anki version (from PyPI) into its own environment.
#   ./install.sh 26.9.4
# Needs uv (https://docs.astral.sh/uv/). A few hundred MB per version, mostly Qt.
set -eu
V="$1"
HOME_DIR="${ANKI_HARNESS_HOME:-$HOME/.local/state/anki-harness}"
ENV="$HOME_DIR/env-$V"
mkdir -p "$HOME_DIR"
[ -x "$ENV/bin/python" ] || uv venv --quiet --python 3.13 "$ENV"
uv pip install --quiet --python "$ENV/bin/python" "aqt==$V" "anki==$V"
"$ENV/bin/python" -c 'import anki.buildinfo as b; print("installed Anki", b.version)'
