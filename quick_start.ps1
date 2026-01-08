"""
🚀 QUICK START - Agent Integration Test
Run this to verify everything is connected
"""

# Change to project directory
cd C:\Users\SONUR\projects\side-effects

# Test 1: Check if DataQualityAgent is accessible
Write-Host "`n=== Testing DataQualityAgent ===" -ForegroundColor Cyan
python -c "from dataQualityAgent import DataQualityAgent; print('✅ DataQualityAgent imported')"

# Test 2: Check if integration module works
Write-Host "`n=== Testing Integration Module ===" -ForegroundColor Cyan
python -c "import sys; sys.path.append('backend'); from agent_integration import initialize_data_quality_agent; print('✅ Integration module working')"

# Test 3: Start Flask backend (in background)
Write-Host "`n=== Starting Flask Backend ===" -ForegroundColor Cyan
Write-Host "Backend will run on http://localhost:5000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

# Start the backend
python backend/app.py
