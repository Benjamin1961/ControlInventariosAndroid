"""
base.py — Clase base para todas las pantallas del sistema.
KivyMD 2.0: TopAppBar café oscuro, fondo blanco, MDButton con MDButtonText.
"""

from kivy.utils import get_color_from_hex
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.appbar import (
    MDTopAppBar, MDTopAppBarLeadingButtonContainer,
    MDTopAppBarTitle, MDActionTopAppBarButton,
)
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText
from kivymd.uix.dialog import (
    MDDialog, MDDialogHeadlineText, MDDialogSupportingText,
    MDDialogButtonContainer,
)
from kivymd.uix.button import MDButton, MDButtonText

# Colores corporativos (mismos que main.py)
_CAFE   = get_color_from_hex("#3E2723")
_BLANCO = [1, 1, 1, 1]
_FONDO  = [1, 1, 1, 1]          # #FFFFFF blanco puro


class PantallaBase(MDScreen):
    """
    Pantalla base con:
    - TopAppBar café oscuro, título centrado, ícono menú blanco
    - Fondo #FAFAFA
    - show_snack() y confirmar()
    """

    titulo_pantalla = "Pantalla"

    def __init__(self, nav_drawer_ref=None, screen_manager_ref=None, **kwargs):
        super().__init__(**kwargs)
        self._nav    = nav_drawer_ref
        self._sm     = screen_manager_ref
        self._dialog = None

        # Fondo blanco en toda la pantalla
        self.md_bg_color = _FONDO

        self.layout_raiz = MDBoxLayout(orientation="vertical")

        # ── TopAppBar ──────────────────────────────────────────────────────
        self.toolbar = MDTopAppBar(
            theme_bg_color="Custom",
            md_bg_color=_CAFE,
        )

        leading = MDTopAppBarLeadingButtonContainer()
        btn_menu = MDActionTopAppBarButton(
            icon="menu",
            theme_icon_color="Custom",
            icon_color=_BLANCO,
        )
        btn_menu.bind(on_release=lambda x: self._abrir_menu())
        leading.add_widget(btn_menu)

        self.toolbar.add_widget(leading)
        self.toolbar.add_widget(MDTopAppBarTitle(
            text=self.titulo_pantalla,
            halign="center",
            theme_text_color="Custom",
            text_color=_BLANCO,
        ))

        self.layout_raiz.add_widget(self.toolbar)
        self.add_widget(self.layout_raiz)

    # ── Menú ──────────────────────────────────────────────────────────────

    def _abrir_menu(self):
        if self._nav:
            self._nav.set_state("open")

    # ── Snackbar ──────────────────────────────────────────────────────────

    def show_snack(self, texto, duracion=3):
        MDSnackbar(
            MDSnackbarText(text=texto),
            y="24dp",
            pos_hint={"center_x": 0.5},
            size_hint_x=0.9,
            duration=duracion,
        ).open()

    # ── Diálogo de confirmación ───────────────────────────────────────────

    def confirmar(self, titulo, mensaje, callback_si):
        if self._dialog:
            self._dialog.dismiss()

        self._dialog = MDDialog(
            MDDialogHeadlineText(text=titulo),
            MDDialogSupportingText(text=mensaje),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="Cancelar"),
                    style="text",
                    on_release=lambda x: self._dialog.dismiss(),
                ),
                MDButton(
                    MDButtonText(text="Aceptar"),
                    style="text",
                    on_release=lambda x: self._on_confirmar(callback_si),
                ),
            ),
        )
        self._dialog.open()

    def _on_confirmar(self, callback):
        if self._dialog:
            self._dialog.dismiss()
        callback()
