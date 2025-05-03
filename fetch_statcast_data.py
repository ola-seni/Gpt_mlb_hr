from pybaseball import statcast_batter, statcast_pitcher, cache
import pandas as pd
from datetime import datetime

cache.enable()

def fetch_batter_metrics(lineups_df):
    print("📊 Fetching batter metrics...")
    metrics = []

    # Define date range
    if datetime.now().year >= 2025:
        start = "2025-03-01"
        end = datetime.now().strftime("%Y-%m-%d")
    else:
        start = "2023-04-01"
        end = "2023-10-01"

    seen_ids = set()
    for _, row in lineups_df.iterrows():
        batter_id = row['batter_id']
        if batter_id in seen_ids:
            continue
        try:
            stats = statcast_batter(start, end, batter_id)
            if stats.empty:
                continue

            batted = stats[stats['events'].notna()]
            iso = (
                batted['events'].eq('double').sum() * 2 +
                batted['events'].eq('triple').sum() * 3 +
                batted['events'].eq('home_run').sum() * 4
            ) / max(1, batted.shape[0])

            last50 = batted.tail(50)
            barrels = (
                last50['launch_speed'].gt(98) &
                last50['launch_angle'].between(26, 30)
            ).mean()

            metrics.append({
                "batter_name": row["batter_name"],
                "batter_id": batter_id,
                "opposing_pitcher": row["opposing_pitcher"],
                "game_date": row["game_date"],
                "game_id": row["game_id"],
                "ISO": round(iso, 3),
                "barrel_rate_50": round(barrels, 3),
                # Preserve ballpark and home team info
                "ballpark": row.get("ballpark", "Unknown Ballpark"),
                "home_team": row.get("home_team", "Unknown"),
            })
            seen_ids.add(batter_id)

        except Exception as e:
            print(f"❌ Error fetching data for {row['batter_name']}: {e}")
    return pd.DataFrame(metrics)
       
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
                # Weather API call - existing code
                pass  # Keep your existing weather API call code here
            
            # Apply park factor (use enhanced version)
            df.at[idx, 'park_factor'] = get_enhanced_park_factor(home_team, weather_conditions)
            print(f"⚾ Applied park factor {df.at[idx, 'park_factor']} for {df.at[idx, 'ballpark']}")
        else:
            print(f"⚠️ Unknown home team or ballpark for {row.get('batter_name')} vs {row.get('opposing_pitcher')}")
            # Set default reasonable values
            df.at[idx, 'park_factor'] = 1.0
    
    return df

def fetch_pitcher_metrics(lineups_df):
    print("📊 Fetching pitcher metrics...")
    metrics = []

    # Define date range
    if datetime.now().year >= 2025:
        start = "2025-03-01"
        end = datetime.now().strftime("%Y-%m-%d")
    else:
        start = "2023-04-01"
        end = "2023-10-01"

    seen_ids = set()
    for _, row in lineups_df.iterrows():
        pitcher_id = row['pitcher_id']
        if pitcher_id in seen_ids:
            continue
        try:
            stats = statcast_pitcher(start, end, pitcher_id)
            if stats.empty:
                continue

            outs = stats['outs_when_up'].count()
            ip = outs / 3.0
            hr = stats['events'].eq('home_run').sum()
            hr_per_9 = (hr / ip) * 9 if ip > 0 else 0.0

            metrics.append({
                "pitcher_name": row["opposing_pitcher"],
                "pitcher_id": pitcher_id,
                "game_date": row["game_date"],
                "game_id": row["game_id"],
                "hr_per_9": round(hr_per_9, 3),
            })
            seen_ids.add(pitcher_id)

        except Exception as e:
            print(f"❌ Error fetching data for {row['opposing_pitcher']}: {e}")
    return pd.DataFrame(metrics)
