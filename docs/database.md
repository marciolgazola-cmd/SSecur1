# Banco de Dados do SSecur1

## Escopo deste documento

Este documento descreve o estado real do armazenamento de dados do `SSecur1` com base em:

- modelos ORM em [ssecur1/db.py](/home/marcio-gazola/SSecur1/ssecur1/db.py);
- schema efetivo do arquivo `ssecur1.db`;
- dados observados em 2026-03-18.

O foco aqui e responder de forma pratica:

- qual banco existe hoje;
- qual banco e recomendado para evolucao;
- quais entidades existem;
- quais campos sao `PK`, `FK`, `TEXT`, datas e JSON serializado;
- o que nasce automaticamente no sistema;
- o que se perde quando o `.db` e apagado;
- exemplos reais de dados armazenados.

## 1. Panorama de bancos

### 1.1 Banco em uso hoje

O projeto usa atualmente:

- engine: `SQLite`
- arquivo: `ssecur1.db`
- URL ORM: `sqlite:///ssecur1.db`

Essa configuracao esta declarada em [ssecur1/db.py](/home/marcio-gazola/SSecur1/ssecur1/db.py).

### 1.2 Banco alvo recomendado para producao

Para evolucao SaaS madura, o banco mais coerente hoje e `PostgreSQL`.

Motivos:

- melhor concorrencia e controle transacional;
- tipos mais ricos;
- suporte nativo melhor para JSON (`jsonb`);
- melhor observabilidade e operacao em nuvem;
- menor fragilidade para multi-tenancy em producao.

### 1.3 Situacao atual de JSON

Hoje o projeto usa muito JSON, mas nao com tipo nativo de banco. Os dados ficam em colunas `TEXT`, serializados manualmente.

Exemplos:

- `tenants.assigned_client_ids`
- `users.assigned_client_ids`
- `roles.permissions`
- `questions.options_json`
- `workflow_boxes.config_json`
- `dashboard_boxes.config_json`
- `action_plans.task_items_json`
- `interview_sessions.dimension_scores_json`
- `assistant_chunks.embedding_json`

No `SQLite` isso funciona como texto sem validacao estrutural. Em `PostgreSQL`, a recomendacao seria migrar esses campos para `jsonb` quando fizer sentido.

## 2. Ciclo de vida do banco

## 2.1 Como o banco nasce

Ao carregar [ssecur1/db.py](/home/marcio-gazola/SSecur1/ssecur1/db.py), o sistema executa:

1. `Base.metadata.create_all(bind=engine)`
2. `ensure_schema_updates()`
3. `_seed()`

## 2.2 O que o seed cria automaticamente

Se o banco estiver vazio, o sistema cria ao menos:

- tenant `default`
- usuario `Admin SmartLab`
- email `admin@smartlab.com`
- senha `admin123`

## 2.3 O que acontece se `ssecur1.db` for apagado

Na proxima inicializacao:

- as tabelas serao recriadas;
- colunas adicionais serao reaplicadas por `ensure_schema_updates()`;
- o seed minimo retornara.

Sera perdido:

- todo dado operacional criado pelos usuarios;
- projetos;
- clientes;
- formularios;
- perguntas;
- respostas;
- entrevistas;
- planos e tarefas;
- permissoes;
- configuracoes customizadas;
- metadados da IA;
- recomendacoes e chunks.

Pode permanecer no disco, fora do banco:

- arquivos em `uploaded_files/`

Isso significa que apagar apenas o `.db` pode gerar arquivos orfaos no filesystem.

## 2.4 Dados nativos do sistema vs dados operacionais

### Dados nativos ou seed do sistema

- tenant `default`
- usuario `admin@smartlab.com`

### Dados operacionais

Tudo o que for criado apos o bootstrap:

- tenants adicionais;
- usuarios adicionais;
- clientes;
- projetos;
- pesquisas;
- entrevistas;
- arquivos da base de IA;
- registros analiticos;
- planos de acao.

Esses dados desaparecem se o `.db` for descartado e recriado.

## 3. Inventario atual das tabelas

Em 2026-03-18 o banco possui 20 tabelas de aplicacao:

