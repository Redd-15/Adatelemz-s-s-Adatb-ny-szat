# -*- coding: utf-8 -*-
"""1. Adatok előkészítése PCA-hoz.

Bemenet: student_performance_imputed.csv

Kiválasztjuk a hallgatók numerikus tanulási jellemzőit (az exam_score
nélkül, mert a passed közvetlenül abból készült), és standardizáljuk őket.
Megmutatjuk, mennyire eltérő a változók skálája és szórása a
standardizálás előtt, és hogy utána mindegyik átlaga 0, szórása 1.
"""

import os

import pandas as pd
import matplotlib.pyplot as plt

from pca_kozos import (MAPPA, JELLEMZOK, SZIN, SZIN2, beolvas, cim, standardizal,
                       ax_formaz)


def leiro(adat):
    return adat.agg(["mean", "std", "min", "max"]).T.rename(
        columns={"mean": "átlag", "std": "szórás"})


def abra(df, z):
    fig, (ax_elott, ax_utan) = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, adat, szin, felirat, ylabel in (
            (ax_elott, df[JELLEMZOK], SZIN2, "Standardizálás előtt (eredeti mértékegység)", "érték"),
            (ax_utan, z, SZIN, "Standardizálás után (z-érték)", "z-érték")):
        doboz = ax.boxplot([adat[v] for v in JELLEMZOK], patch_artist=True, widths=0.55,
                           medianprops={"color": "black", "linewidth": 1.8})
        for test in doboz["boxes"]:
            test.set(facecolor=szin, alpha=0.45, edgecolor=szin)
        ax.set_xticks(range(1, len(JELLEMZOK) + 1))
        ax.set_xticklabels(JELLEMZOK, rotation=15, fontsize=9)
        ax_formaz(ax, felirat, "", ylabel, racs="y")
    fig.suptitle("A PCA bemeneti változói", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "01_adatelokeszites.png"), dpi=120)


def main():
    pd.set_option("display.width", 130)
    df = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    cim("A PCA jellemzői")
    print("Kiválasztott változók: {}".format(", ".join(JELLEMZOK)))
    print("Hiányzó értékek: {}".format(int(df[JELLEMZOK].isna().sum().sum())))
    print()
    print("Az exam_score kimarad: a passed (≥ 50 pont → yes) közvetlenül az exam_score-ból")
    print("készült. Ha bevonnánk, a főkomponensek részben magát a sikerességet kódolnák, és a")
    print("sikeres / sikertelen hallgatók elkülönülése mesterségesen felerősödne az ábrán.")

    cim("Leíró statisztikák standardizálás előtt")
    elotte = leiro(df[JELLEMZOK])
    print(elotte.round(2).to_string())
    print()
    print("A változók mértékegysége és szórása nagyon eltérő: az attendance szórása ({:.2f})"
          .format(elotte.loc["attendance", "szórás"]))
    print("közel {:.0f}-szorosa a previous_gpa szórásának ({:.2f}), a szórásnégyzet (variancia)"
          .format(elotte.loc["attendance", "szórás"] / elotte.loc["previous_gpa", "szórás"],
                  elotte.loc["previous_gpa", "szórás"]))
    print("esetében ez az arány a négyzete. Mivel a PCA a varianciát maximalizálja,")
    print("standardizálás nélkül az első főkomponens gyakorlatilag az attendance lenne.")

    cim("Standardizálás: z = (x − átlag) / szórás")
    z = standardizal(df, JELLEMZOK)
    # + 0.0: a lebegőpontos −0.000 kiírás helyett 0.000
    print((leiro(z).round(3) + 0.0).to_string())
    print()
    print("Standardizálás után minden változó átlaga 0 és szórása 1 (a StandardScaler a")
    print("populációs szórással, n-nel oszt, ezért a pandas n−1-es szórása {:.3f})."
          .format(z["study_hours"].std()))
    print("Így minden változó azonos súllyal indul a főkomponensek képzésében; a PCA ekkor")
    print("a korrelációs mátrixra épül.")
    print()
    print("Az első 5 hallgató standardizált értékei:")
    print(pd.concat([df["student_id"], z.round(3)], axis=1).head().to_string(index=False))

    abra(df, z)
    plt.show()


if __name__ == "__main__":
    main()
