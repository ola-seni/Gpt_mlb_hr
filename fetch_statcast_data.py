from pybaseball import statcast_batter, playerid_lookup, cache
import pandas as pd
from datetime import datetime, timedelta

cache.enable()

def fetch_batter_metrics(lineups_df):
    print("📊 Fetching batter metrics...")
    metrics = []
    for _, row in lineups_df.iterrows():
        try:
            stats = statcast_batter(row['batter_id'], start_dt=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
            if not stats.empty:
                stats['batter_name'] = row['batter_name']
                metrics.append(stats)
        except Exception as e:
            print(f"❌ Error fetching data for {row['batter_name']}: {e}")
    return pd.concat(metrics) if metrics else pd.DataFrame()

def fetch_pitcher_metrics(lineups_df):
    print("📊 Fetching pitcher metrics...")
    # Placeholder logic
    return pd.DataFrame([
        {
            "game_id": row["game_id"],
            "pitcher_name": row["opposing_pitcher"],
            "hr_per_9": 1.2  # Mock stat
        }
        for _, row in lineups_df.iterrows()
    ])
