# JafaStage Cloud — plan wdrożeniowy (v2, MODEL HYBRYDOWY)

> **Strona (SaaS)** = przygotowanie: piosenki, setlisty, zespół, ćwiczenie,
> preferencje; pełne LIVE w przeglądarce też działa (fallback np. dla Maców).
> **Aplikacja desktop (Microsoft Store)** = docelowe narzędzie do grania NA ŻYWO:
> offline-first (lokalna baza), dane wspólnoty pobiera z chmury po sparowaniu
> KODEM (bez logowania). Zmiany lokalne (np. profile muzyków) wysyłają się
> z powrotem do chmury.
> Wersja webowa powstaje w NOWYM repozytorium (`jafastage-cloud`); repo desktop
> pozostaje zamrożone do fazy M5, w której dostaje wyłącznie moduł synchronizacji.

---

## 0. Decyzje fundamentalne

| Decyzja | Wybór | Uzasadnienie |
|---|---|---|
| Repo | Nowe repo `jafastage-cloud` (nie branch) | Inny stack wdrożeniowy; zero ryzyka dla bety desktop |
| Backend | Flask + Flask-SocketIO + SQLAlchemy | Maksymalny transfer istniejącego kodu i wiedzy |
| Baza | PostgreSQL (prod) / SQLite (dev) | Multi-tenant, współbieżność, backupy |
| Cache / kolejka socketów | Redis | Flask-SocketIO przy >1 workerze; stan pokoi live |
| Frontend | Jinja + vanilla JS (jak desktop), docelowo PWA | Widoki band/stage/projector przenoszą się niemal wprost |
| Serwer | VPS Hetzner (~30 zł/mies.), Docker Compose, Caddy | Tanio, auto-HTTPS, odtwarzalny z plików w repo |
| Płatności | Lemon Squeezy lub Paddle (merchant of record) | Zero papierologii VAT/sales tax |
| Desktop ↔ chmura | Parowanie KODEM (bez logowania), sync offline-first | Prostota dla wspólnot + bezpieczeństwo tokenu na urządzenie |
| ID | UUID w URL-ach i sync | Bezpieczeństwo między-tenantowe, scalanie offline |

**Przenosimy z desktopu 1:1** (pakiet `music_core/`): process_song (pary
akord+sylaba), transpozycja z enharmonią, detekcja tonacji, walidacja,
konwerter „akordy nad tekstem", silniki przejść V2/V3/V4, i18n, design-system.
**Adaptujemy**: band_member/stage/projector/control (scope do pokoju,
preferencje z profilu).

---

## 1. Model danych

```
users
  id UUID PK, email UNIQUE, password_hash, display_name,
  locale, email_verified_at, created_at, last_login_at

churches
  id UUID PK, name, slug UNIQUE, owner_user_id FK,
  plan ENUM(free_beta, standard, pro), locale, timezone,
  settings JSONB (default_notation, transition_engine, projector_theme, logo),
  created_at

memberships                               -- konto w zespole wspólnoty
  id PK, user_id FK, church_id FK, UNIQUE(user_id, church_id),
  role ENUM(admin, prowadzacy, muzyk), status ENUM(active, invited, removed)

profiles                                  -- profil muzyka (KLUCZ HYBRYDY)
  id UUID PK, church_id FK, name, instrument, color,
  user_id FK NULLABLE,        -- NULL = profil utworzony w aplikacji desktop
                              -- bez konta; muzyk może go później "przejąć"
  prefs JSONB,  -- {show_chords, notation, lowercase_minor, capo_default,
                --  font_size, beginner_mode, diagram_instrument}
  updated_at, deleted BOOL    -- pola synchronizacji

invitations
  id PK, church_id FK, code VARCHAR(8) UNIQUE,  -- link/QR "dołącz do zespołu"
  email NULLABLE, role, expires_at, created_by FK, max_uses INT NULL, uses INT

songs
  id UUID PK, church_id FK, title, content TEXT (ChordPro),
  key VARCHAR, bpm INT, tags VARCHAR[], created_by FK,
  created_at, updated_at, deleted BOOL
  INDEX (church_id, title)

song_personal                             -- "moje tonacje" + notatki prywatne
  id PK, profile_id FK, song_id FK, UNIQUE(profile_id, song_id),
  preferred_transpose INT NULL,   -- muzyk: gram capo/w innej tonacji
  preferred_key VARCHAR NULL,     -- wokalista: moja wygodna tonacja
  note TEXT, updated_at
  -- kluczowane po PROFILU (nie koncie): działa tak samo dla muzyka
  -- zalogowanego na stronie i profilu z aplikacji desktop

setlists
  id UUID PK, church_id FK, name, service_date DATE NULL,
  status ENUM(draft, ready, archived), created_by FK, created_at, updated_at,
  deleted BOOL,
  items JSONB  -- [{song_id, transpose, custom_sections[], note}]

live_sessions                             -- wirtualny pokój LIVE (www)
  id UUID PK, church_id FK, setlist_id FK, code VARCHAR(6),
  started_by FK, started_at, ended_at NULL, is_practice BOOL,
  state JSONB  -- {song_idx, section_idx, blackout, logo, last_slide{...}}
  -- Faza 1: max 1 aktywna sesja na wspólnotę

screen_tokens                             -- rzutnik/TV bez konta (www live)
  id PK, church_id FK, token VARCHAR(32) UNIQUE, type ENUM(projector, stage),
  name VARCHAR, created_at, revoked_at NULL

pairing_codes                             -- parowanie aplikacji desktop KODEM
  id PK, church_id FK, code VARCHAR(9),   -- np. K7F3-QD2M, ważny 15 minut
  created_by FK, expires_at, used_at NULL

devices                                   -- sparowane aplikacje desktop
  id UUID PK, church_id FK, device_token VARCHAR(64) UNIQUE,
  name VARCHAR ("Laptop — sala główna"), last_sync_at, last_seen_version,
  created_at, revoked_at NULL

church_changes                            -- dziennik zmian do delta-sync
  seq BIGSERIAL PK, church_id FK,
  entity ENUM(song, setlist, profile, song_personal, settings),
  entity_id UUID, op ENUM(upsert, delete), updated_at

subscriptions
  church_id FK UNIQUE, provider, external_id, plan, status,
  trial_ends_at, current_period_end
```

