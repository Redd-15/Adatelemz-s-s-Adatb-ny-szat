# Féléves feladat – munkadokumentáció

Formula Student versenyautó hajtáslánc- és akkumulátor-telemetriájának elemzése.
Ez a fájl lépésenként rögzíti a döntéseket, a mért számokat és az indoklásokat; a PDF-jelentés ebből készül.

A Beadando mappában vannak a CSV-k, ez a dokumentáció és a közös modul (`hajtaslanc_kozos.py`); minden fázis kódja és ábrái a saját almappájában. Minden script a saját sorszámával egy CSV-t ment a Beadando mappába.

**A beadandó jelentés:** `Jelentes_FS_hajtaslanc_telemetria.docx` (14 oldal, 10 ábra, 11 táblázat; a nyilvános adatforrás linkje sárga helyőrzővel jelölve, kitöltendő). Ez a munkadokumentáció a jelentés részletes háttéranyaga.

**A bemutató:** `Prezentacio_FS_hajtaslanc_telemetria.pptx` (13 dia, 10–15 perc, a csapat sablonjának stílusában; címszavak és ábrák, minden diához előadói jegyzet).

| Mappa / script | Kimenet (CSV a Beadando-ban, ábrák a mappában) | Tartalom |
|---|---|---|
| `00_blf_konvertalas/00_blf_konvertalas.py` | `00_hajtaslanc_nyers.csv` | BLF → CSV dekódolás (nyers, tisztítatlan) |
| `01_tisztitas/01_tisztitas.py` | `01_hajtaslanc_tisztitott.csv` + 3 ábra | adattisztítás, -előkészítés, inverterhiba-jelölés |
| `02_feltaro_elemzes/02_feltaro_elemzes.py` | `02_leiro_statisztika.csv` + 4 ábra | feltáró elemzés (egy- és kétváltozós) |
| `03_hipotezisek/03_hipotezisek.py` | `03_futamok.csv` + 2 ábra | H1 (inverter-melegedés), H2 (belső ellenállás) |
| `04_inverter_homodell/04_inverter_homodell.py` | `04_homodell_elorejelzes.csv` + 3 ábra | inverter-hőmodell (fő: tényleges nyomaték), lekapcsolásig hátralévő idő |
| `05_klaszterezes/05_klaszterezes.py` | `05_klaszterek.csv` + 5 ábra | üzemállapotok: K-közép és fuzzy C-means |
| `hajtaslanc_kozos.py` | – | közös útvonalak, színek, formázás, futamok, inverterhiba-jelölés |

Futtatás a Beadando mappából (bármely munkakönyvtárból is működik), sorrendben:
```
python 00_blf_konvertalas/00_blf_konvertalas.py
python 01_tisztitas/01_tisztitas.py
python 02_feltaro_elemzes/02_feltaro_elemzes.py
python 03_hipotezisek/03_hipotezisek.py
python 04_inverter_homodell/04_inverter_homodell.py
python 05_klaszterezes/05_klaszterezes.py
```
A klaszterezés új adatához a 00-s és a 01-es script egy másik mérésen is lefut, ugyanazokkal a lépésekkel (a 04 és 05 előtt):
```
python 00_blf_konvertalas/00_blf_konvertalas.py --fajlok "2026-08-28 12.59.30.154699.blf" --kimenet 00_hajtaslanc_uj_nyers.csv
python 01_tisztitas/01_tisztitas.py --bemenet 00_hajtaslanc_uj_nyers.csv --kimenet 01_hajtaslanc_uj_tisztitott.csv
```
Környezet: Python 3.13, python-can 4.6.1, cantools 45.2.0, pandas 3.1.1, numpy 2.2.5, scipy 1.15.2, matplotlib 3.10.1, scikit-learn 1.9.1, scikit-fuzzy 0.5.0.

---

## 0. Adatforrás és konvertálás

### Nyers adatok

- **Forrás:** a csapat autójának CAN FD hálózatáról rögzített nyers napló egy 2026. augusztus 28-i tesztnapról, 14 db Vector BLF fájl (`BaseData/`).
- **Jelleírás:** a DBC fájl, amely megadja, hogy melyik CAN-azonosító melyik jelet hordozza, milyen bitpozíción, skálázással és mértékegységgel.
- **Rendszerek a buszon:** MPCU (fővezérlő), AMS (akkumulátor-felügyelet), APPS (gázpedál-szenzor), RSU/FSU (hátsó/első szenzoregység), Dash, Telemetry.

### A DBC-verzió ellenőrzése

Két DBC állt rendelkezésre: `ERMe01_v2_2.dbc` és `ERMe01_v2_4.dbc`. A tesztnap augusztusi, a v2.4 szeptemberi, ezért a **v2.2 az alap**. A két verzió csak két ponton tér el, ezeket a nyers adatokon ellenőriztük:

| Üzenet | v2.2 | v2.4 | Ami a buszon van | Döntés |
|---|---|---|---|---|
| `AMS_AvailableCurrent` (453) | 4 bájt, 2 jel | 10 bájt, 4 jel | 4 bájt | **v2.2** |
| `MPCU_InverterForceRequest.Force` (48) | big-endian, előjel nélküli | little-endian, előjeles | – | **v2.4** |

A `Force` (nyomatékkérés) v2.2 szerinti olvasata értelmetlen. Teljes gáznál 384-et, részgáznál ~35 000-et ad, a gázpedállal való korrelációja r = 0,04. A v2.4 szerinti olvasat teljes gáznál −32767 (= 100%), és monoton követi a pedált (r = 0,97, Spearman ρ = 0,93). Valószínűleg a vezérlő firmware-je már a javított kódolással futott, és ezt a DBC csak később dokumentálta.
→ **Minden üzenetet a v2.2 alapján dekódolunk, kivéve a Force-ot, amelyet a v2.4 alapján.**

Egyéb eltérések a DBC és a busz között (mindkét verzióban; egyik sem érinti a felhasznált jeleket):
- Az `AMS_Temperatures1–5` 64 bájtos (DBC: 48), a `Dash_Status` 8 bájtos (DBC: 1).
- Az `MPCU_Values` ~10 Hz-en érkezik (DBC: 1000 ms).
- `VehicleState = 4` előfordul, de nincs az értéktáblában. Csak azokban a fájlokban jelenik meg, amelyekben `MPCU_Error` üzenet is van, így valószínűleg hibaállapot. A kiválasztott blokkban nem fordul elő.
- A `LemCurrent` a 12 V-os rendszer árama (a csapat tájékoztatása szerint), skálázás nélküli nyers érték, ezért nem vettük fel.

### A mérés kiválasztása

A 14 fájlt közös 10 Hz-es rácsra dekódolva értékeltük. Mozgás: v > 5 km/h. Teljes gáz: gázpedál > 80% legalább 0,5 s-ig.

| Fájl | Hossz [s] | R2D arány | Mozgás [s] | v > 40 km/h [s] | v_max [km/h] | Teljes gáz | RSU/FSU |
|---|---|---|---|---|---|---|---|
| 12.45.12 | 140 | 37% | 0 | 0 | 0 | 3 (álló) | van |
| 12.46.32 | 550* | 14% | 36 | 3 | 48,0 | 2 | van |
| 12.59.30 | 49 | 91% | 37 | 9 | 80,0 | 2 | van |
| 13.04.04 | 66 | 52% | 27 | 4 | 69,0 | 1 | van |
| 13.12.22 | 52 | 94% | 42 | 0 | 31,1 | 0 | van |
| 15.02.10 | 178 | 50% | 97 | 37 | 54,0 | 0 | van |
| 15.07.42 | 158 | 19% | 27 | 9 | **102,9** | 19 (főleg álló pedálteszt) | van |
| 15.13.10 | 35 | 37% | 10 | 6 | 85,5 | 1 | van |
| 15.18.00 | 178 | 28% | 43 | 13 | 88,5 | 4 | van |
| **15.21.59** | 34 | 91% | 27 | 18 | 87,4 | 1 | nincs |
| **15.23.21** | 165 | 25% | 36 | 24 | 86,1 | 4 | nincs |
| **15.29.33** | 241 | 17% | 36 | 26 | 85,0 | 3 | nincs |
| 15.39.08 | 20 | 0% | 0 | 0 | 0 | 0 | nincs |
| **15.39.36** | 219 | 37% | 71 | 49 | 85,6 | 5 | nincs |

