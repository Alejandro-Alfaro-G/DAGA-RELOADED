"""Chat con bot dinámico · mockup mobile.
Backend: router por keywords + respuestas plantilla.
TODO: conectar a Anthropic/OpenAI en _generar_respuesta_llm().
"""
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from utils.carga import (
    load_clientes, load_productos, load_transacciones, load_conversaciones,
    lista_users_demo,
)

st.set_page_config(page_title="Chat Bot", page_icon="💬", layout="wide")

# ============================================================
# DEFINICIÓN DE BOTS (8 personalidades)
# ============================================================
BOTS = {
    "coach_gastos": {
        "nombre": "Coach de Gastos", "emoji": "📊", "color": "#1565C0",
        "saludo": "Hola, soy tu Coach de Gastos. ¿Qué te gustaría revisar hoy?",
    },
    "anti_friccion": {
        "nombre": "Asistente de Soporte", "emoji": "🛠️", "color": "#6A1B9A",
        "saludo": "Hola, estoy aquí para resolver cualquier problema con tus operaciones.",
    },
    "hey_pro": {
        "nombre": "Asesor Hey Pro", "emoji": "⭐", "color": "#F9A825",
        "saludo": "Te puedo mostrar todos los beneficios de Hey Pro y si te conviene.",
    },
    "inversion": {
        "nombre": "Asesor de Inversión", "emoji": "💰", "color": "#2E7D32",
        "saludo": "Hola, te ayudo a hacer crecer tu dinero con Inversión Hey.",
    },
    "anomalias": {
        "nombre": "Centro de Seguridad", "emoji": "🚨", "color": "#C62828",
        "saludo": "Estoy monitoreando tu cuenta. ¿Detectaste algún movimiento extraño?",
    },
    "cross_sell": {
        "nombre": "Asesor Hey", "emoji": "🎯", "color": "#00838F",
        "saludo": "Tengo recomendaciones de productos que se ajustan a tu perfil.",
    },
    "retencion": {
        "nombre": "Atención al Cliente", "emoji": "💝", "color": "#EF6C00",
        "saludo": "Hola, soy parte del equipo de atención. Cuéntame cómo te podemos ayudar.",
    },
    "onboarding": {
        "nombre": "Havi", "emoji": "🤖", "color": "#E30613",
        "saludo": "¡Hola! Soy Havi, tu asistente Hey. ¿En qué te ayudo?",
    },
}

# ============================================================
# ROUTER DE INTENT
# ============================================================
KEYWORDS = {
    "inversion": ["invertir", "inversión", "inversion", "cetes", "rendimiento", "ahorrar plazo"],
    "anomalias": ["fraude", "no reconozco", "cargo extraño", "robaron", "suplantación",
                  "movimiento raro", "cargo desconocido", "no fui yo"],
    "coach_gastos": ["gasto", "gasté", "presupuesto", "ahorrar", "categoría", "cuánto gasté",
                     "gasta", "gastando"],
    "anti_friccion": ["no me funciona", "error", "falló", "no procesó", "no pasó",
                      "rechazada", "problema con"],
    "hey_pro": ["hey pro", "premium", "upgrade", "cashback", "membresía"],
    "cross_sell": ["tarjeta", "crédito", "credito", "préstamo", "prestamo", "seguro",
                   "producto", "contratar"],
    "retencion": ["cancelar", "cerrar cuenta", "darme de baja", "irme", "ya no quiero"],
}


def detectar_bot(mensaje: str) -> str:
    msg = mensaje.lower()
    for bot_key, kws in KEYWORDS.items():
        if any(k in msg for k in kws):
            return bot_key
    return "onboarding"


