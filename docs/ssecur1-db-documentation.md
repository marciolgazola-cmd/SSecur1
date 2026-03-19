# Documento Substituido

Este arquivo foi substituido por [database.md](/home/marcio-gazola/SSecur1/docs/database.md), que passa a ser a referencia principal e mais completa para:

- motores de banco usados e recomendados;
- entidades e atributos;
- PK, FK e relacionamentos;
- campos JSON serializados;
- comportamento de recriacao do `ssecur1.db`;
- exemplos reais de dados armazenados.

O conteudo historico abaixo foi mantido apenas como registro da analise anterior.

# Documentacao Tecnica do Banco `ssecur1.db`

Data da analise: 2026-03-13
Arquivo analisado: `/home/marcio-gazola/SSecur1/ssecur1.db`
Motor: SQLite

## 1. Visao geral

O banco modela uma aplicacao multi-tenant para diagnostico e gestao de cultura de seguranca, com modulos para:

- cadastro de tenants, usuarios e clientes;
- projetos e planos de acao;
- formularios, perguntas e respostas;
- papeis, responsabilidades e permissoes;
- configuracao de dashboard e workflow por tenant/projeto.

## 2. Entidades encontradas

- `tenants`
- `users`
- `clients`
- `projects`
- `workflow_boxes`
- `action_plans`
- `forms`
- `questions`
- `responses`
- `roles`
- `responsibilities`
- `permission_boxes`
- `dashboard_boxes`

## 3. Chaves, restricoes e dependencias

### 3.1 Chaves primarias

- `action_plans.id`
- `clients.id`
- `dashboard_boxes.id`
- `forms.id`
- `permission_boxes.id`
- `projects.id`
- `questions.id`
- `responses.id`
- `responsibilities.id`
- `roles.id`
- `tenants.id`
- `users.id`
- `workflow_boxes.id`

### 3.2 Chaves unicas / alternativas

- `tenants.slug` possui restricao `UNIQUE`
- `users.email` possui restricao `UNIQUE`

### 3.3 Chaves estrangeiras explicitas

- `action_plans.tenant_id -> tenants.id`
- `action_plans.project_id -> projects.id`
- `clients.tenant_id -> tenants.id`
- `dashboard_boxes.tenant_id -> tenants.id`
- `forms.tenant_id -> tenants.id`
- `permission_boxes.tenant_id -> tenants.id`
- `projects.tenant_id -> tenants.id`
- `questions.form_id -> forms.id`
- `questions.tenant_id -> tenants.id`
- `responses.form_id -> forms.id`
- `responses.question_id -> questions.id`
- `responses.tenant_id -> tenants.id`
- `responsibilities.tenant_id -> tenants.id`
- `responsibilities.role_id -> roles.id`
- `roles.tenant_id -> tenants.id`
- `users.tenant_id -> tenants.id`
- `workflow_boxes.tenant_id -> tenants.id`
- `workflow_boxes.project_id -> projects.id`

### 3.4 Relacionamentos mestre-detalhe

- `tenants` e a entidade mestre principal do banco. Quase todas as tabelas dependem dela.
- `projects` e mestre de `workflow_boxes` e `action_plans`.
- `forms` e mestre de `questions` e tambem referenciado por `responses`.
- `questions` e mestre de `responses`.
- `roles` e mestre de `responsibilities`.

### 3.5 Relacionamentos implicitos nao garantidos por FK

As relacoes abaixo parecem existir pela semantica dos dados, mas nao sao protegidas por chave estrangeira:

- `users.role` parece representar o nome textual de um papel, mas nao referencia `roles.id` nem `roles.name`.
- `permission_boxes.user_email` parece apontar para `users.email` ou `clients.email`, mas nao possui FK.
- `dashboard_boxes.role_scope` parece representar um escopo/perfil de acesso, mas nao referencia `roles`.

### 3.6 Escravo / detalhe

Se a nomenclatura "mestre/escravo" for interpretada como "pai/filho" ou "master/detail", o mapeamento atual e:

- `tenants` -> `users`, `clients`, `projects`, `forms`, `questions`, `responses`, `roles`, `responsibilities`, `permission_boxes`, `dashboard_boxes`, `workflow_boxes`, `action_plans`
- `projects` -> `workflow_boxes`, `action_plans`
- `forms` -> `questions`, `responses`
- `questions` -> `responses`
- `roles` -> `responsibilities`

