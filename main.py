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
from dotenv import load_dotenv
from projected_lineups import get_projected_lineups
from get_projected_lineups import get_projected_lineups
from get_projected_lineups import get_projected_lineups




import pandas as pd
from datetime import date, datetime
import os
import sys

load_dotenv()
FORCE_TEST_MODE = "--test" in sys.argv

def get_projected_lineups():
    print("📋 Using projected lineups (fallback mode)")
    from datetime import date
    return pd.DataFrame([
        {
            "batter_name": "Aaron Judge",
            "batter_id": 592450,
            "opposing_pitcher": "Clarke Schmidt",
            "pitcher_id": 668676,
            "pitcher_team": "NYY",
            "game_date": date.today().isoformat(),
            "game_id": "aaron_judge__vs__clarke_schmidt__" + date.today().isoformat()
        },
        {
            "batter_name": "Juan Soto",
            "batter_id": 665742,
            "opposing_pitcher": "Max Scherzer",
            "pitcher_id": 453286,
            "pitcher_team": "TEX",
            "game_date": date.today().isoformat(),
            "game_id": "juan_soto__vs__max_scherzer__" + date.today().isoformat()
        }
    ])

def main():
    print("🛠️ Gpt_mlb_hr: Starting home run prediction...")

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

    predictions = generate_hr_predictions(filtered)
    if predictions.empty:
        print("⚠️ No predictions after filtering — skipping save, update, and alert.")
        return

    predictions = apply_weather_boosts(predictions)

    predictions["matchup_score"] = (
        predictions["HR_Score"] * 0.5 +
        predictions.get("pitch_matchup_score", 0) * 0.2 +
        predictions.get("park_factor", 0) * 0.1 +
        predictions.get("wind_boost", 0) * 0.1 +
        predictions.get("bullpen_boost", 0) * 0.1
    )

    print("🔮 Prediction sample:")
    print(predictions[["batter_name", "HR_Score", "matchup_score", "pitch_matchup_score", "bullpen_boost"]].head(5))

    os.makedirs("results", exist_ok=True)
    today = date.today().isoformat()
    out_path = f"results/hr_predictions_{today}.csv"
    predictions.to_csv(out_path, index=False)
    print(f"✅ Saved predictions to {out_path}")

    update_local_csv(out_path)
    
    # ✅ Assign HR prediction tiers for Telegram alerts
    def assign_tag(score):
        if score >= 0.25:
            return "Lock"
        elif score >= 0.15:
            return "Sleeper"
        else:
            return "Risky"

    predictions["tag"] = predictions["HR_Score"].apply(assign_tag)

    send_telegram_alerts(predictions)

if __name__ == "__main__":
    main()
