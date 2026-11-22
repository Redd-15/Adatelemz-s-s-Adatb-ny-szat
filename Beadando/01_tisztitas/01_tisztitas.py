# -*- coding: utf-8 -*-
"""1. Adattisztítás és -előkészítés.

Bemenet: 00_hajtaslanc_nyers.csv (a 00_blf_konvertalas.py kimenete)
Kimenet: 01_hajtaslanc_tisztitott.csv, valamint három ábra:
         01_hibas_keretek.png, 01_gyorsulas_simitas.png, 01_kiugro_vs_hiba.png

Új (a modellezésben nem használt) mérés tisztítása ugyanezekkel a lépésekkel, ábrák nélkül:
    python 01_tisztitas/01_tisztitas.py --bemenet 00_hajtaslanc_uj_nyers.csv --kimenet 01_hajtaslanc_uj_tisztitott.csv
(a relatív fájlnevek a Beadando mappára vonatkoznak; az ábrák a 01_tisztitas mappába kerülnek)

A lépések sorrendje: előbb az idősor-szintű műveletek a teljes, folytonos
10 Hz-es soron (egyenletes mintavételt feltételeznek), utána a sorok szűrése,
végül az oszlopok rendezése és az ellenőrzés.

 A) Idősor-szintű lépések (munkamenetenként)
    1. Negatív sebesség és fordulatszám -> 0
    2. Gyorsulás (accel_ms2) a sebességből, 0,5 s-os simítással
    3. A BMS kisütőáram-korlát hiányzó értékei -> előző érték
 B) Sorszűrés
    4. Fizikailag lehetetlen AMS keretek törlése (3 szabály)
    5. Csak az R2D (menetkész) állapot marad, és abból is csak az, ahol a
       nagyfeszültségű rendszer valóban be van kapcsolva (leállási átmenet nélkül)
    6. A nyomatékkérés hiányzó értékei -> 0
    7. Inverterhiba-szakaszok JELÖLÉSE (inverter_hiba oszlop, a sorok megmaradnak)
 C) Oszlopok
    8. Redundáns oszlopok törlése
    9. batt_power_kW, valamint a torque_est_Nm újraszámolása
 D) Ellenőrzés: hiányzó értékek, fizikai tartományok, IQR-kiugrók.
    A statisztikai kiugrókat NEM töröljük, csak a fizikailag lehetetlen értékeket.
"""

import argparse
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import os as _os
import sys as _sys
# a közös modul (hajtaslanc_kozos.py) a szülőmappában, a Beadando mappában van
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from hajtaslanc_kozos import (MAPPA, NYERS_CSV, TISZTITOTT_CSV, SZIN, SZIN2, HIBA_SZIN,
                              HALVANY_SZIN, SZOVEG_SZIN, MASODLAGOS_SZOVEG,
                              beolvas, cim, ax_formaz, abra_mentes, ezres,
                              inverter_hiba_jeloles, inverter_hiba_esemenyek)

CELLASZAM = 110          # soros cellák: pack_voltage / cell_v_avg mediánja = 110,0
ARAM_SZORZO = 1.5        # |áram| > 1,5 × BMS max. kisütőáram -> lehetetlen
PACK_TURES_V = 10        # |pack - 110 × átlagos cellafesz.| > 10 V -> lehetetlen
MIN_TS_FESZULTSEG_V = 275   # 110 cella × 2,5 V: ez alatt a nagyfeszültségű rendszer ki van kapcsolva
SIMITAS_MINTA = 5        # 5 minta = 0,5 s mozgóátlag a gyorsuláshoz
MIN_RPM_NYOMATEKHOZ = 500   # ugyanaz, mint a 00_blf_konvertalas.py-ban
R2D = "R2D"

REDUNDANS_OSZLOPOK = ["apps1_pct", "apps2_pct", "dc_bus_voltage_V", "pack_voltage_V",
                      "vehicle_state", "vehicle_state_name"]

KIMENETI_OSZLOPOK = [
    "session", "timestamp", "t_s", "inverter_hiba",
    "apps_pct", "torque_request_pct", "torque_est_Nm", "motor_rpm", "speed_kmh", "accel_ms2",
    "batt_current_A", "batt_voltage_V", "batt_power_kW", "soc_pct", "max_discharge_current_A",
    "cell_v_min_V", "cell_v_avg_V", "cell_v_max_V", "cell_t_min_C", "cell_t_avg_C",
    "cell_t_max_C", "inverter_temp_C", "motor_temp_C",
]

