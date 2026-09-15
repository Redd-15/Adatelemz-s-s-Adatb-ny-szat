# -*- coding: utf-8 -*-
"""Érmét dobunk az első fejig. Ha ez az n-edik dobás,
akkor a nyeremény 2*n forint.
A nyeremény mintaátlaga m = 100, 10000 és 1000000 játék esetén."""

import random


def egy_jatek():
    """Dobálunk az első fejig, visszaadjuk a nyereményt (2*n)."""
    n = 1
    while random.getrandbits(1) == 0:   # 0 = írás, 1 = fej
        n += 1
    return 2 * n


def atlagos_nyeremeny(m):
    """m játék lejátszása, a nyeremények átlaga."""
    osszeg = 0
    for _ in range(m):
        osszeg += egy_jatek()
    return osszeg / m


def main():
    for m in (100, 10000, 1000000):
        print("m = {:>7}   átlagos nyeremény: {:>8.4f} Ft".format(
            m, atlagos_nyeremeny(m)))

    print()
    print("Várható érték: E(2*n) = 2 * E(n) = 2 * 2 = 4.0000 Ft")


if __name__ == "__main__":
    main()
