# ======================================================================
# --- File: page_collective.py (VERSI FINAL & LENGKAP) ---
# ======================================================================
import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
import io

# Impor fungsi yang kita butuhkan dari utils.py
from utils import save_prediction_to_db, preprocess_input_for_pipeline

def show():
    """
    Fungsi ini berisi semua elemen UI dan logika untuk halaman 
    Prediksi Kolektif, yang sudah disinkronkan dengan benar.
    """
    
    st.title("🗂️ Pemeriksaan Risiko Kolektif (Unggah File)")
    st.markdown("Unggah file CSV atau Excel Anda untuk mendapatkan prediksi untuk semua pasien sekaligus.")

    # --- Muat Pipeline Lengkap ---
    @st.cache_resource
    def load_artifacts():
        try:
            pipeline = joblib.load('pregnancy_risk_full_pipeline.pkl')
            feature_names = joblib.load('feature_names.pkl')
            return pipeline, feature_names
        except FileNotFoundError:
            st.error("File model/pipeline tidak ditemukan. Mohon jalankan skrip 'train_model.py'.")
            return None, None

    pipeline, feature_names = load_artifacts()
    if not pipeline or not feature_names:
        st.stop()

    # --- Area untuk Template dan Upload File ---
    col1, col2 = st.columns([1, 3])
    with col1:
        st.subheader("Langkah 1: Unduh Template")
        st.write("Gunakan template ini untuk format data yang benar.")
        
        @st.cache_data
        def get_template_df():
            template_cols = [
                'nama_pasien', 
                'umur_ibu', 'gravida', 'umur_kehamilan', 'tinggi_badan',
                'tekanan_darah', 'penyakit_anemia', 'posisi_janin', 
                'hasil_tes_VDRL', 'hasil_tes_HbsAg'
            ]
            return pd.DataFrame(columns=template_cols)

        template_df = get_template_df()
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            template_df.to_excel(writer, index=False, sheet_name='Data Pasien')
        
        st.download_button(
            "Unduh Template (.xlsx)",
            data=output_excel,
            file_name='template_prediksi_kolektif.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True
        )

    with col2:
        st.subheader("Langkah 2: Unggah File Anda")
        st.write("Pilih file CSV atau Excel yang sudah Anda isi.")
        uploaded_file = st.file_uploader("Pilih file...", type=['csv', 'xlsx'], label_visibility="collapsed")
    
    st.divider()

    # --- Area Utama untuk Proses dan Tampilan Hasil ---
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_input = pd.read_csv(uploaded_file)
            else:
                df_input = pd.read_excel(uploaded_file)
            
            st.subheader("1. Pratinjau Data yang Diunggah")
            st.dataframe(df_input.head(), use_container_width=True)

            if st.button("🚀 Proses dan Prediksi Semua Data", type="primary", use_container_width=True):
                with st.spinner("Membersihkan data dan menjalankan pipeline..."):
                    
                    # PANGGIL FUNGSI PREPROCESSING DARI UTILS
                    df_ready_for_pipeline = preprocess_input_for_pipeline(df_input.copy())

                    # PREDIKSI LANGSUNG
                    predictions = pipeline.predict(df_ready_for_pipeline)
                    
                    # Buat dataframe output dengan data asli dan hasil prediksi
                    df_output = df_input.copy()
                    df_output['hasil_prediksi'] = predictions
                    
                    st.session_state['processed_df_collective'] = df_output

        except Exception as e:
            st.error(f"Terjadi error saat membaca atau memproses file: {e}")
            st.warning("Pastikan format file dan nama kolom sudah sesuai dengan template.")

    # --- Tampilkan hasil ---
    if 'processed_df_collective' in st.session_state:
        df_output = st.session_state['processed_df_collective']
        
        st.subheader("2. Hasil Klasifikasi")
        st.dataframe(df_output, use_container_width=True)

        col_dl, col_save = st.columns(2)
        with col_dl:
            output_buffer = io.BytesIO()
            df_output.to_csv(output_buffer, index=False, encoding='utf-8')
            output_buffer.seek(0)
            st.download_button("Unduh Hasil Prediksi (.csv)", data=output_buffer, file_name='hasil_prediksi_kolektif.csv', mime='text/csv', use_container_width=True)
        
        with col_save:
            if st.button("Simpan Semua Hasil ke Database", use_container_width=True, type="secondary"):
                with st.spinner("Menyimpan semua data ke riwayat..."):
                    success_count = 0
                    fail_count = 0
                    for index, row in df_output.iterrows():
                        data_pasien = row.to_dict()
                        if 'tekanan_darah' in data_pasien and isinstance(data_pasien['tekanan_darah'], str):
                            parts = data_pasien['tekanan_darah'].split('/')
                            data_pasien['tekanan_sistolik'] = parts[0]
                            data_pasien['tekanan_diastolik'] = parts[1]
                        is_saved, message = save_prediction_to_db(data_pasien)
                        if is_saved: success_count += 1
                        else: fail_count += 1
                st.success(f"Penyimpanan Selesai! {success_count} data berhasil disimpan.")
                if fail_count > 0: st.warning(f"{fail_count} data gagal disimpan.")

        st.divider()
        
        st.divider()
        st.header("📊 Visualisasi & Analisis Data")

        # --- VISUALISASI 1: Distribusi Tingkat Risiko (Bar Chart) ---
        st.subheader("Distribusi Tingkat Risiko")
        risk_counts = df_output['hasil_prediksi'].value_counts().reset_index()
        risk_counts.columns = ['Tingkat Risiko', 'Jumlah Pasien']
        
        fig_bar = px.bar(
            risk_counts, 
            x='Tingkat Risiko', 
            y='Jumlah Pasien',
            title='Jumlah Pasien per Kategori Risiko',
            text='Jumlah Pasien',  # Menampilkan angka di atas bar
            color='Tingkat Risiko',
            color_discrete_map={'KRR': '#28a745', 'KRT': '#ffc107', 'KRST': '#dc3545'},
            labels={'Tingkat Risiko': 'Kategori Risiko', 'Jumlah Pasien': 'Jumlah Pasien'}
        )
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)


        # --- VISUALISASI 2: Faktor Risiko Paling Berpengaruh (Feature Importance) ---
        st.subheader("Faktor Risiko Paling Berpengaruh")
        st.info("""
        Grafik ini menunjukkan variabel mana yang paling dipertimbangkan oleh model dalam membuat keputusan.
        Semakin panjang bar, semakin penting faktor tersebut.
        """)

        # Ekstrak model Decision Tree dari dalam pipeline
        model = pipeline.named_steps['classifier']
        
        # Buat DataFrame untuk feature importance
        importance_df = pd.DataFrame({
            'Fitur': feature_names,
            'Tingkat Kepentingan': model.feature_importances_
        }).sort_values(by='Tingkat Kepentingan', ascending=False).head(10) # Ambil 10 teratas

        fig_importance = px.bar(
            importance_df,
            x='Tingkat Kepentingan',
            y='Fitur',
            orientation='h', # Membuatnya jadi horizontal bar chart
            title='10 Faktor Paling Penting dalam Prediksi',
            text='Tingkat Kepentingan',
            labels={'Fitur': 'Faktor Risiko', 'Tingkat Kepentingan': 'Tingkat Kepentingan (%)'}
        )
        fig_importance.update_traces(texttemplate='%{text:.2%}', textposition='outside')
        fig_importance.update_yaxes(categoryorder='total ascending') # Urutkan dari bawah ke atas
        st.plotly_chart(fig_importance, use_container_width=True)

        # --- VISUALISASI 3: Analisis Risiko Berdasarkan Faktor Demografis ---
        st.subheader("Analisis Risiko Berdasarkan Faktor Demografis")
        
        # --- Fungsi Helper untuk membuat kategori umur & gravida ---
        def get_age_group(age):
            if age < 20:
                return "< 20 Tahun"
            elif 20 <= age <= 35:
                return "20-35 Tahun (Optimal)"
            else:
                return "> 35 Tahun"

        def get_gravida_group(gravida):
            if gravida == 1:
                return "1 (Primigravida)"
            elif 2 <= gravida <= 4:
                return "2-4"
            else:
                return "> 4 (Grande Multigravida)"

        # --- LANGKAH KUNCI YANG DIPERBAIKI ---
        # Buat salinan DataFrame dan PASTIKAN TIPE DATA BENAR sebelum apply
        df_viz = df_output.copy()

        # Konversi 'umur_ibu' ke numerik, ganti error dengan NaN lalu 0
        df_viz['umur_ibu'] = pd.to_numeric(df_viz['umur_ibu'], errors='coerce').fillna(0)

        # Ekstrak angka dari 'gravida' dan konversi ke numerik
        df_viz['gravida'] = pd.to_numeric(df_viz['gravida'].astype(str).str.extract(r'(\d+)', expand=False), errors='coerce').fillna(0)
        # ------------------------------------

        # Sekarang aman untuk membuat kolom kelompok
        df_viz['kelompok_umur'] = df_viz['umur_ibu'].apply(get_age_group)
        df_viz['kelompok_gravida'] = df_viz['gravida'].apply(get_gravida_group)

        # --- Membuat Visualisasi dengan Pilihan (Tidak ada perubahan di sini) ---
        st.write("Pilih faktor demografis untuk dianalisis:")
        
        analysis_option = st.selectbox(
            "Analisis Berdasarkan:",
            ("Kelompok Umur", "Jumlah Kehamilan (Gravida)"),
            label_visibility="collapsed"
        )

        if analysis_option == "Kelompok Umur":
            # Hitung jumlah untuk setiap kombinasi kelompok umur dan hasil prediksi
            df_grouped = df_viz.groupby(['kelompok_umur', 'hasil_prediksi']).size().reset_index(name='jumlah')
            
            # Buat Grouped Bar Chart
            fig_demo = px.bar(
                df_grouped,
                x='kelompok_umur',
                y='jumlah',
                color='hasil_prediksi',
                barmode='group', # Ini yang membuat chart menjadi berkelompok
                title='Distribusi Risiko Berdasarkan Kelompok Umur',
                labels={
                    'kelompok_umur': 'Kelompok Umur',
                    'jumlah': 'Jumlah Pasien',
                    'hasil_prediksi': 'Tingkat Risiko'
                },
                color_discrete_map={'KRR': '#28a745', 'KRT': '#ffc107', 'KRST': '#dc3545'},
                text='jumlah' # Menampilkan angka di atas bar
            )
            fig_demo.update_traces(textposition='outside')
            st.plotly_chart(fig_demo, use_container_width=True)

        elif analysis_option == "Jumlah Kehamilan (Gravida)":
            # Hitung jumlah untuk setiap kombinasi kelompok gravida dan hasil prediksi
            df_grouped = df_viz.groupby(['kelompok_gravida', 'hasil_prediksi']).size().reset_index(name='jumlah')

            # Buat Grouped Bar Chart
            fig_demo = px.bar(
                df_grouped,
                x='kelompok_gravida',
                y='jumlah',
                color='hasil_prediksi',
                barmode='group',
                title='Distribusi Risiko Berdasarkan Jumlah Kehamilan',
                labels={
                    'kelompok_gravida': 'Kelompok Jumlah Kehamilan',
                    'jumlah': 'Jumlah Pasien',
                    'hasil_prediksi': 'Tingkat Risiko'
                },
                color_discrete_map={'KRR': '#28a745', 'KRT': '#ffc107', 'KRST': '#dc3545'},
                text='jumlah'
            )
            fig_demo.update_traces(textposition='outside')
            # Urutkan sumbu x secara logis
            fig_demo.update_xaxes(categoryorder='array', categoryarray=['1 (Primigravida)', '2-4', '> 4 (Grande Multigravida)'])
            st.plotly_chart(fig_demo, use_container_width=True)

    else:
        st.info("Silakan unggah file Anda di atas untuk memulai analisis.")