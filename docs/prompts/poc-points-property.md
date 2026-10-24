# Prompt: proof of concept — property `points` na liściach i koszt przebudowy

Zbuduj **jednorazowy proof of concept**, który ma obalić albo potwierdzić hipotezy
nośne architektury, zanim powstanie jakikolwiek kod biblioteki. To nie jest
implementacja `manim-plots`: nie projektuj API, nie pisz kodu „na później”, nie dotykaj
`src/`. Kod PoC ma być najkrótszym kodem, który rozstrzyga hipotezę.

Kod pisz po angielsku. Raport napisz po angielsku, bo trafia obok ADR do `docs/`.

## 1. Kontekst — przeczytaj przed pisaniem kodu

- `PLAN.md`, sekcja *Integration: the `points` property on library-owned leaves*,
  w całości: cztery reguły (getter zwraca obiekt cache, shadow copy jako test trybu
  przejściowego, override `shift` i `apply_points_function_about_point`, dwa przypadki
  settera) oraz kontrakt animacji przywracających i usuwających.
- `docs/adr/0001-architecture.md`: warstwy `core/` i `mobjects/`, kontrakty, sekcja 4.
- `docs/scope.md`: F-105, F-901..F-909, F-1001, F-1004.
- `docs/api-sketch.md`: A3.2 (`__setattr__` oznacza węzeł jako brudny).

Środowisko: Manim **0.21.0** w `.venv`. Cytując Manim, podawaj najpierw symbol, potem
linię (`indication.py::Wiggle.interpolate_submobject`, `:559`) — taka jest konwencja
`PLAN.md`.

## 2. Hipotezy

Każda hipoteza kończy się werdyktem **CONFIRMED**, **FALSIFIED** albo
**INCONCLUSIVE**, z dowodem: nazwą testu, liczbami i cytatem z kodu Manim.

### H1 — property `points` w ogóle działa na liściu `VMobject`

Minimalny liść: podklasa `VMobject`, której `points` jest property wyliczanym z
`Source -> Map -> placement`. Wystarczy źródło tablicowe i mapa liniowa; `placement`
to uporządkowana lista węzłów afinicznych i nieafinicznych (`PLAN.md`, *Placement is an
ordered chain*). Sprawdź:

- `Mobject.__init__` i `reset_points` (`mobject.py::Mobject.reset_points`) wołają setter,
  zanim stan liścia istnieje — liść musi to przeżyć;
- getter zwraca **ten sam obiekt** cache, gdy pipeline jest czysty (`is`, nie `==`);
- renderer Cairo rysuje liść poprawnie (porównaj klatkę z rysunkiem zwykłego `VMobject`
  o tych samych punktach);
- `leaf.shift(v)`, `leaf.rotate(a)`, `leaf.scale(s)` i `leaf.apply_function(f)` poza
  animacją trafiają do `placement` i przetrwają przebudowę wymuszoną zmianą danych.

### H2 — test shadow odróżnia animację od wywołania bezpośredniego

To jest hipoteza, która najpewniej się nie utrzyma. Analiza na papierze:
`indication.py::Wiggle.interpolate_submobject` (`:559`) najpierw przywraca bufor do
punktów startowych (`submobject.points[:, :] = starting_submobject.points`), a dopiero
potem woła `scale` i `rotate`. Kopia startowa pochodzi z tego samego bufora
(`animation.py::Animation.begin` -> `create_starting_mobject` -> `Mobject.copy`), więc po
linii 559 bufor jest **bit w bit równy** shadow. Override widzi więc czysty bufor i
wkłada `scale` oraz `rotate` do współdzielonego `placement`, na stałe. To samo robi
`movement.py::Homotopy.interpolate_submobject` (`:103`), a więc i `ApplyWave`: najpierw
przypisanie punktów startowych, potem `apply_function`.

Zrób dwa warianty i porównaj je na tym samym zestawie testów:

- **Wariant A — mechanizm z `PLAN.md` dokładnie tak, jak go opisano.** Tylko test
  shadow, żadnego innego sygnału.
- **Wariant B — kandydat na poprawkę.** `animation.py::Animation.begin` (`:206-213`)
  i `Animation.finish` (`:226-227`) wołają `suspend_updating` / `resume_updating` na
  animowanym mobjekcie, rekurencyjnie (`mobject.py::Mobject.suspend_updating`). Override
  tych dwóch metod na liściu wyznacza tryb przejściowy: w trybie przejściowym operacje
  geometryczne trafiają do bufora, a nie do `placement`. `resume_updating` kończy tryb
  i uruchamia odroczoną przebudowę. Test shadow zostaje dla zapisów poza animacją.
  Sprawdź, które animacje *nie* wołają `suspend_updating` (`suspend_mobject_updating=False`
  mają w 0.21.0 m.in. `ShowIncreasingSubsets`, `AddTextLetterByLetter`,
  `RemoveTextLetterByLetter`, `PhaseFlow`, `MoveAlongPath`) i co się z nimi dzieje.

