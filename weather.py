import requests
import os
import pandas as pd
import numpy as np
import time
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mlb_hr_predictions.log")
    ]
)
logger = logging.getLogger("mlb_weather")

# Load environment variables
load_dotenv()
OPENWEATHER_API = os.getenv("OPENWEATHER_API")

def fetch_weather_data(location):
    """Fetch weather data from OpenWeather API for a given location."""
    if not OPENWEATHER_API:
        logger.warning("⚠️ OpenWeather API key not found in environment variables")
        return None
    
    try:
        # Add retry logic with backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={OPENWEATHER_API}&units=metric"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                # If we get here, request was successful
                data = response.json()
                logger.info(f"✅ Weather data fetched for {location}")
                return data
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"⚠️ Retry {attempt+1}/{max_retries} for {location} after {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise
                    
    except Exception as e:
        logger.error(f"❌ Error fetching weather data for {location}: {e}")
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

def get_ballpark_names():
    """Return a dictionary mapping team codes to ballpark names."""
    return {
        "ARI": "Chase Field",
        "ATL": "Truist Park",
        "BAL": "Oriole Park at Camden Yards",
        "BOS": "Fenway Park",
        "CHC": "Wrigley Field",
        "CWS": "Guaranteed Rate Field",
        "CIN": "Great American Ball Park",
        "CLE": "Progressive Field",
        "COL": "Coors Field",
        "DET": "Comerica Park",
        "HOU": "Minute Maid Park",
        "KC": "Kauffman Stadium",
        "LAA": "Angel Stadium",
        "LAD": "Dodger Stadium",
        "MIA": "LoanDepot Park",
        "MIL": "American Family Field",
        "MIN": "Target Field",
        "NYM": "Citi Field",
        "NYY": "Yankee Stadium",
        "OAK": "Oakland Coliseum",
        "PHI": "Citizens Bank Park",
        "PIT": "PNC Park",
        "SD": "Petco Park",
        "SF": "Oracle Park",
        "SEA": "T-Mobile Park",
        "STL": "Busch Stadium",
        "TB": "Tropicana Field",
        "TEX": "Globe Life Field",
        "TOR": "Rogers Centre",
        "WSH": "Nationals Park"
    }

def get_team_from_ballpark(ballpark_name):
    """Try to determine team code from ballpark name"""
    ballpark_to_team = {v: k for k, v in get_ballpark_names().items()}
    # Exact match
    if ballpark_name in ballpark_to_team:
        return ballpark_to_team[ballpark_name]
    
    # Partial match
    for known_park, team in ballpark_to_team.items():
        if known_park in ballpark_name or ballpark_name in known_park:
            return team
    
    # No match found
    return None

def calculate_enhanced_wind_boost(wind_speed, wind_direction, temp):
    """
    Enhanced wind boost calculation that better accounts for 
    directional effects and temperature
    """
    # Normalize wind direction to value between 0-1 where:
    # 1.0 = perfect tailwind (blowing out to center)
    # 0.0 = perfect headwind (blowing in from center)
    # 0.5 = crosswind (neutral effect)
    
    # Blowing out = ~180 degrees (normalize to 1.0)
    # Blowing in = ~0 or ~360 degrees (normalize to 0.0)
    normalized_direction = 0
    
    if wind_direction is None:
        normalized_direction = 0.5  # Neutral if unknown
    else:
        # Convert to value between 0-1, with 1 being blowing out
        if wind_direction <= 180:
            normalized_direction = wind_direction / 180.0  # 0->0, 90->0.5, 180->1
        else:
            normalized_direction = (360 - wind_direction) / 180.0  # 270->0.5, 360->0
    
    # Calculate directional factor (-0.1 to +0.15)
    direction_factor = (normalized_direction * 0.25) - 0.1
    
    # Speed factor (0 to 0.15)
    speed_factor = min(wind_speed / 20.0, 1.0) * 0.15
    
    # Temperature factor (-0.05 to +0.08)
    # Cold reduces HR, warm increases HR probability
    temp_celsius = temp if temp else 20  # Default temp
    temp_factor = ((temp_celsius - 10) / 30.0) * 0.13 - 0.05
    
    # Combined effect
    return round(direction_factor * speed_factor + temp_factor, 3)

