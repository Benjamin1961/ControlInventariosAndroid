"""
modulos/reportes.py — Centro de reportes completo.

6 reportes con tarjetas de menú, filtros, tablas con filas alternas,
semáforos de estado y exportación de texto (share en Android,
MDDialog en escritorio).

Reportes disponibles:
  1. Inventario Actual          — stock + valor por materia prima
  2. Vencimientos               — vencidos (rojo) y próximos 30 días (naranja)
  3. Movimientos                — entradas/salidas con DatePicker desde/hasta
  4. Costos por Receta          — costo/porción + semáforo de rentabilidad
  5. Productos Terminados       — stock, precios y vencimientos
  6. Proyección de Compras      — consumo histórico y días estimados hasta agotamiento
"""

from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.divider import MDDivider
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.textfield.textfield import MDTextFieldHintText
from kivymd.uix.dialog import (
    MDDialog, MDDialogHeadlineText,
    MDDialogButtonContainer, MDDialogContentContainer,
)
from kivymd.uix.card import MDCard
from kivymd.uix.pickers import MDModalDatePicker
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText

from datetime import date, datetime, timedelta
from pathlib import Path
import os
import subprocess as _subproc

import database
from modulos.base import PantallaBase

# ─── Paleta ───────────────────────────────────────────────────────────────────
_CAFE    = get_color_from_hex("#3E2723")
_DORADO  = get_color_from_hex("#FFA000")
_GRIS    = get_color_from_hex("#F5F5F5")
_BLANCO  = [1, 1, 1, 1]
_ROJO    = get_color_from_hex("#B71C1C")
_VERDE   = get_color_from_hex("#1B5E20")
_NARANJA = get_color_from_hex("#E65100")
_BORDE   = get_color_from_hex("#BDBDBD")

_ROJO_FONDO   = get_color_from_hex("#FFCDD2")
_NARANJA_FONDO= get_color_from_hex("#FFE0B2")
_VERDE_FONDO  = get_color_from_hex("#C8E6C9")

# ─── Detección de Android ─────────────────────────────────────────────────────
try:
    from android.content import Intent           # type: ignore
    from android import mActivity                # type: ignore
    _ANDROID = True
except ImportError:
    _ANDROID = False

# ─── ReportLab (exportación PDF) ──────────────────────────────────────────────
_REPORTLAB = False
_FUENTE    = "Helvetica"
_FUENTE_B  = "Helvetica-Bold"
try:
    from reportlab.lib import colors as _rl_colors
    from reportlab.lib.pagesizes import A4, landscape as _rl_landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm as _cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.pdfbase import pdfmetrics as _pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont as _TTFont
    _REPORTLAB = True

    # Intentar fuente Unicode para el símbolo ₡ (U+20A1)
    for _ttf in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if os.path.exists(_ttf):
            try:
                _pdfmetrics.registerFont(_TTFont("_PanFont", _ttf))
                _ttf_b = (_ttf.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
                              .replace("LiberationSans-Regular.ttf",
                                       "LiberationSans-Bold.ttf"))
                if os.path.exists(_ttf_b):
                    _pdfmetrics.registerFont(_TTFont("_PanFontB", _ttf_b))
                    _FUENTE_B = "_PanFontB"
                else:
                    _FUENTE_B = "_PanFont"
                _FUENTE = "_PanFont"
                break
            except Exception:
                pass
except ImportError:
    pass

# ─── Definición del menú ─────────────────────────────────────────────────────
_MENU = [
    ("inventario",  "📦", "Inventario Actual",
     "Stock y valor de todas las materias primas"),
    ("vencimientos","⚠️", "Vencimientos",
     "Lotes vencidos y próximos a vencer (30 días)"),
    ("movimientos", "📊", "Movimientos",
     "Entradas y salidas por período seleccionado"),
    ("costos",      "💰", "Costos por Receta",
     "Costo/porción y semáforo de rentabilidad"),
    ("productos",   "🎁", "Productos Terminados",
     "Stock, precios de venta y vencimientos"),
    ("proyeccion",  "🛒", "Proyección de Compras",
     "Días hasta agotamiento y cantidad sugerida"),
]


# ─── Helpers de UI ───────────────────────────────────────────────────────────

def _fila_tabla(cols: list, bg=None, negrita=False):
    """Fila de tabla genérica: lista de (texto, size_hint_x)."""
    fila = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(44),
        padding=[dp(8), dp(4), dp(8), dp(4)],
        spacing=dp(4),
    )
    if bg:
        fila.md_bg_color = bg
    for texto, sx in cols:
        lbl = MDLabel(
            text=str(texto),
            size_hint_x=sx,
            valign="middle",
            font_style="Body",
            role="small" if not negrita else "medium",
            bold=negrita,
            shorten=True,
            shorten_from="right",
        )
        fila.add_widget(lbl)
    return fila


def _seccion_titulo(texto: str, color=None):
    """Encabezado de sección dentro de un reporte."""
    box = MDBoxLayout(
        size_hint_y=None,
        height=dp(36),
        padding=[dp(12), dp(4)],
        md_bg_color=color or _CAFE,
    )
    box.add_widget(MDLabel(
        text=texto,
        bold=True,
        theme_text_color="Custom",
        text_color=_BLANCO,
        valign="middle",
    ))
    return box


def _pie_totales(texto: str):
    """Barra de pie con totales."""
    box = MDBoxLayout(
        size_hint_y=None,
        height=dp(40),
        padding=[dp(16), dp(4)],
        md_bg_color=_CAFE,
    )
    box.add_widget(MDLabel(
        text=texto,
        bold=True,
        theme_text_color="Custom",
        text_color=_DORADO,
        valign="middle",
    ))
    return box


# ─── Pantalla principal ───────────────────────────────────────────────────────

