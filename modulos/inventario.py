"""
modulos/inventario.py — Inventario actual por materia prima (solo lectura).
KivyMD 1.2.0 compatible.
"""

from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.uix.widget import Widget

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu

from datetime import date, timedelta

import database
from modulos.base import PantallaBase, MDDivider

# ─── Paleta ───────────────────────────────────────────────────────────────────
_CAFE     = get_color_from_hex("#3E2723")
_DORADO   = get_color_from_hex("#FFA000")
_BLANCO   = [1, 1, 1, 1]
_VERDE    = get_color_from_hex("#1B5E20")
_VERDE_BG = get_color_from_hex("#E8F5E9")
_AMARILLO = get_color_from_hex("#E65100")
_AMAR_BG  = get_color_from_hex("#FFF3E0")
_ROJO     = get_color_from_hex("#B71C1C")
_ROJO_BG  = get_color_from_hex("#FFEBEE")
_GRIS     = get_color_from_hex("#757575")
_GRIS_BG  = get_color_from_hex("#F5F5F5")


def _semaforo(stock: float, minimo: float):
    if stock <= 0:
        return "🔴", _ROJO, _ROJO_BG, "Sin stock"
    if minimo > 0:
        if stock < minimo:
            return "🔴", _ROJO, _ROJO_BG, "Bajo mínimo"
        if stock < minimo * 2:
            return "🟡", _AMARILLO, _AMAR_BG, "Stock bajo"
    return "🟢", _VERDE, _VERDE_BG, "Abastecido"


# ─── Widget de fila individual ────────────────────────────────────────────────

class _FilaInventario(MDBoxLayout):
    def __init__(self, row: dict, on_detalle, **kwargs):
        nombre   = row["nombre"]
        unidad   = row["unidad_medida"]
        stock    = float(row["stock"])
        minimo   = float(row["stock_minimo"])
        valor    = float(row["valor_total"])
        n_lotes  = int(row["n_lotes"])
        categoria = row["categoria"] or "Sin categoría"

        emoji, color_txt, color_bg, desc = _semaforo(stock, minimo)

        super().__init__(
            orientation="horizontal",
            size_hint_y=None, height=dp(88),
            padding=[dp(6), dp(6), dp(6), dp(6)],
            spacing=dp(6), md_bg_color=color_bg, **kwargs,
        )

        barra_lateral = MDBoxLayout(size_hint=(None, 1), width=dp(6), md_bg_color=color_txt)
        barra_lateral.radius = [dp(3)]

        avatar = MDBoxLayout(size_hint=(None, None), size=(dp(42), dp(42)), md_bg_color=_CAFE)
        avatar.radius = [dp(21)]
        avatar.add_widget(MDLabel(
            text=nombre[0].upper() if nombre else "?",
            halign="center", valign="middle",
            theme_text_color="Custom", text_color=_BLANCO, bold=True,
        ))

        info = MDBoxLayout(orientation="vertical", size_hint_x=1, spacing=dp(1))
        info.add_widget(MDLabel(
            text=nombre, font_style="Body1", bold=True,
            size_hint_y=None, height=dp(22),
            shorten=True, shorten_from="right",
        ))
        info.add_widget(MDLabel(
            text=f"{categoria}  ·  Mín: {minimo:g} {unidad}",
            font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(18),
        ))
        lbl_stock = MDLabel(
            text=f"Stock: {stock:,.3f} {unidad}",
            font_style="Body1", bold=True,
            theme_text_color="Custom", text_color=color_txt,
            size_hint_y=None, height=dp(20),
        )
        info.add_widget(lbl_stock)
        info.add_widget(MDLabel(
            text=f"Valor: ₡{valor:,.2f}  ·  {n_lotes} lote{'s' if n_lotes != 1 else ''} activo{'s' if n_lotes != 1 else ''}",
            font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(18),
        ))

        lado_der = MDBoxLayout(orientation="vertical", size_hint=(None, 1), width=dp(44), spacing=dp(2))
        lbl_emoji = MDLabel(
            text=emoji, halign="center", font_size="24sp",
            size_hint_y=None, height=dp(32),
        )
        btn_info = MDIconButton(icon="information-outline", size_hint_y=None, height=dp(36))
        btn_info.bind(on_release=lambda x: on_detalle())
        lado_der.add_widget(lbl_emoji)
        lado_der.add_widget(btn_info)

        self.add_widget(barra_lateral)
        self.add_widget(avatar)
        self.add_widget(info)
        self.add_widget(lado_der)


