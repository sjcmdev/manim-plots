# Prompt: audyt upstream issues i PR-ów Manim dotyczących graphingu

Przeprowadź **audyt źródłowy**, a nie przegląd architektury ani projektowanie
rozwiązania. Zbadaj issues i pull requesty repozytorium
[`ManimCommunity/manim`](https://github.com/ManimCommunity/manim), aby ustalić, co
upstream już zgłosił, naprawił, odrzucił albo uznał za zachowanie zamierzone w
obszarze mechaniki wykresów i układów współrzędnych.

Raport napisz po polsku. Oryginalnych wypowiedzi maintainerów nie tłumacz w polu
cytatu.

## 1. Cel i kontekst

Audyt ma być podstawą do weryfikacji defektów zidentyfikowanych wcześniej w ManimCE
0.19.2 przed pracą nad niezależną biblioteką `manim-plots`, której wersją docelową
jest ManimCE 0.21.0.

`manim-plots` ma być biblioteką pisaną od zera. Korzysta z podstawowych mobjectów
Manima, takich jak `Line`, `MathTex` i `VGroup`, ale **nie dziedziczy** po
`Axes`, `NumberLine` ani `NumberPlane`. Ta informacja służy wyłącznie do oceny
implikacji i ograniczeń interoperacyjności. Nie projektuj na jej podstawie
architektury ani rozwiązań.

## 2. Zakres upstream

Przejrzyj **issues i pull requesty, otwarte i zamknięte, bez ograniczenia daty**,
które dotyczą kodu lub zachowania związanego z:

- całym katalogiem `manim/mobject/graphing/`, także jego historycznymi nazwami,
  lokalizacjami i przeniesionym kodem;
- `manim/mobject/geometry/line.py`, o ile wątek ma znaczenie dla obiektów z
  `graphing/`, szczególnie `NumberLine`;
- `Mobject.apply_points_function_about_point` w
  `manim/mobject/mobject.py`, o ile wątek ma znaczenie dla transformacji układów
  współrzędnych, osi albo odwzorowań liczba–punkt;
- historycznymi odpowiednikami powyższych klas, metod i plików.

Włącz w szczególności wątki dotyczące `CoordinateSystem`, `Axes`, `ThreeDAxes`,
`NumberPlane`, `ComplexPlane`, `NumberLine`, `ParametricFunction`, `FunctionGraph`,
`ImplicitFunction`, `LinearBase`, `LogBase`, klas z `probability.py` oraz ich metod
konwersji współrzędnych, tworzenia ticków i etykiet, skalowania, transformacji i
rysowania funkcji.

Wątek wchodzi do raportu tylko wtedy, gdy jego związek z tym zakresem można wykazać.
Samo wystąpienie ogólnego słowa, np. `line`, `scale`, `plot` albo `axis`, nie
wystarcza.

## 3. Priorytet źródeł

Najcenniejsze są wątki zamknięte jako **wontfix / not planned / by design / out of
scope** oraz PR-y zamknięte bez merge'a, ponieważ mogą zawierać uzasadnienie decyzji
maintainerów. Szukaj zarówno formalnej etykiety lub `state_reason`, jak i wypowiedzi
o tym znaczeniu w komentarzach lub review.

Kolejność prezentacji wyników:

1. zamknięte jako `not planned`, `wontfix`, „by design” albo równoważne;
2. zamknięte PR-y bez merge'a;
3. duplikaty prowadzące do uzasadnionego wątku nadrzędnego;
4. naprawione lub zmergowane;
5. nadal otwarte;
6. niejednoznaczne.

Nie ograniczaj jednak wyszukiwania do tych kategorii.

## 4. Lista kontrolna 13 naszych defektów

Lista służy do kontroli pokrycia, **nie jest zamkniętym katalogiem problemów**.
Aktywnie szukaj także zachowań, defektów, ograniczeń i decyzji upstream, których na
niej nie ma.

- **D01 — Float accumulation:** float accumulation w generowaniu ticków
  `NumberLine` przez `np.arange`.
- **D02 — Tip changes semantics:** `include_tip` zmienia zakres ticków i mapowanie
  współrzędnych w niespójny sposób.
- **D03 — No plot clipping:** krzywe wychodzą poza viewport osi; brak clippingu,
  szczególnie dla funkcji z asymptotami lub nieciągłościami.
- **D04 — Aspect-ratio distortion:** niezależna parametryzacja długości osi
  zniekształca proporcje geometryczne wykresu.
- **D05 — `unit_size` through config:** `unit_size` jest ignorowane, gdy zostanie
  przekazane przez `axis_config`.
- **D06 — Stale ticks after range mutation:** zmiana `x_range` po utworzeniu obiektu
  pozostawia nieaktualne ticki.
- **D07 — Broken ndarray guard:** guard tablicowy w `LogBase.inverse_function` jest
  wadliwy; wartości ujemne przechodzą w `NaN` bez jawnego błędu.
- **D08 — Missing logarithmic minor ticks:** `LogBase` nie udostępnia minor ticks
  między dekadami.
- **D09 — Misleading `LogBase` naming:** metoda `LogBase.function()` realizuje
  funkcję wykładniczą, a nie logarytmiczną.
- **D10 — Label collisions:** brak mechanizmu unikania kolizji etykiet przy dużej
  gęstości.
- **D11 — Tick direction:** ticki są wycentrowane na linii osi i nie można skierować
  ich wyłącznie na zewnątrz.
- **D12 — `_origin_shift` outside zero:** `_origin_shift` przy zakresie
  nieobejmującym zera przycina przesunięcie do minimum zakresu.
- **D13 — Geometry corrupts coordinate mapping:** operacje geometryczne na
  `NumberLine`, wynikające m.in. z dziedziczenia po `Line` i użycia
  `apply_points_function_about_point`, mogą rozspójnić odwzorowanie liczba–punkt.

Brak natywnej legendy **nie należy do tych 13 defektów**; jest brakiem funkcji. Jeżeli
upstream zawiera istotne decyzje lub ograniczenia dotyczące legend, można je ująć
wyłącznie jako znalezisko spoza listy.

## 5. Metoda wyszukiwania

Zastosuj co najmniej trzy niezależne przejścia.

### A. Wyszukiwanie konwersacji GitHub

Wyszukuj osobno issues i PR-y, a w każdej grupie osobno stan `open` i `closed`.
Użyj:

- nazw klas, metod, parametrów i plików;
- dawnych nazw i dawnych ścieżek kodu;
- terminów opisujących obserwowane zachowanie oraz ich synonimów;
- etykiet i powodów zamknięcia, m.in. `bug`, `wontfix`, `not planned`, `duplicate`;
- kombinacji pojęć, nie tylko dosłownego brzmienia D01–D13.

Wyszukiwanie ma obejmować między innymi: tick generation and precision, endpoint
inclusion, tips, coordinate conversion and round trips, scaling and stretching,
aspect ratio, stale state/cache, clipping, discontinuities, asymptotes, `NaN`/`Inf`,
logarithmic scales, minor ticks, labels and overlap, renderer differences,
transformations, `animate`, `become`, `apply_points_function_about_point`,
`number_to_point`/`n2p`, `point_to_number`/`p2n`,
`coords_to_point`/`c2p`, `point_to_coords`/`p2c` oraz konfigurację osi.

### B. Przejście po historii kodu

Nie polegaj wyłącznie na wyszukiwaniu tekstowym w tytułach i opisach. Przejrzyj
historię zmian wszystkich plików objętych zakresem. Odszukaj PR-y stojące za
commitami, które modyfikowały te pliki, i otwórz ich pełne wątki. To przejście ma
wykryć PR-y o ogólnych tytułach, które nie zawierają nazw klas ani symptomów.

### C. Rozwijanie odsyłaczy

Jeżeli otwarty wątek odsyła do innego issue, PR-a, review, wcześniejszej implementacji
albo duplikatu, otwórz również wskazany wątek, jeżeli może należeć do zakresu. Kontynuuj
aż do wyczerpania istotnych odsyłaczy.

Jeśli narzędzie lub API ogranicza liczbę wyników, dziel zapytania według typu, stanu,
okresu, klasy lub rodziny problemu i stronicuj do końca. Jeśli mimo tego pełny przegląd
nie jest możliwy, nie próbuj maskować luki — oznacz audyt jako nieukończony i podaj
dokładne liczby w tabeli pokrycia.

## 6. Twarde reguły dowodowe

1. **Otwórz każdy znaleziony wątek.** „Przejrzany” oznacza przeczytanie opisu,
   wszystkich komentarzy oraz — dla PR-a — conversation, review i istotnych zmian.
   Snippet lub lista wyników nie są przeglądem wątku.
2. **Nie streszczaj wypowiedzi jako cytatu.** W polu „Cytat maintainera” wstaw krótki,
   dosłowny fragment wypowiedzi (maksymalnie 25 słów), wraz z autorem, datą i
   permalinkiem bezpośrednio do komentarza lub review.
3. Osobę nazywaj maintainerem tylko wtedy, gdy potwierdza to rola GitHub
   (`OWNER`, `MEMBER`, `COLLABORATOR`) albo inne jawne źródło. W przeciwnym razie
   wpisz `unknown`.
4. **Brak kanonicznego URL issue lub PR-a oznacza, że wpis nie wchodzi do raportu.**
   Nie używaj URL strony wyników wyszukiwania jako źródła.
5. Nie wyprowadzaj wersji z samej daty. Wersję uznaj za ustaloną tylko na podstawie
   jawnego zgłoszenia, milestone'u, tagu, changelogu, testu reprodukcyjnego albo
   zmergowanego kodu. W innych przypadkach wpisz `unknown`.
6. Gdy stan, wersja, rola autora, intencja maintainerów albo związek z defektem nie są
   ustalone, wpisz **`unknown` zamiast zgadywać**.
7. Odróżniaj fakt ze źródła od własnej inferencji. Inferencję oznacz jawnie słowem
   `inference` i obniż odpowiednio poziom pewności.
8. Nie utożsamiaj automatycznie `closed` z `fixed` ani zamkniętego PR-a z kodem
   obecnym w wydaniu. Rozróżniaj `closed-completed`, `closed-not-planned`, `duplicate`,
   `merged` i `closed-unmerged`.
9. Jeden wątek opisz tylko raz, nawet jeśli pojawił się w wielu zapytaniach. Może on
   mapować się na kilka defektów.
10. Nie pomijaj trafienia tylko dlatego, że nie pasuje do D01–D13. Nadaj mu identyfikator
    `Nxx` i umieść w sekcji znalezisk spoza listy.
11. **Nie proponuj żadnych rozwiązań dla `manim-plots`.** Nie podawaj implementacji,
    architektury, obejść, rekomendacji, planu prac ani „next steps”. Masz raportować
    stan upstream i jego konsekwencje, a nie projektować bibliotekę.

## 7. Sztywny schemat każdego wpisu

Każde issue lub PR przedstaw w osobnym wpisie. Nagłówek ma postać:

`### Uxxx — dokładny tytuł wątku`

Pod nagłówkiem podaj **dokładnie poniższe osiem pól, zawsze w tej kolejności**:

1. **Typ:** `issue` albo `PR`.
2. **Link:** kanoniczny URL issue albo PR-a.
3. **Status:** dla issue użyj `open`, `closed-completed`, `closed-not-planned`,
   `duplicate` albo `unknown`; dla PR-a użyj `open`, `draft`, `merged`,
   `closed-unmerged` albo `unknown`. Dopisz jawne etykiety i `state_reason`, jeśli są
   dostępne.
4. **Wersje:** `reported: ...; reproduced: ...; fixed/changed: ...; current: ...`.
   Każdą nieustaloną część oznacz `unknown`.
5. **Cytat maintainera:** `„...” — @autor, RRRR-MM-DD, permalink`. Jeżeli brak
   potwierdzonej wypowiedzi maintainera, wpisz
   `unknown — brak potwierdzonego cytatu maintainera w przejrzanym wątku`.
6. **Mapowanie na nasz defekt:** `Dxx — direct`, `Dxx — partial`, kilka identyfikatorów
   albo `Nxx — poza listą`. Nie wymuszaj mapowania do D01–D13.
7. **Implikacja:** wyłącznie konsekwencja dla zakresu, kompatybilności lub założeń
   `manim-plots`; bez propozycji rozwiązania. Oddziel fakt od `inference`.
8. **Poziom pewności:** `high`, `medium` albo `low` oraz jednozdaniowe uzasadnienie
   oparte na jakości dowodu.

Nie dodawaj dziewiątego pola. Dodatkowy kontekst umieszczaj tylko w odpowiednim z
ośmiu pól.

## 8. Obowiązkowa struktura raportu

### 8.1. Stan audytu

Na samym początku napisz jednoznacznie `COMPLETE` albo `INCOMPLETE`, podaj datę
wykonania, commit/tag upstream użyty do sprawdzania aktualnego kodu oraz wersje
odniesienia 0.19.2 i 0.21.0. `COMPLETE` wolno użyć tylko wtedy, gdy wszystkie zwrócone
wyniki i wszystkie istotne odsyłacze zostały rzeczywiście otwarte i przejrzane.

### 8.2. Wontfix / not planned / closed-unmerged

Najpierw wpisy o najwyższej wartości decyzyjnej, zgodnie z priorytetem z sekcji 3.

### 8.3. Pozostałe znaleziska mapujące się na D01–D13

Podziel według D01–D13, ale nie duplikuj tych samych wątków.

### 8.4. Znaleziska spoza listy kontrolnej

Obowiązkowa sekcja, nawet jeśli wynik brzmi `Brak`. Każdy nowy problem oznacz `Nxx`
i opisz w tym samym ośmiopolowym schemacie.

### 8.5. Tabela pokrycia wyszukiwania

Ta sekcja jest obowiązkowa i nie może być zastąpiona opisem słownym. Podaj co najmniej
kolumny:

| Rodzina zapytania / przejście | Typ i stan | Wyniki surowe | Unikalne wątki | Wątki otwarte i w pełni przejrzane | Nieprzejrzane | Włączone do raportu | Uwagi / ograniczenie |
|---|---|---:|---:|---:|---:|---:|---|

Pod tabelą podaj sumy globalne po deduplikacji. Wyjaśnij rozbieżności między liczbą
wyników a liczbą przejrzanych. Jeśli choć jeden wynik lub istotny odsyłacz pozostał
nieprzejrzany, stan audytu musi być `INCOMPLETE`.

Dodaj również macierz pokrycia listy kontrolnej:

| Defekt | Bezpośrednie ślady upstream | Częściowe ślady | Liczba przejrzanych powiązanych wątków | Ocena pokrycia |
|---|---:|---:|---:|---|

### 8.6. Nasze defekty bez śladu upstream

Wymień jawnie każdy z D01–D13, dla którego nie znaleziono żadnego wiarygodnego śladu.
Oddziel:

- `brak śladu`;
- `tylko ślad częściowy lub pośredni`.

Nie interpretuj braku śladu jako dowodu, że problem nie istnieje.

### 8.7. Ograniczenia biblioteki spoza hierarchii klas Manima

Na podstawie **dowodów znalezionych w issues i PR-ach** wypisz ograniczenia i koszty
kompatybilności wynikające z tego, że `manim-plots` nie dziedziczy po `Axes`,
`NumberLine` ani `NumberPlane`. Sprawdź zwłaszcza zależności od:

- `isinstance` i kodu oczekującego konkretnych klas Manima;
- metod lub narzędzi oczekujących `CoordinateSystem`;
- zachowania `animate`, transformacji, `become`, kopiowania i updaterów;
- mapowania współrzędnych po transformacjach geometrycznych;
- kontraktów zwracanych obiektów, typów i integracji rendererów;
- funkcji pomocniczych, które zakładają istniejącą hierarchię klas.

Dla każdego ograniczenia podaj: fakt upstream, URL źródła, krótki dosłowny cytat
maintainera albo `unknown`, implikację dla niezależnej biblioteki i poziom pewności.
Odróżnij twarde ograniczenie od kosztu kompatybilności i od niepotwierdzonej
inferencji. Jeśli brak dowodów upstream, napisz to wprost; nie wypełniaj sekcji
spekulacją i nie proponuj rozwiązania.

### 8.8. Ograniczenia samego audytu

Wymień ograniczenia narzędzi, indeksowania, paginacji, niedostępnych komentarzy,
niejednoznacznych historycznych wersji i innych luk. Nie używaj ogólnego zastrzeżenia,
jeżeli można podać konkretną liczbę lub zakres luki.

## 9. Kryteria poziomu pewności

- **high:** bezpośrednia wypowiedź potwierdzonego maintainera albo zmergowany PR z
  jednoznacznym testem/zmianą i ustaloną wersją;
- **medium:** mocny związek potwierdzony treścią wątku lub kodem, ale niepełna
  informacja o intencji, roli autora albo wersji;
- **low:** związek pośredni, niejednoznaczny lub oparty częściowo na jawnie oznaczonej
  inferencji.

## 10. Kontrola przed oddaniem

Przed oddaniem raportu sprawdź:

- czy każdy wpis ma kanoniczny URL i wszystkie osiem pól;
- czy każdy cytat jest dosłowny, krótki i ma permalink;
- czy nie nazwano nikogo maintainerem bez potwierdzenia;
- czy `unknown` zastępuje wszystkie nieuprawnione domysły;
- czy przejrzano pełne wątki, a nie tylko wyniki wyszukiwania;
- czy D01–D13 mają jawny wynik pokrycia;
- czy aktywnie raportowano znaleziska spoza listy;
- czy tabela pokazuje wyniki zwrócone **w porównaniu z** faktycznie przejrzanymi;
- czy nieukończony przegląd jest oznaczony `INCOMPLETE`;
- czy sekcja o bibliotece spoza hierarchii Manima opiera się na dowodach;
- czy w całym raporcie nie ma propozycji rozwiązań, architektury, obejść ani planu
  implementacji dla `manim-plots`.
