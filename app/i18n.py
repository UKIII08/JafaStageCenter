# i18n dla panelu (server-side). Model gettext: teksty w szablonach i we
# flash-ach piszemy PO ANGIELSKU (źródło, rynek USA = priorytet), a polski to
# warstwa tłumaczeń z fallbackiem do angielskiego. Studio i ekrany mają własny
# i18n po stronie klienta (static/js/i18n.js) — tego nie dotyczy.
from flask import session

# Języki dostępne w UI (kod, natywna nazwa). Angielski domyślny (rynek USA).
# Dodanie kolejnego języka = jedna linia tutaj + jego słownik tłumaczeń.
LANGUAGES = (
    ('en', 'English'),
    ('pl', 'Polski'),
    # ('es', 'Español'),
)
SUPPORTED = tuple(code for code, _name in LANGUAGES)
DEFAULT_LANG = 'en'


def get_lang():
    lang = session.get('lang')
    return lang if lang in SUPPORTED else DEFAULT_LANG


def set_lang(lang):
    if lang in SUPPORTED:
        session['lang'] = lang


# Angielskie źródło -> polskie tłumaczenie. Brak wpisu = zostaje angielski.
PL = {
    # ── Nawigacja / topbar / wspólne ──
    "Studio": "Studio", "Services": "Granie", "Songs": "Piosenki",
    "Live": "Live", "Team": "Zespół", "Screens": "Ekrany",
    "Settings": "Ustawienia", "Profile": "Profil", "Panel": "Panel",
    "Sign out": "Wyloguj", "Sign in": "Zaloguj się", "Account": "Konto",
    "Save": "Zapisz", "Save changes": "Zapisz zmiany", "Cancel": "Anuluj",
    "Create": "Utwórz", "Delete": "Usuń", "Remove": "Usuń", "Add": "Dodaj",
    "Edit": "Edytuj", "Open": "Otwórz", "Back": "Wróć", "Date": "Data",
    "Name": "Nazwa", "Title": "Tytuł", "Key": "Tonacja", "BPM": "BPM",
    "Role": "Rola", "Instrument": "Instrument", "Person": "Osoba",
    "Duplicate": "Duplikuj", "For worship teams": "Dla zespołów uwielbienia",
    "None": "Brak", "Comment": "Komentarz",

    # ── Auth: logowanie ──
    "Log in — Jonathan App": "Logowanie — Jonathan App",
    "Log in": "Zaloguj się", "Come back to your team.": "Wróć do swojego zespołu.",
    "E-mail": "E-mail", "Password": "Hasło", "Create account": "Załóż konto",
    "Forgot password": "Nie pamiętam hasła",
    "One place for the whole Sunday.": "Jedno miejsce na całą niedzielę.",
    "We build it because we needed it ourselves. Preparing, leading for the "
    "room and for the band, and sorting out who plays — without three "
    "different apps and a group chat.":
        "Robimy to, bo sami tego potrzebowaliśmy. Przygotowanie, prowadzenie "
        "dla ludzi i dla zespołu, i ogarnięcie kto gra — bez trzech różnych "
        "apek i grupy na WhatsAppie.",
    "The leader, the musician on stage and the projector — connected live.":
        "Prowadzący, muzyk na scenie i rzutnik — połączeni na żywo.",
    "Chords in every musician's key, even if they're just starting out.":
        "Akordy w tonacji każdego muzyka, nawet jeśli dopiero zaczyna.",
    "The tech fades into the background. Worship stays.":
        "Technika schodzi w tło. Zostaje uwielbienie.",
    "Encrypted connection · data in Europe":
        "Szyfrowane połączenie · dane w Europie",

    # ── Auth: rejestracja ──
    "Sign up — Jonathan App": "Rejestracja — Jonathan App",
    "Free for churches. No card.": "Bezpłatnie dla wspólnot. Bez karty.",
    "First name": "Imię", "Visible to your team.": "Widoczne dla Twojego zespołu.",
    "At least 8 characters.": "Minimum 8 znaków.",
    "By creating an account you accept the": "Zakładając konto akceptujesz",
    "terms": "regulamin", "and the": "i", "privacy policy": "politykę prywatności",
    "Already have an account?": "Masz już konto?",
    "Start leading calmer.": "Zacznij prowadzić spokojniej.",
    "Create an account, set up your church and paste your first songs. The "
    "team joins with a single code, screens connect by QR. Fifteen minutes — "
    "and you're ready for Sunday.":
        "Załóż konto, stwórz wspólnotę i wklej pierwsze pieśni. Zespół dołącza "
        "jednym kodem, ekrany podłączasz przez QR. Kwadrans — i jesteś gotowy "
        "na niedzielę.",

    # ── Auth: reset / 2FA ──
    "Reset password — Jonathan App": "Reset hasła — Jonathan App",
    "Reset password": "Reset hasła",
    "We'll send a link to your e-mail.": "Wyślemy link na Twój adres e-mail.",
    "Account e-mail": "E-mail konta", "Send reset link": "Wyślij link resetujący",
    "Back to login": "Wróć do logowania", "It happens to everyone.": "Zdarza się każdemu.",
    "Enter your account e-mail and we'll send a link to set a new password.":
        "Podaj adres konta, a wyślemy link do ustawienia nowego hasła.",
    "New password — Jonathan App": "Nowe hasło — Jonathan App",
    "New password": "Nowe hasło",
    "Enter a new password for your account.": "Wpisz nowe hasło do swojego konta.",
    "Save new password": "Zapisz nowe hasło", "Almost done.": "Prawie gotowe.",
    "Set a new password and get back to your team.":
        "Ustaw nowe hasło i wracaj do zespołu.",
    "Two-factor authentication — Jonathan App": "Weryfikacja dwuetapowa — Jonathan App",
    "Two-factor authentication": "Weryfikacja dwuetapowa",
    "Enter the 6-digit code from your authenticator app.":
        "Wpisz 6-cyfrowy kod z aplikacji uwierzytelniającej.",
    "Verification code": "Kod weryfikacyjny", "One more step.": "Jeszcze jeden krok.",
    "Your account is protected by two-factor authentication. Enter the code "
    "from your authenticator app.":
        "Twoje konto chroni weryfikacja dwuetapowa. Wpisz kod z aplikacji "
        "uwierzytelniającej.",

    # ── Konto ──
    "My account — Jonathan App": "Moje konto — Jonathan App", "My account": "Moje konto",
    "e-mail verified": "e-mail potwierdzony", "e-mail not verified": "e-mail niepotwierdzony",
    "Send verification link": "Wyślij link weryfikacyjny",
    "Enabled — login requires a code from your app.":
        "Włączona — logowanie wymaga kodu z aplikacji.",
    "Confirm with your password to disable": "Potwierdź hasłem, aby wyłączyć",
    "Disable 2FA": "Wyłącz 2FA",
    "An extra layer of account protection — recommended especially for admins. "
    "Requires a free app (Google Authenticator, Microsoft Authenticator, Aegis).":
        "Dodatkowa warstwa ochrony konta — zalecana zwłaszcza dla "
        "administratorów. Potrzebna darmowa aplikacja (Google Authenticator, "
        "Microsoft Authenticator, Aegis).",
    "Enable 2FA": "Włącz 2FA", "Danger zone": "Strefa niebezpieczna",
    "Deleting your account erases all your personal data (GDPR — the right to "
    "be forgotten).":
        "Usunięcie konta kasuje wszystkie Twoje dane osobiste (RODO — prawo "
        "do bycia zapomnianym).",
    "Delete account…": "Usuń konto…",
    "Delete account — Jonathan App": "Usunięcie konta — Jonathan App",
    "Delete account": "Usunięcie konta",
    "Deleting your account is permanent. We'll erase your profile, preferred "
    "keys and notes, availability, service assignments and church memberships.":
        "Usunięcie konta jest nieodwracalne. Skasujemy Twój profil, "
        "preferowane tonacje i notatki, zgłoszenia dostępności, przypisania "
        "do grań oraz członkostwa we wspólnotach.",
    "Confirm with password": "Potwierdź hasłem",
    "Delete account forever": "Usuń konto na zawsze",
    "Really? This can't be undone.": "Na pewno? Tej operacji nie da się cofnąć.",
    "You own communities with other members:":
        "Jesteś właścicielem wspólnot z innymi członkami:",
    "Before deleting your account, hand them over to another admin (Team → "
    "change role) or remove the remaining members.":
        "Zanim usuniesz konto, przekaż je innemu adminowi (Zespół → zmień "
        "rolę) albo usuń pozostałych członków.",
    "You are the only member of:": "Jesteś jedynym członkiem wspólnot:",
    "they will be deleted entirely (songs, setlists, services, files).":
        "zostaną usunięte w całości (piosenki, setlisty, grania, pliki).",

    # ── Panel: wspólnota ──
    "Create your church": "Załóż wspólnotę",
    "You'll create a space for your team — songs, setlists and musician profiles.":
        "Utworzysz przestrzeń dla swojego zespołu — piosenki, setlisty i "
        "profile muzyków.",
    "Church / community name": "Nazwa wspólnoty / zboru",
    "e.g. Grace Community Church": "np. Zbór Betania Warszawa",
    "Choose a community": "Wybierz wspólnotę",
    "Your role:": "Twoja rola:",
    "Your communities": "Twoje wspólnoty", "New community": "Nowa wspólnota",
    "Invalid or expired link": "Nieprawidłowy lub wygasły link",
    "Ask the leader for a new invite link.":
        "Poproś prowadzącego o nowy link zaproszenia.",
    "Live now": "Na żywo", "A live session is running": "Trwa sesja LIVE",
    "Join as a musician": "Dołącz jako muzyk",
    "Leader panel": "Panel prowadzącego",

    # ── Dashboard (kafelki na wejście) ──
    "Good to see you, %(name)s": "Dobrze Cię widzieć, %(name)s",
    "here is what matters today.": "oto co dziś najważniejsze.",
    "Welcome back — your worship buddy is ready.": "Witaj z powrotem — Twój kumpel od uwielbienia jest gotowy.",
    "How to pick voicings": "Jak dobierać chwyty",
    "Easy": "Łatwe",
    "Smooth": "Płynne",
    "open": "otwarty",
    "fret": "próg",
    "best for this song": "najlepszy do tej piosenki",
    "Note": "Notatka",
    "Note for this part (only you)": "Notatka do tej części (tylko Ty)",
    "Plain": "Zwykłe",
    "Pretty": "Ładne",
    "plain": "zwykły",
    "Setlist for:": "Setlista dla:",
    "click Save setlist to attach": "kliknij Zapisz setlistę, aby podpiąć",
    "First pick a song from the setlist": "Najpierw wybierz piosenkę z setlisty",
    "Projector (lyrics for the congregation) and the stage screen (chords for the band).":
        "Rzutnik (tekst dla zboru) i ekran sceny (akordy dla zespołu).",
    "Open the link on the device once — it is remembered and joins every LIVE session by itself.":
        "Otwórz link na urządzeniu raz — zapamięta się i sam podejmie każdą sesję LIVE.",
    "Name (e.g. Projector – main hall)": "Nazwa (np. Rzutnik sala główna)",
    "Projector (lyrics)": "Rzutnik (tekst)",
    "Stage screen (chords)": "Ekran sceny (akordy)",
    "Add screen": "Dodaj ekran",
    "Projector": "Rzutnik",
    "Stage screen": "Ekran sceny",
    "lyrics": "tekst",
    "chords": "akordy",
    "Disconnect this screen?": "Odłączyć ten ekran?",
    "Disconnect": "Odłącz",
    "Get your church set up": "Skonfiguruj swoją wspólnotę",
    "%(done)s of %(total)s done — you can do these in any order":
        "%(done)s z %(total)s zrobione — kolejność dowolna",
    "Hide": "Ukryj",
    "Add your first songs": "Dodaj pierwsze piosenki",
    "Invite your team": "Zaproś zespół",
    "Add your church logo": "Dodaj logo wspólnoty",
    "Connect a screen": "Podłącz ekran",
    "Plan your first service": "Zaplanuj pierwsze granie",
    # ── Ekran powitalny (odliczanie + ogłoszenia) ──
    "Welcome screen": "Ekran powitalny",
    "Edit announcements": "Edytuj ogłoszenia",
    "A countdown to this service plus rotating announcements — shown on the projector before the first song. Photos are shared across your services.":
        "Odliczanie do tego grania i przewijające się ogłoszenia — pokazywane na rzutniku przed pierwszą pieśnią. Zdjęcia są wspólne dla wszystkich grań.",
    "Countdown to this service plus rotating announcements, shown on the projector before the first song. Launch it live from Studio with “Play announcements”.":
        "Odliczanie do tego grania i przewijające się ogłoszenia na rzutniku przed pierwszą pieśnią. Odpal na żywo ze Studia przyciskiem „Ogłoszenia”.",
    "Countdown to this service plus rotating announcements, shown on the projector before the first song. They belong to this service's setlist, so they also play when you load it from History in Studio. Launch it live with “Play announcements”.":
        "Odliczanie do tego grania i przewijające się ogłoszenia na rzutniku przed pierwszą pieśnią. Należą do setlisty tego grania, więc odtworzą się także, gdy wczytasz ją z Historii w Studiu. Odpal na żywo przyciskiem „Ogłoszenia”.",
    "Announcements belong to a setlist. Arrange or attach a setlist above first, then you can add the countdown and announcements here.":
        "Ogłoszenia należą do setlisty. Najpierw ułóż lub podepnij setlistę powyżej, a potem dodasz tu odliczanie i ogłoszenia.",
    "A countdown to your service start plus rotating announcements — shown on the projector before the first song. These belong to this setlist, so they follow it into Studio and the offline app. Photos are shared across your services.":
        "Odliczanie do startu nabożeństwa i przewijające się ogłoszenia — pokazywane na rzutniku przed pierwszą pieśnią. Należą do tej setlisty, więc podążają za nią do Studia i aplikacji offline. Zdjęcia są wspólne dla wszystkich grań.",
    "Service start time": "Godzina rozpoczęcia",
    "Open on projector ↗": "Otwórz na rzutniku ↗",
    "Open on projector": "Otwórz na rzutniku",
    "A countdown to your next service plus rotating announcements — shown on the projector before the first song. Set it once; it reuses your photos across services.":
        "Odliczanie do najbliższego grania i przewijające się ogłoszenia — pokazywane na rzutniku przed pierwszą pieśnią. Ustawiasz raz; zdjęcia używane są wielokrotnie.",
    "Photo library": "Biblioteka zdjęć",
    "Up to 10 photos, reused across announcements.": "Do 10 zdjęć, wielokrotnego użytku w ogłoszeniach.",
    "Announcements": "Ogłoszenia",
    "+ Add announcement": "+ Dodaj ogłoszenie",
    "Seconds per announcement": "Sekundy na ogłoszenie",
    "Photo": "Zdjęcie",
    "— no photo —": "— bez zdjęcia —",
    "Announcement title": "Tytuł ogłoszenia",
    "Short description": "Krótki opis",
    "Badge (optional)": "Etykieta (opcjonalnie)",
    "Background icons (watermark)": "Ikony w tle (znak wodny)",
    "Your church symbols, shown faintly behind the announcements — a dark shape on a light or white background works best. Leave empty to use the built-in ones.":
        "Symbole Twojej wspólnoty, pokazywane subtelnie w tle ogłoszeń — najlepiej ciemny kształt na jasnym lub białym tle. Zostaw puste, aby użyć wbudowanych.",
    "Icon limit reached.": "Osiągnięto limit ikon.",
    "Delete this photo?": "Usunąć to zdjęcie?",
    "Saved.": "Zapisano.",
    "STARTS IN": "START ZA",
    "ANNOUNCEMENT": "OGŁOSZENIE",
    "Add announcements in the event planner to show them here.":
        "Dodaj ogłoszenia w planerze wydarzeń, aby pokazać je tutaj.",
    "Photo limit reached (10).": "Osiągnięto limit zdjęć (10).",
    "No file.": "Brak pliku.",
    "Must be an image up to 8 MB.": "Musi być obrazem do 8 MB.",
    # ── Podpowiedzi na hover (coach marks) ──
    "Hover tips": "Podpowiedzi",
    "On": "Wł.",
    "Off": "Wył.",
    "Little tips appear when you hover over buttons. They show automatically the first few times you open the app, then switch off — turn them back on here anytime.":
        "Krótkie podpowiedzi pojawiają się, gdy najedziesz myszką na przycisk. Przez pierwsze kilka uruchomień apki pokazują się same, potem się wyłączają — tutaj możesz je włączyć z powrotem w każdej chwili.",
    "Run the service live — pick slides and everyone’s screens follow the same second.":
        "Prowadź granie na żywo — wybierasz slajdy, a ekrany wszystkich zmieniają się w tej samej sekundzie.",
    "Plan a service — the team marks availability, you assign parts and attach the setlist.":
        "Zaplanuj granie — zespół zaznacza dostępność, Ty przydzielasz role i podpinasz setlistę.",
    "Your song library — import from ChordPro/.txt, set keys and edit chords.":
        "Twoja biblioteka pieśni — importuj z ChordPro/.txt, ustawiaj tonacje i edytuj akordy.",
    "The musician view on your phone — chords in your key, tuner, metronome and auto-scroll.":
        "Widok muzyka na telefonie — akordy w Twojej tonacji, stroik, metronom i auto-przewijanie.",
    "Invite members and set roles — musicians add songs, leaders run the service.":
        "Zaproś członków i ustaw role — muzycy dodają pieśni, prowadzący prowadzą granie.",
    "Language, theme, church logo, projection look and CCLI — and turn these tips on or off.":
        "Język, motyw, logo wspólnoty, wygląd projekcji i CCLI — oraz włączanie i wyłączanie tych podpowiedzi.",
    "Your instrument and preferred key — every chart transposes to what you actually play.":
        "Twój instrument i preferowana tonacja — każdy zapis akordów przeniesie się na to, co realnie grasz.",
    'Discover what you can do →': 'Odkryj, co potrafi apka →',
    'What Jonathan can do': 'Co potrafi Jonathan',
    'A quick tour of what makes Jonathan different — pick what your team needs, no need to use it all at once.': 'Szybki przegląd tego, co wyróżnia Jonathana — wybierz to, czego potrzebuje Twój zespół, nie musisz używać wszystkiego naraz.',
    'One system, three screens': 'Jeden system, trzy ekrany',
    'Worship leader · Studio': 'Prowadzący · Studio',
    'Click once, everyone sees it': 'Klikasz raz — widzą wszyscy',
    'You pick a slide in Studio — the projector, the stage screen and every musician’s phone update the same second.': 'Wybierasz slajd w Studiu — rzutnik, ekran sceny i telefon każdego muzyka aktualizują się w tej samej sekundzie.',
    'Smart song-to-song transitions': 'Sprytne przejścia między piosenkami',
    'A music engine suggests bridge chords from one key to the next, aware of the style and tempo of both songs.': 'Silnik muzyczny podpowiada akordy-pomost z jednej tonacji do drugiej, świadomy stylu i tempa obu piosenek.',
    'Ambient pads in the song’s key': 'Pady w tonacji piosenki',
    'Atmosphere beds that follow the current key with smooth crossfades when it changes.': 'Podkłady atmosferyczne idące za aktualną tonacją, z płynnym przejściem przy zmianie.',
    'Spontaneous moments': 'Spontaniczne momenty',
    'One tap to put a line of text on screen for an unplanned moment — save it as a tile to reuse.': 'Jedno dotknięcie, by wrzucić tekst na ekran w nieplanowanym momencie — zapisz jako kafelek, by użyć ponownie.',
    'Open Studio →': 'Otwórz Studio →',
    'Made for every musician': 'Dla każdego muzyka',
    'Musician · their phone': 'Muzyk · jego telefon',
    'Chords in YOUR key': 'Akordy w TWOJEJ tonacji',
    'Each musician saves a preferred key — everyone sees the chart transposed to what they actually play.': 'Każdy muzyk zapisuje swoją tonację — każdy widzi zapis transponowany do tego, co realnie gra.',
    'Plain or Pretty voicings': 'Zwykłe lub ładne chwyty',
    'Switch between simple shapes and tasteful open chords (add9, sus, m7) — the algorithm picks the best for the song.': 'Przełączaj między prostymi kształtami a ładnymi otwartymi akordami (add9, sus, m7) — algorytm wybiera najlepszy do piosenki.',
    'Every shape on the neck': 'Każdy chwyt na gryfie',
    'Browse all fingerings of a chord up the fretboard, with the best-for-this-song one starred.': 'Przeglądaj wszystkie przewroty akordu w górę gryfu, z gwiazdką na najlepszym do tej piosenki.',
    'Practice mode': 'Tryb ćwiczenia',
    'Metronome, auto-scroll, capo and beginner mode, and a private note on any part of the song.': 'Metronom, autoprzewijanie, kapo i tryb początkującego oraz prywatna notatka do dowolnej części piosenki.',
    'Built-in tuner': 'Wbudowany stroik',
    'Tune straight from the phone before you play — no extra app.': 'Nastrój prosto z telefonu przed graniem — bez osobnej apki.',
    'Set my instrument & key →': 'Ustaw instrument i tonację →',
    'Clean screens for the room': 'Czyste ekrany dla sali',
    'Congregation · projector': 'Zbór · rzutnik',
    'Lyrics without the clutter': 'Tekst bez bałaganu',
    'The congregation sees clean lyrics — your church’s background and logo, no chords.': 'Zbór widzi czysty tekst — tło i logo Waszej wspólnoty, bez akordów.',
    'CCLI notice, automatic': 'Notka CCLI automatycznie',
    'The copyright line and song-usage count are handled for you, ready for your reporting period.': 'Linia copyright i licznik użyć pieśni robią się same, gotowe na Wasz okres raportowania.',
    'Connect a screen with a QR': 'Podłącz ekran przez QR',
    'Open the link on a projector or TV once — it joins every LIVE session by itself.': 'Otwórz link na rzutniku lub TV raz — sam dołączy do każdej sesji LIVE.',
    'Connect a screen →': 'Podłącz ekran →',
    'Get the team ready': 'Przygotuj zespół',
    'Whole team': 'Cały zespół',
    'Plan a service': 'Zaplanuj granie',
    'The team marks availability, you assign who plays what and attach the setlist.': 'Zespół zaznacza dostępność, Ty przydzielasz kto co gra i podpinasz setlistę.',
    'Everyone knows their part': 'Każdy wie, co gra',
    'Each musician sees when they play and gets practice links in their own key.': 'Każdy muzyk widzi, kiedy gra, i dostaje linki do ćwiczenia w swojej tonacji.',
    'Keys that fit your vocalists': 'Tonacje pod Waszych wokalistów',
    'Building the setlist, you see who prefers which key — and transpose in one click.': 'Układając setlistę, widzisz kto woli jaką tonację — i transponujesz jednym kliknięciem.',
    'Plan a service →': 'Zaplanuj granie →',
    'Quietly in the background': 'Po cichu w tle',
    'Behind the scenes': 'Za kulisami',
    'Cloud sync with the desktop app': 'Synchronizacja z aplikacją desktop',
    'The offline .exe pulls your songs, setlists and profiles from the cloud on startup — work anywhere, on or offline.': 'Offline’owy .exe dociąga piosenki, setlisty i profile z chmury przy starcie — pracuj gdziekolwiek, online i offline.',
    'Import your existing library': 'Zaimportuj istniejącą bibliotekę',
    'Bring songs in from ChordPro (.cho) or .txt in one step — title, key and CCLI number are read automatically.': 'Wciągnij piosenki z ChordPro (.cho) lub .txt w jednym kroku — tytuł, tonacja i numer CCLI czytają się same.',
    'Leader & musician roles': 'Role prowadzącego i muzyka',
    'Musicians add songs and set their keys; leaders run the service and manage the team.': 'Muzycy dodają piosenki i ustawiają tonacje; prowadzący prowadzą granie i zarządzają zespołem.',

    "You're on the team": "Grasz w obsadzie",
    "Your next service:": "Twoje najbliższe granie:",
    "Prepare! →": "Przygotuj się! →",
    "No upcoming service": "Brak nadchodzącego grania",
    "When a service is scheduled, it shows up here with everything you need to "
    "prepare.":
        "Gdy zaplanujecie granie, pojawi się tu razem ze wszystkim, czego "
        "potrzebujesz do przygotowania.",
    "Plan a service →": "Zaplanuj granie →",
    "See services →": "Zobacz grania →",
    "Back to practice": "Wróć do ćwiczenia",
    "Open the song library and rehearse with chords and diagrams.":
        "Otwórz bibliotekę piosenek i ćwicz z akordami i diagramami.",
    "Practice now →": "Ćwicz teraz →",
    "Build the setlist and run the whole service live.":
        "Ułóż setlistę i poprowadź całe granie na żywo.",
    "Open Studio →": "Otwórz Studio →",
    "Live view": "Widok na żywo",
    "Follow lyrics and chords sent live during the service.":
        "Śledź tekst i akordy wysyłane na żywo podczas grania.",
    "Go live →": "Wejdź na żywo →",
    "See who plays and invite new members.":
        "Zobacz, kto gra, i zaproś nowe osoby.",
    "View team →": "Zobacz zespół →",
    "My profile": "Mój profil",
    "Set your instrument and playing preferences.":
        "Ustaw swój instrument i preferencje grania.",
    "Edit profile →": "Edytuj profil →",
    # Dashboard „Precision" (bento) — nowe etykiety
    "Next service": "Najbliższe granie",
    "more songs": "więcej pieśni", "Prepare": "Przygotuj się",
    "Offline": "Offline",
    "Plan a service": "Zaplanuj granie", "See services": "Zobacz grania",
    "Last setlist:": "Ostatnia setlista:",
    "Recently practiced:": "Ostatnio ćwiczone:",
    "Practiced %(d)s of %(t)s songs from the setlist":
        "Przećwiczone %(d)s z %(t)s pieśni z setlisty",
    "people": "osób",
    # Wygląd i język (ustawienia / profil)
    "Appearance & language": "Wygląd i język",
    # Logo wspólnoty + wygląd projekcji (strona Ustawień)
    "Church logo & projection look": "Logo wspólnoty i wygląd projekcji",
    "The logo shows on the projector when nothing is being displayed. Colors "
    "and font apply to what the congregation sees on screen.":
        "Logo pokazuje się na rzutniku, gdy nic nie jest wyświetlane. Kolory i "
        "czcionka dotyczą tego, co zbór widzi na ekranie.",
    "Logo (PNG/JPG, up to 8 MB)": "Logo (PNG/JPG, do 8 MB)",
    "Choose logo": "Wybierz logo",
    "Projector background (optional)": "Tło rzutnika (opcjonalnie)",
    "Choose background": "Wybierz tło", "Remove background": "Usuń tło",
    "Projection font": "Czcionka projekcji",
    "Background": "Tło", "Text": "Tekst", "Save appearance": "Zapisz wygląd",
    "Theme": "Motyw", "Light": "Jasny", "Dark": "Ciemny",
    "Language": "Język",
    # Dashboard — dane na kafelkach (design z obrazków)
    "today": "dzisiaj", "tomorrow": "jutro",
    "in %(n)s days": "za %(n)s dni",
    "songs": "pieśni", "min": "min",
    "No active session. Last:": "Brak aktywnej sesji. Ostatnia:",
    "No active session yet.": "Jeszcze bez sesji na żywo.",
    "International notation": "Notacja międzynarodowa",
    "Polish notation": "Notacja polska",
    "capo": "kapo", "chords on": "akordy wł.", "chords off": "akordy wył.",
    "admins": "adminów", "leaders": "prowadzących", "musicians": "muzyków",

    "Prepare songs and a setlist, invite the team, and on Sunday start a LIVE "
    "session from the chosen setlist — the team's phones and screens sync "
    "automatically.":
        "Przygotuj piosenki i setlistę, zaproś zespół, a w niedzielę rozpocznij "
        "sesję LIVE z wybranej setlisty — telefony zespołu i ekrany "
        "zsynchronizują się same.",

    # ── Panel: zespół ──
    "Instrument": "Instrument", "Invite to the team": "Zaproś do zespołu",
    "Generate link": "Wygeneruj link", "Invite link": "Link zaproszenia",
    "Role:": "Rola:", "musician": "muzyk", "leader": "prowadzący", "admin": "admin",
    # kody ról (dashboard używa _(membership.role)) — ładne PL
    "muzyk": "muzyk", "prowadzacy": "prowadzący",
    "Change role": "Zmień rolę", "owner": "właściciel",
    "Remove from the team?": "Usunąć z zespołu?",
    "Profile without an account:": "Profil bez konta:",
    "— from the desktop app": "— z aplikacji desktop",
    "A join link, valid until": "Link dołączenia, ważny do",
    "— send it to your team (e.g. in a group chat):":
        "— wyślij zespołowi (np. na grupie):",
    "Role: musician": "Rola: muzyk", "Role: leader": "Rola: prowadzący",
    "Generate a new link": "Wygeneruj nowy link",
    # settings — pady + CCLI opis
    "Atmosphere beds played in Studio in the current song's key. Upload up to "
    "12 MP3 files named by major key:":
        "Tła dźwiękowe odtwarzane w Studiu pod tonację piosenki. Wgraj do 12 "
        "plików MP3 nazwanych tonacją durową:",
    "(flats work too — Eb.mp3 saves as D#). Minor keys play the pad of the "
    "relative major, so 12 files are enough.":
        "(bemole też zadziałają — Eb.mp3 zapisze się jako D#). Tonacje molowe "
        "grają pad równoległej durowej, więc 12 plików wystarcza.",
    "Remove pad": "Usunąć pad", "Click to remove": "Kliknij, aby usunąć",
    "No file": "Brak pliku",
    "The notice (title, writers, © and license number) is required by the "
    "CCLI license when projecting lyrics — turn it off only if you don't use "
    "CCLI-covered songs. Song uses still count toward the":
        "Notka (tytuł, autorzy, © i numer licencji) to warunek licencji CCLI "
        "przy projekcji tekstów — wyłączaj tylko, jeśli nie korzystasz z "
        "utworów objętych CCLI. Użycia piosenek zliczają się niezależnie do",

    # ── Ustawienia wspólnoty ──
    "Settings — %(church)s": "Ustawienia — %(church)s",
    "Community settings": "Ustawienia wspólnoty",
    "Default chord notation": "Domyślna notacja akordów",
    "International (Bb, B)": "Międzynarodowa (Bb, B)",
    "Polish (B, H, Cis, Fis)": "Polska (B, H, Cis, Fis)",
    "Song-to-song transition engine": "Silnik przejść między piosenkami",
    "Contextual (recommended)": "Kontekstowy (zalecany)",
    "Pivot Pro": "Pivot Pro", "Advanced": "Advanced",
    "CCLI license number (optional — US market)":
        "Numer licencji CCLI (opcjonalnie — rynek USA)",
    "e.g. 123456789": "np. 123456789",
    "Show the copyright notice on the projector":
        "Pokazuj notkę copyright na rzutniku",
    "With a CCLI license the projector adds the required copyright notice "
    "automatically, and song uses count toward the": "",  # long, handled inline
    "CCLI report": "raport CCLI",
    "Atmosphere pads": "Pady atmosfery",
    "Upload MP3 files": "Wgraj pliki MP3",
    "you can select all at once": "możesz zaznaczyć wszystkie naraz",

    # ── Granie (events) ──
    "Services — %(church)s": "Granie — %(church)s",
    "New service": "Nowe granie",
    "Name (e.g. Sunday morning)": "Nazwa (np. Niedziela poranna)",
    "The third field is the signup deadline (optional) — after it the team "
    "can still mark availability, but it shows as past due.":
        "Trzecie pole to termin zgłoszeń (opcjonalny) — po nim zespół nadal "
        "może zaznaczać dostępność, ale widać, że jest po terminie.",
    "Upcoming services": "Nadchodzące grania",
    "Recent services": "Ostatnie grania",
    "Signup deadline (optional)": "Termin zgłoszeń (opcjonalnie)", "yes": "tak",
    "My availability": "Moja dostępność", "Playing on": "Gram na",
    "no reply": "brak odpowiedzi", "can": "mogę", "can't": "nie mogę",
    "Nothing planned yet": "Nic jeszcze nie zaplanowano",
    "Create your first service above — the team gets a place to mark "
    "availability.":
        "Utwórz pierwsze granie powyżej — zespół dostanie miejsce, żeby "
        "zaznaczyć dostępność.",
    "When the leader schedules a service, it shows up here with your "
    "availability and a setlist to learn.":
        "Gdy prowadzący zaplanuje granie, pojawi się tutaj z Twoją "
        "dostępnością i setlistą do nauki.",
    "Delete service": "Usuń granie", "Delete this service?": "Usunąć to granie?",
    "Song": "Piosenka",
    "Signup deadline:": "Termin zgłoszeń:", "past due": "po terminie",
    "I can play": "Mogę grać", "I can't": "Nie mogę",
    "Comment (e.g. only until noon)": "Komentarz (np. tylko do 12:00)",
    "The signup deadline has passed, but you can still change your answer — "
    "just let the leader know.":
        "Termin zgłoszeń minął, ale nadal możesz zmienić odpowiedź — daj "
        "tylko znać prowadzącemu.",
    "You're playing this service:": "Grasz na tym graniu:",
    "instrument unspecified": "instrument nieokreślony",
    "Setlist": "Setlista", "orig.": "oryg.",
    '"Practice" opens the song in the setlist key — with a metronome, '
    'auto-scroll and your private note.':
        "„Ćwicz” otwiera piosenkę w tonacji z setlisty — z metronomem, "
        "autoprzewijaniem i Twoją prywatną notatką.",
    "not in library": "brak w bibliotece", "Practice": "Ćwicz",
    "Setlist from Studio": "Setlista ze Studia",
    "Arrange the setlist in Studio": "Ułóż setlistę w Studiu",
    "Edit the setlist in Studio": "Edytuj setlistę w Studiu",
    "The button opens Studio in this service's mode: arrange songs, order and "
    "keys, hit “Save setlist” — and the setlist attaches here by itself. You "
    "can also attach one you saved earlier:":
        "Przycisk otwiera Studio w trybie tego grania: układasz piosenki, "
        "kolejność i tonacje, klikasz „Zapisz setlistę” — i setlista sama "
        "podpina się tutaj. Możesz też podpiąć wcześniej zapisaną:",
    "— none / detach —": "— brak / odepnij —", "no date": "bez daty",
    "Attach selected": "Podepnij wybraną",
    "Team responses": "Zgłoszenia zespołu", "Availability": "Dostępność",
    "Lineup — who plays": "Obsada — kto gra",
    "The lineup isn't set yet.": "Obsada jeszcze nie ułożona.",
    "You can add the same person several times with different instruments. "
    "The list shows who signed up.":
        "Tę samą osobę możesz dodać kilka razy z różnymi instrumentami. Lista "
        "podpowiada, kto się zgłosił.",
    "— instrument —": "— instrument —", "Add to lineup": "Dodaj do obsady",
    "(can play)": "(mogę)", "(can't play!)": "(nie może!)", "(no reply)": "(brak odp.)",
    "Edit service": "Edytuj granie",
    "Note for the team (e.g. rehearsal at 8:30)":
        "Notatka dla zespołu (np. próba o 8:30)",

    # ── Piosenki ──
    "Songs — %(church)s": "Piosenki — %(church)s",
    "The library is empty": "Biblioteka jest pusta",
    "Manage in Studio": "Zarządzaj w Studiu", "Edit in Studio": "Edytuj w Studiu",
    "Import .txt": "Importuj .txt",
    "Search by title or lyrics": "Szukaj po tytule lub tekście",
    "Add your first song with the button above — or import a .txt file "
    "exported from the desktop app.":
        "Dodaj pierwszą pieśń przyciskiem powyżej — albo zaimportuj plik .txt "
        "z eksportu aplikacji desktop.",
    "Setlists — %(church)s": "Setlisty — %(church)s",
    "Setlists": "Setlisty", "New setlist": "Nowa setlista",
    "Name (e.g. Sunday morning)": "Nazwa (np. Niedziela poranna)",
    "No setlists": "Brak setlist",
    "Setlists are arranged in Studio and attached to a specific service.":
        "Setlisty układasz w Studiu i podpinasz do konkretnego grania.",
    "Delete this song?": "Usunąć tę piosenkę?",
    "Delete setlist?": "Usunąć setlistę?", "# of songs": "Piosenek",
    "The setlist is empty — add songs below.":
        "Setlista jest pusta — dodaj piosenki poniżej.",
    "Up": "W górę", "Down": "W dół", "Add to setlist": "Dodaj do setlisty",
    "Transpose": "Transpozycja", "Songs count": "Piosenek",
    "Practice — %(title)s": "Ćwiczenie — %(title)s", "my key": "moja tonacja",
    "Auto-scroll": "Autoprzewijanie", "Metronome": "Metronom", "Stop": "Stop",
    "Recording": "Nagranie",
    "Recording link (optional)": "Link do nagrania (opcjonalnie)",
    "YouTube, Spotify, Google Drive… — anything to practice with":
        "YouTube, Spotify, Google Drive… — cokolwiek do ćwiczenia",
    "saved": "zapisano", "saving…": "zapisywanie…",
    "Practice:": "Ćwiczenie:", "my key": "moja tonacja",
    "Chords": "Akordy", "Guitar": "Gitara", "Piano": "Pianino",
    "No chords to show yet.": "Brak akordów do pokazania.",
    "My note": "Moja notatka", "(visible only to you)": "(widoczna tylko dla Ciebie)",
    "e.g. play barre on the bridge, come in on 3":
        "np. w bridge gram barré, wejście na 3",
    "Start LIVE": "Rozpocznij LIVE", "Song": "Piosenka",
    # form (dodawanie/edycja poza Studiem)
    "Add song": "Dodaj piosenkę", "Edit:": "Edytuj:",
    "Input notation": "Notacja wejściowa",
    "Chords in square brackets:": "Akordy w nawiasach kwadratowych:",
    "Separate sections (Verse, Chorus) with a blank line. Pasted a song with "
    "chords above the lyrics (e.g. from a tabs site)? Use the convert button.":
        "Sekcje (Zwrotka, Refren) oddzielaj pustą linią. Wkleiłeś piosenkę z "
        "akordami nad tekstem (np. z serwisu z chwytami)? Użyj przycisku "
        "konwersji.",
    "Convert chords-above-lyrics": "Konwertuj akordy nad tekstem",
    "Save to library": "Zapisz do biblioteki",

    # ── Mój profil ──
    "My profile": "Mój profil", "Account & password": "Konto i hasło",
    "Settings save to your account and apply automatically in the musician "
    "view (live and practice) on every device.":
        "Ustawienia zapisują się na Twoim koncie i stosują automatycznie w "
        "widoku muzyka (live i ćwiczenie) na każdym urządzeniu.",
    "Name / nickname (visible to the team)":
        "Imię / pseudonim (widoczne dla zespołu)",
    "Chord notation": "Notacja akordów",
    "Default capo (frets)": "Domyślne capo (progi)",
    "Show chords": "Pokazuj akordy",
    "Lowercase = minor": "Małe litery = moll",
    "Beginner mode (simplify chords)": "Tryb początkującego (upraszczaj akordy)",

    # ── Piosenki: widok / edycja ──
    "Team preferences:": "Preferencje zespołu:",

    # ── Flash: panel ──
    "Enter a community name (min. 3 characters).":
        "Podaj nazwę wspólnoty (min. 3 znaki).",
    "You joined the team! Set your instrument and preferences.":
        "Dołączyłeś do zespołu! Ustaw swój instrument i preferencje.",
    "Settings saved.": "Zapisano ustawienia.",
    "Profile saved.": "Zapisano profil.",

    # ── Flash: auth ──
    "Enter a valid e-mail address.": "Podaj poprawny adres e-mail.",
    "Password must be at least 8 characters.": "Hasło musi mieć co najmniej 8 znaków.",
    "Enter your name.": "Podaj swoje imię.",
    "An account with this address already exists — please log in.":
        "Konto z tym adresem już istnieje — zaloguj się.",
    "Invalid e-mail or password.": "Nieprawidłowy e-mail lub hasło.",
    "Invalid code — try again.": "Nieprawidłowy kod — spróbuj ponownie.",
    "Two-factor authentication enabled.": "Weryfikacja dwuetapowa włączona.",
    "The code doesn't match — scan the QR again and try once more.":
        "Kod się nie zgadza — zeskanuj QR jeszcze raz i spróbuj.",
    "Wrong password — 2FA stays enabled.": "Błędne hasło — 2FA pozostaje włączone.",
    "Two-factor authentication disabled.": "Weryfikacja dwuetapowa wyłączona.",
    "If the account exists, we've sent a password reset link.":
        "Jeśli konto istnieje, wysłaliśmy link do resetu hasła.",
    "The link expired or is invalid — request a new one.":
        "Link wygasł lub jest nieprawidłowy — poproś o nowy.",
    "Password changed — please log in.": "Hasło zmienione — zaloguj się.",
    "We've sent a verification link to your e-mail address.":
        "Wysłaliśmy link weryfikacyjny na Twój adres e-mail.",
    "The verification link expired — send a new one from account settings.":
        "Link weryfikacyjny wygasł — wyślij nowy z ustawień konta.",
    "E-mail address confirmed.": "Adres e-mail potwierdzony.",
    "Wrong password — the account was not deleted.":
        "Błędne hasło — konto nie zostało usunięte.",
    "First hand the community over to another admin or remove the remaining "
    "members.":
        "Najpierw przekaż wspólnotę innemu adminowi albo usuń pozostałych "
        "członków.",
    "Your account and data have been deleted.":
        "Konto i dane zostały usunięte.",

    # ── Maile ──
    "Jonathan App — confirm your e-mail": "Jonathan App — potwierdź adres e-mail",
    "Hi %(name)s!": "Cześć %(name)s!",
    "Confirm your e-mail address by opening this link (valid for 3 days):":
        "Potwierdź swój adres e-mail, otwierając link (ważny 3 dni):",
    "If you didn't create this account, ignore this message.":
        "Jeśli to nie Ty zakładałeś konto — zignoruj tę wiadomość.",
    "Jonathan App — password reset": "Jonathan App — reset hasła",
    "To set a new password, open this link (valid for 2 hours):":
        "Aby ustawić nowe hasło, otwórz link (ważny 2 godziny):",

    # ── Flash: events ──
    "Enter a service date.": "Podaj datę grania.",
    "Service deleted.": "Usunięto granie.",

    # ── Flash: panel (dodatkowe) ──
    "The community owner stays an administrator.":
        "Założyciel wspólnoty pozostaje administratorem.",
    "The community owner can't be removed.":
        "Nie można usunąć założyciela wspólnoty.",
    "Removed from the team.": "Usunięto z zespołu.",

    # ── Flash: songs ──
    "Song saved.": "Zapisano piosenkę.",
    "Setlist created.": "Utworzono setlistę.",
    "Setlist deleted.": "Usunięto setlistę.",
    "Title and content are required.": "Tytuł i treść są wymagane.",
    "Added:": "Dodano:", "Deleted:": "Usunięto:", "Saved changes.": "Zapisano zmiany.",
    "Imported:": "Zaimportowano:",
    "Skipped (title already exists):": "Pominięto (tytuł już istnieje):",
    "Import songs": "Importuj piosenki",
    "Import ChordPro (.cho) or .txt files. Title, key, CCLI number and copyright are picked up automatically. Only import songs you are licensed to use.":
        "Importuj pliki ChordPro (.cho) lub .txt. Tytuł, tonacja, numer CCLI i copyright wczytują się automatycznie. Importuj tylko piosenki, do których masz licencję.",
    "Skipped (file too large, max 512 KB):": "Pominięto (plik za duży, maks. 512 KB):",

    # ── Flash: live / studio ──
    "A live session is already running — joined it.":
        "Sesja LIVE już trwa — dołączono do niej.",
    "Live session ended.": "Zakończono sesję LIVE.",
    "Pads uploaded:": "Wgrano pady:",
    "Skipped (bad name — use e.g. C.mp3, F#.mp3, Eb.mp3):":
        "Pominięto (zła nazwa — użyj np. C.mp3, F#.mp3, Eb.mp3):",
}


