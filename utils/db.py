# utils/db.py
import pyodbc
import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional
import msal  # mantemos para login interativo quando não for SPN

SCOPE = ["https://database.windows.net//.default"]

# ===== Logins de usuário (quando NÃO for SPN) =====
def _get_access_token_interactive(tenant_id: str, client_id: Optional[str] = None) -> str:
    """Login interativo abrindo o navegador."""
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.PublicClientApplication(client_id or "04b07795-8ddb-461a-bbee-02f9e1bf7b46", authority=authority)
    result = app.acquire_token_interactive(scopes=SCOPE, prompt="select_account")
    if "access_token" not in result:
        raise RuntimeError(f"MSAL não retornou access_token. Detalhes: {result}")
    return result["access_token"]

def _get_access_token_devicecode(tenant_id: str, client_id: Optional[str] = None) -> str:
    """Login via device code (mostra código/URL no app)."""
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.PublicClientApplication(client_id or "04b07795-8ddb-461a-bbee-02f9e1bf7b46", authority=authority)
    flow = app.initiate_device_flow(scopes=SCOPE)
    if "user_code" not in flow:
        raise RuntimeError(f"Falha ao iniciar device flow. Resposta: {flow}")
    st.info(f"📲 Acesse {flow['verification_uri']} e entre com o código: **{flow['user_code']}**")
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"MSAL não retornou access_token (devicecode). Detalhes: {result}")
    return result["access_token"]

# ===== Util =====
def _normalize_server(server: str) -> str:
    sv = server.strip()
    if not sv.lower().startswith("tcp:"):
        sv = f"tcp:{sv}"
    if "," not in sv:
        sv = f"{sv},1433"
    return sv

def _pick_driver() -> str:
    installed = list(pyodbc.drivers())
    for d in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server Native Client 11.0", "SQL Server"]:
        if d in installed:
            return d
    raise RuntimeError(
        "Nenhum driver ODBC do SQL Server encontrado.\n"
        f"Drivers instalados: {installed}\n"
        "Instale o 'Microsoft ODBC Driver 18 for SQL Server (x64)' ou o 17."
    )

@st.cache_resource(show_spinner=False)
def get_conn() -> pyodbc.Connection:
    cfg = st.secrets
    server   = cfg["server"]
    database = cfg["database"]
    tenant_id = cfg.get("tenant_id", "")
    client_id = cfg.get("client_id", "")
    client_secret = cfg.get("client_secret", "")
    auth_mode = cfg.get("auth_mode", "spn").lower()  # padrão: spn (como seu exemplo)
    trust_sc = bool(cfg.get("trust_server_certificate", False))

    sv = _normalize_server(server)
    driver = _pick_driver()

    # ===== Caminho A: Service Principal via ODBC (igual ao seu exemplo) =====
    if auth_mode == "spn":
        # IMPORTANTE: não use attrs_before/token aqui. Deixe o ODBC autenticar com AAD SPN.
        conn_str = (
            "Driver={" + driver + "};"
            f"Server={sv};"
            f"Database={database};"
            "Encrypt=yes;"
            f"TrustServerCertificate={'yes' if trust_sc else 'no'};"
            "Authentication=ActiveDirectoryServicePrincipal;"
            f"UID={client_id};"
            f"PWD={client_secret};"
        )
        # Opcional: informar o tenant explicitamente (alguns ambientes exigem)
        if tenant_id:
            conn_str += f"Authority Id={tenant_id};"

        try:
            return pyodbc.connect(conn_str, timeout=30)
        except Exception as e:
            raise RuntimeError(
                "Falha ao conectar com Service Principal via ODBC.\n"
                f"Driver: {driver}\nServer: {sv}\nDatabase: {database}\n"
                "Dicas:\n"
                "- Confirme client_id/client_secret/tenant_id do App Registration (Entra ID).\n"
                "- O SPN precisa ter acesso ao Workspace/SQL endpoint no Fabric.\n"
                "- Teste 'trust_server_certificate=true' para diagnosticar TLS (remova depois).\n"
                f"Erro: {e}"
            )

    # ===== Caminho B: Login de usuário (browser/devicecode) usando access token =====
    if auth_mode in ("browser", "interactive"):
        token = _get_access_token_interactive(tenant_id, client_id)
        auth_kw = "ActiveDirectoryInteractive"
    elif auth_mode == "devicecode":
        token = _get_access_token_devicecode(tenant_id, client_id)
        auth_kw = "ActiveDirectoryDeviceCode"
    else:
        raise ValueError('auth_mode inválido. Use "spn", "browser" (interactive) ou "devicecode".')

    # Conexão ODBC com token (para browser/devicecode)
    base_conn_str = (
        "Driver={" + driver + "};"
        f"Server={sv};"
        f"Database={database};"
        "Encrypt=yes;"
        f"TrustServerCertificate={'yes' if trust_sc else 'no'};"
        "Connection Timeout=30;"
    )
    token_bytes = token.encode("utf-16le")  # 1256 = SQL_COPT_SS_ACCESS_TOKEN
    try:
        return pyodbc.connect(base_conn_str, attrs_before={1256: token_bytes})
    except Exception as e:
        # Fallback: alguns ambientes com ODBC 17 dão HY000 com token manual.
        # Tentamos a autenticação nativa do driver (sem token).
        try:
            fallback_conn_str = base_conn_str + f"Authentication={auth_kw};"
            st.warning("Tentando fallback com autenticação nativa do driver (sem token manual)...")
            return pyodbc.connect(fallback_conn_str)
        except Exception as e2:
            raise RuntimeError(
                "Falha ao conectar com access token pelo ODBC E no fallback nativo do driver.\n"
                f"Driver: {driver}\nServer: {sv}\nDatabase: {database}\n"
                f"Tentativas: attrs_before=token e Authentication={auth_kw}\n"
                "Dicas:\n"
                "- Confirme o formato do 'server' (tcp:... ,1433).\n"
                "- Instale o ODBC Driver 18 (x64) para melhor compatibilidade.\n"
                "- Se for TLS/certificado, teste 'trust_server_certificate=true' temporariamente.\n"
                f"Erro token: {e}\nErro fallback: {e2}"
            )

@st.cache_data(ttl=300, show_spinner=False)
def run_query(sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    conn = get_conn()
    return pd.read_sql(sql, conn, params=params) if params else pd.read_sql(sql, conn)
