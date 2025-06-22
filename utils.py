# ======================================================================
# --- File: utils.py (VERSI FINAL & LENGKAP) ---
# ======================================================================
import mysql.connector
import hashlib
import pandas as pd
import numpy as np
import streamlit as st

# --- FUNGSI-FUNGSI LOGIKA DATABASE & AUTENTIKASI (TIDAK BERUBAH) ---

def get_db_connection():
    """Membuat koneksi ke database. Tidak menampilkan error di layar."""
    try:
        connection = mysql.connector.connect(
            host=st.secrets.mysql.host,
            user=st.secrets.mysql.user,
            password=st.secrets.mysql.password,
            database=st.secrets.mysql.database
        )
        return connection
    except mysql.connector.Error as e:
        print(f"DATABASE CONNECTION ERROR: {e}")
        return None

def make_hashes(password):
    """Membuat hash dari password."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    """Memeriksa apakah password cocok dengan hash."""
    return make_hashes(password) == hashed_text

def save_prediction_to_db(data_pasien):
    """Menyimpan data prediksi ke database."""
    if not st.session_state.get('logged_in'):
        return False, "Gagal menyimpan: Pengguna tidak login."
    conn = get_db_connection()
    if not conn:
        return False, "Gagal menyimpan: Tidak dapat terhubung ke database."
    try:
        cursor = conn.cursor()
        query = """
        INSERT INTO data_pasien (
            nama_pasien, umur_ibu, gravida, umur_kehamilan, tinggi_badan, 
            tekanan_sistolik, tekanan_diastolik, penyakit_anemia, posisi_janin, 
            hasil_tes_VDRL, hasil_tes_HbsAg, hasil_prediksi, created_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data_pasien.get('nama_pasien'), data_pasien.get('umur_ibu'), data_pasien.get('gravida'), 
            data_pasien.get('umur_kehamilan'), data_pasien.get('tinggi_badan'), 
            data_pasien.get('tekanan_sistolik'), data_pasien.get('tekanan_diastolik'),
            data_pasien.get('penyakit_anemia'), data_pasien.get('posisi_janin'), 
            data_pasien.get('hasil_tes_VDRL'), data_pasien.get('hasil_tes_HbsAg'), 
            data_pasien.get('hasil_prediksi'), st.session_state.get('user_id')
        )
        cursor.execute(query, values)
        conn.commit()
        return True, "Data berhasil disimpan ke riwayat."
    except mysql.connector.Error as e:
        print(f"DATABASE SAVE ERROR: {e}")
        return False, f"Gagal menyimpan: Terjadi error pada database. ({e})"
    finally:
        if conn and conn.is_connected():
            conn.close()

def get_user_history(user_id):
    """Mengambil riwayat prediksi untuk user_id tertentu."""
    conn = get_db_connection()
    if not conn: return None
    try:
        query = """
            SELECT nama_pasien, umur_ibu, gravida, umur_kehamilan, tinggi_badan, 
                   tekanan_sistolik, tekanan_diastolik, penyakit_anemia, posisi_janin, 
                   hasil_tes_VDRL, hasil_tes_HbsAg, hasil_prediksi, created_at
            FROM data_pasien 
            WHERE created_by = %s ORDER BY created_at DESC LIMIT 10
        """
        df_history = pd.read_sql(query, conn, params=(user_id,))
        return df_history
    except Exception as e:
        print(f"ERROR saat mengambil riwayat: {e}")
        return pd.DataFrame()
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- FUNGSI BARU UNTUK DATA CLEANING & FEATURE ENGINEERING ---
# Ini akan menjadi satu-satunya sumber kebenaran untuk preprocessing

def preprocess_input_for_pipeline(df_raw):
    """
    Membersihkan dan melakukan feature engineering pada data mentah
    agar SIAP dimasukkan ke dalam pipeline.
    Output dari fungsi ini adalah DataFrame dengan kolom yang diharapkan pipeline.
    """
    df = df_raw.copy()

    # Fungsi kecil di dalam untuk menangani format feet.inches
    def feet_to_cm(value):
        try:
            feet, inches = map(float, str(value).replace('"', '').replace("'", '').split('.'))
            return round((feet * 30.48) + (inches * 2.54), 2)
        except:
            return value # Kembalikan apa adanya jika format tidak cocok

    # Fungsi kecil di dalam untuk klasifikasi tekanan darah
    def klasifikasi_tekanan_darah(s, d):
        s, d = pd.to_numeric(s, errors='coerce'), pd.to_numeric(d, errors='coerce')
        if pd.isna(s) or pd.isna(d): return 'Tidak diketahui'
        if s < 90 or d < 60: return 'Hipotensi'
        elif 90 <= s < 120 and 60 <= d < 80: return 'Normal'
        elif 120 <= s < 140 or 80 <= d < 90: return 'Prehipertensi'
        elif 140 <= s < 160 or 90 <= d < 100: return 'Hipertensi Stage 1'
        elif s >= 160 or d >= 100: return 'Hipertensi Stage 2'
        else: return 'Tidak diketahui'
    
    # 1. Cleaning kolom numerik dari teks (seperti '3rd', '25 week')
    for col in ['gravida', 'umur_kehamilan']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.extract(r'(\d+)', expand=False), errors='coerce').fillna(0)
    
    # 2. Cleaning dan konversi 'tinggi_badan'
    if 'tinggi_badan' in df.columns:
        df['tinggi_badan'] = df['tinggi_badan'].apply(feet_to_cm).astype(float)

    # 3. Proses 'tekanan_darah' (dari file) atau sistolik/diastolik (dari form)
    if 'tekanan_darah' in df.columns:
        parts = df['tekanan_darah'].astype(str).str.split('/', expand=True)
        sistolik = pd.to_numeric(parts[0], errors='coerce')
        diastolik = pd.to_numeric(parts.get(1), errors='coerce') # .get(1) lebih aman
        df['kategori_tekanan_darah'] = [klasifikasi_tekanan_darah(s, d) for s, d in zip(sistolik, diastolik)]
    elif 'tekanan_sistolik' in df.columns and 'tekanan_diastolik' in df.columns:
        df['kategori_tekanan_darah'] = df.apply(
            lambda row: klasifikasi_tekanan_darah(row['tekanan_sistolik'], row['tekanan_diastolik']),
            axis=1
        )

    # 4. Cleaning kolom kategorikal lain
    if 'penyakit_anemia' in df.columns:
        df['penyakit_anemia'] = df['penyakit_anemia'].fillna("Negatif").replace({'Minimal': 'Positif', 'Medium': 'Positif'})
    for col in ['hasil_tes_VDRL', 'hasil_tes_HbsAg']:
        if col in df.columns:
            df[col] = df[col].replace({'Negative': 'Negatif', 'Positive': 'Positif'})

    return df