# PowerShell script to run all Raft tests on Windows

$BASE_PATH = "C:\Users\LMAPA\Documents\GitHub\go-raft"
$SCRIPT_PATH = "$BASE_PATH\scripts"
$BIN_PATH = "$BASE_PATH\bin"
$TEMP_PATH = "$BASE_PATH\temp"

if (-not (Test-Path $TEMP_PATH)) {
    New-Item -ItemType Directory -Path $TEMP_PATH -Force | Out-Null
}

# Kill any existing raft processes
Write-Host "Cleaning up existing processes..."
function Clean-RaftProcesses {
    Write-Host "Cleaning up existing raft processes and ports..."
    
    # Kill raft related processes
    Get-Process | Where-Object { $_.Name -match "raft|raftrunner|raftproxy" } -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    
    # Also kill any Go processes that might be holding ports
    Get-Process | Where-Object { $_.Name -match "go-raft" } -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    
    # Wait for ports to be released
    Start-Sleep -Seconds 3
    
    Write-Host "Cleanup completed, waiting for ports to be released..."
}

Clean-RaftProcesses

# Compile yourCode
Write-Host "Compiling yourCode..."
Set-Location "$BASE_PATH\yourCode"
go build -o "$BIN_PATH\raftrunner" main.go
if ($LASTEXITCODE -ne 0) { 
    Write-Host "ERROR: Failed to compile raftrunner"
    exit 1 
}

# Build the proxy runner
Write-Host "Building proxy runner..."
Set-Location "$BASE_PATH\tests"
go build -o "$BIN_PATH\raftproxyrunner" ./raftproxyrunner
if ($LASTEXITCODE -ne 0) { 
    Write-Host "ERROR: Failed to build raftproxyrunner"
    exit 1 
}

# Build the test binary
Write-Host "Building test binary..."
go build -o "$BIN_PATH\rafttest" ./rafttest
if ($LASTEXITCODE -ne 0) { 
    Write-Host "ERROR: Failed to build rafttest"
    exit 1 
}

Set-Location $BASE_PATH

# Remove old log file
if (Test-Path "$BASE_PATH\rafttest.log") {
    Remove-Item "$BASE_PATH\rafttest.log" -Force
}

Write-Host "Running tests..."

$tests = @(
    "testOneCandidateOneRoundElection",
    "testOneCandidateStartTwoElection",
    "testTwoCandidateForElection",
    "testSplitVote",
    "testAllForElection",
    "testLeaderRevertToFollower",
    "testOneSimplePut",
    "testOneSimpleUpdate",
    "testOneSimpleDelete",
    "testDeleteNonExistKey"
)

# Run each test with fresh ports
foreach ($test in $tests) {
    Write-Host "Running: $test..."
    
    # Kill any existing raft processes before each test - use function
    Clean-RaftProcesses
    
    & "$SCRIPT_PATH\run_test_single.ps1" $test
    
    # Wait for ports to be released
    Start-Sleep -Seconds 3
}

# Show test log
Write-Host "`n=== Test Results ==="
if (Test-Path "$BASE_PATH\rafttest.log") {
    Get-Content "$BASE_PATH\rafttest.log"
    Remove-Item "$BASE_PATH\rafttest.log" -Force
}

Write-Host "All tests completed."
