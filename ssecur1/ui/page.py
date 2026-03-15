import reflex as rx


def build_nav_button(State, label: str, icon: str, view: str) -> rx.Component:
    return rx.button(
        rx.hstack(
            rx.icon(tag=icon, color="var(--nav-icon)", size=18),
            rx.cond(
                State.sidebar_collapsed,
                rx.fragment(),
                rx.text(label, color="var(--nav-text)", font_size="0.96rem", font_weight="500"),
            ),
            width="100%",
            align="center",
            spacing="3",
        ),
        on_click=State.set_active_view(view),
        width="100%",
        justify_content=rx.cond(State.sidebar_collapsed, "center", "flex-start"),
        bg=rx.cond(State.active_view == view, "var(--active-item-bg)", "transparent"),
        border=rx.cond(State.active_view == view, "1px solid var(--active-item-border)", "1px solid transparent"),
        _hover={"bg": "var(--active-item-hover-bg)", "transform": "translateX(1px)"},
        transition="all 0.2s ease",
        border_radius="12px",
        padding="0.7rem",
        class_name="nav-item",
    )


def build_main_page(State, workspace_view, landing_public, auth_modal, toast, delete_confirm_modal) -> rx.Component:
    return rx.cond(
        State.dark_mode,
        rx.theme(
            rx.box(
                rx.cond(State.is_logged, workspace_view(), landing_public()),
                auth_modal(),
                delete_confirm_modal(),
                toast(),
                class_name="theme-dark app-theme",
            ),
            appearance="dark",
            accent_color="orange",
            radius="large",
        ),
        rx.theme(
            rx.box(
                rx.cond(State.is_logged, workspace_view(), landing_public()),
                auth_modal(),
                delete_confirm_modal(),
                toast(),
                class_name="theme-light app-theme",
            ),
            appearance="light",
            accent_color="orange",
            radius="large",
        ),
    )
