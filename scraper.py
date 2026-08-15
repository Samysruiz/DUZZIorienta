"""
scraper.py — Coleta dados da Faculdade Donaduzzi e do INEP
Execute: python scraper.py
Ou chame update_all() de dentro do app.
"""

import json
import logging
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
COURSES_FILE  = BASE_DIR / "courses.json"
INEP_FILE     = BASE_DIR / "inep_data.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# ── Configuração dos cursos ───────────────────────────────────────────────────
COURSE_CONFIG = [
    {
        "id":    "administracao",
        "url":   "https://faculdadedonaduzzi.com.br/graduacao-administracao",
        "tags":  ["negócios","liderança","gestão","marketing","empreendedorismo"],
        "areas": ["gestão empresarial","finanças","marketing","logística","consultoria"],
        "weights_hint": "administracao",
    },
    {
        "id":    "ads",
        "url":   "https://faculdadedonaduzzi.com.br/graduacao-analise-e-desenvolvimento-de-sistemas",
        "tags":  ["programação","software","web","mobile","infraestrutura"],
        "areas": ["desenvolvimento de software","gestão de projetos","análise de requisitos"],
        "weights_hint": "ads",
    },
    {
        "id":    "pedagogia",
        "url":   "https://faculdadedonaduzzi.com.br/cursos-de-graduacao/graduacao-em-pedagogia/",
        "tags":  ["ensino","educação","desenvolvimento humano","mediação","didática"],
        "areas": ["docência","gestão escolar","educação infantil","educação inclusiva","EJA","pedagogia empresarial e hospitalar"],
        "weights_hint": "pedagogia",
    },
    {
        "id":    "ciencia_dados",
        "url":   "https://faculdadedonaduzzi.com.br/graduacao-ciencia-de-dados",
        "tags":  ["dados","estatística","machine learning","mlops","bi"],
        "areas": ["análise de dados","inteligência artificial","engenharia de dados","business intelligence"],
        "weights_hint": "ciencia_dados",
    },
    {
        "id":    "eng_software",
        "url":   "https://faculdadedonaduzzi.com.br/graduacao-engenharia-de-software",
        "tags":  ["arquitetura","qualidade","cloud","microsserviços","desenvolvimento"],
        "areas": ["engenharia de software","arquitetura","pesquisa","modernização de sistemas"],
        "weights_hint": "eng_software",
    },
    {
        "id":    "eng_bioprocessos",
        "url":   "https://faculdadedonaduzzi.com.br/graduacao-engenharia-de-bioprocessos",
        "tags":  ["biotecnologia","laboratório","sustentabilidade","agro","engenharia"],
        "areas": ["bioprocessos","agronegócio","pesquisa aplicada","indústria farmacêutica"],
        "weights_hint": "eng_bioprocessos",
    },
    {
        "id":    "farmacia",
        "url":   "https://faculdadedonaduzzi.com.br/graduacao-farmacia",
        "tags":  ["saúde","laboratório","medicamentos","análises clínicas","pacientes"],
        "areas": ["indústria farmacêutica","análises clínicas","farmácia hospitalar","toxicologia"],
        "weights_hint": "farmacia",
    },
    {
        "id":    "inteligencia_artificial",
        "url":   "https://faculdadedonaduzzi.com.br/inteligencia-artificial",
        "tags":  ["ia","deep learning","visão computacional","pln","dados"],
        "areas": ["especialista em IA","cientista de dados","engenheiro de dados","gestão de projetos de IA"],
        "weights_hint": "inteligencia_artificial",
    },
    {
        "id":    "psicologia",
        "url":   "https://faculdadedonaduzzi.com.br/cursos-de-graduacao/graduacao-em-psicologia/",
        "tags":  ["saúde mental","comportamento humano","cuidado","terapia","pessoas"],
        "areas": ["psicologia clínica","psicologia hospitalar","psicologia organizacional","psicologia escolar","psicologia jurídica","saúde coletiva"],
        "weights_hint": "psicologia",
    },
]

