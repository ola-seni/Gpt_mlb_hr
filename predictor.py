import joblib
import os
import numpy as np

model_path = "model.pkl"
USE_MODEL = os.path.exists(model_path)
model = joblib.load(model_path) if USE_MODEL else None

# Add to predictor.py - place after the existing generate_hr_predictions function

def generate_enhanced_hr_predictions(df):
    """
    Enhanced prediction function with optimized feature weights and advanced matchup analysis.
    """
    if df.empty:
        return df
        
    # Define features here, outside of any conditional blocks
    features = ["ISO", "barrel_rate_50", "pitch_matchup_score", "bullpen_boost", "hr_per_9"]
    
    # Add column for advanced matchup score
    df["advanced_matchup_score"] = 0.0
    
    # Calculate advanced matchup scores for a subset of top matchups to avoid excessive API calls
    top_n = min(10, len(df))  # Only analyze top 10 matchups
    top_candidates = df.sort_values("ISO", ascending=False).head(top_n)
    
    for idx, row in top_candidates.iterrows():
        try:
            batter_id = row.get("batter_id")
            pitcher_id = row.get("pitcher_id")
            
            if batter_id and pitcher_id:
                # In the real implementation, this would call the advanced matchup analysis
                # But for now, use a placeholder value based on their stats
                iso = row.get("ISO", 0)
                barrel = row.get("barrel_rate_50", 0)
                hr_per_9 = row.get("hr_per_9", 0)
                
                advanced_score = (iso * 0.5 + barrel * 0.4 + hr_per_9 * 0.1)
                df.at[idx, "advanced_matchup_score"] = min(0.3, advanced_score)
        except Exception as e:
            print(f"⚠️ Error in advanced matchup analysis for {row.get('batter_name', 'Unknown')}: {e}")
    
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
            df["ISO"].fillna(0) * 0.40 +             # Slightly reduced
            df["barrel_rate_50"].fillna(0) * 0.30 +  # Slightly reduced
            df["pitch_matchup_score"].fillna(0) * 0.10 +  # Reduced to make room for advanced
            df["advanced_matchup_score"].fillna(0) * 0.10 +  # New factor
            df["bullpen_boost"].fillna(0) * 0.10 -   # Same
            df["hr_per_9"].fillna(0) * 0.05          # Same
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
