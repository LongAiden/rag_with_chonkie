#!/bin/bash
# ============================================
# Docker Test Runner Script
# ============================================
# This script provides easy commands to run tests inside Docker containers.
# Usage: ./test/run_tests_docker.sh [command] [args]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if containers are running
check_postgres() {
    if ! docker ps --filter "name=rag_postgres" --filter "status=running" | grep -q rag_postgres; then
        print_warning "PostgreSQL container is not running."
        print_info "Starting PostgreSQL container..."
        docker-compose up -d postgres
        print_info "Waiting for PostgreSQL to be healthy..."
        sleep 5
    fi
}

# Function to run all tests
run_all_tests() {
    print_info "Running all tests with coverage..."
    check_postgres
    docker-compose --profile test run --rm test
    print_success "All tests completed! Coverage report available in htmlcov/"
}

# Function to run specific test file
run_test_file() {
    local test_file=$1
    if [ -z "$test_file" ]; then
        print_error "Please specify a test file"
        echo "Usage: $0 file <test_file>"
        echo "Example: $0 file test_database_connection.py"
        exit 1
    fi

    print_info "Running tests from: $test_file"
    check_postgres
    docker-compose --profile test run --rm test pytest "test/$test_file" -v
}

# Function to run tests by marker or keyword
run_test_filter() {
    local filter=$1
    if [ -z "$filter" ]; then
        print_error "Please specify a filter (marker or keyword)"
        echo "Usage: $0 filter <keyword>"
        echo "Example: $0 filter database"
        exit 1
    fi

    print_info "Running tests matching: $filter"
    check_postgres
    docker-compose --profile test run --rm test pytest test/ -v -k "$filter"
}

# Function to run tests with custom pytest args
run_custom() {
    print_info "Running tests with custom arguments: $@"
    check_postgres
    docker-compose --profile test run --rm test pytest "$@"
}

# Function to enter interactive shell in test container
run_shell() {
    print_info "Starting interactive shell in test container..."
    check_postgres
    docker-compose --profile test run --rm test /bin/bash
}

# Function to build test image
build_test_image() {
    print_info "Building test Docker image..."
    docker-compose --profile test build test
    print_success "Test image built successfully!"
}

# Function to clean up test containers and volumes
cleanup() {
    print_info "Cleaning up test containers..."
    docker-compose --profile test down
    print_success "Cleanup completed!"
}

# Function to run quick tests (skip slow ones)
run_quick() {
    print_info "Running quick tests (skipping slow tests)..."
    check_postgres
    docker-compose --profile test run --rm test pytest test/ -v -m "not slow"
}

# Function to run only database tests
run_database() {
    print_info "Running database connection tests..."
    check_postgres
    docker-compose --profile test run --rm test pytest test/test_database_connection.py -v
}

# Function to run only embedding tests
run_embedding() {
    print_info "Running embedding tests..."
    check_postgres
    docker-compose --profile test run --rm test pytest test/test_embedding.py -v
}

# Function to run only retrieval tests
run_retrieval() {
    print_info "Running retrieval tests..."
    check_postgres
    docker-compose --profile test run --rm test pytest test/test_retrieval.py -v
}

# Function to run only API tests (Gemini, Logfire)
run_api() {
    print_info "Running API integration tests..."
    check_postgres
    docker-compose --profile test run --rm test pytest test/test_gemini_api.py test/test_logfire.py -v
}

# Function to show test coverage report
show_coverage() {
    print_info "Generating coverage report..."
    check_postgres
    docker-compose --profile test run --rm test pytest test/ --cov=. --cov-report=html --cov-report=term
    print_success "Coverage report generated in htmlcov/"

    # Try to open in browser (works on some systems)
    if command -v xdg-open &> /dev/null; then
        xdg-open htmlcov/index.html 2>/dev/null || true
    elif command -v open &> /dev/null; then
        open htmlcov/index.html 2>/dev/null || true
    fi
}

# Function to run tests in order (recommended)
run_ordered() {
    print_info "Running tests in recommended order..."
    check_postgres

    print_info "Step 1/5: Database connection tests"
    docker-compose --profile test run --rm test pytest test/test_database_connection.py -v

    print_info "Step 2/5: Gemini API tests"
    docker-compose --profile test run --rm test pytest test/test_gemini_api.py -v

    print_info "Step 3/5: Logfire integration tests"
    docker-compose --profile test run --rm test pytest test/test_logfire.py -v

    print_info "Step 4/5: Embedding tests"
    docker-compose --profile test run --rm test pytest test/test_embedding.py -v

    print_info "Step 5/5: Retrieval tests"
    docker-compose --profile test run --rm test pytest test/test_retrieval.py -v

    print_success "All tests completed in order!"
}

# Function to show help
show_help() {
    cat << EOF
${GREEN}RAG with Llama - Docker Test Runner${NC}

Usage: $0 [command] [args]

${YELLOW}Commands:${NC}
  all                 Run all tests with coverage (default)
  file <name>         Run specific test file
  filter <keyword>    Run tests matching keyword
  custom <args>       Run pytest with custom arguments
  shell               Start interactive shell in test container
  build               Build test Docker image
  cleanup             Clean up test containers

  ${YELLOW}Test Categories:${NC}
  quick               Run quick tests (skip slow ones)
  database            Run database connection tests only
  embedding           Run embedding tests only
  retrieval           Run retrieval tests only
  api                 Run API integration tests (Gemini, Logfire)
  ordered             Run all tests in recommended order

  ${YELLOW}Coverage:${NC}
  coverage            Generate and show coverage report

  ${YELLOW}Help:${NC}
  help                Show this help message

${YELLOW}Examples:${NC}
  $0                                    # Run all tests
  $0 all                                # Run all tests with coverage
  $0 file test_database_connection.py   # Run specific test file
  $0 filter "embedding"                 # Run tests with "embedding" in name
  $0 database                           # Run database tests only
  $0 ordered                            # Run tests in recommended order
  $0 custom test/ -v -k "similarity"    # Custom pytest arguments
  $0 shell                              # Interactive shell
  $0 coverage                           # Generate coverage report
  $0 build                              # Rebuild test image

${YELLOW}Prerequisites:${NC}
  - Docker and Docker Compose installed
  - .env file configured with necessary credentials
  - PostgreSQL container running (will be started automatically if needed)

${YELLOW}Environment Variables:${NC}
  Required: GOOGLE_API_KEY, POSTGRES_USER, POSTGRES_PASSWORD
  Optional: LOGFIRE_WRITE_TOKEN

EOF
}

# Main script logic
case "${1:-all}" in
    all)
        run_all_tests
        ;;
    file)
        run_test_file "$2"
        ;;
    filter)
        run_test_filter "$2"
        ;;
    custom)
        shift
        run_custom "$@"
        ;;
    shell)
        run_shell
        ;;
    build)
        build_test_image
        ;;
    cleanup)
        cleanup
        ;;
    quick)
        run_quick
        ;;
    database)
        run_database
        ;;
    embedding)
        run_embedding
        ;;
    retrieval)
        run_retrieval
        ;;
    api)
        run_api
        ;;
    ordered)
        run_ordered
        ;;
    coverage)
        show_coverage
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
