import requests
import pandas as pd
from datetime import date

# Modified section for lineup_parser.py

def get_confirmed_lineups(force_test=False):
    if force_test:
        print("🧪 Test mode enabled: using fallback lineups")
        today = date.today().isoformat()
        return pd.DataFrame([
            {
                "batter_name": "Aaron Judge",
                "batter_id": 592450,
                "opposing_pitcher": "Clarke Schmidt",  # Make sure these are filled
                "pitcher_id": 688676,
                "pitcher_team": "NYY",
                "game_date": today,
                "game_id": generate_game_id("Aaron Judge", "Clarke Schmidt", today),
                "ballpark": "Yankee Stadium",  # Ensure ballpark is provided
                "home_team": "NYY"
            },
            # Other test data
        ])

    # Rest of the function

# Modify the merger in main.py to ensure pitcher info is preserved:
try:
    log_step("🔄 Merging batter and pitcher data...")
    # Rename columns before merging to avoid conflicts
    if "pitcher_name" in pitchers.columns:
        pitchers.rename(columns={"pitcher_name": "pitcher_name_db"}, inplace=True)
    
    merged = pd.merge(batters, pitchers, on="game_id", how="inner")
    
    # Ensure opposing_pitcher is preserved
    if "opposing_pitcher" in batters.columns and "opposing_pitcher" not in merged.columns:
        merged["opposing_pitcher"] = batters["opposing_pitcher"]
    
    # Make sure we have pitcher name info
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
