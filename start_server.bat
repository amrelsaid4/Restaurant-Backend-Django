@echo off
echo Starting Django Restaurant Backend Server...
echo.
echo Server will be available at: http://127.0.0.1:8000/
echo Admin panel: http://127.0.0.1:8000/admin/
echo API endpoints: http://127.0.0.1:8000/api/
echo.
echo Press Ctrl+C to stop the server
echo.
python manage.py runserver
pause 