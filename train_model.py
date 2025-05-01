# train_model.py

import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Load labeled data — make sure this file exists and has 'Hit_HR' column
df = pd.read_csv("results/accuracy_log.csv")

# Filter for valid rows
df = df[df["HR_Score"].notna() & df["Hit_HR"].notna()]

# Features to train on — must match those used in main.py
model_features = [
    "ISO",
    "barrel_rate_50",
    "HR/9",
    "wind_boost",
    "park_factor",
    "pitch_matchup_score",
    "bullpen_boost",
    "pitcher_hr_suppression"
]

# Drop rows with missing feature data
df = df.dropna(subset=model_features + ["Hit_HR"])

X = df[model_features]
y = df["Hit_HR"]

# Split for validation
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate
print("📊 Model Evaluation on Test Set:")
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# Save model
joblib.dump(model, "model.pkl")
print("✅ model.pkl saved successfully.")
