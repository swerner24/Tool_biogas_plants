from dash import Dash, dcc, html, Input, Output, State, callback_context
from dash import ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import geopandas as gpd
import json
import os
import plotly.graph_objects as go
import sys
import pandas as pd
from shapely.geometry import Polygon, mapping
import matplotlib.pyplot as plt
from potential import calculate_potential
from potential_env_imp import calculate_potential_env_imp
from env_imp_PW1 import calculate_emissions
from env_imp_PW1 import compute_field_n2o_vectorized
from env_imp_PW1 import apply_chp_emissions_to_polygons
from env_imp_PW1 import  apply_upgrading_emissions_to_polygons
import numpy as np
from dash import callback, Input, Output, State
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate

input_shapefile = "data/Polygons_Cantonal_Climate_WGS_1984.shp"
technical_path = "data/Polygons_technical_29_12_25_export_wgs.shp"
biogas_path = "data/biogas_plants_points_export_wgs.shp"
legal_path = "data/Polygons_legal_29_12_25_Project_export_wgs.shp"

# Laden der Dateien
gdf_technical = gpd.read_file(technical_path)
gdf_plants = gpd.read_file(biogas_path)
gdf_legal = gpd.read_file(legal_path)


gdf_main, fm_totals, dm_totals, x1, x2, x3, x4, x5, x6= calculate_potential(input_shapefile)

#Cantons dissolve for basemap
gdf_cantons = gdf_main.dissolve(by="Canton")
gdf_cantons = gdf_cantons.to_crs(4326)
cantons_geojson = json.loads(gdf_cantons.to_json())

# Convert GeoDataFrame to GeoJSON for the main content
geojson_main = json.loads(gdf_main.to_json())
geojson_technical = json.loads(gdf_technical.to_json())
geojson_legal = json.loads(gdf_legal.to_json())
gdf_main_4326 = gdf_main.to_crs(4326).copy()
geojson_main_4326 = json.loads(gdf_main_4326.to_json())

gdf_technical["Reclassifi"] = pd.to_numeric(gdf_technical["Reclassifi"], errors="coerce").fillna(1).astype(int)
gdf_technical["detour_fac"] = pd.to_numeric(gdf_technical["detour_fac"], errors="coerce").fillna(1.0).astype(float)



#Biogas plants points
# sicherstellen, dass es WGS84 ist (Mapbox braucht lon/lat)
gdf_plants = gdf_plants.to_crs(4326)

# nur Punkte behalten (falls in der Datei mal was anderes drin ist)
gdf_plants = gdf_plants[gdf_plants.geometry.notnull()].copy()
gdf_plants = gdf_plants[gdf_plants.geometry.geom_type.isin(["Point", "MultiPoint"])].copy()

# lon/lat Spalten
gdf_plants["lon"] = gdf_plants.geometry.x
gdf_plants["lat"] = gdf_plants.geometry.y

# IDs sauber als int
gdf_main["TARGET_FID"] = gdf_main["TARGET_FID"].astype(int)
gdf_technical["TARGET_FID"] = gdf_technical["TARGET_FID"].astype(int)

# Merge detour + Reclassifi rüber
gdf_main = gdf_main.merge(
    gdf_technical[["TARGET_FID", "detour_fac", "Reclassifi"]],
    on="TARGET_FID",
    how="left",
    suffixes=("", "_tech")
)



# für Buffer/Distanz in Metern (Schweiz)
gdf_main_2056 = gdf_main.to_crs(2056).copy()

# Spatial index für schnelle "which polygons might intersect buffer"
sindex = gdf_main_2056.sindex

