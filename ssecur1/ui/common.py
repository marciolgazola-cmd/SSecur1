from typing import Any

import reflex as rx


def build_app_header(State, smartlab_logo) -> rx.Component:
    return rx.hstack(
        rx.hstack(
            smartlab_logo("52px"),
            rx.vstack(
                rx.text("SSecur1", color="var(--text-primary)", font_weight="700"),
                rx.text("Diagnóstico de Segurança", color="var(--text-muted)", font_size="0.8rem"),
                spacing="0",
                align="start",
            ),
            align="center",
            spacing="2",
        ),
        rx.spacer(),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="search", size=16, color="var(--text-muted)"),
                    rx.input(
                        placeholder="Buscar cliente, formulario, usuario, papel...",
                        value=State.global_search_query,
                        on_change=State.set_global_search_query,
                        class_name="header-search-input",
                        bg="transparent",
                        border="0",
                        box_shadow="none",
                        color="var(--text-primary)",
                        width="100%",
                    ),
                    rx.cond(
                        State.global_search_query != "",
                        rx.button(
                            "Limpar",
                            on_click=State.clear_global_search,
                            class_name="header-search-clear",
                        ),
                        rx.fragment(),
                    ),
                    class_name="header-search-shell",
                    width="100%",
                    align="center",
                    spacing="2",
                ),
                rx.cond(
                    State.global_search_query != "",
                    rx.box(
                        rx.cond(
                            State.global_search_results.length() > 0,
                            rx.vstack(
                                rx.foreach(
                                    State.global_search_results,
                                    lambda item: rx.button(
                                        rx.hstack(
                                            rx.badge(item["kind"], color_scheme="gray", variant="soft"),
                                            rx.vstack(
                                                rx.text(item["title"], color="var(--text-primary)", font_weight="600"),
                                                rx.text(item["subtitle"], color="var(--text-muted)", font_size="0.8rem"),
                                                align="start",
                                                spacing="0",
                                                width="100%",
                                            ),
                                            width="100%",
                                            align="center",
                                            spacing="3",
                                        ),
                                        on_click=State.open_search_result(item["view"], item["record_id"]),
                                        class_name="header-search-result",
                                        bg="transparent",
                                        color="var(--text-primary)",
                                        border="1px solid transparent",
                                        width="100%",
                                        justify_content="flex-start",
                                    ),
                                ),
                                width="100%",
                                spacing="1",
                                align="stretch",
                            ),
                            rx.text(
                                "Nenhum resultado encontrado.",
                                color="var(--text-muted)",
                                class_name="header-search-empty",
                            ),
                        ),
                        class_name="header-search-popover",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                spacing="2",
                width="100%",
                align="stretch",
            ),
            width="320px",
            position="relative",
        ),
        rx.cond(
            State.user_scope == "smartlab",
            rx.select(
                State.tenant_display_options,
                value=State.current_tenant_display,
                on_change=State.switch_tenant_from_display,
                color="var(--text-primary)",
                bg="var(--surface-soft)",
                border="1px solid var(--input-border)",
                width="240px",
            ),
            rx.box(
                rx.vstack(
                    rx.text("Tenant Atual", color="var(--text-muted)", font_size="0.72rem"),
                    rx.text(State.current_tenant, color="var(--text-primary)", font_weight="600"),
                    spacing="0",
                    align="start",
                ),
                padding="0.5rem 0.8rem",
                border="1px solid var(--input-border)",
                border_radius="12px",
                bg="var(--surface-soft)",
            ),
        ),
        rx.button(
            rx.cond(State.dark_mode, rx.icon(tag="sun", size=16), rx.icon(tag="moon", size=16)),
            rx.text(State.theme_toggle_short_label, font_size="0.78rem"),
            on_click=State.toggle_theme,
            bg="var(--toggle-btn-bg)",
            color="var(--toggle-btn-text)",
            border="1px solid var(--toggle-btn-border)",
            _hover={"bg": "var(--toggle-btn-hover-bg)"},
        ),
        rx.badge(State.user_role, color_scheme="purple"),
        rx.badge(State.user_scope, color_scheme="orange"),
        rx.button(
            "Sair",
            on_click=State.logout,
            bg="rgba(239,68,68,0.18)",
            color="#fda4af",
            border="1px solid rgba(239,68,68,0.35)",
        ),
        width="100%",
        align="center",
        spacing="3",
        flex_wrap="wrap",
        padding="0.8rem 1rem",
        border_bottom="1px solid var(--card-border)",
        bg="var(--header-bg)",
        backdrop_filter="blur(12px)",
        position="sticky",
        top="0",
        z_index="10",
        class_name="header-bar",
    )


