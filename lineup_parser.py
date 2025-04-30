import pandas as pd

def get_confirmed_lineups():
    print("📋 Getting confirmed lineups...")
    # Mock confirmed lineups
    return pd.DataFrame([
        {
            "game_id": 1,
            "batter_id": 592450,
            "batter_name": "Aaron Judge",
            "opposing_pitcher": "Clarke Schmidt"
        },
        {
            "game_id": 2,
            "batter_id": 665742,
            "batter_name": "Juan Soto",
            "opposing_pitcher": "Max Scherzer"
        }
    ])
