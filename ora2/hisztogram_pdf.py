# -*- coding: utf-8 -*-
"""Hisztogram (empirikus eloszlás) és elméleti normális sűrűségfüggvény (PDF).

1000 elemű normális eloszlású mintákat generálunk, kirajzoljuk a
hisztogramjukat, és rárajzoljuk az elméleti norm.pdf görbét.

Megfigyelés: az átlag (mu) a görbe helyét változtatja, a szórás (sigma)
pedig az alakját: kisebb szórásnál keskenyebb és magasabb, nagyobb
szórásnál szélesebb és laposabb a görbe.
"""

import os

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

MINTA_MERET = 1000
X_TENGELY = np.linspace(0, 200, 500)

# Kategorikus színek rögzített sorrendben
SZINEK = ("#2a78d6", "#eb6834", "#1baf7a")

# Az egyes ábrarészek: cím és a kirajzolandó (mu, sigma) párok
ABRAK = [
    ("Alapeset: mu = 100, sigma = 15", [(100, 15)]),
    ("mu változik (sigma = 10)", [(60, 10), (100, 10), (140, 10)]),
    ("sigma változik (mu = 100)", [(100, 5), (100, 10), (100, 25)]),
]


def rajzol(ax, cim, parameterek):
    """Egy ábrarészre kirajzolja a minták hisztogramját és az elméleti PDF-et."""
    for szin, (mu, sigma) in zip(SZINEK, parameterek):
        x = np.random.normal(mu, sigma, MINTA_MERET)
        ax.hist(x, bins=30, density=True, alpha=0.35, color=szin)
        y = norm.pdf(X_TENGELY, mu, sigma)
        ax.plot(X_TENGELY, y, color=szin, linewidth=2,
                label="mu = {}, sigma = {}".format(mu, sigma))

    ax.set_title(cim, loc="left", fontsize=11)
    ax.set_xlim(0, 200)
    ax.set_xlabel("érték")
    ax.set_ylabel("sűrűség")
    ax.grid(axis="y", color="#e5e4df", linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)
    if len(parameterek) > 1:
        ax.legend(frameon=False, fontsize=9)


def main():
    fig, axes = plt.subplots(3, 1, figsize=(9, 11))
    for ax, (cim, parameterek) in zip(axes, ABRAK):
        rajzol(ax, cim, parameterek)

    fig.suptitle("Normális eloszlás: hisztogram és sűrűségfüggvény", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "hisztogram_pdf.png"), dpi=120)
    plt.show()


if __name__ == "__main__":
    main()
