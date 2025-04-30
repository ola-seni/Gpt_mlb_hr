import pandas as pd
import random

def apply_weather_boosts(df):
    print("🌤️ Applying weather boosts...")
    df['weather_boost'] = [random.uniform(-1, 1) for _ in range(len(df))]
    df['HR_Score'] += df['weather_boost']
    df['HR_Score'] = df['HR_Score'].clip(0, 1)
    return df
