"""
modulos/salidas.py — Registro de salidas / producción con lógica PEPS.
KivyMD 1.2.0 compatible.
"""

from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.uix.widget import Widget

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFloatingActionButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.pickers import MDDatePicker

from datetime import date, timedelta

import database
from modulos.base import PantallaBase, MDDivider

_CAFE    = get_color_from_hex("#3E2723")
_DORADO  = get_color_from_hex("#FFA000")
_GRIS    = get_color_from_hex("#F5F5F5")
_BLANCO  = [1, 1, 1, 1]
_ROJO    = get_color_from_hex("#B71C1C")
_VERDE   = get_color_from_hex("#1B5E20")
_NARANJA = get_color_from_hex("#E65100")
_BORDE   = get_color_from_hex("#BDBDBD")

_PERIODOS = ["Todas", "Hoy", "Esta semana", "Este mes"]


def _rango_periodo(periodo: str):
    hoy = date.today()
    if periodo == "Hoy":
        return hoy.isoformat(), hoy.isoformat()
    if periodo == "Esta semana":
        inicio = hoy - timedelta(days=hoy.weekday())
        return inicio.isoformat(), hoy.isoformat()
    if periodo == "Este mes":
        return hoy.replace(day=1).isoformat(), hoy.isoformat()
    return None, None


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

        self._lbl = MDLabel(
            text=hint, theme_text_color="Secondary",
            size_hint_x=1, valign="middle",
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
            self._seleccionar(valor)


# ─── Fila de producción en la lista ──────────────────────────────────────────

class _FilaSalida(MDBoxLayout):
    def __init__(self, row_data: dict, on_eliminar, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None, height=dp(80),
            padding=[dp(8), dp(4), dp(4), dp(4)], spacing=dp(4),
            **kwargs,
        )

        receta  = row_data["receta"]
        fecha   = row_data["fecha"]
        cant    = float(row_data["cantidad_producida"])
        costo   = float(row_data["costo_total"] or 0)
        costo_u = costo / cant if cant > 0 else 0.0
        _id     = row_data["id"]

        avatar = MDBoxLayout(size_hint=(None, None), size=(dp(44), dp(44)), md_bg_color=_CAFE)
        avatar.radius = [dp(22)]
        avatar.add_widget(MDLabel(
            text="P", halign="center", valign="middle",
            theme_text_color="Custom", text_color=_DORADO,
            bold=True, font_size="22sp",
        ))

        textos = MDBoxLayout(orientation="vertical", size_hint_x=1, padding=[dp(8), dp(4), 0, dp(4)])
        textos.add_widget(MDLabel(
            text=receta, font_style="Body1", bold=True,
            size_hint_y=None, height=dp(26),
            shorten=True, shorten_from="right",
        ))
        cant_s = str(int(cant)) if cant == int(cant) else f"{cant:.2f}"
        textos.add_widget(MDLabel(
            text=f"{fecha}  ·  {cant_s} porciones",
            font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(20),
        ))
        textos.add_widget(MDLabel(
            text=f"Total: ₡{costo:,.2f}  ·  ₡{costo_u:,.2f}/porción",
            font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(18),
        ))

        btn_del = MDIconButton(icon="delete-outline", theme_icon_color="Custom", icon_color=_ROJO)
        btn_del.bind(on_release=lambda x, i=_id: on_eliminar(i))

        self.add_widget(avatar)
        self.add_widget(textos)
        self.add_widget(btn_del)


# ─── Pantalla principal ───────────────────────────────────────────────────────

class Pantalla(PantallaBase):
    name            = "salidas"
    titulo_pantalla = "Producción"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dialog_form    = None
        self._todos          = []
        self._recetas_list   = []
        self._receta_sel     = None
        self._periodo_actual = "Todas"
        self._debounce_event = None
        self._construir_ui()

    def _construir_ui(self):
        barra = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(64),
            padding=[dp(12), dp(8)], spacing=dp(8), md_bg_color=_BLANCO,
        )
        barra.add_widget(MDLabel(
            text="Período:", size_hint=(None, None), size=(dp(68), dp(40)),
            valign="middle", theme_text_color="Secondary",
        ))
        self._sel_periodo = _SelectorDropdown(
            hint="Todas", opciones=_PERIODOS, on_seleccion=self._cambiar_periodo,
        )
        barra.add_widget(self._sel_periodo)
        self.layout_raiz.add_widget(barra)
        self.layout_raiz.add_widget(MDDivider())

        self._contenedor = MDBoxLayout(
            orientation="vertical", adaptive_height=True, md_bg_color=_BLANCO,
        )
        scroll = MDScrollView(do_scroll_x=False)
        scroll.add_widget(self._contenedor)
        self.layout_raiz.add_widget(scroll)

        self._footer = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(48),
            padding=[dp(16), dp(8)], spacing=dp(16), md_bg_color=_CAFE,
        )
        self._lbl_total_prod = MDLabel(
            text="0 producción(es)",
            theme_text_color="Custom", text_color=_BLANCO,
            font_style="Body1", size_hint_x=1,
        )
        self._lbl_total_costo = MDLabel(
            text="Costo total: ₡0.00",
            theme_text_color="Custom", text_color=_DORADO,
            font_style="Body1", bold=True, halign="right", size_hint_x=1,
        )
        self._footer.add_widget(self._lbl_total_prod)
        self._footer.add_widget(self._lbl_total_costo)
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
        self._cargar_datos()

    def _cargar_datos(self):
        f_ini, f_fin = _rango_periodo(self._periodo_actual)
        conn = database.get_connection()
        if f_ini:
            rows = conn.execute("""
                SELECT s.id, s.fecha, s.cantidad_producida, s.costo_total, r.nombre AS receta
                FROM salidas s JOIN recetas r ON r.id = s.receta_id
                WHERE s.fecha BETWEEN ? AND ? ORDER BY s.fecha DESC, s.id DESC
            """, (f_ini, f_fin)).fetchall()
        else:
            rows = conn.execute("""
                SELECT s.id, s.fecha, s.cantidad_producida, s.costo_total, r.nombre AS receta
                FROM salidas s JOIN recetas r ON r.id = s.receta_id
                ORDER BY s.fecha DESC, s.id DESC LIMIT 200
            """).fetchall()
        conn.close()
        self._todos = [dict(r) for r in rows]
        self._renderizar(self._todos)

    def _cambiar_periodo(self, periodo: str):
        self._periodo_actual = periodo
        self._cargar_datos()

    def _renderizar(self, rows):
        self._contenedor.clear_widgets()
        if not rows:
            vacio = MDBoxLayout(
                orientation="vertical", size_hint_y=None, height=dp(200),
                padding=[dp(16), dp(32)], spacing=dp(12),
            )
            vacio.add_widget(MDLabel(
                text="Sin producciones registradas",
                halign="center", font_style="H6", theme_text_color="Secondary",
                size_hint_y=None, height=dp(40),
            ))
            vacio.add_widget(MDLabel(
                text='Toca "+" para registrar una nueva producción',
                halign="center", font_style="Body2", theme_text_color="Secondary",
                size_hint_y=None, height=dp(30),
            ))
            self._contenedor.add_widget(vacio)
            self._actualizar_footer([])
            return

        for i, row in enumerate(rows):
            fila = _FilaSalida(row_data=row, on_eliminar=self._pedir_confirmar_eliminar)
            if i % 2 == 1:
                fila.md_bg_color = _GRIS
            self._contenedor.add_widget(fila)
            self._contenedor.add_widget(MDDivider())
        self._actualizar_footer(rows)

    def _actualizar_footer(self, rows):
        if not hasattr(self, "_lbl_total_prod"):
            return
        n = len(rows)
        total = sum(float(r["costo_total"] or 0) for r in rows)
        prod_s = "producción" if n == 1 else "producciones"
        self._lbl_total_prod.text  = f"{n} {prod_s}"
        self._lbl_total_costo.text = f"Costo total: ₡{total:,.2f}"

    def _campo_texto(self, hint: str, texto: str = "", teclado: str = "normal") -> MDTextField:
        tf = MDTextField(
            text=texto, hint_text=hint,
            size_hint_y=None, height=dp(68),
        )
        if teclado != "normal":
            tf.input_type = teclado
        return tf

    def _campo_fecha_con_picker(self, hint: str, texto: str = ""):
        fila = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(68), spacing=dp(4))
        tf = MDTextField(
            text=texto, hint_text=hint,
            helper_text="Formato AAAA-MM-DD",
            size_hint_x=0.82, size_hint_y=None, height=dp(68),
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

    def _abrir_form(self):
        self._receta_sel = None

        conn = database.get_connection()
        recetas = conn.execute("""
            SELECT id, nombre, porciones FROM recetas WHERE activo=1 ORDER BY nombre COLLATE NOCASE
        """).fetchall()
        conn.close()

        self._recetas_list = [dict(r) for r in recetas]
        if not self._recetas_list:
            self.show_snack("No hay recetas registradas. Crea una receta primero.")
            return

        self._sel_receta = _SelectorDropdown(
            hint="Receta *",
            opciones=[r["nombre"] for r in self._recetas_list],
            on_seleccion=self._on_receta_seleccionada,
        )

        self._tf_porciones = self._campo_texto("Cantidad a producir (porciones) *", teclado="number")
        self._tf_porciones.bind(text=self._on_porciones_change)

        fila_fecha, self._tf_fecha = self._campo_fecha_con_picker(
            "Fecha de producción *", date.today().isoformat(),
        )
        self._tf_notas = self._campo_texto("Notas (opcional)")

        self._caja_preview = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(2))

        self._lbl_costo_est = MDLabel(text="", size_hint_y=None, height=dp(0))
        self._lbl_advertencia = MDLabel(
            text="", theme_text_color="Custom", text_color=_ROJO,
            bold=True, size_hint_y=None, height=dp(0),
        )

        inner = MDBoxLayout(
            orientation="vertical", spacing=dp(10),
            padding=[dp(4), dp(8), dp(4), dp(8)], adaptive_height=True,
        )
        for w in [self._sel_receta, self._tf_porciones, fila_fecha, self._tf_notas]:
            inner.add_widget(w)

        inner.add_widget(MDDivider())
        self._lbl_seccion_ing = MDLabel(
            text="Ingredientes necesarios", font_style="Subtitle2", bold=True,
            theme_text_color="Custom", text_color=_CAFE,
            size_hint_y=None, height=dp(0),
        )
        inner.add_widget(self._lbl_seccion_ing)
        inner.add_widget(self._caja_preview)
        inner.add_widget(self._lbl_costo_est)
        inner.add_widget(self._lbl_advertencia)

        scroll_form = MDScrollView(size_hint_y=None, height=dp(500), do_scroll_x=False)
        scroll_form.add_widget(inner)

        self._btn_confirmar_flat = MDFlatButton(
            text="Confirmar producción",
            theme_text_color="Custom", text_color=_CAFE,
            on_release=lambda x: self._registrar(),
        )

        self._dialog_form = MDDialog(
            title="Nueva producción",
            type="custom",
            content_cls=scroll_form,
            buttons=[
                MDFlatButton(text="Cancelar", on_release=lambda x: self._dialog_form.dismiss()),
                self._btn_confirmar_flat,
            ],
        )
        self._dialog_form.open()

    def _on_receta_seleccionada(self, nombre: str):
        rec = next((r for r in self._recetas_list if r["nombre"] == nombre), None)
        self._receta_sel = rec
        self._actualizar_preview()

    def _on_porciones_change(self, instance, value):
        if self._debounce_event:
            self._debounce_event.cancel()
        self._debounce_event = Clock.schedule_once(lambda dt: self._actualizar_preview(), 0.6)

    def _actualizar_preview(self):
        self._caja_preview.clear_widgets()

        if not self._receta_sel:
            self._lbl_seccion_ing.height = dp(0)
            self._lbl_costo_est.height   = dp(0)
            self._lbl_advertencia.height = dp(0)
            return

        try:
            cant = float(self._tf_porciones.text.strip() or "0")
            if cant <= 0:
                cant = 0.0
        except (ValueError, TypeError):
            cant = 0.0

        receta_id = self._receta_sel["id"]
        conn = database.get_connection()
        ings = conn.execute("""
            SELECT ri.materia_prima_id, ri.cantidad,
                   mp.nombre AS mp_nombre, mp.unidad_medida,
                   COALESCE(SUM(l.cantidad_actual), 0) AS stock_actual
            FROM receta_ingredientes ri
            JOIN materias_primas mp ON mp.id = ri.materia_prima_id
            LEFT JOIN lotes l ON l.materia_prima_id = mp.id AND l.activo = 1
            WHERE ri.receta_id = ?
            GROUP BY ri.materia_prima_id
        """, (receta_id,)).fetchall()
        conn.close()

        self._lbl_seccion_ing.height = dp(32)
        self._lbl_costo_est.height   = dp(28)
        self._lbl_advertencia.height = dp(28)

        hay_error   = False
        costo_total = 0.0

        if not ings:
            self._caja_preview.add_widget(MDLabel(
                text="Esta receta no tiene ingredientes",
                theme_text_color="Secondary", size_hint_y=None, height=dp(28),
            ))
            self._lbl_costo_est.text   = ""
            self._lbl_advertencia.text = ""
            return

        conn2 = database.get_connection()
        for idx, ing in enumerate(ings):
            cant_req   = ing["cantidad"] * cant
            stock_disp = float(ing["stock_actual"])
            ok         = cant == 0 or stock_disp >= cant_req - 1e-9
            costo_u    = database.get_costo_promedio_ponderado(ing["materia_prima_id"], conn2)
            costo_total += cant_req * costo_u
            if not ok:
                hay_error = True
            self._caja_preview.add_widget(self._fila_preview_ing(idx, ing, cant_req, stock_disp, ok))
        conn2.close()

        if cant > 0:
            self._lbl_costo_est.text = f"Costo estimado: ₡{costo_total:,.2f}"
            self._lbl_costo_est.theme_text_color = "Custom"
            self._lbl_costo_est.text_color = _CAFE
            self._lbl_costo_est.bold = True
        else:
            self._lbl_costo_est.text = ""

        if hay_error and cant > 0:
            self._lbl_advertencia.text = "⚠ Stock insuficiente. No se puede confirmar la producción."
        else:
            self._lbl_advertencia.text = ""

    def _fila_preview_ing(self, idx: int, ing, cant_req: float, stock: float, ok: bool):
        bg = _GRIS if idx % 2 == 0 else _BLANCO

        fila = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(52),
            spacing=dp(6), padding=[dp(6), dp(2), dp(6), dp(2)], md_bg_color=bg,
        )
        fila.radius = [dp(4)]

        if ok and cant_req > 0:
            icon_name  = "check-circle-outline"; icon_color = _VERDE
        elif cant_req == 0:
            icon_name  = "circle-outline";        icon_color = _BORDE
        else:
            icon_name  = "alert-circle-outline";  icon_color = _ROJO

        fila.add_widget(MDLabel(
            text=icon_name, font_style="Caption",
            size_hint=(None, None), size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5},
        ))

        textos = MDBoxLayout(orientation="vertical", size_hint_x=1)
        nombre = ing["mp_nombre"]
        unidad = ing["unidad_medida"] or ""
        cant_req_s = str(int(cant_req)) if cant_req == int(cant_req) else f"{cant_req:.4g}"
        stock_s    = str(int(stock))    if stock    == int(stock)    else f"{stock:.4g}"

        textos.add_widget(MDLabel(
            text=nombre, font_style="Body1", bold=True,
            size_hint_y=None, height=dp(22),
            shorten=True, shorten_from="right",
        ))
        info_txt = (
            f"Necesario: {cant_req_s} {unidad}  ·  Stock: {stock_s} {unidad}"
        ) if cant_req > 0 else f"Stock: {stock_s} {unidad}"

        lbl_info = MDLabel(
            text=info_txt, font_style="Body2",
            size_hint_y=None, height=dp(20),
            shorten=True, shorten_from="right",
        )
        if not ok and cant_req > 0:
            lbl_info.theme_text_color = "Custom"
            lbl_info.text_color = _ROJO
        else:
            lbl_info.theme_text_color = "Secondary"
        textos.add_widget(lbl_info)
        fila.add_widget(textos)
        return fila

    def _registrar(self):
        if not self._receta_sel:
            self.show_snack("Selecciona una receta")
            return

        try:
            cant = float(self._tf_porciones.text.strip())
            if cant <= 0:
                raise ValueError
        except (ValueError, TypeError):
            self.show_snack("La cantidad de porciones debe ser un número mayor a 0")
            return

        fecha = self._tf_fecha.text.strip()
        if not fecha:
            self.show_snack("Ingresa la fecha de producción")
            return

        receta_id = self._receta_sel["id"]
        obs       = self._tf_notas.text.strip() or None

        conn = database.get_connection()
        costo_total = 0.0
        try:
            ingredientes = conn.execute("""
                SELECT ri.materia_prima_id, ri.cantidad * ? AS cant_total, mp.nombre
                FROM receta_ingredientes ri
                JOIN materias_primas mp ON mp.id = ri.materia_prima_id
                WHERE ri.receta_id = ?
            """, (cant, receta_id)).fetchall()

            if not ingredientes:
                self.show_snack("La receta no tiene ingredientes registrados")
                return

            plan = []
            for ing in ingredientes:
                consumos = database.consumir_peps(ing["materia_prima_id"], ing["cant_total"], conn)
                plan.append((ing["materia_prima_id"], consumos))

            costo_total = sum(
                c["cantidad"] * c["costo_unitario"]
                for _, consumos in plan for c in consumos
            )

            cur = conn.execute("""
                INSERT INTO salidas (receta_id, fecha, cantidad_producida, costo_total, observaciones)
                VALUES (?, ?, ?, ?, ?)
            """, (receta_id, fecha, cant, costo_total, obs))
            salida_id = cur.lastrowid

            for mp_id, consumos in plan:
                for c in consumos:
                    conn.execute(
                        "UPDATE lotes SET cantidad_actual = cantidad_actual - ? WHERE id = ?",
                        (c["cantidad"], c["lote_id"])
                    )
                    conn.execute("""
                        INSERT INTO salida_detalle
                            (salida_id, lote_id, materia_prima_id, cantidad, costo_unitario)
                        VALUES (?, ?, ?, ?, ?)
                    """, (salida_id, c["lote_id"], mp_id, c["cantidad"], c["costo_unitario"]))
                    conn.execute("""
                        INSERT INTO movimientos
                            (tipo, fecha, materia_prima_id, lote_id, cantidad, costo_unitario, referencia)
                        VALUES ('salida', ?, ?, ?, ?, ?, ?)
                    """, (fecha, mp_id, c["lote_id"], c["cantidad"], c["costo_unitario"], f"Salida #{salida_id}"))

            conn.commit()

        except ValueError as e:
            self.show_snack(str(e))
            return
        except Exception as e:
            self.show_snack(f"Error al registrar: {e}")
            return
        finally:
            conn.close()

        self._dialog_form.dismiss()
        cant_s = str(int(cant)) if cant == int(cant) else f"{cant:.2f}"
        self.show_snack(f"✓ Producción registrada — {cant_s} porciones · ₡{costo_total:,.2f}")
        self._cargar_datos()

    def _pedir_confirmar_eliminar(self, id_salida):
        conn = database.get_connection()
        row = conn.execute("""
            SELECT s.fecha, s.cantidad_producida, r.nombre AS receta
            FROM salidas s JOIN recetas r ON r.id = s.receta_id WHERE s.id = ?
        """, (id_salida,)).fetchone()
        conn.close()

        if not row:
            return

        cant_s = str(int(row["cantidad_producida"])) \
            if row["cantidad_producida"] == int(row["cantidad_producida"]) \
            else f"{row['cantidad_producida']:.2f}"

        self.confirmar(
            "Eliminar producción",
            f'¿Eliminar la producción de "{row["receta"]}" del {row["fecha"]} ({cant_s} porciones)?\n\n'
            f"El stock de ingredientes será restaurado automáticamente.",
            lambda: self._confirmar_eliminar(id_salida),
        )

    def _confirmar_eliminar(self, id_salida):
        conn = database.get_connection()
        try:
            detalles = conn.execute(
                "SELECT lote_id, cantidad FROM salida_detalle WHERE salida_id = ?", (id_salida,)
            ).fetchall()
            for d in detalles:
                conn.execute(
                    "UPDATE lotes SET cantidad_actual = cantidad_actual + ? WHERE id = ?",
                    (d["cantidad"], d["lote_id"])
                )
            conn.execute("DELETE FROM salida_detalle WHERE salida_id = ?", (id_salida,))
            conn.execute("DELETE FROM movimientos WHERE referencia = ?", (f"Salida #{id_salida}",))
            conn.execute("DELETE FROM salidas WHERE id = ?", (id_salida,))
            conn.commit()
        except Exception as e:
            self.show_snack(f"Error al eliminar: {e}")
            return
        finally:
            conn.close()

        self.show_snack("✓ Producción eliminada y stock restaurado")
        self._cargar_datos()