def translate(text):
    if get_lang() == 'pl':
        return PL.get(text, text)
    return text


# ── Instrumenty ──────────────────────────────────────────────────────────
# Wartości w bazie są po polsku (zgodność ze starymi danymi), ale ETYKIETĘ
# wyświetlamy tłumaczoną: EN domyślnie (rynek USA), PL jako fallback.
INSTRUMENT_LABELS = {
    'wokal': 'Vocals',
    'gitara': 'Guitar',
    'gitara elektryczna': 'Electric guitar',
    'bas': 'Bass',
    'klawisze': 'Keys',
    'perkusja': 'Drums',
    'skrzypce': 'Violin',
    'inny': 'Other',
}
PL.update({
    'Vocals': 'Wokal',
    'Guitar': 'Gitara',
    'Electric guitar': 'Gitara elektryczna',
    'Bass': 'Bas',
    'Keys': 'Klawisze',
    'Drums': 'Perkusja',
    'Violin': 'Skrzypce',
    'Other': 'Inny',
})


def instrument_label(value):
    """Przetłumaczona etykieta instrumentu dla podanej (polskiej) wartości."""
    v = (value or '').strip()
    if not v:
        return ''
    return translate(INSTRUMENT_LABELS.get(v, v))


# ── Role (wartości w bazie po polsku) ─────────────────────────────────────
ROLE_LABELS = {'muzyk': 'Musician', 'prowadzacy': 'Leader', 'admin': 'Admin'}
PL.update({'Musician': 'Muzyk', 'Leader': 'Prowadzący', 'Admin': 'Admin'})


