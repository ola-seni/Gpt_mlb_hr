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

        # Add actual outcome
        df['Hit_HR'] = df['batter_name'].apply(lambda name: 1 if name in hr_hitters else 0)

        # Add prediction type
        def get_type(score):
            if score >= 0.40:
                return "Lock"
            elif score >= 0.25:
                return "Sleeper"
            else:
                return "Risky"

        df["Prediction_Type"] = df["HR_Score"].apply(get_type)

        # Save updated prediction file
        df.to_csv(prediction_file, index=False)
        print("✅ Updated with HR results.")

        # 📊 Log accuracy summary (aggregate per type)
        grouped = df.groupby("Prediction_Type").agg(
            total_preds=("batter_name", "count"),
            hit_count=("Hit_HR", "sum")
        ).reset_index()
        grouped["date"] = today
        grouped["hit_rate"] = grouped["hit_count"] / grouped["total_preds"]

        log_file = "results/accuracy_log.csv"
        os.makedirs("results", exist_ok=True)

        if os.path.exists(log_file):
            existing = pd.read_csv(log_file)
            combined = pd.concat([existing, grouped], ignore_index=True)
        else:
            combined = grouped

        combined.to_csv(log_file, index=False)
        print("📈 Logged accuracy summary.")

    except Exception as e:
        print(f"❌ Error updating HR results: {e}")
