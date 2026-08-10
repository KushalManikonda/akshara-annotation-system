#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Phase 2: Apply Alembic migration + run data migration (SQLite → PostgreSQL).

.DESCRIPTION
    Run this script AFTER:
    1. You have set DATABASE_URL in .env to your Supabase PostgreSQL URL.
    2. You have set SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY in .env.

.USAGE
    From the project root:
    .\scripts\phase2_run.ps1

.STEPS
    1. Verify .env has PostgreSQL DATABASE_URL
    2. Run Alembic migration (creates all tables in Postgres)
    3. Run data migration script (copies SQLite → Postgres)
    4. Run Phase 2 regression tests
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot | Split-Path -Parent

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Akshara Platform — Phase 2: Database Migration" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check .env has Postgres URL ────────────────────────────────────────────
Write-Host "STEP 1: Checking .env configuration..." -ForegroundColor Yellow

$envPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "ERROR: .env not found at $envPath" -ForegroundColor Red
    Write-Host "       Copy .env.example to .env and fill in your Supabase credentials." -ForegroundColor Red
    exit 1
}

$dbUrl = (Get-Content $envPath | Where-Object { $_ -match "^DATABASE_URL=" }) -replace "DATABASE_URL=", ""
if ($dbUrl -like "*sqlite*" -or [string]::IsNullOrWhiteSpace($dbUrl)) {
    Write-Host "ERROR: DATABASE_URL in .env is still set to SQLite (or empty)." -ForegroundColor Red
    Write-Host "       Update it to your Supabase PostgreSQL URL and re-run." -ForegroundColor Red
    Write-Host "       Current value: $dbUrl" -ForegroundColor Red
    exit 1
}

Write-Host "  PostgreSQL URL detected: $($dbUrl.Substring(0, [Math]::Min(50, $dbUrl.Length)))..." -ForegroundColor Green
Write-Host ""

# ── 2. Apply Alembic migration ────────────────────────────────────────────────
Write-Host "STEP 2: Applying Alembic migration (creates tables in PostgreSQL)..." -ForegroundColor Yellow
Set-Location $ProjectRoot

alembic -c migrations/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Alembic migration failed." -ForegroundColor Red
    exit 1
}
Write-Host "  Migration applied successfully." -ForegroundColor Green
Write-Host ""

# ── 3. Run data migration script ──────────────────────────────────────────────
Write-Host "STEP 3: Migrating data (SQLite → PostgreSQL)..." -ForegroundColor Yellow
python scripts/migrate_sqlite_to_postgres.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Data migration failed. Check output above." -ForegroundColor Red
    exit 1
}
Write-Host ""

# ── 4. Run Phase 2 tests ──────────────────────────────────────────────────────
Write-Host "STEP 4: Running Phase 2 regression tests..." -ForegroundColor Yellow
python -m pytest tests/backend/test_phase2_database.py -v --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Some Phase 2 tests failed. Review output above." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "  Phase 2 COMPLETE. PostgreSQL is now your primary DB." -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  - Start the Streamlit app: streamlit run streamlit_app/app.py" -ForegroundColor Cyan
    Write-Host "  - Start the FastAPI server: uvicorn backend.main:app --reload" -ForegroundColor Cyan
    Write-Host "  - Start the React frontend: cd frontend && npm run dev" -ForegroundColor Cyan
}
