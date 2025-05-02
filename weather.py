import requests
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
OPENWEATHER_API = os.getenv("OPENWEATHER_API")

def fetch_weather_data(location):
    """Fetch weather data from OpenWeather API for a given location."""
    if not OPENWEATHER_API:
        print("⚠️ OpenWeather API key not found in environment variables")
        return None
    
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={OPENWEATHER_API}&units=metric"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching weather data for {location}: {e}")
        return None

def get_ballpark_locations():
    """Return a dictionary mapping team codes to ballpark cities."""
    return {
        "ARI": "Phoenix,US",
        "ATL": "Atlanta,US",
        "BAL": "Baltimore,US",
        "BOS": "Boston,US",
        "CHC": "Chicago,US",
        "CWS": "Chicago,US",
        "CIN": "Cincinnati,US",
        "CLE": "Cleveland,US",
        "COL": "Denver,US",
        "DET": "Detroit,US",
        "HOU": "Houston,US",
        "KC": "Kansas City,US",
        "LAA": "Anaheim,US",
        "LAD": "Los Angeles,US",
        "MIA": "Miami,US",
        "MIL": "Milwaukee,US",
        "MIN": "Minneapolis,US",
        "NYM": "Queens,US",
        "NYY": "Bronx,US",
        "OAK": "Oakland,US",
        "PHI": "Philadelphia,US",
        "PIT": "Pittsburgh,US",
        "SD": "San Diego,US",
        "SF": "San Francisco,US",
        "SEA": "Seattle,US",
        "STL": "St. Louis,US",
        "TB": "St. Petersburg,US",
        "TEX": "Arlington,US",
        "TOR": "Toronto,CA",
        "WSH": "Washington,US"
    }

def calculate_wind_boost(wind_speed, wind_direction):
    """
    Calculate HR boost based on wind speed and direction
    Higher values = more favorable for HRs
    """
    # Basic assumption: tail wind (blowing outward) helps HRs
    # For simplification, we assume wind_direction of 180 is blowing out to center
    # Values close to 180 are more favorable
    direction_factor = 1 - abs(wind_direction - 180) / 180
    speed_factor = min(wind_speed / 20, 1)  # Cap at wind speed of 20 m/s
    
    # Combined factor ranges from -0.1 to 0.15
    return (direction_factor * speed_factor * 0.15) - 0.1

def get_park_factor(team_code):
    """Get ballpark home run factor for a team."""
    park_factors = {
        "COL": 1.15,  # Coors Field - elevation helps HRs
        "CIN": 1.10,  # Great American Ball Park - HR friendly
        "NYY": 1.08,  # Yankee Stadium - short right field
        "MIL": 1.06,  # American Family Field - retractable roof
        "PHI": 1.05,  # Citizens Bank Park
        "BAL": 1.04,  # Camden Yards 
        "CHC": 1.02,  # Wrigley Field - depends on wind
        "LAA": 1.02,  # Angel Stadium
        "BOS": 1.01,  # Fenway Park
        "TOR": 1.01,  # Rogers Centre
        "ATL": 1.00,  # Truist Park
        "CLE": 1.00,  # Progressive Field
        "CWS": 1.00,  # Guaranteed Rate Field
        "DET": 1.00,  # Comerica Park
        "LAD": 0.99,  # Dodger Stadium
        "STL": 0.99,  # Busch Stadium
        "HOU": 0.98,  # Minute Maid Park
        "MIN": 0.98,  # Target Field
        "ARI": 0.97,  # Chase Field
        "KC": 0.97,  # Kauffman Stadium
        "NYM": 0.97,  # Citi Field
        "OAK": 0.97,  # Oakland Coliseum
        "PIT": 0.97,  # PNC Park
        "TB": 0.97,  # Tropicana Field
        "TEX": 0.97,  # Globe Life Field
        "WSH": 0.97,  # Nationals Park
        "MIA": 0.96,  # LoanDepot Park
        "SEA": 0.95,  # T-Mobile Park
        "SF": 0.90,   # Oracle Park - suppresses HRs
        "SD": 0.92,   # Petco Park
    }
    return park_factors.get(team_code, 1.0)

def apply_weather_boosts(df):
    print("🌤️ Applying weather and park effects...")
    ballpark_locations = get_ballpark_locations()
    
    # Add columns for weather data
    df['wind_boost'] = 0.0
    df['park_factor'] = 1.0
    df['ballpark'] = ""
    
    # Apply team-specific park factors
    for idx, row in df.iterrows():
        team_code = row.get('pitcher_team')
        if team_code:
            df.at[idx, 'park_factor'] = get_park_factor(team_code)
            
            # Get ballpark location and fetch weather
            location = ballpark_locations.get(team_code)
            if location:
                df.at[idx, 'ballpark'] = location.split(',')[0]  # City name
                
                if OPENWEATHER_API:  # Only fetch if API key is available
                    weather_data = fetch_weather_data(location)
                    if weather_data:
                        wind_speed = weather_data.get('wind', {}).get('speed', 0)
                        wind_direction = weather_data.get('wind', {}).get('deg', 0)
                        temp = weather_data.get('main', {}).get('temp', 20)
                        
                        # Apply temp boost (warmer = better for HRs)
                        temp_factor = (temp - 15) / 30  # 15°C is neutral, range: -0.5 to 0.5
                        temp_boost = max(min(temp_factor * 0.05, 0.05), -0.05)
                        
                        wind_boost = calculate_wind_boost(wind_speed, wind_direction)
                        
                        # Combined weather boost
                        df.at[idx, 'wind_boost'] = wind_boost + temp_boost
                else:
                    print(f"⚠️ Weather data not available for {location}")
    
    return df
