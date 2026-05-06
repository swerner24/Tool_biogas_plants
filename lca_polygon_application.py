import geopandas as gpd
import pandas as pd
import numpy as np

from nutrients import calculate_nitrogen
from potential_env_imp import calculate_potential_env_imp
from potential import calculate_potential
from Storage_emissions import (
    build_systems_for_polygon,
    compute_daily_storage_emissions_multi,
    precompute_weights,
    emissions_for_polygon,
    get_ch4_cum_funcs_from_cardenas,
    build_season_functions_weibull,
)
from lca_chp import precompute_chp_lca_factors_for_climate
from lca_upgrading import precompute_upgrading_lca_factors_for_climate
from lca_baseline import precompute_baseline_lca_factors_for_climate

# =============================================================================
# CONSTANTS
# =============================================================================

input_shapefile = "data/Polygons_Cantonal_Climate_WGS_1984.shp"

N_content = {
    "Cattle":  5.0,
    "Horses":  3.9,
    "Sheep":   9.6,
    "Goats":  10.0,
    "Pigs":    5.7,
    "Poultry": 30.7,
}

factor_available = 1

n_plant_available = {
    "Slurry": {
        "Cattle": 0.60 * factor_available,
        "Horses": None,
        "Sheep":  None,
        "Goats":  None,
        "Pigs":   0.61 * factor_available,
        "Poultry":0.51 * factor_available,
    },
    "Solid": {
        "Cattle": 0.40 * factor_available,
        "Horses": 0.125 * factor_available,
        "Sheep":  0.5 * factor_available,
        "Goats":  0.5 * factor_available,
        "Pigs":   None,
        "Poultry":None,
    },
    "Deep litter": {
        "Cattle": 0.50 * factor_available,
        "Horses": None, "Sheep": None, "Goats": None, "Pigs": None, "Poultry": None,
    },
    "Poultry System": {
        "Cattle": None, "Horses": None, "Sheep": None, "Goats": None, "Pigs": None,
        "Poultry": 0.52 * factor_available,
    },
}

storage_share = {
    "Cattle":  {"Slurry": 0.74, "Solid": 0.22, "Deep litter": 0.04},
    "Horses":  {"Solid": 1.0},
    "Sheep":   {"Solid": 1.0},
    "Goats":   {"Solid": 1.0},
    "Pigs":    {"Slurry": 1.0},
    "Poultry": {"Slurry": 0.61, "Poultry System": 0.39},
}

SPECIES = ["Cattle", "Horses", "Sheep", "Goats", "Pigs", "Poultry"]

# Plant availability fraction per species (weighted over storage shares) — computed once
PLANT_AVAIL_FRAC = {}
for sp in SPECIES:
    frac = 0.0
    for short, share in storage_share[sp].items():
        pa = n_plant_available.get(short, {}).get(sp, None)
        if pa is not None:
            frac += share * pa
    PLANT_AVAIL_FRAC[sp] = frac

SPECIES_FM_COLS = {
    "Cattle":  "FM_total_t_cattle_av",
    "Horses":  "FM_total_t_horses_av",
    "Sheep":   "FM_total_t_sheep_av",
    "Goats":   "FM_total_t_goats_av",
    "Pigs":    "FM_total_t_pigs_av",
    "Poultry": "FM_total_t_poultry_av",
}

# =============================================================================
# OPT 1: Module-level caches — computed ONCE, reused across all calls
# =============================================================================

# CH4 and N2O curve functions — expensive, computed once at import
_f_su_ch4, _f_wi_ch4 = get_ch4_cum_funcs_from_cardenas()
_f_su_n2o, _f_wi_n2o, _info_n2o = build_season_functions_weibull()

# Weights cache: keyed by (days_summer, days_winter)
_weights_cache = {}

# Data caches: each shapefile computed only once
_potential_env_imp_cache = {}
_nitrogen_cache = {}

