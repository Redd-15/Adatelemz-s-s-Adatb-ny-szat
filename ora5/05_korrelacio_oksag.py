# -*- coding: utf-8 -*-
"""5. Korrelációs és oksági kapcsolat.

Bemenet: student_performance_imputed.csv

Megvizsgáljuk a study_hours és az exam_score kapcsolatát, majd azt, hogy
mennyit változik ez a kapcsolat, ha a többi mért változó hatását kiszűrjük
(parciális korreláció), illetve képzési programonként. Végül szövegesen
megválaszoljuk, hogy a korrelációból következik-e oksági kapcsolat.

Fontos: a korreláció nem jelent oksági kapcsolatot.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_imputed.csv")

X, Y = "study_hours", "exam_score"
KONTROLL = ["previous_gpa", "attendance", "assignments_completed"]

SZIN = "#2a78d6"
SZIN2 = "#eb6834"
SZOVEG_SZIN = "#0b0b0b"
RACS_SZIN = "#e5e4df"
PROGRAM_SZINEK = ["#2a78d6", "#eb6834", "#1f9e6e"]


def cim(szoveg):
    """Szakaszcím a kimenetben."""
    print()
    print("=" * 70)
    print(szoveg)
    print("=" * 70)


def beolvas():
    return pd.read_csv(BEMENET, sep=";", encoding="utf-8")


def ax_formaz(ax, cim_szoveg, xlabel, ylabel):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim_szoveg, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def reziduum(df, cel, magyarazok):
    """A cél változó lineáris regressziós reziduuma a magyarázó változókra."""
    M = np.column_stack([np.ones(len(df))] + [df[v].to_numpy(dtype=float) for v in magyarazok])
    y = df[cel].to_numpy(dtype=float)
    b, *_ = np.linalg.lstsq(M, y, rcond=None)
    return y - M @ b


def parcialis(df, kontroll):
    """X és Y parciális korrelációja: a kontrollváltozók hatását mindkettőből kiszűrjük."""
    rx = reziduum(df, X, kontroll)
    ry = reziduum(df, Y, kontroll)
    return stats.pearsonr(rx, ry).statistic, rx, ry


def abra(df, rx, ry, r, r_parc):
    fig, (ax_bal, ax_jobb) = plt.subplots(1, 2, figsize=(13, 5.2))

    for (program, resz), szin in zip(df.groupby("programme"), PROGRAM_SZINEK):
        ax_bal.scatter(resz[X], resz[Y], s=28, color=szin, alpha=0.7, edgecolor="white",
                       linewidth=0.5, label=program)
    meredekseg, metszet = np.polyfit(df[X], df[Y], 1)
    vonal = np.linspace(df[X].min(), df[X].max(), 100)
    ax_bal.plot(vonal, metszet + meredekseg * vonal, color=SZOVEG_SZIN, linewidth=1.8)
    ax_bal.legend(frameon=False, fontsize=8, loc="lower right")
    ax_formaz(ax_bal, "Nyers kapcsolat (r = {:.3f})".format(r), X, Y)

    # parciális regressziós ábra: mindkét változóból kiszűrve a kontrollváltozók hatását
    ax_jobb.scatter(rx, ry, s=28, color=SZIN, alpha=0.6, edgecolor="white", linewidth=0.5)
    meredekseg, metszet = np.polyfit(rx, ry, 1)
    vonal = np.linspace(rx.min(), rx.max(), 100)
    ax_jobb.plot(vonal, metszet + meredekseg * vonal, color=SZIN2, linewidth=2)
    ax_jobb.axhline(0, color=RACS_SZIN, linewidth=1)
    ax_formaz(ax_jobb, "GPA, attendance, assignments hatása nélkül (parciális r = {:.3f})"
              .format(r_parc), X + " reziduuma", Y + " reziduuma")

    fig.suptitle("study_hours és exam_score: korreláció ≠ okság", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "05_korrelacio_oksag.png"), dpi=120)


def main():
    df = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    cim("A study_hours és az exam_score kapcsolata")
    pearson = stats.pearsonr(df[X], df[Y])
    spearman = stats.spearmanr(df[X], df[Y])
    meredekseg, metszet = np.polyfit(df[X], df[Y], 1)
    r = pearson.statistic
    print("Pearson r = {:.3f} (p = {:.2e}), Spearman ρ = {:.3f}".format(
        r, pearson.pvalue, spearman.statistic))
    print("R² = {:.3f}: a tanulási idő a vizsgapontszám szórásának ~{:.0f}%-ával együtt mozog.".format(
        r ** 2, 100 * r ** 2))
    print("Regressziós egyenes: exam_score = {:.2f} + {:.2f} · study_hours".format(metszet, meredekseg))
    print("→ egy további tanulási óra átlagosan {:.2f} ponttal magasabb eredménnyel JÁR EGYÜTT".format(
        meredekseg))
    print("  (ez leíró összefüggés, nem azt jelenti, hogy egy óra tanulás {:.2f} pontot OKOZ).".format(
        meredekseg))

    cim("Változik-e a kapcsolat, ha más változókat is figyelembe veszünk?")
    print("study_hours korrelációja a többi mért változóval:")
    for v in KONTROLL:
        print("  {:<22} r = {:>6.3f}".format(v, df[X].corr(df[v])))
    print()
    print("Parciális korreláció (a kontrollváltozók hatását X-ből és Y-ból is kiszűrve):")
    for kontroll in ([v] for v in KONTROLL):
        print("  kontroll: {:<34} r = {:.3f}".format(", ".join(kontroll), parcialis(df, kontroll)[0]))
    r_parc, rx, ry = parcialis(df, KONTROLL)
    print("  kontroll: {:<34} r = {:.3f}".format("mind a három", r_parc))
    print()
    print("Képzési programonként:")
    for program, resz in df.groupby("programme"):
        print("  {:<24} n = {:>3}, r = {:.3f}".format(program, len(resz), resz[X].corr(resz[Y])))
    print()
    print("A három mért változó együttes kiszűrése után is megmarad a kapcsolat ({:.3f} → {:.3f}),"
          .format(r, r_parc))
    print("mert a study_hours alig korrelál velük. Az attendance kiszűrése kissé gyengíti, mert")
    print("a tanulás és az órára járás enyhén együtt mozog; az assignments_completed kiszűrése")
    print("erősíti, mert az a study_hours-szal negatívan, az exam_score-ral pozitívan függ össze.")
    print("Ez azonban NEM bizonyítja az okságot: csak azokat a tényezőket tudjuk kiszűrni,")
    print("amelyeket mértünk. A motiváció, a tárgy nehézsége vagy az előzetes ismeretek nagy része")
    print("nem szerepel az adatbázisban. A kapcsolat programonként is eltérő erősségű.")

    cim("1. Következik-e a korrelációból, hogy a több tanulás önmagában magasabb eredményt okoz?")
    print("Nem. A pozitív korreláció csak annyit mond, hogy a többet tanuló hallgatók átlagosan")
    print("jobb eredményt érnek el. Megfigyelési adatokból (nem kontrollált kísérletből) az")
    print("együttmozgás oka nem állapítható meg: lehet, hogy a tanulás hat az eredményre, de")
    print("lehet, hogy egy harmadik tényező hat mindkettőre. Oksági következtetéshez véletlen")
    print("besorolású kísérlet vagy speciális oksági módszertan kellene.")

    cim("2. Milyen további változók befolyásolhatják mindkettőt? (zavaró változók)")
    print("- Hallgatói motiváció, ambíció: a motivált hallgató többet tanul ÉS jobban is teljesít.")
    print("- Előzetes ismeretek, képességek: aki jobban érti az anyagot, másképp tanul és jobb")
    print("  eredményt ér el (részben a previous_gpa méri).")
    print("- A tantárgy / program nehézsége: nehezebb tárgyon többet kell tanulni, és a pontszámok")
    print("  is alacsonyabbak lehetnek, ez akár el is fedheti a valódi hatást.")
    print("- Szabadidő, munkavállalás, anyagi helyzet: a dolgozó hallgatónak kevesebb ideje")
    print("  van tanulni és órára járni is.")
    print("- Egészség, alvás, stressz, tanulási módszer: a tanulás minősége nem azonos a")
    print("  mennyiségével.")
    print("- Mérési hiba: a study_hours valószínűleg önbevallás, torzíthat.")

    cim("3. Elképzelhető-e fordított vagy közvetett kapcsolat?")
    print("Fordított kapcsolat: igen. Aki korábban sikerélményt szerzett vagy jól halad,")
    print("motiváltabb, ezért többet tanul – ekkor a jó teljesítmény okozza a több tanulást.")
    print("Ugyanígy a gyengébb hallgató feladhatja és kevesebbet tanul.")
    print("Közvetett kapcsolat: igen. A tanulás hathat közvetítő változókon keresztül, pl. több")
    print("tanulás → jobb megértés → több beadott feladat → jobb vizsga. Az is lehet, hogy a")
    print("két változó csak egy közös okon keresztül függ össze: motiváció → több tanulás, és")
    print("motiváció → rendszeres órára járás → jobb eredmény.")

    cim("Fontos megjegyzés")
    print("A korreláció nem jelent oksági kapcsolatot. A study_hours és az exam_score között")
    print("r = {:.3f} közepes pozitív együttmozgás van, de ebből önmagában nem következik, hogy"
          .format(r))
    print("a tanulási idő növelése automatikusan javítaná a vizsgaeredményt.")

    abra(df, rx, ry, r, r_parc)
    plt.show()


if __name__ == "__main__":
    main()