def sum_within_detour_buffer(target_fid: int, value_col: str,road_max_km: float = 15.0):
    # ausgewähltes Polygon
    sel = gdf_main_2056.loc[gdf_main_2056["TARGET_FID"] == int(target_fid)]
    if sel.empty:
        raise ValueError(f"TARGET_FID {target_fid} nicht gefunden.")
    sel = sel.iloc[0]

    detour = float(sel.get("detour_fac", 1.0))
    if not np.isfinite(detour) or detour <= 0:
        detour = 1.0

    # road_distance ≈ euclid_distance * detour  => euclid_radius = road_max / detour
    euclid_radius_m = (float(road_max_km) * 1000.0) / detour

    center = sel.geometry.representative_point()  # stabiler als centroid bei weird shapes
    buf = center.buffer(euclid_radius_m, resolution=64)

    # Kandidaten über bbox (schnell), dann exakt prüfen
    cand_idx = list(sindex.intersection(buf.bounds))
    cand = gdf_main_2056.iloc[cand_idx]
    inside = cand[cand.intersects(buf)]

    total = float(inside[value_col].sum())

    # Buffer als GeoJSON (für Plotly/Mapbox in 4326)
    buf_4326 = gpd.GeoSeries([buf], crs=2056).to_crs(4326).iloc[0]
    buffer_geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "TARGET_FID": int(target_fid),
                "road_max_km": float(road_max_km),
                "detour_fac": detour,
                "euclid_radius_m": euclid_radius_m,
                "sum_TJ": total
            },
            "geometry": mapping(buf_4326)
        }]
    }

    return total, buffer_geojson, inside[["TARGET_FID", value_col]], buf_4326

def polygon_to_latlon_lines(poly_4326):
    # unterstützt Polygon oder MultiPolygon
    if poly_4326.geom_type == "Polygon":
        polys = [poly_4326]
    else:
        polys = list(poly_4326.geoms)

    lats, lons = [], []
    for p in polys:
        x, y = p.exterior.coords.xy  # x=lon, y=lat
        lons += list(x) + [None]
        lats += list(y) + [None]
    return lats, lons

fig = px.choropleth_mapbox(
    gdf_main.to_crs(4326),
    geojson=json.loads(gdf_main.to_json()),   # neu erzeugen, sicherheitshalber
    locations="TARGET_FID",
    featureidkey="properties.TARGET_FID",
    color="Total_primary_energy_available_TJ",
    custom_data=["TARGET_FID"],               # <- DAS ist Punkt 1
    mapbox_style="carto-positron",
    center={"lat": 46.8, "lon": 8.3},
    zoom=7,
)

#--------------Utilization options prep.--------------------------------------
gridcode_mapping = {
    1: "Electricity only",
    11: "Gas, no heat",
    101: "Heat, no gas",
    102: "Gas and heat, different locations",
    111: "Gas and heat, same location",
}

gdf_technical["util_option"] = gdf_technical["Reclassifi"].map(gridcode_mapping).fillna("Unknown")

# Ensure gridcode is treated as an integer before mapping
gdf_technical['Reclassifi'] = gdf_technical['Reclassifi'].astype(int)

# Add the new column with the mapped values
gdf_technical['Reclassifi_named'] = gdf_technical['Reclassifi'].map(gridcode_mapping)

gdf_main["util_option"] = gdf_main["Reclassifi"].map(gridcode_mapping).fillna("Unknown")
gdf_main["util_option"] = gdf_main["util_option"].astype(str)

#--------------Legal requir. prep.--------------------------------------

gridcode_mapping_legal = {
    0: "No farms located in legally designated areas",
    1: "At least one farm located in legal permissive area with lenient legal criteria estimates",
    2: "At least one farm located in legal permissive area with restrictive legal criteria estimates",
    3: "Farms located in both lenient and restrictive legal areas",
}



# Ensure gridcode is treated as an integer before mapping
gdf_legal['legal_clas'] = gdf_legal['legal_clas'].astype(int)

# Add the new column with the mapped values
gdf_legal['legal_clas_named'] = gdf_legal['legal_clas'].map(gridcode_mapping_legal)


# --------------------- PRECOMPUTE FM once (STATIC, does not depend on days) ---

gdf_pot_env,_, _, _, _, _, _, _, _ = calculate_potential(input_shapefile)

FM_COLS_AV = [
    "FM_total_t_cattle_av",
    "FM_total_t_horses_av",
    "FM_total_t_sheep_av",
    "FM_total_t_goats_av",
    "FM_total_t_pigs_av",
    "FM_total_t_poultry_av",
]