# oszlop -> (alsó határ, felső határ, forrás); a tisztított adatnak ezen belül kell lennie
FIZIKAI_HATAROK = {
    "apps_pct": (0, 100, "DBC"),
    "torque_request_pct": (0, 100, "definíció"),
    "motor_rpm": (0, 10000, "DBC"),
    "speed_kmh": (0, 200, "DBC"),
    "accel_ms2": (-20, 20, "kb. ±2 g"),
    "batt_current_A": (-5, 189, "BMS max. kisütőáram; -5 A: mérési zaj"),
    "batt_voltage_V": (275, 462, "110 cella × 2,5…4,2 V"),
    "soc_pct": (0, 100, "definíció"),
    "cell_v_min_V": (2.5, 4.2, "Li-ion cella"),
    "cell_v_avg_V": (2.5, 4.2, "Li-ion cella"),
    "cell_v_max_V": (2.5, 4.2, "Li-ion cella"),
    "cell_t_min_C": (0, 60, "FS szabály: max. 60 °C"),
    "cell_t_avg_C": (0, 60, "FS szabály: max. 60 °C"),
    "cell_t_max_C": (0, 60, "FS szabály: max. 60 °C"),
    "inverter_temp_C": (0, 100, "DBC"),
    "motor_temp_C": (0, 200, "DBC"),
}

DOBOZ_VALTOZOK = [
    ("batt_current_A", "Akkuáram [A]"),
    ("batt_power_kW", "Akkuteljesítmény [kW]"),
    ("accel_ms2", "Gyorsulás [m/s²]"),
    ("torque_est_Nm", "Becsült nyomaték [Nm]"),
    ("inverter_temp_C", "Inverterhőmérséklet [°C]"),
    ("cell_v_min_V", "Min. cellafeszültség [V]"),
]


# ---------------------------------------------------------------------------
# A) Idősor-szintű lépések
# ---------------------------------------------------------------------------

def negativ_levagas(df):
    cim("1. Negatív sebesség és fordulatszám -> 0")
    for oszlop in ("speed_kmh", "motor_rpm"):
        negativ = df[oszlop] < 0
        print("{:10s} {} negatív érték (legkisebb: {}) -> 0".format(
            oszlop, negativ.sum(), df.loc[negativ, oszlop].min()))
        df.loc[negativ, oszlop] = 0
    print()
    print("Az autó nem tolat; ezek álló helyzetben mért szenzor-offszetek.")
    negativ_aram = df["batt_current_A"] < 0
    print("A negatív akkuáram MEGMARAD: {} sor, legkisebb {} A.".format(
        negativ_aram.sum(), df["batt_current_A"].min()))
    print("A ±1,5 A az áramszenzor mérési pontosságán belül van, a 0-ra vágás")
    print("pozitív irányba torzítaná az áram eloszlását.")
    return df


def gyorsulas(df):
    cim("2. Gyorsulás számítása a sebességből")
    csoport = df.groupby("session")
    dv = csoport["speed_kmh"].diff() / 3.6          # km/h -> m/s
    dt = csoport["t_s"].diff()
    df["accel_nyers"] = dv / dt
    df["accel_ms2"] = df.groupby("session")["accel_nyers"].transform(
        lambda s: s.rolling(SIMITAS_MINTA, center=True, min_periods=1).mean())
    osszevetes = df[["accel_nyers", "accel_ms2"]].agg(["min", "max", "std"]).T
    print(osszevetes.round(2).to_string())
    print()
    print("A sebesség 0,1 km/h felbontású és 10 Hz-en érkezik, ezért a nyers")
    print("Δv/Δt (0,1 s) ±15 m/s²-ig ugrál; ez kvantálási és időzítési zaj, nem")
    print("valós gyorsulás. Az {} mintás (0,5 s-os) középre igazított mozgóátlag".format(SIMITAS_MINTA))
    print("után a tartomány fizikailag reális (egy FS autó kb. 0,8 g-vel gyorsul).")
    print("A számítás munkamenetenként, a sorok törlése ELŐTT történik, mert a")
    print("különbségképzéshez folytonos idősor kell.")
    return df


