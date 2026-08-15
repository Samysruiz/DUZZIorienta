"""
course_manager.py — Gerenciador de cursos e pesos do quiz
Detecta novos cursos no site da Donaduzzi e permite cadastro com um clique.
"""

import json
import unicodedata
from pathlib import Path

import streamlit as st

BASE_DIR       = Path(__file__).parent
QUESTIONS_FILE = BASE_DIR / "questions.json"
COURSES_FILE   = BASE_DIR / "courses.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_questions() -> list:
    if QUESTIONS_FILE.exists():
        return json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    return []


def _load_courses() -> list:
    if COURSES_FILE.exists():
        return json.loads(COURSES_FILE.read_text(encoding="utf-8"))
    return []


def _save_questions(questions: list):
    QUESTIONS_FILE.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _save_courses(courses: list):
    COURSES_FILE.write_text(
        json.dumps(courses, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Geração de pesos por palavras-chave ──────────────────────────────────────

def _generate_weights_by_keywords(course_id, course_name, course_description, tags, questions):
    texto = (course_name + " " + course_description + " " + " ".join(tags)).lower()

    CATEGORIAS = {
        "tech_dev":        ["programação","software","sistemas","desenvolvimento","web","mobile","código","api"],
        "dados_ia":        ["dados","inteligência artificial","machine learning","deep learning","estatística","análise","pln","visão computacional","algoritmo"],
        "hardware_iot":    ["robótica","iot","hardware","sensor","arduino","prototipagem","automação","eletrônica"],
        "saude":           ["saúde","farmácia","medicamento","clínica","paciente","hospital","análise clínica","fármaco","bioquímica"],
        "bio_agro":        ["biotecnologia","bioprocesso","biologia","agro","agronegócio","pesquisa","sustentabilidade","química","genética"],
        "negocios":        ["gestão","administração","negócios","empreendedorismo","marketing","financeiro","liderança","estratégia","vendas"],
        "design_criativo": ["design","criação","visual","arte","ux","ui","interface","branding","identidade","ilustração","animação"],
        "comunicacao":     ["comunicação","jornalismo","publicidade","mídia","redes sociais","conteúdo","redação"],
    }

    AFINIDADE_OPCAO = {
        "tech_dev":        ["tecnologia","sistemas","criar aplicativos","programação","web","mobile","código","software"],
        "dados_ia":        ["dados","padrões","inteligência artificial","ia","machine","deep learning","estatística","análise","previsão"],
        "hardware_iot":    ["robótica","iot","protótipo","sensor","hardware","automação","eletrônica"],
        "saude":           ["saúde","laboratório","medicamento","clínica","paciente","bem-estar","farmácia"],
        "bio_agro":        ["biotecnologia","bioprocesso","agro","laboratório","pesquisa","biologia","sustentabilidade"],
        "negocios":        ["negócio","gestão","empresa","liderança","empreendedor","financeiro","marketing","administração","estratégia"],
        "design_criativo": ["design","visual","arte","criação","ux","ui","interface","criativo"],
        "comunicacao":     ["comunicação","conteúdo","mídia","redes","publicidade","marketing digital"],
    }

    scores = {cat: sum(1 for p in palavras if p in texto) for cat, palavras in CATEGORIAS.items()}
    cat_principal = max(scores, key=scores.get)
    cat_valor_max = scores[cat_principal]

    pesos = {}
    for q in questions:
        for i, opt in enumerate(q["options"]):
            label_lower = opt["label"].lower()
            key = f"{q['id']}_{i}"
            peso = 0
            if cat_valor_max > 0:
                matches = sum(1 for p in AFINIDADE_OPCAO.get(cat_principal, []) if p in label_lower)
                if matches >= 2:   peso = 4
                elif matches == 1: peso = 2
            matches_diretos = sum(1 for p in texto.split() if len(p) > 4 and p in label_lower)
            if matches_diretos > 0:
                peso = max(peso, min(matches_diretos * 2, 4))
            pesos[key] = peso
    return pesos


def _apply_weights_to_questions(questions, course_id, weights):
    updated = json.loads(json.dumps(questions))
    for q in updated:
        for i, opt in enumerate(q["options"]):
            key = f"{q['id']}_{i}"
            peso = weights.get(key, 0)
            if peso > 0:
                opt.setdefault("weights", {})[course_id] = peso
            else:
                opt.get("weights", {}).pop(course_id, None)
    return updated


def _remove_course_from_questions(questions, course_id):
    updated = json.loads(json.dumps(questions))
    for q in updated:
        for opt in q["options"]:
            opt.get("weights", {}).pop(course_id, None)
    return updated


# ── Cadastro com um clique ────────────────────────────────────────────────────

def register_course_one_click(course: dict) -> tuple:
    try:
        from scraper import dismiss_pending_course
    except ImportError:
        def dismiss_pending_course(x): pass

    try:
        questions = _load_questions()
        courses   = _load_courses()
        course_id = course["id"]

        if any(c["id"] == course_id for c in courses):
            return False, f"Curso '{course_id}' já existe."

        pesos = _generate_weights_by_keywords(
            course_id,
            course.get("name", course_id),
            course.get("summary", ""),
            course.get("tags", []),
            questions
        )

        course_clean = {k: v for k, v in course.items() if not k.startswith("_")}
        courses.append(course_clean)
        _save_courses(courses)

        updated_q = _apply_weights_to_questions(questions, course_id, pesos)
        _save_questions(updated_q)

        dismiss_pending_course(course_id)

        return True, f"✅ '{course.get('name', course_id)}' cadastrado com pesos gerados!"

    except Exception as e:
        return False, f"Erro: {e}"


# ── Banner de alerta no painel ────────────────────────────────────────────────

def render_new_courses_alert():
    try:
        from scraper import load_pending_courses
    except ImportError:
        return

    pending = load_pending_courses()
    if not pending:
        return

    st.markdown(
        f'<div style="background:linear-gradient(135deg,rgba(200,169,110,0.15),rgba(139,26,42,0.10));'
        f'border:1.5px solid #C8A96E;border-radius:14px;padding:1rem 1.4rem;margin-bottom:1rem">'
        f'<p style="color:#C8A96E;font-weight:700;margin:0 0 .3rem;font-size:1rem">'
        f'🆕 {len(pending)} novo(s) curso(s) detectado(s) no site da Donaduzzi!</p>'
        f'<p style="color:#E8A0A8;font-size:.88rem;margin:0">'
        f'Acesse <b>Configurações → Novos Detectados</b> para cadastrar com um clique.</p>'
        f'</div>',
        unsafe_allow_html=True
    )


# ── Render principal ──────────────────────────────────────────────────────────

def render_course_manager():
    try:
        from scraper import (
            detect_new_courses, load_pending_courses,
            save_new_courses_pending, dismiss_pending_course
        )
        scraper_ok = True
    except ImportError:
        scraper_ok = False
        def load_pending_courses(): return []
        def dismiss_pending_course(x): pass

    questions  = _load_questions()
    courses    = _load_courses()
    course_ids = [c["id"] for c in courses]

    st.markdown("---")
    st.markdown("#### 🎓 Gerenciar Cursos e Pesos do Quiz")

    # Badge de pendentes
    pending_count = len(load_pending_courses())
    tab_label_detected = f"🆕 Novos Detectados{'  🔴' if pending_count > 0 else ''}"

    tab_detected, tab_manual, tab_edit, tab_remove = st.tabs([
        tab_label_detected, "➕ Cadastrar Manual", "✏️ Editar Pesos", "🗑️ Remover"
    ])

    # ══ ABA: NOVOS DETECTADOS ════════════════════════════════════════════════
    with tab_detected:
        st.markdown("Detecta automaticamente cursos novos no site da Faculdade Donaduzzi.")

        c1, c2 = st.columns([1, 2])
        with c1:
            if scraper_ok:
                if st.button("🔍 Verificar site agora", use_container_width=True, key="btn_scan"):
                    with st.spinner("Varrendo o site da Donaduzzi..."):
                        log_msgs = []
                        found = detect_new_courses(log_fn=log_msgs.append)
                        st.session_state["_scan_log"] = log_msgs
                        if found:
                            save_new_courses_pending(found)
                            st.success(f"🆕 {len(found)} novo(s) curso(s) encontrado(s)!")
                        else:
                            st.info("✅ Nenhum curso novo detectado.")
                    st.rerun()
            else:
                st.warning("scraper.py não encontrado.")
        with c2:
            st.markdown(
                '<p style="color:#c0a0b8;font-size:.85rem;margin-top:.5rem">'
                'O sistema varre o site e compara com cursos já cadastrados. '
                'Novos aparecem abaixo para aprovação com um clique.</p>',
                unsafe_allow_html=True
            )

        if "_scan_log" in st.session_state:
            with st.expander("📋 Log da varredura"):
                st.code("\n".join(st.session_state["_scan_log"]))

        st.markdown("---")
        pending = load_pending_courses()

        if not pending:
            st.markdown(
                '<div class="dz-card" style="text-align:center;padding:1.5rem">'
                '<p style="font-size:1.5rem">✅</p>'
                '<p style="color:#60ffb0;margin:0">Nenhum curso novo pendente.</p>'
                '<p style="color:#c0a0b8;font-size:.82rem">Clique em "Verificar site agora" para checar.</p>'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"**{len(pending)} curso(s) aguardando aprovação:**")

            for course in pending:
                cid    = course.get("id", "?")
                cname  = course.get("name", cid)
                curl   = course.get("url", "")
                cdesc  = course.get("summary", "Sem descrição extraída.")
                clevel = course.get("level", "A definir")
                cdur   = course.get("duration", "A definir")
                cturno = course.get("turno", "A definir")

                with st.expander(f"🆕  {cname}  —  `{cid}`", expanded=True):
                    st.markdown(
                        f'<div style="background:rgba(200,169,110,0.08);border-radius:10px;'
                        f'padding:.8rem 1rem;margin-bottom:.8rem">'
                        f'<p style="color:#E8A0A8;margin:0 0 .4rem;font-size:.9rem">{cdesc}</p>'
                        f'<p style="color:#c0a0b8;font-size:.82rem;margin:0">'
                        f'{clevel} · {cdur} · {cturno}<br>'
                        f'🔗 <a href="{curl}" target="_blank" style="color:#C8A96E">{curl}</a>'
                        f'</p></div>',
                        unsafe_allow_html=True
                    )

                    # Edição rápida antes de confirmar
                    e1, e2 = st.columns(2)
                    with e1:
                        course["name"] = st.text_input("Nome", value=cname, key=f"pname_{cid}")
                        course["level"] = st.selectbox(
                            "Grau", ["Bacharelado","Tecnólogo","Licenciatura","A definir"],
                            index=["Bacharelado","Tecnólogo","Licenciatura","A definir"].index(clevel)
                            if clevel in ["Bacharelado","Tecnólogo","Licenciatura","A definir"] else 3,
                            key=f"plevel_{cid}"
                        )
                    with e2:
                        course["duration"] = st.text_input("Duração", value=cdur, key=f"pdur_{cid}")
                        course["turno"] = st.selectbox(
                            "Turno", ["Noturno","Matutino","Integral","A definir"],
                            index=["Noturno","Matutino","Integral","A definir"].index(cturno)
                            if cturno in ["Noturno","Matutino","Integral","A definir"] else 3,
                            key=f"pturno_{cid}"
                        )

                    tags_raw = st.text_input(
                        "Tags (separadas por vírgula)",
                        value=", ".join(course.get("tags", [])),
                        key=f"ptags_{cid}"
                    )
                    course["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]
                    course["summary"] = st.text_area("Descrição", value=cdesc, height=70, key=f"pdesc_{cid}")

                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button(
                            f"✅ Cadastrar agora",
                            use_container_width=True,
                            type="primary",
                            key=f"btn_reg_{cid}"
                        ):
                            ok, msg = register_course_one_click(course)
                            if ok:
                                st.success(msg)
                                st.balloons()
                            else:
                                st.error(msg)
                            st.rerun()
                    with b2:
                        if st.button("🚫 Ignorar", use_container_width=True, key=f"btn_dis_{cid}"):
                            dismiss_pending_course(cid)
                            st.info(f"'{cname}' removido dos pendentes.")
                            st.rerun()

    # ══ ABA: CADASTRAR MANUAL ════════════════════════════════════════════════
    with tab_manual:
        st.markdown("Cadastre um curso manualmente informando os dados.")

        c1, c2 = st.columns(2)
        with c1:
            new_id    = st.text_input("ID (sem espaços, minúsculas)", placeholder="ex: design_grafico", key="nm_id")
            new_name  = st.text_input("Nome completo", placeholder="ex: Design Gráfico", key="nm_name")
            new_level = st.selectbox("Grau", ["Bacharelado","Tecnólogo","Licenciatura"], key="nm_level")
        with c2:
            new_url   = st.text_input("URL da página do curso", placeholder="https://...", key="nm_url")
            new_dur   = st.text_input("Duração", placeholder="ex: 8 semestres", key="nm_dur")
            new_turno = st.selectbox("Turno", ["Noturno","Matutino","Integral"], key="nm_turno")

        new_desc     = st.text_area("Descrição do curso", height=80, key="nm_desc")
        new_tags_raw = st.text_input("Tags (separadas por vírgula)", placeholder="ex: design, visual, ux", key="nm_tags")
        new_tags     = [t.strip() for t in new_tags_raw.split(",") if t.strip()]

        if new_id and new_id in course_ids:
            st.warning(f"⚠️ O curso '{new_id}' já existe.")

        b1, b2 = st.columns(2)
        with b1:
            if st.button(
                "✅ Cadastrar + Gerar Pesos",
                disabled=not (new_id and new_name and new_url),
                use_container_width=True,
                type="primary",
                key="btn_manual_reg"
            ):
                new_course = {
                    "id": new_id, "name": new_name, "level": new_level,
                    "duration": new_dur, "turno": new_turno, "url": new_url,
                    "summary": new_desc, "tags": new_tags, "areas": [], "evidence": [],
                }
                ok, msg = register_course_one_click(new_course)
                if ok:
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)
        with b2:
            if st.button("🔄 Limpar", use_container_width=True, key="btn_clear_nm"):
                for k in ["nm_id","nm_name","nm_url","nm_desc","nm_tags","nm_dur"]:
                    st.session_state.pop(k, None)
                st.rerun()

    # ══ ABA: EDITAR PESOS ════════════════════════════════════════════════════
    with tab_edit:
        if not course_ids:
            st.info("Nenhum curso em courses.json.")
        else:
            sel_cid = st.selectbox(
                "Curso",
                course_ids,
                format_func=lambda x: next((c["name"] for c in courses if c["id"]==x), x),
                key="edit_sel"
            )
            pesos_novos = {}
            for q in questions:
                st.markdown(
                    f'<p style="color:#e0c0d0;font-size:.88rem;margin:.8rem 0 .3rem">'
                    f'<b>{q["id"].upper()}</b>: {q["text"]}</p>',
                    unsafe_allow_html=True
                )
                for i, opt in enumerate(q["options"]):
                    key = f"{q['id']}_{i}"
                    val = opt.get("weights", {}).get(sel_cid, 0)
                    pesos_novos[key] = st.slider(f'"{opt["label"]}"', 0, 5, int(val), key=f"edit_{key}")

            if st.button("💾 Salvar", use_container_width=True, key="btn_save_edit"):
                updated_q = _apply_weights_to_questions(questions, sel_cid, pesos_novos)
                _save_questions(updated_q)
                st.success(f"✅ Pesos de '{sel_cid}' atualizados!")
                st.rerun()

    # ══ ABA: REMOVER ═════════════════════════════════════════════════════════
    with tab_remove:
        st.warning("⚠️ O curso deixará de ser recomendado no quiz. Não apaga do courses.json.")
        if not course_ids:
            st.info("Nenhum curso encontrado.")
        else:
            sel_rm = st.selectbox(
                "Curso",
                course_ids,
                format_func=lambda x: next((c["name"] for c in courses if c["id"]==x), x),
                key="rm_sel"
            )
            if st.button(f"🗑️ Remover '{sel_rm}' do quiz", use_container_width=True, key="btn_rm"):
                updated_q = _remove_course_from_questions(questions, sel_rm)
                _save_questions(updated_q)
                st.success(f"✅ '{sel_rm}' removido do quiz.")
                st.rerun()
