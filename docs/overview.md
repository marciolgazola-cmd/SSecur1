# SSecur1: Visao Geral de Engenharia

## Objetivo

O `SSecur1` e uma aplicacao SaaS multi-tenant focada em diagnostico de cultura de seguranca, gestao de projetos, entrevistas, formularios, planos de acao e apoio analitico com IA local.

No estado atual, o produto funciona como um monolito em `Python` com `Reflex` no frontend/backend de aplicacao e `SQLAlchemy` para persistencia em `SQLite`.

## Stack atual

| Camada | Tecnologia atual | Observacao |
| --- | --- | --- |
| UI web | `Reflex` | Renderiza a experiencia web a partir de componentes Python |
| Aplicacao | `app.py` | Estado, regras, queries e eventos concentrados em um unico arquivo principal |
| Componentes UI | `ssecur1/ui/*.py` | Camada visual modularizada por areas funcionais |
| Sessao/Auth | `ssecur1/state/session.py` | Estado base de autenticacao, navegacao e exclusoes |
| Persistencia | `SQLAlchemy ORM` | Modelos em `ssecur1/db.py` |
| Banco atual | `SQLite` | Arquivo local `ssecur1.db` |
| Build desktop | `PyInstaller` | Existe `pyinstaller.spec`, ainda sem validacao formal documentada |
| Container | `docker-compose.yml` | Ambiente simples de execucao local/containerizada |

## Modulos funcionais atualmente refletidos no codigo

- autenticacao local por email/senha;
- multi-tenancy logico por `tenant_id`;
- clientes, usuarios, tenants e papeis;
- formularios, perguntas e respostas;
- surveys e sessoes de entrevista;
- projetos, workflow boxes e plano de acao;
- tarefas do plano de acao;
- permissoes visuais por recurso;
- dashboard configuravel por caixas;
- base documental para IA, chunks e recomendacoes.

## Estado atual da arquitetura

### O que existe de forma objetiva

- Uma unica pagina principal `"/"` registrada em [app.py](/home/marcio-gazola/SSecur1/app.py), com alternancia entre landing publica e workspace autenticado.
- Um `State` central no mesmo `app.py`, apoiado por `SessionStateMixin`, concentrando:
  - regras de UI;
  - consultas no banco;
  - comandos CRUD;
  - seeds operacionais;
  - parte da logica da IA local.
- Modelos ORM em [ssecur1/db.py](/home/marcio-gazola/SSecur1/ssecur1/db.py), incluindo criacao automatica de schema e ajustes incrementais de colunas.

### O que isso implica

- O projeto e rapido para evolucao local.
- O acoplamento entre interface, regra de negocio e persistencia ainda e alto.
- A documentacao de engenharia precisa deixar claro que a aplicacao ainda nao esta separada em camadas de servico/API.

## Fluxo de inicializacao

1. O modulo [ssecur1/db.py](/home/marcio-gazola/SSecur1/ssecur1/db.py) cria todas as tabelas com `Base.metadata.create_all(bind=engine)`.
2. Em seguida executa `ensure_schema_updates()` para adicionar colunas faltantes em bancos legados.
3. Depois executa `_seed()` para garantir ao menos:
   - tenant `default`
   - usuario `admin@smartlab.com`
4. O `Reflex` sobe a app definida em [app.py](/home/marcio-gazola/SSecur1/app.py).

## Caracteristicas importantes para a operacao

- O banco atual e local e baseado em arquivo: `ssecur1.db`.
- Parte relevante do comportamento depende de dados persistidos, nao apenas de codigo.
- O modulo de IA grava metadados no banco e arquivos fisicos em `uploaded_files/`.
- Se o banco for apagado e recriado, o schema volta, mas os dados operacionais desaparecem; os arquivos em `uploaded_files/` podem continuar no disco sem referencia no banco.

## Maturidade atual

### Pontos fortes

- Base funcional ampla para um MVP SaaS.
- Multi-tenant ja refletido em quase todos os dominios.
- Estrutura suficiente para formularios, entrevistas, workflow e recomendacoes.

### Lacunas relevantes

- sem API publica versionada;
- sem trilha formal de migracoes com Alembic;
- sem documentacao operacional completa;
- sem endurecimento minimo de seguranca para producao;
- sem suite de testes automatizados no repositorio.

## Documentos complementares

- [setup.md](/home/marcio-gazola/SSecur1/docs/setup.md)
- [deploy.md](/home/marcio-gazola/SSecur1/docs/deploy.md)
- [operacao-fase1-ubuntu.md](/home/marcio-gazola/SSecur1/docs/operacao-fase1-ubuntu.md)
- [security.md](/home/marcio-gazola/SSecur1/docs/security.md)
- [code-architecture.md](/home/marcio-gazola/SSecur1/docs/code-architecture.md)
- [database.md](/home/marcio-gazola/SSecur1/docs/database.md)
