var socket = io();

// --- I18N (TRANSLATION SYSTEM) ---
const translations = {
    pl: {
        worship_mode: "UWIELBIENIE",
        conf_mode: "KONFERENCJA",
        settings_btn: "⚙️ USTAWIENIA",
        connect_btn: "📱 POŁĄCZ EKRANY",
        library_header: "Biblioteka",
        add_manual: "📝 Dodaj ręcznie",
        import_file: "📂 Importuj z pliku",
        search_ph: "Szukaj piosenki...",
        setlist_header: "Setlista",
        empty_setlist: "Brak piosenek w setliście.",
        download_pdf: "POBIERZ PDF",
        live_panel: "Panel Live",
        next_btn: "NASTĘPNA ➔",
        screen_off: "EKRAN WYGASZONY",
        mob_lib: "Biblioteka",
        mob_set: "Setlista",
        speaker_panel: "Panel Mówcy / Konferencja",
        time_label: "Czas (min):",
        set_btn: "USTAW",
        msg_ph: "Wiadomość do mówcy...",
        send_btn: "WYŚLIJ",
        clear_btn: "WYCZYŚĆ",
        import_header: "Import Piosenek (.txt)",
        opt1: "OPCJA 1: Pojedyncze pliki",
        opt1_desc: "Wgraj pliki np. Barka (C).txt.",
        opt2: "OPCJA 2: Plik zbiorczy",
        opt2_desc: "Oddzielaj ---.",
        choose_file: "📂 WYBIERZ PLIK",
        add_header: "Dodaj Nową Piosenkę",
        title_ph: "Tytuł",
        paste_ph: "Wklej tekst tutaj...",
        save_db_btn: "ZAPISZ DO BAZY",
        edit_header: "Edycja",
        delete_btn: "USUŃ",
        save_btn: "ZAPISZ",
        settings_header: "Ustawienia",
        general_settings: "Ogólne",
        appearance: "Wygląd",
        dark_mode: "Tryb ciemny:",
        smart_features: "Inteligentne funkcje",
        auto_trans: "Automatyczne przejścia:",
        key_suggest: "Sugerowanie tonacji:",
        trans_engine: "Styl przejść (Silnik AI):",
        projector_screen: "Rzutnik (Ekran Zewnętrzny)",
        font_label: "Czcionka:",
        bg_color: "Tło",
        text_color: "Tekst",
        chord_color: "Akordy",
        save_settings: "ZAPISZ USTAWIENIA",
        media_header: "Multimedia",
        bg_proj_label: "Tło Rzutnika:",
        choose_file_label: "Wybierz plik...",
        upload_btn: "WGRAJ",
        delete_current: "USUŃ OBECNE",
        backup_btn: "💾 KOPIA BAZY",
        control_qr: "STEROWANIE",
        band_qr: "ZESPÓŁ",
        proj_qr: "RZUTNIK",
        open_win: "OTWÓRZ OKNO ↗",
        ios_install: "Zainstaluj jako aplikację",
        ios_desc: "Aby uruchomić na pełnym ekranie, kliknij przycisk <span class=\"icon-share\"></span> i wybierz <strong>\"Do ekranu początkowego\"</strong>.",
        add_btn_small: "DODAJ",
        
        // --- NOWE: TRYB KONFERENCJI ---
        clock_msg_title: "ZEGAR & WIADOMOŚĆ",
        multimedia_pres_title: "MULTIMEDIA (EKRAN & PREZENTER)",
        canva_title: "1. CANVA (Zapisane prezentacje)",
        canva_link_ph: "Wklej link Canva...",
        add_link_btn: "+ DODAJ",
        no_canva_msg: "Brak dodanych prezentacji.",
        presentation_label: "Prezentacja",
        show_btn: "🖥️ POKAŻ",
        pdf_title: "2. PLIK PREZENTACJI (PDF / PPTX)",
        pdf_ph: "Wybierz plik PDF lub PPTX...",
        slides_control_title: "Sterowanie Slajdami",
        show_pres_btn: "🖥️ POKAŻ PREZENTACJĘ NA EKRANACH",
        blackout_on_btn: "WYGAŚ EKRAN RZUTNIKA",
        blackout_off_btn: "ZDEJMIJ BLACKOUT (POKAŻ EKRAN)",
        open_presenter_btn: "📱 OTWÓRZ WIDOK PREZENTERA (W NOWEJ KARCIE) ↗"
    },
    en: {
        worship_mode: "🎸 WORSHIP",
        conf_mode: "🎤 CONFERENCE",
        settings_btn: "⚙️ SETTINGS",
        connect_btn: "📱 CONNECT SCREENS",
        library_header: "Library",
        add_manual: "📝 Add Manually",
        import_file: "📂 Import from File",
        search_ph: "Search song...",
        setlist_header: "Setlist",
        empty_setlist: "No songs in setlist.",
        download_pdf: "DOWNLOAD PDF",
        live_panel: "Live Panel",
        next_btn: "NEXT ➔",
        screen_off: "SCREEN BLACKED OUT",
        mob_lib: "Library",
        mob_set: "Setlist",
        speaker_panel: "Speaker Panel / Conference",
        time_label: "Time (min):",
        set_btn: "SET",
        msg_ph: "Message to speaker...",
        send_btn: "SEND",
        clear_btn: "CLEAR",
        import_header: "Import Songs (.txt)",
        opt1: "OPTION 1: Single Files",
        opt1_desc: "Upload files e.g. Amazing Grace (C).txt.",
        opt2: "OPTION 2: Batch File",
        opt2_desc: "Separate with ---.",
        choose_file: "📂 CHOOSE FILE",
        add_header: "Add New Song",
        title_ph: "Title",
        paste_ph: "Paste lyrics here...",
        save_db_btn: "SAVE TO DB",
        edit_header: "Edit Song",
        delete_btn: "DELETE",
        save_btn: "SAVE",
        settings_header: "Settings",
        general_settings: "General",
        appearance: "Appearance",
        dark_mode: "Dark Mode:",
        smart_features: "Smart Features",
        auto_trans: "Auto Transitions:",
        key_suggest: "Key Suggestion:",
        trans_engine: "Transition Style (AI Engine):",
        projector_screen: "Projector (External Screen)",
        font_label: "Font:",
        bg_color: "Background",
        text_color: "Text",
        chord_color: "Chords",
        save_settings: "SAVE SETTINGS",
        media_header: "Multimedia",
        bg_proj_label: "Projector Background:",
        choose_file_label: "Choose file...",
        upload_btn: "UPLOAD",
        delete_current: "DELETE CURRENT",
        backup_btn: "💾 DB BACKUP",
        control_qr: "CONTROL",
        band_qr: "STAGE BAND",
        proj_qr: "PROJECTOR",
        open_win: "OPEN WINDOW ↗",
        ios_install: "Install as App",
        ios_desc: "To launch in full screen, tap the <span class=\"icon-share\"></span> button and select <strong>\"Add to Home Screen\"</strong>.",
        add_btn_small: "ADD",
        
        // --- NEW: CONFERENCE MODE ---
        clock_msg_title: "CLOCK & MESSAGE",
        multimedia_pres_title: "MULTIMEDIA (SCREEN & PRESENTER)",
        canva_title: "1. CANVA (Saved presentations)",
        canva_link_ph: "Paste Canva link...",
        add_link_btn: "+ ADD",
        no_canva_msg: "No presentations added.",
        presentation_label: "Presentation",
        show_btn: "🖥️ SHOW",
        pdf_title: "2. PRESENTATION FILE (PDF / PPTX)",
        pdf_ph: "Choose PDF or PPTX file...",
        slides_control_title: "Slide Controls",
        show_pres_btn: "🖥️ SHOW PRESENTATION ON SCREENS",
        blackout_on_btn: "BLACKOUT PROJECTOR SCREEN",
        blackout_off_btn: "REMOVE BLACKOUT (SHOW SCREEN)",
        open_presenter_btn: "📱 OPEN PRESENTER VIEW (NEW TAB) ↗"
    }
};

