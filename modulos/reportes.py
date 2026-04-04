"""
modulos/reportes.py — Centro de reportes completo.
KivyMD 1.2.0 compatible.

6 reportes con tarjetas de menú, filtros, tablas con filas alternas,
semáforos de estado y exportación de texto.
"""

from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.card import MDCard
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.snackbar import MDSnackbar

from datetime import date, datetime, timedelta
from pathlib import Path
import os
import subprocess as _subproc

import database
from modulos.base import PantallaBase, MDDivider

_CAFE    = get_color_from_hex("#3E2723")
_DORADO  = get_color_from_hex("#FFA000")
_GRIS    = get_color_from_hex("#F5F5F5")
_BLANCO  = [1, 1, 1, 1]
_ROJO    = get_color_from_hex("#B71C1C")
_VERDE   = get_color_from_hex("#1B5E20")
_NARANJA = get_color_from_hex("#E65100")

_ROJO_FONDO    = get_color_from_hex("#FFCDD2")
_NARANJA_FONDO = get_color_from_hex("#FFE0B2")
_VERDE_FONDO   = get_color_from_hex("#C8E6C9")

try:
    from android.content import Intent           # type: ignore
    from android import mActivity                # type: ignore
    _ANDROID = True
except ImportError:
    _ANDROID = False

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
                              .replace("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"))
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

_MENU = [
    ("inventario",   "📦", "Inventario Actual",     "Stock y valor de todas las materias primas"),
    ("vencimientos", "⚠️", "Vencimientos",           "Lotes vencidos y próximos a vencer (30 días)"),
    ("movimientos",  "📊", "Movimientos",            "Entradas y salidas por período seleccionado"),
    ("costos",       "💰", "Costos por Receta",      "Costo/porción y semáforo de rentabilidad"),
    ("productos",    "🎁", "Productos Terminados",   "Stock, precios de venta y vencimientos"),
    ("proyeccion",   "🛒", "Proyección de Compras",  "Días hasta agotamiento y cantidad sugerida"),
]


# ─── Helpers de UI ───────────────────────────────────────────────────────────

def _fila_tabla(cols: list, bg=None, negrita=False):
    fila = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None, height=dp(44),
        padding=[dp(8), dp(4), dp(8), dp(4)], spacing=dp(4),
    )
    if bg:
        fila.md_bg_color = bg
    for texto, sx in cols:
        lbl = MDLabel(
            text=str(texto), size_hint_x=sx, valign="middle",
            font_style="Body2" if not negrita else "Body1",
            bold=negrita, shorten=True, shorten_from="right",
        )
        fila.add_widget(lbl)
    return fila


def _seccion_titulo(texto: str, color=None):
    box = MDBoxLayout(size_hint_y=None, height=dp(36), padding=[dp(12), dp(4)], md_bg_color=color or _CAFE)
    box.add_widget(MDLabel(text=texto, bold=True, theme_text_color="Custom", text_color=_BLANCO, valign="middle"))
    return box


def _pie_totales(texto: str):
    box = MDBoxLayout(size_hint_y=None, height=dp(40), padding=[dp(16), dp(4)], md_bg_color=_CAFE)
    box.add_widget(MDLabel(text=texto, bold=True, theme_text_color="Custom", text_color=_DORADO, valign="middle"))
    return box


# ─── Pantalla principal ───────────────────────────────────────────────────────

