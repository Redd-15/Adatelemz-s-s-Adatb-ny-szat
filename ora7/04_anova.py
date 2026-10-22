# -*- coding: utf-8 -*-
"""4. ANOVA varianciaelemzés.

Bemenet: student_performance_cleaned.csv (tisztított, nem imputált)

Kérdés: van-e szignifikáns különbség a hallgatók átlagos vizsgapontszáma
között képzési programonként?

H0: a három program sokasági átlagpontszáma azonos.
H1: legalább két program sokasági átlagpontszáma eltér. α = 0,05.
"""

from scipy import stats

from proba_kozos import ALFA, beolvas, cim, dontes


def main():
    df = beolvas()
    adat = df.dropna(subset=["programme", "exam_score"])

    cim("1. Hipotézisek")
    print("  H0: a három program sokasági átlagpontszáma azonos")
    print("  H1: legalább két program sokasági átlagpontszáma eltér")
    print("  α = {}".format(ALFA))

    cim("2. Adatok")
    print("Felhasznált rekordok (ismert program és pontszám): {}".format(len(adat)))
    print(adat.groupby("programme")["exam_score"].agg(["count", "mean", "std"]).round(2).to_string())
    csoportok = [g["exam_score"] for _, g in adat.groupby("programme")]

    cim("3. Egyszempontos ANOVA")
    proba = stats.f_oneway(*csoportok)
    print("F = {:.3f}, p = {:.4f}".format(proba.statistic, proba.pvalue))

    cim("4. Döntés")
    print(dontes(proba.pvalue))
    if proba.pvalue <= ALFA:
        print("Legalább két program átlagos vizsgapontszáma eltér.")
    else:
        print("Nem mutatható ki különbség a programok átlagos vizsgapontszáma között.")
    print()
    print("Megjegyzés: az ANOVA nem mondja meg, mely programok különböznek; ehhez további,")
    print("többszörös összehasonlítást kezelő post hoc vizsgálat szükséges.")


if __name__ == "__main__":
    main()
