import geopandas as gpd
import pandas as pd

# =============================================================================
# CONSTANTS
# =============================================================================

CV_lower_oDM     = 21       # MJ/kg oDM (Thees et al., 2017)
CV_lower_methane = 35.883   # MJ/m3    (Thees et al., 2017)

# --- Cattle ------------------------------------------------------------------
manure_production_cattle = {
    "cattle_1": {"s": 23,  "sm1": 11,  "sm2": 8.9, "m": 21},
    "cattle_2": {"s": 17,  "sm1": 8.7, "sm2": 6.7, "m": 16},
    "cattle_3": {"s": 8,   "sm1": 4,   "sm2": 3.2, "m": 7.6},
    "cattle_4": {"s": 4.8, "sm1": 2.4, "sm2": 2,   "m": 4.6},
    "cattle_5": {"s": 10,  "sm1": 0,   "sm2": 0,   "m": 11},
}

stable_system_cattle = {
    "cattle_1": [0.13, 0.29, 0.45, 0.12, 0.01],
    "cattle_2": [0.03, 0.13, 0.28, 0.51, 0.05],
    "cattle_3": [0.03, 0.20, 0.31, 0.39, 0.07],
    "cattle_4": [0.01, 0.17, 0.19, 0.50, 0.13],
    "cattle_5": [0.01, 0.12, 0.21, 0.57, 0.08],
}

categories_cattle_stable = {
    "only_slurry":   [0, 2],
    "manure_slurry": [1, 3],
    "only_manure":   [4],
}

stable_cattle_total = {
    cattle: {
        category: round(sum(stable_system_cattle[cattle][i] for i in indices), 2)
        for category, indices in categories_cattle_stable.items()
    }
    for cattle in stable_system_cattle
}

# --- Other livestock ---------------------------------------------------------
manure_production_horse = {
    "horse_1": {"s": 0, "sm1": 0, "sm2": 0, "m": 10},
    "horse_2": {"s": 0, "sm1": 0, "sm2": 0, "m": 12},
}

manure_production_sheep = {
    "sheep_1": {"s": 0, "sm1": 0, "sm2": 0, "m": 2.3},
    "sheep_2": {"s": 0, "sm1": 0, "sm2": 0, "m": 1.7},
}

manure_production_goats = {
    "goats": {"s": 0, "sm1": 0, "sm2": 0, "m": 1.7},
}

manure_production_pigs = {
    "pigs_1": {"s": 7.5, "sm1": 0, "sm2": 0, "m": 0},
    "pigs_2": {"s": 7.5, "sm1": 0, "sm2": 0, "m": 0},
    "pigs_3": {"s": 1.6, "sm1": 0, "sm2": 0, "m": 0},
}

manure_production_poultry = {
    "poultry_1": {"s": 2.7, "sm1": 0, "sm2": 0, "m": 1.5},
    "poultry_2": {"s": 0,   "sm1": 0, "sm2": 0, "m": 0.8},
    "poultry_3": {"s": 0,   "sm1": 0, "sm2": 0, "m": 3},
}

stable_system_poultry = {
    "poultry_1": {"floor_system": 0.1, "manure_belt": 0.9},
}

DM_oDM = {
    "slurry_cattle":          {"DM": 90,  "oDM": 70},
    "slurry_lowstraw_cattle": {"DM": 75,  "oDM": 40},
    "manure_cattle":          {"DM": 210, "oDM": 175},
    "manure_cattle_4":        {"DM": 200, "oDM": 150},
    "liquid_cattle_5":        {"DM": 90,  "oDM": 65},
    "manure_cattle_5":        {"DM": 210, "oDM": 155},
    "manure_horse":           {"DM": 350, "oDM": 300},
    "manure_sheep":           {"DM": 270, "oDM": 200},
    "manure_goat":            {"DM": 270, "oDM": 200},
    "pigs":                   {"DM": 50,  "oDM": 33},
    "pigs_3":                 {"DM": 50,  "oDM": 36},
    "poultry_1_manurebelt":   {"DM": 350, "oDM": 250},
    "poultry_1_floorsystem":  {"DM": 500, "oDM": 330},
    "poultry_2":              {"DM": 650, "oDM": 440},
    "poultry_3":              {"DM": 600, "oDM": 400},
}

methane_yield = {
    "Cattle_slurry":       {"MY": 150},
    "Cattle_manure":       {"MY": 250},
    "Cattle_5_slurry":     {"MY": 150},
    "Cattle_5_manure":     {"MY": 250},
    "Horse_manure":        {"MY": 255},
    "Sheep_manure":        {"MY": 240},
    "Goat_manure":         {"MY": 240},
    "Pigs_slurry":         {"MY": 250},
    "poultry_manurebelt":  {"MY": 290},
    "poultry_floorsystem": {"MY": 280},
}

reduction_factors = {
    "Cattle_1": {"RF": 0.841},
    "Cattle_2": {"RF": 0.698},
    "Cattle_3": {"RF": 0.663},
    "Cattle_4": {"RF": 0.778},
    "Cattle_5": {"RF": 0.963},
    "Horses_1": {"RF": 0.657},
    "Horses_2": {"RF": 0.797},
    "Sheep_1":  {"RF": 0.738},
    "Sheep_2":  {"RF": 0.563},
    "Goats":    {"RF": 0.676},
}