def build_sidebar(State, nav_button) -> rx.Component:
    nav_items = rx.vstack(
        rx.cond(State.show_menu_clients, nav_button("Clientes", "users", "clientes"), rx.fragment()),
        rx.cond(State.show_menu_tenants, nav_button("Tenants", "building_2", "tenants"), rx.fragment()),
        rx.cond(State.show_menu_users, nav_button("Usuários", "users", "usuarios"), rx.fragment()),
        rx.cond(State.show_menu_permissions, nav_button("Permissões", "lock_keyhole", "permissoes"), rx.fragment()),
        rx.cond(State.show_menu_projects, nav_button("Projetos", "file_text", "projetos"), rx.fragment()),
        rx.cond(State.show_menu_forms, nav_button("Respostas", "file_text", "formularios"), rx.fragment()),
        rx.cond(State.show_menu_plans, nav_button("Plano de Ação", "list_todo", "planos"), rx.fragment()),
        rx.cond(State.show_menu_dashboard, nav_button("Dashboard", "layout_dashboard", "dashboard"), rx.fragment()),
        rx.cond(State.show_menu_apis, nav_button("APIs", "plug", "apis"), rx.fragment()),
        rx.cond(State.show_menu_roles, nav_button("Papéis", "shield_check", "papeis"), rx.fragment()),
        rx.cond(
            State.show_menu_responsibilities,
            nav_button("Responsabilidades", "clipboard_list", "responsabilidades"),
            rx.fragment(),
        ),
        rx.cond(State.show_menu_ai, nav_button("Assistente IA", "sparkles", "ia"), rx.fragment()),
        width="100%",
        spacing="2",
    )

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.button(
                    rx.icon(tag="panel_left", size=18, color="var(--nav-icon)"),
                    on_click=State.toggle_sidebar,
                    variant="ghost",
                    border="1px solid var(--card-border)",
                ),
                rx.cond(
                    State.sidebar_collapsed,
                    rx.fragment(),
                    rx.text("Navegação", color="var(--text-muted)", font_weight="500"),
                ),
                width="100%",
                justify="between",
            ),
            nav_items,
            spacing="4",
            width="100%",
            align="start",
            padding="0.8rem",
        ),
        width=rx.cond(State.sidebar_collapsed, "72px", "300px"),
        min_height="100dvh",
        height="100dvh",
        max_height="100dvh",
        overflow_y="auto",
        transition="width 0.2s ease",
        background="var(--sidebar-bg)",
        border_right="1px solid var(--card-border)",
        position="sticky",
        top="0",
        align_self="stretch",
        display="block",
        class_name="sidebar-panel",
    )


def build_metric_card(CARD_STYLE: dict[str, Any], title: str, value: rx.Var) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(class_name="hexagon"),
            rx.vstack(
                rx.text(title, color="var(--text-muted)"),
                rx.heading(value, color="var(--text-primary)", size="6"),
                align="start",
                spacing="0",
            ),
            align="center",
            spacing="3",
        ),
        padding="1rem",
        _hover={"transform": "scale(1.02)"},
        transition="all 0.2s ease",
        class_name="panel-card metric-card",
        **CARD_STYLE,
    )


def build_field_block(label: str, control: rx.Component, help_text: str = "") -> rx.Component:
    return rx.vstack(
        rx.text(label, color="var(--text-muted)", font_size="0.78rem", font_weight="600"),
        control,
        rx.cond(
            help_text != "",
            rx.text(help_text, color="var(--text-muted)", font_size="0.76rem"),
            rx.fragment(),
        ),
        spacing="1",
        align="start",
        width="100%",
        class_name="field-block",
    )