Observacao: o banco nao define nenhuma configuracao de replicacao, publicacao/assinatura ou escravo no sentido de infraestrutura. Aqui so existe hierarquia de dados.

## 4. Cardinalidade observada

| Tabela | Registros |
| --- | ---: |
| `action_plans` | 3 |
| `clients` | 5 |
| `dashboard_boxes` | 3 |
| `forms` | 6 |
| `permission_boxes` | 2 |
| `projects` | 3 |
| `questions` | 3 |
| `responses` | 2 |
| `responsibilities` | 0 |
| `roles` | 2 |
| `tenants` | 3 |
| `users` | 2 |
| `workflow_boxes` | 9 |

## 5. Dicionario de dados por entidade

## 5.1 `tenants`

Finalidade inferida: cadastro das organizacoes/ambientes isolados do sistema.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `VARCHAR` | PK, NOT NULL | identificador tecnico do tenant | `default`, `consultoria-de-negocios`, `consultoria` |
| `name` | `VARCHAR` | NOT NULL | nome exibido da empresa/tenant | `SmartLab Demo`, `i9Exp` |
| `slug` | `VARCHAR` | NOT NULL, UNIQUE | identificador amigavel/slug | `smartlab`, `Consultoria de Negocios`, `consultoria` |
| `limit_users` | `INTEGER` | opcional | limite de usuarios permitido | `150`, `50` |
| `created_at` | `DATETIME` | opcional | data/hora de criacao do tenant | `2026-03-04 02:27:59.415780` |

Amostra de dados:

| id | name | slug | limit_users | created_at |
|---|---|---|---:|---|
| `default` | `SmartLab Demo` | `smartlab` | 150 | `2026-03-04 02:27:59.415780` |
| `consultoria-de-negocios` | `i9Exp` | `Consultoria de Negocios` | 50 | `2026-03-04 15:25:18.209119` |
| `consultoria` | `i9Exp` | `consultoria` | 50 | `2026-03-05 20:07:28.436275` |

Dependencias:

- pai de praticamente todo o restante do modelo.

## 5.2 `users`

Finalidade inferida: usuarios internos do sistema autenticados por email e senha.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador do usuario | `1`, `2` |
| `name` | `VARCHAR` | NOT NULL | nome do usuario | `Admin SmartLab`, `Marcio Gazola` |
| `email` | `VARCHAR` | NOT NULL, UNIQUE | login/contato do usuario | `admin@smartlab.com`, `marciol.gazola@gmail.com` |
| `password` | `VARCHAR` | NOT NULL | senha armazenada em texto puro | `admin123`, `Teste` |
| `role` | `VARCHAR` | opcional | papel textual do usuario | `admin`, `viewer` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant ao qual o usuario pertence | `default` |

Amostra de dados:

| id | name | email | password | role | tenant_id |
|---|---|---|---|---|---|
| 1 | `Admin SmartLab` | `admin@smartlab.com` | `admin123` | `admin` | `default` |
| 2 | `Marcio Gazola` | `marciol.gazola@gmail.com` | `Teste` | `viewer` | `default` |

Dependencias:

- pertence a `tenants`
- relacao implicita potencial com `roles`

Observacao tecnica:

- ha risco de seguranca relevante porque `password` aparenta estar sem hash.

## 5.3 `clients`

Finalidade inferida: clientes ou contatos externos associados a um tenant.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador do cliente | `1` a `5` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant dono do cliente | `default`, `industrial`, `consultoria-de-negocios` |
| `name` | `VARCHAR` | NOT NULL | nome do cliente/conta | `Ana Costa`, `i9Exp` |
| `email` | `VARCHAR` | NOT NULL | email de contato | `ana@cliente.com`, `@i9exp.com` |
| `created_at` | `DATETIME` | opcional | data/hora do cadastro | `2026-03-04 02:27:59.414988` |

Amostra de dados:

