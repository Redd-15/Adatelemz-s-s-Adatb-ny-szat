# -*- coding: utf-8 -*-
"""4. Hiányzó adatok feltárása.

Bemenet: student_performance_cleaned-NEW.csv

Meghatározzuk változónként a hiányzó értékek számát és arányát, a hiányos
rekordok számát, és azt, hogy mely változók hiányoznak gyakran együtt.
Végül megvizsgáljuk, hogy a hiányzó exam_score összefügg-e más
változókkal (például az óralátogatással).
"""

import os
from itertools import combinations

import pandas as pd
import matplotlib.pyplot as plt

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_cleaned-NEW.csv")

NUMERIKUS = ["study_hours", "attendance", "previous_gpa",
             "assignments_completed", "exam_score"]
EGESZ = ["assignments_completed"]

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


def beolvas():
    """Beolvasás; a fájl mezői szóközökkel vannak kitöltve, ezért mindent levágunk."""
    df = pd.read_csv(BEMENET, sep=";", encoding="utf-8", dtype="string")
    df.columns = [nev.strip() for nev in df.columns]
    for oszlop in df.columns:
        # a szóközzel feltöltött mezőkből üres sztring lesz, az pedig hiányzó érték
        df[oszlop] = df[oszlop].str.strip().replace("", pd.NA)
    for oszlop in NUMERIKUS:
        df[oszlop] = pd.to_numeric(
            df[oszlop].str.replace(",", ".", regex=False), errors="coerce")
    for oszlop in EGESZ:
        df[oszlop] = df[oszlop].round().astype("Int64")
    return df


def ax_formaz(ax, cim_szoveg, xlabel, ylabel):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim_szoveg, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def osszefoglalo_tabla(df):
    """Változó, hiányzó értékek száma, hiányzó értékek aránya."""
    tabla = pd.DataFrame({
        "változó": df.columns,
        "hiányzó_db": df.isna().sum().to_numpy(),
        "hiányzó_arány_%": (df.isna().mean() * 100).round(1).to_numpy(),
    })
    return tabla.sort_values("hiányzó_db", ascending=False).reset_index(drop=True)


def egyutt_hianyzas(df):
    """Mely változópárok hiányoznak gyakran együtt?"""
    hianyzik = df.isna()
    erintett = [oszlop for oszlop in df.columns if hianyzik[oszlop].any()]
    parok = []
    for a, b in combinations(erintett, 2):
        egyutt = int((hianyzik[a] & hianyzik[b]).sum())
        if egyutt:
            # feltételes arány: ha A hiányzik, milyen gyakran hiányzik B is
            parok.append({
                "változó_1": a,
                "változó_2": b,
                "együtt_db": egyutt,
                "A_hiányzóin_belül_%": round(100 * egyutt / int(hianyzik[a].sum()), 1),
                "B_hiányzóin_belül_%": round(100 * egyutt / int(hianyzik[b].sum()), 1),
            })
    return pd.DataFrame(parok).sort_values("együtt_db", ascending=False) \
        if parok else pd.DataFrame()


def hianyzasi_mintak(df):
    """A hiányzás mintázatai: mely oszlopok hiányoznak egyszerre egy rekordban."""
    hianyzik = df.isna()
    erintett = [oszlop for oszlop in df.columns if hianyzik[oszlop].any()]
    minta = hianyzik[erintett].apply(
        lambda sor: ", ".join([oszlop for oszlop in erintett if sor[oszlop]]) or "(nincs hiányzó)",
        axis=1)
    return minta.value_counts()


def exam_score_vizsgalat(df):
    """Összefügg-e a hiányzó exam_score más változókkal?"""
    csoport = df["exam_score"].isna().map({True: "nincs eredmény", False: "van eredmény"})
    osszehasonlitando = [oszlop for oszlop in NUMERIKUS if oszlop != "exam_score"]

    print("Csoportlétszámok:")
    print(csoport.value_counts().to_string())
    print()
    print("Numerikus változók átlaga és mediánja a két csoportban:")
    stat = df.groupby(csoport)[osszehasonlitando].agg(["mean", "median", "count"])
    print(stat.round(2).to_string())

    print()
    print("Az óralátogatás részletesen:")
    for nev, reszlet in df.groupby(csoport)["attendance"]:
        ertekek = reszlet.dropna()
        print("  {:<16} n = {:>3}, átlag = {:>6.2f}, medián = {:>6.2f}, "
              "min = {:>5.1f}, max = {:>5.1f}".format(
                  str(nev), len(ertekek), ertekek.mean(), ertekek.median(),
                  ertekek.min(), ertekek.max()))

    print()
    print("Képzés szerinti megoszlás a két csoportban (%):")
    megoszlas = pd.crosstab(df["programme"], csoport, normalize="columns") * 100
    print(megoszlas.round(1).to_string())
    return csoport


