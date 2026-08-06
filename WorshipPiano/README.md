# Jafa Worship Piano

Wtyczka **VST3** (+ wersja standalone) — pianino do grania uwielbienia, z gotowymi presetami
w stylu nowoczesnych brzmień worshipowych i pełnym torem efektów.

Napisana w C++/JUCE, bez bibliotek sampli — cały dźwięk jest generowany w czasie rzeczywistym.

---

## Ważna uwaga na start — czego ta wtyczka nie jest

Prosiłeś o brzmienie „jak w Nordzie". Powiem wprost, żeby nie było rozczarowania:

* **Nord Stage / Piano** to kilka gigabajtów nagranych sampli prawdziwych fortepianów.
  Nie da się tego wygenerować kodem — trzeba by nagrać fortepian w studiu.
* Ta wtyczka używa **modelowania fizycznego strun** (ta sama rodzina technik, co Pianoteq):
  każda struna to cyfrowy falowód z filtrem tłumienia i dyspersją. Efekt: około 5 MB zamiast
  30 GB, płynne sterowanie każdym parametrem, ale sam „surowy" fortepian brzmi bardziej jak
  dobry modeler niż jak sampler klasy Nord.

**Natomiast** — i to jest sedno — brzmienie, które kojarzysz z nagrań worshipowych, w 80%
nie bierze się z samego fortepianu, tylko z tego, co jest **za nim**: kompresja, nasycenie,
delay ósemkowy z kropką, wielki pogłos, shimmer, pad pod spodem. To wszystko jest tutaj
zrobione porządnie i to ono robi robotę.

Jeśli kiedyś zechcesz podmienić sam silnik na sample — tor efektów zostaje i możesz go
używać na dowolnym innym pianinie (patrz sekcja *Sam tor efektów*).

---

## Skąd wziąć plik `.vst3`

### Wariant 1: pobierz gotowy build (najprościej)

Po każdym pushu GitHub Actions buduje wtyczkę na Windows, macOS i Linux:

1. Wejdź w zakładkę **Actions** w tym repo
2. Kliknij ostatni przebieg **Build Worship Piano VST3**
3. Na dole strony, w sekcji **Artifacts**, pobierz `JafaWorshipPiano-Windows-x64`
4. Rozpakuj — w środku jest `Jafa Worship Piano.vst3`

### Wariant 2: zbuduj sam

```bash
cd WorshipPiano
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel
```

CMake sam pobierze JUCE 8.0.15 (potrzebny internet przy pierwszym uruchomieniu).
Gotowa wtyczka ląduje w `build/JafaWorshipPiano_artefacts/Release/VST3/`.

Na Linuksie potrzebne są jeszcze pakiety deweloperskie:

```bash
sudo apt install libasound2-dev libjack-jackd2-dev libx11-dev libxext-dev \
  libxinerama-dev libxrandr-dev libxcursor-dev libxcomposite-dev \
  libfreetype6-dev libfontconfig1-dev libgl1-mesa-dev
```

---

## Instalacja w Reaperze

**Windows** — skopiuj `Jafa Worship Piano.vst3` do:

```
C:\Program Files\Common Files\VST3\
```

**macOS** — do `/Library/Audio/Plug-Ins/VST3/` (lub `~/Library/Audio/Plug-Ins/VST3/`)

**Linux** — do `~/.vst3/`

Potem w Reaperze: `Options → Preferences → Plug-ins → VST → Re-scan`.

Wtyczka pojawi się jako **VSTi: Jafa Worship Piano (Jafa Stage)** — wstaw ją na ścieżkę MIDI
(przycisk `FX` → zakładka *Instruments*), uzbrój ścieżkę i graj.

> Delay synchronizuje się z tempem projektu Reapera automatycznie — zmiana BPM zmienia
> czas powtórek.

---

## Presety

15 presetów fabrycznych, pogrupowanych w cztery kategorie. Strzałki `<` `>` na górnym pasku
przeskakują po kolei, kliknięcie nazwy otwiera pełne menu. Presety są też widoczne jako
programy hosta, więc możesz je przełączać z Reapera.