| Tabela | Registros observados |
| --- | ---: |
| `action_plans` | 2 |
| `action_tasks` | 2 |
| `assistant_chunks` | 240 |
| `assistant_documents` | 1 |
| `assistant_recommendations` | 7 |
| `clients` | 2 |
| `custom_options` | 0 |
| `dashboard_boxes` | 0 |
| `forms` | 4 |
| `interview_sessions` | 3 |
| `permission_boxes` | 48 |
| `project_assignments` | 1 |
| `projects` | 1 |
| `questions` | 25 |
| `responses` | 75 |
| `responsibilities` | 1 |
| `roles` | 1 |
| `surveys` | 3 |
| `tenants` | 3 |
| `users` | 4 |
| `workflow_boxes` | 1 |

## 4. Mapa de relacionamentos

### Mestre principal

- `tenants`

### Relacoes mais importantes

- `tenants -> users`
- `tenants -> clients`
- `tenants -> roles`
- `roles -> responsibilities`
- `tenants -> forms`
- `forms -> questions`
- `forms -> responses`
- `questions -> responses`
- `tenants -> surveys`
- `tenants -> interview_sessions`
- `tenants -> projects`
- `projects -> workflow_boxes`
- `projects -> action_plans`
- `action_plans -> action_tasks`
- `projects -> assistant_documents`
- `assistant_documents -> assistant_chunks`

### Relacoes importantes sem FK formal em todos os casos

- `users.role` guarda o nome textual do papel, nao referencia `roles.id`
- `permission_boxes.user_email` depende de email textual, nao de `users.id`
- varios campos `client_id`, `survey_id`, `project_id` e correlatos sao semanticos, mas nem todos estao protegidos por FK

## 5. Dicionario de dados por entidade

Cada secao abaixo traz:

- finalidade;
- campos e tipos;
- PK/FK;
- observacoes;
- exemplo real de registro.

## 5.1 `tenants`

Finalidade: espacos logicos isolados do sistema.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `VARCHAR` | PK |
| `name` | `VARCHAR` | NOT NULL |
| `slug` | `VARCHAR` | UNIQUE, NOT NULL |
| `owner_client_id` | `INTEGER` | opcional |
| `limit_users` | `INTEGER` | opcional |
| `created_at` | `DATETIME` | opcional |
| `assigned_client_ids` | `TEXT` | JSON serializado |

Observacoes:

- tabela base do multi-tenant;
- `assigned_client_ids` armazena lista em JSON textual.

Exemplo real:

```json
{
  "id": "default",
  "name": "SmartLab",
  "slug": "smartlab",
  "owner_client_id": 1,
  "limit_users": 150,
  "created_at": "2026-03-13 21:21:24.074375",
  "assigned_client_ids": "[\"1\", \"2\"]"
}
```

## 5.2 `users`

Finalidade: usuarios autenticados do sistema.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `name` | `VARCHAR` | NOT NULL |
| `email` | `VARCHAR` | UNIQUE, NOT NULL |
| `password` | `VARCHAR` | NOT NULL |
| `role` | `VARCHAR` | opcional |
| `account_scope` | `VARCHAR` | opcional |
| `client_id` | `INTEGER` | opcional |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `must_change_password` | `INTEGER` | default `0` |
| `profession` | `VARCHAR` | opcional |
| `department` | `VARCHAR` | opcional |
| `reports_to_user_id` | `INTEGER` | opcional |
| `assigned_client_ids` | `TEXT` | JSON serializado |

Observacoes:

- senha hoje esta sem hash;
- `role` e textual, nao ligado por FK a `roles`;
- `reports_to_user_id` nao tem FK formal.

Exemplo real:

```json
{
  "id": 1,
  "name": "Admin SmartLab",
  "email": "admin@smartlab.com",
  "password": "admin123",
  "role": "admin",
  "account_scope": "smartlab",
  "client_id": null,
  "tenant_id": "default",
  "must_change_password": 0,
  "profession": "CEO",
  "department": "Operacao",
  "reports_to_user_id": null,
  "assigned_client_ids": "[\"1\", \"2\"]"
}
```

## 5.3 `clients`