\* 136 s-os naplózási kieséssel.

**Választás: a nap utolsó blokkja (15:21–15:43) egyben**, a 15.39.08-as fájl nélkül (abban az autó végig állt). Indoklás:
- Ebben a blokkban van a legtöbb nagy sebességű menet (~120 s 40 km/h felett), legalább 8 gyorsítással 80+ km/h-ig.
- A négy fájl jelkészlete egységes (egyikben sincs RSU/FSU, `MPCU_Error`, sem nem dokumentált állapot).
- A `session` oszlop természetes csoportváltozót ad a hipotézisvizsgálathoz.

A sebesség ~85 km/h körüli plafonja annak a következménye, hogy a motor fordulatszáma aznap ~3000 rpm-re volt korlátozva. A 15.23.21-es naplóban látható a `MaxMotorRpm` 3000 → 3500 → 3000 átállítása.

A munkamenetek közötti SOC-ugrások (92,4% → 84,4% és 82,2% → 76,9%) valószínűleg valósak: az autó a naplózott futamok között is mehetett.

### Konvertálás (`00_blf_konvertalas/`)

1. A keretek dekódolása a DBC alapján, fizikai mértékegységre skálázva.
2. **Közös 10 Hz-es időrács.** Az `AMS_Stat` és az `MPCU_Values` is ~10 Hz-en érkezik. Minden rácspontban a jel legutóbb beérkezett értéke szerepel (mintavétel-tartás), legfeljebb 0,5 s-ig visszamenőleg; régebbi érték esetén a cella üres. Átlagolás helyett ezt választottuk, mert az átlag a hibás kereteket „szétkenné” a szomszédos mintákra.
3. **Aktív szakasz fájlonként:** 5 s-mal az első R2D (Ready-to-Drive) előttől 5 s-mal az utolsó R2D / mozgás utánig.
4. **Nyomaték:** a buszon nincs mért nyomaték, ezért két származtatott oszlop készült.
   - `torque_request_pct = −Force / 32767 · 100`: a vezérlő által kért nyomaték a maximum százalékában.
   - `torque_est_Nm = P_akku / ω_motor`: az elektromos teljesítményből becsült nyomaték, a veszteségeket nem vonja le (felső becslés). Csak 500 rpm felett számoljuk, mert alatta ω → 0 miatt instabil.
5. **Szándékosan nincs tisztítás.** A hibák bent maradnak, ezeket a tisztítási lépés kezeli.

**Eredmény:** `00_hajtaslanc_nyers.csv`, 2170 sor × 27 oszlop. Munkamenetenként: 15:21:59 – 337, 15:23:21 – 462, 15:29:33 – 449, 15:39:36 – 922 sor.

### A nyers CSV oszlopai

| Oszlop | Mértékegység | Forrás (üzenet.jel) | Leírás |
|---|---|---|---|
| `session` | – | fájlnév | a munkamenet kezdőideje |
| `timestamp` | – | fájlnév + BLF idő | abszolút időbélyeg (ms) |
| `t_s` | s | – | idő a munkamenet-ablak elejétől |
| `vehicle_state`, `_name` | – | MPCU_VehicleState.VehicleState | 1 STANDBY, 2 TS_ON, 3 R2D |
| `apps_pct` | % | APPS_NormalData.AppsData | gázpedál-állás (a két szenzor átlaga) |
| `apps1_pct`, `apps2_pct` | % | APPS_NormalData.Apps1/2Interpolated | a két pedálszenzor külön |
| `torque_request_pct` | % | MPCU_InverterForceRequest.Force | nyomatékkérés (származtatott) |
| `torque_est_Nm` | Nm | AMS_Stat.IsaPower, MPCU_Values.MotorRpm | becsült nyomaték (származtatott) |
| `motor_rpm` | 1/min | MPCU_Values.MotorRpm | motor-fordulatszám |
| `speed_kmh` | km/h | MPCU_Values.SpeedKmph | sebesség |
| `batt_current_A` | A | AMS_Stat.IsaCurrent | akkuáram (söntös áramszenzor) |
| `batt_voltage_V` | V | AMS_Stat.IsaVoltage | akkufeszültség (söntös szenzor) |
| `batt_power_W` | W | AMS_Stat.IsaPower | akkuteljesítmény |
| `soc_pct` | % | AMS_Stat.Soc | töltöttség |
| `pack_voltage_V` | V | AMS_Stat.SumVoltage | a cellafeszültségek összege |
| `dc_bus_voltage_V` | V | MPCU_Values.BusVoltage | az inverter DC-köri feszültsége |
| `max_discharge_current_A` | A | AMS_AvailableCurrent.MaxDischargeCurrent | a BMS által engedett max. kisütőáram |
| `cell_v_min/avg/max_V` | V | AMS_Stat.Min/Avg/MaxVoltage | cellafeszültség (110 soros cella) |
| `cell_t_min/avg/max_C` | °C | AMS_Stat.Min/Avg/MaxTemp | cellahőmérséklet |
| `inverter_temp_C` | °C | MPCU_Values.InverterTemperature | inverterhőmérséklet |
| `motor_temp_C` | °C | MPCU_Values.MotorTemperature | motorhőmérséklet |

---

## 1. Adattisztítás és -előkészítés (`01_tisztitas/`)

**Elv:** csak a fizikailag lehetetlen vagy a vizsgálat szempontjából értelmetlen adatot távolítjuk el; a statisztikailag ritka, de valós értékeket megtartjuk.
**Sorrend:** előbb az idősor-szintű műveletek a teljes, folytonos 10 Hz-es soron, mert ezek egyenletes mintavételt feltételeznek. Ezután jön a sorok szűrése, végül az oszlopok rendezése és az ellenőrzés.

### A) Idősor-szintű lépések (munkamenetenként)

**1. Negatív sebesség és fordulatszám → 0.** 1-1 érték (−0,1 km/h, −7 rpm), álló helyzetben. Az autó nem tolat, ezek szenzor-offszetek.
A **negatív akkuáram megmarad** (141 sor, legkisebb −1,56 A). A ±1,5 A a szenzor mérési pontosságán belül van, a 0-ra vágás pozitív irányba torzítaná az eloszlást.

**2. Gyorsulás (`accel_ms2`).** A sebesség különbségéből (Δv/Δt), munkamenetenként, 5 mintás (0,5 s-os) középre igazított mozgóátlaggal.
- A nyers Δv/Δt −15…+17 m/s² (szórás 3,32); ez a 0,1 km/h-s felbontás és a 10 Hz-es mintavétel zaja.
- Simítva −6,1…+7,9 m/s² (szórás 1,91), ami egy FS autótól fizikailag reális.
- Ábra: `01_tisztitas/01_gyorsulas_simitas.png`.

**3. A BMS kisütőáram-korlát hiányzó értékei → előző érték.** 83 hiányzó értékből 82 pótolva. Az 1 maradék a 15:21:59-es munkamenet legelején van, és az 5. lépésben kiesik. Az üzenet ~5 Hz-en érkezik, ezért néha 0,5 s-nál hosszabb a szünet. Az érték lassan változó korlát (175–189 A), így az utolsó ismert érték a legjobb becslés.

### B) Sorszűrés

**4. Fizikailag lehetetlen AMS keretek – 2 sor törölve.** Három független szabály, mindhárom pontosan ugyanazt a 2 sort jelöli:

