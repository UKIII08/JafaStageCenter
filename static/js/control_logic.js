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

const KEY_MAP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
const FLAT_TO_SHARP = {'Db':'C#', 'Eb':'D#', 'Gb':'F#', 'Ab':'G#', 'Bb':'A#', 'Cb':'B'};

function ensureAudioCtx() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
}

function getPadNode(el) {
    if (padNodes.has(el)) return padNodes.get(el);
    const ctx = ensureAudioCtx();
    const source = ctx.createMediaElementSource(el);
    const gain = ctx.createGain();
    gain.gain.value = 0;
    source.connect(gain);
    gain.connect(ctx.destination);
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

    let filename = `/static/pads/${targetKey}.mp3`;
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

        // Nowy pad narasta liniowo
        nextNode.gain.gain.setValueAtTime(0, t);
        nextNode.gain.gain.linearRampToValueAtTime(globalPadVolume, t + fadeOutSec);

        // Stary pad maleje liniowo — równoległy crossfade
        if (active && active !== next && !active.paused) {
            const activeNode = getPadNode(active);
            const currentVol = activeNode.gain.gain.value;
            activeNode.gain.gain.cancelScheduledValues(t);
            activeNode.gain.gain.setValueAtTime(currentVol, t);
            activeNode.gain.gain.linearRampToValueAtTime(0, t + fadeOutSec);
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
            node.gain.gain.setValueAtTime(vol, now);
            node.gain.gain.linearRampToValueAtTime(0, now + duration);
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

    // Restore blackout state from server
    if (data.is_blackout !== undefined) {
        isBlackoutActive = data.is_blackout;
        const btns = document.querySelectorAll('button[onclick="blackout()"]');
        btns.forEach(btn => {
            if (isBlackoutActive) {
                btn.style.background = "var(--accent-danger)";
                btn.style.color = "white";
                btn.style.boxShadow = "0 0 20px rgba(255, 107, 107, 0.7)";
                btn.innerText = translations[currentLang].blackout_off_btn || "ZDEJMIJ BLACKOUT (POKAŻ EKRAN)";
            } else {
                btn.style.background = "";
                btn.style.color = "";
                btn.style.boxShadow = "";
                btn.innerText = translations[currentLang].blackout_on_btn || "WYGAŚ EKRAN RZUTNIKA";
            }
        });
    }

    if (needsRender) {
        renderSetlist();
    }

    if (data.current_index !== undefined && data.current_index !== -1 && setlist[data.current_index]) {
        selectForLive(data.current_index, false);
    } else if (data.current_index === -1) {
        document.getElementById('live-header').style.display = 'none';
        document.getElementById('slides-container').innerHTML = '';
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
    if (!fileInput.files[0]) return alert(t('alert_choose_pdf'));

    const formData = new FormData();
    formData.append("pres_file", fileInput.files[0]);

    fetch('/upload_presentation', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if(data.status === 'ok') {
            alert(t('alert_slides_ready'));
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
        const btnShow = translations[currentLang].show_btn || "Pokaż";

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

function switchMode(m){document.querySelectorAll('.mode-container').forEach(c=>c.classList.remove('active'));document.querySelectorAll('.segmented-control button, .mode-btn').forEach(b=>b.classList.remove('active'));if(m==='worship'){document.getElementById('worship-mode').classList.add('active');document.querySelector('button[onclick="switchMode(\'worship\')"]').classList.add('active');resendCurrentSlide();}else{document.getElementById('conference-mode').classList.add('active');document.querySelector('button[onclick="switchMode(\'conference\')"]').classList.add('active');sendConferenceData();}}
function resendCurrentSlide(){var active=document.querySelector('.slide-btn.active');if(active){active.click();}else if(currentLiveState){goLiveSection(currentLiveState.c,currentLiveState.n,currentLiveState.forceTrans,currentLiveState.nextTrans);}else{fetch('/send_text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({logo:true})});}}
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
            d.innerHTML = `
                <summary class="lib-summary">
                    <div><b>${s.title}</b></div>
                    <div style="display:flex;gap:5px;">
                        <button class="btn-icon" onclick="event.preventDefault(); openEditModal(${s.id})" style="background:none; border:none; cursor:pointer; color:var(--text-muted);">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        </button> 
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
                        playPad(nextKey, 5);
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
        let newVal = setlist[currentSetIndex].transpose + a;
        if (newVal < -12 || newVal > 12) return;
        setlist[currentSetIndex].transpose = newVal;
        document.getElementById('current-trans').innerText = (setlist[currentSetIndex].transpose>0?"+":"")+setlist[currentSetIndex].transpose;
        let finalKey = calculateTransposedKey(setlist[currentSetIndex].key, setlist[currentSetIndex].transpose);
        document.getElementById('live-key').innerText = finalKey;
        
        if (isPadPlaying) {
            triggerDebouncedPad(finalKey);
        }
        
        selectForLive(currentSetIndex); 
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
            btn.style.boxShadow = "0 0 20px rgba(255, 107, 107, 0.7)";
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
    document.getElementById('live-preview-box').innerText = c.replace(/\[.*?\]/g, "");
}
function showLogo(){fetch('/send_text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({logo:true})});document.getElementById('live-preview-box').innerText="LOGO";}

function saveSetlistHistory() {
    if (!setlist.length) { showToast(t('alert_empty_setlist'), 'error'); return; }
    var dateStr = new Date().toLocaleDateString('pl-PL');
    var name = prompt(t('setlist_history_name') || 'Nazwa setlisty:', dateStr);
    if (name === null) return;
    if (!name.trim()) name = dateStr;
    var songs = setlist.map(function(s) {
        return { id: s.id, title: s.title, key: s.key || '', bpm: s.bpm || 0, transpose: s.transpose || 0 };
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
            html += '<div style="padding:12px;border-bottom:1px solid var(--border-default);cursor:pointer;" onclick="loadSetlistHistory(' + h.id + ')">' +
                '<div style="font-weight:600;">' + (h.name || h.date) + '</div>' +
                '<div style="font-size:0.8em;color:var(--text-tertiary);">' + h.date + ' — ' + h.song_count + ' ' + (t('songs_count') || 'piosenek') + '</div>' +
                '<div style="font-size:0.75em;color:var(--text-muted);margin-top:4px;">' +
                h.songs.map(function(s) { return s.title; }).join(', ') + '</div></div>';
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

function loadSetlistHistory(id) {
    fetch('/api/setlist-history/' + id).then(function(r) { return r.json(); }).then(function(data) {
        if (data.error) return;
        setlist = [];
        data.songs.forEach(function(s) {
            var libSong = library.find(function(ls) { return ls.id === s.id; });
            if (libSong) {
                setlist.push(Object.assign({}, libSong, { transpose: s.transpose || 0 }));
            }
        });
        renderSetlist();
        if (setlist.length) selectForLive(0);
        updateServerState();
        document.querySelectorAll('div[style*="fixed"][style*="z-index:99999"]').forEach(function(el) { el.remove(); });
        showToast((t('setlist_loaded') || 'Setlista wczytana!') + ' (' + setlist.length + ' ' + (t('songs_count') || 'piosenek') + ')', 'success');
    });
}

function shareSetlist() {
    if (!setlist.length) { showToast(t('alert_empty_setlist'), 'error'); return; }
    var songs = setlist.map(function(s) {
        return { id: s.id, title: s.title, key: s.key || '', bpm: s.bpm || 0, transpose: s.transpose || 0 };
    });
    var dateStr = new Date().toISOString().split('T')[0];
    fetch('/api/setlist-share', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ name: dateStr, date: dateStr, songs: songs })
    }).then(function(r) { return r.json(); }).then(function(data) {
        var modal = document.createElement('div');
        modal.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = '<div style="background:var(--bg-elevated);border-radius:14px;padding:24px;max-width:400px;width:90%;border:1px solid var(--border-default);text-align:center;">' +
            '<h3 style="margin:0 0 8px;">' + (t('share_code_title') || 'Kod setlisty') + '</h3>' +
            '<p style="margin:0 0 16px;color:var(--text-tertiary);font-size:0.9em;">' + (t('share_code_msg') || 'Podaj ten kod na innym urzadzeniu:') + '</p>' +
            '<div style="font-size:2.5rem;font-weight:700;letter-spacing:0.3em;padding:16px;background:var(--bg-surface);border-radius:10px;font-family:monospace;">' + data.code + '</div>' +
            '<button onclick="this.closest(\'div[style*=fixed]\').remove()" style="margin-top:16px;padding:8px 24px;border-radius:8px;background:var(--bg-surface);color:var(--text-primary);border:1px solid var(--border-default);cursor:pointer;">OK</button></div>';
        document.body.appendChild(modal);
    }).catch(function() { showToast(t('alert_error') || 'Blad', 'error'); });
}

function importSetlistCode() {
    var code = window.prompt(t('import_code_prompt') || 'Wpisz kod setlisty:');
    if (!code) return;
    fetch('/api/setlist-share/' + code.trim().toUpperCase()).then(function(r) {
        if (!r.ok) throw new Error('not found');
        return r.json();
    }).then(function(data) {
        if (data.error) { showToast(t('import_code_not_found') || 'Nie znaleziono', 'error'); return; }
        setlist = [];
        data.songs.forEach(function(s) {
            var libSong = library.find(function(ls) { return ls.id === s.id; });
            if (libSong) {
                setlist.push(Object.assign({}, libSong, { transpose: s.transpose || 0 }));
            }
        });
        renderSetlist();
        if (setlist.length) selectForLive(0);
        updateServerState();
        showToast((t('setlist_loaded') || 'Setlista wczytana!') + ' (' + setlist.length + ' ' + (t('songs_count') || 'piosenek') + ')', 'success');
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
function setTimer(){var v=parseInt(document.getElementById('timer-input').value);totSec=(isNaN(v)||v<0)?0:v*60;updTimer();sendConferenceData();}
function updTimer(){let m=Math.floor(Math.abs(totSec)/60),s=Math.abs(totSec)%60,fmt=(totSec<0?"-":"")+(m<10?"0":"")+m+":"+(s<10?"0":"")+s;document.getElementById('timer-val').innerText=fmt;document.getElementById('timer-val').style.color=totSec<=0?"#ff6b6b":"var(--text-main)";return{text:fmt,color:totSec<=0?"red":"white"};}
function startTimer(){if(isRun)return;isRun=true;tInt=setInterval(()=>{totSec--;updTimer();sendConferenceData();},1000);}
function stopTimer(){isRun=false;clearInterval(tInt);}
function resetTimer(){stopTimer();setTimer();}
function sendConfMessage(){actMsg=document.getElementById('conf-msg').value;sendConferenceData();}
function clearConfMessage(){actMsg="";document.getElementById('conf-msg').value="";sendConferenceData();}
function sendConferenceData(){let d=updTimer();fetch('/send_text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:'conference',timer:d.text,timer_color:d.color,message:actMsg})});}

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
        fetch('/print_lyrics', {
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
            border-radius: 8px;
            background: transparent;
            box-shadow: 0 0 0 9999px rgba(6,6,10,0.82);
            transition: top 0.45s ease, left 0.45s ease, width 0.45s ease, height 0.45s ease;
            pointer-events: none;
        }
        .onboarding-spotlight::after {
            content: '';
            position: absolute;
            inset: -4px;
            border-radius: 12px;
            border: 2px solid rgba(59,130,246,0.5);
            animation: onboarding-pulse 2s ease-in-out infinite;
        }
        @keyframes onboarding-pulse {
            0%, 100% { border-color: rgba(59,130,246,0.5); box-shadow: 0 0 8px rgba(59,130,246,0.2); }
            50% { border-color: rgba(59,130,246,0.9); box-shadow: 0 0 20px rgba(59,130,246,0.4); }
        }
        .onboarding-tooltip {
            position: absolute;
            max-width: 340px;
            background: rgba(14,14,20,0.96);
            border: 1px solid rgba(59,130,246,0.2);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            z-index: 99992;
            opacity: 0;
            transform: translateY(10px);
            transition: opacity 0.35s ease, transform 0.35s ease;
            color: #e0e0e0;
            font-family: inherit;
        }
        .onboarding-tooltip.visible {
            opacity: 1;
            transform: translateY(0);
        }
        .onboarding-tooltip-arrow {
            position: absolute;
            width: 0; height: 0;
            border: 8px solid transparent;
        }
        .onboarding-tooltip-arrow.arrow-top {
            bottom: 100%;
            left: 24px;
            border-bottom-color: rgba(14,14,20,0.96);
        }
        .onboarding-tooltip-arrow.arrow-bottom {
            top: 100%;
            left: 24px;
            border-top-color: rgba(14,14,20,0.96);
        }
        .onboarding-tooltip-arrow.arrow-left {
            right: 100%;
            top: 24px;
            border-right-color: rgba(14,14,20,0.96);
        }
        .onboarding-tooltip-arrow.arrow-right {
            left: 100%;
            top: 24px;
            border-left-color: rgba(14,14,20,0.96);
        }
        .onboarding-step-counter {
            display: inline-block;
            background: rgba(59,130,246,0.15);
            color: rgba(59,130,246,0.9);
            font-size: 11px;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 20px;
            margin-bottom: 10px;
            letter-spacing: 0.5px;
        }
        .onboarding-tooltip h3 {
            margin: 0 0 8px 0;
            font-size: 16px;
            font-weight: 700;
            color: #fff;
        }
        .onboarding-tooltip p {
            margin: 0 0 18px 0;
            font-size: 13.5px;
            line-height: 1.5;
            color: #b0b0b0;
        }
        .onboarding-btn-row {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .onboarding-btn-primary {
            background: linear-gradient(135deg, #3B82F6, #60A5FA);
            color: #fff;
            border: none;
            padding: 8px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .onboarding-btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 16px rgba(59,130,246,0.4);
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
                if (!document.getElementById('conference-mode').classList.contains('active')) {
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
                if (document.getElementById('conference-mode').classList.contains('active')) {
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
            onboardingTooltip.classList.add('visible');
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
            var rect = targetEl.getBoundingClientRect();
            var PAD = 8;

            onboardingSpotlight.style.top = (rect.top - PAD) + 'px';
            onboardingSpotlight.style.left = (rect.left - PAD) + 'px';
            onboardingSpotlight.style.width = (rect.width + PAD * 2) + 'px';
            onboardingSpotlight.style.height = (rect.height + PAD * 2) + 'px';
            onboardingSpotlight.style.display = 'block';

            onboardingTooltip.classList.remove('visible');
            setTimeout(function() {
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

        if (document.getElementById('conference-mode').classList.contains('active')) {
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