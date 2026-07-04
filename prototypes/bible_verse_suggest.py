# -*- coding: utf-8 -*-
"""Prototyp: sugestie wersetów biblijnych do tekstu pieśni (offline).

Silnik: FastText trenowany na UBG (subwordy => polska fleksja) +
embeddingi wersetów ważone IDF z oknem kontekstu ±1 + detektor cytatów.
Wyjście: same SIGLA (np. Ps 23:1-3) — zero problemów z prawami.
"""
import re, math, sys, json
from collections import Counter
import numpy as np
from gensim.models import FastText

DIR = "/tmp/claude-0/-home-user-JafaStageCenter/c433b786-994d-51dd-bbb0-3a97a4020736/scratchpad"

# ── Polskie skróty ksiąg (USFM -> polskie sigla) ──
BOOK_PL = {
 'GEN':'Rdz','EXO':'Wj','LEV':'Kpł','NUM':'Lb','DEU':'Pwt','JOS':'Joz','JDG':'Sdz','RUT':'Rt',
 '1SA':'1Sm','2SA':'2Sm','1KI':'1Krl','2KI':'2Krl','1CH':'1Krn','2CH':'2Krn','EZR':'Ezd','NEH':'Ne',
 'EST':'Est','JOB':'Hi','PSA':'Ps','PRO':'Prz','ECC':'Koh','SNG':'PnP','ISA':'Iz','JER':'Jr',
 'LAM':'Lm','EZK':'Ez','DAN':'Dn','HOS':'Oz','JOL':'Jl','AMO':'Am','OBA':'Ab','JON':'Jon',
 'MIC':'Mi','NAM':'Na','HAB':'Ha','ZEP':'So','HAG':'Ag','ZEC':'Za','MAL':'Ml',
 'MAT':'Mt','MRK':'Mk','LUK':'Łk','JHN':'J','ACT':'Dz','ROM':'Rz','1CO':'1Kor','2CO':'2Kor',
 'GAL':'Ga','EPH':'Ef','PHP':'Flp','COL':'Kol','1TH':'1Tes','2TH':'2Tes','1TI':'1Tm','2TI':'2Tm',
 'TIT':'Tt','PHM':'Flm','HEB':'Hbr','JAS':'Jk','1PE':'1P','2PE':'2P','1JN':'1J','2JN':'2J',
 '3JN':'3J','JUD':'Jud','REV':'Obj'
}

STOP = set("""a aby ale będzie bo być co czy dla do i ich jak jest jego jej im ja je jako
mnie mi mu na nad nie o od po przez się swoje swoją swój ta tak też to ty twoja twoje twój
w we z za że ów oto ku the jestem jesteś був gdy তো których który która które kto ma
przed ani lub oraz bez ten tej tym te go by jeśli więc niech was nas wam nam wy my on ona ono oni""".split())

def norm_tokens(text):
    text = text.lower()
    text = re.sub(r'\[.*?\]', ' ', text)           # akordy [C] itd.
    toks = re.findall(r'[a-ząćęłńóśźż]+', text)
    return [t for t in toks if len(t) > 1 and t not in STOP]

def load_bible():
    verses, refs = [], []
    with open(f"{DIR}/ubg.txt", encoding='utf-8') as f1, open(f"{DIR}/vref.txt", encoding='utf-8') as f2:
        for text, ref in zip(f1, f2):
            text, ref = text.strip(), ref.strip()
            if not text: continue
            book = ref.split()[0]
            if book not in BOOK_PL: continue   # pomijamy deuterokanon spoza UBG
            verses.append(text); refs.append(ref)
    return verses, refs

def ref_pl(ref):
    book, cv = ref.split()
    return f"{BOOK_PL[book]} {cv}"

