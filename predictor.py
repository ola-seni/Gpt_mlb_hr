import pandas as pd
import numpy as np

def generate_hr_predictions(df):
    print("🧠 Generating HR predictions...")

    # Remove exact duplicate rows (optional)
    df = df.drop_duplicates(subset=['batter_name', 'pitcher_name'])

    # Calculate HR_Score (placeholder logic)
    df['HR_Score'] = 1.0  # Replace with actual logic

    # Add label
    def label(score):
        if score > 0.6:
            return "Lock 🔒"
        elif score > 0.3:
            return "Sleeper 🌙"
        else:
            return "Risky ⚠️"

    df['Label'] = df['HR_Score'].apply(label)
    return df[['batter_name', 'pitcher_name', 'HR_Score', 'Label']]

