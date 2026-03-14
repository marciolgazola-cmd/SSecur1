# Arquitetura SmartLab SaaS (Evolução)

## Objetivo
Evoluir o SSecur1 para uma plataforma SaaS multi-tenant com builder low-code/no-code de "Caixas" para:
- Diagnóstico de Cultura de Segurança
- Trilhas de Desenvolvimento de Liderança
- Gestão de ações, análise e entregáveis

## O que já está implementado neste ciclo
- Multi-tenant por `tenant_id` em todos os domínios principais.
- Módulo de projetos com workflow por "Caixas" (`projects`, `workflow_boxes`).
- Módulo de planos de ação em Kanban (`action_plans`).
- Permissões visuais por recurso (`permission_boxes`).
- Dashboard configurável por caixas por perfil (`dashboard_boxes`).
- Primeira evolucao da tela de permissões para modelo visual de `RBAC`, com templates de papel, catalogo de recursos e canvas de acesso por usuario.
- Tela inicial de acesso alinhada a estrategia corporativa: somente `Login`, sem auto-registro publico.

## Estrategia de acesso inicial

Na fase atual do produto:

- a tela inicial deve oferecer apenas `Login`;
- usuarios nao se registram livremente pela landing page;
- contas sao criadas e liberadas de forma controlada pela SmartLab;
- a criacao de usuarios foi movida para um modulo administrativo interno de `Usuarios`;
- no futuro, administradores do cliente poderao criar usuarios limitados dentro do proprio tenant;
- o que cada usuario visualiza depende de `tenant`, `papel` e permissoes explicitas.

### Observacao de UX atual

- a tela `Permissoes` trabalha apenas com usuarios ja existentes;
- a separacao funcional passou a ser:
  - `Clientes`: cadastra a empresa atendida;
  - `Tenants`: cria o espaco isolado vinculado ao cliente;
  - `Usuarios`: cria e administra contas de `SmartLab` ou do `Cliente`;
  - `Permissoes`: define o que cada conta pode acessar;
- o canvas de acessos continua funcional por acoes explicitas (`Permitir`, `Negar`, `Limpar`);
- o `drag-and-drop` visual generico entre colunas foi adiado para uma iteracao futura, porque a stack atual nao oferece uma implementacao nativa simples e segura para esse comportamento no contexto atual do projeto.

### Ordem operacional recomendada

1. cadastrar `Cliente`
2. provisionar `Tenant` vinculado a esse cliente
3. cadastrar `Usuarios`
4. configurar `Permissoes`

Decisao de UX:

- `Cliente` e o cadastro principal de negocio;
- `Tenant` e uma estrutura tecnica de isolamento;
- por isso, o tenant deve nascer automaticamente no cadastro do cliente;
- a tela de `Tenants` permanece apenas como area administrativa avancada;
- o quadro de `Permissoes` deixa de simular drag-and-drop e usa interacao explicita ate a entrega de um componente customizado para DnD real.

Regra de acesso:

- usuarios com escopo `smartlab` podem operar varios clientes, conforme o papel;
- usuarios com escopo `cliente` devem ficar vinculados a um cliente especifico e ao tenant correspondente;
- tenants operacionais de cliente devem ser vinculados explicitamente ao cliente dono;
- usuarios de cliente so podem ser criados se estiverem vinculados ao tenant do proprio cliente;
- a navegacao e o acesso a dados devem respeitar esse escopo.

### Regra de hierarquia de usuarios

- o cadastro de usuarios do cliente deve suportar hierarquia organizacional;
- o campo `A quem se reporta` depende da existencia previa de um usuario superior no mesmo cliente/workspace;
- por isso, o primeiro usuario do cliente normalmente deve ser o nivel mais alto da estrutura, como `CEO`, `Diretor` ou equivalente;
- esse primeiro usuario pode ser criado sem reporte a ninguem;
- depois disso, os demais usuarios podem ser cadastrados apontando para a hierarquia ja existente;
- a hierarquia deve sempre respeitar o mesmo contexto de `cliente` e `workspace`, sem cruzamento entre empresas diferentes.

## Próximos passos técnicos (prioridade)
1. API-first
- Expor camada REST/GraphQL para `projects`, `workflow_boxes`, `action_plans`, `permission_boxes` e `dashboard_boxes`.
- Versionamento de API (`/api/v1`), contratos OpenAPI e testes de contrato.

2. Segurança e identidade
- OAuth2/OIDC com provedores corporativos.
- RBAC + ABAC por tenant com policy engine.
- Hardening OWASP Top 10 (CSRF, rate limit, auditoria e trilha de eventos).

3. Tenant dedicado
- Estratégia por banco/schema dedicado por cliente.
- Provisionamento automatizado de tenant, backup e isolamento lógico/físico.

4. IA estruturada
- Pipeline de ingestão + vetorização + RAG.
- Guardrails, avaliação automática de respostas e telemetria de qualidade.
- Suporte a tuning por contexto de cliente.

5. Frontend de caixas evoluído
- Drag-and-drop com conexões visuais reais (estilo n8n).
- Drill-down contextual em qualquer resultado analítico.
- Biblioteca de componentes reutilizáveis de caixas.