#---------------- Initialization of Dash app ------------------------------------------------------------------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.COSMO])
# Expose the server object for Gunicorn
server = app.server


column_labels = {
    'Total_primary_energy_available_TJ': 'Available potential from manure: Primary energy content in TJ per year',
    'Total_biomethane_yield_available_TJ': 'Available potential from manure: Potential biomethane yield in TJ per year',
}

column_labels_technical = {
    'Reclassifi': 'Utilization options',
}

short_titles = {
    "Total_primary_energy_available_TJ": "Primary energy [TJ/y]",
    "Total_biomethane_yield_available_TJ": "Biomethane potential [TJ/y]"
}

# Define layout of the app
app.layout = html.Div([
    html.H1('Decision support tool for agricultural biogas plants in Switzerland'),
    html.H5('Version 0.0 – 9 January 2026'),

    html.H4("Purpose"),
    html.P(
        "This decision support tool supports the early-stage assessment of suitable locations "
        "for agricultural biogas plants in Switzerland, focusing on manure as feedstock."
    ),

    html.H4("What the tool provides"),
    html.Ul([
        html.Li("Manure-based energy potential"),
        html.Li("Legal constraints and regulatory framework"),
        html.Li("Technical requirements"),
        html.Li("Climate change impacts"),
    ]),

    html.H4("Manure-to-energy pathways"),
    html.Ul([
        html.Li("Combined heat and power (CHP) generation"),
        html.Li("Biogas upgrading to biomethane"),
    ]),

    html.H4("Important notes"),
    html.P(
        "The tool is intended as a screening-level decision support instrument. "
        "A detailed site-specific analysis remains necessary before concrete planning decisions."
    ),
    html.P(
        "Legal requirements are not always unambiguous and may vary across cantons, authorities, "
        "and site-specific conditions. To reflect this uncertainty, both restrictive and lenient "
        "estimates are provided based on expert judgement and the literature."
    ),

    html.H4("Methodological background"),
    html.P(
        "Werner, S., et al. (in preparation). Unlocking manure's energy potential in Switzerland: "
        "A GIS-based decision support tool for agricultural biogas plants."
    ),

    html.H3("Map mode"),

    dcc.Dropdown(
        id="map_mode",
        options=[
            {"label": "Energy potential", "value": "energy"},
            {"label": "Technical restrictions", "value": "technical"},
            {"label": "Regulatory framework for plant siting", "value": "legal"},
            {"label": "Climate change impacts (GWP100)", "value": "gwp"},
        ],
        value="energy",
        clearable=False,
        style={"maxWidth": "520px", "marginBottom": "10px"}
    ),

    # --- Energy controls ---
    html.Div(
        id="controls-energy",
        children=[
            html.H4("Energy potential from manure"),
            dcc.RadioItems(
                id="energy_metric",
                options=[
                    {"label": column_labels["Total_primary_energy_available_TJ"], "value": "Total_primary_energy_available_TJ"},
                    {"label": column_labels["Total_biomethane_yield_available_TJ"], "value": "Total_biomethane_yield_available_TJ"},
                ],
                value="Total_primary_energy_available_TJ",
                inline=False
            ),

            html.H4("Energy potential with transport"),
            html.Label("Max. road distance (km)"),
            dcc.Slider(
                id="road-max-km",
                min=1, max=30, step=1, value=15,
                marks=None,
                tooltip={"placement": "bottom", "always_visible": True}
            ),
            dbc.Button(
                "Deselect",
                id="clear-selection",
                color="secondary",
                outline=True,
                n_clicks=0,
                style={"marginTop": "10px"}
            ),
        ],
        style={"display": "block"}
    ),
    #---Legal controls---
    html.Div(
        id="controls-legal",
        children=[
            html.H4("Regulatory framework"),
            dcc.RadioItems(
                            id="legal_metric",
                            options=[
                                {"label": "Regulatory framework", "value": "legal_cla"},
                            ],
                            value="legal_cla",
                            inline=False
                        ),
            dcc.Checklist(
                id="show-plants-legal",
                options=[{"label": "Show existing biogas plants", "value": "on"}],
                value=["on"],
                style={"marginTop": "10px"}
            ),
        ],
        style={"display": "none"}
    ),
    # --- Technical controls ---
    html.Div(
        id="controls-technical",
        children=[
            html.H4("Technical restrictions"),
            dcc.RadioItems(
                id="technical_metric",
                options=[
                    {"label": "Utilization options", "value": "Reclassifi"},
                ],
                value="Reclassifi",
                inline=False
            ),
            dcc.Checklist(
                id="show-plants",
                options=[{"label": "Show existing biogas plants", "value": "on"}],
                value=["on"],
                style={"marginTop": "10px"}
            ),
        ],
        style={"display": "none"}
    ),
    #---gwp controls---
    html.Div(
        id="controls-gwp",
        children=[
            html.H4("Climate change impacts (GWP100)"),
            dcc.RadioItems(
                id="gwp_pathway",
                options=[
                    {
                        "label": "No energy recovery",
                        "value": "no_recovery"},
                    {
                        "label": "CHP",
                        "value": "chp"},
                    {
                        "label": "Upgrading",
                        "value": "upgrading"},
                ],
                value="no_recovery",
                style={
                    "maxWidth": "520px",
                    "marginBottom": "10px"}
            ),
        ],
        style={
            "display": "none"}
    ),

    # shared outputs / stores
    html.Div(id="sum-output", style={"marginTop": "10px", "fontWeight": "600"}),
    dcc.Store(id="selected-fid", data=None),
    dcc.Store(id="map_settings", data={'zoom': 7, 'center': {"lat": 47, "lon": 8.5}}),
    # --- GWP: controls only for NO ENERGY RECOVERY (days) ---
    html.Div(
        id="controls-gwp-no-recovery",
        children=[
            html.H5("No energy recovery – storage duration"),
            html.Div([
                html.Label("Storage days:"),
                dcc.Input(id="days_summer", type="number", value=90, min=1, max=183, step=1),
            ], style={
                'display': 'flex',
                'gap': '20px',
                'margin-bottom': '10px'}),
        ],
        style={
            "display": "none"}  # default hidden
    ),
    html.Div(
        id="controls-gwp-chp",
        children=[
            html.H5("CHP pathway – parameters"),

            html.Label("Days pre-digestion storage:"),
            dcc.Input(id="chp_days_pre", type="number", value=12, min=0, step=1),

            html.Label("Days post-digestion storage:"),
            dcc.Input(id="chp_days_post", type="number", value=30, min=0, step=1),

            html.Hr(),

            html.Label("External heat usage factor (0–1)"),
            dcc.Slider(
                id="chp_external_heat_pct",
                min=0, max=100, step=5, value=35,
                tooltip={
                    "placement": "bottom",
                    "always_visible": True}
            ),
        ],
        style={
            "display": "none"},
    ),
    html.Div(
        id="controls-gwp-upgrading",
        children=[
            html.H5("Upgrading pathway – parameters"),

            html.Label("Days pre-storage (summer):"),
            dcc.Input(id="upg_days_pre", type="number", value=12, min=0, step=1),

            html.Label("Days post-storage (summer):"),
            dcc.Input(id="upg_days_post", type="number", value=30, min=0, step=1),

        ],
        style={"display": "none"},
    ),

    dcc.Graph(id="graph", style={'width': '100%', 'height': '650px'}, config={'scrollZoom': True}),



])


