#!/bin/bash
# Playwright E2E Test Runner with Auto-Start Frontend
# Usage: ./run-tests-with-server.sh [options]

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
SLOWMO=0
TRACE="on-first-retry"
START_SERVER=true
SERVER_PORT=5175
SERVER_PID=""

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
    --no-server)
      START_SERVER=false
      shift
      ;;
    --port)
      SERVER_PORT="$2"
      shift 2
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
      echo "  --no-server            Don't start frontend server (assume already running)"
      echo "  --port <port>          Frontend server port (default: 5175)"
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

# Function to start frontend server
start_frontend_server() {
    if [ "$START_SERVER" = false ]; then
        echo -e "${YELLOW}Skipping frontend server startup (--no-server flag)${NC}"
        return 0
    fi

    echo -e "${BLUE}Starting frontend development server on port $SERVER_PORT...${NC}"
    
    # Check if port is already in use
    if lsof -ti:$SERVER_PORT > /dev/null 2>&1; then
        echo -e "${YELLOW}Port $SERVER_PORT already in use. Assuming server is already running.${NC}"
        return 0
    fi

    # Start frontend server in background
    cd "$SCRIPT_DIR/../../web/apps/portal"
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        npm ci
    fi
    
    # Start dev server in background
    npm run dev -- --host 0.0.0.0 --port $SERVER_PORT > frontend-server.log 2>&1 &
    SERVER_PID=$!
    
    # Wait for server to be ready
    echo -e "${YELLOW}Waiting for frontend server to start on port $SERVER_PORT...${NC}"
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "http://localhost:$SERVER_PORT" > /dev/null 2>&1; then
            echo -e "${GREEN}Frontend server is ready!${NC}"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}ERROR: Frontend server failed to start within 60 seconds${NC}"
    if [ -n "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
    fi
    exit 1
}

# Function to cleanup
cleanup() {
    if [ -n "$SERVER_PID" ] && [ "$START_SERVER" = true ]; then
        echo -e "${YELLOW}Stopping frontend server (PID: $SERVER_PID)...${NC}"
        kill $SERVER_PID 2>/dev/null || true
    fi
}

# Trap cleanup on exit
trap cleanup EXIT

# Parse arguments
PROJECT="chromium-canary"
HEADED=false
DEBUG=false
SPECIFIC_TEST=""
UPDATE_SNAPSHOTS=false
SLOWMO=0
TRACE="on-first-retry"
START_SERVER=true
SERVER_PORT=5175
SERVER_PID=""

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
    --no-server)
      START_SERVER=false
      shift
      ;;
    --port)
      SERVER_PORT="$2"
      shift 2
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
      echo "  --no-server            Don't start frontend server (assume already running)"
      echo "  --port <port>          Frontend server port (default: 5175)"
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
echo -e "Start server: ${GREEN}$START_SERVER${NC}"
echo -e "Server port: ${GREEN}$SERVER_PORT${NC}"
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

# Start frontend server if needed
if [ "$START_SERVER" = true ]; then
    start_frontend_server
fi

# Run tests
echo -e "${YELLOW}Running: $CMD${NC}"
eval $CMD

EXIT_CODE=$?

# Cleanup
cleanup

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