Dla każdej z animacji `Create`, `Write`, `ShowPassingFlash`, `Indicate`, `Wiggle`,
`ApplyWave`, `Flash`, `Circumscribe` oraz `Uncreate`, odtworzonej przez `Scene.play` z
**prawdziwą interpolacją klatka po klatce** (nie `skip_animations`; potwierdź licznikiem,
że `interpolate` wywołano więcej niż raz) na rendererze Cairo w niskiej rozdzielczości,
bez zapisu filmu, sprawdź po zakończeniu:

1. `placement` jest taki sam jak przed animacją;
2. bufor jest równy punktom pochodnym (`np.array_equal`), czyli liść jest czysty —
   z wyjątkiem `Uncreate`, który kończy się geometrią zdegenerowaną;
3. `c2p` układu współrzędnych jest niezmienione, a drugi liść na tym samym układzie
   nie przesunął się ani nie odkształcił;
4. parametr danych zmieniony w trakcie animacji (`ValueTracker` z updaterem na scenie)
   zostaje zastosowany najpóźniej po jej zakończeniu.

W wariancie B sprawdź dodatkowo kanał geometryczny, który *ma* być trwały:
`self.play(leaf.animate.shift(RIGHT))` i ten sam ruch przez `override_animate` (F-908)
muszą się kończyć przesunięciem w `placement`, a nie zmianą, która cofnie się przy
następnej przebudowie.

### H3 — kopia liścia

`mobject.py::Mobject.__deepcopy__` (`:444-451`) tworzy obiekt przez `cls.__new__`,
a potem robi `setattr` dla każdego klucza `__dict__`, bez `__init__`. Animacje kopiują
przy każdym `play` (`create_starting_mobject`, `generate_target`). Sprawdź:

- czy liść z property `points` i z `__setattr__`, który oznacza węzeł jako brudny
  (A3.2), przeżywa `copy()`;
- co jest kopiowane razem z liściem, jeśli trzyma referencję do układu współrzędnych:
  czy cały układ z innymi artystami i źródłami;
- ile trwa `copy()` dla sceny z F-1001 (cztery artyści po 2000 próbek na jednym
  układzie).

### H4 — koszt: getter i przebudowa

Scena z F-1001: cztery liście po 2000 próbek na jednym układzie i około dziesięciu
ticków, jeden parametr animowany, który brudzi pipeline w każdej klatce.

- Policz wywołania gettera `points` na klatkę i czas, jaki zajmuje w nich test shadow.
- Zmierz p95 czasu przebudowy na co najmniej 600 klatkach. Próg z F-1001: **4 ms**.
  Pipeline w PoC jest minimalny (bez adaptacyjnego próbkowania), więc wynik to dolne
  ograniczenie. Napisz to wprost w raporcie i oszacuj zapas.

### H5 — etykiety `MathTex` jako liście biblioteki

ADR 0001 (pytanie 2) wybrał `MathTex` dla etykiet, a F-1004 wymaga, żeby każdy
wygenerowany liść był typem biblioteki. Glify `MathTex` to typy Manim ze zwykłym
atrybutem `points`.

- Przepisz glify jednej etykiety do liści PoC: punkty glifu stają się źródłem, a
  `placement` układu jest stosowany do nich. Sprawdź `Write(label)` i `ax.rotate(...)`.
- Zmierz koszt etykiet przy animowanym zakresie od `(0, 10)` do `(0, 1000)` w 2 s przy
  15 fps, z tickami w stylu `MaxN(5)`, tak że w trakcie pojawiają się nowe napisy. Mierz
  przy zimnym cache TeX (osobny, pusty katalog media) i przy ciepłym. Porównaj z
  alternatywą składania liczb z cache pojedynczych glifów, tak jak robi to
  `numbers.py::DecimalNumber`.

## 3. Ograniczenia

- Cały kod w `poc/`. Nie zmieniaj `src/`, `tests/`, `pyproject.toml`, `PLAN.md`,
  `TODO.md` ani ADR. Jedyny plik poza `poc/` to raport z sekcji 4.
- Uruchamiaj `.venv\Scripts\python.exe` bezpośrednio, bez `uv`. Niczego nie instaluj
  i nie korzystaj z sieci.
- Testy PoC to `poc/test_*.py`, bez markera `render`, uruchamiane przez
  `.venv\Scripts\python.exe -m pytest poc`. Katalog media ustaw wewnątrz `poc/`.
- `ruff check .` i `ruff format --check .` mają przechodzić; `pyproject.toml` zwalnia
  już `poc/*` z reguł `D` i `ANN`. mypy nie obejmuje `poc/`.
- Nie commituj. Zmiany przejrzy maintainer.
- Jeśli hipoteza okaże się źle postawiona, napisz to w raporcie, zamiast naginać test.

## 4. Raport

Zapisz `docs/poc-points-property.md`:

1. tabela: hipoteza, werdykt, jedno zdanie dowodu;
2. sekcja na każdą hipotezę: co zbudowano, wynik (liczby, nazwy testów), cytaty z Manim
   (symbol, potem linia) i **co musi się zmienić w `PLAN.md` albo w ADR 0001**, jeśli
   hipoteza padła;
3. dla H2: tabela animacji × wariant (A, B) × kryteria 1-4;
4. komendy, które odtwarzają każdy wynik.
