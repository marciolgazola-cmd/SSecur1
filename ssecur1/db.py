import json
import os
import hashlib
import hmac
from datetime import datetime
from pathlib import Path

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


def _resolve_database_url() -> str:
    env_url = str(os.getenv("SSECUR1_DATABASE_URL", "")).strip()
    if env_url:
        return env_url
    data_dir = str(os.getenv("SSECUR1_DATA_DIR", "")).strip()
    if data_dir:
        db_path = Path(data_dir).expanduser().resolve() / "ssecur1.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"
    return "sqlite:///ssecur1.db"


DATABASE_URL = _resolve_database_url()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def hash_password(raw_password: str) -> str:
    password = str(raw_password or "")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"pbkdf2_sha256$200000${salt.hex()}${digest.hex()}"


def verify_password(raw_password: str, stored_password: str) -> bool:
    candidate = str(raw_password or "")
    stored = str(stored_password or "")
    if not stored.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(stored, candidate)
    try:
        _, iterations_raw, salt_hex, digest_hex = stored.split("$", 3)
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    computed = hashlib.pbkdf2_hmac("sha256", candidate.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(expected, computed)


def password_needs_rehash(stored_password: str) -> bool:
    return not str(stored_password or "").startswith("pbkdf2_sha256$")


class TenantModel(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    owner_client_id = Column(Integer, nullable=True)
    assigned_client_ids = Column(Text, default="[]")
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
    trade_name = Column(String, nullable=True)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    state_code = Column(String, nullable=True)
    cnpj = Column(String, nullable=True)
    business_sector = Column(String, nullable=True)
    employee_count = Column(Integer, nullable=True)
    branch_count = Column(Integer, nullable=True)
    annual_revenue = Column(Integer, nullable=True)
    parent_client_id = Column(Integer, nullable=True)
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


class SurveyModel(Base):
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    service_name = Column(String, nullable=False, default="Diagnóstico Cultura de Segurança")
    stage_name = Column(String, nullable=False, default="Visita Técnica - Guiada")
    share_token = Column(String, nullable=True)
    legacy_form_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FormModel(Base):
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    target_client_id = Column(Integer, nullable=True)
    target_user_email = Column(String, nullable=True)


class QuestionModel(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    survey_id = Column(Integer, nullable=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    text = Column(Text, nullable=False)
    qtype = Column(String, default="fechada")
    dimension = Column(String, nullable=True)
    polarity = Column(String, default="positiva")
    weight = Column(Integer, default=1)
    order_index = Column(Integer, default=0)
    options_json = Column(Text, default="[]")


class ResponseModel(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    survey_id = Column(Integer, nullable=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    interview_id = Column(Integer, nullable=True)
    respondent_id = Column(Integer, nullable=True)
    client_id = Column(Integer, nullable=True)
    service_name = Column(String, nullable=True)
    response_token = Column(String, nullable=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    answer = Column(Text, nullable=False)
    score = Column(Integer, default=3)
    submitted_at = Column(DateTime, default=datetime.utcnow)


class InterviewSessionModel(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    survey_id = Column(Integer, nullable=True)
    project_id = Column(Integer, nullable=True)
    client_id = Column(Integer, nullable=True)
    interviewee_user_id = Column(Integer, nullable=True)
    target_area = Column(String, nullable=True)
    audience_group = Column(String, nullable=True)
    interview_date = Column(String, default="")
    interviewee_name = Column(String, nullable=False)
    interviewee_role = Column(String, nullable=True)
    consultant_name = Column(String, nullable=True)
    status = Column(String, default="em_andamento")
    notes = Column(Text, default="")
    total_score = Column(Integer, default=0)
    dimension_scores_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    project_type = Column(String, default="Diagnóstico de Cultura")
    service_name = Column(String, default="Diagnóstico Cultura de Segurança")
    client_id = Column(Integer, nullable=True)
    contracted_at = Column(String, default="")
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
    client_id = Column(Integer, nullable=True)
    service_name = Column(String, default="")
    dimension_names = Column(Text, default="")
    target_area = Column(String, default="")
    title = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    start_date = Column(String, default="")
    planned_due_date = Column(String, default="")
    due_date = Column(String, default="")
    due_date_change_count = Column(Integer, default=0)
    status = Column(String, default="a_fazer")
    expected_result = Column(Text, default="")
    actual_result = Column(Text, default="")
    attainment = Column(Integer, default=0)
    task_items_json = Column(Text, default="[]")
    completed_at = Column(String, default="")


class ActionTaskModel(Base):
    __tablename__ = "action_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    action_plan_id = Column(Integer, ForeignKey("action_plans.id"), nullable=False)
    title = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    start_date = Column(String, default="")
    planned_due_date = Column(String, default="")
    due_date = Column(String, default="")
    due_date_change_count = Column(Integer, default=0)
    expected_result = Column(Text, default="")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class AssistantDocumentModel(Base):
    __tablename__ = "assistant_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    knowledge_scope = Column(String, default="tenant")
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    resource_type = Column(String, default="politica")
    file_size = Column(Integer, default=0)
    uploaded_by = Column(String, default="sistema")
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class AssistantChunkModel(Base):
    __tablename__ = "assistant_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("assistant_documents.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    knowledge_scope = Column(String, default="tenant")
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    keyword_blob = Column(Text, default="")
    embedding_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)


class AssistantRecommendationModel(Base):
    __tablename__ = "assistant_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    title = Column(String, nullable=False)
    owner = Column(String, default="")
    due_date = Column(String, default="")
    expected_result = Column(Text, default="")
    status = Column(String, default="open")
    created_by = Column(String, default="sistema")
    created_at = Column(DateTime, default=datetime.utcnow)


class AssistantConversationModel(Base):
    __tablename__ = "assistant_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    user_email = Column(String, nullable=False)
    scope_mode = Column(String, default="tenant")
    title = Column(String, default="")
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AssistantMessageModel(Base):
    __tablename__ = "assistant_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("assistant_conversations.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    user_email = Column(String, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    model_name = Column(String, default="")
    prompt_mode = Column(String, default="")
    answer_mode = Column(String, default="")
    sources = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class CustomOptionModel(Base):
    __tablename__ = "custom_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    catalog_key = Column(String, nullable=False)
    option_value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


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
        session.add(TenantModel(id="default", name="SmartLab", slug="smartlab", limit_users=150))
        session.add(
            UserModel(
                name="Admin SmartLab",
                email="admin@smartlab.com",
                password=hash_password("admin123"),
                role="admin",
                account_scope="smartlab",
                tenant_id="default",
            )
        )
        session.commit()
    session.close()


def ensure_schema_updates() -> None:
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
        _safe_add_column(conn, "tenants", "assigned_client_ids", "ALTER TABLE tenants ADD COLUMN assigned_client_ids TEXT DEFAULT '[]';")
        _safe_add_column(conn, "clients", "trade_name", "ALTER TABLE clients ADD COLUMN trade_name VARCHAR;")
        _safe_add_column(conn, "clients", "phone", "ALTER TABLE clients ADD COLUMN phone VARCHAR;")
        _safe_add_column(conn, "clients", "address", "ALTER TABLE clients ADD COLUMN address VARCHAR;")
        _safe_add_column(conn, "clients", "state_code", "ALTER TABLE clients ADD COLUMN state_code VARCHAR;")
        _safe_add_column(conn, "clients", "cnpj", "ALTER TABLE clients ADD COLUMN cnpj VARCHAR;")
        _safe_add_column(conn, "clients", "business_sector", "ALTER TABLE clients ADD COLUMN business_sector VARCHAR;")
        _safe_add_column(conn, "clients", "employee_count", "ALTER TABLE clients ADD COLUMN employee_count INTEGER;")
        _safe_add_column(conn, "clients", "branch_count", "ALTER TABLE clients ADD COLUMN branch_count INTEGER;")
        _safe_add_column(conn, "clients", "annual_revenue", "ALTER TABLE clients ADD COLUMN annual_revenue INTEGER;")
        _safe_add_column(conn, "clients", "parent_client_id", "ALTER TABLE clients ADD COLUMN parent_client_id INTEGER;")
        _safe_add_column(conn, "forms", "target_client_id", "ALTER TABLE forms ADD COLUMN target_client_id INTEGER;")
        _safe_add_column(conn, "forms", "target_user_email", "ALTER TABLE forms ADD COLUMN target_user_email VARCHAR;")
        _safe_add_column(conn, "surveys", "service_name", "ALTER TABLE surveys ADD COLUMN service_name VARCHAR DEFAULT 'Diagnóstico Cultura de Segurança';")
        _safe_add_column(conn, "surveys", "stage_name", "ALTER TABLE surveys ADD COLUMN stage_name VARCHAR DEFAULT 'Visita Técnica - Guiada';")
        _safe_add_column(conn, "surveys", "share_token", "ALTER TABLE surveys ADD COLUMN share_token VARCHAR;")
        _safe_add_column(conn, "surveys", "legacy_form_id", "ALTER TABLE surveys ADD COLUMN legacy_form_id INTEGER;")
        _safe_add_column(conn, "questions", "dimension", "ALTER TABLE questions ADD COLUMN dimension VARCHAR;")
        _safe_add_column(conn, "questions", "polarity", "ALTER TABLE questions ADD COLUMN polarity VARCHAR DEFAULT 'positiva';")
        _safe_add_column(conn, "questions", "weight", "ALTER TABLE questions ADD COLUMN weight INTEGER DEFAULT 1;")
        _safe_add_column(conn, "questions", "survey_id", "ALTER TABLE questions ADD COLUMN survey_id INTEGER;")
        _safe_add_column(conn, "questions", "order_index", "ALTER TABLE questions ADD COLUMN order_index INTEGER DEFAULT 0;")
        _safe_add_column(conn, "responses", "survey_id", "ALTER TABLE responses ADD COLUMN survey_id INTEGER;")
        _safe_add_column(conn, "responses", "interview_id", "ALTER TABLE responses ADD COLUMN interview_id INTEGER;")
        _safe_add_column(conn, "responses", "respondent_id", "ALTER TABLE responses ADD COLUMN respondent_id INTEGER;")
        _safe_add_column(conn, "responses", "client_id", "ALTER TABLE responses ADD COLUMN client_id INTEGER;")
        _safe_add_column(conn, "responses", "service_name", "ALTER TABLE responses ADD COLUMN service_name VARCHAR;")
        _safe_add_column(conn, "responses", "response_token", "ALTER TABLE responses ADD COLUMN response_token VARCHAR;")
        _safe_add_column(conn, "responses", "submitted_at", "ALTER TABLE responses ADD COLUMN submitted_at DATETIME;")
        _safe_add_column(conn, "interview_sessions", "interviewee_user_id", "ALTER TABLE interview_sessions ADD COLUMN interviewee_user_id INTEGER;")
        _safe_add_column(conn, "interview_sessions", "survey_id", "ALTER TABLE interview_sessions ADD COLUMN survey_id INTEGER;")
        _safe_add_column(conn, "interview_sessions", "target_area", "ALTER TABLE interview_sessions ADD COLUMN target_area VARCHAR;")
        _safe_add_column(conn, "interview_sessions", "audience_group", "ALTER TABLE interview_sessions ADD COLUMN audience_group VARCHAR;")
        _safe_add_column(conn, "interview_sessions", "total_score", "ALTER TABLE interview_sessions ADD COLUMN total_score INTEGER DEFAULT 0;")
        _safe_add_column(conn, "interview_sessions", "dimension_scores_json", "ALTER TABLE interview_sessions ADD COLUMN dimension_scores_json TEXT DEFAULT '{}';")
        _safe_add_column(conn, "projects", "service_name", "ALTER TABLE projects ADD COLUMN service_name VARCHAR DEFAULT 'Diagnóstico Cultura de Segurança';")
        _safe_add_column(conn, "projects", "client_id", "ALTER TABLE projects ADD COLUMN client_id INTEGER;")
        _safe_add_column(conn, "projects", "contracted_at", "ALTER TABLE projects ADD COLUMN contracted_at VARCHAR DEFAULT '';")
        _safe_add_column(conn, "action_plans", "client_id", "ALTER TABLE action_plans ADD COLUMN client_id INTEGER;")
        _safe_add_column(conn, "action_plans", "service_name", "ALTER TABLE action_plans ADD COLUMN service_name VARCHAR DEFAULT '';")
        _safe_add_column(conn, "action_plans", "dimension_names", "ALTER TABLE action_plans ADD COLUMN dimension_names TEXT DEFAULT '';")
        _safe_add_column(conn, "action_plans", "target_area", "ALTER TABLE action_plans ADD COLUMN target_area VARCHAR DEFAULT '';")
        _safe_add_column(conn, "action_plans", "start_date", "ALTER TABLE action_plans ADD COLUMN start_date VARCHAR DEFAULT '';")
        _safe_add_column(conn, "action_plans", "planned_due_date", "ALTER TABLE action_plans ADD COLUMN planned_due_date VARCHAR DEFAULT '';")
        _safe_add_column(conn, "action_plans", "due_date_change_count", "ALTER TABLE action_plans ADD COLUMN due_date_change_count INTEGER DEFAULT 0;")
        _safe_add_column(conn, "action_plans", "task_items_json", "ALTER TABLE action_plans ADD COLUMN task_items_json TEXT DEFAULT '[]';")
        _safe_add_column(conn, "action_plans", "completed_at", "ALTER TABLE action_plans ADD COLUMN completed_at VARCHAR DEFAULT '';")
        _safe_add_column(conn, "action_tasks", "planned_due_date", "ALTER TABLE action_tasks ADD COLUMN planned_due_date VARCHAR DEFAULT '';")
        _safe_add_column(conn, "action_tasks", "due_date_change_count", "ALTER TABLE action_tasks ADD COLUMN due_date_change_count INTEGER DEFAULT 0;")
        _safe_add_column(conn, "action_tasks", "expected_result", "ALTER TABLE action_tasks ADD COLUMN expected_result TEXT DEFAULT '';")
        _safe_add_column(conn, "assistant_documents", "knowledge_scope", "ALTER TABLE assistant_documents ADD COLUMN knowledge_scope VARCHAR DEFAULT 'tenant';")
        conn.exec_driver_sql("UPDATE assistant_documents SET knowledge_scope = 'tenant' WHERE knowledge_scope IS NULL;")


Base.metadata.create_all(bind=engine)
ensure_schema_updates()
_seed()
