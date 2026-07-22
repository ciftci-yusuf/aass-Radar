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
    page_title="AASS - DEFENSE & AIRSPACE COMMAND CENTER",
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
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ AASS — Otonom Hava Sahası Komuta & Savunma Merkezi")
st.caption("Gelişmiş Havalimanı Tespiti, Canlı Uçuş Detayları & Rota Analiz Motoru")

# --- TÜRKİYE VE BÖLGE HAVALİMANLARI VERİTABANI ---
HAVALIMANLARI = [
    {"kod": "IST", "ad": "İstanbul Havalimanı", "lat": 41.275, "lon": 28.751, "tip": "Uluslararası Ana Hub"},
    {"kod": "SAW", "ad": "Sabiha Gökçen Havalimanı", "lat": 40.898, "lon": 29.309, "tip": "Uluslararası / Bölgesel"},
    {"kod": "ESB", "ad": "Ankara Esenboğa Havalimanı", "lat": 40.128, "lon": 32.995, "tip": "Protokol & Başkent"},
    {"kod": "ADB", "ad": "İzmir Adnan Menderes", "lat": 38.292, "lon": 27.157, "tip": "Ege Bölge Hub"},
    {"kod": "AYT", "ad": "Antalya Havalimanı", "lat": 36.898, "lon": 30.800, "tip": "Uluslararası Turizm Hub"},
    {"kod": "ADA", "ad": "Adana Şakirpaşa Havalimanı", "lat": 36.982, "lon": 35.280, "tip": "Çukurova Bölgesi"},
    {"kod": "TZX", "ad": "Trabzon Havalimanı", "lat": 40.995, "lon": 39.789, "tip": "Karadeniz Bölgesi"}
]

HAVAYOLLARI = ["Türk Hava Yolları", "Pegasus", "Baykar İHA/Dron", "TUSAŞ Otonom İHA", "SunExpress", "AJet", "Lufthansa", "Emirates"]

def tahmini_rota_bul(callsign, idx):
    np.random.seed(abs(hash(str(callsign))) % 1000)
    kalkis = np.random.choice(HAVALIMANLARI)
    varis = np.random.choice([h for h in HAVALIMANLARI if h["kod"] != kalkis["kod"]])
    havayolu = np.random.choice(HAVAYOLLARI)
    is_uav = "İHA" in havayolu or "Dron" in havayolu or "UAV" in str(callsign) or "BAYRAKTAR" in str(callsign)
    
    # Kalkış ve varış saatleri simülasyonu
    kalkis_saat = f"{np.random.randint(0,23):02d}:{np.random.randint(0,59):02d}"
    varis_saat = f"{np.random.randint(0,23):02d}:{np.random.randint(0,59):02d}"
    
    return kalkis, varis, havayolu, is_uav, kalkis_saat, varis_saat

# --- CANLI ADS-B + AESA RADAR FÜZYON MOTORU ---
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
                        kalkis, varis, havayolu, is_uav, k_saat, v_saat = tahmini_rota_bul(callsign, idx)
                        
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
        additional_count = 30 - len(ucak_listesi)
        for i in range(additional_count):
            callsign = f"BAYRAKTAR-TB2-{i}" if i % 4 == 0 else (f"THY{100 + i}" if i % 2 == 0 else f"PGT{200 + i}")
            lat = np.random.uniform(36.5, 41.5)
            lon = np.random.uniform(27.0, 43.0)
            irtifa = np.random.uniform(1200, 4000) if i % 4 == 0 else np.random.uniform(4000, 11000)
            hiz = np.random.uniform(180, 280) if i % 4 == 0 else np.random.uniform(450, 850)
            yon = np.random.uniform(0, 360)
            
            orta_lat, orta_lon = 39.1, 33.5
            mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
            kalkis, varis, havayolu, is_uav, k_saat, v_saat = tahmini_rota_bul(callsign, i)
            
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

    # GHOST TARGETS (TANİMSİZ TEMASLAR)
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
                'ucak_id': f"BİLİNMEYEN-GHOST-{g+1}",
                'icao24': "NO-SQUAWK",
                'ulke': "BİLİNMİYOR (TANIMSIZ)",
                'havayolu': "⚠️ TEHDİT / ASKERİ UNIDENTIFIED",
                'is_uav': False,
                'is_ghost': True,
                'kalkis': "Bilinmeyen Başlangıç",
                'varis': "Bilinmeyen Hedef",
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

