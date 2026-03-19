# Deploy e Operacao

## Estado atual

O repositorio ainda nao traz uma esteira madura de publicacao. O que existe hoje e suficiente para execucao local, empacotamento inicial e um experimento simples em container.

## Docker Compose atual

O projeto possui [docker-compose.yml](/home/marcio-gazola/SSecur1/docker-compose.yml) com um servico unico:

- imagem base `python:3.11-slim`;
- volume montando o repositorio inteiro em `/app`;
- comando instalando dependencias em runtime e subindo `reflex run --env prod`.

## Limitacoes do compose atual

- instala dependencias a cada subida do container;
- nao separa imagem de runtime e build;
- nao documenta persistencia do banco `SQLite`;
- expõe apenas a porta `3000`, enquanto o backend interno sobe em `8000`;
- nao define secrets, variaveis de ambiente, storage persistente ou healthcheck.

## Empacotamento desktop

Existe `pyinstaller.spec`, indicando intencao de gerar executavel desktop. Hoje isso deve ser tratado como trilha complementar, nao como arquitetura principal do SaaS.

## Fase 1 recomendada: servidor local Ubuntu

Para a fase atual do projeto, com apenas um cliente e duas consultoras SmartLab, a estrategia mais segura e pragmatica e:

1. manter a aplicacao web rodando em uma maquina Ubuntu central;
2. manter o banco `SQLite` local nessa mesma maquina;
3. permitir que as consultoras acessem a ferramenta pelo navegador em seus notebooks ou tablets;
4. usar `OneDrive` apenas para backup e compartilhamento de arquivos exportados.

### O que evitar nesta fase

- nao abrir o mesmo `ssecur1.db` a partir de duas maquinas via pasta sincronizada;
- nao usar `OneDrive` como storage ativo do banco;
- nao fazer merge manual de arquivos `.db` como rotina operacional.

### Variaveis de ambiente uteis

O projeto agora aceita:

- `SSECUR1_DATABASE_URL`
  - define explicitamente a URL do banco;
- `SSECUR1_DATA_DIR`
  - define um diretorio para armazenar `ssecur1.db`;
- `HOST`
  - define o host de bind do backend do Reflex no script `run_reflex.sh`.

### Exemplo de subida no Ubuntu como host central

```bash
mkdir -p ~/smartlab-ssecur1-data
export SSECUR1_DATA_DIR=~/smartlab-ssecur1-data
export HOST=0.0.0.0
export FRONTEND_PORT=3010
export BACKEND_PORT=8010
./run_reflex.sh
```

### Acesso das consultoras

- notebooks: recomendado como canal principal;
- iPad/tablet: aceitavel para entrevistas e formularios, desde que a rede esteja estavel;
- celular: apenas apoio, nao recomendado como estacao principal.

### Operacao diaria recomendada

1. subir a aplicacao no Ubuntu;
2. manter o banco local fora do diretorio do codigo;
3. acessar pela URL `http://IP_DO_SERVIDOR:3010`;
4. ao fim do dia, copiar backup do banco para `OneDrive`;
5. manter `uploaded_files/` tambem em rotina de backup.

## Recomendacao objetiva de deploy

Para um ambiente SaaS serio:

1. containerizar a aplicacao de forma reprodutivel;
2. remover `SQLite` como banco principal de producao;
3. usar banco gerenciado;
4. externalizar secrets;
5. separar armazenamento de arquivos enviados;
6. adicionar observabilidade minima.

## Estrategia sugerida para Azure

### Aplicacao

- `Azure App Service` ou `Azure Container Apps` para a app web;
- imagem versionada em registry;
- variaveis de ambiente por ambiente;
- deployment por pipeline.

### Banco

- `PostgreSQL` gerenciado no Azure como destino preferencial para producao;
- migracoes formais com Alembic;
- backup, restore e observabilidade no servico gerenciado.

### Arquivos

- substituir `uploaded_files/` local por storage persistente;
- manter referencia no banco para os metadados e em storage para o binario.

## Runbook minimo recomendado

### Backup atual do banco SQLite

```bash
cp ssecur1.db ssecur1.db.bak
```

### Restauracao

```bash
cp ssecur1.db.bak ssecur1.db
```

### Impacto de apagar o banco

Ao remover `ssecur1.db`:

- todas as tabelas e registros atuais somem;
- o sistema recria o schema automaticamente na proxima subida;
- o seed minimo volta a existir;
- os arquivos em `uploaded_files/` podem permanecer no disco, mas ficam sem referencia se o banco sumir.

## Checklist antes de publicar

- migrar para `PostgreSQL`;
- proteger senhas com hash forte;
- revisar integridade referencial;
- criar estrategia formal para migracoes;
- definir storage persistente para uploads;
- documentar e automatizar backup/restore;
- criar validacao de smoke test e healthcheck.
