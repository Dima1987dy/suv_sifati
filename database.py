"""
database.py
SQLite bazasi: jadval yaratish, CRUD operatsiyalar.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional


def _resolve_db_path() -> Path:
    """
    Foydalanuvchiga tegishli papkada DB yo'lini qaytaradi.
      Windows : %APPDATA%\\SuvSifati\\water_quality.db
      Linux   : ~/.local/share/SuvSifati/water_quality.db
      macOS   : ~/.local/share/SuvSifati/water_quality.db

    Papka mavjud bo'lmasa avtomatik yaratiladi.
    Eski DB (loyiha papkasida) mavjud bo'lsa yangi joyga ko'chiriladi.
    """
    if os.name == "nt":                          # Windows
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:                                        # Linux / macOS
        base = Path.home() / ".local" / "share"

    app_dir = base / "SuvSifati"
    app_dir.mkdir(parents=True, exist_ok=True)
    new_path = app_dir / "water_quality.db"

    # Eski DB ni yangi joyga ko'chirish (bir martalik migratsiya)
    old_path = Path(__file__).parent / "water_quality.db"
    if old_path.exists() and not new_path.exists():
        old_path.rename(new_path)

    return new_path


DB_PATH = _resolve_db_path()


# ─────────────────────────────────────────────
#  Ulanish
# ─────────────────────────────────────────────
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # natijani dict kabi o'qish uchun
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────
#  Jadvallar yaratish
# ─────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,           -- loyiha nomi: "P daryosi, A kresimi"
    description TEXT    DEFAULT '',
    created_at  TEXT    DEFAULT (date('now'))
);

-- Kuzatuv nuqtalari (bir loyihada bir nechta nuqta bo'lishi mumkin)
CREATE TABLE IF NOT EXISTS monitoring_stations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,           -- "A kresimi yuqori", "B kresimi"
    latitude    REAL,                       -- kenglik
    longitude   REAL,                       -- uzunlik
    river       TEXT    DEFAULT '',         -- daryo nomi
    region      TEXT    DEFAULT '',         -- viloyat/tuman
    description TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS substances (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    mpc         REAL    NOT NULL,
    unit        TEXT    DEFAULT 'mg/dm3',
    hazard_class INTEGER DEFAULT 3,
    is_oxygen   INTEGER DEFAULT 0,
    order_index INTEGER DEFAULT 999
);

CREATE TABLE IF NOT EXISTS measurements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(id)   ON DELETE CASCADE,
    station_id      INTEGER REFERENCES monitoring_stations(id) ON DELETE SET NULL,
    substance_id    INTEGER NOT NULL REFERENCES substances(id) ON DELETE CASCADE,
    sample_date     TEXT    NOT NULL,       -- "2023-01-14"
    concentration   REAL,                   -- NULL = aniqlanmagan
    year            INTEGER GENERATED ALWAYS AS (CAST(substr(sample_date, 1, 4) AS INTEGER)) VIRTUAL
);

CREATE TABLE IF NOT EXISTS results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    year        INTEGER NOT NULL,
    substance_id INTEGER REFERENCES substances(id) ON DELETE SET NULL,
    -- har bir modda uchun oraliq ko'rsatkichlar
    ni          INTEGER,        -- o'lchovlar soni
    ni_exceed   INTEGER,        -- MPC oshgan soni
    alpha       REAL,           -- takroriylik, %
    beta_avg    REAL,           -- o'rtacha oshish karraligi
    s_alpha     REAL,           -- E-ilova ball
    s_beta      REAL,           -- J-ilova ball
    s_ij        REAL,           -- umumlashtirilgan ball
    -- yakuniy (faqat substance_id NULL bo'lsa — butun loyiha uchun)
    ki          REAL,           -- Kombinatör indeks
    ski         REAL,           -- Solishtirma kombinatör indeks
    f_count     INTEGER,        -- kritik ko'rsatkichlar soni
    k_reserve   REAL,           -- zaxira koeffitsienti
    water_class INTEGER,        -- sinf 1-5
    class_label TEXT,           -- "Shartli toza", "Iflos", ...
    UNIQUE(project_id, year, substance_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_meas_unique
    ON measurements(project_id, substance_id, sample_date);

CREATE INDEX IF NOT EXISTS idx_meas_proj_year
    ON measurements(project_id, year);
"""