def bms_korlat_potlas(df):
    cim("3. A BMS kisütőáram-korlát hiányzó értékei -> előző érték")
    hiany = df["max_discharge_current_A"].isna()
    df["max_discharge_current_A"] = df.groupby("session")["max_discharge_current_A"].ffill()
    maradt = df["max_discharge_current_A"].isna()
    print("Hiányzó érték: {} sor, ebből előző értékkel pótolva: {}, maradt: {}".format(
        hiany.sum(), (hiany & ~maradt).sum(), maradt.sum()))
    if maradt.any():
        print("A maradék a munkamenetek legelején van (még nem érkezett üzenet):",
              df.loc[maradt, ["session", "t_s"]].to_dict("records"))
        print("Ezek nem R2D sorok, így az 5. lépésben kiesnek.")
    print()
    print("Az AMS ezt az üzenetet ritkábban küldi (~5 Hz), ezért néhol 0,5 s-nál")
    print("hosszabb a szünet. Az érték lassan változó korlát (175–189 A), így az utolsó")
    print("ismert érték a legjobb becslés.")
    return df


# ---------------------------------------------------------------------------
# B) Sorszűrés
# ---------------------------------------------------------------------------

def hibas_keretek(df):
    cim("4. Fizikailag lehetetlen AMS keretek")
    arany = (df["pack_voltage_V"] / df["cell_v_avg_V"]).median()
    print("pack_voltage_V / cell_v_avg_V mediánja = {:.1f} -> {} soros cella".format(arany, CELLASZAM))
    aram_hatar = ARAM_SZORZO * df["max_discharge_current_A"].max()
    szabalyok = {
        "A) |áram| > {:.0f} A (1,5 × BMS max.)".format(aram_hatar):
            df["batt_current_A"].abs() > aram_hatar,
        "B) cellafeszültség: nem min ≤ átlag ≤ max":
            ~((df["cell_v_min_V"] <= df["cell_v_avg_V"]) & (df["cell_v_avg_V"] <= df["cell_v_max_V"]))
            & df["cell_v_avg_V"].notna(),
        "C) |pack - {} × átlagos cellafesz.| > {} V".format(CELLASZAM, PACK_TURES_V):
            (df["pack_voltage_V"] - CELLASZAM * df["cell_v_avg_V"]).abs() > PACK_TURES_V,
    }
    for nev, maszk in szabalyok.items():
        print("  {:45s} {} sor".format(nev, maszk.sum()))
    hibas = np.logical_or.reduce(list(szabalyok.values()))
    print("  {:45s} {} sor".format("bármelyik szabály (unió)", hibas.sum()))
    print()
    hibas_sorok = df[hibas]
    print(hibas_sorok[["session", "t_s", "batt_current_A", "batt_voltage_V", "soc_pct",
                       "pack_voltage_V", "cell_v_avg_V", "cell_v_max_V"]].to_string(index=False))
    print()
    print("Mindhárom független szabály ugyanazt a 2 sort jelöli. Ezekben a keretekben a")
    print("nyers bájtok cellahőmérséklet-mintázatúak (0x018x = 38,x °C): az AMS időnként")
    print("hőmérséklet-csomagot küld az AMS_Stat (450) azonosítóval. Ezért a sor MINDEN")
    print("akkus értéke hibás (a látszólagos SOC-zuhanás 84 -> 38% is ebből jön), így a")
    print("teljes sort töröljük. A 10 Hz-es idősorban 0,1 s-os rés marad, ez elhanyagolható.")
    return df[~hibas].copy(), hibas_sorok


