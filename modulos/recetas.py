"""
modulos/recetas.py — Gestión completa de recetas e ingredientes.

Mismo patrón que materias_primas.py:
- Lista scrolleable con búsqueda, botones editar/eliminar por fila
- Formulario MDDialog con ingredientes dinámicos y cálculo de costo automático
- Mini-dialog con dropdown de materia prima para agregar ingredientes
- CRUD completo sobre tablas 'recetas' y 'receta_ingredientes'
- Colores corporativos café #3E2723 / dorado #FFA000
"""

from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.uix.widget import Widget

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


# ─── Selector con dropdown ────────────────────────────────────────────────────

class _SelectorDropdown(MDBoxLayout):
    """
    Campo selector de apariencia outlined con etiqueta y flecha.
    Muestra un MDDropdownMenu al tocar.
    Uso:
        sel = _SelectorDropdown(hint="Materia prima", opciones=[...])
        sel.valor  → texto seleccionado (str)
    """

    def __init__(self, hint: str, opciones: list, on_seleccion=None, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            height=dp(68),
            spacing=0,
            **kwargs,
        )
        self._hint       = hint
        self._opciones   = opciones
        self._menu       = None
        self.valor       = ""
        self._callback   = on_seleccion  # llamado con el valor al seleccionar

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
            width=dp(260),
        )
        self._menu.open()

    def _seleccionar(self, valor: str):
        self.valor = valor
        self._lbl.text = valor
        self._lbl.theme_text_color = "Primary"
        if self._menu:
            self._menu.dismiss()
        if self._callback:
            self._callback(valor)

    def set_valor(self, valor: str):
        """Pone un valor inicial (al editar un registro existente)."""
        if valor:
            self._seleccionar(valor)


# ─── Fila de receta en la lista ───────────────────────────────────────────────

