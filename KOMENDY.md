# Ściąga — Komendy i Skille

## Kiedy co użyć?

### Nowy ficzer / zadanie produktowe
```
/ceo {krótka nazwa}
```
Pełny pipeline: intelligence → assess → PM spec → build → verify → ship.
Użyj gdy nie wiesz co dalej lub chcesz autonomiczny sprint.

### Wiem dokładnie co zrobić
```
/cto {opis zadania}
```
Router: deleguje do /build z odpowiednim kontekstem. Pomija CEO/PM.

### Bug do naprawienia
```
/fix-bug {opis buga}
```
Test-first: najpierw failing test → fix → boundary tests → regression-lock.
Gwarantuje że bug nie wróci.

### Review zakładki (głęboki)
```
/audit-deep {nazwa zakładki}
```
3 etapy: ads-user → ads-expert → ads-critic (odrzuca płytkie review).
Użyj gdy chcesz naprawdę wiedzieć co nie działa.

### Review zakładki (standardowy)
```
/ads-user {nazwa zakładki}
```
Symulacja Marka (PPC specialist) → auto-chain ads-expert → ads-verify.

### Zamknij zadanie i wypchnij
```
/done
```
commit + docs-sync + pm-check + push.

### Synchronizuj dokumentację
```
/docs-sync
```
Aktualizuje PROGRESS.md i API_ENDPOINTS.md na podstawie kodu.

---

## Wszystkie skille

| Komenda | Kiedy |
|---------|-------|
| `/ceo` | Nowe zadanie, nie wiesz od czego zacząć, autonomiczny sprint |
| `/cto {zadanie}` | Wiesz co zrobić, chcesz pełny build pipeline |
| `/fix-bug {opis}` | Bug — z gwarancją że nie wróci (regression-lock) |
| `/audit-deep {tab}` | Głęboki audit zakładki z meta-krytykiem |
| `/ads-user {tab}` | Symulacja PPC specialist → auto ads-expert → ads-verify |
| `/ads-expert {tab}` | Tylko ekspert Google Ads (bez UX simulation) |
| `/ads-verify {tab}` | Plan implementacji na podstawie raportu ads-expert |
| `/sprint {tab}` | Wykonaj plan z ads-verify |
| `/ads-check {tab}` | Weryfikacja czy sprint był wykonany poprawnie |
| `/build {opis}` | Bezpośredni build pipeline (6 faz) |
| `/review` | Code review: 3 agenty równolegle (quality + security + domain) |
| `/done` | Zamknij zadanie: commit + docs-sync + push |
| `/docs-sync` | Sync PROGRESS.md i API_ENDPOINTS.md z kodem |
| `/pm-check` | PM gate — score >= 7/10 pozwala na push |
| `/commit` | Smart commit z conventional prefix |
| `/debug {opis}` | Debug konkretnego problemu |
| `/start` | Uruchom serwery (backend + frontend) |
| `/seed` | Regeneruj bazę danych |
| `/audit` | Pełny audit projektu |
| `/intelligence` | Market research — competitor scan, platform alerts |
| `/strategist` | Wizja produktu, roadmapa v1.1+ |
| `/competitor` | Devil's advocate — krytyczna analiza decyzji |
| `/sync-check` | Sprawdź spójność docs vs kod |
| `/visual-check` | Playwright screenshoty + weryfikacja UI |

---

## Typowe scenariusze

**"Chcę nową funkcję"**
→ `/ceo {nazwa funkcji}`

**"Coś się sypie"**
→ `/fix-bug {opis}`

**"Czy ta zakładka jest dobra?"**
→ `/audit-deep {tab}` (głęboko) lub `/ads-user {tab}` (szybciej)

**"Skończyłem, chcę wypchnąć"**
→ `/done`

**"Docs są nieaktualne"**
→ `/docs-sync`

**"Co dalej w projekcie?"**
→ `/ceo` (bez argumentów)
