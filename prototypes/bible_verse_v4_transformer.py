# -*- coding: utf-8 -*-
"""V4: backend transformerowy (sentence-transformers) dla sugestii wersetów.

Prawdziwe rozumienie KONTEKSTU zdania (nie tylko wspólne słowa):
model wielojęzyczny koduje całe zdania — „ślepym przejrzenie" dopasuje
się do „abym przejrzał" nawet bez wspólnych słów kluczowych.

WYMAGA internetu RAZ (pobranie modelu ~0.5 GB), potem pełny offline.
Nie dało się przetestować w środowisku deweloperskim (HF zablokowany) —
uruchom u siebie:

    pip install sentence-transformers
    python bible_verse_v4_transformer.py                # benchmark 10 testów
    python bible_verse_v4_transformer.py "tekst pieśni" # sugestie

Architektura: transformer zastępuje FastText jako głos semantyczny;
BM25 + cytaty + fuzja RRF zostają z V3 (bible_verse_suggest.py).
Opcjonalny reranker (cross-encoder) czyta pieśń+werset RAZEM i
przestawia top-40 — najbliższe "przeczytał i zrozumiał".
"""
import os, sys, numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
from bible_verse_suggest import (VerseSuggester, ref_pl, norm_tokens)

# Model: wielojęzyczny, sprawdzony na polskim, rozsądny rozmiar.
# Alternatywy: 'intfloat/multilingual-e5-small' (lepszy, wymaga prefiksów
# "query: "/"passage: "), 'sdadas/st-polish-paraphrase-from-distilroberta'
# (czysto polski — prawdopodobnie najlepszy do tego zadania).
ST_MODEL = os.environ.get("JAFA_ST_MODEL", "sdadas/st-polish-paraphrase-from-distilroberta")
RERANK_MODEL = os.environ.get("JAFA_RERANK_MODEL", "")  # np. "sdadas/polish-reranker-base-ranknet"

class TransformerSuggester(VerseSuggester):
    """V4: semantyka z sentence-transformera, reszta (BM25/cytaty) z V3."""

    def __init__(self):
        super().__init__()  # buduje też FastText (fallback + cache reuse)
        from sentence_transformers import SentenceTransformer
        print(f"Ładowanie modelu zdaniowego: {ST_MODEL}")
        self.st = SentenceTransformer(ST_MODEL)
        tag = ST_MODEL.replace('/', '_')
        cache = os.path.join(DIR, f"M_st_{tag}.npy")
        if os.path.exists(cache):
            self.M_st = np.load(cache)
        else:
            print("Kodowanie 31k wersetów transformerem (raz, ~5-15 min na CPU)...")
            # kontekst ±1 werset, jak w V3
            ctx = []
            for i, v in enumerate(self.verses):
                parts = [v]
                if i > 0 and self.refs[i-1].split()[0] == self.refs[i].split()[0]:
                    parts.insert(0, self.verses[i-1])
                if i+1 < len(self.verses) and self.refs[i+1].split()[0] == self.refs[i].split()[0]:
                    parts.append(self.verses[i+1])
                ctx.append(" ".join(parts))
            self.M_st = self.st.encode(ctx, batch_size=64, show_progress_bar=True,
                                       normalize_embeddings=True).astype(np.float32)
            np.save(cache, self.M_st)
        self.reranker = None
        if RERANK_MODEL:
            from sentence_transformers import CrossEncoder
            print(f"Ładowanie rerankera: {RERANK_MODEL}")
            self.reranker = CrossEncoder(RERANK_MODEL)

    def suggest(self, lyrics, topn=5):
        toks_raw = norm_tokens(lyrics)
        if not toks_raw: return [], []

        # cytaty — jak w V3 (stemowane 3-gramy)
        quotes = []
        if self.stemmed is not None:
            q3 = self._ngrams(self.stem_tokens(lyrics), 3)
            for i, vg in enumerate(self.verse_3g):
                hit = len(q3 & vg)
                if hit >= 2: quotes.append((hit, i))
            quotes.sort(reverse=True)

        # semantyka: TRANSFORMER (całe zdania, kontekst)
        q = self.st.encode([lyrics], normalize_embeddings=True)[0].astype(np.float32)
        sem = self.M_st @ q
        sem_rank = np.argsort(-sem)

        # fuzja z BM25 (RRF 0.7/0.3) — jak w V3
        K = 60
        rrf = np.zeros(len(self.refs))
        for rank, i in enumerate(sem_rank[:300]): rrf[i] += 0.70/(K+rank)
        bs = None
        if self.bm25 is not None:
            bs = np.array(self.bm25.get_scores(self.stem_tokens(lyrics)))
            bm_rank = np.argsort(-bs)
            for rank, i in enumerate(bm_rank[:300]): rrf[i] += 0.30/(K+rank)

        # opcjonalny reranker: czyta (pieśń, werset) RAZEM, przestawia top-40
        order = np.argsort(-rrf)
        if self.reranker is not None:
            cand = [int(i) for i in order[:40] if rrf[i] > 0]
            pairs = [(lyrics, self.verses[i]) for i in cand]
            scores = self.reranker.predict(pairs)
            order = [cand[j] for j in np.argsort(-np.asarray(scores))]
            rrf_display = {i: float(s) for i, s in zip(cand, scores)}
        else:
            rrf_display = None

        out, seen = [], set()
        for i in order:
            i = int(i)
            if rrf_display is None and rrf[i] <= 0: break
            ch = self.chap_of[i]
            if ch in seen: continue
            seen.add(ch)
            score = rrf_display[i] if rrf_display else float(rrf[i])
            out.append((score, i))
            if len(out) >= topn: break

        # bonus "prawie dosłowny" — jak w V3
        if bs is not None:
            sd = bs.std() or 1.0
            bz = (bs - bs.mean()) / sd
            top_bm = int(np.argmax(bs))
            if bz[top_bm] >= 4.5 and self.chap_of[top_bm] not in seen:
                out.append((float(bz[top_bm]), top_bm))
        return quotes[:2], out


