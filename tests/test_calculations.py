"""
tests/test_calculations.py
calculations.py moduli uchun unit testlar.

Ishga tushirish:
    cd /mnt/d/test
    python -m pytest tests/ -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from calculations import (
    get_s_alpha,
    get_s_beta,
    calc_substance,
    calc_reserve_coeff,
    calc_ki,
    calc_ski,
    get_water_class,
    calculate_all,
    SubstanceResult,
)


# ═══════════════════════════════════════════════
#  get_s_alpha — E-ilova
# ═══════════════════════════════════════════════
class TestGetSAlpha:
    def test_zero_below_threshold(self):
        """1% dan past → 0"""
        assert get_s_alpha(0.0) == 0.0
        assert get_s_alpha(0.99) == 0.0

    def test_lower_bound_returns_one(self):
        """1% → 1.0"""
        assert get_s_alpha(1.0) == pytest.approx(1.0, abs=0.01)

    def test_range_1_10(self):
        """[1, 10) → [1, 2)"""
        assert 1.0 <= get_s_alpha(1.0) < 2.0
        assert 1.0 <= get_s_alpha(5.0) < 2.0
        assert 1.0 <= get_s_alpha(9.99) < 2.0

    def test_range_10_30(self):
        """[10, 30) → [2, 3)"""
        assert get_s_alpha(10.0) == pytest.approx(2.0, abs=0.01)
        assert 2.0 <= get_s_alpha(20.0) < 3.0
        assert 2.0 <= get_s_alpha(29.99) < 3.0

    def test_range_30_50(self):
        """[30, 50) → [3, 4)"""
        assert get_s_alpha(30.0) == pytest.approx(3.0, abs=0.01)
        assert 3.0 <= get_s_alpha(40.0) < 4.0
        assert 3.0 <= get_s_alpha(49.99) < 4.0

    def test_range_50_plus(self):
        """[50, 100] → 4 (maksimum)"""
        assert get_s_alpha(50.0) == 4.0
        assert get_s_alpha(75.0) == 4.0
        assert get_s_alpha(100.0) == 4.0

    def test_monotone_increasing(self):
        """Alpha oshsa, S_alpha ham oshishi kerak."""
        values = [0, 1, 5, 10, 20, 30, 40, 50, 80, 100]
        scores = [get_s_alpha(v) for v in values]
        assert scores == sorted(scores)


# ═══════════════════════════════════════════════
#  get_s_beta — J-ilova
# ═══════════════════════════════════════════════
class TestGetSBeta:
    def test_no_excess_returns_zero(self):
        """beta <= 1 → 0"""
        assert get_s_beta(0.5) == 0.0
        assert get_s_beta(1.0) == 0.0

    def test_range_1_2(self):
        """(1, 2) → [1, 2)"""
        assert get_s_beta(1.5) == pytest.approx(1.5, abs=0.01)
        assert 1.0 <= get_s_beta(1.01) < 2.0
        assert 1.0 <= get_s_beta(1.99) < 2.0

    def test_range_2_10(self):
        """[2, 10) → [2, 3)"""
        assert get_s_beta(2.0) == pytest.approx(2.0, abs=0.01)
        assert 2.0 <= get_s_beta(5.0) < 3.0
        assert 2.0 <= get_s_beta(9.99) < 3.0

    def test_range_10_50(self):
        """[10, 50) → [3, 4)"""
        assert get_s_beta(10.0) == pytest.approx(3.0, abs=0.01)
        assert 3.0 <= get_s_beta(30.0) < 4.0
        assert 3.0 <= get_s_beta(49.99) < 4.0

    def test_range_50_plus(self):
        """[50, ∞) → 4"""
        assert get_s_beta(50.0) == 4.0
        assert get_s_beta(100.0) == 4.0

    def test_oxygen_special_range(self):
        """Kislorod uchun maxsus gradatsiya."""
        # (1, 1.5] → [1, 2)
        assert 1.0 <= get_s_beta(1.25, is_oxygen=True) < 2.0
        # (1.5, 2] → [2, 3)
        assert 2.0 <= get_s_beta(1.75, is_oxygen=True) < 3.0
        # (2, 3] → [3, 4)
        assert 3.0 <= get_s_beta(2.5, is_oxygen=True) < 4.0
        # (3, ∞) → 4
        assert get_s_beta(3.5, is_oxygen=True) == 4.0

    def test_oxygen_no_excess(self):
        """Kislorodda beta <= 1 → 0."""
        assert get_s_beta(1.0, is_oxygen=True) == 0.0


# ═══════════════════════════════════════════════
#  calc_substance
# ═══════════════════════════════════════════════
class TestCalcSubstance:
    def test_empty_concentrations_returns_none(self):
        result = calc_substance("Fenol", 0.001, [])
        assert result is None

    def test_all_none_concentrations_returns_none(self):
        result = calc_substance("Fenol", 0.001, [None, None])
        assert result is None

    def test_no_exceedance(self):
        """MPC oshilmasa → s_ij = 0, is_critical = False."""
        result = calc_substance("Mis", 0.001, [0.0005, 0.0008, 0.0009])
        assert result is not None
        assert result.ni_exceed == 0
        assert result.s_ij == 0.0
        assert result.is_critical is False

    def test_exceedance_detected(self):
        """MPC oshilgan hollarda to'g'ri hisob.
        Shart: v > mpc (qat'iy), teng qiymat oshish hisoblanmaydi."""
        concs = [0.002, 0.003, 0.0015, 0.0005]  # mpc=0.001: 3 ta oshgan
        result = calc_substance("Mis", 0.001, concs)
        assert result is not None
        assert result.ni == 4
        assert result.ni_exceed == 3
        assert result.alpha == pytest.approx(75.0, abs=0.01)
        assert result.s_ij > 0

    def test_critical_flag(self):
        """s_ij >= 9 bo'lsa is_critical = True."""
        # 100% takroriylik + katta oshish → s_ij >= 9
        concs = [100.0] * 12   # mpc=0.001 → beta = 100000
        result = calc_substance("Fenol", 0.001, concs)
        assert result is not None
        assert result.is_critical is True
        assert result.s_ij >= 9.0

    def test_oxygen_reverse_logic(self):
        """Kislorodda MPC dan PAST bo'lsa oshish hisoblanadi."""
        # mpc = 4.0, qiymatlar: [2.0, 3.0, 5.0] → 2 ta MPC dan past
        result = calc_substance("O2", 4.0, [2.0, 3.0, 5.0], is_oxygen=True)
        assert result is not None
        assert result.ni_exceed == 2

    def test_none_values_skipped(self):
        """None qiymatlar hisobdan chiqariladi."""
        result = calc_substance("Rux", 0.01, [None, 0.02, None, 0.03])
        assert result is not None
        assert result.ni == 2
        assert result.ni_exceed == 2


# ═══════════════════════════════════════════════
#  calc_reserve_coeff
# ═══════════════════════════════════════════════
class TestCalcReserveCoeff:
    def test_no_critical(self):
        """F=0 → k=1.0"""
        assert calc_reserve_coeff(0) == 1.0

    def test_typical_values(self):
        assert calc_reserve_coeff(1) == pytest.approx(0.9, abs=0.0001)
        assert calc_reserve_coeff(5) == pytest.approx(0.5, abs=0.0001)
        assert calc_reserve_coeff(6) == pytest.approx(0.4, abs=0.0001)

    def test_never_negative(self):
        """k hech qachon manfiy bo'lmasligi kerak."""
        for f in range(0, 25):
            assert calc_reserve_coeff(f) >= 0.0, f"F={f} da k manfiy!"

    def test_large_f_clamps_to_zero(self):
        """F >= 10 da k = 0."""
        assert calc_reserve_coeff(10) == 0.0
        assert calc_reserve_coeff(15) == 0.0
        assert calc_reserve_coeff(20) == 0.0


# ═══════════════════════════════════════════════
#  get_water_class
# ═══════════════════════════════════════════════
class TestGetWaterClass:
    def test_class_1(self):
        """SKI <= 1*k → 1-sinf."""
        cls, lbl = get_water_class(ski=0.5, k=1.0, f=0)
        assert cls == 1
        assert "toza" in lbl.lower()

    def test_class_2(self):
        """(1*k ; 2*k] → 2-sinf."""
        cls, lbl = get_water_class(ski=1.5, k=1.0, f=0)
        assert cls == 2

    def test_class_3a(self):
        """(2*k ; 3*k] → 3-sinf."""
        cls, lbl = get_water_class(ski=2.5, k=1.0, f=0)
        assert cls == 3
        assert "3a" in lbl

    def test_class_3b(self):
        cls, lbl = get_water_class(ski=3.5, k=1.0, f=0)
        assert cls == 3
        assert "3b" in lbl

    def test_class_4(self):
        """(4*k ; 11*k] → 4-sinf."""
        cls, lbl = get_water_class(ski=5.0, k=1.0, f=0)
        assert cls == 4

    def test_class_5_by_ski(self):
        """(11*k ; ∞) → 5-sinf."""
        cls, lbl = get_water_class(ski=15.0, k=1.0, f=0)
        assert cls == 5

    def test_class_5_by_f(self):
        """F >= 6 → bevosita 5-sinf."""
        cls, lbl = get_water_class(ski=0.1, k=1.0, f=6)
        assert cls == 5

    def test_negative_k_clamped(self):
        """k manfiy bo'lsa 0 ga clamp qilinadi — cheksiz loop bo'lmaydi."""
        cls, lbl = get_water_class(ski=5.0, k=-0.5, f=0)
        assert cls == 5   # k=0 da hamma SKI > 0 → 5-sinf


# ═══════════════════════════════════════════════
#  calculate_all — integratsiya testi
# ═══════════════════════════════════════════════
class TestCalculateAll:
    def _make_data(self, concs, mpc=0.001, is_oxygen=False):
        return {"name": "TestModda", "mpc": mpc,
                "concentrations": concs, "is_oxygen": is_oxygen}

    def test_empty_returns_class_1(self):
        """Ma'lumot yo'q → barcha ko'rsatkichlar 0, sinf 1."""
        result = calculate_all([])
        assert result.ki == 0.0
        assert result.ski == 0.0
        assert result.water_class == 1

    def test_no_exceedance(self):
        """Hech qaysi MPC oshilmasa → sinf 1."""
        data = [self._make_data([0.0005, 0.0008], mpc=0.001)]
        result = calculate_all(data)
        assert result.water_class == 1
        assert result.f_count == 0

    def test_high_pollution(self):
        """Kuchli ifloslanish → yuqori sinf."""
        # 100% takroriylik, 100x oshgan
        data = [
            self._make_data([0.1, 0.2, 0.15, 0.12], mpc=0.001),   # Fenol
            self._make_data([0.5, 0.8, 0.6,  0.7],  mpc=0.001),   # Mis
        ]
        result = calculate_all(data)
        assert result.water_class >= 4

    def test_ki_equals_sum_of_sij(self):
        """KI = Σ S_ij."""
        data = [
            self._make_data([0.002, 0.003], mpc=0.001),
            self._make_data([0.05,  0.08],  mpc=0.01),
        ]
        result = calculate_all(data)
        expected_ki = sum(r.s_ij for r in result.substance_results)
        assert result.ki == pytest.approx(expected_ki, abs=0.0001)

    def test_ski_equals_ki_divided_by_nj(self):
        """SKI = KI / Nj."""
        data = [
            self._make_data([0.002, 0.003], mpc=0.001),
            self._make_data([0.05,  0.08],  mpc=0.01),
        ]
        result = calculate_all(data)
        if result.nj > 0:
            assert result.ski == pytest.approx(result.ki / result.nj, abs=0.0001)

    def test_oxygen_included(self):
        """Kislorod modda to'g'ri ishlanadi."""
        data = [self._make_data([1.0, 2.0, 5.0], mpc=4.0, is_oxygen=True)]
        result = calculate_all(data)
        # 2 ta MPC dan past → oshish bor
        assert result.substance_results[0].ni_exceed == 2

    def test_critical_names_collected(self):
        """Kritik moddalar nomlari to'g'ri yig'iladi."""
        concs = [100.0] * 12
        data = [
            {"name": "Fenol", "mpc": 0.001, "concentrations": concs, "is_oxygen": False},
            {"name": "Mis",   "mpc": 0.001, "concentrations": [0.0005], "is_oxygen": False},
        ]
        result = calculate_all(data)
        assert "Fenol" in result.critical_names
        assert "Mis" not in result.critical_names