let currentLang = 'pl';
function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('appLang', lang);
    document.documentElement.setAttribute('data-lang', lang);
    const langSelect = document.getElementById('lang-select');
    if (langSelect) langSelect.value = lang;

    // Update text elements
    document.querySelectorAll('[data-t]').forEach(el => {
        const key = el.getAttribute('data-t');
        if (translations[lang][key]) {
            el.innerHTML = translations[lang][key];
        }
    });

    // Update placeholders
    document.querySelectorAll('[data-t-ph]').forEach(el => {
        const key = el.getAttribute('data-t-ph');
        if (translations[lang][key]) {
            el.placeholder = translations[lang][key];
        }
    });
    
    // Re-render library to update "Add" button
    filterLibrary();
}

// --- THEME LOGIC ---
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const newTheme = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// --- AUDIO PAD LOGIC ---
const padA = document.getElementById('pad-player-a');
const padB = document.getElementById('pad-player-b');

let currentPadPlayer = null; 
let isPadPlaying = false;
let globalPadVolume = 0.5;
let activeFadeIntervals = new Map();

let currentTargetKey = null;

let padDebounceTimer = null;
const PAD_DELAY_MS = 2000;

const KEY_MAP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
const FLAT_TO_SHARP = {'Db':'C#', 'Eb':'D#', 'Gb':'F#', 'Ab':'G#', 'Bb':'A#', 'Cb':'B'};

document.addEventListener("DOMContentLoaded", function() {
    const slider = document.getElementById('pad-volume-slider');
    if(slider) updatePadVolume(slider);
    
    // Init Language
    const savedLang = localStorage.getItem('appLang') || 'pl';
    setLanguage(savedLang);
    
    // Load library from Global Window Object
    if(window.SERVER_DATA && window.SERVER_DATA.songs) {
        // Initial render
        filterLibrary();
    }
});

function normalizeKey(k) {
    if(!k) return null;
    let match = k.match(/^([A-G][#b]?)(.*)$/i);
    if(!match) return null;
    let root = match[1];
    root = root.charAt(0).toUpperCase() + root.slice(1).toLowerCase();
    if(FLAT_TO_SHARP[root]) root = FLAT_TO_SHARP[root];
    
    let suffix = match[2].trim().toLowerCase();
    if(suffix.startsWith('m') && !suffix.startsWith('maj')) {
        let idx = KEY_MAP.indexOf(root);
        if(idx !== -1) {
            let newIdx = (idx + 3) % 12;
            return KEY_MAP[newIdx];
        }
    }
    return root;
}

function triggerDebouncedPad(targetKey) {
    if(!isPadPlaying) return;

    if (padDebounceTimer) clearTimeout(padDebounceTimer);
    
    console.log(`[PAD] Oczekiwanie na ustabilizowanie tonacji: ${targetKey}...`);

    padDebounceTimer = setTimeout(() => {
        console.log(`[PAD] Tonacja stabilna przez ${PAD_DELAY_MS}ms. Odtwarzam: ${targetKey}`);
        playPad(targetKey);
    }, PAD_DELAY_MS);
}

function togglePad() {
    isPadPlaying = !isPadPlaying;
    const btn = document.getElementById('pad-toggle-btn');
    const status = document.getElementById('pad-status-text');
    
    if (padDebounceTimer) clearTimeout(padDebounceTimer);

    if(isPadPlaying) {
        btn.classList.add('active');
        status.innerText = "ON";
        if(currentSetIndex !== -1 && setlist[currentSetIndex]) {
            let rawKey = calculateTransposedKey(setlist[currentSetIndex].key, setlist[currentSetIndex].transpose);
            playPad(rawKey); 
        }
    } else {
        btn.classList.remove('active');
        status.innerText = "OFF";
        currentTargetKey = null; 
        fadeOutAllPads();
    }
}

function updatePadVolume(slider) {
    let val = parseFloat(slider.value);
    globalPadVolume = val;
    
    if(currentPadPlayer && !currentPadPlayer.paused) {
         if (!activeFadeIntervals.has(currentPadPlayer)) {
              currentPadPlayer.volume = globalPadVolume;
         }
    }

    const percentage = (val - slider.min) / (slider.max - slider.min) * 100;
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const accentColor = isDark ? '#4e95ff' : '#5e72e4';
    const trackColor = isDark ? '#333' : '#e9ecef';
    
    slider.style.background = `linear-gradient(to right, ${accentColor} 0%, ${accentColor} ${percentage}%, ${trackColor} ${percentage}%, ${trackColor} 100%)`;
    
    const txt = document.getElementById('pad-vol-text');
    if(txt) txt.innerText = Math.round(percentage) + "%";
}

const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.type === "attributes" && mutation.attributeName === "data-theme") {
              const slider = document.getElementById('pad-volume-slider');
              if(slider) updatePadVolume(slider);
        }
    });
});
observer.observe(document.documentElement, { attributes: true });

