from dash import Dash, dcc, html, Input, Output, State, callback_context
from dash import ctx
import dash_bootstrap_components as dbc
import plotly.express as px
import geopandas as gpd
import json
import os
import plotly.graph_objects as go
import pandas as pd
from shapely.geometry import Polygon, mapping
from potential import calculate_potential
from lca_polygon_application import apply_baseline_emissions_to_polygons
from lca_polygon_application import apply_chp_emissions_to_polygons
from lca_polygon_application import apply_upgrading_emissions_to_polygons
import numpy as np
from dash.exceptions import PreventUpdate

# =============================================================================
# STARTUP: Alle Daten einmalig laden & vorbereiten
# =============================================================================

input_shapefile = "data/Polygons_Cantonal_Climate_WGS_1984.shp"
technical_path  = "data/Polygons_technical_29_12_25_export_wgs.shp"
biogas_path     = "data/biogas_plants_points_export_wgs.shp"
legal_path      = "data/Polygons_legal_29_12_25_Project_export_wgs.shp"

def load_or_cache(shp_path):
    parquet_path = shp_path.replace(".shp", ".parquet")
    if os.path.exists(parquet_path):
        return gpd.read_parquet(parquet_path)
    gdf = gpd.read_file(shp_path)
    try:
        gdf.to_parquet(parquet_path)
    except Exception:
        pass
    return gdf

gdf_technical = load_or_cache(technical_path)
gdf_plants    = load_or_cache(biogas_path)
gdf_legal     = load_or_cache(legal_path)

gdf_main, fm_totals, dm_totals, x1, x2, x3, x4, x5, x6 = calculate_potential(input_shapefile)

gdf_main = gdf_main.rename(columns={
    "Climatezon": "climate_zone",
    "Klimazone": "climate_zone",
    "climateZone": "climate_zone",
})

gdf_pot_env = gdf_main.copy()

FM_COLS_AV = [
    "FM_total_t_cattle_av",
    "FM_total_t_horses_av",
    "FM_total_t_sheep_av",
    "FM_total_t_goats_av",
    "FM_total_t_pigs_av",
    "FM_total_t_poultry_av",
]

gdf_technical["Reclassifi"] = pd.to_numeric(gdf_technical["Reclassifi"], errors="coerce").fillna(1).astype(int)
gdf_technical["detour_fac"] = pd.to_numeric(gdf_technical["detour_fac"], errors="coerce").fillna(1.0).astype(float)

gdf_plants = gdf_plants.to_crs(4326)
gdf_plants = gdf_plants[gdf_plants.geometry.notnull()].copy()
gdf_plants = gdf_plants[gdf_plants.geometry.geom_type.isin(["Point", "MultiPoint"])].copy()
gdf_plants["lon"] = gdf_plants.geometry.x
gdf_plants["lat"] = gdf_plants.geometry.y

gdf_main["TARGET_FID"]      = gdf_main["TARGET_FID"].astype(int)
gdf_technical["TARGET_FID"] = gdf_technical["TARGET_FID"].astype(int)

gdf_main = gdf_main.merge(
    gdf_technical[["TARGET_FID", "detour_fac", "Reclassifi"]],
    on="TARGET_FID", how="left", suffixes=("", "_tech")
)

gridcode_mapping = {
    1:   "Electricity only",
    11:  "Gas, no heat",
    101: "Heat, no gas",
    102: "Gas and heat, different locations",
    111: "Gas and heat, same location",
}
gdf_technical["util_option"]      = gdf_technical["Reclassifi"].map(gridcode_mapping).fillna("Unknown")
gdf_technical["Reclassifi_named"] = gdf_technical["Reclassifi"].map(gridcode_mapping)
gdf_main["util_option"]           = gdf_main["Reclassifi"].map(gridcode_mapping).fillna("Unknown").astype(str)

gridcode_mapping_legal = {
    0: "No farms located in legally designated areas",
    1: "At least one farm located in legal permissive area with lenient legal criteria estimates",
    2: "At least one farm located in legal permissive area with restrictive legal criteria estimates",
    3: "Farms located in both lenient and restrictive legal areas",
}
gdf_legal["legal_clas"]       = gdf_legal["legal_clas"].astype(int)
gdf_legal["legal_clas_named"] = gdf_legal["legal_clas"].map(gridcode_mapping_legal)

