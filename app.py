import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Climate Disaster Early Warning", layout="wide")

# ---- Same regions as your Colab ----
regions = {
    "Chennai, India": {"lat": 13.0827, "lon": 80.2707, "disaster_focus": "Flood"},
    "Manila, Philippines": {"lat": 14.5995, "lon": 120.9842, "disaster_focus": "Flood/Landslide"},
}

# ---- Same fetch function as before ----
def get_live_data(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m,pressure_msl,soil_moisture_0_to_1cm"
        "&hourly=precipitation,soil_moisture_0_to_1cm"
        "&past_days=2&timezone=auto"
    )
    data = requests.get(url).json()
    current = data["current"]
    rainfall_48h = sum(v for v in data["hourly"]["precipitation"] if v is not None)
    return {
        "temperature_c": current["temperature_2m"],
        "humidity_pct": current["relative_humidity_2m"],
        "current_rain_mm": current["precipitation"],
        "rainfall_last_48h_mm": round(rainfall_48h, 1),
        "wind_speed_kmh": current["wind_speed_10m"],
        "wind_gusts_kmh": current["wind_gusts_10m"],
        "pressure_msl": current["pressure_msl"],
        "soil_moisture": current["soil_moisture_0_to_1cm"],
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

def compute_flood_risk(d):
    score = 0
    if d["rainfall_last_48h_mm"] > 100: score += 40
    elif d["rainfall_last_48h_mm"] > 50: score += 25
    elif d["rainfall_last_48h_mm"] > 20: score += 10
    if d["soil_moisture"] is not None:
        if d["soil_moisture"] > 0.35: score += 30
        elif d["soil_moisture"] > 0.25: score += 15
    if d["current_rain_mm"] > 5: score += 20
    elif d["current_rain_mm"] > 1: score += 10
    if d["wind_gusts_kmh"] > 60: score += 10
    return min(score, 100)

def risk_label(score):
    if score >= 70: return "HIGH", "#8B0000"
    elif score >= 40: return "MODERATE", "#D9822B"
    elif score >= 15: return "LOW", "#D9B31C"
    else: return "MINIMAL", "#1B7A3D"

# ---- Header ----
st.title("🌍 Climate Disaster Early Warning System")
st.caption("Live monitoring for flood & landslide risk in vulnerable city regions")

if st.button("🔄 Refresh Live Data"):
    st.rerun()

# ---- City cards ----
cols = st.columns(len(regions))

for col, (city, info) in zip(cols, regions.items()):
    with col:
        live = get_live_data(info["lat"], info["lon"])
        score = compute_flood_risk(live)
        label, color = risk_label(score)

        st.markdown(
            f"""
            <div style="background-color:{color}22; border-left: 6px solid {color};
                        padding: 16px; border-radius: 8px;">
                <h3 style="margin:0;">{city}</h3>
                <p style="margin:0; color:gray;">Focus: {info['disaster_focus']}</p>
                <h1 style="color:{color}; margin:8px 0;">{score}% — {label}</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.progress(score / 100)

        m1, m2 = st.columns(2)
        m1.metric("Temperature (°C)", live["temperature_c"])
        m1.metric("Humidity (%)", live["humidity_pct"])
        m1.metric("Wind Speed (km/h)", live["wind_speed_kmh"])
        m2.metric("Rainfall 48h (mm)", live["rainfall_last_48h_mm"])
        m2.metric("Soil Moisture (m³/m³)", live["soil_moisture"])
        m2.metric("Wind Gusts (km/h)", live["wind_gusts_kmh"])

        st.caption(f"Last updated: {live['fetched_at']}")
