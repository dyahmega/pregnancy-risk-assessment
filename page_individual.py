# ======================================================================
# --- File: page_individual.py (VERSI FINAL & LENGKAP) ---
# ======================================================================
import streamlit as st
import pandas as pd
import joblib

# Impor fungsi yang kita butuhkan dari utils.py
from utils import save_prediction_to_db, preprocess_input_for_pipeline

def show():
    """
    Fungsi ini berisi semua elemen UI dan logika untuk halaman 
    Prediksi Individual, yang sudah disinkronkan dengan benar.
    """
    
    st.title("📝 Pemeriksaan Risiko Individual")
    st.info("Silakan isi semua data pasien di bawah ini untuk prediksi.")

    # --- Memuat Pipeline Lengkap ---
    @st.cache_resource
    def load_full_pipeline():
        try:
            # Memuat pipeline yang sudah mencakup semua langkah preprocessing
            pipeline = joblib.load('pregnancy_risk_full_pipeline.pkl')
            return pipeline
        except FileNotFoundError:
            st.error("File 'pregnancy_risk_full_pipeline.pkl' tidak ditemukan. Mohon jalankan skrip 'train_model.py'.")
            return None

    pipeline = load_full_pipeline()
    if not pipeline:
        st.stop()

    # --- Formulir Input Data Pasien ---
    with st.form("individual_prediction_form"):
        st.header("Formulir Data Pasien")
        
        user_profesi = st.session_state.get('profesi', '')
        user_nama_lengkap = st.session_state.get('nama_lengkap', '')
        if user_profesi == 'Ibu Hamil':
            nama_pasien_value = st.text_input('Nama Pasien', value=user_nama_lengkap, disabled=True)
        else:
            nama_pasien_value = st.text_input('Nama Pasien', placeholder='Masukkan nama lengkap pasien...')

        st.divider()

        col1, col2, col3 = st.columns(3)
        with col1:
            umur_ibu = st.number_input('Umur Ibu (tahun)', min_value=15, max_value=60, value=30)
            gravida = st.number_input('Gravida (kehamilan ke-)', min_value=1, value=1)
            penyakit_anemia = st.selectbox('Riwayat Anemia', ['Negatif', 'Positif'])
        with col2:
            tinggi_badan = st.number_input('Tinggi Badan (cm)', min_value=130, max_value=200, value=155)
            tekanan_sistolik = st.number_input('Tekanan Darah Sistolik (mmHg)', min_value=70, max_value=250, value=120)
            posisi_janin = st.selectbox('Posisi Janin', ['Normal', 'Abnormal'])
        with col3:
            umur_kehamilan = st.number_input('Umur Kehamilan (minggu)', min_value=4, max_value=45, value=20)
            tekanan_diastolik = st.number_input('Tekanan Darah Diastolik (mmHg)', min_value=40, max_value=150, value=80)
            hasil_tes_VDRL = st.selectbox('Hasil Tes VDRL', ['Negatif', 'Positif'])
            hasil_tes_HbsAg = st.selectbox('Hasil Tes HbsAg', ['Negatif', 'Positif'])
        
        submitted = st.form_submit_button("Prediksi Tingkat Risiko")

    # --- Logika Setelah Form Disubmit ---
    if submitted:
        if not nama_pasien_value.strip():
            st.warning("Mohon isi Nama Pasien.")
        else:
            with st.spinner("Memproses prediksi..."):
                
                # Kumpulkan data mentah dari form ke dalam dictionary
                raw_input_data = {
                    'umur_ibu': umur_ibu,
                    'gravida': gravida,
                    'umur_kehamilan': umur_kehamilan,
                    'tinggi_badan': tinggi_badan,
                    'penyakit_anemia': penyakit_anemia,
                    'posisi_janin': posisi_janin,
                    'hasil_tes_VDRL': hasil_tes_VDRL,
                    'hasil_tes_HbsAg': hasil_tes_HbsAg,
                    'tekanan_sistolik': tekanan_sistolik,
                    'tekanan_diastolik': tekanan_diastolik
                }
                input_df = pd.DataFrame([raw_input_data])
                
                # PANGGIL FUNGSI PREPROCESSING DARI UTILS
                df_ready_for_pipeline = preprocess_input_for_pipeline(input_df)
                
                # PREDIKSI LANGSUNG PADA DATA YANG SUDAH SIAP
                prediction = pipeline.predict(df_ready_for_pipeline)
                hasil_prediksi = prediction[0]
                
                # Siapkan data untuk disimpan ke database
                data_to_save = raw_input_data.copy()
                data_to_save['nama_pasien'] = nama_pasien_value
                data_to_save['hasil_prediksi'] = hasil_prediksi
                is_saved, message = save_prediction_to_db(data_to_save)

            # Tampilkan hasil
            st.subheader("Hasil Prediksi", divider='rainbow')
            if is_saved: st.success(message)
            else: st.warning(message)
            if hasil_prediksi == 'KRR': st.success("Risiko Rendah (KRR)")
            elif hasil_prediksi == 'KRT': st.warning("Risiko Tinggi (KRT)")
            else: st.error("Risiko Sangat Tinggi (KRST)")