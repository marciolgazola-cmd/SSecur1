from typing import Any

import reflex as rx


def build_toast(State, CARD_STYLE: dict[str, Any]) -> rx.Component:
    return rx.cond(
        State.toast_message != "",
        rx.box(
            rx.hstack(
                rx.icon(
                    tag=rx.cond(State.toast_type == "success", "circle_check", "triangle_alert"),
                    color=rx.cond(State.toast_type == "success", "#22c55e", "#ef4444"),
                ),
                rx.text(State.toast_message, color="var(--text-primary)"),
                rx.spacer(),
                rx.button("Fechar", on_click=State.clear_toast, variant="ghost", color="var(--text-muted)"),
                width="100%",
                align="center",
            ),
            position="fixed",
            bottom="18px",
            right="18px",
            width="380px",
            z_index="999",
            padding="0.9rem",
            **CARD_STYLE,
        ),
        rx.fragment(),
    )


def build_delete_confirm_modal(State, CARD_STYLE: dict[str, Any]) -> rx.Component:
    return rx.cond(
        State.delete_confirm_open,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.heading("Realmente deseja excluir?", color="var(--text-primary)", size="5"),
                    rx.text(
                        rx.cond(
                            State.pending_delete_label != "",
                            f"Confirme a exclusão de: {State.pending_delete_label}",
                            "Confirme a exclusão do registro selecionado.",
                        ),
                        color="var(--text-secondary)",
                        text_align="center",
                        width="100%",
                    ),
                    rx.hstack(
                        rx.button(
                            "Sim",
                            on_click=State.confirm_delete_action,
                            variant="ghost",
                            border="1px solid var(--input-border)",
                            color="var(--text-secondary)",
                            _hover={"bg": "var(--surface-soft)"},
                            min_width="110px",
                        ),
                        rx.button(
                            "Nao",
                            on_click=State.cancel_delete_confirmation,
                            bg="rgba(34,197,94,0.18)",
                            color="#86efac",
                            border="1px solid rgba(34,197,94,0.35)",
                            _hover={"bg": "rgba(34,197,94,0.24)"},
                            min_width="110px",
                        ),
                        spacing="3",
                        justify="center",
                        width="100%",
                    ),
                    spacing="4",
                    align="center",
                    width="100%",
                ),
                width="min(420px, 92vw)",
                padding="1.2rem",
                class_name="auth-shell",
                **CARD_STYLE,
            ),
            position="fixed",
            inset="0",
            bg="var(--overlay-bg)",
            display="flex",
            align_items="center",
            justify_content="center",
            z_index="1100",
        ),
        rx.fragment(),
    )


def build_landing_public(State, CARD_STYLE: dict[str, Any], smartlab_logo) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                smartlab_logo("64px"),
                rx.vstack(
                    rx.heading("SSecur1", color="var(--text-primary)", size="8"),
                    rx.text("Segurança que acontece na prática", color="var(--text-muted)"),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.cond(State.dark_mode, rx.icon(tag="sun", size=16), rx.icon(tag="moon", size=16)),
                    rx.text(State.theme_toggle_label, font_size="0.85rem"),
                    on_click=State.toggle_theme,
                    bg="var(--toggle-btn-bg)",
                    color="var(--toggle-btn-text)",
                    border="1px solid var(--toggle-btn-border)",
                    _hover={"bg": "var(--toggle-btn-hover-bg)"},
                ),
                rx.button(
                    "Entrar",
                    on_click=State.open_auth,
                    bg="rgba(255,122,47,0.18)",
                    color="#fdba74",
                    border="1px solid rgba(255,122,47,0.38)",
                    _hover={"transform": "scale(1.03)"},
                ),
                width="100%",
            ),
            rx.box(height="20px"),
            rx.hstack(
                rx.vstack(
                    rx.heading(
                        "Segurança que acontece na prática",
                        color="var(--text-primary)",
                        font_size=["2rem", "3rem"],
                        line_height="1.05",
                    ),
                    rx.text(
                        "Vamos juntos transformar cultura de segurança em vantagem competitiva sustentável.",
                        color="var(--text-muted)",
                        font_size="1.1rem",
                    ),
                    rx.hstack(
                        rx.button(
                            "Comece Grátis",
                            on_click=State.open_auth,
                            bg="rgba(255,122,47,0.18)",
                            color="#fdba74",
                            border="1px solid rgba(255,122,47,0.38)",
                            padding="1.1rem 1.4rem",
                            _hover={"transform": "scale(1.04)"},
                            transition="all 0.2s ease",
                        ),
                        rx.button(
                            "Ver Dashboard",
                            on_click=[State.open_auth],
                            variant="outline",
                            border="1px solid var(--input-border)",
                            color="var(--text-primary)",
                        ),
                    ),
                    align="start",
                    spacing="5",
                    width="100%",
                ),
                rx.box(
                    smartlab_logo("220px"),
                    class_name="pulse-soft",
                    padding="1rem",
                ),
                width="100%",
                gap="8",
                flex_direction="row",
            ),
            rx.grid(
                rx.foreach(
                    [
                        ("Diagnóstico de Cultura", "Mapeie maturidade, comportamentos críticos e variação cultural por unidade."),
                        ("Liderança em Segurança", "Conecte atuação da liderança com resultados em campo e produtividade segura."),
                        ("IA de Recomendação", "Converta dados em recomendações práticas e decisões estratégicas assertivas."),
                    ],
                    lambda item: rx.box(
                        rx.heading(item[0], color="var(--text-primary)", size="5"),
                        rx.text(item[1], color="var(--text-secondary)"),
                        bg="var(--surface-soft)",
                        border="1px solid var(--card-border)",
                        border_radius="16px",
                        padding="1.2rem",
                        backdrop_filter="blur(10px)",
                        transition="all 0.22s ease",
                        box_shadow="0 12px 28px rgba(15, 23, 42, 0.08)",
                        _hover={
                            "transform": "translateY(-8px)",
                            "border_color": "rgba(255,122,47,0.38)",
                            "background": "linear-gradient(180deg, rgba(255,122,47,0.10), rgba(123,115,154,0.06)), var(--surface-soft)",
                            "box_shadow": "0 24px 40px rgba(15, 23, 42, 0.16)",
                        },
                    ),
                ),
                columns="3",
                spacing="4",
                width="100%",
            ),
            rx.box(
                rx.hstack(
                    rx.button("◀", on_click=State.next_testimonial, variant="soft", color_scheme="purple"),
                    rx.vstack(
                        rx.text(State.current_testimonial["text"], color="var(--text-primary)", font_size="1.1rem"),
                        rx.text(State.current_testimonial["name"], color="var(--accent-strong)"),
                        align="start",
                    ),
                    rx.button("▶", on_click=State.next_testimonial, variant="soft", color_scheme="purple"),
                    width="100%",
                    align="center",
                ),
                width="100%",
                padding="1rem",
                **CARD_STYLE,
            ),
            max_width="1180px",
            width="100%",
            margin="0 auto",
            padding="2rem 1rem 4rem",
            spacing="8",
        ),
        min_height="100vh",
        background="var(--page-bg)",
    )
