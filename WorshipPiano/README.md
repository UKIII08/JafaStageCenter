# Jafa Worship Piano

Wtyczka **VST3** (+ wersja standalone) — pianino do grania uwielbienia, z gotowymi presetami
w stylu nowoczesnych brzmień worshipowych i pełnym torem efektów.

Napisana w C++/JUCE, bez bibliotek sampli — cały dźwięk jest generowany w czasie rzeczywistym.

---

## Ważna uwaga na start — czego ta wtyczka nie jest

Prosiłeś o brzmienie „jak w Nordzie". Powiem wprost, żeby nie było rozczarowania:

* **Nord Stage / Piano** to kilka gigabajtów nagranych sampli prawdziwych fortepianów.
  Nie da się tego wygenerować kodem — trzeba by nagrać fortepian w studiu.
* Ta wtyczka buduje dźwięk **syntezą addytywną (modalną)**: każdy dźwięk jest składany
  partial po partialu z fizyki, która kształtuje brzmienie fortepianu. Około 5 MB zamiast
  30 GB i płynna kontrola nad barwą, ale to modeler, nie sampler klasy Nord.

**Natomiast** — i to jest sedno — brzmienie, które kojarzysz z nagrań worshipowych, w dużej
mierze nie bierze się z samego fortepianu, tylko z tego, co jest **za nim**: kompresji,
nasycenia, delaya ósemkowego z kropką, wielkiego pogłosu, shimmera i padu pod spodem.
To wszystko jest tutaj zrobione porządnie.

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
| **Sunday Grand** | Classic | Gładki fortepian koncertowy w ciepłym pomieszczeniu. Domyślny. |
| **Intimate Prayer** | Classic | Miękko, blisko, ciemno. Pod mówione słowo. |
| **Ballad Grand** | Classic | Pełny fortepian z odrobiną delaya. Zwrotki i wolne buildy. |
| **Upright Chapel** | Classic | Małe ciepłe pianino, bardziej sucho i „pudełkowo". |
| **Modern Worship Lead** | Modern | Jasny fortepian → delay 1/8 z kropką → szeroki plate. Klasyk gatunku. |
| **Arena Anthem** | Modern | Skompresowany, do przodu, ogromny. Wielki refren. |
| **Pad Underneath** | Modern | Fortepian z padem narastającym na tych samych nutach. |
| **Upper Room** | Ambient | Filcowe młoteczki, długi shimmer, pad. Cichy moment. |
| **Felt & Air** | Ambient | Filc i wolne kołysanie, prawie bez ataku. |
| **Ambient Bed** | Ambient | Trzymasz akord i on żyje sam. |
| **Stage Clean** | Live | Sucho i do przodu, do grania przez PA. |

*Presety są inspirowane stylem brzmienia współczesnej muzyki uwielbieniowej. Nie są
powiązane z żadnym konkretnym zespołem, kościołem ani marką i nie odtwarzają cudzych
nagrań — to po prostu ustawienia parametrów tej wtyczki.*

---

## Panele i parametry

Świadomie mało pokręteł — wszystko, co i tak miało tylko jedno sensowne ustawienie, jest
zaszyte w kodzie. Presety mają być do grania, a nie do kręcenia.

### PIANO

| Parametr | Co robi |
|---|---|
| **Model** | Smooth Grand / Bright Grand / Warm Upright / Felt Piano — zmienia nachylenie widma, twardość filcu, sztywność strun i długość wybrzmienia |
| **Tone** | Ciemno ↔ jasno. Przesuwa filtr filcu i nachylenie widma jednocześnie |
| **Attack** | Ile słychać uderzenia filcu o strunę i stuku mechaniki |
| **Sustain** | Mnożnik czasu wybrzmiewania (0.5× – 2×) |
| **Dynamics** | Zakres głośności między najcichszym a najgłośniejszym uderzeniem |
| **Level** | Głośność fortepianu przed torem efektów |

### PAD LAYER

Osobny syntezator grający te same nuty. `Pad` na minimum (−60 dB) wyłącza go całkowicie.
`Pad` · `Tone` · `Swell` (narastanie) · `Release`

### TONE & DRIVE

`Warmth` (półka 180 Hz) · `Presence` (półka 3.6 kHz) · `Air` (półka 14 kHz) ·
`Compress` · `Drive`

### MOVEMENT & DELAY

`Chorus` · `Delay` (mix) · `Feedback`, plus przełącznik **SYNC** i lista podziałów
(`1/4` … `1/16`). Pod spodem widać aktualne BPM hosta.

> Ustawienie na worship: **SYNC + 1/8.** (ósemka z kropką), feedback ~40%, mix ~30%.

### SPACE & OUTPUT

`Reverb` · `Size` · `Decay` · **`Shimmer`** (oktawa w górę wpięta w pętlę pogłosu) ·
`Width` · `Output`. Predelay skaluje się automatycznie z rozmiarem pomieszczenia.

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

[`Source/dsp/PianoEngine.cpp`](Source/dsp/PianoEngine.cpp) — silnik addytywny. Uderzona
struna to nie szarpnięta struna, więc nie ma tu żadnej pętli falowodu. Każdy dźwięk jest
składany z osobnych zanikających sinusoid, a o barwie decyduje fizyka:

* partial nr *k* leży na `k·f0·√(1 + B·k²)` — sztywność struny podnosi wyższe partiale,
  ale delikatnie (B rzędu 10⁻⁴), a nie metalicznie
* młoteczek uderza mniej więcej w 1/8 długości struny, więc partiale mające tam węzeł są
  osłabione — osłabione, nie wycięte
* filc działa jak filtr dolnoprzepustowy, który otwiera się im mocniej grasz; tu mieszka
  praktycznie cała dynamika fortepianu
* płyta rezonansowa słabo promieniuje najniższe częstotliwości, dlatego w basie barwa
  pochodzi z 2. i 3. partiala, a nie z fundamentu
* każdy partial ma własny czas zaniku i dwustopniową obwiednię: szybki początkowy spadek
  i długie dobrzmiewanie
* najniższe partiale są zdublowane i rozstrojone o **pół centa** — tak jak dwie lub trzy
  struny jednego chóru — co daje powolne migotanie

[`Source/dsp/PadLayer.cpp`](Source/dsp/PadLayer.cpp) — pad: piły polyBLEP + filtr SVF.
[`Source/dsp/EffectChain.cpp`](Source/dsp/EffectChain.cpp) — EQ, kompresor, nasycenie,
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
