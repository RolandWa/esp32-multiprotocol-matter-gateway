# Wytyczne projektowania części drukowanych 3D – na co uważać

Lista kontrolna i wnioski z dotychczasowych projektów (szablony meblowe, ograniczniki wierteł, szyny drzwi przesuwnych szafki nad WC).
Drukarka: **Bambu Lab H2D**, dysza 0,4 mm, płyta **Textured PEI**.
Materiały: **biały PETG Basic** (preferowany w łazience) lub **biały PLA Basic**.

---

## 1. Proces projektowy

1. **Najpierw koncepcja, potem pliki.** Rysunek przekrojów, złączy i kolejności montażu → akceptacja → dopiero wtedy STL.
2. **Uwzględnij realne miejsce montażu.** Mebel może już wisieć, mieć 5 mm szczeliny do ściany, rury, sznury na pranie, obudowę GK – złącza muszą dać się zamknąć w takiej sytuacji.
3. **Element zamykający** (np. środkowy segment szyny) musi wejść między dwa zamocowane → złącze wsuwane w poprzek, nie wzdłuż.
4. **Kierunek wsuwania złączy** od strony dostępnej (otwór szafki), nie od ściany.
5. Po każdej zmianie pełna weryfikacja: kolizje w złożeniu, cienkie ścianki, szczelność siatki.
6. Elementy współpracujące przeliczyć po każdej zmianie (np. wymiar skrzydeł plexi zmienił się z 402 × 874 na 400 × 872 po zmianie głębokości rowków).

## 2. Druk bez podpór

| Zasada | Jak spełnić |
|---|---|
| Elementy złączy wzdłuż osi Z druku | ogony, gniazda, wpusty jako pryzmaty pionowe w orientacji druku |
| Nic nie wisi w powietrzu | występy rosną od stołu albo ich nie ma (zakładka nad kanałami wymagała podpór – odrzucona) |
| Nawisy ≤ 45° | skosy i fazy zamiast półek; otwory skośne pod 45° są OK |
| Otwory poziome ≤ ok. Ø8 | większe → orientacja pionowa albo kształt łzy |
| Zaokrąglenie krawędzi leżącej na stole | ostatni fragment łuku zamienić na fazę 45° |
| Kanały / rowki | otwarte do góry w orientacji druku |
| Mostki | tylko krótkie (do ok. 10 mm), podparte z dwóch stron |
| Orientacja | podana w pliku STL – nie obracać w slicerze |

## 3. Cienkie i samotne elementy

- **Minimalna ścianka 1,5–2 mm** (≈ 4 linie dyszy 0,4); poniżej 0,8 mm slicer tworzy „samotne” ścianki albo je pomija.
- **Złącze nie może przecinać kanałów, rowków ani otworów** – inaczej rozpada się na cienkie listki (błąd pierwszej wersji jaskółczego ogona).
- Ogon / wpust tylko w pełnym materiale, ≥ 1 mm od dna kanału i ≥ 2 mm od krawędzi.
- Przy złączu usuń całe resztki cienkich przegród zamiast zostawiać pasek 0,5 mm.
- Ścianka wokół gniazda wkrętu / zaślepki ≥ 1 mm; jeśli mniej – mniejszy wkręt albo przesunięcie osi.
- **Kontrola:** przekroje warstw co 0,2–0,4 mm + podgląd warstw w Bambu Studio przed drukiem.

## 4. Siatka STL

- Przed wysłaniem: **0 otwartych krawędzi, 0 non-manifold, 0 odwróconych ścian** – sprawdzić **zapisany plik**, nie tylko model.
- Operacje CSG zostawiają wierzchołki T → zgrzać wierzchołki, rozciąć krawędzie w punktach T, triangulować od środka ściany.
- Gdy Bambu Studio pokazuje „repaired / open edges / reversed faces” – nie drukować, poprawić plik u źródła i zaimportować od nowa.

## 5. Pasowania (dysza 0,4)

| Połączenie | Wartość wyjściowa | Uwagi |
|---|---|---|
| Otwór przelotowy M3 | Ø3,6 | |
| Gniazdo nakrętki M3 (3 mm) | 5,9 × 3,4 | otwarte w stronę drukowalną |
| Tuleja pod wiertło | Ø wiertła + 0,3 | przetrzeć wiertłem |
| Jaskółczy ogon (5 × 4/6 mm) | 0,05 / 0,10 / 0,15 na stronę | próbka, wybór po teście |
| Zaślepka na wcisk, gniazdo Ø8,2 | Ø8,05 / 7,95 / 7,85 | próbka |
| Zaślepka na wcisk, gniazdo Ø7,4 | Ø7,25 / 7,15 / 7,05 | próbka |
| Kanał na plexi 3 mm | 3,7 | druk zwęża szczeliny |
| Kołek drukowany Ø3 | otwór Ø3,25 | |