gdf_main_4326      = gdf_main.to_crs(4326).copy()
gdf_cantons        = gdf_main.dissolve(by="Canton").to_crs(4326)
gdf_legal_4326     = gdf_legal.to_crs(4326)
gdf_legal_4326 = gdf_legal_4326.reset_index(drop=True)
gdf_legal_4326["legal_id"] = gdf_legal_4326.index
# =============================================================================
# EXPORT LIGHTWEIGHT GEOJSON FILES FOR DASH ASSETS
# =============================================================================

os.makedirs("assets", exist_ok=True)

main_geojson_path = "assets/polygons_main.geojson"
legal_geojson_path = "assets/polygons_legal.geojson"

if not os.path.exists(main_geojson_path):
    gdf_main_4326[["TARGET_FID", "geometry"]].to_file(
        main_geojson_path,
        driver="GeoJSON"
    )

if not os.path.exists(legal_geojson_path):
    gdf_legal_4326[["legal_id", "geometry"]].to_file(
        legal_geojson_path,
        driver="GeoJSON"
    )




cantons_geojson    = json.loads(gdf_cantons.to_json())

gdf_main_2056 = gdf_main.to_crs(2056).copy()
sindex        = gdf_main_2056.sindex



def build_gdf_emissions_pw1(days_summer):
    gdf_em = apply_baseline_emissions_to_polygons(
        gdf_pot_env.copy(),
        days_summer=int(days_summer)
    )
    return gdf_em

_gwp_geojson_cache = {}

def get_gwp_geojson(gdf_em):
    key = id(gdf_em)
    if key not in _gwp_geojson_cache:
        _gwp_geojson_cache[key] = json.loads(gdf_em.to_crs(4326).to_json())
    return _gwp_geojson_cache[key]

def sum_within_detour_buffer(target_fid: int, value_col: str, road_max_km: float = 15.0):
    sel = gdf_main_2056.loc[gdf_main_2056["TARGET_FID"] == int(target_fid)]
    if sel.empty:
        raise ValueError(f"TARGET_FID {target_fid} nicht gefunden.")
    sel    = sel.iloc[0]
    detour = float(sel.get("detour_fac", 1.0))
    if not np.isfinite(detour) or detour <= 0:
        detour = 1.0
    euclid_radius_m = (float(road_max_km) * 1000.0) / detour
    center          = sel.geometry.representative_point()
    buf             = center.buffer(euclid_radius_m, resolution=64)
    cand_idx = list(sindex.intersection(buf.bounds))
    cand     = gdf_main_2056.iloc[cand_idx]
    inside   = cand[cand.intersects(buf)]
    total    = float(inside[value_col].sum())
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
    polys = [poly_4326] if poly_4326.geom_type == "Polygon" else list(poly_4326.geoms)
    lats, lons = [], []
    for p in polys:
        x, y = p.exterior.coords.xy
        lons += list(x) + [None]
        lats += list(y) + [None]
    return lats, lons

CANTON_LAYER = {
    "sourcetype": "geojson",
    "source":     cantons_geojson,
    "type":       "line",
    "color":      "rgba(50,50,50,0.8)",
    "line":       {"width": 1.5},
}

def base_layout(zoom, center):
    return dict(
        mapbox=dict(style="carto-positron", zoom=zoom, center=center, layers=[CANTON_LAYER]),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        width=1200,
        height=650,
    )

# =============================================================================
# DASH APP
# =============================================================================
app    = Dash(__name__, external_stylesheets=[dbc.themes.COSMO])
server = app.server

column_labels = {
    "Total_primary_energy_available_TJ":  "Available potential from manure: Primary energy content in TJ per year",
    "Total_biomethane_yield_available_TJ": "Available potential from manure: Potential biomethane yield in TJ per year",
}
short_titles = {
    "Total_primary_energy_available_TJ":  "Primary energy [TJ/y]",
    "Total_biomethane_yield_available_TJ": "Biomethane potential [TJ/y]",
}

