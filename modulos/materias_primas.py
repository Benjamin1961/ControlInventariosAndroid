"""
modulos/materias_primas.py — Gestión completa de materias primas.

Mismo patrón que proveedores.py:
- Lista con avatar, búsqueda, botones editar/eliminar por fila
- Formulario MDDialog con campos de texto y dropdowns para
  Unidad de medida, Categoría y Proveedor principal
- CRUD completo sobre tabla 'materias_primas'
- Colores corporativos café #3E2723 / dorado #FFA000
"""

from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.core.window import Window

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.divider import MDDivider
from kivymd.uix.button import MDFabButton, MDButton, MDButtonText, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.textfield.textfield import MDTextFieldHintText, MDTextFieldHelperText
from kivymd.uix.dialog import (
    MDDialog, MDDialogHeadlineText,
    MDDialogButtonContainer, MDDialogContentContainer,
)
from kivymd.uix.menu import MDDropdownMenu

import database
from modulos.base import PantallaBase

# ─── Paleta ───────────────────────────────────────────────────────────────────
_CAFE   = get_color_from_hex("#3E2723")
_DORADO = get_color_from_hex("#FFA000")
_GRIS   = get_color_from_hex("#F5F5F5")
_BLANCO = [1, 1, 1, 1]
_ROJO   = get_color_from_hex("#B71C1C")
_BORDE  = get_color_from_hex("#BDBDBD")

# ─── Opciones fijas de dropdowns ─────────────────────────────────────────────
UNIDADES = ["kg", "g", "lb", "oz", "L", "ml", "unidad", "docena", "paquete"]
CATEGORIAS = [
    "Harinas", "Lácteos", "Huevos", "Azúcares",
    "Grasas", "Levaduras", "Frutas", "Esencias",
    "Empaques", "Otros",
]


# ─── Selector con dropdown ────────────────────────────────────────────────────

class _SelectorDropdown(MDBoxLayout):
    """
    Campo selector de apariencia outlined con etiqueta y flecha.
    Muestra un MDDropdownMenu al tocar.
    Uso:
        sel = _SelectorDropdown(hint="Unidad de medida *")
        sel.valor  → texto seleccionado (str)
    """

    def __init__(self, hint: str, opciones: list, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            height=dp(68),
            spacing=0,
            **kwargs,
        )
        self._hint    = hint
        self._opciones = opciones
        self._menu    = None
        self.valor    = ""          # valor seleccionado

        # ── Contenedor outlined ───────────────────────────────────────────
        self._caja = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(12), 0, dp(8), 0],
            spacing=dp(4),
            md_bg_color=_BLANCO,
            line_color=_BORDE,
        )
        self._caja.radius = [dp(4)]

        # Texto del selector (hint o valor elegido)
        self._lbl = MDLabel(
            text=hint,
            theme_text_color="Secondary",
            size_hint_x=1,
            valign="middle",
            shorten=True,
            shorten_from="right",
        )
        self._icono = MDIcon(
            icon="chevron-down",
            theme_text_color="Secondary",
            size_hint=(None, None),
            size=(dp(24), dp(24)),
        )
        self._caja.add_widget(self._lbl)
        self._caja.add_widget(self._icono)
        self.add_widget(self._caja)

        # Toque sobre la caja abre el menú
        self._caja.bind(on_touch_down=self._on_touch)

    def _on_touch(self, widget, touch):
        if widget.collide_point(*touch.pos):
            self._abrir_menu()
            return True

    def _abrir_menu(self):
        items = [
            {
                "text": op,
                "on_release": (lambda v: lambda: self._seleccionar(v))(op),
            }
            for op in self._opciones
        ]
        self._menu = MDDropdownMenu(
            caller=self._caja,
            items=items,
            width=dp(220),
        )
        self._menu.open()

    def _seleccionar(self, valor: str):
        self.valor = valor
        self._lbl.text = valor
        self._lbl.theme_text_color = "Primary"
        if self._menu:
            self._menu.dismiss()

    def set_valor(self, valor: str):
        """Pone un valor inicial (al editar un registro existente)."""
        if valor:
            self._seleccionar(valor)


# ─── Fila de la lista ─────────────────────────────────────────────────────────

