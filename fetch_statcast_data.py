from pybaseball import statcast_batter, playerid_lookup, cache
import pandas as pd
from datetime import datetime, timedelta

cache.enable()

def fetch_batter_metrics(lineups_df):
    print("📊 Fetching batter metrics...")
    metrics = []
    start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")

    seen_ids = set()  # To avoid duplicates

    for _, row in lineups_df.iterrows():
        batter_id = row['batter_id']
        if batter_id in seen_ids:
            continue  # skip duplicates

        try:
            stats = statcast_batter(start, end, player_id=batter_id)
            if not stats.empty:
                stats['batter_name'] = row['batter_name']
                stats['game_id'] = row['game_id']
                metrics.append(stats)
                seen_ids.add(batter_id)
        except Exception as e:
            print(f"❌ Error fetching data for {row['batter_name']}: {e}")
    return pd.concat(metrics, ignore_index=True) if metrics else pd.DataFrame()
