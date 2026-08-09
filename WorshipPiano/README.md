# Jafa Worship Piano

Wtyczka **VST3** (+ wersja standalone) — pianino do grania uwielbienia z warstwą **soaking**:
padem i gęstym, płynącym pogłosem, które można nałożyć na fortepian jednym pokrętłem.

Napisana w C++/JUCE. Gra z **własnej biblioteki sampli** — wskazujesz ją raz i wtyczka
pamięta ścieżkę.

---

## Biblioteka sampli — wymagana

Wtyczka **nie ma wbudowanego generatora dźwięku**. Gra wyłącznie z prawdziwych sampli
fortepianowych, które wskazujesz sam. Dopóki nie wczytasz biblioteki, na górze widnieje
czerwony pasek i nic nie zabrzmi — to nie usterka, tylko konstrukcja.

Wcześniej obok samplera był silnik modelowany (synteza addytywna). Został usunięty: brzmiał
gorzej od byle jakiej biblioteki, a przy tym kosztował blisko **trzy razy więcej procesora**
niż odtwarzanie sampli.

### Salamander Grand Piano — krok po kroku

1. Pobierz `SalamanderGrandPianoV3+20161209_48khz24bit.tar` (Yamaha C5, 16 warstw dynamiki,
   licencja CC-BY). Na Windowsie do rozpakowania `.tar` przyda się 7-Zip.
2. Rozpakuj gdziekolwiek — powstanie folder z plikiem `.sfz` i podfolderem `48khz24bit`.
3. We wtyczce: **`Sample library...`** na górnej belce → **`Wczytaj folder z samplami...`**
   i wskaż rozpakowany folder. Plik SFZ zostanie znaleziony sam (szukanie jest rekurencyjne).

Wczytywanie zajmuje kilkadziesiąt sekund i zjada około **700–900 MB RAM**. Idzie w tle,
więc Reaper nie zamarza, a pasek obok przycisku pokazuje postęp. Ścieżka jest zapisywana
w projekcie, więc po ponownym otwarciu biblioteka wraca sama.

Inne sprawdzone darmowe biblioteki: **Piano in 162** (Ivy Audio, Steinway Model B).
Działa każda biblioteka SFZ. Można też wskazać **folder z samymi plikami WAV** — wtedy
wysokość dźwięku jest odczytywana z nazw plików (`Piano_C4.wav`, `A#2.wav` albo numer MIDI
21–108), a pliki na tej samej nucie są traktowane jako kolejne warstwy dynamiki.

### Automatyczne wyrównanie poziomu

Biblioteki są masterowane do bardzo różnych poziomów — Salamander siedzi tuż pod pełną skalą,
inne dziesięć decybeli niżej. Cały tor za samplerem (nasycenie, kompresor, limiter) działa
poprawnie tylko wtedy, gdy sygnał przychodzi w spodziewanym zakresie. Dlatego przy wczytaniu
mierzona jest najgłośniejsza warstwa dynamiki ze środka klawiatury i skalowana do stałego
celu. Nie trzeba nic ustawiać, a żadna biblioteka nie wpadnie w limiter.

### Obsługiwane opcodes SFZ

Dziedziczenie `<global>` / `<master>` / `<group>` / `<region>`, strefy klawiszy i dynamiki,
`pitch_keycenter`, `key`, `tune`, `transpose`, `volume`, pętle (`loop_mode`, `loop_start`,
`loop_end`, a także pętle zapisane w samym pliku WAV), `ampeg_attack`, `ampeg_release`,
`default_path`, oraz **`trigger=release` z `rt_decay`** — czyli osobne sample tłumików,
odtwarzane przy puszczeniu klawisza, tym ciszej im dłużej klawisz był trzymany.

Sample są trzymane w pamięci jako znormalizowane 16-bitowe, nie jako float — duża biblioteka
fortepianowa to setki kilkunastosekundowych plików, które we float32 zajęłyby grubo ponad
gigabajt. Ogony poniżej −90 dBFS są obcinane.

---

## Presety

Szesnaście presetów fabrycznych w pięciu kategoriach plus **własne**, zapisywane na dysk.

W widoku **LIVE**, pod listą presetów, są dwa przyciski:

- **ZAPISZ** — pyta o nazwę i zapisuje wszystkie gałki do pliku. Jeśli grasz już na własnym
  presecie, nazwa podpowiada się sama, więc nadpisanie to jedno kliknięcie.
