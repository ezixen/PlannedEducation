<#>
.SYNOPSIS
    Playwright E2E Test Runner with Auto-Start Frontend for PlannedEducation
.DESCRIPTION
    Runs Playwright E2E tests with automatic frontend server startup
.PARAMETER Project
    Project to run (chromium, chromium-canary, chromium-debug, mobile-chrome, tablet)
.PARAMETER Headed
    Run in headed mode (show browser)
.PARAMETER Debug
    Run in debug mode (step through)
.PARAMETER Test
    Run specific test by name pattern
.PARAMETER UpdateSnapshots
    Update visual regression snapshots
.PARAMETER NoServer
    Don't start frontend server (assume already running)
.PARAMETER Port
    Frontend server port (default: 5175)
.PARAMETER Slowmo
    Slow down operations by ms
.PARAMETER Trace
    Trace mode (on, off, on-first-retry, retain-on-failure)
.PARAMETER Help
    Show this help
.EXAMPLE
    .\run-tests-with-server.ps1 --project chromium-canary --headed
    .\run-tests-with-server.ps1 --project chromium-debug --headed --debug
    .\run-tests-with-server.ps1 --test "Full exam flow" --headed
    .\run-tests-with-server.ps1 --no-server --project chromium-canary --headed
#>

param(
    [Parameter(Position=0)]
    [string]$Project = "chromium-canary",
    [switch]$Headed,
    [string]$Test = "",
    [switch]$UpdateSnapshots,
    [switch]$NoServer,
    [int]$Port = 5175,
    [int]$Slowmo = 0,
    [string]$Trace = "on-first-retry",
    [switch]$Help
)

# Colors for output
$RED = [ConsoleColor]::Red
$GREEN = [ConsoleColor]::Green
$YELLOW = [ConsoleColor]::Yellow
$BLUE = [ConsoleColor]::Blue
$NC = [ConsoleColor]::Gray

# Script directory
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $SCRIPT_DIR

# Default values
$PROJECT = "chromium-canary"
$HEADED = $false
$SPECIFIC_TEST = ""
$UPDATE_SNAPSHOTS = $false
$NO_SERVER = $false
$PORT = 5175
$SLOWMO = 0
$TRACE = "on-first-retry"
$START_SERVER = $true
$SERVER_PORT = 5175
$SERVER_PID = $null

# Parse arguments manually to handle switches properly
$i = 0
while ($i -lt $args.Count) {
    $arg = $args[$i]
    switch -Regex ($arg) {
        '^--project$' { $Project = $args[$i + 1]; $i++ }
        '^--headed$' { $HEADED = $true }
        '^--test$' { $SPECIFIC_TEST = $args[$i + 1]; $i++ }
        '^--update-snapshots$' { $UPDATE_SNAPSHOTS = $true }
        '^--no-server$' { $START_SERVER = $false }
        '^--port$' { $PORT = [int]$args[$i + 1]; $i++ }
        '^--slowmo$' { $SLOWMO = [int]$args[$i + 1]; $i++ }
        '^--trace$' { $TRACE = $args[$i + 1]; $i++ }
        '^--no-server$' { $START_SERVER = $false }
        '^--help$' { 
            Write-Host "Usage: .\run-tests-with-server.ps1 [options]"
            Write-Host "Options:"
            Write-Host "  --project <name>       Project to run (chromium, chromium-canary, chromium-debug, mobile-chrome, tablet)"
            Write-Host "  --headed               Run in headed mode (show browser)"
            Write-Host "  --test <name>          Run specific test by name pattern"
            Write-Host "  --update-snapshots     Update visual regression snapshots"
            Write-Host "  --no-server            Don't start frontend server (assume already running)"
            Write-Host "  --port <port>          Frontend server port (default: 5175)"
            Write-Host "  --slowmo <ms>          Slow down operations by ms"
            Write-Host "  --trace <mode>         Trace mode (on, off, on-first-retry, retain-on-failure)"
            Write-Host "  --help                 Show this help"
            exit 0
        }
        default { Write-Host "Unknown option: $_"; exit 1 }
    }
    $i++
}

# Colors for output
function Write-Color($color, $message) {
    Write-Host -ForegroundColor $color $message
}

function Write-ColorLine($color, $message) {
    Write-Host -ForegroundColor $color $message
}

