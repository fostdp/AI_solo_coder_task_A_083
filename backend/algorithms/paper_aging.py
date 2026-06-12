"""
纸张老化动力学模型
基于 Arrhenius 方程 + pH 下降速率模型

参考模型：
1. Arrhenius 方程: k = A * exp(-Ea / (R * T))
   k: 反应速率, Ea: 活化能, R: 气体常数, T: 绝对温度(K)
2. pH 下降速率受温度、湿度、初始 pH 综合影响
3. 纸张聚合度(DP)下降与 pH 的关系
"""
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


R_GAS = 8.314

PAPER_TYPE_EA_MAP = {
    "bamboo": 78.0,
    "bark": 85.0,
    "xuan": 92.0,
    "hemp": 88.0,
    "default": 100.0,
}

PAPER_TYPE_LABELS = {
    "bamboo": "竹纸",
    "bark": "皮纸",
    "xuan": "宣纸",
    "hemp": "麻纸",
    "default": "通用手工纸",
}


@dataclass
class AgingPrediction:
    ph_current: float
    ph_30d: float
    ph_90d: float
    ph_180d: float
    ph_365d: float
    aging_rate_per_year: float
    dp_current: float
    dp_365d: float
    life_expectancy_years: float
    risk_level: str
    paper_type: str = "default"
    activation_energy_kj: float = 100.0


