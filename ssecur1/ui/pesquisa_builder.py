from typing import Any

import reflex as rx


def build_pesquisa_builder_view(State, CARD_STYLE: dict[str, Any], field_block, custom_option_field, data_table) -> rx.Component:
    survey_headers = ["ID", "Pesquisa", "Serviço SmartLab", "Etapa", "Dimensões", "Link", "Ações"]
    question_headers = ["Ordem", "Dimensão", "Pergunta", "Tipo", "Viés", "Peso", "Opções", "Lógica", "Ações"]
    diagnostic_headers = ["Dimensão", "Pontuação", "Maturidade", "Respostas"]
    question_grid_template = "58px minmax(120px,0.9fr) minmax(240px,2fr) minmax(118px,0.9fr) minmax(104px,0.8fr) 72px minmax(200px,1.4fr) minmax(160px,1fr) minmax(170px,1fr)"
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

    def dimension_badge(label) -> rx.Component:
        return rx.badge(
            label,
            bg=rx.cond(
                label == "Presença",
                "rgba(255,122,47,0.16)",
                rx.cond(
                    label == "Correção",
                    "rgba(14,165,233,0.16)",
                    rx.cond(
                        label == "Reconhecimento",
                        "rgba(168,85,247,0.16)",
                        rx.cond(
                            label == "Comunicação",
                            "rgba(34,197,94,0.16)",
                            rx.cond(
                                label == "Disciplina/Exemplo",
                                "rgba(244,63,94,0.16)",
                                "rgba(148,163,184,0.16)",
                            ),
                        ),
                    ),
                ),
            ),
            color=rx.cond(
                label == "Presença",
                "#fdba74",
                rx.cond(
                    label == "Correção",
                    "#7dd3fc",
                    rx.cond(
                        label == "Reconhecimento",
                        "#d8b4fe",
                        rx.cond(
                            label == "Comunicação",
                            "#86efac",
                            rx.cond(
                                label == "Disciplina/Exemplo",
                                "#fda4af",
                                "var(--text-secondary)",
                            ),
                        ),
                    ),
                ),
            ),
            border=rx.cond(
                label == "Presença",
                "1px solid rgba(255,122,47,0.34)",
                rx.cond(
                    label == "Correção",
                    "1px solid rgba(14,165,233,0.34)",
                    rx.cond(
                        label == "Reconhecimento",
                        "1px solid rgba(168,85,247,0.34)",
                        rx.cond(
                            label == "Comunicação",
                            "1px solid rgba(34,197,94,0.34)",
                            rx.cond(
                                label == "Disciplina/Exemplo",
                                "1px solid rgba(244,63,94,0.34)",
                                "1px solid rgba(148,163,184,0.3)",
                            ),
                        ),
                    ),
                ),
            ),
            width="fit-content",
            size="1",
            variant="soft",
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
                            State.smartlab_service_options,
                            value=State.new_form_category,
                            on_change=State.set_new_form_category,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.cond(
                        State.new_form_category == "Outro",
                        custom_option_field(
                            "Novo Serviço SmartLab",
                            value=State.new_form_custom_category,
                            on_change=State.set_new_form_custom_category,
                            on_confirm=State.confirm_new_form_category,
                            placeholder="Digite aqui para cadastrar um novo serviço",
                            help_text="Clique em OK para registrar o novo serviço e trazê-lo de volta ao seletor.",
                        ),
                        rx.fragment(),
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
                            f"Roteiro ativo: {State.selected_form_name}",
                            "Selecione o formulário base para cadastrar as perguntas por dimensão.",
                        ),
                        color="var(--text-muted)",
                        font_size="0.82rem",
                    ),
                    field_block(
                        "Etapa da Pesquisa",
                        rx.select(
                            State.survey_stage_options,
                            value=State.new_form_stage,
                            on_change=State.set_new_form_stage,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.cond(
                        State.new_form_stage == "Outra",
                        custom_option_field(
                            "Nova Etapa da Pesquisa",
                            value=State.new_form_custom_stage,
                            on_change=State.set_new_form_custom_stage,
                            on_confirm=State.confirm_new_form_stage,
                            placeholder="Digite aqui para cadastrar uma nova etapa",
                        ),
                        rx.fragment(),
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
                        custom_option_field(
                            "Nova Dimensão",
                            value=State.new_question_custom_dimension,
                            on_change=State.set_new_question_custom_dimension,
                            on_confirm=State.confirm_new_question_dimension,
                            placeholder="Nova dimensão",
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
                    columns="7",
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
                                    rx.text(f["stage"], color="var(--text-secondary)", font_size="0.82rem"),
                                ),
                                project_table_cell(
                                    rx.cond(
                                        f["dimensions"] != "-",
                                        rx.flex(
                                            rx.cond(
                                                f["has_dim_presenca"] == "1",
                                                dimension_badge("Presença"),
                                                rx.fragment(),
                                            ),
                                            rx.cond(
                                                f["has_dim_correcao"] == "1",
                                                dimension_badge("Correção"),
                                                rx.fragment(),
                                            ),
                                            rx.cond(
                                                f["has_dim_reconhecimento"] == "1",
                                                dimension_badge("Reconhecimento"),
                                                rx.fragment(),
                                            ),
                                            rx.cond(
                                                f["has_dim_comunicacao"] == "1",
                                                dimension_badge("Comunicação"),
                                                rx.fragment(),
                                            ),
                                            rx.cond(
                                                f["has_dim_disciplina"] == "1",
                                                dimension_badge("Disciplina/Exemplo"),
                                                rx.fragment(),
                                            ),
                                            wrap="wrap",
                                            spacing="2",
                                            width="100%",
                                            justify="center",
                                        ),
                                        rx.text(
                                            f["dimensions"],
                                            color="var(--text-secondary)",
                                            font_size="0.8rem",
                                            white_space="normal",
                                            word_break="break-word",
                                        ),
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
                                        rx.cond(
                                            f["has_questions"] == "1",
                                            rx.button(
                                                "Selecionar",
                                                on_click=State.select_form_by_id(f["id"]),
                                                bg="rgba(34,197,94,0.16)",
                                                color="#86efac",
                                                border="1px solid rgba(34,197,94,0.34)",
                                                size="1",
                                            ),
                                            rx.fragment(),
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
                                columns="7",
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
                    grid_template_columns=question_grid_template,
                    width="100%",
                    align_items="center",
                    justify_items="stretch",
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
                                    rx.box(
                                        rx.text(q["order"], color="var(--text-secondary)", font_size="0.82rem"),
                                        width="100%",
                                        text_align="center",
                                    ),
                                ),
                                project_table_cell(
                                    rx.cond(
                                        State.editing_question_id == q["id_key"],
                                        rx.vstack(
                                            rx.select(
                                                State.question_dimension_options,
                                                value=State.new_question_dimension,
                                                on_change=State.set_new_question_dimension,
                                                bg="var(--input-bg)",
                                                color="var(--text-primary)",
                                                width="100%",
                                                size="1",
                                            ),
                                            rx.cond(
                                                State.new_question_dimension == "Outro",
                                                rx.hstack(
                                                    rx.input(
                                                        placeholder="Nova dimensão",
                                                        value=State.new_question_custom_dimension,
                                                        on_change=State.set_new_question_custom_dimension,
                                                        bg="var(--input-bg)",
                                                        color="var(--text-primary)",
                                                        width="100%",
                                                        size="1",
                                                    ),
                                                    rx.button(
                                                        "OK",
                                                        on_click=State.confirm_new_question_dimension,
                                                        bg="rgba(255,122,47,0.18)",
                                                        color="#fdba74",
                                                        border="1px solid rgba(255,122,47,0.38)",
                                                        size="1",
                                                    ),
                                                    width="100%",
                                                    spacing="2",
                                                ),
                                                rx.fragment(),
                                            ),
                                            width="100%",
                                            spacing="2",
                                        ),
                                        dimension_badge(q["dimension"]),
                                    ),
                                ),
                                project_table_cell(
                                    rx.cond(
                                        State.editing_question_id == q["id_key"],
                                        rx.text_area(
                                            value=State.new_question_text,
                                            on_change=State.set_new_question_text,
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            min_height="92px",
                                            width="100%",
                                        ),
                                        rx.text(
                                            q["text"],
                                            color="var(--text-primary)",
                                            font_size="0.82rem",
                                            white_space="normal",
                                            word_break="break-word",
                                        ),
                                    ),
                                ),
                                project_table_cell(
                                    rx.cond(
                                        State.editing_question_id == q["id_key"],
                                        rx.select(
                                            ["escala_0_5", "texto"],
                                            value=State.new_question_type,
                                            on_change=State.set_new_question_type,
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            width="100%",
                                            size="1",
                                        ),
                                        rx.badge(q["qtype"], color_scheme="purple", width="fit-content", size="1"),
                                    ),
                                ),
                                project_table_cell(
                                    rx.cond(
                                        State.editing_question_id == q["id_key"],
                                        rx.select(
                                            State.question_polarity_options,
                                            value=State.new_question_polarity,
                                            on_change=State.set_new_question_polarity,
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            width="100%",
                                            size="1",
                                        ),
                                        rx.badge(
                                            q["polarity"],
                                            color_scheme=rx.cond(q["polarity"] == "negativa", "red", "green"),
                                            width="fit-content",
                                            size="1",
                                        ),
                                    ),
                                ),
                                project_table_cell(
                                    rx.cond(
                                        State.editing_question_id == q["id_key"],
                                        rx.select(
                                            State.question_weight_options,
                                            value=State.new_question_weight,
                                            on_change=State.set_new_question_weight,
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            width="100%",
                                            size="1",
                                        ),
                                        rx.text(q["weight"], color="var(--text-secondary)", font_size="0.82rem"),
                                    ),
                                ),
                                project_table_cell(
                                    rx.cond(
                                        State.editing_question_id == q["id_key"],
                                        rx.text_area(
                                            value=State.new_question_options,
                                            on_change=State.set_new_question_options,
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            min_height="92px",
                                            width="100%",
                                        ),
                                        rx.text(
                                            q["options_str"],
                                            color="var(--text-secondary)",
                                            font_size="0.8rem",
                                            white_space="normal",
                                            word_break="break-word",
                                        ),
                                    ),
                                ),
                                project_table_cell(
                                    rx.cond(
                                        State.editing_question_id == q["id_key"],
                                        rx.input(
                                            placeholder="Condição lógica",
                                            value=State.new_question_condition,
                                            on_change=State.set_new_question_condition,
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            width="100%",
                                        ),
                                        rx.text(
                                            q["logic_rule"],
                                            color="var(--text-muted)",
                                            font_size="0.8rem",
                                            white_space="normal",
                                            word_break="break-word",
                                        ),
                                    ),
                                ),
                                project_table_cell(
                                    rx.cond(
                                        State.editing_question_id == q["id_key"],
                                        rx.hstack(
                                            rx.button(
                                                "Salvar",
                                                on_click=State.create_question,
                                                bg="rgba(34,197,94,0.16)",
                                                color="#86efac",
                                                border="1px solid rgba(34,197,94,0.34)",
                                                size="1",
                                            ),
                                            rx.button(
                                                "Cancelar",
                                                on_click=State.cancel_edit_question,
                                                bg="rgba(250,204,21,0.16)",
                                                color="#fde68a",
                                                border="1px solid rgba(250,204,21,0.34)",
                                                size="1",
                                            ),
                                            spacing="2",
                                            align="center",
                                            justify="center",
                                            width="100%",
                                        ),
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
                                ),
                                grid_template_columns=question_grid_template,
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