# ── Daty po ludzku (bez strftime('%-d'), które nie działa na Windows) ──
_PL_DAYS = ('poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela')
_PL_MONTHS = ('stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca', 'lipca',
              'sierpnia', 'września', 'października', 'listopada', 'grudnia')
_EN_DAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
_EN_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
              'August', 'September', 'October', 'November', 'December')


def nice_date(d, part='full'):
    """'full' -> „niedziela, 20 października" / „Sunday, October 20";
    'weekday' -> „niedziela"; 'daymonth' -> „20 października"."""
    if not d:
        return ''
    pl = get_lang() == 'pl'
    day = (_PL_DAYS if pl else _EN_DAYS)[d.weekday()]
    month = (_PL_MONTHS if pl else _EN_MONTHS)[d.month - 1]
    dm = f'{d.day} {month}' if pl else f'{month} {d.day}'
    if part == 'weekday':
        return day
    if part == 'daymonth':
        return dm
    return f'{day}, {dm}'


def role_label(value):
    v = (value or '').strip()
    return translate(ROLE_LABELS.get(v, v)) if v else ''


# ── Studio: napisy dotąd zaszyte po polsku (teraz EN domyślnie, PL fallback) ──
PL.update({
    'Back to panel': 'Wróć do panelu',
    'Fullscreen': 'Pełny ekran',
    'Collapse / expand library': 'Zwiń / rozwiń bibliotekę',
    'Collapse library': 'Zwiń bibliotekę',
    'Restore defaults?': 'Przywrócić domyślne?',
    'Connect screens': 'Połącz ekrany',
    'Manage connected screens (names, disconnecting)':
        'Zarządzaj podłączonymi ekranami (nazwy, odłączanie)',
    "Band's preferred keys": 'Preferowane tonacje zespołu',
    'Original key:': 'Oryginalna tonacja:',
    'Set the transpose for whoever leads the vocal.':
        'Ustaw transpozycję pod osobę prowadzącą wokal.',
    'No one on the team has saved their key for this song yet '
    '(they do it in the practice view: the −1 / +1 “my key” buttons).':
        'Nikt z zespołu nie zapisał jeszcze swojej tonacji dla tej piosenki '
        '(robi się to w widoku ćwiczenia: przyciski −1 / +1 „moja tonacja”).',
    "Click: the band's preferred keys for this song":
        'Kliknij: preferowane tonacje zespołu dla tej piosenki',
    # Ekran startowy (brak wspólnoty) + przełącznik wspólnot
    'Get started': 'Zacznij',
    'Welcome to Jonathan': 'Witaj w Jonathan',
    "You're not in any community yet. Start your own team, or join one you were invited to.":
        'Nie należysz jeszcze do żadnej wspólnoty. Załóż własny zespół albo dołącz do tego, do którego masz zaproszenie.',
    'Create a community': 'Załóż wspólnotę',
    "A space for your team — songs, setlists, service planning and musician profiles. You'll be its admin.":
        'Przestrzeń dla Twojego zespołu — pieśni, setlisty, planowanie grań i profile muzyków. Będziesz jej administratorem.',
    'Create community': 'Utwórz wspólnotę',
    'Join an existing team': 'Dołącz do istniejącego zespołu',
    'Ask your worship leader for the invite code (they find it in the Team tab), then enter it here.':
        'Poproś prowadzącego o kod zaproszenia (znajdzie go w zakładce Zespół) i wpisz go tutaj.',
    'e.g. 7KQ2AB': 'np. 7KQ2AB',
    'Join': 'Dołącz',
    'Switch community': 'Zmień wspólnotę',
    'New / join community': 'Nowa / dołącz do wspólnoty',
})


