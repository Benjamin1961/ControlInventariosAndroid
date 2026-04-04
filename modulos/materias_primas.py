"""
modulos/materias_primas.py — Gestión completa de materias primas.
KivyMD 1.2.0 compatible.
"""

from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.core.window import Window

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFloatingActionButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu

import database
from modulos.base import PantallaBase, MDDivider

# ─── Paleta ───────────────────────────────────────────────────────────────────
_CAFE   = get_color_from_hex("#3E2723")
_DORADO = get_color_from_hex("#FFA000")
_GRIS   = get_color_from_hex("#F5F5F5")
_BLANCO = [1, 1, 1, 1]
_ROJO   = get_color_from_hex("#B71C1C")

# ─── Opciones fijas de dropdowns ─────────────────────────────────────────────
UNIDADES = ["kg", "g", "lb", "oz", "L", "ml", "unidad", "docena", "paquete"]
CATEGORIAS = [
    "Harinas", "Lácteos", "Huevos", "Azúcares",
    "Grasas", "Levaduras", "Frutas", "Esencias",
    "Empaques", "Otros",
]


# ─── Selector con dropdown ────────────────────────────────────────────────────

class _SelectorDropdown(MDBoxLayout):
    """Campo selector que muestra un MDDropdownMenu al tocar."""

    def __init__(self, hint: str, opciones: list, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            height=dp(56),
            **kwargs,
        )
        self._hint    = hint
        self._opciones = opciones
        self._menu    = None
        self.valor    = ""

        self._caja = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(12), 0, dp(8), 0],
            spacing=dp(4),
            md_bg_color=_GRIS,
        )
        self._caja.radius = [dp(4)]

        self._lbl = MDLabel(
            text=hint,
            theme_text_color="Secondary",
            size_hint_x=1,
            valign="middle",
        )
        self._caja.add_widget(self._lbl)
        self.add_widget(self._caja)
        self._caja.bind(on_touch_down=self._on_touch)

    def _on_touch(self, widget, touch):
        if widget.collide_point(*touch.pos):
            self._abrir_menu()
            return True

    def _abrir_menu(self):
        items = [
            {
                "viewclass": "OneLineListItem",
                "text": op,
                "on_release": (lambda v: lambda: self._seleccionar(v))(op),
            }
            for op in self._opciones
        ]
        self._menu = MDDropdownMenu(
            caller=self._caja,
            items=items,
            width_mult=4,
        )
        self._menu.open()

    def _seleccionar(self, valor: str):
        self.valor = valor
        self._lbl.text = valor
        self._lbl.theme_text_color = "Primary"
        if self._menu:
            self._menu.dismiss()

    def set_valor(self, valor: str):
        if valor:
            self._seleccionar(valor)


# ─── Fila de la lista ─────────────────────────────────────────────────────────

