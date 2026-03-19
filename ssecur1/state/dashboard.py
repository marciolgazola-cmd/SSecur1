from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import reflex as rx

from ssecur1.db import (
    ActionPlanModel,
    ActionTaskModel,
    ClientModel,
    DashboardBoxModel,
    FormModel,
    InterviewSessionModel,
    ProjectModel,
    QuestionModel,
    ResponseModel,
    SessionLocal,
    SurveyModel,
    TenantModel,
    UserModel,
)
from ssecur1.utils import format_display_datetime as _format_display_datetime
from ssecur1.utils import loads_json as _loads_json
from ssecur1.utils import now_brasilia as _now_brasilia


class DashboardStateMixin:
    dashboard_scope_mode: str = "tenant"
    dashboard_theme_tab: str = "executive"
    dashboard_period_mode: str = "Todo período"
    dashboard_selected_project_id: str = "Todos"
    dashboard_selected_client_id: str = "Todos"
    dashboard_selected_service_name: str = "Todos"
    dashboard_selected_department: str = "Todos"
    dashboard_drill_key: str = ""

    def reset_dashboard_state(self):
        self.dashboard_scope_mode = "tenant"
        self.dashboard_period_mode = "Todo período"
        self.dashboard_selected_project_id = "Todos"
        self.dashboard_selected_client_id = "Todos"
        self.dashboard_selected_service_name = "Todos"
        self.dashboard_selected_department = "Todos"
        self.dashboard_drill_key = ""

    @rx.var(cache=False)
    def dashboard_boxes_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        scope = "consultor" if self.user_role in {"admin", "editor"} else "cliente"
        box_tenant = "default" if self.dashboard_scope_mode == "default" and self.user_scope == "smartlab" else self.current_tenant
        rows = (
            session.query(DashboardBoxModel)
            .filter(
                DashboardBoxModel.tenant_id == box_tenant,
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
    def dashboard_scope_options(self) -> list[str]:
        session = SessionLocal()
        options = ["tenant"]
        if self.user_scope == "smartlab":
            options.append("default")
        if len(self._group_tenant_ids_for_tenant(session, self.current_tenant)) > 1:
            options.append("group")
        session.close()
        deduped: list[str] = []
        for item in options:
            if item not in deduped:
                deduped.append(item)
        return deduped

    def _dashboard_scope_tenant_ids(self, session) -> list[str]:
        mode = self.dashboard_scope_mode if self.dashboard_scope_mode in self.dashboard_scope_options else "tenant"
        if mode == "default" and self.user_scope == "smartlab":
            return ["default"]
        if mode == "group":
            return sorted(self._group_tenant_ids_for_tenant(session, self.current_tenant))
        return [self.current_tenant]

    @rx.var(cache=False)
    def dashboard_period_options(self) -> list[str]:
        return ["Todo período", "Últimos 30 dias", "Últimos 90 dias", "Últimos 365 dias"]

    def _dashboard_period_cutoff(self) -> datetime | None:
        mapping = {"Últimos 30 dias": 30, "Últimos 90 dias": 90, "Últimos 365 dias": 365}
        days = mapping.get(self.dashboard_period_mode)
        if not days:
            return None
        return datetime.utcnow() - timedelta(days=days)

    def _dashboard_project_row(self, session, tenant_ids: list[str]) -> ProjectModel | None:
        if not str(self.dashboard_selected_project_id).isdigit():
            return None
        return (
            session.query(ProjectModel)
            .filter(ProjectModel.id == int(self.dashboard_selected_project_id), ProjectModel.tenant_id.in_(tenant_ids))
            .first()
        )

    @rx.var(cache=False)
    def dashboard_project_options(self) -> list[str]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        tenant_lookup = {
            str(row[0]): self._workspace_label(str(row[0]), str(row[1] or ""))
            for row in session.query(TenantModel.id, TenantModel.name).filter(TenantModel.id.in_(tenant_ids)).all()
        }
        rows = session.query(ProjectModel).filter(ProjectModel.tenant_id.in_(tenant_ids)).order_by(ProjectModel.created_at.desc(), ProjectModel.id.desc()).all()
        options = ["Todos"]
        for row in rows:
            workspace = tenant_lookup.get(str(row.tenant_id), str(row.tenant_id))
            options.append(f'{row.id} - {row.name} | {workspace}')
        session.close()
        return options

    @rx.var(cache=False)
    def dashboard_selected_project_option(self) -> str:
        if not str(self.dashboard_selected_project_id).isdigit():
            return "Todos"
        selected_prefix = f"{self.dashboard_selected_project_id} - "
        for item in self.dashboard_project_options:
            if item.startswith(selected_prefix):
                return item
        return "Todos"

    @rx.var(cache=False)
    def dashboard_client_options(self) -> list[str]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        visible_lookup = self.client_lookup
        rows = session.query(ClientModel.id, ClientModel.name).filter(ClientModel.tenant_id.in_(tenant_ids)).order_by(ClientModel.name.asc(), ClientModel.id.asc()).all()
        options = ["Todos"]
        for client_id, client_name in rows:
            key = str(client_id)
            if key in visible_lookup:
                options.append(f'{key} - {visible_lookup.get(key, str(client_name or key))}')
        session.close()
        return options

    @rx.var(cache=False)
    def dashboard_selected_client_option(self) -> str:
        if not str(self.dashboard_selected_client_id).isdigit():
            return "Todos"
        selected_prefix = f"{self.dashboard_selected_client_id} - "
        for item in self.dashboard_client_options:
            if item.startswith(selected_prefix):
                return item
        return "Todos"

    @rx.var(cache=False)
    def dashboard_service_options(self) -> list[str]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        values: set[str] = set()
        for model, column in (
            (ProjectModel, ProjectModel.service_name),
            (ResponseModel, ResponseModel.service_name),
            (ActionPlanModel, ActionPlanModel.service_name),
            (SurveyModel, SurveyModel.service_name),
        ):
            for row in session.query(column).filter(model.tenant_id.in_(tenant_ids)).all():
                if str(row[0] or "").strip():
                    values.add(str(row[0]).strip())
        session.close()
        return ["Todos", *sorted(values)]

    @rx.var(cache=False)
    def dashboard_scope_summary(self) -> dict[str, str]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        tenant_rows = session.query(TenantModel.id, TenantModel.name).filter(TenantModel.id.in_(tenant_ids)).order_by(TenantModel.name.asc(), TenantModel.id.asc()).all()
        session.close()
        labels = [self._workspace_label(str(row[0]), str(row[1] or "")) for row in tenant_rows]
        mode = self.dashboard_scope_mode if self.dashboard_scope_mode in self.dashboard_scope_options else "tenant"
        label_map = {"tenant": "Workspace atual", "group": "Grupo do cliente", "default": "Workspace default"}
        return {"mode": mode, "label": label_map.get(mode, "Workspace atual"), "tenants_count": str(len(tenant_ids)), "tenants": ", ".join(labels) or self.current_tenant}

    @rx.var(cache=False)
    def dashboard_filter_summary(self) -> dict[str, str]:
        return {
            "periodo": self.dashboard_period_mode,
            "projeto": self.dashboard_selected_project_option,
            "cliente": self.dashboard_selected_client_option,
            "servico": self.dashboard_selected_service_name,
        }

    def _is_leadership_label(self, raw_value: str) -> bool:
        value = str(raw_value or "").strip().lower()
        if not value:
            return False
        return any(token in value for token in ["ceo", "diretor", "diretora", "gerente", "supervisor", "coordenador", "coordenadora", "lider", "líder", "manager", "head"])

    def _dashboard_department_lookup(self, session, tenant_ids: list[str]) -> tuple[dict[int, str], dict[int, str]]:
        user_rows = session.query(UserModel.id, UserModel.department, UserModel.profession).filter(UserModel.tenant_id.in_(tenant_ids)).all()
        user_department_lookup = {int(row[0]): str(row[1] or "").strip() for row in user_rows if row[0] is not None}
        user_profession_lookup = {int(row[0]): str(row[2] or "").strip() for row in user_rows if row[0] is not None}
        return user_department_lookup, user_profession_lookup

    def _response_department_name(self, response_row: ResponseModel, interview_lookup: dict[int, InterviewSessionModel], user_department_lookup: dict[int, str]) -> str:
        if response_row.respondent_id is not None and int(response_row.respondent_id) in user_department_lookup:
            department = user_department_lookup[int(response_row.respondent_id)].strip()
            if department:
                return department
        if response_row.interview_id is not None and int(response_row.interview_id) in interview_lookup:
            interview = interview_lookup[int(response_row.interview_id)]
            target_area = str(interview.target_area or "").strip()
            if target_area:
                return target_area
        return "Sem área"

    def _dashboard_date_in_scope(self, raw_dt: datetime | None, cutoff: datetime | None) -> bool:
        if cutoff is None:
            return True
        if raw_dt is None:
            return False
        return raw_dt >= cutoff

    def _dashboard_matches_business_filters(self, client_id: int | None, service_name: str | None) -> bool:
        if str(self.dashboard_selected_client_id).isdigit() and (client_id is None or int(client_id) != int(self.dashboard_selected_client_id)):
            return False
        selected_service = str(self.dashboard_selected_service_name or "").strip().lower()
        if selected_service and selected_service != "todos" and str(service_name or "").strip().lower() != selected_service:
            return False
        return True

    def _dashboard_interviews_in_scope(self, session, tenant_ids: list[str]) -> list[InterviewSessionModel]:
        cutoff = self._dashboard_period_cutoff()
        project_row = self._dashboard_project_row(session, tenant_ids)
        query = session.query(InterviewSessionModel).filter(InterviewSessionModel.tenant_id.in_(tenant_ids))
        if project_row is not None:
            query = query.filter(InterviewSessionModel.project_id == int(project_row.id))
        rows = query.all()
        project_ids = sorted({int(row.project_id) for row in rows if row.project_id is not None})
        project_lookup = {int(row.id): row for row in session.query(ProjectModel).filter(ProjectModel.id.in_(project_ids)).all()} if project_ids else {}
        filtered: list[InterviewSessionModel] = []
        for row in rows:
            interview_dt = self._parse_iso_date(row.interview_date) or row.created_at
            project = project_lookup.get(int(row.project_id)) if row.project_id is not None else None
            service_name = str(project.service_name or "") if project else ""
            if self._dashboard_date_in_scope(interview_dt, cutoff) and self._dashboard_matches_business_filters(int(row.client_id) if row.client_id is not None else None, service_name):
                filtered.append(row)
        return filtered

    def _dashboard_responses_in_scope(self, session, tenant_ids: list[str]) -> list[ResponseModel]:
        cutoff = self._dashboard_period_cutoff()
        project_row = self._dashboard_project_row(session, tenant_ids)
        rows = session.query(ResponseModel).filter(ResponseModel.tenant_id.in_(tenant_ids)).all()
        filtered = [row for row in rows if self._dashboard_date_in_scope(row.submitted_at, cutoff)]
        if project_row is None:
            return [row for row in filtered if self._dashboard_matches_business_filters(int(row.client_id) if row.client_id is not None else None, str(row.service_name or ""))]
        project_id = int(project_row.id)
        project_client_id = int(project_row.client_id) if project_row.client_id is not None else None
        project_service = str(project_row.service_name or "").strip().lower()
        interview_rows = session.query(InterviewSessionModel.id, InterviewSessionModel.project_id).filter(InterviewSessionModel.id.in_([int(row.interview_id) for row in filtered if row.interview_id is not None])).all()
        interview_project_lookup = {int(row[0]): int(row[1]) for row in interview_rows if row[0] is not None and row[1] is not None}
        scoped: list[ResponseModel] = []
        for row in filtered:
            matched = False
            if row.interview_id is not None and int(row.interview_id) in interview_project_lookup:
                matched = interview_project_lookup[int(row.interview_id)] == project_id
            elif project_client_id is not None and row.client_id is not None and int(row.client_id) == project_client_id:
                matched = True
            elif project_service and str(row.service_name or "").strip().lower() == project_service:
                matched = True
            if matched and self._dashboard_matches_business_filters(int(row.client_id) if row.client_id is not None else None, str(row.service_name or "")):
                scoped.append(row)
        return scoped

    def _dashboard_action_plans_in_scope(self, session, tenant_ids: list[str]) -> list[ActionPlanModel]:
        project_row = self._dashboard_project_row(session, tenant_ids)
        query = session.query(ActionPlanModel).filter(ActionPlanModel.tenant_id.in_(tenant_ids))
        if project_row is not None:
            query = query.filter(ActionPlanModel.project_id == int(project_row.id))
        rows = query.all()
        cutoff = self._dashboard_period_cutoff()
        filtered: list[ActionPlanModel] = []
        for row in rows:
            plan_dt = self._parse_iso_date(row.start_date) or self._parse_iso_date(row.planned_due_date) or self._parse_iso_date(row.due_date)
            if self._dashboard_date_in_scope(plan_dt, cutoff) and self._dashboard_matches_business_filters(int(row.client_id) if row.client_id is not None else None, str(row.service_name or "")):
                filtered.append(row)
        return filtered

    def _dashboard_projects_in_scope(self, session, tenant_ids: list[str]) -> list[ProjectModel]:
        project_row = self._dashboard_project_row(session, tenant_ids)
        query = session.query(ProjectModel).filter(ProjectModel.tenant_id.in_(tenant_ids))
        if project_row is not None:
            query = query.filter(ProjectModel.id == int(project_row.id))
        rows = query.all()
        cutoff = self._dashboard_period_cutoff()
        filtered: list[ProjectModel] = []
        for row in rows:
            project_dt = self._parse_iso_date(row.contracted_at) or row.created_at
            if self._dashboard_date_in_scope(project_dt, cutoff) and self._dashboard_matches_business_filters(int(row.client_id) if row.client_id is not None else None, str(row.service_name or "")):
                filtered.append(row)
        return filtered

    def _dashboard_action_tasks_in_scope(self, session, tenant_ids: list[str]) -> list[ActionTaskModel]:
        plans = self._dashboard_action_plans_in_scope(session, tenant_ids)
        plan_ids = [int(row.id) for row in plans if row.id is not None]
        if not plan_ids:
            return []
        rows = session.query(ActionTaskModel).filter(ActionTaskModel.tenant_id.in_(tenant_ids), ActionTaskModel.action_plan_id.in_(plan_ids)).all()
        cutoff = self._dashboard_period_cutoff()
        if cutoff is None:
            return rows
        return [row for row in rows if self._dashboard_date_in_scope(row.created_at or self._parse_iso_date(row.start_date) or self._parse_iso_date(row.planned_due_date) or self._parse_iso_date(row.due_date), cutoff)]

    @rx.var(cache=False)
    def dashboard_department_options(self) -> list[str]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        departments: set[str] = set()
        for row in session.query(UserModel.department).filter(UserModel.tenant_id.in_(tenant_ids)).all():
            department = str(row[0] or "").strip()
            if department:
                departments.add(department)
        for row in self._dashboard_interviews_in_scope(session, tenant_ids):
            target_area = str(row.target_area or "").strip()
            if target_area:
                departments.add(target_area)
        session.close()
        return ["Todos", *sorted(departments)]

    def _dashboard_workspace_rollup(self, session) -> list[dict[str, str]]:
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        tenant_rows = session.query(TenantModel.id, TenantModel.name).filter(TenantModel.id.in_(tenant_ids)).order_by(TenantModel.name.asc(), TenantModel.id.asc()).all()
        rollup: list[dict[str, str]] = []
        scoped_responses = self._dashboard_responses_in_scope(session, tenant_ids)
        responses_by_tenant: dict[str, list[ResponseModel]] = {}
        for row in scoped_responses:
            responses_by_tenant.setdefault(str(row.tenant_id), []).append(row)
        for tenant_id, tenant_name in tenant_rows:
            forms = session.query(FormModel).filter(FormModel.tenant_id == str(tenant_id)).all()
            response_rows = responses_by_tenant.get(str(tenant_id), [])
            valid_scores = [int(row.score) for row in response_rows if row.score is not None]
            avg_response_score = round(sum(valid_scores) / max(1, len(valid_scores)), 2) if valid_scores else 0.0
            form_averages: list[float] = []
            forms_with_responses = 0
            for form in forms:
                form_scores = [int(row.score) for row in response_rows if int(row.form_id) == int(form.id) and row.score is not None]
                if form_scores:
                    forms_with_responses += 1
                form_averages.append(round(sum(form_scores) / max(1, len(form_scores)), 2) if form_scores else 0.0)
            avg_dashboard_score = round(sum(form_averages) / max(1, len(form_averages)), 2) if form_averages else 0.0
            rollup.append({"tenant_id": str(tenant_id), "workspace": self._workspace_label(str(tenant_id), str(tenant_name or "")), "clientes": str(session.query(ClientModel).filter(ClientModel.tenant_id == str(tenant_id)).count()), "formularios": str(len(forms)), "formularios_respondidos": str(forms_with_responses), "respostas": str(len(response_rows)), "media_dashboard": f"{avg_dashboard_score:.2f}", "media_respostas": f"{avg_response_score:.2f}"})
        return rollup

    @rx.var(cache=False)
    def dashboard_workspace_rollup(self) -> list[dict[str, str]]:
        session = SessionLocal()
        data = self._dashboard_workspace_rollup(session)
        session.close()
        return data

    @rx.var(cache=False)
    def dashboard_dimension_compare_data(self) -> list[dict[str, str | float]]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        responses = [row for row in self._dashboard_responses_in_scope(session, tenant_ids) if row.score is not None]
        question_ids = sorted({int(row.question_id) for row in responses if row.question_id is not None})
        question_dimension_lookup = {int(question_id): str(dimension or "Sem dimensão") for question_id, dimension in session.query(QuestionModel.id, QuestionModel.dimension).filter(QuestionModel.id.in_(question_ids)).all()} if question_ids else {}
        interview_ids = sorted({int(row.interview_id) for row in responses if row.interview_id is not None})
        interviews = session.query(InterviewSessionModel).filter(InterviewSessionModel.id.in_(interview_ids)).all() if interview_ids else []
        interview_lookup = {int(row.id): row for row in interviews if row.id is not None}
        user_department_lookup, _ = self._dashboard_department_lookup(session, tenant_ids)
        selected_department = self.dashboard_selected_department if self.dashboard_selected_department in self.dashboard_department_options else "Todos"
        company_totals: dict[str, int] = {}
        company_counts: dict[str, int] = {}
        department_totals: dict[str, int] = {}
        department_counts: dict[str, int] = {}
        for row in responses:
            dimension = question_dimension_lookup.get(int(row.question_id), "Sem dimensão") if row.question_id is not None else "Sem dimensão"
            score = int(row.score or 0)
            company_totals[dimension] = company_totals.get(dimension, 0) + score
            company_counts[dimension] = company_counts.get(dimension, 0) + 1
            department_name = self._response_department_name(row, interview_lookup, user_department_lookup)
            if selected_department != "Todos" and department_name == selected_department:
                department_totals[dimension] = department_totals.get(dimension, 0) + score
                department_counts[dimension] = department_counts.get(dimension, 0) + 1
        dimensions = sorted(set(company_totals) | set(department_totals))
        data = []
        for dimension in dimensions:
            company_avg = round(company_totals.get(dimension, 0) / max(1, company_counts.get(dimension, 0)), 2)
            department_avg = round(department_totals.get(dimension, 0) / max(1, department_counts.get(dimension, 0)), 2) if selected_department != "Todos" else company_avg
            data.append({"dimension": dimension, "empresa": company_avg, "departamento": department_avg, "limite": 5.0})
        session.close()
        return data

    @rx.var(cache=False)
    def dashboard_dimension_cards(self) -> list[dict[str, str]]:
        return [{"key": str(item["dimension"]), "dimension": str(item["dimension"]), "score": f'{float(item["empresa"]):.2f}', "status": "Forte" if float(item["empresa"]) >= 4 else "Em evolução" if float(item["empresa"]) >= 2.5 else "Crítico"} for item in self.dashboard_dimension_compare_data]

    @rx.var(cache=False)
    def dashboard_diagnosis_cards(self) -> list[dict[str, str]]:
        table = self.dashboard_table
        critical = [row for row in table if row["status"] == "Crítico"]
        evolving = [row for row in table if row["status"] == "Em evolução"]
        strongest = next((row for row in sorted(table, key=lambda item: float(item["media"]), reverse=True)), None)
        weakest = next((row for row in sorted(table, key=lambda item: float(item["media"]))), None)
        return [
            {"key": "forms_criticos", "label": "Forms Críticos", "value": str(len(critical)), "detail": "exigem plano de ação imediato"},
            {"key": "forms_evolucao", "label": "Forms em Evolução", "value": str(len(evolving)), "detail": "em faixa intermediária de maturidade"},
            {"key": "melhor_form", "label": "Melhor Form", "value": str(strongest["form"]) if strongest else "-", "detail": str(strongest["media"]) if strongest else "sem dados"},
            {"key": "pior_form", "label": "Pior Form", "value": str(weakest["form"]) if weakest else "-", "detail": str(weakest["media"]) if weakest else "sem dados"},
        ]

    @rx.var(cache=False)
    def dashboard_diagnosis_chart_data(self) -> list[dict[str, str | float]]:
        return [{"name": item["dimension"], "value": float(item["score"])} for item in self.dashboard_dimension_cards]

    @rx.var(cache=False)
    def dashboard_executive_cards(self) -> list[dict[str, str]]:
        metrics = self.dashboard_metrics
        dimensions = self.dashboard_dimension_cards
        top_gap = next((item["dimension"] for item in sorted(dimensions, key=lambda row: float(row["score"]))), "-")
        return [
            {"key": "score_geral", "label": "Score Geral", "value": metrics["media_respostas"], "detail": "média real das respostas válidas"},
            {"key": "score_dashboard", "label": "Score Dashboard", "value": metrics["media_dashboard"], "detail": "média das médias por formulário"},
            {"key": top_gap, "label": "Dimensão Crítica", "value": top_gap, "detail": "menor aderência atual no escopo"},
            {"key": "cobertura", "label": "Cobertura", "value": f'{metrics["formularios_respondidos"]}/{metrics["formularios"]}', "detail": "formulários já respondidos"},
        ]

    @rx.var(cache=False)
    def dashboard_operational_cards(self) -> list[dict[str, str]]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        tasks = self._dashboard_action_tasks_in_scope(session, tenant_ids)
        plans = self._dashboard_action_plans_in_scope(session, tenant_ids)
        today = _now_brasilia().date()
        overdue = 0
        on_time = 0
        done = 0
        for task in tasks:
            progress = int(task.progress or 0)
            due_dt = self._parse_iso_date(task.due_date)
            if progress >= 100:
                done += 1
            elif due_dt and due_dt.date() < today:
                overdue += 1
            else:
                on_time += 1
        plans_open = sum(1 for row in plans if str(row.status or "").strip().lower() != "concluido")
        session.close()
        return [
            {"key": "tarefas_no_prazo", "label": "Tarefas no Prazo", "value": str(on_time), "detail": "backlog operacional saudável"},
            {"key": "tarefas_atrasadas", "label": "Tarefas Atrasadas", "value": str(overdue), "detail": "itens exigindo escalonamento"},
            {"key": "tarefas_concluidas", "label": "Tarefas Concluídas", "value": str(done), "detail": "entregas finalizadas"},
            {"key": "planos_em_aberto", "label": "Planos em Aberto", "value": str(plans_open), "detail": "planos ainda não concluídos"},
        ]

    @rx.var(cache=False)
    def dashboard_operational_chart_data(self) -> list[dict[str, str | int]]:
        return [{"name": item["label"], "value": int(item["value"]) if str(item["value"]).isdigit() else 0} for item in self.dashboard_operational_cards]

    @rx.var(cache=False)
    def dashboard_engagement_cards(self) -> list[dict[str, str]]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        users = session.query(UserModel).filter(UserModel.tenant_id.in_(tenant_ids)).all()
        responses = self._dashboard_responses_in_scope(session, tenant_ids)
        interviews = self._dashboard_interviews_in_scope(session, tenant_ids)
        leadership_user_ids = {int(user.id) for user in users if user.id is not None and (self._is_leadership_label(str(user.profession or "")) or self._is_leadership_label(str(user.name or "")))}
        leadership_responded = {int(row.respondent_id) for row in responses if row.respondent_id is not None and int(row.respondent_id) in leadership_user_ids}
        visit_keywords = ("visita", "guiada", "técnica", "tecnica")
        roda_keywords = ("roda", "conversa")
        visits_done = sum(1 for row in interviews if "visita" in str(row.target_area or "").lower() or "visita" in str(row.interviewee_name or "").lower())
        rodas_done = sum(1 for row in interviews if "roda" in str(row.audience_group or "").lower() or "conversa" in str(row.interviewee_name or "").lower())
        surveys = session.query(SurveyModel).filter(SurveyModel.tenant_id.in_(tenant_ids)).all()
        visits_planned = sum(1 for row in surveys if any(token in str(row.stage_name or "").lower() for token in visit_keywords))
        rodas_planned = sum(1 for row in surveys if any(token in str(row.stage_name or "").lower() for token in roda_keywords))
        session.close()
        return [
            {"key": "liderancas", "label": "Lideranças", "value": str(len(leadership_user_ids)), "detail": "universo elegível por cargo/perfil"},
            {"key": "liderancas_respondentes", "label": "Lideranças Respondentes", "value": str(len(leadership_responded)), "detail": "já responderam no escopo"},
            {"key": "visitas_planejadas", "label": "Visitas Planejadas", "value": str(visits_planned), "detail": "surveys/etapas mapeadas"},
            {"key": "visitas_realizadas", "label": "Visitas Realizadas", "value": str(visits_done), "detail": "sessões executadas no escopo"},
            {"key": "rodas_planejadas", "label": "Rodas Planejadas", "value": str(rodas_planned), "detail": "etapas previstas"},
            {"key": "rodas_realizadas", "label": "Rodas Realizadas", "value": str(rodas_done), "detail": "execução registrada"},
        ]

    @rx.var(cache=False)
    def dashboard_engagement_chart_data(self) -> list[dict[str, str | int]]:
        return [{"name": item["label"], "value": int(item["value"]) if str(item["value"]).isdigit() else 0} for item in self.dashboard_engagement_cards]

    @rx.var(cache=False)
    def dashboard_projects_cards(self) -> list[dict[str, str]]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        projects = self._dashboard_projects_in_scope(session, tenant_ids)
        statuses: dict[str, int] = {}
        services: dict[str, int] = {}
        for row in projects:
            statuses[str(row.status or "planejamento")] = statuses.get(str(row.status or "planejamento"), 0) + 1
            service = str(row.service_name or "Serviço não definido")
            services[service] = services.get(service, 0) + 1
        dominant_status = next((item[0] for item in sorted(statuses.items(), key=lambda item: item[1], reverse=True)), "-")
        dominant_service = next((item[0] for item in sorted(services.items(), key=lambda item: item[1], reverse=True)), "-")
        avg_progress = round(sum(int(row.progress or 0) for row in projects) / max(1, len(projects)), 1) if projects else 0.0
        session.close()
        return [
            {"key": "projetos_total", "label": "Projetos no Recorte", "value": str(len(projects)), "detail": "portfólio ativo no escopo"},
            {"key": "status_dominante", "label": "Status Dominante", "value": dominant_status, "detail": "fase predominante do portfólio"},
            {"key": "servico_dominante", "label": "Serviço Dominante", "value": dominant_service, "detail": "oferta mais presente"},
            {"key": "progresso_medio", "label": "Progresso Médio", "value": f"{avg_progress:.1f}%", "detail": "execução média declarada"},
        ]

    @rx.var(cache=False)
    def dashboard_projects_chart_data(self) -> list[dict[str, str | int]]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        projects = self._dashboard_projects_in_scope(session, tenant_ids)
        counts: dict[str, int] = {}
        for row in projects:
            label = str(row.status or "planejamento")
            counts[label] = counts.get(label, 0) + 1
        session.close()
        return [{"name": key, "value": value} for key, value in sorted(counts.items())]

    @rx.var(cache=False)
    def dashboard_executive_timeline_data(self) -> list[dict[str, str | float]]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        responses = [row for row in self._dashboard_responses_in_scope(session, tenant_ids) if row.score is not None and row.submitted_at is not None]
        grouped: dict[str, dict[str, float]] = {}
        for row in responses:
            key = row.submitted_at.strftime("%Y-%m")
            bucket = grouped.setdefault(key, {"sum": 0.0, "count": 0.0})
            bucket["sum"] += float(row.score or 0)
            bucket["count"] += 1
        session.close()
        return [{"name": key, "value": round(values["sum"] / max(values["count"], 1.0), 2)} for key, values in sorted(grouped.items())]

    @rx.var(cache=False)
    def dashboard_projects_timeline_data(self) -> list[dict[str, str | int]]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        projects = self._dashboard_projects_in_scope(session, tenant_ids)
        grouped: dict[str, int] = {}
        for row in projects:
            project_dt = self._parse_iso_date(row.contracted_at) or row.created_at
            if project_dt is None:
                continue
            key = project_dt.strftime("%Y-%m")
            grouped[key] = grouped.get(key, 0) + 1
        session.close()
        return [{"name": key, "value": value} for key, value in sorted(grouped.items())]

    @rx.var(cache=False)
    def dashboard_builder_preview(self) -> list[dict[str, str]]:
        return [{"title": box["title"], "kind": box["kind"], "source": box["source"], "description": box["description"] or "Sem descricao funcional"} for box in self.dashboard_boxes_data]

    @rx.var(cache=False)
    def dashboard_metrics(self) -> dict[str, str]:
        session = SessionLocal()
        rollup = self._dashboard_workspace_rollup(session)
        total_clients = sum(int(item["clientes"]) for item in rollup)
        total_forms = sum(int(item["formularios"]) for item in rollup)
        total_forms_with_responses = sum(int(item["formularios_respondidos"]) for item in rollup)
        total_responses = sum(int(item["respostas"]) for item in rollup)
        dashboard_scores = [float(item["media_dashboard"]) for item in rollup]
        response_scores = [float(item["media_respostas"]) for item in rollup if float(item["media_respostas"]) > 0]
        avg_dashboard_score = round(sum(dashboard_scores) / max(1, len(dashboard_scores)), 2) if dashboard_scores else 0.0
        avg_response_score = round(sum(response_scores) / max(1, len(response_scores)), 2) if response_scores else 0.0
        session.close()
        return {"workspaces": str(len(rollup)), "clientes": str(total_clients), "formularios": str(total_forms), "formularios_respondidos": str(total_forms_with_responses), "respostas": str(total_responses), "media": str(avg_dashboard_score), "media_dashboard": str(avg_dashboard_score), "media_respostas": str(avg_response_score)}

    @rx.var(cache=False)
    def dashboard_table(self) -> list[dict[str, str]]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        scoped_responses = self._dashboard_responses_in_scope(session, tenant_ids)
        tenant_lookup = {str(row[0]): self._workspace_label(str(row[0]), str(row[1] or "")) for row in session.query(TenantModel.id, TenantModel.name).filter(TenantModel.id.in_(tenant_ids)).all()}
        forms = session.query(FormModel).filter(FormModel.tenant_id.in_(tenant_ids)).order_by(FormModel.tenant_id.asc(), FormModel.name.asc()).all()
        rows: list[dict[str, str]] = []
        for form in forms:
            responses = [row for row in scoped_responses if str(row.tenant_id) == str(form.tenant_id) and int(row.form_id) == int(form.id)]
            count = len(responses)
            valid_scores = [int(r.score) for r in responses if r.score is not None]
            avg = round(sum(valid_scores) / max(1, len(valid_scores)), 2)
            status = "Forte" if avg >= 4 else "Em evolução" if avg >= 2.5 else "Crítico"
            rows.append({"workspace": tenant_lookup.get(str(form.tenant_id), str(form.tenant_id)), "form": form.name, "categoria": form.category, "respostas": str(count), "media": str(avg), "status": status})
        session.close()
        return rows

    @rx.var(cache=False)
    def dashboard_detail_title(self) -> str:
        if self.dashboard_theme_tab == "diagnosis":
            mapping = {"forms_criticos": "Formulários Críticos", "forms_evolucao": "Formulários em Evolução", "melhor_form": "Melhores Resultados por Formulário", "pior_form": "Piores Resultados por Formulário"}
            return mapping.get(self.dashboard_drill_key, "Detalhe de Diagnóstico")
        if self.dashboard_theme_tab == "projects":
            mapping = {"projetos_total": "Portfólio de Projetos", "status_dominante": "Projetos por Status", "servico_dominante": "Projetos por Serviço", "progresso_medio": "Progresso dos Projetos"}
            return mapping.get(self.dashboard_drill_key, "Detalhe de Projetos")
        if self.dashboard_theme_tab == "operational":
            mapping = {"tarefas_no_prazo": "Detalhe de Tarefas no Prazo", "tarefas_atrasadas": "Detalhe de Tarefas Atrasadas", "tarefas_concluidas": "Detalhe de Tarefas Concluídas", "planos_em_aberto": "Detalhe de Planos em Aberto"}
            return mapping.get(self.dashboard_drill_key, "Detalhe Operacional")
        if self.dashboard_theme_tab == "engagement":
            mapping = {"liderancas": "Cobertura de Lideranças por Área", "liderancas_respondentes": "Lideranças Respondentes por Área", "visitas_planejadas": "Etapas Planejadas de Visitas", "visitas_realizadas": "Sessões de Visitas Realizadas", "rodas_planejadas": "Etapas Planejadas de Rodas", "rodas_realizadas": "Sessões de Rodas Realizadas"}
            return mapping.get(self.dashboard_drill_key, "Detalhe de Engajamento")
        if self.dashboard_drill_key in {"score_geral", "score_dashboard", "cobertura", ""}:
            return "Leitura por Área/Departamento"
        return f"Detalhe da Dimensão: {self.dashboard_drill_key}"

    @rx.var(cache=False)
    def dashboard_detail_rows(self) -> list[dict[str, str]]:
        session = SessionLocal()
        tenant_ids = self._dashboard_scope_tenant_ids(session)
        tenant_lookup = {str(row[0]): self._workspace_label(str(row[0]), str(row[1] or "")) for row in session.query(TenantModel.id, TenantModel.name).filter(TenantModel.id.in_(tenant_ids)).all()}
        rows: list[dict[str, str]] = []
        if self.dashboard_theme_tab == "executive":
            responses = [row for row in self._dashboard_responses_in_scope(session, tenant_ids) if row.score is not None]
            question_ids = sorted({int(row.question_id) for row in responses if row.question_id is not None})
            question_dimension_lookup = {int(question_id): str(dimension or "Sem dimensão") for question_id, dimension in session.query(QuestionModel.id, QuestionModel.dimension).filter(QuestionModel.id.in_(question_ids)).all()} if question_ids else {}
            interview_ids = sorted({int(row.interview_id) for row in responses if row.interview_id is not None})
            interview_lookup = {int(row.id): row for row in session.query(InterviewSessionModel).filter(InterviewSessionModel.id.in_(interview_ids)).all()} if interview_ids else {}
            user_department_lookup, _ = self._dashboard_department_lookup(session, tenant_ids)
            selected_dimension = self.dashboard_drill_key
            if selected_dimension in {"", "score_geral", "score_dashboard", "cobertura"}:
                ordered_dimensions = sorted(self.dashboard_dimension_cards, key=lambda item: float(item["score"]))
                selected_dimension = ordered_dimensions[0]["dimension"] if ordered_dimensions else ""
            grouped: dict[str, dict[str, float]] = {}
            for row in responses:
                dimension = question_dimension_lookup.get(int(row.question_id), "Sem dimensão") if row.question_id is not None else "Sem dimensão"
                if selected_dimension and dimension != selected_dimension:
                    continue
                area = self._response_department_name(row, interview_lookup, user_department_lookup)
                bucket = grouped.setdefault(area, {"sum": 0.0, "count": 0.0})
                bucket["sum"] += float(row.score or 0)
                bucket["count"] += 1
            for area, values in sorted(grouped.items(), key=lambda item: ((item[1]["sum"] / max(item[1]["count"], 1.0)) if item[1]["count"] else 0.0)):
                avg = round(values["sum"] / max(values["count"], 1.0), 2)
                rows.append({"primary": area, "secondary": selected_dimension or "Todas as dimensões", "metric": f"{avg:.2f}", "detail": f'{int(values["count"])} resposta(s)', "status": "Forte" if avg >= 4 else "Em evolução" if avg >= 2.5 else "Crítico"})
        elif self.dashboard_theme_tab == "diagnosis":
            rows = [{"primary": row["form"], "secondary": row["workspace"], "metric": row["media"], "detail": f'{row["respostas"]} resposta(s) | {row["categoria"]}', "status": row["status"]} for row in sorted(self.dashboard_table, key=lambda item: float(item["media"]), reverse=self.dashboard_drill_key == "melhor_form")]
            if self.dashboard_drill_key == "forms_criticos":
                rows = [row for row in rows if row["status"] == "Crítico"]
            elif self.dashboard_drill_key == "forms_evolucao":
                rows = [row for row in rows if row["status"] == "Em evolução"]
        elif self.dashboard_theme_tab == "operational":
            plans = self._dashboard_action_plans_in_scope(session, tenant_ids)
            tasks = self._dashboard_action_tasks_in_scope(session, tenant_ids)
            plan_lookup = {int(row.id): row for row in plans if row.id is not None}
            project_ids = sorted({int(row.project_id) for row in plans if row.project_id is not None})
            project_lookup = {int(row.id): row for row in session.query(ProjectModel).filter(ProjectModel.id.in_(project_ids)).all()} if project_ids else {}
            today = _now_brasilia().date()
            if self.dashboard_drill_key == "planos_em_aberto":
                for row in plans:
                    if str(row.status or "").strip().lower() == "concluido":
                        continue
                    project = project_lookup.get(int(row.project_id)) if row.project_id is not None else None
                    rows.append({"primary": str(row.title or "Plano"), "secondary": str(project.name if project else "Sem projeto"), "metric": str(row.owner or "-"), "detail": str(row.planned_due_date or row.due_date or "-"), "status": str(row.status or "a_fazer")})
            else:
                for task in tasks:
                    progress = int(task.progress or 0)
                    due_dt = self._parse_iso_date(task.due_date or task.planned_due_date or "")
                    status_key = "tarefas_no_prazo"
                    if progress >= 100:
                        status_key = "tarefas_concluidas"
                    elif due_dt and due_dt.date() < today:
                        status_key = "tarefas_atrasadas"
                    if self.dashboard_drill_key and status_key != self.dashboard_drill_key:
                        continue
                    plan = plan_lookup.get(int(task.action_plan_id)) if task.action_plan_id is not None else None
                    project = project_lookup.get(int(plan.project_id)) if plan and plan.project_id is not None else None
                    rows.append({"primary": str(task.title or "Tarefa"), "secondary": str(project.name if project else "Sem projeto"), "metric": f"{progress}%", "detail": str(task.due_date or task.planned_due_date or "-"), "status": "Concluída" if progress >= 100 else ("Atrasada" if due_dt and due_dt.date() < today else "No prazo")})
        elif self.dashboard_theme_tab == "engagement":
            users = session.query(UserModel).filter(UserModel.tenant_id.in_(tenant_ids)).all()
            responses = self._dashboard_responses_in_scope(session, tenant_ids)
            interviews = self._dashboard_interviews_in_scope(session, tenant_ids)
            user_department_lookup, _ = self._dashboard_department_lookup(session, tenant_ids)
            leadership_user_ids = {int(user.id) for user in users if user.id is not None and (self._is_leadership_label(str(user.profession or "")) or self._is_leadership_label(str(user.name or "")))}
            if self.dashboard_drill_key in {"liderancas", "liderancas_respondentes", ""}:
                dept_totals: dict[str, dict[str, int]] = {}
                for user in users:
                    if user.id is None or int(user.id) not in leadership_user_ids:
                        continue
                    dept = str(user.department or "").strip() or "Sem área"
                    bucket = dept_totals.setdefault(dept, {"total": 0, "responded": 0})
                    bucket["total"] += 1
                for row in responses:
                    if row.respondent_id is None or int(row.respondent_id) not in leadership_user_ids:
                        continue
                    dept = user_department_lookup.get(int(row.respondent_id), "").strip() or "Sem área"
                    bucket = dept_totals.setdefault(dept, {"total": 0, "responded": 0})
                    bucket["responded"] += 1
                for dept, values in sorted(dept_totals.items()):
                    metric_value = values["responded"] if self.dashboard_drill_key == "liderancas_respondentes" else values["total"]
                    coverage = round((values["responded"] / max(values["total"], 1)) * 100, 1) if values["total"] else 0.0
                    rows.append({"primary": dept, "secondary": f'{values["responded"]}/{values["total"]} respondentes', "metric": str(metric_value), "detail": f"{coverage:.1f}% cobertura", "status": "Alta" if coverage >= 80 else "Média" if coverage >= 50 else "Baixa"})
            else:
                for row in interviews:
                    audience = str(row.audience_group or "").lower()
                    target = str(row.target_area or "").lower()
                    name = str(row.interviewee_name or "").lower()
                    if self.dashboard_drill_key == "visitas_realizadas" and "visita" not in target and "visita" not in name:
                        continue
                    if self.dashboard_drill_key == "rodas_realizadas" and "roda" not in audience and "conversa" not in name:
                        continue
                    rows.append({"primary": str(row.interviewee_name or "Sessão"), "secondary": tenant_lookup.get(str(row.tenant_id), str(row.tenant_id)), "metric": str(row.target_area or row.audience_group or "-"), "detail": str(row.interview_date or _format_display_datetime(row.created_at)), "status": str(row.status or "em_andamento")})
        else:
            projects = sorted(self._dashboard_projects_in_scope(session, tenant_ids), key=lambda row: (row.created_at or datetime.min, int(row.id or 0)), reverse=True)
            for row in projects:
                service = str(row.service_name or "Serviço não definido")
                if self.dashboard_drill_key == "status_dominante":
                    secondary = service
                    metric = f'{int(row.progress or 0)}%'
                elif self.dashboard_drill_key == "servico_dominante":
                    secondary = str(row.status or "planejamento")
                    metric = service
                else:
                    secondary = service
                    metric = f'{int(row.progress or 0)}%'
                rows.append({"primary": str(row.name or "Projeto"), "secondary": secondary, "metric": metric, "detail": str(row.contracted_at or "-"), "status": str(row.status or "planejamento")})
        session.close()
        return rows[:12]

    def set_dashboard_scope_mode(self, value: str):
        allowed = set(self.dashboard_scope_options)
        self.dashboard_scope_mode = value if value in allowed else "tenant"
        if self.dashboard_selected_project_option not in self.dashboard_project_options:
            self.dashboard_selected_project_id = "Todos"
        if self.dashboard_selected_client_option not in self.dashboard_client_options:
            self.dashboard_selected_client_id = "Todos"
        if self.dashboard_selected_service_name not in self.dashboard_service_options:
            self.dashboard_selected_service_name = "Todos"
        self.dashboard_selected_department = "Todos"
        self.dashboard_drill_key = ""

    def set_dashboard_theme_tab(self, value: str):
        self.dashboard_theme_tab = value
        self.dashboard_drill_key = ""

    def set_dashboard_period_mode(self, value: str):
        allowed = set(self.dashboard_period_options)
        self.dashboard_period_mode = value if value in allowed else "Todo período"
        self.dashboard_selected_department = "Todos"
        self.dashboard_drill_key = ""

    def set_dashboard_selected_project(self, value: str):
        project_id = value.split(" - ", 1)[0].strip() if value and value != "Todos" else "Todos"
        allowed_ids = {item.split(" - ", 1)[0].strip() for item in self.dashboard_project_options if item != "Todos"}
        self.dashboard_selected_project_id = project_id if project_id in allowed_ids else "Todos"
        self.dashboard_selected_department = "Todos"
        self.dashboard_drill_key = ""

    def set_dashboard_selected_client(self, value: str):
        client_id = value.split(" - ", 1)[0].strip() if value and value != "Todos" else "Todos"
        allowed_ids = {item.split(" - ", 1)[0].strip() for item in self.dashboard_client_options if item != "Todos"}
        self.dashboard_selected_client_id = client_id if client_id in allowed_ids else "Todos"
        self.dashboard_selected_project_id = "Todos"
        self.dashboard_selected_department = "Todos"
        self.dashboard_drill_key = ""

    def set_dashboard_selected_service(self, value: str):
        allowed = set(self.dashboard_service_options)
        self.dashboard_selected_service_name = value if value in allowed else "Todos"
        self.dashboard_selected_project_id = "Todos"
        self.dashboard_selected_department = "Todos"
        self.dashboard_drill_key = ""

    def set_dashboard_selected_department(self, value: str):
        allowed = set(self.dashboard_department_options)
        self.dashboard_selected_department = value if value in allowed else "Todos"
        self.dashboard_drill_key = ""

    def set_dashboard_drill_key(self, value: str):
        self.dashboard_drill_key = str(value or "").strip()
