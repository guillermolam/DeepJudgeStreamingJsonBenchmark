#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

function Install-GlobalTool
{
    param($Name, $CheckCmd, $InstallAction)
    Write-Host "▶ Checking for $Name..."
    if (-not (Get-Command $CheckCmd -ErrorAction SilentlyContinue))
    {
        Write-Host "  • $Name not found, installing..."
        & $InstallAction
    }
    else
    {
        $path = (Get-Command $CheckCmd).Source
        Write-Host "  • Found $Name at $path"
    }
}

# 1. winget
Install-GlobalTool -Name 'winget' -CheckCmd 'winget' -InstallAction {
    # winget is part of App Installer; if missing, register via Appx
    Write-Host "    ↳ Installing App Installer via winget..."
    winget install --id Microsoft.DesktopAppInstaller --source msstore --accept-package-agreements --accept-source-agreements
}

# 2. task (Go-Task)
Install-GlobalTool -Name 'task' -CheckCmd 'task' -InstallAction {
    Write-Host "    ↳ Installing Go-Task via winget..."
    winget install --id go-task --source winget
}

# 3. nektos/act
Install-GlobalTool -Name 'act' -CheckCmd 'act' -InstallAction {
    Write-Host "    ↳ Installing act via official script..."
    Invoke-WebRequest -useb https://raw.githubusercontent.com/nektos/act/master/install.ps1 | Invoke-Expression
}

# 4. Configure act for this project
$actrc = ".actrc"
Write-Host "▶ Ensuring .actrc exists..."
if (-not (Test-Path $actrc))
{
    @"
-P ubuntu-latest=node:20-bullseye-slim
"@ | Set-Content $actrc
    Write-Host "  • Wrote default runner mapping to .actrc"
}
else
{
    Write-Host "  • .actrc already present"
}

# 5. Ensure Rancher Desktop runtime is accessible
Write-Host "▶ Verifying container runtime (Rancher Desktop)..."
try
{
    & wsl -d ubuntu -- docker version | Out-Null
    Write-Host "  • Docker accessible in WSL Ubuntu"
}
catch
{
    Write-Error "❌ Docker not accessible in WSL Ubuntu. Ensure Rancher Desktop WSL integration is enabled."
    exit 1
}

# 6. Ensure CI workflow exists
$ciFile = ".github/workflows/ci.yml"
Write-Host "▶ Checking for $ciFile..."
if (-not (Test-Path $ciFile))
{
    Write-Error "❌ CI workflow not found at $ciFile"
    exit 1
}
else
{
    Write-Host "  • Found CI workflow"
}

# 7. Run the CI workflow locally with act
Write-Host "▶ Running CI via act..."
act -j build-and-test --env RUST_LOG=info

Write-Host "✅ Local CI run complete!"
