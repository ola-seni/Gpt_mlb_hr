from fetch_statcast_data import fetch_batter_metrics, fetch_pitcher_metrics
from predictor import generate_hr_predictions
from lineup_parser import get_confirmed_lineups
from weather import apply_weather_boosts
from telegram_alerts import send_telegram_alerts
import pandas as pd
from datetime import date
import os

def main():
    print("🛠️ Gpt_mlb_hr: Starting home run prediction...")

    # Get confirmed lineups
    lineups = get_confirmed_lineups()
    if lineups.empty:
        print("⚠️ No confirmed lineups found.")
        return

    # Fetch metrics
    batters = fetch_batter_metrics(lineups)
    pitchers = fetch_pitcher_metrics(lineups)

    # Merge and predict
    merged = pd.merge(batters, pitchers, on='game_id', how='inner')
    predictions = generate_hr_predictions(merged)

    # Apply weather boosts
    predictions = apply_weather_boosts(predictions)

    # ✅ Ensure folder exists
    os.makedirs("results", exist_ok=True)

    # Save CSV
    today = date.today().isoformat()
    predictions.to_csv(f"results/hr_predictions_{today}.csv", index=False)
    print(f"✅ Saved predictions to results/hr_predictions_{today}.csv")

    # Send Telegram alerts
    send_telegram_alerts(predictions)

if __name__ == "__main__":
    main()