def main():
    print("Wczytywanie UBG...")
    verses, refs = load_bible()
    print(f"  {len(verses)} wersetów")

    tokenized = [norm_tokens(v) for v in verses]

    print("Trening FastText na Biblii (subwordy => fleksja)...")
    model = FastText(sentences=tokenized, vector_size=100, window=5, min_count=3,
                     sg=1, epochs=25, min_n=3, max_n=5, workers=4, seed=42)
    print(f"  słownik: {len(model.wv)} słów")

    # IDF
    df = Counter()
    for toks in tokenized: df.update(set(toks))
    N = len(tokenized)
    idf = {w: math.log(N / (1 + c)) for w, c in df.items()}
    def w_idf(w): return idf.get(w, math.log(N / 1.5))

    def embed(tokens):
        if not tokens: return None
        vecs, ws = [], []
        for t in tokens:
            try: v = model.wv[t]      # FastText: OOV przez subwordy
            except KeyError: continue
            vecs.append(v); ws.append(w_idf(t))
        if not vecs: return None
        e = np.average(vecs, axis=0, weights=ws)
        n = np.linalg.norm(e)
        return e / n if n > 0 else None

    print("Embeddingi wersetów (okno ±1)...")
    ctx_tokens = []
    for i in range(len(tokenized)):
        toks = list(tokenized[i])
        if i > 0 and refs[i-1].split()[0] == refs[i].split()[0]: toks += tokenized[i-1]
        if i+1 < len(tokenized) and refs[i+1].split()[0] == refs[i].split()[0]: toks += tokenized[i+1]
        ctx_tokens.append(toks)
    M = np.zeros((len(verses), 100), dtype=np.float32)
    for i, toks in enumerate(ctx_tokens):
        e = embed(toks)
        if e is not None: M[i] = e

    # ── Detektor bezpośrednich cytatów: 4-gramy słów ──
    def ngrams(toks, n=4): return set(tuple(toks[i:i+n]) for i in range(len(toks)-n+1))
    verse_ngrams = [ngrams(t) for t in tokenized]

    def suggest(lyrics, topn=5):
        toks = norm_tokens(lyrics)
        # 1. cytaty wprost
        quotes = []
        ln = ngrams(toks)
        if ln:
            for i, vg in enumerate(verse_ngrams):
                hit = len(ln & vg)
                if hit: quotes.append((hit, i))
            quotes.sort(reverse=True)
        # 2. semantyka
        e = embed(toks)
        sem = []
        if e is not None:
            sims = M @ e
            best = np.argsort(-sims)[:topn*4]
            seen_ch = set()
            for i in best:
                ch = refs[i].rsplit(':', 1)[0]
                if ch in seen_ch: continue   # max 1 wynik na rozdział
                seen_ch.add(ch)
                sem.append((float(sims[i]), i))
                if len(sem) >= topn: break
        return quotes[:2], sem

    # ── TESTY: własne teksty w stylu uwielbienia (bez praw autorskich),
    #    każdy celuje w znany fragment ──
    tests = [
        ("Pasterz",       "Ty jesteś moim pasterzem niczego mi nie braknie prowadzisz mnie nad spokojne wody dusza moja odpoczywa w Tobie na zielonych łąkach",  "PSA 23"),
        ("Łaska",         "Łaską zbawieni jesteśmy przez wiarę nie z uczynków to dar Boży nikt niech się nie chlubi",                                             "EPH 2"),
        ("Jak łania",     "Jak łania pragnie wody ze strumieni tak moja dusza pragnie Ciebie Boże tęskni za Tobą dusza moja",                                     "PSA 42"),
        ("Warownia",      "Bóg jest naszą ucieczką i siłą pomocą w utrapieniach dlatego nie będziemy się bać choćby ziemia się poruszyła",                        "PSA 46"),
        ("Jego rany",     "On był zraniony za nasze występki starty za nasze nieprawości a Jego ranami jesteśmy uzdrowieni",                                      "ISA 53"),
        ("Tak umiłował",  "Bóg tak umiłował świat że dał swego jednorodzonego Syna aby każdy kto wierzy nie zginął ale miał życie wieczne",                       "JHN 3"),
        ("Święty Baranek","Godzien jest Baranek zabity przyjąć moc i bogactwo i mądrość i siłę i cześć i chwałę święty święty święty Pan Bóg wszechmogący",       "REV 5"),
        ("Błogosław duszo","Błogosław duszo moja Pana i wszystko co we mnie Jego święte imię nie zapominaj o wszystkich Jego dobrodziejstwach",                    "PSA 103"),
        ("Nowe stworzenie","Kto jest w Chrystusie nowym jest stworzeniem stare przeminęło oto wszystko stało się nowe",                                           "2CO 5"),
        ("Skrzydła orła", "Ci którzy ufają Panu nabierają nowych sił wzbijają się na skrzydłach jak orły biegną a się nie męczą",                                  "ISA 40"),
    ]

    print("\n" + "═"*74)
    print("TESTY JAKOŚCI — czy celny fragment jest w TOP 5 (semantyka) lub cytatach")
    print("═"*74)
    hits = 0
    for name, lyrics, target in tests:
        quotes, sem = suggest(lyrics)
        got = []
        for hitcount, i in quotes: got.append(("CYTAT", ref_pl(refs[i]), hitcount))
        for s, i in sem: got.append(("sem", ref_pl(refs[i]), round(s,3)))
        found = any(refs[i].startswith(target) for _, i in quotes) or \
                any(refs[i].startswith(target) for _, i in sem)
        hits += found
        mark = "✓" if found else "✗"
        print(f"\n{mark} [{name}]  cel: {ref_pl(target + ':1').rsplit(':',1)[0]}")
        for kind, r, sc in got[:6]:
            print(f"     {kind:5} {r:14} {sc}")
    print("\n" + "═"*74)
    print(f"WYNIK: {hits}/{len(tests)} trafień w TOP5")

if __name__ == '__main__':
    main()

# ─────────────────────────────────────────────────────────────────
# WYNIKI (2026-07-04): 10/10 trafień w TOP5 na 10 tekstach testowych
# (Ps 23, Ef 2, Ps 42, Ps 46, Iz 53, J 3, Obj 5, Ps 103, 2Kor 5, Iz 40).
# Cytaty wprost łapane przez 4-gramy (J 3:16 → 7 wspólnych n-gramów),
# parafrazy przez semantykę FastText (Ps 103:2 → 0.945 bez cytatu).
#
# Dane: eBible.org, plik pol-polubg.txt (Uwspółcześniona Biblia Gdańska,
# wolna licencja) + metadata/vref.txt (sigla) z repo BibleNLP/ebible.
#
# Droga do produkcji:
#  - shipować TYLKO ubg.txt (~4.5 MB) + vref.txt; trening FastText
#    (bucket=100k → ~40 MB RAM) i embeddingi wersetów (~15 MB) liczyć
#    RAZ przy pierwszym uruchomieniu i cache'ować na dysk;
#  - sugestie liczyć przy zapisie piosenki do bazy (cache w DB),
#    zero pracy podczas nabożeństwa;
#  - UI pokazuje wyłącznie SIGLA (Ps 23:1-3) — bez tekstu wersetów,
#    więc zero problemów licencyjnych po stronie wyświetlania;
#  - zależności: gensim + numpy (pip).
# ─────────────────────────────────────────────────────────────────
