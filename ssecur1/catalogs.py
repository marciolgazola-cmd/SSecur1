SMARTLAB_ADMIN_PERMS = {
    "create:users",
    "edit:users",
    "delete:users",
    "reset_password:users",
    "create:clientes",
    "edit:clientes",
    "delete:clientes",
    "create:tenants",
    "edit:tenants",
    "delete:tenants",
    "create:roles",
    "edit:roles",
    "delete:roles",
    "create:responsabilidades",
    "edit:responsabilidades",
    "delete:responsabilidades",
    "create:forms",
    "edit:forms",
    "delete:forms",
}

CLIENTE_ADMIN_PERMS = {
    "create:users",
    "edit:users",
    "delete:users",
    "reset_password:users",
    "create:roles",
    "edit:roles",
    "delete:roles",
    "create:responsabilidades",
    "edit:responsabilidades",
    "delete:responsabilidades",
}

ROLE_PERMS = {
    "sem_acesso": set(),
    "smartlab_admin": SMARTLAB_ADMIN_PERMS,
    "smartlab_viewer": set(),
    "cliente_admin": CLIENTE_ADMIN_PERMS,
    "cliente_viewer": set(),
    "admin": SMARTLAB_ADMIN_PERMS,
    "editor": SMARTLAB_ADMIN_PERMS,
    "viewer": set(),
}

ROLE_TEMPLATE_OPTION_KEYS = [
    "smartlab_admin",
    "smartlab_viewer",
    "cliente_admin",
    "cliente_viewer",
]

ROLE_TEMPLATE_ALIASES = {
    "admin": "smartlab_admin",
    "editor": "smartlab_admin",
    "viewer": "smartlab_viewer",
}

ROLE_PERMISSION_CATALOG = [
    {"module": "Usuarios", "token": "create:users", "label": "Criar usuarios", "description": "Cadastrar novas contas no tenant."},
    {"module": "Usuarios", "token": "edit:users", "label": "Editar usuarios", "description": "Alterar cadastro, escopo e dados funcionais do usuario."},
    {"module": "Usuarios", "token": "delete:users", "label": "Excluir usuarios", "description": "Remover contas existentes do tenant."},
    {"module": "Usuarios", "token": "reset_password:users", "label": "Resetar senha", "description": "Gerar senha temporaria e forcar troca no proximo acesso."},
    {"module": "Clientes", "token": "create:clientes", "label": "Criar clientes", "description": "Cadastrar novos clientes e workspaces."},
    {"module": "Clientes", "token": "edit:clientes", "label": "Editar clientes", "description": "Atualizar dados cadastrais, grupos e estrutura."},
    {"module": "Clientes", "token": "delete:clientes", "label": "Excluir clientes", "description": "Remover clientes e seus vinculos."},
    {"module": "Tenants", "token": "create:tenants", "label": "Criar tenants", "description": "Criar novos workspaces e escopos operacionais."},
    {"module": "Tenants", "token": "edit:tenants", "label": "Editar tenants", "description": "Ajustar slug, limites e escopos de cliente."},
    {"module": "Tenants", "token": "delete:tenants", "label": "Excluir tenants", "description": "Remover tenants existentes."},
    {"module": "Papeis", "token": "create:roles", "label": "Criar papeis", "description": "Criar papeis customizados de acesso."},
    {"module": "Papeis", "token": "edit:roles", "label": "Editar papeis", "description": "Manter o baseline de permissoes dos papeis."},
    {"module": "Papeis", "token": "delete:roles", "label": "Excluir papeis", "description": "Remover papeis customizados."},
    {"module": "Responsabilidades", "token": "create:responsabilidades", "label": "Criar responsabilidades", "description": "Definir governanca e atribuicoes por papel."},
    {"module": "Responsabilidades", "token": "edit:responsabilidades", "label": "Editar responsabilidades", "description": "Ajustar aprovadores, revisores e operadores."},
    {"module": "Responsabilidades", "token": "delete:responsabilidades", "label": "Excluir responsabilidades", "description": "Remover vinculos de governanca."},
    {"module": "Formularios", "token": "create:forms", "label": "Criar formularios", "description": "Cadastrar novas pesquisas e formularios."},
    {"module": "Formularios", "token": "edit:forms", "label": "Editar formularios", "description": "Atualizar estrutura, etapas e conteudo."},
    {"module": "Formularios", "token": "delete:forms", "label": "Excluir formularios", "description": "Remover pesquisas e formularios."},
]

