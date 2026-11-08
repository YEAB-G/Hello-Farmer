param(
    [string]$IP = ""
)

# 1. Detect active network IP if not supplied
if (-not $IP) {
    # Check Tailscale interface first (if using mesh VPN across different networks)
    $ts = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*Tailscale*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($ts) {
        $IP = $ts.IPAddress
        Write-Host "  [Auto-Detected Tailscale VPN IP: $IP]" -ForegroundColor Magenta
    } else {
        $wifi = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi*" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($wifi) {
            $IP = $wifi.IPAddress
        } else {
            $adapter = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
                $_.IPAddress -notlike "127.*" -and 
                $_.IPAddress -notlike "169.254.*" -and 
                $_.IPAddress -notlike "172.*" 
            } | Select-Object -First 1
            if ($adapter) {
                $IP = $adapter.IPAddress
            } else {
                $IP = "127.0.0.1"
            }
        }
    }
}

$hostname = $env:COMPUTERNAME

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  [Hello Farmer] Network IP Configurator" -ForegroundColor Green
Write-Host "  Active Target IP: $IP" -ForegroundColor Yellow
Write-Host "  Local Hostname:   $hostname.local" -ForegroundColor Yellow
Write-Host "=======================================================" -ForegroundColor Cyan

$root = Split-Path -Parent $PSScriptRoot
$pjsipPath = Join-Path $root "asterisk\pjsip.conf"
$envPath = Join-Path $root ".env"

# 2. Update asterisk/pjsip.conf
if (Test-Path $pjsipPath) {
    $content = Get-Content $pjsipPath -Raw
    $content = $content -replace "external_media_address=.*", "external_media_address=$IP"
    $content = $content -replace "external_signaling_address=.*", "external_signaling_address=$IP"
    $content = $content -replace "media_address=.*", "media_address=$IP"
    Set-Content -Path $pjsipPath -Value $content -NoNewline
    Write-Host "  [OK] Updated asterisk\pjsip.conf with $IP" -ForegroundColor Green
}

# 3. Update .env
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
    if ($envContent -match "SIP_SERVER_IP=") {
        $envContent = $envContent -replace "SIP_SERVER_IP=.*", "SIP_SERVER_IP=$IP"
    } else {
        $envContent = $envContent + "`nSIP_SERVER_IP=$IP`n"
    }
    Set-Content -Path $envPath -Value $envContent -NoNewline
    Write-Host "  [OK] Updated .env with SIP_SERVER_IP=$IP" -ForegroundColor Green
}

# 4. Apply changes to Asterisk and Backend if Docker is running
Write-Host "`n  Checking Docker engine status..." -ForegroundColor Cyan
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -eq 0) {
    docker compose up -d backend asterisk | Out-Null
    Write-Host "  [OK] Asterisk restarted and ready on ${IP}:5060!" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Docker Desktop is not currently running." -ForegroundColor Yellow
    Write-Host "         Files updated successfully! When you launch Docker Desktop, run:" -ForegroundColor Yellow
    Write-Host "         docker compose up -d" -ForegroundColor Yellow
}

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  Softphone (MicroSIP / Linphone / Zoiper) Connection:" -ForegroundColor Green
Write-Host "  - Option A (Direct IP):  ${IP}:5060" -ForegroundColor Yellow
Write-Host "  - Option B (LAN Domain): ${hostname}.local:5060" -ForegroundColor Yellow
Write-Host "  - Username:              1001"
Write-Host "  - Password:              FarmerPass1001!"
Write-Host "  - Dial Destination:      8028"
Write-Host "=======================================================" -ForegroundColor Cyan

