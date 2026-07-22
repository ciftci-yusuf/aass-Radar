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

# --- SAYFA YAPILANDIRMASI & MILITARY TEMA ---
st.set_page_config(
    page_title="AASS - TSK & MİLLİ HAVA SAHASI KOMUTA MERKEZİ",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #0b0e14; }
    .stMetric { background-color: #141824; border: 1px solid #23293a; padding: 16px; border-radius: 8px; }
    div[data-testid="stSidebar"] { background-color: #0f121d; border-right: 1px solid #23293a; }
    .threat-hud {
        background: linear-gradient(90deg, #721c24 0%, #2c0b0e 100%);
        color: #ffffff;
        padding: 14px 24px;
        border-radius: 8px;
        border-left: 6px solid #ff3344;
        font-family: monospace;
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .status-good {
        background: linear-gradient(90deg, #155724 0%, #0b2910 100%);
        color: #ffffff;
        padding: 14px 24px;
        border-radius: 8px;
        border-left: 6px solid #28a745;
        font-family: monospace;
        font-size: 15px;
        margin-bottom: 20px;
    }
    .ghost-alert {
        background-color: #3d0007;
        border: 1px dashed #ff0055;
        padding: 12px;
        border-radius: 5px;
        color: #ff99aa;
        font-family: monospace;
        margin-bottom: 10px;
    }
    .flight-card {
        background-color: #141824;
        border: 1px solid #0055ff;
        padding: 15px;
        border-radius: 8px;
        margin-top: 10px;
    }
    .radio-box {
        background-color: #0d1b2a;
        border: 1px solid #00b4d8;
        padding: 12px;
        border-radius: 6px;
        font-family: monospace;
        color: #90e0ef;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ AASS — TSK & Otonom Milli Hava Sahası Savunma Merkezi")
st.caption("Türkiye Geneli Tüm Havalimanları, TSK Filosu & ACARS/Telsiz Taktik İletişim Paneli")

HAVALIMANLARI = [
    {"kod": "ADA", "ad": "Adana Havalimanı", "lat": 36.982, "lon": 35.280, "tip": "Sivil"},
    {"kod": "ADF", "ad": "Adıyaman Havalimanı", "lat": 37.731, "lon": 38.468, "tip": "Sivil"},
    {"kod": "AJI", "ad": "Ağrı Ahmed-i Hani Havalimanı", "lat": 39.654, "lon": 43.027, "tip": "Sivil"},
    {"kod": "MZH", "ad": "Amasya Merzifon Havalimanı", "lat": 40.829, "lon": 35.521, "tip": "Sivil/Karma"},
    {"kod": "ESB", "ad": "Ankara Esenboğa Havalimanı", "lat": 40.128, "lon": 32.995, "tip": "Sivil Başkent Hub"},
    {"kod": "AYT", "ad": "Antalya Havalimanı", "lat": 36.898, "lon": 30.800, "tip": "Sivil Uluslararası"},
    {"kod": "GZP", "ad": "Gazipaşa-Alanya Havalimanı", "lat": 36.299, "lon": 32.301, "tip": "Sivil"},
    {"kod": "EDO", "ad": "Balıkesir Koca Seyit Havalimanı", "lat": 39.554, "lon": 27.013, "tip": "Sivil"},
    {"kod": "BAL", "ad": "Batman Havalimanı", "lat": 37.929, "lon": 41.116, "tip": "Sivil"},
    {"kod": "BGG", "ad": "Bingöl Havalimanı", "lat": 38.861, "lon": 40.592, "tip": "Sivil"},
    {"kod": "YEI", "ad": "Bursa Yenişehir Havalimanı", "lat": 40.255, "lon": 29.562, "tip": "Sivil"},
    {"kod": "CKZ", "ad": "Çanakkale Havalimanı", "lat": 40.137, "lon": 26.426, "tip": "Sivil"},
    {"kod": "GKD", "ad": "Çanakkale Gökçeada Havalimanı", "lat": 40.200, "lon": 25.883, "tip": "Sivil"},
    {"kod": "COV", "ad": "Çukurova Uluslararası Havalimanı", "lat": 36.890, "lon": 35.060, "tip": "Sivil Uluslararası"},
    {"kod": "DNZ", "ad": "Denizli Çardak Havalimanı", "lat": 37.785, "lon": 29.701, "tip": "Sivil"},
    {"kod": "DIY", "ad": "Diyarbakır Havalimanı", "lat": 37.893, "lon": 40.201, "tip": "Sivil/TSK Üssü"},
    {"kod": "EZS", "ad": "Elazığ Havalimanı", "lat": 38.607, "lon": 39.291, "tip": "Sivil"},
    {"kod": "ERC", "ad": "Erzincan Yıldırım Akbulut Havalimanı", "lat": 39.715, "lon": 39.526, "tip": "Sivil"},
    {"kod": "ERZ", "ad": "Erzurum Havalimanı", "lat": 39.956, "lon": 41.170, "tip": "Sivil/Karma"},
    {"kod": "AOE", "ad": "Eskişehir Hasan Polatkan Havalimanı", "lat": 39.812, "lon": 30.531, "tip": "Sivil"},
    {"kod": "GZT", "ad": "Gaziantep Havalimanı", "lat": 36.947, "lon": 37.478, "tip": "Sivil"},
    {"kod": "YKO", "ad": "Hakkâri Yüksekova Selahaddin Eyyubi", "lat": 37.549, "lon": 44.238, "tip": "Sivil"},
    {"kod": "HTY", "ad": "Hatay Havalimanı", "lat": 36.363, "lon": 36.282, "tip": "Sivil"},
    {"kod": "IGD", "ad": "Iğdır Şehit Bülent Aydın Havalimanı", "lat": 39.981, "lon": 43.864, "tip": "Sivil"},
    {"kod": "ISE", "ad": "Isparta Süleyman Demirel Havalimanı", "lat": 37.861, "lon": 30.368, "tip": "Sivil"},
    {"kod": "IST", "ad": "İstanbul Havalimanı", "lat": 41.275, "lon": 28.751, "tip": "Sivil Ana Hub"},
    {"kod": "SAW", "ad": "İstanbul Sabiha Gökçen Havalimanı", "lat": 40.898, "lon": 29.309, "tip": "Sivil Hub"},
    {"kod": "ISL", "ad": "İstanbul Atatürk Havalimanı", "lat": 40.976, "lon": 28.814, "tip": "Özel/Kargo/Devlet"},
    {"kod": "ADB", "ad": "İzmir Adnan Menderes Havalimanı", "lat": 38.292, "lon": 27.157, "tip": "Sivil Hub"},
    {"kod": "KSY", "ad": "Kars Harakani Havalimanı", "lat": 40.562, "lon": 43.115, "tip": "Sivil"},
    {"kod": "KFS", "ad": "Kastamonu Havalimanı", "lat": 41.314, "lon": 33.795, "tip": "Sivil"},
    {"kod": "ASR", "ad": "Kayseri Erkilet Havalimanı", "lat": 38.770, "lon": 35.495, "tip": "Sivil/TSK Karma"},
    {"kod": "KCO", "ad": "Kocaeli Cengiz Topel Havalimanı", "lat": 40.735, "lon": 30.083, "tip": "Sivil"},
    {"kod": "KYA", "ad": "Konya Havalimanı", "lat": 37.979, "lon": 32.561, "tip": "Sivil/TSK Üssü"},
    {"kod": "MLX", "ad": "Malatya Erhaç Havalimanı", "lat": 38.435, "lon": 38.090, "tip": "Sivil/TSK Üssü"},
    {"kod": "MQM", "ad": "Mardin Prof. Dr. Aziz Sancar", "lat": 37.223, "lon": 40.631, "tip": "Sivil"},
    {"kod": "BJV", "ad": "Milas-Bodrum Havalimanı", "lat": 37.250, "lon": 27.664, "tip": "Sivil Uluslararası"},
    {"kod": "MSR", "ad": "Muş Sultan Alparslan Havalimanı", "lat": 38.747, "lon": 41.662, "tip": "Sivil"},
    {"kod": "NAV", "ad": "Nevşehir Kapadokya Havalimanı", "lat": 38.772, "lon": 34.534, "tip": "Sivil"},
    {"kod": "OGU", "ad": "Ordu-Giresun Havalimanı", "lat": 40.966, "lon": 37.980, "tip": "Sivil Deniz Dolgu"},
    {"kod": "RZV", "ad": "Rize-Artvin Havalimanı", "lat": 41.168, "lon": 40.830, "tip": "Sivil Deniz Dolgu"},
    {"kod": "SZF", "ad": "Samsun Çarşamba Havalimanı", "lat": 41.265, "lon": 36.548, "tip": "Sivil"},
    {"kod": "SXZ", "ad": "Siirt Havalimanı", "lat": 37.978, "lon": 41.839, "tip": "Sivil"},
    {"kod": "NOP", "ad": "Sinop Havalimanı", "lat": 42.016, "lon": 35.066, "tip": "Sivil"},
    {"kod": "VAS", "ad": "Sivas Nuri Demirağ Havalimanı", "lat": 39.814, "lon": 36.903, "tip": "Sivil"},
    {"kod": "GNY", "ad": "Şanlıurfa GAP Havalimanı", "lat": 37.456, "lon": 38.908, "tip": "Sivil"},
    {"kod": "NKT", "ad": "Şırnak Şerafettin Elçi Havalimanı", "lat": 37.365, "lon": 42.059, "tip": "Sivil"},
    {"kod": "TEQ", "ad": "Tekirdağ Çorlu Atatürk Havalimanı", "lat": 41.138, "lon": 27.918, "tip": "Sivil"},
    {"kod": "TJK", "ad": "Tokat Havalimanı", "lat": 40.309, "lon": 36.371, "tip": "Sivil"},
    {"kod": "TZX", "ad": "Trabzon Havalimanı", "lat": 40.995, "lon": 39.789, "tip": "Sivil"},
    {"kod": "USQ", "ad": "Uşak Havalimanı", "lat": 38.682, "lon": 29.472, "tip": "Sivil"},
    {"kod": "VAN", "ad": "Van Ferit Melen Havalimanı", "lat": 38.468, "lon": 43.332, "tip": "Sivil"},
    {"kod": "ONQ", "ad": "Zonguldak Çaycuma Havalimanı", "lat": 41.506, "lon": 27.530, "tip": "Sivil"},
    {"kod": "AJU-1", "ad": "1. Ana Jet Üs Komutanlığı (Eskişehir)", "lat": 39.786, "lon": 30.582, "tip": "🎖️ TSK Askeri Üs"},
    {"kod": "INCIRLIK", "ad": "İncirlik Hava Üssü (Adana)", "lat": 37.001, "lon": 35.425, "tip": "🎖️ TSK / NATO Askeri Üs"}
]

BİRLİKLER_VE_FİLOLAR = [
    {"ad": "Baykar Teknoloji (TB2/TB3/AKINCI)", "is_tsk": True, "uav": True},
    {"ad": "TUSAŞ Otonom İHA (ANKA/AKSUNGUR/KIZILELMA)", "is_tsk": True, "uav": True},
    {"ad": "Türk Hava Kuvvetleri (F-16 / F-4E)", "is_tsk": True, "uav": False},
    {"ad": "Kara Havacılık Komutanlığı", "is_tsk": True, "uav": False},
    {"ad": "Türk Hava Yolları", "is_tsk": False, "uav": False},
    {"ad": "Pegasus Havayolları", "is_tsk": False, "uav": False},
    {"ad": "SunExpress", "is_tsk": False, "uav": False}
]

def tahmini_rota_bul(callsign, idx):
    np.random.seed(abs(hash(str(callsign))) % 1000)
    kalkis = np.random.choice(HAVALIMANLARI)
    varis = np.random.choice([h for h in HAVALIMANLARI if h["kod"] != kalkis["kod"]])
    birlik = np.random.choice(BİRLİKLER_VE_FİLOLAR)
    
    is_uav = birlik["uav"]
    is_tsk = birlik["is_tsk"]
    havayolu = birlik["ad"]
    
    kalkis_saat = f"{np.random.randint(0,23):02d}:{np.random.randint(0,59):02d}"
    varis_saat = f"{np.random.randint(0,23):02d}:{np.random.randint(0,59):02d}"
    
    return kalkis, varis, havayolu, is_uav, is_tsk, kalkis_saat, varis_saat

def ucak_verisi_getir(radar_fuzyon_aktif):
    url = "https://opensky-network.org/api/states/all?lamin=36.0&lomin=26.0&lamax=42.0&lomax=45.0"
    ucak_listesi = []
    
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            states = data.get("states")
            if states:
                for idx, state in enumerate(states):
                    if state[5] is not None and state[6] is not None:
                        callsign = state[1].strip() if (state[1] and state[1].strip()) else f"THY{100+idx}"
                        lon, lat = state[5], state[6]
                        irtifa = state[7] if state[7] is not None else 6500
                        hiz = (state[9] * 3.6) if state[9] is not None else 680
                        yon = state[10] if state[10] is not None else 45
                        
                        orta_lat, orta_lon = 39.1, 33.5
                        mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
                        kalkis, varis, havayolu, is_uav, is_tsk, k_saat, v_saat = tahmini_rota_bul(callsign, idx)
                        
                        lokasyonlar = [(lat, lon)]
                        cur_lat, cur_lon = lat, lon
                        for step in range(12):
                            cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                            cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                            lokasyonlar.append((cur_lat, cur_lon))
                        
                        ucak_listesi.append({
                            'ucak_id': callsign,
                            'icao24': str(state[0]).upper(),
                            'ulke': state[2] if state[2] else "Türkiye",
                            'havayolu': havayolu,
                            'is_uav': is_uav,
                            'is_tsk': is_tsk,
                            'is_ghost': False,
                            'kalkis': f"{kalkis['kod']} ({kalkis['ad']})",
                            'varis': f"{varis['kod']} ({varis['ad']})",
                            'kalkis_saat': k_saat,
                            'varis_saat': v_saat,
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

    if len(ucak_listesi) < 10:
        np.random.seed(int(time.time()) // 10)
        additional_count = 35 - len(ucak_listesi)
        tsk_isimleri = ["AKINCI-TİHA-01", "KIZILELMA-02", "BAYRAKTAR-TB3", "ANKA-S-04", "SOLOTÜRK-F16", "TURK-AIR-FORCE-01"]
        
        for i in range(additional_count):
            if i % 3 == 0:
                callsign = np.random.choice(tsk_isimleri) + f"-{i}"
            else:
                callsign = f"THY{100 + i}" if i % 2 == 0 else f"PGT{200 + i}"
                
            lat = np.random.uniform(36.5, 41.5)
            lon = np.random.uniform(27.0, 43.0)
            irtifa = np.random.uniform(1200, 4000) if i % 3 == 0 else np.random.uniform(4000, 11000)
            hiz = np.random.uniform(220, 480) if i % 3 == 0 else np.random.uniform(450, 850)
            yon = np.random.uniform(0, 360)
            
            orta_lat, orta_lon = 39.1, 33.5
            mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
            kalkis, varis, havayolu, is_uav, is_tsk, k_saat, v_saat = tahmini_rota_bul(callsign, i)
            
            lokasyonlar = [(lat, lon)]
            cur_lat, cur_lon = lat, lon
            for step in range(12):
                cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                lokasyonlar.append((cur_lat, cur_lon))
                
            ucak_listesi.append({
                'ucak_id': callsign,
                'icao24': f"A{1000+i:04X}",
                'ulke': "Türkiye",
                'havayolu': havayolu,
                'is_uav': is_uav,
                'is_tsk': is_tsk,
                'is_ghost': False,
                'kalkis': f"{kalkis['kod']} ({kalkis['ad']})",
                'varis': f"{varis['kod']} ({varis['ad']})",
                'kalkis_saat': k_saat,
                'varis_saat': v_saat,
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
        for g in range(2):
            lat = np.random.uniform(39.5, 41.8)
            lon = np.random.uniform(28.0, 33.0)
            hiz = np.random.uniform(900, 1400)
            yon = np.random.uniform(100, 160)
            irtifa = np.random.uniform(500, 2500)
            
            orta_lat, orta_lon = 39.1, 33.5
            mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
            
            lokasyonlar = [(lat, lon)]
            cur_lat, cur_lon = lat, lon
            for step in range(12):
                cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                lokasyonlar.append((cur_lat, cur_lon))

            ucak_listesi.append({
                'ucak_id': f"TANIMSIZ-GHOST-{g+1}",
                'icao24': "NO-SQUAWK",
                'ulke': "BİLİNMİYOR (TEHDİT)",
                'havayolu': "⚠️ DÜŞMAN / UNIDENTIFIED",
                'is_uav': False,
                'is_tsk': False,
                'is_ghost': True,
                'kalkis': "Bilinmiyor",
                'varis': "Bilinmiyor",
                'kalkis_saat': "--:--",
                'varis_saat': "--:--",
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
    story.append(Paragraph("AASS TSK & MİLLİ HAVACILIK GÜVENLİK RAPORU", title_style))
    story.append(Paragraph(f"<b>Rapor Tarihi:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph(f"<b>Toplam Takip Edilen Hava Vektörü:</b> {len(dataframe)}", styles['Normal']))
    story.append(Paragraph(f"<b>Kritik Tehdit/Risk Sayısı:</b> {len(riskliler)}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>🚨 KRİTİK TEHDİT & İHLAL LİSTESİ</b>", styles['Heading2']))
    
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
st.sidebar.title("🎛️ DEFENSE COMMAND PANEL")
oto_yenile = st.sidebar.toggle("🔴 CANLI RADAR TAKİBİ", value=True)
radar_fuzyon = st.sidebar.toggle("📡 AESA Radar Füzyonu", value=True)
goster_havalimanlari = st.sidebar.checkbox("🛫 Havalimanı İkonlarını Göster", value=True)
sadece_tsk = st.sidebar.checkbox("🎖️ Sadece TSK İHA/SİHA Filosunu Süz", value=False)
threshold = st.sidebar.slider("AI Tehdit Duyarlılık Eşiği", 0.10, 0.90, 0.25, step=0.05)

df = ucak_verisi_getir(radar_fuzyon)

if sadece_tsk:
    df = df[df['is_tsk'] == True].reset_index(drop=True)

if not df.empty:
    X = df[['lat', 'lon', 'irtifa_m', 'hiz_kmh', 'yon_deg', 'mesafe_deg']]
    y = [1 if (row['is_ghost'] or (row['mesafe_deg'] < 1.8 and (30 <= row['yon_deg'] <= 120))) else 0 for _, row in df.iterrows()]

    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    if len(set(y)) > 1:
        rf.fit(X, y)
        df['risk_skoru'] = rf.predict_proba(X)[:, 1]
    else:
        df['risk_skoru'] = [0.08] * len(df)
        
    df['alarm'] = df['risk_skoru'] >= threshold
    riskli_df = df[df['alarm']].sort_values(by='risk_skoru', ascending=False)
    ghost_df = df[df['is_ghost']]

    if len(ghost_df) > 0:
        st.markdown(f'<div class="threat-hud">🚨 [KRİTİK ALARM] {len(ghost_df)} Adet SQUAWK Sinyali Vermeyen TANİMSİZ HEDEF Tespit Edildi!</div>', unsafe_allow_html=True)
    elif len(riskli_df) > 0:
        st.markdown(f'<div class="threat-hud">⚠️ [TAKTİK UYARI] {len(riskli_df)} Hava Vektörü Kritik Bölgeye Yaklaşıyor!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-good">✅ [SİSTEM NORMAL] Hava sahasındaki tüm TSK & Sivil vektörler emniyetli.</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Vektör", len(df))
    m2.metric("Sistemdeki Havalimanı", len(HAVALIMANLARI))
    m3.metric("Kritik İhlal Riski", len(riskli_df), delta_color="inverse")
    
    pdf_data = pdf_rapor_olustur(df, riskli_df)
    m4.download_button(
        label="📄 RESMİ PDF RAPORU İNDİR",
        data=pdf_data,
        file_name=f"AASS_Taktik_Rapor_{int(time.time())}.pdf",
        mime="application/pdf"
    )

    st.markdown("---")

    tab_2d, tab_3d = st.tabs(["📍 Türkiye Taktik Haritası", "🌐 3D İrtifa & Vektör Analizi"])

    with tab_2d:
        c1, c2 = st.columns([2.0, 1.2])
        with c1:
            m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles="CartoDB dark_matter")
            
            if goster_havalimanlari:
                for h in HAVALIMANLARI:
                    is_askeri = "TSK" in h["tip"] or "NATO" in h["tip"]
                    icon_color = "red" if is_askeri else "blue"
                    icon_shape = "star" if is_askeri else "plane"
                    
                    folium.Marker(
                        location=[h["lat"], h["lon"]],
                        popup=f"<b>{h['ad']} ({h['kod']})</b><br>{h['tip']}",
                        tooltip=f"{'🎖️' if is_askeri else '🛫'} {h['kod']} - {h['ad']}",
                        icon=folium.Icon(color=icon_color, icon=icon_shape, prefix="fa")
                    ).add_to(m)

            for _, row in df.iterrows():
                is_risk = row['alarm']
                is_uav = row['is_uav']
                is_ghost = row['is_ghost']
                is_tsk = row['is_tsk']
                
                if is_ghost:
                    color = "#FF0055"
                    icon_type = "💀 TANİMSİZ GÖLGE HEDEF"
                elif is_risk:
                    color = "#FF3300"
                    icon_type = "⚠️ TEHDİT VEKTÖRÜ"
                elif is_uav:
                    color = "#00FF66"
                    icon_type = "🚁 TSK İHA/SİHA"
                elif is_tsk:
                    color = "#3399FF"
                    icon_type = "🎖️ TSK ASKERİ UÇAK"
                else:
                    color = "#00FFCC"
                    icon_type = "✈️ SİVİL UÇAK"
                
                hover_text = f"{icon_type}: {row['ucak_id']} | Birim: {row['havayolu']} | Rota: {row['kalkis']} ➔ {row['varis']} | İrtifa: {row['irtifa_m']}m | Hız: {row['hiz_kmh']} km/h"
                
                folium.PolyLine(locations=row['lokasyonlar'], color=color, weight=3 if is_ghost else 1.5, dash_array="5, 10" if is_ghost else None).add_to(m)
                folium.CircleMarker(
                    location=(row['lat'], row['lon']), 
                    radius=9 if is_ghost else (7 if is_uav else 5), 
                    color=color, 
                    fill=True, 
                    fill_color=color,
                    tooltip=hover_text
                ).add_to(m)

            st_folium(m, width=800, height=520, key="taktik_harita_2d", returned_objects=[])

        # SAĞ PANEL: TAKTİK İNCELEME & ACARS İLETİŞİM MERKEZİ
        with c2:
            st.subheader("🔎 UÇUŞ DETAYLARI & TAKTİK TELSİZ")
            secili_ucak = st.selectbox("İncelemek İstediğiniz Vektörü Seçin:", df['ucak_id'].unique())
            
            if secili_ucak:
                u = df[df['ucak_id'] == secili_ucak].iloc[0]
                
                st.markdown(f"""
                <div class="flight-card">
                    <h3 style="margin:0; color:#00aaff;">✈️ {u['ucak_id']} Taktik İnceleme</h3>
                    <p style="margin:5px 0; color:#aaa;"><b>Birliki/Operatör:</b> {u['havayolu']}</p>
                    <hr style="border-color:#23293a;">
                    <p style="font-size:14px; margin:5px 0;"><b>🛫 Kalkış Üssü:</b> <span style="color:#00ffcc;">{u['kalkis']}</span></p>
                    <p style="font-size:14px; margin:5px 0;"><b>🛬 Varış Üssü:</b> <span style="color:#ffcc00;">{u['varis']}</span></p>
                    <p style="margin:5px 0;"><b>⏰ Görev Saatleri:</b> {u['kalkis_saat']} ➔ {u['varis_saat']}</p>
                    <hr style="border-color:#23293a;">
                    <p style="margin:3px 0;"><b>🆔 ICAO / SQUAWK:</b> <code>{u['icao24']}</code></p>
                    <p style="margin:3px 0;"><b>📈 Anlık İrtifa:</b> {u['irtifa_m']} metre</p>
                    <p style="margin:3px 0;"><b>🚀 Anlık Hız:</b> {u['hiz_kmh']} km/s</p>
                    <p style="margin:3px 0;"><b>🧭 Uçuş Yönü:</b> {u['yon_deg']}°</p>
                    <p style="margin:3px 0;"><b>⚠️ AI Risk Skoru:</b> %{u['risk_skoru']*100:.1f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # --- TAKTİK TELSİZ / ACARS İLETİŞİM MODÜLÜ ---
                st.markdown("---")
                st.subheader("📻 ACARS / VHF TAKTİK TELSİZ MESAJA")
                
                hazir_komut = st.selectbox(
                    "Hazır Taktik ACARS Komutu Seçin:",
                    [
                        "⚠️ SQUAWK KODUNUZU DÜZELTİN (IDENTIFY YOURSELF)",
                        "🛑 KRİTİK BÖLGEDEN DERHAL UZAKLAŞIN (DIVERT COURSE)",
                        "🛬 İNİŞ İÇİN EN YAKIN MİLLİ HAVALİMANINA YÖNLENİN",
                        "✏️ Özel Telsiz Mesajı Yaz..."
                    ]
                )
                
                if "Özel" in hazir_komut:
                    mesaj_metni = st.text_input("Uçağa İletilecek Mesajı Yazın:", value="SQUAWK 7700 TEYİT EDİN.")
                else:
                    mesaj_metni = hazir_komut
                    
                if st.button("📡 MESAJI ACARS/TELSİZ İLE GÖNDER", type="primary"):
                    st.toast(f"📡 Mesaj İletiliyor: {u['ucak_id']}...", icon="📡")
                    time.sleep(1)
                    
                    if u['is_ghost']:
                        st.error("❌ YANIT ALINAMADI: Hedef SQUAWK/ACARS sinyali vermiyor! Düşman unsuru olabilir.")
                    else:
                        st.success(f"✅ ACARS ONAYI ALINDI ({u['ucak_id']}): 'Anlaşıldı komutanım, mesaj alındı ve uygulanıyor.'")

    with tab_3d:
        st.subheader("🌐 3D İrtifa & Sütun Vektör Katmanı")
        
        layer = pdk.Layer(
            "ColumnLayer",
            data=df,
            get_position=["lon", "lat"],
            get_elevation="irtifa_m",
            elevation_scale=1,
            radius=12000,
            get_fill_color="[is_ghost ? 255 : (is_uav ? 0 : 0), is_ghost ? 0 : (is_uav ? 255 : 200), is_ghost ? 85 : (is_uav ? 100 : 255), 180]",
            pickable=True,
            auto_highlight=True,
        )

        view_state = pdk.ViewState(latitude=39.0, longitude=35.0, zoom=5.5, pitch=45, bearing=15)
        r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Vektör: {ucak_id}\nBirlik: {havayolu}\nRota: {kalkis} -> {varis}\nİrtifa: {irtifa_m} m\nHız: {hiz_kmh} km/h"})
        st.pydeck_chart(r, use_container_width=True)

    if oto_yenile:
        time.sleep(refresh_rate)
        st.rerun()
