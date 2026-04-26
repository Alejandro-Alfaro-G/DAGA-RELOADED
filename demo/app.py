import streamlit as st

from utils.carga import (
    load_clientes, load_transacciones, load_conversaciones, load_productos,
)
from utils.config import apply_sidebar_dark_theme

# Aplicar tema oscuro a la barra lateral
apply_sidebar_dark_theme()

st.set_page_config(
    page_title="Hey Banco · Motor de Inteligencia",
    page_icon="🟥",
    layout="wide",
)

st.title("🟥 Hey Banco · Motor de Inteligencia & Atención Personalizada")

st.markdown(
    """
Pipeline híbrido (transaccional + conversacional) para segmentación, 
insights accionables y bots dinámicos.

**Navega por las páginas en el sidebar →**

- **Perfil 360°** — vista completa de un usuario.
- **Segmentos** — mapa UMAP de clusters conversacionales.
- **Acciones** — tablero agregado de oportunidades.
- **Chat Bot** — orquestador de personalidades con contexto 360°.
- **Casos Demo** — historias preseleccionadas con impacto en pesos.
"""
)

st.divider()

# KPIs reales (cacheados)
cli = load_clientes()
tx = load_transacciones()
conv = load_conversaciones()
prod = load_productos()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Usuarios", f"{len(cli):,}" if not cli.empty else "—")
c2.metric("Transacciones", f"{len(tx):,}" if not tx.empty else "—")
c3.metric("Conversaciones", f"{conv['conv_id'].nunique():,}" if not conv.empty else "—")
c4.metric("Productos activos", f"{len(prod):,}" if not prod.empty else "—")

st.caption("Hackathon Hey Banco · Pipeline IA híbrida · 24h")
