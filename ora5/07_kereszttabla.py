# -*- coding: utf-8 -*-
"""7. Két kategorikus változó kapcsolata.

Bemenet: student_performance_imputed.csv

Kereszttáblát készítünk a programme és a passed változókból, majd a
programonkénti összehasonlíthatóság érdekében soronkénti százalékos
megoszlást számítunk, és halmozott oszlopdiagramon ábrázoljuk.

A kereszttábla leíró eredményt ad; a két kategorikus változó közötti
kapcsolat statisztikai vizsgálatához khi-négyzet-próba használható.
"""

import os

import pandas as pd
import matplotlib.pyplot as plt

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_imputed.csv")

# a sikeres teljesítés kerül alulra, így az arányok közvetlenül leolvashatók
SORREND = ["yes", "no"]
FELIRAT = {"yes": "sikeres (yes)", "no": "sikertelen (no)"}
SZINEK = {"yes": "#2a78d6", "no": "#eb6834"}
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


def abra(gyakorisag, szazalek):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    programok = list(szazalek.index)
    alap = pd.Series(0.0, index=programok)
    for kimenet in SORREND:
        ertekek = szazalek[kimenet]
        ax.bar(programok, ertekek, bottom=alap, width=0.6, color=SZINEK[kimenet],
               alpha=0.85, label=FELIRAT[kimenet])
        for x, program in enumerate(programok):
            ax.text(x, alap[program] + ertekek[program] / 2,
                    "{:.1f}%\n({} fő)".format(ertekek[program], gyakorisag.loc[program, kimenet]),
                    ha="center", va="center", fontsize=9, color="white")
        alap += ertekek
    # a teljes minta sikerességi aránya viszonyítási vonalként
    osszes = 100 * gyakorisag["yes"].sum() / gyakorisag.to_numpy().sum()
    ax.axhline(osszes, color=SZOVEG_SZIN, linewidth=1, linestyle="--",
               label="sikeresek aránya a teljes mintában ({:.1f}%)".format(osszes))
    ax.set_xticks(range(len(programok)))
    ax.set_xticklabels(["{}\n(n = {})".format(p, gyakorisag.loc[p].sum()) for p in programok])
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3,
              fontsize=9)
    ax_formaz(ax, "Sikeres teljesítés aránya képzési programonként", "", "megoszlás (%)")
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "07_kereszttabla.png"), dpi=120)


def main():
    pd.set_option("display.width", 130)
    df = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    cim("Kereszttábla: programme × passed (gyakoriságok)")
    gyakorisag = pd.crosstab(df["programme"], df["passed"])[SORREND]
    print(pd.crosstab(df["programme"], df["passed"], margins=True,
                      margins_name="összesen")[SORREND + ["összesen"]].to_string())

    cim("Soronkénti százalékos megoszlás (minden program = 100%)")
    szazalek = pd.crosstab(df["programme"], df["passed"], normalize="index")[SORREND] * 100
    teljes = df["passed"].value_counts(normalize=True)[SORREND] * 100
    print(pd.concat([szazalek, teljes.to_frame("összesen").T]).round(1).to_string())
    print()
    print("A nyers gyakoriságok nem hasonlíthatók össze közvetlenül, mert a programok létszáma")
    print("eltér ({}); ezért a soronkénti százalékokat vetjük össze.".format(
        ", ".join("{} fő".format(n) for n in gyakorisag.sum(axis=1))))

    cim("Melyik képzési programban a legmagasabb a sikeres teljesítések aránya?")
    sorrend = szazalek["yes"].sort_values(ascending=False)
    for program, arany in sorrend.items():
        print("  {:<24} {:>5.1f}%  ({} / {} fő)".format(
            program, arany, gyakorisag.loc[program, "yes"], gyakorisag.loc[program].sum()))
    print()
    print("A legmagasabb a {} programban ({:.1f}%), a legalacsonyabb a {} programban ({:.1f}%)."
          .format(sorrend.index[0], sorrend.iloc[0], sorrend.index[-1], sorrend.iloc[-1]))
    print("A különbség {:.1f} százalékpont; a teljes minta sikerességi aránya {:.1f}%.".format(
        sorrend.iloc[0] - sorrend.iloc[-1], teljes["yes"]))
    print("A legkisebb program is csak {} fős, így néhány hallgató is több százalékpontot mozdít"
          .format(gyakorisag.sum(axis=1).min()))
    print("az arányokon.")
    atlag = df.groupby("programme")["exam_score"].agg(["mean", "std"])
    print("Érdemes összevetni a 6. feladattal: a legmagasabb átlagpontszám a {} programé"
          .format(atlag["mean"].idxmax()))
    print("({:.1f} pont), a {} programban viszont a legkisebb a szórás ({:.1f}), ezért ott".format(
        atlag["mean"].max(), atlag["std"].idxmin(), atlag["std"].min()))
    print("esnek a legkevesebben a sikeres teljesítés határa alá.")

    cim("Megjegyzés")
    print("A kereszttábla leíró eredményt ad: azt mutatja, hogy ebben a mintában eltérnek az")
    print("arányok. Hogy a programme és a passed között statisztikailag is van-e kapcsolat")
    print("(vagy az eltérés a véletlen mintavételi ingadozás eredménye), azt khi-négyzet-próbával")
    print("lehet vizsgálni.")

    abra(gyakorisag, szazalek)
    plt.show()


if __name__ == "__main__":
    main()