- **Zawsze najpierw próbki pasowania** (krótki odcinek + 3 warianty luzu), dopiero potem komplet.
- **Próbki z tego samego filamentu co komplet** – PETG i PLA pasują inaczej.
- Cały komplet z jednego materiału (różny skurcz zmienia pasowania).

## 6. Materiały

| | PETG Basic (biały) | PLA Basic (biały) |
|---|---|---|
| Łazienka, wilgoć, ciepło | **lepszy** | OK w temp. pokojowej, z dala od grzejnika |
| Wkręty | odporny, nie pęka | kruchy – nie dokręcać na siłę |
| Wymiary | lekko zwęża otwory i szczeliny | dokładniejszy |
| Wcisk | bardziej sprężysty, wyrozumiały | sztywny |
| Stół | Textured PEI (gładki PEI tylko z klejem jako separatorem) | dowolny |
| Po druku | usunąć nitki z kanałów i gniazd (nożyk, opalarka) | – |
| Profil Bambu Studio | „Bambu PETG Basic” | „Bambu PLA Basic” |

## 7. Wkręty w częściach drukowanych

- Wkręt przechodzi przez część drukowaną w płytę; nigdy nie gwintować w plastik (wyjątek: M3 w nakrętkę w gnieździe).
- Gniazdo pod łeb stożkowy 90° + gniazdo zaślepki ok. 3,3 mm głębokości; zaślepka odwzorowuje kształt powierzchni (łuk).
- W czole płyty 18 mm wkręt w osi lub ≤ 2,5 mm od środka; nawiercić Ø2,5 mm.
- Dobrane wkręty: AZMET 4 × 30 (łeb 7,5) – gniazdo Ø8,2; wkręt 3,5 × 30 – gniazdo Ø7,4; euro 6,3 × 13 – tylko w lico płyty w otwór Ø5.
- Wkręty euro z łbem walcowym (Ø9,3) nie mieszczą się w kanałach – tylko do prowadników.

## 8. Ustawienia druku (części konstrukcyjne)

- **4 obrysy, wypełnienie ~30 %** (nie 2 obrysy / 15 % z profilu domyślnego), warstwa 0,2 mm.
- Zaślepki i widoczne łuki: warstwa 0,12 mm.
- Szew na niewidocznej ścianie (od strony płyty / ściany).
- Długość części ≤ ok. 240 mm (stół H2D) – dłuższe dzielić na segmenty ze złączem.

## 9. Wnioski z projektu szyn szafki nad WC

- Profil = grubość płyty (18 mm), wysunięcie 13,6 mm, zaokrąglenie R6 od frontu, bez kołnierzy.
- Kanały: górny 9 mm (unoszenie skrzydła), dolny i boczne 4 mm; skrzydła plexi opal 3 mm 400 × 872.
- Segmenty łączone jaskółczym ogonem wsuwanym w poprzek szyny; narożniki 45° na kołki Ø3 prostopadłe do ucięcia.
- Druk krawędzią zewnętrzną do stołu, kanały do góry.
- Kolejność: boki → narożne segmenty góry/dołu (po skosie na kołki) → środkowe segmenty wsuwane → skrzydła → zaślepki.
- Plexi PMMA opal 3 mm cięta na wymiar (2,35 zł / 10 × 10 cm); polistyren 2 mm i PP kanalikowy – za wiotkie / za małe arkusze.

## 10. Lista kontrolna przed wysłaniem plików

- [ ] Koncepcja zaakceptowana
- [ ] Kolejność montażu możliwa na zamocowanym meblu (w tym element zamykający)
- [ ] Brak podpór w orientacji z pliku
- [ ] Brak ścianek < 1,5 mm i samotnych elementów (przekroje warstw)
- [ ] Zero kolizji w złączach (model złożony)
- [ ] Siatka szczelna (0 błędnych krawędzi w zapisanym STL)
- [ ] Próbki pasowania dołączone (z tego samego materiału)
- [ ] Długość części ≤ ok. 240 mm
- [ ] Elementy współpracujące przeliczone (plexi, wkręty, zaślepki)
- [ ] Zalecane ustawienia druku podane (materiał, obrysy, wypełnienie)
