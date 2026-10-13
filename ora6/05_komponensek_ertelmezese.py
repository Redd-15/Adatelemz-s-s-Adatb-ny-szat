# -*- coding: utf-8 -*-
"""5. A főkomponensek értelmezése.

Bemenet: student_performance_imputed.csv

A 3. (négy változó) és a 4. feladat (öt változó, + sleep_hours) két
komponensű PCA-jának komponenssúlyait (pca.components_) táblázatba
rendezzük, összevetjük, és tartalmi értelmezést adunk a PC1-nek és a PC2-nek.

A komponensek előjele önkényes: egy főkomponens −1-szerese ugyanazt a
varianciát magyarázza, ezért a súlyok előjelét mindig egymáshoz képest
értelmezzük.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pca_kozos import (MAPPA, JELLEMZOK, JELLEMZOK_ALVASSAL, SZIN, SZIN2, SZOVEG_SZIN,
                       beolvas, cim, alvas_hozzaad, pca_2d, sulyok, ax_formaz)

# ekkora |súly| fölött tekintjük a változót a komponens meghatározó elemének
JELENTOS = 0.4


def legnagyobb_sulyok(tabla, nev):
    for pc in ("PC1", "PC2"):
        rendezett = tabla[pc].reindex(tabla[pc].abs().sort_values(ascending=False).index)
        jelentos = rendezett[rendezett.abs() >= JELENTOS]
        print("  {} – {}: {}".format(nev, pc, ", ".join(
            "{} ({:+.3f})".format(v, s) for v, s in jelentos.items())))


def abra(s4, s5):
    fig, tengelyek = plt.subplots(1, 2, figsize=(14, 5.4), sharex=True)
    for ax, tabla, felirat in ((tengelyek[0], s4, "3. feladat: négy változó"),
                               (tengelyek[1], s5, "4. feladat: öt változó (+ sleep_hours)")):
        y = np.arange(len(tabla))
        magassag = 0.38
        for eltolas, pc, szin in ((-magassag / 2, "PC1", SZIN), (magassag / 2, "PC2", SZIN2)):
            ax.barh(y + eltolas, tabla[pc], height=magassag, color=szin, alpha=0.85, label=pc)
            for yi, ertek in zip(y + eltolas, tabla[pc]):
                ax.text(ertek + (0.02 if ertek >= 0 else -0.02), yi, "{:+.2f}".format(ertek),
                        va="center", ha="left" if ertek >= 0 else "right", fontsize=8)
        ax.set_yticks(y)
        ax.set_yticklabels(tabla.index)
        ax.invert_yaxis()
        ax.axvline(0, color=SZOVEG_SZIN, linewidth=0.8)
        for hatar in (-JELENTOS, JELENTOS):
            ax.axvline(hatar, color=SZOVEG_SZIN, linewidth=0.8, linestyle=":")
        ax.set_xlim(-1, 1)
        ax.legend(frameon=False, fontsize=9, loc="lower right")
        ax_formaz(ax, felirat, "komponenssúly (pontozott vonal: |súly| = {})".format(JELENTOS),
                  "", racs="x")
    fig.suptitle("A főkomponensek súlyai az eredeti változókon", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "05_komponensek_ertelmezese.png"), dpi=120)


def main():
    pd.set_option("display.width", 140)
    df = beolvas()
    pca4, _ = pca_2d(df, JELLEMZOK)
    pca5, _ = pca_2d(alvas_hozzaad(df), JELLEMZOK_ALVASSAL)
    s4 = sulyok(pca4, JELLEMZOK)
    s5 = sulyok(pca5, JELLEMZOK_ALVASSAL)

    cim("Komponenssúlyok a 3. és a 4. feladatban")
    tabla = pd.concat({"3. feladat (4 változó)": s4, "4. feladat (5 változó)": s5}, axis=1)
    print(tabla.round(3).to_string(na_rep="–"))
    print()
    print("A súlyok egységvektort alkotnak: a négyzetösszegük komponensenként 1 (pl. 3. feladat")
    print("PC1: {:.3f}). Egy hallgató PC-pontszáma a standardizált értékeinek súlyozott összege."
          .format((s4["PC1"] ** 2).sum()))

    cim("Mely változók súlyai a legnagyobbak abszolút értékben?")
    print("(|súly| ≥ {} esetén, csökkenő sorrendben)".format(JELENTOS))
    legnagyobb_sulyok(s4, "3. feladat")
    legnagyobb_sulyok(s5, "4. feladat")

    cim("Azonos-e a változók súlya a két feladat esetén?")
    print("Nem. A sleep_hours bevonása átrendezi a komponenseket:")
    print("- A 3. feladat PC1-ét a previous_gpa, az attendance és az assignments_completed")
    print("  határozza meg; a 4. feladatban ezek a PC2-re kerülnek, közel ugyanazzal a mintázattal:")
    for v in ("previous_gpa", "attendance", "assignments_completed"):
        print("    {:<22} 3. feladat PC1: {:+.2f}   4. feladat PC2: {:+.2f}".format(
            v, s4.loc[v, "PC1"], s5.loc[v, "PC2"]))
    print("- A 4. feladat PC1-ét szinte teljesen a study_hours és a sleep_hours adja, míg a")
    print("  3. feladatban a study_hours a PC2 legnagyobb súlyú változója volt.")
    print("A komponensek sorrendje azért cserélődik, mert a megduplázott tanulási idő együtt")
    print("nagyobb varianciát képvisel, mint a többi változó közös része.")

    cim("A 4. feladatban milyen előjellel szerepel a study_hours és a sleep_hours a PC1-ben?")
    sh, sl = s5.loc["study_hours", "PC1"], s5.loc["sleep_hours", "PC1"]
    print("study_hours: {:+.3f}, sleep_hours: {:+.3f} → hasonló nagyságú, ellentétes előjelű súly."
          .format(sh, sl))
    print("(Az előjelek együtt megfordulhatnak egy másik futtatásban vagy programban, az")
    print("ellentétes előjel viszont mindig megmarad.)")

    cim("Mit jelent, ha hasonló nagyságú, de ellentétes előjelű súlyt kapnak?")
    print("A komponens a két változó KÜLÖNBSÉGÉT méri: magas PC1-értéket az kap, aki sokat")
    print("tanul ÉS keveset alszik, alacsonyat, aki keveset tanul és sokat alszik. A két változó")
    print("ugyanannak a dimenziónak a két végét írja le (erős negatív korreláció), ezért a PCA")
    print("egyetlen tengelyre vonja össze őket. A hasonló nagyság azt mutatja, hogy egyenlő")
    print("mértékben járulnak hozzá a komponenshez – ami a redundanciájuk jele: együtt sem")
    print("hordoznak több információt, mint külön-külön.")

    cim("Adható-e rövid, tartalmilag indokolható értelmezés a PC1-nek és a PC2-nek?")
    print("3. feladat (négy változó):")
    print("  PC1 – „általános tanulmányi elkötelezettség / akadémiai háttér”: a previous_gpa, az")
    print("        attendance és az assignments_completed azonos előjellel, hasonló súllyal")
    print("        szerepel; magas értéket a jó előzetes eredményű, rendszeresen órára járó és")
    print("        feladatait beadó hallgató kap. A sikertelenek átlagosan itt alacsonyabbak.")
    print("  PC2 – „tanulási idő kontra feladatmegoldás”: pozitív súlyú a study_hours (és")
    print("        kisebb mértékben az attendance), negatív az assignments_completed; azokat")
    print("        különíti el, akik sok időt töltenek tanulással, de kevesebb feladatot adnak")
    print("        be, azoktól, akik kevesebb órát, de több feladatot teljesítenek.")
    print("4. feladat (öt változó):")
    print("  PC1 – „időráfordítás: tanulás kontra alvás”: a study_hours és a sleep_hours")
    print("        ellentétes előjellel; lényegében a tanulási időt méri (kétszer).")
    print("  PC2 – „akadémiai elkötelezettség”: a previous_gpa, az assignments_completed és az")
    print("        attendance azonos előjellel – tartalmilag a 3. feladat PC1-ének felel meg.")
    print()
    print("Fontos: a PC2 a 3. feladatban csak {:.1f} százalékponttal kevesebb varianciát magyaráz,"
          .format(100 * (pca4.explained_variance_ratio_[0] - pca4.explained_variance_ratio_[1])))
    print("mint a PC1 ({:.1%} vs {:.1%}), és a változók gyengén korrelálnak, ezért az értelmezések"
          .format(*pca4.explained_variance_ratio_))
    print("tájékoztató jellegűek: kis adatváltozás is átrendezheti a két komponenst.")

    abra(s4, s5)
    plt.show()


if __name__ == "__main__":
    main()
