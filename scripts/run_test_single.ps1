# PowerShell script to run single Raft test on Windows

param(
    [string]$testName = "testOneCandidateOneRoundElection",
    [string]$nodePort0 = "",
    [string]$nodePort1 = "",
    [string]$nodePort2 = "",
    [string]$nodePort3 = "",
    [string]$nodePort4 = "",
    [string]$proxyPort0 = "",
    [string]$proxyPort1 = "",
    [string]$proxyPort2 = "",
    [string]$proxyPort3 = "",
    [string]$proxyPort4 = "",
    [string]$testerPort = ""
)

function Clean-RaftProcesses {
    Write-Host "Cleaning up existing raft processes and ports..."
    
    Get-Process | Where-Object { $_.Name -match "raft|raftrunner|raftproxy" } -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Get-Process | Where-Object { $_.Name -match "go-raft" } -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Start-Sleep -Seconds 3
    
    Write-Host "Cleanup completed, waiting for ports to be released..."
}

$BASE_PATH = "C:\Users\LMAPA\Documents\GitHub\go-raft"
$BIN_PATH = "$BASE_PATH\bin"
$TEMP_PATH = "$BASE_PATH\temp"

if (-not (Test-Path $TEMP_PATH)) {
    New-Item -ItemType Directory -Path $TEMP_PATH -Force | Out-Null
}

$RAFT_TEST = "$BIN_PATH\rafttest"
$RAFT_NODE = "$BIN_PATH\raftrunner"
$PROXY_NODE = "$BIN_PATH\raftproxyrunner"

# Manual cleanup before starting
Clean-RaftProcesses

# Generate random ports if not provided
if ([string]::IsNullOrEmpty($nodePort0)) {
    $ports = @()
    while ($ports.Count -lt 11) {
        $port = Get-Random -Minimum 10000 -Maximum 20000
        if ($ports -notcontains $port) { $ports += $port }
    }
    
    $NODE_PORT0 = $ports[0]
    $NODE_PORT1 = $ports[1]
    $NODE_PORT2 = $ports[2]
    $NODE_PORT3 = $ports[3]
    $NODE_PORT4 = $ports[4]
    $PROXY_PORT0 = $ports[5]
    $PROXY_PORT1 = $ports[6]
    $PROXY_PORT2 = $ports[7]
    $PROXY_PORT3 = $ports[8]
    $PROXY_PORT4 = $ports[9]
    $TESTER_PORT = $ports[10]
} else {
    $NODE_PORT0 = $nodePort0
    $NODE_PORT1 = $nodePort1
    $NODE_PORT2 = $nodePort2
    $NODE_PORT3 = $nodePort3
    $NODE_PORT4 = $nodePort4
    $PROXY_PORT0 = $proxyPort0
    $PROXY_PORT1 = $proxyPort1
    $PROXY_PORT2 = $proxyPort2
    $PROXY_PORT3 = $proxyPort3
    $PROXY_PORT4 = $proxyPort4
    $TESTER_PORT = $testerPort
}

$ALL_PORTS = "$NODE_PORT0,$NODE_PORT1,$NODE_PORT2,$NODE_PORT3,$NODE_PORT4"
$ALL_PROXY_PORTS = "$PROXY_PORT0,$PROXY_PORT1,$PROXY_PORT2,$PROXY_PORT3,$PROXY_PORT4"

$ErrorActionPreference = "Continue"

Write-Host "Running test: $testName..."

# Check executables
if (-not (Test-Path $RAFT_TEST) -or -not (Test-Path $RAFT_NODE) -or -not (Test-Path $PROXY_NODE)) {
    Write-Host "ERROR: Missing executables. Run run_test_all.ps1 first to build."
    exit 1
}

# Start proxies
$proxyProcs = @()
$proxyPorts = @(
    @{raft=$NODE_PORT0; proxy=$PROXY_PORT0; id=0},
    @{raft=$NODE_PORT1; proxy=$PROXY_PORT1; id=1},
    @{raft=$NODE_PORT2; proxy=$PROXY_PORT2; id=2},
    @{raft=$NODE_PORT3; proxy=$PROXY_PORT3; id=3},
    @{raft=$NODE_PORT4; proxy=$PROXY_PORT4; id=4}
)

foreach ($p in $proxyPorts) {
    $proc = Start-Process -FilePath $PROXY_NODE -ArgumentList "-raftport=$($p.raft)","-proxyport=$($p.proxy)","-id=$($p.id)" -NoNewWindow -PassThru -RedirectStandardOutput "$TEMP_PATH\proxy$($p.id)_out.txt" -RedirectStandardError "$TEMP_PATH\proxy$($p.id)_err.txt"
    $proxyProcs += $proc
}

Start-Sleep -Seconds 2

# Check proxy status
$proxyFailed = $false
for ($i = 0; $i -lt 5; $i++) {
    $outFile = "$TEMP_PATH\proxy${i}_out.txt"
    $errFile = "$TEMP_PATH\proxy${i}_err.txt"
    
    $proxyOK = $false
    if (Test-Path $outFile) {
        $out = Get-Content $outFile -Raw
        if ($out -match "Proxy started") { $proxyOK = $true }
    }
    if (Test-Path $errFile) {
        $err = Get-Content $errFile -Raw
        if ($err) { 
            Write-Host "ERROR: Proxy ${i} failed: $err"
            $proxyFailed = $true 
        }
    }
    if (-not $proxyOK -and -not $proxyFailed) {
        Write-Host "ERROR: Proxy ${i} failed to start"
        $proxyFailed = $true
    }
}

if ($proxyFailed) { exit 1 }

# Start Raft nodes
$nodeProcs = @()
for ($i = 0; $i -lt 5; $i++) {
    $nodePort = (Get-Variable "NODE_PORT$i").Value
    $proc = Start-Process -FilePath $RAFT_NODE -ArgumentList $nodePort,$ALL_PROXY_PORTS,$i,10000,10000 -NoNewWindow -PassThru -RedirectStandardOutput "$TEMP_PATH\node${i}_out.txt" -RedirectStandardError "$TEMP_PATH\node${i}_err.txt"
    $nodeProcs += $proc
}

Start-Sleep -Seconds 2

# Check node status
$nodeFailed = $false
for ($i = 0; $i -lt 5; $i++) {
    $errFile = "$TEMP_PATH\node${i}_err.txt"
    if (Test-Path $errFile) {
        $err = Get-Content $errFile -Raw
        if ($err -match "Successfully connect all nodes") {
            # OK
        } elseif ($err) {
            Write-Host "WARNING: Node ${i}: $err"
        }
    }
}

# Run test
$testStdoutFile = "$TEMP_PATH\test_stdout.txt"
$testStderrFile = "$TEMP_PATH\test_stderr.txt"

Push-Location $BASE_PATH
try {
    $process = Start-Process -FilePath $RAFT_TEST -ArgumentList "-proxyports=$ALL_PROXY_PORTS","-N=5","-t",$testName -NoNewWindow -Wait -PassThru -RedirectStandardOutput $testStdoutFile -RedirectStandardError $testStderrFile
    $testExitCode = $process.ExitCode
} finally {
    Pop-Location
}

# Show test result
if (Test-Path $testStdoutFile) {
    $stdout = Get-Content $testStdoutFile -Raw
    if ($stdout) { Write-Host $stdout.Trim() }
}

# Cleanup
foreach ($proc in $nodeProcs) {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
}
foreach ($proc in $proxyProcs) {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
}

if ($testExitCode -eq 0) {
    Write-Host "$testName PASS"
} else {
    Write-Host "$testName FAIL (exit code: $testExitCode)"
}
