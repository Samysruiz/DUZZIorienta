"""
test_mode.py — Modo Teste do Duzzi Orienta
Permite ao superadmin testar a experiência do aluno e do admin
sem contaminar dados reais. Invisível para alunos e admins comuns.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st

BASE_DIR      = Path(__file__).parent
TEST_DB_PATH  = BASE_DIR / ".test_leads.db"


# ── Banco de dados de teste (SQLite separado) ─────────────────────────────────

def _init_test_db():
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS test_leads (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            nome                TEXT DEFAULT '',
            telefone            TEXT DEFAULT '',
            email               TEXT DEFAULT '',
            escola_origem       TEXT DEFAULT '',
            cidade              TEXT DEFAULT '',
            curso_recomendado   TEXT DEFAULT '',
            score_top           INTEGER DEFAULT 0,
            compatibilidade_pct INTEGER DEFAULT 0,
            ranking_json        TEXT DEFAULT '[]',
            abriu_inscricao     INTEGER DEFAULT 0,
            status              TEXT DEFAULT 'Ativo',
            origem              TEXT DEFAULT 'test',
            criado_em           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            testado_por         TEXT DEFAULT 'superadmin',
            notas               TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


def save_test_lead(nome, telefone, email, escola_origem, cidade,
                   top_course, score_top, compat_pct, ranking_json,
                   notas="") -> int:
    _init_test_db()
    conn = sqlite3.connect(TEST_DB_PATH)
    cur = conn.execute(
        """INSERT INTO test_leads
           (nome,telefone,email,escola_origem,cidade,
            curso_recomendado,score_top,compatibilidade_pct,
            ranking_json,origem,testado_por,notas)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (nome, telefone, email, escola_origem, cidade,
         top_course, score_top, compat_pct, ranking_json,
         "test", st.session_state.get("username","superadmin"), notas),
    )
    lead_id = cur.lastrowid
    conn.commit()
    conn.close()
    return lead_id


def list_test_leads() -> list:
    _init_test_db()
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM test_leads ORDER BY criado_em DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_test_lead(lead_id: int):
    _init_test_db()
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.execute("DELETE FROM test_leads WHERE id=?", (lead_id,))
    conn.commit()
    conn.close()


def clear_all_test_leads():
    _init_test_db()
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.execute("DELETE FROM test_leads")
    conn.commit()
    conn.close()


# ── Controle do modo teste ────────────────────────────────────────────────────

def is_test_mode() -> bool:
    return st.session_state.get("test_mode", False)


def enter_test_mode(as_role: str = "student"):
    """Ativa o modo teste. as_role: 'student' ou 'admin'"""
    st.session_state["test_mode"]      = True
    st.session_state["test_role"]      = as_role
    st.session_state["test_started"]   = datetime.now().isoformat()
    # Limpa dados de sessão para simular experiência fresh
    st.session_state["answers"]         = {}
    st.session_state["ranking"]         = None
    st.session_state["lead_id"]         = None
    st.session_state["student_name"]    = ""
    st.session_state["phone"]           = ""
    st.session_state["email"]           = ""
    st.session_state["escola"]          = ""
    st.session_state["cidade"]          = ""
    st.session_state["lgpd_consented"]  = True  # pula consentimento no teste
    st.session_state["inscricao_pendente"]   = False
    st.session_state["inscricao_confirmada"] = False


def exit_test_mode():
    """Sai do modo teste e volta ao painel."""
    for k in ["test_mode","test_role","test_started"]:
        st.session_state.pop(k, None)
    # Restaura sessão limpa
    st.session_state["answers"]         = {}
    st.session_state["ranking"]         = None
    st.session_state["lead_id"]         = None
    st.session_state["student_name"]    = ""
    st.session_state["phone"]           = ""
    st.session_state["lgpd_consented"]  = None
    st.session_state["page"]            = "Painel"


# ── Banner flutuante do modo teste ────────────────────────────────────────────

