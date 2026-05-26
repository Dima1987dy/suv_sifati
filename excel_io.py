"""
excel_io.py
Excel bilan ishlash:
  - create_template()   : to'ldirishga tayyor shablon yaratish
  - import_from_excel() : to'ldirilgan shablonni bazaga yuklash
  - export_results()    : hisob natijalarini Excelga chiqarish
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Any

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import database as db


# ─────────────────────────────────────────────
#  Umumiy ranglar va stillar
# ─────────────────────────────────────────────
C_HEADER_BG   = "2C3E50"   # to'q ko'k
C_HEADER_FG   = "FFFFFF"
C_ACCENT      = "2980B9"   # ko'k
C_LIGHT_BLUE  = "D6EAF8"
C_GREEN       = "D5F5E3"
C_YELLOW      = "FEF9E7"
C_ORANGE      = "FDEBD0"
C_RED         = "FADBD8"
C_GRAY        = "F2F3F4"
C_BORDER      = "BDC3C7"

# Sinf ranglari
CLASS_BG = {
    1: "D5F5E3",   # yashil
    2: "A9DFBF",
    3: "F7DC6F",   # sariq
    4: "E59866",   # to'q sariq
    5: "E74C3C",   # qizil
}

thin = Side(style="thin", color=C_BORDER)
THIN_BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
thick_bottom = Border(left=thin, right=thin,
                      top=thin, bottom=Side(style="medium", color="000000"))


def _hdr(ws, row: int, col: int, value: Any,
         bg: str = C_HEADER_BG, fg: str = C_HEADER_FG,
         bold: bool = True, wrap: bool = True,
         align: str = "center") -> None:
    """Sarlavha katakchasi."""
    cell = ws.cell(row=row, column=col, value=value)
    cell.font      = Font(bold=bold, color=fg,
                          name="Calibri", size=10)
    cell.fill      = PatternFill("solid", fgColor=bg)
    cell.alignment = Alignment(horizontal=align,
                               vertical="center", wrap_text=wrap)
    cell.border    = THIN_BORDER


def _cell(ws, row: int, col: int, value: Any,
          bg: str | None = None, bold: bool = False,
          align: str = "left", fmt: str | None = None) -> None:
    """Oddiy katakcha."""
    cell = ws.cell(row=row, column=col, value=value)
    cell.font      = Font(name="Calibri", size=10, bold=bold)
    cell.alignment = Alignment(horizontal=align, vertical="center")
    cell.border    = THIN_BORDER
    if bg:
        cell.fill = PatternFill("solid", fgColor=bg)
    if fmt:
        cell.number_format = fmt


def _freeze(ws, cell: str = "B2") -> None:
    ws.freeze_panes = cell


def _col_width(ws, widths: dict[str, float]) -> None:
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


# ═══════════════════════════════════════════════════════════════
#  1. SHABLON YARATISH
# ═══════════════════════════════════════════════════════════════
def create_template(save_path: str | Path,
                    project_id: int | None = None) -> Path:
    """
    To'ldirishga tayyor Excel shabloni yaratadi.
    project_id berilsa, moddalar ro'yxati avtomatik yuklanadi.

    Sheetlar:
      1. Yo'riqnoma   — qanday to'ldirish
      2. O'lchovlar   — asosiy kiritish jadvali
      3. Moddalar     — substance nomi va MPC (tahrirlash mumkin)
    """
    save_path = Path(save_path)
    wb = Workbook()

    _build_guide_sheet(wb)
    _build_measurements_sheet(wb, project_id)
    _build_substances_sheet(wb, project_id)

    # Birinchi sheetni faol qilish
    wb.active = wb["O'lchovlar"]

    wb.save(save_path)
    return save_path


# ── Sheet 1: Yo'riqnoma ─────────────────────
def _build_guide_sheet(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "Yo'riqnoma"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 35
    ws.column_dimensions["C"].width = 65

    # Sarlavha
    ws.merge_cells("B1:C1")
    c = ws["B1"]
    c.value = "💧  YER USTI SUVLARI — MA'LUMOT KIRITISH SHABLONI"
    c.font  = Font(bold=True, size=14, color=C_ACCENT, name="Calibri")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    ws.merge_cells("B2:C2")
    c = ws["B2"]
    c.value = "Qo'llanma: M.Sh. Abdieva, Toshkent, Renessans Press, 2026"
    c.font  = Font(italic=True, size=9, color="7F8C8D", name="Calibri")
    c.alignment = Alignment(horizontal="center")

    rows = [
        ("",  ""),
        ("SHEETLAR TUZILISHI", ""),
        ("📋  O'lchovlar",
         "Asosiy kiritish jadvali. Har ustun — bir modda, "
         "har qator — bir sana."),
        ("📋  Moddalar",
         "Moddalar ro'yxati va MPC qiymatlari. "
         "Yangi modda qo'shish mumkin."),
        ("", ""),
        ("TO'LDIRISH QOIDALARI", ""),
        ("Loyiha nomi",    "O'lchovlar sheetidagi B1 katakchaga yozing."),
        ("Stansiya nomi",  "O'lchovlar sheetidagi B2 katakchaga yozing."),
        ("Yil",            "O'lchovlar sheetidagi B3 katakchaga raqam kiriting."),
        ("Sana formati",   "YYYY-MM-DD  (masalan: 2023-01-14)"),
        ("Koncentratsiya", "Raqam kiriting (mg/dm³). "
                           "Aniqlanmagan bo'lsa — bo'sh qoldiring."),
        ("Kislorod (O2)",  "Oddiy konzentrasiya kiriting (mg/dm³). "
                           "Teskari hisob avtomatik."),
        ("", ""),
        ("MUHIM ESLATMALAR", ""),
        ("MPC dan oshish",
         "Dastur avtomatik hisoblaydi — siz faqat o'lchov natijasini kiriting."),
        ("Moddalar tartibi",
         "Ustun sarlavhasi 'Moddalar' sheetidagi nom bilan mos bo'lishi shart."),
        ("Bo'sh qatorlar",
         "O'lchovlar jadvalidagi bo'sh qatorlar e'tiborga olinmaydi."),
    ]

    for i, (key, val) in enumerate(rows, start=4):
        if val == "" and key in ("SHEETLAR TUZILISHI",
                                 "TO'LDIRISH QOIDALARI",
                                 "MUHIM ESLATMALAR"):
            ws.merge_cells(f"B{i}:C{i}")
            c = ws.cell(row=i, column=2, value=key)
            c.font  = Font(bold=True, size=11, color=C_HEADER_FG,
                           name="Calibri")
            c.fill  = PatternFill("solid", fgColor=C_ACCENT)
            c.alignment = Alignment(horizontal="left",
                                    vertical="center", indent=1)
            ws.row_dimensions[i].height = 22
        elif key:
            _cell(ws, i, 2, key, bg=C_LIGHT_BLUE, bold=True, align="left")
            _cell(ws, i, 3, val, align="left")
            ws.row_dimensions[i].height = 20
        else:
            ws.row_dimensions[i].height = 8


# ── Sheet 2: O'lchovlar (vertikal moddalar, gorizontal sanalar) ──
def _build_measurements_sheet(wb: Workbook,
                               project_id: int | None) -> None:
    ws = wb.create_sheet("O'lchovlar")
    ws.sheet_view.showGridLines = False

    substances = db.get_all_substances()
    cur_year   = datetime.now().year

    # ── Meta qatorlar (1-3) ──────────────────────────────────────
    meta = [
        ("Loyiha nomi:", ""),
        ("Punkt nomi:",  ""),
        ("Yil:",         cur_year),
    ]
    for r, (k, v) in enumerate(meta, start=1):
        _hdr(ws, r, 1, k, bg=C_LIGHT_BLUE, fg="2C3E50",
             bold=True, align="right")
        ws.column_dimensions["A"].width = 22
        c = ws.cell(row=r, column=2, value=v)
        c.font      = Font(name="Calibri", size=10,
                           bold=True, color=C_ACCENT)
        c.alignment = Alignment(horizontal="left",
                                vertical="center")
        ws.merge_cells(f"B{r}:D{r}")
        ws.row_dimensions[r].height = 20

    # ── Sarlavha qatori (5) ──────────────────────────────────────
    HDR_ROW = 5
    ws.row_dimensions[HDR_ROW].height = 32

    _hdr(ws, HDR_ROW, 1, "Modda",        bg=C_HEADER_BG, align="left")
    _hdr(ws, HDR_ROW, 2, "MPC (mg/dm³)", bg=C_HEADER_BG, align="center")
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 14

    # 12 ta sana ustunlari (C dan N gacha)
    months_uz = ["Yanvar","Fevral","Mart","Aprel","May","Iyun",
                 "Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"]
    DATE_COL_START = 3   # C ustunidan boshlanadi

    for i in range(12):
        col  = DATE_COL_START + i
        col_letter = get_column_letter(col)
        # Sarlavha: "Oy\nYYYY-MM-DD"
        _hdr(ws, HDR_ROW, col,
             f"{months_uz[i]}\n({cur_year}-{i+1:02d}-??)",
             bg=C_ACCENT, align="center")
        ws.column_dimensions[col_letter].width = 13

    # ── Moddalar qatorlari (6 dan boshlab) ──────────────────────
    DATA_ROW_START = HDR_ROW + 1

    for ri, s in enumerate(substances):
        row = DATA_ROW_START + ri
        bg  = C_GRAY if ri % 2 == 0 else None

        # Modda nomi
        is_o2 = s["is_oxygen"]
        name  = ("🔵 " if is_o2 else "    ") + s["name"]
        _cell(ws, row, 1, name, bg=bg, bold=False, align="left")

        # MPC
        mpc_txt = f"{s['mpc']}" + ("  ↓" if is_o2 else "")
        _cell(ws, row, 2, mpc_txt,
              bg=C_YELLOW, bold=True, align="center")

        # 12 ta bo'sh katak (foydalanuvchi to'ldiradi)
        for i in range(12):
            col = DATE_COL_START + i
            _cell(ws, row, col, None,
                  bg=C_LIGHT_BLUE if is_o2 else bg,
                  align="center")

        ws.row_dimensions[row].height = 20

    # ── Sana qatori (oxirida) — foydalanuvchi sana yozadi ───────
    date_row = DATA_ROW_START + len(substances) + 1
    ws.row_dimensions[date_row - 1].height = 6   # ajratuvchi bo'sh
    _hdr(ws, date_row, 1, "Sana (YYYY-MM-DD)",
         bg=C_HEADER_BG, align="center")
    _hdr(ws, date_row, 2, "→ Har oy sanasini yozing",
         bg=C_HEADER_BG, align="left")
    for i in range(12):
        col = DATE_COL_START + i
        # Namuna sana: har oy 15-kuni
        _cell(ws, date_row, col,
              f"{cur_year}-{i+1:02d}-15",
              bg=C_YELLOW, bold=True, align="center")
    ws.row_dimensions[date_row].height = 22

    # Izoh
    note_row = date_row + 2
    ws.merge_cells(f"A{note_row}:{get_column_letter(DATE_COL_START+11)}{note_row}")
    c2 = ws.cell(row=note_row, column=1,
        value="ℹ️  Sanalarni o'zgartiring (YYYY-MM-DD). "
              "Bo'sh qoldirsa — aniqlanmagan. 0 YOZMANG! "
              "🔵 belgisi kislorod (MPC dan PAST bo'lsa oshgan hisoblanadi ↓).")
    c2.font      = Font(italic=True, size=9,
                        color="7F8C8D", name="Calibri")
    c2.alignment = Alignment(horizontal="left", wrap_text=True)
    ws.row_dimensions[note_row].height = 28

    _freeze(ws, "C6")


# ── Sheet 3: Moddalar ───────────────────────
def _build_substances_sheet(wb: Workbook,
                             project_id: int | None) -> None:
    ws = wb.create_sheet("Moddalar")
    ws.sheet_view.showGridLines = False

    hdrs = ["#", "Modda nomi", "MPC (mg/dm³)",
            "Birlik", "Xavf sinfi", "Kislorod? (1/0)"]
    widths = {"A": 5, "B": 28, "C": 15, "D": 12, "E": 12, "F": 16}
    _col_width(ws, widths)

    for ci, h in enumerate(hdrs, 1):
        _hdr(ws, 1, ci, h)
    ws.row_dimensions[1].height = 28

    substances = db.get_all_substances()
    for ri, s in enumerate(substances, start=2):
        bg = C_GRAY if ri % 2 == 0 else None
        _cell(ws, ri, 1, ri - 1,   bg=bg, align="center")
        _cell(ws, ri, 2, s["name"],   bg=bg)
        _cell(ws, ri, 3, s["mpc"],    bg=bg, align="center",
              fmt="0.000000")
        _cell(ws, ri, 4, s["unit"],   bg=bg, align="center")
        _cell(ws, ri, 5, s["hazard_class"], bg=bg, align="center")
        _cell(ws, ri, 6, s["is_oxygen"],    bg=bg, align="center")
        ws.row_dimensions[ri].height = 20

    # Yangi modda uchun bo'sh qatorlar
    for ri in range(len(substances) + 2,
                    len(substances) + 12):
        for ci in range(1, 7):
            _cell(ws, ri, ci, None, bg=C_LIGHT_BLUE if ci > 1 else C_GRAY)
        ws.row_dimensions[ri].height = 20

    # Izoh
    note_row = len(substances) + 13
    ws.merge_cells(f"A{note_row}:F{note_row}")
    c = ws.cell(row=note_row, column=1,
                value="ℹ️  Yangi modda qo'shish uchun bo'sh qatorlarga yozing. "
                      "Kislorod uchun '1', boshqalar uchun '0' kiriting.")
    c.font      = Font(italic=True, size=9, color="7F8C8D", name="Calibri")
    c.alignment = Alignment(horizontal="left", wrap_text=True)

    _freeze(ws, "C2")


# ═══════════════════════════════════════════════════════════════
#  2. IMPORT
# ═══════════════════════════════════════════════════════════════
class ImportError(Exception):
    pass


def _get_or_create_project(name: str) -> int:
    """Loyiha mavjud bo'lsa id qaytaradi, yo'q bo'lsa yaratadi."""
    projects = db.get_all_projects()
    for p in projects:
        if p["name"].strip().lower() == name.strip().lower():
            return p["id"]
    return db.add_project(name.strip(), "Shablon orqali yaratildi")


