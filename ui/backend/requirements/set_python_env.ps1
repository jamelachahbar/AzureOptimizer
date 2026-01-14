# Set up Python environment for Azure Cost Optimizer using UV
# This script creates a virtual environment and installs dependencies

$ErrorActionPreference = "Stop"

Write-Host "Setting up Python environment with UV..." -ForegroundColor Cyan

# Check if UV is installed
$uvPath = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvPath) {
    Write-Host "UV is not installed. Installing UV..." -ForegroundColor Yellow
    irm https://astral.sh/uv/install.ps1 | iex
}

# Navigate to backend directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Split-Path -Parent $scriptDir
Set-Location $backendDir

Write-Host "Working directory: $backendDir" -ForegroundColor Gray

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Green
uv venv .venv

# Install dependencies
Write-Host "Installing dependencies with UV..." -ForegroundColor Green
& .\.venv\Scripts\activate.ps1
uv pip install --prerelease=allow -e .

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the environment:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To run the application:" -ForegroundColor Cyan
Write-Host "  flask run" -ForegroundColor White
Write-Host "  # or" -ForegroundColor Gray
Write-Host "  python app.py" -ForegroundColor White
