# -*- coding: utf-8 -*-
"""BLF -> CSV konverter: az FS autó CAN-naplóiból hajtáslánc- és akkumulátoradatok.

Bemenet:  BaseData/*.blf (Vector BLF, CAN FD nyers napló) és a tesztnap idején
          érvényes BaseData/ERMe01_v2_2.dbc
Kimenet:  00_hajtaslanc_nyers.csv (pontosvesszővel tagolt, UTF-8, tizedespont)

DBC-javítás: a v2.2 az MPCU_InverterForceRequest.Force jelet big-endian,
előjel nélküli 16 bitesnek írja le, a nyers adatok viszont a v2.4-es
definíciónak (little-endian, előjeles) felelnek meg. Így a Force teljes gáznál
-32767, és monoton követi a gázpedált (r = 0,97). A v2.2 szerinti olvasat
teljes gáznál 384-et, részgáznál ~35 000-et adna. Ezért ezt az egy üzenetet a
v2.4 alapján dekódoljuk, minden mást a v2.2 alapján.

Feldolgozási lépések:
1. A keretek dekódolása a DBC alapján, fizikai mértékegységre skálázva.
2. Közös, egyenletes 10 Hz-es időrács. Minden rácspontban a jel legutóbb
   beérkezett értéke szerepel (mintavétel-tartás), legfeljebb 0,5 s-ig
   visszamenőleg. Ha az utolsó érték ennél régebbi (az üzenet nem érkezik),
   a cella üres.
3. Fájlonként csak az aktív szakasz marad: 5 s-mal az első R2D (Ready-to-Drive)
   állapot előttől 5 s-mal az utolsó R2D / mozgás utánig.
4. Két származtatott oszlop: nyomatékkérés (%) és becsült nyomaték (Nm).

SZÁNDÉKOSAN NINCS ADATTISZTÍTÁS. A hibás keretek (pl. ~26 000 A-es áramtüskék),
a hiányzó értékek és az álló szakaszok bent maradnak, ezeket az elemzés
tisztítási lépése kezeli.

Használat (a Beadando mappából; a CSV a Beadando mappába kerül):
    python 00_blf_konvertalas/00_blf_konvertalas.py
    python 00_blf_konvertalas/00_blf_konvertalas.py --fajlok "2026-08-28 12.59.30.154699.blf" --kimenet 00_hajtaslanc_uj_nyers.csv
"""

import argparse
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta

import can
import cantools
import numpy as np
import pandas as pd

# a script a Beadando/00_blf_konvertalas mappában van; a nyers adatok és a CSV a Beadando-ban
MAPPA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAT_MAPPA = os.path.join(MAPPA, "BaseData")
DBC_FAJL = os.path.join(ADAT_MAPPA, "ERMe01_v2_2.dbc")
# Ebből csak a Force üzenet definíciója kell (lásd a modul leírását).
DBC_FORCE_JAVITAS = os.path.join(ADAT_MAPPA, "ERMe01_v2_4.dbc")
KIMENET = os.path.join(MAPPA, "00_hajtaslanc_nyers.csv")

# A tesztnap utolsó menetblokkja (15:21-15:43). A 15.39.08-as fájl kimarad:
# abban az autó végig STANDBY/TS_ON állapotban állt.
ALAP_FAJLOK = [
    "2026-08-28 15.21.59.673596.blf",
    "2026-08-28 15.23.21.822649.blf",
    "2026-08-28 15.29.33.918484.blf",
    "2026-08-28 15.39.36.918785.blf",
]

FREKVENCIA_HZ = 10       # az AMS_Stat és az MPCU_Values is ~10 Hz-en érkezik
TURES_S = 0.5            # ennél régebbi utolsó érték -> hiányzó
ELOTTE_S = 5.0           # ennyivel az első R2D előttől
UTANA_S = 5.0            # ennyivel az utolsó R2D / mozgás utánig
R2D = 3                  # MPCU_VehicleState: 3 = "R2D" (Ready-to-Drive)
MOZGAS_KMH = 1.0         # e fölött mozgónak tekintjük az autót
FORCE_TELJES_SKALA = 32767   # Force = -32767 -> 100% nyomatékkérés
MIN_RPM_NYOMATEKHOZ = 500    # alatta a P/omega becslés instabil (omega -> 0)