# Dados padrão caso o scraping falhe
FALLBACK_COURSES = [
    {"id":"administracao","name":"Administração","level":"Bacharelado","duration":"8 semestres","turno":"Noturno","url":"https://faculdadedonaduzzi.com.br/graduacao-administracao","summary":"Formação em gestão, empreendedorismo, finanças e liderança com forte base em projetos reais.","tags":["negócios","liderança","gestão","marketing","empreendedorismo"],"areas":["gestão empresarial","finanças","marketing","logística","consultoria"],"evidence":["56 projetos aplicáveis","aprendizagem em situações reais de mercado","100% dos estudantes inseridos no mercado já no primeiro semestre"]},
    {"id":"ads","name":"Análise e Desenvolvimento de Sistemas","level":"Tecnólogo","duration":"5 semestres","turno":"Noturno","url":"https://faculdadedonaduzzi.com.br/graduacao-analise-e-desenvolvimento-de-sistemas","summary":"Curso focado em análise, projeto, desenvolvimento e manutenção de sistemas, com alta proximidade do mercado.","tags":["programação","software","web","mobile","infraestrutura"],"areas":["desenvolvimento de software","gestão de projetos","análise de requisitos","manutenção de sistemas"],"evidence":["parque tecnológico","professor mentor","alta taxa de empregabilidade desde o início"]},
    {"id":"pedagogia","name":"Pedagogia","level":"Licenciatura","duration":"8 semestres","turno":"Matutino e Noturno","url":"https://faculdadedonaduzzi.com.br/cursos-de-graduacao/graduacao-em-pedagogia/","summary":"Formação de professores e gestores educacionais com metodologias ativas, conexão direta com o Colégio Donaduzzi e projetos sociais reais, preparando para docência, gestão escolar e educação inclusiva.","tags":["ensino","educação","desenvolvimento humano","mediação","didática"],"areas":["docência","gestão escolar","educação infantil","educação inclusiva","EJA","pedagogia empresarial e hospitalar"],"evidence":["vivência prática desde o início em escolas e projetos sociais","metodologias ativas e aprendizagem baseada em projetos","atuação ampliada: gestão escolar, empresas, ONGs e iniciativas sociais"]},
    {"id":"ciencia_dados","name":"Ciência de Dados","level":"Tecnólogo","duration":"5 semestres","turno":"Noturno","url":"https://faculdadedonaduzzi.com.br/graduacao-ciencia-de-dados","summary":"Curso para análise de dados, machine learning, MLOps e sistemas de apoio à decisão com aplicação prática.","tags":["dados","estatística","machine learning","mlops","bi"],"areas":["análise de dados","inteligência artificial","engenharia de dados","business intelligence","pesquisa e desenvolvimento"],"evidence":["base sólida em ciência e tecnologia","captura de dados na web","MLOps e aprendizado supervisionado"]},
    {"id":"eng_software","name":"Engenharia de Software","level":"Bacharelado","duration":"8 semestres","turno":"Noturno","url":"https://faculdadedonaduzzi.com.br/graduacao-engenharia-de-software","summary":"Formação completa no ciclo de vida de software, arquitetura, testes, cloud, IoT e modernização de sistemas.","tags":["arquitetura","qualidade","cloud","microsserviços","desenvolvimento"],"areas":["engenharia de software","arquitetura","pesquisa","gestão","modernização de sistemas"],"evidence":["compreender todo o processo","conhecimento moderno","alta taxa de empregabilidade"]},
    {"id":"eng_bioprocessos","name":"Engenharia de Bioprocessos e Biotecnologia","level":"Bacharelado","duration":"10 semestres","turno":"Noturno","url":"https://faculdadedonaduzzi.com.br/graduacao-engenharia-de-bioprocessos","summary":"Integra biologia, química, física e engenharia para criar soluções em biotecnologia, agro, indústria e saúde.","tags":["biotecnologia","laboratório","sustentabilidade","agro","engenharia"],"areas":["bioprocessos","agronegócio","pesquisa aplicada","indústria farmacêutica","gestão industrial"],"evidence":["visão sistêmica e inovadora","90% dos estudantes no mercado durante a formação","forte atuação em agronegócio e saúde"]},
    {"id":"farmacia","name":"Farmácia","level":"Bacharelado","duration":"10 semestres","turno":"Matutino","url":"https://faculdadedonaduzzi.com.br/graduacao-farmacia","summary":"Formação generalista em saúde, análises clínicas, indústria farmacêutica, farmacotécnica e atenção ao paciente.","tags":["saúde","laboratório","medicamentos","análises clínicas","pacientes"],"areas":["indústria farmacêutica","análises clínicas","farmácia hospitalar","farmácia magistral","toxicologia"],"evidence":["estágios em várias áreas farmacêuticas","laboratórios tecnológicos","múltiplas oportunidades em saúde e pesquisa"]},
    {"id":"inteligencia_artificial","name":"Inteligência Artificial","level":"Bacharelado","duration":"8 semestres","turno":"Noturno","url":"https://faculdadedonaduzzi.com.br/inteligencia-artificial","summary":"Forma especialistas em IA com base em dados, machine learning, deep learning, visão computacional, PLN e IoT.","tags":["ia","deep learning","visão computacional","pln","dados"],"areas":["especialista em IA","cientista de dados","engenheiro de dados","gestão de projetos de IA"],"evidence":["formação completa em dados e IA","aprofundamento em deep learning e PLN","contato direto com empresas e startups"]},
    {"id":"psicologia","name":"Psicologia","level":"Bacharelado","duration":"10 semestres","turno":"Noturno","url":"https://faculdadedonaduzzi.com.br/cursos-de-graduacao/graduacao-em-psicologia/","summary":"Formação presencial para compreender o comportamento humano, promover saúde mental e atuar em contextos clínico, hospitalar, organizacional, escolar, jurídico e social. Autorizado com nota máxima (Conceito 5) pelo MEC. Primeira turma: 2º semestre de 2026.","tags":["saúde mental","comportamento humano","cuidado","terapia","pessoas"],"areas":["psicologia clínica","psicologia hospitalar","psicologia organizacional","psicologia escolar","psicologia jurídica","saúde coletiva"],"evidence":["curso autorizado com Conceito 5 pelo MEC","prática desde os primeiros semestres","inserção no ecossistema de inovação do Biopark"]},
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCRAPER — FACULDADE DONADUZZI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_page(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        logger.warning(f"[Scraper] erro em {url}: {e}")
        return None


def _extract_course_info(soup: BeautifulSoup, cfg: dict) -> dict:
    """Extrai nome, resumo, turno, duração e diferenciais da página do curso."""

    # Nome
    name_el = soup.find("h1") or soup.find("h2")
    name = name_el.get_text(strip=True) if name_el else cfg["id"].replace("_", " ").title()

    # Remove prefixos comuns
    for prefix in ["Graduação em ", "Bacharelado em ", "Tecnólogo em ", "GRADUAÇÃO EM "]:
        if name.upper().startswith(prefix.upper()):
            name = name[len(prefix):]

    # Resumo — pega o primeiro parágrafo longo
    summary = ""
    for p in soup.find_all("p"):
        t = p.get_text(strip=True)
        if len(t) > 80 and not any(x in t.lower() for x in ["cookie", "©", "whatsapp", "clique"]):
            summary = t[:300]
            break

    # Duração e turno
    duration = "A definir"
    turno    = "A definir"
    level    = "Bacharelado"

    text_all = soup.get_text(" ", strip=True).lower()

    # Detectar duração
    import re
    dur_match = re.search(r"(\d+)\s*semestres?", text_all)
    if dur_match:
        duration = f"{dur_match.group(1)} semestres"

    # Detectar turno
    if "noturno" in text_all:
        turno = "Noturno"
    elif "matutino" in text_all:
        turno = "Matutino"
    elif "integral" in text_all:
        turno = "Integral"

    # Detectar grau
    if "tecnólogo" in text_all or "tecnologico" in text_all:
        level = "Tecnólogo"
    elif "licenciatura" in text_all:
        level = "Licenciatura"

    # Diferenciais / Evidence — pega itens de listas
    evidence = []
    for li in soup.find_all("li"):
        t = li.get_text(strip=True)
        if 10 < len(t) < 120 and t not in evidence:
            evidence.append(t)
        if len(evidence) >= 5:
            break

    if not evidence:
        evidence = ["Currículo atualizado", "Corpo docente especializado", "Alta empregabilidade"]

    return {
        "id":       cfg["id"],
        "name":     name,
        "level":    level,
        "duration": duration,
        "turno":    turno,
        "url":      cfg["url"],
        "summary":  summary or f"Curso de {name} na Faculdade Donaduzzi.",
        "tags":     cfg["tags"],
        "areas":    cfg["areas"],
        "evidence": evidence[:4],
    }


def scrape_donaduzzi(log_fn=None) -> list:
    """
    Raspa todas as páginas de curso da Faculdade Donaduzzi.
    Retorna lista de dicts com dados dos cursos.
    Usa fallback se a página não puder ser acessada.
    """
    fallback_map = {c["id"]: c for c in FALLBACK_COURSES}
    courses = []

    for cfg in COURSE_CONFIG:
        msg = f"🔍 Buscando: {cfg['id']}..."
        logger.info(msg)
        if log_fn: log_fn(msg)

        soup = _get_page(cfg["url"])
        if soup:
            course = _extract_course_info(soup, cfg)
            msg = f"  ✅ {course['name']} ({course['level']} · {course['duration']} · {course['turno']})"
        else:
            course = fallback_map[cfg["id"]]
            msg = f"  ⚠️ {cfg['id']} — usando dados locais (site fora do ar)"

        if log_fn: log_fn(msg)
        courses.append(course)
        time.sleep(0.8)  # respeito ao servidor

    return courses


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCRAPER — INEP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Mapeamento: id do curso → nome(s) possíveis no INEP
INEP_COURSE_MAP = {
    "administracao":          ["administração", "administracao"],
    "ads":                    ["análise e desenvolvimento de sistemas", "analise e desenvolvimento de sistemas"],
    "ciencia_dados":          ["ciência de dados", "ciencia de dados"],
    "eng_software":           ["engenharia de software"],
    "eng_bioprocessos":       ["engenharia de bioprocessos", "bioprocessos e biotecnologia", "engenharia de bioprocessos e biotecnologia"],
    "farmacia":               ["farmácia", "farmacia"],
    "inteligencia_artificial":["inteligência artificial", "inteligencia artificial"],
}

# Dados INEP reais — médias nacionais, coorte 2020, ref 2024
# Calculados a partir do arquivo oficial (download manual abr/2025)
INEP_FALLBACK = {
    "administracao":           {"tda": 62.1, "tca": 24.4, "tap": 13.6, "registros": 1962, "area": "Negócios, administração e direito"},
    "ads":                     {"tda": 65.7, "tca": 27.4, "tap":  6.9, "registros":  603, "area": "Computação e TIC"},
    "ciencia_dados":           {"tda": 65.6, "tca": 24.3, "tap": 10.0, "registros":   28, "area": "Computação e TIC"},
    "eng_software":            {"tda": 58.5, "tca": 23.8, "tap": 17.6, "registros":   88, "area": "Computação e TIC"},
    "eng_bioprocessos":        {"tda": 50.2, "tca":  6.5, "tap": 43.3, "registros":   19, "area": "Agropecuária e Biotecnologia"},
    "farmacia":                {"tda": 49.3, "tca": 32.6, "tap": 18.1, "registros":  649, "area": "Saúde e bem-estar"},
    "inteligencia_artificial": {"tda": 58.8, "tca": 27.4, "tap": 13.8, "registros":    7, "area": "Computação e TIC"},
}


def scrape_inep(log_fn=None) -> dict:
    """
    Lê os Indicadores de Trajetória do INEP.
    Prioridade:
      1. Arquivo local  (coloque o .xlsx na mesma pasta do scraper.py)
      2. Download da URL oficial do INEP
      3. Fallback com médias nacionais pré-calculadas (coorte 2020, ref 2024)
    """
    import pandas as pd, io, urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    msg = "🏛️ Buscando dados do INEP (Indicadores de Trajetória)..."
    logger.info(msg)
    if log_fn: log_fn(msg)

    # ── 1. Tenta ler arquivo local primeiro ──────────────────────────────────
    LOCAL_NAMES = [
        "indicadores_trajetoria_educacao_superior_2020_2024.xlsx",
        "indicadores_trajetoria_educacao_superior_2019_2023.xlsx",
        "indicadores_trajetoria_educacao_superior_2018_2022.xlsx",
    ]
    data = None
    fonte_arquivo = None

    for nome in LOCAL_NAMES:
        local_path = BASE_DIR / nome
        if local_path.exists():
            if log_fn: log_fn(f"  📂 Arquivo local encontrado: {nome}")
            data = local_path.read_bytes()
            fonte_arquivo = nome
            break

    # ── 2. Se não achou local, tenta download ────────────────────────────────
    if data is None:
        INEP_URLS = [
            "https://download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais/2024/indicadores_trajetoria_educacao_superior_2020_2024.xlsx",
            "https://download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais/2023/indicadores_trajetoria_educacao_superior_2019_2023.xlsx",
            "https://download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais/2022/indicadores_trajetoria_educacao_superior_2018_2022.xlsx",
        ]
        for url in INEP_URLS:
            nome = url.split("/")[-1]
            if log_fn: log_fn(f"  📥 Tentando download: {nome}...")
            try:
                r = requests.get(url, headers=HEADERS, timeout=90, stream=True, verify=False)
                if r.status_code == 200:
                    data = b""
                    for chunk in r.iter_content(chunk_size=65536):
                        data += chunk
                    fonte_arquivo = nome
                    if log_fn: log_fn(f"  ✅ Download OK — {len(data)/1024/1024:.1f} MB")
                    break
                else:
                    if log_fn: log_fn(f"     ↳ HTTP {r.status_code} — pulando")
            except Exception as e:
                if log_fn: log_fn(f"     ↳ Erro: {str(e)[:80]} — pulando")

    # ── 3. Fallback se tudo falhou ────────────────────────────────────────────
    if data is None:
        msg = (
            "  ⚠️ Arquivo INEP não encontrado.\n"
            "  💡 Solução: baixe o arquivo manualmente e coloque na pasta do projeto:\n"
            "     https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/"
            "indicadores-educacionais/indicadores-de-trajetoria-da-educacao-superior\n"
            "  📁 Nome esperado: indicadores_trajetoria_educacao_superior_2020_2024.xlsx"
        )
        if log_fn: log_fn(msg)
        return {k: {**v, "fonte": "fallback"} for k, v in INEP_FALLBACK.items()}

    try:
        # ── Lê o Excel (header na linha 8, índice 8) ─────────────────────────
        df = pd.read_excel(io.BytesIO(data), header=8)

        for col in ["TAP", "TCA", "TDA", "TCAN", "TADA", "NU_ANO_REFERENCIA", "CO_IES"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Ano de referência mais recente do arquivo
        ano_ref = int(df["NU_ANO_REFERENCIA"].max()) if "NU_ANO_REFERENCIA" in df.columns else "?"
        df_ano  = df[df["NU_ANO_REFERENCIA"] == ano_ref].copy() if "NU_ANO_REFERENCIA" in df.columns else df
        if log_fn: log_fn(f"  📅 Ano de referência: {ano_ref} | {len(df_ano):,} registros")

        # Tenta filtrar pela Donaduzzi (cód. INEP 25452)
        COD_DONADUZZI = 25452
        df_dona = df_ano[df_ano["CO_IES"] == COD_DONADUZZI] if "CO_IES" in df_ano.columns else pd.DataFrame()
        n_dona  = len(df_dona)
        if log_fn: log_fn(f"  🏫 Donaduzzi (cód {COD_DONADUZZI}): {n_dona} registro(s) no INEP")

        df_fonte    = df_dona if n_dona > 0 else df_ano
        fonte_label = f"INEP {ano_ref} — Donaduzzi" if n_dona > 0 else f"INEP {ano_ref} — média nacional"
        area_col    = "NO_CINE_AREA_GERAL"

        if n_dona == 0 and log_fn:
            log_fn("  ℹ️  Donaduzzi ainda sem coorte completa no INEP — usando médias nacionais")

        result = {}
        for cid, names in INEP_COURSE_MAP.items():
            mask = pd.Series([False] * len(df_fonte), index=df_fonte.index)
            if "NO_CURSO" in df_fonte.columns:
                for nm in names:
                    mask |= df_fonte["NO_CURSO"].str.lower().str.contains(nm, na=False)
            sub = df_fonte[mask]
            if len(sub) > 0 and "TDA" in sub.columns:
                result[cid] = {
                    "tda":       round(float(sub["TDA"].mean()), 1),
                    "tca":       round(float(sub["TCA"].mean()), 1) if "TCA" in sub.columns else 0,
                    "tap":       round(float(sub["TAP"].mean()), 1) if "TAP" in sub.columns else 0,
                    "registros": len(sub),
                    "area":      sub[area_col].mode()[0] if area_col in sub.columns and len(sub) > 0 else "-",
                    "fonte":     fonte_label,
                }
                if log_fn: log_fn(f"  📊 {cid}: TDA={result[cid]['tda']}% TCA={result[cid]['tca']}% TAP={result[cid]['tap']}% ({result[cid]['registros']} registros)")
            else:
                result[cid] = {**INEP_FALLBACK.get(cid, {}), "fonte": "fallback"}

        return result

    except Exception as e:
        msg = f"  ⚠️ Erro ao processar XLSX ({e}) — usando dados pré-calculados"
        logger.warning(msg)
        if log_fn: log_fn(msg)
        return {k: {**v, "fonte": "fallback"} for k, v in INEP_FALLBACK.items()}



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DETECTOR DE NOVOS CURSOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# URLs conhecidas para varrer em busca de novos cursos
PAGES_TO_SCAN = [
    "https://faculdadedonaduzzi.com.br",
    "https://faculdadedonaduzzi.com.br/cursos",
    "https://faculdadedonaduzzi.com.br/graduacao",
    "https://bioparkeducacao.com.br/cursos",
]

# Padrões de URL que indicam página de curso
COURSE_URL_PATTERNS = [
    "/graduacao-",
    "/curso-",
    "/bacharelado-",
    "/tecnologo-",
    "/licenciatura-",
    "/farmacia",
    "/inteligencia-artificial",
]

# Palavras que indicam que um link é de curso
COURSE_LINK_KEYWORDS = [
    "graduação", "graduacao", "curso", "bacharelado",
    "tecnólogo", "tecnologo", "licenciatura", "engenharia",
    "farmácia", "farmacia", "administração", "análise",
    "ciência", "inteligência",
]


def _url_to_id(url: str) -> str:
    """Converte uma URL de curso em um ID normalizado."""
    import re
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"[^a-z0-9]+", "_", slug.lower())
    # Remove prefixos comuns
    for prefix in ["graduacao_", "curso_", "bacharelado_", "tecnologo_"]:
        if slug.startswith(prefix):
            slug = slug[len(prefix):]
    return slug.strip("_")


def detect_new_courses(log_fn=None) -> list:
    """
    Varre o site da Faculdade Donaduzzi em busca de cursos novos
    que ainda não estão em courses.json.

    Retorna lista de dicts com os cursos novos encontrados:
    [{ "id", "name", "url", "summary", "tags", ... }]
    """
    import re

    # Carrega IDs já conhecidos
    known_urls = {cfg["url"].rstrip("/") for cfg in COURSE_CONFIG}
    known_ids  = {cfg["id"] for cfg in COURSE_CONFIG}

    if COURSES_FILE.exists():
        try:
            existing = json.loads(COURSES_FILE.read_text(encoding="utf-8"))
            for c in existing:
                known_ids.add(c.get("id",""))
                known_urls.add(c.get("url","").rstrip("/"))
        except Exception:
            pass

    msg = "🔍 Varrendo site da Donaduzzi em busca de novos cursos..."
    logger.info(msg)
    if log_fn: log_fn(msg)

    found_urls = set()

    for page_url in PAGES_TO_SCAN:
        soup = _get_page(page_url)
        if not soup:
            continue

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()

            # Normaliza URL
            if href.startswith("/"):
                href = "https://faculdadedonaduzzi.com.br" + href
            if not href.startswith("http"):
                continue

            href = href.rstrip("/").split("?")[0].split("#")[0]

            # Verifica se parece URL de curso
            is_course_url = any(p in href for p in COURSE_URL_PATTERNS)
            link_text = a.get_text(strip=True).lower()
            is_course_text = any(k in link_text for k in COURSE_LINK_KEYWORDS)

            if (is_course_url or is_course_text) and "faculdadedonaduzzi" in href:
                found_urls.add(href)

        time.sleep(0.5)

    # Filtra só os novos
    new_urls = found_urls - known_urls
    if log_fn: log_fn(f"  🔗 {len(found_urls)} links de curso encontrados, {len(new_urls)} novos")

    new_courses = []
    for url in sorted(new_urls):
        course_id = _url_to_id(url)

        if course_id in known_ids or len(course_id) < 3:
            continue

        msg = f"  🆕 Novo curso detectado: {url}"
        logger.info(msg)
        if log_fn: log_fn(msg)

        # Tenta extrair info da página
        soup = _get_page(url)
        if soup:
            fake_cfg = {
                "id":    course_id,
                "url":   url,
                "tags":  [],
                "areas": [],
            }
            try:
                info = _extract_course_info(soup, fake_cfg)
            except Exception:
                info = {
                    "id": course_id, "name": course_id.replace("_"," ").title(),
                    "url": url, "summary": "", "tags": [], "areas": [],
                    "level": "A definir", "duration": "A definir", "turno": "A definir",
                    "evidence": [],
                }
        else:
            info = {
                "id": course_id, "name": course_id.replace("_"," ").title(),
                "url": url, "summary": "", "tags": [], "areas": [],
                "level": "A definir", "duration": "A definir", "turno": "A definir",
                "evidence": [],
            }

        info["_novo"] = True  # marcador para o painel
        new_courses.append(info)
        time.sleep(0.5)

    if log_fn:
        if new_courses:
            log_fn(f"✅ {len(new_courses)} curso(s) novo(s) encontrado(s)!")
        else:
            log_fn("✅ Nenhum curso novo detectado.")

    return new_courses


def save_new_courses_pending(courses: list):
    """Salva cursos novos detectados em pending_courses.json para o admin revisar."""
    pending_file = BASE_DIR / "pending_courses.json"
    pending_file.write_text(
        json.dumps(courses, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def load_pending_courses() -> list:
    """Carrega cursos pendentes de aprovação."""
    pending_file = BASE_DIR / "pending_courses.json"
    if pending_file.exists():
        try:
            return json.loads(pending_file.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def dismiss_pending_course(course_id: str):
    """Remove um curso da lista de pendentes."""
    pending = load_pending_courses()
    pending = [c for c in pending if c.get("id") != course_id]
    pending_file = BASE_DIR / "pending_courses.json"
    pending_file.write_text(
        json.dumps(pending, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )




def update_all(log_fn=None) -> dict:
    """
    Atualiza courses.json e inep_data.json.
    Retorna {"courses": [...], "inep": {...}, "status": "ok"|"partial"|"fallback"}
    """
    if log_fn: log_fn("🚀 Iniciando atualização dos dados...")

    # 1. Cursos
    courses = scrape_donaduzzi(log_fn)
    with open(COURSES_FILE, "w", encoding="utf-8") as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)
    if log_fn: log_fn(f"✅ courses.json salvo com {len(courses)} cursos")

    # 2. INEP
    inep = scrape_inep(log_fn)
    with open(INEP_FILE, "w", encoding="utf-8") as f:
        json.dump(inep, f, ensure_ascii=False, indent=2)
    if log_fn: log_fn(f"✅ inep_data.json salvo com {len(inep)} cursos")

    # Verificar se usou fallback
    used_fallback = any(v.get("fonte") == "fallback" for v in inep.values())
    status = "partial" if used_fallback else "ok"

    if log_fn: log_fn(f"🏁 Atualização concluída! Status: {status}")
    return {"courses": courses, "inep": inep, "status": status}


def load_inep() -> dict:
    """Carrega dados INEP do arquivo local (ou fallback)."""
    if INEP_FILE.exists():
        with open(INEP_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {k: {**v, "fonte": "fallback"} for k, v in INEP_FALLBACK.items()}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_all(log_fn=print)
