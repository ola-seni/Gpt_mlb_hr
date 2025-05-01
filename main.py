from fetch_statcast_data import fetch_batter_metrics, fetch_pitcher_metrics
from predictor import generate_hr_predictions
from lineup_parser import get_confirmed_lineups
from weather import apply_weather_boosts
from telegram_alerts import send_telegram_alerts
from update_hr_results import update_local_csv

from get_pitch_mix import get_pitch_mix
from get_batter_iso_vs_pitch import get_batter_iso_vs_pitch_types
from calculate_pitch_matchup_score import calculate_pitch_matchup_score
from bullpen_tracker import get_starter_avg_ip, get_bullpen_quality, adjust_for_bullpen
from pitcher_suppression import calculate_pitcher_suppression_score
from cache_utils import load_json_cache, save_json_cache

import pandas as pd
from datetime import date, datetime
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

    # Merge batter & pitcher metrics
    merged = pd.merge(batters, pitchers, on='game_id', how='inner')

    # Load persistent caches with TTL (30 days)
    batter_cache_path = "cache/batter_pitch_iso.json"
    pitcher_cache_path = "cache/pitcher_pitch_mix.json"
    os.makedirs("cache", exist_ok=True)

    batter_cache = load_json_cache(batter_cache_path, max_age_days=30)
    pitcher_cache = load_json_cache(pitcher_cache_path, max_age_days=30)

    # Initialize new features
    print("⚙️ Calculating matchup and suppression metrics...")
    merged["pitch_matchup_score"] = 0.15
    merged["bullpen_boost"] = 0.0
    merged["pitcher_hr_suppression"] = 0.0
    merged["suppression_tag"] = False

    for idx, row in merged.iterrows():
        batter_id = str(row.get("batter_id"))
        pitcher_id = str(row.get("pitcher_id"))
        game_date = row.get("game_date")

        if not all([batter_id, pitcher_id, game_date]):
            continue

        start_date = end_date = game_date

        # --- Get batter ISO vs pitch types ---
        if batter_id in batter_cache:
            batter_iso = batter_cache[batter_id]["data"]
        else:
            batter_iso = get_batter_iso_vs_pitch_types(batter_id, start_date, end_date)
            batter_cache[batter_id] = {
                "data": batter_iso,
                "timestamp": datetime.utcnow().isoformat()
            }

        # --- Get pitcher pitch mix ---
        if pitcher_id in pitcher_cache:
            pitch_mix = pitcher_cache[pitcher_id]["data"]
        else:
            pitch_mix = get_pitch_mix(pitcher_id, start_date, end_date)
            pitcher_cache[pitcher_id] = {
                "data": pitch_mix,
                "timestamp": datetime.utcnow().isoformat()
            }

        # --- Compute pitch matchup score ---
        pitch_score = calculate_pitch_matchup_score(pitch_mix, batter_iso)
        merged.at[idx, "pitch_matchup_score"] = pitch_score

        # --- Compute bullpen boost ---
        pitcher_name = row.get("pitcher_name")
        team_name = row.get("pitcher_team")
        if pitcher_name and team_name:
            avg_ip = get_starter_avg_ip(pitcher_name)
            bullpen_hr9 = get_bullpen_quality(team_name)
            bullpen_boost = adjust_for_bullpen(avg_ip, bullpen_hr9)
            merged.at[idx, "bullpen_boost"] = bullpen_boost

        # --- Compute pitcher HR suppression score ---
        suppression_score = calculate_pitcher_suppression_score(row)
        merged.at[idx, "pitcher_hr_suppression"] = suppression_score

    # Save updated cache
    save_json_cache(batter_cache, batter_cache_path)
    save_json_cache(pitcher_cache, pitcher_cache_path)

    # Identify top 10% suppressors and tag them
    suppression_cutoff = merged["pitcher_hr_suppression"].quantile(0.90)
    merged["suppression_tag"] = merged["pitcher_hr_suppression"] >= suppression_cutoff

    # Filter out batters facing elite HR-suppressing pitchers
    filtered = merged[~merged["suppression_tag"]].copy()

    # Run predictions
    predictions = generate_hr_predictions(filtered)

    # Apply weather boosts
    predictions = apply_weather_boosts(predictions)

    # Save predictions
    os.makedirs("results", exist_ok=True)
    today = date.today().isoformat()
    filepath = f"results/hr_predictions_{today}.csv"
    predictions.to_csv(filepath, index=False)
    print(f"✅ Saved predictions to {filepath}")

    # Update with actual HR results
    update_local_csv(filepath)

    # Send Telegram alerts
    send_telegram_alerts(predictions)

if __name__ == "__main__":
    main()
