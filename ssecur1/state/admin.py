from __future__ import annotations

import json

from ssecur1.db import (
    ClientModel,
    ResponsibilityModel,
    RoleModel,
    SessionLocal,
    TenantModel,
    UserModel,
    hash_password,
)
from ssecur1.utils import (
    build_client_children_map as _build_client_children_map,
    collect_descendant_client_ids as _collect_descendant_client_ids,
    format_brl_amount as _format_brl_amount,
    loads_json as _loads_json,
    now_brasilia as _now_brasilia,
    parse_brl_amount as _parse_brl_amount,
    parse_int as _parse_int,
    slugify as _slugify,
)


ROLE_TEMPLATE_OPTION_KEYS = [
    "smartlab_admin",
    "smartlab_viewer",
    "cliente_admin",
    "cliente_viewer",
]


class AdminStateMixin:
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
        self.new_user_tenant_id = value.strip()

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
        self.new_user_role = "sem_acesso"
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
        self.editing_role_template_key = ""
        self.editing_role_template_origin = ""
        self.new_role_name = ""
        self.new_role_permissions = ""
        self.new_role_responsibilities = ""
        self.role_permission_module_filter = "Todos"
        self.role_permission_choice = "create:users"

    def reset_resp_form(self):
        self.editing_resp_id = ""
        self.new_resp_role_id = ""
        self.new_resp_desc = ""

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
        self.new_user_role = row.role or "sem_acesso"
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
        if not row:
            session.close()
            self.toast_message = "Papel nao encontrado"
            self.toast_type = "error"
            return
        responsibility_rows = (
            session.query(ResponsibilityModel.description)
            .filter(ResponsibilityModel.tenant_id == self.current_tenant, ResponsibilityModel.role_id == row.id)
            .order_by(ResponsibilityModel.id.asc())
            .all()
        )
        session.close()
        self.editing_role_id = str(row.id)
        self.new_role_name = row.name or ""
        self.new_role_permissions = ", ".join(_loads_json(row.permissions, []))
        self.new_role_responsibilities = "\n".join(
            str(item[0]).strip() for item in responsibility_rows if item and str(item[0]).strip()
        )
        self.role_permission_module_filter = "Todos"
        available = self.available_role_permission_choices
        self.role_permission_choice = available[0] if available else ""

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

    def set_new_role_responsibilities(self, value: str):
        self.new_role_responsibilities = value

    def set_role_permission_module_filter(self, value: str):
        self.role_permission_module_filter = value
        available = self.available_role_permission_choices
        self.role_permission_choice = available[0] if available else ""

    def set_role_permission_choice(self, value: str):
        self.role_permission_choice = value

    def add_role_permission_choice(self):
        token = self.role_permission_choice.split(" - ", 1)[0].strip() if self.role_permission_choice else ""
        self.add_role_permission_token(token)

    def add_role_permission_token(self, token: str):
        if not token:
            self.toast_message = "Selecione uma permissao para adicionar ao papel"
            self.toast_type = "error"
            return
        permissions = list(self.selected_role_permissions)
        if token not in permissions:
            permissions.append(token)
        self.new_role_permissions = ",".join(permissions)
        self.toast_message = "Permissao adicionada ao papel"
        self.toast_type = "success"

    def remove_role_permission_choice(self, token: str):
        permissions = [item for item in self.selected_role_permissions if item != token]
        self.new_role_permissions = ",".join(permissions)
        self.toast_message = "Permissao removida do papel"
        self.toast_type = "success"

    def set_new_resp_role_id(self, value: str):
        self.new_resp_role_id = value

    def set_new_resp_desc(self, value: str):
        self.new_resp_desc = value

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

    def create_client(self):
        if not self.can_manage_clients:
            self.toast_message = "Permissão insuficiente"
            self.toast_type = "error"
            return
        client_name = self.new_client_name.strip()
        trade_name = self.new_client_trade_name.strip()
        if not client_name or not self.new_client_email.strip():
            self.toast_message = "Nome e e-mail são obrigatórios"
            self.toast_type = "error"
            return
        business_sector = self.new_client_custom_business_sector.strip() if self.new_client_business_sector == "Outro" else self.new_client_business_sector.strip()
        if not business_sector:
            self.toast_message = "Informe o ramo de atividade"
            self.toast_type = "error"
            return
        session = SessionLocal()
        editing_id = int(self.editing_client_id) if self.editing_client_id.isdigit() else None
        if editing_id is not None:
            parent_client_id = int(self.new_client_parent_id) if self.new_client_parent_id.isdigit() else None
            if parent_client_id == editing_id:
                session.close()
                self.toast_message = "Um cliente não pode ser pai dele mesmo"
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
            descendants = _collect_descendant_client_ids(_build_client_children_map(session.query(ClientModel).all()), editing_id)
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
        parent_client_id = int(self.new_client_parent_id) if self.new_client_parent_id.isdigit() else None
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
        profession = self.new_user_custom_profession.strip() if self.new_user_profession == "Outro" else self.new_user_profession.strip()
        if not profession:
            self.toast_message = "Informe a profissao do usuario"
            self.toast_type = "error"
            session.close()
            return
        department = self.new_user_custom_department.strip() if self.new_user_department == "Outro" else self.new_user_department.strip()
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
                user.password = hash_password(self.new_user_password)
                user.must_change_password = 1 if self.new_user_scope == "cliente" else 0
            if not user.role:
                user.role = "sem_acesso"
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
                    password=hash_password(self.new_user_password),
                    role="sem_acesso",
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
        self.toast_message = "Usuario atualizado" if editing_id is not None else "Usuario criado sem acesso. Libere o template e as permissoes na UI Permissoes."
        self.toast_type = "success"

    def delete_user(self, user_id: int):
        if not self.can_delete_users:
            self.toast_message = "Sem permissao para remover usuarios"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = session.query(UserModel).filter(UserModel.id == user_id, UserModel.tenant_id == self.current_tenant).first()
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
        row = session.query(ClientModel).filter(ClientModel.id == client_id, ClientModel.tenant_id == self.current_tenant).first()
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
            slug_exists = session.query(TenantModel).filter(TenantModel.slug == tenant_slug, TenantModel.id != editing_id).first()
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
        perms = sorted({p.strip() for p in self.new_role_permissions.split(",") if p.strip()})
        responsibilities = [line.strip() for line in self.new_role_responsibilities.splitlines() if line.strip()]
        if not self.new_role_name.strip():
            self.toast_message = "Informe o nome do papel"
            self.toast_type = "error"
            return
        if not perms:
            self.toast_message = "Selecione pelo menos uma permissao para o papel"
            self.toast_type = "error"
            return
        session = SessionLocal()
        role_name = self.new_role_name.strip()
        if role_name in ROLE_TEMPLATE_OPTION_KEYS:
            session.close()
            self.toast_message = "Esse nome e reservado para templates globais da SmartLab"
            self.toast_type = "error"
            return
        if self.editing_role_id.isdigit():
            row = session.query(RoleModel).filter(RoleModel.id == int(self.editing_role_id), RoleModel.tenant_id == self.current_tenant).first()
            if not row:
                session.close()
                self.toast_message = "Papel nao encontrado para edicao"
                self.toast_type = "error"
                return
            duplicate = (
                session.query(RoleModel.id)
                .filter(RoleModel.tenant_id == self.current_tenant, RoleModel.name == role_name, RoleModel.id != int(self.editing_role_id))
                .first()
            )
            if duplicate:
                session.close()
                self.toast_message = "Ja existe um papel com esse nome neste tenant"
                self.toast_type = "error"
                return
            row.name = role_name
            row.permissions = json.dumps(perms)
            role_id = int(row.id)
        else:
            duplicate = session.query(RoleModel.id).filter(RoleModel.tenant_id == self.current_tenant, RoleModel.name == role_name).first()
            if duplicate:
                session.close()
                self.toast_message = "Ja existe um papel com esse nome neste tenant"
                self.toast_type = "error"
                return
            row = RoleModel(tenant_id=self.current_tenant, name=role_name, permissions=json.dumps(perms))
            session.add(row)
            session.flush()
            role_id = int(row.id)
        session.query(ResponsibilityModel).filter(
            ResponsibilityModel.tenant_id == self.current_tenant,
            ResponsibilityModel.role_id == role_id,
        ).delete()
        for description in responsibilities:
            session.add(
                ResponsibilityModel(tenant_id=self.current_tenant, role_id=role_id, description=description)
            )
        session.commit()
        session.close()
        was_editing = self.editing_role_id != ""
        self.reset_role_form()
        self.toast_message = "Papel atualizado" if was_editing else "Papel criado"
        self.toast_type = "success"

    def delete_role(self, role_id: int):
        if not self.can_delete_roles:
            self.toast_message = "Sem permissão para deletar papéis"
            self.toast_type = "error"
            return
        session = SessionLocal()
        row = session.query(RoleModel).filter(RoleModel.id == role_id, RoleModel.tenant_id == self.current_tenant).first()
        if row and row.name in ROLE_TEMPLATE_OPTION_KEYS:
            session.close()
            self.toast_message = "Templates globais da SmartLab nao podem ser excluidos por esta acao"
            self.toast_type = "error"
            return
        if row:
            session.query(ResponsibilityModel).filter(
                ResponsibilityModel.tenant_id == self.current_tenant,
                ResponsibilityModel.role_id == role_id,
            ).delete()
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
        if not self.can_delete_resps:
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
