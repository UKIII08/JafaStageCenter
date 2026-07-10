var socket = io();

// --- I18N: uses shared translations from i18n.js ---
function setLanguage(lang) {
    initI18n(lang);
    socket.emit('set_language', {lang: lang});
    filterLibrary();
}

// --- THEME LOGIC ---
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const newTheme = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// --- AUDIO PAD LOGIC (Web Audio API) ---
const padElA = document.getElementById('pad-player-a');
const padElB = document.getElementById('pad-player-b');

let audioCtx = null;
let padNodes = new Map(); // element -> { source, gain }
let currentPadEl = null;
let currentPadKey = null;
let isPadPlaying = false;
let globalPadVolume = 0.5;

let padDebounceTimer = null;
const PAD_DELAY_MS = 2000;

// Jedna konwencja enharmoniczna w całej aplikacji (jak TRANSPOSE_LOOKUP na serwerze
// i NOTES w band_member): krzyżyki dla C#/F#, bemole dla Eb/Ab/Bb.
const KEY_MAP = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'];
const NOTE_TO_PC = {
    'C':0, 'C#':1, 'DB':1, 'D':2, 'D#':3, 'EB':3, 'E':4, 'FB':4, 'E#':5,
    'F':5, 'F#':6, 'GB':6, 'G':7, 'G#':8, 'AB':8, 'A':9, 'A#':10, 'BB':10,
    'B':11, 'CB':11, 'H':11, 'B#':0,
    'CIS':1, 'DIS':3, 'ES':3, 'FIS':6, 'GIS':8, 'AS':8, 'AIS':10, 'HIS':0
};

// ── Szyny wyjściowe: pady i metronom mają osobne busy, które można
//    kierować na różne kanały interfejsu audio (albo wspólnie w stereo).
var AudioRouting = {
    built: false,
    maxCh: 2,
    merger: null,
    padBus: null,
    metroBus: null,
    padPanner: null,
    metroPanner: null,
    padChannels: (function(){ try { return JSON.parse(localStorage.getItem('padChannels')) || [0,1]; } catch(e){ return [0,1]; } })(),
    metroChannels: (function(){ try { return JSON.parse(localStorage.getItem('metroChannels')) || [0,1]; } catch(e){ return [0,1]; } })(),
    // Podział L/P na zwykłym stereo (bez interfejsu) — pady L, metronom P,
    // rozdzielasz przejściówką jack → 2× mono.
    stereoSplit: localStorage.getItem('stereoSplit') === '1',
    outputDeviceId: localStorage.getItem('audioOutId') || ''
};

function buildAudioGraph(ctx) {
    if (AudioRouting.built) return;
    AudioRouting.maxCh = ctx.destination.maxChannelCount || 2;
    AudioRouting.padBus = ctx.createGain();
    AudioRouting.metroBus = ctx.createGain();
    // Panery do podziału L/P na zwykłym stereo (gdy brak interfejsu wielokan.)
    if (typeof ctx.createStereoPanner === 'function') {
        AudioRouting.padPanner = ctx.createStereoPanner();
        AudioRouting.metroPanner = ctx.createStereoPanner();
    }
    if (AudioRouting.maxCh > 2) {
        try {
            ctx.destination.channelCountMode = 'explicit';
            ctx.destination.channelInterpretation = 'discrete';
            ctx.destination.channelCount = AudioRouting.maxCh;
        } catch (e) {}
        AudioRouting.merger = ctx.createChannelMerger(AudioRouting.maxCh);
        AudioRouting.merger.connect(ctx.destination);
    }
    AudioRouting.built = true;
    wireAudioBuses(ctx);
    // Wybrane wyjście (interfejs) — jeśli setSinkId wspierane
    if (AudioRouting.outputDeviceId && typeof ctx.setSinkId === 'function') {
        ctx.setSinkId(AudioRouting.outputDeviceId).catch(function(){});
    }
}

function connectBusToChannels(ctx, bus, channels) {
    var sp = ctx.createChannelSplitter(2);
    bus.connect(sp);
    var a = Math.min(channels[0], AudioRouting.maxCh - 1);
    var b = Math.min(channels[1], AudioRouting.maxCh - 1);
    sp.connect(AudioRouting.merger, 0, a);
    sp.connect(AudioRouting.merger, 1, b);
}

// (Prze)podłącza busy do wyjścia — wołane przy zmianie kanałów / trybu.
function wireAudioBuses(ctx) {
    if (!AudioRouting.padBus) return;
    try { AudioRouting.padBus.disconnect(); } catch (e) {}
    try { AudioRouting.metroBus.disconnect(); } catch (e) {}
    if (AudioRouting.padPanner) { try { AudioRouting.padPanner.disconnect(); } catch (e) {} }
    if (AudioRouting.metroPanner) { try { AudioRouting.metroPanner.disconnect(); } catch (e) {} }

    if (AudioRouting.stereoSplit && AudioRouting.padPanner) {
        // Podział L/P: pady twardo na lewo, metronom twardo na prawo.
        // Ma PRIORYTET nad mergerem — działa na zwykłym stereo, a na karcie
        // wielokanałowej trafia na kanały wyjściowe 0/1. Dzięki temu wybór
        // „Pady L / Metronom P" jest zawsze respektowany, także gdy sterownik
        // raportuje >2 kanały (Realtek 5.1/7.1, HDMI itd.).
        AudioRouting.padPanner.pan.value = -1;
        AudioRouting.metroPanner.pan.value = 1;
        AudioRouting.padBus.connect(AudioRouting.padPanner);
        AudioRouting.padPanner.connect(ctx.destination);
        AudioRouting.metroBus.connect(AudioRouting.metroPanner);
        AudioRouting.metroPanner.connect(ctx.destination);
    } else if (AudioRouting.merger) {
        // Interfejs wielokanałowy — kieruj na wybrane pary kanałów
        connectBusToChannels(ctx, AudioRouting.padBus, AudioRouting.padChannels);
        connectBusToChannels(ctx, AudioRouting.metroBus, AudioRouting.metroChannels);
    } else {
        // Zwykłe stereo, razem (wyzeruj panery na wszelki wypadek)
        if (AudioRouting.padPanner) AudioRouting.padPanner.pan.value = 0;
        if (AudioRouting.metroPanner) AudioRouting.metroPanner.pan.value = 0;
        AudioRouting.padBus.connect(ctx.destination);
        AudioRouting.metroBus.connect(ctx.destination);
    }
}

window.setStereoSplit = function (on) {
    AudioRouting.stereoSplit = !!on;
    localStorage.setItem('stereoSplit', AudioRouting.stereoSplit ? '1' : '0');
    if (audioCtx) wireAudioBuses(audioCtx);
    if (typeof populateAudioRoutingUI === 'function') populateAudioRoutingUI();
};

function ensureAudioCtx() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') audioCtx.resume();
    buildAudioGraph(audioCtx);
    return audioCtx;
}

function getPadNode(el) {
    if (padNodes.has(el)) return padNodes.get(el);
    const ctx = ensureAudioCtx();
    const source = ctx.createMediaElementSource(el);
    const gain = ctx.createGain();
    gain.gain.value = 0;
    source.connect(gain);
    gain.connect(AudioRouting.padBus);   // pady → szyna padów
    const node = { source, gain };
    padNodes.set(el, node);
    return node;
}

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

    // Restore collapsed-library state (desktop only; CSS ignores it on mobile)
    if (localStorage.getItem('libraryCollapsed') === '1') {
        var lib = document.getElementById('col-library');
        if (lib) lib.classList.add('collapsed');
    }
});

// Zwijanie/rozwijanie biblioteki — gdy set gotowy, oddaje szerokość panelowi live
function toggleLibrary() {
    var lib = document.getElementById('col-library');
    if (!lib) return;
    var collapsed = lib.classList.toggle('collapsed');
    localStorage.setItem('libraryCollapsed', collapsed ? '1' : '0');
}

// Nazwy plików padów używają WYŁĄCZNIE krzyżyków (C#, D#, F#, G#, A#) — to
// historyczna konwencja tej aplikacji i pod nią użytkownicy mają nazwane pliki.
// (Notacja mieszana C#/Eb/... dotyczy tylko wyświetlania tonacji i akordów.)
const PAD_SHARP_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

function keyToPitchClass(k) {
    if(!k) return null;
    let match = k.match(/^([AaEe][Ss](?![uU])|[A-Ha-h][#b]?(?:is|IS|Is)?)(.*)$/);
    if(!match) return null;
    let isLowerRoot = match[1][0] === match[1][0].toLowerCase();
    let pc = NOTE_TO_PC[match[1].toUpperCase()];
    if(pc === undefined) return null;

    let suffix = match[2].trim().toLowerCase();
    let isMinor = isLowerRoot || (suffix.startsWith('m') && !suffix.startsWith('maj'));
    if(isMinor) pc = (pc + 3) % 12; // pad w tonacji równoległej durowej
    return pc;
}

// Zwraca nazwę pliku pada (krzyżyki) dla danej tonacji.
function normalizeKey(k) {
    let pc = keyToPitchClass(k);
    return pc === null ? null : PAD_SHARP_NAMES[pc];
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
        ensureAudioCtx();
        btn.classList.add('active');
        status.innerText = "ON";
        if(currentSetIndex !== -1 && setlist[currentSetIndex]) {
            let rawKey = calculateTransposedKey(setlist[currentSetIndex].key, setlist[currentSetIndex].transpose);
            playPad(rawKey);
        }
    } else {
        btn.classList.remove('active');
        status.innerText = "OFF";
        currentPadKey = null;
        fadeOutAllPads();
    }
}

function updatePadVolume(slider) {
    let val = parseFloat(slider.value);
    globalPadVolume = val;

    if(currentPadEl && !currentPadEl.paused && audioCtx) {
        const node = padNodes.get(currentPadEl);
        if (node) {
            node.gain.gain.cancelScheduledValues(audioCtx.currentTime);
            node.gain.gain.setTargetAtTime(globalPadVolume, audioCtx.currentTime, 0.1);
        }
    }

    const percentage = (val - slider.min) / (slider.max - slider.min) * 100;
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const accentColor = isDark ? '#3B82F6' : '#3B82F6';
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

// Krzywa equal-power (sin przy narastaniu, cos przy opadaniu) — suma mocy obu
// padów podczas crossfade'u jest stała, bez dołka głośności w środku przejścia.
// setValueCurveAtTime sam ustawia wartość startową (curve[0]), więc NIE wolno
// przed nim wołać setValueAtTime na tym samym czasie — inaczej rzuca
// NotSupportedError. Wywołujący robi tylko cancelScheduledValues(startTime).
function scheduleFade(gainParam, from, to, startTime, durationSec) {
    const steps = 48;
    const curve = new Float32Array(steps);
    const rising = to > from;
    for (let i = 0; i < steps; i++) {
        const x = i / (steps - 1);
        const shape = rising ? Math.sin(x * Math.PI / 2) : (1 - Math.cos(x * Math.PI / 2));
        curve[i] = from + (to - from) * shape;
    }
    try {
        gainParam.setValueCurveAtTime(curve, startTime, durationSec);
    } catch (e) {
        // Fallback: ustaw punkt startowy nieco wcześniej, potem rampa liniowa
        gainParam.setValueAtTime(from, startTime);
        gainParam.linearRampToValueAtTime(to, startTime + durationSec);
    }
}

function playPad(rawKey, fadeOutSec = 4) {
    if(!isPadPlaying) return;
    let targetKey = normalizeKey(rawKey);
    if(!targetKey) return;

    const ctx = ensureAudioCtx();
    const now = ctx.currentTime;

    if (targetKey === currentPadKey && currentPadEl && !currentPadEl.paused) {
        const node = getPadNode(currentPadEl);
        node.gain.gain.cancelScheduledValues(now);
        node.gain.gain.setTargetAtTime(globalPadVolume, now, 0.3);
        return;
    }

    currentPadKey = targetKey;

    // encodeURIComponent: '#' w nazwie pliku (C#.mp3) inaczej ucina URL jako fragment
    let filename = `/static/pads/${encodeURIComponent(targetKey)}.mp3`;
    let active = currentPadEl;
    let next = (active === padElA) ? padElB : padElA;

    console.log(`[PAD] Przełączam na ${targetKey}`);
    document.getElementById('pad-status-text').innerText = targetKey;

    const nextNode = getPadNode(next);
    nextNode.gain.gain.cancelScheduledValues(now);
    nextNode.gain.gain.setValueAtTime(0, now);

    next.src = filename;
    next.volume = 1;

    next.play().then(() => {
        if (!isPadPlaying) {
            next.pause();
            next.currentTime = 0;
            return;
        }
        if (currentPadKey !== targetKey) return;

        const t = ctx.currentTime;
        currentPadEl = next;

        // Nowy pad narasta (equal-power). Bez setValueAtTime — krzywa sama
        // ustala punkt startowy, a jawne zdarzenie w t rozbiłoby setValueCurve.
        nextNode.gain.gain.cancelScheduledValues(t);
        scheduleFade(nextNode.gain.gain, 0, globalPadVolume, t, fadeOutSec);

        // Stary pad opada (equal-power) — równoległy crossfade o stałej mocy
        if (active && active !== next && !active.paused) {
            const activeNode = getPadNode(active);
            const currentVol = activeNode.gain.gain.value;
            activeNode.gain.gain.cancelScheduledValues(t);
            scheduleFade(activeNode.gain.gain, currentVol, 0, t, fadeOutSec);
            setTimeout(() => {
                if (currentPadEl !== active) {
                    active.pause();
                    active.currentTime = 0;
                }
            }, fadeOutSec * 1000 + 200);
        }

    }).catch(e => console.error("Pad play error:", e));
}

function fadeOutAllPads(duration = 3) {
    if (!audioCtx) {
        [padElA, padElB].forEach(p => { p.pause(); p.currentTime = 0; });
        currentPadEl = null;
        return;
    }
    const now = audioCtx.currentTime;
    [padElA, padElB].forEach(el => {
        if (!el.paused) {
            const node = getPadNode(el);
            const vol = node.gain.gain.value;
            node.gain.gain.cancelScheduledValues(now);
            scheduleFade(node.gain.gain, vol, 0, now, duration);
            setTimeout(() => {
                el.pause();
                el.currentTime = 0;
            }, duration * 1000 + 200);
        }
    });
    currentPadEl = null;
}

// --- SYNCHRONIZACJA ---
socket.on('connect', function() {
    console.log('Połączono z serwerem via SocketIO');
});

socket.on('sync_state_to_client', function(data) {
    console.log('Otrzymano synchronizację:', data);

    let needsRender = false;

    if (data.setlist && JSON.stringify(setlist) !== JSON.stringify(data.setlist)) {
        setlist = data.setlist;
        needsRender = true;
    }

    if (data.current_index !== undefined && data.current_index !== currentSetIndex) {
        currentSetIndex = data.current_index;
        needsRender = true;
    }

    // Restore blackout state from server (tylko klasa .active — bez zmiany
    // tekstu, żeby nie skakała wysokość sekcji).
    if (data.is_blackout !== undefined) {
        isBlackoutActive = data.is_blackout;
        document.querySelectorAll('button[onclick="blackout()"]').forEach(btn => {
            btn.classList.toggle('active', isBlackoutActive);
        });
    }

    if (needsRender) {
        renderSetlist();
    }

    if (data.current_index !== undefined && data.current_index !== -1 && setlist[data.current_index] && needsRender) {
        selectForLive(data.current_index, false);
    } else if (data.current_index === -1) {
        var lh = document.getElementById('live-header');
        if (lh) lh.style.display = 'none';
        var sc = document.getElementById('slides-container');
        if (sc) sc.innerHTML = '';
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

        // Podgląd live na panelu głównym — z auto-dopasowaniem, żeby długie
        // zwrotki nie były przycinane przez sztywne 16:9 + overflow:hidden.
        if (data.is_blackout) {
            const txt = (currentLang === 'en') ? "SCREEN BLACKED OUT" : "EKRAN WYGASZONY";
            previewBox.innerText = txt;
        } else if (window.updateLocalPreview) {
            window.updateLocalPreview(textContent);
        } else {
            previewBox.innerText = textContent;
        }

        // Tile active state is managed by click handlers directly — no socket sync needed
    } else if (data.mode === 'blackout') {
        const txt = (currentLang === 'en') ? "SCREEN BLACKED OUT" : "EKRAN WYGASZONY";
        previewBox.innerText = txt;
    } else if (data.mode === 'logo') {
        previewBox.innerText = "LOGO";
    }
});
let currentPresentationSlides = [];
let currentSlideIndex = 0;
// Wszystkie wgrane prezentacje: [{ id, name, slides }]. Przełączamy między
// nimi bez ponownego wgrywania — jeden PDF pokazujemy, potem kolejny itd.
let loadedPresentations = [];
let activePresentationId = null;

// Funkcja wgrywająca PDF
function uploadPdfPresentation() {
    const fileInput = document.getElementById('pdf-upload');
    if (!fileInput.files[0]) return alert(t('alert_choose_pdf'));

    const btn = document.querySelector('.conf-upload-btn');
    if (btn) { btn.disabled = true; btn.dataset.prev = btn.innerText; btn.innerText = '…'; }

    const formData = new FormData();
    formData.append("pres_file", fileInput.files[0]);

    fetch('/upload_presentation', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.status !== 'ok') {
            alert(data.message);
        }
        // reset pola wyboru pliku, by można było wgrać kolejny
        fileInput.value = '';
        const lbl = document.getElementById('pdf-file-label');
        if (lbl) lbl.innerText = t('pdf_ph');
    })
    .catch(() => alert(t('alert_upload_failed') || 'Upload failed.'))
    .finally(() => {
        if (btn) { btn.disabled = false; btn.innerText = btn.dataset.prev || t('upload_btn'); }
    });
}

// Odbieranie slajdów od serwera — dodajemy do listy i od razu aktywujemy
socket.on('presentation_ready', function(data) {
    if (!data || !data.slides || !data.slides.length) return;
    var pres = { id: data.id, name: data.name || 'PDF', slides: data.slides };
    // jeśli ten sam id już był (np. odświeżenie), podmień
    var existing = loadedPresentations.findIndex(function(p) { return p.id === pres.id; });
    if (existing >= 0) loadedPresentations[existing] = pres;
    else loadedPresentations.push(pres);
    selectPresentation(pres.id, false);
    renderPresentationList();
});

// Ustawia daną prezentację jako aktywną (do sterowania i pokazywania)
function selectPresentation(id, autoShow) {
    var pres = loadedPresentations.find(function(p) { return p.id === id; });
    if (!pres) return;
    activePresentationId = id;
    currentPresentationSlides = pres.slides;
    currentSlideIndex = 0;
    var counter = document.getElementById('slide-counter');
    if (counter) counter.innerText = `1 / ${currentPresentationSlides.length}`;
    renderPresentationList();
    if (autoShow) sendPresentationState();
}

// Pokazuje wybraną prezentację na ekranach (aktywuje + wypycha slajd)
function showPresentation(id) {
    selectPresentation(id, true);
}

function removePresentation(id) {
    fetch('/delete_presentation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id })
    }).catch(function() {});
    loadedPresentations = loadedPresentations.filter(function(p) { return p.id !== id; });
    if (activePresentationId === id) {
        activePresentationId = null;
        currentPresentationSlides = [];
        currentSlideIndex = 0;
        var counter = document.getElementById('slide-counter');
        if (counter) counter.innerText = '0 / 0';
    }
    renderPresentationList();
}