| Szabály | Jelölt sor |
|---|---|
| \|áram\| > 284 A (1,5 × a BMS max. kisütőárama) | 2 |
| a cellafeszültségekre nem teljesül: min ≤ átlag ≤ max | 2 |
| \|pack − 110 × átlagos cellafeszültség\| > 10 V | 2 |

A cellaszámot (110) az adatból határoztuk meg: a pack/átlag cellafeszültség hányados mediánja 110,0.

| Munkamenet | t_s | Áram | Feszültség | SOC | Pack | Max. cellafesz. |
|---|---|---|---|---|---|---|
| 15:29:33 | 6,8 s | 25 232 A | 25 232 V | 38,4% | 2530 V | 0,039 V |
| 15:39:36 | 69,6 s | 26 542 A | 26 739 V | 40,3% | 2720 V | 0,042 V |

**Ok:** ezekben a keretekben a nyers bájtok cellahőmérséklet-mintázatúak (0x018x = 38,x °C). Az AMS időnként hőmérséklet-csomagot küld az `AMS_Stat` (450) azonosítóval. A sor **minden** akkus értéke hibás (a látszólagos SOC-zuhanás 84 → 38% is ebből jön), ezért a teljes sort töröljük. Ábra: `01_tisztitas/01_hibas_keretek.png`.

**5. Állapotszűrés – 240 sor törölve.**
- **a) Csak az R2D állapot marad.** 232 sor törölve (106 STANDBY, 126 TS_ON); ezekben a hajtáslánc nem ad nyomatékot. Ezzel az első, teljesen üres sor is kiesik.

  | Munkamenet | R2D | STANDBY | TS_ON |
  |---|---|---|---|
  | 15:21:59 | 305 | 1 | 31 |
  | 15:23:21 | 412 | 24 | 26 |
  | 15:29:33 | 398 | 31 | 19 |
  | 15:39:36 | 821 | 50 | 50 |

- **b) Leállási átmenet: 8 sor törölve.** *(A tisztítás közben derült ki, utólag jóváhagyva.)* A 15:39:36-os munkamenet végén (t = 86,4–87,1 s) a nagyfeszültségű rendszer már lekapcsolt: az akkufeszültség 0,2 s alatt 425 V-ról ~0 V-ra esik, az inverter DC-köre 421 V-ról 110 V-ra sül ki. Az állapotjel ennek ellenére még ~0,8 s-ig R2D-t mutat. A csapat értékelése szerint valószínűleg rendszerhiba történt: az akkumulátor (AMS) lekapcsolta a nagyfeszültséget, de a vezérlő állapota R2D-ben maradt. A szabály: R2D-ben az akkufeszültség nem lehet 275 V (110 × 2,5 V) alatt.
- Az **álló R2D sorok megmaradnak** (182 sor, v < 1 km/h): ez valós üzemállapot (menetkész, áll). A klaszterezésnél külön döntünk róluk.

**6. A nyomatékkérés hiányzó értékei → 0.** 18 sor, munkamenetenként 4–6, mindegyik az R2D kezdete utáni első 0,4–0,6 s-ban, a gázpedál ekkor 0–9%. A vezérlő az üzenetet csak R2D-ben küldi, és kicsit késve indul el. Ha nincs üzenet, nincs nyomatékkérés, így a helyes érték 0.
Ezután törlődik minden olyan R2D sor, amelyben más mért érték is hiányzik. A `torque_est_Nm` ebből kivétel, mert 500 rpm alatt definíció szerint üres. A fő adatban ez 0 sort érint. Az új mérésben (12:59:30) 2 sort érint: a napló már menet közben indult, így az első R2D sorban még nem érkezett meg minden üzenet.

**7. Az inverterhiba-szakaszok jelölése: új `inverter_hiba` oszlop, a sorok megmaradnak.** Három esetben az inverter lekapcsolt, és a napló végéig nem kapcsolt vissza; ezt a csapat megerősítette. Ezekben a sorokban az állapot R2D, a pilóta gázt ad, de az akkuáram ≈ 0, és az autó kigurul.
- **Az inverter védelmi határai** (a csapat tájékoztatása): 83 °C felett biztosan lekapcsol; kb. 70 °C-tól a hőmérséklet arányában visszaszabályozza a leadható nyomatékot (ez utóbbi bizonytalan).
- **Felismerés:** a motor forog (> 500 rpm), a kérés ≥ 50%, de az akkuáram ~0-ra esik (< 1 A), és legalább 1 s-ig nem tér vissza. A hiba az áram visszatéréséig, ennek hiányában a munkamenet végéig tart.
  - A kérés felfutásakor az áram csak 0,1–0,2 s késéssel indul; ezek a rövid átmenetek így kimaradnak.
  - Az összes ilyen szakasz vizsgálata egyértelmű elválasztást adott: a hibák 10–21 s-ig tartanak, és az áram nem tér vissza; az átmenetek legfeljebb 0,2 s-osak.
- **A szabály története:** az első változat azt követelte meg, hogy a ≥ 50%-os kérés is tartson ki 1 s-ig. Ez kihagyta a 15:39:36-os lekapcsolást, mert ott a pilóta hamar levette a gázt. A 83 °C-os határról kapott információ után derült ki, hogy ez is lekapcsolás, ezért a szabályt javítottuk.

| Munkamenet | Hiba [s] | Hossz | Sorok | Ebből kérés > 5% | Fordulat a kezdetén | Sebesség | Inverter a hibakor | Valószínű ok |
|---|---|---|---|---|---|---|---|---|
| 15:21:59 | 12,8–33,6 | 20,9 s | 209 | 96 | 3127 rpm | 84 → 30 km/h | 57,2 °C | nem termikus (előtte 3241 rpm-es túllövés) |
| 15:29:33 | 34,8–44,8 | 10,1 s | 101 | 85 | 2267 rpm | 61 → 39 km/h | **84,3 °C** | **termikus (≥ 83 °C)** |
| 15:39:36 | 66,8–86,3 | 19,6 s | 195 | 27 | 2124 rpm | 57 → 0 km/h | **84,2 °C** | **termikus (≥ 83 °C)** |

- **Jelölve 505 sor (26,2%), a működő hajtáslánc 1423 sora marad.** Törlés helyett jelölés: a feltáró elemzés, a hipotézisvizsgálat és a klaszterezés kizárja ezeket a sorokat, mert a hajtáslánc nem működik. A hőmodell viszont hűlési adatként használja őket, mert ilyenkor az inverter terhelés nélkül hűl.

### C) Oszlopok

**8. Redundáns oszlopok törlése (6 oszlop):**
- `apps1_pct`, `apps2_pct`: a két pedálszenzor max. eltérése 4,0%. Ez az FS szabály szerinti 10%-os határ alatt van, tehát nincs érvénytelen jel. Az `apps_pct` a kettő átlaga (max. eltérés 0,05%).
- `dc_bus_voltage_V`: ugyanazt méri, mint a `batt_voltage_V` (r = 0,85, mediánkülönbség −2,3 V), de csak egész V felbontással. Terhelésváltáskor a két üzenet időzítése eltér.
- `pack_voltage_V`: a cellafeszültségek összege (r = 0,99, mediánkülönbség −0,14 V a `batt_voltage_V`-hez képest).
- `vehicle_state`, `vehicle_state_name`: a szűrés után konstans (R2D).

**9. Származtatott oszlopok:**
- `batt_power_kW = batt_power_W / 1000`.
- `torque_est_Nm` újraszámolva a tisztított adatokból. Maximuma 207,3 Nm; a nyers adatban 141 897,7 Nm volt, a hibás keretek miatt.
- `accel_ms2`: lásd a 2. lépést.

### D) Ellenőrzés

