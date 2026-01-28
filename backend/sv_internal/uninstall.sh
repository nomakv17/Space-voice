#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"

echo "Uninstalling sv_internal module..."

# Remove symlinks
echo "Removing frontend symlinks..."
rm -f "$FRONTEND_DIR/src/app/dashboard/income"
rm -f "$FRONTEND_DIR/src/lib/api/income.ts"

echo "Internal module frontend unlinked successfully"
echo ""
echo "To complete uninstallation, run from backend directory:"
echo "  pip uninstall sv-internal"
