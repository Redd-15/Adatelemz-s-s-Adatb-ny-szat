# -*- coding: utf-8 -*-
"""A 6. óra PCA-feladatainak közös segédfüggvényei.

Beolvasás, a jellemzők standardizálása, a redundáns sleep_hours oszlop
előállítása (4–5. feladat), valamint a kimenet és az ábrák formázása.
"""

import os

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_imputed.csv")

# Az exam_score szándékosan kimarad: a passed közvetlenül abból készült.
JELLEMZOK = ["study_hours", "attendance", "previous_gpa", "assignments_completed"]
JELLEMZOK_ALVASSAL = JELLEMZOK + ["sleep_hours"]

SZIN = "#2a78d6"
SZIN2 = "#eb6834"
SZIN3 = "#1f9e6e"
SZOVEG_SZIN = "#0b0b0b"
RACS_SZIN = "#e5e4df"
PASSED_SZINEK = {"yes": SZIN, "no": SZIN2}
PROGRAM_SZINEK = {"Business Informatics": SZIN, "Computer Science": SZIN2,
                  "Mechanical Engineering": SZIN3}


def cim(szoveg):
    """Szakaszcím a kimenetben."""
    print()
    print("=" * 70)
    print(szoveg)
    print("=" * 70)


def beolvas():
    return pd.read_csv(BEMENET, sep=";", encoding="utf-8")


def standardizal(df, oszlopok):
    """z-értékek (átlag 0, szórás 1) DataFrame-ként, az eredeti oszlopnevekkel."""
    z = StandardScaler().fit_transform(df[oszlopok])
    return pd.DataFrame(z, columns=oszlopok, index=df.index)


def alvas_hozzaad(df, seed=42):
    """sleep_hours: erősen negatívan korrelál a study_hours-szal (a tanulás az alvás rovására megy).

    sleep_hours = 9 − 0,25 · study_hours + N(0; 0,4) zaj, 4 és 10 óra közé korlátozva.
    """
    rng = np.random.default_rng(seed)
    uj = df.copy()
    alvas = 9 - 0.25 * uj["study_hours"] + rng.normal(0, 0.4, len(uj))
    uj["sleep_hours"] = alvas.clip(4, 10).round(1)
    return uj


def pca_2d(df, oszlopok):
    """Standardizálás + két komponensű PCA; a modell és a pontszámok DataFrame-je."""
    z = standardizal(df, oszlopok)
    pca = PCA(n_components=2)
    pontszam = pca.fit_transform(z)
    eredmeny = pd.DataFrame(pontszam, columns=["PC1", "PC2"], index=df.index)
    eredmeny[["student_id", "programme", "passed"]] = df[["student_id", "programme", "passed"]]
    return pca, eredmeny


def sulyok(pca, oszlopok):
    """Komponenssúlyok (pca.components_) táblázata: sorok = változók, oszlopok = PC-k."""
    return pd.DataFrame(pca.components_.T, index=oszlopok,
                        columns=["PC{}".format(i + 1) for i in range(pca.n_components_)])


def ax_formaz(ax, cim_szoveg, xlabel, ylabel, racs="both"):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim_szoveg, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis=racs, color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def heatmap(ax, korr):
    """Annotált korrelációs hőtérkép matplotlibbel (seaborn nélkül)."""
    n = len(korr)
    kep = ax.imshow(korr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    for i in range(n):
        for j in range(n):
            ertek = korr.iat[i, j]
            ax.text(j, i, "{:.2f}".format(ertek), ha="center", va="center", fontsize=10,
                    color="white" if abs(ertek) > 0.6 else SZOVEG_SZIN)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(korr.columns, rotation=30, ha="right")
    ax.set_yticklabels(korr.index)
    ax.set_xticks(np.arange(-0.5, n), minor=True)
    ax.set_yticks(np.arange(-0.5, n), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="both", length=0)
    for oldal in ax.spines.values():
        oldal.set_visible(False)
    return kep


def pontdiagram(ax, eredmeny, szinezes, cim_szoveg, arany):
    """A hallgatók az első két főkomponens síkjában, a szinezes oszlop szerint színezve."""
    szinek = PASSED_SZINEK if szinezes == "passed" else PROGRAM_SZINEK
    for csoport, szin in szinek.items():
        resz = eredmeny[eredmeny[szinezes] == csoport]
        ax.scatter(resz["PC1"], resz["PC2"], s=30, color=szin, alpha=0.7, edgecolor="white",
                   linewidth=0.5, label="{} (n = {})".format(csoport, len(resz)))
        # csoportközéppont
        ax.scatter(resz["PC1"].mean(), resz["PC2"].mean(), s=160, marker="X", color=szin,
                   edgecolor=SZOVEG_SZIN, linewidth=1, zorder=3)
    ax.axhline(0, color=RACS_SZIN, linewidth=1)
    ax.axvline(0, color=RACS_SZIN, linewidth=1)
    ax.legend(frameon=False, fontsize=8, title=szinezes, title_fontsize=8)
    ax_formaz(ax, cim_szoveg, "PC1 ({:.1%})".format(arany[0]), "PC2 ({:.1%})".format(arany[1]))


def elkulonules(eredmeny, oszlopok=("PC1", "PC2")):
    """A passed csoportok középpontjainak távolsága a közös szórás egységében (Mahalanobis).

    Leíró mérőszám: minél nagyobb, annál kevésbé fedik át egymást a csoportok.
    """
    oszlopok = list(oszlopok)
    yes = eredmeny.loc[eredmeny["passed"] == "yes", oszlopok]
    no = eredmeny.loc[eredmeny["passed"] == "no", oszlopok]
    kul = (yes.mean() - no.mean()).to_numpy()
    kozos = ((len(yes) - 1) * yes.cov() + (len(no) - 1) * no.cov()) / (len(yes) + len(no) - 2)
    return float(np.sqrt(kul @ np.linalg.solve(kozos.to_numpy(), kul)))