def _get_or_create_station(project_id: int, name: str) -> int:
    """Punkt mavjud bo'lsa id qaytaradi, yo'q bo'lsa yaratadi."""
    stations = db.get_stations(project_id)
    for s in stations:
        if s["name"].strip().lower() == name.strip().lower():
            return s["id"]
    return db.add_station(project_id, name.strip())


def import_from_excel(file_path: str | Path,
                      project_id: int | None = None,
                      station_id: int | None = None) -> dict:
    """
    Yangi format (vertikal moddalar, gorizontal sanalar) shablonni o'qiydi.
    Qaytaradi: {"imported": int, "skipped": int, "errors": list[str]}
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise ImportError(f"Fayl topilmadi: {file_path}")

    wb = openpyxl.load_workbook(file_path, data_only=True)

    if "O'lchovlar" not in wb.sheetnames:
        raise ImportError("'O'lchovlar' sheeti topilmadi.")

    ws = wb["O'lchovlar"]

    # Moddalar sheetidan yangi moddalarni sinxronlaymiz
    if "Moddalar" in wb.sheetnames:
        _sync_substances_sheet(wb["Moddalar"])

    # ── Shablondan loyiha va punkt nomini o'qish ─────────────────
    proj_name = ws.cell(row=1, column=2).value
    stat_name = ws.cell(row=2, column=2).value

    if proj_name and str(proj_name).strip():
        project_id = _get_or_create_project(str(proj_name).strip())
    
    if not project_id:
        raise ImportError(
            "Loyiha aniqlanmadi!\n\n"
            "Shablonda B1 katakchaga loyiha nomini yozing\n"
            "(masalan: Sirdaryo) yoki dasturda loyihani tanlang."
        )

    if stat_name and str(stat_name).strip():
        station_id = _get_or_create_station(
            project_id, str(stat_name).strip())

    all_subs = {s["name"]: s for s in db.get_all_substances()}

    HDR_ROW       = 5    # sarlavha qatori
    DATA_ROW_START = HDR_ROW + 1  # moddalar 6-qatordan
    DATE_COL_START = 3   # C ustunidan sanalar boshlanadi

    # ── Sana qatorini topamiz (moddalar tugaganidan keyin) ───────
    # Sana qatori: A ustunida "Sana (YYYY-MM-DD)" yozilgan
    date_row = None
    for row in range(DATA_ROW_START, ws.max_row + 1):
        val = ws.cell(row=row, column=1).value
        if val and "Sana" in str(val):
            date_row = row
            break

    if not date_row:
        raise ImportError(
            "Sana qatori topilmadi.\n"
            "Shablon oxirida 'Sana (YYYY-MM-DD)' qatori bo'lishi kerak."
        )

    # ── Har ustun uchun sana ─────────────────────────────────────
    col_dates: dict[int, str] = {}
    errors: list[str] = []
    skipped = 0

    for col in range(DATE_COL_START, DATE_COL_START + 12):
        val = ws.cell(row=date_row, column=col).value
        if not val:
            continue
        if hasattr(val, "strftime"):
            date_str = val.strftime("%Y-%m-%d")
        else:
            date_str = str(val).strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            col_dates[col] = date_str
        except ValueError:
            errors.append(f"Ustun {col}: '{date_str}' noto'g'ri sana.")
            skipped += 1

    if not col_dates:
        raise ImportError(
            "Sanalar topilmadi.\n"
            "Sana qatoriga YYYY-MM-DD formatida sana yozing."
        )

    # ── Modda qatorlarini o'qish + MPC yangilash ────────────────
    rows_to_insert: list[tuple] = []
    mpc_updated: list[str] = []   # yangilangan moddalar

    for row in range(DATA_ROW_START, date_row):
        # Modda nomi (A ustuni) — "🔵 " prefiksini tozalaymiz
        name_raw = ws.cell(row=row, column=1).value
        if not name_raw:
            continue
        name_clean = str(name_raw).strip()
        for prefix in ["🔵 ", "🔵", "    ", "   "]:
            if name_clean.startswith(prefix):
                name_clean = name_clean[len(prefix):]
                break
        name_clean = name_clean.strip()

        if name_clean not in all_subs:
            matched = next(
                (k for k in all_subs if name_clean in k or k in name_clean),
                None)
            if not matched:
                continue
            name_clean = matched

        sub = all_subs[name_clean]

        # ── MPC ni B ustunidan o'qib, bazani yangilaymiz ─────────
        mpc_raw = ws.cell(row=row, column=2).value
        if mpc_raw is not None and str(mpc_raw).strip():
            # "4.0  ↓" kabi formatdan raqamni ajratamiz
            mpc_str = str(mpc_raw).replace("↓","").replace("↑","").strip()
            try:
                new_mpc = float(mpc_str.replace(",","."))
                if new_mpc > 0 and abs(new_mpc - sub["mpc"]) > 1e-9:
                    db.update_substance(
                        sub["id"], sub["name"], new_mpc,
                        sub["unit"] or "mg/dm3",
                        sub["hazard_class"] or 3,
                        bool(sub["is_oxygen"]))
                    mpc_updated.append(
                        f"{sub['name']}: {sub['mpc']} → {new_mpc}")
                    # all_subs ni ham yangilaymiz
                    all_subs[name_clean] = db.get_substance(sub["id"])
                    sub = all_subs[name_clean]
            except (ValueError, TypeError):
                pass

        for col, date_str in col_dates.items():
            val = ws.cell(row=row, column=col).value
            if val is None or str(val).strip() == "":
                concentration = None
            else:
                try:
                    concentration = float(str(val).replace(",", "."))
                    if concentration < 0:
                        raise ValueError
                except (ValueError, TypeError):
                    errors.append(
                        f"Qator {row}, ustun {col}: "
                        f"'{val}' raqam emas, o'tkazib yuborildi."
                    )
                    skipped += 1
                    continue
            rows_to_insert.append(
                (project_id, station_id, sub["id"], date_str, concentration)
            )

    if not rows_to_insert:
        raise ImportError(
            "Import qilinadigan ma'lumot topilmadi.\n"
            "Konsentratsiya katakchalarini to'ldiring."
        )

    from database import add_measurements_with_station
    add_measurements_with_station(rows_to_insert)

    # Qaytariladigan natijaga loyiha/punkt ma'lumotlarini qo'shamiz
    proj = db.get_project(project_id)
    stat_info = db.get_station(station_id) if station_id else None

    return {
        "imported":     len(rows_to_insert),
        "skipped":      skipped,
        "errors":       errors,
        "project_id":   project_id,
        "station_id":   station_id,
        "project_name": proj["name"] if proj else "—",
        "station_name": stat_info["name"] if stat_info else "—",
        "mpc_updated":  mpc_updated,
    }


def _bulk_insert_with_station(rows: list[tuple]) -> None:
    """rows = (project_id, station_id, substance_id, date, concentration)"""
    import sqlite3
    conn = db.get_connection()
    try:
        conn.executemany(
            """INSERT INTO measurements
               (project_id, station_id, substance_id, sample_date, concentration)
               VALUES (?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _sync_substances_sheet(ws) -> None:
    """
    Moddalar sheetidagi yangi qatorlarni bazaga qo'shadi.
    """
    existing = {s["name"] for s in db.get_all_substances()}

    for row in range(2, ws.max_row + 1):
        name = ws.cell(row=row, column=2).value
        mpc  = ws.cell(row=row, column=3).value
        if not name or not mpc:
            continue
        name = str(name).strip()
        if name in existing:
            continue
        try:
            unit        = str(ws.cell(row=row, column=4).value or "mg/dm3")
            hazard      = int(ws.cell(row=row, column=5).value or 3)
            is_oxygen   = int(ws.cell(row=row, column=6).value or 0)
            db.add_substance(name, float(mpc), unit, hazard,
                             bool(is_oxygen))
        except Exception:
            pass   # noto'g'ri qatorni o'tkazib yuboramiz


# ═══════════════════════════════════════════════════════════════
#  3. EKSPORT — natijalar
# ═══════════════════════════════════════════════════════════════
def export_results(save_path: str | Path,
                   project_id: int,
                   year: int) -> Path:
    """
    Hisob natijalarini Excelga chiqaradi.
    Sheetlar:
      1. Xulosa      — KI, SKI, sinf, kritik moddalar
      2. Moddalar    — har bir modda uchun α, β, Sα, Sβ, Sij
      3. O'lchovlar  — xom ma'lumotlar
    """
    save_path = Path(save_path)
    project   = db.get_project(project_id)
    if not project:
        raise ValueError(f"Loyiha topilmadi: {project_id}")

    wb = Workbook()
    _build_summary_sheet(wb, project, year)
    _build_detail_sheet(wb, project_id, year)
    _build_raw_data_sheet(wb, project_id, year)

    wb.active = wb["Xulosa"]
    wb.save(save_path)
    return save_path


# ── Xulosa sheeti ───────────────────────────
def _build_summary_sheet(wb: Workbook, project, year: int) -> None:
    ws = wb.active
    ws.title = "Xulosa"
    ws.sheet_view.showGridLines = False
    _col_width(ws, {"A": 3, "B": 32, "C": 22, "D": 22, "E": 22})

    # Sarlavha
    ws.merge_cells("B1:E1")
    c = ws["B1"]
    c.value = f"GIDROKIMYOVIY BAHOLASH — {year} YIL"
    c.font  = Font(bold=True, size=14, color=C_HEADER_FG,
                   name="Calibri")
    c.fill  = PatternFill("solid", fgColor=C_HEADER_BG)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    ws.merge_cells("B2:E2")
    c = ws["B2"]
    c.value = f"Loyiha: {project['name']}"
    c.font  = Font(bold=True, size=11, color=C_ACCENT, name="Calibri")
    c.alignment = Alignment(horizontal="left", indent=1, vertical="center")
    ws.row_dimensions[2].height = 24

    # Yakuniy natijalar
    final = db.get_final_result(project["id"], year)
    r = 4
    summary_data = []
    if final:
        wc   = final["water_class"] or 0
        bg_c = CLASS_BG.get(wc, "FFFFFF")
        summary_data = [
            ("Suv sifati sinfi",
             f"{wc}-sinf — {final['class_label'] or '—'}",
             bg_c),
            ("SKI (Solishtirma kombinatör indeks)",
             f"{final['ski']:.4f}" if final["ski"] else "—",
             C_LIGHT_BLUE),
            ("KI (Kombinatör indeks)",
             f"{final['ki']:.2f}" if final["ki"] else "—",
             C_LIGHT_BLUE),
            ("Kritik ko'rsatkichlar soni (F)",
             str(final["f_count"] or 0),
             C_YELLOW if (final["f_count"] or 0) > 0 else None),
            ("Zaxira koeffitsienti (k)",
             f"{final['k_reserve']:.2f}" if final["k_reserve"] else "—",
             None),
        ]
    else:
        summary_data = [("Natijalar topilmadi",
                         "Avval hisob o'tkazing", C_YELLOW)]

    _hdr(ws, r, 2, "Ko'rsatkich", align="left")
    _hdr(ws, r, 3, "Qiymat", align="center")
    ws.merge_cells(f"C{r}:E{r}")
    ws.row_dimensions[r].height = 24
    r += 1

    for label, value, bg in summary_data:
        _cell(ws, r, 2, label, bg=bg, bold=False)
        ws.merge_cells(f"C{r}:E{r}")
        _cell(ws, r, 3, value, bg=bg, bold=True, align="center")
        ws.row_dimensions[r].height = 22
        r += 1

    # Kritik moddalar ro'yxati
    r += 1
    ws.merge_cells(f"B{r}:E{r}")
    c = ws.cell(row=r, column=2, value="KRITIK KO'RSATKICHLAR (Sij ≥ 9)")
    c.font  = Font(bold=True, size=10, color=C_HEADER_FG, name="Calibri")
    c.fill  = PatternFill("solid", fgColor="E74C3C")
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[r].height = 24
    r += 1

    sub_results = db.get_substance_results(project["id"], year)
    critical = [s for s in sub_results
                if s["s_ij"] and s["s_ij"] >= 9]

    if critical:
        _hdr(ws, r, 2, "Modda",     align="left",   bg=C_ACCENT)
        _hdr(ws, r, 3, "Sij ball",  align="center", bg=C_ACCENT)
        _hdr(ws, r, 4, "α (%)",     align="center", bg=C_ACCENT)
        _hdr(ws, r, 5, "β' (o'rtacha)", align="center", bg=C_ACCENT)
        ws.row_dimensions[r].height = 22
        r += 1
        for s in critical:
            _cell(ws, r, 2, s["sub_name"], bg=CLASS_BG[5])
            _cell(ws, r, 3, round(s["s_ij"], 2),
                  bg=CLASS_BG[5], align="center", bold=True)
            _cell(ws, r, 4, f"{s['alpha']:.1f}%",
                  bg=CLASS_BG[5], align="center")
            _cell(ws, r, 5, round(s["beta_avg"], 3) if s["beta_avg"] else "—",
                  bg=CLASS_BG[5], align="center")
            ws.row_dimensions[r].height = 20
            r += 1
    else:
        ws.merge_cells(f"B{r}:E{r}")
        _cell(ws, r, 2, "Kritik ko'rsatkichlar yo'q",
              bg=CLASS_BG[1], align="center")

    # Sana
    r += 2
    ws.merge_cells(f"B{r}:E{r}")
    c = ws.cell(row=r, column=2,
                value=f"Hisobot tayyorlandi: "
                      f"{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.font = Font(italic=True, size=9, color="7F8C8D", name="Calibri")
    c.alignment = Alignment(horizontal="right")

    _freeze(ws, "B3")


# ── Moddalar sheeti ─────────────────────────
def _build_detail_sheet(wb: Workbook,
                        project_id: int, year: int) -> None:
    ws = wb.create_sheet("Moddalar tahlili")
    ws.sheet_view.showGridLines = False
    _col_width(ws, {
        "A": 3, "B": 24, "C": 10, "D": 10,
        "E": 10, "F": 12, "G": 10, "H": 10, "I": 10,
    })

    hdrs = ["Modda", "ni", "ni' (oshdi)", "α (%)",
            "β' (o'rtacha)", "Sα", "Sβ", "Sij"]
    for ci, h in enumerate(hdrs, 2):
        _hdr(ws, 1, ci, h)
    ws.row_dimensions[1].height = 28

    sub_results = db.get_substance_results(project_id, year)
    for ri, s in enumerate(sub_results, start=2):
        is_crit = s["s_ij"] and s["s_ij"] >= 9
        bg = CLASS_BG[5] if is_crit else (C_GRAY if ri % 2 == 0 else None)
        _cell(ws, ri, 2,  s["sub_name"],                  bg=bg)
        _cell(ws, ri, 3,  s["ni"]        or 0,            bg=bg, align="center")
        _cell(ws, ri, 4,  s["ni_exceed"] or 0,            bg=bg, align="center")
        _cell(ws, ri, 5,  f"{s['alpha']:.1f}%" if s["alpha"] is not None
                          else "—",                        bg=bg, align="center")
        _cell(ws, ri, 6,  round(s["beta_avg"], 3) if s["beta_avg"]
                          else "—",                        bg=bg, align="center")
        _cell(ws, ri, 7,  round(s["s_alpha"], 3) if s["s_alpha"]
                          else "—",                        bg=bg, align="center")
        _cell(ws, ri, 8,  round(s["s_beta"], 3) if s["s_beta"]
                          else "—",                        bg=bg, align="center")
        bold_sij = bool(is_crit)
        _cell(ws, ri, 9,  round(s["s_ij"], 3) if s["s_ij"]
                          else "—",                        bg=bg,
              align="center", bold=bold_sij)
        ws.row_dimensions[ri].height = 20

    _freeze(ws, "C2")


# ── Xom ma'lumotlar sheeti ──────────────────
def _build_raw_data_sheet(wb: Workbook,
                          project_id: int, year: int) -> None:
    ws = wb.create_sheet("Xom ma'lumotlar")
    ws.sheet_view.showGridLines = False

    substances = db.get_all_substances()
    sub_map    = {s["id"]: s["name"] for s in substances}

    measurements = db.get_measurements(project_id, year)
    if not measurements:
        ws.cell(row=1, column=1,
                value="Bu yil uchun o'lchovlar yo'q")
        return

    # Sana × modda matritsasi
    dates: list[str]    = []
    data:  dict         = {}   # {date: {sub_id: concentration}}
    sub_ids_used: set   = set()

    for m in measurements:
        d = m["sample_date"]
        if d not in data:
            data[d] = {}
            dates.append(d)
        data[d][m["substance_id"]] = m["concentration"]
        sub_ids_used.add(m["substance_id"])

    dates.sort()
    sub_ids_sorted = sorted(sub_ids_used)

    # Sarlavha
    _hdr(ws, 1, 1, "Sana")
    ws.column_dimensions["A"].width = 16
    for ci, sid in enumerate(sub_ids_sorted, 2):
        _hdr(ws, 1, ci, sub_map.get(sid, f"Sub#{sid}"),
             bg=C_ACCENT)
        ws.column_dimensions[get_column_letter(ci)].width = 14
    ws.row_dimensions[1].height = 28

    # MPC qatori
    all_subs_dict = {s["id"]: s for s in substances}
    _hdr(ws, 2, 1, "MPC", bg=C_GRAY, fg="2C3E50")
    for ci, sid in enumerate(sub_ids_sorted, 2):
        s = all_subs_dict.get(sid)
        mpc_txt = f"{s['mpc']}" + (" ↓" if s and s["is_oxygen"] else "") if s else "—"
        _cell(ws, 2, ci, mpc_txt, bg=C_YELLOW, align="center", bold=True)

    # Ma'lumotlar
    for ri, date in enumerate(dates, start=3):
        bg = C_GRAY if ri % 2 == 0 else None
        _cell(ws, ri, 1, date, bg=bg, align="center")
        for ci, sid in enumerate(sub_ids_sorted, 2):
            val = data[date].get(sid)
            _cell(ws, ri, ci, val, bg=bg, align="center")
        ws.row_dimensions[ri].height = 20

    _freeze(ws, "B3")
