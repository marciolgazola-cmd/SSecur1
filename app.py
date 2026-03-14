import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import reflex as rx
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()
DATABASE_URL = "sqlite:///ssecur1.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TenantModel(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    owner_client_id = Column(Integer, nullable=True)
    limit_users = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    role = Column(String, default="viewer")
    account_scope = Column(String, default="smartlab")
    client_id = Column(Integer, nullable=True)
    must_change_password = Column(Integer, default=0)
    profession = Column(String, nullable=True)
    department = Column(String, nullable=True)
    reports_to_user_id = Column(Integer, nullable=True)
    assigned_client_ids = Column(Text, default="[]")
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)


class ClientModel(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    cnpj = Column(String, nullable=True)
    business_sector = Column(String, nullable=True)
    employee_count = Column(Integer, nullable=True)
    branch_count = Column(Integer, nullable=True)
    annual_revenue = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RoleModel(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    permissions = Column(Text, default="[]")


class ResponsibilityModel(Base):
    __tablename__ = "responsibilities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    description = Column(Text, nullable=False)
    role = relationship("RoleModel")


class FormModel(Base):
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)


class QuestionModel(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    text = Column(Text, nullable=False)
    qtype = Column(String, default="fechada")
    options_json = Column(Text, default="[]")


class ResponseModel(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    answer = Column(Text, nullable=False)
    score = Column(Integer, default=3)


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    project_type = Column(String, default="Diagnóstico de Cultura")
    status = Column(String, default="planejamento")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProjectAssignmentModel(Base):
    __tablename__ = "project_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    client_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowBoxModel(Base):
    __tablename__ = "workflow_boxes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    box_type = Column(String, default="etapa")
    position = Column(Integer, default=0)
    config_json = Column(Text, default="{}")


class ActionPlanModel(Base):
    __tablename__ = "action_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    due_date = Column(String, default="")
    status = Column(String, default="a_fazer")
    expected_result = Column(Text, default="")
    actual_result = Column(Text, default="")
    attainment = Column(Integer, default=0)


class PermissionBoxModel(Base):
    __tablename__ = "permission_boxes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_email = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    decision = Column(String, default="permitido")


class DashboardBoxModel(Base):
    __tablename__ = "dashboard_boxes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    role_scope = Column(String, default="consultor")
    title = Column(String, nullable=False)
    kind = Column(String, default="kpi")
    position = Column(Integer, default=0)
    config_json = Column(Text, default="{}")


Base.metadata.create_all(bind=engine)


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


def _loads_json(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _question_payload(options_json: str | None) -> dict[str, Any]:
    parsed = _loads_json(options_json, [])
    if isinstance(parsed, dict):
        options = parsed.get("options", [])
        logic = parsed.get("logic", {})
        return {
            "options": options if isinstance(options, list) else [],
            "logic": logic if isinstance(logic, dict) else {},
        }
    if isinstance(parsed, list):
        return {"options": parsed, "logic": {}}
    return {"options": [], "logic": {}}


def _slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "-")


def _dom_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return token.strip("-") or "item"


def _parse_int(value: str) -> int | None:
    cleaned = re.sub(r"[^\d]", "", value or "")
    return int(cleaned) if cleaned else None


def _parse_brl_amount(value: str) -> int | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    digits = re.sub(r"[^\d]", "", cleaned)
    return int(digits) if digits else None


def _format_brl_amount(value: int | None) -> str:
    if value is None:
        return "-"
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _safe_add_column(conn, table_name: str, column_name: str, ddl: str) -> None:
    columns = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table_name});").fetchall()}
    if column_name in columns:
        return
    try:
        conn.exec_driver_sql(ddl)
    except OperationalError as err:
        if "duplicate column name" not in str(err).lower():
            raise


def _seed() -> None:
    session = SessionLocal()
    if session.query(TenantModel).count() == 0:
        t1 = TenantModel(id="default", name="SmartLab", slug="smartlab", limit_users=150)
        session.add(t1)
        session.add(
            UserModel(
                name="Admin SmartLab",
                email="admin@smartlab.com",
                password="admin123",
                role="admin",
                account_scope="smartlab",
                tenant_id="default",
            )
        )
        session.commit()
    session.close()


def _ensure_schema_updates() -> None:
    with engine.begin() as conn:
        user_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users);").fetchall()}
        if "account_scope" not in user_columns:
            _safe_add_column(conn, "users", "account_scope", "ALTER TABLE users ADD COLUMN account_scope VARCHAR DEFAULT 'smartlab';")
            conn.exec_driver_sql("UPDATE users SET account_scope = 'smartlab' WHERE account_scope IS NULL;")
        if "client_id" not in user_columns:
            _safe_add_column(conn, "users", "client_id", "ALTER TABLE users ADD COLUMN client_id INTEGER;")
        _safe_add_column(conn, "users", "must_change_password", "ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0;")
        _safe_add_column(conn, "users", "profession", "ALTER TABLE users ADD COLUMN profession VARCHAR;")
        _safe_add_column(conn, "users", "department", "ALTER TABLE users ADD COLUMN department VARCHAR;")
        _safe_add_column(conn, "users", "reports_to_user_id", "ALTER TABLE users ADD COLUMN reports_to_user_id INTEGER;")
        _safe_add_column(conn, "users", "assigned_client_ids", "ALTER TABLE users ADD COLUMN assigned_client_ids TEXT DEFAULT '[]';")
        _safe_add_column(conn, "tenants", "owner_client_id", "ALTER TABLE tenants ADD COLUMN owner_client_id INTEGER;")
        _safe_add_column(conn, "clients", "cnpj", "ALTER TABLE clients ADD COLUMN cnpj VARCHAR;")
        _safe_add_column(conn, "clients", "business_sector", "ALTER TABLE clients ADD COLUMN business_sector VARCHAR;")
        _safe_add_column(conn, "clients", "employee_count", "ALTER TABLE clients ADD COLUMN employee_count INTEGER;")
        _safe_add_column(conn, "clients", "branch_count", "ALTER TABLE clients ADD COLUMN branch_count INTEGER;")
        _safe_add_column(conn, "clients", "annual_revenue", "ALTER TABLE clients ADD COLUMN annual_revenue INTEGER;")


_ensure_schema_updates()
_seed()


def smartlab_logo(size: str = "44px") -> rx.Component:
    return rx.image(
        src="/LogoSmartLab.jpeg",
        width=size,
        height="auto",
        alt="Logo SSecur1",
        border_radius="10px",
        object_fit="contain",
    )


