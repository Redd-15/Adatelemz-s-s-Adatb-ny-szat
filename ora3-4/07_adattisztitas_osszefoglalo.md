# Adattisztítási összefoglaló

Adathalmaz: `student_performance_raw.csv` (124 rekord, 8 változó)
Eredmény: `05_student_performance_potolt.csv` (**114 rekord**, 8 változó, hiányzó érték nélkül)

## Rekordszám lépésenként

| lépés | rekordszám | változás |
|---|---|---|
| nyers adat | 124 | |
| 2. duplikátumok eltávolítása | 121 | −3 |
| 5. hiányzó `previous_gpa` miatti törlés | 114 | −7 |
| 6. kiugró értékek kezelése | 114 | 0 |

## 1. Duplikált sorok (2. feladat)

- **3 teljesen azonos sort távolítottunk el:** S015, S050 és S090 kétszer szerepelt, mindig ugyanazokkal az adatokkal.
- **Az S033 két rekordja eltér** (`attendance`, `exam_score`), ezért nem tekintettük duplikátumnak. Mindkettő megmaradt, a második `S033_2` azonosítót kapott.
- Az egységesítés során a `programme` 10 különböző írásmódját 3 kategóriára vontuk össze. 7 érték változott (pl. `CS`, `computer science` → `Computer Science`).

## 2. Hibás értékek átalakítása (3. feladat)

**Összesen 11 hibás értéket alakítottunk át:**

| hiba típusa | db | példa |
|---|---|---|
| nem számként tárolt érték | 3 | `'ten'` → 10, `'3,2'` → 3.2, `'seven'` → 7 |
| negatív érték (elírt előjel) → abszolútérték | 2 | S012 `study_hours` −4 → 4, S094 `attendance` −12 → 12 |
| maximum feletti érték → a maximumra vágva | 4 | S030 `attendance` 108 → 100, S077 `exam_score` 118 → 100 |
| `passed` ellentmond az `exam_score`-nak (ponthatár: 50) | 2 | S039 Yes → No, S071 No → Yes |

Emellett minden numerikus oszlop szöveges típusról számtípusra lett alakítva.

## 3. Hiányzó értékek pótlása (4–5. feladat)

A pótlás előtt 23 rekordban (19,0%) hiányzott legalább egy érték. Az `exam_score` és a `passed` mind a 7 esetben együtt hiányzott.

| változó | hiányzó | módszer |
|---|---|---|
| `study_hours` | 7 | a `passed` csoport átlaga (Yes: 11,7 óra; No: 9,6 óra). Mind a 7 hallgató Yes volt, ezért mindegyik 11,7-et kapott. |
| `previous_gpa` | 7 | **a rekordok törlése** (7 rekord) |
| `programme` | 3 | módusz (`Computer Science`) |
| `exam_score` | 7 | képzési programonként számított medián (64,9–66,9 pont) |
| `passed` | 7 | a pótolt `exam_score`-ból számítva (≥ 50 → Yes), mind a 7 Yes lett |

A pótlás a `study_hours` és az `exam_score` szórását kissé csökkentette. A változók közötti korrelációkon legfeljebb 0,05-ot változtatott.

## 4. Kiugró értékek (6. feladat)

Az IQR-módszerrel (Q1 − 1,5·IQR, Q3 + 1,5·IQR) **6 lehetséges kiugró értéket** találtunk 6 rekordban:

| változó | db | rekordok |
|---|---|---|
| `study_hours` | 2 | S006 (32,0 óra), S109 (29,0 óra) |
| `attendance` | 2 | S055 (38,0%), S094 (12,0%) |
| `assignments_completed` | 2 | S045 (0), S104 (2) |
| `previous_gpa`, `exam_score` | 0 | – |

## 5. A kiugró értékek kezelése

- **Egyik kiugró értéket sem töröltük és nem módosítottuk.** Mind a megengedett tartományon belül esik, és a rekordok többi adata alapján valós szélsőségnek tűnik.
- **`study_hours`:** a négy módszer (megtartás, törlés, korlátozás, mediánnal csere) összevetése után a **megtartást** választottuk. A két érték a legszorgalmasabb hallgatókhoz tartozik (93–94 pont). A törlés és a mediánnal csere a `study_hours`–`exam_score` korrelációt 0,365-ről 0,32 körülire rontaná.
- **Gyanús rekord: S094.** A 12%-os óralátogatás mellett 64,3 pontot ért el, és az érték a nyers adatban −12 volt. Valószínű adathiba, de a helyes érték nem állapítható meg, ezért változatlanul hagytuk.

## Eredmény

A megtisztított adathalmazban **114 rekord** maradt, hiányzó érték nélkül.
