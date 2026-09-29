# -*- coding: utf-8 -*-
"""3. Hibás és lehetetlen értékek ellenőrzése.

a) Tárolt és elvárt adattípusok összevetése, a nem számmá alakítható
   értékek listázása és kezelése.
b) Tartományellenőrzés, majd a passed és az exam_score összhangjának
   vizsgálata 50 pontos ponthatárral.

Bemenet: 02_student_performance_step2.csv (a 2. feladat kimenete)
Kimenet: student_performance_clean.csv (a tisztított adathalmaz)

Döntések (egyeztetve):
  - a hiányzó értékek üresen maradnak, nem pótoljuk őket;
  - a negatív értékeket az abszolútértékükkel helyettesítjük (elírt előjel);
  - a maximumot meghaladó értékeket a maximumra vágjuk;
  - ami ezek után is a megengedett tartományon kívül esik, hiányzó lesz;
  - a tizedesvesszős érték ('3,2') egyértelműen javítható: 3.2;
  - a szóval kiírt szám ('ten', 'seven') egyértelmű, ezért számmá alakítjuk;
  - a passed értékét a vizsgaeredményből javítjuk (ponthatár: 50).
"""

import os

import pandas as pd

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "02_student_performance_step2.csv")
KIMENET = os.path.join(MAPPA, "student_performance_clean.csv")

PONTHATAR = 50

# Elvárt tárolási típus a változó tartalmi típusa alapján
ELVART_TIPUS = {
    "student_id": "szöveg (azonosító)",
    "programme": "szöveg (kategorikus)",
    "study_hours": "float",
    "attendance": "float",
    "previous_gpa": "float",
    "assignments_completed": "egész (Int64)",
    "exam_score": "float",
    "passed": "szöveg (kategorikus)",
}

NUMERIKUS = ["study_hours", "attendance", "previous_gpa",
             "assignments_completed", "exam_score"]
EGESZ = ["assignments_completed"]

# Megengedett tartományok a feladat szabályai szerint
TARTOMANY = {
    "study_hours": (0, 80),
    "attendance": (0, 100),
    "previous_gpa": (1, 5),
    "assignments_completed": (0, 10),
    "exam_score": (0, 100),
}

# Szóval kiírt számok (egyértelműen feloldhatók)
SZAM_SZAVAK = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12",
}


def cim(szoveg):
    """Szakaszcím a kimenetben."""
    print()
    print("=" * 70)
    print(szoveg)
    print("=" * 70)


def szammaalakithato(sorozat):
    """A szöveges oszlop számmá alakítása a nyilvánvaló hibák javításával."""
    tisztitott = (sorozat.str.strip()
                  .str.replace(",", ".", regex=False)     # tizedesvessző -> pont
                  .str.lower()
                  .replace(SZAM_SZAVAK))                  # 'ten' -> '10'
    return pd.to_numeric(tisztitott, errors="coerce")


