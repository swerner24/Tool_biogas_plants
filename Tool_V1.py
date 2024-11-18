from dash import Dash, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import geopandas as gpd
import json
import plotly.graph_objects as go
import sys
print('Python %s on %s' % (sys.version, sys.platform))
# Load shapefile for the main content
gdf_main = gpd.read_file('C:/Users/Werner/PhD/Tool/Shapefiles/Input_Information_Tool_Project.shp')

# Load shapefile for legal requirements
gdf_legal = gpd.read_file('C:/Users/Werner/PhD/Tool/Shapefiles/Suitablearea_total_Project.shp')

# Load shapefile for technical requirements
gdf_technical = gpd.read_file('C:/Users/Werner/PhD/Tool/Shapefiles/Technical_requirements_excact_project.shp')

# Load shapefile for biogas plants
gdf_biogasplants = gpd.read_file('C:/Users/Werner/PhD/Tool/Shapefiles/Biogasplants_project.shp')

#Calculating centroids for visualisation of clicked polygons
# Step 1: Project to a suitable projected CRS, here: World Mercator (EPSG:3395)
gdf_projected = gdf_main.to_crs(epsg=3395)

# Step 2: Calculate the centroids in the projected CRS
gdf_centroid = gdf_projected.geometry.centroid

# Step 3: To store the centroid coordinates in geographic CRS, reproject the centroids back to EPSG:4326
gdf_centroid_latlon = gdf_centroid.to_crs(epsg=4326)

# Step 4: Add the latitude and longitude of the centroids as new columns in the original GeoDataFrame
gdf_main['centroid_lat'] = gdf_centroid_latlon.y
gdf_main['centroid_lon'] = gdf_centroid_latlon.x

print(gdf_main.columns)



# Convert GeoDataFrame to GeoJSON for the main content
geojson_main = json.loads(gdf_main.to_json())
geojson_legal = json.loads(gdf_legal.to_json())
geojson_technical = json.loads(gdf_technical.to_json())
geojson_biogasplants = json.loads(gdf_biogasplants.to_json())

# Initialize Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.COSMO])

column_labels = {
    'TOTprmGJ': 'Available potential: Primary energy content in GJ',
    'TOTmetGJ': 'Available potential: Potential Biomethane Yield in GJ',
    't_CO2_Eq_P': 'Total environmental impact: "Business-as-usual" Scenario (t CO2-Eq.)',
    't_CO2_Eq2_': 'Total environmental impact: "Anaerobic Digestion" Scenario (t CO2-Eq.)',
    'gridcode': 'Technical requirements',
    'Min_Distan': 'Minimum distance',
    'Max_Distan': 'Maximum distance',
    'Number': 'biogas_plants',
}

# Mapping gridcode to string values
gridcode_mapping = {
    1: 'Electricity only',
    11: 'Heat, no gas',
    101: 'Gas, no heat',
    102: 'Gas and heat, at two separate locations',
    111: 'Gas and heat, at the same location'
}

# Ensure gridcode is treated as an integer before mapping
gdf_main['gridcode'] = gdf_main['gridcode'].astype(int)
gdf_technical['gridcode'] = gdf_technical['gridcode'].astype(int)

# Add the new column with the mapped values
gdf_main['gridcode_named'] = gdf_main['gridcode'].map(gridcode_mapping)
gdf_technical['gridcode_named'] = gdf_technical['gridcode'].map(gridcode_mapping)

