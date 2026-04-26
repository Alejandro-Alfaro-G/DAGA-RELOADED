"""Configuración centralizada de colores y paleta de la aplicación."""

# Paleta de colores principal
PALETTE = {
    "primary": "#fcec02",      # Amarillo
    "dark": "#221f1f",         # Negro/Gris oscuro
    "accent_1": "#fdc4d2",     # Rosa claro
    "accent_2": "#40e0f1",     # Cian
    "accent_3": "#63ff76",     # Verde lima
}

# Colores para bots (8 personalidades)
BOT_COLORS = {
    "coach_gastos": PALETTE["primary"],      # Amarillo
    "anti_friccion": PALETTE["accent_2"],    # Cian
    "hey_pro": PALETTE["accent_3"],          # Verde lima
    "inversion": PALETTE["accent_1"],        # Rosa claro
    "anomalias": PALETTE["dark"],            # Negro/Gris oscuro
    "cross_sell": PALETTE["accent_2"],       # Cian
    "retencion": PALETTE["accent_1"],        # Rosa claro
    "onboarding": PALETTE["accent_1"],       # Rosa claro (Chatbot Havi)
}

# Colores para casos demo
CASE_COLORS = {
    "cross_sell": PALETTE["accent_3"],       # Verde lima
    "anomalia": PALETTE["dark"],             # Negro/Gris oscuro
    "gasto": PALETTE["primary"],             # Amarillo
    "churn": PALETTE["accent_1"],            # Rosa claro
}

# Colores para gráficos
CHART_COLORS = {
    "transactions": PALETTE["primary"],      # Amarillo
    "conversations": PALETTE["accent_3"],    # Verde lima
}


def apply_sidebar_dark_theme():
    """Aplica tema oscuro con textos blancos a la barra lateral y ajusta el contraste de los botones."""
    import streamlit as st
    
    st.markdown(
        """
        <style>
        /* 1. Fondo y textos generales de la barra lateral */
        [data-testid="stSidebar"] {
            background-color: #221f1f;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stRadio > label {
            color: #FFFFFF !important;
        }
        
        /* 2. Inputs de texto y selectores */
        [data-testid="stSidebar"] .stSelectbox,
        [data-testid="stSidebar"] .stNumberInput,
        [data-testid="stSidebar"] .stTextInput {
            color: #221f1f;
        }

        /* 3. Botones PRIMARIOS (st.button("Texto", type="primary")) */
        /* Fondo amarillo, texto oscuro para máximo contraste */
        .stButton > button[kind="primary"] {
            background-color: #fcec02 !important;
            color: #221f1f !important; 
            border: 1px solid #fcec02 !important;
            font-weight: 700 !important;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #e3d402 !important; /* Un amarillo ligeramente más oscuro al pasar el mouse */
            border-color: #e3d402 !important;
            color: #000000 !important;
        }

        /* 4. Botones SECUNDARIOS (st.button("Texto", type="secondary") - el valor por defecto) */
        /* Fondo oscuro, texto blanco, borde cyan para mantener el esquema de colores */
        .stButton > button[kind="secondary"] {
            background-color: #221f1f !important;
            color: #FFFFFF !important;
            border: 1px solid #40e0f1 !important; /* accent_2 (Cian) */
            font-weight: 600 !important;
        }
        .stButton > button[kind="secondary"]:hover {
            border-color: #fcec02 !important; /* Cambia a amarillo al pasar el mouse */
            color: #fcec02 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )