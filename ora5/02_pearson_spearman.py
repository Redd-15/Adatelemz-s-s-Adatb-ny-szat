# -*- coding: utf-8 -*-
"""2. Pearson- és Spearman-korreláció összehasonlítása.

Bemenet: student_performance_imputed.csv

Az 1. feladat változópárjaira (X – exam_score) kiszámítjuk a kovarianciát,
a Pearson-féle korrelációs együtthatót és a Spearman-féle rangkorrelációs
együtthatót, majd értelmezzük az előjelüket, abszolút értéküket és az
egymáshoz viszonyított eltérésüket.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_imputed.csv")

CEL = "exam_score"
MAGYARAZO = ["study_hours", "attendance", "previous_gpa", "assignments_completed"]

# ekkora |Pearson − Spearman| eltérés alatt a két mutatót hasonlónak tekintjük
ELTERES_HATAR = 0.05

SZIN = "#2a78d6"
SZIN2 = "#eb6834"
SZOVEG_SZIN = "#0b0b0b"
RACS_SZIN = "#e5e4df"


def cim(szoveg):
    """Szakaszcím a kimenetben."""
    print()
    print("=" * 70)
    print(szoveg)
    print("=" * 70)


def beolvas():
    return pd.read_csv(BEMENET, sep=";", encoding="utf-8")


def ax_formaz(ax, cim_szoveg, xlabel, ylabel):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim_szoveg, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


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


def mutatok(df):
    """Kovariancia, Pearson és Spearman minden változópárra."""
    sorok = []
    for valtozo in MAGYARAZO:
        x, y = df[valtozo], df[CEL]
        pearson = stats.pearsonr(x, y)
        spearman = stats.spearmanr(x, y)
        sorok.append({
            "változó": valtozo,
            "kovariancia": x.cov(y),
            "pearson_r": pearson.statistic,
            "pearson_p": pearson.pvalue,
            "spearman_rho": spearman.statistic,
            "spearman_p": spearman.pvalue,
            "eltérés": spearman.statistic - pearson.statistic,
        })
    return pd.DataFrame(sorok)


def abra(tabla):
    fig, ax = plt.subplots(figsize=(10, 5))
    pozicio = np.arange(len(tabla))
    szelesseg = 0.38
    for eltolas, oszlop, szin, felirat in (
            (-szelesseg / 2, "pearson_r", SZIN, "Pearson r"),
            (szelesseg / 2, "spearman_rho", SZIN2, "Spearman ρ")):
        ax.bar(pozicio + eltolas, tabla[oszlop], width=szelesseg, color=szin,
               alpha=0.85, label=felirat)
        for x, ertek in zip(pozicio + eltolas, tabla[oszlop]):
            ax.text(x, ertek + 0.01, "{:.3f}".format(ertek), ha="center", fontsize=9,
                    color=SZOVEG_SZIN)
    ax.set_xticks(pozicio)
    ax.set_xticklabels(tabla["változó"])
    ax.set_ylim(0, max(tabla["pearson_r"].max(), tabla["spearman_rho"].max()) * 1.2)
    ax.legend(frameon=False)
    ax_formaz(ax, "Korreláció az exam_score-ral: Pearson és Spearman", "", "együttható")
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "02_pearson_spearman.png"), dpi=120)


def main():
    pd.set_option("display.width", 130)
    df = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    cim("Kovariancia, Pearson- és Spearman-együttható (X – exam_score)")
    tabla = mutatok(df)
    print(tabla.to_string(index=False, formatters={
        "kovariancia": "{:.3f}".format,
        "pearson_r": "{:.3f}".format,
        "pearson_p": "{:.2e}".format,
        "spearman_rho": "{:.3f}".format,
        "spearman_p": "{:.2e}".format,
        "eltérés": "{:+.3f}".format,
    }))
    print()
    print("A kovariancia előjele a kapcsolat irányát mutatja, nagysága viszont a változók")
    print("mértékegységétől függ (pl. previous_gpa 1–5 skála, attendance 0–100%), ezért a")
    print("párok egymással nem hasonlíthatók össze. A korreláció a kovariancia standardizált,")
    print("[-1; 1] közé eső változata, így a kapcsolatok erőssége már összevethető.")

    cim("A korreláció előjele és abszolút értéke")
    for _, sor in tabla.iterrows():
        print("  {:<22} r = {:>6.3f} → {} irányú, {} kapcsolat; ρ = {:>6.3f} → {}".format(
            sor["változó"], sor["pearson_r"],
            "pozitív" if sor["pearson_r"] > 0 else "negatív", erosseg(sor["pearson_r"]),
            sor["spearman_rho"], erosseg(sor["spearman_rho"])))
    print()
    print("Pozitív előjel: a változó nagyobb értékeihez átlagosan nagyobb vizsgapontszám")
    print("tartozik. Az abszolút érték a kapcsolat szorosságát mutatja (0 = nincs, 1 = tökéletes).")
    print("Mind a négy p-érték 0.05 alatt van, tehát a kapcsolatok szignifikánsan eltérnek 0-tól."
          if (tabla[["pearson_p", "spearman_p"]] < 0.05).all().all()
          else "Nem minden p-érték van 0.05 alatt, egyes kapcsolatok nem szignifikánsak.")

    cim("1. Melyik változó mutatja a legerősebb kapcsolatot a vizsgaeredménnyel?")
    legerosebb_p = tabla.loc[tabla["pearson_r"].abs().idxmax()]
    legerosebb_s = tabla.loc[tabla["spearman_rho"].abs().idxmax()]
    print("Pearson szerint:  {} (r = {:.3f})".format(
        legerosebb_p["változó"], legerosebb_p["pearson_r"]))
    print("Spearman szerint: {} (ρ = {:.3f})".format(
        legerosebb_s["változó"], legerosebb_s["spearman_rho"]))
    print("Sorrend |r| szerint: " + " > ".join(
        tabla.sort_values("pearson_r", key=abs, ascending=False)["változó"]))
    print("Sorrend |ρ| szerint: " + " > ".join(
        tabla.sort_values("spearman_rho", key=abs, ascending=False)["változó"]))

    cim("2. A Pearson- és Spearman-együttható hasonló eredményt ad-e?")
    for _, sor in tabla.iterrows():
        print("  {:<22} |ρ − r| = {:.3f} → {}".format(
            sor["változó"], abs(sor["eltérés"]),
            "hasonló" if abs(sor["eltérés"]) < ELTERES_HATAR else "érdemi eltérés"))
    print()
    print("Igen: minden párnál {:.2f}-nál kisebb az eltérés, az előjel és a sorrend is egyezik."
          .format(ELTERES_HATAR) if (tabla["eltérés"].abs() < ELTERES_HATAR).all()
          else "Nem minden párnál: ahol érdemi eltérés van, a kapcsolat alakját meg kell nézni.")
    print("A változók kapcsolata tehát közel lineáris, és nincs olyan kiugró érték, amely")
    print("az egyik mutatót jelentősen torzítaná.")

    cim("3. Mit jelezhet, ha a két együttható jelentősen eltér?")
    print("- Nemlineáris, de monoton kapcsolat: a Spearman (rangok alapján) erősebb kapcsolatot")
    print("  mutat, mint a Pearson, mert az csak a lineáris komponenst méri.")
    print("- Kiugró értékek: a Pearson érzékeny a szélsőséges pontokra (felfelé vagy lefelé")
    print("  torzulhat), a Spearman a rangok miatt robusztusabb.")
    print("- Ferde eloszlás vagy erős csoportosulás (pl. sok azonos érték, plafonhatás):")
    print("  a rangsorolás másképp kezeli, mint a nyers értékeket.")
    print("Ilyenkor a pontdiagram megtekintése elengedhetetlen a helyes értelmezéshez.")

    abra(tabla)
    plt.show()


if __name__ == "__main__":
    main()
