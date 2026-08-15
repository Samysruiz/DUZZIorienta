"""
Duzzi Orienta — app.py
Banco: Supabase (PostgreSQL) | Fallback: SQLite
Login com perfis: admin e superadmin
"""

import io as _io
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Imports com fallback seguro ───────────────────────────────────────────────
try:
    from database import (
        save_lead, list_leads, mark_inscricao_aberta,
        mark_concluido, delete_lead, get_metrics, supabase_ok, init_db,
    )
    try: from database import mark_descartado
    except: from duzzi import mark_descartado
except ImportError:
    from duzzi import (
        save_lead, list_leads, mark_inscricao_aberta,
        mark_concluido, mark_descartado, delete_lead,
        get_metrics, init_db,
    )
    def supabase_ok(): return False

try:
    from login_page import render_login, logout, require_role
except ImportError:
    def render_login(): return True
    def logout():
        for k in ["logged_in","user_role","username","user_id"]:
            st.session_state.pop(k, None)
        st.rerun()
    def require_role(r): return True

try:
    from admin_panel import render_admin
except ImportError:
    def render_admin(): st.info("admin_panel.py não encontrado no repositório.")

try:
    from lgpd import (
        render_consent_screen, render_consent_refused,
        render_titular_rights, render_lgpd_admin,
    )
    lgpd_ok = True
except ImportError:
    lgpd_ok = False
    def render_consent_screen(): return False
    def render_consent_refused(): pass
    def render_titular_rights(t=""): pass
    def render_lgpd_admin(): pass

try:
    from test_mode import (
        is_test_mode, render_test_banner,
        save_test_lead,
    )
    test_mode_ok = True
except ImportError:
    test_mode_ok = False
    def is_test_mode(): return False
    def render_test_banner(): pass
    def save_test_lead(*a, **kw): return 0

from duzzi import (
    build_explanation, build_message, calculate_scores,
    get_course_map, load_inep_data, load_questions,
    make_url_qr, make_whatsapp_qr, rank_courses,
    score_percent, sms_link, whatsapp_link,
)

try:
    from superadmin import load_config
except ImportError:
    def load_config():
        return {
            "app_title":"Duzzi Orienta",
            "app_subtitle":"Descubra o curso ideal com a Duzzi 🤖✨",
            "hero_text":"Vou te ajudar a descobrir qual curso da Faculdade Donaduzzi combina com você.",
            "cta_quiz":"🎯  Fazer o quiz agora","cta_cursos":"📚  Ver todos os cursos",
            "cor_primaria":"#8B1A2A","cor_fundo":"#1C0508","cor_destaque":"#E8A0A8","cor_gold":"#C8A96E",
            "admin_password":"","max_results":3,"mostrar_inep":True,"mostrar_qr":True,
            "mensagem_sucesso":"✅ Dados salvos! A equipe da Faculdade Donaduzzi pode entrar em contato.",
            "rodape":"Duzzi Orienta • Faculdade Donaduzzi 🎓",
        }

# ── Setup ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Duzzi Orienta", page_icon="🤖",
                   layout="wide", initial_sidebar_state="expanded")

BASE   = Path(__file__).parent
LOGO_D = BASE / "duzzi_logo.png"
LOGO_F = BASE / "logofaculdade.png"
cfg    = load_config()

try: init_db()
except: pass

