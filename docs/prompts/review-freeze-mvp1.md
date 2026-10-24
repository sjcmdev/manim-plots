# Prompt: przegląd przed zamrożeniem 0.1 i architektury

Jesteś niezależnym recenzentem. Ten sam prompt dostają dwaj recenzenci, którzy nie widzą
swoich raportów. Celem jest **zamrożenie zakresu 0.1 (MVP1) i architektury**: po tym przeglądzie
maintainer zmienia status ADR 0001 i `docs/scope.md` na *Frozen*, a każda późniejsza zmiana
kontraktu wymaga nowego ADR. Szukasz więc wszystkiego, co po zamrożeniu byłoby drogie: błędu
w kontrakcie, sprzeczności między dokumentami, luki w zakresie, odstępstwa od Manima, którego
nikt nie zapisał, i architektury większej, niż wymaga problem.

Pracuj adwersarialnie i konkretnie. Każde znalezisko ma dowód: plik i linię w repozytorium,
albo symbol i linię w źródle Manima. Nie chwal. Nie streszczaj dokumentów. Jeśli coś jest
dobrze, wystarczy jedno zdanie w sekcji *Sound as-is*.

Raport po angielsku. Kod niepotrzebny; jeśli coś sprawdzasz eksperymentem, pokaż komendę
i wynik.

## 1. Co przeczytać

W tej kolejności, w całości:

1. `docs/grill-log.md` — D1-D21, szczególnie D17-D21 (decyzje po proofs of concept).
2. `PLAN.md`.
3. `docs/scope.md` — wszystkie `F-*`, tabela invalid input, paper checks, traceability.
4. `docs/adr/0001-architecture.md`.
5. `docs/architecture-review-2026-10-24.md` — recenzja zrobiona skillami arch-crew. Oceń ją
   tak samo krytycznie jak resztę: czy jej cztery znaleziska są trafne, czy czegoś brakuje,
   czy coś jest zbędne.
6. `docs/api-sketch.md` (komentarze maintainera, historyczne) i `docs/parity-survey.md`
   (sekcja 1, Manim).
7. Raporty PoC: `docs/poc-points-property.md`, `docs/poc2-frame-lifecycle.md`,
   `docs/poc3-stack-context.md`, `docs/poc4-keyed-alignment.md`, i kod `poc4/model.py`,
   `poc4/context.py` jako najbliższy produkcji model mechanizmu.
8. `CONTRIBUTING.md`, `TODO.md`, `pyproject.toml`, `tools/check.py`, `tests/`.

Źródła Manima:

