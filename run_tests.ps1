# Runs the full DartaLink test-suite (uses a throw-away test database).
Set-Location $PSScriptRoot
& .\.venv\Scripts\Activate.ps1
python manage.py makemigrations accounts requests_app workflow documents notifications
python manage.py test --verbosity 2
