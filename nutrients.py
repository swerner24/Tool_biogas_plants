import geopandas as gpd
import pandas as pd

#Parameters for various livestock for nutrients excretion

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

#Nitrogen excretion per livestock
#0: [kg/(animal*year)]
nutrients= {
    "Cattle_1":     {"N": 112},
    "Cattle_2":     {"N": 85},    #Assumption: Mother cow, medium-weight
    "Cattle_3":     {"N": 40},    #Assumption: Breeding cattle, 1-2 y.
    "Cattle_4":     {"N": 25},    #Assumption: Breeding cattle, under 1 y.
    "Cattle_5":     {"N": 40},    #Assumption: Rindviehweidemast
    "Horses_1":     {"N": 42},
    "Horses_2":     {"N": 44},
    "Sheep_1":      {"N": 20},
    "Sheep_2":      {"N": 18},
    "Goats":        {"N": 17},
    "Pigs_1":       {"N": 49},    #Assumption: Breeding pig place
    "Pigs_2":       {"N": 18},
    "Pigs_3":       {"N": 13},    #Assumption: Pig fattening place
    "Poultry_1":    {"N": 80/100},    #100 laying hen places
    "Poultry_2":    {"N": 36/100},    #100 fattening chicken places
    "Poultry_3":    {"N": 48/100},   #100 fattening turkey places, old "N": 140/100
}

nutrients_P= {
    "Cattle_1":     {"P": 17},
    "Cattle_2":     {"P": 12},    #Assumption: Mother cow, medium-weight
    "Cattle_3":     {"P": 5.7},    #Assumption: Breeding cattle, 1-2 y.
    "Cattle_4":     {"P": 3.3},    #Assumption: Breeding cattle, under 1 y.
    "Cattle_5":     {"P": 5.2},    #Assumption: Rindviehweidemast
    "Horses_1":     {"P": 8},
    "Horses_2":     {"P": 10},
    "Sheep_1":      {"P": 3.7},
    "Sheep_2":      {"P": 2.6},
    "Goats":        {"P": 2.5},
    "Pigs_1":       {"P": 10},    #Assumption: Breeding pig place
    "Pigs_2":       {"P": 4.4},
    "Pigs_3":       {"P": 2.3},    #Assumption: Pig fattening place
    "Poultry_1":    {"P": 20/100},    #100 laying hen places
    "Poultry_2":    {"P": 6/100},    #100 fattening chicken places
    "Poultry_3":    {"P": 11/100},   #100 fattening turkey places, old "N": 140/100
}

