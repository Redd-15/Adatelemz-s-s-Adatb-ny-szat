# -*- coding: utf-8 -*-
"""2. A komponensek számának kiválasztása.

Bemenet: student_performance_imputed.csv

A standardizált négy jellemzőn PCA-t végzünk minden lehetséges
főkomponens megtartásával, kiírjuk a magyarázott és a kumulált
varianciaarányt, ábrázoljuk őket, és eldöntjük, hány komponens kell
legalább 80%-hoz, illetve indokolt-e a kétdimenziós ábrázolás.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

from pca_kozos import (MAPPA, JELLEMZOK, SZIN, SZIN2, SZOVEG_SZIN, beolvas, cim,
                       standardizal, ax_formaz)

HATAR = 0.80   # gyakorlati irányelv, nem kötelező szabály


def abra(tabla):
    fig, ax = plt.subplots(figsize=(9, 5.2))
    x = np.arange(1, len(tabla) + 1)
    ax.bar(x, tabla["magyarázott_arány"], color=SZIN, alpha=0.85, width=0.6,
           label="magyarázott varianciaarány")
    ax.plot(x, tabla["kumulált_arány"], color=SZIN2, marker="o", linewidth=2,
            label="kumulált varianciaarány")
    for xi, (egy, kum) in zip(x, tabla[["magyarázott_arány", "kumulált_arány"]].to_numpy()):
        ax.text(xi, egy / 2, "{:.1%}".format(egy), ha="center", va="center", color="white",
                fontsize=9)
        ax.text(xi, kum + 0.025, "{:.1%}".format(kum), ha="center", fontsize=9, color=SZIN2)
    ax.axhline(HATAR, color=SZOVEG_SZIN, linestyle="--", linewidth=1,
               label="80%-os irányelv")
    # Kaiser-kritérium: standardizált adatnál az 1/p arány felel meg az 1-es sajátértéknek
    ax.axhline(1 / len(tabla), color=SZOVEG_SZIN, linestyle=":", linewidth=1,
               label="egy eredeti változó súlya (1/{} = {:.0%})".format(len(tabla), 1 / len(tabla)))
    ax.set_xticks(x)
    ax.set_xticklabels(tabla.index)
    ax.set_ylim(0, 1.08)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: "{:.0%}".format(v)))
    ax.legend(frameon=False, fontsize=9, loc="center right")
    ax_formaz(ax, "Magyarázott és kumulált varianciaarány (scree plot)", "főkomponens",
              "varianciaarány", racs="y")
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "02_komponensek_szama.png"), dpi=120)


def main():
    pd.set_option("display.width", 130)
    df = beolvas()
    z = standardizal(df, JELLEMZOK)

    cim("PCA az összes főkomponens megtartásával")
    pca = PCA()            # n_components nélkül: annyi komponens, ahány változó
    pca.fit(z)
    tabla = pd.DataFrame({
        "sajátérték": pca.explained_variance_,
        "magyarázott_arány": pca.explained_variance_ratio_,
        "kumulált_arány": np.cumsum(pca.explained_variance_ratio_),
    }, index=["PC{}".format(i + 1) for i in range(pca.n_components_)])
    print(tabla.to_string(formatters={
        "sajátérték": "{:.3f}".format,
        "magyarázott_arány": "{:.2%}".format,
        "kumulált_arány": "{:.2%}".format}))
    print()
    print("A sajátértékek összege {:.3f} ≈ a változók száma ({}), mert standardizált".format(
        tabla["sajátérték"].sum(), len(JELLEMZOK)))
    print("adatnál minden változó 1 egységnyi varianciával járul a teljes varianciához.")
    print("(Az sklearn n−1-gyel osztva becsli a sajátértéket, ezért az összeg kicsit nagyobb {}-nél.)"
          .format(len(JELLEMZOK)))

    cim("Hány komponens szükséges legalább 80% magyarázott varianciához?")
    k = int(np.argmax(tabla["kumulált_arány"].to_numpy() >= HATAR)) + 1
    print("{} komponens: a kumulált arány {:.2%} (az első {} csak {:.2%}).".format(
        k, tabla["kumulált_arány"].iat[k - 1], k - 1, tabla["kumulált_arány"].iat[k - 2]))
    print("Négy változóból ez csak eggyel kevesebb dimenzió, vagyis a dimenziócsökkentés itt")
    print("kevés tömörítést ad.")

    cim("Mekkora információveszteséggel járna két komponens megtartása?")
    ket = tabla["kumulált_arány"].iat[1]
    print("Két komponens a teljes variancia {:.2%}-át őrzi meg, a veszteség {:.2%}".format(ket, 1 - ket))
    print("(PC3: {:.2%}, PC4: {:.2%}).".format(*tabla["magyarázott_arány"].iloc[2:4]))

    cim("Indokolt-e az adatok kétdimenziós reprezentációja?")
    print("- A varianciaarányok egyenletesen csökkennek ({}), nincs jól".format(
        ", ".join("{:.1%}".format(a) for a in tabla["magyarázott_arány"])))
    print("  látható „könyök”: a változók egymással csak gyengén korrelálnak, ezért nincs")
    print("  néhány erős közös dimenzió, minden változó jórészt saját információt hordoz.")
    print("- A Kaiser-kritérium (sajátérték > 1) szerint {} komponens tartható meg.".format(
        int((tabla["sajátérték"] > 1).sum())))
    print("- A 2D ábrázolás SZEMLÉLTETÉSRE elfogadható (egy síkon látható a hallgatók")
    print("  elrendeződése), de a variancia ~{:.0%}-a kimarad, így a 2D ábra alapján levont".format(1 - ket))
    print("  következtetések (pl. csoportok keveredése) óvatosan kezelendők. További")
    print("  elemzéshez (pl. modellezéshez) {} komponens vagy az eredeti változók javasoltak.".format(k))
    print()
    print("Megjegyzés: a 80%-os határ gyakorlati irányelv, nem általánosan kötelező szabály.")

    abra(tabla)
    plt.show()


if __name__ == "__main__":
    main()
