# -*- coding: utf-8 -*-
"""Normális eloszlás ellenőrzése Q-Q ábrával.

Az előző feladat (eloszlasok.py) három mintájára készítünk kvantilis-
kvantilis ábrát. A scipy.stats.probplot a minta kvantiliseit veti össze a
normális eloszlás elméleti kvantiliseivel: ha a pontok egy egyenesre
esnek, a minta normális eloszlásúnak tekinthető.
"""

import os

import matplotlib.pyplot as plt
from scipy import stats

from eloszlasok import SZINEK, mintak_generalasa

VONAL_SZIN = "#0b0b0b"


def main():
    mintak = mintak_generalasa()

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    for ax, szin, (nev, x) in zip(axes, SZINEK, mintak):
        stats.probplot(x, dist="norm", plot=ax)
        pontok, egyenes = ax.get_lines()
        pontok.set(color=szin, markersize=4, alpha=0.6)
        egyenes.set(color=VONAL_SZIN, linewidth=1.5)

        ax.set_title("")  # a probplot saját "Probability Plot" címének törlése
        ax.set_title(nev, loc="left", fontsize=11)
        ax.set_xlabel("elméleti kvantilisek (N(0,1))")
        ax.set_ylabel("minta kvantilisei")
        ax.grid(color="#e5e4df", linewidth=0.8)
        ax.set_axisbelow(True)
        for oldal in ("top", "right"):
            ax.spines[oldal].set_visible(False)

    print("Q-Q ábra értelmezése:")
    print("  - Normális: a pontok az egyenesen vannak -> normális eloszlás.")
    print("  - Egyenletes: S alakú görbe; a széleken a pontok visszahajlanak")
    print("    az egyenes felé, mert a mintának nincsenek hosszú farkai.")
    print("  - Exponenciális: ív alakú görbe; bal oldalt az egyenes felett,")
    print("    jobb oldalt meredeken felfelé tér el -> jobbra ferde eloszlás.")

    fig.suptitle("Q-Q ábrák: mennyire normális a minta?", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "qq_abra.png"), dpi=120)
    plt.show()


if __name__ == "__main__":
    main()
