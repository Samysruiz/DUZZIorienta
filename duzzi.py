"""
duzzi.py — Lógica central do Duzzi Orienta
Todos os arquivos estão na raiz do repositório.
"""

import io
import json
import logging
import sqlite3
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import qrcode

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / ".leads.db"

# ── Caminhos dos dados (tudo na raiz) ─────────────────────────────────────────
def _find(filename: str) -> Path:
    """Procura o arquivo na raiz e em subpastas comuns."""
    for candidate in [
        BASE_DIR / filename,
        BASE_DIR / "data" / filename,
    ]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Arquivo não encontrado: {filename}")


# ── Google Sheets (opcional) ──────────────────────────────────────────────────
def _get_worksheet():
    try:
        import os, gspread
        from google.oauth2.service_account import Credentials

        SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds_json = os.getenv("GOOGLE_CREDS_JSON", "")
        creds_file = BASE_DIR / "google_creds.json"

        if creds_json:
            info = json.loads(creds_json)
        elif creds_file.exists():
            with open(creds_file) as f:
                info = json.load(f)
        else:
            return None

        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        gc    = gspread.authorize(creds)
        sid   = os.getenv("GOOGLE_SHEET_ID", "")
        sname = os.getenv("GOOGLE_SHEET_NAME", "Duzzi Leads")

        try:
            sh = gc.open_by_key(sid) if sid else gc.open(sname)
        except Exception:
            sh = gc.create(sname)
            sh.share(None, perm_type="anyone", role="writer")

        try:
            ws = sh.worksheet("Leads")
        except Exception:
            ws = sh.add_worksheet("Leads", rows=2000, cols=20)
            ws.append_row([
                "ID","Data/Hora","Nome","WhatsApp","E-mail",
                "Escola de Origem","Cidade",
                "Curso Recomendado","Score","Compatibilidade %",
                "Abriu Inscrição","Origem","2º Curso","3º Curso",
            ], value_input_option="RAW")
        return ws

    except Exception as e:
        logger.warning(f"[Sheets] {e}")
        return None


# ── Dados ─────────────────────────────────────────────────────────────────────
def load_courses():
    with open(_find("courses.json"), encoding="utf-8") as f:
        return json.load(f)

def load_questions():
    with open(_find("questions.json"), encoding="utf-8") as f:
        return json.load(f)

def get_course_map():
    return {c["id"]: c for c in load_courses()}


# ── Scoring ───────────────────────────────────────────────────────────────────
def empty_scores():
    return {c["id"]: 0 for c in load_courses()}

def calculate_scores(answers: dict) -> dict:
    scores = empty_scores()
    for q in load_questions():
        idx = answers.get(q["id"])
        if idx is None:
            continue
        for cid, val in q["options"][idx].get("weights", {}).items():
            if cid in scores:
                scores[cid] += val
    return scores

def rank_courses(scores: dict) -> list:
    cm = get_course_map()
    ranked = [
        {**cm[cid], "score": sc}
        for cid, sc in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if cid in cm
    ]
    # Normaliza top 3 para somarem exatamente 100%
    top3 = [r for r in ranked[:3] if r["score"] > 0]
    total = sum(r["score"] for r in top3)
    if total > 0:
        pcts = [round(r["score"] / total * 100) for r in top3]
        diff = 100 - sum(pcts)
        pcts[0] += diff  # ajusta arredondamento no 1o lugar
        for r, p in zip(top3, pcts):
            r["compat_pct"] = p
    else:
        for r in top3:
            r["compat_pct"] = 0
    for r in ranked[3:]:
        r["compat_pct"] = 0
    return ranked

def score_percent(score: int, max_score: int = 27) -> int:
    return min(100, round(score / max_score * 100))


# ── Texto e links ─────────────────────────────────────────────────────────────
def build_explanation(course: dict) -> str:
    tags = ", ".join(course["tags"][:4])
    return (
        f"{course['name']} aparece forte no seu perfil porque combina com "
        f"interesses em **{tags}**. {course['summary']}"
    )

