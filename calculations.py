"""
calculations.py
Qo'llanma formulalari:
  - E-ilova  : takroriylik → S_alpha ball
  - J-ilova  : oshish karraligi → S_beta ball
  - S_ij     : umumlashtirilgan ball
  - KI / SKI : kombinatör / solishtirma kombinatör indeks
  - k        : zaxira koeffitsienti
  - Sinf     : K-ilova bo'yicha suv sifati sinfi
"""

from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════
#  E-ILOVA: takroriylik → S_alpha
#  [1,10)→[1,2)  |  [10,30)→[2,3)  |  [30,50)→[3,4)  |  [50,100]→4
# ═══════════════════════════════════════════════════════
def get_s_alpha(alpha: float) -> float:
    """
    alpha — takroriylik foizda (0..100).
    Qaytaradi: S_alpha ball (chiziqli interpolatsiya bilan).
    """
    if alpha < 1.0:
        return 0.0
    elif alpha < 10.0:
        # [1,10) → [1,2) : 1% = 0.11 birlik
        return 1.0 + (alpha - 1.0) * 0.11
    elif alpha < 30.0:
        # [10,30) → [2,3) : 1% = 0.05 birlik
        return 2.0 + (alpha - 10.0) * 0.05
    elif alpha < 50.0:
        # [30,50) → [3,4) : 1% = 0.05 birlik
        return 3.0 + (alpha - 30.0) * 0.05
    else:
        # [50,100] → 4 (to'liq)
        return 4.0


# ═══════════════════════════════════════════════════════
#  J-ILOVA: oshish karraligi → S_beta
#  (1,2)→[1,2)  |  [2,10)→[2,3)  |  [10,50)→[3,4)  |  [50,∞)→4
#  Kislorod uchun maxsus gradatsiya:
#  (1,1.5]→[1,2) | (1.5,2]→[2,3) | (2,3]→[3,4) | (3,∞)→4
# ═══════════════════════════════════════════════════════
def get_s_beta(beta: float, is_oxygen: bool = False) -> float:
    """
    beta     — o'rtacha oshish karraligi (MPC dan necha marta oshgan).
    is_oxygen — True bo'lsa kislorod uchun maxsus gradatsiya ishlatiladi.
    Qaytaradi: S_beta ball.
    """
    if beta <= 1.0:
        return 0.0

    if is_oxygen:
        # Kislorod: teskari — MPC / C, shuning uchun beta = MPC / C_avg
        if beta <= 1.5:
            return 1.0 + (beta - 1.0) / 0.5         # [1,1.5] → [1,2)
        elif beta <= 2.0:
            return 2.0 + (beta - 1.5) / 0.5         # (1.5,2] → [2,3)
        elif beta <= 3.0:
            return 3.0 + (beta - 2.0) / 1.0         # (2,3]   → [3,4)
        else:
            return 4.0
    else:
        if beta < 2.0:
            # (1,2) → [1,2) : 1 birlik = 1.0 ball
            return 1.0 + (beta - 1.0) * 1.0
        elif beta < 10.0:
            # [2,10) → [2,3) : 1 birlik = 0.125 ball
            return 2.0 + (beta - 2.0) * 0.125
        elif beta < 50.0:
            # [10,50) → [3,4) : 1 birlik = 0.025 ball
            return 3.0 + (beta - 10.0) * 0.025
        else:
            return 4.0


# ═══════════════════════════════════════════════════════
#  Bitta modda uchun hisob
# ═══════════════════════════════════════════════════════
@dataclass
class SubstanceResult:
    name: str
    mpc: float
    ni: int               # o'lchovlar soni
    ni_exceed: int        # MPC oshgan soni
    alpha: float          # takroriylik, %
    beta_avg: float       # o'rtacha oshish karraligi
    s_alpha: float        # E-ilova ball
    s_beta: float         # J-ilova ball
    s_ij: float           # umumlashtirilgan ball = s_alpha * s_beta
    is_critical: bool     # s_ij >= 9