- **0.21.0**: `.venv\Lib\site-packages\manim\`.
- **0.22.0**: rozpakowane w cache uv:
  `C:\Users\Franek\AppData\Local\uv\cache\archive-v0\4EyJTiZ3HPBhfsYn9Inoz\manim\`. Tylko
  do czytania. 0.1 obiecuje obie wersje (F-1007), a mechanizm opiera się na wnętrzu
  Manima, więc to jest tu ważne.

Cytując Manim, podawaj symbol, potem linię (`transform.py::Transform.begin`, `:211`) i wersję,
jeśli linie się różnią.

## 2. Co zbadać

### A. Architektura

1. Czy podział na `core/` (tylko NumPy) i `mobjects/` jest właściwy i wystarczający? Co
   z mechanizmu (ramka, cykl życia, kontekst stosu, wyrównanie po kluczu) da się przenieść do
   rdzenia, żeby było testowalne bez mobjectu, a co musi zostać po stronie Manima?
2. Najmniejsza architektura: co w 0.1 jest większe, niż wymaga wymaganie? Wskaż konkretne
   `F-*` lub części mechanizmu do wycięcia albo odroczenia, z kosztem pozostawienia.
3. Cykl życia liścia jako maszyna stanów: wypisz stany i zdarzenia z PLAN (reguły 1-5),
   F-903..F-907, D19-D21 i `poc4/model.py`. Zbuduj tabelę stan × zdarzenie. Każda komórka
   nieokreślona przez dokumenty jest znaleziskiem. Szczególnie: zagnieżdżone animacje
   (`AnimationGroup`, `Succession`), animacja na artyście i jego układzie naraz, remover
   w trakcie innej animacji, `become` w trakcie animacji, `copy()` w każdym stanie,
   `refresh()` w trakcie animacji.
4. Kontrakt ze stosu (D19, F-917): wypisz każdą ramkę, zmienną lokalną i linię, na której
   mechanizm polega (raport PoC 4, *Updated stack and source contract*), i **porównaj każdą
   między 0.21.0 a 0.22.0** w źródłach. Czy mechanizm z PoC 4 działałby na 0.22 bez zmian?
   Jeśli nie — to jest bloker zamrożenia, bo F-1007 obiecuje 0.22.
5. Kontrakty publiczne (ADR 0001 §3: `Scale`, `Locator`, `Formatter`, `Source`, `Payload`):
   czy coś w nich wymusi breaking change w 0.2 — polar (nieseparowalny), osie dat, pola
   (`region`), 3D, druga skala? Powtórz paper checks z `docs/scope.md` w świetle ramki
   (siatka jest planarna 2D) i natywnego kanału danych.
6. Wydajność: czy F-1001 jest dobrze zdefiniowany po zmianach (pula ticków, symulacja przy
   `suspend`, updater co klatkę, ścieżka dwuliniowa)? Które koszty są poza bramką, a powinny
   być w niej?

### B. Zgodność z Manimem (D17 — cel nadrzędny)

Korpus: każda scena przykładowa `.. manim::` w docstringach zainstalowanego Manima 0.21.0 —
`mobject/graphing/coordinate_systems.py` (34), `mobject/graphing/functions.py` (5),
`mobject/graphing/number_line.py` (1), `animation/updaters/mobject_update_utils.py` (4),
`mobject/value_tracker.py` (3) i te z `animation/transform.py`, które używają osi albo
wykresu. Dla każdej sceny:

1. przepisz ją w myślach na manim-plots według PLAN, scope i F-1009 (pisownia Manima,
   `mp.Axes`, `axis_config`, domyślne wartości `Axes()`);
2. zapisz każdą różnicę: w pisowni (czego brakuje albo co nazywa się inaczej), w zachowaniu
   (co użytkownik zobaczy inaczej) i w wydajności. Dla każdej podaj, czy jest zapisana
   w dokumentach jako świadoma (D17-D21, F-907, F-916, F-1008), czy nie;
3. scena, która przechodzi bez żadnej zmiany poza importem, to jeden wiersz „bez różnic”.

Wynik: tabela scena × różnice oraz lista **niezapisanych** różnic, posortowana według tego,
jak często idiom pojawia się w korpusie. Oddziel, co dotyczy 0.1, a co funkcji z 0.2
(`get_area`, `get_riemann_rectangles`, polar…): dla tych drugich wystarczy potwierdzić, że
zamrożone kontrakty 0.1 ich nie blokują.

Do tego idiomy spoza korpusu, które użytkownik Manima pisze często: `always_redraw`,
`ValueTracker` z `add_updater`, `VGroup(ax, graph).animate`, `Transform(graph, ax.plot(g))`,
`ReplacementTransform(ax, new_ax)`, `ax.get_graph_label`, `ax.plot_line_graph`,
`ax.add_coordinates`, `MoveAlongPath(dot, graph)`, `ax.i2gp` w updaterze, `Create(ax)`,
`Write(ax.x_axis.numbers)`, `self.add(ax, graph)` w różnej kolejności.

### C. Spójność dokumentów

PLAN, scope, ADR 0001, grill-log, architecture review, TODO, CONTRIBUTING i raporty PoC:
każda sprzeczność, nieaktualne zdanie (np. pozostałości testu shadow, `mp.Group`,
`override_animate`, `refresh()` jako wymóg po `Uncreate`), numer `F-*` bez pokrycia albo
wskazujący na nieistniejące decyzje, liczby, które się nie zgadzają (liczba wymagań 0.1,
liczba modułów). Podaj dokładne miejsca.

### D. Gotowość zakresu 0.1 do zamrożenia

1. `F-*` z tierem 0.1 **niedookreślone** na tyle, że implementacja musiałaby zgadywać
   (wymień, czego brakuje).
2. `F-*` z tierem 0.1, które warto **wyciąć albo odroczyć** — z uzasadnieniem kosztem
   i wartością dla użytkownika Manima.
3. **Brakujące** wymagania: rzeczy, które implementacja 0.1 musi rozstrzygnąć, a których
   żaden `F-*` nie nazywa (np. harmonogram puli ticków, gęstość siatki, introducery
   z punktem z konstruktora, kolor domyślny, zachowanie przy funkcjach skalarnych).
4. Otwarte kontrakty z ADR 0001 (*What stays open*) i recenzji arch-crew (znaleziska 1-4):
   które muszą być rozstrzygnięte **przed** zamrożeniem, a które mogą poczekać.

### E. Strategia testów

Portfel dowodów z `docs/architecture-review-2026-10-24.md`: czy pokrywa nazwane ryzyka, czy
czegoś jest za dużo, czy wyrocznie są niezależne (zwłaszcza testy portowane z PoC napisanych
przez model).

## 3. Zasady

- Tylko czytanie. Jedyny plik, który tworzysz, to raport z sekcji 4. Nie zmieniaj niczego
  w repozytorium, nie commituj, nie instaluj, bez sieci.
- Eksperymenty dozwolone, jeśli nie zapisują w repo: `.venv\Scripts\python.exe` z kodem
  w pamięci albo w katalogu tymczasowym poza repo. Bez `tempfile.mkdtemp` w repo.
- Nie powtarzaj PoC. Jeśli wątpisz w wynik PoC, wskaż test i powód.
- Znalezisko bez dowodu nie jest znaleziskiem.

## 4. Raport

Zapisz do pliku podanego w poleceniu uruchomienia (`docs/reviews/…`). Struktura:

1. **Verdict** — jedno z: *freeze*, *freeze after the listed blockers*, *do not freeze*,
   z jednym zdaniem uzasadnienia.
2. **Freeze blockers** — numerowana lista; każdy: problem, dowód, poprawka, koszt.
3. **Findings** — według sekcji A-E, każde z wagą (*major* / *minor*), dowodem i poprawką.
4. **Manim compatibility table** (sekcja B) i lista niezapisanych różnic.
5. **Lifecycle state × event table** (A.3) z komórkami nieokreślonymi zaznaczonymi.
6. **0.21 vs 0.22 stack-contract diff** (A.4).
7. **Cut or defer** — lista `F-*` lub części mechanizmu z kosztem i wartością.
8. **Sound as-is** — krótko.