function playPad(rawKey, transitionDuration = 2000) {
    if(!isPadPlaying) return;
    let targetKey = normalizeKey(rawKey);
    if(!targetKey) return; 

    currentTargetKey = targetKey;

    let filename = `/static/pads/${targetKey}.mp3`;
    let active = currentPadPlayer;
    let next = (active === padA) ? padB : padA;

    if(active && active.src.includes(encodeURIComponent(targetKey)+".mp3") && !active.paused && !activeFadeIntervals.has(active)) {
        fadeInPlayer(active, transitionDuration);
        return; 
    }

    console.log(`[PAD] Przełączam na ${targetKey}`);
    document.getElementById('pad-status-text').innerText = targetKey;

    next.src = filename;
    next.volume = 0; 
    
    next.play().then(() => {
        if (!isPadPlaying) {
            next.pause();
            next.currentTime = 0;
            return;
        }
        if (currentTargetKey !== targetKey) {
            return;
        }

        currentPadPlayer = next;
        fadeInPlayer(next, transitionDuration);
        
        if (active && active !== next) {
            fadeOutPlayer(active, transitionDuration);
        }

    }).catch(e => console.error("Pad play error:", e));
}

function fadeInPlayer(player, duration) {
    if (activeFadeIntervals.has(player)) {
        clearInterval(activeFadeIntervals.get(player));
        activeFadeIntervals.delete(player);
    }

    const startTime = Date.now();
    const startVol = player.volume;
    const targetVol = globalPadVolume;

    const interval = setInterval(() => {
        if (!player || (player !== currentPadPlayer && !activeFadeIntervals.has(player))) {
             clearInterval(interval);
             return;
        }

        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const newVol = startVol + (targetVol - startVol) * progress;
        player.volume = Math.max(0, Math.min(1, newVol));

        if (progress >= 1) {
            clearInterval(interval);
            activeFadeIntervals.delete(player);
            player.volume = targetVol; 
        }
    }, 20);

    activeFadeIntervals.set(player, interval);
}

function fadeOutPlayer(player, duration) {
    if (activeFadeIntervals.has(player)) {
        clearInterval(activeFadeIntervals.get(player));
        activeFadeIntervals.delete(player);
    }

    const startTime = Date.now();
    const startVol = player.volume;

    const interval = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);

        player.volume = Math.max(0, startVol * (1 - progress));

        if (progress >= 1) {
            clearInterval(interval);
            activeFadeIntervals.delete(player);
            player.pause();
            player.currentTime = 0;
            player.volume = 0;
        }
    }, 20);

    activeFadeIntervals.set(player, interval);
}

function fadeOutAllPads() {
    [padA, padB].forEach(p => {
        if(!p.paused) fadeOutPlayer(p, 2000); 
    });
    currentPadPlayer = null;
}

// --- SYNCHRONIZACJA ---
socket.on('connect', function() {
    console.log('Połączono z serwerem via SocketIO');
});

socket.on('sync_state_to_client', function(data) {
    console.log('Otrzymano synchronizację:', data);
    
    if (data.setlist && JSON.stringify(setlist) !== JSON.stringify(data.setlist)) {
        setlist = data.setlist;
        renderSetlist();
    }

    if (data.current_index !== undefined && data.current_index !== currentSetIndex) {
        currentSetIndex = data.current_index;
        renderSetlist(); 
        
        if (currentSetIndex !== -1 && setlist[currentSetIndex]) {
            selectForLive(currentSetIndex, false); 
        } else {
            document.getElementById('live-header').style.display = 'none';
            document.getElementById('slides-container').innerHTML = '';
        }
    }
});

socket.on('update_slide', function(data) {
    const previewBox = document.getElementById('live-preview-box');
    if (!previewBox) return;
    previewBox.innerHTML = "";
    
    if (data.mode === 'worship') {
        let textContent = data.people.replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, ""); 
        
        // Synchronizacja przycisku z innymi urządzeniami (opcjonalnie)
        if (data.is_blackout !== undefined) {
            isBlackoutActive = data.is_blackout;
            const btn = document.querySelector('button[onclick="blackout()"]');
            if (btn) {
                if (isBlackoutActive) btn.classList.add('active');
                else btn.classList.remove('active');
            }
        }

        // Podgląd live na panelu głównym
        if (data.is_blackout) {
            const txt = (currentLang === 'en') ? "SCREEN BLACKED OUT" : "EKRAN WYGASZONY";
            previewBox.innerText = txt;
        } else {
            previewBox.innerText = textContent;
        }

        const slides = document.querySelectorAll('.slide-btn');
        slides.forEach(btn => {
            btn.classList.remove('active');
            const spans = btn.querySelectorAll('span');
            if (spans.length > 1) {
                const btnText = spans[1].innerText.replace(/\s/g, '').substring(0, 20);
                const currentText = textContent.replace(/\s/g, '').substring(0, 20);
                if (btnText && currentText && (btnText === currentText || currentText.includes(btnText))) {
                    btn.classList.add('active');
                }
            }
        });
    } else if (data.mode === 'blackout') {
        const txt = (currentLang === 'en') ? "SCREEN BLACKED OUT" : "EKRAN WYGASZONY";
        previewBox.innerText = txt;
    } else if (data.mode === 'logo') {
        previewBox.innerText = "LOGO";
    }
});
let currentPresentationSlides = [];
let currentSlideIndex = 0;

// Funkcja wgrywająca PDF
function uploadPdfPresentation() {
    const fileInput = document.getElementById('pdf-upload');
    if (!fileInput.files[0]) return alert("Wybierz plik PDF!");

    const formData = new FormData();
    formData.append("pres_file", fileInput.files[0]);

    fetch('/upload_presentation', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if(data.status === 'ok') {
            alert("Slajdy gotowe!");
            // Slajdy zostaną odebrane przez socket event 'presentation_ready'
        } else {
            alert(data.message);
        }
    });
}

// Odbieranie slajdów od serwera
socket.on('presentation_ready', function(data) {
    currentPresentationSlides = data.slides;
    currentSlideIndex = 0;
    document.getElementById('slide-counter').innerText = `1 / ${currentPresentationSlides.length}`;
});

// Sterowanie lokalną prezentacją
function changeSlide(direction) {
    if (currentPresentationSlides.length === 0) return;
    
    currentSlideIndex += direction;
    if (currentSlideIndex < 0) currentSlideIndex = 0;
    if (currentSlideIndex >= currentPresentationSlides.length) currentSlideIndex = currentPresentationSlides.length - 1;
    
    document.getElementById('slide-counter').innerText = `${currentSlideIndex + 1} / ${currentPresentationSlides.length}`;
    sendPresentationState();
}

function sendPresentationState() {
    let currentUrl = currentPresentationSlides[currentSlideIndex];
    let nextUrl = (currentSlideIndex + 1 < currentPresentationSlides.length) ? currentPresentationSlides[currentSlideIndex + 1] : null;
    
    let d = updTimer(); // Twoja funkcja aktualizująca zegar
    fetch('/send_text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            mode: 'presentation', 
            slide_url: currentUrl, 
            next_slide_url: nextUrl,
            timer: d.text, 
            timer_color: d.color, 
            message: actMsg,
            blackout: isBlackoutActive
        })
    });
}

