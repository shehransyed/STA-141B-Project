
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import requests
import plotly.express as px
import urllib.error
import time

def download_file(url):
    max_retries = 10
    delay = 1  # Initial delay in seconds

    for _ in range(max_retries):
        try:
            data = pd.read_csv(url, header=0)

            break  # If download is successful, break the loop
        except urllib.error.URLError:
            print(f"Download failed. Retrying in {delay} seconds...")
            time.sleep(delay)
            # delay *= 2  # Increase the delay each time
    else:
        print(f"Failed to download file after {max_retries} attempts.")
    
    return data

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

def get_hist_weather(api_key, city, country = 'US'):
    """Get 24 hour historical weather for city name."""
    weather_url = f"https://history.openweathermap.org/data/2.5/history/city?q={city},{country}&cnt={24}&appid={api_key}&units=imperial"
    response = requests.get(weather_url)
    return response.json()

def get_forecast_weather(api_key, city, country = 'US'):
    """Get 4 day hourly forecast for city name."""
    weather_url = f"https://pro.openweathermap.org/data/2.5/forecast/hourly?q={city},{country}&appid={api_key}&units=imperial"
    response = requests.get(weather_url)
    return response.json()

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

# Define the layout of your dashboard
app.layout = html.Div(
    children=[
        html.H1("Weather Dashboard"),

        html.H4("Note: This dashboard is running on a free hosting service with limited resources. For demonstration, please select State/County with no more than approximately 10 zip codes. (example: California, Yolo)"),

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

        # Dropdown for selecting City/Town for weather forecast
        dcc.Dropdown(
            id='city-dropdown',
            placeholder="Select a City/Town for temperature chart",
        ),

        # Temperature Chart map button and output
        html.Button('Generate Temperature Chart', id='temp-chart-button'),
        dcc.Graph(id='temp-chart'),
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
            # width=900,
            # height=600,
            size=df['speed'],
            color_continuous_scale="temps",
            title=f'Weather Map of {selected_county} county'
        )
        fig.update_layout(mapbox_style='carto-positron')

        return fig
    else:
        # Return an empty figure if not all required inputs are available
        return px.scatter()
    

# Define callback to update city/town dropdown based on selected county
@app.callback(
    Output('city-dropdown', 'options'),
    [Input('county-dropdown', 'value')]
)
def update_city_dropdown(selected_county):
    if selected_county is not None:
        # Filter cities based on the selected state
        cities = zipdata[zipdata['Primary Official County Name'] == selected_county]['Official USPS city name'].unique()

        # Format options for the dropdown
        city_options = [{'label': city, 'value': city} for city in cities]
        return city_options
    else:
        return []


# Define callback to update temperature chart based on button click
@app.callback(
    Output('temp-chart', 'figure'),
    [Input('temp-chart-button', 'n_clicks')],
    [State('city-dropdown', 'value')]
)
def update_temp_chart(n_clicks, selected_city):
    if n_clicks is not None and selected_city is not None:
        hist_data = get_hist_weather(api_key, selected_city)
        forecast_data = get_forecast_weather(api_key, selected_city)

        # Build historical data frame
        date_time = pd.DataFrame([pd.to_datetime(hist_data['list'][i]['dt'], unit='s') for i in range(len(hist_data['list']))])
        main_data = pd.DataFrame([hist_data['list'][i]['main'] for i in range(len(hist_data['list']))])
        wind_data = pd.DataFrame([hist_data['list'][i]['wind'] for i in range(len(hist_data['list']))])
        cloud_data = pd.DataFrame([hist_data['list'][i]['clouds'] for i in range(len(hist_data['list']))])
        weather_data = pd.DataFrame([hist_data['list'][i]['weather'][0] for i in range(len(hist_data['list']))])

        hist_df = pd.concat([date_time, main_data, wind_data, cloud_data, weather_data], axis=1)
        hist_df['data_type'] = "Historical"

        # Build forecast data frame
        date_time = pd.DataFrame([pd.to_datetime(forecast_data['list'][i]['dt'], unit='s') for i in range(len(forecast_data['list']))])
        main_data = pd.DataFrame([forecast_data['list'][i]['main'] for i in range(len(forecast_data['list']))])
        wind_data = pd.DataFrame([forecast_data['list'][i]['wind'] for i in range(len(forecast_data['list']))])
        cloud_data = pd.DataFrame([forecast_data['list'][i]['clouds'] for i in range(len(forecast_data['list']))])
        weather_data = pd.DataFrame([forecast_data['list'][i]['weather'][0] for i in range(len(forecast_data['list']))])


        forecast_df = pd.concat([date_time, main_data, wind_data, cloud_data, weather_data], axis=1)
        forecast_df['data_type'] = "Forecast"

        #merge data for plotting
        plot_df = pd.concat([hist_df, forecast_df], ignore_index=True, sort=True, axis=0)
        plot_df.rename(columns={plot_df.columns[0]: 'date_time'}, inplace=True)

        # Create the plot
        fig = px.line(plot_df, x='date_time', y=['temp_min', 'temp_max', 'temp'], custom_data=['speed', 'description'],
                    labels={'date_time': 'Date','value': 'Temperature (°F)', 'variable': 'Temperature Type'},
                    title='Current Day and 4-Day Hourly Forecast Temperatures')

        # Add hover data
        fig.update_traces(mode='lines+markers')
        
        for trace in fig.data:
            trace.name = trace.name.replace('_',' ').title()
        fig.update_layout(hovermode='x unified')

        fig.update_traces(hovertemplate="<br>".join([
            "%{y}°F",
            "Wind Speed: %{customdata[0]} mph",
            "Weather: %{customdata[1]}",
        ]))

        return fig
    else:
        # Return an empty figure if not all required inputs are available
        return px.scatter()

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)