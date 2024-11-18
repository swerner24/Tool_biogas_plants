from dash import Dash, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import geopandas as gpd
import json
import plotly.graph_objects as go
import sys


print('Python %s on %s' % (sys.version, sys.platform))
# Load shapefile for the main content
# gdf_main = gpd.read_file('C:/Users/Werner/PhD/Tool/Shapefiles/Input_Information_Tool_Project.shp')


url = "https://raw.githubusercontent.com/swerner24/Tool_biogas_plants/main/data/Input_Information_Tool_Project.shp"
gdf_main = gpd.read_file(url)

# Convert GeoDataFrame to GeoJSON for the main content
geojson_main = json.loads(gdf_main.to_json())


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
}



# Ensure gridcode is treated as an integer before mapping
gdf_main['gridcode'] = gdf_main['gridcode'].astype(int)




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
    dcc.Store(id='map_settings', data={'zoom': 7, 'center': {"lat": 47, "lon": 8.5}}),
    dcc.Graph(id="graph", style={'width': '100%', 'height': '650px'}),
])


# Define callback to update the graph with shapefile data
@app.callback(
    Output("graph", "figure"),
    [
     Input("energy_potential", "value"),
     State("map_settings", "data")]
)
def display_choropleth(energy_potential, map_settings):
    print("display_choropleth called with:")
    print(f"energy_potential: {energy_potential}")


    color_column = None
    fig = go.Figure()  # Initialize fig to avoid UnboundLocalError
    hovertemplate = ''  # Initialize hovertemplate to avoid UnboundLocalError
    if energy_potential:
        color_column = energy_potential

    if color_column:

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


# Speichern der App als statisches HTML
import os
os.makedirs("export", exist_ok=True)
with open("export/index.html", "w") as f:
    f.write(app.index())


# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)


