# Prompt: proof of concept v3 — kontekst ze stosu wywołań

Zbuduj **trzeci jednorazowy proof of concept**. v2 (`poc2/`, raport
`docs/poc2-frame-lifecycle.md`) potwierdził ramkę-siatkę i cykl życia liści, ale zostawił
dwie różnice względem Manima, które maintainer chce usunąć, i kilka błędów. Obie różnice
mają jedną przyczynę: liść nie wie, **kto** go w tej chwili rusza. Manim nie daje granicy
transakcji, ale stos wywołań ją zawiera. Ten PoC sprawdza, czy odczyt kontekstu ze stosu
wystarcza.

Cel nadrzędny bez zmian: **z punktu widzenia użytkownika API zachowuje się jak zwykły
Manim**. Każdy test „co zobaczy użytkownik” porównuje z tym, co w tej samej sytuacji
robi Manim na zwykłych mobjectach.

To nie jest implementacja `manim-plots`: nie dotykaj `src/`, nie projektuj API. Kod
i raport po angielsku.

## 1. Kontekst — przeczytaj przed pisaniem kodu

- `docs/poc2-frame-lifecycle.md` w całości, łącznie z *Review notes* na końcu.
- `poc2/model.py` i testy `poc2/test_*.py`.
- `docs/prompts/poc2-frame-lifecycle.md`: mechanizmy A, B, C, na których budujesz.

Środowisko: Manim **0.21.0** w `.venv`. Cytując Manim, podawaj najpierw symbol, potem
linię.

**Punkt startowy:** skopiuj `poc2/` do `poc3/` i zmieniaj kopię. Nie importuj z `poc2/`
ani z `poc/`. Testy v2 skopiowane do `poc3/` są bazą regresji: mają przechodzić, chyba
że decyzja z sekcji 2 zmienia oczekiwany wynik — każdą taką zmianę oczekiwania wypisz
w raporcie z uzasadnieniem.

## 2. Mechanizm do sprawdzenia

Maintainer sprawdził na 0.21, że to jest odczytywalne (skrypt sondy, nie test):

- w override `suspend_updating` na liściu, idąc po `sys._getframe()` w górę, znajduje
  się ramka `animation.py::Animation.begin` (`:213`) z `self` będącym animacją —
  `Indicate`, `FadeOut` (`remover=True`), `Wiggle`, `_MethodAnimation`;
- w setterze `points` znajduje się ramka `mobject.py::Mobject.shift` (`:1282-1283`) albo
  `mobject.py::Mobject.apply_points_function_about_point` (`:1581-1584`) z `self`
  będącym kontenerem, który właśnie pisze, a w tej drugiej także `func` i
  `about_point`.

Na tym zbuduj trzy rzeczy.

**D. Odpinanie artystów od nietrwałych animacji osi.** Ramka w `suspend_updating`
dostaje animację i rozstrzyga, czy po animacji (łącznie z `clean_up_from_scene`) osie
będą w stanie sprzed niej. Jeśli tak, zarejestrowani artyści, którzy sami nie są w tej
animacji, na jej czas czytają **zamrożoną kopię ramki** — stoją jak w Manimie; w
`resume_updating` wracają do żywej ramki. Jeśli nie, jadą z ramką co klatkę, jak w v2.
Rozstrzygnięcie robi **symulacja na kopii**: głęboka kopia animacji z jej mobjectem,
`begin`, `finish`, `clean_up_from_scene` na atrapie sceny, porównanie końcowej ramki
z początkową. Flagi `remover` / `introducer` wolno użyć jako skrótu, jeśli wynik jest
ten sam. Reguła dla użytkownika ma się dać powiedzieć jednym zdaniem: **krzywe idą tylko
za trwałymi zmianami osi**. Konsekwencja przyjęta przez maintainera: `Rotate(ax, TAU)`
nie obraca krzywych.

**E. Zapis z obcego kontenera.** Setter liścia pochodnego poza animacją czyta kontener
ze stosu:

- rodzina kontenera zawiera ramkę układu, do którego liść należy: osie jadą w tej samej
  operacji, zapis jest ignorowany, liść idzie za ramką (jak w v2);
- nie zawiera: to przekształcenie samego liścia — zapisz je do własnego `placement`
  artysty (dla `apply_points_function_about_point` dokładne `func` i `about_point`,
  dla `shift` wektor), tak jak `curve.shift(v)` w v2. Krzywa jedzie jak w Manimie
  i dalej reaguje na zmianę danych;
- brak takiej ramki na stosie (np. ręczne `curve.points += v`): zachowanie z v2.

**F. Kontekst animacji w `align_data`.** `transform.py::Transform.begin` woła
`align_data` (`:211`) przed `suspend_updating`. Jeśli na stosie jest `Transform.begin`,
tryb przejściowy zaczyna się już w `align_data`. Dla animacji z `remover=True` cel nie
jest przyjmowany.

Poprawki z v2, każda z testem, który przed poprawką pada:

1. `FadeOut(curve, shift=DOWN)` — po cleanup krzywa w stanie sprzed animacji, jak w
   Manimie (`fading.py::FadeOut.clean_up_from_scene`, `:190-192`).
2. `Transform` do celu z większą liczbą punktów (36 -> 196) — gra i przyjmuje cel.
3. Własny `placement` artysty w **lokalnej** przestrzeni układu, nie w scenie:
   `curve.shift(UP)`, potem `ax.rotate(PI / 2)` — przesunięcie obraca się z osiami,
   jak zwykły `VGroup(ax, graph)` w Manimie po wcześniejszym `graph.shift(UP)`. Przy
   ramce nieafinicznej sprzężenie jest przybliżone: podaj błąd.
4. Ścieżka dwuliniowa: indeksy komórek i wagi liczone raz na próbki, nie na każde
   wywołanie. p95 na scenie z F-1001 przy N = 33, próg 4 ms.
5. Bez punktu poza płaszczyzną: `get_center()` i oś obrotu `ax` równe tym samym
   widocznym osiom bez ramki.
6. Wzrost `placement`: przechwycone operacje co klatkę (`MoveAlongPath(curve, path)`,
   `PhaseFlow` na krzywej) nie mogą dokładać węzła na klatkę bez końca — sąsiednie
   afiniczne zwijaj; podaj liczbę węzłów po 2 s.

Funkcja wykresu jako wiązanie do callable (D8 w `docs/grill-log.md`: polling, callable
zawsze brudny): updater synchronizujący oznacza źródło z callable jako brudne **raz na
klatkę**, nie przy każdym odczycie.

## 3. Hipotezy

Werdykty **CONFIRMED** / **FALSIFIED** / **INCONCLUSIVE**, z nazwą testu, liczbami
i cytatem z Manim. Animacje przez `Scene.play` z prawdziwą interpolacją klatka po
klatce, Cairo, niska rozdzielczość, bez zapisu filmu — jak w v2.

### K1 — kontekst ze stosu jest kompletny

Dla każdej animacji z tabel G2 i G3 v2 oraz `AnimationGroup`, `Succession` i
`LaggedStart` z animacją osi w środku: czy hook widzi właściwą animację i właściwy
kontener. Zapisz przypadki, w których `suspend_updating` przychodzi kilka razy (grupa,
potem animacja w grupie) albo w trakcie `play` (`Succession` startuje kolejne animacje
w trakcie odtwarzania), i co wtedy robi D. Animacje z `suspend_mobject_updating=False`
(`MoveAlongPath`, `ShowIncreasingSubsets`, `PhaseFlow`): co widzi E. Koszt odczytu
stosu na zapis i na `suspend_updating`.

### K2 — odpinanie przy nietrwałych animacjach osi

Nietrwałe, krzywa ma stać: `Indicate`, `Wiggle`, `ApplyWave`, `Circumscribe`, `Flash`,
`FadeIn(shift=UP)`, `FadeOut(shift=DOWN)`, `GrowFromCenter`, `Create`, `Write`,
`Uncreate`, `DrawBorderThenFill`, `ShowPassingFlash`, `Rotate(ax, TAU)`.
Trwałe, krzywa ma jechać co klatkę: `Rotate(ax, PI / 6)`, `ScaleInPlace`,
`ax.animate.shift(RIGHT).scale(0.5)`, `MoveToTarget`,
`Transform(ax, ax.copy().shift(RIGHT))`, `ApplyMatrix`, `ApplyPointwiseFunction`,
`Homotopy` kończąca się poza startem, `Restore` do innego stanu.
Kryteria: w każdej klatce artysta tam, gdzie powinien (stoi albo idzie za bieżącą
ramką); po końcu znowu podpięty (następne `ax.shift` go przesuwa); symulacja nie zmienia
sceny, `ax`, rejestru ani liczby artystów; koszt symulacji na `play`. Pikselowo
porównaj nietrwałe z natywną sceną, w której krzywa jest zwykłym `VMobject` poza osiami.

