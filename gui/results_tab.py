"""
results_tab.py — Hisob natijalarini ko'rsatish
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db
from gui.main_window import COLORS, get_class_color


CLASS_LABELS = {
    1:    "1-sinf — Shartli toza",
    2:    "2-sinf — Kam ifloslangan",
    3:    "3-sinf — Ifloslangan",
    4:    "4-sinf — Iflos",
    5:    "5-sinf — Ekstremal ifloslangan",
}


class ResultsTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app    = app
        self._build()

    def _build(self):
        # Yuqori — yil tanlash + umumiy ko'rsatkich
        top = ttk.Frame(self.parent)
        top.pack(fill="x", padx=8, pady=(8,4))

        ttk.Label(top, text="Yil:").pack(side="left")
        self.cmb_year = ttk.Combobox(top, width=8, state="readonly")
        self.cmb_year.pack(side="left", padx=(4,16))
        self.cmb_year.bind("<<ComboboxSelected>>", self._on_year_change)

        ttk.Button(top, text="🔄 Yangilash",
                   command=self.on_project_changed).pack(side="left", padx=4)

        # Sinf badge
        self.lbl_class = tk.Label(top, text="Sinf: —",
                                   font=("Segoe UI", 12, "bold"),
                                   bg=COLORS["border"], fg=COLORS["white"],
                                   padx=16, pady=4, relief="flat")
        self.lbl_class.pack(side="right", padx=8)

        # Asosiy ko'rsatkichlar qatori
        kpi = ttk.Frame(self.parent)
        kpi.pack(fill="x", padx=8, pady=(0,6))
        self.kpi_vars = {}
        for label, key in [("KI", "ki"), ("SKI", "ski"),
                            ("F (kritik)", "f_count"), ("k (zaxira)", "k_reserve"),
                            ("K% (kompleks.)", "complexity")]:
            f = tk.Frame(kpi, bg=COLORS["white"],
                         relief="flat", bd=1,
                         highlightbackground=COLORS["border"],
                         highlightthickness=1)
            f.pack(side="left", padx=4, pady=2, ipadx=12, ipady=6)
            tk.Label(f, text=label, bg=COLORS["white"],
                     font=("Segoe UI", 8), fg=COLORS["text_light"]).pack()
            var = tk.StringVar(value="—")
            tk.Label(f, textvariable=var, bg=COLORS["white"],
                     font=("Segoe UI", 13, "bold"),
                     fg=COLORS["accent"]).pack()
            self.kpi_vars[key] = var

        # Pastki qism: chapda — moddalar, o'ngda — dinamika
        body = ttk.Frame(self.parent)
        body.pack(fill="both", expand=True, padx=8, pady=(0,8))

        # Chap — moddalar natijalari
        left = ttk.LabelFrame(body, text="  📋  Moddalar bo'yicha natijalar  ")
        left.pack(side="left", fill="both", expand=True, padx=(0,4))

        self._build_substances_table(left)

        # O'ng — ko'p yillik dinamika
        right = ttk.LabelFrame(body, text="  📈  Ko'p yillik dinamika  ")
        right.pack(side="left", fill="y", padx=(4,0), ipadx=4)
        right.configure(width=260)

        self._build_trend_table(right)

    def _build_substances_table(self, parent):
        cols = ("name","ni","ni_x","alpha","beta","s_alpha",
                "s_beta","s_ij","critical")
        self.tree_sub = ttk.Treeview(parent, columns=cols,
                                     show="headings", height=22)
        headers = [("name","Modda",160), ("ni","ni",45),
                   ("ni_x","ni'",45), ("alpha","α (%)",65),
                   ("beta","β' (o'rt.)",80), ("s_alpha","Sα",55),
                   ("s_beta","Sβ",55), ("s_ij","Sij",60),
                   ("critical","Holat",80)]
        for col, text, w in headers:
            self.tree_sub.heading(col, text=text,
                                  command=lambda c=col: self._sort(c))
            self.tree_sub.column(col, width=w,
                                 anchor="center" if col != "name" else "w")

        sb = ttk.Scrollbar(parent, orient="vertical",
                           command=self.tree_sub.yview)
        self.tree_sub.configure(yscrollcommand=sb.set)
        self.tree_sub.pack(side="left", fill="both",
                           expand=True, padx=(6,0), pady=6)
        sb.pack(side="left", fill="y", pady=6)

        self.tree_sub.tag_configure("critical", background="#FADBD8",
                                    foreground="#C0392B", font=("Segoe UI",9,"bold"))
        self.tree_sub.tag_configure("normal",   background="#D5F5E3")
        self.tree_sub.tag_configure("zero",     background=COLORS["bg"],
                                    foreground=COLORS["text_light"])

    def _build_trend_table(self, parent):
        ttk.Label(parent, text="Yil → Sinf → SKI",
                  font=("Segoe UI",9,"bold")).pack(padx=6, pady=(6,2))

        cols = ("year","class","ski")
        self.tree_trend = ttk.Treeview(parent, columns=cols,
                                       show="headings", height=22)
        self.tree_trend.heading("year",  text="Yil")
        self.tree_trend.heading("class", text="Sinf")
        self.tree_trend.heading("ski",   text="SKI")
        self.tree_trend.column("year",  width=55,  anchor="center")
        self.tree_trend.column("class", width=90,  anchor="center")
        self.tree_trend.column("ski",   width=75,  anchor="center")

        for cls in range(1,6):
            self.tree_trend.tag_configure(
                f"cls{cls}",
                background=get_class_color(cls),
                foreground="#FFFFFF" if cls >= 4 else "#2C3E50")

        sb = ttk.Scrollbar(parent, orient="vertical",
                           command=self.tree_trend.yview)
        self.tree_trend.configure(yscrollcommand=sb.set)
        self.tree_trend.pack(side="left", fill="both",
                             expand=True, padx=(6,0), pady=4)
        sb.pack(side="left", fill="y", pady=4)

    # ── Yangilash ────────────────────────────
    def on_project_changed(self, event=None):
        pid = self.app.current_project_id
        if not pid:
            self._clear()
            return

        years = db.get_available_years(pid)
        self.cmb_year["values"] = [str(y) for y in years]

        self._load_trend(pid)

        if years:
            cur = self.cmb_year.get()
            if cur not in [str(y) for y in years]:
                self.cmb_year.set(str(years[-1]))
            self._load_results(pid, int(self.cmb_year.get()))
        else:
            self._clear()

    def _on_year_change(self, event=None):
        pid = self.app.current_project_id
        if not pid: return
        try:
            year = int(self.cmb_year.get())
            self._load_results(pid, year)
        except Exception:
            pass

    def _load_results(self, pid, year):
        self.tree_sub.delete(*self.tree_sub.get_children())

        final = db.get_final_result(pid, year)
        if not final:
            self._reset_kpis()
            self.lbl_class.config(text="Hisob o'tkazilmagan",
                                  bg=COLORS["border"])
            return

        # KPI
        self.kpi_vars["ki"].set(f"{final['ki']:.2f}" if final["ki"] else "—")
        self.kpi_vars["ski"].set(f"{final['ski']:.4f}" if final["ski"] else "—")
        self.kpi_vars["f_count"].set(str(final["f_count"] or 0))

        # k zaxira: manfiy bo'lmasin, F>=6 da 0 ko'rsatiladi
        k_val = final["k_reserve"]
        if k_val is not None:
            k_display = max(0.0, k_val)
            k_text = f"{k_display:.2f}" + (" ⚠️" if (final["f_count"] or 0) >= 6 else "")
        else:
            k_text = "—"
        self.kpi_vars["k_reserve"].set(k_text)

        # K% hisoblash — MPC dan oshgan moddalar ulushi
        subs_for_k = db.get_substance_results(pid, year)
        if subs_for_k:
            n_total  = len(subs_for_k)
            n_exceed = sum(1 for s in subs_for_k if (s["ni_exceed"] or 0) > 0)
            k_pct    = (n_exceed / n_total) * 100
            self.kpi_vars["complexity"].set(f"{k_pct:.1f}%")
        else:
            self.kpi_vars["complexity"].set("—")

        wc  = final["water_class"] or 0
        # DB da saqlangan to'liq daraja tavsifini ishlatamiz
        lbl = final["class_label"] or CLASS_LABELS.get(wc, "—")
        bg  = get_class_color(wc)
        fg  = "#FFFFFF" if wc >= 4 else "#2C3E50"
        self.lbl_class.config(text=f"  {lbl}  ", bg=bg, fg=fg)

        # Moddalar
        subs = db.get_substance_results(pid, year)
        for s in subs:
            is_crit = s["s_ij"] and s["s_ij"] >= 9
            is_zero = not s["ni_exceed"]
            tag = "critical" if is_crit else ("zero" if is_zero else "normal")

            self.tree_sub.insert("", "end",
                values=(
                    s["sub_name"],
                    s["ni"] or "—",
                    s["ni_exceed"] or 0,
                    f"{s['alpha']:.1f}%" if s["alpha"] is not None else "—",
                    f"{s['beta_avg']:.3f}" if s["beta_avg"] else "—",
                    f"{s['s_alpha']:.3f}" if s["s_alpha"] else "—",
                    f"{s['s_beta']:.3f}" if s["s_beta"] else "—",
                    f"{s['s_ij']:.3f}" if s["s_ij"] else "—",
                    "⚠️ KRITIK" if is_crit else ("✓ Norma" if not is_zero else "○ Oshmas"),
                ),
                tags=(tag,))

    def _load_trend(self, pid):
        self.tree_trend.delete(*self.tree_trend.get_children())
        finals = db.get_all_final_results(pid)
        for f in finals:
            wc  = f["water_class"] or 0
            tag = f"cls{wc}" if 1 <= wc <= 5 else ""
            self.tree_trend.insert("", "end",
                values=(f["year"],
                        f"{wc}-sinf" if wc else "—",
                        f"{f['ski']:.3f}" if f["ski"] else "—"),
                tags=(tag,))

    def _clear(self):
        self.tree_sub.delete(*self.tree_sub.get_children())
        self.tree_trend.delete(*self.tree_trend.get_children())
        self._reset_kpis()
        self.lbl_class.config(text="Sinf: —", bg=COLORS["border"], fg=COLORS["white"])

    def _reset_kpis(self):
        for v in self.kpi_vars.values():
            v.set("—")

    def _sort(self, col):
        """Ustun bo'yicha saralash."""
        data = [(self.tree_sub.set(k, col), k)
                for k in self.tree_sub.get_children("")]
        try:
            data.sort(key=lambda x: float(x[0].replace("%","").replace("—","0")),
                      reverse=True)
        except Exception:
            data.sort(reverse=True)
        for i, (_, k) in enumerate(data):
            self.tree_sub.move(k, "", i)
