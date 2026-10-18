# Jonathan — Aranżacje, nagrania z prób i skrypt do Reapera

> Plan funkcji (do napisania na gałęzi `web`). Status: **ustalony, nie zaczęty.**
> Cel: to, co zespół wymyśli na próbie (głosy, melodyjki, forma), ma zostać
> zapisane i być do przećwiczenia w trybie ćwiczenia — wewnętrznie, tylko dla
> członków wspólnoty.

---

## 1. Pojęcia

| Pojęcie | Co to jest |
|---|---|
| **Piosenka** | jak dziś: tekst + akordy (ChordPro) podzielone na sekcje |
| **Aranżacja** | „jak MY to gramy”. Piosenka ma **Główną** + opcjonalnie inne („Akustyczna”, „Wielkanoc”…) |
| **Forma** | kolejność **kafelków** w aranżacji: `Intro → Z1 → Refren → Z2 → Refren → Bridge ×2 → Refren` |
| **Kafelek** | jedna część formy: odwołanie do sekcji piosenki + powtórzenia (×2) + dynamika (cicho / build / pełno…) |
| **Obsada** | lista **ról** (instrumentów) w aranżacji, np. `Wokal`, `Wokal 2`, `Gitara akustyczna`, `Piano`, `Skrzypce` |
| **Komórka** | rola × kafelek: notatka (np. „tercja w górę”, tab gitarowy) i opcjonalnie krótkie nagranie z telefonu |
| **Nagranie aranżacji** | pliki z Reapera: miks + wersje per rola, z pozycjami kafelków w czasie |

---

## 2. Obsada = instrumenty, nie osoby

- Każdy użytkownik ma w profilu **listę swoich instrumentów** (dziś jest jedno pole tekstowe →
  zmiana na listę). Np. X: `Wokal`, `Gitara akustyczna`; Y: `Piano`, `Skrzypce`.
- Przy dodawaniu roli do obsady lista podpowiedzi = **suma instrumentów członków wspólnoty**
  (Wokal, Gitara akustyczna, Piano, Skrzypce…).
- Można dodać kolejny egzemplarz: `Wokal 2`, `Gitara akustyczna 2` (numer dokłada się sam).
- Muzyk w trybie ćwiczenia widzi role ze swoich instrumentów; jeśli pasuje kilka
  (np. Wokal i Wokal 2) — wybiera raz, Jonathan zapamiętuje wybór per aranżacja.

---

## 3. Kto co edytuje

| Co | Kto |
|---|---|
| Forma (kafelki, kolejność, ×2, dynamika) | **każdy** członek zespołu |
| Obsada (dodaj/usuń rolę) | **każdy** |
| Komórki (notatki, nagrania z telefonu) | **każdy** |
| Wysyłanie nagrań z Reapera | **tylko jeden komputer** (token studia) |
| Tworzenie / usuwanie aranżacji | każdy tworzy; usuwa lider/admin |

**Historia zmian zamiast blokad:** każda zmiana formy/obsady zapisuje migawkę
(„Kasia zmieniła formę, wt 21:14”) z przyciskiem **Przywróć**.

---

## 4. Na próbie: „🎙 Nagraj pomysł”

Telefon → piosenka → aranżacja → klik w komórkę (rola × kafelek) → nagranie
(MediaRecorder w przeglądarce, Android + iPhone) → opcjonalnie jedno zdanie → zapis.
Cały zespół od razu to widzi i słyszy. **To rozwiązuje główny problem „zapominamy”.**

---

## 5. Reaper → Jonathan (skrypt Lua, nie VST)

### Konwencja nazw (jedyne, co trzeba wpisać)

| W Reaperze | Nazwa | Przykład |
|---|---|---|
| **Region** = piosenka | `Tytuł` albo `Tytuł \| Aranżacja` | `Oceany`, `Oceany \| Akustyczna` |
| **Markery** w regionie = kafelki | nazwy kafelków po kolei | `Intro`, `Z1`, `Refren`, `Z2`, `Refren`, `Bridge` |
| **Ślady** do wysłania = role | `J:` + nazwa roli z obsady | `J:Wokal 2`, `J:Gitara akustyczna`, `J:Piano` |

- Ślady bez `J:` (ambient, klik, FX) są ignorowane.
- Markery dopasowują się do kafelków **po kolei i po nazwie**, z aliasami
  (`R`=`Refren`=`Chorus`, `Z`=`Zwrotka`=`Verse`, `B`=`Bridge`…), bez wielkości liter.
- Region bez `| …` → aranżacja **Główna**.
- Kilka regionów w sesji = kilka piosenek wysłanych jednym kliknięciem.

### Przebieg

1. Akcja w Reaperze: **„Jonathan: wyślij próbę”**.
2. Skrypt pobiera z Jonathana listę piosenek/aranżacji/obsad (token studia).
3. Pokazuje podsumowanie do potwierdzenia:
   ```
   Oceany → Główna
     Kafelki: 7/7 ✓
     Ślady:  J:Gitara akustyczna ✓   J:Wokal 2 ✓   J:Perkusja ⚠ brak w obsadzie → [dodaj rolę]
   Oceany | Akustyczna → (nie istnieje) → [utwórz]
   Forma w Reaperze różni się od Jonathana → [ustaw formę wg nagrania] (domyślnie)
   [Wyślij]  [Anuluj]
   ```
