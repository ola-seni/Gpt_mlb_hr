import pandas as pd
import numpy as np
import joblib

model = joblib.load("model.pkl")

def generate_hr_predictions(df):
    print("🧠 Generating HR predictions...")

    df = df.drop_duplicates(subset=['batter_name', 'pitcher_name'])

    # Simulate HR_Score with base logic (until you have more features)
    df['HR_Score'] = np.clip(np.random.normal(0.45, 0.2, len(df)), 0, 1)

    # ✅ Predict actual HR probability using trained model
    model_features = ["ISO", "barrel_rate_50", "hr_per_9", "wind_boost", "park_factor", 'pitcher_hr_suppression']
    df["HR_Prob"] = model.predict_proba(df[model_features])[:, 1]


    # Optional: base labels on ML probabilities instead of HR_Score
    def label(prob):
        if prob >= 0.7:
            return "Lock 🔒"
        elif prob >= 0.4:
            return "Sleeper 🌙"
        else:
            return "Risky ⚠️"

    df['Label'] = df['HR_Prob'].apply(label)

    return df[['batter_name', 'pitcher_name', 'HR_Score', 'HR_Prob', 'Label']]
