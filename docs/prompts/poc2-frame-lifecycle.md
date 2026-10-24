# Prompt: proof of concept v2 — ramka-siatka i cykl życia liści

Zbuduj **drugi jednorazowy proof of concept**. Pierwszy (`poc/`, raport
`docs/poc-points-property.md`) obalił mechanizm z `PLAN.md`: test shadow nie odróżnia
animacji od wywołania bezpośredniego (H2), a `VMobject.apply_function` nie trafia do
`placement` (H1). Ten PoC sprawdza mechanizm zastępczy. Nadrzędny cel projektu się nie
zmienia, ale teraz jest wprost priorytetem: **z punktu widzenia użytkownika API ma się
zachowywać możliwie jak zwykły Manim**. Każdy test, który odpowiada na pytanie „co
zobaczy użytkownik Manima”, porównuje z tym, co w tej samej sytuacji robi Manim.

To nie jest implementacja `manim-plots`: nie dotykaj `src/`, nie projektuj API, nie pisz
kodu „na później”. Kod PoC to najkrótszy kod, który rozstrzyga hipotezę. Kod i raport po
angielsku.

## 1. Kontekst — przeczytaj przed pisaniem kodu

- `docs/poc-points-property.md` w całości: wyniki v1, liczby, cytaty.
- `poc/points.py`, `poc/scene.py`, `poc/test_animations.py`: jak v1 liczył klatki
  i interpolacje. Wolno skopiować wzorzec, nie wolno importować z `poc/`.
- `PLAN.md`, sekcje *Integration: the `points` property on library-owned leaves*,
  *Containers and attachment*, *`.animate` needs `override_animate`*.
- `docs/grill-log.md`, D11 (artysta nie jest dzieckiem układu, „double-transform trap”).
- `docs/scope.md`: F-708, F-709, F-901..F-912, F-1001.

Środowisko: Manim **0.21.0** w `.venv`. Cytując Manim, podawaj najpierw symbol, potem
linię (`transform.py::Transform.begin`, `:211`).

## 2. Mechanizm do sprawdzenia

Trzy zmiany względem v1. Opisuję je, żeby było wiadomo, co testować; szczegóły
implementacji wybierz sam, byle najprostsze.

**A. Ramka-siatka zamiast łańcucha `placement`.** Układ współrzędnych (`System`) jest
`VGroup`. Jednym z jego dzieci jest niewidoczna **ramka**: `VMobject`, którego punkty to
siatka `N x N` rozpięta na prostokącie osi, plus jeden punkt poza płaszczyzną (żeby
afiniczne przekształcenie w 3D było wyznaczalne). Manim przekształca ramkę natywnie, jak
każdy inny liść: `shift`, `rotate`, `apply_function`, `.animate`, kontener, animacja.
`placement` przestaje być stanem — to **interpolacja dwuliniowa po aktualnych węzłach
ramki**, z szybką ścieżką, gdy ramka jest afiniczna (wtedy wynik ma być dokładny, także
poza prostokątem). `c2p` czyta ramkę, `p2c` ją odwraca (afinicznie dokładnie,
nieliniowo np. Newtonem — zmierz koszt i błąd).

Ramka nie może się degenerować ani stać widoczna:

- `creation.py::ShowPartial.interpolate_submobject` (`:132-134`) woła
  `pointwise_become_partial` na każdym liściu, więc `Create(ax)`, `Write(ax)`,
  `Uncreate(ax)` i `ShowPassingFlash(ax)` obcięłyby siatkę. Ramka ma to ignorować.
- `ax.set_opacity(1)`, `ax.set_color(RED)`, `ax.set_stroke(width=8)`, `FadeIn`, `FadeOut`
  nie mogą jej pokazać. Sprawdź pikselowo: klatka z ramką == klatka bez ramki.
- Wykrywanie, że ramka się zmieniła, nie może polegać tylko na setterze:
  `indication.py::Wiggle.interpolate_submobject` (`:559`) pisze w miejscu. Zmierz koszt
  porównania ramki z ostatnio widzianą kopią.

**B. Cykl życia liści pochodnych.** Liście pochodne (linie osi, ticki, krzywa artysty)
mają property `points` jak w v1, ale bez testu shadow. Zamiast niego:

- **w animacji** (między `suspend_updating` a `resume_updating`, wołanymi przez
  `animation.py::Animation.begin` `:213` i `Animation.finish` `:227`) bufor jest
  przejściowy: zapisy trafiają do bufora, nic nie trafia do stanu;
- **poza animacją** obcy zapis do liścia pochodnego jest **odrzucany**: liść oznacza się
  brudnym i przy następnym odczycie przebudowuje z danych i ramki. To zamyka podwójne
  przesunięcie w `VGroup(ax, curve).shift(v)` (ramka już się przesunęła, a pętla
  `Mobject.shift` dopisuje `v` jeszcze raz do krzywej) — zweryfikuj w obu kolejnościach,
  `VGroup(ax, curve)` i `VGroup(curve, ax)`;
- **na końcu animacji przyjmowany jest cel**, jeśli animacja na nim skończyła.
  `transform.py::Transform.begin` woła `self.mobject.align_data(self.target_copy)`
  (`:211`) **przed** `super().begin()`, czyli przed `suspend_updating`. Override
  `align_data` na artyście może więc zapamiętać kopię celu, a `resume_updating` — jeśli
  bufor równa się punktom celu — przejąć jego stan (źródło, parametry, własny
  `placement` artysty, styl). Jeśli bufor celowi się nie równa (`Indicate` kończy na
  starcie, bo `there_and_back`), nic nie przyjmuje i przebudowuje. Cel, który nie jest
  artystą (`Transform(curve, Circle())`), odłącza artystę od danych: zostaje kształt
  zapisany w lokalnych współrzędnych układu, więc nadal podąża za ramką.

**C. Własny kanał geometryczny artysty.** Artysta nie jest dzieckiem układu (D11), ale
ma własny, krótki `placement` stosowany po ramce. Artysta krzywej to **jeden `VMobject`
z punktami**, a odcinki po rozcięciu na biegunie to jego podścieżki — tak jak
`ParametricFunction` z `discontinuities` w Manimie. Kontener bez własnych punktów
odpada, bo wtedy `graph.get_end()`, `graph.point_from_proportion(t)` i
`MoveAlongPath(dot, graph)` rzucają wyjątek. Override `shift`
i `apply_points_function_about_point` na artyście: **poza animacją** zapis do własnego
`placement` (trwały), **w animacji** zapis do bufora (`Wiggle` woła
`submobject.scale` i `submobject.rotate` na samym artyście, `indication.py::Wiggle.interpolate_submobject`,
`:559-567`). `curve.shift(UP)` przesuwa więc krzywą względem osi na stałe, jak w
Manimie, a surowy zapis z obcego kontenera (`VGroup(...).shift` pisze w `mob.points`,
nie woła `curve.shift`) podlega regule B. Bez `override_animate` na metodach
geometrycznych: `curve.animate.shift(UP).scale(2)` idzie natywną ścieżką
kopiuj-i-przekształć, a trwałość daje przyjęcie celu z B.
`become` na artyście jest nadpisane i przejmuje stan drugiego artysty, bo
`mobject.py::Mobject.become` (`:3308-3310`) przepisuje punkty poza animacją, a takie
zapisy B odrzuca.

Do tego:

- **Rejestr artystów słaby** (`weakref`), bo `always_redraw(lambda: ax.plot(...))`
  (`mobject_update_utils.py::always_redraw`, `:107-109`) tworzy nowego artystę co klatkę.
- **Kopia**: własny `__deepcopy__` — źródło współdzielone, rejestr niekopiowany.
  `mobject.py::Mobject.__deepcopy__` (`:444-451`) przekazuje `memo`: jeśli układ jest
  kopiowany w tej samej operacji (`VGroup(ax, curve).copy()`, cel `.animate`), kopia
  artysty wiąże się z kopią układu; jeśli kopiowany jest tylko artysta, kopia wiąże się
  z oryginałem.