Finalidade: empresas, contas ou estruturas de cliente vinculadas ao tenant.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `name` | `VARCHAR` | NOT NULL |
| `email` | `VARCHAR` | NOT NULL |
| `created_at` | `DATETIME` | opcional |
| `cnpj` | `VARCHAR` | opcional |
| `business_sector` | `VARCHAR` | opcional |
| `employee_count` | `INTEGER` | opcional |
| `branch_count` | `INTEGER` | opcional |
| `annual_revenue` | `INTEGER` | opcional |
| `trade_name` | `VARCHAR` | opcional |
| `parent_client_id` | `INTEGER` | opcional |
| `phone` | `VARCHAR` | opcional |
| `address` | `VARCHAR` | opcional |
| `state_code` | `VARCHAR` | opcional |

Observacoes:

- `parent_client_id` sugere hierarquia, mas nao tem FK formal.

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "name": "i9exp",
  "email": "adm@i9exp.com",
  "created_at": "2026-03-13 22:42:53.652756",
  "cnpj": "36.014.210/0001-46",
  "business_sector": "Servicos",
  "employee_count": 5,
  "branch_count": 1,
  "annual_revenue": 10000,
  "trade_name": null,
  "parent_client_id": null,
  "phone": null,
  "address": null,
  "state_code": null
}
```

## 5.4 `roles`

Finalidade: papeis customizados por tenant.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `name` | `VARCHAR` | NOT NULL |
| `permissions` | `TEXT` | JSON serializado |

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "name": "RH - Gestão",
  "permissions": "[\"create:users\", \"edit:users\"]"
}
```

## 5.5 `responsibilities`

Finalidade: responsabilidades textuais ligadas a um papel.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `role_id` | `INTEGER` | FK -> `roles.id` |
| `description` | `TEXT` | NOT NULL |

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "role_id": 1,
  "description": "Permite ao time de RH cadastrar um novo Usuário e Alterar um Usuário Existente."
}
```

## 5.6 `forms`

Finalidade: formularios configurados no sistema.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `name` | `VARCHAR` | NOT NULL |
| `category` | `VARCHAR` | NOT NULL |
| `target_client_id` | `INTEGER` | opcional |
| `target_user_email` | `VARCHAR` | opcional |

Observacoes:

- `target_client_id` nao tem FK formal;
- pode ser usado como formulario generico ou orientado a alvo especifico.

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "name": "Formulário Entrevista com a Liderança",
  "category": "Diagnóstico Cultura de Segurança",
  "target_client_id": null,
  "target_user_email": null
}
```

## 5.7 `questions`

Finalidade: perguntas vinculadas a formularios e opcionalmente a surveys.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `form_id` | `INTEGER` | FK -> `forms.id` |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `text` | `TEXT` | NOT NULL |
| `qtype` | `VARCHAR` | opcional |
| `options_json` | `TEXT` | JSON serializado |
| `dimension` | `VARCHAR` | opcional |
| `polarity` | `VARCHAR` | default `positiva` |
| `weight` | `INTEGER` | default `1` |
| `survey_id` | `INTEGER` | opcional |
| `order_index` | `INTEGER` | default `0` |

Observacoes:

- `qtype` esta sendo usado de forma rica, inclusive com JSON serializado dentro de `VARCHAR`;
- `options_json` guarda opcoes e logica condicional;
- `survey_id` nao esta protegido por FK formal.

Exemplo real:

```json
{
  "id": 1,
  "form_id": 2,
  "tenant_id": "default",
  "text": "O líder circula regularmente nas áreas operacionais durante o turno?",
  "qtype": "{\"kind\": \"escala_0_5\", \"scale\": {\"0\": \"Nada aderente\", \"1\": \"Pouco aderente\", \"2\": \"Parcialmente aderente\", \"3\": \"Moderadamente aderente\", \"4\": \"Muito aderente\", \"5\": \"Totalmente aderente\"}}",
  "options_json": "{\"options\": [\"Nada Aderente\", \"Pouco Aderente\", \"Parcialmente Aderente\", \"Moderadamente Aderente\", \"Muito Aderente\", \"Totalmente Aderente\"], \"logic\": {\"show_if\": \"\"}}",
  "dimension": "Presença",
  "polarity": "positiva",
  "weight": 1,
  "survey_id": 1,
  "order_index": 1
}
```