@callback(
    Output("controls-energy", "style"),
    Output("controls-technical", "style"),
    Output("controls-legal", "style"),
    Output("controls-gwp", "style"),
    Output("controls-gwp-no-recovery", "style"),
    Output("controls-gwp-chp", "style"),
    Output("controls-gwp-upgrading", "style"),
    Input("map_mode", "value"),
    Input("gwp_pathway", "value"),
)
def toggle_controls(map_mode, gwp_pathway):
    hide = {"display": "none"}
    show = {"display": "block"}

    # default: alles hide
    energy_style = hide
    technical_style = hide
    legal_style = hide
    gwp_style = hide
    gwp_no_rec_style = hide
    gwp_chp_style = hide
    gwp_upg_style = hide

    if map_mode == "energy":
        energy_style = show
    elif map_mode == "technical":
        technical_style = show
    elif map_mode == "legal":
        legal_style = show
    elif map_mode == "gwp":
        gwp_style = show
        # days inputs nur bei no_recovery
        if gwp_pathway == "no_recovery":
            gwp_no_rec_style = show
        if gwp_pathway == "chp":
            gwp_chp_style = show
        if gwp_pathway == "upgrading":
            gwp_upg_style = show

    return energy_style, technical_style, legal_style, gwp_style, gwp_no_rec_style,gwp_chp_style,gwp_upg_style


