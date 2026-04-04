"""
modulos/proveedores.py — Gestión completa de proveedores.
KivyMD 1.2.0 compatible.

Características:
- Lista con buscador en tiempo real
- Cada fila muestra nombre, teléfono y correo
- Botón editar (lápiz) y eliminar (papelera) por fila
- Formulario en MDDialog con 6 campos y validación inline
- Confirmación antes de eliminar
- Colores corporativos café #3E2723 / dorado #FFA000
"""

from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.uix.widget import Widget
from kivy.core.window import Window

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFloatingActionButton, MDFlatButton, MDIconButton
from kivy.clock import Clock
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog

import database
from modulos.base import PantallaBase, MDDivider

# ─── Paleta ───────────────────────────────────────────────────────────────────
_CAFE    = get_color_from_hex("#3E2723")
_DORADO  = get_color_from_hex("#FFA000")
_GRIS_BG = get_color_from_hex("#F5F5F5")
_BLANCO  = [1, 1, 1, 1]
_ROJO    = get_color_from_hex("#B71C1C")


# ─── Widget de fila individual ────────────────────────────────────────────────

class _FilaProveedor(MDBoxLayout):
    """
    Fila compacta: [avatar-inicial] [nombre / teléfono · RUC] [editar] [eliminar]
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

        nombre  = row_data["nombre"]
        tel     = row_data["telefono"] or "—"
        correo  = row_data["correo"]   or "—"
        ruc     = row_data["ruc_cedula"] or ""
        _id     = row_data["id"]

        # ── Avatar inicial ────────────────────────────────────────────────
        avatar = MDBoxLayout(
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            md_bg_color=_CAFE,
        )
        avatar.radius = [dp(20)]
        inicial = MDLabel(
            text=nombre[0].upper() if nombre else "?",
            halign="center",
            valign="middle",
            theme_text_color="Custom",
            text_color=_BLANCO,
            bold=True,
        )
        avatar.add_widget(inicial)

        # ── Textos ────────────────────────────────────────────────────────
        textos = MDBoxLayout(
            orientation="vertical",
            size_hint_x=1,
            padding=[dp(8), dp(4), 0, dp(4)],
        )
        lbl_nombre = MDLabel(
            text=nombre,
            font_style="Body1",
            bold=True,
            size_hint_y=None,
            height=dp(24),
            shorten=True,
            shorten_from="right",
        )
        detalle = f"Tel: {tel}"
        if ruc:
            detalle += f"  ·  RUC: {ruc}"
        lbl_detalle = MDLabel(
            text=detalle,
            font_style="Body2",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(20),
            shorten=True,
            shorten_from="right",
        )
        lbl_correo = MDLabel(
            text=correo,
            font_style="Body2",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(18),
            shorten=True,
            shorten_from="right",
        )
        textos.add_widget(lbl_nombre)
        textos.add_widget(lbl_detalle)
        textos.add_widget(lbl_correo)

        # ── Botones de acción ─────────────────────────────────────────────
        btn_editar = MDIconButton(
            icon="pencil-outline",
            theme_icon_color="Custom",
            icon_color=_CAFE,
        )
        btn_editar.bind(on_release=lambda x, i=_id: on_editar(i))

        btn_eliminar = MDIconButton(
            icon="delete-outline",
            theme_icon_color="Custom",
            icon_color=_ROJO,
        )
        btn_eliminar.bind(on_release=lambda x, i=_id: on_eliminar(i))

        self.add_widget(avatar)
        self.add_widget(textos)
        self.add_widget(btn_editar)
        self.add_widget(btn_eliminar)


# ─── Pantalla principal ───────────────────────────────────────────────────────

class Pantalla(PantallaBase):
    name            = "proveedores"
    titulo_pantalla = "Proveedores"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._id_editando = None
        self._dialog_form = None
        self._todos       = []
        self._construir_ui()

    # ── Construcción de la UI ─────────────────────────────────────────────────

    def _construir_ui(self):
        # Barra de búsqueda
        barra = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(64),
            padding=[dp(12), dp(8)],
            md_bg_color=_BLANCO,
        )
        self._tf_buscar = MDTextField(
            hint_text="Buscar por nombre…",
            size_hint_x=1,
        )
        self._tf_buscar.bind(text=lambda inst, val: self._filtrar(val))
        barra.add_widget(self._tf_buscar)
        self.layout_raiz.add_widget(barra)
        self.layout_raiz.add_widget(MDDivider())

        # Área de lista
        self._contenedor_lista = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            md_bg_color=_BLANCO,
            padding=[0, dp(8), 0, 0],
        )
        scroll = MDScrollView(do_scroll_x=False)
        scroll.add_widget(self._contenedor_lista)
        self.layout_raiz.add_widget(scroll)

        # FAB
        self._fab = MDFloatingActionButton(
            icon="plus",
            md_bg_color=_CAFE,
            pos_hint={"right": 0.97, "y": 0.03},
        )
        self._fab.bind(on_release=lambda x: self._abrir_form())
        self.add_widget(self._fab)
        Clock.schedule_once(self._aplicar_color_fab, 0)

    def _aplicar_color_fab(self, dt):
        self._fab.theme_icon_color = "Custom"
        self._fab.icon_color = _DORADO

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def on_pre_enter(self, *args):
        self._tf_buscar.text = ""
        self._cargar_datos()

    # ── Carga y filtro ────────────────────────────────────────────────────────

    def _cargar_datos(self):
        conn = database.get_connection()
        rows = conn.execute("""
            SELECT id, nombre, ruc_cedula, telefono, correo, direccion, condiciones_pago
            FROM   proveedores
            WHERE  activo = 1
            ORDER  BY nombre COLLATE NOCASE
        """).fetchall()
        conn.close()
        self._todos = [dict(r) for r in rows]
        self._renderizar(self._todos)

    def _filtrar(self, texto):
        texto = texto.strip().lower()
        if not texto:
            self._renderizar(self._todos)
            return
        self._renderizar([r for r in self._todos if texto in r["nombre"].lower()])

    def _renderizar(self, rows):
        self._contenedor_lista.clear_widgets()

        if not rows:
            vacio = MDBoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(200),
                padding=[dp(16), dp(32)],
                spacing=dp(12),
            )
            vacio.add_widget(MDLabel(
                text="No hay proveedores registrados",
                halign="center",
                font_style="H6",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(40),
            ))
            vacio.add_widget(MDLabel(
                text='Toca el botón "+" para agregar el primero',
                halign="center",
                font_style="Body2",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(30),
            ))
            self._contenedor_lista.add_widget(vacio)
            return

        for i, row in enumerate(rows):
            fila = _FilaProveedor(
                row_data=row,
                on_editar=self._abrir_form,
                on_eliminar=self._pedir_confirmar_eliminar,
            )
            if i % 2 == 1:
                fila.md_bg_color = _GRIS_BG
            self._contenedor_lista.add_widget(fila)
            self._contenedor_lista.add_widget(MDDivider())

    # ── Formulario ────────────────────────────────────────────────────────────

    def _construir_campo(self, hint: str, texto: str = "",
                         teclado: str = "normal",
                         error_msg: str = "") -> MDTextField:
        tf = MDTextField(
            text=texto,
            hint_text=hint,
            helper_text=error_msg,
            size_hint_y=None,
            height=dp(68),
        )
        if teclado != "normal":
            tf.input_type = teclado
        return tf

    def _abrir_form(self, id_prov=None):
        self._id_editando = id_prov
        datos = {}
        if id_prov:
            conn = database.get_connection()
            row = conn.execute(
                "SELECT * FROM proveedores WHERE id=?", (id_prov,)
            ).fetchone()
            conn.close()
            if row:
                datos = dict(row)

        self._tf_nombre    = self._construir_campo(
            "Nombre *", datos.get("nombre", ""), error_msg="El nombre es obligatorio"
        )
        self._tf_ruc       = self._construir_campo("RUC / Cédula jurídica",  datos.get("ruc_cedula", "") or "")
        self._tf_telefono  = self._construir_campo("Teléfono",               datos.get("telefono", "") or "", teclado="tel")
        self._tf_correo    = self._construir_campo("Correo electrónico",     datos.get("correo", "") or "", teclado="mail")
        self._tf_direccion = self._construir_campo("Dirección",              datos.get("direccion", "") or "")
        self._tf_condpago  = self._construir_campo("Condiciones de pago",    datos.get("condiciones_pago", "") or "")

        inner = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[dp(4), dp(8), dp(4), dp(8)],
            adaptive_height=True,
        )
        for tf in [self._tf_nombre, self._tf_ruc, self._tf_telefono,
                   self._tf_correo, self._tf_direccion, self._tf_condpago]:
            inner.add_widget(tf)

        scroll_form = MDScrollView(
            size_hint_y=None,
            height=Window.height * 0.55,
            do_scroll_x=False,
        )
        scroll_form.add_widget(inner)

        buttons = []
        if id_prov:
            btn_del = MDFlatButton(
                text="Eliminar",
                theme_text_color="Custom",
                text_color=_ROJO,
                on_release=lambda x: self._desde_form_eliminar(id_prov),
            )
            buttons.append(btn_del)

        buttons.append(MDFlatButton(
            text="Cancelar",
            on_release=lambda x: self._dialog_form.dismiss(),
        ))
        buttons.append(MDFlatButton(
            text="Guardar",
            theme_text_color="Custom",
            text_color=_CAFE,
            on_release=lambda x: self._guardar(),
        ))

        titulo = "Editar proveedor" if id_prov else "Nuevo proveedor"
        self._dialog_form = MDDialog(
            title=titulo,
            type="custom",
            content_cls=scroll_form,
            buttons=buttons,
        )
        self._dialog_form.open()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _guardar(self):
        nombre = self._tf_nombre.text.strip()
        if not nombre:
            self.show_snack("El nombre del proveedor es obligatorio")
            return

        datos = (
            nombre,
            self._tf_ruc.text.strip()       or None,
            self._tf_telefono.text.strip()  or None,
            self._tf_correo.text.strip()    or None,
            self._tf_direccion.text.strip() or None,
            self._tf_condpago.text.strip()  or None,
        )

        conn = database.get_connection()
        try:
            if self._id_editando:
                conn.execute("""
                    UPDATE proveedores
                       SET nombre=?, ruc_cedula=?, telefono=?, correo=?,
                           direccion=?, condiciones_pago=?
                     WHERE id=?
                """, datos + (self._id_editando,))
                msg = "✓ Proveedor actualizado"
            else:
                conn.execute("""
                    INSERT INTO proveedores
                        (nombre, ruc_cedula, telefono, correo, direccion, condiciones_pago)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, datos)
                msg = "✓ Proveedor registrado"
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

    def _desde_form_eliminar(self, id_prov):
        self._dialog_form.dismiss()
        self._pedir_confirmar_eliminar(id_prov)

    def _pedir_confirmar_eliminar(self, id_prov):
        conn = database.get_connection()
        row = conn.execute(
            "SELECT nombre FROM proveedores WHERE id=?", (id_prov,)
        ).fetchone()
        conn.close()
        nombre = row["nombre"] if row else "este proveedor"

        self.confirmar(
            "Eliminar proveedor",
            f'¿Está seguro que desea eliminar a "{nombre}"?\n\nEsta acción no se puede deshacer.',
            lambda: self._confirmar_eliminar(id_prov),
        )

    def _confirmar_eliminar(self, id_prov):
        conn = database.get_connection()
        conn.execute("UPDATE proveedores SET activo=0 WHERE id=?", (id_prov,))
        conn.commit()
        conn.close()
        self.show_snack("Proveedor eliminado")
        self._cargar_datos()
