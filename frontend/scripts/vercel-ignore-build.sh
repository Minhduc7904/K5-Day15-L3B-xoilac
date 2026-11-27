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
  git fetch --quiet --no-tags --depth=50 origin main || exit 1
  baseline=$(git merge-base HEAD FETCH_HEAD) || exit 1
fi

git diff --quiet "$baseline" HEAD -- ':(top)frontend/'
