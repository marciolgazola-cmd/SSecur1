from typing import Any

import reflex as rx


def build_ia_view(State, CARD_STYLE: dict[str, Any]) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("Assistente Conversacional SSecur1", color="var(--text-primary)", size="6"),
                rx.text(
                    "Use IA para entender dashboards, priorizar ações e orientar entrevistas de diagnóstico.",
                    color="var(--text-muted)",
                ),
                rx.text_area(
                    placeholder="Pergunte: Como interpretar Segurança vs Produtividade?",
                    value=State.ai_prompt,
                    on_change=State.set_ai_prompt,
                    bg="var(--input-bg)",
                    color="var(--text-primary)",
                    min_height="120px",
                ),
                rx.box(
                    rx.vstack(
                        rx.text("Dropzone: arraste uma pergunta da tela de Formulários para cá.", color="var(--text-muted)"),
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
                    padding="0.9rem",
                    border="1px dashed var(--input-border)",
                    border_radius="14px",
                    bg="var(--surface-soft)",
                    on_click=State.drop_question_into_prompt,
                ),
                rx.button(
                    "Gerar orientação",
                    on_click=State.ask_ai,
                    class_name="primary-soft-action",
                ),
                rx.box(
                    rx.text(State.ai_answer, white_space="pre-wrap", color="var(--text-secondary)"),
                    width="100%",
                    min_height="140px",
                    padding="1rem",
                    bg="var(--surface-soft)",
                    border="1px solid var(--input-border)",
                    border_radius="12px",
                ),
                rx.text(
                    "Resultados suportam: clareza real da cultura, base para trilha da liderança, redução de riscos e custos.",
                    color="var(--text-muted)",
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
    )


def build_workspace_view(
    State,
    sidebar,
    app_header,
    dashboard_view,
    apis_view,
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
