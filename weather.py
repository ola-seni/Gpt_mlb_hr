import requests
import os
import pandas as pd
import time
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
OPENWEATHER_API = os.getenv("OPENWEATHER_API")

# Cache for weather data to reduce API calls
WEATHER_CACHE = {}
WEATHER_CACHE_FILE = "cache/weather_cache.json"

def load_weather_cache():
    """Load cached weather data if available"""
    if os.path.exists(WEATHER_CACHE_FILE):
        try:
            with open(WEATHER_CACHE_FILE, 'r') as f:
                cache = json.load(f)
                
            # Convert cache to format we can use
            today = datetime.now().strftime("%Y-%m-%d")
            valid_cache = {}
            for location, data in cache.items():
                if data.get("date") == today:
                    valid_cache[location] = data
                    
            print(f"✅ Loaded {len(valid_cache)} weather cache entries")
            return valid_cache
        except Exception as e:
            print(f"⚠️ Error loading weather cache: {e}")
    
    return {}

def save_weather_cache(cache):
    """Save weather cache to file"""
    try:
        os.makedirs(os.path.dirname(WEATHER_CACHE_FILE), exist_ok=True)
        with open(WEATHER_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
        print(f"✅ Saved {len(cache)} weather cache entries")
    except Exception as e:
        print(f"⚠️ Error saving weather cache: {e}")

def fetch_weather_data(location):
    """Fetch weather data from OpenWeather API with improved error handling"""
    global WEATHER_CACHE
    
    # Initialize cache if needed
    if not WEATHER_CACHE:
        WEATHER_CACHE = load_weather_cache()
    
    # Check cache first
    if location in WEATHER_CACHE:
        print(f"✅ Using cached weather data for {location}")
        return WEATHER_CACHE[location]
    
    # If no API key, use default values
    if not OPENWEATHER_API:
        print(f"⚠️ OpenWeather API key not found, using default weather for {location}")
        default_data = {
            "main": {"temp": 22},  # 22°C is a mild day
            "wind": {"speed": 2.5, "deg": 180},  # Light breeze blowing out
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        WEATHER_CACHE[location] = default_data
        return default_data
    
    # Try to fetch from API with retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🌤️ Fetching weather for {location} (attempt {attempt+1}/{max_retries})")
            url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={OPENWEATHER_API}&units=metric"
            response = requests.get(url, timeout=10)  # Add timeout
            response.raise_for_status()
            
            data = response.json()
            
            # Add date to track freshness
            data["date"] = datetime.now().strftime("%Y-%m-%d")
            
            # Cache the result
            WEATHER_CACHE[location] = data
            
            # Save updated cache
            save_weather_cache(WEATHER_CACHE)
            
            print(f"✅ Weather for {location}: {data['main']['temp']}°C, "
                  f"wind: {data['wind'].get('speed', 0)} m/s at {data['wind'].get('deg', 0)}°")
            return data
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"⚠️ Weather API attempt {attempt+1} failed for {location}, "
                      f"retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                print(f"❌ All weather API attempts failed for {location}: {e}")
                # Provide reasonable default weather rather than failing
                default_data = {
                    "main": {"temp": 22},  # 22°C is a mild day
                    "wind": {"speed": 2.5, "deg": 180},  # Light breeze blowing out
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
                WEATHER_CACHE[location] = default_data
                return default_data
    
    # Shouldn't get here, but just in case
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
        "BAL": "Camden Yards",
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
    
    # Get base factor
    park_factor = base_factors.get(team_code, 1.0)
    
    # Apply special adjustment if applicable
    if team_code in special_adjustments and weather_conditions:
        park_factor += special_adjustments[team_code](weather_conditions)
        
    return round(park_factor, 3)

def apply_enhanced_weather_boosts(df):
    print("🌤️ Applying enhanced weather and park effects...")
    ballpark_locations = get_ballpark_locations()
    ballpark_names = get_ballpark_names()
    
    # Add columns for weather data
    df['wind_boost'] = 0.0
    df['park_factor'] = 1.0
    df['temperature'] = 20.0  # Default temperature in Celsius
    df['wind_speed'] = 0.0
    df['wind_direction'] = None
    
    # Apply team-specific park factors
    for idx, row in df.iterrows():
        # Get home team for ballpark data
        home_team = row.get('home_team')
        
        # Get ballpark info if available
        if not home_team or home_team == "Unknown":
            # Try to infer from ballpark name
            ballpark = row.get('ballpark', "Unknown Ballpark")
            home_team = next((team for team, name in ballpark_names.items() 
                             if name.lower() == ballpark.lower()), None)
        
        # Apply park factor if we have team info
        if home_team and home_team != "Unknown":
            # Ensure it's uppercase to match our dictionaries
            home_team = home_team.upper()
            
            # Set ballpark name if not already set
            if 'ballpark' not in df.columns or pd.isna(row.get('ballpark')) or row.get('ballpark') == "Unknown Ballpark":
                df.at[idx, 'ballpark'] = ballpark_names.get(home_team, f"{home_team} Ballpark")
            
            # Apply park factor
            weather_conditions = {
                'batter_stands': row.get('batter_stands', 'R'),
                'temperature': 20,
                'wind_direction': None,
                'wind_speed': 0
            }
            
            # Get location for weather
            location = ballpark_locations.get(home_team)
            if location and OPENWEATHER_API:
                # Weather API call
                weather_data = fetch_weather_data(location)
                if weather_data:
                    wind_speed = weather_data.get('wind', {}).get('speed', 0)
                    wind_direction = weather_data.get('wind', {}).get('deg', 0)
                    temp = weather_data.get('main', {}).get('temp', 20)
                    
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
                    
                    print(f"🌡️ {df.at[idx, 'ballpark']}: {temp}°C, Wind: {wind_speed}m/s at {wind_direction}°")
            
            # Apply park factor (use enhanced version)
            df.at[idx, 'park_factor'] = get_enhanced_park_factor(home_team, weather_conditions)
            print(f"⚾ Applied park factor {df.at[idx, 'park_factor']} for {df.at[idx, 'ballpark']}")
        else:
            print(f"⚠️ Unknown home team or ballpark for {row.get('batter_name')} vs {row.get('opposing_pitcher')}")
            # Set default reasonable values
            df.at[idx, 'park_factor'] = 1.0
    
    return df

def get_park_factor(team_code):
    """Simplified function to get park factor by team code."""
    # Same base factors as in the enhanced function
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
    
    return base_factors.get(team_code.upper(), 1.0)
