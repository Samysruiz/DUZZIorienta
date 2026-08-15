"""
login_page.py — Tela de login para Admin e Super Admin
"""

import streamlit as st
from database import login


def render_login():
    """
    Renderiza a tela de login.
    Retorna True se logado, False se não.
    Guarda em st.session_state: logged_in, user_role, username
    """
    if st.session_state.get("logged_in"):
        return True

    st.markdown("""
    <div style="max-width:420px;margin:3rem auto">
        <div style="text-align:center;margin-bottom:2rem">
            <div style="font-size:3rem">🔐</div>
            <h2 style="color:#ffd6ec;margin:.3rem 0">Área Restrita</h2>
            <p style="color:#c0a0b8">Duzzi Orienta — Painel de Gestão</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Usuário", placeholder="admin ou superadmin")
        password = st.text_input("Senha", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar →", use_container_width=True)

    if submitted:
        user = login(username, password)
        if user:
            st.session_state.logged_in  = True
            st.session_state.user_role  = user["role"]
            st.session_state.username   = user["username"]
            st.session_state.user_id    = user.get("id", 0)
            st.success(f"Bem-vindo, {user['username']}! ({user['role']})")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

    st.markdown("""
    <p style="text-align:center;color:#7f5a67;font-size:.82rem;margin-top:1rem">
    Admin: usuário <b>admin</b> · SuperAdmin: usuário <b>superadmin</b>
    </p>
    """, unsafe_allow_html=True)

    return False


def logout():
    for key in ["logged_in","user_role","username","user_id"]:
        st.session_state.pop(key, None)
    st.rerun()


def require_role(required: str) -> bool:
    """Verifica se usuário tem permissão. required: 'admin' ou 'superadmin'"""
    role = st.session_state.get("user_role","")
    if required == "admin":
        return role in ("admin","superadmin")
    return role == "superadmin"
