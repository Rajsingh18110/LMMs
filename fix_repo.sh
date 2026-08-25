#!/bin/bash
rm -rf build/ dist/ *.egg-info __pycache__/ || true
git fetch origin main || true
git stash
# Force head exactly to where we want it to be to fix the git state
git reset --hard origin/main
