import geopandas as gpd
import pandas as pd
from nutrients import calculate_nitrogen
from potential_env_imp import calculate_potential_env_imp
from potential import calculate_potential
from Storage_emissions import build_systems_for_polygon, RHO_CH4_STP_g_per_mL
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



FACTORS_PRE = {
    # (Beispiel: deine bisherigen Pre-Storage-Werte; falls identisch, duplizieren)
    "MCF": {
        "Liquid/slurry": {"14": 18.2, "15": 14.7, "26": 7.7, "27": 7.7, "29": 7.7},
        "Solid storage": {"14": 4.0,  "15": 4.0,  "26": 2.0, "27": 2.0, "29": 2.0},
        "Deep litter":   {"14": 10.0, "15": 10.0, "26": 10.0,"27": 10.0,"29": 10.0},
        "Poultry system":{"14": 1.5,  "15": 1.5,  "26": 1.5, "27": 1.5, "29": 1.5},
    },
    "N2O": {  # als Anteil des Total-N (Direktemissionen im Lager)
        "Liquid/slurry": 0.002,
        "Solid storage": 0.005,
        "Deep litter":   0.010,
        "Poultry system":0.001,
    }
}

FACTORS_POST = {
    # === DEINE Post-Storage-Werte (aus deinem Snippet) =======================
    "MCF" : {
        "Solid storage": {"14": 4*0.33,"15": 4*0.33,"26": 2*0.33,"27": 2*0.33,"29": 2*0.33},
        "Liquid/slurry": {"14": 18.2*0.33,"15": 14.7*0.33,"26": 7.7*0.33,"27": 7.7*0.33,"29": 7.7*0.33},
        "Deep litter": {"14": 10*0.33,"15": 10*0.33,"26": 10*0.33,"27": 10*0.33,"29": 10*0.33},
        "Poultry system": {"14": 1.5*0.33,"15": 1.5*0.33,"26": 1.5*0.33,"27": 1.5*0.33,"29": 1.5*0.33},
    },

    "N2O" : {
        "Liquid/slurry": 0.002*1.41,
        "Solid storage": 0.005*1.41,
        "Deep litter": 0.01*1.41,
        "Poultry system": 0.001*1.41,
        #"Indirect emissions due to volatilisation": 0.026,
    }
}

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