Zasada twarda: **każde zapytanie filtrowane po `church_id`** (dekorator
`require_membership(role=...)` / `require_device_token`); testy tenancy w CI
od pierwszego dnia.

---

## 2. Role i uprawnienia

| Akcja | admin | prowadzący | muzyk |
|---|---|---|---|
| Wspólnota, płatności, członkowie, urządzenia | ✓ | — | — |
| Piosenki/setlisty: tworzenie, edycja | ✓ | ✓ | podgląd |
| Start/prowadzenie LIVE (www) | ✓ | ✓ | — |
| Dołączenie do LIVE, widok muzyka | ✓ | ✓ | ✓ |
| Profil, moje tonacje, notatki, ćwiczenie | ✓ | ✓ | ✓ |

Rzutnik/TV (www live) = `screen_token`. Aplikacja desktop = `device_token`
(pełny dostęp do danych wspólnoty — parowana przez admina/prowadzącego,
odwoływalna w panelu).

---

## 3. Kluczowe przepływy

### 3.1 Rejestracja wspólnoty (onboarding www)
1. Rejestracja e-mail+hasło → weryfikacja mailem.
2. „Załóż wspólnotę" (nazwa → slug) → użytkownik = admin (+ auto-profil).
3. Kreator: (a) dodaj/wklej pierwsze piosenki (konwerter UG), (b) zaproś
   zespół (link/QR), (c) podłącz ekran LUB sparuj aplikację desktop (kod).

### 3.2 Zapraszanie zespołu
- Panel „Zespół" → link `app.x/join/K7F3QD` (+ QR), rola domyślna `muzyk`;
  udostępniany na grupie WhatsApp wspólnoty.
- Wejście: logowanie/rejestracja → członkostwo + profil → ekran „ustaw
  instrument i preferencje".
- Zaproszenia imienne e-mailem dla ról prowadzący/admin.

### 3.3 Pokój LIVE w przeglądarce (fallback/Mac)
- Prowadzący: setlista → „Rozpocznij LIVE" → sesja + panel prowadzenia
  (dzisiejszy control: kafelki, PRZEJŚCIA, pad, blackout/logo, metronom).
- Muzyk: baner „🔴 LIVE trwa — dołącz" → widok muzyka z preferencjami
  z profilu. Spóźnieni dostają bieżący slajd (stan w Redis).
- Ekrany: projektor/TV na stałych URL-ach tokenowych.
- Socket.IO: room `live:{session_id}`, zdarzenia jak w desktopie, stan w Redis.

### 3.3a ARCHITEKTURA HYBRYDOWA: aplikacja desktop ⇄ chmura

**Zasada:** strona do przygotowania, apka do grania. Apka jest offline-first —
działa w 100% bez internetu na lokalnym SQLite; chmura jest źródłem prawdy,
z którym apka uzgadnia się, kiedy ma sieć.

**Parowanie (bez logowania):**
1. Admin w panelu www: „Urządzenia → Sparuj aplikację" → kod `K7F3-QD2M`
   (ważny 15 min) + QR.
