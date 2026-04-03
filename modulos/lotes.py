"""
modulos/lotes.py — Registro y consulta de lotes / ingresos de materia prima.
KivyMD 2.0.

Características:
- Lista scrolleable con semáforo de vencimientos (rojo/naranja/verde)
- Indicador PEPS: marca el lote "próximo a usar" por materia prima
- Filtro superior por materia prima
- Formulario con DatePicker, dropdowns de MP y Proveedor
- Costo total calculado automáticamente (cantidad × costo unitario)
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
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText
from kivymd.uix.dialog import (
    MDDialog, MDDialogHeadlineText,
    MDDialogButtonContainer, MDDialogContentContainer,
)
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.pickers import MDModalDatePicker

from datetime import date, timedelta

import database
from modulos.base import PantallaBase

# ─── Paleta ───────────────────────────────────────────────────────────────────
_CAFE    = get_color_from_hex("#3E2723")
_DORADO  = get_color_from_hex("#FFA000")
_BLANCO  = [1, 1, 1, 1]
_GRIS_BG = get_color_from_hex("#F5F5F5")
_VERDE   = get_color_from_hex("#1B5E20")
_NARANJA = get_color_from_hex("#E65100")
_ROJO    = get_color_from_hex("#B71C1C")
_GRIS    = get_color_from_hex("#757575")


# ─── Helper: fecha de hoy + 30 días ──────────────────────────────────────────

def _en_30_dias():
    return (date.today() + timedelta(days=30)).isoformat()


# ─── Widget dropdown reutilizable ─────────────────────────────────────────────

class _DropdownCampo(MDBoxLayout):
    """
    Campo con estilo outlined que abre un MDDropdownMenu al tocarlo.
    Uso: instanciar con hint y lista de (texto_visible, valor_id).
    """

    def __init__(self, hint, opciones, **kwargs):
        """
        opciones: lista de dict {"texto": str, "valor": any}
        """
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=dp(0),
            **kwargs,
        )
        self._hint    = hint
        self._opciones = opciones
        self._valor   = None
        self._menu    = None

        # Caja outlined (simula MDTextField outlined)
        self._caja = MDBoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=dp(56),
            padding=[dp(12), dp(0), dp(4), dp(0)],
            spacing=dp(4),
        )
        self._caja.md_bg_color = [1, 1, 1, 1]
        self._caja.radius = [dp(4)]

        self._lbl = MDLabel(
            text=hint,
            theme_text_color="Hint",
            size_hint_x=0.88,
        )
        icon = MDIcon(
            icon="chevron-down",
            theme_text_color="Secondary",
            size_hint=(None, None),
            size=(dp(24), dp(24)),
        )
        self._caja.add_widget(self._lbl)
        self._caja.add_widget(icon)
        self.add_widget(self._caja)

        self._caja.bind(on_touch_down=self._on_touch)

    def _on_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self._abrir_menu()
            return True

    def _abrir_menu(self):
        if self._menu:
            self._menu.dismiss()
        items = [
            {
                "text": op["texto"],
                "on_release": (lambda v, t: lambda: self._seleccionar(v, t))(
                    op["valor"], op["texto"]
                ),
            }
            for op in self._opciones
        ]
        self._menu = MDDropdownMenu(
            caller=self._caja,
            items=items,
            width=dp(260),
        )
        self._menu.open()

    def _seleccionar(self, valor, texto):
        self._valor = valor
        self._lbl.text = texto
        self._lbl.theme_text_color = "Primary"
        if self._menu:
            self._menu.dismiss()

    def set_valor(self, valor, texto):
        """Pre-selecciona un valor (modo edición)."""
        self._valor = valor
        self._lbl.text = texto
        self._lbl.theme_text_color = "Primary"

    def set_opciones(self, opciones):
        """Reemplaza la lista de opciones (para carga dinámica)."""
        self._opciones = opciones

    @property
    def valor(self):
        return self._valor


# ─── Widget de fila individual ────────────────────────────────────────────────

class _FilaLote(MDBoxLayout):
    """
    Fila de la lista:
      [circulo-inicial-MP] [info: MP·proveedor / lote·ingreso / cant·costo / vencimiento] [editar][eliminar]
    """

    def __init__(self, row_data: dict, es_peps: bool, on_editar, on_eliminar, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(108),
            padding=[dp(8), dp(6), dp(4), dp(6)],
            spacing=dp(6),
            **kwargs,
        )

        materia  = row_data["materia"]
        unidad   = row_data["unidad_medida"]
        proveedor = row_data["proveedor"] or "—"
        numero   = row_data["numero_lote"]
        f_ing    = row_data["fecha_ingreso"]
        cantidad = float(row_data["cantidad_actual"])
        costo    = float(row_data["costo_unitario"])
        vence    = row_data["fecha_vencimiento"] or ""

        hoy     = date.today().isoformat()
        lim30   = _en_30_dias()

        if not vence:
            color_v = _GRIS
            txt_v   = "Sin fecha de vencimiento"
        elif vence < hoy:
            color_v = _ROJO
            txt_v   = f"⬤ VENCIDO  {vence}"
        elif vence <= lim30:
            color_v = _NARANJA
            txt_v   = f"⬤ Vence pronto  {vence}"
        else:
            color_v = _VERDE
            txt_v   = f"⬤ Vigente  {vence}"

        # ── Avatar circular (inicial de MP) ───────────────────────────────
        avatar = MDBoxLayout(
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            md_bg_color=_CAFE,
        )
        avatar.radius = [dp(20)]
        avatar.add_widget(MDLabel(
            text=materia[0].upper() if materia else "?",
            halign="center",
            valign="middle",
            theme_text_color="Custom",
            text_color=_BLANCO,
            bold=True,
        ))

        # ── Columna de información ────────────────────────────────────────
        info = MDBoxLayout(
            orientation="vertical",
            size_hint_x=0.78,
            spacing=dp(1),
        )

        peps_tag = "  ⚑ PEPS" if es_peps else ""
        lbl_mp = MDLabel(
            text=f"{materia}{peps_tag}",
            font_style="Body",
            role="large",
            bold=True,
            size_hint_y=None,
            height=dp(22),
            shorten=True,
            shorten_from="right",
        )
        if es_peps:
            lbl_mp.theme_text_color = "Custom"
            lbl_mp.text_color = _DORADO

        lbl_prov = MDLabel(
            text=f"Proveedor: {proveedor}",
            font_style="Body",
            role="small",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(18),
            shorten=True,
            shorten_from="right",
        )
        lbl_lote = MDLabel(
            text=f"Lote: {numero}  ·  Ingreso: {f_ing}",
            font_style="Body",
            role="small",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(18),
        )
        total = cantidad * costo
        lbl_cant = MDLabel(
            text=f"{cantidad:.3f} {unidad}  ·  ₡{costo:,.2f}/u  ·  Total: ₡{total:,.2f}",
            font_style="Body",
            role="small",
            size_hint_y=None,
            height=dp(18),
        )
        lbl_vence = MDLabel(
            text=txt_v,
            font_style="Body",
            role="small",
            theme_text_color="Custom",
            text_color=color_v,
            size_hint_y=None,
            height=dp(18),
        )

        for w in [lbl_mp, lbl_prov, lbl_lote, lbl_cant, lbl_vence]:
            info.add_widget(w)

        # ── Botones ───────────────────────────────────────────────────────
        btns = MDBoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(40),
            spacing=dp(2),
        )
        btn_editar  = MDIconButton(icon="pencil",           size_hint_y=0.5)
        btn_eliminar = MDIconButton(icon="trash-can-outline", size_hint_y=0.5)
        btn_editar.bind(on_release=lambda x: on_editar())
        btn_eliminar.bind(on_release=lambda x: on_eliminar())
        btns.add_widget(btn_editar)
        btns.add_widget(btn_eliminar)

        self.add_widget(avatar)
        self.add_widget(info)
        self.add_widget(btns)


# ─── Pantalla principal ───────────────────────────────────────────────────────

class Pantalla(PantallaBase):
    name = "lotes"
    titulo_pantalla = "Lotes e Ingresos"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._id_editando    = None
        self._dialog_form    = None
        self._todos          = []        # caché de rows
        self._filtro_mp_id   = None      # None = todos
        self._filtro_mp_txt  = "Todas las materias primas"
        self._menu_filtro    = None
        self._construir_ui()

    # ── Construcción de UI ────────────────────────────────────────────────────

    def _construir_ui(self):
        # Barra de filtro
        barra = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(6)],
            spacing=dp(8),
        )
        self._btn_filtro = MDButton(
            MDButtonText(text="Todas las materias primas"),
            style="outlined",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(44),
        )
        self._btn_filtro.bind(on_release=lambda x: self._abrir_filtro())
        barra.add_widget(self._btn_filtro)
        self.layout_raiz.add_widget(barra)

        # Lista scrolleable
        self._contenedor = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=0,
            padding=[0, dp(8), 0, 0],
        )
        scroll = MDScrollView()
        scroll.add_widget(self._contenedor)
        self.layout_raiz.add_widget(scroll)

        # FAB
        self._fab = MDFabButton(
            icon="plus",
            style="standard",
            theme_bg_color="Custom",
            md_bg_color=_CAFE,
            pos_hint={"right": 0.97, "y": 0.02},
        )
        self._fab.bind(on_release=lambda x: self._abrir_form())
        self.add_widget(self._fab)
        Clock.schedule_once(self._aplicar_color_fab, 0)

    def _aplicar_color_fab(self, dt):
        self._fab.theme_icon_color = "Custom"
        self._fab.icon_color = _DORADO

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def on_pre_enter(self, *args):
        self._cargar_lista()

    # ── Filtro de materia prima ───────────────────────────────────────────────

    def _abrir_filtro(self):
        conn = database.get_connection()
        mps = conn.execute(
            "SELECT id, nombre FROM materias_primas WHERE activo=1 ORDER BY nombre"
        ).fetchall()
        conn.close()

        items = [{"text": "Todas las materias primas",
                  "on_release": lambda: self._aplicar_filtro(None, "Todas las materias primas")}]
        for mp in mps:
            items.append({
                "text": mp["nombre"],
                "on_release": (
                    lambda mid, mnom: lambda: self._aplicar_filtro(mid, mnom)
                )(mp["id"], mp["nombre"]),
            })

        if self._menu_filtro:
            self._menu_filtro.dismiss()
        self._menu_filtro = MDDropdownMenu(
            caller=self._btn_filtro,
            items=items,
            width=dp(280),
        )
        self._menu_filtro.open()

    def _aplicar_filtro(self, mp_id, texto):
        self._filtro_mp_id  = mp_id
        self._filtro_mp_txt = texto
        # Actualizar texto del botón
        for w in self._btn_filtro.children:
            if isinstance(w, MDButtonText):
                w.text = texto
                break
        if self._menu_filtro:
            self._menu_filtro.dismiss()
        self._cargar_lista()

    # ── Carga y renderizado ───────────────────────────────────────────────────

    def _cargar_lista(self):
        self._contenedor.clear_widgets()

        conn = database.get_connection()

        # Obtener IDs PEPS (lote más antiguo con stock por materia prima)
        peps_ids = set()
        mps_con_stock = conn.execute(
            "SELECT DISTINCT materia_prima_id FROM lotes WHERE activo=1 AND cantidad_actual>0"
        ).fetchall()
        for r in mps_con_stock:
            lote_peps = conn.execute("""
                SELECT id FROM lotes
                WHERE materia_prima_id=? AND activo=1 AND cantidad_actual>0
                ORDER BY fecha_ingreso ASC, id ASC
                LIMIT 1
            """, (r["materia_prima_id"],)).fetchone()
            if lote_peps:
                peps_ids.add(lote_peps["id"])

        # Consulta principal
        where = "WHERE l.activo=1"
        params = []
        if self._filtro_mp_id is not None:
            where += " AND l.materia_prima_id=?"
            params.append(self._filtro_mp_id)

        rows = conn.execute(f"""
            SELECT l.id, l.numero_lote, l.fecha_ingreso, l.fecha_vencimiento,
                   l.cantidad_inicial, l.cantidad_actual, l.costo_unitario,
                   mp.nombre AS materia, mp.unidad_medida,
                   p.nombre  AS proveedor
            FROM lotes l
            JOIN materias_primas mp ON mp.id = l.materia_prima_id
            LEFT JOIN proveedores p ON p.id = l.proveedor_id
            {where}
            ORDER BY l.fecha_ingreso ASC, l.id ASC
        """, params).fetchall()
        conn.close()

        if not rows:
            icono = MDIcon(
                icon="inbox-remove-outline",
                halign="center",
                font_size="64sp",
                theme_text_color="Hint",
            )
            lbl = MDLabel(
                text="Sin lotes registrados",
                halign="center",
                theme_text_color="Hint",
                size_hint_y=None,
                height=dp(40),
            )
            espacio = Widget(size_hint_y=None, height=dp(80))
            self._contenedor.add_widget(espacio)
            self._contenedor.add_widget(icono)
            self._contenedor.add_widget(lbl)
            return

        for row in rows:
            _id    = row["id"]
            es_peps = _id in peps_ids
            fila = _FilaLote(
                row_data=dict(row),
                es_peps=es_peps,
                on_editar=lambda i=_id: self._abrir_form(i),
                on_eliminar=lambda i=_id: self._confirmar_eliminar_ui(i),
            )
            self._contenedor.add_widget(fila)
            self._contenedor.add_widget(MDDivider())

    # ── Helpers de formulario ─────────────────────────────────────────────────

    def _campo_texto(self, hint, texto="", input_filter=None):
        tf = MDTextField(
            text=str(texto),
            mode="outlined",
            size_hint_y=None,
            height=dp(68),
        )
        tf.add_widget(MDTextFieldHintText(text=hint))
        if input_filter:
            tf.input_filter = input_filter
        return tf

    def _campo_fecha(self, hint, texto=""):
        """Campo de fecha: MDTextField + botón de calendario."""
        fila = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(68),
            spacing=dp(4),
        )
        tf = MDTextField(
            text=str(texto),
            mode="outlined",
            size_hint_x=0.82,
            size_hint_y=None,
            height=dp(68),
        )
        tf.add_widget(MDTextFieldHintText(text=hint))

        btn_cal = MDIconButton(
            icon="calendar",
            size_hint_x=None,
            width=dp(48),
            size_hint_y=None,
            height=dp(48),
        )
        btn_cal.bind(on_release=lambda x, t=tf: self._abrir_picker(t))
        fila.add_widget(tf)
        fila.add_widget(btn_cal)
        return fila, tf      # retorna la fila y el tf para leer .text

    def _abrir_picker(self, tf):
        """Abre MDModalDatePicker y escribe la fecha seleccionada en tf."""
        picker = MDModalDatePicker()

        def _on_ok(instance):
            fechas = instance.get_date()
            if fechas:
                tf.text = fechas[0].strftime("%Y-%m-%d")

        picker.bind(on_ok=_on_ok)
        picker.open()

    def _cargar_opciones_form(self):
        """Carga las listas de materias primas y proveedores para los dropdowns."""
        conn = database.get_connection()
        mps = conn.execute(
            "SELECT id, nombre, unidad_medida FROM materias_primas WHERE activo=1 ORDER BY nombre"
        ).fetchall()
        provs = conn.execute(
            "SELECT id, nombre FROM proveedores WHERE activo=1 ORDER BY nombre"
        ).fetchall()
        conn.close()

        opc_mp   = [{"texto": f"{r['nombre']} ({r['unidad_medida']})", "valor": r["id"]} for r in mps]
        opc_prov = [{"texto": r["nombre"], "valor": r["id"]} for r in provs]
        return opc_mp, opc_prov

    # ── Formulario ────────────────────────────────────────────────────────────

    def _abrir_form(self, id_lote=None):
        self._id_editando = id_lote
        datos = {}

        if id_lote:
            conn = database.get_connection()
            row = conn.execute("""
                SELECT l.*, mp.nombre AS mp_nombre, mp.unidad_medida,
                       p.nombre AS prov_nombre
                FROM lotes l
                JOIN materias_primas mp ON mp.id = l.materia_prima_id
                LEFT JOIN proveedores p ON p.id = l.proveedor_id
                WHERE l.id=?
            """, (id_lote,)).fetchone()
            conn.close()
            if row:
                datos = dict(row)

        opc_mp, opc_prov = self._cargar_opciones_form()

        # Dropdowns
        self._dd_mp   = _DropdownCampo("Materia Prima *",  opc_mp)
        self._dd_prov = _DropdownCampo("Proveedor",        opc_prov)

        if datos.get("materia_prima_id") and datos.get("mp_nombre"):
            mp_txt = datos["mp_nombre"]
            if datos.get("unidad_medida"):
                mp_txt += f" ({datos['unidad_medida']})"
            self._dd_mp.set_valor(datos["materia_prima_id"], mp_txt)
        if datos.get("proveedor_id") and datos.get("prov_nombre"):
            self._dd_prov.set_valor(datos["proveedor_id"], datos["prov_nombre"])

        # Campos de texto
        self._tf_lote    = self._campo_texto("Número de lote *", datos.get("numero_lote", ""))
        fila_ing, self._tf_ingreso = self._campo_fecha(
            "Fecha de ingreso * (AAAA-MM-DD)",
            datos.get("fecha_ingreso", date.today().isoformat()),
        )
        fila_vence, self._tf_vence = self._campo_fecha(
            "Fecha de vencimiento (AAAA-MM-DD)",
            datos.get("fecha_vencimiento", "") or "",
        )
        self._tf_cantidad = self._campo_texto("Cantidad *",           datos.get("cantidad_inicial", ""), "float")
        self._tf_costo    = self._campo_texto("Costo unitario (₡) *", datos.get("costo_unitario", ""),   "float")

        # Label de costo total
        self._lbl_total = MDLabel(
            text="Total: ₡ —",
            theme_text_color="Custom",
            text_color=_CAFE,
            bold=True,
            size_hint_y=None,
            height=dp(32),
            halign="right",
        )
        self._tf_cantidad.bind(text=self._recalcular_total)
        self._tf_costo.bind(text=self._recalcular_total)
        self._recalcular_total()

        # Contenido del formulario
        contenido = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=[dp(8), dp(4), dp(8), dp(4)],
            adaptive_height=True,
        )
        for w in [self._dd_mp, self._dd_prov, self._tf_lote,
                  fila_ing, fila_vence,
                  self._tf_cantidad, self._tf_costo, self._lbl_total]:
            contenido.add_widget(w)

        scroll_form = MDScrollView(size_hint_y=None, height=Window.height * 0.55, do_scroll_x=False)
        scroll_form.add_widget(contenido)

        # Botones
        btns = MDDialogButtonContainer(spacing=dp(8))
        if id_lote:
            btn_elim = MDButton(
                MDButtonText(text="Eliminar"),
                style="text",
                on_release=lambda x: self._eliminar_desde_form(id_lote),
            )
            for w in btn_elim.children:
                if isinstance(w, MDButtonText):
                    w.theme_text_color = "Custom"
                    w.text_color = _ROJO
            btns.add_widget(btn_elim)

        btns.add_widget(MDButton(
            MDButtonText(text="Cancelar"),
            style="text",
            on_release=lambda x: self._dialog_form.dismiss(),
        ))
        btns.add_widget(MDButton(
            MDButtonText(text="Guardar"),
            style="text",
            on_release=lambda x: self._guardar(),
        ))

        titulo = "Editar Lote" if id_lote else "Nuevo Ingreso"
        self._dialog_form = MDDialog(
            MDDialogHeadlineText(text=titulo),
            MDDialogContentContainer(scroll_form),
            btns,
        )
        self._dialog_form.open()

    def _recalcular_total(self, *args):
        try:
            cantidad = float(self._tf_cantidad.text)
            costo    = float(self._tf_costo.text)
            total    = cantidad * costo
            self._lbl_total.text = f"Total: ₡ {total:,.2f}"
        except (ValueError, AttributeError):
            self._lbl_total.text = "Total: ₡ —"

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _guardar(self):
        mp_id   = self._dd_mp.valor
        prov_id = self._dd_prov.valor

        if mp_id is None:
            self.show_snack("Selecciona una materia prima")
            return

        numero_lote = self._tf_lote.text.strip()
        if not numero_lote:
            self.show_snack("El número de lote es obligatorio")
            return

        fecha_ing   = self._tf_ingreso.text.strip()
        fecha_vence = self._tf_vence.text.strip() or None

        if not fecha_ing:
            self.show_snack("La fecha de ingreso es obligatoria")
            return

        try:
            cantidad = float(self._tf_cantidad.text)
            costo    = float(self._tf_costo.text)
        except (ValueError, TypeError):
            self.show_snack("Cantidad y costo deben ser números")
            return

        if cantidad <= 0:
            self.show_snack("La cantidad debe ser mayor a 0")
            return
        if costo <= 0:
            self.show_snack("El costo unitario debe ser mayor a 0")
            return

        conn = database.get_connection()
        try:
            if self._id_editando:
                # En edición solo se actualizan datos no-financieros del lote
                # (no cambiamos cantidad_actual para no alterar el saldo)
                conn.execute("""
                    UPDATE lotes
                    SET numero_lote=?, fecha_ingreso=?, fecha_vencimiento=?,
                        costo_unitario=?, proveedor_id=?
                    WHERE id=?
                """, (numero_lote, fecha_ing, fecha_vence,
                      costo, prov_id, self._id_editando))
                msg = "Lote actualizado"
            else:
                # Nuevo lote: insertar y registrar movimiento de ingreso
                cur = conn.execute("""
                    INSERT INTO lotes
                        (numero_lote, fecha_ingreso, fecha_vencimiento,
                         cantidad_inicial, cantidad_actual, costo_unitario,
                         proveedor_id, materia_prima_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (numero_lote, fecha_ing, fecha_vence,
                      cantidad, cantidad, costo,
                      prov_id, mp_id))
                lote_id = cur.lastrowid
                conn.execute("""
                    INSERT INTO movimientos
                        (tipo, fecha, materia_prima_id, lote_id,
                         cantidad, costo_unitario, referencia)
                    VALUES ('ingreso', ?, ?, ?, ?, ?, ?)
                """, (fecha_ing, mp_id, lote_id, cantidad, costo,
                      f"Ingreso lote {numero_lote}"))
                msg = "Lote registrado"
            conn.commit()
        except Exception as e:
            self.show_snack(f"Error: {e}")
            return
        finally:
            conn.close()

        self._dialog_form.dismiss()
        self.show_snack(msg)
        self._cargar_lista()

    def _eliminar_desde_form(self, id_lote):
        self._dialog_form.dismiss()
        self.confirmar(
            "Desactivar lote",
            "¿Desactivar este lote? El stock registrado ya no estará disponible.",
            lambda: self._hacer_eliminar(id_lote),
        )

    def _confirmar_eliminar_ui(self, id_lote):
        """Eliminación desde botón de la lista (sin diálogo abierto)."""
        self.confirmar(
            "Desactivar lote",
            "¿Desactivar este lote?",
            lambda: self._hacer_eliminar(id_lote),
        )

    def _hacer_eliminar(self, id_lote):
        conn = database.get_connection()
        conn.execute("UPDATE lotes SET activo=0 WHERE id=?", (id_lote,))
        conn.commit()
        conn.close()
        self.show_snack("Lote desactivado")
        self._cargar_lista()
