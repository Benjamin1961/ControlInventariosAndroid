"""
database.py — Conexión SQLite y lógica de base de datos.
Compatible con el proyecto de escritorio (misma estructura).
"""

import sqlite3
import os


def _get_db_path():
    try:
        from android.storage import app_storage_path  # type: ignore
        return os.path.join(app_storage_path(), 'inventario_panaderia.db')
    except ImportError:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventario_panaderia.db')


DB_PATH = _get_db_path()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS proveedores (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre           TEXT    NOT NULL,
            ruc_cedula       TEXT,
            telefono         TEXT,
            correo           TEXT,
            direccion        TEXT,
            condiciones_pago TEXT,
            activo           INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS materias_primas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre        TEXT    NOT NULL,
            descripcion   TEXT,
            unidad_medida TEXT    NOT NULL,
            stock_minimo  REAL    DEFAULT 0,
            categoria     TEXT,
            proveedor_id  INTEGER REFERENCES proveedores(id),
            activo        INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS lotes (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_lote       TEXT    NOT NULL,
            fecha_ingreso     TEXT    NOT NULL,
            fecha_vencimiento TEXT,
            cantidad_inicial  REAL    NOT NULL,
            cantidad_actual   REAL    NOT NULL,
            costo_unitario    REAL    NOT NULL,
            proveedor_id      INTEGER REFERENCES proveedores(id),
            materia_prima_id  INTEGER NOT NULL REFERENCES materias_primas(id),
            activo            INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS movimientos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo             TEXT    NOT NULL,
            fecha            TEXT    NOT NULL,
            materia_prima_id INTEGER NOT NULL REFERENCES materias_primas(id),
            lote_id          INTEGER REFERENCES lotes(id),
            cantidad         REAL    NOT NULL,
            costo_unitario   REAL,
            referencia       TEXT,
            observaciones    TEXT
        );

        CREATE TABLE IF NOT EXISTS recetas (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre            TEXT    NOT NULL,
            descripcion       TEXT,
            porciones         REAL    DEFAULT 1,
            unidad_produccion TEXT,
            activo            INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS receta_ingredientes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            receta_id        INTEGER NOT NULL REFERENCES recetas(id) ON DELETE CASCADE,
            materia_prima_id INTEGER NOT NULL REFERENCES materias_primas(id),
            cantidad         REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS salidas (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            receta_id          INTEGER NOT NULL REFERENCES recetas(id),
            fecha              TEXT    NOT NULL,
            cantidad_producida REAL    NOT NULL,
            costo_total        REAL    DEFAULT 0,
            observaciones      TEXT
        );

        CREATE TABLE IF NOT EXISTS salida_detalle (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            salida_id        INTEGER NOT NULL REFERENCES salidas(id) ON DELETE CASCADE,
            lote_id          INTEGER NOT NULL REFERENCES lotes(id),
            materia_prima_id INTEGER NOT NULL REFERENCES materias_primas(id),
            cantidad         REAL    NOT NULL,
            costo_unitario   REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS productos_terminados (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre            TEXT    NOT NULL,
            salida_id         INTEGER REFERENCES salidas(id),
            cantidad          REAL    NOT NULL,
            costo_unitario    REAL    DEFAULT 0,
            costo_total       REAL    DEFAULT 0,
            fecha_produccion  TEXT    NOT NULL,
            fecha_vencimiento TEXT,
            observaciones     TEXT
        );
    """)
    conn.commit()

    def _columna_existe(tabla, columna):
        c.execute(f"PRAGMA table_info({tabla})")
        return any(row[1] == columna for row in c.fetchall())

    migraciones = [
        ("productos_terminados", "margen_ganancia", "REAL DEFAULT 0"),
        ("productos_terminados", "precio_venta",    "REAL DEFAULT 0"),
        ("materias_primas",      "fecha_registro",  "TEXT"),
        ("recetas",              "porciones",       "REAL DEFAULT 1"),
    ]
    for tabla, columna, definicion in migraciones:
        if not _columna_existe(tabla, columna):
            c.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
            conn.commit()

    if _columna_existe("materias_primas", "fecha_registro"):
        c.execute("UPDATE materias_primas SET fecha_registro = date('now') WHERE fecha_registro IS NULL")
        conn.commit()

    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Lógica PEPS (FIFO)
# ─────────────────────────────────────────────────────────────────────────────

def consumir_peps(materia_prima_id: int, cantidad_total: float, conn) -> list:
    """
    Calcula el consumo PEPS (FIFO) para una materia prima.
    NO modifica la base de datos; solo retorna la lista de consumos.
    """
    c = conn.cursor()
    c.execute("""
        SELECT id, numero_lote, cantidad_actual, costo_unitario
        FROM   lotes
        WHERE  materia_prima_id = ?
          AND  cantidad_actual  > 0
          AND  activo           = 1
        ORDER  BY fecha_ingreso ASC, id ASC
    """, (materia_prima_id,))
    lotes = c.fetchall()

    disponible = sum(float(l['cantidad_actual']) for l in lotes)
    if disponible < cantidad_total - 1e-9:
        c.execute("SELECT nombre FROM materias_primas WHERE id=?", (materia_prima_id,))
        mp = c.fetchone()
        nombre = mp['nombre'] if mp else f'ID {materia_prima_id}'
        raise ValueError(
            f"Stock insuficiente para «{nombre}».\n"
            f"Disponible: {disponible:.4f} — Requerido: {cantidad_total:.4f}"
        )

    consumos = []
    restante = cantidad_total
    for lote in lotes:
        if restante <= 1e-9:
            break
        tomar = min(float(lote['cantidad_actual']), restante)
        consumos.append({
            'lote_id':        lote['id'],
            'cantidad':       tomar,
            'costo_unitario': float(lote['costo_unitario']),
        })
        restante -= tomar

    return consumos


def get_stock_actual(materia_prima_id: int, conn) -> float:
    c = conn.cursor()
    c.execute("""
        SELECT COALESCE(SUM(cantidad_actual), 0)
        FROM   lotes
        WHERE  materia_prima_id = ? AND activo = 1
    """, (materia_prima_id,))
    return float(c.fetchone()[0])


def get_costo_promedio_ponderado(materia_prima_id: int, conn) -> float:
    c = conn.cursor()
    c.execute("""
        SELECT SUM(cantidad_actual * costo_unitario) AS valor,
               SUM(cantidad_actual)                 AS qty
        FROM   lotes
        WHERE  materia_prima_id = ? AND activo = 1 AND cantidad_actual > 0
    """, (materia_prima_id,))
    row = c.fetchone()
    if row and row['qty'] and float(row['qty']) > 0:
        return float(row['valor']) / float(row['qty'])
    return 0.0
