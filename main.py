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
from utils import generate_game_id

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

    # DEBUG: Preview confirmed hitters
    print("📋 Confirmed lineups sample:")
    print(lineups.head(3))

    # Assign team to pitcher_team column (can adjust for away/home logic)
    lineups["pitcher_team"] = lineups["team"]  # simple default

    # Safety: remove missing IDs
    lineups = lineups.dropna(subset=["batter_id", "pitcher_id"])

    # Fetch metrics
    batters = fetch_batter_metrics(lineups)
    pitchers = fetch_pitcher_metrics(lineups)

    # Generate game_id for merging
    batters["game_id"] = batters.apply(
        lambda row: generate_game_id(row["batter_name"], row["pitcher_name"], row["game_date"]),
        axis=1
    )
    pitchers["game_id"] = pitchers.apply(
        lambda row: generate_game_id(row["pitcher_name"], row["pitcher_name"], row["game_date"]),
        axis=1
    )

    # Check for unmatched rows
    unmatched_ids = set(batters["game_id"]) - set(pitchers["game_id"])
    if unmatched_ids:
        print(f"⚠️ Unmatched game_ids in batters: {len(unmatched_ids)}")
        print(list(unmatched_ids)[:3])

    # Merge on game_id
    merged = pd.merge(batters, pitchers, on="game_id", how="inner")

    # DEBUG: Preview merged rows
    print("🧩 Sample merged matchups:")
    print(merged[["batter_name", "pitcher_name", "game_date"]].head(3))

    # Load persistent caches
    batter_cache_path = "cache/batter_pitch_iso.json"
    pitcher_cache_path = "cache/pitcher_pitch_mix.json"
    os.makedirs("cache", exist_ok=True)
    batter_cache = load_json_cache(batter_cache_path, max_age_days=30)
    pitcher_cache = load_json_cache(pitcher_cache_path, max_age_days=30)

    # Enrich with model features
    print("⚙️ Enriching features...")
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

        # Cache-aware batter ISO vs pitch types
        if batter_id in batter_cache:
            batter_iso = batter_cache[batter_id]["data"]
        else:
            batter_iso = get_batter_iso_vs_pitch_types(batter_id, start_date, end_date)
            batter_cache[batter_id] = {"data": batter_iso, "timestamp": datetime.utcnow().isoformat()}

        # Cache-aware pitcher pitch mix
        if pitcher_id in pitcher_cache:
            pitch_mix = pitcher_cache[pitcher_id]["data"]
        else:
            pitch_mix = get_pitch_mix(pitcher_id, start_date, end_date)
            pitcher_cache[pitcher_id] = {"data": pitch_mix, "timestamp": datetime.utcnow().isoformat()}

        # Compute matchup score
        pitch_score = calculate_pitch_matchup_score(pitch_mix, batter_iso)
        merged.at[idx, "pitch_matchup_score"] = pitch_score

        # Bullpen boost
        pitcher_name = row.get("pitcher_name")
        team_name = row.get("pitcher_team", "Unknown")
        avg_ip = get_starter_avg_ip(pitcher_name)
        bullpen_hr9 = get_bullpen_quality(team_name)
        merged.at[idx, "bullpen_boost"] = adjust_for_bullpen(avg_ip, bullpen_hr9)

        # Pitcher suppression
        suppression_score = calculate_pitcher_suppression_score(row)
        merged.at[idx, "pitcher_hr_suppression"] = suppression_score

    # Save updated caches
    save_json_cache(batter_cache, batter_cache_path)
    save_json_cache(pitcher_cache, pitcher_cache_path)

    # Tag top 10% suppressors
    cutoff = merged["pitcher_hr_suppression"].quantile(0.90)
    merged["suppression_tag"] = merged["pitcher_hr_suppression"] >= cutoff

    # Filter out hitters vs top suppressors
    filtered = merged[~merged["suppression_tag"]].copy()

    # Run predictions
    predictions = generate_hr_predictions(filtered)
    predictions = apply_weather_boosts(predictions)

    # DEBUG: Show top predictions
    print("🔮 Prediction sample:")
    print(predictions[["batter_name", "HR_Score", "pitch_matchup_score", "bullpen_boost"]].head(5))

    # Save results
    os.makedirs("results", exist_ok=True)
    today = date.today().isoformat()
    out_path = f"results/hr_predictions_{today}.csv"
    predictions.to_csv(out_path, index=False)
    print(f"✅ Saved predictions to {out_path}")

    # Log actual results
    update_local_csv(out_path)

    # Send Telegram alerts
    send_telegram_alerts(predictions)

if __name__ == "__main__":
    main()
