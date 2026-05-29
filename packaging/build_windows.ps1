# Build a standalone Windows app and (optionally) a one-click installer.
# Usage (PowerShell):  .\packaging\build_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> Creating build virtualenv (.build-venv)..."
python -m venv .build-venv
& .\.build-venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

Write-Host "==> Running PyInstaller..."
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist)  { Remove-Item dist  -Recurse -Force }
pyinstaller packaging\EverythingConverter.spec --noconfirm

$exe = "dist\EverythingConverter\EverythingConverter.exe"
if (-not (Test-Path $exe)) {
    throw "Expected exe at '$exe' was not produced."
}

# Build an installer if Inno Setup is available; otherwise just zip the folder.
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if ($iscc) {
    Write-Host "==> Building installer with Inno Setup..."
    & iscc packaging\everythingconverter.iss
    Write-Host "Installer written to dist\EverythingConverter-Setup.exe"
} else {
    Write-Host "==> Inno Setup (iscc) not found; zipping the app folder instead..."
    $zip = "dist\EverythingConverter-Windows.zip"
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path "dist\EverythingConverter\*" -DestinationPath $zip
    Write-Host "Zip written to $zip"
}

Write-Host ""
Write-Host "==> Done! Send the installer (or zip) in dist\ to friends."