- **USUN** — kasuje własny preset (fabrycznych nie ruszy).

### Własny preset pamięta bibliotekę sampli

Okienko zapisu ma listę **`Sample:`** z dwoma wyborami:

| Wybór | Co robi |
|---|---|
| **Zapamietaj biblioteke sampli** | Preset zapisuje ścieżkę do biblioteki, na której powstał. Wczytanie presetu przełącza sample |
| **Bez biblioteki** | Preset rusza tylko gałki i zostawia wczytane sample w spokoju |

Dzięki temu jeden set może mieć **różne pianina pod różnymi pieśniami** — filcowe pod
modlitwę, jasny koncertowy pod ostatni refren — bez szukania folderu między numerami.
Presety fabryczne nigdy nie ruszają biblioteki: nie mogą znać ścieżek na Twoim dysku.

Każda raz wczytana biblioteka **zostaje w pamięci do końca sesji**. Powrót do niej to
podmiana wskaźnika, a nie ponowne czytanie z dysku — pierwsze przełączenie na nową
bibliotekę kosztuje te kilkadziesiąt sekund, każde kolejne jest natychmiastowe. Powyżej
**2 GB** w puli najdawniej używana biblioteka jest zwalniana (nigdy ta, która właśnie gra).
Trzymanie dwóch dużych bibliotek naraz to około 1,5–2 GB RAM — warto o tym wiedzieć,
zanim wpiszesz trzecią do setu.

Własne presety pojawiają się na dole listy z etykietą **MOJE**. Leżą jako osobne pliki
`.wppreset` w:

```
Windows:  %APPDATA%\Jafa Stage\Worship Piano\Presets
macOS:    ~/Library/Application Support/Jafa Stage/Worship Piano/Presets
Linux:    ~/.config/Jafa Stage/Worship Piano/Presets
```

Dzięki temu przeżywają przeinstalowanie wtyczki i można je skopiować na inny komputer —
brzmienia na niedzielę nie powinny siedzieć wyłącznie w pliku projektu jednego hosta.

---

## Połączenie z Jafa Stage Center

Aplikacja wie, która piosenka jest na ekranie, w jakim jest tempie i tonacji.
Pianino nie wie, a na scenie nie ma wolnej ręki, żeby mu powiedzieć. Po włączeniu
mostu **tempo i brzmienie idą za piosenką same**.

### Jak to działa

Wymiana idzie przez pliki w folderze, w którym wtyczka i tak trzyma presety:

| Plik | Kto pisze | Co zawiera |
|---|---|---|
| `live.json` | aplikacja | co jest grane: `song_id`, tytuł, tonacja, BPM, przypisany preset |
| `plugin.json` | wtyczka | jakie presety istnieją i co jest wczytane |

Plik, a nie gniazdo sieciowe — świadomie. Obie strony chodzą na tym samym
komputerze, więc plik nie potrzebuje portu, nie wywoła pytania zapory w środku
nabożeństwa i nie wymaga sieci we wtyczce audio. Przeżywa też restart
którejkolwiek strony: aplikację można zamknąć i otworzyć w środku setu, a pianino
po prostu czyta dalej.

Wtyczka sprawdza plik pięć razy na sekundę — koszt niemierzalny obok dźwięku.
Robi to **procesor, nie okno**, więc śledzenie działa też przy zamkniętym oknie
wtyczki, co na scenie jest normą.

### Co idzie za piosenką

- **Tempo** — trafia w podziały delaya. Istotne w wersji standalone, która nie ma
  transportu hosta i do tej pory tkwiła na 120 BPM niezależnie od tego, co grał
  zespół. W DAW-ie transport hosta pozostaje nadrzędny.
- **Brzmienie** — preset przypisany do piosenki. Jeśli preset niesie własną
  bibliotekę sampli, przełączenie jest natychmiastowe, bo raz wczytane biblioteki
  zostają w pamięci.
- **Tonacja** — **tylko pokazywana** w belce, nigdy ustawiana. Akordy, z których
  gra pianista, są już przeniesione przez aplikację; ustawienie transpozycji
  jeszcze raz we wtyczce przesunęłoby dźwięk drugi raz.

