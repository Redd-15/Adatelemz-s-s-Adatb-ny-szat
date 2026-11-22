# -*- coding: utf-8 -*-
"""3. Hipotézisvizsgálat.

Bemenet: 01_hajtaslanc_tisztitott.csv
Kimenet: 03_futamok.csv – futamonkénti jellemzők (a két próba bemenete)
         03_h1_inverter.png, 03_h2_belso_ellenallas.png

Megfigyelési egység: a gyorsító futam (hajtaslanc_kozos.futam_azonosito). A 10 Hz-es sorok
erősen autokorreláltak (az akkuteljesítményé 1 s eltolásnál 0,73, az inverterhőmérsékleté
3 s-nál is 0,83), ezért soronként nem tesztelünk: a p-értékek irreálisan kicsik lennének.

H1: Egy gyorsító futam alatt az inverter hőmérséklete nő.
    d = T_vég − T_kezdet; H0: μ_d = 0, H1: μ_d > 0 (egyoldali).
    Próba: páros t-próba; feltétel a különbségek normalitása (Shapiro–Wilk).
    Robusztussági ellenőrzés: Wilcoxon-féle előjeles rangpróba.
    Kiegészítés: a melegedés és a nyomatékkérés-integrál kapcsolata (Spearman).
H2: A belső ellenállás eltér magas (≥ 90%) és alacsonyabb (< 90%) töltöttségnél.
    H0: μ_magas = μ_alacsony, H1: μ_magas ≠ μ_alacsony (kétoldali).
    Próba: Welch-féle kétmintás t-próba (nem tételez fel egyenlő szórást); feltétel a
    csoportonkénti normalitás (Shapiro–Wilk). Robusztussági ellenőrzés: Mann–Whitney U.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

import os as _os
import sys as _sys
# a közös modul (hajtaslanc_kozos.py) a szülőmappában, a Beadando mappában van
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from hajtaslanc_kozos import (MAPPA, SZIN, SZIN2, SZOVEG_SZIN, MASODLAGOS_SZOVEG, ALFA, DT_S,
                              beolvas, cim, ax_formaz, abra_mentes, ezres, futam_azonosito)

FUTAMOK_CSV = os.path.join(MAPPA, "03_futamok.csv")

VEG_MINTA = 3                   # a futam eleji / végi hőmérséklet: az első / utolsó 0,3 s átlaga
R_MIN_ARAMTARTOMANY_A = 30      # ennél kisebb áramtartományból a meredekség nem becsülhető jól
SOC_HATAR_PCT = 90              # magas / alacsonyabb töltöttség határa (a munkamenetek között
                                # természetes rés van: 92–95% vs. 73–84%)


# ---------------------------------------------------------------------------
# Futamok
# ---------------------------------------------------------------------------

def futam_tabla(df):
    df = df.copy()
    df["futam"] = futam_azonosito(df)
    sorok = []
    for futam, g in df.dropna(subset=["futam"]).groupby("futam"):
        T = g["inverter_temp_C"]
        aram = g["batt_current_A"]
        sor = {
            "futam": int(futam), "munkamenet": g["session"].iloc[0],
            "kezdet_s": g["t_s"].iloc[0], "veg_s": g["t_s"].iloc[-1],
            "hossz_s": round(len(g) * DT_S, 1),
            "atl_keres_pct": g["torque_request_pct"].mean(),
            # teljes-kérés-másodperc: 1 = 1 s 100%-os (vagy 2 s 50%-os) nyomatékkérés
            "keres_integral_s": (g["torque_request_pct"] / 100 * DT_S).sum(),
            "energia_kJ": (g["batt_power_kW"] * DT_S).sum(),
            "max_aram_A": aram.max(), "aram_tartomany_A": aram.max() - aram.min(),
            "inv_T_kezdet_C": T.iloc[:VEG_MINTA].mean(), "inv_T_veg_C": T.iloc[-VEG_MINTA:].mean(),
            "soc_atl_pct": g["soc_pct"].mean(), "cell_t_atl_C": g["cell_t_avg_C"].mean(),
        }
        sor["inv_dT_C"] = sor["inv_T_veg_C"] - sor["inv_T_kezdet_C"]
        if sor["aram_tartomany_A"] >= R_MIN_ARAMTARTOMANY_A:
            reg = stats.linregress(aram, g["batt_voltage_V"])
            sor["R_mOhm"], sor["R_illeszkedes_r"] = -reg.slope * 1000, reg.rvalue
        else:
            sor["R_mOhm"], sor["R_illeszkedes_r"] = np.nan, np.nan
        sorok.append(sor)
    return pd.DataFrame(sorok)


def futamok_leirasa(futamok):
    cim("Gyorsító futamok (megfigyelési egységek)")
    print("Futam: összefüggő szakasz, ahol a nyomatékkérés > 5%, legalább 2 s hosszú, és a")
    print("hajtáslánc legalább 5 kJ energiát ad le. Az energiafeltétel kizárja az inverterhiba")
    print("utáni szakaszokat (van kérés, de az inverter ki van kapcsolva).")
    print()
    oszlopok = ["futam", "munkamenet", "kezdet_s", "hossz_s", "atl_keres_pct", "keres_integral_s",
                "energia_kJ", "inv_T_kezdet_C", "inv_T_veg_C", "inv_dT_C", "soc_atl_pct", "R_mOhm"]
    print(futamok[oszlopok].round(2).to_string(index=False))
    print()
    print("Futamok száma: {} (munkamenetenként: {})".format(
        len(futamok), futamok["munkamenet"].value_counts(sort=False).to_dict()))


# ---------------------------------------------------------------------------
# H1: inverter-melegedés
# ---------------------------------------------------------------------------

def h1_inverter(futamok):
    cim("H1: melegszik-e az inverter egy gyorsító futam alatt?")
    kezdet, veg = futamok["inv_T_kezdet_C"], futamok["inv_T_veg_C"]
    d = veg - kezdet
    n = len(d)
    print("H0: μ_d = 0 (nincs melegedés)   H1: μ_d > 0   (d = T_vég − T_kezdet, α = {})".format(ALFA))
    print("n = {} futam; d átlaga {:.2f} °C, mediánja {:.2f} °C, szórása {:.2f} °C".format(
        n, d.mean(), d.median(), d.std()))

    sw = stats.shapiro(d)
    print()
    print("1) Feltétel: a különbségek normalitása, Shapiro–Wilk W = {:.3f}, p = {:.3f}".format(
        sw.statistic, sw.pvalue))
    print("   -> {}".format("nem vetjük el a normalitást, a páros t-próba alkalmazható"
                          if sw.pvalue > ALFA else
                          "a normalitás sérül; a Wilcoxon-próba eredménye a mérvadó"))

    t = stats.ttest_rel(veg, kezdet, alternative="greater")
    t_ketoldali = stats.ttest_rel(veg, kezdet)
    se = d.std() / np.sqrt(n)
    also_korlat = d.mean() - stats.t.ppf(1 - ALFA, n - 1) * se
    ki = d.mean() + np.array([-1, 1]) * stats.t.ppf(1 - ALFA / 2, n - 1) * se
    print()
    print("2) Páros t-próba: t({}) = {:.2f}, egyoldali p = {:.1e} (kétoldali p = {:.1e})".format(
        n - 1, t.statistic, t.pvalue, t_ketoldali.pvalue))
    print("   átlagos melegedés: {:.2f} °C, 95%-os CI: [{:.2f}; {:.2f}] °C, egyoldali alsó korlát {:.2f} °C"
          .format(d.mean(), ki[0], ki[1], also_korlat))
    print("   hatásméret (Cohen d_z = átlag / szórás): {:.2f}".format(d.mean() / d.std()))

    w = stats.wilcoxon(veg, kezdet, alternative="greater")
    print()
    print("3) Robusztussági ellenőrzés, Wilcoxon-féle előjeles rangpróba: W = {:.0f}, p = {:.1e}"
          .format(w.statistic, w.pvalue))

    rho_keres = stats.spearmanr(futamok["keres_integral_s"], d)
    rho_energia = stats.spearmanr(futamok["energia_kJ"], d)
    rho_kezdet = stats.spearmanr(futamok["inv_T_kezdet_C"], d)
    print()
    print("4) Kiegészítés, mitől függ a melegedés (Spearman):")
    for nev, rho in (("nyomatékkérés-integrál", rho_keres), ("leadott energia", rho_energia),
                     ("kezdő hőmérséklet", rho_kezdet)):
        print("   {:24s} ρ = {:+.2f}, p = {:.3f} ({})".format(
            nev + ":", rho.statistic, rho.pvalue,
            "szignifikáns" if rho.pvalue < ALFA else "nem szignifikáns"))

    print()
    print("Döntés: p = {:.1e} < α = {} -> H0-t elvetjük. Egy gyorsító futam alatt az".format(
        t.pvalue, ALFA))
    print("inverter hőmérséklete szignifikánsan nő, átlagosan {:.1f} °C-kal (95%-os CI {:.1f}–{:.1f} °C)."
          .format(d.mean(), ki[0], ki[1]))
    def jelzo(rho):
        return "szignifikáns" if rho.pvalue < ALFA else "nem szignifikáns"
    print("A melegedés nő a nyomatékkérés-integrállal (ρ = {:.2f}, {}) és a leadott energiával".format(
        rho_keres.statistic, jelzo(rho_keres)))
    print("(ρ = {:.2f}, {}), és csökken a kezdő hőmérséklettel (ρ = {:.2f}, {}): melegebb".format(
        rho_energia.statistic, jelzo(rho_energia), rho_kezdet.statistic, jelzo(rho_kezdet)))
    print("inverterről indulva nagyobb a hűlés, így kisebb a nettó melegedés. A futamszintű")
    print("korrelációk csak közepesek, mert a melegedést a terhelés és a kezdő hőmérséklet együtt")
    print("határozza meg. Ezt a dinamikát a 04-es hőmodell írja le és jósolja.")
    return {"d": d, "rho_keres": rho_keres}


def abra_h1(futamok, eredmeny):
    d = eredmeny["d"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.4), gridspec_kw={"width_ratios": [1, 1.4]})
    for _, sor in futamok.iterrows():
        ax1.plot([0, 1], [sor["inv_T_kezdet_C"], sor["inv_T_veg_C"]], color=SZIN, alpha=0.45,
                 linewidth=1.4, marker="o", markersize=5)
    ax1.plot([0, 1], [futamok["inv_T_kezdet_C"].mean(), futamok["inv_T_veg_C"].mean()],
             color=SZIN2, linewidth=3, marker="o", markersize=9, label="átlag")
    ax1.set_xticks([0, 1])
    ax1.set_xticklabels(["futam eleje", "futam vége"])
    ax1.set_xlim(-0.3, 1.3)
    ax1.legend(frameon=False, loc="lower right")
    ax_formaz(ax1, "Inverterhőmérséklet futamonként (n = {})\nátlagos melegedés: +{} °C".format(
        len(futamok), ezres(d.mean(), 1)), "", "inverterhőmérséklet [°C]", racs="y")

    pontok = ax2.scatter(futamok["keres_integral_s"], d, s=70, c=futamok["inv_T_kezdet_C"],
                         cmap="Oranges", vmin=30, vmax=85, edgecolor=MASODLAGOS_SZOVEG, linewidth=0.6)
    fig.colorbar(pontok, ax=ax2, label="inverterhőmérséklet a futam elején [°C]")
    ax2.axhline(0, color=MASODLAGOS_SZOVEG, linewidth=0.8)
    ax_formaz(ax2, "Melegedés a kért nyomaték függvényében (Spearman ρ = {}, p = {})\n"
              "azonos kérésnél a hidegebbről (világos) induló inverter jobban melegszik".format(
                  ezres(eredmeny["rho_keres"].statistic, 2), ezres(eredmeny["rho_keres"].pvalue, 2)),
              "nyomatékkérés-integrál [teljes-kérés-másodperc]", "melegedés a futam alatt [°C]")
    fig.suptitle("H1: az inverter melegszik egy gyorsító futam alatt", x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    abra_mentes(fig, "03_h1_inverter.png")


# ---------------------------------------------------------------------------
# H2: belső ellenállás és töltöttség
# ---------------------------------------------------------------------------

def welch_konfidencia(a, b):
    """A két átlag különbségének 95%-os konfidencia-intervalluma Welch-féle szabadságfokkal."""
    va, vb = a.var() / len(a), b.var() / len(b)
    se = np.sqrt(va + vb)
    df_welch = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    kul = a.mean() - b.mean()
    return kul, kul + np.array([-1, 1]) * stats.t.ppf(1 - ALFA / 2, df_welch) * se, df_welch


def hedges_g(a, b):
    sp = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / (len(a) + len(b) - 2))
    return (a.mean() - b.mean()) / sp * (1 - 3 / (4 * (len(a) + len(b)) - 9))


def h2_belso_ellenallas(futamok):
    cim("H2: eltér-e a belső ellenállás magas és alacsonyabb töltöttségnél?")
    r = futamok.dropna(subset=["R_mOhm"]).copy()
    r["csoport"] = np.where(r["soc_atl_pct"] >= SOC_HATAR_PCT, "magas SOC", "alacsonyabb SOC")
    magas = r.loc[r["csoport"] == "magas SOC", "R_mOhm"]
    alacsony = r.loc[r["csoport"] == "alacsonyabb SOC", "R_mOhm"]
    print("Belső ellenállás futamonként: az akkufeszültség és az áram lineáris regressziójának")
    print("meredeksége (U = U0 − R · I), csak a legalább {} A áramtartományt bejáró futamokból.".format(
        R_MIN_ARAMTARTOMANY_A))
    print("Felhasznált futamok: {} / {}; az illesztések r értéke {:.2f}…{:.2f}.".format(
        len(r), len(futamok), r["R_illeszkedes_r"].min(), r["R_illeszkedes_r"].max()))
    print()
    print("H0: μ_magas = μ_alacsony   H1: μ_magas ≠ μ_alacsony   (α = {})".format(ALFA))
    print(r.groupby("csoport", sort=False).agg(
        n=("R_mOhm", "size"), atlag_mOhm=("R_mOhm", "mean"), szoras_mOhm=("R_mOhm", "std"),
        median_mOhm=("R_mOhm", "median"), soc_tartomany=("soc_atl_pct", lambda s: "{:.0f}–{:.0f}%".format(s.min(), s.max())),
        cellahom_atlag_C=("cell_t_atl_C", "mean")).round(1).to_string())

    print()
    print("1) Feltételek:")
    for nev, minta in (("magas SOC", magas), ("alacsonyabb SOC", alacsony)):
        sw = stats.shapiro(minta)
        print("   normalitás ({}): Shapiro–Wilk W = {:.3f}, p = {:.3f}".format(nev, sw.statistic, sw.pvalue))
    lev = stats.levene(magas, alacsony)
    print("   szóráshomogenitás: Levene W = {:.2f}, p = {:.3f}; a Welch-próba ezt nem igényli".format(
        lev.statistic, lev.pvalue))

    t = stats.ttest_ind(magas, alacsony, equal_var=False)
    kul, ki, df_welch = welch_konfidencia(magas, alacsony)
    print()
    print("2) Welch-féle t-próba: t({:.1f}) = {:.2f}, p = {:.3f}".format(df_welch, t.statistic, t.pvalue))
    print("   különbség (magas − alacsonyabb): {:.1f} mΩ, 95%-os CI: [{:.1f}; {:.1f}] mΩ".format(
        kul, ki[0], ki[1]))
    print("   hatásméret (Hedges g): {:.2f}".format(hedges_g(magas, alacsony)))
    mw = stats.mannwhitneyu(magas, alacsony)
    print()
    print("3) Robusztussági ellenőrzés, Mann–Whitney U = {:.0f}, p = {:.3f}".format(mw.statistic, mw.pvalue))
    rho_soc = stats.spearmanr(r["soc_atl_pct"], r["R_mOhm"])
    rho_hom = stats.spearmanr(r["cell_t_atl_C"], r["R_mOhm"])
    rho_soc_hom = stats.spearmanr(r["soc_atl_pct"], r["cell_t_atl_C"])
    print()
    print("4) Kiegészítés (Spearman): R–SOC ρ = {:.2f} (p = {:.2f}), R–cellahőmérséklet ρ = {:.2f} (p = {:.2f});"
          .format(rho_soc.statistic, rho_soc.pvalue, rho_hom.statistic, rho_hom.pvalue))
    print("   a SOC és a cellahőmérséklet maga is szorosan összefügg (ρ = {:.2f}).".format(
        rho_soc_hom.statistic))

    print()
    if t.pvalue < ALFA:
        print("Döntés: p = {:.3f} < α = {} -> H0-t elvetjük: a belső ellenállás a két csoportban eltér."
              .format(t.pvalue, ALFA))
    else:
        print("Döntés: p = {:.2f} > α = {} -> H0-t nem vetjük el. A belső ellenállás átlaga a két".format(
            t.pvalue, ALFA))
        print("töltöttségi csoportban nem tér el szignifikánsan (közös átlag ~{:.0f} mΩ).".format(
            r["R_mOhm"].mean()))
        print("Ez nem bizonyítja, hogy nincs különbség: a minta kicsi (n = {} + {}), és a különbség".format(
            len(magas), len(alacsony)))
        print("95%-os CI-je széles ({:.0f}…{:.0f} mΩ), tehát ekkora eltérést nem tudunk kizárni.".format(
            ki[0], ki[1]))
    print()
    print("A SOC és a cellahőmérséklet futamszinten együtt változott (ρ = {:.2f}): a későbbi,".format(
        rho_soc_hom.statistic))
    print("alacsonyabb SOC-ú futamokban a cellák ~{:.1f} °C-kal melegebbek. Az alacsonyabb SOC".format(
        r.loc[r["csoport"] == "alacsonyabb SOC", "cell_t_atl_C"].mean()
        - r.loc[r["csoport"] == "magas SOC", "cell_t_atl_C"].mean()))
    print("általában NÖVELI, a melegebb cella CSÖKKENTI a belső ellenállást, így ebből az adatból")
    print("a két hatás nem választható szét.")
    if rho_soc.pvalue < ALFA:
        irany = "csökken" if rho_soc.statistic > 0 else "nő"
        print("A kiegészítő, folytonos összefüggés (Spearman) viszont szignifikáns: R–SOC ρ = {:.2f}".format(
            rho_soc.statistic))
        print("(p = {:.3f}), vagyis a nap előrehaladtával (alacsonyabb SOC, melegebb cellák) a belső".format(
            rho_soc.pvalue))
        print("ellenállás {}. {}".format(irany,
              "Ez az iránya a hőmérséklet hatásával egyezik (a SOC-é ellentétes lenne)."
              if rho_soc.statistic > 0 else "Ez az iránya a SOC hatásával egyezik."))
        print("Óvatosan kezelendő: kiegészítő elemzés, kis minta, és a két csoport átlaga nem tér el")
        print("szignifikánsan.")
    else:
        print("A kiegészítő, folytonos összefüggés (Spearman) sem szignifikáns (R–SOC ρ = {:.2f},".format(
            rho_soc.statistic))
        print("p = {:.2f}): a két hatás részben kiolthatja egymást.".format(rho_soc.pvalue))
    return r


def abra_h2(r):
    csoportok = ["magas SOC", "alacsonyabb SOC"]
    szinek = {"magas SOC": SZIN, "alacsonyabb SOC": SZIN2}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))
    rng = np.random.default_rng(42)
    for i, cs in enumerate(csoportok):
        ertek = r.loc[r["csoport"] == cs, "R_mOhm"]
        ax1.boxplot(ertek, positions=[i], widths=0.45, showfliers=False,
                    medianprops={"color": SZOVEG_SZIN, "linewidth": 1.6},
                    boxprops={"color": MASODLAGOS_SZOVEG}, whiskerprops={"color": MASODLAGOS_SZOVEG},
                    capprops={"color": MASODLAGOS_SZOVEG})
        ax1.scatter(i + rng.uniform(-0.12, 0.12, len(ertek)), ertek, s=50, color=szinek[cs],
                    alpha=0.85, edgecolor="white", zorder=3)
        se = ertek.std() / np.sqrt(len(ertek))
        hiba = stats.t.ppf(1 - ALFA / 2, len(ertek) - 1) * se
        ax1.errorbar(i + 0.32, ertek.mean(), yerr=hiba, fmt="D", color=SZOVEG_SZIN, capsize=5,
                     markersize=6)
    ax1.set_xticks(range(len(csoportok)))
    ax1.set_xticklabels(["{}\n(n = {})".format(cs, (r["csoport"] == cs).sum()) for cs in csoportok])
    ax_formaz(ax1, "Belső ellenállás futamonként\n(◆ átlag 95%-os CI-vel)", "", "belső ellenállás [mΩ]",
              racs="y")

    for cs in csoportok:
        resz = r[r["csoport"] == cs]
        ax2.scatter(resz["cell_t_atl_C"], resz["R_mOhm"], s=55, color=szinek[cs], alpha=0.85,
                    edgecolor="white", label=cs)
    ax2.legend(frameon=False, loc="lower left")
    ax_formaz(ax2, "A töltöttség és a cellahőmérséklet együtt változik\n(a két hatás nem választható szét)",
              "átlagos cellahőmérséklet a futam alatt [°C]", "belső ellenállás [mΩ]")
    fig.suptitle("H2: belső ellenállás magas és alacsonyabb töltöttségnél", x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    abra_mentes(fig, "03_h2_belso_ellenallas.png")


# ---------------------------------------------------------------------------
# Főprogram
# ---------------------------------------------------------------------------

def main():
    pd.set_option("display.width", 170)
    teljes = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*teljes.shape))
    df = teljes[~teljes["inverter_hiba"]].copy()
    print("Az inverterhiba miatt jelölt {} sor kizárva, marad {} sor.".format(
        teljes["inverter_hiba"].sum(), len(df)))

    futamok = futam_tabla(df)
    futamok_leirasa(futamok)
    futamok.round(3).to_csv(FUTAMOK_CSV, sep=";", index=False, encoding="utf-8")

    eredmeny_h1 = h1_inverter(futamok)
    abra_h1(futamok, eredmeny_h1)
    r = h2_belso_ellenallas(futamok)
    abra_h2(r)

    print()
    print("Futamtábla mentve: {}".format(FUTAMOK_CSV))
    plt.show()


if __name__ == "__main__":
    main()
