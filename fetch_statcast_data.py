from pybaseball import statcast_batter, statcast_pitcher, cache
import pandas as pd
from datetime import datetime

cache.enable()

def fetch_batter_metrics(lineups_df):
    print("📊 Fetching batter metrics...")
    metrics = []

    # Define date range
    if datetime.now().year >= 2025:
        start = "2025-03-01"
        end = datetime.now().strftime("%Y-%m-%d")
    else:
        start = "2023-04-01"
        end = "2023-10-01"

    seen_ids = set()
    for _, row in lineups_df.iterrows():
        batter_id = row['batter_id']
        if batter_id in seen_ids:
            continue
        try:
            stats = statcast_batter(start, end, batter_id)
            if stats.empty:
                continue

            batted = stats[stats['events'].notna()]
            iso = (
                batted['events'].eq('double').sum() * 2 +
                batted['events'].eq('triple').sum() * 3 +
                batted['events'].eq('home_run').sum() * 4
            ) / max(1, batted.shape[0])

            last50 = batted.tail(50)
            barrels = (
                last50['launch_speed'].gt(98) &
                last50['launch_angle'].between(26, 30)
            ).mean()

            metrics.append({
                "batter_name": row["batter_name"],
                "batter_id": batter_id,
                "pitcher_name": row["opposing_pitcher"],
                "game_date": row["game_date"],
                "game_id": row["game_id"],
                "ISO": round(iso, 3),
                "barrel_rate_50": round(barrels, 3),
            })
            seen_ids.add(batter_id)

        except Exception as e:
            print(f"❌ Error fetching data for {row['batter_name']}: {e}")
    return pd.DataFrame(metrics)


def fetch_pitcher_metrics(lineups_df):
    print("📊 Fetching pitcher metrics...")
    metrics = []

    # Define date range
    if datetime.now().year >= 2025:
        start = "2025-03-01"
        end = datetime.now().strftime("%Y-%m-%d")
    else:
        start = "2023-04-01"
        end = "2023-10-01"

    seen_ids = set()
    for _, row in lineups_df.iterrows():
        pitcher_id = row['pitcher_id']
        if pitcher_id in seen_ids:
            continue
        try:
            stats = statcast_pitcher(start, end, pitcher_id)
            if stats.empty:
                continue

            outs = stats['outs_when_up'].count()
            ip = outs / 3.0
            hr = stats['events'].eq('home_run').sum()
            hr_per_9 = (hr / ip) * 9 if ip > 0 else 0.0

            metrics.append({
                "pitcher_name": row["opposing_pitcher"],
                "pitcher_id": pitcher_id,
                "game_date": row["game_date"],
                "game_id": row["game_id"],
                "hr_per_9": round(hr_per_9, 3),
            })
            seen_ids.add(pitcher_id)

        except Exception as e:
            print(f"❌ Error fetching data for {row['opposing_pitcher']}: {e}")
    return pd.DataFrame(metrics)
