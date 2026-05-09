#!/bin/bash

# NivasAI Platform - Complete Test Suite Execution
# This script runs all tests and generates comprehensive reports

set -e

echo "=========================================="
echo "NivasAI Platform - Test Suite Execution"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create test results directory
mkdir -p test_results

echo "Step 1: Environment Validation"
echo "------------------------------"
python -c "import sys; print(f'Python version: {sys.version}')"
python -c "import pytest; print(f'Pytest version: {pytest.__version__}')"
echo ""

echo "Step 2: Running Unit Tests"
echo "------------------------------"
pytest tests/complaint_classifier/ -v --tb=short --junit-xml=test_results/unit_complaint_classifier.xml || true
pytest tests/complaint_router/ -v --tb=short --junit-xml=test_results/unit_complaint_router.xml || true
pytest tests/housing_matcher/ -v --tb=short --junit-xml=test_results/unit_housing_matcher.xml || true
pytest tests/document_parser/ -v --tb=short --junit-xml=test_results/unit_document_parser.xml || true
pytest tests/bot_webhook/ -v --tb=short --junit-xml=test_results/unit_bot_webhook.xml || true
pytest tests/notification_broadcaster/ -v --tb=short --junit-xml=test_results/unit_notification_broadcaster.xml || true
echo ""

echo "Step 3: Running Integration Tests"
echo "------------------------------"
pytest tests/integration/ -v --tb=short --junit-xml=test_results/integration.xml || true
echo ""

echo "Step 4: Running API Tests"
echo "------------------------------"
pytest tests/api/ -v --tb=short --junit-xml=test_results/api.xml || true
echo ""

echo "Step 5: Running Coverage Analysis"
echo "------------------------------"
pytest tests/ --cov=app --cov-report=html:test_results/coverage_html --cov-report=term --cov-report=xml:test_results/coverage.xml || true
echo ""

echo "Step 6: Test Summary"
echo "------------------------------"
echo "Test results saved to: test_results/"
echo "Coverage report: test_results/coverage_html/index.html"
echo ""

# Count test results
TOTAL_TESTS=$(find test_results -name "*.xml" -exec grep -h "tests=" {} \; | grep -oP 'tests="\K[0-9]+' | awk '{s+=$1} END {print s}')
PASSED_TESTS=$(find test_results -name "*.xml" -exec grep -h "failures=" {} \; | grep -oP 'failures="\K[0-9]+' | awk '{s+=$1} END {print s}')

echo -e "${GREEN}Total Tests Run: ${TOTAL_TESTS}${NC}"
echo -e "${YELLOW}Check test_results/ for detailed reports${NC}"
echo ""

echo "=========================================="
echo "Test Execution Complete"
echo "=========================================="
