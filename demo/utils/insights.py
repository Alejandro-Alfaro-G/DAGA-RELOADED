"""Reglas para insights accionables por usuario.
Ajusta HEY_PRO_FEE_ANUAL si tienes el dato real.
"""
import pandas as pd
import numpy as np

HEY_PRO_FEE_ANUAL = 1200  # MXN, placeholder
INGRESO_MIN_INVERSION = 25000


def _safe_float(x, default=0.0):
    try:
        v = float(x)
        return default if pd.isna(v) else v
    except (TypeError, ValueError):
        return default


def _safe_bool(x):
    if isinstance(x, bool):
        return x
    if pd.isna(x):
        return False
    s = str(x).strip().lower()
    return s in {"true", "1", "si", "sí", "yes", "y"}


def insights_usuario(user_id, cliente_row, productos_user, tx_user, features_tx_row, conv_user):
    """Devuelve lista de dicts: {tipo, mensaje, impacto_mxn, severidad}."""
    out = []
    ingreso = _safe_float(cliente_row.get("ingreso_mensual_mxn"), 0)

    # --- Hey Pro upgrade ---
    es_pro = _safe_bool(cliente_row.get("es_hey_pro"))
    gasto_anual = 0.0
    if not tx_user.empty and "monto" in tx_user.columns:
        tx_ok = tx_user
        if "estatus" in tx_user.columns:
            tx_ok = tx_user[tx_user["estatus"].astype(str).str.lower() == "exitosa"]
        if not tx_ok.empty and "fecha_hora" in tx_ok.columns:
            ult_fecha = tx_ok["fecha_hora"].max()
            ventana = tx_ok[tx_ok["fecha_hora"] >= ult_fecha - pd.Timedelta(days=90)]
            gasto_90 = ventana["monto"].sum()
            gasto_anual = gasto_90 * 4
        else:
            gasto_anual = tx_ok["monto"].sum()
    cashback = gasto_anual * 0.01
    if (not es_pro) and cashback > HEY_PRO_FEE_ANUAL:
        out.append({
            "tipo": "Hey Pro",
            "mensaje": f"Cashback estimado anual ${cashback:,.0f} > cuota ${HEY_PRO_FEE_ANUAL:,}. Conviene upgrade.",
            "impacto_mxn": cashback - HEY_PRO_FEE_ANUAL,
            "severidad": "alta",
        })

    # --- Cross-sell inversión ---
    tipos_prod = set(productos_user["tipo_producto"].unique()) if not productos_user.empty else set()
    if "inversion_hey" not in tipos_prod and ingreso >= INGRESO_MIN_INVERSION:
        out.append({
            "tipo": "Cross-sell inversión",
            "mensaje": f"Ingreso ${ingreso:,.0f}/mes sin inversion_hey. Oferta CETES vía Inversión Hey.",
            "impacto_mxn": ingreso * 0.10 * 12 * 0.005,
            "severidad": "media",
        })

    # --- Fricción silenciosa ---
    pct_fric = np.nan
    if features_tx_row is not None and "pct_no_procesada" in features_tx_row.index:
        pct_fric = _safe_float(features_tx_row.get("pct_no_procesada"), np.nan)
    if pd.notna(pct_fric) and pct_fric >= 0.10 and conv_user.empty:
        out.append({
            "tipo": "Fricción silenciosa",
            "mensaje": f"{pct_fric*100:.1f}% de tx no procesadas y 0 conversaciones. Riesgo de abandono.",
            "impacto_mxn": ingreso * 0.30,
            "severidad": "alta",
        })

    # --- Anomalía / patrón atípico ---
    if _safe_bool(cliente_row.get("patron_uso_atipico")):
        out.append({
            "tipo": "Anomalía",
            "mensaje": "Patrón de uso atípico detectado. Verificar identidad / posible fraude.",
            "impacto_mxn": 0,
            "severidad": "alta",
        })

    # --- Churn por inactividad + insatisfacción ---
    dias_login = _safe_float(cliente_row.get("dias_desde_ultimo_login"), 0)
    sat = _safe_float(cliente_row.get("satisfaccion_1_10"), 10)
    if dias_login > 30 and sat <= 6:
        out.append({
            "tipo": "Churn",
            "mensaje": f"Sin login {dias_login:.0f} días + satisfacción {sat:.0f}/10. Activar retención.",
            "impacto_mxn": ingreso * 0.30,
            "severidad": "alta",
        })

    return out