app.layout = html.Div([
    html.H1("Decision support tool for agricultural biogas plants in Switzerland"),
    html.H5("Version 0.0 – 05 May 2026"),

    html.H4("Purpose"),
    html.P(
        "This decision support tool supports the early-stage assessment of suitable locations "
        "for agricultural biogas plants in Switzerland, focusing on manure as feedstock."
    ),

    html.H4("Please note:"),
    html.P("The tool and its maps may take a few seconds to minutes to load."),

    html.H3("Map mode"),
    dcc.Dropdown(
        id="map_mode",
        options=[
            {"label": "Energy potential",                      "value": "energy"},
            {"label": "Technical restrictions",                "value": "technical"},
            {"label": "Regulatory framework for plant siting", "value": "legal"},
            {"label": "Climate change impacts (GWP100)",       "value": "gwp"},
        ],
        value="energy", clearable=False,
        style={"maxWidth": "520px", "marginBottom": "10px"}
    ),

    # --- Energy controls ---
    html.Div(id="controls-energy", children=[
        html.H4("Energy potential from manure"),
        dcc.RadioItems(
            id="energy_metric",
            options=[{"label": v, "value": k} for k, v in column_labels.items()],
            value="Total_primary_energy_available_TJ", inline=False
        ),
        html.H4("Energy potential with transport"),
        html.Label("Max. road distance (km)"),
        dcc.Slider(id="road-max-km", min=1, max=30, step=1, value=15, marks=None,
                   tooltip={"placement": "bottom", "always_visible": True}),
        dbc.Button("Deselect", id="clear-selection", color="secondary", outline=True,
                   n_clicks=0, style={"marginTop": "10px"}),
        # FIX: show-plants nur hier, nicht doppelt
        dcc.Checklist(
            id="show-plants",
            options=[{"label": "Show existing biogas plants", "value": "on"}],
            value=["on"], style={"marginTop": "10px"}
        ),
    ], style={"display": "block"}),

    # --- Legal controls ---
    html.Div(id="controls-legal", children=[
        html.H4("Regulatory framework"),
        dcc.RadioItems(id="legal_metric",
                       options=[{"label": "Regulatory framework", "value": "legal_cla"}],
                       value="legal_cla", inline=False),
        dcc.Checklist(
            id="show-plants-legal",
            options=[{"label": "Show existing biogas plants", "value": "on"}],
            value=["on"], style={"marginTop": "10px"}
        ),
    ], style={"display": "none"}),

    # --- Technical controls ---
    html.Div(id="controls-technical", children=[
        html.H4("Technical restrictions"),
        dcc.RadioItems(id="technical_metric",
                       options=[{"label": "Utilization options", "value": "Reclassifi"}],
                       value="Reclassifi", inline=False),
        dcc.Checklist(
            id="show-plants-technical",
            options=[{"label": "Show existing biogas plants", "value": "on"}],
            value=["on"], style={"marginTop": "10px"}
        ),
    ], style={"display": "none"}),

    # --- GWP controls ---
    html.Div(id="controls-gwp", children=[
        html.H4("Climate change impacts (GWP100)"),
        dcc.RadioItems(
            id="gwp_view",
            options=[
                {"label": "Absolute emissions – No energy recovery (baseline)", "value": "abs_no_recovery"},
                {"label": "Absolute emissions – CHP",                           "value": "abs_chp"},
                {"label": "Absolute emissions – Upgrading",                     "value": "abs_upgrading"},
            ],
            value="abs_no_recovery",
            style={"maxWidth": "560px", "marginBottom": "10px"},
        ),
    ], style={"display": "none"}),

    # Stores (kein UI)
    dcc.Store(id="selected-fid", data=None),
    dcc.Store(id="map_settings", data={"zoom": 7, "center": {"lat": 47, "lon": 8.5}}),
    dcc.Store(id="chp_heat_substitution", data=0.102),  # Oil: 0.102 kgCO2/MJ (fixed)

    # GWP sub-controls
    html.Div(id="controls-gwp-no-recovery", children=[
        html.H5("No energy recovery – storage duration"),
        html.Div([
            html.Label("Storage days:"),
            dcc.Input(id="days_summer", type="number", value=90, min=1, max=183, step=1),
        ], style={"display": "flex", "gap": "20px", "margin-bottom": "10px"}),
    ], style={"display": "none"}),

    html.Div(id="controls-gwp-chp", children=[
        html.H5("CHP pathway – parameters"),
        html.Label("Days pre-digestion storage:"),
        dcc.Input(id="chp_days_pre", type="number", value=12, min=0, step=1),
        html.Label("Days post-digestion storage:"),
        dcc.Input(id="chp_days_post", type="number", value=30, min=0, step=1),
        html.Hr(),
        html.Label("Excess heat usage factor (0–100%)"),
        dcc.Slider(id="chp_external_heat_pct", min=0, max=100, step=5, value=35,
                   tooltip={"placement": "bottom", "always_visible": True}),
    ], style={"display": "none"}),

    html.Div(id="controls-gwp-upgrading", children=[
        html.H5("Upgrading pathway – parameters"),
        html.Label("Days pre-storage (summer):"),
        dcc.Input(id="upg_days_pre", type="number", value=12, min=0, step=1),
        html.Label("Days post-storage (summer):"),
        dcc.Input(id="upg_days_post", type="number", value=30, min=0, step=1),
    ], style={"display": "none"}),

    dcc.Loading(
        id="loading-map",
        type="default",
        color="#2c7bb6",
        children=[
            html.Div(id="sum-output", style={"marginTop": "10px", "fontWeight": "600"}),
            dcc.Graph(
                id="graph",
                style={"width": "100%", "height": "650px"},
                config={"scrollZoom": True, "displayModeBar": False},
            ),
        ],
    ),



    html.H4("Additional Information:"),
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
    html.P(
        "Transport distance representation: "
        "The displayed buffer represents an equivalent linear (Euclidean) distance, adjusted by "
        "polygon-specific detour factors to approximate a maximum road transport distance. "
        "All polygons that intersect the buffer are selected and fully included in the aggregation."
    ),
    html.H4("Methodological background"),
    html.P(
        "Werner, S., et al. (in preparation). Unlocking manure's energy potential from local to "
        "national scale: A case study of Switzerland"
    ),
])

