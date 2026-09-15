# -*- coding: utf-8 -*-
"""Valószínűség számítása normális eloszlás esetén.

Egy vizsgán a pontszámok normális eloszlást követnek (mu = 70, sigma = 10).
  a) P(X < 80) kiszámítása az eloszlásfüggvénnyel (CDF).
  b) P(60 < X < 80), P(50 < X < 90), P(40 < X < 100) kiszámítása és
     ábrázolása, összevetve a 68-95-99,7 szabállyal.
"""

import os

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

MU = 70
SIGMA = 10

# (alsó határ, felső határ, hány sigma, szabály szerinti érték)
INTERVALLUMOK = [
    (60, 80, 1, 0.68),
    (50, 90, 2, 0.95),
    (40, 100, 3, 0.997),
]

SZIN = "#2a78d6"
GORBE_SZIN = "#52514e"
SZOVEG_SZIN = "#0b0b0b"


def intervallum_valoszinuseg(also, felso, mu=MU, sigma=SIGMA):
    """P(also < X < felso) = F(felso) - F(also)."""
    return norm.cdf(felso, loc=mu, scale=sigma) - norm.cdf(also, loc=mu, scale=sigma)


def ax_formaz(ax, cim):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim, loc="left", fontsize=11)
    ax.set_xlim(MU - 4 * SIGMA, MU + 4 * SIGMA)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("pontszám")
    ax.set_ylabel("sűrűség")
    ax.grid(axis="y", color="#e5e4df", linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def satiroz(ax, also, felso, szoveg):
    """Kirajzolja a sűrűségfüggvényt, és besatírozza az [also, felso] részt."""
    x_axis = np.linspace(MU - 4 * SIGMA, MU + 4 * SIGMA, 500)
    ax.plot(x_axis, norm.pdf(x_axis, MU, SIGMA), color=GORBE_SZIN, linewidth=2)

    x_resz = np.linspace(also, felso, 300)
    ax.fill_between(x_resz, norm.pdf(x_resz, MU, SIGMA), color=SZIN, alpha=0.45)
    ax.text(0.98, 0.95, szoveg, transform=ax.transAxes, ha="right", va="top",
            fontsize=10, color=SZOVEG_SZIN)


def main():
    # a) P(X < 80)
    p = norm.cdf(80, loc=MU, scale=SIGMA)
    print("a) P(X < 80) = {:.4f}  ({:.2f}%)".format(p, p * 100))
    print()

    # b) intervallumok
    print("b) Intervallumok (mu = {}, sigma = {}):".format(MU, SIGMA))
    print("{:>12} {:>12} {:>12} {:>12}".format(
        "intervallum", "mu +/- k*s", "számított", "szabály"))
    eredmenyek = []
    for also, felso, k, szabaly in INTERVALLUMOK:
        valoszinuseg = intervallum_valoszinuseg(also, felso)
        eredmenyek.append(valoszinuseg)
        print("{:>12} {:>12} {:>11.2f}% {:>11.1f}%".format(
            "{}-{}".format(also, felso), "{} sigma".format(k),
            valoszinuseg * 100, szabaly * 100))

    # Ábra: a) és a három b) intervallum
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharey=True)
    axes = axes.ravel()

    satiroz(axes[0], MU - 4 * SIGMA, 80, "P(X < 80) = {:.2%}".format(p))
    ax_formaz(axes[0], "a) 80 pontnál kevesebb")

    for ax, (also, felso, k, szabaly), valoszinuseg in zip(
            axes[1:], INTERVALLUMOK, eredmenyek):
        szoveg = "P({} < X < {}) = {:.2%}\nszabály: ~{:.1%}".format(
            also, felso, valoszinuseg, szabaly)
        satiroz(ax, also, felso, szoveg)
        ax_formaz(ax, "b) {} és {} között (mu +/- {} sigma)".format(also, felso, k))

    fig.suptitle("Vizsgapontszámok: normális eloszlás (mu = {}, sigma = {})".format(
        MU, SIGMA), fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "valoszinuseg.png"), dpi=120)
    plt.show()


if __name__ == "__main__":
    main()
