import json
import math
import re
import secrets
import subprocess
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Any

import reflex as rx
from sqlalchemy import or_
from ssecur1.db import (
    ActionPlanModel,
    AssistantChunkModel,
    AssistantDocumentModel,
    ClientModel,
    CustomOptionModel,
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

AUDIT_LOG_PATH = Path(".states") / "audit.log"
EMBED_MODEL = "nomic-embed-text:latest"


def _run_ollama_command(*args: str, input_text: str | None = None, timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            ["ollama", *args],
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return (result.stdout or "").strip()


def _parse_ollama_list(raw_output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = [line.rstrip() for line in raw_output.splitlines() if line.strip()]
    if len(lines) <= 1:
        return rows
    for line in lines[1:]:
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 4:
            continue
        rows.append(
            {
                "name": parts[0],
                "id": parts[1],
                "size": parts[2],
                "modified": parts[3],
            }
        )
    return rows


def _append_audit_file(entry: dict[str, str]) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(entry, ensure_ascii=True) + "\n")


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _extract_text_from_pdf(file_path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", str(file_path), "-"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return _normalize_space(result.stdout)


def _extract_text_from_docx(file_path: Path) -> str:
    try:
        with zipfile.ZipFile(file_path) as archive:
            fragments: list[str] = []
            for member in archive.namelist():
                if not member.startswith("word/") or not member.endswith(".xml"):
                    continue
                if "document.xml" not in member and "header" not in member and "footer" not in member:
                    continue
                root = ET.fromstring(archive.read(member))
                texts = [node.text or "" for node in root.iter() if node.tag.endswith("}t") and (node.text or "").strip()]
                if texts:
                    fragments.append(" ".join(texts))
            return _normalize_space("\n".join(fragments))
    except (OSError, KeyError, ET.ParseError, zipfile.BadZipFile):
        return ""


def _extract_text_from_xlsx(file_path: Path) -> str:
    try:
        with zipfile.ZipFile(file_path) as archive:
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                for item in root.iter():
                    if item.tag.endswith("}t") and item.text:
                        shared_strings.append(item.text)
            fragments: list[str] = []
            for member in archive.namelist():
                if not member.startswith("xl/worksheets/") or not member.endswith(".xml"):
                    continue
                root = ET.fromstring(archive.read(member))
                row_values: list[str] = []
                for cell in root.iter():
                    if not cell.tag.endswith("}c"):
                        continue
                    value_text = ""
                    cell_type = cell.attrib.get("t", "")
                    value_node = next((child for child in cell if child.tag.endswith("}v") and child.text), None)
                    inline_node = next((child for child in cell.iter() if child.tag.endswith("}t") and child.text), None)
                    if cell_type == "s" and value_node is not None:
                        idx = int(value_node.text or "0")
                        if 0 <= idx < len(shared_strings):
                            value_text = shared_strings[idx]
                    elif inline_node is not None:
                        value_text = inline_node.text or ""
                    elif value_node is not None:
                        value_text = value_node.text or ""
                    if value_text.strip():
                        row_values.append(value_text.strip())
                if row_values:
                    sheet_name = Path(member).stem
                    fragments.append(f"{sheet_name}: {' | '.join(row_values)}")
            return _normalize_space("\n".join(fragments))
    except (OSError, ET.ParseError, zipfile.BadZipFile, ValueError):
        return ""


def _extract_text_from_plain(file_path: Path) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return _normalize_space(file_path.read_text(encoding=encoding))
        except OSError:
            return ""
        except UnicodeDecodeError:
            continue
    return ""


def _extract_document_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_from_pdf(file_path)
    if suffix == ".docx":
        return _extract_text_from_docx(file_path)
    if suffix == ".xlsx":
        return _extract_text_from_xlsx(file_path)
    if suffix in {".txt", ".md", ".csv", ".json"}:
        return _extract_text_from_plain(file_path)
    return ""


def _chunk_text(content: str, max_chars: int = 1400, overlap: int = 220) -> list[str]:
    normalized = _normalize_space(content)
    if not normalized:
        return []
    chunks: list[str] = []
    cursor = 0
    length = len(normalized)
    while cursor < length:
        end = min(length, cursor + max_chars)
        if end < length:
            split_at = normalized.rfind(". ", cursor, end)
            if split_at <= cursor:
                split_at = normalized.rfind(" ", cursor, end)
            if split_at > cursor:
                end = split_at + 1
        chunk = normalized[cursor:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        cursor = max(end - overlap, cursor + 1)
    return chunks


def _keyword_blob(content: str, max_terms: int = 60) -> str:
    words = re.findall(r"[a-zA-Z0-9_À-ÿ-]{3,}", (content or "").lower())
    counts: dict[str, int] = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    top_words = [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:max_terms]]
    return " ".join(top_words)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _lexical_overlap_score(query: str, content: str, keyword_blob: str = "") -> float:
    query_terms = set(re.findall(r"[a-zA-Z0-9_À-ÿ-]{3,}", (query or "").lower()))
    if not query_terms:
        return 0.0
    haystack = f"{content} {keyword_blob}".lower()
    matches = sum(1 for term in query_terms if term in haystack)
    return matches / max(len(query_terms), 1)


def _request_ollama_json(path: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:11434{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _ollama_embed_texts(texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for text in texts:
        payload = {"model": model, "input": text}
        parsed = _request_ollama_json("/api/embed", payload, timeout=45)
        vector = parsed.get("embeddings")
        if isinstance(vector, list) and vector and isinstance(vector[0], list):
            try:
                embeddings.append([float(value) for value in vector[0]])
                continue
            except (TypeError, ValueError):
                pass
        fallback = parsed.get("embedding")
        if isinstance(fallback, list):
            try:
                embeddings.append([float(value) for value in fallback])
                continue
            except (TypeError, ValueError):
                pass
        embeddings.append([])
    return embeddings


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
    ai_selected_model: str = ""
    ai_resource_type: str = "politica"
    ai_knowledge_scope: str = "tenant"
    ai_scope_mode: str = "tenant"
    ai_history: list[dict[str, str]] = []
    audit_filter_scope: str = "Todos"
    audit_filter_event: str = "Todos"
    audit_filter_tenant: str = "Todos"
    audit_filter_user: str = "Todos"
    audit_expanded_event_ids: list[str] = []

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
    new_tenant_assigned_client_ids: list[str] = []
    new_tenant_assigned_clients_open: bool = False
    editing_tenant_id: str = ""

    new_role_name: str = ""
    new_role_permissions: str = "create:clientes,edit:clientes"
    editing_role_id: str = ""

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
    new_sticky_note_text: str = ""
    workflow_logs: list[str] = []

    new_action_title: str = ""
    new_action_owner: str = ""
    new_action_due_date: str = ""
    new_action_expected_result: str = ""
    new_action_dimensions: str = ""
    new_action_area: str = ""

    perm_user_email: str = ""
    perm_selected_module: str = "Todos"
    perm_selected_role_template: str = "cliente_admin"

    new_dashboard_box_title: str = ""
    new_dashboard_box_kind: str = "kpi"
    new_dashboard_box_scope: str = "consultor"
    new_dashboard_box_source: str = "projetos"
    new_dashboard_box_description: str = ""

    testimonial_index: int = 0

    def _append_audit_entry(self, event: str, detail: str, scope: str = "info", extra: dict[str, str] | None = None):
        entry = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
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

    def prepare_ai_view(self):
        self.ai_answer = ""
        self.dragged_question_text = ""

    def _resolve_ai_document_scope(self) -> tuple[str, int | None]:
        target_tenant = self.selected_project_source_tenant if self.ai_scope_mode_effective == "projeto" else self.current_tenant
        project_id = int(self.selected_project_id) if self.ai_scope_mode_effective == "projeto" and self.selected_project_id and self.selected_project_id.isdigit() else None
        return target_tenant, project_id

    def _visible_ai_documents_query(self, session):
        target_tenant, project_id = self._resolve_ai_document_scope()
        query = session.query(AssistantDocumentModel).filter(
            or_(
                (
                    (AssistantDocumentModel.tenant_id == target_tenant)
                    & (AssistantDocumentModel.knowledge_scope == "tenant")
                ),
                (AssistantDocumentModel.knowledge_scope == "smartlab"),
            )
        )
        if project_id is not None:
            query = query.filter(
                (
                    (AssistantDocumentModel.knowledge_scope == "smartlab")
                    | (AssistantDocumentModel.project_id == project_id)
                    | (AssistantDocumentModel.project_id.is_(None))
                )
            )
        return query

    def _retrieve_ai_chunks(self, query_text: str, limit: int = 6) -> list[dict[str, str]]:
        prompt = (query_text or "").strip()
        if not prompt:
            return []
        session = SessionLocal()
        visible_docs = self._visible_ai_documents_query(session).all()
        if not visible_docs:
            session.close()
            return []
        doc_lookup = {int(doc.id): doc for doc in visible_docs}
        rows = (
            session.query(AssistantChunkModel)
            .filter(AssistantChunkModel.document_id.in_(list(doc_lookup.keys())))
            .order_by(AssistantChunkModel.document_id.asc(), AssistantChunkModel.chunk_index.asc())
            .all()
        )
        query_embedding = _ollama_embed_texts([prompt])[0]
        ranked: list[dict[str, str | float]] = []
        for row in rows:
            embedding = _loads_json(row.embedding_json, [])
            vector = [float(item) for item in embedding if isinstance(item, (int, float))]
            lexical_score = _lexical_overlap_score(prompt, row.content, row.keyword_blob or "")
            embedding_score = _cosine_similarity(query_embedding, vector) if query_embedding and vector else 0.0
            score = round((embedding_score * 0.8) + (lexical_score * 0.2), 6) if (query_embedding and vector) else round(lexical_score, 6)
            if score <= 0:
                continue
            doc = doc_lookup.get(int(row.document_id))
            if not doc:
                continue
            ranked.append(
                {
                    "document_id": str(row.document_id),
                    "file_name": doc.file_name,
                    "resource_type": doc.resource_type or "politica",
                    "project_scope": "Base SmartLab" if doc.knowledge_scope == "smartlab" else ("Projeto atual" if doc.project_id else "Tenant"),
                    "content": row.content,
                    "score": score,
                }
            )
        session.close()
        ranked.sort(key=lambda item: (-float(item["score"]), item["file_name"]))
        deduped: list[dict[str, str]] = []
        seen_hashes: set[str] = set()
        for item in ranked:
            digest = sha1(f"{item['file_name']}|{item['content'][:180]}".encode("utf-8")).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            deduped.append(
                {
                    "document_id": str(item["document_id"]),
                    "file_name": str(item["file_name"]),
                    "resource_type": str(item["resource_type"]),
                    "project_scope": str(item["project_scope"]),
                    "content": str(item["content"]),
                    "score": f"{float(item['score']):.3f}",
                }
            )
            if len(deduped) >= limit:
                break
        return deduped

    def _index_assistant_document(self, session, document_row: AssistantDocumentModel) -> tuple[int, str]:
        file_path = Path(document_row.file_path)
        raw_text = _extract_document_text(file_path)
        session.query(AssistantChunkModel).filter(AssistantChunkModel.document_id == int(document_row.id)).delete()
        if not raw_text:
            return 0, "sem_texto"
        chunks = _chunk_text(raw_text)
        if not chunks:
            return 0, "sem_chunks"
        embeddings = _ollama_embed_texts(chunks)
        for index, chunk in enumerate(chunks):
            vector = embeddings[index] if index < len(embeddings) else []
            session.add(
                AssistantChunkModel(
                    document_id=int(document_row.id),
                    tenant_id=document_row.tenant_id,
                    project_id=document_row.project_id,
                    knowledge_scope=document_row.knowledge_scope or "tenant",
                    chunk_index=index,
                    content=chunk,
                    keyword_blob=_keyword_blob(chunk),
                    embedding_json=json.dumps(vector),
                )
            )
        return len(chunks), ("vetorial" if any(embeddings) else "lexical")

    def _build_ai_factual_answer(self, prompt: str, insights: dict[str, Any]) -> str:
        prompt_lower = prompt.lower()
        asks_companies = any(term in prompt_lower for term in ["empresa", "empresas", "cliente", "clientes"])
        asks_respondents = any(term in prompt_lower for term in ["quem respondeu", "quem delas", "quem respondeu", "respondente", "respondentes", "nomes"])
        asks_count = any(term in prompt_lower for term in ["quantas", "quantos", "número", "numero", "total"])
        asks_interviews = any(term in prompt_lower for term in ["entrevista", "entrevistas"])
        asks_in_progress = any(term in prompt_lower for term in ["em andamento", "andamento", "aberta", "abertas"])
        asks_completed = any(term in prompt_lower for term in ["conclu", "finalizada", "finalizadas"])

        company_lines = [
            f"- {item['name']}: {item['responses']} respostas; responderam {item['respondents']}"
            for item in insights["company_breakdown"]
        ]
        respondent_lines = [
            f"- {item['name']}: {item['responses']} respostas"
            for item in insights["respondent_breakdown"]
        ]
        interview_company_lines = [
            f"- {item['name']}: {item['status_count']} entrevistas ({item['statuses']})"
            for item in insights["interview_company_breakdown"]
        ]
        completed_names = ", ".join(insights["completed_interviewees"]) or "nenhum"

        if asks_interviews and asks_in_progress:
            return f"Entrevistas em andamento no contexto atual: {insights['interviews_in_progress']}."
        if asks_interviews and asks_completed and asks_companies:
            return (
                f"Empresas com entrevistas concluídas: {', '.join(insights['completed_companies']) or 'nenhuma'}.\n"
                f"{chr(10).join(interview_company_lines) if interview_company_lines else 'Nenhuma entrevista concluída identificada.'}"
            )
        if asks_interviews and asks_completed:
            return (
                f"Entrevistas concluídas no contexto atual: {insights['interviews_completed']}.\n"
                f"Entrevistados concluídos: {completed_names}."
            )
        if asks_interviews and asks_companies:
            return (
                f"Empresas com entrevistas no contexto atual: {', '.join(insights['interview_company_names']) or 'nenhuma'}.\n"
                f"{chr(10).join(interview_company_lines) if interview_company_lines else 'Nenhum vínculo empresa-entrevista encontrado.'}"
            )
        if asks_interviews and asks_count:
            return (
                f"Total de entrevistas no contexto atual: {insights['total_interviews']}.\n"
                f"Concluídas: {insights['interviews_completed']} | Em andamento: {insights['interviews_in_progress']}."
            )

        if asks_companies and asks_respondents:
            return (
                f"Empresas que responderam: {', '.join(insights['company_names']) or 'nenhuma'}.\n"
                f"{chr(10).join(company_lines) if company_lines else 'Nenhum vínculo empresa-respondente encontrado.'}"
            )
        if asks_companies and asks_count:
            return (
                f"Total de empresas com respostas: {len(insights['company_names'])}.\n"
                f"Empresas: {', '.join(insights['company_names']) or 'nenhuma'}."
            )
        if asks_companies:
            return (
                f"Empresas que responderam: {', '.join(insights['company_names']) or 'nenhuma'}.\n"
                f"{chr(10).join(company_lines) if company_lines else 'Nenhuma empresa identificada.'}"
            )
        if asks_respondents and asks_count:
            return (
                f"Total de respostas: {insights['total_responses']}.\n"
                f"{chr(10).join(respondent_lines) if respondent_lines else 'Nenhum respondente identificado.'}"
            )
        if asks_respondents:
            return chr(10).join(respondent_lines) if respondent_lines else "Nenhum respondente identificado."
        if asks_count and "respost" in prompt_lower:
            return (
                f"Total de respostas no contexto atual: {insights['total_responses']}.\n"
                f"Empresas: {', '.join(insights['company_names']) or 'nenhuma'}."
            )
        return ""

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

    @rx.var
    def show_menu_audit(self) -> bool:
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
                "created_at": r.created_at.strftime("%Y-%m-%d") if r.created_at else "-",
                "document_count": str(document_counts.get(r.id, 0)),
                "project_count": str(project_counts.get(r.id, 0)),
                "form_count": str(form_counts.get(r.id, 0)),
                "client_scope_count": str(len([item for item in _loads_json(r.assigned_client_ids, []) if str(item).isdigit()])),
                "client_scope_summary": (
                    "SmartLab default: acesso total"
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
        return _parse_ollama_list(_run_ollama_command("list"))

    @rx.var
    def ai_model_options(self) -> list[str]:
        return [row["name"] for row in self.ollama_models_data]

    @rx.var
    def ai_selected_model_effective(self) -> str:
        if self.ai_selected_model and self.ai_selected_model in self.ai_model_options:
            return self.ai_selected_model
        preferred = "llama3:8b-instruct-q8_0"
        if preferred in self.ai_model_options:
            return preferred
        return self.ai_model_options[0] if self.ai_model_options else "Nenhum modelo local disponível"

    @rx.var
    def ai_runtime_status(self) -> dict[str, str]:
        version_output = _run_ollama_command("--version")
        status = "online" if self.ollama_models_data else "sem modelos"
        if not version_output:
            status = "offline"
        return {
            "engine": "Ollama local",
            "version": version_output or "indisponível",
            "status": status,
            "models": str(len(self.ollama_models_data)),
            "default_model": self.ai_selected_model_effective,
        }

    @rx.var
    def ai_resource_type_options(self) -> list[str]:
        return ["politica", "procedimento", "evidencia", "comentario", "relatorio"]

    @rx.var
    def ai_knowledge_scope_options(self) -> list[str]:
        options = ["tenant"]
        if self.user_scope == "smartlab":
            options.append("smartlab")
        return options

    @rx.var
    def ai_knowledge_scope_effective(self) -> str:
        if self.ai_knowledge_scope == "smartlab" and self.user_scope == "smartlab":
            return "smartlab"
        return "tenant"

    @rx.var
    def ai_scope_options(self) -> list[str]:
        options = ["tenant"]
        if self.selected_project_id and self.selected_project_id.isdigit():
            options.append("projeto")
        return options

    @rx.var
    def ai_scope_mode_effective(self) -> str:
        if self.ai_scope_mode == "projeto" and self.selected_project_id and self.selected_project_id.isdigit():
            return "projeto"
        return "tenant"

    @rx.var
    def ai_selected_project_label(self) -> str:
        if self.ai_scope_mode_effective != "projeto":
            return "Projeto desativado no Assistente"
        return self.selected_project_option or "Projeto não selecionado"

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

    @rx.var
    def selected_tenant_assigned_clients_summary(self) -> str:
        if self.new_tenant_slug == "default":
            return "SmartLab default: acesso total e irrestrito"
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
                .filter(
                    ProjectModel.id == int(self.new_interview_project_id),
                    ProjectModel.tenant_id == self.current_tenant,
                )
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
        if row and row[0]:
            return str(row[0]).strip()
        return "-"

    @rx.var(cache=False)
    def interview_inline_form_options(self) -> list[str]:
        target_service = ""
        if self.edit_interview_project_id.isdigit():
            session = SessionLocal()
            row = (
                session.query(ProjectModel.service_name)
                .filter(
                    ProjectModel.id == int(self.edit_interview_project_id),
                    ProjectModel.tenant_id == self.current_tenant,
                )
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
                .filter(
                    ProjectModel.id == int(self.edit_interview_project_id),
                    ProjectModel.tenant_id == self.current_tenant,
                )
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
    def active_interview_client_id(self) -> str:
        if not self.selected_interview_id.isdigit():
            return self.new_interview_client_id if self.interview_draft_active else ""
        session = SessionLocal()
        row = (
            session.query(InterviewSessionModel.client_id)
            .filter(
                InterviewSessionModel.id == int(self.selected_interview_id),
                InterviewSessionModel.tenant_id == self.current_tenant,
            )
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
            .filter(
                UserModel.account_scope == "cliente",
                UserModel.client_id == int(self.active_interview_client_id),
            )
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
                    .filter(
                        InterviewSessionModel.id == int(self.selected_interview_id),
                        InterviewSessionModel.tenant_id == self.current_tenant,
                    )
                    .first()
                )
                session.close()
                target_user_id = str(interview_row[0]) if interview_row and interview_row[0] is not None else ""
        if not target_user_id.isdigit():
            return ""
        session = SessionLocal()
        row = (
            session.query(UserModel.id, UserModel.name, UserModel.email, UserModel.profession)
            .filter(UserModel.id == int(target_user_id))
            .first()
        )
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
            .filter(
                UserModel.account_scope == "cliente",
                UserModel.client_id == int(self.new_interview_client_id),
                UserModel.department.is_not(None),
            )
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
            .filter(
                UserModel.account_scope == "cliente",
                UserModel.client_id == int(client_id),
                UserModel.department.is_not(None),
            )
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
            .filter(
                InterviewSessionModel.id == int(self.selected_interview_id),
                InterviewSessionModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        if not interview:
            session.close()
            return False
        survey = None
        if interview.survey_id is not None:
            survey = session.query(SurveyModel).filter(SurveyModel.id == int(interview.survey_id)).first()
        stage_name = survey.stage_name if survey and survey.stage_name else self.selected_interview_record["stage_name"]
        ready = True
        if stage_name == "Entrevista Individual com o Líder":
            ready = interview.interviewee_user_id is not None
        elif stage_name == "Visita Técnica - Guiada":
            ready = bool(str(interview.target_area or "").strip())
        elif stage_name in {"Rodas de Conversa", "Rodada de Conversa"}:
            ready = bool(str(interview.target_area or "").strip() and str(interview.audience_group or "").strip())
        session.close()
        return ready

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
                "interview_date": self.new_interview_date or "-",
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
                "contracted_at": r.contracted_at or "-",
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
        return self.user_scope == "smartlab" and self.current_tenant == "default"

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
                "client_name": self.client_lookup.get(str(r.client_id), "-") if r.client_id is not None else self.selected_project_record["client_name"],
                "service_name": r.service_name or self.selected_project_record["service_name"],
                "dimensions": r.dimension_names or "-",
                "target_area": r.target_area or "-",
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
    def ai_documents_data(self) -> list[dict[str, str]]:
        session = SessionLocal()
        rows = self._visible_ai_documents_query(session).order_by(AssistantDocumentModel.uploaded_at.desc(), AssistantDocumentModel.id.desc()).all()
        chunk_counts: dict[int, int] = {}
        for document_id, _ in session.query(AssistantChunkModel.document_id, AssistantChunkModel.id).all():
            chunk_counts[int(document_id)] = chunk_counts.get(int(document_id), 0) + 1
        data = [
            {
                "id": str(row.id),
                "file_name": row.file_name,
                "resource_type": row.resource_type or "politica",
                "project_scope": "Base SmartLab" if row.knowledge_scope == "smartlab" else ("Projeto atual" if row.project_id else "Tenant"),
                "knowledge_scope": row.knowledge_scope or "tenant",
                "uploaded_by": row.uploaded_by or "-",
                "uploaded_at": row.uploaded_at.strftime("%Y-%m-%d %H:%M") if row.uploaded_at else "-",
                "file_size": f"{max(int(row.file_size or 0) // 1024, 1)} KB" if int(row.file_size or 0) > 0 else "-",
                "chunk_count": str(chunk_counts.get(int(row.id), 0)),
                "can_delete": bool(row.knowledge_scope != "smartlab" or self.user_scope == "smartlab"),
            }
            for row in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def ai_context_summary(self) -> dict[str, str]:
        session = SessionLocal()
        target_tenant = self.selected_project_source_tenant if self.ai_scope_mode_effective == "projeto" else self.current_tenant
        forms_count = session.query(FormModel).filter(FormModel.tenant_id == target_tenant).count()
        tenant_documents_count = session.query(AssistantDocumentModel).filter(
            AssistantDocumentModel.tenant_id == target_tenant,
            AssistantDocumentModel.knowledge_scope == "tenant",
        ).count()
        smartlab_documents_count = session.query(AssistantDocumentModel).filter(
            AssistantDocumentModel.knowledge_scope == "smartlab"
        ).count()
        tenant_chunk_document_ids = [
            int(row[0])
            for row in session.query(AssistantDocumentModel.id).filter(
                AssistantDocumentModel.tenant_id == target_tenant,
                AssistantDocumentModel.knowledge_scope == "tenant",
            ).all()
        ]
        smartlab_chunk_document_ids = [
            int(row[0])
            for row in session.query(AssistantDocumentModel.id).filter(
                AssistantDocumentModel.knowledge_scope == "smartlab"
            ).all()
        ]
        chunk_document_ids = list({*tenant_chunk_document_ids, *smartlab_chunk_document_ids})
        chunk_count = 0
        if chunk_document_ids:
            chunk_count = session.query(AssistantChunkModel).filter(AssistantChunkModel.document_id.in_(chunk_document_ids)).count()
        query_interviews = session.query(InterviewSessionModel).filter(InterviewSessionModel.tenant_id == target_tenant)
        query_actions = session.query(ActionPlanModel).filter(ActionPlanModel.tenant_id == target_tenant)
        if self.ai_scope_mode_effective == "projeto" and self.selected_project_id and self.selected_project_id.isdigit():
            project_id = int(self.selected_project_id)
            query_interviews = query_interviews.filter(InterviewSessionModel.project_id == project_id)
            query_actions = query_actions.filter(ActionPlanModel.project_id == project_id)
        interviews = query_interviews.all()
        interview_ids = [row.id for row in interviews]
        responses_count = 0
        if interview_ids:
            responses_count = session.query(ResponseModel).filter(
                ResponseModel.tenant_id == target_tenant,
                ResponseModel.interview_id.in_(interview_ids),
            ).count()
        actions_total = query_actions.count()
        actions_open = query_actions.filter(ActionPlanModel.status != "concluido").count()
        session.close()
        return {
            "tenant": target_tenant,
            "scope": self.ai_scope_mode_effective,
            "documents": str(tenant_documents_count + smartlab_documents_count),
            "tenant_documents": str(tenant_documents_count),
            "smartlab_documents": str(smartlab_documents_count),
            "chunks": str(chunk_count),
            "forms": str(forms_count),
            "interviews": str(len(interviews)),
            "responses": str(responses_count),
            "actions_total": str(actions_total),
            "actions_open": str(actions_open),
        }

    @rx.var(cache=False)
    def ai_response_insights(self) -> dict[str, Any]:
        session = SessionLocal()
        target_tenant = self.selected_project_source_tenant if self.ai_scope_mode_effective == "projeto" else self.current_tenant
        query_interviews = session.query(InterviewSessionModel).filter(InterviewSessionModel.tenant_id == target_tenant)
        query_responses = session.query(ResponseModel).filter(ResponseModel.tenant_id == target_tenant)
        if self.ai_scope_mode_effective == "projeto" and self.selected_project_id and self.selected_project_id.isdigit():
            project_id = int(self.selected_project_id)
            query_interviews = query_interviews.filter(InterviewSessionModel.project_id == project_id)
            interview_ids = [row.id for row in query_interviews.all()]
            if interview_ids:
                query_responses = query_responses.filter(ResponseModel.interview_id.in_(interview_ids))
            else:
                query_responses = query_responses.filter(ResponseModel.id == -1)
        interviews = query_interviews.all()
        responses = query_responses.all()
        user_rows = session.query(UserModel).all()
        client_rows = session.query(ClientModel).all()
        user_lookup = {int(row.id): row.name for row in user_rows}
        user_client_lookup = {int(row.id): str(row.client_id) if row.client_id is not None else "" for row in user_rows}
        client_lookup = {str(row.id): row.trade_name or row.name for row in client_rows}
        respondent_counts: dict[str, int] = {}
        company_counts: dict[str, int] = {}
        company_respondent_map: dict[str, set[str]] = {}
        interview_status_counts: dict[str, int] = {}
        interview_company_counts: dict[str, int] = {}
        interview_company_status_map: dict[str, set[str]] = {}
        completed_interviewees: list[str] = []
        completed_companies: set[str] = set()
        for interview in interviews:
            status = (interview.status or "sem_status").strip().lower()
            interview_status_counts[status] = interview_status_counts.get(status, 0) + 1
            company_name = client_lookup.get(str(interview.client_id), "Empresa não identificada") if interview.client_id is not None else "Empresa não identificada"
            interview_company_counts[company_name] = interview_company_counts.get(company_name, 0) + 1
            interview_company_status_map.setdefault(company_name, set()).add(status)
            if status == "concluida":
                completed_interviewees.append(interview.interviewee_name or "Entrevistado não identificado")
                completed_companies.add(company_name)
        for row in responses:
            client_name = "Empresa não identificada"
            client_id = str(row.client_id) if row.client_id is not None else ""
            if not client_id and row.respondent_id and int(row.respondent_id) in user_client_lookup:
                client_id = user_client_lookup[int(row.respondent_id)]
            if not client_id and row.interview_id:
                interview = next((item for item in interviews if item.id == row.interview_id), None)
                if interview and interview.client_id is not None:
                    client_id = str(interview.client_id)
            if client_id and client_id in client_lookup:
                client_name = client_lookup[client_id]
            if row.respondent_id and int(row.respondent_id) in user_lookup:
                name = user_lookup[int(row.respondent_id)]
            elif row.interview_id:
                interview = next((item for item in interviews if item.id == row.interview_id), None)
                name = interview.interviewee_name if interview and interview.interviewee_name else f"Entrevista {row.interview_id}"
            else:
                name = "Respondente não identificado"
            respondent_counts[name] = respondent_counts.get(name, 0) + 1
            company_counts[client_name] = company_counts.get(client_name, 0) + 1
            company_respondent_map.setdefault(client_name, set()).add(name)
        interview_names = [row.interviewee_name for row in interviews if row.interviewee_name]
        session.close()
        top_respondents = [
            {"name": name, "responses": count}
            for name, count in sorted(respondent_counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        top_companies = [
            {
                "name": name,
                "responses": count,
                "respondents": ", ".join(sorted(company_respondent_map.get(name, set()))),
            }
            for name, count in sorted(company_counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        interview_companies = [
            {
                "name": name,
                "status_count": count,
                "statuses": ", ".join(sorted(interview_company_status_map.get(name, set()))),
            }
            for name, count in sorted(interview_company_counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        return {
            "total_responses": len(responses),
            "total_interviews": len(interviews),
            "interviews_completed": interview_status_counts.get("concluida", 0),
            "interviews_in_progress": interview_status_counts.get("em_andamento", 0),
            "respondent_names": [item["name"] for item in top_respondents],
            "respondent_breakdown": top_respondents,
            "company_names": [item["name"] for item in top_companies],
            "company_breakdown": top_companies,
            "interview_company_names": [item["name"] for item in interview_companies],
            "interview_company_breakdown": interview_companies,
            "completed_interviewees": sorted(completed_interviewees),
            "completed_companies": sorted(completed_companies),
            "interviewee_names": interview_names,
        }

    @rx.var
    def ai_source_snapshot(self) -> list[dict[str, str]]:
        return [
            {"label": "Documentos IA", "value": self.ai_context_summary["documents"], "detail": "PDF, Word, Excel e outros artefatos indexados"},
            {"label": "Base SmartLab", "value": self.ai_context_summary["smartlab_documents"], "detail": "materiais-mestre compartilhados pela SmartLab"},
            {"label": "Chunks RAG", "value": self.ai_context_summary["chunks"], "detail": "trechos prontos para recuperação contextual"},
            {"label": "Formulários", "value": self.ai_context_summary["forms"], "detail": "instrumentos ativos no tenant"},
            {"label": "Entrevistas", "value": self.ai_context_summary["interviews"], "detail": "sessões vinculadas ao contexto"},
            {"label": "Respostas", "value": self.ai_context_summary["responses"], "detail": "evidências textuais e scores"},
            {"label": "Planos em aberto", "value": self.ai_context_summary["actions_open"], "detail": "ações ainda não concluídas"},
        ]

    @rx.var
    def ai_recommended_actions(self) -> list[dict[str, str]]:
        recommendations: list[dict[str, str]] = []
        critical_rows = [row for row in self.dashboard_table if row["status"] in {"Crítico", "Moderado"}]
        for row in critical_rows[:3]:
            recommendations.append(
                {
                    "title": f"Plano 30-60-90 para {row['form']}",
                    "owner": "Liderança do processo",
                    "due_date": "30 dias",
                    "expected_result": (
                        f"Elevar a categoria {row['categoria']} acima de {row['media']} com base em políticas, entrevistas e evidências do tenant."
                    ),
                }
            )
        if not recommendations:
            recommendations.append(
                {
                    "title": "Revisar aderência entre políticas e respostas",
                    "owner": "Consultoria SmartLab",
                    "due_date": "15 dias",
                    "expected_result": "Consolidar lacunas, conflitos e ausências documentais antes da próxima rodada de entrevistas.",
                }
            )
        return recommendations

    @rx.var
    def ai_history_data(self) -> list[dict[str, str]]:
        return list(reversed(self.ai_history))

    @rx.var(cache=False)
    def audit_events_data(self) -> list[dict[str, str]]:
        if not AUDIT_LOG_PATH.exists():
            return []
        entries: list[dict[str, str]] = []
        for idx, line in enumerate(AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(parsed, dict):
                continue
            entry = {str(key): str(value) for key, value in parsed.items()}
            entry.setdefault("question", "")
            entry.setdefault("answer", "")
            entry.setdefault("model", "")
            entry.setdefault("assistant_scope", "")
            entry.setdefault("answer_mode", "")
            entry.setdefault("sources", "")
            entry.setdefault("audit_id", str(idx))
            if entry.get("event", "").startswith("assistant.ask"):
                raw_event = entry.get("event", "")
                if not entry["answer_mode"]:
                    if raw_event == "assistant.ask.factual":
                        entry["answer_mode"] = "factual"
                    elif raw_event == "assistant.ask.fallback":
                        entry["answer_mode"] = "fallback"
                    else:
                        entry["answer_mode"] = "llm"
                entry["event"] = "assistant.ask"
                entry["event_label"] = "Especialista IA"
                entry["answer_mode_label"] = {
                    "factual": "Banco local",
                    "llm": "LLM local",
                    "fallback": "Fallback",
                }.get(entry["answer_mode"], entry["answer_mode"] or "-")
            else:
                entry.setdefault("event_label", entry.get("event", ""))
                entry.setdefault("answer_mode_label", "")
            if self.user_scope != "smartlab" and entry.get("tenant") != self.current_tenant:
                continue
            entries.append(entry)
        return list(reversed(entries[-200:]))

    @rx.var
    def audit_scope_options(self) -> list[str]:
        values = sorted({item["scope"] for item in self.audit_events_data if item.get("scope")})
        return ["Todos", *values]

    @rx.var
    def audit_event_options(self) -> list[str]:
        values = sorted({item["event"] for item in self.audit_events_data if item.get("event")})
        return ["Todos", *values]

    @rx.var
    def audit_tenant_options(self) -> list[str]:
        values = sorted({item["tenant"] for item in self.audit_events_data if item.get("tenant")})
        return ["Todos", *values]

    @rx.var
    def audit_user_options(self) -> list[str]:
        values = sorted({item["user"] for item in self.audit_events_data if item.get("user")})
        return ["Todos", *values]

    @rx.var
    def audit_filtered_events_data(self) -> list[dict[str, str]]:
        data = list(self.audit_events_data)
        if self.audit_filter_scope != "Todos":
            data = [item for item in data if item["scope"] == self.audit_filter_scope]
        if self.audit_filter_event != "Todos":
            data = [item for item in data if item["event"] == self.audit_filter_event]
        if self.audit_filter_tenant != "Todos":
            data = [item for item in data if item["tenant"] == self.audit_filter_tenant]
        if self.audit_filter_user != "Todos":
            data = [item for item in data if item["user"] == self.audit_filter_user]
        return data

    @rx.var
    def audit_theme_summary(self) -> list[dict[str, str]]:
        counts: dict[str, int] = {}
        for item in self.audit_filtered_events_data:
            scope = item.get("scope", "info") or "info"
            counts[scope] = counts.get(scope, 0) + 1
        return [
            {
                "scope": scope,
                "count": str(count),
                "label": scope.replace("_", " ").title(),
            }
            for scope, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
        ]

    @rx.var
    def audit_grouped_sections(self) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, str]]] = {}
        for item in self.audit_filtered_events_data:
            scope = item.get("scope", "info") or "info"
            grouped.setdefault(scope, []).append(item)
        return [
            {
                "scope": scope,
                "title": scope.replace("_", " ").title(),
                "count": str(len(items)),
                "items": items,
            }
            for scope, items in sorted(grouped.items(), key=lambda pair: pair[0])
        ]

    @rx.var
    def audit_log_path_display(self) -> str:
        return str(AUDIT_LOG_PATH)

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
        self._append_audit_entry("tenant.switch", f"Contexto alterado para tenant {value}", "security")

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

    def confirm_new_client_business_sector(self):
        value = self._register_catalog_option("business_sector", self.new_client_custom_business_sector)
        if not value:
            self.toast_message = "Informe o ramo de atividade antes de confirmar"
            self.toast_type = "error"
            return
        self.new_client_business_sector = value
        self.new_client_custom_business_sector = ""
        if self.editing_client_id.isdigit():
            session = SessionLocal()
            client = (
                session.query(ClientModel)
                .filter(ClientModel.id == int(self.editing_client_id), ClientModel.tenant_id == self.current_tenant)
                .first()
            )
            if client:
                client.business_sector = value
                session.commit()
            session.close()
        self.toast_message = "Ramo registrado e disponível na lista"
        self.toast_type = "success"

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

    def confirm_new_user_profession(self):
        value = self._register_catalog_option("user_profession", self.new_user_custom_profession)
        if not value:
            self.toast_message = "Informe a profissao antes de confirmar"
            self.toast_type = "error"
            return
        self.new_user_profession = value
        self.new_user_custom_profession = ""
        if self.editing_user_id.isdigit():
            session = SessionLocal()
            user = session.query(UserModel).filter(UserModel.id == int(self.editing_user_id)).first()
            if user:
                user.profession = value
                session.commit()
            session.close()
        self.toast_message = "Profissao registrada e disponível na lista"
        self.toast_type = "success"

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

    def confirm_new_user_department(self):
        value = self._register_catalog_option("user_department", self.new_user_custom_department)
        if not value:
            self.toast_message = "Informe o departamento antes de confirmar"
            self.toast_type = "error"
            return
        self.new_user_department = value
        self.new_user_custom_department = ""
        if self.editing_user_id.isdigit():
            session = SessionLocal()
            user = session.query(UserModel).filter(UserModel.id == int(self.editing_user_id)).first()
            if user:
                user.department = value
                session.commit()
            session.close()
        self.toast_message = "Departamento registrado e disponível na lista"
        self.toast_type = "success"

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
        self.new_tenant_assigned_client_ids = []
        self.new_tenant_assigned_clients_open = False

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
        assigned_client_ids = [str(item) for item in _loads_json(row.assigned_client_ids, []) if str(item).isdigit()]
        if not assigned_client_ids and row.owner_client_id is not None:
            assigned_client_ids = self._expand_client_scope([str(row.owner_client_id)])
        self.new_tenant_assigned_client_ids = assigned_client_ids
        self.new_tenant_assigned_clients_open = False

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

    def set_new_form_stage(self, value: str):
        self.new_form_stage = value
        if value != "Outra":
            self.new_form_custom_stage = ""
        if not self.selected_form_id.isdigit():
            return
        if value == "Outra":
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
            .filter(
                ProjectModel.id == int(self.new_interview_project_id),
                ProjectModel.tenant_id == self.current_tenant,
            )
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
            .filter(
                ProjectModel.id == int(self.edit_interview_project_id),
                ProjectModel.tenant_id == self.current_tenant,
            )
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
                .filter(
                    QuestionModel.id == int(self.editing_question_id),
                    QuestionModel.tenant_id == self.current_tenant,
                )
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

    def set_ai_prompt(self, value: str):
        self.ai_prompt = value

    def set_ai_selected_model(self, value: str):
        self.ai_selected_model = value

    def set_ai_resource_type(self, value: str):
        self.ai_resource_type = value

    def set_ai_knowledge_scope(self, value: str):
        self.ai_knowledge_scope = value

    def set_ai_scope_mode(self, value: str):
        self.ai_scope_mode = value

    def set_audit_filter_scope(self, value: str):
        self.audit_filter_scope = value

    def set_audit_filter_event(self, value: str):
        self.audit_filter_event = value

    def set_audit_filter_tenant(self, value: str):
        self.audit_filter_tenant = value

    def set_audit_filter_user(self, value: str):
        self.audit_filter_user = value

    def toggle_audit_event_expanded(self, audit_id: str):
        current = list(self.audit_expanded_event_ids)
        if audit_id in current:
            current = [item for item in current if item != audit_id]
        else:
            current.append(audit_id)
        self.audit_expanded_event_ids = current

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
            .filter(
                ProjectModel.id == int(project_id),
                ProjectModel.tenant_id == self.current_tenant,
            )
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
            .filter(
                ProjectModel.id == int(self.editing_project_id),
                ProjectModel.tenant_id == self.current_tenant,
            )
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
        project.contracted_at = self.new_project_contracted_at.strip() or datetime.utcnow().strftime("%Y-%m-%d")
        assignment = (
            session.query(ProjectAssignmentModel)
            .filter(ProjectAssignmentModel.project_id == int(project.id))
            .first()
        )
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
            self.toast_message = "Projetos so podem ser geridos no SmartLab - interno"
            self.toast_type = "error"
            return
        session = SessionLocal()
        project = (
            session.query(ProjectModel)
            .filter(
                ProjectModel.id == int(project_id),
                ProjectModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        if not project:
            session.close()
            self.toast_message = "Projeto não encontrado"
            self.toast_type = "error"
            return
        interview_ids = [
            int(row[0])
            for row in session.query(InterviewSessionModel.id)
            .filter(InterviewSessionModel.project_id == int(project_id))
            .all()
            if row[0] is not None
        ]
        action_count = session.query(ActionPlanModel.id).filter(ActionPlanModel.project_id == int(project_id)).count()
        workflow_count = session.query(WorkflowBoxModel.id).filter(WorkflowBoxModel.project_id == int(project_id)).count()
        document_ids = [
            int(row[0])
            for row in session.query(AssistantDocumentModel.id)
            .filter(AssistantDocumentModel.project_id == int(project_id))
            .all()
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

    def set_new_action_dimensions(self, value: str):
        self.new_action_dimensions = value

    def set_new_action_area(self, value: str):
        self.new_action_area = value

    def set_new_user_client_id(self, value: str):
        self.new_user_client_id = value

    def set_new_user_tenant_id(self, value: str):
        self.new_user_tenant_id = value

    def _expand_client_scope(self, client_ids: list[str]) -> list[str]:
        normalized_ids = [int(client_id) for client_id in client_ids if client_id.isdigit()]
        if not normalized_ids:
            return []
        session = SessionLocal()
        rows = session.query(ClientModel.id, ClientModel.parent_client_id).all()
        session.close()
        children_map = _build_client_children_map(
            [ClientModel(id=row[0], parent_client_id=row[1]) for row in rows]  # type: ignore[call-arg]
        )
        expanded: set[str] = set()
        for client_id in normalized_ids:
            expanded.add(str(client_id))
            expanded.update(str(item) for item in _collect_descendant_client_ids(children_map, client_id))
        return sorted(expanded, key=lambda item: int(item))

    def set_new_tenant_client_id(self, value: str):
        self.new_tenant_client_id = value

    def set_new_tenant_client_option(self, value: str):
        client_id = value.split(" - ", 1)[0].strip()
        self.new_tenant_client_id = client_id
        self.new_tenant_assigned_client_ids = [client_id] if client_id else []

    def toggle_new_tenant_assigned_client(self, client_id: str):
        current = list(self.new_tenant_assigned_client_ids)
        if client_id in current:
            current = [item for item in current if item != client_id]
        else:
            current.append(client_id)
        current = sorted({item for item in current if item.isdigit()}, key=lambda item: int(item))
        self.new_tenant_assigned_client_ids = current
        self.new_tenant_client_id = current[0] if current else ""

    def toggle_new_tenant_assigned_clients_open(self):
        self.new_tenant_assigned_clients_open = not self.new_tenant_assigned_clients_open

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
        tenant_slug = self.new_tenant_slug.strip().lower().replace(" ", "-")
        is_default_workspace = tenant_slug == "default"
        assigned_client_ids = self._expand_client_scope(self.new_tenant_assigned_client_ids)
        owner_client_id = int(assigned_client_ids[0]) if assigned_client_ids else None
        if not is_default_workspace and owner_client_id is None:
            self.toast_message = "Tenant de operacao deve ser vinculado a um cliente"
            self.toast_type = "error"
            session.close()
            return
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
            row.assigned_client_ids = json.dumps([] if is_default_workspace else assigned_client_ids)
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
                    assigned_client_ids=json.dumps([] if is_default_workspace else assigned_client_ids),
                    limit_users=int(self.new_tenant_limit or "50"),
                )
            )
        session.commit()
        session.close()
        self.reset_tenant_form()
        self._append_audit_entry(
            "tenant.save",
            f"Tenant {'atualizado' if editing_id else 'criado'}: {tenant_slug} com {len(assigned_client_ids) if not is_default_workspace else 'acesso total'} no escopo",
            "security",
        )
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
            .filter(
                SurveyModel.id == int(self.new_interview_form_id),
                SurveyModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        project = (
            session.query(ProjectModel)
            .filter(
                ProjectModel.id == int(self.new_interview_project_id),
                ProjectModel.tenant_id == self.current_tenant,
            )
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
                .filter(
                    UserModel.id == int(self.new_interview_user_id),
                    UserModel.account_scope == "cliente",
                )
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
            .filter(
                SurveyModel.id == int(self.new_interview_form_id),
                SurveyModel.tenant_id == self.current_tenant,
            )
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
                .filter(
                    UserModel.id == int(self.new_interview_user_id),
                    UserModel.account_scope == "cliente",
                )
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
            interview_date=self.new_interview_date.strip() or datetime.utcnow().strftime("%Y-%m-%d"),
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
            .filter(
                InterviewSessionModel.id == int(self.editing_interview_table_id),
                InterviewSessionModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        project = (
            session.query(ProjectModel)
            .filter(
                ProjectModel.id == int(self.edit_interview_project_id),
                ProjectModel.tenant_id == self.current_tenant,
            )
            .first()
        )
        survey = (
            session.query(SurveyModel)
            .filter(
                SurveyModel.id == int(self.edit_interview_form_id),
                SurveyModel.tenant_id == self.current_tenant,
            )
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
        interview.interview_date = self.edit_interview_date.strip() or interview.interview_date or datetime.utcnow().strftime("%Y-%m-%d")
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
        self.new_interview_project_id = str(interview.project_id or "")
        response_rows = (
            session.query(ResponseModel)
            .filter(
                ResponseModel.tenant_id == self.current_tenant,
                ResponseModel.interview_id == int(interview_id),
            )
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
            .filter(
                InterviewSessionModel.id == int(interview_id),
                InterviewSessionModel.tenant_id == self.current_tenant,
            )
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
        interview = None
        if self.selected_interview_id.isdigit():
            interview = (
                session.query(InterviewSessionModel)
                .filter(
                    InterviewSessionModel.id == int(self.selected_interview_id),
                    InterviewSessionModel.tenant_id == self.current_tenant,
                )
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
        contracted_at = self.new_project_contracted_at.strip() or datetime.utcnow().strftime("%Y-%m-%d")
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
        action_title = self.new_action_title
        project_row = (
            session.query(ProjectModel)
            .filter(ProjectModel.id == int(self.selected_project_id), ProjectModel.tenant_id == self.selected_project_source_tenant)
            .first()
        )
        session.add(
            ActionPlanModel(
                tenant_id=self.selected_project_source_tenant,
                project_id=int(self.selected_project_id),
                client_id=int(project_row.client_id) if project_row and project_row.client_id is not None else None,
                service_name=(project_row.service_name if project_row else self.selected_project_record["service_name"]),
                dimension_names=self.new_action_dimensions.strip(),
                target_area=self.new_action_area.strip(),
                title=action_title,
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
        self.new_action_dimensions = ""
        self.new_action_area = ""
        self._append_audit_entry("action.create", f"Ação criada: {action_title}", "operations")
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
        action_title = row.title
        session.commit()
        session.close()
        self._append_audit_entry("action.status", f"Ação '{action_title}' movida para {status}", "operations")
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

        knowledge_scope = self.ai_knowledge_scope_effective
        target_tenant = "default" if knowledge_scope == "smartlab" else (self.selected_project_source_tenant if self.ai_scope_mode_effective == "projeto" else self.current_tenant)
        project_scope = (
            "smartlab"
            if knowledge_scope == "smartlab"
            else (self.selected_project_id if self.ai_scope_mode_effective == "projeto" and self.selected_project_id and self.selected_project_id.isdigit() else "tenant")
        )
        upload_dir = Path(str(rx.get_upload_dir())) / "assistant_resources" / target_tenant / str(project_scope)
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_files: list[str] = []
        indexing_notes: list[str] = []
        unsupported_files: list[str] = []
        session = SessionLocal()
        allowed_suffixes = {".pdf", ".docx", ".xlsx", ".txt", ".md", ".csv", ".json"}

        for file in files:
            file_name = file.filename or "arquivo.bin"
            safe_name = file_name.replace("..", "").replace("/", "_").replace("\\", "_")
            suffix = Path(safe_name).suffix.lower()
            if suffix not in allowed_suffixes:
                unsupported_files.append(safe_name)
                continue
            stored_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}_{safe_name}"
            file_bytes = await file.read()
            stored_path = upload_dir / stored_name
            stored_path.write_bytes(file_bytes)
            saved_files.append(safe_name)
            document = AssistantDocumentModel(
                tenant_id=target_tenant,
                project_id=(
                    int(self.selected_project_id)
                    if knowledge_scope != "smartlab" and self.ai_scope_mode_effective == "projeto" and self.selected_project_id and self.selected_project_id.isdigit()
                    else None
                ),
                knowledge_scope=knowledge_scope,
                file_name=safe_name,
                file_path=str(stored_path),
                resource_type=self.ai_resource_type,
                file_size=len(file_bytes),
                uploaded_by=self.login_email.strip().lower() or "sistema",
            )
            session.add(document)
            session.flush()
            chunk_count, retrieval_mode = self._index_assistant_document(session, document)
            indexing_notes.append(f"{safe_name}: {chunk_count} chunk(s), modo {retrieval_mode}")

        session.commit()
        session.close()
        self.uploaded_resources = saved_files + self.uploaded_resources
        self._append_audit_entry(
            "assistant.upload",
            f"{len(saved_files)} arquivo(s) enviados para {target_tenant}/{project_scope}: {', '.join(saved_files)}",
            "assistant",
            {
                "knowledge_scope": knowledge_scope,
                "sources": " | ".join(indexing_notes),
            },
        )
        if not saved_files and unsupported_files:
            self.toast_message = "Formatos suportados: PDF, Word (.docx), Excel (.xlsx), TXT, CSV e JSON"
            self.toast_type = "error"
            return
        detail = f"{len(saved_files)} arquivo(s) enviado(s) com sucesso"
        if unsupported_files:
            detail += f" | Ignorados: {', '.join(unsupported_files)}"
        self.toast_message = detail
        self.toast_type = "success" if saved_files else "error"

    def delete_ai_document(self, document_id: str):
        if not document_id.isdigit():
            return
        session = SessionLocal()
        row = session.query(AssistantDocumentModel).filter(AssistantDocumentModel.id == int(document_id)).first()
        if not row:
            session.close()
            return
        if row.knowledge_scope == "smartlab" and self.user_scope != "smartlab":
            session.close()
            self.toast_message = "Somente a SmartLab pode remover documentos da base mestre"
            self.toast_type = "error"
            return
        target_tenant = self.selected_project_source_tenant if self.selected_project_id else self.current_tenant
        if row.knowledge_scope != "smartlab" and row.tenant_id != target_tenant:
            session.close()
            return
        file_path = Path(row.file_path)
        if file_path.exists():
            file_path.unlink()
        removed_name = row.file_name
        session.query(AssistantChunkModel).filter(AssistantChunkModel.document_id == int(row.id)).delete()
        session.delete(row)
        session.commit()
        session.close()
        self._append_audit_entry("assistant.document.delete", f"Documento removido: {removed_name}", "assistant")
        self.toast_message = "Documento removido do contexto da IA"
        self.toast_type = "success"

    def promote_ai_action(self, title: str, owner: str, due_date: str, expected_result: str):
        if not self.selected_project_id or not self.selected_project_id.isdigit():
            self.toast_message = "Selecione um projeto antes de enviar a recomendação para o Plano de Ação"
            self.toast_type = "error"
            return
        session = SessionLocal()
        project_row = (
            session.query(ProjectModel)
            .filter(ProjectModel.id == int(self.selected_project_id), ProjectModel.tenant_id == self.selected_project_source_tenant)
            .first()
        )
        session.add(
            ActionPlanModel(
                tenant_id=self.selected_project_source_tenant,
                project_id=int(self.selected_project_id),
                client_id=int(project_row.client_id) if project_row and project_row.client_id is not None else None,
                service_name=(project_row.service_name if project_row else self.selected_project_record["service_name"]),
                dimension_names="",
                target_area="",
                title=title,
                owner=owner or "Consultoria SmartLab",
                due_date=due_date,
                status="a_fazer",
                expected_result=expected_result,
                attainment=0,
            )
        )
        session.commit()
        session.close()
        self._append_audit_entry("assistant.action.promote", f"Recomendação enviada ao plano: {title}", "assistant")
        self.toast_message = "Recomendação enviada ao Plano de Ação"
        self.toast_type = "success"

    def ask_ai(self):
        prompt = (self.ai_prompt or "").strip()
        if not prompt:
            self.toast_message = "Escreva uma pergunta ou objetivo para o Especialista IA"
            self.toast_type = "error"
            return

        rows = self.dashboard_table
        avg = round(sum(float(r["media"]) for r in rows) / len(rows), 2) if rows else 0.0
        low_rows = [r for r in rows if r["status"] in {"Crítico", "Moderado"}]
        docs = self.ai_documents_data[:6]
        doc_summary = ", ".join(f'{item["file_name"]} ({item["resource_type"]})' for item in docs) or "Sem documentos anexados"
        risk_summary = ", ".join(f'{item["form"]}: {item["status"]} ({item["media"]})' for item in low_rows[:4]) or "Sem criticidades explícitas no dashboard"
        context = self.ai_context_summary
        insights = self.ai_response_insights
        retrieved_chunks = self._retrieve_ai_chunks(prompt, limit=6)
        rag_sources = ", ".join(
            f'{item["file_name"]} [{item["project_scope"]}]'
            for item in retrieved_chunks
        ) or "Sem fontes recuperadas"
        rag_context = "\n\n".join(
            f"Fonte {index + 1}: {item['file_name']} | {item['resource_type']} | {item['project_scope']} | score {item['score']}\nTrecho: {item['content']}"
            for index, item in enumerate(retrieved_chunks)
        ) or "Nenhum trecho documental foi recuperado para esta pergunta."
        respondent_summary = ", ".join(
            f"{item['name']} ({item['responses']} respostas)"
            for item in insights["respondent_breakdown"][:6]
        ) or "Nenhum respondente identificado"
        company_summary = ", ".join(
            f"{item['name']} ({item['responses']} respostas)"
            for item in insights["company_breakdown"][:6]
        ) or "Nenhuma empresa identificada"
        factual_answer = self._build_ai_factual_answer(prompt, insights)
        if factual_answer:
            self.ai_answer = factual_answer
            self.ai_history = self.ai_history + [
                {
                    "asked_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "question": prompt,
                    "answer": factual_answer,
                    "model": "banco_local",
                    "scope": self.ai_scope_mode_effective,
                }
            ]
            self.ai_prompt = ""
            self._append_audit_entry(
                "assistant.ask.factual",
                "Pergunta respondida diretamente pelo banco local",
                "assistant",
                {
                    "question": prompt,
                    "answer": factual_answer,
                    "model": "banco_local",
                    "assistant_scope": self.ai_scope_mode_effective,
                    "answer_mode": "factual",
                    "sources": rag_sources,
                },
            )
            self.toast_message = "Resposta factual gerada diretamente do banco"
            self.toast_type = "success"
            return
        compiled_prompt = (
            "Você é o Especialista IA interno da SmartLab, rodando localmente e sem usar dados fora da plataforma.\n"
            "Nunca misture tenants. Responda apenas com base no contexto abaixo.\n\n"
            f"Tenant ativo: {context['tenant']}\n"
            f"Projeto selecionado: {self.selected_project_option or 'não selecionado'}\n"
            f"Documentos disponíveis: {context['documents']}\n"
            f"Base SmartLab disponível: {context['smartlab_documents']}\n"
            f"Chunks RAG disponíveis: {context['chunks']}\n"
            f"Documentos do tenant/projeto: {context['tenant_documents']}\n"
            f"Formulários ativos: {context['forms']}\n"
            f"Entrevistas: {context['interviews']}\n"
            f"Respostas vinculadas: {context['responses']}\n"
            f"Respondentes identificados: {respondent_summary}\n"
            f"Empresas identificadas: {company_summary}\n"
            f"Ações em aberto: {context['actions_open']}\n"
            f"Média geral do dashboard: {avg}\n"
            f"Principais alertas: {risk_summary}\n"
            f"Fontes documentais: {doc_summary}\n\n"
            "Trechos recuperados por RAG:\n"
            f"{rag_context}\n\n"
            "Objetivo do usuário:\n"
            f"{prompt}\n\n"
            "Entregue uma resposta objetiva com:\n"
            "1. leitura executiva;\n"
            "2. lacunas prováveis entre respostas e políticas;\n"
            "3. ações priorizadas;\n"
            "4. riscos de governança se faltar evidência documental.\n"
            "5. cite as fontes usadas pelo nome do arquivo.\n"
        )

        model_name = self.ai_selected_model_effective
        answer = ""
        if model_name != "Nenhum modelo local disponível":
            answer = _run_ollama_command("run", model_name, input_text=compiled_prompt, timeout=120)

        if answer:
            self.ai_history = self.ai_history + [
                {
                    "asked_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "question": prompt,
                    "answer": answer,
                    "model": model_name,
                    "scope": self.ai_scope_mode_effective,
                }
            ]
            self.ai_answer = answer
            self.ai_prompt = ""
            self._append_audit_entry(
                "assistant.ask",
                f"Pergunta respondida com {model_name}",
                "assistant",
                {
                    "question": prompt,
                    "answer": answer,
                    "model": model_name,
                    "assistant_scope": self.ai_scope_mode_effective,
                    "answer_mode": "llm",
                    "sources": rag_sources,
                },
            )
            self.toast_message = f"Resposta gerada com {model_name}"
            self.toast_type = "success"
            return

        prompt_lower = prompt.lower()
        if any(term in prompt_lower for term in ["quantas respostas", "qtd respostas", "numero de respostas", "número de respostas"]):
            names = ", ".join(insights["respondent_names"]) or "nenhum nome identificado"
            self.ai_answer = (
                "Especialista IA SSecur1\n"
                f"No contexto atual tivemos {insights['total_responses']} respostas registradas.\n"
                f"Respondentes identificados: {names}.\n"
                f"Entrevistas relacionadas: {insights['total_interviews']}."
            )
        elif any(term in prompt_lower for term in ["quem respondeu", "nomes", "quem foram", "quais pessoas"]):
            breakdown = "\n".join(
                f"- {item['name']}: {item['responses']} respostas"
                for item in insights["respondent_breakdown"]
            ) or "- Nenhum respondente identificado"
            self.ai_answer = (
                "Especialista IA SSecur1\n"
                "Respondentes identificados no contexto atual:\n"
                f"{breakdown}"
            )
        else:
            recommendation = [
            "Leitura executiva: concentre a análise nas dimensões com maior fricção entre segurança e produtividade.",
            "Lacunas prováveis: valide se as respostas críticas possuem política, procedimento e evidência anexada no mesmo tenant.",
            "Ações priorizadas: converta cada achado crítico em ação 30-60-90 com responsável, prazo e evidência esperada.",
            "Governança: não promova conclusão sem documento de suporte e mantenha o contexto isolado por tenant/projeto.",
            ]
            self.ai_answer = (
                "Especialista IA SSecur1\n"
                f"Modo local preparado, mas sem resposta do runtime {model_name}.\n"
                f"Tenant: {context['tenant']} | Projeto: {self.selected_project_option or '-'}\n"
                f"Média geral atual: {avg}\n"
                f"Fontes: {context['documents']} documentos, {context['chunks']} chunks RAG, {insights['total_responses']} respostas, {context['actions_open']} ações abertas.\n"
                f"RAG: {rag_sources}.\n"
                f"Respondentes: {respondent_summary}.\n"
                f"Resumo: {' '.join(recommendation)}"
            )
        self.ai_history = self.ai_history + [
            {
                "asked_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "question": prompt,
                "answer": self.ai_answer,
                "model": model_name,
                "scope": self.ai_scope_mode_effective,
            }
        ]
        self.ai_prompt = ""
        self._append_audit_entry(
            "assistant.ask.fallback",
            f"Pergunta atendida em modo heurístico; modelo {model_name}",
            "assistant",
            {
                "question": prompt,
                "answer": self.ai_answer,
                "model": model_name,
                "assistant_scope": self.ai_scope_mode_effective,
                "answer_mode": "fallback",
                "sources": rag_sources,
            },
        )
        self.toast_message = "Runtime local indisponível; análise heurística apresentada"
        self.toast_type = "error"


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


def custom_option_field(label: str, value: rx.Var, on_change, on_confirm, placeholder: str, help_text: str = "") -> rx.Component:
    from ssecur1.ui.common import build_custom_option_field

    return build_custom_option_field(
        label=label,
        value=value,
        on_change=on_change,
        on_confirm=on_confirm,
        placeholder=placeholder,
        help_text=help_text,
    )


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


def auditoria_view() -> rx.Component:
    from ssecur1.ui.operacoes import build_auditoria_view

    return build_auditoria_view(State=State, CARD_STYLE=CARD_STYLE)


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
        custom_option_field=custom_option_field,
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
        custom_option_field=custom_option_field,
        table_text_cell=table_text_cell,
        data_table=data_table,
    )


def usuarios_view() -> rx.Component:
    from ssecur1.ui.admin_people import build_usuarios_view

    return build_usuarios_view(
        State=State,
        CARD_STYLE=CARD_STYLE,
        field_block=field_block,
        custom_option_field=custom_option_field,
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
        custom_option_field=custom_option_field,
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
        auditoria_view=auditoria_view,
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
