#!/bin/bash
# Setup script for Highlight MCP Server

set -e

echo "Setting up Highlight MCP Server..."

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    echo "Error: Node.js 20 or later is required (found v$NODE_VERSION)"
    exit 1
fi
echo "Node.js version: $(node -v)"

# Install dependencies
echo "Installing dependencies..."
npm install

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "IMPORTANT: Edit .env with your CAST Highlight credentials"
else
    echo ".env already exists, skipping..."
fi

# Run type check
echo "Running type check..."
npm run typecheck || {
    echo "Warning: Type check had issues (may be expected for initial setup)"
}

# Run tests
echo "Running tests..."
npm test || {
    echo "Warning: Some tests may fail without valid credentials"
}

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your CAST Highlight credentials"
echo "2. Run 'make dev' to start development server"
echo "3. See CLAUDE.md for AI agent instructions"
echo ""