- **Updater synchronizujący.** `scene.py::Scene.get_moving_mobjects` (`:937-946`) i
  `cairo_renderer.py::CairoRenderer.play` (`:110`) rysują raz, jako statyczne tło,
  wszystko przed pierwszym mobjektem, który jest animowany albo ma updater. Artysta
  podążający za ramką, dodany do sceny przed `ax`, albo artysta z parametrem związanym
  z trackerem animowanym przez `self.play(t.animate.set_value(...))`, zamarznie w trakcie
  animacji i przeskoczy na końcu. Sprawdź, czy tak jest, i czy pusty updater na układzie
  i artyście to naprawia.

Wiązanie parametru z trackerem zrób najprościej, jak się da (np. `amplitude` artysty
czytane z `ValueTracker` przy przebudowie). To nie jest projekt API parametrów.

## 3. Hipotezy

Każda kończy się werdyktem **CONFIRMED**, **FALSIFIED** albo **INCONCLUSIVE**, z dowodem:
nazwą testu, liczbami i cytatem z Manim. Wszystkie animacje przez `Scene.play` z
**prawdziwą interpolacją klatka po klatce** (licznik interpolacji > 1, jak w v1), Cairo,
niska rozdzielczość, bez zapisu filmu.

**Prawda wzorcowa.** Oczekiwaną geometrię licz niezależnie od mechanizmu: ten sam
`Source -> Map` próbkowany gęsto, a potem przekształcony tym samym przekształceniem, które
dostał układ. Raportuj maksymalny błąd w jednostkach sceny, nie tylko pass/fail.

### G1 — ramka łapie każde przekształcenie układu

Poza animacją, na `ax`, potem wymuszona przebudowa (zmiana zakresu danych):
`shift`, `rotate`, `scale`, `stretch`, `flip`, `apply_matrix`, `move_to`, `next_to`,
`to_corner`, `scale_to_fit_width`, `apply_function` (nieliniowa gładka),
`apply_complex_function`. Każda w czterech opakowaniach: samo `ax`, `VGroup(ax)`,
`VGroup(ax, curve)`, `VGroup(curve, ax, dot)`. Kryteria: krzywa po przebudowie zgadza się
z prawdą wzorcową; dla afinicznych błąd <= `1e-9`; `dot` przesunął się jak w Manimie;
krzywa nie przesunęła się podwójnie.

Dla nieliniowych: tabela błędu dla `N` = 9, 17, 33, 65, dla trzech funkcji (fala,
`z**2` przez `apply_complex_function`, mocne zgięcie) oraz jednej nieciągłej. Podaj
też, ile kosztuje przebudowa przy każdym `N`. Nie ustalaj progu „niewidoczności” na oko:
podaj błąd w pikselach przy 1080p.

### G2 — animacje na `ax`

`Create`, `Write`, `Uncreate`, `DrawBorderThenFill`, `ShowPassingFlash`, `FadeIn`,
`FadeOut`, `FadeIn(shift=UP)`, `FadeOut(shift=DOWN)`, `GrowFromCenter`, `Indicate`,
`Wiggle`, `Circumscribe`, `Flash`, `ApplyWave`, `Rotate`, `ScaleInPlace`,
`MoveAlongPath(ax, path)`, `Homotopy`, `ApplyPointwiseFunction`, `ApplyMatrix`,
`Transform(ax, ax.copy().shift(RIGHT))`, `MoveToTarget`, `Restore`,
`ax.animate.shift(RIGHT).scale(0.5)` (łańcuch — natywny, bez `override_animate`),
`ax.animate.rotate(PI / 6)`. Dla każdej:

1. w **każdej** klatce zarejestrowany artysta (nie w animacji) = pochodna z bieżącej
   ramki;
2. po końcu ramka jest w stanie, w którym Manim zostawiłby zwykły `VGroup` (przekształcenia
   trwałe, wskazania wracają);
3. ramka nie zdegenerowała się (liczba punktów, brak `NaN`, prostokąt niezdegenerowany —
   poza `GrowFromCenter` przy `alpha = 0`, gdzie zapisz, co się dzieje z `p2c`);
4. ramka niewidoczna (piksele).

Osobno zapisz, co widzi użytkownik przy `FadeOut(ax, shift=DOWN)`, `Indicate(ax)` i
`Wiggle(ax)`: artysta jedzie razem z osiami, choć sam nie jest animowany. W Manimie by
stał. To nie jest błąd testu, tylko fakt do raportu.

