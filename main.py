"""
main.py — Punto de entrada de la app de inventarios para panadería.
KivyMD 1.2.0 + SQLite. Diseño móvil con NavigationDrawer.
"""

from kivymd.app import MDApp
from kivymd.uix.navigationdrawer import (
    MDNavigationDrawer, MDNavigationDrawerMenu,
    MDNavigationDrawerItem, MDNavigationDrawerLabel,
    MDNavigationLayout,
)
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from datetime import datetime

import database

# Colores corporativos
COLOR_CAFE   = "#3E2723"   # fondo barra superior
COLOR_DORADO = "#FFA000"   # acento
COLOR_BLANCO = [1, 1, 1, 1]
COLOR_FONDO  = [1, 1, 1, 1]

# ─────────────────────────────────────────────────────────────────────────────
# KV Layout
# ─────────────────────────────────────────────────────────────────────────────

KV = """
MDNavigationLayout:

    MDScreenManager:
        id: screen_manager
        md_bg_color: 1, 1, 1, 1

        MDScreen:
            name: "dashboard"
            md_bg_color: 1, 1, 1, 1

            MDBoxLayout:
                orientation: "vertical"

                # ── Barra superior ──────────────────────────────────────────
                MDTopAppBar:
                    title: "Panadería Inventarios"
                    left_action_items: [["menu", lambda x: nav_drawer.set_state("open")]]
                    right_action_items: [["exit-to-app", lambda x: app.confirmar_salir()]]
                    md_bg_color: app.color_cafe
                    specific_text_color: 1, 1, 1, 1
                    elevation: 4

                # ── Contenido dashboard ──────────────────────────────────────
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "24dp"
                    spacing: "20dp"
                    md_bg_color: 1, 1, 1, 1

                    MDLabel:
                        text: "Panadería"
                        halign: "center"
                        font_style: "H4"
                        theme_text_color: "Custom"
                        text_color: app.color_cafe
                        size_hint_y: None
                        height: "56dp"

                    MDLabel:
                        text: "Sistema de Control de Inventarios"
                        halign: "center"
                        font_style: "H6"
                        theme_text_color: "Secondary"
                        size_hint_y: None
                        height: "36dp"

                    MDLabel:
                        id: lbl_fecha
                        text: ""
                        halign: "center"
                        font_style: "Body1"
                        theme_text_color: "Secondary"
                        size_hint_y: None
                        height: "32dp"

                    Widget:
                        size_hint_y: 1

                    MDLabel:
                        text: "Usa el menú ☰ para navegar entre módulos"
                        halign: "center"
                        font_style: "Body2"
                        theme_text_color: "Secondary"
                        size_hint_y: None
                        height: "32dp"

                    Widget:
                        size_hint_y: 0.5

    # ── Navigation Drawer — inicia CERRADO ───────────────────────────────────
    MDNavigationDrawer:
        id: nav_drawer
        state: "close"
        radius: 0, "16dp", "16dp", 0

        MDNavigationDrawerMenu:

            MDNavigationDrawerLabel:
                text: "MENÚ PRINCIPAL"

            MDNavigationDrawerItem:
                icon: "view-dashboard"
                text: "Panel Principal"
                on_release:
                    screen_manager.current = "dashboard"
                    nav_drawer.set_state("close")

            MDNavigationDrawerItem:
                icon: "account-tie"
                text: "Proveedores"
                on_release:
                    screen_manager.current = "proveedores"
                    nav_drawer.set_state("close")

            MDNavigationDrawerItem:
                icon: "package-variant"
                text: "Materias Primas"
                on_release:
                    screen_manager.current = "materias_primas"
                    nav_drawer.set_state("close")

            MDNavigationDrawerItem:
                icon: "layers"
                text: "Lotes"
                on_release:
                    screen_manager.current = "lotes"
                    nav_drawer.set_state("close")

            MDNavigationDrawerItem:
                icon: "warehouse"
                text: "Inventario"
                on_release:
                    screen_manager.current = "inventario"
                    nav_drawer.set_state("close")

            MDNavigationDrawerItem:
                icon: "book-open-variant"
                text: "Recetas"
                on_release:
                    screen_manager.current = "recetas"
                    nav_drawer.set_state("close")

            MDNavigationDrawerItem:
                icon: "tray-arrow-up"
                text: "Salidas / Producción"
                on_release:
                    screen_manager.current = "salidas"
                    nav_drawer.set_state("close")

            MDNavigationDrawerItem:
                icon: "bread-slice"
                text: "Producto Terminado"
                on_release:
                    screen_manager.current = "producto_terminado"
                    nav_drawer.set_state("close")

            MDNavigationDrawerItem:
                icon: "chart-bar"
                text: "Reportes"
                on_release:
                    screen_manager.current = "reportes"
                    nav_drawer.set_state("close")

            # ── Separador ────────────────────────────────────────────────────
            MDBoxLayout:
                size_hint_y: None
                height: "1dp"
                md_bg_color: 0.75, 0.75, 0.75, 1

            MDNavigationDrawerItem:
                icon: "exit-to-app"
                text: "Salir"
                theme_text_color: "Custom"
                text_color: 0.8, 0.1, 0.1, 1
                icon_color: 0.8, 0.1, 0.1, 1
                on_release:
                    nav_drawer.set_state("close")
                    app.confirmar_salir()
"""


# ─────────────────────────────────────────────────────────────────────────────
# Pantalla placeholder
# ─────────────────────────────────────────────────────────────────────────────

