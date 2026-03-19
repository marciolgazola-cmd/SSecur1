from typing import Any

import reflex as rx

from ssecur1.ui.admin_people import build_clientes_view, build_usuarios_view
from ssecur1.ui.admin_security import (
    build_papeis_view,
    build_responsabilidades_view,
    build_tenants_view,
)
from ssecur1.ui.auth import build_auth_modal
from ssecur1.ui.common import (
    build_app_header,
    build_custom_option_field,
    build_data_table,
    build_field_block,
    build_metric_card,
    build_table_text_cell,
    build_workflow_connection_line,
    build_workflow_node,
    build_sidebar,
)
from ssecur1.ui.formularios import build_formularios_view
from ssecur1.ui.operacoes import build_apis_view, build_auditoria_view, build_dashboard_view, build_planos_view
from ssecur1.ui.page import build_main_page, build_nav_button
from ssecur1.ui.permissoes import build_permissoes_view
from ssecur1.ui.pesquisa_builder import build_pesquisa_builder_view
from ssecur1.ui.projetos import build_projetos_view
from ssecur1.ui.public import build_delete_confirm_modal, build_landing_public, build_toast
from ssecur1.ui.shell import build_ia_view, build_workspace_view


CARD_STYLE = {
    "bg": "var(--card-bg)",
    "backdrop_filter": "blur(10px)",
    "border": "1px solid var(--card-border)",
    "border_radius": "16px",
    "box_shadow": "0 12px 28px var(--card-shadow)",
}


def smartlab_logo(size: str = "44px") -> rx.Component:
    return rx.image(
        src="/LogoSmartLab.jpeg",
        width=size,
        height="auto",
        alt="Logo SSecur1",
        border_radius="10px",
        object_fit="contain",
    )


