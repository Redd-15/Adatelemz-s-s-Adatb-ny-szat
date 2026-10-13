# -*- coding: utf-8 -*-
"""3. Hallgatók eredményeinek kétdimenziós PCA-ábrázolása.

Bemenet: student_performance_imputed.csv

Két főkomponenssel végezzük a PCA-t, az eredményből új DataFrame-et
készítünk, és a hallgatókat az első két főkomponens síkjában ábrázoljuk,
egyszer a passed, egyszer a programme szerint színezve. A színezés csak
megjelenítés: a főkomponensek képzésében a passed és a programme nem vesz részt.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from pca_kozos import (MAPPA, JELLEMZOK, SZOVEG_SZIN, beolvas, cim, pca_2d, pontdiagram,
                       elkulonules)

# a PC-k szórásával skálázott távolság négyzete 2 szabadságfokú khi-négyzet eloszlású
TAVOLI_HATAR = stats.chi2.ppf(0.975, df=2)


def tavoli_hallgatok(df, eredmeny, pca):
    """Az első két PC síkjában a középponttól távol eső hallgatók."""
    d2 = (eredmeny["PC1"] ** 2 / pca.explained_variance_[0]
          + eredmeny["PC2"] ** 2 / pca.explained_variance_[1])
    tavoli = eredmeny.assign(távolság=np.sqrt(d2))[d2 > TAVOLI_HATAR]
    tavoli = tavoli.sort_values("távolság", ascending=False)
    return tavoli.join(df[JELLEMZOK + ["exam_score"]])


def main():
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)
    df = beolvas()

    cim("PCA két komponenssel – az eredmény DataFrame-je")
    pca, eredmeny = pca_2d(df, JELLEMZOK)
    arany = pca.explained_variance_ratio_
    print(eredmeny.head(10).round(3).to_string(index=False))
    print("... ({} sor)".format(len(eredmeny)))
    print()
    print("Magyarázott varianciaarány: PC1 = {:.2%}, PC2 = {:.2%}, együtt {:.2%}".format(
        arany[0], arany[1], arany.sum()))

    cim("Elkülönülnek-e a sikeres és sikertelen hallgatók?")
    kozep = eredmeny.groupby("passed")[["PC1", "PC2"]].agg(["mean", "std"])
    print(kozep.round(3).to_string())
    d_pc1 = elkulonules(eredmeny, ["PC1"])
    d_2d = elkulonules(eredmeny)
    print()
    print("A csoportközéppontok távolsága a közös szórás egységében: PC1 mentén {:.2f},"
          .format(d_pc1))
    print("a PC1–PC2 síkban {:.2f}.".format(d_2d))
    print("A sikertelen hallgatók átlagosan a PC1 negatív oldalán vannak (alacsonyabb GPA,")
    print("óralátogatás és beadott feladatszám), a sikeresek a pozitív oldalán. Ez")
    print("eltolódás, nem szétválás: a két pontfelhő nagy részben átfedi egymást, sok")
    print("sikertelen hallgató a sikeresek között helyezkedik el.")

    cim("Megfigyelhetők-e csoportok (például szakonként)?")
    print(eredmeny.groupby("programme")[["PC1", "PC2"]].agg(["mean", "std"]).round(3).to_string())
    print()
    print("A szakok középpontjai közel vannak az origóhoz és egymáshoz (a PC-k szórásához,")
    print("~1-hez képest), a pontfelhők teljesen keverednek: a négy tanulási jellemző alapján")
    print("nincsenek szakonként elkülönülő csoportok. Más, jól elkülönülő csoportosulás sem")
    print("látszik, a pontok egyetlen, nagyjából kerek felhőt alkotnak.")

    cim("Találhatók-e a többi megfigyeléstől távol eső hallgatók?")
    tavoli = tavoli_hallgatok(df, eredmeny, pca)
    print("Feltétel: a PC-k szórásával skálázott távolság² > χ²(2; 0,975) = {:.2f}".format(
        TAVOLI_HATAR))
    print(tavoli.round(2).to_string(index=False))
    print()
    print("Ezek a hallgatók a változók szokatlan kombinációja miatt esnek távol, nem feltétlenül")
    print("hibás adatok. S055: minimális tanulás (1 óra) és a legalacsonyabb (korlátozott)")
    print("óralátogatás mellett magas GPA és sok beadott feladat – a PC2 negatív szélén áll.")
    print("S006: a legtöbb tanulási óra (25.3, a korlátozott felső érték) magas óralátogatással")
    print("– a PC2 pozitív szélén. A határ közelében van még pár pont, a felhőtől élesen")
    print("elváló csoport azonban nincs.")

    cim("Mekkora variancia maradt ki a kétdimenziós ábrázolásból?")
    print("A két főkomponens a teljes variancia {:.2%}-át őrzi meg, {:.2%} kimarad".format(
        arany.sum(), 1 - arany.sum()))
    print("(ez a PC3 és PC4 együttes aránya).")
    print()
    print("Megjegyzések:")
    print("- A PCA nem a csoportok szétválasztására törekszik, hanem a bemeneti változók")
    print("  varianciájának minél nagyobb részét őrzi meg. A passed és a programme csak a")
    print("  pontok színét határozza meg, a főkomponensek képzését nem befolyásolja.")
    print("- A csoportok megkülönböztetéséhez hasznos eltérések a kihagyott komponensekben is")
    print("  megjelenhetnek, ezért a keveredés nem bizonyítja, hogy az eredeti változók alapján")
    print("  sincs különbség a csoportok között.")

    fig, (ax_bal, ax_jobb) = plt.subplots(1, 2, figsize=(14, 6))
    pontdiagram(ax_bal, eredmeny, "passed", "Sikeres és sikertelen hallgatók (✕ = középpont)", arany)
    pontdiagram(ax_jobb, eredmeny, "programme", "Képzési programok (✕ = középpont)", arany)
    for ax in (ax_bal, ax_jobb):
        for _, sor in tavoli.iterrows():
            ax.annotate(sor["student_id"], (sor["PC1"], sor["PC2"]), xytext=(4, 4),
                        textcoords="offset points", fontsize=7, color=SZOVEG_SZIN)
    fig.suptitle("Hallgatók az első két főkomponens síkjában "
                 "(a megőrzött variancia {:.2%})".format(arany.sum()), fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "03_pca_2d.png"), dpi=120)
    plt.show()


if __name__ == "__main__":
    main()