- **Hiányzó érték:** csak a `torque_est_Nm`-ben (322 sor), 500 rpm alatt definíció szerint. Nem adathiba, ezért nem pótoljuk.
- **Fizikai tartományok:** minden oszlop a határon belül van.

  | Oszlop | Min | Max | Határ | Forrás |
  |---|---|---|---|---|
  | `apps_pct`, `torque_request_pct` | 0 | 100 | 0…100% | DBC / definíció |
  | `motor_rpm` | 0 | 3241 | 0…10 000 | DBC |
  | `speed_kmh` | 0 | 87,4 | 0…200 | DBC |
  | `accel_ms2` | −6,06 | 7,94 | ±20 m/s² | kb. ±2 g |
  | `batt_current_A` | −1,56 | 108,7 | −5…189 A | BMS-korlát, −5 A: mérési zaj |
  | `batt_voltage_V` | 413,0 | 447,5 | 275…462 V | 110 cella × 2,5…4,2 V |
  | `soc_pct` | 72,9 | 95,5 | 0…100% | definíció |
  | `cell_v_*` | 3,754 | 4,071 | 2,5…4,2 V | Li-ion cella |
  | `cell_t_*` | 36,5 | 42,2 | 0…60 °C | FS szabály |
  | `inverter_temp_C` | 41,3 | 84,3 | 0…100 °C | DBC |
  | `motor_temp_C` | 43,5 | 58,9 | 0…200 °C | DBC |

  Továbbá egyetlen sorban sem haladja meg az áram az adott pillanatban érvényes BMS-korlátot.
- **Statisztikai kiugrók (IQR, 1,5 × IQR), nem töröljük őket:** kiugró csak az `accel_ms2`-ben van (43 db, 2,2%). Ezek a rajtok és az erős lassítások csúcsai, a fizikai határon belül. **A statisztikai kiugró nem azonos a hibával;** a törlésük éppen a legintenzívebb üzemállapotokat vinné el. A többi változó eloszlása olyan széles (pl. az áram 0 és 109 A között), hogy minden érték az 1,5 × IQR-sávon belül marad. Ábra: `01_tisztitas/01_kiugro_vs_hiba.png`.

### Eredmény

`01_hajtaslanc_tisztitott.csv`: **1928 sor × 23 oszlop**. Munkamenetenként: 15:21:59 – 305, 15:23:21 – 412, 15:29:33 – 398, 15:39:36 – 813 sor. Ebből 505 sor `inverter_hiba = True`; **a működő hajtáslánc 1423 sora** a további elemzések alapja (a hőmodell kivételével).

| Lépés | Sorok |
|---|---|
| nyers | 2170 |
| 4. hibás AMS keretek | −2 → 2168 |
| 5a. nem R2D állapot | −232 → 1936 |
| 5b. leállási átmenet | −8 → **1928** |
| 7. inverterhiba (jelölés, nem törlés) | 505 jelölt → 1423 működő |

Oszlopok: `session`, `timestamp`, `t_s`, `inverter_hiba`, `apps_pct`, `torque_request_pct`, `torque_est_Nm`, `motor_rpm`, `speed_kmh`, `accel_ms2`, `batt_current_A`, `batt_voltage_V`, `batt_power_kW`, `soc_pct`, `max_discharge_current_A`, `cell_v_min_V`, `cell_v_avg_V`, `cell_v_max_V`, `cell_t_min_C`, `cell_t_avg_C`, `cell_t_max_C`, `inverter_temp_C`, `motor_temp_C`.

---

## 2. Feltáró adatelemzés (`02_feltaro_elemzes/`)

**Bemenet:** `01_hajtaslanc_tisztitott.csv`. Az `inverter_hiba = True` sorokat (505) kizárjuk, mert ott a hajtáslánc nem működik; **az elemzés 1423 soron fut.**
**Kimenet:** `02_leiro_statisztika.csv`, amely minden numerikus változóra tartalmazza: n, átlag, medián, szórás, min, Q1, Q3, max, IQR, ferdeség, többlet-csúcsosság.

### Egyváltozós elemzés (ábra: `02_feltaro_elemzes/02_egyvaltozos.png`)

| Változó | Átlag | Medián | Szórás | Min | Max | Ferdeség | Csúcsosság |
|---|---|---|---|---|---|---|---|
| sebesség [km/h] | 48,33 | 54,60 | 28,41 | 0,00 | 87,40 | −0,41 | −1,25 |
| gázpedál [%] | 58,80 | 64,10 | 37,98 | 0,00 | 100,00 | −0,22 | −1,54 |
| akkuáram [A] | 31,28 | 32,51 | 25,46 | −1,56 | 108,73 | 0,21 | −1,04 |
| akkuteljesítmény [kW] | 13,25 | 13,86 | 10,80 | −0,73 | 46,83 | 0,22 | −1,00 |
| inverterhőmérséklet [°C] | 65,40 | 66,80 | 12,70 | 41,30 | 84,20 | −0,34 | −1,14 |
| min. cellafeszültség [V] | 3,89 | 3,89 | 0,09 | 3,75 | 4,06 | 0,41 | −0,96 |

- **Sebesség:** balra ferde. 9,7% álló (v < 1 km/h), 25,3% 75 km/h felett. A felső végét a ~3000 rpm-es fordulatszám-korlát 80–87 km/h-nál elvágja.
- **Gázpedál:** kétcsúcsú, U alakú eloszlás (csúcsosság −1,54). 11,9% 5% alatt, 36,0% 95% felett: a pilóta „be-ki” stílusban vezet. Ezért az átlag (58,8%) itt rossz középérték-mutató.
- **Akkuáram:** enyhén jobbra ferde és lapos, két tömörülésből áll.
  - A sorok 21,4%-a 2 A alatt van (gurulás, állás).
  - A 2 A feletti sorok középső fele 22–57 A között van.
  - A ritka, 80 A feletti áramok (1,6%) a teljes gázas rajtok csúcsai.
  - A teljesítmény ugyanilyen alakú, mert a feszültség szűk sávban mozog (P ≈ U·I, r = 0,993).
- **Inverterhőmérséklet:** lapos, kétcsúcsú. Az ok a munkamenetek közötti melegedés: munkamenet-átlagok 47,8 → 51,9 → 73,4 → 73,3 °C.
- **Min. cellafeszültség:** a töltöttség és a terhelés együtt alakítja. Munkamenet-átlagok: 3,99 V / 95% SOC → 3,98 V / 94% → 3,89 V / 83% → 3,82 V / 75%.

### Kétváltozós elemzés

**Áttekintés: Spearman-korrelációs mátrix** (`02_feltaro_elemzes/02_korrelacio.png`, 14 változó). Rangkorrelációt használunk, mert több változó ferde vagy kétcsúcsú, és a kapcsolatok nem mind lineárisak.
- `speed_kmh`–`motor_rpm` ρ = 1,00: a sebességet a vezérlő a fordulatszámból számolja (állandó áttétel, 37,09). A két változó ugyanazt az információt hordozza, a modellezésben csak az egyiket érdemes használni.
- `apps_pct`–`torque_request_pct` ρ = 0,96: a nyomatékkérés a pedálállásból képződik.
- A hőmérsékletek és a SOC/feszültség közötti erős kapcsolatok (pl. SOC–motorhőmérséklet ρ = −0,99) **nem ok-okozatiak**. Mindkét változó az idővel változik, a munkamenet közös háttérváltozó (zavaró tényező).

**(a) Akkuáram ↔ akkufeszültség: feszültségesés, belső ellenállás** (`02_feltaro_elemzes/02_aram_feszultseg.png`)

