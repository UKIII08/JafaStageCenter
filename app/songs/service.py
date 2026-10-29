# Wspólne reguły biblioteki piosenek (panel, Studio, import).
from sqlalchemy import func

from app.models import Song


def find_by_title(church_id, title, exclude_id=None):
    """Piosenka o tym tytule (bez rozróżniania wielkości liter i spacji
    na brzegach) albo None."""
    q = Song.query.filter(Song.church_id == church_id, Song.deleted.is_(False),
                          func.lower(func.trim(Song.title)) == (title or '').strip().lower())
    if exclude_id:
        q = q.filter(Song.id != exclude_id)
    return q.first()


def unique_title(church_id, title, exclude_id=None):
    """Tytuł bez kolizji: „Oceany" zajęte -> „Oceany (2)", „Oceany (3)"…
    Dwie piosenki o tym samym tytule psują raport CCLI i wyszukiwanie."""
    title = (title or '').strip()[:200]
    if not find_by_title(church_id, title, exclude_id):
        return title
    n = 2
    while find_by_title(church_id, f'{title} ({n})', exclude_id):
        n += 1
    return f'{title[:190]} ({n})'


# ── Prywatne notatki do części ───────────────────────────────────────────
# Kiedyś klucz = numer części ("2"), więc po dopisaniu części na początku
# notatka „do Bridge" lądowała przy Refrenie. Teraz klucz = nazwa części
# i które to jej wystąpienie ("s:refren#2"). Stare klucze liczbowe są
# czytane dalej i przepisywane przy następnym zapisie.
import json

import music_core as mc


def section_keys(content):
    keys, seen = [], {}
    for i, s in enumerate(mc.parse_song_sections(content or '')):
        lab = s['label'].strip().lower()
        if lab.startswith('slajd '):          # część bez nazwy: tylko pozycja
            keys.append(f'pos#{i}')
            continue
        seen[lab] = seen.get(lab, 0) + 1
        keys.append(f'{lab}#{seen[lab]}')
    return keys


def _load(raw):
    try:
        d = json.loads(raw or '{}')
        return d if isinstance(d, dict) else {}
    except (ValueError, TypeError):
        return {}


def notes_by_index(raw, content):
    """{"<numer części>": notatka} dla bieżącej treści piosenki."""
    d, out = _load(raw), {}
    for i, k in enumerate(section_keys(content)):
        if 's:' + k in d:
            out[str(i)] = d['s:' + k]
        elif str(i) in d:                     # stary zapis po numerze
            out[str(i)] = d[str(i)]
    return out


def notes_with(raw, content, by_index, complete=False):
    """Zapis notatek podanych po numerze części. complete=True: by_index to
    pełna lista (Studio) — części bez wpisu tracą notatkę."""
    keys = section_keys(content)
    d = {k: v for k, v in _load(raw).items() if not k.isdigit()}
    current = notes_by_index(raw, content)          # migracja starych kluczy
    for i, txt in current.items():
        d['s:' + keys[int(i)]] = txt
    for i, k in enumerate(keys):
        txt = (by_index or {}).get(str(i))
        if txt is None:
            if complete:
                d.pop('s:' + k, None)
            continue
        txt = str(txt)[:1000]
        if txt.strip():
            d['s:' + k] = txt
        else:
            d.pop('s:' + k, None)
    return json.dumps(d, ensure_ascii=False)
