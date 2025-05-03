# main.py
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
from integrate_enhanced_metrics import integrate_enhanced_metrics  # New import
import pandas as pd
from datetime import date, datetime
import os
import sys
from projected_lineups import get_projected_lineups
import numpy as np 

load_dotenv()
FORCE_TEST_MODE = "--test" in sys.argv
# Maximum number of API retries
MAX_RETRIES = 3

def log_step(message):
    """Log a step with timestamp for better workflow debugging"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def is_test_mode():
    """Check if we're running in test mode"""
    return FORCE_TEST_MODE or os.getenv("TEST_MODE") == "1"

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

def calculate_enhanced_matchup_score(row):
    """
    Calculate an enhanced matchup score incorporating all available metrics.
    """
    # Base components (same as original)
    base_score = (
        row["HR_Score"] * 0.35 +
        row.get("pitch_matchup_score", 0) * 0.15 +
        row.get("park_factor", 1.0) * 0.15 +
        row.get("wind_boost", 0) * 0.15 +
        row.get("bullpen_boost", 0) * 0.1
    )
    
    # Advanced components if available
    advanced_score = 0.0
    
    # Exit velocity contribution
    if pd.notna(row.get("avg_exit_velo")):
        advanced_score += max(0, (row["avg_exit_velo"] - 85) / 100) * 0.02
    
    # xSLG contribution
    if pd.notna(row.get("xSLG")):
        advanced_score += row["xSLG"] * 0.03
    
    # Recent HR contribution
    if pd.notna(row.get("hrs_last_10_games")):
        advanced_score += min(row["hrs_last_10_games"] * 0.01, 0.03)
    
    # Platoon advantage
    if pd.notna(row.get("platoon_advantage")):
        advanced_score += (row["platoon_advantage"] - 0.5) * 0.05
    
    # Hard Hit % allowed by pitcher
    if pd.notna(row.get("hard_hit_pct_allowed")):
        advanced_score += row["hard_hit_pct_allowed"] * 0.02
    
    return base_score + advanced_score