# =============================================================================
# CALLBACKS
# =============================================================================

@app.callback(
    Output("controls-energy",          "style"),
    Output("controls-technical",       "style"),
    Output("controls-legal",           "style"),
    Output("controls-gwp",             "style"),
    Output("controls-gwp-no-recovery", "style"),
    Output("controls-gwp-chp",         "style"),
    Output("controls-gwp-upgrading",   "style"),
    Input("map_mode",  "value"),
    Input("gwp_view",  "value"),
)
def toggle_controls(map_mode, gwp_view):
    hide, show = {"display": "none"}, {"display": "block"}
    e = t = l = g = nr = chp = upg = hide
    if map_mode == "energy":
        e = show
    elif map_mode == "technical":
        t = show
    elif map_mode == "legal":
        l = show
    elif map_mode == "gwp":
        g = show
        if gwp_view == "abs_no_recovery":
            nr = show
        elif gwp_view == "abs_chp":
            nr  = show
            chp = show
        elif gwp_view == "abs_upgrading":
            nr  = show
            upg = show
    return e, t, l, g, nr, chp, upg


@app.callback(
    Output("selected-fid", "data"),
    Input("graph",           "clickData"),
    Input("clear-selection", "n_clicks"),
    Input("map_mode",        "value"),
    prevent_initial_call=True,
)
def store_selected_fid(clickData, clear_clicks, map_mode):
    if map_mode in ["technical", "legal", "gwp"]:
        raise PreventUpdate
    if not ctx.triggered:
        raise PreventUpdate
    trigger = ctx.triggered_id
    if trigger == "clear-selection":
        return None
    if trigger == "graph":
        if not clickData or "points" not in clickData or not clickData["points"]:
            raise PreventUpdate
        p = clickData["points"][0]
        if "location" in p and p["location"] is not None:
            return int(p["location"])
        if "customdata" in p and p["customdata"] is not None:
            cd = p["customdata"]
            return int(cd[0] if isinstance(cd, (list, tuple)) else cd)
        raise PreventUpdate
    raise PreventUpdate


