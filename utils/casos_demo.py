"""Escanea la base y elige 4 user_ids óptimos, uno por caso demo.
Cacheado: la primera vez tarda ~10s, luego es instantáneo.
"""
import pandas as pd
import numpy as np
import streamlit as st

from utils.carga import (
    load_clientes, load_productos, load_transacciones,
)


def _safe_bool(x):
    if isinstance(x, bool):
        return x
    if pd.isna(x):
        return False
    return str(x).strip().lower() in {"true", "1", "si", "sí", "yes"}


def _seleccionar_caso_gasto(cli, tx):
    """Búsqueda en cascada: relaja criterios hasta encontrar algo."""
    if tx.empty or "categoria_mcc" not in tx.columns:
        return None

    tx_ok = tx
    if "estatus" in tx.columns:
        tx_ok = tx[tx["estatus"].astype(str).str.lower() == "exitosa"]
    if tx_ok.empty:
        return None

    g = tx_ok.groupby(["user_id", "categoria_mcc"])["monto"].sum().reset_index()
    total = tx_ok.groupby("user_id")["monto"].sum().rename("total")
    g = g.merge(total, on="user_id")
    g["pct"] = g["monto"] / g["total"]

    # Categorías "narrativas" para storyline
    cats_jugosas = ["delivery", "restaurante", "entretenimiento", "viajes",
                    "tecnologia", "ropa_accesorios", "servicios_digitales"]
    cats_aburridas = ["transferencia"]  # no narrativas

    # NIVEL 1: estricto - cat jugosa, >=40%, gasto >=5k
    cand = g[
        (g["categoria_mcc"].isin(cats_jugosas))
        & (g["pct"] >= 0.40)
        & (g["total"] >= 5000)
    ].sort_values("pct", ascending=False)
    if not cand.empty:
        for _, r in cand.iterrows():
            if r["user_id"] in cli["user_id"].values:
                return {
                    "user_id": r["user_id"],
                    "motivo": f"{r['pct']*100:.0f}% del gasto en {r['categoria_mcc']} (${r['monto']:,.0f})",
                    "metrica": r["monto"],
                }

    # NIVEL 2: bajar a 30% en cat jugosa
    cand = g[
        (g["categoria_mcc"].isin(cats_jugosas))
        & (g["pct"] >= 0.30)
        & (g["total"] >= 2000)
    ].sort_values("pct", ascending=False)
    if not cand.empty:
        for _, r in cand.iterrows():
            if r["user_id"] in cli["user_id"].values:
                return {
                    "user_id": r["user_id"],
                    "motivo": f"{r['pct']*100:.0f}% del gasto en {r['categoria_mcc']} (${r['monto']:,.0f})",
                    "metrica": r["monto"],
                }

    # NIVEL 3: cualquier categoría excepto transferencia, >=30%
    cand = g[
        (~g["categoria_mcc"].isin(cats_aburridas))
        & (g["pct"] >= 0.30)
        & (g["total"] >= 2000)
    ].sort_values("pct", ascending=False)
    if not cand.empty:
        for _, r in cand.iterrows():
            if r["user_id"] in cli["user_id"].values:
                return {
                    "user_id": r["user_id"],
                    "motivo": f"{r['pct']*100:.0f}% del gasto en {r['categoria_mcc']} (${r['monto']:,.0f})",
                    "metrica": r["monto"],
                }

    # NIVEL 4: cualquiera con concentración mayor (lo que sea)
    g_sorted = g.sort_values("pct", ascending=False)
    for _, r in g_sorted.iterrows():
        if r["user_id"] in cli["user_id"].values and r["total"] >= 1000:
            return {
                "user_id": r["user_id"],
                "motivo": f"{r['pct']*100:.0f}% del gasto en {r['categoria_mcc']} (${r['monto']:,.0f})",
                "metrica": r["monto"],
            }

    return None


@st.cache_data(show_spinner="Escaneando candidatos para casos demo...")
def seleccionar_casos_demo() -> dict:
    """Devuelve dict con keys: cross_sell, anomalia, gasto, churn.
    Cada valor es dict con: user_id, motivo, metrica.
    """
    cli = load_clientes()
    prod = load_productos()
    tx = load_transacciones()

    if cli.empty:
        return {}

    casos = {}

    # ---------- Caso 1: Cross-sell inversión ----------
    users_con_inv = set()
    if not prod.empty:
        users_con_inv = set(
            prod.loc[prod["tipo_producto"] == "inversion_hey", "user_id"].unique()
        )
    cand = cli[~cli["user_id"].isin(users_con_inv)].copy()
    cand = cand[cand["ingreso_mensual_mxn"] >= 30000]
    if cand.empty:
        cand = cli[~cli["user_id"].isin(users_con_inv)].sort_values(
            "ingreso_mensual_mxn", ascending=False
        )
    if not cand.empty:
        cand = cand.sort_values("ingreso_mensual_mxn", ascending=False)
        row = cand.iloc[0]
        casos["cross_sell"] = {
            "user_id": row["user_id"],
            "motivo": f"Ingreso ${row['ingreso_mensual_mxn']:,.0f}/mes sin producto de inversión",
            "metrica": row["ingreso_mensual_mxn"],
        }

    # ---------- Caso 2: Anomalía ----------
    cand = cli[cli["patron_uso_atipico"].apply(_safe_bool)].copy()
    if cand.empty and not tx.empty and "patron_uso_atipico" in tx.columns:
        users_atip = tx.loc[tx["patron_uso_atipico"].apply(_safe_bool), "user_id"].unique()
        cand = cli[cli["user_id"].isin(users_atip)]
    if not cand.empty:
        elegido = cand.iloc[0]
        if not tx.empty:
            tx_cand = tx[tx["user_id"].isin(cand["user_id"])]
            if not tx_cand.empty and "monto" in tx_cand.columns:
                tops = (
                    tx_cand.groupby("user_id")["monto"].max()
                    .sort_values(ascending=False).head(20).index
                )
                cand_top = cand[cand["user_id"].isin(tops)]
                if not cand_top.empty:
                    elegido = cand_top.iloc[0]
        casos["anomalia"] = {
            "user_id": elegido["user_id"],
            "motivo": "Patrón de uso atípico detectado · posible fraude",
            "metrica": None,
        }

    # ---------- Caso 3: Insight de gasto (cascada) ----------
    gasto = _seleccionar_caso_gasto(cli, tx)
    if gasto:
        casos["gasto"] = gasto

    # ---------- Caso 4: Churn ----------
    cand = cli[
        (cli["dias_desde_ultimo_login"] > 30)
        & (cli["satisfaccion_1_10"] <= 6)
        & (cli["ingreso_mensual_mxn"] >= 15000)
    ].copy()
    if cand.empty:
        cand = cli[
            (cli["dias_desde_ultimo_login"] > 14)
            & (cli["satisfaccion_1_10"] <= 7)
        ].copy()
    if not cand.empty:
        cand["score"] = cand["antiguedad_dias"] * cand["ingreso_mensual_mxn"]
        cand = cand.sort_values("score", ascending=False)
        row = cand.iloc[0]
        casos["churn"] = {
            "user_id": row["user_id"],
            "motivo": f"{row['dias_desde_ultimo_login']:.0f} días sin login · satisfacción {row['satisfaccion_1_10']}/10",
            "metrica": row["ingreso_mensual_mxn"],
        }

    return casos
    