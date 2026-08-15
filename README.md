# 🤖 Duzzi Orienta

> Sistema inteligente de recomendação de cursos da **Faculdade Donaduzzi**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://duzziorienta.streamlit.app)

---

## 📋 Sobre o projeto

O **Duzzi Orienta** é uma aplicação web desenvolvida em Python/Streamlit que ajuda candidatos a descobrir qual curso da Faculdade Donaduzzi combina melhor com o seu perfil. Por meio de um quiz vocacional com 8 perguntas baseado na teoria RIASEC de Holland, o sistema calcula um ranking personalizado de compatibilidade entre o perfil do candidato e os **9 cursos** da instituição, exibindo também indicadores oficiais do INEP sobre evasão e conclusão de cada área.

O sistema conta com painel administrativo para gestão de dados institucionais e uma camada de Super Admin para manutenção técnica.

> ⚠️ **Protótipo funcional em fase de aprovação institucional.** O sistema está operacional e disponível para demonstração, mas ainda não está em produção com coleta de dados reais de candidatos.

---

## 🗂️ Estrutura do projeto

```
duzzi_orienta/
├── app.py              # Interface principal (Streamlit)
├── duzzi.py            # Lógica de negócio: scoring e ranking
├── scraper.py          # Coleta dados da Faculdade Donaduzzi e INEP
├── admin_panel.py      # Painel Admin: gestão de dados institucionais
├── superadmin.py       # Super Admin: manutenção técnica e scraping
├── github_sync.py      # Commit de atualizações direto no GitHub
├── lgpd.py             # Tela de consentimento e menu Meus Dados (LGPD)
├── login_page.py       # Autenticação de acesso administrativo
├── course_manager.py   # Gerenciamento de cursos
├── database.py         # Camada de acesso a dados
├── courses.json        # Dados dos 9 cursos (atualizado via scraper)
├── questions.json      # Perguntas e pesos do quiz RIASEC
├── inep_data.json      # Indicadores INEP por curso (média nacional)
├── bolsas.json         # Informações de bolsas por curso
├── requirements.txt    # Dependências Python
├── duzzi_logo.png      # Logo do Duzzi Orienta
└── logofaculdade.png   # Logo da Faculdade Donaduzzi
```

---

## ⚙️ Como rodar localmente

### 1. Clone o repositório

```bash
git clone https://github.com/samysruiz/duzziorienta.git
cd duzziorienta
```

### 2. Crie o ambiente virtual e instale as dependências

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 3. Configure os segredos locais

Crie o arquivo `.streamlit/secrets.toml` com suas credenciais (veja seção abaixo). **Nunca suba esse arquivo para o GitHub** — ele já está no `.gitignore`.

### 4. Rode o app

```bash
streamlit run app.py
```

O app abrirá em `http://localhost:8501`.

---

## 🚀 Deploy no Streamlit Cloud

1. Faça push do repositório para o GitHub (todos os arquivos da pasta raiz)
2. Acesse [share.streamlit.io](https://share.streamlit.io) e crie um novo app apontando para `app.py`
3. Configure as variáveis de ambiente em **Settings → Secrets**
4. Clique em **Deploy**

---

## 🔐 Variáveis de ambiente

Configure no painel **Secrets** do Streamlit Cloud (`Settings → Secrets`). 

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| `DUZZI_ADMIN_PASSWORD` | Senha do painel Admin | ✅ |
| `DUZZI_SUPER_PASSWORD` | Senha do Super Admin (manutenção técnica) | ✅ |
| `GITHUB_TOKEN` | Token de acesso ao GitHub (Contents: read/write) para commit automático de atualizações | ✅ |
| `GITHUB_REPO` | Repositório no formato `usuario/repo` | ✅ |

Exemplo de `.streamlit/secrets.toml` para desenvolvimento local:

```toml
DUZZI_ADMIN_PASSWORD = "sua_senha_admin"
DUZZI_SUPER_PASSWORD = "sua_senha_superadmin"
GITHUB_TOKEN = "github_pat_..."
GITHUB_REPO = "seu-usuario/duzziorienta"
```

> ⚠️ **Importante:** Use senhas fortes e únicas. Nunca exponha os valores reais em código ou documentação pública.

---

## 📱 Funcionalidades

### 🎯 Quiz de orientação vocacional (RIASEC)
- 8 perguntas com pesos calibrados por curso, baseadas na teoria de Holland
- Cálculo de score de compatibilidade (0–100%)
- Ranking dos 3 cursos mais indicados, normalizados para somar 100%
- Cobre 5 das 6 dimensões RIASEC (Realista, Investigativo, Social, Empreendedor, Convencional)

### 📚 Catálogo de 9 cursos
Administração · ADS · Ciência de Dados · Engenharia de Bioprocessos · Engenharia de Software · Farmácia · Inteligência Artificial · Pedagogia · Psicologia

Dados coletados diretamente do site da Faculdade Donaduzzi via scraping administrativo (com confirmação humana).

### 📊 Indicadores INEP
- Indicadores de Trajetória da Educação Superior — **média nacional** por área (coorte 2020, referência 2024)
- TDA (Taxa de Desistência Acumulada), TCA (Taxa de Conclusão Acumulada), TAP (Taxa de Permanência Acumulada)
- Cursos novos sem histórico de coorte exibem aviso "🆕 Curso novo"

### 🔐 Níveis de acesso administrativo

**Admin** — voltado para a equipe de captação: visualização e filtragem de leads por cidade, curso de interesse e escola de origem. Permite acompanhar e segmentar o público que interagiu com a ferramenta.

**Super Admin** — manutenção técnica: atualização dos dados institucionais via scraping do site, configuração do sistema e commit direto no GitHub via `commit_file_to_github()`.

### 🛡️ LGPD
- Tela de consentimento antes da coleta de qualquer dado
- Menu "Meus Dados" com acesso e exclusão pelo próprio usuário
- Registro das Atividades de Tratamento preparado para encaminhamento ao DPO institucional

---

## 🔄 Atualização dos dados

Os dados dos cursos podem ser atualizados pelo Super Admin via interface web (fluxo em duas etapas: comparação → confirmação → commit no GitHub). O sistema detecta automaticamente cursos novos e descontinuados comparando com a versão salva.

---

## 🗄️ Banco de dados

O app usa **SQLite** local (arquivo `.leads.db`, gerado automaticamente e incluído no `.gitignore`). 

> No Streamlit Cloud o banco SQLite é **efêmero** — os dados são perdidos a cada reboot. Para produção persistente com coleta de dados reais, configure um banco externo (Supabase com pg_cron recomendado para rotinas de exclusão automática, conforme LGPD).

---

## 🧩 Tecnologias utilizadas

| Tecnologia | Uso |
|------------|-----|
| [Streamlit](https://streamlit.io) | Interface web |
| [Pandas](https://pandas.pydata.org) | Manipulação de dados |
| [requests + BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) | Scraping do site da faculdade |
| [GitHub Contents API](https://docs.github.com/en/rest/repos/contents) | Commit automático de atualizações |
| SQLite | Armazenamento local |

---

## 👩‍💻 Desenvolvimento

Projeto desenvolvido para a **Faculdade Donaduzzi** como ferramenta de apoio ao processo de captação de alunos, especialmente no evento **Duzzi Orienta** (outubro). Em fase de aprovação institucional.

---

*Duzzi Orienta • Faculdade Donaduzzi 🎓*