# ── Formularz piosenki: trwała ściąga formatu + walidacja na żywo ──
PL.update({
    'How to format a song': 'Jak zapisać piosenkę',
    'Put chords in square brackets, right before the word:':
        'Akordy wpisuj w nawiasach kwadratowych, tuż przed słowem:',
    'Start each section with a label on its own line — Intro, Verse, Chorus, Bridge… (any language).':
        'Każdą sekcję zaczynaj od etykiety w osobnej linii — Intro, Zwrotka, '
        'Refren, Bridge… (w dowolnym języku).',
    'Separate sections with one blank line.':
        'Sekcje oddzielaj jedną pustą linią.',
    'A section can be chords only, with no lyrics — perfect for an intro or '
    'instrumental. Just write a line of chords.':
        'Sekcja może zawierać same akordy, bez tekstu — idealne na intro albo '
        'przejście instrumentalne. Wpisz po prostu linię z akordami.',
    'Example': 'Przykład',
    'The Intro above has chords only — no lyrics. Any section can be like that.':
        'Intro powyżej ma same akordy — bez tekstu. Każda sekcja może tak wyglądać.',
    # Etykiety pól / statusy na żywo (klient czyta z SONG_EDITOR_I18N)
    'chords': 'akordów',
    'sections': 'sekcji',
    'all recognized': 'wszystkie rozpoznane',
    'not recognized': 'nierozpoznane',
    'Unclosed bracket “[” — every chord needs a closing “]”.':
        'Niezamknięty nawias „[” — każdy akord potrzebuje domykającego „]”.',
    'No chords yet — put them in [brackets], e.g. [Am].':
        'Jeszcze brak akordów — wpisuj je w [nawiasach], np. [Am].',
    'Converted — check the result': 'Przekonwertowano — sprawdź wynik',
    'No chords-above-lyrics detected': 'Nie wykryto akordów nad tekstem',
})


