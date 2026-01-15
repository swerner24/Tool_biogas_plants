import geopandas as gpd
import pandas as pd
from nutrients import calculate_nitrogen
from potential_env_imp import calculate_potential_env_imp
from potential import calculate_potential
from Storage_emissions import build_systems_for_polygon
from Storage_emissions import compute_daily_storage_emissions_multi
from Storage_emissions import get_ch4_cum_funcs_from_cardenas
from Storage_emissions import build_season_functions_weibull
from Storage_emissions import  precompute_weights
from Storage_emissions import emissions_for_polygon
import numpy as np
import matplotlib.pyplot as plt
import datetime
import matplotlib.dates as mdates
from scipy.integrate import cumulative_trapezoid
import datetime as dt
import time



f_su_ch4, f_wi_ch4 = get_ch4_cum_funcs_from_cardenas()
f_su_n2o, f_wi_n2o, info_n2o = build_season_functions_weibull()
# Aufteilung der Lagerungssysteme (Summe pro Tier = 1)
storage_share = {
    "Cattle":  {"Slurry": 0.74, "Solid": 0.22, "Deep litter": 0.04},
    "Horses":  {"Solid": 1.0},   # falls Pferde nur feste Lagerung haben
    "Sheep":   {"Solid": 1.0},
    "Goats":   {"Solid": 1.0},
    "Pigs":    {"Slurry": 1.0},
    "Poultry": {"Slurry": 0.61, "Poultry System": 0.39}
}

# Biomethanertrag in m³ CH4 / t Frischmasse
biomethane_yield = {
    "Slurry": {
        "Cattle": 13.8, "Horses": None, "Sheep": None, "Goats": None, "Pigs": 11.3, "Poultry": 72.5
    },
    "Solid": {
        "Cattle": 50.6, "Horses": 83.1, "Sheep": 48.0, "Goats": 48.0, "Pigs": None, "Poultry": None
    },
    "Deep litter": {
        "Cattle": 50.6, "Horses": None, "Sheep": None, "Goats": None, "Pigs": None, "Poultry": None
    },
    "Poultry System manure": {
        "Cattle": None, "Horses": None, "Sheep": None, "Goats": None, "Pigs": None, "Poultry": 101.0
    }
}

# Schweizer Mix (bereits vorgerechnet)
biomethane_yield_ch_mix = {
    "Cattle": 23.4,
    "Horses": 83.1,
    "Sheep": 48.0,
    "Goats": 48.0,
    "Pigs": 11.3,
    "Poultry": 83.6
}

# N-Gehalt (kg N / t Frischmasse)
N_content = {
    "Cattle": 5.0,
    "Horses": 3.9,
    "Sheep": 9.6,
    "Goats": 10.0,
    "Pigs": 5.7,
    "Poultry": 30.7
}
factor_available=1
# Verhältnis
n_plant_available = {
    "Slurry": {
        "Cattle": 0.60*factor_available, "Horses": None, "Sheep": None, "Goats": None, "Pigs": 0.61*factor_available, "Poultry": 0.51*factor_available
    },
    "Solid": {
        "Cattle": 0.40*factor_available, "Horses": 0.125*factor_available, "Sheep": 0.5*factor_available, "Goats": 0.5*factor_available, "Pigs": None, "Poultry": None
    },
    "Deep litter": {
        "Cattle": 0.50*factor_available, "Horses": None, "Sheep": None, "Goats": None, "Pigs": None, "Poultry": None
    },
    "Poultry System": {
        "Cattle": None, "Horses": None, "Sheep": None, "Goats": None, "Pigs": None, "Poultry": 0.52*factor_available
    }
}



#Pre storage emissions

STORAGE_NAME_MAP = {
    "Slurry": "Liquid/slurry",
    "Solid": "Solid storage",
    "Deep litter": "Deep litter",
    "Poultry System": "Poultry system",
}

def _yield_m3_per_t(storage_label, species):
    # holt den m³/t-Ertrag aus deiner biomethane_yield-Matrix
    label = "Poultry System manure" if storage_label == "Poultry System" else storage_label
    return (biomethane_yield.get(label, {}) or {}).get(species, None)

