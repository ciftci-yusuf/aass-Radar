# 🛡️ AASS — C4ISR Otonom Milli Hava Sahası Savunma & Önleme Sistemi

AASS (Autonomous Airspace Defense System), Türkiye hava sahası üzerindeki canlı sivil/askeri hava trafiğini OpenSky Network ADS-B verileri ve sanal AESA radar füzyonu ile anlık izleyen, makine öğrenmesi tabanlı bir **C4ISR Komuta Kontrol Portalıdır**.

![AASS C4ISR Platform](https://img.shields.io/badge/Military-C4ISR_HUD-00ff66?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)

---

## ✨ Öne Çıkan Başlıca Yetenekler

* **🚀 Otonom Jet Önleme Geometrisi (Interception Geometry):** SQUAWK sinyali vermeyen "Gölge Temas" tespit edildiğinde, Eskişehir 1. Ana Jet Üssü'nden kalkan F-16'nın düşman uçağını havada ne kadar sürede ve hangi koordinatta yakalayacağını (Intercept Point) trigonometrik fiziki vektör hesabı ile çizer.
* **🎙️ Canlı Askeri Telsiz & Roger Beep Sentezleyici:** Web Audio API ve Web Speech API entegrasyonu ile mikrofondan Türkçe sesli komut alıp, pilot/otonom İHA yanıtını hoparlörden telsiz cızırtısı ve "bip" efekti ile döndürür.
* **🔑 RBAC Yetkilendirme & Giriş Paneli:** Komutan ve Operatör rolleri ile yetki kısıtlaması (Komutan telsiz ve alarm eşik yetkisine sahiptir).
* **📍 53 Türkiye Havalimanı & Üssü:** Adana'dan Zonguldak'a kadar tüm sivil havalimanları ve TSK Ana Jet Üsleri entegredir.
* **🌐 2D & 3D PyDeck İrtifa Katmanı:** 3 boyutlu sütun irtifa haritası ve SAR Uydu Arazisi katmanı.
* **📄 Resmi Taktik Müdahale PDF Raporu:** Canlı verilerden resmi rapor dökümü üretir.

---

## 🔑 Demo Giriş Bilgileri

* **Hava Savunma Komutanı:** Kullanıcı: `admin` | Parola: `1234`
* **Nöbetçi Radar Operatörü:** Kullanıcı: `operator` | Parola: `1234`
