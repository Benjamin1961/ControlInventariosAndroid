"""
main.py — Punto de entrada de la app de inventarios para panadería.
KivyMD 2.0 + SQLite. Diseño móvil con NavigationDrawer.
"""

from kivymd.app import MDApp
from kivymd.uix.navigationdrawer import (
    MDNavigationDrawer, MDNavigationDrawerMenu,
    MDNavigationDrawerItem, MDNavigationDrawerItemLeadingIcon,
    MDNavigationDrawerItemText, MDNavigationDrawerLabel,
    MDNavigationLayout,
)
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.appbar import (
    MDTopAppBar, MDTopAppBarLeadingButtonContainer,
    MDTopAppBarTitle, MDActionTopAppBarButton,
)
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivy.lang import Builder
from kivy.clock import Clock
from datetime import datetime

import database

# Colores corporativos
COLOR_CAFE   = "#3E2723"   # fondo barra superior
COLOR_DORADO = "#FFA000"   # acento
COLOR_BLANCO = [1, 1, 1, 1]
COLOR_FONDO  = [1, 1, 1, 1]            # #FFFFFF blanco puro

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
                    theme_bg_color: "Custom"
                    md_bg_color: app.COLOR_CAFE
                    MDTopAppBarLeadingButtonContainer:
                        MDActionTopAppBarButton:
                            icon: "menu"
                            theme_icon_color: "Custom"
                            icon_color: 1, 1, 1, 1
                            on_release: nav_drawer.set_state("open")
                    MDTopAppBarTitle:
                        text: "Panadería Inventarios"
                        halign: "center"
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1

                # ── Contenido dashboard ──────────────────────────────────────
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "24dp"
                    spacing: "20dp"
                    md_bg_color: 1, 1, 1, 1

                    MDLabel:
                        text: "Panadería"
                        halign: "center"
                        font_style: "Display"
                        role: "small"
                        theme_text_color: "Custom"
                        text_color: app.COLOR_CAFE
                        size_hint_y: None
                        height: "56dp"

                    MDLabel:
                        text: "Sistema de Control de Inventarios"
                        halign: "center"
                        font_style: "Title"
                        role: "medium"
                        theme_text_color: "Secondary"
                        size_hint_y: None
                        height: "36dp"

                    MDLabel:
                        id: lbl_fecha
                        text: ""
                        halign: "center"
                        font_style: "Body"
                        role: "large"
                        theme_text_color: "Secondary"
                        size_hint_y: None
                        height: "32dp"

                    Widget:
                        size_hint_y: 1

                    MDLabel:
                        text: "Usa el menú ☰ para navegar entre módulos"
                        halign: "center"
                        font_style: "Body"
                        role: "medium"
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
                on_release:
                    screen_manager.current = "dashboard"
                    nav_drawer.set_state("close")
                MDNavigationDrawerItemLeadingIcon:
                    icon: "view-dashboard"
                MDNavigationDrawerItemText:
                    text: "Panel Principal"

            MDNavigationDrawerItem:
                on_release:
                    screen_manager.current = "proveedores"
                    nav_drawer.set_state("close")
                MDNavigationDrawerItemLeadingIcon:
                    icon: "account-tie"
                MDNavigationDrawerItemText:
                    text: "Proveedores"

            MDNavigationDrawerItem:
                on_release:
                    screen_manager.current = "materias_primas"
                    nav_drawer.set_state("close")
                MDNavigationDrawerItemLeadingIcon:
                    icon: "package-variant"
                MDNavigationDrawerItemText:
                    text: "Materias Primas"

            MDNavigationDrawerItem:
                on_release:
                    screen_manager.current = "lotes"
                    nav_drawer.set_state("close")
                MDNavigationDrawerItemLeadingIcon:
                    icon: "layers"
                MDNavigationDrawerItemText:
                    text: "Lotes"

            MDNavigationDrawerItem:
                on_release:
                    screen_manager.current = "inventario"
                    nav_drawer.set_state("close")
                MDNavigationDrawerItemLeadingIcon:
                    icon: "warehouse"
                MDNavigationDrawerItemText:
                    text: "Inventario"

            MDNavigationDrawerItem:
                on_release:
                    screen_manager.current = "recetas"
                    nav_drawer.set_state("close")
                MDNavigationDrawerItemLeadingIcon:
                    icon: "book-open-variant"
                MDNavigationDrawerItemText:
                    text: "Recetas"

            MDNavigationDrawerItem:
                on_release:
                    screen_manager.current = "salidas"
                    nav_drawer.set_state("close")
                MDNavigationDrawerItemLeadingIcon:
                    icon: "tray-arrow-up"
                MDNavigationDrawerItemText:
                    text: "Salidas / Producción"

            MDNavigationDrawerItem:
                on_release:
                    screen_manager.current = "producto_terminado"
                    nav_drawer.set_state("close")
                MDNavigationDrawerItemLeadingIcon:
                    icon: "bread-slice"
                MDNavigationDrawerItemText:
                    text: "Producto Terminado"

            MDNavigationDrawerItem:
                on_release:
                    screen_manager.current = "reportes"
                    nav_drawer.set_state("close")
                MDNavigationDrawerItemLeadingIcon:
                    icon: "chart-bar"
                MDNavigationDrawerItemText:
                    text: "Reportes"
