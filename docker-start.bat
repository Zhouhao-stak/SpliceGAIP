@echo off
REM SpliceGAIP Docker Start Script for Windows
REM Usage: docker-start.bat

echo ========================================
echo   SpliceGAIP Docker Setup
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo AI features will be disabled without API key.
    echo.
    echo Create .env file with your DeepSeek API key:
    echo   MODEL_API_KEY=sk-your-key-here
    echo.
    set /p CREATE_ENV="Create sample .env file now? (y/n): "
    if /i "!CREATE_ENV!"=="y" (
        (
            echo # SpliceGAIP Docker Configuration
            echo MODEL_API_BASE_URL=https://api.deepseek.com
            echo MODEL_NAME=deepseek-flash
            echo MODEL_API_KEY=sk-YOUR_API_KEY_HERE
            echo MODEL_THINKING=auto
            echo MODEL_REASONING_EFFORT=low
        ) > .env
        echo Created .env file. Please edit it with your API key.
        echo.
    )
)

REM Build and start containers
echo [1/3] Building Docker image...
docker-compose build
if errorlevel 1 (
    echo ERROR: Docker build failed!
    pause
    exit /b 1
)
echo       Done.
echo.

echo [2/3] Starting containers...
docker-compose up -d
if errorlevel 1 (
    echo ERROR: Failed to start containers!
    pause
    exit /b 1
)
echo       Done.
echo.

echo [3/3] Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Check health
docker-compose ps | findstr "Up" >nul
if errorlevel 1 (
    echo WARNING: Container may not be healthy. Check logs with: docker-compose logs
) else (
    echo       Services are running!
)
echo.

echo ========================================
echo   SpliceGAIP is now running!
echo ========================================
echo.
echo   Web UI:      http://localhost:8800/
echo   API:         http://localhost:8800/api/health
echo   Streamlit:   http://localhost:8501/
echo.
echo To view logs:     docker-compose logs -f
echo To stop:          docker-compose down
echo To restart:       docker-compose restart
echo.
pause
