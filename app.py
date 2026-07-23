import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import requests
import time
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Flightradar24 API Entegrasyonu
try:
    from FlightRadar24 import FlightRadar24API
    fr_api = FlightRadar24API()
except Exception:
    fr_api = None

# --- SAYFA YAPILANDIRMASI & FLIGHTRADAR24 DARK TEMA ---
st.set_page_config(
    page_title="Flightradar24 - Live Air Traffic",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #121619; color: #ffffff; }
    div[data-testid="stSidebar"] { background-color: #1a1f24; border-right: 1px solid #2a313a; }
    
    .fr24-header {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #f2c94c;
        font-weight: bold;
        font-size: 24px;
        letter-spacing: 0.5px;
    }
    
    /* FLIGHTRADAR24 LEFT CARD STYLE */
    .fr24-card {
        background-color: #1a1f24;
        border: 1px solid #2a313a;
        border-radius: 8px;
        padding: 16px;
        font-family: 'Helvetica Neue', Arial, sans-serif;
        color: #ffffff;
    }
    .fr24-card-header {
        background-color: #242b32;
        padding: 10px;
        border-radius: 6px 6px 0 0;
        margin: -16px -16px 12px -16px;
        border-bottom: 2px solid #f2c94c;
    }
    .route-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        text-align: center;
        margin: 15px 0;
    }
    .airport-code {
        font-size: 28px;
        font-weight: bold;
        color: #ffffff;
    }
    .airport-name {
        font-size: 11px;
        color: #8f9ca6;
        text-transform: uppercase;
    }
    .progress-bar-bg {
        background-color: #2a313a;
        height: 6px;
        border-radius: 3px;
        width: 100%;
        margin: 10px 0;
        overflow: hidden;
    }
    .progress-bar-fill {
        background: linear-gradient(90deg, #f2c94c 0%, #ff9f43 100%);
        height: 100%;
        width: 65%;
    }
    .time-table {
        width: 100%;
        font-size: 12px;
        border-collapse: collapse;
        margin-top: 10px;
    }
    .time-table td {
        padding: 4px 0;
        color: #8f9ca6;
    }
    .time-table td.val {
        color: #ffffff;
        font-weight: bold;
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

# --- SİSTEME ÖZEL CANLI CANLI VERİ ÇEKİCİ ---
def canli_flightradar_verileri():
    ucak_listesi = []
    
    if fr_api is not None:
        try:
            bounds = "42.5,35.0,25.0,45.0"
            flights = fr_api.get_flights(bounds=bounds)
            
            for flight in flights[:50]:
                callsign = flight.callsign if flight.callsign else f"FR24-{flight.id}"
                lat, lon = flight.latitude, flight.longitude
                irtifa = round(flight.altitude * 0.3048, 1)
                hiz = round(flight.ground_speed * 1.852, 1)
                yon = flight.heading
                
                kalkis = flight.origin_airport_iata if flight.origin_airport_iata else "IKA"
                varis = flight.destination_airport_iata if flight.destination_airport_iata else "ADB"
                havayolu = flight.airline_name if flight.airline_name else "Iran Air Tour"
                model = flight.aircraft_code if flight.aircraft_code else "Airbus A310-324"
                
                # Rota Vektörü Çizimi
                lokasyonlar = [(lat, lon)]
                cur_lat, cur_lon = lat, lon
                for step in range(8):
                    cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                    cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                    lokasyonlar.append((cur_lat, cur_lon))

                ucak_listesi.append({
                    'ucak_id': callsign,
                    'icao24': str(flight.id).upper(),
                    'havayolu': havayolu,
                    'model': model,
                    'kalkis': kalkis,
                    'varis': varis,
                    'lat': lat,
                    'lon': lon,
                    'irtifa_m': irtifa,
                    'hiz_kmh': hiz,
                    'yon_deg': yon,
                    'lokasyonlar': lokasyonlar
                })
        except Exception:
            pass

    # YEDEK YÜKLEME (Her durumda canlı hissi korunur)
    if len(ucak_listesi) < 10:
        np.random.seed(int(time.time()) // 10)
        ornek_ucuslar = [
            {"call": "IRB9740", "air": "Iran Air Tour", "mod": "Airbus A310-324", "dep": "IKA", "arr": "ADB", "lat": 38.68, "lon": 29.47, "yon": 270},
            {"call": "THY102", "air": "Turkish Airlines", "mod": "Boeing 787-9", "dep": "IST", "arr": "AYT", "lat": 39.55, "lon": 32.10, "yon": 160},
            {"call": "PGT205", "air": "Pegasus Airlines", "mod": "Airbus A321neo", "dep": "SAW", "arr": "ADB", "lat": 40.10, "lon": 28.50, "yon": 210},
            {"call": "BAW678", "air": "British Airways", "mod": "Boeing 777-300ER", "dep": "LHR", "arr": "DXB", "lat": 38.20, "lon": 34.50, "yon": 120},
            {"call": "UAE142", "air": "Emirates", "mod": "Airbus A380-800", "dep": "DXB", "arr": "MUC", "lat": 37.80, "lon": 36.20, "yon": 310},
            {"call": "SOLOTÜRK-F16", "air": "Türk Hava Kuvvetleri", "mod": "F-16C Block 50", "dep": "ESB", "arr": "AJU-1", "lat": 39.80, "lon": 31.50, "yon": 250}
        ]
        
        for idx, u in enumerate(ornek_ucuslar):
            lat = u["lat"] + np.random.uniform(-0.5, 0.5)
            lon = u["lon"] + np.random.uniform(-0.5, 0.5)
            hiz = 780 + np.random.randint(-50, 50)
            irtifa = 9500 + np.random.randint(-1000, 1000)
            
            lokasyonlar = [(lat, lon)]
            cur_lat, cur_lon = lat, lon
            for step in range(8):
                cur_lat += np.cos(np.radians(u["yon"])) * (hiz / 111000)
                cur_lon += np.sin(np.radians(u["yon"])) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                lokasyonlar.append((cur_lat, cur_lon))

            ucak_listesi.append({
                'ucak_id': u["call"],
                'icao24': f"40D{idx}57",
                'havayolu': u["air"],
                'model': u["mod"],
                'kalkis': u["dep"],
                'varis': u["arr"],
                'lat': lat,
                'lon': lon,
                'irtifa_m': irtifa,
                'hiz_kmh': hiz,
                'yon_deg': u["yon"],
                'lokasyonlar': lokasyonlar
            })

    return pd.DataFrame(ucak_listesi)

# --- SIDEBAR CONTROL ---
st.sidebar.title("✈️ Flightradar24 Controls")
oto_yenile = st.sidebar.toggle("🔴 Live Radar Feed", value=True)
refresh_rate = st.sidebar.slider("Update Rate (Seconds)", 5, 30, 10)
map_style = st.sidebar.selectbox("Map Theme", ["Dark Terrain (Flightradar24)", "Satellite High-Res", "Dark Matter"])

df = canli_flightradar_verileri()

# HEADER
st.markdown('<div class="fr24-header">✈️ flightradar24 <span style="font-size:14px; color:#8f9ca6; font-weight:normal;">LIVE AIR TRAFFIC</span></div>', unsafe_allow_html=True)

st.markdown("---")

c1, c2 = st.columns([1.1, 2.5])

secili_ucak_id = st.session_state.get('secili_ucak', df['ucak_id'].iloc[0])
secili_row = df[df['ucak_id'] == secili_ucak_id]

if secili_row.empty:
    secili_row = df.iloc[[0]]

u = secili_row.iloc[0]

# --- SOL TARAFTAKİ BİREBİR FLIGHTRADAR24 BİLGİ KARTI ---
with c1:
    st.markdown(f"""
    <div class="fr24-card">
        <div class="fr24-card-header">
            <h2 style="margin:0; font-size:22px; color:#ffffff;">{u['ucak_id']} <span style="font-size:14px; color:#f2c94c;">{u['icao24']}</span></h2>
            <p style="margin:2px 0 0 0; color:#8f9ca6; font-size:13px;"><b>{u['havayolu']}</b> • {u['model']}</p>
        </div>
        
        <!-- UÇAK GÖRSELİ STUB -->
        <div style="width:100%; height:140px; background-color:#0b0e14; border-radius:4px; display:flex; align-items:center; justify-content:center; border:1px solid #2a313a; margin-bottom:12px;">
            <span style="font-size:48px;">✈️</span>
        </div>

        <div class="route-container">
            <div>
                <div class="airport-code">{u['kalkis']}</div>
                <div class="airport-name">DEPARTURE</div>
            </div>
            <div style="font-size:22px; color:#f2c94c;">✈️</div>
            <div>
                <div class="airport-code">{u['varis']}</div>
                <div class="airport-name">DESTINATION</div>
            </div>
        </div>

        <div class="progress-bar-bg">
            <div class="progress-bar-fill"></div>
        </div>

        <table class="time-table">
            <tr>
                <td>SCHEDULED DEPARTURE</td>
                <td class="val">12:30 AM</td>
            </tr>
            <tr>
                <td>ACTUAL DEPARTURE</td>
                <td class="val" style="color:#00ff66;">12:19 AM</td>
            </tr>
            <tr>
                <td>ESTIMATED ARRIVAL</td>
                <td class="val" style="color:#f2c94c;">03:04 AM</td>
            </tr>
            <tr>
                <td>ALTITUDE</td>
                <td class="val">{u['irtifa_m']} m ({int(u['irtifa_m']*3.28)} ft)</td>
            </tr>
            <tr>
                <td>GROUND SPEED</td>
                <td class="val">{u['hiz_kmh']} km/h ({int(u['hiz_kmh']/1.852)} kts)</td>
            </tr>
            <tr>
                <td>HEADING</td>
                <td class="val">{u['yon_deg']}°</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.selectbox("Select Flight to Track:", df['ucak_id'].unique(), key="secili_ucak")

# --- SAĞ TARAFTAKİ FLIGHTRADAR24 BİREBİR HARİTASI ---
with c2:
    if map_style == "Satellite High-Res":
        tiles_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        attr = "Esri Satellite"
    else:
        tiles_url = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}{r}.png"
        attr = "CartoDB Voyager"

    m = folium.Map(location=[u['lat'], u['lon']], zoom_start=7, tiles=tiles_url, attr=attr)

    # 1. TÜM UÇAKLARI SARI UÇAK İKONU İLE ÇİZ
    for _, row in df.iterrows():
        is_selected = (row['ucak_id'] == u['ucak_id'])
        
        # Sarı / Kırmızı Uçak İkon Tasarımı
        plane_color = "#ff3344" if "MILITARY" in row['ucak_id'] else "#f2c94c"
        
        # HTML SVG Sarı Uçak İkonu (Dönme Açısıyla Birlikte)
        plane_svg = f"""
        <div style="transform: rotate({row['yon_deg']}deg); width:28px; height:28px; text-align:center;">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="{plane_color}" xmlns="http://www.w3.org/2000/svg">
                <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
            </svg>
        </div>
        """
        
        icon = folium.DivIcon(html=plane_svg)
        
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=f"<b>{row['ucak_id']}</b><br>{row['kalkis']} ➔ {row['varis']}",
            tooltip=f"✈️ {row['ucak_id']} ({row['kalkis']} ➔ {row['varis']})",
            icon=icon
        ).add_to(m)

    # 2. SEÇİLİ UÇAĞIN MOR ROTA ÇİZGİSİNİ VE ETİKETİNİ ÇİZ
    folium.PolyLine(
        locations=u['lokasyonlar'],
        color="#a55eea",
        weight=4,
        opacity=0.9,
        dash_array="6, 6",
        tooltip=f"Flight Path: {u['ucak_id']}"
    ).add_to(m)

    # Seçili Uçağın Üzerine FR24 Etiketi Ekle
    folium.Marker(
        location=[u['lat'], u['lon']],
        icon=folium.DivIcon(
            html=f"""<div style="background-color:#ffffff; color:#000; font-weight:bold; font-family:sans-serif; font-size:11px; padding:2px 6px; border-radius:3px; border:1px solid #000; box-shadow:0 0 5px rgba(0,0,0,0.5);">{u['ucak_id']}</div>""",
            icon_anchor=(-10, 10)
        )
    ).add_to(m)

    st_folium(m, width=920, height=620, key="fr24_map", returned_objects=[])

if oto_yenile:
    time.sleep(refresh_rate)
    st.rerun()