| | n | átl. SOC | U0 [V] | R [mΩ] | r | R² |
|---|---|---|---|---|---|---|
| összevonva | 1423 | – | 434,6 | 175 | −0,47 | 0,22 |
| 15:21:59 | 96 | 95,3% | 447,8 | 178 | −0,99 | 0,99 |
| 15:23:21 | 412 | 93,8% | 444,1 | 183 | −0,88 | 0,78 |
| 15:29:33 | 297 | 83,5% | 433,7 | 172 | −0,77 | 0,59 |
| 15:39:36 | 618 | 75,0% | 426,2 | 159 | −0,81 | 0,66 |
| **közös modell** (munkamenetenként külön U0) | 1423 | – | – | **171** | – | **0,92** |

Az összevont Spearman ρ = −0,44. Minden p < 10⁻⁵⁰.
**Értelmezés:**
- Munkameneten belül az áram szorosan, lineárisan meghatározza a feszültséget. A meredekség az akkumulátor belső ellenállása: ~171 mΩ, azaz 110 cellára ~1,55 mΩ/cella.
- Összevonva a kapcsolat jóval gyengébbnek látszik, mert a munkamenetek eltérő töltöttségről indulnak (U0 426–448 V).
- A munkamenet itt zavaró tényező (Simpson-paradoxon jellegű hatás). Ha figyelembe vesszük, a magyarázott variancia 22%-ról 92%-ra nő.

**(b) Fordulatszám ↔ becsült nyomaték teljes gáznál** (`02_feltaro_elemzes/02_nyomatek_fordulat.png`)
- Teljes gáznál (pedál > 95%, 512 sor) 16 sorban (3,1%) a kérés 0%: ezek rövid, 0,1–0,4 s-os nyomatékmegvonások. Az okuk a meglévő jelekből nem azonosítható (fékjel ebben a blokkban nincs). Ezért az elemzés a **≥ 99%-os nyomatékkérésű** sorokra szűkül (465 sor 500 rpm felett).
- Ebből 4 sorban az áram ≈ 0. Ezek rövid átmenetek: a kérés felfutása után az áram késve követi. A mediángörbe a teljesítményt leadó 461 sorból készül.
- **Eredmény:** Spearman ρ = −0,78 (p < 10⁻⁹⁰).

  | rpm-sáv | n | nyomaték mediánja [Nm] | teljesítmény mediánja [kW] |
  |---|---|---|---|
  | 500–1000 | 8 | 186–203 | 14–16 |
  | 1000–1500 | 68 | 113–119 | 14–16 |
  | 1500–2000 | 63 | 105–137 | 19–27 |
  | 2000–2500 | 62 | 94–99 | 22–23 |
  | 2500–3000 | 193 | 79–87 | 24 |
  | 3000–3250 | 67 | 62,5 | 20,2 |

- **Értelmezés:** a kérés végig 100%, a nyomaték mégis csökken a fordulattal.
  - 1000 és 3000 rpm között a csökkenés közel hiperbolikus, ~14–27 kW közel állandó akkuteljesítmény mellett. Itt tehát nem a kérés, hanem a hajtáslánc rendelkezésre álló teljesítménye korlátoz (lásd még a 4. lépés teljesítmény–hőmérséklet kiegészítését).
  - 3000 rpm felett a medián tovább esik (24 → 20 kW, 79 → 62,5 Nm). **Ez futamonként nem igazolódik.** Csak 3 teljes kérésű futam tölt legalább 0,3 s-ot a korlát alatt (2500–3000 rpm) és felett is. Ezekben a teljesítmény 38,2 → 41,1, 18,9 → 14,4, illetve 26,0 → 26,6 kW, tehát csak egyben csökken. A mediáncsökkenés részben összetételi hatás. A korlát hatása így nem igazolható egyértelműen.
  - Szembetűnő, hogy a 15:21:59-es munkamenetben a 3241 rpm-es túllövés után közvetlenül következett az egyik (nem termikus) inverterhiba.
  - A `torque_est_Nm` felső becslés, mert az elektromos teljesítményből számoljuk, és a veszteségeket nem vonja le. 1000 rpm alatt kevés a pont (n = 8).

### Módszertani megjegyzés: autokorreláció

A 10 Hz-es sorok nem függetlenek. Az akkuteljesítmény autokorrelációja 1 s eltolásnál 0,73, 3 s-nál 0,33; az inverterhőmérsékleté 3 s-nál is 0,83. Soronkénti statisztikai próbánál ezért a p-értékek irreálisan kicsik lennének (pszeudo-replikáció). A hipotézisvizsgálat egysége ezért a gyorsító futam.

---

## 3. Hipotézisvizsgálat (`03_hipotezisek/`)

### Megfigyelési egység: a gyorsító futam

A **gyorsító futam** összefüggő szakasz, ahol a nyomatékkérés > 5%, legalább 2 s hosszú, és a hajtáslánc legalább 5 kJ energiát ad le. Az inverterhiba-sorok kizárva. Így **17 futam** adódik (munkamenetenként 2, 4, 3, 8), 2,2–13,2 s hosszúak. A futamtábla: `03_futamok.csv`.

- A hibajelölés pontosította a futamokat. A 2., a 9. és a 17. futam korábban belelógott egy-egy inverterhiba kezdetébe: a kérés még tartott, de az inverter már lekapcsolt. Most a futam a hiba kezdeténél véget ér. A 17. futam a termikus lekapcsolásnál, 84,1 °C-on ér véget.
- A futam eleji és végi hőmérséklet az első, illetve utolsó 3 minta (0,3 s) átlaga; ez csökkenti a 0,1 °C-os kvantálás zaját.
- Belső ellenállás futamonként: az U = U0 − R·I regresszió meredeksége, csak a legalább 30 A áramtartományt bejáró futamokból (16 / 17). Az illesztések r értéke −1,00…−0,88.
- α = 0,05.

### H1: melegszik-e az inverter egy gyorsító futam alatt? (`03_hipotezisek/03_h1_inverter.png`)

- **Hipotézisek:** d = T_vég − T_kezdet; H0: μ_d = 0; H1: μ_d > 0 (egyoldali, mert fizikailag melegedés várható).
- **Feltétel:** a különbségek normalitása, Shapiro–Wilk W = 0,939, p = 0,307 → a normalitást nem vetjük el, a páros t-próba alkalmazható.
- **Páros t-próba:** t(16) = 5,37, egyoldali p = 3,1·10⁻⁵ (kétoldali p = 6,3·10⁻⁵).
  - Átlagos melegedés **5,16 °C**, 95%-os CI [3,13; 7,20] °C, egyoldali alsó korlát 3,49 °C. Medián 5,87 °C, szórás 3,97 °C.
  - Hatásméret Cohen d_z = 1,30 (nagy).
- **Robusztusság:** Wilcoxon-féle előjeles rangpróba W = 153, p = 7,6·10⁻⁶.
- **Döntés:** H0-t elvetjük. Egy gyorsító futam alatt az inverter hőmérséklete szignifikánsan nő.
- **Mitől függ a melegedés** (Spearman):
  - nyomatékkérés-integrál: ρ = 0,62, p = 0,008 (szignifikáns);
  - leadott energia: ρ = 0,59, p = 0,013 (szignifikáns);
  - kezdő hőmérséklet: ρ = −0,44, p = 0,078 (nem szignifikáns).

  A futamszintű korrelációk csak közepesek, mert a melegedést a terhelés és a kezdő hőmérséklet együtt határozza meg. Melegebb inverterről indulva nagyobb a hűlés. Ezt a 4. lépés hőmodellje írja le.

### H2: eltér-e a belső ellenállás magas és alacsonyabb töltöttségnél? (`03_hipotezisek/03_h2_belso_ellenallas.png`)

- **Hipotézisek:** H0: μ_magas = μ_alacsony; H1: μ_magas ≠ μ_alacsony (kétoldali). A csoportok a futam átlagos SOC-ja alapján képződnek: ≥ 90% vs. < 90%, a munkamenetek között itt természetes rés van.

  | Csoport | n | SOC | Átlagos R | Szórás | Medián | Cellahőmérséklet |
  |---|---|---|---|---|---|---|
  | magas SOC | 6 | 93–95% | 158,8 mΩ | 24,5 | 152,2 | 37,6 °C |
  | alacsonyabb SOC | 10 | 73–84% | 145,5 mΩ | 37,8 | 136,9 | 40,3 °C |

