@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo   Google Ads Helper - Konfiguracja API
echo ========================================
echo.
echo Ten wizard pomoże Ci skonfigurować połączenie z Google Ads API.
echo.
echo Będziesz potrzebował:
echo   1. Developer Token (z Google Ads API Center)
echo   2. OAuth 2.0 Client ID (z Google Cloud Console)
echo   3. OAuth 2.0 Client Secret (z Google Cloud Console)
echo   4. Login Customer ID (Twój MCC ID lub Customer ID)
echo.
echo Gdzie to znaleźć:
echo   - Developer Token: https://ads.google.com/aw/apicenter
echo   - OAuth credentials: https://console.cloud.google.com/apis/credentials
echo.
echo Jeśli nie wiesz jak to zdobyć, przeczytaj:
echo   JAK_ZDOBYC_CREDENTIALS.md
echo.
echo ========================================
echo.

REM Prompt for Developer Token
set /p DEVELOPER_TOKEN="Wprowadź GOOGLE_DEVELOPER_TOKEN: "
if "!DEVELOPER_TOKEN!"=="" (
    echo.
    echo ❌ Error: Developer Token nie może być pusty
    pause
    exit /b 1
)

echo.
REM Prompt for Client ID
set /p CLIENT_ID="Wprowadź GOOGLE_CLIENT_ID: "
if "!CLIENT_ID!"=="" (
    echo.
    echo ❌ Error: Client ID nie może być pusty
    pause
    exit /b 1
)

echo.
REM Prompt for Client Secret
set /p CLIENT_SECRET="Wprowadź GOOGLE_CLIENT_SECRET: "
if "!CLIENT_SECRET!"=="" (
    echo.
    echo ❌ Error: Client Secret nie może być pusty
    pause
    exit /b 1
)

echo.
REM Prompt for Login Customer ID
set /p LOGIN_CUSTOMER_ID="Wprowadź GOOGLE_LOGIN_CUSTOMER_ID (bez kresek, np. 1234567890): "
if "!LOGIN_CUSTOMER_ID!"=="" (
    echo.
    echo ❌ Error: Login Customer ID nie może być pusty
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Zapisuję konfigurację...
echo ========================================

REM Check if backend/.env exists
if not exist "backend\.env" (
    echo.
    echo ❌ Error: Plik backend\.env nie istnieje
    echo    Utworzę go z szablonu backend\.env.example...

    if not exist "backend\.env.example" (
        echo ❌ Error: Brak backend\.env.example
        echo    Nie mogę kontynuować.
        pause
        exit /b 1
    )

    copy "backend\.env.example" "backend\.env" >nul
    echo ✅ Utworzono backend\.env
)

REM Create backup
copy "backend\.env" "backend\.env.backup" >nul 2>&1
echo 📋 Backup: backend\.env.backup

REM Replace placeholders using PowerShell
powershell -Command "(Get-Content 'backend\.env') -replace 'GOOGLE_ADS_DEVELOPER_TOKEN=.*', 'GOOGLE_ADS_DEVELOPER_TOKEN=!DEVELOPER_TOKEN!' | Set-Content 'backend\.env'"
powershell -Command "(Get-Content 'backend\.env') -replace 'GOOGLE_ADS_CLIENT_ID=.*', 'GOOGLE_ADS_CLIENT_ID=!CLIENT_ID!' | Set-Content 'backend\.env'"
powershell -Command "(Get-Content 'backend\.env') -replace 'GOOGLE_ADS_CLIENT_SECRET=.*', 'GOOGLE_ADS_CLIENT_SECRET=!CLIENT_SECRET!' | Set-Content 'backend\.env'"
powershell -Command "(Get-Content 'backend\.env') -replace 'GOOGLE_ADS_LOGIN_CUSTOMER_ID=.*', 'GOOGLE_ADS_LOGIN_CUSTOMER_ID=!LOGIN_CUSTOMER_ID!' | Set-Content 'backend\.env'"

echo.
echo ========================================
echo   ✅ Konfiguracja zapisana pomyślnie!
echo ========================================
echo.
echo Credentials zapisane w: backend\.env
echo Backup poprzedniej wersji: backend\.env.backup
echo.
echo Co dalej:
echo   1. Uruchom: URUCHOM_APLIKACJE.bat
echo   2. W przeglądarce otworzy się strona logowania Google
echo   3. Zaloguj się kontem które ma dostęp do Google Ads
echo   4. Aplikacja pobierze dane z Google Ads API
echo.
echo ⚠️  WAŻNE: Plik backend\.env zawiera sekrety!
echo    - NIE udostępniaj tego pliku nikomu
echo    - Jest już w .gitignore (nie trafi do Git)
echo.
echo ========================================
echo.
pause
