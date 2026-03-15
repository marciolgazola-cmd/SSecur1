from typing import Any

import reflex as rx


def build_permissoes_view(
    State,
    CARD_STYLE: dict[str, Any],
    metric_card,
    field_block,
    table_text_cell,
    data_table,
) -> rx.Component:
    permissions_template_headers = ["Papel", "Escopo", "Descricao", "Permissoes base"]
    permissions_history_headers = ["Usuário", "Recurso", "Decisão", "Ações"]

    def permissions_table_cell(*children: rx.Component) -> rx.Component:
        return rx.vstack(
            *children,
            spacing="1",
            align="center",
            justify="center",
            text_align="center",
            width="100%",
            min_height="100%",
        )

    def permission_action_button_id(resource_token: str, decision: str) -> str:
        return f"permission-action-{decision}-{resource_token}"

    permission_dnd_script = """
    (() => {
      const version = 'v7-mount-bootstrap';
      const existing = window.__smartlabPermissionDnd;
      if (existing && existing.version === version) {
        existing.install();
        return;
      }

      const findInPath = (event, selector) => {
        const path = typeof event.composedPath === 'function' ? event.composedPath() : [];
        for (const node of path) {
          if (node && node instanceof Element && node.matches(selector)) {
            return node;
          }
        }
        const target = event.target;
        if (target && target instanceof Element) {
          return target.closest(selector);
        }
        return null;
      };

      const cleanup = () => {
        document.querySelectorAll('.permission-card.is-dragging').forEach((card) => {
          card.classList.remove('is-dragging');
        });
        document.querySelectorAll('.permission-card.is-drop-commit').forEach((card) => {
          card.classList.remove('is-drop-commit');
        });
        document.querySelectorAll('.permission-lane.is-drop-target').forEach((lane) => {
          lane.classList.remove('is-drop-target');
        });
        window.__smartlabPermissionDrag = null;
      };

      const handlers = {
        dragstart: (event) => {
          const card = findInPath(event, '.permission-card[data-resource]');
          if (!card) {
            return;
          }
          const resource = card.dataset.resource;
          const resourceToken = card.dataset.resourceToken;
          const origin = card.dataset.decision || 'disponivel';
          window.__smartlabPermissionDrag = { resource, resourceToken, origin };
          card.classList.add('is-dragging');
          if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', resourceToken || resource || '');
          }
        },
        dragend: () => {
          cleanup();
        },
        dragover: (event) => {
          const lane = findInPath(event, '.permission-lane[data-lane-decision]');
          if (!lane || !window.__smartlabPermissionDrag) {
            return;
          }
          event.preventDefault();
          if (event.dataTransfer) {
            event.dataTransfer.dropEffect = 'move';
          }
        },
        dragenter: (event) => {
          const lane = findInPath(event, '.permission-lane[data-lane-decision]');
          if (!lane || !window.__smartlabPermissionDrag) {
            return;
          }
          lane.classList.add('is-drop-target');
        },
        dragleave: (event) => {
          const lane = findInPath(event, '.permission-lane[data-lane-decision]');
          if (!lane) {
            return;
          }
          const related = event.relatedTarget;
          if (related && lane.contains(related)) {
            return;
          }
          lane.classList.remove('is-drop-target');
        },
        drop: (event) => {
          const lane = findInPath(event, '.permission-lane[data-lane-decision]');
          const drag = window.__smartlabPermissionDrag;
          if (!lane || !drag) {
            cleanup();
            return;
          }
          event.preventDefault();
          const decision = lane.dataset.laneDecision || 'disponivel';
          lane.classList.remove('is-drop-target');
          if (decision === drag.origin) {
            cleanup();
            return;
          }
          const actionButton = document.getElementById(`permission-action-${decision}-${drag.resourceToken}`);
          if (actionButton) {
            actionButton.click();
            const card = document.querySelector(`.permission-card[data-resource-token="${drag.resourceToken}"]`);
            if (card) {
              card.classList.add('is-drop-commit');
              window.setTimeout(() => card.classList.remove('is-drop-commit'), 260);
            }
          }
          cleanup();
        },
      };

      const dnd = {
        version,
        attached: false,
        cleanup,
        install() {
          if (this.attached) {
            return;
          }
          document.addEventListener('dragstart', handlers.dragstart, true);
          document.addEventListener('dragend', handlers.dragend, true);
          document.addEventListener('dragover', handlers.dragover, true);
          document.addEventListener('dragenter', handlers.dragenter, true);
          document.addEventListener('dragleave', handlers.dragleave, true);
          document.addEventListener('drop', handlers.drop, true);
          this.attached = true;
        },
        uninstall() {
          if (!this.attached) {
            return;
          }
          document.removeEventListener('dragstart', handlers.dragstart, true);
          document.removeEventListener('dragend', handlers.dragend, true);
          document.removeEventListener('dragover', handlers.dragover, true);
          document.removeEventListener('dragenter', handlers.dragenter, true);
          document.removeEventListener('dragleave', handlers.dragleave, true);
          document.removeEventListener('drop', handlers.drop, true);
          this.attached = false;
          cleanup();
        },
      };

      window.__smartlabPermissionDnd = dnd;
      dnd.install();
    })();
    """

    def permission_resource_card(item: dict[str, Any], current_decision: str) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.badge(item["module"], color_scheme="purple"),
                    rx.badge(item["action"], color_scheme="orange"),
                    rx.spacer(),
                    width="100%",
                ),
                rx.heading(item["label"], size="3", color="var(--text-primary)"),
                rx.text(item["description"], color="var(--text-secondary)", font_size="0.84rem"),
                rx.badge(
                    rx.cond(
                        current_decision == "permitido",
                        "Liberado",
                        rx.cond(current_decision == "negado", "Bloqueado", "Disponivel para decisao"),
                    ),
                    color_scheme=rx.cond(
                        current_decision == "permitido",
                        "green",
                        rx.cond(current_decision == "negado", "red", "gray"),
                    ),
                ),
                rx.hstack(
                    rx.cond(
                        current_decision != "permitido",
                        rx.button(
                            "Permitir",
                            on_click=State.apply_permission_from_catalog(item["resource"], "permitido"),
                            id=permission_action_button_id(item["resource_token"], "permitido"),
                            class_name="permission-card-action",
                            size="1",
                            bg="rgba(34,197,94,0.18)",
                            color="#15803d",
                            border="1px solid rgba(34,197,94,0.32)",
                            custom_attrs={
                                "data-resource-token": item["resource_token"],
                                "data-action-decision": "permitido",
                            },
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        current_decision != "negado",
                        rx.button(
                            "Negar",
                            on_click=State.apply_permission_from_catalog(item["resource"], "negado"),
                            id=permission_action_button_id(item["resource_token"], "negado"),
                            class_name="permission-card-action",
                            size="1",
                            bg="rgba(239,68,68,0.16)",
                            color="#b91c1c",
                            border="1px solid rgba(239,68,68,0.28)",
                            custom_attrs={
                                "data-resource-token": item["resource_token"],
                                "data-action-decision": "negado",
                            },
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        current_decision != "disponivel",
                        rx.button(
                            "Limpar",
                            on_click=State.clear_permission_from_catalog(item["resource"]),
                            id=permission_action_button_id(item["resource_token"], "disponivel"),
                            class_name="permission-card-action",
                            size="1",
                            bg="rgba(239,68,68,0.2)",
                            color="#fca5a5",
                            border="1px solid rgba(239,68,68,0.4)",
                            custom_attrs={
                                "data-resource-token": item["resource_token"],
                                "data-action-decision": "disponivel",
                            },
                        ),
                        rx.fragment(),
                    ),
                    width="100%",
                    spacing="2",
                    flex_wrap="wrap",
                ),
                align="start",
                spacing="2",
                width="100%",
            ),
            class_name="permission-card panel-card",
            draggable=True,
            transition="all 0.18s ease",
            _hover={
                "transform": "translateY(-6px)",
                "box_shadow": "0 26px 42px rgba(17, 24, 39, 0.22)",
                "border_color": "rgba(255, 122, 47, 0.58)",
                "background": "linear-gradient(180deg, rgba(255, 122, 47, 0.10), rgba(123, 115, 154, 0.08)), var(--card-bg)",
            },
            custom_attrs={
                "data-resource": item["resource"],
                "data-resource-token": item["resource_token"],
                "data-decision": current_decision,
            },
        )

    def permission_lane(title: str, tone: str, items: rx.Var) -> rx.Component:
        tone_bg = {
            "neutral": "rgba(148,163,184,0.10)",
            "success": "rgba(34,197,94,0.10)",
            "danger": "rgba(239,68,68,0.08)",
        }[tone]
        tone_border = {
            "neutral": "rgba(148,163,184,0.22)",
            "success": "rgba(34,197,94,0.28)",
            "danger": "rgba(239,68,68,0.24)",
        }[tone]
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(title, color="var(--text-primary)", font_weight="700"),
                    width="100%",
                    align="center",
                ),
                rx.foreach(
                    items,
                    lambda item: permission_resource_card(
                        item,
                        "permitido" if title == "Permitido" else "negado" if title == "Negado" else "disponivel",
                    ),
                ),
                rx.cond(
                    items.length() == 0,
                    rx.text("Nenhum item nesta coluna.", color="var(--text-muted)", font_size="0.84rem"),
                    rx.fragment(),
                ),
                width="100%",
                spacing="3",
                align="stretch",
            ),
            class_name="permission-lane",
            width="100%",
            background=tone_bg,
            border=f"1px dashed {tone_border}",
            custom_attrs={
                "data-lane-decision": (
                    "permitido" if title == "Permitido" else "negado" if title == "Negado" else "disponivel"
                )
            },
        )

    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.heading("RBAC e Permissões por Cliente", color="var(--text-primary)", size="5"),
                rx.text(
                    "Defina acessos por usuario com base em papel, modulo e recursos liberados. Esta tela sera a base do portal do cliente.",
                    color="var(--text-muted)",
                    font_size="0.9rem",
                ),
                rx.grid(
                    metric_card("Catalogo", State.permission_summary["catalogo"]),
                    metric_card("Permitidos", State.permission_summary["permitidos"]),
                    metric_card("Negados", State.permission_summary["negados"]),
                    metric_card("Pendentes", State.permission_summary["pendentes"]),
                    columns="4",
                    spacing="3",
                    width="100%",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            padding="1rem",
            **CARD_STYLE,
        ),
        rx.grid(
            rx.box(
                rx.vstack(
                    rx.heading("Contexto de acesso", color="var(--text-primary)", size="4"),
                    field_block(
                        "Usuario",
                        rx.select(
                            State.access_principal_options,
                            value=State.perm_user_email,
                            on_change=State.set_perm_user_email,
                            placeholder="Selecione um usuario existente",
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        "As permissoes se aplicam a uma conta ja criada.",
                    ),
                    field_block(
                        "Template de referencia",
                        rx.select(
                            State.role_template_options,
                            value=State.perm_selected_role_template,
                            on_change=State.set_perm_selected_role_template,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    field_block(
                        "Modulo",
                        rx.select(
                            State.permission_module_options,
                            value=State.perm_selected_module,
                            on_change=State.set_perm_selected_module,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                    ),
                    rx.text(
                        "Permissoes sao configuradas apenas sobre contas ja existentes. Crie ou ajuste o usuario no menu Usuarios.",
                        color="var(--text-muted)",
                        font_size="0.82rem",
                    ),
                    align="start",
                    spacing="3",
                    width="100%",
                ),
                padding="1rem",
                **CARD_STYLE,
            ),
            rx.box(
                rx.vstack(
                    rx.heading("Template RBAC", color="var(--text-primary)", size="4"),
                    rx.badge(State.selected_role_template_data["label"], color_scheme="purple"),
                    rx.text(State.selected_role_template_data["description"], color="var(--text-secondary)"),
                    rx.hstack(
                        rx.text("Escopo:", color="var(--text-muted)", font_size="0.85rem"),
                        rx.text(State.selected_role_template_data["scope"], color="var(--text-muted)", font_size="0.85rem"),
                        spacing="2",
                    ),
                    rx.box(
                        rx.text(State.selected_role_template_data["permissions_str"], color="var(--text-secondary)"),
                        class_name="permission-template-box",
                    ),
                    align="start",
                    spacing="3",
                    width="100%",
                ),
                padding="1rem",
                **CARD_STYLE,
            ),
            rx.box(
                rx.vstack(
                    rx.heading("Usuario selecionado", color="var(--text-primary)", size="4"),
                    rx.text(State.selected_access_principal["name"], color="var(--text-primary)", font_weight="700"),
                    rx.text(State.selected_access_principal["email"], color="var(--text-secondary)"),
                    rx.hstack(
                        rx.badge(State.selected_access_principal["role"], color_scheme="purple"),
                        rx.badge(State.selected_access_principal["scope"], color_scheme="orange"),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text("Tenant:", color="var(--text-muted)", font_size="0.84rem"),
                        rx.text(State.selected_access_principal["tenant"], color="var(--text-muted)", font_size="0.84rem"),
                        spacing="2",
                    ),
                    rx.cond(
                        State.selected_access_principal["client"] != "-",
                        rx.hstack(
                            rx.text("Cliente:", color="var(--text-muted)", font_size="0.84rem"),
                            rx.text(State.selected_access_principal["client"], color="var(--text-muted)", font_size="0.84rem"),
                            spacing="2",
                        ),
                        rx.text("Conta interna SmartLab", color="var(--text-muted)", font_size="0.84rem"),
                    ),
                    align="start",
                    spacing="2",
                    width="100%",
                ),
                padding="1rem",
                **CARD_STYLE,
            ),
            columns="3",
            spacing="4",
            width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading("Canvas de Acessos", color="var(--text-primary)", size="5"),
                    rx.spacer(),
                    rx.text(
                        "Arraste os cards entre Disponivel, Permitido e Negado. Os botoes continuam como fallback operacional.",
                        color="var(--text-muted)",
                        font_size="0.9rem",
                    ),
                    width="100%",
                ),
                rx.grid(
                    permission_lane("Disponivel", "neutral", State.permission_canvas_available),
                    permission_lane("Permitido", "success", State.permission_canvas_allowed),
                    permission_lane("Negado", "danger", State.permission_canvas_denied),
                    columns="3",
                    spacing="4",
                    width="100%",
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
            State.perm_user_email != "",
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
                            for header in permissions_template_headers
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
                        State.role_templates_data.length() == 0,
                        rx.box(
                            rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.86rem"),
                            width="100%",
                            padding="1.25rem 0.5rem 0.5rem",
                            text_align="center",
                        ),
                        rx.vstack(
                            rx.foreach(
                                State.role_templates_data,
                                lambda row: rx.grid(
                                    permissions_table_cell(
                                        rx.text(row["label"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                    ),
                                    permissions_table_cell(
                                        rx.badge(row["scope"], color_scheme="orange", width="fit-content", size="1"),
                                    ),
                                    permissions_table_cell(
                                        rx.text(
                                            row["description"],
                                            color="var(--text-secondary)",
                                            font_size="0.82rem",
                                            white_space="normal",
                                            word_break="break-word",
                                        ),
                                    ),
                                    permissions_table_cell(
                                        rx.text(
                                            row["permissions_str"],
                                            color="var(--text-secondary)",
                                            font_size="0.8rem",
                                            white_space="normal",
                                            word_break="break-word",
                                        ),
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
            rx.box(
                rx.text(
                    "Selecione um usuario para visualizar o template RBAC e as permissoes base aplicaveis.",
                    color="var(--text-muted)",
                ),
                width="100%",
                padding="1rem",
                class_name="panel-card data-table-card permission-empty-state",
                **CARD_STYLE,
            ),
        ),
        rx.cond(
            State.perm_user_email != "",
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
                            for header in permissions_history_headers
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
                        State.permission_boxes_data.length() == 0,
                        rx.box(
                            rx.text("Nenhum registro encontrado.", color="var(--text-muted)", font_size="0.86rem"),
                            width="100%",
                            padding="1.25rem 0.5rem 0.5rem",
                            text_align="center",
                        ),
                        rx.vstack(
                            rx.foreach(
                                State.permission_boxes_data,
                                lambda p: rx.grid(
                                    permissions_table_cell(
                                        rx.text(p["user_email"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                    ),
                                    permissions_table_cell(
                                        rx.text(
                                            p["resource"],
                                            color="var(--text-secondary)",
                                            font_size="0.82rem",
                                            white_space="normal",
                                            word_break="break-word",
                                        ),
                                    ),
                                    permissions_table_cell(
                                        rx.badge(
                                            p["decision"],
                                            color_scheme=rx.cond(p["decision"] == "permitido", "green", "red"),
                                            width="fit-content",
                                            size="1",
                                        ),
                                    ),
                                    permissions_table_cell(
                                        rx.button(
                                            "Remover",
                                            on_click=State.request_delete_confirmation("permission_box", p["id"], p["resource"]),
                                            variant="ghost",
                                            border="1px solid var(--input-border)",
                                            color="var(--text-secondary)",
                                            size="1",
                                        ),
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
            rx.box(
                rx.text(
                    "Selecione um usuario para visualizar as permissoes aplicadas e o historico do canvas.",
                    color="var(--text-muted)",
                ),
                width="100%",
                padding="1rem",
                class_name="panel-card data-table-card permission-empty-state",
                **CARD_STYLE,
            ),
        ),
        width="100%",
        spacing="4",
        on_mount=rx.call_script(permission_dnd_script),
        on_unmount=rx.call_script("window.__smartlabPermissionDnd?.cleanup?.();"),
    )
