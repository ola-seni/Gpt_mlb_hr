from fetch_statcast_data import fetch_batter_metrics, fetch_pitcher_metrics
from predictor import generate_enhanced_hr_predictions  # Use enhanced prediction function
from lineup_parser import get_confirmed_lineups
from weather import apply_enhanced_weather_boosts  # Use enhanced weather function
from telegram_alerts import send_telegram_alerts
from update_hr_results import update_local_csv
from get_pitch_mix import get_pitch_mix
from get_batter_iso_vs_pitch import get_batter_iso_vs_pitch_types
from calculate_pitch_matchup_score import calculate_pitch_matchup_score
from bullpen_tracker import get_starter_avg_ip, get_bullpen_quality, adjust_for_bullpen
from pitcher_suppression import calculate_pitcher_suppression_score
from cache_utils import load_json_cache, save_json_cache
from utils import generate_game_id
from dotenv import load_dotenv
import pandas as pd
from datetime import date, datetime
import os
import sys
from projected_lineups import get_projected_lineups
import numpy as np 

load_dotenv()
FORCE_TEST_MODE = "--test" in sys.argv

def safe_execution(func, default_return=None, error_msg="Function failed"):
    """Safely execute a function with error handling."""
    try:
        return func()
    except Exception as e:
        print(f"❌ {error_msg}: {e}")
        return default_return

def enhance_batter_data(batters_df):
    """Add enhanced batting metrics to the DataFrame"""
    print("🧮 Adding enhanced batting metrics...")
    
    try:
        # Add recent form indicators (dummy data for demo - in production, 
        # you'd calculate these from recent statcast data)
        if not batters_df.empty:
            # Add "last 7 days" metrics
            batters_df['last_7_iso'] = batters_df['ISO'] * (0.8 + (0.4 * np.random.random(len(batters_df))))
            batters_df['last_7_barrel'] = batters_df['barrel_rate_50'] * (0.7 + (0.6 * np.random.random(len(batters_df))))
            
            # Add recent HR rate (simplified approach)
            batters_df['recent_hr_rate'] = batters_df['barrel_rate_50'] * 0.7 * (0.8 + (0.4 * np.random.random(len(batters_df))))
            
            # Add stand orientation (L/R) - in production, get this from player data
            # Roughly 65% of batters are right-handed
            batters_df['batter_stands'] = np.random.choice(['R', 'L'], size=len(batters_df), p=[0.65, 0.35])
            
        print(f"✅ Enhanced {len(batters_df)} batter records")
    except Exception as e:
        print(f"❌ Error enhancing batter data: {e}")
    
    return batters_df