def _crear_pantalla_placeholder(nombre, titulo):
    from kivymd.uix.screen import MDScreen
    from kivymd.uix.label import MDLabel
    from kivymd.uix.toolbar import MDTopAppBar
    from kivy.utils import get_color_from_hex

    cafe = get_color_from_hex(COLOR_CAFE)

    class _Pantalla(MDScreen):
        def __init__(self, nav_drawer_ref=None, screen_manager_ref=None, **kwargs):
            super().__init__(name=nombre, **kwargs)
            self._nav = nav_drawer_ref
            self.md_bg_color = COLOR_FONDO

            layout = MDBoxLayout(orientation="vertical")

            bar = MDTopAppBar(
                title=titulo,
                md_bg_color=cafe,
                specific_text_color=COLOR_BLANCO,
                elevation=4,
            )
            bar.left_action_items = [
                ["menu", lambda x: self._nav and self._nav.set_state("open")]
            ]
            layout.add_widget(bar)

            layout.add_widget(MDLabel(
                text=f"Módulo: {titulo}\n(en desarrollo)",
                halign="center",
                valign="middle",
            ))
            self.add_widget(layout)

    return _Pantalla


# ─────────────────────────────────────────────────────────────────────────────
# Aplicación principal
# ─────────────────────────────────────────────────────────────────────────────

class PanaderiaApp(MDApp):

    # Exponer color café como lista RGBA para el KV string
    color_cafe = get_color_from_hex(COLOR_CAFE)

    def build(self):
        # Tema Material 2 con paleta café oscuro
        self.theme_cls.primary_palette = "Brown"
        self.theme_cls.theme_style = "Light"

        database.inicializar_db()

        root = Builder.load_string(KV)
        sm  = root.ids.screen_manager
        nav = root.ids.nav_drawer

        self._nav_drawer = nav
        self._exit_dialog = None
        self._registrar_pantallas(sm, nav)

        # Reloj para fecha/hora en el dashboard
        self._lbl_fecha = root.ids.lbl_fecha
        Clock.schedule_interval(self._actualizar_reloj, 1)
        self._actualizar_reloj(0)

        return root

    def on_start(self):
        # Garantizar que el drawer esté cerrado cuando la UI esté lista
        self._nav_drawer.set_state("close")

    # ── Salida limpia ──────────────────────────────────────────────────────────

    def confirmar_salir(self):
        if self._exit_dialog:
            self._exit_dialog.dismiss()

        def _salir(x):
            self._exit_dialog.dismiss()
            self.stop()
            Window.close()

        self._exit_dialog = MDDialog(
            title="Salir",
            text="¿Deseas cerrar la aplicación?",
            buttons=[
                MDFlatButton(
                    text="Cancelar",
                    on_release=lambda x: self._exit_dialog.dismiss(),
                ),
                MDFlatButton(
                    text="Salir",
                    theme_text_color="Custom",
                    text_color=get_color_from_hex(COLOR_CAFE),
                    on_release=_salir,
                ),
            ],
        )
        self._exit_dialog.open()

    def on_request_close(self, *args):
        self.confirmar_salir()
        return True  # impide el cierre inmediato hasta confirmar

    def _actualizar_reloj(self, dt):
        ahora = datetime.now()
        dias   = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
        meses  = ["enero","febrero","marzo","abril","mayo","junio",
                  "julio","agosto","septiembre","octubre","noviembre","diciembre"]
        dia_semana = dias[ahora.weekday()]
        self._lbl_fecha.text = (
            f"{dia_semana}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year}"
            f"  —  {ahora.strftime('%H:%M:%S')}"
        )

    def _registrar_pantallas(self, sm, nav):
        modulos = [
            ("proveedores",        "Proveedores"),
            ("materias_primas",    "Materias Primas"),
            ("lotes",              "Lotes"),
            ("inventario",         "Inventario"),
            ("recetas",            "Recetas"),
            ("salidas",            "Salidas / Producción"),
            ("producto_terminado", "Producto Terminado"),
            ("reportes",           "Reportes"),
        ]

        for nombre, titulo in modulos:
            try:
                modulo = __import__(f"modulos.{nombre}", fromlist=["Pantalla"])
                pantalla = modulo.Pantalla(
                    nav_drawer_ref=nav,
                    screen_manager_ref=sm,
                )
            except (ImportError, AttributeError):
                ClasePlaceholder = _crear_pantalla_placeholder(nombre, titulo)
                pantalla = ClasePlaceholder(
                    nav_drawer_ref=nav,
                    screen_manager_ref=sm,
                )
            sm.add_widget(pantalla)


if __name__ == "__main__":
    import traceback
    try:
        PanaderiaApp().run()
    except Exception as e:
        error_msg = f"ERROR CRÍTICO: {e}\n\n{traceback.format_exc()}"
        print(error_msg)
        try:
            from kivy.app import App
            from kivy.uix.scrollview import ScrollView
            from kivy.uix.label import Label

            class ErrorApp(App):
                def build(self):
                    sv = ScrollView()
                    lbl = Label(
                        text=error_msg,
                        size_hint_y=None,
                        text_size=(None, None),
                        halign="left",
                        valign="top",
                        font_size="12sp",
                        padding=(10, 10),
                    )
                    lbl.bind(texture_size=lbl.setter("size"))
                    sv.add_widget(lbl)
                    return sv

            ErrorApp().run()
        except Exception:
            pass
