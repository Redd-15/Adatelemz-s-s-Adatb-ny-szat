# -*- coding: utf-8 -*-
"""Eloszlások összehasonlítása.

1000 elemű mintát generálunk normális, egyenletes és exponenciális
eloszlással, hisztogramon összevetjük az alakjukat, és kiszámítjuk az
átlagot, a mediánt és a szórást.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

MINTA_MERET = 1000

# Kategorikus színek rögzített sorrendben
SZINEK = ("#2a78d6", "#eb6834", "#1baf7a")
ATLAG_SZIN = "#0b0b0b"
MEDIAN_SZIN = "#52514e"


def mintak_generalasa(meret=MINTA_MERET):
    """Visszaadja a három mintát (név, adatok) párok listájaként."""
    return [
        ("Normális (mu = 0, sigma = 1)", np.random.normal(0, 1, meret)),
        ("Egyenletes (0 és 10 között)", np.random.uniform(0, 10, meret)),
        ("Exponenciális (scale = 1)", np.random.exponential(scale=1, size=meret)),
    ]


def main():
    mintak = mintak_generalasa()

    print("{:>30} {:>8} {:>8} {:>8}".format("eloszlás", "átlag", "medián", "szórás"))
    for nev, x in mintak:
        print("{:>30} {:>8.3f} {:>8.3f} {:>8.3f}".format(
            nev, x.mean(), np.median(x), x.std()))
    print()
    print("Megfigyelések:")
    print("  - Normális: harang alakú, szimmetrikus, átlag = medián.")
    print("  - Egyenletes: lapos, minden érték nagyjából egyformán gyakori,")
    print("    szimmetrikus, átlag = medián (kb. 5).")
    print("  - Exponenciális: jobbra ferde, hosszú jobb oldali farok;")
    print("    az átlag nagyobb a mediánnál, mert a nagy értékek felhúzzák.")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, szin, (nev, x) in zip(axes, SZINEK, mintak):
        ax.hist(x, bins=30, density=True, color=szin, alpha=0.6)
        ax.axvline(x.mean(), color=ATLAG_SZIN, linewidth=2,
                   label="átlag = {:.2f}".format(x.mean()))
        ax.axvline(np.median(x), color=MEDIAN_SZIN, linewidth=2, linestyle="--",
                   label="medián = {:.2f}".format(np.median(x)))
        ax.set_title("{}\nszórás = {:.2f}".format(nev, x.std()), loc="left", fontsize=11)
        ax.set_xlabel("érték")
        ax.set_ylabel("sűrűség")
        ax.grid(axis="y", color="#e5e4df", linewidth=0.8)
        ax.set_axisbelow(True)
        for oldal in ("top", "right"):
            ax.spines[oldal].set_visible(False)
        # hely a jelmagyarázatnak az oszlopok felett
        ax.set_ylim(0, ax.get_ylim()[1] * 1.3)
        ax.legend(frameon=False, fontsize=9, loc="upper right")

    fig.suptitle("Eloszlások összehasonlítása (n = {})".format(MINTA_MERET), fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "eloszlasok.png"), dpi=120)
    plt.show()


if __name__ == "__main__":
    main()
