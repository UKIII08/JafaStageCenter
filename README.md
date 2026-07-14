# Jonathan App — webowa aplikacja dla zespołów uwielbienia

Webowa (SaaS) część systemu JafaStage — hybrydowego narzędzia dla zespołów
uwielbienia. **Układ gałęzi w tym repozytorium:**

- `main` / gałęzie `claude/...` — aplikacja desktop (.exe), kod stabilny dla bety
- **`web` (ta gałąź)** — wersja webowa, budowana od zera wg PLAN.md; zero
  wspólnej historii z desktopem (orphan branch)

Role produktów:

- **Strona (to repo):** biblioteka piosenek, przygotowanie nabożeństw,
  zespół i profile muzyków, tryb ćwiczenia, „moje tonacje" oraz pełny tryb
  LIVE w przeglądarce (panel prowadzącego, ekrany muzyków, rzutnik).
- **Aplikacja desktop** (gałęzie desktopowe tego repo):
  granie na żywo po sieci lokalnej, offline-first; paruje się ze wspólnotą
  kodem i synchronizuje dane z chmurą.

Pełna architektura, model danych, przepływy i fazy wdrożenia: **[PLAN.md](PLAN.md)**.

## Stack

Flask + Flask-SocketIO + SQLAlchemy · PostgreSQL · Redis · Docker Compose ·
Caddy (auto-HTTPS) · deploy przez GitHub Actions na VPS.

## Struktura (docelowa)

```
app/            aplikacja Flask (blueprinty: auth, panel, live, api, sync)
music_core/     silnik muzyczny przeniesiony z desktopu (akordy, transpozycja,
                silniki przejść, konwerter formatów) + testy
templates/      widoki Jinja (panel, live, muzyk, rzutnik, ćwiczenie)
static/         JS/CSS (design-system współdzielony z desktopem)
deploy/         docker-compose, Caddyfile, skrypty
tests/          jednostkowe + tenancy + E2E (Playwright)
RUNBOOK.md      kroki operacyjne (serwer, domena, sekrety) — powstanie w M0
```

## Status

Faza **M0 — fundament** (auth, wspólnoty, zespół) — w budowie.
