<#
 DartaLink one-shot setup for Windows PowerShell.
   .\setup.ps1            # PostgreSQL (edit .env first if your credentials differ)
   .\setup.ps1 -Sqlite    # quick demo with a local SQLite file, no PostgreSQL needed
   .\setup.ps1 -NoRun     # do everything except start the dev server
#>
param([switch]$Sqlite, [switch]$NoRun)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip | Out-Null
pip install -r requirements.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    $key = python -c "import secrets; print(secrets.token_urlsafe(50))"
    (Get-Content .env) -replace "change-me-to-a-long-random-string", $key | Set-Content .env
}
if ($Sqlite) { (Get-Content .env) -replace "DB_ENGINE=postgres", "DB_ENGINE=sqlite" | Set-Content .env }

python manage.py makemigrations accounts requests_app workflow documents notifications
python manage.py migrate
python manage.py seed_demo
python manage.py check

Write-Host "`nSetup complete. Sign in with username 'admin' (or any demo user) and the DEMO_PASSWORD from .env." -ForegroundColor Green
if (-not $NoRun) { python manage.py runserver }