def render_test_banner():
    """
    Mostra banner vermelho fixo no topo indicando que está em modo teste.
    Visível APENAS para o superadmin — invisível para alunos e admins comuns.
    """
    if not is_test_mode():
        return
    if st.session_state.get("user_role") != "superadmin":
        return

    role = st.session_state.get("test_role", "student")
    role_label = "👨‍🎓 Experiência do Aluno" if role == "student" else "🔐 Experiência do Admin"
    started = st.session_state.get("test_started","")[:16].replace("T"," ")

    st.markdown(
        f'<div style="position:sticky;top:0;z-index:999;background:rgba(180,30,30,0.95);'
        f'border:2px solid #ff4060;border-radius:12px;padding:.6rem 1.2rem;'
        f'margin-bottom:1rem;display:flex;justify-content:space-between;align-items:center">'
        f'<div>'
        f'<span style="color:#fff;font-weight:700;font-size:.95rem">🧪 MODO TESTE ATIVO</span>'
        f'&nbsp;&nbsp;<span style="color:#ffb0b0;font-size:.85rem">{role_label} &nbsp;·&nbsp; iniciado {started}</span>'
        f'</div>'
        f'<span style="color:#ffb0b0;font-size:.8rem">Dados salvos separadamente — não aparecem para alunos/admins</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    if st.button("⏹️ Sair do modo teste", key="btn_exit_test"):
        exit_test_mode()
        st.rerun()


# ── Painel de resultados dos testes ──────────────────────────────────────────

def render_test_panel():
    """Painel completo de testes no superadmin."""

    st.markdown("---")
    st.markdown("#### 🧪 Modo Teste")
    st.markdown(
        '<p style="color:#c0a0b8;font-size:.88rem">'
        'Teste a experiência completa do aluno ou do admin sem afetar dados reais. '
        'Os registros ficam isolados e visíveis apenas aqui.</p>',
        unsafe_allow_html=True
    )

    # ── Botões de ativação ────────────────────────────────────────────────────
    if not is_test_mode():
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                '<div style="background:rgba(0,150,255,0.08);border:1px solid rgba(0,150,255,0.3);'
                'border-radius:14px;padding:1rem;text-align:center;margin-bottom:.5rem">'
                '<div style="font-size:1.8rem">👨‍🎓</div>'
                '<p style="color:#e0c0d0;font-weight:600;margin:.3rem 0 .2rem">Experiência do Aluno</p>'
                '<p style="color:#c0a0b8;font-size:.82rem;margin:0">'
                'Faz o quiz completo como um candidato real</p>'
                '</div>',
                unsafe_allow_html=True
            )
            if st.button("▶️ Testar como Aluno", use_container_width=True, key="btn_test_student"):
                enter_test_mode("student")
                st.session_state["page"] = "Quiz"
                st.rerun()
        with c2:
            st.markdown(
                '<div style="background:rgba(255,150,0,0.08);border:1px solid rgba(255,150,0,0.3);'
                'border-radius:14px;padding:1rem;text-align:center;margin-bottom:.5rem">'
                '<div style="font-size:1.8rem">🔐</div>'
                '<p style="color:#e0c0d0;font-weight:600;margin:.3rem 0 .2rem">Experiência do Admin</p>'
                '<p style="color:#c0a0b8;font-size:.82rem;margin:0">'
                'Navega pelo painel como um admin comum</p>'
                '</div>',
                unsafe_allow_html=True
            )
            if st.button("▶️ Testar como Admin", use_container_width=True, key="btn_test_admin"):
                enter_test_mode("admin")
                # Simula perfil admin temporariamente
                st.session_state["_real_role"]  = st.session_state.get("user_role")
                st.session_state["user_role"]   = "admin"
                st.session_state["page"]        = "Painel"
                st.rerun()
    else:
        st.warning("🧪 Modo teste ativo. Saia do modo teste para iniciar outro.")
        if st.button("⏹️ Sair do modo teste agora", use_container_width=True, key="btn_exit_test2"):
            # Restaura perfil real se estava testando como admin
            if "_real_role" in st.session_state:
                st.session_state["user_role"] = st.session_state.pop("_real_role")
            exit_test_mode()
            st.rerun()

    # ── Registros de teste ────────────────────────────────────────────────────
    st.markdown("##### 📋 Registros de Teste")
    test_leads = list_test_leads()

    if not test_leads:
        st.markdown(
            '<div class="dz-card" style="text-align:center;padding:1.2rem">'
            '<p style="color:#c0a0b8;margin:0">Nenhum teste realizado ainda.</p>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        import pandas as pd
        df = pd.DataFrame(test_leads)
        cols_show = [c for c in [
            "id","nome","telefone","curso_recomendado",
            "compatibilidade_pct","status","testado_por","criado_em"
        ] if c in df.columns]
        st.dataframe(
            df[cols_show].rename(columns={
                "id":"ID","nome":"Nome","telefone":"WhatsApp",
                "curso_recomendado":"Curso","compatibilidade_pct":"Compat.%",
                "status":"Status","testado_por":"Testado por","criado_em":"Data"
            }),
            use_container_width=True,
            hide_index=True
        )

        # Ações
        tc1, tc2 = st.columns(2)
        with tc1:
            lead_opts = [f"#{r['id']} — {r.get('nome','?')} ({r.get('criado_em','')[:10]})" for r in test_leads]
            sel = st.selectbox("Excluir registro específico", lead_opts, key="test_del_sel")
            if st.button("🗑️ Excluir este registro", use_container_width=True, key="btn_del_test"):
                sel_id = int(sel.split("—")[0].replace("#","").strip())
                delete_test_lead(sel_id)
                st.success("✅ Registro de teste excluído.")
                st.rerun()
        with tc2:
            st.markdown('<div style="padding-top:1.85rem"></div>', unsafe_allow_html=True)
            if st.button("🗑️ Limpar TODOS os registros de teste", use_container_width=True, key="btn_clear_tests"):
                clear_all_test_leads()
                st.success("✅ Todos os registros de teste excluídos.")
                st.rerun()

        # Detalhes do teste selecionado
        with st.expander("🔍 Ver detalhes do teste selecionado"):
            sel_id = int(sel.split("—")[0].replace("#","").strip())
            lead = next((r for r in test_leads if r["id"] == sel_id), None)
            if lead:
                st.json(lead)
