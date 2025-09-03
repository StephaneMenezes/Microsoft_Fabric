# 🎓 Fabric Lakehouse + Streamlit — Dashboard de Alunos

> Conecta um **Lakehouse/Warehouse do Microsoft Fabric** ao **Streamlit** para análises simples e rápidas (ex.: **Alunos por Série/Idade/Status**), com gráficos, tabela e download de CSV.

## ✨ Destaques

* ⚡ Conexão ao **SQL endpoint** do Fabric via **ODBC**
* 🔐 Autenticação flexível: **Browser**, **Device Code** ou **Service Principal (SPN)**
* 📊 Gráficos e tabelas com **Plotly/Streamlit**
* 🧩 Código simples de adaptar (tabela/colunas)
* 🧯 "Troubleshooting" para erros comuns (IM002, HY000, ScriptRunContext)

---

## 🧱 Arquitetura (alto nível)

```
Streamlit (app.py)  →  utils/db.py  →  ODBC Driver 17/18  →  SQL Endpoint (Fabric)
                                         ↑
                            Autenticação AAD (Browser / Device Code / SPN)
```

---

## 📂 Estrutura do projeto

```
Fabric/
├─ app.py                  # Página Streamlit (gráficos + tabelas)
├─ utils/
│  └─ db.py                # Conexão ODBC + Autenticação AAD
├─ .streamlit/
│  ├─ secrets.toml         # ⚠️ NÃO commitar
│  └─ secrets.template.toml# Exemplo (sem credenciais)
├─ requirements.txt
└─ README.md (este arquivo)
```

---

## ✅ Pré‑requisitos

* **Python 3.12** (pyenv-win, Microsoft Store, etc.)
* **Microsoft ODBC Driver 18** (preferível) ou **17** — **x64**
* Acesso a um **Lakehouse/Warehouse** no **Microsoft Fabric** com **SQL endpoint** habilitado

> Dica: verifique os drivers disponíveis no Python:
> `python -c "import pyodbc; print(pyodbc.drivers())"`

---

## 🚀 Como rodar

1. **Instalar dependências**

```powershell
python -m pip install -r requirements.txt
```

2. **Criar segredos**
   Crie `.streamlit/secrets.toml` (ou copie do template abaixo):

```toml
# .streamlit/secrets.toml
server   = "tcp:<seu-endpoint>.datawarehouse.fabric.microsoft.com,1433"
database = "<NOME_DO_SQL_ENDPOINT>"

# um destes modos: browser | devicecode | spn
auth_mode = "browser"

# se usar SPN (opcional)
tenant_id = "<TENANT_GUID>"
client_id = "<APP_CLIENT_ID>"
client_secret = "<APP_CLIENT_SECRET>"

# opcional, só para diagnosticar TLS (remova depois)
# trust_server_certificate = true
```

3. **Iniciar o app**

```powershell
python -m streamlit run app.py
```

> Se aparecer aviso tipo *ScriptRunContext*, é porque você rodou `python app.py`. Use sempre `streamlit run`.

---

## 🔐 Modos de autenticação

* **browser**: abre o navegador para login (ideal no desenvolvimento local).
* **devicecode**: mostra um código/URL no app (útil sem navegador).
* **spn**: **Service Principal** (client\_id + client\_secret). Recomendado para automação/CI.

  * Requer App Registration no Entra ID, segredo válido e permissões no Workspace/SQL endpoint do Fabric.

> **Tenant ID**: copie em *Microsoft Entra ID → Overview → Directory (tenant) ID*.

---

## 🧪 Consultas incluídas (exemplos)

### 1) Alunos por **Série** (fixa)

```sql
SELECT
    serie AS categoria,
    COUNT(DISTINCT id) AS qtd_alunos
FROM dbo.tb_alunos
GROUP BY serie
ORDER BY qtd_alunos DESC;
```

### 2) Dinâmico por **Série/Idade/Status** (variação)

```sql
SELECT
    {dim} AS categoria,
    COUNT(DISTINCT id) AS qtd_alunos
FROM dbo.tb_alunos
GROUP BY {dim}
ORDER BY qtd_alunos DESC;
```

> Observação: se a coluna se chamar `status` e o dialeto tratar como palavra reservada, use `[status]`.

---

## 🧑‍💻 Como adaptar para suas colunas

No `app.py` altere:

```python
TABLE = "dbo.tb_alunos"
COL_ID = "id"
COL_SERIE = "serie"
COL_IDADE = "idade"
COL_STATUS = "status"  # use [status] na SQL se necessário
```

---

## 🧯 Troubleshooting

**1) `missing ScriptRunContext`**
Você rodou `python app.py`. Use: `python -m streamlit run app.py`.

**2) `IM002: Nome da fonte de dados não encontrado`**
Driver ODBC não instalado/errado (32/64). Rode:

```powershell
python -c "import pyodbc; print(pyodbc.drivers())"
```

Instale **Microsoft ODBC Driver 18 (x64)** ou use o 17 (o código detecta automaticamente).

**3) `HY000: The driver did not supply an error!`**
Com ODBC 17, o *token manual* às vezes falha. O `db.py` já tenta **fallback** para a autenticação nativa do driver.
Se persistir:

* Instale o **ODBC 18 (x64)**
* Teste temporariamente `trust_server_certificate = true`

**4) Checar rede/porta 1433**

```powershell
Test-NetConnection <seu-endpoint>.datawarehouse.fabric.microsoft.com -Port 1433
```

---

## 🔒 Segurança & Git

* **NÃO** commitar `.streamlit/secrets.toml`.
* Use um **template** versionado:

```
# .streamlit/secrets.template.toml
server   = "tcp:<seu-endpoint>.datawarehouse.fabric.microsoft.com,1433"
database = "<NOME_DO_SQL_ENDPOINT>"
auth_mode = "browser"  # ou "spn"
tenant_id = "<TENANT_GUID>"
client_id = "<APP_CLIENT_ID>"
client_secret = "<APP_CLIENT_SECRET>"
```

* Em `.gitignore`:

```
/.streamlit/secrets.toml
*.env
```

* Se já vazou segredo, **revogue/rotacione** no Entra ID e reescreva o histórico do git.

---

## 🗺️ Roadmap (idéias)

* Filtros por campus/ano letivo
* KPIs de total de alunos, turmas únicas, etc.
* Exportação para Parquet/Excel
* Deploy em Azure App Service/Container Apps com SPN

---

## 🙌 Créditos

Feito com ❤️ por quem gosta de dados + Python + Fabric.

> Qualquer dúvida, abra uma Issue ou mande um PR! 😉