def build_message(student_name: str, top_courses: list) -> str:
    first_name = student_name.split()[0] if student_name else "você"
    top = top_courses[0]
    pct_top = top.get("compat_pct", score_percent(top["score"]))

    medal = ["", "", ""]
    ranking_lines = []
    for i, c in enumerate(top_courses[:3], 0):
        pct = c.get("compat_pct", score_percent(c["score"]))
        ranking_lines.append(f"{medal[i]} {c['name']} — {pct}% compatibilidade")

    ranking_str = "\n".join(ranking_lines)

    message = (
        f"Olá, {first_name}! \n"
        f"\n"
        f"Analisei seu perfil e encontrei os cursos da Faculdade Donaduzzi "
        f"que mais combinam com você:\n"
        f"\n"
        f"{ranking_str}\n"
        f"\n"
        f" *{top['name']}* é o curso mais indicado para o seu perfil "
        f"- {pct_top}% de compatibilidade!\n"
        f"\n"
        f" Inscreva-se agora:\n"
        f"{top['url']}\n"
        f"\n"
        f"Qualquer dúvida, é só responder essa mensagem \n"
        f"\n"
        f"Duzzi Orienta • Faculdade Donaduzzi "
    )
    return message


def whatsapp_link(phone: str, message: str) -> str:
    clean = "".join(c for c in phone if c.isdigit())
    if clean and not clean.startswith("55"):
        clean = "55" + clean
    return f"https://wa.me/{clean}?text={quote(message)}"

def sms_link(phone: str, message: str) -> str:
    clean = "".join(c for c in phone if c.isdigit())
    return f"sms:{clean}?body={quote(message)}"


# ── QR Code ───────────────────────────────────────────────────────────────────
def _make_qr(url: str) -> bytes:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8, border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#8B1A2A", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def make_whatsapp_qr(phone: str, message: str) -> bytes:
    return _make_qr(whatsapp_link(phone, message))

def make_url_qr(url: str) -> bytes:
    return _make_qr(url)


# ── Banco SQLite ──────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            nome                TEXT NOT NULL,
            telefone            TEXT DEFAULT '',
            email               TEXT DEFAULT '',
            escola_origem       TEXT DEFAULT '',
            cidade              TEXT DEFAULT '',
            curso_recomendado   TEXT DEFAULT '',
            score_top           INTEGER DEFAULT 0,
            compatibilidade_pct INTEGER DEFAULT 0,
            ranking_json        TEXT DEFAULT '[]',
            abriu_inscricao     INTEGER DEFAULT 0,
            origem              TEXT DEFAULT 'quiz',
            criado_em           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for col, typedef in [
        ("escola_origem",       "TEXT DEFAULT ''"),
        ("cidade",              "TEXT DEFAULT ''"),
        ("compatibilidade_pct", "INTEGER DEFAULT 0"),
        ("abriu_inscricao",     "INTEGER DEFAULT 0"),
    ]:
        try:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    conn.commit()
    conn.close()