| Preset | Kategoria | Do czego |
|---|---|---|
| **Sunday Morning** | Classic | Czysty fortepian koncertowy, ciepłe pomieszczenie. Bezpieczny domyślny. |
| **Ballad Grand** | Classic | Pełny fortepian z lekkim delayem. Zwrotki i wolne buildy. |
| **Intimate Prayer** | Classic | Miękki, blisko, sucho. Pod mówione słowo. |
| **Upright Chapel** | Classic | Mały ciepły pianino z charakterem mechaniki. |
| **Arena Anthem** | Modern | Jasny, skompresowany, ogromny — brzmienie wielkiego refrenu. |
| **Modern Worship Lead** | Modern | Jasne stage piano → delay 1/8 z kropką → szeroki plate. Klasyk gatunku. |
| **Pad Underneath** | Modern | Fortepian z padem narastającym na tych samych nutach. |
| **Upper Room** | Ambient | Filcowe młoteczki, długi shimmer, pad. Na cichy moment. |
| **Shimmer Cloud** | Ambient | Oktawa w górę w ogonie pogłosu, wszystko kwitnie po puszczeniu klawiszy. |
| **Felt & Tape** | Ambient | Filc, nasycenie taśmowe, wolne kołysanie. |
| **Cinematic Swell** | Ambient | Ciemno, wolno, ogromnie. Podkład pod modlitwę. |
| **Ambient Bed** | Ambient | Ledwo już fortepian. Trzymasz akord i on żyje sam. |
| **Stage Clean** | Live | Sucho i do przodu, do grania na żywo przez PA. |
| **Gospel Bright** | Live | Twarde młoteczki, mocna kompresja. Przebija się przez pełny band. |
| **Bright Pop Piano** | Live | Ciasny, szklisty, bardzo obecny. Szybkie kawałki. |

*Presety są inspirowane stylem brzmienia współczesnej muzyki uwielbieniowej. Nie są
powiązane z żadnym konkretnym zespołem, kościołem ani marką i nie odtwarzają cudzych
nagrań — to po prostu ustawienia parametrów tej wtyczki.*

---

## Panele i parametry

### PIANO — silnik strunowy

| Parametr | Co robi |
|---|---|
| **Model** | Concert Grand / Warm Upright / Felt Piano / Stage Bright — zmienia twardość młoteczka, tłumienie i długość wybrzmienia |
| **Brightness** | Tłumienie górnych partiali w pętli struny. W lewo ciemniej, w prawo otwarciej |
| **Hammer** | Twardość młoteczka. Miękki = ciemny i wolniejszy atak, twardy = jasny klik |
| **Decay** | Mnożnik czasu wybrzmiewania (0.4× – 2×) |
| **Unison** | Rozstrojenie 2–3 strun jednej nuty w centach. To stąd bierze się naturalne „migotanie" i podwójne wybrzmienie |
| **Stretch** | Nieharmoniczność — o ile wyższe partiale są podwyższone. Prawdziwy fortepian ma jej najwięcej na skrajach klawiatury |
| **Resonance** | Rezonans współczujący: 24 nietłumione struny, które grają, gdy trzymasz pedał |
| **Mechanics** | Szum mechaniki — klik młoteczka i szmer tłumików przy puszczaniu klawisza |
| **Vel Curve** | Krzywa dynamiki. W lewo trzeba grać mocniej, w prawo łatwiej o głośny dźwięk |
| **Dynamics** | Zakres głośności między najcichszym a najgłośniejszym uderzeniem (dB) |
| **Spread** | Rozstawienie stereo według pozycji na klawiaturze |
| **Level** | Głośność samego fortepianu przed torem efektów |

### PAD LAYER — pad pod spodem

Osobny syntezator grający te same nuty co fortepian — trzy rozstrojone piły przez filtr
dolnoprzepustowy z wolnym atakiem. `Pad` na minimum (−60 dB) całkowicie go wyłącza.

`Pad` · `Tone` (odcięcie filtra) · `Detune` · `Attack` · `Release`

### TONE & DRIVE

