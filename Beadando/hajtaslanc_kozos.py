# -*- coding: utf-8 -*-
"""A beadandó elemző scriptjeinek közös segédfüggvényei.

Fájlútvonalak, beolvasás, valamint a kimenet és az ábrák egységes formázása.

Mappaszerkezet: a Beadando mappában vannak a CSV-k, a dokumentáció és ez a modul;
minden fázis (00_…, 01_…, …) kódja és ábrái a saját almappájában. A fázisscriptek a
szülőmappát a sys.path-ba téve importálják ezt a modult.
"""

import os
import sys

import numpy as np
import pandas as pd

MAPPA = os.path.dirname(os.path.abspath(__file__))     # a Beadando mappa (CSV-k helye)
# Minden script a saját sorszámával ment egy CSV-t (00_, 01_, ...).
NYERS_CSV = os.path.join(MAPPA, "00_hajtaslanc_nyers.csv")
TISZTITOTT_CSV = os.path.join(MAPPA, "01_hajtaslanc_tisztitott.csv")

SZIN = "#2a78d6"
SZIN2 = "#eb6834"
SZIN3 = "#1baf7a"
SZIN4 = "#eda100"
# Munkamenet-színek fix sorrendben (validált paletta). Az utolsó kettő kontrasztja a
# fehér háttéren 3:1 alatti, ezért mindig szöveges felirat / jelmagyarázat kíséri.
SESSION_SZINEK = {"15:21:59": SZIN, "15:23:21": SZIN2, "15:29:33": SZIN3, "15:39:36": SZIN4}
HIBA_SZIN = "#e34948"
HALVANY_SZIN = "#b5b4ad"
SZOVEG_SZIN = "#0b0b0b"
MASODLAGOS_SZOVEG = "#52514e"
RACS_SZIN = "#e5e4df"


ALFA = 0.05              # szignifikanciaszint
DT_S = 0.1               # mintavételi idő (10 Hz)

# Gyorsító futam: összefüggő szakasz, ahol a nyomatékkérés > 5%, legalább 2 s hosszú, és
# a hajtáslánc ténylegesen ad energiát (≥ 5 kJ). Az energiafeltétel kizárja az inverterhiba
# utáni szakaszokat, ahol van kérés, de az inverter ki van kapcsolva.
FUTAM_KERES_PCT = 5
FUTAM_MIN_HOSSZ_S = 2.0
FUTAM_MIN_ENERGIA_KJ = 5.0


# Inverterhiba (lekapcsolás): a motor forog, a kérés ≥ 50%, de az akkuáram ~0-ra esik, és
# legalább 1 s-ig nem tér vissza. A hiba az áram visszatéréséig (≥ 1 A), ennek hiányában a
# munkamenet (napló) végéig tart. A rövid átmenetek (a kérés felfutása után az áram
# 0,1–0,2 s késéssel követi) így kimaradnak. A csapat megerősítése szerint ilyenkor az
# inverter lekapcsolt; 83 °C felett az inverter biztosan lekapcsol (termikus védelem).
HIBA_KERES_PCT = 50
HIBA_ARAM_A = 1.0
HIBA_MIN_RPM = 500
HIBA_MIN_HOSSZ_S = 1.0
INVERTER_LEKAPCSOLASI_T_C = 83.0     # a csapat tájékoztatása: e fölött biztosan lekapcsol
INVERTER_LESZABALYOZAS_T_C = 70.0    # a csapat szerint (bizonytalan): innen szabályoz vissza


def inverter_hiba_jeloles(df):
    """Logikai sorozat: True a sorokban, ahol az inverter hiba miatt ki van kapcsolva."""
    jeloles = pd.Series(False, index=df.index)
    for _, g in df.groupby("session", sort=False):
        kezdet = ((g["torque_request_pct"] >= HIBA_KERES_PCT) & (g["batt_current_A"] < HIBA_ARAM_A)
                  & (g["motor_rpm"] > HIBA_MIN_RPM))
        i, indexek = 0, g.index
        while i < len(g):
            if not kezdet.iloc[i]:
                i += 1
                continue
            j = i
            while j < len(g) and g["batt_current_A"].iloc[j] < HIBA_ARAM_A:
                j += 1
            if g["t_s"].iloc[j - 1] - g["t_s"].iloc[i] + DT_S >= HIBA_MIN_HOSSZ_S:
                jeloles[indexek[i:j]] = True
            i = j
    return jeloles