def calculate_nitrogen(input_shapefile):
    # Load the shapefile with animal numbers per polygon
    gdf = gpd.read_file(input_shapefile)

    # Initialize a dictionary to store calculated columns
    calc_columns = {}

    #Theoretical N
    calc_columns['Cattle_1_theor'] = (gdf['Cattle_1'] * nutrients["Cattle_1"]["N"] )
    calc_columns['Cattle_2_theor'] = (gdf['Cattle_2'] * nutrients["Cattle_2"]["N"])
    calc_columns['Cattle_3_theor'] = (gdf['Cattle_3'] * nutrients["Cattle_3"]["N"])
    calc_columns['Cattle_4_theor'] = (gdf['Cattle_4'] * nutrients["Cattle_4"]["N"])
    calc_columns['Cattle_5_theor'] = (gdf['Cattle_5'] * nutrients["Cattle_5"]["N"])

    calc_columns['Horses_1_theor'] = (gdf['Horses_1'] * nutrients["Horses_1"]["N"])
    calc_columns['Horses_2_theor'] = (gdf['Horses_2'] * nutrients["Horses_2"]["N"])

    calc_columns['Sheep_1_theor'] = (gdf['Sheep_1'] * nutrients["Sheep_1"]["N"])
    calc_columns['Sheep_2_theor'] = (gdf['Sheep_2'] * nutrients["Sheep_2"]["N"])

    calc_columns['Goats_theor'] = (gdf['Goats'] * nutrients["Goats"]["N"])

    calc_columns['Pigs_1_theor'] = (gdf['Pigs_1'] * nutrients["Pigs_1"]["N"])
    calc_columns['Pigs_2_theor'] = (gdf['Pigs_2'] * nutrients["Pigs_2"]["N"])
    calc_columns['Pigs_3_theor'] = (gdf['Pigs_3'] * nutrients["Pigs_3"]["N"])

    calc_columns['Poultry_1_theor'] = (gdf['Poultry_1'] * nutrients["Poultry_1"]["N"])
    calc_columns['Poultry_2_theor'] = (gdf['Poultry_2'] * nutrients["Poultry_2"]["N"])
    calc_columns['Poultry_3_theor'] = (gdf['Poultry_3'] * nutrients["Poultry_3"]["N"])

    calc_columns['Total_theor_N_kg']=(calc_columns['Cattle_1_theor']+calc_columns['Cattle_2_theor']+calc_columns['Cattle_3_theor']
                                 +calc_columns['Cattle_4_theor']+calc_columns['Cattle_5_theor']+calc_columns['Horses_1_theor']
                                 +calc_columns['Horses_2_theor']+calc_columns['Sheep_1_theor']+calc_columns['Sheep_2_theor']
                                 +calc_columns['Goats_theor']+calc_columns['Pigs_1_theor']+calc_columns['Pigs_2_theor']+calc_columns['Pigs_3_theor']
                                 +calc_columns['Poultry_1_theor']+calc_columns['Poultry_2_theor']+calc_columns['Poultry_3_theor'])

    # Available N
    calc_columns['Cattle_1_avail'] = (gdf['Cattle_1'] * nutrients["Cattle_1"]["N"]*reduction_factors["Cattle_1"]["RF"])
    calc_columns['Cattle_2_avail'] = (gdf['Cattle_2'] * nutrients["Cattle_2"]["N"]*reduction_factors["Cattle_2"]["RF"])
    calc_columns['Cattle_3_avail'] = (gdf['Cattle_3'] * nutrients["Cattle_3"]["N"]*reduction_factors["Cattle_3"]["RF"])
    calc_columns['Cattle_4_avail'] = (gdf['Cattle_4'] * nutrients["Cattle_4"]["N"]*reduction_factors["Cattle_4"]["RF"])
    calc_columns['Cattle_5_avail'] = (gdf['Cattle_5'] * nutrients["Cattle_5"]["N"]*reduction_factors["Cattle_5"]["RF"])

    calc_columns['Horses_1_avail'] = (gdf['Horses_1'] * nutrients["Horses_1"]["N"]*reduction_factors["Horses_1"]["RF"])
    calc_columns['Horses_2_avail'] = (gdf['Horses_2'] * nutrients["Horses_2"]["N"]*reduction_factors["Horses_2"]["RF"])

    calc_columns['Sheep_1_avail'] = (gdf['Sheep_1'] * nutrients["Sheep_1"]["N"]*reduction_factors["Sheep_1"]["RF"])
    calc_columns['Sheep_2_avail'] = (gdf['Sheep_2'] * nutrients["Sheep_2"]["N"]*reduction_factors["Sheep_2"]["RF"])

    calc_columns['Goats_avail'] = (gdf['Goats'] * nutrients["Goats"]["N"]*reduction_factors["Goats"]["RF"])

    calc_columns['Pigs_1_avail'] = (gdf['Pigs_1'] * nutrients["Pigs_1"]["N"])
    calc_columns['Pigs_2_avail'] = (gdf['Pigs_2'] * nutrients["Pigs_2"]["N"])
    calc_columns['Pigs_3_avail'] = (gdf['Pigs_3'] * nutrients["Pigs_3"]["N"])

    calc_columns['Poultry_1_avail'] = (gdf['Poultry_1'] * nutrients["Poultry_1"]["N"])
    calc_columns['Poultry_2_avail'] = (gdf['Poultry_2']  * nutrients["Poultry_2"]["N"])
    calc_columns['Poultry_3_avail'] = (gdf['Poultry_3']  * nutrients["Poultry_3"]["N"])

    calc_columns['Total_avail_N_kg'] = (calc_columns['Cattle_1_avail'] + calc_columns['Cattle_2_avail'] + calc_columns['Cattle_3_avail']
                                   + calc_columns['Cattle_4_avail'] + calc_columns['Cattle_5_avail'] + calc_columns['Horses_1_avail']
                                   + calc_columns['Horses_2_avail'] + calc_columns['Sheep_1_avail'] + calc_columns['Sheep_2_avail']
                                   + calc_columns['Goats_avail'] + calc_columns['Pigs_1_avail'] + calc_columns['Pigs_2_avail'] + calc_columns[
                                       'Pigs_3_avail']
                                   + calc_columns['Poultry_1_avail'] + calc_columns['Poultry_2_avail'] + calc_columns['Poultry_3_avail'])

    calc_columns['Total_N_on_pasture']=calc_columns['Total_theor_N_kg']-calc_columns['Total_avail_N_kg']


    gdf['Total_theor_N_kg']=calc_columns['Total_theor_N_kg']
    gdf['Total_avail_N_kg']=calc_columns['Total_avail_N_kg']
    gdf['Total_N_on_pasture']=calc_columns['Total_N_on_pasture']

    gdf['Cattle_1_avail']= calc_columns['Cattle_1_avail']
    gdf['Cattle_2_avail']= calc_columns['Cattle_2_avail']
    gdf['Cattle_3_avail']= calc_columns['Cattle_3_avail']
    gdf['Cattle_4_avail']= calc_columns['Cattle_4_avail']
    gdf['Cattle_5_avail']= calc_columns['Cattle_5_avail']

    gdf['Horses_1_avail']= calc_columns['Horses_1_avail']
    gdf['Horses_2_avail']= calc_columns['Horses_2_avail']

    gdf['Sheep_1_avail']= calc_columns['Sheep_1_avail']
    gdf['Sheep_2_avail']= calc_columns['Sheep_2_avail']
    gdf['Goats_avail']= calc_columns['Goats_avail']

    gdf['Pigs_1_avail']= calc_columns['Pigs_1_avail']
    gdf['Pigs_2_avail']= calc_columns['Pigs_2_avail']
    gdf['Pigs_3_avail']= calc_columns['Pigs_3_avail']

    gdf['Poultry_1_avail']= calc_columns['Poultry_1_avail']
    gdf['Poultry_2_avail']= calc_columns['Poultry_2_avail']
    gdf['Poultry_3_avail']= calc_columns['Poultry_3_avail']

    # Return the updated GeoDataFrame
    return gdf