## 5.8 `responses`

Finalidade: respostas capturadas em formularios, surveys e entrevistas.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `form_id` | `INTEGER` | FK -> `forms.id` |
| `question_id` | `INTEGER` | FK -> `questions.id` |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `answer` | `TEXT` | NOT NULL |
| `score` | `INTEGER` | opcional/default |
| `interview_id` | `INTEGER` | opcional |
| `survey_id` | `INTEGER` | opcional |
| `respondent_id` | `INTEGER` | opcional |
| `client_id` | `INTEGER` | opcional |
| `service_name` | `VARCHAR` | opcional |
| `response_token` | `VARCHAR` | opcional |
| `submitted_at` | `DATETIME` | opcional |

Observacoes:

- varios ids semanticos nao possuem FK formal;
- `answer` pode coexistir com `score`.

Exemplo real:

```json
{
  "id": 1,
  "form_id": 2,
  "question_id": 1,
  "tenant_id": "default",
  "answer": "",
  "score": 1,
  "interview_id": 1,
  "survey_id": 1,
  "respondent_id": 2,
  "client_id": 1,
  "service_name": "Diagnóstico Cultura de Segurança",
  "response_token": "survey-1-session-1",
  "submitted_at": "2026-03-17 00:38:22.881165"
}
```

## 5.9 `surveys`

Finalidade: instancia ou configuracao de coleta compartilhavel.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `name` | `VARCHAR` | NOT NULL |
| `service_name` | `VARCHAR` | NOT NULL |
| `share_token` | `VARCHAR` | opcional |
| `legacy_form_id` | `INTEGER` | opcional |
| `created_at` | `DATETIME` | opcional |
| `stage_name` | `VARCHAR` | default `"Visita Técnica - Guiada"` |

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "name": "Form - Coleta dados - Diagnostico - Liderança",
  "service_name": "Diagnóstico Cultura de Segurança",
  "share_token": "Z61JKCqrYsQ",
  "legacy_form_id": 2,
  "created_at": "2026-03-14 19:40:17.271368",
  "stage_name": "Entrevista Individual com o Líder"
}
```

## 5.10 `interview_sessions`

Finalidade: sessao de entrevista vinculada a formulario, projeto e contexto do entrevistado.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `form_id` | `INTEGER` | FK -> `forms.id` |
| `project_id` | `INTEGER` | opcional |
| `client_id` | `INTEGER` | opcional |
| `interview_date` | `VARCHAR` | opcional |
| `interviewee_name` | `VARCHAR` | NOT NULL |
| `interviewee_role` | `VARCHAR` | opcional |
| `consultant_name` | `VARCHAR` | opcional |
| `status` | `VARCHAR` | opcional/default |
| `notes` | `TEXT` | opcional/default |
| `created_at` | `DATETIME` | opcional |
| `interviewee_user_id` | `INTEGER` | opcional |
| `survey_id` | `INTEGER` | opcional |
| `total_score` | `INTEGER` | default `0` |
| `dimension_scores_json` | `TEXT` | JSON serializado |
| `target_area` | `VARCHAR` | opcional |
| `audience_group` | `VARCHAR` | opcional |

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "form_id": 2,
  "project_id": 1,
  "client_id": 1,
  "interview_date": "2026-03-14",
  "interviewee_name": "Mateus Gazola",
  "interviewee_role": "Coordenador",
  "consultant_name": "admin@smartlab.com",
  "status": "concluida",
  "notes": "",
  "created_at": "2026-03-14 21:57:47.502915",
  "interviewee_user_id": 2,
  "survey_id": 1,
  "total_score": 62,
  "dimension_scores_json": "{\"Presen\\u00e7a\": 5, \"Corre\\u00e7\\u00e3o\": 11, \"Reconhecimento\": 16, \"Comunica\\u00e7\\u00e3o\": 25, \"Disciplina/Exemplo\": 5}",
  "target_area": null,
  "audience_group": null
}
```

## 5.11 `projects`

