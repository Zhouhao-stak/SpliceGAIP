@echo off
REM SpliceGAIP Build Script - Outputs to dist/ directory
REM Usage: build.bat

setlocal enabledelayedexpansion

echo ========================================
echo   SpliceGAIP Build Script
echo ========================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    exit /b 1
)

REM Clean previous builds
echo [1/3] Cleaning previous builds...
if exist "packaging\build-temp" rmdir /s /q "packaging\build-temp"
echo       Done.
echo.

REM Build with PyInstaller
echo [2/3] Building EXE with PyInstaller...
call venv\Scripts\activate.bat
python -m PyInstaller packaging\SpliceGAIP-Web.spec ^
    --distpath dist ^
    --workpath packaging\build-temp ^
    --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    deactivate
    exit /b 1
)
deactivate
echo       Done.
echo.

REM Copy .env file if it exists (for user's API key)
echo [3/3] Copying configuration files...
if exist ".env" (
    copy /Y ".env" "dist\SpliceGAIP\.env" >nul 2>&1
    echo       Copied .env to dist folder
)
if exist "API_CONFIG.md" (
    copy /Y "API_CONFIG.md" "dist\SpliceGAIP\API_CONFIG.md" >nul 2>&1
    echo       Copied API_CONFIG.md to dist folder
)
echo       Done.
echo.

REM Verify output
echo [4/4] Verifying output...
if exist "dist\SpliceGAIP\SpliceGAIP.exe" (
    for %%I in ("dist\SpliceGAIP\SpliceGAIP.exe") do set SIZE=%%~zI
    set /a SIZE_MB=!SIZE! / 1048576
    echo       SUCCESS!
    echo.
    echo ========================================
    echo   Build Complete!
    echo ========================================
    echo   Location: dist\SpliceGAIP\
    echo   EXE Size: !SIZE_MB! MB
    echo   Date: %date% %time%
    echo ========================================
    echo.
    echo To run: cd dist\SpliceGAIP ^&^& SpliceGAIP.exe
    echo.
) else (
    echo ERROR: EXE file not found in dist/SpliceGAIP/
    exit /b 1
)

pause