class _FilaMateria(MDBoxLayout):
    def __init__(self, row_data: dict, on_editar, on_eliminar, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(72),
            padding=[dp(8), dp(4), dp(4), dp(4)],
            spacing=dp(4),
            **kwargs,
        )

        nombre   = row_data["nombre"]
        unidad   = row_data["unidad_medida"] or "—"
        cat      = row_data["categoria"]     or "Sin categoría"
        min_stk  = row_data["stock_minimo"]  or 0
        stock    = row_data.get("stock_actual", 0) or 0
        _id      = row_data["id"]

        avatar = MDBoxLayout(size_hint=(None, None), size=(dp(40), dp(40)), md_bg_color=_CAFE)
        avatar.radius = [dp(20)]
        avatar.add_widget(MDLabel(
            text=nombre[0].upper() if nombre else "?",
            halign="center", valign="middle",
            theme_text_color="Custom", text_color=_BLANCO, bold=True,
        ))

        textos = MDBoxLayout(orientation="vertical", size_hint_x=1, padding=[dp(8), dp(4), 0, dp(4)])
        textos.add_widget(MDLabel(
            text=nombre, font_style="Body1", bold=True,
            size_hint_y=None, height=dp(24),
            shorten=True, shorten_from="right",
        ))
        textos.add_widget(MDLabel(
            text=f"{cat}  ·  {unidad}",
            font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(20),
            shorten=True, shorten_from="right",
        ))

        if stock <= 0:
            stock_txt = f"Stock: {stock:.2f} {unidad}  🔴 SIN STOCK"
        elif stock < min_stk:
            stock_txt = f"Stock: {stock:.2f}  ⚠ < mínimo ({min_stk:.2f})"
        else:
            stock_txt = f"Stock: {stock:.2f} {unidad}  ·  Mín: {min_stk:.2f}"

        textos.add_widget(MDLabel(
            text=stock_txt, font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(18),
            shorten=True, shorten_from="right",
        ))

        btn_ed = MDIconButton(icon="pencil-outline", theme_icon_color="Custom", icon_color=_CAFE)
        btn_ed.bind(on_release=lambda x, i=_id: on_editar(i))

        btn_del = MDIconButton(icon="delete-outline", theme_icon_color="Custom", icon_color=_ROJO)
        btn_del.bind(on_release=lambda x, i=_id: on_eliminar(i))

        self.add_widget(avatar)
        self.add_widget(textos)
        self.add_widget(btn_ed)
        self.add_widget(btn_del)


# ─── Pantalla principal ───────────────────────────────────────────────────────

