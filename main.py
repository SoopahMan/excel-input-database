import pandas as pd
from sqlalchemy import create_engine
import os

def import_excel_to_db(excel_path, db_url, prefix="", mode="append"):
    """
    Import semua sheet dari file Excel ke database.
    prefix: string yang ditambahkan di depan nama tabel, contoh "case1_"
    mode: "append" untuk tambah data, "replace" untuk timpa tabel lama
    """
    engine = create_engine(db_url)
    xls = pd.ExcelFile(excel_path)

    for sheet_name in xls.sheet_names:
        print(f"📄 Memproses sheet: {sheet_name} ...")

        # Baca sheet
        df = pd.read_excel(xls, sheet_name=sheet_name)

        # Bersihkan nama kolom biar aman
        df.columns = [c.strip().replace(' ', '_').replace('-', '_') for c in df.columns]

        # Buat nama tabel: prefix + nama sheet (snake_case)
        table_name = f"{prefix}{sheet_name.lower().replace(' ', '_')}"

        # Simpan ke database
        try:
            df.to_sql(table_name, engine, if_exists=mode, index=False)
            print(f"✅ Sheet '{sheet_name}' disimpan ke tabel '{table_name}' ({mode})")
        except Exception as e:
            print(f"❌ Gagal menyimpan sheet '{sheet_name}': {e}")

    print("🎉 Semua sheet berhasil dimasukkan ke database!")
    
# ==== Cara Pakai ====
if __name__ == "__main__":
    # Path file Excel
    excel_file = r"D:\ITDevelopment\Visidata Project\Bank Sahabat Sampoerna\Code input database\excel\Case 1\Bank Wide Dashboard.xlsx"

    # Database connection string
    # SQLite contoh (otomatis buat file .db)
    # db_url = "sqlite:///output.db"

    # MySQL contoh:
    db_url = "mysql+pymysql://root:@localhost/bss"

    # PostgreSQL contoh:
    # db_url = "postgresql+psycopg2://username:password@localhost/nama_database"

    import_excel_to_db(excel_file, db_url, prefix="case1_", mode="append")