# ============================================================
# CONTEXTO 360°
# ============================================================
def construir_contexto_360(user_id, cli, prod, tx, conv):
    if cli.empty:
        return {}
    cli_match = cli[cli["user_id"] == user_id]
    if cli_match.empty:
        return {}
    row = cli_match.iloc[0]

    prod_u = prod[prod["user_id"] == user_id] if not prod.empty else pd.DataFrame()
    tx_u = tx[tx["user_id"] == user_id] if not tx.empty else pd.DataFrame()
    conv_u = conv[conv["user_id"] == user_id] if not conv.empty else pd.DataFrame()

    gasto_top = ""
    if not tx_u.empty and "categoria_mcc" in tx_u.columns and "monto" in tx_u.columns:
        tx_ok = tx_u
        if "estatus" in tx_u.columns:
            tx_ok = tx_u[tx_u["estatus"].astype(str).str.lower() == "exitosa"]
        if not tx_ok.empty:
            gp = tx_ok.groupby("categoria_mcc")["monto"].sum().sort_values(ascending=False)
            if len(gp):
                gasto_top = f"{gp.index[0]} (${gp.iloc[0]:,.0f})"

    return {
        "user_id": user_id,
        "nombre": f"Cliente {user_id[-4:]}" if isinstance(user_id, str) else "Cliente",
        "edad": int(row.get("edad", 0) or 0),
        "ingreso_mensual": float(row.get("ingreso_mensual_mxn", 0) or 0),
        "es_hey_pro": bool(row.get("es_hey_pro", False)),
        "score_buro": int(row.get("score_buro", 0) or 0),
        "satisfaccion": int(row.get("satisfaccion_1_10", 0) or 0),
        "antiguedad_dias": int(row.get("antiguedad_dias", 0) or 0),
        "ciudad": row.get("ciudad", "—"),
        "num_productos": int(row.get("num_productos_activos", 0) or 0),
        "tipos_productos": list(prod_u["tipo_producto"].unique()) if not prod_u.empty else [],
        "n_tx": len(tx_u),
        "gasto_top_categoria": gasto_top,
        "n_conversaciones": conv_u["conv_id"].nunique() if not conv_u.empty else 0,
    }


# ============================================================
# GENERADOR DE RESPUESTAS (mock)
# ============================================================
def _generar_respuesta_llm(bot_key, mensaje, contexto):
    nombre = contexto.get("nombre", "")
    ingreso = contexto.get("ingreso_mensual", 0)
    es_pro = contexto.get("es_hey_pro", False)
    gasto_top = contexto.get("gasto_top_categoria", "")
    productos = contexto.get("tipos_productos", [])

    plantillas = {
        "inversion": (
            f"Con tu ingreso de ${ingreso:,.0f}/mes, te recomiendo arrancar con "
            f"<b>Inversión Hey</b> en CETES. Rendimiento ~10% anual, sin comisiones, "
            f"liquidez en 24h. ¿Quieres que prepare la apertura?"
        ),
        "anomalias": (
            "Detecté que tu última actividad fue normal, pero por seguridad voy a "
            "revisar los movimientos de las últimas 48h. Si identificas algo raro, "
            "podemos bloquear la tarjeta al instante. ¿Confirmas?"
        ),
        "coach_gastos": (
            f"Vi que tu mayor gasto fue en <b>{gasto_top or 'varias categorías'}</b>. "
            f"Si reduces 15% ahí, ahorrarías alrededor de ${ingreso*0.05:,.0f} al mes. "
            f"¿Te activo alertas de presupuesto?"
        ),
        "anti_friccion": (
            "Lamento el problema. Déjame revisar tu última transacción rechazada. "
            "Lo más común es límite diario o validación 3DS. Te confirmo en segundos."
        ),
        "hey_pro": (
            "Ya eres Hey Pro, aprovecha al máximo el cashback del 1%."
            if es_pro else
            f"Con tu nivel de gasto generarías cashback estimado de "
            f"${ingreso*0.30*12*0.01:,.0f} al año, mucho más que la cuota. "
            f"¿Te interesa ver el detalle?"
        ),
        "cross_sell": (
            f"Tienes {len(productos)} producto(s). Basado en tu perfil, te conviene "
            f"complementar con {'Inversión Hey' if 'inversion_hey' not in productos else 'Seguro de Compras'}. "
            f"¿Te paso los detalles?"
        ),
        "retencion": (
            f"Antes de irte, quiero entender qué pasó. Llevas {contexto.get('antiguedad_dias',0)} "
            f"días con nosotros. ¿Podemos ofrecerte 3 meses sin comisiones para que "
            f"reconsideres?"
        ),
        "onboarding": (
            f"¡Hola! Veo que tienes {contexto.get('num_productos',0)} producto(s) activo(s). "
            f"¿Quieres que revisemos tu cuenta, hagamos un plan de ahorro, o prefieres "
            f"explorar nuevos productos?"
        ),
    }
    return plantillas.get(bot_key, "Estoy procesando tu solicitud, dame un momento.")


# ============================================================
# CARGA Y SIDEBAR
# ============================================================
cli = load_clientes()
prod = load_productos()
tx = load_transacciones()
conv = load_conversaciones()

if cli.empty:
    st.error("Falta hey_clientes.csv en data/")
    st.stop()