Finalidade: projetos operacionais de diagnostico, trilha ou execucao.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `name` | `VARCHAR` | NOT NULL |
| `project_type` | `VARCHAR` | opcional/default |
| `status` | `VARCHAR` | opcional/default |
| `progress` | `INTEGER` | opcional/default |
| `created_at` | `DATETIME` | opcional |
| `service_name` | `VARCHAR` | default |
| `client_id` | `INTEGER` | opcional |
| `contracted_at` | `VARCHAR` | default `""` |

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "name": "Projeto de Teste i9exp - Cultura de Segurança",
  "project_type": "Diagnóstico de Cultura",
  "status": "planejamento",
  "progress": 0,
  "created_at": "2026-03-14 02:31:35.651450",
  "service_name": "Diagnóstico Cultura de Segurança",
  "client_id": 1,
  "contracted_at": "2026-03-16"
}
```

## 5.12 `project_assignments`

Finalidade: vinculo entre projeto e cliente no tenant.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `project_id` | `INTEGER` | FK -> `projects.id` |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `client_id` | `INTEGER` | opcional |
| `created_at` | `DATETIME` | opcional |

Exemplo real:

```json
{
  "id": 1,
  "project_id": 1,
  "tenant_id": "default",
  "client_id": 1,
  "created_at": "2026-03-14 15:35:55.043135"
}
```

## 5.13 `workflow_boxes`

Finalidade: caixas/etapas do fluxo de projeto.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `project_id` | `INTEGER` | FK -> `projects.id` |
| `title` | `VARCHAR` | NOT NULL |
| `box_type` | `VARCHAR` | opcional/default |
| `position` | `INTEGER` | opcional/default |
| `config_json` | `TEXT` | JSON serializado |

Observacoes:

- `config_json` e uma das chaves do modelo low-code.

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "project_id": 1,
  "title": "Sticky Note",
  "box_type": "nota",
  "position": 1,
  "config_json": "{\"zone\": \"right\", \"note\": \"Entrevista Maturidade no Canvas\", \"source\": \"sticky-note\", \"timestamp\": \"2026-03-14T02:34:59.435783\"}"
}
```

## 5.14 `action_plans`

Finalidade: itens de plano de acao ligados a projeto.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `project_id` | `INTEGER` | FK -> `projects.id` |
| `title` | `VARCHAR` | NOT NULL |
| `owner` | `VARCHAR` | NOT NULL |
| `due_date` | `VARCHAR` | opcional |
| `status` | `VARCHAR` | opcional/default |
| `expected_result` | `TEXT` | opcional/default |
| `actual_result` | `TEXT` | opcional/default |
| `attainment` | `INTEGER` | opcional/default |
| `client_id` | `INTEGER` | opcional |
| `service_name` | `VARCHAR` | default `""` |
| `dimension_names` | `TEXT` | default `""` |
| `target_area` | `VARCHAR` | default `""` |
| `start_date` | `VARCHAR` | default `""` |
| `planned_due_date` | `VARCHAR` | default `""` |
| `due_date_change_count` | `INTEGER` | default `0` |
| `task_items_json` | `TEXT` | JSON serializado |
| `completed_at` | `VARCHAR` | default `""` |

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "project_id": 1,
  "title": "bla",
  "owner": "Fernanda",
  "due_date": "2026-04-01",
  "status": "em_andamento",
  "expected_result": "nao sei.",
  "actual_result": "",
  "attainment": 35,
  "client_id": null,
  "service_name": "",
  "dimension_names": "",
  "target_area": "",
  "start_date": "",
  "planned_due_date": "",
  "due_date_change_count": 0,
  "task_items_json": "[]",
  "completed_at": ""
}
```

## 5.15 `action_tasks`

Finalidade: tarefas filhas de um plano de acao.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `action_plan_id` | `INTEGER` | FK -> `action_plans.id` |
| `title` | `VARCHAR` | NOT NULL |
| `owner` | `VARCHAR` | NOT NULL |
| `start_date` | `VARCHAR` | default `""` |
| `due_date` | `VARCHAR` | default `""` |
| `progress` | `INTEGER` | default `0` |
| `created_at` | `DATETIME` | opcional |
| `planned_due_date` | `VARCHAR` | default `""` |
| `due_date_change_count` | `INTEGER` | default `0` |
| `expected_result` | `TEXT` | default `""` |

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "action_plan_id": 2,
  "title": "Desenvolver plano estruturado para harmonizar resultados operacionais com práticas seguras",
  "owner": "JBS",
  "start_date": "18-03-2026",
  "due_date": "31/05/2026",
  "progress": 100,
  "created_at": "2026-03-18 03:08:11.648561",
  "planned_due_date": "31/05/2026",
  "due_date_change_count": 0,
  "expected_result": "Redução dos gaps entre respostas e políticas"
}
```

