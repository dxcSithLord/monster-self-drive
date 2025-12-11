#!/bin/bash
# verify-dependencies.sh
# Verifies all vendored dependencies against known checksums
#
# Usage: ./scripts/verify-dependencies.sh
#
# Exit codes:
#   0 - All dependencies verified
#   1 - Checksum mismatch or missing file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "MonsterBorg Dependency Verification"
echo "===================================="
echo ""

# Track failures
FAILURES=0

# Function to verify a file
verify_file() {
    local file="$1"
    local expected_sha256="$2"
    local name="$3"

    local full_path="$PROJECT_ROOT/$file"

    if [ ! -f "$full_path" ]; then
        echo "✗ $name: FILE NOT FOUND"
        echo "  Path: $file"
        FAILURES=$((FAILURES + 1))
        return
    fi

    local actual_sha256=$(sha256sum "$full_path" | cut -d' ' -f1)

    if [ "$expected_sha256" = "$actual_sha256" ]; then
        echo "✓ $name: OK"
    else
        echo "✗ $name: CHECKSUM MISMATCH"
        echo "  Expected: $expected_sha256"
        echo "  Actual:   $actual_sha256"
        FAILURES=$((FAILURES + 1))
    fi
}

echo "Verifying vendored JavaScript dependencies..."
echo ""

# Socket.IO client 4.8.1 (latest stable, includes CVE-2024-38355 fix)
verify_file \
    "src/web/static/js/vendor/socket.io-4.8.1.min.js" \
    "b0e735814f8dcfecd6cdb8a7ce95a297a7e1e5f2727a29e6f5901801d52fa0c5" \
    "socket.io-client 4.8.1"

echo ""
echo "Checking for external runtime URLs in templates..."
echo ""

# Check for external URLs in templates and static files
EXTERNAL_URLS=$(grep -rE "https?://[^\"']*" \
    "$PROJECT_ROOT/src/web/templates/" \
    "$PROJECT_ROOT/src/web/static/" \
    2>/dev/null | grep -v "^#" | grep -v "localhost" | grep -v "127.0.0.1" || true)

if [ -n "$EXTERNAL_URLS" ]; then
    echo "✗ External URLs found in web assets:"
    echo "$EXTERNAL_URLS"
    FAILURES=$((FAILURES + 1))
else
    echo "✓ No external runtime URLs in web assets"
fi

echo ""
echo "===================================="

if [ $FAILURES -eq 0 ]; then
    echo "All dependencies verified successfully."
    exit 0
else
    echo "FAILED: $FAILURES verification(s) failed."
    exit 1
fi
