from typing import Any

import reflex as rx


def build_ia_view(State, CARD_STYLE: dict[str, Any]) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Especialista IA", color="var(--text-primary)", size="6"),
                        rx.text(
                            "Contexto local com RAG para comparar respostas, políticas, evidências e transformar achados em plano de ação sem dependência externa.",
                            color="var(--text-muted)",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.badge(State.ai_runtime_status["engine"], color_scheme="purple"),
                    rx.badge(State.ai_runtime_status["status"], color_scheme="orange"),
                    width="100%",
                    align="center",
                ),
                rx.grid(
                    rx.box(
                        rx.vstack(
                            rx.text("Runtime local", color="var(--text-muted)", font_size="0.8rem"),
                            rx.text(State.ai_runtime_status["version"], color="var(--text-primary)", font_weight="600"),
                            rx.text(f"Modelos instalados: {State.ai_runtime_status['models']}", color="var(--text-secondary)", font_size="0.84rem"),
                            rx.select(
                                State.ai_model_options,
                                value=State.ai_selected_model_effective,
                                on_change=State.set_ai_selected_model,
                                placeholder="Modelo local",
                                width="100%",
                            ),
                            align="start",
                            spacing="2",
                            width="100%",
                        ),
                        padding="1rem",
                        class_name="panel-card",
                        **CARD_STYLE,
                    ),
                    rx.box(
                        rx.vstack(
                            rx.text("Contexto analisado", color="var(--text-muted)", font_size="0.8rem"),
                            rx.text(f"Tenant: {State.ai_context_summary['tenant']}", color="var(--text-primary)", font_weight="600"),
                            rx.select(
                                State.ai_scope_options,
                                value=State.ai_scope_mode_effective,
                                on_change=State.set_ai_scope_mode,
                                width="100%",
                            ),
                            rx.text(
                                f"Escopo: {State.ai_scope_mode_effective}",
                                color="var(--text-secondary)",
                                font_size="0.84rem",
                            ),
                            rx.text(
                                rx.cond(
                                    State.ai_scope_mode_effective == "projeto",
                                    f"Projeto: {State.ai_selected_project_label}",
                                    "Projeto: desativado; o Especialista IA está usando a visão geral do tenant.",
                                ),
                                color="var(--text-secondary)",
                                font_size="0.84rem",
                            ),
                            rx.text(
                                f"Documentos {State.ai_context_summary['documents']} | Respostas {State.ai_context_summary['responses']} | Ações abertas {State.ai_context_summary['actions_open']}",
                                color="var(--text-secondary)",
                                font_size="0.84rem",
                            ),
                            align="start",
                            spacing="2",
                            width="100%",
                        ),
                        padding="1rem",
                        class_name="panel-card",
                        **CARD_STYLE,
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.grid(
                    rx.foreach(
                        State.ai_source_snapshot,
                        lambda item: rx.box(
                            rx.vstack(
                                rx.text(item["label"], color="var(--text-muted)", font_size="0.78rem"),
                                rx.heading(item["value"], size="5", color="var(--text-primary)"),
                                rx.text(item["detail"], color="var(--text-secondary)", font_size="0.82rem"),
                                align="start",
                                spacing="1",
                                width="100%",
                            ),
                            padding="0.9rem",
                            class_name="panel-card metric-card",
                            **CARD_STYLE,
                        ),
                    ),
                    columns="6",
                    spacing="3",
                    width="100%",
                ),
                rx.grid(
                    rx.box(
                        rx.vstack(
                            rx.text_area(
                                placeholder="Pergunte em linguagem natural: compare respostas com as políticas, identifique lacunas e proponha ações.",
                                value=State.ai_prompt,
                                on_change=State.set_ai_prompt,
                                bg="var(--input-bg)",
                                color="var(--text-primary)",
                                min_height="180px",
                                width="100%",
                            ),
                            rx.box(
                                rx.vstack(
                                    rx.icon(tag="mouse_pointer_click", color="var(--accent-strong)", size=20),
                                    rx.text("Solte uma pergunta da tela de Formulários", color="var(--text-primary)"),
                                    rx.text("ou clique para aproveitar a pergunta em arraste", color="var(--text-muted)", font_size="0.85rem"),
                                    rx.text(
                                        rx.cond(
                                            State.dragged_question_text != "",
                                            "Pronto para soltar uma pergunta arrastada.",
                                            "Nenhuma pergunta em arraste no momento.",
                                        ),
                                        color="var(--text-secondary)",
                                        font_size="0.9rem",
                                    ),
                                    rx.cond(
                                        State.dragged_question_text != "",
                                        rx.text(State.dragged_question_text, color="var(--text-secondary)", font_size="0.85rem"),
                                        rx.fragment(),
                                    ),
                                    align="start",
                                    width="100%",
                                    spacing="2",
                                ),
                                width="100%",
                                padding="1.2rem",
                                border="2px dashed var(--dropzone-border)",
                                border_radius="16px",
                                bg="var(--dropzone-bg)",
                                class_name="dropzone-area",
                                on_click=State.drop_question_into_prompt,
                            ),
                            rx.hstack(
                                rx.button(
                                    "Analisar com Especialista IA",
                                    on_click=State.ask_ai,
                                    class_name="primary-soft-action",
                                ),
                                rx.badge(f"Modelo: {State.ai_selected_model_effective}", color_scheme="purple"),
                                spacing="3",
                                width="100%",
                                align="center",
                            ),
                            rx.box(
                                rx.cond(
                                    State.ai_answer != "",
                                    rx.text(State.ai_answer, white_space="pre-wrap", color="var(--text-secondary)"),
                                    rx.vstack(
                                        rx.icon(tag="sparkles", color="var(--accent-strong)", size=22),
                                        rx.text("Nenhuma resposta exibida ainda.", color="var(--text-primary)", font_weight="600"),
                                        rx.text(
                                            "Escreva uma pergunta objetiva ou use a base de conhecimento para iniciar a análise RAG.",
                                            color="var(--text-muted)",
                                            font_size="0.84rem",
                                            text_align="center",
                                        ),
                                        align="center",
                                        spacing="2",
                                        width="100%",
                                        justify="center",
                                        min_height="188px",
                                    ),
                                ),
                                width="100%",
                                min_height="220px",
                                padding="1rem",
                                bg="var(--surface-soft)",
                                border="1px solid var(--input-border)",
                                border_radius="12px",
                            ),
                            align="start",
                            width="100%",
                            spacing="3",
                        ),
                        width="100%",
                        padding="1rem",
                        **CARD_STYLE,
                    ),
                    rx.box(
                        rx.vstack(
                            rx.heading("Base de conhecimento da IA", color="var(--text-primary)", size="4"),
                            rx.text(
                                "Os arquivos enviados aqui compõem a base de conhecimento do Especialista IA. Cada arquivo suportado vira texto indexado para recuperação RAG local.",
                                color="var(--text-muted)",
                                font_size="0.88rem",
                            ),
                            rx.select(
                                State.ai_knowledge_scope_options,
                                value=State.ai_knowledge_scope_effective,
                                on_change=State.set_ai_knowledge_scope,
                                width="100%",
                            ),
                            rx.text(
                                rx.cond(
                                    State.ai_knowledge_scope_effective == "smartlab",
                                    "Destino atual: Base SmartLab. Esses materiais passam a apoiar análises, comparações e planos em toda a plataforma.",
                                    "Destino atual: Base do tenant. Esses materiais ficam isolados no contexto do cliente atual.",
                                ),
                                color="var(--text-secondary)",
                                font_size="0.82rem",
                            ),
                            rx.select(
                                State.ai_resource_type_options,
                                value=State.ai_resource_type,
                                on_change=State.set_ai_resource_type,
                                width="100%",
                            ),
                            rx.upload(
                                rx.vstack(
                                    rx.icon(tag="upload", color="var(--accent-strong)", size=20),
                                    rx.text("Solte PDF, Word (.docx) e Excel (.xlsx)", color="var(--text-primary)"),
                                    rx.text("ou clique para abrir o seletor. TXT, CSV e JSON também são aceitos.", color="var(--text-muted)", font_size="0.85rem"),
                                    align="center",
                                    spacing="2",
                                ),
                                id="assistant_resource_upload",
                                width="100%",
                                padding="1.2rem",
                                border="2px dashed var(--dropzone-border)",
                                border_radius="16px",
                                bg="var(--dropzone-bg)",
                                class_name="dropzone-area",
                            ),
                            rx.hstack(
                                rx.button(
                                    "Enviar para a base IA",
                                    on_click=State.handle_resource_upload(rx.upload_files(upload_id="assistant_resource_upload")),
                                    class_name="primary-soft-action",
                                ),
                                rx.button(
                                    "Limpar seleção",
                                    on_click=rx.clear_selected_files("assistant_resource_upload"),
                                    variant="ghost",
                                    border="1px solid var(--input-border)",
                                    color="var(--text-secondary)",
                                ),
                                spacing="3",
                            ),
                            rx.vstack(
                                rx.foreach(
                                    rx.selected_files("assistant_resource_upload"),
                                    lambda file_name: rx.text(file_name, color="var(--text-secondary)", font_size="0.84rem"),
                                ),
                                align="start",
                                width="100%",
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.foreach(
                                    State.ai_documents_data,
                                    lambda item: rx.box(
                                        rx.vstack(
                                            rx.hstack(
                                                rx.text(item["file_name"], color="var(--text-primary)", font_weight="600"),
                                                rx.spacer(),
                                                rx.badge(item["resource_type"], color_scheme="orange"),
                                                spacing="2",
                                                width="100%",
                                            ),
                                            rx.text(
                                                f"{item['project_scope']} | {item['uploaded_at']} | {item['file_size']} | chunks: {item['chunk_count']}",
                                                color="var(--text-muted)",
                                                font_size="0.78rem",
                                            ),
                                            rx.hstack(
                                                rx.text(f"Por: {item['uploaded_by']}", color="var(--text-secondary)", font_size="0.8rem"),
                                                rx.spacer(),
                                                rx.cond(
                                                    item["can_delete"],
                                                    rx.button(
                                                        "Remover",
                                                        on_click=State.delete_ai_document(item["id"]),
                                                        size="1",
                                                        variant="ghost",
                                                        border="1px solid var(--input-border)",
                                                        color="var(--text-secondary)",
                                                    ),
                                                    rx.badge("Somente leitura", color_scheme="gray"),
                                                ),
                                                width="100%",
                                                align="center",
                                            ),
                                            align="start",
                                            spacing="1",
                                            width="100%",
                                        ),
                                        width="100%",
                                        padding="0.85rem",
                                        class_name="panel-card",
                                        **CARD_STYLE,
                                    ),
                                ),
                                align="start",
                                width="100%",
                                spacing="2",
                            ),
                            align="start",
                            width="100%",
                            spacing="3",
                        ),
                        width="100%",
                        padding="1rem",
                        **CARD_STYLE,
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.heading("Recomendações prontas para Plano de Ação", color="var(--text-primary)", size="4"),
                            rx.spacer(),
                            rx.badge(
                                rx.cond(State.selected_project_option != "", "Projeto selecionado", "Selecione um projeto"),
                                color_scheme="purple",
                            ),
                            width="100%",
                        ),
                        rx.foreach(
                            State.ai_recommended_actions,
                            lambda item: rx.box(
                                rx.vstack(
                                    rx.hstack(
                                        rx.text(item["title"], color="var(--text-primary)", font_weight="700"),
                                        rx.spacer(),
                                        rx.badge(item["due_date"], color_scheme="orange"),
                                        width="100%",
                                        align="center",
                                    ),
                                    rx.text(item["expected_result"], color="var(--text-secondary)", font_size="0.86rem"),
                                    rx.hstack(
                                        rx.text(f"Owner sugerido: {item['owner']}", color="var(--text-muted)", font_size="0.82rem"),
                                        rx.spacer(),
                                        rx.button(
                                            "Enviar ao Plano de Ação",
                                            on_click=State.promote_ai_action(
                                                item["title"],
                                                item["owner"],
                                                item["due_date"],
                                                item["expected_result"],
                                            ),
                                            class_name="primary-soft-action",
                                        ),
                                        width="100%",
                                        align="center",
                                    ),
                                    align="start",
                                    spacing="2",
                                    width="100%",
                                ),
                                padding="0.95rem",
                                class_name="panel-card data-table-card",
                                **CARD_STYLE,
                            ),
                        ),
                        align="start",
                        width="100%",
                        spacing="3",
                    ),
                    width="100%",
                    padding="1rem",
                    **CARD_STYLE,
                ),
                align="start",
                width="100%",
                spacing="4",
            ),
            width="100%",
            padding="1.2rem",
            **CARD_STYLE,
        ),
        width="100%",
        on_mount=State.prepare_ai_view,
    )


