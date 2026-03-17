from typing import Any

import reflex as rx


def build_tenants_view(State, CARD_STYLE: dict[str, Any], field_block, table_text_cell, data_table) -> rx.Component:
    tenant_table_headers = [
        "ID",
        "Workspace",
        "Slug",
        "Cliente proprietário",
        "Escopo Cliente",
        "Criado em",
        "Limite",
        "Ações",
    ]

    def tenant_table_cell(*children: rx.Component) -> rx.Component:
        return rx.vstack(
            *children,
            spacing="1",
            align="center",
            justify="center",
            text_align="center",
            width="100%",
            min_height="100%",
        )

    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Tenants", color="var(--text-primary)", size="5"),
                        rx.text(
                            "Cada workspace opera com contexto próprio. Documentos, respostas e análises do Especialista IA devem permanecer isolados por tenant.",
                            color="var(--text-muted)",
                            font_size="0.88rem",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.badge("Admin avancado", color_scheme="purple"),
                    width="100%",
                    align="center",
                ),
                rx.grid(
                    field_block(
                        "Nome Tenant",
                        rx.input(
                            placeholder="Nome Tenant",
                            value=State.new_tenant_name,
                            on_change=State.set_new_tenant_name,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Slug do workspace",
                        rx.input(
                            placeholder="ex: 4zoom, smartlab-interno",
                            value=State.new_tenant_slug,
                            on_change=State.set_new_tenant_slug,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        "Identificador único do workspace. Use letras minúsculas, números e hífen, sem espaços ou acentos.",
                    ),
                    field_block(
                        "Limite Usuários",
                        rx.input(
                            placeholder="Total Usuarios",
                            value=State.new_tenant_limit,
                            on_change=State.set_new_tenant_limit,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Clientes do tenant",
                        rx.box(
                            rx.vstack(
                                rx.button(
                                    rx.hstack(
                                        rx.text(State.selected_tenant_assigned_clients_summary, color="var(--text-primary)"),
                                        rx.spacer(),
                                        rx.icon(
                                            tag=rx.cond(State.new_tenant_assigned_clients_open, "chevron_up", "chevron_down"),
                                            size=16,
                                            color="var(--text-muted)",
                                        ),
                                        width="100%",
                                        align="center",
                                    ),
                                    on_click=State.toggle_new_tenant_assigned_clients_open,
                                    variant="ghost",
                                    border="1px solid var(--input-border)",
                                    bg="var(--input-bg)",
                                    width="100%",
                                    justify_content="flex-start",
                                ),
                                rx.cond(
                                    State.new_tenant_assigned_clients_open,
                                    rx.foreach(
                                        State.assignable_client_options,
                                        lambda client: rx.button(
                                            rx.hstack(
                                                rx.badge(
                                                    rx.cond(
                                                        State.new_tenant_assigned_client_ids.contains(client["id"]),
                                                        "No escopo",
                                                        "Disponível",
                                                    ),
                                                    color_scheme=rx.cond(
                                                        State.new_tenant_assigned_client_ids.contains(client["id"]),
                                                        "orange",
                                                        "gray",
                                                    ),
                                                ),
                                                rx.text(f'{client["id"]} - {client["name"]}', color="var(--text-primary)"),
                                                width="100%",
                                                align="center",
                                                spacing="3",
                                            ),
                                            on_click=State.toggle_new_tenant_assigned_client(client["id"]),
                                            variant="ghost",
                                            border=rx.cond(
                                                State.new_tenant_assigned_client_ids.contains(client["id"]),
                                                "1px solid rgba(255,122,47,0.38)",
                                                "1px solid var(--input-border)",
                                            ),
                                            bg=rx.cond(
                                                State.new_tenant_assigned_client_ids.contains(client["id"]),
                                                "rgba(255,122,47,0.10)",
                                                "transparent",
                                            ),
                                            width="100%",
                                            justify_content="flex-start",
                                        ),
                                    ),
                                    rx.fragment(),
                                ),
                                spacing="2",
                                width="100%",
                                align="stretch",
                            ),
                            width="100%",
                        ),
                        "Se selecionar um cliente pai, o tenant herda automaticamente o acesso aos clientes descendentes cadastrados no grupo. O workspace default da SmartLab permanece irrestrito.",
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.hstack(
                    rx.cond(
                        State.can_manage_tenants,
                        rx.hstack(
                            rx.button(
                                State.tenant_submit_label,
                                on_click=State.create_tenant,
                                bg="rgba(255,122,47,0.18)",
                                color="#fdba74",
                                border="1px solid rgba(255,122,47,0.38)",
                            ),
                            rx.cond(
                                State.is_editing_tenant,
                                rx.button(
                                    "Cancelar",
                                    on_click=State.reset_tenant_form,
                                    variant="ghost",
                                    border="1px solid var(--input-border)",
                                    color="var(--text-secondary)",
                                ),
                                rx.fragment(),
                            ),
                        ),
                        rx.badge("Sem permissao para editar tenants", color_scheme="red"),
                    ),
                    width="100%",
                ),
                width="100%",
                spacing="3",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        rx.box(
            rx.vstack(
                rx.grid(
                    *[
                        rx.text(
                            header,
                            color="var(--text-secondary)",
                            font_weight="600",
                            font_size="0.77rem",
                            text_align="center",
                            width="100%",
                        )
                        for header in tenant_table_headers
                    ],
                    columns="8",
                    width="100%",
                    align_items="center",
                    justify_items="center",
                    padding="0.1rem 0 0.85rem",
                    border_bottom="1px solid rgba(148,163,184,0.18)",
                    column_gap="0.9rem",
                ),
                rx.cond(
                    State.tenants_data.length() == 0,
                    rx.box(
                        rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.86rem"),
                        width="100%",
                        padding="1.25rem 0.5rem 0.5rem",
                        text_align="center",
                    ),
                    rx.vstack(
                        rx.foreach(
                            State.tenants_data,
                            lambda t: rx.grid(
                                tenant_table_cell(
                                    rx.text(t["id"], color="var(--text-primary)", font_weight="600", font_size="0.86rem"),
                                ),
                                tenant_table_cell(
                                    rx.text(t["name"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                ),
                                tenant_table_cell(
                                    rx.text(t["slug"], color="var(--text-secondary)", font_size="0.82rem"),
                                    rx.button(
                                        "Copiar slug",
                                        on_click=rx.set_clipboard(t["slug"]),
                                        variant="ghost",
                                        border="1px solid var(--input-border)",
                                        color="var(--text-secondary)",
                                        size="1",
                                    ),
                                ),
                                tenant_table_cell(
                                    rx.text(t["owner_client_name"], color="var(--text-secondary)", font_size="0.82rem"),
                                    rx.text(
                                        rx.cond(t["owner_client_name"] == "SmartLab", "Workspace interno", "Workspace do cliente"),
                                        color="var(--text-muted)",
                                        font_size="0.76rem",
                                    ),
                                ),
                                tenant_table_cell(
                                    rx.text(
                                        rx.cond(
                                            t["id"] == "default",
                                            "SmartLab default: total",
                                            f"Clientes no escopo: {t['client_scope_count']}",
                                        ),
                                        color="var(--text-secondary)",
                                        font_size="0.82rem",
                                    ),
                                    rx.text(
                                        t["client_scope_summary"],
                                        color="var(--text-muted)",
                                        font_size="0.76rem",
                                    ),
                                ),
                                tenant_table_cell(
                                    rx.text(t["created_at"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                tenant_table_cell(
                                    rx.text(t["limit"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                tenant_table_cell(
                                    rx.hstack(
                                        rx.cond(
                                            State.can_manage_tenants,
                                            rx.button(
                                                "Alterar",
                                                on_click=State.start_edit_tenant(t["id"]),
                                                bg="rgba(255,122,47,0.18)",
                                                color="#fdba74",
                                                border="1px solid rgba(255,122,47,0.38)",
                                                size="1",
                                            ),
                                            rx.fragment(),
                                        ),
                                        rx.cond(
                                            State.can_delete_tenants,
                                            rx.button(
                                                "Excluir",
                                                on_click=State.request_delete_confirmation("tenant", t["id"], t["name"]),
                                                bg="rgba(239,68,68,0.2)",
                                                color="#fca5a5",
                                                border="1px solid rgba(239,68,68,0.4)",
                                                size="1",
                                            ),
                                            rx.text("-", color="#64748b", font_size="0.82rem"),
                                        ),
                                        spacing="2",
                                        align="center",
                                        justify="center",
                                        width="100%",
                                    ),
                                ),
                                columns="8",
                                width="100%",
                                align_items="center",
                                justify_items="center",
                                column_gap="0.9rem",
                                padding="0.45rem 0",
                                border_bottom="1px solid rgba(148,163,184,0.12)",
                            ),
                        ),
                        width="100%",
                        spacing="0",
                    ),
                ),
                width="100%",
                spacing="3",
            ),
            width="100%",
            overflow_x="auto",
            padding="0.95rem 1rem",
            class_name="panel-card data-table-card",
            **CARD_STYLE,
        ),
        width="100%",
        spacing="4",
    )


def build_papeis_view(State, CARD_STYLE: dict[str, Any], field_block, data_table) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Papéis", color="var(--text-primary)", size="5"),
                rx.grid(
                    field_block(
                        "Nome do papel",
                        rx.input(
                            placeholder="Nome do papel",
                            value=State.new_role_name,
                            on_change=State.set_new_role_name,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Permissões",
                        rx.input(
                            placeholder="create:clientes,edit:clientes",
                            value=State.new_role_permissions,
                            on_change=State.set_new_role_permissions,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.hstack(
                    rx.cond(
                        State.can_manage_roles,
                        rx.hstack(
                            rx.button(
                                State.role_submit_label,
                                on_click=State.create_role,
                                bg="rgba(255,122,47,0.18)",
                                color="#fdba74",
                                border="1px solid rgba(255,122,47,0.38)",
                            ),
                            rx.cond(
                                State.is_editing_role,
                                rx.button(
                                    "Cancelar",
                                    on_click=State.reset_role_form,
                                    variant="ghost",
                                    border="1px solid var(--input-border)",
                                    color="var(--text-secondary)",
                                ),
                                rx.fragment(),
                            ),
                        ),
                        rx.badge("Sem permissao para editar papeis", color_scheme="red"),
                    ),
                    width="100%",
                ),
                width="100%",
                spacing="3",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["Nome", "Permissões", "Ações"],
            State.roles_data,
            lambda r: rx.hstack(
                rx.text(r["name"], color="var(--text-primary)", width="100%"),
                rx.text(r["permissions"], color="var(--text-secondary)", width="100%"),
                rx.hstack(
                    rx.cond(
                        State.can_manage_roles,
                        rx.button(
                            "Alterar",
                            on_click=State.start_edit_role(r["id"]),
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        State.can_delete_roles,
                        rx.button(
                            "Excluir",
                            on_click=State.request_delete_confirmation("role", r["id"], r["name"]),
                            bg="rgba(239,68,68,0.2)",
                            color="#fca5a5",
                            border="1px solid rgba(239,68,68,0.4)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2",
                ),
                width="100%",
            ),
        ),
        width="100%",
        spacing="4",
    )


def build_responsabilidades_view(State, CARD_STYLE: dict[str, Any], field_block, data_table) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Responsabilidades", color="var(--text-primary)", size="5"),
                rx.grid(
                    field_block(
                        "Papel",
                        rx.select(
                            State.role_id_options,
                            value=State.new_resp_role_id,
                            on_change=State.set_new_resp_role_id,
                            placeholder="Selecione o papel",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Descrição",
                        rx.input(
                            placeholder="Descrição da responsabilidade",
                            value=State.new_resp_desc,
                            on_change=State.set_new_resp_desc,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.hstack(
                    rx.cond(
                        State.can_manage_resps,
                        rx.hstack(
                            rx.button(
                                State.resp_submit_label,
                                on_click=State.create_responsibility,
                                bg="rgba(255,122,47,0.18)",
                                color="#fdba74",
                                border="1px solid rgba(255,122,47,0.38)",
                            ),
                            rx.cond(
                                State.is_editing_resp,
                                rx.button(
                                    "Cancelar",
                                    on_click=State.reset_resp_form,
                                    variant="ghost",
                                    border="1px solid var(--input-border)",
                                    color="var(--text-secondary)",
                                ),
                                rx.fragment(),
                            ),
                        ),
                        rx.badge("Sem permissao para editar responsabilidades", color_scheme="red"),
                    ),
                    width="100%",
                ),
                width="100%",
                spacing="3",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["Papel", "Descrição", "Ações"],
            State.responsibilities_data,
            lambda r: rx.hstack(
                rx.text(r["role"], color="var(--text-primary)", width="100%"),
                rx.text(r["description"], color="var(--text-secondary)", width="100%"),
                rx.hstack(
                    rx.cond(
                        State.can_manage_resps,
                        rx.button(
                            "Alterar",
                            on_click=State.start_edit_responsibility(r["id"]),
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        State.can_delete_resps,
                        rx.button(
                            "Excluir",
                            on_click=State.request_delete_confirmation("responsibility", r["id"], r["description"]),
                            bg="rgba(239,68,68,0.2)",
                            color="#fca5a5",
                            border="1px solid rgba(239,68,68,0.4)",
                            size="2",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2",
                ),
                width="100%",
            ),
        ),
        width="100%",
        spacing="4",
    )
