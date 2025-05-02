import joblib
import os

model_path = "model.pkl"
USE_MODEL = os.path.exists(model_path)
model = joblib.load(model_path) if USE_MODEL else None

def generate_hr_predictions(df):
    if df.empty:
        return df
        
    # Define features here, outside of any conditional blocks
    features = ["ISO", "barrel_rate_50", "pitch_matchup_score", "bullpen_boost", "hr_per_9"]

    if USE_MODEL:
        print("🤖 Using ML model for HR predictions...")
        # Make sure all required features exist
        for feature in features:
            if feature not in df.columns:
                print(f"⚠️ Missing feature: {feature}, adding default value")
                df[feature] = 0.0
            else:
                df[feature] = df[feature].fillna(0.0)
                
        df["HR_Prob"] = model.predict_proba(df[features])[:, 1]
        df["HR_Score"] = df["HR_Prob"]
    else:
        print("⚠️ model.pkl not found — using rule-based HR_Score only.")
        df["HR_Score"] = (
            df["ISO"].fillna(0) * 0.4 +
            df["barrel_rate_50"].fillna(0) * 0.4 +
            df["pitch_matchup_score"].fillna(0) * 0.1 +
            df["bullpen_boost"].fillna(0) * 0.05 -
            df["hr_per_9"].fillna(0) * 0.05
        )
        df["HR_Prob"] = df["HR_Score"]

    return df.sort_values("HR_Score", ascending=False).reset_index(drop=True)
