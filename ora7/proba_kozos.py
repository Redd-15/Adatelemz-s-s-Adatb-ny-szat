# -*- coding: utf-8 -*-
"""A 7. óra hipotézisvizsgálati feladatainak közös segédfüggvényei.

Beolvasás (tisztított, de NEM imputált adatok), a döntés kiírása és a
normalitásvizsgálat (Shapiro–Wilk-próba).
"""

import os

import pandas as pd
from scipy import stats

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_cleaned.csv")

ALFA = 0.05
SEED = 42          # a véletlen mintavétel reprodukálhatóságáért


def cim(szoveg):
    """Szakaszcím a kimenetben."""
    print()
    print("=" * 70)
    print(szoveg)
    print("=" * 70)


def beolvas():
    """A tisztított adatok; a hiányzó értékek megmaradnak (nincs pótlás)."""
    df = pd.read_csv(BEMENET, sep=";", encoding="utf-8")
    df["passed"] = df["passed"].str.strip().str.lower()
    return df


def dontes(p, alfa=ALFA):
    """A p-érték alapján hozott döntés szövege."""
    if p <= alfa:
        return "p = {:.4g} ≤ α = {} → H0-t ELUTASÍTJUK (statisztikailag szignifikáns)".format(p, alfa)
    return "p = {:.4g} > α = {} → H0-t NEM utasítjuk el (nem szignifikáns)".format(p, alfa)


def normalitas(ertekek, nev):
    """Shapiro–Wilk-próba; H0: a sokasági eloszlás normális. Igaz, ha nem utasítjuk el."""
    eredmeny = stats.shapiro(ertekek)
    rendben = eredmeny.pvalue > ALFA
    print("  {:<28} n = {:>3}, W = {:.4f}, p = {:.4f} → {}".format(
        nev, len(ertekek), eredmeny.statistic, eredmeny.pvalue,
        "a normalitás nem vethető el" if rendben else "a normalitás elvetendő"))
    return rendben