def build_table_text_cell(primary: rx.Component, secondary: rx.Component | None = None) -> rx.Component:
    children = [primary]
    if secondary is not None:
        children.append(secondary)
    return rx.vstack(
        *children,
        spacing="0",
        align="start",
        width="100%",
        class_name="table-cell",
    )


def build_data_table(CARD_STYLE: dict[str, Any], headers: list[str], rows: rx.Var, row_builder) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.foreach(
                    headers,
                    lambda h: rx.text(h, color="var(--text-secondary)", font_weight="600", width="100%"),
                ),
                width="100%",
                border_bottom="1px solid rgba(148,163,184,0.18)",
                padding_bottom="0.75rem",
                class_name="data-table-header",
            ),
            rx.cond(
                rows.length() == 0,
                rx.box(
                    rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.9rem"),
                    class_name="data-table-empty",
                ),
                rx.vstack(
                    rx.foreach(
                        rows,
                        lambda row: rx.box(
                            row_builder(row),
                            class_name="data-table-row",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="2",
                ),
            ),
            width="100%",
            spacing="3",
        ),
        width="100%",
        overflow_x="auto",
        class_name="panel-card data-table-card",
        **CARD_STYLE,
        padding="1rem",
    )


def build_workflow_connection_line(line_type: rx.Var) -> rx.Component:
    return rx.vstack(
        rx.box(
            width="2px",
            height="30px",
            bg=rx.cond(line_type == "ai", "rgba(123,115,154,0.75)", "rgba(255,81,0,0.72)"),
            class_name="workflow-connection-line",
        ),
        rx.badge(rx.cond(line_type == "ai", "AI", "MAIN"), color_scheme=rx.cond(line_type == "ai", "purple", "orange")),
        align="center",
        spacing="1",
        width="100%",
    )


def build_workflow_node(State, node_data: dict[str, Any]) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.cond(
                        node_data["box_type"] == "trigger",
                        rx.icon(tag="zap", size=14, color="#f59e0b"),
                        rx.icon(tag="box", size=14, color="var(--text-muted)"),
                    ),
                    rx.text(node_data["title"], color="var(--text-primary)", font_weight="700", font_size="0.84rem"),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.badge(node_data["box_type"], color_scheme=rx.cond(node_data["box_type"] == "trigger", "yellow", "orange")),
                width="100%",
                align="center",
            ),
            rx.hstack(
                rx.box(width="9px", height="9px", border_radius="999px", bg="rgba(255,81,0,0.82)"),
                rx.text(
                    rx.cond(node_data["endpoint"] != "", node_data["endpoint"], "Sem endpoint"),
                    color="var(--text-muted)",
                    font_size="0.72rem",
                ),
                rx.spacer(),
                rx.box(width="9px", height="9px", border_radius="999px", bg="rgba(123,115,154,0.82)"),
                width="100%",
                align="center",
                spacing="2",
            ),
            rx.cond(
                node_data["condition"] != "",
                rx.text(
                    f"Condicao: {node_data['condition']}",
                    color="var(--text-secondary)",
                    font_size="0.72rem",
                ),
                rx.fragment(),
            ),
            rx.cond(
                node_data["output_key"] != "",
                rx.text(
                    f"Saida: {node_data['output_key']}",
                    color="var(--accent-strong)",
                    font_size="0.72rem",
                ),
                rx.fragment(),
            ),
            rx.hstack(
                rx.button("↑", on_click=State.move_workflow_box(node_data["id"], "up"), size="1", variant="ghost"),
                rx.button("↓", on_click=State.move_workflow_box(node_data["id"], "down"), size="1", variant="ghost"),
                rx.button(
                    "Excluir",
                    on_click=State.request_delete_confirmation("workflow_box", node_data["id"], node_data["title"]),
                    size="1",
                    bg="rgba(239,68,68,0.16)",
                    color="#fca5a5",
                    border="1px solid rgba(239,68,68,0.35)",
                ),
                spacing="2",
            ),
            width="100%",
            spacing="2",
            align="start",
        ),
        class_name="workflow-node",
        width="100%",
        max_width="420px",
    )