WORKFLOW_STAGE_LIBRARY = [
    {
        "key": "kickoff",
        "title": "Kickoff e Alinhamento",
        "box_type": "trigger",
        "zone": "left",
        "context": "Preparacao",
        "objective": "Alinhar escopo, patrocinadores, cronograma e combinados de operacao do projeto.",
        "owner": "Consultor SmartLab",
        "trigger": "Projeto contratado e cliente confirmado",
        "expected_output": "Kickoff validado e cronograma inicial aprovado",
    },
    {
        "key": "planejamento",
        "title": "Planejamento de Campo",
        "box_type": "etapa",
        "zone": "left",
        "context": "Preparacao",
        "objective": "Definir areas, publico, agenda de entrevistas, formularios e pontos de contato.",
        "owner": "Coordenacao do Projeto",
        "trigger": "Kickoff concluido",
        "expected_output": "Plano de campo e agenda operacional publicados",
    },
    {
        "key": "coleta",
        "title": "Coleta em Campo",
        "box_type": "coleta",
        "zone": "center",
        "context": "Execucao",
        "objective": "Executar entrevistas, visitas, rodas e capturar evidencias do cliente.",
        "owner": "Equipe de Campo",
        "trigger": "Agenda liberada e participantes confirmados",
        "expected_output": "Respostas, evidencias e apontamentos consolidados",
    },
    {
        "key": "analise",
        "title": "Analise e Diagnostico",
        "box_type": "analise",
        "zone": "center",
        "context": "Execucao",
        "objective": "Interpretar evidencias, maturidade e lacunas para gerar diagnostico preliminar.",
        "owner": "Especialista SmartLab",
        "trigger": "Coleta encerrada",
        "expected_output": "Diagnostico preliminar e principais achados",
    },
    {
        "key": "devolutiva",
        "title": "Devolutiva Executiva",
        "box_type": "relatorio",
        "zone": "right",
        "context": "Fechamento",
        "objective": "Apresentar achados, priorizacoes e riscos para lideranca e patrocinadores.",
        "owner": "Lider do Projeto",
        "trigger": "Diagnostico consolidado",
        "expected_output": "Devolutiva validada com direcionadores executivos",
    },
    {
        "key": "plano_acao",
        "title": "Plano de Acao e Follow-up",
        "box_type": "relatorio",
        "zone": "right",
        "context": "Fechamento",
        "objective": "Traduzir os achados em iniciativas, responsaveis, prazos e acompanhamento.",
        "owner": "Cliente e SmartLab",
        "trigger": "Devolutiva aprovada",
        "expected_output": "Plano de acao ativo e rotina de follow-up definida",
    },
]

API_RESOURCE_CATALOG = [
    {
        "name": "Projetos",
        "method": "GET",
        "path": "/api/v1/projects",
        "purpose": "Listar projetos por tenant",
        "kind": "core",
    },
    {
        "name": "Workflow Boxes",
        "method": "POST",
        "path": "/api/v1/projects/{id}/workflow-boxes",
        "purpose": "Adicionar caixas ao fluxo",
        "kind": "builder",
    },
    {
        "name": "Planos de Acao",
        "method": "PATCH",
        "path": "/api/v1/action-plans/{id}",
        "purpose": "Atualizar status e atingimento",
        "kind": "operations",
    },
    {
        "name": "Formularios",
        "method": "GET",
        "path": "/api/v1/forms",
        "purpose": "Listar formularios e categorias",
        "kind": "diagnostics",
    },
    {
        "name": "Respostas",
        "method": "POST",
        "path": "/api/v1/responses",
        "purpose": "Registrar respostas e scores",
        "kind": "diagnostics",
    },
    {
        "name": "Dashboards",
        "method": "GET",
        "path": "/api/v1/dashboard-boxes",
        "purpose": "Entregar widgets configurados por perfil",
        "kind": "analytics",
    },
]

