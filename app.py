import json
from datetime import datetime
from pathlib import Path
from typing import Any

import reflex as rx
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
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
    limit_users = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    role = Column(String, default="viewer")
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)


class ClientModel(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
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


def _seed() -> None:
    session = SessionLocal()
    if session.query(TenantModel).count() == 0:
        t1 = TenantModel(id="default", name="SmartLab Demo", slug="smartlab", limit_users=150)
        t2 = TenantModel(id="industrial", name="Industrial Ops", slug="industrial-ops", limit_users=80)
        session.add_all([t1, t2])
        session.add(
            UserModel(
                name="Admin SmartLab",
                email="admin@smartlab.com",
                password="admin123",
                role="admin",
                tenant_id="default",
            )
        )
        session.add_all(
            [
                ClientModel(tenant_id="default", name="Ana Costa", email="ana@cliente.com"),
                ClientModel(tenant_id="default", name="Bruno Silva", email="bruno@cliente.com"),
                ClientModel(tenant_id="industrial", name="Carlos Souza", email="carlos@ops.com"),
            ]
        )
        role = RoleModel(tenant_id="default", name="Lideranca", permissions=json.dumps(["diagnostico", "treinamento"]))
        session.add(role)
        session.flush()
        session.add(
            ResponsibilityModel(
                tenant_id="default",
                role_id=role.id,
                description="Garantir diálogo diário sobre riscos críticos na operação.",
            )
        )
        form = FormModel(tenant_id="default", name="Diagnóstico Cultura de Segurança", category="Cultura")
        session.add(form)
        session.flush()
        q1 = QuestionModel(
            tenant_id="default",
            form_id=form.id,
            text="A liderança discute segurança antes da produtividade?",
            qtype="fechada",
            options_json=json.dumps(["Sempre", "Frequentemente", "Raramente", "Nunca"]),
        )
        q2 = QuestionModel(
            tenant_id="default",
            form_id=form.id,
            text="Quais barreiras você encontra para seguir os procedimentos?",
            qtype="aberta",
            options_json="[]",
        )
        session.add_all([q1, q2])
        session.flush()
        session.add_all(
            [
                ResponseModel(
                    tenant_id="default",
                    form_id=form.id,
                    question_id=q1.id,
                    answer="Frequentemente",
                    score=4,
                ),
                ResponseModel(
                    tenant_id="default",
                    form_id=form.id,
                    question_id=q2.id,
                    answer="Pressão de prazo e comunicação entre turnos.",
                    score=2,
                ),
            ]
        )
        session.commit()

    if session.query(ProjectModel).count() == 0:
        project = ProjectModel(
            tenant_id="default",
            name="Diagnóstico Cultura 2026",
            project_type="Diagnóstico de Cultura",
            status="execucao",
            progress=35,
        )
        session.add(project)
        session.flush()

        session.add_all(
            [
                WorkflowBoxModel(
                    tenant_id="default",
                    project_id=project.id,
                    title="Visita Técnica",
                    box_type="coleta",
                    position=1,
                    config_json=json.dumps({"owner": "Consultor SmartLab", "duracao": "2h"}),
                ),
                WorkflowBoxModel(
                    tenant_id="default",
                    project_id=project.id,
                    title="Rodas de Conversa",
                    box_type="coleta",
                    position=2,
                    config_json=json.dumps({"owner": "Lideranças", "duracao": "90min"}),
                ),
                WorkflowBoxModel(
                    tenant_id="default",
                    project_id=project.id,
                    title="Análise IA",
                    box_type="analise",
                    position=3,
                    config_json=json.dumps({"modelo": "smartlab-nlp-v1", "drill_down": True}),
                ),
            ]
        )
        session.add_all(
            [
                ActionPlanModel(
                    tenant_id="default",
                    project_id=project.id,
                    title="Ritual diário de 10 min de segurança",
                    owner="Supervisão de Turno",
                    due_date="2026-04-15",
                    status="a_fazer",
                    expected_result="Aumentar presença da liderança",
                    attainment=0,
                ),
                ActionPlanModel(
                    tenant_id="default",
                    project_id=project.id,
                    title="Checklist de parada segura",
                    owner="Operação",
                    due_date="2026-04-05",
                    status="em_andamento",
                    expected_result="Reduzir riscos críticos",
                    attainment=40,
                ),
            ]
        )
        session.add_all(
            [
                PermissionBoxModel(
                    tenant_id="default",
                    user_email="ana@cliente.com",
                    resource="Dashboard Executivo",
                    decision="permitido",
                ),
                PermissionBoxModel(
                    tenant_id="default",
                    user_email="ana@cliente.com",
                    resource="Plano de Ações",
                    decision="negado",
                ),
            ]
        )
        session.add_all(
            [
                DashboardBoxModel(
                    tenant_id="default",
                    role_scope="consultor",
                    title="Projetos Ativos",
                    kind="lista",
                    position=1,
                    config_json=json.dumps({"fonte": "projetos"}),
                ),
                DashboardBoxModel(
                    tenant_id="default",
                    role_scope="consultor",
                    title="Score de Cultura",
                    kind="kpi",
                    position=2,
                    config_json=json.dumps({"fonte": "scores"}),
                ),
                DashboardBoxModel(
                    tenant_id="default",
                    role_scope="cliente",
                    title="Progresso do Projeto",
                    kind="kpi",
                    position=1,
                    config_json=json.dumps({"fonte": "progresso"}),
                ),
            ]
        )
        session.commit()
    session.close()


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
    register_name: str = ""
    register_email: str = ""
    register_password: str = ""
    register_password_visible: bool = False
    dragged_question_text: str = ""
    uploaded_resources: list[str] = []

    new_client_name: str = ""
    new_client_email: str = ""

    new_tenant_name: str = ""
    new_tenant_slug: str = ""
    new_tenant_limit: str = "50"

    new_role_name: str = ""
    new_role_permissions: str = "create:clientes,edit:clientes"

    new_resp_role_id: str = ""
    new_resp_desc: str = ""

    new_form_name: str = ""
    new_form_category: str = "Diagnóstico Cultura de Segurança"
    selected_form_id: str = ""
    new_question_text: str = ""
    new_question_type: str = "fechada"
    new_question_options: str = "Sempre,Frequentemente,Raramente,Nunca"

    ai_prompt: str = ""
    ai_answer: str = ""

    new_project_name: str = ""
    new_project_type: str = "Diagnóstico de Cultura"
    selected_project_id: str = ""
    new_box_title: str = ""
    new_box_type: str = "etapa"
    new_box_method: str = "GET"
    new_box_endpoint: str = ""
    new_box_headers: str = "Authorization: Bearer token"
    new_box_retry_policy: str = "none"
    new_box_client_id: str = ""
    new_box_client_secret: str = ""
    new_box_schedule: str = "0 8 * * 1-5"
    new_sticky_note_text: str = ""
    workflow_logs: list[str] = []

    new_action_title: str = ""
    new_action_owner: str = ""
    new_action_due_date: str = ""
    new_action_expected_result: str = ""

    perm_user_email: str = ""
    perm_resource_name: str = ""

    new_dashboard_box_title: str = ""
    new_dashboard_box_kind: str = "kpi"
    new_dashboard_box_scope: str = "consultor"

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
        data = [t.id for t in session.query(TenantModel).order_by(TenantModel.name.asc()).all()]
        session.close()
        return data

    @rx.var
    def can_manage_clients(self) -> bool:
        return "create:clientes" in ROLE_PERMS.get(self.user_role, set())

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
    def can_manage_resps(self) -> bool:
        return "create:responsabilidades" in ROLE_PERMS.get(self.user_role, set())

    @rx.var
    def can_manage_forms(self) -> bool:
        return "create:forms" in ROLE_PERMS.get(self.user_role, set())

    def has_perm(self, perm: str) -> bool:
        return perm in ROLE_PERMS.get(self.user_role, set())

    @rx.var(cache=False)
    def tenants_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        rows = session.query(TenantModel).order_by(TenantModel.created_at.desc()).all()
        data = [{"id": r.id, "name": r.name, "slug": r.slug, "limit": r.limit_users} for r in rows]
        session.close()
        return data

    @rx.var(cache=False)
    def clients_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        rows = (
            session.query(ClientModel)
            .filter(ClientModel.tenant_id == self.current_tenant)
            .order_by(ClientModel.created_at.desc())
            .all()
        )
        data = [{"id": r.id, "name": r.name, "email": r.email, "tenant_id": r.tenant_id} for r in rows]
        session.close()
        return data

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
                "options": json.loads(r.options_json or "[]"),
                "options_str": ", ".join(json.loads(r.options_json or "[]")),
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def projects_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        rows = (
            session.query(ProjectModel)
            .filter(ProjectModel.tenant_id == self.current_tenant)
            .order_by(ProjectModel.created_at.desc())
            .all()
        )
        data = [
            {
                "id": r.id,
                "name": r.name,
                "project_type": r.project_type,
                "status": r.status,
                "progress": r.progress,
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var
    def project_id_options(self) -> list[str]:
        return [str(p["id"]) for p in self.projects_data]

    @rx.var(cache=False)
    def workflow_boxes_data(self) -> list[dict[str, Any]]:
        if not self.selected_project_id:
            return []
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
        data = [
            {
                "id": r.id,
                "title": r.title,
                "box_type": r.box_type,
                "position": r.position,
                "config": json.loads(r.config_json or "{}"),
                "zone": json.loads(r.config_json or "{}").get("zone", "center"),
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
                    "has_next": has_next,
                    "line_type": line_type,
                }
            )
        return items

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
                ActionPlanModel.tenant_id == self.current_tenant,
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
        session = SessionLocal()
        query = session.query(PermissionBoxModel).filter(PermissionBoxModel.tenant_id == self.current_tenant)
        if self.perm_user_email:
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
        data = [{"id": r.id, "title": r.title, "kind": r.kind, "position": r.position} for r in rows]
        session.close()
        return data

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

    def toggle_register_password_visibility(self):
        self.register_password_visible = not self.register_password_visible

    def set_active_view(self, view: str):
        self.active_view = view
        self.mobile_menu_open = False

    def switch_tenant(self, value: str):
        self.current_tenant = value
        self.hydrate_tenant_context()

    def hydrate_tenant_context(self):
        session = SessionLocal()
        first_project = (
            session.query(ProjectModel.id)
            .filter(ProjectModel.tenant_id == self.current_tenant)
            .order_by(ProjectModel.created_at.desc())
            .first()
        )
        session.close()
        self.selected_project_id = str(first_project[0]) if first_project else ""

    def set_auth_mode(self, mode: str):
        self.auth_mode = mode

    def set_login_email(self, value: str):
        self.login_email = value

    def set_login_password(self, value: str):
        self.login_password = value

    def set_register_name(self, value: str):
        self.register_name = value

    def set_register_email(self, value: str):
        self.register_email = value

    def set_register_password(self, value: str):
        self.register_password = value

    def set_new_client_name(self, value: str):
        self.new_client_name = value

    def set_new_client_email(self, value: str):
        self.new_client_email = value

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

    def set_ai_prompt(self, value: str):
        self.ai_prompt = value

    def set_new_project_name(self, value: str):
        self.new_project_name = value

    def set_new_project_type(self, value: str):
        self.new_project_type = value

    def select_project(self, value: str):
        self.selected_project_id = value

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

    def set_perm_user_email(self, value: str):
        self.perm_user_email = value

    def set_perm_resource_name(self, value: str):
        self.perm_resource_name = value

    def set_new_dashboard_box_title(self, value: str):
        self.new_dashboard_box_title = value

    def set_new_dashboard_box_kind(self, value: str):
        self.new_dashboard_box_kind = value

    def set_new_dashboard_box_scope(self, value: str):
        self.new_dashboard_box_scope = value

    def open_auth(self):
        self.auth_open = True

    def close_auth(self):
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
        self.current_tenant = user.tenant_id
        self.hydrate_tenant_context()
        self.auth_open = False
        self.toast_message = "Login realizado com sucesso"
        self.toast_type = "success"
        session.close()

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
        self.current_tenant = "default"
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
        session = SessionLocal()
        session.add(
            ClientModel(
                tenant_id=self.current_tenant,
                name=self.new_client_name,
                email=self.new_client_email,
            )
        )
        session.commit()
        session.close()
        self.new_client_name = ""
        self.new_client_email = ""
        self.toast_message = "Cliente criado"
        self.toast_type = "success"

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
        tenant_id = self.new_tenant_slug.strip().lower().replace(" ", "-")
        exists = session.query(TenantModel).filter(TenantModel.id == tenant_id).first()
        if exists:
            self.toast_message = "Slug já existe"
            self.toast_type = "error"
            session.close()
            return
        session.add(
            TenantModel(
                id=tenant_id,
                name=self.new_tenant_name,
                slug=self.new_tenant_slug,
                limit_users=int(self.new_tenant_limit or "50"),
            )
        )
        session.commit()
        session.close()
        self.new_tenant_name = ""
        self.new_tenant_slug = ""
        self.new_tenant_limit = "50"
        self.toast_message = "Tenant criado"
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
        session.add(
            RoleModel(
                tenant_id=self.current_tenant,
                name=self.new_role_name or "Novo Papel",
                permissions=json.dumps(perms),
            )
        )
        session.commit()
        session.close()
        self.new_role_name = ""
        self.new_role_permissions = ""
        self.toast_message = "Papel criado"
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
        session.add(
            ResponsibilityModel(
                tenant_id=self.current_tenant,
                role_id=int(self.new_resp_role_id),
                description=self.new_resp_desc,
            )
        )
        session.commit()
        session.close()
        self.new_resp_desc = ""
        self.toast_message = "Responsabilidade adicionada"
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
        self.new_form_name = ""
        self.toast_message = "Formulário criado"
        self.toast_type = "success"

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
                options_json=json.dumps(options),
            )
        )
        session.commit()
        session.close()
        self.new_question_text = ""
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
                        "zone": "center",
                        "method": self.new_box_method,
                        "endpoint": self.new_box_endpoint.strip(),
                        "retry_policy": self.new_box_retry_policy,
                        "schedule": self.new_box_schedule.strip(),
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
            if node["box_type"] == "trigger":
                schedule = config.get("schedule", "sem agenda")
                logs.append(f"Trigger '{node['title']}' armado com schedule {schedule}")
                continue
            if endpoint:
                logs.append(f"Node '{node['title']}' executado: {method} {endpoint}")
            else:
                logs.append(f"Node '{node['title']}' executado em modo interno ({node['box_type']})")
            if node["box_type"] == "analise":
                logs.append("Análise IA concluída: recomendação preliminar gerada.")

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
                config_json=json.dumps({"editable": True}),
            )
        )
        session.commit()
        session.close()
        self.new_dashboard_box_title = ""
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
                    background="var(--brand-gradient)",
                    color="#fff",
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
                            background="var(--brand-gradient-strong)",
                            color="#fff",
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
        rx.input(
            placeholder="Buscar cliente, formulário, papel...",
            bg="var(--input-bg)",
            color="var(--text-primary)",
            width="260px",
            display="block",
            border="1px solid var(--input-border)",
        ),
        rx.select(
            State.tenant_options,
            value=State.current_tenant,
            on_change=State.switch_tenant,
            color="var(--text-primary)",
            bg="var(--surface-soft)",
            border="1px solid var(--input-border)",
            width="240px",
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
        nav_button("Dashboard", "layout_dashboard", "dashboard"),
        nav_button("Projetos", "file_text", "projetos"),
        nav_button("Plano de Ação", "list_todo", "planos"),
        nav_button("Permissões", "lock_keyhole", "permissoes"),
        nav_button("Clientes", "users", "clientes"),
        nav_button("Tenants", "building_2", "tenants"),
        nav_button("Papéis", "shield_check", "papeis"),
        nav_button("Responsabilidades", "clipboard_list", "responsabilidades"),
        nav_button("Formulários", "file_text", "formularios"),
        nav_button("Assistente IA", "sparkles", "ia"),
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
                padding_bottom="0.6rem",
            ),
            rx.foreach(rows, row_builder),
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
                        background="var(--brand-gradient)",
                        color="#fff",
                    ),
                    width="100%",
                    spacing="3",
                    flex_wrap="wrap",
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
        rx.grid(
            rx.box(
                rx.vstack(
                    rx.heading("Novo Projeto", color="var(--text-primary)", size="5"),
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
                        background="var(--brand-gradient)",
                        color="#fff",
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
                            background="var(--brand-gradient)",
                            color="#fff",
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
                            bg="rgba(245,158,11,0.2)",
                            color="#f59e0b",
                            border="1px solid rgba(245,158,11,0.35)",
                        ),
                        width="100%",
                        spacing="3",
                    ),
                    rx.hstack(
                        rx.button(
                            "Execute Workflow",
                            on_click=State.execute_workflow,
                            background="var(--brand-gradient)",
                            color="#fff",
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
            columns="2",
            spacing="4",
            width="100%",
        ),
        data_table(
            ["Projeto", "Tipo", "Status", "Progresso"],
            State.projects_data,
            lambda p: rx.hstack(
                rx.text(p["name"], color="var(--text-primary)", width="100%"),
                rx.text(p["project_type"], color="var(--text-secondary)", width="100%"),
                rx.badge(p["status"], color_scheme="purple", width="fit-content"),
                rx.text(f"{p['progress']}%", color="#f59e0b", width="100%"),
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
                    background="var(--brand-gradient)",
                    color="#fff",
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
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Caixas de Permissão", color="var(--text-primary)", size="5"),
                rx.text(
                    "Defina o acesso por usuário usando o campo Permitidos/Negados.",
                    color="var(--text-muted)",
                    font_size="0.9rem",
                ),
                rx.hstack(
                    rx.input(
                        placeholder="E-mail do colaborador",
                        value=State.perm_user_email,
                        on_change=State.set_perm_user_email,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.input(
                        placeholder="Recurso (ex: Relatório Executivo)",
                        value=State.perm_resource_name,
                        on_change=State.set_perm_resource_name,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.button(
                        "Permitir",
                        on_click=State.add_permission_box("permitido"),
                        bg="rgba(34,197,94,0.2)",
                        color="#86efac",
                        border="1px solid rgba(34,197,94,0.4)",
                    ),
                    rx.button(
                        "Negar",
                        on_click=State.add_permission_box("negado"),
                        bg="rgba(239,68,68,0.2)",
                        color="#fca5a5",
                        border="1px solid rgba(239,68,68,0.4)",
                    ),
                    width="100%",
                    spacing="3",
                    flex_wrap="wrap",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["Usuário", "Recurso", "Decisão", "Ações"],
            State.permission_boxes_data,
            lambda p: rx.hstack(
                rx.text(p["user_email"], color="var(--text-primary)", width="100%"),
                rx.text(p["resource"], color="var(--text-secondary)", width="100%"),
                rx.badge(
                    p["decision"],
                    color_scheme=rx.cond(p["decision"] == "permitido", "green", "red"),
                    width="fit-content",
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
        width="100%",
        spacing="4",
    )


def clientes_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.hstack(
                rx.input(
                    placeholder="Nome",
                    value=State.new_client_name,
                    on_change=State.set_new_client_name,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                ),
                rx.input(
                    placeholder="Email",
                    value=State.new_client_email,
                    on_change=State.set_new_client_email,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                ),
                rx.cond(
                    State.can_manage_clients,
                    rx.button(
                        "Adicionar Cliente",
                        on_click=State.create_client,
                        background="var(--brand-gradient)",
                        color="#fff",
                    ),
                    rx.badge("Viewer: somente leitura", color_scheme="purple"),
                ),
                width="100%",
                spacing="3",
                flex_direction="row",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["Nome", "Email", "Tenant", "Ações"],
            State.clients_data,
            lambda c: rx.hstack(
                rx.text(c["name"], color="var(--text-primary)", width="100%"),
                rx.text(c["email"], color="var(--text-secondary)", width="100%"),
                rx.badge(c["tenant_id"], color_scheme="purple", width="100%"),
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
                width="100%",
                align="center",
            ),
        ),
        spacing="4",
        width="100%",
    )


def tenants_view() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.hstack(
                rx.input(
                    placeholder="Nome tenant",
                    value=State.new_tenant_name,
                    on_change=State.set_new_tenant_name,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                ),
                rx.input(
                    placeholder="slug",
                    value=State.new_tenant_slug,
                    on_change=State.set_new_tenant_slug,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                ),
                rx.input(
                    placeholder="Limite usuários",
                    value=State.new_tenant_limit,
                    on_change=State.set_new_tenant_limit,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                ),
                rx.cond(
                    State.can_manage_tenants,
                    rx.button(
                        "Criar Tenant",
                        on_click=State.create_tenant,
                        background="var(--brand-gradient)",
                        color="#fff",
                    ),
                    rx.badge("Sem permissão", color_scheme="red"),
                ),
                width="100%",
                flex_direction="row",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        ),
        data_table(
            ["ID", "Nome", "Slug", "Limite", "Ações"],
            State.tenants_data,
            lambda t: rx.hstack(
                rx.text(t["id"], color="var(--text-primary)", width="100%"),
                rx.text(t["name"], color="var(--text-primary)", width="100%"),
                rx.text(t["slug"], color="var(--text-secondary)", width="100%"),
                rx.text(t["limit"], color="#f59e0b", width="100%"),
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
                    rx.button(
                        "Criar Papel",
                        on_click=State.create_role,
                        background="var(--brand-gradient)",
                        color="#fff",
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
                rx.button(
                    "Excluir",
                    on_click=State.delete_role(r["id"]),
                    bg="rgba(239,68,68,0.2)",
                    color="#fca5a5",
                    border="1px solid rgba(239,68,68,0.4)",
                    size="2",
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
                    rx.button(
                        "Adicionar",
                        on_click=State.create_responsibility,
                        background="var(--brand-gradient)",
                        color="#fff",
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
                rx.button(
                    "Excluir",
                    on_click=State.delete_responsibility(r["id"]),
                    bg="rgba(239,68,68,0.2)",
                    color="#fca5a5",
                    border="1px solid rgba(239,68,68,0.4)",
                    size="2",
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
                        "Salvar Formulário",
                        on_click=State.create_form,
                        background="var(--brand-gradient)",
                        color="#fff",
                        width="100%",
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
                    rx.button(
                        "Adicionar Pergunta",
                        on_click=State.create_question,
                        background="var(--brand-gradient)",
                        color="#fff",
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
            ["ID", "Formulário", "Categoria", "Ação"],
            State.forms_data,
            lambda f: rx.hstack(
                rx.text(str(f["id"]), color="var(--text-primary)", width="100%"),
                rx.text(f["name"], color="var(--text-primary)", width="100%"),
                rx.text(f["category"], color="var(--text-secondary)", width="100%"),
                rx.button(
                    "Selecionar",
                    on_click=State.select_form_by_id(f["id"]),
                    background="var(--brand-gradient)",
                    color="#fff",
                    size="2",
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
                        background="var(--brand-gradient)",
                        color="#fff",
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
                    background="var(--brand-gradient)",
                    color="#fff",
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
                            State.active_view == "projetos",
                            projetos_view(),
                            rx.cond(
                                State.active_view == "planos",
                                planos_view(),
                                rx.cond(
                                    State.active_view == "permissoes",
                                    permissoes_view(),
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
                    smartlab_logo("52px"),
                    rx.vstack(
                        rx.heading("Tenha uma ótima experiência com o SmartLab!", color="var(--text-primary)", size="6"),
                        rx.text("Login e Registro", color="var(--text-muted)"),
                        align="start",
                        spacing="0",
                    ),
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        "Login",
                        on_click=State.set_auth_mode("login"),
                        bg=rx.cond(State.auth_mode == "login", "var(--active-item-bg)", "transparent"),
                        border="1px solid var(--active-item-border)",
                        color="var(--text-primary)",
                    ),
                    rx.button(
                        "Registro",
                        on_click=State.set_auth_mode("register"),
                        bg=rx.cond(State.auth_mode == "register", "var(--active-item-bg)", "transparent"),
                        border="1px solid var(--active-item-border)",
                        color="var(--text-primary)",
                    ),
                ),
                rx.cond(
                    State.auth_mode == "login",
                    rx.vstack(
                        rx.input(
                            placeholder="email",
                            value=State.login_email,
                            on_change=State.set_login_email,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                        ),
                        rx.hstack(
                            rx.input(
                                placeholder="senha",
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
                            "Entrar",
                            on_click=State.login,
                            background="var(--brand-gradient)",
                            color="#fff",
                            width="100%",
                        ),
                        rx.link(
                            "Esqueceu sua senha?",
                            href="#",
                            color="var(--accent-strong)",
                            text_decoration="underline",
                            font_size="0.88rem",
                        ),
                        width="100%",
                    ),
                    rx.vstack(
                        rx.input(
                            placeholder="nome",
                            value=State.register_name,
                            on_change=State.set_register_name,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                        ),
                        rx.input(
                            placeholder="email",
                            value=State.register_email,
                            on_change=State.set_register_email,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                        ),
                        rx.hstack(
                            rx.input(
                                placeholder="senha",
                                type=rx.cond(State.register_password_visible, "text", "password"),
                                value=State.register_password,
                                on_change=State.set_register_password,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            rx.button(
                                rx.icon(tag=rx.cond(State.register_password_visible, "eye_off", "eye"), size=16),
                                on_click=State.toggle_register_password_visibility,
                                variant="ghost",
                                border="1px solid var(--input-border)",
                            ),
                            width="100%",
                        ),
                        rx.button(
                            "Criar conta",
                            on_click=State.register,
                            background="var(--brand-gradient)",
                            color="#fff",
                            width="100%",
                        ),
                        width="100%",
                    ),
                ),
                rx.text(
                    "Desenvolvido por i9Exp - SmartLab",
                    color="var(--text-muted)",
                    font_size="0.82rem",
                    text_align="center",
                    width="100%",
                ),
                rx.button("Fechar", on_click=State.close_auth, variant="ghost", color="var(--text-muted)"),
                width="540px",
                padding="1.4rem",
                spacing="4",
                **CARD_STYLE,
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
