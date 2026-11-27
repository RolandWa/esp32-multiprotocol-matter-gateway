# Specyfikacja Techniczna i Wymagania Projektowe: `esp32-multiprotocol-matter-gateway`

**Autor:** RolandWa  
**Cel projektu:** Budowa lokalnej, wieloprotokołowej bramki Smart Home integrującej urządzenia **Wi-Fi, Bluetooth Low Energy (BLE) oraz Zigbee 3.0** i wystawiającej je bezpośrednio do ekosystemu **Amazon Alexa** za pomocą standardu **Matter Bridge (Matter-over-Wi-Fi)** — bez konieczności utrzymywania zewnętrznego serwera (np. Raspberry Pi / Home Assistant).

> **Status weryfikacji (2026-11-26):** dokument scala ustalenia z Gemini oraz dawny `repository_readme.md`. Liczby (pamięci, moce, odległości anten, piny RF switch GPIO3/GPIO14, kanały Zigbee/Wi-Fi, progi IAQ) pochodzą z materiałów AI i są **niezweryfikowane** — przed użyciem sprawdzić z datasheetami / wiki Seeed / dokumentacją Espressif i Bosch. Otwarte decyzje (wersja IDF + esp-matter, C6 jako RCP, licencja, zakres KiCad): [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md). Wartości elementów i numery części: źródłem prawdy jest schemat KiCad (gdy powstanie).

> **Doprecyzowanie autora (2026-11-26) — rola Wi-Fi:** Wi-Fi **nie jest protokołem czujników**, tylko **łączem bramki do Alexy** (Matter-over-Wi-Fi z routerem domowym i Echo). Bramka **zbiera** dane z czujników **BLE** i **Zigbee** (oraz z własnego BME680), **pakuje** je jako urządzenia Matter Bridge i **wysyła przez Wi-Fi** do Alexy. Dawne sformułowania „urządzenia Wi-Fi” / „czujniki Wi-Fi” w tym dokumencie oznaczają więc to łącze; osobne czujniki lub aktory działające po Wi-Fi (np. gniazdka Wi-Fi) są **poza zakresem**, chyba że autor zdecyduje inaczej (wymagałyby własnego protokołu lub mostu — esp-matter nie ma gotowego). Uwaga: „Bluetooth” w tym projekcie = **Bluetooth Low Energy**; układy ESP32-S3 i ESP32-C6 **nie mają Bluetooth Classic (BR/EDR)** (z wiedzy o układach, do potwierdzenia w datasheecie) — czujniki klasyczne nie będą obsługiwane.

---

## 1. Architektura Sprzętowa (Układ Dual-SoC + Czujnik Środowiskowy)

Ze względu na fizyczne ograniczenia toru radiowego 2.4 GHz (współdzielona antena i kolizje czasowe między stałym nasłuchem koordynatora Zigbee a ruchem Wi-Fi/BLE) oraz brak sprzętowego radia IEEE 802.15.4 w układzie ESP32-S3, bramka opiera się na architekturze **dwupłytkowej połączonej przewodowo przez UART**.

```text
+-------------------------------------------------------------------+
|                        AMAZON ECHO / ALEXA                        |
|                  (Lokalny kontroler Matter LAN)                   |
+---------------------------------+---------------------------------+
                                  |
                         Matter-over-Wi-Fi (IPv6)
                                  |
+---------------------------------v---------------------------------+
|  MODUŁ 1: Seeed Studio XIAO ESP32-S3 Plus (Host)                  |
|  - Wi-Fi 2.4 GHz (Matter Bridge - esp-matter)                     |
|  - Bluetooth LE (commissioning + pasywny skaner czujników)        |
|  - Antena zewnętrzna U.FL -> SMA #1                               |
+----------------+---------------------------------+----------------+
                 |                                 |
      UART (TX, RX, RTS, CTS)                 I2C (SDA, SCL)
                 |                                 |
+----------------v----------------+   +------------v----------------+
| MODUŁ 2: XIAO ESP32-C6 (RCP)    |   | MODUŁ 3: Bosch BME680       |
| - Radio IEEE 802.15.4 (Zigbee)  |   | - Temp., wilgotność,        |
|   Wi-Fi/BLE wyłączone           |   |   ciśnienie, IAQ (BSEC)     |
| - Antena U.FL -> SMA #2         |   |                             |
+---------------------------------+   +-----------------------------+
```

### Wykaz komponentów (BOM)
1. **Moduł 1 — Host Główny (Wi-Fi + BLE + Matter Bridge + Logika):**
   * **Układ:** `Seeed Studio XIAO ESP32-S3 Plus`
   * **Specyfikacja:** Dwurdzeniowy Xtensa LX7 240 MHz, **8 MB PSRAM**, **16 MB Flash**, gniazdo antenowe **U.FL (I-PEX)**, 18 wyprowadzonych GPIO.
   * **Zadania:**
     * Utrzymanie połączenia Wi-Fi 2.4 GHz z siecią domową i kontrolerem Amazon Echo (Alexa).
     * Działanie jako **Matter Bridge** (stos ConnectedHomeIP / `esp-matter`).
     * Obsługa Bluetooth LE (proces *commissioning* Matter oraz pasywne skanowanie czujników BLE z niskim priorytetem odświeżania).
     * Odczyt danych środowiskowych z czujnika BME680 po magistrali I2C i zapis stanu kalibracji BSEC w pamięci NVS.
     * Komunikacja z koprocesorem Zigbee przez 4-przewodowy UART.
