import json
from datetime import datetime

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
                password="admin123",
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
        _safe_add_column(conn, "interview_sessions", "total_score", "ALTER TABLE interview_sessions ADD COLUMN total_score INTEGER DEFAULT 0;")
        _safe_add_column(conn, "interview_sessions", "dimension_scores_json", "ALTER TABLE interview_sessions ADD COLUMN dimension_scores_json TEXT DEFAULT '{}';")


Base.metadata.create_all(bind=engine)
ensure_schema_updates()
_seed()
