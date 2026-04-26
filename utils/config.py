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
    "onboarding": PALETTE["primary"],        # Amarillo
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