### K3 — obce kontenery

Poza animacją: `VGroup(curve, dot)` z `shift`, `rotate`, `scale`, `apply_matrix`,
`apply_function`, `move_to`, `next_to`, `to_corner`; `VGroup(curve1, curve2).arrange(DOWN)`;
`Group(curve, dot)`; zagnieżdżone `VGroup(VGroup(ax), curve)`; `VGroup(ax, curve, other)`,
gdzie `other` należy do drugiego układu. W animacji: `VGroup(curve, dot).animate.shift(UP)`,
`Rotate(VGroup(curve, dot))`. Kryteria: zaraz po operacji punkty krzywej równe natywnemu
Manimowi (także uchwyty po `VMobject.apply_function`, `vectorized_mobject.py`,
`:1226-1228`, gdzie v1 miał błąd 0,864); po wymuszonej przebudowie (zmiana zakresu
i danych) przekształcenie zostaje, a nowe dane są przez nie widoczne; żadnego podwójnego
ruchu.

### K4 — poprawki z v2

Po jednym teście na każdą z sześciu poprawek z sekcji 2, z liczbami przed i po.

### K5 — funkcja wykresu liczona raz na klatkę

`ax.plot(lambda x: a.get_value() * np.sin(x))` bez `always_redraw` i
`self.play(a.animate.set_value(2))`: każda klatka jest wykresem bieżącego `a`; liczba
wywołań próbkowania na klatkę na artystę; `self.wait(2)` potem — liczba wywołań
(oczekiwane zero, bo zamrożony `wait` nie renderuje).

### K6 — regresja v2

Pełny zestaw skopiowanych testów v2: ile przechodzi, które oczekiwania zmieniły się
przez D, E albo F, i dlaczego.

## 4. Ograniczenia

- Cały kod w `poc3/`. Jedyny plik poza `poc3/` to raport z sekcji 5. Nie zmieniaj
  `src/`, `tests/`, `poc/`, `poc2/`, `pyproject.toml`, `PLAN.md`, `TODO.md` ani ADR.
  `pyproject.toml` zwalnia już `poc3/*` z reguł `D` i `ANN`.
- Uruchamiaj `.venv\Scripts\python.exe` bezpośrednio, bez `uv`. Niczego nie instaluj,
  bez sieci.
- Testy: `.venv\Scripts\python.exe -m pytest poc3 -p no:cacheprovider`, bez markera
  `render`.
- Bez `tempfile.mkdtemp`, `TemporaryDirectory` i `tmp_path` (ACL Pythona 3.13 na
  Windows, patrz prompt v2). Katalog media przez zwykłe `Path.mkdir`.
- Bez `MathTex` i `Tex`.
- `ruff check .` i `ruff format --check .` mają przechodzić.
- Nie commituj.
- Nie łataj porażek heurystyką dopasowującą delty między liśćmi ani zgadywaniem
  transakcji z kolejności wywołań `get_family` — oba kierunki maintainer odrzucił.
  Kontekst ma pochodzić z obiektów na stosie: animacji, kontenera, funkcji. Jeśli to nie
  wystarcza, zapisz porażkę.
- Monkeypatch klas Manima jest zabroniony: kontekst czytamy, Manima nie zmieniamy.

## 5. Raport

Zapisz `docs/poc3-stack-context.md`:

1. tabela: hipoteza, werdykt, jedno zdanie dowodu;
2. sekcja na każdą hipotezę: co zbudowano, wynik (liczby, nazwy testów), cytaty z Manim
   (symbol, potem linia), **co musi się zmienić w `PLAN.md` albo w ADR 0001**;
3. dla K2 i K3: tabela przypadek × kryteria z kolumną „Manim robi to samo?”;
4. zaktualizowana lista z v2 *Differences from ordinary Manim*: co zniknęło, co zostało,
   co nowego doszło;
5. od czego w Manimie zależy mechanizm — każda ramka stosu, na której polega, z
   symbolem i linią — żeby test cytowanych symboli łapał zmianę przy aktualizacji Manima;
6. komendy, które odtwarzają każdy wynik.
