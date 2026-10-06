# -*- coding: utf-8 -*-
"""8. Hiányzó és kiugró értékek hatása a korrelációra.

Bemenet: student_performance_cleaned-NEW.csv (a tisztított adathalmaz a
hiányzó és kiugró értékek pótlása, kezelése előtt; az ora3-4 mappából másolva)

A study_hours és az exam_score Pearson- és Spearman-korrelációját
ötféle adatkezelés mellett számítjuk ki:
  1. a hiányzó értéket tartalmazó rekordok elhagyásával,
  2. a study_hours hiányzó értékeinek mediánnal történő pótlása után,
  3. a kiugró értékek megtartásával,
  4. a kiugró értékek eltávolítása után,
  5. az IQR-határokra történő korlátozás (clipping) után.
A 3–5. változat a teljes rekordokon (1. változat) dolgozik, így csak a
kiugró értékek kezelésében tér el egymástól.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_cleaned-NEW.csv")

X, Y = "study_hours", "exam_score"

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
    """Beolvasás; a fájl mezői szóközökkel vannak kitöltve, ezért mindent levágunk."""
    df = pd.read_csv(BEMENET, sep=";", encoding="utf-8", dtype="string")
    df.columns = [nev.strip() for nev in df.columns]
    for oszlop in df.columns:
        df[oszlop] = df[oszlop].str.strip().replace("", pd.NA)
    for oszlop in (X, Y):
        df[oszlop] = pd.to_numeric(
            df[oszlop].str.replace(",", ".", regex=False), errors="coerce").astype(float)
    return df


def ax_formaz(ax, cim_szoveg, xlabel, ylabel, racs="both"):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim_szoveg, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis=racs, color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def iqr_hatarok(sorozat):
    """Q1 − 1,5·IQR és Q3 + 1,5·IQR."""
    q1, q3 = sorozat.quantile([0.25, 0.75])
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def korrelaciok(adat):
    """n, Pearson és Spearman a study_hours – exam_score párra."""
    adat = adat[[X, Y]].dropna()
    return {
        "n": len(adat),
        "pearson_r": stats.pearsonr(adat[X], adat[Y]).statistic,
        "spearman_rho": stats.spearmanr(adat[X], adat[Y]).statistic,
    }


def valtozatok(df):
    """Az öt adatkezelési változat adatai."""
    teljes = df.dropna(subset=[X, Y])

    median = df[X].median()
    potolt = df.copy()
    potolt[X] = potolt[X].fillna(median)

    also, felso = iqr_hatarok(teljes[X])
    kiugro = (teljes[X] < also) | (teljes[X] > felso)
    korlatozott = teljes.copy()
    korlatozott[X] = korlatozott[X].clip(lower=also, upper=felso)

    return {
        "1. hiányzók elhagyása": teljes,
        "2. study_hours mediánnal pótolva": potolt,
        "3. kiugrók megtartása": teljes,
        "4. kiugrók eltávolítása": teljes[~kiugro],
        "5. korlátozás IQR-határra": korlatozott,
    }, {"median": median, "also": also, "felso": felso, "kiugro": teljes[kiugro]}


def abra(df, adatok, info, tabla):
    fig, (ax_pont, ax_oszlop) = plt.subplots(1, 2, figsize=(14, 5.4),
                                            gridspec_kw={"width_ratios": [1, 1.15]})

    teljes = adatok["1. hiányzók elhagyása"]
    kiugro = info["kiugro"]
    normal = teljes.drop(index=kiugro.index)
    ax_pont.scatter(normal[X], normal[Y], s=26, color=SZIN, alpha=0.6, edgecolor="white",
                    linewidth=0.5, label="teljes rekord")
    ax_pont.scatter(kiugro[X], kiugro[Y], s=60, color=SZIN2, edgecolor=SZOVEG_SZIN,
                    linewidth=0.8, label="kiugró study_hours", zorder=3)
    for i, sor in kiugro.iterrows():
        ax_pont.annotate(df.loc[i, "student_id"], (sor[X], sor[Y]), xytext=(0, 8),
                         textcoords="offset points", fontsize=8, ha="center")
    potoltak = df[df[X].isna() & df[Y].notna()]
    ax_pont.scatter(np.full(len(potoltak), info["median"]), potoltak[Y], s=40, marker="s",
                    color=SZIN3, alpha=0.85, label="mediánnal pótolt ({:.2f} óra)".format(
                        info["median"]), zorder=3)
    ax_pont.axvline(info["felso"], color=SZOVEG_SZIN, linewidth=1, linestyle="--",
                    label="IQR felső határ ({:.2f})".format(info["felso"]))
    ax_pont.legend(frameon=False, fontsize=8, loc="lower right")
    ax_formaz(ax_pont, "study_hours és exam_score a pótlás előtt", X, Y)

    pozicio = np.arange(len(tabla))
    szelesseg = 0.38
    for eltolas, oszlop, szin, felirat in (
            (-szelesseg / 2, "pearson_r", SZIN, "Pearson r"),
            (szelesseg / 2, "spearman_rho", SZIN2, "Spearman ρ")):
        ax_oszlop.bar(pozicio + eltolas, tabla[oszlop], width=szelesseg, color=szin,
                      alpha=0.85, label=felirat)
        for x, ertek in zip(pozicio + eltolas, tabla[oszlop]):
            ax_oszlop.text(x, ertek + 0.005, "{:.3f}".format(ertek), ha="center",
                           fontsize=8, color=SZOVEG_SZIN)
    ax_oszlop.set_xticks(pozicio)
    rovid = ["1. elhagyás", "2. medián-\npótlás", "3. kiugrók\nmegtartása",
             "4. kiugrók\neltávolítása", "5. korlátozás\nIQR-határra"]
    ax_oszlop.set_xticklabels(["{}\n(n = {})".format(nev, n)
                               for nev, n in zip(rovid, tabla["n"])], fontsize=8)
    ax_oszlop.set_ylim(0.25, 0.42)
    ax_oszlop.legend(frameon=False, fontsize=9, loc="upper right", ncol=2)
    ax_formaz(ax_oszlop, "Korreláció adatkezelési módszerenként (a tengely 0.25-nél indul)",
              "", "együttható", racs="y")

    fig.suptitle("Hiányzó és kiugró értékek hatása a korrelációra", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "08_hianyzo_kiugro_hatas.png"), dpi=120)


def main():
    pd.set_option("display.width", 130)
    df = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    cim("Hiányzó értékek a vizsgált két változóban")
    print("study_hours hiányzik: {} rekord, exam_score hiányzik: {} rekord, mindkettő: {}".format(
        int(df[X].isna().sum()), int(df[Y].isna().sum()),
        int((df[X].isna() & df[Y].isna()).sum())))
    print("Teljes rekord a két változóra: {}; minden változóra: {}".format(
        len(df.dropna(subset=[X, Y])), len(df.dropna())))
    print()
    print("A study_hours-hiányos rekordok vizsgaeredménye:")
    print(df.loc[df[X].isna(), ["student_id", X, Y]].to_string(index=False))

    adatok, info = valtozatok(df)

    cim("Kiugró értékek a study_hours-ban (IQR-módszer, teljes rekordokon)")
    print("IQR-határok: [{:.2f}; {:.2f}]".format(info["also"], info["felso"]))
    print(df.loc[info["kiugro"].index, ["student_id", X, Y]].to_string(index=False))
    also_y, felso_y = iqr_hatarok(adatok["1. hiányzók elhagyása"][Y])
    print("Az exam_score-ban nincs kiugró érték (határok: [{:.1f}; {:.1f}], tartomány 0–100)."
          .format(also_y, felso_y))
    print("A mediánnal pótolt érték: {:.2f} óra".format(info["median"]))

    cim("Összefoglaló táblázat")
    tabla = pd.DataFrame({nev: korrelaciok(adat) for nev, adat in adatok.items()}).T
    tabla["n"] = tabla["n"].astype(int)
    alap = tabla.loc["1. hiányzók elhagyása"]
    tabla["Δ_pearson"] = tabla["pearson_r"] - alap["pearson_r"]
    tabla["Δ_spearman"] = tabla["spearman_rho"] - alap["spearman_rho"]
    print(tabla.to_string(formatters={
        "pearson_r": "{:.3f}".format, "spearman_rho": "{:.3f}".format,
        "Δ_pearson": "{:+.3f}".format, "Δ_spearman": "{:+.3f}".format}))
    print("(Δ: eltérés az 1. változattól; a 3. változat adatai azonosak az 1.-vel, ez a viszonyítási alap.)")

    cim("Mennyire változtak meg az együtthatók?")
    print("Pearson:  {:.3f} – {:.3f} (terjedelem {:.3f})".format(
        tabla["pearson_r"].min(), tabla["pearson_r"].max(), np.ptp(tabla["pearson_r"])))
    print("Spearman: {:.3f} – {:.3f} (terjedelem {:.3f})".format(
        tabla["spearman_rho"].min(), tabla["spearman_rho"].max(), np.ptp(tabla["spearman_rho"])))
    print("Minden változatban közepes erősségű pozitív kapcsolat marad, az irány és a minősítés")
    print("nem változik. Érdemi (0.01-nél nagyobb) változást egyedül a kiugró értékek")
    print("eltávolítása okoz: a két legtöbbet tanuló hallgató (32 és 29 óra) egyben a legjobb")
    print("eredményt elérők közé tartozik (93–94 pont), így ők erősítik a pozitív trendet.")

    cim("Melyik mutató kevésbé érzékeny a kiugró értékekre?")
    kiugro_valt = ["4. kiugrók eltávolítása", "5. korlátozás IQR-határra"]
    for nev in kiugro_valt:
        print("  {:<28} Δ Pearson = {:+.3f}, Δ Spearman = {:+.3f}".format(
            nev, tabla.loc[nev, "Δ_pearson"], tabla.loc[nev, "Δ_spearman"]))
    print()
    print("A Spearman. Az eltávolítás mindkettőt csökkenti, de a Spearmant kevésbé: a rangsor")
    print("szerint a két hallgató „csak” az első két helyen áll, a Pearson viszont a nyers")
    print("távolságokat is figyelembe veszi, így a trendtől messze kinyúló pontok nagyobb súllyal")
    print("hatnak rá. A korlátozás a rangsort nem változtatja meg (a két legnagyobb érték")
    print("legnagyobb marad, csak holtversenybe kerül), ezért a Spearman gyakorlatilag változatlan.")
    print("A Pearson is csak kicsit csökken, mert a két pont a határra húzva is a trend")
    print("irányában marad (sok tanulás – magas pontszám).")

    cim("Okozott-e a mediánnal történő pótlás mesterséges változást a kapcsolatban?")
    potolt = tabla.loc["2. study_hours mediánnal pótolva"]
    pot_y = df.loc[df[X].isna(), Y]
    print("A korreláció alig változott (Pearson {:+.3f}, Spearman {:+.3f}), mert a {} pótolt".format(
        potolt["Δ_pearson"], potolt["Δ_spearman"], len(pot_y)))
    print("hallgató vizsgaeredménye ({:.1f}–{:.1f} pont, átlag {:.1f}) közel van az átlaghoz".format(
        pot_y.min(), pot_y.max(), pot_y.mean()))
    print("({:.1f}), így a mediánnál, vagyis középen elhelyezett pontok nem húzzák el a trendet.".format(
        df[Y].mean()))
    print("A pótlás mégis mesterséges: {} hallgató pontosan ugyanazt az értéket kapta (függőleges".format(
        len(pot_y)))
    szoras = [adatok[nev].dropna(subset=[X, Y])[X].std()
              for nev in ("1. hiányzók elhagyása", "2. study_hours mediánnal pótolva")]
    print("pontsor az ábrán), a study_hours szórása {:.2f}-ről {:.2f}-re csökken, és a Spearman-"
          .format(*szoras))
    print("hoz holtversenyes rangokat ad. A mediánnal pótolt rekordok gyengíteni hajlamosak a")
    print("kapcsolatot, mert az X-értéküket az Y-tól függetlenül választjuk ki; a mintabeli")
    print("hatás itt csak azért kicsi, mert e hallgatók eredménye éppen átlag körüli.")

    cim("Következtetések")
    print("1. A korreláció segíthet egy hiányzó érték pótlására alkalmas segédváltozó")
    print("   kiválasztásában (pl. a study_hours pótlásánál olyan változó jöhet szóba, amivel")
    print("   szorosan együtt mozog), de önmagában nem indokolja automatikusan a pótlást.")
    print("2. A korreláció jelentős megváltozása jelezheti, hogy egy kiugró érték nagy hatással")
    print("   van az elemzésre (itt 2 rekord eltávolítása {:+.3f}-mal változtatja a Pearsont),".format(
        tabla.loc["4. kiugrók eltávolítása", "Δ_pearson"]))
    print("   de nem bizonyítja, hogy az érték hibás: a 29–32 tanulási óra lehetséges, és a")
    print("   rekordok többi adata is konzisztens.")

    abra(df, adatok, info, tabla)
    plt.show()


if __name__ == "__main__":
    main()
