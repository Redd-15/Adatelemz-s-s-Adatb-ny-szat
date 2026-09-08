# -*- coding: utf-8 -*-
"""21-es (huszonegyes) magyar kártyajáték szimulációja.

A játékos két lapot kap. Ha a két lap értéke 18 fölött van (19, 20 vagy 21),
akkor három stratégiát vizsgálunk 1000-1000 esettel:
  - nem kér lapot,
  - kér egy lapot,
  - 0.5 valószínűséggel kér lapot.
"""

import random

JATEKOK = 10000


class Kartya:
    """Egy magyar kártyalap: szín, figura és a 21-esben érvényes érték."""

    SZINEK = ("Makk", "Tök", "Zöld", "Piros")
    # (figura, érték) párok: Ász = 11, Király = 4, Felső = 3, Alsó = 2
    FIGURAK = (("VII", 7), ("VIII", 8), ("IX", 9), ("X", 10),
               ("Alsó", 2), ("Felső", 3), ("Király", 4), ("Ász", 11))

    def __init__(self, szin, figura, ertek):
        self.szin = szin
        self.figura = figura
        self.ertek = ertek

    def __str__(self):
        return "{} {} ({})".format(self.szin, self.figura, self.ertek)

    def __repr__(self):
        return str(self)


class Pakli:
    """32 lapos magyar kártyapakli."""

    def __init__(self):
        self.lapok = [Kartya(szin, figura, ertek)
                      for szin in Kartya.SZINEK
                      for figura, ertek in Kartya.FIGURAK]
        self.kever()

    def kever(self):
        random.shuffle(self.lapok)

    def huz(self):
        """A pakli tetejéről egy lapot ad vissza."""
        return self.lapok.pop()


class Kez:
    """A játékos lapjai."""

    def __init__(self, lapok=None):
        self.lapok = list(lapok) if lapok else []

    @property
    def ertek(self):
        return sum(lap.ertek for lap in self.lapok)

    def hozzaad(self, lap):
        self.lapok.append(lap)

    def tullepte(self):
        return self.ertek > 21

    def __str__(self):
        return ", ".join(str(lap) for lap in self.lapok) + " = " + str(self.ertek)


def kezdo_leosztas():
    """Addig oszt új pakliból, míg a két lap értéke 18 fölött, de legföljebb 21 lesz.
    (Az Ász + Ász = 22 eleve túllépés, ott nincs mit eldönteni.)"""
    while True:
        pakli = Pakli()
        kez = Kez([pakli.huz(), pakli.huz()])
        if 18 < kez.ertek <= 21:
            return pakli, kez


def egy_jatek(strategia):
    """Egy játék a megadott stratégiával: 'nem_ker', 'ker' vagy 'veletlen'.
    Visszatér: (nem lépte túl, pontosan 21 lett)."""

    pakli, kez = kezdo_leosztas()

    if strategia == "ker":
        huz = True
    elif strategia == "nem_ker":
        huz = False
    else:                                # 'veletlen': 0.5 - 0.5
        huz = random.random() < 0.5

    if huz:
        kez.hozzaad(pakli.huz())

    return (not kez.tullepte(), kez.ertek == 21)


def szimulacio(strategia, n=JATEKOK):
    """n játék: a túl nem lépések és a pontosan 21-ek relatív gyakorisága."""
    nem_lepte_tul = 0
    huszonegy = 0
    for _ in range(n):
        rendben, pont21 = egy_jatek(strategia)
        nem_lepte_tul += rendben
        huszonegy += pont21
    return nem_lepte_tul / n, huszonegy / n


def main():
    strategiak = [("Nem kér", "nem_ker"), ("Kér", "ker"), ("Véletlen", "veletlen")]
    eredmenyek = [szimulacio(kod) for _, kod in strategiak]

    print(" " * 20 + "   ".join(nev.rjust(9) for nev, _ in strategiak))
    print("Nem lépte túl:  " + "   ".join(
        "{:>9.5f}".format(e[0]) for e in eredmenyek))
    print("Pontosan 21:    " + "   ".join(
        "{:>9.5f}".format(e[1]) for e in eredmenyek))


if __name__ == "__main__":
    main()
