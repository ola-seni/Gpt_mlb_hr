# get_pitch_mix.py

from pybaseball import statcast_pitcher
import pandas as pd

def get_pitch_mix(pitcher_id, start_date, end_date):
    try:
        df = statcast_pitcher(start_date, end_date, pitcher_id)
        if df.empty:
            return {}

        pitch_counts = df['pitch_type'].value_counts(normalize=True).to_dict()

        # Optional: Map codes to readable pitch names
        pitch_type_map = {
            'FF': '4-Seam Fastball', 'SL': 'Slider', 'CH': 'Changeup',
            'CU': 'Curveball', 'SI': 'Sinker', 'FC': 'Cutter',
            'FS': 'Splitter', 'KN': 'Knuckleball', 'FT': '2-Seam Fastball'
        }
        readable_pitch_mix = {
            pitch_type_map.get(k, k): round(v, 3)
            for k, v in pitch_counts.items()
        }
        return readable_pitch_mix

    except Exception as e:
        print(f"Error fetching pitch mix: {e}")
        return {}
