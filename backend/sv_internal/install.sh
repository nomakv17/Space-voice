#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"

echo "Installing sv_internal module..."

# Install recharts for charts
echo "Installing recharts..."
cd "$FRONTEND_DIR"
npm install recharts

# Create symlinks for frontend files
echo "Creating frontend symlinks..."
ln -sfn "$SCRIPT_DIR/frontend/income" "$FRONTEND_DIR/src/app/dashboard/income"
ln -sfn "$SCRIPT_DIR/frontend/lib/api/income.ts" "$FRONTEND_DIR/src/lib/api/income.ts"

echo "Internal module frontend linked successfully"
echo ""
echo "To complete installation, run from backend directory:"
echo "  pip install -e ../sv_internal"
