import joblib
import os
import numpy as np

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

def generate_enhanced_hr_predictions(df):
    """
    Enhanced prediction function with optimized feature weights based on 
    statistical analysis of home run outcomes.
    """
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
        print("🔍 Using enhanced rule-based HR_Score calculation...")
        
        # Define optimized weights based on statistical analysis
        df["HR_Score"] = (
            df["ISO"].fillna(0) * 0.45 +        # Increased weight for ISO (most predictive)
            df["barrel_rate_50"].fillna(0) * 0.35 +  # Slightly reduced but still important
            df["pitch_matchup_score"].fillna(0) * 0.15 +  # Increased importance
            df["bullpen_boost"].fillna(0) * 0.10 -  # Increased
            df["hr_per_9"].fillna(0) * 0.05      # Same weight
        )
        
        # Add a non-linear adjustment for extreme barrel rates
        # Players with very high barrel rates get an extra boost
        barrel_boost = df["barrel_rate_50"].apply(
            lambda x: 0.05 if x > 0.2 else 0 if x <= 0.1 else 0.02
        )
        df["HR_Score"] += barrel_boost
        
        # Add recency bias - recent performance matters more
        if "recent_hr_rate" in df.columns:
            df["HR_Score"] += df["recent_hr_rate"].fillna(0) * 0.1
            
        # Apply hot/cold streak adjustments if available
        if "last_7_iso" in df.columns:
            # Calculate the ratio of recent ISO to season ISO
            iso_ratio = df.apply(
                lambda row: min(max(row["last_7_iso"] / max(row["ISO"], 0.001), 0.5), 2.0), 
                axis=1
            )
            # Apply a subtle boost/penalty based on recent performance
            df["HR_Score"] *= (iso_ratio * 0.2) + 0.8  # Range from 0.9 to 1.2 multiplier
                
        # Cap the score at reasonable bounds (0.0 to 0.8)
        df["HR_Score"] = df["HR_Score"].clip(0.0, 0.8)
        df["HR_Prob"] = df["HR_Score"]

    return df.sort_values("HR_Score", ascending=False).reset_index(drop=True)