# Function to start frontend server
function Start-FrontendServer {
    if (-not $START_SERVER) {
        Write-ColorLine $YELLOW "Skipping frontend server startup (--no-server flag)"
        return
    }

    Write-ColorLine $BLUE "Starting frontend development server on port $SERVER_PORT..."

    # Check if port is already in use
    $portInUse = Get-NetTCPConnection -LocalPort $SERVER_PORT -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-ColorLine $YELLOW "Port $SERVER_PORT already in use. Assuming server is already running."
        return
    }

    # Start frontend server in background
    $portalPath = Join-Path $SCRIPT_DIR "..\..\..\web\apps\portal"
    Push-Location $portalPath

    # Check if node_modules exists
    if (-not (Test-Path "node_modules")) {
        Write-ColorLine $YELLOW "Installing frontend dependencies..."
        npm ci
    }

    # Start dev server in background
    $env:PORT = $SERVER_PORT
    $env:HOST = "127.0.0.1"
    $outLog = Join-Path $SCRIPT_DIR "frontend-server.out.log"
    $errLog = Join-Path $SCRIPT_DIR "frontend-server.err.log"
    $process = Start-Process "npm.cmd" -ArgumentList "run", "dev", "--", "--host", "127.0.0.1", "--port", $SERVER_PORT -PassThru -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    $global:SERVER_PID = $process.Id
    Pop-Location

    # Wait for server to be ready
    Write-ColorLine $YELLOW "Waiting for frontend server to start on port $SERVER_PORT..."
    $maxAttempts = 30
    $attempt = 0

    while ($attempt -lt $maxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$SERVER_PORT" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-ColorLine $GREEN "Frontend server is ready!"
                return
            }
        } catch {
            # Server not ready yet
        }
        Start-Sleep -Seconds 2
        $attempt++
    }

    Write-ColorLine $RED "ERROR: Frontend server failed to start within 60 seconds"
    if ($global:SERVER_PID) {
        Stop-Process -Id $global:SERVER_PID -Force -ErrorAction SilentlyContinue
    }
    exit 1
}

# Function to cleanup
function Cleanup {
    if ($global:SERVER_PID -and $START_SERVER) {
        Write-ColorLine $YELLOW "Stopping frontend server (PID: $($global:SERVER_PID))..."
        Stop-Process -Id $global:SERVER_PID -Force -ErrorAction SilentlyContinue
    }
}

# Trap cleanup on exit
$global:SERVER_PID = $null
$global:START_SERVER = $START_SERVER
Register-EngineEvent -SourceIdentifier "PowerShell.Exiting" -Action { Cleanup } | Out-Null

# Build command
$CMD = "npx playwright test"

if ($PROJECT) { $CMD += " --project=$PROJECT" }
if ($HEADED) { $CMD += " --headed" }
if ($DEBUG) { $CMD += " --debug" }
if ($SPECIFIC_TEST) { $CMD += " -g `"$SPECIFIC_TEST`"" }
if ($UPDATE_SNAPSHOTS) { $CMD += " --update-snapshots" }
if ($SLOWMO -gt 0) { $CMD += " --slowmo=$SLOWMO" }
if ($TRACE) { $CMD += " --trace=$TRACE" }

Write-ColorLine $BLUE "=========================================="
Write-ColorLine $BLUE "PlannedEducation E2E Test Runner"
Write-ColorLine $BLUE "=========================================="
Write-ColorLine $NC "Project: $PROJECT"
Write-ColorLine $NC "Headed: $HEADED"
Write-ColorLine $NC "Debug: $DEBUG"
Write-ColorLine $NC "Test filter: $($SPECIFIC_TEST -replace '^$', 'all')"
Write-ColorLine $NC "Update snapshots: $UPDATE_SNAPSHOTS"
Write-ColorLine $NC "Start server: $START_SERVER"
Write-ColorLine $NC "Server port: $SERVER_PORT"
Write-ColorLine $NC "Slowmo: $SLOWMO"
Write-ColorLine $NC "Trace: $TRACE"
Write-ColorLine $BLUE "=========================================="

# Check if Playwright is installed
if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-ColorLine $RED "ERROR: npx not found. Please install Node.js and npm."
    exit 1
}

# Check if Playwright is installed
if (-not (npx playwright --version 2>$null)) {
    Write-ColorLine $YELLOW "Playwright not found. Installing..."
    npm install -D @playwright/test
    npx playwright install --with-deps chromium
}

# Start frontend server if needed
if ($START_SERVER) {
    Start-FrontendServer
}

# Run tests
Write-ColorLine $YELLOW "Running: $CMD"
$exitCode = 0
try {
    Invoke-Expression $CMD
    $exitCode = $LASTEXITCODE
} catch {
    Write-ColorLine $RED "Test execution failed: $_"
    $exitCode = 1
}

# Cleanup
Cleanup

if ($exitCode -eq 0) {
    Write-ColorLine $GREEN "=========================================="
    Write-ColorLine $GREEN "All tests passed!"
    Write-ColorLine $GREEN "=========================================="
} else {
    Write-ColorLine $RED "=========================================="
    Write-ColorLine $RED "Some tests failed!"
    Write-ColorLine $RED "=========================================="
}

# Show report location
if (Test-Path "playwright-report") {
    Write-ColorLine $BLUE "HTML Report: $(Resolve-Path playwright-report/index.html)"
}

if (Test-Path "test-results") {
    Write-ColorLine $BLUE "Test Results: $(Resolve-Path test-results)"
}

exit $exitCode