function renderPresentationList() {
    var list = document.getElementById('pdf-list');
    if (!list) return;
    list.innerHTML = '';
    if (loadedPresentations.length === 0) {
        var emptyMsg = t('no_pdf_msg') || 'Brak wgranych prezentacji.';
        list.innerHTML = `<div style="color:var(--text-muted); font-size:0.8rem; text-align:center; padding:10px; border:1px dashed var(--border-color); border-radius:6px;">${emptyMsg}</div>`;
        return;
    }
    var btnShow = t('show_btn') || 'Pokaż';
    loadedPresentations.forEach(function(pres) {
        var item = document.createElement('div');
        item.style.display = 'flex';
        item.style.alignItems = 'center';
        item.style.gap = '8px';
        item.style.padding = '8px 12px';
        item.style.borderRadius = '6px';
        var isActive = pres.id === activePresentationId;
        item.style.background = isActive ? 'var(--accent-primary-soft, rgba(59,130,246,0.15))' : 'var(--bg-element)';
        item.style.border = isActive ? '1px solid var(--accent-primary, #3B82F6)' : '1px solid var(--border-color)';

        var safeName = String(pres.name).replace(/</g, '&lt;').replace(/>/g, '&gt;');
        var shortName = safeName.length > 28 ? safeName.substring(0, 28) + '…' : safeName;

        item.innerHTML = `
            <div style="flex-grow:1; font-size:0.8rem; color:var(--text-main); overflow:hidden; white-space:nowrap; text-overflow:ellipsis;" title="${safeName}">
                📄 ${shortName} <span style="color:var(--text-muted); font-size:0.7rem;">(${pres.slides.length})</span>
            </div>
            <button class="action-btn" style="background:var(--accent-success); padding:6px 12px; font-size:0.75rem;" onclick="showPresentation('${pres.id}')">${btnShow}</button>
            <button class="btn-sm" style="background:var(--accent-danger); color:white; border:none; padding:6px 10px; font-weight:bold; border-radius:6px;" onclick="removePresentation('${pres.id}')">✕</button>
        `;
        list.appendChild(item);
    });
}

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
    if (!currentPresentationSlides || currentPresentationSlides.length === 0) return;
    confMode = 'presentation';   // od teraz konferencja pokazuje slajdy
    pushConference();
}

// JEDNO źródło prawdy dla ekranów w trybie konferencji. Timer, wiadomość,
// blackout i zmiana slajdu — wszystko przechodzi tędy, więc tik zegara NIE
// nadpisuje już prezentacji trybem 'conference'.
function pushConference() {
    var d = (typeof updTimer === 'function') ? updTimer() : { text: '00:00', color: 'white' };
    var payload = {
        timer: d.text, timer_color: d.color,
        message: (typeof actMsg !== 'undefined') ? actMsg : '',
        blackout: isBlackoutActive
    };
    if (confMode === 'presentation' && currentPresentationSlides && currentPresentationSlides.length) {
        payload.mode = 'presentation';
        payload.slide_url = currentPresentationSlides[currentSlideIndex];
        payload.next_slide_url = (currentSlideIndex + 1 < currentPresentationSlides.length) ? currentPresentationSlides[currentSlideIndex + 1] : null;
    } else if (confMode === 'canva' && confCanvaUrl) {
        payload.mode = 'canva';
        payload.url = confCanvaUrl;
    } else {
        payload.mode = 'conference';
    }
    fetch('/send_text', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
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
        const btnShow = translations[currentLang].show_btn || "Pokaż";

        item.innerHTML = `
            <div style="flex-grow: 1; font-size: 0.75rem; color: var(--text-muted); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-family: monospace;" title="${link}">
                ${label} ${index + 1}: ${shortLink}
            </div>
            <button class="action-btn" style="background:var(--accent-success); padding: 6px 12px; font-size: 0.75rem;" onclick="sendSpecificCanvaLink(${index})">${btnShow}</button>
            <button class="btn-sm setlist-remove" style="background:transparent; color:var(--text-tertiary); border:none; padding: 6px 10px; font-weight: bold;" onclick="removeCanvaLink(${index})">✕</button>
        `;
        list.appendChild(item);
    });
}

