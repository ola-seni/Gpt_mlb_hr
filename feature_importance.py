# feature_importance.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
import os
from datetime import datetime


def analyze_feature_importance(results_csv=None, model_path="model.pkl"):
    """
    Analyze feature importance of the HR prediction model.
    
    Args:
        results_csv (str): Path to CSV with prediction results including actual outcomes
        model_path (str): Path to the trained model
    """
    print("📊 Analyzing feature importance...")
    output_dir = "feature_analysis"
    os.makedirs(output_dir, exist_ok=True)

    # Features we use for prediction
    model_features = [
        "ISO",
        "barrel_rate_50",
        "hr_per_9",
        "park_factor",
        "wind_boost",
        "pitch_matchup_score",
        "bullpen_boost",
        "pitcher_hr_suppression"
    ]
    
    # Try to load model
    try:
        model = joblib.load(model_path)
        has_model = True
        print(f"✅ Model loaded from {model_path}")
    except:
        print(f"⚠️ Model not found at {model_path}, using training data only")
        has_model = False
    
    # Load results data
    if results_csv and os.path.exists(results_csv):
        df = pd.read_csv(results_csv)
        print(f"✅ Loaded {len(df)} records from {results_csv}")
    else:
        # Try to find accuracy logs
        default_path = "results/accuracy_log.csv"
        if os.path.exists(default_path):
            df = pd.read_csv(default_path)
            print(f"✅ Loaded {len(df)} records from default accuracy log")
        else:
            print("❌ No data source found. Please provide a CSV with prediction results.")
            return
    
    # Rename column if needed
    if "Hit_HR" in df.columns:
        target_col = "Hit_HR"
    elif "hit_hr" in df.columns:
        target_col = "hit_hr"
    else:
        print("❌ No target column (Hit_HR or hit_hr) found in data")
        return

    # Make sure all required features exist in data
    missing_features = []
    for feature in model_features:
        if feature not in df.columns and feature.lower() not in df.columns:
            missing_features.append(feature)
    
    if missing_features:
        print(f"❌ Missing features in data: {', '.join(missing_features)}")
        # Try to continue with available features
        model_features = [f for f in model_features if f not in missing_features 
                          and f.lower() not in missing_features]
        print(f"⚠️ Continuing with available features: {', '.join(model_features)}")

    # Normalize feature names if needed
    feature_cols = []
    for feature in model_features:
        if feature in df.columns:
            feature_cols.append(feature)
        elif feature.lower() in df.columns:
            feature_cols.append(feature.lower())
    
    # Ensure features and target are numeric
    for col in feature_cols + [target_col]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop rows with NaN values
    df_clean = df.dropna(subset=feature_cols + [target_col])
    print(f"✅ Using {len(df_clean)} records after removing missing values")
    
    if len(df_clean) < 10:
        print("❌ Not enough data for analysis after cleaning")
        return
    
    # 1. Basic correlation analysis
    print("📈 Calculating feature correlations...")
    correlation_matrix = df_clean[feature_cols + [target_col]].corr()
    
    # Save correlation matrix
    plt.figure(figsize=(12, 10))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
    plt.title('Feature Correlation Matrix')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/correlation_matrix.png")
    plt.close()
    
    # 2. Feature importance from model
    if has_model and hasattr(model, 'feature_importances_'):
        print("🔍 Extracting feature importance from model...")
        # Get built-in feature importance
        importance_df = pd.DataFrame({
            'Feature': model_features,
            'Importance': model.feature_importances_
        }).sort_values(by='Importance', ascending=False)
        
        plt.figure(figsize=(10, 6))
        sns.barplot(x='Importance', y='Feature', data=importance_df)
        plt.title('Feature Importance (From Model)')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/model_feature_importance.png")
        plt.close()
        
        # Save to CSV
        importance_df.to_csv(f"{output_dir}/model_feature_importance.csv", index=False)
    
    # 3. Permutation importance - works even if we don't have original model
    print("🔄 Calculating permutation importance...")
    X = df_clean[feature_cols]
    y = df_clean[target_col]
    
    # If we don't have the original model, train a simple one
    if not has_model:
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
    
    # Calculate permutation importance
    perm_importance = permutation_importance(model, X, y, n_repeats=10, random_state=42)
    
    # Create DataFrame and sort by importance
    perm_importance_df = pd.DataFrame({
        'Feature': feature_cols,
        'Importance': perm_importance.importances_mean,
        'Std_Dev': perm_importance.importances_std
    }).sort_values(by='Importance', ascending=False)
    
    # Plot
    plt.figure(figsize=(10, 6))
    sns.barplot(x='Importance', y='Feature', data=perm_importance_df, 
                xerr=perm_importance_df['Std_Dev'])
    plt.title('Feature Importance (Permutation Method)')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/permutation_importance.png")
    plt.close()
    
    # Save to CSV
    perm_importance_df.to_csv(f"{output_dir}/permutation_importance.csv", index=False)
    
    # 4. Univariate feature analysis
    print("📊 Creating feature distribution plots...")
    plt.figure(figsize=(15, 10))
    
    for i, feature in enumerate(feature_cols, 1):
        plt.subplot(3, 3, i)
        sns.histplot(df_clean, x=feature, hue=target_col, element="step", stat="density", common_norm=False)
        plt.title(f'{feature} Distribution by HR Outcome')
        
    plt.tight_layout()
    plt.savefig(f"{output_dir}/feature_distributions.png")
    plt.close()
    
    # 5. Feature relationships
    print("🔗 Analyzing feature relationships...")
    g = sns.pairplot(df_clean[feature_cols + [target_col]], hue=target_col, 
                   plot_kws={'alpha': 0.6}, diag_kind="kde", corner=True)
    g.fig.suptitle('Feature Relationships', y=1.02)
    plt.savefig(f"{output_dir}/feature_relationships.png")
    plt.close()
    
    # 6. Summary report
    print("📝 Generating summary report...")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(f"{output_dir}/feature_importance_summary.txt", "w") as f:
        f.write(f"Feature Importance Analysis Report\n")
        f.write(f"Generated: {timestamp}\n\n")
        
        f.write("Target Correlation with Features:\n")
        target_corr = correlation_matrix[target_col].drop(target_col).sort_values(ascending=False)
        for feature, corr in target_corr.items():
            f.write(f"- {feature}: {corr:.4f}\n")
        
        f.write("\nTop Features by Permutation Importance:\n")
        for _, row in perm_importance_df.head().iterrows():
            f.write(f"- {row['Feature']}: {row['Importance']:.4f} (±{row['Std_Dev']:.4f})\n")
        
        if has_model and hasattr(model, 'feature_importances_'):
            f.write("\nTop Features by Model Importance:\n")
            for _, row in importance_df.head().iterrows():
                f.write(f"- {row['Feature']}: {row['Importance']:.4f}\n")
    
    print(f"✅ Analysis complete! Reports saved to {output_dir}/")
    return {
        'correlation': correlation_matrix,
        'permutation_importance': perm_importance_df,
        'model_importance': importance_df if has_model and hasattr(model, 'feature_importances_') else None
    }

if __name__ == "__main__":
    # Check for backtest results first
    backtest_file = "backtest_results/backtest_2023-05-01_to_2023-05-15.csv"
    accuracy_log = "results/accuracy_log.csv"
    
    if os.path.exists(backtest_file):
        analyze_feature_importance(backtest_file)
    elif os.path.exists(accuracy_log):
        analyze_feature_importance(accuracy_log)
    else:
        print("⚠️ No results file found. Run backtest.py first or specify a CSV file.")
