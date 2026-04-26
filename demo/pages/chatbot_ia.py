"""
pages/4_Chat_Bot.py  ·  Hey Banco — Chatbot IA con Pipeline Proactivo
─────────────────────────────────────────────────────────────────────
Coloca este archivo en:   hey_demo/pages/4_Chat_Bot.py
El backend (pipeline) se inicializa una sola vez con st.cache_resource.

Requisitos adicionales:
    pip install sentence-transformers
    ollama serve   (en terminal separada)
"""

import re
import time
import requests
import numpy as np
import pandas as pd
import streamlit as st
import torch

from utils.config import apply_sidebar_dark_theme
from utils.carga import load_features_conv, lista_users_demo

# ── Tema ───────────────────────────────────────────────────────────────
apply_sidebar_dark_theme()

st.set_page_config(
    page_title="Chat Bot · Hey Banco",
    page_icon="🤖",
    layout="wide",
)

# ══════════════════════════════════════════════════════════════════════
# CSS personalizado — paleta Hey Banco
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* Burbujas de chat -------------------------------------------------- */
.burbuja-user {
    background: #fcec02;
    color: #221f1f;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 16px;
    margin: 6px 0 6px 15%;
    font-size: 0.95rem;
    font-weight: 500;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.burbuja-bot {
    background: #2d2a2a;
    color: #f5f5f5;
    border-radius: 18px 18px 18px 4px;
    padding: 12px 16px;
    margin: 6px 15% 6px 0;
    font-size: 0.95rem;
    line-height: 1.6;
    border-left: 3px solid #40e0f1;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.burbuja-bot strong { color: #fcec02; }

/* Chips de perfiles detectados -------------------------------------- */
.chip {
    display: inline-block;
    background: #1a1818;
    color: #40e0f1;
    border: 1px solid #40e0f1;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.78rem;
    margin: 2px 3px;
}

/* Panel de contexto IA ---------------------------------------------- */
.ctx-panel {
    background: #1a1818;
    border: 1px solid #333;
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 0.82rem;
    color: #aaa;
}
.ctx-panel b { color: #fcec02; }

/* Header del chat ---------------------------------------------------- */
.chat-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
}
.avatar-bot {
    width: 38px; height: 38px;
    background: #fcec02;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
    flex-shrink: 0;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# Backend: inicialización cacheada (solo corre una vez por sesión)
# ══════════════════════════════════════════════════════════════════════
OLLAMA_URL       = "http://localhost:11434/api/generate"
OLLAMA_MODEL     = "qwen2.5:14b"
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K_PERFILES   = 2
SIM_THRESHOLD    = 0.25

EMBEDDINGS_PATH  = "demo/data/embeddings_conv.npy"
CONV_FULL_PATH   = "demo/data/conv_full_perfiles_finales.parquet"

SYSTEM_PROMPT = """Eres Havi, el asistente virtual de Hey Banco. Tu objetivo es ayudar proactivamente al usuario.

Se te dará:
- El mensaje del usuario
- Los temas más probables relacionados con su consulta
- Su historial de interacciones previas con el banco

Tu tarea:
1. Identifica los 2 o 3 problemas más probables que el usuario podría estar enfrentando
2. Para cada problema, proporciona pasos concretos de solución (mínimo 3-4 pasos por problema)
3. Sé directo, empático y claro
4. NO menciones embeddings, clusters, perfiles ni datos técnicos internos
5. Habla siempre en español, tono profesional pero cercano y cálido
6. Si el usuario ya tiene historial con ese tema, menciónalo sutilmente
7. Termina siempre preguntando si hay algo más en lo que puedas ayudar
"""


@st.cache_resource(show_spinner="Inicializando pipeline IA…")
def inicializar_pipeline():
    """Carga embeddings, calcula centroides y carga el modelo. Solo corre 1 vez."""
    from sentence_transformers import SentenceTransformer

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Cargar embeddings y metadata
    try:
        embeddings = np.load(EMBEDDINGS_PATH)
        conv_full  = pd.read_parquet(CONV_FULL_PATH).reset_index(drop=True)
    except FileNotFoundError as e:
        st.error(f"Archivo no encontrado: {e}. Verifica las rutas en chatbot_ia.py")
        st.stop()

    assert len(embeddings) == len(conv_full), \
        "Mismatch entre embeddings y conv_full"

    conv_full["_emb_idx"] = conv_full.index

    # Calcular centroides por perfil
    centroides = {}
    for perfil, grupo in conv_full.groupby("perfil_final"):
        if perfil in ("Sin clasificar", "Otros", "sin clasificar"):
            continue
        idxs = grupo["_emb_idx"].values
        vecs = embeddings[idxs]
        c = vecs.mean(axis=0)
        c = c / (np.linalg.norm(c) + 1e-10)
        centroides[perfil] = c

    perfil_labels   = list(centroides.keys())
    centroid_matrix = np.stack([centroides[p] for p in perfil_labels])

    # Cargar modelo de embeddings
    embed_model = SentenceTransformer(EMBED_MODEL_NAME, device=device)

    return embed_model, centroid_matrix, perfil_labels


def limpiar_texto(t: str) -> str:
    t = str(t).lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"http\S+", "", t)
    return t.strip()


def clasificar_prompt(prompt: str, embed_model, centroid_matrix, perfil_labels,
                      top_k=TOP_K_PERFILES, threshold=SIM_THRESHOLD):
    vec = embed_model.encode(
        [limpiar_texto(prompt)],
        normalize_embeddings=True,
        convert_to_numpy=True
    )[0]
    sims = centroid_matrix @ vec
    top_idx = np.argsort(sims)[::-1][:top_k]
    return [
        (perfil_labels[i], float(sims[i]))
        for i in top_idx
        if float(sims[i]) >= threshold
    ]


def buscar_usuario(user_id: str, features: pd.DataFrame) -> dict | None:
    fila = features[features["user_id"].astype(str) == str(user_id)]
    if fila.empty:
        return None
    row = fila.iloc[0]
    pct_cols = [c for c in features.columns if c.startswith("pct_")]
    top_p = (
        row[pct_cols].sort_values(ascending=False).head(3)
        if pct_cols else pd.Series(dtype=float)
    )
    top_p_dict = {
        c.replace("pct_", "").replace("_", " "): round(float(v), 3)
        for c, v in top_p.items()
    }
    return {
        "user_id":           str(user_id),
        "perfil_dominante":  row.get("perfil_dominante", "desconocido"),
        "n_conversaciones":  int(row.get("n_conversaciones", 0)),
        "top_perfiles_pct":  top_p_dict,
    }


def construir_prompt_llm(prompt_usuario, perfiles, datos_usuario) -> str:
    temas_str = "\n".join(
        f"  - {p} (relevancia: {s:.2f})" for p, s in perfiles
    ) if perfiles else "  - Consulta general (sin tema específico detectado)"

    if datos_usuario:
        hist_str = (
            f"  - Perfil dominante: {datos_usuario['perfil_dominante']}\n"
            f"  - Conversaciones previas: {datos_usuario['n_conversaciones']}\n"
            f"  - Temas frecuentes: "
            + ", ".join(f"{k} ({v:.0%})" for k, v in datos_usuario["top_perfiles_pct"].items())
        )
    else:
        hist_str = "  - Usuario nuevo o no encontrado en el sistema"

    return f"""=== MENSAJE DEL USUARIO ===
{prompt_usuario}

=== TEMAS PROBABLES ===
{temas_str}

=== HISTORIAL DEL USUARIO ===
{hist_str}

=== INSTRUCCIÓN ===
Propón de forma proactiva los 2-3 problemas más probables y ofrece soluciones concretas.
Responde directamente al usuario como Havi."""


def llamar_ollama(prompt_llm: str) -> str:
    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt_llm,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": 0.6,
            "top_p":       0.9,
            "num_predict": 2048,
            "num_ctx":     4096,
        }
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json().get("response", "[sin respuesta]").strip()
    except requests.exceptions.ConnectionError:
        return "⚠️ No se pudo conectar con Ollama. Verifica que esté corriendo con `ollama serve`."
    except requests.exceptions.Timeout:
        return "⚠️ El modelo tardó demasiado en responder. Intenta de nuevo o revisa los recursos disponibles."
    except Exception as e:
        return f"⚠️ Error inesperado: {str(e)}"


def correr_pipeline(prompt_usuario: str, user_id: str,
                    embed_model, centroid_matrix, perfil_labels,
                    features: pd.DataFrame) -> tuple[str, list, dict | None]:
    """Devuelve (respuesta, perfiles_detectados, datos_usuario)."""
    perfiles      = clasificar_prompt(prompt_usuario, embed_model, centroid_matrix, perfil_labels)
    datos_usuario = buscar_usuario(user_id, features)
    prompt_llm    = construir_prompt_llm(prompt_usuario, perfiles, datos_usuario)
    respuesta     = llamar_ollama(prompt_llm)
    return respuesta, perfiles, datos_usuario


# ══════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════

# ── Sidebar: selector de usuario ──────────────────────────────────────
with st.sidebar:
    st.markdown("### 👤 Usuario activo")
    users = lista_users_demo(n=300)

    if users:
        user_id_sel = st.selectbox(
            "Selecciona un user_id",
            options=users,
            index=0,
        )
    else:
        user_id_sel = st.text_input("Ingresa tu user_id", value="")

    st.divider()
    st.caption("El user_id se adjunta automáticamente a cada mensaje.")
    st.markdown(f"**Modelo:** `{OLLAMA_MODEL}`")
    st.markdown(f"**Threshold similitud:** `{SIM_THRESHOLD}`")

    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.mensajes = []
        st.rerun()

# ── Inicializar pipeline (cacheado) ───────────────────────────────────
embed_model, centroid_matrix, perfil_labels = inicializar_pipeline()
features = load_features_conv()

# ── Estado de la conversación ─────────────────────────────────────────
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# ── Layout principal ──────────────────────────────────────────────────
col_chat, col_ctx = st.columns([3, 1], gap="large")

with col_chat:
    st.markdown("""
    <div class="chat-header">
        <div class="avatar-bot">🤖</div>
        <div>
            <strong style="font-size:1.1rem">Havi</strong><br>
            <span style="color:#40e0f1;font-size:0.8rem">Asistente Hey Banco · IA Proactiva</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Mensaje de bienvenida si no hay historial
    if not st.session_state.mensajes:
        st.markdown("""
        <div class="burbuja-bot">
            ¡Hola! Soy <strong>Havi</strong>, tu asistente de Hey Banco 👋<br><br>
            Puedo ayudarte con pagos, transferencias, productos, estado de cuenta y más.
            ¿En qué puedo ayudarte hoy?
        </div>
        """, unsafe_allow_html=True)

    # Historial de mensajes
    for msg in st.session_state.mensajes:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="burbuja-user">{msg["content"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="burbuja-bot">{msg["content"]}</div>',
                unsafe_allow_html=True
            )

    # Input del usuario
    with st.form("chat_form", clear_on_submit=True):
        col_inp, col_btn = st.columns([5, 1])
        with col_inp:
            user_input = st.text_input(
                "Escribe tu mensaje…",
                label_visibility="collapsed",
                placeholder="Ej: No puedo hacer pagos con mi tarjeta",
            )
        with col_btn:
            enviado = st.form_submit_button("Enviar", use_container_width=True, type="primary")

    # Procesar mensaje
    if enviado and user_input.strip():
        prompt_limpio = user_input.strip()

        # Agregar mensaje del usuario
        st.session_state.mensajes.append({"role": "user", "content": prompt_limpio})

        # Llamar al pipeline con spinner
        with st.spinner("Havi está analizando tu consulta…"):
            t0 = time.time()
            respuesta, perfiles_det, datos_usr = correr_pipeline(
                prompt_usuario   = prompt_limpio,
                user_id          = str(user_id_sel),
                embed_model      = embed_model,
                centroid_matrix  = centroid_matrix,
                perfil_labels    = perfil_labels,
                features         = features,
            )
            elapsed = time.time() - t0

        # Guardar respuesta y metadata
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
        st.session_state["ultima_meta"] = {
            "perfiles":     perfiles_det,
            "datos_usr":    datos_usr,
            "elapsed":      elapsed,
            "user_id":      str(user_id_sel),
        }

        st.rerun()

# ── Panel de contexto IA (columna derecha) ────────────────────────────
with col_ctx:
    st.markdown("#### 🧠 Contexto IA")

    meta = st.session_state.get("ultima_meta")

    if not meta:
        st.markdown("""
        <div class="ctx-panel">
            El análisis de contexto aparecerá aquí después de tu primer mensaje.
        </div>
        """, unsafe_allow_html=True)
    else:
        # User ID
        st.markdown(f"""
        <div class="ctx-panel">
            <b>User ID</b><br>
            <code style="color:#63ff76">{meta['user_id']}</code>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Perfiles detectados
        st.markdown("**Temas detectados**")
        if meta["perfiles"]:
            chips = "".join(
                f'<span class="chip">🏷 {p} <span style="color:#fcec02">{s:.2f}</span></span>'
                for p, s in meta["perfiles"]
            )
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown(
                '<span class="chip" style="color:#aaa;border-color:#555">Sin tema específico</span>',
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Perfil del usuario
        st.markdown("**Perfil del usuario**")
        d = meta["datos_usr"]
        if d:
            st.markdown(f"""
            <div class="ctx-panel">
                <b>Dominante:</b> {d['perfil_dominante']}<br>
                <b>Conversaciones previas:</b> {d['n_conversaciones']}<br>
                <b>Temas frecuentes:</b><br>
                {"<br>".join(f"· {k}: {v:.0%}" for k,v in d['top_perfiles_pct'].items())}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="ctx-panel">Usuario nuevo / no encontrado</div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption(f"⏱ Respuesta en {meta['elapsed']:.1f}s")
