# expanded_predictions.py
import pandas as pd
import numpy as np
from predictor import generate_enhanced_hr_predictions
import joblib
import os

class BaseballOutcomePredictor:
    """
    Expanded predictor for multiple baseball outcomes including:
    - Home runs
    - Doubles
    - Triples
    - RBIs
    - Hits
    - Runs
    """
    
    def __init__(self):
        """Initialize the multi-outcome predictor"""
        self.models = {}
        self.load_models()
        
    def load_models(self):
        """Load available prediction models"""
        model_dir = "models/expanded"
        os.makedirs(model_dir, exist_ok=True)
        
        outcomes = ["hr", "double", "triple", "rbi", "hit", "run"]
        
        for outcome in outcomes:
            model_path = f"{model_dir}/{outcome}_model.pkl"
            if os.path.exists(model_path):
                try:
                    self.models[outcome] = joblib.load(model_path)
                    print(f"✅ Loaded {outcome} prediction model")
                except Exception as e:
                    print(f"❌ Error loading {outcome} model: {e}")
    
    def predict_all_outcomes(self, df):
        """
        Generate predictions for all outcomes.
        Falls back to rule-based prediction if model not available.
        
        Args:
            df (pandas.DataFrame): DataFrame with player matchup data
            
        Returns:
            pandas.DataFrame: DataFrame with predictions for all outcomes
        """
        if df.empty:
            return df
            
        # Make a copy to avoid modifying the original
        result_df = df.copy()
        
        # Start with HR predictions using existing function
        result_df = generate_enhanced_hr_predictions(result_df)
        
        # Add predictions for other outcomes
        self._predict_doubles(result_df)
        self._predict_triples(result_df)
        self._predict_rbis(result_df)
        self._predict_hits(result_df)
        self._predict_runs(result_df)
        
        return result_df
    
    def _predict_doubles(self, df):
        """Add double predictions to DataFrame"""
        if "double" in self.models:
            # Use model for prediction
            # Implement model prediction logic here
            pass
        else:
            # Rule-based prediction
            df["Double_Score"] = (
                df["ISO"].fillna(0) * 0.35 +
                df["barrel_rate_50"].fillna(0) * 0.25 +
                df["pitch_matchup_score"].fillna(0) * 0.15 +
                df["park_factor"].fillna(1.0) * 0.15 +
                df["bullpen_boost"].fillna(0) * 0.10
            )
        
        return df
    
    def _predict_triples(self, df):
        """Add triple predictions to DataFrame"""
        if "triple" in self.models:
            # Use model for prediction
            pass
        else:
            # Rule-based prediction
            # Triples are more about speed than power
            df["Triple_Score"] = (
                df["ISO"].fillna(0) * 0.15 +
                df.get("sprint_speed", pd.Series(0, index=df.index)).fillna(0) * 0.40 +
                df["park_factor"].fillna(1.0) * 0.25 +  # Park dimensions matter a lot
                df["wind_boost"].fillna(0) * 0.20
            )
            
            # Cap at reasonable values
            df["Triple_Score"] = df["Triple_Score"].clip(0.0, 0.3)  # Triples are rare
        
        return df
    
    def _predict_rbis(self, df):
        """Add RBI predictions to DataFrame"""
        if "rbi" in self.models:
            # Use model for prediction
            pass
        else:
            # Rule-based prediction
            # RBIs depend on HR/hit likelihood and lineup position
            df["RBI_Score"] = (
                df["HR_Score"] * 0.40 +  # HRs guarantee at least 1 RBI
                df["Double_Score"] * 0.25 +  # Doubles often drive in runs
                df.get("batting_order", pd.Series(4, index=df.index)).apply(
                    lambda x: 0.2 if 3 <= x <= 5 else 0.1  # Middle order gets more RBI chances
                ) * 0.35
            )
        
        return df
    
    def _predict_hits(self, df):
        """Add hit predictions to DataFrame"""
        if "hit" in self.models:
            # Use model for prediction
            pass
        else:
            # Rule-based prediction
            # Hits are about contact and batting
