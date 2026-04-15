#!/bin/bash
# Run Playwright tests with visible browser windows

echo "Starting Playwright tests with visible browser..."

# Kill any existing playwright/vite processes
pkill -f "playwright" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 2

# Run tests with headed mode and single worker to see each test
npx playwright test --headed --workers=1 --timeout=60000