class Pantalla(PantallaBase):
    name            = "materias_primas"
    titulo_pantalla = "Materias Primas"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._id_editando = None
        self._dialog_form = None
        self._todos       = []
        self._construir_ui()

    def _construir_ui(self):
        barra = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(64),
            padding=[dp(12), dp(8)], md_bg_color=_BLANCO,
        )
        self._tf_buscar = MDTextField(
            hint_text="Buscar por nombre…",
            mode="rectangle", size_hint_x=1,
        )
        self._tf_buscar.bind(text=lambda inst, val: self._filtrar(val))
        barra.add_widget(self._tf_buscar)
        self.layout_raiz.add_widget(barra)
        self.layout_raiz.add_widget(MDDivider())

        self._contenedor = MDBoxLayout(
            orientation="vertical", adaptive_height=True,
            md_bg_color=_BLANCO, padding=[0, dp(8), 0, 0],
        )
        scroll = MDScrollView(do_scroll_x=False)
        scroll.add_widget(self._contenedor)
        self.layout_raiz.add_widget(scroll)

        self._fab = MDFloatingActionButton(
            icon="plus", md_bg_color=_CAFE,
            pos_hint={"right": 0.97, "y": 0.03},
        )
        self._fab.bind(on_release=lambda x: self._abrir_form())
        self.add_widget(self._fab)
        Clock.schedule_once(self._color_fab, 0)

    def _color_fab(self, dt):
        self._fab.theme_icon_color = "Custom"
        self._fab.icon_color = _DORADO

    def on_pre_enter(self, *args):
        self._tf_buscar.text = ""
        self._cargar_datos()

    def _cargar_datos(self):
        conn = database.get_connection()
        rows = conn.execute("""
            SELECT  mp.id, mp.nombre, mp.descripcion, mp.unidad_medida,
                    mp.stock_minimo, mp.categoria, mp.proveedor_id,
                    COALESCE(SUM(l.cantidad_actual), 0) AS stock_actual
            FROM    materias_primas mp
            LEFT JOIN lotes l ON l.materia_prima_id = mp.id AND l.activo = 1
            WHERE   mp.activo = 1
            GROUP   BY mp.id
            ORDER   BY mp.nombre COLLATE NOCASE
        """).fetchall()
        conn.close()
        self._todos = [dict(r) for r in rows]
        self._renderizar(self._todos)

    def _filtrar(self, texto):
        t = texto.strip().lower()
        if not t:
            self._renderizar(self._todos)
            return
        self._renderizar([r for r in self._todos if t in r["nombre"].lower()])

    def _renderizar(self, rows):
        self._contenedor.clear_widgets()
        if not rows:
            vacio = MDBoxLayout(
                orientation="vertical", size_hint_y=None, height=dp(200),
                padding=[dp(16), dp(32)], spacing=dp(12),
            )
            vacio.add_widget(MDLabel(
                text="No hay materias primas registradas",
                halign="center", font_style="H6", theme_text_color="Secondary",
                size_hint_y=None, height=dp(40),
            ))
            vacio.add_widget(MDLabel(
                text='Toca el botón "+" para agregar la primera',
                halign="center", font_style="Body2", theme_text_color="Secondary",
                size_hint_y=None, height=dp(30),
            ))
            self._contenedor.add_widget(vacio)
            return

        for i, row in enumerate(rows):
            fila = _FilaMateria(
                row_data=row,
                on_editar=self._abrir_form,
                on_eliminar=self._pedir_confirmar_eliminar,
            )
            if i % 2 == 1:
                fila.md_bg_color = _GRIS
            self._contenedor.add_widget(fila)
            self._contenedor.add_widget(MDDivider())

    def _campo_texto(self, hint: str, texto: str = "",
                     teclado: str = "normal", error_msg: str = "") -> MDTextField:
        tf = MDTextField(
            text=texto,
            hint_text=hint,
            helper_text=error_msg,
            helper_text_mode="on_error" if error_msg else "none",
            mode="rectangle",
            size_hint_y=None,
            height=dp(68),
        )
        if teclado != "normal":
            tf.input_type = teclado
        return tf

    def _abrir_form(self, id_mp=None):
        self._id_editando = id_mp
        datos = {}
        if id_mp:
            conn = database.get_connection()
            row = conn.execute("SELECT * FROM materias_primas WHERE id=?", (id_mp,)).fetchone()
            conn.close()
            datos = dict(row) if row else {}

        self._tf_nombre = self._campo_texto(
            "Nombre *", datos.get("nombre", ""), error_msg="El nombre es obligatorio"
        )
        self._tf_desc = self._campo_texto("Descripción", datos.get("descripcion", "") or "")
        self._tf_stock_min = self._campo_texto(
            "Stock mínimo",
            str(datos.get("stock_minimo", 0) or 0),
            teclado="number", error_msg="Ingresa un número válido",
        )

        self._sel_unidad = _SelectorDropdown(hint="Unidad de medida *", opciones=UNIDADES)
        self._sel_unidad.set_valor(datos.get("unidad_medida", ""))

        self._sel_categoria = _SelectorDropdown(hint="Categoría", opciones=CATEGORIAS)
        self._sel_categoria.set_valor(datos.get("categoria", "") or "")

        provs = self._cargar_proveedores()
        self._prov_map = {p["nombre"]: p["id"] for p in provs}
        nombre_prov = ""
        if datos.get("proveedor_id"):
            prov_row = next((p for p in provs if p["id"] == datos["proveedor_id"]), None)
            if prov_row:
                nombre_prov = prov_row["nombre"]
        self._sel_proveedor = _SelectorDropdown(
            hint="Proveedor principal (opcional)",
            opciones=["— Ninguno —"] + [p["nombre"] for p in provs],
        )
        self._sel_proveedor.set_valor(nombre_prov)

        inner = MDBoxLayout(
            orientation="vertical", spacing=dp(12),
            padding=[dp(4), dp(8), dp(4), dp(8)], adaptive_height=True,
        )
        for w in [self._tf_nombre, self._tf_desc, self._sel_unidad,
                  self._tf_stock_min, self._sel_categoria, self._sel_proveedor]:
            inner.add_widget(w)

        scroll_form = MDScrollView(size_hint_y=None, height=Window.height * 0.55, do_scroll_x=False)
        scroll_form.add_widget(inner)

        buttons = []
        if id_mp:
            buttons.append(MDFlatButton(
                text="Eliminar", theme_text_color="Custom", text_color=_ROJO,
                on_release=lambda x: self._desde_form_eliminar(id_mp),
            ))
        buttons.append(MDFlatButton(text="Cancelar", on_release=lambda x: self._dialog_form.dismiss()))
        buttons.append(MDFlatButton(
            text="Guardar", theme_text_color="Custom", text_color=_CAFE,
            on_release=lambda x: self._guardar(),
        ))

        titulo = "Editar materia prima" if id_mp else "Nueva materia prima"
        self._dialog_form = MDDialog(title=titulo, type="custom", content_cls=scroll_form, buttons=buttons)
        self._dialog_form.open()

    def _cargar_proveedores(self) -> list:
        conn = database.get_connection()
        rows = conn.execute("SELECT id, nombre FROM proveedores WHERE activo=1 ORDER BY nombre").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _guardar(self):
        nombre = self._tf_nombre.text.strip()
        unidad = self._sel_unidad.valor.strip()

        if not nombre:
            self._tf_nombre.error = True
            self.show_snack("El nombre es obligatorio")
            return
        self._tf_nombre.error = False

        if not unidad:
            self.show_snack("Selecciona la unidad de medida")
            return

        try:
            stock_min = float(self._tf_stock_min.text.strip() or 0)
            self._tf_stock_min.error = False
        except ValueError:
            self._tf_stock_min.error = True
            self.show_snack("El stock mínimo debe ser un número")
            return

        categoria = self._sel_categoria.valor or None
        nombre_prov = self._sel_proveedor.valor
        proveedor_id = self._prov_map.get(nombre_prov) if nombre_prov and nombre_prov != "— Ninguno —" else None
        desc = self._tf_desc.text.strip() or None

        conn = database.get_connection()
        try:
            if self._id_editando:
                conn.execute("""
                    UPDATE materias_primas
                       SET nombre=?, descripcion=?, unidad_medida=?,
                           stock_minimo=?, categoria=?, proveedor_id=?
                     WHERE id=?
                """, (nombre, desc, unidad, stock_min, categoria, proveedor_id, self._id_editando))
                msg = "✓ Materia prima actualizada"
            else:
                conn.execute("""
                    INSERT INTO materias_primas
                        (nombre, descripcion, unidad_medida, stock_minimo, categoria, proveedor_id, fecha_registro)
                    VALUES (?, ?, ?, ?, ?, ?, date('now'))
                """, (nombre, desc, unidad, stock_min, categoria, proveedor_id))
                msg = "✓ Materia prima registrada"
            conn.commit()
        except Exception as e:
            self.show_snack(f"Error al guardar: {e}")
            return
        finally:
            conn.close()

        self._dialog_form.dismiss()
        self.show_snack(msg)
        self._cargar_datos()

    def _desde_form_eliminar(self, id_mp):
        self._dialog_form.dismiss()
        self._pedir_confirmar_eliminar(id_mp)

    def _pedir_confirmar_eliminar(self, id_mp):
        conn = database.get_connection()
        row = conn.execute("SELECT nombre FROM materias_primas WHERE id=?", (id_mp,)).fetchone()
        conn.close()
        nombre = row["nombre"] if row else "esta materia prima"
        self.confirmar(
            "Eliminar materia prima",
            f'¿Está seguro que desea eliminar "{nombre}"?\n\nNo se eliminará el historial de lotes.',
            lambda: self._confirmar_eliminar(id_mp),
        )

    def _confirmar_eliminar(self, id_mp):
        conn = database.get_connection()
        conn.execute("UPDATE materias_primas SET activo=0 WHERE id=?", (id_mp,))
        conn.commit()
        conn.close()
        self.show_snack("Materia prima eliminada")
        self._cargar_datos()
