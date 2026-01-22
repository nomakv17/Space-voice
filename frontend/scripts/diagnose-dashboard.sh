#!/bin/bash
# Dashboard Diagnostic Script
# Run this to diagnose issues with the dashboard

echo "=================================="
echo "SpaceVoice Dashboard Diagnostics"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check backend
echo "1. Checking Backend (http://localhost:8000)..."
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)
if [ "$BACKEND_STATUS" = "200" ]; then
    echo -e "   ${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "   ${RED}✗ Backend returned status: $BACKEND_STATUS${NC}"
    echo "   → Start backend: cd backend && uv run uvicorn app.main:app --reload"
fi

# Check database
echo ""
echo "2. Checking Database..."
DB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/db 2>/dev/null)
if [ "$DB_STATUS" = "200" ]; then
    echo -e "   ${GREEN}✓ Database is connected${NC}"
else
    echo -e "   ${RED}✗ Database check returned: $DB_STATUS${NC}"
    echo "   → Start PostgreSQL: docker-compose up -d postgres"
fi

# Check Redis
echo ""
echo "3. Checking Redis..."
REDIS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/redis 2>/dev/null)
if [ "$REDIS_STATUS" = "200" ]; then
    echo -e "   ${GREEN}✓ Redis is connected${NC}"
else
    echo -e "   ${RED}✗ Redis check returned: $REDIS_STATUS${NC}"
    echo "   → Start Redis: docker-compose up -d redis"
fi

# Check frontend
echo ""
echo "4. Checking Frontend (http://localhost:3001)..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 2>/dev/null)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo -e "   ${GREEN}✓ Frontend is running${NC}"
else
    echo -e "   ${RED}✗ Frontend not responding (status: $FRONTEND_STATUS)${NC}"
    echo "   → Start frontend: cd frontend && npm run dev"
fi

# Check API endpoints
echo ""
echo "5. Checking API Endpoints..."
echo "   Testing /api/v1/phone-numbers..."
PN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/phone-numbers 2>/dev/null)
if [ "$PN_STATUS" = "401" ]; then
    echo -e "   ${GREEN}✓ Phone numbers endpoint exists (401 = needs auth)${NC}"
elif [ "$PN_STATUS" = "200" ]; then
    echo -e "   ${GREEN}✓ Phone numbers endpoint working${NC}"
else
    echo -e "   ${YELLOW}⚠ Phone numbers endpoint returned: $PN_STATUS${NC}"
fi

echo ""
echo "=================================="
echo "Diagnostic Summary"
echo "=================================="

if [ "$BACKEND_STATUS" = "200" ] && [ "$FRONTEND_STATUS" = "200" ]; then
    echo -e "${GREEN}All services are running!${NC}"
    echo ""
    echo "If you still see 'fetch error', check:"
    echo "  1. Browser console for specific error messages"
    echo "  2. Are you logged in? (check localStorage for access_token)"
    echo "  3. Run E2E tests: npm run test:e2e:diagnose"
else
    echo -e "${RED}Some services are not running.${NC}"
    echo ""
    echo "Quick Start:"
    echo "  docker-compose up -d           # Start DB + Redis"
    echo "  cd backend && uv run uvicorn app.main:app --reload &"
    echo "  cd frontend && npm run dev &"
fi

echo ""
echo "=================================="