# FM → oDM column + methane yield key mapping
FM_TO_oDM = {
    "Slurry_only_FM_cattle_1_m3":      ("Slurry_only_oDM_cattle_1",  "Cattle_slurry"),
    "Slurry_mixed_FM_cattle_1_m3":     ("Slurry_mixed_oDM_cattle_1", "Cattle_slurry"),
    "Manure_mixed_FM_cattle_1_tonnes": ("Manure_mixed_oDM_cattle_1", "Cattle_manure"),
    "Manure_only_FM_cattle_1_tonnes":  ("Manure_only_oDM_cattle_1",  "Cattle_manure"),
    "Slurry_only_FM_cattle_2_m3":      ("Slurry_only_oDM_cattle_2",  "Cattle_slurry"),
    "Slurry_mixed_FM_cattle_2_m3":     ("Slurry_mixed_oDM_cattle_2", "Cattle_slurry"),
    "Manure_mixed_FM_cattle_2_tonnes": ("Manure_mixed_oDM_cattle_2", "Cattle_manure"),
    "Manure_only_FM_cattle_2_tonnes":  ("Manure_only_oDM_cattle_2",  "Cattle_manure"),
    "Slurry_only_FM_cattle_3_m3":      ("Slurry_only_oDM_cattle_3",  "Cattle_slurry"),
    "Slurry_mixed_FM_cattle_3_m3":     ("Slurry_mixed_oDM_cattle_3", "Cattle_slurry"),
    "Manure_mixed_FM_cattle_3_tonnes": ("Manure_mixed_oDM_cattle_3", "Cattle_manure"),
    "Manure_only_FM_cattle_3_tonnes":  ("Manure_only_oDM_cattle_3",  "Cattle_manure"),
    "Slurry_only_FM_cattle_4_m3":      ("Slurry_only_oDM_cattle_4",  "Cattle_slurry"),
    "Slurry_mixed_FM_cattle_4_m3":     ("Slurry_mixed_oDM_cattle_4", "Cattle_slurry"),
    "Manure_mixed_FM_cattle_4_tonnes": ("Manure_mixed_oDM_cattle_4", "Cattle_manure"),
    "Manure_only_FM_cattle_4_tonnes":  ("Manure_only_oDM_cattle_4",  "Cattle_manure"),
    "Slurry_only_FM_cattle_5_m3":      ("Slurry_only_oDM_cattle_5",  "Cattle_5_slurry"),
    "Slurry_mixed_FM_cattle_5_m3":     ("Slurry_mixed_oDM_cattle_5", "Cattle_5_slurry"),
    "Manure_mixed_FM_cattle_5_tonnes": ("Manure_mixed_oDM_cattle_5", "Cattle_5_manure"),
    "Manure_only_FM_cattle_5_tonnes":  ("Manure_only_oDM_cattle_5",  "Cattle_5_manure"),
    "Manure_horses_FM_1_tonnes":       ("Manure_oDM_horses_1",       "Horse_manure"),
    "Manure_horses_FM_2_tonnes":       ("Manure_oDM_horses_2",       "Horse_manure"),
    "Manure_sheep_FM_1_tonnes":        ("Manure_oDM_sheep_1",        "Sheep_manure"),
    "Manure_sheep_FM_2_tonnes":        ("Manure_oDM_sheep_2",        "Sheep_manure"),
    "Manure_goats_FM_tonnes":          ("Manure_oDM_goats",          "Goat_manure"),
    "Slurry_pigs_FM_1_m3":            ("Slurry_oDM_pigs_1",         "Pigs_slurry"),
    "Slurry_pigs_FM_2_m3":            ("Slurry_oDM_pigs_2",         "Pigs_slurry"),
    "Slurry_pigs_FM_3_m3":            ("Slurry_oDM_pigs_3",         "Pigs_slurry"),
    "Slurry_poultry_FM_1_m3":         ("Slurry_oDM_poultry_1",      "poultry_manurebelt"),
    "Manure_poultry_FM_1_tonnes":      ("Manure_oDM_poultry_1",      "poultry_floorsystem"),
    "Manure_poultry_FM_2_tonnes":      ("Manure_oDM_poultry_2",      "poultry_floorsystem"),
    "Manure_poultry_FM_3_tonnes":      ("Manure_oDM_poultry_3",      "poultry_floorsystem"),
}

# =============================================================================
# OPT: Ergebnisse cachen — calculate_potential() läuft nur einmal pro Shapefile
# =============================================================================
_potential_cache = {}


