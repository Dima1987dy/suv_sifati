"""
main_window.py
Asosiy oyna: MenuBar, Notebook (tablar), StatusBar.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path

# Loyiha ildizini path ga qo'shamiz
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db, seed_default_substances


# ─────────────────────────────────────────────
#  Ranglar va stil
# ─────────────────────────────────────────────
COLORS = {
    "bg":           "#F4F6F9",
    "sidebar":      "#2C3E50",
    "sidebar_text": "#ECF0F1",
    "accent":       "#2980B9",
    "accent_hover": "#3498DB",
    "success":      "#27AE60",
    "warning":      "#F39C12",
    "danger":       "#E74C3C",
    "white":        "#FFFFFF",
    "border":       "#BDC3C7",
    "text":         "#2C3E50",
    "text_light":   "#7F8C8D",
    # Suv sinflari
    "class_1":      "#2ECC71",   # yashil  — shartli toza
    "class_2":      "#A9DFBF",   # och yashil — kam ifloslangan
    "class_3":      "#F7DC6F",   # sariq — ifloslangan
    "class_4":      "#E59866",   # to'q sariq — iflos
    "class_5":      "#E74C3C",   # qizil — ekstremal
}

CLASS_COLORS = {
    1: COLORS["class_1"],
    2: COLORS["class_2"],
    3: COLORS["class_3"],
    4: COLORS["class_4"],
    5: COLORS["class_5"],
}


def get_class_color(water_class: int | None) -> str:
    return CLASS_COLORS.get(water_class, COLORS["border"])


# ─────────────────────────────────────────────
#  Stil sozlamalari
# ─────────────────────────────────────────────
def apply_styles(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")

    # Umumiy fon
    style.configure(".",
                    background=COLORS["bg"],
                    foreground=COLORS["text"],
                    font=("Segoe UI", 10))

    # Notebook (tablar)
    style.configure("TNotebook",
                    background=COLORS["bg"],
                    tabmargins=[2, 5, 2, 0])
    style.configure("TNotebook.Tab",
                    background=COLORS["border"],
                    foreground=COLORS["text"],
                    padding=[14, 6],
                    font=("Segoe UI", 10))
    style.map("TNotebook.Tab",
              background=[("selected", COLORS["accent"]),
                          ("active",   COLORS["accent_hover"])],
              foreground=[("selected", COLORS["white"]),
                          ("active",   COLORS["white"])])

    # Tugmalar
    style.configure("TButton",
                    background=COLORS["accent"],
                    foreground=COLORS["white"],
                    padding=[10, 5],
                    relief="flat",
                    font=("Segoe UI", 10))
    style.map("TButton",
              background=[("active", COLORS["accent_hover"]),
                          ("disabled", COLORS["border"])],
              foreground=[("disabled", COLORS["text_light"])])

    style.configure("Danger.TButton",
                    background=COLORS["danger"],
                    foreground=COLORS["white"])
    style.map("Danger.TButton",
              background=[("active", "#C0392B")])

    style.configure("Success.TButton",
                    background=COLORS["success"],
                    foreground=COLORS["white"])
    style.map("Success.TButton",
              background=[("active", "#229954")])

    # LabelFrame
    style.configure("TLabelframe",
                    background=COLORS["bg"],
                    bordercolor=COLORS["border"])
    style.configure("TLabelframe.Label",
                    background=COLORS["bg"],
                    foreground=COLORS["accent"],
                    font=("Segoe UI", 10, "bold"))

    # Treeview (jadvallar)
    style.configure("Treeview",
                    background=COLORS["white"],
                    foreground=COLORS["text"],
                    rowheight=26,
                    fieldbackground=COLORS["white"],
                    borderwidth=0,
                    font=("Segoe UI", 9))
    style.configure("Treeview.Heading",
                    background=COLORS["sidebar"],
                    foreground=COLORS["white"],
                    relief="flat",
                    font=("Segoe UI", 9, "bold"))
    style.map("Treeview",
              background=[("selected", COLORS["accent"])],
              foreground=[("selected", COLORS["white"])])

    # Entry
    style.configure("TEntry",
                    fieldbackground=COLORS["white"],
                    borderwidth=1,
                    relief="solid")

    # Combobox
    style.configure("TCombobox",
                    fieldbackground=COLORS["white"],
                    background=COLORS["white"])

    # Scrollbar
    style.configure("TScrollbar",
                    background=COLORS["border"],
                    troughcolor=COLORS["bg"],
                    borderwidth=0,
                    arrowsize=12)

    # Frame
    style.configure("Card.TFrame",
                    background=COLORS["white"],
                    relief="flat")


# ─────────────────────────────────────────────
#  Asosiy oyna
# ─────────────────────────────────────────────
class MainWindow:
    def __init__(self) -> None:
        # DB ni ishga tushirish
        init_db()
        seed_default_substances()

        # Asosiy oyna
        self.root = tk.Tk()
        self.root.title("Yer usti suvlari — Gidrokimyoviy baholash tizimi")
        self.root.geometry("1200x750")
        self.root.minsize(900, 600)
        self.root.configure(bg=COLORS["bg"])

        # Ikonka (mavjud bo'lsa)
        try:
            self.root.iconbitmap("assets/icon.ico")
        except Exception:
            pass

        apply_styles(self.root)
        self._build_menu()
        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        # Tablarni yuklaymiz (lazy import — siklik importdan qochish)
        self._load_tabs()

    # ── Menu ─────────────────────────────────
    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root, bg=COLORS["sidebar"],
                          fg=COLORS["sidebar_text"],
                          activebackground=COLORS["accent"],
                          activeforeground=COLORS["white"],
                          relief="flat")

        # Fayl
        m_file = tk.Menu(menubar, tearoff=0,
                         bg=COLORS["white"], fg=COLORS["text"])
        m_file.add_command(label="Yangi loyiha",
                           command=self._on_new_project,
                           accelerator="Ctrl+N")
        m_file.add_separator()
        m_file.add_command(label="Excel shablon yuklash",
                           command=self._on_import_excel)
        m_file.add_command(label="Excel hisobot eksport",
                           command=self._on_export_excel)
        m_file.add_separator()
        m_file.add_command(label="Chiqish",
                           command=self.root.quit,
                           accelerator="Alt+F4")
        menubar.add_cascade(label=" 📁 Fayl ", menu=m_file)

        # Ko'rinish
        m_view = tk.Menu(menubar, tearoff=0,
                         bg=COLORS["white"], fg=COLORS["text"])
        m_view.add_command(label="Loyihalar",
                           command=lambda: self._switch_tab(0))
        m_view.add_command(label="Ma'lumot kiritish",
                           command=lambda: self._switch_tab(1))
        m_view.add_command(label="Natijalar",
                           command=lambda: self._switch_tab(2))
        m_view.add_command(label="Xarita",
                           command=lambda: self._switch_tab(3))
        m_view.add_command(label="Hisobot",
                           command=lambda: self._switch_tab(4))
        menubar.add_cascade(label=" 👁 Ko'rinish ", menu=m_view)

        # Yordam
        m_help = tk.Menu(menubar, tearoff=0,
                         bg=COLORS["white"], fg=COLORS["text"])
        m_help.add_command(label="Dastur haqida",
                           command=self._on_about)
        m_help.add_command(label="Formulalar",
                           command=self._on_formulas)
        menubar.add_cascade(label=" ❓ Yordam ", menu=m_help)

        self.root.config(menu=menubar)

        # Klaviatura kombinatsiyalari
        self.root.bind("<Control-n>", lambda e: self._on_new_project())

    # ── Header ───────────────────────────────
    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=COLORS["sidebar"], height=52)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="💧  Yer usti suvlari — Gidrokimyoviy baholash tizimi",
            bg=COLORS["sidebar"],
            fg=COLORS["sidebar_text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=18, pady=12)

        # Joriy loyiha ko'rsatkichi
        self.lbl_current = tk.Label(
            header, text="Loyiha tanlanmagan",
            bg=COLORS["sidebar"],
            fg=COLORS["accent_hover"],
            font=("Segoe UI", 10),
        )
        self.lbl_current.pack(side="right", padx=18)

    # ── Notebook ─────────────────────────────
    def _build_notebook(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        # Tab freymlar (hozir bo'sh, tablar yuklanadi)
        self.tab_frames = {}
        tab_defs = [
            ("projects",    "📋  Loyihalar"),
            ("input",       "📥  Ma'lumot kiritish"),
            ("results",     "📊  Natijalar"),
            ("map",         "🗺️   Xarita"),
            ("report",      "📄  Hisobot"),
        ]
        for key, label in tab_defs:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=label)
            self.tab_frames[key] = frame

    # ── Status bar ───────────────────────────
    def _build_statusbar(self) -> None:
        bar = tk.Frame(self.root, bg=COLORS["sidebar"], height=24)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.status_var = tk.StringVar(value="Tayyor")
        tk.Label(bar, textvariable=self.status_var,
                 bg=COLORS["sidebar"], fg=COLORS["sidebar_text"],
                 font=("Segoe UI", 9), anchor="w").pack(
            side="left", padx=10, pady=3)

        # DB yo'li
        from database import DB_PATH
        tk.Label(bar, text=f"DB: {DB_PATH}",
                 bg=COLORS["sidebar"], fg=COLORS["text_light"],
                 font=("Segoe UI", 8)).pack(side="right", padx=10)

    # ── Tablarni yuklash ─────────────────────
    def _load_tabs(self) -> None:
        """Har bir tab o'z modulidan yuklanadi."""
        from gui.project_tab import ProjectTab
        from gui.input_tab   import InputTab
        from gui.results_tab import ResultsTab
        from gui.map_tab     import MapTab
        from gui.report_tab  import ReportTab

        self.tab_projects = ProjectTab(
            self.tab_frames["projects"], self)
        self.tab_input    = InputTab(
            self.tab_frames["input"], self)
        self.tab_results  = ResultsTab(
            self.tab_frames["results"], self)
        self.tab_map      = MapTab(
            self.tab_frames["map"], self)
        self.tab_report   = ReportTab(
            self.tab_frames["report"], self)

        # Tab o'zgarganda xaritani yangilash
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    # ── Umumiy holat o'zgaruvchilari ─────────
    @property
    def current_project_id(self) -> int | None:
        return getattr(self, "_current_project_id", None)

    @property
    def current_station_id(self) -> int | None:
        return getattr(self, "_current_station_id", None)

    @property
    def current_year(self) -> int | None:
        return getattr(self, "_current_year", None)

    def set_current_project(self, project_id: int | None,
                            name: str = "") -> None:
        """Loyiha tanlanganda barcha tablarni xabardor qiladi."""
        self._current_project_id = project_id
        self._current_station_id = None
        self._current_year       = None
        self.lbl_current.config(
            text=f"📂  {name}" if name else "Loyiha tanlanmagan"
        )
        self.set_status(f"Loyiha: {name}" if name else "Tayyor")
        # Tablarni yangilash
        if hasattr(self, "tab_input"):
            self.tab_input.on_project_changed()
        if hasattr(self, "tab_results"):
            self.tab_results.on_project_changed()
        if hasattr(self, "tab_report"):
            self.tab_report.on_project_changed()

    def set_current_station(self, station_id: int | None,
                            name: str = "") -> None:
        self._current_station_id = station_id
        if hasattr(self, "tab_input"):
            self.tab_input.on_station_changed()

    def set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.root.update_idletasks()

    def _switch_tab(self, index: int) -> None:
        self.notebook.select(index)

    # ── Hodisalar ────────────────────────────
    def _on_tab_changed(self, event) -> None:
        tab = self.notebook.index(self.notebook.select())
        if tab == 1 and hasattr(self, "tab_input"):
            self.tab_input.refresh()
        if tab == 2 and hasattr(self, "tab_results"):
            self.tab_results.on_project_changed()
        if tab == 3 and hasattr(self, "tab_map"):
            self.tab_map.refresh()
        if tab == 4 and hasattr(self, "tab_report"):
            self.tab_report.on_project_changed()

    def _on_new_project(self) -> None:
        self._switch_tab(0)
        if hasattr(self, "tab_projects"):
            self.tab_projects.open_add_dialog()

    def _on_import_excel(self) -> None:
        self._switch_tab(4)
        if hasattr(self, "tab_report"):
            self.tab_report.import_excel()

    def _on_export_excel(self) -> None:
        self._switch_tab(4)
        if hasattr(self, "tab_report"):
            self.tab_report.export_excel()

    def _on_about(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("Dastur haqida")
        win.geometry("480x320")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)

        # Header
        hdr = tk.Frame(win, bg=COLORS["sidebar"], height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="💧  Dastur haqida",
                 bg=COLORS["sidebar"], fg=COLORS["sidebar_text"],
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=18, pady=14)

        frm = tk.Frame(win, bg=COLORS["bg"])
        frm.pack(fill="both", expand=True, padx=24, pady=16)

        rows = [
            ("Dastur nomi",    "Yer usti suvlari gidrokimyoviy baholash tizimi"),
            ("Dastur muallifi","M.Sh. Abdiyeva"),
            ("Ilmiy asos",     "«Yer usti suvlari ifloslanish darajasini\n"
                               "gidrokimyoviy ko'rsatkichlar bo'yicha\n"
                               "kompleks baholash usuli»"),

            ("Versiya",        "1.0"),
        ]
        for label, value in rows:
            rf = tk.Frame(frm, bg=COLORS["bg"])
            rf.pack(fill="x", pady=3)
            tk.Label(rf, text=f"{label}:",
                     bg=COLORS["bg"], fg=COLORS["text_light"],
                     font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
            tk.Label(rf, text=value,
                     bg=COLORS["bg"], fg=COLORS["text"],
                     font=("Segoe UI", 9, "bold"), anchor="w",
                     justify="left").pack(side="left", padx=4)

        ttk.Button(win, text="Yopish",
                   command=win.destroy).pack(pady=(0, 14))

    def _on_formulas(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("Formulalar")
        win.geometry("500x420")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)

        txt = tk.Text(win, bg=COLORS["white"], fg=COLORS["text"],
                      font=("Courier New", 10), wrap="word",
                      padx=12, pady=10, relief="flat", bd=0)
        txt.pack(fill="both", expand=True, padx=10, pady=10)

        formulas = """\
ASOSIY FORMULALAR (qo'llanma asosida)
══════════════════════════════════════

1. Takroriylik:
   α_ij = (n'_ij / n_ij) × 100%

2. O'rtacha oshish karraligi:
   β'_ij = Σβ_ij / n'_ij
   (Kislorod uchun: β = MPC / C)

3. Umumlashtirilgan ball:
   S_ij = S_α × S_β   [1..25]

4. Kombinatör indeks (KI):
   S_j = Σ S_ij

5. Solishtirma kombinatör indeks (SKI):
   S'_j = S_j / N_j

6. Zaxira koeffitsienti:
   k = 1 - 0.1 × F
   (F — kritik ko'rsatkichlar soni, S_ij ≥ 9)

7. Sinf chegaralari (SKI bo'yicha):
   1-sinf:  SKI ≤ 1·k        — Shartli toza
   2-sinf:  (1·k ; 2·k]      — Kam ifloslangan
   3-sinf:  (2·k ; 4·k]      — Ifloslangan
   4-sinf:  (4·k ; 11·k]     — Iflos
   5-sinf:  (11·k ; ∞)       — Ekstremal iflos

E-ILOVA (S_alpha):
   [1,10)  → [1,2)   (0.11/%)
   [10,30) → [2,3)   (0.05/%)
   [30,50) → [3,4)   (0.05/%)
   [50,100]→  4

J-ILOVA (S_beta):
   (1,2)   → [1,2)   (1.00/birlik)
   [2,10)  → [2,3)   (0.125/birlik)
   [10,50) → [3,4)   (0.025/birlik)
   [50,∞)  →  4
"""
        txt.insert("1.0", formulas)
        txt.config(state="disabled")

        ttk.Button(win, text="Yopish",
                   command=win.destroy).pack(pady=(0, 10))

    # ── Ishga tushirish ───────────────────────
    def run(self) -> None:
        self.root.mainloop()
