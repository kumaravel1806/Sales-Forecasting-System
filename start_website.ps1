# Retail Forecasting Website Auto-Starter
Write-Host "🚀 Starting Retail Forecasting Website..." -ForegroundColor Green
Write-Host ""

# Change to backend directory
Set-Location "c:\Users\Gopinath C\OneDrive\Desktop\Jason_Forecasting\backend"

# Start backend server in new window
Write-Host "📡 Starting backend server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python app.py" -WindowStyle Normal

# Wait for server to start
Write-Host "⏳ Waiting for server to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 6

# Test if server is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "✅ Backend server is running!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Backend might still be starting..." -ForegroundColor Yellow
}

# Open website in default browser
Write-Host "🌐 Opening website in browser..." -ForegroundColor Cyan
Start-Process "http://localhost:8000"

Write-Host ""
Write-Host "🎉 Website Started Successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Quick Access URLs:" -ForegroundColor White
Write-Host "   Main Site: http://localhost:8000" -ForegroundColor Gray
Write-Host "   Login: http://localhost:8000/login.html" -ForegroundColor Gray
Write-Host "   Admin: http://localhost:8000/admin_dashboard.html" -ForegroundColor Gray
Write-Host ""
Write-Host "🔑 Admin Login:" -ForegroundColor White
Write-Host "   Email: admin@example.com" -ForegroundColor Gray
Write-Host "   Password: password" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  Keep the backend server window open!" -ForegroundColor Red
Write-Host ""

Read-Host "Press Enter to close this window"
