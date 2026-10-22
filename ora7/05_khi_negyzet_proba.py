# -*- coding: utf-8 -*-
"""5. Khi-négyzet próba.

Bemenet: student_performance_cleaned.csv (tisztított, nem imputált)

Kérdés: összefügg-e a képzési program azzal, hogy a hallgató sikeresen
teljesítette-e a vizsgát?

H0: a program és a sikeresség független (a sikeres teljesítés sokasági
    aránya minden programban azonos).
H1: nem függetlenek (legalább két programban eltér az arány). α = 0,05.
Feltétel: a megfigyelések függetlensége; a normalitás és a varianciák
homogenitása nem feltétel.
"""

import pandas as pd
from scipy import stats

from proba_kozos import ALFA, beolvas, cim, dontes


def main():
    df = beolvas()
    adat = df.dropna(subset=["programme", "passed"])

    cim("1. Hipotézisek")
    print("  H0: a képzési program és a vizsga sikeressége független")
    print("  H1: a két változó nem független")
    print("  α = {}".format(ALFA))

    cim("2. Kereszttábla (megfigyelt gyakoriságok)")
    print("Felhasznált rekordok (ismert program és passed): {}".format(len(adat)))
    megfigyelt = pd.crosstab(adat["programme"], adat["passed"])
    print(megfigyelt.to_string())

    cim("3. Khi-négyzet próba")
    eredmeny = stats.chi2_contingency(megfigyelt)
    print("χ² = {:.3f}, szabadságfok = {}, p = {:.4f}".format(
        eredmeny.statistic, eredmeny.dof, eredmeny.pvalue))

    cim("4. Döntés")
    print(dontes(eredmeny.pvalue))
    if eredmeny.pvalue <= ALFA:
        print("A képzési program és a vizsga sikeressége összefügg.")
    else:
        print("Nem mutatható ki összefüggés a képzési program és a vizsga sikeressége között.")


if __name__ == "__main__":
    main()
