# -*- coding: utf-8 -*-
"""Prototyp: sugestie wersetów biblijnych do tekstu pieśni (offline). V3.

Silnik hybrydowy (trzy głosy + fuzja):
  1. SEMANTYKA — FastText trenowany na UBG (subwordy => polska fleksja),
     embeddingi wersetów ważone IDF z oknem kontekstu ±1 werset;
  2. LEKSYKA — BM25 na korpusie stemowanym (pystempel + normalizacja
     wariantów lecz/ale, mię/mnie, twe/twój...); rzadkie słowa ważą mocno;
  3. CYTATY — wspólne 3-gramy stemów: pieśni cytujące Biblię wprost
     łapane z bardzo wysoką precyzją i pokazywane na szczycie.
Fuzja: ważony Reciprocal Rank Fusion (semantyka 0.7 / BM25 0.3) + jeden
"prawie dosłowny" werset BM25 (z-score >= 4.5) doklejany jako dodatkowy
wiersz. Zależności opcjonalne: bez pystempel/rank_bm25 działa sama
semantyka + cytaty 4-gramowe (tryb V1).

Wyjście: same SIGLA (np. Ps 23:1-3) — zero problemów z prawami.

Użycie:
  python bible_verse_suggest.py "tekst piosenki..."   # sugestie
  python bible_verse_suggest.py                        # testy jakości
"""
import re, math, sys, os, json, pickle, urllib.request
from collections import Counter
import numpy as np
from gensim.models import FastText

try:
    from pystempel import Stemmer as _PLStemmer
    HAS_STEM = True
except ImportError:
    HAS_STEM = False
try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

DIR = os.path.dirname(os.path.abspath(__file__))

CORPUS_URLS = {
    "ubg.txt":  "https://raw.githubusercontent.com/BibleNLP/ebible/main/corpus/pol-polubg.txt",
    "vref.txt": "https://raw.githubusercontent.com/BibleNLP/ebible/main/metadata/vref.txt",
}

def ensure_corpus():
    """Pobiera UBG + sigla przy pierwszym uruchomieniu (raz, ~5 MB)."""
    for fname, url in CORPUS_URLS.items():
        path = os.path.join(DIR, fname)
        if os.path.exists(path):
            continue
        print(f"Pobieranie {fname} (pierwsze uruchomienie)...")
        urllib.request.urlretrieve(url, path)

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

# Normalizacja wariantów (archaizmy, spójniki, zaimki — psują n-gramy cytatów)
VARIANTS = {
    'lecz':'ale', 'iż':'że', 'iżby':'żeby', 'mię':'mnie',
    'tyś':'ty', 'twe':'twój', 'twa':'twój',
    'me':'mój', 'moje':'mój', 'moja':'mój', 'swe':'swój',
    'panie':'pan', 'jahwe':'pan', 'jehowa':'pan',
}

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

