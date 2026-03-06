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
