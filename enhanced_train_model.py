#!/usr/bin/env python3
"""
Enhanced Model Training for MLB HR Prediction
Uses expanded feature set with plate discipline and xHR metrics
"""

import pandas as pd
import numpy as np
import os
import joblib
import json
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    roc_auc_score, confusion_matrix, classification_report,
    roc_curve, precision_recall_curve, average_precision_score
)

class HRModelTrainer:
    """Enhanced model trainer for HR prediction with expanded features"""
    
    def __init__(self, 
                 data_path=None, 
                 output_dir="models",
                 target_col="hit_hr"):
        """Initialize the model trainer"""
        self.data_path = data_path
        self.output_dir = output_dir
        self.target_col = target_col
        self.models = {}
        self.results = None
        self.best_model = None
        self.best_model_name = None
        self.features = None
        self.scaler = None
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def load_data(self):
        """Load training data from file or default locations"""
        print("🔍 Preparing data for model training...")
        
        # Try to load data
        if self.data_path and os.path.exists(self.data_path):
            df = pd.read_csv(self.data_path)
            print(f"✅ Loaded {len(df)} records from {self.data_path}")
            return df
        else:
            # Look for backtesting results
            default_paths = [
                "backtest_results/backtest_2023-05-01_to_2023-05-15.csv",
                "results/accuracy_log.csv"
            ]
            
            for path in default_paths:
                if os.path.exists(path):
                    df = pd.read_csv(path)
                    print(f"✅ Loaded {len(df)} records from {path}")
                    return df
                    
        print("❌ No data found. Please provide a CSV file with historical data.")
        return None
    
    def prepare_features(self, df):
        """Prepare features for training, including all new metrics"""
        # Core features (from original model)
        core_features = [
            "ISO", "iso",
            "barrel_rate_50", "barrel_rate",
            "hr_per_9", "HR/9",
            "park_factor",
            "wind_boost",
            "pitch_matchup_score",
            "bullpen_boost",
            "pitcher_hr_suppression"
        ]
        
        # New enhanced features
        enhanced_features = [
            # Power metrics
            "avg_exit_velo", "xHR_per_100", "xSLG",
            
            # Barrel metrics
            "barrel_pct_allowed", "hard_hit_pct_allowed",
            
            # Directional metrics
            "avg_launch_angle", "pull_pct", "fly_ball_pct", "fb_pct_allowed",
            
            # Plate discipline metrics
            "swing_pct", "contact_pct", "zone_pct", "z_swing_pct", "o_swing_pct",
            "whiff_rate", "swing_pct_against", 
            
            # Matchup metrics
            "platoon_advantage"
        ]
        
        # Combine all potential features
        all_potential_features = core_features + enhanced_features
        
        # Find which features are actually in the data
        self.features = [f for f in all_potential_features if f in df.columns]
        
        if len(self.features) < 3:
            print(f"❌ Not enough features found in data. Found: {self.features}")
            return None
            
        print(f"✅ Using {len(self.features)} features: {', '.join(self.features)}")
        
        # Check target column
        if self.target_col not in df.columns:
            alt_target = "Hit_HR" if self.target_col == "hit_hr" else "hit_hr"
            if alt_target in df.columns:
                self.target_col = alt_target
                print(f"⚠️ Using {self.target_col} as target column")
            else:
                print(f"❌ Target column {self.target_col} not found in data")
                return None
        
        # Prepare data
        df_clean = df.dropna(subset=self.features + [self.target_col])
        print(f"✅ Using {len(df_clean)} records after removing missing values")
        
        if len(df_clean) < 50:
            print(f"❌ Not enough clean data for training. Only {len(df_clean)} records after filtering.")
            return None
            
        # Split data
        X = df_clean[self.features]
        y = df_clean[self.target_col].astype(int)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"✅ Data split: {len(X_train)} training samples, {len(X_test)} test samples")
        
        # Feature scaling
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return (X_train, X_test, y_train, y_test, X_train_scaled, X_test_scaled)
    
    def setup_models(self):
        """Setup models to evaluate"""
        return {
            "RandomForest": {
                "model": RandomForestClassifier(random_state=42),
                "params": {
                    "n_estimators": [100, 200, 300],
                    "max_depth": [None, 10, 20],
                    "min_samples_split": [2, 5, 10]
                },
                "needs_scaling": False
            },
            "GradientBoosting": {
                "model": GradientBoostingClassifier(random_state=42),
                "params": {
                    "n_estimators": [100, 200],
                    "learning_rate": [0.01, 0.1],
                    "max_depth": [3, 5]
                },
                "needs_scaling": False
            },
            "LogisticRegression": {
                "model": LogisticRegression(random_state=42, max_iter=1000),
                "params": {
                    "C": [0.1, 1.0, 10.0],
                    "penalty": ["l2"],
                    "solver": ["liblinear", "saga"]
                },
                "needs_scaling": True
            },
            "XGBoost": {
                "model": XGBClassifier(random_state=42),
                "params": {
                    "n_estimators": [100, 200],
                    "learning_rate": [0.01, 0.1],
                    "max_depth": [3, 5]
                },
                "needs_scaling": False
            },
            "LightGBM": {
                "model": LGBMClassifier(random_state=42),
                "params": {
                    "n_estimators": [100, 200],
                    "learning_rate": [0.01, 0.1],
                    "max_depth": [3, 5]
                },
                "needs_scaling": False
            },
            "NeuralNetwork": {
                "model": MLPClassifier(random_state=42, max_iter=500),
                "params": {
                    "hidden_layer_sizes": [(50,), (100,), (50, 50)],
                    "alpha": [0.0001, 0.001, 0.01],
                    "learning_rate": ["constant", "adaptive"]
                },
                "needs_scaling": True
            }
        }
    
    def train_models(self, data):
        """Train and evaluate all models"""
        X_train, X_test, y_train, y_test, X_train_scaled, X_test_scaled = data
        
        # Setup models
        models = self.setup_models()
        
        # Train and evaluate each model
        results = []
        trained_models = {}
        
        for name, config in models.items():
            print(f"🔧 Training {name}...")
            
            model = config["model"]
            params = config["params"]
            
            # Use scaled data if the model needs it
            X_train_data = X_train_scaled if config["needs_scaling"] else X_train
            X_test_data = X_test_scaled if config["needs_scaling"] else X_test
            
            # Define the grid search
            grid_search = GridSearchCV(
                estimator=model,
                param_grid=params,
                cv=5,
                scoring='roc_auc',
                n_jobs=-1
            )
            
            # Train the model
            try:
                grid_search.fit(X_train_data, y_train)
                
                # Get the best model
                best_model = grid_search.best_estimator_
                
                # Make predictions
                y_pred = best_model.predict(X_test_data)
                y_proba = best_model.predict_proba(X_test_data)[:, 1]
                
                # Calculate metrics
                metrics = {
                    "Model": name,
                    "Accuracy": accuracy_score(y_test, y_pred),
                    "Precision": precision_score(y_test, y_pred),
                    "Recall": recall_score(y_test, y_pred),
                    "F1": f1_score(y_test, y_pred),
                    "AUC": roc_auc_score(y_test, y_proba),
                    "AP": average_precision_score(y_test, y_proba),
                    "Best_Params": grid_search.best_params_
                }
                
                results.append(metrics)
                trained_models[name] = {
                    "model": best_model,
                    "needs_scaling": config["needs_scaling"],
                    "metrics": metrics
                }
                
                print(f"✅ {name} AUC: {metrics['AUC']:.4f}")
                
            except Exception as e:
                print(f"❌ Error training {name}: {e}")
                continue
        
        # Convert results to DataFrame
        results_df = pd.DataFrame(results)
        
        if not results_df.empty:
            results_df = results_df.sort_values("AUC", ascending=False).reset_index(drop=True)
        
        self.results = results_df
        self.models = trained_models
        
        return results_df
    
    def analyze_best_model(self):
        """Analyze the best performing model"""
        if self.results is None or self.results.empty:
            print("❌ No models were successfully trained")
            return
            
        # Get best model
        best_model_name = self.results.iloc[0]["Model"]
        best_model_config = self.models[best_model_name]
        best_model = best_model_config["model"]
        needs_scaling = best_model_config["needs_scaling"]
        
        print(f"🏆 Best model: {best_model_name} (AUC: {self.results.iloc[0]['AUC']:.4f})")
        
        # Save as class attributes
        self.best_model = best_model
        self.best_model_name = best_model_name
        
        # Create feature importance visualization
        if hasattr(best_model, 'feature_importances_'):
            feature_imp = pd.DataFrame({
                'Feature': self.features,
                'Importance': best_model.feature_importances_
            }).sort_values('Importance', ascending=False)
            
            plt.figure(figsize=(12, 8))
            ax = sns.barplot(x='Importance', y='Feature', data=feature_imp)
            plt.title(f'Feature Importance ({best_model_name})')
            
            # Format feature names for readability
            feature_list = feature_imp['Feature'].tolist()
            feature_labels = [f"{item} ({i+1})" for i, item in enumerate(feature_list)]
            plt.yticks(range(len(feature_list)), feature_labels)
            
            # Add values to bars
            for i, v in enumerate(feature_imp['Importance']):
                ax.text(v + 0.01, i, f'{v:.3f}', va='center')
            
            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/feature_importance.png")
            plt.close()
            
            # Save feature importance to CSV
            feature_imp.to_csv(f"{self.output_dir}/feature_importance.csv", index=False)
            
            # Print top features
            print("\n🔝 Top 10 Most Important Features:")
            for i, (feature, importance) in enumerate(zip(feature_imp['Feature'].head(10), 
                                                         feature_imp['Importance'].head(10))):
                print(f"{i+1}. {feature}: {importance:.4f}")
        
        return best_model
    
    def save_model(self):
        """Save the best model and related artifacts"""
        if self.best_model is None:
            print("❌ No best model to save")
            return
            
        # Save model
        model_path = f"{self.output_dir}/model.pkl"
        joblib.dump(self.best_model, model_path)
        
        # Save scaler if needed
        if any(self.models[name]["needs_scaling"] for name in self.models):
            scaler_path = f"{self.output_dir}/scaler.pkl"
            joblib.dump(self.scaler, scaler_path)
            print(f"✅ Scaler saved to {scaler_path}")
        
        # Save meta information
        meta_info = {
            "model_name": self.best_model_name,
            "features": self.features,
            "needs_scaling": self.models[self.best_model_name]["needs_scaling"],
            "metrics": {k: v for k, v in self.results.iloc[0].items() if k != "Best_Params"},
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "threshold": 0.5  # Default threshold, could be tuned
        }
        
        with open(f"{self.output_dir}/model_meta.json", "w") as f:
            json.dump(meta_info, f, indent=2)
        
        print(f"✅ Best model ({self.best_model_name}) saved to {model_path}")
        
        # Create prediction utility
        self._create_prediction_utility()
        
        return model_path
    
    def _create_prediction_utility(self):
        """Create a utility script for making predictions"""
        utility_path = f"{self.output_dir}/predict_hr.py"
        
        with open(utility_path, "w") as f:
            f.write("""
import joblib
import pandas as pd
import os
import json

def predict_hr_probability(player_data):
    \"\"\"
    Predict the home run probability for a player.
    
    Args:
        player_data: Dictionary with player features
        
    Returns:
        Probability of hitting a home run (0-1)
    \"\"\"
    # Load model metadata
    with open("models/model_meta.json", "r") as f:
        meta = json.load(f)
    
    # Load the model
    model = joblib.load("models/model.pkl")
    
    # Check if we need scaling
    needs_scaling = meta.get("needs_scaling", False)
    scaler = None
    if needs_scaling:
        scaler = joblib.load("models/scaler.pkl")
    
    # Get required features
    features = meta["features"]
    
    # Prepare input data
    missing_features = [f for f in features if f not in player_data]
    if missing_features:
        print(f"Warning: Missing features: {missing_features}")
        for f in missing_features:
            player_data[f] = 0.0
    
    # Create DataFrame
    df = pd.DataFrame([player_data])
    X = df[features]
    
    # Apply scaling if needed
    if needs_scaling and scaler is not None:
        X = scaler.transform(X)
    
    # Make prediction
    probability = model.predict_proba(X)[0, 1]
    
    return probability

def classify_hr_prediction(probability):
    \"\"\"
    Classify the HR prediction into tiers.
    
    Args:
        probability: Home run probability (0-1)
        
    Returns:
        Classification as "Lock", "Sleeper", or "Risky"
    \"\"\"
    if probability >= 0.25:
        return "Lock 🔒"
    elif probability >= 0.15:
        return "Sleeper 🌙"
    else:
        return "Risky ⚠️"

# Example usage
if __name__ == "__main__":
    # Example player data with enhanced metrics
    player = {
        "ISO": 0.250,
        "barrel_rate_50": 0.15,
        "hr_per_9": 1.2,
        "park_factor": 1.05,
        "wind_boost": 0.05,
        "pitch_matchup_score": 0.2,
        "bullpen_boost": 0.1,
        # Enhanced metrics
        "xHR_per_100": 4.5,
        "avg_exit_velo": 92.3,
        "avg_launch_angle": 26.5,
        "swing_pct": 0.48,
        "contact_pct": 0.76,
        "platoon_advantage": 0.65
    }
    
    prob = predict_hr_probability(player)
    classification = classify_hr_prediction(prob)
    
    print(f"HR Probability: {prob:.3f}")
    print(f"Classification: {classification}")
"""
        )
        
        print(f"✅ Prediction utility saved to {utility_path}")
    
    def train(self):
        """Run the full training pipeline"""
        # Load and prepare data
        df = self.load_data()
        if df is None:
            return False
            
        # Prepare features
        data = self.prepare_features(df)
        if data is None:
            return False
            
        # Train models
        self.train_models(data)
        
        # Analyze best model
        self.analyze_best_model()
        
        # Save model
        self.save_model()
        
        # Print final summary
        print("\n📊 Model Performance Summary:")
        if self.results is not None:
            print(self.results[["Model", "AUC", "Precision", "Recall"]].to_string(index=False))
        print(f"\nDetailed results saved to {self.output_dir}/")
        
        return True

def main():
    """Main function to run model training"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train enhanced MLB HR prediction models")
    parser.add_argument("--data", type=str, help="Path to training data CSV")
    parser.add_argument("--output", type=str, default="models", help="Output directory for models")
    parser.add_argument("--target", type=str, default="hit_hr", help="Target column name")
    
    args = parser.parse_args()
    
    trainer = HRModelTrainer(
        data_path=args.data,
        output_dir=args.output,
        target_col=args.target
    )
    
    success = trainer.train()
    
    if success:
        print("✅ Enhanced model training completed successfully!")
    else:
        print("❌ Model training failed. Please check errors above.")

if __name__ == "__main__":
    main()
