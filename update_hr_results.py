from pybaseball import statcast
from datetime import date
import pandas as pd

def update_local_csv(prediction_file):
    today = date.today().isoformat()
    print(f"🔎 Checking HR results for {today}")

    try:
        df = pd.read_csv(prediction_file)
        actual_stats = statcast(today, today)
        hr_hitters = actual_stats[actual_stats['events'] == 'home_run']['player_name'].unique()
        df['Hit_HR'] = df['batter_name'].apply(lambda name: 1 if name in hr_hitters else 0)
        df.to_csv(prediction_file, index=False)
        print("✅ Updated with HR results.")
    except Exception as e:
        print(f"❌ Error updating HR results: {e}")
