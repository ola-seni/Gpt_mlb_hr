# advanced_models.py
import pandas as pd
import numpy as np
import os
import joblib
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, GridSearchCV
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

def train_advanced_models(
    data_path=None, 
    target_col="hit_hr", 
    test_size=0.2, 
    random_state=42,
    save_models=True
):
    """
    Train and evaluate multiple ML models for HR prediction
    
    Args:
        data_path: CSV file with historical data for training
        target_col: Column name for the target variable
        test_size: Percentage of data to use for testing
        random_state: Random seed for reproducibility
        save_models: Whether to save trained models to disk
    """
    # Setup output directory
    output_dir = "models"
    os.makedirs(output_dir, exist_ok=True)
    
    print("🔍 Preparing data for model training...")
    
    # Try to load data
    if data_path and os.path.exists(data_path):
        df = pd.read_csv(data_path)
        print(f"✅ Loaded {len(df)} records from {data_path}")
    else:
        # Look for backtesting results
        default_paths = [
            "backtest_results/backtest_2023-05-01_to_2023-05-15.csv",
            "results/accuracy_log.csv"
        ]
        
        data_loaded = False
        for path in default_paths:
            if os.path.exists(path):
                df = pd.read_csv(path)
                print(f"✅ Loaded {len(df)} records from {path}")
                data_loaded = True
                break
                
        if not data_loaded:
            print("❌ No data found. Please provide a CSV file with historical data.")
            return
    
    # Check if target column exists
    if target_col not in df.columns:
        alt_target = "Hit_HR" if target_col == "hit_hr" else "hit_hr"
        if alt_target in df.columns:
            target_col = alt_target
            print(f"⚠️ Using {target_col} as target column")
        else:
            print(f"❌ Target column {target_col} not found in data")
            return
    
    # Define features for prediction
    potential_features = [
        "ISO", "iso",
        "barrel_rate_50", "barrel_rate",
        "hr_per_9", "HR/9",
        "park_factor",
        "wind_boost",
        "pitch_matchup_score",
        "bullpen_boost",
        "pitcher_hr_suppression"
    ]
    
    # Find which features are actually in the data
    features = [f for f in potential_features if f in df.columns]
    
    if len(features) < 3:
        print(f"❌ Not enough features found in data. Found: {features}")
        return
    
    print(f"✅ Using features: {features}")
    
    # Prepare data
    df = df.dropna(subset=features + [target_col])
    X = df[features]
    y = df[target_col].astype(int)
    
    if len(X) < 50:
        print(f"❌ Not enough clean data for training. Only {len(X)} records after filtering.")
        return
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    print(f"✅ Data split: {len(X_train)} training samples, {len(X_test)} test samples")
    
    # Feature scaling for some models
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Define models to evaluate
    models = {
        "RandomForest": {
            "model": RandomForestClassifier(random_state=random_state),
            "params": {
                "n_estimators": [100, 200, 300],
                "max_depth": [None, 10, 20],
                "min_samples_split": [2, 5, 10]
            },
            "needs_scaling": False
        },
        "GradientBoosting": {
            "model": GradientBoostingClassifier(random_state=random_state),
            "params": {
                "n_estimators": [100, 200],
                "learning_rate": [0.01, 0.1],
                "max_depth": [3, 5]
            },
            "needs_scaling": False
        },
        "LogisticRegression": {
            "model": LogisticRegression(random_state=random_state, max_iter=1000),
            "params": {
                "C": [0.1, 1.0, 10.0],
                "penalty": ["l2"],
                "solver": ["liblinear", "saga"]
            },
            "needs_scaling": True
        },
        "XGBoost": {
            "model": XGBClassifier(random_state=random_state),
            "params": {
                "n_estimators": [100, 200],
                "learning_rate": [0.01, 0.1],
                "max_depth": [3, 5]
            },
            "needs_scaling": False
        },
        "LightGBM": {
            "model": LGBMClassifier(random_state=random_state),
            "params": {
                "n_estimators": [100, 200],
                "learning_rate": [0.01, 0.1],
                "max_depth": [3, 5]
            },
            "needs_scaling": False
        },
        "NeuralNetwork": {
            "model": MLPClassifier(random_state=random_state, max_iter=500),
            "params": {
                "hidden_layer_sizes": [(50,), (100,), (50, 50)],
                "alpha": [0.0001, 0.001, 0.01],
                "learning_rate": ["constant", "adaptive"]
            },
            "needs_scaling": True
        }
    }
    
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
                "metrics": metrics,
                "feature_names": features
            }
            
            print(f"✅ {name} AUC: {metrics['AUC']:.4f}")
            
        except Exception as e:
            print(f"❌ Error training {name}: {e}")
    
    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("AUC", ascending=False).reset_index(drop=True)
    
    # Save results
    results_df.to_csv(f"{output_dir}/model_comparison.csv", index=False)
    
    # Plot performance comparison
    plt.figure(figsize=(12, 6))
    sns.barplot(x="Model", y="AUC", data=results_df)
    plt.title("Model Performance Comparison (AUC)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/model_comparison.png")
    plt.close()
    
    # Detailed analysis of the best model
    if results_df.empty:
        print("❌ No models were successfully trained")
        return None
        
    best_model_name = results_df.iloc[0]["Model"]
    best_model_config = trained_models[best_model_name]
    best_model = best_model_config["model"]
    needs_scaling = best_model_config["needs_scaling"]
    
    print(f"🏆 Best model: {best_model_name} (AUC: {results_df.iloc[0]['AUC']:.4f})")
    
    # Prepare test data for the best model
    X_test_best = X_test_scaled if needs_scaling else X_test
    y_proba_best = best_model.predict_proba(X_test_best)[:, 1]
    
    # Plot ROC curve
    plt.figure(figsize=(10, 8))
    
    # ROC Curve
    plt.subplot(2, 2, 1)
    fpr, tpr, _ = roc_curve(y_test, y_proba_best)
    plt.plot(fpr, tpr, label=f'AUC = {roc_auc_score(y_test, y_proba_best):.3f}')
    plt.plot([0, 1], [0, 1], 'k--', label='Random')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve')
    plt.legend()
    
    # Precision-Recall Curve
    plt.subplot(2, 2, 2)
    precision, recall, _ = precision_recall_curve(y_test, y_proba_best)
    plt.plot(recall, precision, label=f'AP = {average_precision_score(y_test, y_proba_best):.3f}')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.legend()
    
    # Probability Distribution
    plt.subplot(2, 2, 3)
    sns.histplot(y_proba_best[y_test == 0], color='red', alpha=0.5, label='No HR', bins=20)
    sns.histplot(y_proba_best[y_test == 1], color='green', alpha=0.5, label='HR', bins=20)
    plt.xlabel('Predicted Probability')
    plt.ylabel('Count')
    plt.title('Probability Distribution')
    plt.legend()
    
    # Confusion Matrix
    plt.subplot(2, 2, 4)
    threshold = 0.5  # Default threshold
    y_pred_best = (y_proba_best >= threshold).astype(int)
    cm = confusion_matrix(y_test, y_pred_best)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.title('Confusion Matrix')
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/best_model_analysis.png")
    plt.close()
    
    # Feature importance for the best model
    if hasattr(best_model, 'feature_importances_'):
        feature_imp = pd.DataFrame({
            'Feature': features,
            'Importance': best_model.feature_importances_
        }).sort_values('Importance', ascending=False)
        
        plt.figure(figsize=(10, 6))
        sns.barplot(x='Importance', y='Feature', data=feature_imp)
        plt.title(f'Feature Importance ({best_model_name})')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/best_model_feature_importance.png")
        plt.close()
        
        feature_imp.to_csv(f"{output_dir}/best_model_feature_importance.csv", index=False)
    
    # Save the best model
    if save_models:
        # Save best model
        best_model_path = f"{output_dir}/best_model_{best_model_name}.pkl"
        joblib.dump(best_model, best_model_path)
        
        # Save scaler if needed
        if needs_scaling:
            scaler_path = f"{output_dir}/scaler.pkl"
            joblib.dump(scaler, scaler_path)
            print(f"✅ Scaler saved to {scaler_path}")
        
        # Save meta information
        meta_info = {
            "model_name": best_model_name,
            "features": features,
            "needs_scaling": needs_scaling,
            "metrics": {k: v for k, v in results_df.iloc[0].items() if k != "Best_Params"},
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "threshold": threshold
        }
        
        with open(f"{output_dir}/model_meta.json", "w") as f:
            import json
            json.dump(meta_info, f, indent=2)
        
        print(f"✅ Best model saved to {best_model_path}")
        
        # Create a simple prediction function
        with open(f"{output_dir}/predict_hr.py", "w") as f:
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
    model = joblib.load(f"models/best_model_{meta['model_name']}.pkl")
    
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
    # Example player data
    player = {
        "ISO": 0.250,
        "barrel_rate_50": 0.15,
        "hr_per_9": 1.2,
        "park_factor": 1.05,
        "wind_boost": 0.05,
        "pitch_matchup_score": 0.2,
        "bullpen_boost": 0.1
    }
    
    prob = predict_hr_probability(player)
    classification = classify_hr_prediction(prob)
    
    print(f"HR Probability: {prob:.3f}")
    print(f"Classification: {classification}")
""")
        
        print(f"✅ Prediction utility saved to {output_dir}/predict_hr.py")
    
    # Print final summary
    print("\n📊 Model Performance Summary:")
    print(results_df[["Model", "AUC", "Precision", "Recall"]].to_string(index=False))
    print(f"\nDetailed results saved to {output_dir}/")
    
    return {
        "best_model": best_model,
        "best_model_name": best_model_name,
        "metrics": results_df,
        "features": features,
        "needs_scaling": needs_scaling
    }

if __name__ == "__main__":
    # Check for existing data sources
    potential_sources = [
        "backtest_results/backtest_2023-05-01_to_2023-05-15.csv",
        "results/accuracy_log.csv"
    ]
    
    data_path = None
    for source in potential_sources:
        if os.path.exists(source):
            data_path = source
            break
    
    if data_path:
        train_advanced_models(data_path)
    else:
        print("⚠️ No data source found. Please run backtest.py first.")