def systems_from_species_masses(species_tonnes, climate_zone, days_summer, days_winter,
                                f_su_ch4, f_wi_ch4, f_su_n2o, f_wi_n2o):
    systems = []
    for sp, tFM in species_tonnes.items():
        if not tFM or tFM <= 0:
            continue
        N_total = N_content[sp] * tFM
        for short, share in storage_share[sp].items():
            y = _yield_m3_per_t(short, sp)
            if y is None or share <= 0:
                continue
            systems.append({
                "species": sp,
                "storage_type": STORAGE_NAME_MAP[short],
                "climate_zone": str(climate_zone),
                "ch4_potential": tFM * share * y,
                "ch4_potential_unit": "Nm3_CH4",
                "total_N_kg_y": N_total * share ,
                "days_summer": days_summer,
                "days_winter": days_winter,
                "CH4_density_kg_per_m3": 0.67,
                "ch4_cum_funcs": (f_su_ch4, f_wi_ch4),
                "n2o_cum_funcs": (f_su_n2o, f_wi_n2o),
            })
    return systems

species_tonnes = {
    "Cattle": 1,
    "Horses": 1,
    "Sheep": 1,
    "Goats": 1,
    "Pigs": 1,
    "Poultry": 1,
}

results_LCA = {
    sp: {
        "pre_storage_CH4": 0,
        "N2O_field": 0,
    }
    for sp in species_tonnes.keys()
}


results_per_species = {}

for sp, tFM in species_tonnes.items():
    if tFM <= 0:
        continue

    systems_sp = systems_from_species_masses(
        {
            sp: tFM},
        "15",
        90,
        180,
        f_su_ch4, f_wi_ch4,
        f_su_n2o, f_wi_n2o
    )

    res_sp = compute_daily_storage_emissions_multi(systems_sp, year=2025)
    # -> Arrays aus dem Ergebnis holen
    dates = res_sp["dates"]
    total_ch4 = res_sp["total"]["ch4_kg_daily"]
    total_n2o = res_sp["total"]["n2o_kg_daily"]

    results_LCA[sp]["pre_storage_CH4"] = float(total_ch4.sum())
    results_LCA[sp]["pre_storage_N2O"] = float(total_n2o.sum())

    results_per_species[sp] = res_sp
    # print(f"\n--- {sp} ---")
    # print("CH4 (kg/year)::", round(float(total_ch4.sum()), 2))
    # print("N2O (kg/year):", round(float(total_n2o.sum()), 2))






#Field application emissions

df_rows = []

for sp, res_sp in results_per_species.items():
    total_n2o = res_sp["total"]["n2o_kg_daily"]
    # --- Storage-N2O (window) ---
    total_n2o_window_kg = total_n2o.sum()
    total_n2o_N_window_kg = total_n2o_window_kg * (28/44)

    # ---- EXACTLY match spreadsheet logic (do NOT subtract storage N2O-N here) ----
    N_initial = N_content[sp]

    # weighted plant-availability fraction per species
    plant_avail_fraction = 0.0
    for short, share in storage_share[sp].items():
        pa = n_plant_available.get(short, {}).get(sp, None)
        if pa is not None:
            plant_avail_fraction += share * pa

    # 1) "N verfügbar kgN" (sheet): N_initial * frac * 0.5
    N_available = (N_initial - total_n2o_N_window_kg) * plant_avail_fraction * 0.5

    # 2) NH3 emissions (kg NH3-N) = N_available * 0.5 *0.7
    NH3_N = N_available * 0.5*0.7

    # 3) N2O after land application (kg N2O/t)
    N2O_after = (N_available - NH3_N) * 0.1  * (44 / 28)

    results_LCA[sp]["N2O_field"] = N2O_after

    df_rows.append({
        "species": sp,
        "N_initial (kg N/t)": round(N_initial, 4),
        "Plant availability ratio": round(plant_avail_fraction, 4),
        "N verfügbar kgN": round(N_available, 4),
        "NH3 emissions kg NH3-N": round(NH3_N, 4),
        "N2O emissions kg N2O": round(N2O_after, 4),
    })



df = pd.DataFrame(df_rows)
#print(df.to_string(index=False))

#Total LCA:
GWP_CH4=27
GWP_N2O=273


for sp in results_LCA:
    Pre_storage = (results_LCA[sp]["pre_storage_CH4"] *GWP_CH4) + (results_LCA[sp]["pre_storage_N2O"] *GWP_N2O)

    Field_application=(results_LCA[sp]["N2O_field"]*GWP_N2O)

    GWP_total=Pre_storage+Field_application

# Komponenten zurückschreiben (optional, aber praktisch)
    results_LCA[sp]["GWP_prestorage"] = Pre_storage
    results_LCA[sp]["GWP_field_application"] = Field_application
    results_LCA[sp]["GWP_Total"] = GWP_total




# Übersichtstabelle (nur relevante Spalten)
cols = [
    "GWP_prestorage",
    "GWP_field_application",
    "GWP_Total",
]


pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)
df_lca = pd.DataFrame(results_LCA).T.reindex(columns=cols)
#print(df_lca.round(4))