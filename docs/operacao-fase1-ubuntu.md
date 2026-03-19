# Operacao Fase 1: Ubuntu como Servidor Local

## Objetivo

Este guia descreve a operacao recomendada para a fase atual do `SSecur1`:

- aplicacao web rodando em um `Ubuntu` central;
- banco `SQLite` local na maquina do responsavel;
- acesso remoto das consultoras pelo navegador;
- backup diario para pasta compartilhada ou `OneDrive`.

Esse modelo atende a etapa atual de uso restrito, sem transformar a pasta sincronizada em banco ativo.

## Arquitetura recomendada

### Host central

- 1 maquina `Ubuntu` fica ligada durante o expediente;
- nela rodam:
  - frontend `Reflex`;
  - backend `Reflex`;
  - banco local `SQLite`;
  - arquivos enviados em `uploaded_files/`.

### Clientes de acesso

- notebooks: canal principal;
- tablet/iPad: aceitavel para entrevistas e formularios;
- celular: apenas apoio, nao recomendado como dispositivo principal.

### Armazenamento

- banco ativo: local no `Ubuntu`;
- uploads ativos: local no `Ubuntu`;
- backup: copia para `OneDrive`, pasta compartilhada ou disco externo.

## Estrutura sugerida no Ubuntu

```text
~/SSecur1/
~/smartlab-ssecur1-data/
~/smartlab-ssecur1-backups/
```

### Responsabilidade de cada pasta

- `~/SSecur1/`
  - codigo-fonte da aplicacao.
- `~/smartlab-ssecur1-data/`
  - banco `ssecur1.db`;
  - idealmente tambem a base de dados operacional persistente da fase 1.
- `~/smartlab-ssecur1-backups/`
  - copias datadas do banco e dos arquivos.

## Subida recomendada

No host Ubuntu:

```bash
cd ~/SSecur1
source .venv/bin/activate
mkdir -p ~/smartlab-ssecur1-data
export SSECUR1_DATA_DIR=~/smartlab-ssecur1-data
export HOST=0.0.0.0
export FRONTEND_PORT=3010
export BACKEND_PORT=8010
./run_reflex.sh
```

## Como as consultoras acessam

### Mesma rede local

As consultoras acessam:

```text
http://IP_DO_UBUNTU:3010
```

Exemplo:

```text
http://192.168.0.25:3010
```

### Fora da mesma rede

Nao exponha a porta diretamente na internet.

Use uma destas alternativas:

- `Tailscale`;
- `VPN`;
- `RDP`/acesso remoto controlado no host;
- tunel privado administrado pela SmartLab.

## Checklist antes do uso diario

1. confirmar que o host Ubuntu esta ligado;
2. confirmar que o `run_reflex.sh` esta em execucao;
3. validar acesso local em `http://127.0.0.1:3010`;
4. validar acesso remoto pelo IP do host;
5. confirmar que `~/smartlab-ssecur1-data/ssecur1.db` existe;
6. confirmar espaco livre em disco;
7. confirmar que o backup do dia anterior foi gerado.

## Checklist de campo para as consultoras

1. abrir a aplicacao no notebook;
2. confirmar login correto;
3. validar projeto e cliente antes de iniciar entrevista;
4. ao encerrar cada entrevista, confirmar persistencia da resposta;
5. em caso de tablet, validar conexao de rede antes de iniciar coleta longa.

## Checklist de encerramento do dia

1. encerrar entrevistas em andamento;
2. validar se o banco foi atualizado no dia;
3. executar backup local;
4. copiar backup para `OneDrive` ou pasta compartilhada;
5. copiar `uploaded_files/` se houver novos documentos relevantes;
6. registrar incidentes operacionais do dia.

## Backup recomendado

### Banco

Gerar uma copia datada do `SQLite`:

```bash
mkdir -p ~/smartlab-ssecur1-backups
cp ~/smartlab-ssecur1-data/ssecur1.db ~/smartlab-ssecur1-backups/ssecur1_$(date +%Y%m%d_%H%M%S).db
```

### Uploads

Opcionalmente, salvar tambem os arquivos enviados:

```bash
tar -czf ~/smartlab-ssecur1-backups/uploaded_files_$(date +%Y%m%d_%H%M%S).tar.gz ~/SSecur1/uploaded_files
```

## Restauracao rapida

Com a aplicacao parada:

```bash
cp ~/smartlab-ssecur1-backups/NOME_DO_BACKUP.db ~/smartlab-ssecur1-data/ssecur1.db
```

Depois, subir novamente a aplicacao.

## O que nao fazer

- nao colocar o `.db` ativo dentro do `OneDrive`;
- nao deixar duas pessoas editando o mesmo `.db` por compartilhamento de arquivo;
- nao sincronizar o `.db` por ferramenta de sync enquanto a aplicacao estiver rodando;
- nao usar celular como dispositivo principal de coleta;
- nao expor a porta do app diretamente na internet sem camada de seguranca.

## Caminho para a fase 2

Quando a SmartLab evoluir para SaaS real, o proximo passo natural e:

1. migrar de `SQLite` para `PostgreSQL`;
2. mover uploads para storage persistente dedicado;
3. publicar em infraestrutura de servidor;
4. adotar backup, observabilidade e seguranca de nivel producao.