- **Feltételek:** normalitás csoportonként Shapiro–Wilk p = 0,450 és p = 0,253. Szóráshomogenitás Levene p = 0,480; a Welch-próba ezt amúgy sem igényli.
- **Welch-féle t-próba:** t(13,8) = 0,86, **p = 0,405**. A különbség 13,4 mΩ, 95%-os CI [−20,1; 46,8] mΩ. Hedges g = 0,38.
- **Robusztusság:** Mann–Whitney U = 41, p = 0,263.
- **Döntés:** H0-t nem vetjük el, a belső ellenállás átlaga a két csoportban nem tér el szignifikánsan. Ez nem bizonyítja az egyenlőséget: kicsi a minta, és a CI −20…+47 mΩ-os eltérést sem zár ki.
- **Kiegészítő, folytonos elemzés (Spearman):** R–SOC ρ = 0,45, p = 0,08, ez sem szignifikáns.
- **Értelmezés:**
  - A SOC és a cellahőmérséklet futamszinten teljesen együtt mozog (ρ = −1,00): a későbbi futamokban a cellák ~2,7 °C-kal melegebbek.
  - Az alacsonyabb SOC általában növeli, a melegebb cella csökkenti a belső ellenállást. A két hatás részben kiolthatja egymást, és ebből az adatból nem választhatók szét.

---

## 4. Az inverter melegedésének előrejelzése (`04_inverter_homodell/`)

A csapat kérdése: adott nyomatékkérés mennyivel melegíti az invertert, és hogyan alakul a hőmérséklet?

### Modell

**Elsőrendű hőmodell:** a hőtermelés arányos a terheléssel, a hűlés newtoni:

  dT/dt = α·u − β·(T − T∞)

- **Fő modell (a csapat döntése alapján):** u = a ténylegesen leadott, becsült nyomaték / 100 Nm. Ez a `torque_est_Nm`; 500 rpm alatt P/ω-val, 500 rpm-mel számolva. Fizikailag ez a reális bemenet, mert az inverter vesztesége a ténylegesen folyó áramtól függ.
- **Összehasonlító modell:** u = a nyomatékkérés (0…1).
- **Mindkét bemenet 0, ahol az inverter nem ad áramot** (akkuáram < 1 A vagy `inverter_hiba`), összesen 766 sor, ebből 505 inverterhiba. Ezek hűlési adatként bent maradnak.
- **Becslés:** legkisebb négyzetek 1 s-os ablakokon (1868 ablak), a tisztításkor törölt sorok résén átnyúló ablakok nélkül.
- **Modellválasztás:**
  - Késleltetés: a kérés és a melegedés kapcsolata 0 s eltolásnál a legerősebb (r = 0,59), ezért nincs holtidő a modellben.
  - A négyzetes nyomaték-bemenet rosszabb volt: munkamenet-szintű hiba 6,8 °C a lineáris 4,4 °C-ával szemben.
- **Az inverter védelmi határai** (a csapat tájékoztatása): **83 °C felett biztosan lekapcsol**; kb. 70 °C-tól a hőmérséklet arányában visszaszabályozza a nyomatékot (bizonytalan). A modell e határok felett már nem érvényes.

| Modell | α | τ = 1/β | T∞ |
|---|---|---|---|
| **tényleges nyomaték (fő)** | **1,86 °C/s 100 Nm-enként** | **63 s** | **25,2 °C** |
| nyomatékkérés (összehasonlítás) | 1,68 °C/s 100%-os kérésnél | 50 s | 44,5 °C |

- **α:** 100 Nm leadott nyomatéknál az inverter kezdetben ~1,9 °C/s sebességgel melegszik, 200 Nm-nél kétszer ennyivel.
- **τ:** terhelés nélkül a T∞ feletti többlet 44 s alatt feleződik.
- **T∞:** a terhelés nélküli egyensúly (≈ hűtőközeg / környezet). A fő modell értéke (25 °C) fizikailag hihetőbb, mint a kérés-modellé.
- **Érvényesség:** rövid, néhány 10 s-os terhelésekre érvényes. A mért tartomány 41–84 °C és legfeljebb 13,2 s-os futam.

### Validáció (`04_inverter_homodell/04_homodell_validacio.png`)

**Leave-one-session-out:** 3 munkameneten illesztünk, a 4.-et a kezdő hőmérsékletéből és a mért bemenetből szimuláljuk.

| Kihagyott munkamenet | α [°C/s/100 Nm] | τ [s] | T∞ [°C] | RMSE nyomaték-modell | RMSE kérés-modell | RMSE alapmodell* |
|---|---|---|---|---|---|---|
| 15:21:59 | 1,81 | 61,8 | 28,7 | 3,61 °C | 4,53 °C | 6,85 °C |
| 15:23:21 | 1,88 | 53,8 | 34,1 | 4,34 °C | 4,61 °C | 12,07 °C |
| 15:29:33 | 1,86 | 71,3 | 19,8 | 2,83 °C | 7,93 °C | 13,40 °C |
| 15:39:36 | 1,92 | 47,3 | 27,9 | 6,88 °C | 3,11 °C | 17,54 °C |
| **átlag** | | | | **4,42 °C** | 5,05 °C | 12,47 °C |

\* alapmodell: a hőmérséklet változatlan marad a munkamenet kezdő értékén.

**Futamszintű melegedés, jósolt vs. mért** (LOSO, 17 futam):

| Modell | r | p | Átlagos abszolút hiba |
|---|---|---|---|
| **tényleges nyomaték (fő)** | **0,84** | < 0,001 | **1,59 °C** |
| nyomatékkérés | 0,43 | 0,088 | 3,29 °C |
| viszonyítás: mindig az átlagos melegedés | – | – | 3,26 °C |

**Értelmezés:**
- A fő modell a futamok melegedését jól jósolja, és a hőmérséklet lefutását munkamenet-szinten is követi. A változatlan hőmérséklethez képest a hiba ~35%-ára csökken (12,5 → 4,4 °C).
- Az α paraméter a kihagyott munkamenettől függetlenül stabil (1,81–1,92).
- **A kérés gyenge előrejelző**, futamszinten nem jobb a puszta átlagnál. Ennek oka, hogy magas fordulaton a teljesítménykorlát miatt 100%-os kérés mellett is kevesebb nyomaték (és hő) keletkezik.
- **Korlátok:**
  - A terhelés utáni hűlés az első másodpercekben gyorsabb, mint amit a modell jósol. Ez több időállandós rendszerre utal: gyors félvezető–hűtőborda és lassú hűtőközeg.
  - A hűtőközeg hőmérséklete és áramlása nincs mérve, ezért T∞ a kihagyott munkamenettől függően 20–34 °C között változik.
  - A 70 °C feletti visszaszabályozást a modell nem tartalmazza; a nyomaték-bemenet viszont a már visszaszabályozott, tényleges nyomaték.

### Előrejelzés (`04_inverter_homodell/04_homodell_forgatokonyvek.png`, `04_homodell_elorejelzes.csv`)

Állandó terhelés D ideig, T0-ról: T(D) = T_ss + (T0 − T_ss)·e^(−D/τ), ahol T_ss = T∞ + α·u/β.
A CSV mindkét modellel 3 kezdő hőmérséklet × 4 terhelésszint × 4 időtartam forgatókönyvet tartalmaz. A `mert_tartomanyon_kivul` oszlop jelöli az extrapolációkat: végső hőmérséklet > 84,3 °C vagy időtartam > 13,2 s.

**Fő modell, 60 °C-ról indulva** (* = extrapoláció):