# Define layout of the app
app.layout = html.Div([
    html.H1('Information tool for agricultural biogas plants in Switzerland'),
    html.P("The information tool provides a wide range of data to help assess the suitability of a location for an "
           "agricultural biogas plant based on various criteria. It covers the entire country of Switzerland and aims "
           "to assist in planning new agricultural plants while supporting the decision-making process.  However, "
           "a detailed analysis of a specific location is still necessary and recommended."),

    html.H3('Energy and Biogas potential'),

    dcc.RadioItems(
        id='energy_potential',
        options=[
            {'label': column_labels['TOTprmGJ'], 'value': 'TOTprmGJ'},
            {'label': column_labels['TOTmetGJ'], 'value': 'TOTmetGJ'}
        ],
        value=None,
        inline=False
    ),

    html.H3('Environmental impacts (GWP100)'),

    dcc.RadioItems(
        id='gwp100',
        options=[
            {'label': column_labels['t_CO2_Eq_P'], 'value': 't_CO2_Eq_P'},
            {'label': 'Total environmental impact: "Anaerobic Digestion" Scenario (t CO2-Eq.)', 'value': 't_CO2_Eq2_'}
        ],
        value=None,
        inline=False
    ),

    html.Div(id='calculated_input', children=[
        html.Label("Percentage of the excess heat that is utilized:"),
        dcc.Slider(
            id='heat_factor_slider',
            min=0,
            max=1,
            step=0.01,
            value=0.35,
            marks={i / 10: f'{i / 10:.1f}' for i in range(0, 11)},
            tooltip={"placement": "bottom", "always_visible": True}
        ),
        html.Label("Select the heat source that is being replaced:"),
        dcc.Dropdown(
            id='emission_factor_dropdown',
            options=[
                {'label': 'Natural Gas', 'value': 0.030988},
                {'label': 'Other than Natural Gas', 'value': 0.00312}
            ],
            value=0.030988
        ),
    ], style={'display': 'none'}),


    html.H3('Legal Framework'),

    dcc.RadioItems(
        id='legal_requirements',
        options=[
            {'label': 'Legal requirements: Areas that meet the legal criteria', 'value': 'legal'},
            {'label': 'Minimum distance (m): Shortest distance between two farms within a polygon (should be greater '
                      'than 150m)', 'value': 'Min_Distan'},
            {'label': 'Maximum transport distance (m): Largest distance between two farms within a polygon (should be '
                      'less than 12km)', 'value': 'Max_Distan'}
        ],
        value=None,
        inline=False
    ),

    html.H3('Technical requirements'),

    dcc.RadioItems(
        id='technical_requirements',
        options=[
         {'label': 'Minimum size of biogas plant: Shows whether there is enough manure in one polygon to run a '
                  '“combined heat and power” with a capacity by default of 720 GJ (10kWel.)', 'value': 'min_size'},
         {'label': 'Biogas utilization options: Aggregated', 'value': 'gridcode'},
         {'label': 'Biogas utilization options: Exact', 'value': 'gridcode_technical'},
         {'label': 'Current biogas plants (State 2020 KEV recipients)', 'value': 'biogas_plants'}
        ],
        value=None,
        inline=False
    ),

    html.Div(id='min_size_input', children=[
        html.Label("Set the threshold value for the minimum size of \"combined heat and power\" system in GJ:"),
        dcc.Input(id='threshold_input', type='number', value=720),
    ], style={'display': 'none'}),



    dcc.Store(id='clicked_indices', data=[]),
    dcc.Store(id='map_settings', data={'zoom': 7, 'center': {"lat": 47, "lon": 8.5}}),

    html.Div(id='sum_output', style={'textAlign': 'center', 'marginBottom': '20px'}),

    html.Button('Reset Selection', id='reset_button', n_clicks=0),

    dcc.Graph(id="graph", style={'width': '100%', 'height': '650px'}),

    html.H3('More information'),
    html.P(""),
])


# Define callback to enable/disable the selection options
@app.callback(
    [Output('legal_requirements', 'value'),
     Output('technical_requirements', 'value'),
     Output('energy_potential', 'value'),
     Output('gwp100', 'value')],
    [Input('legal_requirements', 'value'),
     Input('technical_requirements', 'value'),
     Input('energy_potential', 'value'),
     Input('gwp100', 'value')]
)
def toggle_selection(legal_requirements, technical_requirements, energy_potential, gwp100):
    ctx = callback_context
    if not ctx.triggered:
        return None, None, None, None
    input_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if input_id == 'legal_requirements':
        return legal_requirements, None, None, None
    elif input_id == 'technical_requirements':
        return None, technical_requirements, None, None
    elif input_id == 'energy_potential':
        return None, None, energy_potential, None
    elif input_id == 'gwp100':
        return None, None, None, gwp100
    return None, None, None, None


