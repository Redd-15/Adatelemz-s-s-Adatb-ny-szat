# -*- coding: utf-8 -*-
"""1. Két numerikus változó kapcsolatának grafikus vizsgálata.

Bemenet: student_performance_imputed.csv

Pontdiagramot készítünk az exam_score és a többi numerikus változó között,
mindegyikre illesztett regressziós egyenessel. Megvizsgáljuk a kapcsolat
irányát, szorosságát, linearitását, és azt, hogy vannak-e a kapcsolatot
jelentősen befolyásoló megfigyelések (Cook-távolság alapján).
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

MAPPA = os.path.dirname(os.path.abspath(__file__))
BEMENET = os.path.join(MAPPA, "student_performance_imputed.csv")

CEL = "exam_score"
MAGYARAZO = ["study_hours", "attendance", "previous_gpa", "assignments_completed"]

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


def erosseg(r):
    """A korreláció abszolút értékének szöveges minősítése."""
    a = abs(r)
    if a < 0.1:
        return "elhanyagolható"
    if a < 0.3:
        return "gyenge"
    if a < 0.7:
        return "közepes"
    return "erős"


def regresszio(x, y):
    """Egyszerű lineáris regresszió: tengelymetszet, meredekség, R², Cook-távolság."""
    n = len(x)
    X = np.column_stack([np.ones(n), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    rezid = y - X @ b
    r2 = 1 - (rezid @ rezid) / ((y - y.mean()) @ (y - y.mean()))
    # tőkeáttétel (hat mátrix főátlója) és Cook-távolság
    h = np.einsum("ij,jk,ik->i", X, np.linalg.inv(X.T @ X), X)
    s2 = (rezid @ rezid) / (n - 2)
    cook = rezid ** 2 / (2 * s2) * h / (1 - h) ** 2
    return b[0], b[1], r2, np.sqrt(s2), cook


def masodfoku_r2(x, y):
    """Másodfokú illesztés R²-e: ha jóval nagyobb a lineárisnál, a kapcsolat görbült."""
    egyutt = np.polyfit(x, y, 2)
    rezid = y - np.polyval(egyutt, x)
    return 1 - (rezid @ rezid) / ((y - y.mean()) @ (y - y.mean()))


def vizsgal(df, valtozo):
    """Egy változópár kiértékelése; a kirajzoláshoz szükséges adatokkal tér vissza."""
    x = df[valtozo].to_numpy(dtype=float)
    y = df[CEL].to_numpy(dtype=float)
    n = len(x)
    a, b, r2, s, cook = regresszio(x, y)
    r = np.corrcoef(x, y)[0, 1]
    r2_masod = masodfoku_r2(x, y)
    hatar = 4 / n
    befolyasolo = np.flatnonzero(cook > hatar)
    befolyasolo = befolyasolo[np.argsort(cook[befolyasolo])[::-1]]

    print()
    print("{} – {}".format(valtozo, CEL))
    print("-" * 70)
    print("  regressziós egyenes: {} = {:.2f} {} {:.2f} · {}".format(
        CEL, a, "+" if b >= 0 else "−", abs(b), valtozo))
    print("  irány:      {} (r = {:.3f}); egységnyi növekedés átlagosan {:+.2f} pont "
          "változással jár".format("pozitív" if r > 0 else "negatív", r, b))
    print("  szorosság:  {} kapcsolat, R² = {:.3f} (a szórás {:.0f}%-át magyarázza), "
          "reziduális szórás = {:.1f} pont".format(erosseg(r), r2, 100 * r2, s))
    javulas = r2_masod - r2
    print("  linearitás: R² lineáris = {:.3f}, másodfokú = {:.3f} (javulás {:.3f}) → {}".format(
        r2, r2_masod, javulas,
        "a görbült illesztés alig javít, a kapcsolat lineárisnak tűnik"
        if javulas < 0.02 else "érdemi görbület látszik, a kapcsolat nem teljesen lineáris"))
    print("  befolyásoló megfigyelések (Cook-távolság > 4/n = {:.3f}): {} db".format(
        hatar, len(befolyasolo)))
    for i in befolyasolo:
        print("      {}  {} = {:>6.2f}, {} = {:>5.1f}, D = {:.3f}".format(
            df["student_id"].iat[i], valtozo, x[i], CEL, y[i], cook[i]))

    # Mennyit változik az eredmény a legnagyobb hatású pont elhagyásával?
    if len(befolyasolo):
        maradek = np.delete(np.arange(n), befolyasolo[0])
        _, b2, _, _, _ = regresszio(x[maradek], y[maradek])
        r_nelkul = np.corrcoef(x[maradek], y[maradek])[0, 1]
        print("  {} nélkül: meredekség {:+.2f} → {:+.2f}, r {:.3f} → {:.3f}".format(
            df["student_id"].iat[befolyasolo[0]], b, b2, r, r_nelkul))
    print("  (Cook-távolság > 1 esetén lenne egy pont önmagában meghatározó; "
          "itt a legnagyobb D = {:.3f})".format(cook.max()))

    return {"x": x, "y": y, "a": a, "b": b, "r": r, "r2": r2,
            "befolyasolo": befolyasolo}


def abra(df, eredmenyek):
    fig, tengelyek = plt.subplots(2, 2, figsize=(12, 9))
    for ax, valtozo in zip(tengelyek.flat, MAGYARAZO):
        e = eredmenyek[valtozo]
        ax.scatter(e["x"], e["y"], s=28, color=SZIN, alpha=0.6, edgecolor="white",
                   linewidth=0.5, label="hallgató")
        vonal_x = np.linspace(e["x"].min(), e["x"].max(), 100)
        ax.plot(vonal_x, e["a"] + e["b"] * vonal_x, color=SZIN2, linewidth=2,
                label="regressziós egyenes")
        # a befolyásoló pontok kiemelése azonosítóval
        bef = e["befolyasolo"]
        if len(bef):
            ax.scatter(e["x"][bef], e["y"][bef], s=60, facecolor="none",
                       edgecolor=SZOVEG_SZIN, linewidth=1.2,
                       label="befolyásoló (Cook D > 4/n)")
            for i in bef:
                ax.annotate(df["student_id"].iat[i], (e["x"][i], e["y"][i]),
                            xytext=(4, 4), textcoords="offset points", fontsize=7,
                            color=SZOVEG_SZIN)
        ax_formaz(ax, "{} és {}\nr = {:.3f},  R² = {:.3f},  y = {:.1f} {} {:.2f}x".format(
                      valtozo, CEL, e["r"], e["r2"], e["a"],
                      "+" if e["b"] >= 0 else "−", abs(e["b"])),
                  valtozo, CEL)
    kezelok, feliratok = tengelyek.flat[0].get_legend_handles_labels()
    fig.legend(kezelok, feliratok, loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("Pontdiagramok regressziós egyenessel", fontsize=13)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(MAPPA, "01_pontdiagramok.png"), dpi=120)


def main():
    df = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*df.shape))

    cim("Változópárok vizsgálata")
    eredmenyek = {valtozo: vizsgal(df, valtozo) for valtozo in MAGYARAZO}

    cim("Összegzés")
    sorrend = sorted(MAGYARAZO, key=lambda v: abs(eredmenyek[v]["r"]), reverse=True)
    for valtozo in sorrend:
        e = eredmenyek[valtozo]
        print("  {:<22} r = {:>6.3f}  ({} {})".format(
            valtozo, e["r"], erosseg(e["r"]), "pozitív" if e["r"] > 0 else "negatív"))
    print()
    print("- Mind a négy kapcsolat pozitív: a nagyobb értékhez átlagosan jobb vizsgaeredmény")
    print("  tartozik, de egyik sem szoros, a pontok szélesen szóródnak az egyenes körül.")
    print("- A másodfokú illesztés egyik esetben sem javít érdemben, a lineáris trend elfogadható.")
    print("- Vannak az átlagosnál nagyobb hatású pontok, de egyik sem fordítja meg vagy")
    print("  változtatja meg drasztikusan a trendet (minden Cook-távolság jóval 1 alatt van).")
    print("- Az assignments_completed diszkrét (3–10), ezért a pontok függőleges oszlopokba")
    print("  rendeződnek; ennél a változónál a legkisebb a magyarázott szórás.")
    print("- Az S055 hallgató (GPA 4.48, 1 tanulási óra, 22.8 pont) mind a négy párban")
    print("  kiemelkedő hatású; egy ilyen rekordot érdemes külön ellenőrizni.")

    abra(df, eredmenyek)
    plt.show()


if __name__ == "__main__":
    main()
