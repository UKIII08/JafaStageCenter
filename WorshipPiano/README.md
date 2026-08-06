# Jafa Worship Piano

Wtyczka **VST3** (+ wersja standalone) — pianino do grania uwielbienia z warstwą **soaking**:
padem i gęstym, płynącym pogłosem, które można nałożyć na fortepian jednym pokrętłem.

Napisana w C++/JUCE, bez bibliotek sampli — cały dźwięk jest generowany w czasie rzeczywistym.

---

## Dwa źródła dźwięku

Wtyczka ma dwa silniki fortepianu i przełącznik **Source** na górze panelu PIANO.

### 1. Sample Library — jeśli chcesz brzmienie klasy top

Syntezowany fortepian ma sufit, którego nie da się przeskoczyć strojeniem parametrów.
Uderzona struna to chaotyczne, nieliniowe zdarzenie i żadna synteza addytywna nie oszuka
ucha na ataku. Jedyny modelowany fortepian, który realnie konkuruje z samplerami, to
Pianoteq — dwadzieścia lat pracy zespołu akustyków.

Dlatego wtyczka potrafi **wczytać prawdziwą bibliotekę sampli**, a cały tor za nią —
pad, przestrzeń, shimmer, reverse, warstwa soaking — działa wtedy na prawdziwym fortepianie.

#### Salamander Grand Piano — krok po kroku

1. Pobierz `SalamanderGrandPianoV3+20161209_48khz24bit.tar` (Yamaha C5, 16 warstw dynamiki,
   licencja CC-BY). Na Windowsie do rozpakowania `.tar` przyda się 7-Zip.
2. Rozpakuj gdziekolwiek — powstanie folder z plikiem `.sfz` i podfolderem `48khz24bit`.
3. We wtyczce: `Sample library...` → **`Wczytaj folder z samplami...`** i wskaż rozpakowany
   folder. Plik SFZ zostanie znaleziony sam (szukanie jest rekurencyjne).
   Możesz też wybrać `Wczytaj plik .sfz...` i wskazać go bezpośrednio.

Wczytywanie zajmuje kilkadziesiąt sekund i zjada około **700–900 MB RAM**. Idzie w tle,
więc Reaper nie zamarza, a pasek pod przełącznikiem Source pokazuje postęp.

Inne sprawdzone darmowe biblioteki: **Piano in 162** (Ivy Audio, Steinway Model B).
Działa każda biblioteka SFZ.

Można też wskazać **folder z samymi plikami WAV** — wtedy wysokość dźwięku jest odczytywana
z nazw plików (`Piano_C4.wav`, `A#2.wav` albo numer MIDI 21–108), a pliki na tej samej nucie
są traktowane jako kolejne warstwy dynamiki.

Obsługiwane opcodes SFZ: dziedziczenie `<global>` / `<master>` / `<group>` / `<region>`,
strefy klawiszy i dynamiki, `pitch_keycenter`, `key`, `tune`, `transpose`, `volume`, pętle
(`loop_mode`, `loop_start`, `loop_end`, a także pętle zapisane w samym pliku WAV),
`ampeg_attack`, `ampeg_release`, `default_path`, oraz **`trigger=release` z `rt_decay`** —
czyli osobne sample tłumików, odtwarzane przy puszczeniu klawisza, tym ciszej im dłużej
klawisz był trzymany.

Sample są trzymane w pamięci jako znormalizowane 16-bitowe, nie jako float — duża biblioteka
fortepianowa to setki kilkunastosekundowych plików, które we float32 zajęłyby grubo ponad
gigabajt. Normalizacja każdego sampla do jego własnego szczytu sprawia, że podłoga 16 bitów
leży około 90 dB pod nim, czyli poniżej słyszalności. Ogony poniżej −90 dBFS są obcinane.

> Ładowanie idzie w tle, z paskiem postępu — Reaper nie zawiesza się na czas wczytywania.
> Ścieżka do biblioteki jest zapisywana w projekcie, więc po ponownym otwarciu wraca sama.

### 2. Modelled — silnik wbudowany

Synteza addytywna, około 5 MB, zero plików zewnętrznych. Nie dorówna dobrej bibliotece
sampli, ale gra od razu po instalacji i pozwala płynnie przechodzić między barwami, których
sampler nie ma (`Felt Piano` jest tu najlepszy). Przydaje się też jako zapasowe źródło,
kiedy nie chcesz taszczyć gigabajtów na próbę.