def calc_substance(name: str,
                   mpc: float,
                   concentrations: list[float | None],
                   is_oxygen: bool = False) -> SubstanceResult | None:
    """
    name           — modda nomi
    mpc            — ruxsat etilgan chegara
    concentrations — o'lchov natijalari (None = aniqlanmagan)
    is_oxygen      — kislorod uchun teskari hisob

    Qaytaradi: SubstanceResult yoki None (ma'lumot yetarli emas).
    """
    # None qiymatlarni olib tashlaymiz
    values = [c for c in concentrations if c is not None]
    ni = len(values)
    if ni == 0:
        return None

    if is_oxygen:
        # Kislorod: MPC dan PAST bo'lsa oshish hisoblanadi
        exceeds = [v for v in values if v < mpc]
        ni_exceed = len(exceeds)
        alpha = (ni_exceed / ni) * 100.0

        if ni_exceed == 0:
            return SubstanceResult(
                name=name, mpc=mpc, ni=ni, ni_exceed=0,
                alpha=0.0, beta_avg=0.0,
                s_alpha=0.0, s_beta=0.0, s_ij=0.0, is_critical=False
            )

        # Kislorod uchun beta = MPC / C (teskari nisbat)
        # Agar C = 0 bo'lsa shartli 0.01 qabul qilinadi (qo'llanma J-ilova)
        betas = [mpc / (v if v > 0 else 0.01) for v in exceeds]
        beta_avg = sum(betas) / len(betas)

    else:
        # Oddiy moddalar: MPC dan YUQORI bo'lsa oshish
        exceeds = [v for v in values if v > mpc]
        ni_exceed = len(exceeds)
        alpha = (ni_exceed / ni) * 100.0

        if ni_exceed == 0:
            return SubstanceResult(
                name=name, mpc=mpc, ni=ni, ni_exceed=0,
                alpha=0.0, beta_avg=0.0,
                s_alpha=0.0, s_beta=0.0, s_ij=0.0, is_critical=False
            )

        betas = [v / mpc for v in exceeds]
        beta_avg = sum(betas) / len(betas)

    s_alpha = get_s_alpha(alpha)
    s_beta  = get_s_beta(beta_avg, is_oxygen=is_oxygen)
    s_ij    = round(s_alpha * s_beta, 4)

    return SubstanceResult(
        name=name, mpc=mpc, ni=ni, ni_exceed=ni_exceed,
        alpha=round(alpha, 2),
        beta_avg=round(beta_avg, 4),
        s_alpha=round(s_alpha, 4),
        s_beta=round(s_beta, 4),
        s_ij=s_ij,
        is_critical=(s_ij >= 9.0)
    )


# ═══════════════════════════════════════════════════════
#  Komplekslik koeffitsienti (K%)  — formula (1)(2)
# ═══════════════════════════════════════════════════════
def calc_complexity_coeff(results: list[SubstanceResult]) -> float:
    """
    K = (N' / N) * 100%
    N  — baholangan moddalar soni
    N' — MPC oshgan moddalar soni
    """
    n_total   = len(results)
    n_exceed  = sum(1 for r in results if r.ni_exceed > 0)
    if n_total == 0:
        return 0.0
    return round((n_exceed / n_total) * 100.0, 2)


# ═══════════════════════════════════════════════════════
#  KI va SKI  — formula (9)(10)
# ═══════════════════════════════════════════════════════
def calc_ki(results: list[SubstanceResult]) -> float:
    """Sj = Σ Sij — kombinatör indeks."""
    return round(sum(r.s_ij for r in results), 4)


def calc_ski(ki: float, nj: int) -> float:
    """S'j = Sj / Nj — solishtirma kombinatör indeks."""
    if nj == 0:
        return 0.0
    return round(ki / nj, 4)


# ═══════════════════════════════════════════════════════
#  Zaxira koeffitsienti  — formula (11)
# ═══════════════════════════════════════════════════════
def calc_reserve_coeff(f: int) -> float:
    """
    k = 1 - 0.1 * F
    F — kritik ko'rsatkichlar soni (Sij >= 9).
    Agar F >= 6: k <= 0.4, sinf to'g'ridan-to'g'ri 5 ga o'tadi.
    k hech qachon manfiy bo'lmaydi (min = 0.0).
    """
    return round(max(0.0, 1.0 - 0.1 * f), 4)