# CSV oszlop -> (DBC üzenet, DBC jel). A sorrend a kimenet oszlopsorrendje.
JELEK = {
    "vehicle_state": ("MPCU_VehicleState", "VehicleState"),
    "apps_pct": ("APPS_NormalData", "AppsData"),
    "apps1_pct": ("APPS_NormalData", "Apps1Interpolated"),
    "apps2_pct": ("APPS_NormalData", "Apps2Interpolated"),
    "inverter_force": ("MPCU_InverterForceRequest", "Force"),
    "motor_rpm": ("MPCU_Values", "MotorRpm"),
    "speed_kmh": ("MPCU_Values", "SpeedKmph"),
    "batt_current_A": ("AMS_Stat", "IsaCurrent"),
    "batt_voltage_V": ("AMS_Stat", "IsaVoltage"),
    "batt_power_W": ("AMS_Stat", "IsaPower"),
    "soc_pct": ("AMS_Stat", "Soc"),
    "pack_voltage_V": ("AMS_Stat", "SumVoltage"),
    "dc_bus_voltage_V": ("MPCU_Values", "BusVoltage"),
    "max_discharge_current_A": ("AMS_AvailableCurrent", "MaxDischargeCurrent"),
    "cell_v_min_V": ("AMS_Stat", "MinVoltage"),
    "cell_v_avg_V": ("AMS_Stat", "AvgVoltage"),
    "cell_v_max_V": ("AMS_Stat", "MaxVoltage"),
    "cell_t_min_C": ("AMS_Stat", "MinTemp"),
    "cell_t_avg_C": ("AMS_Stat", "AvgTemp"),
    "cell_t_max_C": ("AMS_Stat", "MaxTemp"),
    "inverter_temp_C": ("MPCU_Values", "InverterTemperature"),
    "motor_temp_C": ("MPCU_Values", "MotorTemperature"),
}

KIMENETI_OSZLOPOK = (
    ["session", "timestamp", "t_s", "vehicle_state", "vehicle_state_name",
     "apps_pct", "apps1_pct", "apps2_pct", "torque_request_pct", "torque_est_Nm"]
    + [o for o in JELEK if o not in ("vehicle_state", "apps_pct", "apps1_pct",
                                     "apps2_pct", "inverter_force")]
)


# ---------------------------------------------------------------------------
# Dekódolás
# ---------------------------------------------------------------------------

def jelterkep_epitese(db, db_force):
    """frame_id -> (üzenetdefiníció, [(oszlop, jelnév), ...])."""
    jelterkep = {}
    for oszlop, (uzenet_nev, jelnev) in JELEK.items():
        forras = db_force if uzenet_nev == "MPCU_InverterForceRequest" else db
        uzenet = forras.get_message_by_name(uzenet_nev)
        jelterkep.setdefault(uzenet.frame_id, (uzenet, []))[1].append((oszlop, jelnev))
    return jelterkep


def blf_beolvasasa(utvonal, jelterkep):
    """Egy BLF fájl dekódolt jelei: {oszlop: DataFrame[t, oszlop]} és a napló hossza.

    t = a fájl első keretétől eltelt idő másodpercben.
    """
    idok = defaultdict(list)
    ertekek = defaultdict(list)
    t0 = t_utolso = None
    with can.BLFReader(utvonal) as olvaso:
        for keret in olvaso:
            if t0 is None:
                t0 = keret.timestamp
            t_utolso = keret.timestamp
            if keret.is_error_frame or keret.arbitration_id not in jelterkep:
                continue
            uzenet, oszlopok = jelterkep[keret.arbitration_id]
            dekodolt = uzenet.decode(bytes(keret.data), decode_choices=False,
                                     allow_truncated=True)
            t = keret.timestamp - t0
            for oszlop, jelnev in oszlopok:
                if jelnev in dekodolt:
                    idok[oszlop].append(t)
                    ertekek[oszlop].append(dekodolt[jelnev])
    jelsorok = {o: pd.DataFrame({"t": idok[o], o: ertekek[o]}) for o in idok}
    return jelsorok, t_utolso - t0


# ---------------------------------------------------------------------------
# Időrács, aktív szakasz, származtatott oszlopok
# ---------------------------------------------------------------------------

def racsra_igazitas(jelsorok, hossz_s):
    """Közös 10 Hz-es rács; minden jelből a legutóbbi érték (max. TURES_S-ig)."""
    racs = pd.DataFrame({"t": np.round(np.arange(0, hossz_s, 1 / FREKVENCIA_HZ), 3)})
    for oszlop in JELEK:
        if oszlop not in jelsorok:          # az üzenet nem szerepel a naplóban
            racs[oszlop] = np.nan
            continue
        racs = pd.merge_asof(racs, jelsorok[oszlop].sort_values("t"), on="t",
                             direction="backward", tolerance=TURES_S)
    return racs


def aktiv_szakasz(df):
    """Az első R2D előtt ELOTTE_S-tól az utolsó R2D / mozgás után UTANA_S-ig."""
    r2d = df["vehicle_state"] == R2D
    if not r2d.any():
        return None
    aktiv = r2d | (df["speed_kmh"] > MOZGAS_KMH)
    kezdet = df.loc[r2d, "t"].iloc[0] - ELOTTE_S
    veg = df.loc[aktiv, "t"].iloc[-1] + UTANA_S
    return df[(df["t"] >= kezdet) & (df["t"] <= veg)].copy()


