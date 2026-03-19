import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import reflex as rx
from ssecur1.db import (
    ActionTaskModel,
    ActionPlanModel,
    AssistantChunkModel,
    AssistantConversationModel,
    AssistantDocumentModel,
    AssistantMessageModel,
    AssistantRecommendationModel,
    ClientModel,
    CustomOptionModel,
    DashboardBoxModel,
    FormModel,
    hash_password,
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
from ssecur1.catalogs import (
    API_RESOURCE_CATALOG,
    BRAZILIAN_STATE_CODES,
    PERMISSION_RESOURCE_CATALOG,
    RESOURCE_PERMISSION_TOKENS,
    ROLE_PERMS,
    ROLE_PERMISSION_CATALOG,
    ROLE_TEMPLATE_ALIASES,
    ROLE_TEMPLATE_CATALOG,
    ROLE_TEMPLATE_OPTION_KEYS,
    WORKFLOW_STAGE_LIBRARY,
    _catalog_tenant_for_key,
)
from ssecur1.state.assistant import (
    AssistantStateMixin,
    append_audit_file as _append_audit_file,
)
from ssecur1.state.access import AccessStateMixin
from ssecur1.state.admin import AdminStateMixin
from ssecur1.state.dashboard import DashboardStateMixin
from ssecur1.state.forms import FormStateMixin
from ssecur1.state.projects import ProjectStateMixin
from ssecur1.state.session import SessionStateMixin
from ssecur1.ui.composition import build_main_page_component
from ssecur1.utils import (
    build_client_children_map as _build_client_children_map,
    collect_descendant_client_ids as _collect_descendant_client_ids,
    dimension_maturity_label as _dimension_maturity_label,
    dom_token as _dom_token,
    format_display_date as _format_display_date,
    format_display_datetime as _format_display_datetime,
    format_brl_amount as _format_brl_amount,
    loads_json as _loads_json,
    now_brasilia as _now_brasilia,
    parse_brl_amount as _parse_brl_amount,
    parse_int as _parse_int,
    question_payload as _question_payload,
    slugify as _slugify,
)


class State(AccessStateMixin, AdminStateMixin, ProjectStateMixin, FormStateMixin, AssistantStateMixin, DashboardStateMixin, SessionStateMixin):
    dragged_question_text: str = ""
    uploaded_resources: list[str] = []
    global_search_query: str = ""
    dashboard_scope_mode: str = "tenant"
    dashboard_theme_tab: str = "executive"
    dashboard_period_mode: str = "Todo período"
    dashboard_selected_project_id: str = "Todos"
    dashboard_selected_client_id: str = "Todos"
    dashboard_selected_service_name: str = "Todos"
    dashboard_selected_department: str = "Todos"
    dashboard_drill_key: str = ""
    ai_selected_model: str = ""
    ai_resource_type: str = "politica"
    ai_knowledge_scope: str = "tenant"
    ai_scope_mode: str = "tenant"
    ai_history: list[dict[str, str]] = []
    ai_recommendation_items: list[dict[str, str]] = []
    ai_recommendation_editing_id: str = ""
    ai_recommendation_sending_id: str = ""
    ai_recommendation_snapshot: list[dict[str, str]] = []
    audit_active_tab: str = "overview"
    audit_filter_scope: str = "Todos"
    audit_filter_event: str = "Todos"
    audit_filter_tenant: str = "Todos"
    audit_filter_user: str = "Todos"
    audit_expanded_event_ids: list[str] = []

    new_user_name: str = ""
    new_user_email: str = ""
    new_user_password: str = ""
    new_user_role: str = "sem_acesso"
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
    new_tenant_assigned_client_ids: list[str] = []
    new_tenant_assigned_clients_open: bool = False
    editing_tenant_id: str = ""

    new_role_name: str = ""
    new_role_permissions: str = ""
    new_role_responsibilities: str = ""
    role_permission_module_filter: str = "Todos"
    role_permission_choice: str = "create:users"
    last_reset_user_password: str = ""
    permissions_tab: str = "governanca"
    editing_role_id: str = ""
    editing_role_template_key: str = ""
    editing_role_template_origin: str = ""

    new_resp_role_id: str = ""
    new_resp_desc: str = ""
    editing_resp_id: str = ""

    new_form_name: str = ""
    new_form_category: str = "Diagnóstico Cultura de Segurança"
    new_form_custom_category: str = ""
    new_form_stage: str = "Visita Técnica - Guiada"
    new_form_custom_stage: str = ""
    new_form_target_client_id: str = ""
    new_form_target_user_email: str = ""
    selected_form_id: str = ""
    editing_form_id: str = ""
    editing_question_id: str = ""
    new_interview_form_id: str = ""
    new_interview_project_id: str = ""
    new_interview_client_id: str = ""
    new_interview_user_id: str = ""
    new_interview_area: str = ""
    new_interview_group_name: str = ""
    new_interview_date: str = ""
    new_interview_notes: str = ""
    interview_draft_active: bool = False
    editing_interview_id: str = ""
    editing_interview_table_id: str = ""
    edit_interview_form_id: str = ""
    edit_interview_project_id: str = ""
    edit_interview_client_id: str = ""
    edit_interview_date: str = ""
    edit_interview_status: str = "em_andamento"
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
    new_project_service_name: str = "Diagnóstico Cultura de Segurança"
    new_project_custom_service_name: str = ""
    new_project_client_id: str = ""
    new_project_contracted_at: str = ""
    editing_project_id: str = ""
    project_portfolio_service_filter: str = "Todos"
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
    new_box_owner: str = ""
    new_box_objective: str = ""
    new_box_trigger: str = ""
    new_box_expected_output: str = ""
    new_sticky_note_text: str = ""
    workflow_logs: list[str] = []

    new_action_title: str = ""
    new_action_owner: str = ""
    new_action_start_date: str = ""
    new_action_planned_due_date: str = ""
    new_action_due_date: str = ""
    new_action_expected_result: str = ""
    new_action_dimensions: str = ""
    new_action_area: str = ""
    new_action_dimension_ids: list[str] = []
    selected_action_plan_id: str = ""
    editing_action_plan_id: str = ""
    new_action_task_title: str = ""
    new_action_task_owner: str = ""
    new_action_task_start_date: str = ""
    new_action_task_planned_due_date: str = ""
    new_action_task_due_date: str = ""
    new_action_task_expected_result: str = ""
    new_action_task_progress: str = "0"
    draft_action_tasks: list[dict[str, str]] = []
    expanded_action_plan_ids: list[str] = []

    perm_user_email: str = ""
    perm_selected_module: str = "Todos"
    perm_selected_role_template: str = "smartlab_admin"
    new_dashboard_box_title: str = ""
    new_dashboard_box_kind: str = "kpi"
    new_dashboard_box_scope: str = "consultor"
    new_dashboard_box_source: str = "projetos"
    new_dashboard_box_description: str = ""

    testimonial_index: int = 0

    def set_dashboard_scope_mode(self, value: str):
        return DashboardStateMixin.set_dashboard_scope_mode(self, value)

    def set_dashboard_theme_tab(self, value: str):
        return DashboardStateMixin.set_dashboard_theme_tab(self, value)

    def set_dashboard_period_mode(self, value: str):
        return DashboardStateMixin.set_dashboard_period_mode(self, value)

    def set_dashboard_selected_project(self, value: str):
        return DashboardStateMixin.set_dashboard_selected_project(self, value)

    def set_dashboard_selected_client(self, value: str):
        return DashboardStateMixin.set_dashboard_selected_client(self, value)

    def set_dashboard_selected_service(self, value: str):
        return DashboardStateMixin.set_dashboard_selected_service(self, value)

    def set_dashboard_selected_department(self, value: str):
        return DashboardStateMixin.set_dashboard_selected_department(self, value)

    def set_dashboard_drill_key(self, value: str):
        return DashboardStateMixin.set_dashboard_drill_key(self, value)

    def prepare_ai_view(self):
        return AssistantStateMixin.prepare_ai_view(self)

    @rx.var(cache=False)
    def dashboard_boxes_data(self) -> list[dict[str, Any]]:
        return super().dashboard_boxes_data

    @rx.var(cache=False)
    def dashboard_scope_options(self) -> list[str]:
        return super().dashboard_scope_options

    @rx.var(cache=False)
    def dashboard_period_options(self) -> list[str]:
        return super().dashboard_period_options

    @rx.var(cache=False)
    def dashboard_project_options(self) -> list[str]:
        return super().dashboard_project_options

    @rx.var(cache=False)
    def dashboard_selected_project_option(self) -> str:
        return super().dashboard_selected_project_option

    @rx.var(cache=False)
    def dashboard_client_options(self) -> list[str]:
        return super().dashboard_client_options

    @rx.var(cache=False)
    def dashboard_selected_client_option(self) -> str:
        return super().dashboard_selected_client_option

    @rx.var(cache=False)
    def dashboard_service_options(self) -> list[str]:
        return super().dashboard_service_options

    @rx.var(cache=False)
    def dashboard_scope_summary(self) -> dict[str, str]:
        return super().dashboard_scope_summary

    @rx.var(cache=False)
    def dashboard_filter_summary(self) -> dict[str, str]:
        return super().dashboard_filter_summary

    @rx.var(cache=False)
    def dashboard_department_options(self) -> list[str]:
        return super().dashboard_department_options

    @rx.var(cache=False)
    def dashboard_workspace_rollup(self) -> list[dict[str, str]]:
        return super().dashboard_workspace_rollup

    @rx.var(cache=False)
    def dashboard_dimension_compare_data(self) -> list[dict[str, str | float]]:
        return super().dashboard_dimension_compare_data

    @rx.var(cache=False)
    def dashboard_dimension_cards(self) -> list[dict[str, str]]:
        return super().dashboard_dimension_cards

    @rx.var(cache=False)
    def dashboard_diagnosis_cards(self) -> list[dict[str, str]]:
        return super().dashboard_diagnosis_cards

    @rx.var(cache=False)
    def dashboard_diagnosis_chart_data(self) -> list[dict[str, str | float]]:
        return super().dashboard_diagnosis_chart_data

    @rx.var(cache=False)
    def dashboard_executive_cards(self) -> list[dict[str, str]]:
        return super().dashboard_executive_cards

    @rx.var(cache=False)
    def dashboard_operational_cards(self) -> list[dict[str, str]]:
        return super().dashboard_operational_cards

    @rx.var(cache=False)
    def dashboard_operational_chart_data(self) -> list[dict[str, str | int]]:
        return super().dashboard_operational_chart_data

    @rx.var(cache=False)
    def dashboard_engagement_cards(self) -> list[dict[str, str]]:
        return super().dashboard_engagement_cards

    @rx.var(cache=False)
    def dashboard_engagement_chart_data(self) -> list[dict[str, str | int]]:
        return super().dashboard_engagement_chart_data

    @rx.var(cache=False)
    def dashboard_projects_cards(self) -> list[dict[str, str]]:
        return super().dashboard_projects_cards

    @rx.var(cache=False)
    def dashboard_projects_chart_data(self) -> list[dict[str, str | int]]:
        return super().dashboard_projects_chart_data

    @rx.var(cache=False)
    def dashboard_executive_timeline_data(self) -> list[dict[str, str | float]]:
        return super().dashboard_executive_timeline_data

    @rx.var(cache=False)
    def dashboard_projects_timeline_data(self) -> list[dict[str, str | int]]:
        return super().dashboard_projects_timeline_data

    @rx.var(cache=False)
    def dashboard_builder_preview(self) -> list[dict[str, str]]:
        return super().dashboard_builder_preview

    @rx.var(cache=False)
    def dashboard_metrics(self) -> dict[str, str]:
        return super().dashboard_metrics

    @rx.var(cache=False)
    def dashboard_table(self) -> list[dict[str, str]]:
        return super().dashboard_table

    @rx.var(cache=False)
    def dashboard_detail_title(self) -> str:
        return super().dashboard_detail_title

    @rx.var(cache=False)
    def dashboard_detail_rows(self) -> list[dict[str, str]]:
        return super().dashboard_detail_rows

    def _append_audit_entry(self, event: str, detail: str, scope: str = "info", extra: dict[str, str] | None = None):
        entry = {
            "timestamp": _format_display_datetime(_now_brasilia(), include_seconds=True),
            "event": event,
            "detail": detail,
            "scope": scope,
            "tenant": self.current_tenant,
            "user": self.login_email.strip().lower() or "anonimo",
            "view": self.active_view,
        }
        if extra:
            entry.update({str(key): str(value) for key, value in extra.items()})
        _append_audit_file(entry)

    def _catalog_options(self, catalog_key: str) -> list[str]:
        tenant_id = _catalog_tenant_for_key(self.current_tenant, catalog_key)
        session = SessionLocal()
        rows = (
            session.query(CustomOptionModel.option_value)
            .filter(
                CustomOptionModel.tenant_id == tenant_id,
                CustomOptionModel.catalog_key == catalog_key,
            )
            .order_by(CustomOptionModel.option_value.asc())
            .all()
        )
        session.close()
        values: list[str] = []
        seen: set[str] = set()
        for row in rows:
            raw = str(row[0] or "").strip()
            if not raw:
                continue
            normalized = raw.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            values.append(raw)
        return values

    def _register_catalog_option(self, catalog_key: str, raw_value: str) -> str:
        value = str(raw_value or "").strip()
        if not value:
            return ""
        tenant_id = _catalog_tenant_for_key(self.current_tenant, catalog_key)
        session = SessionLocal()
        existing_rows = (
            session.query(CustomOptionModel)
            .filter(
                CustomOptionModel.tenant_id == tenant_id,
                CustomOptionModel.catalog_key == catalog_key,
            )
            .all()
        )
        existing = next(
            (
                row
                for row in existing_rows
                if str(row.option_value or "").strip().casefold() == value.casefold()
            ),
            None,
        )
        if existing is None:
            session.add(
                CustomOptionModel(
                    tenant_id=tenant_id,
                    catalog_key=catalog_key,
                    option_value=value,
                )
            )
            session.commit()
        else:
            value = str(existing.option_value or "").strip() or value
        session.close()
        return value

    def _group_tenant_ids_for_tenant(self, session, tenant_id: str) -> set[str]:
        tenant_value = str(tenant_id or "").strip() or self.current_tenant
        group_tenants = {tenant_value}
        tenant_row = session.query(TenantModel).filter(TenantModel.id == tenant_value).first()
        owner_client_id = int(tenant_row.owner_client_id) if tenant_row and tenant_row.owner_client_id is not None else None
        if owner_client_id is None:
            return group_tenants
        client_pairs = [
            ClientModel(id=row[0], parent_client_id=row[1])  # type: ignore[call-arg]
            for row in session.query(ClientModel.id, ClientModel.parent_client_id).all()
        ]
        children_map = _build_client_children_map(client_pairs)
        group_client_ids = {owner_client_id, *_collect_descendant_client_ids(children_map, owner_client_id)}
        for row in session.query(TenantModel.id, TenantModel.owner_client_id).all():
            row_client_id = int(row[1]) if row[1] is not None else None
            if row_client_id is not None and row_client_id in group_client_ids:
                group_tenants.add(str(row[0]))
        return group_tenants

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
        return [self._workspace_label(str(row.id), str(row.name or "")) for row in rows]

    @rx.var(cache=False)
    def current_tenant_display(self) -> str:
        session = SessionLocal()
        tenant = session.query(TenantModel).filter(TenantModel.id == self.current_tenant).first()
        session.close()
        if not tenant:
            return self.current_tenant
        return self._workspace_label(str(tenant.id), str(tenant.name or ""))

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
                            "view": "permissoes",
                            "record_id": str(row.id),
                        }
                    )

        session.close()
        return results[:8]

    @rx.var
    def can_manage_clients(self) -> bool:
        return super().can_manage_clients

    @rx.var
    def can_manage_users(self) -> bool:
        return super().can_manage_users

    @rx.var
    def can_delete_users(self) -> bool:
        return super().can_delete_users

    @rx.var
    def can_reset_user_password(self) -> bool:
        return super().can_reset_user_password

    @rx.var
    def can_delete_clients(self) -> bool:
        return super().can_delete_clients

    @rx.var
    def can_manage_tenants(self) -> bool:
        return super().can_manage_tenants

    @rx.var
    def can_delete_tenants(self) -> bool:
        return super().can_delete_tenants

    @rx.var
    def can_manage_roles(self) -> bool:
        return super().can_manage_roles

    @rx.var
    def can_delete_roles(self) -> bool:
        return super().can_delete_roles

    @rx.var
    def can_manage_global_role_templates(self) -> bool:
        return super().can_manage_global_role_templates

    @rx.var
    def can_manage_resps(self) -> bool:
        return super().can_manage_resps

    @rx.var
    def can_delete_resps(self) -> bool:
        return super().can_delete_resps

    @rx.var
    def can_manage_forms(self) -> bool:
        return super().can_manage_forms

    @rx.var
    def can_delete_forms(self) -> bool:
        return super().can_delete_forms

    @rx.var
    def can_operate_interviews(self) -> bool:
        return super().can_operate_interviews

    @rx.var
    def show_menu_clients(self) -> bool:
        return super().show_menu_clients

    @rx.var
    def show_menu_tenants(self) -> bool:
        return super().show_menu_tenants

    @rx.var
    def show_menu_users(self) -> bool:
        return super().show_menu_users

    @rx.var
    def show_menu_permissions(self) -> bool:
        return super().show_menu_permissions

    @rx.var
    def show_menu_dashboard(self) -> bool:
        return super().show_menu_dashboard

    @rx.var
    def show_menu_projects(self) -> bool:
        return super().show_menu_projects

    @rx.var
    def show_menu_plans(self) -> bool:
        return super().show_menu_plans

    @rx.var
    def show_menu_apis(self) -> bool:
        return super().show_menu_apis

    @rx.var
    def show_menu_roles(self) -> bool:
        return super().show_menu_roles

    @rx.var
    def show_menu_responsibilities(self) -> bool:
        return super().show_menu_responsibilities

    @rx.var
    def show_menu_forms(self) -> bool:
        return super().show_menu_forms

    @rx.var
    def show_menu_ai(self) -> bool:
        return super().show_menu_ai

    @rx.var
    def show_menu_audit(self) -> bool:
        return super().show_menu_audit

    @rx.var
    def has_platform_access(self) -> bool:
        return super().has_platform_access

    def _current_permission_set(self) -> set[str]:
        return AccessStateMixin._current_permission_set(self)

    def has_perm(self, perm: str) -> bool:
        return AccessStateMixin.has_perm(self, perm)

    def _workspace_label(self, tenant_id: str, tenant_name: str = "") -> str:
        return AccessStateMixin._workspace_label(self, tenant_id, tenant_name)

    def _permission_overrides_for(self, user_email: str, tenant_id: str) -> dict[str, str]:
        return AccessStateMixin._permission_overrides_for(self, user_email, tenant_id)

    def _resource_allowed_from_profile(
        self,
        resource: str,
        role_name: str,
        user_scope: str,
        tenant_id: str,
        perm_set: set[str],
    ) -> bool:
        return AccessStateMixin._resource_allowed_from_profile(
            self, resource, role_name, user_scope, tenant_id, perm_set
        )

    def _role_permission_set_for_user(self, role_name: str, tenant_id: str) -> set[str]:
        return AccessStateMixin._role_permission_set_for_user(self, role_name, tenant_id)

    def _effective_permission_decisions_for(
        self,
        user_email: str,
        role_name: str,
        user_scope: str,
        tenant_id: str,
    ) -> dict[str, str]:
        return AccessStateMixin._effective_permission_decisions_for(
            self, user_email, role_name, user_scope, tenant_id
        )

    def _current_user_permission_decisions(self) -> dict[str, str]:
        return AccessStateMixin._current_user_permission_decisions(self)

    def _is_resource_allowed(self, resource: str) -> bool:
        return AccessStateMixin._is_resource_allowed(self, resource)

    @rx.var(cache=False)
    def tenants_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        query = session.query(TenantModel)
        if self.user_scope == "cliente" and self.home_tenant_id:
            query = query.filter(TenantModel.id == self.home_tenant_id)
        rows = query.order_by(TenantModel.created_at.desc()).all()
        client_lookup = {row[0]: row[1] for row in session.query(ClientModel.id, ClientModel.name).all()}
        client_cnpj_lookup = {row[0]: row[1] or "-" for row in session.query(ClientModel.id, ClientModel.cnpj).all()}
        document_counts: dict[str, int] = {}
        for row in session.query(AssistantDocumentModel.tenant_id).all():
            document_counts[row[0]] = document_counts.get(row[0], 0) + 1
        project_counts: dict[str, int] = {}
        for row in session.query(ProjectModel.tenant_id).all():
            project_counts[row[0]] = project_counts.get(row[0], 0) + 1
        form_counts: dict[str, int] = {}
        for row in session.query(FormModel.tenant_id).all():
            form_counts[row[0]] = form_counts.get(row[0], 0) + 1
        data = [
            {
                "id": r.id,
                "id_key": str(r.id),
                "name": r.name,
                "slug": r.slug,
                "limit": r.limit_users,
                "owner_client_id": str(r.owner_client_id) if r.owner_client_id is not None else "-",
                "owner_client_name": client_lookup.get(r.owner_client_id, "SmartLab"),
                "owner_client_cnpj": client_cnpj_lookup.get(r.owner_client_id, "-"),
                "created_at": _format_display_date(r.created_at),
                "document_count": str(document_counts.get(r.id, 0)),
                "project_count": str(project_counts.get(r.id, 0)),
                "form_count": str(form_counts.get(r.id, 0)),
                "client_scope_count": str(len([item for item in _loads_json(r.assigned_client_ids, []) if str(item).isdigit()])),
                "client_scope_summary": (
                    "default: acesso total"
                    if r.id == "default"
                    else ", ".join(
                        client_lookup.get(int(item), str(item))
                        for item in _loads_json(r.assigned_client_ids, [])
                        if str(item).isdigit()
                    ) or client_lookup.get(r.owner_client_id, "Cliente principal")
                ),
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var
    def ollama_models_data(self) -> list[dict[str, str]]:
        return super().ollama_models_data

    @rx.var
    def ai_model_options(self) -> list[str]:
        return super().ai_model_options

    @rx.var
    def ai_selected_model_effective(self) -> str:
        return super().ai_selected_model_effective

    @rx.var
    def ai_runtime_status(self) -> dict[str, str]:
        return super().ai_runtime_status

    @rx.var
    def ai_resource_type_options(self) -> list[str]:
        return super().ai_resource_type_options

    @rx.var
    def ai_knowledge_scope_options(self) -> list[str]:
        return super().ai_knowledge_scope_options

    @rx.var
    def ai_knowledge_scope_effective(self) -> str:
        return super().ai_knowledge_scope_effective

    @rx.var
    def ai_scope_options(self) -> list[str]:
        return super().ai_scope_options

    @rx.var
    def ai_scope_mode_effective(self) -> str:
        return super().ai_scope_mode_effective

    @rx.var
    def ai_selected_project_label(self) -> str:
        return super().ai_selected_project_label

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
        return [self._workspace_label(str(row.id), str(row.name or "")) for row in rows]

    @rx.var
    def selected_new_user_workspace_option(self) -> str:
        if not self.new_user_tenant_id:
            return ""
        session = SessionLocal()
        tenant = session.query(TenantModel).filter(TenantModel.id == self.new_user_tenant_id).first()
        session.close()
        return self._workspace_label(str(tenant.id), str(tenant.name or "")) if tenant else self.new_user_tenant_id

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
    def selected_tenant_assigned_clients_summary(self) -> str:
        if self.new_tenant_slug == "default":
            return "default: acesso total e irrestrito"
        if not self.new_tenant_assigned_client_ids:
            return "Clique para escolher os clientes do tenant"
        names = [
            self.client_lookup.get(client_id, client_id)
            for client_id in self.new_tenant_assigned_client_ids
        ]
        expanded_count = len(self._expand_client_scope(self.new_tenant_assigned_client_ids))
        return f"{', '.join(names)} (escopo efetivo: {expanded_count} cliente(s))"

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
        catalog_options = self._catalog_options("business_sector")
        dynamic_options = sorted({option for option in [*custom_options, *catalog_options] if option not in base_options})
        return [*base_options, *dynamic_options, "Outro"]

    @rx.var
    def brazilian_state_options(self) -> list[str]:
        return BRAZILIAN_STATE_CODES

    @rx.var(cache=False)
    def form_target_client_options(self) -> list[str]:
        return super().form_target_client_options

    @rx.var(cache=False)
    def form_target_user_options(self) -> list[str]:
        return super().form_target_user_options

    @rx.var(cache=False)
    def question_dimension_options(self) -> list[str]:
        return super().question_dimension_options

    @rx.var
    def question_polarity_options(self) -> list[str]:
        return super().question_polarity_options

    @rx.var
    def question_weight_options(self) -> list[str]:
        return super().question_weight_options

    @rx.var
    def selected_form_target_client_option(self) -> str:
        return super().selected_form_target_client_option

    @rx.var(cache=False)
    def selected_form_target_user_option(self) -> str:
        return super().selected_form_target_user_option

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
    def is_editing_role_template(self) -> bool:
        return self.editing_role_template_key != ""

    @rx.var
    def is_editing_resp(self) -> bool:
        return self.editing_resp_id != ""

    @rx.var
    def resp_submit_label(self) -> str:
        return "Salvar Alterações" if self.is_editing_resp else "Adicionar"

    @rx.var
    def is_editing_form(self) -> bool:
        return super().is_editing_form

    @rx.var
    def form_submit_label(self) -> str:
        return super().form_submit_label

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

    @rx.var(cache=False)
    def profession_options(self) -> list[str]:
        base_options = ["Analista", "Motorista", "Coordenador", "Supervisor", "Gerente", "Diretor", "CEO"]
        session = SessionLocal()
        values = [
            str(row[0]).strip()
            for row in session.query(UserModel.profession)
            .filter(UserModel.profession.is_not(None))
            .all()
            if row[0] and str(row[0]).strip()
        ]
        session.close()
        catalog_options = self._catalog_options("user_profession")
        dynamic_options = sorted({option for option in [*values, *catalog_options] if option not in base_options})
        return [*base_options, *dynamic_options, "Outro"]

    @rx.var(cache=False)
    def department_options(self) -> list[str]:
        base_options = ["RH", "Operacao", "Logistica", "Vendas", "Marketing"]
        session = SessionLocal()
        values = [
            str(row[0]).strip()
            for row in session.query(UserModel.department)
            .filter(UserModel.department.is_not(None))
            .all()
            if row[0] and str(row[0]).strip()
        ]
        session.close()
        catalog_options = self._catalog_options("user_department")
        dynamic_options = sorted({option for option in [*values, *catalog_options] if option not in base_options})
        return [*base_options, *dynamic_options, "Outro"]

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
        return super().access_principal_options

    @rx.var(cache=False)
    def selected_access_principal(self) -> dict[str, str]:
        return super().selected_access_principal

    @rx.var(cache=False)
    def selected_access_responsibilities(self) -> list[str]:
        return super().selected_access_responsibilities

    @rx.var(cache=False)
    def has_valid_permission_principal(self) -> bool:
        return super().has_valid_permission_principal

    @rx.var(cache=False)
    def roles_data(self) -> list[dict[str, Any]]:
        return super().roles_data

    @rx.var
    def role_id_options(self) -> list[str]:
        return super().role_id_options

    @rx.var
    def role_permission_module_options(self) -> list[str]:
        return super().role_permission_module_options

    @rx.var(cache=False)
    def selected_role_permissions(self) -> list[str]:
        return super().selected_role_permissions

    @rx.var(cache=False)
    def selected_role_permissions_summary(self) -> str:
        return super().selected_role_permissions_summary

    @rx.var(cache=False)
    def selected_role_permission_details(self) -> list[dict[str, str]]:
        return super().selected_role_permission_details

    @rx.var(cache=False)
    def available_role_permission_choices(self) -> list[str]:
        return super().available_role_permission_choices

    @rx.var(cache=False)
    def selected_role_permission_catalog(self) -> list[dict[str, str]]:
        return super().selected_role_permission_catalog

    @rx.var(cache=False)
    def available_role_permissions_data(self) -> list[dict[str, str]]:
        return super().available_role_permissions_data

    @rx.var(cache=False)
    def chosen_role_permissions_data(self) -> list[dict[str, str]]:
        return super().chosen_role_permissions_data

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
        return super().forms_data

    @rx.var
    def form_id_options(self) -> list[str]:
        return super().form_id_options

    @rx.var(cache=False)
    def survey_builder_options(self) -> list[str]:
        return super().survey_builder_options

    @rx.var(cache=False)
    def interview_form_options(self) -> list[str]:
        return super().interview_form_options

    @rx.var
    def selected_form_name(self) -> str:
        return super().selected_form_name

    @rx.var
    def selected_survey_builder_option(self) -> str:
        return super().selected_survey_builder_option

    @rx.var(cache=False)
    def selected_interview_form_option(self) -> str:
        return super().selected_interview_form_option

    @rx.var(cache=False)
    def selected_interview_client_option(self) -> str:
        return super().selected_interview_client_option

    @rx.var(cache=False)
    def selected_interview_client_name(self) -> str:
        return super().selected_interview_client_name

    @rx.var(cache=False)
    def selected_interview_stage_name(self) -> str:
        return super().selected_interview_stage_name

    @rx.var(cache=False)
    def interview_inline_form_options(self) -> list[str]:
        return super().interview_inline_form_options

    @rx.var(cache=False)
    def selected_edit_interview_form_option(self) -> str:
        return super().selected_edit_interview_form_option

    @rx.var(cache=False)
    def selected_edit_interview_project_option(self) -> str:
        return super().selected_edit_interview_project_option

    @rx.var(cache=False)
    def selected_edit_interview_client_name(self) -> str:
        return super().selected_edit_interview_client_name

    @rx.var(cache=False)
    def selected_edit_interview_stage_name(self) -> str:
        return super().selected_edit_interview_stage_name

    @rx.var
    def interview_status_options(self) -> list[str]:
        return super().interview_status_options

    @rx.var(cache=False)
    def is_new_interview_leadership_stage(self) -> bool:
        return super().is_new_interview_leadership_stage

    @rx.var(cache=False)
    def is_new_interview_group_stage(self) -> bool:
        return super().is_new_interview_group_stage

    @rx.var(cache=False)
    def is_new_interview_visit_stage(self) -> bool:
        return super().is_new_interview_visit_stage

    @rx.var(cache=False)
    def interview_user_options(self) -> list[str]:
        return super().interview_user_options

    @rx.var(cache=False)
    def active_interview_client_id(self) -> str:
        return super().active_interview_client_id

    @rx.var(cache=False)
    def active_interview_user_options(self) -> list[str]:
        return super().active_interview_user_options

    @rx.var(cache=False)
    def selected_interview_user_option(self) -> str:
        return super().selected_interview_user_option

    @rx.var(cache=False)
    def interview_area_options(self) -> list[str]:
        return super().interview_area_options

    @rx.var(cache=False)
    def active_interview_area_options(self) -> list[str]:
        return super().active_interview_area_options

    @rx.var(cache=False)
    def selected_interview_area_option(self) -> str:
        return super().selected_interview_area_option

    @rx.var(cache=False)
    def active_interview_group_name(self) -> str:
        return super().active_interview_group_name

    @rx.var(cache=False)
    def active_interview_requires_user(self) -> bool:
        return super().active_interview_requires_user

    @rx.var(cache=False)
    def active_interview_is_group_stage(self) -> bool:
        return super().active_interview_is_group_stage

    @rx.var(cache=False)
    def active_interview_is_visit_stage(self) -> bool:
        return super().active_interview_is_visit_stage

    @rx.var(cache=False)
    def active_interview_context_ready(self) -> bool:
        return super().active_interview_context_ready

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
        survey_lookup = {
            str(row.id): {
                "name": row.name,
                "stage": row.stage_name or "Visita Técnica - Guiada",
            }
            for row in session.query(SurveyModel).filter(SurveyModel.tenant_id == self.current_tenant).all()
        }
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
                "survey_id": str(row.survey_id or ""),
                "project_id": str(row.project_id or ""),
                "client_id": str(row.client_id or ""),
                "form_name": survey_lookup.get(str(row.survey_id), {}).get("name", f"Pesquisa {row.survey_id or '-'}"),
                "stage_name": survey_lookup.get(str(row.survey_id), {}).get("stage", "-"),
                "project_name": project_lookup.get(str(row.project_id), "-") if row.project_id is not None else "-",
                "client_name": client_lookup.get(str(row.client_id), "-") if row.client_id is not None else "-",
                "interviewee_name": row.interviewee_name or "-",
                "interviewee_role": row.interviewee_role or "-",
                "interviewee_email": user_lookup.get(str(row.interviewee_user_id), {}).get("email", "-") if row.interviewee_user_id is not None else "-",
                "target_area": row.target_area or "-",
                "audience_group": row.audience_group or "-",
                "consultant_name": row.consultant_name or "-",
                "interview_date": _format_display_date(row.interview_date),
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
        if not self.selected_interview_id and self.interview_draft_active:
            stage_name = self.selected_interview_stage_name
            interviewee_name = "-"
            interviewee_role = "-"
            if stage_name == "Entrevista Individual com o Líder" and self.new_interview_user_id.isdigit():
                session = SessionLocal()
                row = (
                    session.query(UserModel.name, UserModel.email, UserModel.profession, UserModel.department)
                    .filter(UserModel.id == int(self.new_interview_user_id))
                    .first()
                )
                session.close()
                if row:
                    interviewee_name = row[0] or row[1] or "-"
                    interviewee_role = row[2] or row[3] or "-"
            elif stage_name in {"Rodas de Conversa", "Rodada de Conversa"}:
                interviewee_name = self.new_interview_group_name.strip() or "Grupo pendente"
                interviewee_role = self.new_interview_area.strip() or "Área pendente"
            elif stage_name == "Visita Técnica - Guiada":
                interviewee_name = f"Área: {self.new_interview_area.strip()}" if self.new_interview_area.strip() else "Área pendente"
                interviewee_role = "Observação em campo"
            return {
                "id": "",
                "survey_id": self.new_interview_form_id,
                "project_id": self.new_interview_project_id,
                "client_id": self.new_interview_client_id,
                "form_name": self.selected_interview_form_option or "Entrevista em preparação",
                "project_name": self.selected_interview_project_option.split(" - ", 1)[1] if " - " in self.selected_interview_project_option else "-",
                "client_name": self.selected_interview_client_name,
                "stage_name": stage_name,
                "interviewee_name": interviewee_name,
                "interviewee_role": interviewee_role,
                "interviewee_email": "-",
                "target_area": self.new_interview_area or "-",
                "audience_group": self.new_interview_group_name or "-",
                "consultant_name": self.login_email.strip().lower() or "-",
                "interview_date": _format_display_date(self.new_interview_date),
                "status": "rascunho",
                "responses": "0",
                "total_score": "0",
            }
        if not self.selected_interview_id:
            return {
                "id": "",
                "survey_id": "",
                "project_id": "",
                "client_id": "",
                "form_name": "Nenhuma entrevista selecionada",
                "project_name": "-",
                "client_name": "-",
                "stage_name": "-",
                "interviewee_name": "-",
                "interviewee_role": "-",
                "interviewee_email": "-",
                "target_area": "-",
                "audience_group": "-",
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
            "survey_id": "",
            "project_id": "",
            "client_id": "",
            "form_name": "Entrevista nao encontrada",
            "project_name": "-",
            "client_name": "-",
            "stage_name": "-",
            "interviewee_name": "-",
            "interviewee_role": "-",
            "interviewee_email": "-",
            "target_area": "-",
            "audience_group": "-",
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
                "id_key": str(r.id),
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
        survey_id = None
        if self.selected_interview_id.isdigit():
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
            survey_id = int(interview.survey_id or 0)
            response_rows = (
                session.query(ResponseModel)
                .filter(
                    ResponseModel.tenant_id == self.current_tenant,
                    ResponseModel.interview_id == interview.id,
                )
                .all()
            )
        elif self.interview_draft_active and self.new_interview_form_id.isdigit():
            session = SessionLocal()
            survey_id = int(self.new_interview_form_id)
            response_rows = []
        else:
            return []
        response_lookup = {int(row.question_id): row for row in response_rows}
        questions = (
            session.query(QuestionModel)
            .filter(
                QuestionModel.tenant_id == self.current_tenant,
                QuestionModel.survey_id == int(survey_id or 0),
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
            score_touched = str(question.id) in self.interview_score_touched_ids or stored_response is not None
            is_answered = "1" if score_touched else "0"
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
                    "is_answered": is_answered,
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
        return super().projects_data

    @rx.var
    def project_id_options(self) -> list[str]:
        return super().project_id_options

    @rx.var(cache=False)
    def project_portfolio_service_options(self) -> list[str]:
        return super().project_portfolio_service_options

    @rx.var(cache=False)
    def filtered_projects_data(self) -> list[dict[str, Any]]:
        return super().filtered_projects_data

    @rx.var(cache=False)
    def selected_project_option(self) -> str:
        return super().selected_project_option

    @rx.var
    def can_configure_projects(self) -> bool:
        return super().can_configure_projects

    @rx.var(cache=False)
    def smartlab_service_options(self) -> list[str]:
        return super().smartlab_service_options

    @rx.var
    def effective_new_form_service_name(self) -> str:
        return super().effective_new_form_service_name

    @rx.var
    def effective_new_project_service_name(self) -> str:
        return super().effective_new_project_service_name

    @rx.var(cache=False)
    def survey_stage_options(self) -> list[str]:
        return super().survey_stage_options

    @rx.var
    def effective_new_form_stage_name(self) -> str:
        return super().effective_new_form_stage_name

    @rx.var(cache=False)
    def project_client_options(self) -> list[str]:
        return super().project_client_options

    @rx.var
    def selected_project_client_option(self) -> str:
        return super().selected_project_client_option

    @rx.var
    def selected_project_assigned_clients_summary(self) -> str:
        return super().selected_project_assigned_clients_summary

    @rx.var(cache=False)
    def selected_project_source_tenant(self) -> str:
        return super().selected_project_source_tenant

    @rx.var
    def project_admin_tabs(self) -> list[str]:
        return super().project_admin_tabs

    @rx.var(cache=False)
    def selected_project_record(self) -> dict[str, str]:
        return super().selected_project_record

    @rx.var(cache=False)
    def interview_project_options(self) -> list[str]:
        return super().interview_project_options

    @rx.var(cache=False)
    def selected_interview_project_option(self) -> str:
        return super().selected_interview_project_option

    @rx.var
    def selected_project_plan_context(self) -> str:
        return super().selected_project_plan_context

    @rx.var(cache=False)
    def project_action_people(self) -> list[dict[str, str]]:
        return super().project_action_people

    @rx.var(cache=False)
    def project_action_area_options(self) -> list[str]:
        return super().project_action_area_options

    @rx.var(cache=False)
    def project_action_owner_options(self) -> list[str]:
        return super().project_action_owner_options

    @rx.var(cache=False)
    def action_dimension_options(self) -> list[str]:
        return super().action_dimension_options

    @rx.var
    def selected_action_dimensions_summary(self) -> str:
        return super().selected_action_dimensions_summary

    @rx.var(cache=False)
    def action_plan_options(self) -> list[str]:
        return super().action_plan_options

    @rx.var
    def selected_action_plan_option(self) -> str:
        return super().selected_action_plan_option

    @rx.var
    def effective_action_plan_target_id(self) -> str:
        return super().effective_action_plan_target_id

    @rx.var
    def effective_action_plan_target_label(self) -> str:
        return super().effective_action_plan_target_label

    @rx.var
    def selected_project_link_clients_summary(self) -> str:
        return super().selected_project_link_clients_summary

    @rx.var(cache=False)
    def workflow_hierarchy_snapshot(self) -> list[dict[str, str]]:
        return super().workflow_hierarchy_snapshot

    @rx.var(cache=False)
    def workflow_boxes_data(self) -> list[dict[str, Any]]:
        return super().workflow_boxes_data

    @rx.var(cache=False)
    def workflow_boxes_left(self) -> list[dict[str, Any]]:
        return super().workflow_boxes_left

    @rx.var(cache=False)
    def workflow_boxes_center(self) -> list[dict[str, Any]]:
        return super().workflow_boxes_center

    @rx.var(cache=False)
    def workflow_boxes_right(self) -> list[dict[str, Any]]:
        return super().workflow_boxes_right

    @rx.var(cache=False)
    def workflow_canvas_items(self) -> list[dict[str, Any]]:
        return super().workflow_canvas_items

    @rx.var(cache=False)
    def workflow_blueprint(self) -> list[dict[str, str]]:
        return super().workflow_blueprint

    @rx.var(cache=False)
    def workflow_sticky_notes(self) -> list[dict[str, Any]]:
        return super().workflow_sticky_notes

    def _workflow_stage_semantics(self, box: dict[str, Any]) -> dict[str, Any]:
        return ProjectStateMixin._workflow_stage_semantics(self, box)

    @rx.var(cache=False)
    def workflow_operational_stages(self) -> list[dict[str, Any]]:
        return super().workflow_operational_stages

    @rx.var(cache=False)
    def workflow_left_stages(self) -> list[dict[str, Any]]:
        return super().workflow_left_stages

    @rx.var(cache=False)
    def workflow_center_stages(self) -> list[dict[str, Any]]:
        return super().workflow_center_stages

    @rx.var(cache=False)
    def workflow_right_stages(self) -> list[dict[str, Any]]:
        return super().workflow_right_stages

    @rx.var(cache=False)
    def workflow_stage_summary(self) -> list[dict[str, str]]:
        return super().workflow_stage_summary

    @rx.var(cache=False)
    def workflow_stage_templates(self) -> list[dict[str, str]]:
        return super().workflow_stage_templates

    @rx.var(cache=False)
    def workflow_missing_stage_templates(self) -> list[dict[str, str]]:
        return super().workflow_missing_stage_templates

    def _parse_iso_date(self, raw_value: str | None) -> datetime | None:
        return ProjectStateMixin._parse_iso_date(self, raw_value)

    def _normalize_action_tasks(self, raw_tasks: list[dict[str, Any]] | Any) -> list[dict[str, Any]]:
        return ProjectStateMixin._normalize_action_tasks(self, raw_tasks)

    def _schedule_progress_percent(self, start_date: str, due_date: str) -> int:
        return ProjectStateMixin._schedule_progress_percent(self, start_date, due_date)

    def _action_progress_metrics(
        self,
        start_date: str,
        planned_due_date: str,
        due_date: str,
        tasks: list[dict[str, Any]],
        attainment: int,
        status: str,
        completed_at: str,
    ) -> dict[str, Any]:
        return ProjectStateMixin._action_progress_metrics(
            self, start_date, planned_due_date, due_date, tasks, attainment, status, completed_at
        )

    def _task_delay_label(self, planned_due_date: str, due_date: str, progress: int) -> str:
        return ProjectStateMixin._task_delay_label(self, planned_due_date, due_date, progress)

    @rx.var(cache=False)
    def action_plan_tasks_data(self) -> list[dict[str, Any]]:
        return super().action_plan_tasks_data

    @rx.var(cache=False)
    def action_plans_data(self) -> list[dict[str, Any]]:
        return super().action_plans_data

    @rx.var(cache=False)
    def action_plan_summary_cards(self) -> list[dict[str, str]]:
        return super().action_plan_summary_cards

    @rx.var(cache=False)
    def actions_todo(self) -> list[dict[str, Any]]:
        return super().actions_todo

    @rx.var(cache=False)
    def actions_doing(self) -> list[dict[str, Any]]:
        return super().actions_doing

    @rx.var(cache=False)
    def actions_done(self) -> list[dict[str, Any]]:
        return super().actions_done

    @rx.var(cache=False)
    def ai_documents_data(self) -> list[dict[str, str]]:
        return super().ai_documents_data

    @rx.var(cache=False)
    def ai_context_summary(self) -> dict[str, str]:
        return super().ai_context_summary

    @rx.var(cache=False)
    def ai_response_insights(self) -> dict[str, Any]:
        return super().ai_response_insights

    @rx.var
    def ai_source_snapshot(self) -> list[dict[str, str]]:
        return super().ai_source_snapshot

    def refresh_ai_recommendations(self):
        return AssistantStateMixin.refresh_ai_recommendations(self)

    def _project_option_for_id(self, project_id: str) -> str:
        return AssistantStateMixin._project_option_for_id(self, project_id)

    def _project_source_tenant_by_id(self, project_id: str) -> str:
        return AssistantStateMixin._project_source_tenant_by_id(self, project_id)

    def _action_plan_options_for_project(self, project_id: str) -> list[str]:
        return AssistantStateMixin._action_plan_options_for_project(self, project_id)

    @rx.var(cache=False)
    def ai_recommendation_cards_data(self) -> list[dict[str, Any]]:
        return super().ai_recommendation_cards_data

    @rx.var(cache=False)
    def ai_recommendation_active_action_plan_options(self) -> list[str]:
        return super().ai_recommendation_active_action_plan_options

    @rx.var
    def ai_history_data(self) -> list[dict[str, str]]:
        return super().ai_history_data

    @rx.var(cache=False)
    def audit_events_data(self) -> list[dict[str, str]]:
        return super().audit_events_data

    @rx.var
    def audit_scope_options(self) -> list[str]:
        return super().audit_scope_options

    @rx.var
    def audit_event_options(self) -> list[str]:
        return super().audit_event_options

    @rx.var
    def audit_tenant_options(self) -> list[str]:
        return super().audit_tenant_options

    @rx.var
    def audit_user_options(self) -> list[str]:
        return super().audit_user_options

    @rx.var
    def audit_filtered_events_data(self) -> list[dict[str, str]]:
        return super().audit_filtered_events_data

    @rx.var
    def audit_ai_events_data(self) -> list[dict[str, str]]:
        return super().audit_ai_events_data

    @rx.var
    def audit_system_events_data(self) -> list[dict[str, str]]:
        return super().audit_system_events_data

    @rx.var
    def audit_ai_summary(self) -> list[dict[str, str]]:
        return super().audit_ai_summary

    @rx.var
    def audit_overview_cards(self) -> list[dict[str, str]]:
        return super().audit_overview_cards

    @rx.var
    def audit_theme_summary(self) -> list[dict[str, str]]:
        return super().audit_theme_summary

    @rx.var
    def audit_grouped_sections(self) -> list[dict[str, Any]]:
        return super().audit_grouped_sections

    @rx.var
    def audit_log_path_display(self) -> str:
        return super().audit_log_path_display

    @rx.var(cache=False)
    def permission_boxes_data(self) -> list[dict[str, Any]]:
        return super().permission_boxes_data

    @rx.var
    def permission_module_options(self) -> list[str]:
        return super().permission_module_options

    @rx.var(cache=False)
    def permission_catalog(self) -> list[dict[str, str]]:
        return super().permission_catalog

    @rx.var
    def role_template_options(self) -> list[str]:
        return super().role_template_options

    @rx.var(cache=False)
    def custom_role_templates_data(self) -> list[dict[str, Any]]:
        return super().custom_role_templates_data

    @rx.var(cache=False)
    def custom_role_template_keys(self) -> list[str]:
        return super().custom_role_template_keys

    @rx.var
    def role_template_display_options(self) -> list[str]:
        return super().role_template_display_options

    @rx.var
    def selected_role_template_option(self) -> str:
        return super().selected_role_template_option

    @rx.var(cache=False)
    def role_templates_data(self) -> list[dict[str, Any]]:
        return super().role_templates_data

    @rx.var(cache=False)
    def selected_role_template_key(self) -> str:
        return super().selected_role_template_key

    @rx.var(cache=False)
    def selected_role_template_data(self) -> dict[str, Any]:
        return super().selected_role_template_data

    @rx.var(cache=False)
    def permission_decision_map(self) -> dict[str, str]:
        return super().permission_decision_map

    @rx.var(cache=False)
    def permission_canvas_available(self) -> list[dict[str, str]]:
        return super().permission_canvas_available

    @rx.var(cache=False)
    def permission_canvas_allowed(self) -> list[dict[str, str]]:
        return super().permission_canvas_allowed

    @rx.var(cache=False)
    def permission_canvas_denied(self) -> list[dict[str, str]]:
        return super().permission_canvas_denied

    @rx.var(cache=False)
    def permission_summary(self) -> dict[str, str]:
        return super().permission_summary

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
        self.dashboard_scope_mode = "tenant"
        self.dashboard_period_mode = "Todo período"
        self.dashboard_selected_project_id = "Todos"
        self.dashboard_selected_client_id = "Todos"
        self.dashboard_selected_service_name = "Todos"
        self.dashboard_selected_department = "Todos"
        self.dashboard_drill_key = ""
        self.hydrate_tenant_context()
        if not self.show_menu_projects and self.active_view == "projetos":
            self.active_view = "dashboard"
        self.ai_history = []
        self.ai_answer = ""
        self.ai_prompt = ""
        self.load_ai_history()
        self._append_audit_entry("tenant.switch", f"Contexto alterado para tenant {value}", "security")

    def switch_tenant_from_display(self, value: str):
        session = SessionLocal()
        query = session.query(TenantModel)
        if self.user_scope == "cliente" and self.home_tenant_id:
            query = query.filter(TenantModel.id == self.home_tenant_id)
        rows = query.order_by(TenantModel.name.asc()).all()
        session.close()
        for row in rows:
            label = self._workspace_label(str(row.id), str(row.name or ""))
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
        return AdminStateMixin.set_new_client_name(self, value)

    def set_new_client_trade_name(self, value: str):
        return AdminStateMixin.set_new_client_trade_name(self, value)

    def set_new_client_email(self, value: str):
        return AdminStateMixin.set_new_client_email(self, value)

    def set_new_client_phone(self, value: str):
        return AdminStateMixin.set_new_client_phone(self, value)

    def set_new_client_address(self, value: str):
        return AdminStateMixin.set_new_client_address(self, value)

    def set_new_client_state_code(self, value: str):
        return AdminStateMixin.set_new_client_state_code(self, value)

    def set_new_client_cnpj(self, value: str):
        return AdminStateMixin.set_new_client_cnpj(self, value)

    def set_new_client_business_sector(self, value: str):
        return AdminStateMixin.set_new_client_business_sector(self, value)

    def set_new_client_custom_business_sector(self, value: str):
        return AdminStateMixin.set_new_client_custom_business_sector(self, value)

    def confirm_new_client_business_sector(self):
        return AdminStateMixin.confirm_new_client_business_sector(self)

    def set_new_client_employee_count(self, value: str):
        return AdminStateMixin.set_new_client_employee_count(self, value)

    def set_new_client_branch_count(self, value: str):
        return AdminStateMixin.set_new_client_branch_count(self, value)

    def set_new_client_annual_revenue(self, value: str):
        return AdminStateMixin.set_new_client_annual_revenue(self, value)

    def set_new_client_parent_option(self, value: str):
        return AdminStateMixin.set_new_client_parent_option(self, value)

    def set_new_user_name(self, value: str):
        return AdminStateMixin.set_new_user_name(self, value)

    def set_new_user_email(self, value: str):
        return AdminStateMixin.set_new_user_email(self, value)

    def set_new_user_password(self, value: str):
        return AdminStateMixin.set_new_user_password(self, value)

    def set_new_user_role(self, value: str):
        return AdminStateMixin.set_new_user_role(self, value)

    def set_new_user_scope(self, value: str):
        return AdminStateMixin.set_new_user_scope(self, value)

    def set_new_user_profession(self, value: str):
        return AdminStateMixin.set_new_user_profession(self, value)

    def set_new_user_custom_profession(self, value: str):
        return AdminStateMixin.set_new_user_custom_profession(self, value)

    def confirm_new_user_profession(self):
        return AdminStateMixin.confirm_new_user_profession(self)

    def set_new_user_department(self, value: str):
        return AdminStateMixin.set_new_user_department(self, value)

    def set_new_user_client_option(self, value: str):
        return AdminStateMixin.set_new_user_client_option(self, value)

    def set_new_user_reports_to_user_option(self, value: str):
        return AdminStateMixin.set_new_user_reports_to_user_option(self, value)

    def set_new_user_workspace_option(self, value: str):
        return AdminStateMixin.set_new_user_workspace_option(self, value)

    def toggle_new_user_assigned_client(self, client_id: str):
        return AdminStateMixin.toggle_new_user_assigned_client(self, client_id)

    def set_new_user_custom_department(self, value: str):
        return AdminStateMixin.set_new_user_custom_department(self, value)

    def confirm_new_user_department(self):
        return AdminStateMixin.confirm_new_user_department(self)

    def toggle_new_user_assigned_clients_open(self):
        return AdminStateMixin.toggle_new_user_assigned_clients_open(self)

    def reset_client_form(self):
        return AdminStateMixin.reset_client_form(self)

    def reset_user_form(self):
        return AdminStateMixin.reset_user_form(self)

    def reset_tenant_form(self):
        return AdminStateMixin.reset_tenant_form(self)

    def reset_role_form(self):
        return AdminStateMixin.reset_role_form(self)

    def reset_resp_form(self):
        return AdminStateMixin.reset_resp_form(self)

    def reset_form_builder(self):
        return FormStateMixin.reset_form_builder(self)

    def reset_interview_form(self):
        return FormStateMixin.reset_interview_form(self)

    def start_edit_client(self, client_id: int):
        return AdminStateMixin.start_edit_client(self, client_id)

    def start_edit_user(self, user_id: int):
        return AdminStateMixin.start_edit_user(self, user_id)

    def start_edit_tenant(self, tenant_id: str):
        return AdminStateMixin.start_edit_tenant(self, tenant_id)

    def start_edit_role(self, role_id: int):
        return AdminStateMixin.start_edit_role(self, role_id)

    def start_edit_role_template(self, role_key: str):
        target = next((item for item in self.role_templates_data if item["key"] == role_key), None)
        if not target:
            self.toast_message = "Template RBAC nao encontrado"
            self.toast_type = "error"
            return
        if not bool(target.get("can_edit")):
            self.toast_message = "Sem permissao para editar esta linha"
            self.toast_type = "error"
            return
        self.editing_role_template_key = str(target["key"])
        self.editing_role_template_origin = str(target.get("origin", "tenant"))
        self.editing_role_id = str(target.get("id", "") or "")
        self.new_role_name = str(target["label"] if target.get("origin") == "global" else target["key"])
        self.new_role_permissions = ", ".join(target.get("permissions", []))
        responsibilities_str = str(target.get("responsibilities_str", "-"))
        self.new_role_responsibilities = "" if responsibilities_str == "-" else responsibilities_str
        self.role_permission_module_filter = "Todos"
        available = self.available_role_permission_choices
        self.role_permission_choice = available[0] if available else ""

    def save_role_template_row(self):
        if not self.can_manage_roles:
            self.toast_message = "Sem permissão para salvar papéis"
            self.toast_type = "error"
            return
        role_key = self.editing_role_template_key.strip()
        role_origin = self.editing_role_template_origin.strip() or "tenant"
        if not role_key:
            self.create_role()
            return
        perms = sorted({p.strip() for p in self.new_role_permissions.split(",") if p.strip()})
        responsibilities = [
            line.strip()
            for line in self.new_role_responsibilities.splitlines()
            if line.strip()
        ]
        if not perms:
            self.toast_message = "Selecione pelo menos uma permissao para o papel"
            self.toast_type = "error"
            return
        session = SessionLocal()
        if role_origin == "global":
            if not self.can_manage_global_role_templates:
                session.close()
                self.toast_message = "Apenas perfis autorizados no workspace default podem alterar este template"
                self.toast_type = "error"
                return
            row = (
                session.query(RoleModel)
                .filter(RoleModel.tenant_id == "default", RoleModel.name == role_key)
                .first()
            )
            if not row:
                row = RoleModel(
                    tenant_id="default",
                    name=role_key,
                    permissions=json.dumps(perms),
                )
                session.add(row)
                session.flush()
            else:
                row.permissions = json.dumps(perms)
            role_id = int(row.id)
            target_tenant = "default"
        else:
            role_name = self.new_role_name.strip() or role_key
            if role_name in ROLE_TEMPLATE_OPTION_KEYS:
                session.close()
                self.toast_message = "Esse nome e reservado para templates globais da SmartLab"
                self.toast_type = "error"
                return
            if self.editing_role_id.isdigit():
                row = (
                    session.query(RoleModel)
                    .filter(RoleModel.id == int(self.editing_role_id), RoleModel.tenant_id == self.current_tenant)
                    .first()
                )
                if not row:
                    session.close()
                    self.toast_message = "Papel nao encontrado para edicao"
                    self.toast_type = "error"
                    return
                duplicate = (
                    session.query(RoleModel.id)
                    .filter(
                        RoleModel.tenant_id == self.current_tenant,
                        RoleModel.name == role_name,
                        RoleModel.id != int(self.editing_role_id),
                    )
                    .first()
                )
                if duplicate:
                    session.close()
                    self.toast_message = "Ja existe um papel com esse nome neste tenant"
                    self.toast_type = "error"
                    return
                row.name = role_name
                row.permissions = json.dumps(perms)
            else:
                duplicate = (
                    session.query(RoleModel.id)
                    .filter(
                        RoleModel.tenant_id == self.current_tenant,
                        RoleModel.name == role_name,
                    )
                    .first()
                )
                if duplicate:
                    session.close()
                    self.toast_message = "Ja existe um papel com esse nome neste tenant"
                    self.toast_type = "error"
                    return
                row = RoleModel(
                    tenant_id=self.current_tenant,
                    name=role_name,
                    permissions=json.dumps(perms),
                )
                session.add(row)
                session.flush()
            role_id = int(row.id)
            target_tenant = self.current_tenant
        (
            session.query(ResponsibilityModel)
            .filter(
                ResponsibilityModel.tenant_id == target_tenant,
                ResponsibilityModel.role_id == role_id,
            )
            .delete()
        )
        for description in responsibilities:
            session.add(
                ResponsibilityModel(
                    tenant_id=target_tenant,
                    role_id=role_id,
                    description=description,
                )
            )
        session.commit()
        session.close()
        self.reset_role_form()
        self.toast_message = "Template RBAC atualizado"
        self.toast_type = "success"

    def start_edit_responsibility(self, resp_id: int):
        return AdminStateMixin.start_edit_responsibility(self, resp_id)

    def start_edit_form(self, form_id: int):
        return FormStateMixin.start_edit_form(self, form_id)

    def start_edit_question(self, question_id: int):
        return FormStateMixin.start_edit_question(self, question_id)

    def delete_question(self, question_id: int):
        return FormStateMixin.delete_question(self, question_id)

    def cancel_edit_question(self):
        return FormStateMixin.cancel_edit_question(self)

    def set_new_tenant_name(self, value: str):
        return AdminStateMixin.set_new_tenant_name(self, value)

    def set_new_tenant_slug(self, value: str):
        return AdminStateMixin.set_new_tenant_slug(self, value)

    def set_new_tenant_limit(self, value: str):
        return AdminStateMixin.set_new_tenant_limit(self, value)

    def set_new_role_name(self, value: str):
        return AdminStateMixin.set_new_role_name(self, value)

    def set_new_role_permissions(self, value: str):
        return AdminStateMixin.set_new_role_permissions(self, value)

    def set_new_role_responsibilities(self, value: str):
        return AdminStateMixin.set_new_role_responsibilities(self, value)

    def set_role_permission_module_filter(self, value: str):
        return AdminStateMixin.set_role_permission_module_filter(self, value)

    def set_role_permission_choice(self, value: str):
        return AdminStateMixin.set_role_permission_choice(self, value)

    def add_role_permission_choice(self):
        return AdminStateMixin.add_role_permission_choice(self)

    def add_role_permission_token(self, token: str):
        return AdminStateMixin.add_role_permission_token(self, token)

    def remove_role_permission_choice(self, token: str):
        return AdminStateMixin.remove_role_permission_choice(self, token)

    def set_new_resp_role_id(self, value: str):
        return AdminStateMixin.set_new_resp_role_id(self, value)

    def set_new_resp_desc(self, value: str):
        return AdminStateMixin.set_new_resp_desc(self, value)

    def set_new_form_name(self, value: str):
        return FormStateMixin.set_new_form_name(self, value)

    def set_new_form_stage(self, value: str):
        return FormStateMixin.set_new_form_stage(self, value)

    def set_new_form_custom_stage(self, value: str):
        return FormStateMixin.set_new_form_custom_stage(self, value)

    def confirm_new_form_stage(self):
        return FormStateMixin.confirm_new_form_stage(self)

    def set_new_form_category(self, value: str):
        return FormStateMixin.set_new_form_category(self, value)

    def set_new_form_custom_category(self, value: str):
        return FormStateMixin.set_new_form_custom_category(self, value)

    def confirm_new_form_category(self):
        return FormStateMixin.confirm_new_form_category(self)

    def set_new_form_target_client_option(self, value: str):
        return FormStateMixin.set_new_form_target_client_option(self, value)

    def set_new_form_target_user_option(self, value: str):
        return FormStateMixin.set_new_form_target_user_option(self, value)

    def set_new_interview_form_option(self, value: str):
        return FormStateMixin.set_new_interview_form_option(self, value)

    def set_new_interview_project_option(self, value: str):
        return FormStateMixin.set_new_interview_project_option(self, value)

    def set_new_interview_date(self, value: str):
        return FormStateMixin.set_new_interview_date(self, value)

    def set_new_interview_user_option(self, value: str):
        return FormStateMixin.set_new_interview_user_option(self, value)

    def set_new_interview_area(self, value: str):
        return FormStateMixin.set_new_interview_area(self, value)

    def set_new_interview_group_name(self, value: str):
        return FormStateMixin.set_new_interview_group_name(self, value)

    def set_edit_interview_form_option(self, value: str):
        return FormStateMixin.set_edit_interview_form_option(self, value)

    def set_edit_interview_project_option(self, value: str):
        return FormStateMixin.set_edit_interview_project_option(self, value)

    def set_edit_interview_date(self, value: str):
        return FormStateMixin.set_edit_interview_date(self, value)

    def set_edit_interview_status(self, value: str):
        return FormStateMixin.set_edit_interview_status(self, value)

    def set_new_interview_notes(self, value: str):
        return FormStateMixin.set_new_interview_notes(self, value)

    def set_new_question_text(self, value: str):
        return FormStateMixin.set_new_question_text(self, value)

    def set_new_question_type(self, value: str):
        return FormStateMixin.set_new_question_type(self, value)

    def set_new_question_dimension(self, value: str):
        return FormStateMixin.set_new_question_dimension(self, value)

    def set_new_question_custom_dimension(self, value: str):
        return FormStateMixin.set_new_question_custom_dimension(self, value)

    def confirm_new_question_dimension(self):
        return FormStateMixin.confirm_new_question_dimension(self)

    def set_new_question_weight(self, value: str):
        return FormStateMixin.set_new_question_weight(self, value)

    def set_new_question_polarity(self, value: str):
        return FormStateMixin.set_new_question_polarity(self, value)

    def set_new_question_options(self, value: str):
        return FormStateMixin.set_new_question_options(self, value)

    def set_new_question_condition(self, value: str):
        return FormStateMixin.set_new_question_condition(self, value)

    def set_interview_answer(self, question_id: str, value: str):
        return FormStateMixin.set_interview_answer(self, question_id, value)

    def set_interview_score(self, question_id: str, value: str):
        return FormStateMixin.set_interview_score(self, question_id, value)

    def set_ai_prompt(self, value: str):
        return AssistantStateMixin.set_ai_prompt(self, value)

    def set_ai_selected_model(self, value: str):
        return AssistantStateMixin.set_ai_selected_model(self, value)

    def set_ai_resource_type(self, value: str):
        return AssistantStateMixin.set_ai_resource_type(self, value)

    def set_ai_knowledge_scope(self, value: str):
        return AssistantStateMixin.set_ai_knowledge_scope(self, value)

    def set_ai_scope_mode(self, value: str):
        return AssistantStateMixin.set_ai_scope_mode(self, value)

    def _update_ai_recommendation_field(self, recommendation_id: str, field_name: str, value: str):
        return AssistantStateMixin._update_ai_recommendation_field(self, recommendation_id, field_name, value)

    def start_edit_ai_recommendation(self, recommendation_id: str):
        return AssistantStateMixin.start_edit_ai_recommendation(self, recommendation_id)

    def save_ai_recommendation_edit(self, recommendation_id: str):
        return AssistantStateMixin.save_ai_recommendation_edit(self, recommendation_id)

    def cancel_ai_recommendation_edit(self, recommendation_id: str):
        return AssistantStateMixin.cancel_ai_recommendation_edit(self, recommendation_id)

    def delete_ai_recommendation(self, recommendation_id: str):
        return AssistantStateMixin.delete_ai_recommendation(self, recommendation_id)

    def set_ai_recommendation_title(self, recommendation_id: str, value: str):
        return AssistantStateMixin.set_ai_recommendation_title(self, recommendation_id, value)

    def set_ai_recommendation_owner(self, recommendation_id: str, value: str):
        return AssistantStateMixin.set_ai_recommendation_owner(self, recommendation_id, value)

    def set_ai_recommendation_due_date(self, recommendation_id: str, value: str):
        return AssistantStateMixin.set_ai_recommendation_due_date(self, recommendation_id, value)

    def set_ai_recommendation_expected_result(self, recommendation_id: str, value: str):
        return AssistantStateMixin.set_ai_recommendation_expected_result(self, recommendation_id, value)

    def set_ai_recommendation_project_option(self, recommendation_id: str, value: str):
        return AssistantStateMixin.set_ai_recommendation_project_option(self, recommendation_id, value)

    def set_ai_recommendation_action_plan_option(self, recommendation_id: str, value: str):
        return AssistantStateMixin.set_ai_recommendation_action_plan_option(self, recommendation_id, value)

    def open_ai_recommendation_send(self, recommendation_id: str):
        return AssistantStateMixin.open_ai_recommendation_send(self, recommendation_id)

    def cancel_ai_recommendation_send(self, recommendation_id: str):
        return AssistantStateMixin.cancel_ai_recommendation_send(self, recommendation_id)

    def set_audit_filter_scope(self, value: str):
        return AssistantStateMixin.set_audit_filter_scope(self, value)

    def set_audit_active_tab(self, value: str):
        return AssistantStateMixin.set_audit_active_tab(self, value)

    def set_audit_filter_event(self, value: str):
        return AssistantStateMixin.set_audit_filter_event(self, value)

    def set_audit_filter_tenant(self, value: str):
        return AssistantStateMixin.set_audit_filter_tenant(self, value)

    def set_audit_filter_user(self, value: str):
        return AssistantStateMixin.set_audit_filter_user(self, value)

    def toggle_audit_event_expanded(self, audit_id: str):
        return AssistantStateMixin.toggle_audit_event_expanded(self, audit_id)

    def set_new_project_name(self, value: str):
        return ProjectStateMixin.set_new_project_name(self, value)

    def set_new_project_type(self, value: str):
        return ProjectStateMixin.set_new_project_type(self, value)

    def set_new_project_service_name(self, value: str):
        return ProjectStateMixin.set_new_project_service_name(self, value)

    def set_new_project_custom_service_name(self, value: str):
        return ProjectStateMixin.set_new_project_custom_service_name(self, value)

    def confirm_new_project_service_name(self):
        return ProjectStateMixin.confirm_new_project_service_name(self)

    def set_new_project_client_option(self, value: str):
        return ProjectStateMixin.set_new_project_client_option(self, value)

    def set_new_project_contracted_at(self, value: str):
        return ProjectStateMixin.set_new_project_contracted_at(self, value)

    def set_project_portfolio_service_filter(self, value: str):
        return ProjectStateMixin.set_project_portfolio_service_filter(self, value)

    def start_edit_project(self, project_id: int):
        return ProjectStateMixin.start_edit_project(self, project_id)

    def cancel_edit_project(self):
        return ProjectStateMixin.cancel_edit_project(self)

    def save_project_inline(self):
        return ProjectStateMixin.save_project_inline(self)

    def delete_project(self, project_id: int):
        return ProjectStateMixin.delete_project(self, project_id)

    def select_project(self, value: str):
        return ProjectStateMixin.select_project(self, value)

    def set_project_admin_tab(self, value: str):
        return ProjectStateMixin.set_project_admin_tab(self, value)

    def toggle_new_project_assigned_client(self, client_id: str):
        return ProjectStateMixin.toggle_new_project_assigned_client(self, client_id)

    def toggle_new_project_assigned_clients_open(self):
        return ProjectStateMixin.toggle_new_project_assigned_clients_open(self)

    def sync_project_assignments(self):
        return ProjectStateMixin.sync_project_assignments(self)

    def set_new_box_title(self, value: str):
        return ProjectStateMixin.set_new_box_title(self, value)

    def set_new_box_type(self, value: str):
        return ProjectStateMixin.set_new_box_type(self, value)

    def set_new_box_method(self, value: str):
        return ProjectStateMixin.set_new_box_method(self, value)

    def set_new_box_endpoint(self, value: str):
        return ProjectStateMixin.set_new_box_endpoint(self, value)

    def set_new_box_headers(self, value: str):
        return ProjectStateMixin.set_new_box_headers(self, value)

    def set_new_box_retry_policy(self, value: str):
        return ProjectStateMixin.set_new_box_retry_policy(self, value)

    def set_new_box_client_id(self, value: str):
        return ProjectStateMixin.set_new_box_client_id(self, value)

    def set_new_box_client_secret(self, value: str):
        return ProjectStateMixin.set_new_box_client_secret(self, value)

    def set_new_box_schedule(self, value: str):
        return ProjectStateMixin.set_new_box_schedule(self, value)

    def set_new_box_zone(self, value: str):
        return ProjectStateMixin.set_new_box_zone(self, value)

    def set_new_box_condition(self, value: str):
        return ProjectStateMixin.set_new_box_condition(self, value)

    def set_new_box_output_key(self, value: str):
        return ProjectStateMixin.set_new_box_output_key(self, value)

    def set_new_box_owner(self, value: str):
        return ProjectStateMixin.set_new_box_owner(self, value)

    def set_new_box_objective(self, value: str):
        return ProjectStateMixin.set_new_box_objective(self, value)

    def set_new_box_trigger(self, value: str):
        return ProjectStateMixin.set_new_box_trigger(self, value)

    def set_new_box_expected_output(self, value: str):
        return ProjectStateMixin.set_new_box_expected_output(self, value)

    def set_new_sticky_note_text(self, value: str):
        return ProjectStateMixin.set_new_sticky_note_text(self, value)

    def set_new_action_title(self, value: str):
        return ProjectStateMixin.set_new_action_title(self, value)

    def set_new_action_owner(self, value: str):
        return ProjectStateMixin.set_new_action_owner(self, value)

    def set_new_action_start_date(self, value: str):
        return ProjectStateMixin.set_new_action_start_date(self, value)

    def set_new_action_planned_due_date(self, value: str):
        return ProjectStateMixin.set_new_action_planned_due_date(self, value)

    def set_new_action_due_date(self, value: str):
        return ProjectStateMixin.set_new_action_due_date(self, value)

    def set_new_action_expected_result(self, value: str):
        return ProjectStateMixin.set_new_action_expected_result(self, value)

    def set_new_action_dimensions(self, value: str):
        return ProjectStateMixin.set_new_action_dimensions(self, value)

    def set_new_action_area(self, value: str):
        return ProjectStateMixin.set_new_action_area(self, value)

    def set_selected_action_plan_option(self, value: str):
        return ProjectStateMixin.set_selected_action_plan_option(self, value)

    def toggle_new_action_dimension(self, value: str):
        return ProjectStateMixin.toggle_new_action_dimension(self, value)

    def set_new_action_task_title(self, value: str):
        return ProjectStateMixin.set_new_action_task_title(self, value)

    def set_new_action_task_owner(self, value: str):
        return ProjectStateMixin.set_new_action_task_owner(self, value)

    def set_new_action_task_start_date(self, value: str):
        return ProjectStateMixin.set_new_action_task_start_date(self, value)

    def set_new_action_task_planned_due_date(self, value: str):
        return ProjectStateMixin.set_new_action_task_planned_due_date(self, value)

    def set_new_action_task_due_date(self, value: str):
        return ProjectStateMixin.set_new_action_task_due_date(self, value)

    def set_new_action_task_expected_result(self, value: str):
        return ProjectStateMixin.set_new_action_task_expected_result(self, value)

    def set_new_action_task_progress(self, value: str):
        return ProjectStateMixin.set_new_action_task_progress(self, value)

    def add_draft_action_task(self):
        return ProjectStateMixin.add_draft_action_task(self)

    def remove_draft_action_task(self, index: int):
        return ProjectStateMixin.remove_draft_action_task(self, index)

    def reset_action_task_form(self):
        return ProjectStateMixin.reset_action_task_form(self)

    def create_action_task(self):
        return ProjectStateMixin.create_action_task(self)

    def toggle_action_plan_expanded(self, action_id: int):
        return ProjectStateMixin.toggle_action_plan_expanded(self, action_id)

    def cancel_edit_action_plan(self):
        return ProjectStateMixin.cancel_edit_action_plan(self)

    def start_edit_action_plan(self):
        return ProjectStateMixin.start_edit_action_plan(self)

    def set_new_user_client_id(self, value: str):
        return AdminStateMixin.set_new_user_client_id(self, value)

    def set_new_user_tenant_id(self, value: str):
        return AdminStateMixin.set_new_user_tenant_id(self, value)

    def _expand_client_scope(self, client_ids: list[str]) -> list[str]:
        return AdminStateMixin._expand_client_scope(self, client_ids)

    def set_new_tenant_client_id(self, value: str):
        return AdminStateMixin.set_new_tenant_client_id(self, value)

    def set_new_tenant_client_option(self, value: str):
        return AdminStateMixin.set_new_tenant_client_option(self, value)

    def toggle_new_tenant_assigned_client(self, client_id: str):
        return AdminStateMixin.toggle_new_tenant_assigned_client(self, client_id)

    def toggle_new_tenant_assigned_clients_open(self):
        return AdminStateMixin.toggle_new_tenant_assigned_clients_open(self)

    def set_perm_user_email(self, value: str):
        return AccessStateMixin.set_perm_user_email(self, value)

    def set_perm_selected_module(self, value: str):
        return AccessStateMixin.set_perm_selected_module(self, value)

    def set_permissions_tab(self, value: str):
        return AccessStateMixin.set_permissions_tab(self, value)

    def set_perm_selected_role_template(self, value: str):
        return AccessStateMixin.set_perm_selected_role_template(self, value)

    def apply_selected_role_template(self):
        return AccessStateMixin.apply_selected_role_template(self)

    def reset_selected_user_password(self):
        return AccessStateMixin.reset_selected_user_password(self)

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
        return AdminStateMixin.create_client(self)

    def create_user(self):
        return AdminStateMixin.create_user(self)

    def delete_user(self, user_id: int):
        return AdminStateMixin.delete_user(self, user_id)

    def delete_client(self, client_id: int):
        return AdminStateMixin.delete_client(self, client_id)

    def create_tenant(self):
        return AdminStateMixin.create_tenant(self)

    def delete_tenant(self, tenant_id: str):
        return AdminStateMixin.delete_tenant(self, tenant_id)

    def create_role(self):
        return AdminStateMixin.create_role(self)

    def delete_role(self, role_id: int):
        return AdminStateMixin.delete_role(self, role_id)

    def create_responsibility(self):
        return AdminStateMixin.create_responsibility(self)

    def delete_responsibility(self, resp_id: int):
        return AdminStateMixin.delete_responsibility(self, resp_id)

    def create_form(self):
        return FormStateMixin.create_form(self)

    def delete_form(self, form_id: int):
        return FormStateMixin.delete_form(self, form_id)

    def select_form(self, value: str):
        return FormStateMixin.select_form(self, value)

    def select_form_by_id(self, form_id: int):
        return FormStateMixin.select_form_by_id(self, form_id)

    def create_interview_session(self):
        return FormStateMixin.create_interview_session(self)

    def update_active_interview_context(self):
        return FormStateMixin.update_active_interview_context(self)

    def _clear_active_interview_state(self):
        return FormStateMixin._clear_active_interview_state(self)

    def cancel_active_interview(self):
        return FormStateMixin.cancel_active_interview(self)

    def _create_interview_session_record(self, session) -> InterviewSessionModel | None:
        return FormStateMixin._create_interview_session_record(self, session)

    def start_table_edit_interview(self, interview_id: str):
        return FormStateMixin.start_table_edit_interview(self, interview_id)

    def cancel_table_edit_interview(self):
        return FormStateMixin.cancel_table_edit_interview(self)

    def _save_interview_inline_internal(self, show_toast: bool = True) -> bool:
        return FormStateMixin._save_interview_inline_internal(self, show_toast)

    def save_interview_inline(self):
        return FormStateMixin.save_interview_inline(self)

    def start_edit_interview(self, interview_id: str):
        return FormStateMixin.start_edit_interview(self, interview_id)

    def delete_interview_session(self, interview_id: str):
        return FormStateMixin.delete_interview_session(self, interview_id)

    def select_interview_session(self, interview_id: str):
        return FormStateMixin.select_interview_session(self, interview_id)

    def _save_interview_responses_internal(self) -> bool:
        return FormStateMixin._save_interview_responses_internal(self)

    def save_interview_responses(self):
        return FormStateMixin.save_interview_responses(self)

    def update_interview_status(self, status: str):
        return FormStateMixin.update_interview_status(self, status)

    def _resolve_selected_form_id(self) -> int | None:
        return FormStateMixin._resolve_selected_form_id(self)

    def create_question(self):
        return FormStateMixin.create_question(self)

    def add_mock_response(self, question_id: int, answer: str, score: int = 3):
        return FormStateMixin.add_mock_response(self, question_id, answer, score)

    def create_project(self):
        return ProjectStateMixin.create_project(self)

    def save_project_client_links(self):
        return ProjectStateMixin.save_project_client_links(self)

    def add_workflow_box(self):
        return ProjectStateMixin.add_workflow_box(self)

    def add_workflow_stage_template(self, stage_key: str):
        return ProjectStateMixin.add_workflow_stage_template(self, stage_key)

    def seed_workflow_journey(self):
        return ProjectStateMixin.seed_workflow_journey(self)

    def add_sticky_note(self):
        return ProjectStateMixin.add_sticky_note(self)

    def move_workflow_box(self, box_id: int, direction: str):
        return ProjectStateMixin.move_workflow_box(self, box_id, direction)

    def nudge_workflow_box(self, box_id: int, axis: str, delta: int):
        return ProjectStateMixin.nudge_workflow_box(self, box_id, axis, delta)

    def drop_workflow_box_to_zone(self, box_id: int, zone: str):
        return ProjectStateMixin.drop_workflow_box_to_zone(self, box_id, zone)

    def delete_workflow_box(self, box_id: int):
        return ProjectStateMixin.delete_workflow_box(self, box_id)

    def clear_workflow_logs(self):
        return ProjectStateMixin.clear_workflow_logs(self)

    def execute_workflow(self):
        return ProjectStateMixin.execute_workflow(self)

    def create_action_plan(self):
        return ProjectStateMixin.create_action_plan(self)

    def delete_action_plan(self, action_id: int):
        return ProjectStateMixin.delete_action_plan(self, action_id)

    def move_action_status(self, action_id: int, status: str):
        return ProjectStateMixin.move_action_status(self, action_id, status)

    def shift_action_due_date(self, action_id: int, delta_days: int):
        return ProjectStateMixin.shift_action_due_date(self, action_id, delta_days)

    def shift_action_task_due_date(self, task_id: int, delta_days: int):
        return ProjectStateMixin.shift_action_task_due_date(self, task_id, delta_days)

    def update_action_task_progress(self, action_id: int, task_id: int, new_progress: int):
        return ProjectStateMixin.update_action_task_progress(self, action_id, task_id, new_progress)

    def adjust_action_task_progress(self, action_id: int, task_id: int, delta: int):
        return ProjectStateMixin.adjust_action_task_progress(self, action_id, task_id, delta)

    def add_permission_box(self, decision: str):
        return AccessStateMixin.add_permission_box(self, decision)

    def apply_permission_from_catalog(self, resource: str, decision: str):
        return AccessStateMixin.apply_permission_from_catalog(self, resource, decision)

    def clear_permission_from_catalog(self, resource: str):
        return AccessStateMixin.clear_permission_from_catalog(self, resource)

    def delete_permission_box(self, permission_id: int):
        return AccessStateMixin.delete_permission_box(self, permission_id)

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
        return AssistantStateMixin.start_drag_question(self, question_text)

    def drop_question_into_prompt(self):
        return AssistantStateMixin.drop_question_into_prompt(self)

    async def handle_resource_upload(self, files: list[rx.UploadFile]):
        return await AssistantStateMixin.handle_resource_upload(self, files)

    def delete_ai_document(self, document_id: str):
        return AssistantStateMixin.delete_ai_document(self, document_id)

    def send_ai_recommendation_to_plan(self, recommendation_id: str):
        return AssistantStateMixin.send_ai_recommendation_to_plan(self, recommendation_id)

    def ask_ai(self):
        return AssistantStateMixin.ask_ai(self)

    def create_ai_recommendations_from_prompt(self, prompt: str, answer: str = ""):
        return AssistantStateMixin.create_ai_recommendations_from_prompt(self, prompt, answer)


def main_page() -> rx.Component:
    return build_main_page_component(State)


app = rx.App(
    stylesheets=["styles.css"],
)
app.add_page(
    main_page,
    route="/",
    title="SSecur1 | Plataforma SaaS",
    description="Plataforma SaaS multi-tenant para diagnóstico de cultura de segurança, liderança e produtividade segura.",
)
