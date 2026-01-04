import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="City Ops Dashboard", layout="wide")

@st.cache_data
def load_data(csv_path="city_metrics.csv"):
    df = pd.read_csv(csv_path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df

# Load data
try:
    df = load_data()
except Exception as e:
    st.error("Could not load city_metrics.csv. Please place it next to app.py. Error: " + str(e))
    st.stop()

# Basic required columns with defaults if missing
required_cols = [
    "date", "hour", "city", "dau", "opd", "fod",
    "efficiency", "avg_login_hours", "orders", "login_hours"
]
for col in required_cols:
    if col not in df.columns:
        df[col] = 0

# Sidebar filters
st.sidebar.title("Filters")
city_options = sorted(df["city"].dropna().unique().tolist())
if not city_options:
    city_options = ["Guwahati", "Bhubaneswar"]
city = st.sidebar.selectbox("City", city_options)

min_date = df["date"].min()
max_date = df["date"].max()
if pd.isna(min_date) or pd.isna(max_date):
    min_date = pd.to_datetime("2025-01-01")
    max_date = pd.to_datetime("2025-01-07")

date_range = st.sidebar.date_input(
    "Date range",
    value=[min_date, max_date]
)

if isinstance(date_range, list) or isinstance(date_range, tuple):
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[-1])
else:
    start_date = pd.to_datetime(date_range)
    end_date = pd.to_datetime(date_range)

city_df = df[(df["city"] == city) & (df["date"] >= start_date) & (df["date"] <= end_date)].copy()

if city_df.empty:
    st.warning("No data for selected filters.")
    st.stop()

city_df["date"] = pd.to_datetime(city_df["date"]).dt.date

st.title("City Operations Dashboard")
st.subheader("Daily and Hourly Tracking - " + city)

# Aggregate daily
daily = city_df.groupby("date").agg({
    "dau": "sum",
    "opd": "sum",
    "fod": "sum",
    "efficiency": "mean",
    "avg_login_hours": "mean",
    "orders": "sum",
    "login_hours": "sum"
}).reset_index()

if not daily.empty:
    daily["orders_per_hour"] = np.where(
        daily["login_hours"] > 0,
        daily["orders"] / daily["login_hours"],
        0
    )

# Today / yesterday context (based on max date in filtered data)
latest_date = max(daily["date"])
prev_date = latest_date - pd.Timedelta(days=1)

latest_row = daily[daily["date"] == latest_date].tail(1)
prev_row = daily[daily["date"] == prev_date].tail(1)

col1, col2, col3, col4 = st.columns(4)

def pct_change(curr, prev):
    if prev is None or prev == 0:
        return 0
    return (curr - prev) / prev * 100.0

if not latest_row.empty:
    latest_dau = float(latest_row["dau"].iloc[0])
    latest_opd = float(latest_row["opd"].iloc[0])
    latest_eff = float(latest_row["efficiency"].iloc[0])
    latest_oph = float(latest_row["orders_per_hour"].iloc[0])
else:
    latest_dau = latest_opd = latest_eff = latest_oph = 0

if not prev_row.empty:
    prev_dau = float(prev_row["dau"].iloc[0])
    prev_opd = float(prev_row["opd"].iloc[0])
    prev_eff = float(prev_row["efficiency"].iloc[0])
    prev_oph = float(prev_row["orders_per_hour"].iloc[0])
else:
    prev_dau = prev_opd = prev_eff = prev_oph = 0

col1.metric("DAU", int(latest_dau), str(round(pct_change(latest_dau, prev_dau), 1)) + "% vs Yest")
col2.metric("OPD", int(latest_opd), str(round(pct_change(latest_opd, prev_opd), 1)) + "% vs Yest")
col3.metric("Efficiency", round(latest_eff, 2), str(round(pct_change(latest_eff, prev_eff), 1)) + "% vs Yest")
col4.metric("Orders / Hour", round(latest_oph, 2), str(round(pct_change(latest_oph, prev_oph), 1)) + "% vs Yest")

st.markdown("---")

# Daily trend chart
if len(daily) > 1:
    fig_daily = px.line(
        daily,
        x="date",
        y=["opd", "orders_per_hour"],
        markers=True,
        labels={"value": "Value", "date": "Date", "variable": "Metric"},
        title="Daily OPD and Orders per Hour Trend"
    )
    st.plotly_chart(fig_daily, use_container_width=True)

# Hourly same-day vs yesterday comparison
hourly_df = city_df.copy()

latest_day_data = hourly_df[hourly_df["date"] == latest_date]
yest_day_data = hourly_df[hourly_df["date"] == prev_date]

if not latest_day_data.empty and not yest_day_data.empty:
    latest_day_data["label"] = "Today"
    yest_day_data["label"] = "Yesterday"
    cmp_df = pd.concat([latest_day_data, yest_day_data], ignore_index=True)

    fig_hourly = px.line(
        cmp_df,
        x="hour",
        y="orders",
        color="label",
        markers=True,
        title="Hourly Orders: Today vs Yesterday"
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

st.markdown("---")

# Week on Week comparison for same weekday
city_df["weekday"] = pd.to_datetime(city_df["date"]).astype("datetime64[D]").map(lambda x: x.weekday())

wow_daily = city_df.groupby(["weekday", "date"]).agg({"orders": "sum"}).reset_index()

if not wow_daily.empty:
    fig_wow = px.line(
        wow_daily,
        x="date",
        y="orders",
        color="weekday",
        markers=True,
        title="Week on Week Orders (by Weekday)"
    )
    st.plotly_chart(fig_wow, use_container_width=True)

st.caption("Simple ready-to-run dashboard. Plug in your city_metrics.csv with Guwahati and Bhubaneswar data.")