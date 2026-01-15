import geopandas as gpd
import pandas as pd

# DM and oDM: in Tonnes/year

#Lower calorific value of oDM:
CV_lower_oDM=21 #MJ/kg oDM (Thees et al., 2017).

#Lower calorific value of methane:
CV_lower_methane=35.883 # MJ/m3 (Thees et al., 2017).

#-------------------------------------------------------------------
#Parameters for Cattle

#Manure production

#0: m3/year of slurry production per year per cow (Only slurry)
#1: m3/year of slurry production per year per cow (Slurry and manure)
#2: t/year of slurry production per year per cow (Slurry and manure)
#3: t/year of slurry production per year per cow (Only manure)

manure_production_cattle = {
    "cattle_1": {"s": 23, "sm1": 11, "sm2": 8.9, "m": 21},
    "cattle_2": {"s": 17, "sm1": 8.7, "sm2": 6.7, "m": 16},
    "cattle_3": {"s": 8, "sm1": 4, "sm2": 3.2, "m": 7.6},
    "cattle_4": {"s": 4.8, "sm1": 2.4, "sm2": 2, "m": 4.6},
    "cattle_5": {"s": 10, "sm1": 0, "sm2": 0, "m": 11},
}
#Barn system
#0: [%] Tethered barn with only slurry production
#1: [%] Tethered barn with slurry and manure production
#2: [%] Freestall barn with only slurry production
#3: [%] Freestall barn with slurry and manure production
#4: [%] Feestall barn with deep litter manure

stable_system_cattle = {
    "cattle_1": [0.13, 0.29, 0.45, 0.12, 0.01],
    "cattle_2": [0.03, 0.13, 0.28, 0.51, 0.05],
    "cattle_3": [0.03, 0.20, 0.31, 0.39, 0.07],
    "cattle_4": [0.01, 0.17, 0.19, 0.50, 0.13],
    "cattle_5": [0.01, 0.12, 0.21, 0.57, 0.08],
}

# Define indices for each category
categories_cattle_stable= {
    "only_slurry": [0, 2],        # Only slurry production
    "manure_slurry": [1, 3],        # Slurry and manure production
    "only_manure": [4],      # Only manure
}



stable_cattle_total = {}

# Calculate the sum for each cattle type across all categories
for cattle in stable_system_cattle:
    # Initialize an empty dictionary for each cattle type
    stable_cattle_total[cattle] = {
        category: round(sum(stable_system_cattle[cattle][i] for i in indices), 2)
        for category, indices in categories_cattle_stable.items()
    }


#-------------------------------------------------------------------
#Parameters for Horse
manure_production_horse = {
    "horse_1": {"s": 0, "sm1": 0, "sm2": 0, "m": 10},
    "horse_2": {"s": 0, "sm1": 0, "sm2": 0, "m": 12},
}

#-------------------------------------------------------------------
#Parameters for Sheep
manure_production_sheep = {
    "sheep_1": {"s": 0, "sm1": 0, "sm2": 0, "m": 2.3},
    "sheep_2": {"s": 0, "sm1": 0, "sm2": 0, "m": 1.7},
}
#-------------------------------------------------------------------
#Parameters for Goats
manure_production_goats = {
    "goats": {"s": 0, "sm1": 0, "sm2": 0, "m": 1.7},
}
#-------------------------------------------------------------------
#Parameters for Pigs
manure_production_pigs = {
    "pigs_1": {"s": 7.5, "sm1": 0, "sm2": 0, "m": 0},
    "pigs_2": {"s": 7.5, "sm1": 0, "sm2": 0, "m": 0},
    "pigs_3": {"s": 1.6, "sm1": 0, "sm2": 0, "m": 0},
}

#-------------------------------------------------------------------
#Parameters for Poultry

#s=manure belt, m=floor system/manure pit
manure_production_poultry = {
    "poultry_1": {"s": 2.7, "sm1": 0, "sm2": 0, "m": 1.5}, #100 laying hen places
    "poultry_2": {"s": 0, "sm1": 0, "sm2": 0, "m": 0.8},#100 fattening chicken places
    "poultry_3": {"s": 0, "sm1": 0, "sm2": 0, "m": 3},#100 fattening turkey places
}

stable_system_poultry = {
    "poultry_1": {"floor_system": 0.1, "manure_belt": 0.9}, #floor system=manure, manure_belt=slurry
}


#-------------------------------------------------------------------
#Parameters for various livestock

#DM and oDM content for various livestocks
#0: [kg/m3 slurry or kg/t manure] DM
#1: [kg/m3 slurry or kg/t manure] oDM
DM_oDM= {
    "slurry_cattle": {"DM": 90, "oDM": 70},             #Cows/Breeding cattle
    "slurry_lowstraw_cattle": {"DM": 75, "oDM": 40},    #Cows/Breeding cattle
    "manure_cattle": {"DM": 210, "oDM": 175},           #Cows/Breeding cattle
    "manure_cattle_4":{"DM": 200, "oDM": 150},          #Calves
    "liquid_cattle_5": {"DM": 90, "oDM": 65},           #Fattening cattle
    "manure_cattle_5": {"DM": 210, "oDM": 155},         #Fattening cattle
    "manure_horse": {"DM": 350, "oDM": 300},            #Fresh horse manure
    "manure_sheep": {"DM": 270, "oDM": 200},            #Sheep manure
    "manure_goat": {"DM": 270, "oDM": 200},             #Goat manure
    "pigs": {"DM": 50, "oDM": 33},                      #Breeding pig
    "pigs_3": {"DM": 50, "oDM": 36},                    #Fattening pig
    "poultry_1_manurebelt": {"DM": 350, "oDM": 250},    #Hens/Young hens manure (manure belt)
    "poultry_1_floorsystem": {"DM": 500, "oDM": 330},   #Hens/Young hens manure (floor system)
    "poultry_2": {"DM": 650, "oDM": 440},               #Fattening chicken
    "poultry_3": {"DM": 600, "oDM": 400},               #Turkey manure

}

#Methane yield for the various livestock
#[Nl/kg oDM]
methane_yield = {
    "Cattle_slurry": {"MY": 257}, #364 257
    "Cattle_manure": {"MY": 305}, #359 305
    "Cattle_5_slurry": {"MY": 238}, #326 238
    "Cattle_5_manure": {"MY": 303},#355 303
    "Horse_manure": {"MY": 277},#298 277
    "Sheep_manure": {"MY": 240},
    "Goat_manure": {"MY": 240}, #Assumption=Sheep_manure
    "Pigs_slurry": {"MY": 331},#411 331
    "poultry_manurebelt":{"MY": 290},
    "poultry_floorsystem":{"MY": 270 }, #259 280 #Assumption: Geflügelmist for fattening chicken and turkey (poultry_2 and poultry_3)
}



#Reduction factors due to pasture grazing for various livestock [%]
reduction_factors = {
    "Cattle_1": {"RF": 0.841},
    "Cattle_2": {"RF": 0.698},
    "Cattle_3": {"RF": 0.663},
    "Cattle_4": {"RF": 0.778},
    "Cattle_5": {"RF": 0.963},
    "Horses_1": {"RF": 0.657},
    "Horses_2": {"RF": 0.797},
    "Sheep_1": {"RF": 0.738},
    "Sheep_2": {"RF": 0.563},
    "Goats": {"RF": 0.676},
}