### G3 — animacje na artyście

Lista z v1 (`Create`, `Write`, `ShowPassingFlash`, `Indicate`, `Wiggle`, `ApplyWave`,
`Flash`, `Circumscribe`, `Uncreate`) plus: `Rotate(curve)`, `curve.animate.shift(UP)`,
`curve.animate.shift(UP).scale(2)` (łańcuch), `MoveToTarget`,
`Transform(curve, ax.plot(other))`, `ReplacementTransform(curve, ax.plot(other))`,
`Transform(curve, Circle())`, `TransformFromCopy`, `FadeOut(curve, shift=DOWN)`. Dla
każdej:

1. stan końcowy taki, jaki zostawiłby Manim na zwykłym `VMobject`;
2. ten stan **przetrwa** następną przebudowę (zmiana zakresu): przyjęte przekształcenia
   i przyjęty cel zostają, wskazania nie zostawiają śladu;
3. ramka i drugi artysta nietknięte;
4. parametr danych zmieniony w trakcie (tracker) zastosowany najpóźniej po końcu.

`Uncreate` i `ReplacementTransform` usuwają mobject ze sceny: zapisz, w jakim stanie
zostaje artysta i co trzeba zrobić, żeby go dodać z powrotem.

### G4 — idiomy Manima

- `always_redraw(lambda: ax.plot(lambda x: a.get_value() * np.sin(x)))` z
  `self.play(a.animate.set_value(2))`: każda klatka poprawna, rejestr `ax` po animacji
  i `gc.collect()` ma stały rozmiar.
- `graph.add_updater(lambda m: m.become(ax.plot(...)))`: to samo.
- `MoveAlongPath(dot, curve)`, `curve.point_from_proportion(0.5)`, `curve.get_end()`
  i `dot.move_to(curve.get_end())`, także na krzywej rozciętej na biegunie (`1 / x`).
- kropka z updaterem `d.move_to(ax.c2p(t.get_value(), 0))` w trakcie `ax.animate.rotate`.
- `ax.add(curve)` (zwykłe `Mobject.add`, krzywa staje się dzieckiem) i potem `ax.shift`:
  jedno przesunięcie, nie dwa. Potem `self.add(ax); self.play(Create(curve))`: zapisz, co
  robi `scene.py::Scene.add` z `ax` (splice) — tak samo jak w Manimie, czy gorzej.
- `self.play(ax.animate.shift(LEFT), curve.animate.shift(LEFT))`: kod przeniesiony z
  Manima, gdzie oba trzeba było przesunąć. Zapisz wynik (krzywa przesunięta raz czy dwa
  razy względem sceny) i czy da się to tanio wykryć i ostrzec (np. układ jest w animacji,
  gdy startuje animacja artysty).
- `VGroup(curve, dot).shift(v)` bez `ax`: w Manimie krzywa się przesuwa. Zapisz, co
  robi mechanizm B (odrzuca zapis) i czy da się wiarygodnie ostrzec.

### G5 — zamarzanie statycznych mobjektów

Kolejność sceny `self.add(curve, ax)`, potem `self.play(ax.animate.shift(RIGHT))`;
oraz artysta z parametrem związanym z trackerem i `self.play(t.animate.set_value(...))`,
gdzie tracker nie jest w scenie. Zmierz, czy w środkowych klatkach artysta jest tam,
gdzie powinien (rysuj klatki do tablic i porównaj), bez updatera i z pustym updaterem.
Podaj koszt: o ile wolniej renderuje się `self.wait(2)` z updaterem niż bez.

### G6 — koszt

Scena z F-1001 (cztery artyści po 2000 próbek na jednym układzie, ok. dziesięciu
ticków, jeden parametr brudzący pipeline co klatkę, 1080p60, co najmniej 600 klatek):
p95 przebudowy z ramką (ścieżka afiniczna i wymuszona dwuliniowa przy `N = 33`), koszt
wykrycia zmiany ramki na odczyt, narzut updatera, mediana `copy()` układu z artystami.
Próg F-1001: 4 ms. Porównaj z liczbami v1 (H4).

### G7 — kanał danych pod `.animate`

