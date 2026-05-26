"""
map_tab.py — Monitoring punktlari xaritasi
tkintermapview ishlatiladi (pip install tkintermapview)
Agar o'rnatilmagan bo'lsa — koordinatalar jadvali ko'rsatiladi.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db
from gui.main_window import COLORS, get_class_color

# tkintermapview optional
try:
    import tkintermapview
    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False


CLASS_LABEL = {1:"Shartli toza",2:"Kam iflos",3:"Ifloslangan",
               4:"Iflos",5:"Ekstremal iflos"}
MARKER_COLOR = {1:"green",2:"#90EE90",3:"yellow",4:"orange",5:"red"}


class MapTab:
    def __init__(self, parent, app):
        self.parent  = parent
        self.app     = app
        self.markers = []
        self._build()

    def _build(self):
        # Toolbar
        tb = ttk.Frame(self.parent)
        tb.pack(fill="x", padx=8, pady=(8,4))

        ttk.Button(tb, text="🔄 Yangilash",
                   command=self.refresh).pack(side="left", padx=4)
        ttk.Button(tb, text="🏠 Markazga qaytish",
                   command=self._center_map).pack(side="left", padx=4)
        ttk.Button(tb, text="💾 HTML xarita eksport",
                   style="Success.TButton",
                   command=self.export_html).pack(side="right", padx=4)

        # Tile source
        ttk.Label(tb, text="Xarita turi:").pack(side="left", padx=(16,4))
        self.cmb_tile = ttk.Combobox(tb, width=18, state="readonly",
            values=["OpenStreetMap","Google Normal","Google Satellite"])
        self.cmb_tile.set("OpenStreetMap")
        self.cmb_tile.pack(side="left")
        self.cmb_tile.bind("<<ComboboxSelected>>", self._change_tile)

        # Asosiy qism
        body = ttk.Frame(self.parent)
        body.pack(fill="both", expand=True, padx=8, pady=(0,8))

        if MAP_AVAILABLE:
            self._build_map_widget(body)
        else:
            self._build_fallback(body)

        # Stansiyalar jadvali (o'ngda)
        right = ttk.LabelFrame(body, text="  📍  Stansiyalar  ")
        right.pack(side="right", fill="y", padx=(4,0))
        right.configure(width=280)

        self._build_station_list(right)

    def _build_map_widget(self, parent):
        self.map_widget = tkintermapview.TkinterMapView(
            parent, width=800, height=500, corner_radius=0)
        self.map_widget.pack(side="left", fill="both", expand=True)
        # O'zbekiston markaziga
        self.map_widget.set_position(41.3, 64.6)
        self.map_widget.set_zoom(6)

    def _build_fallback(self, parent):
        """tkintermapview o'rnatilmagan bo'lsa."""
        frm = tk.Frame(parent, bg=COLORS["bg"])
        frm.pack(side="left", fill="both", expand=True)

        tk.Label(frm,
            text="🗺️  Xarita moduli o'rnatilmagan",
            font=("Segoe UI",14,"bold"),
            bg=COLORS["bg"], fg=COLORS["text"]).pack(pady=(60,8))
        tk.Label(frm,
            text="Xaritani ko'rish uchun terminalda quyidagini ishga tushiring:",
            font=("Segoe UI",10), bg=COLORS["bg"],
            fg=COLORS["text_light"]).pack()

        code = tk.Frame(frm, bg="#2C3E50", padx=16, pady=12)
        code.pack(pady=12)
        tk.Label(code, text="pip install tkintermapview",
                 font=("Courier New",12,"bold"),
                 bg="#2C3E50", fg="#2ECC71").pack()

        tk.Label(frm,
            text="O'rnatgandan keyin dasturni qayta ishga tushiring.",
            font=("Segoe UI",10), bg=COLORS["bg"],
            fg=COLORS["text_light"]).pack()

        tk.Label(frm,
            text="📌  HTML xarita eksport hozir ham ishlaydi (o'ngdagi tugma)",
            font=("Segoe UI",10,"bold"), bg=COLORS["bg"],
            fg=COLORS["accent"]).pack(pady=16)

        self.map_widget = None

    def _build_station_list(self, parent):
        cols = ("name","river","class","ski")
        self.tree_st = ttk.Treeview(parent, columns=cols,
                                    show="headings", height=24)
        self.tree_st.heading("name",  text="Stansiya")
        self.tree_st.heading("river", text="Daryo")
        self.tree_st.heading("class", text="Sinf")
        self.tree_st.heading("ski",   text="SKI")
        self.tree_st.column("name",  width=130)
        self.tree_st.column("river", width=80)
        self.tree_st.column("class", width=45,  anchor="center")
        self.tree_st.column("ski",   width=55,  anchor="center")

        for cls in range(1,6):
            self.tree_st.tag_configure(
                f"cls{cls}", background=get_class_color(cls),
                foreground="#FFFFFF" if cls >= 4 else "#2C3E50")
        self.tree_st.tag_configure("no_data", foreground=COLORS["text_light"])

        sb = ttk.Scrollbar(parent, orient="vertical",
                           command=self.tree_st.yview)
        self.tree_st.configure(yscrollcommand=sb.set)
        self.tree_st.pack(side="left", fill="both",
                          expand=True, padx=(6,0), pady=6)
        sb.pack(side="left", fill="y", pady=6)
        self.tree_st.bind("<<TreeviewSelect>>", self._on_station_click)

    # ── Yangilash ────────────────────────────
    def refresh(self):
        if MAP_AVAILABLE and self.map_widget:
            for m in self.markers:
                m.delete()
            self.markers.clear()

        self.tree_st.delete(*self.tree_st.get_children())

        stations = db.get_all_stations_with_results()
        for s in stations:
            wc  = s["water_class"]
            tag = f"cls{wc}" if wc else "no_data"

            self.tree_st.insert("", "end",
                iid=str(s["id"]),
                values=(s["name"],
                        s["river"] or "—",
                        f"{wc}-sinf" if wc else "—",
                        f"{s['ski']:.2f}" if s["ski"] else "—"),
                tags=(tag,))

            if MAP_AVAILABLE and self.map_widget and s["latitude"]:
                color = MARKER_COLOR.get(wc, "blue")
                label = (f"{s['name']}\n"
                         f"Loyiha: {s['project_name']}\n"
                         f"Sinf: {wc} — {CLASS_LABEL.get(wc,'—')}\n"
                         f"SKI: {s['ski']:.3f}" if s["ski"]
                         else s["name"])
                marker = self.map_widget.set_marker(
                    s["latitude"], s["longitude"],
                    text=s["name"],
                    marker_color_circle=color,
                    marker_color_outside=color,
                    command=lambda m, lbl=label: messagebox.showinfo(
                        "Stansiya", lbl, parent=self.parent))
                self.markers.append(marker)

    def _on_station_click(self, event=None):
        sel = self.tree_st.selection()
        if not sel or not MAP_AVAILABLE or not self.map_widget:
            return
        sid = int(sel[0])
        s   = db.get_station(sid)
        if s and s["latitude"] and s["longitude"]:
            self.map_widget.set_position(s["latitude"], s["longitude"])
            self.map_widget.set_zoom(12)

    def _center_map(self):
        if MAP_AVAILABLE and self.map_widget:
            self.map_widget.set_position(41.3, 64.6)
            self.map_widget.set_zoom(6)

    def _change_tile(self, event=None):
        if not MAP_AVAILABLE or not self.map_widget:
            return
        tile = self.cmb_tile.get()
        if tile == "OpenStreetMap":
            self.map_widget.set_tile_server(
                "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
        elif tile == "Google Normal":
            self.map_widget.set_tile_server(
                "https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga",
                max_zoom=22)
        elif tile == "Google Satellite":
            self.map_widget.set_tile_server(
                "https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga",
                max_zoom=22)

    # ── HTML eksport ──────────────────────────
    def export_html(self):
        try:
            import folium
        except ImportError:
            messagebox.showerror("Modul yo'q",
                "HTML xarita uchun folium kerak:\n\npip install folium",
                parent=self.parent)
            return

        stations = db.get_all_stations_with_results()
        has_coords = [s for s in stations if s["latitude"]]
        if not has_coords:
            messagebox.showwarning("Ma'lumot",
                "Koordinatalari kiritilgan stansiyalar topilmadi.",
                parent=self.parent)
            return

        path = filedialog.asksaveasfilename(
            title="HTML xaritani saqlash",
            defaultextension=".html",
            filetypes=[("HTML fayli","*.html")],
            initialfile="suv_monitoringi_xarita.html",
            parent=self.parent)
        if not path: return

        # Markazni hisoblash
        lats = [s["latitude"]  for s in has_coords]
        lons = [s["longitude"] for s in has_coords]
        center = [sum(lats)/len(lats), sum(lons)/len(lons)]

        m = folium.Map(location=center, zoom_start=7,
                       tiles="OpenStreetMap")

        # Ranglar
        color_map = {1:"green",2:"lightgreen",3:"orange",4:"red",5:"darkred",None:"gray"}

        for s in has_coords:
            wc     = s["water_class"]
            color  = color_map.get(wc, "gray")
            popup  = folium.Popup(
                f"""<b>{s['name']}</b><br>
                Loyiha: {s['project_name']}<br>
                Daryo: {s['river'] or '—'}<br>
                Sinf: <b>{wc} — {CLASS_LABEL.get(wc,'Ma\'lumot yo\'q')}</b><br>
                SKI: {f"{s['ski']:.3f}" if s['ski'] else '—'}<br>
                Yil: {s['result_year'] or '—'}""",
                max_width=260)
            folium.Marker(
                location=[s["latitude"], s["longitude"]],
                popup=popup,
                tooltip=f"{s['name']} ({wc}-sinf)" if wc else s["name"],
                icon=folium.Icon(color=color, icon="tint",
                                 prefix="fa")
            ).add_to(m)

        # Legenda
        legend = """
        <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                    background:white;padding:12px;border-radius:8px;
                    box-shadow:2px 2px 8px rgba(0,0,0,0.3);
                    font-family:Arial;font-size:13px;">
          <b>Suv sifati sinflari</b><br>
          <span style="color:green">●</span> 1 — Shartli toza<br>
          <span style="color:#90EE90">●</span> 2 — Kam ifloslangan<br>
          <span style="color:orange">●</span> 3 — Ifloslangan<br>
          <span style="color:red">●</span> 4 — Iflos<br>
          <span style="color:darkred">●</span> 5 — Ekstremal iflos<br>
          <span style="color:gray">●</span> Ma'lumot yo'q
        </div>"""
        m.get_root().html.add_child(folium.Element(legend))

        m.save(path)
        self.app.set_status(f"HTML xarita saqlandi: {path}")
        messagebox.showinfo("✅ Tayyor",
            f"HTML xarita saqlandi:\n{path}\n\n"
            "Brauzerda ochish uchun faylni ikki marta bosing.",
            parent=self.parent)
