"""
lgpd.py — Conformidade LGPD para o Duzzi Orienta
Implements: consentimento, direitos do titular, retenção e exclusão de dados.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent

# ── Configurações de retenção ─────────────────────────────────────────────────
RETENTION_DAYS = 365  # 1 ano


# ── Tela de Consentimento ─────────────────────────────────────────────────────

def render_consent_screen() -> bool:
    """
    Exibe tela de consentimento LGPD antes do quiz.
    Retorna True se o usuário consentiu, False caso contrário.
    """
    st.markdown(
        '<div style="background:linear-gradient(135deg,rgba(139,26,42,0.15),rgba(45,10,16,0.4));'
        'border:1.5px solid rgba(232,160,168,0.3);border-radius:20px;padding:1.8rem 2rem;'
        'max-width:680px;margin:0 auto">'

        '<div style="text-align:center;margin-bottom:1.2rem">'
        '<div style="font-size:2.2rem">🔒</div>'
        '<h3 style="margin:.4rem 0;color:#ffd6ec">Antes de começar</h3>'
        '<p style="color:#c0a0b8;font-size:.9rem;margin:0">'
        'Precisamos do seu consentimento para prosseguir, conforme a LGPD (Lei nº 13.709/2018).</p>'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div style="background:rgba(0,0,0,0.2);border-radius:12px;padding:1rem 1.2rem;'
        'margin-bottom:1rem">'
        '<p style="color:#e0c0d0;font-weight:600;margin:0 0 .6rem;font-size:.9rem">'
        '📋 Quais dados serão coletados?</p>'
        '<ul style="color:#c0a0b8;font-size:.85rem;margin:0;padding-left:1.2rem;line-height:1.8">'
        '<li><b style="color:#e0c0d0">Nome completo</b> — para personalizar sua recomendação</li>'
        '<li><b style="color:#e0c0d0">WhatsApp</b> — para enviar seu resultado e entrar em contato</li>'
        '<li><b style="color:#e0c0d0">E-mail</b> — opcional, para comunicações adicionais</li>'
        '<li><b style="color:#e0c0d0">Cidade e escola</b> — para contextualizar seu perfil</li>'
        '<li><b style="color:#e0c0d0">Respostas do quiz</b> — para gerar sua recomendação de curso</li>'
        '</ul>'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div style="background:rgba(0,0,0,0.2);border-radius:12px;padding:1rem 1.2rem;'
        'margin-bottom:1rem">'
        '<p style="color:#e0c0d0;font-weight:600;margin:0 0 .6rem;font-size:.9rem">'
        '🎯 Para que serão usados?</p>'
        '<ul style="color:#c0a0b8;font-size:.85rem;margin:0;padding-left:1.2rem;line-height:1.8">'
        '<li>Gerar recomendação personalizada de curso</li>'
        '<li>Contato da equipe da Faculdade Donaduzzi sobre inscrições</li>'
        '<li>Análise interna de perfil de candidatos (uso institucional)</li>'
        '</ul>'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div style="background:rgba(0,0,0,0.2);border-radius:12px;padding:1rem 1.2rem;'
        'margin-bottom:1rem">'
        '<p style="color:#e0c0d0;font-weight:600;margin:0 0 .6rem;font-size:.9rem">'
        '🏛️ Quem trata os dados?</p>'
        '<p style="color:#c0a0b8;font-size:.85rem;margin:0;line-height:1.7">'
        '<b style="color:#e0c0d0">Controlador:</b> Faculdade Donaduzzi / Associação de Ensino, '
        'Pesquisa e Extensão Biopark — CNPJ 30.694.272/0001-08<br>'
        '<b style="color:#e0c0d0">Contato DPO:</b> juridico@biopark.com.br<br>'
        '<b style="color:#e0c0d0">Onde ficam armazenados:</b> Supabase (PostgreSQL) e/ou '
        'Google Sheets — servidores com criptografia em repouso<br>'
        '<b style="color:#e0c0d0">Por quanto tempo:</b> até 12 meses após o cadastro, '
        'ou até a revogação do consentimento</p>'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div style="background:rgba(0,0,0,0.2);border-radius:12px;padding:1rem 1.2rem;'
        'margin-bottom:1.2rem">'
        '<p style="color:#e0c0d0;font-weight:600;margin:0 0 .6rem;font-size:.9rem">'
        '✅ Seus direitos (Art. 18 LGPD)</p>'
        '<p style="color:#c0a0b8;font-size:.85rem;margin:0;line-height:1.7">'
        'Você pode a qualquer momento: acessar seus dados, corrigir informações incorretas, '
        'solicitar a exclusão dos seus dados ou revogar este consentimento. '
        'Use o menu <b style="color:#e0c0d0">Meus Dados</b> no quiz para exercer esses direitos.'
        '</p>'
        '</div>',
        unsafe_allow_html=True
    )

    consentiu = st.checkbox(
        "Li e concordo com o tratamento dos meus dados pessoais conforme descrito acima, "
        "com base no Art. 7º, inciso I da LGPD (consentimento).",
        key="lgpd_consent_check"
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "✅ Concordo e quero continuar",
            disabled=not consentiu,
            use_container_width=True,
            type="primary",
            key="btn_consent_ok"
        ):
            st.session_state["lgpd_consented"] = True
            st.session_state["lgpd_consent_date"] = datetime.now().isoformat()
            st.rerun()
    with c2:
        if st.button(
            "❌ Não concordo",
            use_container_width=True,
            key="btn_consent_no"
        ):
            st.session_state["lgpd_consented"] = False
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    return False


def render_consent_refused():
    """Tela para quem não consentiu."""
    st.markdown(
        '<div style="text-align:center;padding:2rem">'
        '<div style="font-size:3rem">🔒</div>'
        '<h3 style="color:#ffd6ec">Consentimento não fornecido</h3>'
        '<p style="color:#c0a0b8">Sem consentimento não é possível prosseguir com o quiz, '
        'pois precisamos armazenar suas respostas para gerar a recomendação.<br><br>'
        'Você pode explorar os cursos disponíveis sem fornecer dados pessoais.</p>'
        '</div>',
        unsafe_allow_html=True
    )
    if st.button("📚 Ver cursos sem fornecer dados", use_container_width=True):
        st.session_state.page = "Cursos"
        st.rerun()
    if st.button("↩️ Voltar e reconsiderar", use_container_width=True):
        for k in ["lgpd_consented", "lgpd_consent_check"]:
            st.session_state.pop(k, None)
        st.rerun()


# ── Interface de Direitos do Titular ─────────────────────────────────────────

def render_titular_rights(telefone: str = ""):
    """
    Interface para exercício dos direitos do titular (Art. 18 LGPD).
    Integrada ao quiz após o usuário preencher o telefone.
    """
    with st.expander("🔒 Meus Dados — Direitos LGPD (Art. 18)", expanded=False):
        st.markdown(
            '<p style="color:#c0a0b8;font-size:.85rem;margin-bottom:1rem">'
            'Como titular de dados, você pode exercer os seguintes direitos a qualquer momento:</p>',
            unsafe_allow_html=True
        )

        tab_access, tab_delete, tab_revoke = st.tabs([
            "👁️ Acessar meus dados",
            "🗑️ Solicitar exclusão",
            "↩️ Revogar consentimento"
        ])

        with tab_access:
            st.markdown(
                '<p style="color:#c0a0b8;font-size:.85rem">'
                'Para acessar os dados registrados com seu número de WhatsApp, '
                'entre em contato com a Faculdade Donaduzzi:</p>',
                unsafe_allow_html=True
            )
            tel_display = telefone if telefone else "seu número de WhatsApp"
            st.markdown(
                f'<div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:.8rem 1rem">'
                f'<p style="color:#e0c0d0;margin:0;font-size:.88rem">'
                f'📧 <b>E-mail DPO:</b> juridico@biopark.com.br<br>'
                f'📱 <b>WhatsApp institucional:</b> (45) 99114-8284<br>'
                f'🔍 <b>Identifique-se com:</b> {tel_display}</p>'
                f'</div>',
                unsafe_allow_html=True
            )

        with tab_delete:
            st.warning("A exclusão removerá permanentemente todos os seus dados do sistema.")
            motivo = st.text_area(
                "Motivo da solicitação (opcional)",
                placeholder="Ex: não tenho mais interesse no processo seletivo",
                height=70,
                key="lgpd_delete_motivo"
            )
            if st.button("🗑️ Solicitar exclusão dos meus dados", use_container_width=True, key="btn_lgpd_delete"):
                _send_deletion_request(telefone, motivo)
                st.success(
                    "✅ Solicitação enviada! A Faculdade Donaduzzi tem até 15 dias úteis "
                    "para confirmar a exclusão, conforme Art. 18, §3º da LGPD."
                )

        with tab_revoke:
            st.markdown(
                '<p style="color:#c0a0b8;font-size:.85rem">'
                'Ao revogar o consentimento, seus dados serão marcados para exclusão '
                'e o sistema não utilizará mais suas informações.</p>',
                unsafe_allow_html=True
            )
            if st.button("↩️ Revogar meu consentimento", use_container_width=True, key="btn_lgpd_revoke"):
                st.session_state["lgpd_consented"] = False
                st.session_state.pop("lgpd_consent_date", None)
                _send_deletion_request(telefone, "Revogação de consentimento")
                st.success("✅ Consentimento revogado. Seus dados serão excluídos em até 15 dias úteis.")
                st.rerun()


def _send_deletion_request(telefone: str, motivo: str):
    """Registra solicitação de exclusão localmente e/ou no banco."""
    request = {
        "telefone": telefone,
        "motivo": motivo or "Não informado",
        "data_solicitacao": datetime.now().isoformat(),
        "status": "pendente",
    }

    # Salva em arquivo local como fallback
    requests_file = BASE_DIR / "lgpd_requests.json"
    try:
        existing = json.loads(requests_file.read_text(encoding="utf-8")) if requests_file.exists() else []
        existing.append(request)
        requests_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    # Tenta excluir diretamente do banco se tiver telefone
    if telefone:
        try:
            from database import list_leads, delete_lead
            leads = list_leads()
            digits = "".join(c for c in telefone if c.isdigit())
            for lead in leads:
                lead_tel = "".join(c for c in str(lead.get("telefone","")) if c.isdigit())
                if lead_tel and lead_tel in digits or digits in lead_tel:
                    delete_lead(lead["id"])
        except Exception:
            pass


# ── Política de Retenção e Exclusão Automática ────────────────────────────────

def apply_retention_policy(log_fn=None):
    """
    Exclui automaticamente leads com mais de RETENTION_DAYS dias.
    Chamada pelo superadmin no painel de configurações.
    """
    try:
        from database import list_leads, delete_lead
    except ImportError:
        if log_fn: log_fn("⚠️ database.py não encontrado.")
        return 0

    cutoff = (date.today() - timedelta(days=RETENTION_DAYS)).isoformat()
    leads  = list_leads()
    deleted = 0

    for lead in leads:
        criado = str(lead.get("criado_em",""))[:10]
        if criado and criado < cutoff:
            try:
                delete_lead(lead["id"])
                deleted += 1
                if log_fn: log_fn(f"  🗑️ Lead #{lead['id']} ({lead.get('nome','?')}) excluído — data: {criado}")
            except Exception as e:
                if log_fn: log_fn(f"  ⚠️ Erro ao excluir lead #{lead['id']}: {e}")

    msg = f"✅ Política de retenção aplicada: {deleted} lead(s) excluído(s) (>{RETENTION_DAYS} dias)."
    if log_fn: log_fn(msg)
    return deleted


def load_deletion_requests() -> list:
    """Carrega solicitações de exclusão pendentes."""
    requests_file = BASE_DIR / "lgpd_requests.json"
    if requests_file.exists():
        try:
            return json.loads(requests_file.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


# ── Registro de Atividades de Tratamento (Art. 37) ───────────────────────────

REGISTRO_ATIVIDADES = {
    "controlador": "Associação de Ensino, Pesquisa e Extensão Biopark (Faculdade Donaduzzi)",
    "cnpj": "30.694.272/0001-08",
    "dpo_contato": "juridico@biopark.com.br",
    "ultima_atualizacao": "2025-01-01",
    "atividades": [
        {
            "nome": "Orientação vocacional — Quiz Duzzi Orienta",
            "finalidade": "Recomendar cursos de graduação com base no perfil do candidato",
            "base_legal": "Consentimento do titular (Art. 7º, I, LGPD)",
            "dados_coletados": ["nome completo","telefone (WhatsApp)","e-mail (opcional)","cidade","estado","escola de origem","respostas do quiz"],
            "dados_sensiveis": "Não",
            "destinatarios": ["Banco Supabase (PostgreSQL) — servidores AWS","Google Sheets (opcional) — Google LLC","Painel administrativo interno da Faculdade Donaduzzi"],
            "transferencia_internacional": "Sim — Google LLC (EUA), mediante cláusulas contratuais padrão",
            "prazo_retencao": "12 meses a partir da data de cadastro",
            "medidas_segurança": ["Autenticação por usuário e senha no painel","Controle de acesso por perfil (admin/superadmin)","Criptografia em repouso no Supabase","HTTPS em todas as comunicações"],
        },
        {
            "nome": "Gestão de leads — Painel Administrativo",
            "finalidade": "Acompanhamento e conversão de candidatos interessados",
            "base_legal": "Interesse legítimo do controlador (Art. 7º, IX, LGPD)",
            "dados_coletados": ["nome","telefone","e-mail","curso recomendado","status de inscrição"],
            "dados_sensiveis": "Não",
            "destinatarios": ["Usuários internos com perfil admin ou superadmin"],
            "transferencia_internacional": "Não",
            "prazo_retencao": "12 meses",
            "medidas_segurança": ["Acesso restrito a usuários autenticados","Log de ações administrativas"],
        },
    ]
}


def render_registro_atividades():
    """Exibe o Registro de Atividades de Tratamento (Art. 37 LGPD) no painel admin."""
    st.markdown("#### 📄 Registro de Atividades de Tratamento — Art. 37 LGPD")
    st.markdown(
        f'<div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:.8rem 1rem;margin-bottom:1rem">'
        f'<p style="color:#e0c0d0;margin:0;font-size:.88rem">'
        f'<b>Controlador:</b> {REGISTRO_ATIVIDADES["controlador"]}<br>'
        f'<b>CNPJ:</b> {REGISTRO_ATIVIDADES["cnpj"]}<br>'
        f'<b>DPO:</b> {REGISTRO_ATIVIDADES["dpo_contato"]}<br>'
        f'<b>Última atualização:</b> {REGISTRO_ATIVIDADES["ultima_atualizacao"]}'
        f'</p></div>',
        unsafe_allow_html=True
    )

    for i, atv in enumerate(REGISTRO_ATIVIDADES["atividades"], 1):
        with st.expander(f"Atividade {i}: {atv['nome']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Finalidade:** {atv['finalidade']}")
                st.markdown(f"**Base legal:** {atv['base_legal']}")
                st.markdown(f"**Dados sensíveis:** {atv['dados_sensiveis']}")
                st.markdown(f"**Retenção:** {atv['prazo_retencao']}")
                st.markdown(f"**Transferência internacional:** {atv['transferencia_internacional']}")
            with col2:
                st.markdown("**Dados coletados:**")
                for d in atv["dados_coletados"]:
                    st.markdown(f"- {d}")
                st.markdown("**Destinatários:**")
                for d in atv["destinatarios"]:
                    st.markdown(f"- {d}")


def render_lgpd_admin():
    """Painel LGPD completo para superadmin."""
    st.markdown("---")
    st.markdown("#### 🔒 LGPD — Conformidade e Gestão de Dados")

    tab_ret, tab_req, tab_reg = st.tabs([
        "🗑️ Retenção de Dados",
        "📬 Solicitações de Exclusão",
        "📄 Registro de Atividades"
    ])

    with tab_ret:
        st.markdown(
            f'<p style="color:#c0a0b8;font-size:.88rem">'
            f'Política de retenção configurada: <b style="color:#e0c0d0">{RETENTION_DAYS} dias</b>. '
            f'Leads cadastrados há mais de {RETENTION_DAYS} dias serão excluídos automaticamente.</p>',
            unsafe_allow_html=True
        )
        cutoff_date = (date.today() - timedelta(days=RETENTION_DAYS)).strftime("%d/%m/%Y")
        st.info(f"Leads anteriores a **{cutoff_date}** serão excluídos.")

        if st.button("🗑️ Aplicar política agora", use_container_width=True, key="btn_retention"):
            log = []
            n = apply_retention_policy(log_fn=log.append)
            if n > 0:
                st.success(f"✅ {n} lead(s) excluído(s).")
            else:
                st.info("Nenhum lead fora do prazo de retenção.")
            if log:
                with st.expander("Log"):
                    st.code("\n".join(log))

    with tab_req:
        requests = load_deletion_requests()
        if not requests:
            st.info("Nenhuma solicitação de exclusão pendente.")
        else:
            st.markdown(f"**{len(requests)} solicitação(ões) registrada(s):**")
            for req in requests:
                status_color = "#ffb400" if req["status"] == "pendente" else "#60ffb0"
                st.markdown(
                    f'<div style="background:rgba(0,0,0,0.2);border-radius:10px;'
                    f'padding:.7rem 1rem;margin-bottom:.5rem">'
                    f'<p style="color:#e0c0d0;margin:0;font-size:.88rem">'
                    f'📱 <b>{req.get("telefone","?")}</b> &nbsp;'
                    f'<span style="color:{status_color}">● {req["status"]}</span><br>'
                    f'📅 {req["data_solicitacao"][:10]}<br>'
                    f'📝 {req.get("motivo","")}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    with tab_reg:
        render_registro_atividades()