# CHP/Upgrading LCA factor caches: keyed by (cz, days_pre, days_post, heat_usage)
_chp_factors_cache = {}
_upg_factors_cache = {}
_baseline_factors_cache = {}


def _get_potential_env_imp(shapefile):
    """Cached call to calculate_potential_env_imp."""
    if shapefile not in _potential_env_imp_cache:
        result = calculate_potential_env_imp(shapefile)
        _potential_env_imp_cache[shapefile] = result
    r = _potential_env_imp_cache[shapefile]
    return r[0].copy(), *r[1:]


def _get_nitrogen(shapefile):
    """Cached call to calculate_nitrogen."""
    if shapefile not in _nitrogen_cache:
        _nitrogen_cache[shapefile] = calculate_nitrogen(shapefile)
    return _nitrogen_cache[shapefile].copy()


def _get_weights(days_summer, days_winter=180):
    """Cached call to precompute_weights."""
    key = (days_summer, days_winter)
    if key not in _weights_cache:
        _weights_cache[key] = precompute_weights(
            days_summer, days_winter,
            _f_su_ch4, _f_wi_ch4,
            _f_su_n2o, _f_wi_n2o,
        )
    return _weights_cache[key]


# =============================================================================
# MAIN EMISSION FUNCTION
# =============================================================================

def calculate_emissions(input_shapefile, days_summer):
    days_winter = 180

    # OPT: all three calls are now cached
    gdf_potential, methane_1, x1 = _get_potential_env_imp(input_shapefile)
    gdf_nitrogen                  = _get_nitrogen(input_shapefile)
    gdf_shares, *_rest            = calculate_potential(input_shapefile)   # cached in potential.py

    # Rename climate zone column (handle different spellings)
    gdf_shares = gdf_shares.rename(columns={
        "Climatezon": "climate_zone",
        "Klimazone":  "climate_zone",
        "climateZone":"climate_zone",
    })

    cols_needed = [
        "Share_liquid/slurry",
        "Share_solid_storage",
        "Share_deep_litter",
        "Share_poultry_system",
        "climate_zone",
    ]
    gdf_selected = gdf_shares[cols_needed]

    # Merge potential + nitrogen + shares
    gdf_main = gdf_potential.merge(
        gdf_nitrogen[["Total_avail_N_kg"]],
        left_index=True, right_index=True, how="left",
    )
    gdf_main = gdf_main.merge(
        gdf_selected,
        left_index=True, right_index=True, how="left",
    )

    gdf_main["climate_zone"] = gdf_main["climate_zone"].astype(float).astype(int).astype(str)
    gdf_main = gdf_main.rename(columns={"Share_liquid/slurry": "Share_liquid_slurry"})

    # OPT: weights computed once and cached
    weights = _get_weights(days_summer, days_winter)

    # Emissions per polygon (vectorized within emissions_for_polygon)
    gdf_main[["ch4_cut_kg", "n2o_cut_kg"]] = gdf_main.apply(
        lambda row: pd.Series(emissions_for_polygon(row, weights, days_summer, days_winter)),
        axis=1,
    )

    GWP100_CH4 = 27
    GWP100_N2O = 273

    gdf_main["Total_GWP100_CO2eq_prestorage"] = (
        gdf_main["ch4_cut_kg"] * GWP100_CH4
        + gdf_main["n2o_cut_kg"] * GWP100_N2O
    )

    return gdf_main


# =============================================================================
# FIELD N2O (vectorized)
# =============================================================================

