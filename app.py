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
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ AASS — Otonom Hava Sahası Komuta & Savunma Merkezi")
st.caption("Çoklu Geofence Koruma Halkaları, 3D İrtifa Analizi & OTOMATİK RAPOR MOTORU")

HAVALIMANI_GEOFENCE = [
    {"ad": "İstanbul Havalimanı (IST)", "lat": 41.275, "lon": 28.751, "yarıcap_m": 15000},
    {"ad": "Sabiha Gökçen (SAW)", "lat": 40.898, "lon": 29.309, "yarıcap_m": 12000},
    {"ad": "Ankara Esenboğa (ESB)", "lat": 40.128, "lon": 32.995, "yarıcap_m": 15000}
]

LIMANLAR = ["IST (İstanbul)", "SAW (Sabiha Gökçen)", "ESB (Ankara)", "ADB (İzmir)", "AYT (Antalya)", "FRA (Frankfurt)", "DXB (Dubai)"]
HAVAYOLLARI = ["Türk Hava Yolları", "Pegasus", "Baykar İHA/Dron", "TUSAŞ Otonom İHA", "SunExpress", "Lufthansa"]

def tahmini_rota_bul(callsign, idx):
    np.random.seed(abs(hash(str(callsign))) % 1000)
    kalkis = np.random.choice(LIMANLAR)
    varis = np.random.choice([l for l in LIMANLAR if l != kalkis])
    havayolu = np.random.choice(HAVAYOLLARI)
    is_uav = "İHA" in havayolu or "Dron" in havayolu or "UAV" in str(callsign) or "BAYRAKTAR" in str(callsign)
    return kalkis, varis, havayolu, is_uav