---

## Reverse piano

`Reverse` w panelu AMBIENCE odtwarza to, co właśnie zagrałeś, **od tyłu**. Każda fraza
narasta w siebie samą, bez przerwy i bez kliku na styku — zamiast jednego odwróconego
fragmentu chodzą dwa ziarna przesunięte o pół okna, ważone kosinusem, więc ich suma jest
stała.

Lista obok wybiera, jak daleko wstecz sięga każdy swell: **1/2 taktu do 4 taktów**,
zsynchronizowane z tempem projektu. Wyjście reverse idzie też mocniej w pogłos niż sygnał
suchy, żeby swell mieszkał w przestrzeni, a nie przed nią.

Preset **Reverse Swell** pokazuje ustawienie. Graj rzadko i zostaw miejsce.

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

## Warstwa soaking

To jest sedno wtyczki. Pod fortepianem siedzi osobna warstwa: pad grający te same nuty plus
pogłos, który **nie jest zwykłym reverbem na końcu łańcucha** — pad wchodzi w niego dużo
mocniej niż fortepian, dzięki czemu czyta się jako wash *za* instrumentem, a nie obok niego.

### SOAK — jedno pokrętło

`SOAK` to makro, nie tryb. Na zerze nie robi nic, a kręcone w prawo podnosi jednocześnie:
poziom padu, jego narastanie i rozstrojenie, głębokość i długość pogłosu, shimmer, chorus
i delay. Powyżej połowy przełącza też pogłos na większe maszyny (Bloom, potem Cloud).

Działa na **każdym** presecie — nawet na całkiem suchym „Sunday Grand" wykręcenie SOAK do
końca daje pełny wash.

> W Reaperze: prawy klik na pokrętle → *Parameter modulation / MIDI learn* i możesz sterować
> SOAK-iem z pedału ekspresji albo pokrętła na klawiaturze w trakcie grania.

### Maszyny pogłosu

| Maszyna | Charakter |
|---|---|
| **Room** | Krótko i ciasno. Do grania na żywo. |
| **Hall** | Duży, naturalny. Domyślny. |
| **Plate** | Gęsty i jasny, szybko się buduje. |
| **Cloud** | Ogromny, mocno modulowany, wszystko rozmywa. |
| **Bloom** | Ogon narasta wolno *za* tym, co zagrałeś. |
| **Shimmer** | Nastawiony na oktawę w pętli. |

`Shimmer` dodaje przesunięty dźwięk w pętli zwrotnej, a lista obok wybiera co dokładnie:
oktawa w górę, oktawa + kwinta, oktawa w dół, albo góra i dół naraz.

**FREEZE** zamraża ogon w nieskończoność — trzymasz akord, wciskasz, i grasz po zamrożonym
podkładzie. Przycisk jest automatyzowalny, więc w Reaperze można go podpiąć pod pedał.

`Duck` sprawia, że pogłos schodzi z drogi, kiedy grasz, i wraca w przerwach — to trik, dzięki
któremu można mieć jednocześnie ogromną przestrzeń i czytelne nuty.

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
| **Soaking Grand** | Soak | Fortepian z ambientowym łóżkiem narastającym za nim. **Zacznij tutaj.** |
| **Soaking Cloud** | Soak | Wszystko rozmyte w jedną wolno płynącą chmurę, oktawa i kwinta na górze. |
| **Prayer Room** | Soak | Filcowy fortepian nad powolnym bloomem, z duckingiem żeby nuty zostały czytelne. |
| **Infinite Wash** | Soak | Trzymasz akord, wciskasz FREEZE i grasz po wierzchu bez końca. |
| **Reverse Swell** | Soak | Każda fraza narasta w siebie od tyłu. Graj rzadko. |
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
| **Source** | `Modelled` — silnik wbudowany, `Sample Library` — wczytana biblioteka |
| **Sample library...** | Wczytanie pliku SFZ, folderu z WAV-ami, albo powrót do silnika modelowanego |
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

### AMBIENCE

Górny rząd: wybór maszyny, tryb shimmera, długość okna reverse i przycisk **FREEZE**.
Pokrętła: `Reverb` (ile), `Size`, `Decay` (do 30 s), `Shimmer`, `Reverse` i `Duck`.
Predelay skaluje się sam z rozmiarem pomieszczenia.