| id | tenant_id | name | email | created_at |
|---|---|---|---|---|
| 1 | `default` | `Ana Costa` | `ana@cliente.com` | `2026-03-04 02:27:59.414988` |
| 2 | `default` | `Bruno Silva` | `bruno@cliente.com` | `2026-03-04 02:27:59.414991` |
| 3 | `industrial` | `Carlos Souza` | `carlos@ops.com` | `2026-03-04 02:27:59.414992` |
| 4 | `default` | `Marcio Gazola` | `marciol.gazola@gmail.com` | `2026-03-04 15:07:01.044005` |
| 5 | `consultoria-de-negocios` | `i9Exp` | `@i9exp.com` | `2026-03-05 20:06:50.979437` |

Dependencias:

- pertence a `tenants`

Observacao tecnica:

- existe `tenant_id = industrial`, mas nao ha tenant correspondente na tabela `tenants`. Isso indica violacao historica de integridade ou FK nao aplicada no momento da carga.

## 5.4 `projects`

Finalidade inferida: projetos de consultoria/diagnostico executados dentro de um tenant.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador do projeto | `1`, `2`, `3` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant do projeto | `default`, `consultoria-de-negocios` |
| `name` | `VARCHAR` | NOT NULL | nome do projeto | `Diagnostico Cultura 2026` |
| `project_type` | `VARCHAR` | opcional | tipo/categoria do projeto | `Diagnostico de Cultura`, `Trilha de Lideranca` |
| `status` | `VARCHAR` | opcional | status operacional | `execucao`, `planejamento` |
| `progress` | `INTEGER` | opcional | percentual ou score de progresso | `35`, `0` |
| `created_at` | `DATETIME` | opcional | data/hora da criacao | `2026-03-05 19:29:14.941201` |

Amostra de dados:

| id | tenant_id | name | project_type | status | progress | created_at |
|---|---|---|---|---|---:|---|
| 1 | `default` | `Diagnostico Cultura 2026` | `Diagnostico de Cultura` | `execucao` | 35 | `2026-03-05 19:29:14.941201` |
| 2 | `default` | `Projeto i9Exp Diagnostico Cultura` | `Diagnostico de Cultura` | `planejamento` | 0 | `2026-03-05 20:02:55.471974` |
| 3 | `consultoria-de-negocios` | `i9exp_NovoProjeto` | `Trilha de Lideranca` | `planejamento` | 0 | `2026-03-05 20:12:06.886392` |

Dependencias:

- pertence a `tenants`
- pai de `workflow_boxes`
- pai de `action_plans`

## 5.5 `workflow_boxes`

Finalidade inferida: etapas/blocos configuraveis de um fluxo de projeto.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador do bloco | `1` a `9` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant do bloco | `default`, `consultoria-de-negocios` |
| `project_id` | `INTEGER` | FK, NOT NULL | projeto ao qual o bloco pertence | `1`, `2`, `3` |
| `title` | `VARCHAR` | NOT NULL | titulo da etapa | `Visita Tecnica`, `Analise IA` |
| `box_type` | `VARCHAR` | opcional | natureza do bloco | `coleta`, `analise`, `etapa` |
| `position` | `INTEGER` | opcional | ordem no fluxo | `1`, `2`, `3` |
| `config_json` | `TEXT` | opcional | configuracao do bloco em JSON | `{\"owner\":\"Consultor SmartLab\",\"duracao\":\"2h\"}` |

Amostra de dados:

| id | tenant_id | project_id | title | box_type | position | config_json |
|---|---|---:|---|---|---:|---|
| 1 | `default` | 1 | `Visita Tecnica` | `coleta` | 1 | `{"owner":"Consultor SmartLab","duracao":"2h"}` |
| 2 | `default` | 1 | `Rodas de Conversa` | `coleta` | 2 | `{"owner":"Liderancas","duracao":"90min"}` |
| 3 | `default` | 1 | `Analise IA` | `analise` | 3 | `{"modelo":"smartlab-nlp-v1","drill_down":true}` |
| 4 | `default` | 2 | `Visitas Tecnicas` | `etapa` | 1 | `{"source":"builder","timestamp":"2026-03-05T20:03:38.937645","zone":"left"}` |
| 5 | `default` | 2 | `Roda de Conversa` | `coleta` | 2 | `{"source":"builder","timestamp":"2026-03-05T20:04:17.794421","zone":"left"}` |
| 6 | `default` | 2 | `Entrevista Lideranca` | `coleta` | 3 | `{"source":"builder","timestamp":"2026-03-05T20:04:52.297896","zone":"left"}` |
| 7 | `consultoria-de-negocios` | 3 | `Visita` | `coleta` | 1 | `{"source":"builder","timestamp":"2026-03-05T20:12:23.382422","zone":"left"}` |
| 8 | `consultoria-de-negocios` | 3 | `entrevista` | `coleta` | 2 | `{"source":"builder","timestamp":"2026-03-05T20:12:30.326129","zone":"center"}` |
| 9 | `consultoria-de-negocios` | 3 | `roda de conversa` | `coleta` | 3 | `{"source":"builder","timestamp":"2026-03-05T20:12:38.626095","zone":"center"}` |