def allapot_szures(df):
    cim("5. Állapotszűrés: csak R2D (menetkész)")
    print(pd.crosstab(df["session"], df["vehicle_state_name"], margins=True,
                      margins_name="összesen").to_string())
    elotte = len(df)
    df = df[df["vehicle_state_name"] == R2D].copy()
    print()
    print("a) Törölve: {} sor (STANDBY / TS_ON), marad: {} sor".format(elotte - len(df), len(df)))
    print("   STANDBY / TS_ON állapotban a hajtáslánc nem ad nyomatékot, ezek a sorok nem")
    print("   a hajtáslánc működését írják le. Ezzel az első, teljesen üres sor is kiesik")
    print("   (a naplózás legelején még egyetlen üzenet sem érkezett).")

    leallas = df["batt_voltage_V"] < MIN_TS_FESZULTSEG_V
    print()
    print("b) R2D, de az akkufeszültség < {} V (110 cella × 2,5 V): {} sor".format(
        MIN_TS_FESZULTSEG_V, leallas.sum()))
    print(df.loc[leallas, ["session", "t_s", "speed_kmh", "batt_current_A", "batt_voltage_V",
                           "dc_bus_voltage_V"]].to_string(index=False))
    df = df[~leallas].copy()
    print("   Leállási átmenet: a nagyfeszültségű rendszer már lekapcsolt (az akkufeszültség")
    print("   0,2 s alatt ~0 V-ra esik, az inverter DC-köre kisül), de az állapotjel még")
    print("   ~0,8 s-ig R2D-t mutat. A hajtáslánc ekkor már nem működik -> törölve.")
    print("   Marad: {} sor".format(len(df)))

    print()
    print("Az álló R2D sorok MEGMARADNAK ({} sor, v < 1 km/h): ez valós üzemállapot".format(
        (df["speed_kmh"] < 1).sum()))
    print("(menetkész, áll). A klaszterezésnél külön döntünk róluk.")
    return df


def nyomatekkeres_potlas(df):
    cim("6. A nyomatékkérés hiányzó értékei -> 0")
    hiany = df["torque_request_pct"].isna()
    print("Hiányzó érték R2D-ben: {} sor".format(hiany.sum()))
    for session, resz in df[hiany].groupby("session"):
        print("  {}: {} sor, t_s = {}–{} s, gázpedál max. {}%".format(
            session, len(resz), resz["t_s"].min(), resz["t_s"].max(), resz["apps_pct"].max()))
    df.loc[hiany, "torque_request_pct"] = 0.0
    print()
    print("A vezérlő a nyomatékkérés-üzenetet csak R2D-ben küldi, és az R2D kezdete után")
    print("néhány tized másodperccel indul el. Ha nincs üzenet, nincs nyomatékkérés")
    print("(a gázpedál is ~0%), ezért a helyes érték 0.")

    # a torque_est_Nm 500 rpm alatt definíció szerint üres, ezért nem számít hiánynak
    ellenorzott = [o for o in df.columns if o != "torque_est_Nm"]
    hianyos = df[ellenorzott].isna().any(axis=1)
    print()
    print("Maradék hiányos R2D sor (más mért érték is hiányzik): {} sor -> törölve".format(hianyos.sum()))
    if hianyos.any():
        print(df.loc[hianyos, ["session", "t_s"]].to_string(index=False))
        print("Ha a napló már menet közben indul, az első sorokban még nem érkezett meg")
        print("minden üzenet; ezek a sorok nem pótolhatók megbízhatóan.")
    return df[~hianyos].copy()


def inverter_hiba(df):
    cim("7. Inverterhiba-szakaszok jelölése (inverter_hiba oszlop)")
    df["inverter_hiba"] = inverter_hiba_jeloles(df)
    print(inverter_hiba_esemenyek(df).round(1).to_string(index=False))
    print()
    print("Jelölve: {} sor ({:.1%}). Felismerés: a motor forog, a kérés ≥ 50%, de az akkuáram ~0-ra".format(
        df["inverter_hiba"].sum(), df["inverter_hiba"].mean()))
    print("esik, és legalább 1 s-ig nem tér vissza (a rövid, 0,1–0,2 s-os átmenetek így kimaradnak).")
    print("A hiba az áram visszatéréséig, ennek hiányában a napló végéig tart.")
    print("A csapat tájékoztatása szerint az inverter ilyenkor lekapcsolt; 83 °C felett a termikus")
    print("védelem biztosan lekapcsolja. A 'valoszinu_ok' oszlop ezt a hiba pillanatában mért")
    print("inverterhőmérséklet alapján jelzi. A sorokat NEM töröljük, csak jelöljük: a feltáró")
    print("elemzés és a klaszterezés kizárja őket (a hajtáslánc nem működik), a hőmodell viszont")
    print("hűlési adatként használja (terhelés nélkül hűlő inverter).")
    return df


# ---------------------------------------------------------------------------
# C) Oszlopok
# ---------------------------------------------------------------------------

