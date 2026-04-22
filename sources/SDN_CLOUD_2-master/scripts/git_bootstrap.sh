#!/usr/bin/env bash
set -euo pipefail

BRANCH_NAME="${1:-main}"
REMOTE_URL="${2:-}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "${ROOT_DIR}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is not installed. Install git first."
  exit 1
fi

if ! git config --global user.name >/dev/null 2>&1 || ! git config --global user.email >/dev/null 2>&1; then
  echo "Git user identity is not configured. Run:"
  echo '  git config --global user.name "Your Name"'
  echo '  git config --global user.email "you@example.com"'
  exit 1
fi

if [[ ! -d .git ]]; then
  git init
fi

git add .

if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  git commit -m "Initial commit: SDN adaptive cloud framework"
fi

git branch -M "${BRANCH_NAME}"

if [[ -n "${REMOTE_URL}" ]]; then
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "${REMOTE_URL}"
  else
    git remote add origin "${REMOTE_URL}"
  fi
  git push -u origin "${BRANCH_NAME}"
fi

echo "Git bootstrap complete."
git status --short || true
git remote -v || true
