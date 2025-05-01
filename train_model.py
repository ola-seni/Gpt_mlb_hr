import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import joblib
import glob
import os

def load_training_data(results_dir="results"):
    print("📁 Loading past predictions...")
    files = glob.glob(os.path.join(results_dir, "hr_predictions_*.csv"))
    all_data = []

    for file in files:
        df = pd.read_csv(file)
        if "Hit_HR" in df.columns:
            all_data.append(df)

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

def train_model():
    df = load_training_data()
    if df.empty:
        print("⚠️ No labeled HR data found.")
        return

    print("📊 Preparing features...")
    features = ["ISO", "barrel_rate_50", "hr_per_9", "wind_boost", "park_factor"]
    df = df.dropna(subset=features + ["Hit_HR"])
    
    X = df[features]
    y = df["Hit_HR"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("🧠 Training model...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    acc = model.score(X_test, y_test)
    print(f"✅ Model trained. Accuracy on test set: {acc:.2f}")

    joblib.dump(model, "model.pkl")
    print("💾 Model saved to model.pkl")

if __name__ == "__main__":
    train_model()
