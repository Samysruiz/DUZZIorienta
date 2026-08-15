"""
superadmin.py — Painel Super Admin do Duzzi Orienta
Permite editar perguntas, cursos, textos e configurações visuais.
"""

import json
from pathlib import Path

import streamlit as st

BASE_DIR     = Path(__file__).parent
COURSES_FILE = BASE_DIR / "courses.json"
QUESTIONS_FILE = BASE_DIR / "questions.json"
CONFIG_FILE  = BASE_DIR / "config.json"

SUPER_PWD = "duzzi@super2024"  # troque via variável de ambiente DUZZI_SUPER_PASSWORD

# ── Config padrão ─────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "app_title":    "Duzzi Orienta",
    "app_subtitle": "Descubra o curso ideal com a Duzzi 🤖✨",
    "hero_text":    "Vou te ajudar a descobrir qual curso da Faculdade Donaduzzi combina com o seu jeito de pensar, seus interesses e seus sonhos.",
    "cta_quiz":     "🎯  Fazer o quiz agora",
    "cta_cursos":   "📚  Ver todos os cursos",
    "cor_primaria": "#8B1A2A",
    "cor_fundo":    "#1C0508",
    "cor_destaque": "#E8A0A8",
    "cor_gold":     "#C8A96E",
    "admin_password": "",
    "max_results":  3,
    "mostrar_inep": True,
    "mostrar_qr":   True,
    "mensagem_sucesso": "✅ Dados salvos automaticamente! A equipe da Faculdade Donaduzzi pode entrar em contato em breve.",
    "rodape":       "Duzzi Orienta • Faculdade Donaduzzi 🎓",
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        cfg = {**DEFAULT_CONFIG, **saved}
    else:
        cfg = DEFAULT_CONFIG.copy()
    return cfg


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_courses() -> list:
    with open(COURSES_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_courses(courses: list):
    with open(COURSES_FILE, "w", encoding="utf-8") as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)