// --- ZARZĄDZANIE KILKOMA LINKAMI CANVA ---
let canvaLinks = JSON.parse(localStorage.getItem('canvaLinks')) || [];

function renderCanvaLinks() {
    const list = document.getElementById('canva-links-list');
    if (!list) return;
    list.innerHTML = '';
    
    if(canvaLinks.length === 0) {
        // Tłumaczenie błędu
        const emptyMsg = translations[currentLang].no_canva_msg || "Brak dodanych prezentacji.";
        list.innerHTML = `<div style="color:var(--text-muted); font-size:0.8rem; text-align:center; padding: 10px; border: 1px dashed var(--border-color); border-radius: 6px;">${emptyMsg}</div>`;
        return;
    }

    canvaLinks.forEach((link, index) => {
        const item = document.createElement('div');
        item.style.display = 'flex';
        item.style.alignItems = 'center';
        item.style.gap = '10px';
        item.style.background = 'var(--bg-element)';
        item.style.padding = '8px 12px';
        item.style.borderRadius = '6px';
        item.style.border = '1px solid var(--border-color)';
        
        const shortLink = link.length > 35 ? link.substring(0, 35) + '...' : link;
        
        // Tłumaczenia przycisków wewnątrz listy
        const label = translations[currentLang].presentation_label || "Prezentacja";
        const btnShow = translations[currentLang].show_btn || "🖥️ POKAŻ";

        item.innerHTML = `
            <div style="flex-grow: 1; font-size: 0.75rem; color: var(--text-muted); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-family: monospace;" title="${link}">
                ${label} ${index + 1}: ${shortLink}
            </div>
            <button class="action-btn" style="background:var(--accent-success); padding: 6px 12px; font-size: 0.75rem;" onclick="sendSpecificCanvaLink(${index})">${btnShow}</button>
            <button class="btn-sm" style="background:var(--accent-danger); color:white; border:none; padding: 6px 10px; font-weight: bold;" onclick="removeCanvaLink(${index})">✕</button>
        `;
        list.appendChild(item);
    });
}

function addCanvaLink() {
    let input = document.getElementById('new-canva-link');
    let link = input.value.trim();
    if (!link) return;

    // Auto-naprawa linku do wersji embed (zabezpieczenie)
    if (link.includes('canva.com') && !link.includes('?embed')) {
        link = link.replace(/\/edit.*$/, '/view?embed').replace(/\/view.*$/, '/view?embed');
    }

    canvaLinks.push(link);
    localStorage.setItem('canvaLinks', JSON.stringify(canvaLinks)); // Zapisujemy w pamięci
    input.value = '';
    renderCanvaLinks();
}

function removeCanvaLink(index) {
    canvaLinks.splice(index, 1);
    localStorage.setItem('canvaLinks', JSON.stringify(canvaLinks));
    renderCanvaLinks();
}

function sendSpecificCanvaLink(index) {
    const link = canvaLinks[index];
    if (!link) return;

    let d = typeof updTimer === 'function' ? updTimer() : {text: '00:00', color: 'white'};
    fetch('/send_text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            mode: 'canva', 
            url: link,
            timer: d.text, 
            timer_color: d.color, 
            message: typeof actMsg !== 'undefined' ? actMsg : '',
            blackout: typeof isBlackoutActive !== 'undefined' ? isBlackoutActive : false
        })
    });
}

// Inicjalizacja listy po załadowaniu skryptu
document.addEventListener('DOMContentLoaded', () => {
    renderCanvaLinks();
});
// Asekuracyjne wywołanie (gdyby skrypt załadował się po DOMContentLoaded)
setTimeout(renderCanvaLinks, 500);

function updateServerState() {
    socket.emit('client_update_state', {
        setlist: setlist,
        current_index: currentSetIndex
    });
}

