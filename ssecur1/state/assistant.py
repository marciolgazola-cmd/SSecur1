from __future__ import annotations

import json
import math
import re
import secrets
import subprocess
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta
from hashlib import sha1
from pathlib import Path
from typing import Any

import reflex as rx
from sqlalchemy import or_

from ssecur1.db import (
    ActionPlanModel,
    ActionTaskModel,
    AssistantChunkModel,
    AssistantConversationModel,
    AssistantDocumentModel,
    AssistantMessageModel,
    AssistantRecommendationModel,
    ClientModel,
    FormModel,
    InterviewSessionModel,
    ProjectModel,
    QuestionModel,
    ResponseModel,
    SessionLocal,
    TenantModel,
    UserModel,
)
from ssecur1.utils import (
    format_display_date as _format_display_date,
    format_display_datetime as _format_display_datetime,
    loads_json as _loads_json,
    now_brasilia as _now_brasilia,
)


AUDIT_LOG_PATH = Path(".states") / "audit.log"
EMBED_MODEL = "nomic-embed-text:latest"


def run_ollama_command(*args: str, input_text: str | None = None, timeout: int = 60) -> str:
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


def parse_ollama_list(raw_output: str) -> list[dict[str, str]]:
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


def append_audit_file(entry: dict[str, str]) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(entry, ensure_ascii=True) + "\n")


