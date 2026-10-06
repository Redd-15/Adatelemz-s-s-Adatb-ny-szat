# -*- coding: utf-8 -*-
"""4. Korrelációs mátrix.

Bemenet: student_performance_imputed.csv

Elkészítjük a numerikus változók Pearson-féle korrelációs mátrixát, és
annotált heatmapen jelenítjük meg. Meghatározzuk a legerősebb kapcsolatot,
a pozitív és negatív kapcsolatokat, az esetleg redundáns változókat, és
azokat a párokat, amelyek további grafikus vizsgálatot igényelnek.
"""

import os
from itertools import combinations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_imputed.csv")

NUMERIKUS = ["study_hours", "attendance", "previous_gpa",
             "assignments_completed", "exam_score"]

REDUNDANS_HATAR = 0.7     # e fölött a két változó részben ugyanazt méri
ELTERES_HATAR = 0.05      # |Pearson − Spearman| e fölött nemlinearitásra vagy kiugróra utalhat
FIGYELEM_HATAR = 0.3      # legalább közepes kapcsolat

SZOVEG_SZIN = "#0b0b0b"


def cim(szoveg):
    """Szakaszcím a kimenetben."""
    print()
    print("=" * 70)
    print(szoveg)
    print("=" * 70)


def beolvas():
    return pd.read_csv(BEMENET, sep=";", encoding="utf-8")


def erosseg(r):
    """A korreláció abszolút értékének szöveges minősítése."""
    a = abs(r)
    if a < 0.1:
        return "elhanyagolható"
    if a < 0.3:
        return "gyenge"
    if a < 0.7:
        return "közepes"
    return "erős"


def parok_tablaja(pearson, spearman):
    """A mátrix felső háromszöge párok listájaként, |r| szerint csökkenő sorrendben."""
    sorok = []
    for a, b in combinations(pearson.columns, 2):
        r = pearson.loc[a, b]
        sorok.append({
            "változó_1": a,
            "változó_2": b,
            "pearson_r": r,
            "spearman_rho": spearman.loc[a, b],
            "irány": "pozitív" if r > 0 else "negatív",
            "erősség": erosseg(r),
        })
    tabla = pd.DataFrame(sorok)
    return tabla.sort_values("pearson_r", key=abs, ascending=False).reset_index(drop=True)


def heatmap(korr):
    fig, ax = plt.subplots(figsize=(8, 6.5))
    kep = ax.imshow(korr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    n = len(korr)
    for i in range(n):
        for j in range(n):
            ertek = korr.iat[i, j]
            # sötét cellában fehér, világosban fekete felirat
            ax.text(j, i, "{:.2f}".format(ertek), ha="center", va="center", fontsize=10,
                    color="white" if abs(ertek) > 0.6 else SZOVEG_SZIN)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(korr.columns, rotation=30, ha="right")
    ax.set_yticklabels(korr.index)
    ax.set_xticks(np.arange(-0.5, n), minor=True)
    ax.set_yticks(np.arange(-0.5, n), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="both", length=0)
    for oldal in ax.spines.values():
        oldal.set_visible(False)
    szinskala = fig.colorbar(kep, ax=ax, shrink=0.85)
    szinskala.set_label("Pearson r")
    ax.set_title("Numerikus változók Pearson-féle korrelációs mátrixa", loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "04_korrelacios_matrix.png"), dpi=120)


def main():
    pd.set_option("display.width", 130)
    pd.set_option("display.max_columns", 20)
    df = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    pearson = df[NUMERIKUS].corr(method="pearson")
    spearman = df[NUMERIKUS].corr(method="spearman")

    cim("Pearson-féle korrelációs mátrix")
    print(pearson.round(3).to_string())

    cim("Változópárok |r| szerint csökkenő sorrendben")
    tabla = parok_tablaja(pearson, spearman)
    print(tabla.to_string(index=False, formatters={
        "pearson_r": "{:.3f}".format, "spearman_rho": "{:.3f}".format}))

    cim("Mely változópár kapcsolata a legerősebb?")
    elso = tabla.iloc[0]
    print("{} – {}: r = {:.3f} ({} {} kapcsolat)".format(
        elso["változó_1"], elso["változó_2"], elso["pearson_r"],
        elso["erősség"], elso["irány"]))
    magyarazok = tabla[(tabla["változó_1"] != "exam_score") & (tabla["változó_2"] != "exam_score")]
    m = magyarazok.iloc[0]
    print("A magyarázó változók egymás közötti legerősebb kapcsolata: {} – {}, r = {:.3f}".format(
        m["változó_1"], m["változó_2"], m["pearson_r"]))

    cim("Pozitív és negatív kapcsolatok")
    for irany in ("pozitív", "negatív"):
        resz = tabla[tabla["irány"] == irany]
        print("{} ({} db):".format(irany.capitalize(), len(resz)))
        for _, sor in resz.iterrows():
            print("  {:<22} – {:<22} r = {:>6.3f}  ({})".format(
                sor["változó_1"], sor["változó_2"], sor["pearson_r"], sor["erősség"]))

    cim("Vannak-e erősen korreláló, részben redundáns változók?")
    redundans = tabla[tabla["pearson_r"].abs() >= REDUNDANS_HATAR]
    if redundans.empty:
        print("Nincs: a legnagyobb |r| = {:.3f}, egyik pár sem éri el a {:.1f}-et.".format(
            tabla["pearson_r"].abs().max(), REDUNDANS_HATAR))
        print("A magyarázó változók egymással legfeljebb gyengén korrelálnak (|r| ≤ {:.2f}),"
              .format(magyarazok["pearson_r"].abs().max()))
        print("tehát mindegyik más-más információt hordoz, egyik sem hagyható el a többi miatt.")
    else:
        print("Igen, a következő párok részben ugyanazt mérik:")
        print(redundans.to_string(index=False))

    cim("Mely kapcsolatok igényelnek további grafikus vizsgálatot?")
    tabla["eltérés"] = (tabla["spearman_rho"] - tabla["pearson_r"]).abs()
    figyelendo = tabla[(tabla["pearson_r"].abs() >= FIGYELEM_HATAR)
                       | (tabla["eltérés"] >= ELTERES_HATAR)]
    for _, sor in figyelendo.iterrows():
        okok = []
        if abs(sor["pearson_r"]) >= FIGYELEM_HATAR:
            okok.append("legalább közepes kapcsolat, az alakját és a kiugrókat érdemes megnézni")
        if sor["eltérés"] >= ELTERES_HATAR:
            okok.append("Pearson és Spearman eltér ({:.3f} vs {:.3f}) → nemlinearitás vagy kiugró?"
                        .format(sor["pearson_r"], sor["spearman_rho"]))
        print("  {} – {}: {}".format(sor["változó_1"], sor["változó_2"], "; ".join(okok)))
    print()
    print("Emellett a study_hours – assignments_completed gyenge negatív kapcsolata (r = {:.3f})"
          .format(pearson.loc["study_hours", "assignments_completed"]))
    print("meglepő (több tanulás, kevesebb beadott feladat), ezt is érdemes pontdiagramon megnézni.")
    print("A korrelációs együttható egyetlen szám: a kapcsolat alakját, a kiugró értékeket és a")
    print("csoportosulásokat csak a pontdiagram mutatja meg.")

    heatmap(pearson)
    plt.show()


if __name__ == "__main__":
    main()