def redundans_oszlopok(df):
    cim("8. Redundáns oszlopok törlése")
    apps_elteres = (df["apps1_pct"] - df["apps2_pct"]).abs()
    print("apps1_pct, apps2_pct: a két pedálszenzor max. eltérése {:.1f}% (az FS szabály"
          .format(apps_elteres.max()))
    print("  szerinti 10%-os határ alatt, nincs érvénytelen jel); az apps_pct a kettő")
    print("  átlaga (max. eltérés {:.2f}%).".format(
        (df["apps_pct"] - (df["apps1_pct"] + df["apps2_pct"]) / 2).abs().max()))
    kul_bus = df["batt_voltage_V"] - df["dc_bus_voltage_V"]
    print("dc_bus_voltage_V: r = {:.3f} a batt_voltage_V-vel, mediánkülönbség {:.2f} V;".format(
        df["batt_voltage_V"].corr(df["dc_bus_voltage_V"]), kul_bus.median()))
    print("  az inverter mérése, egész V felbontással. A pontosabb akkumérés (batt_voltage_V) marad.")
    kul_pack = df["batt_voltage_V"] - df["pack_voltage_V"]
    print("pack_voltage_V: r = {:.3f} a batt_voltage_V-vel, mediánkülönbség {:.2f} V;".format(
        df["batt_voltage_V"].corr(df["pack_voltage_V"]), kul_pack.median()))
    print("  a cellafeszültségek összege, ugyanazt méri.")
    print("vehicle_state, vehicle_state_name: a szűrés után konstans ({}).".format(
        ", ".join(df["vehicle_state_name"].unique())))
    return df.drop(columns=REDUNDANS_OSZLOPOK + ["accel_nyers"])


def szarmaztatott_oszlopok(df, nyers_nyomatek_max):
    cim("9. Származtatott oszlopok")
    omega = df["motor_rpm"] * 2 * np.pi / 60
    df["torque_est_Nm"] = (df["batt_power_W"] / omega).where(
        df["motor_rpm"] > MIN_RPM_NYOMATEKHOZ).round(1)
    df["batt_power_kW"] = (df["batt_power_W"] / 1000).round(3)
    df["accel_ms2"] = df["accel_ms2"].round(2)
    df = df.drop(columns=["batt_power_W"])
    print("batt_power_kW = batt_power_W / 1000 (olvashatóbb skála).")
    print("torque_est_Nm újraszámolva a tisztított értékekből: P / ω, csak {} rpm felett."
          .format(MIN_RPM_NYOMATEKHOZ))
    print("  Maximuma a hibás keretek törlése után {} Nm (a nyers adatban {} Nm volt,".format(
        ezres(df["torque_est_Nm"].max(), 1), ezres(nyers_nyomatek_max, 1)))
    print("  azt a hibás akkuteljesítmény okozta).")
    print("accel_ms2: lásd a 2. lépést.")
    # egész értékű oszlopok egészként (a hiányzó értékek miatt float-ként olvasódtak be)
    for oszlop in ("motor_rpm", "max_discharge_current_A"):
        df[oszlop] = df[oszlop].astype(int)
    return df


# ---------------------------------------------------------------------------
# D) Ellenőrzés
# ---------------------------------------------------------------------------

