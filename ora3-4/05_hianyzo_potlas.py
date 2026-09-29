# -*- coding: utf-8 -*-
"""5. Hiányzó értékek pótlása.

Bemenet: student_performance_cleaned-NEW.csv
Kimenet: 05_student_performance_potolt.csv (a pótolt adathalmaz)

A pótlás lépései (egyeztetve), mindegyik az előző lépés másolatán dolgozik:
  1. study_hours: a hallgató passed csoportjának átlaga
     (passed == Yes -> a sikeresek átlaga, passed == No -> a sikertelenek átlaga);
  2. previous_gpa: ahol hiányzik, a rekordot töröljük;
  3. programme: pótlás a módusszal;
  4. ami még hiányzik: pótlás a képzési programonként számított mediánnal.
     A passed kategorikus, ezért nem mediánnal pótoljuk, hanem a pótolt
     exam_score-ból számítjuk (ponthatár: 50, mint a 3. feladatban).

Minden lépés után összevetjük a változatot az eredetivel: elemszám, átlag,
medián, szórás, az eloszlás alakja (ferdeség, csúcsosság, hisztogram), és a
változók közötti korrelációk.
"""

import os

import pandas as pd
import matplotlib.pyplot as plt

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_cleaned-NEW.csv")
KIMENET = os.path.join(MAPPA, "05_student_performance_potolt.csv")

NUMERIKUS = ["study_hours", "attendance", "previous_gpa",
             "assignments_completed", "exam_score"]
EGESZ = ["assignments_completed"]
PONTHATAR = 50

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


def potlasok_kiirasa(elotte, utana, oszlop):
    """A pótolt cellák listázása: azonosító és a beírt érték."""
    potolt = elotte[oszlop].isna() & utana[oszlop].notna()
    for index in utana.index[potolt]:
        print("  PÓTOLVA  {} {} -> {}".format(
            utana.at[index, "student_id"], oszlop, utana.at[index, oszlop]))
    return int(potolt.sum())


def lepes1_study_hours(df):
    """study_hours pótlása a passed csoport (Yes / No) átlagával."""
    v = df.copy()
    atlagok = v.groupby("passed")["study_hours"].mean()
    print("A study_hours átlaga passed csoportonként (a meglévő értékekből):")
    for csoport, atlag in atlagok.items():
        print("  passed = {:<4} átlag = {:.2f}".format(csoport, atlag))
    csoport_atlag = v.groupby("passed")["study_hours"].transform("mean")
    # a tanulási idő egy tizedesre van megadva, a pótolt érték is ilyen legyen
    v["study_hours"] = v["study_hours"].fillna(csoport_atlag.round(1))
    db = potlasok_kiirasa(df, v, "study_hours")
    print("Pótolt study_hours: {} db, továbbra is hiányzik: {} db".format(
        db, int(v["study_hours"].isna().sum())))
    return v


def lepes2_gpa_torles(df):
    """Ahol a previous_gpa hiányzik, a rekordot töröljük."""
    torlendo = df["previous_gpa"].isna()
    print("Törölt rekordok (hiányzó previous_gpa): {}".format(
        ", ".join(df.loc[torlendo, "student_id"])))
    v = df.loc[~torlendo].copy()
    print("Elemszám: {} -> {}".format(len(df), len(v)))
    return v


def lepes3_programme(df):
    """A hiányzó programme pótlása a módusszal."""
    v = df.copy()
    print("A programme gyakoriságai a pótlás előtt:")
    print(v["programme"].value_counts().to_string())
    modusz = v["programme"].mode().iloc[0]
    print("Módusz: {}".format(modusz))
    v["programme"] = v["programme"].fillna(modusz)
    potlasok_kiirasa(df, v, "programme")
    return v


def lepes4_program_median(df):
    """A maradék hiányzó numerikus értékek pótlása a program mediánjával."""
    v = df.copy()
    for oszlop in NUMERIKUS:
        if not v[oszlop].isna().any():
            continue
        medianok = v.groupby("programme")[oszlop].median()
        print("A(z) {} mediánja képzési programonként:".format(oszlop))
        for program, median in medianok.items():
            print("  {:<24} {:.2f}".format(program, median))
        v[oszlop] = v[oszlop].fillna(v.groupby("programme")[oszlop].transform("median"))
        potlasok_kiirasa(df, v, oszlop)

    # a passed a pótolt vizsgaeredményből következik
    hianyzo_passed = v["passed"].isna()
    v.loc[hianyzo_passed, "passed"] = (
        v.loc[hianyzo_passed, "exam_score"].ge(PONTHATAR).map({True: "Yes", False: "No"}))
    print("A passed a pótolt exam_score-ból (ponthatár: {}):".format(PONTHATAR))
    potlasok_kiirasa(df, v, "passed")
    return v


