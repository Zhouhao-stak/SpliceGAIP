@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"
title SpliceGAIP - One-click Startup

echo ========================================
echo   SpliceGAIP One-click Startup
echo ========================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker was not found in PATH.
    echo Install Docker Desktop, then run this script again.
    goto :failed
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running.
    echo Start Docker Desktop and wait until it shows Running.
    goto :failed
)

echo [1/3] Building and starting the container...
docker compose up -d --build --force-recreate
if errorlevel 1 (
    goto :compose_failed
)

echo [2/3] Waiting for the API health check...
set "HEALTHY="
for /L %%N in (1,1,30) do (
    set "HEALTH_STATUS="
    for /f "delims=" %%S in ('docker inspect --format="{{.State.Health.Status}}" splicegaip 2^>nul') do set "HEALTH_STATUS=%%S"
    if /I "!HEALTH_STATUS!"=="healthy" (
        set "HEALTHY=1"
        goto :healthy
    )
    timeout /t 2 /nobreak >nul
)

:healthy
if not defined HEALTHY (
    echo.
    echo [ERROR] The container started, but the API did not become healthy in 60 seconds.
    echo Check the logs with:
    echo   docker compose logs --tail=100
    goto :failed
)

echo [3/3] SpliceGAIP is ready.
echo.
echo   Web UI: http://127.0.0.1:8800/
echo   API:    http://127.0.0.1:8800/api/health
echo.
start "" "http://127.0.0.1:8800/"
echo The browser has been opened. This window will close in 5 seconds.
timeout /t 5 /nobreak >nul
exit /b 0

:failed
echo.
pause
exit /b 1

:compose_failed
echo.
echo [ERROR] The container could not be started.
echo.
echo If the error above mentions 401, unauthorized, or a registry mirror,
echo check the base image registry in Dockerfile.
echo If it mentions a port conflict, stop the process using port 8800 or 8501.
echo Current listeners:
netstat -ano | findstr "8800 8501"
echo.
pause
exit /b 1
