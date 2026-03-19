# Arquitetura do Codigo

## Visao geral

O projeto segue uma arquitetura ainda concentrada em `State`, com `Reflex` como framework de interface e `SQLAlchemy` como ORM, mas o monolito original ja foi parcialmente quebrado em mixins por dominio. O ponto de composicao continua em [app.py](/home/marcio-gazola/SSecur1/app.py), enquanto regras especificas ja foram separadas em modulos de estado.

## Estrutura principal

| Caminho | Papel |
| --- | --- |
| [app.py](/home/marcio-gazola/SSecur1/app.py) | composicao principal da aplicacao, registro da pagina, fachada do `State` e integracao entre dominios |
| [ssecur1/catalogs.py](/home/marcio-gazola/SSecur1/ssecur1/catalogs.py) | catalogos, templates, baselines de permissao, estagios de workflow e constantes de dominio compartilhadas |
| [ssecur1/db.py](/home/marcio-gazola/SSecur1/ssecur1/db.py) | modelos ORM, engine, sessao, criacao de schema e seed |
| [ssecur1/state/session.py](/home/marcio-gazola/SSecur1/ssecur1/state/session.py) | mixin de sessao, autenticacao, navegacao e exclusoes |
| [ssecur1/state/access.py](/home/marcio-gazola/SSecur1/ssecur1/state/access.py) | mixin de acesso e governanca: RBAC, canvas de permissao, templates, visibilidade de menu e acoes de liberacao |
| [ssecur1/state/dashboard.py](/home/marcio-gazola/SSecur1/ssecur1/state/dashboard.py) | mixin do Dashboard: filtros, agregacoes, cards, drill-down e timelines |
| [ssecur1/state/assistant.py](/home/marcio-gazola/SSecur1/ssecur1/state/assistant.py) | mixin do Especialista IA e Auditoria: RAG, chat, recomendacoes, documentos e trilha de auditoria |
| [ssecur1/state/forms.py](/home/marcio-gazola/SSecur1/ssecur1/state/forms.py) | mixin de Formularios e Entrevistas: builder, perguntas, sessoes, respostas e contexto operacional |
| [ssecur1/state/projects.py](/home/marcio-gazola/SSecur1/ssecur1/state/projects.py) | mixin de Projetos, Workflow e Planos: portfolio, jornadas, sticky notes, planos de acao, tarefas e agregacoes operacionais |
| [ssecur1/state/admin.py](/home/marcio-gazola/SSecur1/ssecur1/state/admin.py) | mixin de Administracao e Cadastros: clientes, usuarios, tenants, papeis, responsabilidades e permissoes |
| [ssecur1/ui/composition.py](/home/marcio-gazola/SSecur1/ssecur1/ui/composition.py) | composicao da UI principal, factories de views e integracao entre shell, cards e telas funcionais |
| [ssecur1/ui/page.py](/home/marcio-gazola/SSecur1/ssecur1/ui/page.py) | montagem da pagina principal |
| [ssecur1/ui/shell.py](/home/marcio-gazola/SSecur1/ssecur1/ui/shell.py) | componentes de shell e views de IA |
| `ssecur1/ui/*.py` | componentes por modulo funcional |
| [rxconfig.py](/home/marcio-gazola/SSecur1/rxconfig.py) | configuracao do app Reflex |

## Composicao do State

O `State` principal agora e montado por heranca de mixins:

- [AssistantStateMixin](/home/marcio-gazola/SSecur1/ssecur1/state/assistant.py)
- [AccessStateMixin](/home/marcio-gazola/SSecur1/ssecur1/state/access.py)
- [AdminStateMixin](/home/marcio-gazola/SSecur1/ssecur1/state/admin.py)
- [DashboardStateMixin](/home/marcio-gazola/SSecur1/ssecur1/state/dashboard.py)
- [FormStateMixin](/home/marcio-gazola/SSecur1/ssecur1/state/forms.py)
- [ProjectStateMixin](/home/marcio-gazola/SSecur1/ssecur1/state/projects.py)
- [SessionStateMixin](/home/marcio-gazola/SSecur1/ssecur1/state/session.py)

Na pratica:

- os mixins concentram regras, consultas ORM, calculos e handlers de dominio;
- [app.py](/home/marcio-gazola/SSecur1/app.py) continua expondo wrappers explicitos para compatibilidade com o `Reflex`, especialmente em `@rx.var` e eventos `on_change`;
- catalogos compartilhados e baselines de permissao sairam do `State` e agora ficam em [ssecur1/catalogs.py](/home/marcio-gazola/SSecur1/ssecur1/catalogs.py);
- a composicao visual principal saiu do modulo principal e agora fica em [ssecur1/ui/composition.py](/home/marcio-gazola/SSecur1/ssecur1/ui/composition.py).