class PaperAgingModel:

    def __init__(
        self,
        ea_kj_mol: float = 100.0,
        ref_temp_c: float = 25.0,
        base_rate_ph_year: float = 0.15,
        cellulose_initial_dp: float = 1200.0,
        dp_end_of_life: float = 200.0,
    ):
        self.Ea = ea_kj_mol * 1000.0
        self.T_ref = ref_temp_c + 273.15
        self.base_k_ph = base_rate_ph_year
        self.DP0 = cellulose_initial_dp
        self.DP_EOL = dp_end_of_life
        self.k_ref_ph = self._arrhenius(self.Ea, self.T_ref) * self.base_k_ph

    @staticmethod
    def _arrhenius(ea_j: float, T_abs: float) -> float:
        return math.exp(-ea_j / (R_GAS * T_abs))

    @staticmethod
    def get_ea_for_paper_type(paper_type: str) -> float:
        return PAPER_TYPE_EA_MAP.get(paper_type, PAPER_TYPE_EA_MAP["default"]) * 1000.0

    @staticmethod
    def get_ea_kj_for_paper_type(paper_type: str) -> float:
        return PAPER_TYPE_EA_MAP.get(paper_type, PAPER_TYPE_EA_MAP["default"])

    def _temp_factor(self, temp_c: float, ea_j: float = None) -> float:
        ea = ea_j if ea_j is not None else self.Ea
        T = temp_c + 273.15
        k_T = self._arrhenius(ea, T)
        k_ref = self._arrhenius(ea, self.T_ref)
        return k_T / k_ref if k_ref > 0 else 1.0

    def _humidity_factor(self, rh_percent: float) -> float:
        rh = max(0.0, min(100.0, rh_percent))
        return 1.0 + 0.05 * (rh - 50.0) / 10.0 + 0.02 * ((rh - 50.0) / 10.0) ** 2

    def _ph_sensitivity_factor(self, current_ph: float) -> float:
        if current_ph >= 7.0:
            return 1.0
        elif current_ph >= 6.0:
            return 1.0 + (7.0 - current_ph) * 0.3
        elif current_ph >= 5.0:
            return 1.3 + (6.0 - current_ph) * 0.5
        else:
            return 1.8 + (5.0 - current_ph) * 0.8

    def calculate_instant_aging_rate(
        self,
        temp_c: float,
        rh_percent: float,
        current_ph: float,
        voc_ppm: float = 0.0,
        paper_type: str = "default",
    ) -> float:
        ea_j = self.get_ea_for_paper_type(paper_type)
        f_temp = self._temp_factor(temp_c, ea_j)
        f_hum = self._humidity_factor(rh_percent)
        f_ph = self._ph_sensitivity_factor(current_ph)
        f_voc = 1.0 + voc_ppm * 0.15
        return self.base_k_ph * f_temp * f_hum * f_ph * f_voc

    def predict_ph_over_time(
        self,
        initial_ph: float,
        avg_temp_c: float,
        avg_rh: float,
        avg_voc_ppm: float = 0.0,
        days_list: Optional[List[int]] = None,
        paper_type: str = "default",
    ) -> Dict[int, float]:
        days_list = days_list or [30, 90, 180, 365]
        results = {}
        rate_per_year = self.calculate_instant_aging_rate(
            avg_temp_c, avg_rh, initial_ph, avg_voc_ppm, paper_type
        )
        rate_per_day = rate_per_year / 365.0
        for d in days_list:
            decay_factor = math.exp(-rate_per_day * d * 0.5)
            predicted = initial_ph - rate_per_day * d * decay_factor
            results[d] = max(3.5, round(predicted, 4))
        return results

    def calculate_dp(self, current_ph: float, years_since_manufacture: float = 100.0) -> float:
        acid_factor = max(0.0, 7.0 - current_ph)
        dp_drop_from_acid = acid_factor * 80.0
        dp_drop_age = min(self.DP0 - 300, years_since_manufacture * 3.0)
        return max(self.DP_EOL, self.DP0 - dp_drop_from_acid - dp_drop_age)

    def estimate_life_expectancy(
        self,
        current_ph: float,
        dp_current: float,
        avg_temp_c: float,
        avg_rh: float,
        avg_voc_ppm: float = 0.0,
        paper_type: str = "default",
    ) -> float:
        annual_rate = self.calculate_instant_aging_rate(
            avg_temp_c, avg_rh, current_ph, avg_voc_ppm, paper_type
        )
        ph_to_eol = max(0.0, current_ph - 4.5)
        years_by_ph = ph_to_eol / annual_rate if annual_rate > 0 else 999.0
        dp_to_eol = max(0.0, dp_current - self.DP_EOL)
        dp_annual_drop = annual_rate * 80.0 + 3.0
        years_by_dp = dp_to_eol / dp_annual_drop if dp_annual_drop > 0 else 999.0
        return round(min(years_by_ph, years_by_dp), 1)

    def full_prediction(
        self,
        initial_ph: float,
        avg_temp_c: float,
        avg_rh: float,
        avg_voc_ppm: float = 0.0,
        book_age_years: float = 100.0,
        paper_type: str = "default",
    ) -> AgingPrediction:
        ph_dict = self.predict_ph_over_time(
            initial_ph, avg_temp_c, avg_rh, avg_voc_ppm,
            days_list=[30, 90, 180, 365],
            paper_type=paper_type,
        )
        rate = self.calculate_instant_aging_rate(
            avg_temp_c, avg_rh, initial_ph, avg_voc_ppm, paper_type
        )
        dp_now = self.calculate_dp(initial_ph, book_age_years)
        ph_365 = ph_dict.get(365, initial_ph)
        dp_365 = self.calculate_dp(ph_365, book_age_years + 1.0)
        life = self.estimate_life_expectancy(
            initial_ph, dp_now, avg_temp_c, avg_rh, avg_voc_ppm, paper_type
        )

        if ph_365 < 5.0 or life < 20:
            risk = "CRITICAL"
        elif ph_365 < 5.5 or life < 50:
            risk = "HIGH"
        elif ph_365 < 6.0 or life < 100:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        ea_kj = self.get_ea_kj_for_paper_type(paper_type)

        return AgingPrediction(
            ph_current=round(initial_ph, 4),
            ph_30d=ph_dict.get(30, initial_ph),
            ph_90d=ph_dict.get(90, initial_ph),
            ph_180d=ph_dict.get(180, initial_ph),
            ph_365d=ph_dict.get(365, initial_ph),
            aging_rate_per_year=round(rate, 5),
            dp_current=round(dp_now, 1),
            dp_365d=round(dp_365, 1),
            life_expectancy_years=life,
            risk_level=risk,
            paper_type=paper_type,
            activation_energy_kj=ea_kj,
        )


paper_aging_model = PaperAgingModel()
