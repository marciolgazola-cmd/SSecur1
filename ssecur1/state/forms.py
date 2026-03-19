from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import Any

import reflex as rx

from ssecur1.db import (
    ClientModel,
    FormModel,
    InterviewSessionModel,
    ProjectModel,
    QuestionModel,
    ResponseModel,
    SessionLocal,
    SurveyModel,
    UserModel,
)
from ssecur1.utils import format_display_date as _format_display_date
from ssecur1.utils import loads_json as _loads_json
from ssecur1.utils import now_brasilia as _now_brasilia
from ssecur1.utils import question_payload as _question_payload


class FormStateMixin:
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
        base_options = ["Presença", "Correção", "Reconhecimento", "Comunicação", "Disciplina/Exemplo"]
        session = SessionLocal()
        query = session.query(QuestionModel.dimension).filter(
            QuestionModel.tenant_id == self.current_tenant,
            QuestionModel.dimension.is_not(None),
        )
        if self.selected_form_id.isdigit():
            query = query.filter(QuestionModel.survey_id == int(self.selected_form_id))
        custom_options = [row[0].strip() for row in query.all() if row[0] and row[0].strip()]
        session.close()
        catalog_options = self._catalog_options("question_dimension")
        dynamic_options = sorted({option for option in [*custom_options, *catalog_options] if option not in base_options})
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
            .filter(UserModel.tenant_id == self.current_tenant, UserModel.email == self.new_form_target_user_email)
            .first()
        )
        session.close()
        if not row:
            return self.new_form_target_user_email
        return f"{row[0]} - {row[1] or row[0]}"

    @rx.var
    def is_editing_form(self) -> bool:
        return self.editing_form_id != ""

    @rx.var
    def form_submit_label(self) -> str:
        return "Salvar Alterações" if self.is_editing_form else "Salvar Formulário"

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
                "stage": r.stage_name or "Visita Técnica - Guiada",
                "dimensions": ", ".join(dimension_lookup.get(int(r.id), [])) or "-",
                "has_dim_presenca": "1" if "Presença" in dimension_lookup.get(int(r.id), []) else "0",
                "has_dim_correcao": "1" if "Correção" in dimension_lookup.get(int(r.id), []) else "0",
                "has_dim_reconhecimento": "1" if "Reconhecimento" in dimension_lookup.get(int(r.id), []) else "0",
                "has_dim_comunicacao": "1" if "Comunicação" in dimension_lookup.get(int(r.id), []) else "0",
                "has_dim_disciplina": "1" if "Disciplina/Exemplo" in dimension_lookup.get(int(r.id), []) else "0",
                "question_count": str(question_counts.get(int(r.id), 0)),
                "has_questions": "1" if question_counts.get(int(r.id), 0) > 0 else "0",
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
        return [f'{form["id"]} - {form["name"]} [{form["stage"]}]' for form in self.forms_data]

    @rx.var(cache=False)
    def interview_form_options(self) -> list[str]:
        target_service = ""
        if self.new_interview_project_id.isdigit():
            for item in self.projects_data:
                if str(item["id"]) == self.new_interview_project_id:
                    target_service = str(item.get("service_name") or "").strip()
                    break
        forms = self.forms_data
        if target_service:
            forms = [form for form in forms if str(form.get("category") or "").strip() == target_service]
        return [f'{form["id"]} - {form["name"]} ({form["category"]} | {form["stage"]})' for form in forms]

    @rx.var
    def selected_form_name(self) -> str:
        if not self.selected_form_id:
            return ""
        for form in self.forms_data:
            if str(form["id"]) == self.selected_form_id:
                return f'{form["name"]} | {form["stage"]}'
        return ""

    @rx.var
    def selected_survey_builder_option(self) -> str:
        if not self.selected_form_id:
            return ""
        for form in self.forms_data:
            if str(form["id"]) == self.selected_form_id:
                return f'{form["id"]} - {form["name"]} [{form["stage"]}]'
        return ""

    @rx.var(cache=False)
    def selected_interview_form_option(self) -> str:
        if not self.new_interview_form_id:
            return ""
        for form in self.forms_data:
            if str(form["id"]) == self.new_interview_form_id:
                return f'{form["id"]} - {form["name"]} ({form["category"]} | {form["stage"]})'
        return ""

    @rx.var(cache=False)
    def selected_interview_client_option(self) -> str:
        if not self.new_interview_client_id:
            return ""
        name = self.client_lookup.get(self.new_interview_client_id, "")
        return f"{self.new_interview_client_id} - {name}" if name else ""

    @rx.var(cache=False)
    def selected_interview_client_name(self) -> str:
        if self.new_interview_project_id.isdigit():
            session = SessionLocal()
            row = (
                session.query(ClientModel.name)
                .join(ProjectModel, ProjectModel.client_id == ClientModel.id)
                .filter(ProjectModel.id == int(self.new_interview_project_id), ProjectModel.tenant_id == self.current_tenant)
                .first()
            )
            session.close()
            if row and row[0]:
                return str(row[0]).strip()
        if not self.new_interview_client_id:
            return "-"
        name = self.client_lookup.get(self.new_interview_client_id, "").strip()
        if name:
            return name
        session = SessionLocal()
        row = session.query(ClientModel.name).filter(ClientModel.id == int(self.new_interview_client_id)).first()
        session.close()
        return str(row[0]).strip() if row and row[0] else "-"

    @rx.var(cache=False)
    def selected_interview_stage_name(self) -> str:
        if not self.new_interview_form_id:
            return "-"
        for form in self.forms_data:
            if str(form["id"]) == self.new_interview_form_id:
                return str(form.get("stage") or "-")
        session = SessionLocal()
        row = session.query(SurveyModel.stage_name).filter(SurveyModel.id == int(self.new_interview_form_id)).first()
        session.close()
        return str(row[0]).strip() if row and row[0] else "-"

    @rx.var(cache=False)
    def interview_inline_form_options(self) -> list[str]:
        target_service = ""
        if self.edit_interview_project_id.isdigit():
            session = SessionLocal()
            row = (
                session.query(ProjectModel.service_name)
                .filter(ProjectModel.id == int(self.edit_interview_project_id), ProjectModel.tenant_id == self.current_tenant)
                .first()
            )
            session.close()
            target_service = str(row[0] or "").strip() if row and row[0] else ""
        forms = self.forms_data
        if target_service:
            forms = [form for form in forms if str(form.get("category") or "").strip() == target_service]
        return [f'{form["id"]} - {form["name"]} ({form["category"]} | {form["stage"]})' for form in forms]

    @rx.var(cache=False)
    def selected_edit_interview_form_option(self) -> str:
        if not self.edit_interview_form_id:
            return ""
        for form in self.forms_data:
            if str(form["id"]) == self.edit_interview_form_id:
                return f'{form["id"]} - {form["name"]} ({form["category"]} | {form["stage"]})'
        return ""

    @rx.var(cache=False)
    def selected_edit_interview_project_option(self) -> str:
        if not self.edit_interview_project_id:
            return ""
        for item in self.projects_data:
            if str(item["id"]) == self.edit_interview_project_id:
                return f'{item["id"]} - {item["name"]}'
        return ""

    @rx.var(cache=False)
    def selected_edit_interview_client_name(self) -> str:
        if self.edit_interview_client_id:
            name = self.client_lookup.get(self.edit_interview_client_id, "").strip()
            if name:
                return name
        if self.edit_interview_project_id.isdigit():
            session = SessionLocal()
            row = (
                session.query(ClientModel.name)
                .join(ProjectModel, ProjectModel.client_id == ClientModel.id)
                .filter(ProjectModel.id == int(self.edit_interview_project_id), ProjectModel.tenant_id == self.current_tenant)
                .first()
            )
            session.close()
            if row and row[0]:
                return str(row[0]).strip()
        return "-"

    @rx.var(cache=False)
    def selected_edit_interview_stage_name(self) -> str:
        if not self.edit_interview_form_id:
            return "-"
        for form in self.forms_data:
            if str(form["id"]) == self.edit_interview_form_id:
                return str(form.get("stage") or "-")
        session = SessionLocal()
        row = session.query(SurveyModel.stage_name).filter(SurveyModel.id == int(self.edit_interview_form_id)).first()
        session.close()
        return str(row[0]).strip() if row and row[0] else "-"

    @rx.var
    def interview_status_options(self) -> list[str]:
        return ["em_andamento", "concluida"]

    @rx.var(cache=False)
    def is_new_interview_leadership_stage(self) -> bool:
        return self.selected_interview_stage_name == "Entrevista Individual com o Líder"

    @rx.var(cache=False)
    def is_new_interview_group_stage(self) -> bool:
        return self.selected_interview_stage_name == "Rodas de Conversa"

    @rx.var(cache=False)
    def is_new_interview_visit_stage(self) -> bool:
        return self.selected_interview_stage_name == "Visita Técnica - Guiada"

    @rx.var(cache=False)
    def interview_user_options(self) -> list[str]:
        if not self.new_interview_client_id.isdigit():
            return []
        session = SessionLocal()
        rows = (
            session.query(UserModel.id, UserModel.name, UserModel.email, UserModel.profession)
            .filter(UserModel.account_scope == "cliente", UserModel.client_id == int(self.new_interview_client_id))
            .order_by(UserModel.name.asc())
            .all()
        )
        session.close()
        return [f'{row[0]} - {row[1] or row[2]} ({row[3] or "Sem cargo"})' for row in rows]

    @rx.var(cache=False)
    def active_interview_client_id(self) -> str:
        if not self.selected_interview_id.isdigit():
            return self.new_interview_client_id if self.interview_draft_active else ""
        session = SessionLocal()
        row = (
            session.query(InterviewSessionModel.client_id)
            .filter(InterviewSessionModel.id == int(self.selected_interview_id), InterviewSessionModel.tenant_id == self.current_tenant)
            .first()
        )
        session.close()
        return str(row[0]) if row and row[0] is not None else ""

    @rx.var(cache=False)
    def active_interview_user_options(self) -> list[str]:
        if not self.active_interview_client_id.isdigit():
            return []
        session = SessionLocal()
        rows = (
            session.query(UserModel.id, UserModel.name, UserModel.email, UserModel.profession)
            .filter(UserModel.account_scope == "cliente", UserModel.client_id == int(self.active_interview_client_id))
            .order_by(UserModel.name.asc())
            .all()
        )
        session.close()
        return [f'{row[0]} - {row[1] or row[2]} ({row[3] or "Sem cargo"})' for row in rows]

    @rx.var(cache=False)
    def selected_interview_user_option(self) -> str:
        target_user_id = self.new_interview_user_id
        if not target_user_id.isdigit():
            target_user_id = self.selected_interview_record.get("id", "")
            if self.selected_interview_id.isdigit():
                session = SessionLocal()
                interview_row = (
                    session.query(InterviewSessionModel.interviewee_user_id)
                    .filter(InterviewSessionModel.id == int(self.selected_interview_id), InterviewSessionModel.tenant_id == self.current_tenant)
                    .first()
                )
                session.close()
                target_user_id = str(interview_row[0]) if interview_row and interview_row[0] is not None else ""
        if not target_user_id.isdigit():
            return ""
        session = SessionLocal()
        row = session.query(UserModel.id, UserModel.name, UserModel.email, UserModel.profession).filter(UserModel.id == int(target_user_id)).first()
        session.close()
        if not row:
            return ""
        return f'{row[0]} - {row[1] or row[2]} ({row[3] or "Sem cargo"})'

    @rx.var(cache=False)
    def interview_area_options(self) -> list[str]:
        if not self.new_interview_client_id.isdigit():
            return []
        session = SessionLocal()
        rows = (
            session.query(UserModel.department)
            .filter(UserModel.account_scope == "cliente", UserModel.client_id == int(self.new_interview_client_id), UserModel.department.is_not(None))
            .all()
        )
        session.close()
        values = sorted({str(row[0]).strip() for row in rows if row[0] and str(row[0]).strip()})
        values.extend(option for option in self._catalog_options("user_department") if option not in values)
        return values

    @rx.var(cache=False)
    def active_interview_area_options(self) -> list[str]:
        client_id = self.active_interview_client_id
        if not client_id.isdigit():
            return []
        session = SessionLocal()
        rows = (
            session.query(UserModel.department)
            .filter(UserModel.account_scope == "cliente", UserModel.client_id == int(client_id), UserModel.department.is_not(None))
            .all()
        )
        session.close()
        values = sorted({str(row[0]).strip() for row in rows if row[0] and str(row[0]).strip()})
        values.extend(option for option in self._catalog_options("user_department") if option not in values)
        return values

    @rx.var(cache=False)
    def selected_interview_area_option(self) -> str:
        if self.new_interview_area:
            return self.new_interview_area
        return self.selected_interview_record.get("target_area", "")

    @rx.var(cache=False)
    def active_interview_group_name(self) -> str:
        if self.new_interview_group_name:
            return self.new_interview_group_name
        return self.selected_interview_record.get("audience_group", "")

    @rx.var(cache=False)
    def active_interview_requires_user(self) -> bool:
        return self.selected_interview_record["stage_name"] == "Entrevista Individual com o Líder"

    @rx.var(cache=False)
    def active_interview_is_group_stage(self) -> bool:
        return self.selected_interview_record["stage_name"] in {"Rodas de Conversa", "Rodada de Conversa"}

    @rx.var(cache=False)
    def active_interview_is_visit_stage(self) -> bool:
        return self.selected_interview_record["stage_name"] == "Visita Técnica - Guiada"

    @rx.var(cache=False)
    def active_interview_context_ready(self) -> bool:
        if not self.selected_interview_id.isdigit():
            if not self.interview_draft_active:
                return False
            stage_name = self.selected_interview_stage_name
            if stage_name == "Entrevista Individual com o Líder":
                return self.new_interview_user_id.isdigit()
            if stage_name == "Visita Técnica - Guiada":
                return bool(self.new_interview_area.strip())
            if stage_name in {"Rodas de Conversa", "Rodada de Conversa"}:
                return bool(self.new_interview_area.strip() and self.new_interview_group_name.strip())
            return False
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(InterviewSessionModel.id == int(self.selected_interview_id), InterviewSessionModel.tenant_id == self.current_tenant)
            .first()
        )
        survey = None
        if interview and interview.survey_id is not None:
            survey = session.query(SurveyModel).filter(SurveyModel.id == int(interview.survey_id)).first()
        session.close()
        if not interview:
            return False
        stage_name = survey.stage_name if survey and survey.stage_name else self.selected_interview_record["stage_name"]
        if stage_name == "Entrevista Individual com o Líder":
            return bool(interview.interviewee_user_id)
        if stage_name == "Visita Técnica - Guiada":
            return bool((interview.target_area or "").strip())
        if stage_name in {"Rodas de Conversa", "Rodada de Conversa"}:
            return bool((interview.target_area or "").strip() and (interview.audience_group or "").strip())
        return False

    def reset_form_builder(self):
        self.editing_form_id = ""
        self.new_form_name = ""
        self.new_form_category = "Diagnóstico Cultura de Segurança"
        self.new_form_custom_category = ""
        self.new_form_stage = "Visita Técnica - Guiada"
        self.new_form_custom_stage = ""
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
        self.new_interview_project_id = ""
        self.new_interview_client_id = ""
        self.new_interview_user_id = ""
        self.new_interview_area = ""
        self.new_interview_group_name = ""
        self.new_interview_date = ""
        self.new_interview_notes = ""
        self.interview_draft_active = False
        self.interview_score_touched_ids = []

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
        self.new_form_stage = row.stage_name or "Visita Técnica - Guiada"
        self.new_form_custom_stage = ""
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

    def cancel_edit_question(self):
        self.editing_question_id = ""
        self.new_question_text = ""
        self.new_question_dimension = "Presença"
        self.new_question_custom_dimension = ""
        self.new_question_type = "escala_0_5"
        self.new_question_polarity = "positiva"
        self.new_question_weight = "1"
        self.new_question_options = "Nada Aderente,Pouco Aderente,Parcialmente Aderente,Moderadamente Aderente,Muito Aderente,Totalmente Aderente"
        self.new_question_condition = ""

    def set_new_form_name(self, value: str):
        self.new_form_name = value

    def set_new_form_stage(self, value: str):
        self.new_form_stage = value
        if value != "Outra":
            self.new_form_custom_stage = ""
        if not self.selected_form_id.isdigit() or value == "Outra":
            return
        session = SessionLocal()
        survey = (
            session.query(SurveyModel)
            .filter(SurveyModel.id == int(self.selected_form_id), SurveyModel.tenant_id == self.current_tenant)
            .first()
        )
        if survey:
            survey.stage_name = value
            session.commit()
        session.close()

    def set_new_form_custom_stage(self, value: str):
        self.new_form_custom_stage = value

    def confirm_new_form_stage(self):
        value = self._register_catalog_option("survey_stage", self.new_form_custom_stage)
        if not value:
            self.toast_message = "Informe a etapa antes de confirmar"
            self.toast_type = "error"
            return
        self.new_form_stage = value
        self.new_form_custom_stage = ""
        if self.selected_form_id.isdigit():
            session = SessionLocal()
            survey = (
                session.query(SurveyModel)
                .filter(SurveyModel.id == int(self.selected_form_id), SurveyModel.tenant_id == self.current_tenant)
                .first()
            )
            if survey:
                survey.stage_name = value
                session.commit()
            session.close()
        self.toast_message = "Etapa registrada e disponível na lista"
        self.toast_type = "success"

    def set_new_form_category(self, value: str):
        self.new_form_category = value
        if value != "Outro":
            self.new_form_custom_category = ""

    def set_new_form_custom_category(self, value: str):
        self.new_form_custom_category = value

    def confirm_new_form_category(self):
        value = self._register_catalog_option("smartlab_service", self.new_form_custom_category)
        if not value:
            self.toast_message = "Informe o serviço antes de confirmar"
            self.toast_type = "error"
            return
        self.new_form_category = value
        self.new_form_custom_category = ""
        if self.editing_form_id.isdigit():
            session = SessionLocal()
            survey = (
                session.query(SurveyModel)
                .filter(SurveyModel.id == int(self.editing_form_id), SurveyModel.tenant_id == self.current_tenant)
                .first()
            )
            if survey:
                survey.service_name = value
                session.commit()
            session.close()
        self.toast_message = "Serviço registrado e disponível na lista"
        self.toast_type = "success"

    def set_new_form_target_client_option(self, value: str):
        self.new_form_target_client_id = value.split(" - ", 1)[0].strip() if value else ""

    def set_new_form_target_user_option(self, value: str):
        self.new_form_target_user_email = value.split(" - ", 1)[0].strip() if value else ""

    def set_new_interview_form_option(self, value: str):
        self.new_interview_form_id = value.split(" - ", 1)[0].strip() if value else ""
        self.new_interview_user_id = ""
        self.new_interview_area = ""
        self.new_interview_group_name = ""

    def set_new_interview_project_option(self, value: str):
        self.new_interview_project_id = value.split(" - ", 1)[0].strip() if value else ""
        self.new_interview_form_id = ""
        self.new_interview_user_id = ""
        self.new_interview_area = ""
        self.new_interview_group_name = ""
        self.new_interview_notes = self.new_interview_notes
        if not self.new_interview_project_id.isdigit():
            self.new_interview_client_id = ""
            return
        session = SessionLocal()
        project = (
            session.query(ProjectModel.client_id)
            .filter(ProjectModel.id == int(self.new_interview_project_id), ProjectModel.tenant_id == self.current_tenant)
            .first()
        )
        session.close()
        self.new_interview_client_id = str(project[0]) if project and project[0] is not None else ""
        self.interview_draft_active = False

    def set_new_interview_date(self, value: str):
        self.new_interview_date = value

    def set_new_interview_user_option(self, value: str):
        self.new_interview_user_id = value.split(" - ", 1)[0].strip() if value else ""

    def set_new_interview_area(self, value: str):
        self.new_interview_area = value

    def set_new_interview_group_name(self, value: str):
        self.new_interview_group_name = value

    def set_edit_interview_form_option(self, value: str):
        self.edit_interview_form_id = value.split(" - ", 1)[0].strip() if value else ""

    def set_edit_interview_project_option(self, value: str):
        self.edit_interview_project_id = value.split(" - ", 1)[0].strip() if value else ""
        self.edit_interview_form_id = ""
        if not self.edit_interview_project_id.isdigit():
            self.edit_interview_client_id = ""
            return
        session = SessionLocal()
        row = (
            session.query(ProjectModel.client_id)
            .filter(ProjectModel.id == int(self.edit_interview_project_id), ProjectModel.tenant_id == self.current_tenant)
            .first()
        )
        session.close()
        self.edit_interview_client_id = str(row[0]) if row and row[0] is not None else ""

    def set_edit_interview_date(self, value: str):
        self.edit_interview_date = value

    def set_edit_interview_status(self, value: str):
        self.edit_interview_status = value or "em_andamento"

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

    def confirm_new_question_dimension(self):
        value = self._register_catalog_option("question_dimension", self.new_question_custom_dimension)
        if not value:
            self.toast_message = "Informe a dimensão antes de confirmar"
            self.toast_type = "error"
            return
        self.new_question_dimension = value
        self.new_question_custom_dimension = ""
        if self.editing_question_id.isdigit():
            session = SessionLocal()
            question = (
                session.query(QuestionModel)
                .filter(QuestionModel.id == int(self.editing_question_id), QuestionModel.tenant_id == self.current_tenant)
                .first()
            )
            if question:
                question.dimension = value
                session.commit()
            session.close()
        self.toast_message = "Dimensão registrada e disponível na lista"
        self.toast_type = "success"

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
        if str(question_id) not in self.interview_score_touched_ids:
            self.interview_score_touched_ids = [*self.interview_score_touched_ids, str(question_id)]

    def create_form(self):
        if not self.can_manage_forms:
            self.toast_message = "Sem permissão para criar pesquisas"
            self.toast_type = "error"
            return
        if not self.new_form_name:
            self.toast_message = "Informe o nome da pesquisa"
            self.toast_type = "error"
            return
        service_name = self.effective_new_form_service_name.strip()
        stage_name = self.effective_new_form_stage_name.strip()
        if self.new_form_category == "Outro" and not self.new_form_custom_category.strip():
            self.toast_message = "Informe o nome do novo serviço SmartLab"
            self.toast_type = "error"
            return
        if self.new_form_stage == "Outra" and not self.new_form_custom_stage.strip():
            self.toast_message = "Informe o nome da nova etapa da pesquisa"
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
            survey.service_name = service_name
            survey.stage_name = stage_name
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
            category=service_name,
            target_client_id=None,
            target_user_email=None,
        )
        session.add(legacy_form)
        session.commit()
        session.refresh(legacy_form)
        survey = SurveyModel(
            tenant_id=self.current_tenant,
            name=self.new_form_name.strip(),
            service_name=service_name,
            stage_name=stage_name,
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
        if not self.can_delete_forms:
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
        if not self.selected_form_id.isdigit():
            self.new_form_stage = "Visita Técnica - Guiada"
            self.new_form_custom_stage = ""
            return
        available_stages = {stage for stage in self.survey_stage_options if stage != "Outra"}
        for form in self.forms_data:
            if str(form["id"]) == self.selected_form_id:
                stage = form.get("stage", "Visita Técnica - Guiada")
                if stage in available_stages:
                    self.new_form_stage = stage
                    self.new_form_custom_stage = ""
                else:
                    self.new_form_stage = "Outra"
                    self.new_form_custom_stage = stage
                break

    def select_form_by_id(self, form_id: int):
        self.selected_form_id = str(form_id)
        available_stages = {stage for stage in self.survey_stage_options if stage != "Outra"}
        for form in self.forms_data:
            if str(form["id"]) == str(form_id):
                stage = form.get("stage", "Visita Técnica - Guiada")
                if stage in available_stages:
                    self.new_form_stage = stage
                    self.new_form_custom_stage = ""
                else:
                    self.new_form_stage = "Outra"
                    self.new_form_custom_stage = stage
                break

    def create_interview_session(self):
        if not self.can_operate_interviews:
            self.toast_message = "Somente consultores SmartLab podem registrar entrevistas"
            self.toast_type = "error"
            return
        if not self.new_interview_project_id.isdigit():
            self.toast_message = "Selecione o projeto contratado pelo cliente"
            self.toast_type = "error"
            return
        if not self.new_interview_client_id.isdigit():
            self.toast_message = "O cliente precisa ser derivado do projeto selecionado"
            self.toast_type = "error"
            return
        if not self.new_interview_form_id.isdigit():
            self.toast_message = "Selecione a pesquisa base da aplicação"
            self.toast_type = "error"
            return
        session = SessionLocal()
        survey = (
            session.query(SurveyModel)
            .filter(SurveyModel.id == int(self.new_interview_form_id), SurveyModel.tenant_id == self.current_tenant)
            .first()
        )
        project = (
            session.query(ProjectModel)
            .filter(ProjectModel.id == int(self.new_interview_project_id), ProjectModel.tenant_id == self.current_tenant)
            .first()
        )
        if not survey:
            session.close()
            self.toast_message = "Pesquisa nao encontrada"
            self.toast_type = "error"
            return
        if not project:
            session.close()
            self.toast_message = "Projeto contratado nao encontrado"
            self.toast_type = "error"
            return
        if project.client_id is not None and int(project.client_id) != int(self.new_interview_client_id):
            session.close()
            self.toast_message = "O projeto selecionado não pertence ao cliente informado"
            self.toast_type = "error"
            return
        session.close()
        self.selected_interview_id = ""
        self.selected_form_id = self.new_interview_form_id
        self.interview_answer_map = {}
        self.interview_score_map = {}
        self.interview_score_touched_ids = []
        self.interview_draft_active = True
        self.toast_message = "Entrevista preparada. Defina o contexto e depois clique em Salvar."
        self.toast_type = "success"

    def update_active_interview_context(self):
        if not self.selected_interview_id.isdigit() and not self.interview_draft_active:
            self.toast_message = "Selecione uma entrevista ativa"
            self.toast_type = "error"
            return
        if not self.selected_interview_id.isdigit() and self.interview_draft_active:
            stage_name = self.selected_interview_stage_name
            if stage_name == "Entrevista Individual com o Líder":
                if not self.new_interview_user_id.isdigit():
                    self.toast_message = "Selecione o usuário respondente"
                    self.toast_type = "error"
                    return
            elif stage_name == "Visita Técnica - Guiada":
                if not self.new_interview_area.strip():
                    self.toast_message = "Selecione a área observada"
                    self.toast_type = "error"
                    return
            elif stage_name in {"Rodas de Conversa", "Rodada de Conversa"}:
                if not self.new_interview_area.strip():
                    self.toast_message = "Selecione a área da rodada"
                    self.toast_type = "error"
                    return
                if not self.new_interview_group_name.strip():
                    self.toast_message = "Informe o grupo entrevistado"
                    self.toast_type = "error"
                    return
            self.toast_message = "Contexto da entrevista preparado"
            self.toast_type = "success"
            return
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(InterviewSessionModel.id == int(self.selected_interview_id), InterviewSessionModel.tenant_id == self.current_tenant)
            .first()
        )
        if not interview:
            session.close()
            self.toast_message = "Entrevista nao encontrada"
            self.toast_type = "error"
            return
        survey = None
        if interview.survey_id is not None:
            survey = session.query(SurveyModel).filter(SurveyModel.id == int(interview.survey_id)).first()
        stage_name = survey.stage_name if survey and survey.stage_name else self.selected_interview_record["stage_name"]
        if stage_name == "Entrevista Individual com o Líder":
            if not self.new_interview_user_id.isdigit():
                session.close()
                self.toast_message = "Selecione o usuário respondente"
                self.toast_type = "error"
                return
            user = (
                session.query(UserModel)
                .filter(UserModel.id == int(self.new_interview_user_id), UserModel.account_scope == "cliente")
                .first()
            )
            if not user:
                session.close()
                self.toast_message = "Usuário não encontrado"
                self.toast_type = "error"
                return
            if interview.client_id is not None and user.client_id != int(interview.client_id):
                session.close()
                self.toast_message = "O usuário selecionado não pertence ao cliente da entrevista"
                self.toast_type = "error"
                return
            interview.interviewee_user_id = int(user.id)
            interview.interviewee_name = user.name or user.email
            interview.interviewee_role = user.profession or user.department or None
            toast_message = "Respondente vinculado à entrevista"
        elif stage_name == "Visita Técnica - Guiada":
            if not self.new_interview_area.strip():
                session.close()
                self.toast_message = "Selecione a área observada"
                self.toast_type = "error"
                return
            interview.interviewee_user_id = None
            interview.target_area = self.new_interview_area.strip()
            interview.audience_group = ""
            interview.interviewee_name = f"Área: {self.new_interview_area.strip()}"
            interview.interviewee_role = "Observação em campo"
            toast_message = "Área da visita atualizada"
        elif stage_name in {"Rodas de Conversa", "Rodada de Conversa"}:
            if not self.new_interview_area.strip():
                session.close()
                self.toast_message = "Selecione a área da rodada"
                self.toast_type = "error"
                return
            if not self.new_interview_group_name.strip():
                session.close()
                self.toast_message = "Informe o grupo entrevistado"
                self.toast_type = "error"
                return
            interview.interviewee_user_id = None
            interview.target_area = self.new_interview_area.strip()
            interview.audience_group = self.new_interview_group_name.strip()
            interview.interviewee_name = self.new_interview_group_name.strip()
            interview.interviewee_role = self.new_interview_area.strip()
            toast_message = "Contexto da rodada atualizado"
        else:
            session.close()
            self.toast_message = "Etapa da entrevista nao suporta vínculo de contexto"
            self.toast_type = "error"
            return
        session.commit()
        session.close()
        self.select_interview_session(self.selected_interview_id)
        self.toast_message = toast_message
        self.toast_type = "success"

    def _clear_active_interview_state(self):
        self.selected_interview_id = ""
        self.selected_form_id = ""
        self.interview_answer_map = {}
        self.interview_score_map = {}
        self.interview_score_touched_ids = []
        self.editing_interview_id = ""
        self.cancel_table_edit_interview()
        self.reset_interview_form()

    def cancel_active_interview(self):
        self._clear_active_interview_state()
        self.toast_message = "Entrevista cancelada"
        self.toast_type = "success"

    def _create_interview_session_record(self, session) -> InterviewSessionModel | None:
        if not self.new_interview_form_id.isdigit() or not self.new_interview_project_id.isdigit() or not self.new_interview_client_id.isdigit():
            return None
        survey = (
            session.query(SurveyModel)
            .filter(SurveyModel.id == int(self.new_interview_form_id), SurveyModel.tenant_id == self.current_tenant)
            .first()
        )
        if not survey:
            return None
        stage_name = survey.stage_name or "Visita Técnica - Guiada"
        interviewee_name = "-"
        interviewee_role = None
        interviewee_user_id = int(self.new_interview_user_id) if self.new_interview_user_id.isdigit() else None
        if stage_name == "Entrevista Individual com o Líder":
            interviewee = (
                session.query(UserModel)
                .filter(UserModel.id == int(self.new_interview_user_id), UserModel.account_scope == "cliente")
                .first()
            )
            if not interviewee or interviewee.client_id != int(self.new_interview_client_id):
                return None
            interviewee_name = interviewee.name or interviewee.email
            interviewee_role = interviewee.profession or interviewee.department or None
        elif stage_name in {"Rodas de Conversa", "Rodada de Conversa"}:
            interviewee_user_id = None
            interviewee_name = self.new_interview_group_name.strip()
            interviewee_role = self.new_interview_area.strip() or None
        elif stage_name == "Visita Técnica - Guiada":
            interviewee_user_id = None
            interviewee_name = f"Área: {self.new_interview_area.strip()}"
            interviewee_role = "Observação em campo"
        interview = InterviewSessionModel(
            tenant_id=self.current_tenant,
            form_id=int(survey.legacy_form_id or 0),
            survey_id=int(self.new_interview_form_id),
            project_id=int(self.new_interview_project_id),
            client_id=int(self.new_interview_client_id),
            interviewee_user_id=interviewee_user_id,
            target_area=self.new_interview_area.strip() or None,
            audience_group=self.new_interview_group_name.strip() or None,
            interview_date=self.new_interview_date.strip() or _now_brasilia().strftime("%Y-%m-%d"),
            interviewee_name=interviewee_name,
            interviewee_role=interviewee_role,
            consultant_name=self.login_email.strip().lower() or "consultor@smartlab.com",
            status="em_andamento",
            notes=self.new_interview_notes.strip(),
        )
        session.add(interview)
        session.flush()
        return interview

    def start_table_edit_interview(self, interview_id: str):
        if not str(interview_id).isdigit():
            self.toast_message = "Entrevista invalida"
            self.toast_type = "error"
            return
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(InterviewSessionModel.id == int(interview_id), InterviewSessionModel.tenant_id == self.current_tenant)
            .first()
        )
        session.close()
        if not interview:
            self.toast_message = "Entrevista nao encontrada"
            self.toast_type = "error"
            return
        self.editing_interview_table_id = str(interview.id)
        self.edit_interview_form_id = str(interview.survey_id or "")
        self.edit_interview_project_id = str(interview.project_id or "")
        self.edit_interview_client_id = str(interview.client_id or "")
        self.edit_interview_date = interview.interview_date or ""
        self.edit_interview_status = interview.status or "em_andamento"
        self.select_interview_session(str(interview.id))

    def cancel_table_edit_interview(self):
        self.editing_interview_table_id = ""
        self.edit_interview_form_id = ""
        self.edit_interview_project_id = ""
        self.edit_interview_client_id = ""
        self.edit_interview_date = ""
        self.edit_interview_status = "em_andamento"

    def _save_interview_inline_internal(self, show_toast: bool = True) -> bool:
        if not self.editing_interview_table_id.isdigit():
            if show_toast:
                self.toast_message = "Nenhuma entrevista em edição"
                self.toast_type = "error"
            return False
        if not self.edit_interview_project_id.isdigit():
            if show_toast:
                self.toast_message = "Selecione o projeto contratado"
                self.toast_type = "error"
            return False
        if not self.edit_interview_form_id.isdigit():
            if show_toast:
                self.toast_message = "Selecione a pesquisa"
                self.toast_type = "error"
            return False
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(InterviewSessionModel.id == int(self.editing_interview_table_id), InterviewSessionModel.tenant_id == self.current_tenant)
            .first()
        )
        project = (
            session.query(ProjectModel)
            .filter(ProjectModel.id == int(self.edit_interview_project_id), ProjectModel.tenant_id == self.current_tenant)
            .first()
        )
        survey = (
            session.query(SurveyModel)
            .filter(SurveyModel.id == int(self.edit_interview_form_id), SurveyModel.tenant_id == self.current_tenant)
            .first()
        )
        if not interview or not project or not survey:
            session.close()
            if show_toast:
                self.toast_message = "Entrevista, projeto ou pesquisa não encontrados"
                self.toast_type = "error"
            return False
        interview.project_id = int(project.id)
        interview.client_id = int(project.client_id) if project.client_id is not None else None
        interview.survey_id = int(survey.id)
        interview.form_id = int(survey.legacy_form_id or 0)
        interview.interview_date = self.edit_interview_date.strip() or interview.interview_date or _now_brasilia().strftime("%Y-%m-%d")
        interview.status = self.edit_interview_status or "em_andamento"
        session.commit()
        session.close()
        if self.selected_interview_id == self.editing_interview_table_id:
            self.select_interview_session(self.selected_interview_id)
        if show_toast:
            self.cancel_table_edit_interview()
            self.toast_message = "Entrevista atualizada"
            self.toast_type = "success"
        return True

    def save_interview_inline(self):
        metadata_saved = self._save_interview_inline_internal(show_toast=False)
        if not metadata_saved:
            return
        saved_responses = True
        if self.selected_interview_id == self.editing_interview_table_id:
            saved_responses = self._save_interview_responses_internal()
        if not saved_responses:
            return
        self._clear_active_interview_state()
        self.toast_message = "Entrevista atualizada"
        self.toast_type = "success"

    def start_edit_interview(self, interview_id: str):
        if not str(interview_id).isdigit():
            self.toast_message = "Entrevista invalida"
            self.toast_type = "error"
            return
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(InterviewSessionModel.id == int(interview_id), InterviewSessionModel.tenant_id == self.current_tenant)
            .first()
        )
        if not interview:
            session.close()
            self.toast_message = "Entrevista nao encontrada"
            self.toast_type = "error"
            return
        self.new_interview_project_id = str(interview.project_id or "")
        response_rows = (
            session.query(ResponseModel)
            .filter(ResponseModel.tenant_id == self.current_tenant, ResponseModel.interview_id == int(interview_id))
            .all()
        )
        session.close()
        self.editing_interview_id = str(interview.id)
        self.selected_interview_id = str(interview.id)
        self.selected_form_id = str(interview.survey_id or "")
        self.new_interview_form_id = str(interview.survey_id or "")
        self.new_interview_client_id = str(interview.client_id or "")
        self.new_interview_user_id = str(interview.interviewee_user_id or "")
        self.new_interview_area = interview.target_area or ""
        self.new_interview_group_name = interview.audience_group or ""
        self.new_interview_date = interview.interview_date or ""
        self.new_interview_notes = interview.notes or ""
        self.interview_draft_active = False
        self.interview_answer_map = {str(row.question_id): row.answer or "" for row in response_rows if row.question_id is not None}
        self.interview_score_map = {str(row.question_id): str(row.score if row.score is not None else 0) for row in response_rows if row.question_id is not None}
        self.interview_score_touched_ids = [str(row.question_id) for row in response_rows if row.question_id is not None]
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
            .filter(InterviewSessionModel.id == int(interview_id), InterviewSessionModel.tenant_id == self.current_tenant)
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
            self.interview_score_touched_ids = []
            self.interview_draft_active = False
        if self.editing_interview_id == str(interview_id):
            self.reset_interview_form()
        self.toast_message = "Entrevista excluida"
        self.toast_type = "success"

    def select_interview_session(self, interview_id: str):
        self.selected_interview_id = str(interview_id)
        if not str(interview_id).isdigit():
            self.interview_answer_map = {}
            self.interview_score_map = {}
            self.interview_score_touched_ids = []
            self.interview_draft_active = False
            return
        session = SessionLocal()
        interview = (
            session.query(InterviewSessionModel)
            .filter(InterviewSessionModel.id == int(interview_id), InterviewSessionModel.tenant_id == self.current_tenant)
            .first()
        )
        if interview:
            self.interview_draft_active = False
            self.selected_form_id = str(interview.survey_id or "")
            self.new_interview_project_id = str(interview.project_id or "")
            self.new_interview_form_id = str(interview.survey_id or "")
            self.new_interview_client_id = str(interview.client_id or "")
            self.new_interview_user_id = str(interview.interviewee_user_id or "")
            self.new_interview_area = interview.target_area or ""
            self.new_interview_group_name = interview.audience_group or ""
            self.new_interview_date = interview.interview_date or ""
            self.new_interview_notes = interview.notes or ""
            response_rows = (
                session.query(ResponseModel)
                .filter(ResponseModel.tenant_id == self.current_tenant, ResponseModel.interview_id == int(interview_id))
                .all()
            )
            self.interview_answer_map = {str(row.question_id): row.answer or "" for row in response_rows if row.question_id is not None}
            self.interview_score_map = {str(row.question_id): str(row.score if row.score is not None else 0) for row in response_rows if row.question_id is not None}
            self.interview_score_touched_ids = [str(row.question_id) for row in response_rows if row.question_id is not None]
        else:
            self.interview_answer_map = {}
            self.interview_score_map = {}
            self.interview_score_touched_ids = []
        session.close()

    def _save_interview_responses_internal(self) -> bool:
        created_draft_record = False
        if not self.selected_interview_id.isdigit():
            if not self.interview_draft_active:
                self.toast_message = "Selecione uma entrevista ativa"
                self.toast_type = "error"
                return False
            if not self.active_interview_context_ready:
                self.toast_message = "Defina o contexto da entrevista antes de salvar"
                self.toast_type = "error"
                return False
        session = SessionLocal()
        if self.selected_interview_id.isdigit():
            interview = (
                session.query(InterviewSessionModel)
                .filter(InterviewSessionModel.id == int(self.selected_interview_id), InterviewSessionModel.tenant_id == self.current_tenant)
                .first()
            )
        else:
            interview = self._create_interview_session_record(session)
            created_draft_record = interview is not None
        if not interview:
            session.close()
            self.toast_message = "Entrevista nao encontrada ou contexto invalido"
            self.toast_type = "error"
            return False
        questions = (
            session.query(QuestionModel)
            .filter(QuestionModel.tenant_id == self.current_tenant, QuestionModel.survey_id == int(interview.survey_id or 0))
            .all()
        )
        survey = None
        if interview.survey_id is not None:
            survey = session.query(SurveyModel).filter(SurveyModel.id == int(interview.survey_id)).first()
        service_name = survey.service_name if survey else self.selected_interview_record["form_name"]
        saved_count = 0
        answered_count = 0
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
            score_touched = question_id in self.interview_score_touched_ids or existing is not None
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
            if score_touched:
                answered_count += 1
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
        interview.status = "concluida" if questions and answered_count == len(questions) else "em_andamento"
        session.commit()
        if created_draft_record:
            self.selected_interview_id = str(interview.id)
            self.interview_draft_active = False
            self.interview_score_touched_ids = [str(question.id) for question in questions if str(question.id) in self.interview_score_touched_ids]
        session.close()
        self.toast_message = "Entrevista e respostas salvas" if created_draft_record else "Respostas da entrevista salvas"
        self.toast_type = "success"
        return True

    def save_interview_responses(self):
        metadata_saved = True
        if self.editing_interview_table_id and self.selected_interview_id == self.editing_interview_table_id:
            metadata_saved = self._save_interview_inline_internal(show_toast=False)
        if not metadata_saved:
            return
        saved = self._save_interview_responses_internal()
        if saved:
            self._clear_active_interview_state()

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
            .filter(InterviewSessionModel.id == int(self.selected_interview_id), InterviewSessionModel.tenant_id == self.current_tenant)
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
        dimension = self.new_question_custom_dimension.strip() if self.new_question_dimension == "Outro" else self.new_question_dimension.strip()
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
        next_order = session.query(QuestionModel).filter(QuestionModel.tenant_id == self.current_tenant, QuestionModel.survey_id == survey_id).count() + 1
        if self.editing_question_id.isdigit():
            question = (
                session.query(QuestionModel)
                .filter(QuestionModel.id == int(self.editing_question_id), QuestionModel.tenant_id == self.current_tenant)
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
            question.options_json = json.dumps({"options": options, "logic": {"show_if": self.new_question_condition.strip()}})
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
                    options_json=json.dumps({"options": options, "logic": {"show_if": self.new_question_condition.strip()}}),
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