def abrak(df, tabla, csoport):
    """Hiányzási arányok oszlopdiagramon és az óralátogatás a két csoportban."""
    fig, (ax_arany, ax_box) = plt.subplots(1, 2, figsize=(13, 5))

    pozicio = range(len(tabla))
    ax_arany.bar(pozicio, tabla["hiányzó_arány_%"], color=SZIN, alpha=0.85, width=0.7)
    for x, (arany, db) in enumerate(zip(tabla["hiányzó_arány_%"], tabla["hiányzó_db"])):
        if arany > 0:
            ax_arany.text(x, arany + 0.15, "{}%\n({} db)".format(arany, db),
                          ha="center", fontsize=8, color=SZOVEG_SZIN)
    ax_arany.set_xticks(list(pozicio))
    ax_arany.set_xticklabels(tabla["változó"], rotation=30, ha="right", fontsize=9)
    ax_arany.set_ylim(0, max(tabla["hiányzó_arány_%"].max() * 1.3, 1))
    ax_formaz(ax_arany, "Hiányzó értékek aránya változónként", "", "hiányzó (%)")

    # Óralátogatás azoknál, akiknek van, illetve nincs vizsgaeredménye
    csoportnevek = ["van eredmény", "nincs eredmény"]
    adatok = [df.loc[csoport == nev, "attendance"].dropna().to_numpy()
              for nev in csoportnevek]
    doboz = ax_box.boxplot(adatok, patch_artist=True, widths=0.5,
                           medianprops={"color": SZOVEG_SZIN, "linewidth": 2})
    for test, szin in zip(doboz["boxes"], (SZIN, SZIN2)):
        test.set(facecolor=szin, alpha=0.55, edgecolor=szin)
    for x, ertekek in enumerate(adatok, start=1):
        ax_box.text(x, 103, "n = {}\nátlag = {:.1f}".format(len(ertekek), ertekek.mean()),
                    ha="center", fontsize=9, color=SZOVEG_SZIN)
    ax_box.set_xticks([1, 2])
    ax_box.set_xticklabels(csoportnevek)
    ax_box.set_ylim(0, 115)
    ax_formaz(ax_box, "Óralátogatás a vizsgaeredmény hiánya szerint",
              "", "attendance (%)")

    fig.suptitle("Hiányzó adatok feltárása", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "04_hianyzo_adatok.png"), dpi=120)


def main():
    pd.set_option("display.width", 130)
    pd.set_option("display.max_columns", 20)

    df = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    cim("Hiányzó értékek száma (df.isna().sum())")
    print(df.isna().sum().to_string())

    cim("Hiányzó értékek aránya (df.isna().mean())")
    print((df.isna().mean() * 100).round(1).to_string())

    cim("Összefoglaló táblázat")
    tabla = osszefoglalo_tabla(df)
    print(tabla.to_string(index=False))

    cim("Hiányzó értéket tartalmazó rekordok")
    hianyos = df.isna().any(axis=1)
    print("Legalább egy hiányzó értéket tartalmazó rekord: {} db ({:.1f}%)".format(
        int(hianyos.sum()), 100 * hianyos.mean()))
    print("Teljesen kitöltött rekord: {} db".format(int((~hianyos).sum())))
    print()
    print("Rekordonkénti hiányzó értékek száma szerinti megoszlás:")
    print(df.isna().sum(axis=1).value_counts().sort_index().to_string())

    cim("Mely változók hiányoznak gyakran együtt?")
    parok = egyutt_hianyzas(df)
    if parok.empty:
        print("Nincs olyan változópár, amely ugyanabban a rekordban hiányzik.")
    else:
        print(parok.to_string(index=False))
    print()
    print("Hiányzási mintázatok (mely oszlopok hiányoznak egy rekordban):")
    print(hianyzasi_mintak(df).to_string())

    cim("Összefügg-e a hiányzó exam_score más változókkal?")
    csoport = exam_score_vizsgalat(df)

    abrak(df, tabla, csoport)
    plt.show()


if __name__ == "__main__":
    main()