| Leadott nyomaték | 2 s | 4 s | 10 s | 20 s |
|---|---|---|---|---|
| 50 Nm | +0,7 °C | +1,5 °C | +3,5 °C | +6,5 °C* |
| 100 Nm | +2,6 °C | +5,1 °C | +12,1 °C | +22,4 °C* |
| 150 Nm | +4,4 °C | +8,7 °C | +20,7 °C | +38,4 °C* |
| 200 Nm | +6,2 °C | +12,3 °C | +29,3 °C* | +54,3 °C* |

**A kérdésre adott válasz: mennyivel melegít egy 100%-os nyomatékkérés?** A kérésből létrejövő tényleges nyomaték a fordulatszámtól függ (lásd 2(b), teljesítménykorlát). A mért medián nyomatékkal a fő modell szerint, 4 s, 60 °C-ról:

| Fordulat [rpm] | n | Tényleges nyomaték (medián) | Melegedés 4 s alatt |
|---|---|---|---|
| 500–1000 | 8 | 190 Nm | +11,5 °C |
| 1000–1500 | 68 | 114 Nm | +6,1 °C |
| 1500–2000 | 63 | 105 Nm | +5,4 °C |
| 2000–2500 | 62 | 98 Nm | +4,9 °C |
| 2500–3000 | 193 | 83 Nm | +3,8 °C |
| 3000–3500 | 67 | 62,5 Nm | +2,4 °C |

**Ugyanaz a 100%-os kérés alacsony fordulaton (rajtnál) ~3-szor annyira melegíti az invertert, mint 2500–3000 rpm-en.** Azonos nyomatéknál a melegedés a kezdő hőmérséklettel csökken: 100 Nm, 4 s mellett 45 °C-ról +6,0 °C, 60 °C-ról +5,1 °C, 75 °C-ról +4,2 °C.

**Mennyi idő alatt éri el az inverter a 83 °C-os lekapcsolási határt?** Állandó nyomatékkal, a fő modellel (* = hosszabb a leghosszabb mért futamnál, extrapoláció):

| Kezdő T | 50 Nm | 100 Nm | 150 Nm | 200 Nm |
|---|---|---|---|---|
| 45 °C | 240 s* | 31,1 s* | 17,6 s* | 12,3 s |
| 60 °C | 209 s* | 20,6 s* | 11,2 s | 7,7 s |
| 75 °C | 146 s* | 8,0 s | 4,1 s | 2,8 s |

- A modell állandó nyomatékot feltételez. ~70 °C felett az inverter visszaszabályozza a nyomatékot, ez lassítja a melegedést, ezért az idők alsó becslések.
- A mérésben két lekapcsolás is a 83 °C-os határnál történt: 15:29:33-ban 84,3 °C-on, 15:39:36-ban 84,2 °C-on. Ez megerősíti a határt.

### Kiegészítés: teljes kérésű teljesítmény és inverterhőmérséklet (`04_inverter_homodell/04_teljesitmeny_homerseklet.png`)

Teljes kérésű (≥ 99%) futamszakaszok 1500–3000 rpm között (legalább 5 minta), délután (10 szakasz) és délelőtt (12:59:30, 2 szakasz):

| Blokk | Átlagos inverterhőmérséklet | Átlagos akkuteljesítmény |
|---|---|---|
| délelőtt | 52–57 °C | 34–36 kW |
| délután, < 60 °C | 49–59 °C | 21–33 kW |
| délután, 69–83 °C | 69–83 °C | 10–26 kW (jellemzően 19–24 kW) |

- **Spearman, minden szakasz (n = 12):** teljesítmény–inverterhőmérséklet ρ = −0,71 (p = 0,009); teljesítmény–SOC ρ = 0,77 (p = 0,003).
- **Csak délután (n = 10):** ρ = −0,58, p = 0,082, nem szignifikáns.
- **Értelmezés:** a teljes kérésű teljesítmény a melegebb inverterrel csökken. Ez összhangban van a ~70 °C-tól induló visszaszabályozással. A csapat szerint azonban délután az inverter PWM-frekvenciáját is módosíthatták, ami szintén csökkentheti a leadható nyomatékot, és a töltöttség is a nappal együtt csökkent. A három hatás ebből az adatból nem választható szét; ehhez azonos beállítással, eltérő hőmérsékleten mért futamok kellenének.

---

## 5. Klaszterezés: a hajtáslánc üzemállapotai (`05_klaszterezes/`)

### Feladat és adatok

**Cél:** a hajtáslánc üzemállapotainak felismerése címkék nélkül (B változat: klaszterezés).
- **Tanító adat:** a tisztított adat működő, mozgó sorai (`inverter_hiba = False`, v ≥ 1 km/h), **1285 sor**. Az álló sorok kimaradnak, mert triviálisan külön csoportot alkotnának.
- **Új adat:** a 12:59:30-as délelőtti mérés, amelyet a modellek nem láttak. Ugyanazzal a 00 → 01 lánccal készült, 447 sorból mozgó: **376 sor**. Inverterhiba nincs benne.
- **Jellemzők:** `torque_request_pct` (mit kér a pilóta), `batt_power_kW` (mit ad le a hajtáslánc), `speed_kmh`, `accel_ms2`.
  - A redundáns párok másik tagja kimarad: fordulatszám ~ sebesség, áram ~ teljesítmény, pedál ~ kérés.
  - A hőmérsékletek is kimaradnak, mert a munkamenet zavaró hatását hoznák be.
  - A gyorsulás a tisztítás 0,5 s-os simításával készül; a klaszterprofilok ezzel tiszták.
- **Standardizálás:** z = (x − átlag) / szórás, a tanító adat paramétereivel; az új adat ugyanezekkel transzformálva.

### A két algoritmus

- **K-közép (K-means):** a pontokat k csoportba sorolja úgy, hogy a csoportközéppontoktól mért négyzetes távolságok összege minimális legyen. Éles besorolás: minden pont pontosan egy klaszterbe tartozik. Beállítás: 20 indítás, `random_state = 42`.
- **Fuzzy C-means (FCM):** ugyanezt a célfüggvényt a tagsági fokokkal súlyozva minimalizálja (m = 2 fuzzy kitevő). Minden pont minden klaszterhez tartozik egy 0…1 közötti fokkal, a fokok összege 1. Így az állapotok közötti fokozatos átmenetek is láthatók. Beállítás: tűrés 10⁻⁵, legfeljebb 1000 iteráció, `seed = 42`.
- Mindkettő középpont-alapú, ezért **új adatra is alkalmazható**: a K-közép a legközelebbi középpontot adja, az FCM a `cmeans_predict` függvénnyel tagsági fokot számol a meglévő középpontokhoz.
- **Miért ez a pár:** a felhasználó kérése volt a C-means. A K-közép a természetes viszonyítási alap, mert ugyanazon az elven működik, csak éles besorolással.

### A klaszterszám megválasztása (`05_klaszterezes/05_k_valasztas.png`)

| k | inercia | sziluett K-közép | sziluett C-means | DB K-közép | DB C-means | FPC | ARI |
|---|---|---|---|---|---|---|---|
| 2 | 2767 | 0,430 | 0,428 | 1,009 | 1,008 | 0,730 | 0,951 |
| 3 | 2011 | 0,435 | 0,432 | 0,872 | 0,898 | 0,643 | 0,953 |
| **4** | **1576** | **0,366** | **0,362** | **1,029** | **1,050** | **0,566** | **0,919** |
| 5 | 1322 | 0,357 | 0,351 | 1,037 | 1,045 | 0,514 | 0,882 |
| 6 | 1133 | 0,366 | 0,362 | 1,049 | 1,030 | 0,484 | 0,657 |
| 7 | 1018 | 0,372 | 0,347 | 0,968 | 1,110 | 0,468 | 0,681 |
| 8 | 910 | 0,380 | 0,330 | 0,988 | 1,156 | 0,440 | 0,677 |

