# -*- coding: utf-8 -*-
"""6. Kiugró értékek felismerése és kezelése.

Bemenet: 05_student_performance_potolt.csv (az 5. feladat kimenete)

a) Boxplotok a numerikus változókról, IQR-alapú határok
   (Q1 - 1,5*IQR, Q3 + 1,5*IQR), a határokon kívül eső értékek száma és
   rekordjai. Semmit nem törlünk; a megengedett tartomány (3. feladat) és a
   rekord többi értéke alapján mérlegeljük, adathiba-e vagy valós szélsőség.
b) A study_hours kiugró értékeinek kezelése négyféleképpen, külön
   másolatokon: megtartás, rekordtörlés, korlátozás az IQR-határra,
   helyettesítés a mediánnal. Összevetés: elemszám, átlag, medián, szórás,
   minimum, maximum, eloszlás alakja, valamint a kapcsolat az exam_score-ral.
"""

import os

import pandas as pd
import matplotlib.pyplot as plt

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "05_student_performance_potolt.csv")

NUMERIKUS = ["study_hours", "attendance", "previous_gpa",
             "assignments_completed", "exam_score"]
VIZSGALT = "study_hours"

# Megengedett tartományok a 3. feladat szabályai szerint
TARTOMANY = {
    "study_hours": (0, 80),
    "attendance": (0, 100),
    "previous_gpa": (1, 5),
    "assignments_completed": (0, 10),
    "exam_score": (0, 100),
}

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


def iqr_hatarok(sorozat):
    """Q1, Q3, IQR és a kiugró értékek alsó és felső határa."""
    q1 = sorozat.quantile(0.25)
    q3 = sorozat.quantile(0.75)
    iqr = q3 - q1
    return q1, q3, iqr, q1 - 1.5 * iqr, q3 + 1.5 * iqr


def ax_formaz(ax, cim_szoveg, xlabel, ylabel, racs="y"):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim_szoveg, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis=racs, color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def boxplot_doboz(ax, adatok, szinek):
    """Egységes megjelenésű boxplot."""
    doboz = ax.boxplot(adatok, patch_artist=True, widths=0.5,
                       medianprops={"color": SZOVEG_SZIN, "linewidth": 2},
                       flierprops={"marker": "o", "markersize": 7,
                                   "markerfacecolor": SZIN2, "markeredgecolor": "white"})
    for test, szin in zip(doboz["boxes"], szinek):
        test.set(facecolor=szin, alpha=0.55, edgecolor=szin)


# ----------------------------------------------------------------------
# a) Kiugró értékek felismerése
# ----------------------------------------------------------------------
def kiugrok_feltarasa(df):
    """Változónként a határok, a kiugrók száma és a kiugró rekordok."""
    osszesito = []
    kiugro_maszk = pd.DataFrame(False, index=df.index, columns=NUMERIKUS)
    for oszlop in NUMERIKUS:
        q1, q3, iqr, also, felso = iqr_hatarok(df[oszlop])
        alatta = df[oszlop] < also
        felette = df[oszlop] > felso
        kiugro_maszk[oszlop] = alatta | felette
        osszesito.append({
            "változó": oszlop, "Q1": q1, "Q3": q3, "IQR": iqr,
            "alsó határ": also, "felső határ": felso,
            "alatta": int(alatta.sum()), "felette": int(felette.sum()),
            "kiugró összesen": int((alatta | felette).sum()),
        })
    return pd.DataFrame(osszesito).set_index("változó").round(3), kiugro_maszk


def kiugro_rekordok(df, maszk):
    """A kiugró értéket tartalmazó rekordok, értékeléssel együtt."""
    for oszlop in NUMERIKUS:
        if not maszk[oszlop].any():
            continue
        also, felso = TARTOMANY[oszlop]
        print()
        print("{} (megengedett tartomány: {}-{}):".format(oszlop, also, felso))
        for index in df.index[maszk[oszlop]]:
            ertek = df.at[index, oszlop]
            megitelés = ("tartományon belül -> lehetséges valós szélsőség"
                         if also <= ertek <= felso else "TARTOMÁNYON KÍVÜL -> adathiba")
            print("  {}  {} = {:<6}  [{}]".format(
                df.at[index, "student_id"], oszlop, ertek, megitelés))
    print()
    print("Kiugró értéket tartalmazó rekordok teljes adatai:")
    print(df.loc[maszk.any(axis=1)].to_string(index=False))


def abra_boxplotok(df, osszesito):
    """Boxplot minden numerikus változóról, saját skálán, a határokkal."""
    fig, tengelyek = plt.subplots(1, len(NUMERIKUS), figsize=(16, 5))
    for ax, oszlop in zip(tengelyek, NUMERIKUS):
        boxplot_doboz(ax, [df[oszlop].to_numpy(dtype=float)], [SZIN])
        for hatar in ("alsó határ", "felső határ"):
            ax.axhline(osszesito.at[oszlop, hatar], color=SZIN2, linewidth=1,
                       linestyle="--")
        ax.set_xticks([])
        ax_formaz(ax, "{}\nkiugró: {} db".format(
            oszlop, osszesito.at[oszlop, "kiugró összesen"]), "", oszlop)
    fig.suptitle("Numerikus változók boxplotja (szaggatott vonal: IQR-határ)",
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "06_boxplotok.png"), dpi=120)