def main():
    log_step("🛠️ Gpt_mlb_hr ENHANCED: Starting home run prediction...")
    
    # Print environment configuration
    test_mode = is_test_mode()
    log_step(f"🧪 Test mode: {'ENABLED' if test_mode else 'DISABLED'}")
    log_step(f"📅 Current date: {date.today().isoformat()}")
    
    # Create required directories
    os.makedirs("results", exist_ok=True)
    os.makedirs("cache", exist_ok=True)

    lineups = get_confirmed_lineups(force_test=test_mode)
    if lineups.empty:
        log_step("📋 Confirmed lineups not available — using projected lineups instead.")
        lineups = safe_execution(get_projected_lineups, pd.DataFrame(), "Failed to get projected lineups")
    
    if lineups.empty:
        log_step("❌ No lineups available. Exiting.")
        return
        
    print("📋 Confirmed lineups sample:")
    print(lineups.head(3))

    lineups = lineups.dropna(subset=["batter_id", "pitcher_id"])
    batters = fetch_batter_metrics(lineups)
    pitchers = fetch_pitcher_metrics(lineups)
    if pitchers.empty or batters.empty:
        log_step("❌ No valid player data found — exiting.")
        return

    try:
        log_step("🔄 Merging batter and pitcher data...")
        # Rename columns before merging to avoid conflicts
        if "pitcher_name" in pitchers.columns:
            pitchers.rename(columns={"pitcher_name": "pitcher_name_db"}, inplace=True)
    
        merged = pd.merge(batters, pitchers, on="game_id", how="inner")
    
        # Ensure opposing_pitcher is preserved
        if "opposing_pitcher" in batters.columns and "opposing_pitcher" not in merged.columns:
            merged["opposing_pitcher"] = batters["opposing_pitcher"]
    
        # Make sure we have pitcher name info for display
        merged["pitcher_display_name"] = merged.apply(
            lambda row: row.get("pitcher_name_db", row.get("opposing_pitcher", "Unknown")),
            axis=1
        )
    
        log_step("🧩 Sample merged matchups:")
        if not merged.empty:
            print("✅ Columns in merged:", merged.columns.tolist())
            print(merged.head(3))
        else:
            log_step("❌ No matchups merged — check game_id alignment.")
            return
    except Exception as e:
        log_step(f"❌ Error merging data: {str(e)}")
        return

    # Add enhanced batter metrics 
    merged = enhance_batter_data(merged)

    log_step("🗃️ Loading cache data...")
    batter_cache_path = "cache/batter_pitch_iso.json"
    pitcher_cache_path = "cache/pitcher_pitch_mix.json"
    os.makedirs("cache", exist_ok=True)
    batter_cache = load_json_cache(batter_cache_path, max_age_days=30)
    pitcher_cache = load_json_cache(pitcher_cache_path, max_age_days=30)

    log_step("⚙️ Enriching features...")
    merged["pitch_matchup_score"] = 0.15
    merged["bullpen_boost"] = 0.0
    merged["pitcher_hr_suppression"] = 0.0
    merged["suppression_tag"] = False

    try:
        for idx, row in merged.iterrows():
            try:
                batter_id = str(row.get("batter_id"))
                pitcher_id = str(row.get("pitcher_id"))
                game_date = row.get("game_date_x", row.get("game_date"))

                if not all([batter_id, pitcher_id, game_date]):
                    log_step(f"⚠️ Missing required data for row {idx}")
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

                pitcher_name = row.get("pitcher_name_x", row.get("opposing_pitcher"))
                team_name = row.get("pitcher_team", "Unknown")
                avg_ip = get_starter_avg_ip(pitcher_name)
                bullpen_hr9 = get_bullpen_quality(team_name)
                merged.at[idx, "bullpen_boost"] = adjust_for_bullpen(avg_ip, bullpen_hr9)

                suppression_score = calculate_pitcher_suppression_score(row)
                merged.at[idx, "pitcher_hr_suppression"] = suppression_score
            except Exception as e:
                log_step(f"⚠️ Error processing row {idx}: {str(e)}")
                # Continue with next row instead of breaking completely
                continue

        log_step("💾 Saving cache data...")
        save_json_cache(batter_cache, batter_cache_path)
        save_json_cache(pitcher_cache, pitcher_cache_path)

        # Calculate suppression tag cutoff
        if "pitcher_hr_suppression" in merged.columns and not merged.empty:
            cutoff = merged["pitcher_hr_suppression"].quantile(0.90)
            merged["suppression_tag"] = merged["pitcher_hr_suppression"] >= cutoff
    except Exception as e:
        log_step(f"❌ Error enriching features: {str(e)}")
        # Continue with what we have

    filtered = merged.copy()

    log_step("🔮 Generating predictions...")
    # Use enhanced prediction function instead of original
    predictions = safe_execution(
        lambda: generate_enhanced_hr_predictions(filtered),
        pd.DataFrame(),
        "Failed to generate predictions"
    )
    
    if predictions.empty:
        log_step("❌ No predictions generated — exiting.")
        return

    # NEW SECTION: Add enhanced metrics integration
    log_step("🔍 Enhancing predictions with additional metrics...")
    enhanced_predictions = safe_execution(
        lambda: integrate_enhanced_metrics(predictions),
        predictions,
        "Failed to integrate enhanced metrics"
    )
    
    # If successful enhancement, use the enhanced score
    if 'enhanced_HR_Score' in enhanced_predictions.columns:
        enhanced_predictions['original_HR_Score'] = enhanced_predictions['HR_Score']
        enhanced_predictions['HR_Score'] = enhanced_predictions['enhanced_HR_Score']
        log_step("✅ Successfully applied enhanced metrics")
        
        # Use enhanced predictions going forward
        predictions = enhanced_predictions
    else:
        log_step("⚠️ Enhanced metrics not available, using original predictions")
    # END NEW SECTION

    # Use enhanced weather function instead of original
    log_step("🌤️ Applying weather boosts...")
    predictions = safe_execution(
        lambda: apply_enhanced_weather_boosts(predictions),
        predictions,
        "Failed to apply weather boosts"
    )

    try:
        # Enhanced scoring formula with more factors
        log_step("📊 Calculating final matchup scores...")
        
        # MODIFIED: Use enhanced matchup score calculation when available
        predictions["matchup_score"] = predictions.apply(
            lambda row: calculate_enhanced_matchup_score(row)
            if any(pd.notna(row.get(col)) for col in ['avg_exit_velo', 'xSLG', 'platoon_advantage', 'hard_hit_pct_allowed'])
            else (
                row["HR_Score"] * 0.4 +
                row.get("pitch_matchup_score", 0) * 0.2 +
                row.get("park_factor", 1.0) * 0.15 +
                row.get("wind_boost", 0) * 0.15 +
                row.get("bullpen_boost", 0) * 0.1
            ),
            axis=1
        )

        log_step("🔮 Prediction sample:")
        print(predictions[["batter_name", "HR_Score", "matchup_score", "pitch_matchup_score", "bullpen_boost", "park_factor", "wind_boost"]].head(5))
    except Exception as e:
        log_step(f"⚠️ Error calculating matchup scores: {str(e)}")
        # Continue with basic HR_Score if matchup_score calculation fails
        predictions["matchup_score"] = predictions["HR_Score"]

    os.makedirs("results", exist_ok=True)
    today = date.today().isoformat()
    out_path = f"results/hr_predictions_{today}.csv"
    
    try:
        predictions.to_csv(out_path, index=False)
        log_step(f"✅ Saved predictions to {out_path}")
    except Exception as e:
        log_step(f"❌ Error saving predictions: {str(e)}")
        
    # Only update results in non-test mode
    if not is_test_mode():
        log_step("📊 Updating local CSV...")
        safe_execution(
            lambda: update_local_csv(out_path),
            None,
            "Failed to update local CSV"
        )
    else:
        log_step("🧪 Skipping update_local_csv in test mode")
    
    try:
        # ✅ Assign HR prediction tiers for Telegram alerts
        log_step("🏷️ Assigning prediction tiers...")
        def assign_tag(score):
            if score >= 0.25:
                return "Lock 🔒"
            elif score >= 0.15:
                return "Sleeper 🌙"
            else:
                return "Risky ⚠️"

        # Use matchup_score instead of HR_Score for tagging
        predictions["tag"] = predictions["matchup_score"].apply(assign_tag)
        
        # Only send alerts in non-test mode
        if not is_test_mode():
            log_step("📱 Sending Telegram alerts...")
            safe_execution(
                lambda: send_telegram_alerts(predictions),
                None,
                "Failed to send Telegram alerts"
            )
        else:
            log_step("🧪 Skipping Telegram alerts in test mode")
            
    except Exception as e:
        log_step(f"❌ Error in final processing steps: {str(e)}")
        
    log_step("✅ Process completed successfully")
    return predictions

if __name__ == "__main__":
    try:
        main()
        log_step("✅ Program completed successfully")
    except Exception as e:
        log_step(f"❌ Program error: {e}")
        # Optional: send error notification
        if "BOT_TOKEN" in os.environ and "CHAT_ID" in os.environ:
            from telegram_alerts import send_telegram_alerts
            error_df = pd.DataFrame([{
                "batter_name": "ERROR",
                "opposing_pitcher": f"Program error: {str(e)}",
                "HR_Score": 0.0,
                "tag": "Error"
            }])
            try:
                send_telegram_alerts(error_df)
            except Exception as alert_error:
                log_step(f"❌ Failed to send error alert: {alert_error}")
