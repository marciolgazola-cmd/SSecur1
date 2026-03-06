# SSecur1 (Reflex)

SaaS multi-tenant em Reflex com:
- Landing pública premium (dark + glassmorphism)
- Auth (login/registro em modal full-screen)
- RBAC (`admin`, `editor`, `viewer`)
- CRUD isolado por tenant: clientes, tenants, papéis, responsabilidades
- Formulários de diagnóstico (perguntas abertas/fechadas)
- Dashboard configurável por "Caixas" (widgets low-code por perfil)
- Gestão de projetos com workflow de "Caixas" (builder visual sequencial)
- Plano de ação em estilo Kanban (A Fazer, Em Andamento, Concluído)
- Permissões visuais por colaborador com "Caixas de Recurso"
- Assistente IA (orientação prática para tomada de decisão)

## 1) Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2) Corrigir PPA quebrado (se `apt update` reclamar de openrgb)

```bash
sudo mv /etc/apt/sources.list.d/thopiekar-ubuntu-openrgb-noble.sources \
  /etc/apt/sources.list.d/thopiekar-ubuntu-openrgb-noble.sources.disabled
sudo apt update
```

## 3) Rodar local (sem Bun, usando npm)

```bash
./run_reflex.sh
```

Ou manualmente:

```bash
source .venv/bin/activate
export REFLEX_USE_NPM=true
export NPM_CONFIG_CACHE="$PWD/.npm-cache"
python -m reflex run --frontend-port 3010 --backend-port 8010
```

## 4) Exportar build web

```bash
./export_reflex.sh
```

Ou manualmente:

```bash
source .venv/bin/activate
export REFLEX_USE_NPM=true
python -m reflex export
```

## 5) Docker

```bash
docker compose up
```

## 6) Build `.exe` (Windows)

```bash
pip install pyinstaller
pyinstaller pyinstaller.spec
```

## Credenciais seed

- Email: `admin@smartlab.com`
- Senha: `admin123`
- Papel: `admin`

Banco local SQLite: `ssecur1.db`.
