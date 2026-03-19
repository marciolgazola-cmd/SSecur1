import secrets
from typing import Any

import reflex as rx

from ssecur1.catalogs import (
    PERMISSION_RESOURCE_CATALOG,
    RESOURCE_PERMISSION_TOKENS,
    ROLE_PERMS,
    ROLE_PERMISSION_CATALOG,
    ROLE_TEMPLATE_ALIASES,
    ROLE_TEMPLATE_CATALOG,
    ROLE_TEMPLATE_OPTION_KEYS,
)
from ssecur1.db import (
    ClientModel,
    PermissionBoxModel,
    ResponsibilityModel,
    RoleModel,
    SessionLocal,
    UserModel,
    hash_password,
)
from ssecur1.utils import dom_token as _dom_token, loads_json as _loads_json


class AccessStateMixin:
    @rx.var
    def can_manage_clients(self) -> bool:
        return self._is_resource_allowed("Gerenciar Clientes")

    @rx.var
    def can_manage_users(self) -> bool:
        return self._is_resource_allowed("Gerenciar Usuarios")

    @rx.var
    def can_delete_users(self) -> bool:
        return self._is_resource_allowed("Gerenciar Usuarios")

    @rx.var
    def can_reset_user_password(self) -> bool:
        return self._is_resource_allowed("Gerenciar Usuarios")

    @rx.var
    def can_delete_clients(self) -> bool:
        return self._is_resource_allowed("Gerenciar Clientes")

    @rx.var
    def can_manage_tenants(self) -> bool:
        return self._is_resource_allowed("Gerenciar Tenants")

    @rx.var
    def can_delete_tenants(self) -> bool:
        return self._is_resource_allowed("Gerenciar Tenants")

    @rx.var
    def can_manage_roles(self) -> bool:
        return self._is_resource_allowed("Papeis e Responsabilidades")

    @rx.var
    def can_delete_roles(self) -> bool:
        return self._is_resource_allowed("Papeis e Responsabilidades")

    @rx.var
    def can_manage_global_role_templates(self) -> bool:
        return self.user_scope == "smartlab" and self.current_tenant == "default" and self.can_manage_roles

    @rx.var
    def can_manage_resps(self) -> bool:
        return self._is_resource_allowed("Papeis e Responsabilidades")

    @rx.var
    def can_delete_resps(self) -> bool:
        return self._is_resource_allowed("Papeis e Responsabilidades")

    @rx.var
    def can_manage_forms(self) -> bool:
        return self._is_resource_allowed("Gerenciar Formularios")

    @rx.var
    def can_delete_forms(self) -> bool:
        return self._is_resource_allowed("Gerenciar Formularios")

    @rx.var
    def can_operate_interviews(self) -> bool:
        return self._is_resource_allowed("Operar Entrevistas e Respostas")

    @rx.var
    def show_menu_clients(self) -> bool:
        if self.user_role == "sem_acesso":
            return False
        return self._is_resource_allowed("Clientes")

    @rx.var
    def show_menu_tenants(self) -> bool:
        if self.user_role == "sem_acesso":
            return False
        return self._is_resource_allowed("Tenants")

    @rx.var
    def show_menu_users(self) -> bool:
        if self.user_role == "sem_acesso":
            return False
        return self._is_resource_allowed("Usuarios")

    @rx.var
    def show_menu_permissions(self) -> bool:
        if self.user_role == "sem_acesso":
            return False
        return self._is_resource_allowed("Canvas de Permissoes") or self._is_resource_allowed("Template RBAC")

    @rx.var
    def show_menu_dashboard(self) -> bool:
        return self._is_resource_allowed("Dashboard Executivo") or self._is_resource_allowed("Dashboard Operacional")

    @rx.var
    def show_menu_projects(self) -> bool:
        if self.user_role == "sem_acesso":
            return False
        return self._is_resource_allowed("Projetos")

    @rx.var
    def show_menu_plans(self) -> bool:
        return self._is_resource_allowed("Plano de Acoes")

    @rx.var
    def show_menu_apis(self) -> bool:
        if self.user_role == "sem_acesso":
            return False
        return self._is_resource_allowed("APIs e Integrações")

    @rx.var
    def show_menu_roles(self) -> bool:
        return False

    @rx.var
    def show_menu_responsibilities(self) -> bool:
        return False

    @rx.var
    def show_menu_forms(self) -> bool:
        if self.user_role == "sem_acesso":
            return False
        return self._is_resource_allowed("Entrevistas e Respostas") or self._is_resource_allowed("Formularios")

    @rx.var
    def show_menu_ai(self) -> bool:
        if self.user_role == "sem_acesso":
            return False
        return self._is_resource_allowed("Especialista IA")

    @rx.var
    def show_menu_audit(self) -> bool:
        if self.user_role == "sem_acesso":
            return False
        return self._is_resource_allowed("Auditoria")

    @rx.var
    def has_platform_access(self) -> bool:
        return self.user_role != "sem_acesso"

    def _current_permission_set(self) -> set[str]:
        session = SessionLocal()
        row = None
        if self.user_role in ROLE_TEMPLATE_CATALOG:
            row = (
                session.query(RoleModel.permissions)
                .filter(RoleModel.tenant_id == "default", RoleModel.name == self.user_role)
                .first()
            )
        if not row:
            row = (
                session.query(RoleModel.permissions)
                .filter(RoleModel.tenant_id == self.current_tenant, RoleModel.name == self.user_role)
                .first()
            )
        session.close()
        if row:
            return {item for item in _loads_json(row[0], []) if item}
        return set(ROLE_PERMS.get(self.user_role, set()))

    def has_perm(self, perm: str) -> bool:
        return perm in self._current_permission_set()

    def _workspace_label(self, tenant_id: str, tenant_name: str = "") -> str:
        return tenant_id or tenant_name or "-"

    def _permission_overrides_for(self, user_email: str, tenant_id: str) -> dict[str, str]:
        email = (user_email or "").strip().lower()
        if not email or not tenant_id:
            return {}
        session = SessionLocal()
        rows = (
            session.query(PermissionBoxModel.resource, PermissionBoxModel.decision)
            .filter(PermissionBoxModel.tenant_id == tenant_id, PermissionBoxModel.user_email == email)
            .all()
        )
        session.close()
        return {str(resource): str(decision) for resource, decision in rows if resource and decision}

    def _resource_allowed_from_profile(
        self,
        resource: str,
        role_name: str,
        user_scope: str,
        tenant_id: str,
        perm_set: set[str],
    ) -> bool:
        scope = user_scope or "smartlab"
        is_default_workspace = tenant_id == "default"
        role = role_name or "sem_acesso"
        if role == "sem_acesso":
            return False
        if resource in {"Dashboard Executivo", "Dashboard Operacional", "Plano de Acoes", "Relatorio Executivo", "Relatorio Detalhado"}:
            return True
        if resource == "Clientes":
            return scope == "smartlab"
        if resource == "Gerenciar Clientes":
            return scope == "smartlab" and bool(RESOURCE_PERMISSION_TOKENS[resource] & perm_set)
        if resource == "Tenants":
            return scope == "smartlab"
        if resource == "Gerenciar Tenants":
            return scope == "smartlab" and bool(RESOURCE_PERMISSION_TOKENS[resource] & perm_set)
        if resource == "Usuarios":
            return scope == "smartlab" or role == "cliente_admin" or bool(RESOURCE_PERMISSION_TOKENS["Gerenciar Usuarios"] & perm_set)
        if resource == "Gerenciar Usuarios":
            return bool(RESOURCE_PERMISSION_TOKENS[resource] & perm_set)
        if resource == "Projetos":
            return scope == "smartlab" and is_default_workspace
        if resource == "Gerenciar Projetos":
            return scope == "smartlab" and is_default_workspace
        if resource == "Formularios":
            return scope == "smartlab"
        if resource == "Gerenciar Formularios":
            return bool(RESOURCE_PERMISSION_TOKENS[resource] & perm_set)
        if resource == "Entrevistas e Respostas":
            return role != "sem_acesso"
        if resource == "Operar Entrevistas e Respostas":
            return scope == "smartlab" and is_default_workspace
        if resource == "Template RBAC":
            return scope == "smartlab" or role == "cliente_admin" or bool(RESOURCE_PERMISSION_TOKENS["Papeis e Responsabilidades"] & perm_set)
        if resource == "Canvas de Permissoes":
            return scope == "smartlab" or role == "cliente_admin" or bool(RESOURCE_PERMISSION_TOKENS[resource] & perm_set)
        if resource == "Papeis e Responsabilidades":
            return scope == "smartlab" or role == "cliente_admin" or bool(RESOURCE_PERMISSION_TOKENS[resource] & perm_set)
        if resource == "APIs e Integrações":
            return scope == "smartlab" and is_default_workspace
        if resource == "Auditoria":
            return scope == "smartlab"
        if resource in {"Especialista IA", "Operar Especialista IA"}:
            return scope == "smartlab"
        return False

    def _role_permission_set_for_user(self, role_name: str, tenant_id: str) -> set[str]:
        if not role_name:
            return set()
        session = SessionLocal()
        row = None
        if role_name in ROLE_TEMPLATE_CATALOG:
            row = (
                session.query(RoleModel.permissions)
                .filter(RoleModel.tenant_id == "default", RoleModel.name == role_name)
                .first()
            )
        if not row:
            row = (
                session.query(RoleModel.permissions)
                .filter(RoleModel.tenant_id == tenant_id, RoleModel.name == role_name)
                .first()
            )
        session.close()
        if row:
            return {item for item in _loads_json(row[0], []) if item}
        return set(ROLE_PERMS.get(role_name, set()))

    def _effective_permission_decisions_for(
        self,
        user_email: str,
        role_name: str,
        user_scope: str,
        tenant_id: str,
    ) -> dict[str, str]:
        perm_set = self._role_permission_set_for_user(role_name, tenant_id)
        decisions = {
            item["resource"]: (
                "permitido"
                if self._resource_allowed_from_profile(item["resource"], role_name, user_scope, tenant_id, perm_set)
                else "negado"
            )
            for item in PERMISSION_RESOURCE_CATALOG
        }
        decisions.update(self._permission_overrides_for(user_email, tenant_id))
        return decisions

    def _current_user_permission_decisions(self) -> dict[str, str]:
        return self._effective_permission_decisions_for(
            self.login_email.strip().lower(),
            self.user_role,
            self.user_scope,
            self.current_tenant,
        )

    def _is_resource_allowed(self, resource: str) -> bool:
        return self._current_user_permission_decisions().get(resource, "negado") == "permitido"

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
                "role_label": "-",
                "scope": "-",
                "scope_label": "-",
                "tenant": "-",
                "client": "-",
            }
        session = SessionLocal()
        user = (
            session.query(UserModel)
            .filter(UserModel.tenant_id == self.current_tenant, UserModel.email == self.perm_user_email.strip().lower())
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
                "role_label": "-",
                "scope": "-",
                "scope_label": "-",
                "tenant": "-",
                "client": "-",
            }
        role_name = user.role or "viewer"
        role_label = role_name
        if role_name in ROLE_TEMPLATE_CATALOG:
            role_label = str(ROLE_TEMPLATE_CATALOG[role_name]["label"])
        else:
            session = SessionLocal()
            role = (
                session.query(RoleModel.name)
                .filter(RoleModel.tenant_id == self.current_tenant, RoleModel.name == role_name)
                .first()
            )
            session.close()
            if role and role[0]:
                role_label = str(role[0])
        return {
            "name": user.name,
            "email": user.email,
            "role": role_name,
            "role_label": role_label,
            "scope": user.account_scope or "smartlab",
            "scope_label": "SmartLab" if (user.account_scope or "smartlab") == "smartlab" else "Cliente",
            "tenant": user.tenant_id,
            "client": client_name,
        }

    @rx.var(cache=False)
    def selected_access_responsibilities(self) -> list[str]:
        if not self.has_valid_permission_principal:
            return []
        session = SessionLocal()
        role_name = (self.selected_access_principal.get("role", "") or "").strip()
        role = (
            session.query(RoleModel)
            .filter(RoleModel.tenant_id == self.current_tenant, RoleModel.name == role_name)
            .first()
        )
        if not role:
            session.close()
            return []
        rows = (
            session.query(ResponsibilityModel.description)
            .filter(ResponsibilityModel.tenant_id == self.current_tenant, ResponsibilityModel.role_id == role.id)
            .order_by(ResponsibilityModel.id.asc())
            .all()
        )
        session.close()
        return [str(row[0]) for row in rows if row and row[0]]

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
        responsibility_rows = (
            session.query(ResponsibilityModel.role_id, ResponsibilityModel.description)
            .filter(ResponsibilityModel.tenant_id == self.current_tenant)
            .order_by(ResponsibilityModel.id.asc())
            .all()
        )
        responsibility_map: dict[int, list[str]] = {}
        for role_id, description in responsibility_rows:
            if role_id is None or not description:
                continue
            responsibility_map.setdefault(int(role_id), []).append(str(description))
        data = [
            {
                "id": r.id,
                "name": r.name,
                "permissions": _loads_json(r.permissions, []),
                "permissions_str": ", ".join(_loads_json(r.permissions, [])),
                "responsibilities": responsibility_map.get(int(r.id), []),
                "responsibilities_str": "\n".join(responsibility_map.get(int(r.id), [])) or "-",
                "tenant_id": r.tenant_id,
            }
            for r in rows
        ]
        session.close()
        return data

    @rx.var
    def role_id_options(self) -> list[str]:
        return [str(r["id"]) for r in self.roles_data]

    @rx.var
    def role_permission_module_options(self) -> list[str]:
        modules = ["Todos"]
        modules.extend(sorted({item["module"] for item in ROLE_PERMISSION_CATALOG}))
        return modules

    @rx.var(cache=False)
    def selected_role_permissions(self) -> list[str]:
        return [item.strip() for item in self.new_role_permissions.split(",") if item.strip()]

    @rx.var(cache=False)
    def selected_role_permissions_summary(self) -> str:
        items = self.selected_role_permissions
        if not items:
            return "Nenhuma permissao escolhida ainda"
        return ", ".join(items)

    @rx.var(cache=False)
    def selected_role_permission_details(self) -> list[dict[str, str]]:
        catalog_map = {item["token"]: item for item in ROLE_PERMISSION_CATALOG}
        details: list[dict[str, str]] = []
        for token in self.selected_role_permissions:
            item = catalog_map.get(token, {})
            details.append(
                {
                    "module": str(item.get("module", "Customizado")),
                    "token": token,
                    "label": str(item.get("label", token)),
                    "description": str(item.get("description", "Permissao adicionada manualmente ao papel.")),
                }
            )
        return details

    @rx.var(cache=False)
    def available_role_permission_choices(self) -> list[str]:
        items = ROLE_PERMISSION_CATALOG
        if self.role_permission_module_filter != "Todos":
            items = [item for item in items if item["module"] == self.role_permission_module_filter]
        return [f'{item["token"]} - {item["label"]}' for item in items]

    @rx.var(cache=False)
    def selected_role_permission_catalog(self) -> list[dict[str, str]]:
        items = ROLE_PERMISSION_CATALOG
        if self.role_permission_module_filter != "Todos":
            items = [item for item in items if item["module"] == self.role_permission_module_filter]
        selected = set(self.selected_role_permissions)
        return [
            {
                "module": item["module"],
                "token": item["token"],
                "label": item["label"],
                "description": item["description"],
                "selected": "sim" if item["token"] in selected else "nao",
            }
            for item in items
        ]

    @rx.var(cache=False)
    def available_role_permissions_data(self) -> list[dict[str, str]]:
        return [item for item in self.selected_role_permission_catalog if item["selected"] != "sim"]

    @rx.var(cache=False)
    def chosen_role_permissions_data(self) -> list[dict[str, str]]:
        return [item for item in self.selected_role_permission_catalog if item["selected"] == "sim"]

    @rx.var(cache=False)
    def permission_boxes_data(self) -> list[dict[str, Any]]:
        if not self.perm_user_email.strip():
            return []
        session = SessionLocal()
        rows = (
            session.query(PermissionBoxModel)
            .filter(
                PermissionBoxModel.tenant_id == self.current_tenant,
                PermissionBoxModel.user_email == self.perm_user_email.strip().lower(),
            )
            .order_by(PermissionBoxModel.id.desc())
            .all()
        )
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
        return [*ROLE_TEMPLATE_OPTION_KEYS, *self.custom_role_template_keys]

    @rx.var(cache=False)
    def custom_role_templates_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        rows = (
            session.query(RoleModel)
            .filter(RoleModel.tenant_id == self.current_tenant)
            .order_by(RoleModel.name.asc())
            .all()
        )
        responsibility_rows = (
            session.query(ResponsibilityModel.role_id, ResponsibilityModel.description)
            .filter(ResponsibilityModel.tenant_id == self.current_tenant)
            .order_by(ResponsibilityModel.id.asc())
            .all()
        )
        session.close()
        responsibility_map: dict[int, list[str]] = {}
        for role_id, description in responsibility_rows:
            if role_id is None or not description:
                continue
            responsibility_map.setdefault(int(role_id), []).append(str(description))
        return [
            {
                "id": row.id,
                "key": row.name,
                "label": row.name,
                "scope": "smartlab" if self.current_tenant == "default" else "cliente",
                "workspace_label": self.current_tenant,
                "description": "Papel local criado no tenant atual para operacao e governanca daquele workspace.",
                "permissions": _loads_json(row.permissions, []),
                "permissions_str": ", ".join(_loads_json(row.permissions, [])) or "Sem permissoes configuradas",
                "responsibilities": responsibility_map.get(int(row.id), []),
                "responsibilities_str": "\n".join(responsibility_map.get(int(row.id), [])) or "-",
            }
            for row in rows
            if (row.name or "").strip() and row.name not in ROLE_TEMPLATE_OPTION_KEYS
        ]

    @rx.var(cache=False)
    def custom_role_template_keys(self) -> list[str]:
        return [item["key"] for item in self.custom_role_templates_data]

    @rx.var
    def role_template_display_options(self) -> list[str]:
        return [
            f'{item["label"]} - {item["context_label"]} - {item["workspace_label"]}'
            for item in self.role_templates_data
        ]

    @rx.var
    def selected_role_template_option(self) -> str:
        key = self.selected_role_template_key
        row = next((item for item in self.role_templates_data if item["key"] == key), None)
        if row:
            return f'{row["label"]} - {row["context_label"]} - {row["workspace_label"]}'
        if key in ROLE_TEMPLATE_CATALOG:
            template = ROLE_TEMPLATE_CATALOG.get(key, ROLE_TEMPLATE_CATALOG["smartlab_viewer"])
            context_label = "SmartLab" if template["scope"] == "smartlab" else "Cliente"
            return f'{template["label"]} - {context_label} - default'
        return key

    @rx.var(cache=False)
    def role_templates_data(self) -> list[dict[str, Any]]:
        session = SessionLocal()
        base_rows = (
            session.query(RoleModel)
            .filter(RoleModel.tenant_id == "default", RoleModel.name.in_(ROLE_TEMPLATE_OPTION_KEYS))
            .all()
        )
        responsibility_rows = (
            session.query(ResponsibilityModel.role_id, ResponsibilityModel.description)
            .filter(ResponsibilityModel.tenant_id == "default")
            .order_by(ResponsibilityModel.id.asc())
            .all()
        )
        session.close()
        base_row_map = {str(row.name): row for row in base_rows if (row.name or "").strip()}
        responsibility_map: dict[int, list[str]] = {}
        for role_id, description in responsibility_rows:
            if role_id is None or not description:
                continue
            responsibility_map.setdefault(int(role_id), []).append(str(description))
        base_data = []
        for key in ROLE_TEMPLATE_OPTION_KEYS:
            value = ROLE_TEMPLATE_CATALOG[key]
            row = base_row_map.get(key)
            permissions = _loads_json(row.permissions, []) if row else value["permissions"]
            responsibilities = responsibility_map.get(int(row.id), []) if row else []
            base_data.append(
                {
                    "id": row.id if row else "",
                    "key": key,
                    "label": value["label"],
                    "scope": value["scope"],
                    "context_label": "SmartLab" if value["scope"] == "smartlab" else "Cliente",
                    "workspace_label": "default",
                    "reach_label": "Plataforma",
                    "description": value["description"],
                    "permissions": permissions,
                    "permissions_str": ", ".join(permissions) if permissions else "Somente leitura",
                    "responsibilities": responsibilities,
                    "responsibilities_str": "\n".join(responsibilities) or "-",
                    "origin": "global",
                    "origin_label": "default",
                    "governance": "Governado pela SmartLab no workspace central da plataforma.",
                    "can_edit": self.can_manage_global_role_templates,
                    "can_delete": False,
                }
            )
        custom_data = [
            {
                **item,
                "origin": "tenant",
                "context_label": "SmartLab" if item.get("scope") == "smartlab" else "Cliente",
                "workspace_label": self.current_tenant,
                "reach_label": "Tenant",
                "origin_label": self.current_tenant,
                "governance": "Governado no workspace atual, sempre dentro das permissões liberadas pela SmartLab.",
                "can_edit": self.can_manage_roles,
                "can_delete": self.can_delete_roles,
            }
            for item in self.custom_role_templates_data
        ]
        return [*base_data, *custom_data]

    @rx.var(cache=False)
    def selected_role_template_key(self) -> str:
        default_key = "cliente_viewer" if self.selected_access_principal["scope"] == "cliente" else "smartlab_viewer"
        if self.perm_selected_role_template in ROLE_TEMPLATE_OPTION_KEYS:
            return self.perm_selected_role_template
        if self.perm_selected_role_template in self.custom_role_template_keys:
            return self.perm_selected_role_template
        if self.perm_selected_role_template in ROLE_TEMPLATE_ALIASES:
            return ROLE_TEMPLATE_ALIASES[self.perm_selected_role_template]
        if not self.has_valid_permission_principal:
            return default_key
        principal_role = self.selected_access_principal["role"]
        if principal_role in ROLE_TEMPLATE_OPTION_KEYS:
            return principal_role
        if principal_role in self.custom_role_template_keys:
            return principal_role
        if principal_role in ROLE_TEMPLATE_ALIASES:
            return ROLE_TEMPLATE_ALIASES[principal_role]
        return default_key

    @rx.var(cache=False)
    def selected_role_template_data(self) -> dict[str, Any]:
        if not self.has_valid_permission_principal:
            return {
                "label": "Nenhum usuario selecionado",
                "scope": "-",
                "context_label": "-",
                "reach_label": "-",
                "origin_label": "-",
                "workspace_label": "-",
                "description": "Selecione uma conta valida deste tenant para visualizar o template RBAC.",
                "permissions_str": "-",
                "governance": "-",
            }
        template_row = next((item for item in self.role_templates_data if item["key"] == self.selected_role_template_key), None)
        if template_row:
            return {
                "label": template_row["label"],
                "scope": template_row["scope"],
                "context_label": template_row.get("context_label", template_row["scope"]),
                "reach_label": template_row.get("reach_label", "Tenant"),
                "origin_label": template_row.get("origin_label", "-"),
                "workspace_label": template_row.get("workspace_label", template_row.get("origin_label", "-")),
                "description": template_row["description"],
                "permissions_str": template_row["permissions_str"],
                "governance": template_row.get("governance", "-"),
            }
        template = ROLE_TEMPLATE_CATALOG.get(self.selected_role_template_key, ROLE_TEMPLATE_CATALOG["smartlab_viewer"])
        return {
            "label": template["label"],
            "scope": template["scope"],
            "context_label": "SmartLab" if template["scope"] == "smartlab" else "Cliente",
            "reach_label": "Plataforma",
            "origin_label": "default",
            "workspace_label": "default",
            "description": template["description"],
            "permissions_str": ", ".join(template["permissions"]) if template["permissions"] else "Somente leitura",
            "governance": "Governado pela SmartLab no workspace central da plataforma.",
        }

    @rx.var(cache=False)
    def permission_decision_map(self) -> dict[str, str]:
        email = (self.perm_user_email or "").strip().lower()
        if not email or not self.has_valid_permission_principal:
            return {}
        return self._effective_permission_decisions_for(
            email,
            self.selected_role_template_key,
            str(self.selected_role_template_data.get("scope", "")),
            self.current_tenant,
        )

    @rx.var(cache=False)
    def permission_canvas_available(self) -> list[dict[str, str]]:
        decisions = self.permission_decision_map
        return [item for item in self.permission_catalog if decisions.get(item["resource"], "") == ""]

    @rx.var(cache=False)
    def permission_canvas_allowed(self) -> list[dict[str, str]]:
        decisions = self.permission_decision_map
        return [item for item in self.permission_catalog if decisions.get(item["resource"], "") == "permitido"]

    @rx.var(cache=False)
    def permission_canvas_denied(self) -> list[dict[str, str]]:
        decisions = self.permission_decision_map
        return [item for item in self.permission_catalog if decisions.get(item["resource"], "") == "negado"]

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

    def set_perm_user_email(self, value: str):
        self.perm_user_email = value
        self.last_reset_user_password = ""
        session = SessionLocal()
        user = (
            session.query(UserModel)
            .filter(UserModel.tenant_id == self.current_tenant, UserModel.email == value.strip().lower())
            .first()
        )
        custom_role_names = {
            row[0]
            for row in session.query(RoleModel.name)
            .filter(RoleModel.tenant_id == self.current_tenant)
            .all()
            if row[0]
        }
        session.close()
        if user and ((user.role or "") in ROLE_TEMPLATE_CATALOG or (user.role or "") in custom_role_names):
            self.perm_selected_role_template = user.role or "smartlab_viewer"
        else:
            self.perm_selected_role_template = "smartlab_viewer"
        self.perm_selected_module = "Todos"

    def set_perm_selected_module(self, value: str):
        self.perm_selected_module = value

    def set_permissions_tab(self, value: str):
        self.permissions_tab = value or "governanca"

    def set_perm_selected_role_template(self, value: str):
        if not value:
            self.perm_selected_role_template = "smartlab_viewer"
            return
        selected = next(
            (
                item for item in self.role_templates_data
                if f'{item["label"]} - {item["context_label"]} - {item["workspace_label"]}' == value
            ),
            None,
        )
        if selected:
            self.perm_selected_role_template = str(selected["key"])
            return
        self.perm_selected_role_template = value.split(" - ", 1)[0].strip()

    def apply_selected_role_template(self):
        if not self.perm_user_email.strip():
            self.toast_message = "Selecione um usuario para liberar acesso"
            self.toast_type = "error"
            return
        role_key = self.selected_role_template_key
        session = SessionLocal()
        user = (
            session.query(UserModel)
            .filter(UserModel.tenant_id == self.current_tenant, UserModel.email == self.perm_user_email.strip().lower())
            .first()
        )
        if not user:
            session.close()
            self.toast_message = "Usuario nao encontrado para liberacao"
            self.toast_type = "error"
            return
        template = ROLE_TEMPLATE_CATALOG.get(role_key)
        if template:
            user_scope = user.account_scope or "smartlab"
            if template["scope"] != user_scope:
                session.close()
                self.toast_message = "O template selecionado nao corresponde ao escopo da conta"
                self.toast_type = "error"
                return
        else:
            custom_role = (
                session.query(RoleModel)
                .filter(RoleModel.tenant_id == self.current_tenant, RoleModel.name == role_key)
                .first()
            )
            if not custom_role:
                session.close()
                self.toast_message = "Template RBAC invalido"
                self.toast_type = "error"
                return
        user.role = role_key
        session.commit()
        session.close()
        label = template["label"] if template else role_key
        self.toast_message = f"Acesso base liberado com template {label}"
        self.toast_type = "success"

    def reset_selected_user_password(self):
        if not self.can_reset_user_password:
            self.toast_message = "Sem permissao para resetar senha"
            self.toast_type = "error"
            return
        email = self.perm_user_email.strip().lower()
        if not email:
            self.toast_message = "Selecione um usuario antes de resetar a senha"
            self.toast_type = "error"
            return
        session = SessionLocal()
        user = (
            session.query(UserModel)
            .filter(UserModel.tenant_id == self.current_tenant, UserModel.email == email)
            .first()
        )
        if not user:
            session.close()
            self.toast_message = "Usuario nao encontrado para reset de senha"
            self.toast_type = "error"
            return
        temp_password = secrets.token_urlsafe(8)[:12]
        user.password = hash_password(temp_password)
        user.must_change_password = 1
        session.commit()
        session.close()
        self.last_reset_user_password = temp_password
        self._append_audit_entry(
            "user.password_reset",
            f"Senha temporaria redefinida para {email}",
            "security",
            {"target_user": email},
        )
        self.toast_message = "Senha temporaria gerada. Compartilhe com o usuario e exija troca no proximo login."
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
            .filter(PermissionBoxModel.id == permission_id, PermissionBoxModel.tenant_id == self.current_tenant)
            .first()
        )
        if row:
            session.delete(row)
            session.commit()
            self.toast_message = "Regra removida"
            self.toast_type = "success"
        session.close()