2. **Moduł 2 — Koprocesor Radiowy Zigbee (802.15.4 RCP):**
   * **Układ:** `Seeed Studio XIAO ESP32-C6`
   * **Specyfikacja:** RISC-V 160 MHz, 512 KB SRAM, 4 MB Flash, sprzętowe radio **IEEE 802.15.4**, gniazdo antenowe **U.FL (I-PEX)** przełączane układem RF switch.
   * **Zadania:**
     * Wyłączna obsługa warstwy fizycznej i MAC protokołu **IEEE 802.15.4** (Wi-Fi oraz BLE są na tym układzie całkowicie wyłączone w firmware).
     * Praca jako dedykowany koprocesor radiowy (`ot_rcp` / ZBOSS RCP) zapewniający 100% czasu antenowego dla odbioru ramek z czujników zalania oraz natychmiastowego sterowania gniazdkami i zaworami.
     * **Wymóg programowy:** W kodzie startowym należy jawnie przełączyć przełącznik RF na złącze zewnętrzne U.FL: ustawić `GPIO3 = LOW` (włączenie zasilania przełącznika RF), odczekać ok. 100 ms, następnie `GPIO14 = HIGH` (wybór gniazda U.FL zamiast wbudowanej anteny ceramicznej). *(Korekta 2026-11-26: wcześniejsza wersja miała `GPIO3 = HIGH` — wiki Seeed podaje LOW; forum Seeed zgłasza, że w ESP-IDF przełącznik trzeba obsłużyć ręcznie. Do potwierdzenia na płytce.)*
3. **Moduł 3 — Czujnik Środowiskowy i Jakości Powietrza (Wietrzenie):**
   * **Układ:** `Bosch BME680` (np. moduł PCB **CJMCU-680** lub odpowiednik I2C).
   * **Mierzone parametry:** Temperatura, wilgotność względna, ciśnienie atmosferyczne oraz lotne związki organiczne (VOC) przeliczane przez bibliotekę **Bosch BSEC** na indeks jakości powietrza **IAQ (0–500)** określający potrzebę przewietrzenia mieszkania.
4. **Elementy połączeniowe i antenowe:**
   * 2× antena naklejana FPC **2J Antennas `2JF0802P-010MC137-UFL`** (TME; wybór autora 2026-11-26): Bluetooth/ISM/LoRa/SIGFOX/WiFi/ZigBee, 2.41–2.49 GHz oraz 4.92–7.125 GHz, 39.6 × 8.4 × 0.2 mm, przyklejana, kabel MC137 0.1 m, wtyk U.FL, zysk „1.7 / 4.6 / 5.1 dBi” (**zysk dla 2.4 GHz nie jest podany wprost** — prawdopodobnie 1.7 dBi, niepotwierdzone). Wtyk wpina się bezpośrednio w gniazdo U.FL modułu — **pigtaile U.FL → SMA i gniazda SMA w obudowie nie są potrzebne**. Pozycja BOM zastępuje wcześniejszy zapis „2× pigtail U.FL → SMA + 2× zewnętrzna antena dookólna” (wariant z antenami SMA zostaje jako opcja, jeśli zasięg okaże się za mały). Patrz „Decyzje konstrukcyjne” poniżej.
   * Przewody połączeniowe lutowane bezpośrednio do padów modułów lub goldpiny 2.54 mm (moduły jeden nad drugim) — **bez własnej płytki PCB**.
   * Zasilacz: **IKEA SJÖSS 20 W** (nr art. 506.217.28, jedno gniazdo USB-C, PD, 15 zł; przewód USB-C ↔ USB-C kupowany osobno) — patrz decyzja 7.
   * Superkondensator 5.5 V na pinie `BAT` hosta (C3) — patrz decyzja 6.
   * Zasilanie: **wyłącznie przez gniazdo USB-C modułu hosta (XIAO ESP32-S3 Plus)**, zasilacz 5 V / min. 1.5 A; z pada `5V` hosta wyprowadzone jest 5 V do pada `5V` modułu C6 (kondensatory 100 µF + 100 nF przy końcu przewodu na module C6).