PERMISSION_RESOURCE_CATALOG = [
    {
        "module": "Dashboard",
        "resource": "Dashboard Executivo",
        "label": "Dashboard Executivo",
        "description": "Visao consolidada de KPIs, tendencia e alertas principais.",
        "action": "read",
    },
    {
        "module": "Dashboard",
        "resource": "Dashboard Operacional",
        "label": "Dashboard Operacional",
        "description": "Leitura de indicadores operacionais, widgets e tabelas do tenant.",
        "action": "read",
    },
    {
        "module": "Clientes",
        "resource": "Clientes",
        "label": "Clientes",
        "description": "Visualizar a base de clientes, dados cadastrais e estrutura de grupo.",
        "action": "read",
    },
    {
        "module": "Clientes",
        "resource": "Gerenciar Clientes",
        "label": "Gerenciar Clientes",
        "description": "Criar, editar e excluir clientes e seus dados principais.",
        "action": "admin",
    },
    {
        "module": "Tenants",
        "resource": "Tenants",
        "label": "Tenants",
        "description": "Visualizar workspaces, escopo de clientes e limites configurados.",
        "action": "read",
    },
    {
        "module": "Tenants",
        "resource": "Gerenciar Tenants",
        "label": "Gerenciar Tenants",
        "description": "Criar, editar e excluir tenants e seus escopos operacionais.",
        "action": "admin",
    },
    {
        "module": "Usuarios",
        "resource": "Usuarios",
        "label": "Usuarios",
        "description": "Visualizar contas, vínculos de cliente, tenant e perfil funcional.",
        "action": "read",
    },
    {
        "module": "Usuarios",
        "resource": "Gerenciar Usuarios",
        "label": "Gerenciar Usuarios",
        "description": "Criar, editar, redefinir contexto e excluir usuários do escopo permitido.",
        "action": "admin",
    },
    {
        "module": "Projetos",
        "resource": "Projetos",
        "label": "Projetos",
        "description": "Consulta do escopo, status e configuracoes do projeto.",
        "action": "read",
    },
    {
        "module": "Projetos",
        "resource": "Gerenciar Projetos",
        "label": "Gerenciar Projetos",
        "description": "Criar, editar e reorganizar projetos, vínculos e workflow.",
        "action": "write",
    },
    {
        "module": "Planos",
        "resource": "Plano de Acoes",
        "label": "Plano de Acoes",
        "description": "Visualizacao e acompanhamento do plano de acao.",
        "action": "read",
    },
    {
        "module": "Planos",
        "resource": "Editar Plano de Acoes",
        "label": "Editar Plano de Acoes",
        "description": "Permite criar ou alterar responsaveis, prazos e status.",
        "action": "write",
    },
    {
        "module": "Relatorios",
        "resource": "Relatorio Executivo",
        "label": "Relatorio Executivo",
        "description": "Resumo executivo com findings, metricas e recomendacoes.",
        "action": "read",
    },
    {
        "module": "Relatorios",
        "resource": "Relatorio Detalhado",
        "label": "Relatorio Detalhado",
        "description": "Detalhamento por dimensao, area, respondente e evidencias.",
        "action": "read",
    },
    {
        "module": "Formularios",
        "resource": "Formularios",
        "label": "Formularios",
        "description": "Consulta dos instrumentos de pesquisa, etapas e questões publicadas.",
        "action": "read",
    },
    {
        "module": "Formularios",
        "resource": "Gerenciar Formularios",
        "label": "Gerenciar Formularios",
        "description": "Criar, editar e excluir formulários, etapas e estrutura de perguntas.",
        "action": "write",
    },
    {
        "module": "Respostas",
        "resource": "Entrevistas e Respostas",
        "label": "Entrevistas e Respostas",
        "description": "Visualizar sessões, contexto ativo, respostas e scores registrados.",
        "action": "read",
    },
    {
        "module": "Respostas",
        "resource": "Operar Entrevistas e Respostas",
        "label": "Operar Entrevistas e Respostas",
        "description": "Criar entrevistas, registrar respostas, atualizar score e concluir sessões.",
        "action": "write",
    },
    {
        "module": "Permissoes",
        "resource": "Template RBAC",
        "label": "Template RBAC",
        "description": "Visualizar templates base de papel, escopo e baseline de acesso.",
        "action": "read",
    },
    {
        "module": "Permissoes",
        "resource": "Canvas de Permissoes",
        "label": "Canvas de Permissoes",
        "description": "Liberar ou bloquear módulos, recursos e ações por usuário.",
        "action": "admin",
    },
    {
        "module": "Permissoes",
        "resource": "Papeis e Responsabilidades",
        "label": "Papeis e Responsabilidades",
        "description": "Criar papéis customizados, definir responsabilidades e manter governança de acesso.",
        "action": "admin",
    },
    {
        "module": "APIs",
        "resource": "APIs e Integrações",
        "label": "APIs e Integrações",
        "description": "Visualizar e operar integrações, conectores e parâmetros técnicos do tenant.",
        "action": "admin",
    },
    {
        "module": "Auditoria",
        "resource": "Auditoria",
        "label": "Auditoria",
        "description": "Consultar trilha de eventos, acessos, decisões e uso do sistema.",
        "action": "read",
    },
    {
        "module": "IA",
        "resource": "Especialista IA",
        "label": "Especialista IA",
        "description": "Acessar o assistente, contexto RAG e exploração analítica do tenant.",
        "action": "read",
    },
    {
        "module": "IA",
        "resource": "Operar Especialista IA",
        "label": "Operar Especialista IA",
        "description": "Gerenciar documentos, contexto e automações analíticas do Especialista IA.",
        "action": "write",
    },
]