@app.callback(
    Output("map_settings", "data"),
    Input("graph", "relayoutData"),
    State("map_settings", "data"),
)
def update_map_settings(relayoutData, map_settings):
    if relayoutData and "mapbox.zoom" in relayoutData and "mapbox.center" in relayoutData:
        map_settings["zoom"]   = relayoutData["mapbox.zoom"]
        map_settings["center"] = relayoutData["mapbox.center"]
    return map_settings


@app.callback(
    Output("graph",      "figure"),
    Output("sum-output", "children"),
    Input("map_mode",              "value"),
    Input("energy_metric",         "value"),
    Input("technical_metric",      "value"),
    Input("legal_metric",          "value"),
    Input("selected-fid",          "data"),
    Input("road-max-km",           "value"),
    Input("show-plants",           "value"),
    Input("show-plants-legal",     "value"),
    Input("show-plants-technical", "value"),
    Input("gwp_view",              "value"),
    Input("days_summer",           "value"),
    Input("chp_days_pre",          "value"),
    Input("chp_days_post",         "value"),
    Input("chp_external_heat_pct", "value"),
    State("chp_heat_substitution", "data"),
    Input("upg_days_pre",          "value"),
    Input("upg_days_post",         "value"),
    State("map_settings",          "data"),
    prevent_initial_call=False,
)
def update_map(
    map_mode, energy_metric, technical_metric, legal_metric,
    selected_fid, road_max_km,
    show_plants, show_plants_legal, show_plants_technical,
    gwp_view,
    days_summer, chp_days_pre, chp_days_post, chp_external_heat_pct,
    chp_heat_substitution,
    upg_days_pre, upg_days_post,
    map_settings,
):
    zoom, center = map_settings["zoom"], map_settings["center"]

    # ------------------------------------------------------------------
    # TECHNICAL
    # ------------------------------------------------------------------
    if map_mode == "technical":
        plot_df_technical = gdf_main[["TARGET_FID", "util_option"]].copy()

        fig = px.choropleth_mapbox(
            plot_df_technical,
            geojson="assets/polygons_main.geojson",
            locations="TARGET_FID",
            featureidkey="properties.TARGET_FID",
            color="util_option",
            mapbox_style="carto-positron",
            zoom=zoom, center=center, opacity=0.7,
            labels={"util_option": "Utilization option"},
            custom_data=["util_option"],
            category_orders={"util_option": [
                "Electricity only", "Gas, no heat", "Heat, no gas",
                "Gas and heat, different locations", "Gas and heat, same location",
            ]},
            color_discrete_map={
                "Electricity only":                 "#fdae61",
                "Gas, no heat":                     "#abd9e9",
                "Heat, no gas":                     "#a6d96a",
                "Gas and heat, different locations": "#ffffbf",
                "Gas and heat, same location":       "#2c7bb6",
                "Unknown":                           "#d9d9d9",
            },
        )
        fig.update_traces(
            hovertemplate="Utilization option: %{customdata[0]}<extra></extra>",
        )

        if show_plants_technical and "on" in show_plants_technical:
            fig.add_trace(go.Scattermapbox(
                lat=gdf_plants["lat"], lon=gdf_plants["lon"], mode="markers",
                marker=go.scattermapbox.Marker(size=9, opacity=0.7, color="black"),
                name="Existing biogas plants (State 2020 KEV recipients)",
                text=gdf_plants.apply(lambda r: f"{r.get('Name', 'Biogas plant')}<br>", axis=1),
                hoverinfo="text", showlegend=True,
            ))
        fig.update_layout(**base_layout(zoom, center),
                          legend=dict(title="Utilization option", itemsizing="constant"))
        return fig, "Technical view selected."

    # ------------------------------------------------------------------
    # LEGAL
    # ------------------------------------------------------------------
    if map_mode == "legal":
        color_col = "legal_clas_named"
        plot_df_legal = gdf_legal_4326[["legal_id", "legal_clas_named"]].copy()

        fig = px.choropleth_mapbox(
            plot_df_legal,
            geojson="assets/polygons_legal.geojson",
            locations="legal_id",
            featureidkey="properties.legal_id",
            color="legal_clas_named",
            mapbox_style="carto-positron",
            zoom=zoom,
            center=center,
            opacity=0.7,
            labels={
                "legal_clas_named": "Regulatory status (farm-based)"},
            custom_data=["legal_clas_named"],
            category_orders={color_col: [
                "No farms located in legally designated areas",
                "At least one farm located in lenient legal area",
                "At least one farm located in restrictive legal area",
                "Farms located in both lenient and restrictive legal areas",
            ]},
            color_discrete_map={
                "No farms located in legally designated areas":                                          "#d9d9d9",
                "At least one farm located in legal permissive area with lenient legal criteria estimates":   "#a6d96a",
                "At least one farm located in legal permissive area with restrictive legal criteria estimates": "#fdae61",
                "Farms located in both lenient and restrictive legal areas":                              "#d7191c",
                "Unknown": "#bdbdbd",
            },
        )
        fig.update_traces(
            hovertemplate="Regulatory status (farm-based): %{customdata[0]}<extra></extra>"
        )

        if show_plants_legal and "on" in show_plants_legal:
            fig.add_trace(go.Scattermapbox(
                lat=gdf_plants["lat"], lon=gdf_plants["lon"], mode="markers",
                marker=go.scattermapbox.Marker(size=9, opacity=0.85, color="black"),
                name="Existing biogas plants (State 2020 KEV recipients)",
                text=gdf_plants.apply(lambda r: f"{r.get('Name', 'Biogas plant')}<br>", axis=1),
                hoverinfo="text", showlegend=True,
            ))
        fig.update_layout(**base_layout(zoom, center),
                          legend=dict(title="Regulatory status", itemsizing="constant"))
        return fig, "Regulatory framework view selected."

    # ------------------------------------------------------------------
    # GWP
    # ------------------------------------------------------------------
    if map_mode == "gwp":
        days_summer = int(days_summer or 90)
        gwp_view    = gwp_view or "abs_no_recovery"
        heat_pct    = float(chp_external_heat_pct if chp_external_heat_pct is not None else 35)

        gdf_base = build_gdf_emissions_pw1(days_summer)

        vmin_base = gdf_base["GWP100_total_noRec_t"].quantile(0.05)
        vmax_base = gdf_base["GWP100_total_noRec_t"].quantile(0.95)

        if gwp_view == "abs_no_recovery":
            gdf_em = gdf_base
            col    = "GWP100_total_noRec_t"
            title  = f"GWP100 – No energy recovery | Storage: {days_summer} days"

        elif gwp_view == "abs_chp":
            gdf_em = apply_chp_emissions_to_polygons(
                gdf_base.copy(),
                days_prestorage=int(chp_days_pre or 0),
                days_poststorage=int(chp_days_post or 0),
                external_heat_usage=heat_pct / 100.0,
                heat_substitution_oil=float(chp_heat_substitution or 0.102),
            )
            gdf_em["GWP100_total_CHP_t"] = gdf_em["GWP100_total_CHP_CO2eq"] / 1000.0
            col   = "GWP100_total_CHP_t"
            title = (
                f"GWP100 – CHP | "
                f"Pre: {int(chp_days_pre or 0)}d | Post: {int(chp_days_post or 0)}d | "
                f"Excess heat: {heat_pct:.0f}%"
            )

        elif gwp_view == "abs_upgrading":
            gdf_em = apply_upgrading_emissions_to_polygons(
                gdf_base.copy(),
                days_prestorage=int(upg_days_pre or 0),
                days_poststorage=int(upg_days_post or 0),
            )
            gdf_em["GWP100_total_UPG_t"] = gdf_em["GWP100_total_UPG_CO2eq"] / 1000.0
            col   = "GWP100_total_UPG_t"
            title = (
                f"GWP100 – Upgrading | "
                f"Pre: {int(upg_days_pre or 0)}d | Post: {int(upg_days_post or 0)}d"
            )

        else:
            raise PreventUpdate



        plot_df = gdf_em[["TARGET_FID", col]].copy()

        fig = px.choropleth_mapbox(
            plot_df,
            geojson="assets/polygons_main.geojson",
            locations="TARGET_FID",
            featureidkey="properties.TARGET_FID",
            color=col,
            zoom=zoom, center=center, opacity=0.7,
            color_continuous_scale=px.colors.sequential.Reds,
            range_color=(vmin_base, vmax_base),
            labels={col: "GWP100 total [t CO₂-eq]"},
            custom_data=["TARGET_FID"],
        )
        ticks = np.linspace(vmin_base, vmax_base, 5)
        fig.update_coloraxes(
            colorbar_title="GWP100 total [t CO₂-eq/a]",
            colorbar_tickvals=ticks,
            colorbar_ticktext=["≥ 0", f"{ticks[1]:.0f}", f"{ticks[2]:.0f}",
                               f"{ticks[3]:.0f}", f"≥ {vmax_base:.0f}"],
        )
        fig.update_traces(hovertemplate=" %{z:.1f} t CO₂-eq/a<extra></extra>")
        fig.update_layout(**base_layout(zoom, center))
        return fig, title

    # ------------------------------------------------------------------
    # ENERGY (default)
    # ------------------------------------------------------------------
    color_column  = energy_metric or "Total_primary_energy_available_TJ"
    label         = {color_column: column_labels.get(color_column, color_column)}
    hovertemplate = f'{label[color_column]}: %{{z:.2f}}<extra></extra>'

    s          = pd.to_numeric(gdf_main[color_column], errors="coerce").fillna(0.0)
    vmin, vmax = s.quantile(0.05), s.quantile(0.95)

    plot_df = gdf_main_4326[["TARGET_FID", color_column]].copy()

    fig = px.choropleth_mapbox(
        plot_df,
        geojson="assets/polygons_main.geojson",
        color=color_column,
        locations="TARGET_FID",
        featureidkey="properties.TARGET_FID",
        zoom=zoom, center=center, opacity=0.7,
        color_continuous_scale=px.colors.sequential.YlOrRd,
        labels=label,
        range_color=(vmin, vmax),
    )
    ticks = np.linspace(vmin, vmax, 5)
    fig.update_coloraxes(
        colorbar_title=short_titles.get(color_column, color_column),
        colorbar_tickvals=ticks,
        colorbar_ticktext=["≥ 0", f"{ticks[1]:.1f}", f"{ticks[2]:.1f}",
                           f"{ticks[3]:.1f}", f"≥ {vmax:.1f}"],
    )

    if show_plants and "on" in show_plants:
        fig.add_trace(go.Scattermapbox(
            lat=gdf_plants["lat"],
            lon=gdf_plants["lon"],
            mode="markers",
            marker=go.scattermapbox.Marker(size=9, opacity=0.85, color="black"),
            name="Existing biogas plants (State 2020 KEV recipients)",
            text=gdf_plants.apply(lambda r: f"{r.get('Name', 'Biogas plant')}", axis=1),
            hovertemplate="%{text}<extra></extra>",
            showlegend=True,
        ))

    fig.update_traces(
        hovertemplate=hovertemplate,
        selector=dict(type="choroplethmapbox")
    )
    fig.update_layout(
        **base_layout(zoom, center),
        legend=dict(
            x=0.65,
            y=0.1,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255,255,255,0.75)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1,
            itemsizing="constant"
        )
    )


    if selected_fid is None:
        return fig, "Click a polygon to calculate the aggregated energy potential within the selected transport distance."

    total, _, _, buf_4326 = sum_within_detour_buffer(int(selected_fid), color_column, float(road_max_km))

    # Highlight: ausgewähltes Polygon als dicker roter Rand
    sel_geom = gdf_main_4326.loc[gdf_main_4326["TARGET_FID"] == int(selected_fid), "geometry"]
    if not sel_geom.empty:
        sel_lats, sel_lons = polygon_to_latlon_lines(sel_geom.iloc[0])
        fig.add_trace(go.Scattermapbox(
            lat=sel_lats, lon=sel_lons, mode="lines",
            hoverinfo="skip",
            line={"width": 4, "color": "#e31a1c"},
            showlegend=False,
            name="selected-polygon",
        ))

    # Buffer-Kreis
    lats, lons = polygon_to_latlon_lines(buf_4326)
    fig.add_trace(go.Scattermapbox(
        lat=lats, lon=lons, mode="lines",
        hoverinfo="skip", line={"width": 2, "color": "#1f78b4"}, showlegend=False,
    ))



    return fig, f"Sum: {total:.2f} TJ per year (road distance buffer={road_max_km} km)"


# =============================================================================
if __name__ == "__main__":
    app.run(debug=True)