# ----------------------------------------------------------------------
# b) A study_hours kiugró értékeinek kezelése
# ----------------------------------------------------------------------
def kezelesi_valtozatok(df, oszlop):
    """Négy másolat a négy kezelési módszerrel."""
    _, _, _, also, felso = iqr_hatarok(df[oszlop])
    kiugro = (df[oszlop] < also) | (df[oszlop] > felso)
    median = df[oszlop].median()
    print("Határok: alsó = {:.2f}, felső = {:.2f}; kiugró: {} db; medián = {:.2f}".format(
        also, felso, int(kiugro.sum()), median))

    megtartas = df.copy()

    torles = df.loc[~kiugro].copy()

    korlatozas = df.copy()
    korlatozas[oszlop] = korlatozas[oszlop].clip(lower=also, upper=felso)

    median_csere = df.copy()
    median_csere.loc[kiugro, oszlop] = median

    for index in df.index[kiugro]:
        print("  {}  {} = {} -> korlátozva: {:.2f}, mediánra cserélve: {:.2f}".format(
            df.at[index, "student_id"], oszlop, df.at[index, oszlop],
            korlatozas.at[index, oszlop], median_csere.at[index, oszlop]))

    return {
        "1 megtartás": megtartas,
        "2 rekordtörlés": torles,
        "3 korlátozás": korlatozas,
        "4 medián": median_csere,
    }


def valtozatok_osszevetese(valtozatok, oszlop):
    """Leíró statisztika és korreláció az exam_score-ral minden változatra."""
    sorok = []
    for nev, v in valtozatok.items():
        ertekek = v[oszlop].astype(float)
        sorok.append({
            "változat": nev,
            "n": len(ertekek),
            "átlag": ertekek.mean(),
            "medián": ertekek.median(),
            "szórás": ertekek.std(),
            "min": ertekek.min(),
            "max": ertekek.max(),
            "ferdeség": ertekek.skew(),
            "csúcsosság": ertekek.kurt(),
            "r(exam_score)": ertekek.corr(v["exam_score"].astype(float)),
        })
    return pd.DataFrame(sorok).set_index("változat").round(3)


def abra_modszerek(valtozatok, oszlop):
    """A négy változat boxplotja közös skálán és a hisztogramjaik."""
    fig = plt.figure(figsize=(16, 8))
    racs = fig.add_gridspec(2, len(valtozatok), height_ratios=[1.1, 1])

    ax_box = fig.add_subplot(racs[0, :])
    nevek = list(valtozatok)
    adatok = [valtozatok[nev][oszlop].to_numpy(dtype=float) for nev in nevek]
    boxplot_doboz(ax_box, adatok, [SZIN] * len(nevek))
    for x, ertekek in enumerate(adatok, start=1):
        ax_box.text(x + 0.3, ertekek.max(),
                    "n = {}\nátlag = {:.2f}\nszórás = {:.2f}".format(
                        len(ertekek), ertekek.mean(), ertekek.std(ddof=1)),
                    va="top", fontsize=8, color=SZOVEG_SZIN)
    ax_box.set_xticks(range(1, len(nevek) + 1))
    ax_box.set_xticklabels(nevek)
    ax_formaz(ax_box, "{} a négy kezelési módszer után".format(oszlop), "",
              "{} (óra)".format(oszlop))

    hatarok = pd.cut(pd.Series(adatok[0]), bins=16, retbins=True)[1]
    elso = None
    for i, (nev, ertekek) in enumerate(zip(nevek, adatok)):
        # közös függőleges skála, hogy a hisztogramok összevethetők legyenek
        ax = fig.add_subplot(racs[1, i], sharey=elso)
        elso = elso or ax
        ax.hist(ertekek, bins=hatarok, color=SZIN, alpha=0.75,
                edgecolor="white", linewidth=1)
        ax_formaz(ax, nev, "{} (óra)".format(oszlop), "gyakoriság" if i == 0 else "")
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "06_study_hours_kezeles.png"), dpi=120)


def main():
    pd.set_option("display.width", 150)
    pd.set_option("display.max_columns", 20)

    df = pd.read_csv(BEMENET, sep=";", encoding="utf-8")
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    # --------------------------------------------------------------
    # a)
    # --------------------------------------------------------------
    cim("a) IQR-alapú határok és a határokon kívül eső értékek száma")
    osszesito, maszk = kiugrok_feltarasa(df)
    print(osszesito.to_string())
    print()
    print("Legalább egy kiugró értéket tartalmazó rekord: {} db".format(
        int(maszk.any(axis=1).sum())))

    cim("a) A kiugró értékeket tartalmazó rekordok")
    kiugro_rekordok(df, maszk)
    abra_boxplotok(df, osszesito)

    # --------------------------------------------------------------
    # b)
    # --------------------------------------------------------------
    cim("b) A(z) {} kiugró értékeinek kezelése".format(VIZSGALT))
    valtozatok = kezelesi_valtozatok(df, VIZSGALT)

    cim("b) Összehasonlítás")
    print(valtozatok_osszevetese(valtozatok, VIZSGALT).to_string())
    abra_modszerek(valtozatok, VIZSGALT)

    plt.show()


if __name__ == "__main__":
    main()