class State(rx.State):
    is_logged: bool = False
    user_role: str = "viewer"
    user_scope: str = "smartlab"
    user_client_id: str = ""
    assigned_client_ids: list[str] = []
    home_tenant_id: str = "default"
    current_tenant: str = "default"
    dark_mode: bool = False

    sidebar_collapsed: bool = False
    mobile_menu_open: bool = False
    auth_open: bool = False
    auth_mode: str = "login"
    active_view: str = "dashboard"

    toast_message: str = ""
    toast_type: str = "success"

    login_email: str = "admin@smartlab.com"
    login_password: str = "admin123"
    login_password_visible: bool = False
    force_password_reset_required: bool = False
    first_access_new_password: str = ""
    first_access_confirm_password: str = ""
    first_access_password_visible: bool = False
    register_name: str = ""
    register_email: str = ""
    register_password: str = ""
    register_password_visible: bool = False
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
    new_client_email: str = ""
    new_client_cnpj: str = ""
    new_client_business_sector: str = "Industria"
    new_client_custom_business_sector: str = ""
    new_client_employee_count: str = ""
    new_client_branch_count: str = ""
    new_client_annual_revenue: str = ""
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
    selected_form_id: str = ""
    editing_form_id: str = ""
    new_question_text: str = ""
    new_question_type: str = "fechada"
    new_question_options: str = "Sempre,Frequentemente,Raramente,Nunca"
    new_question_condition: str = ""
    editing_user_id: str = ""

    ai_prompt: str = ""
    ai_answer: str = ""

    new_project_name: str = ""
    new_project_type: str = "Diagnóstico de Cultura"
    selected_project_id: str = ""
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

    @rx.var
    def theme_class(self) -> str:
        return "theme-dark app-theme" if self.dark_mode else "theme-light app-theme"

    @rx.var
    def theme_toggle_label(self) -> str:
        return "Modo Claro" if self.dark_mode else "Modo Escuro"

    @rx.var
    def theme_toggle_short_label(self) -> str:
        return "Claro" if self.dark_mode else "Escuro"

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
        if self.user_scope == "cliente" and self.user_client_id.isdigit():
            client_query = client_query.filter(ClientModel.id == int(self.user_client_id))
        else:
            client_query = client_query.filter(ClientModel.tenant_id == self.current_tenant)
        clients = client_query.order_by(ClientModel.name.asc()).all()
        for row in clients:
            haystack = " ".join(
                [
                    row.name or "",
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
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def clients_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        query = session.query(ClientModel)
        if self.user_scope == "cliente" and self.user_client_id.isdigit():
            query = query.filter(ClientModel.id == int(self.user_client_id))
        else:
            query = query.filter(ClientModel.tenant_id == self.current_tenant)
        rows = query.order_by(ClientModel.created_at.desc()).all()
        tenant_lookup = {str(row[0]): row[1] for row in session.query(TenantModel.owner_client_id, TenantModel.id).all() if row[0] is not None}
        data = [
            {
                "id": r.id,
                "name": r.name,
                "email": r.email,
                "cnpj": r.cnpj or "-",
                "business_sector": r.business_sector or "-",
                "employee_count": str(r.employee_count) if r.employee_count is not None else "-",
                "branch_count": str(r.branch_count) if r.branch_count is not None else "-",
                "annual_revenue": _format_brl_amount(r.annual_revenue),
                "tenant_id": r.tenant_id,
            }
            for r in rows
        ]
        for row in data:
            row["workspace_tenant"] = tenant_lookup.get(str(row["id"]), "-")
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
        if self.user_scope == "cliente" and self.user_client_id.isdigit():
            query = query.filter(ClientModel.id == int(self.user_client_id))
        rows = query.order_by(ClientModel.name.asc()).all()
        session.close()
        return [str(client.id) for client in rows]

    @rx.var(cache=False)
    def client_lookup(self) -> dict[str, str]:
        session = SessionLocal()
        query = session.query(ClientModel)
        if self.user_scope == "cliente" and self.user_client_id.isdigit():
            query = query.filter(ClientModel.id == int(self.user_client_id))
        rows = query.order_by(ClientModel.name.asc()).all()
        session.close()
        return {str(client.id): client.name for client in rows}

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

    @rx.var
    def business_sector_options(self) -> list[str]:
        return ["Industria", "Servicos", "Varejo", "Logistica", "Outro"]

    @rx.var
    def selected_business_sector_label(self) -> str:
        if self.new_client_business_sector == "Outro":
            return self.new_client_custom_business_sector.strip() or "Novo ramo"
        return self.new_client_business_sector

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
            session.query(FormModel)
            .filter(FormModel.tenant_id == self.current_tenant)
            .order_by(FormModel.id.desc())
            .all()
        )
        data = [{"id": r.id, "name": r.name, "category": r.category} for r in rows]
        session.close()
        return data

    @rx.var
    def form_id_options(self) -> list[str]:
        return [str(f["id"]) for f in self.forms_data]

    @rx.var
    def selected_form_name(self) -> str:
        if not self.selected_form_id:
            return ""
        for form in self.forms_data:
            if str(form["id"]) == self.selected_form_id:
                return form["name"]
        return ""

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
                QuestionModel.form_id == int(self.selected_form_id),
            )
            .order_by(QuestionModel.id.desc())
            .all()
        )
        data = [
            {
                "id": r.id,
                "text": r.text,
                "qtype": r.qtype,
                "options": _question_payload(r.options_json)["options"],
                "options_str": ", ".join(_question_payload(r.options_json)["options"]),
                "logic_rule": str(_question_payload(r.options_json)["logic"].get("show_if", "")),
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def form_logic_preview(self) -> list[dict[str, str]]:
        data: list[dict[str, str]] = []
        for item in self.questions_data:
            data.append(
                {
                    "question": item["text"],
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
        return [str(p["id"]) for p in self.projects_data]

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
        return ["cadastro", "clientes"]

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
        principal_role = self.selected_access_principal["role"]
        if principal_role in ROLE_TEMPLATE_CATALOG:
            return principal_role
        if self.perm_selected_role_template in ROLE_TEMPLATE_CATALOG:
            return self.perm_selected_role_template
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
        avg_score = round(sum(s[0] for s in scores) / max(1, len(scores)), 2)
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
            avg = round(sum(r.score for r in responses.all()) / max(1, count), 2)
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

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed

    def toggle_mobile_menu(self):
        self.mobile_menu_open = not self.mobile_menu_open

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode

    def toggle_login_password_visibility(self):
        self.login_password_visible = not self.login_password_visible

    def toggle_first_access_password_visibility(self):
        self.first_access_password_visible = not self.first_access_password_visible

    def toggle_register_password_visibility(self):
        self.register_password_visible = not self.register_password_visible

    def set_active_view(self, view: str):
        self.active_view = view
        self.mobile_menu_open = False

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

    def set_auth_mode(self, mode: str):
        self.auth_mode = mode

    def set_login_email(self, value: str):
        self.login_email = value

    def set_login_password(self, value: str):
        self.login_password = value

    def set_first_access_new_password(self, value: str):
        self.first_access_new_password = value

    def set_first_access_confirm_password(self, value: str):
        self.first_access_confirm_password = value

    def set_register_name(self, value: str):
        self.register_name = value

    def set_register_email(self, value: str):
        self.register_email = value

    def set_register_password(self, value: str):
        self.register_password = value

    def set_global_search_query(self, value: str):
        self.global_search_query = value

    def clear_global_search(self):
        self.global_search_query = ""

    def set_new_client_name(self, value: str):
        self.new_client_name = value

    def set_new_client_email(self, value: str):
        self.new_client_email = value

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
        self.new_client_email = ""
        self.new_client_cnpj = ""
        self.new_client_business_sector = "Industria"
        self.new_client_custom_business_sector = ""
        self.new_client_employee_count = ""
        self.new_client_branch_count = ""
        self.new_client_annual_revenue = ""

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
        self.new_client_email = row.email or ""
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
        row = session.query(FormModel).filter(FormModel.id == form_id, FormModel.tenant_id == self.current_tenant).first()
        session.close()
        if not row:
            self.toast_message = "Formulario nao encontrado"
            self.toast_type = "error"
            return
        self.editing_form_id = str(row.id)
        self.selected_form_id = str(row.id)
        self.new_form_name = row.name or ""
        self.new_form_category = row.category or "Diagnóstico Cultura de Segurança"

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

    def set_new_question_text(self, value: str):
        self.new_question_text = value

    def set_new_question_type(self, value: str):
        self.new_question_type = value

    def set_new_question_options(self, value: str):
        self.new_question_options = value

    def set_new_question_condition(self, value: str):
        self.new_question_condition = value

    def set_ai_prompt(self, value: str):
        self.ai_prompt = value

    def set_new_project_name(self, value: str):
        self.new_project_name = value

    def set_new_project_type(self, value: str):
        self.new_project_type = value

    def select_project(self, value: str):
        self.selected_project_id = value
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

    def open_auth(self):
        self.auth_mode = "login"
        self.auth_open = True

    def close_auth(self):
        if self.force_password_reset_required:
            self.toast_message = "Defina uma nova senha para concluir o primeiro acesso"
            self.toast_type = "error"
            return
        self.auth_open = False

    def login(self):
        session = SessionLocal()
        user = (
            session.query(UserModel)
            .filter(UserModel.email == self.login_email.strip().lower(), UserModel.password == self.login_password)
            .first()
        )
        if not user:
            self.toast_message = "Credenciais inválidas"
            self.toast_type = "error"
            session.close()
            return
        self.is_logged = True
        self.user_role = user.role
        self.user_scope = user.account_scope or "smartlab"
        self.user_client_id = str(user.client_id or "")
        self.assigned_client_ids = [str(item) for item in _loads_json(user.assigned_client_ids, [])]
        self.home_tenant_id = user.tenant_id
        self.current_tenant = user.tenant_id
        self.hydrate_tenant_context()
        self.force_password_reset_required = int(user.must_change_password or 0) == 1
        if self.force_password_reset_required:
            self.auth_open = True
            self.first_access_new_password = ""
            self.first_access_confirm_password = ""
            self.toast_message = "Primeiro acesso detectado. Troque a senha inicial para continuar."
            self.toast_type = "success"
        else:
            self.auth_open = False
            self.toast_message = "Login realizado com sucesso"
            self.toast_type = "success"
        session.close()

    def complete_first_access_password_change(self):
        if not self.first_access_new_password or not self.first_access_confirm_password:
            self.toast_message = "Preencha a nova senha e a confirmacao"
            self.toast_type = "error"
            return
        if self.first_access_new_password != self.first_access_confirm_password:
            self.toast_message = "As senhas nao conferem"
            self.toast_type = "error"
            return
        session = SessionLocal()
        user = session.query(UserModel).filter(UserModel.email == self.login_email.strip().lower()).first()
        if not user:
            self.toast_message = "Usuario nao encontrado para atualizar a senha"
            self.toast_type = "error"
            session.close()
            return
        user.password = self.first_access_new_password
        user.must_change_password = 0
        session.commit()
        session.close()
        self.force_password_reset_required = False
        self.first_access_new_password = ""
        self.first_access_confirm_password = ""
        self.auth_open = False
        self.toast_message = "Senha atualizada com sucesso"
        self.toast_type = "success"

    def register(self):
        if not self.register_name or not self.register_email or not self.register_password:
            self.toast_message = "Preencha os campos de registro"
            self.toast_type = "error"
            return
        session = SessionLocal()
        existing = session.query(UserModel).filter(UserModel.email == self.register_email.strip().lower()).first()
        if existing:
            self.toast_message = "E-mail já cadastrado"
            self.toast_type = "error"
            session.close()
            return
        session.add(
            UserModel(
                name=self.register_name,
                email=self.register_email.strip().lower(),
                password=self.register_password,
                role="viewer",
                tenant_id=self.current_tenant,
            )
        )
        session.commit()
        session.close()
        self.toast_message = "Conta criada. Faça login."
        self.toast_type = "success"
        self.auth_mode = "login"

    def logout(self):
        self.is_logged = False
        self.user_role = "viewer"
        self.user_scope = "smartlab"
        self.user_client_id = ""
        self.assigned_client_ids = []
        self.home_tenant_id = "default"
        self.current_tenant = "default"
        self.force_password_reset_required = False
        self.first_access_new_password = ""
        self.first_access_confirm_password = ""
        self.selected_project_id = ""
        self.active_view = "dashboard"

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
        if self.editing_client_id.isdigit():
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
            client.name = client_name
            client.email = self.new_client_email.strip().lower()
            client.cnpj = self.new_client_cnpj.strip() or None
            client.business_sector = business_sector
            client.employee_count = _parse_int(self.new_client_employee_count)
            client.branch_count = _parse_int(self.new_client_branch_count)
            client.annual_revenue = _parse_brl_amount(self.new_client_annual_revenue)
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
            email=self.new_client_email.strip().lower(),
            cnpj=self.new_client_cnpj.strip() or None,
            business_sector=business_sector,
            employee_count=_parse_int(self.new_client_employee_count),
            branch_count=_parse_int(self.new_client_branch_count),
            annual_revenue=_parse_brl_amount(self.new_client_annual_revenue),
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
            self.toast_message = "Sem permissão para criar formulários"
            self.toast_type = "error"
            return
        if not self.new_form_name:
            self.toast_message = "Informe o nome do formulário"
            self.toast_type = "error"
            return
        session = SessionLocal()
        if self.editing_form_id.isdigit():
            form = (
                session.query(FormModel)
                .filter(FormModel.id == int(self.editing_form_id), FormModel.tenant_id == self.current_tenant)
                .first()
            )
            if not form:
                session.close()
                self.toast_message = "Formulario nao encontrado para edicao"
                self.toast_type = "error"
                return
            form.name = self.new_form_name
            form.category = self.new_form_category
            session.commit()
            selected_form_id = form.id
            session.close()
            self.selected_form_id = str(selected_form_id)
            self.reset_form_builder()
            self.toast_message = "Formulário atualizado"
            self.toast_type = "success"
            return
        form = FormModel(
            tenant_id=self.current_tenant,
            name=self.new_form_name,
            category=self.new_form_category,
        )
        session.add(form)
        session.commit()
        session.refresh(form)
        session.close()
        self.selected_form_id = str(form.id)
        self.reset_form_builder()
        self.toast_message = "Formulário criado"
        self.toast_type = "success"

    def delete_form(self, form_id: int):
        if "delete:forms" not in ROLE_PERMS.get(self.user_role, set()):
            self.toast_message = "Sem permissão para deletar formulários"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = session.query(FormModel).filter(FormModel.id == form_id, FormModel.tenant_id == self.current_tenant).first()
        if row:
            session.delete(row)
            session.commit()
            self.toast_message = "Formulário removido"
            self.toast_type = "success"
            if self.selected_form_id == str(form_id):
                self.selected_form_id = ""
            if self.editing_form_id == str(form_id):
                self.reset_form_builder()
        session.close()

    def select_form(self, value: str):
        self.selected_form_id = value.strip()

    def select_form_by_id(self, form_id: int):
        self.selected_form_id = str(form_id)

    def _resolve_selected_form_id(self) -> int | None:
        raw = (self.selected_form_id or "").strip()
        if raw.isdigit():
            return int(raw)
        session = SessionLocal()
        latest = (
            session.query(FormModel.id)
            .filter(FormModel.tenant_id == self.current_tenant)
            .order_by(FormModel.id.desc())
            .first()
        )
        session.close()
        if latest:
            self.selected_form_id = str(latest[0])
            return int(latest[0])
        return None

    def create_question(self):
        if not self.can_manage_forms:
            self.toast_message = "Sem permissão para editar formulários"
            self.toast_type = "error"
            return
        form_id = self._resolve_selected_form_id()
        if not form_id or not self.new_question_text:
            self.toast_message = "Selecione formulário e preencha pergunta"
            self.toast_type = "error"
            return
        options = [o.strip() for o in self.new_question_options.split(",") if o.strip()]
        if self.new_question_type == "aberta":
            options = []
        session = SessionLocal()
        session.add(
            QuestionModel(
                tenant_id=self.current_tenant,
                form_id=form_id,
                text=self.new_question_text,
                qtype=self.new_question_type,
                options_json=json.dumps(
                    {
                        "options": options,
                        "logic": {"show_if": self.new_question_condition.strip()},
                    }
                ),
            )
        )
        session.commit()
        session.close()
        self.new_question_text = ""
        self.new_question_condition = ""
        self.toast_message = "Pergunta criada"
        self.toast_type = "success"

    def add_mock_response(self, question_id: int, answer: str, score: int = 3):
        form_id = self._resolve_selected_form_id()
        if not form_id:
            return
        session = SessionLocal()
        session.add(
            ResponseModel(
                form_id=form_id,
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
    return rx.button(
        rx.hstack(
            rx.icon(tag=icon, color="var(--nav-icon)", size=18),
            rx.cond(
                State.sidebar_collapsed,
                rx.fragment(),
                rx.text(label, color="var(--nav-text)", font_size="0.96rem", font_weight="500"),
            ),
            width="100%",
            align="center",
            spacing="3",
        ),
        on_click=State.set_active_view(view),
        width="100%",
        justify_content=rx.cond(State.sidebar_collapsed, "center", "flex-start"),
        bg=rx.cond(State.active_view == view, "var(--active-item-bg)", "transparent"),
        border=rx.cond(State.active_view == view, "1px solid var(--active-item-border)", "1px solid transparent"),
        _hover={"bg": "var(--active-item-hover-bg)", "transform": "translateX(1px)"},
        transition="all 0.2s ease",
        border_radius="12px",
        padding="0.7rem",
        class_name="nav-item",
    )


def toast() -> rx.Component:
    return rx.cond(
        State.toast_message != "",
        rx.box(
            rx.hstack(
                rx.icon(
                    tag=rx.cond(State.toast_type == "success", "circle_check", "triangle_alert"),
                    color=rx.cond(State.toast_type == "success", "#22c55e", "#ef4444"),
                ),
                rx.text(State.toast_message, color="var(--text-primary)"),
                rx.spacer(),
                rx.button("Fechar", on_click=State.clear_toast, variant="ghost", color="var(--text-muted)"),
                width="100%",
                align="center",
            ),
            position="fixed",
            bottom="18px",
            right="18px",
            width="380px",
            z_index="999",
            padding="0.9rem",
            **CARD_STYLE,
        ),
        rx.fragment(),
    )


def landing_public() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                smartlab_logo("64px"),
                rx.vstack(
                    rx.heading("SSecur1", color="var(--text-primary)", size="8"),
                    rx.text("Segurança que acontece na prática", color="var(--text-muted)"),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.cond(State.dark_mode, rx.icon(tag="sun", size=16), rx.icon(tag="moon", size=16)),
                    rx.text(State.theme_toggle_label, font_size="0.85rem"),
                    on_click=State.toggle_theme,
                    bg="var(--toggle-btn-bg)",
                    color="var(--toggle-btn-text)",
                    border="1px solid var(--toggle-btn-border)",
                    _hover={"bg": "var(--toggle-btn-hover-bg)"},
                ),
                rx.button(
                    "Entrar",
                    on_click=State.open_auth,
                    class_name="primary-soft-action",
                    _hover={"transform": "scale(1.03)"},
                ),
                width="100%",
            ),
            rx.box(height="20px"),
            rx.hstack(
                rx.vstack(
                    rx.heading(
                        "Segurança que acontece na prática",
                        color="var(--text-primary)",
                        font_size=["2rem", "3rem"],
                        line_height="1.05",
                    ),
                    rx.text(
                        "Vamos juntos transformar cultura de segurança em vantagem competitiva sustentável.",
                        color="var(--text-muted)",
                        font_size="1.1rem",
                    ),
                    rx.hstack(
                        rx.button(
                            "Comece Grátis",
                            on_click=State.open_auth,
                            class_name="primary-soft-action",
                            padding="1.1rem 1.4rem",
                            _hover={"transform": "scale(1.04)"},
                            transition="all 0.2s ease",
                        ),
                        rx.button(
                            "Ver Dashboard",
                            on_click=[State.open_auth],
                            variant="outline",
                            border="1px solid var(--input-border)",
                            color="var(--text-primary)",
                        ),
                    ),
                    align="start",
                    spacing="5",
                    width="100%",
                ),
                rx.box(
                    smartlab_logo("220px"),
                    class_name="pulse-soft",
                    padding="1rem",
                ),
                width="100%",
                gap="8",
                flex_direction="row",
            ),
            rx.grid(
                rx.foreach(
                    [
                        ("Diagnóstico de Cultura", "Mapeie maturidade, comportamentos críticos e variação cultural por unidade."),
                        ("Liderança em Segurança", "Conecte atuação da liderança com resultados em campo e produtividade segura."),
                        ("IA de Recomendação", "Converta dados em recomendações práticas e decisões estratégicas assertivas."),
                    ],
                    lambda item: rx.box(
                        rx.heading(item[0], color="var(--text-primary)", size="5"),
                        rx.text(item[1], color="var(--text-secondary)"),
                        bg="var(--surface-soft)",
                        border="1px solid var(--card-border)",
                        border_radius="16px",
                        padding="1.2rem",
                        backdrop_filter="blur(10px)",
                    ),
                ),
                columns="3",
                spacing="4",
                width="100%",
            ),
            rx.box(
                rx.hstack(
                    rx.button("◀", on_click=State.next_testimonial, variant="soft", color_scheme="purple"),
                    rx.vstack(
                        rx.text(State.current_testimonial["text"], color="var(--text-primary)", font_size="1.1rem"),
                        rx.text(State.current_testimonial["name"], color="var(--accent-strong)"),
                        align="start",
                    ),
                    rx.button("▶", on_click=State.next_testimonial, variant="soft", color_scheme="purple"),
                    width="100%",
                    align="center",
                ),
                width="100%",
                padding="1rem",
                **CARD_STYLE,
            ),
            max_width="1180px",
            width="100%",
            margin="0 auto",
            padding="2rem 1rem 4rem",
            spacing="8",
        ),
        min_height="100vh",
        background="var(--page-bg)",
    )


def app_header() -> rx.Component:
    return rx.hstack(
        rx.hstack(
            smartlab_logo("52px"),
            rx.vstack(
                rx.text("SSecur1", color="var(--text-primary)", font_weight="700"),
                rx.text("Diagnóstico de Segurança", color="var(--text-muted)", font_size="0.8rem"),
                spacing="0",
                align="start",
            ),
            align="center",
            spacing="2",
        ),
        rx.spacer(),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="search", size=16, color="var(--text-muted)"),
                    rx.input(
                        placeholder="Buscar cliente, formulario, usuario, papel...",
                        value=State.global_search_query,
                        on_change=State.set_global_search_query,
                        class_name="header-search-input",
                        bg="transparent",
                        border="0",
                        box_shadow="none",
                        color="var(--text-primary)",
                        width="100%",
                    ),
                    rx.cond(
                        State.global_search_query != "",
                        rx.button(
                            "Limpar",
                            on_click=State.clear_global_search,
                            class_name="header-search-clear",
                        ),
                        rx.fragment(),
                    ),
                    class_name="header-search-shell",
                    width="100%",
                    align="center",
                    spacing="2",
                ),
                rx.cond(
                    State.global_search_query != "",
                    rx.box(
                        rx.cond(
                            State.global_search_results.length() > 0,
                            rx.vstack(
                                rx.foreach(
                                    State.global_search_results,
                                    lambda item: rx.button(
                                        rx.hstack(
                                            rx.badge(item["kind"], color_scheme="gray", variant="soft"),
                                            rx.vstack(
                                                rx.text(item["title"], color="var(--text-primary)", font_weight="600"),
                                                rx.text(item["subtitle"], color="var(--text-muted)", font_size="0.8rem"),
                                                align="start",
                                                spacing="0",
                                                width="100%",
                                            ),
                                            width="100%",
                                            align="center",
                                            spacing="3",
                                        ),
                                        on_click=State.open_search_result(item["view"], item["record_id"]),
                                        class_name="header-search-result",
                                        bg="transparent",
                                        color="var(--text-primary)",
                                        border="1px solid transparent",
                                        width="100%",
                                        justify_content="flex-start",
                                    ),
                                ),
                                width="100%",
                                spacing="1",
                                align="stretch",
                            ),
                            rx.text(
                                "Nenhum resultado encontrado.",
                                color="var(--text-muted)",
                                class_name="header-search-empty",
                            ),
                        ),
                        class_name="header-search-popover",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                spacing="2",
                width="100%",
                align="stretch",
            ),
            width="320px",
            position="relative",
        ),
        rx.cond(
            State.user_scope == "smartlab",
            rx.select(
                State.tenant_display_options,
                value=State.current_tenant_display,
                on_change=State.switch_tenant_from_display,
                color="var(--text-primary)",
                bg="var(--surface-soft)",
                border="1px solid var(--input-border)",
                width="240px",
            ),
            rx.box(
                rx.vstack(
                    rx.text("Tenant Atual", color="var(--text-muted)", font_size="0.72rem"),
                    rx.text(State.current_tenant, color="var(--text-primary)", font_weight="600"),
                    spacing="0",
                    align="start",
                ),
                padding="0.5rem 0.8rem",
                border="1px solid var(--input-border)",
                border_radius="12px",
                bg="var(--surface-soft)",
            ),
        ),
        rx.button(
            rx.cond(State.dark_mode, rx.icon(tag="sun", size=16), rx.icon(tag="moon", size=16)),
            rx.text(State.theme_toggle_short_label, font_size="0.78rem"),
            on_click=State.toggle_theme,
            bg="var(--toggle-btn-bg)",
            color="var(--toggle-btn-text)",
            border="1px solid var(--toggle-btn-border)",
            _hover={"bg": "var(--toggle-btn-hover-bg)"},
        ),
        rx.badge(State.user_role, color_scheme="purple"),
        rx.badge(State.user_scope, color_scheme="orange"),
        rx.button(
            "Sair",
            on_click=State.logout,
            bg="rgba(239,68,68,0.18)",
            color="#fda4af",
            border="1px solid rgba(239,68,68,0.35)",
        ),
        width="100%",
        align="center",
        spacing="3",
        flex_wrap="wrap",
        padding="0.8rem 1rem",
        border_bottom="1px solid var(--card-border)",
        bg="var(--header-bg)",
        backdrop_filter="blur(12px)",
        position="sticky",
        top="0",
        z_index="10",
        class_name="header-bar",
    )


def sidebar() -> rx.Component:
    nav_items = rx.vstack(
        rx.cond(State.show_menu_clients, nav_button("Clientes", "users", "clientes"), rx.fragment()),
        rx.cond(State.show_menu_tenants, nav_button("Tenants", "building_2", "tenants"), rx.fragment()),
        rx.cond(State.show_menu_users, nav_button("Usuários", "users", "usuarios"), rx.fragment()),
        rx.cond(State.show_menu_permissions, nav_button("Permissões", "lock_keyhole", "permissoes"), rx.fragment()),
        rx.cond(State.show_menu_dashboard, nav_button("Dashboard", "layout_dashboard", "dashboard"), rx.fragment()),
        rx.cond(State.show_menu_apis, nav_button("APIs", "plug", "apis"), rx.fragment()),
        rx.cond(State.show_menu_projects, nav_button("Projetos", "file_text", "projetos"), rx.fragment()),
        rx.cond(State.show_menu_plans, nav_button("Plano de Ação", "list_todo", "planos"), rx.fragment()),
        rx.cond(State.show_menu_roles, nav_button("Papéis", "shield_check", "papeis"), rx.fragment()),
        rx.cond(State.show_menu_responsibilities, nav_button("Responsabilidades", "clipboard_list", "responsabilidades"), rx.fragment()),
        rx.cond(State.show_menu_forms, nav_button("Formulários", "file_text", "formularios"), rx.fragment()),
        rx.cond(State.show_menu_ai, nav_button("Assistente IA", "sparkles", "ia"), rx.fragment()),
        width="100%",
        spacing="2",
    )

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.button(
                    rx.icon(tag="panel_left", size=18, color="var(--nav-icon)"),
                    on_click=State.toggle_sidebar,
                    variant="ghost",
                    border="1px solid var(--card-border)",
                ),
                rx.cond(
                    State.sidebar_collapsed,
                    rx.fragment(),
                    rx.text("Navegação", color="var(--text-muted)", font_weight="500"),
                ),
                width="100%",
                justify="between",
            ),
            nav_items,
            spacing="4",
            width="100%",
            align="start",
            padding="0.8rem",
        ),
        width=rx.cond(State.sidebar_collapsed, "72px", "300px"),
        min_height="100dvh",
        height="100dvh",
        max_height="100dvh",
        overflow_y="auto",
        transition="width 0.2s ease",
        background="var(--sidebar-bg)",
        border_right="1px solid var(--card-border)",
        position="sticky",
        top="0",
        align_self="stretch",
        display="block",
        class_name="sidebar-panel",
    )


