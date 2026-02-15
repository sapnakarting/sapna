#!/bin/bash

# SAPNA CARTING - Deployment Verification Script
# Usage: ./scripts/verify_deployment.sh [BASE_URL]
# Example: ./scripts/verify_deployment.sh https://sapna-carting.up.railway.app

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default base URL
BASE_URL="${1:-http://localhost:8000}"

echo "========================================"
echo "SAPNA CARTING Deployment Verification"
echo "========================================"
echo "Testing URL: $BASE_URL"
echo ""

# Track results
FAILED=0
PASSED=0

# Function to check HTTP endpoint
check_endpoint() {
    local endpoint=$1
    local expected_status=${2:-200}
    local description=$3
    
    echo -n "Testing $description... "
    
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${endpoint}" || echo "000")
    
    if [ "$HTTP_STATUS" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $HTTP_STATUS)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_status, got $HTTP_STATUS)"
        ((FAILED++))
        return 1
    fi
}

# Function to check JSON response
check_json_response() {
    local endpoint=$1
    local expected_key=$2
    local description=$3
    
    echo -n "Testing $description... "
    
    RESPONSE=$(curl -s "${BASE_URL}${endpoint}" || echo "")
    
    if echo "$RESPONSE" | grep -q "$expected_key"; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Key '$expected_key' not found)"
        ((FAILED++))
        return 1
    fi
}

echo "1. Basic Connectivity Tests"
echo "----------------------------"
check_endpoint "/health/" 200 "Health check endpoint"
check_endpoint "/ready/" 200 "Readiness probe"
check_endpoint "/health/detailed/" 200 "Detailed health check"

echo ""
echo "2. Application Endpoints"
echo "------------------------"
check_endpoint "/" 302 "Root redirect"
check_endpoint "/dashboard/" 302 "Dashboard (redirects to login if not authenticated)"
check_endpoint "/fleet/login/" 200 "Login page"

echo ""
echo "3. Static Files"
echo "---------------"
check_endpoint "/static/admin/css/base.css" 200 "Admin static files"

echo ""
echo "4. Health Check Content"
echo "-----------------------"
check_json_response "/health/" "healthy" "Health status in response"
check_json_response "/health/detailed/" "components" "Detailed health components"
check_json_response "/health/detailed/" "database" "Database component check"

echo ""
echo "5. SSL/Security Checks (Production)"
echo "-----------------------------------"
if [[ "$BASE_URL" == https* ]]; then
    echo -n "Checking SSL certificate... "
    SSL_INFO=$(curl -sI "${BASE_URL}/health/" 2>&1 || echo "")
    if echo "$SSL_INFO" | grep -q "200"; then
        echo -e "${GREEN}✓ PASS${NC} (SSL working)"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠ WARNING${NC} (Could not verify SSL)"
    fi
    
    echo -n "Checking HSTS header... "
    HSTS=$(curl -sI "${BASE_URL}/health/" | grep -i "strict-transport-security" || echo "")
    if [ -n "$HSTS" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HSTS enabled)"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠ WARNING${NC} (HSTS header not found)"
    fi
else
    echo -e "${YELLOW}Skipping SSL checks (non-HTTPS URL)${NC}"
fi

echo ""
echo "6. Response Time Checks"
echo "----------------------"
echo -n "Health endpoint response time... "
RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "${BASE_URL}/health/" || echo "999")
RESPONSE_MS=$(echo "$RESPONSE_TIME * 1000" | bc | cut -d. -f1)

if [ "$RESPONSE_MS" -lt 500 ]; then
    echo -e "${GREEN}✓ PASS${NC} (${RESPONSE_MS}ms)"
    ((PASSED++))
elif [ "$RESPONSE_MS" -lt 1000 ]; then
    echo -e "${YELLOW}⚠ WARNING${NC} (${RESPONSE_MS}ms - slower than ideal)"
else
    echo -e "${RED}✗ FAIL${NC} (${RESPONSE_MS}ms - too slow)"
    ((FAILED++))
fi

echo ""
echo "========================================"
echo "Verification Summary"
echo "========================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Deployment looks good.${NC}"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the issues above.${NC}"
    exit 1
fi