def init_db() -> None:
    """Baza yo'q bo'lsa yaratadi, jadvallarni sozlaydi."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)


# ─────────────────────────────────────────────
#  projects  CRUD
# ─────────────────────────────────────────────
def add_project(name: str, description: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name.strip(), description.strip()),
        )
        return cur.lastrowid


def get_all_projects() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()


def get_project(project_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()


def update_project(project_id: int, name: str, description: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE projects SET name=?, description=? WHERE id=?",
            (name.strip(), description.strip(), project_id),
        )


def delete_project(project_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


# ─────────────────────────────────────────────
#  monitoring_stations  CRUD
# ─────────────────────────────────────────────
def add_station(project_id: int, name: str,
                latitude: float | None = None,
                longitude: float | None = None,
                river: str = "", region: str = "",
                description: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO monitoring_stations
               (project_id, name, latitude, longitude, river, region, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project_id, name.strip(), latitude, longitude,
             river.strip(), region.strip(), description.strip()),
        )
        return cur.lastrowid


def get_stations(project_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            """SELECT * FROM monitoring_stations
               WHERE project_id = ? ORDER BY name""",
            (project_id,),
        ).fetchall()


def get_station(station_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM monitoring_stations WHERE id = ?",
            (station_id,),
        ).fetchone()


def update_station(station_id: int, name: str,
                   latitude: float | None, longitude: float | None,
                   river: str, region: str, description: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE monitoring_stations
               SET name=?, latitude=?, longitude=?, river=?, region=?, description=?
               WHERE id=?""",
            (name.strip(), latitude, longitude,
             river.strip(), region.strip(), description.strip(), station_id),
        )


def delete_station(station_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM monitoring_stations WHERE id = ?", (station_id,)
        )


def get_all_stations_with_results() -> list[sqlite3.Row]:
    """Xarita uchun: har bir stansiya FAQAT BIR MARTA, oxirgi yil sinfi bilan."""
    with get_connection() as conn:
        return conn.execute(
            """SELECT ms.id, ms.name, ms.latitude, ms.longitude,
                      ms.river, ms.region, ms.project_id,
                      p.name as project_name,
                      r.water_class, r.class_label, r.ski,
                      r.year as result_year
               FROM monitoring_stations ms
               JOIN projects p ON p.id = ms.project_id
               LEFT JOIN results r
                   ON  r.project_id    = ms.project_id
                   AND r.substance_id  IS NULL
                   AND r.year = (
                       SELECT MAX(r2.year)
                       FROM results r2
                       WHERE r2.project_id   = ms.project_id
                         AND r2.substance_id IS NULL
                   )
               WHERE ms.latitude IS NOT NULL AND ms.longitude IS NOT NULL
               ORDER BY ms.id""",
        ).fetchall()


# ─────────────────────────────────────────────
#  substances  CRUD
# ─────────────────────────────────────────────
def add_substance(name: str, mpc: float, unit: str = "mg/dm3",
                  hazard_class: int = 3, is_oxygen: bool = False) -> int:
    with get_connection() as conn:
        # Yangi modda oxiriga qo'shiladi
        max_order = conn.execute(
            "SELECT COALESCE(MAX(order_index),0) FROM substances"
        ).fetchone()[0]
        cur = conn.execute(
            """INSERT INTO substances
               (name, mpc, unit, hazard_class, is_oxygen, order_index)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name.strip(), mpc, unit, hazard_class,
             int(is_oxygen), max_order + 1),
        )
        return cur.lastrowid


def get_all_substances() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM substances ORDER BY order_index, id"
        ).fetchall()


def get_substance(substance_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM substances WHERE id = ?", (substance_id,)
        ).fetchone()


def swap_substance_order(id1: int, id2: int) -> None:
    """Ikki moddaning order_index ini almashtiradi."""
    with get_connection() as conn:
        o1 = conn.execute(
            "SELECT order_index FROM substances WHERE id=?", (id1,)
        ).fetchone()
        o2 = conn.execute(
            "SELECT order_index FROM substances WHERE id=?", (id2,)
        ).fetchone()
        if o1 and o2:
            conn.execute(
                "UPDATE substances SET order_index=? WHERE id=?",
                (o2["order_index"], id1))
            conn.execute(
                "UPDATE substances SET order_index=? WHERE id=?",
                (o1["order_index"], id2))


def reindex_substances() -> None:
    """Barcha moddalarni tartib raqamini 1 dan boshlab qayta belgilaydi."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM substances ORDER BY order_index, id"
        ).fetchall()
        for i, row in enumerate(rows, start=1):
            conn.execute(
                "UPDATE substances SET order_index=? WHERE id=?",
                (i, row["id"]))