def calculate_potential(input_shapefile):
    """
    Berechnet das Energiepotenzial aus Gülle/Mist für alle Polygone im Shapefile.
    Ergebnis wird gecacht → bei erneutem Aufruf mit gleichem Pfad sofort zurückgegeben.
    """
    if input_shapefile in _potential_cache:
        cached = _potential_cache[input_shapefile]
        # gdf als Kopie zurückgeben, Dicts sind read-only also direkt
        return (cached[0].copy(), *cached[1:])

    # -------------------------------------------------------------------------
    # Daten laden
    # -------------------------------------------------------------------------
    gdf = gpd.read_file(input_shapefile)
    c   = {}   # calc_columns – alle Zwischenergebnisse

    # =========================================================================
    # CATTLE
    # =========================================================================
    for i, ci, manure_key_m in [
        (1, "cattle_1", "manure_cattle"),
        (2, "cattle_2", "manure_cattle"),
        (3, "cattle_3", "manure_cattle"),
        (4, "cattle_4", "manure_cattle_4"),
    ]:
        col   = f"Cattle_{i}"
        mp    = manure_production_cattle[ci]
        st    = stable_cattle_total[ci]
        sc    = DM_oDM["slurry_cattle"]
        slsc  = DM_oDM["slurry_lowstraw_cattle"]
        mc    = DM_oDM[manure_key_m]

        # DM / oDM
        c[f"Slurry_DM_cattle_{i}"]  = gdf[col] * (mp["s"]  * st["only_slurry"]   * sc["DM"]   / 1000
                                                  + mp["sm1"] * st["manure_slurry"] * slsc["DM"] / 1000)
        c[f"Manure_DM_cattle_{i}"]  = gdf[col] * (mp["sm2"] * st["manure_slurry"] * mc["DM"]   / 1000
                                                  + mp["m"]   * st["only_manure"]   * mc["DM"]   / 1000)
        c[f"Slurry_oDM_cattle_{i}"] = gdf[col] * (mp["s"]  * st["only_slurry"]   * sc["oDM"]  / 1000
                                                  + mp["sm1"] * st["manure_slurry"] * slsc["oDM"]/ 1000)
        c[f"Manure_oDM_cattle_{i}"] = gdf[col] * (mp["sm2"] * st["manure_slurry"] * mc["oDM"]  / 1000
                                                  + mp["m"]   * st["only_manure"]   * mc["oDM"]  / 1000)

        # FM (fresh matter) theoretical
        c[f"Slurry_only_freshmatter_cattle_{i}_m3"]      = gdf[col] * mp["s"]   * st["only_slurry"]
        c[f"Slurry_mixed_freshmatter_cattle_{i}_m3"]     = gdf[col] * mp["sm1"] * st["manure_slurry"]
        c[f"Manure_mixed_freshmatter_cattle_{i}_tonnes"] = gdf[col] * mp["sm2"] * st["manure_slurry"]
        c[f"Manure_only_freshmatter_cattle_{i}_tonnes"]  = gdf[col] * mp["m"]   * st["only_manure"]

        # DM theoretical (reuse already-computed DM series)
        c[f"Slurry_only_drymatter_cattle_{i}_m3"]      = gdf[col] * mp["s"]   * st["only_slurry"]   * sc["DM"]  / 1000
        c[f"Slurry_mixed_drymatter_cattle_{i}_m3"]     = gdf[col] * mp["sm1"] * st["manure_slurry"] * slsc["DM"]/ 1000
        c[f"Manure_mixed_drymatter_cattle_{i}_tonnes"] = gdf[col] * mp["sm2"] * st["manure_slurry"] * mc["DM"]  / 1000
        c[f"Manure_only_drymatter_cattle_{i}_tonnes"]  = gdf[col] * mp["m"]   * st["only_manure"]   * mc["DM"]  / 1000

        # oDM per sub-category (for energy/CH4 per FM group)
        c[f"Slurry_only_oDM_cattle_{i}"]  = gdf[col] * mp["s"]   * st["only_slurry"]   * sc["oDM"]  / 1000
        c[f"Slurry_mixed_oDM_cattle_{i}"] = gdf[col] * mp["sm1"] * st["manure_slurry"] * slsc["oDM"]/ 1000
        c[f"Manure_mixed_oDM_cattle_{i}"] = gdf[col] * mp["sm2"] * st["manure_slurry"] * mc["oDM"]  / 1000
        c[f"Manure_only_oDM_cattle_{i}"]  = gdf[col] * mp["m"]   * st["only_manure"]   * mc["oDM"]  / 1000

        # Available (reduction factor)
        rf = reduction_factors[f"Cattle_{i}"]["RF"]
        for part in ["Slurry_only_freshmatter", "Slurry_mixed_freshmatter",
                     "Manure_mixed_freshmatter", "Manure_only_freshmatter"]:
            suffix = "m3" if "Slurry" in part else "tonnes"
            base   = f"{part}_cattle_{i}_{suffix}"
            c[base + "_available"] = c[base] * rf

        for part in ["Slurry_only_drymatter", "Slurry_mixed_drymatter",
                     "Manure_mixed_drymatter", "Manure_only_drymatter"]:
            suffix = "m3" if "Slurry" in part else "tonnes"
            base   = f"{part}_cattle_{i}_{suffix}"
            c[base + "_available"] = c[base] * rf

        for part in ["Slurry_only_oDM", "Slurry_mixed_oDM", "Manure_mixed_oDM", "Manure_only_oDM"]:
            base = f"{part}_cattle_{i}"
            c[base + "_available"] = c[base] * rf

    # Cattle 5 (special density keys)
    mp5 = manure_production_cattle["cattle_5"]
    st5 = stable_cattle_total["cattle_5"]
    lc5 = DM_oDM["liquid_cattle_5"]
    slsc= DM_oDM["slurry_lowstraw_cattle"]
    mc5 = DM_oDM["manure_cattle_5"]
    rf5 = reduction_factors["Cattle_5"]["RF"]

    c["Slurry_DM_cattle_5"]  = gdf["Cattle_5"] * (mp5["s"] * st5["only_slurry"]   * lc5["DM"] / 1000
                                                  + mp5["s"]*0.4 * st5["manure_slurry"] * slsc["DM"]/1000)
    c["Manure_DM_cattle_5"]  = gdf["Cattle_5"] * (mp5["m"]*0.6 * st5["manure_slurry"] * mc5["DM"]/1000
                                                  + mp5["m"] * st5["only_manure"]   * mc5["DM"]/1000)
    c["Slurry_oDM_cattle_5"] = gdf["Cattle_5"] * (mp5["s"] * st5["only_slurry"]   * lc5["oDM"]/1000
                                                  + mp5["s"]*0.4 * st5["manure_slurry"] * slsc["oDM"]/1000)
    c["Manure_oDM_cattle_5"] = gdf["Cattle_5"] * (mp5["m"]*0.6 * st5["manure_slurry"] * mc5["oDM"]/1000
                                                  + mp5["m"] * st5["only_manure"]   * mc5["oDM"]/1000)

    c["Slurry_only_freshmatter_cattle_5_m3"]      = gdf["Cattle_5"] * mp5["s"]     * st5["only_slurry"]
    c["Slurry_mixed_freshmatter_cattle_5_m3"]     = gdf["Cattle_5"] * mp5["s"]*0.4 * st5["manure_slurry"]
    c["Manure_mixed_freshmatter_cattle_5_tonnes"] = gdf["Cattle_5"] * mp5["m"]*0.6 * st5["manure_slurry"]
    c["Manure_only_freshmatter_cattle_5_tonnes"]  = gdf["Cattle_5"] * mp5["m"]     * st5["only_manure"]

    c["Slurry_only_drymatter_cattle_5_m3"]      = gdf["Cattle_5"] * mp5["s"]     * st5["only_slurry"]   * lc5["DM"] /1000
    c["Slurry_mixed_drymatter_cattle_5_m3"]     = gdf["Cattle_5"] * mp5["s"]*0.4 * st5["manure_slurry"] * slsc["DM"]/1000
    c["Manure_mixed_drymatter_cattle_5_tonnes"] = gdf["Cattle_5"] * mp5["m"]*0.6 * st5["manure_slurry"] * mc5["DM"] /1000
    c["Manure_only_drymatter_cattle_5_tonnes"]  = gdf["Cattle_5"] * mp5["m"]     * st5["only_manure"]   * mc5["DM"] /1000

    c["Slurry_only_oDM_cattle_5"]  = gdf["Cattle_5"] * mp5["s"]     * st5["only_slurry"]   * lc5["oDM"] /1000
    c["Slurry_mixed_oDM_cattle_5"] = gdf["Cattle_5"] * mp5["s"]*0.4 * st5["manure_slurry"] * slsc["oDM"]/1000
    c["Manure_mixed_oDM_cattle_5"] = gdf["Cattle_5"] * mp5["m"]*0.6 * st5["manure_slurry"] * mc5["oDM"] /1000
    c["Manure_only_oDM_cattle_5"]  = gdf["Cattle_5"] * mp5["m"]     * st5["only_manure"]   * mc5["oDM"] /1000

    for part in ["Slurry_only_freshmatter", "Slurry_mixed_freshmatter",
                 "Manure_mixed_freshmatter", "Manure_only_freshmatter"]:
        suffix = "m3" if "Slurry" in part else "tonnes"
        base   = f"{part}_cattle_5_{suffix}"
        c[base + "_available"] = c[base] * rf5

    for part in ["Slurry_only_drymatter", "Slurry_mixed_drymatter",
                 "Manure_mixed_drymatter", "Manure_only_drymatter"]:
        suffix = "m3" if "Slurry" in part else "tonnes"
        base   = f"{part}_cattle_5_{suffix}"
        c[base + "_available"] = c[base] * rf5

    for part in ["Slurry_only_oDM", "Slurry_mixed_oDM", "Manure_mixed_oDM", "Manure_only_oDM"]:
        base = f"{part}_cattle_5"
        c[base + "_available"] = c[base] * rf5

    # Aggregates cattle
    c["Cattle_total_oDM_slurry"]     = sum(c[f"Slurry_oDM_cattle_{i}"] for i in range(1, 6))
    c["Cattle_total_oDM_manure"]     = sum(c[f"Manure_oDM_cattle_{i}"] for i in range(1, 6))
    c["Cattle_available_oDM_slurry"] = sum(c[f"Slurry_oDM_cattle_{i}"] * reduction_factors[f"Cattle_{i}"]["RF"] for i in range(1, 6))
    c["Cattle_available_oDM_manure"] = sum(c[f"Manure_oDM_cattle_{i}"] * reduction_factors[f"Cattle_{i}"]["RF"] for i in range(1, 6))

    c["Cattle_primary_energy_theoretical"] = (c["Cattle_total_oDM_slurry"] + c["Cattle_total_oDM_manure"]) * CV_lower_oDM
    c["Cattle_primary_energy_available"]   = (c["Cattle_available_oDM_slurry"] + c["Cattle_available_oDM_manure"]) * CV_lower_oDM

    c["Cattle_biomethane_yield_theoretical_m3"] = (
        sum(c[f"Slurry_oDM_cattle_{i}"] for i in range(1, 5)) * methane_yield["Cattle_slurry"]["MY"]
        + sum(c[f"Manure_oDM_cattle_{i}"] for i in range(1, 5)) * methane_yield["Cattle_manure"]["MY"]
        + c["Slurry_oDM_cattle_5"] * methane_yield["Cattle_5_slurry"]["MY"]
        + c["Manure_oDM_cattle_5"] * methane_yield["Cattle_5_manure"]["MY"]
    )
    c["Cattle_biomethane_yield_theoretical_GJ"] = c["Cattle_biomethane_yield_theoretical_m3"] * CV_lower_methane / 1000

    c["Cattle_biomethane_yield_available_m3"] = (
        c["Cattle_available_oDM_slurry"] * methane_yield["Cattle_slurry"]["MY"]
        + c["Cattle_available_oDM_manure"] * methane_yield["Cattle_manure"]["MY"]
    )
    c["Cattle_biomethane_yield_available_GJ"] = c["Cattle_biomethane_yield_available_m3"] * CV_lower_methane / 1000

    # =========================================================================
    # HORSES
    # =========================================================================
    for i in [1, 2]:
        mp  = manure_production_horse[f"horse_{i}"]
        dm  = DM_oDM["manure_horse"]
        rf  = reduction_factors[f"Horses_{i}"]["RF"]
        c[f"Manure_DM_horses_{i}"]               = gdf[f"Horses_{i}"] * mp["m"] * dm["DM"]  / 1000
        c[f"Manure_oDM_horses_{i}"]              = gdf[f"Horses_{i}"] * mp["m"] * dm["oDM"] / 1000
        c[f"Manure_horses_FM_{i}_tonnes"]        = gdf[f"Horses_{i}"] * mp["m"]
        c[f"Manure_horses_DM_{i}_tonnes"]        = c[f"Manure_DM_horses_{i}"]
        c[f"Manure_horses_FM_{i}_tonnes_available"] = c[f"Manure_horses_FM_{i}_tonnes"] * rf
        c[f"Manure_horses_DM_{i}_tonnes_available"] = c[f"Manure_horses_DM_{i}_tonnes"] * rf
        c[f"Manure_oDM_horses_{i}_available"]    = c[f"Manure_oDM_horses_{i}"] * rf

    c["Horses_total_oDM_manure"]     = c["Manure_oDM_horses_1"] + c["Manure_oDM_horses_2"]
    c["Horses_available_oDM_manure"] = c["Manure_oDM_horses_1_available"] + c["Manure_oDM_horses_2_available"]

    c["Horses_primary_energy_theoretical"]     = c["Horses_total_oDM_manure"]     * CV_lower_oDM
    c["Horses_primary_energy_available"]       = c["Horses_available_oDM_manure"] * CV_lower_oDM
    c["Horses_biomethane_yield_theoretical_m3"]= c["Horses_total_oDM_manure"]     * methane_yield["Horse_manure"]["MY"]
    c["Horses_biomethane_yield_theoretical_GJ"]= c["Horses_biomethane_yield_theoretical_m3"] * CV_lower_methane / 1000
    c["Horses_biomethane_yield_available_m3"]  = c["Horses_available_oDM_manure"] * methane_yield["Horse_manure"]["MY"]
    c["Horses_biomethane_yield_available_GJ"]  = c["Horses_biomethane_yield_available_m3"] * CV_lower_methane / 1000

    # =========================================================================
    # SHEEP
    # =========================================================================
    for i in [1, 2]:
        mp = manure_production_sheep[f"sheep_{i}"]
        dm = DM_oDM["manure_sheep"]
        rf = reduction_factors[f"Sheep_{i}"]["RF"]
        c[f"Manure_DM_sheep_{i}"]               = gdf[f"Sheep_{i}"] * mp["m"] * dm["DM"]  / 1000
        c[f"Manure_oDM_sheep_{i}"]              = gdf[f"Sheep_{i}"] * mp["m"] * dm["oDM"] / 1000
        c[f"Manure_sheep_FM_{i}_tonnes"]        = gdf[f"Sheep_{i}"] * mp["m"]
        c[f"Manure_sheep_DM_{i}_tonnes"]        = c[f"Manure_DM_sheep_{i}"]
        c[f"Manure_sheep_FM_{i}_tonnes_available"] = c[f"Manure_sheep_FM_{i}_tonnes"] * rf
        c[f"Manure_sheep_DM_{i}_tonnes_available"] = c[f"Manure_sheep_DM_{i}_tonnes"] * rf
        c[f"Manure_oDM_sheep_{i}_available"]    = c[f"Manure_oDM_sheep_{i}"] * rf

    c["Sheep_total_oDM_manure"]     = c["Manure_oDM_sheep_1"] + c["Manure_oDM_sheep_2"]
    c["Sheep_available_oDM_manure"] = c["Manure_oDM_sheep_1_available"] + c["Manure_oDM_sheep_2_available"]

    c["Sheep_primary_energy_theoretical"]     = c["Sheep_total_oDM_manure"]     * CV_lower_oDM
    c["Sheep_primary_energy_available"]       = c["Sheep_available_oDM_manure"] * CV_lower_oDM
    c["Sheep_biomethane_yield_theoretical_m3"]= c["Sheep_total_oDM_manure"]     * methane_yield["Sheep_manure"]["MY"]
    c["Sheep_biomethane_yield_theoretical_GJ"]= c["Sheep_biomethane_yield_theoretical_m3"] * CV_lower_methane / 1000
    c["Sheep_biomethane_yield_available_m3"]  = c["Sheep_available_oDM_manure"] * methane_yield["Sheep_manure"]["MY"]
    c["Sheep_biomethane_yield_available_GJ"]  = c["Sheep_biomethane_yield_available_m3"] * CV_lower_methane / 1000

    # =========================================================================
    # GOATS
    # =========================================================================
    mp_g = manure_production_goats["goats"]
    dm_g = DM_oDM["manure_goat"]
    rf_g = reduction_factors["Goats"]["RF"]

    c["Manure_DM_goats"]                = gdf["Goats"] * mp_g["m"] * dm_g["DM"]  / 1000
    c["Manure_goats_DM_tonnes"]         = c["Manure_DM_goats"]
    c["Manure_oDM_goats"]               = gdf["Goats"] * mp_g["m"] * dm_g["oDM"] / 1000
    c["Manure_goats_FM_tonnes"]         = gdf["Goats"] * mp_g["m"]
    c["Goats_total_oDM_manure"]         = c["Manure_oDM_goats"]
    c["Goats_available_oDM_manure"]     = c["Manure_oDM_goats"] * rf_g
    c["Manure_oDM_goats_available"]     = c["Goats_available_oDM_manure"]
    c["Manure_goats_FM_tonnes_available"]  = c["Manure_goats_FM_tonnes"] * rf_g
    c["Manure_goats_DM_tonnes_available"]  = c["Manure_goats_DM_tonnes"] * rf_g

    c["Goats_primary_energy_theoretical"]     = c["Goats_total_oDM_manure"]     * CV_lower_oDM
    c["Goats_primary_energy_available"]       = c["Goats_available_oDM_manure"] * CV_lower_oDM
    c["Goats_biomethane_yield_theoretical_m3"]= c["Goats_total_oDM_manure"]     * methane_yield["Goat_manure"]["MY"]
    c["Goats_biomethane_yield_theoretical_GJ"]= c["Goats_biomethane_yield_theoretical_m3"] * CV_lower_methane / 1000
    c["Goats_biomethane_yield_available_m3"]  = c["Goats_available_oDM_manure"] * methane_yield["Goat_manure"]["MY"]
    c["Goats_biomethane_yield_available_GJ"]  = c["Goats_biomethane_yield_available_m3"] * CV_lower_methane / 1000

    # =========================================================================
    # PIGS
    # =========================================================================
    for i in [1, 2, 3]:
        mp  = manure_production_pigs[f"pigs_{i}"]
        dm  = DM_oDM["pigs"] if i < 3 else DM_oDM["pigs_3"]
        c[f"Slurry_DM_pigs_{i}"]            = gdf[f"Pigs_{i}"] * mp["s"] * dm["DM"]  / 1000
        c[f"Slurry_oDM_pigs_{i}"]           = gdf[f"Pigs_{i}"] * mp["s"] * dm["oDM"] / 1000
        c[f"Slurry_pigs_FM_{i}_m3"]         = gdf[f"Pigs_{i}"] * mp["s"]
        c[f"Slurry_pigs_DM_{i}_m3"]         = c[f"Slurry_DM_pigs_{i}"]
        # Pigs: no grazing reduction
        c[f"Slurry_pigs_FM_{i}_m3_available"]  = c[f"Slurry_pigs_FM_{i}_m3"]
        c[f"Slurry_pigs_DM_{i}_m3_available"]  = c[f"Slurry_pigs_DM_{i}_m3"]
        c[f"Slurry_oDM_pigs_{i}_available"]    = c[f"Slurry_oDM_pigs_{i}"]

    c["Pigs_total_oDM_slurry"]     = sum(c[f"Slurry_oDM_pigs_{i}"] for i in [1, 2, 3])
    c["Pigs_available_oDM_slurry"] = c["Pigs_total_oDM_slurry"]

    c["Pigs_primary_energy_theoretical"]      = c["Pigs_total_oDM_slurry"] * CV_lower_oDM
    c["Pigs_primary_energy_available"]        = c["Pigs_primary_energy_theoretical"]
    c["Pigs_biomethane_yield_theoretical_m3"] = c["Pigs_total_oDM_slurry"] * methane_yield["Pigs_slurry"]["MY"]
    c["Pigs_biomethane_yield_theoretical_GJ"] = c["Pigs_biomethane_yield_theoretical_m3"] * CV_lower_methane / 1000
    c["Pigs_biomethane_yield_available_m3"]   = c["Pigs_biomethane_yield_theoretical_m3"]
    c["Pigs_biomethane_yield_available_GJ"]   = c["Pigs_biomethane_yield_theoretical_GJ"]

    # =========================================================================
    # POULTRY
    # =========================================================================
    sp1 = stable_system_poultry["poultry_1"]

    c["Slurry_DM_poultry_1"]   = gdf["Poultry_1"] * sp1["manure_belt"] * manure_production_poultry["poultry_1"]["s"] * (DM_oDM["poultry_1_manurebelt"]["DM"] /100)/1000
    c["Slurry_oDM_poultry_1"]  = gdf["Poultry_1"] * sp1["manure_belt"] * manure_production_poultry["poultry_1"]["s"] * (DM_oDM["poultry_1_manurebelt"]["oDM"]/100)/1000
    c["Manure_DM_poultry_1"]   = gdf["Poultry_1"] * sp1["floor_system"]* manure_production_poultry["poultry_1"]["m"] * (DM_oDM["poultry_1_floorsystem"]["DM"] /100)/1000
    c["Manure_oDM_poultry_1"]  = gdf["Poultry_1"] * sp1["floor_system"]* manure_production_poultry["poultry_1"]["m"] * (DM_oDM["poultry_1_floorsystem"]["oDM"]/100)/1000
    c["Manure_DM_poultry_2"]   = gdf["Poultry_2"] * manure_production_poultry["poultry_2"]["m"] * (DM_oDM["poultry_2"]["DM"] /100)/1000
    c["Manure_oDM_poultry_2"]  = gdf["Poultry_2"] * manure_production_poultry["poultry_2"]["m"] * (DM_oDM["poultry_2"]["oDM"]/100)/1000
    c["Manure_DM_poultry_3"]   = gdf["Poultry_3"] * manure_production_poultry["poultry_3"]["m"] * (DM_oDM["poultry_3"]["DM"] /100)/1000
    c["Manure_oDM_poultry_3"]  = gdf["Poultry_3"] * manure_production_poultry["poultry_3"]["m"] * (DM_oDM["poultry_3"]["oDM"]/100)/1000

    c["Slurry_poultry_FM_1_m3"]         = gdf["Poultry_1"] * sp1["manure_belt"]  * manure_production_poultry["poultry_1"]["s"] / 100
    c["Manure_poultry_FM_1_tonnes"]      = gdf["Poultry_1"] * sp1["floor_system"] * manure_production_poultry["poultry_1"]["m"] / 100
    c["Manure_poultry_FM_2_tonnes"]      = gdf["Poultry_2"] * manure_production_poultry["poultry_2"]["m"] / 100
    c["Manure_poultry_FM_3_tonnes"]      = gdf["Poultry_3"] * manure_production_poultry["poultry_3"]["m"] / 100
    c["Slurry_poultry_DM_1_m3"]         = c["Slurry_DM_poultry_1"]
    c["Manure_poultry_DM_1_tonnes"]     = c["Manure_DM_poultry_1"]
    c["Manure_poultry_DM_2_tonnes"]     = c["Manure_DM_poultry_2"]
    c["Manure_poultry_DM_3_tonnes"]     = c["Manure_DM_poultry_3"]

    # Poultry: no grazing reduction
    for key in ["Slurry_poultry_FM_1_m3", "Manure_poultry_FM_1_tonnes",
                "Manure_poultry_FM_2_tonnes", "Manure_poultry_FM_3_tonnes",
                "Slurry_poultry_DM_1_m3",  "Manure_poultry_DM_1_tonnes",
                "Manure_poultry_DM_2_tonnes","Manure_poultry_DM_3_tonnes"]:
        c[key + "_available"] = c[key]
    for key in ["Slurry_oDM_poultry_1", "Manure_oDM_poultry_1", "Manure_oDM_poultry_2", "Manure_oDM_poultry_3"]:
        c[key + "_available"] = c[key]

    c["Poultry_total_oDM_slurry"]     = c["Slurry_oDM_poultry_1"]
    c["Poultry_available_oDM_slurry"] = c["Slurry_oDM_poultry_1"]
    c["Poultry_total_oDM_manure"]     = c["Manure_oDM_poultry_1"] + c["Manure_oDM_poultry_2"] + c["Manure_oDM_poultry_3"]
    c["Poultry_available_oDM_manure"] = c["Poultry_total_oDM_manure"]

    c["Poultry_primary_energy_theoretical"]      = (c["Poultry_total_oDM_slurry"] + c["Poultry_total_oDM_manure"]) * CV_lower_oDM
    c["Poultry_primary_energy_available"]        = c["Poultry_primary_energy_theoretical"]
    c["Poultry_biomethane_yield_theoretical_m3"] = (c["Poultry_total_oDM_slurry"] * methane_yield["poultry_manurebelt"]["MY"]
                                                   + c["Poultry_total_oDM_manure"] * methane_yield["poultry_floorsystem"]["MY"])
    c["Poultry_biomethane_yield_theoretical_GJ"] = c["Poultry_biomethane_yield_theoretical_m3"] * CV_lower_methane / 1000
    c["Poultry_biomethane_yield_available_m3"]   = c["Poultry_biomethane_yield_theoretical_m3"]
    c["Poultry_biomethane_yield_available_GJ"]   = c["Poultry_biomethane_yield_theoretical_GJ"]

    # =========================================================================
    # TOTALS
    # =========================================================================
    species = ["Cattle", "Horses", "Sheep", "Goats", "Pigs", "Poultry"]

    c["Total_primary_energy_theoretical"] = sum(c[f"{s}_primary_energy_theoretical"] for s in species)
    c["Total_primary_energy_available"]   = sum(c[f"{s}_primary_energy_available"]   for s in species)

    c["Total_biomethane_yield_theoretical_m3"] = sum(c[f"{s}_biomethane_yield_theoretical_m3"] for s in species)
    c["Total_biomethane_yield_theoretical_GJ"] = sum(c[f"{s}_biomethane_yield_theoretical_GJ"] for s in species)
    c["Total_biomethane_yield_available_m3"]   = sum(c[f"{s}_biomethane_yield_available_m3"]   for s in species)
    c["Total_biomethane_yield_available_GJ"]   = sum(c[f"{s}_biomethane_yield_available_GJ"]   for s in species)

    # =========================================================================
    # WRITE RESULTS TO GDF
    # =========================================================================
    gdf["Total_primary_energy_theoretical_GJ"]  = c["Total_primary_energy_theoretical"]
    gdf["Total_biomethane_yield_theoretical_GJ"] = c["Total_biomethane_yield_theoretical_GJ"]
    gdf["Total_primary_energy_available_GJ"]     = c["Total_primary_energy_available"]
    gdf["Total_biomethane_yield_available_GJ"]   = c["Total_biomethane_yield_available_GJ"]
    gdf["Total_primary_energy_theoretical_TJ"]   = c["Total_primary_energy_theoretical"]   / 1000
    gdf["Total_biomethane_yield_theoretical_TJ"] = c["Total_biomethane_yield_theoretical_GJ"] / 1000
    gdf["Total_primary_energy_available_TJ"]     = c["Total_primary_energy_available"]     / 1000
    gdf["Total_biomethane_yield_available_TJ"]   = c["Total_biomethane_yield_available_GJ"] / 1000
    gdf["Biometh_available_m3"]                  = c["Total_biomethane_yield_available_m3"]

    # Fresh matter totals (available)
    slurry_fm_cols = (
        [f"Slurry_only_freshmatter_cattle_{i}_m3_available"  for i in range(1, 6)]
        + [f"Slurry_mixed_freshmatter_cattle_{i}_m3_available" for i in range(1, 6)]
        + [f"Slurry_pigs_FM_{i}_m3_available" for i in [1, 2, 3]]
        + ["Slurry_poultry_FM_1_m3_available"]
    )
    manure_fm_cols = (
        [f"Manure_mixed_freshmatter_cattle_{i}_tonnes_available" for i in range(1, 6)]
        + [f"Manure_only_freshmatter_cattle_{i}_tonnes_available"  for i in range(1, 6)]
        + [f"Manure_horses_FM_{i}_tonnes_available" for i in [1, 2]]
        + [f"Manure_sheep_FM_{i}_tonnes_available"  for i in [1, 2]]
        + ["Manure_goats_FM_tonnes_available"]
        + [f"Manure_poultry_FM_{i}_tonnes_available" for i in [1, 2, 3]]
    )

    gdf["Total_Slurry_FreshMatter_m3_available"]     = sum(c[k] for k in slurry_fm_cols)
    gdf["Total_Manure_FreshMatter_tonnes_available"]  = sum(c[k] for k in manure_fm_cols)
    total_fm = gdf["Total_Slurry_FreshMatter_m3_available"] + gdf["Total_Manure_FreshMatter_tonnes_available"]

    # FM per livestock group
    gdf["FM_total_t_cattle_av"]  = (sum(c[f"Manure_mixed_freshmatter_cattle_{i}_tonnes_available"] for i in range(1, 6))
                                  + sum(c[f"Manure_only_freshmatter_cattle_{i}_tonnes_available"]  for i in range(1, 6))
                                  + sum(c[f"Slurry_only_freshmatter_cattle_{i}_m3_available"]      for i in range(1, 6))
                                  + sum(c[f"Slurry_mixed_freshmatter_cattle_{i}_m3_available"]     for i in range(1, 6)))
    gdf["FM_total_t_horses_av"]  = c["Manure_horses_FM_1_tonnes_available"] + c["Manure_horses_FM_2_tonnes_available"]
    gdf["FM_total_t_sheep_av"]   = c["Manure_sheep_FM_1_tonnes_available"]  + c["Manure_sheep_FM_2_tonnes_available"]
    gdf["FM_total_t_goats_av"]   = c["Manure_goats_FM_tonnes_available"]
    gdf["FM_total_t_pigs_av"]    = sum(c[f"Slurry_pigs_FM_{i}_m3_available"] for i in [1, 2, 3])
    gdf["FM_total_t_poultry_av"] = (c["Manure_poultry_FM_1_tonnes_available"] + c["Manure_poultry_FM_2_tonnes_available"]
                                  + c["Manure_poultry_FM_3_tonnes_available"] + c["Slurry_poultry_FM_1_m3_available"])

    # DM totals (available)
    gdf["Total_Slurry_DM_m3_available"] = (
        sum(c[f"Slurry_only_drymatter_cattle_{i}_m3_available"]  for i in range(1, 6))
        + sum(c[f"Slurry_mixed_drymatter_cattle_{i}_m3_available"] for i in range(1, 6))
        + sum(c[f"Slurry_pigs_DM_{i}_m3_available"] for i in [1, 2, 3])
        + c["Slurry_poultry_DM_1_m3_available"]
    )
    gdf["Total_Manure_DM_tonnes_available"] = (
        sum(c[f"Manure_mixed_drymatter_cattle_{i}_tonnes_available"] for i in range(1, 6))
        + sum(c[f"Manure_only_drymatter_cattle_{i}_tonnes_available"]  for i in range(1, 6))
        + sum(c[f"Manure_horses_DM_{i}_tonnes_available"] for i in [1, 2])
        + sum(c[f"Manure_sheep_DM_{i}_tonnes_available"]  for i in [1, 2])
        + c["Manure_goats_DM_tonnes_available"]
        + sum(c[f"Manure_poultry_DM_{i}_tonnes_available"] for i in [1, 2, 3])
    )

    # Storage system shares
    gdf["Share_liquid/slurry"] = (
        sum(c[f"Slurry_only_freshmatter_cattle_{i}_m3_available"]  for i in range(1, 6))
        + sum(c[f"Slurry_mixed_freshmatter_cattle_{i}_m3_available"] for i in range(1, 6))
        + sum(c[f"Slurry_pigs_FM_{i}_m3_available"] for i in [1, 2, 3])
    ) / total_fm

    gdf["Share_solid_storage"] = (
        sum(c[f"Manure_mixed_freshmatter_cattle_{i}_tonnes_available"] for i in range(1, 6))
        + c["Manure_horses_FM_1_tonnes_available"] + c["Manure_horses_FM_2_tonnes_available"]
        + c["Manure_sheep_FM_1_tonnes_available"]  + c["Manure_sheep_FM_2_tonnes_available"]
        + c["Manure_goats_FM_tonnes_available"]
    ) / total_fm

    gdf["Share_deep_litter"] = (
        sum(c[f"Manure_only_freshmatter_cattle_{i}_tonnes_available"] for i in range(1, 6))
    ) / total_fm

    gdf["Share_poultry_system"] = (
        c["Slurry_poultry_FM_1_m3_available"] + c["Manure_poultry_FM_1_tonnes_available"]
        + c["Manure_poultry_FM_2_tonnes_available"] + c["Manure_poultry_FM_3_tonnes_available"]
    ) / total_fm

    # Per-species energy/CH4 written to gdf
    for s in species:
        gdf[f"{s}_primary_energy_theoretical"] = c[f"{s}_primary_energy_theoretical"]
        gdf[f"{s}_primary_energy_available"]   = c[f"{s}_primary_energy_available"]

    # =========================================================================
    # SUMMARY DICTS (for external use / plotting)
    # OPT: alle .sum() in einem Schritt mit pd.concat → ein Durchlauf
    # =========================================================================
    def _sums(keys):
        return {k: float(c[k].sum()) for k in keys}

    fm_theo_keys = [
        *[f"Slurry_only_freshmatter_cattle_{i}_m3"      for i in range(1, 6)],
        *[f"Slurry_mixed_freshmatter_cattle_{i}_m3"     for i in range(1, 6)],
        *[f"Manure_mixed_freshmatter_cattle_{i}_tonnes"  for i in range(1, 6)],
        *[f"Manure_only_freshmatter_cattle_{i}_tonnes"   for i in range(1, 6)],
        "Manure_horses_FM_1_tonnes", "Manure_horses_FM_2_tonnes",
        "Manure_sheep_FM_1_tonnes",  "Manure_sheep_FM_2_tonnes",
        "Manure_goats_FM_tonnes",
        "Slurry_pigs_FM_1_m3", "Slurry_pigs_FM_2_m3", "Slurry_pigs_FM_3_m3",
        "Slurry_poultry_FM_1_m3",
        "Manure_poultry_FM_1_tonnes", "Manure_poultry_FM_2_tonnes", "Manure_poultry_FM_3_tonnes",
    ]
    dm_theo_keys = [k.replace("freshmatter", "drymatter").replace("FM", "DM") for k in fm_theo_keys]
    # Some DM key names differ from FM — build explicitly for safety
    dm_theo_keys = [
        *[f"Slurry_only_drymatter_cattle_{i}_m3"      for i in range(1, 6)],
        *[f"Slurry_mixed_drymatter_cattle_{i}_m3"     for i in range(1, 6)],
        *[f"Manure_mixed_drymatter_cattle_{i}_tonnes"  for i in range(1, 6)],
        *[f"Manure_only_drymatter_cattle_{i}_tonnes"   for i in range(1, 6)],
        "Manure_horses_DM_1_tonnes", "Manure_horses_DM_2_tonnes",
        "Manure_sheep_DM_1_tonnes",  "Manure_sheep_DM_2_tonnes",
        "Manure_goats_DM_tonnes",
        "Slurry_pigs_DM_1_m3", "Slurry_pigs_DM_2_m3", "Slurry_pigs_DM_3_m3",
        "Slurry_poultry_DM_1_m3",
        "Manure_poultry_DM_1_tonnes", "Manure_poultry_DM_2_tonnes", "Manure_poultry_DM_3_tonnes",
    ]
    fm_av_keys = [k + "_available" for k in fm_theo_keys]
    dm_av_keys = [k + "_available" for k in dm_theo_keys]

    fresh_matter_totals    = _sums(fm_theo_keys)
    dry_matter_totals      = _sums(dm_theo_keys)
    fresh_matter_available = _sums(fm_av_keys)
    dry_matter_available   = _sums(dm_av_keys)

    energy_theoretical_totals_GJ = {
        fm_key: float((c[odm_col] * CV_lower_oDM).sum())
        for fm_key, (odm_col, _) in FM_TO_oDM.items()
        if odm_col in c
    }
    energy_available_totals_GJ = {
        fm_key: float((c[odm_col + "_available"] * CV_lower_oDM).sum())
        for fm_key, (odm_col, _) in FM_TO_oDM.items()
        if (odm_col + "_available") in c
    }
    methane_theoretical_totals_GJ = {
        fm_key: float((c[odm_col] * methane_yield[my_key]["MY"] * CV_lower_methane / 1000).sum())
        for fm_key, (odm_col, my_key) in FM_TO_oDM.items()
        if odm_col in c
    }
    methane_available_totals_GJ = {
        fm_key: float((c[odm_col + "_available"] * methane_yield[my_key]["MY"] * CV_lower_methane / 1000).sum())
        for fm_key, (odm_col, my_key) in FM_TO_oDM.items()
        if (odm_col + "_available") in c
    }

    # =========================================================================
    # CACHE & RETURN
    # =========================================================================
    result = (
        gdf,
        fresh_matter_totals,
        dry_matter_totals,
        fresh_matter_available,
        dry_matter_available,
        energy_theoretical_totals_GJ,
        energy_available_totals_GJ,
        methane_theoretical_totals_GJ,
        methane_available_totals_GJ,
    )
    _potential_cache[input_shapefile] = result
    return (result[0].copy(), *result[1:])