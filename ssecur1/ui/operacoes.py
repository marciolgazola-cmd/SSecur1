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


def build_auditoria_view(State, CARD_STYLE: dict[str, Any]) -> rx.Component:
    def audit_tab_button(label: str, value: str) -> rx.Component:
        return rx.button(
            label,
            on_click=State.set_audit_active_tab(value),
            bg=rx.cond(State.audit_active_tab == value, "rgba(249,115,22,0.16)", "transparent"),
            color=rx.cond(State.audit_active_tab == value, "var(--text-primary)", "var(--text-secondary)"),
            border=rx.cond(
                State.audit_active_tab == value,
                "1px solid rgba(249,115,22,0.35)",
                "1px solid var(--input-border)",
            ),
            border_radius="12px",
            padding="0.65rem 0.9rem",
            variant="ghost",
        )

    def event_card(item, show_answer: bool = False) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.badge(item["scope"], color_scheme="orange"),
                    rx.text(item["timestamp"], color="var(--text-muted)", font_size="0.78rem"),
                    rx.spacer(),
                    rx.cond(
                        item["answer_mode_label"] != "",
                        rx.badge(item["answer_mode_label"], color_scheme="purple"),
                        rx.fragment(),
                    ),
                    rx.text(item["tenant"], color="var(--text-secondary)", font_size="0.8rem"),
                    rx.button(
                        rx.cond(
                            State.audit_expanded_event_ids.contains(item["audit_id"]),
                            "Ocultar",
                            "Mostrar",
                        ),
                        on_click=State.toggle_audit_event_expanded(item["audit_id"]),
                        size="1",
                        variant="ghost",
                        border="1px solid var(--input-border)",
                        color="var(--text-secondary)",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.text(item["event_label"], color="var(--text-primary)", font_weight="700"),
                rx.cond(
                    State.audit_expanded_event_ids.contains(item["audit_id"]),
                    rx.vstack(
                        rx.text(item["detail"], color="var(--text-secondary)", font_size="0.86rem"),
                        (
                            rx.cond(
                                item["question"] != "",
                                rx.box(
                                    rx.vstack(
                                        rx.text("Pergunta", color="var(--text-muted)", font_size="0.76rem", font_weight="600"),
                                        rx.text(item["question"], color="var(--text-primary)", font_size="0.84rem"),
                                        rx.text("Resposta", color="var(--text-muted)", font_size="0.76rem", font_weight="600"),
                                        rx.text(item["answer"], color="var(--text-secondary)", white_space="pre-wrap", font_size="0.84rem"),
                                        rx.text(
                                            f"Modo: {item['answer_mode_label']} | Prompt: {item['prompt_mode']} | Modelo: {item['model']} | Escopo: {item['assistant_scope']}",
                                            color="var(--text-muted)",
                                            font_size="0.76rem",
                                        ),
                                        rx.cond(
                                            item["sources"] != "",
                                            rx.text(
                                                f"Fontes usadas: {item['sources']}",
                                                color="var(--text-muted)",
                                                font_size="0.76rem",
                                                white_space="pre-wrap",
                                            ),
                                            rx.fragment(),
                                        ),
                                        rx.cond(
                                            item["has_traceability"] == "1",
                                            rx.badge("Com rastreabilidade", color_scheme="green"),
                                            rx.fragment(),
                                        ),
                                        rx.cond(
                                            item["has_audit_json"] == "1",
                                            rx.box(
                                                rx.vstack(
                                                    rx.text("JSON de Auditoria", color="var(--text-muted)", font_size="0.76rem", font_weight="600"),
                                                    rx.code_block(
                                                        item["audit_json"],
                                                        language="json",
                                                        width="100%",
                                                        wrap_long_lines=True,
                                                    ),
                                                    align="start",
                                                    spacing="2",
                                                    width="100%",
                                                ),
                                                width="100%",
                                                padding="0.75rem",
                                                border="1px solid var(--input-border)",
                                                border_radius="12px",
                                                bg="var(--surface-soft)",
                                            ),
                                            rx.fragment(),
                                        ),
                                        align="start",
                                        spacing="1",
                                        width="100%",
                                    ),
                                    width="100%",
                                    padding="0.75rem",
                                    border="1px solid var(--input-border)",
                                    border_radius="12px",
                                    bg="var(--surface-soft)",
                                ),
                                rx.fragment(),
                            )
                            if show_answer
                            else rx.fragment()
                        ),
                        rx.text(
                            f"Usuário: {item['user']} | Visão: {item['view']}",
                            color="var(--text-muted)",
                            font_size="0.78rem",
                        ),
                        align="start",
                        spacing="1",
                        width="100%",
                    ),
                    rx.text(
                        item["detail"],
                        color="var(--text-secondary)",
                        font_size="0.86rem",
                    ),
                ),
                align="start",
                spacing="1",
                width="100%",
            ),
            width="100%",
            padding="0.9rem",
            class_name="panel-card data-table-card",
            **CARD_STYLE,
        )

    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Auditoria", color="var(--text-primary)", size="5"),
                        rx.text(
                            "Trilha operacional local do sistema. Os eventos ficam gravados em arquivo para consulta e conferência.",
                            color="var(--text-muted)",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.badge("default", color_scheme="purple"),
                    width="100%",
                    align="center",
                ),
                rx.text(f"Arquivo de log: {State.audit_log_path_display}", color="var(--text-secondary)", font_size="0.84rem"),
                rx.hstack(
                    audit_tab_button("Visão Geral", "overview"),
                    audit_tab_button("Eventos Sistema", "system"),
                    audit_tab_button("Especialista IA", "assistant"),
                    width="100%",
                    spacing="3",
                    flex_wrap="wrap",
                ),
                rx.grid(
                    rx.select(
                        State.audit_scope_options,
                        value=State.audit_filter_scope,
                        on_change=State.set_audit_filter_scope,
                        width="100%",
                    ),
                    rx.select(
                        State.audit_event_options,
                        value=State.audit_filter_event,
                        on_change=State.set_audit_filter_event,
                        width="100%",
                    ),
                    rx.select(
                        State.audit_tenant_options,
                        value=State.audit_filter_tenant,
                        on_change=State.set_audit_filter_tenant,
                        width="100%",
                    ),
                    rx.select(
                        State.audit_user_options,
                        value=State.audit_filter_user,
                        on_change=State.set_audit_filter_user,
                        width="100%",
                    ),
                    columns="4",
                    spacing="3",
                    width="100%",
                ),
                rx.cond(
                    State.audit_active_tab == "assistant",
                    rx.grid(
                        rx.foreach(
                            State.audit_ai_summary,
                            lambda item: rx.box(
                                rx.vstack(
                                    rx.text(item["label"], color="var(--text-muted)", font_size="0.8rem"),
                                    rx.heading(item["count"], color="var(--text-primary)", size="5"),
                                    rx.text("item(ns) no filtro atual", color="var(--text-secondary)", font_size="0.8rem"),
                                    align="start",
                                    spacing="1",
                                    width="100%",
                                ),
                                padding="0.9rem",
                                class_name="panel-card metric-card",
                                **CARD_STYLE,
                            ),
                        ),
                        columns="4",
                        spacing="3",
                        width="100%",
                    ),
                    rx.cond(
                        State.audit_active_tab == "overview",
                        rx.grid(
                            rx.foreach(
                                State.audit_overview_cards,
                                lambda item: rx.box(
                                    rx.vstack(
                                        rx.text(item["label"], color="var(--text-muted)", font_size="0.8rem"),
                                        rx.heading(item["count"], color="var(--text-primary)", size="5"),
                                        rx.text("item(ns) no filtro atual", color="var(--text-secondary)", font_size="0.8rem"),
                                        align="start",
                                        spacing="1",
                                        width="100%",
                                    ),
                                    padding="0.9rem",
                                    class_name="panel-card metric-card",
                                    **CARD_STYLE,
                                ),
                            ),
                            columns="4",
                            spacing="3",
                            width="100%",
                        ),
                        rx.grid(
                            rx.foreach(
                                State.audit_theme_summary,
                                lambda item: rx.box(
                                    rx.vstack(
                                        rx.text(item["label"], color="var(--text-muted)", font_size="0.8rem"),
                                        rx.heading(item["count"], color="var(--text-primary)", size="5"),
                                        rx.text("item(ns) no filtro atual", color="var(--text-secondary)", font_size="0.8rem"),
                                        align="start",
                                        spacing="1",
                                        width="100%",
                                    ),
                                    padding="0.9rem",
                                    class_name="panel-card metric-card",
                                    **CARD_STYLE,
                                ),
                            ),
                            columns="4",
                            spacing="3",
                            width="100%",
                        ),
                    ),
                ),
                width="100%",
                spacing="3",
                align="start",
            ),
            width="100%",
            padding="1rem",
            **CARD_STYLE,
        ),
        rx.cond(
            State.audit_active_tab == "overview",
            rx.grid(
                rx.box(
                    rx.vstack(
                        rx.heading("Resumo do Workspace de Auditoria", color="var(--text-primary)", size="4"),
                        rx.text(
                            "Use esta área como hub único de rastreabilidade. A aba de sistema concentra eventos operacionais e a aba do Especialista IA centraliza perguntas, respostas, fontes, modo de resposta e payloads de auditoria.",
                            color="var(--text-secondary)",
                            font_size="0.9rem",
                        ),
                        rx.text(
                            "Filtros acima afetam todas as abas. Se quiser investigar apenas IA, mantenha a aba Especialista IA e refine por escopo, usuário e tenant.",
                            color="var(--text-muted)",
                            font_size="0.84rem",
                        ),
                        align="start",
                        spacing="2",
                        width="100%",
                    ),
                    padding="1rem",
                    width="100%",
                    **CARD_STYLE,
                ),
                rx.box(
                    rx.vstack(
                        rx.heading("Leitura Rápida", color="var(--text-primary)", size="4"),
                        rx.text(f"Eventos filtrados: {State.audit_filtered_events_data.length()}", color="var(--text-secondary)", font_size="0.88rem"),
                        rx.text(f"Eventos do sistema: {State.audit_system_events_data.length()}", color="var(--text-secondary)", font_size="0.88rem"),
                        rx.text(f"Eventos do Especialista IA: {State.audit_ai_events_data.length()}", color="var(--text-secondary)", font_size="0.88rem"),
                        rx.text(f"Arquivo base: {State.audit_log_path_display}", color="var(--text-muted)", font_size="0.8rem"),
                        align="start",
                        spacing="2",
                        width="100%",
                    ),
                    padding="1rem",
                    width="100%",
                    **CARD_STYLE,
                ),
                columns="2",
                spacing="4",
                width="100%",
            ),
            rx.cond(
                State.audit_active_tab == "system",
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.heading("Eventos do Sistema", color="var(--text-primary)", size="4"),
                            rx.spacer(),
                            rx.badge(f"{State.audit_system_events_data.length()} item(ns)", color_scheme="orange"),
                            width="100%",
                            align="center",
                        ),
                        rx.foreach(
                            State.audit_system_events_data,
                            lambda item: event_card(item, False),
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
                        rx.hstack(
                            rx.heading("Auditoria do Especialista IA", color="var(--text-primary)", size="4"),
                            rx.spacer(),
                            rx.badge(f"{State.audit_ai_events_data.length()} item(ns)", color_scheme="orange"),
                            width="100%",
                            align="center",
                        ),
                        rx.text(
                            "Aqui ficam centralizadas as interações do Especialista IA: pergunta, resposta, prompt mode, answer mode, fontes, rastreabilidade e JSON de auditoria quando existir.",
                            color="var(--text-muted)",
                            font_size="0.84rem",
                        ),
                        rx.foreach(
                            State.audit_ai_events_data,
                            lambda item: event_card(item, True),
                        ),
                        width="100%",
                        spacing="3",
                        align="start",
                    ),
                    width="100%",
                    padding="1rem",
                    **CARD_STYLE,
                ),
            ),
        ),
        width="100%",
        spacing="4",
    )