def update_substance(substance_id: int, name: str, mpc: float,
                     unit: str, hazard_class: int, is_oxygen: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE substances
               SET name=?, mpc=?, unit=?, hazard_class=?, is_oxygen=?
               WHERE id=?""",
            (name.strip(), mpc, unit, hazard_class, int(is_oxygen), substance_id),
        )


def delete_substance(substance_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM substances WHERE id = ?", (substance_id,))


def seed_default_substances() -> None:
    """
    Qo'llanmaning V-ilovasi (majburiy ro'yxat №1) asosida
    standart moddalar. Agar allaqachon mavjud bo'lsa, o'tkazib yuboradi.
    """
    defaults = [
        # (order, name,                  mpc,    unit,     hazard, is_oxygen)
        (1,  "O2 (Kislorod)",        4.0,    "mg/dm3", 4, True),
        (2,  "KBT5",                 2.0,    "mg/dm3", 4, False),
        (3,  "KKT",                  15.0,   "mg/dm3", 4, False),
        (4,  "Fenol",                0.001,  "mg/dm3", 2, False),
        (5,  "Neft mahsulotlari",    0.05,   "mg/dm3", 4, False),
        (6,  "N-NO2-",               0.02,   "mg/dm3", 3, False),
        (7,  "N-NO3-",               9.1,    "mg/dm3", 3, False),
        (8,  "N-NH4+",               0.5,    "mg/dm3", 3, False),
        (9,  "Temir umumiy (Feум)",  0.1,    "mg/dm3", 3, False),
        (10, "Mis (Cu)",             0.001,  "mg/dm3", 2, False),
        (11, "Rux (Zn)",             0.01,   "mg/dm3", 3, False),
        (12, "Xrom (Cr)",            0.002,  "mg/dm3", 2, False),
        (13, "Kadmiy (Cd)",          0.005,  "mg/dm3", 2, False),
        (14, "Qo'rg'oshin (Pb)",   0.006,  "mg/dm3", 2, False),
        (15, "Xloridlar (Cl-)",      300.0,  "mg/dm3", 4, False),
        (16, "Sulfatlar (SO42-)",    100.0,  "mg/dm3", 4, False),
        (17, "SSFM",                 0.1,    "mg/dm3", 4, False),
        (18, "Mineralizatsiya",      1000.0, "mg/dm3", 4, False),
        (19, "Ca2+",                 180.0,  "mg/dm3", 4, False),
        (20, "Mg2+",                 40.0,   "mg/dm3", 4, False),
        (21, "Na+",                  120.0,  "mg/dm3", 4, False),
        (22, "Nikel (Ni)",           0.01,   "mg/dm3", 3, False),
    ]
    with get_connection() as conn:
        for row in defaults:
            order_idx = row[0]
            data      = row[1:]
            conn.execute(
                """INSERT OR IGNORE INTO substances
                   (name, mpc, unit, hazard_class, is_oxygen, order_index)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (*data, order_idx),
            )


