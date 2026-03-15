from typing import Any

import reflex as rx


def build_clientes_view(State, CARD_STYLE: dict[str, Any], field_block, table_text_cell, data_table) -> rx.Component:
    client_table_headers = [
        "ID",
        "Cliente",
        "Nome Fantasia",
        "CNPJ",
        "E-mail",
        "Ramo",
        "Colaboradores",
        "Empresas do Grupo",
        "Faturamento",
        "Workspace Cliente",
        "Ações",
    ]

    def client_table_cell(*children: rx.Component) -> rx.Component:
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
                        rx.heading("Clientes", color="var(--text-primary)", size="5"),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.badge("Passo 1: Cliente", color_scheme="orange"),
                    width="100%",
                    align="center",
                ),
                rx.hstack(
                    field_block(
                        "Nome do cliente",
                        rx.input(
                            placeholder="Nome do cliente",
                            value=State.new_client_name,
                            on_change=State.set_new_client_name,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Nome fantasia",
                        rx.input(
                            placeholder="Marca, unidade ou nome comercial",
                            value=State.new_client_trade_name,
                            on_change=State.set_new_client_trade_name,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "CNPJ",
                        rx.input(
                            placeholder="00.000.000/0000-00",
                            value=State.new_client_cnpj,
                            on_change=State.set_new_client_cnpj,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="3",
                    flex_direction="row",
                ),
                rx.hstack(
                    field_block(
                        "E-mail principal",
                        rx.input(
                            placeholder="Email principal",
                            value=State.new_client_email,
                            on_change=State.set_new_client_email,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Telefone de contato",
                        rx.input(
                            placeholder="(11) 99999-9999",
                            value=State.new_client_phone,
                            on_change=State.set_new_client_phone,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "UF",
                        rx.select(
                            State.brazilian_state_options,
                            value=State.new_client_state_code,
                            on_change=State.set_new_client_state_code,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="3",
                    flex_direction="row",
                ),
                rx.hstack(
                    field_block(
                        "Endereco",
                        rx.input(
                            placeholder="Rua, numero, complemento e bairro",
                            value=State.new_client_address,
                            on_change=State.set_new_client_address,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Ramo de atividade",
                        rx.select(
                            State.business_sector_options,
                            value=State.new_client_business_sector,
                            on_change=State.set_new_client_business_sector,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        "Escolha um ramo padrao ou selecione 'Outro' para cadastrar um novo.",
                    ),
                    rx.cond(
                        State.new_client_business_sector == "Outro",
                        field_block(
                            "Novo ramo",
                            rx.input(
                                placeholder="Informe o ramo de atividade",
                                value=State.new_client_custom_business_sector,
                                on_change=State.set_new_client_custom_business_sector,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            "Ao salvar, o novo ramo passa a fazer parte da lista de selecao deste tenant.",
                        ),
                        rx.fragment(),
                    ),
                    field_block(
                        "Cliente principal / Grupo",
                        rx.select(
                            State.group_parent_client_options,
                            value=State.selected_new_client_parent_option,
                            on_change=State.set_new_client_parent_option,
                            placeholder="Opcional: vincular a um grupo ou holding",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        "Use este campo quando a empresa fizer parte de um grupo, holding ou joint venture.",
                    ),
                    field_block(
                        "Quantidade de colaboradores",
                        rx.input(
                            placeholder="Ex.: 250",
                            value=State.new_client_employee_count,
                            on_change=State.set_new_client_employee_count,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Filiais físicas da empresa",
                        rx.input(
                            placeholder="Ex.: 12",
                            value=State.new_client_branch_count,
                            on_change=State.set_new_client_branch_count,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Faturamento anual em R$",
                        rx.input(
                            placeholder="Ex.: 1500000,00",
                            value=State.new_client_annual_revenue,
                            on_change=State.set_new_client_annual_revenue,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="3",
                    flex_direction="row",
                ),
                rx.cond(
                    State.can_manage_clients,
                    rx.hstack(
                        rx.button(
                            State.client_submit_label,
                            on_click=State.create_client,
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                        ),
                        rx.cond(
                            State.is_editing_client,
                            rx.button(
                                "Cancelar",
                                on_click=State.reset_client_form,
                                variant="ghost",
                                border="1px solid var(--input-border)",
                                color="var(--text-secondary)",
                            ),
                            rx.fragment(),
                        ),
                        width="100%",
                        justify="start",
                        align="center",
                        spacing="2",
                    ),
                    rx.badge("Viewer: somente leitura", color_scheme="purple"),
                ),
                rx.box(
                    rx.text(
                        "Ao cadastrar o cliente, o sistema cria automaticamente um workspace isolado para ele. A tela de Tenants fica reservada para administracao avancada.",
                        color="var(--text-muted)",
                        font_size="0.84rem",
                    ),
                    class_name="workspace-guide",
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
                        for header in client_table_headers
                    ],
                    columns="11",
                    width="100%",
                    align_items="center",
                    justify_items="center",
                    padding="0.1rem 0 0.85rem",
                    border_bottom="1px solid rgba(148,163,184,0.18)",
                    column_gap="0.9rem",
                ),
                rx.cond(
                    State.clients_data.length() == 0,
                    rx.box(
                        rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.86rem"),
                        width="100%",
                        padding="1.25rem 0.5rem 0.5rem",
                        text_align="center",
                    ),
                    rx.vstack(
                        rx.foreach(
                            State.clients_data,
                            lambda c: rx.grid(
                                client_table_cell(
                                    rx.text(c["id"], color="var(--text-primary)", font_weight="600", font_size="0.86rem"),
                                ),
                                client_table_cell(
                                    rx.text(c["name"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                ),
                                client_table_cell(
                                    rx.text(c["trade_name"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                client_table_cell(
                                    rx.text(c["cnpj"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                client_table_cell(
                                    rx.text(c["email"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                client_table_cell(
                                    rx.badge(c["business_sector"], color_scheme="orange", width="fit-content", size="1"),
                                ),
                                client_table_cell(
                                    rx.text(c["employee_count"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                client_table_cell(
                                    rx.cond(
                                        c["parent_client_name"] != "-",
                                        rx.badge(
                                            f'Grupo: {c["parent_client_name"]}',
                                            color_scheme="gray",
                                            width="fit-content",
                                            size="1",
                                        ),
                                        rx.fragment(),
                                    ),
                                    rx.text(
                                        c["group_children"],
                                        color="var(--text-secondary)",
                                        font_size="0.8rem",
                                        white_space="normal",
                                        word_break="break-word",
                                    ),
                                ),
                                client_table_cell(
                                    rx.text(c["annual_revenue"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                client_table_cell(
                                    rx.badge(c["workspace_tenant"], color_scheme="orange", width="fit-content", size="1"),
                                ),
                                client_table_cell(
                                    rx.hstack(
                                        rx.cond(
                                            State.can_manage_clients,
                                            rx.button(
                                                "Alterar",
                                                on_click=State.start_edit_client(c["id"]),
                                                bg="rgba(255,122,47,0.18)",
                                                color="#fdba74",
                                                border="1px solid rgba(255,122,47,0.38)",
                                                size="1",
                                            ),
                                            rx.fragment(),
                                        ),
                                        rx.cond(
                                            State.can_delete_clients,
                                            rx.button(
                                                "Excluir",
                                                on_click=State.request_delete_confirmation("client", c["id"], c["name"]),
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
                                columns="11",
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
        spacing="4",
        width="100%",
        min_width="100%",
        align="stretch",
    )


def build_usuarios_view(State, CARD_STYLE: dict[str, Any], field_block, table_text_cell, data_table) -> rx.Component:
    user_table_headers = ["Nome", "Acesso", "Organização", "Workspace", "Ações"]

    def user_table_cell(*children: rx.Component) -> rx.Component:
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
                        rx.heading("Gestao de Usuarios", color="var(--text-primary)", size="5"),
                        rx.text(
                            "Crie contas internas SmartLab ou contas de cliente vinculadas ao workspace correto.",
                            color="var(--text-muted)",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.badge("Passo 3: Colaboradores", color_scheme="orange"),
                    width="100%",
                    align="center",
                ),
                rx.grid(
                    field_block(
                        "Nome completo",
                        rx.input(
                            placeholder="Nome completo",
                            value=State.new_user_name,
                            on_change=State.set_new_user_name,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "E-mail",
                        rx.input(
                            placeholder="usuario@empresa.com",
                            value=State.new_user_email,
                            on_change=State.set_new_user_email,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Senha inicial",
                        rx.input(
                            placeholder="Senha local inicial",
                            value=State.new_user_password,
                            on_change=State.set_new_user_password,
                            type="password",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        State.user_password_help_text,
                    ),
                    field_block(
                        "Papel",
                        rx.select(
                            State.user_role_options,
                            value=State.new_user_role,
                            on_change=State.set_new_user_role,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Escopo da conta",
                        rx.select(
                            State.user_scope_options,
                            value=State.new_user_scope,
                            on_change=State.set_new_user_scope,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        "Define se a conta e interna SmartLab ou se pertence ao cliente.",
                    ),
                    rx.cond(
                        State.new_user_scope == "cliente",
                        field_block(
                            "Cliente vinculado",
                            rx.select(
                                State.client_display_options,
                                value=State.selected_new_user_client_option,
                                on_change=State.set_new_user_client_option,
                                placeholder="Cliente vinculado",
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            "Obrigatorio para contas de cliente.",
                        ),
                        field_block(
                            "Clientes autorizados",
                            rx.box(
                                rx.vstack(
                                    rx.button(
                                        rx.hstack(
                                            rx.text(State.selected_assigned_clients_summary, color="var(--text-primary)"),
                                            rx.spacer(),
                                            rx.icon(
                                                tag=rx.cond(State.new_user_assigned_clients_open, "chevron_up", "chevron_down"),
                                                size=16,
                                                color="var(--text-muted)",
                                            ),
                                            width="100%",
                                            align="center",
                                        ),
                                        on_click=State.toggle_new_user_assigned_clients_open,
                                        variant="ghost",
                                        border="1px solid var(--input-border)",
                                        bg="var(--input-bg)",
                                        width="100%",
                                        justify_content="flex-start",
                                    ),
                                    rx.cond(
                                        State.new_user_assigned_clients_open,
                                        rx.foreach(
                                            State.assignable_client_options,
                                            lambda client: rx.button(
                                                rx.hstack(
                                                    rx.badge(
                                                        rx.cond(
                                                            State.new_user_assigned_client_ids.contains(client["id"]),
                                                            "Autorizado",
                                                            "Disponivel",
                                                        ),
                                                        color_scheme=rx.cond(
                                                            State.new_user_assigned_client_ids.contains(client["id"]),
                                                            "orange",
                                                            "gray",
                                                        ),
                                                    ),
                                                    rx.text(f'{client["id"]} - {client["name"]}', color="var(--text-primary)"),
                                                    width="100%",
                                                    align="center",
                                                    spacing="3",
                                                ),
                                                on_click=State.toggle_new_user_assigned_client(client["id"]),
                                                variant="ghost",
                                                border=rx.cond(
                                                    State.new_user_assigned_client_ids.contains(client["id"]),
                                                    "1px solid rgba(255,122,47,0.38)",
                                                    "1px solid var(--input-border)",
                                                ),
                                                bg=rx.cond(
                                                    State.new_user_assigned_client_ids.contains(client["id"]),
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
                            "Selecione apenas os clientes que este consultor pode operar.",
                        ),
                    ),
                    rx.cond(
                        State.new_user_scope == "cliente",
                        field_block(
                            "Workspace do usuario",
                            rx.select(
                                State.user_workspace_options,
                                value=State.selected_new_user_workspace_option,
                                on_change=State.set_new_user_workspace_option,
                                placeholder="Workspace do usuario",
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            "Workspace e o ambiente isolado onde esse usuario vai operar.",
                        ),
                        field_block(
                            "Workspace base",
                            rx.input(
                                value="default - SmartLab",
                                read_only=True,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                            "Usuarios SmartLab nascem no workspace interno e acessam apenas os clientes autorizados.",
                        ),
                    ),
                    field_block(
                        "Profissao",
                        rx.select(
                            State.profession_options,
                            value=State.new_user_profession,
                            on_change=State.set_new_user_profession,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.cond(
                        State.new_user_profession == "Outro",
                        field_block(
                            "Nova profissao",
                            rx.input(
                                placeholder="Informe a profissao",
                                value=State.new_user_custom_profession,
                                on_change=State.set_new_user_custom_profession,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                        ),
                        rx.fragment(),
                    ),
                    field_block(
                        "Departamento",
                        rx.select(
                            State.department_options,
                            value=State.new_user_department,
                            on_change=State.set_new_user_department,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "A quem se reporta",
                        rx.select(
                            State.reporting_user_options,
                            value=State.selected_reporting_user_option,
                            on_change=State.set_new_user_reports_to_user_option,
                            placeholder="Selecione a hierarquia",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.cond(
                        State.new_user_department == "Outro",
                        field_block(
                            "Novo departamento",
                            rx.input(
                                placeholder="Informe o departamento",
                                value=State.new_user_custom_department,
                                on_change=State.set_new_user_custom_department,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                        ),
                        rx.fragment(),
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.hstack(
                    rx.cond(
                        State.can_manage_users,
                        rx.hstack(
                            rx.button(
                                State.user_submit_label,
                                on_click=State.create_user,
                                bg="rgba(255,122,47,0.18)",
                                color="#fdba74",
                                border="1px solid rgba(255,122,47,0.38)",
                            ),
                            rx.cond(
                                State.is_editing_user,
                                rx.button(
                                    "Cancelar",
                                    on_click=State.reset_user_form,
                                    variant="ghost",
                                    border="1px solid var(--input-border)",
                                    color="var(--text-secondary)",
                                ),
                                rx.fragment(),
                            ),
                        ),
                        rx.badge("Sem permissao para criar usuarios", color_scheme="red"),
                    ),
                    rx.spacer(),
                    rx.text(
                        "Na proxima fase, cliente_admin podera criar usuarios limitados do proprio tenant.",
                        color="var(--text-muted)",
                        font_size="0.84rem",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.box(
                    rx.text(
                        "Regra: colaborador de cliente precisa apontar para o cliente e para o tenant daquele mesmo cliente. Colaborador SmartLab pode operar varios clientes conforme o papel.",
                        color="var(--text-muted)",
                        font_size="0.84rem",
                    ),
                    class_name="auth-note",
                    width="100%",
                ),
                width="100%",
                spacing="3",
                align="start",
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
                        for header in user_table_headers
                    ],
                    columns="5",
                    width="100%",
                    align_items="center",
                    justify_items="center",
                    padding="0.1rem 0 0.85rem",
                    border_bottom="1px solid rgba(148,163,184,0.18)",
                    column_gap="0.9rem",
                ),
                rx.cond(
                    State.users_data.length() == 0,
                    rx.box(
                        rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.86rem"),
                        width="100%",
                        padding="1.25rem 0.5rem 0.5rem",
                        text_align="center",
                    ),
                    rx.vstack(
                        rx.foreach(
                            State.users_data,
                            lambda u: rx.grid(
                                user_table_cell(
                                    rx.text(u["name"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                    rx.text(u["email"], color="var(--text-secondary)", font_size="0.8rem"),
                                ),
                                user_table_cell(
                                    rx.hstack(
                                        rx.badge(u["role"], color_scheme="purple", width="fit-content", size="1"),
                                        rx.badge(
                                            u["account_scope"],
                                            color_scheme=rx.cond(u["account_scope"] == "smartlab", "orange", "green"),
                                            width="fit-content",
                                            size="1",
                                        ),
                                        spacing="2",
                                        align="center",
                                        justify="center",
                                        flex_wrap="wrap",
                                        width="100%",
                                    ),
                                    rx.text(
                                        f'Senha inicial: {u["must_change_password"]}',
                                        color="var(--text-muted)",
                                        font_size="0.78rem",
                                    ),
                                ),
                                user_table_cell(
                                    rx.text(
                                        f'{u["profession"]} • {u["department"]}',
                                        color="var(--text-secondary)",
                                        font_size="0.82rem",
                                        white_space="normal",
                                        word_break="break-word",
                                    ),
                                    rx.cond(
                                        u["account_scope"] == "smartlab",
                                        rx.text(
                                            f'Clientes autorizados: {u["assigned_clients"]}',
                                            color="var(--text-muted)",
                                            font_size="0.78rem",
                                            white_space="normal",
                                            word_break="break-word",
                                        ),
                                        rx.cond(
                                            u["reports_to_user_name"] != "-",
                                            rx.text(
                                                f'Reporta para: {u["reports_to_user_name"]}',
                                                color="var(--text-muted)",
                                                font_size="0.78rem",
                                                white_space="normal",
                                                word_break="break-word",
                                            ),
                                            rx.fragment(),
                                        ),
                                    ),
                                ),
                                user_table_cell(
                                    rx.text(u["tenant_id"], color="var(--text-secondary)", font_size="0.82rem"),
                                    rx.cond(
                                        u["client_name"] != "-",
                                        rx.text(u["client_name"], color="var(--text-muted)", font_size="0.78rem"),
                                        rx.fragment(),
                                    ),
                                ),
                                user_table_cell(
                                    rx.hstack(
                                        rx.cond(
                                            State.can_manage_users,
                                            rx.button(
                                                "Alterar",
                                                on_click=State.start_edit_user(u["id"]),
                                                bg="rgba(255,122,47,0.18)",
                                                color="#fdba74",
                                                border="1px solid rgba(255,122,47,0.38)",
                                                size="1",
                                            ),
                                            rx.fragment(),
                                        ),
                                        rx.cond(
                                            State.can_delete_users,
                                            rx.button(
                                                "Excluir",
                                                on_click=State.request_delete_confirmation("user", u["id"], u["name"]),
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
                                columns="5",
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
