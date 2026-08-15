"""
admin_panel.py — Painel Admin e Super Admin do Duzzi Orienta
Consome database.py (Supabase / SQLite fallback)
"""

import io
import json
import os

import pandas as pd
import streamlit as st

from database import (
    change_password, create_user, delete_lead, get_metrics,
    list_leads, list_users, mark_concluido, mark_descartado,
    mark_inscricao_aberta, supabase_ok, toggle_user, update_lead,
    SETUP_SQL,
)
from login_page import logout, require_role

try:
    from course_manager import render_course_manager, render_new_courses_alert
except ImportError:
    def render_course_manager(): st.info("course_manager.py não encontrado.")
    def render_new_courses_alert(): pass

try:
    from test_mode import render_test_panel
except ImportError:
    def render_test_panel(): st.info("test_mode.py não encontrado.")


def _wa_link(phone: str, msg: str) -> str:
    from urllib.parse import quote
    clean = "".join(c for c in phone if c.isdigit())
    if clean and not clean.startswith("55"): clean = "55" + clean
    return f"https://wa.me/{clean}?text={quote(msg, safe='')}"


def render_admin():
    """Renderiza o painel de admin (role: admin ou superadmin)."""

    role     = st.session_state.get("user_role","admin")
    username = st.session_state.get("username","admin")
    is_super = role == "superadmin"

    # ── Header ────────────────────────────────────────────────────────────────
    col_title, col_logout = st.columns([4,1])
    with col_title:
        icon = "⚙️" if is_super else "🔐"
        st.markdown(f"## {icon} {'Super Admin' if is_super else 'Painel Admin'}")
        st.markdown(f"<p style='color:#c0a0b8'>Logado como <b>{username}</b> ({role})</p>",
                    unsafe_allow_html=True)
    with col_logout:
        st.markdown("")
        if st.button("🚪 Sair", key="btn_header_sair", use_container_width=True):
            logout()

    # ── Alerta de novos cursos ────────────────────────────────────────────────
    render_new_courses_alert()

    # ── Status do banco ───────────────────────────────────────────────────────
    if supabase_ok():
        st.markdown(
            '<div class="dz-inep">🐘 <b>Supabase ativo</b> — dados persistentes e seguros.</div>',
            unsafe_allow_html=True)
    else:
        st.warning(
            "⚠️ Supabase não configurado — usando SQLite local (dados temporários). "
            "Configure SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit Cloud.")

    # ── Abas ──────────────────────────────────────────────────────────────────
    if is_super:
        tab_dash, tab_leads, tab_users, tab_config, tab_test = st.tabs([
            "📊 Dashboard", "👥 Leads", "🔑 Usuários", "⚙️ Configurações", "🧪 Testes"])
    else:
        tab_dash, tab_leads = st.tabs(["📊 Dashboard", "👥 Leads"])

    # ══════════════════════════════════════════════════════════════════════════
    # DASHBOARD
    # ══════════════════════════════════════════════════════════════════════════
    with tab_dash:
        m = get_metrics()

        # KPIs
        k1,k2,k3,k4,k5,k6 = st.columns(6)
        for col,(num,lbl,cls) in zip([k1,k2,k3,k4,k5,k6],[
            (str(m["total"]),          "Total de leads",    ""),
            (str(m["hoje"]),           "Leads hoje",        ""),
            (str(m["abriram_inscricao"]),"Abriram inscrição","green"),
            (str(m["nao_abriram"]),    "Não abriram",       "red"),
            (str(m["concluidos"]),     "Concluídos",        "teal"),
            (m["top_curso"][:14],      "Mais pedido",       ""),
        ]):
            with col:
                st.markdown(
                    f'<div class="dz-metric {cls}">'
                    f'<div class="num">{num}</div>'
                    f'<div class="lbl">{lbl}</div></div>',
                    unsafe_allow_html=True)

        if m["total"] > 0:
            taxa = round(m["abriram_inscricao"] / m["total"] * 100, 1)
            taxa_c = round(m["concluidos"] / m["total"] * 100, 1)
            st.markdown(
                f'<div class="dz-card">'
                f'<b>Taxa de abertura de inscrição:</b> '
                f'<span style="color:#60ffb0;font-size:1.2rem;font-weight:700">{taxa}%</span>'
                f'&nbsp;&nbsp;&nbsp;'
                f'<b>Taxa de conclusão:</b> '
                f'<span style="color:#60e0ff;font-size:1.2rem;font-weight:700">{taxa_c}%</span>'
                f'</div>',
                unsafe_allow_html=True)

        g1, g2 = st.columns(2)
        with g1:
            st.markdown("#### 📈 Leads por dia")
            if m["por_dia"]:
                df_d = pd.DataFrame(list(m["por_dia"].items()),
                                    columns=["Data","Leads"]).sort_values("Data")
                st.line_chart(df_d.set_index("Data"), color="#ff80c0")
        with g2:
            st.markdown("#### 🎓 Por curso")
            if m["cursos_contagem"]:
                df_c = pd.DataFrame(list(m["cursos_contagem"].items()),
                                    columns=["Curso","Leads"]).sort_values("Leads",ascending=False)
                st.bar_chart(df_c.set_index("Curso"), color="#e8557a")

        g3, g4 = st.columns(2)
        with g3:
            st.markdown("#### 🏫 Escolas")
            if m["escolas"]:
                df_e = pd.DataFrame(list(m["escolas"].items()),
                                    columns=["Escola","Alunos"]).sort_values("Alunos",ascending=False)
                st.bar_chart(df_e.set_index("Escola"), color="#c090ff")
            else: st.info("Nenhuma escola ainda.")
        with g4:
            st.markdown("#### 🌍 Cidades")
            if m["cidades"]:
                df_ci = pd.DataFrame(list(m["cidades"].items()),
                                     columns=["Cidade","Alunos"]).sort_values("Alunos",ascending=False)
                st.bar_chart(df_ci.set_index("Cidade"), color="#60ffb0")
            else: st.info("Nenhuma cidade ainda.")

    # ══════════════════════════════════════════════════════════════════════════
    # LEADS
    # ══════════════════════════════════════════════════════════════════════════
    with tab_leads:
        st.markdown("### 👥 Gerenciar Leads")

        # Feedback de ações anteriores
        if "_admin_msg" in st.session_state:
            msg = st.session_state.pop("_admin_msg")
            st.success(msg)

        # CSS fix para selectbox texto visível
        st.markdown("""
        <style>
        [data-baseweb="select"] div,
        [data-baseweb="select"] span,
        [data-baseweb="select"] input,
        [data-baseweb="popover"] li,
        [data-baseweb="menu"] li,
        [role="option"] {
            color: #FFFFFF !important;
            background-color: #3D0A12 !important;
        }
        [data-baseweb="select"] > div {
            background-color: #3D0A12 !important;
            border: 2px solid #8B1A2A !important;
            border-radius: 10px !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Filtros
        fc1,fc2,fc3,fc4 = st.columns(4)
        leads_all = list_leads()
        df_all    = pd.DataFrame(leads_all) if leads_all else pd.DataFrame()

        if df_all.empty:
            st.warning("Nenhum lead cadastrado ainda.")
        else:
            with fc1:
                cursos = ["Todos"] + sorted(df_all["curso_recomendado"].dropna().unique().tolist())
                filtro_curso = st.selectbox("Curso", cursos)
            with fc2:
                cidades = ["Todas"] + sorted(df_all["cidade"].dropna().unique().tolist())
                filtro_cidade = st.selectbox("Cidade", cidades)
            with fc3:
                filtro_status = st.selectbox("Status", ["Todos","Ativo","Concluído","Descartado"])
            with fc4:
                filtro_inscricao = st.selectbox("Inscrição", ["Todos","Abriu","Não abriu"])

            # Aplica filtros
            df_f = df_all.copy()
            if filtro_curso  != "Todos":   df_f = df_f[df_f["curso_recomendado"]==filtro_curso]
            if filtro_cidade != "Todas":   df_f = df_f[df_f["cidade"]==filtro_cidade]
            if filtro_status != "Todos":
                import unicodedata, pandas as _pd
                def _norm(s):
                    if _pd.isna(s) or s is None: s = "Ativo"
                    return unicodedata.normalize("NFD", str(s)).encode("ascii","ignore").decode().lower().strip()
                _target = _norm(filtro_status)
                df_f = df_f[df_f["status"].apply(_norm) == _target]
            if filtro_inscricao == "Abriu":
                df_f = df_f[df_f["abriu_inscricao"].isin([True,1,"true","1","Sim"])]
            elif filtro_inscricao == "Não abriu":
                df_f = df_f[~df_f["abriu_inscricao"].isin([True,1,"true","1","Sim"])]

            st.caption(f"{len(df_f)} de {len(df_all)} leads")

            # Tabela
            cols_show = ["id","nome","telefone","email","escola_origem",
                         "cidade","curso_recomendado","compatibilidade_pct",
                         "abriu_inscricao","status","criado_em"]
            cols_show = [c for c in cols_show if c in df_f.columns]
            df_show = df_f[cols_show].copy()
            rename  = {"id":"ID","nome":"Nome","telefone":"WhatsApp","email":"E-mail",
                       "escola_origem":"Escola","cidade":"Cidade",
                       "curso_recomendado":"Curso","compatibilidade_pct":"Compatib. %",
                       "abriu_inscricao":"Abriu Inscrição","status":"Status",
                       "criado_em":"Data/Hora"}
            df_show.rename(columns={k:v for k,v in rename.items() if k in df_show.columns},
                           inplace=True)
            if "Abriu Inscrição" in df_show.columns:
                df_show["Abriu Inscrição"] = df_show["Abriu Inscrição"]\
                    .map(lambda x: "✅ Sim" if x in (True,1,"true","1","Sim") else "❌ Não")

            st.dataframe(df_show, use_container_width=True, hide_index=True)

            # ── Ações por lead ─────────────────────────────────────────────
            st.markdown("#### 🎯 Ações")
            if not df_f.empty:
                lead_opts = [
                    f"{r.get('nome','?')} — {r.get('telefone','')} [{r.get('status','Ativo')}]"
                    for _, r in df_f.iterrows()
                ]
                sel_opt  = st.selectbox("Selecione o lead", lead_opts, key="lead_sel")
                sel_idx  = lead_opts.index(sel_opt)
                sel_lead = df_f.iloc[sel_idx]
                # Use original column names (before rename)
                _id_col   = "id" if "id" in sel_lead.index else "ID"
                _nome_col = "nome" if "nome" in sel_lead.index else "Nome"
                _tel_col  = "telefone" if "telefone" in sel_lead.index else "WhatsApp"
                _st_col   = "status" if "status" in sel_lead.index else "Status"
                sel_id   = int(sel_lead.get(_id_col, 0) or 0)
                sel_nome = str(sel_lead.get(_nome_col, "?"))
                sel_tel  = str(sel_lead.get(_tel_col, ""))

                ba1,ba2,ba3,ba4,ba5 = st.columns(5)
                with ba1:
                    if st.button("✅ Concluído", key="btn_conc", use_container_width=True):
                        mark_concluido(sel_id)
                        st.session_state["_admin_msg"] = f"✅ {sel_nome} marcado como Concluído!"
                        st.rerun()
                with ba2:
                    if st.button("🗑️ Descartar", key="btn_desc", use_container_width=True):
                        mark_descartado(sel_id)
                        st.session_state["_admin_msg"] = f"🗑️ {sel_nome} descartado."
                        st.rerun()
                with ba3:
                    if is_super:
                        if st.button("❌ Apagar", key="btn_del", use_container_width=True):
                            delete_lead(sel_id)
                            st.session_state["_admin_msg"] = f"🗑️ {sel_nome} apagado permanentemente."
                            st.rerun()
                    else:
                        st.caption("(apagar: superadmin)")
                with ba4:
                    if sel_tel:
                        msg_wa = (f"Ola, {sel_nome}! Aqui e a Faculdade Donaduzzi. "
                                  f"Vi seu resultado no Duzzi Orienta e gostariamos de "
                                  f"te ajudar na inscricao. Podemos conversar?")
                        st.link_button("💬 WhatsApp",
                                       _wa_link(sel_tel, msg_wa),
                                       use_container_width=True)
                with ba5:
                    status_atual = sel_lead.get(_st_col, "Ativo")
                    st.markdown(
                        f'<div class="dz-metric" style="padding:.5rem">'
                        f'<div class="num" style="font-size:.9rem">{status_atual}</div>'
                        f'<div class="lbl">status</div></div>',
                        unsafe_allow_html=True)

            # ── Exportar ───────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("#### ⬇️ Exportar")
            ec1,ec2 = st.columns(2)
            with ec1:
                st.download_button("📊 Baixar CSV",
                    data=df_show.to_csv(index=False).encode("utf-8"),
                    file_name="duzzi_leads.csv", mime="text/csv",
                    use_container_width=True)
            with ec2:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df_show.to_excel(writer, index=False, sheet_name="Leads")
                    m = get_metrics()
                    pd.DataFrame([
                        ["Total", m["total"]],
                        ["Hoje",  m["hoje"]],
                        ["Abriram inscrição", m["abriram_inscricao"]],
                        ["Não abriram", m["nao_abriram"]],
                        ["Concluídos", m["concluidos"]],
                        ["Taxa abertura %", round(m["abriram_inscricao"]/max(m["total"],1)*100,1)],
                        ["Curso mais pedido", m["top_curso"]],
                    ], columns=["Métrica","Valor"]).to_excel(
                        writer, index=False, sheet_name="Métricas")
                st.download_button("📗 Baixar Excel",
                    data=buf.getvalue(), file_name="duzzi_leads.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # USUÁRIOS (só superadmin)
    # ══════════════════════════════════════════════════════════════════════════
    if is_super:
        with tab_users:
            st.markdown("### 🔑 Gerenciar Usuários")

            # Listar
            users = list_users()
            if users:
                df_u = pd.DataFrame(users)[["id","username","role","ativo","criado_em"]]
                df_u.columns = ["ID","Usuário","Perfil","Ativo","Criado em"]
                df_u["Ativo"] = df_u["Ativo"].map({True:"✅ Sim", False:"❌ Não"})
                st.dataframe(df_u, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum usuário cadastrado no Supabase (usando variáveis de ambiente).")

            st.markdown("---")

            # Criar usuário
            with st.expander("➕ Criar novo usuário"):
                nu1,nu2 = st.columns(2)
                with nu1:
                    new_user = st.text_input("Usuário", key="new_username",
                                             placeholder="Ex: ana.silva")
                    new_role = st.selectbox("Perfil", ["admin","superadmin"], key="new_role")
                with nu2:
                    new_pass = st.text_input("Senha", type="password", key="new_pass")
                    new_pass2 = st.text_input("Confirmar senha", type="password", key="new_pass2")
                if st.button("✅ Criar usuário", key="btn_create_user"):
                    if not new_user or not new_pass:
                        st.error("Preencha usuário e senha.")
                    elif new_pass != new_pass2:
                        st.error("As senhas não coincidem.")
                    elif create_user(new_user, new_pass, new_role):
                        st.success(f"Usuário '{new_user}' criado com perfil {new_role}!")
                        st.rerun()
                    else:
                        st.error("Erro ao criar usuário. Verifique se o Supabase está configurado.")

            # Ações em usuários existentes
            if users:
                with st.expander("✏️ Ações em usuário existente"):
                    user_opts = [f"{u['username']} ({u['role']})" for u in users]
                    sel_u     = st.selectbox("Usuário", user_opts, key="sel_user")
                    sel_uid   = users[user_opts.index(sel_u)]["id"]
                    sel_uname = users[user_opts.index(sel_u)]["username"]
                    sel_ativo = users[user_opts.index(sel_u)]["ativo"]

                    ua1,ua2,ua3 = st.columns(3)
                    with ua1:
                        lbl = "🔴 Desativar" if sel_ativo else "🟢 Ativar"
                        if st.button(lbl, key="btn_toggle_user", use_container_width=True):
                            toggle_user(sel_uid, not sel_ativo)
                            st.success(f"Usuário {sel_uname} atualizado!"); st.rerun()
                    with ua2:
                        new_pwd_change = st.text_input("Nova senha", type="password",
                                                        key="pwd_change")
                    with ua3:
                        st.markdown("")
                        st.markdown("")
                        if st.button("🔑 Alterar senha", key="btn_change_pwd",
                                     use_container_width=True):
                            if new_pwd_change and change_password(sel_uid, new_pwd_change):
                                st.success("Senha alterada!")
                            else:
                                st.error("Erro ao alterar senha.")

        # ══════════════════════════════════════════════════════════════════════
        # CONFIGURAÇÕES (só superadmin)
        # ══════════════════════════════════════════════════════════════════════
        with tab_config:
            st.markdown("### ⚙️ Configurações do Sistema")

            st.markdown("#### 🐘 Supabase")
            if supabase_ok():
                st.success("✅ Supabase configurado e funcionando!")
                url = os.getenv("SUPABASE_URL","")
                st.code(f"URL: {url[:40]}...")
            else:
                st.error("❌ Supabase não configurado.")
                st.markdown("""
**Para configurar, adicione nos Secrets do Streamlit Cloud:**
```toml
SUPABASE_URL  = "https://xxxx.supabase.co"
SUPABASE_KEY  = "sua_anon_key"
DUZZI_ADMIN_PASSWORD = "sua_senha_admin"
DUZZI_SUPER_PASSWORD = "sua_senha_superadmin"
```
                """)

            st.markdown("---")
            st.markdown("#### 🐙 GitHub (commit automático)")
            from github_sync import github_configured as _gh_ok
            if _gh_ok():
                st.success(f"✅ GitHub configurado! Repositório: {os.getenv('GITHUB_REPO','')}")
            else:
                st.error("❌ GITHUB_TOKEN / GITHUB_REPO não configurados.")
                st.markdown("""
**Para o commit automático funcionar, adicione nos Secrets do Streamlit Cloud:**
```toml
GITHUB_TOKEN  = "ghp_xxxxxxxxxxxxxxxxxxxx"
GITHUB_REPO   = "seu-usuario/seu-repositorio"
```
O token precisa ser um **Personal Access Token (fine-grained)** com permissão de **leitura e escrita em "Contents"** apenas para este repositório.
                """)

            st.markdown("---")
            st.markdown("#### 🗃️ SQL para criação das tabelas")
            st.markdown("Cole isso no **SQL Editor** do Supabase e clique em **Run**:")
            st.code(SETUP_SQL, language="sql")

            st.markdown("---")
            st.markdown("#### 🔄 Atualizar dados")
            sc1,sc2 = st.columns(2)
            with sc1:
                if st.button("🌐 Atualizar cursos (site Donaduzzi)", key="btn_scrape_cursos", use_container_width=True):
                    try:
                        from scraper import scrape_donaduzzi
                        import json as _j
                        from pathlib import Path
                        from datetime import datetime

                        log_msgs = []
                        p = Path(__file__).parent / "courses.json"
                        log_p = Path(__file__).parent / "scrape_log.json"

                        # Snapshot de como estava ANTES de atualizar
                        cursos_antes = {}
                        if p.exists():
                            try:
                                cursos_antes = {c["id"]: c["name"] for c in _j.loads(p.read_text(encoding="utf-8"))}
                            except Exception:
                                cursos_antes = {}

                        with st.spinner("Raspando site..."):
                            courses = scrape_donaduzzi(log_fn=log_msgs.append)
                            p.write_text(_j.dumps(courses, ensure_ascii=False, indent=2))

                        cursos_depois = {c["id"]: c["name"] for c in courses}
                        novos        = [cursos_depois[cid] for cid in cursos_depois if cid not in cursos_antes]
                        descontinuados = [cursos_antes[cid] for cid in cursos_antes if cid not in cursos_depois]
                        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

                        # Guarda histórico de atualizações
                        historico = []
                        if log_p.exists():
                            try:
                                historico = _j.loads(log_p.read_text(encoding="utf-8"))
                            except Exception:
                                historico = []
                        historico.append({
                            "data": agora,
                            "total_cursos": len(courses),
                            "novos": novos,
                            "descontinuados": descontinuados,
                        })
                        log_p.write_text(_j.dumps(historico, ensure_ascii=False, indent=2))

                        # Guarda no session_state pra sobreviver ao clique do botão de confirmação
                        st.session_state["scrape_cursos_resultado"] = {
                            "courses": courses,
                            "novos": novos,
                            "descontinuados": descontinuados,
                            "agora": agora,
                            "log_msgs": log_msgs,
                            "historico": historico,
                            "github_done": False,
                        }
                    except Exception as e:
                        st.error(f"Erro: {e}")

                # ── Mostra o resultado da última raspagem (persiste entre cliques) ──
                resultado = st.session_state.get("scrape_cursos_resultado")
                if resultado:
                    import json as _j
                    st.success(f"✅ {len(resultado['courses'])} cursos atualizados! · Atualizado em {resultado['agora']}")

                    for nome in resultado["novos"]:
                        st.info(f"🆕 Novo curso detectado: **{nome}**")
                    for nome in resultado["descontinuados"]:
                        st.warning(f"❌ Curso descontinuado: **{nome}**")
                    if not resultado["novos"] and not resultado["descontinuados"]:
                        st.caption("Nenhuma mudança na grade de cursos desde a última atualização.")

                    with st.expander("📋 Cursos atualmente no site"):
                        for c in resultado["courses"]:
                            st.markdown(f"- {c['name']}")
                        if resultado["descontinuados"]:
                            st.markdown("---")
                            st.markdown("**Removido nesta atualização:**")
                            for nome in resultado["descontinuados"]:
                                st.markdown(f"- ~~{nome}~~ 🔻 descontinuado")

                    with st.expander("Log técnico"):
                        st.code("\n".join(resultado["log_msgs"]))

                    if resultado["github_done"]:
                        st.success("✅ Já está atualizado no GitHub também.")
                    else:
                        st.markdown("**Deseja atualizar isso direto no GitHub também?**")
                        colg1, colg2 = st.columns(2)
                        with colg1:
                            if st.button("✅ Sim, atualizar no GitHub", key="btn_confirma_github_cursos", use_container_width=True):
                                from github_sync import commit_file_to_github, github_configured
                                if not github_configured():
                                    st.error(
                                        "❌ GITHUB_TOKEN / GITHUB_REPO não configurados. "
                                        "Adicione nos Secrets do Streamlit Cloud:\n\n"
                                        "GITHUB_TOKEN = \"ghp_xxxxx\"\nGITHUB_REPO = \"seu-usuario/seu-repositorio\""
                                    )
                                else:
                                    resumo_msg = f"Atualização automática de cursos — {resultado['agora']}"
                                    if resultado["novos"]: resumo_msg += f" | novo: {', '.join(resultado['novos'])}"
                                    if resultado["descontinuados"]: resumo_msg += f" | descontinuado: {', '.join(resultado['descontinuados'])}"
                                    with st.spinner("Comitando courses.json no GitHub..."):
                                        res = commit_file_to_github(
                                            "courses.json",
                                            _j.dumps(resultado["courses"], ensure_ascii=False, indent=2),
                                            resumo_msg,
                                        )
                                    if res["ok"]:
                                        with st.spinner("Comitando histórico (scrape_log.json) no GitHub..."):
                                            res_log = commit_file_to_github(
                                                "scrape_log.json",
                                                _j.dumps(resultado["historico"], ensure_ascii=False, indent=2),
                                                f"Histórico de atualização de cursos — {resultado['agora']}",
                                            )
                                        st.session_state["scrape_cursos_resultado"]["github_done"] = True
                                        st.success(f"✅ Commit feito direto no GitHub! [Ver commit]({res['url']})")
                                        if not res_log["ok"]:
                                            st.caption(f"(scrape_log.json não foi comitado: {res_log['error']})")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Não consegui comitar no GitHub: {res['error']}")
                        with colg2:
                            st.download_button(
                                "⬇️ Não, só baixar o arquivo",
                                data=_j.dumps(resultado["courses"], ensure_ascii=False, indent=2),
                                file_name="courses.json",
                                mime="application/json",
                                key="dl_courses_json",
                                use_container_width=True,
                            )
                        st.error(f"Erro: {e}")
            with sc2:
                git_auto_inep = st.checkbox(
                    "📤 Comitar inep_data.json direto no GitHub após atualizar (requer GITHUB_TOKEN nos Secrets)",
                    key="chk_git_auto_inep",
                )
                if st.button("🏛️ Atualizar INEP", key="btn_scrape_inep", use_container_width=True):
                    try:
                        from scraper import scrape_inep
                        import json as _j
                        from pathlib import Path
                        from datetime import datetime
                        log_msgs = []
                        with st.spinner("Baixando INEP (~1 min)..."):
                            inep = scrape_inep(log_fn=log_msgs.append)
                            p = Path(__file__).parent / "inep_data.json"
                            p.write_text(_j.dumps(inep, ensure_ascii=False, indent=2))
                        agora_inep = datetime.now().strftime("%d/%m/%Y às %H:%M")
                        st.success(f"✅ INEP atualizado! · Atualizado em {agora_inep}")
                        with st.expander("Log"): st.code("\n".join(log_msgs))

                        st.download_button(
                            "⬇️ Baixar inep_data.json atualizado (subir no GitHub p/ tornar permanente)",
                            data=_j.dumps(inep, ensure_ascii=False, indent=2),
                            file_name="inep_data.json",
                            mime="application/json",
                            key="dl_inep_json",
                        )

                        if git_auto_inep:
                            from github_sync import commit_file_to_github, github_configured
                            if not github_configured():
                                st.error(
                                    "❌ GITHUB_TOKEN / GITHUB_REPO não configurados. "
                                    "Adicione nos Secrets do Streamlit Cloud:\n\n"
                                    "GITHUB_TOKEN = \"ghp_xxxxx\"\nGITHUB_REPO = \"seu-usuario/seu-repositorio\""
                                )
                            else:
                                with st.spinner("Comitando inep_data.json no GitHub..."):
                                    res = commit_file_to_github(
                                        "inep_data.json",
                                        _j.dumps(inep, ensure_ascii=False, indent=2),
                                        f"Atualização automática de dados INEP — {agora_inep}",
                                    )
                                if res["ok"]:
                                    st.success(f"✅ Commit feito direto no GitHub! [Ver commit]({res['url']})")
                                else:
                                    st.error(f"❌ Não consegui comitar no GitHub: {res['error']}")
                    except Exception as e:
                        st.error(f"Erro: {e}")

            if is_super:
                try:
                    from superadmin import render as super_render
                    st.markdown("---")
                    st.markdown("#### 🎨 Aparência e Perguntas")
                    super_render()
                except ImportError:
                    pass

            # ── Gerenciador de cursos e pesos ──────────────────────────────
            render_course_manager()

            # ── LGPD ───────────────────────────────────────────────────────
            try:
                from lgpd import render_lgpd_admin
                render_lgpd_admin()
            except ImportError:
                pass

        # ══════════════════════════════════════════════════════════════════
        # TESTES (só superadmin)
        # ══════════════════════════════════════════════════════════════════
        with tab_test:
            st.markdown("### 🧪 Modo Teste")
            st.markdown(
                '<p style="color:#c0a0b8;font-size:.88rem">'
                'Teste a experiência completa do aluno ou do admin sem afetar dados reais. '
                'Os registros ficam isolados nesta aba e são invisíveis para alunos e admins comuns.</p>',
                unsafe_allow_html=True
            )
            render_test_panel()