with st.sidebar:
    st.markdown("### ⚙️ Contexto")

    demo_users = lista_users_demo(50)
    default_idx = 0
    if "selected_user" in st.session_state and st.session_state["selected_user"] in demo_users:
        default_idx = demo_users.index(st.session_state["selected_user"])
    user_id = st.selectbox("Usuario activo", demo_users, index=default_idx, key="chat_user")

    if st.button("🔄 Reiniciar conversación", use_container_width=True):
        st.session_state["chat_messages"] = []
        st.session_state["chat_bot_activo"] = "onboarding"
        st.session_state["chat_acciones"] = []
        st.rerun()

    contexto = construir_contexto_360(user_id, cli, prod, tx, conv)

    st.divider()
    st.markdown("### 🤖 Bot activo")
    bot_activo = st.session_state.get("chat_bot_activo", "onboarding")
    bot_def = BOTS[bot_activo]
    st.markdown(
        f"<div style='padding:10px; border-radius:8px; "
        f"background:{bot_def['color']}20; border-left:4px solid {bot_def['color']};'>"
        f"<b>{bot_def['emoji']} {bot_def['nombre']}</b></div>",
        unsafe_allow_html=True,
    )

    with st.expander("📥 Datos inyectados al prompt", expanded=False):
        if contexto:
            st.json(contexto, expanded=False)
        else:
            st.caption("Sin contexto.")

    with st.expander("⚡ Acciones disparadas", expanded=False):
        acciones = st.session_state.get("chat_acciones", [])
        if not acciones:
            st.caption("Aún sin acciones.")
        else:
            for a in acciones:
                st.markdown(f"- {a}")


# ============================================================
# ESTADO INICIAL
# ============================================================
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []
if "chat_bot_activo" not in st.session_state:
    st.session_state["chat_bot_activo"] = "onboarding"
if "chat_acciones" not in st.session_state:
    st.session_state["chat_acciones"] = []


# ============================================================
# BOT ACTIVO
# ============================================================
bot_def = BOTS[st.session_state["chat_bot_activo"]]


# ============================================================
# LAYOUT
# ============================================================
col_l, col_phone, col_r = st.columns([1, 1.3, 1])

with col_l:
    st.markdown("### 🎯 Demo")
    st.caption(
        "Bot dinámico con contexto 360°. El sistema detecta intent, "
        "carga datos del cliente y elige la personalidad adecuada."
    )
    st.markdown("**Cliente:**")
    st.code(user_id, language=None)
    if contexto:
        st.markdown(
            f"**Ingreso:** ${contexto['ingreso_mensual']:,.0f}  \n"
            f"**Hey Pro:** {'Sí' if contexto['es_hey_pro'] else 'No'}  \n"
            f"**Productos:** {contexto['num_productos']}  \n"
            f"**Top gasto:** {contexto['gasto_top_categoria'] or '—'}"
        )

with col_r:
    st.markdown("### 💡 Prueba con")
    sugerencias = [
        "¿Cómo voy de gastos este mes?",
        "Quiero invertir mi dinero",
        "No reconozco un cargo",
        "Me quiero dar de baja",
        "¿Qué es Hey Pro?",
        "Mi tarjeta no funciona",
    ]
    for txt in sugerencias:
        if st.button(txt, use_container_width=True, key=f"sug_{txt[:20]}"):
            st.session_state["chat_messages"].append({"role": "user", "content": txt})
            nuevo_bot = detectar_bot(txt)
            st.session_state["chat_bot_activo"] = nuevo_bot
            respuesta = _generar_respuesta_llm(nuevo_bot, txt, contexto)
            st.session_state["chat_messages"].append(
                {"role": "bot", "content": respuesta, "bot": nuevo_bot}
            )
            st.session_state["chat_acciones"].append(
                f"{BOTS[nuevo_bot]['emoji']} {BOTS[nuevo_bot]['nombre']} activado"
            )
            st.rerun()