class VerseSuggester:
    """Silnik V3. Buduje/wczytuje cache przy pierwszym użyciu."""

    def __init__(self):
        ensure_corpus()
        self.verses, self.refs = load_bible()
        self.chap_of = [r.rsplit(':', 1)[0] for r in self.refs]
        self.tokenized = [norm_tokens(v) for v in self.verses]

        # ── semantyka: FastText (niestemowany — stemy zamulają embeddingi) ──
        cache = os.path.join(DIR, "bible_model.cache")
        if os.path.exists(cache):
            self.model = FastText.load(cache)
        else:
            print("Trening FastText na Biblii (raz, ~1-2 min; potem cache)...")
            self.model = FastText(sentences=self.tokenized, vector_size=100, window=5,
                                  min_count=3, sg=1, epochs=25, min_n=3, max_n=5,
                                  workers=4, seed=42, bucket=100000)
            self.model.save(cache)

        df = Counter()
        for toks in self.tokenized: df.update(set(toks))
        self.N = len(self.tokenized)
        self.idf = {w: math.log(self.N / (1 + c)) for w, c in df.items()}

        emb_cache = os.path.join(DIR, "verse_embeddings.npy")
        if os.path.exists(emb_cache):
            self.M = np.load(emb_cache)
        else:
            print("Embeddingi wersetów (okno ±1)...")
            self.M = np.zeros((len(self.verses), 100), dtype=np.float32)
            for i in range(len(self.tokenized)):
                toks = list(self.tokenized[i])
                if i > 0 and self.refs[i-1].split()[0] == self.refs[i].split()[0]:
                    toks += self.tokenized[i-1]
                if i+1 < len(self.tokenized) and self.refs[i+1].split()[0] == self.refs[i].split()[0]:
                    toks += self.tokenized[i+1]
                e = self.embed(toks)
                if e is not None: self.M[i] = e
            np.save(emb_cache, self.M)

        # ── leksyka + cytaty: stemowane (opcjonalnie) ──
        self._stem_cache = {}
        if HAS_STEM:
            self._stemmer = _PLStemmer.polimorf()
            spkl = os.path.join(DIR, "stemmed_verses.pkl")
            if os.path.exists(spkl):
                self.stemmed = pickle.load(open(spkl, 'rb'))
            else:
                print("Stemming korpusu (raz)...")
                self.stemmed = [self.stem_tokens(v) for v in self.verses]
                pickle.dump(self.stemmed, open(spkl, 'wb'))
            self.verse_3g = [self._ngrams(t, 3) for t in self.stemmed]
        else:
            self.stemmed = None
            self.verse_4g = [self._ngrams(t, 4) for t in self.tokenized]

        self.bm25 = BM25Okapi(self.stemmed) if (HAS_BM25 and self.stemmed) else None

    # ── pomocnicze ──
    def stem(self, w):
        if w in self._stem_cache: return self._stem_cache[w]
        s = VARIANTS.get(w) or (self._stemmer(w) if HAS_STEM else w) or w
        s = VARIANTS.get(s, s)
        self._stem_cache[w] = s
        return s

    def stem_tokens(self, text):
        return [self.stem(t) for t in norm_tokens(text)]

    @staticmethod
    def _ngrams(toks, n):
        return set(tuple(toks[i:i+n]) for i in range(len(toks)-n+1))

    def embed(self, tokens):
        vecs, ws = [], []
        for t in tokens:
            try: v = self.model.wv[t]
            except KeyError: continue
            vecs.append(v); ws.append(self.idf.get(t, math.log(self.N / 1.5)))
        if not vecs: return None
        e = np.average(vecs, axis=0, weights=ws)
        n = np.linalg.norm(e)
        return e / n if n > 0 else None

    # ── główne API ──
    def suggest(self, lyrics, topn=5):
        """Zwraca (cytaty, dopasowania): listy par (score, indeks wersetu).
        Ostatnie dopasowanie może być 'prawie dosłownym' bonusem BM25
        (score > 1 => z-score BM25, nie RRF)."""
        toks_raw = norm_tokens(lyrics)
        if not toks_raw: return [], []

        # cytaty
        quotes = []
        if self.stemmed is not None:
            q3 = self._ngrams(self.stem_tokens(lyrics), 3)
            for i, vg in enumerate(self.verse_3g):
                hit = len(q3 & vg)
                if hit >= 2: quotes.append((hit, i))
        else:
            q4 = self._ngrams(toks_raw, 4)
            for i, vg in enumerate(self.verse_4g):
                hit = len(q4 & vg)
                if hit: quotes.append((hit, i))
        quotes.sort(reverse=True)

        # semantyka
        e = self.embed(toks_raw)
        sem = (self.M @ e) if e is not None else np.zeros(len(self.refs))
        sem_rank = np.argsort(-sem)

        # fuzja z BM25 (ważony RRF 0.7/0.3); bez BM25 — sama semantyka
        K = 60
        rrf = np.zeros(len(self.refs))
        for rank, i in enumerate(sem_rank[:300]): rrf[i] += 0.70/(K+rank)
        bs = None
        if self.bm25 is not None:
            bs = np.array(self.bm25.get_scores(self.stem_tokens(lyrics)))
            bm_rank = np.argsort(-bs)
            for rank, i in enumerate(bm_rank[:300]): rrf[i] += 0.30/(K+rank)

        best = np.argsort(-rrf)
        out, seen = [], set()
        for i in best:
            if rrf[i] <= 0: break
            ch = self.chap_of[i]
            if ch in seen: continue
            seen.add(ch)
            out.append((float(rrf[i]), int(i)))
            if len(out) >= topn: break

        # bonus: JEDEN prawie dosłowny werset BM25 (nie zabiera miejsc semantyce)
        if bs is not None:
            sd = bs.std() or 1.0
            bz = (bs - bs.mean()) / sd
            top_bm = int(np.argmax(bs))
            if bz[top_bm] >= 4.5 and self.chap_of[top_bm] not in seen:
                out.append((float(bz[top_bm]), top_bm))

        return quotes[:2], out


