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

# --- SAYFA YAPILANDIRMASI & MILITARY C4ISR TEMA ---
st.set_page_config(
    page_title="MİLHAD-C4ISR - Entegre Hava & Deniz Savunma Komuta Merkezi",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #03070a; color: #00ff66; }
    .stMetric { background-color: #07131d; border: 1px solid #00ff66; padding: 12px; border-radius: 4px; box-shadow: 0 0 10px rgba(0,255,102,0.15); }
    div[data-testid="stSidebar"] { background-color: #040a10; border-right: 1px solid #00ff66; }
    
    .hud-title {
        font-family: 'Courier New', monospace;
        color: #00ff66;
        font-size: 24px;
        font-weight: bold;
        letter-spacing: 2px;
        text-shadow: 0 0 8px rgba(0,255,102,0.4);
    }
    .threat-hud {
        background: linear-gradient(90deg, #400000 0%, #100000 100%);
        color: #ff3344;
        padding: 14px 24px;
        border-radius: 4px;
        border: 1px solid #ff3344;
        box-shadow: 0 0 15px rgba(255,51,68,0.4);
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

    /* ALT SISTEMATIK YUVARLAK PPI RADAR EKRANI CSS */
    .bottom-radar-panel {
        background-color: #040c12;
        border: 1px solid #00ff66;
        border-radius: 6px;
        padding: 14px;
        margin-top: 15px;
        box-shadow: 0 0 15px rgba(0,255,102,0.2);
        font-family: 'Courier New', monospace;
    }
    .radar-scope-box {
        position: relative;
        width: 180px;
        height: 180px;
        background: radial-gradient(circle, #01210f 0%, #020b08 100%);
        border: 2px solid #00ff66;
        border-radius: 50%;
        margin: 0 auto;
        overflow: hidden;
        box-shadow: 0 0 15px rgba(0,255,102,0.3);
    }
    .radar-scope-ring-1 {
        position: absolute; top: 25%; left: 25%; width: 50%; height: 50%;
        border: 1px dashed rgba(0,255,102,0.4); border-radius: 50%;
    }
    .radar-scope-ring-2 {
        position: absolute; top: 10%; left: 10%; width: 80%; height: 80%;
        border: 1px solid rgba(0,255,102,0.3); border-radius: 50%;
    }
    .radar-scope-cross-h {
        position: absolute; top: 50%; left: 0; width: 100%; height: 1px; background: rgba(0,255,102,0.3);
    }
    .radar-scope-cross-v {
        position: absolute; top: 0; left: 50%; width: 1px; height: 100%; background: rgba(0,255,102,0.3);
    }
    .radar-scope-sweep {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        border-radius: 50%;
        background: conic-gradient(from 0deg, rgba(0, 255, 102, 0.55) 0deg, transparent 55deg);
        animation: radarSpin 2.5s linear infinite;
    }
    @keyframes radarSpin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .radar-blip-target {
        position: absolute; top: 32%; left: 62%; width: 7px; height: 7px;
        background: #ff0055; border-radius: 50%; box-shadow: 0 0 8px #ff0055;
        animation: blipPulse 1.2s infinite alternate;
    }
    .radar-blip-friendly {
        position: absolute; top: 68%; left: 28%; width: 6px; height: 6px;
        background: #00ff66; border-radius: 50%; box-shadow: 0 0 6px #00ff66;
    }
    @keyframes blipPulse {
        from { opacity: 0.3; transform: scale(0.8); }
        to { opacity: 1.0; transform: scale(1.3); }
    }
    .radar-log-box {
        background-color: #010508;
        border: 1px solid #004d26;
        padding: 10px;
        border-radius: 4px;
        color: #00ff66;
        font-size: 11px;
        height: 140px;
        overflow-y: auto;
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
st.caption("AESA Radar Füzyonu, Doğu Akdeniz Donanma Unsurları, Otonom Önleme Geometrisi & Taktik Telsiz")

# UÇAK GEMİLERİ
UCAK_GEMILERI = [
    {
        "kod": "TCG-ANADOLU",
        "ad": "TCG Anadolu (L-400) - Türkiye SİHA Gemisi",
        "ülke": "Türkiye",
        "lat": 36.520,
        "lon": 30.750,
        "konuşlu": "Bayraktar TB3, KIZILELMA",
        "is_friendly": True
    },
    {
        "kod": "CVN-78-FORD",
        "ad": "USS Gerald R. Ford (CVN-78) Carrier Group",
        "ülke": "ABD",
        "lat": 35.800,
        "lon": 28.100,
        "konuşlu": "F-35C, F/A-18E Super Hornet",
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

def en_yakin_havalimani(lat, lon):
    en_kucuk = 999999
    secilen = HAVALIMANLARI[0]
    for h in HAVALIMANLARI:
        d = np.sqrt((lat - h["lat"])**2 + (lon - h["lon"])**2)
        if d < en_kucuk:
            en_kucuk = d
            secilen = h
    return secilen

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

def ucak_verisi_getir(radar_fuzyon_aktif):
    url = "https://opensky-network.org/api/states/all?lamin=35.0&lomin=25.0&lamax=42.5&lomax=45.0"
    ucak_listesi = []
    
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
                        
                        is_uav = "BAYRAKTAR" in callsign or "AKINCI" in callsign or "ANKA" in callsign
                        is_tsk = is_uav or "TUAF" in callsign or "TURK" in callsign or ulke == "Turkey"
                        is_foreign_threat = (not is_tsk) and ("F16" in callsign or "MIL" in callsign or "NAVY" in callsign)
                        
                        kalkis = en_yakin_havalimani(lat, lon)
                        varis = HAVALIMANLARI[(idx+2) % len(HAVALIMANLARI)]
                        
                        lokasyonlar = [(lat, lon)]
                        cur_lat, cur_lon = lat, lon
                        for step in range(12):
                            cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                            cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                            lokasyonlar.append((cur_lat, cur_lon))
                            
                        orta_lat, orta_lon = 39.1, 33.5
                        mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
                        sinir_ihlal = turkiye_sinirlari_icinde_mi(lat, lon) and is_foreign_threat
                        
                        ucak_listesi.append({
                            'ucak_id': callsign,
                            'icao24': str(state[0]).upper(),
                            'havayolu': f"{ulke} Hava Trafiği" if not is_tsk else "TSK / Milli Filo",
                            'is_uav': is_uav,
                            'is_tsk': is_tsk,
                            'is_ghost': False,
                            'is_foreign_threat': is_foreign_threat,
                            'sinir_ihlal': sinir_ihlal,
                            'kalkis': f"{kalkis['kod']} ({kalkis['ad']})",
                            'varis': f"{varis['kod']} ({varis['ad']})",
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

    if len(ucak_listesi) < 12:
        np.random.seed(int(time.time()) // 10)
        eksik = 28 - len(ucak_listesi)
        tsk_filosu = ["AKINCI-TİHA-01", "KIZILELMA-02", "BAYRAKTAR-TB3", "SOLOTÜRK-F16"]
        
        for i in range(eksik):
            if i % 3 == 0:
                callsign = np.random.choice(tsk_filosu) + f"-{i}"
                is_uav, is_tsk, havayolu = True, True, "TSK Otonom Filo"
            else:
                callsign = f"THY{200 + i}" if i % 2 == 0 else f"PGT{300 + i}"
                is_uav, is_tsk, havayolu = False, False, "Türk Hava Yolları"
                
            lat = np.random.uniform(36.8, 41.5)
            lon = np.random.uniform(27.5, 42.5)
            irtifa = np.random.uniform(1500, 11000)
            hiz = np.random.uniform(250, 820)
            yon = np.random.uniform(0, 360)
            
            kalkis = en_yakin_havalimani(lat, lon)
            varis = HAVALIMANLARI[(i+3) % len(HAVALIMANLARI)]
            
            lokasyonlar = [(lat, lon)]
            cur_lat, cur_lon = lat, lon
            for step in range(12):
                cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                lokasyonlar.append((cur_lat, cur_lon))
                
            orta_lat, orta_lon = 39.1, 33.5
            mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)

            ucak_listesi.append({
                'ucak_id': callsign,
                'icao24': f"A{2000+i:04X}",
                'havayolu': havayolu,
                'is_uav': is_uav,
                'is_tsk': is_tsk,
                'is_ghost': False,
                'is_foreign_threat': False,
                'sinir_ihlal': False,
                'kalkis': f"{kalkis['kod']} ({kalkis['ad']})",
                'varis': f"{varis['kod']} ({varis['ad']})",
                'lat': lat,
                'lon': lon,
                'irtifa_m': round(irtifa, 1),
                'hiz_kmh': round(hiz, 1),
                'yon_deg': round(yon, 1),
                'mesafe_deg': mesafe,
                'lokasyonlar': lokasyonlar
            })

    if radar_fuzyon_aktif:
        np.random.seed(int(time.time()) // 5)
        for g in range(1):
            lat, lon = 38.2, 26.8
            hiz, yon, irtifa = 1450, 85, 2100
            orta_lat, orta_lon = 39.1, 33.5
            mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
            
            lokasyonlar = [(lat, lon)]
            cur_lat, cur_lon = lat, lon
            for step in range(12):
                cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                lokasyonlar.append((cur_lat, cur_lon))

            ucak_listesi.append({
                'ucak_id': "YABANCI-MILITARY-X",
                'icao24': "NO-SQUAWK",
                'havayolu': "⚠️ UNIDENTIFIED HOSTILE",
                'is_uav': False,
                'is_tsk': False,
                'is_ghost': True,
                'is_foreign_threat': True,
                'sinir_ihlal': True,
                'kalkis': "CVN-78 / Doğu Akdeniz",
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
    story.append(Paragraph("MİLHAD-C4ISR RESMİ MİLLİ SAVUNMA RAPORU", title_style))
    story.append(Paragraph(f"<b>Rapor Tarihi:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Paragraph(f"<b>Raporu Oluşturan Yetkili:</b> {st.session_state.get('user_name', 'Bilinmiyor')} ({st.session_state.get('user_role', 'Rol Yok')})", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph(f"<b>Toplam Takip Edilen Canlı Hava Vektörü:</b> {len(dataframe)}", styles['Normal']))
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
st.sidebar.title("🎛️ MİLHAD-C4ISR COMMAND PANEL")
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

df = ucak_verisi_getir(radar_fuzyon)

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

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Vektör", len(df))
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

    tab_2d, tab_3d = st.tabs(["📍 MİLHAD-C4ISR Taktik Harita & Önleme Geometrisi", "🌐 3D İrtifa & Vektör Analizi"])

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
                tiles_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attr = "Esri Satellite"
            else:
                tiles_url = "CartoDB dark_matter"
                attr = "CartoDB Dark"

            m = folium.Map(location=map_center, zoom_start=map_zoom, tiles=tiles_url, attr=attr)

            # HAVALİMANLARI
            for h in HAVALIMANLARI:
                is_askeri = "TSK" in h["tip"] or "NATO" in h["tip"]
                folium.Marker(
                    location=[h["lat"], h["lon"]],
                    popup=f"<b>{h['ad']} ({h['kod']})</b>",
                    icon=folium.Icon(color="red" if is_askeri else "blue", icon="star" if is_askeri else "plane", prefix="fa")
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
                    folium.Marker(
                        location=[carrier["lat"], carrier["lon"]],
                        popup=f"<b>🚢 {carrier['ad']}</b>",
                        icon=folium.Icon(color="cadetblue" if carrier["is_friendly"] else "orange", icon="ship", prefix="fa")
                    ).add_to(m)

            # F-16 ÖNLEME GEOMETRİSİ
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

            # TÜM CANLI UÇAKLAR & VEKTÖRLER
            for _, row in df.iterrows():
                is_ihlal = row['sinir_ihlal']
                is_risk = row['alarm']
                is_uav = row['is_uav']
                
                color = "#FF0055" if is_ihlal else ("#FF3300" if is_risk else ("#00FF66" if is_uav else "#00FFCC"))
                hover_text = f"{row['ucak_id']} | Birim: {row['havayolu']} | Rota: {row['kalkis']} ➔ {row['varis']} | İrtifa: {row['irtifa_m']}m"
                
                folium.PolyLine(locations=row['lokasyonlar'], color=color, weight=3 if is_ihlal else 1.5).add_to(m)
                folium.CircleMarker(
                    location=(row['lat'], row['lon']), radius=9 if is_ihlal else 6, color=color, fill=True, fill_color=color, tooltip=hover_text
                ).add_to(m)

            st_folium(m, width=800, height=520, key="taktik_harita_2d", returned_objects=[])

        with c2:
            st.subheader("🔎 TAKTİK HEDEF İNCELEME & SESLİ TELSİZ")
            secili_ucak = st.selectbox("İncelemek İstediğiniz Canlı Vektörü Seçin:", df['ucak_id'].unique(), key="secili_ucak")
            
            if secili_ucak:
                u = df[df['ucak_id'] == secili_ucak].iloc[0]
                fr24_url = f"https://www.flightradar24.com/{u['ucak_id']}"
                
                st.markdown(f"""
                <div class="flight-card">
                    <h3 style="margin:0; color:#00ff66;">🎯 TARGET LOCK: {u['ucak_id']}</h3>
                    <p style="margin:5px 0; color:#aaa;"><b>Birlik/Operatör:</b> {u['havayolu']}</p>
                    <hr style="border-color:#00ff66;">
                    <p style="margin:3px 0;"><b>🛫 Kalkış:</b> <span style="color:#00ffcc;">{u['kalkis']}</span></p>
                    <p style="margin:3px 0;"><b>🛬 Varış:</b> <span style="color:#ffcc00;">{u['varis']}</span></p>
                    <p style="margin:3px 0;"><b>🆔 SQUAWK:</b> <code>{u['icao24']}</code></p>
                    <p style="margin:3px 0;"><b>📈 İrtifa:</b> {u['irtifa_m']} m | <b>🚀 Hız:</b> {u['hiz_kmh']} km/h</p>
                    <p style="margin:3px 0;"><b>🧭 Vektör Yönü:</b> {u['yon_deg']}°</p>
                    <p style="margin:3px 0;"><b>🚨 Sınır İhlal Durumu:</b> {"⚠️ İHLAL VAR!" if u['sinir_ihlal'] else "✅ Emniyetli"}</p>
                    <a href="{fr24_url}" target="_blank" class="live-stream-btn">🎥 GERÇEK ZAMANLI CANLI İZLE (FLIGHTRADAR24)</a>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.session_state["user_role"] == "Komutan":
                    is_ghost_val = "true" if u['is_ghost'] or u['sinir_ihlal'] else "false"
                    callsign_val = str(u['ucak_id'])
                    
                    voice_html = f"""
                    <div class="voice-card">
                        <p style="color:#00ff66; font-weight:bold; margin-top:0; margin-bottom:8px; font-size:14px;">📻 VHF TAKTİK TELSİZ (MİKROFON / BEEP EFEKTLİ)</p>
                        <p style="color:#aaa; font-size:12px; margin-bottom:8px;">🎙️ Telsiz Mandalına Basıp Konuşun:</p>
                        <button id="recordBtn" onclick="startSpeech()" style="background:#002b11; color:#00ff66; border:1px solid #00ff66; padding:10px 18px; border-radius:4px; font-size:13px; cursor:pointer; font-weight:bold; width:100%;">
                            🔴 MANDALA BAS & TELSİZDEN TALİMAT VER
                        </button>
                        <p id="speechStatus" style="color:#aaa; font-size:12px; margin-top:8px;">Telsiz Durumu: Dinleme Modunda...</p>
                        <hr style="border-color:#00ff66;">
                        <p style="color:#00ffcc; font-size:12px; font-weight:bold;">🔊 Pilot / İHA Yanıtı (VHF Cızırtılı):</p>
                        <div id="replyBox" style="background:#000; padding:10px; border:1px solid #00ff66; border-radius:4px; color:#00ff66; font-family:monospace; min-height:40px; font-size:12px;">
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
                    st.components.v1.html(voice_html, height=270)
                else:
                    st.warning("🔒 Telsiz kanalı üzerinden talimat verme yetkisi yalnızca 'Komutan' rolüne aittir.")

    with tab_3d:
        st.subheader("🌐 3D İrtifa & Sütun Vektör Katmanı")
        
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

    # --- EN ALTA EKLENEN CANLI GÖRSEL PPI RADAR EKRANI & KONSOL ---
    st.markdown("---")
    st.subheader("📡 CANLI AESA RADAR SCOPE & SİSTEMATİK TELEMETRİ KONSOLU")
    
    r_col1, r_col2, r_col3 = st.columns([1.2, 1.5, 2.2])
    
    with r_col1:
        st.markdown("""
        <div class="bottom-radar-panel" style="text-align:center;">
            <h4 style="color:#00ff66; margin-top:0; font-size:13px;">📡 360° CANLI PPI RADAR SCOPE</h4>
            <div class="radar-scope-box">
                <div class="radar-scope-ring-1"></div>
                <div class="radar-scope-ring-2"></div>
                <div class="radar-scope-cross-h"></div>
                <div class="radar-scope-cross-v"></div>
                <div class="radar-scope-sweep"></div>
                <div class="radar-blip-target"></div>
                <div class="radar-blip-friendly"></div>
            </div>
            <p style="color:#8f9ca6; font-size:10px; margin-top:8px; margin-bottom:0;">X-BAND AESA FREQUENCY LOCK</p>
        </div>
        """, unsafe_allow_html=True)

    with r_col2:
        st.markdown("""
        <div class="bottom-radar-panel">
            <h4 style="color:#00ff66; margin-top:0; font-size:13px;">📊 Radar İstatistiki Frekanslar</h4>
            <p style="margin:4px 0; font-size:11px;">• <b>AESA Tarama Frekansı:</b> 9.4 GHz (X-Band)</p>
            <p style="margin:4px 0; font-size:11px;">• <b>Tarama Hızı:</b> 120 RPM (Tur/Dakika)</p>
            <p style="margin:4px 0; font-size:11px;">• <b>Aktif Radar Mevzii:</b> 5 İstasyon Kilitli</p>
            <p style="margin:4px 0; font-size:11px;">• <b>Gecikme / Akış:</b> ADS-B Realtime (< 120 ms)</p>
            <p style="margin:4px 0; font-size:11px;">• <b>Erken Tespit:</b> Otonom İhbar Aktif</p>
        </div>
        """, unsafe_allow_html=True)
        
    with r_col3:
        curr_time = time.strftime('%H:%M:%S')
        st.markdown(f"""
        <div class="bottom-radar-panel">
            <h4 style="color:#00ff66; margin-top:0; font-size:13px;">📜 Canlı Radar Sistem Konsolu [{curr_time}]</h4>
            <div class="radar-log-box">
                [{curr_time}] [RADAR-KURECIK] X-Band Erken ihbar taraması aktif. Sinyal kalitesi: %99.8<br>
                [{curr_time}] [MİLHAD-C4ISR] OpenSky & AESA füzyon katmanı senkronize edildi.<br>
                [{curr_time}] [AHLATLIBEL-RADAR] Başkent yaklaşma kontrolü temiz. Vektör takibi stabil.<br>
                [{curr_time}] [GEOFENCE-ENGINE] Türkiye milli hava sınır çizgisi (35.8-42.1 N / 25.6-44.8 E) kilitlendi.<br>
                [{curr_time}] [SYSTEM] Toplam {len(df)} adet hava/deniz vektörü canlı işleniyor...
            </div>
        </div>
        """, unsafe_allow_html=True)

    if oto_yenile:
        time.sleep(refresh_rate)
        st.rerun()