### SOAK & OUTPUT

Duże pokrętło **SOAK** (opisane wyżej) oraz `Width` i `Output`. Po prawej wskaźnik poziomu.

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

[`Source/dsp/SampleLibrary.cpp`](Source/dsp/SampleLibrary.cpp) — parser SFZ, ładowanie
folderów i odtwarzanie sampli (interpolacja Catmull-Roma, pętle, warstwy dynamiki, pedały).
Ładowanie idzie na wątku w tle; wątek audio widzi wyłącznie gotową bibliotekę, podmienianą
jednym wskaźnikiem, a poprzednie biblioteki są trzymane przy życiu poza nim, żeby nigdy nie
doszło do zwalniania pamięci w callbacku audio.

[`Source/dsp/PadLayer.cpp`](Source/dsp/PadLayer.cpp) — pad: piły polyBLEP rozstawione
w stereo, filtr SVF na kanał, otwierający się razem z narastaniem dźwięku.

[`Source/dsp/Ambience.cpp`](Source/dsp/Ambience.cpp) — warstwa przestrzeni. Trzy rzeczy
odróżniają pogłos, który płynie, od takiego, który tylko dokłada ogon:

* **gęstość** — cztery modulowane allpassy rozmazują każdy transjent w chmurę, *zanim*
  cokolwiek trafi do sprzężenia, a sam tank ma szesnaście linii zamiast ośmiu
* **ruch** — każda linia opóźniająca ma własne wolne LFO, więc ogon dryfuje zamiast stać
* **oktawa** — shimmer przesuwa wyjście tanku, dyfunduje je jeszcze raz, filtruje i wpina
  z powrotem, dzięki czemu oktawa *narasta* w ogonie, a nie siedzi na wierzchu

Saturator w pętli shimmera jest tym, co powstrzymuje oktawę w sprzężeniu przed ucieczką —
i przy okazji sprawia, że shimmer nie robi się szklisty.

[`Source/dsp/EffectChain.cpp`](Source/dsp/EffectChain.cpp) — EQ, kompresor równoległy,
nasycenie z nadpróbkowaniem, ensemble, delay, limiter bezpieczeństwa.

### Test DSP

W repo jest offline renderer, który przepuszcza progresję akordów przez **wszystkie** presety
i sprawdza, czy nie ma NaN-ów, rozbiegania sprzężeń ani ciszy:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DWORSHIPPIANO_BUILD_TOOLS=ON
cmake --build build --config Release
./build/WorshipPianoRender_artefacts/Release/WorshipPianoRender wyniki/
```

Sprawdza też trzy rzeczy osobno:

* **stres warstwy ambientowej** — maksymalny decay, podwójny shimmer i FREEZE naraz, czyli
  pętla o wzmocnieniu jeden z pitch-shifterem w środku; ogon musi się utrzymać, a nie uciec
* **działanie makra SOAK** — na całkiem suchym presecie wash po puszczeniu klawiszy musi
  realnie urosnąć
* **round-trip stanu** — żeby Reaper nie gubił ustawień przy ponownym otwarciu projektu
* **źródło samplowe od początku do końca** — wczytuje bibliotekę przez procesor tak, jak
  robi to host, przełącza źródło i sprawdza, czy na wyjściu faktycznie są sample, a nie
  silnik modelowany po cichu udający, że wszystko gra
* **loader sampli** — buduje na dysku bibliotekę SFZ ułożoną tak, jak układa się prawdziwa
  biblioteka fortepianowa (`<control> default_path`, obwiednia w `<global>`, grupy dynamiki,
  backslashe w ścieżkach, osobna grupa `trigger=release`), wczytuje ją z powrotem i sprawdza:
  rozdzielenie sampli grających od tłumików, dziedziczenie opcode'ów przez sekcje, `rt_decay`,
  `volume` per grupa, mapowanie klawiszy i dynamiki oraz stroj odtwarzania

Zapisuje też WAV-y do podanego katalogu, więc można odsłuchać każdy preset bez hosta.
Ten sam test chodzi w CI przy każdym buildzie.

---

## Licencja

Kod wtyczki: patrz licencja repozytorium.
JUCE jest pobierane jako zależność i objęte własną licencją (GPLv3 albo komercyjna) —
przy dystrybucji binarki obowiązują warunki JUCE.