4. Render (ustawienia renderu ustawiane przez skrypt, bez SWS) i wysyłka `curl`
   (wbudowany w Windows 10/11).

### Zasady

- **Nadpisywanie:** wysłanie zastępuje nagranie tej aranżacji. Bez archiwum wersji.
  Inna aranżacja = osobne nagranie.
- **Jeden komputer:** admin generuje w ustawieniach wspólnoty **token studia**
  (jeden aktywny; nowy unieważnia stary) i wkleja go w ustawienia skryptu.

---

## 6. Na telefonie: dwa pliki na muzyka

Skrypt renderuje na aranżację:
- **cały miks** (wspólny),
- dla każdej roli `J:`: **„miks + ja głośniej”** i **„miks beze mnie”**.

Muzyk dostaje tylko swoje dwa pliki i przełącza **Nauka ↔ Gram sam** (pozycja w utworze
zostaje). Do tego: pętla na kafelku (z markerów), „wolniej” bez zmiany wysokości dźwięku.

> Decyzja techniczna: gotowe zgrania zamiast miksowania dwóch śladów w telefonie —
> jeden odtwarzacz, zero rozjeżdżania się ścieżek, mało RAM, pewne działanie na iPhonie
> (zwolnienie tempa z zachowaniem wysokości działa natywnie w `<audio>`).
> Mono / MP3 ~128 kb/s → ok. 4 MB na plik.

---

## 7. Prywatność

- Pliki **poza** publicznym `static/` — każde pobranie sprawdza członkostwo we wspólnocie
  (jak dziś piosenki).
- Brak publicznych linków i udostępniania.
- Token studia przechowywany jako hash, z datą ostatniego użycia; do unieważnienia w każdej chwili.

---

## 8. Model danych (szkic)

```
Profile.instruments      JSON  ["Wokal", "Gitara akustyczna"]     (migracja z Profile.instrument)

Arrangement
  id, church_id, song_id, name ("Główna"), is_main
  form   JSON  [{tile_id, section_idx, label, repeat, dynamics}]
  roles  JSON  ["Wokal", "Wokal 2", "Gitara akustyczna"]
  updated_by, updated_at

ArrangementRevision      id, arrangement_id, snapshot JSON (form+roles), user_id, created_at
ArrangementCell          id, arrangement_id, tile_id, role, note, memo_path, updated_by, updated_at
ArrangementRecording     id, arrangement_id, kind (mix|loud|minus), role, path, duration,
                         markers JSON [{tile_id, start, end}], uploaded_at        (nadpisywane)
ProfileArrangementRole   profile_id, arrangement_id, role        (zapamiętany wybór roli)

Church.settings.studio_token_hash / studio_token_last_used
Setlist.items            [{song_id, transpose, arrangement_id?}]
```

`tile_id` jest stały (UUID kafelka) — przesunięcie kafelka nie gubi notatek w komórkach.

## 9. Endpointy (szkic)

```
GET  /c/<id>/songs/<song>/arrangements                 lista + edytor (strona)
POST /c/<id>/arrangements/<arr>/form | roles | cell     zapis (AJAX), zapis rewizji
POST /c/<id>/arrangements/<arr>/cell/<tile>/<role>/memo nagranie z telefonu
GET  /c/<id>/media/arr/<arr>/<plik>                     audio (sprawdza członkostwo)

# skrypt Reapera (nagłówek: Authorization: Bearer <token studia>)
GET  /api/studio/catalog                                piosenki, aranżacje, formy, role
POST /api/studio/arrangements/<arr>/recording           multipart: pliki + markery (+ forma)
```

---

## 10. Etapy

| # | Zakres | Szacunek | Uwagi |
|---|---|---|---|
| 1 | Instrumenty w profilu, aranżacje, forma (przeciąganie), obsada, komórki z notatkami, historia, widok w ćwiczeniu, wybór aranżacji w setliście, live wg formy | 3–4 dni | MVP |
| 2 | „🎙 Nagraj pomysł” w komórce + odtwarzanie | 1–2 dni | rozwiązuje „zapominamy” |
| 3 | Token studia + API + skrypt Lua do Reapera (dopasowanie, podsumowanie, render, wysyłka) | 2–3 dni | test na prawdziwej sesji z Winga |
| 4 | Odtwarzacz w ćwiczeniu: Nauka ↔ Gram sam, pętla kafelka, wolniej | 1–2 dni | |
| 5 | Synchronizacja aranżacji do aplikacji desktop (offline na scenie) | 1–2 dni | później |

## 11. Do sprawdzenia przy pisaniu

- Nagrywanie w Safari na iPhonie (format AAC/mp4) — test na prawdziwym urządzeniu.
- Czas renderu w Reaperze przy wielu rolach (2 zgrania × liczba ról × piosenki) —
  ewentualnie render tylko zmienionych regionów.
- Limit rozmiaru uploadu w Caddy/gunicorn dla wysyłki z Reapera.
- Ekrany zespołu w live: „następne: Bridge ×2, cicho” z formy — mało pracy, duży zysk.
