# -*- coding: utf-8 -*-
"""1. Egymintás t-próba.

Bemenet: student_performance_cleaned.csv (tisztított, nem imputált)

Kérdés: eltér-e a Computer Science program hallgatóinak átlagos
vizsgapontszáma a korábbi években jellemző 70 ponttól?

H0: μ = 70 (nincs eltérés), H1: μ ≠ 70 (kétoldali), α = 0,05.
A programból véletlenszerűen 25 hallgatót választunk (seed = 42).
"""

from scipy import stats

from proba_kozos import ALFA, SEED, beolvas, cim, dontes, normalitas

PROGRAM = "Computer Science"
MU0 = 70
N = 25


def main():
    df = beolvas()

    cim("1. Hipotézisek")
    print("  H0: μ = {}  (az átlagos pontszám megegyezik a korábbi évekével)".format(MU0))
    print("  H1: μ ≠ {}  (van eltérés) – kétoldali próba".format(MU0))
    print("  α = {}".format(ALFA))

    cim("2. Mintavétel")
    sokasag = df[(df["programme"] == PROGRAM) & df["exam_score"].notna()]
    x = sokasag.sample(N, random_state=SEED)["exam_score"]
    print("{}: véletlenszerűen kiválasztott {} hallgató vizsgapontszáma".format(PROGRAM, N))
    print("Mintaátlag = {:.2f}, szórás = {:.2f}".format(x.mean(), x.std()))

    cim("3. Feltételek")
    print("Függetlenség: a megfigyeléseket függetlennek feltételezzük.")
    print("Normalitás – Shapiro–Wilk-próba:")
    normalitas(x, "exam_score")

    cim("4. Egymintás t-próba")
    proba = stats.ttest_1samp(x, MU0)
    ki = proba.confidence_interval(0.95)
    print("t = {:.3f}, szabadságfok = {}, p = {:.4f}".format(proba.statistic, proba.df, proba.pvalue))
    print("Hatás: az átlag eltérése a {} ponttól = {:+.2f} pont".format(MU0, x.mean() - MU0))
    print("95%-os konfidenciaintervallum a sokasági átlagra: [{:.2f}; {:.2f}]".format(ki.low, ki.high))

    cim("5. Döntés")
    print(dontes(proba.pvalue))
    if proba.pvalue <= ALFA:
        print("A {} hallgatóinak átlagos pontszáma eltér a korábbi {} ponttól.".format(PROGRAM, MU0))
    else:
        print("Nem mutatható ki, hogy a {} hallgatóinak átlagos pontszáma eltérne a korábbi".format(
            PROGRAM))
        print("{} ponttól; a megfigyelt eltérés a véletlen mintavételi ingadozással is magyarázható.".format(
            MU0))
        print("A H0 el nem utasítása nem bizonyítja, hogy nincs eltérés.")


if __name__ == "__main__":
    main()