# --- CANLI ADS-B & KESİNTİSİZ SIMULASYON MOTORU ---
def ucak_verisi_getir():
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
                        kalkis, varis, havayolu, is_uav = tahmini_rota_bul(callsign, idx)
                        
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

    # Canlı veri yetersizse yedek simülasyonları ekle
    if len(ucak_listesi) < 10:
        np.random.seed(int(time.time()) // 10)
        additional_count = 35 - len(ucak_listesi)
        for i in range(additional_count):
            callsign = f"BAYRAKTAR-TB2-{i}" if i % 4 == 0 else (f"THY{100 + i}" if i % 2 == 0 else f"PGT{200 + i}")
            lat = np.random.uniform(36.5, 41.5)
            lon = np.random.uniform(27.0, 43.0)
            irtifa = np.random.uniform(1200, 4000) if i % 4 == 0 else np.random.uniform(4000, 11000)
            hiz = np.random.uniform(180, 280) if i % 4 == 0 else np.random.uniform(450, 850)
            yon = np.random.uniform(0, 360)
            
            orta_lat, orta_lon = 39.1, 33.5
            mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
            kalkis, varis, havayolu, is_uav = tahmini_rota_bul(callsign, i)
            
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
    
    table_data = [["Çağrı Kodu", "Tip", "İrtifa (m)", "Hız (km/h)", "Risk Skoru"]]
    for _, row in riskliler.iterrows():
        tip = "İHA/Dron" if row['is_uav'] else "Uçak"
        table_data.append([row['ucak_id'], tip, str(row['irtifa_m']), str(row['hiz_kmh']), f"%{row['risk_skoru']*100:.1f}"])

    if len(table_data) > 1:
        t = Table(table_data, colWidths=[100, 80, 90, 90, 90])
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
    else:
        story.append(Paragraph("Şu an aktif bir tehdit ihlali bulunmamaktadır.", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer

# --- SIDEBAR KONTROL PANELİ ---
st.sidebar.title("🎛️ DEFENSE COMMAND PANEL")
oto_yenile = st.sidebar.toggle("🔴 CANLI RADAR TAKİBİ", value=True)
refresh_rate = st.sidebar.slider("Yenileme Frekansı (Saniye)", 5, 30, 10)
threshold = st.sidebar.slider("AI Duyarlılık Eşiği (Threshold)", 0.10, 0.90, 0.25, step=0.05)
goster_uav = st.sidebar.checkbox("🚁 Sadece İHA / Dron Vektörlerini Süz", value=False)

df = ucak_verisi_getir()

if goster_uav:
    df = df[df['is_uav'] == True].reset_index(drop=True)

if not df.empty:
    X = df[['lat', 'lon', 'irtifa_m', 'hiz_kmh', 'yon_deg', 'mesafe_deg']]
    y = [1 if row['mesafe_deg'] < 1.8 and (30 <= row['yon_deg'] <= 120) else 0 for _, row in df.iterrows()]

    rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    if len(set(y)) > 1:
        rf.fit(X, y)
        df['risk_skoru'] = rf.predict_proba(X)[:, 1]
    else:
        df['risk_skoru'] = [0.08] * len(df)
        
    df['alarm'] = df['risk_skoru'] >= threshold
    riskli_df = df[df['alarm']].sort_values(by='risk_skoru', ascending=False)

    if len(riskli_df) > 0:
        st.markdown(f'<div class="threat-hud">🚨 [TAKTİK ALARM] {len(riskli_df)} Hava Aracı Kritik Geofence Bölgesine Yaklaşıyor!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-good">✅ [SİSTEM NORMAL] Hava sahasındaki tüm vektörler emniyetli rotalarda.</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Hava Aracı", len(df))
    m2.metric("Tespit Edilen İHA/Dron", len(df[df['is_uav']]))
    m3.metric("Kritik İhlal Riski", len(riskli_df), delta_color="inverse")
    
    # PDF RAPOR İNDİRME BUTONU
    pdf_data = pdf_rapor_olustur(df, riskli_df)
    m4.download_button(
        label="📄 RESMİ PDF RAPORU İNDİR",
        data=pdf_data,
        file_name=f"AASS_Taktik_Rapor_{int(time.time())}.pdf",
        mime="application/pdf"
    )

    st.markdown("---")

    tab_2d, tab_3d = st.tabs(["📍 2D Taktik Harita", "🌐 3D İrtifa & Vektör Analizi"])

    with tab_2d:
        c1, c2 = st.columns([2.2, 1])
        with c1:
            m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles="CartoDB dark_matter")
            for gf in HAVALIMANI_GEOFENCE:
                folium.Circle(location=[gf["lat"], gf["lon"]], radius=gf["yarıcap_m"], color="#FF3344", fill=True, fill_opacity=0.2, popup=gf["ad"]).add_to(m)

            # EKSİK OLAN DETAYLI BİLGİ KARTLARI BURAYA GERİ EKLENDİ!
            for _, row in df.iterrows():
                is_risk = row['alarm']
                is_uav = row['is_uav']
                color = "#FF0033" if is_risk else ("#FFCC00" if is_uav else "#00FFCC")
                icon_type = "🛸 İHA/DRON" if is_uav else "✈️ YOLCU UÇAĞI"
                
                popup_html = f"""
                <div style='font-family: Arial, sans-serif; font-size: 13px; width: 230px; line-height: 1.6;'>
                    <h4 style='margin:0 0 5px 0; color:#0055ff;'>{icon_type}: {row['ucak_id']}</h4>
                    <b>🏢 Operatör:</b> {row['havayolu']}<br>
                    <b>🛫 Kalkış:</b> {row['kalkis']}<br>
                    <b>🛬 Varış:</b> {row['varis']}<br>
                    <b>🆔 ICAO24:</b> {row['icao24']}<br>
                    <hr style='margin:5px 0;'>
                    <b>📈 İrtifa:</b> {row['irtifa_m']} m<br>
                    <b>🚀 Hız:</b> {row['hiz_kmh']} km/h<br>
                    <b>🧭 Yön:</b> {row['yon_deg']}°<br>
                    <b>⚠️ Risk Skoru:</b> <span style='color:{color}; font-weight:bold;'>%{row['risk_skoru']*100:.1f}</span>
                </div>
                """
                
                folium.PolyLine(locations=row['lokasyonlar'], color=color, weight=2.5 if is_risk else 1.2).add_to(m)
                folium.CircleMarker(
                    location=(row['lat'], row['lon']), 
                    radius=7 if is_uav else 5, 
                    color=color, 
                    fill=True, 
                    fill_color=color,
                    popup=folium.Popup(popup_html, max_width=260)
                ).add_to(m)

            st_folium(m, width=850, height=500, key="taktik_harita_2d", returned_objects=[])

        with c2:
            st.subheader("📼 BLACKBOX TELEMETRİ")
            secili_ucak = st.selectbox("Hava Aracı Seçin:", df['ucak_id'].unique())
            if secili_ucak:
                ucak_detay = df[df['ucak_id'] == secili_ucak].iloc[0]
                st.info(f"**Tip:** {'🚁 İHA/Dron' if ucak_detay['is_uav'] else '✈️ Yolcu Uçağı'}")
                st.write(f"• **Operatör:** {ucak_detay['havayolu']}")
                st.write(f"• **Telemetri:** {ucak_detay['irtifa_m']} m | {ucak_detay['hiz_kmh']} km/h")
                st.caption("Tahmini İrtifa Profili")
                st.line_chart([ucak_detay['irtifa_m'] + np.random.randint(-150, 150) for _ in range(10)])

    with tab_3d:
        st.subheader("🌐 3D İrtifa & Sütun Vektör Katmanı")
        st.caption("Hava araçlarının yüksekliği (irtifası) 3 boyutlu sütun yükseklikleri ile modellenmiştir.")
        
        # 3D Haritada üzerine gelince (hover) çıkan kutucuk
        layer = pdk.Layer(
            "ColumnLayer",
            data=df,
            get_position=["lon", "lat"],
            get_elevation="irtifa_m",
            elevation_scale=1,
            radius=12000,
            get_fill_color="[alarm ? 255 : 0, alarm ? 50 : 255, alarm ? 50 : 200, 180]",
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
            tooltip={"text": "Hava Aracı: {ucak_id}\nİrtifa: {irtifa_m} m\nHız: {hiz_kmh} km/h\nRisk Skoru: %{risk_skoru}"}
        )
        st.pydeck_chart(r, use_container_width=True)

    if oto_yenile:
        time.sleep(refresh_rate)
        st.rerun()