class _FilaMateria(MDBoxLayout):
    """
    Fila compacta:
      [avatar] [nombre / categoría · unidad · mínimo] [✏] [🗑]
    """

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

        # Avatar
        avatar = MDBoxLayout(
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            md_bg_color=_CAFE,
        )
        avatar.radius = [dp(20)]
        avatar.add_widget(MDLabel(
            text=nombre[0].upper() if nombre else "?",
            halign="center",
            valign="middle",
            theme_text_color="Custom",
            text_color=_BLANCO,
            bold=True,
        ))

        # Textos
        textos = MDBoxLayout(
            orientation="vertical",
            size_hint_x=1,
            padding=[dp(8), dp(4), 0, dp(4)],
        )
        textos.add_widget(MDLabel(
            text=nombre,
            font_style="Body",
            role="large",
            bold=True,
            size_hint_y=None,
            height=dp(24),
            shorten=True,
            shorten_from="right",
        ))
        textos.add_widget(MDLabel(
            text=f"{cat}  ·  {unidad}",
            font_style="Body",
            role="small",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(20),
            shorten=True,
            shorten_from="right",
        ))
        # Semáforo de stock
        if stock <= 0:
            stock_txt  = f"Stock: {stock:.2f} {unidad}  🔴 SIN STOCK"
        elif stock < min_stk:
            stock_txt  = f"Stock: {stock:.2f}  ⚠ < mínimo ({min_stk:.2f})"
        else:
            stock_txt  = f"Stock: {stock:.2f} {unidad}  ·  Mín: {min_stk:.2f}"

        textos.add_widget(MDLabel(
            text=stock_txt,
            font_style="Body",
            role="small",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(18),
            shorten=True,
            shorten_from="right",
        ))

        # Botones
        btn_ed = MDIconButton(
            icon="pencil-outline",
            style="standard",
            theme_icon_color="Custom",
            icon_color=_CAFE,
        )
        btn_ed.bind(on_release=lambda x, i=_id: on_editar(i))

        btn_del = MDIconButton(
            icon="delete-outline",
            style="standard",
            theme_icon_color="Custom",
            icon_color=_ROJO,
        )
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

    # ── UI base ───────────────────────────────────────────────────────────────

    def _construir_ui(self):
        # Barra de búsqueda
        barra = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(64),
            padding=[dp(12), dp(8)],
            md_bg_color=_BLANCO,
        )
        self._tf_buscar = MDTextField(mode="outlined", size_hint_x=1)
        self._tf_buscar.add_widget(MDTextFieldHintText(text="Buscar por nombre…"))
        self._tf_buscar.bind(text=lambda inst, val: self._filtrar(val))
        barra.add_widget(self._tf_buscar)
        self.layout_raiz.add_widget(barra)
        self.layout_raiz.add_widget(MDDivider())

        # Lista
        self._contenedor = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            md_bg_color=_BLANCO,
            padding=[0, dp(8), 0, 0],
        )
        scroll = MDScrollView(do_scroll_x=False)
        scroll.add_widget(self._contenedor)
        self.layout_raiz.add_widget(scroll)

        # FAB
        self._fab = MDFabButton(
            icon="plus",
            style="standard",
            theme_bg_color="Custom",
            md_bg_color=_CAFE,
            pos_hint={"right": 0.97, "y": 0.03},
        )
        self._fab.bind(on_release=lambda x: self._abrir_form())
        self.add_widget(self._fab)
        Clock.schedule_once(self._color_fab, 0)

    def _color_fab(self, dt):
        self._fab.theme_icon_color = "Custom"
        self._fab.icon_color = _DORADO

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def on_pre_enter(self, *args):
        self._tf_buscar.text = ""
        self._cargar_datos()

    # ── Datos ─────────────────────────────────────────────────────────────────

    def _cargar_datos(self):
        conn = database.get_connection()
        rows = conn.execute("""
            SELECT  mp.id, mp.nombre, mp.descripcion, mp.unidad_medida,
                    mp.stock_minimo, mp.categoria, mp.proveedor_id,
                    COALESCE(SUM(l.cantidad_actual), 0) AS stock_actual
            FROM    materias_primas mp
            LEFT JOIN lotes l
                   ON l.materia_prima_id = mp.id AND l.activo = 1
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
                orientation="vertical",
                size_hint_y=None,
                height=dp(220),
                padding=[dp(16), dp(32)],
                spacing=dp(12),
            )
            vacio.add_widget(MDIcon(
                icon="package-variant-closed-remove",
                halign="center",
                font_size="48sp",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(56),
            ))
            vacio.add_widget(MDLabel(
                text="No hay materias primas registradas",
                halign="center",
                font_style="Title",
                role="medium",
                theme_text_color="Secondary",
            ))
            vacio.add_widget(MDLabel(
                text='Toca el botón "+" para agregar la primera',
                halign="center",
                font_style="Body",
                role="medium",
                theme_text_color="Secondary",
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

    # ── Formulario ────────────────────────────────────────────────────────────

    def _campo_texto(self, hint: str, texto: str = "",
                     teclado: str = "normal", error_msg: str = "") -> MDTextField:
        tf = MDTextField(
            text=texto,
            mode="outlined",
            size_hint_y=None,
            height=dp(68),
        )
        tf.add_widget(MDTextFieldHintText(text=hint))
        if error_msg:
            tf.add_widget(MDTextFieldHelperText(text=error_msg, mode="on_error"))
        if teclado != "normal":
            tf.input_type = teclado
        return tf

    def _abrir_form(self, id_mp=None):
        self._id_editando = id_mp
        datos = {}
        if id_mp:
            conn = database.get_connection()
            row = conn.execute(
                "SELECT * FROM materias_primas WHERE id=?", (id_mp,)
            ).fetchone()
            conn.close()
            datos = dict(row) if row else {}

        # ── Campos de texto ───────────────────────────────────────────────
        self._tf_nombre = self._campo_texto(
            "Nombre *",
            datos.get("nombre", ""),
            error_msg="El nombre es obligatorio",
        )
        self._tf_desc = self._campo_texto(
            "Descripción",
            datos.get("descripcion", "") or "",
        )
        self._tf_stock_min = self._campo_texto(
            "Stock mínimo",
            str(datos.get("stock_minimo", 0) or 0),
            teclado="number",
            error_msg="Ingresa un número válido",
        )

        # ── Dropdowns ─────────────────────────────────────────────────────
        self._sel_unidad = _SelectorDropdown(
            hint="Unidad de medida *",
            opciones=UNIDADES,
        )
        self._sel_unidad.set_valor(datos.get("unidad_medida", ""))

        self._sel_categoria = _SelectorDropdown(
            hint="Categoría",
            opciones=CATEGORIAS,
        )
        self._sel_categoria.set_valor(datos.get("categoria", "") or "")

        # Dropdown de proveedores (cargado desde BD)
        provs = self._cargar_proveedores()
        self._prov_map = {p["nombre"]: p["id"] for p in provs}  # nombre → id
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

        # ── Contenedor del formulario ──────────────────────────────────────
        inner = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[dp(4), dp(8), dp(4), dp(8)],
            adaptive_height=True,
        )
        for w in [
            self._tf_nombre,
            self._tf_desc,
            self._sel_unidad,
            self._tf_stock_min,
            self._sel_categoria,
            self._sel_proveedor,
        ]:
            inner.add_widget(w)

        scroll_form = MDScrollView(
            size_hint_y=None,
            height=Window.height * 0.55,
            do_scroll_x=False,
        )
        scroll_form.add_widget(inner)

        # ── Botones del diálogo ────────────────────────────────────────────
        btns = MDDialogButtonContainer(spacing=dp(4))

        if id_mp:
            btn_del = MDButton(
                MDButtonText(text="Eliminar", theme_text_color="Custom", text_color=_ROJO),
                style="text",
            )
            btn_del.bind(on_release=lambda x: self._desde_form_eliminar(id_mp))
            btns.add_widget(btn_del)

        btns.add_widget(Widget())

        btn_cancel = MDButton(MDButtonText(text="Cancelar"), style="text")
        btn_cancel.bind(on_release=lambda x: self._dialog_form.dismiss())

        btn_save = MDButton(
            MDButtonText(text="Guardar", theme_text_color="Custom", text_color=_CAFE),
            style="text",
        )
        btn_save.bind(on_release=lambda x: self._guardar())

        btns.add_widget(btn_cancel)
        btns.add_widget(btn_save)

        titulo = "Editar materia prima" if id_mp else "Nueva materia prima"
        self._dialog_form = MDDialog(
            MDDialogHeadlineText(text=titulo),
            MDDialogContentContainer(scroll_form),
            btns,
        )
        self._dialog_form.open()

    def _cargar_proveedores(self) -> list:
        conn = database.get_connection()
        rows = conn.execute(
            "SELECT id, nombre FROM proveedores WHERE activo=1 ORDER BY nombre"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _guardar(self):
        nombre = self._tf_nombre.text.strip()
        unidad = self._sel_unidad.valor.strip()

        # Validaciones
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

        # Resolver proveedor_id desde el nombre seleccionado
        nombre_prov = self._sel_proveedor.valor
        if nombre_prov and nombre_prov != "— Ninguno —":
            proveedor_id = self._prov_map.get(nombre_prov)
        else:
            proveedor_id = None

        desc = self._tf_desc.text.strip() or None

        conn = database.get_connection()
        try:
            if self._id_editando:
                conn.execute("""
                    UPDATE materias_primas
                       SET nombre=?, descripcion=?, unidad_medida=?,
                           stock_minimo=?, categoria=?, proveedor_id=?
                     WHERE id=?
                """, (nombre, desc, unidad, stock_min,
                      categoria, proveedor_id, self._id_editando))
                msg = "✓ Materia prima actualizada"
            else:
                conn.execute("""
                    INSERT INTO materias_primas
                        (nombre, descripcion, unidad_medida,
                         stock_minimo, categoria, proveedor_id, fecha_registro)
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

    # ── Eliminar ──────────────────────────────────────────────────────────────

    def _desde_form_eliminar(self, id_mp):
        self._dialog_form.dismiss()
        self._pedir_confirmar_eliminar(id_mp)

    def _pedir_confirmar_eliminar(self, id_mp):
        conn = database.get_connection()
        row = conn.execute(
            "SELECT nombre FROM materias_primas WHERE id=?", (id_mp,)
        ).fetchone()
        conn.close()
        nombre = row["nombre"] if row else "esta materia prima"

        self.confirmar(
            "Eliminar materia prima",
            f'¿Está seguro que desea eliminar "{nombre}"?\n\n'
            f"No se eliminará el historial de lotes existentes.",
            lambda: self._confirmar_eliminar(id_mp),
        )

    def _confirmar_eliminar(self, id_mp):
        conn = database.get_connection()
        conn.execute("UPDATE materias_primas SET activo=0 WHERE id=?", (id_mp,))
        conn.commit()
        conn.close()
        self.show_snack("Materia prima eliminada")
        self._cargar_datos()
