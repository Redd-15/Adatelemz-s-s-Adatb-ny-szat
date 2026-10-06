# -*- coding: utf-8 -*-
"""6. Numerikus és kategorikus változó kapcsolata.

Bemenet: student_performance_imputed.csv

Változópárok:
  programme – exam_score,
  passed – study_hours,
  passed – attendance,
  passed – previous_gpa.

Csoportonkénti leíró statisztikákat számítunk (elemszám, átlag, medián,
szórás, kvartilisek, IQR, kiugró értékek száma), és boxplotot készítünk.
A grafikus különbség önmagában nem elég a statisztikai különbség
kimondásához: ahhoz hipotézisvizsgálat (ANOVA) szükséges.
"""

import os

import pandas as pd
import matplotlib.pyplot as plt

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_imputed.csv")

PAROK = [
    ("programme", "exam_score"),
    ("passed", "study_hours"),
    ("passed", "attendance"),
    ("passed", "previous_gpa"),
]

SZIN = "#2a78d6"
SZIN2 = "#eb6834"
SZIN3 = "#1f9e6e"
SZOVEG_SZIN = "#0b0b0b"
RACS_SZIN = "#e5e4df"


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
    ax.grid(axis="y", color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def kiugrok(ertekek):
    """Az 1,5·IQR szabály szerinti kiugró értékek (ugyanez a boxplot bajusza is)."""
    q1, q3 = ertekek.quantile([0.25, 0.75])
    iqr = q3 - q1
    return ertekek[(ertekek < q1 - 1.5 * iqr) | (ertekek > q3 + 1.5 * iqr)]


def csoport_statisztika(df, kat, num):
    stat = df.groupby(kat)[num].agg(
        n="count", átlag="mean", medián="median", szórás="std",
        min="min", Q1=lambda s: s.quantile(0.25), Q3=lambda s: s.quantile(0.75), max="max")
    stat["IQR"] = stat["Q3"] - stat["Q1"]
    stat["CV_%"] = 100 * stat["szórás"] / stat["átlag"]
    stat["kiugró_db"] = df.groupby(kat)[num].apply(lambda s: len(kiugrok(s)))
    return stat


def ertelmez(df, kat, num, stat):
    """A kérdések megválaszolása a csoportstatisztikák alapján."""
    atlag, median, szoras = stat["átlag"], stat["medián"], stat["szórás"]
    print("Átlagok:   legnagyobb {} ({:.2f}), legkisebb {} ({:.2f}), különbség {:.2f}".format(
        atlag.idxmax(), atlag.max(), atlag.idxmin(), atlag.min(), atlag.max() - atlag.min()))
    print("Mediánok:  legnagyobb {} ({:.2f}), legkisebb {} ({:.2f}), különbség {:.2f}".format(
        median.idxmax(), median.max(), median.idxmin(), median.min(), median.max() - median.min()))
    # a különbséget a teljes minta szórásához viszonyítjuk, hogy a változók összevethetők legyenek
    relativ = (atlag.max() - atlag.min()) / df[num].std()
    print("           az átlagkülönbség a teljes szórás {:.0%}-a → {}".format(
        relativ, "kicsi" if relativ < 0.3 else "mérsékelt" if relativ < 0.6 else "jelentős"))
    print("Szóródás:  szórás {:.2f} – {:.2f}, arányuk {:.2f} → {}".format(
        szoras.min(), szoras.max(), szoras.max() / szoras.min(),
        "hasonló szóródás" if szoras.max() / szoras.min() < 1.5 else "eltérő szóródás"))
    for csoport, resz in df.groupby(kat)[num]:
        k = kiugrok(resz)
        if len(k):
            print("Kiugró:    {}: {}".format(
                csoport, ", ".join("{} = {:g}".format(df.loc[i, "student_id"], v)
                                   for i, v in k.items())))
    if stat["kiugró_db"].sum() == 0:
        print("Kiugró:    egyik csoportban sincs az 1,5·IQR szabály szerint.")


def boxplot(ax, df, kat, num):
    csoportok = sorted(df[kat].unique())
    adatok = [df.loc[df[kat] == cs, num].to_numpy() for cs in csoportok]
    doboz = ax.boxplot(adatok, patch_artist=True, widths=0.55,
                       medianprops={"color": SZOVEG_SZIN, "linewidth": 2},
                       flierprops={"marker": "o", "markerfacecolor": SZIN2,
                                   "markeredgecolor": SZIN2, "markersize": 5})
    for test, szin in zip(doboz["boxes"], (SZIN, SZIN2, SZIN3)):
        test.set(facecolor=szin, alpha=0.45, edgecolor=szin)
    # az átlagot rombusszal jelöljük, hogy a mediánnal össze lehessen vetni
    for x, ertekek in enumerate(adatok, start=1):
        ax.scatter(x, ertekek.mean(), marker="D", color=SZOVEG_SZIN, s=30, zorder=3)
    ax.set_xticks(range(1, len(csoportok) + 1))
    ax.set_xticklabels(["{}\n(n = {})".format(cs, len(a)) for cs, a in zip(csoportok, adatok)],
                       fontsize=9)
    ax_formaz(ax, "{} szerint: {}".format(kat, num), "", num)


def main():
    pd.set_option("display.width", 150)
    pd.set_option("display.max_columns", 20)
    df = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    fig, tengelyek = plt.subplots(2, 2, figsize=(13, 9))
    for (kat, num), ax in zip(PAROK, tengelyek.flat):
        cim("{} – {}".format(kat, num))
        stat = csoport_statisztika(df, kat, num)
        print(stat.round(2).to_string())
        print()
        ertelmez(df, kat, num, stat)
        boxplot(ax, df, kat, num)

    cim("Összegzés")
    print("- programme – exam_score: a Business Informatics átlaga és mediánja a legmagasabb,")
    print("  de a különbségek (néhány pont) kicsik a ~20 pontos csoporton belüli szóráshoz")
    print("  képest, a dobozok nagyrészt átfedik egymást. A Mechanical Engineering szóródása")
    print("  a legkisebb.")
    print("- passed – study_hours / attendance / previous_gpa: a sikeres hallgatóknál mindhárom")
    print("  változó átlaga és mediánja magasabb. A legnagyobb, legtisztább eltolódás a")
    print("  previous_gpa-nál látszik; az attendance-nál a dobozok erősen átfedik egymást.")
    print("- A csoporton belüli szóródás nagyjából hasonló, kiugró értékek csak elvétve vannak.")
    print()
    print("Elegendő-e a grafikus különbség ahhoz, hogy statisztikailag is különbséget állítsunk?")
    print("NEM. A boxplot és a csoportátlagok csak leírják a mintát. Hogy a különbség a")
    print("véletlen mintavételi ingadozásnál nagyobb-e, azt hipotézisvizsgálattal kell eldönteni:")
    print("több csoportnál (programme) ANOVA-val, két csoportnál (passed) kétmintás t-próbával")
    print("(ami a két csoportos ANOVA-val egyenértékű), illetve nem normális eloszlásnál")
    print("Kruskal–Wallis- vagy Mann–Whitney-próbával.")
    print()
    hatar = df.groupby("passed")["exam_score"].agg(["min", "max"])
    print("(A passed változó az exam_score-ból képzett – sikertelen ≤ {:g} pont, sikeres ≥ {:g} –,"
          .format(hatar.loc["no", "max"], hatar.loc["yes", "min"]))
    print("ezért a passed – exam_score párt nem vizsgáljuk: az definíció szerint különbözik.)")

    fig.suptitle("Numerikus változók eloszlása csoportonként (◆ = átlag)", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "06_numerikus_kategorikus.png"), dpi=120)
    plt.show()


if __name__ == "__main__":
    main()