## 5.16 `permission_boxes`

Finalidade: permissoes visuais por recurso e usuario.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `user_email` | `VARCHAR` | NOT NULL |
| `resource` | `VARCHAR` | NOT NULL |
| `decision` | `VARCHAR` | default `permitido` |

Observacoes:

- o usuario e identificado por email textual;
- nao ha FK para `users`.

Exemplo real:

```json
{
  "id": 3,
  "tenant_id": "default",
  "user_email": "admin@smartlab.com",
  "resource": "Projetos",
  "decision": "permitido"
}
```

## 5.17 `dashboard_boxes`

Finalidade: widgets configuraveis por escopo de papel.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `role_scope` | `VARCHAR` | default `consultor` |
| `title` | `VARCHAR` | NOT NULL |
| `kind` | `VARCHAR` | default `kpi` |
| `position` | `INTEGER` | default `0` |
| `config_json` | `TEXT` | JSON serializado |

Observacoes:

- tabela vazia no banco observado em 2026-03-18.

## 5.18 `assistant_documents`

Finalidade: metadados de arquivos enviados para a base da IA.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `project_id` | `INTEGER` | FK -> `projects.id`, opcional |
| `file_name` | `VARCHAR` | NOT NULL |
| `file_path` | `VARCHAR` | NOT NULL |
| `resource_type` | `VARCHAR` | default `politica` |
| `file_size` | `INTEGER` | default `0` |
| `uploaded_by` | `VARCHAR` | default `sistema` |
| `uploaded_at` | `DATETIME` | opcional |
| `knowledge_scope` | `VARCHAR` | default `tenant` |

Observacoes:

