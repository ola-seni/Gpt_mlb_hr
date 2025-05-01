
import pandas as pd
import joblib
import os

USE_MODEL_SCORING = os.path.exists("model.pkl")

if USE_MODEL_SCORING:
    try:
        model = joblib.load("model.pkl")
        print("✅ Loaded trained model (model.pkl)")
    except Exception as e:
        print(f"⚠️ Failed to load model.pkl: {e}")
        USE_MODEL_SCORING = False
else:
    print("⚠️ model.pkl not found — using rule-based HR_Score only.")

def generate_hr_predictions(df):
    df = df.copy()

    # Fallback score if not using model
    if not USE_MODEL_SCORING:
        df["HR_Prob"] = df["HR_Score"]
        return df

    # Features used in model
    model_features = [
        "ISO",
        "barrel_rate_50",
        "hr_per_9",
        "wind_boost",
        "park_factor",
        "pitch_matchup_score",
        "bullpen_boost",
        "pitcher_hr_suppression"
    ]

    # Drop NA rows
    df = df.dropna(subset=model_features)

    # Predict
    df["HR_Prob"] = model.predict_proba(df[model_features])[:, 1]
    return df