class _FilaReceta(MDBoxLayout):
    """
    Fila compacta:
      [avatar] [nombre / ingredientes · porciones / costo] [✏] [🗑]
    """

    def __init__(self, row_data: dict, on_editar, on_eliminar, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(80),
            padding=[dp(8), dp(4), dp(4), dp(4)],
            spacing=dp(4),
            **kwargs,
        )

        nombre    = row_data["nombre"]
        num_ings  = row_data.get("num_ingredientes", 0) or 0
        porciones = row_data.get("porciones") or 1
        costo     = row_data.get("costo_total") or 0.0
        _id       = row_data["id"]

        # Avatar
        avatar = MDBoxLayout(
            size_hint=(None, None),
            size=(dp(44), dp(44)),
            md_bg_color=_CAFE,
        )
        avatar.radius = [dp(22)]
        avatar.add_widget(MDIcon(
            icon="chef-hat",
            halign="center",
            valign="middle",
            theme_icon_color="Custom",
            icon_color=_BLANCO,
            font_size="22sp",
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
            height=dp(26),
            shorten=True,
            shorten_from="right",
        ))

        cant_s = "ingrediente" if num_ings == 1 else "ingredientes"
        porc_s = f"{porciones:.0f}" if porciones == int(porciones) else f"{porciones:.1f}"
        textos.add_widget(MDLabel(
            text=f"{num_ings} {cant_s}  ·  {porc_s} porción(es)",
            font_style="Body",
            role="small",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(20),
        ))
        textos.add_widget(MDLabel(
            text=f"Costo estimado: ₡{costo:,.2f}",
            font_style="Body",
            role="small",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(18),
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
    name            = "recetas"
    titulo_pantalla = "Recetas"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._id_editando       = None
        self._dialog_form       = None
        self._dialog_ing        = None
        self._ingredientes_temp = []
        self._todos             = []
        self._mp_list           = []   # materias primas cargadas del mini-dialog
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
            SELECT  r.id, r.nombre, r.descripcion, r.porciones,
                    COUNT(ri.id) AS num_ingredientes
            FROM    recetas r
            LEFT JOIN receta_ingredientes ri ON ri.receta_id = r.id
            WHERE   r.activo = 1
            GROUP   BY r.id
            ORDER   BY r.nombre COLLATE NOCASE
        """).fetchall()
        conn.close()

        result = []
        for row in rows:
            d = dict(row)
            d["costo_total"] = self._calcular_costo_receta(d["id"])
            result.append(d)

        self._todos = result
        self._renderizar(self._todos)

    def _calcular_costo_receta(self, receta_id: int) -> float:
        """Suma costo promedio ponderado × cantidad de cada ingrediente."""
        conn = database.get_connection()
        try:
            ings = conn.execute("""
                SELECT materia_prima_id, cantidad
                FROM   receta_ingredientes
                WHERE  receta_id = ?
            """, (receta_id,)).fetchall()
            total = 0.0
            for ing in ings:
                costo_u = database.get_costo_promedio_ponderado(
                    ing["materia_prima_id"], conn
                )
                total += ing["cantidad"] * costo_u
            return total
        finally:
            conn.close()

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
                icon="chef-hat",
                halign="center",
                font_size="48sp",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(56),
            ))
            vacio.add_widget(MDLabel(
                text="No hay recetas registradas",
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
            fila = _FilaReceta(
                row_data=row,
                on_editar=self._abrir_form,
                on_eliminar=self._pedir_confirmar_eliminar,
            )
            if i % 2 == 1:
                fila.md_bg_color = _GRIS
            self._contenedor.add_widget(fila)
            self._contenedor.add_widget(MDDivider())

    # ── Helpers de formulario ─────────────────────────────────────────────────

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

    # ── Formulario principal ──────────────────────────────────────────────────

    def _abrir_form(self, id_receta=None):
        self._id_editando       = id_receta
        self._ingredientes_temp = []
        datos = {}

        if id_receta:
            conn = database.get_connection()
            row = conn.execute(
                "SELECT * FROM recetas WHERE id=?", (id_receta,)
            ).fetchone()
            if row:
                datos = dict(row)
            ings = conn.execute("""
                SELECT ri.materia_prima_id, mp.nombre AS mp_nombre,
                       mp.unidad_medida,    ri.cantidad
                FROM   receta_ingredientes ri
                JOIN   materias_primas mp ON mp.id = ri.materia_prima_id
                WHERE  ri.receta_id = ?
            """, (id_receta,)).fetchall()
            self._ingredientes_temp = [dict(i) for i in ings]
            conn.close()

        # ── Campos sección 1 ──────────────────────────────────────────────
        self._tf_nombre = self._campo_texto(
            "Nombre de receta *",
            datos.get("nombre", ""),
            error_msg="El nombre es obligatorio",
        )
        self._tf_desc = self._campo_texto(
            "Descripción",
            datos.get("descripcion", "") or "",
        )
        porciones_val = datos.get("porciones") or 1
        porc_str = str(int(porciones_val)) if porciones_val == int(porciones_val) else str(porciones_val)
        self._tf_porciones = self._campo_texto(
            "Porciones que produce *",
            porc_str,
            teclado="number",
            error_msg="Ingresa un número mayor a 0",
        )

        # ── Contenedor del formulario ──────────────────────────────────────
        inner = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(4), dp(8), dp(4), dp(8)],
            adaptive_height=True,
        )

        # Sección 1: datos generales
        for w in [self._tf_nombre, self._tf_desc, self._tf_porciones]:
            inner.add_widget(w)

        # Separador sección 2
        inner.add_widget(MDDivider())
        inner.add_widget(MDLabel(
            text="Ingredientes",
            font_style="Title",
            role="small",
            bold=True,
            theme_text_color="Custom",
            text_color=_CAFE,
            size_hint_y=None,
            height=dp(32),
        ))

        # Lista dinámica de ingredientes
        self._caja_ings = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(2),
        )
        inner.add_widget(self._caja_ings)

        # Costo total estimado
        self._lbl_costo_form = MDLabel(
            text="Costo estimado: ₡0.00",
            font_style="Body",
            role="medium",
            bold=True,
            theme_text_color="Custom",
            text_color=_CAFE,
            size_hint_y=None,
            height=dp(30),
        )
        inner.add_widget(self._lbl_costo_form)

        # Botón "Agregar ingrediente"
        btn_agregar_ing = MDButton(
            MDButtonText(
                text="+ Agregar ingrediente",
                theme_text_color="Custom",
                text_color=_DORADO,
            ),
            style="outlined",
            size_hint_y=None,
            height=dp(44),
        )
        btn_agregar_ing.bind(on_release=lambda x: self._abrir_dialog_ingrediente())
        inner.add_widget(btn_agregar_ing)

        # Renderizar ingredientes actuales
        self._renderizar_ingredientes()

        scroll_form = MDScrollView(
            size_hint_y=None,
            height=dp(480),
            do_scroll_x=False,
        )
        scroll_form.add_widget(inner)

        # ── Botones del diálogo ────────────────────────────────────────────
        btns = MDDialogButtonContainer(spacing=dp(4))

        if id_receta:
            btn_del = MDButton(
                MDButtonText(text="Eliminar", theme_text_color="Custom", text_color=_ROJO),
                style="text",
            )
            btn_del.bind(on_release=lambda x: self._desde_form_eliminar(id_receta))
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

        titulo = "Editar receta" if id_receta else "Nueva receta"
        self._dialog_form = MDDialog(
            MDDialogHeadlineText(text=titulo),
            MDDialogContentContainer(scroll_form),
            btns,
        )
        self._dialog_form.open()

    # ── Lista de ingredientes en el formulario ────────────────────────────────

    def _renderizar_ingredientes(self):
        self._caja_ings.clear_widgets()

        if not self._ingredientes_temp:
            self._caja_ings.add_widget(MDLabel(
                text="Sin ingredientes agregados",
                theme_text_color="Secondary",
                halign="center",
                size_hint_y=None,
                height=dp(32),
            ))
        else:
            for idx, ing in enumerate(self._ingredientes_temp):
                self._caja_ings.add_widget(self._fila_ingrediente(idx, ing))

        self._actualizar_costo_form()

    def _fila_ingrediente(self, idx: int, ing: dict):
        fila = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=dp(4),
            padding=[dp(8), dp(2), dp(0), dp(2)],
            md_bg_color=_GRIS if idx % 2 == 0 else _BLANCO,
        )
        fila.radius = [dp(4)]

        nombre   = ing.get("mp_nombre", f"MP #{ing['materia_prima_id']}")
        unidad   = ing.get("unidad_medida", "")
        cantidad = ing["cantidad"]
        cant_str = str(int(cantidad)) if cantidad == int(cantidad) else f"{cantidad:.4g}"

        fila.add_widget(MDLabel(
            text=f"{nombre}  ·  {cant_str} {unidad}".rstrip(),
            size_hint_x=1,
            valign="middle",
            shorten=True,
            shorten_from="right",
        ))

        btn_x = MDIconButton(
            icon="close-circle-outline",
            style="standard",
            theme_icon_color="Custom",
            icon_color=_ROJO,
            size_hint=(None, None),
            size=(dp(36), dp(36)),
        )
        btn_x.bind(on_release=lambda x, i=idx: self._quitar_ingrediente(i))
        fila.add_widget(btn_x)

        return fila

    def _actualizar_costo_form(self):
        if not hasattr(self, "_lbl_costo_form"):
            return
        conn = database.get_connection()
        try:
            total = 0.0
            for ing in self._ingredientes_temp:
                costo_u = database.get_costo_promedio_ponderado(
                    ing["materia_prima_id"], conn
                )
                total += ing["cantidad"] * costo_u
        finally:
            conn.close()
        self._lbl_costo_form.text = f"Costo estimado: ₡{total:,.2f}"

    def _quitar_ingrediente(self, idx: int):
        if 0 <= idx < len(self._ingredientes_temp):
            self._ingredientes_temp.pop(idx)
            self._renderizar_ingredientes()

    # ── Mini-dialog: agregar ingrediente ─────────────────────────────────────

    def _abrir_dialog_ingrediente(self):
        conn = database.get_connection()
        mp_rows = conn.execute("""
            SELECT id, nombre, unidad_medida
            FROM   materias_primas
            WHERE  activo = 1
            ORDER  BY nombre COLLATE NOCASE
        """).fetchall()
        conn.close()

        self._mp_list = [dict(r) for r in mp_rows]
        if not self._mp_list:
            self.show_snack("No hay materias primas registradas")
            return

        # Etiqueta de unidad (se actualiza al seleccionar MP)
        self._lbl_unidad_ing = MDLabel(
            text="Unidad: —",
            theme_text_color="Secondary",
            font_style="Body",
            role="small",
            size_hint_y=None,
            height=dp(24),
        )

        # Selector de materia prima con callback para actualizar unidad
        self._sel_mp_ing = _SelectorDropdown(
            hint="Materia prima *",
            opciones=[mp["nombre"] for mp in self._mp_list],
            on_seleccion=self._on_mp_seleccionada,
        )

        # Campo cantidad
        self._tf_cantidad_ing = MDTextField(
            mode="outlined",
            size_hint_y=None,
            height=dp(68),
        )
        self._tf_cantidad_ing.add_widget(MDTextFieldHintText(text="Cantidad *"))
        self._tf_cantidad_ing.add_widget(
            MDTextFieldHelperText(text="Ingresa un número mayor a 0", mode="on_error")
        )
        self._tf_cantidad_ing.input_type = "number"

        # Contenido del mini-dialog
        inner = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[dp(4), dp(8), dp(4), dp(8)],
            adaptive_height=True,
        )
        inner.add_widget(self._sel_mp_ing)
        inner.add_widget(self._lbl_unidad_ing)
        inner.add_widget(self._tf_cantidad_ing)

        # Botones
        btns_ing = MDDialogButtonContainer(spacing=dp(4))

        btn_cancel = MDButton(MDButtonText(text="Cancelar"), style="text")
        btn_add = MDButton(
            MDButtonText(text="Agregar", theme_text_color="Custom", text_color=_CAFE),
            style="text",
        )

        self._dialog_ing = MDDialog(
            MDDialogHeadlineText(text="Agregar ingrediente"),
            MDDialogContentContainer(inner),
            btns_ing,
        )

        btn_cancel.bind(on_release=lambda x: self._dialog_ing.dismiss())
        btn_add.bind(on_release=lambda x: self._confirmar_agregar_ingrediente())

        btns_ing.add_widget(btn_cancel)
        btns_ing.add_widget(btn_add)

        self._dialog_ing.open()

    def _on_mp_seleccionada(self, nombre_mp: str):
        """Actualiza la etiqueta de unidad al elegir una materia prima."""
        mp = next((m for m in self._mp_list if m["nombre"] == nombre_mp), None)
        if mp:
            self._lbl_unidad_ing.text = f"Unidad: {mp['unidad_medida'] or '—'}"

    def _confirmar_agregar_ingrediente(self):
        nombre_mp = self._sel_mp_ing.valor
        if not nombre_mp:
            self.show_snack("Selecciona una materia prima")
            return

        try:
            cantidad = float(self._tf_cantidad_ing.text.strip())
            if cantidad <= 0:
                raise ValueError
            self._tf_cantidad_ing.error = False
        except (ValueError, TypeError):
            self._tf_cantidad_ing.error = True
            self.show_snack("La cantidad debe ser un número mayor a 0")
            return

        mp = next((m for m in self._mp_list if m["nombre"] == nombre_mp), None)
        if not mp:
            self.show_snack("Materia prima no encontrada")
            return

        # Evitar duplicados
        ya_existe = any(
            i["materia_prima_id"] == mp["id"]
            for i in self._ingredientes_temp
        )
        if ya_existe:
            self.show_snack(f'"{nombre_mp}" ya fue agregado. Elimínalo primero para modificarlo.')
            return

        self._ingredientes_temp.append({
            "materia_prima_id": mp["id"],
            "mp_nombre":        mp["nombre"],
            "unidad_medida":    mp["unidad_medida"] or "",
            "cantidad":         cantidad,
        })

        self._dialog_ing.dismiss()
        self._renderizar_ingredientes()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _guardar(self):
        nombre = self._tf_nombre.text.strip()
        if not nombre:
            self._tf_nombre.error = True
            self.show_snack("El nombre de la receta es obligatorio")
            return
        self._tf_nombre.error = False

        try:
            porciones = float(self._tf_porciones.text.strip())
            if porciones <= 0:
                raise ValueError
            self._tf_porciones.error = False
        except (ValueError, TypeError):
            self._tf_porciones.error = True
            self.show_snack("Las porciones deben ser un número mayor a 0")
            return

        if not self._ingredientes_temp:
            self.show_snack("Agrega al menos un ingrediente a la receta")
            return

        desc = self._tf_desc.text.strip() or None

        conn = database.get_connection()
        try:
            if self._id_editando:
                conn.execute("""
                    UPDATE recetas
                       SET nombre=?, descripcion=?, porciones=?
                     WHERE id=?
                """, (nombre, desc, porciones, self._id_editando))
                conn.execute(
                    "DELETE FROM receta_ingredientes WHERE receta_id=?",
                    (self._id_editando,)
                )
                receta_id = self._id_editando
                msg = "✓ Receta actualizada"
            else:
                cur = conn.execute("""
                    INSERT INTO recetas (nombre, descripcion, porciones)
                    VALUES (?, ?, ?)
                """, (nombre, desc, porciones))
                receta_id = cur.lastrowid
                msg = "✓ Receta creada"

            for ing in self._ingredientes_temp:
                conn.execute("""
                    INSERT INTO receta_ingredientes
                        (receta_id, materia_prima_id, cantidad)
                    VALUES (?, ?, ?)
                """, (receta_id, ing["materia_prima_id"], ing["cantidad"]))

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

    def _desde_form_eliminar(self, id_receta):
        self._dialog_form.dismiss()
        self._pedir_confirmar_eliminar(id_receta)

    def _pedir_confirmar_eliminar(self, id_receta):
        conn = database.get_connection()
        row = conn.execute(
            "SELECT nombre FROM recetas WHERE id=?", (id_receta,)
        ).fetchone()
        conn.close()
        nombre = row["nombre"] if row else "esta receta"

        self.confirmar(
            "Eliminar receta",
            f'¿Está seguro que desea eliminar "{nombre}"?\n\n'
            f"No afectará el historial de producciones existentes.",
            lambda: self._confirmar_eliminar(id_receta),
        )

    def _confirmar_eliminar(self, id_receta):
        conn = database.get_connection()
        conn.execute("UPDATE recetas SET activo=0 WHERE id=?", (id_receta,))
        conn.commit()
        conn.close()
        self.show_snack("Receta eliminada")
        self._cargar_datos()