def metric_card(title: str, value: rx.Var) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(class_name="hexagon"),
            rx.vstack(
                rx.text(title, color="var(--text-muted)"),
                rx.heading(value, color="var(--text-primary)", size="6"),
                align="start",
                spacing="0",
            ),
            align="center",
            spacing="3",
        ),
        padding="1rem",
        _hover={"transform": "scale(1.02)"},
        transition="all 0.2s ease",
        class_name="panel-card metric-card",
        **CARD_STYLE,
    )


def field_block(label: str, control: rx.Component, help_text: str = "") -> rx.Component:
    return rx.vstack(
        rx.text(label, color="var(--text-muted)", font_size="0.78rem", font_weight="600"),
        control,
        rx.cond(
            help_text != "",
            rx.text(help_text, color="var(--text-muted)", font_size="0.76rem"),
            rx.fragment(),
        ),
        spacing="1",
        align="start",
        width="100%",
        class_name="field-block",
    )


def table_text_cell(primary: rx.Component, secondary: rx.Component | None = None) -> rx.Component:
    children = [primary]
    if secondary is not None:
        children.append(secondary)
    return rx.vstack(
        *children,
        spacing="0",
        align="start",
        width="100%",
        class_name="table-cell",
    )


def data_table(headers: list[str], rows: rx.Var, row_builder) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.foreach(
                    headers,
                    lambda h: rx.text(h, color="var(--text-secondary)", font_weight="600", width="100%"),
                ),
                width="100%",
                border_bottom="1px solid rgba(148,163,184,0.18)",
                padding_bottom="0.75rem",
                class_name="data-table-header",
            ),
            rx.cond(
                rows.length() == 0,
                rx.box(
                    rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.9rem"),
                    class_name="data-table-empty",
                ),
                rx.vstack(
                    rx.foreach(
                        rows,
                        lambda row: rx.box(
                            row_builder(row),
                            class_name="data-table-row",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="2",
                ),
            ),
            width="100%",
            spacing="3",
        ),
        width="100%",
        overflow_x="auto",
        class_name="panel-card data-table-card",
        **CARD_STYLE,
        padding="1rem",
    )


def workflow_connection_line(line_type: rx.Var) -> rx.Component:
    return rx.vstack(
        rx.box(
            width="2px",
            height="30px",
            bg=rx.cond(line_type == "ai", "rgba(123,115,154,0.75)", "rgba(255,81,0,0.72)"),
            class_name="workflow-connection-line",
        ),
        rx.badge(rx.cond(line_type == "ai", "AI", "MAIN"), color_scheme=rx.cond(line_type == "ai", "purple", "orange")),
        align="center",
        spacing="1",
        width="100%",
    )


def workflow_node(node_data: dict[str, Any]) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.cond(
                        node_data["box_type"] == "trigger",
                        rx.icon(tag="zap", size=14, color="#f59e0b"),
                        rx.icon(tag="box", size=14, color="var(--text-muted)"),
                    ),
                    rx.text(node_data["title"], color="var(--text-primary)", font_weight="700", font_size="0.84rem"),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.badge(node_data["box_type"], color_scheme=rx.cond(node_data["box_type"] == "trigger", "yellow", "orange")),
                width="100%",
                align="center",
            ),
            rx.hstack(
                rx.box(width="9px", height="9px", border_radius="999px", bg="rgba(255,81,0,0.82)"),
                rx.text(
                    rx.cond(node_data["endpoint"] != "", node_data["endpoint"], "Sem endpoint"),
                    color="var(--text-muted)",
                    font_size="0.72rem",
                ),
                rx.spacer(),
                rx.box(width="9px", height="9px", border_radius="999px", bg="rgba(123,115,154,0.82)"),
                width="100%",
                align="center",
                spacing="2",
            ),
            rx.cond(
                node_data["condition"] != "",
                rx.text(
                    f"Condicao: {node_data['condition']}",
                    color="var(--text-secondary)",
                    font_size="0.72rem",
                ),
                rx.fragment(),
            ),
            rx.cond(
                node_data["output_key"] != "",
                rx.text(
                    f"Saida: {node_data['output_key']}",
                    color="var(--accent-strong)",
                    font_size="0.72rem",
                ),
                rx.fragment(),
            ),
            rx.hstack(
                rx.button("↑", on_click=State.move_workflow_box(node_data["id"], "up"), size="1", variant="ghost"),
                rx.button("↓", on_click=State.move_workflow_box(node_data["id"], "down"), size="1", variant="ghost"),
                rx.button(
                    "Excluir",
                    on_click=State.delete_workflow_box(node_data["id"]),
                    size="1",
                    bg="rgba(239,68,68,0.16)",
                    color="#fca5a5",
                    border="1px solid rgba(239,68,68,0.35)",
                ),
                spacing="2",
            ),
            width="100%",
            spacing="2",
            align="start",
        ),
        class_name="workflow-node",
        width="100%",
        max_width="420px",
    )


def apis_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Camada API-First", color="var(--text-primary)", size="5"),
                rx.text(
                    "Recursos priorizados para integração, embedding e composição low-code do produto.",
                    color="var(--text-muted)",
                ),
                rx.grid(
                    rx.foreach(
                        State.api_catalog,
                        lambda item: rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.badge(item["method"], color_scheme="orange"),
                                    rx.badge(item["kind"], color_scheme="purple"),
                                    rx.spacer(),
                                    width="100%",
                                ),
                                rx.heading(item["name"], size="4", color="var(--text-primary)"),
                                rx.text(item["path"], color="var(--accent-strong)", font_size="0.85rem"),
                                rx.text(item["purpose"], color="var(--text-secondary)", font_size="0.9rem"),
                                align="start",
                                spacing="2",
                                width="100%",
                            ),
                            padding="1rem",
                            class_name="panel-card",
                            **CARD_STYLE,
                        ),
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["Recurso", "Metodo", "Path", "Objetivo", "Classe"],
            State.api_catalog,
            lambda item: rx.hstack(
                rx.text(item["name"], color="var(--text-primary)", width="100%"),
                rx.badge(item["method"], color_scheme="orange", width="fit-content"),
                rx.text(item["path"], color="var(--text-secondary)", width="100%"),
                rx.text(item["purpose"], color="var(--text-secondary)", width="100%"),
                rx.badge(item["kind"], color_scheme="purple", width="fit-content"),
                width="100%",
            ),
        ),
        width="100%",
        spacing="4",
    )


def dashboard_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Caixas do Dashboard", color="var(--text-primary)", size="5"),
                rx.hstack(
                    rx.input(
                        placeholder="Nome da caixa (ex: Alertas de Prazo)",
                        value=State.new_dashboard_box_title,
                        on_change=State.set_new_dashboard_box_title,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.select(
                        ["kpi", "grafico", "lista", "texto"],
                        value=State.new_dashboard_box_kind,
                        on_change=State.set_new_dashboard_box_kind,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                        width="150px",
                    ),
                    rx.select(
                        ["consultor", "cliente"],
                        value=State.new_dashboard_box_scope,
                        on_change=State.set_new_dashboard_box_scope,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                        width="150px",
                    ),
                    rx.button(
                        "Adicionar Caixa",
                        on_click=State.add_dashboard_box,
                        class_name="primary-soft-action",
                    ),
                        width="100%",
                        spacing="3",
                        flex_wrap="wrap",
                ),
                rx.grid(
                    rx.select(
                        ["projetos", "scores", "progresso", "formularios", "respostas", "custom"],
                        value=State.new_dashboard_box_source,
                        on_change=State.set_new_dashboard_box_source,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Descricao funcional da caixa",
                        value=State.new_dashboard_box_description,
                        on_change=State.set_new_dashboard_box_description,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                        width="100%",
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.grid(
                    rx.foreach(
                        State.dashboard_boxes_data,
                        lambda b: rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.heading(b["title"], size="4", color="var(--text-primary)"),
                                    rx.spacer(),
                                    rx.badge(b["kind"], color_scheme="purple"),
                                    spacing="2",
                                    width="100%",
                                    align="center",
                                ),
                                rx.text(f"Fonte: {b['source']}", color="var(--text-muted)", font_size="0.82rem"),
                                rx.text(
                                    rx.cond(
                                        b["description"] != "",
                                        b["description"],
                                        "Sem descricao funcional",
                                    ),
                                    color="var(--text-secondary)",
                                    font_size="0.84rem",
                                ),
                                rx.badge(f"embed: {b['embed']}", color_scheme="orange"),
                                rx.hstack(
                                    rx.button(
                                        "Subir",
                                        on_click=State.move_dashboard_box(b["id"], "up"),
                                        size="1",
                                        variant="ghost",
                                        border="1px solid var(--input-border)",
                                        color="var(--text-secondary)",
                                    ),
                                    rx.button(
                                        "Descer",
                                        on_click=State.move_dashboard_box(b["id"], "down"),
                                        size="1",
                                        variant="ghost",
                                        border="1px solid var(--input-border)",
                                        color="var(--text-secondary)",
                                    ),
                                    spacing="2",
                                ),
                                align="start",
                                spacing="2",
                                width="100%",
                            ),
                            padding="0.9rem",
                            class_name="panel-card",
                            **CARD_STYLE,
                        ),
                    ),
                    columns="3",
                    spacing="3",
                    width="100%",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        ),
        rx.grid(
            metric_card("Clientes", State.dashboard_metrics["clientes"]),
            metric_card("Formulários", State.dashboard_metrics["formularios"]),
            metric_card("Respostas", State.dashboard_metrics["respostas"]),
            metric_card("Média de Segurança", State.dashboard_metrics["media"]),
            columns="4",
            spacing="4",
            width="100%",
        ),
        data_table(
            ["Caixa", "Tipo", "Fonte", "Descricao"],
            State.dashboard_builder_preview,
            lambda item: rx.hstack(
                rx.text(item["title"], color="var(--text-primary)", width="100%"),
                rx.badge(item["kind"], color_scheme="purple", width="fit-content"),
                rx.text(item["source"], color="var(--text-secondary)", width="100%"),
                rx.text(item["description"], color="var(--text-secondary)", width="100%"),
                width="100%",
            ),
        ),
        data_table(
            ["Formulário", "Categoria", "Respostas", "Média", "Status"],
            State.dashboard_table,
            lambda r: rx.hstack(
                rx.text(r["form"], color="var(--text-primary)", width="100%"),
                rx.text(r["categoria"], color="var(--text-secondary)", width="100%"),
                rx.text(r["respostas"], color="var(--text-secondary)", width="100%"),
                rx.text(r["media"], color="#f59e0b", width="100%"),
                rx.badge(
                    r["status"],
                    color_scheme=rx.cond(r["status"] == "Forte", "green", rx.cond(r["status"] == "Crítico", "red", "purple")),
                    width="fit-content",
                ),
                width="100%",
            ),
        ),
        spacing="4",
        width="100%",
    )


