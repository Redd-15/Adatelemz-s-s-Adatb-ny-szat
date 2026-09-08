# -*- coding: utf-8 -*-
"""A 21-es feladat pontos valószínűségei az összes eset végigvizsgálásával."""

from collections import Counter
from fractions import Fraction as F
from itertools import combinations

ERTEKEK = [7, 8, 9, 10, 2, 3, 4, 11] * 4          # 32 lapos pakli értékei

kezek = [(a, b) for a, b in combinations(range(32), 2)
         if 18 < ERTEKEK[a] + ERTEKEK[b] <= 21]

print("kedvezo kezdolapok:", len(kezek), "/", 32 * 31 // 2)
print("eloszlas:", Counter(ERTEKEK[a] + ERTEKEK[b] for a, b in kezek))

n = len(kezek)
marad_tul = marad_21 = marad_pont = F(0)
ker_tul = ker_21 = ker_pont = F(0)

for a, b in kezek:
    v = ERTEKEK[a] + ERTEKEK[b]
    marad_tul += F(1, n)
    marad_pont += F(v, n)
    if v == 21:
        marad_21 += F(1, n)
    for c in range(32):
        if c in (a, b):
            continue
        u = v + ERTEKEK[c]
        p = F(1, n) * F(1, 30)
        if u <= 21:
            ker_tul += p
            ker_pont += p * u
            if u == 21:
                ker_21 += p

sorok = [
    ("NEM KER  nem lep tul", marad_tul),
    ("NEM KER  pontosan 21", marad_21),
    ("NEM KER  varhato pont", marad_pont),
    ("KER      nem lep tul", ker_tul),
    ("KER      pontosan 21", ker_21),
    ("KER      varhato pont", ker_pont),
    ("VELETLEN nem lep tul", (marad_tul + ker_tul) / 2),
    ("VELETLEN pontosan 21", (marad_21 + ker_21) / 2),
    ("VELETLEN varhato pont", (marad_pont + ker_pont) / 2),
]
print()
for nev, ertek in sorok:
    print("{:<24} {:>12}  = {:.5f}".format(nev, str(ertek), float(ertek)))
