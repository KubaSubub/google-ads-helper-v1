@echo off
cls
echo.
echo ====================================================
echo   Google Ads Helper - Automatyczne uruchomienie
echo ====================================================
echo.
echo Przygotowuje aplikacje...
echo.

REM Sprawdz czy backend istnieje
if not exist "backend\app\main.py" (
    echo BLAD: Nie znaleziono backendu!
    pause
    exit /b 1
)

REM Sprawdz czy frontend istnieje
if not exist "frontend\package.json" (
    echo BLAD: Nie znaleziono frontendu!
    pause
    exit /b 1
)

REM Uruchom backend w tle
echo [1/3] Uruchamiam backend...
start /min "Google Ads - Backend" cmd /c "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

REM Poczekaj 5 sekund na start backendu
timeout /t 5 /nobreak > nul

REM Uruchom frontend w tle
echo [2/3] Uruchamiam frontend...
start /min "Google Ads - Frontend" cmd /c "cd frontend && npm run dev"

REM Poczekaj 5 sekund na start frontendu
timeout /t 5 /nobreak > nul

REM Otwórz przeglądarkę
echo [3/3] Otwieram aplikacje w przegladarce...
start http://localhost:5173

echo.
echo ====================================================
echo   APLIKACJA URUCHOMIONA!
echo ====================================================
echo.
echo Aplikacja otwiera sie w przegladarce.
echo.
echo Aby ZATRZYMAC aplikacje:
echo   - Nacisnij CTRL+C tutaj
echo   - Lub zamknij to okno
echo.
echo ====================================================
echo.

REM Czekaj na CTRL+C
:loop
timeout /t 1 > nul
goto loop