def ellenorzes(df):
    cim("Ellenőrzés: hiányzó értékek")
    hiany = df.isna().sum()
    print(hiany[hiany > 0].to_string() if hiany.any() else "nincs hiányzó érték")
    print("A torque_est_Nm {} rpm alatt definíció szerint üres (ω -> 0 miatt a P/ω".format(
        MIN_RPM_NYOMATEKHOZ))
    print("instabil); ez nem adathiba, ezért nem pótoljuk.")

    cim("Ellenőrzés: fizikai tartományok")
    sorok = []
    for oszlop, (also, felso, forras) in FIZIKAI_HATAROK.items():
        s = df[oszlop]
        sorok.append({"oszlop": oszlop, "min": s.min(), "max": s.max(), "alsó határ": also,
                      "felső határ": felso, "forrás": forras,
                      "rendben": "igen" if s.min() >= also and s.max() <= felso else "NEM"})
    print(pd.DataFrame(sorok).to_string(index=False))
    tullepes = (df["batt_current_A"] > df["max_discharge_current_A"]).sum()
    print()
    print("Áram > az adott pillanatban érvényes BMS-korlát: {} sor".format(tullepes))

    cim("Ellenőrzés: statisztikai kiugrók (IQR-módszer, 1,5 × IQR) – NEM töröljük")
    sorok = []
    for oszlop in df.select_dtypes("number").columns.drop("t_s"):
        s = df[oszlop].dropna()
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        kiugro = ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum()
        sorok.append({"oszlop": oszlop, "kiugró": kiugro, "arány %": round(100 * kiugro / len(s), 1)})
    tabla = pd.DataFrame(sorok)
    print(tabla.to_string(index=False))
    van = tabla[tabla["kiugró"] > 0]
    print()
    print("IQR-kiugró csak itt van: {}.".format(
        ", ".join("{} ({} db)".format(o, k) for o, k in zip(van["oszlop"], van["kiugró"]))))
    print("Mind a fizikai határon belül esik (lásd fent), tehát valós, csak ritka értékek:")
    print("a gyorsulás kiugrói a rajtok és az erős lassítások csúcsai. A statisztikai kiugró")
    print("nem azonos a hibával. A törlésük éppen a hajtáslánc legintenzívebb üzemállapotait")
    print("vinné el, ezért megtartjuk őket. A többi változó eloszlása olyan széles (pl. az")
    print("akkuáram 0 és 109 A között), hogy az 1,5 × IQR-sávon belül marad.")


# ---------------------------------------------------------------------------
# Ábrák
# ---------------------------------------------------------------------------

def abra_hibas_keretek(nyers, hibas):
    fig, axes = plt.subplots(1, len(hibas), figsize=(13, 4.4))
    for ax, (index, sor) in zip(np.atleast_1d(axes), hibas.iterrows()):
        resz = nyers[(nyers["session"] == sor["session"]) & (nyers.index != index)]
        felso = resz["batt_current_A"].max() * 1.75     # hely a feliratnak az adatok felett
        ax.plot(resz["t_s"], resz["batt_current_A"], color=SZIN, linewidth=1.2)
        ax.axvline(sor["t_s"], color=HIBA_SZIN, linewidth=1, linestyle="--")
        ax.plot(sor["t_s"], felso, marker="^", markersize=10, color=HIBA_SZIN, clip_on=False)
        jobbra = sor["t_s"] < resz["t_s"].max() * 0.6
        szoveg = ("hibás keret, t = {} s\n"
                  "áram: {} A\nfeszültség: {} V\nSOC: {}%\nmax. cellafesz.: {} V").format(
            ezres(sor["t_s"], 1), ezres(sor["batt_current_A"]), ezres(sor["batt_voltage_V"]),
            ezres(sor["soc_pct"], 1), ezres(sor["cell_v_max_V"], 3))
        ax.annotate(szoveg, xy=(sor["t_s"], felso), xytext=(12 if jobbra else -12, -14),
                    textcoords="offset points", ha="left" if jobbra else "right", va="top",
                    fontsize=8.5, color=SZOVEG_SZIN)
        ax.set_ylim(-5, felso)
        ax_formaz(ax, "{} munkamenet".format(sor["session"]),
                  "idő a munkamenet elejétől [s]", "akkuáram [A]")
    fig.suptitle("Hibás AMS keretek: a sor minden akkus értéke fizikailag lehetetlen "
                 "(a ▲ a skálán kívül esik)", fontsize=12)
    fig.tight_layout()
    abra_mentes(fig, "01_hibas_keretek.png")


def abra_gyorsulas(idosor):
    resz = idosor[(idosor["session"] == "15:39:36") & idosor["t_s"].between(10, 50)]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True,
                                   gridspec_kw={"height_ratios": [1, 1.4]})
    ax1.plot(resz["t_s"], resz["speed_kmh"], color=SZIN, linewidth=1.5)
    ax_formaz(ax1, "Sebesség (15:39:36 munkamenet)", "", "km/h")
    ax2.plot(resz["t_s"], resz["accel_nyers"], color=HALVANY_SZIN, linewidth=1,
             label="nyers: Δv / Δt (0,1 s)")
    ax2.plot(resz["t_s"], resz["accel_ms2"], color=SZIN2, linewidth=2,
             label="simított: {} mintás (0,5 s) mozgóátlag".format(SIMITAS_MINTA))
    ax2.axhline(0, color=MASODLAGOS_SZOVEG, linewidth=0.8)
    ax2.legend(frameon=False, loc="lower left", fontsize=9)
    ax_formaz(ax2, "Gyorsulás a sebességből", "idő a munkamenet elejétől [s]", "m/s²")
    fig.tight_layout()
    abra_mentes(fig, "01_gyorsulas_simitas.png")


