@echo off
echo Creating desktop shortcut for Retail Forecasting Website...

set "shortcut_path=%USERPROFILE%\Desktop\Retail Forecasting Website.lnk"
set "target_path=%~dp0start_website.bat"
set "icon_path=%SystemRoot%\System32\shell32.dll,13"

powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%shortcut_path%'); $Shortcut.TargetPath = '%target_path%'; $Shortcut.IconLocation = '%icon_path%'; $Shortcut.Description = 'Start Retail Forecasting Website'; $Shortcut.Save()"

echo ✅ Desktop shortcut created!
echo You can now double-click "Retail Forecasting Website" on your desktop
pause