function switchMode(m){document.querySelectorAll('.mode-container').forEach(c=>c.classList.remove('active'));document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active'));if(m==='worship'){document.getElementById('worship-mode').classList.add('active');document.querySelector('button[onclick="switchMode(\'worship\')"]').classList.add('active');}else{document.getElementById('conference-mode').classList.add('active');document.querySelector('button[onclick="switchMode(\'conference\')"]').classList.add('active');sendConferenceData();}}
function openQRModal(){document.getElementById('qrModal').style.display='flex';}
function closeQRModal(){document.getElementById('qrModal').style.display='none';}

function openSettingsModal(){
    document.getElementById('settingsModal').style.display='flex';
    
    const storedState = localStorage.getItem('transitionsEnabled');
    document.getElementById('trans-toggle').checked = (storedState !== 'false');
    const keyState = localStorage.getItem('keyDetectionEnabled');
    document.getElementById('key-detect-toggle').checked = (keyState !== 'false');
    
    const currentTheme = document.documentElement.getAttribute('data-theme');
    document.getElementById('theme-toggle').checked = (currentTheme === 'dark');
    
    document.getElementById('lang-select').value = localStorage.getItem('appLang') || 'pl';
}
function closeSettingsModal(){document.getElementById('settingsModal').style.display='none';}
function openImportModal(){document.getElementById('importModal').style.display='flex';}
function closeImportModal(){document.getElementById('importModal').style.display='none';}
function openAddModal(){document.getElementById('addModal').style.display='flex';}
function closeAddModal(){document.getElementById('addModal').style.display='none';}

function toggleAddMenu() {
    const menu = document.getElementById('add-menu-dropdown');
    menu.classList.toggle('show');
}
window.onclick = function(e) {
    if(e.target.classList.contains('modal')) e.target.style.display='none';
    if (!e.target.matches('.plus-btn')) {
        const dropdowns = document.getElementsByClassName("dropdown-menu");
        for (let i = 0; i < dropdowns.length; i++) {
            if (dropdowns[i].classList.contains('show')) dropdowns[i].classList.remove('show');
        }
    }
}

const isIos = () => {
    const userAgent = window.navigator.userAgent.toLowerCase();
    return /iphone|ipad|ipod/.test(userAgent);
}
const isInStandaloneMode = () => ('standalone' in window.navigator) && (window.navigator.standalone);

const prompt = document.getElementById('ios-install-prompt');
if (prompt && isIos()) {
    const fsBtn = document.getElementById('fs-btn-desktop');
    if(fsBtn) fsBtn.style.display = 'none'; 
    if (!isInStandaloneMode()) {
        prompt.style.display = 'block';
    }
}

function toggleFullscreen() {
    var doc = window.document;
    var docEl = doc.documentElement;
    var requestFullScreen = docEl.requestFullscreen || docEl.mozRequestFullScreen || docEl.webkitRequestFullScreen || docEl.msRequestFullscreen;
    var cancelFullScreen = doc.exitFullscreen || doc.mozCancelFullScreen || doc.webkitExitFullscreen || doc.msExitFullscreen;

    if (!doc.fullscreenElement && !doc.mozFullScreenElement && !doc.webkitFullscreenElement && !doc.msFullscreenElement) {
        if (requestFullScreen) {
            requestFullScreen.call(docEl).catch(err => {
                alert("Na iPhone/iPad: Dodaj stronę do ekranu gł, aby uzyskać pełny ekran.");
            });
        }
    } else {
        if (cancelFullScreen) cancelFullScreen.call(doc);
    }
}

function updateFileName(input) {
    if (input.files && input.files.length > 0) {
        input.previousElementSibling.innerText = input.files[0].name;
    }
}

document.addEventListener('keydown', (e) => {
    // Ignoruj strzałki, jeśli akurat wpisujesz coś w polu tekstowym (np. wiadomość dla mówcy)
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    
    // Sprawdzamy, który tryb jest obecnie włączony na ekranie
    const isConferenceActive = document.getElementById('conference-mode').classList.contains('active');

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { 
        e.preventDefault(); 
        if (isConferenceActive) {
            changeSlide(1); // Zmienia slajd PDF w trybie Konferencji
        } else {
            navigateSlides(1); // Zmienia kafelek piosenki w trybie Uwielbienia
        }
    }
    
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { 
        e.preventDefault(); 
        if (isConferenceActive) {
            changeSlide(-1);
        } else {
            navigateSlides(-1); 
        }
    }
});

function navigateSlides(direction) {
    const slides = Array.from(document.querySelectorAll('.slide-btn'));
    if (slides.length === 0) return;
    const activeIndex = slides.findIndex(s => s.classList.contains('active'));
    if (activeIndex === -1) { slides[0].click(); return; }
    const nextIndex = activeIndex + direction;
    if (nextIndex >= 0 && nextIndex < slides.length) { slides[nextIndex].click(); } 
    else if (nextIndex >= slides.length) {
        if (currentSetIndex < setlist.length - 1) {
            selectForLive(currentSetIndex + 1);
            setTimeout(() => {
                  const newSlides = document.querySelectorAll('.slide-btn');
                  if(newSlides.length > 0) newSlides[0].click();
            }, 50);
        }
    }
    else if (nextIndex < 0) {
        if (currentSetIndex > 0) {
            selectForLive(currentSetIndex - 1);
            setTimeout(() => {
                const newSlides = document.querySelectorAll('.slide-btn');
                if(newSlides.length > 0) newSlides[newSlides.length - 1].click();
            }, 50);
        }
    }
}

function goToNextSong() {
    if (currentSetIndex < setlist.length - 1) {
        selectForLive(currentSetIndex + 1);
        setTimeout(() => {
              const newSlides = document.querySelectorAll('.slide-btn');
              if(newSlides.length > 0) newSlides[0].click();
        }, 100);
    } else {
        const txt = currentLang === 'en' ? "Last song in setlist!" : "To ostatnia piosenka w setliście!";
        alert(txt);
    }
}

let transitionsEnabled = true;
let keyDetectionEnabled = true;

(function initSettings() {
    const transState = localStorage.getItem('transitionsEnabled');
    transitionsEnabled = (transState !== 'false');
    const keyState = localStorage.getItem('keyDetectionEnabled');
    keyDetectionEnabled = (keyState !== 'false');
})();

function toggleTransitions() {
    const checkbox = document.getElementById('trans-toggle');
    transitionsEnabled = checkbox.checked;
    localStorage.setItem('transitionsEnabled', transitionsEnabled);
    if(currentSetIndex !== -1) selectForLive(currentSetIndex);
}

function toggleKeyDetection() {
    const checkbox = document.getElementById('key-detect-toggle');
    keyDetectionEnabled = checkbox.checked;
    localStorage.setItem('keyDetectionEnabled', keyDetectionEnabled);
}

function switchMobTab(tabName) {
    document.getElementById('col-library').style.display = 'none';
    document.getElementById('col-setlist').style.display = 'none';
    document.getElementById('col-live').style.display = 'none';
    
    // KLUCZOWA ZMIANA: Zmieniamy z 'block' na 'flex', aby listy znów dało się przewijać
    document.getElementById('col-' + tabName).style.display = 'flex';

    document.querySelectorAll('.mob-tab').forEach(b => b.classList.remove('active'));
    event.currentTarget.classList.add('active');
}
function showToast(message) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerText = message;
    container.appendChild(toast);
    
    // Usuwamy powiadomienie po 2.5 sekundach
    setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 2500);
}
// UŻYWAMY DANYCH PRZEKAZANYCH Z HTML
const library = (window.SERVER_DATA && window.SERVER_DATA.songs) ? window.SERVER_DATA.songs : [];
let setlist = []; let currentSetIndex = -1;

let tapTimes = [];
function tapTempo(inputId) {
    const now = Date.now();
    if (tapTimes.length > 0 && now - tapTimes[tapTimes.length - 1] > 2000) tapTimes = [];
    tapTimes.push(now);
    if (tapTimes.length > 1) {
        let intervals = [];
        for (let i = 1; i < tapTimes.length; i++) intervals.push(tapTimes[i] - tapTimes[i-1]);
        let avg = intervals.reduce((a,b) => a+b) / intervals.length;
        let bpm = Math.round(60000 / avg);
        document.getElementById(inputId).value = bpm;
    }
}

function useSuggestedKey(inputId) {
    const el = document.getElementById(inputId);
    if (!el.value && el.placeholder && el.placeholder !== "Key") el.value = el.placeholder;
}

let timeoutId = null;
function liveKeyCheck(contentId, inputId) {
    if (!keyDetectionEnabled) return;
    const text = document.getElementById(contentId).value;
    const inputEl = document.getElementById(inputId);
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
        if(!text) { inputEl.placeholder = "Key"; return; }
        fetch('/detect_key', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: text})})
        .then(r => r.json()).then(data => { if(data.key && data.key !== "N/A") inputEl.placeholder = data.key; else inputEl.placeholder = "Key"; });
    }, 500); 
}