def load_questions() -> list:
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_questions(questions: list):
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER PRINCIPAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render(super_pwd: str = SUPER_PWD):
    import os
    super_pwd = os.getenv("DUZZI_SUPER_PASSWORD", super_pwd)

    st.markdown("## ⚙️ Super Admin")
    st.markdown("<p style='color:#c0a0b8'>Área restrita — controle total do sistema.</p>", unsafe_allow_html=True)

    pwd = st.text_input("Senha Super Admin", type="password", placeholder="••••••••••")
    if pwd != super_pwd:
        st.warning("Digite a senha Super Admin para continuar.")
        st.stop()

    cfg = load_config()

    # ── Abas ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Perguntas do Quiz",
        "🎓 Cursos",
        "🎨 Aparência & Textos",
        "⚙️ Configurações",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — PERGUNTAS
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### 💬 Gerenciar Perguntas do Quiz")
        questions = load_questions()

        # Adicionar nova pergunta
        with st.expander("➕ Adicionar nova pergunta"):
            new_q_text = st.text_input("Texto da pergunta", key="new_q_text", placeholder="Ex: Você prefere trabalhar com pessoas ou tecnologia?")
            new_q_id   = st.text_input("ID da pergunta", key="new_q_id", placeholder="Ex: q9")

            st.markdown("**Opções de resposta** (preencha pelo menos 2):")
            new_opts = []
            courses_ids = [c["id"] for c in load_courses()]

            for oi in range(5):
                col_l, col_w = st.columns([1, 2])
                with col_l:
                    lbl = st.text_input(f"Opção {oi+1}", key=f"new_opt_lbl_{oi}", placeholder=f"Texto da opção {oi+1}")
                with col_w:
                    st.markdown(f"*Pesos para opção {oi+1}* (formato: `curso_id:peso,curso_id:peso`)")
                    w_str = st.text_input("", key=f"new_opt_w_{oi}", placeholder="inteligencia_artificial:3,ciencia_dados:2")
                if lbl:
                    weights = {}
                    for part in w_str.split(","):
                        part = part.strip()
                        if ":" in part:
                            k, v = part.split(":", 1)
                            try: weights[k.strip()] = int(v.strip())
                            except: pass
                    new_opts.append({"label": lbl, "weights": weights})

            if st.button("✅ Adicionar pergunta", key="btn_add_q"):
                if new_q_text and new_q_id and len(new_opts) >= 2:
                    if any(q["id"] == new_q_id for q in questions):
                        st.error(f"ID '{new_q_id}' já existe! Use outro ID.")
                    else:
                        questions.append({"id": new_q_id, "text": new_q_text, "options": new_opts})
                        save_questions(questions)
                        st.success(f"✅ Pergunta '{new_q_id}' adicionada!")
                        st.rerun()
                else:
                    st.error("Preencha o texto, o ID e pelo menos 2 opções.")

        st.markdown("---")
        st.markdown(f"**{len(questions)} perguntas cadastradas**")

        for qi, q in enumerate(questions):
            with st.expander(f"📝 {q['id']} — {q['text'][:60]}..."):
                col_edit, col_del = st.columns([4, 1])

                with col_edit:
                    new_text = st.text_input("Texto", value=q["text"], key=f"q_text_{qi}")

                    st.markdown("**Opções:**")
                    new_options = []
                    for oi, opt in enumerate(q["options"]):
                        st.markdown(f"*Opção {oi+1}*")
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            new_lbl = st.text_input("Label", value=opt["label"], key=f"q{qi}_opt{oi}_lbl")
                        with c2:
                            w_str = ", ".join(f"{k}:{v}" for k, v in opt.get("weights", {}).items())
                            new_w_str = st.text_input("Pesos (curso:valor)", value=w_str, key=f"q{qi}_opt{oi}_w")
                        weights = {}
                        for part in new_w_str.split(","):
                            part = part.strip()
                            if ":" in part:
                                k, v = part.split(":", 1)
                                try: weights[k.strip()] = int(v.strip())
                                except: pass
                        new_options.append({"label": new_lbl, "weights": weights})

                    if st.button("💾 Salvar alterações", key=f"save_q_{qi}"):
                        questions[qi] = {"id": q["id"], "text": new_text, "options": new_options}
                        save_questions(questions)
                        st.success("✅ Pergunta salva!")
                        st.rerun()

                with col_del:
                    st.markdown("")
                    st.markdown("")
                    if st.button("🗑️ Excluir", key=f"del_q_{qi}"):
                        questions.pop(qi)
                        save_questions(questions)
                        st.success("✅ Pergunta excluída!")
                        st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — CURSOS
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### 🎓 Gerenciar Cursos")
        courses = load_courses()

        with st.expander("➕ Adicionar novo curso"):
            nc1, nc2 = st.columns(2)
            with nc1:
                n_id       = st.text_input("ID do curso", placeholder="Ex: direito")
                n_name     = st.text_input("Nome do curso", placeholder="Ex: Direito")
                n_level    = st.selectbox("Grau acadêmico", ["Bacharelado","Tecnólogo","Licenciatura"])
                n_duration = st.text_input("Duração", placeholder="Ex: 10 semestres")
            with nc2:
                n_turno   = st.selectbox("Turno", ["Noturno","Matutino","Integral","Vespertino"])
                n_url     = st.text_input("URL da página", placeholder="https://faculdadedonaduzzi.com.br/...")
                n_summary = st.text_area("Resumo", placeholder="Breve descrição do curso...")
            n_tags  = st.text_input("Tags (separadas por vírgula)", placeholder="gestão,direito,carreiras jurídicas")
            n_areas = st.text_input("Áreas de atuação (separadas por vírgula)", placeholder="advocacia,gestão pública,consultoria")
            n_ev    = st.text_input("Destaques/evidências (separados por vírgula)", placeholder="Estágio desde o 1º ano,Alta empregabilidade")

            if st.button("✅ Adicionar curso", key="btn_add_course"):
                if n_id and n_name and n_url:
                    if any(c["id"] == n_id for c in courses):
                        st.error(f"ID '{n_id}' já existe!")
                    else:
                        courses.append({
                            "id": n_id, "name": n_name, "level": n_level,
                            "duration": n_duration, "turno": n_turno, "url": n_url,
                            "summary": n_summary,
                            "tags":     [t.strip() for t in n_tags.split(",") if t.strip()],
                            "areas":    [a.strip() for a in n_areas.split(",") if a.strip()],
                            "evidence": [e.strip() for e in n_ev.split(",") if e.strip()],
                        })
                        save_courses(courses)
                        st.success(f"✅ Curso '{n_name}' adicionado!")
                        st.rerun()
                else:
                    st.error("Preencha ID, Nome e URL.")

        st.markdown("---")
        st.markdown(f"**{len(courses)} cursos cadastrados**")

        for ci, course in enumerate(courses):
            with st.expander(f"🎓 {course['name']} ({course['level']})"):
                cc1, cc2 = st.columns(2)
                with cc1:
                    e_name     = st.text_input("Nome", value=course["name"], key=f"c_name_{ci}")
                    e_level    = st.selectbox("Grau", ["Bacharelado","Tecnólogo","Licenciatura"],
                                              index=["Bacharelado","Tecnólogo","Licenciatura"].index(course.get("level","Bacharelado")),
                                              key=f"c_level_{ci}")
                    e_duration = st.text_input("Duração", value=course["duration"], key=f"c_dur_{ci}")
                    e_turno    = st.selectbox("Turno", ["Noturno","Matutino","Integral","Vespertino"],
                                              index=["Noturno","Matutino","Integral","Vespertino"].index(course.get("turno","Noturno")) if course.get("turno") in ["Noturno","Matutino","Integral","Vespertino"] else 0,
                                              key=f"c_turno_{ci}")
                with cc2:
                    e_url     = st.text_input("URL", value=course["url"], key=f"c_url_{ci}")
                    e_summary = st.text_area("Resumo", value=course["summary"], key=f"c_sum_{ci}", height=100)

                e_tags  = st.text_input("Tags", value=", ".join(course.get("tags",[])),  key=f"c_tags_{ci}")
                e_areas = st.text_input("Áreas", value=", ".join(course.get("areas",[])), key=f"c_areas_{ci}")
                e_ev    = st.text_input("Destaques", value=", ".join(course.get("evidence",[])), key=f"c_ev_{ci}")

                col_s, col_d = st.columns([3,1])
                with col_s:
                    if st.button("💾 Salvar curso", key=f"save_c_{ci}"):
                        courses[ci] = {
                            "id":       course["id"],
                            "name":     e_name, "level": e_level,
                            "duration": e_duration, "turno": e_turno,
                            "url":      e_url, "summary": e_summary,
                            "tags":     [t.strip() for t in e_tags.split(",") if t.strip()],
                            "areas":    [a.strip() for a in e_areas.split(",") if a.strip()],
                            "evidence": [e.strip() for e in e_ev.split(",") if e.strip()],
                        }
                        save_courses(courses)
                        st.success("✅ Curso salvo!")
                        st.rerun()
                with col_d:
                    if st.button("🗑️ Excluir", key=f"del_c_{ci}"):
                        courses.pop(ci)
                        save_courses(courses)
                        st.success("✅ Curso excluído!")
                        st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — APARÊNCIA E TEXTOS
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### 🎨 Aparência e Textos da Interface")

        st.markdown("#### 📝 Textos principais")
        cfg["app_title"]    = st.text_input("Título do app", value=cfg["app_title"])
        cfg["app_subtitle"] = st.text_input("Subtítulo", value=cfg["app_subtitle"])
        cfg["hero_text"]    = st.text_area("Texto de boas-vindas", value=cfg["hero_text"], height=80)
        cfg["cta_quiz"]     = st.text_input("Botão 'Fazer quiz'", value=cfg["cta_quiz"])
        cfg["cta_cursos"]   = st.text_input("Botão 'Ver cursos'", value=cfg["cta_cursos"])
        cfg["mensagem_sucesso"] = st.text_input("Mensagem após salvar lead", value=cfg["mensagem_sucesso"])
        cfg["rodape"]       = st.text_input("Texto do rodapé da mensagem", value=cfg["rodape"])

        st.markdown("#### 🎨 Cores")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            cfg["cor_primaria"] = st.color_picker("Cor primária (botões)", value=cfg.get("cor_primaria","#c41060"))
        with c2:
            cfg["cor_fundo"]    = st.color_picker("Cor de fundo", value=cfg.get("cor_fundo","#1a0010"))
        with c3:
            cfg["cor_destaque"] = st.color_picker("Cor destaque (textos)", value=cfg.get("cor_destaque","#ff9ecf"))
        with c4:
            cfg["cor_gold"]     = st.color_picker("Cor dourada", value=cfg.get("cor_gold","#D4A017"))

        # Preview
        st.markdown("#### 👁️ Preview das cores")
        st.markdown(
            f'<div style="background:{cfg["cor_fundo"]};padding:1.5rem;border-radius:16px;margin:.5rem 0">'
            f'<h3 style="color:{cfg["cor_destaque"]};margin:0">{cfg["app_title"]}</h3>'
            f'<p style="color:#e0c0d0">{cfg["hero_text"][:80]}...</p>'
            f'<div style="display:inline-block;background:{cfg["cor_primaria"]};color:white;padding:.4rem 1rem;border-radius:10px;margin-top:.5rem">{cfg["cta_quiz"]}</div>'
            f'<span style="color:{cfg["cor_gold"]};margin-left:1rem">● Cor dourada</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.button("💾 Salvar aparência e textos", type="primary", key="save_appearance"):
            save_config(cfg)
            st.success("✅ Aparência e textos salvos! Reinicie o app para aplicar.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — CONFIGURAÇÕES
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("### ⚙️ Configurações do Sistema")

        st.markdown("#### 🔐 Senhas")
        cfg["admin_password"] = st.text_input("Senha do painel Admin (altera o acesso ao Admin)", value=cfg["admin_password"], type="password")
        st.caption("A senha Super Admin é definida via variável de ambiente `DUZZI_SUPER_PASSWORD`.")

        st.markdown("#### 🎯 Comportamento do quiz")
        cfg["max_results"]  = st.slider("Número de cursos no ranking", min_value=1, max_value=8, value=int(cfg.get("max_results", 3)))
        cfg["mostrar_inep"] = st.toggle("Mostrar dados INEP nas recomendações", value=bool(cfg.get("mostrar_inep", True)))
        cfg["mostrar_qr"]   = st.toggle("Mostrar QR Code de inscrição", value=bool(cfg.get("mostrar_qr", True)))

        st.markdown("#### 📊 Dados e scraping")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("🌐 Atualizar cursos (site Donaduzzi)", use_container_width=True):
                from scraper import scrape_donaduzzi
                log_msgs = []
                with st.spinner("Raspando site..."):
                    courses = scrape_donaduzzi(log_fn=log_msgs.append)
                    save_courses(courses)
                st.success(f"✅ {len(courses)} cursos atualizados!")
                with st.expander("Log"):
                    st.code("\n".join(log_msgs))
        with col_s2:
            if st.button("🏛️ Atualizar dados INEP", use_container_width=True):
                from scraper import scrape_inep
                import json as _j
                log_msgs = []
                with st.spinner("Baixando INEP (~1 min)..."):
                    inep = scrape_inep(log_fn=log_msgs.append)
                    with open(BASE_DIR / "inep_data.json", "w", encoding="utf-8") as f:
                        _j.dump(inep, f, ensure_ascii=False, indent=2)
                st.success("✅ INEP atualizado!")
                with st.expander("Log"):
                    st.code("\n".join(log_msgs))

        st.markdown("#### 📋 Exportar configurações")
        if st.button("⬇️ Baixar config.json atual"):
            st.download_button(
                "💾 Download config.json",
                data=json.dumps(cfg, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="config.json",
                mime="application/json",
            )

        st.markdown("#### ⚠️ Zona de risco")
        with st.expander("🗑️ Resetar configurações para o padrão"):
            st.warning("Isso apaga todas as personalizações de aparência e textos.")
            if st.button("🔄 Resetar tudo para o padrão", key="reset_config"):
                save_config(DEFAULT_CONFIG)
                st.success("✅ Configurações resetadas!")
                st.rerun()

        st.markdown("---")
        if st.button("💾 Salvar configurações", type="primary", key="save_config_btn"):
            save_config(cfg)
            st.success("✅ Configurações salvas!")