def main():
    if not (HAS_STEM and HAS_BM25):
        print("(Uwaga: brak pystempel/rank_bm25 — tryb V1, sama semantyka."
              " Doinstaluj: pip install pystempel rank_bm25)")
    sugg = VerseSuggester()
    refs = sugg.refs

    # ── Tryb CLI: python bible_verse_suggest.py "tekst piosenki..." ──
    if len(sys.argv) > 1:
        lyrics = " ".join(sys.argv[1:])
        quotes, sem = sugg.suggest(lyrics, topn=6)
        print("\n=== SUGEROWANE SIGLA ===")
        for hitc, i in quotes:
            print(f"  CYTAT   {ref_pl(refs[i]):16} ({hitc} wspólnych fraz)")
        for s_, i in sem:
            tag = "~dosł." if s_ > 1.0 else "temat "
            print(f"  {tag}  {ref_pl(refs[i]):16} ({s_:.2f})")
        return

    # ── TESTY: własne teksty w stylu uwielbienia (bez praw autorskich) ──
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
    print("TESTY JAKOŚCI — czy celny fragment jest w TOP (cytaty + dopasowania)")
    print("═"*74)
    hits = 0
    for name, lyrics, target in tests:
        quotes, sem = sugg.suggest(lyrics)
        got = [("CYTAT", refs[i], h) for h, i in quotes] + [("match", refs[i], round(s, 3)) for s, i in sem]
        found = any(r.startswith(target) for _, r, _ in got)
        hits += found
        print(f"\n{'✓' if found else '✗'} [{name}]  cel: {ref_pl(target + ':1').rsplit(':',1)[0]}")
        for kind, r, sc in got[:6]:
            print(f"     {kind:5} {ref_pl(r):14} {sc}")
    print("\n" + "═"*74)
    print(f"WYNIK: {hits}/{len(tests)} trafień")

if __name__ == '__main__':
    main()

# ─────────────────────────────────────────────────────────────────
# WYNIKI:
#  V1 (sama semantyka + surowe 4-gramy), 2026-07-04:
#   - testy syntetyczne: 10/10
#   - realny śpiewnik (71 pieśni), 14 ze znanym źródłem: 9/14
#  V3 (semantyka + stemowany BM25 + stemowane cytaty, ważony RRF
#      0.7/0.3 + bonus "prawie dosłowny" BM25 z>=4.5), 2026-07-04:
#   - testy syntetyczne: 10/10 (bez regresji)
#   - realny śpiewnik: 11/14 (+ nowe trafienia: Obj 4:8 dla "Święty,
#     święty, święty", Ps 62:1, J 1:29 "Oto Baranek Boży")
#   - pudła: parafrazy daleko od słownictwa UBG (Jl 3:10, Lm 3:22-23,
#     Ps 104:30) — sugestie i tak tematycznie sensowne.
#  Ślepe uliczki (zbadane): stemowanie SEMANTYKI pogarsza (8/14);
#  fuzja z-score gorsza od RRF (9/14); chunki zwrotek bez zmian.
#
# Dane: eBible.org, pol-polubg (Uwspółcześniona Biblia Gdańska, wolna
# licencja) + metadata/vref.txt (sigla) z repo BibleNLP/ebible.
#
# Droga do produkcji:
#  - shipować TYLKO ubg.txt (~4.5 MB) + vref.txt; modele i embeddingi
#    liczyć RAZ przy pierwszym uruchomieniu i cache'ować (~65 MB);
#  - sugestie liczyć przy zapisie piosenki do bazy (cache w DB),
#    zero pracy podczas nabożeństwa;
#  - UI pokazuje wyłącznie SIGLA (Ps 23:1-3) — bez tekstu wersetów;
#  - zależności: gensim + numpy (wymagane), pystempel + rank_bm25
#    (opcjonalne — bez nich silnik działa w trybie V1).
# ─────────────────────────────────────────────────────────────────
