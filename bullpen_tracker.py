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
        row = df[df['Team'] == team_name]
        if row.empty:
            return 0.0
        hr9 = row.iloc[0]['HR/9']
        return round(hr9, 2)
    except Exception as e:
        print(f"⚠️ Bullpen data error for {team_name}: {e}")
        return 0.0

# Adjust HR score based on how soon bullpen enters and how weak they are
def adjust_for_bullpen(avg_ip, bullpen_hr9):
    # Scale: If starter lasts short and bullpen is HR-prone, boost
    bullpen_factor = (6.0 - avg_ip) * (bullpen_hr9 / 1.0)
    return round(bullpen_factor, 2)
