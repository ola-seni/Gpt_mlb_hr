import pandas as pd
import numpy as np

def generate_hr_predictions(df):
    print("🧠 Generating HR predictions...")

    df = df.drop_duplicates(subset=['batter_name', 'pitcher_name'])

    # Simulate a scoring formula based on some mock logic
    # In production, you'd replace this with actual metrics
    df['HR_Score'] = np.clip(np.random.normal(0.45, 0.2, len(df)), 0, 1)

    def label(score):
        if score >= 0.7:
            return "Lock 🔒"
        elif score >= 0.4:
            return "Sleeper 🌙"
        else:
            return "Risky ⚠️"

    df['Label'] = df['HR_Score'].apply(label)
    return df[['batter_name', 'pitcher_name', 'HR_Score', 'Label']]