function renderLibrary(f="") {
    const c = document.getElementById('library-list'); 
    if(!c) return;
    c.innerHTML=""; 
    const btnText = translations[currentLang].add_btn_small || "DODAJ";
    library.forEach(s => {
        if (s.title.toLowerCase().includes(f.toLowerCase()) || s.content.toLowerCase().includes(f.toLowerCase())) {
            const d = document.createElement('details'); d.className = 'lib-item';
            const preview = s.content.replace(/\[.*?\]/g, "").substring(0, 300) + "...";
            d.innerHTML = `
                <summary class="lib-summary">
                    <div><b>${s.title}</b></div>
                    <div style="display:flex;gap:5px;">
                        <button class="btn-icon" onclick="event.preventDefault(); openEditModal(${s.id})" style="background:none; border:none; cursor:pointer;">✏️</button> 
                        <button class="btn-sm" onclick="event.preventDefault(); addToSetlist(${s.id}, this)" style="background:var(--accent-success);color:white; border:none; transition: transform 0.2s;">${btnText}</button>
                    </div>
                </summary>
                <div class="lib-content-preview">${preview}</div>`;
            c.appendChild(d);
        }
    });
}
function filterLibrary(){renderLibrary(document.getElementById('searchBox').value);}

function addToSetlist(id, btnElement) {
    const item = library.find(s=>s.id===id);
    setlist.push({...item, transpose:0}); 
    renderSetlist();
    if(setlist.length===1) selectForLive(0);
    updateServerState(); 

    // Animacja przycisku
    if (btnElement) {
        const originalText = btnElement.innerText;
        btnElement.innerText = "✔"; // Krótka zmiana na ptaszka
        btnElement.style.transform = "scale(1.15)";
        
        setTimeout(() => {
            btnElement.innerText = originalText;
            btnElement.style.transform = "scale(1)";
        }, 800);
    }

    // Wyświetlenie dymka powiadomienia
    showToast(`Dodano: ${item.title}`);
}
function removeFromSetlist(i){
    setlist.splice(i,1);
    if(currentSetIndex===i){
        document.getElementById('live-header').style.display='none';
        document.getElementById('slides-container').innerHTML='';
        currentSetIndex=-1;
        fadeOutAllPads(); 
    }
    renderSetlist();
    updateServerState(); 
}

function renderSetlist() {
    const container = document.getElementById('setlist-container');
    if (!container) return;
    
    if (setlist.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); margin-top: 40px; font-size: 0.9rem;">Brak piosenek w setliście.</div>';
        return;
    }

    let html = '';
    setlist.forEach((s, index) => {
        const isActive = (index === currentSetIndex) ? 'active' : '';
        html += `
        <div class="setlist-item ${isActive}" onclick="selectForLive(${index})">
            <div class="drag-handle" onclick="event.stopPropagation()">☰</div>
            
            <div class="setlist-content">
                <span>${index + 1}.</span> ${s.title}
                <span style="color:var(--text-muted); font-size:0.8rem; margin-left:6px;">(${s.key})</span>
            </div>
            
            <button class="btn-sm" onclick="event.stopPropagation(); removeFromSetlist(${index})" style="background:transparent; border:1px solid var(--accent-danger); color:var(--accent-danger); padding: 8px;">✕</button>
        </div>`;
    });
    container.innerHTML = html;
}
function moveSetlistItem(index, direction) {
    const newIndex = index + direction; if (newIndex < 0 || newIndex >= setlist.length) return;
    const temp = setlist[index]; setlist[index] = setlist[newIndex]; setlist[newIndex] = temp;
    if (currentSetIndex === index) currentSetIndex = newIndex; else if (currentSetIndex === newIndex) currentSetIndex = index;
    renderSetlist();
    updateServerState();
}

