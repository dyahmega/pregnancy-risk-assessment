import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from utils import get_db_connection, check_hashes, make_hashes, get_user_history
# Impor modul halaman
import page_individual 
import page_collective

# ======================================================================
# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="Aplikasi Risiko Kehamilan",
    page_icon="🤰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ======================================================================
# --- Fungsi Halaman Profil ---
def show_profile():
    st.title("Profil Pengguna")
    st.write("---")
    st.subheader(f"Nama: {st.session_state.get('nama_lengkap', 'N/A')}")
    st.write(f"**Username:** `{st.session_state.get('username', 'N/A')}`")
    st.write(f"**Profesi:** {st.session_state.get('profesi', 'N/A')}")
    
    st.divider()
    st.subheader("Riwayat 10 Pemeriksaan Terakhir")
    
    user_id = st.session_state.get('user_id')
    history_df = get_user_history(user_id)

    if history_df is None:
        st.error("Gagal terhubung ke database riwayat. Silakan coba lagi nanti.")
    elif history_df.empty:
        st.info("Anda belum memiliki riwayat pemeriksaan. Silakan lakukan pemeriksaan pertama Anda.")
    else:
        # Fungsi untuk mewarnai hasil prediksi agar lebih informatif
        def style_prediksi(val):
            color_map = {'KRR': 'green', 'KRT': 'orange', 'KRST': 'red'}
            return f'color: {color_map.get(val, "black")}; font-weight: bold;'
        
        st.dataframe(
            history_df.style.applymap(style_prediksi, subset=['hasil_prediksi']),
            use_container_width=True
        )

# ======================================================================
# --- Fungsi Halaman Login & Sign Up ---
def show_login_page():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("")
        st.markdown("<h1 style='text-align: center;'>Selamat Datang!</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Silakan masuk untuk melanjutkan</p>", unsafe_allow_html=True)
        st.write("")
        with st.form("login_form"):
            username = st.text_input("Nama pengguna", placeholder="Masukkan nama pengguna Anda")
            password = st.text_input("Kata Sandi", type="password", placeholder="Masukkan kata sandi Anda")
            submitted = st.form_submit_button("Masuk", use_container_width=True)
            if submitted:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                    user_data = cursor.fetchone()
                    conn.close()
                    if user_data and check_hashes(password, user_data["password"]):
                        st.session_state.logged_in = True
                        st.session_state.username = user_data["username"]
                        st.session_state.user_id = user_data["id"]
                        st.session_state.nama_lengkap = user_data["nama_lengkap"]
                        st.session_state.profesi = user_data["profesi"]
                        st.rerun()
                    else:
                        st.error("Nama pengguna atau Kata Sandi salah.")
                else:
                    st.error("Gagal terhubung ke server database.")
        if st.button("Belum punya akun? Daftar sekarang", use_container_width=True, type="secondary"):
            st.session_state.page = "signup"
            st.rerun()

def show_signup_page():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("")
        st.markdown("<h1 style='text-align: center;'>Buat Akun Baru</h1>", unsafe_allow_html=True)
        st.write("")
        with st.form("signup_form"):
            new_nama_lengkap = st.text_input("Nama lengkap", placeholder="Masukkan nama lengkap Anda")
            list_profesi = ['Bidan', 'Dokter', 'Pegawai Rumah Sakit', 'Pegawai Dinas Kesehatan', 'Ibu Hamil', 'Lainnya...']
            profesi_pilihan = st.selectbox("Profesi", list_profesi)
            profesi_final = profesi_pilihan
            if profesi_pilihan == 'Lainnya...':
                profesi_lainnya = st.text_input("Sebutkan profesi Anda:", placeholder="Contoh: Mahasiswa Kebidanan")
                if profesi_lainnya: profesi_final = profesi_lainnya
            new_username = st.text_input("Nama pengguna baru", placeholder="Buat nama pengguna unik")
            new_password = st.text_input("Kata Sandi baru", type="password", placeholder="Minimal 8 karakter")
            confirm_password = st.text_input("Konfirmasi Kata Sandi", type="password", placeholder="Ulangi kata sandi")
            submitted = st.form_submit_button("Daftar", use_container_width=True)
            if submitted:
                if profesi_pilihan == 'Lainnya...' and not profesi_lainnya.strip(): st.warning("Anda memilih 'Lainnya...', mohon sebutkan profesi Anda.")
                elif not all([new_nama_lengkap, profesi_final, new_username, new_password]): st.warning("Mohon isi semua field yang wajib diisi.")
                elif new_password != confirm_password: st.error("Kata Sandi tidak cocok.")
                else:
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT username FROM users WHERE username = %s", (new_username,))
                        if cursor.fetchone(): st.warning("Nama pengguna ini sudah digunakan.")
                        else:
                            hashed_password = make_hashes(new_password)
                            cursor.execute("INSERT INTO users (username, password, nama_lengkap, profesi) VALUES (%s, %s, %s, %s)", (new_username, hashed_password, new_nama_lengkap, profesi_final))
                            conn.commit()
                            st.success("Akun berhasil dibuat! Silakan masuk sekarang.")
                        conn.close()
                    else: st.error("Gagal terhubung ke server database.")
        if st.button("Sudah punya akun? Masuk", use_container_width=True, type="secondary"):
            st.session_state.page = "login"
            st.rerun()

# ======================================================================
# --- KONTROL UTAMA APLIKASI (ROUTER) ---
# ======================================================================

if st.session_state.get("logged_in", False):
    # ---- KONDISI: PENGGUNA SUDAH LOGIN ----
    
    # 1. Tampilkan semua elemen di dalam sidebar
    with st.sidebar:
        # --- HEADER PROFIL KUSTOM ---
        nama_user = st.session_state.get('nama_lengkap', 'Pengguna')
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <div style="background-color: #ddd; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; margin-right: 15px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="#333" class="bi bi-person-fill" viewBox="0 0 16 16">
                        <path d="M3 14s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1zm5-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6"/>
                    </svg>
                </div>
                <h2 style="margin: 0; color: #333;">{nama_user}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

        # --- MENU NAVIGASI ---
        selected_page = option_menu(
            menu_title=None, 
            options=["Profil & Riwayat", "Pemeriksaan Individu", "Pemeriksaan Kolektif"],
            icons=["person-badge", "file-earmark-person-fill", "files"], 
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#4F8BF9", "font-size": "20px"}, 
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#4F8BF9"},
            }
        )

        # --- TOMBOL KELUAR DI BAGIAN BAWAH ---
        st.write("---") # Gunakan divider untuk tampilan lebih bersih
        if st.button("🚪 Keluar", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "login" 
            st.rerun()

    # 2. Tampilkan konten halaman utama SESUAI pilihan dari sidebar
    #    (Blok ini sekarang berada di LUAR 'with st.sidebar:')
    if selected_page == "Profil & Riwayat":
        show_profile() 
    elif selected_page == "Pemeriksaan Individu":
        page_individual.show()
    elif selected_page == "Pemeriksaan Kolektif":
        page_collective.show()

else:
    # ---- KONDISI: PENGGUNA BELUM LOGIN ----
    if st.session_state.get('page', 'login') == 'signup':
        show_signup_page()
    else:
        show_login_page()