# ── Branding / szablony: jedno miejsce na zasoby wizualne ──
PL.update({
    'Templates & branding': 'Szablony i branding',
    'One place for everything shown on the projector — logo, background, the '
    'transition between screens, watermark icons and the welcome-screen photos.':
        'Jedno miejsce na wszystko, co widać na rzutniku — logo, tło, przejście '
        'między ekranami, ikony znaku wodnego i zdjęcia ekranu oczekiwania.',
    'Logo, projector background, the transition between screens, watermark '
    'icons and welcome-screen photos — all in one place.':
        'Logo, tło rzutnika, przejście między ekranami, ikony znaku wodnego i '
        'zdjęcia ekranu oczekiwania — wszystko w jednym miejscu.',
    'Logo': 'Logo',
    'Shows on the projector when nothing else is displayed. PNG/JPG, up to 8 MB.':
        'Pokazuje się na rzutniku, gdy nic innego nie jest wyświetlane. '
        'PNG/JPG, do 8 MB.',
    'Projector background': 'Tło rzutnika',
    'Optional image behind the lyrics. PNG/JPG, up to 8 MB.':
        'Opcjonalny obraz za tekstem. PNG/JPG, do 8 MB.',
    'Transition between screens': 'Przejście między ekranami',
    'A short MP4/WebM video or an HTML animation that plays whenever you switch '
    'between Announcements, Worship and Conference. Up to 60 MB. Tip: for a '
    'smooth clip, upload an MP4 — it plays full-screen with no player controls.':
        'Krótki film MP4/WebM albo animacja HTML odtwarzana przy przełączaniu '
        'między Ogłoszeniami, Uwielbieniem i Konferencją. Do 60 MB. Wskazówka: '
        'dla płynnego klipu wgraj MP4 — gra na pełnym ekranie, bez pasków '
        'odtwarzacza.',
    'Preview': 'Podgląd',
    'Background icons (watermark)': 'Ikony w tle (znak wodny)',
    'Faint symbols behind the welcome screen. Any image works — a white '
    'background disappears automatically.':
        'Delikatne symbole za ekranem oczekiwania. Każdy obraz zadziała — białe '
        'tło znika automatycznie.',
    'Welcome-screen photos': 'Zdjęcia ekranu oczekiwania',
    'Shared photo pool for the announcements/welcome screen. Pick which one '
    'each slide uses in the welcome editor.':
        'Wspólna pula zdjęć dla ekranu ogłoszeń/oczekiwania. Który slajd używa '
        'którego, wybierzesz w edytorze ekranu oczekiwania.',
    'Projection colors & font': 'Kolory i czcionka projekcji',
    'Close': 'Zamknij',
})