def extract_json_code_block(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"```json\s*(\{.*?\})\s*```", value, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


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


class AssistantStateMixin:
    dragged_question_text: str = ""
    uploaded_resources: list[str] = []
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
    ai_prompt: str = ""
    ai_answer: str = ""

    def prepare_ai_view(self):
        self.ai_answer = ""
        self.dragged_question_text = ""
        self.refresh_ai_recommendations()
        self.load_ai_history()

    def _is_default_knowledge_scope(self, value: str | None) -> bool:
        return str(value or "").strip().lower() in {"default", "smartlab", "global"}

    def _ai_knowledge_scope_db_value(self) -> str:
        return "default" if self.ai_knowledge_scope_effective == "default" else "tenant"

    def _default_knowledge_scope_filter(self):
        return AssistantDocumentModel.knowledge_scope.in_(["default", "smartlab"])

    def _ai_document_scope_label(self, knowledge_scope: str | None, project_id: int | None) -> str:
        if self._is_default_knowledge_scope(knowledge_scope):
            return "Workspace default"
        if str(knowledge_scope or "").strip().lower() == "group":
            return "Grupo do tenant"
        if project_id:
            return "Projeto atual"
        return "Tenant atual"

    def _prompt_requests_ai_recommendation(self, prompt: str) -> bool:
        prompt_lower = str(prompt or "").lower()
        triggers = [
            "crie recomend",
            "gere recomend",
            "gere tarefa",
            "crie tarefa",
            "sugira ação",
            "sugira acao",
            "gere ação",
            "gere acao",
            "plano de ação",
            "plano de acao",
            "recomendação",
            "recomendacao",
        ]
        return any(token in prompt_lower for token in triggers)

    def _prompt_needs_deep_analysis(self, prompt: str) -> bool:
        normalized = str(prompt or "").lower()
        triggers = [
            "relatório",
            "relatorio",
            "análise",
            "analise",
            "recomenda",
            "dimens",
            "aderente",
            "aderência",
            "aderencia",
            "cultura de segurança",
            "cultura de seguranca",
            "completo",
        ]
        return any(token in normalized for token in triggers)

    def _prompt_requests_audit_json(self, prompt: str) -> bool:
        normalized = str(prompt or "").lower()
        return (
            "json" in normalized
            and any(
                token in normalized
                for token in [
                    "auditoria",
                    "audit",
                    "rastreabilidade",
                    "calculo",
                    "cálculo",
                    "como chegou",
                    "de onde veio",
                ]
            )
        )

    def _classify_ai_prompt_mode(self, prompt: str) -> str:
        normalized = str(prompt or "").lower()
        factual_triggers = [
            "quanto",
            "quantas",
            "quantos",
            "número",
            "numero",
            "total",
            "quem respondeu",
            "quem foram",
            "nomes",
            "como chegou",
            "de onde veio",
            "passo a passo",
            "racional",
            "calculo",
            "cálculo",
            "mostre",
            "liste",
            "listar",
            "json",
            "auditoria",
            "audit",
            "rastreabilidade",
            "fonte do dado",
        ]
        analytical_triggers = [
            "analise",
            "análise",
            "relatorio",
            "relatório",
            "interprete",
            "interpretação",
            "interpretacao",
            "recomende",
            "recomendação",
            "recomendacao",
            "priorize",
            "plano de ação",
            "plano de acao",
            "lacunas",
            "riscos",
            "governança",
            "governanca",
        ]
        if self._prompt_requests_audit_json(prompt):
            return "audit"
        factual_hits = sum(1 for token in factual_triggers if token in normalized)
        analytical_hits = sum(1 for token in analytical_triggers if token in normalized)
        if factual_hits and factual_hits >= analytical_hits:
            return "factual"
        if analytical_hits:
            return "analytical"
        return "factual"

    def _resolve_ai_target_tenant_and_project(self) -> tuple[str, int | None]:
        target_tenant = self.selected_project_source_tenant if self.ai_scope_mode_effective == "projeto" else self.current_tenant
        project_id = int(self.selected_project_id) if self.ai_scope_mode_effective == "projeto" and self.selected_project_id and self.selected_project_id.isdigit() else None
        return target_tenant, project_id

    def _resolve_ai_conversation_identity(self) -> tuple[str, int | None, str, str]:
        target_tenant, project_id = self._resolve_ai_target_tenant_and_project()
        user_email = self.login_email.strip().lower() or "anonimo"
        scope_mode = self.ai_scope_mode_effective
        return target_tenant, project_id, user_email, scope_mode

    def _ensure_ai_conversation(self, session) -> AssistantConversationModel:
        target_tenant, project_id, user_email, scope_mode = self._resolve_ai_conversation_identity()
        query = session.query(AssistantConversationModel).filter(
            AssistantConversationModel.tenant_id == target_tenant,
            AssistantConversationModel.user_email == user_email,
            AssistantConversationModel.scope_mode == scope_mode,
            AssistantConversationModel.status == "active",
        )
        if project_id is None:
            query = query.filter(AssistantConversationModel.project_id.is_(None))
        else:
            query = query.filter(AssistantConversationModel.project_id == project_id)
        conversation = query.order_by(AssistantConversationModel.updated_at.desc(), AssistantConversationModel.id.desc()).first()
        if conversation:
            return conversation
        title = f"IA {scope_mode}"
        if project_id is not None:
            title = f"IA projeto {project_id}"
        conversation = AssistantConversationModel(
            tenant_id=target_tenant,
            project_id=project_id,
            user_email=user_email,
            scope_mode=scope_mode,
            title=title,
            status="active",
            updated_at=datetime.utcnow(),
        )
        session.add(conversation)
        session.flush()
        return conversation

    def load_ai_history(self):
        session = SessionLocal()
        conversation = self._ensure_ai_conversation(session)
        messages = (
            session.query(AssistantMessageModel)
            .filter(AssistantMessageModel.conversation_id == int(conversation.id))
            .order_by(AssistantMessageModel.id.asc())
            .all()
        )
        interactions: list[dict[str, str]] = []
        pending_question: dict[str, str] | None = None
        for row in messages:
            role = str(row.role or "").strip().lower()
            created_label = _format_display_datetime(row.created_at, include_seconds=True)
            if role == "user":
                pending_question = {
                    "asked_at": created_label,
                    "question": str(row.content or ""),
                    "answer": "",
                    "model": "",
                    "scope": str(conversation.scope_mode or self.ai_scope_mode_effective),
                }
                continue
            if role == "assistant":
                if pending_question is None:
                    pending_question = {
                        "asked_at": created_label,
                        "question": "",
                        "answer": "",
                        "model": "",
                        "scope": str(conversation.scope_mode or self.ai_scope_mode_effective),
                    }
                pending_question["answer"] = str(row.content or "")
                pending_question["model"] = str(row.model_name or "")
                pending_question["scope"] = str(conversation.scope_mode or self.ai_scope_mode_effective)
                interactions.append(pending_question)
                pending_question = None
        if pending_question is not None and pending_question.get("question"):
            interactions.append(pending_question)
        session.close()
        self.ai_history = interactions

    def _persist_ai_interaction(
        self,
        question: str,
        answer: str,
        model_name: str,
        prompt_mode: str,
        answer_mode: str,
        rag_sources: str,
    ):
        session = SessionLocal()
        conversation = self._ensure_ai_conversation(session)
        target_tenant = conversation.tenant_id
        project_id = conversation.project_id
        user_email = conversation.user_email
        session.add(
            AssistantMessageModel(
                conversation_id=int(conversation.id),
                tenant_id=target_tenant,
                project_id=project_id,
                user_email=user_email,
                role="user",
                content=question,
                prompt_mode=prompt_mode,
            )
        )
        session.add(
            AssistantMessageModel(
                conversation_id=int(conversation.id),
                tenant_id=target_tenant,
                project_id=project_id,
                user_email=user_email,
                role="assistant",
                content=answer,
                model_name=model_name,
                prompt_mode=prompt_mode,
                answer_mode=answer_mode,
                sources=rag_sources,
            )
        )
        conversation.updated_at = datetime.utcnow()
        session.commit()
        session.close()

    def _resolve_ai_document_scope(self) -> tuple[str, int | None]:
        target_tenant = self.selected_project_source_tenant if self.ai_scope_mode_effective == "projeto" else self.current_tenant
        project_id = int(self.selected_project_id) if self.ai_scope_mode_effective == "projeto" and self.selected_project_id and self.selected_project_id.isdigit() else None
        return target_tenant, project_id

    def _visible_ai_documents_query(self, session):
        target_tenant, project_id = self._resolve_ai_document_scope()
        group_tenant_ids = sorted(self._group_tenant_ids_for_tenant(session, target_tenant))
        query = session.query(AssistantDocumentModel).filter(
            or_(
                (
                    (AssistantDocumentModel.tenant_id == target_tenant)
                    & (AssistantDocumentModel.knowledge_scope == "tenant")
                ),
                (
                    AssistantDocumentModel.tenant_id.in_(group_tenant_ids)
                    & (AssistantDocumentModel.knowledge_scope == "group")
                ),
                self._default_knowledge_scope_filter(),
            )
        )
        if project_id is not None:
            query = query.filter(
                (
                    self._default_knowledge_scope_filter()
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
                    "project_scope": self._ai_document_scope_label(doc.knowledge_scope, doc.project_id),
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

    def _dimension_average_maturity_label(self, average: float) -> str:
        if average < 2.0:
            return "Baixa"
        if average < 3.0:
            return "Moderada"
        if average < 4.0:
            return "Boa"
        return "Alta"

    def _build_dashboard_average_explanation(self) -> str:
        rows = self.dashboard_table
        if not rows:
            return "Nao ha dados suficientes no dashboard para explicar a media geral."
        numeric_rows: list[tuple[str, float, str, str]] = []
        for row in rows:
            avg = float(row.get("media", "0") or 0)
            numeric_rows.append(
                (
                    str(row.get("form", "Formulario sem nome")),
                    avg,
                    str(row.get("respostas", "0")),
                    str(row.get("categoria", "-")),
                )
            )
        dashboard_avg = round(sum(item[1] for item in numeric_rows) / len(numeric_rows), 2)
        non_empty_rows = [item for item in numeric_rows if item[2].isdigit() and int(item[2]) > 0]
        non_empty_avg = round(sum(item[1] for item in non_empty_rows) / len(non_empty_rows), 2) if non_empty_rows else 0.0
        lines = [
            f"Media geral do dashboard: {dashboard_avg:.2f}",
            "",
            "Passo a passo do calculo:",
        ]
        for index, (form_name, avg, responses, category) in enumerate(numeric_rows, start=1):
            lines.append(
                f"{index}. Formulario '{form_name}' | categoria '{category}' | respostas {responses} | media {avg:.2f}"
            )
        formula = " + ".join(f"{item[1]:.2f}" for item in numeric_rows)
        lines.extend(
            [
                "",
                f"Formula aplicada hoje no codigo: ({formula}) / {len(numeric_rows)} = {dashboard_avg:.2f}",
                "",
                "Origem do numero:",
                "- O valor vem da media das medias por formulario exibidas no dashboard.",
                "- Formularios sem resposta entram no calculo com media 0.00.",
            ]
        )
        if non_empty_rows and len(non_empty_rows) != len(numeric_rows):
            lines.extend(
                [
                    "",
                    f"Observacao importante: se considerar apenas formularios com respostas, a media seria {non_empty_avg:.2f}, nao {dashboard_avg:.2f}.",
                    "Isso acontece porque hoje o dashboard divide pela quantidade total de formularios do tenant, inclusive os que ainda estao vazios.",
                ]
            )
        return "\n".join(lines)

    def _build_ai_dashboard_evidence(self) -> dict[str, Any]:
        rows = self.dashboard_table
        metrics = self.dashboard_metrics
        evidence_rows = [
            {
                "form": str(row.get("form", "")),
                "category": str(row.get("categoria", "")),
                "responses": str(row.get("respostas", "0")),
                "average": str(row.get("media", "0")),
                "status": str(row.get("status", "")),
            }
            for row in rows
        ]
        return {
            "dashboard_average": metrics.get("media_dashboard", "0.00"),
            "response_average": metrics.get("media_respostas", "0.00"),
            "forms_total": metrics.get("formularios", "0"),
            "forms_with_responses": metrics.get("formularios_respondidos", "0"),
            "responses_total": metrics.get("respostas", "0"),
            "rows": evidence_rows,
        }

    def _build_ai_traceability_block(
        self,
        answer_mode: str,
        dashboard_evidence: dict[str, Any],
        insights: dict[str, Any],
        rag_sources: str,
        model_name: str,
    ) -> str:
        return (
            "\n\nRastreabilidade da Resposta:\n"
            f"- Modo: {answer_mode}\n"
            f"- Motor: {model_name}\n"
            f"- Tenant: {self.current_tenant}\n"
            f"- Escopo IA: {self.ai_scope_mode_effective}\n"
            f"- Projeto selecionado: {self.selected_project_option or '-'}\n"
            f"- Media dashboard: {dashboard_evidence.get('dashboard_average', '0.00')}\n"
            f"- Media respostas: {dashboard_evidence.get('response_average', '0.00')}\n"
            f"- Formularios totais: {dashboard_evidence.get('forms_total', '0')}\n"
            f"- Formularios com respostas: {dashboard_evidence.get('forms_with_responses', '0')}\n"
            f"- Respostas consideradas: {dashboard_evidence.get('responses_total', '0')}\n"
            f"- Fontes RAG: {rag_sources}\n"
            f"- Dimensoes analisadas: {len(insights.get('dimension_breakdown', []))}\n"
            "- Criterio numerico: valores de dashboard usam o banco local; quando informado, o sistema diferencia media das medias por formulario e media direta das respostas.\n"
            "- Arredondamento: duas casas decimais."
        )

    def _build_ai_audit_payload(
        self,
        prompt: str,
        dashboard_evidence: dict[str, Any],
        insights: dict[str, Any],
        rag_sources: str,
    ) -> str:
        payload = {
            "question": prompt,
            "mode": "audit",
            "tenant": self.current_tenant,
            "assistant_scope": self.ai_scope_mode_effective,
            "selected_project": self.selected_project_option or "",
            "dashboard": dashboard_evidence,
            "insights": {
                "total_responses": insights.get("total_responses", 0),
                "total_interviews": insights.get("total_interviews", 0),
                "interviews_completed": insights.get("interviews_completed", 0),
                "interviews_in_progress": insights.get("interviews_in_progress", 0),
                "dimension_breakdown": insights.get("dimension_breakdown", []),
                "companies": insights.get("company_breakdown", []),
                "respondents": insights.get("respondent_breakdown", []),
            },
            "sources": {
                "rag": rag_sources,
                "database": "sqlite:///ssecur1.db",
                "calculation_rule": "dashboard_average = mean(form_average for each form in dashboard_table, including forms with zero responses as 0.00); response_average = mean(score for each non-null response)",
                "rounding": "2 decimal places",
            },
        }
        return "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```"

    def _build_ai_factual_answer(
        self,
        prompt: str,
        insights: dict[str, Any],
        dashboard_evidence: dict[str, Any] | None = None,
        rag_sources: str = "Sem fontes recuperadas",
    ) -> str:
        prompt_lower = prompt.lower()
        dashboard_evidence = dashboard_evidence or self._build_ai_dashboard_evidence()
        if self._prompt_requests_audit_json(prompt):
            return self._build_ai_audit_payload(prompt, dashboard_evidence, insights, rag_sources)
        asks_dashboard_average = any(
            term in prompt_lower
            for term in [
                "0.76",
                "0,76",
                "média geral",
                "media geral",
                "como chegou",
                "de onde veio",
                "passo a passo",
                "racional",
                "calculo",
                "cálculo",
            ]
        )
        asks_dashboard_context = any(term in prompt_lower for term in ["dashboard", "media", "média", "0.76", "0,76"])
        if asks_dashboard_average and asks_dashboard_context:
            base_answer = self._build_dashboard_average_explanation()
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        if self._classify_ai_prompt_mode(prompt) == "analytical" and self._prompt_needs_deep_analysis(prompt):
            return ""
        asks_companies = any(term in prompt_lower for term in ["empresa", "empresas", "cliente", "clientes"])
        asks_respondents = any(term in prompt_lower for term in ["quem respondeu", "quem delas", "quem respondeu", "respondente", "respondentes", "nomes"])
        asks_count = bool(re.search(r"\b(quantas|quantos|número|numero|total)\b", prompt_lower))
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
            base_answer = f"Entrevistas em andamento no contexto atual: {insights['interviews_in_progress']}."
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        if asks_interviews and asks_completed and asks_companies:
            base_answer = (
                f"Empresas com entrevistas concluídas: {', '.join(insights['completed_companies']) or 'nenhuma'}.\n"
                f"{chr(10).join(interview_company_lines) if interview_company_lines else 'Nenhuma entrevista concluída identificada.'}"
            )
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        if asks_interviews and asks_completed:
            base_answer = (
                f"Entrevistas concluídas no contexto atual: {insights['interviews_completed']}.\n"
                f"Entrevistados concluídos: {completed_names}."
            )
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        if asks_interviews and asks_companies:
            base_answer = (
                f"Empresas com entrevistas no contexto atual: {', '.join(insights['interview_company_names']) or 'nenhuma'}.\n"
                f"{chr(10).join(interview_company_lines) if interview_company_lines else 'Nenhum vínculo empresa-entrevista encontrado.'}"
            )
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        if asks_interviews and asks_count:
            base_answer = (
                f"Total de entrevistas no contexto atual: {insights['total_interviews']}.\n"
                f"Concluídas: {insights['interviews_completed']} | Em andamento: {insights['interviews_in_progress']}."
            )
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")

        if asks_companies and asks_respondents:
            base_answer = (
                f"Empresas que responderam: {', '.join(insights['company_names']) or 'nenhuma'}.\n"
                f"{chr(10).join(company_lines) if company_lines else 'Nenhum vínculo empresa-respondente encontrado.'}"
            )
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        if asks_companies and asks_count:
            base_answer = (
                f"Total de empresas com respostas: {len(insights['company_names'])}.\n"
                f"Empresas: {', '.join(insights['company_names']) or 'nenhuma'}."
            )
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        if asks_companies:
            base_answer = (
                f"Empresas que responderam: {', '.join(insights['company_names']) or 'nenhuma'}.\n"
                f"{chr(10).join(company_lines) if company_lines else 'Nenhuma empresa identificada.'}"
            )
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        if asks_respondents and asks_count:
            base_answer = (
                f"Total de respostas: {insights['total_responses']}.\n"
                f"{chr(10).join(respondent_lines) if respondent_lines else 'Nenhum respondente identificado.'}"
            )
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        if asks_respondents:
            base_answer = chr(10).join(respondent_lines) if respondent_lines else "Nenhum respondente identificado."
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        if asks_count and "respost" in prompt_lower:
            base_answer = (
                f"Total de respostas no contexto atual: {insights['total_responses']}.\n"
                f"Empresas: {', '.join(insights['company_names']) or 'nenhuma'}."
            )
            return base_answer + self._build_ai_traceability_block("factual", dashboard_evidence, insights, rag_sources, "banco_local")
        return ""

    def _build_ai_dimension_analysis_answer(self, prompt: str, insights: dict[str, Any], context: dict[str, str], rag_sources: str) -> str:
        dimensions = insights.get("dimension_breakdown", [])
        if not dimensions:
            return ""
        lines: list[str] = []
        for item in dimensions:
            avg = float(item["average"])
            if avg < 2:
                recommendation = "Prioridade crítica: atuar imediatamente com liderança, comunicação e reforço de comportamento seguro."
            elif avg < 3:
                recommendation = "Prioridade alta: criar ações de correção, rotina de acompanhamento e reforço operacional."
            elif avg < 4:
                recommendation = "Prioridade moderada: consolidar práticas e reduzir variação entre equipes."
            else:
                recommendation = "Boa aderência: manter disciplina, evidências e replicar a prática nas demais áreas."
            lines.append(
                f"- {item['dimension']}: média {item['average']} / 5, respostas {item['responses']}, leitura {item['maturity']}. {recommendation}"
            )
        executive = (
            "Aderência baixa à cultura de segurança."
            if any(float(item["average"]) < 2.5 for item in dimensions)
            else (
                "Aderência moderada à cultura de segurança."
                if any(float(item["average"]) < 4 for item in dimensions)
                else "Aderência alta à cultura de segurança."
            )
        )
        return (
            "Especialista IA SSecur1\n"
            "Relatório analítico do contexto atual\n\n"
            f"Leitura executiva: {executive}\n"
            f"Total de respostas avaliadas: {insights['total_responses']}\n"
            f"Empresas no contexto: {', '.join(insights['company_names']) or 'nenhuma'}\n"
            f"Tenant analisado: {context['tenant']}\n\n"
            "Análise por dimensões:\n"
            f"{chr(10).join(lines)}\n\n"
            "Recomendações gerais:\n"
            "1. Priorizar as dimensões com média mais baixa para plano de ação imediato.\n"
            "2. Cruzar as respostas críticas com política, procedimento e evidência do mesmo contexto.\n"
            "3. Converter lacunas recorrentes em tarefas com responsável, prazo e evidência esperada.\n"
            f"Fontes RAG consideradas: {rag_sources}."
        )

    def _extract_recommendations_from_ai_answer(self, answer: str) -> list[dict[str, str]]:
        structured = self._extract_structured_recommendations(answer)
        if structured:
            return structured
        raw_lines = [line.strip() for line in str(answer or "").splitlines() if line.strip()]
        normalized_lines: list[str] = []
        for line in raw_lines:
            cleaned = re.sub(r"^\d+[\.\)\-:]\s*", "", line).strip()
            cleaned = re.sub(r"^[-*]\s*", "", cleaned).strip()
            if len(cleaned) < 12:
                continue
            lowered = cleaned.lower()
            if lowered.startswith(("especialista ia", "relatório", "relatorio", "leitura executiva", "análise por dimens", "analise por dimens", "recomendações gerais", "recomendacoes gerais", "fontes rag", "tenant analisado", "total de respostas", "empresas no contexto")):
                continue
            if ":" in cleaned and len(cleaned.split(":", 1)[0]) < 28:
                maybe_label, maybe_text = cleaned.split(":", 1)
                if maybe_label.strip().lower() in {"1", "2", "3", "4", "5", "6", "recomendação", "recomendacao"}:
                    cleaned = maybe_text.strip()
            normalized_lines.append(cleaned)
        recommendations: list[dict[str, str]] = []
        seen_titles: set[str] = set()
        for line in normalized_lines:
            title = line.rstrip(".; ")
            key = title.casefold()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            recommendations.append(
                {
                    "title": title,
                    "owner": "Liderança do processo",
                    "due_date": _format_display_date(_now_brasilia() + timedelta(days=30)),
                    "expected_result": f"Executar a recomendação '{title}' com evidência objetiva de conclusão.",
                }
            )
            if len(recommendations) >= 6:
                break
        return recommendations

    def _extract_structured_recommendations(self, answer: str) -> list[dict[str, str]]:
        raw_answer = str(answer or "").strip()
        if not raw_answer:
            return []
        candidates: list[str] = []
        fenced_blocks = re.findall(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", raw_answer, flags=re.DOTALL | re.IGNORECASE)
        candidates.extend(fenced_blocks)
        candidates.extend(re.findall(r"(\{[\s\S]*\"recommendations\"[\s\S]*\})", raw_answer, flags=re.IGNORECASE))
        seen: set[str] = set()
        parsed_recommendations: list[dict[str, str]] = []
        for candidate in candidates:
            snippet = candidate.strip()
            if not snippet or snippet in seen:
                continue
            seen.add(snippet)
            try:
                payload = json.loads(snippet)
            except json.JSONDecodeError:
                continue
            items = payload.get("recommendations", []) if isinstance(payload, dict) else payload
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "").strip()
                if not title:
                    continue
                parsed_recommendations.append(
                    {
                        "title": title,
                        "owner": str(item.get("owner") or "Liderança do processo").strip() or "Liderança do processo",
                        "due_date": str(item.get("due_date") or _format_display_date(_now_brasilia() + timedelta(days=30))).strip(),
                        "expected_result": str(item.get("expected_result") or f"Executar a recomendação '{title}' com evidência objetiva de conclusão.").strip(),
                    }
                )
            if parsed_recommendations:
                break
        return parsed_recommendations[:6]

    @rx.var
    def ollama_models_data(self) -> list[dict[str, str]]:
        return parse_ollama_list(run_ollama_command("list"))

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
        version_output = run_ollama_command("--version")
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
        session = SessionLocal()
        target_tenant, _ = self._resolve_ai_document_scope()
        if len(self._group_tenant_ids_for_tenant(session, target_tenant)) > 1:
            options.append("group")
        session.close()
        if self.user_scope == "smartlab":
            options.append("default")
        return options

    @rx.var
    def ai_knowledge_scope_effective(self) -> str:
        if self.ai_knowledge_scope == "group" and "group" in self.ai_knowledge_scope_options:
            return "group"
        if self._is_default_knowledge_scope(self.ai_knowledge_scope) and self.user_scope == "smartlab":
            return "default"
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
                "project_scope": self._ai_document_scope_label(row.knowledge_scope, row.project_id),
                "knowledge_scope": (
                    "default"
                    if self._is_default_knowledge_scope(row.knowledge_scope)
                    else ("group" if str(row.knowledge_scope or "").strip().lower() == "group" else "tenant")
                ),
                "uploaded_by": row.uploaded_by or "-",
                "uploaded_at": _format_display_datetime(row.uploaded_at),
                "file_size": f"{max(int(row.file_size or 0) // 1024, 1)} KB" if int(row.file_size or 0) > 0 else "-",
                "chunk_count": str(chunk_counts.get(int(row.id), 0)),
                "can_delete": bool(not self._is_default_knowledge_scope(row.knowledge_scope) or self.user_scope == "smartlab"),
            }
            for row in rows
        ]
        session.close()
        return data

    @rx.var(cache=False)
    def ai_context_summary(self) -> dict[str, str]:
        session = SessionLocal()
        target_tenant = self.selected_project_source_tenant if self.ai_scope_mode_effective == "projeto" else self.current_tenant
        group_tenant_ids = sorted(self._group_tenant_ids_for_tenant(session, target_tenant))
        forms_count = session.query(FormModel).filter(FormModel.tenant_id == target_tenant).count()
        tenant_documents_count = session.query(AssistantDocumentModel).filter(
            AssistantDocumentModel.tenant_id == target_tenant,
            AssistantDocumentModel.knowledge_scope == "tenant",
        ).count()
        group_documents_count = session.query(AssistantDocumentModel).filter(
            AssistantDocumentModel.tenant_id.in_(group_tenant_ids),
            AssistantDocumentModel.knowledge_scope == "group",
        ).count()
        default_documents_count = session.query(AssistantDocumentModel).filter(
            self._default_knowledge_scope_filter()
        ).count()
        tenant_chunk_document_ids = [
            int(row[0])
            for row in session.query(AssistantDocumentModel.id).filter(
                AssistantDocumentModel.tenant_id == target_tenant,
                AssistantDocumentModel.knowledge_scope == "tenant",
            ).all()
        ]
        group_chunk_document_ids = [
            int(row[0])
            for row in session.query(AssistantDocumentModel.id).filter(
                AssistantDocumentModel.tenant_id.in_(group_tenant_ids),
                AssistantDocumentModel.knowledge_scope == "group",
            ).all()
        ]
        default_chunk_document_ids = [
            int(row[0])
            for row in session.query(AssistantDocumentModel.id).filter(
                self._default_knowledge_scope_filter()
            ).all()
        ]
        chunk_document_ids = list({*tenant_chunk_document_ids, *group_chunk_document_ids, *default_chunk_document_ids})
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
            "documents": str(tenant_documents_count + group_documents_count + default_documents_count),
            "tenant_documents": str(tenant_documents_count),
            "group_documents": str(group_documents_count),
            "default_documents": str(default_documents_count),
            "chunks": str(chunk_count),
            "forms": str(forms_count),
            "interviews": str(len(interviews)),
            "responses": str(responses_count),
            "actions_total": str(actions_total),
            "actions_open": str(actions_open),
            "group_tenants": ", ".join(group_tenant_ids),
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
        question_ids = sorted({int(row.question_id) for row in responses if row.question_id is not None})
        question_dimension_lookup: dict[int, str] = {}
        if question_ids:
            question_dimension_lookup = {
                int(question_id): str(dimension or "Sem dimensão")
                for question_id, dimension in session.query(QuestionModel.id, QuestionModel.dimension)
                .filter(QuestionModel.id.in_(question_ids))
                .all()
            }
        user_lookup = {int(row.id): row.name for row in user_rows}
        user_client_lookup = {int(row.id): str(row.client_id) if row.client_id is not None else "" for row in user_rows}
        client_lookup = {str(row.id): row.trade_name or row.name for row in client_rows}
        respondent_counts: dict[str, int] = {}
        company_counts: dict[str, int] = {}
        company_respondent_map: dict[str, set[str]] = {}
        interview_status_counts: dict[str, int] = {}
        interview_company_counts: dict[str, int] = {}
        interview_company_status_map: dict[str, set[str]] = {}
        dimension_totals: dict[str, int] = {}
        dimension_counts: dict[str, int] = {}
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
            dimension = question_dimension_lookup.get(int(row.question_id), "Sem dimensão") if row.question_id is not None else "Sem dimensão"
            score = int(row.score or 0) if row.score is not None else 0
            dimension_totals[dimension] = dimension_totals.get(dimension, 0) + score
            dimension_counts[dimension] = dimension_counts.get(dimension, 0) + 1
        interview_names = [row.interviewee_name for row in interviews if row.interviewee_name]
        session.close()
        top_respondents = [{"name": name, "responses": count} for name, count in sorted(respondent_counts.items(), key=lambda item: (-item[1], item[0]))]
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
        dimension_breakdown = []
        for dimension, total_score in sorted(dimension_totals.items(), key=lambda item: item[0]):
            count = dimension_counts.get(dimension, 0)
            average = round(total_score / count, 2) if count else 0.0
            dimension_breakdown.append(
                {
                    "dimension": dimension,
                    "average": f"{average:.2f}",
                    "responses": str(count),
                    "maturity": self._dimension_average_maturity_label(average),
                }
            )
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
            "dimension_breakdown": dimension_breakdown,
        }

    @rx.var
    def ai_source_snapshot(self) -> list[dict[str, str]]:
        return [
            {"label": "Documentos IA", "value": self.ai_context_summary["documents"], "detail": "PDF, Word, Excel e outros artefatos indexados"},
            {"label": "Grupo", "value": self.ai_context_summary["group_documents"], "detail": "materiais compartilhados entre tenants autorizados do mesmo grupo"},
            {"label": "Workspace default", "value": self.ai_context_summary["default_documents"], "detail": "materiais globais administrados no workspace default"},
            {"label": "Chunks RAG", "value": self.ai_context_summary["chunks"], "detail": "trechos prontos para recuperação contextual"},
            {"label": "Formulários", "value": self.ai_context_summary["forms"], "detail": "instrumentos ativos no tenant"},
            {"label": "Entrevistas", "value": self.ai_context_summary["interviews"], "detail": "sessões vinculadas ao contexto"},
            {"label": "Respostas", "value": self.ai_context_summary["responses"], "detail": "evidências textuais e scores"},
            {"label": "Planos em aberto", "value": self.ai_context_summary["actions_open"], "detail": "ações ainda não concluídas"},
        ]

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
    def audit_ai_events_data(self) -> list[dict[str, str]]:
        data: list[dict[str, str]] = []
        for item in self.audit_filtered_events_data:
            event_name = item.get("event", "")
            scope = item.get("scope", "")
            if not (scope == "assistant" or event_name.startswith("assistant")):
                continue
            enriched = dict(item)
            answer_text = enriched.get("answer", "")
            enriched["has_traceability"] = "1" if "Rastreabilidade da Resposta:" in answer_text else "0"
            enriched["audit_json"] = extract_json_code_block(answer_text)
            enriched["has_audit_json"] = "1" if enriched["audit_json"] else "0"
            enriched["prompt_mode"] = enriched.get("prompt_mode", "")
            data.append(enriched)
        return data

    @rx.var
    def audit_system_events_data(self) -> list[dict[str, str]]:
        return [
            item
            for item in self.audit_filtered_events_data
            if not (item.get("scope", "") == "assistant" or item.get("event", "").startswith("assistant"))
        ]

    @rx.var
    def audit_ai_summary(self) -> list[dict[str, str]]:
        total = len(self.audit_ai_events_data)
        factual = sum(1 for item in self.audit_ai_events_data if item.get("answer_mode") == "factual")
        llm = sum(1 for item in self.audit_ai_events_data if item.get("answer_mode") == "llm")
        fallback = sum(1 for item in self.audit_ai_events_data if item.get("answer_mode") == "fallback")
        traceability = sum(1 for item in self.audit_ai_events_data if item.get("has_traceability") == "1")
        audit_json = sum(1 for item in self.audit_ai_events_data if item.get("has_audit_json") == "1")
        return [
            {"label": "Interações IA", "count": str(total)},
            {"label": "Factual", "count": str(factual)},
            {"label": "LLM Local", "count": str(llm)},
            {"label": "Fallback", "count": str(fallback)},
            {"label": "Com Rastreabilidade", "count": str(traceability)},
            {"label": "Com JSON Auditoria", "count": str(audit_json)},
        ]

    @rx.var
    def audit_overview_cards(self) -> list[dict[str, str]]:
        return [
            {"label": "Eventos Filtrados", "count": str(len(self.audit_filtered_events_data))},
            {"label": "Eventos Sistema", "count": str(len(self.audit_system_events_data))},
            {"label": "Eventos IA", "count": str(len(self.audit_ai_events_data))},
            {"label": "Tenants no Filtro", "count": str(len({item.get('tenant', '') for item in self.audit_filtered_events_data if item.get('tenant', '')}))},
        ]

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

    def refresh_ai_recommendations(self):
        target_tenant, project_id = self._resolve_ai_target_tenant_and_project()
        session = SessionLocal()
        query = (
            session.query(AssistantRecommendationModel)
            .filter(
                AssistantRecommendationModel.tenant_id == target_tenant,
                AssistantRecommendationModel.status == "open",
            )
            .order_by(AssistantRecommendationModel.created_at.desc(), AssistantRecommendationModel.id.desc())
        )
        if project_id is not None:
            query = query.filter(AssistantRecommendationModel.project_id == project_id)
        rows = query.all()
        session.close()
        self.ai_recommendation_items = [
            {
                "id": f"ai-rec-{row.id}",
                "db_id": str(row.id),
                "title": str(row.title or ""),
                "owner": str(row.owner or ""),
                "due_date": str(row.due_date or ""),
                "expected_result": str(row.expected_result or ""),
                "project_id": str(row.project_id) if row.project_id is not None else "",
                "action_plan_id": "",
            }
            for row in rows
        ]
        if self.ai_recommendation_editing_id and not any(item["id"] == self.ai_recommendation_editing_id for item in self.ai_recommendation_items):
            self.ai_recommendation_editing_id = ""
        if self.ai_recommendation_sending_id and not any(item["id"] == self.ai_recommendation_sending_id for item in self.ai_recommendation_items):
            self.ai_recommendation_sending_id = ""

    def _project_option_for_id(self, project_id: str) -> str:
        for item in self.projects_data:
            if str(item.get("id")) == str(project_id):
                return f'{item["id"]} - {item["name"]}'
        return ""

    def _project_source_tenant_by_id(self, project_id: str) -> str:
        for item in self.projects_data:
            if str(item.get("id")) == str(project_id):
                return str(item.get("source_tenant") or self.current_tenant)
        return self.current_tenant

    def _action_plan_options_for_project(self, project_id: str) -> list[str]:
        if not str(project_id).isdigit():
            return []
        target_tenant = self._project_source_tenant_by_id(project_id)
        session = SessionLocal()
        rows = (
            session.query(ActionPlanModel.id, ActionPlanModel.title)
            .filter(
                ActionPlanModel.project_id == int(project_id),
                ActionPlanModel.tenant_id == target_tenant,
            )
            .order_by(ActionPlanModel.title.asc())
            .all()
        )
        session.close()
        return [f"{row[0]} - {row[1]}" for row in rows]

    @rx.var(cache=False)
    def ai_recommendation_cards_data(self) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for item in self.ai_recommendation_items:
            project_id = str(item.get("project_id") or "")
            action_plan_id = str(item.get("action_plan_id") or "")
            action_plan_options = self._action_plan_options_for_project(project_id)
            selected_plan_option = next(
                (option for option in action_plan_options if option.split(" - ", 1)[0].strip() == action_plan_id),
                "",
            )
            data.append(
                {
                    "id": str(item["id"]),
                    "title": str(item["title"]),
                    "owner": str(item["owner"]),
                    "due_date": str(item["due_date"]),
                    "expected_result": str(item["expected_result"]),
                    "project_id": project_id,
                    "project_option": self._project_option_for_id(project_id),
                    "action_plan_id": action_plan_id,
                    "action_plan_option": selected_plan_option,
                    "action_plan_options": action_plan_options,
                    "is_editing": bool(str(item["id"]) == self.ai_recommendation_editing_id),
                    "is_sending": bool(str(item["id"]) == self.ai_recommendation_sending_id),
                }
            )
        return data

    @rx.var(cache=False)
    def ai_recommendation_active_action_plan_options(self) -> list[str]:
        if not self.ai_recommendation_sending_id:
            return []
        item = next(
            (row for row in self.ai_recommendation_items if str(row.get("id")) == self.ai_recommendation_sending_id),
            None,
        )
        if not item:
            return []
        return self._action_plan_options_for_project(str(item.get("project_id") or ""))

    def set_ai_prompt(self, value: str):
        self.ai_prompt = value

    def set_ai_selected_model(self, value: str):
        self.ai_selected_model = value

    def set_ai_resource_type(self, value: str):
        self.ai_resource_type = value

    def set_ai_knowledge_scope(self, value: str):
        self.ai_knowledge_scope = "default" if self._is_default_knowledge_scope(value) else "tenant"

    def set_ai_scope_mode(self, value: str):
        self.ai_scope_mode = value
        self.ai_history = []
        self.ai_answer = ""
        self.ai_prompt = ""
        self.load_ai_history()

    def _update_ai_recommendation_field(self, recommendation_id: str, field_name: str, value: str):
        updated: list[dict[str, str]] = []
        for item in self.ai_recommendation_items:
            if str(item.get("id")) == str(recommendation_id):
                next_item = dict(item)
                next_item[field_name] = value
                if field_name == "project_id":
                    next_item["action_plan_id"] = ""
                updated.append(next_item)
            else:
                updated.append(item)
        self.ai_recommendation_items = updated

    def start_edit_ai_recommendation(self, recommendation_id: str):
        self.ai_recommendation_snapshot = [dict(item) for item in self.ai_recommendation_items]
        self.ai_recommendation_editing_id = recommendation_id
        self.ai_recommendation_sending_id = ""

    def save_ai_recommendation_edit(self, recommendation_id: str):
        item = next((row for row in self.ai_recommendation_items if str(row.get("id")) == str(recommendation_id)), None)
        if not item:
            self.toast_message = "Recomendação não encontrada"
            self.toast_type = "error"
            return
        db_id = str(item.get("db_id") or "")
        if not db_id.isdigit():
            self.toast_message = "Registro da recomendação inválido"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = session.query(AssistantRecommendationModel).filter(AssistantRecommendationModel.id == int(db_id)).first()
        if not row:
            session.close()
            self.toast_message = "Recomendação não encontrada no banco"
            self.toast_type = "error"
            return
        row.title = str(item.get("title") or "").strip() or row.title
        row.owner = str(item.get("owner") or "").strip()
        row.due_date = str(item.get("due_date") or "").strip()
        row.expected_result = str(item.get("expected_result") or "").strip()
        session.commit()
        session.close()
        self.ai_recommendation_snapshot = []
        self.ai_recommendation_editing_id = ""
        self.toast_message = "Recomendação atualizada"
        self.toast_type = "success"

    def cancel_ai_recommendation_edit(self, recommendation_id: str):
        if self.ai_recommendation_snapshot:
            self.ai_recommendation_items = [dict(item) for item in self.ai_recommendation_snapshot]
        self.ai_recommendation_snapshot = []
        if self.ai_recommendation_editing_id == recommendation_id:
            self.ai_recommendation_editing_id = ""
        if self.ai_recommendation_sending_id == recommendation_id:
            self.ai_recommendation_sending_id = ""

    def delete_ai_recommendation(self, recommendation_id: str):
        item = next((row for row in self.ai_recommendation_items if str(row.get("id")) == str(recommendation_id)), None)
        if not item:
            return
        db_id = str(item.get("db_id") or "")
        if db_id.isdigit():
            session = SessionLocal()
            row = session.query(AssistantRecommendationModel).filter(AssistantRecommendationModel.id == int(db_id)).first()
            if row:
                row.status = "discarded"
                session.commit()
            session.close()
        self.ai_recommendation_items = [row for row in self.ai_recommendation_items if str(row.get("id")) != str(recommendation_id)]
        if self.ai_recommendation_editing_id == recommendation_id:
            self.ai_recommendation_editing_id = ""
        if self.ai_recommendation_sending_id == recommendation_id:
            self.ai_recommendation_sending_id = ""
        self.toast_message = "Recomendação descartada"
        self.toast_type = "success"

    def set_ai_recommendation_title(self, recommendation_id: str, value: str):
        self._update_ai_recommendation_field(recommendation_id, "title", value)

    def set_ai_recommendation_owner(self, recommendation_id: str, value: str):
        self._update_ai_recommendation_field(recommendation_id, "owner", value)

    def set_ai_recommendation_due_date(self, recommendation_id: str, value: str):
        self._update_ai_recommendation_field(recommendation_id, "due_date", value)

    def set_ai_recommendation_expected_result(self, recommendation_id: str, value: str):
        self._update_ai_recommendation_field(recommendation_id, "expected_result", value)

    def set_ai_recommendation_project_option(self, recommendation_id: str, value: str):
        project_id = value.split(" - ", 1)[0].strip() if value else ""
        self._update_ai_recommendation_field(recommendation_id, "project_id", project_id)

    def set_ai_recommendation_action_plan_option(self, recommendation_id: str, value: str):
        action_plan_id = value.split(" - ", 1)[0].strip() if value else ""
        self._update_ai_recommendation_field(recommendation_id, "action_plan_id", action_plan_id)

    def open_ai_recommendation_send(self, recommendation_id: str):
        updated: list[dict[str, str]] = []
        for item in self.ai_recommendation_items:
            if str(item.get("id")) != str(recommendation_id):
                updated.append(item)
                continue
            next_item = dict(item)
            if not str(next_item.get("project_id") or "") and self.selected_project_id:
                next_item["project_id"] = self.selected_project_id
            updated.append(next_item)
        self.ai_recommendation_items = updated
        self.ai_recommendation_sending_id = recommendation_id

    def cancel_ai_recommendation_send(self, recommendation_id: str):
        if self.ai_recommendation_sending_id == recommendation_id:
            self.ai_recommendation_sending_id = ""

    def set_audit_filter_scope(self, value: str):
        self.audit_filter_scope = value

    def set_audit_active_tab(self, value: str):
        self.audit_active_tab = value

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
        target_tenant = "default" if knowledge_scope == "default" else (self.selected_project_source_tenant if self.ai_scope_mode_effective == "projeto" else self.current_tenant)
        project_scope = (
            "default"
            if knowledge_scope == "default"
            else ("group" if knowledge_scope == "group" else (self.selected_project_id if self.ai_scope_mode_effective == "projeto" and self.selected_project_id and self.selected_project_id.isdigit() else "tenant"))
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
            stored_name = f"{_now_brasilia().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}_{safe_name}"
            file_bytes = await file.read()
            stored_path = upload_dir / stored_name
            stored_path.write_bytes(file_bytes)
            saved_files.append(safe_name)
            document = AssistantDocumentModel(
                tenant_id=target_tenant,
                project_id=(int(self.selected_project_id) if knowledge_scope == "tenant" and self.ai_scope_mode_effective == "projeto" and self.selected_project_id and self.selected_project_id.isdigit() else None),
                knowledge_scope=("default" if knowledge_scope == "default" else knowledge_scope),
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
            {"knowledge_scope": knowledge_scope, "sources": " | ".join(indexing_notes)},
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
        if self._is_default_knowledge_scope(row.knowledge_scope) and self.user_scope != "smartlab":
            session.close()
            self.toast_message = "Somente a SmartLab pode remover documentos do workspace default"
            self.toast_type = "error"
            return
        target_tenant = self.selected_project_source_tenant if self.selected_project_id else self.current_tenant
        if str(row.knowledge_scope or "").strip().lower() == "group":
            valid_group_tenants = self._group_tenant_ids_for_tenant(session, target_tenant)
            if row.tenant_id not in valid_group_tenants:
                session.close()
                return
        elif not self._is_default_knowledge_scope(row.knowledge_scope) and row.tenant_id != target_tenant:
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

    def send_ai_recommendation_to_plan(self, recommendation_id: str):
        item = next((row for row in self.ai_recommendation_items if str(row.get("id")) == str(recommendation_id)), None)
        if not item:
            self.toast_message = "Recomendação não encontrada"
            self.toast_type = "error"
            return
        project_id = str(item.get("project_id") or "")
        action_plan_id = str(item.get("action_plan_id") or "")
        if not project_id.isdigit():
            self.toast_message = "Selecione o projeto de destino"
            self.toast_type = "error"
            return
        if not action_plan_id.isdigit():
            self.toast_message = "Selecione o plano de ação que receberá a tarefa"
            self.toast_type = "error"
            return
        target_tenant = self._project_source_tenant_by_id(project_id)
        session = SessionLocal()
        project_row = session.query(ProjectModel).filter(ProjectModel.id == int(project_id), ProjectModel.tenant_id == target_tenant).first()
        plan_row = session.query(ActionPlanModel).filter(ActionPlanModel.id == int(action_plan_id), ActionPlanModel.project_id == int(project_id), ActionPlanModel.tenant_id == target_tenant).first()
        if not project_row or not plan_row:
            session.close()
            self.toast_message = "Projeto ou plano de ação inválido para esta recomendação"
            self.toast_type = "error"
            return
        owner = str(item.get("owner") or "").strip() or "Consultoria SmartLab"
        due_date = str(item.get("due_date") or "").strip()
        start_date = _format_display_date(_now_brasilia())
        plan_title = str(plan_row.title or "Plano")
        session.add(
            ActionTaskModel(
                tenant_id=target_tenant,
                action_plan_id=int(action_plan_id),
                title=str(item.get("title") or "").strip() or "Tarefa da IA",
                owner=owner,
                start_date=start_date,
                planned_due_date=due_date,
                due_date=due_date,
                due_date_change_count=0,
                expected_result=str(item.get("expected_result") or "").strip(),
                progress=0,
            )
        )
        if str(plan_row.status or "").strip().lower() == "concluido":
            plan_row.status = "a_fazer"
            plan_row.completed_at = ""
        db_id = str(item.get("db_id") or "")
        if db_id.isdigit():
            recommendation_row = session.query(AssistantRecommendationModel).filter(AssistantRecommendationModel.id == int(db_id)).first()
            if recommendation_row:
                recommendation_row.status = "sent"
        session.commit()
        session.close()
        self.ai_recommendation_items = [row for row in self.ai_recommendation_items if str(row.get("id")) != str(recommendation_id)]
        self.ai_recommendation_editing_id = ""
        self.ai_recommendation_sending_id = ""
        self._append_audit_entry(
            "assistant.task.promote",
            f"Recomendação enviada como tarefa para o plano {plan_title}",
            "assistant",
            {"project_id": project_id, "action_plan_id": action_plan_id, "title": str(item.get("title") or "")},
        )
        self.toast_message = "Recomendação enviada como tarefa para o plano selecionado"
        self.toast_type = "success"

    def ask_ai(self):
        prompt = (self.ai_prompt or "").strip()
        if not prompt:
            self.toast_message = "Escreva uma pergunta ou objetivo para o Especialista IA"
            self.toast_type = "error"
            return
        should_generate_recommendations = self._prompt_requests_ai_recommendation(prompt)
        rows = self.dashboard_table
        metrics = self.dashboard_metrics
        avg = float(metrics.get("media_dashboard", "0") or 0)
        avg_responses = float(metrics.get("media_respostas", "0") or 0)
        low_rows = [r for r in rows if r["status"] != "Forte"]
        docs = self.ai_documents_data[:6]
        doc_summary = ", ".join(f'{item["file_name"]} ({item["resource_type"]})' for item in docs) or "Sem documentos anexados"
        risk_summary = ", ".join(f'{item["form"]}: {item["status"]} ({item["media"]})' for item in low_rows[:4]) or "Sem criticidades explícitas no dashboard"
        context = self.ai_context_summary
        insights = self.ai_response_insights
        dashboard_evidence = self._build_ai_dashboard_evidence()
        retrieved_chunks = self._retrieve_ai_chunks(prompt, limit=6)
        rag_sources = ", ".join(f'{item["file_name"]} [{item["project_scope"]}]' for item in retrieved_chunks) or "Sem fontes recuperadas"
        rag_context = "\n\n".join(
            f"Fonte {index + 1}: {item['file_name']} | {item['resource_type']} | {item['project_scope']} | score {item['score']}\nTrecho: {item['content']}"
            for index, item in enumerate(retrieved_chunks)
        ) or "Nenhum trecho documental foi recuperado para esta pergunta."
        respondent_summary = ", ".join(f"{item['name']} ({item['responses']} respostas)" for item in insights["respondent_breakdown"][:6]) or "Nenhum respondente identificado"
        company_summary = ", ".join(f"{item['name']} ({item['responses']} respostas)" for item in insights["company_breakdown"][:6]) or "Nenhuma empresa identificada"
        prompt_mode = self._classify_ai_prompt_mode(prompt)
        factual_answer = self._build_ai_factual_answer(prompt, insights, dashboard_evidence, rag_sources)
        if factual_answer:
            self._persist_ai_interaction(prompt, factual_answer, "banco_local", prompt_mode, "factual", rag_sources)
            self.ai_answer = factual_answer
            self.ai_history = self.ai_history + [{"asked_at": _format_display_datetime(_now_brasilia(), include_seconds=True), "question": prompt, "answer": factual_answer, "model": "banco_local", "scope": self.ai_scope_mode_effective}]
            self.ai_prompt = ""
            self._append_audit_entry("assistant.ask.factual", "Pergunta respondida diretamente pelo banco local", "assistant", {"question": prompt, "answer": factual_answer, "model": "banco_local", "assistant_scope": self.ai_scope_mode_effective, "answer_mode": "factual", "prompt_mode": prompt_mode, "sources": rag_sources})
            if should_generate_recommendations:
                self.create_ai_recommendations_from_prompt(prompt, factual_answer)
            self.toast_message = "Resposta factual gerada diretamente do banco"
            self.toast_type = "success"
            return
        compiled_prompt = (
            "Você é o Especialista IA interno da SmartLab, rodando localmente e sem usar dados fora da plataforma.\n"
            "Nunca misture tenants. Responda apenas com base no contexto abaixo.\n\n"
            f"Tenant ativo: {context['tenant']}\n"
            f"Tenants do grupo visíveis: {context['group_tenants']}\n"
            f"Projeto selecionado: {self.selected_project_option or 'não selecionado'}\n"
            f"Documentos disponíveis: {context['documents']}\n"
            f"Base de grupo disponível: {context['group_documents']}\n"
            f"Workspace default disponível: {context['default_documents']}\n"
            f"Chunks RAG disponíveis: {context['chunks']}\n"
            f"Documentos do tenant/projeto: {context['tenant_documents']}\n"
            f"Formulários ativos: {context['forms']}\n"
            f"Entrevistas: {context['interviews']}\n"
            f"Respostas vinculadas: {context['responses']}\n"
            f"Respondentes identificados: {respondent_summary}\n"
            f"Empresas identificadas: {company_summary}\n"
            f"Diagnóstico por dimensões: {json.dumps(insights.get('dimension_breakdown', []), ensure_ascii=False)}\n"
            f"Ações em aberto: {context['actions_open']}\n"
            f"Média do dashboard (média das médias por formulário): {avg}\n"
            f"Média real das respostas respondidas: {avg_responses}\n"
            f"Rastreabilidade do dashboard: {json.dumps(dashboard_evidence, ensure_ascii=False)}\n"
            f"Principais alertas: {risk_summary}\n"
            f"Fontes documentais: {doc_summary}\n\n"
            "Trechos recuperados por RAG:\n"
            f"{rag_context}\n\n"
            "Objetivo do usuário:\n"
            f"{prompt}\n\n"
            "Entregue uma resposta objetiva com:\n"
            "1. leitura executiva;\n"
            "2. análise por dimensões usando escala 0 a 5, onde 0 é nada aderente e 5 é totalmente aderente;\n"
            "3. lacunas prováveis entre respostas e políticas;\n"
            "4. ações priorizadas;\n"
            "5. riscos de governança se faltar evidência documental.\n"
            "6. cite as fontes usadas pelo nome do arquivo.\n"
            "7. sempre que citar numero, informe de onde veio o dado, a formula aplicada e o criterio de arredondamento.\n"
            "8. se o numero vier do dashboard, deixe explicito se e media das medias por formulario ou media direta das respostas.\n"
            "9. se nao houver dados suficientes para explicar um numero, diga explicitamente que nao ha trilha suficiente e nao invente o racional.\n"
            "Se o usuário pedir recomendação, tarefa ou plano de ação, acrescente ao final um bloco JSON válido cercado por ```json com o formato:\n"
            '{"recommendations":[{"title":"...","owner":"...","due_date":"DD-MM-YYYY","expected_result":"..."}]}\n'
            "Não invente chaves fora desse formato.\n"
        )
        model_name = self.ai_selected_model_effective
        answer = ""
        if model_name != "Nenhum modelo local disponível":
            answer = run_ollama_command("run", model_name, input_text=compiled_prompt, timeout=120)
        if answer:
            answer = answer + self._build_ai_traceability_block("llm", dashboard_evidence, insights, rag_sources, model_name)
            self._persist_ai_interaction(prompt, answer, model_name, prompt_mode, "llm", rag_sources)
            self.ai_history = self.ai_history + [{"asked_at": _format_display_datetime(_now_brasilia(), include_seconds=True), "question": prompt, "answer": answer, "model": model_name, "scope": self.ai_scope_mode_effective}]
            self.ai_answer = answer
            self.ai_prompt = ""
            self._append_audit_entry("assistant.ask", f"Pergunta respondida com {model_name}", "assistant", {"question": prompt, "answer": answer, "model": model_name, "assistant_scope": self.ai_scope_mode_effective, "answer_mode": "llm", "prompt_mode": prompt_mode, "sources": rag_sources})
            if should_generate_recommendations:
                self.create_ai_recommendations_from_prompt(prompt, self.ai_answer)
            self.toast_message = f"Resposta gerada com {model_name}"
            self.toast_type = "success"
            return
        prompt_lower = prompt.lower()
        if any(term in prompt_lower for term in ["quantas respostas", "qtd respostas", "numero de respostas", "número de respostas"]):
            names = ", ".join(insights["respondent_names"]) or "nenhum nome identificado"
            self.ai_answer = "Especialista IA SSecur1\n" f"No contexto atual tivemos {insights['total_responses']} respostas registradas.\n" f"Respondentes identificados: {names}.\n" f"Entrevistas relacionadas: {insights['total_interviews']}."
        elif any(term in prompt_lower for term in ["quem respondeu", "nomes", "quem foram", "quais pessoas"]):
            breakdown = "\n".join(f"- {item['name']}: {item['responses']} respostas" for item in insights["respondent_breakdown"]) or "- Nenhum respondente identificado"
            self.ai_answer = "Especialista IA SSecur1\nRespondentes identificados no contexto atual:\n" f"{breakdown}"
        else:
            detailed_fallback = self._build_ai_dimension_analysis_answer(prompt, insights, context, rag_sources)
            if detailed_fallback:
                self.ai_answer = detailed_fallback + self._build_ai_traceability_block("fallback_analytical", dashboard_evidence, insights, rag_sources, model_name)
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
                ) + self._build_ai_traceability_block("fallback_local", dashboard_evidence, insights, rag_sources, model_name)
        self.ai_history = self.ai_history + [{"asked_at": _format_display_datetime(_now_brasilia(), include_seconds=True), "question": prompt, "answer": self.ai_answer, "model": model_name, "scope": self.ai_scope_mode_effective}]
        self._persist_ai_interaction(prompt, self.ai_answer, model_name, prompt_mode, "fallback", rag_sources)
        self.ai_prompt = ""
        self._append_audit_entry("assistant.ask.fallback", f"Pergunta atendida em modo heurístico; modelo {model_name}", "assistant", {"question": prompt, "answer": self.ai_answer, "model": model_name, "assistant_scope": self.ai_scope_mode_effective, "answer_mode": "fallback", "prompt_mode": prompt_mode, "sources": rag_sources})
        if should_generate_recommendations:
            self.create_ai_recommendations_from_prompt(prompt, self.ai_answer)
        self.toast_message = "Runtime local indisponível; análise heurística apresentada"
        self.toast_type = "error"

    def create_ai_recommendations_from_prompt(self, prompt: str, answer: str = ""):
        target_tenant, project_id = self._resolve_ai_target_tenant_and_project()
        recommendations = self._extract_recommendations_from_ai_answer(answer)
        source_mode = "answer"
        if not recommendations:
            source_mode = "fallback"
            critical_rows = [row for row in self.dashboard_table if row["status"] in {"Crítico", "Moderado"}]
            for row in critical_rows[:3]:
                recommendations.append(
                    {
                        "title": f"Tratar lacunas de {row['form']}",
                        "owner": "Liderança do processo",
                        "due_date": _format_display_date(_now_brasilia() + timedelta(days=30)),
                        "expected_result": f"Elevar a categoria {row['categoria']} acima de {row['media']} com base em políticas, entrevistas e evidências do tenant.",
                    }
                )
        if not recommendations:
            recommendations.append(
                {
                    "title": "Revisar aderência entre políticas e respostas",
                    "owner": "Consultoria SmartLab",
                    "due_date": _format_display_date(_now_brasilia() + timedelta(days=15)),
                    "expected_result": "Consolidar lacunas, conflitos e ausências documentais antes da próxima rodada de entrevistas.",
                }
            )
        session = SessionLocal()
        existing_query = session.query(AssistantRecommendationModel).filter(AssistantRecommendationModel.tenant_id == target_tenant, AssistantRecommendationModel.status == "open")
        if project_id is None:
            existing_query = existing_query.filter(AssistantRecommendationModel.project_id.is_(None))
        else:
            existing_query = existing_query.filter(AssistantRecommendationModel.project_id == project_id)
        for row in existing_query.all():
            row.status = "replaced"
        for item in recommendations:
            session.add(
                AssistantRecommendationModel(
                    tenant_id=target_tenant,
                    project_id=project_id,
                    title=item["title"],
                    owner=item["owner"],
                    due_date=item["due_date"],
                    expected_result=item["expected_result"],
                    status="open",
                    created_by=self.login_email.strip().lower() or "sistema",
                )
            )
        session.commit()
        session.close()
        self.refresh_ai_recommendations()
        self._append_audit_entry(
            "assistant.recommendation.generate",
            "Recomendações geradas sob demanda pelo prompt do usuário",
            "assistant",
            {"question": prompt, "tenant": target_tenant, "project_id": str(project_id or ""), "source_mode": source_mode, "count": str(len(recommendations))},
        )
