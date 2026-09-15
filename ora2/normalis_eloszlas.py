# -*- coding: utf-8 -*-
"""Normális eloszlású véletlen minta generálása.

1000 elemű mintát generálunk különböző mu (várható érték) és sigma (szórás)
értékekkel, és megfigyeljük, hogyan változik a minta átlaga, szórása,
minimuma és maximuma.
"""

import numpy as np

MINTA_MERET = 1000

# (mu, sigma) párok: először mu-t változtatjuk fix sigma mellett,
# majd sigma-t fix mu mellett.
PARAMETEREK = [
    (0, 1),
    (5, 1),
    (-10, 1),
    (100, 1),
    (0, 0.1),
    (0, 5),
    (0, 20),
    (50, 10),
]


def statisztika(mu, sigma):
    """Generál egy mintát, és visszaadja a jellemzőit."""
    x = np.random.normal(mu, sigma, MINTA_MERET)
    return x.mean(), x.std(), x.min(), x.max()


def main():
    print("{:>6} {:>6} | {:>9} {:>9} {:>9} {:>9}".format(
        "mu", "sigma", "átlag", "szórás", "minimum", "maximum"))
    print("-" * 57)
    for mu, sigma in PARAMETEREK:
        atlag, szoras, minimum, maximum = statisztika(mu, sigma)
        print("{:>6} {:>6} | {:>9.3f} {:>9.3f} {:>9.3f} {:>9.3f}".format(
            mu, sigma, atlag, szoras, minimum, maximum))

    print()
    print("Megfigyelések:")
    print("  - Az átlag mu közelében van, a szórás pedig sigma közelében.")
    print("  - mu növelése az egész mintát eltolja: az átlag, a minimum és")
    print("    a maximum is ugyanennyivel változik, a szórás nem.")
    print("  - sigma növelése szétteríti a mintát: a szórás nő, a minimum")
    print("    csökken, a maximum nő, az átlag mu körül marad.")
    print("  - 1000 elemnél a minimum és maximum nagyjából mu +/- 3 sigma.")


if __name__ == "__main__":
    main()
