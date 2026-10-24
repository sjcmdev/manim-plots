# Prompt: proof of concept v4 — natywny łańcuch dane + geometria

Zbuduj **czwarty jednorazowy proof of concept**. v3 (`poc3/`, raport
`docs/poc3-stack-context.md`) potwierdził kontekst ze stosu. Zostało jedno odstępstwo od
Manima, którego maintainer nie chce odkładać do 0.2:
`ax.animate.shift(RIGHT).set_x_range((0, 20))` rzuca dziś
`NotImplementedError: Method chaining is currently not supported for overridden animations`
(`mobject.py::_AnimationBuilder.__getattr__`, `:3443-3445`), bo metoda danych ma
`override_animate`. Natywna droga — kopiuj-i-przekształć bez override — padła w v2 (G7.2):
`transform.py::Transform.begin` woła `align_data` (`:211`), a
`mobject.py::Mobject.add_n_more_submobjects` (`:3079`) dokleja wyblakłe duplikaty po
indeksie, więc ramka paruje się z linią osi, a ticki tracą tożsamość.

Ten PoC sprawdza, czy **wyrównanie rodzin po kluczu** to naprawia. Przy okazji wdraża
cztery decyzje maintainera podjęte po v3 (sekcja 2, część B).

Cel nadrzędny bez zmian: z punktu widzenia użytkownika API zachowuje się jak zwykły
Manim. Każdy test „co zobaczy użytkownik” porównuje z Manimem na zwykłych mobjectach.

To nie jest implementacja `manim-plots`: nie dotykaj `src/`, nie projektuj API. Kod
i raport po angielsku.

## 1. Kontekst — przeczytaj przed pisaniem kodu

- `docs/poc3-stack-context.md` w całości, łącznie z *Review notes*.
- `docs/poc2-frame-lifecycle.md`, sekcja G7 (dlaczego natywna droga padła).
- `poc3/model.py`, `poc3/context.py`, testy `poc3/test_*.py`.
- `PLAN.md`, *Generated parts keep identity*: klucz ticka pochodzi z `key(value)`
  lokatora; ADR 0001, sekcja 3, kontrakt `Locator`.

Środowisko: Manim **0.21.0** w `.venv`. Cytując Manim: symbol, potem linia.

**Punkt startowy:** skopiuj `poc3/` do `poc4/` i zmieniaj kopię. Nie importuj z `poc3/`,
`poc2/` ani `poc/`. Skopiowane testy v3 są bazą regresji: mają przechodzić, chyba że
decyzja z sekcji 2 zmienia oczekiwany wynik — każdą taką zmianę wypisz w raporcie.

## 2. Mechanizm do sprawdzenia

### A. Wyrównanie po kluczu

Ticki w PoC mają klucz z prostego lokatora (np. `Multiple(step)` z kluczem `round(v /
step)` i `MaxN`, który zmienia krok w trakcie zmiany zakresu, tak że ticki pojawiają się
i znikają **w środku** animacji, nie tylko na końcach). Kilka ticków niech ma etykietę
(zwykły `VMobject`, bez TeX), żeby było co pokolorować.

1. **`System.align_data`, gdy na stosie jest `Transform.begin`**, robi wyrównanie samo
   zamiast `Mobject.align_data`: paruje dzieci po roli (ramka z ramką, linia osi z linią
   osi) i po kluczu ticka. Żeby rodziny miały tę samą strukturę przez **całą** animację,
   pula ticków to suma kluczy po całej ścieżce parametru od startu do celu — np.
   próbkowanie zakresu w krokach klatek. Klucz nieaktywny w danej chwili ma liść ukryty.
   Kolejność dzieci w obu rodzinach jest identyczna, więc `zip` w
   `animation.py::Animation.get_all_families_zipped` (`:284-286`) paruje poprawnie.
   Zbadaj też, czy `create_starting_mobject` (kopia robiona po `align_data`) dziedziczy
   pulę.
2. **Interpolacja parametrów, nie punktów.** `transform.py::Transform.interpolate_submobject`
   woła `submobject.interpolate(starting, target, alpha, path_func)` (`:249`). Ramka
   interpoluje swoje punkty natywnie (więc `shift`, `rotate`, `path_arc` działają jak
   dziś) i dodatkowo parametry danych układu (zakres). Liście pochodne nie interpolują
   punktów: wyprowadzają geometrię z bieżących parametrów i bieżącej ramki. Tick
   wchodzący i wychodzący zanika przez krycie, nie przez punkty.
