@echo off
REM SpliceGAIP Docker Management Script
REM Usage: docker-run.bat [command]

setlocal enabledelayedexpansion

if "%1"=="" goto :show_help
if "%1"=="start" goto :start
if "%1"=="stop" goto :stop
if "%1"=="restart" goto :restart
if "%1"=="logs" goto :logs
if "%1"=="status" goto :status
if "%1"=="clean" goto :clean
if "%1"=="rebuild" goto :rebuild
goto :unknown_command

:start
    echo Starting SpliceGAIP...
    docker-compose up -d
    echo Done. Access at http://localhost:8800/
    goto :end

:stop
    echo Stopping SpliceGAIP...
    docker-compose down
    echo Done.
    goto :end

:restart
    echo Restarting SpliceGAIP...
    docker-compose restart
    echo Done.
    goto :end

:logs
    echo Showing logs (Ctrl+C to exit)...
    docker-compose logs -f
    goto :end

:status
    echo Container status:
    docker-compose ps
    echo.
    echo Resource usage:
    docker stats --no-stream splicegaip 2>nul || echo No running container
    goto :end

:clean
    echo WARNING: This will remove all containers, images, and data!
    set /p CONFIRM="Are you sure? (y/n): "
    if /i "!CONFIRM!"=="y" (
        echo Stopping containers...
        docker-compose down -v
        echo Removing images...
        docker rmi splicegaip-splicegaip 2>nul
        echo Cleanup complete.
    ) else (
        echo Cancelled.
    )
    goto :end

:rebuild
    echo Rebuilding Docker image...
    docker-compose build --no-cache
    echo Restarting with new image...
    docker-compose up -d
    echo Done.
    goto :end

:show_help
    echo ========================================
    echo   SpliceGAIP Docker Manager
    echo ========================================
    echo.
    echo Usage: docker-run.bat [command]
    echo.
    echo Commands:
    echo   start     - Start containers
    echo   stop      - Stop containers
    echo   restart   - Restart containers
    echo   logs      - View logs
    echo   status    - Show container status
    echo   rebuild   - Rebuild image
    echo   clean     - Remove all data
    echo   help      - Show this help
    echo.
    goto :end

:unknown_command
    echo Unknown command: %1
    echo.
    goto :show_help

:end
