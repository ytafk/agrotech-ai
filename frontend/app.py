import streamlit as st
import requests
import pandas as pd

# --- Sayfa ayarları ---
st.set_page_config(
    page_title="Agrotech-AI",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_BACKEND = "http://localhost:8000"

# --- Session state ---
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []

# --- Sidebar ---
with st.sidebar:
    st.title("🍎 Agrotech-AI")
    st.caption("Otonom Kalite Kontrol Ajanı")
    st.divider()
    backend_url = st.text_input("Backend URL", DEFAULT_BACKEND)
    st.divider()
    st.markdown("**Ekip**")
    st.markdown("- Üye 1: Vision\n- Üye 2: Backend\n- Üye 3: Frontend")

# --- Ana sekmeler ---
tab1, tab2, tab3 = st.tabs(["📸 Kalite Analizi", "📊 Yönetici Paneli", "ℹ️ Hakkında"])

# === SEKME 1: ANALİZ ===
with tab1:
    col_input, col_output = st.columns([1, 1.2])

    with col_input:
        st.subheader("1. Ürün Fotoğrafı")
        method = st.radio(
            "Yöntem seçin",
            ["📁 Dosya Yükle", "📷 Kameradan Çek"],
            horizontal=True,
            label_visibility="collapsed",
        )

        image_bytes = None
        if method == "📁 Dosya Yükle":
            up = st.file_uploader("Fotoğraf seçin", type=["jpg", "jpeg", "png"])
            if up:
                image_bytes = up.read()
                st.image(image_bytes, use_container_width=True)
        else:
            cam = st.camera_input("Fotoğraf çek")
            if cam:
                image_bytes = cam.getvalue()

        st.subheader("2. Analiz")
        analyze_btn = st.button(
            "🔍 Analiz Et",
            type="primary",
            use_container_width=True,
            disabled=image_bytes is None,
        )

    with col_output:
        st.subheader("Sonuçlar")

        if not image_bytes:
            st.info("👈 Soldan bir fotoğraf yükleyin veya çekin.")
        elif analyze_btn:
            with st.spinner("Backend analiz ediyor..."):
                try:
                    response = requests.post(
                        f"{backend_url}/analyze",
                        files={"file": ("upload.jpg", image_bytes, "image/jpeg")},
                        timeout=30,
                    )
                    if response.status_code == 200:
                        result = response.json()

                        # Metrik kartları
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Toplam Ürün", result["total_items"])
                        m2.metric("✅ Taze", result["fresh"])
                        m3.metric("⚠️ Hasarlı", result["damaged"])
                        m4.metric(
                            "Fire Oranı",
                            f"%{result['fire_rate'] * 100:.1f}",
                            delta=f"-{result['estimated_loss_tl']:.0f} ₺",
                            delta_color="inverse",
                        )

                        st.divider()
                        st.markdown("**Tespit Detayları**")
                        st.dataframe(
                            result["detections"],
                            use_container_width=True,
                            hide_index=True,
                        )

                        # Geçmişe kaydet
                        st.session_state.analysis_history.append({
                            "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
                            "total": result["total_items"],
                            "damaged": result["damaged"],
                            "fire_rate": result["fire_rate"],
                            "loss_tl": result["estimated_loss_tl"],
                        })

                        if result.get("agent_report"):
                            st.divider()
                            st.markdown("**🤖 Ajan Raporu**")
                            st.info(result["agent_report"])
                        else:
                            st.caption("ℹ️ Ajan raporu Pazartesi eklenecek.")
                    else:
                        st.error(f"Backend hatası ({response.status_code}): {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error(
                        f"❌ Backend'e ulaşılamıyor: {backend_url}\n\n"
                        "Üye 2 sunucusu çalışıyor mu?"
                    )
                except Exception as e:
                    st.error(f"Beklenmedik hata: {e}")

# === SEKME 2: YÖNETİCİ PANELİ ===
with tab2:
    st.subheader("Bugünün Analizleri")
    if st.session_state.analysis_history:
        df = pd.DataFrame(st.session_state.analysis_history)
        st.dataframe(df, use_container_width=True, hide_index=True)
        toplam_kayip = sum(a["loss_tl"] for a in st.session_state.analysis_history)
        ortalama_fire = sum(a["fire_rate"] for a in st.session_state.analysis_history) / len(st.session_state.analysis_history)
        c1, c2 = st.columns(2)
        c1.metric("Toplam Tahmini Kayıp", f"{toplam_kayip:.2f} ₺")
        c2.metric("Ortalama Fire Oranı", f"%{ortalama_fire * 100:.1f}")
    else:
        st.info("Henüz analiz yapılmadı. 📸 Kalite Analizi sekmesinden başla.")

# === SEKME 3: HAKKINDA ===
with tab3:
    st.markdown("""
    ### Agrotech-AI

    Tarım kooperatifleri ve gıda işletmeleri için **otonom kalite kontrol ve fire ajanı**.

    **Özellikler:**
    - 📸 Kasadaki ürünlerin anlık kalite analizi (YOLOv8 / Roboflow)
    - 🤖 Multi-agent mimarisi (Quality + Logistics + Communication)
    - 📧 Tedarikçiye otomatik iade maili taslağı
    - ♻️ Sıfır atık lojistik tavsiyesi (salça, kompost yönlendirmesi)

    **Teknolojiler:** FastAPI, Python, Gemini API, Roboflow, Streamlit

    **Hackathon:** Yapay Zeka ve Teknoloji Akademisi 5. Dönem — AI Hackathon
    """)