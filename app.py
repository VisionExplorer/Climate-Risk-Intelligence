import streamlit as st
import requests
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="Climate Disaster Early Warning", layout="wide")

regions = {
    "Chennai, India": {"lat": 13.0827, "lon": 80.2707, "disaster_focus": "Flood"},
    "Manila, Philippines": {"lat": 14.5995, "lon": 120.9842, "disaster_focus": "Flood/Landslide"},
}

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
        "local_time": current["time"].replace("T", " "),
        "timezone_label": data["timezone_abbreviation"],
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
    if score >= 70: return "HIGH", "#8B0000", "⚠️ Flood/Landslide Risk"
    elif score >= 40: return "MODERATE", "#D9822B", "🌧️ Heavy Rain"
    elif score >= 15: return "LOW", "#D9B31C", "🌦️ Light Rain"
    else: return "MINIMAL", "#1B7A3D", "☀️ Clear"

st.title("🌍 Climate Disaster Early Warning System")
st.caption("Live monitoring for flood & landslide risk in vulnerable city regions")

if st.button("🔄 Refresh Live Data"):
    st.rerun()

# ---- Collect data for all cities first (needed for both cards + map) ----
city_data = []
for city, info in regions.items():
    live = get_live_data(info["lat"], info["lon"])
    score = compute_flood_risk(live)
    label, color, condition_icon = risk_label(score)
    city_data.append({
        "city": city, "lat": info["lat"], "lon": info["lon"],
        "disaster_focus": info["disaster_focus"],
        "score": score, "label": label, "color": color,
        "condition_icon": condition_icon, **live,
    })

# ---- Map with risk-colored markers ----
st.subheader("📍 Live Risk Map")

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

map_df = pd.DataFrame([
    {"lat": c["lat"], "lon": c["lon"], "city": c["city"],
     "condition": c["condition_icon"], "risk": f"{c['score']}% ({c['label']})",
     "color": hex_to_rgb(c["color"])}
    for c in city_data
])

layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_df,
    get_position=["lon", "lat"],
    get_fill_color="color",
    get_radius=40000,
    pickable=True,
)
view_state = pdk.ViewState(latitude=14, longitude=100, zoom=2.3)
st.pydeck_chart(pdk.Deck(
    layers=[layer], initial_view_state=view_state,
    tooltip={"text": "{city}\n{condition}\nRisk: {risk}"},
))

# ---- City cards ----
cols = st.columns(len(city_data))
for col, c in zip(cols, city_data):
    with col:
        st.markdown(
            f"""
            <div style="background-color:{c['color']}22; border-left: 6px solid {c['color']};
                        padding: 16px; border-radius: 8px;">
                <h3 style="margin:0;">{c['city']}</h3>
                <p style="margin:0; color:gray;">Focus: {c['disaster_focus']}</p>
                <h2 style="margin:6px 0;">{c['condition_icon']}</h2>
                <h1 style="color:{c['color']}; margin:8px 0;">{c['score']}% — {c['label']}</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(c["score"] / 100)

        m1, m2 = st.columns(2)
        m1.metric("Temperature (°C)", c["temperature_c"])
        m1.metric("Humidity (%)", c["humidity_pct"])
        m1.metric("Wind Speed (km/h)", c["wind_speed_kmh"])
        m2.metric("Rainfall 48h (mm)", c["rainfall_last_48h_mm"])
        m2.metric("Soil Moisture (m³/m³)", c["soil_moisture"])
        m2.metric("Wind Gusts (km/h)", c["wind_gusts_kmh"])
          # ---- NEW: Alert pipeline simulation ----
        if c["score"] >= 70:
            st.error(f"🚨 ALERT TRIGGERED: Simulated SMS/community alert dispatched to local wards and disaster management authority")
        elif c["score"] >= 40:
            st.warning(f"⚠️ WATCH STATUS: Monitoring team notified, community on standby")
        else:
            st.success(f"✅ No alert action needed")
       
        st.caption(f"City local time: {c['local_time']} ({c['timezone_label']})")