def projetos_view() -> rx.Component:
    return rx.vstack(
        rx.cond(
            State.can_configure_projects,
            rx.vstack(
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.heading("Projetos SmartLab - interno", color="var(--text-primary)", size="5"),
                            rx.spacer(),
                            rx.hstack(
                                rx.foreach(
                                    State.project_admin_tabs,
                                    lambda tab: rx.button(
                                        rx.cond(tab == "cadastro", "Cadastro", "Vinculo com Clientes"),
                                        on_click=State.set_project_admin_tab(tab),
                                        bg=rx.cond(
                                            State.project_admin_tab == tab,
                                            "rgba(255,122,47,0.18)",
                                            "transparent",
                                        ),
                                        color=rx.cond(
                                            State.project_admin_tab == tab,
                                            "#fdba74",
                                            "var(--text-secondary)",
                                        ),
                                        border=rx.cond(
                                            State.project_admin_tab == tab,
                                            "1px solid rgba(255,122,47,0.38)",
                                            "1px solid var(--input-border)",
                                        ),
                                        size="2",
                                    ),
                                ),
                                spacing="2",
                            ),
                            width="100%",
                            align="center",
                        ),
                        rx.cond(
                            State.project_admin_tab == "cadastro",
                            rx.vstack(
                                rx.input(
                                    placeholder="Nome do projeto",
                                    value=State.new_project_name,
                                    on_change=State.set_new_project_name,
                                    bg="var(--input-bg)",
                                    color="var(--text-primary)",
                                ),
                                rx.select(
                                    ["Diagnóstico de Cultura", "Trilha de Liderança", "Projeto Especial"],
                                    value=State.new_project_type,
                                    on_change=State.set_new_project_type,
                                    bg="var(--input-bg)",
                                    color="var(--text-primary)",
                                ),
                                rx.button(
                                    "Criar Projeto",
                                    on_click=State.create_project,
                                    bg="rgba(255,122,47,0.18)",
                                    color="#fdba74",
                                    border="1px solid rgba(255,122,47,0.38)",
                                    width="100%",
                                ),
                                rx.select(
                                    State.project_id_options,
                                    value=State.selected_project_id,
                                    on_change=State.select_project,
                                    placeholder="Selecione projeto",
                                    bg="var(--input-bg)",
                                    color="var(--text-primary)",
                                    width="100%",
                                ),
                                align="start",
                                width="100%",
                                spacing="3",
                            ),
                            rx.vstack(
                                rx.select(
                                    State.project_id_options,
                                    value=State.selected_project_id,
                                    on_change=State.select_project,
                                    placeholder="Selecione projeto",
                                    bg="var(--input-bg)",
                                    color="var(--text-primary)",
                                    width="100%",
                                ),
                                field_block(
                                    "Clientes vinculados",
                                    rx.box(
                                        rx.vstack(
                                            rx.button(
                                                rx.hstack(
                                                    rx.text(State.selected_project_link_clients_summary, color="var(--text-primary)"),
                                                    rx.spacer(),
                                                    rx.icon(
                                                        tag=rx.cond(State.new_project_assigned_clients_open, "chevron_up", "chevron_down"),
                                                        size=16,
                                                        color="var(--text-muted)",
                                                    ),
                                                    width="100%",
                                                    align="center",
                                                ),
                                                on_click=State.toggle_new_project_assigned_clients_open,
                                                variant="ghost",
                                                border="1px solid var(--input-border)",
                                                bg="var(--input-bg)",
                                                width="100%",
                                                justify_content="flex-start",
                                            ),
                                            rx.cond(
                                                State.new_project_assigned_clients_open,
                                                rx.foreach(
                                                    State.assignable_client_options,
                                                    lambda client: rx.button(
                                                        rx.hstack(
                                                            rx.badge(
                                                                rx.cond(
                                                                    State.new_project_assigned_client_ids.contains(client["id"]),
                                                                    "Vinculado",
                                                                    "Disponivel",
                                                                ),
                                                                color_scheme=rx.cond(
                                                                    State.new_project_assigned_client_ids.contains(client["id"]),
                                                                    "orange",
                                                                    "gray",
                                                                ),
                                                            ),
                                                            rx.text(f'{client["id"]} - {client["name"]}', color="var(--text-primary)"),
                                                            width="100%",
                                                            align="center",
                                                            spacing="3",
                                                        ),
                                                        on_click=State.toggle_new_project_assigned_client(client["id"]),
                                                        variant="ghost",
                                                        border=rx.cond(
                                                            State.new_project_assigned_client_ids.contains(client["id"]),
                                                            "1px solid rgba(255,122,47,0.38)",
                                                            "1px solid var(--input-border)",
                                                        ),
                                                        bg=rx.cond(
                                                            State.new_project_assigned_client_ids.contains(client["id"]),
                                                            "rgba(255,122,47,0.10)",
                                                            "transparent",
                                                        ),
                                                        width="100%",
                                                        justify_content="flex-start",
                                                    ),
                                                ),
                                                rx.fragment(),
                                            ),
                                            spacing="2",
                                            width="100%",
                                            align="stretch",
                                        ),
                                        width="100%",
                                    ),
                                    "Associe um ou mais clientes aos projetos internos da SmartLab.",
                                ),
                                rx.button(
                                    "Salvar Vinculos",
                                    on_click=State.save_project_client_links,
                                    bg="rgba(255,122,47,0.18)",
                                    color="#fdba74",
                                    border="1px solid rgba(255,122,47,0.38)",
                                    width="100%",
                                ),
                                align="start",
                                width="100%",
                                spacing="3",
                            ),
                        ),
                        width="100%",
                        spacing="3",
                        align="start",
                    ),
                    padding="1rem",
                    **CARD_STYLE,
                ),
                rx.box(
                    rx.vstack(
                        rx.heading("Builder de Workflow (Caixas)", color="var(--text-primary)", size="5"),
                        rx.hstack(
                            rx.input(
                                placeholder="Título da caixa (ex: Visita Técnica)",
                                value=State.new_box_title,
                                on_change=State.set_new_box_title,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                            ),
                            rx.select(
                                ["trigger", "etapa", "coleta", "analise", "relatorio"],
                                value=State.new_box_type,
                                on_change=State.set_new_box_type,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="140px",
                            ),
                            rx.button(
                                "Adicionar Caixa",
                                on_click=State.add_workflow_box,
                                bg="rgba(255,122,47,0.18)",
                                color="#fdba74",
                                border="1px solid rgba(255,122,47,0.38)",
                            ),
                            width="100%",
                            spacing="3",
                            flex_wrap="wrap",
                        ),
                        rx.grid(
                            rx.input(
                                placeholder="String Input: endpoint/URL do node",
                                value=State.new_box_endpoint,
                                on_change=State.set_new_box_endpoint,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.select(
                                ["GET", "POST", "PUT", "DELETE"],
                                value=State.new_box_method,
                                on_change=State.set_new_box_method,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.text_area(
                                placeholder="Collection Input: headers separados por vírgula",
                                value=State.new_box_headers,
                                on_change=State.set_new_box_headers,
                                min_height="84px",
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.select(
                                ["none", "simple", "exponential"],
                                value=State.new_box_retry_policy,
                                on_change=State.set_new_box_retry_policy,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.input(
                                placeholder="Fixed Collection: client_id",
                                value=State.new_box_client_id,
                                on_change=State.set_new_box_client_id,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.input(
                                placeholder="Fixed Collection: client_secret",
                                value=State.new_box_client_secret,
                                on_change=State.set_new_box_client_secret,
                                type="password",
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.input(
                                placeholder="Trigger schedule (cron)",
                                value=State.new_box_schedule,
                                on_change=State.set_new_box_schedule,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.select(
                                ["left", "center", "right"],
                                value=State.new_box_zone,
                                on_change=State.set_new_box_zone,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.input(
                                placeholder="Condicao de execucao (ex: score < 3)",
                                value=State.new_box_condition,
                                on_change=State.set_new_box_condition,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.input(
                                placeholder="Chave de saida (ex: diagnostico.score)",
                                value=State.new_box_output_key,
                                on_change=State.set_new_box_output_key,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            columns="2",
                            spacing="3",
                            width="100%",
                        ),
                        rx.hstack(
                            rx.input(
                                placeholder="Sticky Note no canvas",
                                value=State.new_sticky_note_text,
                                on_change=State.set_new_sticky_note_text,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.button(
                                "Adicionar Sticky Note",
                                on_click=State.add_sticky_note,
                                bg="rgba(255,122,47,0.18)",
                                color="#fdba74",
                                border="1px solid rgba(255,122,47,0.38)",
                            ),
                            width="100%",
                            spacing="3",
                        ),
                        rx.hstack(
                            rx.button(
                                "Execute Workflow",
                                on_click=State.execute_workflow,
                                bg="rgba(255,122,47,0.18)",
                                color="#fdba74",
                                border="1px solid rgba(255,122,47,0.38)",
                            ),
                            rx.button(
                                "Limpar logs",
                                on_click=State.clear_workflow_logs,
                                variant="ghost",
                                border="1px solid var(--input-border)",
                                color="var(--text-secondary)",
                            ),
                            width="100%",
                            spacing="3",
                        ),
                        rx.box(
                            rx.vstack(
                                rx.text("Canvas", color="var(--text-primary)", font_weight="700"),
                                rx.foreach(
                                    State.workflow_canvas_items,
                                    lambda item: rx.vstack(
                                        workflow_node(item),
                                        rx.cond(item["has_next"], workflow_connection_line(item["line_type"]), rx.fragment()),
                                        width="100%",
                                        align="center",
                                        spacing="1",
                                    ),
                                ),
                                width="100%",
                                spacing="1",
                                align="center",
                            ),
                            class_name="workflow-canvas",
                            width="100%",
                        ),
                        rx.box(
                            rx.vstack(
                                rx.text("Sticky Notes", color="var(--text-primary)", font_weight="700"),
                                rx.foreach(
                                    State.workflow_sticky_notes,
                                    lambda note: rx.box(
                                        rx.text(note["note"], color="#4c3f1f", font_size="0.84rem"),
                                        class_name="sticky-note",
                                    ),
                                ),
                                width="100%",
                                spacing="2",
                                align="start",
                            ),
                            width="100%",
                        ),
                        rx.box(
                            rx.vstack(
                                rx.text("Blueprint do fluxo", color="var(--text-primary)", font_weight="700"),
                                rx.foreach(
                                    State.workflow_blueprint,
                                    lambda row: rx.box(
                                        rx.hstack(
                                            rx.text(row["title"], color="var(--text-primary)", width="100%"),
                                            rx.badge(row["type"], color_scheme="purple"),
                                            rx.text(row["condition"], color="var(--text-secondary)", width="100%"),
                                            rx.text(row["output"], color="var(--accent-strong)", width="100%"),
                                            width="100%",
                                            align="center",
                                        ),
                                        width="100%",
                                        padding="0.65rem 0.8rem",
                                        border="1px solid var(--input-border)",
                                        border_radius="12px",
                                        bg="var(--surface-soft)",
                                    ),
                                ),
                                width="100%",
                                spacing="2",
                                align="start",
                            ),
                            class_name="workflow-logs",
                            width="100%",
                        ),
                        rx.box(
                            rx.vstack(
                                rx.text("Logs de execução", color="var(--text-primary)", font_weight="700"),
                                rx.foreach(
                                    State.workflow_logs,
                                    lambda line: rx.text(line, color="var(--text-secondary)", font_size="0.78rem"),
                                ),
                                width="100%",
                                spacing="1",
                                align="start",
                            ),
                            class_name="workflow-logs",
                            width="100%",
                        ),
                        align="start",
                        width="100%",
                        spacing="3",
                    ),
                    padding="1rem",
                    **CARD_STYLE,
                ),
                width="100%",
                spacing="4",
            ),
            rx.box(
                rx.vstack(
                    rx.heading("Acesso restrito", color="var(--text-primary)", size="5"),
                    rx.text(
                        "A tela de Projetos e exclusiva do SmartLab - interno. Outros tenants nao acessam criacao, configuracao ou vinculacao de projetos.",
                        color="var(--text-muted)",
                    ),
                    align="start",
                    width="100%",
                    spacing="3",
                ),
                width="100%",
                padding="1rem",
                **CARD_STYLE,
            ),
        ),
        data_table(
            ["Projeto", "Tipo", "Status", "Progresso", "Clientes Liberados"],
            State.projects_data,
            lambda p: rx.hstack(
                rx.text(p["name"], color="var(--text-primary)", width="100%"),
                rx.text(p["project_type"], color="var(--text-secondary)", width="100%"),
                rx.badge(p["status"], color_scheme="purple", width="fit-content"),
                rx.text(f"{p['progress']}%", color="#f59e0b", width="100%"),
                rx.text(p["assigned_clients"], color="var(--text-secondary)", width="100%"),
                width="100%",
            ),
        ),
        width="100%",
        spacing="4",
    )


def planos_view() -> rx.Component:
    def action_card(action: dict[str, Any]) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.text(action["title"], color="var(--text-primary)", font_weight="600"),
                rx.text(f"Responsável: {action['owner']}", color="var(--text-secondary)", font_size="0.85rem"),
                rx.text(
                    rx.cond(action["due_date"] != "", f"Prazo: {action['due_date']}", "Prazo: -"),
                    color="var(--text-muted)",
                    font_size="0.82rem",
                ),
                rx.text(f"Atingimento: {action['attainment']}%", color="#f59e0b", font_size="0.82rem"),
                rx.hstack(
                    rx.button(
                        "A Fazer",
                        on_click=State.move_action_status(action["id"], "a_fazer"),
                        size="1",
                        variant="ghost",
                        border="1px solid var(--input-border)",
                    ),
                    rx.button(
                        "Andamento",
                        on_click=State.move_action_status(action["id"], "em_andamento"),
                        size="1",
                        variant="ghost",
                        border="1px solid var(--input-border)",
                    ),
                    rx.button(
                        "Concluído",
                        on_click=State.move_action_status(action["id"], "concluido"),
                        size="1",
                        bg="rgba(34,197,94,0.2)",
                        color="#86efac",
                        border="1px solid rgba(34,197,94,0.4)",
                    ),
                    spacing="1",
                ),
                align="start",
                spacing="2",
                width="100%",
            ),
            padding="0.75rem",
            border="1px solid var(--card-border)",
            border_radius="12px",
            bg="var(--surface-soft)",
            width="100%",
        )

    def kanban_col(title: str, items: rx.Var) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(title, color="var(--text-primary)", font_weight="700"),
                    width="100%",
                ),
                rx.foreach(items, action_card),
                width="100%",
                spacing="2",
                align="start",
            ),
            padding="0.8rem",
            width="100%",
            border="1px dashed var(--dropzone-border)",
            border_radius="14px",
            bg="var(--dropzone-bg)",
        )

    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Gestão de Planos de Ação", color="var(--text-primary)", size="5"),
                rx.select(
                    State.project_id_options,
                    value=State.selected_project_id,
                    on_change=State.select_project,
                    placeholder="Selecione projeto",
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                    width="100%",
                ),
                rx.hstack(
                    rx.input(
                        placeholder="Ação",
                        value=State.new_action_title,
                        on_change=State.set_new_action_title,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.input(
                        placeholder="Responsável",
                        value=State.new_action_owner,
                        on_change=State.set_new_action_owner,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.input(
                        placeholder="Prazo (YYYY-MM-DD)",
                        value=State.new_action_due_date,
                        on_change=State.set_new_action_due_date,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    width="100%",
                    spacing="3",
                    flex_wrap="wrap",
                ),
                rx.input(
                    placeholder="Resultado esperado",
                    value=State.new_action_expected_result,
                    on_change=State.set_new_action_expected_result,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                ),
                rx.button(
                    "Criar Ação",
                    on_click=State.create_action_plan,
                    class_name="primary-soft-action",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        ),
        rx.grid(
            kanban_col("A Fazer", State.actions_todo),
            kanban_col("Em Andamento", State.actions_doing),
            kanban_col("Concluído", State.actions_done),
            columns="3",
            spacing="3",
            width="100%",
        ),
        width="100%",
        spacing="4",
    )


def permissoes_view() -> rx.Component:
    def permission_action_button_id(resource_token: str, decision: str) -> str:
        return f"permission-action-{decision}-{resource_token}"

    permission_dnd_script = """
    (() => {
      const version = 'v6-stable';
      if (window.__smartlabPermissionDndVersion === version) {
        return;
      }
      window.__smartlabPermissionDndVersion = version;

      const findInPath = (event, selector) => {
        const path = typeof event.composedPath === 'function' ? event.composedPath() : [];
        for (const node of path) {
          if (node && node instanceof Element && node.matches(selector)) {
            return node;
          }
        }
        const target = event.target;
        if (target && target instanceof Element) {
          return target.closest(selector);
        }
        return null;
      };

      const cleanup = () => {
        document.querySelectorAll('.permission-card.is-dragging').forEach((card) => {
          card.classList.remove('is-dragging');
        });
        document.querySelectorAll('.permission-card.is-drop-commit').forEach((card) => {
          card.classList.remove('is-drop-commit');
        });
        document.querySelectorAll('.permission-lane.is-drop-target').forEach((lane) => {
          lane.classList.remove('is-drop-target');
        });
        window.__smartlabPermissionDrag = null;
      };

      document.addEventListener('dragstart', (event) => {
        const card = findInPath(event, '.permission-card[data-resource]');
        if (!card) {
          return;
        }
        const resource = card.dataset.resource;
        const resourceToken = card.dataset.resourceToken;
        const origin = card.dataset.decision || 'disponivel';
        window.__smartlabPermissionDrag = { resource, resourceToken, origin };
        card.classList.add('is-dragging');
        if (event.dataTransfer) {
          event.dataTransfer.effectAllowed = 'move';
          event.dataTransfer.setData('text/plain', resourceToken || resource || '');
        }
      }, true);

      document.addEventListener('dragend', () => {
        cleanup();
      }, true);

      document.addEventListener('dragover', (event) => {
        const lane = findInPath(event, '.permission-lane[data-lane-decision]');
        if (!lane || !window.__smartlabPermissionDrag) {
          return;
        }
        event.preventDefault();
        if (event.dataTransfer) {
          event.dataTransfer.dropEffect = 'move';
        }
      }, true);

      document.addEventListener('dragenter', (event) => {
        const lane = findInPath(event, '.permission-lane[data-lane-decision]');
        if (!lane || !window.__smartlabPermissionDrag) {
          return;
        }
        lane.classList.add('is-drop-target');
      }, true);

      document.addEventListener('dragleave', (event) => {
        const lane = findInPath(event, '.permission-lane[data-lane-decision]');
        if (!lane) {
          return;
        }
        const related = event.relatedTarget;
        if (related && lane.contains(related)) {
          return;
        }
        lane.classList.remove('is-drop-target');
      }, true);

      document.addEventListener('drop', (event) => {
        const lane = findInPath(event, '.permission-lane[data-lane-decision]');
        const drag = window.__smartlabPermissionDrag;
        if (!lane || !drag) {
          cleanup();
          return;
        }
        event.preventDefault();
        const decision = lane.dataset.laneDecision || 'disponivel';
        lane.classList.remove('is-drop-target');
        if (decision === drag.origin) {
          cleanup();
          return;
        }
        const actionButton = document.getElementById(`permission-action-${decision}-${drag.resourceToken}`);
        if (actionButton) {
          actionButton.click();
          const card = document.querySelector(`.permission-card[data-resource-token="${drag.resourceToken}"]`);
          if (card) {
            card.classList.add('is-drop-commit');
            window.setTimeout(() => card.classList.remove('is-drop-commit'), 260);
          }
        }
        cleanup();
      }, true);
    })();
    """

    def permission_resource_card(item: dict[str, Any], current_decision: str) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.badge(item["module"], color_scheme="purple"),
                    rx.badge(item["action"], color_scheme="orange"),
                    rx.spacer(),
                    width="100%",
                ),
                rx.heading(item["label"], size="3", color="var(--text-primary)"),
                rx.text(item["description"], color="var(--text-secondary)", font_size="0.84rem"),
                rx.badge(
                    rx.cond(
                        current_decision == "permitido",
                        "Liberado",
                        rx.cond(current_decision == "negado", "Bloqueado", "Disponivel para decisao"),
                    ),
                    color_scheme=rx.cond(
                        current_decision == "permitido",
                        "green",
                        rx.cond(current_decision == "negado", "red", "gray"),
                    ),
                ),
                rx.hstack(
                    rx.cond(
                        current_decision != "permitido",
                        rx.button(
                            "Permitir",
                            on_click=State.apply_permission_from_catalog(item["resource"], "permitido"),
                            id=permission_action_button_id(item["resource_token"], "permitido"),
                            class_name="permission-card-action",
                            size="1",
                            bg="rgba(34,197,94,0.18)",
                            color="#15803d",
                            border="1px solid rgba(34,197,94,0.32)",
                            custom_attrs={
                                "data-resource-token": item["resource_token"],
                                "data-action-decision": "permitido",
                            },
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        current_decision != "negado",
                        rx.button(
                            "Negar",
                            on_click=State.apply_permission_from_catalog(item["resource"], "negado"),
                            id=permission_action_button_id(item["resource_token"], "negado"),
                            class_name="permission-card-action",
                            size="1",
                            bg="rgba(239,68,68,0.16)",
                            color="#b91c1c",
                            border="1px solid rgba(239,68,68,0.28)",
                            custom_attrs={
                                "data-resource-token": item["resource_token"],
                                "data-action-decision": "negado",
                            },
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        current_decision != "disponivel",
                        rx.button(
                            "Limpar",
                            on_click=State.clear_permission_from_catalog(item["resource"]),
                            id=permission_action_button_id(item["resource_token"], "disponivel"),
                            class_name="permission-card-action",
                            size="1",
                            variant="ghost",
                            border="1px solid var(--input-border)",
                            color="var(--text-secondary)",
                            custom_attrs={
                                "data-resource-token": item["resource_token"],
                                "data-action-decision": "disponivel",
                            },
                        ),
                        rx.fragment(),
                    ),
                    width="100%",
                    spacing="2",
                    flex_wrap="wrap",
                ),
                align="start",
                spacing="2",
                width="100%",
            ),
            class_name="permission-card panel-card",
            draggable=True,
            transition="all 0.18s ease",
            _hover={
                "transform": "translateY(-6px)",
                "box_shadow": "0 26px 42px rgba(17, 24, 39, 0.22)",
                "border_color": "rgba(255, 122, 47, 0.58)",
                "background": "linear-gradient(180deg, rgba(255, 122, 47, 0.10), rgba(123, 115, 154, 0.08)), var(--card-bg)",
            },
            custom_attrs={
                "data-resource": item["resource"],
                "data-resource-token": item["resource_token"],
                "data-decision": current_decision,
            },
        )

    def permission_lane(title: str, tone: str, items: rx.Var) -> rx.Component:
        tone_bg = {
            "neutral": "rgba(148,163,184,0.10)",
            "success": "rgba(34,197,94,0.10)",
            "danger": "rgba(239,68,68,0.08)",
        }[tone]
        tone_border = {
            "neutral": "rgba(148,163,184,0.22)",
            "success": "rgba(34,197,94,0.28)",
            "danger": "rgba(239,68,68,0.24)",
        }[tone]
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(title, color="var(--text-primary)", font_weight="700"),
                    width="100%",
                    align="center",
                ),
                rx.foreach(
                    items,
                    lambda item: permission_resource_card(
                        item,
                        "permitido" if title == "Permitido" else "negado" if title == "Negado" else "disponivel",
                    ),
                ),
                rx.cond(
                    items.length() == 0,
                    rx.text("Nenhum item nesta coluna.", color="var(--text-muted)", font_size="0.84rem"),
                    rx.fragment(),
                ),
                width="100%",
                spacing="3",
                align="stretch",
            ),
            class_name="permission-lane",
            width="100%",
            background=tone_bg,
            border=f"1px dashed {tone_border}",
            custom_attrs={
                "data-lane-decision": (
                    "permitido" if title == "Permitido" else "negado" if title == "Negado" else "disponivel"
                )
            },
        )

    return rx.vstack(
        rx.script(permission_dnd_script, id="permission-dnd-script"),
        rx.box(
            rx.vstack(
                rx.heading("RBAC e Permissões por Cliente", color="var(--text-primary)", size="5"),
                rx.text(
                    "Defina acessos por usuario com base em papel, modulo e recursos liberados. Esta tela sera a base do portal do cliente.",
                    color="var(--text-muted)",
                    font_size="0.9rem",
                ),
                rx.grid(
                    metric_card("Catalogo", State.permission_summary["catalogo"]),
                    metric_card("Permitidos", State.permission_summary["permitidos"]),
                    metric_card("Negados", State.permission_summary["negados"]),
                    metric_card("Pendentes", State.permission_summary["pendentes"]),
                    columns="4",
                    spacing="3",
                    width="100%",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            padding="1rem",
            **CARD_STYLE,
        ),
        rx.grid(
            rx.box(
                rx.vstack(
                    rx.heading("Contexto de acesso", color="var(--text-primary)", size="4"),
                    field_block(
                        "Usuario",
                        rx.select(
                            State.access_principal_options,
                            value=State.perm_user_email,
                            on_change=State.set_perm_user_email,
                            placeholder="Selecione um usuario existente",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        "As permissoes se aplicam a uma conta ja criada.",
                    ),
                    field_block(
                        "Template de referencia",
                        rx.select(
                            State.role_template_options,
                            value=State.perm_selected_role_template,
                            on_change=State.set_perm_selected_role_template,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Modulo",
                        rx.select(
                            State.permission_module_options,
                            value=State.perm_selected_module,
                            on_change=State.set_perm_selected_module,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.text(
                        "Permissoes sao configuradas apenas sobre contas ja existentes. Crie ou ajuste o usuario no menu Usuarios.",
                        color="var(--text-muted)",
                        font_size="0.82rem",
                    ),
                    align="start",
                    spacing="3",
                    width="100%",
                ),
                padding="1rem",
                **CARD_STYLE,
            ),
            rx.box(
                rx.vstack(
                    rx.heading("Template RBAC", color="var(--text-primary)", size="4"),
                    rx.badge(State.selected_role_template_data["label"], color_scheme="purple"),
                    rx.text(State.selected_role_template_data["description"], color="var(--text-secondary)"),
                    rx.hstack(
                        rx.text("Escopo:", color="var(--text-muted)", font_size="0.85rem"),
                        rx.text(State.selected_role_template_data["scope"], color="var(--text-muted)", font_size="0.85rem"),
                        spacing="2",
                    ),
                    rx.box(
                        rx.text(State.selected_role_template_data["permissions_str"], color="var(--text-secondary)"),
                        class_name="permission-template-box",
                    ),
                    align="start",
                    spacing="3",
                    width="100%",
                ),
                padding="1rem",
                **CARD_STYLE,
            ),
            rx.box(
                rx.vstack(
                    rx.heading("Usuario selecionado", color="var(--text-primary)", size="4"),
                    rx.text(State.selected_access_principal["name"], color="var(--text-primary)", font_weight="700"),
                    rx.text(State.selected_access_principal["email"], color="var(--text-secondary)"),
                    rx.hstack(
                        rx.badge(State.selected_access_principal["role"], color_scheme="purple"),
                        rx.badge(State.selected_access_principal["scope"], color_scheme="orange"),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text("Tenant:", color="var(--text-muted)", font_size="0.84rem"),
                        rx.text(State.selected_access_principal["tenant"], color="var(--text-muted)", font_size="0.84rem"),
                        spacing="2",
                    ),
                    rx.cond(
                        State.selected_access_principal["client"] != "-",
                        rx.hstack(
                            rx.text("Cliente:", color="var(--text-muted)", font_size="0.84rem"),
                            rx.text(State.selected_access_principal["client"], color="var(--text-muted)", font_size="0.84rem"),
                            spacing="2",
                        ),
                        rx.text("Conta interna SmartLab", color="var(--text-muted)", font_size="0.84rem"),
                    ),
                    align="start",
                    spacing="2",
                    width="100%",
                ),
                padding="1rem",
                **CARD_STYLE,
            ),
            columns="3",
            spacing="4",
            width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading("Canvas de Acessos", color="var(--text-primary)", size="5"),
                    rx.spacer(),
                    rx.text(
                        "Arraste os cards entre Disponivel, Permitido e Negado. Os botoes continuam como fallback operacional.",
                        color="var(--text-muted)",
                        font_size="0.9rem",
                    ),
                    width="100%",
                ),
                rx.grid(
                    permission_lane("Disponivel", "neutral", State.permission_canvas_available),
                    permission_lane("Permitido", "success", State.permission_canvas_allowed),
                    permission_lane("Negado", "danger", State.permission_canvas_denied),
                    columns="3",
                    spacing="4",
                    width="100%",
                ),
                width="100%",
                spacing="3",
                align="start",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        rx.cond(
            State.perm_user_email != "",
            data_table(
                ["Papel", "Escopo", "Descricao", "Permissoes base"],
                State.role_templates_data,
                lambda row: rx.hstack(
                    rx.text(row["label"], color="var(--text-primary)", width="100%"),
                    rx.badge(row["scope"], color_scheme="orange", width="fit-content"),
                    rx.text(row["description"], color="var(--text-secondary)", width="100%"),
                    rx.text(row["permissions_str"], color="var(--text-secondary)", width="100%"),
                    width="100%",
                ),
            ),
            rx.box(
                rx.text(
                    "Selecione um usuario para visualizar o template RBAC e as permissoes base aplicaveis.",
                    color="var(--text-muted)",
                ),
                width="100%",
                padding="1rem",
                class_name="panel-card data-table-card permission-empty-state",
                **CARD_STYLE,
            ),
        ),
        rx.cond(
            State.perm_user_email != "",
            data_table(
                ["Usuário", "Recurso", "Decisão", "Ações"],
                State.permission_boxes_data,
                lambda p: rx.hstack(
                    table_text_cell(
                        rx.text(p["user_email"], color="var(--text-primary)", font_weight="600"),
                    ),
                    table_text_cell(
                        rx.text(p["resource"], color="var(--text-secondary)"),
                    ),
                    table_text_cell(
                        rx.badge(
                            p["decision"],
                            color_scheme=rx.cond(p["decision"] == "permitido", "green", "red"),
                            width="fit-content",
                        ),
                    ),
                    rx.button(
                        "Remover",
                        on_click=State.delete_permission_box(p["id"]),
                        variant="ghost",
                        border="1px solid var(--input-border)",
                        color="var(--text-secondary)",
                        size="2",
                    ),
                    width="100%",
                    align="center",
                ),
            ),
            rx.box(
                rx.text(
                    "Selecione um usuario para visualizar as permissoes aplicadas e o historico do canvas.",
                    color="var(--text-muted)",
                ),
                width="100%",
                padding="1rem",
                class_name="panel-card data-table-card permission-empty-state",
                **CARD_STYLE,
            ),
        ),
        width="100%",
        spacing="4",
    )


def clientes_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Clientes", color="var(--text-primary)", size="5"),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.badge("Passo 1: Cliente", color_scheme="orange"),
                    width="100%",
                    align="center",
                ),
                rx.hstack(
                    field_block(
                        "Nome do cliente",
                        rx.input(
                            placeholder="Nome do cliente",
                            value=State.new_client_name,
                            on_change=State.set_new_client_name,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "CNPJ",
                        rx.input(
                            placeholder="00.000.000/0000-00",
                            value=State.new_client_cnpj,
                            on_change=State.set_new_client_cnpj,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "E-mail principal",
                        rx.input(
                            placeholder="Email principal",
                            value=State.new_client_email,
                            on_change=State.set_new_client_email,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="3",
                    flex_direction="row",
                ),
                rx.hstack(
                    field_block(
                        "Ramo de atividade",
                        rx.select(
                            State.business_sector_options,
                            value=State.new_client_business_sector,
                            on_change=State.set_new_client_business_sector,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        "Escolha um ramo padrao ou selecione 'Outro' para cadastrar um novo.",
                    ),
                    rx.cond(
                        State.new_client_business_sector == "Outro",
                        field_block(
                            "Novo ramo",
                            rx.input(
                                placeholder="Informe o ramo de atividade",
                                value=State.new_client_custom_business_sector,
                                on_change=State.set_new_client_custom_business_sector,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                        ),
                        field_block(
                            "Ramo selecionado",
                            rx.input(
                                value=State.selected_business_sector_label,
                                read_only=True,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                        ),
                    ),
                    field_block(
                        "Quantidade de colaboradores",
                        rx.input(
                            placeholder="Ex.: 250",
                            value=State.new_client_employee_count,
                            on_change=State.set_new_client_employee_count,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="3",
                    flex_direction="row",
                ),
                rx.hstack(
                    field_block(
                        "Total de filiais",
                        rx.input(
                            placeholder="Ex.: 12",
                            value=State.new_client_branch_count,
                            on_change=State.set_new_client_branch_count,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Faturamento anual em R$",
                        rx.input(
                            placeholder="Ex.: 1500000,00",
                            value=State.new_client_annual_revenue,
                            on_change=State.set_new_client_annual_revenue,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="3",
                    flex_direction="row",
                ),
                rx.cond(
                    State.can_manage_clients,
                    rx.hstack(
                        rx.button(
                            State.client_submit_label,
                            on_click=State.create_client,
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                        ),
                        rx.cond(
                            State.is_editing_client,
                            rx.button(
                                "Cancelar",
                                on_click=State.reset_client_form,
                                variant="ghost",
                                border="1px solid var(--input-border)",
                                color="var(--text-secondary)",
                            ),
                            rx.fragment(),
                        ),
                        width="100%",
                        justify="start",
                        align="center",
                        spacing="2",
                    ),
                    rx.badge("Viewer: somente leitura", color_scheme="purple"),
                ),
                rx.box(
                    rx.text(
                        "Ao cadastrar o cliente, o sistema cria automaticamente um workspace isolado para ele. A tela de Tenants fica reservada para administracao avancada.",
                        color="var(--text-muted)",
                        font_size="0.84rem",
                    ),
                    class_name="workspace-guide",
                    width="100%",
                ),
                width="100%",
                spacing="3",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["ID", "Cliente", "CNPJ", "E-mail", "Ramo", "Colaboradores", "Filiais", "Faturamento", "Tenant / Workspace", "Ações"],
            State.clients_data,
            lambda c: rx.hstack(
                table_text_cell(
                    rx.text(c["id"], color="var(--text-primary)", font_weight="600"),
                ),
                table_text_cell(
                    rx.text(c["name"], color="var(--text-primary)", font_weight="600"),
                ),
                table_text_cell(
                    rx.text(c["cnpj"], color="var(--text-secondary)"),
                ),
                table_text_cell(
                    rx.text(c["email"], color="var(--text-secondary)"),
                ),
                table_text_cell(
                    rx.badge(c["business_sector"], color_scheme="orange", width="fit-content"),
                ),
                table_text_cell(
                    rx.text(c["employee_count"], color="var(--text-secondary)"),
                ),
                table_text_cell(
                    rx.text(c["branch_count"], color="var(--text-secondary)"),
                ),
                table_text_cell(
                    rx.text(c["annual_revenue"], color="var(--text-secondary)"),
                ),
                table_text_cell(
                    rx.badge(c["tenant_id"], color_scheme="purple", width="fit-content"),
                    rx.badge(c["workspace_tenant"], color_scheme="orange", width="fit-content"),
                ),
                rx.hstack(
                    rx.cond(
                        State.can_manage_clients,
                        rx.button(
                            "Alterar",
                            on_click=State.start_edit_client(c["id"]),
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        State.can_delete_clients,
                        rx.button(
                            "Excluir",
                            on_click=State.delete_client(c["id"]),
                            bg="rgba(239,68,68,0.2)",
                            color="#fca5a5",
                            border="1px solid rgba(239,68,68,0.4)",
                            size="2",
                        ),
                        rx.text("-", color="#64748b"),
                    ),
                    spacing="2",
                ),
                width="100%",
                align="center",
            ),
        ),
        spacing="4",
        width="100%",
    )


def usuarios_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Gestao de Usuarios", color="var(--text-primary)", size="5"),
                        rx.text(
                            "Crie contas internas SmartLab ou contas de cliente vinculadas ao workspace correto.",
                            color="var(--text-muted)",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.badge("Passo 3: Colaboradores", color_scheme="orange"),
                    width="100%",
                    align="center",
                ),
                rx.grid(
                    field_block(
                        "Nome completo",
                        rx.input(
                            placeholder="Nome completo",
                            value=State.new_user_name,
                            on_change=State.set_new_user_name,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "E-mail",
                        rx.input(
                            placeholder="usuario@empresa.com",
                            value=State.new_user_email,
                            on_change=State.set_new_user_email,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Senha inicial",
                        rx.input(
                            placeholder="Senha local inicial",
                            value=State.new_user_password,
                            on_change=State.set_new_user_password,
                            type="password",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        State.user_password_help_text,
                    ),
                    field_block(
                        "Papel",
                        rx.select(
                            State.user_role_options,
                            value=State.new_user_role,
                            on_change=State.set_new_user_role,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Escopo da conta",
                        rx.select(
                            State.user_scope_options,
                            value=State.new_user_scope,
                            on_change=State.set_new_user_scope,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        "Define se a conta e interna SmartLab ou se pertence ao cliente.",
                    ),
                    rx.cond(
                        State.new_user_scope == "cliente",
                        field_block(
                            "Cliente vinculado",
                            rx.select(
                                State.client_display_options,
                                value=State.selected_new_user_client_option,
                                on_change=State.set_new_user_client_option,
                                placeholder="Cliente vinculado",
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            "Obrigatorio para contas de cliente.",
                        ),
                        field_block(
                            "Clientes autorizados",
                            rx.box(
                                rx.vstack(
                                    rx.button(
                                        rx.hstack(
                                            rx.text(State.selected_assigned_clients_summary, color="var(--text-primary)"),
                                            rx.spacer(),
                                            rx.icon(
                                                tag=rx.cond(State.new_user_assigned_clients_open, "chevron_up", "chevron_down"),
                                                size=16,
                                                color="var(--text-muted)",
                                            ),
                                            width="100%",
                                            align="center",
                                        ),
                                        on_click=State.toggle_new_user_assigned_clients_open,
                                        variant="ghost",
                                        border="1px solid var(--input-border)",
                                        bg="var(--input-bg)",
                                        width="100%",
                                        justify_content="flex-start",
                                    ),
                                    rx.cond(
                                        State.new_user_assigned_clients_open,
                                        rx.foreach(
                                            State.assignable_client_options,
                                            lambda client: rx.button(
                                                rx.hstack(
                                                    rx.badge(
                                                        rx.cond(
                                                            State.new_user_assigned_client_ids.contains(client["id"]),
                                                            "Autorizado",
                                                            "Disponivel",
                                                        ),
                                                        color_scheme=rx.cond(
                                                            State.new_user_assigned_client_ids.contains(client["id"]),
                                                            "orange",
                                                            "gray",
                                                        ),
                                                    ),
                                                    rx.text(f'{client["id"]} - {client["name"]}', color="var(--text-primary)"),
                                                    width="100%",
                                                    align="center",
                                                    spacing="3",
                                                ),
                                                on_click=State.toggle_new_user_assigned_client(client["id"]),
                                                variant="ghost",
                                                border=rx.cond(
                                                    State.new_user_assigned_client_ids.contains(client["id"]),
                                                    "1px solid rgba(255,122,47,0.38)",
                                                    "1px solid var(--input-border)",
                                                ),
                                                bg=rx.cond(
                                                    State.new_user_assigned_client_ids.contains(client["id"]),
                                                    "rgba(255,122,47,0.10)",
                                                    "transparent",
                                                ),
                                                width="100%",
                                                justify_content="flex-start",
                                            ),
                                        ),
                                        rx.fragment(),
                                    ),
                                    spacing="2",
                                    width="100%",
                                    align="stretch",
                                ),
                                width="100%",
                            ),
                            "Selecione apenas os clientes que este consultor pode operar.",
                        ),
                    ),
                    rx.cond(
                        State.new_user_scope == "cliente",
                        field_block(
                            "Workspace do usuario",
                            rx.select(
                                State.user_workspace_options,
                                value=State.selected_new_user_workspace_option,
                                on_change=State.set_new_user_workspace_option,
                                placeholder="Workspace do usuario",
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            "Workspace e o ambiente isolado onde esse usuario vai operar.",
                        ),
                        field_block(
                            "Workspace base",
                            rx.input(
                                value="default - SmartLab",
                                read_only=True,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            "Usuarios SmartLab nascem no workspace interno e acessam apenas os clientes autorizados.",
                        ),
                    ),
                    field_block(
                        "Profissao",
                        rx.select(
                            State.profession_options,
                            value=State.new_user_profession,
                            on_change=State.set_new_user_profession,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.cond(
                        State.new_user_profession == "Outro",
                        field_block(
                            "Nova profissao",
                            rx.input(
                                placeholder="Informe a profissao",
                                value=State.new_user_custom_profession,
                                on_change=State.set_new_user_custom_profession,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                        ),
                        rx.fragment(),
                    ),
                    field_block(
                        "Departamento",
                        rx.select(
                            State.department_options,
                            value=State.new_user_department,
                            on_change=State.set_new_user_department,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "A quem se reporta",
                        rx.select(
                            State.reporting_user_options,
                            value=State.selected_reporting_user_option,
                            on_change=State.set_new_user_reports_to_user_option,
                            placeholder="Selecione a hierarquia",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.cond(
                        State.new_user_department == "Outro",
                        field_block(
                            "Novo departamento",
                            rx.input(
                                placeholder="Informe o departamento",
                                value=State.new_user_custom_department,
                                on_change=State.set_new_user_custom_department,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                        ),
                        rx.fragment(),
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.hstack(
                    rx.cond(
                        State.can_manage_users,
                        rx.hstack(
                            rx.button(
                                State.user_submit_label,
                                on_click=State.create_user,
                                bg="rgba(255,122,47,0.18)",
                                color="#fdba74",
                                border="1px solid rgba(255,122,47,0.38)",
                            ),
                            rx.cond(
                                State.is_editing_user,
                                rx.button(
                                    "Cancelar",
                                    on_click=State.reset_user_form,
                                    variant="ghost",
                                    border="1px solid var(--input-border)",
                                    color="var(--text-secondary)",
                                ),
                                rx.fragment(),
                            ),
                        ),
                        rx.badge("Sem permissao para criar usuarios", color_scheme="red"),
                    ),
                    rx.spacer(),
                    rx.text(
                        "Na proxima fase, cliente_admin podera criar usuarios limitados do proprio tenant.",
                        color="var(--text-muted)",
                        font_size="0.84rem",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.box(
                    rx.text(
                        "Regra: colaborador de cliente precisa apontar para o cliente e para o tenant daquele mesmo cliente. Colaborador SmartLab pode operar varios clientes conforme o papel.",
                        color="var(--text-muted)",
                        font_size="0.84rem",
                    ),
                    class_name="auth-note",
                    width="100%",
                ),
                width="100%",
                spacing="3",
                align="start",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["Nome", "Acesso", "Organizacao", "Workspace", "Acoes"],
            State.users_data,
            lambda u: rx.hstack(
                table_text_cell(
                    rx.text(u["name"], color="var(--text-primary)", font_weight="600"),
                    rx.text(u["email"], color="var(--text-secondary)"),
                ),
                table_text_cell(
                    rx.hstack(
                        rx.badge(u["role"], color_scheme="purple", width="fit-content"),
                        rx.badge(
                            u["account_scope"],
                            color_scheme=rx.cond(u["account_scope"] == "smartlab", "orange", "green"),
                            width="fit-content",
                        ),
                        spacing="2",
                    ),
                    rx.text(f'Senha inicial: {u["must_change_password"]}', color="var(--text-muted)", font_size="0.78rem"),
                ),
                table_text_cell(
                    rx.text(f'{u["profession"]} • {u["department"]}', color="var(--text-secondary)"),
                    rx.cond(
                        u["account_scope"] == "smartlab",
                        rx.text(f'Clientes autorizados: {u["assigned_clients"]}', color="var(--text-muted)", font_size="0.78rem"),
                        rx.cond(
                            u["reports_to_user_name"] != "-",
                            rx.text(f'Reporta para: {u["reports_to_user_name"]}', color="var(--text-muted)", font_size="0.78rem"),
                            rx.fragment(),
                        ),
                    ),
                ),
                table_text_cell(
                    rx.text(u["tenant_id"], color="var(--text-secondary)"),
                    rx.cond(
                        u["client_name"] != "-",
                        rx.text(u["client_name"], color="var(--text-muted)", font_size="0.78rem"),
                        rx.fragment(),
                    ),
                ),
                rx.hstack(
                    rx.cond(
                        State.can_manage_users,
                        rx.button(
                            "Alterar",
                            on_click=State.start_edit_user(u["id"]),
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        State.can_delete_users,
                        rx.button(
                            "Excluir",
                            on_click=State.delete_user(u["id"]),
                            bg="rgba(239,68,68,0.2)",
                            color="#fca5a5",
                            border="1px solid rgba(239,68,68,0.4)",
                            size="2",
                        ),
                        rx.text("-", color="#64748b"),
                    ),
                    spacing="2",
                ),
                width="100%",
                align="center",
            ),
        ),
        width="100%",
        spacing="4",
    )


def tenants_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Tenants", color="var(--text-primary)", size="5"),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.badge("Admin avancado", color_scheme="purple"),
                    width="100%",
                    align="center",
                ),
                rx.grid(
                    field_block(
                        "Nome Tenant",
                        rx.input(
                            placeholder="Nome Tenant",
                            value=State.new_tenant_name,
                            on_change=State.set_new_tenant_name,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Slug (url)",
                        rx.input(
                            placeholder="slug-url",
                            value=State.new_tenant_slug,
                            on_change=State.set_new_tenant_slug,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Limite Usuários",
                        rx.input(
                            placeholder="Total Usuarios",
                            value=State.new_tenant_limit,
                            on_change=State.set_new_tenant_limit,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Cliente Vinculo",
                        rx.select(
                            State.client_display_options,
                            value=State.selected_new_tenant_client_option,
                            on_change=State.set_new_tenant_client_option,
                            placeholder="Cliente Vinculo",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.hstack(
                    rx.cond(
                        State.can_manage_tenants,
                        rx.hstack(
                            rx.button(
                                State.tenant_submit_label,
                                on_click=State.create_tenant,
                                bg="rgba(255,122,47,0.18)",
                                color="#fdba74",
                                border="1px solid rgba(255,122,47,0.38)",
                            ),
                            rx.cond(
                                State.is_editing_tenant,
                                rx.button(
                                    "Cancelar",
                                    on_click=State.reset_tenant_form,
                                    variant="ghost",
                                    border="1px solid var(--input-border)",
                                    color="var(--text-secondary)",
                                ),
                                rx.fragment(),
                            ),
                        ),
                        rx.badge("Sem permissão", color_scheme="red"),
                    ),
                    rx.spacer(),
                    rx.text("Cadastre o tenant apos o cliente e antes dos usuarios do cliente.", color="var(--text-muted)", font_size="0.84rem"),
                    width="100%",
                    align="center",
                ),
                rx.box(
                    rx.text(
                        "Use esta tela somente quando precisar intervir manualmente no isolamento tecnico. No fluxo normal, o tenant nasce junto com o cliente.",
                        color="var(--text-muted)",
                        font_size="0.84rem",
                    ),
                    class_name="workspace-guide",
                    width="100%",
                ),
                width="100%",
                spacing="3",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        ),
        data_table(
            ["ID", "Nome", "Slug", "Cliente", "Limite", "Ações"],
            State.tenants_data,
            lambda t: rx.hstack(
                table_text_cell(
                    rx.text(t["id"], color="var(--text-primary)", font_weight="600"),
                    rx.text(f'ID do cliente: {t["owner_client_id"]}', color="var(--text-muted)", font_size="0.78rem"),
                ),
                table_text_cell(rx.text(t["name"], color="var(--text-primary)", font_weight="600")),
                table_text_cell(rx.text(t["slug"], color="var(--text-secondary)")),
                table_text_cell(
                    rx.text(t["owner_client_name"], color="var(--text-secondary)"),
                    rx.text(f'CNPJ: {t["owner_client_cnpj"]}', color="var(--text-muted)", font_size="0.78rem"),
                ),
                table_text_cell(rx.text(t["limit"], color="#f59e0b")),
                rx.hstack(
                    rx.cond(
                        State.can_manage_tenants,
                        rx.button(
                            "Alterar",
                            on_click=State.start_edit_tenant(t["id"]),
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        State.can_delete_tenants,
                        rx.button(
                            "Excluir",
                            on_click=State.delete_tenant(t["id"]),
                            bg="rgba(239,68,68,0.2)",
                            color="#fca5a5",
                            border="1px solid rgba(239,68,68,0.4)",
                            size="2",
                        ),
                        rx.text("-", color="#64748b"),
                    ),
                    spacing="2",
                ),
                width="100%",
            ),
        ),
        width="100%",
        spacing="4",
    )


def papeis_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.hstack(
                rx.input(
                    placeholder="Nome do papel",
                    value=State.new_role_name,
                    on_change=State.set_new_role_name,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                ),
                rx.input(
                    placeholder="Permissões separadas por vírgula",
                    value=State.new_role_permissions,
                    on_change=State.set_new_role_permissions,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                ),
                rx.cond(
                    State.can_manage_roles,
                    rx.hstack(
                        rx.button(
                            State.role_submit_label,
                            on_click=State.create_role,
                            class_name="primary-soft-action",
                        ),
                        rx.cond(
                            State.is_editing_role,
                            rx.button(
                                "Cancelar",
                                on_click=State.reset_role_form,
                                variant="ghost",
                                border="1px solid var(--input-border)",
                                color="var(--text-secondary)",
                            ),
                            rx.fragment(),
                        ),
                    ),
                    rx.badge("Sem permissão", color_scheme="red"),
                ),
                width="100%",
                flex_direction="row",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["Nome", "Permissões", "Ações"],
            State.roles_data,
            lambda r: rx.hstack(
                rx.text(r["name"], color="var(--text-primary)", width="100%"),
                rx.text(r["permissions_str"], color="var(--text-secondary)", width="100%"),
                rx.hstack(
                    rx.cond(
                        State.can_manage_roles,
                        rx.button(
                            "Alterar",
                            on_click=State.start_edit_role(r["id"]),
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        State.can_delete_roles,
                        rx.button(
                            "Excluir",
                            on_click=State.delete_role(r["id"]),
                            bg="rgba(239,68,68,0.2)",
                            color="#fca5a5",
                            border="1px solid rgba(239,68,68,0.4)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2",
                ),
                width="100%",
            ),
        ),
        width="100%",
        spacing="4",
    )


def responsabilidades_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.hstack(
                rx.select(
                    State.role_id_options,
                    placeholder="Role ID",
                    value=State.new_resp_role_id,
                    on_change=State.set_new_resp_role_id,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                    width="160px",
                ),
                rx.input(
                    placeholder="Descrição da responsabilidade",
                    value=State.new_resp_desc,
                    on_change=State.set_new_resp_desc,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                ),
                rx.cond(
                    State.can_manage_resps,
                    rx.hstack(
                        rx.button(
                            State.resp_submit_label,
                            on_click=State.create_responsibility,
                            class_name="primary-soft-action",
                        ),
                        rx.cond(
                            State.is_editing_resp,
                            rx.button(
                                "Cancelar",
                                on_click=State.reset_resp_form,
                                variant="ghost",
                                border="1px solid var(--input-border)",
                                color="var(--text-secondary)",
                            ),
                            rx.fragment(),
                        ),
                    ),
                    rx.badge("Sem permissão", color_scheme="red"),
                ),
                width="100%",
                flex_direction="row",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["Papel", "Descrição", "Ações"],
            State.responsibilities_data,
            lambda r: rx.hstack(
                rx.text(r["role"], color="var(--text-primary)", width="100%"),
                rx.text(r["description"], color="var(--text-secondary)", width="100%"),
                rx.hstack(
                    rx.cond(
                        State.can_manage_resps,
                        rx.button(
                            "Alterar",
                            on_click=State.start_edit_responsibility(r["id"]),
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        State.can_delete_resps,
                        rx.button(
                            "Excluir",
                            on_click=State.delete_responsibility(r["id"]),
                            bg="rgba(239,68,68,0.2)",
                            color="#fca5a5",
                            border="1px solid rgba(239,68,68,0.4)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2",
                ),
                width="100%",
            ),
        ),
        width="100%",
        spacing="4",
    )


def formularios_view() -> rx.Component:
    return rx.vstack(
        rx.grid(
            rx.box(
                rx.vstack(
                    rx.heading("Criar Formulário", color="var(--text-primary)", size="5"),
                    rx.input(
                        placeholder="Nome",
                        value=State.new_form_name,
                        on_change=State.set_new_form_name,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.select(
                        [
                            "Diagnóstico Cultura de Segurança",
                            "Atuação da Liderança",
                            "Segurança versus Produtividade",
                            "Variação Cultural",
                        ],
                        value=State.new_form_category,
                        on_change=State.set_new_form_category,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.button(
                        State.form_submit_label,
                        on_click=State.create_form,
                        class_name="primary-soft-action",
                        width="100%",
                    ),
                    rx.cond(
                        State.is_editing_form,
                        rx.button(
                            "Cancelar",
                            on_click=State.reset_form_builder,
                            variant="ghost",
                            border="1px solid var(--input-border)",
                            color="var(--text-secondary)",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),
                    align="start",
                    width="100%",
                ),
                padding="1rem",
                **CARD_STYLE,
            ),
            rx.box(
                rx.vstack(
                    rx.heading("Perguntas", color="var(--text-primary)", size="5"),
                    rx.select(
                        State.form_id_options,
                        value=State.selected_form_id,
                        on_change=State.select_form,
                        placeholder="Selecione formulário",
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.text(
                        rx.cond(
                            State.selected_form_name != "",
                            f"Formulário ativo: {State.selected_form_name}",
                            "Selecione um formulário ativo para vincular as perguntas.",
                        ),
                        color="var(--text-muted)",
                        font_size="0.78rem",
                    ),
                    rx.input(
                        placeholder="Texto da pergunta",
                        value=State.new_question_text,
                        on_change=State.set_new_question_text,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.select(
                        ["fechada", "aberta"],
                        value=State.new_question_type,
                        on_change=State.set_new_question_type,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.input(
                        placeholder="Opções (vírgula)",
                        value=State.new_question_options,
                        on_change=State.set_new_question_options,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.input(
                        placeholder="Logica condicional (ex: resposta_q1 = Nunca)",
                        value=State.new_question_condition,
                        on_change=State.set_new_question_condition,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.button(
                        "Adicionar Pergunta",
                        on_click=State.create_question,
                        class_name="primary-soft-action",
                        width="100%",
                    ),
                    align="start",
                    width="100%",
                ),
                padding="1rem",
                **CARD_STYLE,
            ),
            columns="2",
            width="100%",
            spacing="4",
        ),
        data_table(
            ["ID", "Formulário", "Categoria", "Ações"],
            State.forms_data,
            lambda f: rx.hstack(
                rx.text(str(f["id"]), color="var(--text-primary)", width="100%"),
                rx.text(f["name"], color="var(--text-primary)", width="100%"),
                rx.text(f["category"], color="var(--text-secondary)", width="100%"),
                rx.hstack(
                    rx.button(
                        "Selecionar",
                        on_click=State.select_form_by_id(f["id"]),
                        class_name="primary-soft-action",
                        size="2",
                    ),
                    rx.cond(
                        State.can_manage_forms,
                        rx.button(
                            "Alterar",
                            on_click=State.start_edit_form(f["id"]),
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        State.can_delete_forms,
                        rx.button(
                            "Excluir",
                            on_click=State.delete_form(f["id"]),
                            bg="rgba(239,68,68,0.2)",
                            color="#fca5a5",
                            border="1px solid rgba(239,68,68,0.4)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2",
                ),
                width="100%",
                align="center",
            ),
        ),
        rx.box(
            rx.vstack(
                rx.heading("Recursos (Drag and Drop)", color="var(--text-primary)", size="5"),
                rx.text(
                    "Arraste arquivos para a área abaixo ou clique para selecionar.",
                    color="var(--text-muted)",
                    font_size="0.9rem",
                ),
                rx.upload(
                    rx.vstack(
                        rx.icon(tag="upload", color="var(--accent-strong)", size=20),
                        rx.text("Solte os arquivos aqui", color="var(--text-primary)"),
                        rx.text("ou clique para abrir o seletor", color="var(--text-muted)", font_size="0.85rem"),
                        align="center",
                        spacing="2",
                    ),
                    id="resource_upload",
                    width="100%",
                    padding="1.2rem",
                    border="2px dashed var(--dropzone-border)",
                    border_radius="16px",
                    bg="var(--dropzone-bg)",
                    class_name="dropzone-area",
                ),
                rx.hstack(
                    rx.button(
                        "Enviar Arquivos",
                        on_click=State.handle_resource_upload(rx.upload_files(upload_id="resource_upload")),
                        class_name="primary-soft-action",
                    ),
                    rx.button(
                        "Limpar Seleção",
                        on_click=rx.clear_selected_files("resource_upload"),
                        variant="ghost",
                        border="1px solid var(--input-border)",
                        color="var(--text-secondary)",
                    ),
                    spacing="3",
                ),
                rx.vstack(
                    rx.text("Selecionados:", color="var(--text-muted)", font_size="0.82rem"),
                    rx.foreach(
                        rx.selected_files("resource_upload"),
                        lambda file_name: rx.text(file_name, color="var(--text-secondary)", font_size="0.85rem"),
                    ),
                    align="start",
                    width="100%",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Enviados:", color="var(--text-muted)", font_size="0.82rem"),
                    rx.foreach(
                        State.uploaded_resources,
                        lambda file_name: rx.text(file_name, color="var(--text-secondary)", font_size="0.85rem"),
                    ),
                    align="start",
                    width="100%",
                    spacing="1",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["Pergunta", "Tipo", "Opções", "Ação"],
            State.questions_data,
            lambda q: rx.hstack(
                rx.text(q["text"], color="var(--text-primary)", width="100%"),
                rx.badge(q["qtype"], color_scheme="purple", width="100%"),
                rx.text(q["options_str"], color="var(--text-secondary)", width="100%"),
                rx.badge("Arrastável", color_scheme="gray", variant="soft"),
                rx.button(
                    "Resposta Mock",
                    on_click=State.add_mock_response(q["id"], "Resposta de diagnóstico", 3),
                    bg="rgba(161,0,161,0.25)",
                    color="#e9d5ff",
                    border="1px solid rgba(161,0,161,0.45)",
                    size="2",
                ),
                rx.button(
                    "Enviar para IA",
                    on_click=State.start_drag_question(q["text"]),
                    variant="outline",
                    border="1px solid var(--input-border)",
                    color="var(--text-secondary)",
                    size="2",
                ),
                width="100%",
            ),
        ),
        data_table(
            ["Pergunta", "Tipo", "Logica", "Entrada"],
            State.form_logic_preview,
            lambda row: rx.hstack(
                rx.text(row["question"], color="var(--text-primary)", width="100%"),
                rx.badge(row["type"], color_scheme="purple", width="fit-content"),
                rx.text(row["logic"], color="var(--text-secondary)", width="100%"),
                rx.text(row["options"], color="var(--text-secondary)", width="100%"),
                width="100%",
            ),
        ),
        width="100%",
        spacing="4",
        class_name="content-stack",
    )


def ia_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Assistente Conversacional SSecur1", color="var(--text-primary)", size="6"),
                rx.text(
                    "Use IA para entender dashboards, priorizar ações e orientar entrevistas de diagnóstico.",
                    color="var(--text-muted)",
                ),
                rx.text_area(
                    placeholder="Pergunte: Como interpretar Segurança vs Produtividade?",
                    value=State.ai_prompt,
                    on_change=State.set_ai_prompt,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                    min_height="120px",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("Dropzone: arraste uma pergunta da tela de Formulários para cá.", color="var(--text-muted)"),
                        rx.text(
                            rx.cond(
                                State.dragged_question_text != "",
                                "Pronto para soltar uma pergunta arrastada.",
                                "Nenhuma pergunta em arraste no momento.",
                            ),
                            color="var(--text-secondary)",
                            font_size="0.9rem",
                        ),
                        rx.cond(
                            State.dragged_question_text != "",
                            rx.text(State.dragged_question_text, color="var(--text-secondary)", font_size="0.85rem"),
                            rx.fragment(),
                        ),
                        align="start",
                        width="100%",
                        spacing="2",
                    ),
                    width="100%",
                    padding="0.9rem",
                    border="1px dashed var(--input-border)",
                    border_radius="14px",
                    bg="var(--surface-soft)",
                    on_click=State.drop_question_into_prompt,
                ),
                rx.button(
                    "Gerar orientação",
                    on_click=State.ask_ai,
                    class_name="primary-soft-action",
                ),
                rx.box(
                    rx.text(State.ai_answer, white_space="pre-wrap", color="var(--text-secondary)"),
                    width="100%",
                    min_height="140px",
                    padding="1rem",
                    bg="var(--surface-soft)",
                    border="1px solid var(--input-border)",
                    border_radius="12px",
                ),
                rx.text(
                    "Resultados suportam: clareza real da cultura, base para trilha da liderança, redução de riscos e custos.",
                    color="var(--text-muted)",
                ),
                align="start",
                width="100%",
                spacing="4",
            ),
            width="100%",
            padding="1.2rem",
            **CARD_STYLE,
        ),
        width="100%",
    )


def workspace_view() -> rx.Component:
    return rx.box(
        rx.box(class_name="bg-orb bg-orb-left"),
        rx.box(class_name="bg-orb bg-orb-right"),
        rx.hstack(
            sidebar(),
            rx.box(
                app_header(),
                rx.box(
                    rx.cond(
                        State.active_view == "dashboard",
                        dashboard_view(),
                        rx.cond(
                            State.active_view == "apis",
                            apis_view(),
                            rx.cond(
                                State.active_view == "projetos",
                                projetos_view(),
                                rx.cond(
                                    State.active_view == "planos",
                                    planos_view(),
                                    rx.cond(
                                        State.active_view == "permissoes",
                                        permissoes_view(),
                                        rx.cond(
                                            State.active_view == "usuarios",
                                            usuarios_view(),
                                            rx.cond(
                                            State.active_view == "clientes",
                                            clientes_view(),
                                            rx.cond(
                                                State.active_view == "tenants",
                                                tenants_view(),
                                                rx.cond(
                                                    State.active_view == "papeis",
                                                    papeis_view(),
                                                    rx.cond(
                                                        State.active_view == "responsabilidades",
                                                        responsabilidades_view(),
                                                        rx.cond(
                                                            State.active_view == "formularios",
                                                            formularios_view(),
                                                            ia_view(),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    padding="1rem 1rem 1.5rem",
                ),
                width="100%",
                min_height="100vh",
                class_name="workspace-main",
            ),
            width="100%",
            align="start",
            bg="var(--page-bg)",
            position="relative",
            z_index="1",
        ),
        width="100%",
        position="relative",
        overflow="hidden",
        class_name="workspace-shell",
    )


def auth_modal() -> rx.Component:
    return rx.cond(
        State.auth_open,
        rx.box(
            rx.box(
                rx.hstack(
                    rx.box(
                        rx.vstack(
                            smartlab_logo("62px"),
                            rx.badge("Acesso Seguro", color_scheme="orange"),
                            rx.heading("Entre na plataforma SmartLab", color="var(--text-primary)", size="7"),
                            rx.text(
                                "Consultores operam clientes, projetos e diagnosticos. O portal do cliente sera liberado com acesso controlado.",
                                color="var(--text-secondary)",
                                font_size="0.96rem",
                            ),
                            rx.vstack(
                                rx.hstack(rx.badge("RBAC", color_scheme="purple"), rx.text("Controle por papel", color="var(--text-muted)")),
                                rx.hstack(rx.badge("Tenant", color_scheme="orange"), rx.text("Dados segregados por cliente", color="var(--text-muted)")),
                                rx.hstack(rx.badge("Local", color_scheme="green"), rx.text("Execucao local com evolucao futura para cloud", color="var(--text-muted)")),
                                align="start",
                                spacing="3",
                                width="100%",
                            ),
                            spacing="4",
                            align="start",
                            width="100%",
                        ),
                        class_name="auth-hero",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.cond(
                                State.force_password_reset_required,
                                rx.vstack(
                                    rx.vstack(
                                        rx.heading("Troca obrigatoria de senha", color="var(--text-primary)", size="6"),
                                        rx.text(
                                            "Este e o primeiro acesso do usuario. Defina uma nova senha para continuar.",
                                            color="var(--text-muted)",
                                        ),
                                        align="start",
                                        spacing="1",
                                        width="100%",
                                    ),
                                    rx.badge("Primeiro acesso", color_scheme="orange"),
                                    rx.vstack(
                                        rx.text("Conta", color="var(--text-muted)", font_size="0.82rem"),
                                        rx.input(
                                            value=State.login_email,
                                            read_only=True,
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            width="100%",
                                        ),
                                        rx.text("Nova senha", color="var(--text-muted)", font_size="0.82rem"),
                                        rx.hstack(
                                            rx.input(
                                                placeholder="Defina a nova senha",
                                                type=rx.cond(State.first_access_password_visible, "text", "password"),
                                                value=State.first_access_new_password,
                                                on_change=State.set_first_access_new_password,
                                                bg="var(--input-bg)",
                                                color="var(--text-primary)",
                                                width="100%",
                                            ),
                                            rx.button(
                                                rx.icon(tag=rx.cond(State.first_access_password_visible, "eye_off", "eye"), size=16),
                                                on_click=State.toggle_first_access_password_visibility,
                                                variant="ghost",
                                                border="1px solid var(--input-border)",
                                            ),
                                            width="100%",
                                        ),
                                        rx.text("Confirmacao", color="var(--text-muted)", font_size="0.82rem"),
                                        rx.hstack(
                                            rx.input(
                                                placeholder="Repita a nova senha",
                                                type=rx.cond(State.first_access_password_visible, "text", "password"),
                                                value=State.first_access_confirm_password,
                                                on_change=State.set_first_access_confirm_password,
                                                bg="var(--input-bg)",
                                                color="var(--text-primary)",
                                                width="100%",
                                            ),
                                            rx.button(
                                                rx.icon(tag=rx.cond(State.first_access_password_visible, "eye_off", "eye"), size=16),
                                                on_click=State.toggle_first_access_password_visibility,
                                                variant="ghost",
                                                border="1px solid var(--input-border)",
                                            ),
                                            width="100%",
                                        ),
                                        rx.button(
                                            "Salvar nova senha",
                                            on_click=State.complete_first_access_password_change,
                                            class_name="primary-soft-action",
                                            width="100%",
                                            size="3",
                                        ),
                                        width="100%",
                                        align="start",
                                        spacing="2",
                                    ),
                                    spacing="4",
                                    align="start",
                                    width="100%",
                                ),
                                rx.vstack(
                                    rx.vstack(
                                        rx.heading("Acesso", color="var(--text-primary)", size="6"),
                                        rx.text("Login usa uma conta ja existente aprovada pela SmartLab.", color="var(--text-muted)"),
                                        align="start",
                                        spacing="1",
                                        width="100%",
                                    ),
                                    rx.badge("Acesso corporativo", color_scheme="purple"),
                                    rx.vstack(
                                        rx.text("E-mail", color="var(--text-muted)", font_size="0.82rem"),
                                        rx.input(
                                            placeholder="admin@smartlab.com",
                                            value=State.login_email,
                                            on_change=State.set_login_email,
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            width="100%",
                                        ),
                                        rx.text("Senha", color="var(--text-muted)", font_size="0.82rem"),
                                        rx.hstack(
                                            rx.input(
                                                placeholder="Digite sua senha",
                                                type=rx.cond(State.login_password_visible, "text", "password"),
                                                value=State.login_password,
                                                on_change=State.set_login_password,
                                                bg="var(--input-bg)",
                                                color="var(--text-primary)",
                                                width="100%",
                                            ),
                                            rx.button(
                                                rx.icon(tag=rx.cond(State.login_password_visible, "eye_off", "eye"), size=16),
                                                on_click=State.toggle_login_password_visibility,
                                                variant="ghost",
                                                border="1px solid var(--input-border)",
                                            ),
                                            width="100%",
                                        ),
                                        rx.button(
                                            "Entrar no workspace",
                                            on_click=State.login,
                                            class_name="primary-soft-action",
                                            width="100%",
                                            size="3",
                                        ),
                                        rx.box(
                                            rx.vstack(
                                                rx.text("Como o acesso funciona", color="var(--text-primary)", font_weight="700"),
                                                rx.text("1. A SmartLab cria ou libera sua conta.", color="var(--text-muted)", font_size="0.84rem"),
                                                rx.text("2. Voce entra com credenciais ja existentes.", color="var(--text-muted)", font_size="0.84rem"),
                                                rx.text("3. O que voce enxerga depende do tenant e do seu papel.", color="var(--text-muted)", font_size="0.84rem"),
                                                align="start",
                                                spacing="1",
                                                width="100%",
                                            ),
                                            class_name="auth-note",
                                        ),
                                        rx.hstack(
                                            rx.text("Nao existe auto-registro publico nesta fase.", color="var(--text-muted)", font_size="0.82rem"),
                                            rx.spacer(),
                                            rx.text("Provisionamento controlado", color="var(--text-muted)", font_size="0.82rem"),
                                            width="100%",
                                        ),
                                        width="100%",
                                        align="start",
                                        spacing="2",
                                    ),
                                    spacing="4",
                                    align="start",
                                    width="100%",
                                ),
                            ),
                            rx.hstack(
                                rx.button("Fechar", on_click=State.close_auth, variant="ghost", color="var(--text-muted)"),
                                rx.spacer(),
                                rx.text("Desenvolvido por i9Exp - SmartLab", color="var(--text-muted)", font_size="0.82rem"),
                                width="100%",
                            ),
                            spacing="4",
                            align="start",
                            width="100%",
                        ),
                        class_name="auth-panel",
                    ),
                    width="min(1080px, 92vw)",
                    align="stretch",
                    spacing="5",
                ),
                width="min(1120px, 94vw)",
                padding="1.2rem",
                spacing="0",
                **CARD_STYLE,
                class_name="auth-shell",
            ),
            position="fixed",
            inset="0",
            bg="var(--overlay-bg)",
            display="flex",
            align_items="center",
            justify_content="center",
            z_index="1000",
        ),
        rx.fragment(),
    )


def main_page() -> rx.Component:
    return rx.cond(
        State.dark_mode,
        rx.theme(
            rx.box(
                rx.cond(State.is_logged, workspace_view(), landing_public()),
                auth_modal(),
                toast(),
                class_name="theme-dark app-theme",
            ),
            appearance="dark",
            accent_color="orange",
            radius="large",
        ),
        rx.theme(
            rx.box(
                rx.cond(State.is_logged, workspace_view(), landing_public()),
                auth_modal(),
                toast(),
                class_name="theme-light app-theme",
            ),
            appearance="light",
            accent_color="orange",
            radius="large",
        ),
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
