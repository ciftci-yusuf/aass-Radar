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

# --- SAYFA YAPILANDIRMASI & C4ISR HUD TEMA ---
st.set_page_config(
    page_title="AASS - C4ISR AIRSPACE DEFENSE CENTER",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# MILITARY HUD STYLES
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
        margin-top: 15px;
        box-shadow: 0 0 10px rgba(0,255,102,0.2);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="hud-title">🛡️ AASS C4ISR — ASKERİ HAVA SAHASI SAVUNMA & ÖNLEME SİSTEMİ</h1>', unsafe_allow_html=True)
st.caption("Otonom Önleme Geometrisi, C4ISR HUD Arayüzü, Taktik Telsiz & SAR Katmanı")

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

def en_yakin_havalimani(lat, lon):
    en_kucuk = 999999
    secilen = HAVALIMANLARI[0]
    for h in HAVALIMANLARI:
        d = np.sqrt((lat - h["lat"])**2 + (lon - h["lon"])**2)
        if d < en_kucuk:
            en_kucuk = d
            secilen = h
    return secilen

# ÖNLEME GEOMETRİSİ HESAPLAYICI (INTERCEPTION POINT)
def onleme_noktasi_hesapla(target_lat, target_lon, target_speed, target_heading, base_lat, base_lon, jet_speed=1800):
    # F-16 supersonic hızı ile hedef uçak arasındaki buluşma noktasını hesaplar
    t_rad = np.radians(target_heading)
    v_target_x = target_speed * np.sin(t_rad)
    v_target_y = target_speed * np.cos(t_rad)
    
    dx = (target_lon - base_lon) * 111000
    dy = (target_lat - base_lat) * 111000
    
    # Basitleştirilmiş vektörel kesişim süresi
    t_intercept = np.sqrt(dx**2 + dy**2) / (jet_speed * 1000 / 3600) # Saniye
    
    intercept_lat = target_lat + (v_target_y * (t_intercept / 3600)) / 111
    intercept_lon = target_lon + (v_target_x * (t_intercept / 3600)) / (111 * np.cos(np.radians(target_lat)))
    
    return intercept_lat, intercept_lon, round(t_intercept, 1)

def ucak_verisi_getir(radar_fuzyon_aktif):
    url = "https://opensky-network.org/api/states/all?lamin=36.0&lomin=26.0&lamax=42.0&lomax=45.0"
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
                        
                        is_uav = "BAYRAKTAR" in callsign or "AKINCI" in callsign or "ANKA" in callsign
                        is_tsk = is_uav or "TUAF" in callsign or "TURK" in callsign
                        havayolu = "TSK / Milli Filo" if is_tsk else "Sivil Hava Trafiği"
                        
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
                        
                        ucak_listesi.append({
                            'ucak_id': callsign,
                            'icao24': str(state[0]).upper(),
                            'havayolu': havayolu,
                            'is_uav': is_uav,
                            'is_tsk': is_tsk,
                            'is_ghost': False,
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

    # DÜŞMAN GÖLGE TEMAS
    if radar_fuzyon_aktif:
        np.random.seed(int(time.time()) // 5)
        for g in range(1):
            lat, lon = 40.2, 31.8
            hiz, yon, irtifa = 1100, 120, 1800
            
            orta_lat, orta_lon = 39.1, 33.5
            mesafe = np.sqrt((lat - orta_lat)**2 + (lon - orta_lon)**2)
            
            lokasyonlar = [(lat, lon)]
            cur_lat, cur_lon = lat, lon
            for step in range(12):
                cur_lat += np.cos(np.radians(yon)) * (hiz / 111000)
                cur_lon += np.sin(np.radians(yon)) * (hiz / (111000 * np.cos(np.radians(cur_lat))))
                lokasyonlar.append((cur_lat, cur_lon))

            ucak_listesi.append({
                'ucak_id': "TEHDİT-GHOST-ALPHA",
                'icao24': "NO-SQUAWK",
                'havayolu': "⚠️ UNIDENTIFIED HOSTILE",
                'is_uav': False,
                'is_tsk': False,
                'is_ghost': True,
                'kalkis': "Bilinmiyor",
                'varis': "Ankara Esenboğa Yaklaşması",
                'lat': lat,
                'lon': lon,
                'irtifa_m': round(irtifa, 1),
                'hiz_kmh': round(hiz, 1),
                'yon_deg': round(yon, 1),
                'mesafe_deg': mesafe,
                'lokasyonlar': lokasyonlar
            })
            
    return pd.DataFrame(ucak_listesi)

# --- SIDEBAR KONTROL PANELİ ---
st.sidebar.title("🎛️ C4ISR COMMAND PANEL")
oto_yenile = st.sidebar.toggle("🔴 CANLI RADAR TARAMASI", value=True)
refresh_rate = st.sidebar.slider("Tarama Frekansı (Saniye)", 5, 30, 10)
radar_fuzyon = st.sidebar.toggle("📡 AESA Radar Füzyonu (Gölge Temas)", value=True)
sar_katmani = st.sidebar.toggle("🛰️ SAR Uydu Katmanı", value=False)
sadece_tsk = st.sidebar.checkbox("🎖️ Sadece TSK Filosunu Göster", value=False)
threshold = st.sidebar.slider("AI Duyarlılık Eşiği", 0.10, 0.90, 0.25, step=0.05)

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
        st.markdown(f'<div class="threat-hud">🚨 [C4ISR KRİTİK ALARM] Transponder Sinyali Vermeyen DÜŞMAN UNSURU Tespit Edildi! Otonom Önleme Aktif!</div>', unsafe_allow_html=True)
    elif len(riskli_df) > 0:
        st.markdown(f'<div class="threat-hud">⚠️ [TAKTİK UYARI] {len(riskli_df)} Hava Aracı Kritik Geofence Bölgesinde!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-good">✅ [SİSTEM NORMAL] Türkiye Hava Sahası Tam Güvenlik Altında.</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Vektör", len(df))
    m2.metric("TSK İHA/SİHA", len(df[df['is_uav']]))
    m3.metric("Kritik İhlal Riski", len(riskli_df), delta_color="inverse")
    m4.metric("AESA Radar Durumu", "AKTİF / FÜZYON")

    st.markdown("---")

    tab_2d, tab_3d = st.tabs(["📍 C4ISR Taktik Harita & Önleme Geometrisi", "🌐 3D İrtifa & Vektör Analizi"])

    with tab_2d:
        c1, c2 = st.columns([2.0, 1.2])
        with c1:
            tiles_type = "Stamen Terrain" if sar_katmani else "CartoDB dark_matter"
            m = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles=tiles_type)
            
            for h in HAVALIMANLARI:
                is_askeri = "TSK" in h["tip"] or "NATO" in h["tip"]
                icon_color = "red" if is_askeri else "blue"
                folium.Marker(
                    location=[h["lat"], h["lon"]],
                    popup=f"<b>{h['ad']} ({h['kod']})</b>",
                    icon=folium.Icon(color=icon_color, icon="star" if is_askeri else "plane", prefix="fa")
                ).add_to(m)

            # EĞER DÜŞMAN GÖLGE HEDEF VARSA OTONOM F-16 ÖNLEME ÇİZGİSİ VE BULUŞMA NOKTASI ÇİZ
            if len(ghost_df) > 0:
                g_target = ghost_df.iloc[0]
                base_jet = HAVALIMANLARI[7] # Eskişehir 1. Ana Jet Üssü
                
                i_lat, i_lon, t_sec = onleme_noktasi_hesapla(
                    g_target['lat'], g_target['lon'], g_target['hiz_kmh'], g_target['yon_deg'],
                    base_jet['lat'], base_jet['lon']
                )
                
                # F-16 Önleme Rotası
                folium.PolyLine(
                    locations=[(base_jet['lat'], base_jet['lon']), (i_lat, i_lon)],
                    color="#00ff66", weight=3, dash_array="10, 10",
                    tooltip=f"🚀 SOLOTÜRK F-16 Önleme Vektörü (Tahmini Temas: {t_sec}s)"
                ).add_to(m)
                
                # Önleme / Buluşma Noktası Hedef Çemberi
                folium.CircleMarker(
                    location=(i_lat, i_lon), radius=12, color="#ff0000", fill=True, fill_color="#ff0000",
                    popup=f"🎯 TAHMİNİ ÖNLEME / TEMAS NOKTASI (Süre: {t_sec} sn)"
                ).add_to(m)

            for _, row in df.iterrows():
                is_ghost = row['is_ghost']
                is_risk = row['alarm']
                is_uav = row['is_uav']
                
                color = "#FF0055" if is_ghost else ("#FF3300" if is_risk else ("#00FF66" if is_uav else "#00FFCC"))
                hover_text = f"{row['ucak_id']} | Birim: {row['havayolu']} | Rota: {row['kalkis']} ➔ {row['varis']} | İrtifa: {row['irtifa_m']}m"
                
                folium.PolyLine(locations=row['lokasyonlar'], color=color, weight=3 if is_ghost else 1.5).add_to(m)
                folium.CircleMarker(
                    location=(row['lat'], row['lon']), radius=9 if is_ghost else 6, color=color, fill=True, fill_color=color, tooltip=hover_text
                ).add_to(m)

            st_folium(m, width=800, height=520, key="taktik_harita_2d", returned_objects=[])

        with c2:
            st.subheader("🔎 TAKTİK HEDEF İNCELEME & SESLİ TELSİZ")
            secili_ucak = st.selectbox("İncelemek İstediğiniz Canlı Vektörü Seçin:", df['ucak_id'].unique())
            
            if secili_ucak:
                u = df[df['ucak_id'] == secili_ucak].iloc[0]
                
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
                    <p style="margin:3px 0;"><b>⚠️ AI Risk Skoru:</b> %{u['risk_skoru']*100:.1f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # CIZIRTILI & ASKERİ ROGER BEEP SESLİ TELSİZ MODÜLÜ
                st.markdown("---")
                st.subheader("📻 VHF TAKTİK TELSİZ (MİKROFON / BEEP EFEKTLİ)")
                
                is_ghost_val = "true" if u['is_ghost'] else "false"
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
                // Askeri Telsiz Cızırtısı ve Roger Beep Sentezleyici
                function playRadioBeepAndSpeak(text) {{
                    var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    
                    // Mandal Sesi (Roger Beep)
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
                            msg.pitch = 0.85; // Telsiz tonu için hafif kalın ses
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
                                var answer = "Cızırtı... Yanıt alınamadı. SQUAWK Sinyali Yok!";
                                reply.innerHTML = "❌ " + answer;
                                playRadioBeepAndSpeak("Sinyal yok. Hedef yanıt vermiyor.");
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
        r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Vektör: {ucak_id}\nBirlik: {havayolu}\nİrtifa: {irtifa_m} m\nHız: {hiz_kmh} km/h"})
        st.pydeck_chart(r, use_container_width=True)

    if oto_yenile:
        time.sleep(refresh_rate)
        st.rerun()