def build_workspace_view(
    State,
    sidebar,
    app_header,
    dashboard_view,
    apis_view,
    auditoria_view,
    projetos_view,
    planos_view,
    permissoes_view,
    usuarios_view,
    clientes_view,
    tenants_view,
    papeis_view,
    responsabilidades_view,
    formularios_view,
    ia_view,
) -> rx.Component:
    return rx.box(
        rx.box(class_name="bg-orb bg-orb-left"),
        rx.box(class_name="bg-orb bg-orb-right"),
        rx.hstack(
            sidebar(),
            rx.box(
                app_header(),
                rx.box(
                    rx.cond(
                        State.active_view == "dashboard",
                        dashboard_view(),
                        rx.cond(
                            State.active_view == "apis",
                            apis_view(),
                            rx.cond(
                                State.active_view == "auditoria",
                                auditoria_view(),
                                rx.cond(
                                    State.active_view == "projetos",
                                    projetos_view(),
                                    rx.cond(
                                        State.active_view == "planos",
                                        planos_view(),
                                        rx.cond(
                                            State.active_view == "permissoes",
                                            permissoes_view(),
                                            rx.cond(
                                                State.active_view == "usuarios",
                                                usuarios_view(),
                                                rx.cond(
                                                    State.active_view == "clientes",
                                                    clientes_view(),
                                                    rx.cond(
                                                        State.active_view == "tenants",
                                                        tenants_view(),
                                                        rx.cond(
                                                            State.active_view == "papeis",
                                                            papeis_view(),
                                                            rx.cond(
                                                                State.active_view == "responsabilidades",
                                                                responsabilidades_view(),
                                                                rx.cond(
                                                                    State.active_view == "formularios",
                                                                    formularios_view(),
                                                                    ia_view(),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    padding="1rem 1rem 1.5rem",
                ),
                width="100%",
                min_height="100vh",
                class_name="workspace-main",
            ),
            width="100%",
            align="start",
            bg="var(--page-bg)",
            position="relative",
            z_index="1",
        ),
        width="100%",
        position="relative",
        overflow="hidden",
        class_name="workspace-shell",
    )
