import reflex as rx

from ssecur1.db import SessionLocal, UserModel
from ssecur1.utils import loads_json as _loads_json


class SessionStateMixin(rx.State):
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
    selected_project_id: str = ""
    selected_interview_id: str = ""
    interview_answer_map: dict[str, str] = {}
    interview_score_map: dict[str, str] = {}
    delete_confirm_open: bool = False
    pending_delete_kind: str = ""
    pending_delete_target_id: str = ""
    pending_delete_label: str = ""

    @rx.var
    def theme_class(self) -> str:
        return "theme-dark app-theme" if self.dark_mode else "theme-light app-theme"

    @rx.var
    def theme_toggle_label(self) -> str:
        return "Modo Claro" if self.dark_mode else "Modo Escuro"

    @rx.var
    def theme_toggle_short_label(self) -> str:
        return "Claro" if self.dark_mode else "Escuro"

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

    def request_delete_confirmation(self, kind: str, target_id: str | int, label: str = ""):
        self.pending_delete_kind = kind
        self.pending_delete_target_id = str(target_id)
        self.pending_delete_label = label.strip() or "este registro"
        self.delete_confirm_open = True

    def cancel_delete_confirmation(self):
        self.delete_confirm_open = False
        self.pending_delete_kind = ""
        self.pending_delete_target_id = ""
        self.pending_delete_label = ""

    def confirm_delete_action(self):
        kind = self.pending_delete_kind
        raw_target = self.pending_delete_target_id
        method_map = {
            "question": "delete_question",
            "user": "delete_user",
            "client": "delete_client",
            "tenant": "delete_tenant",
            "role": "delete_role",
            "responsibility": "delete_responsibility",
            "form": "delete_form",
            "interview": "delete_interview_session",
            "workflow_box": "delete_workflow_box",
            "permission_box": "delete_permission_box",
        }
        method_name = method_map.get(kind, "")
        handler = getattr(self, method_name, None) if method_name else None
        self.cancel_delete_confirmation()
        if not callable(handler):
            self.toast_message = "Ação de exclusão não encontrada"
            self.toast_type = "error"
            return
        int_kinds = {"question", "user", "client", "role", "responsibility", "form", "workflow_box", "permission_box"}
        target = raw_target
        if kind in int_kinds:
            if not str(raw_target).isdigit():
                self.toast_message = "Identificador inválido para exclusão"
                self.toast_type = "error"
                return
            target = int(raw_target)
        handler(target)

    def hydrate_tenant_context(self):
        projects = getattr(self, "projects_data", [])
        self.selected_project_id = str(projects[0]["id"]) if projects else ""
        sync_project_assignments = getattr(self, "sync_project_assignments", None)
        if callable(sync_project_assignments):
            sync_project_assignments()

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
        self.selected_interview_id = ""
        self.interview_answer_map = {}
        self.interview_score_map = {}
        self.active_view = "dashboard"
