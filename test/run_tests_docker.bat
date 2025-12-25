@echo off
REM ============================================
REM Docker Test Runner Script (Windows)
REM ============================================
REM This script provides easy commands to run tests inside Docker containers on Windows.
REM Usage: test\run_tests_docker.bat [command] [args]

setlocal enabledelayedexpansion

REM Check if Docker is installed
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH
    exit /b 1
)

REM Parse command
set "COMMAND=%~1"
if "%COMMAND%"=="" set "COMMAND=all"

REM Execute command
if /i "%COMMAND%"=="all" goto run_all
if /i "%COMMAND%"=="file" goto run_file
if /i "%COMMAND%"=="filter" goto run_filter
if /i "%COMMAND%"=="custom" goto run_custom
if /i "%COMMAND%"=="shell" goto run_shell
if /i "%COMMAND%"=="build" goto build_image
if /i "%COMMAND%"=="cleanup" goto cleanup
if /i "%COMMAND%"=="quick" goto run_quick
if /i "%COMMAND%"=="database" goto run_database
if /i "%COMMAND%"=="embedding" goto run_embedding
if /i "%COMMAND%"=="retrieval" goto run_retrieval
if /i "%COMMAND%"=="api" goto run_api
if /i "%COMMAND%"=="ordered" goto run_ordered
if /i "%COMMAND%"=="coverage" goto show_coverage
if /i "%COMMAND%"=="help" goto show_help
if /i "%COMMAND%"=="-h" goto show_help
if /i "%COMMAND%"=="--help" goto show_help

echo [ERROR] Unknown command: %COMMAND%
echo.
goto show_help

:check_postgres
echo [INFO] Checking PostgreSQL container...
docker ps --filter "name=rag_postgres" --filter "status=running" | find "rag_postgres" >nul
if %errorlevel% neq 0 (
    echo [WARNING] PostgreSQL container is not running.
    echo [INFO] Starting PostgreSQL container...
    docker-compose up -d postgres
    echo [INFO] Waiting for PostgreSQL to be healthy...
    timeout /t 5 /nobreak >nul
)
exit /b 0

:run_all
echo [INFO] Running all tests with coverage...
call :check_postgres
docker-compose --profile test run --rm test
echo [SUCCESS] All tests completed! Coverage report available in htmlcov/
goto end

:run_file
if "%~2"=="" (
    echo [ERROR] Please specify a test file
    echo Usage: %~nx0 file ^<test_file^>
    echo Example: %~nx0 file test_database_connection.py
    exit /b 1
)
echo [INFO] Running tests from: %~2
call :check_postgres
docker-compose --profile test run --rm test pytest "test/%~2" -v
goto end

:run_filter
if "%~2"=="" (
    echo [ERROR] Please specify a filter (marker or keyword)
    echo Usage: %~nx0 filter ^<keyword^>
    echo Example: %~nx0 filter database
    exit /b 1
)
echo [INFO] Running tests matching: %~2
call :check_postgres
docker-compose --profile test run --rm test pytest test/ -v -k "%~2"
goto end

:run_custom
shift
echo [INFO] Running tests with custom arguments...
call :check_postgres
docker-compose --profile test run --rm test pytest %*
goto end

:run_shell
echo [INFO] Starting interactive shell in test container...
call :check_postgres
docker-compose --profile test run --rm test /bin/bash
goto end

:build_image
echo [INFO] Building test Docker image...
docker-compose --profile test build test
echo [SUCCESS] Test image built successfully!
goto end

:cleanup
echo [INFO] Cleaning up test containers...
docker-compose --profile test down
echo [SUCCESS] Cleanup completed!
goto end

:run_quick
echo [INFO] Running quick tests (skipping slow tests)...
call :check_postgres
docker-compose --profile test run --rm test pytest test/ -v -m "not slow"
goto end

:run_database
echo [INFO] Running database connection tests...
call :check_postgres
docker-compose --profile test run --rm test pytest test/test_database_connection.py -v
goto end

:run_embedding
echo [INFO] Running embedding tests...
call :check_postgres
docker-compose --profile test run --rm test pytest test/test_embedding.py -v
goto end

:run_retrieval
echo [INFO] Running retrieval tests...
call :check_postgres
docker-compose --profile test run --rm test pytest test/test_retrieval.py -v
goto end

:run_api
echo [INFO] Running API integration tests...
call :check_postgres
docker-compose --profile test run --rm test pytest test/test_gemini_api.py test/test_logfire.py -v
goto end

:run_ordered
echo [INFO] Running tests in recommended order...
call :check_postgres

echo [INFO] Step 1/5: Database connection tests
docker-compose --profile test run --rm test pytest test/test_database_connection.py -v

echo [INFO] Step 2/5: Gemini API tests
docker-compose --profile test run --rm test pytest test/test_gemini_api.py -v

echo [INFO] Step 3/5: Logfire integration tests
docker-compose --profile test run --rm test pytest test/test_logfire.py -v

echo [INFO] Step 4/5: Embedding tests
docker-compose --profile test run --rm test pytest test/test_embedding.py -v

echo [INFO] Step 5/5: Retrieval tests
docker-compose --profile test run --rm test pytest test/test_retrieval.py -v

echo [SUCCESS] All tests completed in order!
goto end

:show_coverage
echo [INFO] Generating coverage report...
call :check_postgres
docker-compose --profile test run --rm test pytest test/ --cov=. --cov-report=html --cov-report=term
echo [SUCCESS] Coverage report generated in htmlcov/
start htmlcov\index.html 2>nul
goto end

:show_help
echo.
echo RAG with Llama - Docker Test Runner (Windows)
echo.
echo Usage: %~nx0 [command] [args]
echo.
echo Commands:
echo   all                 Run all tests with coverage (default)
echo   file ^<name^>         Run specific test file
echo   filter ^<keyword^>    Run tests matching keyword
echo   custom ^<args^>       Run pytest with custom arguments
echo   shell               Start interactive shell in test container
echo   build               Build test Docker image
echo   cleanup             Clean up test containers
echo.
echo   Test Categories:
echo   quick               Run quick tests (skip slow ones)
echo   database            Run database connection tests only
echo   embedding           Run embedding tests only
echo   retrieval           Run retrieval tests only
echo   api                 Run API integration tests (Gemini, Logfire)
echo   ordered             Run all tests in recommended order
echo.
echo   Coverage:
echo   coverage            Generate and show coverage report
echo.
echo   Help:
echo   help                Show this help message
echo.
echo Examples:
echo   %~nx0                                    # Run all tests
echo   %~nx0 all                                # Run all tests with coverage
echo   %~nx0 file test_database_connection.py   # Run specific test file
echo   %~nx0 filter "embedding"                 # Run tests with "embedding" in name
echo   %~nx0 database                           # Run database tests only
echo   %~nx0 ordered                            # Run tests in recommended order
echo   %~nx0 coverage                           # Generate coverage report
echo   %~nx0 build                              # Rebuild test image
echo.
echo Prerequisites:
echo   - Docker and Docker Compose installed
echo   - .env file configured with necessary credentials
echo   - PostgreSQL container running (will be started automatically if needed)
echo.
echo Environment Variables:
echo   Required: GOOGLE_API_KEY, POSTGRES_USER, POSTGRES_PASSWORD
echo   Optional: LOGFIRE_WRITE_TOKEN
echo.
goto end

:end
endlocal
