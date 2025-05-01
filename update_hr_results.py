from pybaseball import statcast
from datetime import date
import pandas as pd
import os

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

        # 📊 Log accuracy summary
        total_preds = len(df)
        hit_count = df['Hit_HR'].sum()
        hit_rate = round(hit_count / total_preds, 3) if total_preds else 0
        log_row = pd.DataFrame([{
            "date": today,
            "total_preds": total_preds,
            "hit_count": hit_count,
            "hit_rate": hit_rate
        }])

        os.makedirs("results", exist_ok=True)
        log_file = "results/accuracy_log.csv"
        if not os.path.exists(log_file):
            log_row.to_csv(log_file, index=False)
        else:
            log_row.to_csv(log_file, mode='a', index=False, header=False)

        print("📈 Logged accuracy summary.")
    except Exception as e:
        print(f"❌ Error updating HR results: {e}")