def build_main_page_component(State) -> rx.Component:
    def nav_button(label: str, icon: str, view: str) -> rx.Component:
        return build_nav_button(State=State, label=label, icon=icon, view=view)

    def toast() -> rx.Component:
        return build_toast(State=State, CARD_STYLE=CARD_STYLE)

    def delete_confirm_modal() -> rx.Component:
        return build_delete_confirm_modal(State=State, CARD_STYLE=CARD_STYLE)

    def landing_public() -> rx.Component:
        return build_landing_public(State=State, CARD_STYLE=CARD_STYLE, smartlab_logo=smartlab_logo)

    def app_header() -> rx.Component:
        return build_app_header(State=State, smartlab_logo=smartlab_logo)

    def sidebar() -> rx.Component:
        return build_sidebar(State=State, nav_button=nav_button)

    def metric_card(title: str, value: rx.Var) -> rx.Component:
        return build_metric_card(CARD_STYLE=CARD_STYLE, title=title, value=value)

    def field_block(label: str, control: rx.Component, help_text: str = "") -> rx.Component:
        return build_field_block(label=label, control=control, help_text=help_text)

    def custom_option_field(
        label: str,
        value: rx.Var,
        on_change,
        on_confirm,
        placeholder: str,
        help_text: str = "",
    ) -> rx.Component:
        return build_custom_option_field(
            label=label,
            value=value,
            on_change=on_change,
            on_confirm=on_confirm,
            placeholder=placeholder,
            help_text=help_text,
        )

    def table_text_cell(primary: rx.Component, secondary: rx.Component | None = None) -> rx.Component:
        return build_table_text_cell(primary=primary, secondary=secondary)

    def data_table(headers: list[str], rows: rx.Var, row_builder) -> rx.Component:
        return build_data_table(CARD_STYLE=CARD_STYLE, headers=headers, rows=rows, row_builder=row_builder)

    def workflow_connection_line(line_type: rx.Var) -> rx.Component:
        return build_workflow_connection_line(line_type=line_type)

    def workflow_node(node_data: dict[str, Any]) -> rx.Component:
        return build_workflow_node(State=State, node_data=node_data)

    def apis_view() -> rx.Component:
        return build_apis_view(State=State, CARD_STYLE=CARD_STYLE, data_table=data_table)

    def auditoria_view() -> rx.Component:
        return build_auditoria_view(State=State, CARD_STYLE=CARD_STYLE)

    def dashboard_view() -> rx.Component:
        return build_dashboard_view(
            State=State,
            CARD_STYLE=CARD_STYLE,
            metric_card=metric_card,
            data_table=data_table,
        )

    def pesquisa_builder_view() -> rx.Component:
        return build_pesquisa_builder_view(
            State=State,
            CARD_STYLE=CARD_STYLE,
            field_block=field_block,
            custom_option_field=custom_option_field,
            data_table=data_table,
        )

    def projetos_view() -> rx.Component:
        return build_projetos_view(
            State=State,
            CARD_STYLE=CARD_STYLE,
            custom_option_field=custom_option_field,
            workflow_node=workflow_node,
            workflow_connection_line=workflow_connection_line,
            pesquisa_builder_view=pesquisa_builder_view,
        )

    def planos_view() -> rx.Component:
        return build_planos_view(State=State, CARD_STYLE=CARD_STYLE)

    def permissoes_view() -> rx.Component:
        return build_permissoes_view(
            State=State,
            CARD_STYLE=CARD_STYLE,
            metric_card=metric_card,
            field_block=field_block,
            table_text_cell=table_text_cell,
            data_table=data_table,
        )

    def clientes_view() -> rx.Component:
        return build_clientes_view(
            State=State,
            CARD_STYLE=CARD_STYLE,
            field_block=field_block,
            custom_option_field=custom_option_field,
            table_text_cell=table_text_cell,
            data_table=data_table,
        )

    def usuarios_view() -> rx.Component:
        return build_usuarios_view(
            State=State,
            CARD_STYLE=CARD_STYLE,
            field_block=field_block,
            custom_option_field=custom_option_field,
            table_text_cell=table_text_cell,
            data_table=data_table,
        )

    def tenants_view() -> rx.Component:
        return build_tenants_view(
            State=State,
            CARD_STYLE=CARD_STYLE,
            field_block=field_block,
            table_text_cell=table_text_cell,
            data_table=data_table,
        )

    def papeis_view() -> rx.Component:
        return build_papeis_view(
            State=State,
            CARD_STYLE=CARD_STYLE,
            field_block=field_block,
            data_table=data_table,
        )

    def responsabilidades_view() -> rx.Component:
        return build_responsabilidades_view(
            State=State,
            CARD_STYLE=CARD_STYLE,
            field_block=field_block,
            data_table=data_table,
        )

    def formularios_view() -> rx.Component:
        return build_formularios_view(
            State=State,
            CARD_STYLE=CARD_STYLE,
            metric_card=metric_card,
            field_block=field_block,
            table_text_cell=table_text_cell,
            data_table=data_table,
        )

    def ia_view() -> rx.Component:
        return build_ia_view(State=State, CARD_STYLE=CARD_STYLE)

    def workspace_view() -> rx.Component:
        return build_workspace_view(
            State=State,
            sidebar=sidebar,
            app_header=app_header,
            dashboard_view=dashboard_view,
            apis_view=apis_view,
            auditoria_view=auditoria_view,
            projetos_view=projetos_view,
            planos_view=planos_view,
            permissoes_view=permissoes_view,
            usuarios_view=usuarios_view,
            clientes_view=clientes_view,
            tenants_view=tenants_view,
            papeis_view=papeis_view,
            responsabilidades_view=responsabilidades_view,
            formularios_view=formularios_view,
            ia_view=ia_view,
        )

    def auth_modal() -> rx.Component:
        return build_auth_modal(State=State, CARD_STYLE=CARD_STYLE, smartlab_logo=smartlab_logo)

    return build_main_page(
        State=State,
        workspace_view=workspace_view,
        landing_public=landing_public,
        auth_modal=auth_modal,
        toast=toast,
        delete_confirm_modal=delete_confirm_modal,
    )