function calculateTransposedKey(originalKey, shift) {
    if (!originalKey) return "N/A";
    const match = originalKey.match(/^([A-G][#b]?)(.*)$/i);
    if (!match) return originalKey;
    let root = match[1]; let suffix = match[2]; let isLower = (root[0] === root[0].toLowerCase()); let rootUpper = root.toUpperCase();
    const noteMap = {'C':0, 'C#':1, 'DB':1, 'D':2, 'D#':3, 'EB':3, 'E':4, 'F':5, 'F#':6, 'GB':6, 'G':7, 'G#':8, 'AB':8, 'A':9, 'A#':10, 'BB':10, 'B':11, 'CB':11};
    const reverseMap = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    if (noteMap[rootUpper] === undefined) return originalKey;
    let val = noteMap[rootUpper]; let newVal = (val + shift) % 12; if (newVal < 0) newVal += 12;
    let newRoot = reverseMap[newVal]; if (isLower) newRoot = newRoot.toLowerCase();
    return newRoot + suffix;
}

function parseSongSections(raw) {
    if (!raw) return [];
    
    // ZMIANA KLUCZOWA:
    // Regex /\n\s*\n/ oznacza: "Enter, potem opcjonalne spacje, potem kolejny Enter".
    // To gwarantuje, że podział nastąpi TYLKO w miejscach pustych linii.
    // Jeśli piosenka nie ma pustych linii, zostanie potraktowana jako 1 kafelek.
    const parts = raw.split(/\n\s*\n/);

    return parts.filter(b => b.trim()).map((block, i) => {
        let lines = block.trim().split('\n');
        
        // Domyślna nazwa
        let label = `SLAJD ${i + 1}`;
        let content = block;

        // Próba wyciągnięcia nazwy sekcji z pierwszej linii (np. "Zwrotka 1")
        // Warunek: pierwsza linia jest krótka (< 30 znaków) i nie zawiera nawiasów akordów '['
        if (lines.length > 0 && !lines[0].includes('[') && lines[0].length < 30) {
            label = lines[0].trim();
            content = lines.slice(1).join('\n').trim();
        }

        return { label: label, content: content };
    });
}
function selectForLive(i, broadcast = true){
    currentSetIndex=i; 
    renderSetlist();
    
    if (broadcast) {
        updateServerState();
    }

    const item=setlist[i];
    document.getElementById('live-header').style.display='block';
    document.getElementById('current-title').innerText=item.title;
    document.getElementById('current-trans').innerText=(item.transpose>0?"+":"")+item.transpose;
    
    let finalKey = calculateTransposedKey(item.key, item.transpose);
    document.getElementById('live-key').innerText = finalKey;
    document.getElementById('live-bpm').innerText = item.bpm ? item.bpm : "-";
    
    if(isPadPlaying) {
       triggerDebouncedPad(finalKey);
    }

    const sc=document.getElementById('slides-container');sc.innerHTML="";
    const secs=parseSongSections(item.content);
    secs.forEach((sec,idx)=>{
        const b=document.createElement('div'); b.className='slide-btn';
        b.innerHTML=`<span class="slide-label">${sec.label}</span><span>${sec.content.replace(/\[.*?\]/g,"").substring(0,40)}...</span>`;
        b.onclick=()=>{
            document.querySelectorAll('.slide-btn').forEach(x=>x.classList.remove('active')); b.classList.add('active');
            
            let nextContent = "";
            let nextTrans = item.transpose; 

            if (idx + 1 < secs.length) {
                nextContent = secs[idx + 1].content;
            } else if (i + 1 < setlist.length) {
                // To ostatni slajd w piosence, pobieramy pierwszy z następnej:
                const nextSongSecs = parseSongSections(setlist[i + 1].content);
                if (nextSongSecs.length > 0) {
                    nextContent = nextSongSecs[0].content;
                    nextTrans = setlist[i + 1].transpose; // Bierzemy nową transpozycję!
                }
            }

            goLiveSection(sec.content, nextContent, null, nextTrans); 
        };
        sc.appendChild(b);
    });
    
    if (i < setlist.length - 1 && transitionsEnabled) { 
        const nextItem = setlist[i + 1];
        const chordRegex = /\[(.*?)\]/g;
        const currentMatches = item.content.match(chordRegex);
        const nextMatches = nextItem.content.match(chordRegex);
        const lastChordRaw = currentMatches ? currentMatches[currentMatches.length - 1] : null;
        const firstChordRaw = nextMatches ? nextMatches[0] : null;
        if (lastChordRaw && firstChordRaw) {
            const btn = document.createElement('div'); btn.className = 'slide-btn transition-tile';
            btn.innerHTML = `<span class="slide-label">TRANSITION ➔</span><span id="trans-preview" style="font-size:0.7rem;color:var(--text-muted);">Ładowanie...</span>`;
            
            const fetchTransition = () => {
                fetch('/generate_transition', { 
                    method: 'POST', 
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        id_start: item.id,        
                        id_end: nextItem.id,     
                        start_chord: lastChordRaw, 
                        end_chord: firstChordRaw, 
                        transpose_start: item.transpose, 
                        transpose_end: nextItem.transpose 
                    })
                }).then(r => r.json()).then(data => {
                        if (data.status === 'ok') {
                            const previewBox = btn.querySelector('#trans-preview');
                            if(previewBox) previewBox.innerText = `${data.debug_start} → ${data.debug_end}`;
                            btn.dataset.transitionHtml = data.transition;
                        } else { if(btn.querySelector('#trans-preview')) btn.querySelector('#trans-preview').innerText = "Błąd"; }
                });
            };
            fetchTransition();
            btn.onclick = () => {
                document.querySelectorAll('.slide-btn').forEach(x=>x.classList.remove('active')); btn.classList.add('active');
                
                if(isPadPlaying && i < setlist.length - 1) {
                    let nextSong = setlist[i+1];
                    let nextKey = calculateTransposedKey(nextSong.key, nextSong.transpose);
                    console.log(`[TRANSITION] Kliknięto przejście. Pad zmieni się na ${nextKey} za 5s.`);
                    
                    setTimeout(() => {
                        playPad(nextKey, 5000);
                    }, 8000);
                }

                let nextContent = "";
            let nextTrans = nextItem.transpose;
            const nextSongSecs = parseSongSections(nextItem.content);
            if (nextSongSecs.length > 0) {
                nextContent = nextSongSecs[0].content;
            }

            if (btn.dataset.transitionHtml) { 
                goLiveSection(btn.dataset.transitionHtml, nextContent, 0, nextTrans); 
            }
            };
            sc.appendChild(btn);
        }
    }
}

function adjustLiveTrans(a){
    if(currentSetIndex!==-1){
        setlist[currentSetIndex].transpose+=a;
        document.getElementById('current-trans').innerText = (setlist[currentSetIndex].transpose>0?"+":"")+setlist[currentSetIndex].transpose;
        let finalKey = calculateTransposedKey(setlist[currentSetIndex].key, setlist[currentSetIndex].transpose);
        document.getElementById('live-key').innerText = finalKey;
        
        if (isPadPlaying) {
            triggerDebouncedPad(finalKey);
        }
        
        selectForLive(currentSetIndex); 
    }
}

function goLiveSection(c, n, forceTrans = null, nextTrans = null) {
    currentLiveState = { c: c, n: n, forceTrans: forceTrans, nextTrans: nextTrans };
    let t = (forceTrans !== null) ? forceTrans : setlist[currentSetIndex].transpose;
    let nt = (nextTrans !== null) ? nextTrans : t; 
    
    let currentKey = document.getElementById('live-key') ? document.getElementById('live-key').innerText : 'N/A';
    let currentBpm = setlist[currentSetIndex] ? setlist[currentSetIndex].bpm : 0;
    
    fetch('/send_text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            text: c, 
            next_text: n, 
            transpose: t, 
            next_transpose: nt, 
            key: currentKey, 
            bpm: currentBpm,
            current_index: currentSetIndex,
            setlist: setlist,
            blackout: isBlackoutActive // Dodajemy stan blackoutu
        })
    });
    
    if (isBlackoutActive) {
        const txt = (currentLang === 'en') ? "SCREEN BLACKED OUT" : "EKRAN WYGASZONY";
        document.getElementById('live-preview-box').innerText = txt;
    } else {
        document.getElementById('live-preview-box').innerText = c.replace(/\[.*?\]/g, "");
    }
}
let isBlackoutActive = false;
let currentLiveState = { c: '', n: '', forceTrans: null, nextTrans: null };

function blackout() {
    isBlackoutActive = !isBlackoutActive;
    
    const btns = document.querySelectorAll('button[onclick="blackout()"]');
    if (isBlackoutActive) {
        btns.forEach(btn => {
            btn.style.background = "var(--accent-danger)";
            btn.style.color = "white";
            btn.style.boxShadow = "0 0 20px rgba(233, 20, 41, 0.7)";
            // Czerpiemy tekst ze słownika (EN lub PL)
            btn.innerText = translations[currentLang].blackout_off_btn || "ZDEJMIJ BLACKOUT (POKAŻ EKRAN)";
        });
    } else {
        btns.forEach(btn => {
            btn.style.background = ""; 
            btn.style.color = "";
            btn.style.boxShadow = "";
            // Czerpiemy domyślny tekst (EN lub PL)
            btn.innerText = translations[currentLang].blackout_on_btn || "WYGAŚ EKRAN RZUTNIKA";
        });
    }

    let t = (currentLiveState.forceTrans !== null) ? currentLiveState.forceTrans : (setlist[currentSetIndex] ? setlist[currentSetIndex].transpose : 0);
    let nt = (currentLiveState.nextTrans !== null) ? currentLiveState.nextTrans : t;
    let currentKey = document.getElementById('live-key') ? document.getElementById('live-key').innerText : '';
    let currentBpm = setlist[currentSetIndex] ? setlist[currentSetIndex].bpm : '';

    fetch('/send_text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            text: currentLiveState.c, 
            next_text: currentLiveState.n, 
            transpose: t, 
            next_transpose: nt,
            key: currentKey, 
            bpm: currentBpm,
            current_index: currentSetIndex,
            setlist: setlist,
            blackout: isBlackoutActive
        })
    });
}

