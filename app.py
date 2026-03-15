import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

import reflex as rx
from ssecur1.db import (
    ActionPlanModel,
    ClientModel,
    DashboardBoxModel,
    FormModel,
    InterviewSessionModel,
    PermissionBoxModel,
    ProjectAssignmentModel,
    ProjectModel,
    QuestionModel,
    ResponseModel,
    ResponsibilityModel,
    RoleModel,
    SessionLocal,
    SurveyModel,
    TenantModel,
    UserModel,
    WorkflowBoxModel,
)
from ssecur1.state.session import SessionStateMixin
from ssecur1.utils import (
    build_client_children_map as _build_client_children_map,
    collect_descendant_client_ids as _collect_descendant_client_ids,
    dimension_maturity_label as _dimension_maturity_label,
    dom_token as _dom_token,
    format_brl_amount as _format_brl_amount,
    loads_json as _loads_json,
    parse_brl_amount as _parse_brl_amount,
    parse_int as _parse_int,
    question_payload as _question_payload,
    slugify as _slugify,
)


ROLE_PERMS = {
    "admin": {
        "create:users",
        "edit:users",
        "delete:users",
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
    },
    "editor": {
        "create:users",
        "edit:users",
        "create:clientes",
        "edit:clientes",
        "delete:clientes",
        "create:tenants",
        "edit:tenants",
        "create:roles",
        "edit:roles",
        "create:responsabilidades",
        "edit:responsabilidades",
        "create:forms",
        "edit:forms",
    },
    "viewer": set(),
}


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
        "resource": "Progresso do Projeto",
        "label": "Progresso do Projeto",
        "description": "Leitura do andamento, marcos e status do projeto do cliente.",
        "action": "read",
    },
    {
        "module": "Projetos",
        "resource": "Projetos",
        "label": "Projetos",
        "description": "Consulta do escopo, status e configuracoes do projeto.",
        "action": "read",
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
        "description": "Consulta dos instrumentos de pesquisa publicados.",
        "action": "read",
    },
    {
        "module": "Formularios",
        "resource": "Responder Formularios",
        "label": "Responder Formularios",
        "description": "Permite responder formularios associados ao tenant.",
        "action": "write",
    },
    {
        "module": "Usuarios",
        "resource": "Usuarios do Cliente",
        "label": "Usuarios do Cliente",
        "description": "Administracao limitada dos usuarios vinculados ao cliente.",
        "action": "admin",
    },
]

ROLE_TEMPLATE_CATALOG = {
    "admin": {
        "label": "Admin SmartLab",
        "scope": "smartlab",
        "description": "Controle total do tenant e das operacoes da consultoria.",
        "permissions": [
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
        ],
    },
    "editor": {
        "label": "Consultor SmartLab",
        "scope": "smartlab",
        "description": "Opera clientes, projetos, formularios e planos de acao.",
        "permissions": [
            "create:clientes",
            "edit:clientes",
            "delete:clientes",
            "create:tenants",
            "edit:tenants",
            "create:roles",
            "edit:roles",
            "create:responsabilidades",
            "edit:responsabilidades",
            "create:forms",
            "edit:forms",
        ],
    },
    "viewer": {
        "label": "Leitura Interna",
        "scope": "smartlab",
        "description": "Acesso somente leitura para acompanhamento interno.",
        "permissions": [],
    },
    "cliente_admin": {
        "label": "Administrador do Cliente",
        "scope": "cliente",
        "description": "Administra acessos internos e acompanha entregaveis liberados.",
        "permissions": ["read:dashboard", "read:relatorios", "manage:usuarios_cliente"],
    },
    "cliente_viewer": {
        "label": "Leitura do Cliente",
        "scope": "cliente",
        "description": "Consulta dashboards, relatorios e planos autorizados.",
        "permissions": ["read:dashboard", "read:relatorios"],
    },
}

BRAZILIAN_STATE_CODES = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
]
def smartlab_logo(size: str = "44px") -> rx.Component:
    return rx.image(
        src="/LogoSmartLab.jpeg",
        width=size,
        height="auto",
        alt="Logo SSecur1",
        border_radius="10px",
        object_fit="contain",
    )


