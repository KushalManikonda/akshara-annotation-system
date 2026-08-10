<#
.SYNOPSIS
Executes Phase 3 (Storage Migration)

.DESCRIPTION
Runs the Python script to migrate audio files from local disk to Supabase.
#>

$ErrorActionPreference = "Stop"

# Get absolute path to project root (parent of scripts/)
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $ProjectRoot

Write-Host "==========================================================="
Write-Host " Phase 3: Supabase Storage Migration"
Write-Host "==========================================================="

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Error "Could not find .env file in $ProjectRoot. Please create it."
    Pop-Location
    exit 1
}

# Run the python script
Write-Host "Starting python migration script..."
python scripts/migrate_audio_to_supabase.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Migration script failed."
    Pop-Location
    exit $LASTEXITCODE
}

Write-Host "==========================================================="
Write-Host " Phase 3 Completed Successfully!"
Write-Host "==========================================================="

Pop-Location