def save_lead(nome, telefone, email, escola_origem, cidade,
              top_course, score_top, compat_pct, ranking_json,
              origem="quiz") -> int:
    """
    Salva ou atualiza um lead.
    Deduplicação: mesmo nome+telefone → UPDATE em vez de novo INSERT.
    """
    init_db()
    _tel = "".join(d for d in (telefone or "") if d.isdigit())
    conn = sqlite3.connect(DB_PATH)

    existing = conn.execute(
        "SELECT id FROM leads WHERE LOWER(TRIM(nome))=LOWER(TRIM(?)) AND telefone=? LIMIT 1",
        (nome, _tel)
    ).fetchone()

    if existing:
        lead_id = existing[0]
        conn.execute(
            """UPDATE leads SET
               email=?, escola_origem=?, cidade=?,
               curso_recomendado=?, score_top=?, compatibilidade_pct=?,
               ranking_json=?, criado_em=CURRENT_TIMESTAMP
               WHERE id=?""",
            (email, escola_origem, cidade,
             top_course, score_top, compat_pct, ranking_json, lead_id)
        )
    else:
        cur = conn.execute(
            """INSERT INTO leads
               (nome,telefone,email,escola_origem,cidade,
                curso_recomendado,score_top,compatibilidade_pct,ranking_json,origem)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (nome, _tel, email, escola_origem, cidade,
             top_course, score_top, compat_pct, ranking_json, origem),
        )
        lead_id = cur.lastrowid

    conn.commit()
    conn.close()

    try:
        ws = _get_worksheet()
        if ws:
            ranking = json.loads(ranking_json) if ranking_json else []
            c2 = ranking[1]["name"] if len(ranking) > 1 else ""
            c3 = ranking[2]["name"] if len(ranking) > 2 else ""
            ws.append_row([
                lead_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                nome, telefone, email, escola_origem, cidade,
                top_course, score_top, compat_pct,
                "Não", origem, c2, c3,
            ], value_input_option="RAW")
    except Exception as e:
        logger.warning(f"[Sheets] {e}")

    return lead_id

def mark_inscricao_aberta(lead_id: int):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE leads SET abriu_inscricao=1 WHERE id=?", (lead_id,))
    conn.commit()
    conn.close()
    try:
        ws = _get_worksheet()
        if ws:
            cell = ws.find(str(lead_id))
            if cell:
                ws.update_cell(cell.row, 11, "Sim")
    except Exception as e:
        logger.warning(f"[Sheets] {e}")

def list_leads() -> list:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id,nome,telefone,email,escola_origem,cidade,
               curso_recomendado,score_top,compatibilidade_pct,
               abriu_inscricao,ranking_json,origem,criado_em
        FROM leads ORDER BY criado_em DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_concluido(lead_id: int):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    try: conn.execute("ALTER TABLE leads ADD COLUMN status TEXT DEFAULT 'Ativo'")
    except: pass
    conn.execute("UPDATE leads SET status='Concluído' WHERE id=?", (lead_id,))
    conn.commit(); conn.close()

def mark_descartado(lead_id: int):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    try: conn.execute("ALTER TABLE leads ADD COLUMN status TEXT DEFAULT 'Ativo'")
    except: pass
    conn.execute("UPDATE leads SET status='Descartado' WHERE id=?", (lead_id,))
    conn.commit(); conn.close()

def delete_lead(lead_id: int):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM leads WHERE id=?", (lead_id,))
    conn.commit(); conn.close()

def get_metrics() -> dict:
    leads = list_leads()
    if not leads:
        return {"total":0,"hoje":0,"top_curso":"-","abriram_inscricao":0,
                "nao_abriram":0,"concluidos":0,"descartados":0,
                "cursos_contagem":{},"por_dia":{},"escolas":{},"cidades":{}}
    today = date.today().isoformat()
    hoje  = sum(1 for l in leads if str(l.get("criado_em",""))[:10]==today)
    abriram = sum(1 for l in leads if l.get("abriu_inscricao") in (1,True,"Sim","sim"))
    concluidos  = sum(1 for l in leads if l.get("status") in ("Concluído","concluido"))
    descartados = sum(1 for l in leads if l.get("status") in ("Descartado","descartado"))
    cursos  = Counter(l.get("curso_recomendado","") for l in leads)
    escolas = Counter(l.get("escola_origem","") for l in leads if l.get("escola_origem"))
    cidades = Counter(l.get("cidade","") for l in leads if l.get("cidade"))
    por_dia: dict = {}
    for l in leads:
        d = str(l.get("criado_em",""))[:10]
        if d: por_dia[d] = por_dia.get(d,0)+1
    return {
        "total":len(leads),"hoje":hoje,
        "top_curso":cursos.most_common(1)[0][0] if cursos else "-",
        "abriram_inscricao":abriram,"nao_abriram":len(leads)-abriram,
        "concluidos":concluidos,"descartados":descartados,
        "cursos_contagem":dict(cursos),"por_dia":por_dia,
        "escolas":dict(escolas.most_common(10)),"cidades":dict(cidades.most_common(10)),
    }

def load_inep_data() -> dict:
    try:
        from scraper import load_inep
        return load_inep()
    except Exception:
        p = Path(__file__).parent / "inep_data.json"
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        return {}