RESOURCE_PERMISSION_TOKENS = {
    "Gerenciar Clientes": {"create:clientes", "edit:clientes", "delete:clientes"},
    "Gerenciar Tenants": {"create:tenants", "edit:tenants", "delete:tenants"},
    "Gerenciar Usuarios": {"create:users", "edit:users", "delete:users", "reset_password:users"},
    "Gerenciar Projetos": {"create:forms", "edit:forms", "delete:forms"},
    "Editar Plano de Acoes": {"create:forms", "edit:forms"},
    "Gerenciar Formularios": {"create:forms", "edit:forms", "delete:forms"},
    "Operar Entrevistas e Respostas": {"create:forms", "edit:forms"},
    "Canvas de Permissoes": {"create:roles", "edit:roles", "delete:roles"},
    "Papeis e Responsabilidades": {
        "create:roles",
        "edit:roles",
        "delete:roles",
        "create:responsabilidades",
        "edit:responsabilidades",
        "delete:responsabilidades",
    },
    "APIs e Integrações": set(),
    "Operar Especialista IA": set(),
}

CATALOG_SCOPE_DEFAULT = "default"
CATALOG_SCOPE_CURRENT = "current"
CATALOG_SCOPE_BY_KEY = {
    "business_sector": CATALOG_SCOPE_CURRENT,
    "user_profession": CATALOG_SCOPE_CURRENT,
    "user_department": CATALOG_SCOPE_CURRENT,
    "smartlab_service": CATALOG_SCOPE_DEFAULT,
    "survey_stage": CATALOG_SCOPE_DEFAULT,
    "question_dimension": CATALOG_SCOPE_DEFAULT,
}


def _catalog_tenant_for_key(current_tenant: str, catalog_key: str) -> str:
    if CATALOG_SCOPE_BY_KEY.get(catalog_key) == CATALOG_SCOPE_DEFAULT:
        return "default"
    return current_tenant


ROLE_TEMPLATE_CATALOG = {
    "smartlab_admin": {
        "label": "SmartLab Admin",
        "scope": "smartlab",
        "description": "Acesso operacional e administrativo total sobre clientes, tenants, usuários, permissões e formulários.",
        "permissions": sorted(SMARTLAB_ADMIN_PERMS),
    },
    "smartlab_viewer": {
        "label": "SmartLab Viewer",
        "scope": "smartlab",
        "description": "Acesso amplo de leitura ao ecossistema SmartLab, sem operações de criação, edição ou exclusão.",
        "permissions": [],
    },
    "cliente_admin": {
        "label": "Cliente Admin",
        "scope": "cliente",
        "description": "Administra usuários, papéis, responsabilidades e acessos do próprio tenant do cliente.",
        "permissions": sorted(CLIENTE_ADMIN_PERMS),
    },
    "cliente_viewer": {
        "label": "Cliente Viewer",
        "scope": "cliente",
        "description": "Leitura total do próprio tenant do cliente, sem alterações operacionais ou administrativas.",
        "permissions": [],
    },
    "admin": {
        "label": "SmartLab Admin",
        "scope": "smartlab",
        "description": "Alias legado para SmartLab Admin.",
        "permissions": sorted(SMARTLAB_ADMIN_PERMS),
    },
    "editor": {
        "label": "SmartLab Admin",
        "scope": "smartlab",
        "description": "Alias legado para SmartLab Admin.",
        "permissions": sorted(SMARTLAB_ADMIN_PERMS),
    },
    "viewer": {
        "label": "SmartLab Viewer",
        "scope": "smartlab",
        "description": "Alias legado para SmartLab Viewer.",
        "permissions": [],
    },
}

BRAZILIAN_STATE_CODES = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
]
