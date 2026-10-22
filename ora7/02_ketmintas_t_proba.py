# -*- coding: utf-8 -*-
"""2. Független kétmintás t-próba.

Bemenet: student_performance_cleaned.csv (tisztított, nem imputált)

Kérdés: eltér-e a Business Informatics (A) és a Computer Science (B)
program hallgatóinak átlagos vizsgapontszáma?

H0: μA = μB, H1: μA ≠ μB (kétoldali), α = 0,05.
Az A programból 25, a B programból 30 hallgatót választunk véletlenszerűen
(seed = 42); a két csoport különböző hallgatókból áll.
"""

from scipy import stats

from proba_kozos import ALFA, SEED, beolvas, cim, dontes, normalitas

A, B = "Business Informatics", "Computer Science"
N_A, N_B = 25, 30


def main():
    df = beolvas()
    ismert = df[df["exam_score"].notna()]

    cim("1. Hipotézisek")
    print("  H0: μA = μB  (nincs eltérés)")
    print("  H1: μA ≠ μB  (van eltérés) – kétoldali próba")
    print("  α = {}".format(ALFA))

    cim("2. Mintavétel")
    xa = ismert[ismert["programme"] == A].sample(N_A, random_state=SEED)["exam_score"]
    xb = ismert[ismert["programme"] == B].sample(N_B, random_state=SEED)["exam_score"]
    for nev, x in (("A: " + A, xa), ("B: " + B, xb)):
        print("  {:<26} n = {}, átlag = {:.2f}, szórás = {:.2f}".format(nev, len(x), x.mean(), x.std()))

    cim("3. Feltételek")
    print("Függetlenség: a megfigyeléseket függetlennek feltételezzük (a két csoport különböző")
    print("hallgatókból áll).")
    print("Normalitás – Shapiro–Wilk-próba csoportonként:")
    normalitas(xa, A)
    normalitas(xb, B)

    cim("4. Független kétmintás t-próba")
    proba = stats.ttest_ind(xa, xb)
    ki = proba.confidence_interval(0.95)
    print("t = {:.3f}, szabadságfok = {:.0f}, p = {:.4f}".format(proba.statistic, proba.df, proba.pvalue))
    print("Hatás: átlagkülönbség (A − B) = {:+.2f} pont".format(xa.mean() - xb.mean()))
    print("95%-os konfidenciaintervallum a különbségre: [{:.2f}; {:.2f}]".format(ki.low, ki.high))

    cim("5. Döntés")
    print(dontes(proba.pvalue))
    if proba.pvalue <= ALFA:
        print("A két program átlagos vizsgapontszáma eltér.")
    else:
        print("Nem mutatható ki különbség a két program átlagos vizsgapontszáma között; a")
        print("megfigyelt eltérés a véletlen mintavételi ingadozással is magyarázható.")


if __name__ == "__main__":
    main()