factor_digestate_available=1.1
# Verhältnis
n_plant_available = {
    "Slurry": {
        "Cattle": 0.60*factor_digestate_available, "Horses": None, "Sheep": None, "Goats": None, "Pigs": 0.61*factor_digestate_available, "Poultry": 0.51*factor_digestate_available
    },
    "Solid": {
        "Cattle": 0.40*factor_digestate_available, "Horses": 0.125*factor_digestate_available, "Sheep": 0.5*factor_digestate_available, "Goats": 0.5*factor_digestate_available, "Pigs": None, "Poultry": None
    },
    "Deep litter": {
        "Cattle": 0.50*factor_digestate_available, "Horses": None, "Sheep": None, "Goats": None, "Pigs": None, "Poultry": None
    },
    "Poultry System": {
        "Cattle": None, "Horses": None, "Sheep": None, "Goats": None, "Pigs": None, "Poultry": 0.52*factor_digestate_available
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
                "factors": FACTORS_PRE,
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
        "pre_storage_N2O": 0,
        "transport_CO2": 0,
        "AD_methane_slip_CH4": 0,
        "Upgrading_electricity_benefit_CO2": 0,
        "AD_electricity_use_CO2": 0,
        "Upgrading_infrastructure_CO2": 0,
        "AD_infrastructure_CO2": 0,
        "post_storage_CH4": 0,
        "post_storage_N2O": 0,
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
        12,
        12,
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
    #print(f"\n--- {sp} ---")
    #print("CH4 (kg/year)::", round(float(total_ch4.sum()), 2))
    # print("N2O (kg/year):", round(float(total_n2o.sum()), 2))


#Transport

def transport_kgCO2e_per_tonne(
    distance_one_way_km: float,
    fuel_l_per_km: float = 0.48,         # L/km (Lkw/Traktor mit Fass)
    ef_kgCO2e_per_l: float = 2.62,       # kg CO2e / L Diesel
) -> float:
    """
    Liefert kg CO2e pro transportierte Tonne für einen Transportvorgang.
    Wenn `backhaul_loaded=True`, wird der Rückweg als zusätzlicher beladener Transport gewertet.
    """
    # effektive km mit Verbrauch (Rückweg zählt beim Verbrauch immer)
    distance_km = distance_one_way_km * 4

    # Liter Diesel gesamt
    liters = distance_km * fuel_l_per_km

    # Emissionen gesamt (kg CO2e)
    kg_co2e_total = liters * ef_kgCO2e_per_l*1/10

    # kg CO2e pro Tonne
    return kg_co2e_total

transport_co2e_per_t = transport_kgCO2e_per_tonne(
    distance_one_way_km=7.5,
    fuel_l_per_km=0.48,
    ef_kgCO2e_per_l=2.62,
)
# 2) für alle Spezies abspeichern
for sp in results_per_species.keys():  # oder: for sp in species_tonnes.keys():
    results_LCA.setdefault(sp, {})
    results_LCA[sp]["transport_CO2"] = transport_co2e_per_t


#print("Transport_kgco2:", round(transport_co2e_per_t, 2))

# Anaerobic Digestion Process


# Speicher für spätere Nutzung
net_biomethane_m3 = {}      # Netto verfügbar für Energie (m³ CH4/t)
methane_losses_kg = {}      # Methanverluste (kg CH4/t)

RHO_CH4 = 0.67      # kg CH4 pro m3
AD_EFF  = 0.85      # Wirkungsgrad
SLIP    = 0.0105    # 1.05% Methanschlupf
CH4_Biogas= 0.625

for sp, res_sp in results_per_species.items():

    total_ch4_kg = float(res_sp["total"]["ch4_kg_daily"].sum())
    total_ch4_m3 = total_ch4_kg / RHO_CH4

    # Nettobiomethan nach Lagerverlust + AD-Wirkungsgrad
    net_m3 = max(biomethane_yield_ch_mix[sp] - total_ch4_m3, 0.0) * AD_EFF

    # Methanschlupf (wieder in kg CH4)
    methane_losses = net_m3 * SLIP * RHO_CH4
    # --- Speichern ---

    net_biomethane_m3[sp] = net_m3
    methane_losses_kg[sp] = methane_losses
    results_LCA[sp]["AD_methane_slip_CH4"] = methane_losses

    #print(f"\n--- {sp} ---")
    #print("methane losses AD (kg CH4/t):", round(methane_losses, 2))


# Energy benefits
CHP_el=0.34
CHP_heat=0.51
electricity_demand=576 #kJ/m3
heat_demand=3500  #kJ/m3
upgrading_efficiency=0.96

electricity_co2=128 #g CO2/kWh
external_heat_usage=0.0  #%
heat_substitution=0.0125 #kgCO2/MJ
biomethane_substitution=0.633#kgCO2/m3


biomethane_yield_m3_pw3 = {}
electricity_generated_GJ_chp = {}
for sp, res_sp in results_per_species.items():

    biogas_produced_m3=(net_biomethane_m3[sp]-(methane_losses_kg[sp]/RHO_CH4))/ CH4_Biogas#kgCH4
    biomethane_yield_m3=biogas_produced_m3*upgrading_efficiency*CH4_Biogas
    biogas_yield_GJ = biogas_produced_m3 * CH4_Biogas * 35.883 / 1000
    electricity_generated_GJ = biogas_yield_GJ * CHP_el * (8000 / 8670)
    electricity_demand_AD_kWh=biogas_produced_m3*electricity_demand/1000/3.6
    heat_demand_AD_GJ=biogas_produced_m3*heat_demand/1000000*0.95

    #CO2 emissions
    electricity_demand_kgCO2=electricity_demand_AD_kWh * electricity_co2/1000
    #CO2 benefits
    biomethane_after_heat_usage=(biomethane_yield_m3 - (heat_demand_AD_GJ* 277.78 / 9.97))
    biomethane_benefits_kgCO2 =  biomethane_after_heat_usage * biomethane_substitution





    biomethane_yield_m3_pw3 [sp]= biomethane_yield_m3
    electricity_generated_GJ_chp[sp] = electricity_generated_GJ

    results_LCA[sp]["AD_electricity_use_CO2"] = electricity_demand_kgCO2
    results_LCA[sp]["Upgrading_electricity_benefit_CO2"] = -biomethane_benefits_kgCO2

    #print(f"\n--- {sp} ---")
    #print("Upgrading benefits (kg CO2/t):", round(biomethane_benefits_kgCO2, 2))



# Construction
#
Upgrading_infrastructure=0.15 #kgCO2 pro m3 biomethane

AD_infrastructure=42236.193476516

for sp, res_sp in results_per_species.items():


    Upgrading_infrastructure_kgCO2= biomethane_yield_m3_pw3 [sp]* Upgrading_infrastructure

    kgCo2_per_kWh_AD=AD_infrastructure/(50*8000*20)
    AD_infrastructure_kgCo2= electricity_generated_GJ_chp[sp] *kgCo2_per_kWh_AD* 277.78

    results_LCA[sp]["Upgrading_infrastructure_CO2"] = Upgrading_infrastructure_kgCO2
    results_LCA[sp]["AD_infrastructure_CO2"] = AD_infrastructure_kgCo2

    #print(f"\n--- {sp} ---")
    #print("Infrastructure CHP (kg CO2/t):", round(Upgrading_infrastructure_kgCO2, 2))
    #print("Infrastructure AD (kg CO2/t):", round(AD_infrastructure_kgCo2, 2))



#Poststorage

results_per_species_poststorage = {}
CH4_after_AD_m3={}
N2O_after_AD_kgN={}

for sp, tFM in species_tonnes.items():
    if tFM <= 0:
        continue

    # 1) Pull pre-storage results for this species
    res_pre = results_per_species[sp]
    pre_ch4_kg = float(res_pre["total"]["ch4_kg_daily"].sum())
    pre_ch4_m3 = pre_ch4_kg / RHO_CH4

    pre_n2o_kg = float(res_pre["total"]["n2o_kg_daily"].sum())
    pre_n2o_Nkg = pre_n2o_kg * (28.0 / 44.0)

    # 2) Residual potentials after AD
    # Available methane potential per tonne (CH-mix) minus pre-storage CH4 minus net captured in AD
    remaining_m3 = max(biomethane_yield_ch_mix[sp] - pre_ch4_m3 - net_biomethane_m3[sp], 0.0)
    CH4_after_AD_m3[sp] = remaining_m3

    # N after AD: total N minus pre-storage N2O-N loss (you can refine with NH3 if you include it)
    N_after = max(N_content[sp] - pre_n2o_Nkg, 0.0)
    N2O_after_AD_kgN[sp] = N_after

    # 3) Build digestate systems explicitly (we override potentials directly)
    #    Use the same storage shares per species, but with FACTORS_POST
    systems_sp_post = []
    for short, share in storage_share[sp].items():
        if share <= 0:
            continue
        storage_type = STORAGE_NAME_MAP[short]

        systems_sp_post.append({
            "species": sp,
            "storage_type": storage_type,
            "climate_zone": "15",
            # residual methane potential going into digestate storage (split by share)
            "ch4_potential": remaining_m3 *share,  # units = Nm3_CH4 per t FM
            "ch4_potential_unit": "Nm3_CH4",
            # residual N going into digestate storage (split by share)
            "total_N_kg_y": N_after *share,  # kg N per t FM
            "days_summer": 30,
            "days_winter": 180,
            "ch4_cum_funcs": (f_su_ch4, f_wi_ch4),
            "n2o_cum_funcs": (f_su_n2o, f_wi_n2o),
            "factors": FACTORS_POST,  # << use POST factors here
        })

    # 4) Run digestate storage
    res_post = compute_daily_storage_emissions_multi(systems_sp_post, year=2025)
    results_per_species_poststorage[sp] = res_post

    # 5) Report
    total_ch4_post = float(res_post["total"]["ch4_kg_daily"].sum())
    total_n2o_post = float(res_post["total"]["n2o_kg_daily"].sum())
    results_LCA[sp]["post_storage_CH4"] = total_ch4_post
    results_LCA[sp]["post_storage_N2O"] = total_n2o_post

    # print(f"\n--- POST-STORAGE (digestate) {sp} ---")
    # print("Residual CH4 potential entering storage (m3/t):", round(remaining_m3, 3))
    # print("Residual N entering storage (kg N/t):         ", round(N_after, 3))
    # print("Post-storage CH4 (kg/t):                      ", round(total_ch4_post, 3))
    # print("Post-storage N2O (kg/t):                      ", round(total_n2o_post, 3))





#Field application emissions

df_rows = []

for sp, res_sp in results_per_species.items():

    # --- 1) N nach AD und nach Post-Storage ---
    res_post = results_per_species_poststorage[sp]
    post_n2o_kg = float(res_post["total"]["n2o_kg_daily"].sum())
    post_n2o_N = post_n2o_kg * (28 / 44)

    # N nach AD (vor Post-Storage) hatten wir gespeichert:
    N_after_AD = N2O_after_AD_kgN[sp]

    # Jetzt N available vor Ausbringung:
    N_before_field = max(N_after_AD - post_n2o_N, 0.0)

    # ---- EXACTLY match spreadsheet logic (do NOT subtract storage N2O-N here) ----
    N_initial = N_content[sp]

    # weighted plant-availability fraction per species
    plant_avail_fraction = 0.0
    for short, share in storage_share[sp].items():
        pa = n_plant_available.get(short, {}).get(sp, None)
        if pa is not None:
            plant_avail_fraction += share * pa

    # 1) "N verfügbar kgN" (your sheet): N_initial * frac * 0.5
    N_available = N_before_field * plant_avail_fraction * 0.5

    # 2) NH3 emissions (kg NH3-N) = N_available * 0.35
    NH3_N = N_available * 0.5 *0.7

    # 3) N2O after land application (kg N2O/t)
    N2O_after = (N_available - NH3_N) * 0.1 * (44 / 28)
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


#Total LCA:
GWP_CH4=27
GWP_N2O=273


for sp in results_LCA:
    Pre_storage = (results_LCA[sp]["pre_storage_CH4"] *GWP_CH4) + (results_LCA[sp]["pre_storage_N2O"] *GWP_N2O)

    Transport= (results_LCA[sp]["transport_CO2"])

    AD_Methane_losses= (results_LCA[sp]["AD_methane_slip_CH4"]*GWP_CH4)

    Construction_operation_AD=(results_LCA[sp]["AD_electricity_use_CO2"])+(results_LCA[sp]["AD_infrastructure_CO2"])

    Construction_operation_Upgrading=(results_LCA[sp]["Upgrading_infrastructure_CO2"])

    Energy_benefits=(results_LCA[sp]["Upgrading_electricity_benefit_CO2"])


    Post_storage=(results_LCA[sp]["post_storage_CH4"] *GWP_CH4) + (results_LCA[sp]["post_storage_N2O"] *GWP_N2O)

    Field_application=(results_LCA[sp]["N2O_field"]*GWP_N2O)

    GWP_Total = Pre_storage + Transport + AD_Methane_losses + Construction_operation_AD + Construction_operation_Upgrading + Energy_benefits + Post_storage + Field_application

# Komponenten zurückschreiben (optional, aber praktisch)
    results_LCA[sp]["GWP_prestorage"] = Pre_storage
    results_LCA[sp]["GWP_transport"] = Transport
    results_LCA[sp]["GWP_AD_methane_losses"] = AD_Methane_losses
    results_LCA[sp]["GWP_AD_construction_operation"] = Construction_operation_AD
    results_LCA[sp]["GWP_Upgrading_construction_operation"] = Construction_operation_Upgrading
    results_LCA[sp]["GWP_poststorage"] = Post_storage
    results_LCA[sp]["GWP_field_application"] = Field_application
    results_LCA[sp]["GWP_energy_benefits"] = Energy_benefits  # negativ in Summe
    results_LCA[sp]["GWP_Total"] = GWP_Total


# Übersichtstabelle (nur relevante Spalten)
cols = [
    "GWP_prestorage",
    "GWP_transport",
    "GWP_AD_methane_losses",
    "GWP_AD_construction_operation",
    "GWP_Upgrading_construction_operation",
    "GWP_poststorage",
    "GWP_field_application",
    "GWP_energy_benefits",
    "GWP_Total",
]


pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)
df_lca = pd.DataFrame(results_LCA).T.reindex(columns=cols)



def precompute_upgrading_lca_factors_for_climate(
    climate_zone: str,
    days_pre_summer: int = 12,
    days_post_summer: int = 30,
):
    """
    Returns:
      factors[species] = dict with:
        - GWP_Total_kgCO2eq_per_tFM
        - components (kgCO2eq per tFM)
    Notes:
      - Winter is fixed to 180 days (like you decided)
      - Benefits are returned as NEGATIVE numbers (credits)
      - All outputs are kg CO2-eq per t fresh matter
    """
    # constants / shared
    days_pre_winter  = days_pre_summer
    days_post_winter = 180

    upgrading_efficiency =0.96
    biomethane_substitution_kgCO2_per_m3= 0.633
    electricity_co2_g_per_kWh=128
    AD_EFF=0.85
    SLIP= 0.0105


    SPECIES = ["Cattle", "Horses", "Sheep", "Goats", "Pigs", "Poultry"]

    # --- 1) PRE-STORAGE (tFM=1) --------------------------------------------
    results_pre = {}
    for sp in SPECIES:
        systems_sp = systems_from_species_masses(
            {sp: 1.0},
            climate_zone,
            days_pre_summer,
            days_pre_winter,
            f_su_ch4, f_wi_ch4,
            f_su_n2o, f_wi_n2o
        )
        results_pre[sp] = compute_daily_storage_emissions_multi(systems_sp, year=2025)

    # --- 2) Transport per tonne --------------------------------------------
    transport_co2e_per_t = transport_kgCO2e_per_tonne(distance_one_way_km=7.5)

    # --- 3) AD + Upgrading + benefits + infra -------------------------------
    CH4_Biogas = 0.625
    RHO_CH4 = 0.67

    # your AD energy demand assumptions (same as in snippet)
    electricity_demand_kJ_per_m3 = 576
    heat_demand_kJ_per_m3 = 3500

    # you had this: heat demand uses 0.95 factor in upgrading
    heat_demand_factor = 0.95

    # Infra assumptions (from your snippet)
    Upgrading_infrastructure_kgCO2_per_m3_biomethane = 0.15
    AD_infrastructure_total_kgCO2 = 42236.193476516

    # YCHP_el as proxy to compute electricity_generated_GJ even in upgrading
    CHP_el_proxy = 0.34

    # GWPs
    GWP_CH4 = 27
    GWP_N2O = 273

    factors = {}

    for sp in SPECIES:
        res_pre = results_pre[sp]
        pre_ch4_kg = float(res_pre["total"]["ch4_kg_daily"].sum())
        pre_n2o_kg = float(res_pre["total"]["n2o_kg_daily"].sum())

        pre_ch4_m3 = pre_ch4_kg / RHO_CH4
        pre_n2o_Nkg = pre_n2o_kg * (28/44)

        # --- AD net methane + slip (your logic)
        net_m3 = max(biomethane_yield_ch_mix[sp] - pre_ch4_m3, 0.0) * AD_EFF
        slip_kg = net_m3 * SLIP * RHO_CH4

        # biogas produced (your logic)
        biogas_produced_m3 = (net_m3 - (slip_kg / RHO_CH4)) / CH4_Biogas

        # biomethane after upgrading
        biomethane_m3 = biogas_produced_m3 * upgrading_efficiency * CH4_Biogas

        # energy for AD (your logic)
        electricity_demand_kWh = biogas_produced_m3 * electricity_demand_kJ_per_m3 / 1000 / 3.6
        heat_demand_GJ = biogas_produced_m3 * heat_demand_kJ_per_m3 / 1_000_000 * heat_demand_factor

        electricity_use_kgCO2 = electricity_demand_kWh * electricity_co2_g_per_kWh / 1000

        # --- benefit: biomethane substitution (your logic)
        # convert heat demand into biomethane equivalent and subtract from produced biomethane
        # (your 9.97 kWh per m3? you used 277.78 / 9.97)
        biomethane_for_heat_m3 = (heat_demand_GJ * 277.78) / 9.97
        biomethane_after_heat_m3 = max(biomethane_m3 - biomethane_for_heat_m3, 0.0)

        biomethane_benefit_kgCO2 = biomethane_after_heat_m3 * biomethane_substitution_kgCO2_per_m3
        Benefits = -biomethane_benefit_kgCO2  # NEGATIVE credit

        # --- infrastructure (your logic)
        Upgrading_infra_kgCO2 = biomethane_m3 * Upgrading_infrastructure_kgCO2_per_m3_biomethane

        # AD infra allocation (replicate your approach)
        # You compute an electricity_generated_GJ proxy from biogas energy * CHP_el.
        biogas_yield_GJ = biogas_produced_m3 * CH4_Biogas * 35.883 / 1000
        electricity_generated_GJ_proxy = biogas_yield_GJ * CHP_el_proxy * (8000/8670)

        kgCo2_per_kWh_AD = AD_infrastructure_total_kgCO2 / (50 * 8000 * 20)
        AD_infra_kgCO2 = electricity_generated_GJ_proxy * kgCo2_per_kWh_AD * 277.78

        # --- POST-STORAGE (digestate) + FIELD (same as CHP) -------------------
        remaining_m3 = max(biomethane_yield_ch_mix[sp] - pre_ch4_m3 - net_m3, 0.0)
        N_after = max(N_content[sp] - pre_n2o_Nkg, 0.0)

        systems_post = []
        for short, share in storage_share[sp].items():
            if share <= 0:
                continue
            systems_post.append({
                "species": sp,
                "storage_type": STORAGE_NAME_MAP[short],
                "climate_zone": str(climate_zone),
                "ch4_potential": remaining_m3 * share,
                "ch4_potential_unit": "Nm3_CH4",
                "total_N_kg_y": N_after * share,
                "days_summer": days_post_summer,
                "days_winter": days_post_winter,
                "ch4_cum_funcs": (f_su_ch4, f_wi_ch4),
                "n2o_cum_funcs": (f_su_n2o, f_wi_n2o),
                "factors": FACTORS_POST,
            })

        res_post = compute_daily_storage_emissions_multi(systems_post, year=2025)
        post_ch4_kg = float(res_post["total"]["ch4_kg_daily"].sum())
        post_n2o_kg = float(res_post["total"]["n2o_kg_daily"].sum())
        post_n2o_N = post_n2o_kg * (28/44)

        # Field N2O
        N_before_field = max(N_after - post_n2o_N, 0.0)

        plant_avail_fraction = 0.0
        for short, share in storage_share[sp].items():
            pa = n_plant_available.get(short, {}).get(sp, None)
            if pa is not None:
                plant_avail_fraction += share * pa

        N_available = N_before_field * plant_avail_fraction * 0.5
        NH3_N = N_available * 0.5 * 0.7
        N2O_field_kg = max((N_available - NH3_N) * 0.1 * (44/28), 0.0)

        # --- components in kgCO2eq/tFM ---------------------------------------
        Pre_storage = pre_ch4_kg*GWP_CH4 + pre_n2o_kg*GWP_N2O
        Transport   = transport_co2e_per_t
        AD_slip     = slip_kg*GWP_CH4
        AD_const_op = electricity_use_kgCO2 + AD_infra_kgCO2
        Upg_const   = Upgrading_infra_kgCO2
        Post_storage= post_ch4_kg*GWP_CH4 + post_n2o_kg*GWP_N2O
        Field_app   = N2O_field_kg*GWP_N2O

        Total = (Pre_storage + Transport + AD_slip + AD_const_op + Upg_const
                 + Benefits + Post_storage + Field_app)

        factors[sp] = {
            "GWP_Total_kgCO2eq_per_tFM": Total,
            "GWP_prestorage": Pre_storage,
            "GWP_transport": Transport,
            "GWP_AD_methane_losses": AD_slip,
            "GWP_AD_construction_operation": AD_const_op,
            "GWP_Upgrading_construction_operation": Upg_const,
            "GWP_poststorage": Post_storage,
            "GWP_field_application": Field_app,
            "GWP_energy_benefits": Benefits,
        }

    return factors
