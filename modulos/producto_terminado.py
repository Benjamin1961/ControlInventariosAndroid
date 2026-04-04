"""
modulos/producto_terminado.py — Gestión de productos terminados.
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
from kivymd.uix.divider import MDDivider
from kivymd.uix.button import MDFloatingActionButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.pickers import MDDatePicker

from datetime import date, timedelta

import database
from modulos.base import PantallaBase

_CAFE    = get_color_from_hex("#3E2723")
_DORADO  = get_color_from_hex("#FFA000")
_GRIS    = get_color_from_hex("#F5F5F5")
_BLANCO  = [1, 1, 1, 1]
_ROJO    = get_color_from_hex("#B71C1C")
_VERDE   = get_color_from_hex("#1B5E20")
_NARANJA = get_color_from_hex("#E65100")
_GRIS_T  = get_color_from_hex("#757575")


def _estado_vencimiento(fecha_venc: str):
    if not fecha_venc:
        return ("", _GRIS_T, "Sin fecha de vencimiento")
    hoy   = date.today().isoformat()
    lim30 = (date.today() + timedelta(days=30)).isoformat()
    if fecha_venc < hoy:
        return ("⬤", _ROJO,    f"VENCIDO  {fecha_venc}")
    if fecha_venc <= lim30:
        return ("⬤", _NARANJA, f"Vence pronto  {fecha_venc}")
    return ("⬤", _VERDE, f"Vigente  {fecha_venc}")


# ─── Selector dropdown genérico ──────────────────────────────────────────────

class _SelectorDropdown(MDBoxLayout):
    def __init__(self, hint: str, opciones: list, on_seleccion=None, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(56), **kwargs)
        self._opciones = opciones
        self._menu     = None
        self.valor     = ""
        self._callback = on_seleccion

        self._caja = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(56),
            padding=[dp(12), 0, dp(8), 0], spacing=dp(4), md_bg_color=_GRIS,
        )
        self._caja.radius = [dp(4)]

        self._lbl = MDLabel(text=hint, theme_text_color="Secondary", size_hint_x=1, valign="middle")
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
        self._menu = MDDropdownMenu(caller=self._caja, items=items, width_mult=5)
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
        if valor:
            self.valor = valor
            self._lbl.text = valor
            self._lbl.theme_text_color = "Primary"


# ─── Fila de producto en la lista ─────────────────────────────────────────────

class _FilaProducto(MDBoxLayout):
    def __init__(self, row_data: dict, on_editar, on_eliminar, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None, height=dp(96),
            padding=[dp(0), dp(4), dp(4), dp(4)], spacing=dp(6),
            **kwargs,
        )

        nombre    = row_data["nombre"]
        cantidad  = float(row_data["cantidad"]       or 0)
        costo_u   = float(row_data["costo_unitario"] or 0)
        precio    = float(row_data["precio_venta"]   or 0)
        margen    = float(row_data["margen_ganancia"]or 0)
        f_prod    = row_data["fecha_produccion"]      or "—"
        f_venc    = row_data["fecha_vencimiento"]     or ""
        _id       = row_data["id"]

        emoji_v, color_v, texto_v = _estado_vencimiento(f_venc)

        franja = MDBoxLayout(size_hint=(None, None), size=(dp(6), dp(88)), md_bg_color=color_v)
        franja.radius = [dp(3), dp(0), dp(0), dp(3)]

        textos = MDBoxLayout(
            orientation="vertical", size_hint_x=1,
            padding=[dp(8), dp(4), 0, dp(4)], spacing=dp(1),
        )
        textos.add_widget(MDLabel(
            text=nombre, font_style="Body1", bold=True,
            size_hint_y=None, height=dp(24),
            shorten=True, shorten_from="right",
        ))
        textos.add_widget(MDLabel(
            text=f"Producción: {f_prod}",
            font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(18),
        ))

        lbl_venc = MDLabel(
            text=f"{emoji_v} {texto_v}".strip() if emoji_v else texto_v,
            font_style="Body2", size_hint_y=None, height=dp(18),
        )
        if emoji_v:
            lbl_venc.theme_text_color = "Custom"
            lbl_venc.text_color = color_v
        else:
            lbl_venc.theme_text_color = "Secondary"
        textos.add_widget(lbl_venc)

        cant_s = str(int(cantidad)) if cantidad == int(cantidad) else f"{cantidad:.2f}"
        textos.add_widget(MDLabel(
            text=f"Cant: {cant_s}  ·  Costo: ₡{costo_u:,.2f}  ·  Margen: {margen:.1f}%",
            font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(18),
        ))
        textos.add_widget(MDLabel(
            text=f"Precio de venta: ₡{precio:,.2f}",
            font_style="Body2", bold=True,
            theme_text_color="Custom", text_color=_VERDE,
            size_hint_y=None, height=dp(18),
        ))

        btn_ed = MDIconButton(icon="pencil-outline", theme_icon_color="Custom", icon_color=_CAFE)
        btn_ed.bind(on_release=lambda x, i=_id: on_editar(i))
        btn_del = MDIconButton(icon="delete-outline", theme_icon_color="Custom", icon_color=_ROJO)
        btn_del.bind(on_release=lambda x, i=_id: on_eliminar(i))

        self.add_widget(franja)
        self.add_widget(textos)
        self.add_widget(btn_ed)
        self.add_widget(btn_del)


# ─── Pantalla principal ───────────────────────────────────────────────────────

class Pantalla(PantallaBase):
    name            = "producto_terminado"
    titulo_pantalla = "Producto Terminado"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._id_editando  = None
        self._dialog_form  = None
        self._todos        = []
        self._recetas_list = []
        self._debounce_evt = None
        self._construir_ui()

    def _construir_ui(self):
        barra = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(64),
            padding=[dp(12), dp(8)], md_bg_color=_BLANCO,
        )
        self._tf_buscar = MDTextField(
            hint_text="Buscar por nombre…", mode="rectangle", size_hint_x=1,
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

        self._footer = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(48),
            padding=[dp(16), dp(8)], spacing=dp(8), md_bg_color=_CAFE,
        )
        self._lbl_total_prod = MDLabel(
            text="0 producto(s)",
            theme_text_color="Custom", text_color=_BLANCO,
            font_style="Body1", size_hint_x=1,
        )
        self._lbl_valor_stock = MDLabel(
            text="Valor stock: ₡0.00",
            theme_text_color="Custom", text_color=_DORADO,
            font_style="Body1", bold=True, halign="right", size_hint_x=1,
        )
        self._footer.add_widget(self._lbl_total_prod)
        self._footer.add_widget(self._lbl_valor_stock)
        self.layout_raiz.add_widget(self._footer)

        self._fab = MDFloatingActionButton(
            icon="plus", md_bg_color=_CAFE, pos_hint={"right": 0.97, "y": 0.08},
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
            SELECT id, nombre, cantidad, costo_unitario, costo_total,
                   precio_venta, margen_ganancia,
                   fecha_produccion, fecha_vencimiento, observaciones, salida_id
            FROM productos_terminados ORDER BY fecha_produccion DESC, id DESC
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
                text="No hay productos registrados",
                halign="center", font_style="H6", theme_text_color="Secondary",
                size_hint_y=None, height=dp(40),
            ))
            vacio.add_widget(MDLabel(
                text='Toca "+" para registrar el primer producto',
                halign="center", font_style="Body2", theme_text_color="Secondary",
                size_hint_y=None, height=dp(30),
            ))
            self._contenedor.add_widget(vacio)
            self._actualizar_footer([])
            return

        for i, row in enumerate(rows):
            fila = _FilaProducto(
                row_data=row,
                on_editar=self._abrir_form,
                on_eliminar=self._pedir_confirmar_eliminar,
            )
            if i % 2 == 1:
                fila.md_bg_color = _GRIS
            self._contenedor.add_widget(fila)
            self._contenedor.add_widget(MDDivider())
        self._actualizar_footer(rows)

    def _actualizar_footer(self, rows):
        if not hasattr(self, "_lbl_total_prod"):
            return
        n     = len(rows)
        valor = sum(float(r["cantidad"] or 0) * float(r["costo_unitario"] or 0) for r in rows)
        prod_s = "producto" if n == 1 else "productos"
        self._lbl_total_prod.text  = f"{n} {prod_s}"
        self._lbl_valor_stock.text = f"Valor stock: ₡{valor:,.2f}"

    def _campo_texto(self, hint: str, texto: str = "",
                     teclado: str = "normal", error_msg: str = "") -> MDTextField:
        tf = MDTextField(
            text=texto, hint_text=hint,
            helper_text=error_msg,
            helper_text_mode="on_error" if error_msg else "none",
            mode="rectangle", size_hint_y=None, height=dp(68),
        )
        if teclado != "normal":
            tf.input_type = teclado
        return tf

    def _campo_fecha_con_picker(self, hint: str, texto: str = ""):
        fila = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(68), spacing=dp(4))
        tf = MDTextField(
            text=texto, hint_text=hint,
            helper_text="Formato AAAA-MM-DD", helper_text_mode="on_focus",
            mode="rectangle", size_hint_x=0.82, size_hint_y=None, height=dp(68),
        )
        btn_cal = MDIconButton(
            icon="calendar-month",
            size_hint_x=None, width=dp(48), size_hint_y=None, height=dp(48),
            theme_icon_color="Custom", icon_color=_CAFE,
        )
        btn_cal.bind(on_release=lambda x, t=tf: self._abrir_picker(t))
        fila.add_widget(tf)
        fila.add_widget(btn_cal)
        return fila, tf

    def _abrir_picker(self, tf):
        picker = MDDatePicker()
        def on_save(instance, value, date_range):
            tf.text = value.strftime("%Y-%m-%d")
        picker.bind(on_save=on_save)
        picker.open()

    def _abrir_form(self, id_pt=None):
        self._id_editando = id_pt
        datos = {}

        if id_pt:
            conn = database.get_connection()
            row = conn.execute("SELECT * FROM productos_terminados WHERE id=?", (id_pt,)).fetchone()
            conn.close()
            if row:
                datos = dict(row)

        conn = database.get_connection()
        recetas_rows = conn.execute(
            "SELECT id, nombre FROM recetas WHERE activo=1 ORDER BY nombre COLLATE NOCASE"
        ).fetchall()
        conn.close()
        self._recetas_list = [dict(r) for r in recetas_rows]
        opciones_receta = ["— Sin receta —"] + [r["nombre"] for r in self._recetas_list]

        nombre_receta_actual = ""
        if datos.get("salida_id"):
            conn = database.get_connection()
            sal = conn.execute("""
                SELECT r.nombre FROM salidas s JOIN recetas r ON r.id = s.receta_id WHERE s.id = ?
            """, (datos["salida_id"],)).fetchone()
            conn.close()
            if sal:
                nombre_receta_actual = sal["nombre"]

        self._tf_nombre = self._campo_texto(
            "Nombre del producto *", datos.get("nombre", ""), error_msg="El nombre es obligatorio"
        )
        self._sel_receta = _SelectorDropdown(
            hint="Receta asociada (opcional)",
            opciones=opciones_receta,
            on_seleccion=self._on_receta_seleccionada,
        )
        if nombre_receta_actual:
            self._sel_receta.set_valor(nombre_receta_actual)

        self._tf_cantidad = self._campo_texto(
            "Cantidad *", str(datos.get("cantidad", "") or ""),
            teclado="number", error_msg="Ingresa un número mayor a 0",
        )

        fila_fprod, self._tf_fprod = self._campo_fecha_con_picker(
            "Fecha de producción *",
            datos.get("fecha_produccion", date.today().isoformat()) or date.today().isoformat(),
        )
        fila_fvenc, self._tf_fvenc = self._campo_fecha_con_picker(
            "Fecha de vencimiento", datos.get("fecha_vencimiento", "") or "",
        )

        costo_val  = datos.get("costo_unitario", 0) or 0
        margen_val = datos.get("margen_ganancia", 0) or 0
        precio_val = datos.get("precio_venta", 0) or 0

        self._tf_costo = self._campo_texto(
            "Costo unitario (₡)", f"{costo_val:.2f}" if costo_val else "", teclado="number"
        )
        self._tf_margen = self._campo_texto(
            "Margen de ganancia (%) *",
            f"{margen_val:.1f}" if margen_val else "",
            teclado="number", error_msg="Ingresa un porcentaje (ej: 30)",
        )

        self._lbl_precio_calc = MDLabel(
            text=self._texto_precio(costo_val, margen_val, precio_val),
            theme_text_color="Custom", text_color=_VERDE,
            font_style="Subtitle2", bold=True,
            size_hint_y=None, height=dp(36), halign="right",
        )
        self._tf_notas = self._campo_texto("Notas (opcional)", datos.get("observaciones", "") or "")

        self._tf_costo.bind(text=self._on_costo_margen_change)
        self._tf_margen.bind(text=self._on_costo_margen_change)

        inner = MDBoxLayout(
            orientation="vertical", spacing=dp(10),
            padding=[dp(4), dp(8), dp(4), dp(8)], adaptive_height=True,
        )
        for w in [self._tf_nombre, self._sel_receta, self._tf_cantidad, fila_fprod, fila_fvenc]:
            inner.add_widget(w)

        inner.add_widget(MDDivider())
        inner.add_widget(MDLabel(
            text="Costos y precio", font_style="Subtitle2", bold=True,
            theme_text_color="Custom", text_color=_CAFE,
            size_hint_y=None, height=dp(32),
        ))
        for w in [self._tf_costo, self._tf_margen, self._lbl_precio_calc, self._tf_notas]:
            inner.add_widget(w)

        scroll_form = MDScrollView(size_hint_y=None, height=Window.height * 0.55, do_scroll_x=False)
        scroll_form.add_widget(inner)

        buttons = []
        if id_pt:
            buttons.append(MDFlatButton(
                text="Eliminar", theme_text_color="Custom", text_color=_ROJO,
                on_release=lambda x: self._desde_form_eliminar(id_pt),
            ))
        buttons.append(MDFlatButton(text="Cancelar", on_release=lambda x: self._dialog_form.dismiss()))
        buttons.append(MDFlatButton(
            text="Guardar", theme_text_color="Custom", text_color=_CAFE,
            on_release=lambda x: self._guardar(),
        ))

        titulo = "Editar producto" if id_pt else "Nuevo producto terminado"
        self._dialog_form = MDDialog(title=titulo, type="custom", content_cls=scroll_form, buttons=buttons)
        self._dialog_form.open()

    def _texto_precio(self, costo, margen, precio_actual=None) -> str:
        try:
            c = float(costo)
            m = float(margen)
            if c > 0:
                p = c * (1 + m / 100)
                return f"Precio de venta: ₡{p:,.2f}"
        except (ValueError, TypeError):
            pass
        if precio_actual and float(precio_actual or 0) > 0:
            return f"Precio de venta: ₡{float(precio_actual):,.2f}"
        return "Precio de venta: ₡—"

    def _on_costo_margen_change(self, instance, value):
        if self._debounce_evt:
            self._debounce_evt.cancel()
        self._debounce_evt = Clock.schedule_once(lambda dt: self._recalcular_precio(), 0.4)

    def _recalcular_precio(self):
        if not hasattr(self, "_lbl_precio_calc"):
            return
        costo  = self._tf_costo.text.strip()
        margen = self._tf_margen.text.strip()
        self._lbl_precio_calc.text = self._texto_precio(costo, margen)

    def _on_receta_seleccionada(self, nombre: str):
        if nombre == "— Sin receta —" or not nombre:
            return
        rec = next((r for r in self._recetas_list if r["nombre"] == nombre), None)
        if not rec:
            return

        conn = database.get_connection()
        try:
            ings = conn.execute(
                "SELECT ri.materia_prima_id, ri.cantidad FROM receta_ingredientes ri WHERE ri.receta_id = ?",
                (rec["id"],)
            ).fetchall()
            costo_batch = sum(
                ing["cantidad"] * database.get_costo_promedio_ponderado(ing["materia_prima_id"], conn)
                for ing in ings
            )
            receta_row = conn.execute("SELECT porciones FROM recetas WHERE id=?", (rec["id"],)).fetchone()
            porciones = float(receta_row["porciones"] or 1) if receta_row else 1
            costo_unit = costo_batch / porciones if porciones > 0 else costo_batch
        finally:
            conn.close()

        if hasattr(self, "_tf_costo") and costo_unit > 0:
            self._tf_costo.text = f"{costo_unit:.2f}"

    def _guardar(self):
        nombre = self._tf_nombre.text.strip()
        if not nombre:
            self._tf_nombre.error = True
            self.show_snack("El nombre del producto es obligatorio")
            return
        self._tf_nombre.error = False

        try:
            cantidad = float(self._tf_cantidad.text.strip())
            if cantidad <= 0:
                raise ValueError
            self._tf_cantidad.error = False
        except (ValueError, TypeError):
            self._tf_cantidad.error = True
            self.show_snack("La cantidad debe ser un número mayor a 0")
            return

        fecha_prod = self._tf_fprod.text.strip()
        if not fecha_prod:
            self.show_snack("La fecha de producción es obligatoria")
            return

        try:
            margen = float(self._tf_margen.text.strip() or 0)
            self._tf_margen.error = False
        except (ValueError, TypeError):
            self._tf_margen.error = True
            self.show_snack("El margen debe ser un número (ej: 30)")
            return

        try:
            costo_u = float(self._tf_costo.text.strip() or 0)
        except (ValueError, TypeError):
            costo_u = 0.0

        precio_venta = costo_u * (1 + margen / 100) if costo_u > 0 else 0.0
        costo_total  = costo_u * cantidad
        fecha_venc   = self._tf_fvenc.text.strip() or None
        obs          = self._tf_notas.text.strip() or None

        conn = database.get_connection()
        try:
            if self._id_editando:
                conn.execute("""
                    UPDATE productos_terminados
                       SET nombre=?, cantidad=?, costo_unitario=?, costo_total=?,
                           precio_venta=?, margen_ganancia=?,
                           fecha_produccion=?, fecha_vencimiento=?, observaciones=?
                     WHERE id=?
                """, (nombre, cantidad, costo_u, costo_total,
                      precio_venta, margen, fecha_prod, fecha_venc, obs, self._id_editando))
                msg = "✓ Producto actualizado"
            else:
                conn.execute("""
                    INSERT INTO productos_terminados
                        (nombre, cantidad, costo_unitario, costo_total,
                         precio_venta, margen_ganancia,
                         fecha_produccion, fecha_vencimiento, observaciones)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (nombre, cantidad, costo_u, costo_total,
                      precio_venta, margen, fecha_prod, fecha_venc, obs))
                msg = "✓ Producto registrado"
            conn.commit()
        except Exception as e:
            self.show_snack(f"Error al guardar: {e}")
            return
        finally:
            conn.close()

        self._dialog_form.dismiss()
        self.show_snack(msg)
        self._cargar_datos()

    def _desde_form_eliminar(self, id_pt):
        self._dialog_form.dismiss()
        self._pedir_confirmar_eliminar(id_pt)

    def _pedir_confirmar_eliminar(self, id_pt):
        conn = database.get_connection()
        row = conn.execute("SELECT nombre FROM productos_terminados WHERE id=?", (id_pt,)).fetchone()
        conn.close()
        nombre = row["nombre"] if row else "este producto"
        self.confirmar(
            "Eliminar producto",
            f'¿Está seguro que desea eliminar "{nombre}"?\n\nEsta acción no puede deshacerse.',
            lambda: self._confirmar_eliminar(id_pt),
        )

    def _confirmar_eliminar(self, id_pt):
        conn = database.get_connection()
        conn.execute("DELETE FROM productos_terminados WHERE id=?", (id_pt,))
        conn.commit()
        conn.close()
        self.show_snack("✓ Producto eliminado")
        self._cargar_datos()