# ─── Pantalla principal ───────────────────────────────────────────────────────

class Pantalla(PantallaBase):
    name = "inventario"
    titulo_pantalla = "Inventario Actual"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._todos           = []
        self._filtro_cat      = None
        self._filtro_cat_txt  = "Todas las categorías"
        self._menu_cat        = None
        self._dialog_detalle  = None
        self._construir_ui()

    def _construir_ui(self):
        # Botón Actualizar en la barra superior (usando right_action_items)
        self.toolbar.right_action_items = [
            ["refresh", lambda x: self._cargar_datos()]
        ]

        controles = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None, height=dp(124),
            padding=[dp(8), dp(4), dp(8), dp(4)], spacing=dp(4),
        )

        fila1 = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(52), spacing=dp(8))
        self._btn_cat = MDFlatButton(
            text="Todas las categorías",
            theme_text_color="Custom", text_color=_CAFE,
        )
        self._btn_cat.bind(on_release=lambda x: self._abrir_filtro_cat())
        fila1.add_widget(self._btn_cat)

        fila2 = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(68))
        self._tf_buscar = MDTextField(
            hint_text="Buscar materia prima…",
            mode="rectangle", size_hint_x=1, size_hint_y=None, height=dp(64),
        )
        self._tf_buscar.bind(text=lambda inst, val: self._aplicar_filtros())
        fila2.add_widget(self._tf_buscar)

        controles.add_widget(fila1)
        controles.add_widget(fila2)
        self.layout_raiz.add_widget(controles)

        self._contenedor = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=0)
        scroll = MDScrollView()
        scroll.add_widget(self._contenedor)
        self.layout_raiz.add_widget(scroll)

        self._footer = MDBoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(52),
            padding=[dp(12), dp(4)], spacing=dp(4), md_bg_color=_CAFE,
        )
        self._lbl_total_items = MDLabel(
            text="— items", halign="center",
            theme_text_color="Custom", text_color=_BLANCO,
            font_style="Body1", bold=True,
        )
        self._lbl_valor_total = MDLabel(
            text="₡ —", halign="center",
            theme_text_color="Custom", text_color=_DORADO,
            font_style="Body1", bold=True,
        )
        self._lbl_alertas = MDLabel(
            text="— alertas", halign="center",
            theme_text_color="Custom", text_color=_BLANCO,
            font_style="Body1",
        )
        self._footer.add_widget(self._lbl_total_items)
        self._footer.add_widget(MDDivider(orientation="vertical"))
        self._footer.add_widget(self._lbl_valor_total)
        self._footer.add_widget(MDDivider(orientation="vertical"))
        self._footer.add_widget(self._lbl_alertas)
        self.layout_raiz.add_widget(self._footer)

    def on_pre_enter(self, *args):
        self._cargar_datos()

    def _abrir_filtro_cat(self):
        conn = database.get_connection()
        cats = conn.execute("""
            SELECT DISTINCT categoria FROM materias_primas
            WHERE activo=1 AND categoria IS NOT NULL ORDER BY categoria
        """).fetchall()
        conn.close()

        items = [{"viewclass": "OneLineListItem", "text": "Todas las categorías",
                  "on_release": lambda: self._set_cat(None, "Todas las categorías")}]
        for r in cats:
            cat = r["categoria"]
            items.append({
                "viewclass": "OneLineListItem",
                "text": cat,
                "on_release": (lambda c: lambda: self._set_cat(c, c))(cat),
            })

        if self._menu_cat:
            self._menu_cat.dismiss()
        self._menu_cat = MDDropdownMenu(caller=self._btn_cat, items=items, width_mult=5)
        self._menu_cat.open()

    def _set_cat(self, cat, texto):
        self._filtro_cat = cat
        self._btn_cat.text = texto
        if self._menu_cat:
            self._menu_cat.dismiss()
        self._aplicar_filtros()

    def _cargar_datos(self):
        conn = database.get_connection()
        rows = conn.execute("""
            SELECT mp.id, mp.nombre, mp.descripcion, mp.unidad_medida, mp.stock_minimo,
                   mp.categoria, mp.proveedor_id, p.nombre AS proveedor_nombre,
                   COALESCE(SUM(l.cantidad_actual), 0)                    AS stock,
                   COALESCE(SUM(l.cantidad_actual * l.costo_unitario), 0) AS valor_total,
                   COUNT(CASE WHEN l.id IS NOT NULL AND l.activo=1 THEN 1 END) AS n_lotes
            FROM materias_primas mp
            LEFT JOIN lotes l ON l.materia_prima_id = mp.id AND l.activo = 1
            LEFT JOIN proveedores p ON p.id = mp.proveedor_id
            WHERE mp.activo = 1
            GROUP BY mp.id ORDER BY mp.nombre
        """).fetchall()
        conn.close()
        self._todos = [dict(r) for r in rows]
        self._aplicar_filtros()

    def _aplicar_filtros(self):
        texto = self._tf_buscar.text.lower().strip() if hasattr(self, "_tf_buscar") else ""
        cat   = self._filtro_cat

        filtrado = self._todos
        if cat:
            filtrado = [r for r in filtrado if r["categoria"] == cat]
        if texto:
            filtrado = [r for r in filtrado if texto in r["nombre"].lower()]
        self._renderizar(filtrado)

    def _renderizar(self, rows):
        self._contenedor.clear_widgets()

        if not rows:
            self._contenedor.add_widget(Widget(size_hint_y=None, height=dp(60)))
            self._contenedor.add_widget(MDLabel(
                text="Sin materias primas en inventario",
                halign="center", theme_text_color="Hint",
                size_hint_y=None, height=dp(40),
            ))
            self._actualizar_footer([])
            return

        for row in rows:
            fila = _FilaInventario(row=row, on_detalle=lambda r=row: self._abrir_detalle(r))
            self._contenedor.add_widget(fila)
            self._contenedor.add_widget(MDDivider())
        self._actualizar_footer(rows)

    def _actualizar_footer(self, rows):
        total_items = len(rows)
        valor_total = sum(float(r["valor_total"]) for r in rows)
        n_alertas   = sum(
            1 for r in rows
            if float(r["stock"]) <= 0
            or (float(r["stock_minimo"]) > 0 and float(r["stock"]) < float(r["stock_minimo"]))
        )
        self._lbl_total_items.text = f"{total_items} items"
        self._lbl_valor_total.text = f"₡{valor_total:,.0f}"
        self._lbl_alertas.text     = f"{n_alertas} {'alerta' if n_alertas == 1 else 'alertas'}"

    def _abrir_detalle(self, row: dict):
        if self._dialog_detalle:
            self._dialog_detalle.dismiss()

        mp_id   = row["id"]
        nombre  = row["nombre"]
        unidad  = row["unidad_medida"]
        stock   = float(row["stock"])
        minimo  = float(row["stock_minimo"])
        valor   = float(row["valor_total"])
        cat     = row["categoria"] or "—"
        desc    = row["descripcion"] or "—"
        prov    = row["proveedor_nombre"] or "—"
        emoji, color_txt, _, desc_semaforo = _semaforo(stock, minimo)

        conn = database.get_connection()
        lotes = conn.execute("""
            SELECT l.numero_lote, l.fecha_ingreso, l.fecha_vencimiento,
                   l.cantidad_actual, l.costo_unitario, p.nombre AS proveedor
            FROM lotes l
            LEFT JOIN proveedores p ON p.id = l.proveedor_id
            WHERE l.materia_prima_id=? AND l.activo=1 AND l.cantidad_actual>0
            ORDER BY l.fecha_ingreso ASC, l.id ASC
        """, (mp_id,)).fetchall()
        conn.close()

        hoy   = date.today().isoformat()
        lim30 = (date.today() + timedelta(days=30)).isoformat()

        contenido = MDBoxLayout(
            orientation="vertical", adaptive_height=True,
            spacing=dp(4), padding=[dp(4), dp(0), dp(4), dp(8)],
        )

        def _fila_info(etiqueta, valor_txt, color=None):
            fila = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(8))
            fila.add_widget(MDLabel(
                text=etiqueta, size_hint_x=0.38, font_style="Body2",
                bold=True, theme_text_color="Secondary",
            ))
            lbl = MDLabel(text=valor_txt, size_hint_x=0.62, font_style="Body2")
            if color:
                lbl.theme_text_color = "Custom"
                lbl.text_color = color
            fila.add_widget(lbl)
            return fila

        contenido.add_widget(_fila_info("Categoría:", cat))
        contenido.add_widget(_fila_info("Descripción:", desc))
        contenido.add_widget(_fila_info("Unidad:", unidad))
        contenido.add_widget(_fila_info("Stock mínimo:", f"{minimo:g} {unidad}"))
        contenido.add_widget(_fila_info("Proveedor pref.:", prov))
        contenido.add_widget(_fila_info("Stock actual:", f"{stock:,.3f} {unidad}  {emoji} {desc_semaforo}", color=color_txt))
        contenido.add_widget(_fila_info("Valor en inv.:", f"₡{valor:,.2f}"))
        contenido.add_widget(MDDivider())
        contenido.add_widget(MDLabel(
            text=f"Lotes activos — orden PEPS ({len(lotes)} lote{'s' if len(lotes) != 1 else ''})",
            font_style="Body1", bold=True,
            size_hint_y=None, height=dp(32),
            theme_text_color="Custom", text_color=_CAFE,
        ))

        if not lotes:
            contenido.add_widget(MDLabel(
                text="Sin lotes con stock disponible",
                theme_text_color="Hint", size_hint_y=None, height=dp(28), halign="center",
            ))
        else:
            for idx, lote in enumerate(lotes):
                vence = lote["fecha_vencimiento"] or ""
                if not vence:
                    color_v = _GRIS; txt_v = "Sin vencimiento"
                elif vence < hoy:
                    color_v = _ROJO; txt_v = f"VENCIDO {vence}"
                elif vence <= lim30:
                    color_v = _AMARILLO; txt_v = f"Vence pronto {vence}"
                else:
                    color_v = _VERDE; txt_v = f"Vence {vence}"

                peps_tag = "⚑ PEPS  " if idx == 0 else f"#{idx+1}  "
                bloque = MDBoxLayout(
                    orientation="vertical", adaptive_height=True,
                    padding=[dp(8), dp(4), dp(4), dp(4)],
                    md_bg_color=_GRIS_BG if idx % 2 == 0 else _BLANCO,
                )
                bloque.radius = [dp(4)]
                bloque.add_widget(MDLabel(
                    text=f"{peps_tag}Lote: {lote['numero_lote']}  ·  Ingreso: {lote['fecha_ingreso']}",
                    font_style="Body1", bold=(idx == 0),
                    size_hint_y=None, height=dp(22),
                ))
                bloque.add_widget(MDLabel(
                    text=f"Cant: {lote['cantidad_actual']:,.3f} {unidad}  ·  ₡{lote['costo_unitario']:,.2f}/u",
                    font_style="Body2", theme_text_color="Secondary",
                    size_hint_y=None, height=dp(18),
                ))
                lbl_v = MDLabel(
                    text=txt_v, font_style="Body2",
                    theme_text_color="Custom", text_color=color_v,
                    size_hint_y=None, height=dp(18),
                )
                bloque.add_widget(lbl_v)
                contenido.add_widget(bloque)

        scroll_det = MDScrollView(size_hint_y=None, height=dp(400))
        scroll_det.add_widget(contenido)

        self._dialog_detalle = MDDialog(
            title=nombre,
            type="custom",
            content_cls=scroll_det,
            buttons=[
                MDFlatButton(
                    text="Cerrar",
                    on_release=lambda x: self._dialog_detalle.dismiss(),
                ),
            ],
        )
        self._dialog_detalle.open()
