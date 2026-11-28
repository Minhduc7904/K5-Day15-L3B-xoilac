#!/bin/sh

# Vercel skips on exit 0. Build when the Git baseline is unavailable.
if [ -z "${VERCEL_GIT_COMMIT_SHA:-}" ]; then
  exit 1
fi

baseline="${VERCEL_GIT_PREVIOUS_SHA:-}"
if [ -z "$baseline" ]; then
  # The first Git deployment on main establishes the production baseline.
  if [ "${VERCEL_GIT_COMMIT_REF:-}" = main ]; then
    exit 1
  fi

  # A new preview branch has no previous deployment to compare against.
  # Vercel's checkout may not have a remote configured.
  remote=$(git remote get-url origin 2>/dev/null) ||
    remote=https://github.com/Minhduc7904/K5-Day15-L3B-xoilac.git
  git fetch --quiet --no-tags --depth=50 "$remote" main || exit 1
  baseline=$(git merge-base HEAD FETCH_HEAD) || exit 1
fi

git cat-file -e "$baseline^{commit}" 2>/dev/null || exit 1

if git diff --quiet "$baseline" HEAD -- ':(top)frontend/'; then
  exit 0
fi
exit 1
