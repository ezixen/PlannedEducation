#!/bin/bash
# Playwright E2E Test Runner for PlannedEducation
# Usage: ./run-tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default values
PROJECT="chromium-canary"
HEADED=false
DEBUG=false
SPECIFIC_TEST=""
UPDATE_SNAPSHOTS=false
HEADED=false
SLOWMO=0
TRACE="on-first-retry"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --headed)
      HEADED=true
      shift
      ;;
    --debug)
      DEBUG=true
      shift
      ;;
    --test)
      SPECIFIC_TEST="$2"
      shift 2
      ;;
    --update-snapshots)
      UPDATE_SNAPSHOTS=true
      shift
      ;;
    --headed)
      HEADED=true
      shift
      ;;
    --slowmo)
      SLOWMO="$2"
      shift 2
      ;;
    --trace)
      TRACE="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --project <name>       Project to run (chromium, chromium-canary, chromium-debug, mobile-chrome, tablet)"
      echo "  --headed               Run in headed mode (show browser)"
      echo "  --debug                Run in debug mode (step through)"
      echo "  --test <name>          Run specific test by name pattern"
      echo "  --update-snapshots     Update visual regression snapshots"
      echo "  --headed               Run in headed mode (show browser)"
      echo "  --slowmo <ms>          Slow down operations by ms"
      echo "  --trace <mode>         Trace mode (on, off, on-first-retry, retain-on-failure)"
      echo "  --help                 Show this help"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Build command
CMD="npx playwright test"

if [ -n "$PROJECT" ]; then
  CMD="$CMD --project=$PROJECT"
fi

if [ "$HEADED" = true ]; then
  CMD="$CMD --headed"
fi

if [ "$DEBUG" = true ]; then
  CMD="$CMD --debug"
fi

if [ -n "$SPECIFIC_TEST" ]; then
  CMD="$CMD -g \"$SPECIFIC_TEST\""
fi

if [ "$UPDATE_SNAPSHOTS" = true ]; then
  CMD="$CMD --update-snapshots"
fi

if [ "$HEADED" = true ]; then
  CMD="$CMD --headed"
fi

if [ -n "$SLOWMO" ]; then
  CMD="$CMD --slowmo=$SLOWMO"
fi

if [ -n "$TRACE" ]; then
  CMD="$CMD --trace=$TRACE"
fi

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}PlannedEducation E2E Test Runner${NC}"
echo -e "${BLUE}==========================================${NC}"
echo -e "Project: ${GREEN}$PROJECT${NC}"
echo -e "Headed: ${GREEN}$HEADED${NC}"
echo -e "Debug: ${GREEN}$DEBUG${NC}"
echo -e "Test filter: ${GREEN}${SPECIFIC_TEST:-all}${NC}"
echo -e "Update snapshots: ${GREEN}$UPDATE_SNAPSHOTS${NC}"
echo -e "Headed: ${GREEN}$HEADED${NC}"
echo -e "Slowmo: ${GREEN}$SLOWMO${NC}"
echo -e "Trace: ${GREEN}$TRACE${NC}"
echo -e "${BLUE}==========================================${NC}"

# Check if Playwright is installed
if ! command -v npx &> /dev/null; then
    echo -e "${RED}ERROR: npx not found. Please install Node.js and npm.${NC}"
    exit 1
fi

# Check if Playwright is installed
if ! npx playwright --version &> /dev/null; then
    echo -e "${YELLOW}Playwright not found. Installing...${NC}"
    npm install -D @playwright/test
    npx playwright install --with-deps chromium
fi

# Run tests
echo -e "${YELLOW}Running: $CMD${NC}"
eval $CMD

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}All tests passed!${NC}"
    echo -e "${GREEN}==========================================${NC}"
else
    echo -e "${RED}==========================================${NC}"
    echo -e "${RED}Some tests failed!${NC}"
    echo -e "${RED}==========================================${NC}"
fi

# Show report location
if [ -d "playwright-report" ]; then
    echo -e "${BLUE}HTML Report: ${GREEN}./playwright-report/index.html${NC}"
fi

if [ -d "test-results" ]; then
    echo -e "${BLUE}Test Results: ${GREEN}./test-results/${NC}"
fi

exit $EXIT_CODE