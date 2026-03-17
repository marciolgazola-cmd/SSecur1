from typing import Any

import reflex as rx


def build_formularios_view(
    State,
    CARD_STYLE: dict[str, Any],
    metric_card,
    field_block,
    table_text_cell,
    data_table,
) -> rx.Component:
    interview_table_headers = ["ID", "Pesquisa", "Etapa", "Projeto", "Cliente", "Entrevistado", "Data", "Status", "Respostas", "Score Total", "Ações"]
    interview_grid_template = "58px minmax(180px,1.3fr) minmax(150px,1fr) minmax(150px,1fr) minmax(130px,0.95fr) minmax(150px,1fr) 118px 104px 84px 96px minmax(132px,0.95fr)"

    def interview_table_cell(*children: rx.Component) -> rx.Component:
        return rx.vstack(
            *children,
            spacing="1",
            align="start",
            justify="center",
            text_align="left",
            width="100%",
            min_height="100%",
        )

    dimension_columns = [
        ("Presença", "rgba(251,146,60,0.62)"),
        ("Correção", "rgba(14,165,233,0.62)"),
        ("Reconhecimento", "rgba(168,85,247,0.62)"),
        ("Comunicação", "rgba(34,197,94,0.62)"),
        ("Disciplina/Exemplo", "rgba(244,63,94,0.62)"),
    ]

    def interview_metric_card(title: str, value: rx.Var, icon_tag: str, accent_color: str) -> rx.Component:
        return rx.box(
            rx.hstack(
                rx.flex(
                    rx.icon(tag=icon_tag, size=18, color=accent_color),
                    align="center",
                    justify="center",
                    width="42px",
                    height="42px",
                    border_radius="14px",
                    bg=f"color-mix(in srgb, {accent_color} 16%, transparent)",
                    border=f"1px solid color-mix(in srgb, {accent_color} 34%, transparent)",
                    flex_shrink="0",
                ),
                rx.vstack(
                    rx.text(title, color="var(--text-muted)", font_size="0.78rem"),
                    rx.heading(value, color="var(--text-primary)", size="6"),
                    align="start",
                    spacing="0",
                ),
                align="center",
                spacing="3",
                width="100%",
            ),
            padding="1rem",
            border="1px solid var(--card-border)",
            border_radius="14px",
            bg="color-mix(in srgb, var(--card-bg, rgba(15,23,42,0.88)) 88%, transparent)",
            width="100%",
        )

    def dimension_status_badges(dimension: str) -> rx.Component:
        return rx.foreach(
            State.active_interview_dimension_diagnostics,
            lambda item: rx.cond(
                item["dimension"] == dimension,
                rx.hstack(
                    rx.badge(f'Pontuação {item["score"]}', color_scheme="orange"),
                    rx.badge(
                        item["maturity"],
                        color_scheme=rx.cond(
                            item["maturity"] == "Reativo",
                            "red",
                            rx.cond(
                                item["maturity"] == "Dependente",
                                "orange",
                                rx.cond(item["maturity"] == "Independente", "blue", "green"),
                            ),
                        ),
                    ),
                    rx.badge(f'{item["responses"]} respostas', color_scheme="gray"),
                    spacing="2",
                    flex_wrap="wrap",
                    width="100%",
                ),
                rx.fragment(),
            ),
        )

    def interview_question_card(question: dict[str, str]) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.badge(question["polarity"], color_scheme=rx.cond(question["polarity"] == "negativa", "red", "green")),
                    rx.badge(f'Peso {question["weight"]}', color_scheme="gray"),
                    rx.spacer(),
                    rx.badge(f'Nota {question["score"]}', color_scheme="orange"),
                    spacing="2",
                    width="100%",
                    align="center",
                    flex_wrap="wrap",
                ),
                rx.text(
                    question["text"],
                    color="var(--text-primary)",
                    font_weight="700",
                    width="100%",
                    white_space="normal",
                    word_break="break-word",
                    line_height="1.45",
                ),
                rx.vstack(
                    rx.input(
                        type="range",
                        min="0",
                        max="5",
                        step="1",
                        value=question["score"],
                        on_change=State.set_interview_score(question["id"]),
                        width="100%",
                        accent_color="var(--accent-strong)",
                    ),
                    rx.hstack(
                        rx.text("0", color="var(--text-muted)", font_size="0.78rem"),
                        rx.text("1", color="var(--text-muted)", font_size="0.78rem"),
                        rx.text("2", color="var(--text-muted)", font_size="0.78rem"),
                        rx.text("3", color="var(--text-muted)", font_size="0.78rem"),
                        rx.text("4", color="var(--text-muted)", font_size="0.78rem"),
                        rx.text("5", color="var(--text-muted)", font_size="0.78rem"),
                        justify="between",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.text_area(
                    placeholder="Registro literal da resposta, evidências e exemplos observados",
                    value=question["answer"],
                    on_change=State.set_interview_answer(question["id"]),
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                    min_height="116px",
                    width="100%",
                    resize="vertical",
                ),
                rx.cond(
                    question["logic_rule"] != "",
                    rx.text(
                        f'Logica: {question["logic_rule"]}',
                        color="var(--text-muted)",
                        font_size="0.78rem",
                        width="100%",
                        white_space="normal",
                        word_break="break-word",
                    ),
                    rx.fragment(),
                ),
                align="start",
                spacing="2",
                width="100%",
            ),
            width="100%",
            padding="0.95rem",
            border="1px solid var(--kanban-card-border)",
            border_radius="18px",
            bg="var(--kanban-card-bg)",
            box_shadow="var(--kanban-card-shadow)",
            transition="transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease",
            _hover={
                "transform": "translateY(-4px)",
                "border_color": "var(--kanban-card-hover-border)",
                "box_shadow": "var(--kanban-card-hover-shadow)",
                "background": "var(--kanban-card-hover-bg)",
            },
        )

    def dimension_kanban_column(dimension: str, accent_color: str) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.vstack(
                    rx.text(dimension, color="var(--text-primary)", font_size="1rem", font_weight="700", width="100%"),
                    rx.text(
                        "Pontuacao viva da dimensao conforme a entrevista avanca.",
                        color="var(--text-muted)",
                        font_size="0.78rem",
                        width="100%",
                    ),
                    dimension_status_badges(dimension),
                    align="start",
                    spacing="2",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.foreach(
                            State.active_interview_questions,
                            lambda question: rx.cond(
                                question["dimension"] == dimension,
                                interview_question_card(question),
                                rx.fragment(),
                            ),
                        ),
                        align="start",
                        spacing="3",
                        width="100%",
                    ),
                    width="100%",
                    max_height="68vh",
                    overflow_y="auto",
                    padding_right="0.2rem",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            width="340px",
            min_width="340px",
            max_width="340px",
            padding="1rem",
            border="1px solid var(--card-border)",
            border_top=f"4px solid {accent_color}",
            border_radius="22px",
            bg="var(--kanban-column-bg)",
            box_shadow="var(--kanban-column-shadow)",
            backdrop_filter="blur(10px)",
        )

    return rx.vstack(
        rx.cond(
            State.can_operate_interviews,
            rx.vstack(
                rx.grid(
                    rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.vstack(
                                    rx.heading("Abrir Entrevista", color="var(--text-primary)", size="5"),
                                    rx.text(
                                        "Selecione a pesquisa, o cliente e o usuario cadastrado. A abertura fica curta e o preenchimento acontece no kanban abaixo.",
                                        color="var(--text-muted)",
                                        font_size="0.9rem",
                                        width="100%",
                                    ),
                                    align="start",
                                    spacing="1",
                                    width="100%",
                                ),
                                rx.badge("Operacao de campo", color_scheme="orange"),
                                width="100%",
                                align="start",
                            ),
                            rx.grid(
                                field_block(
                                    "Projeto Contratado",
                                    rx.select(
                                        State.interview_project_options,
                                        value=State.selected_interview_project_option,
                                        on_change=State.set_new_interview_project_option,
                                        placeholder="Projeto vinculado ao cliente",
                                        bg="var(--input-bg)",
                                        color="var(--text-primary)",
                                        width="100%",
                                    ),
                                ),
                                field_block(
                                    "Cliente",
                                    rx.input(
                                        value=State.selected_interview_client_name,
                                        read_only=True,
                                        bg="var(--surface-soft)",
                                        color="var(--text-primary)",
                                        width="100%",
                                    ),
                                    "Preenchido automaticamente a partir do projeto contratado.",
                                ),
                                columns="2",
                                spacing="3",
                                width="100%",
                            ),
                            rx.grid(
                                field_block(
                                    "Pesquisa",
                                    rx.select(
                                        State.interview_form_options,
                                        value=State.selected_interview_form_option,
                                        on_change=State.set_new_interview_form_option,
                                        placeholder="Pesquisa da SmartLab vinculada ao serviço do projeto",
                                        bg="var(--input-bg)",
                                        color="var(--text-primary)",
                                        width="100%",
                                    ),
                                ),
                                field_block(
                                    "Etapa",
                                    rx.input(
                                        value=State.selected_interview_stage_name,
                                        read_only=True,
                                        bg="var(--surface-soft)",
                                        color="var(--text-primary)",
                                        width="100%",
                                    ),
                                    "Derivada automaticamente do formulário selecionado.",
                                ),
                                columns="2",
                                spacing="3",
                                width="100%",
                            ),
                            rx.grid(
                                field_block(
                                    "Data da Aplicacao em Campo",
                                    rx.input(
                                        type="date",
                                        value=State.new_interview_date,
                                        on_change=State.set_new_interview_date,
                                        bg="var(--input-bg)",
                                        color="var(--text-primary)",
                                        width="100%",
                                    ),
                                    "Registre a data em que a aplicação ocorreu, não a data de criação da pesquisa.",
                                ),
                                field_block(
                                    "Observacoes Iniciais",
                                    rx.text_area(
                                        placeholder="Objetivo da entrevista, contexto da visita, evidencias iniciais",
                                        value=State.new_interview_notes,
                                        on_change=State.set_new_interview_notes,
                                        bg="var(--input-bg)",
                                        color="var(--text-primary)",
                                        min_height="104px",
                                        width="100%",
                                    ),
                                ),
                                columns="2",
                                spacing="3",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.button(
                                    rx.cond(State.editing_interview_id != "", "Salvar Alterações", "Criar Entrevista"),
                                    on_click=State.create_interview_session,
                                    class_name="primary-soft-action",
                                    flex="1",
                                ),
                                rx.button(
                                    "Cancelar",
                                    on_click=State.cancel_active_interview,
                                    bg="rgba(239,68,68,0.2)",
                                    color="#fca5a5",
                                    border="1px solid rgba(239,68,68,0.4)",
                                    flex="1",
                                ),
                                width="100%",
                                spacing="3",
                            ),
                            align="start",
                            width="100%",
                            spacing="3",
                        ),
                        padding="1rem",
                        width="100%",
                        **CARD_STYLE,
                    ),
                    rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.vstack(
                                    rx.heading("Entrevista Ativa", color="var(--text-primary)", size="5"),
                                    rx.text(
                                        State.selected_interview_record["form_name"],
                                        color="var(--text-primary)",
                                        font_weight="700",
                                        width="100%",
                                    ),
                                    align="start",
                                    spacing="1",
                                    width="100%",
                                ),
                                rx.spacer(),
                                rx.badge(State.selected_interview_record["status"], color_scheme="purple"),
                                width="100%",
                                align="start",
                            ),
                            rx.grid(
                                rx.box(
                                    rx.text("Projeto", color="var(--text-muted)", font_size="0.78rem"),
                                    rx.text(State.selected_interview_record["project_name"], color="var(--text-primary)", font_weight="600"),
                                    width="100%",
                                ),
                                rx.box(
                                    rx.text("Cliente", color="var(--text-muted)", font_size="0.78rem"),
                                    rx.text(State.selected_interview_record["client_name"], color="var(--text-primary)", font_weight="600"),
                                    width="100%",
                                ),
                                rx.box(
                                    rx.text("Etapa", color="var(--text-muted)", font_size="0.78rem"),
                                    rx.text(State.selected_interview_record["stage_name"], color="var(--text-primary)", font_weight="600"),
                                    width="100%",
                                ),
                                rx.box(
                                    rx.text(
                                        rx.cond(State.active_interview_requires_user, "Respondente", "Contexto"),
                                        color="var(--text-muted)",
                                        font_size="0.78rem",
                                    ),
                                    rx.text(State.selected_interview_record["interviewee_name"], color="var(--text-primary)", font_weight="600"),
                                    rx.cond(
                                        State.active_interview_requires_user,
                                        rx.text(State.selected_interview_record["interviewee_email"], color="var(--text-muted)", font_size="0.78rem"),
                                        rx.text(
                                            rx.cond(
                                                State.active_interview_is_group_stage,
                                                State.selected_interview_record["audience_group"],
                                                State.selected_interview_record["interviewee_role"],
                                            ),
                                            color="var(--text-muted)",
                                            font_size="0.78rem",
                                        ),
                                    ),
                                    width="100%",
                                ),
                                rx.box(
                                    rx.text(
                                        rx.cond(
                                            State.active_interview_requires_user,
                                            "Cargo",
                                            rx.cond(State.active_interview_is_group_stage, "Área", "Complemento"),
                                        ),
                                        color="var(--text-muted)",
                                        font_size="0.78rem",
                                    ),
                                    rx.text(
                                        rx.cond(
                                            State.active_interview_is_group_stage,
                                            State.selected_interview_record["target_area"],
                                            State.selected_interview_record["interviewee_role"],
                                        ),
                                        color="var(--text-primary)",
                                    ),
                                    width="100%",
                                ),
                                rx.box(
                                    rx.text("Data", color="var(--text-muted)", font_size="0.78rem"),
                                    rx.text(State.selected_interview_record["interview_date"], color="var(--text-primary)"),
                                    width="100%",
                                ),
                                columns="3",
                                spacing="3",
                                width="100%",
                            ),
                            rx.cond(
                                State.active_interview_requires_user,
                                rx.box(
                                    rx.vstack(
                                        rx.text("Selecionar Respondente", color="var(--text-primary)", font_weight="600"),
                                        rx.hstack(
                                            rx.select(
                                                State.active_interview_user_options,
                                                value=State.selected_interview_user_option,
                                                on_change=State.set_new_interview_user_option,
                                                placeholder="Escolha o líder respondente",
                                                bg="var(--input-bg)",
                                                color="var(--text-primary)",
                                                flex="1",
                                            ),
                                            rx.button(
                                                "Vincular",
                                                on_click=State.update_active_interview_context,
                                                bg="rgba(34,197,94,0.16)",
                                                color="#86efac",
                                                border="1px solid rgba(34,197,94,0.34)",
                                            ),
                                            spacing="3",
                                            align="end",
                                            width="100%",
                                        ),
                                        width="100%",
                                        spacing="2",
                                        align="start",
                                    ),
                                    width="100%",
                                    padding="0.85rem",
                                    border="1px solid var(--input-border)",
                                    border_radius="14px",
                                    bg="var(--surface-soft)",
                                ),
                                rx.fragment(),
                            ),
                            rx.cond(
                                State.active_interview_is_visit_stage,
                                rx.box(
                                    rx.vstack(
                                        rx.text("Selecionar Área", color="var(--text-primary)", font_weight="600"),
                                        rx.hstack(
                                            rx.select(
                                                State.active_interview_area_options,
                                                value=State.selected_interview_area_option,
                                                on_change=State.set_new_interview_area,
                                                placeholder="Escolha a área observada",
                                                bg="var(--input-bg)",
                                                color="var(--text-primary)",
                                                flex="1",
                                            ),
                                            rx.button(
                                                "Atualizar",
                                                on_click=State.update_active_interview_context,
                                                bg="rgba(34,197,94,0.16)",
                                                color="#86efac",
                                                border="1px solid rgba(34,197,94,0.34)",
                                            ),
                                            spacing="3",
                                            align="end",
                                            width="100%",
                                        ),
                                        width="100%",
                                        spacing="2",
                                        align="start",
                                    ),
                                    width="100%",
                                    padding="0.85rem",
                                    border="1px solid var(--input-border)",
                                    border_radius="14px",
                                    bg="var(--surface-soft)",
                                ),
                                rx.fragment(),
                            ),
                            rx.cond(
                                State.active_interview_is_group_stage,
                                rx.box(
                                    rx.vstack(
                                        rx.text("Definir Contexto do Grupo", color="var(--text-primary)", font_weight="600"),
                                        rx.grid(
                                            field_block(
                                                "Área",
                                                rx.select(
                                                    State.active_interview_area_options,
                                                    value=State.selected_interview_area_option,
                                                    on_change=State.set_new_interview_area,
                                                    placeholder="Escolha a área do cliente",
                                                    bg="var(--input-bg)",
                                                    color="var(--text-primary)",
                                                    width="100%",
                                                ),
                                            ),
                                            field_block(
                                                "Grupo",
                                                rx.input(
                                                    placeholder="Ex.: Supervisores do turno B",
                                                    value=State.active_interview_group_name,
                                                    on_change=State.set_new_interview_group_name,
                                                    bg="var(--input-bg)",
                                                    color="var(--text-primary)",
                                                    width="100%",
                                                ),
                                            ),
                                            columns="2",
                                            spacing="3",
                                            width="100%",
                                        ),
                                        rx.button(
                                            "Atualizar Contexto",
                                            on_click=State.update_active_interview_context,
                                            bg="rgba(34,197,94,0.16)",
                                            color="#86efac",
                                            border="1px solid rgba(34,197,94,0.34)",
                                        ),
                                        width="100%",
                                        spacing="2",
                                        align="start",
                                    ),
                                    width="100%",
                                    padding="0.85rem",
                                    border="1px solid var(--input-border)",
                                    border_radius="14px",
                                    bg="var(--surface-soft)",
                                ),
                                rx.fragment(),
                            ),
                            rx.grid(
                                interview_metric_card("Questoes", State.active_interview_score_summary["total_questions"], "list_checks", "#60a5fa"),
                                interview_metric_card("Respondidas", State.active_interview_score_summary["answered_count"], "check_check", "#34d399"),
                                interview_metric_card("Conclusao", f'{State.active_interview_score_summary["completion"]}%', "badge_check", "#f59e0b"),
                                interview_metric_card("Score Total", State.active_interview_score_summary["total_score"], "chart_column", "#f472b6"),
                                columns="4",
                                spacing="3",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.button("Salvar", on_click=State.save_interview_responses, class_name="primary-soft-action"),
                                rx.button(
                                    "Cancelar",
                                    on_click=State.cancel_active_interview,
                                    class_name="primary-soft-action",
                                    bg="rgba(250,204,21,0.16)",
                                    color="#fde68a",
                                    border="1px solid rgba(250,204,21,0.34)",
                                ),
                                spacing="3",
                                width="100%",
                                flex_wrap="wrap",
                            ),
                            align="start",
                            width="100%",
                            spacing="3",
                        ),
                        padding="1rem",
                        width="100%",
                        **CARD_STYLE,
                    ),
                    columns="2",
                    spacing="4",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.vstack(
                                rx.heading("Roteiro e Respostas", color="var(--text-primary)", size="5"),
                                rx.text(
                                    "Cada coluna representa uma dimensao. A pontuacao sobe imediatamente conforme a nota muda, sem estourar o layout dos cards.",
                                    color="var(--text-muted)",
                                    font_size="0.9rem",
                                    width="100%",
                                ),
                                rx.text(
                                    "Escala da nota: 0 Nada Aderente, 1 Pouco Aderente, 2 Parcialmente Aderente, 3 Moderadamente Aderente, 4 Muito Aderente, 5 Totalmente Aderente.",
                                    color="var(--text-muted)",
                                    font_size="0.82rem",
                                    width="100%",
                                    white_space="normal",
                                    word_break="break-word",
                                ),
                                align="start",
                                spacing="1",
                                width="100%",
                            ),
                            rx.badge("Kanban 5 dimensoes", color_scheme="orange"),
                            width="100%",
                            align="start",
                        ),
                        rx.cond(
                            State.active_interview_context_ready,
                            rx.box(
                                rx.hstack(
                                    *[
                                        dimension_kanban_column(dimension, accent_color)
                                        for dimension, accent_color in dimension_columns
                                    ],
                                    spacing="4",
                                    align="start",
                                    width="max-content",
                                ),
                                width="100%",
                                overflow_x="auto",
                                padding_bottom="0.5rem",
                            ),
                            rx.box(
                                rx.vstack(
                                    rx.text(
                                        "A entrevista precisa ter o contexto concluído antes de liberar o roteiro em kanban.",
                                        color="var(--text-muted)",
                                    ),
                                    rx.text(
                                        "Selecione o respondente, a área ou o grupo conforme a etapa e salve esse contexto primeiro.",
                                        color="var(--text-muted)",
                                        font_size="0.84rem",
                                    ),
                                    align="start",
                                    spacing="1",
                                ),
                                width="100%",
                                padding="1rem",
                                border="1px dashed var(--input-border)",
                                border_radius="16px",
                                bg="rgba(255,255,255,0.4)",
                            ),
                        ),
                        align="start",
                        spacing="3",
                        width="100%",
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
                                    text_align=rx.cond(header == "ID", "center", "left"),
                                    width="100%",
                                )
                                for header in interview_table_headers
                            ],
                            grid_template_columns=interview_grid_template,
                            width="100%",
                            align_items="center",
                            justify_items="stretch",
                            padding="0.1rem 0 0.85rem",
                            border_bottom="1px solid rgba(148,163,184,0.18)",
                            column_gap="0.9rem",
                        ),
                        rx.cond(
                            State.interview_sessions_data.length() == 0,
                            rx.box(
                                rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.86rem"),
                                width="100%",
                                padding="1.25rem 0.5rem 0.5rem",
                                text_align="center",
                            ),
                            rx.vstack(
                                rx.foreach(
                                    State.interview_sessions_data,
                                    lambda item: rx.grid(
                                        interview_table_cell(
                                            rx.text(item["id"], color="var(--text-primary)", font_weight="700", font_size="0.86rem"),
                                            rx.text("Entrevista", color="var(--text-muted)", font_size="0.76rem"),
                                        ),
                                        interview_table_cell(
                                            rx.cond(
                                                State.editing_interview_table_id == item["id"],
                                                rx.select(
                                                    State.interview_inline_form_options,
                                                    value=State.selected_edit_interview_form_option,
                                                    on_change=State.set_edit_interview_form_option,
                                                    placeholder="Selecione a pesquisa",
                                                    bg="var(--input-bg)",
                                                    color="var(--text-primary)",
                                                    width="100%",
                                                ),
                                                rx.vstack(
                                                    rx.text(item["form_name"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                                    rx.text("Pesquisa aplicada", color="var(--text-muted)", font_size="0.76rem"),
                                                    spacing="0",
                                                    align="start",
                                                    width="100%",
                                                ),
                                            ),
                                        ),
                                        interview_table_cell(
                                            rx.text(
                                                rx.cond(
                                                    State.editing_interview_table_id == item["id"],
                                                    State.selected_edit_interview_stage_name,
                                                    item["stage_name"],
                                                ),
                                                color="var(--text-secondary)",
                                                font_size="0.82rem",
                                            ),
                                        ),
                                        interview_table_cell(
                                            rx.cond(
                                                State.editing_interview_table_id == item["id"],
                                                rx.select(
                                                    State.interview_project_options,
                                                    value=State.selected_edit_interview_project_option,
                                                    on_change=State.set_edit_interview_project_option,
                                                    placeholder="Selecione o projeto",
                                                    bg="var(--input-bg)",
                                                    color="var(--text-primary)",
                                                    width="100%",
                                                ),
                                                rx.vstack(
                                                    rx.text(item["project_name"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                                    rx.text("Projeto contratado", color="var(--text-muted)", font_size="0.76rem"),
                                                    spacing="0",
                                                    align="start",
                                                    width="100%",
                                                ),
                                            ),
                                        ),
                                        interview_table_cell(
                                            rx.cond(
                                                State.editing_interview_table_id == item["id"],
                                                rx.input(
                                                    value=State.selected_edit_interview_client_name,
                                                    read_only=True,
                                                    bg="var(--surface-soft)",
                                                    color="var(--text-primary)",
                                                    width="100%",
                                                ),
                                                rx.vstack(
                                                    rx.text(item["client_name"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                                    rx.text("Cliente vinculado", color="var(--text-muted)", font_size="0.76rem"),
                                                    spacing="0",
                                                    align="start",
                                                    width="100%",
                                                ),
                                            ),
                                        ),
                                        interview_table_cell(
                                            rx.text(item["interviewee_name"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                            rx.text(item["interviewee_role"], color="var(--text-muted)", font_size="0.76rem"),
                                        ),
                                        interview_table_cell(
                                            rx.cond(
                                                State.editing_interview_table_id == item["id"],
                                                rx.input(
                                                    type="date",
                                                    value=State.edit_interview_date,
                                                    on_change=State.set_edit_interview_date,
                                                    bg="var(--input-bg)",
                                                    color="var(--text-primary)",
                                                    width="100%",
                                                ),
                                                rx.text(item["interview_date"], color="var(--text-secondary)", font_size="0.82rem"),
                                            ),
                                        ),
                                        interview_table_cell(
                                            rx.cond(
                                                State.editing_interview_table_id == item["id"],
                                                rx.select(
                                                    State.interview_status_options,
                                                    value=State.edit_interview_status,
                                                    on_change=State.set_edit_interview_status,
                                                    bg="var(--input-bg)",
                                                    color="var(--text-primary)",
                                                    width="100%",
                                                ),
                                                rx.badge(
                                                    item["status"],
                                                    color_scheme=rx.cond(item["status"] == "concluida", "green", "purple"),
                                                    size="1",
                                                ),
                                            ),
                                        ),
                                        interview_table_cell(
                                            rx.text(item["responses"], color="#f59e0b", font_size="0.82rem"),
                                        ),
                                        interview_table_cell(
                                            rx.text(item["total_score"], color="var(--text-primary)", font_size="0.82rem"),
                                        ),
                                        interview_table_cell(
                                            rx.cond(
                                                State.editing_interview_table_id == item["id"],
                                                rx.hstack(
                                                    rx.button(
                                                        "Salvar",
                                                        on_click=State.save_interview_inline,
                                                        bg="rgba(34,197,94,0.16)",
                                                        color="#86efac",
                                                        border="1px solid rgba(34,197,94,0.34)",
                                                        size="1",
                                                        font_weight="600",
                                                    ),
                                                    rx.button(
                                                        "Cancelar",
                                                        on_click=State.cancel_active_interview,
                                                        bg="rgba(250,204,21,0.16)",
                                                        color="#fde68a",
                                                        border="1px solid rgba(250,204,21,0.34)",
                                                        size="1",
                                                        font_weight="600",
                                                    ),
                                                    spacing="2",
                                                    justify="center",
                                                    align="center",
                                                    width="100%",
                                                ),
                                                rx.hstack(
                                                    rx.button(
                                                        "Alterar",
                                                        on_click=State.start_table_edit_interview(item["id"]),
                                                        bg="rgba(255,122,47,0.18)",
                                                        color="#fdba74",
                                                        border="1px solid rgba(255,122,47,0.38)",
                                                        size="1",
                                                        font_weight="600",
                                                    ),
                                                    rx.button(
                                                        "Excluir",
                                                        on_click=State.request_delete_confirmation("interview", item["id"], item["form_name"]),
                                                        bg="rgba(239,68,68,0.2)",
                                                        color="#fca5a5",
                                                        border="1px solid rgba(239,68,68,0.4)",
                                                        size="1",
                                                        font_weight="600",
                                                    ),
                                                    spacing="2",
                                                    justify="center",
                                                    align="center",
                                                    width="100%",
                                                ),
                                            ),
                                        ),
                                        grid_template_columns=interview_grid_template,
                                        width="100%",
                                        align_items="center",
                                        justify_items="stretch",
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
                rx.box(
                    rx.vstack(
                        rx.heading("Recursos da Entrevista", color="var(--text-primary)", size="5"),
                        rx.text(
                            "Anexe audios, imagens ou evidencias do campo para apoiar a consolidacao posterior.",
                            color="var(--text-muted)",
                            font_size="0.9rem",
                        ),
                        rx.upload(
                            rx.vstack(
                                rx.icon(tag="upload", color="var(--accent-strong)", size=20),
                                rx.text("Solte os arquivos aqui", color="var(--text-primary)"),
                                rx.text("ou clique para abrir o seletor", color="var(--text-muted)", font_size="0.85rem"),
                                align="center",
                                spacing="2",
                            ),
                            id="resource_upload",
                            width="100%",
                            padding="1.2rem",
                            border="2px dashed var(--dropzone-border)",
                            border_radius="16px",
                            bg="var(--dropzone-bg)",
                            class_name="dropzone-area",
                        ),
                        rx.hstack(
                            rx.button(
                                "Enviar Arquivos",
                                on_click=State.handle_resource_upload(rx.upload_files(upload_id="resource_upload")),
                                class_name="primary-soft-action",
                            ),
                            rx.button(
                                "Limpar Selecao",
                                on_click=rx.clear_selected_files("resource_upload"),
                                variant="ghost",
                                border="1px solid var(--input-border)",
                                color="var(--text-secondary)",
                            ),
                            spacing="3",
                        ),
                        rx.vstack(
                            rx.text("Selecionados:", color="var(--text-muted)", font_size="0.82rem"),
                            rx.foreach(
                                rx.selected_files("resource_upload"),
                                lambda file_name: rx.text(file_name, color="var(--text-secondary)", font_size="0.85rem"),
                            ),
                            align="start",
                            width="100%",
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Enviados:", color="var(--text-muted)", font_size="0.82rem"),
                            rx.foreach(
                                State.uploaded_resources,
                                lambda file_name: rx.text(file_name, color="var(--text-secondary)", font_size="0.85rem"),
                            ),
                            align="start",
                            width="100%",
                            spacing="1",
                        ),
                        align="start",
                        spacing="3",
                        width="100%",
                    ),
                    width="100%",
                    padding="1rem",
                    **CARD_STYLE,
                ),
                width="100%",
                spacing="4",
                class_name="content-stack",
            ),
            rx.box(
                rx.vstack(
                    rx.heading("Acesso restrito", color="var(--text-primary)", size="5"),
                    rx.text(
                        "A tela de Formulários agora opera o registro de entrevistas do consultor e fica restrita ao SmartLab - interno.",
                        color="var(--text-muted)",
                    ),
                    align="start",
                    width="100%",
                    spacing="3",
                ),
                width="100%",
                padding="1rem",
                **CARD_STYLE,
            ),
        ),
        width="100%",
        spacing="4",
        class_name="content-stack",
    )