# ═══════════════════════════════════════════════════════
#  Suv sifati sinfi  — K-ilova (SKI + k bo'yicha)
# ═══════════════════════════════════════════════════════
# Sinf + daraja → tavsif
CLASS_LABELS = {
    1:    "Shartli toza",
    2:    "Kam ifloslangan",
    "3a": "Ifloslangan (3a)",
    "3b": "Juda ifloslangan (3b)",
    4:    "Iflos",        # umumiy (backup)
    "4a": "Iflos (4a)",
    "4b": "Iflos (4b)",
    "4v": "Juda iflos (4v)",
    "4g": "Juda iflos (4g)",
    5:    "Ekstremal darajada ifloslangan",
}

# Sinf raqami (int) — faqat asosiy sinf uchun
CLASS_NUMBER = {
    1: 1, 2: 2,
    "3a": 3, "3b": 3,
    "4a": 4, "4b": 4, "4v": 4, "4g": 4,
    5: 5,
}


def get_water_class(ski: float, k: float, f: int) -> tuple[int, str]:
    """
    K-ilova (K-ilova jadvali) asosida sinf + daraja aniqlanadi.
    ski — solishtirma kombinatör indeks
    k   — zaxira koeffitsienti (max 1, min 0)
    f   — kritik ko'rsatkichlar soni

    Qaytaradi: (sinf_raqami int, tavsif str)
    """
    # F >= 6 → bevosita 5-sinf
    if f >= 6:
        return 5, CLASS_LABELS[5]

    k = max(k, 0.0)   # manfiy bo'lmasin

    # 1-sinf: SKI <= 1*k
    if ski <= 1.0 * k:
        return 1, CLASS_LABELS[1]

    # 2-sinf: (1*k ; 2*k]
    if ski <= 2.0 * k:
        return 2, CLASS_LABELS[2]

    # 3-sinf: (2*k ; 4*k]
    if ski <= 3.0 * k:
        return 3, CLASS_LABELS["3a"]
    if ski <= 4.0 * k:
        return 3, CLASS_LABELS["3b"]

    # 4-sinf: (4*k ; 11*k]
    if ski <= 6.0 * k:
        return 4, CLASS_LABELS["4a"]
    if ski <= 8.0 * k:
        return 4, CLASS_LABELS["4b"]
    if ski <= 10.0 * k:
        return 4, CLASS_LABELS["4v"]
    if ski <= 11.0 * k:
        return 4, CLASS_LABELS["4g"]

    # 5-sinf: (11*k ; ∞)
    return 5, CLASS_LABELS[5]


def get_water_class_label(water_class: int) -> str:
    return CLASS_LABELS.get(water_class, "Noma'lum")


# ═══════════════════════════════════════════════════════
#  Asosiy funksiya: bir yil uchun to'liq hisob
# ═══════════════════════════════════════════════════════
@dataclass
class FinalResult:
    substance_results: list[SubstanceResult]
    ki:          float
    ski:         float
    nj:          int
    f_count:     int
    k_reserve:   float
    water_class: int
    class_label: str
    complexity_k: float        # K%
    critical_names: list[str] = field(default_factory=list)


def calculate_all(
    substances_data: list[dict]
) -> FinalResult:
    """
    substances_data — har bir modda uchun dict:
      {
        "name":           str,
        "mpc":            float,
        "concentrations": [float | None, ...],
        "is_oxygen":      bool
      }

    Qaytaradi: FinalResult
    """
    sub_results: list[SubstanceResult] = []

    for sd in substances_data:
        res = calc_substance(
            name=sd["name"],
            mpc=sd["mpc"],
            concentrations=sd["concentrations"],
            is_oxygen=sd.get("is_oxygen", False),
        )
        if res is not None:
            sub_results.append(res)

    nj         = len(sub_results)
    ki         = calc_ki(sub_results)
    ski        = calc_ski(ki, nj)
    f_count    = sum(1 for r in sub_results if r.is_critical)
    k_reserve  = calc_reserve_coeff(f_count)
    complexity = calc_complexity_coeff(sub_results)
    water_cls, cls_label = get_water_class(ski, k_reserve, f_count)

    critical_names = [r.name for r in sub_results if r.is_critical]

    return FinalResult(
        substance_results=sub_results,
        ki=ki, ski=ski, nj=nj,
        f_count=f_count,
        k_reserve=k_reserve,
        water_class=water_cls,
        class_label=cls_label,
        complexity_k=complexity,
        critical_names=critical_names,
    )
