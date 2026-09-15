# -*- coding: utf-8 -*-
"""Kvantilis meghatározása normális eloszlás esetén.

Egy vizsgán a pontszámok normális eloszlást követnek (mu = 70, sigma = 10).
Feladat: milyen pontszám alatt található a hallgatók 90%-a?

A kvantilisfüggvény (PPF) a CDF inverze: megadja azt az értéket, amelynél
az eloszlás értékei a megadott valószínűséggel kisebbek vagy egyenlők.
"""

import os

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

MU = 70
SIGMA = 10
MINTA_MERET = 1000

# (valószínűség, név) párok a nevezetes percentilisekhez
PERCENTILISEK = [
    (0.25, "Q1"),
    (0.50, "medián"),
    (0.75, "Q3"),
    (0.90, "90. percentilis"),
]

SZIN = "#2a78d6"
GORBE_SZIN = "#52514e"
SEGED_SZIN = "#8a8984"
SZOVEG_SZIN = "#0b0b0b"


def ax_formaz(ax, cim, ylabel):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim, loc="left", fontsize=11)
    ax.set_xlim(MU - 4 * SIGMA, MU + 4 * SIGMA)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("pontszám")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color="#e5e4df", linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def main():
    # A feladat: 90%-os kvantilis
    q = norm.ppf(0.90, loc=MU, scale=SIGMA)
    print("A hallgatók 90%-a {:.2f} pont alatt van.".format(q))
    print("Ellenőrzés: norm.cdf({:.2f}) = {:.4f}".format(
        q, norm.cdf(q, loc=MU, scale=SIGMA)))
    print()

    # Nevezetes percentilisek: elméleti (PPF) és egy 1000 elemű mintából
    x = np.random.normal(MU, SIGMA, MINTA_MERET)
    print("{:>16} {:>10} {:>10}".format("percentilis", "elméleti", "mintából"))
    for p, nev in PERCENTILISEK:
        print("{:>16} {:>10.2f} {:>10.2f}".format(
            nev, norm.ppf(p, loc=MU, scale=SIGMA), np.percentile(x, p * 100)))
    print()
    print("A medián megegyezik a várható értékkel: {} = {}".format(
        norm.ppf(0.5, loc=MU, scale=SIGMA), MU))

    x_axis = np.linspace(MU - 4 * SIGMA, MU + 4 * SIGMA, 500)
    fig, (ax_pdf, ax_cdf) = plt.subplots(1, 2, figsize=(12, 5))

    # Bal oldal: sűrűségfüggvény, a q alatti 90% besatírozva
    ax_pdf.plot(x_axis, norm.pdf(x_axis, MU, SIGMA), color=GORBE_SZIN, linewidth=2)
    x_resz = x_axis[x_axis <= q]
    ax_pdf.fill_between(x_resz, norm.pdf(x_resz, MU, SIGMA), color=SZIN, alpha=0.45)
    for p, nev in PERCENTILISEK[:3]:
        ertek = norm.ppf(p, loc=MU, scale=SIGMA)
        ax_pdf.axvline(ertek, color=SEGED_SZIN, linewidth=1, linestyle="--")
        ax_pdf.text(ertek, 0.0415, "{}\n{:.1f}".format(nev, ertek),
                    ha="center", va="bottom", fontsize=9, color=SZOVEG_SZIN)
    ax_pdf.axvline(q, color=SZIN, linewidth=2)
    ax_pdf.text(q + 1, 0.02, "90%-os kvantilis\n{:.2f} pont".format(q),
                ha="left", va="center", fontsize=10, color=SZOVEG_SZIN)
    ax_formaz(ax_pdf, "Sűrűségfüggvény (PDF)", "sűrűség")
    ax_pdf.set_ylim(0, 0.05)

    # Jobb oldal: eloszlásfüggvény, a PPF a CDF megfordítása
    ax_cdf.plot(x_axis, norm.cdf(x_axis, MU, SIGMA), color=GORBE_SZIN, linewidth=2)
    ax_cdf.plot([x_axis[0], q], [0.90, 0.90], color=SZIN, linewidth=1.5, linestyle="--")
    ax_cdf.plot([q, q], [0.90, 0], color=SZIN, linewidth=1.5, linestyle="--")
    ax_cdf.plot(q, 0.90, "o", color=SZIN, markersize=8,
                markeredgecolor="white", markeredgewidth=2)
    ax_cdf.text(q + 1.5, 0.86, "norm.ppf(0.90) = {:.2f}".format(q),
                ha="left", va="top", fontsize=10, color=SZOVEG_SZIN)
    ax_formaz(ax_cdf, "Eloszlásfüggvény (CDF): 0,90-ből visszakeresve", "P(X ≤ x)")
    ax_cdf.set_ylim(0, 1.02)

    fig.suptitle("90%-os kvantilis (mu = {}, sigma = {})".format(MU, SIGMA), fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "kvantilis.png"), dpi=120)
    plt.show()


if __name__ == "__main__":
    main()