def calculate_potential_env_imp(input_shapefile):
    # Load the shapefile with animal numbers per polygon
    gdf = gpd.read_file(input_shapefile)

    # Initialize a dictionary to store calculated columns
    calc_columns = {}


    ##CATTLE ------------------------------------------------------------------------------------------------------------------------------------
    #Cattle_1
    calc_columns['Slurry_DM_cattle_1'] = ((gdf['Cattle_1'] * manure_production_cattle["cattle_1"]["s"] *stable_cattle_total["cattle_1"]["only_slurry"]*DM_oDM["slurry_cattle"]["DM"]/1000)+
                                      (gdf['Cattle_1'] * manure_production_cattle["cattle_1"]["sm1"] *stable_cattle_total["cattle_1"]["manure_slurry"]*DM_oDM["slurry_lowstraw_cattle"]["DM"]/1000))
    calc_columns['Manure_DM_cattle_1'] = ((gdf['Cattle_1'] * manure_production_cattle["cattle_1"]["sm2"] *stable_cattle_total["cattle_1"]["manure_slurry"]*DM_oDM["manure_cattle"]["DM"]/1000)
                                      + (gdf['Cattle_1'] * manure_production_cattle["cattle_1"]["m"] * stable_cattle_total["cattle_1"]["only_manure"]*DM_oDM["manure_cattle"]["DM"]/1000))
    calc_columns['Slurry_oDM_cattle_1']= ((gdf['Cattle_1'] * manure_production_cattle["cattle_1"]["s"] *stable_cattle_total["cattle_1"]["only_slurry"]*DM_oDM["slurry_cattle"]["oDM"]/1000)
                                      +(gdf['Cattle_1'] * manure_production_cattle["cattle_1"]["sm1"] *stable_cattle_total["cattle_1"]["manure_slurry"]*DM_oDM["slurry_lowstraw_cattle"]["oDM"]/1000))
    calc_columns['Manure_oDM_cattle_1']=((gdf['Cattle_1'] * manure_production_cattle["cattle_1"]["sm2"] *stable_cattle_total["cattle_1"]["manure_slurry"]*DM_oDM["manure_cattle"]["oDM"]/1000)
                                     + (gdf['Cattle_1'] * manure_production_cattle["cattle_1"]["m"] * stable_cattle_total["cattle_1"]["only_manure"]*DM_oDM["manure_cattle"]["oDM"]/1000))
    #Cattle_2
    calc_columns['Slurry_DM_cattle_2'] = ((gdf['Cattle_2'] * manure_production_cattle["cattle_2"]["s"] * stable_cattle_total["cattle_2"]["only_slurry"] *DM_oDM["slurry_cattle"]["DM"] / 1000)
                                      + (gdf['Cattle_2'] * manure_production_cattle["cattle_2"]["sm1"] * stable_cattle_total["cattle_2"]["manure_slurry"] * DM_oDM["slurry_lowstraw_cattle"]["DM"] / 1000))
    calc_columns['Manure_DM_cattle_2'] = ((gdf['Cattle_2'] * manure_production_cattle["cattle_2"]["sm2"] * stable_cattle_total["cattle_2"]["manure_slurry"] * DM_oDM["manure_cattle"]["DM"] / 1000)
                                      + (gdf['Cattle_2'] * manure_production_cattle["cattle_2"]["m"] * stable_cattle_total["cattle_2"]["only_manure"] *DM_oDM["manure_cattle"]["DM"] / 1000))
    calc_columns['Slurry_oDM_cattle_2'] = ((gdf['Cattle_2'] * manure_production_cattle["cattle_2"]["s"] * stable_cattle_total["cattle_2"]["only_slurry"] *DM_oDM["slurry_cattle"]["oDM"] / 1000)
                                       + (gdf['Cattle_2'] * manure_production_cattle["cattle_2"]["sm1"] * stable_cattle_total["cattle_2"]["manure_slurry"] * DM_oDM["slurry_lowstraw_cattle"]["oDM"] / 1000))
    calc_columns['Manure_oDM_cattle_2'] = ((gdf['Cattle_2'] * manure_production_cattle["cattle_2"]["sm2"] * stable_cattle_total["cattle_2"]["manure_slurry"] * DM_oDM["manure_cattle"]["oDM"] / 1000)
                                       + (gdf['Cattle_2'] * manure_production_cattle["cattle_2"]["m"] * stable_cattle_total["cattle_2"]["only_manure"] * DM_oDM["manure_cattle"]["oDM"] / 1000))
    #Cattle_3

    calc_columns['Slurry_DM_cattle_3'] = ((gdf['Cattle_3'] * manure_production_cattle["cattle_3"]["s"] * stable_cattle_total["cattle_3"]["only_slurry"] *DM_oDM["slurry_cattle"]["DM"] / 1000)
                                      + (gdf['Cattle_3'] * manure_production_cattle["cattle_3"]["sm1"] * stable_cattle_total["cattle_3"]["manure_slurry"] * DM_oDM["slurry_lowstraw_cattle"]["DM"] / 1000))
    calc_columns['Manure_DM_cattle_3'] = ((gdf['Cattle_3'] * manure_production_cattle["cattle_3"]["sm2"] * stable_cattle_total["cattle_3"]["manure_slurry"] * DM_oDM["manure_cattle"]["DM"] / 1000)
                                      + (gdf['Cattle_3'] * manure_production_cattle["cattle_3"]["m"] * stable_cattle_total["cattle_3"]["only_manure"] * DM_oDM["manure_cattle"]["DM"] / 1000))
    calc_columns['Slurry_oDM_cattle_3'] = ((gdf['Cattle_3'] * manure_production_cattle["cattle_3"]["s"] * stable_cattle_total["cattle_3"]["only_slurry"] *DM_oDM["slurry_cattle"]["oDM"] / 1000)
                                       + (gdf['Cattle_3'] * manure_production_cattle["cattle_3"]["sm1"] * stable_cattle_total["cattle_3"]["manure_slurry"] * DM_oDM["slurry_lowstraw_cattle"]["oDM"] / 1000))
    calc_columns['Manure_oDM_cattle_3'] = ((gdf['Cattle_3'] * manure_production_cattle["cattle_3"]["sm2"] * stable_cattle_total["cattle_3"]["manure_slurry"] * DM_oDM["manure_cattle"]["oDM"] / 1000)
                                       + (gdf['Cattle_3'] * manure_production_cattle["cattle_3"]["m"] * stable_cattle_total["cattle_3"]["only_manure"] * DM_oDM["manure_cattle"]["oDM"] / 1000))

    # Cattle_4

    calc_columns['Slurry_DM_cattle_4'] = ((gdf['Cattle_4'] * manure_production_cattle["cattle_4"]["s"] * stable_cattle_total["cattle_4"]["only_slurry"] *DM_oDM["slurry_cattle"]["DM"] / 1000)
                                      + (gdf['Cattle_4'] * manure_production_cattle["cattle_4"]["sm1"] * stable_cattle_total["cattle_4"]["manure_slurry"] * DM_oDM["slurry_lowstraw_cattle"]["DM"] / 1000))
    calc_columns['Manure_DM_cattle_4'] = ((gdf['Cattle_4'] * manure_production_cattle["cattle_4"]["sm2"] * stable_cattle_total["cattle_4"][ "manure_slurry"] * DM_oDM["manure_cattle_4"]["DM"] / 1000)
                                      + (gdf['Cattle_4'] * manure_production_cattle["cattle_4"]["m"] * stable_cattle_total["cattle_4"]["only_manure"] * DM_oDM["manure_cattle_4"]["DM"] / 1000))
    calc_columns['Slurry_oDM_cattle_4'] = ((gdf['Cattle_4'] * manure_production_cattle["cattle_4"]["s"] * stable_cattle_total["cattle_4"]["only_slurry"] *DM_oDM["slurry_cattle"]["oDM"] / 1000)
                                       + (gdf['Cattle_4'] * manure_production_cattle["cattle_4"]["sm1"] * stable_cattle_total["cattle_4"]["manure_slurry"] * DM_oDM["slurry_lowstraw_cattle"]["oDM"] / 1000))
    calc_columns['Manure_oDM_cattle_4'] = ((gdf['Cattle_4'] * manure_production_cattle["cattle_4"]["sm2"] * stable_cattle_total["cattle_4"]["manure_slurry"] * DM_oDM["manure_cattle_4"]["oDM"] / 1000)
                                       + (gdf['Cattle_4'] * manure_production_cattle["cattle_4"]["m"] * stable_cattle_total["cattle_4"]["only_manure"] * DM_oDM["manure_cattle_4"]["oDM"] / 1000))


    # Cattle_5
    calc_columns['Slurry_DM_cattle_5'] = ((gdf['Cattle_5'] * manure_production_cattle["cattle_5"]["s"] * stable_cattle_total["cattle_5"]["only_slurry"] *DM_oDM["liquid_cattle_5"]["DM"] / 1000)
                                      + (gdf['Cattle_5'] * manure_production_cattle["cattle_5"]["s"]*0.4 * stable_cattle_total["cattle_5"]["manure_slurry"] * DM_oDM["slurry_lowstraw_cattle"]["DM"] / 1000))
    calc_columns['Manure_DM_cattle_5'] = ((gdf['Cattle_5'] * manure_production_cattle["cattle_5"]["m"]*0.6 * stable_cattle_total["cattle_5"][ "manure_slurry"] * DM_oDM["manure_cattle_5"]["DM"] / 1000)
                                      + (gdf['Cattle_5'] * manure_production_cattle["cattle_5"]["m"] * stable_cattle_total["cattle_5"]["only_manure"] * DM_oDM["manure_cattle_5"]["DM"] / 1000))
    calc_columns['Slurry_oDM_cattle_5'] = ((gdf['Cattle_5'] * manure_production_cattle["cattle_5"]["s"] * stable_cattle_total["cattle_5"]["only_slurry"] *DM_oDM["liquid_cattle_5"]["oDM"] / 1000)
                                       + (gdf['Cattle_5'] * manure_production_cattle["cattle_5"]["s"]*0.4 * stable_cattle_total["cattle_5"]["manure_slurry"] * DM_oDM["slurry_lowstraw_cattle"]["oDM"] / 1000))
    calc_columns['Manure_oDM_cattle_5'] = ((gdf['Cattle_5'] * manure_production_cattle["cattle_5"]["m"] *0.6* stable_cattle_total["cattle_5"]["manure_slurry"] * DM_oDM["manure_cattle_5"]["oDM"] / 1000)
                                      + (gdf['Cattle_5'] * manure_production_cattle["cattle_5"]["m"] *stable_cattle_total["cattle_5"]["only_manure"] * DM_oDM["manure_cattle_5"]["oDM"] / 1000))

    calc_columns['Cattle_total_oDM_slurry'] = (calc_columns['Slurry_oDM_cattle_1']+calc_columns['Slurry_oDM_cattle_2']+calc_columns['Slurry_oDM_cattle_3']+
                                           calc_columns['Slurry_oDM_cattle_4'] +calc_columns['Slurry_oDM_cattle_5'])

    calc_columns['Cattle_total_oDM_manure'] = (calc_columns['Manure_oDM_cattle_1'] + calc_columns['Manure_oDM_cattle_2'] + calc_columns['Manure_oDM_cattle_3'] +
                                          calc_columns['Manure_oDM_cattle_4'] + calc_columns['Manure_oDM_cattle_5'])

    calc_columns['Cattle_available_oDM_slurry'] = ((calc_columns['Slurry_oDM_cattle_1'] * reduction_factors['Cattle_1']['RF'])+ (calc_columns['Slurry_oDM_cattle_2'] * reduction_factors['Cattle_2']['RF'])
                                               + (calc_columns['Slurry_oDM_cattle_3'] * reduction_factors['Cattle_3']['RF'])
                                               +  (calc_columns['Slurry_oDM_cattle_4'] * reduction_factors['Cattle_4']['RF'])
                                               + (calc_columns['Slurry_oDM_cattle_5']* reduction_factors['Cattle_5']['RF']))

    calc_columns['Cattle_available_oDM_manure'] = ((calc_columns['Manure_oDM_cattle_1'] * reduction_factors['Cattle_1']['RF'])
                                               + (calc_columns['Manure_oDM_cattle_2'] * reduction_factors['Cattle_2']['RF'])
                                               + (calc_columns['Manure_oDM_cattle_3'] * reduction_factors['Cattle_3']['RF'])
                                               + (calc_columns['Manure_oDM_cattle_4'] * reduction_factors['Cattle_4']['RF'])
                                               + (calc_columns['Manure_oDM_cattle_5'] * reduction_factors['Cattle_5']['RF']))


    #Primary energy (theoretical potential) total cattle in GJ
    calc_columns['Cattle_primary_energy_theoretical']= (calc_columns['Cattle_total_oDM_slurry']+ calc_columns['Cattle_total_oDM_manure'])* CV_lower_oDM

    #Pot. Biomethane Yield (theoretical potential) total cattle in m3
    calc_columns['Cattle_biomethane_yield_theoretical_m3'] = (((calc_columns['Slurry_oDM_cattle_1']+calc_columns['Slurry_oDM_cattle_2']+calc_columns['Slurry_oDM_cattle_3']+
                                                        calc_columns['Slurry_oDM_cattle_4']) * methane_yield["Cattle_slurry"]["MY"])
                                                         +((calc_columns['Manure_oDM_cattle_1'] + calc_columns['Manure_oDM_cattle_2'] + calc_columns['Manure_oDM_cattle_3'] +
                                                        calc_columns['Manure_oDM_cattle_4'] ) * methane_yield["Cattle_manure"]["MY"])
                                                          +((calc_columns['Slurry_oDM_cattle_5'])*methane_yield["Cattle_5_slurry"]["MY"])
                                                          +((calc_columns['Manure_oDM_cattle_5']) * methane_yield["Cattle_5_manure"]["MY"]))


    # Pot. Biomethane Yield (theoretical potential) total cattle in GJ
    calc_columns['Cattle_biomethane_yield_theoretical_GJ'] = calc_columns['Cattle_biomethane_yield_theoretical_m3']*CV_lower_methane/1000

    #----------------------------------------------------------------------
    # Primary energy (available potential) total cattle in GJ
    calc_columns['Cattle_primary_energy_available'] = (calc_columns['Cattle_available_oDM_slurry'] + calc_columns['Cattle_available_oDM_manure']) * CV_lower_oDM

    # Pot. Biomethane Yield (available potential) total cattle in m3
    calc_columns['Cattle_biomethane_yield_available_m3'] = (calc_columns['Cattle_available_oDM_slurry'] * methane_yield["Cattle_slurry"]["MY"]
                                                      + calc_columns['Cattle_available_oDM_manure'] * methane_yield["Cattle_manure"]["MY"])
    # Pot. Biomethane Yield (available potential) total cattle in GJ
    calc_columns['Cattle_biomethane_yield_available_GJ'] = calc_columns['Cattle_biomethane_yield_available_m3'] * CV_lower_methane / 1000



    ##HORSES ------------------------------------------------------------------------------------------------------------------------------------
    # Horses_1
    calc_columns['Manure_DM_horses_1'] = (gdf['Horses_1'] * manure_production_horse["horse_1"]["m"] *DM_oDM["manure_horse"]["DM"] / 1000)

    calc_columns['Manure_oDM_horses_1'] = (gdf['Horses_1'] * manure_production_horse["horse_1"]["m"] *DM_oDM["manure_horse"]["oDM"] / 1000)

    # Horses_2
    calc_columns['Manure_DM_horses_2'] = (gdf['Horses_2'] * manure_production_horse["horse_2"]["m"] * DM_oDM["manure_horse"]["DM"] / 1000)

    calc_columns['Manure_oDM_horses_2'] = (gdf['Horses_2'] * manure_production_horse["horse_2"]["m"] * DM_oDM["manure_horse"]["oDM"] / 1000)




    calc_columns['Horses_total_oDM_manure'] = (calc_columns['Manure_oDM_horses_1'] + calc_columns['Manure_oDM_horses_2'] )

    calc_columns['Horses_available_oDM_manure'] = ((calc_columns['Manure_oDM_horses_1'] * reduction_factors['Horses_1']['RF'])
                                               + (calc_columns['Manure_oDM_horses_2'] * reduction_factors['Horses_2']['RF']))


    # Primary energy (theoretical potential) total horse in GJ
    calc_columns['Horses_primary_energy_theoretical'] = (calc_columns['Horses_total_oDM_manure']) * CV_lower_oDM

    # Pot. Biomethane Yield (theoretical potential) total horse in m3
    calc_columns['Horses_biomethane_yield_theoretical_m3'] = (calc_columns['Horses_total_oDM_manure'] * methane_yield["Horse_manure"]["MY"])

    # Pot. Biomethane Yield (theoretical potential) total horse in GJ
    calc_columns['Horses_biomethane_yield_theoretical_GJ'] = calc_columns['Horses_biomethane_yield_theoretical_m3'] * CV_lower_methane / 1000

    # ----------------------------------------------------------------------
    # Primary energy (available potential) total horse in GJ
    calc_columns['Horses_primary_energy_available'] = (calc_columns['Horses_available_oDM_manure']) * CV_lower_oDM

    # Pot. Biomethane Yield (available potential) total horse in m3
    calc_columns['Horses_biomethane_yield_available_m3'] = (calc_columns['Horses_available_oDM_manure'] * methane_yield["Horse_manure"]["MY"])

    # Pot. Biomethane Yield (available potential) total horse in GJ
    calc_columns['Horses_biomethane_yield_available_GJ'] = calc_columns['Horses_biomethane_yield_available_m3'] * CV_lower_methane / 1000




    ##SHEEP ------------------------------------------------------------------------------------------------------------------------------------
    # Sheep_1
    calc_columns['Manure_DM_sheep_1'] = (gdf['Sheep_1'] * manure_production_sheep["sheep_1"]["m"] * DM_oDM["manure_sheep"]["DM"] / 1000)

    calc_columns['Manure_oDM_sheep_1'] = (gdf['Sheep_1'] * manure_production_sheep["sheep_1"]["m"] * DM_oDM["manure_sheep"]["oDM"] / 1000)

    # Sheep_2
    calc_columns['Manure_DM_sheep_2'] = (gdf['Sheep_2'] * manure_production_sheep["sheep_2"]["m"] * DM_oDM["manure_sheep"]["DM"] / 1000)

    calc_columns['Manure_oDM_sheep_2'] = (gdf['Sheep_2'] * manure_production_sheep["sheep_2"]["m"] * DM_oDM["manure_sheep"]["oDM"] / 1000)


    calc_columns['Sheep_total_oDM_manure'] = (calc_columns['Manure_oDM_sheep_1'] + calc_columns['Manure_oDM_sheep_2'])

    calc_columns['Sheep_available_oDM_manure'] = ((calc_columns['Manure_oDM_sheep_1'] * reduction_factors['Sheep_1']['RF'])
                                               + (calc_columns['Manure_oDM_sheep_2'] * reduction_factors['Sheep_2']['RF']))

    # Primary energy (theoretical potential) total sheep in GJ
    calc_columns['Sheep_primary_energy_theoretical'] = (calc_columns['Sheep_total_oDM_manure']) * CV_lower_oDM

    # Pot. Biomethane Yield (theoretical potential) total sheep in m3
    calc_columns['Sheep_biomethane_yield_theoretical_m3'] = (calc_columns['Sheep_total_oDM_manure'] * methane_yield["Sheep_manure"]["MY"])

    # Pot. Biomethane Yield (theoretical potential) total sheep in GJ
    calc_columns['Sheep_biomethane_yield_theoretical_GJ'] = calc_columns['Sheep_biomethane_yield_theoretical_m3'] * CV_lower_methane / 1000

    # ----------------------------------------------------------------------
    # Primary energy (available potential) total sheep in GJ
    calc_columns['Sheep_primary_energy_available'] = (calc_columns['Sheep_available_oDM_manure']) * CV_lower_oDM

    # Pot. Biomethane Yield (available potential) total sheep in m3
    calc_columns['Sheep_biomethane_yield_available_m3'] = (calc_columns['Sheep_available_oDM_manure'] * methane_yield["Sheep_manure"]["MY"])

    # Pot. Biomethane Yield (available potential) total sheep in GJ
    calc_columns['Sheep_biomethane_yield_available_GJ'] = calc_columns['Sheep_biomethane_yield_available_m3'] * CV_lower_methane / 1000

    ##GOATS ------------------------------------------------------------------------------------------------------------------------------------
    # Goats
    calc_columns['Manure_DM_goats'] = (gdf['Goats'] * manure_production_goats["goats"]["m"] * DM_oDM["manure_goat"]["DM"] / 1000)

    calc_columns['Manure_oDM_goats'] = (gdf['Goats'] * manure_production_goats["goats"]["m"] * DM_oDM["manure_goat"]["oDM"] / 1000)



    calc_columns['Goats_total_oDM_manure'] = calc_columns['Manure_oDM_goats']

    calc_columns['Goats_available_oDM_manure'] = (calc_columns['Goats_total_oDM_manure'] * reduction_factors['Goats']['RF'])


    # Primary energy (theoretical potential) total goats in GJ
    calc_columns['Goats_primary_energy_theoretical'] = (calc_columns['Goats_total_oDM_manure']) * CV_lower_oDM

    # Pot. Biomethane Yield (theoretical potential) total goats in m3
    calc_columns['Goats_biomethane_yield_theoretical_m3'] = (calc_columns['Goats_total_oDM_manure'] * methane_yield["Goat_manure"]["MY"])

    # Pot. Biomethane Yield (theoretical potential) total goats in GJ
    calc_columns['Goats_biomethane_yield_theoretical_GJ'] = calc_columns['Goats_biomethane_yield_theoretical_m3'] * CV_lower_methane / 1000

    # ----------------------------------------------------------------------
    # Primary energy (available potential) total goats in GJ
    calc_columns['Goats_primary_energy_available'] = (calc_columns['Goats_available_oDM_manure']) * CV_lower_oDM

    # Pot. Biomethane Yield (available potential) total goats in m3
    calc_columns['Goats_biomethane_yield_available_m3'] = (calc_columns['Goats_available_oDM_manure'] * methane_yield["Goat_manure"]["MY"])

    # Pot. Biomethane Yield (available potential) total goats in GJ
    calc_columns['Goats_biomethane_yield_available_GJ'] = calc_columns['Goats_biomethane_yield_available_m3'] * CV_lower_methane / 1000



    ##PIGS ------------------------------------------------------------------------------------------------------------------------------------
    # Pigs_1
    calc_columns['Slurry_DM_pigs_1'] = (gdf['Pigs_1'] * manure_production_pigs["pigs_1"]["s"] * DM_oDM["pigs"]["DM"] / 1000)

    calc_columns['Slurry_oDM_pigs_1'] = (gdf['Pigs_1'] * manure_production_pigs["pigs_1"]["s"] * DM_oDM["pigs"]["oDM"] / 1000)

    # Pigs_2
    calc_columns['Slurry_DM_pigs_2'] = (gdf['Pigs_2'] * manure_production_pigs["pigs_2"]["s"] * DM_oDM["pigs"]["DM"] / 1000)

    calc_columns['Slurry_oDM_pigs_2'] = (gdf['Pigs_2'] * manure_production_pigs["pigs_2"]["s"] * DM_oDM["pigs"]["oDM"] / 1000)

    # Pigs_3
    calc_columns['Slurry_DM_pigs_3'] = (gdf['Pigs_3'] * manure_production_pigs["pigs_3"]["s"] * DM_oDM["pigs_3"]["DM"] / 1000)

    calc_columns['Slurry_oDM_pigs_3'] = (gdf['Pigs_3'] * manure_production_pigs["pigs_3"]["s"] * DM_oDM["pigs_3"]["oDM"] / 1000)



    calc_columns['Pigs_total_oDM_slurry'] = (calc_columns['Slurry_oDM_pigs_1'] + calc_columns['Slurry_oDM_pigs_2'] + calc_columns['Slurry_oDM_pigs_3'])

    calc_columns['Pigs_available_oDM_slurry'] = (calc_columns['Pigs_total_oDM_slurry'])

    # Primary energy (theoretical potential) total pigs in GJ
    calc_columns['Pigs_primary_energy_theoretical'] = (calc_columns['Pigs_total_oDM_slurry']) * CV_lower_oDM

    # Pot. Biomethane Yield (theoretical potential) total pigs in m3
    calc_columns['Pigs_biomethane_yield_theoretical_m3'] = (calc_columns['Pigs_total_oDM_slurry'] * methane_yield["Pigs_slurry"]["MY"])

    # Pot. Biomethane Yield (theoretical potential) total pigs in GJ
    calc_columns['Pigs_biomethane_yield_theoretical_GJ'] = calc_columns['Pigs_biomethane_yield_theoretical_m3'] * CV_lower_methane / 1000

    # ----------------------------------------------------------------------
    # Primary energy (available potential) total pigs in GJ
    calc_columns['Pigs_primary_energy_available'] = calc_columns['Pigs_primary_energy_theoretical']

    # Pot. Biomethane Yield (available potential) total pigs in m3
    calc_columns['Pigs_biomethane_yield_available_m3'] = calc_columns['Pigs_biomethane_yield_theoretical_m3']

    # Pot. Biomethane Yield (available potential) total pigs in GJ
    calc_columns['Pigs_biomethane_yield_available_GJ'] = calc_columns['Pigs_biomethane_yield_theoretical_GJ']

    ##POULTRY ------------------------------------------------------------------------------------------------------------------------------------

    # Poultry_1
    calc_columns['Slurry_DM_poultry_1'] = (gdf['Poultry_1'] *stable_system_poultry["poultry_1"]["manure_belt"]* manure_production_poultry["poultry_1"]["s"] * (DM_oDM["poultry_1_manurebelt"]["DM"]/100) / 1000)

    calc_columns['Slurry_oDM_poultry_1'] = (gdf['Poultry_1'] *stable_system_poultry["poultry_1"]["manure_belt"]* manure_production_poultry["poultry_1"]["s"] * (DM_oDM["poultry_1_manurebelt"]["oDM"]/100) / 1000)

    calc_columns['Manure_DM_poultry_1'] = (gdf['Poultry_1'] * stable_system_poultry["poultry_1"]["floor_system"] * manure_production_poultry["poultry_1"]["m"] * (DM_oDM["poultry_1_floorsystem"]["DM"] / 100) / 1000)

    calc_columns['Manure_oDM_poultry_1'] = (gdf['Poultry_1'] * stable_system_poultry["poultry_1"]["floor_system"] * manure_production_poultry["poultry_1"]["m"] * (DM_oDM["poultry_1_floorsystem"]["oDM"] / 100) / 1000)

    # Poultry_2
    calc_columns['Manure_DM_poultry_2'] = (gdf['Poultry_2'] * manure_production_poultry["poultry_2"]["m"] * (DM_oDM["poultry_2"]["DM"]/100) / 1000)

    calc_columns['Manure_oDM_poultry_2'] = (gdf['Poultry_2'] * manure_production_poultry["poultry_2"]["m"] * (DM_oDM["poultry_2"]["oDM"]/100) / 1000)

    # Poultry_3
    calc_columns['Manure_DM_poultry_3'] = (gdf['Poultry_3'] * manure_production_poultry["poultry_3"]["m"] * (DM_oDM["poultry_3"]["DM"] / 100) / 1000)

    calc_columns['Manure_oDM_poultry_3'] = (gdf['Poultry_3'] * manure_production_poultry["poultry_3"]["m"] * (DM_oDM["poultry_3"]["oDM"] / 100) / 1000)


    calc_columns['Poultry_total_oDM_slurry'] = (calc_columns['Slurry_oDM_poultry_1'] )

    calc_columns['Poultry_available_oDM_slurry'] = (calc_columns['Poultry_total_oDM_slurry'])

    calc_columns['Poultry_total_oDM_manure'] = (calc_columns['Manure_oDM_poultry_1']+calc_columns['Manure_oDM_poultry_2']+calc_columns['Manure_oDM_poultry_3'])

    calc_columns['Poultry_available_oDM_manure'] = (calc_columns['Poultry_total_oDM_manure'])


    # Primary energy (theoretical potential) total poultry in GJ
    calc_columns['Poultry_primary_energy_theoretical'] = ( calc_columns['Poultry_total_oDM_slurry']+calc_columns['Poultry_total_oDM_manure']) * CV_lower_oDM

    # Pot. Biomethane Yield (theoretical potential) total poultry in m3
    calc_columns['Poultry_biomethane_yield_theoretical_m3'] = ((calc_columns['Poultry_total_oDM_slurry']* methane_yield["poultry_manurebelt"]["MY"])
                                                    + (calc_columns['Poultry_total_oDM_manure']*methane_yield["poultry_floorsystem"]["MY"] ))

    # Pot. Biomethane Yield (theoretical potential) total poultry in GJ
    calc_columns['Poultry_biomethane_yield_theoretical_GJ'] = calc_columns['Poultry_biomethane_yield_theoretical_m3'] * CV_lower_methane / 1000

    # ----------------------------------------------------------------------
    # Primary energy (available potential) total poultry in GJ
    calc_columns['Poultry_primary_energy_available'] = calc_columns['Poultry_primary_energy_theoretical']

    # Pot. Biomethane Yield (available potential) total poultry in m3
    calc_columns['Poultry_biomethane_yield_available_m3'] = calc_columns['Poultry_biomethane_yield_theoretical_m3']

    # Pot. Biomethane Yield (available potential) total poultry in GJ
    calc_columns['Poultry_biomethane_yield_available_GJ'] = calc_columns['Poultry_biomethane_yield_theoretical_GJ']








    ##TOTAL ALL LIVESTOCK ----------------------------------------------------------------------------------------------------------------------------------
    # Primary energy (theoretical potential) total in GJ
    calc_columns['Total_primary_energy_theoretical'] = (calc_columns['Cattle_primary_energy_theoretical']+calc_columns['Horses_primary_energy_theoretical'] + calc_columns['Sheep_primary_energy_theoretical']
                                                    +calc_columns['Goats_primary_energy_theoretical']+calc_columns['Pigs_primary_energy_theoretical']+calc_columns['Poultry_primary_energy_theoretical'])

    # Pot. Biomethane Yield (theoretical potential) total in m3
    calc_columns['Total_biomethane_yield_theoretical_m3'] = (calc_columns['Cattle_biomethane_yield_theoretical_m3']+calc_columns['Horses_biomethane_yield_theoretical_m3']+calc_columns['Sheep_biomethane_yield_theoretical_m3']
                                                     +calc_columns['Goats_biomethane_yield_theoretical_m3']+calc_columns['Pigs_biomethane_yield_theoretical_m3']+calc_columns['Poultry_biomethane_yield_theoretical_m3'])

    # Pot. Biomethane Yield (theoretical potential) total in GJ
    calc_columns['Total_biomethane_yield_theoretical_GJ'] = (calc_columns['Cattle_biomethane_yield_theoretical_GJ']+calc_columns['Horses_biomethane_yield_theoretical_GJ']+calc_columns['Sheep_biomethane_yield_theoretical_GJ']
                                                     +calc_columns['Goats_biomethane_yield_theoretical_GJ']+calc_columns['Pigs_biomethane_yield_theoretical_GJ']+calc_columns['Poultry_biomethane_yield_theoretical_GJ'])

    # ----------------------------------------------------------------------
    # Primary energy (available potential) total in GJ
    calc_columns['Total_primary_energy_available'] = (calc_columns['Cattle_primary_energy_available']+calc_columns['Horses_primary_energy_available']+calc_columns['Sheep_primary_energy_available']
                                                  +calc_columns['Goats_primary_energy_available']+calc_columns['Pigs_primary_energy_available']+calc_columns['Poultry_primary_energy_available'])

    # Pot. Biomethane Yield (available potential) total in m3
    calc_columns['Total_biomethane_yield_available_m3'] = (calc_columns['Cattle_biomethane_yield_available_m3']+calc_columns['Horses_biomethane_yield_available_m3']+calc_columns['Sheep_biomethane_yield_available_m3']
                                                   +calc_columns['Goats_biomethane_yield_available_m3']+calc_columns['Pigs_biomethane_yield_available_m3']+calc_columns['Poultry_biomethane_yield_available_m3'])

    # Pot. Biomethane Yield (available potential) total in GJ
    calc_columns['Total_biomethane_yield_available_GJ'] = ( calc_columns['Cattle_biomethane_yield_available_GJ']+ calc_columns['Horses_biomethane_yield_available_GJ']+ calc_columns['Sheep_biomethane_yield_available_GJ']
                                                    + calc_columns['Goats_biomethane_yield_available_GJ']+ calc_columns['Pigs_biomethane_yield_available_GJ']+ calc_columns['Poultry_biomethane_yield_available_GJ'])

    # Für Energie-Ertrag von den einzelnen unter Kategorien:
    # === oDM PRO KATEGORIE (benötigt für Energie/CH4) ============================
    # CATTLE 1–4
    for i in [1, 2, 3, 4]:
        ci = f"cattle_{i}"
        # Slurry ...
        calc_columns[f"Slurry_only_oDM_cattle_{i}"] = (
                gdf[f"Cattle_{i}"] * manure_production_cattle[ci]["s"]
                * stable_cattle_total[ci]["only_slurry"] * DM_oDM["slurry_cattle"]["oDM"] / 1000
        )
        calc_columns[f"Slurry_mixed_oDM_cattle_{i}"] = (
                gdf[f"Cattle_{i}"] * manure_production_cattle[ci]["sm1"]
                * stable_cattle_total[ci]["manure_slurry"] * DM_oDM["slurry_lowstraw_cattle"]["oDM"] / 1000
        )

        # >>> HIER der wichtige Teil: für i==4 den calves-Key benutzen
        manure_key = "manure_cattle_4" if i == 4 else "manure_cattle"

        calc_columns[f"Manure_mixed_oDM_cattle_{i}"] = (
                gdf[f"Cattle_{i}"] * manure_production_cattle[ci]["sm2"]
                * stable_cattle_total[ci]["manure_slurry"] * DM_oDM[manure_key]["oDM"] / 1000
        )
        calc_columns[f"Manure_only_oDM_cattle_{i}"] = (
                gdf[f"Cattle_{i}"] * manure_production_cattle[ci]["m"]
                * stable_cattle_total[ci]["only_manure"] * DM_oDM[manure_key]["oDM"] / 1000
        )

    # CATTLE 5 (Sonderfälle: andere oDM-Dichten)
    calc_columns["Slurry_only_oDM_cattle_5"] = (
            gdf["Cattle_5"] * manure_production_cattle["cattle_5"]["s"]
            * stable_cattle_total["cattle_5"]["only_slurry"] * DM_oDM["liquid_cattle_5"]["oDM"] / 1000
    )
    calc_columns["Slurry_mixed_oDM_cattle_5"] = (
            gdf["Cattle_5"] * manure_production_cattle["cattle_5"]["s"] * 0.4
            * stable_cattle_total["cattle_5"]["manure_slurry"] * DM_oDM["slurry_lowstraw_cattle"]["oDM"] / 1000
    )
    calc_columns["Manure_mixed_oDM_cattle_5"] = (
            gdf["Cattle_5"] * manure_production_cattle["cattle_5"]["m"] * 0.6
            * stable_cattle_total["cattle_5"]["manure_slurry"] * DM_oDM["manure_cattle_5"]["oDM"] / 1000
    )
    calc_columns["Manure_only_oDM_cattle_5"] = (
            gdf["Cattle_5"] * manure_production_cattle["cattle_5"]["m"]
            * stable_cattle_total["cattle_5"]["only_manure"] * DM_oDM["manure_cattle_5"]["oDM"] / 1000
    )

    # HORSES (nur Manure, je Altersklasse)
    calc_columns["Manure_oDM_horses_1"] = (
            gdf["Horses_1"] * manure_production_horse["horse_1"]["m"] * DM_oDM["manure_horse"]["oDM"] / 1000
    )
    calc_columns["Manure_oDM_horses_2"] = (
            gdf["Horses_2"] * manure_production_horse["horse_2"]["m"] * DM_oDM["manure_horse"]["oDM"] / 1000
    )

    # SHEEP
    calc_columns["Manure_oDM_sheep_1"] = (
            gdf["Sheep_1"] * manure_production_sheep["sheep_1"]["m"] * DM_oDM["manure_sheep"]["oDM"] / 1000
    )
    calc_columns["Manure_oDM_sheep_2"] = (
            gdf["Sheep_2"] * manure_production_sheep["sheep_2"]["m"] * DM_oDM["manure_sheep"]["oDM"] / 1000
    )

    # GOATS
    calc_columns["Manure_oDM_goats"] = (
            gdf["Goats"] * manure_production_goats["goats"]["m"] * DM_oDM["manure_goat"]["oDM"] / 1000
    )

    # PIGS (nur Slurry, drei Klassen)
    calc_columns["Slurry_oDM_pigs_1"] = (
            gdf["Pigs_1"] * manure_production_pigs["pigs_1"]["s"] * DM_oDM["pigs"]["oDM"] / 1000
    )
    calc_columns["Slurry_oDM_pigs_2"] = (
            gdf["Pigs_2"] * manure_production_pigs["pigs_2"]["s"] * DM_oDM["pigs"]["oDM"] / 1000
    )
    calc_columns["Slurry_oDM_pigs_3"] = (
            gdf["Pigs_3"] * manure_production_pigs["pigs_3"]["s"] * DM_oDM["pigs_3"]["oDM"] / 1000
    )

    # POULTRY  (belt = slurry; floor = manure)
    calc_columns["Slurry_oDM_poultry_1"] = (
            gdf["Poultry_1"] * stable_system_poultry["poultry_1"]["manure_belt"]
            * manure_production_poultry["poultry_1"]["s"] * (DM_oDM["poultry_1_manurebelt"]["oDM"] / 100) / 1000
    )
    calc_columns["Manure_oDM_poultry_1"] = (
            gdf["Poultry_1"] * stable_system_poultry["poultry_1"]["floor_system"]
            * manure_production_poultry["poultry_1"]["m"] * (DM_oDM["poultry_1_floorsystem"]["oDM"] / 100) / 1000
    )
    calc_columns["Manure_oDM_poultry_2"] = (
            gdf["Poultry_2"] * manure_production_poultry["poultry_2"]["m"] * (DM_oDM["poultry_2"]["oDM"] / 100) / 1000
    )
    calc_columns["Manure_oDM_poultry_3"] = (
            gdf["Poultry_3"] * manure_production_poultry["poultry_3"]["m"] * (DM_oDM["poultry_3"]["oDM"] / 100) / 1000
    )

    # === oDM AVAILABLE pro Kategorie ============================================
    def _avail(col, rf):
        return calc_columns[col] * rf

    # Cattle avail (Slurry_only, Slurry_mixed, Manure_mixed, Manure_only je Kategorie)
    for i, rf_key in [(1, "Cattle_1"), (2, "Cattle_2"), (3, "Cattle_3"), (4, "Cattle_4"), (5, "Cattle_5")]:
        for part in ["Slurry_only", "Slurry_mixed", "Manure_mixed", "Manure_only"]:
            key = f"{part}_oDM_cattle_{i}"
            if key in calc_columns:
                calc_columns[key + "_available"] = _avail(key, reduction_factors[rf_key]["RF"])

    # Horses avail
    for i, rf_key in [(1, "Horses_1"), (2, "Horses_2")]:
        key = f"Manure_oDM_horses_{i}"
        calc_columns[key + "_available"] = _avail(key, reduction_factors[rf_key]["RF"])

    # Sheep avail
    for i, rf_key in [(1, "Sheep_1"), (2, "Sheep_2")]:
        key = f"Manure_oDM_sheep_{i}"
        calc_columns[key + "_available"] = _avail(key, reduction_factors[rf_key]["RF"])

    # Goats avail
    calc_columns["Manure_oDM_goats_available"] = _avail("Manure_oDM_goats", reduction_factors["Goats"]["RF"])

    # Pigs avail (keine Reduktion → 1:1)
    for i in [1, 2, 3]:
        key = f"Slurry_oDM_pigs_{i}"
        calc_columns[key + "_available"] = calc_columns[key]

    # Poultry avail (keine Reduktion → 1:1)
    for key in ["Slurry_oDM_poultry_1", "Manure_oDM_poultry_1", "Manure_oDM_poultry_2", "Manure_oDM_poultry_3"]:
        calc_columns[key + "_available"] = calc_columns[key]

    # Mapping: FM-Key -> oDM-Spalte + Methan-Ausbeute
    FM_TO_oDM = {
        # CATTLE 1–4
        "Slurry_only_FM_cattle_1_m3": ("Slurry_only_oDM_cattle_1", "Cattle_slurry"),
        "Slurry_mixed_FM_cattle_1_m3": ("Slurry_mixed_oDM_cattle_1", "Cattle_slurry"),
        "Manure_mixed_FM_cattle_1_tonnes": ("Manure_mixed_oDM_cattle_1", "Cattle_manure"),
        "Manure_only_FM_cattle_1_tonnes": ("Manure_only_oDM_cattle_1", "Cattle_manure"),

        "Slurry_only_FM_cattle_2_m3": ("Slurry_only_oDM_cattle_2", "Cattle_slurry"),
        "Slurry_mixed_FM_cattle_2_m3": ("Slurry_mixed_oDM_cattle_2", "Cattle_slurry"),
        "Manure_mixed_FM_cattle_2_tonnes": ("Manure_mixed_oDM_cattle_2", "Cattle_manure"),
        "Manure_only_FM_cattle_2_tonnes": ("Manure_only_oDM_cattle_2", "Cattle_manure"),

        "Slurry_only_FM_cattle_3_m3": ("Slurry_only_oDM_cattle_3", "Cattle_slurry"),
        "Slurry_mixed_FM_cattle_3_m3": ("Slurry_mixed_oDM_cattle_3", "Cattle_slurry"),
        "Manure_mixed_FM_cattle_3_tonnes": ("Manure_mixed_oDM_cattle_3", "Cattle_manure"),
        "Manure_only_FM_cattle_3_tonnes": ("Manure_only_oDM_cattle_3", "Cattle_manure"),

        "Slurry_only_FM_cattle_4_m3": ("Slurry_only_oDM_cattle_4", "Cattle_slurry"),
        "Slurry_mixed_FM_cattle_4_m3": ("Slurry_mixed_oDM_cattle_4", "Cattle_slurry"),
        "Manure_mixed_FM_cattle_4_tonnes": ("Manure_mixed_oDM_cattle_4", "Cattle_manure"),
        "Manure_only_FM_cattle_4_tonnes": ("Manure_only_oDM_cattle_4", "Cattle_manure"),

        # CATTLE 5 (spezielle MY-Keys)
        "Slurry_only_FM_cattle_5_m3": ("Slurry_only_oDM_cattle_5", "Cattle_5_slurry"),
        "Slurry_mixed_FM_cattle_5_m3": ("Slurry_mixed_oDM_cattle_5", "Cattle_5_slurry"),
        "Manure_mixed_FM_cattle_5_tonnes": ("Manure_mixed_oDM_cattle_5", "Cattle_5_manure"),
        "Manure_only_FM_cattle_5_tonnes": ("Manure_only_oDM_cattle_5", "Cattle_5_manure"),

        # HORSES
        "Manure_horses_FM_1_tonnes": ("Manure_oDM_horses_1", "Horse_manure"),
        "Manure_horses_FM_2_tonnes": ("Manure_oDM_horses_2", "Horse_manure"),

        # SHEEP
        "Manure_sheep_FM_1_tonnes": ("Manure_oDM_sheep_1", "Sheep_manure"),
        "Manure_sheep_FM_2_tonnes": ("Manure_oDM_sheep_2", "Sheep_manure"),

        # GOATS
        "Manure_goats_FM_tonnes": ("Manure_oDM_goats", "Goat_manure"),

        # PIGS
        "Slurry_pigs_FM_1_m3": ("Slurry_oDM_pigs_1", "Pigs_slurry"),
        "Slurry_pigs_FM_2_m3": ("Slurry_oDM_pigs_2", "Pigs_slurry"),
        "Slurry_pigs_FM_3_m3": ("Slurry_oDM_pigs_3", "Pigs_slurry"),

        # POULTRY
        "Slurry_poultry_FM_1_m3": ("Slurry_oDM_poultry_1", "poultry_manurebelt"),
        "Manure_poultry_FM_1_tonnes": ("Manure_oDM_poultry_1", "poultry_floorsystem"),
        "Manure_poultry_FM_2_tonnes": ("Manure_oDM_poultry_2", "poultry_floorsystem"),
        "Manure_poultry_FM_3_tonnes": ("Manure_oDM_poultry_3", "poultry_floorsystem"),
    }

    # ----------- Methane yield per category (available, m³) --------------------
    # Methan verfügbar (m³) – hier der Unterschied!
    methane_available_totals_m3 = {
        fm_key: calc_columns[odm_col + "_available"].sum() * methane_yield[my_key]["MY"]
        for fm_key, (odm_col, my_key) in FM_TO_oDM.items()
        if (odm_col + "_available") in calc_columns
    }

    # ========= NEU: Pro-Hof Frischmasse je Tierkategorie (theoretisch & verfügbar) =========
    # Param: Dichte für Gülle -> t/m³ (kannst du beim Funktionsaufruf setzen)
    slurry_density_t_per_m3 = 1.0  # oder als Funktionsparameter übergeben

    # 1) CATTLE – Gülle (m³) & Mist (t) je Hof (theoretisch)
    slurry_cattle_m3_series = (
            gdf["Cattle_1"] * (manure_production_cattle["cattle_1"]["s"] * stable_cattle_total["cattle_1"]["only_slurry"] +
                               manure_production_cattle["cattle_1"]["sm1"] * stable_cattle_total["cattle_1"]["manure_slurry"]) +
            gdf["Cattle_2"] * (manure_production_cattle["cattle_2"]["s"] * stable_cattle_total["cattle_2"]["only_slurry"] +
                               manure_production_cattle["cattle_2"]["sm1"] * stable_cattle_total["cattle_2"]["manure_slurry"]) +
            gdf["Cattle_3"] * (manure_production_cattle["cattle_3"]["s"] * stable_cattle_total["cattle_3"]["only_slurry"] +
                               manure_production_cattle["cattle_3"]["sm1"] * stable_cattle_total["cattle_3"]["manure_slurry"]) +
            gdf["Cattle_4"] * (manure_production_cattle["cattle_4"]["s"] * stable_cattle_total["cattle_4"]["only_slurry"] +
                               manure_production_cattle["cattle_4"]["sm1"] * stable_cattle_total["cattle_4"]["manure_slurry"]) +
            # cattle_5: 0.4 * s im "manure_slurry"-Zweig (wie oben in deinem Code)
            gdf["Cattle_5"] * (manure_production_cattle["cattle_5"]["s"] * stable_cattle_total["cattle_5"]["only_slurry"] +
                               (manure_production_cattle["cattle_5"]["s"] * 0.4) * stable_cattle_total["cattle_5"]["manure_slurry"])
    )

    manure_cattle_t_series = (
            gdf["Cattle_1"] * (manure_production_cattle["cattle_1"]["sm2"] * stable_cattle_total["cattle_1"]["manure_slurry"] +
                               manure_production_cattle["cattle_1"]["m"] * stable_cattle_total["cattle_1"]["only_manure"]) +
            gdf["Cattle_2"] * (manure_production_cattle["cattle_2"]["sm2"] * stable_cattle_total["cattle_2"]["manure_slurry"] +
                               manure_production_cattle["cattle_2"]["m"] * stable_cattle_total["cattle_2"]["only_manure"]) +
            gdf["Cattle_3"] * (manure_production_cattle["cattle_3"]["sm2"] * stable_cattle_total["cattle_3"]["manure_slurry"] +
                               manure_production_cattle["cattle_3"]["m"] * stable_cattle_total["cattle_3"]["only_manure"]) +
            gdf["Cattle_4"] * (manure_production_cattle["cattle_4"]["sm2"] * stable_cattle_total["cattle_4"]["manure_slurry"] +
                               manure_production_cattle["cattle_4"]["m"] * stable_cattle_total["cattle_4"]["only_manure"]) +
            # cattle_5: 0.6 * m im "manure_slurry"-Zweig
            gdf["Cattle_5"] * ((manure_production_cattle["cattle_5"]["m"] * 0.6) * stable_cattle_total["cattle_5"]["manure_slurry"] +
                               manure_production_cattle["cattle_5"]["m"] * stable_cattle_total["cattle_5"]["only_manure"])
    )

    # Verfügbare FM (mit RF je Klasse) – gleiche Zerlegung wie oben, aber pro Klasse mit RF multiplizieren
    slurry_cattle_m3_av_series = (
            gdf["Cattle_1"] * (manure_production_cattle["cattle_1"]["s"] * stable_cattle_total["cattle_1"]["only_slurry"] +
                               manure_production_cattle["cattle_1"]["sm1"] * stable_cattle_total["cattle_1"]["manure_slurry"]) *
            reduction_factors["Cattle_1"]["RF"] +
            gdf["Cattle_2"] * (manure_production_cattle["cattle_2"]["s"] * stable_cattle_total["cattle_2"]["only_slurry"] +
                               manure_production_cattle["cattle_2"]["sm1"] * stable_cattle_total["cattle_2"]["manure_slurry"]) *
            reduction_factors["Cattle_2"]["RF"] +
            gdf["Cattle_3"] * (manure_production_cattle["cattle_3"]["s"] * stable_cattle_total["cattle_3"]["only_slurry"] +
                               manure_production_cattle["cattle_3"]["sm1"] * stable_cattle_total["cattle_3"]["manure_slurry"]) *
            reduction_factors["Cattle_3"]["RF"] +
            gdf["Cattle_4"] * (manure_production_cattle["cattle_4"]["s"] * stable_cattle_total["cattle_4"]["only_slurry"] +
                               manure_production_cattle["cattle_4"]["sm1"] * stable_cattle_total["cattle_4"]["manure_slurry"]) *
            reduction_factors["Cattle_4"]["RF"] +
            gdf["Cattle_5"] * (manure_production_cattle["cattle_5"]["s"] * stable_cattle_total["cattle_5"]["only_slurry"] +
                               (manure_production_cattle["cattle_5"]["s"] * 0.4) * stable_cattle_total["cattle_5"]["manure_slurry"]) *
            reduction_factors["Cattle_5"]["RF"]
    )

    manure_cattle_t_av_series = (
            gdf["Cattle_1"] * (manure_production_cattle["cattle_1"]["sm2"] * stable_cattle_total["cattle_1"]["manure_slurry"] +
                               manure_production_cattle["cattle_1"]["m"] * stable_cattle_total["cattle_1"]["only_manure"]) *
            reduction_factors["Cattle_1"]["RF"] +
            gdf["Cattle_2"] * (manure_production_cattle["cattle_2"]["sm2"] * stable_cattle_total["cattle_2"]["manure_slurry"] +
                               manure_production_cattle["cattle_2"]["m"] * stable_cattle_total["cattle_2"]["only_manure"]) *
            reduction_factors["Cattle_2"]["RF"] +
            gdf["Cattle_3"] * (manure_production_cattle["cattle_3"]["sm2"] * stable_cattle_total["cattle_3"]["manure_slurry"] +
                               manure_production_cattle["cattle_3"]["m"] * stable_cattle_total["cattle_3"]["only_manure"]) *
            reduction_factors["Cattle_3"]["RF"] +
            gdf["Cattle_4"] * (manure_production_cattle["cattle_4"]["sm2"] * stable_cattle_total["cattle_4"]["manure_slurry"] +
                               manure_production_cattle["cattle_4"]["m"] * stable_cattle_total["cattle_4"]["only_manure"]) *
            reduction_factors["Cattle_4"]["RF"] +
            gdf["Cattle_5"] * ((manure_production_cattle["cattle_5"]["m"] * 0.6) * stable_cattle_total["cattle_5"]["manure_slurry"] +
                               manure_production_cattle["cattle_5"]["m"] * stable_cattle_total["cattle_5"]["only_manure"]) *
            reduction_factors["Cattle_5"]["RF"]
    )

    # 2) HORSES – nur Mist
    manure_horses_t_series = gdf["Horses_1"] * manure_production_horse["horse_1"]["m"] + gdf["Horses_2"] * manure_production_horse["horse_2"]["m"]
    manure_horses_t_av_series = gdf["Horses_1"] * manure_production_horse["horse_1"]["m"] * reduction_factors["Horses_1"]["RF"] + \
                                gdf["Horses_2"] * manure_production_horse["horse_2"]["m"] * reduction_factors["Horses_2"]["RF"]

    # 3) SHEEP – nur Mist
    manure_sheep_t_series = gdf["Sheep_1"] * manure_production_sheep["sheep_1"]["m"] + gdf["Sheep_2"] * manure_production_sheep["sheep_2"]["m"]
    manure_sheep_t_av_series = gdf["Sheep_1"] * manure_production_sheep["sheep_1"]["m"] * reduction_factors["Sheep_1"]["RF"] + \
                               gdf["Sheep_2"] * manure_production_sheep["sheep_2"]["m"] * reduction_factors["Sheep_2"]["RF"]

    # 4) GOATS – nur Mist
    manure_goats_t_series = gdf["Goats"] * manure_production_goats["goats"]["m"]
    manure_goats_t_av_series = manure_goats_t_series * reduction_factors["Goats"]["RF"]

    # 5) PIGS – nur Gülle; RF = 1
    slurry_pigs_m3_series = gdf["Pigs_1"] * manure_production_pigs["pigs_1"]["s"] + \
                            gdf["Pigs_2"] * manure_production_pigs["pigs_2"]["s"] + \
                            gdf["Pigs_3"] * manure_production_pigs["pigs_3"]["s"]
    slurry_pigs_m3_av_series = slurry_pigs_m3_series

    # 6) POULTRY – Gülle (belt) + Mist (floor); RF = 1
    slurry_poultry_m3_series = gdf["Poultry_1"] * stable_system_poultry["poultry_1"]["manure_belt"] * manure_production_poultry["poultry_1"]["s"]
    slurry_poultry_m3_av_series = slurry_poultry_m3_series
    manure_poultry_t_series = gdf["Poultry_1"] * stable_system_poultry["poultry_1"]["floor_system"] * manure_production_poultry["poultry_1"]["m"] + \
                              gdf["Poultry_2"] * manure_production_poultry["poultry_2"]["m"] + \
                              gdf["Poultry_3"] * manure_production_poultry["poultry_3"]["m"]
    manure_poultry_t_av_series = manure_poultry_t_series

    # --- Spalten in gdf schreiben (klar benannt) ---
    def _total_t(slurry_m3, manure_t):
        return slurry_m3 * slurry_density_t_per_m3 + manure_t

    # Cattle
    gdf["FM_slurry_m3_cattle"] = slurry_cattle_m3_series
    gdf["FM_manure_t_cattle"] = manure_cattle_t_series
    gdf["FM_total_t_cattle"] = _total_t(slurry_cattle_m3_series, manure_cattle_t_series)
    gdf["FM_slurry_m3_cattle_av"] = slurry_cattle_m3_av_series
    gdf["FM_manure_t_cattle_av"] = manure_cattle_t_av_series
    gdf["FM_total_t_cattle_av"] = _total_t(slurry_cattle_m3_av_series, manure_cattle_t_av_series)

    # Horses
    gdf["FM_slurry_m3_horses"] = 0.0
    gdf["FM_manure_t_horses"] = manure_horses_t_series
    gdf["FM_total_t_horses"] = _total_t(0.0, manure_horses_t_series)
    gdf["FM_slurry_m3_horses_av"] = 0.0
    gdf["FM_manure_t_horses_av"] = manure_horses_t_av_series
    gdf["FM_total_t_horses_av"] = _total_t(0.0, manure_horses_t_av_series)

    # Sheep
    gdf["FM_slurry_m3_sheep"] = 0.0
    gdf["FM_manure_t_sheep"] = manure_sheep_t_series
    gdf["FM_total_t_sheep"] = _total_t(0.0, manure_sheep_t_series)
    gdf["FM_slurry_m3_sheep_av"] = 0.0
    gdf["FM_manure_t_sheep_av"] = manure_sheep_t_av_series
    gdf["FM_total_t_sheep_av"] = _total_t(0.0, manure_sheep_t_av_series)

    # Goats
    gdf["FM_slurry_m3_goats"] = 0.0
    gdf["FM_manure_t_goats"] = manure_goats_t_series
    gdf["FM_total_t_goats"] = _total_t(0.0, manure_goats_t_series)
    gdf["FM_slurry_m3_goats_av"] = 0.0
    gdf["FM_manure_t_goats_av"] = manure_goats_t_av_series
    gdf["FM_total_t_goats_av"] = _total_t(0.0, manure_goats_t_av_series)

    # Pigs
    gdf["FM_slurry_m3_pigs"] = slurry_pigs_m3_series
    gdf["FM_manure_t_pigs"] = 0.0
    gdf["FM_total_t_pigs"] = _total_t(slurry_pigs_m3_series, 0.0)
    gdf["FM_slurry_m3_pigs_av"] = slurry_pigs_m3_av_series
    gdf["FM_manure_t_pigs_av"] = 0.0
    gdf["FM_total_t_pigs_av"] = _total_t(slurry_pigs_m3_av_series, 0.0)

    # Poultry
    gdf["FM_slurry_m3_poultry"] = slurry_poultry_m3_series
    gdf["FM_manure_t_poultry"] = manure_poultry_t_series
    gdf["FM_total_t_poultry"] = _total_t(slurry_poultry_m3_series, manure_poultry_t_series)
    gdf["FM_slurry_m3_poultry_av"] = slurry_poultry_m3_av_series
    gdf["FM_manure_t_poultry_av"] = manure_poultry_t_av_series
    gdf["FM_total_t_poultry_av"] = _total_t(slurry_poultry_m3_av_series, manure_poultry_t_av_series)

    # (Optional) Dictionary mit Spaltenlisten, falls du sie downstream brauchst
    fm_cols = {
        "cattle": ["FM_slurry_m3_cattle", "FM_manure_t_cattle", "FM_total_t_cattle",
                   "FM_slurry_m3_cattle_av", "FM_manure_t_cattle_av", "FM_total_t_cattle_av"],
        "horses": ["FM_slurry_m3_horses", "FM_manure_t_horses", "FM_total_t_horses",
                   "FM_slurry_m3_horses_av", "FM_manure_t_horses_av", "FM_total_t_horses_av"],
        "sheep": ["FM_slurry_m3_sheep", "FM_manure_t_sheep", "FM_total_t_sheep",
                  "FM_slurry_m3_sheep_av", "FM_manure_t_sheep_av", "FM_total_t_sheep_av"],
        "goats": ["FM_slurry_m3_goats", "FM_manure_t_goats", "FM_total_t_goats",
                  "FM_slurry_m3_goats_av", "FM_manure_t_goats_av", "FM_total_t_goats_av"],
        "pigs": ["FM_slurry_m3_pigs", "FM_manure_t_pigs", "FM_total_t_pigs",
                 "FM_slurry_m3_pigs_av", "FM_manure_t_pigs_av", "FM_total_t_pigs_av"],
        "poultry": ["FM_slurry_m3_poultry", "FM_manure_t_poultry", "FM_total_t_poultry",
                    "FM_slurry_m3_poultry_av", "FM_manure_t_poultry_av", "FM_total_t_poultry_av"],
    }
    # ========= ENDE NEU =========










    #-----------
    #GeoDataFrame to return in TJ
    #ergänzen mit was ich brauche für impact Berechnung
    gdf['Total_primary_energy_available_GJ_env_imp'] = (calc_columns['Total_primary_energy_available'] )
    gdf['Total_biomethane_yield_available_GJ_env_imp'] = (calc_columns['Total_biomethane_yield_available_GJ'])
    gdf['Total_biomethane_yield_available_m3'] = (calc_columns['Total_biomethane_yield_available_m3'])

    # List of columns you want to sum

    columns_to_sum = [
        'Total_primary_energy_available_GJ_env_imp',

    ]



    # Return the updated GeoDataFrame
    return gdf, methane_available_totals_m3, fm_cols