# ── Przejście (stinger) między trybami ekranu ──
PL.update({
    'Transition between screens (optional)':
        'Przejście między ekranami (opcjonalnie)',
    'A short MP4/WebM video or an HTML animation that plays whenever you '
    'switch between Announcements, Worship and Conference. Up to 60 MB.':
        'Krótki film MP4/WebM albo animacja HTML odtwarzana przy każdym '
        'przełączeniu między Ogłoszeniami, Uwielbieniem i Konferencją. '
        'Do 60 MB.',
    'Choose transition file': 'Wybierz plik przejścia',
    'Remove transition': 'Usuń przejście',
    'HTML transition length (seconds)': 'Długość przejścia HTML (sekundy)',
    'Save length': 'Zapisz długość',
    'Upload an MP4/WebM video or an HTML file up to 60 MB.':
        'Wgraj film MP4/WebM albo plik HTML do 60 MB.',
})


# ── Nowy wygląd panelu: menu boczne, pulpit, ćwiczenie ─────────────────
PL.update({
    'Start': 'Start', 'Menu': 'Menu', 'Leading': 'Prowadzenie',
    'Hello, %(name)s.': 'Dzień dobry, %(name)s.',
    'On %(day)s you play %(parts)s.': '%(day)s grasz: %(parts)s.',
    '%(n)s of %(t)s songs still to practise.':
        'Zostało %(n)s z %(t)s piosenek do przećwiczenia.',
    'Every song is practised — nice.': 'Wszystkie piosenki przećwiczone — dobra robota.',
    'Next up: %(name)s, %(day)s.': 'Najbliżej: %(name)s, %(day)s.',
    'Discover what you can do': 'Zobacz, co potrafi Jonathan',
    'Nothing planned': 'Nic zaplanowanego',
    'No setlist attached yet.': 'Setlista nie jest jeszcze podpięta.',
    'All services': 'Wszystkie granie',
    'practised': 'przećwiczone', 'to practise': 'do przećwiczenia',
    'nothing is playing': 'nic nie jest grane',
    'a session is running': 'trwa sesja',
    'Preparation': 'Przygotowanie', 'Line-up': 'Skład',
    'Open the song library': 'Otwórz bibliotekę piosenek',
    'recently practised': 'ostatnio ćwiczone',
    'Tempo': 'Tempo', 'you': 'ty', 'Loop': 'Pętla',
    'Listen': 'Posłuchaj', 'Listen to the idea': 'Posłuchaj pomysłu',
    'recording from': 'nagranie z',
    'Not running': 'Wyłączone', 'Running': 'Trwa', 'Practising': 'Ćwiczenie',
    # pasek formy w ćwiczeniu
    'Press play or tap a part': 'Naciśnij start albo kliknij część',
    'You hear the whole band with your part louder — to learn it.':
        'Słyszysz cały zespół, a swoją partię głośniej — do nauki.',
    'Your part is muted — you play it yourself with the band.':
        'Twojej partii nie ma w nagraniu — grasz ją sam z zespołem.',
    'The rehearsal recording as it sounded.': 'Nagranie z próby tak, jak brzmiało.',
    'Slower without changing the key': 'Wolniej, bez zmiany tonacji',
    'Pick what you play above — you get the Learn and Play along modes.':
        'Wybierz wyżej, na czym grasz — dostaniesz tryby Nauka i Gram sam.',
    'The recording has no separate track for %(role)s — you hear the full mix.':
        'W nagraniu nie ma osobnego śladu dla: %(role)s — słyszysz cały miks.',
    'No rehearsal recording for this version yet — tap a part to jump to it.':
        'Ta wersja nie ma jeszcze nagrania z próby — kliknij część, żeby do niej przejść.',
    'Space': 'Spacja', 'play': 'start/stop', 'loop': 'pętla',
    # praca kilku osób naraz, wybór z listy
    'No dynamics': 'Bez dynamiki',
    'Someone else changed the form in the meantime — you now see their version. Make your change again.':
        'Ktoś inny zmienił w międzyczasie formę — widzisz teraz jego wersję. Wprowadź swoją zmianę jeszcze raz.',
    'Updated — latest change by': 'Zaktualizowano — ostatnia zmiana:',
    'This idea was recorded by %(name)s. Record over it?': 'Ten pomysł nagrał(a) %(name)s. Nagrać na nim swój?',
    'choose your part': 'wybierz partię', 'in the recording': 'jest w nagraniu',
    'with recording': 'z nagraniem',
    # Reaper: dwa skrypty
    'Download the send script': 'Pobierz skrypt wysyłki',
    'Download the settings script': 'Pobierz skrypt ustawień',
    'Add both scripts to Reaper': 'Dodaj oba skrypty do Reapera',
    'Actions → Show action list → New action → Load ReaScript… and pick each downloaded file. You get two actions: “Jonathan - send rehearsal” (sends) and “Jonathan - settings” (server address and token). Tip: give the send action a toolbar button.':
        'Actions → Show action list → New action → Load ReaScript… i wybierz po kolei oba pobrane pliki. Dostaniesz dwie akcje: „Jonathan - send rehearsal” (wysyłka) i „Jonathan - settings” (adres serwera i token). Wskazówka: akcji wysyłki daj przycisk na pasku narzędzi.',
    'Run “Jonathan - settings”, enter the server address shown below and the token — it checks the connection right away. To change them later (new token, another server), run it again.':
        'Uruchom „Jonathan - settings”, wpisz adres serwera podany niżej i token — od razu sprawdzi połączenie. Żeby je później zmienić (nowy token, inny serwer), uruchom go ponownie.',
})


