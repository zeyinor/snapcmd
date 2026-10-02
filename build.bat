@echo off
chcp 65001 >nul
REM 重新打包 SnapCmd.exe
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SnapCmd snapcmd.py
echo.
echo Done: dist\SnapCmd.exe
pause