class State(SessionStateMixin):
    dragged_question_text: str = ""
    uploaded_resources: list[str] = []
    global_search_query: str = ""

    new_user_name: str = ""
    new_user_email: str = ""
    new_user_password: str = ""
    new_user_role: str = "viewer"
    new_user_scope: str = "smartlab"
    new_user_client_id: str = ""
    new_user_tenant_id: str = "default"
    new_user_profession: str = "Analista"
    new_user_custom_profession: str = ""
    new_user_department: str = "Operacao"
    new_user_custom_department: str = ""
    new_user_reports_to_user_id: str = ""
    new_user_assigned_client_ids: list[str] = []
    new_user_assigned_clients_open: bool = False

    new_client_name: str = ""
    new_client_trade_name: str = ""
    new_client_email: str = ""
    new_client_phone: str = ""
    new_client_address: str = ""
    new_client_state_code: str = "SP"
    new_client_cnpj: str = ""
    new_client_business_sector: str = "Industria"
    new_client_custom_business_sector: str = ""
    new_client_employee_count: str = ""
    new_client_branch_count: str = ""
    new_client_annual_revenue: str = ""
    new_client_parent_id: str = ""
    editing_client_id: str = ""

    new_tenant_name: str = ""
    new_tenant_slug: str = ""
    new_tenant_limit: str = "50"
    new_tenant_client_id: str = ""
    editing_tenant_id: str = ""

    new_role_name: str = ""
    new_role_permissions: str = "create:clientes,edit:clientes"
    editing_role_id: str = ""

    new_resp_role_id: str = ""
    new_resp_desc: str = ""
    editing_resp_id: str = ""

    new_form_name: str = ""
    new_form_category: str = "Diagnóstico Cultura de Segurança"
    new_form_target_client_id: str = ""
    new_form_target_user_email: str = ""
    selected_form_id: str = ""
    editing_form_id: str = ""
    editing_question_id: str = ""
    new_interview_form_id: str = ""
    new_interview_project_id: str = ""
    new_interview_client_id: str = ""
    new_interview_user_id: str = ""
    new_interview_date: str = ""
    new_interview_notes: str = ""
    editing_interview_id: str = ""
    new_question_text: str = ""
    new_question_type: str = "escala_0_5"
    new_question_dimension: str = "Presença"
    new_question_custom_dimension: str = ""
    new_question_weight: str = "1"
    new_question_polarity: str = "positiva"
    new_question_options: str = "Nada Aderente,Pouco Aderente,Parcialmente Aderente,Moderadamente Aderente,Muito Aderente,Totalmente Aderente"
    new_question_condition: str = ""
    editing_user_id: str = ""

    ai_prompt: str = ""
    ai_answer: str = ""

    new_project_name: str = ""
    new_project_type: str = "Diagnóstico de Cultura"
    project_admin_tab: str = "cadastro"
    new_project_assigned_client_ids: list[str] = []
    new_project_assigned_clients_open: bool = False
    new_box_title: str = ""
    new_box_type: str = "etapa"
    new_box_method: str = "GET"
    new_box_endpoint: str = ""
    new_box_headers: str = "Authorization: Bearer token"
    new_box_retry_policy: str = "none"
    new_box_client_id: str = ""
    new_box_client_secret: str = ""
    new_box_schedule: str = "0 8 * * 1-5"
    new_box_zone: str = "center"
    new_box_condition: str = ""
    new_box_output_key: str = ""
    new_sticky_note_text: str = ""
    workflow_logs: list[str] = []

    new_action_title: str = ""
    new_action_owner: str = ""
    new_action_due_date: str = ""
    new_action_expected_result: str = ""

    perm_user_email: str = ""
    perm_selected_module: str = "Todos"
    perm_selected_role_template: str = "cliente_admin"

    new_dashboard_box_title: str = ""
    new_dashboard_box_kind: str = "kpi"
    new_dashboard_box_scope: str = "consultor"
    new_dashboard_box_source: str = "projetos"
    new_dashboard_box_description: str = ""

    testimonial_index: int = 0

    def _visible_client_ids(self, session) -> set[int] | None:
        if not (self.user_scope == "cliente" and self.user_client_id.isdigit()):
            return None
        root_id = int(self.user_client_id)
        rows = session.query(ClientModel.id, ClientModel.parent_client_id).all()
        child_pairs = [
            ClientModel(id=row[0], parent_client_id=row[1])  # type: ignore[call-arg]
            for row in rows
        ]
        children_map = _build_client_children_map(child_pairs)
        return {root_id, *_collect_descendant_client_ids(children_map, root_id)}

    @rx.var(cache=False)
    def tenant_options(self) -> list[str]:
        session = SessionLocal()
        query = session.query(TenantModel)
        if self.user_scope == "cliente" and self.home_tenant_id:
            query = query.filter(TenantModel.id == self.home_tenant_id)
        elif self.user_scope == "smartlab" and self.user_role != "admin":
            assigned_ids = [int(item) for item in self.assigned_client_ids if item.isdigit()]
            if assigned_ids:
                query = query.filter((TenantModel.id == "default") | (TenantModel.owner_client_id.in_(assigned_ids)))
            else:
                query = query.filter(TenantModel.id == "default")
        data = [t.id for t in query.order_by(TenantModel.name.asc()).all()]
        session.close()
        return data

    @rx.var(cache=False)
    def tenant_display_options(self) -> list[str]:
        session = SessionLocal()
        query = session.query(TenantModel)
        if self.user_scope == "cliente" and self.home_tenant_id:
            query = query.filter(TenantModel.id == self.home_tenant_id)
        elif self.user_scope == "smartlab" and self.user_role != "admin":
            assigned_ids = [int(item) for item in self.assigned_client_ids if item.isdigit()]
            if assigned_ids:
                query = query.filter((TenantModel.id == "default") | (TenantModel.owner_client_id.in_(assigned_ids)))
            else:
                query = query.filter(TenantModel.id == "default")
        rows = query.order_by(TenantModel.name.asc()).all()
        session.close()
        return [
            "SmartLab - interno" if row.id == "default" else f"{row.name} - cliente"
            for row in rows
        ]

    @rx.var(cache=False)
    def current_tenant_display(self) -> str:
        session = SessionLocal()
        tenant = session.query(TenantModel).filter(TenantModel.id == self.current_tenant).first()
        session.close()
        if not tenant:
            return self.current_tenant
        return "SmartLab - interno" if tenant.id == "default" else f"{tenant.name} - cliente"

    @rx.var(cache=False)
    def global_search_results(self) -> list[dict[str, str]]:
        term = self.global_search_query.strip().lower()
        if len(term) < 2:
            return []
        session = SessionLocal()
        results: list[dict[str, str]] = []

        client_query = session.query(ClientModel)
        visible_client_ids = self._visible_client_ids(session)
        if visible_client_ids is not None:
            if not visible_client_ids:
                session.close()
                return []
            client_query = client_query.filter(ClientModel.id.in_(sorted(visible_client_ids)))
        else:
            client_query = client_query.filter(ClientModel.tenant_id == self.current_tenant)
        clients = client_query.order_by(ClientModel.name.asc()).all()
        for row in clients:
            haystack = " ".join(
                [
                    row.name or "",
                    row.trade_name or "",
                    row.email or "",
                    row.cnpj or "",
                    row.business_sector or "",
                ]
            ).lower()
            if term in haystack:
                results.append(
                    {
                        "kind": "Cliente",
                        "title": row.name,
                        "subtitle": f"{row.email} • {row.cnpj or 'Sem CNPJ'}",
                        "view": "clientes",
                        "record_id": str(row.id),
                    }
                )

        form_query = session.query(FormModel).filter(FormModel.tenant_id == self.current_tenant)
        for row in form_query.order_by(FormModel.name.asc()).all():
            haystack = f"{row.name} {row.category}".lower()
            if term in haystack:
                results.append(
                    {
                        "kind": "Formulario",
                        "title": row.name,
                        "subtitle": row.category,
                        "view": "formularios",
                        "record_id": str(row.id),
                    }
                )

        user_query = session.query(UserModel).filter(UserModel.tenant_id == self.current_tenant)
        for row in user_query.order_by(UserModel.name.asc()).all():
            haystack = f"{row.name} {row.email} {row.role}".lower()
            if term in haystack:
                results.append(
                    {
                        "kind": "Usuario",
                        "title": row.name,
                        "subtitle": f"{row.email} • {row.role}",
                        "view": "usuarios",
                        "record_id": str(row.id),
                    }
                )

        if self.user_scope == "smartlab":
            role_query = session.query(RoleModel).filter(RoleModel.tenant_id == self.current_tenant)
            for row in role_query.order_by(RoleModel.name.asc()).all():
                haystack = f"{row.name} {row.permissions or ''}".lower()
                if term in haystack:
                    results.append(
                        {
                            "kind": "Papel",
                            "title": row.name,
                            "subtitle": "Permissoes configuraveis",
                            "view": "papeis",
                            "record_id": str(row.id),
                        }
                    )

        session.close()
        return results[:8]

    @rx.var
    def can_manage_clients(self) -> bool:
        return "create:clientes" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_manage_users(self) -> bool:
        return "create:users" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_delete_users(self) -> bool:
        return "delete:users" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_delete_clients(self) -> bool:
        return "delete:clientes" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_manage_tenants(self) -> bool:
        return "create:tenants" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_delete_tenants(self) -> bool:
        return "delete:tenants" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_manage_roles(self) -> bool:
        return "create:roles" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_delete_roles(self) -> bool:
        return "delete:roles" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_manage_resps(self) -> bool:
        return "create:responsabilidades" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_delete_resps(self) -> bool:
        return "delete:responsabilidades" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_manage_forms(self) -> bool:
        return "create:forms" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_delete_forms(self) -> bool:
        return "delete:forms" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_operate_interviews(self) -> bool:
        return self.user_scope == "smartlab" and self.current_tenant == "default" and self.can_manage_forms

    @rx.var
    def show_menu_clients(self) -> bool:
        return self.user_scope == "smartlab"

    @rx.var
    def show_menu_tenants(self) -> bool:
        return self.user_scope == "smartlab" and self.user_role == "admin"

    @rx.var
    def show_menu_users(self) -> bool:
        return self.user_scope == "smartlab" or self.user_role == "cliente_admin"

    @rx.var
    def show_menu_permissions(self) -> bool:
        return self.user_scope == "smartlab" or self.user_role == "cliente_admin"

    @rx.var
    def show_menu_dashboard(self) -> bool:
        return True

    @rx.var
    def show_menu_projects(self) -> bool:
        return self.user_scope == "smartlab" and self.current_tenant == "default"

    @rx.var
    def show_menu_plans(self) -> bool:
        return True

    @rx.var
    def show_menu_apis(self) -> bool:
        return self.user_scope == "smartlab" and self.user_role in {"admin", "editor"}

    @rx.var
    def show_menu_roles(self) -> bool:
        return self.user_scope == "smartlab"

    @rx.var
    def show_menu_responsibilities(self) -> bool:
        return self.user_scope == "smartlab"

    @rx.var
    def show_menu_forms(self) -> bool:
        return self.user_scope == "smartlab"

    @rx.var
    def show_menu_ai(self) -> bool:
        return self.user_scope == "smartlab"

    def has_perm(self, perm: str) -> bool:
        return perm in ROLE_PERMS.get(self.user_role, set())

    @rx.var(cache=False)
    def tenants_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        query = session.query(TenantModel)
        if self.user_scope == "cliente" and self.home_tenant_id:
            query = query.filter(TenantModel.id == self.home_tenant_id)
        rows = query.order_by(TenantModel.created_at.desc()).all()
        client_lookup = {row[0]: row[1] for row in session.query(ClientModel.id, ClientModel.name).all()}
        client_cnpj_lookup = {row[0]: row[1] or "-" for row in session.query(ClientModel.id, ClientModel.cnpj).all()}
        data = [
            {
                "id": r.id,
                "name": r.name,
                "slug": r.slug,
                "limit": r.limit_users,
                "owner_client_id": str(r.owner_client_id) if r.owner_client_id is not None else "-",
                "owner_client_name": client_lookup.get(r.owner_client_id, "SmartLab"),
                "owner_client_cnpj": client_cnpj_lookup.get(r.owner_client_id, "-"),
                "created_at": r.created_at.strftime("%Y-%m-%d") if r.created_at else "-",
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def clients_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        query = session.query(ClientModel)
        visible_client_ids = self._visible_client_ids(session)
        if visible_client_ids is not None:
            if not visible_client_ids:
                session.close()
                return []
            query = query.filter(ClientModel.id.in_(sorted(visible_client_ids)))
        else:
            query = query.filter(ClientModel.tenant_id == self.current_tenant)
        rows = query.order_by(ClientModel.created_at.desc()).all()
        all_clients = session.query(ClientModel).order_by(ClientModel.name.asc()).all()
        tenant_lookup = {str(row[0]): row[1] for row in session.query(TenantModel.owner_client_id, TenantModel.id).all() if row[0] is not None}
        client_name_lookup = {int(row.id): row.name for row in all_clients}
        children_map = _build_client_children_map(all_clients)
        data = [
            {
                "id": r.id,
                "name": r.name,
                "trade_name": r.trade_name or "-",
                "email": r.email,
                "cnpj": r.cnpj or "-",
                "business_sector": r.business_sector or "-",
                "employee_count": str(r.employee_count) if r.employee_count is not None else "-",
                "branch_count": str(r.branch_count) if r.branch_count is not None else "-",
                "annual_revenue": _format_brl_amount(r.annual_revenue),
                "tenant_id": r.tenant_id,
                "base_tenant_label": "SmartLab (default)" if r.tenant_id == "default" else r.tenant_id,
                "parent_client_name": client_name_lookup.get(int(r.parent_client_id), "-") if r.parent_client_id is not None else "-",
            }
            for r in rows
        ]
        for row in data:
            row["workspace_tenant"] = tenant_lookup.get(str(row["id"]), "-")
            child_names = [
                client_name_lookup.get(child_id, str(child_id))
                for child_id in sorted(children_map.get(int(row["id"]), []))
            ]
            row["group_children"] = ", ".join(child_names) if child_names else "-"
        session.close()
        return data

    @rx.var(cache=False)
    def client_display_options(self) -> list[str]:
        return [f"{client_id} - {name}" for client_id, name in self.client_lookup.items()]

    @rx.var(cache=False)
    def assignable_client_options(self) -> list[dict[str, str]]:
        return [{"id": client_id, "name": name} for client_id, name in self.client_lookup.items()]

    @rx.var(cache=False)
    def client_options(self) -> list[str]:
        session = SessionLocal()
        query = session.query(ClientModel)
        visible_client_ids = self._visible_client_ids(session)
        if visible_client_ids is not None:
            if not visible_client_ids:
                session.close()
                return []
            query = query.filter(ClientModel.id.in_(sorted(visible_client_ids)))
        rows = query.order_by(ClientModel.name.asc()).all()
        session.close()
        return [str(client.id) for client in rows]

    @rx.var(cache=False)
    def client_lookup(self) -> dict[str, str]:
        session = SessionLocal()
        query = session.query(ClientModel)
        visible_client_ids = self._visible_client_ids(session)
        if visible_client_ids is not None:
            if not visible_client_ids:
                session.close()
                return {}
            query = query.filter(ClientModel.id.in_(sorted(visible_client_ids)))
        rows = query.order_by(ClientModel.name.asc()).all()
        session.close()
        return {str(client.id): client.name for client in rows}

    @rx.var(cache=False)
    def group_parent_client_options(self) -> list[str]:
        session = SessionLocal()
        query = session.query(ClientModel).filter(ClientModel.tenant_id == self.current_tenant)
        editing_client_id = int(self.editing_client_id) if self.editing_client_id.isdigit() else None
        excluded_ids: set[int] = set()
        if editing_client_id is not None:
            excluded_ids = {editing_client_id, *_collect_descendant_client_ids(
                _build_client_children_map(session.query(ClientModel).all()),
                editing_client_id,
            )}
        rows = query.order_by(ClientModel.name.asc()).all()
        session.close()
        return [f"{row.id} - {row.name}" for row in rows if int(row.id) not in excluded_ids]

    @rx.var
    def selected_new_client_parent_option(self) -> str:
        if not self.new_client_parent_id:
            return ""
        session = SessionLocal()
        row = session.query(ClientModel).filter(ClientModel.id == int(self.new_client_parent_id)).first()
        session.close()
        return f"{row.id} - {row.name}" if row else ""

    @rx.var(cache=False)
    def user_workspace_options(self) -> list[str]:
        session = SessionLocal()
        query = session.query(TenantModel)
        if self.user_scope == "cliente" and self.home_tenant_id:
            query = query.filter(TenantModel.id == self.home_tenant_id)
        rows = query.order_by(TenantModel.name.asc()).all()
        session.close()
        return [f"{row.id} - {row.name}" for row in rows]

    @rx.var
    def selected_new_user_workspace_option(self) -> str:
        if not self.new_user_tenant_id:
            return ""
        session = SessionLocal()
        tenant = session.query(TenantModel).filter(TenantModel.id == self.new_user_tenant_id).first()
        session.close()
        return f"{tenant.id} - {tenant.name}" if tenant else self.new_user_tenant_id

    @rx.var
    def selected_new_user_client_option(self) -> str:
        if not self.new_user_client_id:
            return ""
        name = self.client_lookup.get(self.new_user_client_id, "")
        return f"{self.new_user_client_id} - {name}" if name else ""

    @rx.var(cache=False)
    def reporting_user_options(self) -> list[str]:
        session = SessionLocal()
        target_tenant = "default" if self.new_user_scope == "smartlab" else (self.new_user_tenant_id or self.current_tenant)
        rows = (
            session.query(UserModel)
            .filter(UserModel.tenant_id == target_tenant)
            .order_by(UserModel.name.asc())
            .all()
        )
        session.close()
        return [
            f"{row.id} - {row.name} - {row.profession or 'Sem cargo'} - {row.department or 'Sem departamento'}"
            for row in rows
        ]

    @rx.var
    def selected_reporting_user_option(self) -> str:
        if not self.new_user_reports_to_user_id:
            return ""
        session = SessionLocal()
        user = session.query(UserModel).filter(UserModel.id == int(self.new_user_reports_to_user_id)).first()
        session.close()
        return (
            f"{user.id} - {user.name} - {user.profession or 'Sem cargo'} - {user.department or 'Sem departamento'}"
            if user
            else ""
        )

    @rx.var(cache=False)
    def client_display_options(self) -> list[str]:
        return [f"{client_id} - {name}" for client_id, name in self.client_lookup.items()]

    @rx.var
    def selected_new_tenant_client_option(self) -> str:
        if not self.new_tenant_client_id:
            return ""
        name = self.client_lookup.get(self.new_tenant_client_id, "")
        return f"{self.new_tenant_client_id} - {name}" if name else ""

    @rx.var(cache=False)
    def business_sector_options(self) -> list[str]:
        base_options = ["Industria", "Servicos", "Varejo", "Logistica"]
        session = SessionLocal()
        custom_options = [
            row[0].strip()
            for row in session.query(ClientModel.business_sector)
            .filter(
                ClientModel.tenant_id == self.current_tenant,
                ClientModel.business_sector.is_not(None),
            )
            .all()
            if row[0] and row[0].strip()
        ]
        session.close()
        dynamic_options = sorted({option for option in custom_options if option not in base_options})
        return [*base_options, *dynamic_options, "Outro"]

    @rx.var
    def brazilian_state_options(self) -> list[str]:
        return BRAZILIAN_STATE_CODES

    @rx.var(cache=False)
    def form_target_client_options(self) -> list[str]:
        return [f"{client_id} - {name}" for client_id, name in self.client_lookup.items()]

    @rx.var(cache=False)
    def form_target_user_options(self) -> list[str]:
        session = SessionLocal()
        rows = (
            session.query(UserModel.email, UserModel.name)
            .filter(UserModel.tenant_id == self.current_tenant)
            .order_by(UserModel.name.asc())
            .all()
        )
        session.close()
        return [f"{email} - {name or email}" for email, name in rows if email]

    @rx.var(cache=False)
    def question_dimension_options(self) -> list[str]:
        base_options = [
            "Presença",
            "Correção",
            "Reconhecimento",
            "Comunicação",
            "Disciplina/Exemplo",
        ]
        session = SessionLocal()
        query = session.query(QuestionModel.dimension).filter(
            QuestionModel.tenant_id == self.current_tenant,
            QuestionModel.dimension.is_not(None),
        )
        if self.selected_form_id.isdigit():
            query = query.filter(QuestionModel.survey_id == int(self.selected_form_id))
        custom_options = [
            row[0].strip()
            for row in query.all()
            if row[0] and row[0].strip()
        ]
        session.close()
        dynamic_options = sorted({option for option in custom_options if option not in base_options})
        return [*base_options, *dynamic_options, "Outro"]

    @rx.var
    def question_polarity_options(self) -> list[str]:
        return ["positiva", "negativa"]

    @rx.var
    def question_weight_options(self) -> list[str]:
        return ["1", "2", "3", "4", "5"]

    @rx.var
    def selected_form_target_client_option(self) -> str:
        if not self.new_form_target_client_id:
            return ""
        name = self.client_lookup.get(self.new_form_target_client_id, "")
        return f"{self.new_form_target_client_id} - {name}" if name else ""

    @rx.var(cache=False)
    def selected_form_target_user_option(self) -> str:
        if not self.new_form_target_user_email:
            return ""
        session = SessionLocal()
        row = (
            session.query(UserModel.email, UserModel.name)
            .filter(
                UserModel.tenant_id == self.current_tenant,
                UserModel.email == self.new_form_target_user_email,
            )
            .first()
        )
        session.close()
        if not row:
            return self.new_form_target_user_email
        return f"{row[0]} - {row[1] or row[0]}"

    @rx.var
    def is_editing_client(self) -> bool:
        return self.editing_client_id != ""

    @rx.var
    def client_submit_label(self) -> str:
        return "Salvar Alterações" if self.is_editing_client else "Cadastrar Cliente e Workspace"

    @rx.var
    def is_editing_user(self) -> bool:
        return self.editing_user_id != ""

    @rx.var
    def user_submit_label(self) -> str:
        return "Salvar Alterações" if self.is_editing_user else "Criar Usuario"

    @rx.var
    def user_password_help_text(self) -> str:
        if self.is_editing_user:
            return "Preencha apenas se quiser redefinir a senha. Para usuario de cliente, a nova senha exigira troca no primeiro acesso."
        return "Para usuario de cliente, essa senha sera obrigatoriamente trocada no primeiro acesso."

    @rx.var
    def is_editing_tenant(self) -> bool:
        return self.editing_tenant_id != ""

    @rx.var
    def tenant_submit_label(self) -> str:
        return "Salvar Alterações" if self.is_editing_tenant else "Criar Tenant"

    @rx.var
    def is_editing_role(self) -> bool:
        return self.editing_role_id != ""

    @rx.var
    def role_submit_label(self) -> str:
        return "Salvar Alterações" if self.is_editing_role else "Criar Papel"

    @rx.var
    def is_editing_resp(self) -> bool:
        return self.editing_resp_id != ""

    @rx.var
    def resp_submit_label(self) -> str:
        return "Salvar Alterações" if self.is_editing_resp else "Adicionar"

    @rx.var
    def is_editing_form(self) -> bool:
        return self.editing_form_id != ""

    @rx.var
    def form_submit_label(self) -> str:
        return "Salvar Alterações" if self.is_editing_form else "Salvar Formulário"

    @rx.var(cache=False)
    def users_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        rows = (
            session.query(UserModel)
            .filter(UserModel.tenant_id == self.current_tenant)
            .order_by(UserModel.id.desc())
            .all()
        )
        client_lookup = {row[0]: row[1] for row in session.query(ClientModel.id, ClientModel.name).all()}
        user_lookup = {row[0]: row[1] for row in session.query(UserModel.id, UserModel.name).all()}
        assigned_client_lookup = {row[0]: row[1] for row in session.query(ClientModel.id, ClientModel.name).all()}
        data = [
            {
                "id": r.id,
                "name": r.name,
                "email": r.email,
                "role": r.role or "viewer",
                "account_scope": r.account_scope or "smartlab",
                "client_id": str(r.client_id or ""),
                "client_name": client_lookup.get(r.client_id, "-"),
                "profession": r.profession or "-",
                "department": r.department or "-",
                "reports_to_user_name": user_lookup.get(r.reports_to_user_id, "-"),
                "must_change_password": "Sim" if int(r.must_change_password or 0) == 1 else "Nao",
                "assigned_clients": ", ".join(
                    assigned_client_lookup.get(int(item), item)
                    for item in _loads_json(r.assigned_client_ids, [])
                    if str(item).isdigit()
                ) or "-",
                "tenant_id": r.tenant_id,
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var
    def user_role_options(self) -> list[str]:
        return list(ROLE_TEMPLATE_CATALOG.keys())

    @rx.var
    def user_scope_options(self) -> list[str]:
        return ["smartlab", "cliente"]

    @rx.var
    def profession_options(self) -> list[str]:
        return ["Analista", "Motorista", "Coordenador", "Supervisor", "Gerente", "Diretor", "CEO", "Outro"]

    @rx.var
    def department_options(self) -> list[str]:
        return ["RH", "Operacao", "Logistica", "Vendas", "Marketing", "Outro"]

    @rx.var
    def selected_assigned_clients_summary(self) -> str:
        if not self.new_user_assigned_client_ids:
            return "Clique para escolher os clientes autorizados"
        names = [
            self.client_lookup.get(client_id, client_id)
            for client_id in self.new_user_assigned_client_ids
        ]
        return ", ".join(names)

    @rx.var(cache=False)
    def access_principal_options(self) -> list[str]:
        session = SessionLocal()
        user_emails = [
            row[0]
            for row in session.query(UserModel.email)
            .filter(UserModel.tenant_id == self.current_tenant)
            .order_by(UserModel.email.asc())
            .all()
        ]
        session.close()
        return sorted({email for email in user_emails if email})

    @rx.var(cache=False)
    def selected_access_principal(self) -> dict[str, str]:
        if not self.perm_user_email.strip():
            return {
                "name": "Selecione um usuario",
                "email": "Nenhuma conta foi escolhida ainda.",
                "role": "-",
                "scope": "-",
                "tenant": "-",
                "client": "-",
            }
        session = SessionLocal()
        user = (
            session.query(UserModel)
            .filter(
                UserModel.tenant_id == self.current_tenant,
                UserModel.email == self.perm_user_email.strip().lower(),
            )
            .first()
        )
        client_name = "-"
        if user and user.client_id:
            client = session.query(ClientModel).filter(ClientModel.id == user.client_id).first()
            client_name = client.name if client else "-"
        session.close()
        if not user:
            return {
                "name": "Usuario nao encontrado",
                "email": self.perm_user_email.strip().lower(),
                "role": "-",
                "scope": "-",
                "tenant": "-",
                "client": "-",
            }
        return {
            "name": user.name,
            "email": user.email,
            "role": user.role or "viewer",
            "scope": user.account_scope or "smartlab",
            "tenant": user.tenant_id,
            "client": client_name,
        }

    @rx.var(cache=False)
    def has_valid_permission_principal(self) -> bool:
        email = self.perm_user_email.strip().lower()
        if not email:
            return False
        return email in {item.lower() for item in self.access_principal_options}

    @rx.var(cache=False)
    def roles_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        rows = (
            session.query(RoleModel)
            .filter(RoleModel.tenant_id == self.current_tenant)
            .order_by(RoleModel.id.desc())
            .all()
        )
        data = [
            {
                "id": r.id,
                "name": r.name,
                "permissions": json.loads(r.permissions or "[]"),
                "permissions_str": ", ".join(json.loads(r.permissions or "[]")),
                "tenant_id": r.tenant_id,
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var
    def role_id_options(self) -> list[str]:
        return [str(r["id"]) for r in self.roles_data]

    @rx.var(cache=False)
    def responsibilities_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        rows = (
            session.query(ResponsibilityModel)
            .filter(ResponsibilityModel.tenant_id == self.current_tenant)
            .order_by(ResponsibilityModel.id.desc())
            .all()
        )
        data = [
            {
                "id": r.id,
                "role": r.role.name if r.role else "-",
                "role_id": r.role_id,
                "description": r.description,
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def forms_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        rows = (
            session.query(SurveyModel)
            .filter(SurveyModel.tenant_id == self.current_tenant)
            .order_by(SurveyModel.created_at.desc())
            .all()
        )
        question_rows = session.query(QuestionModel.survey_id, QuestionModel.dimension).filter(
            QuestionModel.tenant_id == self.current_tenant,
            QuestionModel.survey_id.is_not(None),
        ).all()
        dimension_lookup: dict[int, list[str]] = {}
        question_counts: dict[int, int] = {}
        for survey_id, dimension in question_rows:
            if survey_id is None:
                continue
            dimension_lookup.setdefault(int(survey_id), [])
            question_counts[int(survey_id)] = question_counts.get(int(survey_id), 0) + 1
            if dimension and dimension not in dimension_lookup[int(survey_id)]:
                dimension_lookup[int(survey_id)].append(dimension)
        data = [
            {
                "id": r.id,
                "name": r.name,
                "category": r.service_name,
                "dimensions": ", ".join(dimension_lookup.get(int(r.id), [])) or "-",
                "question_count": str(question_counts.get(int(r.id), 0)),
                "share_link": f'/form/{r.id}?token={r.share_token or ""}',
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var
    def form_id_options(self) -> list[str]:
        return [str(f["id"]) for f in self.forms_data]

    @rx.var(cache=False)
    def survey_builder_options(self) -> list[str]:
        return [f'{form["id"]} - {form["name"]}' for form in self.forms_data]

    @rx.var(cache=False)
    def interview_form_options(self) -> list[str]:
        return [f'{form["id"]} - {form["name"]} ({form["category"]})' for form in self.forms_data]

    @rx.var
    def selected_form_name(self) -> str:
        if not self.selected_form_id:
            return ""
        for form in self.forms_data:
            if str(form["id"]) == self.selected_form_id:
                return form["name"]
        return ""

    @rx.var
    def selected_survey_builder_option(self) -> str:
        if not self.selected_form_id:
            return ""
        for form in self.forms_data:
            if str(form["id"]) == self.selected_form_id:
                return f'{form["id"]} - {form["name"]}'
        return ""

    @rx.var
    def selected_interview_form_option(self) -> str:
        if not self.new_interview_form_id:
            return ""
        for form in self.forms_data:
            if str(form["id"]) == self.new_interview_form_id:
                return f'{form["id"]} - {form["name"]} ({form["category"]})'
        return ""

    @rx.var
    def interview_client_options(self) -> list[str]:
        return [f"{client_id} - {name}" for client_id, name in self.client_lookup.items()]

    @rx.var
    def selected_interview_client_option(self) -> str:
        if not self.new_interview_client_id:
            return ""
        name = self.client_lookup.get(self.new_interview_client_id, "")
        return f"{self.new_interview_client_id} - {name}" if name else ""

    @rx.var(cache=False)
    def interview_user_options(self) -> list[str]:
        if not self.new_interview_client_id.isdigit():
            return []
        session = SessionLocal()
        rows = (
            session.query(UserModel.id, UserModel.name, UserModel.email, UserModel.profession)
            .filter(
                UserModel.account_scope == "cliente",
                UserModel.client_id == int(self.new_interview_client_id),
            )
            .order_by(UserModel.name.asc())
            .all()
        )
        session.close()
        return [
            f'{row[0]} - {row[1] or row[2]} ({row[3] or "Sem cargo"})'
            for row in rows
        ]

    @rx.var(cache=False)
    def selected_interview_user_option(self) -> str:
        if not self.new_interview_user_id.isdigit():
            return ""
        session = SessionLocal()
        row = (
            session.query(UserModel.id, UserModel.name, UserModel.email, UserModel.profession)
            .filter(UserModel.id == int(self.new_interview_user_id))
            .first()
        )
        session.close()
        if not row:
            return ""
        return f'{row[0]} - {row[1] or row[2]} ({row[3] or "Sem cargo"})'

    @rx.var(cache=False)
    def interview_sessions_data(self) -> list[dict[str, str]]:
        if self.current_tenant != "default":
            return []
        session = SessionLocal()
        rows = (
            session.query(InterviewSessionModel)
            .filter(InterviewSessionModel.tenant_id == self.current_tenant)
            .order_by(InterviewSessionModel.created_at.desc())
            .all()
        )
        survey_lookup = {str(row.id): row.name for row in session.query(SurveyModel).filter(SurveyModel.tenant_id == self.current_tenant).all()}
        project_lookup = {str(row.id): row.name for row in session.query(ProjectModel).filter(ProjectModel.tenant_id == self.current_tenant).all()}
        client_lookup = {str(row.id): row.name for row in session.query(ClientModel).all()}
        user_lookup = {str(row.id): {"name": row.name or row.email, "email": row.email} for row in session.query(UserModel).all()}
        response_counts: dict[int, int] = {}
        for interview_id, count in (
            session.query(ResponseModel.interview_id, ResponseModel.id)
            .filter(
                ResponseModel.tenant_id == self.current_tenant,
                ResponseModel.interview_id.is_not(None),
            )
            .all()
        ):
            if interview_id is None:
                continue
            response_counts[int(interview_id)] = response_counts.get(int(interview_id), 0) + 1
        data = [
            {
                "id": str(row.id),
                "form_name": survey_lookup.get(str(row.survey_id), f"Pesquisa {row.survey_id or '-'}"),
                "project_name": project_lookup.get(str(row.project_id), "-") if row.project_id is not None else "-",
                "client_name": client_lookup.get(str(row.client_id), "-") if row.client_id is not None else "-",
                "interviewee_name": row.interviewee_name or "-",
                "interviewee_role": row.interviewee_role or "-",
                "interviewee_email": user_lookup.get(str(row.interviewee_user_id), {}).get("email", "-") if row.interviewee_user_id is not None else "-",
                "consultant_name": row.consultant_name or "-",
                "interview_date": row.interview_date or "-",
                "status": row.status or "em_andamento",
                "responses": str(response_counts.get(int(row.id), 0)),
                "total_score": str(row.total_score or 0),
            }
            for row in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def selected_interview_record(self) -> dict[str, str]:
        if not self.selected_interview_id:
            return {
                "id": "",
                "form_name": "Nenhuma entrevista selecionada",
                "project_name": "-",
                "client_name": "-",
                "interviewee_name": "-",
                "interviewee_role": "-",
                "interviewee_email": "-",
                "consultant_name": "-",
                "interview_date": "-",
                "status": "-",
                "responses": "0",
                "total_score": "0",
            }
        for item in self.interview_sessions_data:
            if item["id"] == self.selected_interview_id:
                return item
        return {
            "id": "",
            "form_name": "Entrevista nao encontrada",
            "project_name": "-",
            "client_name": "-",
            "interviewee_name": "-",
            "interviewee_role": "-",
            "interviewee_email": "-",
            "consultant_name": "-",
            "interview_date": "-",
            "status": "-",
            "responses": "0",
            "total_score": "0",
        }

    @rx.var(cache=False)
    def questions_data(self) -> list[dict[str, Any]]:
        if not self.selected_form_id:
            return []
        if not self.selected_form_id.isdigit():
            return []
        session = SessionLocal()
        rows = (
            session.query(QuestionModel)
            .filter(
                QuestionModel.tenant_id == self.current_tenant,
                QuestionModel.survey_id == int(self.selected_form_id),
            )
            .order_by(QuestionModel.order_index.asc(), QuestionModel.id.asc())
            .all()
        )
        data = [
            {
                "id": r.id,
                "text": r.text,
                "qtype": _loads_json(r.qtype, {"kind": r.qtype}).get("kind", "texto") if str(r.qtype).startswith("{") else r.qtype,
                "dimension": r.dimension or "-",
                "polarity": r.polarity or "positiva",
                "weight": str(r.weight or 1),
                "options": _question_payload(r.options_json)["options"],
                "options_str": ", ".join(_question_payload(r.options_json)["options"]),
                "logic_rule": str(_question_payload(r.options_json)["logic"].get("show_if", "")),
                "order": str(r.order_index or 0),
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def selected_survey_dimension_diagnostics(self) -> list[dict[str, str]]:
        if not self.selected_form_id or not self.selected_form_id.isdigit():
            return []
        session = SessionLocal()
        questions = (
            session.query(QuestionModel.id, QuestionModel.dimension)
            .filter(
                QuestionModel.tenant_id == self.current_tenant,
                QuestionModel.survey_id == int(self.selected_form_id),
            )
            .all()
        )
        dimension_scores: dict[str, int] = {}
        dimension_response_counts: dict[str, int] = {}
        question_dimension_lookup = {
            int(question_id): (dimension or "Sem dimensão")
            for question_id, dimension in questions
        }
        responses = (
            session.query(ResponseModel.question_id, ResponseModel.score)
            .filter(
                ResponseModel.tenant_id == self.current_tenant,
                ResponseModel.survey_id == int(self.selected_form_id),
            )
            .all()
        )
        for question_id, score in responses:
            if question_id is None:
                continue
            dimension = question_dimension_lookup.get(int(question_id), "Sem dimensão")
            dimension_scores[dimension] = dimension_scores.get(dimension, 0) + int(score or 0)
            dimension_response_counts[dimension] = dimension_response_counts.get(dimension, 0) + 1
        # Keep dimensions visible even before responses exist.
        for _, dimension in questions:
            label = dimension or "Sem dimensão"
            dimension_scores.setdefault(label, 0)
            dimension_response_counts.setdefault(label, 0)
        session.close()
        return [
            {
                "dimension": dimension,
                "score": str(score),
                "maturity": _dimension_maturity_label(score),
                "responses": str(dimension_response_counts.get(dimension, 0)),
            }
            for dimension, score in sorted(dimension_scores.items())
        ]

    @rx.var(cache=False)
    def active_interview_questions(self) -> list[dict[str, str]]:
        if not self.selected_interview_id.isdigit():
            return []
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(
                InterviewSessionModel.id == int(self.selected_interview_id),
                InterviewSessionModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        if not interview:
            session.close()
            return []
        response_rows = (
            session.query(ResponseModel)
            .filter(
                ResponseModel.tenant_id == self.current_tenant,
                ResponseModel.interview_id == interview.id,
            )
            .all()
        )
        response_lookup = {int(row.question_id): row for row in response_rows}
        questions = (
            session.query(QuestionModel)
            .filter(
                QuestionModel.tenant_id == self.current_tenant,
                QuestionModel.survey_id == int(interview.survey_id or 0),
            )
            .order_by(QuestionModel.id.asc())
            .all()
        )
        data = []
        for question in questions:
            payload = _question_payload(question.options_json)
            stored_response = response_lookup.get(int(question.id))
            has_local_score = str(question.id) in self.interview_score_map
            has_local_answer = str(question.id) in self.interview_answer_map
            answer = self.interview_answer_map.get(str(question.id))
            if answer is None:
                answer = stored_response.answer if stored_response else ""
            score = self.interview_score_map.get(str(question.id))
            if score is None:
                score = str(stored_response.score) if stored_response and stored_response.score is not None else "0"
            data.append(
                {
                    "id": str(question.id),
                    "text": question.text,
                    "dimension": question.dimension or "-",
                    "qtype": question.qtype or "fechada",
                    "polarity": question.polarity or "positiva",
                    "weight": str(question.weight or 1),
                    "options_str": ", ".join(payload["options"]) or "Escala livre 0 a 5",
                    "logic_rule": str(payload["logic"].get("show_if", "")) or "Sempre visivel",
                    "answer": answer,
                    "score": score,
                    "is_answered": "1" if stored_response is not None or has_local_score or has_local_answer else "0",
                }
            )
        session.close()
        return data

    @rx.var(cache=False)
    def active_interview_score_summary(self) -> dict[str, str]:
        total_score = 0
        answered_count = 0
        total_questions = len(self.active_interview_questions)
        dimension_totals: dict[str, int] = {}
        for question in self.active_interview_questions:
            raw_score = str(question.get("score") or "0")
            score = int(raw_score) if raw_score.lstrip("-").isdigit() else 0
            weight = int((question.get("weight") or "1"))
            weighted_score = score * weight
            total_score += weighted_score
            if question.get("is_answered") == "1":
                answered_count += 1
            dimension = question.get("dimension") or "Sem dimensão"
            dimension_totals[dimension] = dimension_totals.get(dimension, 0) + weighted_score
        return {
            "total_score": str(total_score),
            "answered_count": str(answered_count),
            "total_questions": str(total_questions),
            "completion": str(int((answered_count / total_questions) * 100) if total_questions else 0),
            "dimensions": ", ".join(f"{name}: {value}" for name, value in dimension_totals.items()) or "-",
        }

    @rx.var(cache=False)
    def active_interview_dimension_diagnostics(self) -> list[dict[str, str]]:
        ordered_dimensions = ["Presença", "Correção", "Reconhecimento", "Comunicação", "Disciplina/Exemplo"]
        diagnostics: dict[str, dict[str, str]] = {
            dimension: {
                "dimension": dimension,
                "score": "0",
                "maturity": _dimension_maturity_label(0),
                "responses": "0",
            }
            for dimension in ordered_dimensions
        }
        score_totals: dict[str, int] = {dimension: 0 for dimension in ordered_dimensions}
        response_counts: dict[str, int] = {dimension: 0 for dimension in ordered_dimensions}
        for question in self.active_interview_questions:
            dimension = question.get("dimension") or "Sem dimensão"
            raw_score = str(question.get("score") or "0")
            score = int(raw_score) if raw_score.lstrip("-").isdigit() else 0
            weight = int(question.get("weight") or "1")
            weighted_score = score * weight
            score_totals[dimension] = score_totals.get(dimension, 0) + weighted_score
            if question.get("is_answered") == "1":
                response_counts[dimension] = response_counts.get(dimension, 0) + 1
            if dimension not in diagnostics:
                diagnostics[dimension] = {
                    "dimension": dimension,
                    "score": "0",
                    "maturity": _dimension_maturity_label(0),
                    "responses": "0",
                }
        for dimension, payload in diagnostics.items():
            total = score_totals.get(dimension, 0)
            payload["score"] = str(total)
            payload["maturity"] = _dimension_maturity_label(total)
            payload["responses"] = str(response_counts.get(dimension, 0))
        ordered = [diagnostics[dimension] for dimension in ordered_dimensions if dimension in diagnostics]
        extras = [payload for dimension, payload in diagnostics.items() if dimension not in ordered_dimensions]
        return [*ordered, *extras]

    @rx.var(cache=False)
    def form_logic_preview(self) -> list[dict[str, str]]:
        data: list[dict[str, str]] = []
        for item in self.questions_data:
            data.append(
                {
                    "question": item["text"],
                    "dimension": item["dimension"],
                    "polarity": item["polarity"],
                    "weight": item["weight"],
                    "type": item["qtype"],
                    "logic": item["logic_rule"] or "Sempre visivel",
                    "options": item["options_str"] or "Resposta aberta",
                }
            )
        return data

    @rx.var(cache=False)
    def api_catalog(self) -> list[dict[str, str]]:
        return [
            {
                "name": item["name"],
                "method": item["method"],
                "path": item["path"],
                "purpose": item["purpose"],
                "kind": item["kind"],
            }
            for item in API_RESOURCE_CATALOG
        ]

    @rx.var(cache=False)
    def projects_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        if self.current_tenant != "default":
            session.close()
            return []
        rows = (
            session.query(ProjectModel)
            .filter(ProjectModel.tenant_id == self.current_tenant)
            .order_by(ProjectModel.created_at.desc())
            .all()
        )
        assignment_rows = session.query(ProjectAssignmentModel.project_id, ProjectAssignmentModel.client_id).all()
        assignment_lookup: dict[int, list[str]] = {}
        for project_id, client_id in assignment_rows:
            assignment_lookup.setdefault(int(project_id), [])
            if client_id is not None:
                assignment_lookup[int(project_id)].append(str(client_id))
        data = [
            {
                "id": r.id,
                "name": r.name,
                "project_type": r.project_type,
                "status": r.status,
                "progress": r.progress,
                "source_tenant": r.tenant_id,
                "assigned_clients": ", ".join(
                    self.client_lookup.get(client_id, client_id)
                    for client_id in assignment_lookup.get(r.id, [])
                ) or "-",
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var
    def project_id_options(self) -> list[str]:
        return [f'{p["id"]} - {p["name"]}' for p in self.projects_data]

    @rx.var(cache=False)
    def selected_project_option(self) -> str:
        if not self.selected_project_id:
            return ""
        for item in self.projects_data:
            if str(item["id"]) == self.selected_project_id:
                return f'{item["id"]} - {item["name"]}'
        return ""

    @rx.var
    def can_configure_projects(self) -> bool:
        return self.user_scope == "smartlab" and self.current_tenant == "default"

    @rx.var
    def selected_project_assigned_clients_summary(self) -> str:
        if not self.new_project_assigned_client_ids:
            return "Clique para escolher os clientes liberados"
        names = [
            self.client_lookup.get(client_id, client_id)
            for client_id in self.new_project_assigned_client_ids
        ]
        return ", ".join(names)

    @rx.var(cache=False)
    def selected_project_source_tenant(self) -> str:
        if not self.selected_project_id or not self.selected_project_id.isdigit():
            return self.current_tenant
        for item in self.projects_data:
            if str(item["id"]) == self.selected_project_id:
                return str(item.get("source_tenant", self.current_tenant))
        return self.current_tenant

    @rx.var
    def project_admin_tabs(self) -> list[str]:
        return ["cadastro", "workflow"]

    @rx.var(cache=False)
    def selected_project_record(self) -> dict[str, str]:
        if not self.selected_project_id:
            return {
                "name": "Nenhum projeto selecionado",
                "type": "-",
                "status": "-",
                "progress": "0",
                "clients": "-",
            }
        for item in self.projects_data:
            if str(item["id"]) == self.selected_project_id:
                return {
                    "name": item["name"],
                    "type": item["project_type"],
                    "status": item["status"],
                    "progress": str(item["progress"]),
                    "clients": item["assigned_clients"],
                }
        return {
            "name": "Projeto nao encontrado",
            "type": "-",
            "status": "-",
            "progress": "0",
            "clients": "-",
        }

    @rx.var
    def selected_project_link_clients_summary(self) -> str:
        if not self.new_project_assigned_client_ids:
            return "Clique para escolher os clientes vinculados"
        names = [
            self.client_lookup.get(client_id, client_id)
            for client_id in self.new_project_assigned_client_ids
        ]
        return ", ".join(names)

    @rx.var(cache=False)
    def workflow_boxes_data(self) -> list[dict[str, Any]]:
        if not self.selected_project_id:
            return []
        session = SessionLocal()
        rows = (
            session.query(WorkflowBoxModel)
            .filter(
                WorkflowBoxModel.tenant_id == self.selected_project_source_tenant,
                WorkflowBoxModel.project_id == int(self.selected_project_id),
            )
            .order_by(WorkflowBoxModel.position.asc(), WorkflowBoxModel.id.asc())
            .all()
        )
        data = [
            {
                "id": r.id,
                "title": r.title,
                "box_type": r.box_type,
                "position": r.position,
                "config": _loads_json(r.config_json, {}),
                "zone": _loads_json(r.config_json, {}).get("zone", "center"),
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def workflow_boxes_left(self) -> list[dict[str, Any]]:
        return [b for b in self.workflow_boxes_data if b["zone"] == "left"]

    @rx.var(cache=False)
    def workflow_boxes_center(self) -> list[dict[str, Any]]:
        return [b for b in self.workflow_boxes_data if b["zone"] == "center"]

    @rx.var(cache=False)
    def workflow_boxes_right(self) -> list[dict[str, Any]]:
        return [b for b in self.workflow_boxes_data if b["zone"] == "right"]

    @rx.var(cache=False)
    def workflow_canvas_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for index, box in enumerate(self.workflow_boxes_data):
            has_next = index < len(self.workflow_boxes_data) - 1
            next_box = self.workflow_boxes_data[index + 1] if has_next else {}
            line_type = "ai" if box["box_type"] == "analise" or next_box.get("box_type") == "analise" else "main"
            items.append(
                {
                    "id": box["id"],
                    "title": box["title"],
                    "box_type": box["box_type"],
                    "position": box["position"],
                    "zone": box["zone"],
                    "endpoint": str(box["config"].get("endpoint", "")),
                    "condition": str(box["config"].get("condition", "")),
                    "output_key": str(box["config"].get("output_key", "")),
                    "has_next": has_next,
                    "line_type": line_type,
                }
            )
        return items

    @rx.var(cache=False)
    def workflow_blueprint(self) -> list[dict[str, str]]:
        blueprint: list[dict[str, str]] = []
        for item in self.workflow_canvas_items:
            blueprint.append(
                {
                    "title": item["title"],
                    "type": item["box_type"],
                    "endpoint": item["endpoint"] or "interno",
                    "condition": item["condition"] or "sempre",
                    "output": item["output_key"] or "-",
                }
            )
        return blueprint

    @rx.var(cache=False)
    def workflow_sticky_notes(self) -> list[dict[str, Any]]:
        return [
            {"id": b["id"], "note": str(b["config"].get("note", ""))}
            for b in self.workflow_boxes_data
            if b["box_type"] == "nota"
        ]

    @rx.var(cache=False)
    def action_plans_data(self) -> list[dict[str, Any]]:
        if not self.selected_project_id:
            return []
        session = SessionLocal()
        rows = (
            session.query(ActionPlanModel)
            .filter(
                ActionPlanModel.tenant_id == self.selected_project_source_tenant,
                ActionPlanModel.project_id == int(self.selected_project_id),
            )
            .order_by(ActionPlanModel.id.desc())
            .all()
        )
        data = [
            {
                "id": r.id,
                "title": r.title,
                "owner": r.owner,
                "due_date": r.due_date,
                "status": r.status,
                "expected_result": r.expected_result,
                "actual_result": r.actual_result,
                "attainment": r.attainment,
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def actions_todo(self) -> list[dict[str, Any]]:
        return [a for a in self.action_plans_data if a["status"] == "a_fazer"]

    @rx.var(cache=False)
    def actions_doing(self) -> list[dict[str, Any]]:
        return [a for a in self.action_plans_data if a["status"] == "em_andamento"]

    @rx.var(cache=False)
    def actions_done(self) -> list[dict[str, Any]]:
        return [a for a in self.action_plans_data if a["status"] == "concluido"]

    @rx.var(cache=False)
    def permission_boxes_data(self) -> list[dict[str, Any]]:
        if not self.perm_user_email.strip():
            return []
        session = SessionLocal()
        query = session.query(PermissionBoxModel).filter(PermissionBoxModel.tenant_id == self.current_tenant)
        query = query.filter(PermissionBoxModel.user_email == self.perm_user_email.strip().lower())
        rows = query.order_by(PermissionBoxModel.id.desc()).all()
        data = [
            {
                "id": r.id,
                "user_email": r.user_email,
                "resource": r.resource,
                "decision": r.decision,
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var
    def permission_module_options(self) -> list[str]:
        modules = ["Todos"]
        modules.extend(sorted({item["module"] for item in PERMISSION_RESOURCE_CATALOG}))
        return modules

    @rx.var(cache=False)
    def permission_catalog(self) -> list[dict[str, str]]:
        if not self.has_valid_permission_principal:
            return []
        items = PERMISSION_RESOURCE_CATALOG
        if self.perm_selected_module != "Todos":
            items = [item for item in items if item["module"] == self.perm_selected_module]
        return [
            {
                "module": item["module"],
                "resource": item["resource"],
                "resource_token": _dom_token(item["resource"]),
                "label": item["label"],
                "description": item["description"],
                "action": item["action"],
            }
            for item in items
        ]

    @rx.var
    def role_template_options(self) -> list[str]:
        return list(ROLE_TEMPLATE_CATALOG.keys())

    @rx.var(cache=False)
    def role_templates_data(self) -> list[dict[str, Any]]:
        if not self.has_valid_permission_principal:
            return []
        key = self.selected_role_template_key
        value = ROLE_TEMPLATE_CATALOG.get(key, ROLE_TEMPLATE_CATALOG["viewer"])
        return [
            {
                "key": key,
                "label": value["label"],
                "scope": value["scope"],
                "description": value["description"],
                "permissions": value["permissions"],
                "permissions_str": ", ".join(value["permissions"]) if value["permissions"] else "Somente leitura",
            }
        ]

    @rx.var(cache=False)
    def selected_role_template_key(self) -> str:
        if not self.has_valid_permission_principal:
            return "viewer"
        if self.perm_selected_role_template in ROLE_TEMPLATE_CATALOG:
            return self.perm_selected_role_template
        principal_role = self.selected_access_principal["role"]
        if principal_role in ROLE_TEMPLATE_CATALOG:
            return principal_role
        return "viewer"

    @rx.var(cache=False)
    def selected_role_template_data(self) -> dict[str, Any]:
        if not self.has_valid_permission_principal:
            return {
                "label": "Nenhum usuario selecionado",
                "scope": "-",
                "description": "Selecione uma conta valida deste tenant para visualizar o template RBAC.",
                "permissions_str": "-",
            }
        template = ROLE_TEMPLATE_CATALOG.get(self.selected_role_template_key, ROLE_TEMPLATE_CATALOG["viewer"])
        return {
            "label": template["label"],
            "scope": template["scope"],
            "description": template["description"],
            "permissions_str": ", ".join(template["permissions"]) if template["permissions"] else "Somente leitura",
        }

    @rx.var(cache=False)
    def permission_decision_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        email = (self.perm_user_email or "").strip().lower()
        if not email or not self.has_valid_permission_principal:
            return mapping
        for item in self.permission_boxes_data:
            if item["user_email"] == email:
                mapping[item["resource"]] = item["decision"]
        return mapping

    @rx.var(cache=False)
    def permission_canvas_available(self) -> list[dict[str, str]]:
        data: list[dict[str, str]] = []
        decisions = self.permission_decision_map
        for item in self.permission_catalog:
            if decisions.get(item["resource"], "") == "":
                data.append(item)
        return data

    @rx.var(cache=False)
    def permission_canvas_allowed(self) -> list[dict[str, str]]:
        data: list[dict[str, str]] = []
        decisions = self.permission_decision_map
        for item in self.permission_catalog:
            if decisions.get(item["resource"], "") == "permitido":
                data.append(item)
        return data

    @rx.var(cache=False)
    def permission_canvas_denied(self) -> list[dict[str, str]]:
        data: list[dict[str, str]] = []
        decisions = self.permission_decision_map
        for item in self.permission_catalog:
            if decisions.get(item["resource"], "") == "negado":
                data.append(item)
        return data

    @rx.var(cache=False)
    def permission_summary(self) -> dict[str, str]:
        decisions = self.permission_decision_map
        allowed = len([value for value in decisions.values() if value == "permitido"])
        denied = len([value for value in decisions.values() if value == "negado"])
        total = len(self.permission_catalog)
        return {
            "catalogo": str(total),
            "permitidos": str(allowed),
            "negados": str(denied),
            "pendentes": str(max(total - allowed - denied, 0)),
        }

    @rx.var(cache=False)
    def dashboard_boxes_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        scope = "consultor" if self.user_role in {"admin", "editor"} else "cliente"
        rows = (
            session.query(DashboardBoxModel)
            .filter(
                DashboardBoxModel.tenant_id == self.current_tenant,
                DashboardBoxModel.role_scope == scope,
            )
            .order_by(DashboardBoxModel.position.asc(), DashboardBoxModel.id.asc())
            .all()
        )
        data = []
        for r in rows:
            config = _loads_json(r.config_json, {})
            data.append(
                {
                    "id": r.id,
                    "title": r.title,
                    "kind": r.kind,
                    "position": r.position,
                    "source": str(config.get("source", "manual")),
                    "description": str(config.get("description", "")),
                    "embed": "sim" if bool(config.get("embed_enabled")) else "nao",
                }
            )
        session.close()
        return data

    @rx.var(cache=False)
    def dashboard_builder_preview(self) -> list[dict[str, str]]:
        return [
            {
                "title": box["title"],
                "kind": box["kind"],
                "source": box["source"],
                "description": box["description"] or "Sem descricao funcional",
            }
            for box in self.dashboard_boxes_data
        ]

    @rx.var(cache=False)
    def dashboard_metrics(self) -> dict[str, str]:
        session = SessionLocal()
        total_clients = session.query(ClientModel).filter(ClientModel.tenant_id == self.current_tenant).count()
        total_forms = session.query(FormModel).filter(FormModel.tenant_id == self.current_tenant).count()
        total_responses = session.query(ResponseModel).filter(ResponseModel.tenant_id == self.current_tenant).count()
        scores = session.query(ResponseModel.score).filter(ResponseModel.tenant_id == self.current_tenant).all()
        valid_scores = [int(score) for score, in scores if score is not None]
        avg_score = round(sum(valid_scores) / max(1, len(valid_scores)), 2)
        session.close()
        return {
            "clientes": str(total_clients),
            "formularios": str(total_forms),
            "respostas": str(total_responses),
            "media": str(avg_score),
        }

    @rx.var(cache=False)
    def dashboard_table(self) -> list[dict[str, str]]:
        session = SessionLocal()
        forms = session.query(FormModel).filter(FormModel.tenant_id == self.current_tenant).all()
        rows: list[dict[str, str]] = []
        for form in forms:
            responses = session.query(ResponseModel).filter(
                ResponseModel.tenant_id == self.current_tenant, ResponseModel.form_id == form.id
            )
            count = responses.count()
            valid_scores = [int(r.score) for r in responses.all() if r.score is not None]
            avg = round(sum(valid_scores) / max(1, len(valid_scores)), 2)
            status = "Forte" if avg >= 4 else "Em evolução" if avg >= 2.5 else "Crítico"
            rows.append(
                {
                    "form": form.name,
                    "categoria": form.category,
                    "respostas": str(count),
                    "media": str(avg),
                    "status": status,
                }
            )
        session.close()
        return rows

    @rx.var
    def testimonials(self) -> list[dict[str, str]]:
        return [
            {
                "name": "Diretora EHS - Mineração",
                "text": "O SSecur1 trouxe clareza real da cultura e acelerou decisões estratégicas de segurança.",
            },
            {
                "name": "Gerente Industrial",
                "text": "Conseguimos integrar segurança e produtividade sem perder performance operacional.",
            },
            {
                "name": "RH Corporativo",
                "text": "A trilha da liderança ficou orientada por dados reais e comportamentos críticos.",
            },
        ]

    @rx.var
    def current_testimonial(self) -> dict[str, str]:
        data = self.testimonials
        if not data:
            return {"name": "", "text": ""}
        return data[self.testimonial_index % len(data)]

    def next_testimonial(self):
        self.testimonial_index = (self.testimonial_index + 1) % max(1, len(self.testimonials))

    def open_search_result(self, view: str, record_id: str = ""):
        self.active_view = view
        self.mobile_menu_open = False
        if view == "formularios":
            self.selected_form_id = record_id
        self.global_search_query = ""

    def switch_tenant(self, value: str):
        if value not in self.tenant_options:
            self.toast_message = "Tenant fora do escopo do usuario"
            self.toast_type = "error"
            return
        self.current_tenant = value
        self.perm_user_email = ""
        self.hydrate_tenant_context()
        if not self.show_menu_projects and self.active_view == "projetos":
            self.active_view = "dashboard"

    def switch_tenant_from_display(self, value: str):
        session = SessionLocal()
        query = session.query(TenantModel)
        if self.user_scope == "cliente" and self.home_tenant_id:
            query = query.filter(TenantModel.id == self.home_tenant_id)
        rows = query.order_by(TenantModel.name.asc()).all()
        session.close()
        for row in rows:
            label = "SmartLab - interno" if row.id == "default" else f"{row.name} - cliente"
            if label == value:
                self.switch_tenant(row.id)
                return

    def hydrate_tenant_context(self):
        projects = self.projects_data
        self.selected_project_id = str(projects[0]["id"]) if projects else ""
        self.sync_project_assignments()

    def set_global_search_query(self, value: str):
        self.global_search_query = value

    def clear_global_search(self):
        self.global_search_query = ""

    def set_new_client_name(self, value: str):
        self.new_client_name = value

    def set_new_client_trade_name(self, value: str):
        self.new_client_trade_name = value

    def set_new_client_email(self, value: str):
        self.new_client_email = value

    def set_new_client_phone(self, value: str):
        self.new_client_phone = value

    def set_new_client_address(self, value: str):
        self.new_client_address = value

    def set_new_client_state_code(self, value: str):
        self.new_client_state_code = value

    def set_new_client_cnpj(self, value: str):
        self.new_client_cnpj = value

    def set_new_client_business_sector(self, value: str):
        self.new_client_business_sector = value
        if value != "Outro":
            self.new_client_custom_business_sector = ""

    def set_new_client_custom_business_sector(self, value: str):
        self.new_client_custom_business_sector = value

    def set_new_client_employee_count(self, value: str):
        self.new_client_employee_count = value

    def set_new_client_branch_count(self, value: str):
        self.new_client_branch_count = value

    def set_new_client_annual_revenue(self, value: str):
        self.new_client_annual_revenue = value

    def set_new_client_parent_option(self, value: str):
        self.new_client_parent_id = value.split(" - ", 1)[0].strip() if value else ""

    def set_new_user_name(self, value: str):
        self.new_user_name = value

    def set_new_user_email(self, value: str):
        self.new_user_email = value

    def set_new_user_password(self, value: str):
        self.new_user_password = value

    def set_new_user_role(self, value: str):
        self.new_user_role = value

    def set_new_user_scope(self, value: str):
        self.new_user_scope = value
        if value == "smartlab":
            self.new_user_client_id = ""
            self.new_user_tenant_id = "default"
        else:
            self.new_user_assigned_client_ids = []
            self.new_user_assigned_clients_open = False

    def set_new_user_profession(self, value: str):
        self.new_user_profession = value
        if value != "Outro":
            self.new_user_custom_profession = ""

    def set_new_user_custom_profession(self, value: str):
        self.new_user_custom_profession = value

    def set_new_user_department(self, value: str):
        self.new_user_department = value
        if value != "Outro":
            self.new_user_custom_department = ""

    def set_new_user_client_option(self, value: str):
        self.new_user_client_id = value.split(" - ", 1)[0].strip()

    def set_new_user_reports_to_user_option(self, value: str):
        self.new_user_reports_to_user_id = value.split(" - ", 1)[0].strip()

    def set_new_user_workspace_option(self, value: str):
        self.new_user_tenant_id = value.split(" - ", 1)[0].strip()

    def toggle_new_user_assigned_client(self, client_id: str):
        current = list(self.new_user_assigned_client_ids)
        if client_id in current:
            current.remove(client_id)
        else:
            current.append(client_id)
        self.new_user_assigned_client_ids = current

    def set_new_user_custom_department(self, value: str):
        self.new_user_custom_department = value

    def toggle_new_user_assigned_clients_open(self):
        self.new_user_assigned_clients_open = not self.new_user_assigned_clients_open

    def reset_client_form(self):
        self.editing_client_id = ""
        self.new_client_name = ""
        self.new_client_trade_name = ""
        self.new_client_email = ""
        self.new_client_phone = ""
        self.new_client_address = ""
        self.new_client_state_code = "SP"
        self.new_client_cnpj = ""
        self.new_client_business_sector = "Industria"
        self.new_client_custom_business_sector = ""
        self.new_client_employee_count = ""
        self.new_client_branch_count = ""
        self.new_client_annual_revenue = ""
        self.new_client_parent_id = ""

    def reset_user_form(self):
        self.editing_user_id = ""
        self.new_user_name = ""
        self.new_user_email = ""
        self.new_user_password = ""
        self.new_user_role = "viewer"
        self.new_user_scope = "smartlab"
        self.new_user_client_id = ""
        self.new_user_tenant_id = "default"
        self.new_user_profession = "Analista"
        self.new_user_custom_profession = ""
        self.new_user_department = "Operacao"
        self.new_user_custom_department = ""
        self.new_user_reports_to_user_id = ""
        self.new_user_assigned_client_ids = []
        self.new_user_assigned_clients_open = False

    def reset_tenant_form(self):
        self.editing_tenant_id = ""
        self.new_tenant_name = ""
        self.new_tenant_slug = ""
        self.new_tenant_limit = "50"
        self.new_tenant_client_id = ""

    def reset_role_form(self):
        self.editing_role_id = ""
        self.new_role_name = ""
        self.new_role_permissions = "create:clientes,edit:clientes"

    def reset_resp_form(self):
        self.editing_resp_id = ""
        self.new_resp_role_id = ""
        self.new_resp_desc = ""

    def reset_form_builder(self):
        self.editing_form_id = ""
        self.new_form_name = ""
        self.new_form_category = "Diagnóstico Cultura de Segurança"
        self.new_form_target_client_id = ""
        self.new_form_target_user_email = ""
        self.new_question_dimension = "Presença"
        self.new_question_custom_dimension = ""
        self.new_question_weight = "1"
        self.new_question_polarity = "positiva"
        self.new_question_type = "escala_0_5"
        self.editing_question_id = ""

    def reset_interview_form(self):
        self.editing_interview_id = ""
        self.new_interview_form_id = ""
        self.new_interview_client_id = ""
        self.new_interview_user_id = ""
        self.new_interview_date = ""
        self.new_interview_notes = ""

    def start_edit_client(self, client_id: int):
        session = SessionLocal()
        row = (
            session.query(ClientModel)
            .filter(ClientModel.id == client_id, ClientModel.tenant_id == self.current_tenant)
            .first()
        )
        session.close()
        if not row:
            self.toast_message = "Cliente nao encontrado"
            self.toast_type = "error"
            return
        self.editing_client_id = str(row.id)
        self.new_client_name = row.name or ""
        self.new_client_trade_name = row.trade_name or ""
        self.new_client_email = row.email or ""
        self.new_client_phone = row.phone or ""
        self.new_client_address = row.address or ""
        self.new_client_state_code = row.state_code or "SP"
        self.new_client_cnpj = row.cnpj or ""
        sector = row.business_sector or "Industria"
        if sector in self.business_sector_options:
            self.new_client_business_sector = sector
            self.new_client_custom_business_sector = ""
        else:
            self.new_client_business_sector = "Outro"
            self.new_client_custom_business_sector = sector
        self.new_client_employee_count = str(row.employee_count or "")
        self.new_client_branch_count = str(row.branch_count or "")
        self.new_client_annual_revenue = _format_brl_amount(row.annual_revenue) if row.annual_revenue is not None else ""
        self.new_client_parent_id = str(row.parent_client_id or "")

    def start_edit_user(self, user_id: int):
        session = SessionLocal()
        row = session.query(UserModel).filter(UserModel.id == user_id).first()
        session.close()
        if not row:
            self.toast_message = "Usuario nao encontrado"
            self.toast_type = "error"
            return
        self.editing_user_id = str(row.id)
        self.new_user_name = row.name or ""
        self.new_user_email = row.email or ""
        self.new_user_password = ""
        self.new_user_role = row.role or "viewer"
        self.new_user_scope = row.account_scope or "smartlab"
        self.new_user_client_id = str(row.client_id or "")
        self.new_user_tenant_id = row.tenant_id or "default"
        profession = row.profession or "Analista"
        if profession in self.profession_options:
            self.new_user_profession = profession
            self.new_user_custom_profession = ""
        else:
            self.new_user_profession = "Outro"
            self.new_user_custom_profession = profession
        department = row.department or "Operacao"
        if department in self.department_options:
            self.new_user_department = department
            self.new_user_custom_department = ""
        else:
            self.new_user_department = "Outro"
            self.new_user_custom_department = department
        self.new_user_reports_to_user_id = str(row.reports_to_user_id or "")
        self.new_user_assigned_client_ids = [str(item) for item in _loads_json(row.assigned_client_ids, [])]
        self.new_user_assigned_clients_open = False

    def start_edit_tenant(self, tenant_id: str):
        session = SessionLocal()
        row = session.query(TenantModel).filter(TenantModel.id == tenant_id).first()
        session.close()
        if not row:
            self.toast_message = "Tenant nao encontrado"
            self.toast_type = "error"
            return
        self.editing_tenant_id = row.id
        self.new_tenant_name = row.name or ""
        self.new_tenant_slug = row.slug or ""
        self.new_tenant_limit = str(row.limit_users or 50)
        self.new_tenant_client_id = str(row.owner_client_id or "")

    def start_edit_role(self, role_id: int):
        session = SessionLocal()
        row = session.query(RoleModel).filter(RoleModel.id == role_id, RoleModel.tenant_id == self.current_tenant).first()
        session.close()
        if not row:
            self.toast_message = "Papel nao encontrado"
            self.toast_type = "error"
            return
        self.editing_role_id = str(row.id)
        self.new_role_name = row.name or ""
        self.new_role_permissions = ", ".join(_loads_json(row.permissions, []))

    def start_edit_responsibility(self, resp_id: int):
        session = SessionLocal()
        row = (
            session.query(ResponsibilityModel)
            .filter(ResponsibilityModel.id == resp_id, ResponsibilityModel.tenant_id == self.current_tenant)
            .first()
        )
        session.close()
        if not row:
            self.toast_message = "Responsabilidade nao encontrada"
            self.toast_type = "error"
            return
        self.editing_resp_id = str(row.id)
        self.new_resp_role_id = str(row.role_id)
        self.new_resp_desc = row.description or ""

    def start_edit_form(self, form_id: int):
        session = SessionLocal()
        row = session.query(SurveyModel).filter(SurveyModel.id == form_id, SurveyModel.tenant_id == self.current_tenant).first()
        session.close()
        if not row:
            self.toast_message = "Pesquisa nao encontrada"
            self.toast_type = "error"
            return
        self.editing_form_id = str(row.id)
        self.selected_form_id = str(row.id)
        self.new_form_name = row.name or ""
        self.new_form_category = row.service_name or "Diagnóstico Cultura de Segurança"
        self.new_form_target_client_id = ""
        self.new_form_target_user_email = ""

    def start_edit_question(self, question_id: int):
        session = SessionLocal()
        row = (
            session.query(QuestionModel)
            .filter(QuestionModel.id == question_id, QuestionModel.tenant_id == self.current_tenant)
            .first()
        )
        session.close()
        if not row:
            self.toast_message = "Pergunta nao encontrada"
            self.toast_type = "error"
            return
        payload = _question_payload(row.options_json)
        question_type = _loads_json(row.qtype, {"kind": row.qtype}).get("kind", "texto") if str(row.qtype).startswith("{") else (row.qtype or "texto")
        self.editing_question_id = str(row.id)
        if row.survey_id is not None:
            self.selected_form_id = str(row.survey_id)
        self.new_question_text = row.text or ""
        if row.dimension and row.dimension in self.question_dimension_options:
            self.new_question_dimension = row.dimension
            self.new_question_custom_dimension = ""
        else:
            self.new_question_dimension = "Outro"
            self.new_question_custom_dimension = row.dimension or ""
        self.new_question_type = question_type
        self.new_question_polarity = row.polarity or "positiva"
        self.new_question_weight = str(row.weight or 1)
        self.new_question_options = ", ".join(payload["options"])
        self.new_question_condition = str(payload["logic"].get("show_if", ""))

    def delete_question(self, question_id: int):
        if not self.can_manage_forms:
            self.toast_message = "Sem permissão para excluir perguntas"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = (
            session.query(QuestionModel)
            .filter(QuestionModel.id == question_id, QuestionModel.tenant_id == self.current_tenant)
            .first()
        )
        if row:
            session.query(ResponseModel).filter(ResponseModel.question_id == question_id).delete()
            session.delete(row)
            session.commit()
            if self.editing_question_id == str(question_id):
                self.editing_question_id = ""
            self.toast_message = "Pergunta removida"
            self.toast_type = "success"
        session.close()

    def set_new_tenant_name(self, value: str):
        self.new_tenant_name = value

    def set_new_tenant_slug(self, value: str):
        self.new_tenant_slug = value

    def set_new_tenant_limit(self, value: str):
        self.new_tenant_limit = value

    def set_new_role_name(self, value: str):
        self.new_role_name = value

    def set_new_role_permissions(self, value: str):
        self.new_role_permissions = value

    def set_new_resp_role_id(self, value: str):
        self.new_resp_role_id = value

    def set_new_resp_desc(self, value: str):
        self.new_resp_desc = value

    def set_new_form_name(self, value: str):
        self.new_form_name = value

    def set_new_form_category(self, value: str):
        self.new_form_category = value

    def set_new_form_target_client_option(self, value: str):
        self.new_form_target_client_id = value.split(" - ", 1)[0].strip() if value else ""

    def set_new_form_target_user_option(self, value: str):
        self.new_form_target_user_email = value.split(" - ", 1)[0].strip() if value else ""

    def set_new_interview_form_option(self, value: str):
        self.new_interview_form_id = value.split(" - ", 1)[0].strip() if value else ""

    def set_new_interview_client_option(self, value: str):
        self.new_interview_client_id = value.split(" - ", 1)[0].strip() if value else ""
        self.new_interview_user_id = ""

    def set_new_interview_date(self, value: str):
        self.new_interview_date = value

    def set_new_interview_user_option(self, value: str):
        self.new_interview_user_id = value.split(" - ", 1)[0].strip() if value else ""

    def set_new_interview_notes(self, value: str):
        self.new_interview_notes = value

    def set_new_question_text(self, value: str):
        self.new_question_text = value

    def set_new_question_type(self, value: str):
        self.new_question_type = value

    def set_new_question_dimension(self, value: str):
        self.new_question_dimension = value
        if value != "Outro":
            self.new_question_custom_dimension = ""

    def set_new_question_custom_dimension(self, value: str):
        self.new_question_custom_dimension = value

    def set_new_question_weight(self, value: str):
        self.new_question_weight = value

    def set_new_question_polarity(self, value: str):
        self.new_question_polarity = value

    def set_new_question_options(self, value: str):
        self.new_question_options = value

    def set_new_question_condition(self, value: str):
        self.new_question_condition = value

    def set_interview_answer(self, question_id: str, value: str):
        updated = dict(self.interview_answer_map)
        updated[str(question_id)] = value
        self.interview_answer_map = updated

    def set_interview_score(self, question_id: str, value: str):
        updated = dict(self.interview_score_map)
        updated[str(question_id)] = str(value).strip() if str(value).strip() else "0"
        self.interview_score_map = updated

    def set_ai_prompt(self, value: str):
        self.ai_prompt = value

    def set_new_project_name(self, value: str):
        self.new_project_name = value

    def set_new_project_type(self, value: str):
        self.new_project_type = value

    def select_project(self, value: str):
        self.selected_project_id = value.split(" - ", 1)[0].strip()
        self.sync_project_assignments()

    def set_project_admin_tab(self, value: str):
        self.project_admin_tab = value

    def toggle_new_project_assigned_client(self, client_id: str):
        current = list(self.new_project_assigned_client_ids)
        if client_id in current:
            current.remove(client_id)
        else:
            current.append(client_id)
        self.new_project_assigned_client_ids = current

    def toggle_new_project_assigned_clients_open(self):
        self.new_project_assigned_clients_open = not self.new_project_assigned_clients_open

    def sync_project_assignments(self):
        if not self.selected_project_id.isdigit() or self.current_tenant != "default":
            self.new_project_assigned_client_ids = []
            self.new_project_assigned_clients_open = False
            return
        session = SessionLocal()
        rows = (
            session.query(ProjectAssignmentModel.client_id)
            .filter(ProjectAssignmentModel.project_id == int(self.selected_project_id))
            .all()
        )
        session.close()
        self.new_project_assigned_client_ids = [str(row[0]) for row in rows if row[0] is not None]
        self.new_project_assigned_clients_open = False

    def set_new_box_title(self, value: str):
        self.new_box_title = value

    def set_new_box_type(self, value: str):
        self.new_box_type = value

    def set_new_box_method(self, value: str):
        self.new_box_method = value

    def set_new_box_endpoint(self, value: str):
        self.new_box_endpoint = value

    def set_new_box_headers(self, value: str):
        self.new_box_headers = value

    def set_new_box_retry_policy(self, value: str):
        self.new_box_retry_policy = value

    def set_new_box_client_id(self, value: str):
        self.new_box_client_id = value

    def set_new_box_client_secret(self, value: str):
        self.new_box_client_secret = value

    def set_new_box_schedule(self, value: str):
        self.new_box_schedule = value

    def set_new_box_zone(self, value: str):
        self.new_box_zone = value

    def set_new_box_condition(self, value: str):
        self.new_box_condition = value

    def set_new_box_output_key(self, value: str):
        self.new_box_output_key = value

    def set_new_sticky_note_text(self, value: str):
        self.new_sticky_note_text = value

    def set_new_action_title(self, value: str):
        self.new_action_title = value

    def set_new_action_owner(self, value: str):
        self.new_action_owner = value

    def set_new_action_due_date(self, value: str):
        self.new_action_due_date = value

    def set_new_action_expected_result(self, value: str):
        self.new_action_expected_result = value

    def set_new_user_client_id(self, value: str):
        self.new_user_client_id = value

    def set_new_user_tenant_id(self, value: str):
        self.new_user_tenant_id = value

    def set_new_tenant_client_id(self, value: str):
        self.new_tenant_client_id = value

    def set_new_tenant_client_option(self, value: str):
        client_id = value.split(" - ", 1)[0].strip()
        self.new_tenant_client_id = client_id

    def set_perm_user_email(self, value: str):
        self.perm_user_email = value
        session = SessionLocal()
        user = (
            session.query(UserModel)
            .filter(
                UserModel.tenant_id == self.current_tenant,
                UserModel.email == value.strip().lower(),
            )
            .first()
        )
        session.close()
        if user and (user.role or "") in ROLE_TEMPLATE_CATALOG:
            self.perm_selected_role_template = user.role or "viewer"
        else:
            self.perm_selected_role_template = "viewer"
        self.perm_selected_module = "Todos"

    def set_perm_selected_module(self, value: str):
        self.perm_selected_module = value

    def set_perm_selected_role_template(self, value: str):
        self.perm_selected_role_template = value

    def set_new_dashboard_box_title(self, value: str):
        self.new_dashboard_box_title = value

    def set_new_dashboard_box_kind(self, value: str):
        self.new_dashboard_box_kind = value

    def set_new_dashboard_box_scope(self, value: str):
        self.new_dashboard_box_scope = value

    def set_new_dashboard_box_source(self, value: str):
        self.new_dashboard_box_source = value

    def set_new_dashboard_box_description(self, value: str):
        self.new_dashboard_box_description = value

    def create_client(self):
        if not self.can_manage_clients:
            self.toast_message = "Permissão insuficiente"
            self.toast_type = "error"
            return
        if not self.new_client_name or not self.new_client_email:
            self.toast_message = "Nome e e-mail são obrigatórios"
            self.toast_type = "error"
            return
        business_sector = (
            self.new_client_custom_business_sector.strip()
            if self.new_client_business_sector == "Outro"
            else self.new_client_business_sector.strip()
        )
        if not business_sector:
            self.toast_message = "Informe o ramo de atividade"
            self.toast_type = "error"
            return
        session = SessionLocal()
        client_name = self.new_client_name.strip()
        trade_name = self.new_client_trade_name.strip() or None
        parent_client_id = int(self.new_client_parent_id) if self.new_client_parent_id.isdigit() else None
        if self.editing_client_id.isdigit():
            editing_id = int(self.editing_client_id)
            if parent_client_id == editing_id:
                session.close()
                self.toast_message = "Um cliente nao pode ser o proprio grupo principal"
                self.toast_type = "error"
                return
            client = (
                session.query(ClientModel)
                .filter(ClientModel.id == int(self.editing_client_id), ClientModel.tenant_id == self.current_tenant)
                .first()
            )
            if not client:
                session.close()
                self.toast_message = "Cliente nao encontrado para edicao"
                self.toast_type = "error"
                return
            descendants = _collect_descendant_client_ids(
                _build_client_children_map(session.query(ClientModel).all()),
                editing_id,
            )
            if parent_client_id in descendants:
                session.close()
                self.toast_message = "Nao e possivel vincular o cliente a uma empresa-filha dele"
                self.toast_type = "error"
                return
            client.name = client_name
            client.trade_name = trade_name
            client.email = self.new_client_email.strip().lower()
            client.phone = self.new_client_phone.strip() or None
            client.address = self.new_client_address.strip() or None
            client.state_code = self.new_client_state_code.strip() or None
            client.cnpj = self.new_client_cnpj.strip() or None
            client.business_sector = business_sector
            client.employee_count = _parse_int(self.new_client_employee_count)
            client.branch_count = _parse_int(self.new_client_branch_count)
            client.annual_revenue = _parse_brl_amount(self.new_client_annual_revenue)
            client.parent_client_id = parent_client_id
            linked_tenant = session.query(TenantModel).filter(TenantModel.owner_client_id == client.id).first()
            if linked_tenant:
                linked_tenant.name = client_name
            session.commit()
            session.close()
            self.reset_client_form()
            self.toast_message = "Cliente atualizado"
            self.toast_type = "success"
            return
        client = ClientModel(
            tenant_id=self.current_tenant,
            name=client_name,
            trade_name=trade_name,
            email=self.new_client_email.strip().lower(),
            phone=self.new_client_phone.strip() or None,
            address=self.new_client_address.strip() or None,
            state_code=self.new_client_state_code.strip() or None,
            cnpj=self.new_client_cnpj.strip() or None,
            business_sector=business_sector,
            employee_count=_parse_int(self.new_client_employee_count),
            branch_count=_parse_int(self.new_client_branch_count),
            annual_revenue=_parse_brl_amount(self.new_client_annual_revenue),
            parent_client_id=parent_client_id,
        )
        session.add(client)
        session.flush()
        base_slug = _slugify(client_name)
        tenant_id = base_slug or f"cliente-{client.id}"
        suffix = 1
        while session.query(TenantModel).filter(TenantModel.id == tenant_id).first():
            suffix += 1
            tenant_id = f"{base_slug}-{suffix}" if base_slug else f"cliente-{client.id}-{suffix}"
        session.add(
            TenantModel(
                id=tenant_id,
                name=client_name,
                slug=tenant_id,
                owner_client_id=client.id,
                limit_users=50,
            )
        )
        session.commit()
        session.close()
        self.reset_client_form()
        self.toast_message = f"Cliente criado com tenant {tenant_id}"
        self.toast_type = "success"

    def create_user(self):
        if not self.can_manage_users:
            self.toast_message = "Sem permissao para criar usuarios"
            self.toast_type = "error"
            return
        if not self.new_user_name or not self.new_user_email:
            self.toast_message = "Nome e e-mail sao obrigatorios"
            self.toast_type = "error"
            return
        session = SessionLocal()
        editing_id = int(self.editing_user_id) if self.editing_user_id.isdigit() else None
        if not self.new_user_password and editing_id is None:
            self.toast_message = "Senha inicial obrigatoria para novo usuario"
            self.toast_type = "error"
            session.close()
            return
        exists = session.query(UserModel).filter(UserModel.email == self.new_user_email.strip().lower()).first()
        if exists and exists.id != editing_id:
            self.toast_message = "E-mail ja cadastrado"
            self.toast_type = "error"
            session.close()
            return
        target_tenant = "default" if self.new_user_scope == "smartlab" else (self.new_user_tenant_id or self.current_tenant)
        target_client_id = int(self.new_user_client_id) if self.new_user_scope == "cliente" and self.new_user_client_id.isdigit() else None
        if self.new_user_scope == "cliente" and (target_client_id is None or not target_tenant):
            self.toast_message = "Usuario de cliente precisa estar vinculado a um cliente e tenant"
            self.toast_type = "error"
            session.close()
            return
        if self.new_user_scope == "cliente":
            tenant = session.query(TenantModel).filter(TenantModel.id == target_tenant).first()
            if not tenant:
                self.toast_message = "Tenant informado nao existe"
                self.toast_type = "error"
                session.close()
                return
            if tenant.owner_client_id != target_client_id:
                self.toast_message = "Usuario de cliente deve estar vinculado ao tenant do proprio cliente"
                self.toast_type = "error"
                session.close()
                return
        profession = (
            self.new_user_custom_profession.strip()
            if self.new_user_profession == "Outro"
            else self.new_user_profession.strip()
        )
        if not profession:
            self.toast_message = "Informe a profissao do usuario"
            self.toast_type = "error"
            session.close()
            return
        department = (
            self.new_user_custom_department.strip()
            if self.new_user_department == "Outro"
            else self.new_user_department.strip()
        )
        if not department:
            self.toast_message = "Informe o departamento do usuario"
            self.toast_type = "error"
            session.close()
            return
        assigned_client_ids = sorted({client_id for client_id in self.new_user_assigned_client_ids if client_id.isdigit()})
        reports_to_user_id = int(self.new_user_reports_to_user_id) if self.new_user_reports_to_user_id.isdigit() else None
        if editing_id is not None:
            user = session.query(UserModel).filter(UserModel.id == editing_id).first()
            if not user:
                session.close()
                self.toast_message = "Usuario nao encontrado para edicao"
                self.toast_type = "error"
                return
            user.name = self.new_user_name.strip()
            user.email = self.new_user_email.strip().lower()
            if self.new_user_password.strip():
                user.password = self.new_user_password
                user.must_change_password = 1 if self.new_user_scope == "cliente" else 0
            user.role = self.new_user_role
            user.account_scope = self.new_user_scope
            user.client_id = target_client_id if self.new_user_scope == "cliente" else None
            user.profession = profession
            user.department = department
            user.reports_to_user_id = reports_to_user_id
            user.assigned_client_ids = json.dumps(assigned_client_ids)
            user.tenant_id = target_tenant
        else:
            session.add(
                UserModel(
                    name=self.new_user_name.strip(),
                    email=self.new_user_email.strip().lower(),
                    password=self.new_user_password,
                    role=self.new_user_role,
                    account_scope=self.new_user_scope,
                    client_id=target_client_id if self.new_user_scope == "cliente" else None,
                    must_change_password=1 if self.new_user_scope == "cliente" else 0,
                    profession=profession,
                    department=department,
                    reports_to_user_id=reports_to_user_id,
                    assigned_client_ids=json.dumps(assigned_client_ids),
                    tenant_id=target_tenant,
                )
            )
        session.commit()
        session.close()
        self.reset_user_form()
        self.toast_message = "Usuario atualizado" if editing_id is not None else "Usuario criado"
        self.toast_type = "success"

    def delete_user(self, user_id: int):
        if not self.can_delete_users:
            self.toast_message = "Sem permissao para remover usuarios"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = (
            session.query(UserModel)
            .filter(UserModel.id == user_id, UserModel.tenant_id == self.current_tenant)
            .first()
        )
        if row:
            if row.email == self.login_email.strip().lower():
                self.toast_message = "Nao remova a conta em uso"
                self.toast_type = "error"
                session.close()
                return
            session.delete(row)
            session.commit()
            self.toast_message = "Usuario removido"
            self.toast_type = "success"
        session.close()

    def delete_client(self, client_id: int):
        if not self.can_delete_clients:
            self.toast_message = "Sem permissão para deletar clientes"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = (
            session.query(ClientModel)
            .filter(ClientModel.id == client_id, ClientModel.tenant_id == self.current_tenant)
            .first()
        )
        if row:
            session.delete(row)
            session.commit()
            self.toast_message = "Cliente removido"
            self.toast_type = "success"
        session.close()

    def create_tenant(self):
        if not self.can_manage_tenants:
            self.toast_message = "Permissão insuficiente"
            self.toast_type = "error"
            return
        if not self.new_tenant_name or not self.new_tenant_slug:
            self.toast_message = "Nome e slug são obrigatórios"
            self.toast_type = "error"
            return
        session = SessionLocal()
        owner_client_id = int(self.new_tenant_client_id) if self.new_tenant_client_id.isdigit() else None
        if owner_client_id is None:
            self.toast_message = "Tenant de operacao deve ser vinculado a um cliente"
            self.toast_type = "error"
            session.close()
            return
        tenant_slug = self.new_tenant_slug.strip().lower().replace(" ", "-")
        editing_id = self.editing_tenant_id.strip()
        if editing_id:
            row = session.query(TenantModel).filter(TenantModel.id == editing_id).first()
            if not row:
                session.close()
                self.toast_message = "Tenant nao encontrado para edicao"
                self.toast_type = "error"
                return
            slug_exists = (
                session.query(TenantModel)
                .filter(TenantModel.slug == tenant_slug, TenantModel.id != editing_id)
                .first()
            )
            if slug_exists:
                self.toast_message = "Slug já existe"
                self.toast_type = "error"
                session.close()
                return
            row.name = self.new_tenant_name.strip()
            row.slug = tenant_slug
            row.owner_client_id = owner_client_id
            row.limit_users = int(self.new_tenant_limit or "50")
        else:
            tenant_id = tenant_slug
            exists = session.query(TenantModel).filter(TenantModel.id == tenant_id).first()
            if exists:
                self.toast_message = "Slug já existe"
                self.toast_type = "error"
                session.close()
                return
            session.add(
                TenantModel(
                    id=tenant_id,
                    name=self.new_tenant_name.strip(),
                    slug=tenant_slug,
                    owner_client_id=owner_client_id,
                    limit_users=int(self.new_tenant_limit or "50"),
                )
            )
        session.commit()
        session.close()
        self.reset_tenant_form()
        self.toast_message = "Tenant atualizado" if editing_id else "Tenant criado"
        self.toast_type = "success"

    def delete_tenant(self, tenant_id: str):
        if not self.can_delete_tenants:
            self.toast_message = "Apenas admin pode deletar tenants"
            self.toast_type = "error"
            return
        if tenant_id == self.current_tenant:
            self.toast_message = "Troque de tenant antes de deletar o atual"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = session.query(TenantModel).filter(TenantModel.id == tenant_id).first()
        if row:
            session.delete(row)
            session.commit()
            self.toast_message = "Tenant removido"
            self.toast_type = "success"
        session.close()

    def create_role(self):
        if not self.can_manage_roles:
            self.toast_message = "Sem permissão para criar papéis"
            self.toast_type = "error"
            return
        perms = [p.strip() for p in self.new_role_permissions.split(",") if p.strip()]
        session = SessionLocal()
        if self.editing_role_id.isdigit():
            row = session.query(RoleModel).filter(RoleModel.id == int(self.editing_role_id), RoleModel.tenant_id == self.current_tenant).first()
            if not row:
                session.close()
                self.toast_message = "Papel nao encontrado para edicao"
                self.toast_type = "error"
                return
            row.name = self.new_role_name or "Novo Papel"
            row.permissions = json.dumps(perms)
        else:
            session.add(
                RoleModel(
                    tenant_id=self.current_tenant,
                    name=self.new_role_name or "Novo Papel",
                    permissions=json.dumps(perms),
                )
            )
        session.commit()
        session.close()
        was_editing = self.editing_role_id != ""
        self.reset_role_form()
        self.toast_message = "Papel atualizado" if was_editing else "Papel criado"
        self.toast_type = "success"

    def delete_role(self, role_id: int):
        if "delete:roles" not in ROLE_PERMS.get(self.user_role, set()):
            self.toast_message = "Sem permissão para deletar papéis"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = session.query(RoleModel).filter(RoleModel.id == role_id, RoleModel.tenant_id == self.current_tenant).first()
        if row:
            session.delete(row)
            session.commit()
            self.toast_message = "Papel removido"
            self.toast_type = "success"
        session.close()

    def create_responsibility(self):
        if not self.can_manage_resps:
            self.toast_message = "Sem permissão para criar responsabilidades"
            self.toast_type = "error"
            return
        if not self.new_resp_role_id or not self.new_resp_desc:
            self.toast_message = "Selecione papel e informe descrição"
            self.toast_type = "error"
            return
        session = SessionLocal()
        if self.editing_resp_id.isdigit():
            row = (
                session.query(ResponsibilityModel)
                .filter(ResponsibilityModel.id == int(self.editing_resp_id), ResponsibilityModel.tenant_id == self.current_tenant)
                .first()
            )
            if not row:
                session.close()
                self.toast_message = "Responsabilidade nao encontrada para edicao"
                self.toast_type = "error"
                return
            row.role_id = int(self.new_resp_role_id)
            row.description = self.new_resp_desc
        else:
            session.add(
                ResponsibilityModel(
                    tenant_id=self.current_tenant,
                    role_id=int(self.new_resp_role_id),
                    description=self.new_resp_desc,
                )
            )
        session.commit()
        session.close()
        was_editing = self.editing_resp_id != ""
        self.reset_resp_form()
        self.toast_message = "Responsabilidade atualizada" if was_editing else "Responsabilidade adicionada"
        self.toast_type = "success"

    def delete_responsibility(self, resp_id: int):
        if "delete:responsabilidades" not in ROLE_PERMS.get(self.user_role, set()):
            self.toast_message = "Sem permissão para deletar"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = (
            session.query(ResponsibilityModel)
            .filter(ResponsibilityModel.id == resp_id, ResponsibilityModel.tenant_id == self.current_tenant)
            .first()
        )
        if row:
            session.delete(row)
            session.commit()
            self.toast_message = "Responsabilidade removida"
            self.toast_type = "success"
        session.close()

    def create_form(self):
        if not self.can_manage_forms:
            self.toast_message = "Sem permissão para criar pesquisas"
            self.toast_type = "error"
            return
        if not self.new_form_name:
            self.toast_message = "Informe o nome da pesquisa"
            self.toast_type = "error"
            return
        session = SessionLocal()
        if self.editing_form_id.isdigit():
            survey = (
                session.query(SurveyModel)
                .filter(SurveyModel.id == int(self.editing_form_id), SurveyModel.tenant_id == self.current_tenant)
                .first()
            )
            if not survey:
                session.close()
                self.toast_message = "Pesquisa nao encontrada para edicao"
                self.toast_type = "error"
                return
            survey.name = self.new_form_name.strip()
            survey.service_name = self.new_form_category
            if not survey.share_token:
                survey.share_token = secrets.token_urlsafe(8)
            legacy_form = None
            if survey.legacy_form_id is not None:
                legacy_form = session.query(FormModel).filter(FormModel.id == int(survey.legacy_form_id)).first()
            if legacy_form:
                legacy_form.name = survey.name
                legacy_form.category = survey.service_name
                legacy_form.target_client_id = None
                legacy_form.target_user_email = None
            session.commit()
            selected_form_id = survey.id
            session.close()
            self.selected_form_id = str(selected_form_id)
            self.reset_form_builder()
            self.toast_message = "Pesquisa atualizada"
            self.toast_type = "success"
            return
        legacy_form = FormModel(
            tenant_id=self.current_tenant,
            name=self.new_form_name.strip(),
            category=self.new_form_category,
            target_client_id=None,
            target_user_email=None,
        )
        session.add(legacy_form)
        session.commit()
        session.refresh(legacy_form)
        survey = SurveyModel(
            tenant_id=self.current_tenant,
            name=self.new_form_name.strip(),
            service_name=self.new_form_category,
            share_token=secrets.token_urlsafe(8),
            legacy_form_id=legacy_form.id,
        )
        session.add(survey)
        session.commit()
        session.refresh(survey)
        session.close()
        self.selected_form_id = str(survey.id)
        self.reset_form_builder()
        self.toast_message = "Pesquisa criada"
        self.toast_type = "success"

    def delete_form(self, form_id: int):
        if "delete:forms" not in ROLE_PERMS.get(self.user_role, set()):
            self.toast_message = "Sem permissão para deletar pesquisas"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = session.query(SurveyModel).filter(SurveyModel.id == form_id, SurveyModel.tenant_id == self.current_tenant).first()
        if row:
            if row.legacy_form_id is not None:
                legacy_form = session.query(FormModel).filter(FormModel.id == int(row.legacy_form_id)).first()
                if legacy_form:
                    session.delete(legacy_form)
            session.query(QuestionModel).filter(QuestionModel.survey_id == form_id).delete()
            session.delete(row)
            session.commit()
            self.toast_message = "Pesquisa removida"
            self.toast_type = "success"
            if self.selected_form_id == str(form_id):
                self.selected_form_id = ""
            if self.editing_form_id == str(form_id):
                self.reset_form_builder()
        session.close()

    def select_form(self, value: str):
        self.selected_form_id = value.split(" - ", 1)[0].strip() if value else ""

    def select_form_by_id(self, form_id: int):
        self.selected_form_id = str(form_id)

    def create_interview_session(self):
        if not self.can_operate_interviews:
            self.toast_message = "Somente consultores SmartLab podem registrar entrevistas"
            self.toast_type = "error"
            return
        if not self.new_interview_form_id.isdigit():
            self.toast_message = "Selecione a pesquisa base da aplicação"
            self.toast_type = "error"
            return
        if not self.new_interview_client_id.isdigit():
            self.toast_message = "Selecione o cliente da entrevista"
            self.toast_type = "error"
            return
        if not self.new_interview_user_id.isdigit():
            self.toast_message = "Selecione o usuario que sera entrevistado"
            self.toast_type = "error"
            return
        session = SessionLocal()
        survey = (
            session.query(SurveyModel)
            .filter(
                SurveyModel.id == int(self.new_interview_form_id),
                SurveyModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        if not survey:
            session.close()
            self.toast_message = "Pesquisa nao encontrada"
            self.toast_type = "error"
            return
        interviewee = (
            session.query(UserModel)
            .filter(
                UserModel.id == int(self.new_interview_user_id),
                UserModel.account_scope == "cliente",
            )
            .first()
        )
        if not interviewee:
            session.close()
            self.toast_message = "Usuario entrevistado nao encontrado"
            self.toast_type = "error"
            return
        if interviewee.client_id != int(self.new_interview_client_id):
            session.close()
            self.toast_message = "O usuario selecionado nao pertence ao cliente informado"
            self.toast_type = "error"
            return
        consultant_name = self.login_email.strip().lower() or "consultor@smartlab.com"
        interview = None
        if self.editing_interview_id.isdigit():
            interview = (
                session.query(InterviewSessionModel)
                .filter(
                    InterviewSessionModel.id == int(self.editing_interview_id),
                    InterviewSessionModel.tenant_id == self.current_tenant,
                )
                .first()
            )
        if interview:
            interview.form_id = int(survey.legacy_form_id or 0)
            interview.survey_id = int(self.new_interview_form_id)
            interview.project_id = None
            interview.client_id = int(self.new_interview_client_id) if self.new_interview_client_id.isdigit() else None
            interview.interviewee_user_id = int(self.new_interview_user_id)
            interview.interview_date = self.new_interview_date.strip() or datetime.utcnow().strftime("%Y-%m-%d")
            interview.interviewee_name = interviewee.name or interviewee.email
            interview.interviewee_role = interviewee.profession or interviewee.department or None
            interview.consultant_name = consultant_name
            interview.notes = self.new_interview_notes.strip()
            toast_message = "Entrevista atualizada"
        else:
            interview = InterviewSessionModel(
                tenant_id=self.current_tenant,
                form_id=int(survey.legacy_form_id or 0),
                survey_id=int(self.new_interview_form_id),
                project_id=None,
                client_id=int(self.new_interview_client_id) if self.new_interview_client_id.isdigit() else None,
                interviewee_user_id=int(self.new_interview_user_id),
                interview_date=self.new_interview_date.strip() or datetime.utcnow().strftime("%Y-%m-%d"),
                interviewee_name=(interviewee.name or interviewee.email),
                interviewee_role=(interviewee.profession or interviewee.department or None),
                consultant_name=consultant_name,
                status="em_andamento",
                notes=self.new_interview_notes.strip(),
            )
            session.add(interview)
            toast_message = "Entrevista criada"
        session.commit()
        session.refresh(interview)
        session.close()
        self.selected_interview_id = str(interview.id)
        self.selected_form_id = str(interview.survey_id or "")
        self.interview_answer_map = {}
        self.interview_score_map = {}
        self.reset_interview_form()
        self.toast_message = toast_message
        self.toast_type = "success"

    def start_edit_interview(self, interview_id: str):
        if not str(interview_id).isdigit():
            self.toast_message = "Entrevista invalida"
            self.toast_type = "error"
            return
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(
                InterviewSessionModel.id == int(interview_id),
                InterviewSessionModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        session.close()
        if not interview:
            self.toast_message = "Entrevista nao encontrada"
            self.toast_type = "error"
            return
        response_rows = (
            session.query(ResponseModel)
            .filter(
                ResponseModel.tenant_id == self.current_tenant,
                ResponseModel.interview_id == int(interview_id),
            )
            .all()
        )
        self.editing_interview_id = str(interview.id)
        self.selected_interview_id = str(interview.id)
        self.selected_form_id = str(interview.survey_id or "")
        self.new_interview_form_id = str(interview.survey_id or "")
        self.new_interview_client_id = str(interview.client_id or "")
        self.new_interview_user_id = str(interview.interviewee_user_id or "")
        self.new_interview_date = interview.interview_date or ""
        self.new_interview_notes = interview.notes or ""
        self.interview_answer_map = {
            str(row.question_id): row.answer or ""
            for row in response_rows
            if row.question_id is not None
        }
        self.interview_score_map = {
            str(row.question_id): str(row.score if row.score is not None else 0)
            for row in response_rows
            if row.question_id is not None
        }
        self.toast_message = "Entrevista carregada para alteracao"
        self.toast_type = "success"

    def delete_interview_session(self, interview_id: str):
        if not str(interview_id).isdigit():
            self.toast_message = "Entrevista invalida"
            self.toast_type = "error"
            return
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(
                InterviewSessionModel.id == int(interview_id),
                InterviewSessionModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        if not interview:
            session.close()
            self.toast_message = "Entrevista nao encontrada"
            self.toast_type = "error"
            return
        session.query(ResponseModel).filter(
            ResponseModel.tenant_id == self.current_tenant,
            ResponseModel.interview_id == int(interview_id),
        ).delete()
        session.delete(interview)
        session.commit()
        session.close()
        if self.selected_interview_id == str(interview_id):
            self.selected_interview_id = ""
            self.selected_form_id = ""
            self.interview_answer_map = {}
            self.interview_score_map = {}
        if self.editing_interview_id == str(interview_id):
            self.reset_interview_form()
        self.toast_message = "Entrevista excluida"
        self.toast_type = "success"

    def select_interview_session(self, interview_id: str):
        self.selected_interview_id = str(interview_id)
        if not str(interview_id).isdigit():
            self.interview_answer_map = {}
            self.interview_score_map = {}
            return
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(
                InterviewSessionModel.id == int(interview_id),
                InterviewSessionModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        if interview:
            self.selected_form_id = str(interview.survey_id or "")
            response_rows = (
                session.query(ResponseModel)
                .filter(
                    ResponseModel.tenant_id == self.current_tenant,
                    ResponseModel.interview_id == int(interview_id),
                )
                .all()
            )
            self.interview_answer_map = {
                str(row.question_id): row.answer or ""
                for row in response_rows
                if row.question_id is not None
            }
            self.interview_score_map = {
                str(row.question_id): str(row.score if row.score is not None else 0)
                for row in response_rows
                if row.question_id is not None
            }
        else:
            self.interview_answer_map = {}
            self.interview_score_map = {}
        session.close()

    def _save_interview_responses_internal(self) -> bool:
        if not self.selected_interview_id.isdigit():
            self.toast_message = "Selecione uma entrevista ativa"
            self.toast_type = "error"
            return False
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(
                InterviewSessionModel.id == int(self.selected_interview_id),
                InterviewSessionModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        if not interview:
            session.close()
            self.toast_message = "Entrevista nao encontrada"
            self.toast_type = "error"
            return False
        questions = (
            session.query(QuestionModel)
            .filter(
                QuestionModel.tenant_id == self.current_tenant,
                QuestionModel.survey_id == int(interview.survey_id or 0),
            )
            .all()
        )
        survey = None
        if interview.survey_id is not None:
            survey = session.query(SurveyModel).filter(SurveyModel.id == int(interview.survey_id)).first()
        service_name = survey.service_name if survey else self.selected_interview_record["form_name"]
        saved_count = 0
        for question in questions:
            question_id = str(question.id)
            existing = (
                session.query(ResponseModel)
                .filter(
                    ResponseModel.tenant_id == self.current_tenant,
                    ResponseModel.interview_id == interview.id,
                    ResponseModel.question_id == question.id,
                )
                .first()
            )
            answer_raw = self.interview_answer_map.get(question_id)
            if answer_raw is None:
                answer = (existing.answer or "").strip() if existing else ""
            else:
                answer = answer_raw.strip()
            score_raw = self.interview_score_map.get(question_id)
            if score_raw is None:
                score = int(existing.score or 0) if existing else 0
            else:
                score = int(score_raw) if str(score_raw).lstrip("-").isdigit() else 0
            if existing:
                existing.answer = answer
                existing.score = score
                existing.survey_id = interview.survey_id
                existing.respondent_id = interview.interviewee_user_id
                existing.client_id = interview.client_id
                existing.service_name = service_name
                existing.response_token = f"survey-{interview.survey_id}-session-{interview.id}"
                existing.submitted_at = datetime.utcnow()
            else:
                session.add(
                    ResponseModel(
                        form_id=interview.form_id,
                        survey_id=interview.survey_id,
                        question_id=question.id,
                        interview_id=interview.id,
                        respondent_id=interview.interviewee_user_id,
                        client_id=interview.client_id,
                        service_name=service_name,
                        response_token=f"survey-{interview.survey_id}-session-{interview.id}",
                        tenant_id=self.current_tenant,
                        answer=answer,
                        score=score,
                        submitted_at=datetime.utcnow(),
                    )
                )
            saved_count += 1
        if saved_count == 0:
            session.close()
            self.toast_message = "Nenhuma resposta preenchida para salvar"
            self.toast_type = "error"
            return False
        dimension_scores: dict[str, int] = {}
        total_score = 0
        for question in questions:
            response = (
                session.query(ResponseModel)
                .filter(
                    ResponseModel.tenant_id == self.current_tenant,
                    ResponseModel.interview_id == interview.id,
                    ResponseModel.question_id == question.id,
                )
                .first()
            )
            if not response:
                continue
            weighted_score = int(response.score or 0) * int(question.weight or 1)
            dimension = question.dimension or "Sem dimensão"
            dimension_scores[dimension] = dimension_scores.get(dimension, 0) + weighted_score
            total_score += weighted_score
        interview.total_score = total_score
        interview.dimension_scores_json = json.dumps(dimension_scores)
        session.commit()
        session.close()
        self.toast_message = "Respostas da entrevista salvas"
        self.toast_type = "success"
        return True

    def save_interview_responses(self):
        saved = self._save_interview_responses_internal()
        if saved:
            self.selected_interview_id = ""
            self.selected_form_id = ""
            self.interview_answer_map = {}
            self.interview_score_map = {}
            self.editing_interview_id = ""

    def update_interview_status(self, status: str):
        if not self.selected_interview_id.isdigit():
            self.toast_message = "Selecione uma entrevista"
            self.toast_type = "error"
            return
        if status == "concluida":
            saved = self._save_interview_responses_internal()
            if saved is False:
                return
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(
                InterviewSessionModel.id == int(self.selected_interview_id),
                InterviewSessionModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        if not interview:
            session.close()
            self.toast_message = "Entrevista nao encontrada"
            self.toast_type = "error"
            return
        interview.status = status
        session.commit()
        session.close()
        self.toast_message = "Status da entrevista atualizado"
        self.toast_type = "success"

    def _resolve_selected_form_id(self) -> int | None:
        raw = (self.selected_form_id or "").strip()
        if raw.isdigit():
            return int(raw)
        session = SessionLocal()
        latest = (
            session.query(SurveyModel.id)
            .filter(SurveyModel.tenant_id == self.current_tenant)
            .order_by(SurveyModel.created_at.desc())
            .first()
        )
        session.close()
        if latest:
            self.selected_form_id = str(latest[0])
            return int(latest[0])
        return None

    def create_question(self):
        if not self.can_manage_forms:
            self.toast_message = "Sem permissão para editar pesquisas"
            self.toast_type = "error"
            return
        survey_id = self._resolve_selected_form_id()
        if not survey_id or not self.new_question_text:
            self.toast_message = "Selecione a pesquisa e preencha a pergunta"
            self.toast_type = "error"
            return
        dimension = (
            self.new_question_custom_dimension.strip()
            if self.new_question_dimension == "Outro"
            else self.new_question_dimension.strip()
        )
        if not dimension:
            self.toast_message = "Informe a dimensão da pergunta"
            self.toast_type = "error"
            return
        session = SessionLocal()
        survey = (
            session.query(SurveyModel)
            .filter(SurveyModel.id == survey_id, SurveyModel.tenant_id == self.current_tenant)
            .first()
        )
        if not survey:
            session.close()
            self.toast_message = "Pesquisa nao encontrada"
            self.toast_type = "error"
            return
        options = [o.strip() for o in self.new_question_options.split(",") if o.strip()]
        if self.new_question_type == "texto":
            options = []
        scale_definition = {
            "kind": self.new_question_type,
            "scale": {
                "0": "Nada aderente",
                "1": "Pouco aderente",
                "2": "Parcialmente aderente",
                "3": "Moderadamente aderente",
                "4": "Muito aderente",
                "5": "Totalmente aderente",
            },
        }
        next_order = (
            session.query(QuestionModel)
            .filter(QuestionModel.tenant_id == self.current_tenant, QuestionModel.survey_id == survey_id)
            .count()
        ) + 1
        if self.editing_question_id.isdigit():
            question = (
                session.query(QuestionModel)
                .filter(
                    QuestionModel.id == int(self.editing_question_id),
                    QuestionModel.tenant_id == self.current_tenant,
                )
                .first()
            )
            if not question:
                session.close()
                self.toast_message = "Pergunta nao encontrada para edicao"
                self.toast_type = "error"
                return
            question.form_id = int(survey.legacy_form_id or 0)
            question.survey_id = survey_id
            question.text = self.new_question_text
            question.qtype = json.dumps(scale_definition) if self.new_question_type == "escala_0_5" else json.dumps({"kind": "texto"})
            question.dimension = dimension
            question.polarity = self.new_question_polarity
            question.weight = int(self.new_question_weight or "1")
            question.options_json = json.dumps(
                {
                    "options": options,
                    "logic": {"show_if": self.new_question_condition.strip()},
                }
            )
            toast_message = "Pergunta atualizada"
        else:
            session.add(
                QuestionModel(
                    tenant_id=self.current_tenant,
                    form_id=int(survey.legacy_form_id or 0),
                    survey_id=survey_id,
                    text=self.new_question_text,
                    qtype=json.dumps(scale_definition) if self.new_question_type == "escala_0_5" else json.dumps({"kind": "texto"}),
                    dimension=dimension,
                    polarity=self.new_question_polarity,
                    weight=int(self.new_question_weight or "1"),
                    order_index=next_order,
                    options_json=json.dumps(
                        {
                            "options": options,
                            "logic": {"show_if": self.new_question_condition.strip()},
                        }
                    ),
                )
            )
            toast_message = "Pergunta criada"
        session.commit()
        session.close()
        self.new_question_text = ""
        self.new_question_condition = ""
        self.new_question_custom_dimension = ""
        self.new_question_weight = "1"
        self.new_question_polarity = "positiva"
        self.new_question_type = "escala_0_5"
        self.editing_question_id = ""
        self.toast_message = toast_message
        self.toast_type = "success"

    def add_mock_response(self, question_id: int, answer: str, score: int = 3):
        survey_id = self._resolve_selected_form_id()
        if not survey_id:
            return
        session = SessionLocal()
        session.add(
            ResponseModel(
                form_id=0,
                survey_id=survey_id,
                question_id=question_id,
                tenant_id=self.current_tenant,
                answer=answer,
                score=score,
            )
        )
        session.commit()
        session.close()
        self.toast_message = "Resposta registrada"
        self.toast_type = "success"

    def create_project(self):
        if not self.can_configure_projects:
            self.toast_message = "Projetos so podem ser configurados no SmartLab - interno"
            self.toast_type = "error"
            return
        if not self.new_project_name:
            self.toast_message = "Informe o nome do projeto"
            self.toast_type = "error"
            return
        session = SessionLocal()
        project = ProjectModel(
            tenant_id=self.current_tenant,
            name=self.new_project_name,
            project_type=self.new_project_type,
            status="planejamento",
            progress=0,
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        session.close()
        self.selected_project_id = str(project.id)
        self.new_project_name = ""
        self.toast_message = "Projeto criado"
        self.toast_type = "success"
        self.sync_project_assignments()

    def save_project_client_links(self):
        if not self.can_configure_projects:
            self.toast_message = "Vinculos so podem ser geridos no SmartLab - interno"
            self.toast_type = "error"
            return
        if not self.selected_project_id.isdigit():
            self.toast_message = "Selecione um projeto para vincular clientes"
            self.toast_type = "error"
            return
        session = SessionLocal()
        project_id = int(self.selected_project_id)
        session.query(ProjectAssignmentModel).filter(ProjectAssignmentModel.project_id == project_id).delete()
        for client_id in sorted({client_id for client_id in self.new_project_assigned_client_ids if client_id.isdigit()}):
            tenant = session.query(TenantModel).filter(TenantModel.owner_client_id == int(client_id)).first()
            if tenant:
                session.add(
                    ProjectAssignmentModel(
                        project_id=project_id,
                        tenant_id=tenant.id,
                        client_id=int(client_id),
                    )
                )
        session.commit()
        session.close()
        self.new_project_assigned_clients_open = False
        self.toast_message = "Clientes vinculados ao projeto"
        self.toast_type = "success"

    def add_workflow_box(self):
        if not self.selected_project_id or not self.new_box_title:
            self.toast_message = "Selecione projeto e nome da caixa"
            self.toast_type = "error"
            return
        session = SessionLocal()
        max_pos = (
            session.query(WorkflowBoxModel)
            .filter(
                WorkflowBoxModel.tenant_id == self.current_tenant,
                WorkflowBoxModel.project_id == int(self.selected_project_id),
            )
            .count()
        )
        session.add(
            WorkflowBoxModel(
                tenant_id=self.current_tenant,
                project_id=int(self.selected_project_id),
                title=self.new_box_title,
                box_type=self.new_box_type,
                position=max_pos + 1,
                config_json=json.dumps(
                    {
                        "source": "builder",
                        "timestamp": datetime.utcnow().isoformat(),
                        "zone": self.new_box_zone,
                        "method": self.new_box_method,
                        "endpoint": self.new_box_endpoint.strip(),
                        "retry_policy": self.new_box_retry_policy,
                        "schedule": self.new_box_schedule.strip(),
                        "condition": self.new_box_condition.strip(),
                        "output_key": self.new_box_output_key.strip(),
                        "headers": [item.strip() for item in self.new_box_headers.split(",") if item.strip()],
                        "credentials": {
                            "client_id": self.new_box_client_id.strip(),
                            "client_secret": self.new_box_client_secret.strip(),
                        },
                    }
                ),
            )
        )
        session.commit()
        session.close()
        self.new_box_title = ""
        self.new_box_endpoint = ""
        self.new_box_client_id = ""
        self.new_box_client_secret = ""
        self.new_box_condition = ""
        self.new_box_output_key = ""
        self.toast_message = "Caixa adicionada ao workflow"
        self.toast_type = "success"

    def add_sticky_note(self):
        if not self.selected_project_id or not self.new_sticky_note_text.strip():
            self.toast_message = "Selecione projeto e escreva a anotação"
            self.toast_type = "error"
            return
        session = SessionLocal()
        max_pos = (
            session.query(WorkflowBoxModel)
            .filter(
                WorkflowBoxModel.tenant_id == self.current_tenant,
                WorkflowBoxModel.project_id == int(self.selected_project_id),
            )
            .count()
        )
        session.add(
            WorkflowBoxModel(
                tenant_id=self.current_tenant,
                project_id=int(self.selected_project_id),
                title="Sticky Note",
                box_type="nota",
                position=max_pos + 1,
                config_json=json.dumps(
                    {
                        "zone": "right",
                        "note": self.new_sticky_note_text.strip(),
                        "source": "sticky-note",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ),
            )
        )
        session.commit()
        session.close()
        self.new_sticky_note_text = ""
        self.toast_message = "Sticky note adicionada"
        self.toast_type = "success"

    def move_workflow_box(self, box_id: int, direction: str):
        if not self.selected_project_id:
            return
        session = SessionLocal()
        rows = (
            session.query(WorkflowBoxModel)
            .filter(
                WorkflowBoxModel.tenant_id == self.current_tenant,
                WorkflowBoxModel.project_id == int(self.selected_project_id),
            )
            .order_by(WorkflowBoxModel.position.asc(), WorkflowBoxModel.id.asc())
            .all()
        )
        index = next((idx for idx, row in enumerate(rows) if row.id == box_id), -1)
        if index < 0:
            session.close()
            return
        target = index - 1 if direction == "up" else index + 1
        if target < 0 or target >= len(rows):
            session.close()
            return
        rows[index], rows[target] = rows[target], rows[index]
        for pos, row in enumerate(rows, start=1):
            row.position = pos
        session.commit()
        session.close()

    def nudge_workflow_box(self, box_id: int, axis: str, delta: int):
        session = SessionLocal()
        row = (
            session.query(WorkflowBoxModel)
            .filter(WorkflowBoxModel.id == box_id, WorkflowBoxModel.tenant_id == self.current_tenant)
            .first()
        )
        if not row:
            session.close()
            return
        config = json.loads(row.config_json or "{}")
        x = int(config.get("x", 24))
        y = int(config.get("y", 24))
        if axis == "x":
            x = max(0, min(920, x + delta))
        if axis == "y":
            y = max(0, min(420, y + delta))
        config["x"] = x
        config["y"] = y
        row.config_json = json.dumps(config)
        session.commit()
        session.close()

    def drop_workflow_box_to_zone(self, box_id: int, zone: str):
        session = SessionLocal()
        row = (
            session.query(WorkflowBoxModel)
            .filter(WorkflowBoxModel.id == box_id, WorkflowBoxModel.tenant_id == self.current_tenant)
            .first()
        )
        if not row:
            session.close()
            return
        config = json.loads(row.config_json or "{}")
        config["zone"] = zone
        row.config_json = json.dumps(config)
        session.commit()
        session.close()

    def delete_workflow_box(self, box_id: int):
        session = SessionLocal()
        row = (
            session.query(WorkflowBoxModel)
            .filter(
                WorkflowBoxModel.id == box_id,
                WorkflowBoxModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        if row:
            session.delete(row)
            session.commit()
            self.toast_message = "Caixa removida"
            self.toast_type = "success"
        session.close()

    def clear_workflow_logs(self):
        self.workflow_logs = []

    def execute_workflow(self):
        if not self.selected_project_id:
            self.toast_message = "Selecione um projeto para executar"
            self.toast_type = "error"
            return

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        logs = [f"[{timestamp}] Iniciando execução do workflow do projeto #{self.selected_project_id}"]
        items = [b for b in self.workflow_boxes_data if b["box_type"] != "nota"]
        if not items:
            logs.append("Nenhum node executável encontrado.")
            self.workflow_logs = logs
            self.toast_message = "Workflow sem nodes executáveis"
            self.toast_type = "error"
            return

        for node in items:
            config = node.get("config", {})
            method = config.get("method", "-")
            endpoint = config.get("endpoint", "")
            condition = str(config.get("condition", "")).strip()
            output_key = str(config.get("output_key", "")).strip()
            if node["box_type"] == "trigger":
                schedule = config.get("schedule", "sem agenda")
                logs.append(f"Trigger '{node['title']}' armado com schedule {schedule}")
                continue
            if condition:
                logs.append(f"Condicao avaliada em '{node['title']}': {condition}")
            if endpoint:
                logs.append(f"Node '{node['title']}' executado: {method} {endpoint}")
            else:
                logs.append(f"Node '{node['title']}' executado em modo interno ({node['box_type']})")
            if node["box_type"] == "analise":
                logs.append("Análise IA concluída: recomendação preliminar gerada.")
            if output_key:
                logs.append(f"Saida publicada no contexto como '{output_key}'.")

        logs.append("Execução finalizada com sucesso.")
        self.workflow_logs = logs
        self.toast_message = "Execução do workflow concluída"
        self.toast_type = "success"

    def create_action_plan(self):
        if not self.selected_project_id:
            self.toast_message = "Selecione um projeto"
            self.toast_type = "error"
            return
        if not self.new_action_title or not self.new_action_owner:
            self.toast_message = "Título e responsável são obrigatórios"
            self.toast_type = "error"
            return
        session = SessionLocal()
        session.add(
            ActionPlanModel(
                tenant_id=self.current_tenant,
                project_id=int(self.selected_project_id),
                title=self.new_action_title,
                owner=self.new_action_owner,
                due_date=self.new_action_due_date,
                status="a_fazer",
                expected_result=self.new_action_expected_result,
                attainment=0,
            )
        )
        session.commit()
        session.close()
        self.new_action_title = ""
        self.new_action_owner = ""
        self.new_action_due_date = ""
        self.new_action_expected_result = ""
        self.toast_message = "Ação criada"
        self.toast_type = "success"

    def move_action_status(self, action_id: int, status: str):
        session = SessionLocal()
        row = (
            session.query(ActionPlanModel)
            .filter(ActionPlanModel.id == action_id, ActionPlanModel.tenant_id == self.current_tenant)
            .first()
        )
        if not row:
            session.close()
            return
        row.status = status
        if status == "concluido" and row.attainment < 100:
            row.attainment = 100
            row.actual_result = row.actual_result or "Concluído conforme planejado."
        session.commit()
        session.close()
        self.toast_message = "Status atualizado"
        self.toast_type = "success"

    def add_permission_box(self, decision: str):
        if not self.perm_user_email or not self.perm_resource_name:
            self.toast_message = "Informe e-mail e recurso"
            self.toast_type = "error"
            return
        session = SessionLocal()
        session.add(
            PermissionBoxModel(
                tenant_id=self.current_tenant,
                user_email=self.perm_user_email.strip().lower(),
                resource=self.perm_resource_name,
                decision=decision,
            )
        )
        session.commit()
        session.close()
        self.perm_resource_name = ""
        self.toast_message = "Permissão atualizada"
        self.toast_type = "success"

    def apply_permission_from_catalog(self, resource: str, decision: str):
        if not self.perm_user_email.strip():
            self.toast_message = "Selecione o e-mail do usuario antes de aplicar permissoes"
            self.toast_type = "error"
            return
        session = SessionLocal()
        email = self.perm_user_email.strip().lower()
        existing = (
            session.query(PermissionBoxModel)
            .filter(
                PermissionBoxModel.tenant_id == self.current_tenant,
                PermissionBoxModel.user_email == email,
                PermissionBoxModel.resource == resource,
            )
            .first()
        )
        if existing:
            existing.decision = decision
        else:
            session.add(
                PermissionBoxModel(
                    tenant_id=self.current_tenant,
                    user_email=email,
                    resource=resource,
                    decision=decision,
                )
            )
        session.commit()
        session.close()
        self.toast_message = f"Permissao '{decision}' aplicada para {resource}"
        self.toast_type = "success"

    def clear_permission_from_catalog(self, resource: str):
        if not self.perm_user_email.strip():
            self.toast_message = "Selecione o e-mail do usuario"
            self.toast_type = "error"
            return
        session = SessionLocal()
        email = self.perm_user_email.strip().lower()
        row = (
            session.query(PermissionBoxModel)
            .filter(
                PermissionBoxModel.tenant_id == self.current_tenant,
                PermissionBoxModel.user_email == email,
                PermissionBoxModel.resource == resource,
            )
            .first()
        )
        if row:
            session.delete(row)
            session.commit()
        session.close()
        self.toast_message = f"Permissao removida de {resource}"
        self.toast_type = "success"

    def delete_permission_box(self, permission_id: int):
        session = SessionLocal()
        row = (
            session.query(PermissionBoxModel)
            .filter(
                PermissionBoxModel.id == permission_id,
                PermissionBoxModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        if row:
            session.delete(row)
            session.commit()
            self.toast_message = "Regra removida"
            self.toast_type = "success"
        session.close()

    def add_dashboard_box(self):
        if not self.new_dashboard_box_title:
            self.toast_message = "Informe o nome da caixa"
            self.toast_type = "error"
            return
        session = SessionLocal()
        max_pos = (
            session.query(DashboardBoxModel)
            .filter(
                DashboardBoxModel.tenant_id == self.current_tenant,
                DashboardBoxModel.role_scope == self.new_dashboard_box_scope,
            )
            .count()
        )
        session.add(
            DashboardBoxModel(
                tenant_id=self.current_tenant,
                role_scope=self.new_dashboard_box_scope,
                title=self.new_dashboard_box_title,
                kind=self.new_dashboard_box_kind,
                position=max_pos + 1,
                config_json=json.dumps(
                    {
                        "editable": True,
                        "source": self.new_dashboard_box_source,
                        "description": self.new_dashboard_box_description.strip(),
                        "embed_enabled": True,
                    }
                ),
            )
        )
        session.commit()
        session.close()
        self.new_dashboard_box_title = ""
        self.new_dashboard_box_description = ""
        self.toast_message = "Caixa do dashboard criada"
        self.toast_type = "success"

    def move_dashboard_box(self, box_id: int, direction: str):
        session = SessionLocal()
        scope = "consultor" if self.user_role in {"admin", "editor"} else "cliente"
        rows = (
            session.query(DashboardBoxModel)
            .filter(
                DashboardBoxModel.tenant_id == self.current_tenant,
                DashboardBoxModel.role_scope == scope,
            )
            .order_by(DashboardBoxModel.position.asc(), DashboardBoxModel.id.asc())
            .all()
        )
        index = next((idx for idx, row in enumerate(rows) if row.id == box_id), -1)
        if index < 0:
            session.close()
            return
        target = index - 1 if direction == "up" else index + 1
        if target < 0 or target >= len(rows):
            session.close()
            return
        rows[index], rows[target] = rows[target], rows[index]
        for pos, row in enumerate(rows, start=1):
            row.position = pos
        session.commit()
        session.close()

    def clear_toast(self):
        self.toast_message = ""

    def start_drag_question(self, question_text: str):
        self.dragged_question_text = question_text

    def drop_question_into_prompt(self):
        if not self.dragged_question_text:
            return
        prefix = f"{self.ai_prompt}\n\n" if self.ai_prompt else ""
        self.ai_prompt = f"{prefix}Pergunta arrastada: {self.dragged_question_text}"
        self.dragged_question_text = ""
        self.toast_message = "Pergunta adicionada via drag and drop"
        self.toast_type = "success"

    async def handle_resource_upload(self, files: list[rx.UploadFile]):
        if not files:
            self.toast_message = "Nenhum arquivo selecionado"
            self.toast_type = "error"
            return

        upload_dir = Path(str(rx.get_upload_dir())) / "resources"
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_files: list[str] = []

        for file in files:
            file_name = file.filename or "arquivo.bin"
            safe_name = file_name.replace("..", "").replace("/", "_").replace("\\", "_")
            file_bytes = await file.read()
            (upload_dir / safe_name).write_bytes(file_bytes)
            saved_files.append(safe_name)

        self.uploaded_resources = saved_files + self.uploaded_resources
        self.toast_message = f"{len(saved_files)} arquivo(s) enviado(s) com sucesso"
        self.toast_type = "success"

    def ask_ai(self):
        prompt = (self.ai_prompt or "").lower()
        rows = self.dashboard_table
        avg = 0.0
        if rows:
            avg = round(sum(float(r["media"]) for r in rows) / len(rows), 2)

        recommendation = [
            "Recomendação prática: priorize rituais de liderança visível em segurança e ajuste metas para evitar pressão insegura.",
            "Mapeie comportamentos críticos por turno e vincule feedbacks semanais com ações corretivas rápidas.",
            "Use os formulários para comparar Segurança vs Produtividade por área e atacar desvios com plano de 30-60-90 dias.",
        ]
        if "press" in prompt or "pressao" in prompt:
            recommendation.append(
                "Impacto da pressão: reduza conflitos de prioridade com regras claras de parada segura e escalonamento de risco."
            )
        if "lider" in prompt:
            recommendation.append(
                "Maturidade da liderança: treine líderes para abrir reuniões com aprendizados de quase acidentes e ações preventivas."
            )
        if "dashboard" in prompt:
            recommendation.append(
                "Leitura de dashboard: categorias abaixo de 2.5 são críticas e exigem intervenção imediata com owner definido."
            )

        self.ai_answer = (
            f"Assistente SSecur1 IA\n"
            f"Média geral atual: {avg}\n"
            f"Resumo: {' '.join(recommendation[:4])}\n"
            "Benefício esperado: decisões estratégicas mais acertadas, redução de riscos e integração segurança-produtividade."
        )


CARD_STYLE = {
    "bg": "var(--card-bg)",
    "backdrop_filter": "blur(10px)",
    "border": "1px solid var(--card-border)",
    "border_radius": "16px",
    "box_shadow": "0 12px 28px var(--card-shadow)",
}


def nav_button(label: str, icon: str, view: str) -> rx.Component:
    from ssecur1.ui.page import build_nav_button

    return build_nav_button(State=State, label=label, icon=icon, view=view)


def toast() -> rx.Component:
    from ssecur1.ui.public import build_toast

    return build_toast(State=State, CARD_STYLE=CARD_STYLE)


def delete_confirm_modal() -> rx.Component:
    from ssecur1.ui.public import build_delete_confirm_modal

    return build_delete_confirm_modal(State=State, CARD_STYLE=CARD_STYLE)


def landing_public() -> rx.Component:
    from ssecur1.ui.public import build_landing_public

    return build_landing_public(State=State, CARD_STYLE=CARD_STYLE, smartlab_logo=smartlab_logo)


def app_header() -> rx.Component:
    from ssecur1.ui.common import build_app_header

    return build_app_header(State=State, smartlab_logo=smartlab_logo)


def sidebar() -> rx.Component:
    from ssecur1.ui.common import build_sidebar

    return build_sidebar(State=State, nav_button=nav_button)


def metric_card(title: str, value: rx.Var) -> rx.Component:
    from ssecur1.ui.common import build_metric_card

    return build_metric_card(CARD_STYLE=CARD_STYLE, title=title, value=value)


def field_block(label: str, control: rx.Component, help_text: str = "") -> rx.Component:
    from ssecur1.ui.common import build_field_block

    return build_field_block(label=label, control=control, help_text=help_text)


def table_text_cell(primary: rx.Component, secondary: rx.Component | None = None) -> rx.Component:
    from ssecur1.ui.common import build_table_text_cell

    return build_table_text_cell(primary=primary, secondary=secondary)


def data_table(headers: list[str], rows: rx.Var, row_builder) -> rx.Component:
    from ssecur1.ui.common import build_data_table

    return build_data_table(CARD_STYLE=CARD_STYLE, headers=headers, rows=rows, row_builder=row_builder)


def workflow_connection_line(line_type: rx.Var) -> rx.Component:
    from ssecur1.ui.common import build_workflow_connection_line

    return build_workflow_connection_line(line_type=line_type)


def workflow_node(node_data: dict[str, Any]) -> rx.Component:
    from ssecur1.ui.common import build_workflow_node

    return build_workflow_node(State=State, node_data=node_data)


def apis_view() -> rx.Component:
    from ssecur1.ui.operacoes import build_apis_view

    return build_apis_view(State=State, CARD_STYLE=CARD_STYLE, data_table=data_table)


def dashboard_view() -> rx.Component:
    from ssecur1.ui.operacoes import build_dashboard_view

    return build_dashboard_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        metric_card=metric_card,
        data_table=data_table,
    )


def projetos_view() -> rx.Component:
    from ssecur1.ui.projetos import build_projetos_view

    return build_projetos_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        workflow_node=workflow_node,
        workflow_connection_line=workflow_connection_line,
        pesquisa_builder_view=pesquisa_builder_view,
    )


def planos_view() -> rx.Component:
    from ssecur1.ui.operacoes import build_planos_view

    return build_planos_view(State=State, CARD_STYLE=CARD_STYLE)


def permissoes_view() -> rx.Component:
    from ssecur1.ui.permissoes import build_permissoes_view

    return build_permissoes_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        metric_card=metric_card,
        field_block=field_block,
        table_text_cell=table_text_cell,
        data_table=data_table,
    )


def clientes_view() -> rx.Component:
    from ssecur1.ui.admin_people import build_clientes_view

    return build_clientes_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        field_block=field_block,
        table_text_cell=table_text_cell,
        data_table=data_table,
    )


def usuarios_view() -> rx.Component:
    from ssecur1.ui.admin_people import build_usuarios_view

    return build_usuarios_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        field_block=field_block,
        table_text_cell=table_text_cell,
        data_table=data_table,
    )


def tenants_view() -> rx.Component:
    from ssecur1.ui.admin_security import build_tenants_view

    return build_tenants_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        field_block=field_block,
        table_text_cell=table_text_cell,
        data_table=data_table,
    )


def papeis_view() -> rx.Component:
    from ssecur1.ui.admin_security import build_papeis_view

    return build_papeis_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        field_block=field_block,
        data_table=data_table,
    )


def responsabilidades_view() -> rx.Component:
    from ssecur1.ui.admin_security import build_responsabilidades_view

    return build_responsabilidades_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        field_block=field_block,
        data_table=data_table,
    )


def pesquisa_builder_view() -> rx.Component:
    from ssecur1.ui.pesquisa_builder import build_pesquisa_builder_view

    return build_pesquisa_builder_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        field_block=field_block,
        data_table=data_table,
    )


def formularios_view() -> rx.Component:
    from ssecur1.ui.formularios import build_formularios_view

    return build_formularios_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        metric_card=metric_card,
        field_block=field_block,
        table_text_cell=table_text_cell,
        data_table=data_table,
    )


def ia_view() -> rx.Component:
    from ssecur1.ui.shell import build_ia_view

    return build_ia_view(State=State, CARD_STYLE=CARD_STYLE)


def workspace_view() -> rx.Component:
    from ssecur1.ui.shell import build_workspace_view

    return build_workspace_view(
        State=State,
        sidebar=sidebar,
        app_header=app_header,
        dashboard_view=dashboard_view,
        apis_view=apis_view,
        projetos_view=projetos_view,
        planos_view=planos_view,
        permissoes_view=permissoes_view,
        usuarios_view=usuarios_view,
        clientes_view=clientes_view,
        tenants_view=tenants_view,
        papeis_view=papeis_view,
        responsabilidades_view=responsabilidades_view,
        formularios_view=formularios_view,
        ia_view=ia_view,
    )


def auth_modal() -> rx.Component:
    from ssecur1.ui.auth import build_auth_modal

    return build_auth_modal(State=State, CARD_STYLE=CARD_STYLE, smartlab_logo=smartlab_logo)


def main_page() -> rx.Component:
    from ssecur1.ui.page import build_main_page

    return build_main_page(
        State=State,
        workspace_view=workspace_view,
        landing_public=landing_public,
        auth_modal=auth_modal,
        toast=toast,
        delete_confirm_modal=delete_confirm_modal,
    )


app = rx.App(
    stylesheets=["styles.css"],
)
app.add_page(
    main_page,
    route="/",
    title="SSecur1 | Plataforma SaaS",
    description="Plataforma SaaS multi-tenant para diagnóstico de cultura de segurança, liderança e produtividade segura.",
)
