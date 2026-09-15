# -*- coding: utf-8 -*-
"""Önálló feladat: vizsgapontszámok normalitásának vizsgálata.

1. Átlag és szórás
2. Hisztogram density=True paraméterrel
3. Normális eloszlás illesztése (norm.fit)
4. Az illesztett sűrűségfüggvény a hisztogramon
5. Q-Q ábra
6. Vizuális döntés a normalitásról
"""

import os

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import norm

scores = np.array([45, 48, 52, 55, 57, 58, 60, 62, 63, 65, 66, 67, 68, 70, 71, 72,
                   74, 75, 77, 80, 82, 85, 88, 90])

SZIN = "#2a78d6"
GORBE_SZIN = "#0b0b0b"


def ax_formaz(ax, cim, xlabel, ylabel):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(color="#e5e4df", linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def main():
    # 1. Átlag és szórás
    print("1. Átlag:  {:.2f}".format(scores.mean()))
    print("   Szórás: {:.2f}".format(scores.std()))

    # 3. Normális eloszlás illesztése
    mu, sigma = norm.fit(scores)
    print("3. Illesztett normális eloszlás: mu = {:.2f}, sigma = {:.2f}".format(mu, sigma))

    fig, (ax_hist, ax_qq) = plt.subplots(1, 2, figsize=(12, 5))

    # 2. Hisztogram és 4. az illesztett sűrűségfüggvény
    ax_hist.hist(scores, bins=6, density=True, color=SZIN, alpha=0.6,
                 edgecolor="white", linewidth=2, label="pontszámok")
    x_axis = np.linspace(30, 105, 500)
    ax_hist.plot(x_axis, norm.pdf(x_axis, mu, sigma), color=GORBE_SZIN, linewidth=2,
                 label="illesztett N({:.1f}, {:.1f})".format(mu, sigma))
    ax_formaz(ax_hist, "Hisztogram és illesztett normális sűrűség", "pontszám", "sűrűség")
    ax_hist.legend(frameon=False, fontsize=9)

    # 5. Q-Q ábra
    stats.probplot(scores, dist="norm", plot=ax_qq)
    pontok, egyenes = ax_qq.get_lines()
    pontok.set(color=SZIN, markersize=7, markeredgecolor="white", markeredgewidth=1)
    egyenes.set(color=GORBE_SZIN, linewidth=1.5)
    ax_qq.set_title("")  # a probplot saját "Probability Plot" címének törlése
    ax_formaz(ax_qq, "Q-Q ábra", "elméleti kvantilisek (N(0,1))", "pontszám")

    # 6. Vizuális döntés
    print()
    print("6. Vizuális értékelés:")
    print("   - A hisztogram nagyjából szimmetrikus, egy csúcsú, a közepén")
    print("     a legmagasabb, és jól követi az illesztett harang görbét.")
    print("   - A Q-Q ábrán a pontok végig az egyenes közelében vannak,")
    print("     nincs szisztematikus S vagy ív alakú eltérés.")
    print("   - A két szélén kicsit laposabb, mint a normális (a legkisebb")
    print("     és legnagyobb pontszámok nem nyúlnak ki annyira), de ez")
    print("     24 elemnél belefér a véletlen ingadozásba.")
    print("   => Az eloszlás jó közelítéssel normálisnak tekinthető.")

    fig.suptitle("Vizsgapontszámok (n = {})".format(len(scores)), fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "onallo_feladat.png"), dpi=120)
    plt.show()


if __name__ == "__main__":
    main()