def main():
    pd.set_option("display.width", 130)
    pd.set_option("display.max_columns", 20)

    df = pd.read_csv(BEMENET, sep=";", encoding="utf-8", dtype="string")
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    # ------------------------------------------------------------------
    # a) Adattípusok
    # ------------------------------------------------------------------
    cim("a) Tárolt adattípusok (df.info())")
    df.info()

    cim("a) Tárolt és elvárt adattípus összevetése")
    print("{:<24} {:<22} {}".format("változó", "tárolt (nyers)", "elvárt"))
    for oszlop, elvart in ELVART_TIPUS.items():
        print("{:<24} {:<22} {}".format(oszlop, str(df[oszlop].dtype), elvart))
    print()
    print("A numerikus oszlopok mind szövegként érkeznek, mert szöveges és")
    print("tizedesvesszős értékeket is tartalmaznak. Ezért alakítjuk át őket.")

    cim("a) Nem számmá alakítható értékek a numerikus oszlopokban")
    szamok = pd.DataFrame(index=df.index)
    for oszlop in NUMERIKUS:
        nyers = df[oszlop]
        szamok[oszlop] = szammaalakithato(nyers)

        # Ami eredetileg nem volt szám, de a javítás után már az: sikeres javítás
        kozvetlen = pd.to_numeric(nyers, errors="coerce")
        javitott = df.loc[kozvetlen.isna() & szamok[oszlop].notna() & nyers.notna(),
                          ["student_id", oszlop]]
        for sor in javitott.to_dict("records"):
            print("JAVÍTVA   {} {} = {!r} -> {}".format(
                sor["student_id"], oszlop, sor[oszlop],
                szamok.loc[df["student_id"] == sor["student_id"], oszlop].iloc[0]))

        # Ami a javítás után sem szám: hiányzó értékké válik
        maradt = df.loc[szamok[oszlop].isna() & nyers.notna(), ["student_id", oszlop]]
        for sor in maradt.to_dict("records"):
            print("NaN LETT  {} {} = {!r} (nem állapítható meg a helyes érték)".format(
                sor["student_id"], oszlop, sor[oszlop]))

    cim("a) Egész értéket tartalmazó változók ellenőrzése")
    for oszlop in EGESZ:
        nem_egesz = szamok.loc[szamok[oszlop].notna() & (szamok[oszlop] % 1 != 0),
                               oszlop]
        print("{}: {} nem egész érték".format(oszlop, len(nem_egesz)))
        if len(nem_egesz):
            print(df.loc[nem_egesz.index, ["student_id", oszlop]].to_string())

    cim("a) Kategorikus és azonosító változók tárolása")
    for oszlop in ["student_id", "programme", "passed"]:
        print("{:<12} {:<8} különböző érték: {}".format(
            oszlop, str(df[oszlop].dtype), df[oszlop].nunique()))
    print("Ezek szövegként tárolva helyesek; a student_id azonosító, nem szám.")

    # ------------------------------------------------------------------
    # b) Tartományellenőrzés
    # ------------------------------------------------------------------
    cim("b) Tartományon kívüli (lehetetlen) értékek")
    print("Szabályok: " + ", ".join(
        "{} {}-{}".format(oszlop, also, felso)
        for oszlop, (also, felso) in TARTOMANY.items()))
    print()
    osszes_serto = 0
    for oszlop, (also, felso) in TARTOMANY.items():
        # 1. Negatív érték: elírt előjel, az abszolútértékét vesszük
        negativ = szamok[oszlop].notna() & (szamok[oszlop] < 0)
        for index, ertek in szamok.loc[negativ, oszlop].items():
            print("ABSZOLÚT  {} {} = {} -> {}".format(
                df.at[index, "student_id"], oszlop, ertek, -ertek))
        szamok.loc[negativ, oszlop] = szamok.loc[negativ, oszlop].abs()

        # 2. A maximumot meghaladó érték: a maximumra vágjuk
        tul_nagy = szamok[oszlop].notna() & (szamok[oszlop] > felso)
        for index, ertek in szamok.loc[tul_nagy, oszlop].items():
            print("MAXIMUMRA {} {} = {} -> {}".format(
                df.at[index, "student_id"], oszlop, ertek, felso))
        szamok.loc[tul_nagy, oszlop] = felso

        # 3. Ami ezek után is kilóg (pl. a minimum alatti pozitív érték): hiányzó
        maradt = szamok[oszlop].notna() & (szamok[oszlop] < also)
        for index, ertek in szamok.loc[maradt, oszlop].items():
            print("NaN LETT  {} {} = {} (megengedett: {}-{})".format(
                df.at[index, "student_id"], oszlop, ertek, also, felso))
        szamok.loc[maradt, oszlop] = pd.NA

        osszes_serto += int(negativ.sum()) + int(tul_nagy.sum()) + int(maradt.sum())
    print()
    print("Összesen {} tartományon kívüli érték kezelve.".format(osszes_serto))
    print("A szélsőséges, de lehetséges értékek (pl. 32 óra tanulás, 38% látogatás)")
    print("megmaradnak, mert a megengedett tartományon belül vannak.")

    # Az átalakított numerikus oszlopok visszaírása
    for oszlop in NUMERIKUS:
        df[oszlop] = szamok[oszlop].astype("Float64")
    for oszlop in EGESZ:
        df[oszlop] = df[oszlop].round().astype("Int64")

    # ------------------------------------------------------------------
    # b) A passed és az exam_score összhangja
    # ------------------------------------------------------------------
    cim("b) A passed összhangja a vizsgaeredménnyel (ponthatár: {})".format(PONTHATAR))
    van_pont = df["exam_score"].notna()
    elvart_passed = df["exam_score"].ge(PONTHATAR).map({True: "Yes", False: "No"})
    ellentmondo = van_pont & df["passed"].notna() & (df["passed"] != elvart_passed)

    for index in df.index[ellentmondo]:
        print("JAVÍTVA   {} exam_score = {} -> passed: {} -> {}".format(
            df.at[index, "student_id"], df.at[index, "exam_score"],
            df.at[index, "passed"], elvart_passed[index]))
    df.loc[ellentmondo, "passed"] = elvart_passed[ellentmondo]
    print("Ellentmondó rekordok száma: {}".format(int(ellentmondo.sum())))

    hianyzo_passed = df["passed"].isna()
    print()
    print("Hiányzó passed: {} sor. Ezekben az exam_score is hiányzik ({} sor),".format(
        int(hianyzo_passed.sum()), int((hianyzo_passed & df["exam_score"].isna()).sum())))
    print("ezért nem pótolható, üresen marad.")

    # ------------------------------------------------------------------
    # Mentés és összegzés
    # ------------------------------------------------------------------
    cim("A tisztított adathalmaz")
    df.info()
    print()
    print(df.describe().round(2))
    print()
    print("Hiányzó értékek oszloponként:")
    print(df.isna().sum())

    df.to_csv(KIMENET, sep=";", index=False, encoding="utf-8")
    cim("Mentés")
    print("{} sor, {} oszlop -> {}".format(*df.shape, os.path.basename(KIMENET)))


if __name__ == "__main__":
    main()
