import geopandas as gpd
import pandas as pd
from nutrients import calculate_nitrogen
from nutrients import calculate_phosphorus
from potential_env_imp import calculate_potential_env_imp
from potential import calculate_potential
from Storage_emissions import build_systems_for_polygon
from Storage_emissions import compute_daily_storage_emissions_multi
from Storage_emissions import  precompute_weights
from Storage_emissions import emissions_for_polygon
from lca_per_tonne_sensitivity_pw2 import precompute_chp_lca_factors_for_climate
from lca_per_tonne_sensitivity_pw3 import precompute_upgrading_lca_factors_for_climate
import numpy as np
import matplotlib.pyplot as plt
import datetime
import matplotlib.dates as mdates
from scipy.integrate import cumulative_trapezoid
import datetime as dt




input_shapefile = "data/Polygons_Cantonal_Climate_WGS_1984.shp"

calc_columns = {}
#-------------------

potential_env_imp, methane,x1= calculate_potential_env_imp(input_shapefile)


#-------Prep.---------------------------------

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
# Aufteilung der Lagerungssysteme (Summe pro Tier = 1)
storage_share = {
    "Cattle":  {"Slurry": 0.74, "Solid": 0.22, "Deep litter": 0.04},
    "Horses":  {"Solid": 1.0},   # falls Pferde nur feste Lagerung haben
    "Sheep":   {"Solid": 1.0},
    "Goats":   {"Solid": 1.0},
    "Pigs":    {"Slurry": 1.0},
    "Poultry": {"Slurry": 0.61, "Poultry System": 0.39}
}

# Pre-Compute plant availability per sepcies
SPECIES = ["Cattle", "Horses", "Sheep", "Goats", "Pigs", "Poultry"]

# plant availability fraction per species (weighted over storage shares)
PLANT_AVAIL_FRAC = {}
for sp in SPECIES:
    frac = 0.0
    for short, share in storage_share[sp].items():
        pa = n_plant_available.get(short, {}).get(sp, None)
        if pa is not None:
            frac += share * pa
    PLANT_AVAIL_FRAC[sp] = frac


#----------------------------------------
#Berechnung
nitrogen= calculate_nitrogen(input_shapefile)


#print(f'Total nitrogeeeeeeen [kg]: {Swiss_aggregated_nitrogen_theor}')
#print(f'Total nitrogeeeeeeen [kg]: {Swiss_aggregated_nitrogen_avail}')
#print(f'Total nitrogeeeeeeen [kg]: {Swiss_aggregated_nitrogen_onpasture}')

#print(f"Total nitrogeeeeeeen Cattle 1[kg]: {nitrogen['Cattle_1_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Cattle 2[kg]: {nitrogen['Cattle_2_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Cattle 3[kg]: {nitrogen['Cattle_3_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Cattle 4[kg]: {nitrogen['Cattle_4_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Cattle 5[kg]: {nitrogen['Cattle_5_avail'].sum()}")

#print(f"Total nitrogeeeeeeen Horse 1[kg]: {nitrogen['Horses_1_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Horse 2[kg]: {nitrogen['Horses_2_avail'].sum()}")

#print(f"Total nitrogeeeeeeen Sheep 1[kg]: {nitrogen['Sheep_1_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Sheep 2[kg]: {nitrogen['Sheep_2_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Goats [kg]: {nitrogen['Goats_avail'].sum()}")

#print(f"Total nitrogeeeeeeen Pigs 1[kg]: {nitrogen['Pigs_1_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Pigs 2[kg]: {nitrogen['Pigs_2_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Pigs 3 [kg]: {nitrogen['Pigs_3_avail'].sum()}")

#print(f"Total nitrogeeeeeeen Poultry 1[kg]: {nitrogen['Poultry_1_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Poultry 2[kg]: {nitrogen['Poultry_2_avail'].sum()}")
#print(f"Total nitrogeeeeeeen Poultry 3[kg]: {nitrogen['Poultry_3_avail'].sum()}")