# ─────────────────────────────────────────────
#  measurements  CRUD
# ─────────────────────────────────────────────
def add_measurement(project_id: int, substance_id: int,
                    sample_date: str, concentration: Optional[float]) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO measurements
               (project_id, substance_id, sample_date, concentration)
               VALUES (?, ?, ?, ?)""",
            (project_id, substance_id, sample_date, concentration),
        )
        return cur.lastrowid


def add_measurements_bulk(rows: list[tuple]) -> None:
    """
    Ko'p qator bir vaqtda qo'shish.
    rows = [(project_id, substance_id, sample_date, concentration), ...]
    Agar shu project_id + substance_id + sample_date allaqachon mavjud bo'lsa,
    concentration yangilanadi (UPSERT).
    """
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO measurements
               (project_id, substance_id, sample_date, concentration)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(project_id, substance_id, sample_date)
               DO UPDATE SET concentration=excluded.concentration""",
            rows,
        )


def add_measurements_with_station(rows: list[tuple]) -> None:
    """
    Stansiya ID bilan ko'p qator qo'shish.
    Agar shu sana + modda allaqachon bo'lsa — yangilaydi (UPSERT).
    rows = [(project_id, station_id, substance_id, sample_date, concentration), ...]
    """
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO measurements
               (project_id, station_id, substance_id, sample_date, concentration)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(project_id, substance_id, sample_date)
               DO UPDATE SET
                   concentration=excluded.concentration,
                   station_id=excluded.station_id""",
            rows,
        )


def get_monthly_status(project_id: int, year: int,
                       station_id: int | None = None) -> dict:
    """
    Har oy uchun nechta namuna kiritilganini qaytaradi.
    Qaytaradi: {1: 5, 2: 0, 3: 8, ...}  (oy: modda soni)
    """
    with get_connection() as conn:
        if station_id:
            rows = conn.execute(
                """SELECT CAST(substr(sample_date,6,2) AS INTEGER) as month,
                          COUNT(DISTINCT substance_id) as cnt
                   FROM measurements
                   WHERE project_id=? AND year=? AND station_id=?
                     AND concentration IS NOT NULL
                   GROUP BY month""",
                (project_id, year, station_id)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT CAST(substr(sample_date,6,2) AS INTEGER) as month,
                          COUNT(DISTINCT substance_id) as cnt
                   FROM measurements
                   WHERE project_id=? AND year=?
                     AND concentration IS NOT NULL
                   GROUP BY month""",
                (project_id, year)
            ).fetchall()
        return {r["month"]: r["cnt"] for r in rows}


def get_measurements(project_id: int, year: int,
                     substance_id: Optional[int] = None) -> list[sqlite3.Row]:
    """Loyiha + yil bo'yicha o'lchovlarni qaytaradi."""
    with get_connection() as conn:
        if substance_id is None:
            return conn.execute(
                """SELECT m.*, s.name as sub_name, s.mpc, s.is_oxygen
                   FROM measurements m
                   JOIN substances s ON s.id = m.substance_id
                   WHERE m.project_id = ? AND m.year = ?
                   ORDER BY m.substance_id, m.sample_date""",
                (project_id, year),
            ).fetchall()
        else:
            return conn.execute(
                """SELECT m.*, s.name as sub_name, s.mpc, s.is_oxygen
                   FROM measurements m
                   JOIN substances s ON s.id = m.substance_id
                   WHERE m.project_id = ? AND m.year = ?
                     AND m.substance_id = ?
                   ORDER BY m.sample_date""",
                (project_id, year, substance_id),
            ).fetchall()


def get_available_years(project_id: int) -> list[int]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT DISTINCT year FROM measurements
               WHERE project_id = ?
               ORDER BY year""",
            (project_id,),
        ).fetchall()
        return [r["year"] for r in rows]


def get_measurement(measurement_id: int) -> Optional[sqlite3.Row]:
    """Bitta o'lchovni id bo'yicha qaytaradi."""
    with get_connection() as conn:
        return conn.execute(
            """SELECT m.*, s.name as sub_name, s.mpc, s.is_oxygen, s.unit
               FROM measurements m
               JOIN substances s ON s.id = m.substance_id
               WHERE m.id = ?""",
            (measurement_id,),
        ).fetchone()


def update_measurement(measurement_id: int,
                       concentration: Optional[float],
                       sample_date: str) -> None:
    """O'lchov konsentratsiyasi va sanasini yangilaydi."""
    with get_connection() as conn:
        conn.execute(
            """UPDATE measurements
               SET concentration=?, sample_date=?
               WHERE id=?""",
            (concentration, sample_date, measurement_id),
        )


