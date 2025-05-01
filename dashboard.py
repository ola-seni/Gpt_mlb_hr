import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

st.set_page_config(page_title="HR Prediction Accuracy", layout="wide")
st.title("📈 Home Run Prediction Accuracy Dashboard")

log_path = "results/accuracy_log.csv"

if not os.path.exists(log_path):
    st.warning("No accuracy log found yet.")
    st.stop()

# Load data
df = pd.read_csv(log_path)
df["date"] = pd.to_datetime(df["date"])

# Summary toggle
view = st.radio("Select view:", ["Daily", "Weekly Summary"], horizontal=True)

if view == "Weekly Summary":
    df["week"] = df["date"].dt.to_period("W").dt.start_time
    df_grouped = df.groupby(["week", "Prediction_Type"]).agg({
        "total_preds": "sum",
        "hit_count": "sum"
    }).reset_index()
    df_grouped["hit_rate"] = df_grouped["hit_count"] / df_grouped["total_preds"]
    date_col = "week"
else:
    df_grouped = df.copy()
    date_col = "date"

# 📅 Accuracy Table
st.subheader(f"📋 {view} Accuracy Log")
st.dataframe(df_grouped.sort_values([date_col, "Prediction_Type"], ascending=False), use_container_width=True)

# 📈 Hit Rate Trend by Type
st.subheader(f"📈 Hit Rate Trends by Prediction Type ({view})")
pivot = df_grouped.pivot_table(index=date_col, columns="Prediction_Type", values="hit_rate")
st.line_chart(pivot)

# 🔍 All-Time Summary
st.subheader("🏁 Overall Accuracy by Prediction Type")
summary = df.groupby("Prediction_Type").agg({
    "total_preds": "sum",
    "hit_count": "sum"
}).reset_index()
summary["hit_rate"] = summary["hit_count"] / summary["total_preds"]
st.dataframe(summary)

# 📊 Total Summary
st.subheader("📦 Overall Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Predictions", int(df["total_preds"].sum()))
col2.metric("Total HR Hits", int(df["hit_count"].sum()))
col3.metric("Overall Hit Rate", f"{(df['hit_count'].sum() / df['total_preds'].sum() * 100):.2f} %")