- o binario do arquivo fica fora do banco;
- aqui ficam os metadados e a referencia de caminho.

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "project_id": null,
  "file_name": "DIAGNOSTICO E EXECUCAO-CULTURA-DE-SEGURANCA-JBS FINAL.pdf",
  "file_path": "uploaded_files/assistant_resources/default/default/20260317235741_0d87f532_DIAGNOSTICO E EXECUCAO-CULTURA-DE-SEGURANCA-JBS FINAL.pdf",
  "resource_type": "relatorio",
  "file_size": 4642116,
  "uploaded_by": "admin@smartlab.com",
  "uploaded_at": "2026-03-18 02:57:41.522125",
  "knowledge_scope": "default"
}
```

## 5.19 `assistant_chunks`

Finalidade: fragmentos textuais e vetoriais indexados para o RAG local.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `document_id` | `INTEGER` | FK -> `assistant_documents.id` |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `project_id` | `INTEGER` | FK -> `projects.id`, opcional |
| `knowledge_scope` | `VARCHAR` | opcional/default |
| `chunk_index` | `INTEGER` | default `0` |
| `content` | `TEXT` | NOT NULL |
| `keyword_blob` | `TEXT` | default `""` |
| `embedding_json` | `TEXT` | JSON serializado |
| `created_at` | `DATETIME` | opcional |

Observacoes:

- `embedding_json` guarda vetor numerico serializado como texto;
- essa tabela cresce rapidamente conforme a base documental aumenta.

Exemplo real resumido:

```json
{
  "id": 1,
  "document_id": 1,
  "tenant_id": "default",
  "project_id": null,
  "knowledge_scope": "default",
  "chunk_index": 0,
  "content": "Segurança que acontece na prática ...",
  "keyword_blob": "segurança cultura liderança prática ...",
  "embedding_json": "[-0.005240858, 0.05363133, -0.14614786, ...]",
  "created_at": "2026-03-18 02:57:45.223488"
}
```

## 5.20 `assistant_recommendations`

Finalidade: recomendacoes operacionais geradas para acompanhamento.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `project_id` | `INTEGER` | FK -> `projects.id`, opcional |
| `title` | `VARCHAR` | NOT NULL |
| `owner` | `VARCHAR` | default `""` |
| `due_date` | `VARCHAR` | default `""` |
| `expected_result` | `TEXT` | default `""` |
| `status` | `VARCHAR` | default `open` |
| `created_by` | `VARCHAR` | default `sistema` |
| `created_at` | `DATETIME` | opcional |

Exemplo real:

```json
{
  "id": 1,
  "tenant_id": "default",
  "project_id": null,
  "title": "Tratar lacunas de Formulário Entrevista com a Liderança",
  "owner": "Liderança do processo",
  "due_date": "16-04-2026",
  "expected_result": "Elevar a categoria Diagnóstico Cultura de Segurança acima de 0.0 com base em políticas, entrevistas e evidências do tenant.",
  "status": "replaced",
  "created_by": "admin@smartlab.com",
  "created_at": "2026-03-18 02:42:43.698566"
}
```

## 5.21 `custom_options`

Finalidade: catalogos customizados por tenant.

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | `INTEGER` | PK, autoincrement |
| `tenant_id` | `VARCHAR` | FK -> `tenants.id` |
| `catalog_key` | `VARCHAR` | NOT NULL |
| `option_value` | `VARCHAR` | NOT NULL |
| `created_at` | `DATETIME` | opcional |

Observacoes:

- tabela vazia no banco observado;
- util para listas configuraveis sem mudar o schema.

## 6. Campos JSON e dados semi-estruturados

## 6.1 Onde o projeto usa JSON hoje

| Tabela | Campo | Uso |
| --- | --- | --- |
| `tenants` | `assigned_client_ids` | lista de clientes associados |
| `users` | `assigned_client_ids` | lista de clientes visiveis ao usuario |
| `roles` | `permissions` | permissoes do papel |
| `questions` | `options_json` | opcoes e logica da pergunta |
| `questions` | `qtype` | modelo de pergunta, em alguns casos como JSON |
| `workflow_boxes` | `config_json` | metadados da caixa |
| `dashboard_boxes` | `config_json` | configuracao do widget |
| `action_plans` | `task_items_json` | itens agregados do plano |
| `interview_sessions` | `dimension_scores_json` | score por dimensao |
| `assistant_chunks` | `embedding_json` | embedding vetorial |

## 6.2 Implicacao tecnica

Isso da flexibilidade ao produto, mas traz custos:

- sem validacao nativa no banco;
- consultas analiticas mais limitadas;
- maior dependencia de serializacao correta no codigo;
- mais trabalho numa futura migracao para banco relacional mais forte.

## 6.3 Recomendacao para PostgreSQL

Ao migrar para `PostgreSQL`, os campos abaixo deveriam ser candidatos a `jsonb`:

- `assigned_client_ids`
- `permissions`
- `options_json`
- `config_json`
- `task_items_json`
- `dimension_scores_json`

`embedding_json` talvez deva seguir outro caminho dependendo da estrategia:

- `jsonb` se a prioridade for simplicidade;
- tabela vetorial especializada se houver busca semantica em escala.

## 7. Integridade, limites e riscos

## 7.1 O que esta bem modelado

- quase todo dominio depende de `tenant_id`;
- ha FK importantes entre formularios, perguntas, respostas e projetos;
- a separacao entre metadado do arquivo e chunk da IA esta clara.

## 7.2 O que ainda esta fragil

- senha sem hash;
- ausencia de migracoes formais;
- varios relacionamentos sem FK;
- campos de data em `VARCHAR` em varias tabelas;
- uso forte de JSON textual sem validacao de schema.

## 7.3 Consequencia pratica

O banco atual e funcional para desenvolvimento e demonstracao, mas ainda nao esta no ponto ideal para operacao SaaS madura.

## 8. Direcao recomendada de evolucao

1. introduzir Alembic de verdade;
2. migrar para `PostgreSQL`;
3. normalizar alguns relacionamentos hoje textuais;
4. mover JSON relevante para `jsonb`;
5. padronizar datas para tipos temporais mais fortes;
6. aplicar hash de senha e controles de seguranca;
7. definir estrategia de backup/restore de banco e arquivos.
