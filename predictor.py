import pandas as pd
import numpy as np

def generate_hr_predictions(df):
    print("🧠 Generating HR predictions...")

    # Calculate HR_Score using mock logic
    df['HR_Score'] = np.random.rand(len(df))

    # Add labels
    def label(score):
        if score > 0.6:
            return "Lock 🔒"
        elif score > 0.3:
            return "Sleeper 🌙"
        else:
            return "Risky ⚠️"

    df['Label'] = df['HR_Score'].apply(label)
    return df[['batter_name', 'pitcher_name', 'HR_Score', 'Label']]
