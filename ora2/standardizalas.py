# -*- coding: utf-8 -*-
"""Standardizálás (z-score).

Minden értékből kivonjuk a minta átlagát, majd elosztjuk a minta szórásával.
A standardizált adatsor átlaga 0, szórása 1, de az eloszlás alakja nem
változik: a standardizálás nem teszi normális eloszlásúvá az adatokat.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

MU = 70
SIGMA = 10
MINTA_MERET = 1000

SZINEK = ("#2a78d6", "#eb6834")


def standardizal(x):
    """z = (x - átlag) / szórás"""
    return (x - x.mean()) / x.std()


def ax_formaz(ax, cim, xlabel):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("sűrűség")
    ax.grid(axis="y", color="#e5e4df", linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def main():
    # a) A 85 pontos eredmény z-score-ja
    z = (85 - MU) / SIGMA
    print("a) z = (85 - {}) / {} = {:.2f}".format(MU, SIGMA, z))
    print("   A 85 pont {:.2f} szórásnyira van az átlag felett.".format(z))
    print()

    # b) Negatív z-score
    z_negativ = (55 - MU) / SIGMA
    print("b) Negatív z-score: az érték az átlag ALATT van.")
    print("   Pl. 55 pont: z = (55 - {}) / {} = {:.2f},".format(MU, SIGMA, z_negativ))
    print("   vagyis 1,5 szórásnyival az átlag alatt.")
    print()

    # c) Adatsor standardizálása és ellenőrzése
    normalis = np.random.normal(MU, SIGMA, MINTA_MERET)
    exponencialis = np.random.exponential(scale=10, size=MINTA_MERET)
    mintak = [
        ("Normális (mu = 70, sigma = 10)", normalis),
        ("Exponenciális (scale = 10)", exponencialis),
    ]

    print("c) Standardizálás előtt és után:")
    print("{:>32} | {:>8} {:>8} | {:>8} {:>8}".format(
        "", "átlag", "szórás", "z átlag", "z szórás"))
    for nev, x in mintak:
        z_minta = standardizal(x)
        # a kerekítési hiba (pl. -1e-16) ne "-0.000"-ként jelenjen meg
        z_atlag = round(z_minta.mean(), 10) + 0.0
        print("{:>32} | {:>8.3f} {:>8.3f} | {:>8.3f} {:>8.3f}".format(
            nev, x.mean(), x.std(), z_atlag, z_minta.std()))
    print()
    print("   Mindkét standardizált adatsor átlaga 0, szórása 1, de az")
    print("   exponenciális minta standardizálás után is ferde marad.")

    # Ábra: eredeti és standardizált hisztogramok
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for sor, (szin, (nev, x)) in enumerate(zip(SZINEK, mintak)):
        axes[sor, 0].hist(x, bins=30, density=True, color=szin, alpha=0.6)
        ax_formaz(axes[sor, 0], "{}: eredeti".format(nev), "érték")
        axes[sor, 1].hist(standardizal(x), bins=30, density=True, color=szin, alpha=0.6)
        ax_formaz(axes[sor, 1], "{}: standardizált".format(nev), "z-score")

    fig.suptitle("Standardizálás: a skála változik, az alak nem", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "standardizalas.png"), dpi=120)
    plt.show()


if __name__ == "__main__":
    main()
