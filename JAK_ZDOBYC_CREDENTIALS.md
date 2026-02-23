# Jak zdobyć Google Ads API Credentials

Ten przewodnik krok-po-kroku pomoże Ci uzyskać wszystkie wymagane dane do połączenia z Google Ads API.

---

## Czego potrzebujesz

Google Ads Helper wymaga **4 wartości** do połączenia z Google Ads API:

1. **GOOGLE_CLIENT_ID** — identyfikator aplikacji OAuth 2.0
2. **GOOGLE_CLIENT_SECRET** — sekret aplikacji OAuth 2.0
3. **GOOGLE_DEVELOPER_TOKEN** — token deweloperski Google Ads API
4. **GOOGLE_LOGIN_CUSTOMER_ID** — ID konta menedżerskiego (MCC) lub klienta

---

## Krok 1: Utwórz projekt w Google Cloud Console

### 1.1 Przejdź do Google Cloud Console

Otwórz: **https://console.cloud.google.com/**

### 1.2 Utwórz nowy projekt

1. Kliknij **"Select a project"** (górny pasek)
2. Kliknij **"NEW PROJECT"**
3. Wprowadź nazwę: `Google Ads Helper` (lub dowolną)
4. Kliknij **"CREATE"**

### 1.3 Poczekaj na utworzenie projektu

Google Cloud automatycznie przełączy Cię na nowy projekt (może to zająć 10-30 sekund).

---

## Krok 2: Włącz Google Ads API

### 2.1 Przejdź do API Library

1. W menu po lewej stronie → **"APIs & Services"** → **"Library"**
2. Lub bezpośrednio: **https://console.cloud.google.com/apis/library**

### 2.2 Wyszukaj Google Ads API

1. W wyszukiwarce wpisz: `Google Ads API`
2. Kliknij na wynik: **"Google Ads API"**

### 2.3 Włącz API

1. Kliknij przycisk **"ENABLE"**
2. Poczekaj 5-10 sekund na aktywację

---

## Krok 3: Utwórz OAuth 2.0 Credentials

### 3.1 Przejdź do Credentials

1. W menu po lewej → **"APIs & Services"** → **"Credentials"**
2. Lub bezpośrednio: **https://console.cloud.google.com/apis/credentials**

### 3.2 Skonfiguruj OAuth Consent Screen (WYMAGANE przed utworzeniem credentials)

1. Kliknij **"CONFIGURE CONSENT SCREEN"**
2. Wybierz **"External"** (jeśli nie masz Google Workspace)
3. Kliknij **"CREATE"**

**Wypełnij formularz:**
- **App name:** `Google Ads Helper`
- **User support email:** Twój email Google
- **Developer contact email:** Twój email Google
- **Authorized domains:** (zostaw puste dla aplikacji desktopowej)

4. Kliknij **"SAVE AND CONTINUE"**
5. **Scopes:** Kliknij **"SAVE AND CONTINUE"** (nie dodawaj nic)
6. **Test users:** Kliknij **"ADD USERS"**, dodaj swój email Google
7. Kliknij **"SAVE AND CONTINUE"**

### 3.3 Utwórz OAuth Client ID

1. Kliknij **"+ CREATE CREDENTIALS"** (górny pasek)
2. Wybierz **"OAuth client ID"**

**W formularzu:**
- **Application type:** `Desktop app`
- **Name:** `Google Ads Helper Desktop`

3. Kliknij **"CREATE"**

### 3.4 Skopiuj Client ID i Client Secret

Po utworzeniu pojawi się okno z credentials:

```
Client ID:     123456789012-abcdefghijklmnop.apps.googleusercontent.com
Client Secret: GOCSPX-abcdefghijklmnopqrstuvwxyz
```

**✅ ZAPISZ TE WARTOŚCI** — będą potrzebne w KONFIGURACJA_GOOGLE_ADS.bat

---

## Krok 4: Uzyskaj Developer Token

### 4.1 Przejdź do Google Ads API Center

Otwórz: **https://ads.google.com/aw/apicenter**

**Uwaga:** Musisz być zalogowany na konto Google które ma dostęp do Google Ads.

### 4.2 Sprawdź status Developer Token

Zobaczysz jedną z dwóch sytuacji:

**Sytuacja A: Masz już token**
- Developer Token: `AbCd1234EfGh5678` (przykład)
- Status: `Approved` lub `In Review`

**Sytuacja B: Brak tokenu**
- Kliknij **"Request a token"**
- Wypełnij formularz (nazwa aplikacji, cel użycia)
- Poczekaj na zatwierdzenie (może zająć 24-48h)

### 4.3 Skopiuj Developer Token

**✅ ZAPISZ TĘ WARTOŚĆ** — będzie potrzebna w KONFIGURACJA_GOOGLE_ADS.bat

**WAŻNE:** Jeśli Twój token ma status `In Review`, możesz go używać w **test mode** (ograniczone do kont testowych). Dla produkcyjnego użycia poczekaj na `Approved`.

---

## Krok 5: Znajdź Login Customer ID

### 5.1 Przejdź do Google Ads

Otwórz: **https://ads.google.com/**

### 5.2 Sprawdź ID konta

**Opcja A: Konto menedżerskie (MCC)**

Jeśli zarządzasz wieloma kontami Google Ads:
1. Kliknij ikonę narzędzi (klucz) → **"Manager Account settings"**
2. Znajdź **"Customer ID"** w formie: `123-456-7890`
3. **Usuń kreski:** `1234567890` ← to jest Twój LOGIN_CUSTOMER_ID