### Decyzje konstrukcyjne (2026-11-26, ustalone przez autora)
1. **Zasilanie:** jedno źródło — USB-C hosta. Moduł C6 dostaje 5 V przewodem z pada `5V` hosta. USB-C modułu C6 służy tylko do flashowania/serwisu i **nie wolno go podłączać, gdy host jest zasilony** (dwa źródła 5 V na jednej szynie), chyba że w przewodzie 5 V host→C6 jest dioda Schottky (do decyzji; wymaga sprawdzenia, jak XIAO prowadzi VBUS do pada `5V` — niezweryfikowane).
2. **Reset i flashowanie C6 przez hosta:** linie `CHIP_EN` i `BOOT` modułu C6 sterowane z GPIO hosta (S3 D0/D1, wyjścia open-drain, rezystory szeregowe 1 kΩ). Pozwala hostowi zresetować RCP i wgrać nowy firmware bez dotykania modułu C6.
3. **Montaż:** brak własnej PCB. Moduły XIAO, czujnik BME680 i drobne elementy (rezystory, kondensatory) są łączone przewodami / goldpinami we wspólnej obudowie drukowanej 3D. Moduły można ustawić jeden nad drugim, ale goldpiny same nie wystarczą — sygnały mają różne piny (TX↔RX, RTS↔CTS), więc potrzebne są przewody lub mała płytka pośrednia (perfboard). *Do zastanowienia:* przewody vs goldpiny; wybór wpływa na wysokość stosu i dostęp do USB-C / przycisków.
4. **Anteny — zmiana 2026-11-26:** autor wybrał **antenę naklejaną FPC `2JF0802P-010MC137-UFL`** (TME, ok. 1.7 dBi dla 2.4 GHz — niepotwierdzone), więc poniższy zapis o „zewnętrznych, większych antenach z pigtailem SMA” obowiązuje już tylko jako wariant zapasowy. Uwaga: ta antena ma zysk zbliżony do anteny dołączanej do modułów XIAO (Botland podaje antenę FPC w zestawie S3 Plus), więc zysk zasięgu względem niej będzie niewielki; limit EIRP przestaje być problemem. Montaż: **naklejona od wewnątrz na plastikowej ściance obudowy** (bez metalu, folii ani przewodzącego filamentu przy antenie); kabel 10 cm ogranicza odległość modułu od ścianki. Pierwotne założenie, zachowane jako wariant: oba moduły z **zewnętrznymi, większymi antenami** (U.FL → pigtail → SMA na ściance obudowy), aby zwiększyć zasięg łącza Wi-Fi do routera, odbioru czujników BLE (host) oraz Zigbee (C6). Wymagania: zysk i typ anteny do wyboru; pigtaile jak najkrótsze (strata kabla 1.13 mm ≈ 0.2 dB na 10 cm, ≈ 0.7 dB na 30 cm przy 2.4 GHz — niezweryfikowane); sprawdzić płeć złącz (SMA / RP-SMA). **Uwaga regulacyjna (niezweryfikowane):** w UE obowiązuje limit EIRP dla pasma 2.4 GHz (ETSI EN 300 328, ok. 20 dBm) — antena o większym zysku przy pełnej mocy modułu może go przekroczyć, więc trzeba sprawdzić moc nadawania i w razie potrzeby ją ograniczyć w firmware.
   **Rozmieszczenie dwóch anten (2026-11-26; obliczenia + źródła ogólne, do sprawdzenia pomiarem na prototypie).** Jednej „dobrej” odległości nie ma — izolacja zależy od odległości, zysku i ustawienia anten. Dla anten w polu dalekim, bez odbić (Friis): izolacja ≈ FSPL(d) − G₁ − G₂, FSPL = 20·log₁₀(4πd/λ), λ ≈ 12.3 cm przy 2.44 GHz → d = 10 cm: ok. 20 dB, 15 cm: 24 dB, 20 cm: 26 dB, 30 cm: 30 dB (od tego odejmij zyski obu anten: dwie anteny po 5 dBi dają o 10 dB gorzej). W małej obudowie rzeczywista izolacja jest zwykle niższa (sprzężenia przez przewody, GND, obudowę); Silicon Labs (UG103.17) podaje 15–20 dB jako typowe w produktach, a do odbioru 802.15.4 przy −80 dBm obok nadającego z +20 dBm Wi-Fi potrzeba ok. 45 dB — „zwykle nieosiągalne w małych urządzeniach”. Wnioski:
   * **decyzja autora (2026-11-26): obudowa ma być mała, odległość środek–środek anten celowo ok. 10 cm (≈ λ); mniej jest dopuszczalne** — ale nie poniżej ok. 6 cm (≈ λ/2; wg wzoru ok. 16 dB przed odjęciem zysków anten, poniżej tego sprzężenie rośnie gwałtownie); wtedy trzeba zastosować środki z poniższej listy (ustawienie współliniowe, przegroda, niski zysk, rozdzielenie kanałów) i potwierdzić pomiarem; powyżej ok. 30 cm w jednej małej obudowie korzyść jest niewielka;
   * **jak uzyskać 10 cm w małej obudowie — dla wybranych anten FPC (płaskich, 39.6 mm, kabel 10 cm):** naklejone od wewnątrz na przeciwległych ściankach; odległość środków anten = wymiar wewnętrzny między tymi ściankami, czyli obudowa potrzebuje **ok. 10 cm w jednym wymiarze** (np. ok. 10 × 4 × 4 cm — wymiary orientacyjne, do potwierdzenia w CAD); moduły XIAO (21 × 17.8 mm) jeden nad drugim mieszczą się w przekroju ok. 4 × 4 cm, a kabel 10 cm sięga każdej ze ścianek. Dla wariantu z prostymi antenami SMA (dipole) odległość środków ≈ wysokość obudowy H + (L₁ + L₂)/2 (np. H = 5 cm i anteny po 5 cm dają ok. 10 cm);
   * **uwaga:** zasada „współliniowo, czubek do czubka” z poprzedniego punktu dotyczy dipoli, **nie płaskiej anteny FPC** — jej charakterystyka jest nieznana (brak karty producenta), więc dla FPC stosuj przeciwległe ścianki i ewentualnie wzajemnie prostopadłe ułożenie anten, a skuteczność sprawdź pomiarem;
   * **ustawienie:** dipol ma zero promieniowania wzdłuż osi, więc najmniejsze sprzężenie dają anteny **współliniowe, czubek do czubka** (antena hosta pionowo w górę, antena C6 pionowo w dół) — pasuje to do układu modułów „jeden nad drugim”; unikać dwóch anten równoległych obok siebie (największe sprzężenie); ortogonalna polaryzacja (jedna pionowo, druga poziomo) jako druga opcja — efekt niezweryfikowany;
   * **zysk:** im większy zysk anten, tym gorsza wzajemna izolacja (wzór wyżej) — kolejny argument za umiarkowanym zyskiem (2–5 dBi), poza limitem EIRP;
   * izolację można poprawić przegrodą z folii miedzianej / taśmy między antenami (źródło poradnikowe: ponad 40 dB, niezweryfikowane) oraz **rozdzieleniem kanałów**: Wi-Fi na kanale 1 lub 6, Zigbee na kanale 25 (2475 MHz) — odstęp ≥ 50 MHz;
   * pigtaile krótkie, prowadzone osobno i nierównolegle, z dala od przewodów zasilających i zasilacza;
   * **sprawdzenie:** test pakietów Zigbee (RSSI, utrata pakietów) przy jednoczesnym ruchu Wi-Fi hosta (np. iperf) przy odległościach 6 / 10 / 15 cm (przedłużki / różne położenia anten przed zamknięciem projektu obudowy); jeśli przy 10 cm utrata pakietów jest nieistotna, zostajemy przy małej obudowie.