class Pantalla(PantallaBase):
    name            = "reportes"
    titulo_pantalla = "Reportes"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._reporte_activo = None
        self._fecha_desde    = (date.today() - timedelta(days=30)).isoformat()
        self._fecha_hasta    = date.today().isoformat()
        self._dias_proyeccion = 30
        self._dialogo_export  = None

        # Área de contenido reemplazable
        self._area = MDBoxLayout(orientation="vertical")
        self.layout_raiz.add_widget(self._area)
        # No cargamos datos aquí para evitar AttributeError en main.py

    def on_pre_enter(self, *args):
        self._mostrar_menu()

    # ─── MENÚ ────────────────────────────────────────────────────────────────

    def _mostrar_menu(self):
        self._reporte_activo = None
        self._area.clear_widgets()

        scroll = MDScrollView(do_scroll_x=False)
        cuerpo = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=[dp(12), dp(12), dp(12), dp(80)],
            spacing=dp(10),
        )

        for tipo, emoji, titulo, desc in _MENU:
            card = self._crear_tarjeta(tipo, emoji, titulo, desc)
            cuerpo.add_widget(card)

        scroll.add_widget(cuerpo)
        self._area.add_widget(scroll)

    def _crear_tarjeta(self, tipo, emoji, titulo, desc):
        card = MDCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(80),
            padding=[dp(12), dp(8), dp(12), dp(8)],
            spacing=dp(12),
            style="elevated",
            md_bg_color=_BLANCO,
        )

        # Ícono en caja café
        caja_icon = MDBoxLayout(
            size_hint=(None, None),
            size=(dp(52), dp(52)),
            md_bg_color=_CAFE,
        )
        caja_icon.radius = [dp(8)]
        caja_icon.add_widget(MDLabel(
            text=emoji,
            halign="center",
            valign="middle",
            font_size="26sp",
        ))

        # Textos
        textos = MDBoxLayout(orientation="vertical", size_hint_x=1)
        textos.add_widget(MDLabel(
            text=titulo,
            bold=True,
            font_style="Body",
            role="large",
            size_hint_y=None,
            height=dp(26),
            shorten=True,
            shorten_from="right",
        ))
        textos.add_widget(MDLabel(
            text=desc,
            font_style="Body",
            role="small",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(22),
            shorten=True,
            shorten_from="right",
        ))

        # Flecha
        card.add_widget(caja_icon)
        card.add_widget(textos)
        card.add_widget(MDIcon(
            icon="chevron-right",
            theme_text_color="Secondary",
            size_hint=(None, None),
            size=(dp(24), dp(24)),
        ))

        card.bind(on_release=lambda x, t=tipo: self._abrir_reporte(t))
        return card

    # ─── ENCABEZADO DE REPORTE ────────────────────────────────────────────────

    def _abrir_reporte(self, tipo):
        self._reporte_activo = tipo
        self._area.clear_widgets()

        titulos = {
            "inventario":  "📦 Inventario Actual",
            "vencimientos":"⚠️ Vencimientos",
            "movimientos": "📊 Movimientos",
            "costos":      "💰 Costos por Receta",
            "productos":   "🎁 Productos Terminados",
            "proyeccion":  "🛒 Proyección de Compras",
        }

        # Barra de navegación del reporte
        barra = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(52),
            padding=[dp(4), dp(4), dp(8), dp(4)],
            spacing=dp(4),
            md_bg_color=_CAFE,
        )
        btn_back = MDIconButton(
            icon="arrow-left",
            theme_icon_color="Custom",
            icon_color=_BLANCO,
        )
        btn_back.bind(on_release=lambda x: self._mostrar_menu())

        barra.add_widget(btn_back)
        barra.add_widget(MDLabel(
            text=titulos.get(tipo, tipo),
            bold=True,
            theme_text_color="Custom",
            text_color=_BLANCO,
            size_hint_x=1,
            valign="middle",
            font_style="Body",
            role="large",
        ))

        self._btn_exportar = MDIconButton(
            icon="share-variant-outline",
            theme_icon_color="Custom",
            icon_color=_DORADO,
        )
        self._btn_exportar.bind(on_release=lambda x: self._exportar_reporte())
        barra.add_widget(self._btn_exportar)

        self._btn_pdf = MDIconButton(
            icon="file-pdf-box",
            theme_icon_color="Custom",
            icon_color=_DORADO,
        )
        self._btn_pdf.bind(on_release=lambda x: self._exportar_pdf())
        barra.add_widget(self._btn_pdf)
        self._area.add_widget(barra)

        # Área de filtros + datos
        self._panel = MDBoxLayout(orientation="vertical")
        self._area.add_widget(self._panel)

        # Renderizar el reporte correspondiente
        {
            "inventario":   self._render_inventario,
            "vencimientos": self._render_vencimientos,
            "movimientos":  self._render_movimientos,
            "costos":       self._render_costos,
            "productos":    self._render_productos,
            "proyeccion":   self._render_proyeccion,
        }[tipo]()

    def _scroll_datos(self):
        """Scroll reutilizable para la sección de datos."""
        sv = MDScrollView(do_scroll_x=False)
        cuerpo = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
        )
        sv.add_widget(cuerpo)
        self._panel.add_widget(sv)
        return cuerpo

    # ─── 1. INVENTARIO ACTUAL ─────────────────────────────────────────────────

    def _render_inventario(self):
        conn = database.get_connection()
        rows = conn.execute("""
            SELECT mp.nombre, mp.categoria, mp.unidad_medida, mp.stock_minimo,
                   COALESCE(SUM(l.cantidad_actual), 0)                     AS stock,
                   COALESCE(SUM(l.cantidad_actual * l.costo_unitario), 0)  AS valor
            FROM   materias_primas mp
            LEFT   JOIN lotes l ON l.materia_prima_id = mp.id AND l.activo = 1
            WHERE  mp.activo = 1
            GROUP  BY mp.id
            ORDER  BY mp.nombre COLLATE NOCASE
        """).fetchall()
        conn.close()

        self._datos_export = rows
        cuerpo = self._scroll_datos()

        # Encabezado columnas
        cuerpo.add_widget(_fila_tabla(
            [("Materia Prima", 0.40), ("Cat.", 0.18),
             ("Stock", 0.22), ("Valor ₡", 0.20)],
            bg=_CAFE, negrita=True,
        ))

        total_valor = 0.0
        for i, r in enumerate(rows):
            stock  = float(r["stock"])
            minimo = float(r["stock_minimo"] or 0)
            valor  = float(r["valor"])
            total_valor += valor

            if stock <= 0:
                bg = _ROJO_FONDO
            elif stock < minimo:
                bg = _NARANJA_FONDO
            else:
                bg = _GRIS if i % 2 == 0 else _BLANCO

            stk_s = f"{stock:,.2f} {r['unidad_medida']}"
            cuerpo.add_widget(_fila_tabla(
                [(r["nombre"], 0.40), (r["categoria"] or "—", 0.18),
                 (stk_s, 0.22), (f"₡{valor:,.0f}", 0.20)],
                bg=bg,
            ))
            cuerpo.add_widget(MDDivider())

        cuerpo.add_widget(_pie_totales(
            f"{len(rows)} materias primas  ·  Valor total: ₡{total_valor:,.2f}"
        ))

    # ─── 2. VENCIMIENTOS ─────────────────────────────────────────────────────

    def _render_vencimientos(self):
        hoy   = date.today().isoformat()
        lim30 = (date.today() + timedelta(days=30)).isoformat()

        conn = database.get_connection()
        vencidos = conn.execute("""
            SELECT l.numero_lote, l.fecha_vencimiento, l.cantidad_actual,
                   mp.nombre, mp.unidad_medida,
                   CAST(julianday('now') - julianday(l.fecha_vencimiento) AS INTEGER) AS dias
            FROM   lotes l
            JOIN   materias_primas mp ON mp.id = l.materia_prima_id
            WHERE  l.activo = 1 AND l.cantidad_actual > 0
              AND  l.fecha_vencimiento < date('now')
            ORDER  BY l.fecha_vencimiento ASC
        """).fetchall()
        proximos = conn.execute("""
            SELECT l.numero_lote, l.fecha_vencimiento, l.cantidad_actual,
                   mp.nombre, mp.unidad_medida,
                   CAST(julianday(l.fecha_vencimiento) - julianday('now') AS INTEGER) AS dias
            FROM   lotes l
            JOIN   materias_primas mp ON mp.id = l.materia_prima_id
            WHERE  l.activo = 1 AND l.cantidad_actual > 0
              AND  l.fecha_vencimiento BETWEEN date('now') AND date('now', '+30 days')
            ORDER  BY l.fecha_vencimiento ASC
        """).fetchall()
        conn.close()

        self._datos_export = {"vencidos": vencidos, "proximos": proximos}
        cuerpo = self._scroll_datos()

        hdrs = [("Producto", 0.38), ("Lote", 0.18),
                ("Fecha", 0.20), ("Días", 0.10), ("Cant.", 0.14)]

        # Sección vencidos
        cuerpo.add_widget(_seccion_titulo(
            f"⬤ Vencidos ({len(vencidos)})", color=_ROJO
        ))
        cuerpo.add_widget(_fila_tabla(hdrs, bg=_CAFE, negrita=True))
        if not vencidos:
            cuerpo.add_widget(_fila_tabla(
                [("Sin lotes vencidos ✓", 1.0)], bg=_VERDE_FONDO
            ))
        for i, r in enumerate(vencidos):
            cuerpo.add_widget(_fila_tabla(
                [(r["nombre"], 0.38), (r["numero_lote"], 0.18),
                 (r["fecha_vencimiento"], 0.20),
                 (f"-{r['dias']}d", 0.10),
                 (f"{float(r['cantidad_actual']):,.2f}", 0.14)],
                bg=_ROJO_FONDO,
            ))
            cuerpo.add_widget(MDDivider())

        # Sección próximos
        cuerpo.add_widget(_seccion_titulo(
            f"⬤ Próximos 30 días ({len(proximos)})", color=_NARANJA
        ))
        cuerpo.add_widget(_fila_tabla(hdrs, bg=_CAFE, negrita=True))
        if not proximos:
            cuerpo.add_widget(_fila_tabla(
                [("Sin vencimientos próximos ✓", 1.0)], bg=_VERDE_FONDO
            ))
        for i, r in enumerate(proximos):
            cuerpo.add_widget(_fila_tabla(
                [(r["nombre"], 0.38), (r["numero_lote"], 0.18),
                 (r["fecha_vencimiento"], 0.20),
                 (f"{r['dias']}d", 0.10),
                 (f"{float(r['cantidad_actual']):,.2f}", 0.14)],
                bg=_NARANJA_FONDO,
            ))
            cuerpo.add_widget(MDDivider())

    # ─── 3. MOVIMIENTOS ──────────────────────────────────────────────────────

    def _render_movimientos(self):
        # Filtros
        filtros = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(68),
            padding=[dp(8), dp(4)],
            spacing=dp(6),
            md_bg_color=_BLANCO,
        )

        self._tf_desde = MDTextField(
            text=self._fecha_desde,
            mode="outlined",
            size_hint_x=0.35,
            size_hint_y=None,
            height=dp(56),
        )
        self._tf_desde.add_widget(MDTextFieldHintText(text="Desde"))

        btn_cal_d = MDIconButton(
            icon="calendar-start",
            theme_icon_color="Custom",
            icon_color=_CAFE,
            size_hint_x=None,
            width=dp(36),
        )
        btn_cal_d.bind(on_release=lambda x: self._picker_fecha(self._tf_desde))

        self._tf_hasta = MDTextField(
            text=self._fecha_hasta,
            mode="outlined",
            size_hint_x=0.35,
            size_hint_y=None,
            height=dp(56),
        )
        self._tf_hasta.add_widget(MDTextFieldHintText(text="Hasta"))

        btn_cal_h = MDIconButton(
            icon="calendar-end",
            theme_icon_color="Custom",
            icon_color=_CAFE,
            size_hint_x=None,
            width=dp(36),
        )
        btn_cal_h.bind(on_release=lambda x: self._picker_fecha(self._tf_hasta))

        btn_filtrar = MDButton(
            MDButtonText(text="Filtrar",
                         theme_text_color="Custom", text_color=_CAFE),
            style="text",
            size_hint_x=None,
            width=dp(70),
        )
        btn_filtrar.bind(on_release=lambda x: self._cargar_movimientos())

        for w in [self._tf_desde, btn_cal_d,
                  self._tf_hasta, btn_cal_h, btn_filtrar]:
            filtros.add_widget(w)

        self._panel.add_widget(filtros)
        self._panel.add_widget(MDDivider())

        self._scroll_mov = MDScrollView(do_scroll_x=False)
        self._cuerpo_mov = MDBoxLayout(orientation="vertical", adaptive_height=True)
        self._scroll_mov.add_widget(self._cuerpo_mov)
        self._panel.add_widget(self._scroll_mov)

        self._cargar_movimientos()

    def _cargar_movimientos(self):
        self._cuerpo_mov.clear_widgets()
        f_desde = self._tf_desde.text.strip() or self._fecha_desde
        f_hasta = self._tf_hasta.text.strip() or self._fecha_hasta
        self._fecha_desde = f_desde
        self._fecha_hasta = f_hasta

        conn = database.get_connection()
        rows = conn.execute("""
            SELECT m.fecha, m.tipo, m.cantidad, m.costo_unitario,
                   mp.nombre, mp.unidad_medida, m.referencia
            FROM   movimientos m
            JOIN   materias_primas mp ON mp.id = m.materia_prima_id
            WHERE  m.fecha BETWEEN ? AND ?
            ORDER  BY m.fecha DESC, m.id DESC
        """, (f_desde, f_hasta)).fetchall()
        conn.close()

        self._datos_export = rows
        hdrs = [("Fecha", 0.22), ("Tipo", 0.12),
                ("Materia Prima", 0.36), ("Cant.", 0.15), ("₡/u", 0.15)]

        entradas = [r for r in rows if r["tipo"] == "ingreso"]
        salidas  = [r for r in rows if r["tipo"] == "salida"]

        total_ent = sum(float(r["cantidad"]) * float(r["costo_unitario"] or 0)
                        for r in entradas)
        total_sal = sum(float(r["cantidad"]) * float(r["costo_unitario"] or 0)
                        for r in salidas)

        for tipo_s, subset, bg_fila, color_sec in [
            ("Entradas", entradas, _VERDE_FONDO, _VERDE),
            ("Salidas",  salidas,  _NARANJA_FONDO, _NARANJA),
        ]:
            total = total_ent if tipo_s == "Entradas" else total_sal
            self._cuerpo_mov.add_widget(_seccion_titulo(
                f"{tipo_s} ({len(subset)})  —  ₡{total:,.2f}",
                color=color_sec,
            ))
            self._cuerpo_mov.add_widget(_fila_tabla(hdrs, bg=_CAFE, negrita=True))
            if not subset:
                self._cuerpo_mov.add_widget(_fila_tabla(
                    [("Sin registros en este período", 1.0)], bg=_GRIS
                ))
            for i, r in enumerate(subset):
                cu = float(r["costo_unitario"] or 0)
                self._cuerpo_mov.add_widget(_fila_tabla(
                    [(r["fecha"], 0.22), (r["tipo"][:3].upper(), 0.12),
                     (r["nombre"], 0.36),
                     (f"{float(r['cantidad']):,.2f} {r['unidad_medida']}", 0.15),
                     (f"₡{cu:,.0f}", 0.15)],
                    bg=bg_fila if i % 2 == 0 else _BLANCO,
                ))
                self._cuerpo_mov.add_widget(MDDivider())

        self._cuerpo_mov.add_widget(_pie_totales(
            f"Entradas: ₡{total_ent:,.2f}  ·  Salidas: ₡{total_sal:,.2f}"
        ))

    def _picker_fecha(self, tf):
        picker = MDModalDatePicker()
        picker.bind(on_ok=lambda inst: self._set_fecha(inst, tf))
        picker.open()

    def _set_fecha(self, inst, tf):
        fechas = inst.get_date()
        if fechas:
            tf.text = fechas[0].strftime("%Y-%m-%d")

    # ─── 4. COSTOS POR RECETA ────────────────────────────────────────────────

    def _render_costos(self):
        conn = database.get_connection()
        recetas = conn.execute("""
            SELECT r.id, r.nombre, r.porciones
            FROM   recetas r
            WHERE  r.activo = 1
            ORDER  BY r.nombre COLLATE NOCASE
        """).fetchall()

        resultado = []
        for rec in recetas:
            ings = conn.execute("""
                SELECT ri.materia_prima_id, ri.cantidad
                FROM   receta_ingredientes ri
                WHERE  ri.receta_id = ?
            """, (rec["id"],)).fetchall()

            costo_batch = sum(
                ing["cantidad"] * database.get_costo_promedio_ponderado(
                    ing["materia_prima_id"], conn
                )
                for ing in ings
            )
            porciones  = float(rec["porciones"] or 1)
            costo_porc = costo_batch / porciones if porciones > 0 else 0

            # Precio promedio de venta de productos vinculados a esta receta
            prec_row = conn.execute("""
                SELECT AVG(pt.precio_venta) AS precio_prom,
                       AVG(pt.margen_ganancia) AS margen_prom
                FROM   productos_terminados pt
                JOIN   salidas s ON s.id = pt.salida_id
                WHERE  s.receta_id = ?
                  AND  pt.precio_venta > 0
            """, (rec["id"],)).fetchone()
            precio_prom = float(prec_row["precio_prom"] or 0)
            margen_prom = float(prec_row["margen_prom"] or 0)

            resultado.append({
                "nombre":      rec["nombre"],
                "porciones":   porciones,
                "costo_batch": costo_batch,
                "costo_porc":  costo_porc,
                "precio_prom": precio_prom,
                "margen_prom": margen_prom,
            })
        conn.close()

        self._datos_export = resultado
        cuerpo = self._scroll_datos()

        cuerpo.add_widget(_fila_tabla(
            [("Receta", 0.34), ("Porciones", 0.14), ("Costo/u ₡", 0.20),
             ("Precio ₡", 0.16), ("Margen", 0.16)],
            bg=_CAFE, negrita=True,
        ))

        for i, r in enumerate(resultado):
            m = r["margen_prom"]
            if m >= 30:
                bg = _VERDE_FONDO
                semal = "🟢"
            elif m >= 10:
                bg = _NARANJA_FONDO
                semal = "🟡"
            elif m > 0:
                bg = _ROJO_FONDO
                semal = "🔴"
            else:
                bg = _GRIS if i % 2 == 0 else _BLANCO
                semal = "—"

            margen_txt = f"{semal} {m:.1f}%" if m > 0 else "—"
            precio_txt = f"₡{r['precio_prom']:,.0f}" if r["precio_prom"] > 0 else "—"

            cuerpo.add_widget(_fila_tabla(
                [(r["nombre"], 0.34),
                 (f"{r['porciones']:.0f}", 0.14),
                 (f"₡{r['costo_porc']:,.2f}", 0.20),
                 (precio_txt, 0.16),
                 (margen_txt, 0.16)],
                bg=bg,
            ))
            cuerpo.add_widget(MDDivider())

        cuerpo.add_widget(_pie_totales(f"{len(resultado)} receta(s) analizadas"))

    # ─── 5. PRODUCTOS TERMINADOS ──────────────────────────────────────────────

    def _render_productos(self):
        conn = database.get_connection()
        rows = conn.execute("""
            SELECT nombre, cantidad, costo_unitario, precio_venta,
                   margen_ganancia, fecha_produccion, fecha_vencimiento
            FROM   productos_terminados
            ORDER  BY fecha_produccion DESC
        """).fetchall()
        conn.close()

        self._datos_export = rows
        cuerpo = self._scroll_datos()

        cuerpo.add_widget(_fila_tabla(
            [("Producto", 0.34), ("Cant.", 0.10), ("Costo ₡", 0.18),
             ("Precio ₡", 0.18), ("Vto.", 0.20)],
            bg=_CAFE, negrita=True,
        ))

        hoy  = date.today().isoformat()
        lim30 = (date.today() + timedelta(days=30)).isoformat()
        total_costo = 0.0
        total_venta = 0.0

        for i, r in enumerate(rows):
            vto  = r["fecha_vencimiento"] or ""
            cant = float(r["cantidad"] or 0)
            cu   = float(r["costo_unitario"] or 0)
            pv   = float(r["precio_venta"] or 0)
            total_costo += cant * cu
            total_venta += cant * pv

            if vto and vto < hoy:
                bg = _ROJO_FONDO
                vto_txt = f"❌ {vto}"
            elif vto and vto <= lim30:
                bg = _NARANJA_FONDO
                vto_txt = f"⚠ {vto}"
            else:
                bg = _GRIS if i % 2 == 0 else _BLANCO
                vto_txt = vto or "—"

            cant_s = str(int(cant)) if cant == int(cant) else f"{cant:.2f}"
            cuerpo.add_widget(_fila_tabla(
                [(r["nombre"], 0.34), (cant_s, 0.10),
                 (f"₡{cu:,.0f}", 0.18), (f"₡{pv:,.0f}", 0.18),
                 (vto_txt, 0.20)],
                bg=bg,
            ))
            cuerpo.add_widget(MDDivider())

        cuerpo.add_widget(_pie_totales(
            f"Costo stock: ₡{total_costo:,.2f}  ·  Valor venta: ₡{total_venta:,.2f}"
        ))

    # ─── 6. PROYECCIÓN DE COMPRAS ─────────────────────────────────────────────

    def _render_proyeccion(self):
        # Filtro de días
        filtros = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(68),
            padding=[dp(8), dp(4)],
            spacing=dp(8),
            md_bg_color=_BLANCO,
        )
        self._tf_dias_proy = MDTextField(
            text=str(self._dias_proyeccion),
            mode="outlined",
            size_hint_x=0.4,
            size_hint_y=None,
            height=dp(56),
            input_type="number",
        )
        self._tf_dias_proy.add_widget(
            MDTextFieldHintText(text="Analizar últimos X días")
        )
        btn_calc = MDButton(
            MDButtonText(text="Calcular",
                         theme_text_color="Custom", text_color=_CAFE),
            style="text",
        )
        btn_calc.bind(on_release=lambda x: self._cargar_proyeccion())
        filtros.add_widget(self._tf_dias_proy)
        filtros.add_widget(btn_calc)
        filtros.add_widget(Widget())

        self._panel.add_widget(filtros)
        self._panel.add_widget(MDDivider())

        self._scroll_proy = MDScrollView(do_scroll_x=False)
        self._cuerpo_proy = MDBoxLayout(orientation="vertical", adaptive_height=True)
        self._scroll_proy.add_widget(self._cuerpo_proy)
        self._panel.add_widget(self._scroll_proy)

        self._cargar_proyeccion()

    def _cargar_proyeccion(self):
        self._cuerpo_proy.clear_widgets()
        try:
            dias = max(1, int(self._tf_dias_proy.text.strip() or 30))
        except (ValueError, TypeError):
            dias = 30
        self._dias_proyeccion = dias

        conn = database.get_connection()
        rows = conn.execute("""
            SELECT mp.id, mp.nombre, mp.unidad_medida, mp.stock_minimo,
                (SELECT COALESCE(SUM(l.cantidad_actual), 0)
                 FROM lotes l
                 WHERE l.materia_prima_id = mp.id AND l.activo = 1) AS stock_actual,
                (SELECT COALESCE(SUM(m.cantidad), 0)
                 FROM movimientos m
                 WHERE m.materia_prima_id = mp.id AND m.tipo = 'salida'
                   AND m.fecha >= date('now', '-' || ? || ' days')) AS consumido
            FROM  materias_primas mp
            WHERE mp.activo = 1
            ORDER BY mp.nombre COLLATE NOCASE
        """, (dias,)).fetchall()
        conn.close()

        self._datos_export = rows
        hdrs = [("Materia Prima", 0.30), ("Stock", 0.16),
                ("Cons./día", 0.16), ("Días stock", 0.14),
                ("Sugerido", 0.24)]

        self._cuerpo_proy.add_widget(_fila_tabla(hdrs, bg=_CAFE, negrita=True))

        for i, r in enumerate(rows):
            stock  = float(r["stock_actual"])
            consum = float(r["consumido"])
            cons_d = consum / dias if dias > 0 else 0.0

            if cons_d > 0:
                dias_stock = stock / cons_d
                sugerido   = max(0.0, cons_d * 60 - stock)  # cubrir 60 días
            else:
                dias_stock = 999
                sugerido   = 0.0

            if stock <= 0:
                bg = _ROJO_FONDO
            elif dias_stock < 7:
                bg = _ROJO_FONDO
            elif dias_stock < 30:
                bg = _NARANJA_FONDO
            else:
                bg = _GRIS if i % 2 == 0 else _BLANCO

            u   = r["unidad_medida"] or ""
            ds  = f"{dias_stock:.0f} d" if dias_stock < 999 else "—"
            sug = f"{sugerido:.2f} {u}" if sugerido > 0 else "OK"

            self._cuerpo_proy.add_widget(_fila_tabla(
                [(r["nombre"], 0.30),
                 (f"{stock:,.2f} {u}", 0.16),
                 (f"{cons_d:,.4f}/d", 0.16),
                 (ds, 0.14),
                 (sug, 0.24)],
                bg=bg,
            ))
            self._cuerpo_proy.add_widget(MDDivider())

        urgentes = sum(
            1 for r in rows
            if float(r["stock_actual"]) <= 0
            or (float(r["consumido"]) > 0
                and float(r["stock_actual"]) / (float(r["consumido"]) / dias) < 7)
        )
        self._cuerpo_proy.add_widget(_pie_totales(
            f"Basado en {dias} días  ·  {urgentes} material(es) urgente(s)"
        ))

    # ─── EXPORTAR ─────────────────────────────────────────────────────────────

    def _exportar_reporte(self):
        texto = self._generar_texto_export()
        if _ANDROID:
            try:
                intent = Intent()
                intent.setAction(Intent.ACTION_SEND)
                intent.putExtra(Intent.EXTRA_TEXT, texto)
                intent.setType("text/plain")
                mActivity.startActivity(
                    Intent.createChooser(intent, "Compartir reporte")
                )
                return
            except Exception:
                pass

        # Fallback: mostrar en dialog con opción de copiar
        sv = MDScrollView(
            size_hint_y=None,
            height=Window.height * 0.50,
            do_scroll_x=False,
        )
        lbl = MDLabel(
            text=texto,
            size_hint_y=None,
            font_style="Body",
            role="small",
            padding=[dp(8), dp(4)],
        )
        lbl.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        sv.add_widget(lbl)

        btn_copiar = MDButton(
            MDButtonText(
                text="📋 Copiar texto",
                theme_text_color="Custom",
                text_color=_DORADO,
            ),
            style="text",
        )
        btn_cerrar = MDButton(MDButtonText(text="Cerrar"), style="text")

        self._dialogo_export = MDDialog(
            MDDialogHeadlineText(text="📄 Exportar reporte"),
            MDDialogContentContainer(sv),
            MDDialogButtonContainer(
                Widget(),
                btn_copiar,
                btn_cerrar,
                spacing=dp(8),
            ),
        )

        def _copiar(x):
            Clipboard.copy(texto)
            MDSnackbar(
                MDSnackbarText(text="✅ Copiado al portapapeles"),
                y=dp(24),
                pos_hint={"center_x": 0.5},
                size_hint_x=0.8,
                duration=2,
            ).open()

        btn_copiar.bind(on_release=_copiar)
        btn_cerrar.bind(on_release=lambda x: self._dialogo_export.dismiss())
        self._dialogo_export.open()

    def _generar_texto_export(self) -> str:
        """Genera texto plano formateado del reporte activo."""
        hoy   = date.today().isoformat()
        sep   = "─" * 42
        lineas = [
            f"REPORTE — {self._reporte_activo.upper()}",
            f"Generado: {hoy}",
            sep,
        ]

        tipo = self._reporte_activo
        datos = getattr(self, "_datos_export", [])

        if tipo == "inventario":
            lineas.append(f"{'Materia Prima':<28} {'Stock':>10} {'Valor ₡':>12}")
            lineas.append(sep)
            for r in datos:
                lineas.append(
                    f"{r['nombre']:<28} {float(r['stock']):>10,.2f} {r['unidad_medida']:<5}"
                    f"  ₡{float(r['valor']):>10,.2f}"
                )
            total = sum(float(r["valor"]) for r in datos)
            lineas += [sep, f"TOTAL VALOR INVENTARIO:  ₡{total:,.2f}"]

        elif tipo == "vencimientos":
            for sec, rows in [("VENCIDOS", datos["vencidos"]),
                               ("PRÓXIMOS 30 DÍAS", datos["proximos"])]:
                lineas.append(f"\n{sec} ({len(rows)})")
                lineas.append(sep)
                for r in rows:
                    lineas.append(
                        f"{r['nombre']:<24} Lote:{r['numero_lote']:<10}"
                        f" Vto:{r['fecha_vencimiento']}  {r['dias']}d"
                    )

        elif tipo == "movimientos":
            for r in datos:
                cu = float(r["costo_unitario"] or 0)
                lineas.append(
                    f"{r['fecha']}  {r['tipo'].upper():<7}  "
                    f"{r['nombre']:<22}  {float(r['cantidad']):,.2f} "
                    f"{r['unidad_medida']:<5}  ₡{cu:,.2f}"
                )

        elif tipo == "costos":
            lineas.append(f"{'Receta':<26} {'Porc':>5} {'Costo/u':>10} {'Margen':>8}")
            lineas.append(sep)
            for r in datos:
                lineas.append(
                    f"{r['nombre']:<26} {r['porciones']:>5.0f}"
                    f"  ₡{r['costo_porc']:>8,.2f}  {r['margen_prom']:>6.1f}%"
                )

        elif tipo == "productos":
            for r in datos:
                lineas.append(
                    f"{r['nombre']:<24}  Cant:{float(r['cantidad']):.2f}"
                    f"  ₡{float(r['precio_venta'] or 0):,.2f}"
                    f"  Vto:{r['fecha_vencimiento'] or '—'}"
                )

        elif tipo == "proyeccion":
            lineas.append(
                f"{'Materia Prima':<26} {'Stock':>8} "
                f"{'Días':>6} {'Sugerido':>12}"
            )
            lineas.append(sep)
            dias = self._dias_proyeccion
            for r in datos:
                stock  = float(r["stock_actual"])
                consum = float(r["consumido"])
                cons_d = consum / dias if dias > 0 else 0
                ds     = f"{stock/cons_d:.0f}d" if cons_d > 0 else "—"
                sug    = f"{max(0.0, cons_d*60-stock):.2f}" if cons_d > 0 else "OK"
                lineas.append(
                    f"{r['nombre']:<26} {stock:>12,.2f}"
                    f" {ds:>6} {sug:>12} {r['unidad_medida']}"
                )

        return "\n".join(lineas)

    # ─── EXPORTAR PDF ─────────────────────────────────────────────────────────

    def _exportar_pdf(self):
        """En Android genera TXT compartible; en escritorio genera PDF con reportlab."""
        if _ANDROID:
            self._exportar_txt_android()
            return

        if not _REPORTLAB:
            MDSnackbar(
                MDSnackbarText(
                    text="❌ reportlab no instalado. "
                         "Ejecute: pip install reportlab --break-system-packages"
                ),
                y=dp(24), pos_hint={"center_x": 0.5},
                size_hint_x=0.98, duration=5,
            ).open()
            return

        carpeta = Path.home() / "Documents" / "Panaderia"
        try:
            carpeta.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            MDSnackbar(
                MDSnackbarText(text=f"❌ No se pudo crear la carpeta: {e}"),
                y=dp(24), pos_hint={"center_x": 0.5},
                size_hint_x=0.9, duration=4,
            ).open()
            return

        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = str(carpeta / f"reporte_{self._reporte_activo}_{ts}.pdf")

        try:
            self._generar_pdf(ruta)
            _subproc.Popen(["xdg-open", ruta])
            MDSnackbar(
                MDSnackbarText(text="✅ PDF guardado en Documents/Panaderia/"),
                y=dp(24), pos_hint={"center_x": 0.5},
                size_hint_x=0.85, duration=3,
            ).open()
        except Exception as e:
            MDSnackbar(
                MDSnackbarText(text=f"❌ Error al generar PDF: {e}"),
                y=dp(24), pos_hint={"center_x": 0.5},
                size_hint_x=0.9, duration=4,
            ).open()

    def _exportar_txt_android(self):
        """Android: guarda el reporte como .txt y lo comparte con un Intent."""
        _nombres = {
            "inventario":   "Inventario Actual",
            "vencimientos": "Vencimientos de Lotes",
            "movimientos":  "Movimientos por Período",
            "costos":       "Costos por Receta",
            "productos":    "Productos Terminados",
            "proyeccion":   "Proyección de Compras",
        }
        texto = self._generar_texto_export()
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Ruta pública en Android (almacenamiento externo)
        try:
            from android.storage import primary_external_storage_path  # type: ignore
            base = primary_external_storage_path()
        except Exception:
            base = "/sdcard"

        carpeta = os.path.join(base, "Documents", "Panaderia")
        try:
            os.makedirs(carpeta, exist_ok=True)
        except Exception as e:
            MDSnackbar(
                MDSnackbarText(text=f"❌ No se pudo crear la carpeta: {e}"),
                y=dp(24), pos_hint={"center_x": 0.5},
                size_hint_x=0.9, duration=4,
            ).open()
            return

        nombre = f"reporte_{self._reporte_activo}_{ts}.txt"
        ruta   = os.path.join(carpeta, nombre)

        try:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(texto)
        except Exception as e:
            MDSnackbar(
                MDSnackbarText(text=f"❌ Error al guardar archivo: {e}"),
                y=dp(24), pos_hint={"center_x": 0.5},
                size_hint_x=0.9, duration=4,
            ).open()
            return

        # Compartir con Intent ACTION_SEND
        try:
            from android.content import Intent                          # type: ignore
            from android import mActivity                               # type: ignore
            intent = Intent()
            intent.setAction(Intent.ACTION_SEND)
            intent.putExtra(Intent.EXTRA_TEXT, texto)
            intent.putExtra(Intent.EXTRA_SUBJECT,
                            _nombres.get(self._reporte_activo, "Reporte"))
            intent.setType("text/plain")
            mActivity.startActivity(
                Intent.createChooser(intent, "Compartir reporte")
            )
        except Exception:
            pass  # Si falla el Intent, el archivo ya quedó guardado

        MDSnackbar(
            MDSnackbarText(text="✅ Reporte guardado en Documents/Panaderia/"),
            y=dp(24), pos_hint={"center_x": 0.5},
            size_hint_x=0.88, duration=3,
        ).open()

    def _generar_pdf(self, ruta: str):
        """Construye el documento PDF con reportlab (orientación horizontal)."""
        _nombres = {
            "inventario":   "Inventario Actual",
            "vencimientos": "Vencimientos de Lotes",
            "movimientos":  "Movimientos por Período",
            "costos":       "Costos por Receta",
            "productos":    "Productos Terminados",
            "proyeccion":   "Proyección de Compras",
        }
        cafe = _rl_colors.HexColor("#3E2723")
        page = _rl_landscape(A4)
        ancho = page[0] - 3 * _cm          # ancho útil (márgenes 1.5 cm c/u)

        doc = SimpleDocTemplate(
            ruta, pagesize=page,
            leftMargin=1.5 * _cm, rightMargin=1.5 * _cm,
            topMargin=1.5 * _cm,  bottomMargin=1.5 * _cm,
            title=_nombres.get(self._reporte_activo, "Reporte"),
        )
        styles = getSampleStyleSheet()
        s_h1 = ParagraphStyle("s_h1", parent=styles["Normal"],
                               fontName=_FUENTE_B, fontSize=18,
                               textColor=cafe, spaceAfter=3)
        s_h2 = ParagraphStyle("s_h2", parent=styles["Normal"],
                               fontName=_FUENTE_B, fontSize=13,
                               textColor=cafe, spaceAfter=2)
        s_ts = ParagraphStyle("s_ts", parent=styles["Normal"],
                               fontName=_FUENTE, fontSize=9,
                               textColor=_rl_colors.grey, spaceAfter=8)

        nombre = _nombres.get(self._reporte_activo, "Reporte")
        ahora  = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")

        elems = [
            Paragraph("Panadería \u2014 Control de Inventarios", s_h1),
            Paragraph(nombre, s_h2),
            Paragraph(f"Generado: {ahora}", s_ts),
            Spacer(1, 0.25 * _cm),
        ]

        metodo = {
            "inventario":   self._pdf_inventario,
            "vencimientos": self._pdf_vencimientos,
            "movimientos":  self._pdf_movimientos,
            "costos":       self._pdf_costos,
            "productos":    self._pdf_productos,
            "proyeccion":   self._pdf_proyeccion,
        }.get(self._reporte_activo)
        if metodo:
            metodo(elems, ancho)
        doc.build(elems)

    # ── helpers PDF internos ──────────────────────────────────────────────────

    def _pdf_tabla(self, datos: list, col_w: list, colores: list = None):
        """Tabla estándar con encabezado café y filas alternas."""
        cafe   = _rl_colors.HexColor("#3E2723")
        gris   = _rl_colors.HexColor("#F5F5F5")
        borde  = _rl_colors.HexColor("#BDBDBD")
        blanco = _rl_colors.white
        n = len(datos)
        cmds = [
            ("BACKGROUND",    (0, 0), (-1, 0), cafe),
            ("TEXTCOLOR",     (0, 0), (-1, 0), blanco),
            ("FONTNAME",      (0, 0), (-1, 0), _FUENTE_B),
            ("FONTSIZE",      (0, 0), (-1, 0), 9),
            ("TOPPADDING",    (0, 0), (-1, 0), 5),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
            ("FONTNAME",      (0, 1), (-1, -1), _FUENTE),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("TOPPADDING",    (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ("GRID",          (0, 0), (-1, -1), 0.5, borde),
            ("LINEBELOW",     (0, 0), (-1, 0),  1.5, cafe),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]
        for i in range(1, n):
            if colores and (i - 1) < len(colores):
                cmds.append(("BACKGROUND", (0, i), (-1, i), colores[i - 1]))
            else:
                cmds.append(("BACKGROUND", (0, i), (-1, i),
                              gris if i % 2 == 0 else blanco))
        t = Table(datos, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle(cmds))
        return t

    def _pdf_pie_tabla(self, texto: str, ancho: float):
        """Fila de totales: fondo café, texto dorado."""
        t = Table([[texto]], colWidths=[ancho])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), _rl_colors.HexColor("#3E2723")),
            ("TEXTCOLOR",     (0, 0), (-1, -1), _rl_colors.HexColor("#FFA000")),
            ("FONTNAME",      (0, 0), (-1, -1), _FUENTE_B),
            ("FONTSIZE",      (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        return t

    def _pdf_seccion_titulo(self, texto: str, ancho: float,
                            color_hex: str = "#3E2723"):
        """Fila de separador de sección con color personalizado."""
        t = Table([[texto]], colWidths=[ancho])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), _rl_colors.HexColor(color_hex)),
            ("TEXTCOLOR",     (0, 0), (-1, -1), _rl_colors.white),
            ("FONTNAME",      (0, 0), (-1, -1), _FUENTE_B),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        return t

    # ── reportes PDF individuales ─────────────────────────────────────────────

    def _pdf_inventario(self, elems: list, ancho: float):
        datos  = getattr(self, "_datos_export", [])
        rojo_f = _rl_colors.HexColor("#FFCDD2")
        nar_f  = _rl_colors.HexColor("#FFE0B2")
        gris   = _rl_colors.HexColor("#F5F5F5")
        blanco = _rl_colors.white

        col_w = [ancho * p for p in (0.36, 0.17, 0.12, 0.18, 0.17)]
        encab = [["Materia Prima", "Categoría", "Unidad", "Stock", "Valor \u20a1"]]

        filas   = []
        colores = []
        total_valor = 0.0
        for i, r in enumerate(datos):
            stock  = float(r["stock"])
            minimo = float(r["stock_minimo"] or 0)
            valor  = float(r["valor"])
            total_valor += valor
            if stock <= 0:
                colores.append(rojo_f)
            elif stock < minimo:
                colores.append(nar_f)
            else:
                colores.append(gris if i % 2 == 0 else blanco)
            filas.append([
                r["nombre"], r["categoria"] or "—",
                r["unidad_medida"], f"{stock:,.2f}",
                f"\u20a1{valor:,.0f}",
            ])

        elems.append(self._pdf_tabla(encab + filas, col_w, colores))
        elems.append(Spacer(1, 0.2 * _cm))
        elems.append(self._pdf_pie_tabla(
            f"{len(datos)} materias primas   "
            f"Valor total: \u20a1{total_valor:,.2f}",
            ancho,
        ))

    def _pdf_vencimientos(self, elems: list, ancho: float):
        datos    = getattr(self, "_datos_export", {})
        vencidos = datos.get("vencidos", [])
        proximos = datos.get("proximos", [])
        rojo_f  = _rl_colors.HexColor("#FFCDD2")
        nar_f   = _rl_colors.HexColor("#FFE0B2")
        verde_f = _rl_colors.HexColor("#C8E6C9")

        col_w = [ancho * p for p in (0.34, 0.18, 0.20, 0.12, 0.16)]
        encab = [["Producto", "Lote", "Fecha Venc.", "Días", "Cantidad"]]

        for sec_txt, subset, color_hex, bg_fila in [
            (f"Vencidos ({len(vencidos)})",         vencidos, "#B71C1C", rojo_f),
            (f"Próximos 30 días ({len(proximos)})",  proximos, "#E65100", nar_f),
        ]:
            elems.append(Spacer(1, 0.2 * _cm))
            elems.append(self._pdf_seccion_titulo(sec_txt, ancho, color_hex))
            if not subset:
                elems.append(self._pdf_tabla(
                    encab + [["Sin registros", "", "", "", ""]],
                    col_w, [verde_f],
                ))
            else:
                filas   = []
                colores = []
                for r in subset:
                    filas.append([
                        r["nombre"], r["numero_lote"],
                        r["fecha_vencimiento"],
                        f"{r['dias']}d",
                        f"{float(r['cantidad_actual']):,.2f}",
                    ])
                    colores.append(bg_fila)
                elems.append(self._pdf_tabla(encab + filas, col_w, colores))

        elems.append(Spacer(1, 0.2 * _cm))
        elems.append(self._pdf_pie_tabla(
            f"Vencidos: {len(vencidos)}   "
            f"Próximos 30 días: {len(proximos)}",
            ancho,
        ))

    def _pdf_movimientos(self, elems: list, ancho: float):
        datos   = getattr(self, "_datos_export", [])
        verde_f = _rl_colors.HexColor("#C8E6C9")
        nar_f   = _rl_colors.HexColor("#FFE0B2")
        blanco  = _rl_colors.white

        col_w = [ancho * p for p in (0.16, 0.09, 0.34, 0.22, 0.19)]
        encab = [["Fecha", "Tipo", "Materia Prima", "Cantidad", "\u20a1/unidad"]]

        entradas = [r for r in datos if r["tipo"] == "ingreso"]
        salidas  = [r for r in datos if r["tipo"] == "salida"]
        total_e  = sum(float(r["cantidad"]) * float(r["costo_unitario"] or 0)
                       for r in entradas)
        total_s  = sum(float(r["cantidad"]) * float(r["costo_unitario"] or 0)
                       for r in salidas)

        for sec_txt, subset, color_hex, bg_fila in [
            (f"Entradas ({len(entradas)})  \u2014  \u20a1{total_e:,.2f}",
             entradas, "#1B5E20", verde_f),
            (f"Salidas ({len(salidas)})  \u2014  \u20a1{total_s:,.2f}",
             salidas,  "#E65100", nar_f),
        ]:
            elems.append(Spacer(1, 0.2 * _cm))
            elems.append(self._pdf_seccion_titulo(sec_txt, ancho, color_hex))
            if not subset:
                elems.append(self._pdf_tabla(
                    encab + [["Sin registros en este período", "", "", "", ""]],
                    col_w, [_rl_colors.HexColor("#F5F5F5")],
                ))
            else:
                filas   = []
                colores = []
                for i, r in enumerate(subset):
                    cu = float(r["costo_unitario"] or 0)
                    filas.append([
                        r["fecha"], r["tipo"][:3].upper(),
                        r["nombre"],
                        f"{float(r['cantidad']):,.2f} {r['unidad_medida']}",
                        f"\u20a1{cu:,.0f}",
                    ])
                    colores.append(bg_fila if i % 2 == 0 else blanco)
                elems.append(self._pdf_tabla(encab + filas, col_w, colores))

        elems.append(Spacer(1, 0.2 * _cm))
        elems.append(self._pdf_pie_tabla(
            f"Entradas: \u20a1{total_e:,.2f}   "
            f"Salidas: \u20a1{total_s:,.2f}",
            ancho,
        ))

    def _pdf_costos(self, elems: list, ancho: float):
        datos   = getattr(self, "_datos_export", [])
        verde_f = _rl_colors.HexColor("#C8E6C9")
        nar_f   = _rl_colors.HexColor("#FFE0B2")
        rojo_f  = _rl_colors.HexColor("#FFCDD2")
        gris    = _rl_colors.HexColor("#F5F5F5")
        blanco  = _rl_colors.white

        col_w = [ancho * p for p in (0.34, 0.12, 0.20, 0.18, 0.16)]
        encab = [["Receta", "Porciones", "Costo/u \u20a1",
                  "Precio \u20a1", "Margen"]]

        filas   = []
        colores = []
        for i, r in enumerate(datos):
            m = r["margen_prom"]
            if m >= 30:
                colores.append(verde_f)
                estado = "BUENO"
            elif m >= 10:
                colores.append(nar_f)
                estado = "REGULAR"
            elif m > 0:
                colores.append(rojo_f)
                estado = "BAJO"
            else:
                colores.append(gris if i % 2 == 0 else blanco)
                estado = "—"

            precio_txt = (f"\u20a1{r['precio_prom']:,.0f}"
                          if r["precio_prom"] > 0 else "—")
            margen_txt = f"{m:.1f}% ({estado})" if m > 0 else "—"
            filas.append([
                r["nombre"], f"{r['porciones']:.0f}",
                f"\u20a1{r['costo_porc']:,.2f}",
                precio_txt, margen_txt,
            ])

        elems.append(self._pdf_tabla(encab + filas, col_w, colores))
        elems.append(Spacer(1, 0.2 * _cm))
        elems.append(self._pdf_pie_tabla(
            f"{len(datos)} receta(s) analizadas", ancho,
        ))

    def _pdf_productos(self, elems: list, ancho: float):
        datos  = getattr(self, "_datos_export", [])
        rojo_f = _rl_colors.HexColor("#FFCDD2")
        nar_f  = _rl_colors.HexColor("#FFE0B2")
        gris   = _rl_colors.HexColor("#F5F5F5")
        blanco = _rl_colors.white

        col_w = [ancho * p for p in (0.28, 0.10, 0.16, 0.16, 0.10, 0.20)]
        encab = [["Producto", "Cant.", "Costo \u20a1", "Precio \u20a1",
                  "Margen", "Vencimiento"]]

        hoy   = date.today().isoformat()
        lim30 = (date.today() + timedelta(days=30)).isoformat()
        filas   = []
        colores = []
        total_costo = 0.0
        total_venta = 0.0

        for i, r in enumerate(datos):
            vto  = r["fecha_vencimiento"] or ""
            cant = float(r["cantidad"] or 0)
            cu   = float(r["costo_unitario"] or 0)
            pv   = float(r["precio_venta"] or 0)
            mg   = float(r["margen_ganancia"] or 0)
            total_costo += cant * cu
            total_venta += cant * pv

            if vto and vto < hoy:
                colores.append(rojo_f)
                vto_txt = f"VENCIDO {vto}"
            elif vto and vto <= lim30:
                colores.append(nar_f)
                vto_txt = f"Próx. {vto}"
            else:
                colores.append(gris if i % 2 == 0 else blanco)
                vto_txt = vto or "—"

            cant_s = str(int(cant)) if cant == int(cant) else f"{cant:.2f}"
            filas.append([
                r["nombre"], cant_s,
                f"\u20a1{cu:,.0f}", f"\u20a1{pv:,.0f}",
                f"{mg:.1f}%" if mg else "—",
                vto_txt,
            ])

        elems.append(self._pdf_tabla(encab + filas, col_w, colores))
        elems.append(Spacer(1, 0.2 * _cm))
        elems.append(self._pdf_pie_tabla(
            f"Costo stock: \u20a1{total_costo:,.2f}   "
            f"Valor venta: \u20a1{total_venta:,.2f}",
            ancho,
        ))

    def _pdf_proyeccion(self, elems: list, ancho: float):
        datos  = getattr(self, "_datos_export", [])
        dias   = self._dias_proyeccion
        rojo_f = _rl_colors.HexColor("#FFCDD2")
        nar_f  = _rl_colors.HexColor("#FFE0B2")
        gris   = _rl_colors.HexColor("#F5F5F5")
        blanco = _rl_colors.white

        col_w = [ancho * p for p in (0.28, 0.18, 0.17, 0.15, 0.22)]
        encab = [["Materia Prima", "Stock Actual", "Cons./día",
                  "Días Stock", "Sugerido (60d)"]]

        filas    = []
        colores  = []
        urgentes = 0

        for i, r in enumerate(datos):
            stock  = float(r["stock_actual"])
            consum = float(r["consumido"])
            cons_d = consum / dias if dias > 0 else 0.0
            u      = r["unidad_medida"] or ""

            if cons_d > 0:
                dias_stock = stock / cons_d
                sugerido   = max(0.0, cons_d * 60 - stock)
            else:
                dias_stock = 999
                sugerido   = 0.0

            if stock <= 0 or (cons_d > 0 and dias_stock < 7):
                colores.append(rojo_f)
                urgentes += 1
            elif cons_d > 0 and dias_stock < 30:
                colores.append(nar_f)
            else:
                colores.append(gris if i % 2 == 0 else blanco)

            ds  = f"{dias_stock:.0f} d" if dias_stock < 999 else "—"
            sug = f"{sugerido:.2f} {u}" if sugerido > 0 else "OK"
            filas.append([
                r["nombre"],
                f"{stock:,.2f} {u}",
                f"{cons_d:,.4f}/d",
                ds, sug,
            ])

        elems.append(self._pdf_tabla(encab + filas, col_w, colores))
        elems.append(Spacer(1, 0.2 * _cm))
        elems.append(self._pdf_pie_tabla(
            f"Basado en {dias} días   "
            f"{urgentes} material(es) urgente(s)",
            ancho,
        ))
