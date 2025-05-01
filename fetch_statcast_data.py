from pybaseball import statcast_batter, cache
import pandas as pd
from datetime import datetime, timedelta

cache.enable()

def fetch_batter_metrics(lineups_df):
    print("📊 Fetching batter metrics...")
    metrics = []
    start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")

    seen_ids = set()
    for _, row in lineups_df.iterrows():
        batter_id = row['batter_id']
        if batter_id in seen_ids:
            continue
        try:
            stats = statcast_batter(start, end, player_id=batter_id)
            if not stats.empty:
                stats['batter_name'] = row['batter_name']
                stats['game_id'] = row['game_id']
                stats['ISO'] = (stats['slg'] - stats['avg']).mean()
                stats['barrel_rate_50'] = (
                    stats.tail(50)['launch_speed'].gt(98) &
                    stats.tail(50)['launch_angle'].between(26, 30)
                ).mean()
                metrics.append(stats)
                seen_ids.add(batter_id)
        except Exception as e:
            print(f"❌ Error fetching data for {row['batter_name']}: {e}")
    return pd.concat(metrics, ignore_index=True) if metrics else pd.DataFrame()

def fetch_pitcher_metrics(lineups_df):
    print("📊 Fetching pitcher metrics...")
    return pd.DataFrame([
        {
            "game_id": row["game_id"],
            "pitcher_name": row["opposing_pitcher"],
            "hr_per_9": 1.2  # Placeholder stat
        }
        for _, row in lineups_df.iterrows()
    ])
