# RUNBOOK — Twoje kroki operacyjne (wersja niskokosztowa)

> Wszystko poniżej to jednorazowe klikanie (~1–2 h łącznie). Kolejność ma
> znaczenie. Koszt całości: **~17 zł/mies. + domena ~20–60 zł/rok**.
> Reszta (konfiguracja serwera, deploy, HTTPS, backupy) jest w kodzie
> tego repo i robi się sama.

## Koszty — podsumowanie

| Co | Gdzie | Koszt |
|---|---|---|
| Serwer VPS | Hetzner CAX11 (ARM, 2 vCPU / 4 GB) | ~4 €/mies. ≈ 17 zł |
| Domena | OVH / cyber_Folks / nazwa.pl (.pl) | ~20–60 zł/rok |
| DNS | Cloudflare (free) | 0 zł |
| E-maile (reset hasła) | Brevo free (300/dzień) | 0 zł |
| Monitoring | UptimeRobot free + Sentry free | 0 zł |
| Backupy | Backblaze B2 (free do 10 GB) | 0 zł |
| Płatności (dopiero M4) | Lemon Squeezy (% od transakcji) | 0 zł stałych |

## Krok 1 — Serwer (Hetzner, ~20 min)

1. Konto: https://accounts.hetzner.com/signUp (weryfikacja karta/PayPal).
2. Cloud Console → **New Project** „jafastage".
3. **Add Server**: lokalizacja **Falkenstein/Nuremberg**, obraz **Ubuntu 24.04**,
   typ **CAX11** (zakładka Arm64 — najtańszy, w zupełności wystarczy),
   sekcja **SSH keys → Add SSH key** (jak nie masz klucza: w PowerShell
   `ssh-keygen -t ed25519`, wklej zawartość `~/.ssh/id_ed25519.pub`),
   nazwa `jafastage-prod` → **Create & Buy now**.
4. Zanotuj **adres IP** serwera.
5. Cloud Console → serwer → **Firewall**: reguły „in": TCP 22, 80, 443.

### Wariant OVH (kupiony VPS-2: 4 vCore / 8 GB, Warszawa)

Krok 1 masz z głowy. Różnice względem Hetznera:
1. Panel OVH → Bare Metal Cloud → VPS → Twój serwer: tu znajdziesz **adres IP**.
2. SSH: jeśli przy zamówieniu nie podałeś klucza, OVH wysyła mailem hasło
   użytkownika (zwykle `ubuntu`, nie `root`). Logujesz się
   `ssh ubuntu@IP`, a w komendach kroku 4 poprzedzaj polecenia `sudo`
   (albo raz: `sudo -i` i dalej jak root).
3. Firewall: Ubuntu na OVH ma domyślnie otwarte porty — dla porządku:
   `sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable`
4. Backup: masz w pakiecie **Automated Backup** (snapshot całego serwera) —
   nasz nocny backup bazy (krok 7) i tak włącz: odzyskanie samej bazy jest
   szybsze niż odtwarzanie całego serwera.

## Krok 2 — Domena + DNS (~15 min)

1. Kup domenę (rekomendacja: krótka .pl; sprawdź promocje pierwszego roku
   na OVH.pl / cyberfolks.pl).
2. Załóż darmowe konto https://dash.cloudflare.com → **Add site** → wpisz
   domenę → plan Free → Cloudflare pokaże 2 serwery nazw (NS).
3. W panelu rejestratora domeny podmień serwery nazw (NS) na te z Cloudflare.
4. W Cloudflare → DNS → **Add record**: typ `A`, nazwa `app`,
   adres = IP serwera z kroku 1, Proxy **OFF (szare)** — ważne, bo Caddy
   sam wystawia certyfikat.

## Krok 3 — E-maile (Brevo free, ~10 min)

1. Konto: https://www.brevo.com (free: 300 maili/dzień — aż nadto).
2. Settings → **SMTP & API → SMTP**: skopiuj host, port, login i klucz SMTP.
3. Te 4 wartości wkleisz do pliku `.env` na serwerze (krok 4) jako
   `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
   oraz `SMTP_FROM="JafaStage <no-reply@twojadomena.pl>"`.
4. Żeby maile nie wpadały do spamu: w Brevo → Senders & Domains →
   **Authenticate domain** → dodaj podane rekordy DKIM w Cloudflare DNS.

## Krok 4 — Pierwsze wdrożenie (raz, ~20 min)

Na swoim komputerze (PowerShell / terminal), `IP` = adres z kroku 1:

```bash
ssh root@IP
# --- na serwerze ---
adduser --disabled-password --gecos "" deploy
mkdir -p /home/deploy/.ssh && cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
mkdir -p /srv/jafastage && chown deploy:deploy /srv/jafastage
su deploy
cd /srv && git clone -b web https://github.com/UKIII08/JafaStageCenter jafastage
cd jafastage/deploy
cp ../.env.example .env && nano .env   # uzupełnij wg komentarzy w pliku
# w Caddyfile podmień app.example.com na app.twojadomena.pl
nano Caddyfile
docker compose up -d --build
```

Po 1–2 minutach `https://app.twojadomena.pl` działa z ważnym certyfikatem.

## Krok 5 — Automatyczny deploy z GitHuba (~10 min)

1. Repo → **Settings → Secrets and variables → Actions**:
   - Secret `VPS_HOST` = IP serwera,
   - Secret `VPS_SSH_KEY` = zawartość Twojego PRYWATNEGO klucza
     (`~/.ssh/id_ed25519`),
   - zakładka **Variables**: `DEPLOY_ENABLED` = `true`.
2. Od teraz każdy push na gałąź `web` z zielonymi testami sam wdraża się
   na serwer.

## Krok 6 — Monitoring (10 min, darmowe)

1. https://uptimerobot.com → monitor HTTP na
   `https://app.twojadomena.pl/healthz`, alert na Twój e-mail.
2. https://sentry.io → nowy projekt Flask → skopiuj DSN → dopisz
   `SENTRY_DSN=...` do `.env` na serwerze i `docker compose up -d`.

## Backupy (zrobię w kodzie — Twoje 5 min)

Załóż konto https://www.backblaze.com/b2 (free 10 GB), utwórz bucket
`jafastage-backups` i klucz aplikacyjny; wartości `B2_KEY_ID`, `B2_APP_KEY`,
`B2_BUCKET` dopisz do `.env`. Skrypt nocnego backupu jest w repo.

---

### Później (nie teraz)
- **M4:** konto Lemon Squeezy (płatności) + 1 h z księgowym.
- **M6:** konto Microsoft Partner Center (~100 zł jednorazowo) pod Store.

## Backup — włączenie (po kroku 4)

Na serwerze, jako `deploy`:
```bash
crontab -e
# dodaj linię (backup codziennie 03:15):
15 3 * * * /srv/jafastage/deploy/backup.sh >> /srv/backups/backup.log 2>&1
```
Do `deploy/.env` dopisz `BACKUP_PASSPHRASE` (długie losowe zdanie — ZAPISZ JE
w bezpiecznym miejscu; bez niego backup jest nie do odczytania) oraz dane B2.
