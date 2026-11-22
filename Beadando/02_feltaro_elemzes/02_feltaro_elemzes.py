# -*- coding: utf-8 -*-
"""2. Feltáró adatelemzés.

Bemenet: 01_hajtaslanc_tisztitott.csv
Kimenet: 02_leiro_statisztika.csv   – minden numerikus változó leíró statisztikái
         02_egyvaltozos.png         – 6 kulcsváltozó eloszlása (dobozábra + hisztogram)
         02_korrelacio.png          – Spearman-korrelációs hőtérkép (áttekintés)
         02_aram_feszultseg.png     – (a) feszültségesés és belső ellenállás
         02_nyomatek_fordulat.png   – (b) nyomaték–fordulatszám teljes gáznál

Az inverterhiba miatt jelölt sorokat (inverter_hiba = True) kizárjuk: ott a hajtáslánc
nem működik.
Egyváltozós elemzés: sebesség, gázpedál, akkuáram, akkuteljesítmény,
inverterhőmérséklet és min. cellafeszültség eloszlása.
Kétváltozós elemzés:
  (a) akkuáram <-> akkufeszültség: összevonva és munkamenetenként
  (b) motor-fordulatszám <-> becsült nyomaték teljes gáznál
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from scipy import stats

import os as _os
import sys as _sys
# a közös modul (hajtaslanc_kozos.py) a szülőmappában, a Beadando mappában van
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from hajtaslanc_kozos import (MAPPA, SZIN, SZIN2, HALVANY_SZIN, SZOVEG_SZIN,
                              MASODLAGOS_SZOVEG, SESSION_SZINEK, beolvas, cim,
                              ax_formaz, abra_mentes, ezres, heatmap, inverter_hiba_esemenyek)

LEIRO_CSV = os.path.join(MAPPA, "02_leiro_statisztika.csv")

EGYVALTOZOS = [
    ("speed_kmh", "Sebesség", "km/h"),
    ("apps_pct", "Gázpedál-állás", "%"),
    ("batt_current_A", "Akkuáram", "A"),
    ("batt_power_kW", "Akkuteljesítmény", "kW"),
    ("inverter_temp_C", "Inverterhőmérséklet", "°C"),
    ("cell_v_min_V", "Min. cellafeszültség", "V"),
]

# A hőtérképhez a redundáns párok egyik tagja elég (pl. cell_v_avg/max ~ cell_v_min).
KORRELACIOS_VALTOZOK = [
    "apps_pct", "torque_request_pct", "torque_est_Nm", "motor_rpm", "speed_kmh", "accel_ms2",
    "batt_current_A", "batt_voltage_V", "batt_power_kW", "soc_pct", "cell_v_min_V",
    "cell_t_max_C", "inverter_temp_C", "motor_temp_C",
]

TELJES_GAZ_PCT = 95          # gázpedál > 95% = teljes gáz
TELJES_KERES_PCT = 99        # nyomatékkérés ≥ 99% = a vezérlő ténylegesen teljes nyomatékot kér
FORDULAT_KORLAT = 3000       # a tesztnapon beállított motorfordulat-korlát
RPM_SAV = 250                # a nyomatékgörbe mediánjához használt fordulatszám-sáv
KIESES_ARAM_A = 1.0          # nagy kérés mellett ennél kisebb áram = nincs leadott teljesítmény
ALLANDO_TELJESITMENYEK_KW = [10, 20, 30, 40]


# ---------------------------------------------------------------------------
# Egyváltozós elemzés
# ---------------------------------------------------------------------------

def leiro_statisztika(df):
    """n, átlag, medián, szórás, min, Q1, Q3, max, IQR, ferdeség, csúcsosság."""
    szamok = df.select_dtypes("number").drop(columns=["t_s"])
    kvartilis = szamok.quantile([0.25, 0.5, 0.75])
    return pd.DataFrame({
        "n": szamok.count(),
        "átlag": szamok.mean(),
        "medián": kvartilis.loc[0.5],
        "szórás": szamok.std(),
        "min": szamok.min(),
        "Q1": kvartilis.loc[0.25],
        "Q3": kvartilis.loc[0.75],
        "max": szamok.max(),
        "IQR": kvartilis.loc[0.75] - kvartilis.loc[0.25],
        "ferdeség": szamok.skew(),
        "csúcsosság": szamok.kurt(),      # többlet-csúcsosság: normális eloszlásnál 0
    })


def egyvaltozos_ertelmezes(df, tabla):
    cim("Egyváltozós elemzés: leíró statisztikák")
    valtozok = [v for v, _, _ in EGYVALTOZOS]
    print(tabla.loc[valtozok].round(2).to_string())
    print()
    print("Ferdeség: 0 = szimmetrikus, > 0 = jobbra (a nagy értékek felé) elnyúló.")
    print("Csúcsosság (többlet): 0 = normális, < 0 = laposabb / többcsúcsú eloszlás.")

    sor = tabla.loc["speed_kmh"]
    cim("Sebesség")
    print("Átlag {:.1f}, medián {:.1f} km/h, szórás {:.1f}; ferdeség {:.2f}.".format(
        sor["átlag"], sor["medián"], sor["szórás"], sor["ferdeség"]))
    print("Álló (v < 1 km/h): {:.1%}, 75 km/h felett: {:.1%} (max. {:.1f} km/h).".format(
        (df["speed_kmh"] < 1).mean(), (df["speed_kmh"] > 75).mean(), sor["max"]))
    print("Az eloszlás enyhén balra ferde: a rajtok és az álló szakaszok húzzák lefelé,")
    print("felül pedig a ~3000 rpm-es fordulatszám-korlát ~80–87 km/h-nál elvágja.")

    cim("Gázpedál-állás")
    print("5% alatt: {:.1%}, 95% felett: {:.1%}, a kettő között: {:.1%}.".format(
        (df["apps_pct"] < 5).mean(), (df["apps_pct"] > TELJES_GAZ_PCT).mean(),
        df["apps_pct"].between(5, TELJES_GAZ_PCT).mean()))
    print("Csúcsosság {:.2f}: kétcsúcsú (U alakú) eloszlás. A pilóta többnyire vagy".format(
        tabla.loc["apps_pct", "csúcsosság"]))
    print("teljes gázt ad, vagy leveszi a gázt ('be-ki' vezetési stílus, gyorsulási próbák);")
    print("ezért az átlag ({:.1f}%) itt rossz középérték-mutató.".format(tabla.loc["apps_pct", "átlag"]))

    cim("Akkuáram és akkuteljesítmény")
    for v, nev in (("batt_current_A", "áram"), ("batt_power_kW", "teljesítmény")):
        s = tabla.loc[v]
        print("{}: átlag {:.2f}, medián {:.2f}, ferdeség {:.2f}".format(
            nev, s["átlag"], s["medián"], s["ferdeség"]))
    aram = df["batt_current_A"]
    terhelt = aram[aram >= 2].quantile([0.25, 0.75])
    print("Az eloszlás enyhén jobbra ferde, és lapos (negatív csúcsosság): két tömörülésből áll.")
    print("- közel nulla áram (gurulás, álló helyzet): a sorok {:.1%}-a 2 A alatt;".format((aram < 2).mean()))
    print("- terhelt szakaszok: a 2 A feletti sorok középső fele {:.0f}–{:.0f} A között;".format(
        terhelt.loc[0.25], terhelt.loc[0.75]))
    print("- a ritka, 80 A feletti áramok ({:.1%}) a teljes gázas rajtok csúcsai.".format((aram > 80).mean()))
    print("A teljesítmény ugyanezt az alakot követi, mert az akkufeszültség szűk sávban mozog")
    print("(P ≈ U · I; Pearson r = {:.3f}).".format(aram.corr(df["batt_power_kW"])))

    cim("Inverterhőmérséklet")
    s = tabla.loc["inverter_temp_C"]
    print("Átlag {:.1f}, medián {:.1f} °C, csúcsosság {:.2f} (lapos, kétcsúcsú).".format(
        s["átlag"], s["medián"], s["csúcsosság"]))
    print(df.groupby("session")["inverter_temp_C"].agg(["mean", "min", "max"]).round(1).to_string())
    print("A két csúcs a munkamenetekből adódik: az első kettőben ~50 °C, a 15:29-es és a")
    print("15:39-es munkamenetben már ~75 °C. Az inverter a nap folyamán felmelegedett.")

    cim("Min. cellafeszültség")
    s = tabla.loc["cell_v_min_V"]
    print("Tartomány {:.3f}–{:.3f} V, szórás {:.3f} V.".format(s["min"], s["max"], s["szórás"]))
    print(df.groupby("session")[["cell_v_min_V", "soc_pct"]].mean().round(3).to_string())
    print("Két hatás alakítja: a töltöttség (alacsonyabb SOC -> alacsonyabb nyugalmi")
    print("feszültség) és a terhelés (nagy áramnál a feszültség leesik, lásd (a)).")


def abra_egyvaltozos(df):
    fig = plt.figure(figsize=(15, 9.5))
    # az 5 sorból a középső (2.) üres térköz a két ábrasor között
    racs = GridSpec(5, 3, figure=fig, height_ratios=[1, 4, 1.3, 1, 4], hspace=0.12, wspace=0.22)
    for i, (oszlop, nev, egyseg) in enumerate(EGYVALTOZOS):
        sor, oszl = (i // 3) * 3, i % 3
        ax_doboz = fig.add_subplot(racs[sor, oszl])
        ax_hiszt = fig.add_subplot(racs[sor + 1, oszl], sharex=ax_doboz)
        s = df[oszlop]
        doboz = ax_doboz.boxplot(s, vert=False, widths=0.6, patch_artist=True,
                                 medianprops={"color": SZOVEG_SZIN, "linewidth": 1.6},
                                 flierprops={"marker": "o", "markersize": 3,
                                             "markerfacecolor": SZIN2, "markeredgecolor": "none"})
        doboz["boxes"][0].set(facecolor=SZIN, alpha=0.45, edgecolor=SZIN)
        ax_doboz.axis("off")
        ax_doboz.set_title("{} [{}]   ferdeség {}, csúcsosság {}".format(
            nev, egyseg, ezres(s.skew(), 2), ezres(s.kurt(), 2)), loc="left", fontsize=10.5)

        ax_hiszt.hist(s, bins=30, color=SZIN, alpha=0.75, edgecolor="white", linewidth=0.6)
        ax_hiszt.axvline(s.mean(), color=SZIN2, linewidth=2, label="átlag")
        ax_hiszt.axvline(s.median(), color=SZOVEG_SZIN, linewidth=1.5, linestyle="--",
                         label="medián")
        ax_formaz(ax_hiszt, "", egyseg, "gyakoriság" if oszl == 0 else "", racs="y")
    kezelok, feliratok = ax_hiszt.get_legend_handles_labels()
    fig.legend(kezelok, feliratok, loc="upper right", ncol=2, frameon=False, fontsize=10)
    fig.suptitle("Egyváltozós eloszlások (n = {} sor, 10 Hz)".format(len(df)),
                 x=0.01, ha="left", fontsize=13)
    fig.subplots_adjust(left=0.05, right=0.99, top=0.9, bottom=0.07)
    abra_mentes(fig, "02_egyvaltozos.png")


# ---------------------------------------------------------------------------
# Kétváltozós elemzés
# ---------------------------------------------------------------------------

def korrelacio(df):
    cim("Spearman-korreláció (áttekintés)")
    korr = df[KORRELACIOS_VALTOZOK].corr(method="spearman")
    parok = korr.where(np.triu(np.ones(korr.shape, dtype=bool), k=1)).stack()
    eros = parok[parok.abs() >= 0.7].sort_values(key=abs, ascending=False)
    print("Erős kapcsolatok (|ρ| ≥ 0,7):")
    for (a, b), r in eros.items():
        print("  {:20s} – {:20s} ρ = {:+.2f}".format(a, b, r))
    print()
    print("Spearman-féle rangkorrelációt használunk, mert több változó ferde vagy kétcsúcsú,")
    print("és a kapcsolatok nem mind lineárisak (pl. nyomaték–fordulatszám).")
    print("- speed_kmh – motor_rpm ρ = 1: a sebességet a vezérlő a fordulatszámból számolja")
    print("  (állandó áttétel, rpm / sebesség = 37,09), ezért a kettő ugyanaz az információ.")
    print("- apps_pct – torque_request_pct: a pedálállásból képzett nyomatékkérés.")
    print("- A hőmérsékletek és a feszültség/SOC közti erős kapcsolat nem ok-okozati: mindkettő")
    print("  az idővel változik (a későbbi munkamenetek melegebbek és alacsonyabb SOC-ról")
    print("  indulnak). A munkamenet közös háttérváltozó (zavaró tényező).")

    fig, ax = plt.subplots(figsize=(11, 9.5))
    kep = heatmap(ax, korr)
    fig.colorbar(kep, ax=ax, shrink=0.75, label="Spearman ρ")
    ax.set_title("Spearman-korrelációs mátrix", loc="left", fontsize=12)
    fig.tight_layout()
    abra_mentes(fig, "02_korrelacio.png")


def aram_feszultseg(df):
    cim("(a) Akkuáram <-> akkufeszültség: feszültségesés és belső ellenállás")
    x, y = df["batt_current_A"], df["batt_voltage_V"]
    pearson = stats.pearsonr(x, y)
    spearman = stats.spearmanr(x, y)
    osszevont = stats.linregress(x, y)
    print("Összevonva (n = {}):".format(len(df)))
    print("  Pearson r = {:.3f} (p = {:.1e}), Spearman ρ = {:.3f} (p = {:.1e})".format(
        pearson.statistic, pearson.pvalue, spearman.statistic, spearman.pvalue))
    print("  U = {:.1f} V − {:.0f} mΩ · I,  R² = {:.3f}".format(
        osszevont.intercept, -osszevont.slope * 1000, osszevont.rvalue ** 2))

    sorok = []
    for session, resz in df.groupby("session"):
        reg = stats.linregress(resz["batt_current_A"], resz["batt_voltage_V"])
        sorok.append({"munkamenet": session, "n": len(resz),
                      "SOC átlag %": round(resz["soc_pct"].mean(), 1),
                      "U0 [V]": round(reg.intercept, 1),
                      "R [mΩ]": round(-reg.slope * 1000), "r": round(reg.rvalue, 3),
                      "R²": round(reg.rvalue ** 2, 3), "p": "{:.1e}".format(reg.pvalue),
                      "_reg": reg, "_imax": resz["batt_current_A"].max()})
    tabla = pd.DataFrame(sorok)
    print()
    print("Munkamenetenként (U = U0 − R · I):")
    print(tabla.drop(columns=["_reg", "_imax"]).to_string(index=False))

    # közös belső ellenállás, munkamenetenként külön U0-val (legkisebb négyzetek)
    X = pd.get_dummies(df["session"], dtype=float)
    X["I"] = x
    egyutthatok, *_ = np.linalg.lstsq(X.to_numpy(), y.to_numpy(), rcond=None)
    becsles = X.to_numpy() @ egyutthatok
    r2_kozos = 1 - ((y - becsles) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    r_kozos = -egyutthatok[-1] * 1000
    print()
    print("Közös modell (munkamenetenként külön U0, közös R): R = {:.0f} mΩ, R² = {:.3f}".format(
        r_kozos, r2_kozos))
    print()
    print("Értelmezés: munkameneten belül az áram szorosan, lineárisan meghatározza a")
    print("feszültséget (r = {:.2f}…{:.2f}); a meredekség az akkumulátor belső ellenállása,".format(
        tabla["r"].min(), tabla["r"].max()))
    print("~{:.0f} mΩ (110 cellára ~{:.2f} mΩ/cella). Összevonva a kapcsolat jóval gyengébbnek".format(
        r_kozos, r_kozos / 110))
    print("látszik (r = {:.2f}), mert a munkamenetek eltérő töltöttségről indulnak: az U0".format(
        pearson.statistic))
    print("{}–{} V között változik a SOC-cal. A munkamenet zavaró tényező (Simpson-paradoxon".format(
        ezres(tabla["U0 [V]"].min(), 1), ezres(tabla["U0 [V]"].max(), 1)))
    print("jellegű hatás); ha figyelembe vesszük, a modell R²-e {:.2f}-ről {:.2f}-re nő.".format(
        osszevont.rvalue ** 2, r2_kozos))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.4), sharey=True)
    ax1.scatter(x, y, s=10, color=SZIN, alpha=0.35, edgecolor="none")
    racs_x = np.linspace(x.min(), x.max(), 50)
    ax1.plot(racs_x, osszevont.intercept + osszevont.slope * racs_x, color=SZIN2, linewidth=2.2)
    ax1.text(0.98, 0.97, "r = {}   R² = {}\nmeredekség: {} mΩ".format(
        ezres(pearson.statistic, 2), ezres(osszevont.rvalue ** 2, 2),
        ezres(-osszevont.slope * 1000)), transform=ax1.transAxes, ha="right", va="top",
        fontsize=10, color=SZOVEG_SZIN)
    ax_formaz(ax1, "Összevonva: egyetlen egyenes", "akkuáram [A]", "akkufeszültség [V]")

    ax2.scatter(x, y, s=8, color=HALVANY_SZIN, alpha=0.35, edgecolor="none")
    for _, sor in tabla.iterrows():
        reg = sor["_reg"]
        vonal_x = np.array([0, sor["_imax"]])
        ax2.plot(vonal_x, reg.intercept + reg.slope * vonal_x,
                 color=SESSION_SZINEK[sor["munkamenet"]], linewidth=2.6,
                 label="{} · SOC {}% · R = {} mΩ · r = {}".format(
                     sor["munkamenet"], ezres(sor["SOC átlag %"], 0), sor["R [mΩ]"],
                     ezres(sor["r"], 2)))
    ax2.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.13),
               ncol=2, title="munkamenet · átlagos SOC · belső ellenállás · korreláció",
               title_fontsize=9)
    ax2.text(0.98, 0.97, "közös R = {} mΩ, R² = {}".format(ezres(r_kozos), ezres(r2_kozos, 2)),
             transform=ax2.transAxes, ha="right", va="top", fontsize=10, color=SZOVEG_SZIN)
    ax_formaz(ax2, "Munkamenetenként: külön U0, hasonló meredekség", "akkuáram [A]", "")
    fig.suptitle("Feszültségesés az áram függvényében (belső ellenállás)", x=0.01, ha="left",
                 fontsize=13)
    fig.tight_layout()
    abra_mentes(fig, "02_aram_feszultseg.png")


def korlat_futamonkent(df):
    """Teljes kérésű futamonként az átlagteljesítmény a korlát alatt (2500–3000) és felett."""
    teljes = (df["torque_request_pct"] >= TELJES_KERES_PCT) & (df["batt_current_A"] >= KIESES_ARAM_A)
    uj = ((df["session"] != df["session"].shift()) | (teljes != teljes.shift())
          | (df["t_s"].diff() > 0.15))
    futam = uj.cumsum()
    sorok = []
    for _, g in df[teljes].groupby(futam[teljes]):
        alatta = g[g["motor_rpm"].between(2500, FORDULAT_KORLAT)]
        felette = g[g["motor_rpm"] > FORDULAT_KORLAT]
        if len(alatta) >= 3 and len(felette) >= 3:
            sorok.append({"munkamenet": g["session"].iloc[0], "kezdet_s": g["t_s"].iloc[0],
                          "P alatta [kW]": alatta["batt_power_kW"].mean(),
                          "P felette [kW]": felette["batt_power_kW"].mean(),
                          "T alatta [Nm]": alatta["torque_est_Nm"].mean(),
                          "T felette [Nm]": felette["torque_est_Nm"].mean()})
    return pd.DataFrame(sorok)


def nyomatek_fordulat(df):
    cim("(b) Motor-fordulatszám <-> becsült nyomaték teljes gáznál")
    gaz = df[df["apps_pct"] > TELJES_GAZ_PCT]
    megvonas = gaz[gaz["torque_request_pct"] < 90]
    print("Teljes gáz (gázpedál > {}%): {} sor. Ebből {} sorban ({:.1%}) a nyomatékkérés".format(
        TELJES_GAZ_PCT, len(gaz), len(megvonas), len(megvonas) / len(gaz)))
    print("0% (rövid, 0,1–0,4 s-os nyomatékmegvonások, {}–{} rpm között). Az okuk a meglévő".format(
        megvonas["motor_rpm"].min(), megvonas["motor_rpm"].max()))
    print("jelekből nem azonosítható (fékjel ebben a blokkban nincs). Ezért az elemzés a")
    print("ténylegesen teljes nyomatékkérésű sorokra szűkül (kérés ≥ {}%).".format(TELJES_KERES_PCT))
    mind = df[(df["torque_request_pct"] >= TELJES_KERES_PCT) & df["torque_est_Nm"].notna()]
    nulla = mind["batt_current_A"] < KIESES_ARAM_A
    tg = mind[~nulla]
    print("Teljes nyomatékkérés és n > 500 rpm: {} sor; ebből {} sorban az akkuáram < {} A.".format(
        len(mind), nulla.sum(), ezres(KIESES_ARAM_A, 0)))
    print("Ezek rövid átmenetek (az inverterhiba-szakaszok már ki vannak zárva): a kérés")
    print("0-ról 100%-ra fut fel, és az áram ~0,2–0,5 s késéssel követi. A nyomatékgörbe")
    print("mediánja csak a teljesítményt leadó sorokból ({} sor) készül.".format(len(tg)))
    print()
    spearman = stats.spearmanr(tg["motor_rpm"], tg["torque_est_Nm"])
    print("Spearman ρ = {:.3f} (p = {:.1e})".format(spearman.statistic, spearman.pvalue))
    savok = pd.cut(tg["motor_rpm"], range(500, 3501, RPM_SAV))
    tabla = tg.groupby(savok, observed=True).agg(
        n=("torque_est_Nm", "size"), nyomatek_median=("torque_est_Nm", "median"),
        teljesitmeny_median_kW=("batt_power_kW", "median"),
        aram_median_A=("batt_current_A", "median"))
    print(tabla.round(1).to_string())
    print()
    teljesitmeny = tabla.loc[[iv.left >= 1000 and iv.right <= FORDULAT_KORLAT for iv in tabla.index],
                             "teljesitmeny_median_kW"]
    print("Értelmezés: a kérés végig 100%, a becsült nyomaték mégis csökken a fordulatszám")
    print("növekedésével (ρ = {:.2f}). 1000 és {} rpm között közel hiperbolikusan, azaz".format(
        spearman.statistic, FORDULAT_KORLAT))
    print("közel állandó, ~{:.0f}–{:.0f} kW akkuteljesítmény mellett. Itt tehát nem a vezérlő".format(
        teljesitmeny.min(), teljesitmeny.max()))
    print("kérése, hanem a hajtáslánc rendelkezésre álló teljesítménye korlátoz.")
    print()
    print("{} rpm felett a medián tovább esik ({} Nm). Futamonkénti ellenőrzés: a teljes".format(
        FORDULAT_KORLAT, ezres(tabla["nyomatek_median"].iloc[-1], 1)))
    print("kérésű futamok közül azok, amelyek a korlát alatt (2500–3000 rpm) és felett is")
    print("legalább 0,3 s-ot töltenek:")
    print(korlat_futamonkent(df).round(1).to_string(index=False))
    print("Csak ennyi futam éri el a korlát feletti tartományt, és ezek közül nem mindegyikben")
    print("csökken a teljesítmény. A mediáncsökkenés részben összetételi hatás: a két sávba")
    print("más-más futamok (eltérő teljesítményszintű) pontjai kerülnek. A korlát hatása így")
    print("nem igazolható egyértelműen. Szembetűnő viszont, hogy a 15:21:59-es munkamenetben")
    print("a 3241 rpm-es túllövés után közvetlenül következett az egyik inverterhiba.")
    print("Megjegyzés: a torque_est_Nm az elektromos teljesítményből számolt felső becslés,")
    print("a veszteségeket nem vonja le; 1000 rpm alatt kevés a mérési pont (n = {}).".format(
        int((tg["motor_rpm"] <= 1000).sum())))

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.scatter(tg["motor_rpm"], tg["torque_est_Nm"], s=12, color=SZIN, alpha=0.4,
               edgecolor="none", label="mérés (10 Hz-es sor)")
    ax.scatter(mind.loc[nulla, "motor_rpm"], mind.loc[nulla, "torque_est_Nm"].clip(lower=0),
               s=22, marker="x", color=MASODLAGOS_SZOVEG, linewidth=1,
               label="áram ≈ 0 a 100%-os kérés ellenére (átmenet)")
    kozep = [iv.mid for iv in tabla.index]
    ax.plot(kozep, tabla["nyomatek_median"], color=SZIN2, linewidth=2.4, marker="o",
            markersize=8, label="medián ({} rpm-es sávok)".format(RPM_SAV))
    fordulat = np.linspace(600, 3400, 200)
    for p_kw in ALLANDO_TELJESITMENYEK_KW:
        nyomatek = p_kw * 1000 / (fordulat * 2 * np.pi / 60)
        lathato = nyomatek < 230
        ax.plot(fordulat[lathato], nyomatek[lathato], color=HALVANY_SZIN, linewidth=1,
                linestyle="--")
        ax.text(fordulat[-1] + 20, nyomatek[-1], "{} kW".format(p_kw), fontsize=9,
                color=MASODLAGOS_SZOVEG, va="center")
    ax.axvline(FORDULAT_KORLAT, color=MASODLAGOS_SZOVEG, linewidth=1)
    ax.text(FORDULAT_KORLAT - 30, 222, "fordulatszám-korlát\n≈ {} rpm".format(FORDULAT_KORLAT),
            ha="right", va="top", fontsize=9, color=MASODLAGOS_SZOVEG)
    ax.set_xlim(400, 3600)
    ax.set_ylim(-5, 230)
    ax.legend(frameon=False, loc="lower left", fontsize=9)
    ax_formaz(ax, "Becsült nyomaték a fordulatszám függvényében 100%-os nyomatékkérésnél "
              "(szaggatott: állandó teljesítmény)", "motor-fordulatszám [1/min]",
              "becsült nyomaték [Nm]")
    fig.tight_layout()
    abra_mentes(fig, "02_nyomatek_fordulat.png")


# ---------------------------------------------------------------------------
# Főprogram
# ---------------------------------------------------------------------------

def main():
    pd.set_option("display.width", 150)
    teljes = beolvas()
    print("Beolvasva: {} sor, {} oszlop".format(*teljes.shape))
    cim("Inverterhiba-szakaszok: kizárva a feltáró elemzésből")
    print(inverter_hiba_esemenyek(teljes).round(1).to_string(index=False))
    df = teljes[~teljes["inverter_hiba"]].copy()
    print("Kizárva: {} sor (az inverter hiba miatt ki volt kapcsolva, a hajtáslánc nem működött).".format(
        teljes["inverter_hiba"].sum()))
    print("Az elemzés {} soron fut.".format(len(df)))

    tabla = leiro_statisztika(df)
    tabla.round(4).to_csv(LEIRO_CSV, sep=";", encoding="utf-8", index_label="valtozo")
    egyvaltozos_ertelmezes(df, tabla)
    abra_egyvaltozos(df)

    korrelacio(df)
    aram_feszultseg(df)
    nyomatek_fordulat(df)

    print()
    print("Leíró statisztikák mentve: {}".format(LEIRO_CSV))
    plt.show()


if __name__ == "__main__":
    main()