# PDF RAPOR ÜRETİCİ
def pdf_rapor_olustur(dataframe, riskliler):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor("#003366"), spaceAfter=12)
    story.append(Paragraph("AASS HAVACILIK GÜVENLİK & TAKTİK İHLAL RAPORU", title_style))
    story.append(Paragraph(f"<b>Rapor Tarihi:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph(f"<b>Toplam Takip Edilen Obje:</b> {len(dataframe)}", styles['Normal']))
    story.append(Paragraph(f"<b>Tespit Edilen Kritik Riskli Obje Sayısı:</b> {len(riskliler)}", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>🚨 KRİTİK TEHDİT / İHLAL LİSTESİ</b>", styles['Heading2']))
    
    table_data = [["Çağrı Kodu", "Kalkış ➔ Varış", "İrtifa (m)", "Hız (km/h)", "Risk Skoru"]]
    for _, row in riskliler.iterrows():
        table_data.append([row['ucak_id'], f"{row['kalkis']} ➔ {row['varis']}", str(row['irtifa_m']), str(row['hiz_kmh']), f"%{row['risk_skoru']*100:.1f}"])

    if len(table_data) > 1:
        t = Table(table_data, colWidths=[90, 150, 70, 70, 70])
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
radar_fuzyon = st.sidebar.toggle("📡 AESA Radar Füzyonu (Gölge Temas)", value=True)
refresh_rate = st.sidebar.slider("Yenileme Frekansı (Saniye)", 5, 30, 10)
threshold = st.sidebar.slider("AI Duyarlılık Eşiği (Threshold)", 0.10, 0.90, 0.25, step=0.05)
goster_uav = st.sidebar.checkbox("🚁 Sadece İHA / Dron Vektörlerini Süz", value=False)

df = ucak_verisi_getir(radar_fuzyon)

if goster_uav:
    df = df[df['is_uav'] == True].reset_index(drop=True)

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
        st.markdown(f'<div class="threat-hud">🚨 [KRİTİK ALARM] {len(ghost_df)} Adet SQUAWK Sinyali Vermeyen TANİMSİZ GÖLGE HEDEF Tespit Edildi!</div>', unsafe_allow_html=True)
    elif len(riskli_df) > 0:
        st.markdown(f'<div class="threat-hud">⚠️ [TAKTİK UYARI] {len(riskli_df)} Hava Aracı Kritik Geofence Bölgesine Yaklaşıyor!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-good">✅ [SİSTEM NORMAL] Hava sahasındaki tüm vektörler emniyetli rotalarda.</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Hava Aracı", len(df))
    m2.metric("Aktif Havalimanı", len(HAVALIMANLARI))
    m3.metric("Kritik İhlal Riski", len(riskli_df), delta_color="inverse")
    
    pdf_data = pdf_rapor_olustur(df, riskli_df)
    m4.download_button(
        label="📄 RESMİ PDF RAPORU İNDİR",
        data=pdf_data,
        file_name=f"AASS_Taktik_Rapor_{int(time.time())}.pdf",
        mime="application/pdf"
    )

    st.markdown("---")

    tab_2d, tab_3d = st.tabs(["📍 2D Taktik Harita & Havalimanları", "🌐 3D İrtifa & Vektör Analizi"])

    with tab_2d:
        c1, c2 = st.columns([2.0, 1.2])
        with c1:
            m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles="CartoDB dark_matter")
            
            # HAVALİMANI BÖLGELERİ VE KULE İKONLARI
            for h in HAVALIMANLARI:
                folium.Marker(
                    location=[h["lat"], h["lon"]],
                    popup=f"<b>🛫 {h['ad']} ({h['kod']})</b><br>{h['tip']}",
                    tooltip=f"🛫 {h['kod']} - {h['ad']}",
                    icon=folium.Icon(color="blue", icon="plane", prefix="fa")
                ).add_to(m)
                
                # Havalimanı Güvenlik Halkası
                folium.Circle(
                    location=[h["lat"], h["lon"]],
                    radius=12000,
                    color="#0088ff",
                    fill=True,
                    fill_opacity=0.1
                ).add_to(m)

            # UÇAKLAR VE BİLGİ KARTLARI
            for _, row in df.iterrows():
                is_risk = row['alarm']
                is_uav = row['is_uav']
                is_ghost = row['is_ghost']
                
                if is_ghost:
                    color = "#FF0055"
                    icon_type = "💀 TANİMSİZ GÖLGE HEDEF"
                elif is_risk:
                    color = "#FF3300"
                    icon_type = "⚠️ TEHDİT VEKTÖRÜ"
                elif is_uav:
                    color = "#FFCC00"
                    icon_type = "🛸 İHA/DRON"
                else:
                    color = "#00FFCC"
                    icon_type = "✈️ YOLCU UÇAĞI"
                
                popup_html = f"""
                <div style='font-family: Arial, sans-serif; font-size: 13px; width: 240px; line-height: 1.6;'>
                    <h4 style='margin:0 0 5px 0; color:{color};'>{icon_type}: {row['ucak_id']}</h4>
                    <b>🛫 Kalkış:</b> {row['kalkis']} ({row['kalkis_saat']})<br>
                    <b>🛬 Varış:</b> {row['varis']} ({row['varis_saat']})<br>
                    <b>🏢 Operatör:</b> {row['havayolu']}<br>
                    <b>🆔 ICAO / SQUAWK:</b> {row['icao24']}<br>
                    <hr style='margin:5px 0;'>
                    <b>📈 İrtifa:</b> {row['irtifa_m']} m<br>
                    <b>🚀 Hız:</b> {row['hiz_kmh']} km/h<br>
                    <b>🧭 Yön:</b> {row['yon_deg']}°<br>
                    <b>⚠️ AI Risk Skoru:</b> <span style='color:{color}; font-weight:bold;'>%{row['risk_skoru']*100:.1f}</span>
                </div>
                """
                
                folium.PolyLine(locations=row['lokasyonlar'], color=color, weight=3 if is_ghost else (2.5 if is_risk else 1.2), dash_array="5, 10" if is_ghost else None).add_to(m)
                folium.CircleMarker(
                    location=(row['lat'], row['lon']), 
                    radius=9 if is_ghost else (7 if is_uav else 5), 
                    color=color, 
                    fill=True, 
                    fill_color=color,
                    popup=folium.Popup(popup_html, max_width=270)
                ).add_to(m)

            st_folium(m, width=800, height=520, key="taktik_harita_2d", returned_objects=[])

        # SAĞ PANEL: DETAYLI UÇUŞ KARTI VE KİM NEREYE GİDİYOR PANELİ
        with c2:
            st.subheader("🔎 BÜTÜN UÇUŞ VE ROTA DETAYLARI")
            secili_ucak = st.selectbox("Detayını Görmek İstediğiniz Uçağı Seçin:", df['ucak_id'].unique())
            
            if secili_ucak:
                u = df[df['ucak_id'] == secili_ucak].iloc[0]
                
                # DETAYLI BİLGİ KARTI
                st.markdown(f"""
                <div class="flight-card">
                    <h3 style="margin:0; color:#00aaff;">✈️ {u['ucak_id']} Detay Analizi</h3>
                    <p style="margin:5px 0; color:#aaa;"><b>Operatör / Birlik:</b> {u['havayolu']}</p>
                    <hr style="border-color:#23293a;">
                    <p style="font-size:15px; margin:5px 0;"><b>🛫 Kalkış Limanı:</b> <span style="color:#00ffcc;">{u['kalkis']}</span></p>
                    <p style="font-size:15px; margin:5px 0;"><b>🛬 Varış Limanı:</b> <span style="color:#ffcc00;">{u['varis']}</span></p>
                    <p style="margin:5px 0;"><b>⏰ Tahmini Saatler:</b> {u['kalkis_saat']} ➔ {u['varis_saat']}</p>
                    <hr style="border-color:#23293a;">
                    <p style="margin:3px 0;"><b>🆔 ICAO / SQUAWK Kodu:</b> <code>{u['icao24']}</code></p>
                    <p style="margin:3px 0;"><b>📈 Anlık İrtifa:</b> {u['irtifa_m']} metre</p>
                    <p style="margin:3px 0;"><b>🚀 Anlık Hız:</b> {u['hiz_kmh']} km/s</p>
                    <p style="margin:3px 0;"><b>🧭 Uçuş Yönü:</b> {u['yon_deg']}°</p>
                    <p style="margin:3px 0;"><b>⚠️ AI Tehdit/Risk Eşiği:</b> %{u['risk_skoru']*100:.1f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if u['is_ghost']:
                    st.markdown('<div class="ghost-alert">🚨 TANİMSİZ SİZMA HEDEFİ! Transponder kapalı.</div>', unsafe_allow_html=True)
                    st.button("🚀 F-16 ÖNLEME JETİ GÖREVLENDİR", type="primary")

                st.caption("📈 Anlık Telemetri & İrtifa Profili")
                st.line_chart([u['irtifa_m'] + np.random.randint(-120, 120) for _ in range(10)])

    with tab_3d:
        st.subheader("🌐 3D İrtifa & Sütun Vektör Katmanı")
        st.caption("AESA radarından gelen veriler ve havalimanı koordinatları 3D sütun yüksekliği ile modellenmektedir.")
        
        layer = pdk.Layer(
            "ColumnLayer",
            data=df,
            get_position=["lon", "lat"],
            get_elevation="irtifa_m",
            elevation_scale=1,
            radius=12000,
            get_fill_color="[is_ghost ? 255 : (alarm ? 255 : 0), is_ghost ? 0 : (alarm ? 50 : 255), is_ghost ? 85 : (alarm ? 50 : 200), 180]",
            pickable=True,
            auto_highlight=True,
        )

        view_state = pdk.ViewState(
            latitude=39.0,
            longitude=35.0,
            zoom=5.5,
            pitch=45,
            bearing=15
        )

        r = pdk.Deck(
            layers=[layer], 
            initial_view_state=view_state, 
            tooltip={"text": "Hava Aracı: {ucak_id}\nKalkış ➔ Varış: {kalkis} -> {varis}\nİrtifa: {irtifa_m} m\nHız: {hiz_kmh} km/h"}
        )
        st.pydeck_chart(r, use_container_width=True)

    if oto_yenile:
        time.sleep(refresh_rate)
        st.rerun()
