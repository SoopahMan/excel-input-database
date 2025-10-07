import streamlit as st

st.set_page_config(page_title="Excel Database Manager", layout="wide")

st.title("📊 Excel to Database Manager")
st.markdown("""
Selamat datang di aplikasi **Excel Database Manager** 🎉  
Gunakan sidebar atau menu di atas untuk berpindah halaman:
- **📥 Upload Excel** untuk mengimpor data ke database  
- **🗄️ Manage Database** untuk melihat atau menghapus tabel  
- **🔗 Foreign Keys** (opsional) untuk mengelola relasi antar tabel  
""")

st.info("Gunakan menu **Pages** di sidebar kiri bawah untuk membuka halaman lain.")