2. W aplikacji: „Połącz ze wspólnotą" → wpisanie kodu → apka wymienia kod na
   trwały `device_token` (zapisany lokalnie) i robi pierwszy pełny import.
3. Kod jest JEDNORAZOWY (wymiana na token). Urządzenia widać w panelu www
   i można je odłączyć jednym kliknięciem — proste jak „wpisz kod",
   bezpieczne jak logowanie.

**Co się synchronizuje:** piosenki, setlisty, profile muzyków + preferencje
+ „moje tonacje", ustawienia wspólnoty. NIE: stan live, rzeczy chwilowe.

**Protokół (celowo prosty):**
- Rekordy mają `uuid`, `updated_at`, lokalnie `dirty` i `deleted` (tombstone).
- Pull: `GET /api/sync?since=<seq>` → delta z `church_changes`.
- Push: `POST /api/sync` z lokalnie zmienionymi rekordami.
- Konflikt: **last-write-wins per rekord**; wyjątek — piosenka zmieniona po
  obu stronach: przegrywająca wersja zapisuje się jako „Tytuł (konflikt
  z <data>)" — nigdy nie gubimy niczyjejś pracy.
- Kiedy: start apki, co 5 min w tle, po lokalnej zmianie (debounce),
  przycisk „Synchronizuj teraz". Pasek stanu: „✓ zsynchronizowano 12:41" /
  „⚠ offline — pracujesz lokalnie".

**Reguła UX ograniczająca konflikty (komunikowana wprost):** „Piosenki
i nabożeństwa przygotowuj na stronie; w aplikacji graj. Możesz edytować
w aplikacji offline — zmiany wyślą się, gdy wróci internet."

**Profile muzyków w hybrydzie:** profil nie wymaga konta. Utworzony
w aplikacji desktop → po sync widoczny na stronie; muzyk, który później
założy konto, „przejmuje" swój profil (admin podpina user_id) i ma te same
preferencje na telefonie (www) i w aplikacji.

### 3.4 Tryb ćwiczenia (www)
- **Solo (M3):** przycisk „Ćwicz" → pełny przewijany widok piosenki
  w MOJEJ tonacji (z `song_personal`), autoprzewijanie w tempie BPM,
  metronom (WebAudio), pad w tle, diagramy, prywatne notatki.
- **Próba zespołowa (po trakcji):** pokój live z flagą `is_practice` —
  nie rusza rzutników, każdy może się odpiąć od prowadzącego (follow/free).

### 3.5 Moje tonacje (muzycy i wokaliści)
- Na karcie piosenki każdy ustawia preferowaną tonację (wokal) albo
  transpozycję/capo (instrument) + prywatną notatkę.