def calculate_phosphorus(input_shapefile):
    # Load the shapefile with animal numbers per polygon
    gdf = gpd.read_file(input_shapefile)

    # Initialize a dictionary to store calculated columns
    calc_columns = {}

    #Theoretical P
    calc_columns['Cattle_1_theor'] = (gdf['Cattle_1'] * nutrients_P["Cattle_1"]["P"] )
    calc_columns['Cattle_2_theor'] = (gdf['Cattle_2'] * nutrients_P["Cattle_2"]["P"])
    calc_columns['Cattle_3_theor'] = (gdf['Cattle_3'] * nutrients_P["Cattle_3"]["P"])
    calc_columns['Cattle_4_theor'] = (gdf['Cattle_4'] * nutrients_P["Cattle_4"]["P"])
    calc_columns['Cattle_5_theor'] = (gdf['Cattle_5'] * nutrients_P["Cattle_5"]["P"])

    calc_columns['Horses_1_theor'] = (gdf['Horses_1'] * nutrients_P["Horses_1"]["P"])
    calc_columns['Horses_2_theor'] = (gdf['Horses_2'] * nutrients_P["Horses_2"]["P"])

    calc_columns['Sheep_1_theor'] = (gdf['Sheep_1'] * nutrients_P["Sheep_1"]["P"])
    calc_columns['Sheep_2_theor'] = (gdf['Sheep_2'] * nutrients_P["Sheep_2"]["P"])

    calc_columns['Goats_theor'] = (gdf['Goats'] * nutrients_P["Goats"]["P"])

    calc_columns['Pigs_1_theor'] = (gdf['Pigs_1'] * nutrients_P["Pigs_1"]["P"])
    calc_columns['Pigs_2_theor'] = (gdf['Pigs_2'] * nutrients_P["Pigs_2"]["P"])
    calc_columns['Pigs_3_theor'] = (gdf['Pigs_3'] * nutrients_P["Pigs_3"]["P"])

    calc_columns['Poultry_1_theor'] = (gdf['Poultry_1'] * nutrients_P["Poultry_1"]["P"])
    calc_columns['Poultry_2_theor'] = (gdf['Poultry_2'] * nutrients_P["Poultry_2"]["P"])
    calc_columns['Poultry_3_theor'] = (gdf['Poultry_3'] * nutrients_P["Poultry_3"]["P"])

    calc_columns['Total_theor_P_kg']=(calc_columns['Cattle_1_theor']+calc_columns['Cattle_2_theor']+calc_columns['Cattle_3_theor']
                                 +calc_columns['Cattle_4_theor']+calc_columns['Cattle_5_theor']+calc_columns['Horses_1_theor']
                                 +calc_columns['Horses_2_theor']+calc_columns['Sheep_1_theor']+calc_columns['Sheep_2_theor']
                                 +calc_columns['Goats_theor']+calc_columns['Pigs_1_theor']+calc_columns['Pigs_2_theor']+calc_columns['Pigs_3_theor']
                                 +calc_columns['Poultry_1_theor']+calc_columns['Poultry_2_theor']+calc_columns['Poultry_3_theor'])

    # Available P
    calc_columns['Cattle_1_avail'] = (gdf['Cattle_1'] * nutrients_P["Cattle_1"]["P"]*reduction_factors["Cattle_1"]["RF"])
    calc_columns['Cattle_2_avail'] = (gdf['Cattle_2'] * nutrients_P["Cattle_2"]["P"]*reduction_factors["Cattle_2"]["RF"])
    calc_columns['Cattle_3_avail'] = (gdf['Cattle_3'] * nutrients_P["Cattle_3"]["P"]*reduction_factors["Cattle_3"]["RF"])
    calc_columns['Cattle_4_avail'] = (gdf['Cattle_4'] * nutrients_P["Cattle_4"]["P"]*reduction_factors["Cattle_4"]["RF"])
    calc_columns['Cattle_5_avail'] = (gdf['Cattle_5'] * nutrients_P["Cattle_5"]["P"]*reduction_factors["Cattle_5"]["RF"])

    calc_columns['Horses_1_avail'] = (gdf['Horses_1'] * nutrients_P["Horses_1"]["P"]*reduction_factors["Horses_1"]["RF"])
    calc_columns['Horses_2_avail'] = (gdf['Horses_2'] * nutrients_P["Horses_2"]["P"]*reduction_factors["Horses_2"]["RF"])

    calc_columns['Sheep_1_avail'] = (gdf['Sheep_1'] * nutrients_P["Sheep_1"]["P"]*reduction_factors["Sheep_1"]["RF"])
    calc_columns['Sheep_2_avail'] = (gdf['Sheep_2'] * nutrients_P["Sheep_2"]["P"]*reduction_factors["Sheep_2"]["RF"])

    calc_columns['Goats_avail'] = (gdf['Goats'] * nutrients_P["Goats"]["P"]*reduction_factors["Goats"]["RF"])

    calc_columns['Pigs_1_avail'] = (gdf['Pigs_1'] * nutrients_P["Pigs_1"]["P"])
    calc_columns['Pigs_2_avail'] = (gdf['Pigs_2'] * nutrients_P["Pigs_2"]["P"])
    calc_columns['Pigs_3_avail'] = (gdf['Pigs_3'] * nutrients_P["Pigs_3"]["P"])

    calc_columns['Poultry_1_avail'] = (gdf['Poultry_1'] * nutrients_P["Poultry_1"]["P"])
    calc_columns['Poultry_2_avail'] = (gdf['Poultry_2']  * nutrients_P["Poultry_2"]["P"])
    calc_columns['Poultry_3_avail'] = (gdf['Poultry_3']  * nutrients_P["Poultry_3"]["P"])

    calc_columns['Total_avail_P_kg'] = (calc_columns['Cattle_1_avail'] + calc_columns['Cattle_2_avail'] + calc_columns['Cattle_3_avail']
                                   + calc_columns['Cattle_4_avail'] + calc_columns['Cattle_5_avail'] + calc_columns['Horses_1_avail']
                                   + calc_columns['Horses_2_avail'] + calc_columns['Sheep_1_avail'] + calc_columns['Sheep_2_avail']
                                   + calc_columns['Goats_avail'] + calc_columns['Pigs_1_avail'] + calc_columns['Pigs_2_avail'] + calc_columns[
                                       'Pigs_3_avail']
                                   + calc_columns['Poultry_1_avail'] + calc_columns['Poultry_2_avail'] + calc_columns['Poultry_3_avail'])

    calc_columns['Total_P_on_pasture']=calc_columns['Total_theor_P_kg']-calc_columns['Total_avail_P_kg']


    gdf['Total_theor_P_kg']=calc_columns['Total_theor_P_kg']
    gdf['Total_avail_P_kg']=calc_columns['Total_avail_P_kg']
    gdf['Total_P_on_pasture']=calc_columns['Total_P_on_pasture']

    gdf['Cattle_1_avail']= calc_columns['Cattle_1_avail']
    gdf['Cattle_2_avail']= calc_columns['Cattle_2_avail']
    gdf['Cattle_3_avail']= calc_columns['Cattle_3_avail']
    gdf['Cattle_4_avail']= calc_columns['Cattle_4_avail']
    gdf['Cattle_5_avail']= calc_columns['Cattle_5_avail']

    gdf['Horses_1_avail']= calc_columns['Horses_1_avail']
    gdf['Horses_2_avail']= calc_columns['Horses_2_avail']

    gdf['Sheep_1_avail']= calc_columns['Sheep_1_avail']
    gdf['Sheep_2_avail']= calc_columns['Sheep_2_avail']
    gdf['Goats_avail']= calc_columns['Goats_avail']

    gdf['Pigs_1_avail']= calc_columns['Pigs_1_avail']
    gdf['Pigs_2_avail']= calc_columns['Pigs_2_avail']
    gdf['Pigs_3_avail']= calc_columns['Pigs_3_avail']

    gdf['Poultry_1_avail']= calc_columns['Poultry_1_avail']
    gdf['Poultry_2_avail']= calc_columns['Poultry_2_avail']
    gdf['Poultry_3_avail']= calc_columns['Poultry_3_avail']

    # Return the updated GeoDataFrame
    return gdf