Dependencias:

- pertence a `tenants`
- pertence a `projects`

## 5.6 `action_plans`

Finalidade inferida: plano de acoes associado a um projeto.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador da acao | `1`, `2`, `3` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant da acao | `default`, `consultoria-de-negocios` |
| `project_id` | `INTEGER` | FK, NOT NULL | projeto vinculado | `1`, `3` |
| `title` | `VARCHAR` | NOT NULL | titulo da acao | `Checklist de parada segura` |
| `owner` | `VARCHAR` | NOT NULL | responsavel pela entrega | `Operacao`, `Suzana` |
| `due_date` | `VARCHAR` | opcional | prazo da acao | `2026-04-15`, `2026/03/05` |
| `status` | `VARCHAR` | opcional | status da acao | `a_fazer`, `concluido`, `em_andamento` |
| `expected_result` | `TEXT` | opcional | resultado esperado | `Reduzir riscos criticos` |
| `actual_result` | `TEXT` | opcional | resultado obtido | `Concluido conforme planejado.` |
| `attainment` | `INTEGER` | opcional | percentual de atingimento | `0`, `100` |

Amostra de dados:

| id | tenant_id | project_id | title | owner | due_date | status | expected_result | actual_result | attainment |
|---|---|---:|---|---|---|---|---|---|---:|
| 1 | `default` | 1 | `Ritual diario de 10 min de seguranca` | `Supervisao de Turno` | `2026-04-15` | `a_fazer` | `Aumentar presenca da lideranca` | `NULL` | 0 |
| 2 | `default` | 1 | `Checklist de parada segura` | `Operacao` | `2026-04-05` | `concluido` | `Reduzir riscos criticos` | `Concluido conforme planejado.` | 100 |
| 3 | `consultoria-de-negocios` | 3 | `Agendar VIsita` | `Suzana` | `2026/03/05` | `em_andamento` | `Alinhar visista e disponibiliade` | `Concluido conforme planejado.` | 100 |

Dependencias:

- pertence a `tenants`
- pertence a `projects`

## 5.7 `forms`

Finalidade inferida: formularios/questionarios cadastrados por tenant.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador do formulario | `1` a `6` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant do formulario | `default`, `industrial`, `consultoria-de-negocios` |
| `name` | `VARCHAR` | NOT NULL | nome do formulario | `Diagnostico Cultura de Seguranca`, `I9EXP TEST FORMA` |
| `category` | `VARCHAR` | NOT NULL | categoria/tema do formulario | `Cultura`, `Atuacao da Lideranca` |

Amostra de dados:

| id | tenant_id | name | category |
|---|---|---|---|
| 1 | `default` | `Diagnostico Cultura de Seguranca` | `Cultura` |
| 2 | `industrial` | `Formulario Entrevistas` | `Diagnostico Cultura de Seguranca` |
| 3 | `industrial` | `Formulario de Entrevista` | `Atuacao da Lideranca` |
| 4 | `default` | `Teste` | `Atuacao da Lideranca` |
| 5 | `default` | `Formulario i9exp Teste` | `Diagnostico Cultura de Seguranca` |
| 6 | `consultoria-de-negocios` | `I9EXP TEST FORMA` | `Atuacao da Lideranca` |

Dependencias:

- pertence a `tenants`
- pai de `questions`
- referenciado por `responses`

Observacao tecnica:

- existe `tenant_id = industrial`, mas nao ha tenant correspondente em `tenants`.

## 5.8 `questions`