- Ćwiczenie otwiera piosenkę w preferencji użytkownika.
- W LIVE pasek muzyka: „Live: A · Twoje capo 2 → chwyty G".
- **Podpowiedź dla prowadzącego** przy ustawianiu tonacji w setliście:
  zebrane preferencje zespołu („Kasia woli G · Tomek capo z D").

---

## 4. Mapa ekranów (www)

1. Landing (PL/EN) → rejestracja/logowanie.
2. **Panel wspólnoty**: dashboard (najbliższa setlista, LIVE, stan urządzeń),
   Piosenki (CRUD/import/konwerter UG), Setlisty (+historia, duplikowanie),
   Zespół (członkowie, role, link/QR), Urządzenia (aplikacje desktop — kod
   parowania; ekrany www — tokeny), Ustawienia, Płatności.
3. **LIVE — prowadzący** (adaptacja control).
4. **LIVE — muzyk** (adaptacja band_member).
5. **Rzutnik / TV** (adaptacja projector/stage).
6. **Ćwiczenie** (widok piosenki z narzędziami).
7. Konto: profil, hasło, moje wspólnoty.

---

## 5. API i zdarzenia

REST (sesyjne, CSRF):
```
POST /auth/register|login|logout|reset   GET /join/<code>
CRUD /api/songs /api/setlists            POST /api/songs/convert-format
GET/PUT /api/me/profile                  GET/PUT /api/songs/<id>/personal
POST /api/live/start /api/live/end       GET /api/live/current
POST /api/team/invite  DELETE /api/team/<member>
POST /api/screens  DELETE /api/screens/<id>
POST /api/billing/checkout  POST /webhooks/lemonsqueezy
-- hybryda (auth: device_token w nagłówku):
POST /api/pair  (code -> device_token)
GET  /api/sync?since=<seq>   POST /api/sync
GET  /api/devices  DELETE /api/devices/<id>   (panel www)
```
Socket.IO (room `live:{id}`): `join_live`, `update_slide`, `set_blackout`,
`set_logo`, `silent_md`, `session_ended`, `state_snapshot`.

---

## 6. Infrastruktura i bezpieczeństwo

- Docker Compose: `app` (gunicorn+eventlet), `postgres`, `redis`, `caddy`.
- CI (GitHub Actions): testy → build → deploy SSH; staging na subdomenie.
- Backupy: nocny `pg_dump` → Backblaze B2 (30 dni) + testy odtworzenia.
- Monitoring: `/healthz`, UptimeRobot, Sentry free, alerty mail.
- Bezpieczeństwo: argon2, rate-limit auth i /api/pair, CSRF, socket auth po
  sesji/tokenie, CSP/HSTS, RODO (polityka, eksport/kasowanie wspólnoty),
  agent DMCA przy wejściu do USA.
- Import z desktopu (przed M5): plik z „Eksportuj piosenki" — format obsłużony.

---

## 7. Fazy wdrożenia

### M0 — Fundament (repo, auth, wspólnoty, zespół)
Scaffold + compose + CI; users/churches/memberships/profiles/invitations;
rejestracja/logowanie/reset; założenie wspólnoty; panel Zespół z linkiem/QR.
**Odbiór:** 2 wspólnoty z odseparowanymi danymi (test tenancy w CI);
przepływ zaproszenia telefonem przez QR.

### M1 — Biblioteka i setlisty
Port `music_core` z testami; CRUD piosenek + import .txt + konwerter UG;
setlisty (kolejność, transpozycja, historia, duplikowanie).
**Odbiór:** parytet funkcji biblioteki z desktopem; testy music_core zielone.

### M2 — Pokój LIVE (www)
Cykl życia sesji; panel prowadzącego; widok muzyka (prefs z profilu); ekrany
tokenowe; przejścia V2/V3/V4; stan dla spóźnionych; blackout/logo; pad.
**Odbiór:** pełna „niedziela" w chmurze: laptop + 2 telefony + TV + rzutnik;
zerwanie i powrót Wi-Fi telefonu nie wywala widoku.

### M3 — Preferencje osobiste i ćwiczenie
`song_personal` (moje tonacje/notatki); podpowiedzi tonacji dla prowadzącego;
ćwiczenie solo (przewijanie, autoscroll, metronom, pad, diagramy).
**Odbiór:** dwóch użytkowników widzi tę samą piosenkę w różnych tonacjach;
prowadzący widzi preferencje zespołu przy setliście.

### M4 — Płatności i publiczna beta
Lemon Squeezy/Paddle + plany + trial 30 dni; landing PL/EN; ToS/privacy;
kreator onboardingu; e-maile transakcyjne.
**Odbiór:** obca wspólnota rejestruje się, testuje i płaci bez naszego udziału.

### M5 — Synchronizacja hybrydowa (chmura ⇄ aplikacja desktop)
Chmura: pairing_codes, devices, church_changes, /api/pair, /api/sync, panel
„Urządzenia". Desktop (TU odmrażamy repo desktop): ekran „Połącz ze
wspólnotą" (kod), migracja lokalnej bazy (uuid/updated_at/dirty/deleted),
silnik sync z LWW i kopiami konfliktów, pasek stanu, offline bez zmian.
**Odbiór:** piosenka dodana na stronie po ≤5 min jest w aplikacji; profil
muzyka utworzony w aplikacji OFFLINE po powrocie sieci jest na stronie;
symulowany konflikt edycji tworzy kopię — nic nie ginie.

### M6 — Microsoft Store
Pakowanie MSIX (baza w AppData, manifest, ikony), test LAN z paczki MSIX,
karta produktu (PL/EN), certyfikacja.
**Odbiór:** apka ze Store paruje się kodem i prowadzi live po LAN.

### (M7 — PWA offline na www: cache setlisty jako „kartka z akordami", gdy
padnie sieć w przeglądarce. Po trakcji — desktop już pokrywa offline.)

---

## 8. Podział pracy

**Ja:** całość kodu i konfiguracji — scaffold, modele, auth, panele, port
music_core i widoków, sockety, sync, płatności, CI/CD, testy (jednostkowe +
tenancy + E2E Playwright), landing, drafty ToS/privacy, RUNBOOK.md z Twoimi
krokami klik-po-kliku.

**Ty (jednorazowo):** repo `jafastage-cloud` na GitHubie + dostęp, konto
Hetzner i domena (wg RUNBOOKa), konto Lemon Squeezy/Paddle, Sentry/UptimeRobot
(darmowe), 1 h z księgowym przy M4, konto Microsoft Partner Center (~100 zł)
przy M6.

**Potwierdzone założenia:** 1 aktywny pokój live na wspólnotę (start);
desktop bez logowania — tylko kod parowania; strona = przygotowanie,
apka = granie (komunikowane w UI).
