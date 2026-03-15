from typing import Any

import reflex as rx


def build_apis_view(State, CARD_STYLE: dict[str, Any], data_table) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Camada API-First", color="var(--text-primary)", size="5"),
                rx.text(
                    "Recursos priorizados para integração, embedding e composição low-code do produto.",
                    color="var(--text-muted)",
                ),
                rx.grid(
                    rx.foreach(
                        State.api_catalog,
                        lambda item: rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.badge(item["method"], color_scheme="orange"),
                                    rx.badge(item["kind"], color_scheme="purple"),
                                    rx.spacer(),
                                    width="100%",
                                ),
                                rx.heading(item["name"], size="4", color="var(--text-primary)"),
                                rx.text(item["path"], color="var(--accent-strong)", font_size="0.85rem"),
                                rx.text(item["purpose"], color="var(--text-secondary)", font_size="0.9rem"),
                                align="start",
                                spacing="2",
                                width="100%",
                            ),
                            padding="1rem",
                            class_name="panel-card",
                            **CARD_STYLE,
                        ),
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        data_table(
            ["Recurso", "Metodo", "Path", "Objetivo", "Classe"],
            State.api_catalog,
            lambda item: rx.hstack(
                rx.text(item["name"], color="var(--text-primary)", width="100%"),
                rx.badge(item["method"], color_scheme="orange", width="fit-content"),
                rx.text(item["path"], color="var(--text-secondary)", width="100%"),
                rx.text(item["purpose"], color="var(--text-secondary)", width="100%"),
                rx.badge(item["kind"], color_scheme="purple", width="fit-content"),
                width="100%",
            ),
        ),
        width="100%",
        spacing="4",
    )


def build_dashboard_view(State, CARD_STYLE: dict[str, Any], metric_card, data_table) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Caixas do Dashboard", color="var(--text-primary)", size="5"),
                rx.hstack(
                    rx.input(
                        placeholder="Nome da caixa (ex: Alertas de Prazo)",
                        value=State.new_dashboard_box_title,
                        on_change=State.set_new_dashboard_box_title,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.select(
                        ["kpi", "grafico", "lista", "texto"],
                        value=State.new_dashboard_box_kind,
                        on_change=State.set_new_dashboard_box_kind,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                        width="150px",
                    ),
                    rx.select(
                        ["consultor", "cliente"],
                        value=State.new_dashboard_box_scope,
                        on_change=State.set_new_dashboard_box_scope,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                        width="150px",
                    ),
                    rx.button(
                        "Adicionar Caixa",
                        on_click=State.add_dashboard_box,
                        class_name="primary-soft-action",
                    ),
                    width="100%",
                    spacing="3",
                    flex_wrap="wrap",
                ),
                rx.grid(
                    rx.select(
                        ["projetos", "scores", "progresso", "formularios", "respostas", "custom"],
                        value=State.new_dashboard_box_source,
                        on_change=State.set_new_dashboard_box_source,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Descricao funcional da caixa",
                        value=State.new_dashboard_box_description,
                        on_change=State.set_new_dashboard_box_description,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                        width="100%",
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.grid(
                    rx.foreach(
                        State.dashboard_boxes_data,
                        lambda b: rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.heading(b["title"], size="4", color="var(--text-primary)"),
                                    rx.spacer(),
                                    rx.badge(b["kind"], color_scheme="purple"),
                                    spacing="2",
                                    width="100%",
                                    align="center",
                                ),
                                rx.text(f"Fonte: {b['source']}", color="var(--text-muted)", font_size="0.82rem"),
                                rx.text(
                                    rx.cond(
                                        b["description"] != "",
                                        b["description"],
                                        "Sem descricao funcional",
                                    ),
                                    color="var(--text-secondary)",
                                    font_size="0.84rem",
                                ),
                                rx.badge(f"embed: {b['embed']}", color_scheme="orange"),
                                rx.hstack(
                                    rx.button(
                                        "Subir",
                                        on_click=State.move_dashboard_box(b["id"], "up"),
                                        size="1",
                                        variant="ghost",
                                        border="1px solid var(--input-border)",
                                        color="var(--text-secondary)",
                                    ),
                                    rx.button(
                                        "Descer",
                                        on_click=State.move_dashboard_box(b["id"], "down"),
                                        size="1",
                                        variant="ghost",
                                        border="1px solid var(--input-border)",
                                        color="var(--text-secondary)",
                                    ),
                                    spacing="2",
                                ),
                                align="start",
                                spacing="2",
                                width="100%",
                            ),
                            padding="0.9rem",
                            class_name="panel-card",
                            **CARD_STYLE,
                        ),
                    ),
                    columns="3",
                    spacing="3",
                    width="100%",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        ),
        rx.grid(
            metric_card("Clientes", State.dashboard_metrics["clientes"]),
            metric_card("Formulários", State.dashboard_metrics["formularios"]),
            metric_card("Respostas", State.dashboard_metrics["respostas"]),
            metric_card("Média de Segurança", State.dashboard_metrics["media"]),
            columns="4",
            spacing="4",
            width="100%",
        ),
        data_table(
            ["Caixa", "Tipo", "Fonte", "Descricao"],
            State.dashboard_builder_preview,
            lambda item: rx.hstack(
                rx.text(item["title"], color="var(--text-primary)", width="100%"),
                rx.badge(item["kind"], color_scheme="purple", width="fit-content"),
                rx.text(item["source"], color="var(--text-secondary)", width="100%"),
                rx.text(item["description"], color="var(--text-secondary)", width="100%"),
                width="100%",
            ),
        ),
        data_table(
            ["Formulário", "Categoria", "Respostas", "Média", "Status"],
            State.dashboard_table,
            lambda r: rx.hstack(
                rx.text(r["form"], color="var(--text-primary)", width="100%"),
                rx.text(r["categoria"], color="var(--text-secondary)", width="100%"),
                rx.text(r["respostas"], color="var(--text-secondary)", width="100%"),
                rx.text(r["media"], color="#f59e0b", width="100%"),
                rx.badge(
                    r["status"],
                    color_scheme=rx.cond(r["status"] == "Forte", "green", rx.cond(r["status"] == "Crítico", "red", "purple")),
                    width="fit-content",
                ),
                width="100%",
            ),
        ),
        spacing="4",
        width="100%",
    )


