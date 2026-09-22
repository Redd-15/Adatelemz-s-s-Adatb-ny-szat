# -*- coding: utf-8 -*-
"""1. Az adathalmaz szerkezetének és tartalmának megismerése.

A student_performance_raw.csv beolvasása pandas DataFrame-be, majd a
szerkezet és a tartalom feltárása (head, tail, shape, columns, info,
describe, nunique, value_counts) és grafikus feltáró elemzés.

Az elválasztójelet a program maga állapítja meg (';' vagy ','), mert az
adathalmaz véglegesen pontosvesszős, a jelenlegi mentés viszont még
vesszős. A tizedesvesszős értékek ('3,2') szándékos hibák, ezeket a
számmá alakításnál kezeljük.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

MAPPA = os.path.dirname(os.path.abspath(__file__))
CSV_UT = os.path.join(MAPPA, "student_performance_clean.csv")

NUMERIKUS = ["study_hours", "attendance", "previous_gpa",
             "assignments_completed", "exam_score"]
KATEGORIKUS = ["programme", "passed"]

SZIN = "#2a78d6"
GORBE_SZIN = "#0b0b0b"
RACS_SZIN = "#e5e4df"


def cim(szoveg):
    """Szakaszcím a kimenetben."""
    print()
    print("=" * 70)
    print(szoveg)
    print("=" * 70)


def elvalasztojel():
    """Megállapítja a fájl elválasztójelét a fejléc alapján (';' vagy ',')."""
    with open(CSV_UT, encoding="utf-8") as fajl:
        fejlec = fajl.readline()
    return ";" if fejlec.count(";") > fejlec.count(",") else ","


def beolvas():
    """Beolvassa a nyers adatállományt (minden oszlop úgy, ahogy a fájlban van)."""
    sep = elvalasztojel()
    print("Elválasztójel: '{}'".format(sep))
    return pd.read_csv(CSV_UT, sep=sep, encoding="utf-8")


def szammaalakit(df):
    """A numerikus oszlopok számmá alakított másolata (csak az ábrákhoz).

    A nyers fájlban szöveges értékek is vannak ('ten', 'seven', '3,2'),
    ezért ezek az oszlopok szöveges (str) típusúak. Az errors='coerce' a
    nem értelmezhető értékeket NaN-ra cseréli.
    """
    szamok = df[NUMERIKUS].copy()
    for oszlop in NUMERIKUS:
        szamok[oszlop] = pd.to_numeric(
            szamok[oszlop].astype("string").str.replace(",", ".", regex=False),
            errors="coerce")
    return szamok


def ax_formaz(ax, cim_szoveg, xlabel, ylabel):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim_szoveg, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def numerikus_abrak(szamok):
    """Hisztogram és sűrűségfüggvény (KDE) a numerikus változókra."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for ax, oszlop in zip(axes.ravel(), NUMERIKUS):
        ertekek = szamok[oszlop].dropna().to_numpy()
        ax.hist(ertekek, bins=20, density=True, color=SZIN, alpha=0.55)

        # KDE: a minta alapján becsült sűrűségfüggvény
        surusegbecsles = gaussian_kde(ertekek)
        x_axis = np.linspace(ertekek.min(), ertekek.max(), 300)
        ax.plot(x_axis, surusegbecsles(x_axis), color=GORBE_SZIN, linewidth=2)

        hianyzo = szamok[oszlop].isna().sum()
        ax_formaz(ax, "{}\nn = {}, hiányzó/érvénytelen = {}".format(
            oszlop, len(ertekek), hianyzo), oszlop, "sűrűség")

    axes.ravel()[-1].axis("off")
    fig.suptitle("Numerikus változók eloszlása (hisztogram + KDE)", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "01_numerikus_eloszlasok.png"), dpi=120)


def kategorikus_abrak(df):
    """Oszlopdiagram a kategorikus változók gyakoriságáról."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, oszlop in zip(axes, KATEGORIKUS):
        gyakorisag = df[oszlop].value_counts(dropna=False)
        cimkek = [("hiányzó" if pd.isna(ertek) else str(ertek))
                  for ertek in gyakorisag.index]
        pozicio = range(len(gyakorisag))
        ax.bar(pozicio, gyakorisag.to_numpy(), color=SZIN, alpha=0.8, width=0.7)
        for x, ertek in zip(pozicio, gyakorisag.to_numpy()):
            ax.text(x, ertek + 0.8, str(ertek), ha="center", fontsize=9,
                    color=GORBE_SZIN)
        ax.set_xticks(list(pozicio))
        ax.set_xticklabels(cimkek, rotation=30, ha="right", fontsize=9)
        ax_formaz(ax, "{} ({} különböző érték)".format(oszlop, df[oszlop].nunique()),
                  "", "gyakoriság")

    fig.suptitle("Kategorikus változók gyakorisága (nyers, tisztítás előtt)",
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "01_kategorikus_gyakorisagok.png"), dpi=120)


def main():
    pd.set_option("display.width", 120)
    pd.set_option("display.max_columns", 20)

    df = beolvas()

    cim("Első 5 sor (df.head())")
    print(df.head())

    cim("Utolsó 5 sor (df.tail())")
    print(df.tail())

    cim("Méret (df.shape)")
    print("{} sor, {} oszlop".format(*df.shape))

    cim("Oszlopnevek (df.columns)")
    print(list(df.columns))

    cim("Adattípusok és hiányzó értékek (df.info())")
    df.info()

    cim("Numerikus változók statisztikái (df.describe())")
    # A nyersen beolvasott oszlopok egy része szöveges, ezért a describe
    # a számmá alakított másolaton fut.
    szamok = szammaalakit(df)
    print(szamok.describe().round(2))

    cim("Kategorikus változók (df.nunique(), df.value_counts())")
    print("Különböző értékek száma oszloponként:")
    print(df.nunique())
    for oszlop in ["programme", "passed"]:
        print()
        print("{} gyakorisága:".format(oszlop))
        print(df[oszlop].value_counts(dropna=False))

    cim("Első észrevételek a nyers adatokról")
    print("- A numerikus oszlopok egy része szöveges (str) típusú, mert")
    print("  szöveges értékeket is tartalmaz ('ten', 'seven', '3,2').")
    print("- A programme oszlopban ugyanaz a képzés többféle néven szerepel")
    print("  (kis-nagybetű, rövidítés: CS, ME, felesleges szóközök).")
    print("- Minden numerikus oszlopban van hiányzó érték.")
    print("- Vannak lehetetlen értékek: negatív tanulási idő, 100% feletti")
    print("  és negatív óralátogatás, 100 feletti vizsgaeredmény.")
    print("- A student_id nem egyedi: {} rekordban {} különböző azonosító van.".format(
        len(df), df["student_id"].nunique()))

    numerikus_abrak(szamok)
    kategorikus_abrak(df)
    plt.show()


if __name__ == "__main__":
    main()