def calculate_emissions(input_shapefile, days_summer):
    days_winter=180
    # 1. Potenzial berechnen
    gdf_potential, methane_1,x1 = calculate_potential_env_imp(input_shapefile)

    # 2. Stickstoff berechnen
    gdf_nitrogen = calculate_nitrogen(input_shapefile)

    # 3. Shares berechnen (falls noch nicht gemacht)
    gdf_shares,fm_totals, dm_totals, x1, x2, x3, x4, x5, x6 = calculate_potential(input_shapefile)

    # After creating gdf_main
    gdf_shares = gdf_shares.rename(columns={
        "Climatezon": "climate_zone",
        "Klimazone": "climate_zone",
        "climateZone": "climate_zone"
    })


    #print("Columns in gdf_shares:", gdf_shares.columns.tolist())

    # nur bestimmte Spalten behalten
    cols_needed = [
        "Share_liquid/slurry",
        "Share_solid_storage",
        "Share_deep_litter",
        "Share_poultry_system",
        "climate_zone",
    ]

    gdf_selected = gdf_shares[cols_needed]

    # 4. Zusammenführen nach Polygon-ID
    gdf_main = gdf_potential.merge(
        gdf_nitrogen[['Total_avail_N_kg']],  # keine geometry doppelt
        left_index=True, right_index=True, how="left"
    )

    gdf_main = gdf_main.merge(
        gdf_selected,
        left_index=True, right_index=True, how="left"
    )

    gdf_main["climate_zone"] = gdf_main["climate_zone"].astype(float).astype(int).astype(str)

    gdf_main = gdf_main.rename(columns={
        "Share_liquid/slurry": "Share_liquid_slurry",
        "Share_solid_storage": "Share_solid_storage",
        "Share_deep_litter": "Share_deep_litter",
        "Share_poultry_system": "Share_poultry_system"
    })

    # CH4-Kurven (Cárdenas)
    from Storage_emissions import get_ch4_cum_funcs_from_cardenas
    f_su_ch4, f_wi_ch4 = get_ch4_cum_funcs_from_cardenas()

    # N2O-Kurven (Weibull-Fit)
    from Storage_emissions import build_season_functions_weibull
    f_su_n2o, f_wi_n2o, info_n2o = build_season_functions_weibull()

    weights_cache = {}
    key = (days_summer, days_winter)
    if key not in weights_cache:
        weights_cache[key] = precompute_weights(days_summer, days_winter, f_su_ch4, f_wi_ch4, f_su_n2o, f_wi_n2o)
    w_su_ch4, w_wi_ch4, w_su_n2o, w_wi_n2o = weights_cache[key]


    # nur 1x vorberechnen
    weights = precompute_weights(days_summer, days_winter, f_su_ch4, f_wi_ch4, f_su_n2o, f_wi_n2o)

    # dann pro Polygon:
    gdf_main[["ch4_cut_kg", "n2o_cut_kg"]] = gdf_main.apply(
        lambda row: pd.Series(emissions_for_polygon(row, weights, days_summer, days_winter)),
        axis=1
    )


    # --- Aggregation ---
    total_ch4_cut = gdf_main["ch4_cut_kg"].sum()
    total_n2o_cut = gdf_main["n2o_cut_kg"].sum()

    GWP100_CH4_factor = 27
    GWP100_N2O_factor = 273


    #print("\n=== Cut (only active days) ===")
    #print(f"Total CH₄ [t]: {total_ch4_cut/1000:.1f}")
    #print(f"Total N₂O [t]: {total_n2o_cut/1000:.1f}")
    # print(f"Total CH₄ GWP100 [kt CO₂-eq]: {total_ch4_cut*GWP100_CH4_factor/1e6:.3f}")
    #print(f"Total N₂O GWP100 [kt CO₂-eq]: {total_n2o_cut*GWP100_N2O_factor/1e6:.3f}")

    gdf_main["Total_GWP100_CO2eq_prestorage"] = (
            gdf_main["ch4_cut_kg"] * GWP100_CH4_factor +
            gdf_main["n2o_cut_kg"] * GWP100_N2O_factor
    )




    return gdf_main




SPECIES_FM_COLS = {
    "Cattle":  "FM_total_t_cattle_av",
    "Horses":  "FM_total_t_horses_av",
    "Sheep":   "FM_total_t_sheep_av",
    "Goats":   "FM_total_t_goats_av",
    "Pigs":    "FM_total_t_pigs_av",
    "Poultry": "FM_total_t_poultry_av",
}

def compute_field_n2o_vectorized(gdf):
    """
    Adds column N2O_field_kg using vectorized operations (fast).
    Requires:
      - gdf["n2o_cut_kg"]  : total storage N2O per polygon (kg)
      - FM_total_t_*_av cols for each species
    """
    # total FM per polygon
    fm_mat = np.column_stack([gdf[col].to_numpy(dtype=float) for col in SPECIES_FM_COLS.values()])
    total_fm = fm_mat.sum(axis=1)

    n2o_storage_total = gdf["n2o_cut_kg"].to_numpy(dtype=float)

    # avoid divide-by-zero
    with np.errstate(divide="ignore", invalid="ignore"):
        shares = np.where(total_fm[:, None] > 0, fm_mat / total_fm[:, None], 0.0)

    n2o_field_total = np.zeros(len(gdf), dtype=float)

    # constants
    conv_N2O_to_N = 28/44

    for j, (sp, col) in enumerate(SPECIES_FM_COLS.items()):
        tFM_sp = fm_mat[:, j]  # tonnes FM in polygon for this species

        # allocate storage N2O to species (kg)
        storage_n2o_sp = n2o_storage_total * shares[:, j]
        storage_n2o_N = storage_n2o_sp * conv_N2O_to_N

        # N entering land application (kg N)
        N_initial_total = N_content[sp] * tFM_sp

        frac = PLANT_AVAIL_FRAC[sp]

        # N available (kg N)
        N_available = (N_initial_total - storage_n2o_N) * frac * 0.5
        N_available = np.maximum(N_available, 0.0)

        # NH3-N (kg)
        NH3_N = N_available * 0.5 * 0.7

        # N2O after application (kg N2O)
        N2O_after = (N_available - NH3_N) * 0.1 * (44/28)
        N2O_after = np.maximum(N2O_after, 0.0)

        n2o_field_total += N2O_after

    gdf["N2O_field_kg"] = n2o_field_total
    return gdf


