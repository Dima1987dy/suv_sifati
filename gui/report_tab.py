"""
report_tab.py — Hisobot: Excel eksport, shablon import
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db
from gui.main_window import COLORS, get_class_color


class ReportTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app    = app
        self._build()

    def _build(self):
        # Sarlavha
        hdr = tk.Frame(self.parent, bg=COLORS["sidebar"], height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📄  Hisobot va Ma'lumot Almashinuvi",
                 bg=COLORS["sidebar"], fg=COLORS["sidebar_text"],
                 font=("Segoe UI",12,"bold")).pack(side="left", padx=16, pady=10)

        body = ttk.Frame(self.parent)
        body.pack(fill="both", expand=True, padx=12, pady=12)

        # 3 ustun karta
        self._card_excel_export(body)
        self._card_excel_import(body)
        self._card_substances(body)

        # Quyi — barcha natijalar jadvali
        self._build_summary_table()

    def _card(self, parent, title, icon, side="left"):
        f = tk.Frame(parent, bg=COLORS["white"],
                     relief="flat", bd=0,
                     highlightbackground=COLORS["border"],
                     highlightthickness=1)
        f.pack(side=side, fill="both", expand=True,
               padx=6, pady=4, ipadx=12, ipady=12)
        tk.Label(f, text=f"{icon}  {title}",
                 bg=COLORS["white"], fg=COLORS["accent"],
                 font=("Segoe UI",11,"bold")).pack(anchor="w", pady=(0,8))
        return f

    def _card_excel_export(self, parent):
        f = self._card(parent, "Excel Hisobot Eksport", "📊")
        tk.Label(f, text="Hisob natijalarini Excel formatida saqlash.",
                 bg=COLORS["white"], fg=COLORS["text_light"],
                 wraplength=220, justify="left").pack(anchor="w", pady=(0,8))

        # Yil tanlash
        yf = ttk.Frame(f)
        yf.pack(fill="x", pady=(0,8))
        ttk.Label(yf, text="Yil:").pack(side="left")
        self.cmb_exp_year = ttk.Combobox(yf, width=8, state="readonly")
        self.cmb_exp_year.pack(side="left", padx=6)

        ttk.Button(f, text="📊 Excel eksport qilish",
                   style="Success.TButton",
                   command=self.export_excel).pack(fill="x", pady=2)
        ttk.Button(f, text="📋 Shablon yuklab olish",
                   command=self.download_template).pack(fill="x", pady=2)

    def _card_excel_import(self, parent):
        f = self._card(parent, "Excel Ma'lumot Import", "📥")
        tk.Label(f,
            text="To'ldirilgan shablonni yuklash.\n"
                 "Avtomatik moddalar sinxronlashtiriladi.",
            bg=COLORS["white"], fg=COLORS["text_light"],
            wraplength=220, justify="left").pack(anchor="w", pady=(0,12))

        ttk.Button(f, text="📥 Excel fayldan import",
                   command=self.import_excel).pack(fill="x", pady=2)

        ttk.Separator(f, orient="horizontal").pack(fill="x", pady=8)
        tk.Label(f, text="⚠️  Import oldidan stansiyani tanlang\n"
                         "('Loyihalar' tabida)",
                 bg=COLORS["white"], fg=COLORS["warning"],
                 font=("Segoe UI",8)).pack(anchor="w")

    def _card_substances(self, parent):
        f = self._card(parent, "Moddalar Boshqaruvi", "🧪")
        tk.Label(f,
            text="Yangi moddalar qo'shish yoki\n"
                 "MPC qiymatlarini tahrirlash.",
            bg=COLORS["white"], fg=COLORS["text_light"],
            wraplength=220, justify="left").pack(anchor="w", pady=(0,8))

        ttk.Button(f, text="🧪 Moddalar ro'yxati",
                   command=self._open_substances).pack(fill="x", pady=2)

    def _build_summary_table(self):
        sep = ttk.LabelFrame(self.parent,
                             text="  📋  Barcha loyihalar — Yakuniy natijalar  ")
        sep.pack(fill="both", expand=True, padx=12, pady=(0,12))

        cols = ("project","station","year","class","label","ki","ski","f")
        self.tree_all = ttk.Treeview(sep, columns=cols,
                                     show="headings", height=10)
        headers = [("project","Loyiha",160), ("station","Stansiya",120),
                   ("year","Yil",55), ("class","Sinf",55),
                   ("label","Tavsif",140), ("ki","KI",70),
                   ("ski","SKI",70), ("f","F (kritik)",80)]
        for col, txt, w in headers:
            self.tree_all.heading(col, text=txt)
            self.tree_all.column(col, width=w,
                                 anchor="center" if col not in ("project","label","station")
                                 else "w")

        for cls in range(1,6):
            self.tree_all.tag_configure(
                f"cls{cls}", background=get_class_color(cls),
                foreground="#FFFFFF" if cls >= 4 else "#2C3E50")

        sb = ttk.Scrollbar(sep, orient="vertical",
                           command=self.tree_all.yview)
        self.tree_all.configure(yscrollcommand=sb.set)
        self.tree_all.pack(side="left", fill="both",
                           expand=True, padx=(6,0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        ttk.Button(sep, text="🔄",
                   command=self._load_all_results).pack(
            side="bottom", padx=6, pady=4)

        self._load_all_results()

    def _load_all_results(self):
        self.tree_all.delete(*self.tree_all.get_children())
        projects = db.get_all_projects()
        for p in projects:
            finals = db.get_all_final_results(p["id"])
            for f in finals:
                wc  = f["water_class"] or 0
                tag = f"cls{wc}" if 1 <= wc <= 5 else ""
                self.tree_all.insert("", "end",
                    values=(p["name"], "—", f["year"],
                            f"{wc}" if wc else "—",
                            f["class_label"] or "—",
                            f"{f['ki']:.2f}" if f["ki"] else "—",
                            f"{f['ski']:.3f}" if f["ski"] else "—",
                            f["f_count"] or 0),
                    tags=(tag,))

    # ── Hodisalar ────────────────────────────
    def on_project_changed(self, event=None):
        pid = self.app.current_project_id
        if not pid:
            return
        years = db.get_available_years(pid)
        self.cmb_exp_year["values"] = [str(y) for y in years]
        if years:
            self.cmb_exp_year.set(str(years[-1]))
        self._load_all_results()

    # ── Excel eksport ─────────────────────────
    def export_excel(self):
        pid = self.app.current_project_id
        if not pid:
            messagebox.showwarning("Xato","Avval loyiha tanlang.",
                                   parent=self.parent)
            return
        year_str = self.cmb_exp_year.get()
        if not year_str:
            messagebox.showwarning("Xato","Yil tanlanmagan.",
                                   parent=self.parent)
            return
        year = int(year_str)
        project = db.get_project(pid)

        default_name = (f"{project['name'].replace(' ','_')}_{year}_"
                        f"{datetime.now().strftime('%Y%m%d')}.xlsx")
        path = filedialog.asksaveasfilename(
            title="Hisobotni saqlash",
            defaultextension=".xlsx",
            filetypes=[("Excel fayli","*.xlsx")],
            initialfile=default_name,
            parent=self.parent)
        if not path: return

        from excel_io import export_results
        export_results(path, pid, year)
        self.app.set_status(f"Hisobot saqlandi: {path}")
        messagebox.showinfo("✅ Tayyor",
            f"Hisobot saqlandi:\n{path}",
            parent=self.parent)

    def download_template(self):
        pid = self.app.current_project_id
        path = filedialog.asksaveasfilename(
            title="Shablonni saqlash",
            defaultextension=".xlsx",
            filetypes=[("Excel fayli","*.xlsx")],
            initialfile="olchov_shablon.xlsx",
            parent=self.parent)
        if not path: return
        from excel_io import create_template
        create_template(path, pid)
        self.app.set_status(f"Shablon saqlandi: {path}")
        messagebox.showinfo("✅ Tayyor",
            f"Shablon saqlandi:\n{path}\n\n"
            "To'ldiring va 'Excel import' orqali yuklang.",
            parent=self.parent)

    def import_excel(self):
        pid = self.app.current_project_id
        if not pid:
            messagebox.showwarning("Xato","Avval loyiha tanlang.",
                                   parent=self.parent)
            return
        path = filedialog.askopenfilename(
            title="Excel faylni tanlang",
            filetypes=[("Excel fayli","*.xlsx *.xls")],
            parent=self.parent)
        if not path: return

        sid = self.app.current_station_id
        from excel_io import import_from_excel, ImportError as ImpErr
        try:
            res = import_from_excel(path, pid, sid)
        except ImpErr as e:
            messagebox.showerror("Import xatosi", str(e), parent=self.parent)
            return

        msg = (f"✅ Import muvaffaqiyatli!\n\n"
               f"Loyiha:         {res.get('project_name','—')}\n"
               f"Import qilindi: {res['imported']} ta o'lchov\n"
               f"O'tkazildi:     {res['skipped']} ta\n")
        mpc_upd = res.get("mpc_updated", [])
        if mpc_upd:
            msg += f"\n📊 MPC yangilandi ({len(mpc_upd)} ta):\n"
            msg += "\n".join(mpc_upd[:5])
        if res["errors"]:
            msg += f"\n\n⚠️ Xatolar ({len(res['errors'])} ta):\n"
            msg += "\n".join(res["errors"][:5])

        self._load_all_results()
        self.app.set_status(f"Import: {res['imported']} ta o'lchov.")
        messagebox.showinfo("Import natijasi", msg, parent=self.parent)

    # ── Moddalar boshqaruvi ───────────────────
    def _open_substances(self):
        _SubstancesWindow(self.parent, self.app)


# ─────────────────────────────────────────────
#  Moddalar boshqaruvi oynasi
# ─────────────────────────────────────────────
class _SubstancesWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Moddalar va MPC qiymatlari")
        self.geometry("800x520")
        self.configure(bg=COLORS["bg"])
        self._build()
        self._load()

    def _build(self):
        # ── Toolbar ──────────────────────────────────────────────
        tb = ttk.Frame(self)
        tb.pack(fill="x", padx=8, pady=6)

        ttk.Button(tb, text="➕ Yangi modda",
                   style="Success.TButton",
                   command=self._add).pack(side="left", padx=2)
        ttk.Button(tb, text="✏️ Tahrirlash",
                   command=self._edit).pack(side="left", padx=2)
        ttk.Button(tb, text="🗑 O'chirish",
                   style="Danger.TButton",
                   command=self._delete).pack(side="left", padx=2)

        ttk.Separator(tb, orient="vertical").pack(
            side="left", fill="y", padx=10, pady=3)

        tk.Label(tb, text="Tartib:",
                 bg=COLORS["bg"],
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(tb, text="⬆  Yuqoriga",
                   command=self._move_up).pack(side="left", padx=2)
        ttk.Button(tb, text="⬇  Pastga",
                   command=self._move_down).pack(side="left", padx=2)
        ttk.Button(tb, text="🔢 Qayta raqamlash",
                   command=self._reindex).pack(side="left", padx=6)

        # ── Body: jadval + yo'riqnoma ────────────────────────────
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=4, pady=(0,4))

        cols = ("order", "name", "mpc", "unit", "hazard", "is_o2")
        self.tree = ttk.Treeview(body, columns=cols,
                                 show="headings", height=20)
        hdrs = [("order","#",45), ("name","Modda nomi",220),
                ("mpc","MPC",90), ("unit","Birlik",75),
                ("hazard","Xavf",55), ("is_o2","Kislorod?",70)]
        for col, txt, w in hdrs:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w,
                             anchor="w" if col=="name" else "center")

        sb = ttk.Scrollbar(body, orient="vertical",
                           command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both",
                       expand=True, padx=(4,0), pady=4)
        sb.pack(side="left", fill="y", pady=4)
        self.tree.bind("<Double-1>", lambda e: self._edit())

        # Yo'riqnoma paneli
        rp = tk.Frame(body, bg=COLORS["white"], width=175,
                      highlightbackground=COLORS["border"],
                      highlightthickness=1)
        rp.pack(side="left", fill="y", padx=(6,4), pady=4)
        rp.pack_propagate(False)

        tk.Label(rp, text="💡 Yo'riqnoma",
                 bg=COLORS["white"], fg=COLORS["accent"],
                 font=("Segoe UI",9,"bold")).pack(pady=(10,4), padx=8)

        for tip in [
            "Moddani tanlang,\nso'ng ⬆⬇ bilan\ntartibini o'zgartiring.",
            "───────────────",
            "Tartib o'zgartirilgach\nshablon yuklaganda\nhuddi shu tartibda\nchiqadi.",
            "───────────────",
            "🔢 Qayta raqamlash\ntartibni 1 dan\nboshlab belgilaydi.",
            "───────────────",
            "\u26a0\ufe0f  O'chirish\no'lchovlarni ham\no'chiradi!",
        ]:
            tk.Label(rp, text=tip,
                     bg=COLORS["white"],
                     fg=COLORS["text_light"] if "───" in tip else COLORS["text"],
                     font=("Segoe UI",8),
                     justify="left", wraplength=160,
                     anchor="w").pack(anchor="w", padx=8, pady=1)

    def _load(self):
        sel_id = self._selected_id()
        self.tree.delete(*self.tree.get_children())
        for i, s in enumerate(db.get_all_substances(), start=1):
            self.tree.insert("", "end", iid=str(s["id"]),
                values=(i,
                        ("🔵 " if s["is_oxygen"] else "    ") + s["name"],
                        s["mpc"],
                        s["unit"] or "mg/dm3",
                        s["hazard_class"] or 3,
                        "Ha ↓" if s["is_oxygen"] else "Yo'q"))
        # Tanlangan modda saqlansin
        if sel_id and self.tree.exists(str(sel_id)):
            self.tree.selection_set(str(sel_id))
            self.tree.see(str(sel_id))

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _move_up(self):
        sid = self._selected_id()
        if not sid:
            messagebox.showwarning("Tanlang",
                "Avval moddani tanlang.", parent=self)
            return
        subs = db.get_all_substances()
        ids  = [s["id"] for s in subs]
        idx  = ids.index(sid)
        if idx == 0:
            return
        db.swap_substance_order(ids[idx], ids[idx-1])
        self._load()

    def _move_down(self):
        sid = self._selected_id()
        if not sid:
            messagebox.showwarning("Tanlang",
                "Avval moddani tanlang.", parent=self)
            return
        subs = db.get_all_substances()
        ids  = [s["id"] for s in subs]
        idx  = ids.index(sid)
        if idx == len(ids) - 1:
            return
        db.swap_substance_order(ids[idx], ids[idx+1])
        self._load()

    def _reindex(self):
        db.reindex_substances()
        self._load()
        messagebox.showinfo("✅ Tayyor",
            "Tartib raqamlari 1 dan qayta belgilandi.",
            parent=self)

    def _add(self):
        _SubstanceDialog(self, self.app, self, substance=None)

    def _edit(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Tanlang",
                "Modda tanlang.", parent=self)
            return
        _SubstanceDialog(self, self.app, self,
                         substance=db.get_substance(int(sel[0])))

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        name = self.tree.item(sel[0])["values"][1].strip()
        if not messagebox.askyesno("O'chirish",
            f"'{name}' moddasini o'chirasizmi?\n"
            "Bu modda bilan bog'liq o'lchovlar ham o'chadi!",
            parent=self):
            return
        db.delete_substance(int(sel[0]))
        self._load()


class _SubstanceDialog(tk.Toplevel):
    def __init__(self, parent, app, win, substance=None):
        super().__init__(parent)
        self.app = app; self.win = win; self.substance = substance
        self.title("Yangi modda" if substance is None else "Modda tahrirlash")
        self.geometry("380x280"); self.resizable(False,False)
        self.configure(bg=COLORS["bg"]); self.grab_set()

        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        fields = [
            ("Modda nomi *",  "ent_name",  ""),
            ("MPC qiymati *", "ent_mpc",   ""),
            ("Birlik",        "ent_unit",  "mg/dm3"),
            ("Xavf sinfi (1-4)", "ent_haz","3"),
        ]
        for i,(lbl,attr,default) in enumerate(fields):
            ttk.Label(frm, text=lbl).grid(row=i,column=0,sticky="w",
                                          padx=(0,8),pady=4)
            ent = ttk.Entry(frm, width=26)
            ent.grid(row=i,column=1,sticky="ew",pady=4)
            ent.insert(0, default)
            setattr(self,attr,ent)

        self.is_oxygen_var = tk.BooleanVar()
        ttk.Checkbutton(frm, text="Kislorod (teskari hisob ↓)",
                        variable=self.is_oxygen_var).grid(
            row=4,column=0,columnspan=2,sticky="w",pady=6)

        bf = ttk.Frame(frm); bf.grid(row=5,column=0,columnspan=2,sticky="e")
        ttk.Button(bf,text="Bekor",command=self.destroy).pack(side="right",padx=(6,0))
        ttk.Button(bf,text="💾 Saqlash",style="Success.TButton",
                   command=self._save).pack(side="right")

        if substance:
            self.ent_name.delete(0,"end"); self.ent_name.insert(0, substance["name"])
            self.ent_mpc.delete(0,"end");  self.ent_mpc.insert(0, str(substance["mpc"]))
            self.ent_unit.delete(0,"end"); self.ent_unit.insert(0, substance["unit"] or "mg/dm3")
            self.ent_haz.delete(0,"end");  self.ent_haz.insert(0, str(substance["hazard_class"] or 3))
            self.is_oxygen_var.set(bool(substance["is_oxygen"]))
        self.ent_name.focus()

    def _save(self):
        name = self.ent_name.get().strip()
        if not name:
            messagebox.showwarning("Xato","Modda nomi bo'sh.",parent=self); return
        try:
            mpc = float(self.ent_mpc.get().replace(",","."))
            haz = int(self.ent_haz.get())
            if not (1 <= haz <= 4): raise ValueError
        except ValueError:
            messagebox.showwarning("Xato","MPC raqam, xavf sinfi 1-4 bo'lishi kerak.",
                                   parent=self); return
        unit    = self.ent_unit.get().strip() or "mg/dm3"
        is_oxy  = self.is_oxygen_var.get()
        if self.substance is None:
            db.add_substance(name, mpc, unit, haz, is_oxy)
        else:
            db.update_substance(self.substance["id"], name, mpc, unit, haz, is_oxy)
        self.win._load()
        self.destroy()
