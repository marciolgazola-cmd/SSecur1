# Setup de Desenvolvimento

## Requisitos

- `python3`
- ambiente virtual `venv`
- `npm` disponivel, porque o projeto usa `REFLEX_USE_NPM=true`
- sistema com portas livres para frontend e backend

## Instalacao local

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Execucao local recomendada

Use o script do projeto:

```bash
./run_reflex.sh
```

O script:

- ativa `.venv`;
- configura `REFLEX_USE_NPM=true`;
- usa cache local em `.npm-cache`;
- encerra processos que estiverem ocupando as portas configuradas;
- sobe o app com `Reflex`.

## Execucao como host local para consultoras

Para a fase 1, quando a maquina `Ubuntu` do operador ficar como servidor local do time:

```bash
mkdir -p ~/smartlab-ssecur1-data
export SSECUR1_DATA_DIR=~/smartlab-ssecur1-data
export HOST=0.0.0.0
export FRONTEND_PORT=3010
export BACKEND_PORT=8010
./run_reflex.sh
```

Guia operacional detalhado:

- [operacao-fase1-ubuntu.md](/home/marcio-gazola/SSecur1/docs/operacao-fase1-ubuntu.md)

## Execucao manual

```bash
source .venv/bin/activate
export REFLEX_USE_NPM=true
export NPM_CONFIG_CACHE="$PWD/.npm-cache"
python -m reflex run --frontend-port 3010 --backend-port 8010
```

## Build web exportada

```bash
./export_reflex.sh
```

Ou:

```bash
source .venv/bin/activate
export REFLEX_USE_NPM=true
python -m reflex export
```

## Credenciais seed

Se o banco for inicializado vazio, o codigo cria automaticamente:

- email: `admin@smartlab.com`
- senha: `admin123`
- tenant: `default`
- role: `admin`

Isso acontece em [ssecur1/db.py](/home/marcio-gazola/SSecur1/ssecur1/db.py), na funcao `_seed()`.

## Banco local

- Arquivo: `ssecur1.db`
- Engine atual: `SQLite`
- Criado/ajustado automaticamente ao importar `ssecur1.db`
- Pode ser externalizado para outro diretorio com `SSECUR1_DATA_DIR`

## Observacoes praticas

- O arquivo `requirements.txt` hoje contem `reflex` duplicado. Isso nao bloqueia o setup, mas deve ser tratado como inconsistencia de manutencao.
- Nao ha, no repositorio atual, uma trilha formal de migracoes com `alembic` mesmo o pacote estando listado.
- Apagar `ssecur1.db` zera os dados operacionais e recria apenas schema + seed minimo na proxima inicializacao.

## Troubleshooting rapido

### Porta ocupada

O proprio `run_reflex.sh` tenta matar processos nas portas do frontend/backend.

### Banco aparentemente inconsistente

1. faça backup de `ssecur1.db`;
2. valide o schema atual contra [database.md](/home/marcio-gazola/SSecur1/docs/database.md);
3. lembre que `ensure_schema_updates()` adiciona colunas, mas nao executa migracoes estruturais completas.

### `python` nao encontrado

Em alguns ambientes, use `python3` fora da `.venv`.
