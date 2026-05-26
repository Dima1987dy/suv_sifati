"""
project_tab.py — Loyihalar va monitoring stansiyalari boshqaruvi
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db
from gui.main_window import COLORS


class ProjectTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app    = app
        self._build()
        self.refresh_projects()

    def _build(self):
        # Sol panel — loyihalar
        left = ttk.LabelFrame(self.parent, text="  📋  Loyihalar  ")
        left.pack(side="left", fill="both", expand=True, padx=(8,4), pady=8)

        tb = ttk.Frame(left)
        tb.pack(fill="x", padx=6, pady=(6,2))
        ttk.Button(tb, text="➕ Yangi",    command=self.open_add_dialog).pack(side="left", padx=2)
        ttk.Button(tb, text="✏️ Tahrirlash",   command=self.open_edit_dialog).pack(side="left", padx=2)
        ttk.Button(tb, text="🗑 O'chirish",   style="Danger.TButton",
                   command=self.delete_project).pack(side="left", padx=2)

        cols = ("id","name","description","created_at")
        self.tree_proj = ttk.Treeview(left, columns=cols, show="headings", height=16)
        self.tree_proj.heading("id",          text="#")
        self.tree_proj.heading("name",        text="Loyiha nomi")
        self.tree_proj.heading("description", text="Tavsif")
        self.tree_proj.heading("created_at",  text="Yaratilgan")
        self.tree_proj.column("id",          width=40,  anchor="center")
        self.tree_proj.column("name",        width=200)
        self.tree_proj.column("description", width=220)
        self.tree_proj.column("created_at",  width=90,  anchor="center")

        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree_proj.yview)
        self.tree_proj.configure(yscrollcommand=sb.set)
        self.tree_proj.pack(side="left", fill="both", expand=True, padx=(6,0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tree_proj.bind("<<TreeviewSelect>>", self._on_project_select)
        self.tree_proj.bind("<Double-1>", lambda e: self.open_edit_dialog())

        # O'ng panel — stansiyalar
        right = ttk.LabelFrame(self.parent, text="  📍  Monitoring punktlari  ")
        right.pack(side="left", fill="both", expand=True, padx=(4,8), pady=8)

        tb2 = ttk.Frame(right)
        tb2.pack(fill="x", padx=6, pady=(6,2))
        ttk.Button(tb2, text="➕ Stansiya",  command=self.open_add_station).pack(side="left", padx=2)
        ttk.Button(tb2, text="✏️ Tahrirlash",    command=self.open_edit_station).pack(side="left", padx=2)
        ttk.Button(tb2, text="🗑 O'chirish",    style="Danger.TButton",
                   command=self.delete_station).pack(side="left", padx=2)

        cols2 = ("id","name","river","region","lat","lon")
        self.tree_stat = ttk.Treeview(right, columns=cols2, show="headings", height=16)
        self.tree_stat.heading("id",     text="#")
        self.tree_stat.heading("name",   text="Punkt nomi")
        self.tree_stat.heading("river",  text="Daryo")
        self.tree_stat.heading("region", text="Viloyat")
        self.tree_stat.heading("lat",    text="Kenglik")
        self.tree_stat.heading("lon",    text="Uzunlik")
        self.tree_stat.column("id",     width=40,  anchor="center")
        self.tree_stat.column("name",   width=160)
        self.tree_stat.column("river",  width=110)
        self.tree_stat.column("region", width=110)
        self.tree_stat.column("lat",    width=80,  anchor="center")
        self.tree_stat.column("lon",    width=80,  anchor="center")

        sb2 = ttk.Scrollbar(right, orient="vertical", command=self.tree_stat.yview)
        self.tree_stat.configure(yscrollcommand=sb2.set)
        self.tree_stat.pack(side="left", fill="both", expand=True, padx=(6,0), pady=6)
        sb2.pack(side="left", fill="y", pady=6)
        self.tree_stat.bind("<<TreeviewSelect>>", self._on_station_select)

    def refresh_projects(self):
        self.tree_proj.delete(*self.tree_proj.get_children())
        for p in db.get_all_projects():
            self.tree_proj.insert("", "end", iid=str(p["id"]),
                values=(p["id"], p["name"], p["description"] or "—", p["created_at"]))

    def refresh_stations(self, project_id):
        self.tree_stat.delete(*self.tree_stat.get_children())
        for s in db.get_stations(project_id):
            self.tree_stat.insert("", "end", iid=str(s["id"]),
                values=(s["id"], s["name"], s["river"] or "—", s["region"] or "—",
                        f"{s['latitude']:.4f}" if s["latitude"] else "—",
                        f"{s['longitude']:.4f}" if s["longitude"] else "—"))

    def _on_project_select(self, event=None):
        sel = self.tree_proj.selection()
        if not sel: return
        pid  = int(sel[0])
        name = self.tree_proj.item(sel[0])["values"][1]
        self.app.set_current_project(pid, name)
        self.refresh_stations(pid)

    def _on_station_select(self, event=None):
        sel = self.tree_stat.selection()
        if not sel: return
        sid  = int(sel[0])
        name = self.tree_stat.item(sel[0])["values"][1]
        self.app.set_current_station(sid, name)

    def open_add_dialog(self):
        _ProjectDialog(self.parent, self.app, self, project=None)

    def open_edit_dialog(self):
        sel = self.tree_proj.selection()
        if not sel:
            messagebox.showwarning("Tanlang", "Avval loyiha tanlang.", parent=self.parent)
            return
        _ProjectDialog(self.parent, self.app, self, project=db.get_project(int(sel[0])))

    def delete_project(self):
        sel = self.tree_proj.selection()
        if not sel: return
        pid  = int(sel[0])
        name = self.tree_proj.item(sel[0])["values"][1]
        if not messagebox.askyesno("O'chirish",
            f"'{name}' loyihasini o'chirasizmi?\nBarcha ma'lumotlar ham o'chadi!",
            parent=self.parent): return
        db.delete_project(pid)
        self.refresh_projects()
        self.tree_stat.delete(*self.tree_stat.get_children())
        self.app.set_current_project(None)

    def open_add_station(self):
        if not self.app.current_project_id:
            messagebox.showwarning("Loyiha", "Avval loyiha tanlang.", parent=self.parent)
            return
        _StationDialog(self.parent, self.app, self, station=None)

    def open_edit_station(self):
        sel = self.tree_stat.selection()
        if not sel:
            messagebox.showwarning("Tanlang", "Avval punkt tanlang.", parent=self.parent)
            return
        _StationDialog(self.parent, self.app, self, station=db.get_station(int(sel[0])))

    def delete_station(self):
        sel = self.tree_stat.selection()
        if not sel: return
        sid  = int(sel[0])
        name = self.tree_stat.item(sel[0])["values"][1]
        if not messagebox.askyesno("O'chirish", f"'{name}' punktni o'chirasizmi?",
                                   parent=self.parent): return
        db.delete_station(sid)
        if self.app.current_project_id:
            self.refresh_stations(self.app.current_project_id)


# ── Loyiha dialog ────────────────────────────
class _ProjectDialog(tk.Toplevel):
    def __init__(self, parent, app, tab, project=None):
        super().__init__(parent)
        self.app = app; self.tab = tab; self.project = project
        self.title("Yangi loyiha" if project is None else "Loyihani tahrirlash")
        self.geometry("420x230"); self.resizable(False, False)
        self.configure(bg=COLORS["bg"]); self.grab_set()
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Loyiha nomi *",
                  font=("Segoe UI",10,"bold")).grid(row=0,column=0,sticky="w",pady=(0,4))
        self.ent_name = ttk.Entry(frm, width=44)
        self.ent_name.grid(row=1,column=0,sticky="ew",pady=(0,10))
        ttk.Label(frm, text="Tavsif").grid(row=2,column=0,sticky="w",pady=(0,4))
        self.txt_desc = tk.Text(frm, width=44, height=4,
                                font=("Segoe UI",10), relief="solid", bd=1)
        self.txt_desc.grid(row=3,column=0,sticky="ew",pady=(0,12))
        bf = ttk.Frame(frm); bf.grid(row=4,column=0,sticky="e")
        ttk.Button(bf, text="Bekor", command=self.destroy).pack(side="right",padx=(6,0))
        ttk.Button(bf, text="💾 Saqlash", style="Success.TButton",
                   command=self._save).pack(side="right")
        if project:
            self.ent_name.insert(0, project["name"])
            self.txt_desc.insert("1.0", project["description"] or "")
        self.ent_name.focus()

    def _save(self):
        name = self.ent_name.get().strip()
        desc = self.txt_desc.get("1.0","end").strip()
        if not name:
            messagebox.showwarning("Xato","Loyiha nomi bo'sh bo'lmasin.",parent=self); return
        if self.project is None:
            pid = db.add_project(name, desc)
            self.app.set_current_project(pid, name)
        else:
            db.update_project(self.project["id"], name, desc)
        self.tab.refresh_projects()
        self.app.set_status(f"Loyiha saqlandi: {name}")
        self.destroy()


# ── Stansiya dialog ──────────────────────────
class _StationDialog(tk.Toplevel):
    def __init__(self, parent, app, tab, station=None):
        super().__init__(parent)
        self.app = app; self.tab = tab; self.station = station
        self.title("Yangi punkt" if station is None else "Punktni tahrirlash")
        self.geometry("440x330"); self.resizable(False, False)
        self.configure(bg=COLORS["bg"]); self.grab_set()
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        fields = [("Punkt nomi *","ent_name"),("Daryo nomi","ent_river"),
                  ("Viloyat/tuman","ent_region"),("Tavsif","ent_desc")]
        for i,(lbl,attr) in enumerate(fields):
            ttk.Label(frm, text=lbl,
                      font=("Segoe UI",10,"bold") if i==0 else ("Segoe UI",10)
                      ).grid(row=i,column=0,sticky="w",padx=(0,8),pady=3)
            ent = ttk.Entry(frm, width=36)
            ent.grid(row=i,column=1,sticky="ew",pady=3)
            setattr(self,attr,ent)

        ttk.Separator(frm,orient="horizontal").grid(row=4,column=0,columnspan=2,
                                                    sticky="ew",pady=8)
        ttk.Label(frm,text="📍 Koordinatalar (ixtiyoriy)",
                  font=("Segoe UI",10,"bold")).grid(row=5,column=0,columnspan=2,sticky="w")
        cf = ttk.Frame(frm); cf.grid(row=6,column=0,columnspan=2,sticky="ew",pady=4)
        ttk.Label(cf,text="Kenglik (lat):").pack(side="left")
        self.ent_lat = ttk.Entry(cf,width=14); self.ent_lat.pack(side="left",padx=(4,16))
        ttk.Label(cf,text="Uzunlik (lon):").pack(side="left")
        self.ent_lon = ttk.Entry(cf,width=14); self.ent_lon.pack(side="left",padx=4)
        ttk.Label(frm,text="Masalan: 40.2214  /  69.2646",
                  font=("Segoe UI",8),foreground=COLORS["text_light"]
                  ).grid(row=7,column=0,columnspan=2,sticky="w")

        bf = ttk.Frame(frm); bf.grid(row=8,column=0,columnspan=2,sticky="e",pady=(12,0))
        ttk.Button(bf,text="Bekor",command=self.destroy).pack(side="right",padx=(6,0))
        ttk.Button(bf,text="💾 Saqlash",style="Success.TButton",
                   command=self._save).pack(side="right")

        if station:
            self.ent_name.insert(0,   station["name"])
            self.ent_river.insert(0,  station["river"]  or "")
            self.ent_region.insert(0, station["region"] or "")
            self.ent_desc.insert(0,   station["description"] or "")
            if station["latitude"]:  self.ent_lat.insert(0, str(station["latitude"]))
            if station["longitude"]: self.ent_lon.insert(0, str(station["longitude"]))
        self.ent_name.focus()

    def _save(self):
        name = self.ent_name.get().strip()
        if not name:
            messagebox.showwarning("Xato","Punkt nomi bo'sh bo'lmasin.",parent=self); return
        try:
            lat = float(self.ent_lat.get()) if self.ent_lat.get().strip() else None
            lon = float(self.ent_lon.get()) if self.ent_lon.get().strip() else None
        except ValueError:
            messagebox.showwarning("Xato","Koordinatalar raqam bo'lishi kerak.",parent=self)
            return
        pid = self.app.current_project_id
        if self.station is None:
            db.add_station(pid, name, lat, lon,
                           self.ent_river.get().strip(),
                           self.ent_region.get().strip(),
                           self.ent_desc.get().strip())
        else:
            db.update_station(self.station["id"], name, lat, lon,
                              self.ent_river.get().strip(),
                              self.ent_region.get().strip(),
                              self.ent_desc.get().strip())
        self.tab.refresh_stations(pid)
        self.app.set_status(f"Punkt saqlandi: {name}")
        # input_tab stansiya comboboxini yangilash
        if hasattr(self.app, "tab_input"):
            self.app.tab_input.on_project_changed()
        self.destroy()