# ── Aranżacje: forma, obsada, partie, nagrania z prób (Reaper) ──────────
PL.update({
    'Arrangement': 'Aranżacja', 'Main': 'Główna', 'New version': 'Nowa wersja',
    'Version': 'Wersja', 'Version name': 'Nazwa wersji',
    'Version options': 'Opcje wersji', 'Rename': 'Zmień nazwę',
    'Delete version': 'Usuń wersję', 'Version deleted.': 'Wersja usunięta.',
    'Delete this version with its notes and recordings?':
        'Usunąć tę wersję razem z notatkami i nagraniami?',
    'A version with this name already exists.':
        'Wersja o tej nazwie już istnieje.',
    'e.g. Acoustic, Easter': 'np. Akustyczna, Wielkanoc',
    'Starts as a copy of the form and cast of':
        'Zaczyna jako kopia formy i obsady wersji',
    'Practice this version': 'Ćwicz tę wersję',
    'Last change:': 'Ostatnia zmiana:',
    'Has a rehearsal recording': 'Ma nagranie z próby',
    'Form & parts': 'Forma i partie',
    'Set up the arrangement: form, parts, recordings':
        'Ustaw aranżację: forma, partie, nagrania',
    # forma
    'Form': 'Forma',
    'Drag tiles to set the order. Anyone on the team can edit — earlier versions are in the history.':
        'Przeciągaj kafelki, żeby ustawić kolejność. Edytować może każdy z zespołu — wcześniejsze wersje są w historii.',
    'Add tile': 'Dodaj kafelek', 'From the song': 'Z piosenki',
    'Without lyrics': 'Bez tekstu',
    'e.g. Solo, Interlude, Tag': 'np. Solo, Przerywnik, Tag',
    'The form is empty — add tiles.': 'Forma jest pusta — dodaj kafelki.',
    'Repeats': 'Powtórzenia', 'Dynamics': 'Dynamika',
    'Soft': 'Cicho', 'Build': 'Narasta', 'Full': 'Pełno',
    'Break down': 'Wyciszenie', 'Band only': 'Sam zespół',
    # obsada
    'Cast': 'Obsada',
    'Parts in this version — instruments, not people, so it keeps working when the line-up changes. In Reaper name tracks the same way with “J:” in front, e.g. J:Vocals 2.':
        'Partie w tej wersji — instrumenty, nie osoby, więc wszystko działa przy zmianie składu. W Reaperze nazwij ślady tak samo z „J:” na początku, np. J:Wokal 2.',
    'Another part, e.g. Choir, Cajon': 'Inna partia, np. Chórek, Cajon',
    'Add part': 'Dodaj partię', 'me': 'ja',
    'Remove the part? Its notes stay in the history of cells and come back if you add it again.':
        'Usunąć partię? Jej notatki zostają i wrócą, jeśli dodasz ją ponownie.',
    # partie
    'Parts': 'Partie',
    'Tap a cell to write what this part does there or record the idea on your phone — the whole team sees and hears it.':
        'Kliknij komórkę, żeby wpisać, co ta partia tam robi, albo nagraj pomysł telefonem — cały zespół to zobaczy i usłyszy.',
    'Add parts in the cast above — then each part gets its row here.':
        'Dodaj partie w obsadzie powyżej — każda dostanie tu swój wiersz.',
    'e.g. third above the melody from the 2nd chorus · riff e|--3--5--7--|':
        'np. tercja nad melodią od 2. refrenu · riff e|--3--5--7--|',
    'Tab font': 'Czcionka do tabów', 'could not save': 'nie zapisano',
    'Idea recording': 'Nagranie pomysłu', 'Record': 'Nagraj',
    'Record an idea': 'Nagraj pomysł',
    'Record again (replaces)': 'Nagraj ponownie (zastępuje)',
    'Sing the harmony, play the riff — up to a few minutes.':
        'Zaśpiewaj głos, zagraj riff — do kilku minut.',
    'Stop and save': 'Zatrzymaj i zapisz', 'Recording…': 'Nagrywanie…',
    'Sending…': 'Wysyłanie…', 'Recorded by': 'Nagrał(a)',
    'Delete recording': 'Usuń nagranie',
    'Delete this recording?': 'Usunąć to nagranie?',
    'The browser has no microphone access. Allow it in the site settings.':
        'Przeglądarka nie ma dostępu do mikrofonu. Zezwól na niego w ustawieniach strony.',
    'This is not an audio file, or it is too big (max 8 MB).':
        'To nie jest plik audio albo jest za duży (maks. 8 MB).',
    # historia
    'History': 'Historia', 'Restore': 'Przywróć', 'before:': 'przed:',
    'tiles': 'kafelków', 'parts': 'partii',
    'changed the form': 'zmienił(a) formę',
    'changed the cast': 'zmienił(a) obsadę',
    'restored a version': 'przywrócił(a) wersję',
    'form from the recording': 'forma z nagrania',
    'Restore the form and cast from before this change?':
        'Przywrócić formę i obsadę sprzed tej zmiany?',
    'Restored the earlier version of the form and cast.':
        'Przywrócono wcześniejszą formę i obsadę.',
    # nagranie z próby
    'Rehearsal recording': 'Nagranie z próby',
    'Sent from Reaper': 'Wysłane z Reapera',
    'A new send replaces it.': 'Kolejne wysłanie je zastąpi.',
    'No recording yet': 'Jeszcze bez nagrania',
    'In Reaper name the region after the song (and “| version”), markers after the tiles and tracks “J:part” — the script sends the mix and every part.':
        'W Reaperze nazwij region jak piosenkę (i „| wersja”), markery jak kafelki, a ślady „J:partia” — skrypt wyśle miks i każdą partię.',
    'Connect Reaper': 'Połącz Reapera',
    # ćwiczenie
    'I play': 'Gram', 'choose': 'wybierz', 'Other parts': 'Pozostałe partie',
    'Play from here': 'Odtwórz od tego miejsca',
    'Loop this part': 'Zapętl ten fragment', 'Play': 'Odtwórz',
    'Learn': 'Nauka', 'Play along': 'Gram sam', 'Mix': 'Miks',
    'Speed': 'Tempo',
    'The full mix with your part louder — to learn it':
        'Cały miks z Twoją partią głośniej — do nauki',
    'The mix without your part — you play it':
        'Miks bez Twojej partii — Ty ją grasz',
    # profil
    'What do you play?': 'Na czym grasz?',
    'Something else? e.g. Cajon, Ukulele (comma-separated)':
        'Coś innego? np. Cajon, Ukulele (po przecinku)',
    'Pick everything you play — arrangements suggest these instruments as parts.':
        'Zaznacz wszystko, na czym grasz — aranżacje podpowiedzą te instrumenty jako partie.',
    # Reaper (admin)
    'Rehearsal recordings (Reaper)': 'Nagrania z prób (Reaper)',
    'Connect the computer with Reaper — one click sends the rehearsal mix and each part to the arrangements.':
        'Połącz komputer z Reaperem — jedno kliknięcie wysyła miks z próby i każdą partię do aranżacji.',
    'After rehearsal one click in Reaper sends the mix and every part to the arrangements. Each musician then practises with “mix + me louder” or “mix without me”. Only your community can listen.':
        'Po próbie jedno kliknięcie w Reaperze wysyła miks i każdą partię do aranżacji. Każdy muzyk ćwiczy potem z „miks + ja głośniej” albo „miks beze mnie”. Słuchać może tylko Wasza wspólnota.',
    'Studio computer': 'Komputer w studiu',
    'Connected': 'Połączony', 'Not connected': 'Niepołączony',
    'token created': 'token utworzony', 'last send': 'ostatnie wysłanie',
    'Only one computer can send recordings — the one that has the token. A new token disconnects the old one.':
        'Nagrania może wysyłać tylko jeden komputer — ten, który ma token. Nowy token odłącza stary.',
    'Copy the token now — it will not be shown again.':
        'Skopiuj token teraz — nie zostanie pokazany ponownie.',
    'Copy': 'Kopiuj', 'Copied': 'Skopiowano',
    'Server address:': 'Adres serwera:',
    'Connect a computer': 'Połącz komputer',
    'Generate a new token': 'Wygeneruj nowy token',
    'Generate a new token? The computer using the old one will be disconnected.':
        'Wygenerować nowy token? Komputer ze starym tokenem zostanie odłączony.',
    'Disconnect the studio computer?': 'Odłączyć komputer w studiu?',
    'Studio token revoked — Reaper can no longer send recordings.':
        'Token studia unieważniony — Reaper nie może już wysyłać nagrań.',
    'Download the Reaper script': 'Pobierz skrypt do Reapera',
    'Setup — once': 'Konfiguracja — raz',
    'Add the script to Reaper': 'Dodaj skrypt do Reapera',
    'Actions → Show action list → New action → Load ReaScript… and pick the downloaded file. Tip: give it a toolbar button.':
        'Actions → Show action list → New action → Load ReaScript… i wybierz pobrany plik. Wskazówka: dodaj mu przycisk na pasku narzędzi.',
    'Set the render format': 'Ustaw format renderu',
    'File → Render…: format MP3, 128–192 kbps (mono is fine for parts). Close the window — the script uses these settings and does the rest.':
        'File → Render…: format MP3, 128–192 kb/s (do partii wystarczy mono). Zamknij okno — skrypt użyje tych ustawień i zrobi resztę.',
    'Paste the token': 'Wklej token',
    'On the first run the script asks for the server address and the token, and remembers them.':
        'Przy pierwszym uruchomieniu skrypt zapyta o adres serwera i token i je zapamięta.',
    'After each rehearsal — naming': 'Po każdej próbie — nazewnictwo',
    'In Reaper': 'W Reaperze', 'Name it': 'Nazwa', 'Example': 'Przykład',
    'Region = song': 'Region = piosenka',
    'song title, optionally “| version”': 'tytuł piosenki, opcjonalnie „| wersja”',
    'Markers in the region = tiles': 'Markery w regionie = kafelki',
    'tile names in order': 'nazwy kafelków po kolei',
    'Tracks to send = parts': 'Ślady do wysłania = partie',
    '“J:” + part name from the cast': '„J:” + nazwa partii z obsady',
    'Tracks without “J:” (room mics, click) are skipped. Short names work too: V = Verse, C/R = Chorus, B = Bridge. Before sending the script shows what matched — a missing version or part is created, and if the markers differ from the tiles the form follows the recording (the old one stays in the history).':
        'Ślady bez „J:” (ambient, klik) są pomijane. Działają też skróty: Z = Zwrotka, R = Refren, B = Bridge. Przed wysłaniem skrypt pokazuje, co się dopasowało — brakująca wersja lub partia zostanie utworzona, a jeśli markery różnią się od kafelków, forma pójdzie za nagraniem (stara zostaje w historii).',
})

# ── Edytor piosenki: walidacja z numerami linii, podgląd, notacja ─────────
PL.update({
    'The song was not saved:': 'Piosenka nie została zapisana:',
    'Line %(line)s: bracket “[” is never closed — add “]” after the chord.':
        'Linia %(line)s: nawias „[” nie jest zamknięty — dopisz „]” po akordzie.',
    'The key “%(key)s” is not a chord — use e.g. G, Em, F#, Bb.':
        'Tonacja „%(key)s” to nie akord — wpisz np. G, Em, F#, Bb.',
    'Chords written above the lyrics were moved into the text — check the result.':
        'Akordy zapisane nad tekstem zostały przeniesione do tekstu — sprawdź wynik.',
    'Section names in brackets, like [Chorus], are now plain labels.':
        'Nazwy części w nawiasach, np. [Refren], zamieniono na zwykłe nazwy.',
    'auto': 'auto', 'Chords are written in': 'Akordy zapisane w notacji',
    'International (B = H, Bb)': 'Międzynarodowej (B = H, Bb)',
    'Polish (H, B, Fis)': 'Polskiej (H, B, Fis)',
    'Switch to Polish': 'Przełącz na polską', 'Convert now': 'Przenieś teraz',
    'Preview': 'Podgląd', 'How to write a song': 'Jak zapisać piosenkę',
    'Start typing — here you see the song exactly as the band will see it.':
        'Zacznij pisać — tutaj widzisz piosenkę dokładnie tak, jak zobaczy ją zespół.',
    'Copied a song with chords above the lyrics? Paste it as is — it gets converted when you save.':
        'Kopiujesz piosenkę z akordami nad tekstem? Wklej ją tak, jak jest — przy zapisie sama się przerobi.',
    'all chords recognized': 'wszystkie akordy rozpoznane',
    'Line': 'Linia',
    'bracket “[” is never closed — add “]” after the chord':
        'nawias „[” nie jest zamknięty — dopisz „]” po akordzie',
    'a “]” without “[” — it will show as text': 'samo „]” bez „[” — pokaże się jako tekst',
    'double brackets [[ ]] — fixed when you save': 'podwójny nawias [[ ]] — poprawi się przy zapisie',
    'section name in brackets — becomes a plain label when you save':
        'nazwa części w nawiasie — przy zapisie stanie się zwykłą nazwą',
    'not a chord we know': 'nierozpoznany akord',
    'detected key': 'wykryta tonacja',
    'These chords look like Polish notation (%(ex)s).':
        'Te akordy wyglądają na polską notację (%(ex)s).',
    'Careful: in Polish “B” means B♭, internationally it means H.':
        'Uwaga: po polsku „B” to B♭, a w notacji międzynarodowej to H.',
    'Lines %(lines)s have chords above the lyrics — they will be moved into the text when you save (the preview already shows it).':
        'Linie %(lines)s mają akordy nad tekstem — przy zapisie trafią do tekstu (podgląd już to pokazuje).',
    'Is this a section name? If it is a lyric, add a section name above it (e.g. Verse).':
        'To nazwa części? Jeśli to tekst piosenki, dopisz nad nim nazwę części (np. Zwrotka).',
    'no name': 'bez nazwy',
})

