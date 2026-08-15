"""
github_sync.py — Comita arquivos direto no repositório GitHub via API.
Usado pelo admin_panel.py para tornar a atualização de courses.json
(via scraping) permanente sem precisar de download/upload manual.

Requer duas variáveis de ambiente / secrets do Streamlit Cloud:
    GITHUB_TOKEN  -> Personal Access Token com permissão de escrita (repo)
    GITHUB_REPO   -> "usuario/repositorio", ex: "samysruiz/duzziorienta"

Opcional:
    GITHUB_BRANCH -> branch de destino (padrão: "main")
"""

import base64
import os

import requests

API_BASE = "https://api.github.com"


def github_configured() -> bool:
    return bool(os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_REPO"))


def commit_file_to_github(path: str, content: str, message: str) -> dict:
    """
    Cria ou atualiza um arquivo no repositório configurado.
    `path` é o caminho do arquivo dentro do repo (ex: "courses.json").
    `content` é o conteúdo texto (será convertido pra base64 automaticamente).
    Retorna {"ok": True, "url": ...} ou {"ok": False, "error": ...}.
    """
    token  = os.getenv("GITHUB_TOKEN", "")
    repo   = os.getenv("GITHUB_REPO", "")
    branch = os.getenv("GITHUB_BRANCH", "main")

    if not token or not repo:
        return {"ok": False, "error": "GITHUB_TOKEN ou GITHUB_REPO não configurados nos Secrets."}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    url = f"{API_BASE}/repos/{repo}/contents/{path}"

    # 1) Busca o sha atual do arquivo (se existir), necessário pra "atualizar"
    sha = None
    try:
        r_get = requests.get(url, headers=headers, params={"ref": branch}, timeout=15)
        if r_get.status_code == 200:
            sha = r_get.json().get("sha")
        elif r_get.status_code not in (404,):
            return {"ok": False, "error": f"Erro ao consultar arquivo atual ({r_get.status_code}): {r_get.text[:200]}"}
    except requests.RequestException as e:
        return {"ok": False, "error": f"Falha de conexão ao consultar GitHub: {e}"}

    # 2) Faz o commit (create ou update)
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    try:
        r_put = requests.put(url, headers=headers, json=payload, timeout=15)
    except requests.RequestException as e:
        return {"ok": False, "error": f"Falha de conexão ao comitar: {e}"}

    if r_put.status_code in (200, 201):
        commit_url = r_put.json().get("commit", {}).get("html_url", "")
        return {"ok": True, "url": commit_url}

    return {"ok": False, "error": f"Erro do GitHub ({r_put.status_code}): {r_put.text[:300]}"}