@callback(
    Output("selected-fid", "data"),
    Input("graph", "clickData"),
    Input("clear-selection", "n_clicks"),
    Input("map_mode", "value"),
    prevent_initial_call=True
)
def store_selected_fid(clickData, clear_clicks, map_mode):
    # 1. Sicherheitscheck: In anderen Modi nichts tun
    if map_mode in ["technical", "legal", "gwp"]:
        return None

    # 2. Prüfen, wer den Callback ausgelöst hat
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger = ctx.triggered_id

    # 3. Bei "Deselect" Button
    if trigger == "clear-selection":
        return None

    # 4. Der eigentliche Klick auf die Karte (Dein Fix!)
    if trigger == "graph":
        # Grundlegender Check: Haben wir überhaupt Daten?
        if not clickData or "points" not in clickData or not clickData["points"]:
            raise PreventUpdate

        p = clickData["points"][0]
        # Strategie B: Location (Backup, oft identisch mit der ID bei Choropleth)
        if "location" in p and p["location"] is not None:
            return int(p["location"])

        # Strategie A: Customdata (Unsere bevorzugte ID)
        if "customdata" in p and p["customdata"] is not None:
            cd = p["customdata"]
            # Sicherstellen, dass wir eine einzelne Zahl bekommen (manchmal ist es eine Liste)
            return int(cd[0] if isinstance(cd, (list, tuple)) else cd)

        # Wenn wir hier sind, wurde geklickt, aber es war kein gültiges Polygon 
        # (z.B. Klick auf eine Grenzlinie oder Hintergrund).
        # Besser nichts tun als abstürzen.
        raise PreventUpdate

    raise PreventUpdate


_emissions_cache = {}

def get_emissions_cached(input_shapefile, days_summer):
    key = (input_shapefile, days_summer)
    if key in _emissions_cache:
        return _emissions_cache[key].copy()

    gdf_em = calculate_emissions(input_shapefile, days_summer)
    _emissions_cache[key] = gdf_em
    return gdf_em.copy()

def build_gdf_emissions_pw1(days_summer):
    gdf_em = get_emissions_cached(input_shapefile, days_summer)

    if "TARGET_FID" not in gdf_em.columns:
        raise ValueError("TARGET_FID missing in gdf_em (calculate_emissions output).")
    gdf_em["TARGET_FID"] = gdf_em["TARGET_FID"].astype(int)

    cols = ["TARGET_FID"] + FM_COLS_AV
    gdf_em = gdf_em.drop(columns=[c for c in FM_COLS_AV if c in gdf_em.columns], errors="ignore")

    gdf_em = gdf_em.merge(
        gdf_pot_env[cols],
        on="TARGET_FID",
        how="left",
        validate="one_to_one"
    ).fillna(0.0)

    gdf_em = compute_field_n2o_vectorized(gdf_em)

    gdf_em["GWP100_field_CO2eq"] = gdf_em["N2O_field_kg"] * 273
    return gdf_em





# Define callback to store map settings (zoom and center)
@app.callback(
    Output("map_settings", "data"),
    [Input("graph", "relayoutData")],
    [State("map_settings", "data")]
)
def update_map_settings(relayoutData, map_settings):
    if (relayoutData and
        "mapbox.zoom" in relayoutData and
        "mapbox.center" in relayoutData):
        map_settings['zoom'] = relayoutData["mapbox.zoom"]
        map_settings['center'] = relayoutData["mapbox.center"]
    return map_settings

