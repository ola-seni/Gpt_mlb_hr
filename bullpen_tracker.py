# bullpen_tracker.py

from pybaseball import team_pitching
import pandas as pd

# Average innings pitched by starters (basic proxy)
def get_starter_avg_ip(pitcher_name, year=2024):
    try:
        df = team_pitching(year)
        row = df[df['Name'] == pitcher_name]
        if row.empty:
            return 5.0  # default
        gs = row.iloc[0]['GS']  # Games started
        ip = row.iloc[0]['IP']
        if gs == 0:
            return 5.0
        avg_ip = ip / gs
        return round(avg_ip, 2)
    except Exception as e:
        print(f"⚠️ Starter IP error for {pitcher_name}: {e}")
        return 5.0

# Team bullpen HR/9 (or create a quality score)
def get_bullpen_quality(team_name, year=2024):
    try:
        df = team_pitching(year)
        # Normalize team name variations
        team_name = team_name.upper() if isinstance(team_name, str) else ""
        team_abbrevs = {
            "ARIZONA": "ARI", "ATLANTA": "ATL", "BALTIMORE": "BAL", 
            "BOSTON": "BOS", "CUBS": "CHC", "CHICAGO": "CHC", 
            "WHITE SOX": "CWS", "CINCINNATI": "CIN", "CLEVELAND": "CLE", 
            "COLORADO": "COL", "DETROIT": "DET", "HOUSTON": "HOU",
            "KANSAS CITY": "KC", "ANGELS": "LAA", "DODGERS": "LAD", 
            "LOS ANGELES": "LAD", "MIAMI": "MIA", "MILWAUKEE": "MIL", 
            "MINNESOTA": "MIN", "METS": "NYM", "YANKEES": "NYY", 
            "NEW YORK": "NYY", "OAKLAND": "OAK", "PHILADELPHIA": "PHI", 
            "PITTSBURGH": "PIT", "SAN DIEGO": "SD", "PADRES": "SD", 
            "SAN FRANCISCO": "SF", "GIANTS": "SF", "SEATTLE": "SEA", 
            "ST. LOUIS": "STL", "TAMPA BAY": "TB", "RAYS": "TB", 
            "TEXAS": "TEX", "RANGERS": "TEX", "TORONTO": "TOR", 
            "WASHINGTON": "WSH", "NATIONALS": "WSH"
        }
        team_code = team_abbrevs.get(team_name, team_name)
        
        # Try exact match first
        row = df[df['Team'] == team_code]
        if row.empty:
            # Try substring match as fallback
            for idx, team_row in df.iterrows():
                db_team = str(team_row['Team']).upper()
                if team_code in db_team or db_team in team_code:
                    row = df.iloc[[idx]]
                    break
                    
        if row.empty:
            print(f"⚠️ No team found for: {team_name}")
            return 1.0  # Default to neutral
            
        hr9 = row.iloc[0].get('HR/9', 1.0)
        return round(float(hr9), 2)
    except Exception as e:
        print(f"⚠️ Bullpen data error for {team_name}: {e}")
        return 1.0  # Default to neutral

# Adjust HR score based on how soon bullpen enters and how weak they are
def adjust_for_bullpen(avg_ip, bullpen_hr9):
    # Scale: If starter lasts short and bullpen is HR-prone, boost
    bullpen_factor = (6.0 - avg_ip) * (bullpen_hr9 / 1.0)
    return round(bullpen_factor, 2)