6. Qualidade
- Testes automatizados (unitários, integração e e2e).
- CI com validação de migrações, cobertura mínima e lint.

## Modelo recomendado para configuração dinâmica
- Manter metadados configuráveis em JSON (`config_json`) para cada caixa.
- Versionar layouts e workflows por tenant e por projeto.
- Suportar rollback de configuração sem deploy.

## Referencias de produto para frontend e backend

As plataformas `BlazeSQL`, `FastQuest`, `Sphinx Brasil` e `Rabbot` podem ser usadas como referencias de linguagem de produto e de arquitetura, com uma ressalva importante: como sao plataformas proprietarias e, em alguns casos, com baixa documentacao publica, o uso aqui deve ser entendido como benchmark funcional e nao como afirmacao de implementacao interna exata.

### Desenvolvimento e integracao

- `BlazeSQL` aponta para uma estrategia `API-first`, com foco em geracao de consultas, embedding e white-label.
- `Sphinx Brasil` sugere uma arquitetura orientada a integracoes, com coleta de dados, sincronizacao com CRM/ERP e regras condicionais em fluxos.
- `FastQuest` e `Rabbot`, embora com menos material tecnico publico, reforcam a ideia de modulos especializados acessiveis por interfaces web e automacao operacional.

Implicacoes para o SSecur1:

- expor APIs consistentes para `projects`, `workflow_boxes`, `forms`, `questions`, `responses`, `action_plans` e dashboards;
- tratar cada "Caixa" como objeto configuravel, com contrato claro de entrada, saida e comportamento;
- suportar embedding futuro de dashboards, formularios e fluxos em portais externos;
- preparar conectores para ERP, CRM, planilhas, webhooks e ingestao externa.

### Interface com usuario

As referencias observadas convergem em tres padroes de UX:

- experiencia conversacional ou assistida por IA para refinamento de consultas e analises;
- builders visuais drag-and-drop para questionarios, dashboards e workflows;
- paines operacionais responsivos, personalizados por perfil de acesso.

Implicacoes para o frontend do SSecur1:

- manter o builder de "Caixas" como objeto central da experiencia;
- permitir preview imediato de configuracoes e alteracoes de fluxo;
- separar claramente visoes por papel, tenant e contexto operacional;
- evoluir dashboards para configuracao declarativa por metadados, sem necessidade de recodificar telas.

### Co-criacao de fluxos

As referencias sugerem forte aderencia a logica condicional e fluxos ramificados:

- questionarios com caminhos `if/then`;
- automacoes disparadas por evento;
- refinamento iterativo de consultas, diagnosticos e paines.

Implicacoes para o backend e para o modelo de objetos:

- representar fluxos como grafos ou sequencias enriquecidas, e nao apenas listas estaticas;
- permitir regras condicionais entre caixas, perguntas e proximas etapas;
- armazenar configuracoes em metadados versionados;
- registrar eventos de execucao para auditoria, reprocessamento e analise posterior.

### Programacao low-code / no-code

O benchmark reforca uma direcao clara: a plataforma deve esconder a complexidade tecnica sem perder extensibilidade.

Implicacoes para a arquitetura do SSecur1:

- `frontend`: editores visuais, formularios dinamicos, drag-and-drop, preview e parametrizacao por JSON;
- `backend`: motor de execucao de caixas, validacao de contratos, versionamento de configuracao e APIs de composicao;
- `dados`: persistencia orientada a configuracao, com metadados por tenant, projeto, formulario e dashboard;
- `seguranca`: controle por papel, tenant e recurso, com capacidade futura de ABAC.

### Traducao para o nosso roadmap

Com base nessas referencias, a evolucao da aplicacao deve priorizar:

1. `Backend composable`
- transformar caixas, formularios, dashboards e planos em recursos de API reutilizaveis;
- criar contratos de execucao para cada tipo de caixa;
- viabilizar conectores e webhooks.

2. `Frontend de co-criacao`
- consolidar uma experiencia visual de montagem de fluxos;
- incluir preview, validacao em tempo real e configuracao por propriedades;
- padronizar componentes reutilizaveis para builder, dashboard e formularios.

3. `Camada de orquestracao`
- suportar logica condicional, gatilhos e bifurcacoes;
- tratar workflows como objetos versionados;
- permitir automacao sem codigo pesado.

4. `Experiencia orientada a perfis`
- dashboards, permissoes e fluxos variando por tenant e papel;
- visoes focadas em consultor, cliente, lideranca e administracao;
- menor acoplamento entre regra de negocio e interface.

## Matriz do que falta implementar

Considerando a estrategia atual de:

- desenvolvimento em `Python`;
- frontend web gerado em base `React` via `Reflex`;
- execucao tambem em `Windows`;
- hospedagem alvo no `Azure`;
- evolucao para SaaS multi-tenant com low-code/no-code;

a tabela abaixo resume o estado atual e os gaps prioritarios.