def build_dashboard_view(State, CARD_STYLE: dict[str, Any], metric_card, data_table) -> rx.Component:
    def theme_button(label: str, value: str) -> rx.Component:
        return rx.button(
            label,
            on_click=State.set_dashboard_theme_tab(value),
            bg=rx.cond(State.dashboard_theme_tab == value, "rgba(249,115,22,0.16)", "transparent"),
            color=rx.cond(State.dashboard_theme_tab == value, "var(--text-primary)", "var(--text-secondary)"),
            border=rx.cond(
                State.dashboard_theme_tab == value,
                "1px solid rgba(249,115,22,0.35)",
                "1px solid var(--input-border)",
            ),
            border_radius="12px",
            padding="0.65rem 0.9rem",
            variant="ghost",
        )

    def executive_card(item) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.text(item["label"], color="var(--text-muted)", font_size="0.8rem"),
                rx.heading(item["value"], color="var(--text-primary)", size="6"),
                rx.text(item["detail"], color="var(--text-secondary)", font_size="0.82rem"),
                align="start",
                spacing="1",
                width="100%",
            ),
            on_click=State.set_dashboard_drill_key(item["key"]),
            padding="1rem",
            class_name="panel-card metric-card",
            cursor="pointer",
            **CARD_STYLE,
        )

    def radar_panel() -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Radar de Dimensões", color="var(--text-primary)", size="4"),
                        rx.text(
                            "Compara a empresa com a área/departamento selecionado dentro do escopo ativo.",
                            color="var(--text-muted)",
                            font_size="0.84rem",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.select(
                        State.dashboard_department_options,
                        value=State.dashboard_selected_department,
                        on_change=State.set_dashboard_selected_department,
                        width="220px",
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.box(
                    rx.recharts.responsive_container(
                        rx.recharts.radar_chart(
                            rx.recharts.polar_grid(),
                            rx.recharts.polar_angle_axis(data_key="dimension"),
                            rx.recharts.polar_radius_axis(angle=30, domain=[0, 5]),
                            rx.recharts.graphing_tooltip(),
                            rx.recharts.legend(),
                            rx.recharts.radar(
                                data_key="empresa",
                                stroke="#f97316",
                                fill="#f97316",
                                fill_opacity=0.2,
                                name="Empresa",
                            ),
                            rx.recharts.radar(
                                data_key="departamento",
                                stroke="#38bdf8",
                                fill="#38bdf8",
                                fill_opacity=0.12,
                                name="Área",
                            ),
                            data=State.dashboard_dimension_compare_data,
                        ),
                        width="100%",
                        height=340,
                    ),
                    width="100%",
                    height="340px",
                ),
                width="100%",
                spacing="3",
                align="start",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        )

    def bar_panel(title: str, description: str, data_source, color: str) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.heading(title, color="var(--text-primary)", size="4"),
                rx.text(description, color="var(--text-muted)", font_size="0.84rem"),
                rx.box(
                    rx.recharts.responsive_container(
                        rx.recharts.bar_chart(
                            rx.recharts.cartesian_grid(stroke_dasharray="3 3", opacity=0.2),
                            rx.recharts.x_axis(data_key="name"),
                            rx.recharts.y_axis(),
                            rx.recharts.graphing_tooltip(),
                            rx.recharts.legend(),
                            rx.recharts.bar(data_key="value", fill=color, radius=6),
                            data=data_source,
                        ),
                        width="100%",
                        height=320,
                    ),
                    width="100%",
                    height="320px",
                ),
                width="100%",
                spacing="2",
                align="start",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        )

    def line_panel(title: str, description: str, data_source, color: str) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.heading(title, color="var(--text-primary)", size="4"),
                rx.text(description, color="var(--text-muted)", font_size="0.84rem"),
                rx.box(
                    rx.recharts.responsive_container(
                        rx.recharts.line_chart(
                            rx.recharts.cartesian_grid(stroke_dasharray="3 3", opacity=0.2),
                            rx.recharts.x_axis(data_key="name"),
                            rx.recharts.y_axis(),
                            rx.recharts.graphing_tooltip(),
                            rx.recharts.legend(),
                            rx.recharts.line(
                                type_="monotone",
                                data_key="value",
                                stroke=color,
                                stroke_width=3,
                                dot=True,
                                name="Série",
                            ),
                            data=data_source,
                        ),
                        width="100%",
                        height=320,
                    ),
                    width="100%",
                    height="320px",
                ),
                width="100%",
                spacing="2",
                align="start",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        )

    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Dashboard SmartLab SaaS", color="var(--text-primary)", size="5"),
                        rx.text(
                            "Monitore a operação por workspace atual, grupo do cliente ou workspace default, sempre respeitando o escopo do usuário logado.",
                            color="var(--text-muted)",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.badge(State.dashboard_scope_summary["label"], color_scheme="orange"),
                    rx.badge(f'{State.dashboard_scope_summary["tenants_count"]} workspace(s)', color_scheme="purple"),
                    rx.badge(State.dashboard_filter_summary["periodo"], color_scheme="blue"),
                    rx.badge(State.dashboard_filter_summary["cliente"], color_scheme="green"),
                    width="100%",
                    align="center",
                ),
                rx.grid(
                    rx.select(
                        State.dashboard_scope_options,
                        value=State.dashboard_scope_mode,
                        on_change=State.set_dashboard_scope_mode,
                        width="100%",
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.select(
                        State.dashboard_period_options,
                        value=State.dashboard_period_mode,
                        on_change=State.set_dashboard_period_mode,
                        width="100%",
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.select(
                        State.dashboard_project_options,
                        value=State.dashboard_selected_project_option,
                        on_change=State.set_dashboard_selected_project,
                        width="100%",
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.select(
                        State.dashboard_client_options,
                        value=State.dashboard_selected_client_option,
                        on_change=State.set_dashboard_selected_client,
                        width="100%",
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.select(
                        State.dashboard_service_options,
                        value=State.dashboard_selected_service_name,
                        on_change=State.set_dashboard_selected_service,
                        width="100%",
                        bg="var(--input-bg)",
                        color="var(--text-primary)",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text(
                                f'Tenants no recorte: {State.dashboard_scope_summary["tenants"]}',
                                color="var(--text-secondary)",
                                font_size="0.84rem",
                            ),
                            rx.text(
                                f'Projeto: {State.dashboard_filter_summary["projeto"]}',
                                color="var(--text-muted)",
                                font_size="0.8rem",
                            ),
                            rx.text(
                                f'Serviço: {State.dashboard_filter_summary["servico"]}',
                                color="var(--text-muted)",
                                font_size="0.8rem",
                            ),
                            align="start",
                            spacing="1",
                        ),
                        padding="0.8rem 1rem",
                        border="1px solid var(--input-border)",
                        border_radius="12px",
                        bg="var(--surface-soft)",
                        width="100%",
                    ),
                    columns="6",
                    spacing="3",
                    width="100%",
                ),
                rx.hstack(
                    theme_button("Executivo", "executive"),
                    theme_button("Diagnóstico", "diagnosis"),
                    theme_button("Operacional", "operational"),
                    theme_button("Engajamento", "engagement"),
                    theme_button("Projetos", "projects"),
                    width="100%",
                    spacing="3",
                    flex_wrap="wrap",
                ),
                width="100%",
                spacing="3",
                align="start",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        ),
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
            metric_card("Workspaces", State.dashboard_metrics["workspaces"]),
            metric_card("Clientes", State.dashboard_metrics["clientes"]),
            metric_card("Formulários", State.dashboard_metrics["formularios"]),
            metric_card("Forms Respondidos", State.dashboard_metrics["formularios_respondidos"]),
            metric_card("Respostas", State.dashboard_metrics["respostas"]),
            metric_card("Média Dashboard", State.dashboard_metrics["media_dashboard"]),
            metric_card("Média Respostas", State.dashboard_metrics["media_respostas"]),
            columns="7",
            spacing="4",
            width="100%",
        ),
        data_table(
            ["Workspace", "Clientes", "Formulários", "Respondidos", "Respostas", "Média Dashboard", "Média Respostas"],
            State.dashboard_workspace_rollup,
            lambda item: rx.hstack(
                rx.text(item["workspace"], color="var(--text-primary)", width="100%"),
                rx.text(item["clientes"], color="var(--text-secondary)", width="100%"),
                rx.text(item["formularios"], color="var(--text-secondary)", width="100%"),
                rx.text(item["formularios_respondidos"], color="var(--text-secondary)", width="100%"),
                rx.text(item["respostas"], color="var(--text-secondary)", width="100%"),
                rx.text(item["media_dashboard"], color="#f59e0b", width="100%"),
                rx.text(item["media_respostas"], color="#34d399", width="100%"),
                width="100%",
            ),
        ),
        rx.grid(
            rx.cond(
                State.dashboard_theme_tab == "executive",
                rx.vstack(
                    rx.grid(
                        rx.foreach(State.dashboard_executive_cards, executive_card),
                        columns="4",
                        spacing="4",
                        width="100%",
                    ),
                    rx.grid(
                        radar_panel(),
                        rx.vstack(
                            rx.vstack(
                                rx.heading("Dimensões Prioritárias", color="var(--text-primary)", size="4"),
                                rx.text(
                                    "Leitura rápida por dimensão para apoiar o board executivo e priorizar decisões.",
                                    color="var(--text-muted)",
                                    font_size="0.84rem",
                                ),
                                rx.vstack(
                                    rx.foreach(
                                        State.dashboard_dimension_cards,
                                        lambda item: rx.box(
                                            rx.hstack(
                                                rx.vstack(
                                                    rx.text(item["dimension"], color="var(--text-primary)", font_weight="600"),
                                                    rx.text(f'Score {item["score"]}', color="var(--text-secondary)", font_size="0.82rem"),
                                                    align="start",
                                                    spacing="0",
                                                ),
                                                rx.spacer(),
                                                rx.badge(
                                                    item["status"],
                                                    color_scheme=rx.cond(
                                                        item["status"] == "Forte",
                                                        "green",
                                                        rx.cond(item["status"] == "Crítico", "red", "orange"),
                                                    ),
                                                ),
                                                width="100%",
                                                align="center",
                                            ),
                                            on_click=State.set_dashboard_drill_key(item["key"]),
                                            width="100%",
                                            padding="0.8rem",
                                            border="1px solid var(--input-border)",
                                            border_radius="12px",
                                            bg="var(--surface-soft)",
                                            cursor="pointer",
                                        ),
                                    ),
                                    width="100%",
                                    spacing="2",
                                    align="start",
                                ),
                                align="start",
                                width="100%",
                                spacing="2",
                            ),
                            line_panel(
                                "Evolução do Score",
                                "Média temporal das respostas válidas no recorte ativo.",
                                State.dashboard_executive_timeline_data,
                                "#f97316",
                            ),
                            padding="1rem",
                            width="100%",
                            spacing="4",
                            **CARD_STYLE,
                        ),
                        columns="2",
                        spacing="4",
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),
                rx.cond(
                    State.dashboard_theme_tab == "diagnosis",
                    rx.vstack(
                        rx.grid(
                            rx.foreach(State.dashboard_diagnosis_cards, executive_card),
                            columns="4",
                            spacing="4",
                            width="100%",
                        ),
                        bar_panel(
                            "Leitura Diagnóstica",
                            "Distribuição do score médio por dimensão para apoiar decisões de profundidade.",
                            State.dashboard_diagnosis_chart_data,
                            "#f59e0b",
                        ),
                        data_table(
                            ["Workspace", "Formulário", "Categoria", "Respostas", "Média", "Status"],
                            State.dashboard_table,
                            lambda r: rx.hstack(
                                rx.text(r["workspace"], color="var(--text-secondary)", width="100%"),
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
                    ),
                    rx.cond(
                        State.dashboard_theme_tab == "operational",
                        rx.vstack(
                            rx.grid(
                                rx.foreach(State.dashboard_operational_cards, executive_card),
                                columns="4",
                                spacing="4",
                                width="100%",
                            ),
                            bar_panel(
                                "Saúde Operacional",
                                "Backlog, prazos e execução das tarefas e planos em aberto.",
                                State.dashboard_operational_chart_data,
                                "#f97316",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        rx.cond(
                            State.dashboard_theme_tab == "engagement",
                            rx.vstack(
                                rx.grid(
                                    rx.foreach(State.dashboard_engagement_cards, executive_card),
                                    columns="3",
                                    spacing="4",
                                    width="100%",
                                ),
                                bar_panel(
                                    "Cobertura e Engajamento",
                                    "Indicadores de adesão das lideranças e execução das frentes de campo.",
                                    State.dashboard_engagement_chart_data,
                                    "#38bdf8",
                                ),
                                spacing="4",
                                width="100%",
                            ),
                            rx.vstack(
                                rx.grid(
                                    rx.foreach(State.dashboard_projects_cards, executive_card),
                                    columns="4",
                                    spacing="4",
                                    width="100%",
                                ),
                            bar_panel(
                                "Portfólio de Projetos",
                                "Visão executiva de status e concentração do portfólio no recorte ativo.",
                                State.dashboard_projects_chart_data,
                                "#34d399",
                            ),
                            line_panel(
                                "Linha do Tempo de Projetos",
                                "Quantidade de projetos por mês considerando contratação ou criação.",
                                State.dashboard_projects_timeline_data,
                                "#10b981",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        ),
                    ),
                ),
            ),
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.heading(State.dashboard_detail_title, color="var(--text-primary)", size="4"),
                            rx.text(
                                "Painel lateral do recorte ativo. Use os cards e dimensões para trocar o foco da análise.",
                                color="var(--text-muted)",
                                font_size="0.84rem",
                            ),
                            align="start",
                            spacing="1",
                        ),
                        rx.spacer(),
                        rx.badge(State.dashboard_theme_tab, color_scheme="orange"),
                        width="100%",
                        align="center",
                    ),
                    data_table(
                        ["Item", "Contexto", "Métrica", "Detalhe", "Status"],
                        State.dashboard_detail_rows,
                        lambda item: rx.hstack(
                            rx.text(item["primary"], color="var(--text-primary)", width="100%"),
                            rx.text(item["secondary"], color="var(--text-secondary)", width="100%"),
                            rx.text(item["metric"], color="#f59e0b", width="100%"),
                            rx.text(item["detail"], color="var(--text-secondary)", width="100%"),
                            rx.badge(
                                item["status"],
                                color_scheme=rx.cond(
                                    (item["status"] == "Forte") | (item["status"] == "Alta") | (item["status"] == "Concluída"),
                                    "green",
                                    rx.cond(
                                        (item["status"] == "Crítico") | (item["status"] == "Baixa") | (item["status"] == "Atrasada"),
                                        "red",
                                        "orange",
                                    ),
                                ),
                                width="fit-content",
                            ),
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="3",
                    align="start",
                ),
                padding="1rem",
                width="100%",
                **CARD_STYLE,
            ),
            columns="2",
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
        spacing="4",
        width="100%",
    )


def build_planos_view(State, CARD_STYLE: dict[str, Any]) -> rx.Component:
    primary_button_style = {
        "bg": "rgba(255,122,47,0.18)",
        "color": "#fdba74",
        "border": "1px solid rgba(255,122,47,0.38)",
        "size": "2",
    }
    secondary_button_style = {
        "bg": "rgba(245,158,11,0.14)",
        "color": "#fcd34d",
        "border": "1px solid rgba(245,158,11,0.34)",
        "size": "2",
    }
    danger_button_style = {
        "bg": "rgba(239,68,68,0.2)",
        "color": "#fca5a5",
        "border": "1px solid rgba(239,68,68,0.4)",
        "size": "2",
    }

    def progress_bar(value: rx.Var, accent: str) -> rx.Component:
        return rx.box(
            rx.box(
                height="8px",
                border_radius="999px",
                bg=accent,
                width=f"{value}%",
                transition="width 160ms ease",
            ),
            width="100%",
            height="8px",
            border_radius="999px",
            bg="rgba(148,163,184,0.18)",
            overflow="hidden",
        )

    def action_card(action: dict[str, Any]) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(action["title"], color="var(--text-primary)", font_weight="700"),
                    rx.spacer(),
                    rx.badge(f"Tarefa #{action['id']}", color_scheme="gray", variant="soft"),
                    width="100%",
                    align="center",
                ),
                rx.text("Hierarquia: Projeto > Plano > Tarefas", color="var(--text-muted)", font_size="0.76rem"),
                rx.text(f"Projeto: {action['project_name']}", color="var(--text-secondary)", font_size="0.83rem"),
                rx.text(f"Plano: {action['plan_title']}", color="var(--text-secondary)", font_size="0.83rem"),
                rx.text(f"Serviço: {action['service_name']}", color="var(--text-secondary)", font_size="0.83rem"),
                rx.text(f"Cliente: {action['client_name']}", color="var(--text-secondary)", font_size="0.83rem"),
                rx.text(f"Responsável: {action['owner']}", color="var(--text-secondary)", font_size="0.85rem"),
                rx.text(f"Dimensões: {action['dimensions']}", color="var(--text-secondary)", font_size="0.83rem"),
                rx.text(
                    rx.cond(
                        action["expected_result"] != "",
                        f"Resultado esperado: {action['expected_result']}",
                        "Resultado esperado: -",
                    ),
                    color="var(--text-secondary)",
                    font_size="0.83rem",
                ),
                rx.grid(
                    rx.text(f"Início: {action['start_date']}", color="var(--text-muted)", font_size="0.8rem"),
                    rx.text(f"Prazo base: {action['planned_due_date']}", color="var(--text-muted)", font_size="0.8rem"),
                    rx.text(f"Fim atual: {action['due_date']}", color="var(--text-muted)", font_size="0.8rem"),
                    rx.text(f"Alterações de prazo: {action['due_date_change_count']}", color="var(--text-muted)", font_size="0.8rem"),
                    columns="2",
                    spacing="2",
                    width="100%",
                ),
                rx.text(f"Leitura do prazo: {action['delay_label']}", color="var(--accent-strong)", font_size="0.82rem"),
                rx.vstack(
                    rx.text(f"Progresso: {action['progress']}%", color="var(--text-primary)", font_size="0.82rem", font_weight="600"),
                    progress_bar(action["progress"], "linear-gradient(90deg, #fb923c, #f59e0b)"),
                    rx.text(f"Calendário: {action['schedule_progress']}%", color="var(--text-muted)", font_size="0.78rem"),
                    width="100%",
                    spacing="1",
                    align="start",
                ),
                rx.hstack(
                    rx.button("A Fazer", on_click=State.update_action_task_progress(action["action_id"], action["id"], 0), size="1", variant="ghost", border="1px solid var(--input-border)"),
                    rx.button("Andamento", on_click=State.update_action_task_progress(action["action_id"], action["id"], 50), size="1", variant="ghost", border="1px solid var(--input-border)"),
                    rx.button(
                        "Concluído",
                        on_click=State.update_action_task_progress(action["action_id"], action["id"], 100),
                        size="1",
                        bg="rgba(34,197,94,0.2)",
                        color="#86efac",
                        border="1px solid rgba(34,197,94,0.4)",
                    ),
                    spacing="1",
                    width="100%",
                    flex_wrap="wrap",
                ),
                rx.hstack(
                    rx.button("-7 dias", on_click=State.shift_action_task_due_date(action["id"], -7), size="1", variant="ghost", border="1px solid var(--input-border)"),
                    rx.button("+7 dias", on_click=State.shift_action_task_due_date(action["id"], 7), size="1", variant="ghost", border="1px solid var(--input-border)"),
                    spacing="2",
                    width="100%",
                    flex_wrap="wrap",
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
                rx.hstack(rx.text(title, color="var(--text-primary)", font_weight="700"), width="100%"),
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
                    width="420px",
                    max_width="100%",
                ),
                rx.text(State.selected_project_plan_context, color="var(--text-muted)", font_size="0.82rem"),
                rx.text(
                    "Estrutura operacional: um Projeto pode ter vários Planos, e cada Plano pode ter várias Tarefas.",
                    color="var(--text-secondary)",
                    font_size="0.82rem",
                ),
                rx.cond(
                    State.action_plan_options.length() > 0,
                    rx.hstack(
                        rx.select(
                            State.action_plan_options,
                            value=State.selected_action_plan_option,
                            on_change=State.set_selected_action_plan_option,
                            placeholder="Selecione um plano existente",
                            width="420px",
                            max_width="100%",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                        ),
                        rx.button("Alterar", on_click=State.start_edit_action_plan, **primary_button_style),
                        rx.button(
                            "Excluir",
                            on_click=State.request_delete_confirmation("action_plan", State.effective_action_plan_target_id, State.effective_action_plan_target_label),
                            **danger_button_style,
                        ),
                        rx.button("Cancelar", on_click=State.cancel_edit_action_plan, **secondary_button_style),
                        width="100%",
                        spacing="3",
                        flex_wrap="wrap",
                    ),
                    rx.fragment(),
                ),
                rx.grid(
                    rx.foreach(
                        State.action_plan_summary_cards,
                        lambda item: rx.box(
                            rx.vstack(
                                rx.text(item["label"], color="var(--text-muted)", font_size="0.78rem"),
                                rx.text(item["value"], color="var(--text-primary)", font_weight="700"),
                                rx.text(item["detail"], color="var(--text-secondary)", font_size="0.8rem"),
                                align="start",
                                spacing="1",
                                width="100%",
                            ),
                            padding="0.8rem",
                            border="1px solid rgba(148,163,184,0.16)",
                            border_radius="14px",
                            bg="var(--surface-soft)",
                            width="100%",
                        ),
                    ),
                    columns=rx.breakpoints(initial="1", md="2", xl="4"),
                    spacing="3",
                    width="100%",
                ),
                rx.grid(
                    rx.box(
                        rx.vstack(
                            rx.heading("Criar ou Alterar Plano", color="var(--text-primary)", size="4"),
                            rx.vstack(
                                rx.text("Qual ação?", color="var(--text-muted)", font_size="0.8rem"),
                                rx.input(
                                    placeholder="Descreva o plano de ação",
                                    value=State.new_action_title,
                                    on_change=State.set_new_action_title,
                                    bg="var(--input-bg)",
                                    color="var(--text-primary)",
                                    width="100%",
                                ),
                                width="100%",
                                spacing="1",
                            ),
                            rx.grid(
                                rx.vstack(
                                    rx.text("Para qual área?", color="var(--text-muted)", font_size="0.8rem"),
                                    rx.select(
                                        State.project_action_area_options,
                                        value=State.new_action_area,
                                        on_change=State.set_new_action_area,
                                        placeholder="Selecione a área",
                                        bg="var(--input-bg)",
                                        color="var(--text-primary)",
                                        width="100%",
                                    ),
                                    width="100%",
                                    spacing="1",
                                ),
                                rx.vstack(
                                    rx.text("Responsável", color="var(--text-muted)", font_size="0.8rem"),
                                    rx.select(
                                        State.project_action_owner_options,
                                        value=State.new_action_owner,
                                        on_change=State.set_new_action_owner,
                                        placeholder="Selecione o responsável",
                                        bg="var(--input-bg)",
                                        color="var(--text-primary)",
                                        width="100%",
                                    ),
                                    width="100%",
                                    spacing="1",
                                ),
                                columns=rx.breakpoints(initial="1", md="2"),
                                width="100%",
                                spacing="3",
                            ),
                            rx.hstack(
                                rx.vstack(
                                    rx.text("Data de Início", color="var(--text-muted)", font_size="0.8rem"),
                                    rx.input(type="date", value=State.new_action_start_date, on_change=State.set_new_action_start_date, bg="var(--input-bg)", color="var(--text-primary)", width="170px"),
                                    spacing="1",
                                    align="start",
                                ),
                                rx.vstack(
                                    rx.text("Prazo Base", color="var(--text-muted)", font_size="0.8rem"),
                                    rx.input(type="date", value=State.new_action_planned_due_date, on_change=State.set_new_action_planned_due_date, bg="var(--input-bg)", color="var(--text-primary)", width="170px"),
                                    spacing="1",
                                    align="start",
                                ),
                                rx.vstack(
                                    rx.text("Data Final Atual", color="var(--text-muted)", font_size="0.8rem"),
                                    rx.input(type="date", value=State.new_action_due_date, on_change=State.set_new_action_due_date, bg="var(--input-bg)", color="var(--text-primary)", width="170px"),
                                    spacing="1",
                                    align="start",
                                ),
                                width="100%",
                                spacing="3",
                                flex_wrap="wrap",
                            ),
                            rx.vstack(
                                rx.text("Descreva o resultado esperado", color="var(--text-muted)", font_size="0.8rem"),
                                rx.text_area(
                                    placeholder="Descreva o resultado esperado do plano",
                                    value=State.new_action_expected_result,
                                    on_change=State.set_new_action_expected_result,
                                    bg="var(--input-bg)",
                                    color="var(--text-primary)",
                                    min_height="110px",
                                    width="100%",
                                ),
                                width="100%",
                                spacing="1",
                            ),
                            rx.box(
                                rx.vstack(
                                    rx.text("Dimensões impactadas", color="var(--text-primary)", font_weight="600"),
                                    rx.text(State.selected_action_dimensions_summary, color="var(--text-muted)", font_size="0.8rem"),
                                    rx.flex(
                                        rx.foreach(
                                            State.action_dimension_options,
                                            lambda dimension: rx.button(
                                                dimension,
                                                on_click=State.toggle_new_action_dimension(dimension),
                                                bg=rx.cond(State.new_action_dimension_ids.contains(dimension), "rgba(255,122,47,0.18)", "transparent"),
                                                color=rx.cond(State.new_action_dimension_ids.contains(dimension), "#fdba74", "var(--text-secondary)"),
                                                border=rx.cond(
                                                    State.new_action_dimension_ids.contains(dimension),
                                                    "1px solid rgba(255,122,47,0.38)",
                                                    "1px solid var(--input-border)",
                                                ),
                                                size="1",
                                            ),
                                        ),
                                        spacing="2",
                                        wrap="wrap",
                                        width="100%",
                                    ),
                                    spacing="2",
                                    width="100%",
                                    align="start",
                                ),
                                width="100%",
                                padding="0.9rem",
                                border="1px solid rgba(148,163,184,0.16)",
                                border_radius="14px",
                                bg="var(--surface-soft)",
                            ),
                            rx.hstack(
                                rx.button(
                                    rx.cond(State.editing_action_plan_id != "", "Salvar Plano", "Criar Plano de Ação"),
                                    on_click=State.create_action_plan,
                                    **primary_button_style,
                                ),
                                rx.button("Cancelar", on_click=State.cancel_edit_action_plan, **secondary_button_style),
                                rx.button(
                                    "Excluir",
                                    on_click=State.request_delete_confirmation("action_plan", State.effective_action_plan_target_id, State.effective_action_plan_target_label),
                                    **danger_button_style,
                                ),
                                width="100%",
                                spacing="3",
                                flex_wrap="wrap",
                            ),
                            spacing="3",
                            width="100%",
                            align="start",
                        ),
                        width="100%",
                        padding="1rem",
                        border="1px solid rgba(148,163,184,0.16)",
                        border_radius="16px",
                        bg="var(--surface-soft)",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.heading("Criar Tarefa do Plano Selecionado", color="var(--text-primary)", size="4"),
                            rx.text(
                                rx.cond(
                                    (State.editing_action_plan_id != "") | (State.selected_action_plan_id != ""),
                                    "A tarefa será vinculada automaticamente ao plano selecionado e entrará no kanban em A Fazer.",
                                    "Selecione ou salve um plano para liberar a criação de tarefas.",
                                ),
                                color="var(--text-muted)",
                                font_size="0.82rem",
                            ),
                            rx.cond(
                                (State.editing_action_plan_id != "") | (State.selected_action_plan_id != ""),
                                rx.fragment(),
                                rx.badge("Plano ainda não selecionado", color_scheme="orange", variant="soft"),
                            ),
                            rx.vstack(
                                rx.vstack(
                                    rx.text("Qual tarefa?", color="var(--text-muted)", font_size="0.8rem"),
                                    rx.input(
                                        placeholder="Descreva a tarefa",
                                        value=State.new_action_task_title,
                                        on_change=State.set_new_action_task_title,
                                        bg="var(--input-bg)",
                                        color="var(--text-primary)",
                                        width="100%",
                                    ),
                                    width="100%",
                                    spacing="1",
                                ),
                                rx.grid(
                                    rx.vstack(
                                        rx.text("Quem fará?", color="var(--text-muted)", font_size="0.8rem"),
                                        rx.select(
                                            State.project_action_owner_options,
                                            value=State.new_action_task_owner,
                                            on_change=State.set_new_action_task_owner,
                                            placeholder="Selecione o executor",
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            width="100%",
                                        ),
                                        width="100%",
                                        spacing="1",
                                    ),
                                    rx.vstack(
                                        rx.text("Início da Tarefa", color="var(--text-muted)", font_size="0.8rem"),
                                        rx.input(type="date", value=State.new_action_task_start_date, on_change=State.set_new_action_task_start_date, bg="var(--input-bg)", color="var(--text-primary)", width="170px"),
                                        spacing="1",
                                        align="start",
                                    ),
                                    rx.vstack(
                                        rx.text("Prazo Base da Tarefa", color="var(--text-muted)", font_size="0.8rem"),
                                        rx.input(type="date", value=State.new_action_task_planned_due_date, on_change=State.set_new_action_task_planned_due_date, bg="var(--input-bg)", color="var(--text-primary)", width="170px"),
                                        spacing="1",
                                        align="start",
                                    ),
                                    rx.vstack(
                                        rx.text("Fim Atual da Tarefa", color="var(--text-muted)", font_size="0.8rem"),
                                        rx.input(type="date", value=State.new_action_task_due_date, on_change=State.set_new_action_task_due_date, bg="var(--input-bg)", color="var(--text-primary)", width="170px"),
                                        spacing="1",
                                        align="start",
                                    ),
                                    columns=rx.breakpoints(initial="1", md="2"),
                                    spacing="3",
                                    width="100%",
                                ),
                                rx.vstack(
                                    rx.text("Descreva o resultado esperado", color="var(--text-muted)", font_size="0.8rem"),
                                    rx.text_area(
                                        placeholder="Descreva o resultado esperado da tarefa",
                                        value=State.new_action_task_expected_result,
                                        on_change=State.set_new_action_task_expected_result,
                                        bg="var(--input-bg)",
                                        color="var(--text-primary)",
                                        min_height="110px",
                                        width="100%",
                                    ),
                                    width="100%",
                                    spacing="1",
                                ),
                                rx.hstack(
                                    rx.button("Criar Tarefa e enviar ao Kanban", on_click=State.create_action_task, **primary_button_style),
                                    rx.button("Cancelar", on_click=State.reset_action_task_form, **secondary_button_style),
                                    width="100%",
                                    spacing="3",
                                    flex_wrap="wrap",
                                ),
                                spacing="3",
                                width="100%",
                                align="start",
                            ),
                            spacing="3",
                            width="100%",
                            align="start",
                        ),
                        width="100%",
                        padding="1rem",
                        border="1px solid rgba(148,163,184,0.16)",
                        border_radius="16px",
                        bg="var(--surface-soft)",
                    ),
                    columns=rx.breakpoints(initial="1", xl="2"),
                    spacing="4",
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
            kanban_col("A Fazer", State.actions_todo),
            kanban_col("Em Andamento", State.actions_doing),
            kanban_col("Concluído", State.actions_done),
            columns=rx.breakpoints(initial="1", lg="3"),
            spacing="3",
            width="100%",
        ),
        width="100%",
        spacing="4",
    )