def get_enhanced_park_factor(team_code, weather_conditions=None):
    """
    Enhanced park factor that accounts for specific ballpark characteristics
    and their interaction with weather conditions
    """
    # Base park factors
    base_factors = {
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
    
    # Special cases for specific ballparks
    special_adjustments = {
        # Yankee Stadium right field is very short
        "NYY": lambda x: 0.04 if x.get('batter_stands') == 'L' else 0,
        
        # Wrigley Field is extremely wind-dependent
        "CHC": lambda x: 0.10 if x.get('wind_direction') in range(160, 200) else 
                        -0.08 if x.get('wind_direction') in range(340, 360) or x.get('wind_direction') in range(0, 20) else 0,
        
        # Coors Field effect is amplified in hot weather
        "COL": lambda x: 0.05 if x.get('temperature', 0) > 25 else 0,
        
        # Fenway Park's Green Monster effect
        "BOS": lambda x: 0.06 if x.get('batter_stands') == 'R' else -0.02,
        
        # Oracle Park is especially tough on left-handed power hitters
        "SF": lambda x: -0.05 if x.get('batter_stands') == 'L' else 0,
        
        # Citizens Bank Park plays smaller in warm weather
        "PHI": lambda x: 0.03 if x.get('temperature', 0) > 25 else 0,
    }
    
    # Get base factor with fallback to neutral
    park_factor = base_factors.get(team_code, 1.0)
    
    # Apply special adjustment if applicable
    if team_code in special_adjustments and weather_conditions:
        adjustment = special_adjustments[team_code](weather_conditions)
        park_factor += adjustment
        
    return round(park_factor, 3)

def get_park_factor(team_code):
    """Original simplified park factor function - kept for backward compatibility"""
    return get_enhanced_park_factor(team_code)

def apply_enhanced_weather_boosts(df):
    """
    Apply enhanced weather and park effects to the dataframe.
    Handles various ballpark data formats and ensures no data is lost.
    """
    logger.info("🌤️ Applying enhanced weather and park effects...")
    ballpark_locations = get_ballpark_locations()
    ballpark_names = get_ballpark_names()
    
    # Add columns for weather data with defaults
    df['wind_boost'] = 0.0
    df['park_factor'] = 1.0
    df['temperature'] = 20.0  # Default temperature in Celsius
    df['wind_speed'] = 0.0
    df['wind_direction'] = None
    
    # Check if ballpark data exists
    if 'ballpark' not in df.columns:
        logger.warning("⚠️ No ballpark column found - adding default values")
        df['ballpark'] = "Unknown Ballpark"
    
    # Apply team-specific park factors
    for idx, row in df.iterrows():
        team_code = None
        
        # Try different approaches to find the correct team code
        
        # 1. Use pitcher_team if available
        pitcher_team = row.get('pitcher_team')
        if pitcher_team and isinstance(pitcher_team, str) and len(pitcher_team) <= 3:
            team_code = pitcher_team.upper()
        
        # 2. Use home_team if available and not the same as pitcher_team
        home_team = row.get('home_team')
        if home_team and isinstance(home_team, str) and len(home_team) <= 3:
            venue_team = home_team.upper()
            team_code = venue_team
        
        # 3. Try to determine from ballpark name
        ballpark_name = row.get('ballpark')
        if not team_code and ballpark_name:
            team_code = get_team_from_ballpark(ballpark_name)
            
        # Default if we still don't have a team
        if not team_code:
            logger.warning(f"⚠️ Could not determine team code for {row.get('batter_name', 'Unknown')} vs {row.get('opposing_pitcher', 'Unknown')} at {ballpark_name}")
            team_code = "UNK"
            
        # Weather data to pass to enhanced park factor
        weather_conditions = {
            'batter_stands': row.get('batter_stands', 'R'),  # Default to right-handed
            'temperature': 20,  # Default
            'wind_direction': None,
            'wind_speed': 0
        }
        
        # Get ballpark location and fetch weather
        location = ballpark_locations.get(team_code)
        if location:
            if OPENWEATHER_API:  # Only fetch if API key is available
                weather_data = fetch_weather_data(location)
                if weather_data and 'main' in weather_data and 'wind' in weather_data:
                    wind_speed = weather_data['wind'].get('speed', 0)
                    wind_direction = weather_data['wind'].get('deg')
                    temp = weather_data['main'].get('temp', 20)
                    
                    # Store weather data
                    df.at[idx, 'temperature'] = temp
                    df.at[idx, 'wind_speed'] = wind_speed
                    df.at[idx, 'wind_direction'] = wind_direction
                    
                    # Update weather conditions for park factor
                    weather_conditions.update({
                        'temperature': temp,
                        'wind_direction': wind_direction,
                        'wind_speed': wind_speed
                    })
                    
                    # Calculate enhanced wind boost
                    df.at[idx, 'wind_boost'] = calculate_enhanced_wind_boost(
                        wind_speed, wind_direction, temp
                    )
                    
                    logger.info(f"🌡️ {df.at[idx, 'ballpark']}: {temp}°C, Wind: {wind_speed}m/s at {wind_direction if wind_direction is not None else 'Unknown'}°")
            else:
                logger.warning(f"⚠️ Weather data not available - OpenWeather API key not set")
        else:
            logger.warning(f"⚠️ Location not found for team code: {team_code}")
        
        # Apply enhanced park factor
        df.at[idx, 'park_factor'] = get_enhanced_park_factor(team_code, weather_conditions)
    
    return df

def apply_weather_boosts(df):
    """Original weather function - kept for backward compatibility"""
    return apply_enhanced_weather_boosts(df)