| Camada | Stack atual / padrao adotado | O que ja temos | O que falta implementar | Prioridade |
|---|---|---|---|---|
| `Backend` | `Python` + `Reflex State` + `SQLAlchemy` | CRUD principal, multi-tenant por `tenant_id`, regras basicas de permissao, persistencia SQLite | separar melhor servicos, criar camada de API publica real (`REST /api/v1`), contratos versionados, validacao mais forte e organizacao por modulos | Alta |
| `Frontend` | `Reflex` com renderizacao web baseada em `React` | dashboard, formularios, workflow builder, kanban, telas administrativas | drag-and-drop mais robusto, conexoes visuais reais entre caixas, edicao mais declarativa, melhor responsividade e UX de builder | Alta |
| `Banco de dados` | `SQLite` local | modelo inicial multi-tenant, entidades principais do dominio | migrar para banco mais adequado a producao no Azure, estrategia de migracoes, isolamento mais forte por tenant, backup e restauracao | Alta |
| `Multi-tenancy` | isolamento logico por `tenant_id` | filtros por tenant em modulos principais | deteccao automatica de tenant, enforcement centralizado, revisao de integridade referencial, opcao futura de tenant dedicado por banco/schema | Alta |
| `API-first` | direcao conceitual ja iniciada | catalogo visual de recursos e modelagem orientada a objetos configuraveis | endpoints reais, autenticacao de API, OpenAPI/Swagger, webhooks, embedding externo e testes de contrato | Alta |
| `Seguranca` | autenticacao simples local | login, papel basico (`admin`, `editor`, `viewer`) e permissoes visuais | hash de senha, RBAC mais consistente, ABAC por recurso, trilha de auditoria, rate limit, CSRF, hardening para publicacao | Critica |
| `Identidade` | usuarios locais no banco | cadastro e login simples | integracao com `Azure AD` / `Microsoft Entra ID`, OAuth2/OIDC, recuperacao de senha, MFA e SSO corporativo | Alta |
| `Workflow / Low-code` | caixas com `config_json` | builder de caixas, condicoes basicas, blueprint de fluxo, logs de execucao | motor de orquestracao mais formal, bifurcacao real, reuso de templates, validacao de contratos de entrada/saida, execucao assincrona | Alta |
| `Formularios inteligentes` | perguntas configuradas por metadados | perguntas abertas/fechadas, preview de logica condicional | caminhos condicionais completos, scorecards, reutilizacao de blocos, respostas por sessao/respondente, analytics mais profundos | Media/Alta |
| `Dashboard configuravel` | caixas configuradas por metadados | widgets por perfil, origem declarativa e preview do builder | graficos reais, filtros dinamicos, drill-down, widgets embedaveis, configuracao por tenant com versionamento | Media/Alta |
| `Integrações` | estrutura preparada por metadados | campos de endpoint, headers, credenciais e schedule no builder | conectores reais com ERP/CRM, webhooks, filas, jobs agendados, monitoramento de falha e retries reais | Alta |
| `Observabilidade` | logs visuais simples no app | logs de execucao de workflow na interface | logging estruturado, metricas por tenant, tracing, alertas operacionais e telemetria para Azure | Alta |
| `Qualidade` | validacao manual e compilacao local | py_compile e verificacoes manuais | testes unitarios, integracao e e2e, lint, CI/CD, validacao de migracoes e regressao visual | Alta |
| `Windows runtime` | objetivo de empacotamento local | ha `pyinstaller.spec` no projeto | validar build completa no Windows, dependencias compativeis, script de inicializacao Windows e testes de operacao local | Alta |
| `Hospedagem Azure` | alvo estrategico definido | nenhuma infraestrutura Azure formalizada no repositorio | definir arquitetura de deploy: `Azure App Service`, `Azure Container Apps` ou `AKS`; configurar banco gerenciado, identidade, secrets, storage, monitoracao e pipeline de deploy | Critica |
| `Empacotamento e distribuicao` | `PyInstaller` previsto | arquivo `pyinstaller.spec` existe | validar geracao do executavel Windows, estrategia de atualizacao, armazenamento do banco local quando desktop e separacao entre modo desktop e modo SaaS | Media |

## Recomendacao objetiva para o seu cenario

Para o seu objetivo imediato, a sequencia mais coerente e:

1. estabilizar o `backend Python` e o `frontend Reflex/React` para producao;
2. substituir `SQLite` por banco adequado ao Azure antes de publicar;
3. implementar autenticacao segura com integracao `Azure AD` se houver usuarios corporativos;
4. publicar uma camada `REST API` real antes de ampliar integracoes low-code;
5. validar em paralelo dois modos de entrega:
   - `Windows desktop` com `PyInstaller`, se voce realmente precisa rodar localmente;
   - `Azure web SaaS`, como ambiente principal centralizado.

## Decisao arquitetural sugerida

Se a prioridade for SaaS hospedado no Azure, o caminho mais consistente hoje e:

- manter `Python + Reflex` no produto;
- evoluir de `SQLite` para um banco gerenciado no Azure;
- rodar a aplicacao como servico web/containerizado;
- tratar o executavel Windows como modo complementar, e nao como arquitetura principal.