**Opcja B: Pojedyncze konto klienta**

Jeśli masz jedno konto Google Ads:
1. W górnym rogu ekranu zobaczysz ID konta: `123-456-7890`
2. **Usuń kreski:** `1234567890` ← to jest Twój LOGIN_CUSTOMER_ID

**✅ ZAPISZ TĘ WARTOŚĆ** — będzie potrzebna w KONFIGURACJA_GOOGLE_ADS.bat

---

## Krok 6: Uruchom wizard konfiguracji

Teraz masz wszystkie 4 wartości:

- ✅ **GOOGLE_CLIENT_ID:** `123456789012-abcdefghijklmnop.apps.googleusercontent.com`
- ✅ **GOOGLE_CLIENT_SECRET:** `GOCSPX-abcdefghijklmnopqrstuvwxyz`
- ✅ **GOOGLE_DEVELOPER_TOKEN:** `AbCd1234EfGh5678`
- ✅ **GOOGLE_LOGIN_CUSTOMER_ID:** `1234567890`

**Uruchom:**

```
KONFIGURACJA_GOOGLE_ADS.bat
```

Wizard poprosi Cię o wprowadzenie każdej wartości (copy-paste) i zapisze je w `backend/.env`.

---

## Krok 7: Testowanie połączenia

### 7.1 Uruchom aplikację

```
URUCHOM_APLIKACJE.bat
```

### 7.2 Logowanie OAuth

1. Aplikacja otworzy przeglądarkę z prośbą o zalogowanie do Google
2. Zaloguj się kontem Google które ma dostęp do Google Ads
3. Kliknij **"Allow"** (zezwól aplikacji na dostęp do Google Ads)

### 7.3 Sprawdź połączenie

W aplikacji:
1. Kliknij zakładkę **"Klienci"**
2. Kliknij przycisk **"Sync"** przy dowolnym kliencie
3. Jeśli sync się powiedzie → **✅ Połączenie działa!**

---

## Rozwiązywanie problemów

### Błąd: "Invalid developer token"

**Przyczyna:** Developer Token nieprawidłowy lub nie został jeszcze zatwierdzony.

**Rozwiązanie:**
1. Sprawdź status tokenu: https://ads.google.com/aw/apicenter
2. Jeśli status `In Review` → możesz używać tylko z kontami testowymi
3. Jeśli status `Approved` → sprawdź czy skopiowałeś cały token (bez spacji)

### Błąd: "Invalid client_id" lub "Invalid client_secret"

**Przyczyna:** Nieprawidłowy OAuth Client ID lub Secret.

**Rozwiązanie:**
1. Wróć do: https://console.cloud.google.com/apis/credentials
2. Znajdź swój OAuth Client ID (nazwa: `Google Ads Helper Desktop`)
3. Kliknij ikonę ołówka (edit)
4. Skopiuj ponownie Client ID i Client Secret
5. Uruchom ponownie: `KONFIGURACJA_GOOGLE_ADS.bat`

### Błąd: "Customer not found"

**Przyczyna:** Nieprawidłowy Login Customer ID.

**Rozwiązanie:**
1. Sprawdź czy usunąłeś kreski (prawidłowy format: `1234567890`)
2. Sprawdź czy konto Google którego używasz ma dostęp do tego Customer ID
3. Jeśli masz MCC → użyj MCC ID (nie ID pojedynczego klienta)

### Błąd: "Access denied"

**Przyczyna:** Konto Google którym się logujesz nie ma dostępu do Google Ads API.

**Rozwiązanie:**
1. W Google Cloud Console → OAuth Consent Screen → **Test users**
2. Dodaj email konta Google które będziesz używać
3. Zaloguj się ponownie w aplikacji

---

## Bezpieczeństwo credentials

### ✅ Dobre praktyki

- **NIGDY** nie udostępniaj pliku `backend/.env` nikomu
- **NIGDY** nie commituj `backend/.env` do Git (jest w `.gitignore`)
- **ZAWSZE** trzymaj Developer Token w tajemnicy (jak hasło)

### ⚠️ Co jeśli credentials wyciekły?

**Jeśli podejrzewasz, że Twoje credentials zostały skompromitowane:**

1. **OAuth Client Secret:**
   - Google Cloud Console → Credentials → Twój Client ID → **"RESET SECRET"**
   - Uruchom ponownie `KONFIGURACJA_GOOGLE_ADS.bat` z nowym secretem

2. **Developer Token:**
   - Nie można go zmienić samodzielnie
   - Kontakt z Google Ads API Support: https://developers.google.com/google-ads/api/support

---

## Przydatne linki

- **Google Cloud Console:** https://console.cloud.google.com/
- **Google Ads API Center:** https://ads.google.com/aw/apicenter
- **Google Ads API Documentation:** https://developers.google.com/google-ads/api/docs/start
- **OAuth 2.0 Setup Guide:** https://developers.google.com/google-ads/api/docs/oauth/cloud-project

---

## Dalsze kroki

Po pomyślnym skonfigurowaniu credentials:

1. Przeczytaj **PROGRESS.md** — co jest zrobione, co planowane
2. Przeczytaj **CLAUDE.md** — architektura aplikacji
3. Testuj aplikację lokalnie przed deploymentem

Powodzenia! 🚀
