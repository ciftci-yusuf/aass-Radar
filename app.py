import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from sklearn.ensemble import RandomForestClassifier
import requests
import time
import pydeck as pdk
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

# --- SAYFA YAPILANDIRMASI & MILITARY C4ISR TEMA ---
st.set_page_config(
    page_title="MİLHAD-C4ISR - Entegre Hava & Deniz Savunma Komuta Merkezi",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #0c1014; color: #ffffff; }
    .stMetric { background-color: #141a20; border: 1px solid #00ff66; padding: 12px; border-radius: 4px; box-shadow: 0 0 10px rgba(0,255,102,0.15); }
    div[data-testid="stSidebar"] { background-color: #080c10; border-right: 1px solid #1f2830; }
    
    .hud-title {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        color: #00ff66;
        font-size: 24px;
        font-weight: bold;
        letter-spacing: 1px;
        text-shadow: 0 0 8px rgba(0,255,102,0.4);
    }
    .threat-hud {
        background: linear-gradient(90deg, #721c24 0%, #2c0b0e 100%);
        color: #ffffff;
        padding: 16px 24px;
        border-radius: 6px;
        border: 2px solid #ff0055;
        box-shadow: 0 0 20px rgba(255,0,85,0.5);
        font-family: monospace;
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .status-good {
        background: linear-gradient(90deg, #002b11 0%, #001006 100%);
        color: #00ff66;
        padding: 14px 24px;
        border-radius: 4px;
        border: 1px solid #00ff66;
        box-shadow: 0 0 15px rgba(0,255,102,0.2);
        font-family: monospace;
        font-size: 15px;
        margin-bottom: 20px;
    }
    
    /* FLIGHTRADAR24 BİREBİR SOL KART TASARIMI */
    .fr24-card {
        background-color: #141a20;
        border: 1px solid #28323e;
        border-radius: 8px;
        padding: 16px;
        font-family: 'Helvetica Neue', Arial, sans-serif;
        color: #ffffff;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .fr24-card-header {
        background-color: #1d252e;
        padding: 10px 14px;
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
        background-color: #28323e;
        height: 6px;
        border-radius: 3px;
        width: 100%;
        margin: 10px 0;
        overflow: hidden;
    }
    .progress-bar-fill {
        background: linear-gradient(90deg, #f2c94c 0%, #ff9f43 100%);
        height: 100%;
        width: 60%;
    }
    .time-table {
        width: 100%;
        font-size: 12px;
        border-collapse: collapse;
        margin-top: 10px;
    }
    .time-table td {
        padding: 5px 0;
        color: #8f9ca6;
        border-bottom: 1px solid #1f2830;
    }
    .time-table td.val {
        color: #ffffff;
        font-weight: bold;
        text-align: right;
    }
    
    .voice-card {
        background: #090e12;
        border: 1px solid #00ff66;
        padding: 15px;
        border-radius: 6px;
        margin-top: 15px;
        box-shadow: 0 0 10px rgba(0,255,102,0.2);
    }
    .login-box {
        background-color: #141a20;
        border: 1px solid #00ff66;
        padding: 30px;
        border-radius: 8px;
        max-width: 450px;
        margin: 50px auto;
        box-shadow: 0 0 20px rgba(0,255,102,0.3);
        font-family: monospace;
    }
    .live-stream-btn {
        display: block;
        width: 100%;
        background: #f2c94c;
        color: #000;
        text-align: center;
        padding: 10px;
        border-radius: 4px;
        font-weight: bold;
        text-decoration: none;
        margin-top: 12px;
    }
    .radar-container {
        position: relative;
        width: 100%;
        height: 90px;
        background: #050a0d;
        border: 1px solid #00ff66;
        border-radius: 6px;
        overflow: hidden;
        margin-bottom: 15px;
    }
    .radar-sweep {
        position: absolute;
        top: 50%;
        left: 50%;
        width: 160px;
        height: 160px;
        margin-top: -80px;
        margin-left: -80px;
        border-radius: 50%;
        border: 1px solid rgba(0,255,102,0.3);
        background: conic-gradient(from 0deg, rgba(0, 255, 102, 0.4) 0deg, transparent 60deg);
        animation: radarSpin 3s linear infinite;
    }
    @keyframes radarSpin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    </style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None

if not st.session_state["logged_in"]:
    st.markdown('<h1 class="hud-title" style="text-align:center;">🛡️ MİLHAD-C4ISR KOMUTA MERKEZİ GİRİŞİ</h1>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.subheader("🔑 Kimlik Doğrulama Paneli")
        username = st.text_input("Kullanıcı Adı / Sicil No:")
        password = st.text_input("Giriş Parolası:", type="password")
        
        c1, c2 = st.columns(2)
        if c1.button("🔑 GİRİŞ YAP", type="primary"):
            if username == "admin" and password == "1234":
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = "Komutan"
                st.session_state["user_name"] = "Hava Savunma Komutanı"
                st.rerun()
            elif username == "operator" and password == "1234":
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = "Operatör"
                st.session_state["user_name"] = "Radar Nöbetçi Operatörü"
                st.rerun()
            else:
                st.error("❌ Geçersiz Kimlik Bilgisi!")
                
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

st.sidebar.markdown(f"👤 **Aktif Kullanıcı:** {st.session_state['user_name']}")
st.sidebar.markdown(f"🎖️ **Yetki Rolü:** `{st.session_state['user_role']}`")

if st.sidebar.button("🚪 Oturumu Kapat"):
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.rerun()

st.markdown('<div class="hud-title">🛡️ MİLHAD-C4ISR <span style="font-size:16px; color:#8f9ca6; font-weight:normal;">| Entegre Hava Sahası, Radar & Deniz Savunma Komuta Merkezi</span></div>', unsafe_allow_html=True)
st.caption("Milli İhlal Erken İhbar, Flightradar24 Canlı Akış, AESA Radar Füzyonu & Taktik Telsiz")

# UÇAK GEMİLERİ KATMANI
UCAK_GEMILERI = [
    {
        "kod": "TCG-ANADOLU",
        "ad": "TCG Anadolu (L-400) - Türkiye SİHA Gemisi",
        "ülke": "Türkiye",
        "lat": 36.520,
        "lon": 30.750,
        "konuşlu": "Bayraktar TB3, KIZILELMA",
        "menzil_km": 200,
        "is_friendly": True
    },
    {
        "kod": "CVN-78-FORD",
        "ad": "USS Gerald R. Ford (CVN-78) Carrier Group",
        "ülke": "ABD",
        "lat": 35.800,
        "lon": 28.100,
        "konuşlu": "F-35C, F/A-18E Super Hornet",
        "menzil_km": 350,
        "is_friendly": False
    }
]

RADAR_ISTASYONLARI = [
    {"kod": "RADAR-KURECIK", "ad": "Kürecik AN/TPY-2 Erken İhbar Radarı", "lat": 38.351, "lon": 37.802, "menzil_km": 400},
    {"kod": "RADAR-AHLATLIBEL", "ad": "Ankara Ahlatlıbel Hava Radar Mevzii", "lat": 39.815, "lon": 32.812, "menzil_km": 300},
    {"kod": "RADAR-CANAKKALE", "ad": "Çanakkale Radar Komutanlığı", "lat": 40.150, "lon": 26.410, "menzil_km": 250},
    {"kod": "RADAR-DATCA", "ad": "Muğla Datça Radar İstasyonu", "lat": 36.720, "lon": 27.680, "menzil_km": 250},
    {"kod": "RADAR-MERZIFON", "ad": "Merzifon AESA Taktik Radarı", "lat": 40.830, "lon": 35.510, "menzil_km": 350}
]

HAVALIMANLARI = [
    {"kod": "ADA", "ad": "Adana Havalimanı", "lat": 36.982, "lon": 35.280, "tip": "Sivil"},
    {"kod": "ESB", "ad": "Ankara Esenboğa", "lat": 40.128, "lon": 32.995, "tip": "Sivil Başkent Hub"},
    {"kod": "AYT", "ad": "Antalya Havalimanı", "lat": 36.898, "lon": 30.800, "tip": "Sivil Uluslararası"},
    {"kod": "IST", "ad": "İstanbul Havalimanı", "lat": 41.275, "lon": 28.751, "tip": "Sivil Ana Hub"},
    {"kod": "SAW", "ad": "Sabiha Gökçen", "lat": 40.898, "lon": 29.309, "tip": "Sivil Hub"},
    {"kod": "ADB", "ad": "İzmir Adnan Menderes", "lat": 38.292, "lon": 27.157, "tip": "Sivil Hub"},
    {"kod": "TZX", "ad": "Trabzon Havalimanı", "lat": 40.995, "lon": 39.789, "tip": "Sivil"},
    {"kod": "AJU-1", "ad": "1. Ana Jet Üssü (Eskişehir)", "lat": 39.786, "lon": 30.582, "tip": "🎖️ TSK Askeri Üs"},
    {"kod": "AJU-5", "ad": "5. Ana Jet Üssü (Merzifon)", "lat": 40.829, "lon": 35.521, "tip": "🎖️ TSK Askeri Üs"},
    {"kod": "INCIRLIK", "ad": "İncirlik Hava Üssü", "lat": 37.001, "lon": 35.425, "tip": "🎖️ TSK/NATO Üssü"}
]

def turkiye_sinirlari_icinde_mi(lat, lon):
    return (35.8 <= lat <= 42.1) and (25.6 <= lon <= 44.8)

def onleme_noktasi_hesapla(target_lat, target_lon, target_speed, target_heading, base_lat, base_lon, jet_speed=1800):
    t_rad = np.radians(target_heading)
    v_target_x = target_speed * np.sin(t_rad)
    v_target_y = target_speed * np.cos(t_rad)
    
    dx = (target_lon - base_lon) * 111000
    dy = (target_lat - base_lat) * 111000
    
    t_intercept = np.sqrt(dx**2 + dy**2) / (jet_speed * 1000 / 3600)
    
    intercept_lat = target_lat + (v_target_y * (t_intercept / 3600)) / 111
    intercept_lon = target_lon + (v_target_x * (t_intercept / 3600)) / (111 * np.cos(np.radians(target_lat)))
    
    return intercept_lat, intercept_lon, round(t_intercept, 1)

# GERÇEK ZAMANLI FLIGHTRADAR24 VERİ SERVİSİ
def flightradar24_canli_veri_getir(radar_fuzyon_aktif):
    ucak_listesi = []
    
    if fr_api is not None:
        try:
            bounds = "42.5,35.0,25.0,45.0"
            flights = fr_api.get_flights(bounds=bounds)
            
            for flight in flights[:60]:
                callsign = flight.callsign if flight.callsign else f"FR24-{flight.id}"
                lat, lon = flight.latitude, flight.longitude
                irtifa = round(flight.altitude * 0.3048, 1)
                hiz = round(flight.ground_speed * 1.852, 1)
                yon = flight.heading
                
                kalkis = flight.origin_airport_iata if flight.origin_airport_iata else "IST"
                varis = flight.destination_airport_iata if flight.destination_airport_iata else "AYT"
                havayolu = flight.airline_name if flight.airline_name else "Turkish Airlines"
                model = flight.aircraft_code if flight.aircraft_code else "B738"
                
                is_uav = "BAYRAKTAR" in callsign or "AKINCI" in callsign or "ANKA" in callsign
                is_tsk = is_uav or "TUAF" in callsign or "TURK" in callsign
                is_foreign_threat = (not is_tsk) and ("F16" in callsign or "F35" in callsign or "MIL" in callsign or "NAVY" in callsign)
                
                lokasyonlar = [(lat, lon)]
                cur_lat, cur_lon = lat, lon
                for step in range(10):
                    cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                    cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                    lokasyonlar.append((cur_lat, cur_lon))
                    
                orta_lat, orta_lon = 39.1, 33.5
                mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
                sinir_ihlal = turkiye_sinirlari_icinde_mi(lat, lon) and is_foreign_threat

                ucak_listesi.append({
                    'ucak_id': callsign,
                    'icao24': str(flight.id).upper(),
                    'havayolu': havayolu,
                    'model': model,
                    'is_uav': is_uav,
                    'is_tsk': is_tsk,
                    'is_ghost': False,
                    'is_foreign_threat': is_foreign_threat,
                    'sinir_ihlal': sinir_ihlal,
                    'kalkis': kalkis,
                    'varis': varis,
                    'lat': lat,
                    'lon': lon,
                    'irtifa_m': irtifa,
                    'hiz_kmh': hiz,
                    'yon_deg': yon,
                    'mesafe_deg': mesafe,
                    'lokasyonlar': lokasyonlar
                })
        except Exception:
            pass

    # OPENSKY CANLI YEDEK (FR24 Limiti veya Bağlantı Yavaşlığında Çalışır)
    if len(ucak_listesi) < 5:
        url = "https://opensky-network.org/api/states/all?lamin=35.0&lomin=25.0&lamax=42.5&lomax=45.0"
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
            if response.status_code == 200:
                data = response.json()
                states = data.get("states")
                if states:
                    for idx, state in enumerate(states):
                        if state[5] is not None and state[6] is not None:
                            callsign = state[1].strip() if (state[1] and state[1].strip()) else f"LIVE-{state[0].upper()}"
                            lon, lat = state[5], state[6]
                            irtifa = round(state[7] if state[7] is not None else 7200, 1)
                            hiz = round((state[9] * 3.6) if state[9] is not None else 710, 1)
                            yon = state[10] if state[10] is not None else 90
                            ulke = state[2] if state[2] else "Türkiye"
                            
                            is_uav = "BAYRAKTAR" in callsign or "AKINCI" in callsign
                            is_tsk = is_uav or "TUAF" in callsign or ulke == "Turkey"
                            is_foreign_threat = (not is_tsk) and ("F16" in callsign or "MIL" in callsign)
                            
                            lokasyonlar = [(lat, lon)]
                            cur_lat, cur_lon = lat, lon
                            for step in range(10):
                                cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                                cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                                lokasyonlar.append((cur_lat, cur_lon))
                                
                            orta_lat, orta_lon = 39.1, 33.5
                            mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
                            sinir_ihlal = turkiye_sinirlari_icinde_mi(lat, lon) and is_foreign_threat
                            
                            ucak_listesi.append({
                                'ucak_id': callsign,
                                'icao24': str(state[0]).upper(),
                                'havayolu': "Türk Hava Yolları" if "THY" in callsign else f"{ulke} Hava Trafiği",
                                'model': "A320",
                                'is_uav': is_uav,
                                'is_tsk': is_tsk,
                                'is_ghost': False,
                                'is_foreign_threat': is_foreign_threat,
                                'sinir_ihlal': sinir_ihlal,
                                'kalkis': "IST",
                                'varis': "AYT",
                                'lat': lat,
                                'lon': lon,
                                'irtifa_m': irtifa,
                                'hiz_kmh': hiz,
                                'yon_deg': yon,
                                'mesafe_deg': mesafe,
                                'lokasyonlar': lokasyonlar
                            })
        except Exception:
            pass

    # YABANCI SAVAŞ UÇAĞI SINIR İHLAL SİMÜLASYONU
    if radar_fuzyon_aktif:
        np.random.seed(int(time.time()) // 5)
        for g in range(1):
            lat, lon = 38.2, 26.8
            hiz, yon, irtifa = 1450, 85, 2100
            orta_lat, orta_lon = 39.1, 33.5
            mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
            
            lokasyonlar = [(lat, lon)]
            cur_lat, cur_lon = lat, lon
            for step in range(10):
                cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                lokasyonlar.append((cur_lat, cur_lon))

            ucak_listesi.append({
                'ucak_id': "YABANCI-MILITARY-X",
                'icao24': "NO-SQUAWK",
                'havayolu': "⚠️ UNIDENTIFIED HOSTILE",
                'model': "F-18",
                'is_uav': False,
                'is_tsk': False,
                'is_ghost': True,
                'is_foreign_threat': True,
                'sinir_ihlal': True,
                'kalkis': "CVN-78",
                'varis': "MİLLİ HAVA SAHASI",
                'lat': lat,
                'lon': lon,
                'irtifa_m': round(irtifa, 1),
                'hiz_kmh': round(hiz, 1),
                'yon_deg': round(yon, 1),
                'mesafe_deg': mesafe,
                'lokasyonlar': lokasyonlar
            })
            
    return pd.DataFrame(ucak_listesi)

def pdf_rapor_olustur(dataframe, riskliler):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#003366"), spaceAfter=12)
    story.append(Paragraph("MİLHAD-C4ISR RESMİ TAKTİK MÜDAHALE RAPORU", title_style))
    story.append(Paragraph(f"<b>Rapor Tarihi:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Paragraph(f"<b>Raporu Oluşturan Yetkili:</b> {st.session_state.get('user_name', 'Bilinmiyor')} ({st.session_state.get('user_role', 'Rol Yok')})", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph(f"<b>Toplam Takip Edilen Canlı FR24 Vektörü:</b> {len(dataframe)}", styles['Normal']))
    story.append(Paragraph(f"<b>Tespit Edilen Tehdit/İhlal Sayısı:</b> {len(riskliler)}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>🚨 KRİTİK İHLAL & TEHDİT LİSTESİ</b>", styles['Heading2']))
    
    table_data = [["Çağrı Kodu", "Birlik/Operatör", "Kalkış ➔ Varış", "İrtifa (m)", "Risk Skoru"]]
    for _, row in riskliler.iterrows():
        table_data.append([row['ucak_id'], row['havayolu'], f"{row['kalkis']} ➔ {row['varis']}", str(row['irtifa_m']), f"%{row['risk_skoru']*100:.1f}"])

    if len(table_data) > 1:
        t = Table(table_data, colWidths=[90, 130, 130, 70, 70])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#721c24")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8d7da")),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer

# --- SIDEBAR KONTROL PANELİ ---
st.sidebar.title("🎛️ MİLHAD-C4ISR PANELS")
oto_yenile = st.sidebar.toggle("🔴 CANLI RADAR TARAMASI", value=True)
refresh_rate = st.sidebar.slider("Tarama Frekansı (Saniye)", 5, 30, 10)
radar_fuzyon = st.sidebar.toggle("📡 AESA Radar Füzyonu (Gölge Temas)", value=True)
goster_radarlar = st.sidebar.checkbox("📡 Radar İstasyonlarını Göster", value=True)
goster_ucak_gemileri = st.sidebar.checkbox("🚢 Uçak Gemilerini Göster", value=True)
sar_katmani = st.sidebar.toggle("🛰️ SAR Uydu Katmanı", value=False)
sadece_tsk = st.sidebar.checkbox("🎖️ Sadece TSK Filosunu Göster", value=False)

if st.session_state["user_role"] == "Komutan":
    threshold = st.sidebar.slider("AI Duyarlılık Eşiği (Komutan Yetkisi)", 0.10, 0.90, 0.25, step=0.05)
else:
    threshold = 0.25
    st.sidebar.info("🔒 AI Duyarlılık Eşiği Komutan yetkisine kilitlidir.")

df = flightradar24_canli_veri_getir(radar_fuzyon)

if sadece_tsk:
    df = df[df['is_tsk'] == True].reset_index(drop=True)

if not df.empty:
    X = df[['lat', 'lon', 'irtifa_m', 'hiz_kmh', 'yon_deg', 'mesafe_deg']]
    y = [1 if (row['sinir_ihlal'] or row['is_ghost'] or (row['mesafe_deg'] < 1.8 and (30 <= row['yon_deg'] <= 120))) else 0 for _, row in df.iterrows()]

    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    if len(set(y)) > 1:
        rf.fit(X, y)
        df['risk_skoru'] = rf.predict_proba(X)[:, 1]
    else:
        df['risk_skoru'] = [0.08] * len(df)
        
    df['alarm'] = df['risk_skoru'] >= threshold
    riskli_df = df[df['alarm']].sort_values(by='risk_skoru', ascending=False)
    ihlal_df = df[df['sinir_ihlal']]

    if len(ihlal_df) > 0:
        st.markdown(f'<div class="threat-hud">🚨 [MİLLİ SINIR İHLAL ALARMI] Türkiye Dışından Gelen {len(ihlal_df)} Yabancı Savaş Unsuru Sınırı İhlal Etti! F-16 Önleme Jeti Görevlendirildi!</div>', unsafe_allow_html=True)
    elif len(riskli_df) > 0:
        st.markdown(f'<div class="threat-hud">⚠️ [TAKTİK UYARI] {len(riskli_df)} Yabancı Hava Aracı Sınır Bölgesinde!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-good">✅ [MİLLİ SINIRLAR EMNİYETTE] Türkiye Hava ve Deniz Sahasını İhlal Eden Yabancı Unsur Yok.</div>', unsafe_allow_html=True)

    st.markdown("""
        <div class="radar-container">
            <div class="radar-sweep"></div>
            <div style="position:absolute; bottom:5px; left:10px; color:#00ff66; font-family:monospace; font-size:11px;">📡 MİLHAD-C4ISR AESA & NAVAL RADAR: CONNECTED</div>
        </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Canlı FR24 Vektörü", len(df))
    m2.metric("TSK İHA/SİHA", len(df[df['is_uav']]))
    m3.metric("Yabancı Sınır İhlali", len(ihlal_df), delta_color="inverse")
    
    pdf_data = pdf_rapor_olustur(df, riskli_df)
    m4.download_button(
        label="📄 İHLAL RAPORU İNDİR",
        data=pdf_data,
        file_name=f"MILHAD_C4ISR_Raporu_{int(time.time())}.pdf",
        mime="application/pdf"
    )

    st.markdown("---")

    tab_2d, tab_3d = st.tabs(["📍 Canlı MİLHAD-C4ISR Rota Haritası", "🌐 3D İrtifa & Vektör Analizi"])

    secili_ucak_id = st.session_state.get('secili_ucak', df['ucak_id'].iloc[0])
    secili_row = df[df['ucak_id'] == secili_ucak_id]

    if secili_row.empty:
        secili_row = df.iloc[[0]]

    u = secili_row.iloc[0]

    with tab_2d:
        c1, c2 = st.columns([1.1, 2.4])

        # --- SOL TARAFTAKİ BİREBİR FLIGHTRADAR24 BİLGİ KARTI ---
        with c1:
            st.markdown(f"""
            <div class="fr24-card">
                <div class="fr24-card-header">
                    <h2 style="margin:0; font-size:20px; color:#ffffff;">{u['ucak_id']} <span style="font-size:13px; color:#f2c94c;">{u['icao24']}</span></h2>
                    <p style="margin:2px 0 0 0; color:#8f9ca6; font-size:12px;"><b>{u['havayolu']}</b> • {u['model']}</p>
                </div>
                
                <div style="width:100%; height:120px; background-color:#0b0e14; border-radius:4px; display:flex; align-items:center; justify-content:center; border:1px solid #28323e; margin-bottom:10px;">
                    <span style="font-size:40px;">✈️</span>
                </div>

                <div class="route-container">
                    <div>
                        <div class="airport-code">{u['kalkis']}</div>
                        <div class="airport-name">DEPARTURE</div>
                    </div>
                    <div style="font-size:20px; color:#f2c94c;">✈️</div>
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
                    <tr>
                        <td>STATUS</td>
                        <td class="val" style="color:{'#ff0055' if u['sinir_ihlal'] else '#00ff66'};">
                            {'⚠️ İHLAL' if u['sinir_ihlal'] else '✅ LIVE IN-FLIGHT'}
                        </td>
                    </tr>
                </table>
                
                <a href="https://www.flightradar24.com/{u['ucak_id']}" target="_blank" class="live-stream-btn">🎥 FLIGHTRADAR24 HARİTADA AÇ</a>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.selectbox("İncelemek İstediğiniz Canlı Uçağı Seçin:", df['ucak_id'].unique(), key="secili_ucak")

            # TAKTİK TELSİZ
            st.markdown("---")
            st.subheader("📻 VHF TAKTİK TELSİZ")
            if st.session_state["user_role"] == "Komutan":
                is_ghost_val = "true" if u['is_ghost'] or u['sinir_ihlal'] else "false"
                callsign_val = str(u['ucak_id'])
                
                voice_html = f"""
                <div class="voice-card">
                    <p style="color:#00ff66; font-weight:bold; margin-bottom:8px;">🎙️ Telsiz Mandalına Basıp Konuşun:</p>
                    <button id="recordBtn" onclick="startSpeech()" style="background:#002b11; color:#00ff66; border:1px solid #00ff66; padding:10px 18px; border-radius:4px; font-size:13px; cursor:pointer; font-weight:bold; width:100%;">
                        🔴 MANDALA BAS & TELSİZDEN TALİMAT VER
                    </button>
                    <p id="speechStatus" style="color:#aaa; font-size:12px; margin-top:8px;">Telsiz Durumu: Dinleme Modunda...</p>
                    <hr style="border-color:#00ff66;">
                    <p style="color:#00ffcc; font-size:12px; font-weight:bold;">🔊 Pilot Yanıtı (VHF Cızırtılı):</p>
                    <div id="replyBox" style="background:#000; padding:8px; border:1px solid #00ff66; border-radius:4px; color:#00ff66; font-family:monospace; min-height:35px; font-size:12px;">
                        [Telsiz Sessiz]
                    </div>
                </div>

                <script>
                function playRadioBeepAndSpeak(text) {{
                    var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    var osc = audioCtx.createOscillator();
                    var gain = audioCtx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(1200, audioCtx.currentTime);
                    gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                    osc.connect(gain);
                    gain.connect(audioCtx.destination);
                    osc.start();
                    osc.stop(audioCtx.currentTime + 0.15);

                    setTimeout(function() {{
                        if ('speechSynthesis' in window) {{
                            window.speechSynthesis.cancel();
                            var msg = new SpeechSynthesisUtterance();
                            msg.text = text;
                            msg.lang = 'tr-TR';
                            msg.rate = 1.0;
                            msg.pitch = 0.85;
                            window.speechSynthesis.speak(msg);
                        }}
                    }}, 200);
                }}

                function startSpeech() {{
                    var status = document.getElementById('speechStatus');
                    var reply = document.getElementById('replyBox');
                    var isGhost = {is_ghost_val};
                    var target = "{callsign_val}";

                    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
                        status.innerHTML = "⚠️ Tarayıcı ses tanımayı desteklemiyor.";
                        return;
                    }}

                    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                    var recognition = new SpeechRecognition();
                    recognition.lang = 'tr-TR';

                    status.innerHTML = "🎙️ TELSİZ KANALI AÇIK...";
                    recognition.start();

                    recognition.onresult = function(event) {{
                        var transcript = event.results[0][0].transcript;
                        status.innerHTML = "<b>Komut:</b> '" + transcript + "'";
                        
                        setTimeout(function() {{
                            if (isGhost) {{
                                var answer = "Cızırtı... Yanıt alınamadı. SQUAWK/ACARS Yok!";
                                reply.innerHTML = "❌ " + answer;
                                playRadioBeepAndSpeak("Sinyal yok. Yabancı unsur yanıt vermiyor.");
                            }} else {{
                                var answer = "Anlaşıldı komutanım. " + target + " komutunuzu aldı.";
                                reply.innerHTML = "✅ " + answer;
                                playRadioBeepAndSpeak(answer);
                            }}
                        }}, 600);
                    }};
                }}
                </script>
                """
                st.components.v1.html(voice_html, height=260)
            else:
                st.warning("🔒 Telsiz yetkisi yalnızca 'Komutan' rolündedir.")

        # --- SAĞ TARAFTAKİ HARİTA ---
        with c2:
            if sar_katmani:
                tiles_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attr = "Esri Satellite"
            else:
                tiles_url = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}{r}.png"
                attr = "CartoDB Voyager"

            m = folium.Map(location=[u['lat'], u['lon']], zoom_start=7, tiles=tiles_url, attr=attr)

            # HAVALİMANLARI
            for h in HAVALIMANLARI:
                is_askeri = "TSK" in h["tip"] or "NATO" in h["tip"]
                folium.Marker(
                    location=[h["lat"], h["lon"]],
                    popup=f"<b>{h['ad']} ({h['kod']})</b>",
                    icon=folium.Icon(color="red" if is_askeri else "blue", icon="star" if is_askeri else "plane", prefix="fa")
                ).add_to(m)

            # RADARLAR
            if goster_radarlar:
                for r in RADAR_ISTASYONLARI:
                    folium.Marker(
                        location=[r["lat"], r["lon"]],
                        popup=f"<b>📡 {r['ad']}</b>",
                        icon=folium.Icon(color="green", icon="rss", prefix="fa")
                    ).add_to(m)

            # UÇAK GEMİLERİ
            if goster_ucak_gemileri:
                for carrier in UCAK_GEMILERI:
                    folium.Marker(
                        location=[carrier["lat"], carrier["lon"]],
                        popup=f"<b>🚢 {carrier['ad']}</b>",
                        icon=folium.Icon(color="cadetblue" if carrier["is_friendly"] else "orange", icon="ship", prefix="fa")
                    ).add_to(m)

            # F-16 ÖNLEME GEOMETRİSİ (Eğer tehdit varsa)
            if len(ihlal_df) > 0:
                g_target = ihlal_df.iloc[0]
                base_jet = HAVALIMANLARI[7]
                i_lat, i_lon, t_sec = onleme_noktasi_hesapla(
                    g_target['lat'], g_target['lon'], g_target['hiz_kmh'], g_target['yon_deg'],
                    base_jet['lat'], base_jet['lon']
                )
                folium.PolyLine(
                    locations=[(base_jet['lat'], base_jet['lon']), (i_lat, i_lon)],
                    color="#00ff66", weight=3, dash_array="10, 10"
                ).add_to(m)
                folium.CircleMarker(
                    location=(i_lat, i_lon), radius=12, color="#ff0000", fill=True, fill_color="#ff0000",
                    popup=f"🎯 ÖNLEME TEMAS NOKTASI ({t_sec}s)"
                ).add_to(m)

            # SARI DÖNEN FLIGHTRADAR24 UÇAKLARI
            for _, row in df.iterrows():
                plane_color = "#ff0055" if row['sinir_ihlal'] else ("#00ff66" if row['is_uav'] else "#f2c94c")
                
                plane_svg = f"""
                <div style="transform: rotate({row['yon_deg']}deg); width:26px; height:26px; text-align:center;">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="{plane_color}" xmlns="http://www.w3.org/2000/svg">
                        <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
                    </svg>
                </div>
                """
                
                folium.Marker(
                    location=[row['lat'], row['lon']],
                    popup=f"<b>{row['ucak_id']}</b><br>{row['kalkis']} ➔ {row['varis']}",
                    tooltip=f"✈️ {row['ucak_id']} ({row['kalkis']} ➔ {row['varis']})",
                    icon=folium.DivIcon(html=plane_svg)
                ).add_to(m)

            # SEÇİLİ UÇAĞIN MOR ROTA ÇİZGİSİ & FR24 ETİKETİ
            folium.PolyLine(
                locations=u['lokasyonlar'],
                color="#a55eea",
                weight=4,
                opacity=0.9,
                dash_array="6, 6"
            ).add_to(m)

            folium.Marker(
                location=[u['lat'], u['lon']],
                icon=folium.DivIcon(
                    html=f"""<div style="background-color:#ffffff; color:#000; font-weight:bold; font-family:sans-serif; font-size:11px; padding:2px 6px; border-radius:3px; border:1px solid #000;">{u['ucak_id']}</div>""",
                    icon_anchor=(-10, 10)
                )
            ).add_to(m)

            st_folium(m, width=900, height=620, key="fr24_map", returned_objects=[])

    with tab_3d:
        st.subheader("🌐 3D İrtifa & Sütun Vektör Analizi")
        layer = pdk.Layer(
            "ColumnLayer",
            data=df,
            get_position=["lon", "lat"],
            get_elevation="irtifa_m",
            elevation_scale=1,
            radius=12000,
            get_fill_color="[sinir_ihlal ? 255 : (is_uav ? 0 : 242), sinir_ihlal ? 0 : (is_uav ? 255 : 201), sinir_ihlal ? 85 : (is_uav ? 100 : 76), 180]",
            pickable=True,
            auto_highlight=True,
        )
        view_state = pdk.ViewState(latitude=39.0, longitude=35.0, zoom=5.5, pitch=45, bearing=15)
        r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Vektör: {ucak_id}\nBirlik: {havayolu}\nİrtifa: {irtifa_m} m\nHız: {hiz_kmh} km/h"})
        st.pydeck_chart(r, use_container_width=True)

    if oto_yenile:
        time.sleep(refresh_rate)
        st.rerun()