@app.callback(
    Output("graph", "figure"),
    Output("sum-output", "children"),
    Input("map_mode", "value"),
    Input("energy_metric", "value"),
    Input("technical_metric", "value"),
    Input("legal_metric", "value"),
    Input("selected-fid", "data"),
    Input("road-max-km", "value"),
    Input("show-plants", "value"),
    Input("show-plants-legal", "value"),
    Input("gwp_pathway","value"),
    Input("days_summer", "value"),
    Input("chp_days_pre", "value"),
    Input("chp_days_post", "value"),
    Input("chp_external_heat_pct", "value"),
    Input("upg_days_pre", "value"),
    Input("upg_days_post", "value"),
    State("map_settings", "data"),
    prevent_initial_call=False
)
def update_map(
    map_mode, energy_metric, technical_metric, legal_metric, selected_fid, road_max_km,
    show_plants, show_plants_legal, gwp_pathway,
    days_summer,
    chp_days_pre, chp_days_post, chp_external_heat_pct,upg_days_pre, upg_days_post,
    map_settings
):

    # decide which column to draw (NO overlay)
    if map_mode == "technical":
        fig = px.choropleth_mapbox(
            gdf_main,
            geojson=geojson_main,
            locations=gdf_main.index,
            color="util_option",  # <-- DISKRET
            mapbox_style="carto-positron",
            zoom=map_settings["zoom"],
            center=map_settings["center"],
            opacity=0.7,
            labels={
                "util_option": "Utilization option"},
            category_orders={
                "util_option": [
                    "Electricity only",
                    "Gas, no heat",
                    "Heat, no gas",
                    "Gas and heat, different locations",
                    "Gas and heat, same location",
                ]
            },
            color_discrete_map={
                "Electricity only": "#fdae61",
                "Gas, no heat": "#abd9e9",
                "Heat, no gas": "#a6d96a",
                "Gas and heat, different locations": "#ffffbf",
                "Gas and heat, same location": "#2c7bb6",
                "Unknown": "#d9d9d9",
            },
        )
        if show_plants and "on" in show_plants:
            fig.add_trace(go.Scattermapbox(
                lat=gdf_plants["lat"],
                lon=gdf_plants["lon"],
                mode="markers",
                marker=go.scattermapbox.Marker(size=9, opacity=0.7, color="black"),
                name="Existing biogas plants (State 2020 KEV recipients) ",
                text=gdf_plants.apply(
                    lambda r: f"{r.get('Name', 'Biogas plant')}<br>",
                    axis=1
                ),
                hoverinfo="text",
                showlegend=True
            ))

        fig.update_layout(
            mapbox=dict(
                style="carto-positron",
                zoom=map_settings["zoom"],
                center=map_settings["center"],
                layers=[{
                    "sourcetype": "geojson",
                    "source": cantons_geojson,
                    "type": "line",
                    "color": "rgba(50,50,50,0.8)",
                    "line": {
                        "width": 1.5},
                }],
            ),
            legend=dict(
                title="Utilization option",
                itemsizing="constant"
            ),
            margin={
                "r": 0,
                "t": 0,
                "l": 0,
                "b": 0},
            width=1200,
            height=650
        )

        return fig, "Technical view selected."

    if map_mode == "legal":
        # if you want to keep a radio switch later, use this:
        # color_col = legal_metric or "legal_clas_named"
        color_col = "legal_clas_named"

        fig = px.choropleth_mapbox(
            gdf_legal.to_crs(4326),
            geojson=geojson_legal,
            locations=gdf_legal.index,
            color=color_col,  # DISCRETE categories (strings)
            mapbox_style="carto-positron",
            zoom=map_settings["zoom"],
            center=map_settings["center"],
            opacity=0.7,
            labels={
                color_col: "Regulatory status (farm-based)"},
            category_orders={
                color_col: [
                    "No farms located in legally designated areas",
                    "At least one farm located in lenient legal area",
                    "At least one farm located in restrictive legal area",
                    "Farms located in both lenient and restrictive legal areas",
                ]
            },
            color_discrete_map={
                "No farms located in legally designated areas": "#d9d9d9",
                "At least one farm located in lenient legal area": "#a6d96a",
                "At least one farm located in restrictive legal area": "#fdae61",
                "Farms located in both lenient and restrictive legal areas": "#d7191c",
                "Unknown": "#bdbdbd",
            },
        )

        # robust hover (shows the category text)
        fig.update_traces(
            customdata=gdf_legal[color_col],
            hovertemplate="Regulatory status (farm-based): %{customdata}<extra></extra>"
        )

        # show plants in legal mode (use show_plants_legal input!)
        if show_plants_legal and "on" in show_plants_legal:
            fig.add_trace(go.Scattermapbox(
                lat=gdf_plants["lat"],
                lon=gdf_plants["lon"],
                mode="markers",
                marker=go.scattermapbox.Marker(
                    size=9,
                    opacity=0.85,
                    color="black"
                ),
                name="Existing biogas plants (State 2020 KEV recipients)",
                text=gdf_plants.apply(lambda r: f"{r.get('Name', 'Biogas plant')}<br>", axis=1),
                hoverinfo="text",
                showlegend=True
            ))

        fig.update_layout(
            mapbox=dict(
                style="carto-positron",
                zoom=map_settings["zoom"],
                center=map_settings["center"],
                layers=[{
                    "sourcetype": "geojson",
                    "source": cantons_geojson,
                    "type": "line",
                    "color": "rgba(50,50,50,0.8)",
                    "line": {
                        "width": 1.5},
                }],
            ),
            legend=dict(title="Regulatory status", itemsizing="constant"),
            margin={
                "r": 0,
                "t": 0,
                "l": 0,
                "b": 0},
            width=1200,
            height=650
        )

        return fig, "Regulatory framework view selected."

    if map_mode == "gwp":
        days_summer = int(days_summer or 90)

        # 1) Baseline immer berechnen (für gemeinsame Skala)
        gdf_base = build_gdf_emissions_pw1(days_summer)
        gdf_base["GWP100_total_noRec_kg"] = (
                gdf_base["Total_GWP100_CO2eq_prestorage"] + gdf_base["GWP100_field_CO2eq"]
        )

        # Baseline in t (das wird geplottet und skaliert!)
        gdf_base["GWP100_total_noRec_t"] = gdf_base["GWP100_total_noRec_kg"] / 1000.0

        vmin_base = gdf_base["GWP100_total_noRec_t"].quantile(0.05)
        vmax_base = gdf_base["GWP100_total_noRec_t"].quantile(0.95)

        # ---------- NO ENERGY RECOVERY ----------
        if gwp_pathway == "no_recovery":
            gdf_em = gdf_base
            col = "GWP100_total_noRec_t"
            title = "GWP100 – No energy recovery"

        elif gwp_pathway == "chp":
            gdf_em = gdf_base.copy()
            external_heat = float(chp_external_heat_pct or 35) / 100.0

            gdf_em = apply_chp_emissions_to_polygons(
                gdf_em,
                days_prestorage=int(chp_days_pre or 0),
                days_poststorage=int(chp_days_post or 0),
                external_heat_usage=external_heat,
            )
            gdf_em["GWP100_total_CHP_t"] = gdf_em["GWP100_total_CHP_CO2eq"] / 1000.0
            col = "GWP100_total_CHP_t"
            title = "GWP100 – CHP pathway"


        elif gwp_pathway == "upgrading":

            gdf_em = gdf_base.copy()

            gdf_em = apply_upgrading_emissions_to_polygons(
                gdf_em,
                days_prestorage=int(upg_days_pre or 0),
                days_poststorage=int(upg_days_post or 0),
            )

            gdf_em["GWP100_total_UPG_t"] = gdf_em["GWP100_total_UPG_CO2eq"] / 1000.0

            col = "GWP100_total_UPG_t"

            title = "GWP100 – Upgrading pathway"

        else:
            raise PreventUpdate

        geojson_em = json.loads(gdf_em.to_crs(4326).to_json())

        fig = px.choropleth_mapbox(
            gdf_em.to_crs(4326),
            geojson=geojson_em,
            locations="TARGET_FID",
            featureidkey="properties.TARGET_FID",
            color=col,
            zoom=map_settings["zoom"],
            center=map_settings["center"],
            opacity=0.7,
            color_continuous_scale=px.colors.sequential.Reds,
            range_color=(vmin_base, vmax_base),  # <<< FIXED SCALE
            labels={
                col: "GWP100 total [t CO₂-eq]"},
            custom_data=["TARGET_FID"],
        )
        ticks = np.linspace(vmin_base, vmax_base, 5)
        fig.update_coloraxes(
            colorbar_title="GWP100 total [t CO₂-eq/a]",
            colorbar_tickvals=ticks,
            colorbar_ticktext=[
                "≥ 0",
                f"{ticks[1]:.0f}",
                f"{ticks[2]:.0f}",
                f"{ticks[3]:.0f}",
                f"≥ {vmax_base:.0f}"
            ]
        )
        fig.update_traces(
            hovertemplate=(
                "GWP100 total: %{z:.1f} t CO₂-eq/a"
                "<extra></extra>"
            )
        )
        fig.update_layout(
            mapbox=dict(
                style="carto-positron",
                zoom=map_settings["zoom"],
                center=map_settings["center"],
                layers=[{
                    "sourcetype": "geojson",
                    "source": cantons_geojson,
                    "type": "line",
                    "color": "rgba(50,50,50,0.8)",
                    "line": {
                        "width": 1.5},
                }],
            ),
            margin={
                "r": 0,
                "t": 0,
                "l": 0,
                "b": 0},
            width=1200,
            height=650
        )

        return fig, title

    # --- energy mode ---
    color_column = energy_metric or "Total_primary_energy_available_TJ"
    labels = {color_column: column_labels.get(color_column, color_column)}
    hovertemplate = f'{labels[color_column]}: %{{z:.2f}}<extra></extra>'

    s = pd.to_numeric(gdf_main[color_column], errors="coerce").fillna(0.0)
    vmin, vmax = s.quantile(0.05), s.quantile(0.95)

    fig = px.choropleth_mapbox(
        gdf_main_4326,
        geojson=geojson_main_4326,
        color=color_column,
        locations="TARGET_FID",
        featureidkey="properties.TARGET_FID",
        zoom=map_settings["zoom"],
        center=map_settings["center"],
        opacity=0.7,
        color_continuous_scale=px.colors.sequential.YlOrRd,
        labels=labels,
        range_color=(vmin, vmax),
        #custom_data=["TARGET_FID"],  # <-- wichtig für clickData
    )
    ticks = np.linspace(vmin, vmax, 5)
    fig.update_coloraxes(
        colorbar_title=short_titles.get(color_column, color_column),
        colorbar_tickvals=ticks,
        colorbar_ticktext=[
            "≥ 0",
            f"{ticks[1]:.1f}",
            f"{ticks[2]:.1f}",
            f"{ticks[3]:.1f}",
            f"≥ {vmax:.1f}"
        ]
    )

    fig.update_traces(hovertemplate=hovertemplate)


    fig.update_layout(
                mapbox=dict(
                    style="carto-positron",
                    zoom=map_settings["zoom"],
                    center=map_settings["center"],
                    layers=[{
                        "sourcetype": "geojson",
                        "source": cantons_geojson,
                        "type": "line",
                        "color": "rgba(50,50,50,0.8)",
                        "line": {"width": 1.5},
                    }],
                ),
                margin={"r":0,"t":0,"l":0,"b":0},
                width=1200, height=650
            )

    if selected_fid is None:
        return fig, "Click a polygon to calculate the aggregated energy potential within the selected transport distance."

    total, _, _, buf_4326 = sum_within_detour_buffer(int(selected_fid), color_column, float(road_max_km))
    lats, lons = polygon_to_latlon_lines(buf_4326)

    fig.add_trace(go.Scattermapbox(
        lat=lats, lon=lons, mode="lines",
        hoverinfo="skip",
        line={"width": 3},
        showlegend=False
    ))

    return fig, f"Sum: {total:.2f} TJ per year (road distance buffer={road_max_km} km)"



# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)



