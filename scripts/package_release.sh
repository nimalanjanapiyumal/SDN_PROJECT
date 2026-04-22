#!/usr/bin/env bash
set -euo pipefail
VERSION="${1:-v0.1.0}"
mkdir -p release
OUTDIR="release/adaptive_cloud_sdn_complete-${VERSION}"
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' ./ "$OUTDIR"/
TARFILE="${OUTDIR}.tar.gz"
tar -czf "$TARFILE" -C release "$(basename "$OUTDIR")"
sha256sum "$TARFILE" > "${TARFILE}.sha256"
echo "Created $TARFILE"
