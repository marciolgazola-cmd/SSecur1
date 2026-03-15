from typing import Any

import reflex as rx


def build_pesquisa_builder_view(State, CARD_STYLE: dict[str, Any], field_block, data_table) -> rx.Component:
    survey_headers = ["ID", "Pesquisa", "Serviço SmartLab", "Dimensões", "Link", "Ações"]
    question_headers = ["Ordem", "Dimensão", "Pergunta", "Tipo", "Viés", "Peso", "Opções", "Lógica", "Ações"]
    diagnostic_headers = ["Dimensão", "Pontuação", "Maturidade", "Respostas"]

    def project_table_cell(*children: rx.Component) -> rx.Component:
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
        rx.grid(
            rx.box(
                rx.vstack(
                    rx.heading("Survey SmartLab", color="var(--text-primary)", size="5"),
                    rx.text(
                        "Nesta aba o consultor cria o formulário-base da consultoria. Aqui não existe cliente, entrevistado, cargo ou data.",
                        color="var(--text-muted)",
                        font_size="0.9rem",
                    ),
                    field_block(
                        "Nome da Pesquisa / Roteiro",
                        rx.input(
                            placeholder="Nome da pesquisa / roteiro",
                            value=State.new_form_name,
                            on_change=State.set_new_form_name,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Serviço SmartLab",
                        rx.select(
                            [
                                "Diagnóstico Cultura de Segurança",
                                "Atuação da Liderança",
                                "Segurança versus Produtividade",
                                "Variação Cultural",
                            ],
                            value=State.new_form_category,
                            on_change=State.set_new_form_category,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.button(
                        State.form_submit_label,
                        on_click=State.create_form,
                        class_name="primary-soft-action",
                        width="100%",
                    ),
                    rx.cond(
                        State.is_editing_form,
                        rx.button(
                            "Cancelar",
                            on_click=State.reset_form_builder,
                            variant="ghost",
                            border="1px solid var(--input-border)",
                            color="var(--text-secondary)",
                            width="100%",
                        ),
                        rx.fragment(),
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
                    rx.heading("Dimensão e Perguntas", color="var(--text-primary)", size="5"),
                    field_block(
                        "Pesquisa / Roteiro",
                        rx.select(
                            State.survey_builder_options,
                            value=State.selected_survey_builder_option,
                            on_change=State.select_form,
                            placeholder="Selecione formulário base",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.text(
                        rx.cond(
                            State.selected_form_name != "",
                            f"Formulário ativo: {State.selected_form_name}",
                            "Selecione o formulário base para cadastrar as perguntas por dimensão.",
                        ),
                        color="var(--text-muted)",
                        font_size="0.82rem",
                    ),
                    field_block(
                        "Dimensão",
                        rx.select(
                            State.question_dimension_options,
                            value=State.new_question_dimension,
                            on_change=State.set_new_question_dimension,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.cond(
                        State.new_question_dimension == "Outro",
                        field_block(
                            "Nova Dimensão",
                            rx.input(
                                placeholder="Nova dimensão",
                                value=State.new_question_custom_dimension,
                                on_change=State.set_new_question_custom_dimension,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                        ),
                        rx.fragment(),
                    ),
                    field_block(
                        "Pergunta",
                        rx.input(
                            placeholder="Texto da pergunta",
                            value=State.new_question_text,
                            on_change=State.set_new_question_text,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Tipo de Resposta",
                        rx.select(
                            ["escala_0_5", "texto"],
                            value=State.new_question_type,
                            on_change=State.set_new_question_type,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.grid(
                        field_block(
                            "Viés da Pergunta",
                            rx.select(
                                State.question_polarity_options,
                                value=State.new_question_polarity,
                                on_change=State.set_new_question_polarity,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                        ),
                        field_block(
                            "Peso",
                            rx.select(
                                State.question_weight_options,
                                value=State.new_question_weight,
                                on_change=State.set_new_question_weight,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                width="100%",
                            ),
                        ),
                        width="100%",
                        spacing="3",
                        columns="2",
                    ),
                    field_block(
                        "Opções / Escala",
                        rx.input(
                            placeholder="Escala fixa 0-5 separada por vírgula",
                            value=State.new_question_options,
                            on_change=State.set_new_question_options,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Lógica Condicional",
                        rx.input(
                            placeholder="Lógica condicional opcional",
                            value=State.new_question_condition,
                            on_change=State.set_new_question_condition,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.button(
                        rx.cond(State.editing_question_id != "", "Salvar Alterações", "Adicionar Pergunta"),
                        on_click=State.create_question,
                        class_name="primary-soft-action",
                        width="100%",
                    ),
                    rx.cond(
                        State.editing_question_id != "",
                        rx.button(
                            "Cancelar Edição",
                            on_click=State.reset_form_builder,
                            variant="ghost",
                            border="1px solid var(--input-border)",
                            color="var(--text-secondary)",
                            width="100%",
                        ),
                        rx.fragment(),
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
            width="100%",
            spacing="4",
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
                        for header in survey_headers
                    ],
                    columns="6",
                    width="100%",
                    align_items="center",
                    justify_items="center",
                    padding="0.1rem 0 0.85rem",
                    border_bottom="1px solid rgba(148,163,184,0.18)",
                    column_gap="0.9rem",
                ),
                rx.cond(
                    State.forms_data.length() == 0,
                    rx.box(
                        rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.86rem"),
                        width="100%",
                        padding="1.25rem 0.5rem 0.5rem",
                        text_align="center",
                    ),
                    rx.vstack(
                        rx.foreach(
                            State.forms_data,
                            lambda f: rx.grid(
                                project_table_cell(
                                    rx.text(f["id"], color="var(--text-primary)", font_weight="600", font_size="0.86rem"),
                                ),
                                project_table_cell(
                                    rx.text(f["name"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                ),
                                project_table_cell(
                                    rx.text(f["category"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                project_table_cell(
                                    rx.text(
                                        f["dimensions"],
                                        color="var(--text-secondary)",
                                        font_size="0.8rem",
                                        white_space="normal",
                                        word_break="break-word",
                                    ),
                                ),
                                project_table_cell(
                                    rx.text(
                                        "Link público",
                                        color="var(--text-primary)",
                                        font_size="0.8rem",
                                        font_weight="600",
                                    ),
                                    rx.text(
                                        f["share_link"],
                                        color="var(--text-muted)",
                                        font_size="0.76rem",
                                        white_space="normal",
                                        word_break="break-word",
                                    ),
                                    rx.button(
                                        "Copiar",
                                        on_click=rx.set_clipboard(f["share_link"]),
                                        variant="ghost",
                                        border="1px solid var(--input-border)",
                                        color="var(--text-secondary)",
                                        size="1",
                                    ),
                                ),
                                project_table_cell(
                                    rx.hstack(
                                        rx.button(
                                            "Selecionar",
                                            on_click=State.select_form_by_id(f["id"]),
                                            class_name="primary-soft-action",
                                            size="1",
                                        ),
                                        rx.button(
                                            "Alterar",
                                            on_click=State.start_edit_form(f["id"]),
                                            bg="rgba(255,122,47,0.18)",
                                            color="#fdba74",
                                            border="1px solid rgba(255,122,47,0.38)",
                                            size="1",
                                        ),
                                        rx.cond(
                                            State.can_delete_forms,
                                            rx.button(
                                                "Excluir",
                                                on_click=State.request_delete_confirmation("form", f["id"], f["name"]),
                                                bg="rgba(239,68,68,0.2)",
                                                color="#fca5a5",
                                                border="1px solid rgba(239,68,68,0.4)",
                                                size="1",
                                            ),
                                            rx.fragment(),
                                        ),
                                        spacing="2",
                                        align="center",
                                        justify="center",
                                        width="100%",
                                    ),
                                ),
                                columns="6",
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
                        for header in question_headers
                    ],
                    columns="9",
                    width="100%",
                    align_items="center",
                    justify_items="center",
                    padding="0.1rem 0 0.85rem",
                    border_bottom="1px solid rgba(148,163,184,0.18)",
                    column_gap="0.9rem",
                ),
                rx.cond(
                    State.questions_data.length() == 0,
                    rx.box(
                        rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.86rem"),
                        width="100%",
                        padding="1.25rem 0.5rem 0.5rem",
                        text_align="center",
                    ),
                    rx.vstack(
                        rx.foreach(
                            State.questions_data,
                            lambda q: rx.grid(
                                project_table_cell(
                                    rx.text(q["order"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                project_table_cell(
                                    rx.badge(q["dimension"], color_scheme="orange", width="fit-content", size="1"),
                                ),
                                project_table_cell(
                                    rx.text(
                                        q["text"],
                                        color="var(--text-primary)",
                                        font_size="0.82rem",
                                        white_space="normal",
                                        word_break="break-word",
                                    ),
                                ),
                                project_table_cell(
                                    rx.badge(q["qtype"], color_scheme="purple", width="fit-content", size="1"),
                                ),
                                project_table_cell(
                                    rx.badge(
                                        q["polarity"],
                                        color_scheme=rx.cond(q["polarity"] == "negativa", "red", "green"),
                                        width="fit-content",
                                        size="1",
                                    ),
                                ),
                                project_table_cell(
                                    rx.text(q["weight"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                project_table_cell(
                                    rx.text(
                                        q["options_str"],
                                        color="var(--text-secondary)",
                                        font_size="0.8rem",
                                        white_space="normal",
                                        word_break="break-word",
                                    ),
                                ),
                                project_table_cell(
                                    rx.text(
                                        q["logic_rule"],
                                        color="var(--text-muted)",
                                        font_size="0.8rem",
                                        white_space="normal",
                                        word_break="break-word",
                                    ),
                                ),
                                project_table_cell(
                                    rx.hstack(
                                        rx.button(
                                            "Alterar",
                                            on_click=State.start_edit_question(q["id"]),
                                            bg="rgba(255,122,47,0.18)",
                                            color="#fdba74",
                                            border="1px solid rgba(255,122,47,0.38)",
                                            size="1",
                                        ),
                                        rx.button(
                                            "Excluir",
                                            on_click=State.request_delete_confirmation("question", q["id"], q["text"]),
                                            bg="rgba(239,68,68,0.2)",
                                            color="#fca5a5",
                                            border="1px solid rgba(239,68,68,0.4)",
                                            size="1",
                                        ),
                                        spacing="2",
                                        align="center",
                                        justify="center",
                                        width="100%",
                                    ),
                                ),
                                columns="9",
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
        rx.box(
            rx.vstack(
                rx.heading("Diagnóstico por Dimensão", color="var(--text-primary)", size="5"),
                rx.text(
                    "A pontuação soma os scores das respostas por dimensão e classifica a maturidade automaticamente.",
                    color="var(--text-muted)",
                    font_size="0.88rem",
                ),
                rx.grid(
                    rx.box(rx.text("0–10 = Reativo", color="var(--text-secondary)"), class_name="permission-template-box"),
                    rx.box(rx.text("11–15 = Dependente", color="var(--text-secondary)"), class_name="permission-template-box"),
                    rx.box(rx.text("16–20 = Independente", color="var(--text-secondary)"), class_name="permission-template-box"),
                    rx.box(rx.text("21–25 = Interdependente", color="var(--text-secondary)"), class_name="permission-template-box"),
                    columns="4",
                    spacing="3",
                    width="100%",
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
                                for header in diagnostic_headers
                            ],
                            columns="4",
                            width="100%",
                            align_items="center",
                            justify_items="center",
                            padding="0.1rem 0 0.85rem",
                            border_bottom="1px solid rgba(148,163,184,0.18)",
                            column_gap="0.9rem",
                        ),
                        rx.cond(
                            State.selected_survey_dimension_diagnostics.length() == 0,
                            rx.box(
                                rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.86rem"),
                                width="100%",
                                padding="1.25rem 0.5rem 0.5rem",
                                text_align="center",
                            ),
                            rx.vstack(
                                rx.foreach(
                                    State.selected_survey_dimension_diagnostics,
                                    lambda item: rx.grid(
                                        project_table_cell(
                                            rx.text(item["dimension"], color="var(--text-primary)", font_size="0.84rem"),
                                        ),
                                        project_table_cell(
                                            rx.text(item["score"], color="#f59e0b", font_size="0.82rem"),
                                        ),
                                        project_table_cell(
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
                                                width="fit-content",
                                                size="1",
                                            ),
                                        ),
                                        project_table_cell(
                                            rx.text(item["responses"], color="var(--text-secondary)", font_size="0.82rem"),
                                        ),
                                        columns="4",
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
    )
