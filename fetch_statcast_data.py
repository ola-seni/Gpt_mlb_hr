from pybaseball import statcast_batter, playerid_lookup, cache
import pandas as pd
from datetime import datetime, timedelta

cache.enable()

def fetch_batter_metrics(lineups_df):
    print("📊 Fetching batter metrics...")
    metrics = []
    start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")

    for _, row in lineups_df.iterrows():
        try:
            stats = statcast_batter(start, end, player_id=row['batter_id'])
            if not stats.empty:
                stats['batter_name'] = row['batter_name']
                stats['game_id'] = row['game_id']  # Needed for merge later
                metrics.append(stats)
        except Exception as e:
            print(f"❌ Error fetching data for {row['batter_name']}: {e}")
    return pd.concat(metrics, ignore_index=True) if metrics else pd.DataFrame()

def fetch_pitcher_metrics(lineups_df):
    print("📊 Fetching pitcher metrics...")
    return pd.DataFrame([
        {
            "game_id": row["game_id"],
            "pitcher_name": row["opposing_pitcher"],
            "hr_per_9": 1.2  # Placeholder
        }
        for _, row in lineups_df.iterrows()
    ])
