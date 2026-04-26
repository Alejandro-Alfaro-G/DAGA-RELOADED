import streamlit as st
import pandas as pd
import plotly.express as px

from utils.carga import (
    load_clientes, load_productos, load_transacciones,
    load_conversaciones, load_features_tx, load_features_conv,
    lista_users_demo,
)
from utils.insights import insights_usuario

st.set_page_config(page_title="Perfil 360°", page_icon="👤", layout="wide")
st.title("👤 Perfil 360°")

# ---------- Carga ----------
with st.spinner("Cargando datasets..."):
    cli = load_clientes()
    prod = load_productos()
    tx = load_transacciones()
    conv = load_conversaciones()
    ftx = load_features_tx()
    fconv = load_features_conv()
    feature = load_features_conv()

if cli.empty:
    st.error("No se encontró hey_clientes.csv en hey_demo/data/. Copia los archivos ahí.")
    st.stop()

# ---------- Selector ----------
demo_users = lista_users_demo(200)
col_sel, col_modo = st.columns([3, 1])
with col_modo:
    modo = st.radio("Modo", ["Demo (200)", "Manual"], horizontal=False,
                    label_visibility="collapsed")
with col_sel:
    if modo == "Demo (200)":
        default_idx = 0
        if "selected_user" in st.session_state and st.session_state["selected_user"] in demo_users:
            default_idx = demo_users.index(st.session_state["selected_user"])
        user_id = st.selectbox("Usuario", demo_users, index=default_idx)
    else:
        user_id = st.text_input("user_id manual",
                                value=st.session_state.get("selected_user",
                                                           demo_users[0] if demo_users else ""))

if not user_id:
    st.stop()

st.session_state["selected_user"] = user_id

# ---------- Filtrado ----------
cli_match = cli[cli["user_id"] == user_id]
if cli_match.empty:
    st.error(f"Usuario `{user_id}` no existe en hey_clientes.csv")
    st.stop()
cliente_row = cli_match.iloc[0]

prod_u = prod[prod["user_id"] == user_id].copy() if not prod.empty else pd.DataFrame()
tx_u = tx[tx["user_id"] == user_id].copy() if not tx.empty else pd.DataFrame()
conv_u = conv[conv["user_id"] == user_id].copy() if not conv.empty else pd.DataFrame()

ftx_u = None
if not ftx.empty and (ftx["user_id"] == user_id).any():
    ftx_u = ftx[ftx["user_id"] == user_id].iloc[0]

fconv_u = None
if not fconv.empty and (fconv["user_id"] == user_id).any():
    fconv_u = fconv[fconv["user_id"] == user_id].iloc[0]

# ---------- KPIs ----------
st.subheader(f"Cliente: `{user_id}`")
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Ingreso/mes", f"${cliente_row.get('ingreso_mensual_mxn', 0):,.0f}")
k2.metric("Score buró", int(cliente_row.get("score_buro", 0) or 0))
k3.metric("Antigüedad (d)", int(cliente_row.get("antiguedad_dias", 0) or 0))
k4.metric("Satisfacción", f"{cliente_row.get('satisfaccion_1_10', 0)}/10")
k5.metric("Hey Pro", "✅" if cliente_row.get("es_hey_pro") else "❌")
k6.metric("Productos", int(cliente_row.get("num_productos_activos", 0) or 0))

# ---------- Demografía + Insights ----------
left, right = st.columns([1, 1.2])

with left:
    st.markdown("#### Demografía")
    demo = {
        "Edad": cliente_row.get("edad"),
        "Sexo": cliente_row.get("sexo"),
        "Estado": cliente_row.get("estado"),
        "Ciudad": cliente_row.get("ciudad"),
        "Educación": cliente_row.get("nivel_educativo"),
        "Ocupación": cliente_row.get("ocupacion"),
        "Nómina domiciliada": "Sí" if cliente_row.get("nomina_domiciliada") else "No",
        "Recibe remesas": "Sí" if cliente_row.get("recibe_remesas") else "No",
        "Usa Hey Shop": "Sí" if cliente_row.get("usa_hey_shop") else "No",
        "Días último login": cliente_row.get("dias_desde_ultimo_login"),
    }
    st.dataframe(
        pd.DataFrame(list(demo.items()), columns=["Campo", "Valor"]),
        hide_index=True, use_container_width=True,
    )

with right:
    st.markdown("#### 💡 Insights accionables")
    ins = insights_usuario(user_id, cliente_row, prod_u, tx_u, ftx_u, conv_u)
    if not ins:
        st.info("Sin insights gatillados por las reglas actuales.")
    else:
        sev_color = {"alta": "🔴", "media": "🟡", "baja": "🟢"}
        for i in ins:
            with st.container(border=True):
                st.markdown(f"{sev_color.get(i['severidad'], '⚪')} **{i['tipo']}**")
                st.write(i["mensaje"])
                if i["impacto_mxn"]:
                    st.caption(f"Impacto estimado: **${i['impacto_mxn']:,.0f} MXN**")

