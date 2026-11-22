# -*- coding: utf-8 -*-
"""4. Az inverter melegedésének előrejelzése (elsőrendű hőmodell).

Bemenet: 01_hajtaslanc_tisztitott.csv
         01_hajtaslanc_uj_tisztitott.csv (csak a teljesítmény–hőmérséklet kiegészítéshez)
Kimenet: 04_homodell_elorejelzes.csv – forgatókönyvek mindkét modellel
         04_homodell_validacio.png, 04_homodell_forgatokonyvek.png,
         04_teljesitmeny_homerseklet.png

Az inverter védelmi határai (a csapat tájékoztatása): 83 °C felett biztosan lekapcsol;
kb. 70 °C-tól a hőmérséklet arányában visszaszabályozza a leadható nyomatékot (bizonytalan).

Modell (a terheléssel arányos hőtermelés + newtoni hűlés):
    dT/dt = α · u − β · (T − T∞)
  α   melegedési sebesség egységnyi terhelésnél [°C/s]
  β   hűlési együttható [1/s]; τ = 1/β az időállandó [s]
  T∞  terhelés nélküli egyensúlyi hőmérséklet [°C]
Két bemenet (u):
  FŐ MODELL:          u = a ténylegesen leadott (becsült) nyomaték / 100 Nm
  ÖSSZEHASONLÍTÁS:    u = a nyomatékkérés (0…1)
  Mindkettő 0, ha az inverter nem ad áramot (akkuáram < 1 A vagy inverter_hiba):
  ilyenkor nincs hőtermelés, csak hűlés. Az inverterhiba-szakaszok így hűlési adatként
  bent maradnak.
Becslés: legkisebb négyzetek 1 s-os ablakokra (a 0,1 °C-os felbontás zaját átlagolja):
    (T[k+10] − T[k]) / 1 s = β·T∞ + α · átlag(u[k..k+9]) − β · T[k]
Validáció: leave-one-session-out. 3 munkameneten illesztünk, a 4.-et a kezdő
    hőmérsékletéből és a mért bemenetből szimuláljuk (RMSE), összevetve a „változatlan
    hőmérséklet" alapmodellel; futamszintű melegedés: mért vs. jósolt.
Előrejelzés: állandó u terhelés D ideig, T0-ról indulva (analitikus megoldás):
    T(t) = T_ss + (T0 − T_ss) · exp(−t/τ),   T_ss = T∞ + α·u/β
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

from hajtaslanc_kozos import (MAPPA, SZIN, SZIN2, SZIN3, HALVANY_SZIN, SZOVEG_SZIN,
                              MASODLAGOS_SZOVEG, DT_S, ALFA, INVERTER_LEKAPCSOLASI_T_C,
                              INVERTER_LESZABALYOZAS_T_C, beolvas, cim, ax_formaz, abra_mentes,
                              ezres, futam_azonosito)

ELOREJELZES_CSV = os.path.join(MAPPA, "04_homodell_elorejelzes.csv")
UJ_CSV = os.path.join(MAPPA, "01_hajtaslanc_uj_tisztitott.csv")
TELJESITMENY_RPM = (1500, 3000)   # ebben a sávban hasonlítjuk a teljes kérésű teljesítményt
MIN_FUTAM_MINTA = 5

ABLAK = 10                  # 10 minta = 1 s
AKTIV_ARAM_A = 1.0          # e fölött ad ténylegesen áramot az inverter
NYOMATEK_EGYSEG_NM = 100    # a fő modell bemenete 100 Nm-es egységben
VEG_MINTA = 3               # mint a 03-ban: futam eleje / vége = első / utolsó 0,3 s átlaga
TELJES_KERES_PCT = 99
FORDULAT_SAVOK = [500, 1000, 1500, 2000, 2500, 3000, 3500]

FORGATOKONYV_T0 = [45, 60, 75]
FORGATOKONYV_NYOMATEK_NM = [50, 100, 150, 200]
FORGATOKONYV_KERES_PCT = [25, 50, 75, 100]
FORGATOKONYV_IDO = [2, 4, 10, 20]
PELDA_T0 = 60
PELDA_IDO_S = 4

MODELLEK = {
    "nyomaték": {"nev": "tényleges nyomaték (fő modell)", "egyseg": "Nm", "skala": NYOMATEK_EGYSEG_NM,
                 "szintek": FORGATOKONYV_NYOMATEK_NM},
    "kérés": {"nev": "nyomatékkérés (összehasonlítás)", "egyseg": "%", "skala": 100,
              "szintek": FORGATOKONYV_KERES_PCT},
}


# ---------------------------------------------------------------------------
# Bemenetek, illesztés, szimuláció
# ---------------------------------------------------------------------------

def inverter_aktiv(df):
    return (df["batt_current_A"] >= AKTIV_ARAM_A) & ~df["inverter_hiba"]


def tenyleges_nyomatek(df):
    """Becsült tényleges nyomaték [Nm]; 500 rpm alatt P / ω, 500 rpm-mel számolva."""
    omega_min = np.maximum(df["motor_rpm"], 500) * 2 * np.pi / 60
    return df["torque_est_Nm"].fillna(df["batt_power_kW"] * 1000 / omega_min).clip(lower=0)


def bemenet(df, modell):
    ertek = tenyleges_nyomatek(df) if modell == "nyomaték" else df["torque_request_pct"]
    return pd.Series(np.where(inverter_aktiv(df), ertek / MODELLEK[modell]["skala"], 0.0),
                     index=df.index)


def illesztes(df, u):
    X, Y = [], []
    for _, g in df.groupby("session", sort=False):
        t = g["t_s"].to_numpy()
        T = g["inverter_temp_C"].to_numpy()
        uu = u.loc[g.index].to_numpy()
        for k in range(len(T) - ABLAK):
            dt = t[k + ABLAK] - t[k]
            if abs(dt - ABLAK * DT_S) > 0.01:      # a tisztításkor törölt sorok résén átnyúló ablak
                continue
            X.append([1.0, uu[k:k + ABLAK].mean(), T[k]])
            Y.append((T[k + ABLAK] - T[k]) / dt)
    c, *_ = np.linalg.lstsq(np.array(X), np.array(Y), rcond=None)
    beta = -c[2]
    return {"alfa": c[1], "beta": beta, "tau": 1 / beta, "T_inf": c[0] / beta, "ablakok": len(Y)}


def szimulacio(p, t, u, T0):
    T = np.empty(len(t))
    T[0] = T0
    for k in range(len(t) - 1):
        dt = t[k + 1] - t[k]
        T[k + 1] = T[k] + dt * (p["alfa"] * u[k] - p["beta"] * (T[k] - p["T_inf"]))
    return T


def analitikus(p, T0, u, ido):
    """Hőmérséklet állandó u terhelés mellett, ido másodperc után."""
    T_ss = p["T_inf"] + p["alfa"] * u / p["beta"]
    return T_ss + (T0 - T_ss) * np.exp(-np.asarray(ido) / p["tau"])


# ---------------------------------------------------------------------------
# Validáció
# ---------------------------------------------------------------------------

def loso_validacio(df, u):
    """Leave-one-session-out: paraméterek, RMSE és szimulált görbe munkamenetenként."""
    eredmeny = {}
    for session in df["session"].unique():
        p = illesztes(df[df["session"] != session], u)
        g = df[df["session"] == session]
        mert = g["inverter_temp_C"].to_numpy()
        sim = szimulacio(p, g["t_s"].to_numpy(), u.loc[g.index].to_numpy(), mert[0])
        eredmeny[session] = {"p": p, "sim": sim, "rmse": np.sqrt(np.mean((sim - mert) ** 2)),
                             "rmse_alap": np.sqrt(np.mean((mert[0] - mert) ** 2))}
    return eredmeny


def futamszintu_validacio(df, u, loso):
    df = df.copy()
    df["futam"] = futam_azonosito(df[~df["inverter_hiba"]])
    sorok = []
    for futam, g in df.dropna(subset=["futam"]).groupby("futam"):
        p = loso[g["session"].iloc[0]]["p"]
        mert = g["inverter_temp_C"].to_numpy()
        T0 = mert[:VEG_MINTA].mean()
        sim = szimulacio(p, g["t_s"].to_numpy(), u.loc[g.index].to_numpy(), T0)
        sorok.append({"futam": int(futam), "munkamenet": g["session"].iloc[0], "T0": T0,
                      "dT_mert": mert[-VEG_MINTA:].mean() - T0,
                      "dT_josolt": sim[-VEG_MINTA:].mean() - T0})
    return pd.DataFrame(sorok)


def modellek_illesztese(df):
    eredmeny = {}
    for modell, leiras in MODELLEK.items():
        u = bemenet(df, modell)
        loso = loso_validacio(df, u)
        futamok = futamszintu_validacio(df, u, loso)
        eredmeny[modell] = {"u": u, "p": illesztes(df, u), "loso": loso, "futamok": futamok}
    futam = futam_azonosito(df[~df["inverter_hiba"]])
    eredmeny["nyomaték"]["max_futam_s"] = futam.value_counts().max() * DT_S
    return eredmeny


def eredmenyek_kiirasa(df, eredmeny):
    cim("Elsőrendű hőmodell: illesztés a teljes adaton")
    print("Bemenet = 0, ahol az inverter nem ad áramot: {} sor (ebből inverterhiba: {}).".format(
        int((~inverter_aktiv(df)).sum()), int(df["inverter_hiba"].sum())))
    for modell, leiras in MODELLEK.items():
        p = eredmeny[modell]["p"]
        print("{}: α = {:.3f} °C/s / {} {}, τ = {:.1f} s, T∞ = {:.1f} °C  [{} ablak]".format(
            leiras["nev"], p["alfa"], leiras["skala"], leiras["egyseg"], p["tau"], p["T_inf"],
            p["ablakok"]))
    p = eredmeny["nyomaték"]["p"]
    print()
    print("A fő modell értelmezése:")
    print("- α: 100 Nm leadott nyomatéknál az inverter kezdetben ~{} °C/s sebességgel melegszik".format(
        ezres(p["alfa"], 2)))
    print("  (200 Nm-nél kétszer ennyivel); melegebb inverternél a hűlés ezt csökkenti.")
    print("- τ ≈ {} s: terhelés nélkül a T∞ feletti többlet {} s alatt feleződik (τ · ln 2).".format(
        ezres(p["tau"]), ezres(p["tau"] * np.log(2))))
    print("- T∞ ≈ {} °C: terhelés nélkül ide hűlne vissza az inverter (≈ hűtőközeg / környezet).".format(
        ezres(p["T_inf"], 1)))
    print("- A modell rövid, néhány 10 s-os terhelésekre érvényes (mért tartomány: 41–84 °C,")
    print("  legfeljebb ~13 s-os futamok); tartós terhelésre extrapolálva nem megbízható.")

    cim("Validáció: leave-one-session-out (a kihagyott munkamenet szimulálása)")
    sorok = []
    for session in df["session"].unique():
        fo = eredmeny["nyomaték"]["loso"][session]
        sorok.append({"kihagyott munkamenet": session, "α [°C/s/100 Nm]": fo["p"]["alfa"],
                      "τ [s]": fo["p"]["tau"], "T∞ [°C]": fo["p"]["T_inf"],
                      "RMSE nyomaték-modell": fo["rmse"],
                      "RMSE kérés-modell": eredmeny["kérés"]["loso"][session]["rmse"],
                      "RMSE alapmodell": fo["rmse_alap"]})
    tabla = pd.DataFrame(sorok)
    print(tabla.round(2).to_string(index=False))
    print("Átlagos RMSE: nyomaték-modell {:.2f} °C, kérés-modell {:.2f} °C, alapmodell".format(
        tabla["RMSE nyomaték-modell"].mean(), tabla["RMSE kérés-modell"].mean()))
    print("(„változatlan hőmérséklet\") {:.2f} °C.".format(tabla["RMSE alapmodell"].mean()))

    cim("Futamszintű validáció: a futam alatti melegedés, mért vs. jósolt (LOSO)")
    futamok = eredmeny["nyomaték"]["futamok"].rename(columns={"dT_josolt": "dT_nyomatek_modell"})
    futamok["dT_keres_modell"] = eredmeny["kérés"]["futamok"]["dT_josolt"]
    print(futamok.round(2).to_string(index=False))
    print()
    mae_alap = (futamok["dT_mert"] - futamok["dT_mert"].mean()).abs().mean()
    for modell, leiras in MODELLEK.items():
        f = eredmeny[modell]["futamok"]
        r = stats.pearsonr(f["dT_mert"], f["dT_josolt"])
        print("{:34s} r = {:.2f} (p = {:.4f}), átlagos abszolút hiba {:.2f} °C".format(
            leiras["nev"] + ":", r.statistic, r.pvalue, (f["dT_mert"] - f["dT_josolt"]).abs().mean()))
    print("{:34s} átlagos abszolút hiba {:.2f} °C".format("viszonyítás (mindig az átlag):", mae_alap))
    print()
    print("A tényleges nyomaték sokkal jobb előrejelző, mint a kérés: az inverter vesztesége a")
    print("ténylegesen folyó áramtól függ, a kérés ennek csak közelítése. Magas fordulaton a")
    print("teljesítménykorlát miatt 100%-os kérés mellett is kevesebb nyomaték (és hő) keletkezik.")
    print("A maradék hiba oka főleg, hogy a hűtőközeg hőmérséklete és áramlása nincs mérve.")
    return tabla


# ---------------------------------------------------------------------------
# Előrejelzés
# ---------------------------------------------------------------------------

def forgatokonyvek(df, eredmeny):
    cim("Előrejelzés: forgatókönyvek (állandó terhelés D ideig, T0-ról)")
    max_T = df["inverter_temp_C"].max()
    max_futam_s = eredmeny["nyomaték"]["max_futam_s"]
    print("A mért tartomány: inverterhőmérséklet legfeljebb {} °C, futamhossz legfeljebb {} s.".format(
        ezres(max_T, 1), ezres(max_futam_s, 1)))
    print("Az ezen kívül eső forgatókönyvek extrapolációk (CSV: mert_tartomanyon_kivul = True),")
    print("ezek csak tájékoztató jellegűek.")
    sorok = []
    for modell, leiras in MODELLEK.items():
        p = eredmeny[modell]["p"]
        for T0 in FORGATOKONYV_T0:
            for szint in leiras["szintek"]:
                for ido in FORGATOKONYV_IDO:
                    T_veg = float(analitikus(p, T0, szint / leiras["skala"], ido))
                    sorok.append({"modell": leiras["nev"], "bemenet": szint, "egyseg": leiras["egyseg"],
                                  "kezdo_T_C": T0, "idotartam_s": ido, "veg_T_C": round(T_veg, 2),
                                  "melegedes_C": round(T_veg - T0, 2),
                                  "mert_tartomanyon_kivul": bool(T_veg > max_T or ido > max_futam_s)})
    tabla = pd.DataFrame(sorok)
    fo = tabla[tabla["modell"] == MODELLEK["nyomaték"]["nev"]].copy()
    fo["cella"] = [("{:.1f}*" if kivul else "{:.1f}").format(m)
                   for m, kivul in zip(fo["melegedes_C"], fo["mert_tartomanyon_kivul"])]
    for T0 in FORGATOKONYV_T0:
        print()
        print("Fő modell, kezdő hőmérséklet {} °C – melegedés [°C] (sor: nyomaték Nm, oszlop: időtartam s;"
              .format(T0))
        print("* = a mért tartományon kívül, extrapoláció):")
        print(fo[fo["kezdo_T_C"] == T0].pivot(index="bemenet", columns="idotartam_s",
                                               values="cella").to_string())
    return tabla


def keres_atvaltasa(df, p):
    """Adott (100%-os) kérés mekkora tényleges nyomatékot ad, és az mennyivel melegít."""
    cim("A kérdés: mennyivel melegít egy 100%-os nyomatékkérés? (a fő modellel)")
    aktiv = df[inverter_aktiv(df) & (df["torque_request_pct"] >= TELJES_KERES_PCT)]
    nyomatek = tenyleges_nyomatek(aktiv)
    savok = pd.cut(aktiv["motor_rpm"], FORDULAT_SAVOK)
    tabla = nyomatek.groupby(savok, observed=True).agg(["size", "median"]).rename(
        columns={"size": "n", "median": "nyomatek_median_Nm"})
    tabla["melegedes_C"] = [float(analitikus(p, PELDA_T0, m / NYOMATEK_EGYSEG_NM, PELDA_IDO_S)) - PELDA_T0
                            for m in tabla["nyomatek_median_Nm"]]
    tabla.index = ["{}–{}".format(iv.left, iv.right) for iv in tabla.index]
    tabla.index.name = "fordulat [rpm]"
    print("100%-os kérés {} s-ig, {} °C-ról; a tényleges nyomaték a mért medián fordulatszám-".format(
        PELDA_IDO_S, PELDA_T0))
    print("sávonként (a teljesítménykorlát miatt a fordulattal csökken):")
    print(tabla.round(1).to_string())
    print()
    print("Ugyanaz a 100%-os kérés alacsony fordulaton ~{} °C-kal, a 2500–3000 rpm-es sávban".format(
        ezres(tabla["melegedes_C"].iloc[0], 1)))
    print("csak ~{} °C-kal melegíti az invertert {} s alatt.".format(
        ezres(tabla.loc["2500–3000", "melegedes_C"], 1), PELDA_IDO_S))
    return tabla


def ido_a_lekapcsolasig(p, max_futam_s):
    """Állandó nyomaték mellett mennyi idő alatt éri el az inverter a lekapcsolási határt."""
    cim("Mennyi idő alatt éri el az inverter a {:.0f} °C-os lekapcsolási határt? (fő modell)".format(
        INVERTER_LEKAPCSOLASI_T_C))
    sorok = []
    for T0 in FORGATOKONYV_T0:
        sor = {"kezdő T [°C]": T0}
        for nyom in FORGATOKONYV_NYOMATEK_NM:
            T_ss = p["T_inf"] + p["alfa"] * nyom / NYOMATEK_EGYSEG_NM / p["beta"]
            if T_ss <= INVERTER_LEKAPCSOLASI_T_C:
                sor["{} Nm".format(nyom)] = "nem éri el"
            else:
                ido = p["tau"] * np.log((T_ss - T0) / (T_ss - INVERTER_LEKAPCSOLASI_T_C))
                sor["{} Nm".format(nyom)] = "{:.1f} s{}".format(ido, "*" if ido > max_futam_s else "")
        sorok.append(sor)
    print(pd.DataFrame(sorok).to_string(index=False))
    print("* = hosszabb, mint a leghosszabb mért futam ({} s): extrapoláció.".format(ezres(max_futam_s, 1)))
    print("A modell állandó nyomatékot feltételez. A valóságban ~{:.0f} °C felett az inverter".format(
        INVERTER_LESZABALYOZAS_T_C))
    print("visszaszabályozza a nyomatékot, ez lassítja a melegedést; az idők ezért alsó becslések.")
    print("Két lekapcsolás a mérésben is a 83 °C-os határnál történt (15:29:33: 84,3 °C, 15:39:36: 84,2 °C).")


def teljesitmeny_homerseklet(df):
    """Teljes kérésű futamok teljesítménye az inverterhőmérséklet függvényében (délelőtt + délután)."""
    cim("Kiegészítés: teljes kérésű teljesítmény és inverterhőmérséklet")
    reszek = []
    for nev, adat in (("délután (tanító)", df), ("délelőtt (12:59:30)", beolvas(UJ_CSV))):
        a = adat[~adat["inverter_hiba"]].copy()
        teljes = (a["torque_request_pct"] >= TELJES_KERES_PCT) & (a["batt_current_A"] >= AKTIV_ARAM_A)
        blokk = ((a["session"] != a["session"].shift()) | (teljes != teljes.shift())
                 | (a["t_s"].diff() > 1.5 * DT_S)).cumsum()
        for _, g in a[teljes].groupby(blokk[teljes]):
            g = g[g["motor_rpm"].between(*TELJESITMENY_RPM)]
            if len(g) >= MIN_FUTAM_MINTA:
                reszek.append({"blokk": nev, "munkamenet": g["session"].iloc[0], "kezdet_s": g["t_s"].iloc[0],
                               "n": len(g), "P_atlag_kW": g["batt_power_kW"].mean(),
                               "T_inverter_C": g["inverter_temp_C"].mean(), "soc_pct": g["soc_pct"].mean()})
    tabla = pd.DataFrame(reszek)
    print("Teljes kérésű (≥ {}%) futamszakaszok {}–{} rpm között (legalább {} minta):".format(
        TELJES_KERES_PCT, *TELJESITMENY_RPM, MIN_FUTAM_MINTA))
    print(tabla.round(1).to_string(index=False))
    rho_T = stats.spearmanr(tabla["P_atlag_kW"], tabla["T_inverter_C"])
    rho_soc = stats.spearmanr(tabla["P_atlag_kW"], tabla["soc_pct"])
    delutan = tabla[tabla["blokk"].str.startswith("délután")]
    rho_du = stats.spearmanr(delutan["P_atlag_kW"], delutan["T_inverter_C"])
    print()
    print("Spearman, minden szakasz (n = {}): P–T_inverter ρ = {:.2f} (p = {:.3f}); P–SOC ρ = {:.2f} (p = {:.3f})".format(
        len(tabla), rho_T.statistic, rho_T.pvalue, rho_soc.statistic, rho_soc.pvalue))
    print("Csak délután (n = {}): P–T_inverter ρ = {:.2f} (p = {:.3f})".format(
        len(delutan), rho_du.statistic, rho_du.pvalue))
    print()
    print("Értelmezés: a teljes kérésű teljesítmény a melegebb inverterrel csökken. Ez összhangban")
    print("van a csapat által leírt védelemmel (kb. {:.0f} °C-tól arányos visszaszabályozás, {:.0f} °C-on".format(
        INVERTER_LESZABALYOZAS_T_C, INVERTER_LEKAPCSOLASI_T_C))
    print("lekapcsolás). A délelőtti és a délutáni blokk között azonban a csapat szerint az inverter")
    print("PWM-frekvenciáját is módosíthatták, ami szintén csökkentheti a leadható nyomatékot, és")
    print("a töltöttség is a nappal együtt csökkent. A három hatás ebből az adatból nem választható")
    print("szét; ehhez azonos beállítással, eltérő hőmérsékleten mért futamok kellenének.")
    return tabla


def abra_teljesitmeny_homerseklet(tabla):
    fig, ax = plt.subplots(figsize=(10, 5.4))
    for blokk, szin, jel in (("délelőtt (12:59:30)", SZIN, "o"), ("délután (tanító)", SZIN2, "s")):
        resz = tabla[tabla["blokk"] == blokk]
        ax.scatter(resz["T_inverter_C"], resz["P_atlag_kW"], s=30 + resz["n"] * 1.5, color=szin, marker=jel,
                   alpha=0.85, edgecolor="white", linewidth=0.8, label="{} (n = {})".format(blokk, len(resz)))
    ax.axvline(INVERTER_LESZABALYOZAS_T_C, color=MASODLAGOS_SZOVEG, linewidth=1, linestyle="--")
    ax.axvline(INVERTER_LEKAPCSOLASI_T_C, color=MASODLAGOS_SZOVEG, linewidth=1.4)
    ax.text(INVERTER_LESZABALYOZAS_T_C - 0.5, 2, "visszaszabályozás\nkezdete (~{:.0f} °C, bizonytalan)".format(
        INVERTER_LESZABALYOZAS_T_C), ha="right", va="bottom", fontsize=9, color=MASODLAGOS_SZOVEG)
    ax.text(INVERTER_LEKAPCSOLASI_T_C - 0.5, 2, "lekapcsolás\n({:.0f} °C)".format(INVERTER_LEKAPCSOLASI_T_C),
            ha="right", va="bottom", fontsize=9, color=MASODLAGOS_SZOVEG)
    ax.set_ylim(0, tabla["P_atlag_kW"].max() * 1.15)
    ax.legend(frameon=False, loc="upper right", fontsize=9, title="pontméret: a szakasz mintaszáma",
              title_fontsize=8.5)
    ax_formaz(ax, "Teljes kérésű akkuteljesítmény ({}–{} rpm) és inverterhőmérséklet, futamszakaszonként".format(
        *TELJESITMENY_RPM), "átlagos inverterhőmérséklet a szakaszban [°C]", "átlagos akkuteljesítmény [kW]")
    fig.tight_layout()
    abra_mentes(fig, "04_teljesitmeny_homerseklet.png")


# ---------------------------------------------------------------------------
# Ábrák
# ---------------------------------------------------------------------------

def terhelt_szakaszok(t, u, kuszob=0.05):
    """A (kezdet, vég) időszakok, ahol a bemenet > küszöb."""
    aktiv = np.r_[False, u > kuszob, False]
    valtas = np.flatnonzero(np.diff(aktiv.astype(int)))
    return [(t[a], t[min(b, len(t) - 1)]) for a, b in zip(valtas[::2], valtas[1::2])]


def abra_validacio(df, eredmeny, tabla):
    fig = plt.figure(figsize=(16, 9.2))
    racs = GridSpec(2, 4, figure=fig, height_ratios=[1, 1.05], hspace=0.45, wspace=0.28)
    fo, osszeh = eredmeny["nyomaték"], eredmeny["kérés"]
    for i, session in enumerate(df["session"].unique()):
        ax = fig.add_subplot(racs[0, i])
        g = df[df["session"] == session]
        t = g["t_s"].to_numpy()
        for a, b in terhelt_szakaszok(t, fo["u"].loc[g.index].to_numpy()):
            ax.axvspan(a, b, color=HALVANY_SZIN, alpha=0.3, linewidth=0)
        hiba = g[g["inverter_hiba"]]
        if not hiba.empty:
            ax.axvspan(hiba["t_s"].iloc[0], hiba["t_s"].iloc[-1], facecolor="none",
                       edgecolor=MASODLAGOS_SZOVEG, hatch="///", linewidth=0, alpha=0.35)
        ax.plot(t, g["inverter_temp_C"], color=SZIN, linewidth=1.6, label="mért")
        ax.plot(t, fo["loso"][session]["sim"], color=SZIN2, linewidth=2, linestyle="--",
                label="nyomaték-modell (fő)")
        ax.plot(t, osszeh["loso"][session]["sim"], color=MASODLAGOS_SZOVEG, linewidth=1.1,
                linestyle=":", label="kérés-modell (összehasonlítás)")
        ax_formaz(ax, "{}  ·  RMSE {} °C".format(session, ezres(fo["loso"][session]["rmse"], 1)),
                  "idő [s]", "inverterhőmérséklet [°C]" if i == 0 else "")
        if i == 0:
            ax.fill_between([], [], color=HALVANY_SZIN, alpha=0.3, label="nyomatékleadás")
            ax.fill_between([], [], facecolor="none", edgecolor=MASODLAGOS_SZOVEG, hatch="///",
                            linewidth=0, label="inverterhiba (csak hűlés)")
            kezelok, feliratok = ax.get_legend_handles_labels()
            fig.legend(kezelok, feliratok, loc="upper right", ncol=5, frameon=False, fontsize=9.5)

    ax = fig.add_subplot(racs[1, 0:2])
    mind = pd.concat([fo["futamok"][["dT_mert", "dT_josolt"]], osszeh["futamok"][["dT_josolt"]]])
    hatar = [mind.min().min() - 1, mind.max().max() + 1]
    ax.plot(hatar, hatar, color=MASODLAGOS_SZOVEG, linewidth=1, linestyle=":", label="tökéletes előrejelzés")
    for modell, jel in (("kérés", {"facecolor": "none", "edgecolor": MASODLAGOS_SZOVEG, "s": 45}),
                        ("nyomaték", {"color": SZIN2, "edgecolor": "white", "s": 60})):
        f = eredmeny[modell]["futamok"]
        r = stats.pearsonr(f["dT_mert"], f["dT_josolt"]).statistic
        ax.scatter(f["dT_josolt"], f["dT_mert"], linewidth=1.2, zorder=3,
                   label="{} (r = {})".format(MODELLEK[modell]["nev"], ezres(r, 2)), **jel)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax_formaz(ax, "Futamonkénti melegedés: jósolt vs. mért (n = {} futam)".format(len(fo["futamok"])),
              "jósolt melegedés [°C]", "mért melegedés [°C]")

    ax = fig.add_subplot(racs[1, 2:4])
    x = np.arange(len(tabla))
    szel = 0.27
    ax.bar(x - szel, tabla["RMSE alapmodell"], szel, color=HALVANY_SZIN,
           label="alapmodell: változatlan hőmérséklet")
    ax.bar(x, tabla["RMSE kérés-modell"], szel, color=MASODLAGOS_SZOVEG, label="kérés-modell")
    ax.bar(x + szel, tabla["RMSE nyomaték-modell"], szel, color=SZIN2, label="nyomaték-modell (fő)")
    ax.set_xticks(x)
    ax.set_xticklabels(tabla["kihagyott munkamenet"])
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax_formaz(ax, "Hiba a kihagyott munkameneten (leave-one-session-out)", "kihagyott munkamenet",
              "RMSE [°C]", racs="y")
    fig.suptitle("Inverter-hőmodell validációja: dT/dt = α·u − β·(T − T∞)", x=0.01, y=0.995,
                 ha="left", fontsize=13)
    abra_mentes(fig, "04_homodell_validacio.png")


def abra_forgatokonyvek(p, atvaltas, max_T, max_futam_s):
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(19, 5.6),
                                        gridspec_kw={"width_ratios": [1.15, 1, 0.9]})
    t = np.arange(0, 120.05, 0.1)
    nyomatek = 150
    for ido, szin in zip([4, 10, 20], [SZIN, SZIN2, SZIN3]):
        u = (t < ido) * nyomatek / NYOMATEK_EGYSEG_NM
        T = szimulacio(p, t, u, PELDA_T0)
        felirat = "{} Nm {} s-ig (csúcs: {} °C)".format(nyomatek, ido, ezres(T.max(), 1))
        atlepes = np.flatnonzero(T >= INVERTER_LEKAPCSOLASI_T_C)
        if atlepes.size:
            i = atlepes[0]
            ax1.plot(t[i], T[i], marker="X", markersize=11, color=szin, markeredgecolor="white", zorder=4)
            felirat = "{} Nm {} s-ig: {} s-nál eléri a {:.0f} °C-ot (X) -> lekapcsolna".format(
                nyomatek, ido, ezres(t[i], 1), INVERTER_LEKAPCSOLASI_T_C)
        ax1.plot(t, T, color=szin, linewidth=2, label=felirat)
    ax1.axhline(INVERTER_LEKAPCSOLASI_T_C, color=MASODLAGOS_SZOVEG, linewidth=1.4)
    ax1.text(118, INVERTER_LEKAPCSOLASI_T_C + 0.6, "lekapcsolás: {:.0f} °C (felette a modell már nem érvényes)"
             .format(INVERTER_LEKAPCSOLASI_T_C), ha="right", va="bottom", fontsize=8.5, color=MASODLAGOS_SZOVEG)
    ax1.axhline(INVERTER_LESZABALYOZAS_T_C, color=MASODLAGOS_SZOVEG, linewidth=1, linestyle="--")
    ax1.text(118, INVERTER_LESZABALYOZAS_T_C + 0.6, "nyomaték-visszaszabályozás kezdete: ~{:.0f} °C".format(
        INVERTER_LESZABALYOZAS_T_C), ha="right", va="bottom", fontsize=8.5, color=MASODLAGOS_SZOVEG)
    ax1.legend(frameon=False, fontsize=9, loc="lower left")
    ax_formaz(ax1, "Hőmérséklet-lefutás {} °C-ról (melegedés, majd hűlés)".format(PELDA_T0),
              "idő [s]", "inverterhőmérséklet [°C]")

    idok = np.linspace(0, 30, 121)
    szinek = plt.get_cmap("Blues")(np.linspace(0.45, 1.0, len(FORGATOKONYV_NYOMATEK_NM)))
    for nyom, szin in zip(FORGATOKONYV_NYOMATEK_NM, szinek):
        melegedes = analitikus(p, PELDA_T0, nyom / NYOMATEK_EGYSEG_NM, idok) - PELDA_T0
        ax2.plot(idok, melegedes, color=szin, linewidth=2.2)
        ax2.text(idok[-1] + 0.4, melegedes[-1], "{} Nm".format(nyom), va="center", fontsize=9.5,
                 color=SZOVEG_SZIN)
    ax2.axhline(0, color=MASODLAGOS_SZOVEG, linewidth=0.8)
    ax2.axvspan(max_futam_s, 35, color=HALVANY_SZIN, alpha=0.25, linewidth=0)
    ax2.set_xlim(0, 35)
    ax_formaz(ax2, "Melegedés az állandó nyomaték időtartama alatt ({} °C-ról)\n"
              "szürke sáv: extrapoláció (> {} s, a leghosszabb mért futam)".format(
                  PELDA_T0, ezres(max_futam_s, 1)),
              "a terhelés időtartama [s]", "melegedés [°C]")

    y = np.arange(len(atvaltas))
    ax3.barh(y, atvaltas["melegedes_C"], color=SZIN2, height=0.6)
    for i, (_, sor) in enumerate(atvaltas.iterrows()):
        ax3.text(sor["melegedes_C"] + 0.1, i, "+{} °C  ({} Nm)".format(
            ezres(sor["melegedes_C"], 1), ezres(sor["nyomatek_median_Nm"])), va="center", fontsize=9,
            color=SZOVEG_SZIN)
    ax3.set_yticks(y)
    ax3.set_yticklabels(atvaltas.index)
    ax3.invert_yaxis()
    ax3.set_xlim(0, atvaltas["melegedes_C"].max() * 1.6)
    ax_formaz(ax3, "100%-os kérés {} s-ig, {} °C-ról:\nmelegedés fordulatszám szerint".format(
        PELDA_IDO_S, PELDA_T0), "melegedés [°C]", "fordulatszám-sáv [rpm]", racs="x")
    fig.suptitle("Előrejelzés (fő modell: tényleges nyomaték): mennyivel melegszik az inverter?",
                 x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    abra_mentes(fig, "04_homodell_forgatokonyvek.png")


# ---------------------------------------------------------------------------
# Főprogram
# ---------------------------------------------------------------------------

def main():
    pd.set_option("display.width", 170)
    df = beolvas()
    print("Beolvasva: {} sor, {} oszlop (az inverterhiba-szakaszok hűlési adatként bent maradnak)".format(
        *df.shape))

    eredmeny = modellek_illesztese(df)
    tabla = eredmenyek_kiirasa(df, eredmeny)
    elorejelzes = forgatokonyvek(df, eredmeny)
    elorejelzes.to_csv(ELOREJELZES_CSV, sep=";", index=False, encoding="utf-8")
    atvaltas = keres_atvaltasa(df, eredmeny["nyomaték"]["p"])
    ido_a_lekapcsolasig(eredmeny["nyomaték"]["p"], eredmeny["nyomaték"]["max_futam_s"])
    teljesitmeny = teljesitmeny_homerseklet(df)

    abra_validacio(df, eredmeny, tabla)
    abra_forgatokonyvek(eredmeny["nyomaték"]["p"], atvaltas, df["inverter_temp_C"].max(),
                        eredmeny["nyomaték"]["max_futam_s"])
    abra_teljesitmeny_homerseklet(teljesitmeny)
    print()
    print("Előrejelzési táblázat mentve: {}".format(ELOREJELZES_CSV))
    plt.show()


if __name__ == "__main__":
    main()