def compute_field_n2o_vectorized(gdf):
    """
    Adds column N2O_field_kg using fully vectorized operations.
    Requires: gdf['n2o_cut_kg'] and FM_total_t_*_av columns.
    """
    fm_mat     = np.column_stack([gdf[col].to_numpy(dtype=float) for col in SPECIES_FM_COLS.values()])
    total_fm   = fm_mat.sum(axis=1)

    n2o_storage_total = gdf["n2o_cut_kg"].to_numpy(dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        shares = np.where(total_fm[:, None] > 0, fm_mat / total_fm[:, None], 0.0)

    n2o_field_total = np.zeros(len(gdf), dtype=float)
    conv_N2O_to_N   = 28 / 44

    for j, (sp, col) in enumerate(SPECIES_FM_COLS.items()):
        tFM_sp       = fm_mat[:, j]
        storage_n2o  = n2o_storage_total * shares[:, j]
        storage_n2o_N= storage_n2o * conv_N2O_to_N

        N_initial    = N_content[sp] * tFM_sp
        frac         = PLANT_AVAIL_FRAC[sp]
        N_available  = np.maximum((N_initial - storage_n2o_N) * frac * 0.5, 0.0)
        NH3_N        = N_available * 0.5 * 0.7
        N2O_after    = np.maximum((N_available - NH3_N) * 0.1 * (44 / 28), 0.0)

        n2o_field_total += N2O_after

    gdf["N2O_field_kg"] = n2o_field_total
    return gdf


# =============================================================================
# CHP PATHWAY
# =============================================================================

def apply_chp_emissions_to_polygons(gdf_main, days_prestorage, days_poststorage,
                                     external_heat_usage, heat_substitution_oil=0.0125):
    """Adds CHP pathway GWP100 emissions per polygon (kg CO2-eq).
    heat_substitution_oil: kgCO2/MJ (default=0.0125 natural gas, use 0.102 for oil)
    """

    gdf_main["climate_zone"] = gdf_main["climate_zone"].astype(float).astype(int).astype(str)
    cz_list = sorted(gdf_main["climate_zone"].dropna().unique().tolist())

    # OPT: cache LCA factors per (cz, prestorage, poststorage, heat)
    cz_to_factors = {}
    for cz in cz_list:
        key = (cz, days_prestorage, days_poststorage, round(external_heat_usage, 4),
               round(heat_substitution_oil, 4))
        if key not in _chp_factors_cache:
            _chp_factors_cache[key] = precompute_chp_lca_factors_for_climate(
                climate_zone=cz,
                days_pre_summer=days_prestorage,
                days_post_summer=days_poststorage,
                external_heat_usage=external_heat_usage,
                heat_substitution=heat_substitution_oil,
            )
        cz_to_factors[cz] = _chp_factors_cache[key]

    comp_names = [
        "GWP_prestorage", "GWP_transport", "GWP_AD_methane_losses",
        "GWP_AD_construction_operation", "GWP_CHP_construction_operation",
        "GWP_poststorage", "GWP_field_application", "GWP_energy_benefits",
    ]

    total        = np.zeros(len(gdf_main), dtype=float)
    comp_arrays  = {k: np.zeros(len(gdf_main), dtype=float) for k in comp_names}
    cz_arr       = gdf_main["climate_zone"].to_numpy()

    for cz in cz_list:
        idx     = np.where(cz_arr == cz)[0]
        if len(idx) == 0:
            continue
        factors = cz_to_factors[cz]

        for sp, col in SPECIES_FM_COLS.items():
            tFM_cz = gdf_main[col].to_numpy(dtype=float)[idx]
            total[idx] += tFM_cz * factors[sp]["GWP_Total_kgCO2eq_per_tFM"]
            for comp in comp_names:
                comp_arrays[comp][idx] += tFM_cz * factors[sp][comp]

    gdf_main["GWP100_total_CHP_CO2eq"] = total
    for comp, arr in comp_arrays.items():
        gdf_main[f"CHP_{comp}_CO2eq"] = arr

    return gdf_main


# =============================================================================
# UPGRADING PATHWAY
# =============================================================================

def apply_upgrading_emissions_to_polygons(gdf_main, days_prestorage, days_poststorage):
    """Adds upgrading pathway GWP100 emissions per polygon (kg CO2-eq)."""

    gdf_main["climate_zone"] = gdf_main["climate_zone"].astype(float).astype(int).astype(str)
    cz_list = sorted(gdf_main["climate_zone"].dropna().unique().tolist())

    # OPT: cache LCA factors per (cz, prestorage, poststorage)
    cz_to_factors = {}
    for cz in cz_list:
        key = (cz, days_prestorage, days_poststorage)
        if key not in _upg_factors_cache:
            _upg_factors_cache[key] = precompute_upgrading_lca_factors_for_climate(
                climate_zone=cz,
                days_pre_summer=days_prestorage,
                days_post_summer=days_poststorage,
            )
        cz_to_factors[cz] = _upg_factors_cache[key]

    comp_names = [
        "GWP_prestorage", "GWP_transport", "GWP_AD_methane_losses",
        "GWP_AD_construction_operation", "GWP_Upgrading_construction_operation",
        "GWP_poststorage", "GWP_field_application", "GWP_energy_benefits",
    ]

    total       = np.zeros(len(gdf_main), dtype=float)
    comp_arrays = {k: np.zeros(len(gdf_main), dtype=float) for k in comp_names}
    cz_arr      = gdf_main["climate_zone"].to_numpy()

    for cz in cz_list:
        idx = np.where(cz_arr == cz)[0]
        if len(idx) == 0:
            continue
        factors = cz_to_factors[cz]

        for sp, col in SPECIES_FM_COLS.items():
            tFM_cz = gdf_main[col].to_numpy(dtype=float)[idx]
            total[idx] += tFM_cz * factors[sp]["GWP_Total_kgCO2eq_per_tFM"]
            for comp in comp_names:
                comp_arrays[comp][idx] += tFM_cz * factors[sp][comp]

    gdf_main["GWP100_total_UPG_CO2eq"] = total
    for comp, arr in comp_arrays.items():
        gdf_main[f"UPG_{comp}_CO2eq"] = arr

    return gdf_main


def apply_baseline_emissions_to_polygons(gdf_main, days_summer):
    """
    Adds no-energy-recovery baseline GWP100 emissions per polygon (kg CO2-eq),
    using species-specific per-tonne factors.
    """

    gdf_main = gdf_main.copy()

    gdf_main["climate_zone"] = (
        gdf_main["climate_zone"]
        .astype(float)
        .astype(int)
        .astype(str)
    )

    cz_list = sorted(gdf_main["climate_zone"].dropna().unique().tolist())

    cz_to_factors = {}

    for cz in cz_list:
        key = (cz, int(days_summer))

        if key not in _baseline_factors_cache:
            _baseline_factors_cache[key] = precompute_baseline_lca_factors_for_climate(
                climate_zone=cz,
                days_summer=int(days_summer),
                days_winter=180,
            )

        cz_to_factors[cz] = _baseline_factors_cache[key]

    total = np.zeros(len(gdf_main), dtype=float)
    storage = np.zeros(len(gdf_main), dtype=float)
    field = np.zeros(len(gdf_main), dtype=float)

    cz_arr = gdf_main["climate_zone"].to_numpy()

    for cz in cz_list:
        idx = np.where(cz_arr == cz)[0]

        if len(idx) == 0:
            continue

        factors = cz_to_factors[cz]

        for sp, col in SPECIES_FM_COLS.items():
            if col not in gdf_main.columns:
                continue

            tFM_cz = gdf_main[col].to_numpy(dtype=float)[idx]

            total[idx] += tFM_cz * factors[sp]["GWP_Total_kgCO2eq_per_tFM"]
            storage[idx] += tFM_cz * factors[sp]["GWP_storage"]
            field[idx] += tFM_cz * factors[sp]["GWP_field_application"]

    gdf_main["GWP100_total_noRec_kg"] = total
    gdf_main["GWP100_total_noRec_t"] = total / 1000.0

    gdf_main["BASE_GWP_storage_CO2eq"] = storage
    gdf_main["BASE_GWP_field_application_CO2eq"] = field

    return gdf_main