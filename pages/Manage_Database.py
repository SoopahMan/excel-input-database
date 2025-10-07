import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
import pymysql

st.set_page_config(page_title="Manage Database", layout="wide")
st.title("🗄️ Manage Database")

db_url = st.text_input("Database URL", value="mysql+pymysql://root:@localhost/bss")

if db_url:
    try:
        engine = create_engine(db_url)
        engine.connect()
        st.success("✅ Connected to Database")
    except Exception as e:
        st.error(f"❌ Connection failed: {e}")
        st.stop()

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if tables:
                st.write(f"📋 Total tabel ditemukan: {len(tables)}")
                selected_table = st.selectbox("Pilih tabel untuk melihat data:", tables)

                if selected_table:
                    # tampilkan data preview
                    query = f"SELECT * FROM {selected_table} LIMIT 10"
                    df_preview = pd.read_sql(query, con=engine)
                    st.dataframe(df_preview)

                    if st.button(f"🗑️ Hapus tabel {selected_table}"):
                        try:
                            with engine.begin() as conn:
                                conn.execute(text(f"DROP TABLE {selected_table}"))
                            st.success(f"✅ Tabel '{selected_table}' telah dihapus.")
                        except Exception as e:
                            st.error(f"❌ Gagal menghapus tabel: {e}")
    else:
        st.info("💡 Tidak ada tabel ditemukan di database ini.")