3. **Koniec animacji.** Przyjęcie celu jak w v3; liście puli, które nie należą do
   końcowego zbioru kluczy, znikają z rodziny, a ticki o tym samym kluczu to **te same
   obiekty** co przed animacją (styl nadany przez użytkownika zostaje).
4. **Bez `override_animate` na metodach danych** systemu. `set_x_range` to zwykła metoda;
   `.animate` idzie natywnie. `_MethodAnimation.finish` (`transform.py`, `:449-451`)
   odtwarza metody na prawdziwym obiekcie przed `interpolate(1)` — sprawdź, że nic się nie
   podwaja.

Jeśli wyrównanie po kluczu nie wystarcza, zapisz porażkę z dokładnym powodem. Nie
dopasowuj ról po pozycjach punktów ani po kolejności `get_family` — kontekst i tożsamość
mają pochodzić z obiektów (klucz, rola), nie z geometrii.

### B. Decyzje maintainera po v3

1. **Remover zostawia odłączony stan.** Animacja z `remover=True`
   (`animation.py::Animation.is_remover`, `:474`) na artyście: po końcu, łącznie z
   cleanup, artysta jest **odłączony** w stanie, w jakim animacja go zostawiła — po
   `Uncreate` zdegenerowany, po `FadeOut` przywrócony przez cleanup
   (`fading.py::FadeOut.clean_up_from_scene`, `:190-192`). Odłączony nie reaguje na dane
   ani nie przebudowuje się. Ponowne `self.add(curve)` pokazuje to, co pokazałby Manim.
2. **Introducer podpina z powrotem.** Animacja z `introducer=True`
   (`Animation.is_introducer`, `:484`) — `Create`, `Write`, `FadeIn`, `GrowFromCenter` —
   startująca na odłączonym artyście podpina go **na początku** (`suspend_updating` z
   animacją na stosie, jak w v3), więc rysuje się pełna, aktualna krzywa. Ręcznie:
   `refresh()`. Manim po `Uncreate` + `Create` nic nie rysuje; u nas rysuje — to jedyna
   zamierzona różnica, zapisz ją.
3. **Zagęszczanie przy nieliniowej ramce.** Gdy ramka nie jest afiniczna, liście pochodne
   o rzadkiej geometrii (linie osi, ticki) przebudowują się z gęstszym próbkowaniem, tak
   że wygięcie jest poprawne. Porównaj z prawdą analityczną i z Manimem po
   `NumberPlane.prepare_for_nonlinear_transform`. Ramka afiniczna: geometria rzadka jak
   dziś (żadnego kosztu).
4. **Fakty zamiast skrótów z v3** (Review notes v3):
   - rozpoznanie afiniczności operacji artysty z ramki wywołującej na stosie —
     `mobject.py::Mobject.rotate` (`rot_matrix`), `Mobject.scale` (`scale_factor`),
     `Mobject.stretch` (`factor`, `dim`), `Mobject.apply_matrix` (`full_matrix`) — zamiast
     ośmiu punktów próbnych; pozostałe funkcje to węzły nieafiniczne;
   - linie „ostatniego zapisu” w `Mobject.shift` i
     `Mobject.apply_points_function_about_point` wyliczone ze źródła przy imporcie
     (`inspect`), nie wpisane na sztywno.

Symulacja przy decyzji „trwała / nietrwała” (D z v3) obejmuje **wszystkie** animacje,
także z callbackami użytkownika — decyzja maintainera. Zapisz w raporcie jednym zdaniem,
co to znaczy dla callbacku z efektem ubocznym.

## 3. Hipotezy

Werdykty **CONFIRMED** / **FALSIFIED** / **INCONCLUSIVE** z nazwą testu, liczbami
i cytatem z Manim. `Scene.play` z prawdziwą interpolacją, Cairo, niska rozdzielczość,
bez filmu — jak w v3.

### L1 — natywny łańcuch dane + geometria

`ax.animate.shift(RIGHT).set_x_range((0, 20))`, odwrotna kolejność,
`ax.animate.scale(0.5).set_x_range((-5, 5)).rotate(PI / 6)`, sam
`ax.animate.set_x_range((0, 100))` z `MaxN` (ticki zmieniają się w środku). Kryteria:
w **każdej** klatce ticki i zarejestrowani artyści są poprawnym wykresem
interpolowanego zakresu w interpolowanej geometrii (prawda wzorcowa liczona niezależnie);
żadnego wyjątku; stan końcowy równy temu po bezpośrednim `ax.shift(RIGHT);
ax.set_x_range((0, 20))`; nic się nie podwaja.