// Zamienia dowolny link Canva na poprawny adres do OSADZENIA (embed).
// Publiczny link ma postać /design/{ID}/{TOKEN}/view?... — zachowujemy ID+token
// i dajemy /view?embed. Bez tokenu (link 'edit' z paska adresu) osadzenie i tak
// wymaga publicznego udostępnienia w Canvie ("Każdy z linkiem może wyświetlać").
function canvaEmbedUrl(raw) {
    var link = (raw || '').trim();
    if (!/canva\.com\/design\//i.test(link)) return link;          // nie Canva — zostaw
    var m = link.match(/canva\.com\/design\/([^\/?#]+)(?:\/([^\/?#]+))?/i);
    if (!m) return link;
    var base = 'https://www.canva.com/design/' + m[1];
    var token = m[2];
    if (token && ['edit', 'view', 'watch', 'present', 'preview'].indexOf(token.toLowerCase()) === -1) {
        base += '/' + token;
    }
    return base + '/view?embed';
}

function addCanvaLink() {
    let input = document.getElementById('new-canva-link');
    let link = input.value.trim();
    if (!link) return;

    link = canvaEmbedUrl(link);

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
    appMode = 'conference';
    confMode = 'canva';
    confCanvaUrl = canvaEmbedUrl(link); // naprawia też starsze, zapisane linki
    pushConference();
}

// Inicjalizacja listy po załadowaniu skryptu
// Opis wybranego silnika przejść w ustawieniach
function updateEngineDesc() {
    var sel = document.getElementById('trans-engine-select');
    if (!sel) return;
    ['v2', 'v3', 'v4'].forEach(function (v) {
        var el = document.getElementById('engine-desc-' + v);
        if (el) el.style.display = (v === sel.value) ? 'block' : 'none';
    });
}

document.addEventListener('DOMContentLoaded', () => {
    updateEngineDesc();
    renderCanvaLinks();
    renderPresentationList();
});
// Asekuracyjne wywołanie (gdyby skrypt załadował się po DOMContentLoaded)
setTimeout(() => { renderCanvaLinks(); renderPresentationList(); }, 500);

function updateServerState() {
    socket.emit('client_update_state', {
        setlist: setlist,
        current_index: currentSetIndex
    });
}

function switchMode(m){document.querySelectorAll('.mode-container').forEach(c=>c.classList.remove('active'));document.querySelectorAll('.segmented-control button, .mode-btn').forEach(b=>b.classList.remove('active'));if(m==='worship'){appMode='worship';var wm=document.getElementById('worship-mode');if(wm)wm.classList.add('active');var wb=document.querySelector('button[onclick="switchMode(\'worship\')"]');if(wb)wb.classList.add('active');resendCurrentSlide();}else{appMode='conference';var cm=document.getElementById('conference-mode');if(cm)cm.classList.add('active');var cb=document.querySelector('button[onclick="switchMode(\'conference\')"]');if(cb)cb.classList.add('active');confMode='timer';pushConference();}}
function resendCurrentSlide(){var active=document.querySelector('.slide-btn.active');if(active){active.click();}else if(currentLiveState){goLiveSection(currentLiveState.c,currentLiveState.n,currentLiveState.forceTrans,currentLiveState.nextTrans);}else{fetch('/send_text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({logo:true})});}}
function openQRModal(){document.getElementById('qrModal').style.display='flex';}
function closeQRModal(){document.getElementById('qrModal').style.display='none';}

function toggleHttps(enabled){
    fetch('/toggle_https', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !!enabled })
    }).then(r => r.json()).then(function(res){
        if (res.status !== 'ok') { showToast((res.message || 'Błąd') ); return; }
        var en = (localStorage.getItem('appLang') || 'pl') === 'en';
        if (enabled && res.can_https === false) {
            alert(en
                ? 'This app build cannot create an HTTPS certificate (missing library). The tuner mic on phones needs an updated build. Nothing was broken — the app keeps working over HTTP.'
                : 'Ta wersja aplikacji nie potrafi utworzyć certyfikatu HTTPS (brak biblioteki). Mikrofon stroika na telefonie wymaga zaktualizowanego builda. Nic się nie zepsuło — apka działa dalej po HTTP.');
            return;
        }
        if (res.restart_required) {
            alert(en
                ? (enabled
                    ? 'HTTPS enabled. Restart the app to apply it. On each phone, open the app and accept the security certificate once — then the tuner mic will work.'
                    : 'HTTPS disabled. Restart the app to go back to a normal (HTTP) connection.')
                : (enabled
                    ? 'HTTPS włączony. Zrestartuj aplikację, żeby zadziałał. Na każdym telefonie otwórz aplikację i raz zaakceptuj certyfikat — wtedy mikrofon stroika będzie działał.'
                    : 'HTTPS wyłączony. Zrestartuj aplikację, żeby wrócić do zwykłego połączenia (HTTP).'));
        }
    }).catch(function(){ showToast('Błąd połączenia'); });
}

function openSettingsModal(){
    document.getElementById('settingsModal').style.display='flex';
    
    const storedState = localStorage.getItem('transitionsEnabled');
    document.getElementById('trans-toggle').checked = (storedState !== 'false');
    const keyState = localStorage.getItem('keyDetectionEnabled');
    document.getElementById('key-detect-toggle').checked = (keyState !== 'false');

    // Stan przełącznika HTTPS z serwera (plik-marker).
    fetch('/https_status').then(r => r.json()).then(function(s) {
        var el = document.getElementById('https-toggle');
        if (el) el.checked = !!s.enabled;
    }).catch(function(){});

    const currentTheme = document.documentElement.getAttribute('data-theme');
    document.getElementById('theme-toggle').checked = (currentTheme === 'dark');
    
    document.getElementById('lang-select').value = localStorage.getItem('appLang') || 'pl';

    renderShortcuts();
    if (typeof refreshMidiSelectUI === 'function') refreshMidiSelectUI();
    if (typeof populateAudioRoutingUI === 'function') populateAudioRoutingUI();
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

const iosPrompt = document.getElementById('ios-install-prompt');
if (iosPrompt && isIos()) {
    const fsBtn = document.getElementById('fs-btn-desktop');
    if(fsBtn) fsBtn.style.display = 'none';
    if (!isInStandaloneMode()) {
        iosPrompt.style.display = 'block';
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
                alert(t('alert_fullscreen_ios'));
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

// ═══════════════════════════════════════════════════════════════
//  KEYBOARD SHORTCUTS — konfigurowalne, pod hardware'owy sterownik
//  (kontroler emulujący klawiaturę/HID mapuje się 1:1 na te akcje)
// ═══════════════════════════════════════════════════════════════

// Akcje, które można podpiąć pod klawisz. `run` wywołuje istniejące funkcje.
const SHORTCUT_ACTIONS = [
    { id: 'next_section',   run: () => navigateSlides(1) },
    { id: 'prev_section',   run: () => navigateSlides(-1) },
    { id: 'next_song',      run: () => goToNextSong() },
    { id: 'prev_song',      run: () => goToPrevSong() },
    { id: 'blackout',       run: () => blackout() },
    { id: 'logo',           run: () => showLogo() },
    { id: 'pad_toggle',     run: () => togglePad() },
    { id: 'resend',         run: () => resendCurrentSlide() },
    { id: 'transpose_up',   run: () => adjustLiveTrans(1) },
    { id: 'transpose_down', run: () => adjustLiveTrans(-1) },
];

// Dwujęzyczne etykiety akcji (specyficzne dla panelu — trzymamy lokalnie)
const SHORTCUT_LABELS = {
    next_section:   { pl: 'Następny kafelek',        en: 'Next section' },
    prev_section:   { pl: 'Poprzedni kafelek',       en: 'Previous section' },
    next_song:      { pl: 'Następna piosenka',       en: 'Next song' },
    prev_song:      { pl: 'Poprzednia piosenka',     en: 'Previous song' },
    blackout:       { pl: 'Wygaś ekran (Blackout)',  en: 'Blackout' },
    logo:           { pl: 'Pokaż logo',              en: 'Show logo' },
    pad_toggle:     { pl: 'Pad (wł / wył)',          en: 'Toggle pad' },
    resend:         { pl: 'Wyślij slajd ponownie',   en: 'Resend slide' },
    transpose_up:   { pl: 'Transpozycja +1',         en: 'Transpose +1' },
    transpose_down: { pl: 'Transpozycja −1',         en: 'Transpose −1' },
};

// Domyślne skróty. Nawigacja na klawiszach nazwanych (strzałki, PgUp/Dn –
// nie kolidują z pisaniem), a akcje na literach ZAWSZE w kombinacji z
// Ctrl+Alt (bare litery są zabronione — patrz startShortcutCapture).
const DEFAULT_KEYMAP = {
    next_section: 'ArrowRight',
    prev_section: 'ArrowLeft',
    next_song: 'PageDown',
    prev_song: 'PageUp',
    blackout: 'Ctrl+Alt+b',
    logo: 'Ctrl+Alt+l',
    pad_toggle: 'Ctrl+Alt+p',
    resend: 'Ctrl+Alt+Enter',
    transpose_up: 'Ctrl+Alt+ArrowUp',
    transpose_down: 'Ctrl+Alt+ArrowDown',
};

// Czy binding wymaga modyfikatora? Tak dla znaków drukowalnych (litery/cyfry),
// nie dla klawiszy nazwanych (ArrowRight, PageDown, F13, Enter...).
function keyNeedsModifier(ev) {
    return ev.key.length === 1; // pojedynczy znak drukowalny
}
const MODIFIER_KEYS = ['Control', 'Alt', 'Shift', 'Meta', 'AltGraph'];

let shortcutKeymap = {};
function loadKeymap() {
    shortcutKeymap = Object.assign({}, DEFAULT_KEYMAP);
    try {
        var saved = JSON.parse(localStorage.getItem('shortcutKeymap') || '{}');
        Object.assign(shortcutKeymap, saved);
    } catch (e) {}
}
function saveKeymap() { localStorage.setItem('shortcutKeymap', JSON.stringify(shortcutKeymap)); }
loadKeymap();

// Ta sama funkcja przy przechwytywaniu i dopasowaniu → gwarancja spójności,
// niezależnie od dokładnej normalizacji przeglądarki.
function eventToKeyString(e) {
    var k = e.key;
    if (k === ' ') k = 'Space';
    // Znaki drukowalne małą literą → Shift zawsze jako JAWNY modyfikator,
    // by "Ctrl+Shift+l" nie mieszało się z "Ctrl+l". Stała kolejność modyfikatorów.
    if (k.length === 1) k = k.toLowerCase();
    var mods = [];
    if (e.ctrlKey) mods.push('Ctrl');
    if (e.altKey) mods.push('Alt');
    if (e.shiftKey) mods.push('Shift');
    if (e.metaKey) mods.push('Meta');
    mods.push(k);
    return mods.join('+');
}

// Ładny podpis klawisza dla UI (np. "Ctrl+Alt+b" → "Ctrl + Alt + B")
function prettyKey(ks) {
    if (!ks) return '—';
    var parts = ks.split('+');
    // ostatni segment to właściwy klawisz; wcześniejsze to modyfikatory
    var key = parts.pop();
    key = key
        .replace('ArrowRight', '→').replace('ArrowLeft', '←')
        .replace('ArrowUp', '↑').replace('ArrowDown', '↓')
        .replace('PageDown', 'PgDn').replace('PageUp', 'PgUp');
    if (key.length === 1) key = key.toUpperCase(); // litera na wielką dla czytelności
    parts.push(key);
    return parts.join(' + ');
}

let shortcutCaptureId = null; // aktywne przechwytywanie (id akcji) — blokuje dispatcher

document.addEventListener('keydown', (e) => {
    // Nie przechwytuj podczas pisania w polach
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (shortcutCaptureId) return; // trwa remapowanie — obsługiwane osobno

    var confEl = document.getElementById('conference-mode');
    const isConferenceActive = confEl ? confEl.classList.contains('active') : false;
    const keyStr = eventToKeyString(e);

    // Tryb konferencji: strzałki sterują slajdami PDF
    if (isConferenceActive) {
        if (keyStr === 'ArrowRight' || keyStr === 'ArrowDown') { e.preventDefault(); changeSlide(1); return; }
        if (keyStr === 'ArrowLeft' || keyStr === 'ArrowUp') { e.preventDefault(); changeSlide(-1); return; }
    }

    // Dopasuj do keymapy
    for (var i = 0; i < SHORTCUT_ACTIONS.length; i++) {
        if (shortcutKeymap[SHORTCUT_ACTIONS[i].id] === keyStr) {
            e.preventDefault();
            SHORTCUT_ACTIONS[i].run();
            return;
        }
    }

    // Fallback: pionowe strzałki też nawigują sekcjami w Uwielbieniu
    if (!isConferenceActive) {
        if (keyStr === 'ArrowDown') { e.preventDefault(); navigateSlides(1); }
        else if (keyStr === 'ArrowUp') { e.preventDefault(); navigateSlides(-1); }
    }
});

// Przechwytywanie klawisza przy remapowaniu (faza capture, by wyprzedzić dispatcher)
function startShortcutCapture(actionId, btn) {
    shortcutCaptureId = actionId;
    btn.classList.add('capturing');
    var promptTxt = currentLang === 'en' ? 'Press a combination…' : 'Naciśnij kombinację…';
    btn.textContent = promptTxt;
    function onKey(ev) {
        ev.preventDefault(); ev.stopPropagation();
        if (ev.key === 'Escape') { finish(); return; }
        // Czekaj na właściwy klawisz — ignoruj samotne modyfikatory
        if (MODIFIER_KEYS.indexOf(ev.key) !== -1) return;
        // Bare litera/cyfra bez modyfikatora — zabroniona (kolidowałaby z pisaniem)
        if (keyNeedsModifier(ev) && !ev.ctrlKey && !ev.altKey && !ev.metaKey) {
            btn.classList.add('capture-warn');
            btn.textContent = currentLang === 'en' ? 'Add Ctrl / Alt…' : 'Dodaj Ctrl / Alt…';
            return; // nie kończ — czekaj na poprawną kombinację
        }
        btn.classList.remove('capture-warn');
        var ks = eventToKeyString(ev);
        // Usuń ten klawisz z innych akcji, by uniknąć duplikatów
        for (var id in shortcutKeymap) { if (shortcutKeymap[id] === ks) delete shortcutKeymap[id]; }
        shortcutKeymap[actionId] = ks;
        saveKeymap();
        finish();
    }
    function finish() {
        window.removeEventListener('keydown', onKey, true);
        shortcutCaptureId = null;
        renderShortcuts();
    }
    window.addEventListener('keydown', onKey, true);
}

function resetShortcuts() {
    shortcutKeymap = Object.assign({}, DEFAULT_KEYMAP);
    saveKeymap();
    renderShortcuts();
}

function renderShortcuts() {
    var list = document.getElementById('shortcuts-list');
    if (!list) return;
    var lang = currentLang || 'pl';
    list.innerHTML = SHORTCUT_ACTIONS.map(function (a) {
        var label = (SHORTCUT_LABELS[a.id] || {})[lang] || a.id;
        var key = shortcutKeymap[a.id];
        return '<div class="shortcut-row">' +
                 '<span class="shortcut-label">' + label + '</span>' +
                 '<button type="button" class="shortcut-key-btn" onclick="startShortcutCapture(\'' + a.id + '\', this)">' +
                    '<kbd>' + prettyKey(key) + '</kbd>' +
                 '</button>' +
               '</div>';
    }).join('');
}

// ── Hands-free worship flow (tylko gdy metronom WŁĄCZONY) ──
// Jeden pedał (next) prowadzi: ostatni slajd → [pedał] przejście (metronom
// milknie, grasz na luzie) → [pedał] intro następnej piosenki (metronom
// wraca, tekst jeszcze się NIE pokazuje) → [pedał] pokazuje się tekst.
var worshipFlow = null;      // null | 'transition' | 'armed'
var flowArmedTile = null;    // kafelek uzbrojony (tekst ukryty)
var metroWasOnBeforeTransition = false; // czy metronom grał przed przejściem (by go przywrócić)

function resetWorshipFlow() {
    worshipFlow = null;
    flowArmedTile = null;
    document.querySelectorAll('.slide-btn.armed').forEach(function (t) { t.classList.remove('armed'); });
}

// Uzbraja pierwszy slajd bieżącej piosenki: podświetla, ale NIE wysyła na ekrany
function armFirstSlide() {
    var reals = document.querySelectorAll('.slide-btn:not(.transition-tile)');
    if (!reals.length) { worshipFlow = null; return; }
    var tile = reals[0];
    document.querySelectorAll('.slide-btn').forEach(function (x) { x.classList.remove('active'); });
    tile.classList.add('active');
    tile.classList.add('armed');
    activeSectionIdx = 0;
    flowArmedTile = tile;
    worshipFlow = 'armed';
}

function navigateSlides(direction) {
    var metroOn = (typeof isMetronomeOn === 'function') && isMetronomeOn();
    // Flow przejść (transition + uzbrojenie intro) działa zawsze, gdy przejścia
    // są włączone — niezależnie od metronomu. Metronom milknie/wraca tylko jako
    // efekt uboczny, jeśli akurat grał.
    var inFlow = metroOn || worshipFlow !== null || transitionsEnabled;

    if (direction === 1 && inFlow) {
        // 1) Uzbrojony slajd → teraz pokaż tekst
        if (worshipFlow === 'armed' && flowArmedTile) {
            var t = flowArmedTile;
            resetWorshipFlow();
            t.click(); // wysyła tekst na ekrany
            return;
        }
        // 2) Na przejściu → przejdź do następnej piosenki, wróć metronom, uzbrój intro
        if (worshipFlow === 'transition') {
            worshipFlow = null;
            if (currentSetIndex < setlist.length - 1) {
                selectForLive(currentSetIndex + 1);
                setTimeout(function () {
                    // Metronom wraca na nowe tempo tylko jeśli grał przed przejściem.
                    if (metroWasOnBeforeTransition && typeof metroSetActive === 'function') metroSetActive(true);
                    armFirstSlide();
                }, 60);
            }
            return;
        }
        // 3) Zwykły krok w obrębie piosenki; na ostatnim slajdzie → wejdź w przejście
        var reals = Array.from(document.querySelectorAll('.slide-btn:not(.transition-tile)'));
        var ai = reals.findIndex(function (s) { return s.classList.contains('active'); });
        if (ai === -1) { if (reals[0]) reals[0].click(); return; }
        if (ai + 1 < reals.length) { reals[ai + 1].click(); return; } // następny slajd tej samej piosenki
        // ostatni slajd piosenki:
        var trans = document.querySelector('.slide-btn.transition-tile');
        if (trans && currentSetIndex < setlist.length - 1) {
            trans.click(); // onclick przejścia: metronom milknie + worshipFlow='transition'
            return;
        }
        if (currentSetIndex < setlist.length - 1) {
            // brak kafelka przejścia → przejdź i uzbrój (metronom gra dalej)
            selectForLive(currentSetIndex + 1);
            setTimeout(function () { armFirstSlide(); }, 60);
            return;
        }
        return; // ostatni slajd ostatniej piosenki
    }

    // ── Zachowanie normalne (metronom wyłączony, brak flow) ──
    if (direction === -1) resetWorshipFlow();
    const slides = Array.from(document.querySelectorAll('.slide-btn:not(.transition-tile)'));
    if (slides.length === 0) return;
    const activeIndex = slides.findIndex(s => s.classList.contains('active'));
    if (activeIndex === -1) { slides[0].click(); return; }
    const nextIndex = activeIndex + direction;
    if (nextIndex >= 0 && nextIndex < slides.length) { slides[nextIndex].click(); }
    else if (nextIndex >= slides.length) {
        if (currentSetIndex < setlist.length - 1) {
            selectForLive(currentSetIndex + 1);
            setTimeout(() => {
                  const newSlides = document.querySelectorAll('.slide-btn:not(.transition-tile)');
                  if(newSlides.length > 0) newSlides[0].click();
            }, 50);
        }
    }
    else if (nextIndex < 0) {
        if (currentSetIndex > 0) {
            selectForLive(currentSetIndex - 1);
            setTimeout(() => {
                const newSlides = document.querySelectorAll('.slide-btn:not(.transition-tile)');
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

function goToPrevSong() {
    if (currentSetIndex > 0) {
        selectForLive(currentSetIndex - 1);
        setTimeout(() => {
            const newSlides = document.querySelectorAll('.slide-btn:not(.transition-tile)');
            if (newSlides.length > 0) newSlides[0].click();
        }, 100);
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
let currentSections = [];
let sectionsSortable = null;
let activeSectionIdx = -1;

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

const CHORD_VALID_RE = /^([AaEe][Ss](?![uU])|[A-Ha-h][#b]?(?:is|IS|Is)?)(.*)$/;
function isValidChordStr(s) {
    if (!s || !s.trim()) return false;
    s = s.trim().replace(/-+$/, '').trim();
    if (s.includes('/')) {
        const parts = s.split('/', 2);
        return isValidChordStr(parts[0]) && (isValidChordStr(parts[1]) || !parts[1].trim());
    }
    const m = s.match(CHORD_VALID_RE);
    if (!m) return false;
    const root = m[1];
    return root && 'ABCDEFGH'.includes(root[0].toUpperCase());
}

function validateChords(contentId, statusId) {
    const text = document.getElementById(contentId).value;
    const statusEl = document.getElementById(statusId);
    if (!statusEl) return;
    const matches = text.match(/\[(.*?)\]/g);
    if (!matches || matches.length === 0) {
        statusEl.innerHTML = '';
        return;
    }
    const invalid = [];
    const valid = [];
    for (const m of matches) {
        const chord = m.slice(1, -1).trim();
        if (!chord) continue;
        if (isValidChordStr(chord)) {
            valid.push(chord);
        } else {
            invalid.push(chord);
        }
    }
    if (invalid.length > 0) {
        statusEl.innerHTML = '<span style="color:#ff6b6b;">Nierozpoznane akordy: <b>' + invalid.map(c => '[' + c + ']').join(', ') + '</b></span>';
    } else {
        statusEl.innerHTML = '<span style="color:#00b894;">' + valid.length + ' akordów — wszystkie poprawne</span>';
    }
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
            const keyBadge = s.key ? `<span class="lib-key-badge">${s.key}</span>` : '';
            d.innerHTML = `
                <summary class="lib-summary">
                    <div class="lib-title-row"><b>${s.title}</b>${keyBadge}</div>
                    <div style="display:flex;gap:5px;">
                        <button class="btn-icon" onclick="event.preventDefault(); openEditModal(${s.id})" style="background:none; border:none; cursor:pointer; color:var(--text-muted);">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        </button>
                        <button class="btn-sm lib-add-btn" onclick="event.preventDefault(); addToSetlist(${s.id}, this)">${btnText}</button>
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
        btnElement.innerText = "OK";
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
        var lh2 = document.getElementById('live-header'); if (lh2) lh2.style.display='none';
        var sc2 = document.getElementById('slides-container'); if (sc2) sc2.innerHTML='';
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
            
            <button class="btn-sm setlist-remove" onclick="event.stopPropagation(); removeFromSetlist(${index})" style="background:transparent; border:none; color:var(--text-tertiary); padding: 8px;">✕</button>
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
    const match = originalKey.match(/^([AaEe][Ss](?![uU])|[A-Ha-h][#b]?(?:is|IS|Is)?)(.*)$/);
    if (!match) return originalKey;
    let root = match[1]; let suffix = match[2]; let isLower = (root[0] === root[0].toLowerCase());
    let val = NOTE_TO_PC[root.toUpperCase()];
    if (val === undefined) return originalKey;
    let newVal = (val + shift) % 12; if (newVal < 0) newVal += 12;
    let newRoot = KEY_MAP[newVal]; if (isLower) newRoot = newRoot.toLowerCase();
    return newRoot + suffix;
}

function getParallelKey(key) {
    if (!key || key === '-' || key === 'N/A') return '';
    var match = key.match(/^([AaEe][Ss](?![uU])|[A-Ha-h][#b]?(?:is|IS|Is)?)\s*(m|min)?$/);
    if (!match) return '';
    var isMinor = !!(match[2]) || match[1][0] === match[1][0].toLowerCase();
    var val = NOTE_TO_PC[match[1].toUpperCase()];
    if (val === undefined) return '';
    if (isMinor) {
        return KEY_MAP[(val + 3) % 12];
    } else {
        return KEY_MAP[(val + 9) % 12] + 'm';
    }
}

function updateParallelKey() {
    var el = document.getElementById('parallel-key');
    if (!el) return;
    var key = document.getElementById('live-key')?.innerText;
    var parallel = getParallelKey(key);
    el.textContent = parallel ? '(' + parallel + ')' : '';
}

function parseSongSections(raw) {
    if (!raw) return [];
    
    // ZMIANA KLUCZOWA:
    // Regex /\n\s*\n/ oznacza: "Enter, potem opcjonalne spacje, potem kolejny Enter".
    // To gwarantuje, że podział nastąpi TYLKO w miejscach pustych linii.
    // Jeśli piosenka nie ma pustych linii, zostanie potraktowana jako 1 kafelek.
    raw = raw.replace(/(\n\s*){2,}\n/g, '\n\n');
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
    if (i < 0 || i >= setlist.length) return;
    currentSetIndex=i;
    activeSectionIdx = -1;
    renderSetlist();
    
    if (broadcast) {
        updateServerState();
    }

    const item=setlist[i];
    // '' (nie 'block') → wraca do arkusza CSS, który steruje layoutem
    // (flex-row na desktopie, contents w landscape). Inline 'block' bił CSS.
    document.getElementById('live-header').style.display='';
    document.getElementById('current-title').innerText=item.title;
    document.getElementById('current-trans').innerText=(item.transpose>0?"+":"")+item.transpose;
    
    let finalKey = calculateTransposedKey(item.key, item.transpose);
    document.getElementById('live-key').innerText = finalKey;
    updateParallelKey();
    document.getElementById('live-bpm').innerText = item.bpm ? item.bpm : "-";
    if (typeof metroSongChanged === 'function') metroSongChanged(i); // BPM + ducking przy zmianie

    if(isPadPlaying) {
       triggerDebouncedPad(finalKey);
    }

    if (item.customSections && Array.isArray(item.customSections)) {
        var allSections = parseSongSections(item.content);
        var sectionMap = {};
        allSections.forEach(function(s) {
            if (!sectionMap[s.label]) sectionMap[s.label] = [];
            sectionMap[s.label].push(s);
        });
        var usedCount = {};
        currentSections = item.customSections.map(function(label) {
            if (!usedCount[label]) usedCount[label] = 0;
            var pool = sectionMap[label];
            if (pool && usedCount[label] < pool.length) {
                return pool[usedCount[label]++];
            } else if (pool && pool.length > 0) {
                return { label: label, content: pool[0].content };
            }
            return { label: label, content: '' };
        });
    } else {
        currentSections = parseSongSections(item.content);
    }
    renderSectionTiles(i);
}

function saveSectionsToSetlist() {
    if (currentSetIndex >= 0 && currentSetIndex < setlist.length) {
        var defaultSections = parseSongSections(setlist[currentSetIndex].content);
        var defaultLabels = defaultSections.map(function(s) { return s.label; });
        var currentLabels = currentSections.map(function(s) { return s.label; });
        var isDefault = currentLabels.length === defaultLabels.length && currentLabels.every(function(l, i) { return l === defaultLabels[i]; });
        if (isDefault) {
            delete setlist[currentSetIndex].customSections;
        } else {
            setlist[currentSetIndex].customSections = currentLabels;
        }
    }
}

function duplicateSection(idx) {
    if (idx < 0 || idx >= currentSections.length) return;
    var copy = { label: currentSections[idx].label, content: currentSections[idx].content };
    currentSections.splice(idx + 1, 0, copy);
    saveSectionsToSetlist();
    renderSectionTiles(currentSetIndex);
}

function removeDuplicatedSection(idx) {
    if (currentSections.length <= 1) return;
    currentSections.splice(idx, 1);
    saveSectionsToSetlist();
    renderSectionTiles(currentSetIndex);
}

function renderSectionTiles(songIdx) {
    const item = setlist[songIdx];
    const sc = document.getElementById('slides-container');
    sc.innerHTML = "";

    currentSections.forEach((sec, idx) => {
        const b = document.createElement('div');
        b.className = 'slide-btn';
        b.setAttribute('data-sec-idx', idx);
        b.innerHTML = `<span class="slide-label">${sec.label}</span><span>${sec.content.replace(/\[.*?\]/g,"").substring(0,40)}...</span><span class="slide-actions"><button class="slide-dup-btn" title="Duplikuj" onclick="event.stopPropagation(); duplicateSection(${idx});">+</button><button class="slide-del-btn" title="Usuń" onclick="event.stopPropagation(); removeDuplicatedSection(${idx});">×</button></span>`;
        b.onclick = () => {
            if (typeof resetWorshipFlow === 'function') resetWorshipFlow(); // klik kasuje stan flow
            document.querySelectorAll('.slide-btn').forEach(x => x.classList.remove('active'));
            b.classList.add('active');
            activeSectionIdx = idx;

            var nextContent = "";
            var nextTrans = item.transpose;

            if (idx + 1 < currentSections.length) {
                nextContent = currentSections[idx + 1].content;
            } else if (songIdx + 1 < setlist.length) {
                var nextSongSecs = parseSongSections(setlist[songIdx + 1].content);
                if (nextSongSecs.length > 0) {
                    nextContent = nextSongSecs[0].content;
                    nextTrans = setlist[songIdx + 1].transpose;
                }
            }

            goLiveSection(sec.content, nextContent, null, nextTrans);
        };
        sc.appendChild(b);
    });

    if (songIdx < setlist.length - 1 && transitionsEnabled) {
        const nextItem = setlist[songIdx + 1];
        const chordRegex = /\[(.*?)\]/g;
        const currentMatches = item.content.match(chordRegex);
        const nextMatches = nextItem.content.match(chordRegex);
        const lastChordRaw = currentMatches ? currentMatches[currentMatches.length - 1] : null;
        const firstChordRaw = nextMatches ? nextMatches[0] : null;
        if (lastChordRaw && firstChordRaw) {
            const btn = document.createElement('div'); btn.className = 'slide-btn transition-tile';
            btn.innerHTML = `<span class="slide-label">Transition</span><span id="trans-preview" style="font-size:0.7rem;color:var(--text-muted);">Ładowanie...</span>`;

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
                        var previewBox = btn.querySelector('#trans-preview');
                        if (previewBox) previewBox.innerText = `${data.debug_start} → ${data.debug_end}`;
                        btn.dataset.transitionHtml = data.transition;
                    } else { if (btn.querySelector('#trans-preview')) btn.querySelector('#trans-preview').innerText = "Błąd"; }
                });
            };
            fetchTransition();
            btn.onclick = () => {
                document.querySelectorAll('.slide-btn').forEach(x => x.classList.remove('active')); btn.classList.add('active');
                activeSectionIdx = -1;

                // Wejście w przejście: kolejny klik przełączy na następną piosenkę
                // i uzbroi intro. Metronom (jeśli grał) milknie na czas przejścia
                // i wróci dopiero na intro następnej piosenki.
                metroWasOnBeforeTransition = (typeof isMetronomeOn === 'function' && isMetronomeOn());
                if (metroWasOnBeforeTransition) metroSetActive(false);
                worshipFlow = 'transition';

                if (isPadPlaying && songIdx < setlist.length - 1) {
                    var nextSong = setlist[songIdx + 1];
                    var nextKey = calculateTransposedKey(nextSong.key, nextSong.transpose);
                    setTimeout(() => { playPad(nextKey, 5); }, 8000);
                }

                var nextContent = "";
                var nextTrans = nextItem.transpose;
                var nextSongSecs = parseSongSections(nextItem.content);
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

    if (sectionsSortable) sectionsSortable.destroy();
    if (typeof Sortable !== 'undefined') {
        sectionsSortable = new Sortable(sc, {
            animation: 150,
            handle: '.slide-label',
            filter: '.transition-tile',
            ghostClass: 'slide-ghost',
            onEnd: function(evt) {
                var el = currentSections.splice(evt.oldIndex, 1)[0];
                currentSections.splice(evt.newIndex, 0, el);
                saveSectionsToSetlist();
                renderSectionTiles(currentSetIndex);
            }
        });
    }
}

function adjustLiveTrans(a){
    if(currentSetIndex!==-1){
        let newVal = setlist[currentSetIndex].transpose + a;
        if (newVal < -12 || newVal > 12) return;
        setlist[currentSetIndex].transpose = newVal;
        document.getElementById('current-trans').innerText = (setlist[currentSetIndex].transpose>0?"+":"")+setlist[currentSetIndex].transpose;
        let finalKey = calculateTransposedKey(setlist[currentSetIndex].key, setlist[currentSetIndex].transpose);
        document.getElementById('live-key').innerText = finalKey;
        updateParallelKey();

        if (isPadPlaying) {
            triggerDebouncedPad(finalKey);
        }

        // Re-send the currently active slide with the new transposition
        var activeBtn = document.querySelector('.slide-btn.active');
        if (activeBtn) {
            activeBtn.click();
        } else {
            resendCurrentSlide();
        }
    }
}

let isBlackoutActive = false;
let currentLiveState = { c: '', n: '', forceTrans: null, nextTrans: null };

// Tryb aplikacji: 'worship' albo 'conference'. Decyduje, jak zachowuje się
// blackout i co odświeża zegar konferencyjny.
let appMode = 'worship';
// W obrębie konferencji: co jest realnie POKAZYWANE na ekranach.
let confMode = 'timer';          // 'timer' | 'presentation' | 'canva'
let confCanvaUrl = null;

function blackout() {
    isBlackoutActive = !isBlackoutActive;

    // Prosty przełącznik: tylko klasa .active (inwersja), bez zmiany tekstu ani
    // rozmiaru — dłuższy napis zawijał się i skakała wysokość całej sekcji.
    document.querySelectorAll('button[onclick="blackout()"]').forEach(btn => {
        btn.classList.toggle('active', isBlackoutActive);
    });

    // W konferencji blackout gasi TYLKO projektor (audiencję) i zachowuje
    // aktualny tryb (prezentacja/zegar) — nie przełącza na worship, żeby ekran
    // ZESPOŁU nie migał i slajdy nie znikały.
    if (appMode === 'conference') {
        pushConference();
        return;
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
    clearLogoActive();

    let t = (forceTrans !== null) ? forceTrans : setlist[currentSetIndex].transpose;
    let nt = (nextTrans !== null) ? nextTrans : t; 
    
    let currentKey = document.getElementById('live-key') ? document.getElementById('live-key').innerText : '';
    let currentBpm = setlist[currentSetIndex] ? setlist[currentSetIndex].bpm : '';
    let songTitle = setlist[currentSetIndex] ? setlist[currentSetIndex].title : '';

    fetch('/send_text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: c,
            next_text: n,
            transpose: t,
            next_transpose: nt,
            key: currentKey,
            bpm: currentBpm,
            song_title: songTitle,
            current_index: currentSetIndex,
            setlist: setlist,
            blackout: isBlackoutActive
        })
    });
    
    // Operator zawsze widzi u siebie na podglądzie tekst, żeby wiedzieć co wysłał zespołowi
    var _previewClean = c.replace(/\[.*?\]/g, "");
    if (window.updateLocalPreview) window.updateLocalPreview(_previewClean);
    else document.getElementById('live-preview-box').innerText = _previewClean;
}
let isLogoActive = false;
function showLogo(){
    isLogoActive = !isLogoActive;
    const btns = document.querySelectorAll('button[onclick="showLogo()"]');
    if (isLogoActive) {
        fetch('/send_text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({logo:true})});
        document.getElementById('live-preview-box').innerText="LOGO";
        btns.forEach(b => b.classList.add('active'));
    } else {
        // Klik ponownie = zdejmij logo i wróć do aktualnego slajdu live.
        btns.forEach(b => b.classList.remove('active'));
        resendCurrentSlide();
    }
}
// Wybranie slajdu na żywo zawsze wyłącza tryb logo (i podświetlenie przycisku).
function clearLogoActive(){
    if (!isLogoActive) return;
    isLogoActive = false;
    document.querySelectorAll('button[onclick="showLogo()"]').forEach(b => b.classList.remove('active'));
}

function saveSetlistHistory() {
    if (!setlist.length) { showToast(t('alert_empty_setlist'), 'error'); return; }
    var dateStr = new Date().toLocaleDateString('pl-PL');
    var name = prompt(t('setlist_history_name') || 'Nazwa setlisty:', dateStr);
    if (name === null) return;
    if (!name.trim()) name = dateStr;
    var songs = setlist.map(function(s) {
        var item = { id: s.id, title: s.title, key: s.key || '', bpm: s.bpm || 0, transpose: s.transpose || 0 };
        if (s.customSections) item.customSections = s.customSections;
        return item;
    });
    fetch('/api/setlist-history', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ name: name, date: new Date().toISOString().split('T')[0], songs: songs })
    }).then(function(r) { return r.json(); }).then(function() {
        showToast(t('setlist_saved') || 'Setlista zapisana!', 'success');
    }).catch(function() {
        showToast(t('alert_error') || 'Błąd', 'error');
    });
}

function showSetlistHistory() {
    fetch('/api/setlist-history').then(function(r) { return r.json(); }).then(function(items) {
        if (!items.length) { showToast(t('no_history') || 'Brak zapisanych setlist', 'info'); return; }
        var html = '<div style="max-height:60vh;overflow-y:auto;">';
        items.forEach(function(h) {
            html += '<div style="padding:12px;border-bottom:1px solid var(--border-default);display:flex;align-items:center;gap:8px;">' +
                '<div style="flex:1;cursor:pointer;" onclick="loadSetlistHistory(' + h.id + ')">' +
                '<div style="font-weight:600;">' + (h.name || h.date) + '</div>' +
                '<div style="font-size:0.8em;color:var(--text-tertiary);">' + h.date + ' — ' + h.song_count + ' ' + (t('songs_count') || 'piosenek') + '</div>' +
                '<div style="font-size:0.75em;color:var(--text-muted);margin-top:4px;">' +
                h.songs.map(function(s) { return s.title; }).join(', ') + '</div></div>' +
                '<button onclick="deleteSetlistHistory(' + h.id + ',this)" style="flex-shrink:0;padding:6px 8px;border-radius:8px;background:transparent;color:var(--accent-danger);border:1px solid var(--accent-danger);cursor:pointer;font-size:0.75em;">' +
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button></div>';
        });
        html += '</div>';
        var modal = document.createElement('div');
        modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = '<div style="background:var(--bg-elevated);border-radius:14px;padding:24px;max-width:500px;width:90%;border:1px solid var(--border-default);">' +
            '<h3 style="margin:0 0 16px;">' + (t('setlist_history_title') || 'Historia setlist') + '</h3>' + html +
            '<button onclick="this.closest(\'div[style*=fixed]\').remove()" style="margin-top:12px;padding:8px 20px;border-radius:8px;background:var(--bg-surface);color:var(--text-primary);border:1px solid var(--border-default);cursor:pointer;">Zamknij</button></div>';
        document.body.appendChild(modal);
    });
}

function deleteSetlistHistory(id, btn) {
    event.stopPropagation();
    fetch('/api/setlist-history/' + id, { method: 'DELETE' }).then(function() {
        var row = btn.closest('div[style*="border-bottom"]');
        row.remove();
        var container = document.querySelector('div[style*="fixed"][style*="z-index:99999"] div[style*="max-height"]');
        if (container && !container.children.length) {
            document.querySelector('div[style*="fixed"][style*="z-index:99999"]').remove();
            showToast(t('no_history') || 'Brak zapisanych setlist', 'info');
        }
    });
}

function loadSetlistHistory(id) {
    fetch('/api/setlist-history/' + id).then(function(r) { return r.json(); }).then(function(data) {
        if (data.error) return;
        setlist = [];
        data.songs.forEach(function(s) {
            var libSong = library.find(function(ls) { return ls.title === s.title; }) || library.find(function(ls) { return ls.id === s.id; });
            if (libSong) {
                var entry = Object.assign({}, libSong, { transpose: s.transpose || 0 });
                if (s.customSections) entry.customSections = s.customSections;
                setlist.push(entry);
            }
        });
        renderSetlist();
        if (setlist.length) selectForLive(0);
        updateServerState();
        document.querySelectorAll('div[style*="fixed"][style*="z-index:99999"]').forEach(function(el) { el.remove(); });
        showToast((t('setlist_loaded') || 'Setlista wczytana!') + ' (' + setlist.length + ' ' + (t('songs_count') || 'piosenek') + ')', 'success');
    });
}

function encodeSetlistData() {
    return setlist.map(function(s) {
        var item = { t: s.title, k: s.key || '', b: s.bpm || 0, tr: s.transpose || 0 };
        if (s.customSections) item.s = s.customSections;
        return item;
    });
}

function decodeSetlistData(songs) {
    var result = [];
    var missing = [];
    songs.forEach(function(s) {
        var title = s.t || s.title;
        var libSong = library.find(function(ls) { return ls.title === title; });
        if (libSong) {
            var entry = Object.assign({}, libSong, { transpose: s.tr !== undefined ? s.tr : (s.transpose || 0) });
            var sections = s.s || s.customSections;
            if (sections && Array.isArray(sections)) {
                if (typeof sections[0] === 'string') {
                    entry.customSections = sections;
                } else if (sections[0] && sections[0].label) {
                    entry.customSections = sections.map(function(sec) { return sec.label; });
                }
            }
            result.push(entry);
        } else {
            missing.push(title);
        }
    });
    return { songs: result, missing: missing };
}

function shareSetlist() {
    if (!setlist.length) { showToast(t('alert_empty_setlist'), 'error'); return; }
    var data = encodeSetlistData();
    var json = JSON.stringify(data);
    var encoded = 'JAFA:' + btoa(unescape(encodeURIComponent(json)));

    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = '<div style="background:var(--bg-elevated);border-radius:14px;padding:24px;max-width:500px;width:90%;border:1px solid var(--border-default);text-align:center;">' +
        '<h3 style="margin:0 0 8px;">' + (t('share_code_title') || 'Udostępnij setlistę') + '</h3>' +
        '<p style="margin:0 0 12px;color:var(--text-tertiary);font-size:0.85em;">' + (t('share_code_msg') || 'Skopiuj kod i wyślij drugiej osobie, lub niech zeskanuje QR:') + '</p>' +
        '<div style="display:flex;justify-content:center;margin-bottom:12px;"><img id="share-qr-img" src="/qr_setlist?data=' + encodeURIComponent(encoded) + '" style="width:200px;height:200px;border-radius:10px;background:white;padding:4px;" onerror="this.style.display=\'none\'"></div>' +
        '<textarea id="share-code-text" readonly style="width:100%;height:60px;font-size:0.75rem;font-family:monospace;background:var(--bg-surface);color:var(--text-primary);border:1px solid var(--border-default);border-radius:8px;padding:8px;resize:none;word-break:break-all;">' + encoded + '</textarea>' +
        '<div style="display:flex;gap:8px;justify-content:center;margin-top:12px;">' +
        '<button onclick="var ta=document.getElementById(\'share-code-text\');ta.select();document.execCommand(\'copy\');showToast(t(\'copied\')||\'Skopiowano!\',\'success\')" style="padding:8px 20px;border-radius:8px;background:var(--accent-primary);color:white;border:none;cursor:pointer;font-weight:600;">' + (t('copy_btn') || 'Kopiuj kod') + '</button>' +
        '<button onclick="this.closest(\'div[style*=fixed]\').remove()" style="padding:8px 20px;border-radius:8px;background:var(--bg-surface);color:var(--text-primary);border:1px solid var(--border-default);cursor:pointer;">OK</button></div></div>';
    document.body.appendChild(modal);
}

function importSetlistCode() {
    var code = window.prompt(t('import_code_prompt') || 'Wklej kod setlisty (JAFA:...):');
    if (!code) return;
    code = code.trim();

    if (code.startsWith('JAFA:')) {
        try {
            var json = decodeURIComponent(escape(atob(code.substring(5))));
            var songs = JSON.parse(json);
            var result = decodeSetlistData(songs);
            setlist = result.songs;
            renderSetlist();
            if (setlist.length) selectForLive(0);
            updateServerState();
            var msg = (t('setlist_loaded') || 'Setlista wczytana!') + ' (' + setlist.length + ' ' + (t('songs_count') || 'piosenek') + ')';
            if (result.missing.length) {
                msg += '\n' + (t('songs_not_found') || 'Nie znaleziono:') + ' ' + result.missing.join(', ');
            }
            showToast(msg, result.missing.length ? 'warning' : 'success');
        } catch(e) {
            showToast(t('import_code_invalid') || 'Nieprawidłowy kod setlisty', 'error');
        }
        return;
    }

    fetch('/api/setlist-share/' + code.toUpperCase()).then(function(r) {
        if (!r.ok) throw new Error('not found');
        return r.json();
    }).then(function(data) {
        if (data.error) { showToast(t('import_code_not_found') || 'Nie znaleziono', 'error'); return; }
        var result = decodeSetlistData(data.songs);
        setlist = result.songs;
        renderSetlist();
        if (setlist.length) selectForLive(0);
        updateServerState();
        var msg = (t('setlist_loaded') || 'Setlista wczytana!') + ' (' + setlist.length + ' ' + (t('songs_count') || 'piosenek') + ')';
        if (result.missing.length) msg += '\n' + (t('songs_not_found') || 'Nie znaleziono:') + ' ' + result.missing.join(', ');
        showToast(msg, result.missing.length ? 'warning' : 'success');
    }).catch(function() { showToast(t('import_code_not_found') || 'Nie znaleziono setlisty', 'error'); });
}

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
function deleteCurrentSong(){if(confirm(t('alert_delete_confirm')))document.getElementById('deleteForm').submit();}

let tInt=null,totSec=0,isRun=false,actMsg="";
// Zegar/wiadomość mówcy idą osobnym kanałem (/conf_timer → 'timer_update'),
// NIE przez pushConference — dzięki temu tik zegara nie przebudowuje rzutnika
// (prezentacja zostaje) i nie trafia na ekrany muzyków (band_member).
function pushTimer(){
    var d = (typeof updTimer === 'function') ? updTimer() : { text:'00:00', color:'white' };
    fetch('/conf_timer', { method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ timer: d.text, timer_color: d.color, message: actMsg || '' }) });
}
function setTimer(){var v=parseInt(document.getElementById('timer-input').value);totSec=(isNaN(v)||v<0)?0:v*60;pushTimer();}
function updTimer(){let m=Math.floor(Math.abs(totSec)/60),s=Math.abs(totSec)%60,fmt=(totSec<0?"-":"")+(m<10?"0":"")+m+":"+(s<10?"0":"")+s;document.getElementById('timer-val').innerText=fmt;document.getElementById('timer-val').style.color=totSec<0?"var(--red)":"var(--text-primary)";return{text:fmt,color:totSec<0?"red":"white"};}
function startTimer(){if(isRun)return;isRun=true;tInt=setInterval(()=>{totSec--;pushTimer();},1000);}
function stopTimer(){isRun=false;clearInterval(tInt);}
function resetTimer(){stopTimer();setTimer();}
function sendConfMessage(){actMsg=document.getElementById('conf-msg').value;pushTimer();}
function clearConfMessage(){actMsg="";document.getElementById('conf-msg').value="";pushTimer();}
// Zachowane dla zgodności — pełny „powrót do samego zegara".
function sendConferenceData(){appMode='conference';confMode='timer';pushConference();}

function exportToPDF() {
    if (!setlist || setlist.length === 0) {
        alert(t('alert_empty_setlist'));
        return;
    }

    if (window.pywebview) {
        const cleanSetlist = JSON.parse(JSON.stringify(setlist));

        window.pywebview.api.save_setlist_html(cleanSetlist).then(response => {
            if (response.status === 'ok') {
                console.log(response.message);
            } else if (response.status === 'error') {
                alert(t('alert_app_error') + response.message);
            } else if (response.status === 'cancelled') {
                console.log("Anulowano zapis.");
            }
        }).catch(err => {
            alert(t('alert_critical_error') + err);
        });
    } else {
        // Okno MUSI być otwarte synchronicznie w kontekście kliknięcia — inaczej
        // blokada popupów przeglądarki je zablokuje (window.open w .then() jest
        // traktowane jako nie-użytkownikowe).
        const w = window.open('', '_blank');
        if (!w) { alert(t('alert_popup_blocked')); return; }
        w.document.write('<!doctype html><meta charset="utf-8"><body style="font-family:sans-serif;padding:40px;color:#555">Generowanie PDF…</body>');
        fetch('/print_setlist', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(setlist)
        }).then(r => r.text()).then(h => {
            w.document.open(); w.document.write(h); w.document.close();
        }).catch(err => {
            try { w.document.body.innerHTML = 'Błąd generowania PDF: ' + err; } catch (e) {}
        });
    }
}
function exportLyricsPDF() {
    if (!setlist || setlist.length === 0) {
        alert(t('alert_empty_setlist'));
        return;
    }

    if (window.pywebview) {
        const cleanSetlist = JSON.parse(JSON.stringify(setlist));
        window.pywebview.api.save_lyrics_html(cleanSetlist).then(response => {
            if (response.status === 'ok') {
                console.log(response.message);
            } else if (response.status === 'error') {
                alert(t('alert_error') + ": " + response.message);
            }
        }).catch(err => {
            alert(t('alert_critical_error') + err);
        });
    } else {
        const w = window.open('', '_blank');
        if (!w) { alert(t('alert_popup_blocked')); return; }
        w.document.write('<!doctype html><meta charset="utf-8"><body style="font-family:sans-serif;padding:40px;color:#555">Generowanie PDF…</body>');
        fetch('/print_lyrics', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(setlist)
        }).then(r => r.text()).then(h => {
            w.document.open(); w.document.write(h); w.document.close();
        }).catch(err => {
            try { w.document.body.innerHTML = 'Błąd generowania PDF: ' + err; } catch (e) {}
        });
    }
}

function saveBackupDesktop() {
    if (window.pywebview) {
        window.pywebview.api.save_backup().then(response => {
            if (response.status === 'ok') {
                alert(t('alert_db_saved'));
            } else if (response.status === 'error') {
                alert(t('alert_error') + ": " + response.message);
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

// Auto-bracket helper: typing '[' in song textareas auto-inserts ']' and places cursor between
document.addEventListener('keydown', function(e) {
    if (e.key !== '[') return;
    const ta = e.target;
    if (ta.tagName !== 'TEXTAREA') return;
    if (ta.id !== 'add-content' && ta.id !== 'edit-content') return;

    e.preventDefault();
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const val = ta.value;
    ta.value = val.substring(0, start) + '[]' + val.substring(end);
    ta.selectionStart = ta.selectionEnd = start + 1;
    ta.dispatchEvent(new Event('input'));
});

// =============================================================================
// ONBOARDING / GUIDED TOUR SYSTEM
// =============================================================================
(function() {
    'use strict';

    // --- Inject onboarding CSS ---
    const onboardingStyleEl = document.createElement('style');
    onboardingStyleEl.textContent = `
        .onboarding-overlay {
            position: fixed;
            top: 0; left: 0;
            width: 100vw; height: 100vh;
            background: transparent;
            z-index: 99990;
            transition: opacity 0.4s ease;
            opacity: 0;
            pointer-events: none;
        }
        .onboarding-overlay.active {
            opacity: 1;
            pointer-events: auto;
        }
        .onboarding-spotlight {
            position: fixed;
            z-index: 99991;
            border-radius: 12px;
            background: transparent;
            box-shadow: 0 0 0 9999px rgba(4,6,11,0.86);
            transition: top 0.45s cubic-bezier(0.16,1,0.3,1), left 0.45s cubic-bezier(0.16,1,0.3,1), width 0.45s cubic-bezier(0.16,1,0.3,1), height 0.45s cubic-bezier(0.16,1,0.3,1);
            pointer-events: none;
        }
        .onboarding-spotlight::after {
            content: '';
            position: absolute;
            inset: -4px;
            border-radius: 16px;
            border: 1.5px solid var(--accent, #22D3EE);
            animation: onboarding-pulse 2.2s ease-in-out infinite;
        }
        @keyframes onboarding-pulse {
            0%, 100% { box-shadow: 0 0 12px var(--accent-glow, rgba(34,211,238,0.3)); opacity: 0.7; }
            50% { box-shadow: 0 0 26px var(--accent-glow, rgba(34,211,238,0.5)); opacity: 1; }
        }
        .onboarding-tooltip {
            position: absolute;
            max-width: 350px;
            background: var(--glass-bg, rgba(11,15,24,0.85));
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-default, rgba(255,255,255,0.08));
            border-radius: 18px;
            padding: 24px;
            box-shadow: 0 24px 70px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.05);
            z-index: 99992;
            opacity: 0;
            transform: translateY(10px) scale(0.98);
            transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.16,1,0.3,1);
            color: var(--text-primary, #EAF1F9);
            font-family: inherit;
        }
        .onboarding-tooltip.visible {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
        .onboarding-tooltip-arrow {
            position: absolute;
            width: 0; height: 0;
            border: 8px solid transparent;
        }
        .onboarding-tooltip-arrow.arrow-top {
            bottom: 100%;
            left: 24px;
            border-bottom-color: var(--glass-bg, rgba(11,15,24,0.85));
        }
        .onboarding-tooltip-arrow.arrow-bottom {
            top: 100%;
            left: 24px;
            border-top-color: var(--glass-bg, rgba(11,15,24,0.85));
        }
        .onboarding-tooltip-arrow.arrow-left {
            right: 100%;
            top: 24px;
            border-right-color: var(--glass-bg, rgba(11,15,24,0.85));
        }
        .onboarding-tooltip-arrow.arrow-right {
            left: 100%;
            top: 24px;
            border-left-color: var(--glass-bg, rgba(11,15,24,0.85));
        }
        .onboarding-step-counter {
            display: inline-block;
            background: var(--accent-subtle, rgba(34,211,238,0.1));
            color: var(--accent, #22D3EE);
            font-size: 11px;
            font-weight: 700;
            padding: 3px 11px;
            border-radius: 20px;
            margin-bottom: 12px;
            letter-spacing: 0.06em;
            border: 1px solid var(--accent-line, rgba(34,211,238,0.35));
        }
        .onboarding-tooltip h3 {
            margin: 0 0 8px 0;
            font-size: 17px;
            font-weight: 800;
            letter-spacing: -0.01em;
            color: var(--text-primary, #fff);
        }
        .onboarding-tooltip p {
            margin: 0 0 18px 0;
            font-size: 13.5px;
            line-height: 1.55;
            color: var(--text-secondary, #94A2B8);
        }
        .onboarding-btn-row {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .onboarding-btn-primary {
            background: linear-gradient(135deg, var(--accent-strong, #06B6D4), var(--accent, #22D3EE));
            color: #04121A;
            border: none;
            padding: 9px 22px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 800;
            cursor: pointer;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .onboarding-btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px var(--accent-glow, rgba(34,211,238,0.4));
        }
        .onboarding-btn-ghost {
            background: transparent;
            color: #b0b0b0;
            border: 1px solid rgba(255,255,255,0.1);
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: border-color 0.15s ease;
        }
        .onboarding-btn-ghost:hover {
            border-color: rgba(255,255,255,0.25);
            color: #e0e0e0;
        }
        .onboarding-btn-skip {
            background: none;
            border: none;
            color: #666;
            font-size: 11.5px;
            cursor: pointer;
            margin-left: auto;
            padding: 4px 8px;
            transition: color 0.15s ease;
        }
        .onboarding-btn-skip:hover {
            color: #999;
        }
    `;
    document.head.appendChild(onboardingStyleEl);

    // --- Step definitions ---
    var ONBOARDING_DEMO_SONG = 'Zwrotka 1\n[Am] Jedyny Krol, ktory [G]przyjal postac slugi\n[F] Jedyny Krol, ktory [Dm]sam unizyl sie\n[Am] Potezny wladca, ktory [G]oddal swoje zycie\n[F] aby mogl, [Dm] zyc jego lud \n\nRefren\n[Am] Oddal zycie, by zycie [Dm]dac\nodziany w majestat zamiast [Am/C]szat\nwsrod pogardy, wywyzsz[Fmaj7]ony objal [Amadd11/E] Tron';

    var onboardingDemoSongAdded = false;

    function onboardingAddDemoSong() {
        if (onboardingDemoSongAdded) return;
        onboardingDemoSongAdded = true;

        var existing = library.find(function(s) { return s.title === 'Jedyny Krol'; });
        if (existing) {
            setlist.push({ ...existing, transpose: 0 });
            renderSetlist();
            selectForLive(0);
            return;
        }

        var formData = new FormData();
        formData.append('title', 'Jedyny Krol');
        formData.append('content', ONBOARDING_DEMO_SONG);
        formData.append('key', 'Am');
        formData.append('bpm', '70');
        formData.append('input_notation', 'international');

        fetch('/add_song', { method: 'POST', body: formData, redirect: 'manual' })
            .then(function() {
                var maxId = library.reduce(function(m, s) { return Math.max(m, s.id); }, 0);
                var demo = { id: maxId + 1, title: 'Jedyny Krol', content: ONBOARDING_DEMO_SONG, key: 'Am', bpm: 70 };
                library.push(demo);
                renderLibrary();
                setlist.push({ ...demo, transpose: 0 });
                renderSetlist();
                selectForLive(0);
            });
    }

    const ONBOARDING_STEPS = [
        // ── Phase 1: Library & Setlist ──
        {
            target: '.plus-btn',
            get title() { return t('onb_step1_title'); },
            get text() { return t('onb_step1_text'); },
            position: 'bottom'
        },
        {
            target: '#searchBox',
            get title() { return t('onb_step2_title'); },
            get text() { return t('onb_step2_text'); },
            position: 'bottom'
        },
        {
            target: '#add-key-input',
            get title() { return t('onb_step3_title'); },
            get text() { return t('onb_step3_text'); },
            position: 'bottom',
            beforeShow: function() {
                openAddModal();
                var modal = document.getElementById('addModal');
                if (modal) modal.style.zIndex = '99989';
                setTimeout(function() {
                    document.getElementById('add-title').value = 'Jedyny Krol';
                    document.getElementById('add-content').value = ONBOARDING_DEMO_SONG;
                    liveKeyCheck('add-content', 'add-key-input');
                    validateChords('add-content', 'add-chord-status');
                    document.getElementById('add-key-input').placeholder = 'Am';
                }, 200);
            },
            afterHide: function() {
                document.getElementById('add-title').value = '';
                document.getElementById('add-content').value = '';
                document.getElementById('add-key-input').value = '';
                document.getElementById('add-key-input').placeholder = 'Key';
                var bpmInput = document.getElementById('add-bpm-input');
                if (bpmInput) bpmInput.value = '';
                var status = document.getElementById('add-chord-status');
                if (status) status.innerHTML = '';
                var modal = document.getElementById('addModal');
                if (modal) modal.style.zIndex = '';
                closeAddModal();
                onboardingAddDemoSong();
            }
        },
        {
            target: '#col-setlist',
            get title() { return t('onb_step4_title'); },
            get text() { return t('onb_step4_text'); },
            position: 'right'
        },
        {
            target: '.setlist-actions',
            get title() { return t('onb_setlisttools_title'); },
            get text() { return t('onb_setlisttools_text'); },
            position: 'top',
            showIf: function() { return !!document.querySelector('.setlist-actions'); }
        },
        // ── Phase 2: Live Panel ──
        {
            target: '#slides-container',
            get title() { return t('onb_step5_title'); },
            get text() { return t('onb_step5_text'); },
            position: 'left',
            beforeShow: function() {
                if (setlist.length > 0 && currentSetIndex < 0) selectForLive(0);
            },
            interactive: true,
            interactiveTarget: '.slide-btn',
            afterInteract: function() {
                var firstSlide = document.querySelector('.slide-btn');
                if (firstSlide) firstSlide.click();
            }
        },
        {
            target: '#live-preview-box',
            get title() { return t('onb_step6_title'); },
            get text() { return t('onb_step6_text'); },
            position: 'left'
        },
        {
            target: '.pad-panel-box',
            get title() { return t('onb_step7_title'); },
            get text() { return t('onb_step7_text'); },
            position: 'left'
        },
        {
            target: '.music-info-box',
            get title() { return t('onb_step8_title'); },
            get text() { return t('onb_step8_text'); },
            position: 'left'
        },
        // ── Phase 3: Band Member View ──
        {
            target: 'button[onclick="openQRModal()"]',
            get title() { return t('onb_step9_title'); },
            get text() { return t('onb_step9_text'); },
            position: 'bottom',
            interactive: true,
            interactiveTarget: 'button[onclick="openQRModal()"]',
            afterInteract: function() {
                window.open('/band_member?tour=1', '_blank');
            }
        },
        // ── Phase 4: Conference Mode ──
        {
            target: 'button[onclick="switchMode(\'conference\')"]',
            get title() { return t('onb_step10_title'); },
            get text() { return t('onb_step10_text'); },
            position: 'bottom',
            interactive: true,
            interactiveTarget: 'button[onclick="switchMode(\'conference\')"]',
            afterInteract: function() { switchMode('conference'); }
        },
        {
            target: '#timer-val',
            get title() { return t('onb_step11_title'); },
            get text() { return t('onb_step11_text'); },
            position: 'right',
            beforeShow: function() {
                var confEl = document.getElementById('conference-mode');
                if (!confEl || !confEl.classList.contains('active')) {
                    switchMode('conference');
                }
            }
        },
        {
            target: '.conf-grid > .conf-card:nth-child(2)',
            get title() { return t('onb_step12_title'); },
            get text() { return t('onb_step12_text'); },
            position: 'left'
        },
        // ── Phase 5: Settings & Finish ──
        {
            target: '.settings-btn',
            get title() { return t('onb_step13_title'); },
            get text() { return t('onb_step13_text'); },
            position: 'bottom',
            beforeShow: function() {
                var confEl = document.getElementById('conference-mode');
                if (confEl && confEl.classList.contains('active')) {
                    switchMode('worship');
                }
            }
        },
        {
            target: 'select[name="chord_notation"]',
            get title() { return t('onb_step14_title'); },
            get text() { return t('onb_step14_text'); },
            position: 'bottom',
            beforeShow: function() { openSettingsModal(); var m = document.getElementById('settingsModal'); if (m) m.style.zIndex = '99989'; },
            afterHide: function() { var m = document.getElementById('settingsModal'); if (m) m.style.zIndex = ''; closeSettingsModal(); }
        },
        {
            target: '.qr-container',
            get title() { return t('onb_step15_title'); },
            get text() { return t('onb_step15_text'); },
            position: 'top',
            beforeShow: function() { openQRModal(); var m = document.getElementById('qrModal'); if (m) m.style.zIndex = '99989'; },
            afterHide: function() { var m = document.getElementById('qrModal'); if (m) m.style.zIndex = ''; closeQRModal(); }
        },
        {
            target: '.bottom-controls',
            get title() { return t('onb_step16_title'); },
            get text() { return t('onb_step16_text'); },
            position: 'top'
        },
        {
            target: '#silent-md-btn',
            get title() { return t('onb_silentmd_title'); },
            get text() { return t('onb_silentmd_text'); },
            position: 'top'
        }
    ];

    // --- Tour state ---
    let onboardingCurrentStep = 0;
    let onboardingOverlay = null;
    let onboardingSpotlight = null;
    let onboardingTooltip = null;
    let onboardingResizeHandler = null;
    let onboardingInteractHandler = null;

    function onboardingCreateElements() {
        // Overlay (click to advance)
        onboardingOverlay = document.createElement('div');
        onboardingOverlay.className = 'onboarding-overlay';
        onboardingOverlay.addEventListener('click', function(e) {
            if (e.target === onboardingOverlay) {
                onboardingNext();
            }
        });
        document.body.appendChild(onboardingOverlay);

        // Spotlight cutout
        onboardingSpotlight = document.createElement('div');
        onboardingSpotlight.className = 'onboarding-spotlight';
        document.body.appendChild(onboardingSpotlight);

        // Tooltip
        onboardingTooltip = document.createElement('div');
        onboardingTooltip.className = 'onboarding-tooltip';
        document.body.appendChild(onboardingTooltip);
    }

    function onboardingCleanupInteract() {
        if (onboardingInteractHandler) {
            onboardingInteractHandler.el.removeEventListener('click', onboardingInteractHandler.fn);
            onboardingInteractHandler.el.style.position = '';
            onboardingInteractHandler.el.style.zIndex = '';
            onboardingInteractHandler = null;
        }
    }

    function onboardingPositionTooltip(targetRect, position, step, totalSteps) {
        const GAP = 16;
        const stepDef = ONBOARDING_STEPS[step];
        const isInteractive = !!stepDef.interactive;

        // Build tooltip content
        const arrowClass = {
            'bottom': 'arrow-top',
            'top': 'arrow-bottom',
            'left': 'arrow-right',
            'right': 'arrow-left'
        }[position] || 'arrow-top';

        const isFirst = (step === 0);
        const isLast = (step === totalSteps - 1);
        var nextLabel = isLast ? t('onb_finish') : t('onb_next');

        onboardingTooltip.innerHTML = `
            <div class="onboarding-tooltip-arrow ${arrowClass}"></div>
            <div class="onboarding-step-counter">${step + 1} / ${totalSteps}</div>
            <h3>${stepDef.title}</h3>
            <p>${stepDef.text}</p>
            <div class="onboarding-btn-row">
                ${!isFirst ? '<button class="onboarding-btn-ghost" data-onboarding="back">' + t('onb_back') + '</button>' : ''}
                <button class="onboarding-btn-primary" data-onboarding="next">${nextLabel}</button>
                <button class="onboarding-btn-skip" data-onboarding="skip">${t('onb_skip')}</button>
            </div>
        `;

        // Attach button listeners
        onboardingTooltip.querySelector('[data-onboarding="next"]').addEventListener('click', function(e) {
            e.stopPropagation();
            if (isInteractive && stepDef.afterInteract) stepDef.afterInteract();
            onboardingNext();
        });
        const backBtn = onboardingTooltip.querySelector('[data-onboarding="back"]');
        if (backBtn) {
            backBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                onboardingBack();
            });
        }
        onboardingTooltip.querySelector('[data-onboarding="skip"]').addEventListener('click', function(e) {
            e.stopPropagation();
            onboardingEnd();
        });

        // Set up interactive target
        onboardingCleanupInteract();
        if (isInteractive && stepDef.interactiveTarget) {
            var iTarget = document.querySelector(stepDef.interactiveTarget);
            if (iTarget) {
                iTarget.style.position = 'relative';
                iTarget.style.zIndex = '100001';
                var handler = function() {
                    if (stepDef.afterInteract) stepDef.afterInteract();
                    setTimeout(function() { onboardingNext(); }, 300);
                };
                iTarget.addEventListener('click', handler);
                onboardingInteractHandler = { el: iTarget, fn: handler };
            }
        }

        // Make tooltip visible to measure it
        onboardingTooltip.classList.remove('visible');
        onboardingTooltip.style.visibility = 'hidden';
        onboardingTooltip.style.display = 'block';

        // Force layout to get dimensions
        const tooltipRect = onboardingTooltip.getBoundingClientRect();
        const tw = tooltipRect.width;
        const th = tooltipRect.height;

        let top, left;

        switch (position) {
            case 'bottom':
                top = targetRect.bottom + GAP;
                left = targetRect.left + (targetRect.width / 2) - (tw / 2);
                break;
            case 'top':
                top = targetRect.top - th - GAP;
                left = targetRect.left + (targetRect.width / 2) - (tw / 2);
                break;
            case 'left':
                top = targetRect.top + (targetRect.height / 2) - (th / 2);
                left = targetRect.left - tw - GAP;
                break;
            case 'right':
                top = targetRect.top + (targetRect.height / 2) - (th / 2);
                left = targetRect.right + GAP;
                break;
            default:
                top = targetRect.bottom + GAP;
                left = targetRect.left;
        }

        // Clamp to viewport
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        if (left < 10) left = 10;
        if (left + tw > vw - 10) left = vw - tw - 10;
        if (top < 10) top = 10;
        if (top + th > vh - 10) top = vh - th - 10;

        onboardingTooltip.style.top = top + 'px';
        onboardingTooltip.style.left = left + 'px';
        onboardingTooltip.style.visibility = '';

        // Animate in
        requestAnimationFrame(function() {
            if (onboardingTooltip) onboardingTooltip.classList.add('visible');
        });
    }

    function onboardingShowStep(stepIndex) {
        if (stepIndex < 0 || stepIndex >= ONBOARDING_STEPS.length) {
            onboardingEnd();
            return;
        }

        onboardingCurrentStep = stepIndex;
        const stepDef = ONBOARDING_STEPS[stepIndex];

        if (stepDef.beforeShow) {
            stepDef.beforeShow();
        }

        var findTarget = function() {
            return document.querySelector(stepDef.target);
        };

        var targetEl = findTarget();

        if (!targetEl) {
            setTimeout(function() {
                targetEl = findTarget();
                if (!targetEl) {
                    if (stepIndex < ONBOARDING_STEPS.length - 1) {
                        onboardingShowStep(stepIndex + 1);
                    } else {
                        onboardingEnd();
                    }
                    return;
                }
                onboardingPositionOnTarget(targetEl, stepDef, stepIndex);
            }, 300);
            return;
        }

        onboardingPositionOnTarget(targetEl, stepDef, stepIndex);
    }

    function onboardingPositionOnTarget(targetEl, stepDef, stepIndex) {
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });

        setTimeout(function() {
            // Tour mógł zostać zamknięty zanim ten callback się wykonał
            if (!onboardingSpotlight || !onboardingTooltip) return;
            var rect = targetEl.getBoundingClientRect();
            var PAD = 8;

            onboardingSpotlight.style.top = (rect.top - PAD) + 'px';
            onboardingSpotlight.style.left = (rect.left - PAD) + 'px';
            onboardingSpotlight.style.width = (rect.width + PAD * 2) + 'px';
            onboardingSpotlight.style.height = (rect.height + PAD * 2) + 'px';
            onboardingSpotlight.style.display = 'block';

            onboardingTooltip.classList.remove('visible');
            setTimeout(function() {
                if (!onboardingTooltip) return;
                onboardingPositionTooltip(rect, stepDef.position, stepIndex, ONBOARDING_STEPS.length);
            }, 50);
        }, 350);
    }

    function onboardingLeaveStep() {
        onboardingCleanupInteract();
        var stepDef = ONBOARDING_STEPS[onboardingCurrentStep];
        if (stepDef && stepDef.afterHide) {
            stepDef.afterHide();
        }
    }

    function onboardingNext() {
        if (onboardingCurrentStep >= ONBOARDING_STEPS.length - 1) {
            onboardingEnd();
        } else {
            onboardingLeaveStep();
            onboardingShowStep(onboardingCurrentStep + 1);
        }
    }

    function onboardingBack() {
        if (onboardingCurrentStep > 0) {
            onboardingLeaveStep();
            onboardingShowStep(onboardingCurrentStep - 1);
        }
    }

    function onboardingEnd() {
        onboardingLeaveStep();
        onboardingCleanupInteract();
        localStorage.setItem('jafa_onboarding_done', '1');

        var confEl = document.getElementById('conference-mode');
        if (confEl && confEl.classList.contains('active')) {
            switchMode('worship');
        }

        if (onboardingOverlay) {
            onboardingOverlay.classList.remove('active');
        }
        if (onboardingTooltip) {
            onboardingTooltip.classList.remove('visible');
        }
        if (onboardingSpotlight) {
            onboardingSpotlight.style.display = 'none';
        }

        // Remove elements after transition
        setTimeout(function() {
            if (onboardingOverlay && onboardingOverlay.parentNode) {
                onboardingOverlay.parentNode.removeChild(onboardingOverlay);
            }
            if (onboardingSpotlight && onboardingSpotlight.parentNode) {
                onboardingSpotlight.parentNode.removeChild(onboardingSpotlight);
            }
            if (onboardingTooltip && onboardingTooltip.parentNode) {
                onboardingTooltip.parentNode.removeChild(onboardingTooltip);
            }
            onboardingOverlay = null;
            onboardingSpotlight = null;
            onboardingTooltip = null;
        }, 500);

        // Remove resize handler
        if (onboardingResizeHandler) {
            window.removeEventListener('resize', onboardingResizeHandler);
            onboardingResizeHandler = null;
        }
    }

    function onboardingStart() {
        onboardingCurrentStep = 0;

        // Create DOM elements
        onboardingCreateElements();

        // Show overlay
        requestAnimationFrame(function() {
            onboardingOverlay.classList.add('active');
        });

        // Handle resize: reposition current step
        onboardingResizeHandler = function() {
            if (onboardingSpotlight && onboardingTooltip) {
                onboardingShowStep(onboardingCurrentStep);
            }
        };
        window.addEventListener('resize', onboardingResizeHandler);

        // Show first step
        setTimeout(function() {
            onboardingShowStep(0);
        }, 200);
    }

    // Expose global function to re-trigger the tour
    window.startOnboarding = function() {
        // Clean up any existing tour
        if (onboardingOverlay) {
            onboardingEnd();
            setTimeout(function() {
                onboardingStart();
            }, 600);
        } else {
            onboardingStart();
        }
    };

    // Auto-start on first visit
    document.addEventListener('DOMContentLoaded', function() {
        if (!localStorage.getItem('jafa_onboarding_done')) {
            setTimeout(function() {
                onboardingStart();
            }, 1500);
        }
    });
})();

// ═══════════════════════════════════════════════════════════════
//  SILENT MUSIC DIRECTOR — pianino MIDI → akordy na żywo u zespołu
//  Odczytuje nuty z USB MIDI, rozpoznaje akord (chord_detect.js) i
//  broadcastuje ślad akordów (obecny + 3 poprzednie) na band_member
//  oraz scenę. Działa jak nakładka blackout — włącz/wyłącz.
// ═══════════════════════════════════════════════════════════════
(function () {
    var midiAccess = null;
    var midiInputs = [];
    var boundInput = null;
    var heldNotes = {};        // midi number -> true (fizycznie wciśnięte)
    var sustained = {};        // podtrzymane pedałem po puszczeniu klawisza
    var sustainOn = false;
    var settleTimer = null;
    var lastChordName = null;
    var history = [];          // ostatnie akordy, najnowszy na końcu
    var active = false;

    function activeMidiSet() {
        // Nuty brzmiące = wciśnięte ∪ podtrzymane pedałem
        var s = {};
        for (var n in heldNotes) if (heldNotes[n]) s[n] = true;
        for (var m in sustained) if (sustained[m]) s[m] = true;
        return Object.keys(s).map(Number);
    }

    function scheduleDetect() {
        if (settleTimer) clearTimeout(settleTimer);
        // ~110ms na "ustabilizowanie" akordu (dźwięki rzadko padają idealnie razem)
        settleTimer = setTimeout(runDetect, 110);
    }

    function runDetect() {
        var notes = activeMidiSet();
        if (notes.length === 0) return; // nie czyścimy — trzymamy ostatni akord na ekranie
        var res = (typeof ChordDetect !== 'undefined') ? ChordDetect.detectChord(notes) : null;
        if (!res) return;
        if (res.name === lastChordName) return; // bez zmian
        lastChordName = res.name;
        history.push(res.name);
        if (history.length > 4) history = history.slice(-4);
        broadcastSilentMD();
    }

    function broadcastSilentMD() {
        socket.emit('silent_md', {
            active: active,
            current: history.length ? history[history.length - 1] : null,
            history: history.slice(0, -1).slice(-3) // do 3 poprzednich (bez obecnego)
        });
    }

    function onMidiMessage(e) {
        if (!active) return;
        var d = e.data;
        var status = d[0] & 0xf0;
        var data1 = d[1], data2 = d[2];
        if (status === 0x90 && data2 > 0) {            // note on
            heldNotes[data1] = true;
            delete sustained[data1];
            scheduleDetect();
        } else if (status === 0x80 || (status === 0x90 && data2 === 0)) { // note off
            if (sustainOn) { sustained[data1] = true; }
            delete heldNotes[data1];
            scheduleDetect();
        } else if (status === 0xb0 && data1 === 64) {  // sustain pedal (CC64)
            if (data2 >= 64) {
                sustainOn = true;
            } else {
                sustainOn = false;
                sustained = {}; // puszczenie pedału gasi podtrzymane
                scheduleDetect();
            }
        }
    }

    var selectedDeviceId = localStorage.getItem('midiDeviceId') || '';

    function listInputs() {
        midiInputs = [];
        if (!midiAccess) return midiInputs;
        midiAccess.inputs.forEach(function (inp) { midiInputs.push(inp); });
        return midiInputs;
    }

    // Podpina TYLKO wybrane urządzenie (albo pierwsze, gdy nic nie wybrano).
    function bindSelectedInput() {
        if (!midiAccess) return;
        listInputs();
        // Odłącz wszystkie, potem podłącz jedno
        midiInputs.forEach(function (inp) { inp.onmidimessage = null; });
        var target = null;
        if (selectedDeviceId) {
            for (var i = 0; i < midiInputs.length; i++) {
                if (midiInputs[i].id === selectedDeviceId) { target = midiInputs[i]; break; }
            }
        }
        if (!target && midiInputs.length > 0) {
            target = midiInputs[0];
            selectedDeviceId = target.id;
        }
        boundInput = target;
        if (target) target.onmidimessage = onMidiMessage;
        populateMidiSelect();
    }

    function ensureMidiAccess(cb) {
        if (!navigator.requestMIDIAccess) {
            showToast(currentLang === 'en' ? 'Web MIDI not supported in this runtime.' : 'To środowisko nie wspiera Web MIDI.');
            return;
        }
        if (midiAccess) { cb(); return; }
        navigator.requestMIDIAccess({ sysex: false }).then(function (acc) {
            midiAccess = acc;
            midiAccess.onstatechange = function () { bindSelectedInput(); };
            cb();
        }).catch(function () {
            showToast(currentLang === 'en' ? 'MIDI access denied.' : 'Odmówiono dostępu do MIDI.');
        });
    }

    function populateMidiSelect() {
        var sel = document.getElementById('midi-device-select');
        if (!sel) return;
        listInputs();
        if (midiInputs.length === 0) {
            sel.innerHTML = '<option value="">' + (currentLang === 'en' ? '— none detected —' : '— nie wykryto —') + '</option>';
            return;
        }
        sel.innerHTML = midiInputs.map(function (inp) {
            var nm = inp.name || inp.id;
            var selAttr = (inp.id === selectedDeviceId) ? ' selected' : '';
            return '<option value="' + inp.id + '"' + selAttr + '>' + nm + '</option>';
        }).join('');
    }

    window.scanMidiDevices = function () {
        ensureMidiAccess(function () {
            bindSelectedInput();
            populateMidiSelect();
            var n = midiInputs.length;
            showToast((currentLang === 'en' ? 'MIDI devices: ' : 'Urządzenia MIDI: ') + n);
        });
    };

    window.selectMidiDevice = function (id) {
        selectedDeviceId = id || '';
        localStorage.setItem('midiDeviceId', selectedDeviceId);
        bindSelectedInput();
    };

    function updateMidiButtonState(state) {
        var btn = document.getElementById('silent-md-btn');
        if (!btn) return;
        btn.classList.toggle('active', active);
        var label = document.getElementById('silent-md-label');
        if (label) {
            label.textContent = active
                ? (currentLang === 'en' ? 'SILENT MD ON' : 'SILENT MD WŁ.')
                : 'SILENT MD';
        }
        if (state) {
            var status = document.getElementById('silent-md-status');
            if (status) status.textContent = state;
        }
    }

    window.toggleSilentMD = function () {
        if (!active) {
            ensureMidiAccess(function () {
                bindSelectedInput();
                if (midiInputs.length === 0) {
                    showToast(currentLang === 'en'
                        ? 'No MIDI device found. Connect your piano.'
                        : 'Nie wykryto pianina MIDI. Podłącz je przez USB.');
                }
                startSilentMD();
            });
        } else {
            stopSilentMD();
        }
    };

    function startSilentMD() {
        active = true;
        heldNotes = {}; sustained = {}; sustainOn = false;
        history = []; lastChordName = null;
        var devName = boundInput ? (boundInput.name || boundInput.id) : '';
        updateMidiButtonState(devName ? ('· ' + devName) : '');
        broadcastSilentMD();
        showToast(currentLang === 'en' ? 'Silent MD on' : 'Silent MD włączony');
    }

    // Populacja listy urządzeń przy otwarciu ustawień (jeśli mamy już dostęp)
    window.refreshMidiSelectUI = function () {
        if (midiAccess) populateMidiSelect();
    };

    function stopSilentMD() {
        active = false;
        if (settleTimer) clearTimeout(settleTimer);
        broadcastSilentMD(); // active:false → ekrany wracają do normalnego widoku
        updateMidiButtonState('');
        showToast(currentLang === 'en' ? 'Silent MD off' : 'Silent MD wyłączony');
    }

    // Ekspozycja do testów (symulacja MIDI bez hardware'u)
    window.__silentMD = {
        feed: function (bytes) { onMidiMessage({ data: bytes }); },
        start: function () { startSilentMD(); },
        stop: function () { stopSilentMD(); },
        state: function () { return { active: active, history: history.slice() }; }
    };
})();


// ═══════════════════════════════════════════════════════════════
//  METRONOM + ROUTING AUDIO
//  Metronom (dokładny scheduler Web Audio) na osobnej szynie, którą
//  można skierować na inne wyjścia interfejsu niż pady (click do IEM,
//  pady do FOH). Bez interfejsu — wszystko w stereo.
// ═══════════════════════════════════════════════════════════════
(function () {
    var metro = {
        on: false, beats: 4, volume: 0.6, manualBpm: 0, timbre: 'beep',
        nextTime: 0, beat: 0, timer: null, ducking: false,
        lookahead: 25, scheduleAhead: 0.12
    };
    try { metro.volume = parseFloat(localStorage.getItem('metroVolume')); if (isNaN(metro.volume)) metro.volume = 0.6; } catch (e) {}
    try { metro.beats = parseInt(localStorage.getItem('metroBeats')) || 4; } catch (e) {}
    metro.timbre = localStorage.getItem('metroTimbre') || 'beep';

    // Barwy metronomu — typ oscylatora, częstotliwości (akcent/normal), zanik
    var TIMBRES = {
        beep:  { type: 'sine',     accent: 1600, normal: 950,  decay: 0.05 },
        click: { type: 'square',   accent: 2000, normal: 1400, decay: 0.03 },
        wood:  { type: 'triangle', accent: 1200, normal: 800,  decay: 0.045 },
        tick:  { type: 'square',   accent: 3200, normal: 2200, decay: 0.02 },
        soft:  { type: 'sine',     accent: 900,  normal: 640,  decay: 0.07 }
    };

    function getLiveBpm() {
        if (typeof currentSetIndex !== 'undefined' && currentSetIndex >= 0 && setlist[currentSetIndex]) {
            var b = parseInt(setlist[currentSetIndex].bpm);
            if (b && b > 0) return b;
        }
        return 0;
    }
    function currentBpm() {
        if (metro.manualBpm > 0) return metro.manualBpm;
        var live = getLiveBpm();
        return (live > 0) ? live : 120;
    }

    function scheduleClick(beat, time) {
        var ctx = ensureAudioCtx();
        var tb = TIMBRES[metro.timbre] || TIMBRES.beep;
        var osc = ctx.createOscillator();
        var g = ctx.createGain();
        var accent = (beat === 0);
        osc.type = tb.type;
        osc.frequency.value = accent ? tb.accent : tb.normal;
        g.gain.setValueAtTime(0.0001, time);
        g.gain.exponentialRampToValueAtTime(metro.volume * (accent ? 1.0 : 0.6), time + 0.001);
        g.gain.exponentialRampToValueAtTime(0.0001, time + tb.decay);
        osc.connect(g);
        g.connect(AudioRouting.metroBus || ctx.destination);
        osc.start(time);
        osc.stop(time + tb.decay + 0.01);
    }

    function scheduler() {
        var ctx = ensureAudioCtx();
        while (metro.nextTime < ctx.currentTime + metro.scheduleAhead) {
            scheduleClick(metro.beat, metro.nextTime);
            metro.nextTime += 60.0 / currentBpm();
            metro.beat = (metro.beat + 1) % metro.beats;
        }
        metro.timer = setTimeout(scheduler, metro.lookahead);
    }

    function updateMetroUI() {
        var btn = document.getElementById('metro-btn');
        if (btn) {
            btn.classList.toggle('active', metro.on);
            btn.textContent = metro.on ? '■' : '▶';
        }
        var bpmv = document.getElementById('metro-bpm-val');
        if (bpmv) bpmv.textContent = currentBpm();
    }

    window.toggleMetronome = function () {
        if (metro.on) {
            metro.on = false;
            if (metro.timer) clearTimeout(metro.timer);
            updateMetroUI();
            if (typeof showToast === 'function') showToast(currentLang === 'en' ? 'Metronome off' : 'Metronom wyłączony');
        } else {
            var ctx = ensureAudioCtx();
            metro.on = true; metro.beat = 0;
            metro.nextTime = ctx.currentTime + 0.06;
            scheduler();
            updateMetroUI();
            if (typeof showToast === 'function') showToast((currentLang === 'en' ? 'Metronome ' : 'Metronom ') + currentBpm() + ' BPM');
        }
    };

    window.isMetronomeOn = function () { return metro.on; };
    // Start/stop bez toastów i bez efektów ubocznych (dla flow pedałowego)
    window.metroSetActive = function (on) {
        if (on && !metro.on) {
            var ctx = ensureAudioCtx();
            metro.on = true; metro.beat = 0; metro.ducking = false;
            if (metro.timer) clearTimeout(metro.timer);
            try { AudioRouting.metroBus.gain.cancelScheduledValues(ctx.currentTime); AudioRouting.metroBus.gain.setValueAtTime(1, ctx.currentTime); } catch (e) {}
            metro.nextTime = ctx.currentTime + 0.06;
            scheduler();
        } else if (!on && metro.on) {
            metro.on = false;
            if (metro.timer) clearTimeout(metro.timer);
        }
        updateMetroUI();
    };

    // Re-sync UI po zmianie piosenki (żeby BPM się odświeżył)
    window.syncMetronome = function () { updateMetroUI(); };

    // Zmiana piosenki — odśwież BPM i (jeśli metronom gra) zrób duck+powrót
    var lastSongForMetro = -1;
    window.metroSongChanged = function (i) {
        var changed = (i !== lastSongForMetro);
        lastSongForMetro = i;
        updateMetroUI();
        if (changed && metro.on) window.duckMetronome();
    };
    window.setMetroVolume = function (v) { metro.volume = parseFloat(v); localStorage.setItem('metroVolume', metro.volume); };
    window.setMetroBeats = function (v) { metro.beats = parseInt(v) || 4; localStorage.setItem('metroBeats', metro.beats); updateMetroUI(); };
    window.setMetroTimbre = function (t) { metro.timbre = t; localStorage.setItem('metroTimbre', t); };

    // Popover ustawień metronomu (barwa, metrum, głośność) przy przycisku
    window.toggleMetroPopover = function (ev) {
        if (ev) ev.stopPropagation();
        var pop = document.getElementById('metro-popover');
        if (!pop) return;
        if (pop.classList.contains('show')) { pop.classList.remove('show'); return; }
        // Załaduj bieżące wartości
        var tb = document.getElementById('metro-timbre-select'); if (tb) tb.value = metro.timbre;
        var be = document.getElementById('metro-beats-select'); if (be) be.value = String(metro.beats);
        var vo = document.getElementById('metro-vol-slider'); if (vo) vo.value = metro.volume;
        // Pozycjonuj pod przyciskiem
        var btn = document.getElementById('metro-cfg-btn');
        pop.classList.add('show');
        if (btn) {
            var r = btn.getBoundingClientRect();
            var w = pop.offsetWidth || 220;
            var left = Math.min(r.left, window.innerWidth - w - 12);
            var top = r.bottom + 8;
            if (top + pop.offsetHeight > window.innerHeight - 10) top = r.top - pop.offsetHeight - 8;
            pop.style.left = Math.max(10, left) + 'px';
            pop.style.top = top + 'px';
        }
        // Zamknij na klik poza
        setTimeout(function () {
            document.addEventListener('click', closeMetroPopoverOnce, { once: true });
        }, 0);
    };
    function closeMetroPopoverOnce(e) {
        var pop = document.getElementById('metro-popover');
        if (!pop) return;
        if (pop.contains(e.target) || (e.target.closest && e.target.closest('#metro-cfg-btn'))) {
            document.addEventListener('click', closeMetroPopoverOnce, { once: true });
            return;
        }
        pop.classList.remove('show');
    }

    // Wyciszenie + powrót przy przejściu między piosenkami: metronom cichnie,
    // robi krótki oddech i wchodzi znów na „jedynkę" w nowym tempie.
    window.duckMetronome = function () {
        if (!metro.on || metro.ducking) return;
        var ctx = ensureAudioCtx();
        var bus = AudioRouting.metroBus;
        if (!bus) return;
        metro.ducking = true;
        // Zatrzymaj harmonogram i wycisz szynę
        if (metro.timer) { clearTimeout(metro.timer); metro.timer = null; }
        var now = ctx.currentTime;
        try {
            bus.gain.cancelScheduledValues(now);
            bus.gain.setValueAtTime(bus.gain.value, now);
            bus.gain.linearRampToValueAtTime(0.0001, now + 0.18);
        } catch (e) {}
        // Po krótkim oddechu wróć na jedynkę w nowym tempie
        setTimeout(function () {
            if (!metro.on) { metro.ducking = false; return; }
            var c2 = ensureAudioCtx();
            try {
                var t2 = c2.currentTime;
                AudioRouting.metroBus.gain.cancelScheduledValues(t2);
                AudioRouting.metroBus.gain.setValueAtTime(0.0001, t2);
                AudioRouting.metroBus.gain.linearRampToValueAtTime(1, t2 + 0.05);
            } catch (e) {}
            metro.beat = 0;
            metro.nextTime = c2.currentTime + 0.06;
            metro.ducking = false;
            scheduler();
            updateMetroUI();
        }, 650);
    };

    // ── Wybór wyjścia audio i kanałów ──
    window.scanAudioOutputs = function () {
        var ctx = ensureAudioCtx(); // zbuduj graf, poznaj maxChannelCount
        populateChannelSelects(ctx);
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
            if (typeof showToast === 'function') showToast(currentLang === 'en' ? 'Device list unavailable.' : 'Lista urządzeń niedostępna.');
            return;
        }
        navigator.mediaDevices.enumerateDevices().then(function (devs) {
            var outs = devs.filter(function (d) { return d.kind === 'audiooutput'; });
            var sel = document.getElementById('audio-out-select');
            if (sel) {
                var def = (currentLang === 'en' ? 'System default' : 'Domyślne systemowe');
                sel.innerHTML = '<option value="">' + def + '</option>' + outs.map(function (d, i) {
                    var nm = d.label || ((currentLang === 'en' ? 'Output ' : 'Wyjście ') + (i + 1));
                    var s = (d.deviceId === AudioRouting.outputDeviceId) ? ' selected' : '';
                    return '<option value="' + d.deviceId + '"' + s + '>' + nm + '</option>';
                }).join('');
            }
            if (typeof showToast === 'function') showToast((currentLang === 'en' ? 'Audio outputs: ' : 'Wyjścia audio: ') + outs.length +
                ' · ' + AudioRouting.maxCh + (currentLang === 'en' ? ' ch' : ' kan.'));
        });
    };

    window.selectAudioOutput = function (id) {
        AudioRouting.outputDeviceId = id || '';
        localStorage.setItem('audioOutId', AudioRouting.outputDeviceId);
        if (audioCtx && typeof audioCtx.setSinkId === 'function') {
            audioCtx.setSinkId(AudioRouting.outputDeviceId).catch(function () {
                if (typeof showToast === 'function') showToast(currentLang === 'en' ? 'Output routing not supported here.' : 'To środowisko nie wspiera wyboru wyjścia.');
            });
        }
    };

    function channelPairOptions(maxCh, selected) {
        var opts = '';
        for (var i = 0; i + 1 < maxCh; i += 2) {
            var val = '[' + i + ',' + (i + 1) + ']';
            var s = (selected[0] === i) ? ' selected' : '';
            opts += '<option value="' + val + '"' + s + '>' + (i + 1) + '–' + (i + 2) + '</option>';
        }
        return opts;
    }
    window.populateAudioRoutingUI = function () {
        var max = AudioRouting.maxCh || 2;
        var multi = max > 2;
        var split = AudioRouting.stereoSplit;
        // Podział L/P jest ZAWSZE dostępny (najczęstszy przypadek — brak
        // interfejsu). Wybór par kanałów pokazujemy tylko przy karcie
        // wielokanałowej i gdy L/P jest wyłączony (bo L/P go nadpisuje).
        var splitRow = document.getElementById('stereo-split-row');
        var padRow = document.getElementById('pad-ch-row');
        var metroRow = document.getElementById('metro-ch-row');
        var showCh = multi && !split;
        if (splitRow) splitRow.style.display = 'flex';
        if (padRow) padRow.style.display = showCh ? 'flex' : 'none';
        if (metroRow) metroRow.style.display = showCh ? 'flex' : 'none';

        var splitSel = document.getElementById('stereo-split-select');
        if (splitSel) splitSel.value = split ? '1' : '0';

        var padSel = document.getElementById('pad-channels-select');
        var metroSel = document.getElementById('metro-channels-select');
        if (padSel) padSel.innerHTML = channelPairOptions(max, AudioRouting.padChannels);
        if (metroSel) metroSel.innerHTML = channelPairOptions(max, AudioRouting.metroChannels);

        var note = document.getElementById('audio-ch-note');
        if (note) {
            note.textContent = split
                ? (currentLang === 'en'
                    ? 'Pads → Left channel, metronome → Right channel. Use a stereo-jack → 2× mono splitter to feed two mixer inputs.'
                    : 'Pady → lewy kanał, metronom → prawy. Użyj przejściówki jack stereo → 2× mono, by wpiąć w dwa wejścia miksera.')
                : (multi ? '' : (currentLang === 'en'
                    ? 'No multi-output interface — turn on “Pads L / Metronome R” and use a Y-splitter cable.'
                    : 'Brak interfejsu wielokanałowego — włącz „Pady L / Metronom P" i użyj przejściówki jack → 2× mono.'));
        }
    };
    function populateChannelSelects(ctx) { window.populateAudioRoutingUI(); }
    window.selectPadChannels = function (val) {
        try { AudioRouting.padChannels = JSON.parse(val); } catch (e) { return; }
        localStorage.setItem('padChannels', JSON.stringify(AudioRouting.padChannels));
        if (audioCtx) wireAudioBuses(audioCtx);
    };
    window.selectMetroChannels = function (val) {
        try { AudioRouting.metroChannels = JSON.parse(val); } catch (e) { return; }
        localStorage.setItem('metroChannels', JSON.stringify(AudioRouting.metroChannels));
        if (audioCtx) wireAudioBuses(audioCtx);
    };

    // Ekspozycja do testów
    window.__metro = {
        state: function () { return { on: metro.on, bpm: currentBpm(), beats: metro.beats }; },
        routing: function () { return AudioRouting; }
    };
})();
