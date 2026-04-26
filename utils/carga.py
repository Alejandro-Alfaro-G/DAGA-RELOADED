"""Carga cacheada de datasets. Todos los archivos viven en hey_demo/data/."""
from pathlib import Path
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _read_csv_safe(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _read_parquet_safe(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def load_clientes() -> pd.DataFrame:
    return _read_csv_safe("dataset_transacciones/hey_clientes.csv")


@st.cache_data(show_spinner=False)
def load_productos() -> pd.DataFrame:
    df = _read_csv_safe("dataset_transacciones/hey_productos.csv")
    if not df.empty and "fecha_apertura" in df.columns:
        df["fecha_apertura"] = pd.to_datetime(df["fecha_apertura"], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_transacciones() -> pd.DataFrame:
    df = _read_csv_safe("dataset_transacciones/hey_transacciones.csv")
    if not df.empty and "fecha_hora" in df.columns:
        df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_conversaciones() -> pd.DataFrame:
    df = _read_parquet_safe("dataset_conversaciones/dataset_50k_anonymized.parquet")
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_features_tx() -> pd.DataFrame:
    return _read_parquet_safe("features_tx.parquet")


@st.cache_data(show_spinner=False)
def load_features_conv() -> pd.DataFrame:
    return _read_parquet_safe("features_conv.parquet")


@st.cache_data(show_spinner=False)
def load_emb_user() -> pd.DataFrame:
    return _read_parquet_safe("emb_user.parquet")


@st.cache_data(show_spinner=False)
def lista_users_demo(n: int = 200) -> list:
    """Subset de usuarios con tx + conv para selectbox rápido."""
    cli = load_clientes()
    if cli.empty:
        return []
    tx = load_transacciones()
    conv = load_conversaciones()
    users_tx = set(tx["user_id"].unique()) if not tx.empty else set()
    users_conv = set(conv["user_id"].unique()) if not conv.empty else set()
    inter = users_tx & users_conv
    if inter:
        cand = cli[cli["user_id"].isin(inter)]
    else:
        cand = cli
    if len(cand) > n:
        cand = cand.sample(n, random_state=42)
    return sorted(cand["user_id"].tolist())
