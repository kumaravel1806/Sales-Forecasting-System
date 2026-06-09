@echo off
setlocal enabledelayedexpansion
echo Starting Retail Forecasting Website...
echo.

rem Detect project root whether this BAT lives in the repo or on Desktop
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"
if exist "%PROJECT_ROOT%backend" goto root_found

rem Fallback to the known absolute path in case the BAT was copied elsewhere
set "PROJECT_ROOT=C:\Users\Gopinath C\OneDrive\Desktop\Jason_Forecasting\"
if exist "%PROJECT_ROOT%backend" goto root_found

echo [ERROR] Unable to locate the backend folder.
echo Tried:
echo   %SCRIPT_DIR%backend
echo   %PROJECT_ROOT%backend
echo Make sure the project folder exists or update start_website.bat with the new path.
pause
exit /b 1

:root_found
pushd "%PROJECT_ROOT%backend"

echo Starting backend server...
start "Backend Server" python app.py

echo Waiting for server to start...
timeout /t 5 /nobreak >nul

echo Opening website in browser...
REM Open login page directly so homepage is login, not previous shopping tab
start "" "http://localhost:8000/login.html"

echo.
echo ✅ Website is starting!
echo ✅ Backend server is running in separate window
echo ✅ Browser should open automatically
echo.
echo ⚠️  DO NOT CLOSE the Backend Server window
echo    (It keeps the website running)
echo.
pause

popd
endlocal
