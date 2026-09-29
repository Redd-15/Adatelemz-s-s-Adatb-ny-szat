# -*- coding: utf-8 -*-
"""2. Duplikált és következetlen adatok felismerése.

a) Teljesen azonos sorok és többször előforduló student_id keresése,
   a valódi duplikátumok eltávolítása.
b) A kategorikus változók egységesítése (felesleges szóközök, kis-nagybetű,
   rövidítések).

A kimenet a 02_student_performance_step2.csv fájl, amellyel a 3. feladat
dolgozik tovább.
"""

import os

import pandas as pd

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_raw.csv")
KIMENET = os.path.join(MAPPA, "02_student_performance_step2.csv")

# Az azonos képzést jelölő írásmódok egységesítése (kisbetűs alak -> végleges név)
PROGRAMME_MAP = {
    "computer science": "Computer Science",
    "cs": "Computer Science",
    "business informatics": "Business Informatics",
    "bi": "Business Informatics",
    "mechanical engineering": "Mechanical Engineering",
    "me": "Mechanical Engineering",
}

PASSED_MAP = {"yes": "Yes", "y": "Yes", "no": "No", "n": "No"}


def cim(szoveg):
    """Szakaszcím a kimenetben."""
    print()
    print("=" * 70)
    print(szoveg)
    print("=" * 70)


def beolvas(ut):
    """Beolvasás a fejléc alapján felismert elválasztójellel (';' vagy ',')."""
    with open(ut, encoding="utf-8") as fajl:
        fejlec = fajl.readline()
    sep = ";" if fejlec.count(";") > fejlec.count(",") else ","
    print("Elválasztójel: '{}'".format(sep))
    return pd.read_csv(ut, sep=sep, encoding="utf-8", dtype="string")


def szoveg_tisztit(sorozat):
    """Felesleges szóközök eltávolítása a sor elejéről, végéről és belsejéből."""
    return sorozat.str.strip().str.replace(r"\s+", " ", regex=True)


def main():
    pd.set_option("display.width", 130)
    pd.set_option("display.max_columns", 20)

    df = beolvas(BEMENET)
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    # ------------------------------------------------------------------
    # a) Duplikátumok
    # ------------------------------------------------------------------
    cim("a) Teljesen azonos sorok (df.duplicated())")
    print("Teljesen duplikált sorok száma: {}".format(int(df.duplicated().sum())))
    print()
    print("Az érintett sorok (mindkét előfordulás):")
    print(df[df.duplicated(keep=False)].sort_values("student_id").to_string())

    cim("a) Többször előforduló azonosítók (df['student_id'].duplicated())")
    ismetlodo_id = df.loc[df["student_id"].duplicated(), "student_id"].tolist()
    print("Ismétlődő student_id értékek: {}".format(ismetlodo_id))
    print()
    print("Az azonos azonosítóhoz tartozó rekordok egymás mellett (df.sort_values()):")
    ismetlodo_sorok = df[df["student_id"].isin(ismetlodo_id)].sort_values("student_id")
    print(ismetlodo_sorok.to_string())

    cim("a) Mely rekordok valódi duplikátumok?")
    for azonosito in sorted(set(ismetlodo_id)):
        reszlet = df[df["student_id"] == azonosito]
        # Minden adatban megegyeznek-e az azonos hallgatóhoz tartozó rekordok?
        azonos = reszlet.drop_duplicates().shape[0] == 1
        if azonos:
            print("{}: a két rekord MINDEN adatban megegyezik -> valódi duplikátum".format(
                azonosito))
        else:
            elteres = [oszlop for oszlop in df.columns
                       if reszlet[oszlop].nunique(dropna=False) > 1]
            print("{}: a rekordok ELTÉRNEK ({}) -> nem valódi duplikátum".format(
                azonosito, ", ".join(elteres)))

    # A valódi (teljesen azonos) duplikátumok eltávolítása
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    print()
    print("A valódi duplikátumok eltávolítása után: {} sor".format(len(df)))

    # Az ellentmondó S033 nem duplikátum: külön rekordként marad, új azonosítóval,
    # hogy a student_id ismét egyedi legyen.
    tobbszoros = df["student_id"].duplicated(keep="first")
    for index in df.index[tobbszoros]:
        regi = df.at[index, "student_id"]
        uj = "{}_2".format(regi)
        df.at[index, "student_id"] = uj
        print("Ellentmondó rekord új azonosítót kapott: {} -> {}".format(regi, uj))
    print("Egyedi azonosítók száma: {} / {} sor".format(
        df["student_id"].nunique(), len(df)))

    # ------------------------------------------------------------------
    # b) Kategorikus változók egységesítése
    # ------------------------------------------------------------------
    cim("b) Kategorikus változók a tisztítás ELŐTT")
    print("programme egyedi értékei ({} db):".format(df["programme"].nunique()))
    print(sorted(df["programme"].dropna().unique().tolist()))
    print()
    print(df["programme"].value_counts(dropna=False))
    print()
    print("passed egyedi értékei: {}".format(
        sorted(df["passed"].dropna().unique().tolist())))

    df["student_id"] = szoveg_tisztit(df["student_id"]).str.upper()
    df["programme"] = szoveg_tisztit(df["programme"]).str.lower().replace(PROGRAMME_MAP)
    df["passed"] = szoveg_tisztit(df["passed"]).str.lower().replace(PASSED_MAP)

    # Maradt-e olyan érték, amit a szótár nem ismert fel?
    ismeretlen = set(df["programme"].dropna().unique()) - set(PROGRAMME_MAP.values())
    if ismeretlen:
        print()
        print("FIGYELEM, ismeretlen képzésnév maradt: {}".format(sorted(ismeretlen)))

    cim("b) Kategorikus változók a tisztítás UTÁN")
    print("programme egyedi értékei ({} db):".format(df["programme"].nunique()))
    print(df["programme"].value_counts(dropna=False))
    print()
    print("passed egyedi értékei: {}".format(
        sorted(df["passed"].dropna().unique().tolist())))
    print(df["passed"].value_counts(dropna=False))

    df.to_csv(KIMENET, sep=";", index=False, encoding="utf-8")
    cim("Mentés")
    print("{} sor, {} oszlop -> {}".format(*df.shape, os.path.basename(KIMENET)))


if __name__ == "__main__":
    main()
