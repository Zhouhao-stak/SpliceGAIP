@echo off
REM Clean all build artifacts except dist/
REM Usage: clean_builds.bat

setlocal enabledelayedexpansion

echo ========================================
echo   Cleaning Build Artifacts
echo ========================================
echo.

REM Kill any running SpliceGAIP processes
echo [1/4] Stopping running instances...
taskkill /F /IM SpliceGAIP.exe 2>nul
timeout /t 2 /nobreak >nul
echo       Done.
echo.

REM Remove packaging subdirectories
echo [2/4] Removing packaging/build-* and packaging/dist-*...
cd packaging
for /d %%D in (build-*) do (
    echo       Removing %%D...
    rmdir /s /q "%%D" 2>nul
)
for /d %%D in (dist-*) do (
    echo       Removing %%D...
    rmdir /s /q "%%D" 2>nul
)
if exist "dist" (
    echo       Removing dist...
    rmdir /s /q "dist" 2>nul
)
cd ..
echo       Done.
echo.

REM Remove temporary build directories
echo [3/4] Removing temporary directories...
if exist "packaging\build-temp" rmdir /s /q "packaging\build-temp" 2>nul
echo       Done.
echo.

REM Show what remains
echo [4/4] Final state:
echo.
echo   Root dist/ directory:
dir dist /b 2>nul || echo     (empty or not found)
echo.
echo   Packaging directory:
dir packaging /b | findstr /v ".py .md .ico .png" || echo     (only config files)
echo.

echo ========================================
echo   Cleanup Complete!
echo ========================================
echo.
echo   EXE location: dist\SpliceGAIP.exe
echo   To rebuild:   run build.bat
echo.

pause
