<#
Stop the BIM POS Streamlit Windows service.
Requires Admin.
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

$ServiceName = "BIMPOS_Streamlit"
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "Service not found: $ServiceName" -ForegroundColor Yellow
    exit 1
}

Stop-Service $ServiceName
Write-Host "Service stopped: $ServiceName"