def apply_chp_emissions_to_polygons(gdf_main, days_prestorage, days_poststorage, external_heat_usage):
    """
    Adds CHP pathway emissions per polygon (kg CO2-eq).
    Assumes gdf_main contains climate_zone + FM_total_t_*_av columns.
    """

    # make sure climate_zone is string (like "14","15"...)
    gdf_main["climate_zone"] = gdf_main["climate_zone"].astype(float).astype(int).astype(str)

    # precompute factors for each climate zone present
    cz_list = sorted(gdf_main["climate_zone"].dropna().unique().tolist())
    cz_to_factors = {}

    for cz in cz_list:
        cz_to_factors[cz] = precompute_chp_lca_factors_for_climate(
            climate_zone=cz,
            days_pre_summer=days_prestorage,
            days_post_summer=days_poststorage,
            external_heat_usage=  external_heat_usage      ,
        )

    # allocate arrays
    total = np.zeros(len(gdf_main), dtype=float)
    comp_arrays = {k: np.zeros(len(gdf_main), dtype=float) for k in [
        "GWP_prestorage","GWP_transport","GWP_AD_methane_losses",
        "GWP_AD_construction_operation","GWP_CHP_construction_operation",
        "GWP_poststorage","GWP_field_application","GWP_energy_benefits"
    ]}

    # loop climate zones (vectorized within each cz group)
    for cz in cz_list:
        idx = np.where(gdf_main["climate_zone"].to_numpy() == cz)[0]
        if len(idx) == 0:
            continue

        factors = cz_to_factors[cz]  # factors[sp][component]

        # for each species, scale by tonnes
        for sp, col in SPECIES_FM_COLS.items():
            tFM = gdf_main[col].to_numpy(dtype=float)
            tFM_cz = tFM[idx]

            total[idx] += tFM_cz * factors[sp]["GWP_Total_kgCO2eq_per_tFM"]

            for comp in comp_arrays.keys():
                comp_arrays[comp][idx] += tFM_cz * factors[sp][comp]

    gdf_main["GWP100_total_CHP_CO2eq"] = total

    for comp, arr in comp_arrays.items():
        gdf_main[f"CHP_{comp}_CO2eq"] = arr

    return gdf_main


def apply_upgrading_emissions_to_polygons(
    gdf_main,
    days_prestorage: int,
    days_poststorage: int,
):
    # climate_zone string
    gdf_main["climate_zone"] = gdf_main["climate_zone"].astype(float).astype(int).astype(str)

    cz_list = sorted(gdf_main["climate_zone"].dropna().unique().tolist())
    cz_to_factors = {}

    for cz in cz_list:
        cz_to_factors[cz] = precompute_upgrading_lca_factors_for_climate(
            climate_zone=cz,
            days_pre_summer=days_prestorage,
            days_post_summer=days_poststorage,
        )

    total = np.zeros(len(gdf_main), dtype=float)

    comp_names = [
        "GWP_prestorage",
        "GWP_transport",
        "GWP_AD_methane_losses",
        "GWP_AD_construction_operation",
        "GWP_Upgrading_construction_operation",
        "GWP_poststorage",
        "GWP_field_application",
        "GWP_energy_benefits",
    ]
    comp_arrays = {k: np.zeros(len(gdf_main), dtype=float) for k in comp_names}

    for cz in cz_list:
        idx = np.where(gdf_main["climate_zone"].to_numpy() == cz)[0]
        if len(idx) == 0:
            continue

        factors = cz_to_factors[cz]

        for sp, col in SPECIES_FM_COLS.items():
            tFM = gdf_main[col].to_numpy(dtype=float)
            tFM_cz = tFM[idx]

            total[idx] += tFM_cz * factors[sp]["GWP_Total_kgCO2eq_per_tFM"]

            for comp in comp_names:
                comp_arrays[comp][idx] += tFM_cz * factors[sp][comp]

    gdf_main["GWP100_total_UPG_CO2eq"] = total  # kg CO2-eq

    for comp, arr in comp_arrays.items():
        gdf_main[f"UPG_{comp}_CO2eq"] = arr

    return gdf_main