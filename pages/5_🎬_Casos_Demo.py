import streamlit as st
import pandas as pd
import plotly.express as px

from utils.carga import (
    load_clientes, load_productos, load_transacciones, load_conversaciones,
)
from utils.casos_demo import seleccionar_casos_demo
from utils.insights import insights_usuario
from utils.config import CASE_COLORS, apply_sidebar_dark_theme

# Aplicar tema oscuro a la barra lateral
apply_sidebar_dark_theme()

st.set_page_config(page_title="Casos Demo", page_icon="🎬", layout="wide")
st.title("🎬 Casos Demo · Storyline")

st.markdown(
    "Cuatro usuarios reales seleccionados automáticamente del dataset. "
    "Cada uno representa una oportunidad accionable cuantificada en pesos."
)

# Carga
cli = load_clientes()
prod = load_productos()
tx = load_transacciones()
conv = load_conversaciones()

if cli.empty:
    st.error("Falta hey_clientes.csv en data/")
    st.stop()

casos = seleccionar_casos_demo()

if not casos:
    st.error("No se pudieron seleccionar casos. Verifica datos.")
    st.stop()

# Definición visual de los 4 casos
DEFS = {
    "cross_sell": {
        "icono": "💰",
        "titulo": "Cross-sell evidente",
        "subtitulo": "Cliente con ingreso alto sin producto de inversión",
        "color": CASE_COLORS["cross_sell"],
        "accion": "Ofrecer **Inversión Hey CETES** vía push notification + email personalizado",
        "bot": "Bot Inversión",
    },
    "anomalia": {
        "icono": "🚨",
        "titulo": "Alerta de cargo anómalo",
        "subtitulo": "Patrón de uso atípico detectado en tiempo real",
        "color": CASE_COLORS["anomalia"],
        "accion": "Disparar **alerta de seguridad** + bloqueo preventivo + verificación 2FA",
        "bot": "Bot Anomalías",
    },
    "gasto": {
        "icono": "📊",
        "titulo": "Insight de gasto sorprendente",
        "subtitulo": "Concentración fuerte en una sola categoría",
        "color": CASE_COLORS["gasto"],
        "accion": "Activar **Coach de Gastos** con plan de ahorro personalizado y alertas de presupuesto",
        "bot": "Coach de Gastos",
    },
    "churn": {
        "icono": "💔",
        "titulo": "Cliente en riesgo de churn",
        "subtitulo": "Inactividad + insatisfacción · cliente valioso",
        "color": CASE_COLORS["churn"],
        "accion": "Disparar **campaña de retención**: 3 meses sin comisiones + llamada proactiva del ejecutivo",
        "bot": "Bot Retención",
    },
}

# ---------- Botones de selección ----------
st.markdown("### Selecciona un caso")
cols = st.columns(4)
keys_ordenadas = ["cross_sell", "anomalia", "gasto", "churn"]

if "caso_seleccionado" not in st.session_state:
    st.session_state["caso_seleccionado"] = keys_ordenadas[0]

for i, k in enumerate(keys_ordenadas):
    if k not in casos:
        cols[i].button(f"{DEFS[k]['icono']} {DEFS[k]['titulo']}\n\n_no disponible_",
                       disabled=True, use_container_width=True, key=f"btn_{k}")
        continue
    label = f"{DEFS[k]['icono']} **Caso {i+1}**\n\n{DEFS[k]['titulo']}"
    if cols[i].button(label, use_container_width=True, key=f"btn_{k}"):
        st.session_state["caso_seleccionado"] = k

st.divider()

# ---------- Render del caso elegido ----------
caso_key = st.session_state["caso_seleccionado"]
if caso_key not in casos:
    caso_key = next(iter(casos.keys()))

caso = casos[caso_key]
defi = DEFS[caso_key]
user_id = caso["user_id"]

cli_match = cli[cli["user_id"] == user_id]
if cli_match.empty:
    st.error(f"Usuario {user_id} no encontrado.")
    st.stop()
row = cli_match.iloc[0]

prod_u = prod[prod["user_id"] == user_id] if not prod.empty else pd.DataFrame()
tx_u = tx[tx["user_id"] == user_id] if not tx.empty else pd.DataFrame()
conv_u = conv[conv["user_id"] == user_id] if not conv.empty else pd.DataFrame()