## Como a aplicacao sobe

1. `Reflex` importa o modulo principal configurado em [rxconfig.py](/home/marcio-gazola/SSecur1/rxconfig.py).
2. [app.py](/home/marcio-gazola/SSecur1/app.py) registra uma unica pagina `"/"`.
3. A pagina principal alterna entre:
   - landing publica;
   - workspace autenticado.
4. O estado do usuario e da sessao determina qual view fica visivel.

## Organizacao funcional observada

### Dominio administrativo

- tenants
- usuarios
- clientes
- papeis
- responsabilidades
- permissoes

### Dominio de diagnostico

- formularios
- perguntas
- respostas
- surveys
- sessoes de entrevista

### Dominio operacional

- projetos
- workflow boxes
- action plans
- action tasks

### Dominio de IA e Auditoria

- documentos da base da IA
- chunks indexados para RAG
- conversas persistidas
- recomendacoes geradas
- trilha de auditoria de respostas e eventos

## Padrao de acesso a dados

Os mixins e handlers ainda abrem sessoes ORM diretamente com `SessionLocal()`. A extracao melhorou a separacao por dominio, mas ainda nao introduziu uma camada dedicada de servicos/repositorios. Isso mantem alguns efeitos:

- consultas dispersas entre mixins de estado;
- mistura entre estado de interface e persistencia;
- maior custo para testar de forma isolada;
- maior risco de regressao ao evoluir schema e fluxos.

## Estado atual da refatoracao

O projeto ja saiu do formato de arquivo unico puro, mas ainda nao terminou a migracao arquitetural. Hoje o estado pode ser resumido assim:

- concluido:
  - acesso, governanca e permissões em [access.py](/home/marcio-gazola/SSecur1/ssecur1/state/access.py)
  - administracao e cadastros em [admin.py](/home/marcio-gazola/SSecur1/ssecur1/state/admin.py)
  - sessao/autenticacao em [session.py](/home/marcio-gazola/SSecur1/ssecur1/state/session.py)
  - dashboard em [dashboard.py](/home/marcio-gazola/SSecur1/ssecur1/state/dashboard.py)
  - especialista IA e auditoria em [assistant.py](/home/marcio-gazola/SSecur1/ssecur1/state/assistant.py)
  - formularios e entrevistas em [forms.py](/home/marcio-gazola/SSecur1/ssecur1/state/forms.py)
  - projetos, workflow e planos em [projects.py](/home/marcio-gazola/SSecur1/ssecur1/state/projects.py)
- remanescente em [app.py](/home/marcio-gazola/SSecur1/app.py):
  - composicao do `State`
  - wrappers explicitos exigidos pelo `Reflex`
  - registro de pagina e integracao final entre dominios

O objetivo recomendado das proximas rodadas e repetir o mesmo padrao para esses dominios restantes, ate que [app.py](/home/marcio-gazola/SSecur1/app.py) fique focado em composicao e nao em regra de negocio.

## Persistencia e schema

O schema e definido em [ssecur1/db.py](/home/marcio-gazola/SSecur1/ssecur1/db.py). O bootstrap atual depende de:

- `Base.metadata.create_all(bind=engine)`;
- `ensure_schema_updates()`;
- `_seed()`.

Isso significa que o proprio runtime faz parte da estrategia de manutencao do banco.

## Caracteristicas arquiteturais importantes

### Multi-tenancy

Quase todas as entidades usam `tenant_id`, indicando isolamento logico no mesmo banco.

### JSON em `TEXT`

Varios recursos dinamicos usam `TEXT` com serializacao JSON, como:

- `workflow_boxes.config_json`
- `dashboard_boxes.config_json`
- `questions.options_json`
- `action_plans.task_items_json`
- `interview_sessions.dimension_scores_json`
- `assistant_chunks.embedding_json`

### Uploads e IA

Os arquivos enviados ficam fora do banco, em disco, e os metadados ficam em `assistant_documents`. O conteudo processado e armazenado em `assistant_chunks`.

## Principais limitacoes da arquitetura atual

- `app.py` muito grande e com responsabilidades demais;
- ausencia de camada de servicos;
- ausencia de API publica;
- ausencia de migracoes formais;
- dependencia de `SQLite` local;
- seguranca ainda insuficiente para producao.

## Refatoracao natural recomendada

1. extrair servicos por dominio;
2. isolar repositores/queries do estado de UI;
3. introduzir migracoes formais;
4. separar configuracao por ambiente;
5. preparar adaptacao para `PostgreSQL`.
