#!/bin/bash
# MonsterBorg Release Script
# Creates a Git tag and prepares release notes
#
# Usage: ./scripts/release.sh <version> [--push]
#   <version>: Semantic version (e.g., 1.0.0, 1.0.0-beta.1)
#   --push: Push tag to remote after creation
#
# Example:
#   ./scripts/release.sh 1.0.0
#   ./scripts/release.sh 1.0.0 --push

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Parse arguments
VERSION="$1"
PUSH_TAG=false

if [[ -z "$VERSION" ]]; then
    echo "Usage: $0 <version> [--push]"
    echo ""
    echo "Examples:"
    echo "  $0 1.0.0           # Create tag v1.0.0"
    echo "  $0 1.0.0 --push    # Create and push tag"
    echo "  $0 1.0.0-beta.1    # Pre-release tag"
    exit 1
fi

if [[ "$2" == "--push" ]]; then
    PUSH_TAG=true
fi

# Validate semantic version format
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    error "Invalid version format: $VERSION (expected: X.Y.Z or X.Y.Z-suffix)"
fi

TAG_NAME="v${VERSION}"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    error "Uncommitted changes detected. Commit or stash before releasing."
fi

# Check if tag already exists
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    error "Tag $TAG_NAME already exists"
fi

info "Creating release $TAG_NAME"

# Generate release notes from recent commits
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

echo ""
info "Generating release notes..."

RELEASE_NOTES_FILE=$(mktemp)
{
    echo "# Release $TAG_NAME"
    echo ""
    echo "## What's Changed"
    echo ""

    if [[ -n "$LAST_TAG" ]]; then
        git log "${LAST_TAG}..HEAD" --pretty=format:"- %s" --no-merges | head -50
    else
        git log --pretty=format:"- %s" --no-merges | head -20
    fi

    echo ""
    echo ""
    echo "## Installation"
    echo ""
    echo "1. Clone the repository:"
    echo "   \`\`\`bash"
    echo "   git clone https://github.com/dxcSithLord/monster-self-drive.git"
    echo "   cd monster-self-drive"
    echo "   git checkout $TAG_NAME"
    echo "   \`\`\`"
    echo ""
    echo "2. Run the install script:"
    echo "   \`\`\`bash"
    echo "   ./scripts/install.sh"
    echo "   \`\`\`"
    echo ""
    echo "3. Access web interface at \`http://<pi-ip>:8080\`"
    echo ""
    echo "## Requirements"
    echo ""
    echo "- Raspberry Pi 3B or newer"
    echo "- Raspberry Pi OS (Debian Trixie / Bookworm)"
    echo "- Python 3.11+"
    echo "- ThunderBorg motor controller"
    echo "- Pi Camera Module"
    echo ""
    echo "## Configuration"
    echo ""
    echo "The install script will prompt for configuration. Key settings:"
    echo "- Web bind address (0.0.0.0 for network access)"
    echo "- Web port (default: 8080)"
    echo "- Battery cell count (for voltage calculations)"
    echo "- Camera orientation (flipped or normal)"
    echo ""

} > "$RELEASE_NOTES_FILE"

echo ""
echo "========== Release Notes =========="
cat "$RELEASE_NOTES_FILE"
echo "===================================="
echo ""

# Confirm
read -r -p "Create tag $TAG_NAME with these notes? [y/N]: " confirm
if [[ ! "$confirm" =~ ^[Yy] ]]; then
    rm -f "$RELEASE_NOTES_FILE"
    info "Release cancelled"
    exit 0
fi

# Create annotated tag
git tag -a "$TAG_NAME" -F "$RELEASE_NOTES_FILE"
success "Tag $TAG_NAME created"

rm -f "$RELEASE_NOTES_FILE"

# Push if requested
if $PUSH_TAG; then
    info "Pushing tag to origin..."
    git push origin "$TAG_NAME"
    success "Tag pushed to remote"
    echo ""
    info "Create GitHub release at:"
    echo "  https://github.com/dxcSithLord/monster-self-drive/releases/new?tag=$TAG_NAME"
else
    echo ""
    info "To push the tag:"
    echo "  git push origin $TAG_NAME"
    echo ""
    info "To create a GitHub release:"
    echo "  1. Push the tag"
    echo "  2. Go to https://github.com/dxcSithLord/monster-self-drive/releases/new?tag=$TAG_NAME"
fi

echo ""
success "Release $TAG_NAME prepared!"
