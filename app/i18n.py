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
    "Your next service:": "Twoja najbliższa służba:",
    "Prepare! →": "Przygotuj się! →",
    "No upcoming service": "Brak nadchodzącej służby",
    "When a service is scheduled, it shows up here with everything you need to "
    "prepare.":
        "Gdy zaplanujecie służbę, pojawi się tu razem ze wszystkim, czego "
        "potrzebujesz do przygotowania.",
    "Plan a service →": "Zaplanuj służbę →",
    "See services →": "Zobacz służby →",
    "Back to practice": "Wróć do ćwiczenia",
    "Open the song library and rehearse with chords and diagrams.":
        "Otwórz bibliotekę piosenek i ćwicz z akordami i diagramami.",
    "Practice now →": "Ćwicz teraz →",
    "Build the setlist and run the whole service live.":
        "Ułóż setlistę i poprowadź całą służbę na żywo.",
    "Open Studio →": "Otwórz Studio →",
    "Live view": "Widok na żywo",
    "Follow lyrics and chords sent live during the service.":
        "Śledź tekst i akordy wysyłane na żywo podczas służby.",
    "Go live →": "Wejdź na żywo →",
    "See who plays and invite new members.":
        "Zobacz, kto gra, i zaproś nowe osoby.",
    "View team →": "Zobacz zespół →",
    "My profile": "Mój profil",
    "Set your instrument and playing preferences.":
        "Ustaw swój instrument i preferencje grania.",
    "Edit profile →": "Edytuj profil →",
    # Dashboard „Precision" (bento) — nowe etykiety
    "Next service": "Najbliższa służba",
    "more songs": "więcej pieśni", "Prepare": "Przygotuj się",
    "Offline": "Offline",
    "Plan a service": "Zaplanuj służbę", "See services": "Zobacz służby",
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
    "Songs": "Piosenek", "Transpose": "Transpozycja", "Songs count": "Piosenek",
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
