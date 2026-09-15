# -*- coding: utf-8 -*-
"""Háromajtós (Monty Hall) probléma szimulációja 3000 játékkal:
az első 1000-ben a játékos kitart, a második 1000-ben változtat,
a harmadik 1000-ben 0.5 valószínűséggel változtat."""

import random

AJTOK = (0, 1, 2)
JATEKOK = 1000


def egy_jatek(strategia):
    """Egy játék lejátszása. strategia: 'marad', 'valt' vagy 'veletlen'.
    Visszatér: True, ha a játékos nyert."""

    nyeremeny = random.choice(AJTOK)          # ide rejtik az autót
    valasztas = random.choice(AJTOK)          # a játékos választása

    # A műsorvezető olyan ajtót nyit ki, amely nem a játékosé és nem a nyereményé.
    lehetsegesek = [a for a in AJTOK if a != valasztas and a != nyeremeny]
    kinyitott = random.choice(lehetsegesek)

    if strategia == "valt":
        valtoztat = True
    elif strategia == "marad":
        valtoztat = False
    else:                                     # 'veletlen': 0.5 - 0.5
        valtoztat = random.random() < 0.5

    if valtoztat:
        # A harmadik ajtó: se nem a mostani választás, se nem a kinyitott.
        valasztas = [a for a in AJTOK
                     if a != valasztas and a != kinyitott][0]

    return valasztas == nyeremeny


def relativ_gyakorisag(strategia, n=JATEKOK):
    """n játék lejátszása, a nyerések relatív gyakorisága."""
    nyeresek = 0
    for _ in range(n):
        if egy_jatek(strategia):
            nyeresek += 1
    return nyeresek / n


def main():
    marad = relativ_gyakorisag("marad")
    valt = relativ_gyakorisag("valt")
    veletlen = relativ_gyakorisag("veletlen")

    print("{:.5f} {:.5f} {:.5f}".format(marad, valt, veletlen))


if __name__ == "__main__":
    main()
