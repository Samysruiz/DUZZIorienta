"""
database.py — Supabase (PostgreSQL) como banco principal do Duzzi Orienta
Tabelas: users, leads
"""

import json
import logging
import os
from datetime import date, datetime

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONEXÃO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_client():
    """Retorna cliente Supabase ou None se não configurado."""
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception as e:
        logger.warning(f"[Supabase] {e}")
        return None

def supabase_ok() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SQL — criação das tabelas (rode uma vez no Supabase SQL Editor)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SETUP_SQL = """
-- Tabela de usuários do sistema (admin e superadmin)
CREATE TABLE IF NOT EXISTS duzzi_users (
    id          SERIAL PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,           -- hash bcrypt
    role        TEXT DEFAULT 'admin',   -- 'admin' | 'superadmin'
    ativo       BOOLEAN DEFAULT TRUE,
    criado_em   TIMESTAMPTZ DEFAULT NOW()
);

-- Inserir superadmin padrão (configure a senha via hash bcrypt)
-- Troque o hash depois de configurar
INSERT INTO duzzi_users (username, password, role)
VALUES ('superadmin', '$2b$12$placeholder', 'superadmin')
ON CONFLICT (username) DO NOTHING;

-- Tabela de leads
CREATE TABLE IF NOT EXISTS leads (
    id                  SERIAL PRIMARY KEY,
    nome                TEXT NOT NULL,
    telefone            TEXT DEFAULT '',
    email               TEXT DEFAULT '',
    escola_origem       TEXT DEFAULT '',
    cidade              TEXT DEFAULT '',
    curso_recomendado   TEXT DEFAULT '',
    score_top           INTEGER DEFAULT 0,
    compatibilidade_pct INTEGER DEFAULT 0,
    ranking_json        TEXT DEFAULT '[]',
    abriu_inscricao     BOOLEAN DEFAULT FALSE,
    status              TEXT DEFAULT 'Ativo',  -- 'Ativo' | 'Concluído' | 'Descartado'
    origem              TEXT DEFAULT 'quiz',
    criado_em           TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_leads_curso ON leads(curso_recomendado);
CREATE INDEX IF NOT EXISTS idx_leads_cidade ON leads(cidade);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_data ON leads(criado_em);
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUTENTICAÇÃO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _hash_password(pwd: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        import hashlib
        return hashlib.sha256(pwd.encode()).hexdigest()

def _check_password(pwd: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(pwd.encode(), hashed.encode())
    except ImportError:
        import hashlib
        return hashlib.sha256(pwd.encode()).hexdigest() == hashed

def login(username: str, password: str) -> dict | None:
    """
    Verifica credenciais.
    Retorna dict com {id, username, role} ou None.
    Tenta Supabase, fallback para variáveis de ambiente.
    """
    sb = _get_client()
    if sb:
        try:
            res = sb.table("duzzi_users")\
                    .select("id,username,password,role")\
                    .eq("username", username)\
                    .eq("ativo", True)\
                    .execute()
            if res.data:
                user = res.data[0]
                if _check_password(password, user["password"]):
                    return {"id": user["id"],
                            "username": user["username"],
                            "role": user["role"]}
        except Exception as e:
            logger.warning(f"[Supabase login] {e}")

    # Fallback: variáveis de ambiente
    admin_pwd  = os.getenv("DUZZI_ADMIN_PASSWORD", "")
    super_pwd  = os.getenv("DUZZI_SUPER_PASSWORD", "")
    if username == "superadmin" and password == super_pwd:
        return {"id": 0, "username": "superadmin", "role": "superadmin"}
    if username == "admin" and password == admin_pwd:
        return {"id": 0, "username": "admin", "role": "admin"}
    return None


def create_user(username: str, password: str, role: str = "admin") -> bool:
    """Cria novo usuário no Supabase."""
    sb = _get_client()
    if not sb:
        return False
    try:
        hashed = _hash_password(password)
        sb.table("duzzi_users").insert({
            "username": username,
            "password": hashed,
            "role": role,
        }).execute()
        return True
    except Exception as e:
        logger.error(f"[Supabase create_user] {e}")
        return False


def list_users() -> list:
    sb = _get_client()
    if not sb:
        return []
    try:
        res = sb.table("duzzi_users")\
                .select("id,username,role,ativo,criado_em")\
                .order("criado_em", desc=True)\
                .execute()
        return res.data or []
    except Exception as e:
        logger.warning(f"[Supabase list_users] {e}")
        return []


def toggle_user(user_id: int, ativo: bool):
    sb = _get_client()
    if sb:
        try:
            sb.table("duzzi_users").update({"ativo": ativo})\
              .eq("id", user_id).execute()
        except Exception as e:
            logger.warning(f"[Supabase toggle_user] {e}")


def change_password(user_id: int, new_password: str) -> bool:
    sb = _get_client()
    if not sb: return False
    try:
        hashed = _hash_password(new_password)
        sb.table("duzzi_users").update({"password": hashed})\
          .eq("id", user_id).execute()
        return True
    except Exception as e:
        logger.warning(f"[Supabase change_password] {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LEADS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def save_lead(nome, telefone, email, escola_origem, cidade,
              top_course, score_top, compat_pct, ranking_json,
              origem="quiz") -> int:
    """Salva lead no Supabase. Fallback: SQLite local."""
    sb = _get_client()
    if sb:
        try:
            res = sb.table("leads").insert({
                "nome":                nome,
                "telefone":            telefone,
                "email":               email,
                "escola_origem":       escola_origem,
                "cidade":              cidade,
                "curso_recomendado":   top_course,
                "score_top":           score_top,
                "compatibilidade_pct": compat_pct,
                "ranking_json":        ranking_json,
                "origem":              origem,
            }).execute()
            lid = res.data[0]["id"] if res.data else 0
            logger.info(f"[Supabase] Lead {lid} salvo")
            return lid
        except Exception as e:
            logger.warning(f"[Supabase save_lead] {e}")

    return _sq_save(nome, telefone, email, escola_origem, cidade,
                    top_course, score_top, compat_pct, ranking_json, origem)


def list_leads(filtros: dict | None = None) -> list:
    """
    Lista leads com filtros opcionais.
    filtros: {"curso": str, "cidade": str, "status": str, "data_inicio": str}
    """
    sb = _get_client()
    if sb:
        try:
            q = sb.table("leads").select("*").order("criado_em", desc=True)
            if filtros:
                if filtros.get("curso"):
                    q = q.eq("curso_recomendado", filtros["curso"])
                if filtros.get("cidade"):
                    q = q.eq("cidade", filtros["cidade"])
                if filtros.get("status"):
                    q = q.eq("status", filtros["status"])
                if filtros.get("data_inicio"):
                    q = q.gte("criado_em", filtros["data_inicio"])
            res = q.execute()
            return res.data or []
        except Exception as e:
            logger.warning(f"[Supabase list_leads] {e}")
    return _sq_list()


def update_lead(lead_id: int, fields: dict):
    """Atualiza campos de um lead."""
    sb = _get_client()
    if sb:
        try:
            sb.table("leads").update(fields).eq("id", lead_id).execute()
            return
        except Exception as e:
            logger.warning(f"[Supabase update_lead] {e}")
    for field, val in fields.items():
        _sq_update(lead_id, field, val)


def mark_inscricao_aberta(lead_id: int):
    update_lead(lead_id, {"abriu_inscricao": True})

def mark_concluido(lead_id: int):
    update_lead(lead_id, {"status": "Concluído"})

def mark_descartado(lead_id: int):
    update_lead(lead_id, {"status": "Descartado"})

def delete_lead(lead_id: int):
    sb = _get_client()
    if sb:
        try:
            sb.table("leads").delete().eq("id", lead_id).execute()
            return
        except Exception as e:
            logger.warning(f"[Supabase delete_lead] {e}")
    _sq_delete(lead_id)


def get_metrics(filtros: dict | None = None) -> dict:
    from collections import Counter
    leads = list_leads(filtros)
    if not leads:
        return {"total": 0, "hoje": 0, "top_curso": "-",
                "abriram_inscricao": 0, "nao_abriram": 0,
                "concluidos": 0, "descartados": 0,
                "cursos_contagem": {}, "por_dia": {},
                "escolas": {}, "cidades": {},
                "supabase_ok": supabase_ok()}

    today  = date.today().isoformat()
    hoje   = sum(1 for l in leads if str(l.get("criado_em",""))[:10] == today)
    abriram = sum(1 for l in leads if l.get("abriu_inscricao") in (True, 1, "true", "1"))
    concluidos  = sum(1 for l in leads if l.get("status") == "Concluído")
    descartados = sum(1 for l in leads if l.get("status") == "Descartado")
    cursos  = Counter(l.get("curso_recomendado","") for l in leads)
    escolas = Counter(l.get("escola_origem","") for l in leads if l.get("escola_origem"))
    cidades = Counter(l.get("cidade","") for l in leads if l.get("cidade"))
    por_dia: dict = {}
    for l in leads:
        d = str(l.get("criado_em",""))[:10]
        if d: por_dia[d] = por_dia.get(d, 0) + 1

    return {
        "total":             len(leads),
        "hoje":              hoje,
        "top_curso":         cursos.most_common(1)[0][0] if cursos else "-",
        "abriram_inscricao": abriram,
        "nao_abriram":       len(leads) - abriram,
        "concluidos":        concluidos,
        "descartados":       descartados,
        "cursos_contagem":   dict(cursos),
        "por_dia":           por_dia,
        "escolas":           dict(escolas.most_common(10)),
        "cidades":           dict(cidades.most_common(10)),
        "supabase_ok":       supabase_ok(),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SQLite FALLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import sqlite3
from pathlib import Path

_DB = Path(__file__).parent / ".leads.db"

def _sq_init():
    conn = sqlite3.connect(_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS leads (
        id SERIAL PRIMARY KEY, nome TEXT, telefone TEXT, email TEXT,
        escola_origem TEXT, cidade TEXT, curso_recomendado TEXT,
        score_top INTEGER, compatibilidade_pct INTEGER, ranking_json TEXT,
        abriu_inscricao INTEGER DEFAULT 0, status TEXT DEFAULT 'Ativo',
        origem TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    for col, td in [("escola_origem","TEXT"),("cidade","TEXT"),
                    ("compatibilidade_pct","INTEGER"),("abriu_inscricao","INTEGER"),
                    ("status","TEXT DEFAULT 'Ativo'")]:
        try: conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {td}")
        except: pass
    conn.commit(); conn.close()

def _sq_save(nome, tel, email, escola, cidade, curso, score, compat, rjson, origem):
    _sq_init()
    conn = sqlite3.connect(_DB)
    cur = conn.execute(
        "INSERT INTO leads (nome,telefone,email,escola_origem,cidade,curso_recomendado,score_top,compatibilidade_pct,ranking_json,origem) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (nome,tel,email,escola,cidade,curso,score,compat,rjson,origem))
    lid = cur.lastrowid; conn.commit(); conn.close(); return lid

def _sq_list():
    _sq_init()
    conn = sqlite3.connect(_DB); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM leads ORDER BY criado_em DESC").fetchall()
    conn.close(); return [dict(r) for r in rows]

def _sq_update(lid, field, val):
    _sq_init(); conn = sqlite3.connect(_DB)
    conn.execute(f"UPDATE leads SET {field}=? WHERE id=?", (val,lid))
    conn.commit(); conn.close()

def _sq_delete(lid):
    _sq_init(); conn = sqlite3.connect(_DB)
    conn.execute("DELETE FROM leads WHERE id=?", (lid,))
    conn.commit(); conn.close()

# Alias para compatibilidade
def init_db(): _sq_init()
