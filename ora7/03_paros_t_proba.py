# -*- coding: utf-8 -*-
"""3. Páros kétmintás t-próba.

Bemenet: student_performance_cleaned.csv (tisztított, nem imputált)

Feltételezzük, hogy minden hallgató kétszer írta meg a dolgozatot: egy
felkészítő kurzus előtt és után. Kérdés: változott (javult)-e a hallgatók
átlagos teszteredménye a kurzus után?

H0: nem változott, H1: javult – jobb oldali próba, α = 0,05.

A „kurzus előtti” eredmény 25 véletlenszerűen kiválasztott hallgató
exam_score-ja. A „kurzus utáni” eredmény nincs az adatbázisban, ezért
szimuláljuk: előtte + N(4; 6) pontos egyéni változás, legfeljebb 100 pont.
"""

import numpy as np
import pandas as pd
from scipy import stats

from proba_kozos import ALFA, SEED, beolvas, cim, dontes, normalitas

N = 25


def main():
    df = beolvas()

    cim("1. Hipotézisek")
    print("d = utána − előtte (hallgatónként)")
    print("  H0: μd = 0  (nem változott)")
    print("  H1: μd > 0  (javult) – jobb oldali próba")
    print("  α = {}".format(ALFA))

    cim("2. Mintavétel és párosítás")
    minta = df[df["exam_score"].notna()].sample(N, random_state=SEED)
    rng = np.random.default_rng(SEED)
    elotte = minta["exam_score"].to_numpy()
    utana = np.clip(elotte + rng.normal(4, 6, N), 0, 100).round(1)
    par = pd.DataFrame({"student_id": minta["student_id"].to_numpy(), "előtte": elotte,
                        "utána": utana, "különbség": (utana - elotte).round(1)})
    print("{} véletlenszerűen kiválasztott hallgató, eredményeik hallgatónként párosítva.".format(N))
    print("(A kurzus utáni pontszám szimulált, mert ilyen adat nincs az adatbázisban.)")
    print()
    print(par.to_string(index=False))
    print()
    print("Átlag: előtte = {:.2f}, utána = {:.2f}, különbség = {:+.2f}".format(
        par["előtte"].mean(), par["utána"].mean(), par["különbség"].mean()))

    cim("3. Feltételek")
    print("Függetlenség: a különböző hallgatók eredménykülönbségeit függetlennek feltételezzük.")
    print("Normalitás – Shapiro–Wilk-próba a különbségekre:")
    normalitas(par["különbség"], "különbség (utána − előtte)")

    cim("4. Páros t-próba (jobb oldali)")
    proba = stats.ttest_rel(par["utána"], par["előtte"], alternative="greater")
    print("t = {:.3f}, szabadságfok = {}, p = {:.4g}".format(proba.statistic, proba.df, proba.pvalue))
    print("Hatás: átlagos különbség = {:+.2f} pont".format(par["különbség"].mean()))
    print("95%-os (egyoldali) konfidenciaintervallum: [{:.2f}; +∞) pont".format(
        proba.confidence_interval(0.95).low))

    cim("5. Döntés")
    print(dontes(proba.pvalue))
    if proba.pvalue <= ALFA:
        print("A felkészítő kurzus után a hallgatók átlagos teszteredménye javult.")
    else:
        print("Nem mutatható ki, hogy a kurzus után javult volna az átlagos teszteredmény.")


if __name__ == "__main__":
    main()