### L2 — tożsamość ticków

`ax` z ręcznie pokolorowanym tickiem i etykietą o kluczu `k`: po L1 to ten sam obiekt
(`is`), z tym samym kolorem, jeśli `k` jest w końcowym zbiorze. Tick, który wyszedł
i wrócił w trakcie jednej animacji: zapisz, czy zachował styl. D10 mówi, że część, która
opuszcza zakres i wraca, dostaje nowy mobject i traci styl; z pulą liści na całą ścieżkę
może być inaczej — zapisz, co jest prawdą.

### L3 — przejście do innego układu

`Transform(ax, new_ax)` i `ReplacementTransform(ax, new_ax)`, gdzie `new_ax` to drugi
`System` z innym zakresem — idiom
Manima do „przeskalowania osi”. Kryteria jak w L1, plus: artyści zarejestrowani w `ax`
po `Transform` jadą z nowym zakresem; po `ReplacementTransform` — zapisz, do którego
układu należą i czy to jest to, czego spodziewa się użytkownik Manima.

### L4 — remover i introducer

`Uncreate(curve)`, potem `self.add(curve)` (nic nie widać — pikselowo jak Manim), zmiana
danych (nic się nie zmienia), `self.play(Create(curve))` (rysuje pełną, aktualną);
`FadeOut(curve)`, potem `self.add(curve)` (stan pierwotny jak Manim), potem `FadeIn`;
`ShrinkToCenter`; `refresh()`. Tabela przypadek × „Manim robi to samo?”.

### L5 — zagęszczanie

`ApplyPointwiseFunction` i `apply_complex_function` na `ax` (fala, `z**2`): błąd linii
osi i ticków względem prawdy analitycznej przed i po zagęszczeniu; porównanie z
Manimem z `prepare_for_nonlinear_transform`; koszt przebudowy; brak zagęszczania przy
ramce afinicznej.

### L6 — fakty zamiast skrótów

Rozpoznanie afiniczności z ramek wywołujących: te same wyniki K3/K4 co w v3, zero
wywołań na punktach próbnych. Linie ostatniego zapisu: test, który podmienia odczytane
źródło na przesunięte o linię (bez zmiany Manima — np. parametr funkcji wyliczającej)
i pokazuje, że wyliczenie idzie za źródłem.

### L7 — koszt i regresja

Scena z F-1001 bez zmian (p95 <= 4 ms) plus `ax.animate.set_x_range` przez 600 klatek
1080p60: p95 klatki z interpolacją parametrów. Koszt `System.align_data` (pula po
ścieżce). Pełny zestaw skopiowanych testów v3: ile przechodzi, które oczekiwania się
zmieniły i dlaczego.

## 4. Ograniczenia

- Cały kod w `poc4/`. Jedyny plik poza `poc4/` to raport z sekcji 5. Nie zmieniaj
  `src/`, `tests/`, `poc/`, `poc2/`, `poc3/`, `pyproject.toml`, `PLAN.md`, `TODO.md` ani
  ADR. `pyproject.toml` zwalnia już `poc4/*` z reguł `D` i `ANN`.
- `.venv\Scripts\python.exe` bezpośrednio, bez `uv`, bez instalacji, bez sieci.
- Testy: `.venv\Scripts\python.exe -m pytest poc4 -p no:cacheprovider`, bez markera
  `render`.
- Bez `tempfile.mkdtemp`, `TemporaryDirectory`, `tmp_path` (ACL Pythona 3.13 na
  Windows). Media przez zwykłe `Path.mkdir`.
- Bez `MathTex` i `Tex`.
- `ruff check .` i `ruff format --check .` mają przechodzić.
- Nie commituj. Nie monkeypatchuj klas Manima.
- Bez heurystyk dopasowujących delty, pozycje punktów albo kolejność `get_family`.
  Porażkę zapisz.

## 5. Raport

Zapisz `docs/poc4-keyed-alignment.md`:

1. tabela: hipoteza, werdykt, jedno zdanie dowodu;
2. sekcja na każdą hipotezę: co zbudowano, liczby, nazwy testów, cytaty z Manim
   (symbol, potem linia), **co musi się zmienić w `PLAN.md` albo w ADR 0001**;
3. dla L1, L3 i L4: tabela przypadek × kryteria z kolumną „Manim robi to samo?”;
4. zaktualizowana lista *Updated differences from ordinary Manim* z v3;
5. zaktualizowany kontrakt ramek stosu i symboli Manim, na których mechanizm polega;
6. komendy, które odtwarzają każdy wynik.