def inverter_hiba_esemenyek(df):
    """Az inverter_hiba oszlop összefüggő szakaszai munkamenetenként (táblázat)."""
    hiba = df[df["inverter_hiba"]]
    # 0,5 s-nál rövidebb rés (pl. a tisztításkor törölt egy-egy hibás keret) nem szakaszhatár
    uj_blokk = (hiba["session"] != hiba["session"].shift()) | (hiba["t_s"].diff() > 5 * DT_S)
    sorok = []
    for _, g in hiba.groupby(uj_blokk.cumsum()):
        T_inv = g["inverter_temp_C"].iloc[0]
        sorok.append({"munkamenet": g["session"].iloc[0], "kezdet_s": g["t_s"].iloc[0],
                      "veg_s": g["t_s"].iloc[-1],
                      "hossz_s": round(g["t_s"].iloc[-1] - g["t_s"].iloc[0] + DT_S, 1),
                      "sorok": len(g), "keres_5pct_felett": int((g["torque_request_pct"] > 5).sum()),
                      "rpm_kezdet": int(g["motor_rpm"].iloc[0]), "v_kezdet_kmh": g["speed_kmh"].iloc[0],
                      "v_veg_kmh": g["speed_kmh"].iloc[-1], "T_inverter_C": T_inv,
                      "valoszinu_ok": ("termikus (≥ {:.0f} °C)".format(INVERTER_LEKAPCSOLASI_T_C)
                                       if T_inv >= INVERTER_LEKAPCSOLASI_T_C else "nem termikus")})
    return pd.DataFrame(sorok)


def futam_azonosito(df):
    """Soronkénti futam-sorszám (1, 2, ...); NaN, ha a sor nem tartozik gyorsító futamhoz."""
    aktiv = df["torque_request_pct"] > FUTAM_KERES_PCT
    uj_blokk = ((df["session"] != df["session"].shift()) | (aktiv != aktiv.shift())
                | (df["t_s"].diff() > 1.5 * DT_S))
    blokk = uj_blokk.cumsum()
    azonosito = pd.Series(np.nan, index=df.index)
    sorszam = 0
    for _, g in df[aktiv].groupby(blokk[aktiv]):
        energia_kj = (g["batt_power_kW"] * DT_S).sum()
        if len(g) * DT_S >= FUTAM_MIN_HOSSZ_S and energia_kj >= FUTAM_MIN_ENERGIA_KJ:
            sorszam += 1
            azonosito[g.index] = sorszam
    return azonosito


def cim(szoveg):
    """Szakaszcím a kimenetben."""
    print()
    print("=" * 70)
    print(szoveg)
    print("=" * 70)


def beolvas(utvonal=TISZTITOTT_CSV):
    return pd.read_csv(utvonal, sep=";", encoding="utf-8")


def ax_formaz(ax, cim_szoveg, xlabel, ylabel, racs="both"):
    """Közös formázás: cím, tengelyfeliratok, halvány rács."""
    ax.set_title(cim_szoveg, loc="left", fontsize=11)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis=racs, color=RACS_SZIN, linewidth=0.8)
    ax.set_axisbelow(True)
    for oldal in ("top", "right"):
        ax.spines[oldal].set_visible(False)


def abra_mentes(fig, fajlnev):
    """Az ábrát a futtatott fázisscript saját mappájába menti."""
    script = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    mappa = os.path.dirname(script) if script.endswith(".py") else MAPPA
    fig.savefig(os.path.join(mappa, fajlnev), dpi=120)


def ezres(x, tizedes=0):
    """Magyar számformátum: szóköz az ezreseknél, tizedesvessző."""
    return "{:,.{}f}".format(x, tizedes).replace(",", " ").replace(".", ",")


def heatmap(ax, korr):
    """Annotált korrelációs hőtérkép matplotlibbel (seaborn nélkül)."""
    n = len(korr)
    kep = ax.imshow(korr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    for i in range(n):
        for j in range(n):
            ertek = korr.iat[i, j]
            ax.text(j, i, "{:.2f}".format(ertek), ha="center", va="center", fontsize=8,
                    color="white" if abs(ertek) > 0.6 else SZOVEG_SZIN)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(korr.columns, rotation=40, ha="right")
    ax.set_yticklabels(korr.index)
    ax.set_xticks(np.arange(-0.5, n), minor=True)
    ax.set_yticks(np.arange(-0.5, n), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="both", length=0)
    for oldal in ax.spines.values():
        oldal.set_visible(False)
    return kep
