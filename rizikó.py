# -*- coding: utf-8 -*-
"""Rizikó: 3 támadó kocka vs. 2 védő kocka összecsapásának
relatív gyakorisága (szimuláció) és pontos valószínűsége."""

import random
from itertools import product

# A három kimenetel indexe: 0 = támadó veszít 2-t, 1 = döntetlen, 2 = védő veszít 2-t


def kimenetel(tamado, vedo):
    """Egy összecsapás kiértékelése.

    tamado: 3 dobás, vedo: 2 dobás.
    Visszatér: hány katonát veszít a védő (0, 1 vagy 2) -> ez a kimenetel indexe.
    """
    t = sorted(tamado, reverse=True)
    v = sorted(vedo, reverse=True)
    vedo_veszteseg = 0
    for i in range(2):
        if t[i] > v[i]:          # döntetlennél a védő nyer
            vedo_veszteseg += 1
    return vedo_veszteseg


def szimulacio(n):
    """n kísérlet elvégzése, a három kimenetel relatív gyakorisága."""
    db = [0, 0, 0]
    for _ in range(n):
        tamado = [random.randint(1, 6) for _ in range(3)]
        vedo = [random.randint(1, 6) for _ in range(2)]
        db[kimenetel(tamado, vedo)] += 1
    return [x / n for x in db]


def pontos_valoszinuseg():
    """Az összes 6^3 * 6^2 = 7776 eset végigvizsgálása."""
    db = [0, 0, 0]
    osszes = 0
    for tamado in product(range(1, 7), repeat=3):
        for vedo in product(range(1, 7), repeat=2):
            db[kimenetel(tamado, vedo)] += 1
            osszes += 1
    return [x / osszes for x in db]


def sor(cimke, ertekek):
    """Egy sor formázása: 5 tizedes pontosság, 3 szóköz elválasztás."""
    return cimke.ljust(CIMKE_SZELES) + "   ".join(
        "{:>{w}.5f}".format(e, w=w) for e, w in zip(ertekek, OSZLOP_SZELES)
    )


FEJLEC = ["Támadó", "Döntetlen", "Védekező"]
OSZLOP_SZELES = [max(7, len(f)) for f in FEJLEC]
CIMKE_SZELES = 18


def main():
    ezer = szimulacio(1000)
    millio = szimulacio(10000000)
    pontos = pontos_valoszinuseg()

    print(" " * CIMKE_SZELES + "   ".join(
        f.rjust(w) for f, w in zip(FEJLEC, OSZLOP_SZELES)
    ))
    print(sor("1000 kísérlet:", ezer))
    print(sor("10000000 kísérlet:", millio))
    print(sor("Valószínűség:", pontos))


if __name__ == "__main__":
    main()
