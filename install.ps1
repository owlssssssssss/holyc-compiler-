# HolyC compiler — one-time Windows setup
# Adds hcc to your user PATH and downloads the bundled C compiler (TinyCC).

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$BinLink = Join-Path $env:LOCALAPPDATA "HolyC\bin"

Write-Host "HolyC compiler setup" -ForegroundColor Cyan
Write-Host "  Root: $Root"

# Create launcher in LocalAppData\bin
New-Item -ItemType Directory -Force -Path $BinLink | Out-Null

$Launcher = Join-Path $BinLink "hcc.cmd"
@"
@echo off
setlocal EnableExtensions
python "$Root\hcc.py" %*
endlocal & exit /b %ERRORLEVEL%
"@ | Set-Content -Path $Launcher -Encoding ASCII

# Add to user PATH if not already there
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinLink*") {
    $newPath = if ($userPath) { "$userPath;$BinLink" } else { $BinLink }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = "$env:Path;$BinLink"
    Write-Host "Added to PATH: $BinLink" -ForegroundColor Green
} else {
    Write-Host "Already on PATH: $BinLink" -ForegroundColor Yellow
}

# Download TinyCC toolchain
Write-Host "Downloading TinyCC (portable C compiler)..." -ForegroundColor Cyan
python -c "
from holyc.toolchain import ensure_toolchain
ensure_toolchain()
"

# Optional: double-click .HC files to run them
$HcAssoc = cmd /c "assoc .HC 2>nul"
if (-not $HcAssoc) {
    cmd /c "assoc .HC=HolyC.Source" | Out-Null
    cmd /c "ftype HolyC.Source=`"$Root\hcc.cmd`" `"%1`" -q" | Out-Null
    Write-Host "Registered .HC double-click -> run with hcc" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done! Open a NEW terminal and try:" -ForegroundColor Green
Write-Host "  hcc mytest.HC"
Write-Host "  hcc examples\hello.HC"
Write-Host ""
Write-Host "Double-click any .HC file in Explorer to run it." -ForegroundColor Green
Write-Host ""
Write-Host "Or from this folder without PATH:" -ForegroundColor Green
Write-Host "  .\hcc.cmd mytest.HC"