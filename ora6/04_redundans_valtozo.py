# -*- coding: utf-8 -*-
"""4. Redundáns változók hatása.

Bemenet: student_performance_imputed.csv

Új oszlopot (sleep_hours) adunk az adatokhoz, amely erős negatív
korrelációban áll a study_hours-szal, ábrázoljuk a korrelációs mátrixot
hőtérképen, majd két komponensű PCA-t végzünk az öt változón, és
összevetjük a négyváltozós (3. feladat) eredménnyel.

Az új oszlop nem ad független információt, csak a tanulási idő
információját ismétli meg.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pca_kozos import (MAPPA, JELLEMZOK, JELLEMZOK_ALVASSAL, beolvas, cim, standardizal,
                       alvas_hozzaad, pca_2d, pontdiagram, heatmap, elkulonules)


def megorzes(df, oszlopok, pca, eredeti):
    """Az eredeti változók varianciájának hány százalékát adja vissza a 2D rekonstrukció."""
    z = standardizal(df, oszlopok)
    vissza = pd.DataFrame(pca.inverse_transform(pca.transform(z)), columns=oszlopok,
                          index=df.index)
    hiba = ((z[eredeti] - vissza[eredeti]) ** 2).sum()
    return 1 - hiba / (z[eredeti] ** 2).sum()


def main():
    pd.set_option("display.width", 140)
    df = beolvas()
    df5 = alvas_hozzaad(df)

    cim("Az új sleep_hours oszlop")
    print("sleep_hours = 9 − 0,25 · study_hours + N(0; 0,4) zaj, 4–10 óra közé korlátozva")
    print(df5[["student_id", "study_hours", "sleep_hours"]].head().to_string(index=False))
    print("...")
    print(df5["sleep_hours"].describe().round(2).to_frame().T.to_string())

    cim("Korrelációs mátrix (öt változó)")
    korr = df5[JELLEMZOK_ALVASSAL].corr()
    print(korr.round(3).to_string())
    r = korr.loc["study_hours", "sleep_hours"]
    print()
    print("study_hours – sleep_hours: r = {:.3f} → erős negatív kapcsolat; a többi változóval a".format(r))
    print("sleep_hours a study_hours korrelációit ellentétes előjellel ismétli meg.")

    cim("PCA két komponenssel – négy, illetve öt változóval")
    pca4, eredmeny4 = pca_2d(df, JELLEMZOK)
    pca5, eredmeny5 = pca_2d(df5, JELLEMZOK_ALVASSAL)
    print("Az öt változós eredmény DataFrame-je:")
    print(eredmeny5.head().round(3).to_string(index=False))
    print("...")
    print()
    osszevetes = pd.DataFrame({
        "4 változó (3. feladat)": np.append(pca4.explained_variance_ratio_,
                                            pca4.explained_variance_ratio_.sum()),
        "5 változó (+ sleep_hours)": np.append(pca5.explained_variance_ratio_,
                                               pca5.explained_variance_ratio_.sum()),
    }, index=["PC1", "PC2", "kumulált"])
    osszevetes["változás (%-pont)"] = 100 * (osszevetes.iloc[:, 1] - osszevetes.iloc[:, 0])
    print(osszevetes.to_string(formatters={
        "4 változó (3. feladat)": "{:.2%}".format,
        "5 változó (+ sleep_hours)": "{:.2%}".format,
        "változás (%-pont)": "{:+.2f}".format}))

    cim("Mennyivel változott az első két főkomponens kumulált varianciaaránya?")
    kul = osszevetes.loc["kumulált", "változás (%-pont)"]
    print("{:.2%} → {:.2%}, azaz {:+.2f} százalékpont.".format(
        osszevetes.iloc[2, 0], osszevetes.iloc[2, 1], kul))
    print("A PC1 aránya különösen megnőtt ({:.2%} → {:.2%}): a két, szinte azonos információt".format(
        osszevetes.iloc[0, 0], osszevetes.iloc[0, 1]))
    print("hordozó változó együtt kb. két egységnyi varianciát ad, és ezt egyetlen komponens")
    print("(a „tanulás kontra alvás” tengely) össze tudja fogni.")
    print()
    m4 = megorzes(df, JELLEMZOK, pca4, JELLEMZOK)
    m5 = megorzes(df5, JELLEMZOK_ALVASSAL, pca5, JELLEMZOK)
    print("Az EREDETI négy változó varianciájából a két komponens által visszaadott rész:")
    tabla = pd.DataFrame({"4 változós PCA": m4, "5 változós PCA": m5})
    print(tabla.to_string(formatters={c: "{:.1%}".format for c in tabla.columns}))
    print("összesen: {:.1%} → {:.1%}".format(m4.mean(), m5.mean()))
    print()
    print("A varianciaarányokat már az ötváltozós adathalmazra számítjuk, ezért a növekedés")
    print("nem jelenti az eredeti négy változó jobb megőrzését – sőt, itt az eredeti négy")
    print("változóból kevesebb marad meg ({:.1%} → {:.1%}). Az egyik komponenst lényegében a".format(
        m4.mean(), m5.mean()))
    print("megduplázott tanulási idő foglalja le (study_hours: {:.1%}), az attendance és az".format(
        m5["study_hours"]))
    print("assignments_completed rovására.")

    cim("Miért jelent redundanciát az erős negatív korreláció is?")
    print("A redundancia azt jelenti, hogy egy változó értéke a másikból jól előre jelezhető.")
    print("Ehhez a korreláció abszolút értéke számít, nem az előjele: r = {:.2f} esetén a".format(r))
    print("sleep_hours varianciájának {:.0%}-át a study_hours lineárisan megmagyarázza (r²).".format(r ** 2))
    print("A sleep_hours tehát csak a study_hours „tükörképe” (standardizálva közel a")
    print("−1-szerese), új információt nem hordoz. A PCA-ban ez az előjelekben látszik: a két")
    print("változó azonos nagyságú, ellentétes előjelű súllyal kerül ugyanarra a komponensre.")

    cim("Jobban elkülönülnek-e a passed szerinti csoportok?")
    print("A csoportközéppontok távolsága a közös szórás egységében:")
    print("  {:<16} {:>10} {:>10}".format("", "4 változó", "5 változó"))
    print("  {:<16} {:>10.2f} {:>10.2f}".format("PC1 mentén", elkulonules(eredmeny4, ["PC1"]),
                                                elkulonules(eredmeny5, ["PC1"])))
    print("  {:<16} {:>10.2f} {:>10.2f}".format("PC1–PC2 síkban", elkulonules(eredmeny4),
                                                elkulonules(eredmeny5)))
    print()
    print("Lényegesen nem. A síkban mért távolság csak kicsit változik, a pontfelhők ugyanúgy")
    print("átfedik egymást. A PC1 mentén az elkülönülés még gyengül is, mert az ötváltozós")
    print("PC1-et a tanulás–alvás tengely uralja, a sikerességgel jobban összefüggő previous_gpa")
    print("a PC2-re szorul. Új, független információ nélkül jobb szétválás nem várható.")

    fig = plt.figure(figsize=(18, 6.4))
    racs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1, 1])
    ax_hot = fig.add_subplot(racs[0])
    kep = heatmap(ax_hot, korr)
    fig.colorbar(kep, ax=ax_hot, shrink=0.8)
    ax_hot.set_title("Korrelációs mátrix (sleep_hours-szal)", loc="left", fontsize=11)
    pontdiagram(fig.add_subplot(racs[1]), eredmeny4, "passed",
                "4 változó – kumulált {:.2%}".format(pca4.explained_variance_ratio_.sum()),
                pca4.explained_variance_ratio_)
    pontdiagram(fig.add_subplot(racs[2]), eredmeny5, "passed",
                "5 változó (+ sleep_hours) – kumulált {:.2%}".format(
                    pca5.explained_variance_ratio_.sum()),
                pca5.explained_variance_ratio_)
    fig.suptitle("Redundáns változó hatása a PCA-ra", fontsize=13)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.2)   # a hőtérkép ferde tengelyfeliratainak helye
    fig.savefig(os.path.join(MAPPA, "04_redundans_valtozo.png"), dpi=120)
    plt.show()


if __name__ == "__main__":
    main()