5. **Zaopatrzenie:** wszystkie części ze sklepów **TME, Mouser, Farnell**. Każda część w schemacie KiCad ma pola `Manufacturer`, `MPN`, `TME`, `Mouser`, `Farnell` (LCSC/JLCPCB nie dotyczy — brak PCB). Lista części i stan weryfikacji: [`hardware/kicad/README.md`](hardware/kicad/README.md). Wyjątek wskazany przez autora: zasilacz IKEA (decyzja 7).
6. **Superkondensator na pinie `BAT` hosta (C3, w schemacie):** podtrzymanie zasilania hosta, by przy zaniku napięcia sieci zdążył zapisać stan (NVS, kalibracja BSEC) i zakończyć pracę. Założenia (niezweryfikowane — sprawdzić w schemacie Seeed i karcie układu ładowarki):
   * ładowarka na module XIAO (wg forów SGM40567-4.2; ok. 4.2 V, ok. 110 mA) sama ładuje kondensator do 4.2 V, gdy jest zasilanie z USB; **nie rozładuje się „do zera”, dopóki jest zasilanie**, a po jego utracie jego rozładowanie nie szkodzi superkondensatorowi (w przeciwieństwie do ogniwa LiPo);
   * wymagane napięcie znamionowe **≥ 5 V (najlepiej 5.5 V)**; pojedyncza komórka 2.7 V odpada, dwie w szeregu wymagałyby balansowania;
   * **niski ESR** (szczyty nadawania Wi-Fi ok. 350 mA wg PDF): przy ESR 30 Ω spadek byłby ok. 10 V, więc modele monetowe/„KR/KW” z ESR 15–50 Ω się nie nadają; ESR ≲ 1 Ω daje spadek ≲ 0.35 V;
   * energia: 1 F od 4.2 V do ok. 3.5 V (próg wejściowy regulatora 3.3 V — założenie) = 0.7 C, przy poborze ok. 120 mA ≈ 6 s — wystarczy na zapis stanu i zamknięcie połączeń, **nie** na pracę ciągłą; moduł C6 nie ma wtedy zasilania (jego 5 V pochodzi z pada `5V` hosta, który bez USB nie ma napięcia);
   * kandydat z wyszukiwarki (nie sprawdzony na stronie sklepu): Eaton PB-5R0V105-R (1 F, 5 V, ESR ok. 0.5 Ω; Farnell 2148505 wg adresu strony); alternatywa Kemet FT0H105ZF (1 F, 5.5 V, ESR ok. 3.5 Ω — spadek ok. 1.2 V przy szczycie, do oceny);
   * do sprawdzenia: czy pusty kondensator nie przeciąża przy starcie ładowarki (prąd ładowania dzieli się z obciążeniem, jeśli moduł jest zasilany z węzła BAT) oraz czy XIAO ma zabezpieczenie podnapięciowe na `BAT`.
7. **Zasilacz sieciowy: IKEA SJÖSS 20 W** (nr art. 506.217.28; ok. 15 zł; jedno gniazdo **USB-C**, PD, „do 3.0 A / 20 W”; przewód USB-C **nie** jest w zestawie; temperatura pracy 5–35 °C; napięcia wyjściowego strona IKEA nie podaje). Nie pochodzi z TME/Mouser/Farnell — wyjątek wskazany przez autora. Uwagi:
   * **ROZSTRZYGNIĘTE (2026-11-26, autor): zostaje zasilacz SJÖSS (USB-C) i kupowany jest przewód IKEA USB-C ↔ USB-C — SITTBRUNN 1.0 m: biały nr 906.185.40 lub jasnozielony nr 305.959.85 (ok. 10 zł wg listingu PL; strona IKEA: 3 A, 480 Mb/s, CE; ceny białego w PL nie potwierdzono).** Wariant (b) poniżej (zasilacz z USB-A) odpada, więc pozostaje do sprawdzenia, czy XIAO ma rezystory 5.1 kΩ na CC (zmierzyć 5 V po podłączeniu). Poprzedni zapis niezgodności, zachowany dla historii:
   * ~~**⚠ Niezgodność do rozstrzygnięcia (2026-11-26):** autor wskazał przewód **IKEA SITTBRUNN USB-A → USB-C, liliowy, 1.0 m, 7 zł, nr 605.959.84** (strona IKEA: 3 A, 480 Mb/s, zabezpieczenia nad-/zwarciowe/przegrzaniowe; PD i mocy nie podaje). **Zasilacz SJÖSS ma wyłącznie gniazdo USB-C, więc końcówka USB-A tego przewodu do niego nie wejdzie.** Wybór: (a) przewód **USB-C ↔ USB-C** (np. SITTBRUNN 1 m ok. 10 zł wg wyszukiwarki — strony nie otwierałem), albo (b) zasilacz IKEA z gniazdem **USB-A** (kategoria „Ładowarki USB” na ikea.com/pl) z przewodem 605.959.84. Wariant (b) ma zaletę: źródło USB-A daje 5 V bez wykrywania odbiornika na liniach CC, więc niepewność co do rezystorów CC w XIAO przestaje mieć znaczenie.~~
   * (poprzedni zapis, dla wariantu C ↔ C) **przewód: z IKEA, USB-C ↔ USB-C** (decyzja autora). Na stronie IKEA PL (wyszukiwarka, nie sprawdzone na stronach produktów): SITTBRUNN 1 m ok. 10 zł (USB 2.0, ok. 3 A / 60 W wg ofert Allegro), LILLHULT 60 W 1.5 m 19.99 zł, RUNDHULT 100 W 1.5 m 29.99 zł; do tego zastosowania wystarczy najtańszy i najkrótszy (nr artykułu do przepisania ze strony produktu);
   * źródło PD włączy 5 V dopiero po wykryciu odbiornika przez rezystory 5.1 kΩ na liniach CC. **Autor zakłada, że moduł XIAO je ma** — to prawdopodobne, ale **niepotwierdzone** (sprawdzić w schemacie Seeed albo po prostu zmierzyć 5 V po podłączeniu); jeśli nie, zasilacz nie da napięcia i trzeba dolutować rezystory 5.1 kΩ CC→GND lub użyć adaptera USB-C → 5 V;
   * XIAO nie negocjuje PD, więc zasilacz da domyślne 5 V (na to wskazują ogólne opisy PD, niezweryfikowane na tym egzemplarzu) — zmierzyć napięcie na padzie `5V` przed podłączeniem modułów;
   * zasilacz umieścić **poza obudową** (ciepło i szum impulsowy w pobliżu BME680 i anten).

---

## 2. Schemat Połączeń Kablowych

### A. Połączenie między Modułem 1 (`XIAO ESP32-S3 Plus`) a Modułem 2 (`XIAO ESP32-C6`)
Połączenie realizowane przez **4-liniowy interfejs UART ze sprzętową kontrolą przepływu (RTS/CTS)** w celu eliminacji gubienia ramek protokołu Spinel/NCP podczas operacji zapisu do pamięci Flash lub przerwań Wi-Fi:

| XIAO ESP32-S3 Plus (Host) | XIAO ESP32-C6 (RCP Zigbee) | Funkcja |
| :--- | :--- | :--- |
| **`5V`** (zasilany z USB-C hosta) | **`5V`** (wejście) | 5 V z hosta do modułu C6 (każda płytka ma własny stabilizator 3.3 V); USB-C modułu C6 nie podłączać przy zasilonym hoście |
| **`GND`** | **`GND`** | Wspólna masa sygnałowa i zasilająca |
| **`D6` (`GPIO43` / TX)** | **`D7` (`GPIO17` / RX)** | Dane: Host $\rightarrow$ Koprocesor |
| **`D7` (`GPIO44` / RX)** | **`D6` (`GPIO16` / TX)** | Dane: Koprocesor $\rightarrow$ Host |
| **`D2` (`GPIO3` / RTS)** | **`D3` (`GPIO21` / CTS)** | Sprzętowa kontrola przepływu (Request To Send $\rightarrow$ Clear To Send) |
| **`D3` (`GPIO4` / CTS)** | **`D2` (`GPIO2` / RTS)** | Sprzętowa kontrola przepływu (Clear To Send $\leftarrow$ Request To Send) |

*(Uwaga: Piny RTS/CTS można dowolnie przypisać w macierzy GPIO ESP-IDF; powyższe mapowanie zachowuje wolne piny I2C `D4`/`D5` na S3 oraz piny RF switch `GPIO3`/`GPIO14` na C6).*

### B. Połączenie Modułu Czujnika `BME680 (CJMCU-680)` z `XIAO ESP32-S3 Plus`

| Moduł BME680 | XIAO ESP32-S3 Plus | Uwagi |
| :--- | :--- | :--- |
| **`VCC`** | **`3V3`** | Zasilanie 3.3 V |
| **`GND`** | **`GND`** | Wspólna masa |
| **`SDA`** | **`D4` (`GPIO5`)** | Linia danych I2C |
| **`SCL`** | **`D5` (`GPIO6`)** | Linia zegarowa I2C |
| **`CS`** | **`3V3`** | Wymuszenie trybu I2C |
| **`SDO`** | **`GND`** | Wybór adresu I2C `0x76` (lub `3V3` dla adresu `0x77`) |

---

## 3. Wymagania Funkcjonalne i Priorytetyzacja Komunikacji

1. **Integracja z Amazon Alexa (Lokalnie przez Matter):**
   * Bramka musi rejestrować się w aplikacji Alexa jako **Matter Bridge** (parowanie kodem QR / kodem numerycznym przez BLE).
   * Komunikacja po sparowaniu odbywa się w 100% lokalnie w sieci LAN (Matter-over-Wi-Fi / IPv6 mDNS) bez chmury pośredniczącej.