function goLiveSection(c, n, forceTrans = null, nextTrans = null) {
    // Zapisujemy aktualny stan slajdu (by blackout mógł go użyć przy włączeniu/wyłączeniu)
    currentLiveState = { c: c, n: n, forceTrans: forceTrans, nextTrans: nextTrans };

    let t = (forceTrans !== null) ? forceTrans : setlist[currentSetIndex].transpose;
    let nt = (nextTrans !== null) ? nextTrans : t; 
    
    let currentKey = document.getElementById('live-key') ? document.getElementById('live-key').innerText : '';
    let currentBpm = setlist[currentSetIndex] ? setlist[currentSetIndex].bpm : '';
    
    // Wysyłamy nowy slajd, PODTRZYMUJĄC obecny stan blackoutu!
    // Jeśli blackout jest włączony, rzutnik to zignoruje, ale widok zespołu (stage) się zaktualizuje.
    fetch('/send_text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            text: c, 
            next_text: n, 
            transpose: t, 
            next_transpose: nt,
            key: currentKey, 
            bpm: currentBpm,
            current_index: currentSetIndex,
            setlist: setlist,
            blackout: isBlackoutActive 
        })
    });
    
    // Operator zawsze widzi u siebie na podglądzie tekst, żeby wiedzieć co wysłał zespołowi
    document.getElementById('live-preview-box').innerText = c.replace(/\[.*?\]/g, "");
}
function showLogo(){fetch('/send_text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({logo:true})});document.getElementById('live-preview-box').innerText="LOGO";}

function openEditModal(id){
    const s=library.find(x=>x.id===id);
    if(s){
        document.getElementById('edit-title').value=s.title;
        document.getElementById('edit-content').value=s.content;
        document.getElementById('edit-key-input').value = s.key || '';
        document.getElementById('edit-bpm-input').value = s.bpm || '';
        if(!s.key) liveKeyCheck('edit-content', 'edit-key-input');
        document.getElementById('editForm').action='/edit_song/'+id;
        document.getElementById('deleteForm').action='/delete_song/'+id;
        document.getElementById('editModal').style.display='flex';
    }
}
function closeEditModal(){document.getElementById('editModal').style.display='none';}
function deleteCurrentSong(){if(confirm("Usunąć?"))document.getElementById('deleteForm').submit();}

let tInt=null,totSec=0,isRun=false,actMsg="";
function setTimer(){totSec=parseInt(document.getElementById('timer-input').value)*60;updTimer();sendConferenceData();}
function updTimer(){let m=Math.floor(Math.abs(totSec)/60),s=Math.abs(totSec)%60,fmt=(totSec<0?"-":"")+(m<10?"0":"")+m+":"+(s<10?"0":"")+s;document.getElementById('timer-val').innerText=fmt;document.getElementById('timer-val').style.color=totSec<=0?"#cf6679":"var(--text-main)";return{text:fmt,color:totSec<=0?"red":"white"};}
function startTimer(){if(isRun)return;isRun=true;tInt=setInterval(()=>{totSec--;updTimer();sendConferenceData();},1000);}
function stopTimer(){isRun=false;clearInterval(tInt);}
function resetTimer(){stopTimer();setTimer();}
function sendConfMessage(){actMsg=document.getElementById('conf-msg').value;sendConferenceData();}
function clearConfMessage(){actMsg="";document.getElementById('conf-msg').value="";sendConferenceData();}
function sendConferenceData(){let d=updTimer();fetch('/send_text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:'conference',timer:d.text,timer_color:d.color,message:actMsg})});}

function exportToPDF() {
    if (!setlist || setlist.length === 0) {
        alert("Setlista jest pusta! Dodaj najpierw piosenki.");
        return;
    }

    if (window.pywebview) {
        const cleanSetlist = JSON.parse(JSON.stringify(setlist));

        window.pywebview.api.save_setlist_html(cleanSetlist).then(response => {
            if (response.status === 'ok') {
                console.log(response.message);
            } else if (response.status === 'error') {
                alert("Błąd po stronie aplikacji: " + response.message);
            } else if (response.status === 'cancelled') {
                console.log("Anulowano zapis.");
            }
        }).catch(err => {
            alert("Krytyczny błąd komunikacji JS->Python: " + err);
        });
    } else {
        fetch('/print_setlist', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(setlist)
        }).then(r => r.text()).then(h => {
            const w = window.open('', '_blank');
            w.document.write(h);
            w.document.close();
        });
    }
}
function saveBackupDesktop() {
    if (window.pywebview) {
        window.pywebview.api.save_backup().then(response => {
            if (response.status === 'ok') {
                alert("Baza została zapisana!");
            } else if (response.status === 'error') {
                alert("Błąd: " + response.message);
            }
        });
    } else {
        window.location.href = "/export_songs";
    }
}

socket.on('refresh_logo', function() { 
    var logo = document.getElementById('control-logo'); 
    if(window.SERVER_DATA && window.SERVER_DATA.logoUrl) {
        logo.src = window.SERVER_DATA.logoUrl + "?v=" + new Date().getTime(); 
    }
});
// --- INICJALIZACJA DRAG & DROP W SETLIŚCIE ---
document.addEventListener('DOMContentLoaded', () => {
    const setlistContainer = document.getElementById('setlist-container');
    
    if (setlistContainer) {
        new Sortable(setlistContainer, {
            animation: 150, // Płynna animacja przesuwania pozostałych kafelków
            handle: '.drag-handle', // Przeciągamy tylko łapiąc za ikonę ☰
            ghostClass: 'sortable-ghost',
            onEnd: function (evt) {
                if (evt.oldIndex === evt.newIndex) return;
                
                const movedItem = setlist.splice(evt.oldIndex, 1)[0];
                setlist.splice(evt.newIndex, 0, movedItem);
                
                if (currentSetIndex === evt.oldIndex) {
                    currentSetIndex = evt.newIndex;
                } else if (currentSetIndex > evt.oldIndex && currentSetIndex <= evt.newIndex) {
                    currentSetIndex--;
                } else if (currentSetIndex < evt.oldIndex && currentSetIndex >= evt.newIndex) {
                    currentSetIndex++;
                }

                updateServerState();
                renderSetlist();

                // --- DODAJ TEN FRAGMENT ---
                // Odświeża panel Live (i przelicza przejścia), jeśli jakakolwiek piosenka jest włączona
                if (currentSetIndex !== -1) {
                    selectForLive(currentSetIndex);
                }
                // --------------------------
            }
        });
    }
});