# -*- coding: utf-8 -*-
"""6. PCA három főkomponens megtartásával.

Bemenet: student_performance_imputed.csv

Az 1–3. feladat alapján (a redundáns sleep_hours nélkül) a négy
standardizált jellemzőn három komponensű PCA-t végzünk, a hallgatókat a
passed szerint színezve ábrázoljuk (térben és a PC3-at tartalmazó
síkvetületekben), majd az eredményt összevetjük a 3. feladat kétkomponensű
megoldásával.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.decomposition import PCA

from pca_kozos import (MAPPA, JELLEMZOK, SZIN, SZIN2, SZOVEG_SZIN, RACS_SZIN, PASSED_SZINEK,
                       beolvas, cim, standardizal, pca_2d, sulyok, ax_formaz, elkulonules)

PC = ["PC1", "PC2", "PC3"]


def pca_3d(df):
    """Standardizálás + három komponensű PCA; a modell és a pontszámok DataFrame-je."""
    z = standardizal(df, JELLEMZOK)
    pca = PCA(n_components=3)
    eredmeny = pd.DataFrame(pca.fit_transform(z), columns=PC, index=df.index)
    eredmeny[["student_id", "programme", "passed"]] = df[["student_id", "programme", "passed"]]
    return pca, eredmeny


def tavoliak(eredmeny, pca, oszlopok):
    """A PC-k szórásával skálázott távolság² > χ²(k; 0,975) feltételnek megfelelő hallgatók."""
    d2 = sum(eredmeny[pc] ** 2 / pca.explained_variance_[i] for i, pc in enumerate(oszlopok))
    hatar = stats.chi2.ppf(0.975, df=len(oszlopok))
    return eredmeny.loc[d2 > hatar, "student_id"].tolist(), np.sqrt(d2), hatar


def szoras_pont(ax, eredmeny, x, y, arany, cim_szoveg):
    """Kétdimenziós vetület a passed szerint színezve, csoportközéppontokkal."""
    for csoport, szin in PASSED_SZINEK.items():
        resz = eredmeny[eredmeny["passed"] == csoport]
        ax.scatter(resz[x], resz[y], s=26, color=szin, alpha=0.7, edgecolor="white",
                   linewidth=0.5, label="{} (n = {})".format(csoport, len(resz)))
        ax.scatter(resz[x].mean(), resz[y].mean(), s=150, marker="X", color=szin,
                   edgecolor=SZOVEG_SZIN, linewidth=1, zorder=3)
    ax.axhline(0, color=RACS_SZIN, linewidth=1)
    ax.axvline(0, color=RACS_SZIN, linewidth=1)
    ax.legend(frameon=False, fontsize=8, title="passed", title_fontsize=8)
    ax_formaz(ax, cim_szoveg, "{} ({:.1%})".format(x, arany[PC.index(x)]),
              "{} ({:.1%})".format(y, arany[PC.index(y)]))


def abra(eredmeny, arany, tavolsagok):
    fig = plt.figure(figsize=(15, 11))

    ax3d = fig.add_subplot(2, 2, 1, projection="3d")
    for csoport, szin in PASSED_SZINEK.items():
        resz = eredmeny[eredmeny["passed"] == csoport]
        ax3d.scatter(resz["PC1"], resz["PC2"], resz["PC3"], s=22, color=szin, alpha=0.75,
                     edgecolor="white", linewidth=0.4, label="{} (n = {})".format(csoport, len(resz)))
        ax3d.scatter(*resz[PC].mean(), s=160, marker="X", color=szin, edgecolor=SZOVEG_SZIN,
                     linewidth=1, depthshade=False)
    ax3d.set_xlabel("PC1 ({:.1%})".format(arany[0]))
    ax3d.set_ylabel("PC2 ({:.1%})".format(arany[1]))
    ax3d.set_zlabel("PC3 ({:.1%})".format(arany[2]))
    ax3d.view_init(elev=20, azim=-60)
    ax3d.legend(frameon=False, fontsize=8, title="passed", title_fontsize=8, loc="upper left")
    ax3d.set_title("Három főkomponens (✕ = csoportközéppont)", loc="left", fontsize=11)

    szoras_pont(fig.add_subplot(2, 2, 2), eredmeny, "PC1", "PC3", arany, "PC1 – PC3 vetület")
    szoras_pont(fig.add_subplot(2, 2, 3), eredmeny, "PC2", "PC3", arany, "PC2 – PC3 vetület")

    ax = fig.add_subplot(2, 2, 4)
    szinek = [SZIN] * 3 + [SZIN2] * 3
    ax.barh(list(tavolsagok.index), tavolsagok.to_numpy(), color=szinek, alpha=0.85, height=0.6)
    for y, ertek in enumerate(tavolsagok):
        ax.text(ertek + 0.02, y, "{:.2f}".format(ertek), va="center", fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, tavolsagok.max() * 1.18)
    ax_formaz(ax, "A passed csoportok elkülönülése (kék: egy PC, narancs: több)",
              "középpontok távolsága a közös szórás egységében", "", racs="x")

    fig.suptitle("PCA három főkomponenssel – a megőrzött variancia {:.2%}".format(arany.sum()),
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "06_pca_3_komponens.png"), dpi=120)


def main():
    pd.set_option("display.width", 150)
    pd.set_option("display.max_columns", 20)
    df = beolvas()

    cim("PCA három komponenssel – az eredmény DataFrame-je")
    pca3, eredmeny3 = pca_3d(df)
    arany3 = pca3.explained_variance_ratio_
    print(eredmeny3.head(10).round(3).to_string(index=False))
    print("... ({} sor)".format(len(eredmeny3)))
    print()
    print("Magyarázott varianciaarány: PC1 = {:.2%}, PC2 = {:.2%}, PC3 = {:.2%}, együtt {:.2%}"
          .format(*arany3, arany3.sum()))

    pca2, eredmeny2 = pca_2d(df, JELLEMZOK)
    arany2 = pca2.explained_variance_ratio_

    cim("Összevetés a 3. feladattal: megőrzött variancia")
    print("  két komponens (3. feladat):  {:.2%}, kimarad {:.2%}".format(arany2.sum(), 1 - arany2.sum()))
    print("  három komponens:             {:.2%}, kimarad {:.2%}".format(arany3.sum(), 1 - arany3.sum()))
    print("A PC3 további {:.2f} százalékpontot ad, így a megoldás átlépi a 80%-os irányelvet.".format(
        100 * arany3[2]))

    cim("Összevetés a 3. feladattal: azonosak-e az első két komponens?")
    s3 = sulyok(pca3, JELLEMZOK)
    s2 = sulyok(pca2, JELLEMZOK)
    azonos = np.allclose(eredmeny3[["PC1", "PC2"]], eredmeny2[["PC1", "PC2"]])
    print(pd.concat({"3. feladat (2 PC)": s2, "6. feladat (3 PC)": s3}, axis=1)
          .round(3).to_string(na_rep="–"))
    print()
    print("A PC1 és a PC2 súlyai és pontszámai {} a 3. feladatéval.".format(
        "pontosan megegyeznek" if azonos else "eltérnek"))
    print("A PCA komponensei egymásra épülnek: a k-adik komponens a maradék variancia")
    print("legnagyobb irányát keresi, ezért egy újabb komponens megtartása a korábbiakat nem")
    print("változtatja meg, csak egy új, rájuk merőleges tengelyt ad hozzá.")

    cim("Mit mér a PC3?")
    rendezett = s3["PC3"].reindex(s3["PC3"].abs().sort_values(ascending=False).index)
    print(", ".join("{} ({:+.3f})".format(v, s) for v, s in rendezett.items()))
    print()
    print("A PC3 az óralátogatást állítja szembe az előzetes eredménnyel és a tanulási idővel:")
    print("magas értéket az kap, aki rendszeresen bejár az órákra, de az előzetes GPA-ja és a")
    print("tanulásra fordított ideje alacsonyabb („bejár, de kevésbé felkészült”), alacsonyat")
    print("az, aki jó előzetes eredményű és sokat tanul, de ritkábban jár órára.")

    cim("Elkülönülnek-e jobban a sikeres és sikertelen hallgatók?")
    print(eredmeny3.groupby("passed")[PC].agg(["mean", "std"]).round(3).to_string())
    print()
    tavolsagok = pd.Series({
        "PC1": elkulonules(eredmeny3, ["PC1"]),
        "PC2": elkulonules(eredmeny3, ["PC2"]),
        "PC3": elkulonules(eredmeny3, ["PC3"]),
        "PC1–PC2 (3. feladat)": elkulonules(eredmeny3, ["PC1", "PC2"]),
        "PC1–PC2–PC3": elkulonules(eredmeny3, PC),
    })
    z = standardizal(df, JELLEMZOK).assign(passed=df["passed"])
    tavolsagok["mind a 4 eredeti változó"] = elkulonules(z, JELLEMZOK)
    print("A csoportközéppontok távolsága a közös szórás egységében:")
    for nev, ertek in tavolsagok.items():
        print("  {:<26} {:.3f}".format(nev, ertek))
    print()
    print("Kétmintás t-próba komponensenként (yes vs no), csak tájékoztatásul:")
    for pc in PC:
        p = stats.ttest_ind(eredmeny3.loc[eredmeny3["passed"] == "yes", pc],
                            eredmeny3.loc[eredmeny3["passed"] == "no", pc]).pvalue
        print("  {}: p = {:.2g}".format(pc, p))
    print()
    print("A PC3 mentén a sikertelenek átlaga pozitív ({:+.2f}), a sikereseké negatív ({:+.2f}):"
          .format(*eredmeny3.groupby("passed")["PC3"].mean().loc[["no", "yes"]]))
    print("a sikertelenek között relatíve több a rendszeresen bejáró, de alacsonyabb GPA-jú")
    print("és kevesebbet tanuló hallgató. Ez a különbség kicsi, a PC3 egymagában gyengén")
    print("választ el (a PC1-nél jóval gyengébben). A harmadik komponenssel a térbeli")
    print("elkülönülés {:.2f}-ről {:.2f}-re nő, és így már szinte eléri a mind a négy eredeti".format(
        tavolsagok["PC1–PC2 (3. feladat)"], tavolsagok["PC1–PC2–PC3"]))
    print("változóval mérhető értéket ({:.2f}). A pontfelhők térben is nagyrészt átfedik".format(
        tavolsagok["mind a 4 eredeti változó"]))
    print("egymást, éles szétválás nincs.")

    cim("Távol eső hallgatók: 2 és 3 komponens")
    tav2, _, hatar2 = tavoliak(eredmeny3, pca3, ["PC1", "PC2"])
    tav3, d3, hatar3 = tavoliak(eredmeny3, pca3, PC)
    print("  2 PC (χ²(2) határ = {:.2f}): {}".format(hatar2, ", ".join(tav2)))
    print("  3 PC (χ²(3) határ = {:.2f}): {}".format(hatar3, ", ".join(tav3)))
    print()
    print("Az S055 három komponensnél is kiugrik (skálázott távolság {:.2f}), őt a változók".format(
        d3[eredmeny3["student_id"] == "S055"].iloc[0]))
    print("szokatlan kombinációja minden nézetben elkülöníti. Az S006 a 3D-ben már a határon")
    print("belül van: a PC3 mentén átlagos, és a három dimenzióhoz tartozó határ magasabb.")

    cim("A megfigyelések összefoglalása")
    print("1. A három komponens a variancia {:.2%}-át őrzi meg (két komponens: {:.2%}); csak".format(
        arany3.sum(), arany2.sum()))
    print("   {:.2%} marad ki, így a 80%-os irányelv teljesül.".format(1 - arany3.sum()))
    print("2. A PC1 és a PC2 a 3. feladattal azonos; a PC3 egy új, tőlük független tengely,")
    print("   amely az óralátogatást a GPA-val és a tanulási idővel állítja szembe.")
    print("3. A passed szerinti elkülönülést továbbra is főként a PC1 hordozza. A PC3")
    print("   kismértékben javít ({:.2f} → {:.2f}), de a csoportok térben is erősen átfednek.".format(
        tavolsagok["PC1–PC2 (3. feladat)"], tavolsagok["PC1–PC2–PC3"]))
    print("4. Ez megerősíti a 3. feladat megjegyzését: a csoportokat megkülönböztető eltérés")
    print("   egy része a kihagyott komponensben volt, de a négy változó alapján sem válik el")
    print("   élesen a két csoport, a sikerességet a mért tanulási jellemzők csak részben írják le.")
    print("5. A 3D ábra kevésbé áttekinthető; a nézőponttól függően más-más átfedés látszik,")
    print("   ezért érdemes a síkvetületeket (PC1–PC3, PC2–PC3) is megnézni.")

    abra(eredmeny3, arany3, tavolsagok)
    plt.show()


if __name__ == "__main__":
    main()
