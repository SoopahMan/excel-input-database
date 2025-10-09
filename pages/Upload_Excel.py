import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from collections import defaultdict
import re
import os
from itertools import combinations
from helpers import normalize_col, safe_convert_for_key, clean_table_name
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# -------------------------------
# 🔹 SESSION STATE INITIALIZATION
# -------------------------------
if 'sheet_data_selected' not in st.session_state:
    st.session_state['sheet_data_selected'] = {}
if 'combined_sheets' not in st.session_state:
    st.session_state['combined_sheets'] = {}
if 'fk_selection' not in st.session_state:
    st.session_state['fk_selection'] = {}
if 'pk_selection' not in st.session_state:
    st.session_state['pk_selection'] = {}
db_url = os.getenv("DB_URL")

# -------------------------------
# 📂 UPLOAD FILE
# -------------------------------
uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])
if db_url is None:
    db_url = st.text_input("Database URL")
    
prefix_global = st.text_input("Prefix nama tabel", value="case1_")

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    st.success(f"Workbook terdeteksi ✅ {len(sheet_names)} sheet ditemukan.")

    # -------------------------------
    # 1️⃣ PILIH TABEL SINGLE
    # -------------------------------
    st.subheader("1️⃣ Pilih Tabel yang Ingin Diimpor")
    remaining_sheets = [s for s in sheet_names if s not in st.session_state['combined_sheets']]
    selected_single_sheets = st.multiselect(
        "Pilih sheet untuk tabel single:",
        remaining_sheets
    )

    # Load selected sheet ke session_state
    for sheet in selected_single_sheets:
        if sheet not in st.session_state['sheet_data_selected']:
            df = xls.parse(sheet)
            st.session_state['sheet_data_selected'][sheet] = {
                "df": df,
                "normalized_cols": {normalize_col(c): c for c in df.columns},
                "pk": None
            }

    # -------------------------------
    # 2️⃣ SHEET GROUPING
    # -------------------------------
    st.subheader("2️⃣ Pilih Sheet Group (Hanya jika ada lebih dari 1 sheet serupa)")
    sheet_groups = defaultdict(list)
    for sheet in remaining_sheets:
        base_prefix = re.split(r'[\s_-]+', sheet.lower())[0]
        sheet_groups[base_prefix].append(sheet)
    
    # Filter grup sheet yang hanya memiliki >1 sheet
    sheet_groups = {k: v for k, v in sheet_groups.items() if len(v) > 1}

    selected_groups = st.multiselect(
        "Pilih grup sheet yang ingin digabung:",
        list(sheet_groups.keys())
    )

    if st.button("🔄 Gabungkan Sheet Group"):
        for group in selected_groups:
            sheets_to_combine = sheet_groups[group]
            dfs = []
            for s in sheets_to_combine:
                if s in st.session_state['sheet_data_selected']:
                    dfs.append(st.session_state['sheet_data_selected'][s]["df"])
                else:
                    dfs.append(xls.parse(s))
            combined_df = pd.concat(dfs, ignore_index=True)
            combined_df.columns = [c.strip().replace(" ", "_").replace("-", "_").lower() for c in combined_df.columns]
            st.session_state['combined_sheets'][group] = {
                "df": combined_df,
                "normalized_cols": {normalize_col(c): c for c in combined_df.columns},
                "pk": None
            }
            st.success(f"✅ Digabung: {', '.join(sheets_to_combine)} → '{group}'")

    # -------------------------------
    # 3️⃣ PILIH PK
    # -------------------------------
    st.subheader("3️⃣ Pilih Primary Key (PK)")
    sheet_data_for_keys = {**st.session_state['sheet_data_selected'], **st.session_state['combined_sheets']}

    for table_name, data in sheet_data_for_keys.items():
        st.markdown(f"### {table_name}")
        st.dataframe(data["df"].head(5))
        pk_col = st.selectbox(
            f"Pilih kolom PK untuk `{table_name}`",
            options=["(tanpa PK)"] + list(data["df"].columns),
            key=f"pk_{table_name}"
        )
        st.session_state['pk_selection'][table_name] = None if pk_col == "(tanpa PK)" else pk_col
        sheet_data_for_keys[table_name]["pk"] = st.session_state['pk_selection'][table_name]

    # -------------------------------
    # 4️⃣ DETEKSI & PILIH FK
    # -------------------------------
    st.subheader("4️⃣ Pilih Foreign Key (FK)")
    table_items = list(sheet_data_for_keys.items())
    common_map = {}
    for i in range(len(table_items)):
        sheet_a, data_a = table_items[i]
        cols_a = data_a["normalized_cols"]
        for j in range(i+1, len(table_items)):
            sheet_b, data_b = table_items[j]
            cols_b = data_b["normalized_cols"]
            common_norm = set(cols_a.keys()) & set(cols_b.keys())
            for norm_name in common_norm:
                col_a = cols_a[norm_name]
                col_b = cols_b[norm_name]
                if pd.api.types.is_datetime64_any_dtype(data_a["df"][col_a]):
                    continue
                common_map.setdefault(norm_name, {"original_names": set([col_a, col_b]), "sheets": set([sheet_a, sheet_b])})
                common_map[norm_name]["sheets"].update([sheet_a, sheet_b])

    if common_map:
        st.markdown("#### Checklist kolom untuk dijadikan FK")
        for norm_col, info in common_map.items():
            col_display = ", ".join(info["original_names"])
            st.write(f"Kolom mirip: `{col_display}`")
            selected_sheets = st.multiselect(
                f"FK `{col_display}` akan menghubungkan tabel:",
                options=list(info["sheets"]),
                key=f"fk_{norm_col}"
            )
            st.session_state['fk_selection'][norm_col] = {
                "original_names": info["original_names"],
                "selected_sheets": selected_sheets
            }

    # -------------------------------
    # 5️⃣ IMPORT KE DATABASE
    # -------------------------------
    mode = st.radio("Mode penyimpanan:", ["replace", "append"], horizontal=True)

    if st.button("🚀 Import ke Database"):
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Simpan semua tabel
            for table_name, data in sheet_data_for_keys.items():
                df = data["df"]
                pk = data.get("pk")
                if pk:
                    df = safe_convert_for_key(df, pk)
                table_clean = clean_table_name(f"{prefix_global}{table_name}")
                st.write(f"Menyimpan `{table_clean}` ({mode}) ...")
                df.to_sql(table_clean, conn, index=False, if_exists=mode)
                if pk:
                    try:
                        conn.execute(text(f"""
                            ALTER TABLE `{table_clean}` 
                            MODIFY `{pk}` VARCHAR(255),
                            ADD PRIMARY KEY (`{pk}`);
                        """))
                        st.success(f"✅ PK `{pk}` ditambahkan ke `{table_clean}`")
                    except Exception as e:
                        st.warning(f"⚠️ Gagal menambahkan PK `{pk}`: {e}")

            # -------------------------------
            # Tambah FK
            # -------------------------------
            fk_selection = st.session_state.get('fk_selection', {})
            for norm_col, info in fk_selection.items():
                sheets = info["selected_sheets"]
                if len(sheets) > 1:
                    # Gunakan kolom yang sudah dinormalisasi sebagai referensi
                    ref_table = clean_table_name(f"{prefix_global}{sheets[0]}")
                    # Ambil nama kolom yang sudah dinormalisasi
                    ref_col_norm = normalize_col(list(info["original_names"])[0])
                    ref_col = sheet_data_for_keys[sheets[0]]["normalized_cols"].get(ref_col_norm)

                    for sheet in sheets[1:]:
                        table_name = clean_table_name(f"{prefix_global}{sheet}")
                        local_col = sheet_data_for_keys[sheet]["normalized_cols"].get(ref_col_norm)

                        if not ref_col or not local_col:
                            st.warning(f"⚠️ Kolom `{ref_col_norm}` tidak ditemukan di `{sheet}` atau tabel referensi. FK dilewati.")
                            continue

                        # Pastikan kolom bertipe VARCHAR(255)
                        try:
                            conn.execute(text(f"ALTER TABLE `{table_name}` MODIFY `{local_col}` VARCHAR(255);"))
                            conn.execute(text(f"ALTER TABLE `{ref_table}` MODIFY `{ref_col}` VARCHAR(255);"))
                        except Exception:
                            pass

                        fk_name = f"fk_{table_name}_{ref_col_norm}"
                        try:
                            conn.execute(text(f"""
                                ALTER TABLE `{table_name}`
                                ADD CONSTRAINT `{fk_name}`
                                FOREIGN KEY (`{local_col}`) REFERENCES `{ref_table}`(`{ref_col}`);
                            """))
                            st.success(f"🔗 FK `{local_col}`: `{table_name}` → `{ref_table}` berhasil dibuat")
                        except Exception as e:
                            st.warning(f"⚠️ Gagal membuat FK `{local_col}` di `{table_name}`: {e}")

        st.success("🎉 Semua tabel dan relasi berhasil diimpor!")
        
        # Reset session state setelah import berhasil
        st.toast("✅ Data berhasil disimpan ke database!", icon="🎉")

        for key in ['sheet_data_selected', 'combined_sheets', 'fk_selection', 'pk_selection']:
            if key in st.session_state:
                st.session_state[key] = {}