# -*- coding: utf-8 -*-
"""5. Klaszterezés: a hajtáslánc üzemállapotai (K-közép és fuzzy C-means).

Bemenet: 01_hajtaslanc_tisztitott.csv      – tanító adat (a nap utolsó menetblokkja)
         01_hajtaslanc_uj_tisztitott.csv   – új, a modellezésben nem használt mérés
                                              (12:59:30, délelőtti futamok)
Kimenet: 05_klaszterek.csv – minden sor klasztercímkéje (mindkét modell) és a C-means
         tagsági fokai, a tanító és az új adatra is
         05_k_valasztas.png, 05_klaszter_profilok.png, 05_klaszterek_pca.png,
         05_idosor_klaszterek.png, 05_uj_adat.png

Sorok: a működő hajtáslánc mozgó sorai (inverter_hiba = False és v ≥ 1 km/h). Az álló
sorok triviálisan külön csoportot alkotnának, ezért kimaradnak.
Változók (standardizálva, a tanító adat átlagával és szórásával):
    torque_request_pct  – mit kér a pilóta
    batt_power_kW       – mit ad le a hajtáslánc
    speed_kmh           – sebesség
    accel_ms2           – gyorsulás
A redundáns párok másik tagja kimarad (fordulatszám ~ sebesség, áram ~ teljesítmény,
pedál ~ kérés), a hőmérsékletek is (a munkamenet zavaró hatását hoznák be).

Két módszer:
  K-közép (K-means): éles besorolás, minden pont pontosan egy klaszterbe tartozik.
  Fuzzy C-means (FCM, m = 2): minden pont tagsági fokkal tartozik minden klaszterhez
      (a fokok összege 1). Így az állapotok közötti fokozatos átmenetek is láthatók.
Mindkettő középpont-alapú, ezért új adatra is alkalmazható (legközelebbi középpont,
illetve tagsági fok a meglévő középpontokhoz).
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
import skfuzzy as fuzz
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score,
                             silhouette_score)
from sklearn.preprocessing import StandardScaler

import os as _os
import sys as _sys
# a közös modul (hajtaslanc_kozos.py) a szülőmappában, a Beadando mappában van
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from hajtaslanc_kozos import (MAPPA, TISZTITOTT_CSV, SZIN, SZIN2, SZOVEG_SZIN, MASODLAGOS_SZOVEG,
                              beolvas, cim, ax_formaz, abra_mentes, ezres)

UJ_CSV = os.path.join(MAPPA, "01_hajtaslanc_uj_tisztitott.csv")
KLASZTEREK_CSV = os.path.join(MAPPA, "05_klaszterek.csv")

JELLEMZOK = ["torque_request_pct", "batt_power_kW", "speed_kmh", "accel_ms2"]
LEIRO_VALTOZOK = JELLEMZOK + ["apps_pct", "batt_current_A", "motor_rpm", "torque_est_Nm",
                              "inverter_temp_C"]
MIN_SEBESSEG_KMH = 1.0
K = 4                        # választott klaszterszám (indoklás: k_valasztas())
K_TARTOMANY = range(2, 9)
FCM_M = 2.0                  # fuzzy kitevő (a szokásos érték)
FCM_HIBA = 1e-5
FCM_MAX_ITER = 1000
SEED = 42
BIZONYTALAN_TAGSAG = 0.6     # ha a legnagyobb tagsági fok ez alatt van: átmeneti pont

# Fix sorrend és színek (validált négyes, minden párra; a sárga és a magenta kontrasztja
# alacsony, ezért mindig felirat / jelmagyarázat kíséri).
NEVEK = ["Gyorsítás", "Nagy sebesség (teljesítménykorlát)", "Gázelvétel, lassítás", "Lassú menet"]
ROVID = {"Gyorsítás": "gyorsitas", "Nagy sebesség (teljesítménykorlát)": "nagy_sebesseg",
         "Gázelvétel, lassítás": "lassitas", "Lassú menet": "lassu_menet"}
SZINEK = {"Gyorsítás": "#2a78d6", "Nagy sebesség (teljesítménykorlát)": "#008300",
          "Gázelvétel, lassítás": "#e87ba4", "Lassú menet": "#eda100"}
IDOSOR_MUNKAMENETEK = ["15:23:21", "15:39:36"]


# ---------------------------------------------------------------------------
# Adatok
# ---------------------------------------------------------------------------

def mozgo_sorok(df):
    return df[~df["inverter_hiba"] & (df["speed_kmh"] >= MIN_SEBESSEG_KMH)].copy()


def adatok():
    cim("Adatok")
    tanito_teljes = beolvas(TISZTITOTT_CSV)
    uj_teljes = beolvas(UJ_CSV)
    tanito, uj = mozgo_sorok(tanito_teljes), mozgo_sorok(uj_teljes)
    for nev, teljes, resz in (("tanító", tanito_teljes, tanito), ("új (12:59:30)", uj_teljes, uj)):
        print("{:14s} {} sor -> inverterhiba nélkül és mozgásban (v ≥ {} km/h): {} sor".format(
            nev + ":", len(teljes), ezres(MIN_SEBESSEG_KMH), len(resz)))
    print()
    print("Jellemzők: {}".format(", ".join(JELLEMZOK)))
    print(tanito[JELLEMZOK].describe().T[["mean", "std", "min", "max"]].round(2).to_string())
    print()
    print("A változók skálája nagyon eltérő (pl. a sebesség szórása ~{:.0f} km/h, a gyorsulásé ~{:.1f} m/s²),".format(
        tanito["speed_kmh"].std(), tanito["accel_ms2"].std()))
    print("ezért standardizálunk: z = (x − átlag) / szórás, a tanító adat paramétereivel. Az új")
    print("adatot ugyanezekkel a paraméterekkel transzformáljuk.")
    # az ábrák görbéihez a teljes (álló sorokat is tartalmazó) működő idősor kell
    return tanito, uj, tanito_teljes[~tanito_teljes["inverter_hiba"]], uj_teljes[~uj_teljes["inverter_hiba"]]


# ---------------------------------------------------------------------------
# Modellek
# ---------------------------------------------------------------------------

def kmeans_illesztes(X, k):
    return KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(X)


def fcm_illesztes(X, k):
    kozeppont, tagsag, _, _, _, _, fpc = fuzz.cluster.cmeans(
        X.T, k, FCM_M, error=FCM_HIBA, maxiter=FCM_MAX_ITER, seed=SEED)
    return kozeppont, tagsag, fpc


def fcm_josol(X, kozeppont):
    tagsag, *_ = fuzz.cluster.cmeans_predict(X.T, kozeppont, FCM_M, error=FCM_HIBA,
                                             maxiter=FCM_MAX_ITER, seed=SEED)
    return tagsag


def k_valasztas(X, skalazo):
    cim("A klaszterszám megválasztása (k = {}…{})".format(K_TARTOMANY.start, K_TARTOMANY.stop - 1))
    sorok = []
    for k in K_TARTOMANY:
        km = kmeans_illesztes(X, k)
        _, tagsag, fpc = fcm_illesztes(X, k)
        fcm_cimke = tagsag.argmax(axis=0)
        sorok.append({"k": k, "inercia": km.inertia_,
                      "sziluett K-közép": silhouette_score(X, km.labels_),
                      "sziluett C-means": silhouette_score(X, fcm_cimke),
                      "Davies–Bouldin K-közép": davies_bouldin_score(X, km.labels_),
                      "Davies–Bouldin C-means": davies_bouldin_score(X, fcm_cimke),
                      "FPC": fpc, "ARI (egyezés)": adjusted_rand_score(km.labels_, fcm_cimke)})
    tabla = pd.DataFrame(sorok)
    print(tabla.round(3).to_string(index=False))
    print()
    print("Mutatók: inercia = klaszteren belüli négyzetösszeg (könyök-módszer); sziluett: −1…1,")
    print("nagyobb a jobb; Davies–Bouldin: kisebb a jobb; FPC (fuzzy partíciós együttható): 1/k…1,")
    print("1 = éles felosztás; ARI: a két módszer besorolásának egyezése (1 = azonos).")
    legjobb = tabla.loc[tabla["sziluett K-közép"].idxmax()]
    km3 = kmeans_illesztes(X, 3)
    profil3 = pd.DataFrame(skalazo.inverse_transform(km3.cluster_centers_), columns=JELLEMZOK)
    profil3["n"] = np.bincount(km3.labels_)
    print()
    print("Összehasonlításként a k = 3-as K-közép középpontjai (eredeti mértékegységben):")
    print(profil3.round(1).to_string())
    k6 = tabla.loc[tabla["k"] == 6, "ARI (egyezés)"].iloc[0]
    print()
    print("Választás: k = {}.".format(K))
    print("- A K-közép sziluettje k = {:.0f}-nál a legnagyobb ({:.3f}), k = {}-nél {:.3f}. A különbség kicsi,".format(
        legjobb["k"], legjobb["sziluett K-közép"], K,
        tabla.loc[tabla["k"] == K, "sziluett K-közép"].iloc[0]))
    print("  és a mutató k = 4 felett már alig változik, így önmagában nem dönt.")
    print("- Az inercia csökkenése k = 4 után lassul (könyök).")
    print("- k = 4-nél a két módszer még erősen egyezik (ARI {:.2f}); k = 6-nál ez {:.2f}-re esik,".format(
        tabla.loc[tabla["k"] == K, "ARI (egyezés)"].iloc[0], k6))
    print("  a felosztás instabillá válik.")
    print("- k = 4 négy fizikailag egyértelmű üzemállapotot ad (lásd a profilokat). k = 3-nál (fent)")
    print("  a nagy kérésű pontok egyetlen klaszterbe kerülnek, így a gyorsítás és a teljesítmény-")
    print("  korlátos nagy sebességű szakasz összeolvad, pedig a kettő fizikailag eltérő állapot.")
    return tabla


def klaszter_nevek(kozeppont_eredeti):
    """Klaszterindex -> név a középpontok fizikai értékei alapján (címkepermutációtól független)."""
    kp = kozeppont_eredeti.copy()
    nevek = {}
    lassu = kp["speed_kmh"].idxmin()
    nevek[lassu] = "Lassú menet"
    maradek = kp.drop(index=lassu)
    lassitas = maradek["torque_request_pct"].idxmin()
    nevek[lassitas] = "Gázelvétel, lassítás"
    maradek = maradek.drop(index=lassitas)
    gyorsitas = maradek["accel_ms2"].idxmax()
    nevek[gyorsitas] = "Gyorsítás"
    nevek[maradek.drop(index=gyorsitas).index[0]] = "Nagy sebesség (teljesítménykorlát)"
    return nevek


def modellek(tanito, uj):
    skalazo = StandardScaler().fit(tanito[JELLEMZOK])
    X, X_uj = skalazo.transform(tanito[JELLEMZOK]), skalazo.transform(uj[JELLEMZOK])
    tabla_k = k_valasztas(X, skalazo)

    km = kmeans_illesztes(X, K)
    km_kp = pd.DataFrame(skalazo.inverse_transform(km.cluster_centers_), columns=JELLEMZOK)
    km_nevek = klaszter_nevek(km_kp)
    fcm_kp, tagsag, fpc = fcm_illesztes(X, K)
    fcm_kp_eredeti = pd.DataFrame(skalazo.inverse_transform(fcm_kp), columns=JELLEMZOK)
    fcm_nevek = klaszter_nevek(fcm_kp_eredeti)
    fcm_sorrend = [next(i for i, n in fcm_nevek.items() if n == nev) for nev in NEVEK]

    for adat, XX, tag in ((tanito, X, tagsag), (uj, X_uj, fcm_josol(X_uj, fcm_kp))):
        adat["kmeans_klaszter"] = [km_nevek[c] for c in km.predict(XX)]
        tag = tag[fcm_sorrend]                       # sorok a NEVEK sorrendjében
        for i, nev in enumerate(NEVEK):
            adat["fcm_" + ROVID[nev]] = tag[i]
        adat["fcm_klaszter"] = [NEVEK[i] for i in tag.argmax(axis=0)]
        adat["fcm_tagsag_max"] = tag.max(axis=0)
        adat["fcm_bizonytalan"] = adat["fcm_tagsag_max"] < BIZONYTALAN_TAGSAG
    return {"X": X, "X_uj": X_uj, "skalazo": skalazo, "km": km, "fpc": fpc, "tabla_k": tabla_k,
            "km_kp": km_kp.rename(index=km_nevek), "fcm_kp": fcm_kp_eredeti.rename(index=fcm_nevek)}


# ---------------------------------------------------------------------------
# Értékelés
# ---------------------------------------------------------------------------

def ertekeles(tanito, m):
    cim("A két modell értékelése (k = {})".format(K))
    X = m["X"]
    sorok = []
    for nev, oszlop in (("K-közép", "kmeans_klaszter"), ("fuzzy C-means", "fcm_klaszter")):
        cimke = tanito[oszlop].map({n: i for i, n in enumerate(NEVEK)}).to_numpy()
        sorok.append({"modell": nev, "sziluett": silhouette_score(X, cimke),
                      "Davies–Bouldin": davies_bouldin_score(X, cimke),
                      "Calinski–Harabasz": calinski_harabasz_score(X, cimke)})
    tabla = pd.DataFrame(sorok)
    print(tabla.round(3).to_string(index=False))
    ari = adjusted_rand_score(tanito["kmeans_klaszter"], tanito["fcm_klaszter"])
    egyezes = (tanito["kmeans_klaszter"] == tanito["fcm_klaszter"]).mean()
    print()
    print("A két besorolás egyezése: ARI = {:.3f}; a sorok {:.1%}-a ugyanabba a klaszterbe kerül.".format(
        ari, egyezes))
    print()
    print("Kereszttábla (sor: K-közép, oszlop: C-means legnagyobb tagsági foka):")
    print(pd.crosstab(tanito["kmeans_klaszter"], tanito["fcm_klaszter"]).reindex(
        index=NEVEK, columns=NEVEK).fillna(0).astype(int).to_string())

    bizonytalan = tanito["fcm_bizonytalan"]
    print()
    print("C-means: FPC = {:.3f} (k = {}-nél a lehetséges tartomány {:.2f}…1).".format(m["fpc"], K, 1 / K))
    print("Átmeneti pontok (legnagyobb tagsági fok < {}): {} sor ({:.1%}).".format(
        BIZONYTALAN_TAGSAG, bizonytalan.sum(), bizonytalan.mean()))
    eltero = tanito["kmeans_klaszter"] != tanito["fcm_klaszter"]
    print("Ahol a két modell eltér, ott a C-means átlagos legnagyobb tagsági foka {:.2f}".format(
        tanito.loc[eltero, "fcm_tagsag_max"].mean()))
    print("(az egyezőknél {:.2f}): az eltérések szinte mind átmeneti pontokon vannak.".format(
        tanito.loc[~eltero, "fcm_tagsag_max"].mean()))
    return tabla, ari


def profilok(tanito):
    cim("Klaszterprofilok (átlagok eredeti mértékegységben)")
    for nev, oszlop in (("K-közép", "kmeans_klaszter"), ("fuzzy C-means", "fcm_klaszter")):
        print()
        print(nev + ":")
        p = tanito.groupby(oszlop)[LEIRO_VALTOZOK].mean().reindex(NEVEK)
        p.insert(0, "n", tanito[oszlop].value_counts().reindex(NEVEK))
        p.insert(1, "arány %", (100 * p["n"] / len(tanito)).round(1))
        print(p.round(1).to_string())
    print()
    print("Értelmezés (C-means):")
    p = tanito.groupby("fcm_klaszter")[LEIRO_VALTOZOK].mean()
    leiras = {
        "Gyorsítás": "nagy kérés, pozitív gyorsulás, közepes sebesség; itt a legnagyobb a nyomaték",
        "Nagy sebesség (teljesítménykorlát)": "nagy kérés, nagy sebesség, kis gyorsulás: a hajtáslánc "
                                              "a teljesítménykorláton fut, a nyomaték már kisebb",
        "Gázelvétel, lassítás": "kis kérés, nagy sebességről negatív gyorsulás (gurulás, fékezés)",
        "Lassú menet": "kis kérés és teljesítmény, alacsony sebesség (manőverezés, lassú indulás)",
    }
    for nev in NEVEK:
        print("- {}: {} (kérés {:.0f}%, {:.0f} km/h, {:+.1f} m/s², {:.0f} Nm, {:.1f} kW).".format(
            nev, leiras[nev], p.loc[nev, "torque_request_pct"], p.loc[nev, "speed_kmh"],
            p.loc[nev, "accel_ms2"], p.loc[nev, "torque_est_Nm"], p.loc[nev, "batt_power_kW"]))


def uj_adat(tanito, uj):
    cim("A választott modell (fuzzy C-means) alkalmazása új adaton: 12:59:30")
    print("A délelőtti mérés két teljes gázas gyorsítást tartalmaz ~80 km/h-ig; a modell nem")
    print("látta. A tanító adat skálázójával transzformálva a C-means a meglévő középpontokhoz")
    print("számol tagsági fokot (cmeans_predict), a K-közép a legközelebbi középpontot adja.")
    print()
    tabla = pd.DataFrame({
        "tanító (%)": 100 * tanito["fcm_klaszter"].value_counts(normalize=True),
        "új adat (%)": 100 * uj["fcm_klaszter"].value_counts(normalize=True),
    }).reindex(NEVEK).fillna(0)
    tabla["új adat (sor)"] = uj["fcm_klaszter"].value_counts().reindex(NEVEK).fillna(0).astype(int)
    print(tabla.round(1).to_string())
    print()
    print("Új adat: átmeneti pontok aránya {:.1%}; K-közép és C-means egyezése {:.1%}.".format(
        uj["fcm_bizonytalan"].mean(), (uj["kmeans_klaszter"] == uj["fcm_klaszter"]).mean()))
    print()
    print("Az új mérés klaszterenkénti átlagai:")
    p = uj.groupby("fcm_klaszter")[LEIRO_VALTOZOK].mean().reindex(NEVEK)
    p.insert(0, "n", uj["fcm_klaszter"].value_counts().reindex(NEVEK))
    print(p.round(1).to_string())
    print()
    osszevetes = pd.DataFrame({
        "P tanító [kW]": tanito.groupby("fcm_klaszter")["batt_power_kW"].mean(),
        "P új [kW]": uj.groupby("fcm_klaszter")["batt_power_kW"].mean(),
        "T_inv tanító [°C]": tanito.groupby("fcm_klaszter")["inverter_temp_C"].mean(),
        "T_inv új [°C]": uj.groupby("fcm_klaszter")["inverter_temp_C"].mean(),
    }).reindex(NEVEK)
    print("Teljesítmény és inverterhőmérséklet klaszterenként, tanító vs. új adat:")
    print(osszevetes.round(1).to_string())
    nagy = "Nagy sebesség (teljesítménykorlát)"
    print("Az új mérésben a(z) '{}' klaszter átlagos teljesítménye {:.1f} kW, szemben".format(
        nagy, osszevetes.loc[nagy, "P új [kW]"]))
    print("a tanító adat {:.1f} kW-jával, miközben az inverter {:.0f} °C-kal hidegebb. A délelőtti".format(
        osszevetes.loc[nagy, "P tanító [kW]"],
        osszevetes.loc[nagy, "T_inv tanító [°C]"] - osszevetes.loc[nagy, "T_inv új [°C]"]))
    print("futamokban tehát nem volt meg a délutáni ~20–25 kW-os teljesítménykorlát. A besorolást")
    print("a kérés, a sebesség és a gyorsulás mintázata így is helyesen adja, de a klaszter neve")
    print("('teljesítménykorlát') a délutáni állapotot írja le.")
    print()
    print("Futamonként (a kérés > 5%-os összefüggő szakaszok) a C-means klasztersorrendje:")
    akt = uj["torque_request_pct"] > 5
    blokk = ((akt != akt.shift()) | (uj["t_s"].diff() > 0.15)).cumsum()
    for _, g in uj[akt].groupby(blokk[akt]):
        if len(g) < 20:
            continue
        sorrend = g["fcm_klaszter"].loc[g["fcm_klaszter"] != g["fcm_klaszter"].shift()].tolist()
        print("  t = {}–{} s, v_max {} km/h: {}".format(
            ezres(g["t_s"].iloc[0], 1), ezres(g["t_s"].iloc[-1], 1), ezres(g["speed_kmh"].max(), 1),
            " -> ".join(sorrend)))
    return tabla


# ---------------------------------------------------------------------------
# Ábrák
# ---------------------------------------------------------------------------

def abra_k_valasztas(tabla_k):
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 4.8))
    ax1.plot(tabla_k["k"], tabla_k["inercia"], color=SZIN, marker="o", linewidth=2)
    ax_formaz(ax1, "K-közép: inercia (könyök-módszer)", "klaszterszám (k)", "klaszteren belüli négyzetösszeg")
    ax2.plot(tabla_k["k"], tabla_k["sziluett K-közép"], color=SZIN, marker="o", linewidth=2, label="K-közép")
    ax2.plot(tabla_k["k"], tabla_k["sziluett C-means"], color=SZIN2, marker="s", linewidth=2,
             linestyle="--", label="fuzzy C-means")
    ax2.legend(frameon=False)
    ax_formaz(ax2, "Sziluett-mutató (nagyobb a jobb)", "klaszterszám (k)", "sziluett")
    ax3.plot(tabla_k["k"], tabla_k["FPC"], color=SZIN2, marker="s", linewidth=2,
             label="FPC (C-means éles­sége)")
    ax3.plot(tabla_k["k"], tabla_k["ARI (egyezés)"], color=MASODLAGOS_SZOVEG, marker="o", linewidth=2,
             label="ARI (a két módszer egyezése)")
    ax3.set_ylim(0, 1.02)
    ax3.legend(frameon=False, loc="lower left")
    ax_formaz(ax3, "C-means élessége és a módszerek egyezése", "klaszterszám (k)", "érték (0…1)")
    for ax in (ax1, ax2, ax3):
        ax.axvline(K, color=MASODLAGOS_SZOVEG, linewidth=1, linestyle=":")
        ax.set_xticks(list(K_TARTOMANY))
    ax1.text(K + 0.1, ax1.get_ylim()[1] * 0.97, "választott k = {}".format(K), va="top", fontsize=9,
             color=MASODLAGOS_SZOVEG)
    fig.suptitle("A klaszterszám megválasztása", x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    abra_mentes(fig, "05_k_valasztas.png")


def abra_profilok(tanito):
    fig, axes = plt.subplots(1, 2, figsize=(17, 5.4), sharey=True)
    atlag, szoras = tanito[LEIRO_VALTOZOK].mean(), tanito[LEIRO_VALTOZOK].std()
    for ax, (cim_szoveg, oszlop) in zip(axes, (("K-közép", "kmeans_klaszter"),
                                               ("fuzzy C-means (legnagyobb tagsági fok)", "fcm_klaszter"))):
        p = tanito.groupby(oszlop)[LEIRO_VALTOZOK].mean().reindex(NEVEK)
        z = (p - atlag) / szoras
        kep = ax.imshow(z.to_numpy(), cmap="RdBu_r", vmin=-1.6, vmax=1.6, aspect="auto")
        for i in range(z.shape[0]):
            for j in range(z.shape[1]):
                ax.text(j, i, ezres(p.iat[i, j], 1 if abs(p.iat[i, j]) < 10 else 0), ha="center",
                        va="center", fontsize=8.5,
                        color="white" if abs(z.iat[i, j]) > 1.0 else SZOVEG_SZIN)
        ax.set_xticks(range(len(LEIRO_VALTOZOK)))
        ax.set_xticklabels(LEIRO_VALTOZOK, rotation=35, ha="right", fontsize=9)
        for oldal in ax.spines.values():
            oldal.set_visible(False)
        ax.tick_params(length=0)
        ax.set_title(cim_szoveg, loc="left", fontsize=11)
    axes[0].set_yticks(range(len(NEVEK)))
    axes[0].set_yticklabels(["{}\nn = {} / {}".format(n, (tanito["kmeans_klaszter"] == n).sum(),
                                                       (tanito["fcm_klaszter"] == n).sum()) for n in NEVEK],
                            fontsize=9)
    fig.subplots_adjust(left=0.15, right=0.88, bottom=0.27, top=0.85, wspace=0.06)
    savszin = fig.add_axes([0.9, 0.27, 0.012, 0.58])
    fig.colorbar(kep, cax=savszin, label="eltérés az átlagtól\n(szórásegységben)")
    fig.suptitle("Klaszterprofilok: átlagok eredeti mértékegységben, színezés a standardizált eltérés "
                 "szerint (n = K-közép / C-means)", x=0.01, ha="left", fontsize=12)
    abra_mentes(fig, "05_klaszter_profilok.png")


def abra_pca(tanito, m):
    pca = PCA(n_components=2).fit(m["X"])
    pont = pca.transform(m["X"])
    arany = pca.explained_variance_ratio_
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharex=True, sharey=True)
    for ax, (cim_szoveg, oszlop, attetszo) in zip(axes, (
            ("K-közép: éles besorolás", "kmeans_klaszter", False),
            ("Fuzzy C-means: halványabb = kisebb tagsági fok (átmeneti pont)", "fcm_klaszter", True))):
        for nev in NEVEK:
            maszk = (tanito[oszlop] == nev).to_numpy()
            alfa = (0.15 + 0.85 * (tanito.loc[maszk, "fcm_tagsag_max"].to_numpy() - 0.25) / 0.75).clip(0.1, 1) \
                if attetszo else 0.7
            ax.scatter(pont[maszk, 0], pont[maszk, 1], s=14, color=SZINEK[nev], alpha=alfa,
                       edgecolor="none", label="{} (n = {})".format(nev, maszk.sum()))
        ax_formaz(ax, cim_szoveg, "PC1 ({:.0%})".format(arany[0]), "PC2 ({:.0%})".format(arany[1]))
    kezelok = [Patch(color=SZINEK[n], label=n) for n in NEVEK]
    fig.legend(handles=kezelok, loc="upper right", ncol=4, frameon=False, fontsize=10)
    fig.suptitle("A klaszterek a két első főkomponens síkjában", x=0.01, ha="left", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    abra_mentes(fig, "05_klaszterek_pca.png")


def idosor_panel(ax_seb, ax_tag, g, teljes, cim_szoveg, xlabel=True):
    """Felül: sebesség és kérés (teljes idősor), háttér a C-means klaszter szerint;
    alul: tagsági fokok. A klaszterezésből kimaradt (álló) sorok háttere fehér."""
    t = g["t_s"].to_numpy()
    blokk = ((g["fcm_klaszter"] != g["fcm_klaszter"].shift()) | (g["t_s"].diff() > 0.15)).cumsum()
    for _, b in g.groupby(blokk):
        ax_seb.axvspan(b["t_s"].iloc[0] - 0.05, b["t_s"].iloc[-1] + 0.05,
                       color=SZINEK[b["fcm_klaszter"].iloc[0]], alpha=0.35, linewidth=0)
    ax_seb.plot(teljes["t_s"], teljes["speed_kmh"], color=SZOVEG_SZIN, linewidth=1.6, label="sebesség [km/h]")
    ax_seb.plot(teljes["t_s"], teljes["torque_request_pct"], color=MASODLAGOS_SZOVEG, linewidth=1,
                linestyle=":", label="nyomatékkérés [%]")
    ax_seb.set_ylim(0, 105)
    ax_formaz(ax_seb, cim_szoveg, "", "km/h  ·  %")
    also = np.zeros(len(g))
    for nev in NEVEK:
        ertek = g["fcm_" + ROVID[nev]].to_numpy()
        ax_tag.bar(t, ertek, bottom=also, width=0.1, color=SZINEK[nev], linewidth=0)
        also += ertek
    ax_tag.axhline(BIZONYTALAN_TAGSAG, color=SZOVEG_SZIN, linewidth=0.8, linestyle="--")
    ax_tag.set_ylim(0, 1)
    ax_formaz(ax_tag, "", "idő a munkamenet elejétől [s]" if xlabel else "", "tagsági fok", racs="y")


def abra_idosor(tanito, tanito_teljes):
    fig = plt.figure(figsize=(16, 9))
    racs = GridSpec(5, 1, figure=fig, height_ratios=[2.2, 1, 0.35, 2.2, 1], hspace=0.3)
    for i, session in enumerate(IDOSOR_MUNKAMENETEK):
        g = tanito[tanito["session"] == session]
        ax_seb = fig.add_subplot(racs[3 * i])
        ax_tag = fig.add_subplot(racs[3 * i + 1], sharex=ax_seb)
        idosor_panel(ax_seb, ax_tag, g, tanito_teljes[tanito_teljes["session"] == session],
                     "{} munkamenet (C-means; fehér háttér: álló sor, nincs klaszterezve)".format(session),
                     xlabel=(i == len(IDOSOR_MUNKAMENETEK) - 1))
        if i == 0:
            ax_seb.legend(frameon=False, loc="upper left", fontsize=9)
    kezelok = [Patch(color=SZINEK[n], alpha=0.6, label=n) for n in NEVEK]
    fig.legend(handles=kezelok, loc="upper right", ncol=4, frameon=False, fontsize=10)
    fig.suptitle("Üzemállapotok időben (alsó sávok: C-means tagsági fokok; szaggatott: {} határ)".format(
        ezres(BIZONYTALAN_TAGSAG, 1)), x=0.01, ha="left", fontsize=13)
    abra_mentes(fig, "05_idosor_klaszterek.png")


def abra_uj_adat(tanito, uj, uj_teljes, tabla):
    fig = plt.figure(figsize=(16, 6.8))
    racs = GridSpec(2, 2, figure=fig, height_ratios=[2.2, 1], width_ratios=[3, 1.15], hspace=0.3,
                    wspace=0.25)
    ax_seb = fig.add_subplot(racs[0, 0])
    ax_tag = fig.add_subplot(racs[1, 0], sharex=ax_seb)
    idosor_panel(ax_seb, ax_tag, uj, uj_teljes,
                 "Új adat: 12:59:30 (a modell nem látta; fehér háttér: álló sor)")
    ax_seb.legend(frameon=False, loc="upper left", fontsize=9)
    ax = fig.add_subplot(racs[:, 1])
    y = np.arange(len(NEVEK))
    ax.barh(y - 0.2, tabla["tanító (%)"], height=0.38, color=[SZINEK[n] for n in NEVEK], alpha=0.45,
            label="tanító adat")
    ax.barh(y + 0.2, tabla["új adat (%)"], height=0.38, color=[SZINEK[n] for n in NEVEK],
            label="új adat")
    for i, nev in enumerate(NEVEK):
        ax.text(tabla.loc[nev, "új adat (%)"] + 1, i + 0.2, "{}%".format(ezres(tabla.loc[nev, "új adat (%)"])),
                va="center", fontsize=9, color=SZOVEG_SZIN)
        ax.text(tabla.loc[nev, "tanító (%)"] + 1, i - 0.2, "{}%".format(ezres(tabla.loc[nev, "tanító (%)"])),
                va="center", fontsize=9, color=MASODLAGOS_SZOVEG)
    ax.set_yticks(y)
    ax.set_yticklabels(NEVEK, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, max(tabla["tanító (%)"].max(), tabla["új adat (%)"].max()) * 1.3)
    ax_formaz(ax, "Klaszterarányok\n(halvány: tanító, telt: új adat)", "sorok aránya [%]", "", racs="x")
    kezelok = [Patch(color=SZINEK[n], alpha=0.6, label=n) for n in NEVEK]
    fig.legend(handles=kezelok, loc="upper right", ncol=4, frameon=False, fontsize=10)
    fig.suptitle("A C-means modell alkalmazása új mérésen", x=0.01, ha="left", fontsize=13)
    abra_mentes(fig, "05_uj_adat.png")


# ---------------------------------------------------------------------------
# Főprogram
# ---------------------------------------------------------------------------

def main():
    pd.set_option("display.width", 190)
    tanito, uj, tanito_teljes, uj_teljes = adatok()
    m = modellek(tanito, uj)
    tabla_ertekeles, ari = ertekeles(tanito, m)
    profilok(tanito)

    cim("Melyik modell a megfelelőbb?")
    km, fcm = tabla_ertekeles.iloc[0], tabla_ertekeles.iloc[1]
    print("A két modell felosztása szinte azonos (ARI {:.2f}), a minőségi mutatók közel egyformák".format(ari))
    print("(sziluett {:.3f} vs {:.3f}; Davies–Bouldin {:.3f} vs {:.3f}). A választott modell a fuzzy".format(
        km["sziluett"], fcm["sziluett"], km["Davies–Bouldin"], fcm["Davies–Bouldin"]))
    print("C-means, mert ugyanazt a felosztást adja, de többletinformációt is hordoz: a tagsági fokok")
    print("megmutatják az állapotok közötti fokozatos átmeneteket (pl. gyorsításból a teljesítmény-")
    print("korlátos szakaszba), és az új adaton is jelzik, mennyire biztos a besorolás. Egy")
    print("folytonos fizikai folyamatnál (menet) ez valósághűbb, mint az éles határ.")

    tabla_uj = uj_adat(tanito, uj)

    kimenet = pd.concat([tanito.assign(adathalmaz="tanító"), uj.assign(adathalmaz="új (12:59:30)")])
    oszlopok = (["adathalmaz", "session", "timestamp", "t_s"] + LEIRO_VALTOZOK
                + ["kmeans_klaszter", "fcm_klaszter", "fcm_tagsag_max", "fcm_bizonytalan"]
                + ["fcm_" + ROVID[n] for n in NEVEK])
    kimenet[oszlopok].round(4).to_csv(KLASZTEREK_CSV, sep=";", index=False, encoding="utf-8")

    abra_k_valasztas(m["tabla_k"])
    abra_profilok(tanito)
    abra_pca(tanito, m)
    abra_idosor(tanito, tanito_teljes)
    abra_uj_adat(tanito, uj, uj_teljes, tabla_uj)
    print()
    print("Klasztercímkék mentve: {} ({} sor)".format(KLASZTEREK_CSV, len(kimenet)))
    plt.show()


if __name__ == "__main__":
    main()