# Define callback to show/hide threshold input based on the selected technical requirement
@app.callback(
    Output('min_size_input', 'style'),
    Input('technical_requirements', 'value')
)
def show_hide_threshold_input(selected_technical_requirement):
    if selected_technical_requirement == 'min_size':
        return {'display': 'block'}
    else:
        return {'display': 'none'}


# Define callback to calculate sum when polygons are clicked
@app.callback(
    Output("sum_output", "children"),
    [Input("clicked_indices", "data"),
     Input("legal_requirements", "value"),
     Input("technical_requirements", "value"),
     Input("energy_potential", "value"),
     Input("gwp100", "value"),
     Input("threshold_input", "value"),
     Input("heat_factor_slider", "value"),
     Input("emission_factor_dropdown", "value")]
)
def calculate_sum(clicked_indices, legal_requirements, technical_requirements, energy_potential, gwp100, threshold_value, heat_factor, emission_factor):
    print("Clicked Indices:", clicked_indices)

    selected_metric = legal_requirements or technical_requirements or energy_potential or gwp100

    if clicked_indices:
        if selected_metric == 'min_size':
            values = gdf_main.iloc[clicked_indices]['TOTmetGJ'].apply(lambda x: x if x >= threshold_value else 0).values
        elif selected_metric == 't_CO2_Eq2_':
            gdf_main['Calculated'] = (gdf_main['kg_CO2_PW2'] - (
                    (gdf_main['Excess_hea'] * heat_factor) * emission_factor * 1000)) / 1000
            values = gdf_main.iloc[clicked_indices]['Calculated'].values
        else:
            values = gdf_main.iloc[clicked_indices][selected_metric].values
        total_sum = sum(values)
        return f"Sum of values: {total_sum:.3f}"
    return "You can select polygons on the map to calculate the sum."


# Define callback to update clicked indices in the Store
@app.callback(
    Output("clicked_indices", "data"),
    [Input("graph", "clickData"),
     Input("reset_button", "n_clicks")],
    [State("clicked_indices", "data")]
)
def update_clicked_indices(clickData, n_clicks, stored_indices):
    ctx = callback_context
    if not ctx.triggered:
        return stored_indices
    input_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if input_id == 'reset_button':
        return []

    stored_indices = stored_indices or []  # Initialize as an empty list if None

    if clickData is not None:
        point_index = clickData['points'][0]['pointIndex']
        if point_index in stored_indices:
            stored_indices.remove(point_index)
        else:
            stored_indices.append(point_index)
    return stored_indices

# Ensure FacilityKi is treated as an integer
gdf_biogasplants['FacilityKi'] = gdf_biogasplants['FacilityKi'].astype(int)
# Replace NaN values in CombinedHe with 0 and convert to integer
gdf_biogasplants['CombinedHe'] = gdf_biogasplants['CombinedHe'].fillna(0).astype(float).astype(int)