Piosenka bez przypisanego brzmienia **nie zmienia niczego** — pianino zostaje na
tym, co ma. Ciche zresetowanie do presetu fabrycznego w środku setu byłoby gorsze
niż nierobienie nic.

### Czego most nie robi

Aplikacja przepisuje `live.json` przy **każdym slajdzie** i przy blackoucie, nie
tylko przy zmianie piosenki. Wtyczka reaguje wyłącznie na `song_id`, preset i
tempo — tytuł i tonacja jadą do wyświetlenia i nie wyzwalają niczego. Dzięki temu
gałka, którą pianista poprawił między zwrotkami, nie wraca do pozycji z presetu,
bo tekst przewinął się o slajd.

### Jak włączyć

1. W panelu sterowania otwórz piosenkę do edycji — wiersz **Brzmienie pianina**
   jest tam zawsze.
2. Lista presetów pojawia się dopiero, gdy pianino **raz chodziło na tym
   komputerze**: to ono zapisuje `plugin.json`. Zanim to nastąpi, wiersz mówi o
   tym wprost. Kliknij **Otwórz pianino** obok — lista dociągnie się sama, bez
   zamykania okna.
3. Przycisk szuka wersji standalone obok aplikacji, w `Program Files` i w
   folderze builda; własną ścieżkę można wskazać zmienną `JAFA_PIANO_PATH`.

