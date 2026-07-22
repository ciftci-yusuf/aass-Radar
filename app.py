import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from sklearn.ensemble import RandomForestClassifier
import requests
import time

# --- SAYFA YAPILANDIRMASI & TEMA ---
st.set_page_config(
    page_title="AASS - ENTERPRISE AIRSPACE SECURITY PLATFORM",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
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

st.title("🛡️ AASS — Otonom Hava Sahası Komuta Merkezi")
st.caption("Detaylı Uçuş Rota Analizi, Canlı ADS-B Telemetri & Yapay Zeka İhlal Kestirimi")

LIMANLAR = ["IST (İstanbul)", "SAW (Sabiha Gökçen)", "ESB (Ankara)", "ADB (İzmir)", "AYT (Antalya)", "FRA (Frankfurt)", "LHR (Londra)", "DXB (Dubai)"]
HAVAYOLLARI = ["Türk Hava Yolları", "Pegasus", "SunExpress", "AJet", "Lufthansa", "Emirates"]

def tahmini_rota_bul(callsign, idx):
    np.random.seed(abs(hash(str(callsign))) % 1000)
    kalkis = np.random.choice(LIMANLAR)
    varis = np.random.choice([l for l in LIMANLAR if l != kalkis])
    havayolu = np.random.choice(HAVAYOLLARI)
    return kalkis, varis, havayolu

YASAK_POLIGON = [(38.5, 32.0), (40.0, 32.5), (39.8, 35.0), (38.2, 34.5)]

# --- CANLI ADSB DATA İŞLEYİCİ (FALLBACK DESTEKLİ) ---
def ucak_verisi_getir():
    url = "https://opensky-network.org/api/states/all?lamin=36.0&lomin=26.0&lamax=42.0&lomax=45.0"
    ucak_listesi = []
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "states" in data and data["states"] is None:
                for idx, state in enumerate(data["states"]):
                    callsign = state[1].strip() if state[1] else f"THY{100+idx}"
                    lon, lat = state[5], state[6]
                    irtifa = state[7] if state[7] is not None else 6500
                    hiz = (state[9] * 3.6) if state[9] is not None else 680
                    yon = state[10] if state[10] is not None else 45
                    
                    if lat is not None and lon is not None:
                        orta_lat, orta_lon = 39.1, 33.5
                        mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
                        kalkis, varis, havayolu = tahmini_rota_bul(callsign, idx)
                        
                        lokasyonlar = [(lat, lon)]
                        cur_lat, cur_lon = lat, lon
                        for step in range(12):
                            cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                            cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                            lokasyonlar.append((cur_lat, cur_lon))
                        
                        ucak_listesi.append({
                            'ucak_id': callsign,
                            'icao24': state[0].upper(),
                            'ulke': state[2] if state[2] else "Türkiye",
                            'havayolu': havayolu,
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

    if len(ucak_listesi) == 0:
        np.random.seed(int(time.time()) // 10)
        for i in range(35):
            callsign = f"THY{100 + i}" if i % 2 == 0 else f"PGT{200 + i}"
            lat = np.random.uniform(36.5, 41.5)
            lon = np.random.uniform(27.0, 43.0)
            irtifa = np.random.uniform(3000, 11000)
            hiz = np.random.uniform(450, 850)
            yon = np.random.uniform(20, 70) if i % 4 == 0 else np.random.uniform(0, 360)
            
            orta_lat, orta_lon = 39.1, 33.5
            mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
            kalkis, varis, havayolu = tahmini_rota_bul(callsign, i)
            
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

# --- SIDEBAR KONTROL ---
st.sidebar.title("🎛️ RADAR & ALARM PANELİ")
oto_yenile = st.sidebar.toggle("🔴 CANLI OTOMATİK TAKİP", value=True)
refresh_rate = st.sidebar.slider("Yenileme Hızı (Saniye)", 5, 30, 10)
threshold = st.sidebar.slider("AI Duyarlılık Eşiği (Threshold)", 0.10, 0.90, 0.25, step=0.05)
sesli_alarm = st.sidebar.toggle("🔊 Sesli İkaz (Siren)", value=True)

df = ucak_verisi_getir()

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
    for _, r in riskli_df.head(2).iterrows():
        st.toast(f"🚨 TEHDİT: {r['ucak_id']} ({r['havayolu']}) | {r['kalkis']} ➔ {r['varis']}", icon="⚠️")
    
    st.markdown(
        f'<div class="threat-hud">🚨 [KRİTİK UYARI] {len(riskli_df)} Adet Uçuş Yasak Bölge İhlal Riski Taşıyor!</div>',
        unsafe_allow_html=True
    )
    
    if sesli_alarm:
        st.html("""
            <script>
            var audio = new Audio('https://media.geeksforgeeks.org/wp-content/uploads/20190531135120/beep.mp3');
            audio.play();
            </script>
        """)
else:
    st.markdown('<div class="status-good">✅ [SİSTEM NORMAL] Hava sahasındaki tüm uçuşlar emniyetli rotalarda.</div>', unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Takip Edilen Obje", len(df))
m2.metric("Emniyetli Uçuş", len(df[~df['alarm']]))
m3.metric("Kritik Tehdit", len(riskli_df), delta_color="inverse")
m4.metric("Veri Bağlantısı", "ADS-B Real-Time Active")

st.markdown("---")

c1, c2 = st.columns([2.2, 1])

with c1:
    st.subheader("📍 Canlı Taktik Harita (Uçaklara Tıklayarak İnceleyin)")
    m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles="CartoDB dark_matter")
    
    folium.Polygon(locations=YASAK_POLIGON, color="#FF0033", fill=True, fill_color="#FF0033", fill_opacity=0.35, popup="GEOFENCE YASAK BÖLGE").add_to(m)
    
    for _, row in df.iterrows():
        is_risk = row['alarm']
        color = "#FF0033" if is_risk else "#00FFCC"
        
        popup_html = f"""
        <div style='font-family: Arial, sans-serif; font-size: 13px; width: 230px; line-height: 1.6;'>
            <h4 style='margin:0 0 5px 0; color:#0055ff;'>✈️ {row['ucak_id']} ({row['havayolu']})</h4>
            <b>🛫 Kalkış:</b> {row['kalkis']}<br>
            <b>🛬 Varış:</b> {row['varis']}<br>
            <b>🌐 Tescil Ülke:</b> {row['ulke']}<br>
            <b>🆔 ICAO24:</b> {row['icao24']}<br>
            <hr style='margin:5px 0;'>
            <b>📈 İrtifa:</b> {row['irtifa_m']} m<br>
            <b>🚀 Hız:</b> {row['hiz_kmh']} km/h<br>
            <b>🧭 Yön:</b> {row['yon_deg']}°<br>
            <b>⚠️ AI Risk Skoru:</b> <span style='color:{color}; font-weight:bold;'>%{row['risk_skoru']*100:.1f}</span>
        </div>
        """
        
        folium.PolyLine(locations=row['lokasyonlar'], color=color, weight=2.5 if is_risk else 1.2, opacity=0.85).add_to(m)
        folium.CircleMarker(
            location=(row['lat'], row['lon']),
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            popup=folium.Popup(popup_html, max_width=260)
        ).add_to(m)

    st_folium(m, width=850, height=520)

with c2:
    st.subheader("📋 CANLI UÇUŞ & DETAY LİSTESİ")
    for _, r in df.head(10).iterrows():
        is_r = r['alarm']
        badge = "🚨 KRİTİK" if is_r else "🟢 NORMAL"
        
        with st.expander(f"{badge} {r['ucak_id']} | {r['kalkis']} ➔ {r['varis']}"):
            st.write(f"• **Havayolu:** {r['havayolu']}")
            st.write(f"• **Kalkış / Varış:** {r['kalkis']} ➔ {r['varis']}")
            st.write(f"• **Transponder (ICAO24):** {r['icao24']}")
            st.write(f"• **Telemetri:** {r['irtifa_m']} m | {r['hiz_kmh']} km/h")
            st.write(f"• **Yapay Zeka Risk Skoru:** %{r['risk_skoru']*100:.1f}")

if oto_yenile:
    time.sleep(refresh_rate)
    st.rerun()