# ============================================================
# PHONE MOCKUP (en col_phone)
# ============================================================
with col_phone:
    hora_actual = datetime.now().strftime("%H:%M")

    # Construir HTML de mensajes
    mensajes_html = (
        f'<div class="msg-row bot">'
        f'  <div>'
        f'    <div class="bot-tag">{bot_def["emoji"]} {bot_def["nombre"]}</div>'
        f'    <div class="bubble bot">{bot_def["saludo"]}</div>'
        f'  </div>'
        f'</div>'
    )
    for m in st.session_state["chat_messages"]:
        if m["role"] == "user":
            mensajes_html += (
                f'<div class="msg-row user">'
                f'  <div class="bubble user">{m["content"]}</div>'
                f'</div>'
            )
        else:
            b = BOTS.get(m.get("bot", "onboarding"), BOTS["onboarding"])
            mensajes_html += (
                f'<div class="msg-row bot">'
                f'  <div>'
                f'    <div class="bot-tag">{b["emoji"]} {b["nombre"]}</div>'
                f'    <div class="bubble bot">{m["content"]}</div>'
                f'  </div>'
                f'</div>'
            )
    # Anchor para auto-scroll
    mensajes_html += '<div id="chat-bottom"></div>'

    # HTML completo embebido en iframe (components.html)
    # — esto permite que el JS de auto-scroll se ejecute
    phone_html_full = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  body {{
    margin: 0;
    padding: 8px 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: transparent;
  }}
  .phone-frame {{
    max-width: 360px;
    margin: 0 auto;
    background: #FFFFFF;
    border-radius: 38px;
    box-shadow: 0 18px 40px rgba(0,0,0,0.18), 0 0 0 8px #1A1A1A, 0 0 0 10px #2A2A2A;
    overflow: hidden;
  }}
  .phone-status {{
    background: {bot_def['color']};
    color: white;
    padding: 10px 22px 6px;
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    font-weight: 600;
  }}
  .phone-notch {{
    background: #1A1A1A;
    width: 100px; height: 18px;
    margin: -2px auto 0;
    border-radius: 0 0 12px 12px;
    position: relative; z-index: 2;
  }}
  .phone-header {{
    background: {bot_def['color']};
    padding: 10px 18px 16px;
    color: white;
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .bot-avatar {{
    width: 38px; height: 38px;
    background: rgba(255,255,255,0.25);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 19px;
  }}
  .bot-info h3 {{ margin: 0; font-size: 15px; font-weight: 600; }}
  .bot-info p {{ margin: 1px 0 0 0; font-size: 11px; opacity: 0.85; }}
  .online-dot {{
    width: 7px; height: 7px;
    background: #4ADE80;
    border-radius: 50%;
    display: inline-block;
    margin-right: 4px;
  }}
  .phone-chat {{
    background: #F7F7F8;
    height: 400px;
    overflow-y: auto;
    padding: 14px 12px;
    scroll-behavior: smooth;
  }}
  .phone-chat::-webkit-scrollbar {{ width: 4px; }}
  .phone-chat::-webkit-scrollbar-thumb {{ background: #CCC; border-radius: 4px; }}

  .msg-row {{ display: flex; margin-bottom: 8px; }}
  .msg-row.user {{ justify-content: flex-end; }}
  .msg-row.bot {{ justify-content: flex-start; }}

  .bubble {{
    max-width: 78%;
    padding: 9px 13px;
    border-radius: 16px;
    font-size: 13.5px;
    line-height: 1.4;
    word-wrap: break-word;
  }}
  .bubble.user {{
    background: #E30613;
    color: white;
    border-bottom-right-radius: 4px;
  }}
  .bubble.bot {{
    background: white;
    color: #1A1A1A;
    border-bottom-left-radius: 4px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  }}
  .bot-tag {{
    font-size: 10px;
    font-weight: 600;
    opacity: 0.55;
    margin-bottom: 2px;
    padding: 0 4px;
  }}
</style>
</head>
<body>
<div class="phone-frame">
  <div class="phone-status">
    <span>{hora_actual}</span>
    <span>● ● ● 100%</span>
  </div>
  <div class="phone-notch"></div>
  <div class="phone-header">
    <div class="bot-avatar">{bot_def['emoji']}</div>
    <div class="bot-info">
      <h3>{bot_def['nombre']}</h3>
      <p><span class="online-dot"></span>en línea · Hey Banco</p>
    </div>
  </div>
  <div class="phone-chat" id="phone-chat">
    {mensajes_html}
  </div>
</div>
<script>
  // Auto-scroll al último mensaje
  const chat = document.getElementById('phone-chat');
  if (chat) {{ chat.scrollTop = chat.scrollHeight; }}
</script>
</body>
</html>
"""
    # Altura total del iframe: status(28) + notch(16) + header(72) + chat(380) + padding(40) ≈ 540
    components.html(phone_html_full, height=560, scrolling=False)

    # Input debajo del teléfono
    with st.form("chat_form", clear_on_submit=True):
        c_input, c_btn = st.columns([5, 1])
        with c_input:
            user_msg = st.text_input("msg", placeholder="Escribe un mensaje...",
                                     label_visibility="collapsed")
        with c_btn:
            enviar = st.form_submit_button("➤", use_container_width=True)

    if enviar and user_msg.strip():
        st.session_state["chat_messages"].append({"role": "user", "content": user_msg})
        nuevo_bot = detectar_bot(user_msg)
        st.session_state["chat_bot_activo"] = nuevo_bot
        respuesta = _generar_respuesta_llm(nuevo_bot, user_msg, contexto)
        st.session_state["chat_messages"].append(
            {"role": "bot", "content": respuesta, "bot": nuevo_bot}
        )
        st.session_state["chat_acciones"].append(
            f"{BOTS[nuevo_bot]['emoji']} {BOTS[nuevo_bot]['nombre']} activado"
        )
        st.rerun()
