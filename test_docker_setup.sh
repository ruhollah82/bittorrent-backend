#!/bin/bash
# Comprehensive Docker Setup Test Script
# Tests if all containers are working correctly

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Docker Setup Test Script${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if Docker is running
echo -e "${YELLOW}Checking Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}\n"

# Check if docker-compose is available
echo -e "${YELLOW}Checking Docker Compose...${NC}"
if ! docker-compose version > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker Compose is not available${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose is available${NC}\n"

# Check if containers are running
echo -e "${YELLOW}Checking containers...${NC}"
containers=("bittorrent_web" "bittorrent_db" "bittorrent_redis" "bittorrent_celery_worker" "bittorrent_celery_beat")

for container in "${containers[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${GREEN}✅ ${container} is running${NC}"
    else
        echo -e "${RED}❌ ${container} is not running${NC}"
        echo -e "${YELLOW}   Start with: docker-compose up -d${NC}"
    fi
done

echo ""

# Test database connection
echo -e "${YELLOW}Testing database connection...${NC}"
if docker-compose exec -T db pg_isready -U bittorrent_user > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Database is accessible${NC}"
else
    echo -e "${RED}❌ Database is not accessible${NC}"
fi

# Test Redis connection
echo -e "${YELLOW}Testing Redis connection...${NC}"
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is accessible${NC}"
else
    echo -e "${RED}❌ Redis is not accessible${NC}"
fi

# Test web server
echo -e "${YELLOW}Testing web server...${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/logs/health/ | grep -q "200"; then
    echo -e "${GREEN}✅ Web server is responding${NC}"
else
    echo -e "${RED}❌ Web server is not responding${NC}"
    echo -e "${YELLOW}   Check logs: docker-compose logs web${NC}"
fi

echo ""

# Run API tests
echo -e "${YELLOW}Running API tests...${NC}"
if docker-compose exec -T web python test_api_comprehensive.py http://localhost:8000 2>&1 | tee /tmp/api_test.log; then
    echo -e "${GREEN}✅ API tests completed${NC}"
else
    echo -e "${RED}❌ API tests failed${NC}"
    echo -e "${YELLOW}   Check logs: cat /tmp/api_test.log${NC}"
fi

echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}To view logs:${NC}"
echo -e "  docker-compose logs -f"
echo -e "${YELLOW}To restart services:${NC}"
echo -e "  docker-compose restart"
echo -e "${YELLOW}To stop services:${NC}"
echo -e "  docker-compose down"
echo ""