Geometria idzie natywnie (A, C), ale parametry danych nie mogą być interpolowane
punktami (`PLAN.md`, „interpolate parameters, never points”). Sprawdź dwie drogi:

1. **`override_animate`** na `ax.set_x_range(...)`, zwracające animację z
   `suspend_mobject_updating=False`, żeby liście przebudowywały się co klatkę zamiast
   wejść w tryb przejściowy B. Kryteria: w każdej klatce ticki i artyści są poprawnym
   wykresem interpolowanego zakresu; po końcu zakres docelowy. Zapisz, co się dzieje
   przy łańcuchu `ax.animate.shift(RIGHT).set_x_range(...)` i
   `ax.animate.set_x_range(...).shift(RIGHT)` (`mobject.py::_AnimationBuilder`,
   `:3443-3445`, rzuca na łańcuch z metodą nadpisaną) — dokładny tekst wyjątku.
2. **Bez `override_animate`**: natywne kopiuj-i-przekształć, a override `interpolate`
   na ramce i na liściach pochodnych interpoluje parametry zamiast punktów. Główna
   przeszkoda: `Transform.begin` woła `align_data` (`:211`), które wyrównuje strukturę
   rodziny, gdy cel ma inną liczbę ticków. Ustal, czy ta droga w ogóle działa; jeśli
   nie, INCONCLUSIVE albo FALSIFIED z powodem wystarczy. Jeśli działa, łańcuch
   `ax.animate.shift(RIGHT).set_x_range(...)` przestaje być problemem.

## 4. Ograniczenia

- Cały kod w `poc2/` (nowy katalog; `poc/` zostaw nietknięty). Jedyny plik poza `poc2/`
  to raport z sekcji 5. Nie zmieniaj `src/`, `tests/`, `pyproject.toml`, `PLAN.md`,
  `TODO.md` ani ADR. `pyproject.toml` zwalnia już `poc2/*` z reguł `D` i `ANN`.
- Uruchamiaj `.venv\Scripts\python.exe` bezpośrednio, bez `uv`. Niczego nie instaluj
  i nie korzystaj z sieci.
- Testy to `poc2/test_*.py`, bez markera `render`, uruchamiane przez
  `.venv\Scripts\python.exe -m pytest poc2 -p no:cacheprovider`.
- **Nie używaj `tempfile.mkdtemp`, `TemporaryDirectory` ani fixture `tmp_path`.** Python
  3.13 na Windows nadaje katalogom z `mode=0o700` ACL tylko dla bieżącego użytkownika;
  katalogi utworzone tak w sandboksie v1 są dla maintainera nieczytelne i nieusuwalne.
  Katalog media to zwykłe `Path("poc2/media").mkdir(exist_ok=True)`. Z tego samego
  powodu `-p no:cacheprovider`.
- Bez `MathTex` i `Tex`: TeX w sandboksie nie działa (v1, H5). Etykiety nie są
  przedmiotem tego PoC.
- `ruff check .` i `ruff format --check .` mają przechodzić. mypy nie obejmuje `poc2/`.
- Nie commituj.
- Jeśli hipoteza okaże się źle postawiona albo mechanizm z sekcji 2 da się zrobić
  prościej, napisz to w raporcie, zamiast naginać test. Jeśli coś z sekcji 2 nie działa,
  nie łataj tego heurystyką dopasowującą delty między liśćmi — taki kierunek maintainer
  już odrzucił. Zapisz porażkę.

## 5. Raport

Zapisz `docs/poc2-frame-lifecycle.md`:

1. tabela: hipoteza, werdykt, jedno zdanie dowodu;
2. sekcja na każdą hipotezę: co zbudowano, wynik (liczby, nazwy testów), cytaty z Manim
   (symbol, potem linia), **co musi się zmienić w `PLAN.md` albo w ADR 0001**;
3. dla G2 i G3: tabela animacja × kryteria 1-4, z kolumną „Manim robi to samo?”;
4. lista sytuacji, w których zachowanie **różni się od Manima**, każda z jednym
   zdaniem: co widzi użytkownik, czy to jest wybór, czy ograniczenie mechanizmu;
5. komendy, które odtwarzają każdy wynik.