P = cfg.get("cor_primaria","#c41060")
BG = cfg.get("cor_fundo","#1a0010")
AC = cfg.get("cor_destaque","#ff9ecf")
BG2 = "#2D0A10"

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"]{{background:linear-gradient(160deg,{BG} 0%,{BG2} 40%,{BG} 100%);min-height:100vh}}
[data-testid="stSidebar"]{{background:linear-gradient(180deg,{BG2} 0%,{BG} 100%) !important;border-right:1px solid {P}33}}
[data-testid="stSidebar"] *{{color:#f5d6e8 !important}}
.dz-card{{background:rgba(255,255,255,0.04);border:1px solid {AC}30;border-radius:20px;padding:1.4rem 1.6rem;margin-bottom:1rem;backdrop-filter:blur(8px)}}
.dz-card:hover{{border-color:{AC}80}}
.dz-card-hi{{background:linear-gradient(135deg,{P}40,{BG2}60);border:1.5px solid {P};border-radius:22px;padding:1.5rem 1.8rem;margin-bottom:1.2rem}}
.dz-hero{{background:linear-gradient(135deg,{P}30 0%,{BG2}60 100%);border:1px solid {AC}40;border-radius:28px;padding:2rem 2.4rem}}
.dz-inep{{background:rgba(0,150,100,0.1);border:1px solid rgba(0,200,150,0.3);border-radius:14px;padding:.8rem 1.2rem;margin:.5rem 0}}
.dz-metric{{background:rgba(255,255,255,0.05);border:1px solid {AC}35;border-radius:16px;padding:1.2rem;text-align:center;margin-bottom:.6rem}}
.dz-metric .num{{font-size:2.2rem;font-weight:800;color:{AC};line-height:1}}
.dz-metric .lbl{{font-size:.82rem;color:#c0a0b8;margin-top:.3rem}}
.dz-metric.green .num{{color:#60ffb0}} .dz-metric.red .num{{color:#ff6060}} .dz-metric.teal .num{{color:#60e0ff}}
.dz-bar-wrap{{background:rgba(255,255,255,0.08);border-radius:999px;height:10px;margin:6px 0 12px}}
.dz-bar-fill{{background:linear-gradient(90deg,{P},{AC});border-radius:999px;height:10px}}
.dz-pill{{display:inline-block;padding:.2rem .65rem;margin:.15rem .1rem;border-radius:999px;background:{P}25;border:1px solid {P}50;color:{AC};font-size:.82rem}}
h1,h2,h3,h4{{color:#ffd6ec !important}}
p,li,label,span,.stMarkdown{{color:#e0c0d0 !important}}
input, textarea,
[data-baseweb] input,
[data-baseweb] textarea,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
div[data-baseweb="input"] input,
div[data-baseweb="base-input"] input {{
    background: #3D0A12 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    opacity: 1 !important;
    border: 2px solid #8B1A2A !important;
    border-radius: 10px !important;
    caret-color: #FFFFFF !important;
    font-size: 1rem !important;
}}
input::placeholder,
textarea::placeholder,
[data-baseweb] input::placeholder,
[data-baseweb] textarea::placeholder {{
    color: #C08090 !important;
    -webkit-text-fill-color: #C08090 !important;
    opacity: 1 !important;
}}
[data-testid="stTextInput"] > div,
[data-testid="stTextArea"] > div,
div[data-baseweb="input"],
div[data-baseweb="base-input"] {{
    background: #3D0A12 !important;
    border-radius: 10px !important;
}}
.stButton>button{{background:linear-gradient(135deg,{P},{P}cc) !important;color:white !important;border:none !important;border-radius:12px !important;font-weight:600 !important}}
.stButton>button:hover{{opacity:.88 !important}}
.stRadio label{{background:rgba(255,255,255,0.04) !important;border:1px solid {P}30 !important;border-radius:12px !important;padding:.45rem .9rem !important;color:#f0d0e0 !important;cursor:pointer}}
.stRadio label:hover{{border-color:{P}80 !important}}
[data-testid="stLinkButton"] a{{background:linear-gradient(135deg,{P},{P}cc) !important;color:white !important;border-radius:12px !important;padding:.5rem 1.1rem !important;text-decoration:none !important;font-weight:600 !important}}
.stSuccess{{background:rgba(0,200,100,0.1) !important;border-color:#00c864 !important;color:#a0ffcc !important;border-radius:12px !important}}
.stInfo{{background:rgba(100,150,255,0.1) !important;border-color:#6496ff !important;color:#c0d0ff !important;border-radius:12px !important}}
.stWarning{{background:rgba(255,180,0,0.1) !important;border-color:#ffb400 !important;border-radius:12px !important}}
</style>
""", unsafe_allow_html=True)

# ── Session ───────────────────────────────────────────────────────────────────
for k,v in [("page","Início"),("answers",{}),("student_name",""),("phone",""),
            ("email",""),("escola",""),("cidade",""),("ranking",None),("lead_id",None),
            ("logged_in",False),("user_role",""),("username",""),
            ("inscricao_pendente",False),("inscricao_confirmada",False),
            ("lgpd_consented",None),("lgpd_consent_date","")]:
    if k not in st.session_state: st.session_state[k] = v

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    if LOGO_F.exists(): st.image(str(LOGO_F), use_container_width=True)
    st.markdown("---")
    for pg,ic in [("Início","🏠"),("Quiz","🎯"),("Cursos","📚"),("Dados INEP","📊")]:
        if st.button(f"{ic}  {pg}", key=f"nav_{pg}", use_container_width=True):
            st.session_state.page = pg; st.rerun()
    st.markdown("---")
    if st.session_state.logged_in:
        st.markdown(f"<p style='color:#60ffb0;font-size:.85rem'>👤 {st.session_state.username} ({st.session_state.user_role})</p>", unsafe_allow_html=True)
        if st.button("📊  Painel", key="nav_painel", use_container_width=True):
            st.session_state.page = "Painel"; st.rerun()
        if st.button("🚪  Sair", key="nav_logout", use_container_width=True):
            logout()
    else:
        if st.button("🔐  Login", key="nav_login", use_container_width=True):
            st.session_state.page = "Login"; st.rerun()
    st.markdown("---")
    st.caption(f"{cfg.get('app_title','Duzzi Orienta')}\nFaculdade Donaduzzi")

course_map = get_course_map()
questions  = load_questions()
inep_data  = load_inep_data()
MAX_R      = int(cfg.get("max_results",3))

# ── Banner modo teste (visível só pro superadmin) ─────────────────────────────
if test_mode_ok:
    render_test_banner()

# ── Helpers INEP ──────────────────────────────────────────────────────────────
def _ctx_tda(v):
    if v is None: return ("–","#888","Dado indisponível.")
    if v < 45:   return ("↓ abaixo da média","#60ffb0","Menos alunos saem antes de concluir — sinal positivo de suporte e qualidade do curso.")
    if v < 58:   return ("~ na média","#ffb400","Dentro da média nacional. É normal que parte dos alunos mude de rumo ao longo do curso.")
    return           ("↑ acima da média","#ff8080","Mais alunos saem antes de concluir — pode indicar curso exigente, longo ou que passou por mudanças recentes.")

def _ctx_tca(v):
    if v is None: return ("–","#888","Dado indisponível.")
    if v > 30:   return ("↑ acima da média","#60ffb0","Mais alunos se formam no prazo — ótimo sinal de qualidade e suporte do curso.")
    if v > 20:   return ("~ na média","#ffb400","Dentro da média nacional. A maioria que persiste consegue se formar.")
    return           ("↓ abaixo da média","#ff8080","Menos alunos concluem no prazo — comum em bacharelados longos. Não indica qualidade ruim, só que o percurso é mais longo.")

def _ctx_tap(v):
    if v is None: return ("–","#888","Dado indisponível.")
    if v > 25:   return ("↑ acima da média","#60e0ff","Muitos alunos ainda cursando e dentro do prazo — curso em crescimento.")
    if v > 15:   return ("~ na média","#ffb400","Dentro da média nacional. Uma parcela saudável segue cursando normalmente.")
    return           ("↓ abaixo da média","#c0a0b8","Poucos ainda no meio do curso — geralmente significa que a maioria já concluiu ou o curso é mais curto.")

# ══ INÍCIO ════════════════════════════════════════════════════════════════════
if st.session_state.page == "Início":
    c_txt,c_img = st.columns([1.3,1])
    with c_txt:
        st.markdown('<div class="dz-hero">', unsafe_allow_html=True)
        st.markdown(f"## {cfg.get('app_subtitle','Olá! Eu sou a Duzzi 🤖✨')}")
        st.markdown(cfg.get("hero_text","Vou te ajudar a descobrir qual curso combina com você."))
        st.markdown(f"<p style='color:#c0a0b8'>Responda {len(questions)} perguntas rápidas — resultado direto no celular! 📱</p>", unsafe_allow_html=True)
        st.markdown("")
        b1,b2 = st.columns(2)
        with b1:
            if st.button(cfg.get("cta_quiz","🎯 Fazer o quiz"), use_container_width=True):
                st.session_state.page = "Quiz"; st.rerun()
        with b2:
            if st.button(cfg.get("cta_cursos","📚 Ver cursos"), use_container_width=True):
                st.session_state.page = "Cursos"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c_img:
        if LOGO_D.exists(): st.image(str(LOGO_D), use_container_width=True)
    st.markdown("---")
    st.markdown("### O que a Duzzi leva em conta?")
    cols = st.columns(4)
    for col,(ic,ttl,desc) in zip(cols,[("💻","Tecnologia & Software","Programação, IA, dados e desenvolvimento"),("🧬","Saúde & Laboratório","Farmácia, biotecnologia e análises clínicas"),("📈","Negócios & Gestão","Empreendedorismo, liderança e finanças"),("📚","Educação & Pessoas","Docência, gestão escolar e desenvolvimento humano")]):
        with col: st.markdown(f'<div class="dz-card" style="text-align:center"><div style="font-size:2rem">{ic}</div><h4 style="margin:.4rem 0">{ttl}</h4><p style="font-size:.88rem">{desc}</p></div>', unsafe_allow_html=True)

# ══ CURSOS ════════════════════════════════════════════════════════════════════
elif st.session_state.page == "Cursos":
    st.markdown("## 📚 Cursos da Faculdade Donaduzzi")
    ICONS = {"administracao":"📈","ads":"💻","pedagogia":"📚","ciencia_dados":"📊","eng_software":"⚙️","eng_bioprocessos":"🧬","farmacia":"💊","inteligencia_artificial":"🧠","psicologia":"🧡"}
    for course in course_map.values():
        ic = ICONS.get(course["id"],"🎓")
        pills = " ".join(f'<span class="dz-pill">{t}</span>' for t in course["tags"])
        d = inep_data.get(course["id"],{})
        inep_html = f'<div class="dz-inep">📊 <b>INEP:</b> Conclusão <b style="color:#60ffb0">{d.get("tca","-")}%</b> · Permanência <b style="color:#60e0ff">{d.get("tap","-")}%</b> · Desistência <b style="color:#ff8080">{d.get("tda","-")}%</b></div>' if d and cfg.get("mostrar_inep",True) else ""
        st.markdown(f'<div class="dz-card"><div style="display:flex;align-items:center;gap:.8rem;margin-bottom:.5rem"><span style="font-size:2rem">{ic}</span><div><h3 style="margin:0">{course["name"]}</h3><span style="color:#c0a0b8;font-size:.88rem">{course["level"]} • {course["duration"]} • {course["turno"]}</span></div></div><p>{course["summary"]}</p><p>{pills}</p>{inep_html}</div>', unsafe_allow_html=True)
        _bolsas_file2 = BASE / "bolsas.json"
        if _bolsas_file2.exists():
            import json as _jc
            _bolsas2 = _jc.loads(_bolsas_file2.read_text(encoding="utf-8"))
            with st.expander("💰  Bolsas e Facilidades para este curso"):
                for _b2 in _bolsas2:
                    _tipo_badge2 = {
                        "federal":       ("#0D2A45","#60B0FF","Governo Federal"),
                        "estadual":      ("#0D2A0D","#60DD80","Governo do PR"),
                        "institucional": ("#2A1A0A","#C8A96E","Donaduzzi"),
                    }
                    _bg2,_tc2,_lbl2 = _tipo_badge2.get(_b2["tipo"],("#2D0A10","#E8A0A8","Bolsa"))
                    _reqs2 = "".join(
                        f'<li style="color:#C08090;font-size:.83rem;line-height:1.6">{r}</li>'
                        for r in _b2["requisitos"])
                    st.markdown(
                        f'<div style="background:#2D0A10;border:1px solid #4A1020;border-radius:14px;padding:1rem 1.2rem;margin-bottom:.7rem">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;margin-bottom:.4rem">'
                        f'<div style="display:flex;align-items:center;gap:.6rem">'
                        f'<span style="font-size:1.5rem;line-height:1">{_b2["icone"]}</span>'
                        f'<div><b style="color:#fff;font-size:.95rem">{_b2["nome"]}</b><br>'
                        f'<span style="background:{_bg2};color:{_tc2};font-size:.7rem;padding:.1rem .45rem;border-radius:999px;border:1px solid {_tc2}35">{_lbl2}</span></div>'
                        f'</div>'
                        f'<span style="color:#C8A96E;font-weight:700;font-size:.95rem">{_b2["percentual"]}</span>'
                        f'</div>'
                        f'<p style="color:#E8A0A8;font-size:.88rem;margin:0 0 .4rem;line-height:1.6">{_b2["descricao"]}</p>'
                        f'<div style="background:rgba(200,169,110,0.1);border-left:3px solid #C8A96E;padding:.3rem .65rem;border-radius:0 6px 6px 0;margin-bottom:.4rem">'
                        f'<span style="color:#C8A96E;font-size:.82rem">✨ {_b2["destaque"]}</span></div>'
                        f'<details><summary style="color:#C08090;font-size:.82rem;cursor:pointer">📋 Ver requisitos</summary>'
                        f'<ul style="margin:.4rem 0 0 1rem;padding:0">{_reqs2}</ul></details>'
                        f'</div>',
                        unsafe_allow_html=True)
                st.link_button(
                    "💬 Falar com a equipe sobre bolsas",
                    "https://api.whatsapp.com/send?phone=554520363600&text=Olá!%20Vim%20pelo%20Duzzi%20Orienta%20e%20gostaria%20de%20saber%20mais%20sobre%20as%20bolsas!",
                    use_container_width=True)
        st.link_button(f"🔗 Inscrição — {course['name']}", course["url"])
        st.markdown("")

# ══ DADOS INEP ════════════════════════════════════════════════════════════════
elif st.session_state.page == "Dados INEP":
    st.markdown("## 📊 Indicadores INEP")
    st.markdown(
        '<div class="dz-card" style="margin-bottom:1.2rem">'
        '<p style="margin:0 0 .8rem;font-size:.95rem;color:#ffd6ec;font-weight:600">ℹ️ Como ler esses dados?</p>'
        '<p style="color:#c0a0b8;font-size:.85rem;margin:0 0 .8rem">Para cada curso, o INEP acompanhou uma turma desde o ingresso e mediu o que aconteceu ao longo dos anos. Os 3 indicadores sempre somam 100%:</p>'
        '<div style="display:flex;flex-wrap:wrap;gap:1rem">'
        '<div style="flex:1;min-width:160px;background:rgba(255,80,80,0.08);border-radius:10px;padding:.7rem">'
        '<span style="color:#ff8080;font-weight:700;font-size:.9rem">❌ Abandonaram</span><br>'
        '<span style="color:#c0a0b8;font-size:.82rem">Saíram antes de concluir — por qualquer motivo (troca de curso, trabalho, dificuldade financeira etc.). <b style="color:#ff8080">Quanto menor, melhor.</b></span></div>'
        '<div style="flex:1;min-width:160px;background:rgba(0,180,100,0.08);border-radius:10px;padding:.7rem">'
        '<span style="color:#60ffb0;font-weight:700;font-size:.9rem">🎓 Se formaram</span><br>'
        '<span style="color:#c0a0b8;font-size:.82rem">Concluíram o curso dentro do prazo esperado. <b style="color:#60ffb0">Quanto maior, melhor.</b></span></div>'
        '<div style="flex:1;min-width:160px;background:rgba(0,150,255,0.08);border-radius:10px;padding:.7rem">'
        '<span style="color:#60e0ff;font-weight:700;font-size:.9rem">📚 Ainda cursando</span><br>'
        '<span style="color:#c0a0b8;font-size:.82rem">Continuam no curso e ainda têm tempo para concluir dentro do prazo. Comum em cursos mais longos.</span></div>'
        '</div>'
        '<p style="margin:.8rem 0 0;color:#888;font-size:.75rem">📁 Fonte: INEP — Coorte 2020, referência 2024. Dados nacionais por área de conhecimento, usados como comparativo.</p>'
        '</div>',
        unsafe_allow_html=True)

    ICONS_INEP = {"administracao":"📈","ads":"💻","pedagogia":"📚","ciencia_dados":"📊","eng_software":"⚙️","eng_bioprocessos":"🧬","farmacia":"💊","inteligencia_artificial":"🧠","psicologia":"🧡"}

    cursos_com = [(cid,c) for cid,c in course_map.items() if inep_data.get(cid,{}).get("tda")]
    cursos_sem = [(cid,c) for cid,c in course_map.items() if not inep_data.get(cid,{}).get("tda")]

    if cursos_com:
        st.markdown("### 📌 Cursos com dados disponíveis")
        for cid, course in cursos_com:
            d    = inep_data.get(cid, {})
            tda  = d.get("tda"); tca = d.get("tca"); tap = d.get("tap")
            ic   = ICONS_INEP.get(cid, "🎓")
            area = d.get("area","")
            fonte = d.get("fonte","")
            fonte_badge = (
                '<span style="background:rgba(100,200,100,0.1);color:#60ffb0;font-size:.7rem;padding:.1rem .4rem;border-radius:4px">INEP 2024</span>'
                if fonte != "fallback" else
                '<span style="background:rgba(255,180,0,0.1);color:#ffb400;font-size:.7rem;padding:.1rem .4rem;border-radius:4px">ref. nacional</span>'
            )
            tda_lbl,tda_cor,tda_desc = _ctx_tda(tda)
            tca_lbl,tca_cor,tca_desc = _ctx_tca(tca)
            tap_lbl,tap_cor,tap_desc = _ctx_tap(tap)

            st.markdown(
                f'<div class="dz-card" style="margin-bottom:.8rem">'
                f'<div style="display:flex;align-items:center;gap:.8rem;margin-bottom:1rem">'
                f'<span style="font-size:1.8rem">{ic}</span>'
                f'<div><h4 style="margin:0;color:#ffd6ec">{course["name"]}</h4>'
                f'<span style="color:#c0a0b8;font-size:.82rem">{course["level"]} • {area} &nbsp;{fonte_badge}</span>'
                f'</div></div>'
                f'<div style="margin-bottom:.8rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
                f'<span style="color:#ff8080;font-size:.82rem;font-weight:600">❌ Abandonaram o curso</span>'
                f'<span><span style="color:#ff8080;font-weight:700">{tda}%</span>'
                f'&nbsp;<span style="color:{tda_cor};font-size:.75rem">{tda_lbl}</span></span></div>'
                f'<div class="dz-bar-wrap"><div style="background:linear-gradient(90deg,#8B1A2A,#ff4060);border-radius:999px;height:10px;width:{min(tda or 0,100)}%"></div></div>'
                f'<p style="color:#888;font-size:.78rem;margin:.2rem 0 0">{tda_desc}</p></div>'
                f'<div style="margin-bottom:.8rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
                f'<span style="color:#60ffb0;font-size:.82rem;font-weight:600">🎓 Se formaram no prazo</span>'
                f'<span><span style="color:#60ffb0;font-weight:700">{tca}%</span>'
                f'&nbsp;<span style="color:{tca_cor};font-size:.75rem">{tca_lbl}</span></span></div>'
                f'<div class="dz-bar-wrap"><div style="background:linear-gradient(90deg,#00a060,#60ffb0);border-radius:999px;height:10px;width:{min(tca or 0,100)}%"></div></div>'
                f'<p style="color:#888;font-size:.78rem;margin:.2rem 0 0">{tca_desc}</p></div>'
                f'<div>'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
                f'<span style="color:#60e0ff;font-size:.82rem;font-weight:600">📚 Ainda cursando</span>'
                f'<span><span style="color:#60e0ff;font-weight:700">{tap}%</span>'
                f'&nbsp;<span style="color:{tap_cor};font-size:.75rem">{tap_lbl}</span></span></div>'
                f'<div class="dz-bar-wrap"><div style="background:linear-gradient(90deg,#0060a0,#60e0ff);border-radius:999px;height:10px;width:{min(tap or 0,100)}%"></div></div>'
                f'<p style="color:#888;font-size:.78rem;margin:.2rem 0 0">{tap_desc}</p></div>'
                f'</div>',
                unsafe_allow_html=True)

    if cursos_sem:
        st.markdown("### 🆕 Cursos novos — sem dados históricos")
        st.markdown('<p style="color:#c0a0b8;font-size:.88rem">Estes cursos são recentes demais para constar na coorte 2020 do INEP. São cursos inovadores e alinhados com as demandas atuais do mercado!</p>', unsafe_allow_html=True)
        cols_new = st.columns(min(len(cursos_sem), 3))
        for idx,(cid,course) in enumerate(cursos_sem):
            with cols_new[idx % 3]:
                st.markdown(
                    f'<div class="dz-card" style="text-align:center;padding:1.2rem">'
                    f'<div style="font-size:2rem;margin-bottom:.4rem">{ICONS_INEP.get(cid,"🎓")}</div>'
                    f'<h4 style="margin:0 0 .3rem;font-size:.9rem;color:#ffd6ec">{course["name"]}</h4>'
                    f'<span style="color:#c0a0b8;font-size:.78rem">{course["level"]}</span><br>'
                    f'<span style="background:rgba(100,150,255,0.15);color:#a0c0ff;font-size:.72rem;padding:.2rem .5rem;border-radius:6px;margin-top:.4rem;display:inline-block">✨ Curso novo</span>'
                    f'</div>',
                    unsafe_allow_html=True)



# ══ QUIZ ══════════════════════════════════════════════════════════════════════
elif st.session_state.page == "Quiz":

    # ── Gate de consentimento LGPD ────────────────────────────────────────────
    if lgpd_ok and st.session_state.get("lgpd_consented") is None:
        st.markdown("## 🎯 Descubra seu curso ideal")
        render_consent_screen()
        st.stop()
    elif lgpd_ok and st.session_state.get("lgpd_consented") is False:
        render_consent_refused()
        st.stop()

    st.markdown("## 🎯 Descubra seu curso ideal")
    st.markdown('<div class="dz-card">', unsafe_allow_html=True)
    st.markdown("#### 👤 Seus dados")

    import re as _re

    _nome_raw = st.text_input("Nome completo *",
        value=st.session_state.student_name, placeholder="Ex: João da Silva")
    _nome_clean = _re.sub(r"[^a-zA-ZÀ-ÿ\s]", "", _nome_raw).strip()
    _nome_fmt = " ".join(w.capitalize() for w in _nome_clean.split())
    if _nome_fmt != _nome_raw:
        st.session_state.student_name = _nome_fmt
    else:
        st.session_state.student_name = _nome_raw
    if _nome_raw and _nome_raw != _nome_fmt:
        st.caption(f"✏️ Nome formatado: **{_nome_fmt}**")

    c1, c2 = st.columns(2)
    with c1:
        _tel_raw = st.text_input("WhatsApp (com DDD) *",
            value=st.session_state.phone, placeholder="45 99999-9999")
        _tel_digits = "".join(c for c in _tel_raw if c.isdigit())
        if len(_tel_digits) == 11:
            _tel_fmt = f"({_tel_digits[:2]}) {_tel_digits[2:7]}-{_tel_digits[7:]}"
        elif len(_tel_digits) == 10:
            _tel_fmt = f"({_tel_digits[:2]}) {_tel_digits[2:6]}-{_tel_digits[6:]}"
        else:
            _tel_fmt = _tel_raw
        st.session_state.phone = _tel_digits
        if _tel_digits and len(_tel_digits) not in (10, 11):
            st.caption("⚠️ Digite DDD + número (10 ou 11 dígitos)")
        elif _tel_digits:
            st.caption(f"📱 {_tel_fmt}")

    with c2:
        st.session_state.email = st.text_input("E-mail (opcional)",
            value=st.session_state.email, placeholder="seu@email.com")
        if st.session_state.email and "@" not in st.session_state.email:
            st.caption("⚠️ E-mail inválido")

    _ESTADOS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS",
                "MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC",
                "SE","SP","TO"]
    cc1, cc2 = st.columns([3, 1])
    with cc1:
        _cid_raw = st.text_input("Sua cidade *",
            value=st.session_state.cidade, placeholder="Ex: Toledo")
        _cid_fmt = " ".join(w.capitalize() for w in
                            _re.sub(r"[^a-zA-ZÀ-ÿ\s]","",_cid_raw).split())
        st.session_state.cidade = _cid_fmt if _cid_fmt else _cid_raw
        if _cid_raw and _cid_fmt and _cid_raw.strip() != _cid_fmt:
            st.caption(f"✏️ Cidade: **{_cid_fmt}**")
    with cc2:
        _estado_atual = st.session_state.get("estado", "PR")
        _idx_estado = _ESTADOS.index(_estado_atual) if _estado_atual in _ESTADOS else _ESTADOS.index("PR")
        st.session_state.estado = st.selectbox("Estado *",
            _ESTADOS, index=_idx_estado, key="sel_estado")

    _esc_raw = st.text_input("Escola onde você estuda ou estudou *",
        value=st.session_state.escola, placeholder="Ex: Colégio Estadual X")
    _esc_fmt = " ".join(w.capitalize() for w in _esc_raw.split())
    st.session_state.escola = _esc_fmt if _esc_fmt else _esc_raw
    if _esc_raw and _esc_fmt and _esc_raw.strip() != _esc_fmt:
        st.caption(f"✏️ Escola: **{_esc_fmt}**")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Direitos do titular LGPD ──────────────────────────────────────────────
    if lgpd_ok:
        render_titular_rights(st.session_state.phone)

    st.markdown("")
    answered = sum(1 for q in questions if q["id"] in st.session_state.answers)
    total_q  = len(questions)
    st.markdown(f'<div style="margin-bottom:1rem"><div style="display:flex;justify-content:space-between;color:#c0a0b8;font-size:.88rem;margin-bottom:4px"><span>Progresso</span><span>{answered}/{total_q}</span></div><div class="dz-bar-wrap"><div class="dz-bar-fill" style="width:{int(answered/total_q*100)}%"></div></div></div>', unsafe_allow_html=True)
    for idx,q in enumerate(questions,1):
        labels  = [o["label"] for o in q["options"]]
        current = st.session_state.answers.get(q["id"])
        st.markdown(f'<div class="dz-card"><p style="color:{AC};font-size:.82rem;margin-bottom:.2rem">PERGUNTA {idx} DE {total_q}</p><h4 style="margin-top:0">{q["text"]}</h4></div>', unsafe_allow_html=True)
        default_idx = current if (current is not None and current < len(labels)) else 0
        if q["id"] not in st.session_state.answers:
            st.session_state.answers[q["id"]] = default_idx
        sel = st.radio(label=f"q{idx}", options=labels, index=default_idx,
                       key=f"radio_{q['id']}", label_visibility="collapsed")
        if sel is not None:
            st.session_state.answers[q["id"]] = labels.index(sel)
        st.markdown("")
    dados_ok = bool(st.session_state.student_name and st.session_state.phone and st.session_state.cidade and st.session_state.escola)
    all_ok   = answered == total_q and dados_ok
    if not dados_ok: st.warning("⚠️ Preencha nome, WhatsApp, cidade e escola.")
    elif not all_ok: st.info(f"Responda todas as {total_q} perguntas.")
    if st.button("🚀  Gerar minha recomendação!", type="primary", use_container_width=True, disabled=not all_ok):
        scores  = calculate_scores(st.session_state.answers)
        ranking = rank_courses(scores)
        st.session_state.ranking = ranking
        top     = ranking[0]
        top_pct = top.get("compat_pct", score_percent(top["score"]))
        _cidade_estado = f"{st.session_state.cidade} — {st.session_state.get('estado','')}"

        # Em modo teste, salva separado — não contamina dados reais
        if test_mode_ok and is_test_mode():
            lead_id = save_test_lead(
                nome=st.session_state.student_name, telefone=st.session_state.phone,
                email=st.session_state.email, escola_origem=st.session_state.escola,
                cidade=_cidade_estado, top_course=top["name"],
                score_top=top["score"], compat_pct=top_pct,
                ranking_json=json.dumps(ranking[:MAX_R], ensure_ascii=False),
                notas="Teste via modo superadmin",
            )
        else:
            lead_id = save_lead(
                nome=st.session_state.student_name, telefone=st.session_state.phone,
                email=st.session_state.email, escola_origem=st.session_state.escola,
                cidade=_cidade_estado, top_course=top["name"],
                score_top=top["score"], compat_pct=top_pct,
                ranking_json=json.dumps(ranking[:MAX_R], ensure_ascii=False),
            )
        st.session_state.lead_id = lead_id
        st.session_state.inscricao_pendente = False
        st.session_state.inscricao_confirmada = False
        st.rerun()

    ranking = st.session_state.ranking
    lead_id = st.session_state.lead_id
    if ranking:
        st.markdown("---")
        top = ranking[0]; top_pct = top.get("compat_pct", score_percent(top["score"]))
        d = inep_data.get(top["id"],{})
        inep_mini = f'<p style="color:#60ffb0;font-size:.85rem;margin:.5rem 0 0">📊 INEP: Conclusão {d.get("tca","-")}% · Permanência {d.get("tap","-")}% · Desistência {d.get("tda","-")}%</p>' if d and cfg.get("mostrar_inep",True) else ""
        st.markdown(f'<div class="dz-card-hi"><p style="color:{AC};font-size:.88rem;margin-bottom:.3rem">🏆 CURSO EM DESTAQUE PARA VOCÊ</p><h2 style="margin:0 0 .4rem">{top["name"]}</h2><p style="color:#c0a0b8;font-size:.9rem">{top["level"]} • {top["duration"]} • {top["turno"]}</p><div class="dz-bar-wrap"><div class="dz-bar-fill" style="width:{top_pct}%"></div></div><p style="color:{AC};font-size:.9rem;margin:0">{top_pct}% de compatibilidade</p>{inep_mini}</div>', unsafe_allow_html=True)
        st.link_button(f"🔗 Quero me inscrever em {top['name']}", top["url"], use_container_width=True)

        if lead_id:
            if not st.session_state.get("inscricao_confirmada"):
                if not st.session_state.get("inscricao_pendente"):
                    if st.button("✅ Cliquei no link de inscrição!",
                                 key="clicked_inscricao",
                                 use_container_width=True):
                        st.session_state.inscricao_pendente = True
                        st.rerun()
                else:
                    st.markdown(
                        '<div style="background:rgba(200,169,110,0.12);border:1px solid #C8A96E;'
                        'border-radius:14px;padding:1rem 1.4rem;margin:.5rem 0;text-align:center">'
                        '<p style="color:#C8A96E;font-weight:600;margin:0 0 .4rem">🎯 Tem certeza?</p>'
                        '<p style="color:#E8A0A8;font-size:.9rem;margin:0">'
                        'Vamos registrar que você acessou o link de inscrição.</p>'
                        '</div>',
                        unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Sim, confirmar!", key="confirmar_inscricao", use_container_width=True):
                            mark_inscricao_aberta(lead_id)
                            st.session_state.inscricao_confirmada = True
                            st.session_state.inscricao_pendente = False
                            st.rerun()
                    with c2:
                        if st.button("↩️ Voltar", key="cancelar_inscricao", use_container_width=True):
                            st.session_state.inscricao_pendente = False
                            st.rerun()
            else:
                st.markdown(
                    '<div style="background:rgba(0,200,100,0.08);border:1.5px solid #00c864;'
                    'border-radius:16px;padding:1.2rem 1.6rem;margin:.5rem 0;text-align:center">'
                    '<div style="font-size:2rem">🎉</div>'
                    '<p style="color:#60ffb0;font-weight:700;font-size:1.05rem;margin:.3rem 0">'
                    'Inscrição registrada!</p>'
                    '<p style="color:#a0ffcc;font-size:.9rem;margin:0">'
                    'Boa sorte! A equipe da Donaduzzi pode entrar em contato em breve 😊</p>'
                    '</div>',
                    unsafe_allow_html=True)

        st.markdown("### Seu ranking completo")
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣"]

        # Monta mapa de respostas escolhidas: {q_id: label escolhida}
        _respostas_labels = {}
        for q in questions:
            ans_idx = st.session_state.answers.get(q["id"])
            if ans_idx is not None and ans_idx < len(q["options"]):
                _respostas_labels[q["id"]] = q["options"][ans_idx]["label"]

        for i,course in enumerate(ranking[:MAX_R]):
            pct = course.get("compat_pct", score_percent(course["score"]))
            pills = " ".join(f'<span class="dz-pill">{t}</span>' for t in course["tags"][:4])
            dd = inep_data.get(course["id"],{})

            # ── Motivos personalizados com base nas respostas ──────────────
            _motivos = []
            for q in questions:
                ans_idx = st.session_state.answers.get(q["id"])
                if ans_idx is None or ans_idx >= len(q["options"]):
                    continue
                opt = q["options"][ans_idx]
                peso = opt.get("weights", {}).get(course["id"], 0)
                if peso >= 3:
                    _motivos.append(
                        f'<span style="background:rgba(139,26,42,0.3);border:1px solid {AC}40;'
                        f'border-radius:8px;padding:.15rem .5rem;font-size:.8rem;color:{AC};'
                        f'margin:.15rem .1rem;display:inline-block">'
                        f'✓ "{opt["label"]}"</span>'
                    )

            _motivos_html = ""
            if _motivos:
                _motivos_html = (
                    f'<p style="color:#c0a0b8;font-size:.78rem;margin:.4rem 0 .2rem">'
                    f'💡 Suas respostas que impulsionaram este curso:</p>'
                    f'<div style="margin-bottom:.5rem">{"".join(_motivos[:3])}</div>'
                )

            # ── INEP contextualizado ───────────────────────────────────────
            _inep_html = ""
            if dd and cfg.get("mostrar_inep", True):
                tda = dd.get("tda", None)
                tca = dd.get("tca", None)

                def _tda_ctx(v):
                    if v is None: return ""
                    if v < 45:   return f'<span style="color:#60ffb0">↓ abaixo da média nacional ({v}%)</span>'
                    if v < 58:   return f'<span style="color:#ffb400">~ na média nacional ({v}%)</span>'
                    return       f'<span style="color:#ff8080">↑ acima da média nacional ({v}%)</span>'

                def _tca_ctx(v):
                    if v is None: return ""
                    if v > 30:   return f'<span style="color:#60ffb0">↑ acima da média nacional ({v}%)</span>'
                    if v > 20:   return f'<span style="color:#ffb400">~ na média nacional ({v}%)</span>'
                    return       f'<span style="color:#ff8080">↓ abaixo da média nacional ({v}%)</span>'

                _inep_html = (
                    f'<div style="background:rgba(0,150,100,0.08);border:1px solid rgba(0,200,150,0.2);'
                    f'border-radius:10px;padding:.5rem .8rem;margin:.4rem 0;font-size:.82rem">'
                    f'📊 <b style="color:#e0c0d0">INEP nacional:</b> '
                    f'Desistência {_tda_ctx(tda)} &nbsp;·&nbsp; '
                    f'Conclusão {_tca_ctx(tca)}'
                    f'</div>'
                )

            st.markdown(
                f'<div class="dz-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<h3 style="margin:0">{medals[i] if i<len(medals) else str(i+1)} {course["name"]}</h3>'
                f'<span style="color:{AC};font-weight:700;font-size:1.1rem">{pct}%</span>'
                f'</div>'
                f'<p style="color:#c0a0b8;font-size:.85rem;margin:.3rem 0">{course["level"]} • {course["duration"]} • {course["turno"]}</p>'
                f'<div class="dz-bar-wrap"><div class="dz-bar-fill" style="width:{pct}%"></div></div>'
                f'<p style="margin:.4rem 0">{build_explanation(course)}</p>'
                f'{_motivos_html}'
                f'{_inep_html}'
                f'<p style="margin:.4rem 0">{pills}</p>'
                f'</div>',
                unsafe_allow_html=True
            )
            cname = course["name"]; curl = course["url"]
            st.link_button(f"Ver {cname}", curl)
            st.markdown("")
        st.markdown("---"); st.markdown("### 📲 Receba no celular")
        message = build_message(st.session_state.student_name or "estudante", ranking)
        message = message.replace("Duzzi Orienta • Faculdade Donaduzzi 🎓", cfg.get("rodape","Duzzi Orienta • Faculdade Donaduzzi 🎓"))
        col_msg,col_qr = st.columns([1.4,1])
        with col_msg:
            st.text_area("Mensagem pronta", message, height=210)
            if st.session_state.phone:
                b1,b2 = st.columns(2)
                with b1: st.link_button("💬 WhatsApp", whatsapp_link(st.session_state.phone, message), use_container_width=True)
                with b2: st.link_button("📩 SMS", sms_link(st.session_state.phone, message), use_container_width=True)
        with col_qr:
            if st.session_state.phone:
                st.markdown('<div class="dz-card" style="text-align:center">', unsafe_allow_html=True)
                st.image(make_whatsapp_qr(st.session_state.phone, message), width=200, caption="📷 Escaneie e abra no WhatsApp")
                st.markdown('</div>', unsafe_allow_html=True)
        if cfg.get("mostrar_qr",True):
            st.markdown("#### 🎓 QR Code de inscrição")
            ca,cb = st.columns([1,2])
            with ca: st.image(make_url_qr(top["url"]), width=180, caption=f"Inscrição — {top['name']}")
            with cb: st.markdown(f'<div class="dz-card"><h4>Pronto? 🚀</h4><p>Escaneie para acessar a inscrição de <strong>{top["name"]}</strong> no celular!</p></div>', unsafe_allow_html=True)
        st.success(cfg.get("mensagem_sucesso","✅ Dados salvos!"))

        # ── Bolsas personalizadas ─────────────────────────────────────────
        st.markdown("---")
        import json as _j
        _bolsas_file = BASE / "bolsas.json"
        if _bolsas_file.exists():
            _bolsas = _j.loads(_bolsas_file.read_text(encoding="utf-8"))
            _cidade_lower = st.session_state.cidade.lower()
            _is_pr = any(c in _cidade_lower for c in [
                "toledo","cascavel","foz","londrina","curitiba","maringá",
                "paranavaí","umuarama","campo mourão","ponta grossa","guarapuava",
                "francisco beltrão","chapecó","palotina","assis chateaubriand"])

            with st.expander("💰  Bolsas e Facilidades — veja como tornar isso possível para você!", expanded=False):
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,rgba(200,169,110,0.12),rgba(139,26,42,0.10));border-left:4px solid #C8A96E;border-radius:0 12px 12px 0;padding:1rem 1.2rem;margin-bottom:1.2rem">'
                    f'<p style="color:#C8A96E;font-weight:500;margin:0 0 .3rem">💬 A Duzzi te conta:</p>'
                    f'<p style="color:#E8A0A8;font-size:.95rem;margin:0">Para chegar até a <b style="color:#fff">{top["name"]}</b>, '
                    f'existem caminhos que tornam tudo muito mais leve. Veja o que temos para você:</p>'
                    f'</div>',
                    unsafe_allow_html=True)

                for _b in _bolsas:
                    if _b.get("apenas_parana") and not _is_pr:
                        continue
                    _tipo_badge = {
                        "federal":       ("#0D2A45", "#60B0FF", "Governo Federal"),
                        "estadual":      ("#0D2A0D", "#60DD80", "Governo do PR"),
                        "institucional": ("#2A1A0A", "#C8A96E", "Donaduzzi"),
                    }
                    _bg, _tc, _lbl = _tipo_badge.get(_b["tipo"], ("#2D0A10","#E8A0A8","Bolsa"))
                    _reqs = "".join(
                        f'<li style="color:#C08090;font-size:.84rem;line-height:1.6;margin:.1rem 0">{r}</li>'
                        for r in _b["requisitos"])
                    st.markdown(
                        f'<div class="dz-card" style="margin-bottom:.8rem">'
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;margin-bottom:.6rem">'
                        f'<div style="display:flex;align-items:center;gap:.7rem">'
                        f'<span style="font-size:1.8rem;line-height:1">{_b["icone"]}</span>'
                        f'<div>'
                        f'<h4 style="margin:0 0 .2rem;color:#fff;font-size:1rem">{_b["nome"]}</h4>'
                        f'<span style="background:{_bg};color:{_tc};font-size:.72rem;padding:.12rem .5rem;border-radius:999px;border:1px solid {_tc}35;font-weight:500">{_lbl}</span>'
                        f'</div></div>'
                        f'<div style="text-align:right;flex-shrink:0">'
                        f'<span style="color:#C8A96E;font-size:1.05rem;font-weight:700">{_b["percentual"]}</span>'
                        f'</div></div>'
                        f'<p style="color:#E8A0A8;font-size:.92rem;margin:0 0 .5rem;line-height:1.6">{_b["descricao"]}</p>'
                        f'<div style="background:rgba(200,169,110,0.1);border-left:3px solid #C8A96E;padding:.35rem .75rem;border-radius:0 6px 6px 0;margin:.5rem 0">'
                        f'<span style="color:#C8A96E;font-size:.84rem">✨ {_b["destaque"]}</span></div>'
                        f'<details style="margin-top:.6rem">'
                        f'<summary style="color:#C08090;font-size:.84rem;cursor:pointer;user-select:none">📋 Ver requisitos</summary>'
                        f'<ul style="margin:.5rem 0 0 1rem;padding:0">{_reqs}</ul></details>'
                        f'</div>',
                        unsafe_allow_html=True)
                    st.link_button(
                        f"Saber mais sobre {_b['nome']}",
                        _b["link"],
                    )
                    st.markdown("")

                st.markdown(
                    '<div class="dz-card" style="text-align:center;background:rgba(139,26,42,0.15);border-color:#8B1A2A60;padding:1rem">'
                    '<p style="color:#E8A0A8;margin:0 0 .2rem;font-size:.95rem">Ficou com dúvida sobre qual bolsa encaixa no seu perfil?</p>'
                    '<p style="color:#C08090;font-size:.85rem;margin:0">A equipe da Donaduzzi te ajuda a escolher a melhor opção! 😊</p>'
                    '</div>',
                    unsafe_allow_html=True)
                st.link_button(
                    "💬 Falar com a equipe da Donaduzzi",
                    "https://api.whatsapp.com/send?phone=554520363600&text=Olá!%20Vim%20pelo%20Duzzi%20Orienta%20e%20gostaria%20de%20saber%20mais%20sobre%20as%20bolsas!",
                    use_container_width=True)

# ══ LOGIN ═════════════════════════════════════════════════════════════════════
elif st.session_state.page == "Login":
    logged = render_login()
    if logged:
        st.session_state.page = "Painel"
        st.rerun()

# ══ PAINEL ════════════════════════════════════════════════════════════════════
elif st.session_state.page == "Painel":
    if not st.session_state.logged_in:
        st.session_state.page = "Login"
        st.rerun()
    else:
        render_admin()
