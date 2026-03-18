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
    permissions_template_headers = ["Papel", "Origem", "Contexto", "Alcance", "Permissoes base", "Governanca", "Responsabilidades", "Acoes"]
    permissions_history_headers = ["Usuário", "Recurso", "Decisão", "Ações"]

    def permission_metric_card(title: str, value: rx.Var, icon_tag: str, accent_color: str) -> rx.Component:
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

    def role_permission_action_button_id(token: str, decision: str) -> str:
        return f"role-permission-action-{decision}-{token.replace(':', '-').replace('_', '-')}"

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

    role_permission_dnd_script = """
    (() => {
      const version = 'role-dnd-v1';
      const existing = window.__smartlabRolePermissionDnd;
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
        document.querySelectorAll('.role-permission-card.is-dragging').forEach((card) => card.classList.remove('is-dragging'));
        document.querySelectorAll('.role-permission-lane.is-drop-target').forEach((lane) => lane.classList.remove('is-drop-target'));
        window.__smartlabRolePermissionDrag = null;
      };

      const handlers = {
        dragstart: (event) => {
          const card = findInPath(event, '.role-permission-card[data-token]');
          if (!card) return;
          const token = card.dataset.token;
          const origin = card.dataset.bucket || 'available';
          window.__smartlabRolePermissionDrag = { token, origin };
          card.classList.add('is-dragging');
          if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', token || '');
          }
        },
        dragend: () => cleanup(),
        dragover: (event) => {
          const lane = findInPath(event, '.role-permission-lane[data-bucket]');
          if (!lane || !window.__smartlabRolePermissionDrag) return;
          event.preventDefault();
          if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
        },
        dragenter: (event) => {
          const lane = findInPath(event, '.role-permission-lane[data-bucket]');
          if (!lane || !window.__smartlabRolePermissionDrag) return;
          lane.classList.add('is-drop-target');
        },
        dragleave: (event) => {
          const lane = findInPath(event, '.role-permission-lane[data-bucket]');
          if (!lane) return;
          const related = event.relatedTarget;
          if (related && lane.contains(related)) return;
          lane.classList.remove('is-drop-target');
        },
        drop: (event) => {
          const lane = findInPath(event, '.role-permission-lane[data-bucket]');
          const drag = window.__smartlabRolePermissionDrag;
          if (!lane || !drag) {
            cleanup();
            return;
          }
          event.preventDefault();
          const bucket = lane.dataset.bucket || 'available';
          lane.classList.remove('is-drop-target');
          if (bucket === drag.origin) {
            cleanup();
            return;
          }
          const actionButton = document.getElementById(`role-permission-action-${bucket}-${drag.token.replace(/[:_]/g, '-')}`);
          if (actionButton) actionButton.click();
          cleanup();
        },
      };

      const dnd = {
        version,
        attached: false,
        cleanup,
        install() {
          if (this.attached) return;
          document.addEventListener('dragstart', handlers.dragstart, true);
          document.addEventListener('dragend', handlers.dragend, true);
          document.addEventListener('dragover', handlers.dragover, true);
          document.addEventListener('dragenter', handlers.dragenter, true);
          document.addEventListener('dragleave', handlers.dragleave, true);
          document.addEventListener('drop', handlers.drop, true);
          this.attached = true;
        },
      };

      window.__smartlabRolePermissionDnd = dnd;
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
                rx.cond(
                    current_decision != "permitido",
                    rx.button(
                        "Permitir",
                        on_click=State.apply_permission_from_catalog(item["resource"], "permitido"),
                        id=permission_action_button_id(item["resource_token"], "permitido"),
                        display="none",
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
                        display="none",
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
                        display="none",
                        custom_attrs={
                            "data-resource-token": item["resource_token"],
                            "data-action-decision": "disponivel",
                        },
                    ),
                    rx.fragment(),
                ),
                align="start",
                spacing="2",
                width="100%",
            ),
            class_name="permission-card panel-card",
            draggable=True,
            width="100%",
            min_height="176px",
            padding="0.85rem",
            border="1px solid rgba(148,163,184,0.18)",
            border_radius="16px",
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
                rx.cond(
                    items.length() > 0,
                    rx.grid(
                        rx.foreach(
                            items,
                            lambda item: permission_resource_card(
                                item,
                                "permitido" if title == "Permitido" else "negado" if title == "Negado" else "disponivel",
                            ),
                        ),
                        columns="repeat(2, minmax(0, 1fr))",
                        spacing="3",
                        width="100%",
                    ),
                    rx.fragment(),
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

    def role_permission_card(item: dict[str, Any], bucket: str) -> rx.Component:
        is_selected = bucket == "selected"
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.badge(item["module"], color_scheme="purple", size="1"),
                    rx.badge("Escolhida" if is_selected else "Disponivel", color_scheme="green" if is_selected else "gray", size="1"),
                    rx.spacer(),
                    width="100%",
                ),
                rx.text(item["label"], color="var(--text-primary)", font_weight="600"),
                rx.text(item["description"], color="var(--text-secondary)", font_size="0.8rem"),
                rx.text(item["token"], color="var(--text-muted)", font_size="0.76rem"),
                rx.cond(
                    is_selected,
                    rx.button(
                        "Remover",
                        on_click=State.remove_role_permission_choice(item["token"]),
                        id=role_permission_action_button_id(item["token"], "available"),
                        display="none",
                    ),
                    rx.button(
                        "Adicionar",
                        on_click=State.add_role_permission_token(item["token"]),
                        id=role_permission_action_button_id(item["token"], "selected"),
                        display="none",
                    ),
                ),
                spacing="2",
                align="start",
                width="100%",
            ),
            class_name="role-permission-card panel-card",
            draggable=True,
            width="100%",
            min_height="126px",
            padding="0.72rem",
            border="1px solid rgba(148,163,184,0.18)",
            border_radius="18px",
            background="linear-gradient(180deg, rgba(255,255,255,0.02), rgba(15,23,42,0.02)), var(--card-bg)",
            box_shadow="0 12px 24px rgba(15,23,42,0.08)",
            transition="all 0.18s ease",
            _hover={
                "transform": "translateY(-4px)",
                "box_shadow": "0 20px 34px rgba(17, 24, 39, 0.18)",
                "border_color": "rgba(255, 122, 47, 0.48)",
            },
            custom_attrs={
                "data-token": item["token"],
                "data-bucket": bucket,
            },
        )

    def role_permission_lane(title: str, tone: str, bucket: str, items: rx.Var) -> rx.Component:
        tone_bg = {
            "neutral": "rgba(148,163,184,0.10)",
            "success": "rgba(34,197,94,0.10)",
        }[tone]
        tone_border = {
            "neutral": "rgba(148,163,184,0.22)",
            "success": "rgba(34,197,94,0.28)",
        }[tone]
        lane_columns = "repeat(4, minmax(0, 1fr))" if bucket == "available" else "repeat(2, minmax(0, 1fr))"
        return rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(title, color="var(--text-primary)", font_weight="700"),
                    rx.spacer(),
                    rx.badge(items.length().to_string(), color_scheme="gray", size="1"),
                    width="100%",
                    align="center",
                ),
                rx.cond(
                    items.length() > 0,
                    rx.grid(
                        rx.foreach(items, lambda item: role_permission_card(item, bucket)),
                        columns=lane_columns,
                        spacing="3",
                        width="100%",
                        justify_content="start",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    items.length() == 0,
                    rx.text("Arraste cards para esta coluna.", color="var(--text-muted)", font_size="0.84rem"),
                    rx.fragment(),
                ),
                width="100%",
                spacing="3",
                align="stretch",
            ),
            class_name="role-permission-lane",
            width="100%",
            background=tone_bg,
            border=f"1px dashed {tone_border}",
            border_radius="18px",
            padding="1rem",
            min_height="420px",
            box_shadow="inset 0 1px 0 rgba(255,255,255,0.04)",
            custom_attrs={"data-bucket": bucket},
        )

    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading("RBAC e Permissões por Cliente", color="var(--text-primary)", size="5"),
                    rx.spacer(),
                    rx.hstack(
                        rx.button(
                            "Governança",
                            on_click=State.set_permissions_tab("governanca"),
                            bg=rx.cond(
                                State.permissions_tab == "governanca",
                                "rgba(255,122,47,0.18)",
                                "transparent",
                            ),
                            color=rx.cond(
                                State.permissions_tab == "governanca",
                                "#fdba74",
                                "var(--text-secondary)",
                            ),
                            border=rx.cond(
                                State.permissions_tab == "governanca",
                                "1px solid rgba(255,122,47,0.38)",
                                "1px solid var(--input-border)",
                            ),
                            size="2",
                            width="100%",
                            flex="1",
                            justify_content="center",
                        ),
                        rx.button(
                            "Associação",
                            on_click=State.set_permissions_tab("associacao"),
                            bg=rx.cond(
                                State.permissions_tab == "associacao",
                                "rgba(255,122,47,0.18)",
                                "transparent",
                            ),
                            color=rx.cond(
                                State.permissions_tab == "associacao",
                                "#fdba74",
                                "var(--text-secondary)",
                            ),
                            border=rx.cond(
                                State.permissions_tab == "associacao",
                                "1px solid rgba(255,122,47,0.38)",
                                "1px solid var(--input-border)",
                            ),
                            size="2",
                            width="100%",
                            flex="1",
                            justify_content="center",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.text(
                    "Defina acessos por usuario com base em papel, modulo e recursos liberados. Esta tela sera a base do portal do cliente.",
                    color="var(--text-muted)",
                    font_size="0.9rem",
                ),
                rx.grid(
                    permission_metric_card("Catalogo", State.permission_summary["catalogo"], "layout_grid", "#60a5fa"),
                    permission_metric_card("Permitidos", State.permission_summary["permitidos"], "shield_check", "#34d399"),
                    permission_metric_card("Negados", State.permission_summary["negados"], "shield_x", "#f87171"),
                    permission_metric_card("Pendentes", State.permission_summary["pendentes"], "clock_3", "#f59e0b"),
                    columns="4",
                    spacing="3",
                    width="100%",
                ),
                rx.box(
                    rx.text(
                        "Use a aba de Governança para desenhar os papéis e a aba de Associação para liberar acessos em usuários reais.",
                        color="var(--text-secondary)",
                        font_size="0.84rem",
                    ),
                    width="100%",
                    padding="0.85rem 1rem",
                    class_name="workspace-guide",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            padding="1rem",
            width="100%",
            **CARD_STYLE,
        ),
        rx.cond(
            State.permissions_tab == "governanca",
            rx.fragment(
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.heading("Templates RBAC Base", color="var(--text-primary)", size="5"),
                            rx.spacer(),
                            rx.text(
                                "Aqui ficam os perfis globais da SmartLab e os perfis locais do tenant atual, separados por origem, contexto e alcance.",
                                color="var(--text-muted)",
                                font_size="0.88rem",
                            ),
                            width="100%",
                            align="center",
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
                                        for header in permissions_template_headers
                                    ],
                                    columns="8",
                                    width="100%",
                                    align_items="center",
                                    justify_items="center",
                                    padding="0.1rem 0 0.85rem",
                                    border_bottom="1px solid rgba(148,163,184,0.18)",
                                    column_gap="0.9rem",
                                ),
                                rx.vstack(
                                    rx.foreach(
                                        State.role_templates_data,
                                        lambda row: rx.grid(
                                            permissions_table_cell(
                                                rx.vstack(
                                                    rx.cond(
                                                        State.editing_role_template_key == row["key"],
                                                        rx.input(
                                                            value=State.new_role_name,
                                                            on_change=State.set_new_role_name,
                                                            bg="var(--input-bg)",
                                                            color="var(--text-primary)",
                                                            width="100%",
                                                            is_disabled=row["origin"] == "global",
                                                        ),
                                                        rx.text(row["label"], color="var(--text-primary)", font_weight="600", font_size="0.84rem"),
                                                    ),
                                                    spacing="1",
                                                    align="center",
                                                    width="100%",
                                                ),
                                            ),
                                            permissions_table_cell(
                                                rx.badge(row["origin_label"], color_scheme=rx.cond(row["origin"] == "global", "purple", "green"), width="fit-content", size="1"),
                                            ),
                                            permissions_table_cell(
                                                rx.badge(row["context_label"], color_scheme="orange", width="fit-content", size="1"),
                                            ),
                                            permissions_table_cell(
                                                rx.badge(row["reach_label"], color_scheme="cyan", width="fit-content", size="1"),
                                            ),
                                            permissions_table_cell(
                                                rx.cond(
                                                    State.editing_role_template_key == row["key"],
                                                    rx.vstack(
                                                        rx.text("Edite as permissões no bloco abaixo. Esta linha fica sincronizada com o editor.", color="var(--text-muted)", font_size="0.78rem"),
                                                        rx.text(State.selected_role_permissions_summary, color="var(--text-secondary)", font_size="0.8rem", white_space="normal"),
                                                        spacing="1",
                                                        width="100%",
                                                    ),
                                                    rx.text(
                                                        row["permissions_str"],
                                                        color="var(--text-secondary)",
                                                        font_size="0.8rem",
                                                        white_space="normal",
                                                        word_break="break-word",
                                                    ),
                                                ),
                                            ),
                                            permissions_table_cell(
                                                rx.vstack(
                                                    rx.text(
                                                        row["description"],
                                                        color="var(--text-secondary)",
                                                        font_size="0.82rem",
                                                        white_space="normal",
                                                        word_break="break-word",
                                                    ),
                                                    rx.text(
                                                        row["governance"],
                                                        color="var(--text-muted)",
                                                        font_size="0.77rem",
                                                        white_space="normal",
                                                        word_break="break-word",
                                                    ),
                                                    spacing="1",
                                                    width="100%",
                                                ),
                                            ),
                                            permissions_table_cell(
                                                rx.cond(
                                                    State.editing_role_template_key == row["key"],
                                                    rx.text_area(
                                                        value=State.new_role_responsibilities,
                                                        on_change=State.set_new_role_responsibilities,
                                                        min_height="92px",
                                                        bg="var(--input-bg)",
                                                        color="var(--text-primary)",
                                                        width="100%",
                                                    ),
                                                    rx.text(
                                                        row["responsibilities_str"],
                                                        color="var(--text-secondary)",
                                                        font_size="0.8rem",
                                                        white_space="pre-wrap",
                                                        word_break="break-word",
                                                    ),
                                                ),
                                            ),
                                            permissions_table_cell(
                                                rx.hstack(
                                                    rx.cond(
                                                        State.editing_role_template_key == row["key"],
                                                        rx.fragment(
                                                            rx.button(
                                                                "Salvar",
                                                                on_click=State.save_role_template_row,
                                                                class_name="primary-soft-action",
                                                            ),
                                                            rx.button(
                                                                "Cancelar",
                                                                on_click=State.reset_role_form,
                                                                min_height="40px",
                                                                padding="0 1rem",
                                                                bg="rgba(250,204,21,0.12)",
                                                                color="#fef08a",
                                                                border="1px solid rgba(250,204,21,0.28)",
                                                                border_radius="12px",
                                                                font_weight="500",
                                                                box_shadow="none",
                                                            ),
                                                        ),
                                                        rx.fragment(
                                                            rx.cond(
                                                                row["can_edit"],
                                                                rx.button(
                                                                    "Alterar",
                                                                    on_click=State.start_edit_role_template(row["key"]),
                                                                    bg="rgba(255,122,47,0.18)",
                                                                    color="#fdba74",
                                                                    border="1px solid rgba(255,122,47,0.38)",
                                                                    size="2",
                                                                ),
                                                                rx.fragment(),
                                                            ),
                                                            rx.cond(
                                                                row["can_delete"],
                                                                rx.button(
                                                                    "Excluir",
                                                                    on_click=State.request_delete_confirmation("role", row["id"], row["label"]),
                                                                    bg="rgba(239,68,68,0.2)",
                                                                    color="#fca5a5",
                                                                    border="1px solid rgba(239,68,68,0.4)",
                                                                    size="2",
                                                                ),
                                                                rx.fragment(),
                                                            ),
                                                        ),
                                                    ),
                                                    spacing="2",
                                                    justify="end",
                                                    width="100%",
                                                    flex_wrap="wrap",
                                                ),
                                            ),
                                            columns="8",
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
                                width="100%",
                                spacing="3",
                            ),
                            width="100%",
                            overflow_x="auto",
                            padding="0.95rem 1rem",
                            class_name="panel-card data-table-card",
                            **CARD_STYLE,
                        ),
                        width="100%",
                        spacing="4",
                        align="start",
                    ),
                    width="100%",
                    padding="1rem",
                    **CARD_STYLE,
                ),
                rx.box(
                    rx.vstack(
                        rx.heading("Governança de Papéis e Responsabilidades", color="var(--text-primary)", size="5"),
                        rx.text(
                            "Modele o papel completo em um unico cadastro: nome, permissoes e responsabilidades de aprovacao, revisao ou operacao.",
                            color="var(--text-muted)",
                            font_size="0.88rem",
                        ),
                        rx.box(
                            rx.vstack(
                                rx.heading("Papel Completo", color="var(--text-primary)", size="4"),
                                rx.text(
                                    "Cadastre um perfil local do tenant. A edição dos perfis já existentes acontece diretamente na tabela acima.",
                                    color="var(--text-muted)",
                                    font_size="0.82rem",
                                ),
                                field_block(
                                    "Nome do papel",
                                    rx.input(
                                        placeholder="Ex.: RH Gestão",
                                        value=State.new_role_name,
                                        on_change=State.set_new_role_name,
                                        bg="var(--input-bg)",
                                        color="var(--text-primary)",
                                        width="100%",
                                    ),
                                ),
                                field_block(
                                    "Escolha guiada das permissões",
                                    rx.vstack(
                                        rx.select(
                                            State.role_permission_module_options,
                                            value=State.role_permission_module_filter,
                                            on_change=State.set_role_permission_module_filter,
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            width="100%",
                                        ),
                                        rx.hstack(
                                            rx.box(
                                                role_permission_lane(
                                                    "Disponíveis para o papel",
                                                    "neutral",
                                                    "available",
                                                    State.available_role_permissions_data,
                                                ),
                                                width="64%",
                                                min_width="0",
                                            ),
                                            rx.box(
                                                role_permission_lane(
                                                    "Permissões já escolhidas",
                                                    "success",
                                                    "selected",
                                                    State.chosen_role_permissions_data,
                                                ),
                                                width="36%",
                                                min_width="0",
                                            ),
                                            spacing="4",
                                            width="100%",
                                            align="start",
                                        ),
                                        spacing="3",
                                        width="100%",
                                    ),
                                    "Arraste as permissões entre as colunas ou use os botões dos cards. A esquerda ficam as disponíveis; a direita, o que fará parte do papel.",
                                ),
                                field_block(
                                    "Responsabilidades do papel",
                                    rx.text_area(
                                        placeholder="Ex.: Aprova acessos do tenant\nRevisa permissões trimestralmente\nOpera desbloqueios urgentes",
                                        value=State.new_role_responsibilities,
                                        on_change=State.set_new_role_responsibilities,
                                        min_height="110px",
                                        bg="var(--input-bg)",
                                        color="var(--text-primary)",
                                        width="100%",
                                    ),
                                    "Use uma linha por responsabilidade. Esse bloco registra a governanca do papel no mesmo cadastro.",
                                ),
                                rx.cond(
                                    State.can_manage_roles,
                                    rx.hstack(
                                        rx.button(
                                            "Criar Papel",
                                            on_click=State.create_role,
                                            class_name="primary-soft-action",
                                        ),
                                        spacing="2",
                                        width="100%",
                                    ),
                                    rx.badge("Sem permissão para editar papéis", color_scheme="red"),
                                ),
                                width="100%",
                                spacing="3",
                                align="start",
                            ),
                            padding="1rem",
                            **CARD_STYLE,
                        ),
                        width="100%",
                        spacing="4",
                        align="start",
                    ),
                    width="100%",
                    padding="1rem",
                    **CARD_STYLE,
                ),
            ),
            rx.fragment(
                rx.box(
                    rx.vstack(
                        rx.heading("Associação de Templates e Usuários", color="var(--text-primary)", size="5"),
                        rx.text(
                            "Esta aba é o cockpit de liberação. Aqui você escolhe uma conta já criada, aplica o template base, pode resetar senha se necessário e prepara o contexto para o canvas logo abaixo.",
                            color="var(--text-muted)",
                            font_size="0.88rem",
                        ),
                        rx.grid(
                            rx.box(
                                rx.vstack(
                                    rx.heading("Selecionar Usuário e Liberar Acesso Base", color="var(--text-primary)", size="4"),
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
                                        "Escolha primeiro a conta que recebera o acesso.",
                                    ),
                                    field_block(
                                        "Template base",
                                        rx.select(
                                            State.role_template_display_options,
                                            value=State.selected_role_template_option,
                                            on_change=State.set_perm_selected_role_template,
                                            bg="var(--input-bg)",
                                            color="var(--text-primary)",
                                            width="100%",
                                        ),
                                        "Aplique um baseline antes de abrir excecoes finas no canvas.",
                                    ),
                                    rx.hstack(
                                        rx.button(
                                            "Aplicar Template ao Usuário",
                                            on_click=State.apply_selected_role_template,
                                            class_name="primary-soft-action",
                                        ),
                                        rx.cond(
                                            State.can_reset_user_password,
                                            rx.button(
                                                "Resetar Senha",
                                                on_click=State.request_password_reset_confirmation(
                                                    State.selected_access_principal["email"]
                                                ),
                                                min_height="40px",
                                                padding="0 1rem",
                                                bg="rgba(239,68,68,0.2)",
                                                color="#fca5a5",
                                                border="1px solid rgba(239,68,68,0.4)",
                                                border_radius="12px",
                                                font_weight="500",
                                                box_shadow="none",
                                            ),
                                            rx.fragment(),
                                        ),
                                        spacing="2",
                                        width="100%",
                                    ),
                                    field_block(
                                        "Modulo para ajuste fino",
                        rx.select(
                            State.permission_module_options,
                            value=State.perm_selected_module,
                            on_change=State.set_perm_selected_module,
                            bg="var(--input-bg)",
                            color="var(--text-primary)",
                            width="100%",
                        ),
                        "Esse filtro afeta os Ajustes Finos de Permissão da seção 4, para facilitar a liberação por módulo.",
                    ),
                                    rx.text(
                                        "As permissoes se aplicam a contas ja criadas. O cadastro do usuario acontece na UI Usuarios; a liberacao fica centralizada aqui.",
                                        color="var(--text-muted)",
                                        font_size="0.82rem",
                                    ),
                                    rx.cond(
                                        State.last_reset_user_password != "",
                                        rx.box(
                                            rx.vstack(
                                                rx.text("Senha temporaria gerada", color="var(--text-primary)", font_weight="600"),
                                                rx.text(
                                                    State.last_reset_user_password,
                                                    color="#fde68a",
                                                    font_family="monospace",
                                                    font_size="1rem",
                                                ),
                                                rx.text(
                                                    "Compartilhe esta senha de forma segura. O usuario sera obrigado a trocá-la no proximo login.",
                                                    color="var(--text-muted)",
                                                    font_size="0.8rem",
                                                ),
                                                spacing="1",
                                                align="start",
                                                width="100%",
                                            ),
                                            width="100%",
                                            padding="0.9rem 1rem",
                                            bg="rgba(250,204,21,0.08)",
                                            border="1px solid rgba(250,204,21,0.2)",
                                            border_radius="14px",
                                        ),
                                        rx.fragment(),
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
                                    rx.heading("Resumo da Conta Selecionada", color="var(--text-primary)", size="4"),
                                    rx.text(
                                        "Leitura do perfil: Nome do papel - Contexto - Workspace tecnico. Ex.: SmartLab Admin - SmartLab - default.",
                                        color="var(--text-muted)",
                                        font_size="0.8rem",
                                    ),
                                    rx.text(State.selected_access_principal["name"], color="var(--text-primary)", font_weight="700"),
                                    rx.text(State.selected_access_principal["email"], color="var(--text-secondary)"),
                                    rx.hstack(
                                        rx.badge(State.selected_access_principal["role_label"], color_scheme="purple"),
                                        rx.badge(State.selected_access_principal["scope_label"], color_scheme="orange"),
                                        spacing="2",
                                    ),
                                    rx.hstack(
                                        rx.text("Workspace:", color="var(--text-muted)", font_size="0.84rem"),
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
                                    rx.vstack(
                                        rx.text("Responsabilidades vinculadas ao papel atual", color="var(--text-primary)", font_weight="600"),
                                        rx.cond(
                                            State.selected_access_responsibilities.length() > 0,
                                            rx.foreach(
                                                State.selected_access_responsibilities,
                                                lambda item: rx.badge(item, color_scheme="gray", width="fit-content", size="1"),
                                            ),
                                            rx.text(
                                                "Nenhuma responsabilidade registrada para o papel atual.",
                                                color="var(--text-muted)",
                                                font_size="0.8rem",
                                            ),
                                        ),
                                        spacing="2",
                                        align="start",
                                        width="100%",
                                    ),
                                    align="start",
                                    spacing="2",
                                    width="100%",
                                ),
                                padding="1rem",
                                **CARD_STYLE,
                            ),
                            rx.box(
                                rx.vstack(
                                    rx.heading("Template Base em Revisão", color="var(--text-primary)", size="4"),
                                    rx.text(
                                        "Depois de selecionar o usuario, revise aqui o baseline que sera aplicado antes das excecoes de acesso.",
                                        color="var(--text-muted)",
                                        font_size="0.82rem",
                                    ),
                                    rx.badge(State.selected_role_template_data["label"], color_scheme="purple"),
                                    rx.text(State.selected_role_template_data["description"], color="var(--text-secondary)"),
                                    rx.hstack(
                                        rx.text("Workspace:", color="var(--text-muted)", font_size="0.85rem"),
                                        rx.text(State.selected_role_template_data["workspace_label"], color="var(--text-muted)", font_size="0.85rem"),
                                        spacing="2",
                                    ),
                                    rx.hstack(
                                        rx.text("Contexto:", color="var(--text-muted)", font_size="0.85rem"),
                                        rx.text(State.selected_role_template_data["context_label"], color="var(--text-muted)", font_size="0.85rem"),
                                        spacing="2",
                                    ),
                                    rx.hstack(
                                        rx.text("Alcance:", color="var(--text-muted)", font_size="0.85rem"),
                                        rx.text(State.selected_role_template_data["reach_label"], color="var(--text-muted)", font_size="0.85rem"),
                                        spacing="2",
                                    ),
                                    rx.text(State.selected_role_template_data["governance"], color="var(--text-muted)", font_size="0.8rem"),
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
                            columns="3",
                            spacing="4",
                            width="100%",
                        ),
                        rx.box(
                            rx.text(
                                "Fluxo: 1. selecione o usuário, 2. revise o resumo da conta, 3. aplique o template base, 4. refine exceções nos Ajustes Finos de Permissão.",
                                color="var(--text-secondary)",
                                font_size="0.82rem",
                            ),
                            width="100%",
                            padding="0.85rem 1rem",
                            class_name="workspace-guide",
                        ),
                        width="100%",
                        spacing="4",
                        align="start",
                    ),
                    width="100%",
                    padding="1rem",
                    **CARD_STYLE,
                ),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.heading("Ajustes Finos de Permissão - Completa o Perfil do Usuário", color="var(--text-primary)", size="5"),
                    rx.spacer(),
                    rx.text(
                        "O perfil já pré-configura este quadro. Aqui você trabalha nas exceções individuais do usuário, que ficam registradas separadamente.",
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
        rx.box(
            rx.vstack(
                rx.heading("Exceções Individuais Registradas", color="var(--text-primary)", size="5"),
                rx.text(
                    "Revise aqui os ajustes individuais ativos do usuário. Ao remover uma exceção, o acesso volta a seguir o perfil base.",
                    color="var(--text-muted)",
                    font_size="0.88rem",
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
                                    rx.text("Nenhuma exceção individual registrada.", color="var(--text-muted)", font_size="0.86rem"),
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
                                                    "Voltar ao Perfil",
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
                            "Selecione um usuario para visualizar as exceções individuais registradas.",
                            color="var(--text-muted)",
                        ),
                        width="100%",
                        padding="1rem",
                        class_name="panel-card data-table-card permission-empty-state",
                        **CARD_STYLE,
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
        ),
        ),
        width="100%",
        spacing="4",
        on_mount=rx.call_script(f"{permission_dnd_script}\n{role_permission_dnd_script}"),
        on_unmount=rx.call_script("window.__smartlabPermissionDnd?.cleanup?.(); window.__smartlabRolePermissionDnd?.cleanup?.();"),
    )
