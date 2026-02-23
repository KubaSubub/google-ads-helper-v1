@echo off
echo ========================================
echo   Google Ads Helper - Development Mode
echo ========================================
echo.

echo [1/3] Starting Backend (FastAPI)...
start "Google Ads Backend" cmd /k "cd backend && uvicorn app.main:app --reload --port 8000"
timeout /t 3 /nobreak > nul

echo [2/3] Starting Frontend (Vite)...
start "Google Ads Frontend" cmd /k "cd frontend && npm run dev"
timeout /t 3 /nobreak > nul

echo [3/3] Opening browser...
timeout /t 2 /nobreak > nul
start http://localhost:5173

echo.
echo ========================================
echo   Application started successfully!
echo ========================================
echo    Backend API:  http://127.0.0.1:8000/docs
echo    Frontend UI:  http://localhost:5173
echo.
echo ⚠️  IMPORTANT: To stop the application:
echo    - Close BOTH terminal windows (Backend + Frontend)
echo    - OR press Ctrl+C in each window individually
echo.
echo    Closing THIS window will NOT stop the servers!
echo ========================================
echo.
pause