def delete_measurement(measurement_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM measurements WHERE id = ?", (measurement_id,))


def delete_measurements_by_year(project_id: int, year: int,
                                 station_id: int | None = None) -> int:
    with get_connection() as conn:
        if station_id:
            cur = conn.execute(
                "DELETE FROM measurements WHERE project_id=? AND year=? AND station_id=?",
                (project_id, year, station_id))
        else:
            cur = conn.execute(
                "DELETE FROM measurements WHERE project_id=? AND year=?",
                (project_id, year))
        return cur.rowcount


def delete_measurements_by_month(project_id: int, year: int, month: int,
                                  station_id: int | None = None) -> int:
    month_str = f"{year}-{month:02d}"
    with get_connection() as conn:
        if station_id:
            cur = conn.execute(
                "DELETE FROM measurements WHERE project_id=? AND year=? AND station_id=? AND substr(sample_date,1,7)=?",
                (project_id, year, station_id, month_str))
        else:
            cur = conn.execute(
                "DELETE FROM measurements WHERE project_id=? AND year=? AND substr(sample_date,1,7)=?",
                (project_id, year, month_str))
        return cur.rowcount


# ─────────────────────────────────────────────
#  results  CRUD
# ─────────────────────────────────────────────
def save_substance_result(project_id: int, year: int, substance_id: int,
                          ni: int, ni_exceed: int, alpha: float,
                          beta_avg: float, s_alpha: float,
                          s_beta: float, s_ij: float) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO results
               (project_id, year, substance_id, ni, ni_exceed, alpha,
                beta_avg, s_alpha, s_beta, s_ij)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(project_id, year, substance_id)
               DO UPDATE SET
                   ni=excluded.ni, ni_exceed=excluded.ni_exceed,
                   alpha=excluded.alpha, beta_avg=excluded.beta_avg,
                   s_alpha=excluded.s_alpha, s_beta=excluded.s_beta,
                   s_ij=excluded.s_ij""",
            (project_id, year, substance_id, ni, ni_exceed, alpha,
             beta_avg, s_alpha, s_beta, s_ij),
        )


def save_final_result(project_id: int, year: int,
                      ki: float, ski: float, f_count: int,
                      k_reserve: float, water_class: int,
                      class_label: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO results
               (project_id, year, substance_id, ki, ski, f_count,
                k_reserve, water_class, class_label)
               VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(project_id, year, substance_id)
               DO UPDATE SET
                   ki=excluded.ki, ski=excluded.ski,
                   f_count=excluded.f_count, k_reserve=excluded.k_reserve,
                   water_class=excluded.water_class,
                   class_label=excluded.class_label""",
            (project_id, year, ki, ski, f_count, k_reserve,
             water_class, class_label),
        )


def get_substance_results(project_id: int, year: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            """SELECT r.*, s.name as sub_name, s.mpc, s.unit
               FROM results r
               JOIN substances s ON s.id = r.substance_id
               WHERE r.project_id = ? AND r.year = ?
                 AND r.substance_id IS NOT NULL
               ORDER BY r.s_ij DESC""",
            (project_id, year),
        ).fetchall()


def get_final_result(project_id: int, year: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            """SELECT * FROM results
               WHERE project_id = ? AND year = ?
                 AND substance_id IS NULL""",
            (project_id, year),
        ).fetchone()


def get_all_final_results(project_id: int) -> list[sqlite3.Row]:
    """Loyihaning barcha yillar bo'yicha yakuniy natijalari."""
    with get_connection() as conn:
        return conn.execute(
            """SELECT * FROM results
               WHERE project_id = ? AND substance_id IS NULL
               ORDER BY year""",
            (project_id,),
        ).fetchall()