# ---------- Gasto por MCC ----------
st.markdown("#### Gasto por categoría (MCC)")
if not tx_u.empty and "categoria_mcc" in tx_u.columns and "monto" in tx_u.columns:
    tx_ok = tx_u
    if "estatus" in tx_u.columns:
        tx_ok = tx_u[tx_u["estatus"].astype(str).str.lower() == "completada"]
    gasto_mcc = (
        tx_ok.groupby("categoria_mcc", as_index=False)["monto"]
        .sum().sort_values("monto", ascending=True)
    )
    if gasto_mcc.empty:
        st.info("Sin transacciones exitosas para este usuario.")
    else:
        fig = px.bar(gasto_mcc, x="monto", y="categoria_mcc", orientation="h",
                     text="monto", color_discrete_sequence=["#E30613"])
        fig.update_traces(texttemplate="$%{x:,.0f}", textposition="outside")
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis_title="MXN", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sin transacciones para este usuario.")

# ---------- Productos + Timeline ----------
c_prod, c_time = st.columns([1, 1])

with c_prod:
    st.markdown("#### Productos contratados")
    if prod_u.empty:
        st.info("Sin productos.")
    else:
        cols_show = [c for c in ["tipo_producto", "estatus", "saldo_actual",
                                  "limite_credito", "utilizacion_pct",
                                  "tasa_interes_anual", "monto_mensualidad"]
                     if c in prod_u.columns]
        st.dataframe(prod_u[cols_show], hide_index=True, use_container_width=True)

with c_time:
    st.markdown("#### Transacciones por mes")
    if tx_u.empty or "fecha_hora" not in tx_u.columns:
        st.info("Sin timeline.")
    else:
        tmp = tx_u.dropna(subset=["fecha_hora"]).copy()
        tmp["mes"] = tmp["fecha_hora"].dt.to_period("M").astype(str)
        agg = tmp.groupby("mes").agg(n=("monto", "size"),
                                     monto=("monto", "sum")).reset_index()
        fig = px.bar(agg, x="mes", y="monto", color_discrete_sequence=["#E30613"])
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                          yaxis_title="MXN gastados", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

# ---------- Conversaciones ----------
st.markdown("#### Conversaciones del usuario con Havi")
if conv_u.empty:
    st.info("Este usuario no tiene conversaciones registradas.")
else:
    st.caption(f"{conv_u['conv_id'].nunique()} conversaciones · {len(conv_u)} interacciones")

    if fconv_u is not None:
        # 1. Mostrar Perfil Dominante
        if "perfil_dominante" in fconv_u.index and pd.notna(fconv_u["perfil_dominante"]):
            st.success(f"Perfil conversacional dominante: **{fconv_u['perfil_dominante']}**")

        # 2. NUEVO: Gráfico de distribución de intenciones
        # Extraemos todas las columnas que empiezan con 'pct_'
        pct_cols = [col for col in fconv_u.index if str(col).startswith('pct_')]
        
        if pct_cols:
            # Construimos un dataframe limpio para Plotly
            df_topics = pd.DataFrame({
                "Tema": [col.replace('pct_', '').replace('_', ' ').capitalize() for col in pct_cols],
                "Porcentaje": [float(fconv_u[col]) for col in pct_cols] # Forzamos a float por seguridad
            })
            
            # Filtramos solo los temas de los que el usuario habló (> 0%)
            df_topics = df_topics[df_topics["Porcentaje"] > 0].sort_values("Porcentaje", ascending=True)

            if not df_topics.empty:
                fig_topics = px.bar(
                    df_topics, 
                    x="Porcentaje", 
                    y="Tema", 
                    orientation="h",
                    color_discrete_sequence=["#E30613"] # Rojo Hey Banco
                )
                
                # Formato visual
                fig_topics.update_traces(texttemplate="%{x:.0%}", textposition="outside")
                fig_topics.update_layout(
                    height=max(200, len(df_topics) * 45), # Ajuste automático de altura según la cantidad de barras
                    margin=dict(l=10, r=40, t=10, b=10),  # Margen derecho extra para que no se corte el porcentaje
                    xaxis_tickformat=".0%",
                    xaxis_title="",
                    yaxis_title=""
                )
                
                st.plotly_chart(fig_topics, use_container_width=True)

    # 3. Historial de chats (Tu código original)
    convs_ord = (
        conv_u.sort_values("date")
        .groupby("conv_id")
        .agg(n=("input", "size"), inicio=("date", "min"))
        .sort_values("inicio", ascending=False)
        .reset_index()
    )
    for _, row in convs_ord.head(10).iterrows():
        with st.expander(f"💬 {row['conv_id']} · {row['n']} turnos · {row['inicio']}"):
            turnos = conv_u[conv_u["conv_id"] == row["conv_id"]].sort_values("date")
            for _, t in turnos.iterrows():
                inp = t.get("input") if pd.notna(t.get("input")) else ""
                outp = t.get("output") if pd.notna(t.get("output")) else ""
                st.markdown(f"**Usuario:** {inp}")
                st.markdown(f"**Havi:** {outp}")
                st.divider()