def main():
    print("🛠️ Gpt_mlb_hr ENHANCED: Starting home run prediction...")

    lineups = get_confirmed_lineups(force_test=FORCE_TEST_MODE)
    if lineups.empty:
        print("📋 Confirmed lineups not available — using projected lineups instead.")
        lineups = get_projected_lineups()

    print("📋 Confirmed lineups sample:")
    print(lineups.head(3))

    lineups = lineups.dropna(subset=["batter_id", "pitcher_id"])
    batters = fetch_batter_metrics(lineups)
    pitchers = fetch_pitcher_metrics(lineups)
    if pitchers.empty or batters.empty:
        print("⚠️ No valid player data found — skipping predictions.")
        return

    merged = pd.merge(batters, pitchers, on="game_id", how="inner")

    print("🧩 Sample merged matchups:")
    if not merged.empty:
        print("✅ Columns in merged:", merged.columns.tolist())
        print(merged.head(3))
    else:
        print("⚠️ No matchups merged — check game_id alignment.")
        return

    # Add enhanced batter metrics 
    merged = enhance_batter_data(merged)

    batter_cache_path = "cache/batter_pitch_iso.json"
    pitcher_cache_path = "cache/pitcher_pitch_mix.json"
    os.makedirs("cache", exist_ok=True)
    batter_cache = load_json_cache(batter_cache_path, max_age_days=30)
    pitcher_cache = load_json_cache(pitcher_cache_path, max_age_days=30)

    print("⚙️ Enriching features...")
    merged["pitch_matchup_score"] = 0.15
    merged["bullpen_boost"] = 0.0
    merged["pitcher_hr_suppression"] = 0.0
    merged["suppression_tag"] = False

    for idx, row in merged.iterrows():
        batter_id = str(row.get("batter_id"))
        pitcher_id = str(row.get("pitcher_id"))
        game_date = row.get("game_date_x", row.get("game_date"))

        if not all([batter_id, pitcher_id, game_date]):
            continue

        start_date = end_date = game_date

        if batter_id in batter_cache:
            batter_iso = batter_cache[batter_id]["data"]
        else:
            batter_iso = get_batter_iso_vs_pitch_types(batter_id, start_date, end_date)
            batter_cache[batter_id] = {"data": batter_iso, "timestamp": datetime.utcnow().isoformat()}

        if pitcher_id in pitcher_cache:
            pitch_mix = pitcher_cache[pitcher_id]["data"]
        else:
            pitch_mix = get_pitch_mix(pitcher_id, start_date, end_date)
            pitcher_cache[pitcher_id] = {"data": pitch_mix, "timestamp": datetime.utcnow().isoformat()}

        pitch_score = calculate_pitch_matchup_score(pitch_mix, batter_iso)
        merged.at[idx, "pitch_matchup_score"] = pitch_score

        pitcher_name = row.get("pitcher_name_x")
        team_name = row.get("pitcher_team", "Unknown")
        avg_ip = get_starter_avg_ip(pitcher_name)
        bullpen_hr9 = get_bullpen_quality(team_name)
        merged.at[idx, "bullpen_boost"] = adjust_for_bullpen(avg_ip, bullpen_hr9)

        suppression_score = calculate_pitcher_suppression_score(row)
        merged.at[idx, "pitcher_hr_suppression"] = suppression_score

    save_json_cache(batter_cache, batter_cache_path)
    save_json_cache(pitcher_cache, pitcher_cache_path)

    cutoff = merged["pitcher_hr_suppression"].quantile(0.90)
    merged["suppression_tag"] = merged["pitcher_hr_suppression"] >= cutoff

    filtered = merged.copy()

    # Use enhanced prediction function instead of original
    predictions = generate_enhanced_hr_predictions(filtered)
    if predictions.empty:
        print("⚠️ No predictions after filtering — skipping save, update, and alert.")
        return

    # Use enhanced weather function instead of original
    predictions = apply_enhanced_weather_boosts(predictions)

    # Enhanced scoring formula with more factors
    predictions["matchup_score"] = (
        predictions["HR_Score"] * 0.4 +
        predictions.get("pitch_matchup_score", 0) * 0.2 +
        predictions.get("park_factor", 0) * 0.15 +
        predictions.get("wind_boost", 0) * 0.15 +
        predictions.get("bullpen_boost", 0) * 0.1
    )

    print("🔮 Prediction sample:")
    print(predictions[["batter_name", "HR_Score", "matchup_score", "pitch_matchup_score", "bullpen_boost", "park_factor", "wind_boost"]].head(5))

    os.makedirs("results", exist_ok=True)
    today = date.today().isoformat()
    out_path = f"results/hr_predictions_{today}.csv"
    predictions.to_csv(out_path, index=False)
    print(f"✅ Saved predictions to {out_path}")

    update_local_csv(out_path)
    
    # ✅ Assign HR prediction tiers for Telegram alerts
    def assign_tag(score):
        if score >= 0.25:
            return "Lock 🔒"
        elif score >= 0.15:
            return "Sleeper 🌙"
        else:
            return "Risky ⚠️"

    # Use matchup_score instead of HR_Score for tagging
    predictions["tag"] = predictions["matchup_score"].apply(assign_tag)

    send_telegram_alerts(predictions)

if __name__ == "__main__":
    try:
        main()
        print("✅ Program completed successfully")
    except Exception as e:
        print(f"❌ Program error: {e}")
        # Optional: send error notification
        if "BOT_TOKEN" in os.environ and "CHAT_ID" in os.environ:
            from telegram_alerts import send_telegram_alerts
            error_df = pd.DataFrame([{
                "batter_name": "ERROR",
                "opposing_pitcher": f"Program error: {str(e)}",
                "HR_Score": 0.0,
                "tag": "Error"
            }])
            send_telegram_alerts(error_df)
