# /done — Zamknij zadanie

Wykonaj pelna procedure zamkniecia zadania. Kroki w kolejnosci:

## 1. Sprawdz stan
- `git status` — czy sa niezcommitowane zmiany?
- Jesli NIE ma zmian — poinformuj uzytkownika i zakoncz

## 2. Ship-check (testy + build + visual)
- Backend testy: `cd backend && python -m pytest --tb=short -q`
- Frontend build: `cd frontend && npx vite build --mode development 2>&1 | tail -5`
- Visual check: uruchom `/visual-check` na zmienionych zakladkach — sprawdz screenshoty
- Jezeli cos FAILUJE — pokaz bledy i ZATRZYMAJ SIE. Nie commituj zepsutego kodu.
- Jezeli wszystko zielone — kontynuuj do commita

## 3. Commit
- Uzyj procedury /commit (git add odpowiednich plikow + git commit z sensownym message)

## 4. Synchronizacja dokumentacji
- Uruchom procedure /docs-sync — zaktualizuj PROGRESS.md i docs/API_ENDPOINTS.md

## 5. Commit dokumentacji
- Jesli docs-sync zmienil pliki: `git add PROGRESS.md docs/API_ENDPOINTS.md && git commit -m "docs: sync documentation with code"`

## 6. Push z PM check
- Uruchom `git push`
- Hook pre-push automatycznie odpali PM review
- Jesli PM review zablokuje push (ocena < 7/10) — pokaz raport PM i zapytaj uzytkownika co robic

## Format koncowy

Po zakonczeniu wypisz:
```
## Zadanie zamkniete
- Commit: [hash] [message]
- Docs: [zaktualizowane/brak zmian]
- Push: [OK/ZABLOKOWANY — powod]
- PM ocena: X/10
```
