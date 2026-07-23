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

# Flightradar24 Kütüphanesi
try:
    from FlightRadar24 import FlightRadar24API
    fr_api = FlightRadar24API()
except Exception:
    fr_api = None

# --- SAYFA YAPILANDIRMASI & C4ISR HUD TEMA ---
st.set_page_config(
    page_title="AASS - C4ISR LIVE FLIGHTRADAR & DEFENSE",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #03070a; color: #00ff66; }
    .stMetric { background-color: #07131d; border: 1px solid #00ff66; padding: 12px; border-radius: 4px; box-shadow: 0 0 10px rgba(0,255,102,0.2); }
    div[data-testid="stSidebar"] { background-color: #040a10; border-right: 1px solid #00ff66; }
    
    .hud-title {
        font-family: 'Courier New', monospace;
        color: #00ff66;
        text-shadow: 0 0 8px #00ff66;
        letter-spacing: 2px;
        font-weight: bold;
    }
    .threat-hud {
        background: linear-gradient(90deg, #721c24 0%, #2c0b0e 100%);
        color: #ffffff;
        padding: 16px 24px;
        border-radius: 6px;
        border: 2px solid #ff0055;
        box-shadow: 0 0 25px rgba(255,0,85,0.6);
        font-family: monospace;
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .status-good {
        background: linear-gradient(90deg, #002b11 0%, #001006 100%);
        color: #00ff66;
        padding: 14px 24px;
        border-radius: 4px;
        border: 1px solid #00ff66;
        box-shadow: 0 0 15px rgba(0,255,102,0.3);
        font-family: monospace;
        font-size: 15px;
        margin-bottom: 20px;
    }
    .flight-card {
        background-color: #07131d;
        border: 1px solid #00a8ff;
        padding: 15px;
        border-radius: 6px;
        box-shadow: 0 0 12px rgba(0,168,255,0.2);
        font-family: monospace;
    }
    .voice-card {
        background: #050e17;
        border: 1px solid #00ff66;
        padding: 15px;
        border-radius: 6px;
        margin-top: 15px;
        box-shadow: 0 0 10px rgba(0,255,102,0.2);
    }
    .login-box {
        background-color: #07131d;
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
        background: #00a8ff;
        color: #000;
        text-align: center;
        padding: 10px;
        border-radius: 4px;
        font-weight: bold;
        text-decoration: none;
        margin-top: 10px;
    }
    .radar-container {
        position: relative;
        width: 100%;
        height: 120px;
        background: #020b08;
        border: 1px solid #00ff66;
        border-radius: 6px;
        overflow: hidden;
        margin-bottom: 15px;
        box-shadow: 0 0 15px rgba(0,255,102,0.2);
    }
    .radar-sweep {
        position: absolute;
        top: 50%;
        left: 50%;
        width: 200px;
        height: 200px;
        margin-top: -100px;
        margin-left: -100px;
        border-radius: 50%;
        border: 1px solid rgba(0,255,102,0.3);
        background: conic-gradient(from 0deg, rgba(0, 255, 102, 0.4) 0deg, transparent 60deg);
        animation: radarSpin 3s linear infinite;
    }
    @keyframes radarSpin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .radar-center {
        position: absolute;
        top: 50%;
        left: 50%;
        width: 8px;
        height: 8px;
        background: #00ff66;
        border-radius: 50%;
        margin-top: -4px;
        margin-left: -4px;
        box-shadow: 0 0 10px #00ff66;
    }
    </style>
""", unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None

if not st.session_state["logged_in"]:
    st.markdown('<h1 class="hud-title" style="text-align:center;">🛡️ AASS C4ISR KOMUTA MERKEZİ GİRİŞİ</h1>', unsafe_allow_html=True)
    
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

st.markdown('<h1 class="hud-title">🛡️ AASS C4ISR — CANLI FLIGHTRADAR24 HAVACILIK & DEFENSE CENTER</h1>', unsafe_allow_html=True)
st.caption("Flightradar24 Gerçek Zamanlı Canlı Rota / Kalkış-Varış Veritabanı & Radar Füzyonu")

# UÇAK GEMİLERİ
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

# GERÇEK FLIGHTRADAR24 VERİ ÇEKİCİ MOTOR
def flightradar24_canli_veri_getir(radar_fuzyon_aktif):
    ucak_listesi = []
    
    # 1. Flightradar24 API Denemesi
    if fr_api is not None:
        try:
            # Türkiye Kapsama Alanı
            bounds = "42.5,35.0,25.0,45.0" # N, S, W, E
            flights = fr_api.get_flights(bounds=bounds)
            
            for flight in flights[:40]: # Performans için ilk 40 canlı uçuş
                callsign = flight.callsign if flight.callsign else f"FR24-{flight.id}"
                lat, lon = flight.latitude, flight.longitude
                irtifa = flight.altitude * 0.3048 # Feet -> Metre
                hiz = flight.ground_speed * 1.852 # Knot -> km/s
                yon = flight.heading
                
                kalkis = flight.origin_airport_iata if flight.origin_airport_iata else "N/A"
                varis = flight.destination_airport_iata if flight.destination_airport_iata else "N/A"
                havayolu = flight.airline_name if flight.airline_name else "Sivil Havacılık"
                
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
                    'is_uav': is_uav,
                    'is_tsk': is_tsk,
                    'is_ghost': False,
                    'is_foreign_threat': is_foreign_threat,
                    'sinir_ihlal': sinir_ihlal,
                    'kalkis': kalkis,
                    'varis': varis,
                    'lat': lat,
                    'lon': lon,
                    'irtifa_m': round(irtifa, 1),
                    'hiz_kmh': round(hiz, 1),
                    'yon_deg': round(yon, 1),
                    'mesafe_deg': mesafe,
                    'lokasyonlar': lokasyonlar
                })
        except Exception:
            pass

    # 2. Eğer FR24 API yanıt vermezse OpenSky Live Fallback
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
                            irtifa = state[7] if state[7] is not None else 7200
                            hiz = (state[9] * 3.6) if state[9] is not None else 710
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
                                'is_uav': is_uav,
                                'is_tsk': is_tsk,
                                'is_ghost': False,
                                'is_foreign_threat': is_foreign_threat,
                                'sinir_ihlal': sinir_ihlal,
                                'kalkis': "IST (İstanbul)",
                                'varis': "AYT (Antalya)",
                                'lat': lat,
                                'lon': lon,
                                'irtifa_m': round(irtifa, 1),
                                'hiz_kmh': round(hiz, 1),
                                'yon_deg': round(yon, 1),
                                'mesafe_deg': mesafe,
                                'lokasyonlar': lokasyonlar
                            })
        except Exception:
            pass

    # DÜŞMAN İHLAL SİMÜLASYONU
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
                'ucak_id': "YABANCI-SAVAŞ-UÇAĞI",
                'icao24': "NO-SQUAWK",
                'havayolu': "⚠️ UNIDENTIFIED HOSTILE",
                'is_uav': False,
                'is_tsk': False,
                'is_ghost': True,
                'is_foreign_threat': True,
                'sinir_ihlal': True,
                'kalkis': "Yabancı Donanma / Akdeniz",
                'varis': "Milli Hava Sahası İhlal Rotası",
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
    story.append(Paragraph("AASS RESMİ TSK CANLI HAVACILIK RAPORU", title_style))
    story.append(Paragraph(f"<b>Rapor Tarihi:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Paragraph(f"<b>Raporu Oluşturan Yetkili:</b> {st.session_state.get('user_name', 'Bilinmiyor')} ({st.session_state.get('user_role', 'Rol Yok')})", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph(f"<b>Toplam Takip Edilen Canlı FR24 Vektörü:</b> {len(dataframe)}", styles['Normal']))
    story.append(Paragraph(f"<b>Tespit Edilen Tehdit/İhlal Sayısı:</b> {len(riskliler)}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>🚨 KRİTİK İHLAL LİSTESİ</b>", styles['Heading2']))
    
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
st.sidebar.title("🎛️ C4ISR COMMAND PANEL")
oto_yenile = st.sidebar.toggle("🔴 CANLI FLIGHTRADAR TARAMASI", value=True)
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
            <div class="radar-center"></div>
            <div style="position:absolute; bottom:5px; left:10px; color:#00ff66; font-family:monospace; font-size:11px;">📡 FLIGHTRADAR24 LIVE FEED & AESA RADAR: CONNECTED</div>
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
        file_name=f"AASS_FR24_Raporu_{int(time.time())}.pdf",
        mime="application/pdf"
    )

    st.markdown("---")

    tab_2d, tab_3d = st.tabs(["📍 Canlı Flightradar24 Rota Haritası", "🌐 3D İrtifa & Vektör Analizi"])

    with tab_2d:
        c1, c2 = st.columns([2.0, 1.2])
        
        secili_ucak_id = st.session_state.get('secili_ucak', df['ucak_id'].iloc[0])
        secili_row = df[df['ucak_id'] == secili_ucak_id]
        
        if not secili_row.empty:
            map_center = [secili_row.iloc[0]['lat'], secili_row.iloc[0]['lon']]
            map_zoom = 7
        else:
            map_center = [38.5, 33.5]
            map_zoom = 6

        with c1:
            if sar_katmani:
                m = folium.Map(
                    location=map_center, 
                    zoom_start=map_zoom, 
                    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    attr="Esri World Imagery"
                )
            else:
                m = folium.Map(
                    location=map_center, 
                    zoom_start=map_zoom, 
                    tiles="CartoDB dark_matter"
                )
            
            # HAVALİMANLARI
            for h in HAVALIMANLARI:
                is_askeri = "TSK" in h["tip"] or "NATO" in h["tip"]
                icon_color = "red" if is_askeri else "blue"
                folium.Marker(
                    location=[h["lat"], h["lon"]],
                    popup=f"<b>{h['ad']} ({h['kod']})</b>",
                    icon=folium.Icon(color=icon_color, icon="star" if is_askeri else "plane", prefix="fa")
                ).add_to(m)

            # RADAR İSTASYONLARI
            if goster_radarlar:
                for r in RADAR_ISTASYONLARI:
                    folium.Marker(
                        location=[r["lat"], r["lon"]],
                        popup=f"<b>📡 {r['ad']}</b><br>Menzil: {r['menzil_km']} km",
                        icon=folium.Icon(color="green", icon="rss", prefix="fa")
                    ).add_to(m)

            # UÇAK GEMİLERİ
            if goster_ucak_gemileri:
                for carrier in UCAK_GEMILERI:
                    c_color = "cadetblue" if carrier["is_friendly"] else "orange"
                    folium.Marker(
                        location=[carrier["lat"], carrier["lon"]],
                        popup=f"<b>🚢 {carrier['ad']}</b><br>Ülke: {carrier['ülke']}<br>Konuşlu: {carrier['konuşlu']}",
                        icon=folium.Icon(color=c_color, icon="ship", prefix="fa")
                    ).add_to(m)

            # FLIGHTRADAR24 UÇAKLARI VE GERÇEK CANLI ROTALARI
            for _, row in df.iterrows():
                is_ihlal = row['sinir_ihlal']
                is_risk = row['alarm']
                is_uav = row['is_uav']
                
                color = "#FF0055" if is_ihlal else ("#FF3300" if is_risk else ("#00FF66" if is_uav else "#00FFCC"))
                hover_text = f"✈️ {row['ucak_id']} ({row['havayolu']}) | 🛫 Rota: {row['kalkis']} ➔ {row['varis']} | 📈 İrtifa: {row['irtifa_m']}m"
                
                # Uçağın Anlık Rotasını Haritada Çiz
                folium.PolyLine(locations=row['lokasyonlar'], color=color, weight=2.5 if is_ihlal else 1.2, opacity=0.8).add_to(m)
                folium.CircleMarker(
                    location=(row['lat'], row['lon']), radius=8 if is_ihlal else 5, color=color, fill=True, fill_color=color, tooltip=hover_text
                ).add_to(m)

            st_folium(m, width=800, height=520, key="taktik_harita_2d", returned_objects=[])

        with c2:
            st.subheader("🔎 CANLI ROTA & TAKTİK TELSİZ")
            secili_ucak = st.selectbox("İncelemek İstediğiniz Canlı FR24 Uçağını Seçin:", df['ucak_id'].unique(), key="secili_ucak")
            
            if secili_ucak:
                u = df[df['ucak_id'] == secili_ucak].iloc[0]
                fr24_url = f"https://www.flightradar24.com/{u['ucak_id']}"
                
                st.markdown(f"""
                <div class="flight-card">
                    <h3 style="margin:0; color:#00ff66;">✈️ {u['ucak_id']}</h3>
                    <p style="margin:5px 0; color:#aaa;"><b>Operatör/Havayolu:</b> {u['havayolu']}</p>
                    <hr style="border-color:#00ff66;">
                    <p style="font-size:15px; margin:5px 0;"><b>🛫 Kalkış Havalimanı:</b> <span style="color:#00ffcc; font-weight:bold;">{u['kalkis']}</span></p>
                    <p style="font-size:15px; margin:5px 0;"><b>🛬 Varış Havalimanı:</b> <span style="color:#ffcc00; font-weight:bold;">{u['varis']}</span></p>
                    <hr style="border-color:#00ff66;">
                    <p style="margin:3px 0;"><b>🆔 Transponder/ICAO:</b> <code>{u['icao24']}</code></p>
                    <p style="margin:3px 0;"><b>📈 Anlık İrtifa:</b> {u['irtifa_m']} metre</p>
                    <p style="margin:3px 0;"><b>🚀 Anlık Hız:</b> {u['hiz_kmh']} km/h</p>
                    <p style="margin:3px 0;"><b>🧭 Uçuş Yönü:</b> {u['yon_deg']}°</p>
                    <a href="{fr24_url}" target="_blank" class="live-stream-btn">🎥 FLIGHTRADAR24 CANLI HARİTADA AÇ</a>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.subheader("📻 VHF TAKTİK TELSİZ (MİKROFON / BEEP EFEKTLİ)")
                
                if st.session_state["user_role"] == "Komutan":
                    is_ghost_val = "true" if u['is_ghost'] or u['sinir_ihlal'] else "false"
                    callsign_val = str(u['ucak_id'])
                    
                    voice_html = f"""
                    <div class="voice-card">
                        <p style="color:#00ff66; font-weight:bold; margin-bottom:8px;">🎙️ Telsiz Mandalına Basıp Konuşun:</p>
                        <button id="recordBtn" onclick="startSpeech()" style="background:#002b11; color:#00ff66; border:1px solid #00ff66; padding:10px 18px; border-radius:4px; font-size:14px; cursor:pointer; font-weight:bold; width:100%;">
                            🔴 MANDALA BAS & TELSİZDEN TALİMAT VER
                        </button>
                        <p id="speechStatus" style="color:#aaa; font-size:12px; margin-top:8px;">Telsiz Durumu: Dinleme Modunda...</p>
                        <hr style="border-color:#00ff66;">
                        <p style="color:#00ffcc; font-size:13px; font-weight:bold;">🔊 Pilot / İHA Yanıtı (VHF Cızırtılı):</p>
                        <div id="replyBox" style="background:#000; padding:10px; border:1px solid #00ff66; border-radius:4px; color:#00ff66; font-family:monospace; min-height:40px;">
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
                            status.innerHTML = "⚠️ Tarayıcınız ses tanımayı desteklemiyor. Chrome veya Edge kullanın.";
                            return;
                        }}

                        var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                        var recognition = new SpeechRecognition();
                        recognition.lang = 'tr-TR';

                        status.innerHTML = "🎙️ TELSİZ KANALI AÇIK... Lütfen konuşun!";
                        recognition.start();

                        recognition.onresult = function(event) {{
                            var transcript = event.results[0][0].transcript;
                            status.innerHTML = "<b>İletilen Telsiz Mesajı:</b> '" + transcript + "'";
                            
                            setTimeout(function() {{
                                if (isGhost) {{
                                    var answer = "Cızırtı... Yanıt alınamadı. Yabancı Unsur İhlal Sinyali Vermiyor!";
                                    reply.innerHTML = "❌ " + answer;
                                    playRadioBeepAndSpeak("Sinyal yok. Yabancı ihlal unsuru yanıt vermiyor.");
                                }} else {{
                                    var answer = "Anlaşıldı komutanım. " + target + " telsiz mesajınızı aldı. Rota güncelleniyor.";
                                    reply.innerHTML = "✅ " + answer;
                                    playRadioBeepAndSpeak(answer);
                                }}
                            }}, 600);
                        }};
                    }}
                    </script>
                    """
                    st.components.v1.html(voice_html, height=280)
                else:
                    st.warning("🔒 Telsiz kanalı üzerinden talimat verme yetkisi yalnızca 'Komutan' rolüne aittir.")

    with tab_3d:
        st.subheader("🌐 3D İrtifa & Sütun Vektör Analizi")
        
        layer = pdk.Layer(
            "ColumnLayer",
            data=df,
            get_position=["lon", "lat"],
            get_elevation="irtifa_m",
            elevation_scale=1,
            radius=12000,
            get_fill_color="[sinir_ihlal ? 255 : (is_uav ? 0 : 0), sinir_ihlal ? 0 : (is_uav ? 255 : 200), sinir_ihlal ? 85 : (is_uav ? 100 : 255), 180]",
            pickable=True,
            auto_highlight=True,
        )

        view_state = pdk.ViewState(latitude=39.0, longitude=35.0, zoom=5.5, pitch=45, bearing=15)
        r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Vektör: {ucak_id}\nBirlik: {havayolu}\nİrtifa: {irtifa_m} m\nHız: {hiz_kmh} km/h"})
        st.pydeck_chart(r, use_container_width=True)

    if oto_yenile:
        time.sleep(refresh_rate)
        st.rerun()
