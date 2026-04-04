"""
base.py — Clase base para todas las pantallas del sistema.
KivyMD 1.2.0: MDTopAppBar de kivymd.uix.toolbar, MDFlatButton, MDSnackbar simple.
"""

from kivy.utils import get_color_from_hex
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton

# Colores corporativos
_CAFE   = get_color_from_hex("#3E2723")
_BLANCO = [1, 1, 1, 1]
_FONDO  = [1, 1, 1, 1]


class PantallaBase(MDScreen):
    """
    Pantalla base con:
    - TopAppBar café oscuro con ícono menú
    - Fondo blanco
    - show_snack() y confirmar()
    """

    titulo_pantalla = "Pantalla"

    def __init__(self, nav_drawer_ref=None, screen_manager_ref=None, **kwargs):
        super().__init__(**kwargs)
        self._nav    = nav_drawer_ref
        self._sm     = screen_manager_ref
        self._dialog = None

        self.md_bg_color = _FONDO

        self.layout_raiz = MDBoxLayout(orientation="vertical")

        # ── TopAppBar ──────────────────────────────────────────────────────────
        self.toolbar = MDTopAppBar(
            title=self.titulo_pantalla,
            md_bg_color=_CAFE,
            specific_text_color=_BLANCO,
            elevation=4,
        )
        self.toolbar.left_action_items = [
            ["menu", lambda x: self._abrir_menu()]
        ]

        self.layout_raiz.add_widget(self.toolbar)
        self.add_widget(self.layout_raiz)

    # ── Menú ───────────────────────────────────────────────────────────────────

    def _abrir_menu(self):
        if self._nav:
            self._nav.set_state("open")

    # ── Snackbar ───────────────────────────────────────────────────────────────

    def show_snack(self, texto, duracion=3):
        try:
            MDSnackbar(text=texto, duration=duracion).open()
        except Exception:
            print(f"[Snack] {texto}")

    # ── Diálogo de confirmación ────────────────────────────────────────────────

    def confirmar(self, titulo, mensaje, callback_si):
        if self._dialog:
            self._dialog.dismiss()

        def _aceptar(x):
            if self._dialog:
                self._dialog.dismiss()
            callback_si()

        self._dialog = MDDialog(
            title=titulo,
            text=mensaje,
            buttons=[
                MDFlatButton(
                    text="Cancelar",
                    on_release=lambda x: self._dialog.dismiss(),
                ),
                MDFlatButton(
                    text="Aceptar",
                    theme_text_color="Custom",
                    text_color=_CAFE,
                    on_release=_aceptar,
                ),
            ],
        )
        self._dialog.open()
