# /visual-check — Wizualna weryfikacja aplikacji

Uruchom backend + frontend, przejdź Playwrightem po zakładkach, zrób screenshoty i zweryfikuj co się renderuje.

## Argument

Opcjonalny: nazwa zakładki (np. "dashboard", "search-optimization"). Bez argumentu — sprawdź WSZYSTKIE zakładki.

## Workflow

### 1. Uruchom serwery (jeśli nie działają)

Sprawdź czy serwery działają:
```bash
curl -s http://localhost:8000/health 2>/dev/null | head -1
curl -s http://localhost:5173/ 2>/dev/null | head -1
```

Jeśli nie działają:
```bash
cd backend && uvicorn app.main:app --reload --port 8000 &
cd frontend && npm run dev &
```
Poczekaj aż oba będą dostępne (max 15s).

### 2. Uruchom Playwright screenshot test

Uruchom skrypt e2e który:
- Przechodzi po każdej zakładce (lub wskazanej)
- Robi screenshot każdej strony
- Sprawdza: czy strona się załadowała (brak "Loading..." po 5s), czy nie ma JS errors, czy główna treść jest widoczna
- Zapisuje screenshoty do `frontend/e2e-screenshots/`

```bash
cd frontend && npx playwright test e2e/visual-audit.spec.js --reporter=list
```

### 3. Przeczytaj screenshoty i raportuj

Dla każdej zakładki:
- Przeczytaj screenshot (Read tool na plik PNG)
- Oceń: czy strona wygląda poprawnie, czy dane się załadowały, czy layout jest OK
- Zanotuj problemy wizualne

### 4. Raport

```markdown
## Visual Check — {data}

| Zakładka | Screenshot | Status | Problemy |
|----------|-----------|--------|----------|
| Dashboard | ✅ | OK | — |
| Keywords | ⚠️ | PARTIAL | Brak danych w tabeli |
| ... | ❌ | FAIL | Biały ekran / JS error |

Problemy krytyczne: X
Problemy wizualne: Y
Zakładki OK: Z/16
```

## Integracja z pipeline

Ten krok jest OBOWIĄZKOWY w:
- `/done` — przed push (po ship-check, przed commit)
- `/ceo` faza VERIFY (4a) — obok testów i buildu
- `/ads-user` — zamiast wyobrażania sobie UI z kodu, patrz na screenshoty

## Zasady

- NIGDY nie raportuj że UI działa bez zobaczenia screenshotu
- Jeśli screenshot pokazuje "Loading..." lub pusty ekran — to jest FAIL
- Jeśli screenshot pokazuje "Brak danych" — to jest OK (ale zanotuj)
- Porównuj z design system v2 (ciemne tło, Syne headings, v2-card karty)