class Pantalla(PantallaBase):
    name            = "reportes"
    titulo_pantalla = "Reportes"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._reporte_activo  = None
        self._fecha_desde     = (date.today() - timedelta(days=30)).isoformat()
        self._fecha_hasta     = date.today().isoformat()
        self._dias_proyeccion = 30
        self._dialogo_export  = None

        self._area = MDBoxLayout(orientation="vertical")
        self.layout_raiz.add_widget(self._area)

    def on_pre_enter(self, *args):
        self._mostrar_menu()

    # ─── MENÚ ────────────────────────────────────────────────────────────────

    def _mostrar_menu(self):
        self._reporte_activo = None
        self._area.clear_widgets()

        scroll = MDScrollView(do_scroll_x=False)
        cuerpo = MDBoxLayout(
            orientation="vertical", adaptive_height=True,
            padding=[dp(12), dp(12), dp(12), dp(80)], spacing=dp(10),
        )

        for tipo, emoji, titulo, desc in _MENU:
            cuerpo.add_widget(self._crear_tarjeta(tipo, emoji, titulo, desc))

        scroll.add_widget(cuerpo)
        self._area.add_widget(scroll)

    def _crear_tarjeta(self, tipo, emoji, titulo, desc):
        card = MDCard(
            orientation="horizontal",
            size_hint_y=None, height=dp(80),
            padding=[dp(12), dp(8), dp(12), dp(8)], spacing=dp(12),
            elevation=2, md_bg_color=_BLANCO,
        )

        caja_icon = MDBoxLayout(size_hint=(None, None), size=(dp(52), dp(52)), md_bg_color=_CAFE)
        caja_icon.radius = [dp(8)]
        caja_icon.add_widget(MDLabel(text=emoji, halign="center", valign="middle", font_size="26sp"))

        textos = MDBoxLayout(orientation="vertical", size_hint_x=1)
        textos.add_widget(MDLabel(
            text=titulo, bold=True, font_style="Body1",
            size_hint_y=None, height=dp(26),
            shorten=True, shorten_from="right",
        ))
        textos.add_widget(MDLabel(
            text=desc, font_style="Body2", theme_text_color="Secondary",
            size_hint_y=None, height=dp(22),
            shorten=True, shorten_from="right",
        ))

        card.add_widget(caja_icon)
        card.add_widget(textos)
        card.bind(on_release=lambda x, t=tipo: self._abrir_reporte(t))
        return card

    # ─── ENCABEZADO DE REPORTE ────────────────────────────────────────────────

    def _abrir_reporte(self, tipo):
        self._reporte_activo = tipo
        self._area.clear_widgets()

        titulos = {
            "inventario":   "📦 Inventario Actual",
            "vencimientos": "⚠️ Vencimientos",
            "movimientos":  "📊 Movimientos",
            "costos":       "💰 Costos por Receta",
            "productos":    "🎁 Productos Terminados",
            "proyeccion":   "🛒 Proyección de Compras",
        }

        barra = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(52),
            padding=[dp(4), dp(4), dp(8), dp(4)], spacing=dp(4), md_bg_color=_CAFE,
        )
        btn_back = MDIconButton(icon="arrow-left", theme_icon_color="Custom", icon_color=_BLANCO)
        btn_back.bind(on_release=lambda x: self._mostrar_menu())

        barra.add_widget(btn_back)
        barra.add_widget(MDLabel(
            text=titulos.get(tipo, tipo), bold=True,
            theme_text_color="Custom", text_color=_BLANCO,
            size_hint_x=1, valign="middle", font_style="Body1",
        ))

        self._btn_exportar = MDIconButton(
            icon="share-variant-outline", theme_icon_color="Custom", icon_color=_DORADO,
        )
        self._btn_exportar.bind(on_release=lambda x: self._exportar_reporte())
        barra.add_widget(self._btn_exportar)

        self._btn_pdf = MDIconButton(
            icon="file-pdf-box", theme_icon_color="Custom", icon_color=_DORADO,
        )
        self._btn_pdf.bind(on_release=lambda x: self._exportar_pdf())
        barra.add_widget(self._btn_pdf)
        self._area.add_widget(barra)

        self._panel = MDBoxLayout(orientation="vertical")
        self._area.add_widget(self._panel)

        {
            "inventario":   self._render_inventario,
            "vencimientos": self._render_vencimientos,
            "movimientos":  self._render_movimientos,
            "costos":       self._render_costos,
            "productos":    self._render_productos,
            "proyeccion":   self._render_proyeccion,
        }[tipo]()

    def _scroll_datos(self):
        sv = MDScrollView(do_scroll_x=False)
        cuerpo = MDBoxLayout(orientation="vertical", adaptive_height=True)
        sv.add_widget(cuerpo)
        self._panel.add_widget(sv)
        return cuerpo

    # ─── 1. INVENTARIO ACTUAL ─────────────────────────────────────────────────

    def _render_inventario(self):
        conn = database.get_connection()
        rows = conn.execute("""
            SELECT mp.nombre, mp.categoria, mp.unidad_medida, mp.stock_minimo,
                   COALESCE(SUM(l.cantidad_actual), 0)                    AS stock,
                   COALESCE(SUM(l.cantidad_actual * l.costo_unitario), 0) AS valor
            FROM materias_primas mp
            LEFT JOIN lotes l ON l.materia_prima_id = mp.id AND l.activo = 1
            WHERE mp.activo = 1 GROUP BY mp.id ORDER BY mp.nombre COLLATE NOCASE
        """).fetchall()
        conn.close()

        self._datos_export = rows
        cuerpo = self._scroll_datos()

        cuerpo.add_widget(_fila_tabla(
            [("Materia Prima", 0.40), ("Cat.", 0.18), ("Stock", 0.22), ("Valor ₡", 0.20)],
            bg=_CAFE, negrita=True,
        ))

        total_valor = 0.0
        for i, r in enumerate(rows):
            stock  = float(r["stock"])
            minimo = float(r["stock_minimo"] or 0)
            valor  = float(r["valor"])
            total_valor += valor

            if stock <= 0:             bg = _ROJO_FONDO
            elif stock < minimo:       bg = _NARANJA_FONDO
            else:                      bg = _GRIS if i % 2 == 0 else _BLANCO

            cuerpo.add_widget(_fila_tabla(
                [(r["nombre"], 0.40), (r["categoria"] or "—", 0.18),
                 (f"{stock:,.2f} {r['unidad_medida']}", 0.22), (f"₡{valor:,.0f}", 0.20)],
                bg=bg,
            ))
            cuerpo.add_widget(MDDivider())

        cuerpo.add_widget(_pie_totales(f"{len(rows)} materias primas  ·  Valor total: ₡{total_valor:,.2f}"))

    # ─── 2. VENCIMIENTOS ─────────────────────────────────────────────────────

    def _render_vencimientos(self):
        conn = database.get_connection()
        vencidos = conn.execute("""
            SELECT l.numero_lote, l.fecha_vencimiento, l.cantidad_actual,
                   mp.nombre, mp.unidad_medida,
                   CAST(julianday('now') - julianday(l.fecha_vencimiento) AS INTEGER) AS dias
            FROM lotes l JOIN materias_primas mp ON mp.id = l.materia_prima_id
            WHERE l.activo = 1 AND l.cantidad_actual > 0 AND l.fecha_vencimiento < date('now')
            ORDER BY l.fecha_vencimiento ASC
        """).fetchall()
        proximos = conn.execute("""
            SELECT l.numero_lote, l.fecha_vencimiento, l.cantidad_actual,
                   mp.nombre, mp.unidad_medida,
                   CAST(julianday(l.fecha_vencimiento) - julianday('now') AS INTEGER) AS dias
            FROM lotes l JOIN materias_primas mp ON mp.id = l.materia_prima_id
            WHERE l.activo = 1 AND l.cantidad_actual > 0
              AND l.fecha_vencimiento BETWEEN date('now') AND date('now', '+30 days')
            ORDER BY l.fecha_vencimiento ASC
        """).fetchall()
        conn.close()

        self._datos_export = {"vencidos": vencidos, "proximos": proximos}
        cuerpo = self._scroll_datos()

        hdrs = [("Producto", 0.38), ("Lote", 0.18), ("Fecha", 0.20), ("Días", 0.10), ("Cant.", 0.14)]

        cuerpo.add_widget(_seccion_titulo(f"⬤ Vencidos ({len(vencidos)})", color=_ROJO))
        cuerpo.add_widget(_fila_tabla(hdrs, bg=_CAFE, negrita=True))
        if not vencidos:
            cuerpo.add_widget(_fila_tabla([("Sin lotes vencidos ✓", 1.0)], bg=_VERDE_FONDO))
        for r in vencidos:
            cuerpo.add_widget(_fila_tabla(
                [(r["nombre"], 0.38), (r["numero_lote"], 0.18),
                 (r["fecha_vencimiento"], 0.20), (f"-{r['dias']}d", 0.10),
                 (f"{float(r['cantidad_actual']):,.2f}", 0.14)],
                bg=_ROJO_FONDO,
            ))
            cuerpo.add_widget(MDDivider())

        cuerpo.add_widget(_seccion_titulo(f"⬤ Próximos 30 días ({len(proximos)})", color=_NARANJA))
        cuerpo.add_widget(_fila_tabla(hdrs, bg=_CAFE, negrita=True))
        if not proximos:
            cuerpo.add_widget(_fila_tabla([("Sin vencimientos próximos ✓", 1.0)], bg=_VERDE_FONDO))
        for r in proximos:
            cuerpo.add_widget(_fila_tabla(
                [(r["nombre"], 0.38), (r["numero_lote"], 0.18),
                 (r["fecha_vencimiento"], 0.20), (f"{r['dias']}d", 0.10),
                 (f"{float(r['cantidad_actual']):,.2f}", 0.14)],
                bg=_NARANJA_FONDO,
            ))
            cuerpo.add_widget(MDDivider())

    # ─── 3. MOVIMIENTOS ──────────────────────────────────────────────────────

    def _render_movimientos(self):
        filtros = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(68),
            padding=[dp(8), dp(4)], spacing=dp(6), md_bg_color=_BLANCO,
        )

        self._tf_desde = MDTextField(
            text=self._fecha_desde, hint_text="Desde",
            mode="rectangle", size_hint_x=0.35, size_hint_y=None, height=dp(56),
        )
        btn_cal_d = MDIconButton(
            icon="calendar-start", theme_icon_color="Custom", icon_color=_CAFE,
            size_hint_x=None, width=dp(36),
        )
        btn_cal_d.bind(on_release=lambda x: self._picker_fecha(self._tf_desde))

        self._tf_hasta = MDTextField(
            text=self._fecha_hasta, hint_text="Hasta",
            mode="rectangle", size_hint_x=0.35, size_hint_y=None, height=dp(56),
        )
        btn_cal_h = MDIconButton(
            icon="calendar-end", theme_icon_color="Custom", icon_color=_CAFE,
            size_hint_x=None, width=dp(36),
        )
        btn_cal_h.bind(on_release=lambda x: self._picker_fecha(self._tf_hasta))

        btn_filtrar = MDFlatButton(
            text="Filtrar",
            theme_text_color="Custom", text_color=_CAFE,
        )
        btn_filtrar.bind(on_release=lambda x: self._cargar_movimientos())

        for w in [self._tf_desde, btn_cal_d, self._tf_hasta, btn_cal_h, btn_filtrar]:
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
            FROM movimientos m JOIN materias_primas mp ON mp.id = m.materia_prima_id
            WHERE m.fecha BETWEEN ? AND ? ORDER BY m.fecha DESC, m.id DESC
        """, (f_desde, f_hasta)).fetchall()
        conn.close()

        self._datos_export = rows
        hdrs = [("Fecha", 0.22), ("Tipo", 0.12), ("Materia Prima", 0.36), ("Cant.", 0.15), ("₡/u", 0.15)]

        entradas = [r for r in rows if r["tipo"] == "ingreso"]
        salidas  = [r for r in rows if r["tipo"] == "salida"]
        total_ent = sum(float(r["cantidad"]) * float(r["costo_unitario"] or 0) for r in entradas)
        total_sal = sum(float(r["cantidad"]) * float(r["costo_unitario"] or 0) for r in salidas)

        for tipo_s, subset, bg_fila, color_sec in [
            ("Entradas", entradas, _VERDE_FONDO, _VERDE),
            ("Salidas",  salidas,  _NARANJA_FONDO, _NARANJA),
        ]:
            total = total_ent if tipo_s == "Entradas" else total_sal
            self._cuerpo_mov.add_widget(_seccion_titulo(f"{tipo_s} ({len(subset)})  —  ₡{total:,.2f}", color=color_sec))
            self._cuerpo_mov.add_widget(_fila_tabla(hdrs, bg=_CAFE, negrita=True))
            if not subset:
                self._cuerpo_mov.add_widget(_fila_tabla([("Sin registros en este período", 1.0)], bg=_GRIS))
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
        picker = MDDatePicker()
        picker.bind(on_save=lambda inst, val, rng: self._set_fecha(val, tf))
        picker.open()

    def _set_fecha(self, value, tf):
        tf.text = value.strftime("%Y-%m-%d")

    # ─── 4. COSTOS POR RECETA ────────────────────────────────────────────────

    def _render_costos(self):
        conn = database.get_connection()
        recetas = conn.execute(
            "SELECT r.id, r.nombre, r.porciones FROM recetas r WHERE r.activo = 1 ORDER BY r.nombre COLLATE NOCASE"
        ).fetchall()

        resultado = []
        for rec in recetas:
            ings = conn.execute(
                "SELECT ri.materia_prima_id, ri.cantidad FROM receta_ingredientes ri WHERE ri.receta_id = ?",
                (rec["id"],)
            ).fetchall()
            costo_batch = sum(
                ing["cantidad"] * database.get_costo_promedio_ponderado(ing["materia_prima_id"], conn)
                for ing in ings
            )
            porciones  = float(rec["porciones"] or 1)
            costo_porc = costo_batch / porciones if porciones > 0 else 0

            prec_row = conn.execute("""
                SELECT AVG(pt.precio_venta) AS precio_prom, AVG(pt.margen_ganancia) AS margen_prom
                FROM productos_terminados pt JOIN salidas s ON s.id = pt.salida_id
                WHERE s.receta_id = ? AND pt.precio_venta > 0
            """, (rec["id"],)).fetchone()
            precio_prom = float(prec_row["precio_prom"] or 0)
            margen_prom = float(prec_row["margen_prom"] or 0)

            resultado.append({
                "nombre": rec["nombre"], "porciones": porciones,
                "costo_batch": costo_batch, "costo_porc": costo_porc,
                "precio_prom": precio_prom, "margen_prom": margen_prom,
            })
        conn.close()

        self._datos_export = resultado
        cuerpo = self._scroll_datos()

        cuerpo.add_widget(_fila_tabla(
            [("Receta", 0.34), ("Porciones", 0.14), ("Costo/u ₡", 0.20), ("Precio ₡", 0.16), ("Margen", 0.16)],
            bg=_CAFE, negrita=True,
        ))

        for i, r in enumerate(resultado):
            m = r["margen_prom"]
            if m >= 30:   bg = _VERDE_FONDO;   semal = "🟢"
            elif m >= 10: bg = _NARANJA_FONDO; semal = "🟡"
            elif m > 0:   bg = _ROJO_FONDO;    semal = "🔴"
            else:         bg = _GRIS if i % 2 == 0 else _BLANCO; semal = "—"

            margen_txt = f"{semal} {m:.1f}%" if m > 0 else "—"
            precio_txt = f"₡{r['precio_prom']:,.0f}" if r["precio_prom"] > 0 else "—"

            cuerpo.add_widget(_fila_tabla(
                [(r["nombre"], 0.34), (f"{r['porciones']:.0f}", 0.14),
                 (f"₡{r['costo_porc']:,.2f}", 0.20), (precio_txt, 0.16), (margen_txt, 0.16)],
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
            FROM productos_terminados ORDER BY fecha_produccion DESC
        """).fetchall()
        conn.close()

        self._datos_export = rows
        cuerpo = self._scroll_datos()

        cuerpo.add_widget(_fila_tabla(
            [("Producto", 0.34), ("Cant.", 0.10), ("Costo ₡", 0.18), ("Precio ₡", 0.18), ("Vto.", 0.20)],
            bg=_CAFE, negrita=True,
        ))

        hoy   = date.today().isoformat()
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

            if vto and vto < hoy:          bg = _ROJO_FONDO;    vto_txt = f"❌ {vto}"
            elif vto and vto <= lim30:     bg = _NARANJA_FONDO; vto_txt = f"⚠ {vto}"
            else:                          bg = _GRIS if i % 2 == 0 else _BLANCO; vto_txt = vto or "—"

            cant_s = str(int(cant)) if cant == int(cant) else f"{cant:.2f}"
            cuerpo.add_widget(_fila_tabla(
                [(r["nombre"], 0.34), (cant_s, 0.10),
                 (f"₡{cu:,.0f}", 0.18), (f"₡{pv:,.0f}", 0.18), (vto_txt, 0.20)],
                bg=bg,
            ))
            cuerpo.add_widget(MDDivider())

        cuerpo.add_widget(_pie_totales(f"Costo stock: ₡{total_costo:,.2f}  ·  Valor venta: ₡{total_venta:,.2f}"))

    # ─── 6. PROYECCIÓN DE COMPRAS ─────────────────────────────────────────────

    def _render_proyeccion(self):
        filtros = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(68),
            padding=[dp(8), dp(4)], spacing=dp(8), md_bg_color=_BLANCO,
        )
        self._tf_dias_proy = MDTextField(
            text=str(self._dias_proyeccion), hint_text="Analizar últimos X días",
            mode="rectangle", size_hint_x=0.4, size_hint_y=None, height=dp(56),
            input_type="number",
        )
        btn_calc = MDFlatButton(
            text="Calcular", theme_text_color="Custom", text_color=_CAFE,
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
                 FROM lotes l WHERE l.materia_prima_id = mp.id AND l.activo = 1) AS stock_actual,
                (SELECT COALESCE(SUM(m.cantidad), 0)
                 FROM movimientos m
                 WHERE m.materia_prima_id = mp.id AND m.tipo = 'salida'
                   AND m.fecha >= date('now', '-' || ? || ' days')) AS consumido
            FROM materias_primas mp WHERE mp.activo = 1
            ORDER BY mp.nombre COLLATE NOCASE
        """, (dias,)).fetchall()
        conn.close()

        self._datos_export = rows
        hdrs = [("Materia Prima", 0.30), ("Stock", 0.16), ("Cons./día", 0.16), ("Días stock", 0.14), ("Sugerido", 0.24)]
        self._cuerpo_proy.add_widget(_fila_tabla(hdrs, bg=_CAFE, negrita=True))

        for i, r in enumerate(rows):
            stock  = float(r["stock_actual"])
            consum = float(r["consumido"])
            cons_d = consum / dias if dias > 0 else 0.0

            if cons_d > 0:
                dias_stock = stock / cons_d
                sugerido   = max(0.0, cons_d * 60 - stock)
            else:
                dias_stock = 999
                sugerido   = 0.0

            if stock <= 0 or (cons_d > 0 and dias_stock < 7): bg = _ROJO_FONDO
            elif cons_d > 0 and dias_stock < 30:               bg = _NARANJA_FONDO
            else:                                              bg = _GRIS if i % 2 == 0 else _BLANCO

            u   = r["unidad_medida"] or ""
            ds  = f"{dias_stock:.0f} d" if dias_stock < 999 else "—"
            sug = f"{sugerido:.2f} {u}" if sugerido > 0 else "OK"

            self._cuerpo_proy.add_widget(_fila_tabla(
                [(r["nombre"], 0.30), (f"{stock:,.2f} {u}", 0.16),
                 (f"{cons_d:,.4f}/d", 0.16), (ds, 0.14), (sug, 0.24)],
                bg=bg,
            ))
            self._cuerpo_proy.add_widget(MDDivider())

        urgentes = sum(
            1 for r in rows
            if float(r["stock_actual"]) <= 0
            or (float(r["consumido"]) > 0
                and float(r["stock_actual"]) / (float(r["consumido"]) / dias) < 7)
        )
        self._cuerpo_proy.add_widget(_pie_totales(f"Basado en {dias} días  ·  {urgentes} material(es) urgente(s)"))

    # ─── EXPORTAR ─────────────────────────────────────────────────────────────

    def _exportar_reporte(self):
        texto = self._generar_texto_export()
        if _ANDROID:
            try:
                intent = Intent()
                intent.setAction(Intent.ACTION_SEND)
                intent.putExtra(Intent.EXTRA_TEXT, texto)
                intent.setType("text/plain")
                mActivity.startActivity(Intent.createChooser(intent, "Compartir reporte"))
                return
            except Exception:
                pass

        sv = MDScrollView(size_hint_y=None, height=Window.height * 0.50, do_scroll_x=False)
        lbl = MDLabel(
            text=texto, size_hint_y=None, font_style="Body2",
            padding=[dp(8), dp(4)],
        )
        lbl.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        sv.add_widget(lbl)

        def _copiar(x):
            Clipboard.copy(texto)
            try:
                MDSnackbar(text="✅ Copiado al portapapeles", duration=2).open()
            except Exception:
                pass

        self._dialogo_export = MDDialog(
            title="📄 Exportar reporte",
            type="custom",
            content_cls=sv,
            buttons=[
                MDFlatButton(text="📋 Copiar", theme_text_color="Custom", text_color=_DORADO, on_release=_copiar),
                MDFlatButton(text="Cerrar", on_release=lambda x: self._dialogo_export.dismiss()),
            ],
        )
        self._dialogo_export.open()

    def _generar_texto_export(self) -> str:
        hoy   = date.today().isoformat()
        sep   = "─" * 42
        lineas = [f"REPORTE — {self._reporte_activo.upper()}", f"Generado: {hoy}", sep]

        tipo  = self._reporte_activo
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
            for sec, rows in [("VENCIDOS", datos["vencidos"]), ("PRÓXIMOS 30 DÍAS", datos["proximos"])]:
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
            lineas.append(f"{'Materia Prima':<26} {'Stock':>8} {'Días':>6} {'Sugerido':>12}")
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
        if _ANDROID:
            self._exportar_txt_android()
            return

        if not _REPORTLAB:
            try:
                MDSnackbar(
                    text="❌ reportlab no instalado. Ejecute: pip install reportlab",
                    duration=5,
                ).open()
            except Exception:
                pass
            return

        carpeta = Path.home() / "Documents" / "Panaderia"
        try:
            carpeta.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.show_snack(f"❌ No se pudo crear la carpeta: {e}")
            return

        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = str(carpeta / f"reporte_{self._reporte_activo}_{ts}.pdf")

        try:
            self._generar_pdf(ruta)
            _subproc.Popen(["xdg-open", ruta])
            self.show_snack("✅ PDF guardado en Documents/Panaderia/")
        except Exception as e:
            self.show_snack(f"❌ Error al generar PDF: {e}")

    def _exportar_txt_android(self):
        texto = self._generar_texto_export()
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            from android.storage import primary_external_storage_path  # type: ignore
            base = primary_external_storage_path()
        except Exception:
            base = "/sdcard"

        carpeta = os.path.join(base, "Documents", "Panaderia")
        try:
            os.makedirs(carpeta, exist_ok=True)
        except Exception as e:
            self.show_snack(f"❌ No se pudo crear la carpeta: {e}")
            return

        nombre = f"reporte_{self._reporte_activo}_{ts}.txt"
        ruta   = os.path.join(carpeta, nombre)

        try:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(texto)
        except Exception as e:
            self.show_snack(f"❌ Error al guardar archivo: {e}")
            return

        try:
            from android.content import Intent                       # type: ignore
            from androidx.core.content import FileProvider           # type: ignore
            from android import mActivity                            # type: ignore
            from java.io import File                                 # type: ignore
            jfile   = File(ruta)
            uri     = FileProvider.getUriForFile(
                mActivity, mActivity.getPackageName() + ".provider", jfile
            )
            intent  = Intent(Intent.ACTION_SEND)
            intent.setType("text/plain")
            intent.putExtra(Intent.EXTRA_STREAM, uri)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            mActivity.startActivity(Intent.createChooser(intent, "Compartir reporte"))
        except Exception:
            self.show_snack(f"✅ Guardado en {ruta}")

    def _generar_pdf(self, ruta: str):
        """Genera un PDF simple del reporte activo usando reportlab."""
        doc = SimpleDocTemplate(ruta, pagesize=_rl_landscape(A4))
        styles = getSampleStyleSheet()
        story  = []

        normal = ParagraphStyle("normal", fontName=_FUENTE, fontSize=9, leading=11)
        titulo_style = ParagraphStyle("titulo", fontName=_FUENTE_B, fontSize=13, leading=15, spaceAfter=6)
        cabecera_style = ParagraphStyle("cab", fontName=_FUENTE_B, fontSize=9, leading=11,
                                        textColor=_rl_colors.white, backColor=_rl_colors.HexColor("#3E2723"))

        story.append(Paragraph(f"Panadería — Reporte: {self._reporte_activo.upper()}", titulo_style))
        story.append(Paragraph(f"Generado: {date.today().isoformat()}", normal))
        story.append(Spacer(1, 0.3 * _cm))

        texto = self._generar_texto_export()
        for linea in texto.split("\n"):
            story.append(Paragraph(linea or " ", normal))

        doc.build(story)
