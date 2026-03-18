#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${HOME}/.local/bin"
TARGET="${TARGET_DIR}/floaty"

mkdir -p "${TARGET_DIR}"
ln -sfn "${ROOT_DIR}/floaty" "${TARGET}"

cat <<EOF
Installed user command:
${TARGET}

If '${TARGET_DIR}' is not on PATH, add this to your shell config:
export PATH="\$HOME/.local/bin:\$PATH"
EOF
