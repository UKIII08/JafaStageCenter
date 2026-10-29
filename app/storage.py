"""Miejsce na pliki wspólnoty: ile zajmują i czy zmieści się kolejny plik.

Liczymy wszystko, co wspólnota trzyma na dysku serwera:
- private/<church>/arrangements/<arr>/  nagrania z Reapera i notatki głosowe
- uploads/<church>/                     logo, tło, przejście, zdjęcia powitań

Limit sprawdzamy tylko tam, gdzie pliki przybywają (nagrania, notatki,
zdjęcia). Logo, tło i przejście zawsze podmieniają jeden plik, więc nie rosną.
"""
import os

from flask import current_app

DEFAULT_LIMIT_MB = 2048     # 2 GB na wspólnotę; zmiana: settings['storage_limit_mb']
WARN_AT = 0.8               # od 80% admin widzi ostrzeżenie


def _dir_size(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def limit_bytes(church):
    mb = DEFAULT_LIMIT_MB
    try:
        mb = int((church.settings or {}).get('storage_limit_mb') or mb)
    except (TypeError, ValueError):
        pass
    return mb * 1024 * 1024


def usage(church):
    """{'total', 'limit', 'pct', 'parts': {...}, 'by_arr': {arr_id: bytes}}"""
    inst = current_app.instance_path
    rec = memos = 0
    by_arr = {}
    arr_root = os.path.join(inst, 'private', church.id, 'arrangements')
    if os.path.isdir(arr_root):
        for aid in os.listdir(arr_root):
            d = os.path.join(arr_root, aid)
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                try:
                    size = os.path.getsize(os.path.join(d, f))
                except OSError:
                    continue
                if f.startswith('memo-'):
                    memos += size
                else:
                    rec += size
                    by_arr[aid] = by_arr.get(aid, 0) + size
    private_total = _dir_size(os.path.join(inst, 'private', church.id))
    media = _dir_size(os.path.join(inst, 'uploads', church.id))
    other = max(0, private_total - rec - memos)
    total = private_total + media
    limit = limit_bytes(church)
    return {'total': total, 'limit': limit,
            'pct': min(100, round(total * 100 / limit)) if limit else 0,
            'warn': total >= limit * WARN_AT,
            'parts': {'recordings': rec, 'memos': memos, 'media': media + other},
            'by_arr': by_arr}


def has_room(church, incoming, freed=0):
    """Czy plik o rozmiarze `incoming` się zmieści (po zwolnieniu `freed`)."""
    u = usage(church)
    return u['total'] - freed + incoming <= u['limit']


def human(n):
    """Rozmiar dla ludzi: 340 KB, 12.5 MB, 2 GB."""
    n = float(n or 0)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            txt = f'{n:.0f}' if unit in ('B', 'KB') or n >= 100 else f'{n:.1f}'
            return (txt[:-2] if txt.endswith('.0') else txt) + ' ' + unit
        n /= 1024