def build_planos_view(State, CARD_STYLE: dict[str, Any]) -> rx.Component:
    def action_card(action: dict[str, Any]) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.text(action["title"], color="var(--text-primary)", font_weight="600"),
                rx.text(f"Responsável: {action['owner']}", color="var(--text-secondary)", font_size="0.85rem"),
                rx.text(
                    rx.cond(action["due_date"] != "", f"Prazo: {action['due_date']}", "Prazo: -"),
                    color="var(--text-muted)",
                    font_size="0.82rem",
                ),
                rx.text(f"Atingimento: {action['attainment']}%", color="#f59e0b", font_size="0.82rem"),
                rx.hstack(
                    rx.button(
                        "A Fazer",
                        on_click=State.move_action_status(action["id"], "a_fazer"),
                        size="1",
                        variant="ghost",
                        border="1px solid var(--input-border)",
                    ),
                    rx.button(
                        "Andamento",
                        on_click=State.move_action_status(action["id"], "em_andamento"),
                        size="1",
                        variant="ghost",
                        border="1px solid var(--input-border)",
                    ),
                    rx.button(
                        "Concluído",
                        on_click=State.move_action_status(action["id"], "concluido"),
                        size="1",
                        bg="rgba(34,197,94,0.2)",
                        color="#86efac",
                        border="1px solid rgba(34,197,94,0.4)",
                    ),
                    spacing="1",
                ),
                align="start",
                spacing="2",
                width="100%",
            ),
            padding="0.75rem",
            border="1px solid var(--card-border)",
            border_radius="12px",
            bg="var(--surface-soft)",
            width="100%",
        )

    def kanban_col(title: str, items: rx.Var) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(title, color="var(--text-primary)", font_weight="700"),
                    width="100%",
                ),
                rx.foreach(items, action_card),
                width="100%",
                spacing="2",
                align="start",
            ),
            padding="0.8rem",
            width="100%",
            border="1px dashed var(--dropzone-border)",
            border_radius="14px",
            bg="var(--dropzone-bg)",
        )

    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Gestão de Planos de Ação", color="var(--text-primary)", size="5"),
                rx.select(
                    State.project_id_options,
                    value=State.selected_project_option,
                    on_change=State.select_project,
                    placeholder="Selecione projeto",
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                    width="100%",
                ),
                rx.hstack(
                    rx.input(
                        placeholder="Ação",
                        value=State.new_action_title,
                        on_change=State.set_new_action_title,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.input(
                        placeholder="Responsável",
                        value=State.new_action_owner,
                        on_change=State.set_new_action_owner,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.input(
                        placeholder="Prazo (YYYY-MM-DD)",
                        value=State.new_action_due_date,
                        on_change=State.set_new_action_due_date,
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    width="100%",
                    spacing="3",
                    flex_wrap="wrap",
                ),
                rx.input(
                    placeholder="Resultado esperado",
                    value=State.new_action_expected_result,
                    on_change=State.set_new_action_expected_result,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                ),
                rx.button(
                    "Criar Ação",
                    on_click=State.create_action_plan,
                    class_name="primary-soft-action",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        ),
        rx.grid(
            kanban_col("A Fazer", State.actions_todo),
            kanban_col("Em Andamento", State.actions_doing),
            kanban_col("Concluído", State.actions_done),
            columns="3",
            spacing="3",
            width="100%",
        ),
        width="100%",
        spacing="4",
    )