"""


# ─────────────────────────────────────────────────────────────────────────────
# Pantalla placeholder
# ─────────────────────────────────────────────────────────────────────────────

def _crear_pantalla_placeholder(nombre, titulo):
    from kivymd.uix.screen import MDScreen
    from kivymd.uix.label import MDLabel
    from kivymd.uix.appbar import (
        MDTopAppBar, MDTopAppBarLeadingButtonContainer,
        MDTopAppBarTitle, MDActionTopAppBarButton,
    )
    from kivy.utils import get_color_from_hex

    cafe = get_color_from_hex(COLOR_CAFE)

    class _Pantalla(MDScreen):
        def __init__(self, nav_drawer_ref=None, screen_manager_ref=None, **kwargs):
            super().__init__(name=nombre, **kwargs)
            self._nav = nav_drawer_ref
            self.md_bg_color = COLOR_FONDO

            layout = MDBoxLayout(orientation="vertical")

            bar = MDTopAppBar(
                theme_bg_color="Custom",
                md_bg_color=cafe,
            )
            leading = MDTopAppBarLeadingButtonContainer()
            btn_menu = MDActionTopAppBarButton(
                icon="menu",
                theme_icon_color="Custom",
                icon_color=COLOR_BLANCO,
            )
            btn_menu.bind(on_release=lambda x: self._nav and self._nav.set_state("open"))
            leading.add_widget(btn_menu)
            bar.add_widget(leading)
            bar.add_widget(MDTopAppBarTitle(
                text=titulo,
                halign="center",
                theme_text_color="Custom",
                text_color=COLOR_BLANCO,
            ))
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

    # Exponer constante de color al KV string
    COLOR_CAFE = COLOR_CAFE

    def build(self):
        # Tema Material 3 con color semilla café oscuro
        self.theme_cls.primary_palette = COLOR_CAFE
        self.theme_cls.theme_style = "Light"

        database.inicializar_db()

        root = Builder.load_string(KV)
        sm  = root.ids.screen_manager
        nav = root.ids.nav_drawer

        self._nav_drawer = nav
        self._registrar_pantallas(sm, nav)

        # Reloj para fecha/hora en el dashboard
        self._lbl_fecha = root.ids.lbl_fecha
        Clock.schedule_interval(self._actualizar_reloj, 1)
        self._actualizar_reloj(0)

        return root

    def on_start(self):
        # Garantizar que el drawer esté cerrado cuando la UI esté lista
        self._nav_drawer.set_state("close")

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