# Header del caso
st.markdown(
    f"""
    <div style="padding:20px; border-radius:10px; background:{defi['color']}15; 
                border-left:6px solid {defi['color']};">
        <h2 style="margin:0; color:{defi['color']};">{defi['icono']} {defi['titulo']}</h2>
        <p style="margin:5px 0 0 0; font-size:1.05em;">{defi['subtitulo']}</p>
        <p style="margin:8px 0 0 0; opacity:0.7;"><b>Usuario:</b> <code>{user_id}</code> · {caso['motivo']}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# ---------- Layout: perfil resumido + acción ----------
left, right = st.columns([1, 1])

with left:
    st.markdown("#### Perfil del cliente")
    k1, k2, k3 = st.columns(3)
    k1.metric("Ingreso", f"${row.get('ingreso_mensual_mxn', 0):,.0f}")
    k2.metric("Edad", int(row.get("edad", 0) or 0))
    k3.metric("Antigüedad", f"{int(row.get('antiguedad_dias', 0) or 0)} d")

    k4, k5, k6 = st.columns(3)
    k4.metric("Score buró", int(row.get("score_buro", 0) or 0))
    k5.metric("Satisfacción", f"{row.get('satisfaccion_1_10', 0)}/10")
    k6.metric("Hey Pro", "✅" if row.get("es_hey_pro") else "❌")

    st.caption(
        f"📍 {row.get('ciudad', '—')}, {row.get('estado', '—')} · "
        f"{row.get('ocupacion', '—')} · {row.get('nivel_educativo', '—')}"
    )

    # Mini gráfica de gasto si aplica
    if not tx_u.empty and "categoria_mcc" in tx_u.columns:
        tx_ok = tx_u
        if "estatus" in tx_u.columns:
            tx_ok = tx_u[tx_u["estatus"].astype(str).str.lower() == "exitosa"]
        if not tx_ok.empty:
            top = (tx_ok.groupby("categoria_mcc")["monto"].sum()
                   .sort_values(ascending=True).tail(6).reset_index())
            fig = px.bar(top, x="monto", y="categoria_mcc", orientation="h",
                         color_discrete_sequence=[defi["color"]])
            fig.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10),
                              xaxis_title="MXN", yaxis_title="")
            fig.update_traces(texttemplate="$%{x:,.0f}", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

with right:
    st.markdown("#### 🤖 Acción que dispara el sistema")
    st.markdown(
        f"""
        <div style="padding:15px; border-radius:8px; background:#F5F5F5;">
            <p style="margin:0;"><b>Bot activado:</b> {defi['bot']}</p>
            <p style="margin:8px 0 0 0;">{defi['accion']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    # Calcular impacto via insights.py
    ftx_u = None  # opcional
    ins = insights_usuario(user_id, row, prod_u, tx_u, ftx_u, conv_u)

    impacto_total = sum(i["impacto_mxn"] for i in ins if i.get("impacto_mxn"))

    st.markdown("#### 💵 Impacto cuantificado")
    if impacto_total > 0:
        st.metric("Valor estimado anual", f"${impacto_total:,.0f} MXN")
    else:
        # estimaciones por defecto si insights no aplica
        ingreso = float(row.get("ingreso_mensual_mxn") or 0)
        defaults = {
            "cross_sell": ingreso * 0.10 * 12 * 0.005,
            "anomalia": 5000,  # fraude evitado promedio
            "gasto": ingreso * 0.05 * 12,  # ahorro 5% redirigido
            "churn": ingreso * 3,  # 3 meses de relación recuperada
        }
        st.metric("Valor estimado anual", f"${defaults.get(caso_key, 0):,.0f} MXN")

    st.markdown("#### Insights detectados")
    if not ins:
        st.info("Las reglas de insights no gatillaron para este usuario, "
                "pero el caso aplica por contexto demográfico/transaccional.")
    else:
        sev_color = {"alta": "🔴", "media": "🟡", "baja": "🟢"}
        for i in ins:
            st.markdown(
                f"{sev_color.get(i['severidad'], '⚪')} **{i['tipo']}** — {i['mensaje']}"
            )

# ---------- CTA al perfil completo ----------
st.divider()
c1, c2 = st.columns([3, 1])
with c1:
    st.caption("Para ver el perfil 360° completo de este cliente, "
               "selecciónalo en la página **Perfil 360°** del sidebar.")
with c2:
    if st.button("📋 Copiar user_id", use_container_width=True):
        st.session_state["selected_user"] = user_id
        st.success(f"`{user_id}` listo para Perfil 360°")
