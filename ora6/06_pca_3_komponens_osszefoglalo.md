# PCA három főkomponenssel – megfigyelések

Szkript: `06_pca_3_komponens.py`, ábra: `06_pca_3_komponens.png`
Adathalmaz: `student_performance_imputed.csv` (114 hallgató)
Jellemzők: `study_hours`, `attendance`, `previous_gpa`, `assignments_completed` (standardizálva, a redundáns `sleep_hours` nélkül)

## Összevetés a 3. feladattal

| | 2 komponens (3. feladat) | 3 komponens |
|---|---|---|
| megőrzött variancia | 60,93% | **81,79%** |
| kimaradt variancia | 39,07% | 18,21% |
| passed csoportok elkülönülése* | 1,11 | **1,20** |
| távol eső hallgatók | S006, S055 | S055 |

\* A sikeres és a sikertelen csoport középpontjának távolsága a közös szórás egységében (Mahalanobis-távolság). Mind a négy eredeti változóval mérve az érték 1,22.

## Komponenssúlyok

| változó | PC1 | PC2 | PC3 |
|---|---|---|---|
| `study_hours` | 0,110 | 0,739 | −0,359 |
| `attendance` | 0,522 | 0,394 | **0,742** |
| `previous_gpa` | **0,677** | −0,015 | −0,562 |
| `assignments_completed` | 0,507 | −0,547 | 0,064 |

## Megfigyelések

1. **A három komponens a variancia 81,79%-át őrzi meg.** A PC3 20,86 százalékpontot ad hozzá, így teljesül a 80%-os gyakorlati irányelv.

2. **Az első két komponens nem változik.** A PC1 és a PC2 súlyai és pontszámai pontosan megegyeznek a 3. feladatéval. A PCA komponensei egymásra épülnek: egy újabb komponens csak egy új, a korábbiakra merőleges tengelyt ad hozzá.

3. **A PC3 az óralátogatást állítja szembe az előzetes eredménnyel és a tanulási idővel.** Magas PC3-értéket az kap, aki rendszeresen bejár az órákra, de az előzetes GPA-ja és a tanulási ideje alacsonyabb („bejár, de kevésbé felkészült”). Alacsonyat az kap, aki jó előzetes eredményű és sokat tanul, de ritkábban jár órára.

4. **A sikeres és a sikertelen hallgatókat továbbra is főként a PC1 választja szét.**

   | komponens | elkülönülés | t-próba p-értéke |
   |---|---|---|
   | PC1 | 1,07 | < 0,001 |
   | PC2 | 0,24 | 0,24 |
   | PC3 | 0,35 | 0,09 |

   A PC3 mentén a sikertelenek átlaga kissé magasabb (+0,23, a sikereseké −0,09), de ez a különbség gyenge. Három dimenzióban az elkülönülés 1,11-ről 1,20-ra nő, a pontfelhők azonban térben is erősen átfedik egymást.

5. **Ez alátámasztja a 3. feladat megjegyzését.** A csoportokat megkülönböztető eltérés kis része valóban a kihagyott komponensben volt. A négy tanulási jellemző alapján azonban sem válik el élesen a két csoport: a sikerességet ezek a változók csak részben írják le.

6. **A távol eső hallgatók köre szűkül.** Az S055 (1 tanulási óra, a legalacsonyabb óralátogatás, magas GPA) három dimenzióban is kiugrik. Az S006 már a határon belül van, mert a PC3 mentén átlagos (−0,18), és három dimenzióban magasabb a határ (χ²(3; 0,975) = 9,35 a kétdimenziós 7,38 helyett).

7. **A térbeli ábra nehezen olvasható.** A nézőponttól függ, mennyi átfedés látszik. A PC1–PC3 és a PC2–PC3 síkvetület áttekinthetőbb képet ad.

## Megjegyzés

A PCA nem a csoportok szétválasztására törekszik, hanem a bemeneti változók varianciáját őrzi meg. A `passed` csak a pontok színét határozza meg, a főkomponensek képzésében nem vesz részt. Az elkülönülési mutató és a t-próba leíró, tájékoztató jellegű.