def leiro_statisztika(valtozatok):
    """Változónként: elemszám, átlag, medián, szórás, ferdeség, csúcsosság."""
    sorok = []
    for oszlop in NUMERIKUS:
        for nev, v in valtozatok.items():
            ertekek = v[oszlop].dropna().astype(float)
            sorok.append({
                "változó": oszlop,
                "változat": nev,
                "rekord": len(v),
                "n (nem hiányzó)": len(ertekek),
                "átlag": ertekek.mean(),
                "medián": ertekek.median(),
                "szórás": ertekek.std(),
                "ferdeség": ertekek.skew(),
                "csúcsosság": ertekek.kurt(),
            })
    return pd.DataFrame(sorok).set_index(["változó", "változat"]).round(3)


def ax_formaz(ax, cim_szoveg, xlabel, ylabel):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim_szoveg, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def abra(eredeti, vegso):
    """Az eredeti és a pótolt eloszlás hisztogramja a pótolt változóknál."""
    oszlopok = ["study_hours", "previous_gpa", "exam_score"]
    fig, tengelyek = plt.subplots(1, len(oszlopok), figsize=(15, 4.8))
    for ax, oszlop in zip(tengelyek, oszlopok):
        regi = eredeti[oszlop].dropna().to_numpy(dtype=float)
        uj = vegso[oszlop].dropna().to_numpy(dtype=float)
        hatarok = pd.cut(pd.Series(list(regi) + list(uj)), bins=15, retbins=True)[1]
        ax.hist(regi, bins=hatarok, color=SZIN, alpha=0.45, label="eredeti")
        ax.hist(uj, bins=hatarok, histtype="step", color=SZIN2, linewidth=2,
                label="pótolt")
        ax.text(0.98, 0.97,
                "eredeti: n = {}, átlag = {:.2f}, szórás = {:.2f}\n"
                "pótolt:  n = {}, átlag = {:.2f}, szórás = {:.2f}".format(
                    len(regi), regi.mean(), regi.std(ddof=1),
                    len(uj), uj.mean(), uj.std(ddof=1)),
                transform=ax.transAxes, ha="right", va="top", fontsize=8,
                color=SZOVEG_SZIN)
        ax.set_ylim(0, ax.get_ylim()[1] * 1.3)
        ax_formaz(ax, oszlop, oszlop, "gyakoriság")
        ax.legend(loc="upper left", frameon=False, fontsize=9)
    fig.suptitle("Eloszlás a pótlás előtt és után", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPPA, "05_potlas_eloszlasok.png"), dpi=120)


def main():
    pd.set_option("display.width", 150)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.max_rows", 100)

    eredeti = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*eredeti.shape))
    print("Hiányzó értékek a pótlás előtt:")
    print(eredeti.isna().sum().to_string())

    cim("1. lépés: study_hours pótlása a passed csoport átlagával")
    v1 = lepes1_study_hours(eredeti)

    cim("2. lépés: a hiányzó previous_gpa-t tartalmazó rekordok törlése")
    v2 = lepes2_gpa_torles(v1)

    cim("3. lépés: a programme pótlása a módusszal")
    v3 = lepes3_programme(v2)

    cim("4. lépés: a többi hiányzó érték pótlása a program mediánjával")
    v4 = lepes4_program_median(v3)

    print()
    print("Hiányzó értékek a pótlás után:")
    print(v4.isna().sum().to_string())

    valtozatok = {
        "0 eredeti": eredeti,
        "1 study_hours": v1,
        "2 gpa törlés": v2,
        "3 programme": v3,
        "4 végső": v4,
    }

    cim("Összehasonlítás: elemszám, átlag, medián, szórás, eloszlás alakja")
    print(leiro_statisztika(valtozatok).to_string())

    cim("A kategorikus változók megoszlása (eredeti -> végső)")
    for oszlop in ["programme", "passed"]:
        osszevetes = pd.DataFrame({
            "eredeti": eredeti[oszlop].value_counts(dropna=False),
            "végső": v4[oszlop].value_counts(dropna=False),
        }).fillna(0).astype(int)
        print(osszevetes.to_string())
        print()

    cim("Változók közötti kapcsolatok: korreláció (eredeti -> végső)")
    korr_eredeti = eredeti[NUMERIKUS].astype(float).corr()
    korr_vegso = v4[NUMERIKUS].astype(float).corr()
    print("Eredeti (a hiányzó értékeket páronként kihagyva):")
    print(korr_eredeti.round(3).to_string())
    print()
    print("Végső (pótolt):")
    print(korr_vegso.round(3).to_string())
    print()
    print("Változás (végső - eredeti):")
    print((korr_vegso - korr_eredeti).round(3).to_string())

    abra(eredeti, v4)

    v4.to_csv(KIMENET, sep=";", index=False, encoding="utf-8")
    cim("Mentés")
    print("{} sor, {} oszlop -> {}".format(*v4.shape, os.path.basename(KIMENET)))
    plt.show()


if __name__ == "__main__":
    main()