Gdy listy nie widać mimo uruchomionego pianina, sprawdź, czy w
`%APPDATA%\Jafa Stage\Worship Piano\` leży `plugin.json`. Jeśli go nie ma,
pianino jest ze starszego builda, sprzed połączenia z aplikacją.

Przypisania siedzą w lokalnej tabeli `SongPatch`, a nie w samej piosence —
piosenki są nadpisywane przy synchronizacji z chmurą, a brzmienie zależy od tego,
jakie sample ma **ten** komputer. Edycja piosenki na maszynie bez pianina nie
kasuje przypisań zrobionych na maszynie, która je ma.

---

## Pedalboard

Osiem przełączników na dole widoku **LIVE**, ułożonych w kolejności toru sygnału:

```
TACK   DRIVE   PAD   CHORUS   DELAY   REVERSE   REVERB   SOAK
```

Każdy działa jak kostka gitarowa: gałka obok ustawia **ile** efekt robi, a przełącznik
decyduje **czy w ogóle**. Klikasz na zwrotkę REVERSE i SOAK, na refren zdejmujesz je i
dodajesz CHORUS — bez ruszania gałek i bez zmiany presetu.

Załączanie i wyłączanie jest **wygaszane rampą 45 ms**, nie przełączane skokiem. Twarde
cięcie brzmiącego fortepianu to klik, a nie efekt. Pad ma własną, dłuższą rampę (55 ms),
bo jest dźwiękiem ciągłym — urwanie pada słychać znacznie bardziej niż urwanie zanikającej
nuty. Delay i pogłos przy wyłączeniu **dograją swój ogon do końca** zamiast zniknąć w pół
powtórki.

### Sterowanie nogą

Każdy przełącznik siedzi na kontrolerze MIDI z zakresu **CC 80–87**:

| CC | Stomp | CC | Stomp |
|---|---|---|---|
| 80 | PAD | 84 | REVERB |
| 81 | CHORUS | 85 | SOAK |
| 82 | DELAY | 86 | DRIVE |
| 83 | REVERSE | 87 | TACK |

To są kontrolery „general purpose" ze specyfikacji MIDI, więc nie kolidują z niczym, co
klawiatura wysyła sama. Działa zarówno przełącznik chwilowy, jak i zatrzaskowy — liczy się
tylko, czy wartość jest powyżej połowy.

### TACK

Pinezki wbite w filc młoteczków. Metal dotyka struny pierwszy, więc jasność mieszka
**wyłącznie w ataku** — zwykła półka górnoprzepustowa zrobiłaby z całego instrumentu
piszczałkę. Stopień wykrywa transjent (szybka obwiednia ponad wolną) i podbija górę tylko
na czas uderzenia. Gałka **Tack** w widoku EDIT ustawia siłę.

Domyślnie wyłączony. Dwa presety mają go włączonego od razu, delikatnie — *Modern Worship
Lead* (22 %) i *Arena Anthem* (30 %) — bo obydwa mają się przebić przez zespół.

---

## Szybki dostęp

Nikt nie przewija listy dwudziestu presetów między dwiema pieśniami. Przycisk **`*`** obok
ZAPISZ/USUN dodaje bieżący preset do sześciu slotów szybkiego dostępu — pasek nad panelami,
jedno kliknięcie. Wybór jest zapisywany na dysku (`favourites.txt` obok presetów), więc
idzie za komputerem, a nie za projektem. Preset, który przestał istnieć, zwalnia slot sam.

### Chowanie listy presetów

Przycisk **`PRESETY`** na końcu paska szybkiego dostępu zwija **całą lewą sekcję z listą**.
Zostaje sam pasek sześciu slotów, a zwolniona jedna trzecia szerokości idzie do pokręteł
i pedalboardu — na scenie lista jest głównie czymś, co można trącić łokciem.

Razem z listą znikają **ZAPISZ**, **USUN** i **`*`** — to rzeczy, które robi się przy
budowaniu setu, a nie w trakcie grania. Wracają jednym kliknięciem tego samego przycisku.

Ustawienie leży na dysku (`view.txt` obok presetów), więc opisuje **komputer na scenie**,
a nie pojedynczy projekt — raz zwinięta lista zostaje zwinięta w każdym następnym projekcie.

---

## Pady

Pięć charakterów, wybierane listą w panelu PAD:

| Typ | Brzmienie |
|---|---|
| **Warm Saw** | Klasyczne analogowe łóżko, trzy rozstrojone piły. Domyślny |
| **Soft Choir** | Trójkąt bez góry — oddycha zamiast brzęczeć. Pod mówione słowo |
| **Glass** | Jasny, dzwonkowy, siada **nad** fortepianem zamiast z nim walczyć |
| **Strings** | Szersze rozstrojenie i wolniejszy swell. Sekcja, nie syntezator |
| **Air Vox** | Wąski impuls, oddechowy, wokalny |

Każdy typ zmienia nie tylko falę, ale i filtr, rozstrojenie oraz czasy narastania —
sekcja smyczkowa to nie piła z inną falą, tylko wolniejsza i szersza.

Presety fabryczne z padem korzystają z różnych typów, żeby nie brzmiały tak samo pod
spodem: **Glass** w *Modern Worship Lead*, **Warm Saw** w *Pad Underneath*, **Soft Choir**
w *Upper Room*, *Soaking Grand* i *Prayer Room*, **Strings** w *Ambient Bed* i *Infinite
Wash*, **Air Vox** w *Soaking Cloud* i *Reverse Swell*.

---

## Jakość dźwięku — co jest mierzone

Trzy rzeczy, które odróżniają pad brzmiący drogo od brzmiącego tanio, i które da
się zmierzyć zamiast dyskutować.

### Aliasing oscylatorów

Piła band-limited (polyBLEP) nie ma energii powyżej Nyquista. Ale **mnożenie
sygnału przez siebie podwaja pasmo**, a przepuszczenie go przez `abs()` to
załamanie, które nie ma limitu pasma w ogóle. Nadmiar składowych odbija się od
góry widma i ląduje **pomiędzy** harmonicznymi, na częstotliwościach niezwiązanych
z graną nutą. Słychać to jako szorstkość i ziarno, nie jako jasność.

Mierzone na C6, z filtrem otwartym, jako stosunek energii między harmonicznymi do
energii na harmonicznych:

| Charakter | Przedtem | Teraz |
|---|---|---|
| Warm Saw | −34,4 dB | **−55,4 dB** |
| Soft Choir | −18,4 dB | **−72,5 dB** |
| Glass | −26,6 dB | **−43,4 dB** |
| Strings | −34,9 dB | **−50,9 dB** |
| Air Vox | −15,9 dB | **−53,4 dB** |

Naprawione dwiema rzeczami. Po pierwsze oscylatory chodzą na **podwójnej
częstotliwości** i wracają przez 31-punktowy filtr półpasmowy. Po drugie — i to
dało większość poprawy — każdy kształt jest teraz budowany **wyłącznie z pił
band-limited**: prostokąt to dwie piły odległe o pół okresu, impuls to dwie piły
odległe o ułamek okresu, trójkąt to całka z prostokąta. Wcześniej trójkąt
powstawał przez `abs()`, a impuls przez mnożenie — obie metody niszczyły to, co
polyBLEP właśnie zbudował.

Kosztuje to około 4 punkty procentowe czasu procesora (z ~7,6 % do ~11,6 % czasu
rzeczywistego), co przy zapasie, jaki jest, nie ma znaczenia.

### Gęstość — supersaw zamiast trzech pił

Trzy rozstrojone piły dają jedno dudnienie. Siedem, rozstawionych **nierówno**,
wypełnia przestrzeń wokół każdej harmonicznej — i to wypełnienie słychać jako
gęstość, a nie jako chorus.

Offsety i krzywe głośności pochodzą z pracy Adama Szabo *„How to Emulate the
Super Saw"* (2010), która jest odwrotną inżynierią oscylatora Rolanda JP-8000 i
punktem odniesienia dla większości programowych supersawów:

- siedem oscylatorów o offsetach `−0.11002313 … 0 … +0.10745242`, **celowo
  nierównych** — równy rozstaw zlewa się w jedną słyszalną częstotliwość dudnienia
- głośność środka `−0.55366·x + 0.99785`
- głośność boków `−0.73764·x² + 1.2841·x + 0.044372`

Środek cichnie, a boki rosną wraz z rozstrojeniem — to jest ta zależność, która
przy szerokim ustawieniu nie zamienia pada w papkę bez nuty w środku.

Zakres jest nasz: oryginał przy pełnym rozstrojeniu rozjeżdża się o blisko dwa
półtony, co jest leadem trance'owym, a nie łóżkiem pod zborem. Ustawienie w
centach mapuje się na dolną część tej skali.

Liczone jako rozróżnialne prążki widma w paśmie 80 Hz – 4 kHz, ponad −40 dB:

| Charakter | 3 oscylatory | 7 oscylatorów |
|---|---|---|
| Warm Saw | 44 | **99** |
| Glass | 43 | **100** |
| Strings | 44 | **99** |
| Air Vox | 44 | **99** |
| Soft Choir | 29 | **33** |

Soft Choir rośnie najmniej i tak ma być — trójkąt ma z natury mało harmonicznych,
na tym polega jego charakter.

Koszt: z ~11,6 % do ~14,4 % czasu rzeczywistego.

### Zgodność mono

Sporo sal ma nagłośnienie mono, a pad zbudowany przez rozrzucenie rozstrojonych
kopii w panoramie to dokładnie ten materiał, który przy sumowaniu potrafi się
częściowo wykasować. Pad, który znika po złożeniu do mono, nie jest szeroki,
tylko zepsuty.

Mierzone jako poziom sumy `(L+R)/2` względem średniej z obu stron: **−0,3 dB**
dla każdego charakteru, czyli praktycznie nic. Panorama bierze się z tego, że
każdy oscylator ma **inną częstotliwość**, a nie ze sztuczek fazowych, które
rozpadają się dalej w torze.

### Ruch ogona pogłosu

Zbiornik ze sztywnymi długościami linii opóźniających ma sztywne rezonanse.
Energia zbiera się na nich i po długim wybrzmieniu zostaje nie pomieszczenie,
tylko kilka dzwoniących wysokości — to jest to, co ludzie nazywają brzmieniem
„metalicznym" albo „pudełkowym".

Modulacja tu **była** od początku, ale w dwóch rzeczach kulała:

- pole `modRate` siedziało w tabeli maszyn i **nigdzie nie było użyte** — `lfoInc`
  liczyło się ze sztywnego wzoru, więc każda maszyna modulowała tak samo szybko
  mimo zapisanej własnej szybkości
- przebieg był czystą sinusoidą, czyli ruchem okresowym, na który ucho potrafi
  się zestroić; szesnaście linii chodziło w takt

Teraz każda linia wędruje **wygładzanym losowym przebiegiem** — kolejne losowe
cele, sklejane podniesionym cosinusem, więc ciągła jest zarówno wartość, jak i
prędkość zmian i nigdzie nie powstaje załamanie wysokości. Szybkość bierze się z
maszyny, a każda linia dostaje własny mnożnik, żeby szesnaście linii nigdy nie
wróciło do wspólnego rytmu.

Mierzone jako **zmienność poziomu prążka między kolejnymi ramkami widma ogona**,
kilka sekund po ucichnięciu nut. Uwaga: **niżej znaczy gładziej**, co jest
odwrotnie, niż podpowiada intuicja — stojący zbiornik ma ostre, izolowane
rezonanse, a prążki wokół ostrego piku skaczą między ramkami; rozmyty ogon ma
każdy prążek spokojniejszy.

| Stan | Ruch prążka |
|---|---|
| modulacja wyłączona | ~8,2 dB |
| sinus (poprzednio) | ~6,2 dB |
| losowa (teraz) | ~6,0 dB |

Uczciwie: **większość efektu była już wcześniej**. Sama zamiana sinusa na losowy
przebieg daje niewiele, a zwiększanie głębokości nie daje nic — powyżej dwukrotnej
wskaźnik stoi, a dla maszyny Plate wręcz się pogarsza. Realną wartością tej zmiany
jest ożywienie `modRate` i zdjęcie okresowości, a nie skok jakości.

### Kradzież głosów w padzie

Pad idzie za każdą nutą pianina, a gra się z wciśniętym pedałem — więc głosy
piętrzą się i po dwóch akordach każda nowa nuta musi któryś zabrać. Zabranie
**grającego** głosu przez podmianę wysokości w locie słychać jako „strzał":
brzmiąca nuta skacze na inną częstotliwość, przy pełnej głośności, w środku
okresu, ciągnąc za sobą stan filtra.

Teraz głosów jest **32 zamiast 16**, a gdy któryś naprawdę trzeba zabrać, jest
najpierw **wygaszany przez 6 ms**, a nowa nuta startuje od ciszy dopiero za nim.
Pod padem, który narasta przez 700 ms, tego opóźnienia nie da się usłyszeć.

To jest wada niewidoczna dla testu przebiegu — skok wysokości jest idealnie
ciągły próbka po próbce, nic się nie „schodkuje". Dlatego pad liczy takie
przypadki sam, a test sprawdza, że licznik stoi na zerze przy 60 nutach na
pedale (i że kradzież w ogóle zaszła, inaczej test nie dowodziłby niczego).

---

## Reverse piano

`Reverse` w panelu AMBIENCE odtwarza to, co właśnie zagrałeś, **od tyłu**. Każda fraza
narasta w siebie samą, bez przerwy i bez kliku na styku — zamiast jednego odwróconego
fragmentu chodzą dwa ziarna przesunięte o pół okna, ważone kosinusem, więc ich suma jest
stała.

Lista obok wybiera, jak daleko wstecz sięga każdy swell: **1/2 taktu do 4 taktów**,
zsynchronizowane z tempem projektu. Wyjście reverse idzie też mocniej w pogłos niż sygnał
suchy, żeby swell mieszkał w przestrzeni, a nie przed nią.

Pokrętło **Reverse** jest też w panelu MIX na stronie **LIVE**, obok Piano, Pad, Reverb,
Delay i Tone. Stopa REVERSE decyduje *czy* swell w ogóle jest, a to pokrętło *ile* go w
brzmieniu — i tego drugiego nie da się prowadzić w trakcie grania z widoku EDIT.

Preset **Reverse Swell** pokazuje ustawienie. Graj rzadko i zostaw miejsce.

## Wersja standalone — dźwięk i opóźnienie

Standalone to ten sam instrument w osobnym oknie, bez hosta. Ustawienia audio są
pod **Options → Audio/MIDI Settings**.

Dwie rzeczy, na których wszyscy się przewracają:

- **MIDI Input** — JUCE domyślnie ma **wszystkie wejścia MIDI wyłączone**. Trzeba
  ręcznie zaznaczyć swoją klawiaturę, inaczej wtyczka nie zareaguje na nic i
  będzie wyglądać na zepsutą. Klawiatura ekranowa na dole okna działa myszą od
  razu, więc do sprawdzenia brzmienia klawiatura MIDI nie jest potrzebna.
- **Sterownik audio** — tu mieszka opóźnienie.

### Sterowniki, od najgorszego do najlepszego

| Typ | Opóźnienie | Kiedy |
|---|---|---|
| Windows Audio | ~20–40 ms | domyślne, do grania za wolne |
| Windows Audio (Low Latency Mode) | ~10–20 ms | bez sterownika producenta |
| Windows Audio (Exclusive Mode) | ~8–15 ms | blokuje kartę dla tej aplikacji |
| **ASIO** | **3–8 ms** | **sterownik interfejsu audio — to chcesz** |

**ASIO jest wkompilowane** (`JUCE_ASIO=1` w `CMakeLists.txt`). Jeśli interfejs ma
własny sterownik ASIO, pojawi się na liście `Audio device type` jako osobna
pozycja. Wybierz go, a potem zejdź z **Audio buffer size** — 128 lub 256 próbek
przy 48 kHz to 2,7 albo 5,3 ms i tyle wystarczy.

Nie każda karta ma ASIO. Wbudowana karta w laptopie zwykle nie ma — wtedy albo
**ASIO4ALL** (nakładka na sterownik systemowy, pomaga, ale nie dorówna
prawdziwemu), albo **Windows Audio (Exclusive Mode)**, które jest zaskakująco
przyzwoite i nie wymaga niczego instalować.

W DAW-ie to nie dotyczy: tam o opóźnieniu decyduje host, a Reaper i tak chodzi
na ASIO.

> ASIO SDK należy do Steinberga. JUCE dołącza jego nagłówki u siebie, więc nic
> nie trzeba pobierać, ale włączenie tej opcji oznacza, że program podlega
> licencji tych plików. Dla zespołu budującego sobie narzędzie to bez znaczenia;
> przy rozpowszechnianiu gotowych binariów warto o tym wiedzieć.

---

## Skąd wziąć plik `.vst3`

### Wariant 1: Windows, jednym kliknieciem (zalecany)

Potrzebujesz **Visual Studio 2022 Community** z zaznaczonym skladnikiem
*Desktop development with C++* ([pobierz](https://visualstudio.microsoft.com/downloads/)).
CMake jest w nim zawarty, nie trzeba go instalowac osobno.

Potem po prostu uruchom **`WorshipPiano\build-windows.bat`** (dwuklik albo z wiersza
polecen). Skrypt sam:

1. znajdzie CMake — w PATH albo ten dolaczony do Visual Studio 2022/2019,
2. pobierze JUCE i zbuduje wtyczke,
3. zainstaluje ja w folderze VST3 — systemowym, a jesli brak uprawnien, w folderze
   uzytkownika, i wtedy wypisze sciezke, ktora trzeba dodac w Reaperze.

Pierwszy przebieg trwa kilka-kilkanascie minut, bo pobiera JUCE. Kolejne sa szybkie.

Jesli cos pojdzie nie tak, skrypt zatrzyma sie i wypisze przyczyne. Dwie najczestsze:
**Reaper jest uruchomiony** (trzyma wtyczke otwarta, wiec nie da sie jej nadpisac —
zamknij go i uruchom skrypt ponownie) oraz **brak skladnika C++** w Visual Studio.

### Wariant 2: linia polecen (macOS, Linux, albo recznie na Windows)

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

### Wariant 3: gotowy build z GitHub Actions (bez instalowania czegokolwiek)

Po kazdym pushu w `WorshipPiano/` workflow **Build Worship Piano VST3** buduje wtyczke na
Windows i wrzuca ja jako artefakt:

1. Zakladka **Actions** w tym repo
2. Ostatni przebieg **Build Worship Piano VST3**
3. Na dole strony, w sekcji **Artifacts**, pobierz `JafaWorshipPiano-Windows-x64`
   (albo `...-standalone`, jesli chcesz odpalic wtyczke bez Reapera)
4. Rozpakuj — w srodku jest folder `Jafa Worship Piano.vst3`

Buildy na macOS i Linuksa robi sie z reki: Actions → *Run workflow* → **platforms: all**.

Repo jest publiczne, wiec te buildy sa darmowe i nie zjadaja puli 2000 minut konta.
Gdyby repo kiedys stalo sie prywatne, przestaje to obowiazywac — minuty na Windows licza
sie wtedy podwojnie, a na macOS dziesieciokrotnie.

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

## Lista presetów fabrycznych

Strzałki `<` `>` na górnym pasku przeskakują po kolei. Presety są też widoczne jako
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
| **Sample library...** | Wczytanie pliku SFZ albo folderu z WAV-ami. Bez tego wtyczka milczy |
| **Tone** | Ciemno ↔ jasno. Przesuwa filtr filcu i nachylenie widma jednocześnie |
| **Attack** | Ile słychać uderzenia filcu o strunę i stuku mechaniki |
| **Sustain** | Mnożnik czasu tłumienia po puszczeniu klawisza (**0× – 2×**). 1× = tyle, ile deklaruje biblioteka (`ampeg_release`). **0× = nuta kończy się z klawiszem** i sustain robisz wyłącznie pedałem |
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

[`Source/dsp/SampleLibrary.cpp`](Source/dsp/SampleLibrary.cpp) — parser SFZ i sampler.
Sample trzymane jako znormalizowane int16, interpolacja Catmull-Rom przy przestrajaniu,
osobne sample tłumików wyzwalane puszczeniem klawisza. Biblioteka jest wczytywana w wątku
tle i podmieniana na wątku audio przez wskaźnik z licznikiem referencji, więc nic nie jest
zwalniane w callbacku audio.

Poziom jest wyrównywany przy wczytaniu: mierzona jest najgłośniejsza warstwa dynamiki i
skalowana do stałego celu, żeby biblioteka o dowolnym masteringu trafiła w zakres, pod
który zestrojony jest cały tor za nią.

Polifonia ma miękki limit 44 głosów. Powyżej niego najcichsze głosy są **wygaszane rampą
6 ms**, a nie urywane — odebranie brzmiącego głosu przestawia go na zerową próbkę sampla,
a ten skok w przebiegu słychać jako kliknięcie. Głos, który przez pół sekundy nie wyszedł
ponad −90 dBFS, jest wycofywany: sample fortepianowe grają jeszcze długo po tym, jak
przestają być słyszalne, a każdy z nich kosztuje interpolację i filtr.

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
  robi to host, i sprawdza widmem, czy na wyjściu faktycznie jest wczytany sampel
* **kalibracja poziomu i zapas na limiter** — czy biblioteka trafia w spodziewany poziom
  i czy żaden preset nie wchodzi w kolano limitera na twardym akordzie
* **presety użytkownika** — zapis na dysk, odczyt i skasowanie, plus nazwa z takimi znakami,
  że nie da się nią wyjść poza folder presetów; osobno sprawdzane, czy preset zapisany
  z biblioteką oddaje dokładnie tę ścieżkę, a zapisany bez niej nie przyciąga żadnej
* **pula bibliotek** — powrót do raz wczytanej biblioteki nie może ruszyć dysku ani wątku
  ładującego i musi grać już w następnym bloku; inaczej preset przełączający sample
  zatrzymywałby scenę na kilkadziesiąt sekund
* **tłumienie po puszczeniu klawisza** — nuta musi ucichnąć w czasie, który deklaruje
  biblioteka, mierzone jako różnica względem przebiegu z klawiszem trzymanym, więc mierzy
  samą obwiednię, a nie zanikanie sampla. Pilnuje błędu, przez który `ampeg_release` był
  brany za stałą czasową krzywej zamiast za czas zaniku — nuty schodziły wtedy do −60 dB
  jakieś dziewięć razy wolniej, niż biblioteka prosiła
* **kontrolki sceniczne** — transpozycja musi przesuwać wysokość dźwięku (mierzone w centach)
  a split trzymać pianino poza lewą ręką; obie funkcje przepisują numery nut na wejściu,
  co łatwo zepsuć w sposób niewidoczny aż do próby
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

---

## Skąd wzięły się decyzje o funkcjach

Zestaw kontrolek w widoku LIVE nie jest zgadywany — odpowiada temu, co realnie mają rigi
sceniczne używane w kościołach (Sunday Keys i szablony MainStage) oraz temu, co powtarza się
w poradnikach dla grających na klawiszach w uwielbieniu:

* szybkie przeglądanie presetów, warstwy i splity, transpozycja jednym klikiem oraz
  sterowanie sprzętowe zamiast sięgania po myszkę —
  [Sunday Keys](https://sundaysounds.com/pages/sunday-keys),
  [jak złożyć rig klawiszowy](https://worshipteamresources.com/how-to-set-up-a-keys-rig/)
* **low cut w pogłosie**: nadmiar pogłosu robi z brzmienia błoto, a wycięcie dołu z ogona
  jest tym, co temu zapobiega — dlatego `Low Cut` jest osobnym pokrętłem, a nie ukrytą
  stałą — [trzy błędy grających na klawiszach](https://sundaysounds.com/blogs/news/keys-tutorial-three-mistakes-worship-keys-players-should-never-make),
  [najczęstsze błędy pianistów](https://worshiponline.com/the-top-8-mistakes-worship-piano-players-make-how-to-fix-them/)
