import numpy as np

def apply_weather_boosts(df):
    print("🌤️ Applying weather and park effects...")
    df['wind_boost'] = np.random.normal(0, 0.05, size=len(df))  # Simulated for now
    df['park_factor'] = np.random.uniform(0.95, 1.10, size=len(df))  # Simulated for now
    return df