def main():
    sugg = TransformerSuggester()
    refs = sugg.refs
    if len(sys.argv) > 1:
        quotes, sem = sugg.suggest(" ".join(sys.argv[1:]), topn=6)
        print("\n=== SUGEROWANE SIGLA (V4 transformer) ===")
        for h, i in quotes: print(f"  CYTAT  {ref_pl(refs[i]):16} ({h} wspólnych fraz)")
        for s, i in sem:   print(f"  temat  {ref_pl(refs[i]):16} ({s:.3f})")
        return
    # syntetyczny benchmark — te same 10 testów co V1/V3
    from bible_verse_suggest import main as _m  # noqa
    tests_src = open(os.path.join(DIR, "bible_verse_suggest.py"), encoding='utf-8').read()
    # (testy trzymane w jednym miejscu — odpal tam CLI albo porównaj ręcznie)
    tests = [
        ("Pasterz","Ty jesteś moim pasterzem niczego mi nie braknie prowadzisz mnie nad spokojne wody dusza moja odpoczywa w Tobie na zielonych łąkach","PSA 23"),
        ("Łaska","Łaską zbawieni jesteśmy przez wiarę nie z uczynków to dar Boży nikt niech się nie chlubi","EPH 2"),
        ("Jak łania","Jak łania pragnie wody ze strumieni tak moja dusza pragnie Ciebie Boże tęskni za Tobą dusza moja","PSA 42"),
        ("Warownia","Bóg jest naszą ucieczką i siłą pomocą w utrapieniach dlatego nie będziemy się bać choćby ziemia się poruszyła","PSA 46"),
        ("Jego rany","On był zraniony za nasze występki starty za nasze nieprawości a Jego ranami jesteśmy uzdrowieni","ISA 53"),
        ("Tak umiłował","Bóg tak umiłował świat że dał swego jednorodzonego Syna aby każdy kto wierzy nie zginął ale miał życie wieczne","JHN 3"),
        ("Święty Baranek","Godzien jest Baranek zabity przyjąć moc i bogactwo i mądrość i siłę i cześć i chwałę święty święty święty Pan Bóg wszechmogący","REV 5"),
        ("Błogosław duszo","Błogosław duszo moja Pana i wszystko co we mnie Jego święte imię nie zapominaj o wszystkich Jego dobrodziejstwach","PSA 103"),
        ("Nowe stworzenie","Kto jest w Chrystusie nowym jest stworzeniem stare przeminęło oto wszystko stało się nowe","2CO 5"),
        ("Skrzydła orła","Ci którzy ufają Panu nabierają nowych sił wzbijają się na skrzydłach jak orły biegną a się nie męczą","ISA 40"),
        # NOWE: czysto kontekstowe (mało wspólnych słów z celem — tu FastText
        # zawodzi, transformer powinien dać radę)
        ("Kontekst: pasterz bez słów","Nie zabraknie mi niczego bo Ty się troszczysz prowadzisz tam gdzie odpocznę bezpiecznie","PSA 23"),
        ("Kontekst: syn marnotrawny","Wracam do domu Ojca choć zgrzeszyłem On wybiega mi na spotkanie i przyjmuje mnie z radością","LUK 15"),
        ("Kontekst: burza ucisza","Gdy fale się piętrzą a wiatr szaleje Ty mówisz jedno słowo i wszystko cichnie",("MRK 4","LUK 8","MAT 8","PSA 107")),  # paralelne opisy
    ]
    hits = 0
    for name, lyr, tgt in tests:
        tgts = tgt if isinstance(tgt, tuple) else (tgt,)
        q, sem = sugg.suggest(lyr)
        got = [refs[i] for _, i in q] + [refs[i] for _, i in sem]
        ok = any(any(r.startswith(t) for t in tgts) for r in got)
        hits += ok
        top = " | ".join(ref_pl(refs[i]) for _, i in (q + sem)[:5])
        print(f"{'✓' if ok else '✗'} [{name}] -> {top}")
    print(f"\nV4: {hits}/{len(tests)}  (porównaj z V3: python bible_verse_suggest.py)")

if __name__ == '__main__':
    main()
