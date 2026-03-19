from __future__ import annotations

import json
from datetime import datetime
from datetime import timedelta
from typing import Any

import reflex as rx

from ssecur1.db import (
    ActionPlanModel,
    ActionTaskModel,
    AssistantChunkModel,
    AssistantDocumentModel,
    ClientModel,
    InterviewSessionModel,
    ProjectAssignmentModel,
    ProjectModel,
    QuestionModel,
    ResponseModel,
    SessionLocal,
    SurveyModel,
    TenantModel,
    UserModel,
    WorkflowBoxModel,
)
from ssecur1.utils import format_display_date as _format_display_date
from ssecur1.utils import format_display_datetime as _format_display_datetime
from ssecur1.utils import loads_json as _loads_json
from ssecur1.utils import now_brasilia as _now_brasilia
from ssecur1.utils import question_payload as _question_payload
from ssecur1.utils import parse_int as _parse_int


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


class ProjectStateMixin:
    def set_new_project_name(self, value: str):
        self.new_project_name = value

    def set_new_project_type(self, value: str):
        self.new_project_type = value

    def set_new_project_service_name(self, value: str):
        self.new_project_service_name = value
        if value != "Outro":
            self.new_project_custom_service_name = ""

    def set_new_project_custom_service_name(self, value: str):
        self.new_project_custom_service_name = value

    def confirm_new_project_service_name(self):
        value = self._register_catalog_option("smartlab_service", self.new_project_custom_service_name)
        if not value:
            self.toast_message = "Informe o serviço antes de confirmar"
            self.toast_type = "error"
            return
        self.new_project_service_name = value
        self.new_project_custom_service_name = ""
        self.toast_message = "Serviço registrado e disponível na lista"
        self.toast_type = "success"

    def set_new_project_client_option(self, value: str):
        self.new_project_client_id = value.split(" - ", 1)[0].strip() if value else ""

    def set_new_project_contracted_at(self, value: str):
        self.new_project_contracted_at = value

    def set_project_portfolio_service_filter(self, value: str):
        self.project_portfolio_service_filter = value or "Todos"

    def start_edit_project(self, project_id: int):
        session = SessionLocal()
        project = (
            session.query(ProjectModel)
            .filter(ProjectModel.id == int(project_id), ProjectModel.tenant_id == self.current_tenant)
            .first()
        )
        session.close()
        if not project:
            self.toast_message = "Projeto não encontrado"
            self.toast_type = "error"
            return
        self.editing_project_id = str(project.id)
        self.new_project_name = project.name or ""
        self.new_project_type = project.project_type or "Diagnóstico de Cultura"
        self.new_project_service_name = project.service_name or "Diagnóstico Cultura de Segurança"
        self.new_project_custom_service_name = ""
        self.new_project_client_id = str(project.client_id or "")
        self.new_project_contracted_at = project.contracted_at or ""

    def cancel_edit_project(self):
        self.editing_project_id = ""
        self.new_project_name = ""
        self.new_project_type = "Diagnóstico de Cultura"
        self.new_project_service_name = "Diagnóstico Cultura de Segurança"
        self.new_project_custom_service_name = ""
        self.new_project_client_id = ""
        self.new_project_contracted_at = ""

    def save_project_inline(self):
        if not self.editing_project_id.isdigit():
            self.toast_message = "Nenhum projeto em edição"
            self.toast_type = "error"
            return
        if not self.new_project_name.strip():
            self.toast_message = "Informe o nome do projeto"
            self.toast_type = "error"
            return
        if not self.new_project_client_id.isdigit():
            self.toast_message = "Selecione o cliente do projeto"
            self.toast_type = "error"
            return
        service_name = self.effective_new_project_service_name.strip()
        if self.new_project_service_name == "Outro" and not self.new_project_custom_service_name.strip():
            self.toast_message = "Informe o nome do novo serviço SmartLab"
            self.toast_type = "error"
            return
        session = SessionLocal()
        project = (
            session.query(ProjectModel)
            .filter(ProjectModel.id == int(self.editing_project_id), ProjectModel.tenant_id == self.current_tenant)
            .first()
        )
        if not project:
            session.close()
            self.toast_message = "Projeto não encontrado"
            self.toast_type = "error"
            return
        project.name = self.new_project_name.strip()
        project.project_type = self.new_project_type
        project.service_name = service_name
        project.client_id = int(self.new_project_client_id)
        project.contracted_at = self.new_project_contracted_at.strip() or _now_brasilia().strftime("%Y-%m-%d")
        assignment = session.query(ProjectAssignmentModel).filter(ProjectAssignmentModel.project_id == int(project.id)).first()
        if assignment:
            assignment.client_id = int(self.new_project_client_id)
            assignment.tenant_id = self.current_tenant
        else:
            session.add(
                ProjectAssignmentModel(
                    project_id=int(project.id),
                    tenant_id=self.current_tenant,
                    client_id=int(self.new_project_client_id),
                )
            )
        session.commit()
        session.close()
        self.selected_project_id = self.editing_project_id
        self.cancel_edit_project()
        self.toast_message = "Projeto atualizado"
        self.toast_type = "success"
        self.sync_project_assignments()

    def delete_project(self, project_id: int):
        if not self.can_configure_projects:
            self.toast_message = "Projetos so podem ser geridos no workspace default"
            self.toast_type = "error"
            return
        session = SessionLocal()
        project = (
            session.query(ProjectModel)
            .filter(ProjectModel.id == int(project_id), ProjectModel.tenant_id == self.current_tenant)
            .first()
        )
        if not project:
            session.close()
            self.toast_message = "Projeto não encontrado"
            self.toast_type = "error"
            return
        interview_ids = [
            int(row[0])
            for row in session.query(InterviewSessionModel.id).filter(InterviewSessionModel.project_id == int(project_id)).all()
            if row[0] is not None
        ]
        action_count = session.query(ActionPlanModel.id).filter(ActionPlanModel.project_id == int(project_id)).count()
        workflow_count = session.query(WorkflowBoxModel.id).filter(WorkflowBoxModel.project_id == int(project_id)).count()
        document_ids = [
            int(row[0])
            for row in session.query(AssistantDocumentModel.id).filter(AssistantDocumentModel.project_id == int(project_id)).all()
            if row[0] is not None
        ]
        if interview_ids:
            session.query(ResponseModel).filter(ResponseModel.interview_id.in_(interview_ids)).delete(synchronize_session=False)
            session.query(InterviewSessionModel).filter(InterviewSessionModel.id.in_(interview_ids)).delete(synchronize_session=False)
        if action_count:
            session.query(ActionPlanModel).filter(ActionPlanModel.project_id == int(project_id)).delete(synchronize_session=False)
        if workflow_count:
            session.query(WorkflowBoxModel).filter(WorkflowBoxModel.project_id == int(project_id)).delete(synchronize_session=False)
        if document_ids:
            session.query(AssistantChunkModel).filter(AssistantChunkModel.document_id.in_(document_ids)).delete(synchronize_session=False)
            session.query(AssistantDocumentModel).filter(AssistantDocumentModel.id.in_(document_ids)).delete(synchronize_session=False)
        session.query(ProjectAssignmentModel).filter(ProjectAssignmentModel.project_id == int(project_id)).delete()
        session.delete(project)
        session.commit()
        session.close()
        if self.selected_project_id == str(project_id):
            self.selected_project_id = ""
        if self.editing_project_id == str(project_id):
            self.cancel_edit_project()
        details = []
        if interview_ids:
            details.append(f"{len(interview_ids)} entrevista(s)")
        if action_count:
            details.append(f"{action_count} plano(s)")
        if workflow_count:
            details.append(f"{workflow_count} caixa(s) de workflow")
        if document_ids:
            details.append(f"{len(document_ids)} documento(s) IA")
        suffix = f" em cascata: {', '.join(details)}" if details else ""
        self.toast_message = f"Projeto excluído{suffix}"
        self.toast_type = "success"

    def select_project(self, value: str):
        self.selected_project_id = value.split(" - ", 1)[0].strip()
        self.sync_project_assignments()
        self.ai_history = []
        self.ai_answer = ""
        self.ai_prompt = ""
        self.load_ai_history()
        if self.selected_project_id:
            self._append_audit_entry("project.select", f"Projeto selecionado: {value}", "operations")

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
        rows = session.query(ProjectAssignmentModel.client_id).filter(ProjectAssignmentModel.project_id == int(self.selected_project_id)).all()
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

    def set_new_box_owner(self, value: str):
        self.new_box_owner = value

    def set_new_box_objective(self, value: str):
        self.new_box_objective = value

    def set_new_box_trigger(self, value: str):
        self.new_box_trigger = value

    def set_new_box_expected_output(self, value: str):
        self.new_box_expected_output = value

    def set_new_sticky_note_text(self, value: str):
        self.new_sticky_note_text = value

    def set_new_action_title(self, value: str):
        self.new_action_title = value

    def set_new_action_owner(self, value: str):
        self.new_action_owner = value

    def set_new_action_start_date(self, value: str):
        self.new_action_start_date = value

    def set_new_action_planned_due_date(self, value: str):
        self.new_action_planned_due_date = value

    def set_new_action_due_date(self, value: str):
        self.new_action_due_date = value

    def set_new_action_expected_result(self, value: str):
        self.new_action_expected_result = value

    def set_new_action_dimensions(self, value: str):
        self.new_action_dimensions = value

    def set_new_action_area(self, value: str):
        self.new_action_area = value
        if self.new_action_owner and self.new_action_owner not in self.project_action_owner_options:
            self.new_action_owner = ""
        if self.new_action_task_owner and self.new_action_task_owner not in self.project_action_owner_options:
            self.new_action_task_owner = ""

    def set_selected_action_plan_option(self, value: str):
        self.selected_action_plan_id = value.split(" - ", 1)[0].strip() if value else ""

    def toggle_new_action_dimension(self, value: str):
        current = list(self.new_action_dimension_ids)
        if value in current:
            current.remove(value)
        else:
            current.append(value)
        self.new_action_dimension_ids = current
        self.new_action_dimensions = ", ".join(current)

    def set_new_action_task_title(self, value: str):
        self.new_action_task_title = value

    def set_new_action_task_owner(self, value: str):
        self.new_action_task_owner = value

    def set_new_action_task_start_date(self, value: str):
        self.new_action_task_start_date = value

    def set_new_action_task_planned_due_date(self, value: str):
        self.new_action_task_planned_due_date = value

    def set_new_action_task_due_date(self, value: str):
        self.new_action_task_due_date = value

    def set_new_action_task_expected_result(self, value: str):
        self.new_action_task_expected_result = value

    def set_new_action_task_progress(self, value: str):
        self.new_action_task_progress = value

    def add_draft_action_task(self):
        if not self.new_action_task_title.strip():
            self.toast_message = "Informe o nome da tarefa"
            self.toast_type = "error"
            return
        progress = max(0, min(100, _parse_int(self.new_action_task_progress) or 0))
        self.draft_action_tasks = self.draft_action_tasks + [
            {
                "title": self.new_action_task_title.strip(),
                "owner": self.new_action_task_owner.strip() or self.new_action_owner.strip() or "Responsavel nao definido",
                "start_date": self.new_action_task_start_date.strip(),
                "planned_due_date": self.new_action_task_planned_due_date.strip() or self.new_action_task_due_date.strip(),
                "due_date": self.new_action_task_due_date.strip() or self.new_action_task_planned_due_date.strip(),
                "expected_result": self.new_action_task_expected_result.strip(),
                "progress": str(progress),
            }
        ]
        self.new_action_task_title = ""
        self.new_action_task_owner = ""
        self.new_action_task_start_date = ""
        self.new_action_task_planned_due_date = ""
        self.new_action_task_due_date = ""
        self.new_action_task_expected_result = ""
        self.new_action_task_progress = "0"

    def remove_draft_action_task(self, index: int):
        self.draft_action_tasks = [item for idx, item in enumerate(self.draft_action_tasks) if idx != int(index)]

    def reset_action_task_form(self):
        self.new_action_task_title = ""
        self.new_action_task_owner = ""
        self.new_action_task_start_date = ""
        self.new_action_task_planned_due_date = ""
        self.new_action_task_due_date = ""
        self.new_action_task_expected_result = ""
        self.new_action_task_progress = "0"

    def create_action_task(self):
        plan_id = self.editing_action_plan_id or self.selected_action_plan_id
        if not str(plan_id).isdigit():
            self.toast_message = "Selecione ou salve um plano antes de criar tarefas"
            self.toast_type = "error"
            return
        if not self.new_action_task_title.strip():
            self.toast_message = "Informe a tarefa"
            self.toast_type = "error"
            return
        planned_due_date = self.new_action_task_planned_due_date.strip() or self.new_action_task_due_date.strip()
        due_date = self.new_action_task_due_date.strip() or planned_due_date
        progress = 0
        session = SessionLocal()
        session.query(ActionTaskModel).filter(
            ActionTaskModel.tenant_id == self.selected_project_source_tenant,
            ActionTaskModel.action_plan_id == int(plan_id),
        ).count()
        session.add(
            ActionTaskModel(
                tenant_id=self.selected_project_source_tenant,
                action_plan_id=int(plan_id),
                title=self.new_action_task_title.strip(),
                owner=self.new_action_task_owner.strip() or self.new_action_owner.strip() or "Responsavel nao definido",
                start_date=self.new_action_task_start_date.strip(),
                planned_due_date=planned_due_date,
                due_date=due_date,
                due_date_change_count=0,
                expected_result=self.new_action_task_expected_result.strip(),
                progress=progress,
            )
        )
        session.commit()
        session.close()
        self.reset_action_task_form()
        self.toast_message = "Tarefa criada e enviada para A Fazer"
        self.toast_type = "success"

    def toggle_action_plan_expanded(self, action_id: int):
        action_key = str(action_id)
        current = list(self.expanded_action_plan_ids)
        if action_key in current:
            current.remove(action_key)
        else:
            current.append(action_key)
        self.expanded_action_plan_ids = current

    def cancel_edit_action_plan(self):
        self.editing_action_plan_id = ""
        self.selected_action_plan_id = ""
        self.new_action_title = ""
        self.new_action_owner = ""
        self.new_action_start_date = ""
        self.new_action_planned_due_date = ""
        self.new_action_due_date = ""
        self.new_action_expected_result = ""
        self.new_action_dimensions = ""
        self.new_action_area = ""
        self.new_action_dimension_ids = []
        self.new_action_task_title = ""
        self.new_action_task_owner = ""
        self.new_action_task_start_date = ""
        self.new_action_task_planned_due_date = ""
        self.new_action_task_due_date = ""
        self.new_action_task_expected_result = ""
        self.new_action_task_progress = "0"
        self.draft_action_tasks = []

    def start_edit_action_plan(self):
        if not self.selected_action_plan_id.isdigit():
            self.toast_message = "Selecione um plano para alterar"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = session.query(ActionPlanModel).filter(ActionPlanModel.id == int(self.selected_action_plan_id)).first()
        if not row:
            session.close()
            self.toast_message = "Plano nao encontrado"
            self.toast_type = "error"
            return
        task_rows = (
            session.query(ActionTaskModel)
            .filter(ActionTaskModel.tenant_id == row.tenant_id, ActionTaskModel.action_plan_id == int(row.id))
            .order_by(ActionTaskModel.id.asc())
            .all()
        )
        session.close()
        self.editing_action_plan_id = str(row.id)
        self.new_action_title = row.title or ""
        self.new_action_area = row.target_area or ""
        self.new_action_owner = row.owner or ""
        self.new_action_start_date = row.start_date or ""
        self.new_action_planned_due_date = row.planned_due_date or ""
        self.new_action_due_date = row.due_date or ""
        self.new_action_expected_result = row.expected_result or ""
        self.new_action_dimensions = row.dimension_names or ""
        self.new_action_dimension_ids = [item.strip() for item in str(row.dimension_names or "").split(",") if item.strip()]
        self.draft_action_tasks = [
            {
                "title": task.title,
                "owner": task.owner,
                "start_date": task.start_date or "",
                "planned_due_date": task.planned_due_date or "",
                "due_date": task.due_date or "",
                "expected_result": task.expected_result or "",
                "progress": str(int(task.progress or 0)),
            }
            for task in task_rows
        ]
        self.toast_message = "Plano carregado para alteracao"
        self.toast_type = "success"

    def create_project(self):
        if not self.can_configure_projects:
            self.toast_message = "Projetos so podem ser configurados no workspace default"
            self.toast_type = "error"
            return
        if not self.new_project_name:
            self.toast_message = "Informe o nome do projeto"
            self.toast_type = "error"
            return
        if not self.new_project_client_id.isdigit():
            self.toast_message = "Selecione o cliente que contratou o serviço"
            self.toast_type = "error"
            return
        service_name = self.effective_new_project_service_name.strip()
        if self.new_project_service_name == "Outro" and not self.new_project_custom_service_name.strip():
            self.toast_message = "Informe o nome do novo serviço SmartLab"
            self.toast_type = "error"
            return
        project_name = self.new_project_name.strip()
        contracted_at = self.new_project_contracted_at.strip() or _now_brasilia().strftime("%Y-%m-%d")
        session = SessionLocal()
        duplicate = (
            session.query(ProjectModel)
            .filter(
                ProjectModel.tenant_id == self.current_tenant,
                ProjectModel.name == project_name,
                ProjectModel.service_name == service_name,
                ProjectModel.client_id == int(self.new_project_client_id),
                ProjectModel.contracted_at == contracted_at,
            )
            .first()
        )
        if duplicate:
            self.selected_project_id = str(duplicate.id)
            session.close()
            self.toast_message = "Já existe um projeto com esse nome, cliente, serviço e data"
            self.toast_type = "error"
            return
        project = ProjectModel(
            tenant_id=self.current_tenant,
            name=project_name,
            project_type=self.new_project_type,
            service_name=service_name,
            client_id=int(self.new_project_client_id),
            contracted_at=contracted_at,
            status="planejamento",
            progress=0,
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        session.add(
            ProjectAssignmentModel(
                project_id=int(project.id),
                tenant_id=self.current_tenant,
                client_id=int(self.new_project_client_id),
            )
        )
        session.commit()
        project_id = int(project.id)
        session.close()
        self.selected_project_id = str(project_id)
        self.new_project_name = ""
        self.new_project_client_id = ""
        self.new_project_contracted_at = ""
        self.new_project_service_name = "Diagnóstico Cultura de Segurança"
        self.new_project_custom_service_name = ""
        self.toast_message = "Projeto criado"
        self.toast_type = "success"
        self.sync_project_assignments()

    def save_project_client_links(self):
        if not self.can_configure_projects:
            self.toast_message = "Vinculos so podem ser geridos no workspace default"
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
                    ProjectAssignmentModel(project_id=project_id, tenant_id=tenant.id, client_id=int(client_id))
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
        target_tenant = self.selected_project_source_tenant
        session = SessionLocal()
        max_pos = (
            session.query(WorkflowBoxModel)
            .filter(WorkflowBoxModel.tenant_id == target_tenant, WorkflowBoxModel.project_id == int(self.selected_project_id))
            .count()
        )
        session.add(
            WorkflowBoxModel(
                tenant_id=target_tenant,
                project_id=int(self.selected_project_id),
                title=self.new_box_title,
                box_type=self.new_box_type,
                position=max_pos + 1,
                config_json=json.dumps(
                    {
                        "source": "builder",
                        "timestamp": _now_brasilia().isoformat(),
                        "zone": self.new_box_zone,
                        "owner": self.new_box_owner.strip(),
                        "objective": self.new_box_objective.strip(),
                        "trigger": self.new_box_trigger.strip(),
                        "expected_output": self.new_box_expected_output.strip(),
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
        self.new_box_owner = ""
        self.new_box_objective = ""
        self.new_box_trigger = ""
        self.new_box_expected_output = ""
        self.toast_message = "Caixa adicionada ao workflow"
        self.toast_type = "success"

    def add_workflow_stage_template(self, stage_key: str):
        if not self.selected_project_id:
            self.toast_message = "Selecione um projeto"
            self.toast_type = "error"
            return
        template = next((item for item in WORKFLOW_STAGE_LIBRARY if item["key"] == stage_key), None)
        if not template:
            self.toast_message = "Etapa sugerida nao encontrada"
            self.toast_type = "error"
            return
        target_tenant = self.selected_project_source_tenant
        session = SessionLocal()
        exists = (
            session.query(WorkflowBoxModel.id)
            .filter(
                WorkflowBoxModel.tenant_id == target_tenant,
                WorkflowBoxModel.project_id == int(self.selected_project_id),
                WorkflowBoxModel.title == template["title"],
            )
            .first()
        )
        if exists:
            session.close()
            self.toast_message = "Essa etapa ja existe na jornada"
            self.toast_type = "error"
            return
        max_pos = (
            session.query(WorkflowBoxModel)
            .filter(WorkflowBoxModel.tenant_id == target_tenant, WorkflowBoxModel.project_id == int(self.selected_project_id))
            .count()
        )
        session.add(
            WorkflowBoxModel(
                tenant_id=target_tenant,
                project_id=int(self.selected_project_id),
                title=template["title"],
                box_type=template["box_type"],
                position=max_pos + 1,
                config_json=json.dumps(
                    {
                        "source": "journey_template",
                        "timestamp": _now_brasilia().isoformat(),
                        "zone": template["zone"],
                        "owner": template["owner"],
                        "objective": template["objective"],
                        "trigger": template["trigger"],
                        "expected_output": template["expected_output"],
                    }
                ),
            )
        )
        session.commit()
        session.close()
        self.toast_message = "Etapa sugerida adicionada a jornada"
        self.toast_type = "success"

    def seed_workflow_journey(self):
        if not self.selected_project_id:
            self.toast_message = "Selecione um projeto"
            self.toast_type = "error"
            return
        missing = self.workflow_missing_stage_templates
        if not missing:
            self.toast_message = "A jornada sugerida ja esta carregada"
            self.toast_type = "success"
            return
        target_tenant = self.selected_project_source_tenant
        session = SessionLocal()
        max_pos = (
            session.query(WorkflowBoxModel)
            .filter(WorkflowBoxModel.tenant_id == target_tenant, WorkflowBoxModel.project_id == int(self.selected_project_id))
            .count()
        )
        for offset, template in enumerate(missing, start=1):
            full_template = next((item for item in WORKFLOW_STAGE_LIBRARY if item["key"] == template["key"]), None)
            if not full_template:
                continue
            session.add(
                WorkflowBoxModel(
                    tenant_id=target_tenant,
                    project_id=int(self.selected_project_id),
                    title=full_template["title"],
                    box_type=full_template["box_type"],
                    position=max_pos + offset,
                    config_json=json.dumps(
                        {
                            "source": "journey_template",
                            "timestamp": _now_brasilia().isoformat(),
                            "zone": full_template["zone"],
                            "owner": full_template["owner"],
                            "objective": full_template["objective"],
                            "trigger": full_template["trigger"],
                            "expected_output": full_template["expected_output"],
                        }
                    ),
                )
            )
        session.commit()
        session.close()
        self.toast_message = "Jornada sugerida carregada no projeto"
        self.toast_type = "success"

    def add_sticky_note(self):
        if not self.selected_project_id or not self.new_sticky_note_text.strip():
            self.toast_message = "Selecione projeto e escreva a anotação"
            self.toast_type = "error"
            return
        target_tenant = self.selected_project_source_tenant
        session = SessionLocal()
        max_pos = (
            session.query(WorkflowBoxModel)
            .filter(WorkflowBoxModel.tenant_id == target_tenant, WorkflowBoxModel.project_id == int(self.selected_project_id))
            .count()
        )
        session.add(
            WorkflowBoxModel(
                tenant_id=target_tenant,
                project_id=int(self.selected_project_id),
                title="Sticky Note",
                box_type="nota",
                position=max_pos + 1,
                config_json=json.dumps(
                    {
                        "zone": "right",
                        "note": self.new_sticky_note_text.strip(),
                        "source": "sticky-note",
                        "timestamp": _now_brasilia().isoformat(),
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
        target_tenant = self.selected_project_source_tenant
        session = SessionLocal()
        rows = (
            session.query(WorkflowBoxModel)
            .filter(WorkflowBoxModel.tenant_id == target_tenant, WorkflowBoxModel.project_id == int(self.selected_project_id))
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
        target_tenant = self.selected_project_source_tenant
        session = SessionLocal()
        row = session.query(WorkflowBoxModel).filter(WorkflowBoxModel.id == box_id, WorkflowBoxModel.tenant_id == target_tenant).first()
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
        target_tenant = self.selected_project_source_tenant
        session = SessionLocal()
        row = session.query(WorkflowBoxModel).filter(WorkflowBoxModel.id == box_id, WorkflowBoxModel.tenant_id == target_tenant).first()
        if not row:
            session.close()
            return
        config = json.loads(row.config_json or "{}")
        config["zone"] = zone
        row.config_json = json.dumps(config)
        session.commit()
        session.close()

    def delete_workflow_box(self, box_id: int):
        target_tenant = self.selected_project_source_tenant
        session = SessionLocal()
        row = (
            session.query(WorkflowBoxModel)
            .filter(WorkflowBoxModel.id == box_id, WorkflowBoxModel.tenant_id == target_tenant)
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
        timestamp = _format_display_datetime(_now_brasilia(), include_seconds=True)
        project = self.selected_project_record
        logs = [f"[{timestamp}] Simulando jornada operacional do projeto '{project['name']}'"]
        items = self.workflow_operational_stages
        if not items:
            logs.append("Nenhuma etapa operacional cadastrada.")
            self.workflow_logs = logs
            self.toast_message = "Jornada sem etapas configuradas"
            self.toast_type = "error"
            return
        for stage in items:
            logs.append(f"[{stage['context']}] {stage['title']} | Responsavel: {stage['owner']}")
            logs.append(f"Objetivo: {stage['objective']}")
            logs.append(f"Gatilho: {stage['trigger']}")
            logs.append(f"Entrega esperada: {stage['expected_output']}")
            if stage["box_type"] == "analise":
                logs.append("Leitura analitica concluida: diagnostico preliminar preparado.")
            if stage["title"].casefold().startswith("plano de acao"):
                logs.append(f"Planos de acao vinculados ao projeto: {len(self.action_plans_data)} item(ns).")
        logs.append("Simulacao finalizada com sucesso.")
        self.workflow_logs = logs
        self.toast_message = "Jornada operacional simulada"
        self.toast_type = "success"

    def create_action_plan(self):
        if not self.selected_project_id or not self.selected_project_id.isdigit():
            self.toast_message = "Selecione um projeto"
            self.toast_type = "error"
            return
        action_title = self.new_action_title.strip()
        action_owner = self.new_action_owner.strip()
        if not action_title or not action_owner:
            self.toast_message = "Título e responsável são obrigatórios"
            self.toast_type = "error"
            return
        start_date = self.new_action_start_date.strip() or _now_brasilia().strftime("%Y-%m-%d")
        planned_due_date = self.new_action_planned_due_date.strip() or self.new_action_due_date.strip()
        due_date = self.new_action_due_date.strip() or planned_due_date
        if not planned_due_date:
            self.toast_message = "Informe pelo menos o prazo base do plano"
            self.toast_type = "error"
            return
        attainment = 0
        session = SessionLocal()
        target_tenant = self.selected_project_source_tenant
        project_row = session.query(ProjectModel).filter(ProjectModel.id == int(self.selected_project_id), ProjectModel.tenant_id == target_tenant).first()
        if not project_row:
            session.close()
            self.toast_message = "Projeto não encontrado para salvar o plano"
            self.toast_type = "error"
            return
        if self.editing_action_plan_id.isdigit():
            action_row = session.query(ActionPlanModel).filter(ActionPlanModel.id == int(self.editing_action_plan_id)).first()
            if not action_row:
                session.close()
                self.toast_message = "Plano nao encontrado para edicao"
                self.toast_type = "error"
                return
            action_row.client_id = int(project_row.client_id) if project_row and project_row.client_id is not None else None
            action_row.service_name = project_row.service_name if project_row else self.selected_project_record["service_name"]
            action_row.dimension_names = ", ".join(self.new_action_dimension_ids) or self.new_action_dimensions.strip()
            action_row.target_area = self.new_action_area.strip()
            action_row.title = action_title
            action_row.owner = action_owner
            action_row.start_date = start_date
            action_row.planned_due_date = planned_due_date
            action_row.due_date = due_date
            action_row.expected_result = self.new_action_expected_result.strip()
            action_row.attainment = attainment
            action_id = int(action_row.id)
        else:
            action_row = ActionPlanModel(
                tenant_id=target_tenant,
                project_id=int(self.selected_project_id),
                client_id=int(project_row.client_id) if project_row and project_row.client_id is not None else None,
                service_name=(project_row.service_name if project_row else self.selected_project_record["service_name"]),
                dimension_names=", ".join(self.new_action_dimension_ids) or self.new_action_dimensions.strip(),
                target_area=self.new_action_area.strip(),
                title=action_title,
                owner=action_owner,
                start_date=start_date,
                planned_due_date=planned_due_date,
                due_date=due_date,
                due_date_change_count=0,
                status="a_fazer",
                expected_result=self.new_action_expected_result.strip(),
                attainment=attainment,
            )
            session.add(action_row)
            session.flush()
            action_id = int(action_row.id)
        session.commit()
        session.close()
        self.selected_action_plan_id = str(action_id)
        self.editing_action_plan_id = ""
        self.new_action_title = ""
        self.new_action_owner = ""
        self.new_action_start_date = ""
        self.new_action_planned_due_date = ""
        self.new_action_due_date = ""
        self.new_action_expected_result = ""
        self.new_action_dimensions = ""
        self.new_action_area = ""
        self.new_action_dimension_ids = []
        self.reset_action_task_form()
        self._append_audit_entry("action.create", f"Ação criada: {action_title}", "operations")
        self.toast_message = "Plano salvo"
        self.toast_type = "success"

    def delete_action_plan(self, action_id: int):
        session = SessionLocal()
        row = session.query(ActionPlanModel).filter(ActionPlanModel.id == int(action_id)).first()
        if not row:
            session.close()
            self.toast_message = "Plano nao encontrado"
            self.toast_type = "error"
            return
        session.query(ActionTaskModel).filter(ActionTaskModel.tenant_id == row.tenant_id, ActionTaskModel.action_plan_id == int(action_id)).delete()
        session.delete(row)
        session.commit()
        session.close()
        if self.selected_action_plan_id == str(action_id) or self.editing_action_plan_id == str(action_id):
            self.cancel_edit_action_plan()
        self.toast_message = "Plano excluido"
        self.toast_type = "success"

    def move_action_status(self, action_id: int, status: str):
        session = SessionLocal()
        row = (
            session.query(ActionPlanModel)
            .filter(ActionPlanModel.id == action_id, ActionPlanModel.tenant_id == self.selected_project_source_tenant)
            .first()
        )
        if not row:
            session.close()
            return
        row.status = status
        if status == "concluido" and row.attainment < 100:
            row.attainment = 100
            row.actual_result = row.actual_result or "Concluído conforme planejado."
        if status == "concluido":
            row.completed_at = row.completed_at or _now_brasilia().strftime("%Y-%m-%d")
        action_title = row.title
        session.commit()
        session.close()
        self._append_audit_entry("action.status", f"Ação '{action_title}' movida para {status}", "operations")
        self.toast_message = "Status atualizado"
        self.toast_type = "success"

    def shift_action_due_date(self, action_id: int, delta_days: int):
        session = SessionLocal()
        row = (
            session.query(ActionPlanModel)
            .filter(ActionPlanModel.id == action_id, ActionPlanModel.tenant_id == self.selected_project_source_tenant)
            .first()
        )
        if not row:
            session.close()
            return
        base_dt = self._parse_iso_date(row.due_date or row.planned_due_date or "")
        if not base_dt:
            session.close()
            self.toast_message = "Plano sem data final para ajustar"
            self.toast_type = "error"
            return
        new_due = base_dt + timedelta(days=int(delta_days))
        row.due_date = new_due.strftime("%Y-%m-%d")
        row.due_date_change_count = int(row.due_date_change_count or 0) + 1
        session.commit()
        session.close()
        self.toast_message = "Prazo atualizado"
        self.toast_type = "success"

    def shift_action_task_due_date(self, task_id: int, delta_days: int):
        session = SessionLocal()
        row = (
            session.query(ActionTaskModel)
            .filter(ActionTaskModel.tenant_id == self.selected_project_source_tenant, ActionTaskModel.id == int(task_id))
            .first()
        )
        if not row:
            session.close()
            return
        base_dt = self._parse_iso_date(row.due_date or row.planned_due_date or "")
        if not base_dt:
            session.close()
            self.toast_message = "Tarefa sem data final para ajustar"
            self.toast_type = "error"
            return
        new_due = base_dt + timedelta(days=int(delta_days))
        row.due_date = new_due.strftime("%Y-%m-%d")
        row.due_date_change_count = int(row.due_date_change_count or 0) + 1
        session.commit()
        session.close()
        self.toast_message = "Prazo da tarefa atualizado"
        self.toast_type = "success"

    def update_action_task_progress(self, action_id: int, task_id: int, new_progress: int):
        session = SessionLocal()
        action_row = (
            session.query(ActionPlanModel)
            .filter(ActionPlanModel.id == action_id, ActionPlanModel.tenant_id == self.selected_project_source_tenant)
            .first()
        )
        if not action_row:
            session.close()
            return
        task_rows = (
            session.query(ActionTaskModel)
            .filter(ActionTaskModel.tenant_id == self.selected_project_source_tenant, ActionTaskModel.action_plan_id == int(action_id))
            .order_by(ActionTaskModel.id.asc())
            .all()
        )
        tasks = [
            {
                "id": int(item.id),
                "title": item.title,
                "owner": item.owner,
                "start_date": item.start_date or "",
                "due_date": item.due_date or "",
                "progress": int(item.progress or 0),
            }
            for item in task_rows
        ]
        target_index = next((idx for idx, item in enumerate(tasks) if int(item["id"]) == int(task_id)), -1)
        if target_index < 0:
            session.close()
            return
        tasks[target_index]["progress"] = max(0, min(100, int(new_progress)))
        target_row = next((item for item in task_rows if int(item.id) == int(task_id)), None)
        if target_row:
            target_row.progress = int(tasks[target_index]["progress"])
        metrics = self._action_progress_metrics(
            action_row.start_date or "",
            action_row.planned_due_date or "",
            action_row.due_date or "",
            tasks,
            int(action_row.attainment or 0),
            action_row.status or "a_fazer",
            action_row.completed_at or "",
        )
        action_row.attainment = int(metrics["overall_progress"])
        if tasks and all(int(item["progress"]) >= 100 for item in tasks):
            action_row.status = "concluido"
            action_row.completed_at = action_row.completed_at or _now_brasilia().strftime("%Y-%m-%d")
            action_row.actual_result = action_row.actual_result or "Concluído conforme execução das tarefas."
        elif any(int(item["progress"]) > 0 for item in tasks):
            action_row.status = "em_andamento"
            action_row.completed_at = ""
        else:
            action_row.status = "a_fazer"
            action_row.completed_at = ""
        session.commit()
        session.close()
        self.toast_message = "Progresso da tarefa atualizado"
        self.toast_type = "success"

    def adjust_action_task_progress(self, action_id: int, task_id: int, delta: int):
        session = SessionLocal()
        task_row = (
            session.query(ActionTaskModel)
            .filter(
                ActionTaskModel.tenant_id == self.selected_project_source_tenant,
                ActionTaskModel.action_plan_id == int(action_id),
                ActionTaskModel.id == int(task_id),
            )
            .first()
        )
        session.close()
        if not task_row:
            return
        self.update_action_task_progress(int(action_id), int(task_id), int(task_row.progress or 0) + int(delta))

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
        interview_counts: dict[int, int] = {}
        for row in session.query(InterviewSessionModel.project_id).filter(InterviewSessionModel.project_id.is_not(None)).all():
            if row[0] is not None:
                interview_counts[int(row[0])] = interview_counts.get(int(row[0]), 0) + 1
        action_counts: dict[int, int] = {}
        for row in session.query(ActionPlanModel.project_id).filter(ActionPlanModel.project_id.is_not(None)).all():
            if row[0] is not None:
                action_counts[int(row[0])] = action_counts.get(int(row[0]), 0) + 1
        workflow_counts: dict[int, int] = {}
        for row in session.query(WorkflowBoxModel.project_id).filter(WorkflowBoxModel.project_id.is_not(None)).all():
            if row[0] is not None:
                workflow_counts[int(row[0])] = workflow_counts.get(int(row[0]), 0) + 1
        knowledge_counts: dict[int, int] = {}
        for row in session.query(AssistantDocumentModel.project_id).filter(AssistantDocumentModel.project_id.is_not(None)).all():
            if row[0] is not None:
                knowledge_counts[int(row[0])] = knowledge_counts.get(int(row[0]), 0) + 1
        data = [
            {
                "id": r.id,
                "id_key": str(r.id),
                "name": r.name,
                "project_type": r.project_type,
                "service_name": r.service_name or "Diagnóstico Cultura de Segurança",
                "client_id": str(r.client_id) if r.client_id is not None else "",
                "client_name": self.client_lookup.get(str(r.client_id), "-") if r.client_id is not None else "-",
                "contracted_at": _format_display_date(r.contracted_at),
                "status": r.status,
                "progress": r.progress,
                "source_tenant": r.tenant_id,
                "assigned_client_ids": assignment_lookup.get(r.id, []),
                "assigned_clients": ", ".join(
                    self.client_lookup.get(client_id, client_id)
                    for client_id in assignment_lookup.get(r.id, [])
                ) or "-",
                "interview_count": str(interview_counts.get(int(r.id), 0)),
                "action_count": str(action_counts.get(int(r.id), 0)),
                "workflow_count": str(workflow_counts.get(int(r.id), 0)),
                "knowledge_count": str(knowledge_counts.get(int(r.id), 0)),
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var
    def project_id_options(self) -> list[str]:
        return [f'{p["id"]} - {p["name"]}' for p in self.projects_data]

    @rx.var(cache=False)
    def project_portfolio_service_options(self) -> list[str]:
        services = sorted({str(item.get("service_name") or "").strip() for item in self.projects_data if str(item.get("service_name") or "").strip()})
        return ["Todos", *services]

    @rx.var(cache=False)
    def filtered_projects_data(self) -> list[dict[str, Any]]:
        if self.project_portfolio_service_filter == "Todos":
            return self.projects_data
        return [
            item
            for item in self.projects_data
            if str(item.get("service_name") or "").strip() == self.project_portfolio_service_filter
        ]

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
        return self._is_resource_allowed("Gerenciar Projetos")

    @rx.var(cache=False)
    def smartlab_service_options(self) -> list[str]:
        session = SessionLocal()
        names: set[str] = {"Diagnóstico Cultura de Segurança"}
        for row in session.query(SurveyModel.service_name).all():
            if row[0]:
                names.add(str(row[0]).strip())
        for row in session.query(ProjectModel.service_name).all():
            if row[0]:
                names.add(str(row[0]).strip())
        for row in session.query(ActionPlanModel.service_name).all():
            if row[0]:
                names.add(str(row[0]).strip())
        session.close()
        names.update(self._catalog_options("smartlab_service"))
        dynamic_options = [name for name in sorted(names) if name and name != "Diagnóstico Cultura de Segurança"]
        return ["Diagnóstico Cultura de Segurança", "Outro", *dynamic_options]

    @rx.var
    def effective_new_form_service_name(self) -> str:
        if self.new_form_custom_category.strip():
            return self.new_form_custom_category.strip()
        if self.new_form_category == "Outro":
            return self.new_form_custom_category.strip() or "Diagnóstico Cultura de Segurança"
        return self.new_form_category

    @rx.var
    def effective_new_project_service_name(self) -> str:
        if self.new_project_custom_service_name.strip():
            return self.new_project_custom_service_name.strip()
        if self.new_project_service_name == "Outro":
            return self.new_project_custom_service_name.strip() or "Diagnóstico Cultura de Segurança"
        return self.new_project_service_name

    @rx.var(cache=False)
    def survey_stage_options(self) -> list[str]:
        session = SessionLocal()
        names = {
            "Visita Técnica - Guiada",
            "Entrevista Individual com o Líder",
            "Rodas de Conversa",
        }
        for row in session.query(SurveyModel.stage_name).all():
            if row[0]:
                names.add(str(row[0]).strip())
        session.close()
        names.update(self._catalog_options("survey_stage"))
        dynamic_options = [
            name
            for name in sorted(names)
            if name and name not in {"Visita Técnica - Guiada", "Entrevista Individual com o Líder", "Rodas de Conversa"}
        ]
        return [
            "Visita Técnica - Guiada",
            "Entrevista Individual com o Líder",
            "Rodas de Conversa",
            "Outra",
            *dynamic_options,
        ]

    @rx.var
    def effective_new_form_stage_name(self) -> str:
        if self.new_form_custom_stage.strip():
            return self.new_form_custom_stage.strip()
        if self.new_form_stage == "Outra":
            return "Visita Técnica - Guiada"
        return self.new_form_stage

    @rx.var(cache=False)
    def project_client_options(self) -> list[str]:
        return [f'{item["id"]} - {item["name"]}' for item in self.clients_data]

    @rx.var
    def selected_project_client_option(self) -> str:
        if not self.new_project_client_id:
            return ""
        name = self.client_lookup.get(self.new_project_client_id, "")
        return f"{self.new_project_client_id} - {name}" if name else ""

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
        return ["cadastro", "projetos", "workflow"]

    @rx.var(cache=False)
    def selected_project_record(self) -> dict[str, str]:
        if not self.selected_project_id:
            return {
                "name": "Nenhum projeto selecionado",
                "type": "-",
                "service_name": "-",
                "client_name": "-",
                "contracted_at": "-",
                "status": "-",
                "progress": "0",
                "clients": "-",
            }
        for item in self.projects_data:
            if str(item["id"]) == self.selected_project_id:
                return {
                    "name": item["name"],
                    "type": item["project_type"],
                    "service_name": item["service_name"],
                    "client_name": item["client_name"],
                    "contracted_at": item["contracted_at"],
                    "status": item["status"],
                    "progress": str(item["progress"]),
                    "clients": item["assigned_clients"],
                }
        return {
            "name": "Projeto nao encontrado",
            "type": "-",
            "service_name": "-",
            "client_name": "-",
            "contracted_at": "-",
            "status": "-",
            "progress": "0",
            "clients": "-",
        }

    @rx.var(cache=False)
    def interview_project_options(self) -> list[str]:
        return [f'{item["id"]} - {item["name"]}' for item in self.projects_data]

    @rx.var(cache=False)
    def selected_interview_project_option(self) -> str:
        if not self.new_interview_project_id:
            return ""
        for item in self.projects_data:
            if str(item["id"]) == self.new_interview_project_id:
                return f'{item["id"]} - {item["name"]}'
        return ""

    @rx.var
    def selected_project_plan_context(self) -> str:
        project = self.selected_project_record
        return (
            f"{project.get('service_name', '-')} | "
            f"Cliente: {project.get('client_name', '-')} | "
            f"Contratado em: {project.get('contracted_at', '-')}"
        )

    @rx.var(cache=False)
    def project_action_people(self) -> list[dict[str, str]]:
        if not self.selected_project_id or not self.selected_project_id.isdigit():
            return []
        session = SessionLocal()
        project = (
            session.query(ProjectModel)
            .filter(
                ProjectModel.id == int(self.selected_project_id),
                ProjectModel.tenant_id == self.selected_project_source_tenant,
            )
            .first()
        )
        assigned_client_ids = {
            str(row[0])
            for row in session.query(ProjectAssignmentModel.client_id).filter(
                ProjectAssignmentModel.project_id == int(self.selected_project_id),
                ProjectAssignmentModel.client_id.is_not(None),
            ).all()
        }
        if project and project.client_id is not None:
            assigned_client_ids.add(str(project.client_id))
        query = session.query(UserModel).filter(UserModel.tenant_id == self.selected_project_source_tenant)
        if assigned_client_ids:
            query = query.filter(UserModel.client_id.in_([int(item) for item in assigned_client_ids if item.isdigit()]))
        rows = query.order_by(UserModel.department.asc(), UserModel.name.asc()).all()
        session.close()
        return [
            {
                "id": str(row.id),
                "label": f"{row.name or row.email} - {row.department or 'Sem área'}",
                "name": row.name or row.email,
                "department": row.department or "Sem área",
                "profession": row.profession or "-",
                "email": row.email,
            }
            for row in rows
        ]

    @rx.var(cache=False)
    def project_action_area_options(self) -> list[str]:
        names = sorted({item["department"] for item in self.project_action_people if item["department"]})
        return names or ["Sem área"]

    @rx.var(cache=False)
    def project_action_owner_options(self) -> list[str]:
        items = self.project_action_people
        if self.new_action_area.strip():
            items = [item for item in items if item["department"] == self.new_action_area.strip()]
        return [item["label"] for item in items]

    @rx.var(cache=False)
    def action_dimension_options(self) -> list[str]:
        items = [item for item in self.question_dimension_options if item not in {"Outro"}]
        return items

    @rx.var
    def selected_action_dimensions_summary(self) -> str:
        if not self.new_action_dimension_ids:
            return "Nenhuma dimensão selecionada"
        return ", ".join(self.new_action_dimension_ids)

    @rx.var(cache=False)
    def action_plan_options(self) -> list[str]:
        return [f'{item["id"]} - {item["title"]}' for item in self.action_plans_data]

    @rx.var
    def selected_action_plan_option(self) -> str:
        if not self.selected_action_plan_id:
            return ""
        target = next((item for item in self.action_plans_data if str(item["id"]) == self.selected_action_plan_id), None)
        if not target:
            return ""
        return f'{target["id"]} - {target["title"]}'

    @rx.var
    def effective_action_plan_target_id(self) -> str:
        return self.editing_action_plan_id or self.selected_action_plan_id

    @rx.var
    def effective_action_plan_target_label(self) -> str:
        target_id = self.effective_action_plan_target_id
        if not target_id:
            return ""
        target = next((item for item in self.action_plans_data if str(item["id"]) == str(target_id)), None)
        if not target:
            return ""
        return f'{target["id"]} - {target["title"]}'

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
    def workflow_hierarchy_snapshot(self) -> list[dict[str, str]]:
        if not self.selected_project_id.isdigit():
            return []
        session = SessionLocal()
        project = session.query(ProjectModel).filter(ProjectModel.id == int(self.selected_project_id)).first()
        assigned_ids = {
            str(row[0])
            for row in session.query(ProjectAssignmentModel.client_id).filter(
                ProjectAssignmentModel.project_id == int(self.selected_project_id),
                ProjectAssignmentModel.client_id.is_not(None),
            ).all()
        }
        if project and project.client_id is not None:
            assigned_ids.add(str(project.client_id))
        client_rows = [row for row in session.query(ClientModel).all() if str(row.id) in assigned_ids]
        parent_names = sorted({self.client_lookup.get(str(row.parent_client_id), "-") for row in client_rows if row.parent_client_id is not None})
        user_rows = [
            row
            for row in session.query(UserModel).filter(UserModel.client_id.is_not(None)).all()
            if str(row.client_id) in assigned_ids
        ]
        departments = sorted({(row.department or "-").strip() for row in user_rows if (row.department or "").strip()})
        professions = sorted({(row.profession or "-").strip() for row in user_rows if (row.profession or "").strip()})
        report_lines = sum(1 for row in user_rows if row.reports_to_user_id is not None)
        session.close()
        return [
            {"label": "Grupo", "value": ", ".join(parent_names) or "Sem grupo", "detail": "estrutura cliente pai cadastrada"},
            {"label": "Empresa", "value": ", ".join(sorted(row.trade_name or row.name for row in client_rows)) or "Sem empresa", "detail": "clientes vinculados ao projeto"},
            {"label": "Área", "value": ", ".join(departments) or "Sem área", "detail": "departamentos vindos dos usuários"},
            {"label": "Usuários", "value": str(len(user_rows)), "detail": "colaboradores vinculados às empresas do projeto"},
            {"label": "Cargos e Reportes", "value": f"{len(professions)} cargos / {report_lines} reportes", "detail": "profissões e linhas de reporte cadastradas"},
        ]

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

    def _workflow_stage_semantics(self, box: dict[str, Any]) -> dict[str, Any]:
        config = dict(box.get("config", {}))
        zone = str(box.get("zone", config.get("zone", "center")))
        if zone not in {"left", "center", "right"}:
            zone = "center"
        context_lookup = {"left": "Preparacao", "center": "Execucao", "right": "Fechamento"}
        stage_type_lookup = {
            "trigger": "Marco de inicio",
            "etapa": "Etapa operacional",
            "coleta": "Coleta e evidencias",
            "analise": "Analise e diagnostico",
            "relatorio": "Devolutiva e plano",
            "nota": "Observacao",
        }
        trigger = (
            str(config.get("trigger", "")).strip()
            or str(config.get("schedule", "")).strip()
            or str(config.get("condition", "")).strip()
            or "Fluxo definido manualmente"
        )
        expected_output = (
            str(config.get("expected_output", "")).strip()
            or str(config.get("output_key", "")).strip()
            or "Sem entrega definida"
        )
        owner = str(config.get("owner", "")).strip() or "Responsavel nao definido"
        objective = str(config.get("objective", "")).strip() or "Objetivo ainda nao detalhado"
        return {
            "id": box["id"],
            "title": str(box.get("title", "")),
            "box_type": str(box.get("box_type", "etapa")),
            "stage_type_label": stage_type_lookup.get(str(box.get("box_type", "etapa")), "Etapa operacional"),
            "position": int(box.get("position", 0) or 0),
            "zone": zone,
            "context": context_lookup.get(zone, "Execucao"),
            "objective": objective,
            "owner": owner,
            "trigger": trigger,
            "expected_output": expected_output,
            "source": str(config.get("source", "manual")),
            "note": str(config.get("note", "")).strip(),
        }

    @rx.var(cache=False)
    def workflow_operational_stages(self) -> list[dict[str, Any]]:
        return [
            self._workflow_stage_semantics(box)
            for box in self.workflow_boxes_data
            if box["box_type"] != "nota"
        ]

    @rx.var(cache=False)
    def workflow_left_stages(self) -> list[dict[str, Any]]:
        return [item for item in self.workflow_operational_stages if item["zone"] == "left"]

    @rx.var(cache=False)
    def workflow_center_stages(self) -> list[dict[str, Any]]:
        return [item for item in self.workflow_operational_stages if item["zone"] == "center"]

    @rx.var(cache=False)
    def workflow_right_stages(self) -> list[dict[str, Any]]:
        return [item for item in self.workflow_operational_stages if item["zone"] == "right"]

    @rx.var(cache=False)
    def workflow_stage_summary(self) -> list[dict[str, str]]:
        stages = self.workflow_operational_stages
        owner_count = sum(1 for item in stages if item["owner"] != "Responsavel nao definido")
        return [
            {
                "label": "Etapas configuradas",
                "value": str(len(stages)),
                "detail": "jornada operacional registrada para o projeto",
            },
            {
                "label": "Responsaveis definidos",
                "value": f"{owner_count}/{len(stages) or 0}",
                "detail": "etapas com dono operacional declarado",
            },
            {
                "label": "Planos de acao",
                "value": str(len(self.action_plans_data)),
                "detail": "itens de follow-up ja cadastrados neste projeto",
            },
            {
                "label": "Cobertura da jornada",
                "value": "Completa" if len(stages) >= 4 else "Parcial",
                "detail": "avaliacao simples para orientar a montagem inicial",
            },
        ]

    @rx.var(cache=False)
    def workflow_stage_templates(self) -> list[dict[str, str]]:
        return [
            {
                "key": item["key"],
                "title": item["title"],
                "context": item["context"],
                "objective": item["objective"],
                "owner": item["owner"],
                "trigger": item["trigger"],
                "expected_output": item["expected_output"],
            }
            for item in WORKFLOW_STAGE_LIBRARY
        ]

    @rx.var(cache=False)
    def workflow_missing_stage_templates(self) -> list[dict[str, str]]:
        existing = {item["title"].casefold() for item in self.workflow_operational_stages}
        return [
            {
                "key": item["key"],
                "title": item["title"],
                "context": item["context"],
                "objective": item["objective"],
                "owner": item["owner"],
                "trigger": item["trigger"],
                "expected_output": item["expected_output"],
            }
            for item in WORKFLOW_STAGE_LIBRARY
            if item["title"].casefold() not in existing
        ]

    def _parse_iso_date(self, raw_value: str | None) -> datetime | None:
        value = str(raw_value or "").strip()
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    def _normalize_action_tasks(self, raw_tasks: list[dict[str, Any]] | Any) -> list[dict[str, Any]]:
        if not isinstance(raw_tasks, list):
            return []
        tasks: list[dict[str, Any]] = []
        for item in raw_tasks:
            if not isinstance(item, dict):
                continue
            progress = max(0, min(100, int(item.get("progress", 0) or 0)))
            tasks.append(
                {
                    "title": str(item.get("title", "")).strip() or "Tarefa sem nome",
                    "owner": str(item.get("owner", "")).strip() or "Responsavel nao definido",
                    "start_date": str(item.get("start_date", "")).strip(),
                    "planned_due_date": str(item.get("planned_due_date", "")).strip(),
                    "due_date": str(item.get("due_date", "")).strip(),
                    "expected_result": str(item.get("expected_result", "")).strip(),
                    "progress": progress,
                }
            )
        return tasks

    def _schedule_progress_percent(self, start_date: str, due_date: str) -> int:
        start_dt = self._parse_iso_date(start_date)
        due_dt = self._parse_iso_date(due_date)
        if not start_dt or not due_dt or due_dt < start_dt:
            return 0
        today = _now_brasilia().date()
        start_day = start_dt.date()
        due_day = due_dt.date()
        if today <= start_day:
            return 0
        total_days = max((due_day - start_day).days, 1)
        elapsed_days = min(max((today - start_day).days, 0), total_days)
        return max(0, min(100, round((elapsed_days / total_days) * 100)))

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
        normalized_tasks = self._normalize_action_tasks(tasks)
        task_progress = round(sum(int(item["progress"]) for item in normalized_tasks) / len(normalized_tasks)) if normalized_tasks else int(attainment or 0)
        schedule_basis = planned_due_date or due_date
        schedule_progress = self._schedule_progress_percent(start_date, schedule_basis)
        overall_progress = 100 if normalized_tasks and all(int(item["progress"]) >= 100 for item in normalized_tasks) else round((task_progress * 0.7) + (schedule_progress * 0.3))
        planned_dt = self._parse_iso_date(planned_due_date)
        current_due_dt = self._parse_iso_date(due_date)
        completed_dt = self._parse_iso_date(completed_at)
        current_variance = (current_due_dt - planned_dt).days if planned_dt and current_due_dt else 0
        completion_variance = (completed_dt - planned_dt).days if planned_dt and completed_dt else 0
        delay_label = "No prazo"
        if status == "concluido" and completed_dt and planned_dt:
            if completion_variance > 0:
                delay_label = f"{completion_variance} dia(s) de atraso"
            elif completion_variance < 0:
                delay_label = f"{abs(completion_variance)} dia(s) antes do prazo"
        elif current_variance > 0:
            delay_label = f"{current_variance} dia(s) prorrogado(s)"
        elif current_variance < 0:
            delay_label = f"{abs(current_variance)} dia(s) antecipado(s)"
        return {
            "tasks": normalized_tasks,
            "task_progress": task_progress,
            "schedule_progress": schedule_progress,
            "overall_progress": max(0, min(100, overall_progress)),
            "current_variance_days": current_variance,
            "completion_variance_days": completion_variance,
            "delay_label": delay_label,
            "task_done_count": sum(1 for item in normalized_tasks if int(item["progress"]) >= 100),
        }

    def _task_delay_label(self, planned_due_date: str, due_date: str, progress: int) -> str:
        planned_dt = self._parse_iso_date(planned_due_date)
        due_dt = self._parse_iso_date(due_date)
        if not planned_dt or not due_dt:
            return "Prazo nao definido"
        variance = (due_dt - planned_dt).days
        if progress >= 100:
            if variance > 0:
                return f"{variance} dia(s) de atraso"
            if variance < 0:
                return f"{abs(variance)} dia(s) antes do prazo"
            return "Concluida no prazo"
        if variance > 0:
            return f"{variance} dia(s) prorrogado(s)"
        if variance < 0:
            return f"{abs(variance)} dia(s) antecipado(s)"
        return "No prazo"

    @rx.var(cache=False)
    def action_plan_tasks_data(self) -> list[dict[str, Any]]:
        if not self.selected_project_id:
            return []
        session = SessionLocal()
        plan_rows = session.query(
            ActionPlanModel.id,
            ActionPlanModel.title,
            ActionPlanModel.client_id,
            ActionPlanModel.service_name,
            ActionPlanModel.dimension_names,
        ).filter(
            ActionPlanModel.tenant_id == self.selected_project_source_tenant,
            ActionPlanModel.project_id == int(self.selected_project_id),
        ).all()
        plan_ids = [int(row[0]) for row in plan_rows]
        if not plan_ids:
            session.close()
            return []
        plan_lookup = {
            int(plan_id): {
                "plan_title": plan_title,
                "client_name": self.client_lookup.get(str(client_id), "-") if client_id is not None else self.selected_project_record["client_name"],
                "service_name": service_name or self.selected_project_record["service_name"],
                "dimensions": dimension_names or "-",
            }
            for plan_id, plan_title, client_id, service_name, dimension_names in plan_rows
        }
        rows = (
            session.query(ActionTaskModel)
            .filter(
                ActionTaskModel.tenant_id == self.selected_project_source_tenant,
                ActionTaskModel.action_plan_id.in_(plan_ids),
            )
            .order_by(ActionTaskModel.action_plan_id.asc(), ActionTaskModel.id.asc())
            .all()
        )
        data = [
            {
                "id": int(row.id),
                "action_id": int(row.action_plan_id),
                "plan_title": str(plan_lookup.get(int(row.action_plan_id), {}).get("plan_title", "-")),
                "title": row.title,
                "project_name": self.selected_project_record["name"],
                "service_name": str(plan_lookup.get(int(row.action_plan_id), {}).get("service_name", self.selected_project_record["service_name"])),
                "client_name": str(plan_lookup.get(int(row.action_plan_id), {}).get("client_name", self.selected_project_record["client_name"])),
                "owner": row.owner,
                "dimensions": str(plan_lookup.get(int(row.action_plan_id), {}).get("dimensions", "-")),
                "expected_result": row.expected_result or "-",
                "start_date": _format_display_date(row.start_date),
                "planned_due_date": _format_display_date(row.planned_due_date),
                "due_date": _format_display_date(row.due_date),
                "due_date_change_count": int(row.due_date_change_count or 0),
                "progress": int(row.progress or 0),
                "schedule_progress": self._schedule_progress_percent(row.start_date or "", row.planned_due_date or row.due_date or ""),
                "delay_label": self._task_delay_label(row.planned_due_date or row.due_date or "", row.due_date or "", int(row.progress or 0)),
                "status": "concluido" if int(row.progress or 0) >= 100 else ("em_andamento" if int(row.progress or 0) > 0 else "a_fazer"),
            }
            for row in rows
        ]
        session.close()
        return data

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
        task_rows = (
            session.query(ActionTaskModel)
            .filter(
                ActionTaskModel.tenant_id == self.selected_project_source_tenant,
                ActionTaskModel.action_plan_id.in_([int(row.id) for row in rows]) if rows else False,
            )
            .order_by(ActionTaskModel.id.asc())
            .all()
        ) if rows else []
        task_lookup: dict[int, list[dict[str, Any]]] = {}
        for task in task_rows:
            task_lookup.setdefault(int(task.action_plan_id), []).append(
                {
                    "id": int(task.id),
                    "title": task.title,
                    "owner": task.owner,
                    "start_date": task.start_date or "",
                    "due_date": task.due_date or "",
                    "progress": int(task.progress or 0),
                }
            )
        data = [
            {
                **(lambda metrics: {
                    "id": r.id,
                    "title": r.title,
                    "client_name": self.client_lookup.get(str(r.client_id), "-") if r.client_id is not None else self.selected_project_record["client_name"],
                    "service_name": r.service_name or self.selected_project_record["service_name"],
                    "dimensions": r.dimension_names or "-",
                    "target_area": r.target_area or "-",
                    "owner": r.owner,
                    "start_date": _format_display_date(r.start_date),
                    "planned_due_date": _format_display_date(r.planned_due_date),
                    "due_date": _format_display_date(r.due_date),
                    "due_date_change_count": int(r.due_date_change_count or 0),
                    "status": r.status,
                    "expected_result": r.expected_result,
                    "actual_result": r.actual_result,
                    "attainment": int(r.attainment or 0),
                    "progress": int(metrics["overall_progress"]),
                    "schedule_progress": int(metrics["schedule_progress"]),
                    "task_progress": int(metrics["task_progress"]),
                    "delay_label": str(metrics["delay_label"]),
                    "task_count": str(len(metrics["tasks"])),
                    "task_done_count": str(metrics["task_done_count"]),
                    "completed_at": _format_display_date(r.completed_at),
                })(self._action_progress_metrics(
                    r.start_date or "",
                    r.planned_due_date or "",
                    r.due_date or "",
                    task_lookup.get(int(r.id), []),
                    int(r.attainment or 0),
                    r.status or "a_fazer",
                    r.completed_at or "",
                ))
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def action_plan_summary_cards(self) -> list[dict[str, str]]:
        delayed = 0
        for item in self.action_plans_data:
            if "atraso" in item["delay_label"] or "prorrogado" in item["delay_label"]:
                delayed += 1
        avg_progress = round(sum(int(item["progress"]) for item in self.action_plans_data) / len(self.action_plans_data)) if self.action_plans_data else 0
        total_tasks = len(self.action_plan_tasks_data)
        return [
            {"label": "Planos do Projeto", "value": str(len(self.action_plans_data)), "detail": "registros de plano vinculados ao projeto"},
            {"label": "Tarefas dos Planos", "value": str(total_tasks), "detail": "tarefas operacionais vinculadas aos planos"},
            {"label": "Em risco de prazo", "value": str(delayed), "detail": "planos com desvio frente ao prazo base"},
            {"label": "Progresso medio", "value": f"{avg_progress}%", "detail": "media composta entre tarefas e calendario"},
        ]

    @rx.var(cache=False)
    def actions_todo(self) -> list[dict[str, Any]]:
        return [a for a in self.action_plan_tasks_data if a["status"] == "a_fazer"]

    @rx.var(cache=False)
    def actions_doing(self) -> list[dict[str, Any]]:
        return [a for a in self.action_plan_tasks_data if a["status"] == "em_andamento"]

    @rx.var(cache=False)
    def actions_done(self) -> list[dict[str, Any]]:
        return [a for a in self.action_plan_tasks_data if a["status"] == "concluido"]
