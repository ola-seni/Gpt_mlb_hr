# get_batter_iso_vs_pitch.py

from pybaseball import statcast_batter
import pandas as pd

def get_batter_iso_vs_pitch_types(batter_id, start_date, end_date):
    try:
        df = statcast_batter(start_date, end_date, batter_id)
        if df.empty:
            return {}

        df = df[df['events'].notnull()]
        df['single'] = df['events'] == 'single'
        df['double'] = df['events'] == 'double'
        df['triple'] = df['events'] == 'triple'
        df['home_run'] = df['events'] == 'home_run'

        # Basic SLG calc per pitch
        df['total_bases'] = (df['single'] * 1 + df['double'] * 2 +
                             df['triple'] * 3 + df['home_run'] * 4)
        pitch_groups = df.groupby('pitch_type').agg({
            'total_bases': 'sum',
            'events': 'count'
        }).rename(columns={'events': 'ab'})

        pitch_groups['iso'] = pitch_groups['total_bases'] / pitch_groups['ab']
        pitch_type_map = {
            'FF': '4-Seam Fastball', 'SL': 'Slider', 'CH': 'Changeup',
            'CU': 'Curveball', 'SI': 'Sinker', 'FC': 'Cutter',
            'FS': 'Splitter', 'KN': 'Knuckleball', 'FT': '2-Seam Fastball'
        }
        iso_by_pitch = {
            pitch_type_map.get(k, k): round(v, 3)
            for k, v in pitch_groups['iso'].to_dict().items()
        }
        return iso_by_pitch

    except Exception as e:
        print(f"Error fetching batter ISO: {e}")
        return {}