A mutatók jelentése: DB = Davies–Bouldin (kisebb a jobb); FPC = fuzzy partíciós együttható (1/k…1, ahol 1 = éles felosztás); ARI = a két módszer besorolásának egyezése.

**Választás: k = 4.**
- A sziluett k = 3-nál a legnagyobb (0,435), k = 4-nél 0,366. A különbség kicsi, és a mutató k = 4 felett alig változik, így önmagában nem dönt.
- Az inercia csökkenése k = 4 után lassul (könyök).
- k = 4-nél a két módszer még erősen egyezik (ARI 0,92); k = 6-nál ez 0,66-ra esik, a felosztás instabil.
- k = 4 négy fizikailag egyértelmű üzemállapotot ad. **k = 3-nál** a nagy kérésű pontok egyetlen klaszterbe kerülnek (kérés 89%, 65 km/h, +1,5 m/s², n = 726). Így a gyorsítás és a teljesítménykorlátos nagy sebességű szakasz összeolvad, pedig a kettő fizikailag eltérő állapot.

### A klaszterek (`05_klaszterezes/05_klaszter_profilok.png`, `05_klaszterezes/05_klaszterek_pca.png`)

**Elnevezés:** a nevek szabály alapján, a középpontok fizikai értékeiből adódnak, így a két modell klaszterei automatikusan ugyanazt a nevet kapják.
- a legkisebb sebességű a „Lassú menet”;
- a maradékból a legkisebb kérésű a „Gázelvétel, lassítás”;
- a két nagy kérésűből a nagyobb gyorsulású a „Gyorsítás”, a másik a „Nagy sebesség (teljesítménykorlát)”.

Profil, fuzzy C-means, átlagok:

| Klaszter | n | Arány | Kérés | Teljesítmény | Sebesség | Gyorsulás | Nyomaték | Fordulat |
|---|---|---|---|---|---|---|---|---|
| Gyorsítás | 331 | 25,8% | 82% | 20,1 kW | 47 km/h | +2,9 m/s² | 114 Nm | 1731 |
| Nagy sebesség (teljesítménykorlát) | 447 | 34,8% | 90% | 21,9 kW | 77 km/h | +0,6 m/s² | 74 Nm | 2844 |
| Gázelvétel, lassítás | 257 | 20,0% | 13% | 5,5 kW | 59 km/h | −2,7 m/s² | 25 Nm | 2185 |
| Lassú menet | 250 | 19,5% | 25% | 3,9 kW | 16 km/h | +1,0 m/s² | 59 Nm | 578 |

- **Gyorsítás:** nagy kérés, pozitív gyorsulás, közepes sebesség; itt a legnagyobb a nyomaték.
- **Nagy sebesség:** a kérés még nagyobb, de a gyorsulás kicsi és a nyomaték is kisebb (74 Nm). A hajtáslánc itt a teljesítménykorláton fut, ugyanazt mutatja, mint a 2(b) elemzés.
- **Gázelvétel, lassítás:** nagy sebességről lassul, kis teljesítménnyel (gurulás, fékezés).
- **Lassú menet:** alacsony sebesség, kis kérés és teljesítmény (manőverezés, lassú indulás).
- A K-közép profiljai szinte azonosak (n = 314 / 469 / 261 / 241).
- A PCA-síkban az első két főkomponens a variancia 58% + 29%-át írja le; a négy klaszter jól elkülönül, az átmeneti pontok a határaikon vannak.

### A két modell értékelése és összehasonlítása

| Modell | Sziluett | Davies–Bouldin | Calinski–Harabasz |
|---|---|---|---|
| K-közép | 0,366 | 1,029 | 965,3 |
| fuzzy C-means | 0,362 | 1,050 | 960,3 |

- **Egyezés:** ARI = 0,919; a sorok **97,0%**-a ugyanabba a klaszterbe kerül. A legtöbb eltérés a gyorsítás és a nagy sebesség határán van: 24 sort a K-közép nagy sebességnek, a C-means gyorsításnak sorolt.
- **C-means:** FPC = 0,566 (k = 4-nél a tartomány 0,25…1).
  - A sorok **34,6%-a átmeneti pont** (legnagyobb tagsági fok < 0,6).
  - Ahol a két modell eltér, ott a C-means legnagyobb tagsági foka átlagosan 0,43, az egyező soroknál 0,69: az eltérések az átmeneti pontokon vannak.
- **Idősorban** (`05_klaszterezes/05_idosor_klaszterek.png`): a futamok jellegzetes sorrendje lassú menet → gyorsítás → nagy sebesség → gázelvétel. A tagsági fokok a gyorsítás → nagy sebesség átmenetnél fokozatosan cserélődnek; ezt az éles besorolás egyetlen ugrásként mutatja.

**A választott modell: fuzzy C-means.**
- Ugyanazt a felosztást adja, mint a K-közép, közel azonos minőségi mutatókkal.
- Többletinformációt is hordoz: a tagsági fokok megmutatják a fokozatos átmeneteket, és jelzik, mennyire biztos egy besorolás. Egy folytonos fizikai folyamatnál (menet) ez valósághűbb, mint az éles határ.
- A K-közép mellett az egyszerűség és a valamivel jobb mutatók szólnának, de a különbség elhanyagolható (sziluett 0,366 vs 0,362).

### Alkalmazás új adaton (`05_klaszterezes/05_uj_adat.png`)

A 12:59:30-as mérés két teljes gázas gyorsítást tartalmaz ~80 km/h-ig.

| Klaszter | Tanító | Új adat | Új adat (sor) |
|---|---|---|---|
| Gyorsítás | 25,8% | 19,9% | 75 |
| Nagy sebesség (teljesítménykorlát) | 34,8% | 6,6% | 25 |
| Gázelvétel, lassítás | 20,0% | 13,6% | 51 |
| Lassú menet | 19,5% | 59,8% | 225 |

- **A modell felismeri a futamok szerkezetét.** Mindkét gyorsítás „Lassú menet → Gyorsítás → Nagy sebesség” sorrendű; utánuk gázelvétel és lassú menet következik.
- Átmeneti pontok aránya 32,2%; a K-közép és a C-means 99,5%-ban egyezik.
- **Az arányok eltérnek:** ebben a mérésben sok a lassú menet (manőverezés a futamok előtt), és rövidebb a nagy sebességű szakasz.
- **Fontos eltérés a teljesítményben:**

  | Klaszter | P tanító | P új | Gyorsulás új | T_inverter tanító | T_inverter új |
  |---|---|---|---|---|---|
  | Gyorsítás | 20,1 kW | 24,5 kW | +4,3 m/s² | 67,1 °C | 50,4 °C |
  | Nagy sebesség | 21,9 kW | **39,8 kW** | +2,5 m/s² | 69,4 °C | 56,3 °C |

  A délelőtti futamokban nem volt meg a délutáni ~20–25 kW-os teljesítménykorlát. Ennek lehetséges okai a 4. lépés kiegészítésében szerepelnek: inverter-visszaszabályozás ~70 °C felett, a PWM-frekvencia módosítása, töltöttség. A besorolást a kérés, a sebesség és a gyorsulás mintázata így is helyesen adja, de a „teljesítménykorlát” elnevezés a délutáni állapotot írja le.

---

## Nyitott kérdések

- **Nyilvános forrás:** a feladat nyilvánosan elérhető adathalmazt és forráslinket kér. A saját mérésnél ezt pl. a CSV GitHubra feltöltésével lehet teljesíteni (link a jelentésbe).
- **A délutáni ~20–25 kW-os teljesítménykorlát oka** (a csapat szerint bizonytalan): a délutáni PWM-frekvencia-módosítás, a ~70 °C-tól induló termikus visszaszabályozás, vagy a töltöttség. Ebből az adatból nem dönthető el.