Finalidade inferida: perguntas de um formulario.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador da pergunta | `1`, `2`, `3` |
| `form_id` | `INTEGER` | FK, NOT NULL | formulario ao qual pertence | `1`, `6` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant da pergunta | `default`, `consultoria-de-negocios` |
| `text` | `TEXT` | NOT NULL | enunciado da pergunta | `A lideranca discute seguranca antes da produtividade?` |
| `qtype` | `VARCHAR` | opcional | tipo da pergunta | `fechada`, `aberta` |
| `options_json` | `TEXT` | opcional | opcoes da pergunta em JSON | `["Sempre","Frequentemente","Raramente","Nunca"]`, `[]` |

Amostra de dados:

| id | form_id | tenant_id | text | qtype | options_json |
|---|---:|---|---|---|---|
| 1 | 1 | `default` | `A lideranca discute seguranca antes da produtividade?` | `fechada` | `["Sempre", "Frequentemente", "Raramente", "Nunca"]` |
| 2 | 1 | `default` | `Quais barreiras voce encontra para seguir os procedimentos?` | `aberta` | `[]` |
| 3 | 6 | `consultoria-de-negocios` | `Qual o seu interesse em Cultura?` | `aberta` | `[]` |

Dependencias:

- pertence a `tenants`
- pertence a `forms`
- pai de `responses`

## 5.9 `responses`

Finalidade inferida: respostas dadas para perguntas de formularios.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador da resposta | `1`, `2` |
| `form_id` | `INTEGER` | FK, NOT NULL | formulario respondido | `1` |
| `question_id` | `INTEGER` | FK, NOT NULL | pergunta respondida | `1`, `2` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant da resposta | `default` |
| `answer` | `TEXT` | NOT NULL | conteudo da resposta | `Frequentemente`, `Pressao de prazo e comunicacao entre turnos.` |
| `score` | `INTEGER` | opcional | nota/pontuacao associada | `4`, `2` |

Amostra de dados:

| id | form_id | question_id | tenant_id | answer | score |
|---|---:|---:|---|---|---:|
| 1 | 1 | 1 | `default` | `Frequentemente` | 4 |
| 2 | 1 | 2 | `default` | `Pressao de prazo e comunicacao entre turnos.` | 2 |

Dependencias:

- pertence a `tenants`
- pertence a `forms`
- pertence a `questions`

## 5.10 `roles`

Finalidade inferida: papeis/perfis configuraveis por tenant.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador do papel | `1`, `2` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant do papel | `default` |
| `name` | `VARCHAR` | NOT NULL | nome do papel | `Novo Papel`, `Nova condicao comercial` |
| `permissions` | `TEXT` | opcional | lista de permissoes em JSON/texto | `["create:clientes","edit:clientes"]` |

Amostra de dados:

| id | tenant_id | name | permissions |
|---|---|---|---|
| 1 | `default` | `Novo Papel` | `["create:clientes", "edit:clientes"]` |
| 2 | `default` | `Nova condicao comercial` | `["Auterado para melhor retratar o negocio", "proposta aprovado em 30%"]` |

Dependencias:

- pertence a `tenants`
- pai de `responsibilities`

Observacao tecnica:

- `permissions` mistura, nos exemplos, permissao formal e anotacao livre de negocio. Isso fragiliza validacao e autorizacao.

## 5.11 `responsibilities`

Finalidade inferida: responsabilidades associadas a um papel.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador da responsabilidade | sem dados |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant da responsabilidade | sem dados |
| `role_id` | `INTEGER` | FK, NOT NULL | papel associado | sem dados |
| `description` | `TEXT` | NOT NULL | descricao textual da responsabilidade | sem dados |

Amostra de dados:

Sem registros no momento da analise.

Dependencias:

- pertence a `tenants`
- pertence a `roles`

## 5.12 `permission_boxes`

Finalidade inferida: regras pontuais de permissao por email e recurso.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador da regra | `2`, `3` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant da permissao | `default` |
| `user_email` | `VARCHAR` | NOT NULL | email alvo da permissao | `ana@cliente.com`, `suzana.soncin@i9exp.com` |
| `resource` | `VARCHAR` | NOT NULL | recurso/tela/objeto protegido | `Plano de Acoes`, `Relatorio Executivo` |
| `decision` | `VARCHAR` | opcional | decisao aplicada | `negado`, `permitido` |

Amostra de dados:

| id | tenant_id | user_email | resource | decision |
|---|---|---|---|---|
| 2 | `default` | `ana@cliente.com` | `Plano de Acoes` | `negado` |
| 3 | `default` | `suzana.soncin@i9exp.com` | `Relatorio Executivo` | `permitido` |

