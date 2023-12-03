
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import requests
import plotly.express as px
import urllib.error
import time

def download_file(url):
    max_retries = 3
    delay = 5  # Initial delay in seconds

    for _ in range(max_retries):
        try:
            # Your download operation here
            data = pd.read_csv(url, header=0)
            # ...
            break  # If download is successful, break the loop
        except urllib.error.URLError:
            print(f"Download failed. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Increase the delay each time
    else:
        print(f"Failed to download file after {max_retries} attempts.")
    
    return data

# Load your dataset
# Your existing functions and Dash initialization
# GitHub raw file URL
github_url = 'https://raw.githubusercontent.com/fsatlis/141B/main/zipdatafixed.csv'
# Read CSV file into a Pandas DataFrame
zipdata = download_file(github_url)
# OpenWeatherMap API key
api_key = '4a8b15e8da98bcfed048039b4851248d'

def get_zip_weather(api_key,zipp, country = 'US'):
    """Get the weather for zip."""
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?zip={zipp},{country}&appid={api_key}&units=imperial"
    response = requests.get(weather_url)
    return response.json()

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the layout of your dashboard
app.layout = html.Div(
    children=[
        html.H1("ZIP Data Dashboard"),

        # Dropdown for selecting Official State Name
        dcc.Dropdown(
            id='state-dropdown',
            options=[
                {'label': state, 'value': state}
                for state in zipdata['Official State Name'].unique()
            ],
            placeholder="Select an Official State Name",
        ),

        # Dropdown for selecting Primary Official County Name
        dcc.Dropdown(
            id='county-dropdown',
            placeholder="Select a Primary Official County Name",
        ),

        # Display selected Zip Code information
        html.Div(id='selected-zip-info'),

        # Weather map button and output
        html.Button('Generate Weather Map', id='weather-map-button'),
        dcc.Graph(id='weather-map'),
    ]
)


# Define callback to update county dropdown based on selected state
@app.callback(
    Output('county-dropdown', 'options'),
    [Input('state-dropdown', 'value')]
)
def update_county_dropdown(selected_state):
    if selected_state is not None:
        # Filter counties based on the selected state
        counties = zipdata[zipdata['Official State Name'] == selected_state]['Primary Official County Name'].unique()

        # Format options for the dropdown
        county_options = [{'label': county, 'value': county} for county in counties]
        return county_options
    else:
        return []


# Define callback to update displayed information based on selected state and county
@app.callback(
    Output('selected-zip-info', 'children'),
    [Input('state-dropdown', 'value'),
     Input('county-dropdown', 'value')]
)
def update_selected_info(selected_state, selected_county):
    if selected_state is not None and selected_county is not None:
        # Filter zip codes based on the selected state and county
        selected_zips = zipdata[(zipdata['Official State Name'] == selected_state) & (
                    zipdata['Primary Official County Name'] == selected_county)]['Zip Code'].unique()

        # Display selected Zip Code information
        info_text = f"Selected State: {selected_state}\nSelected County: {selected_county}\nZip Codes: {', '.join(map(str, selected_zips))}"
        return info_text
    else:
        return "No selection."


# Define callback to update weather map based on button click
@app.callback(
    Output('weather-map', 'figure'),
    [Input('weather-map-button', 'n_clicks')],
    [State('state-dropdown', 'value'),
     State('county-dropdown', 'value')]
)
def update_weather_map(n_clicks, selected_state, selected_county):
    if n_clicks is not None and selected_state is not None and selected_county is not None:
        # Get zip codes for the selected state and county
        zipcodes = zipdata[(zipdata['Official State Name'] == selected_state) & (
                    zipdata['Primary Official County Name'] == selected_county)]['Zip Code']

        combined = []
        for zipcode in zipcodes:
            test_data = get_zip_weather(api_key, zipcode)
            # gather subseted data
            weather_info = test_data['weather'][0]
            main_info = test_data['main']
            wind_info = test_data['wind']
            loc_info = test_data['coord']
            city_info = test_data['name']
            # join all to a dictionary
            sub = {**{'name': city_info},
                   **{'zip': zipcode},
                   **weather_info,
                   **main_info,
                   **wind_info,
                   **loc_info}
            combined.append(sub)

        df = pd.DataFrame(combined)

        # Create the weather map figure
        fig = px.scatter_mapbox(
            df,
            lon=df['lon'],
            lat=df['lat'],
            hover_name=df['name'],
            hover_data=df[['feels_like', 'temp_min', 'temp_max', 'humidity']],
            zoom=5,
            color=df['temp'],
            width=900,
            height=600,
            size=df['speed'],
            color_continuous_scale="temps",
            title=f'Weather Map of {selected_county} county'
        )
        fig.update_layout(mapbox_style='carto-positron')

        return fig
    else:
        # Return an empty figure if not all required inputs are available
        return px.scatter()


# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)