# Define callback to update the graph with shapefile data
@app.callback(
    Output("graph", "figure"),
    [Input("legal_requirements", "value"),
     Input("technical_requirements", "value"),
     Input("energy_potential", "value"),
     Input("gwp100", "value"),
     Input("threshold_input", "value"),
     Input("heat_factor_slider", "value"),
     Input("emission_factor_dropdown", "value"),
     Input("clicked_indices", "data"),
     State("map_settings", "data")]
)
def display_choropleth(legal_requirements, technical_requirements, energy_potential, gwp100, threshold_value, heat_factor, emission_factor, clicked_indices, map_settings):
    print("display_choropleth called with:")
    print(f"legal_requirements: {legal_requirements}")
    print(f"technical_requirements: {technical_requirements}")
    print(f"energy_potential: {energy_potential}")
    print(f"gwp100: {gwp100}")
    print(f"threshold_value: {threshold_value}")
    print(f"heat_factor: {heat_factor}")
    print(f"emission_factor: {emission_factor}")
    print(f"clicked_indices: {clicked_indices}")
    print(f"map_settings: {map_settings}")

    color_column = None
    fig = go.Figure()  # Initialize fig to avoid UnboundLocalError
    hovertemplate = ''  # Initialize hovertemplate to avoid UnboundLocalError
    if legal_requirements:
        color_column = legal_requirements
    elif technical_requirements:
        if technical_requirements == 'min_size':
            color_column = 'TOTprmGJ'
        elif technical_requirements == 'biogas_plants':
            fig.add_trace(go.Scattermapbox(
                lat=gdf_biogasplants.geometry.y,
                lon=gdf_biogasplants.geometry.x,
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=10,
                    color='blue',
                    opacity=0.7
                ),
                text=gdf_biogasplants.apply(
                    lambda row: f"Name: {row['Name']}<br>Facility: {'Agricultural biogas plant' if row['FacilityKi'] == 1 else 'Industrial biogas plant'}<br>CHP capacity [kW]: {(row['CombinedHe'])}", axis=1),
                hoverinfo='text'
            ))

            fig.update_layout(
                mapbox=dict(
                    style="open-street-map",
                    zoom=map_settings['zoom'],
                    center=map_settings['center']
                ),
                width=1200,
                height=650
            )

            return fig
        else:
            color_column = technical_requirements
    elif energy_potential:
        color_column = energy_potential
    elif gwp100:
        color_column = gwp100

    # Recalculate the 'Calculated' column dynamically if 't_CO2_Eq2_' is selected
    if color_column == 't_CO2_Eq2_':
        gdf_main['Calculated'] = (gdf_main['kg_CO2_PW2'] - (
                (gdf_main['Excess_hea'] * heat_factor) * emission_factor * 1000)) / 1000
        color_column = 'Calculated'

    if color_column:
        if color_column == 'legal':
            fig = px.choropleth_mapbox(
                gdf_legal,
                geojson=gdf_legal.geometry.__geo_interface__,
                locations=gdf_legal.index,
                color='Name',
                color_discrete_map={
                    'Liberal_parameter': 'blue',
                    'Restrictive_parameter': 'red'
                },
                mapbox_style="open-street-map",
                zoom=map_settings['zoom'],
                center=map_settings['center'],
                opacity=0.5
            )
            hovertemplate = 'Legal requirements'
        elif color_column == 'Min_Distan':
            fig = px.choropleth_mapbox(
                gdf_main,
                geojson=geojson_main,
                locations=gdf_main.index,
                color='Min_Distan',
                mapbox_style="open-street-map",
                zoom=map_settings['zoom'],
                center=map_settings['center'],
                opacity=0.5,
                labels = {'Min_Distan': 'Minimum Distance (m)'}
            )
            hovertemplate = 'Minimum Distance (m): %{z}<extra></extra>'
        elif color_column == 'Max_Distan':
            fig = px.choropleth_mapbox(
                gdf_main,
                geojson=geojson_main,
                locations=gdf_main.index,
                color='Max_Distan',
                mapbox_style="open-street-map",
                zoom=map_settings['zoom'],
                center=map_settings['center'],
                opacity=0.5,
                labels={'Max_Distan': 'Maximum Distance (m)'}
            )
            hovertemplate = 'Maximum Distance (m): %{z}<extra></extra>'
        elif color_column == 'gridcode_technical':
            labels = {color_column: column_labels.get(color_column, color_column)}
            hovertemplate = 'Technical requirements'
            color_continuous_scale = None
            category_orders = {"gridcode_named": [
                'Electricity only',
                'Heat, no gas',
                'Gas, no heat',
                'Gas and heat, at two separate locations',
                'Gas and heat, at the same location'
            ]}
            fig = px.choropleth_mapbox(
                gdf_technical,
                geojson=geojson_technical,
                locations=gdf_technical.index,
                color='gridcode_named',
                zoom=map_settings['zoom'],
                center=map_settings['center'],
                opacity=0.7,
                labels=labels,
                category_orders=category_orders,
                color_discrete_map={
                    "Electricity only": "lightgray",
                    "Heat, no gas": "LightGreen",
                    "Gas, no heat": "orange",
                    "Gas and heat, at two separate locations": "Magenta",
                    "Gas and heat, at the same location": "blue"
                }
            )
            hovertemplate = 'Technical requirement'
        elif color_column == 'gridcode':
            labels = {color_column: column_labels.get(color_column, color_column)}
            hovertemplate = 'Technical requirements'
            color_continuous_scale = None
            category_orders = {"gridcode_named": [
                'Electricity only',
                'Heat, no gas',
                'Gas, no heat',
                'Gas and heat, at two separate locations',
                'Gas and heat, at the same location'
            ]}
            fig = px.choropleth_mapbox(
                gdf_main,
                geojson=geojson_main,
                locations=gdf_main.index,
                color='gridcode_named',
                zoom=map_settings['zoom'],
                center=map_settings['center'],
                opacity=0.7,
                labels=labels,
                category_orders=category_orders,
                color_discrete_map={
                    "Electricity only": "lightgray",
                    "Heat, no gas": "LightGreen",
                    "Gas, no heat": "orange",
                    "Gas and heat, at two separate locations": "Magenta",
                    "Gas and heat, at the same location": "blue"
                }
            )
            hovertemplate = 'Technical requirement'
        elif color_column == 'TOTprmGJ' and technical_requirements == 'min_size':
            gdf_main['TOTmetGJ_conditional'] = gdf_main['TOTmetGJ'].apply(lambda x: 'Above threshold' if x >= threshold_value else 'Below threshold')
            fig = px.choropleth_mapbox(
                gdf_main,
                geojson=geojson_main,
                locations=gdf_main.index,
                color='TOTmetGJ_conditional',
                color_discrete_map={
                    'Above threshold': 'green',
                    'Below threshold': 'red'
                },
                mapbox_style="open-street-map",
                zoom=map_settings['zoom'],
                center=map_settings['center'],
                opacity=0.7,

            )
            hovertemplate = 'Minimal amount of manure'

        elif color_column == 'Calculated':  # This ensures the label is applied to Calculated map
            fig = px.choropleth_mapbox(
                gdf_main,
                geojson=geojson_main,
                locations=gdf_main.index,
                color=color_column,
                mapbox_style="open-street-map",
                zoom=map_settings['zoom'],
                center=map_settings['center'],
                opacity=0.7,
                color_continuous_scale = px.colors.sequential.YlOrRd,
                labels={'Calculated': 'Total environmental impact: "Anaerobic Digestion" Scenario (t CO2-Eq.)'}
            )
            hovertemplate = f'Total environmental impact: "Anaerobic Digestion" Scenario (t CO2-Eq.): %{{z}}<extra></extra>'

        else:
            labels = {color_column: column_labels.get(color_column, color_column)}
            hovertemplate = f'{labels[color_column]}: %{{z}}<extra></extra>'
            color_continuous_scale = px.colors.sequential.YlOrRd
            category_orders = None

            max_value = gdf_main[color_column].max()
            print(f"Max value for {color_column}: {max_value}")  # Debugging line

            fig = px.choropleth_mapbox(
                gdf_main,
                geojson=geojson_main,
                color=color_column,
                locations=gdf_main.index,
                zoom=map_settings['zoom'],
                center=map_settings['center'],
                opacity=0.7,
                color_continuous_scale=color_continuous_scale,
                labels=labels,
                range_color=(0, max_value)
            )

        # Highlight the selected polygons if any
        if clicked_indices:
            gdf_selected = gdf_main.iloc[clicked_indices]
            fig.add_trace(go.Scattermapbox(
                lat=gdf_selected['centroid_lat'],
                lon=gdf_selected['centroid_lon'],
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=14,
                    color='red',
                    opacity=0.6
                ),
                text=gdf_selected.index,
                hoverinfo='skip'
            ))

        fig.update_traces(hovertemplate=hovertemplate)

        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            mapbox=dict(
                style="open-street-map",
                zoom=map_settings['zoom'],
                center=map_settings['center']
            ),
            width=1200,
            height=650,
            #clickmode='event+select',
            legend=dict(
                title=dict(text='Legend', font=dict(size=12)),
                itemsizing='constant'
            )
        )

    return fig


#callback to show/hide the slider and dropdown menu based on the selected map
@app.callback(
    Output('calculated_input', 'style'),
    Input('gwp100', 'value')
)
def show_hide_calculated_input(selected_gwp100):
    if selected_gwp100 == 't_CO2_Eq2_':
        return {'display': 'block'}
    else:
        return {'display': 'none'}


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


# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)

