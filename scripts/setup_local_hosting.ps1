<# 
One-time local hosting setup for BIM POS Inventory.
Requires Admin (firewall + Windows service).
Expects NSSM at C:\tools\nssm\nssm.exe (download from https://nssm.cc/download).
#>

$ErrorActionPreference = "Stop"

function Assert-Admin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "Please run this script as Administrator." -ForegroundColor Yellow
        exit 1
    }
}

Assert-Admin

$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$NssmPath = "C:\tools\nssm\nssm.exe"
$ServiceName = "BIMPOS_Streamlit"
$FirewallRuleName = "Streamlit BIM POS"

if (-not (Test-Path $NssmPath)) {
    Write-Host "NSSM not found at $NssmPath." -ForegroundColor Yellow
    Write-Host "Download NSSM, extract it, and place nssm.exe at $NssmPath." -ForegroundColor Yellow
    exit 1
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "Python not found on PATH. Install Python 3.10+ and retry." -ForegroundColor Yellow
    exit 1
}

$pythonExe = $pythonCmd.Source

# Firewall rule
$existingRule = Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
if (-not $existingRule) {
    New-NetFirewallRule -DisplayName $FirewallRuleName -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow | Out-Null
    Write-Host "Firewall rule added: $FirewallRuleName"
} else {
    Write-Host "Firewall rule exists: $FirewallRuleName"
}

# Install or update Windows service
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $existingService) {
    & $NssmPath install $ServiceName $pythonExe
}

& $NssmPath set $ServiceName AppDirectory $RepoRoot
& $NssmPath set $ServiceName AppParameters "-m streamlit run app.py"
& $NssmPath set $ServiceName AppStdout "$RepoRoot\logs\streamlit_out.log"
& $NssmPath set $ServiceName AppStderr "$RepoRoot\logs\streamlit_err.log"
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

if (-not (Test-Path "$RepoRoot\logs")) {
    New-Item -ItemType Directory -Path "$RepoRoot\logs" | Out-Null
}

Start-Service $ServiceName
Write-Host "Service started: $ServiceName"
Write-Host "Open: http://<PC-IP>:8501"