def szarmaztatott_oszlopok(df):
    """Nyomatékkérés (%) és akkuteljesítményből becsült nyomaték (Nm).

    torque_request_pct = -Force / 32767 * 100. A Force-t a vezérlő csak R2D
        állapotban küldi, máshol üres.
    torque_est_Nm = P_akku / omega_motor (omega = rpm * 2*pi / 60). Ez az
        elektromos teljesítményből számolt felső becslés (a veszteségeket nem
        vonja le), csak MIN_RPM_NYOMATEKHOZ fölött. A batt_power_W hibás értékei
        átöröklődnek, ezért tisztítás után érdemes újraszámolni.
    """
    df["torque_request_pct"] = -df["inverter_force"] / FORCE_TELJES_SKALA * 100
    omega = df["motor_rpm"] * 2 * np.pi / 60
    df["torque_est_Nm"] = (df["batt_power_W"] / omega).where(
        df["motor_rpm"] > MIN_RPM_NYOMATEKHOZ)
    return df


def tizedesjegyek(jel):
    """A DBC skálatényezőből következő értelmes tizedesjegyszám (0.1 -> 1)."""
    return max(0, -math.floor(math.log10(jel.scale))) if jel.scale < 1 else 0


def formazas(df, db, allapotnevek):
    """Kerekítés a DBC felbontására, egész jelek Int64-ként, állapotnév."""
    for oszlop, (uzenet, jelnev) in JELEK.items():
        if oszlop not in df:
            continue
        jel = db.get_message_by_name(uzenet).get_signal_by_name(jelnev)
        if jel.scale == 1 and jel.offset == 0:
            df[oszlop] = df[oszlop].round().astype("Int64")
        else:
            df[oszlop] = df[oszlop].round(tizedesjegyek(jel))
    df["torque_request_pct"] = df["torque_request_pct"].round(2) + 0.0   # -0.0 -> 0.0
    df["torque_est_Nm"] = df["torque_est_Nm"].round(1)
    df["vehicle_state_name"] = df["vehicle_state"].map(
        lambda v: pd.NA if pd.isna(v) else allapotnevek.get(int(v), f"UNDEFINED_{int(v)}"))
    return df


# ---------------------------------------------------------------------------
# Főprogram
# ---------------------------------------------------------------------------

def fajl_feldolgozasa(fajlnev, db, jelterkep, teljes):
    utvonal = os.path.join(ADAT_MAPPA, fajlnev)
    kezdo_ido = datetime.strptime(os.path.splitext(fajlnev)[0], "%Y-%m-%d %H.%M.%S.%f")

    jelsorok, hossz_s = blf_beolvasasa(utvonal, jelterkep)
    df = racsra_igazitas(jelsorok, hossz_s)
    if not teljes:
        df = aktiv_szakasz(df)
        if df is None:
            print(f"  {fajlnev}: nincs R2D állapot, kimarad")
            return None

    df = szarmaztatott_oszlopok(df)
    df["session"] = kezdo_ido.strftime("%H:%M:%S")
    df["timestamp"] = [(kezdo_ido + timedelta(seconds=t)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                       for t in df["t"]]
    df["t_s"] = (df["t"] - df["t"].iloc[0]).round(1)
    print(f"  {fajlnev}: {len(df)} sor ({df['t'].iloc[0]:.1f}-{df['t'].iloc[-1]:.1f} s a naplóban)")
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fajlok", nargs="+", default=ALAP_FAJLOK,
                        help="BLF fájlnevek a BaseData mappából")
    parser.add_argument("--kimenet", default=KIMENET, help="a kimeneti CSV útvonala")
    parser.add_argument("--teljes", action="store_true",
                        help="a teljes napló kerüljön be, ne csak az aktív szakasz")
    args = parser.parse_args()

    db = cantools.database.load_file(DBC_FAJL, strict=False)
    db_force = cantools.database.load_file(DBC_FORCE_JAVITAS, strict=False)
    jelterkep = jelterkep_epitese(db, db_force)
    allapotnevek = {int(k): str(v) for k, v in
                    db.get_message_by_name("MPCU_VehicleState")
                    .get_signal_by_name("VehicleState").choices.items()}

    print("Dekódolás:")
    reszek = [fajl_feldolgozasa(f, db, jelterkep, args.teljes) for f in args.fajlok]
    df = pd.concat([r for r in reszek if r is not None], ignore_index=True)
    df = formazas(df, db, allapotnevek)[KIMENETI_OSZLOPOK]

    kimenet = os.path.join(MAPPA, args.kimenet)     # relatív név esetén a Beadando mappába
    df.to_csv(kimenet, sep=";", index=False, encoding="utf-8")
    print(f"\nKimenet: {kimenet}")
    print(f"{len(df)} sor x {len(df.columns)} oszlop\n")
    print("Sorok munkamenetenként:", df["session"].value_counts(sort=False).to_dict())
    print("Állapotok:", df["vehicle_state_name"].value_counts(dropna=False).to_dict())
    print("\nOszlopok (kitöltött db, min, max):")
    for oszlop in df.columns[3:]:
        s = df[oszlop]
        if pd.api.types.is_numeric_dtype(s):
            print(f"  {oszlop:25s} {s.notna().sum():5d}  {s.min():>12}  {s.max():>12}")
        else:
            print(f"  {oszlop:25s} {s.notna().sum():5d}")


if __name__ == "__main__":
    main()
