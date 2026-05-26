"""
seed_demo.py — Demo ma'lumotlar bilan bazani to'ldirish.
Ishga tushirish:  python seed_demo.py
"""
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import database as db
import calculations as calc

random.seed(42)


# ─────────────────────────────────────
#  Yordamchi: tasodifiy konsentratsiya
# ─────────────────────────────────────
def rnd(base, spread=0.4):
    """base atrofida ±spread nisbatida tasodifiy qiymat."""
    return round(base * (1 + random.uniform(-spread, spread)), 4)


def gen_conc(mpc, factor, is_oxygen=False):
    """
    factor > 1  → ifloslangan (MPC dan yuqori)
    factor < 1  → toza
    Kislorod uchun teskari: factor < 1 → MPC dan past → iflos
    """
    base = mpc * factor
    return max(0.0001, rnd(base))


# ─────────────────────────────────────
#  Asosiy sozlamalar
# ─────────────────────────────────────
MONTHS = list(range(1, 13))          # yanvardan dekabrgacha

PROJECTS = [
    {
        "name": "Sirdaryo daryosi — 2024 yil monitoring",
        "description": "Sirdaryo havzasi bo'ylab suv sifatini kuzatish",
        "stations": [
            {"name": "Sirdaryo — Bekobod kresimi",
             "river": "Sirdaryo", "region": "Toshkent viloyati",
             "lat": 40.2214, "lon": 69.2646,
             "pollution": 2.5},     # o'rtacha ifloslanish
            {"name": "Sirdaryo — Boyovut kresimi",
             "river": "Sirdaryo", "region": "Sirdaryo viloyati",
             "lat": 40.5714, "lon": 68.0082,
             "pollution": 4.0},     # kuchli ifloslanish
            {"name": "Sirdaryo — Chinoz kresimi",
             "river": "Sirdaryo", "region": "Toshkent viloyati",
             "lat": 40.9376, "lon": 68.7729,
             "pollution": 1.5},     # nisbatan toza
        ]
    },
    {
        "name": "Chirchiq daryosi — 2024 yil monitoring",
        "description": "Chirchiq daryosi sanoat zonasi monitoringi",
        "stations": [
            {"name": "Chirchiq — Yuqori kesim",
             "river": "Chirchiq", "region": "Toshkent viloyati",
             "lat": 41.4686, "lon": 69.5826,
             "pollution": 1.2},
            {"name": "Chirchiq — Quyi kesim (Toshkent)",
             "river": "Chirchiq", "region": "Toshkent shahri",
             "lat": 41.2995, "lon": 69.2401,
             "pollution": 5.5},     # juda iflos
        ]
    },
]

# Moddalar va ifloslanish omillari (har stansiya uchun ko'paytiriladi)
# (modda_nomi, nisbiy_factor)
SUBSTANCE_FACTORS = {
    "O2 (Kislorod)":        0.55,   # past bo'lishi kerak (iflos)
    "KBT5":                 1.8,
    "KKT":                  1.4,
    "Fenol":                3.5,
    "Neft mahsulotlari":    2.8,
    "N-NO2-":               4.2,
    "N-NO3-":               1.3,
    "N-NH4+":               2.1,
    "Temir umumiy (Feум)":  3.0,
    "Mis (Cu)":             2.4,
    "Rux (Zn)":             1.9,
    "Xrom (Cr)":            1.2,
    "Kadmiy (Cd)":          0.8,
    "Qo'rg'oshin (Pb)":   1.6,
    "Xloridlar (Cl-)":      0.9,
    "Sulfatlar (SO42-)":    1.1,
    "SSFM":                 2.2,
    "Mineralizatsiya":      0.7,
    "Ca2+":                 0.85,
    "Mg2+":                 1.0,
    "Na+":                  0.95,
    "Nikel (Ni)":           1.7,
}


def fill_project(proj_data):
    pid = db.add_project(proj_data["name"], proj_data["description"])
    print(f"\n📁 Loyiha: {proj_data['name']}  (id={pid})")

    all_subs = {s["name"]: s for s in db.get_all_substances()}

    for st_data in proj_data["stations"]:
        sid = db.add_station(
            pid,
            st_data["name"],
            latitude=st_data["lat"],
            longitude=st_data["lon"],
            river=st_data["river"],
            region=st_data["region"],
        )
        poll = st_data["pollution"]
        print(f"  📍 Stansiya: {st_data['name']}  (ifloslanish x{poll})")

        rows = []
        for month in MONTHS:
            day = random.randint(10, 20)
            date_str = f"2024-{month:02d}-{day:02d}"

            for sub_name, base_factor in SUBSTANCE_FACTORS.items():
                s = all_subs.get(sub_name)
                if not s:
                    continue
                is_ox  = bool(s["is_oxygen"])
                factor = base_factor * poll

                # Kislorod uchun teskari: factor kichik → past qiymat
                if is_ox:
                    conc = gen_conc(s["mpc"], 1.0 / max(factor, 0.3), is_oxygen=True)
                else:
                    conc = gen_conc(s["mpc"], factor)

                # Ba'zi o'lchovlar "aniqlanmagan" (None) — real hayotga yaqin
                if random.random() < 0.05:
                    conc = None

                rows.append((pid, sid, s["id"], date_str, conc))

        db.add_measurements_with_station(rows)
        print(f"     ✅ {len(rows)} ta o'lchov kiritildi (12 oy × {len(SUBSTANCE_FACTORS)} modda)")

        # ── Hisob ────────────────────────────
        measurements = db.get_measurements(pid, 2024)
        all_subs_list = {s["id"]: s for s in db.get_all_substances()}
        groups = {}
        for m in measurements:
            if m["station_id"] == sid:
                groups.setdefault(m["substance_id"], []).append(m["concentration"])

        substances_data = []
        for sub_id, concs in groups.items():
            s = all_subs_list.get(sub_id)
            if s:
                substances_data.append({
                    "name":           s["name"],
                    "mpc":            s["mpc"],
                    "concentrations": concs,
                    "is_oxygen":      bool(s["is_oxygen"]),
                })

        result = calc.calculate_all(substances_data)

        for sr in result.substance_results:
            sub = next((s for s in all_subs_list.values()
                        if s["name"] == sr.name), None)
            if sub:
                db.save_substance_result(
                    pid, 2024, sub["id"],
                    sr.ni, sr.ni_exceed, sr.alpha,
                    sr.beta_avg, sr.s_alpha, sr.s_beta, sr.s_ij)

        db.save_final_result(
            pid, 2024,
            result.ki, result.ski, result.f_count,
            result.k_reserve, result.water_class, result.class_label)

        sinf_emoji = {1:"🟢",2:"🟩",3:"🟡",4:"🟠",5:"🔴"}.get(result.water_class,"⚪")
        print(f"     {sinf_emoji} Sinf: {result.water_class} — {result.class_label} "
              f"| SKI={result.ski:.3f} | KI={result.ki:.2f} | F={result.f_count}")

    return pid


# ─────────────────────────────────────
#  Ishga tushirish
# ─────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  DEMO MA'LUMOTLAR YUKLANMOQDA...")
    print("=" * 55)

    db.init_db()
    db.seed_default_substances()

    for proj in PROJECTS:
        fill_project(proj)

    print("\n" + "=" * 55)
    print("  ✅ DEMO MA'LUMOTLAR MUVAFFAQIYATLI YUKLANDI!")
    print(f"  DB: {db.DB_PATH}")
    print("  Dasturni ishga tushiring:  python main.py")
    print("=" * 55)
