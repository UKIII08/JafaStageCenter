# i18n dla panelu (server-side). Model gettext: teksty w szablonach i we
# flash-ach piszemy PO ANGIELSKU (źródło, rynek USA = priorytet), a polski to
# warstwa tłumaczeń z fallbackiem do angielskiego. Studio i ekrany mają własny
# i18n po stronie klienta (static/js/i18n.js) — tego nie dotyczy.
from flask import session

SUPPORTED = ('en', 'pl')
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
    "Your role:": "Twoja rola:", "Open": "Otwórz",

    # ── Panel: zespół ──
    "Instrument": "Instrument", "Invite to the team": "Zaproś do zespołu",
    "Generate link": "Wygeneruj link", "Invite link": "Link zaproszenia",
    "Role:": "Rola:", "musician": "muzyk", "leader": "prowadzący", "admin": "admin",
    "This link joins as": "Ten link dołącza jako",
    "Change role": "Zmień rolę", "owner": "właściciel",

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
    "Delete service": "Usuń granie",
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
    "Search by title or lyrics": "Szukaj po tytule lub tekście",
    "Add your first song in Studio — or import a .txt file exported from the "
    "desktop app.":
        "Dodaj pierwszą pieśń w Studiu — albo zaimportuj plik .txt z eksportu "
        "aplikacji desktop.",
    "Setlists — %(church)s": "Setlisty — %(church)s",
    "Setlists": "Setlisty", "New setlist": "Nowa setlista",
    "Name (e.g. Sunday morning)": "Nazwa (np. Niedziela poranna)",
    "No setlists": "Brak setlist",
    "Setlists are arranged in Studio and attached to a specific service.":
        "Setlisty układasz w Studiu i podpinasz do konkretnego grania.",
    "Songs": "Piosenek", "Transpose": "Transpozycja", "Songs count": "Piosenek",
    "Practice — %(title)s": "Ćwiczenie — %(title)s", "my key": "moja tonacja",
    "Auto-scroll": "Autoprzewijanie", "Metronome": "Metronom", "Stop": "Stop",
    "My note (visible only to you)": "Moja notatka (widoczna tylko dla Ciebie)",
    "saved": "zapisano", "saving…": "zapisywanie…",

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

    # ── Flash: events ──
    "Enter a service date.": "Podaj datę grania.",
    "Service deleted.": "Usunięto granie.",

    # ── Flash: songs ──
    "Song saved.": "Zapisano piosenkę.",
    "Setlist created.": "Utworzono setlistę.",
    "Setlist deleted.": "Usunięto setlistę.",

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
