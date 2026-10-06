# -*- coding: utf-8 -*-
"""3. Lineáris és monoton kapcsolat összehasonlítása.

Szimulált adatok (rng seed = 42), három változópár:
  1. lineáris kapcsolat,
  2. monoton, de nem lineáris kapcsolat,
  3. kapcsolat nélküli változók.

Pontdiagramot készítünk, és mindhárom esetben kiszámítjuk a Pearson- és a
Spearman-korrelációt. A monoton esetnél a rangok pontdiagramját is
megmutatjuk: a Spearman valójában a rangokra számolt Pearson-korreláció.
"""

import os

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

MAPPA = os.path.dirname(os.path.abspath(__file__))

SZIN = "#2a78d6"
SZIN2 = "#eb6834"
SZOVEG_SZIN = "#0b0b0b"
RACS_SZIN = "#e5e4df"


def cim(szoveg):
    """Szakaszcím a kimenetben."""
    print()
    print("=" * 70)
    print(szoveg)
    print("=" * 70)


def ax_formaz(ax, cim_szoveg, xlabel, ylabel):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim_szoveg, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def adatok():
    rng = np.random.default_rng(42)
    x = np.linspace(1, 10, 50)
    y_linear = 3 * x + rng.normal(0, 2, 50)
    y_monotonic = x**2 + rng.normal(0, 3, 50)
    y_random = rng.normal(0, 20, 50)
    return x, {
        "lineáris": y_linear,
        "monoton, nem lineáris": y_monotonic,
        "kapcsolat nélküli": y_random,
    }


def abra(x, esetek, eredmenyek):
    fig, tengelyek = plt.subplots(1, 4, figsize=(17, 4.6))
    for ax, (nev, y) in zip(tengelyek, esetek.items()):
        e = eredmenyek[nev]
        ax.scatter(x, y, s=26, color=SZIN, alpha=0.7, edgecolor="white", linewidth=0.5)
        meredekseg, metszet = np.polyfit(x, y, 1)
        ax.plot(x, metszet + meredekseg * x, color=SZIN2, linewidth=2,
                label="illesztett egyenes")
        ax_formaz(ax, "{}\nPearson r = {:.3f},  Spearman ρ = {:.3f}".format(
            nev, e["pearson"], e["spearman"]), "x", "y")

    # A Spearman a rangokra számolt Pearson: a monoton görbe rangjai egy egyenesre esnek.
    y_mon = esetek["monoton, nem lineáris"]
    rang_x, rang_y = stats.rankdata(x), stats.rankdata(y_mon)
    ax = tengelyek[3]
    ax.scatter(rang_x, rang_y, s=26, color=SZIN2, alpha=0.7, edgecolor="white", linewidth=0.5)
    ax.plot([1, len(x)], [1, len(x)], color=SZOVEG_SZIN, linewidth=1, linestyle="--")
    ax_formaz(ax, "monoton eset rangjai\nPearson(rangok) = {:.3f}".format(
        np.corrcoef(rang_x, rang_y)[0, 1]), "x rangja", "y rangja")

    tengelyek[0].legend(loc="upper left", frameon=False, fontsize=9)
    fig.suptitle("Lineáris, monoton és kapcsolat nélküli változópárok", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "03_linearis_monoton.png"), dpi=120)


def main():
    x, esetek = adatok()

    cim("Pearson- és Spearman-korreláció a három esetben")
    eredmenyek = {}
    print("  {:<24} {:>10} {:>10} {:>10} {:>10}".format(
        "eset", "Pearson r", "p", "Spearman ρ", "p"))
    for nev, y in esetek.items():
        p = stats.pearsonr(x, y)
        s = stats.spearmanr(x, y)
        eredmenyek[nev] = {"pearson": p.statistic, "spearman": s.statistic}
        print("  {:<24} {:>10.3f} {:>10.2e} {:>10.3f} {:>10.2e}".format(
            nev, p.statistic, p.pvalue, s.statistic, s.pvalue))

    # A lineáris illesztés hibája a monoton esetben: a reziduumok rendszeres mintázatot mutatnak.
    y_mon = esetek["monoton, nem lineáris"]
    meredekseg, metszet = np.polyfit(x, y_mon, 1)
    rezid = y_mon - (metszet + meredekseg * x)
    harmad = len(x) // 3
    print()
    print("A monoton eset egyenes körüli reziduumainak átlaga szakaszonként:")
    print("  eleje: {:+.1f}, közepe: {:+.1f}, vége: {:+.1f}  (U alak → a kapcsolat görbült)".format(
        rezid[:harmad].mean(), rezid[harmad:-harmad].mean(), rezid[-harmad:].mean()))

    lin, mon, ves = (eredmenyek[nev] for nev in esetek)
    cim("Értelmezés")
    print("Melyik mutató méri elsősorban a lineáris kapcsolatot?")
    print("  A Pearson-korreláció. A lineáris esetben r = {:.3f}, ρ = {:.3f}: amikor a pontok"
          .format(lin["pearson"], lin["spearman"]))
    print("  egy egyenes körül szóródnak, a két mutató szinte azonos.")
    print()
    print("Melyik mutató érzékeli jobban a nem lineáris, de monoton kapcsolatot?")
    print("  A Spearman-korreláció: ρ = {:.3f} > r = {:.3f}. Az x² az [1; 10] szakaszon"
          .format(mon["spearman"], mon["pearson"]))
    print("  szigorúan növekvő, így a két rangsor szinte egyezik, a Spearman ezért 1 közeli.")
    print("  A Pearson is magas, mert az 1–10 tartományon az x² még jól közelíthető egyenessel,")
    print("  de a reziduumok U alakja és a pontdiagram is mutatja, hogy a kapcsolat nem lineáris.")
    print()
    print("Mi történik kapcsolat nélküli változók esetén?")
    print("  Mindkét mutató 0 közeli (r = {:.3f}, ρ = {:.3f}), és a p-értékek alapján nem"
          .format(ves["pearson"], ves["spearman"]))
    print("  különböznek szignifikánsan 0-tól: nincs sem lineáris, sem monoton kapcsolat.")

    cim("Fő következtetés")
    print("- A Pearson-korreláció a lineáris kapcsolat erősségét méri.")
    print("- A Spearman-korreláció a monoton kapcsolatot méri a rangsorok alapján.")
    print("- Az erős Spearman-korreláció nem feltétlenül jelent lineáris kapcsolatot.")

    abra(x, esetek, eredmenyek)
    plt.show()


if __name__ == "__main__":
    main()