def abra_kiugrok(df):
    fig, axes = plt.subplots(2, 3, figsize=(14, 6.2))
    for ax, (oszlop, felirat) in zip(axes.flat, DOBOZ_VALTOZOK):
        s = df[oszlop].dropna()
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        kiugro = ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum()
        doboz = ax.boxplot(s, vert=False, widths=0.5, patch_artist=True,
                           medianprops={"color": SZOVEG_SZIN, "linewidth": 1.8},
                           flierprops={"marker": "o", "markersize": 3.5,
                                       "markerfacecolor": SZIN2, "markeredgecolor": "none",
                                       "alpha": 0.6})
        doboz["boxes"][0].set(facecolor=SZIN, alpha=0.45, edgecolor=SZIN)
        ax.set_yticks([])
        kiugro_szoveg = ("nincs IQR-kiugró" if kiugro == 0
                         else "{} IQR-kiugró (megtartva)".format(kiugro))
        if oszlop in FIZIKAI_HATAROK:
            also, felso, _ = FIZIKAI_HATAROK[oszlop]
            alcim = "{} · fizikai határ: {}…{}".format(
                kiugro_szoveg, ezres(also, 1 if also % 1 else 0), ezres(felso, 1 if felso % 1 else 0))
        else:
            alcim = kiugro_szoveg
        ax_formaz(ax, "{}\n{}".format(felirat, alcim), "", "", racs="x")
        ax.title.set_fontsize(10)
    fig.suptitle("Tisztított adatok: a statisztikai kiugrók valós üzemállapotok, nem hibák",
                 fontsize=12)
    fig.tight_layout()
    abra_mentes(fig, "01_kiugro_vs_hiba.png")


# ---------------------------------------------------------------------------
# Főprogram
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--bemenet", default=NYERS_CSV, help="a nyers CSV (a 00-s script kimenete)")
    parser.add_argument("--kimenet", default=TISZTITOTT_CSV, help="a tisztított CSV útvonala")
    args = parser.parse_args()
    bemenet = os.path.join(MAPPA, args.bemenet)
    kimenet = os.path.join(MAPPA, args.kimenet)
    alapadat = os.path.abspath(bemenet) == os.path.abspath(NYERS_CSV)

    pd.set_option("display.width", 140)
    nyers = beolvas(bemenet)
    print("Beolvasva: {} sor, {} oszlop ({})".format(*nyers.shape, bemenet))

    # A) idősor-szintű lépések a teljes, folytonos soron
    df = negativ_levagas(nyers.copy())
    df = gyorsulas(df)
    idosor = df.copy()                       # az ábrához (nyers és simított gyorsulás)
    df = bms_korlat_potlas(df)

    # B) sorszűrés
    df, hibas = hibas_keretek(df)
    df = allapot_szures(df)
    df = nyomatekkeres_potlas(df)
    df = inverter_hiba(df)

    # C) oszlopok
    df = redundans_oszlopok(df)
    df = szarmaztatott_oszlopok(df, nyers["torque_est_Nm"].max())
    df = df[KIMENETI_OSZLOPOK].reset_index(drop=True)

    # D) ellenőrzés
    ellenorzes(df)

    df.to_csv(kimenet, sep=";", index=False, encoding="utf-8")
    cim("Összegzés")
    print("Nyers:      {} sor × {} oszlop".format(*nyers.shape))
    print("Tisztított: {} sor × {} oszlop -> {}".format(*df.shape, kimenet))
    print("Sorok munkamenetenként:", df["session"].value_counts(sort=False).to_dict())
    print("Ebből inverterhiba miatt jelölt (inverter_hiba = True): {} sor; működő hajtáslánc: {} sor".format(
        df["inverter_hiba"].sum(), (~df["inverter_hiba"]).sum()))

    if not alapadat:
        print("(Új mérés: az ábrák nem készülnek el, hogy ne írják felül az alapadat ábráit.)")
        return
    abra_hibas_keretek(nyers, hibas)
    abra_gyorsulas(idosor)
    abra_kiugrok(df)
    plt.show()


if __name__ == "__main__":
    main()
