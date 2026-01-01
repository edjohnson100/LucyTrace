#!/bin/bash
# LucyTrace: Turn "Ruff Drafts" into the "Director's Cut"
cd "$(dirname "$0")"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    read -p "Press Enter to exit..."
    exit 1
fi

# Activate venv if exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# --- Interactive Menu ---
echo ""
echo "=========================================="
echo "  LUCYTRACE"
echo "  Turn 'Ruff Drafts' into the 'Director's Cut'"
echo "=========================================="
echo ""
echo "Select Processing Profile:"
echo ""
echo "  [1] BASE (Fast)"
echo "      - Simple thresholding."
echo "      - Best for clean black & white line art."
echo ""
echo "  [2] ADVANCED (Smart)"
echo "      - Auto-levels, saturation detection."
echo "      - Best for photos, gray scans, or comics."
echo ""
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    ARGS="--profile base"
else
    ARGS="--profile adv"
fi

echo ""
echo "Running LucyTrace with $ARGS..."
echo ""

# Run Python
python3 lucytrace.py $ARGS

echo ""
echo "Processing complete. Press Enter to exit..."
read