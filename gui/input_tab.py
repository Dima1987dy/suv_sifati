"""
input_tab.py — O'lchov ma'lumotlarini kiritish (qo'lda + Excel import)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date
import threading
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db
import calculations as calc
from gui.main_window import COLORS


class InputTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app    = app
        self._build()

    # ── Layout ───────────────────────────────
    def _build(self):
        # Yuqori panel — loyiha/stansiya/yil tanlash
        top = ttk.LabelFrame(self.parent, text="  ⚙️  Sozlamalar  ")
        top.pack(fill="x", padx=8, pady=(8,4))

        tf = ttk.Frame(top)
        tf.pack(fill="x", padx=8, pady=6)

        # Stansiya
        ttk.Label(tf, text="Punkt:").pack(side="left")
        self.cmb_station = ttk.Combobox(tf, width=28, state="readonly")
        self.cmb_station.pack(side="left", padx=(4,16))
        self.cmb_station.bind("<<ComboboxSelected>>", self._on_station_change)

        # Yil — namuna sanasidan avtomatik aniqlanadi
        ttk.Label(tf, text="Hisob yili:").pack(side="left")
        self.cmb_year = ttk.Combobox(tf, width=8, state="readonly")
        self.cmb_year["values"] = [str(y) for y in range(2010, 2031)]
        self.cmb_year.set(str(date.today().year))
        self.cmb_year.pack(side="left", padx=(4,4))
        ttk.Label(tf, text="(sanadan avtomatik)",
                  font=("Segoe UI",8),
                  foreground=COLORS["text_light"]).pack(side="left", padx=(0,16))
        self.cmb_year.bind("<<ComboboxSelected>>", self._on_year_change)

        # Excel tugmalari
        ttk.Button(tf, text="📥 Excel import",
                   command=self.import_excel).pack(side="right", padx=4)
        ttk.Button(tf, text="📋 Shablon yuklab olish",
                   command=self.download_template).pack(side="right", padx=4)

        # Quyi qism: chap — kiritish, o'ng — mavjud o'lchovlar
        body = ttk.Frame(self.parent)
        body.pack(fill="both", expand=True, padx=8, pady=(0,8))

        # Chap — qo'lda kiritish
        left = ttk.LabelFrame(body, text="  ✍️  Qo'lda kiritish  ")
        left.pack(side="left", fill="both", expand=True, padx=(0,4))

        self._build_manual_input(left)

        # O'ng — mavjud o'lchovlar jadvali
        right = ttk.LabelFrame(body, text="  📊  Kiritilgan o'lchovlar  ")
        right.pack(side="left", fill="both", expand=True, padx=(4,0))

        self._build_records_table(right)

    def _build_manual_input(self, parent):
        # Sana
        sf = ttk.Frame(parent)
        sf.pack(fill="x", padx=8, pady=(8,4))
        ttk.Label(sf, text="Namuna sanasi:").pack(side="left")
        self.ent_date = ttk.Entry(sf, width=14)
        self.ent_date.insert(0, str(date.today()))
        self.ent_date.pack(side="left", padx=(4,0))
        ttk.Label(sf, text="(YYYY-MM-DD)",
                  font=("Segoe UI",8), foreground=COLORS["text_light"]
                  ).pack(side="left", padx=4)

        # Moddalar ro'yxati (scrollable)
        ttk.Label(parent, text="Konsentratsiyalar (mg/dm³):",
                  font=("Segoe UI",9,"bold")).pack(anchor="w", padx=8, pady=(4,2))

        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill="both", expand=True, padx=4, pady=2)

        self.canvas = tk.Canvas(canvas_frame, bg=COLORS["white"],
                                highlightthickness=0)
        sb = ttk.Scrollbar(canvas_frame, orient="vertical",
                           command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

        self.sub_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window(
            (0,0), window=self.sub_frame, anchor="nw")
        self.sub_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Moddalar satrlari
        self.sub_entries: dict[int, ttk.Entry] = {}
        self._build_substance_entries()

        # Tugmalar — BIRINCHI pack qilinadi (pastda doim ko'rinib tursin)
        bf = ttk.Frame(parent)
        bf.pack(side="bottom", fill="x", padx=8, pady=6)
        ttk.Button(bf, text="💾 Saqlash", style="Success.TButton",
                   command=self._save_manual).pack(side="left")
        ttk.Button(bf, text="🔄 Tozalash",
                   command=self._clear_entries).pack(side="left", padx=6)
        self._btn_calc = ttk.Button(bf, text="⚡ Saqlash va Hisoblash",
                                    style="Success.TButton",
                                    command=self._run_calculation)
        self._btn_calc.pack(side="right")

        # Oylik holat paneli
        month_lf = ttk.LabelFrame(parent, text="  📅  Oylik namunalar holati  ")
        month_lf.pack(side="bottom", fill="x", padx=8, pady=(0,2))
        self.month_frame = ttk.Frame(month_lf)
        self.month_frame.pack(fill="x", padx=6, pady=6)
        self._build_month_indicators()

    def _build_substance_entries(self):
        for w in self.sub_frame.winfo_children():
            w.destroy()
        self.sub_entries.clear()

        substances = db.get_all_substances()

        # Sarlavha
        ttk.Label(self.sub_frame, text="Modda",
                  font=("Segoe UI",9,"bold"),
                  width=26).grid(row=0,column=0,sticky="w",padx=4,pady=2)
        ttk.Label(self.sub_frame, text="MPC",
                  font=("Segoe UI",9,"bold"),
                  width=10).grid(row=0,column=1,padx=4,pady=2)
        ttk.Label(self.sub_frame, text="Qiymat",
                  font=("Segoe UI",9,"bold"),
                  width=12).grid(row=0,column=2,padx=4,pady=2)

        ttk.Separator(self.sub_frame,orient="horizontal").grid(
            row=1,column=0,columnspan=3,sticky="ew",pady=2)

        for i, s in enumerate(substances, start=2):
            bg = COLORS["bg"] if i % 2 == 0 else COLORS["white"]
            lbl = ttk.Label(self.sub_frame,
                            text=("🔵 " if s["is_oxygen"] else "  ") + s["name"],
                            width=26, background=bg)
            lbl.grid(row=i, column=0, sticky="w", padx=4, pady=1)

            ttk.Label(self.sub_frame,
                      text=f"{s['mpc']} {'↓' if s['is_oxygen'] else '↑'}",
                      width=10, foreground=COLORS["text_light"],
                      background=bg).grid(row=i, column=1, padx=4, pady=1)

            ent = ttk.Entry(self.sub_frame, width=12)
            ent.grid(row=i, column=2, padx=4, pady=1)
            self.sub_entries[s["id"]] = ent

    def _build_records_table(self, parent):
        # Filter — 1-qator: Modda va Sana
        ff = ttk.Frame(parent)
        ff.pack(fill="x", padx=6, pady=(6,2))

        # Modda filter
        ttk.Label(ff, text="Modda:").pack(side="left")
        self.cmb_filter_sub = ttk.Combobox(ff, width=18, state="readonly")
        self.cmb_filter_sub.pack(side="left", padx=(4, 12))
        self.cmb_filter_sub.bind("<<ComboboxSelected>>", self._on_filter_sub)

        # Sana filter
        ttk.Label(ff, text="Sana:").pack(side="left")
        self.cmb_filter_date = ttk.Combobox(ff, width=13, state="readonly")
        self.cmb_filter_date.pack(side="left", padx=(4, 4))
        self.cmb_filter_date.bind("<<ComboboxSelected>>", self._on_filter_date)

        # Tozalash tugmasi
        ttk.Button(ff, text="✕",
                   width=2,
                   command=self._clear_filters).pack(side="left", padx=(0, 8))

        # O'chirish tugmasi — yil/oy/tanlangan
        del_btn = ttk.Menubutton(ff, text="🗑 O'chirish ▾",
                                  style="Danger.TButton",
                                  direction="below")
        del_menu = tk.Menu(del_btn, tearoff=0)
        del_menu.add_command(label="🗓  Tanlangan qatorlarni o'chirish",
                             command=self._delete_record)
        del_menu.add_separator()
        del_menu.add_command(label="📅  Joriy oyni o'chirish",
                             command=self._delete_by_month)
        del_menu.add_command(label="📆  Joriy yilni o'chirish",
                             command=self._delete_by_year)
        del_btn["menu"] = del_menu
        del_btn.pack(side="right", padx=4)

        cols = ("id","date","sub","conc","exceed")
        self.tree_rec = ttk.Treeview(parent, columns=cols,
                                     show="headings", height=20)
        self.tree_rec.heading("id",     text="#")
        self.tree_rec.heading("date",   text="Sana")
        self.tree_rec.heading("sub",    text="Modda")
        self.tree_rec.heading("conc",   text="Konsentratsiya")
        self.tree_rec.heading("exceed", text="MPC holati")
        self.tree_rec.column("id",     width=40,  anchor="center")
        self.tree_rec.column("date",   width=100, anchor="center")
        self.tree_rec.column("sub",    width=160)
        self.tree_rec.column("conc",   width=110, anchor="center")
        self.tree_rec.column("exceed", width=100, anchor="center")

        sb = ttk.Scrollbar(parent, orient="vertical",
                           command=self.tree_rec.yview)
        self.tree_rec.configure(yscrollcommand=sb.set)
        self.tree_rec.pack(side="left", fill="both",
                           expand=True, padx=(6,0), pady=4)
        sb.pack(side="left", fill="y", pady=4)

        # Ranglar teglari
        self.tree_rec.tag_configure("exceed", background="#FADBD8")
        self.tree_rec.tag_configure("ok",     background="#D5F5E3")
        self.tree_rec.tag_configure("none",   background=COLORS["bg"])

        # Ikki marta bosish → tahrirlash
        self.tree_rec.bind("<Double-1>", self._on_edit_record)

    # ── Canvas scroll ─────────────────────────
    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    # ── Hodisalar ────────────────────────────
    def on_project_changed(self):
        pid = self.app.current_project_id
        if not pid:
            self.cmb_station["values"] = []
            self.cmb_station.set("")
            return
        stations = db.get_stations(pid)
        self._station_map = {s["name"]: s["id"] for s in stations}
        self.cmb_station["values"] = [s["name"] for s in stations]
        if stations:
            self.cmb_station.set(stations[0]["name"])
            self.app._current_station_id = stations[0]["id"]
            self._load_records()
            self.refresh_month_indicators()

    def on_station_changed(self):
        self._load_records()

    def _on_station_change(self, event=None):
        name = self.cmb_station.get()
        if hasattr(self, "_station_map") and name in self._station_map:
            self.app._current_station_id = self._station_map[name]
        self._load_records()

    def _on_year_change(self, event=None):
        self.app._current_year = int(self.cmb_year.get())
        self._load_records()
        self.refresh_month_indicators()

    # ── Filter hodisalari ─────────────────────
    def _on_filter_sub(self, event=None):
        """Modda tanlanganda — sana filterni tozalaymiz."""
        self.cmb_filter_date.set("Barcha sanalar")
        self._load_records()

    def _on_filter_date(self, event=None):
        """Sana tanlanganda — modda filterni tozalaymiz."""
        self.cmb_filter_sub.set("Barcha moddalar")
        self._load_records()

    def _clear_filters(self):
        """Ikkala filterni ham tozalash."""
        self.cmb_filter_sub.set("Barcha moddalar")
        self.cmb_filter_date.set("Barcha sanalar")
        self._load_records()

    # ── O'lchovlarni yuklash ──────────────────
    def _load_records(self, event=None):
        pid  = self.app.current_project_id
        sid  = self.app.current_station_id
        year = self._get_year()
        if not pid or not year:
            return

        all_subs = db.get_all_substances()

        # Modda combobox ni to'ldirish
        self.cmb_filter_sub["values"] = (
            ["Barcha moddalar"] + [s["name"] for s in all_subs]
        )
        if not self.cmb_filter_sub.get():
            self.cmb_filter_sub.set("Barcha moddalar")

        # Sana combobox ni to'ldirish (DB dan mavjud sanalar)
        available_dates = db.get_available_dates(pid, year, sid)
        self.cmb_filter_date["values"] = (
            ["Barcha sanalar"] + available_dates
        )
        if not self.cmb_filter_date.get():
            self.cmb_filter_date.set("Barcha sanalar")

        # Qaysi filter aktiv?
        filter_name = self.cmb_filter_sub.get()
        filter_date = self.cmb_filter_date.get()

        sub_id_filter  = None
        date_filter    = None

        if filter_name and filter_name != "Barcha moddalar":
            sub_id_filter = next(
                (s["id"] for s in all_subs if s["name"] == filter_name), None)

        if filter_date and filter_date != "Barcha sanalar":
            date_filter = filter_date

        # Ma'lumotlarni olish
        measurements = db.get_measurements(pid, year, sub_id_filter)

        # Sana bo'yicha qo'shimcha filter (xotirada)
        if date_filter:
            measurements = [m for m in measurements
                            if m["sample_date"] == date_filter]

        self.tree_rec.delete(*self.tree_rec.get_children())
        sub_dict = {s["id"]: s for s in all_subs}

        for m in measurements:
            s     = sub_dict.get(m["substance_id"])
            mpc   = s["mpc"] if s else None
            conc  = m["concentration"]
            is_ox = s["is_oxygen"] if s else 0

            if conc is None:
                tag    = "none"
                status = "—"
            elif mpc is None:
                tag    = "none"
                status = "MPC yo'q"
            else:
                if is_ox:
                    exceeded = conc < mpc
                else:
                    exceeded = conc > mpc
                tag    = "exceed" if exceeded else "ok"
                ratio  = (mpc / conc if is_ox and conc > 0
                          else conc / mpc) if mpc else 0
                status = (f"↑ {ratio:.2f}x" if exceeded and not is_ox
                          else f"↓ {ratio:.2f}x" if exceeded
                          else "✓ Norma")

            self.tree_rec.insert("", "end",
                iid=str(m["id"]),
                values=(m["id"], m["sample_date"],
                        s["name"] if s else "?",
                        f"{conc}" if conc is not None else "—",
                        status),
                tags=(tag,))

    # ── Qo'lda saqlash ───────────────────────
    def _save_manual(self, silent=False):
        pid  = self.app.current_project_id
        sid  = self.app.current_station_id
        year = self._get_year()
        date_str = self.ent_date.get().strip()

        if not pid:
            messagebox.showwarning("Xato","Loyiha tanlanmagan.",parent=self.parent)
            return

        from datetime import datetime
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            # Yil comboboxni kiritilgan sana yiliga avtomatik moslashtirish
            entered_year = str(dt.year)
            if entered_year in self.cmb_year["values"]:
                self.cmb_year.set(entered_year)
                self.app._current_year = dt.year
        except ValueError:
            messagebox.showwarning("Xato",
                "Sana formati noto'g'ri.\nTo'g'ri: YYYY-MM-DD (masalan 2023-01-14)",
                parent=self.parent)
            return

        rows = []
        for sub_id, ent in self.sub_entries.items():
            val = ent.get().strip()
            if val == "":
                rows.append((pid, sid, sub_id, date_str, None))
            else:
                try:
                    c = float(val.replace(",","."))
                    rows.append((pid, sid, sub_id, date_str, c))
                except ValueError:
                    messagebox.showwarning("Xato",
                        f"Noto'g'ri qiymat: '{val}'\nFaqat raqam kiriting.",
                        parent=self.parent)
                    return

        # Faqat bo'sh bo'lmaganlarni saqlash
        non_empty = [r for r in rows if r[4] is not None]
        if not non_empty:
            if not silent:
                messagebox.showinfo("Ma'lumot","Hech qanday qiymat kiritilmadi.",
                                    parent=self.parent)
            return False

        db.add_measurements_with_station(non_empty)

        self._load_records()
        self.app.set_status(f"Saqlandi: {len(non_empty)} ta o'lchov ({date_str})")
        self.refresh_month_indicators()
        if not silent:
            messagebox.showinfo("✅ Saqlandi",
                f"{len(non_empty)} ta o'lchov saqlandi.\nSana: {date_str}",
                parent=self.parent)
        return True

    def _clear_entries(self):
        for ent in self.sub_entries.values():
            ent.delete(0, "end")

    def _on_edit_record(self, event=None):
        """Jadvalda ikki marta bosilganda tahrirlash oynasini ochadi."""
        sel = self.tree_rec.selection()
        if not sel:
            return
        meas_id = int(sel[0])
        row = db.get_measurement(meas_id)
        if not row:
            return
        self._open_edit_dialog(meas_id, row)

    def _open_edit_dialog(self, meas_id: int, row) -> None:
        """Tahrirlash dialog oynasi."""
        win = tk.Toplevel(self.parent)
        win.title("✏️  O'lchovni tahrirlash")
        win.geometry("380x260")
        win.resizable(False, False)
        win.configure(bg=COLORS["bg"])
        win.grab_set()   # modal

        # ── Header ───────────────────────────────
        hdr = tk.Frame(win, bg=COLORS["sidebar"], height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="✏️  O'lchovni tahrirlash",
                 bg=COLORS["sidebar"], fg=COLORS["sidebar_text"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=14, pady=10)

        # ── Ma'lumotlar ───────────────────────────
        frm = ttk.Frame(win)
        frm.pack(fill="both", expand=True, padx=18, pady=12)

        def lbl_row(text, value, row_num):
            ttk.Label(frm, text=text, foreground=COLORS["text_light"],
                      font=("Segoe UI", 9)).grid(
                row=row_num, column=0, sticky="w", pady=3)
            ttk.Label(frm, text=value, font=("Segoe UI", 9, "bold")).grid(
                row=row_num, column=1, sticky="w", padx=10, pady=3)

        lbl_row("Modda:",  row["sub_name"], 0)
        lbl_row("MPC:",    f"{row['mpc']} {row['unit']}", 1)

        # ── Sana ─────────────────────────────────
        ttk.Label(frm, text="Sana:",
                  foreground=COLORS["text_light"],
                  font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=3)
        ent_date = ttk.Entry(frm, width=16, font=("Segoe UI", 10))
        ent_date.insert(0, row["sample_date"] or "")
        ent_date.grid(row=2, column=1, sticky="w", padx=10, pady=3)

        # ── Konsentratsiya ────────────────────────
        is_ox = bool(row["is_oxygen"])
        arrow = "↓ (past bo'lsa oshgan)" if is_ox else "↑ (yuqori bo'lsa oshgan)"
        ttk.Label(frm, text=f"Qiymat ({arrow}):",
                  foreground=COLORS["text_light"],
                  font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", pady=3)

        ent_conc = ttk.Entry(frm, width=16, font=("Segoe UI", 10))
        cur_val  = row["concentration"]
        ent_conc.insert(0, str(cur_val) if cur_val is not None else "")
        ent_conc.grid(row=3, column=1, sticky="w", padx=10, pady=3)
        ent_conc.focus_set()
        ent_conc.select_range(0, "end")

        # ── Eslatma ───────────────────────────────
        ttk.Label(frm, text="Bo'sh qoldirsa — 'aniqlanmagan' saqlanadi.",
                  foreground=COLORS["text_light"],
                  font=("Segoe UI", 8)).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # ── Tugmalar ─────────────────────────────
        bf = ttk.Frame(win)
        bf.pack(fill="x", padx=18, pady=(0, 14))

        def save():
            date_str = ent_date.get().strip()
            val_str  = ent_conc.get().strip()

            # Sana tekshiruv
            from datetime import datetime as _dt
            try:
                _dt.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Xato",
                    "Sana formati noto'g'ri.\nTo'g'ri: YYYY-MM-DD",
                    parent=win)
                return

            # Qiymat tekshiruv
            if val_str == "":
                conc = None
            else:
                try:
                    conc = float(val_str.replace(",", "."))
                except ValueError:
                    messagebox.showwarning("Xato",
                        f"Noto'g'ri qiymat: '{val_str}'\nFaqat raqam kiriting.",
                        parent=win)
                    return

            db.update_measurement(meas_id, conc, date_str)
            self._load_records()
            self.refresh_month_indicators()
            self.app.set_status(
                f"✅ Yangilandi: {row['sub_name']} | {date_str} | "
                f"{conc if conc is not None else 'aniqlanmagan'}")
            win.destroy()

        ttk.Button(bf, text="💾 Saqlash", style="Success.TButton",
                   command=save).pack(side="left")
        ttk.Button(bf, text="Bekor qilish",
                   command=win.destroy).pack(side="left", padx=8)

        # Enter → saqlash, Escape → yopish
        win.bind("<Return>",  lambda e: save())
        win.bind("<Escape>",  lambda e: win.destroy())

    def _delete_record(self):
        sel = self.tree_rec.selection()
        if not sel:
            messagebox.showwarning("Tanlang","O'chiriladigan qatorni tanlang.",
                                   parent=self.parent)
            return
        if not messagebox.askyesno("O'chirish",
            f"{len(sel)} ta o'lchovni o'chirasizmi?",
            parent=self.parent): return
        for iid in sel:
            db.delete_measurement(int(iid))
        self._load_records()
        self.app.set_status(f"{len(sel)} ta o'lchov o'chirildi.")

    # ── Hisob o'tkazish ──────────────────────
    def _delete_by_year(self):
        pid  = self.app.current_project_id
        sid  = self.app.current_station_id
        year = self._get_year()
        if not pid or not year:
            messagebox.showwarning("Xato", "Loyiha va yilni tanlang.",
                                   parent=self.parent)
            return
        if not messagebox.askyesno(
            "O'chirish",
            f"{year} yil uchun BARCHA o'lchovlarni o'chirasizmi?\n\n"
            f"Bu amal qaytarib bo'lmaydi!",
            icon="warning",
            parent=self.parent
        ):
            return
        count = db.delete_measurements_by_year(pid, year, sid)
        self._load_records()
        self.refresh_month_indicators()
        self.app.set_status(f"O'chirildi: {year} yil — {count} ta o'lchov.")
        messagebox.showinfo("✅ O'chirildi",
            f"{year} yil uchun {count} ta o'lchov o'chirildi.",
            parent=self.parent)

    def _delete_by_month(self):
        pid  = self.app.current_project_id
        sid  = self.app.current_station_id
        year = self._get_year()
        if not pid or not year:
            messagebox.showwarning("Xato", "Loyiha va yilni tanlang.",
                                   parent=self.parent)
            return
        # Joriy oyni aniqlaymiz — sanadan
        date_str = self.ent_date.get().strip()
        try:
            from datetime import datetime
            dt    = datetime.strptime(date_str, "%Y-%m-%d")
            month = dt.month
            from calendar import month_name
            months_uz = ["","Yanvar","Fevral","Mart","Aprel","May","Iyun",
                         "Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"]
            mon_name = months_uz[month]
        except Exception:
            messagebox.showwarning("Xato",
                "Sana kiritilmagan yoki noto'g'ri.\n"
                "Avval sana maydoniga oy sanasini kiriting.",
                parent=self.parent)
            return

        if not messagebox.askyesno(
            "O'chirish",
            f"{year} yil {mon_name} oyi uchun barcha o'lchovlarni\n"
            f"o'chirasizmi?\n\nBu amal qaytarib bo'lmaydi!",
            icon="warning",
            parent=self.parent
        ):
            return
        count = db.delete_measurements_by_month(pid, year, month, sid)
        self._load_records()
        self.refresh_month_indicators()
        self.app.set_status(
            f"O'chirildi: {year}/{month:02d} — {count} ta o'lchov.")
        messagebox.showinfo("✅ O'chirildi",
            f"{year} yil {mon_name} uchun {count} ta o'lchov o'chirildi.",
            parent=self.parent)

    def _run_calculation(self):
        pid  = self.app.current_project_id
        year = self._get_year()
        if not pid or not year:
            messagebox.showwarning("Xato", "Loyiha va yilni tanlang.",
                                   parent=self.parent)
            return

        # Formada kiritilgan qiymatlar borligini tekshirib, avto-saqlash
        # (bu GUI operatsiyasi — asosiy threadda qoladi)
        has_input = any(
            ent.get().strip() != ""
            for ent in self.sub_entries.values()
        )
        if has_input:
            saved = self._save_manual(silent=True)
            if not saved:
                return
            self._clear_entries()

        # Yil validatsiyasi — messagebox talab qiladi, asosiy threadda
        available_years = db.get_available_years(pid)
        if year not in available_years:
            if available_years:
                year = available_years[-1]
                self.cmb_year.set(str(year))
                self.app._current_year = year
                messagebox.showinfo("Yil o'zgartirildi",
                    f"Ma'lumotlar {year} yil uchun topildi.\n"
                    f"Yil avtomatik o'zgartirildi.",
                    parent=self.parent)
            else:
                messagebox.showwarning("Ma'lumot",
                    "Hech qanday o'lchov topilmadi.\n\n"
                    "Avval ma'lumot kiriting, keyin hisob o'tkazing.",
                    parent=self.parent)
                return

        # ── Tugmani bloklash + status ─────────
        self._btn_calc.config(state="disabled")
        self.app.set_status("⏳ Hisob o'tkazilmoqda...")

        # ── Og'ir ish — fon threadida ─────────
        def worker():
            try:
                measurements = db.get_measurements(pid, year)
                if not measurements:
                    self.app.root.after(0, lambda: self._on_calc_error(
                        f"{year} yil uchun o'lchovlar topilmadi.\n"
                        f"Mavjud yillar: {available_years}\n"
                        f"Yil comboboxida to'g'ri yilni tanlang."))
                    return

                # Substansiyalar bo'yicha guruhlaymiz
                all_subs = {s["id"]: s for s in db.get_all_substances()}
                groups: dict[int, list] = {}
                for m in measurements:
                    s_id = m["substance_id"]
                    conc = m["concentration"]
                    groups.setdefault(s_id, []).append(conc)

                substances_data = []
                for s_id, concs in groups.items():
                    s = all_subs.get(s_id)
                    if not s:
                        continue
                    substances_data.append({
                        "name":           s["name"],
                        "mpc":            s["mpc"],
                        "concentrations": concs,
                        "is_oxygen":      bool(s["is_oxygen"]),
                    })

                # Asosiy hisob (og'ir qism)
                result = calc.calculate_all(substances_data)

                # Bazaga saqlash
                for sr in result.substance_results:
                    sub = next(
                        (s for s in all_subs.values() if s["name"] == sr.name),
                        None)
                    if sub:
                        db.save_substance_result(
                            pid, year, sub["id"],
                            sr.ni, sr.ni_exceed, sr.alpha,
                            sr.beta_avg, sr.s_alpha, sr.s_beta, sr.s_ij)

                db.save_final_result(
                    pid, year,
                    result.ki, result.ski, result.f_count,
                    result.k_reserve, result.water_class, result.class_label)

                # GUI yangilash — asosiy threadga qaytamiz
                self.app.root.after(
                    0, lambda r=result, y=year: self._on_calc_done(r, y))

            except Exception as exc:
                self.app.root.after(
                    0, lambda e=str(exc): self._on_calc_error(e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_calc_done(self, result, year):
        """Hisob muvaffaqiyatli tugaganda asosiy threadda chaqiriladi."""
        self._btn_calc.config(state="normal")
        self.app.set_status(
            f"✅ Hisob tugadi: {year} yil | "
            f"Sinf: {result.water_class} — {result.class_label} | "
            f"SKI: {result.ski:.3f}")

        messagebox.showinfo("✅ Hisob natijalari",
            f"Yil: {year}\n\n"
            f"Kombinatör indeks (KI):    {result.ki:.2f}\n"
            f"Solishtirma ind. (SKI):    {result.ski:.4f}\n"
            f"Kritik ko'rsatkichlar (F): {result.f_count}\n"
            f"Zaxira koeffitsienti (k):  {result.k_reserve:.2f}\n\n"
            f"🏷  Suv sifati sinfi: {result.water_class} — {result.class_label}\n\n"
            f"Natijalar → 'Natijalar' tabini ko'ring.",
            parent=self.parent)

        if hasattr(self.app, "tab_results"):
            self.app.tab_results.on_project_changed()
        self.app.notebook.select(2)

    def _on_calc_error(self, message):
        """Hisob xato bo'lganda asosiy threadda chaqiriladi."""
        self._btn_calc.config(state="normal")
        self.app.set_status("❌ Hisob xatosi")
        messagebox.showwarning("Ma'lumot", message, parent=self.parent)

    # ── Excel import/export ───────────────────
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
            "Excel da to'ldiring va 'Excel import' tugmasi orqali yuklang.",
            parent=self.parent)

    def import_excel(self):
        path = filedialog.askopenfilename(
            title="Excel faylni tanlang",
            filetypes=[("Excel fayli","*.xlsx *.xls")],
            parent=self.parent)
        if not path: return

        pid = self.app.current_project_id
        sid = self.app.current_station_id

        from excel_io import import_from_excel, ImportError as ImpErr
        try:
            res = import_from_excel(path, pid, sid)
        except ImpErr as e:
            messagebox.showerror("Import xatosi", str(e), parent=self.parent)
            return

        # Loyiha avtomatik yaratilgan bo'lishi mumkin — yangilaymiz
        self.app.tab_projects.refresh_projects()
        if res.get("project_id"):
            from database import get_project
            p = get_project(res["project_id"])
            if p:
                self.app.set_current_project(p["id"], p["name"])

        msg = (f"✅ Import muvaffaqiyatli!\n\n"
               f"Loyiha:          {res.get('project_name', '—')}\n"
               f"Punkt:           {res.get('station_name', '—')}\n"
               f"Import qilindi:  {res['imported']} ta o'lchov\n"
               f"O'tkazildi:      {res['skipped']} ta\n")
        mpc_upd = res.get("mpc_updated", [])
        if mpc_upd:
            msg += f"\n📊 MPC yangilandi ({len(mpc_upd)} ta modda):\n"
            msg += "\n".join(mpc_upd[:8])
            if len(mpc_upd) > 8:
                msg += f"\n... va yana {len(mpc_upd)-8} ta"
        if res["errors"]:
            msg += f"\n\n⚠️ Xatolar ({len(res['errors'])} ta):\n"
            msg += "\n".join(res["errors"][:5])

        self.on_project_changed()
        self._load_records()
        self.refresh_month_indicators()
        self.app.set_status(f"Import: {res['imported']} ta o'lchov yuklandi.")
        messagebox.showinfo("Import natijasi", msg, parent=self.parent)

    # ── Yordamchi ────────────────────────────

    def _build_month_indicators(self):
        """12 ta oy uchun ko'rsatkichlar."""
        self.month_labels = {}
        months = ["Yan","Fev","Mar","Apr","May","Iyun",
                  "Iyul","Avg","Sen","Okt","Noy","Dek"]
        for i, mon in enumerate(months):
            col_frame = tk.Frame(self.month_frame, bg=COLORS["bg"])
            col_frame.pack(side="left", expand=True, fill="x", padx=2)

            # Oy nomi
            tk.Label(col_frame, text=mon,
                     font=("Segoe UI",8,"bold"),
                     bg=COLORS["bg"], fg=COLORS["text_light"]
                     ).pack()

            # Holat doirasi
            lbl = tk.Label(col_frame, text="○",
                           font=("Segoe UI",14),
                           bg=COLORS["bg"],
                           fg=COLORS["border"])
            lbl.pack()

            # Namuna soni
            cnt_lbl = tk.Label(col_frame, text="",
                               font=("Segoe UI",7),
                               bg=COLORS["bg"],
                               fg=COLORS["text_light"])
            cnt_lbl.pack()

            self.month_labels[i+1] = (lbl, cnt_lbl)

    def refresh_month_indicators(self):
        """DB dan oylik ma'lumotlarni o'qib, indikatorlarni yangilaydi."""
        pid  = self.app.current_project_id
        sid  = self.app.current_station_id
        year = self._get_year()
        if not pid or not year:
            for lbl, cnt in self.month_labels.values():
                lbl.config(text="○", fg=COLORS["border"])
                cnt.config(text="")
            return

        from database import get_monthly_status
        status = get_monthly_status(pid, year, sid)

        for month in range(1, 13):
            lbl, cnt_lbl = self.month_labels[month]
            count = status.get(month, 0)
            if count == 0:
                # Kiritilmagan
                lbl.config(text="○", fg=COLORS["border"])
                cnt_lbl.config(text="")
            elif count < 5:
                # Kam kiritilgan (qisman)
                lbl.config(text="◑", fg=COLORS["warning"])
                cnt_lbl.config(text=f"{count}ta")
            else:
                # To'liq kiritilgan
                lbl.config(text="●", fg=COLORS["success"])
                cnt_lbl.config(text=f"{count}ta")

    def refresh(self):
        self.on_project_changed()

    def _get_year(self) -> int | None:
        try:
            return int(self.cmb_year.get())
        except Exception:
            return None
