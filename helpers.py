import re
import pandas as pd

def normalize_col(col: str) -> str:
    """Ubah nama kolom jadi bentuk seragam untuk perbandingan FK"""
    return re.sub(r'[^a-z0-9]', '', col.lower())

def safe_convert_for_key(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Konversi kolom ke string agar bisa jadi PK/FK"""
    if not pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_datetime64_any_dtype(df[col]):
        df[col] = df[col].astype(str)
    return df

def clean_table_name(name: str) -> str:
    """Membersihkan nama tabel untuk database"""
    return re.sub(r'[^a-z0-9_]', '_', name.lower())

