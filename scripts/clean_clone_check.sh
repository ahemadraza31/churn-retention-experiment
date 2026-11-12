#!/usr/bin/env bash
# scripts/clean_clone_check.sh
# Verifies end-to-end clean clone, setup, health, all-starter generation, tests, and bitwise data parity.

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <repo path or URL> [python executable]"
    exit 1
fi

REPO_SRC="$1"
PYTHON_BIN="${2:-python3.11}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
    else
        echo "ERROR: Python interpreter '$PYTHON_BIN' not found."
        exit 1
    fi
fi

TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/churnexp_clean_clone.XXXXXXXX")
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=================================================="
echo "Starting Clean Clone Verification"
echo "Repository : $REPO_SRC"
echo "Python     : $PYTHON_BIN"
echo "Temp Dir   : $TMP_DIR"
echo "=================================================="

# Step 1: Clone
echo "[1/6] Cloning repository into temp directory..."
if git clone --quiet "$REPO_SRC" "$TMP_DIR/repo"; then
    echo "  -> CLONE: PASS"
else
    echo "  -> CLONE: FAIL"
    exit 1
fi

cd "$TMP_DIR/repo"

# Step 2: Environment setup & dependencies
echo "[2/6] Creating virtual environment and installing packages..."
if "$PYTHON_BIN" -m venv .venv && \
   .venv/bin/pip install --quiet --upgrade pip && \
   .venv/bin/pip install --quiet -r requirements.txt && \
   .venv/bin/pip install --quiet -e .; then
    echo "  -> SETUP: PASS"
else
    echo "  -> SETUP: FAIL"
    exit 1
fi

# Step 3: Health check
echo "[3/6] Running health check..."
if .venv/bin/python -m churnexp health --scale starter >/dev/null; then
    STEP_HEALTH="PASS"
else
    STEP_HEALTH="FAIL"
fi
echo "  -> HEALTH: $STEP_HEALTH"

# Step 4: Run full starter pipeline
echo "[4/6] Running full pipeline ('all') at starter scale..."
if .venv/bin/python -m churnexp all --scale starter >/dev/null; then
    STEP_ALL="PASS"
else
    STEP_ALL="FAIL"
fi
echo "  -> ALL STARTER: $STEP_ALL"

# Step 5: Run pytest test suite
echo "[5/6] Running pytest test suite..."
if .venv/bin/pytest -q >/dev/null; then
    STEP_TEST="PASS"
else
    STEP_TEST="FAIL"
fi
echo "  -> PYTEST: $STEP_TEST"

# Step 6: Git data diff check (deterministic byte-identical parity)
echo "[6/6] Checking git status on committed starter data..."
if git diff --quiet -- data/starter/csv data/starter/json data/starter/sql data/starter/ground_truth; then
    STEP_DIFF="PASS"
else
    STEP_DIFF="FAIL"
fi
echo "  -> DATA PARITY: $STEP_DIFF"

echo ""
echo "=================================================="
echo "Clean Clone Verification Summary"
echo "=================================================="
echo "  Clone & Setup : PASS"
echo "  Health Check  : $STEP_HEALTH"
echo "  Pipeline All  : $STEP_ALL"
echo "  Test Suite    : $STEP_TEST"
echo "  Data Parity   : $STEP_DIFF"
echo "=================================================="

if [[ "$STEP_HEALTH" == "PASS" && "$STEP_ALL" == "PASS" && "$STEP_TEST" == "PASS" && "$STEP_DIFF" == "PASS" ]]; then
    echo "OVERALL: PASS"
    exit 0
else
    echo "OVERALL: FAIL"
    exit 1
fi