2. **Hierarchia priorytetów urządzeń i zdarzeń:**
   * **Priorytet Krytyczny / Wysoki (Natychmiastowa reakcja):**
     * **Czujniki zalania / wycieku wody (Zigbee / BLE):** Natychmiastowe przekazanie zmiany stanu (`WaterLeakDetector` / `ContactSensor`) do Alexy w celu uruchomienia alarmu głosowego lub rutyny odcinającej wodę.
     * **Elementy wykonawcze — gniazdka elektryczne, przekaźniki i zawory kulowe (Zigbee; urządzenia Wi-Fi poza zakresem — patrz doprecyzowanie na górze):** Niskie opóźnienie przełączania (`OnOff` cluster) oraz pewne raportowanie stanu zwrotnego.
   * **Priorytet Niski (Odświeżanie okresowe):**
     * **Czujniki BLE — wybór autora (2026-11-26): Xiaomi Mijia `LYWSD03MMC` (temperatura + wilgotność, bateria CR2032).** Ustalenia z przeglądu źródeł (ESPHome, repozytorium pvvx/ATC_MiThermometer, ble_monitor; 2026-11-26):
       * **Firmware fabryczny** nadaje odczyty w reklamach BLE **zaszyfrowanych** (MiBeacon) — potrzebny `bindkey` z konta Mi Home (zmienia się po ponownym sparowaniu); odczyt przez połączenie GATT jest możliwy, ale wolny i energochłonny — nie nadaje się do bramki zbierającej wiele czujników.
       * **Decyzja autora (2026-11-26): w czujnikach zostanie podmieniony firmware na niestandardowy `pvvx/ATC_MiThermometer`** (autor wgra go sam na każdy czujnik; firmware fabryczny i bindkey z Mi Home nie są używane). Opis firmware (wgrywany z przeglądarki przez Web Bluetooth, **bez otwierania obudowy**, z możliwością powrotu do oryginału): od wersji 6.0 reklamuje **wyłącznie w formacie BTHome v2** (otwarty standard), opcjonalnie szyfrowany `bindkey`; skaner hosta wykonuje wtedy tylko pasywny odbiór i prosty parser (temperatura, wilgotność, napięcie/poziom baterii) — bez parowania i bez chmury.
       * **Wersja sprzętowa przy zakupie:** README pvvx odradza LYWSD03MMC **HW B1.5/B1.6 (od 03.2025)** — wysoki pobór prądu; B1.6 ma inny firmware fabryczny i osobną instrukcję pierwszego OTA; do wgrania potrzebny poziom baterii > 40 %. Sprawdzić wersję przed zakupem (naklejka / opis sprzedawcy).
       * **Matter:** każdy czujnik = osobny węzeł mostkowany (Bridged Node) z klastrami Temperature Measurement i Relative Humidity Measurement (typy urządzeń Temperature Sensor 0x0302 i Humidity Sensor 0x0307 — obsługiwane przez Alexę wg dokumentacji Amazon); bateria przez Power Source — obsługa w Alexie niezweryfikowana.
       * **Ryzyko (do pomiaru):** README pvvx ostrzega przed ESP32 jako odbiornikiem reklam BLE przy wielu czujnikach („do not use ESP32xxx”, dyskusja #328, dotyczy narzędzi pvvx); ESPHome używa jednak ESP32 jako pasywnego skanera `xiaomi_ble` / `atc_mithermometer`. Do sprawdzenia na S3 z aktywnym Wi-Fi: odsetek odebranych reklam przy N czujnikach i interwale reklam ustawionym na kilka–kilkadziesiąt sekund.
     * **Czujniki BLE (temperatura, wilgotność, stany baterii):** Pasywne skanowanie z niskim cyklem pracy (*duty cycle*, np. okno skanowania co 10–30 sekund), aby nie obciążać radia 2.4 GHz na module S3.
     * **Czujnik BME680 (temperatura, ciśnienie, wilgotność, IAQ):** Pomiar w trybie `BSEC_SAMPLE_RATE_LP` (co 3 s), raportowanie zmian do Matter Bridge przy przekroczeniu progu histerezy (np. $\Delta T \ge 0.2^\circ\text{C}$, $\Delta \text{IAQ} \ge 10$) lub cyklicznie co 60 s.
3. **Logika oceny potrzeby wietrzenia (BME680 + BSEC):**
   * Wykorzystanie biblioteki **Bosch BSEC** do wyliczania indeksu **IAQ (0–500)**.
   * Wystawienie do Alexy wirtualnego czujnika jakości powietrza (`AirQuality` cluster) oraz pomocniczego czujnika binarnego (np. *„Wymagane wietrzenie”*), który aktywuje się po przekroczeniu progu `IAQ > 150` (z histerezą powrotu `IAQ < 110`).
   * Cykliczny zapis stanu kalibracji BSEC (`bsec_get_state`) do partycji **NVS** we Flashu co 6 godzin, aby zachować dokładność `IAQ Accuracy = 3` po restartach zasilania.

---

## 4. Wytyczne Konstrukcyjne dla Obudowy Drukowanej 3D

Ponieważ obudowa będzie drukowana w technologii FDM/SLA i oparta na gotowych modułach połączonych kablami, projekt mechaniczny (CAD) musi uwzględniać poniższe wymagania:

1. **Separacja termiczna czujnika BME680 (Kluczowe):**
   * Pracujące układy ESP32-S3 i ESP32-C6 rozpraszają łącznie ok. **0.8–1.2 W** ciepła, a sama grzałka płytki MOX w BME680 generuje dodatkowe ~1.5–2°C.
   * **Wymóg:** Nie umieszczać BME680 w głównej komorze z modułami XIAO. Zaprojektować w obudowie **odseparowaną, wysuniętą kieszeń zewnętrzną** (połączoną 4-żyłowym przewodem o długości min. 8–12 cm) z otworami wentylacyjnymi od dołu i po bokach (swobodny przepływ konwekcyjny powietrza) oraz przegrodą termiczną oddzielającą ją od elektroniki głównej.
   * W kodzie BSEC ustawić kompensację offsetu temperatury (`temp_offset = 2.0f`, do ostatecznego skalibrowania po wydrukowaniu obudowy).
2. **Separacja przestrzenna i polaryzacja anten 2.4 GHz:**
   * Obie anteny zewnętrzne (Wi-Fi/BLE oraz Zigbee) pracują w paśmie **2.4 GHz**.
   * **Wymóg:** Wyprowadzić dwa gniazda SMA na przeciwległych ściankach obudowy w odległości **minimum 7–10 cm** od siebie. Zalecany montaż anten pod kątem prostym względem siebie (polaryzacja ortogonalna: jedna pionowo, druga poziomo), aby ograniczyć wzajemne zatykanie odbiorników (*desensitization*).
   * Przewody koncentryczne U.FL $\rightarrow$ SMA prowadzić z dala od przewodów zasilających 5 V i magistrali UART.
3. **Dobór kanałów radiowych (Konfiguracja sieciowa):**
   * Ustawić kanał sieci Zigbee na **kanał 25** (górny skraj pasma 2.4 GHz), natomiast domowy router Wi-Fi ustawić na **kanał 1 lub 6**, aby uniknąć nakładania się widma.
4. **Dostęp serwisowy i montaż modułów:**
   * Zastosować zatrzaskowe lub przykręcane sanki (np. na wtopki mosiężne M2/M2.5) dla obu płytek XIAO, z bezpośrednim dostępem do gniazda **USB-C** modułu XIAO ESP32-S3 Plus (zasilanie + logi/flashowanie) oraz otworem na szpilkę do przycisków `BOOT` / `RESET`.
   * Wyprowadzić na front obudowy dyfuzor (np. z transparentnego PETG) dla diody LED statusu sieci i parowania Matter.
   * Materiał wydruku: **PETG** lub **ASA/ABS** (wyższa odporność termiczna niż PLA w okolicach stabilizatorów napięcia).

---

## 4A. Środowisko Budowania — ochrona toolchaina projektu `wireless-esp8266-dap` (wymaganie autora, 2026-11-26)

**Zasada:** instalacja narzędzi dla tej bramki **nie może uszkodzić ani zmienić** toolchaina starego projektu `wireless-esp8266-dap`, który ma się **nadal budować** tak jak dotąd. Jeśli ta bramka potrzebuje innego toolchaina (ESP-IDF z obsługą ESP32-C6, esp-matter, esp-zigbee-sdk), jest on **dokładany osobno, obok**, a nie w miejsce istniejącego. Oba projekty muszą dać się zbudować na tym samym komputerze bez przełączania i bez naprawiania środowiska.

**Toolchain starego projektu (stan zweryfikowany 2026-11-26, nie zmieniać):**
* ESP-IDF **v4.4.2** w WSL: `~/esp/esp-idf-v4.4.2` (ESP32, ESP32-C3, ESP32-S3; **bez** ESP32-C6); środowisko Pythona `~/.espressif/python_env/idf4.4_py3.10_env` (Python **3.10**, cmake 3.28.4 z tego środowiska);
* kompilatory z generacji IDF 4.4.2 w `~/.espressif/tools/`: `riscv32-esp-elf`, `xtensa-esp32-elf`, `xtensa-esp32s3-elf` (wersja esp-2021r2-patch3-8.4.0), `openocd-esp32` 0.11.0;
* pomocnicze: shim `~/idf_python_shim` (`python3` → `python3.10`), `~/esptool` (v4.6.2), katalogi robocze `~/wireless_dap` i `~/build_wireless_dap`, skrypt `~/idf_env_dump.sh`;
* ESP8266: `ESP8266_RTOS_SDK` (submoduł w repozytorium starego projektu) i kompilator `xtensa-lx106-elf` 1.22.0-100;
* systemowe: Python 3.10.20 (obok domyślnego 3.14), cmake/ninja/gcc z apt.

**Zasady dla tego projektu:**
1. **Nie modyfikować, nie aktualizować i nie usuwać** niczego z powyższej listy (w tym `git checkout`/`git pull` w `~/esp/esp-idf-v4.4.2`, `pip install` do jego środowiska Pythona, ręcznych zmian w `~/.espressif/tools/` dla wersji IDF 4.4.2).
2. **Nowy ESP-IDF, esp-matter i esp-zigbee-sdk — w osobnych katalogach:** `~/esp/esp-idf-<tag>`, `~/esp/esp-matter`, `~/esp/esp-zigbee-sdk` (nie `~/esp/esp-idf` z niezatagowanego checkoutu — nie nadaje się do produktu).
3. **Osobny `IDF_TOOLS_PATH` dla nowego IDF** (np. `~/.espressif-gateway`), żeby `install.sh` nowego IDF nie dotykał `~/.espressif` starego projektu. Środowiska Pythona nowego IDF mają własne nazwy (`idf<wersja>_py<wersja>_env`) i nie zastępują `idf4.4_py3.10_env`.
4. **Niczego nie ustawiać globalnie:** żadnych `IDF_PATH`, `IDF_TOOLS_PATH`, `PATH` z `export.sh` w `~/.bashrc`, `~/.profile` ani `/etc`; `export.sh` wywoływać wyłącznie w podpowłoce skryptu budującego (`scripts/wsl_idf.sh`). Nie zmieniać domyślnego `python3`, systemowego cmake ani nie używać `update-alternatives` dla narzędzi używanych przez stary projekt.
5. **Wspólne narzędzia o innej wersji** (Python, cmake, esptool) — instalować w osobnym venv lub prefiksie, nie zastępować wersji systemowej ani tej ze starego projektu. `esptool` 5.3.1 na Windows służy do flashowania i zostaje; stary projekt używa `~/esptool` v4.6.2.
6. **Katalogi robocze rozdzielone:** ta bramka buduje w `~/work/src/<nazwa>` i `~/work/build/<nazwa>/<idf>-<cel>` (kopia przez `rsync`, bo ścieżka w OneDrive ma spacje i przecinek); stary projekt zostaje przy `~/wireless_dap` i `~/build_wireless_dap`. Skrypty tego projektu nie piszą poza `~/work` i katalogami nowego IDF.
7. **Nie aktualizować systemu bez sprawdzenia:** `apt remove/upgrade` pakietów `python3.10`, `cmake`, `ninja-build`, `gcc` oraz zmiana wydania Ubuntu mogą uszkodzić środowisko IDF 4.4.2 (tak działają nieaktualne środowiska Pythona po aktualizacji Pythona w systemie) — po takiej zmianie najpierw zbudować stary projekt.
8. **Test akceptacji (obowiązkowy przed i po każdej zmianie środowiska):**
   * przed pierwszą instalacją zapisać stan wyjściowy: lista `~/.espressif/tools/*/*`, `git describe` w `~/esp/esp-idf-v4.4.2`, `pip freeze` środowiska `idf4.4_py3.10_env`, wersje `python3.10`, `cmake`, `ninja`;
   * po zmianie porównać ze stanem wyjściowym (musi być identyczny w części starego projektu);
   * zbudować stary projekt (`build.bat --build` w `wireless-esp8266-dap`, cel `esp32c3`) i potwierdzić sukces budowy; wynik z datą wpisać do `tests/TEST_RESULTS.md`.
9. **Wzorzec w razie wątpliwości — stary projekt (decyzja autora, 2026-11-26):** `GitHub\wireless-esp8266-dap` działa i poprawnie się kompiluje, więc jest **sprawdzonym wzorcem**. Przy każdej wątpliwości dotyczącej budowania, środowiska, skryptów, łączenia plików binarnych, konfiguracji `sdkconfig.defaults`, CI lub flashowania **najpierw sprawdź, jak zrobiono to tam** (`build_WSL.py`, `build.bat`, `.github/workflows/main.yml`, `CMakeLists.txt`, `sdkconfig.defaults.*`, `docs/build_wsl.md`, `detect_port.py`, `flash_*.bat`) i zacznij od tego rozwiązania; odstąp od niego tylko z powodem (np. brak obsługi ESP32-C6 w IDF 4.4.2) i zapisz ten powód. **Dostęp tylko do odczytu: w tamtym projekcie niczego nie zmieniać** — żadnych edycji plików, `git checkout/pull/commit`, budowania w jego katalogu ani uruchamiania jego skryptów, które zapisują (np. `build_WSL.py` zapisuje do `~/wireless_dap` i `~/build_wireless_dap`; uruchamia go tylko autor lub test akceptacji z pkt 8). Czytanie plików i `git log/status/diff` jest dozwolone.
10. **Rozbieżność, o której wiadomo:** w starym projekcie Docker (`espressif/idf:v5.3.2`, bootloader pod 0x1000) jest niezgodny z CI i `build_WSL.py` (IDF 4.4.2, bootloader pod 0x0 dla C3/S3). Ten projekt go nie używa i go nie zmienia.

Szczegóły środowiska: [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md); decyzja o wersji IDF i esp-matter: `docs/OPEN_QUESTIONS.md` §1.

---

## 5. Struktura Repozytorium i Licencja

* `firmware/host-esp32s3/` *(planowane)* — aplikacja główna na XIAO ESP32-S3 Plus (Matter Bridge, Zigbee host, skaner BLE, BME680 + BSEC).
* `firmware/rcp-esp32c6/` *(planowane)* — firmware koprocesora radiowego 802.15.4 RCP na XIAO ESP32-C6 z obsługą przełącznika antenowego U.FL.
* `firmware/common/` — czysta logika w C (bez ESP-IDF), testowana jednostkowo.
* `hardware/kicad/`, `hardware/enclosure-3d/` *(planowane)* — projekt KiCad oraz obudowa 3D (STL/STEP) z komorą termiczną dla BME680.
* `docs/`, `scripts/`, `tests/` — dokumentacja, skrypty pomocnicze, testy. Indeks: [`AGENTS.md`](AGENTS.md) §7.

**Licencja:** README zakładało MIT, ale plik `LICENSE` to GPL-3.0 — **do rozstrzygnięcia przez autora**. Biblioteka Bosch BSEC jest zamknięta (binarna, własne warunki redystrybucji); `esp-matter` / `esp-idf` mają własne licencje.

---

## 6. Katalog Repozytoriów GitHub i Dokumentacji Referencyjnej

### A. Repozytoria przeanalizowane na etapie koncepcji (wskazane przez autora)
* **[`automatous-io/shelly-1-gen4-matter-thread`](https://github.com/automatous-io/shelly-1-gen4-matter-thread)**  
  *Rola w analizie:* Przykład urządzenia końcowego (*End Device*) na ESP32-C6 działającego jako Matter-over-Thread (wyłącza Wi-Fi i Zigbee; używa BLE wyłącznie do parowania). Potwierdza konieczność odseparowania roli urządzenia końcowego od bramki wieloprotokołowej.
* **[`automatous-io/shelly-gen4-esphome`](https://github.com/automatous-io/shelly-gen4-esphome)**  
  *Rola w analizie:* Konfiguracja ESPHome dla układów ESP32-C6 po Wi-Fi. Wskazuje na brak natywnego wsparcia ESPHome dla jednoczesnej koordynacji Zigbee i bezpośredniego mostkowania Matter do Alexy bez serwera Home Assistant.
* **[`firsttris/esp32c6-zigbee-router`](https://github.com/firsttris/esp32c6-zigbee-router)**  
  *Rola w analizie:* Konfiguracja XIAO ESP32-C6 jako routera Zigbee 3.0. Pokazuje konieczność wyłączenia radia Wi-Fi podczas dedykowanej pracy w sieci 802.15.4 oraz sposób obsługi przełącznika antenowego U.FL na XIAO ESP32-C6.
* **[`firsttris/esp32c6-thread-router`](https://github.com/firsttris/esp32c6-thread-router)**  
  *Rola w analizie:* Analogiczna implementacja routera 802.15.4 (Thread FTD) na XIAO ESP32-C6 potwierdzająca rozdzielenie stosów radiowych.
* **[`RolandWa/wireless-esp8266-dap`](https://github.com/RolandWa/wireless-esp8266-dap)**  
  *Rola w analizie:* Własne repozytorium autora (bezprzewodowy debugger CMSIS-DAP po Wi-Fi TCP/UDP). Punkt odniesienia dla warsztatu programistycznego i narzędzi debugowania.

### B. Kluczowe repozytoria bazowe do budowy docelowego firmware'u
1. **[`espressif/esp-matter`](https://github.com/espressif/esp-matter)** (w szczególności przykład **`examples/bridge_apps/zigbee_bridge`** — ścieżka sprawdzona 2026-11-26; wcześniejszy zapis `examples/zigbee_bridge` jest nieaktualny; README tego przykładu opisuje RCP na ESP32-H2, nie na C6)  
   * *Dlaczego kluczowe:* Oficjalne SDK Espressif dla protokołu Matter. Zawiera gotową architekturę dwuukładowego mostu **Zigbee $\rightarrow$ Matter Bridge** (Host na ESP32-S3 + koprocesor radiowy 802.15.4 RCP po UART). Stanowi główną bazę kodową do rozbudowy o skaner BLE oraz klaster czujnika BME680.
2. **[`espressif/esp-zigbee-sdk`](https://github.com/espressif/esp-zigbee-sdk)**  
   * *Dlaczego kluczowe:* Oficjalny stos Zigbee (ZBOSS) dla układów Espressif. Zawiera definicje klastrów ZCL (gniazdka `On/Off`, zawory, czujniki zalania `IAS Zone`) oraz przykłady konfiguracji koprocesora radiowego (`esp_zigbee_rcp`).
3. **[`espressif/esp-idf`](https://github.com/espressif/esp-idf)** (przykład **`examples/openthread/ot_rcp`**)  
   * *Dlaczego kluczowe:* Bazowy framework systemowy (FreeRTOS, sterowniki UART z RTS/CTS, stos NimBLE dla Bluetooth LE, I2C, pamięć NVS) oraz źródło firmware'u koprocesora radiowego 802.15.4 wgrywanego na XIAO ESP32-C6.
4. **[`boschsensortec/Bosch-BSEC2-Library`](https://github.com/boschsensortec/Bosch-BSEC2-Library)** (oraz **[`boschsensortec/BME68x_SensorAPI`](https://github.com/boschsensortec/BME68x_SensorAPI)**)  
   * *Dlaczego kluczowe:* Oficjalna biblioteka algorytmów firmy Bosch do przeliczania surowych danych z czujnika BME680 na indeks jakości powietrza **IAQ** (wykrywanie potrzeby wietrzenia) oraz kompensacji temperatury i wilgotności.
5. **[`arendst/Tasmota`](https://github.com/arendst/Tasmota)** (moduły `Zigbee2Tasmota` + `Matter Bridge`)  
   * *Dlaczego kluczowe:* Alternatywny punkt odniesienia pokazujący praktyczne mapowanie encji Zigbee oraz czujników BLE na standardowe punkty końcowe (*endpoints*) protokołu Matter Bridge.

### C. Dokumentacja sprzętowa (Datasheety i Wiki)
* **Seeed Studio XIAO ESP32-S3 Plus Wiki:** [wiki.seeedstudio.com/xiao_esp32s3_getting_started](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/) (pinout, konfiguracja PSRAM/Flash, schemat zasilania).
* **Seeed Studio XIAO ESP32-C6 Wiki (sekcja RF Switch U.FL):** [wiki.seeedstudio.com/xiao_esp32c6_getting_started](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/) (sterowanie `GPIO3` i `GPIO14` dla anteny zewnętrznej).
* **Espressif Matter Bridge Guide:** [docs.espressif.com/projects/esp-matter](https://docs.espressif.com/projects/esp-matter/en/latest/esp32s3/) (konfiguracja środowiska budowania i parowania z Amazon Alexa).