# ── UX etap 1: piosenka, nabożeństwa, ustawienia ─────────────────────────
PL.update({
    'Half a step down': 'Pół tonu niżej',
    'Half a step up': 'Pół tonu wyżej',
    'original': 'oryginał',
    'Back to original': 'Wróć do oryginału',
    'Delete song': 'Usuń piosenkę',
    'The song disappears from the library for the whole team.': 'Piosenka zniknie z biblioteki dla całego zespołu.',
    'e.g. Sunday morning': 'np. Niedziela rano',
    'Time': 'Godzina',
    '(optional)': '(opcjonalnie)',
    'Reply by': 'Odpowiedź do',
    'Until when the team should mark availability': 'Do kiedy zespół ma zaznaczyć, czy może grać',
    'Create service': 'Utwórz granie',
    'Upcoming': 'Najbliższe',
    'Fill in the form above — the team gets a place to mark availability.': 'Wypełnij formularz powyżej — zespół dostanie miejsce, żeby zaznaczyć, czy może grać.',
    'No songs yet. Arrange them in Studio — after “Save setlist” they appear here.': 'Nie ma jeszcze piosenek. Ułóż je w Studiu — po „Zapisz setlistę” pojawią się tutaj.',
    'The leader hasn’t added songs yet.': 'Prowadzący nie dodał jeszcze piosenek.',
    'Use a setlist saved earlier': 'Użyj setlisty zapisanej wcześniej',
    'Saved setlist': 'Zapisana setlista',
    'Countdown and announcements on the projector before the first song.': 'Odliczanie i ogłoszenia na rzutniku przed pierwszą piosenką.',
    'Add songs to the service first — then you can set up the countdown and announcements.': 'Najpierw dodaj piosenki do grania — potem ustawisz odliczanie i ogłoszenia.',
    'Edit service details': 'Edytuj szczegóły grania',
    'The team’s availability and lineup for this service are removed too.': 'Usunięte zostaną też odpowiedzi zespołu i skład na to granie.',
    'Settings for the whole community. Your own theme, language and tips are in': 'Ustawienia dla całej wspólnoty. Twój motyw, język i podpowiedzi są w zakładce',
})


# ── Wpisywanie piosenek: ChordPro, kapodaster ─────────────────────────────
PL.update({
    'Pasted ChordPro was converted — check the result.':
        'Wklejony ChordPro został przerobiony — sprawdź wynik.',
    'capo is set by each musician in their own view — this line would show as lyrics, delete it':
        'kapodaster ustawia każdy muzyk u siebie — ta linia pokazałaby się jako tekst, usuń ją',
})


# ── Edytor piosenki: kafelki ──────────────────────────────────────────────
PL.update({
    'Tiles': 'Kafelki',
    'Two views of the same song — switch any time.': 'Dwa widoki tej samej piosenki — możesz przełączać w każdej chwili.',
    'Verse': 'Zwrotka',
    'Chorus': 'Refren',
    'Pre-chorus': 'Przedrefren',
    'Interlude': 'Przejście',
    'Ending': 'Zakończenie',
    'Add a part:': 'Dodaj część:',
    'Paste a song from anywhere': 'Wklej piosenkę skądkolwiek',
    'Chords above the lyrics, ChordPro from SongSelect or plain lyrics — it splits into parts by itself and the chords land on the right syllables.': 'Akordy nad tekstem, ChordPro z SongSelect albo sam tekst — sama podzieli się na części, a akordy trafią nad właściwe sylaby.',
    'Paste here (Ctrl+V)…': 'Wklej tutaj (Ctrl+V)…',
    'or': 'albo',
    'Start from an empty verse': 'Zacznij od pustej zwrotki',
    'Part name, e.g. Verse 1': 'Nazwa części, np. Zwrotka 1',
    'Type or paste the lyrics of this part — you add chords afterwards by clicking above the words.': 'Wpisz albo wklej tekst tej części — akordy dodasz potem, klikając nad słowami.',
    'Done — add chords': 'Gotowe — dodaj akordy',
    'Edit lyrics': 'Edytuj tekst',
    'Click above a letter to add a chord, click a chord to change it.': 'Kliknij literę, żeby dodać nad nią akord. Kliknij akord, żeby go zmienić.',
    'Move up': 'Przesuń wyżej',
    'Move down': 'Przesuń niżej',
    'Duplicate (e.g. the chorus again)': 'Powiel (np. refren jeszcze raz)',
    'Delete part': 'Usuń część',
    'Delete the part “%(name)s”?': 'Usunąć część „%(name)s”?',
    'Add a chord at the end of the line': 'Dodaj akord na końcu linii',
    'Chord above': 'Akord nad',
    'Change chord': 'Zmień akord',
    'In the key of %(key)s': 'W tonacji %(key)s',
    'Common chords': 'Popularne akordy',
    'Already in this song': 'Już w tej piosence',
    'Other chord, e.g. Cadd9, D/F#': 'Inny akord, np. Cadd9, D/F#',
    'Insert': 'Wstaw',
    'Change': 'Zmień',
    'That doesn’t look like a chord — e.g. Am, F#m7, D/F#.': 'To nie wygląda na akord — np. Am, F#m7, D/F#.',
    'move by one letter': 'przesuń o literę',
    'One letter left': 'O literę w lewo',
    'One letter right': 'O literę w prawo',
    'Recognised ChordPro — converted.': 'Rozpoznano ChordPro — przerobiono.',
    'Chords were above the lyrics — moved onto the syllables.': 'Akordy były nad tekstem — przeniesiono je nad sylaby.',
    'Part names in brackets became plain names.': 'Nazwy części w nawiasach zamieniono na zwykłe nazwy.',
    'Part names separated by a blank line were joined to their lyrics.': 'Nazwy części oddzielone pustą linią połączono z ich tekstem.',
    'Invisible characters from the web page were removed.': 'Usunięto niewidoczne znaki skopiowane ze strony.',
})


# ── Kafelki: powtórzenia i długość slajdu ─────────────────────────────────
PL.update({
    '(cont.)': '(cd.)',
    'Lines %(from)s–%(to)s: the same %(n)s lines %(times)s times in a row.':
        'Linie %(from)s–%(to)s: te same %(n)s linie %(times)s razy z rzędu.',
    'Lines %(from)s–%(to)s: the same line %(times)s times in a row.':
        'Linie %(from)s–%(to)s: ta sama linia %(times)s razy z rzędu.',
    'Keep once (x%(times)s)': 'Zostaw raz (x%(times)s)',
    '%(n)s lines on one slide — on the projector the text gets small.':
        '%(n)s linii na jednym slajdzie — na rzutniku tekst będzie mały.',
    'Split into %(parts)s slides': 'Podziel na %(parts)s slajdy',
    'Undo': 'Cofnij',
    'Repeated lines are kept once with (x2).': 'Powtórzone linie zostawiono raz z dopiskiem (x2).',
    'Long parts were split into slides of up to 8 lines.': 'Długie części podzielono na slajdy po maks. 8 linii.',
    '%(n)s lines — too much for one slide, split it (max 8)':
        '%(n)s linii — za dużo na jeden slajd, podziel (maks. 8)',
})


# ── Import: tonacja z nagłówka, puste części ──────────────────────────────
PL.update({
    'Key in the title did not match the chords — detected instead:':
        'Tonacja w tytule nie pasowała do akordów — użyto wykrytej:',
    'a part with only a name — it would be an empty slide; add its lyrics or delete the name':
        'część z samą nazwą — byłby pusty slajd; dopisz tekst albo usuń nazwę',
    'Lines were separated by blank lines (copied text) — joined back into parts.':
        'Linie były przedzielone pustymi liniami (skopiowany tekst) — połączono je z powrotem w części.',
    'Unnamed blocks after a part got its name with “(cont.)”.':
        'Bloki bez nazwy po części dostały jej nazwę z „(cd.)”.',
    'Repeat marks like “/2x” were written as “(x2)”.': 'Oznaczenia powtórzeń typu „/2x” zapisano jako „(x2)”.',
})


# ── Forma i partie: oś czasu i riffy ─────────────────────────────────────
PL.update({
    'Timeline': 'Oś czasu',
    'The whole song at a glance — every instrument has its own lane. Tap a cell to add a note, a riff (tab) or record an idea; the whole team sees and hears it.':
        'Cała piosenka w jednym widoku — każdy instrument ma swój tor. Kliknij kratkę, żeby dodać notatkę, riff (tabulaturę) albo nagrać pomysł; cały zespół to zobaczy i usłyszy.',
    'Riff (tab)': 'Riff (tabulatura)',
    'riff': 'riff',
    'Guitar': 'Gitara', 'Bass': 'Bas', 'Play': 'Odtwórz', 'Stop': 'Stop',
    'bar': 'takt', 'Clear': 'Wyczyść',
    'Clear the whole riff?': 'Wyczyścić cały riff?',
    'Delete the last bar with its notes?': 'Usunąć ostatni takt razem z nutami?',
    'Delete a character': 'Usuń znak',
    'Click a box, then type the fret (or use the buttons). h = hammer-on, p = pull-off, / = slide, b = bend, ~ = vibrato, x = muted. Arrows move, Space plays.':
        'Kliknij kratkę i wpisz próg (albo użyj przycisków). h = hammer-on, p = pull-off, / = slajd, b = podciągnięcie, ~ = wibrato, x = stłumiona. Strzałki przesuwają, spacja odtwarza.',
    'hammer-on (5h7)': 'hammer-on (5h7)', 'pull-off (7p5)': 'pull-off (7p5)', 'slide (5/7)': 'slajd (5/7)',
    'bend (7b)': 'podciągnięcie (7b)', 'vibrato': 'wibrato', 'muted': 'stłumiona',
})


# ── Nuty (pięciolinia) i zapis w „Ćwicz" ─────────────────────────────────
PL.update({
    'Riff or melody': 'Riff albo melodia',
    'Tab': 'Tabulatura', 'Notes': 'Nuty', 'notes': 'nuty',
    'Switching deletes what is written here now. Continue?': 'Przełączenie usunie to, co jest tu teraz zapisane. Kontynuować?',
    'C,D,E,F,G,A,B': 'C,D,E,F,G,A,H',
    'Treble clef': 'Wiolinowy', 'Bass clef': 'Basowy',
    'Clear all notes?': 'Wyczyścić wszystkie nuty?', 'Rest': 'Pauza',
    'Dotted (longer by half)': 'Z kropką (dłuższa o połowę)',
    'Delete the selected or last note': 'Usuń zaznaczoną albo ostatnią nutę',
    'Octave up': 'Oktawa wyżej', 'Octave down': 'Oktawa niżej',
    'whole': 'cała nuta', 'half': 'półnuta', 'quarter': 'ćwierćnuta', 'eighth': 'ósemka', 'sixteenth': 'szesnastka',
    'Pick a length, then click the keys — the notes appear here.': 'Wybierz długość i klikaj klawisze — nuty pojawią się tutaj.',
    'Choose the length (¼ = quarter), then click piano keys; ♯ ♭ before the key. Click a note to change or delete it. Keyboard: c d e f g a h, 1–5 length, ↑ ↓ moves the selected note, Space plays.':
        'Wybierz długość (¼ = ćwierćnuta) i klikaj klawisze; ♯ ♭ przed klawiszem. Kliknij nutę, żeby ją zmienić albo usunąć. Klawiatura: c d e f g a h, 1–5 długość, ↑ ↓ przesuwa zaznaczoną nutę, spacja odtwarza.',
    'Show notes': 'Pokaż nuty', 'Show riff': 'Pokaż riff',
})