Dependencias:

- pertence a `tenants`
- relacao implicita com usuarios/clientes por email

## 5.13 `dashboard_boxes`

Finalidade inferida: widgets/blocos do dashboard configurados por tenant e escopo de papel.

| Atributo | Tipo | Regra | Descricao funcional inferida | Exemplos observados |
|---|---|---|---|---|
| `id` | `INTEGER` | PK, NOT NULL | identificador do widget | `1`, `2`, `3` |
| `tenant_id` | `VARCHAR` | FK, NOT NULL | tenant do widget | `default` |
| `role_scope` | `VARCHAR` | opcional | perfil/escopo que visualiza o widget | `consultor`, `cliente` |
| `title` | `VARCHAR` | NOT NULL | titulo exibido no dashboard | `Projetos Ativos`, `Score de Cultura` |
| `kind` | `VARCHAR` | opcional | tipo visual do widget | `lista`, `kpi` |
| `position` | `INTEGER` | opcional | ordem/posicao | `1`, `2` |
| `config_json` | `TEXT` | opcional | configuracao do widget em JSON | `{"fonte":"projetos"}` |

Amostra de dados:

| id | tenant_id | role_scope | title | kind | position | config_json |
|---|---|---|---|---|---:|---|
| 1 | `default` | `consultor` | `Projetos Ativos` | `lista` | 2 | `{"fonte": "projetos"}` |
| 2 | `default` | `consultor` | `Score de Cultura` | `kpi` | 1 | `{"fonte": "scores"}` |
| 3 | `default` | `cliente` | `Progresso do Projeto` | `kpi` | 1 | `{"fonte": "progresso"}` |

Dependencias:

- pertence a `tenants`
- relacao implicita potencial com `roles`

## 6. Mapa textual de relacionamentos

```text
tenants
  |- users
  |- clients
  |- projects
  |    |- workflow_boxes
  |    \- action_plans
  |- forms
  |    |- questions
  |    |    \- responses
  |    \- responses
  |- roles
  |    \- responsibilities
  |- permission_boxes
  \- dashboard_boxes
```

## 7. Inconsistencias e riscos de modelagem identificados

1. Senhas em texto puro em `users.password`.
2. Valores de `tenant_id` em `clients` e `forms` apontando para `industrial`, mas esse tenant nao existe em `tenants`.
3. Campos com datas armazenadas como texto em `action_plans.due_date`, inclusive com formatos mistos (`YYYY-MM-DD` e `YYYY/MM/DD`).
4. Relacoes importantes sem FK explicita:
   - `users.role`
   - `permission_boxes.user_email`
   - `dashboard_boxes.role_scope`
5. JSON armazenado em `TEXT` sem validacao estrutural (`config_json`, `options_json`, `permissions`).
6. `roles.permissions` aparenta misturar permissoes tecnicas com anotacoes de negocio.
7. Ha divergencias de padronizacao ortografica nos dados (`Agendar VIsita`, `visista`, `Auterado`), o que dificulta analise e filtros.

## 8. Recomendacoes tecnicas

1. Aplicar hash seguro em `users.password` com algoritmo apropriado para autenticacao.
2. Corrigir e validar integridade referencial de `tenant_id` em todas as tabelas.
3. Normalizar `users.role` para FK em `roles.id` ou criar tabela de associacao usuario-papel se houver multiplos papeis.
4. Considerar FK logica para `permission_boxes.user_email`, ou melhor, substituir por `user_id` / `client_id`.
5. Padronizar datas em colunas `DATE`/`DATETIME` ou, no minimo, em ISO 8601.
6. Definir convencao forte para colunas JSON e validar payloads na aplicacao.
7. Separar permissoes tecnicas de anotacoes descritivas na modelagem de `roles`.

## 9. Resumo executivo

O `ssecur1.db` tem um nucleo multi-tenant coerente e suficiente para suportar projetos, formularios e configuracao operacional. O principal eixo de relacionamento parte de `tenants`, com especializacoes em projetos (`projects`, `workflow_boxes`, `action_plans`) e formularios (`forms`, `questions`, `responses`). As maiores fragilidades estao em seguranca (`users.password`), integridade referencial parcial e uso de relacoes implicitas por texto/email em vez de chaves estruturadas.