`Low` (półka 180 Hz) · `Mid` (dzwon 900 Hz) · `High` (półka 3.6 kHz) · `Air` (półka 14 kHz) ·
`Compress` (próg i ratio jednym pokrętłem) · `Comp Mix` (kompresja równoległa) ·
`Drive` (nasycenie z 2× nadpróbkowaniem) · `Drive Tone`

### MOVEMENT & DELAY

`Chorus` · `Rate` · `Delay` (mix) · `Feedback` · `Delay Tone` · `Ping Pong` · `Free Time`

Przełącznik **SYNC** decyduje, czy delay chodzi w tempie projektu (wtedy działa lista
podziałów: `1/4`, `1/4T`, `1/8.`, `1/8`, `1/8T`, `1/16.`, `1/16`), czy w milisekundach
(`Free Time`). Pod spodem wyświetla się aktualne BPM hosta.

> Ustawienie na worship: **SYNC + 1/8.** (ósemka z kropką), feedback ~40%, mix ~30%.

### SPACE & OUTPUT

Pogłos to sieć ośmiu sprzężonych linii opóźniających (FDN) z modulacją i tłumieniem.

`Reverb` (mix) · `Size` · `Decay` (0.4–15 s) · `Tone` · `Predelay` ·
**`Shimmer`** (oktawa w górę wpięta w pętlę pogłosu — charakterystyczny narastający „anielski"
ogon) · `Width` · `Output`

Po prawej jest wskaźnik poziomu wyjścia.

---

## Sterowanie MIDI

| CC | Funkcja |
|---|---|
| **CC64** | Pedał sustain — obsługuje też **półpedał** (wartości pośrednie skracają tłumienie proporcjonalnie) |
| **CC66** | Sostenuto |
| **CC67** | Pedał piano (una corda) — ścisza i przyciemnia |
| CC120 / CC123 | All sound off / all notes off |

Polifonia: 32 głosy fortepianu + 16 głosów padu, z kradzieżą najcichszego głosu.

---

## Sam tor efektów

Jeśli chcesz użyć tylko efektów na innym pianinie (samplowanym, sprzętowym, czymkolwiek):
ustaw `Level` w panelu PIANO na minimum i `Pad` na −60 dB — wtyczka nadal jest instrumentem,
więc najprościej jest po prostu odtworzyć te same ustawienia efektów w ReaEQ / ReaComp /
ReaDelay / ReaVerbate na ścieżce z Twoim pianinem. Wartości znajdziesz w
[`Source/Presets.cpp`](Source/Presets.cpp).

---

## Jak to działa w środku

* [`Source/dsp/PianoEngine.cpp`](Source/dsp/PianoEngine.cpp) — struny jako falowody cyfrowe.
  Pobudzenie to krótki impuls szumu zależny od dynamiki, przepuszczony przez grzebień
  odpowiadający miejscu uderzenia młoteczka (~1/8 długości struny), przez co brakuje tych
  samych partiali co w prawdziwym instrumencie. Do tego rezonans pudła i bank strun
  współczujących.
* [`Source/dsp/PadLayer.cpp`](Source/dsp/PadLayer.cpp) — pad: piły polyBLEP + filtr SVF.
* [`Source/dsp/EffectChain.cpp`](Source/dsp/EffectChain.cpp) — EQ, kompresor, nasycenie,
  ensemble, delay, pogłos FDN z shimmerem, limiter bezpieczeństwa.

### Test DSP

W repo jest offline renderer, który przepuszcza progresję akordów przez **wszystkie** presety
i sprawdza, czy nie ma NaN-ów, rozbiegania sprzężeń ani ciszy:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DWORSHIPPIANO_BUILD_TOOLS=ON
cmake --build build --config Release
./build/WorshipPianoRender_artefacts/Release/WorshipPianoRender wyniki/
```

Zapisuje też WAV-y do podanego katalogu, więc można odsłuchać każdy preset bez hosta.
Ten sam test chodzi w CI przy każdym buildzie.

---

## Licencja

Kod wtyczki: patrz licencja repozytorium.
JUCE jest pobierane jako zależność i objęte własną licencją (GPLv3 albo komercyjna) —
przy dystrybucji binarki obowiązują warunki JUCE.
