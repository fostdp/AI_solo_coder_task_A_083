import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class MoldGrowthResult:
    mold_risk_index: float
    mold_growth_rate: float
    germination_likelihood: float
    mycelium_coverage_days: float
    spore_production_risk: float
    active_mold_risk: float
    insect_risk_index: float
    mold_species: List[str] = field(default_factory=list)


class MoldGrowthModel:
    R = 8.314

    SPECIES = [
        {
            "name": "Aspergillus flavus",
            "zh": "黄曲霉",
            "T_opt": (28.0, 33.0),
            "RH_min": 0.80,
            "RH_opt": (0.90, 0.95),
            "activation_kj": 70.0,
            "toxin": True,
            "paper_digest": True,
        },
        {
            "name": "Aspergillus niger",
            "zh": "黑曲霉",
            "T_opt": (25.0, 30.0),
            "RH_min": 0.75,
            "RH_opt": (0.85, 0.95),
            "activation_kj": 65.0,
            "toxin": True,
            "paper_digest": True,
        },
        {
            "name": "Penicillium chrysogenum",
            "zh": "产黄青霉",
            "T_opt": (22.0, 28.0),
            "RH_min": 0.78,
            "RH_opt": (0.85, 0.92),
            "activation_kj": 62.0,
            "toxin": False,
            "paper_digest": True,
        },
        {
            "name": "Chaetomium globosum",
            "zh": "球毛壳霉",
            "T_opt": (25.0, 32.0),
            "RH_min": 0.82,
            "RH_opt": (0.92, 0.98),
            "activation_kj": 75.0,
            "toxin": False,
            "paper_digest": True,
        },
        {
            "name": "Trichoderma viride",
            "zh": "绿色木霉",
            "T_opt": (24.0, 30.0),
            "RH_min": 0.80,
            "RH_opt": (0.88, 0.96),
            "activation_kj": 60.0,
            "toxin": False,
            "paper_digest": True,
        },
    ]

    def _temperature_response(self, T_c: float, T_opt_min: float, T_opt_max: float, Ea_kj: float) -> float:
        if T_c <= 0 or T_c >= 55:
            return 0.0
        T_k = T_c + 273.15
        T_opt_mid = (T_opt_min + T_opt_max) / 2 + 273.15
        Ea = Ea_kj * 1000.0
        R = 8.314
        try:
            arrh = math.exp(Ea / R * (1 / T_opt_mid - 1 / T_k))
        except OverflowError:
            arrh = 0.0
        if T_c < T_opt_min:
            penalty = math.exp(-0.15 * (T_opt_min - T_c) ** 2)
        elif T_c > T_opt_max:
            penalty = math.exp(-0.12 * (T_c - T_opt_max) ** 2)
        else:
            penalty = 1.0
        return max(0.0, min(1.5, arrh * penalty))

    def _humidity_response(self, rh_percent: float, rh_min: float, rh_opt_min: float, rh_opt_max: float) -> float:
        rh = rh_percent / 100.0
        if rh < rh_min:
            return max(0.0, math.exp(-8.0 * (rh_min - rh)))
        if rh < rh_opt_min:
            t = (rh - rh_min) / (rh_opt_min - rh_min) if rh_opt_min > rh_min else 1.0
            return 0.1 + 0.9 * t
        if rh <= rh_opt_max:
            return 1.0
        return max(0.7, 1.0 - 2.5 * (rh - rh_opt_max))

    def evaluate(
        self,
        temp_c: float,
        rh_percent: float,
        exposure_hours: float,
        spore_concentration: float,
        active_mold_flag: int = 0,
        voc_ppm: float = 0.0,
    ) -> MoldGrowthResult:
        T = max(-10.0, min(60.0, float(temp_c)))
        RH = max(0.0, min(100.0, float(rh_percent)))
        exposure_h = max(0.0, float(exposure_hours))
        spores = max(0.0, float(spore_concentration))
        voc = max(0.0, float(voc_ppm))
        active = int(active_mold_flag)

        species_risks: List[Dict[str, Any]] = []
        for sp in self.SPECIES:
            t_resp = self._temperature_response(T, sp["T_opt"][0], sp["T_opt"][1], sp["activation_kj"])
            h_resp = self._humidity_response(RH, sp["RH_min"], sp["RH_opt"][0], sp["RH_opt"][1])
            combined = t_resp * h_resp
            species_risks.append({
                "spec": sp,
                "t_resp": t_resp,
                "h_resp": h_resp,
                "combined": combined,
            })

        species_risks.sort(key=lambda x: x["combined"], reverse=True)
        top_species = species_risks[:3]

        avg_combined = sum(s["combined"] for s in species_risks) / max(1, len(species_risks))
        max_combined = max(s["combined"] for s in species_risks)

        spore_factor = 1.0 + math.log1p(spores / 100.0) / math.log(101.0) * 2.5
        if spores > 1000:
            spore_factor *= 1.5
        if spores < 50:
            spore_factor *= 0.4

        exposure_factor = 1.0 - math.exp(-exposure_h / 48.0)

        voc_factor = 1.0 + 0.15 * voc

        mold_growth_rate = max_combined * spore_factor * voc_factor

        germination_likelihood = min(1.0, avg_combined * spore_factor * (1.0 - math.exp(-exposure_h / 12.0)))
        germination_likelihood *= (0.4 + 0.6 * min(1.0, spores / 500.0))

        if germination_likelihood > 0.1 and mold_growth_rate > 0.1:
            coverage_rate = 0.08 * mold_growth_rate * germination_likelihood
            if coverage_rate > 0:
                mycelium_coverage_days = max(1.0, 1.0 / coverage_rate)
            else:
                mycelium_coverage_days = 999.0
        else:
            mycelium_coverage_days = 999.0

        spore_production_risk = min(1.0, germination_likelihood * (1.0 - math.exp(-exposure_h / 240.0)) * (0.3 + 0.7 * min(1.0, spores / 1500.0)))

        active_mold_risk = min(1.0, active + (0.5 * germination_likelihood * (1.0 - math.exp(-exposure_h / 120.0))))

        mold_risk_index = 0.35 * max_combined + 0.25 * germination_likelihood + 0.2 * spore_production_risk + 0.2 * active_mold_risk
        mold_risk_index = max(0.0, min(1.0, mold_risk_index * spore_factor * exposure_factor))

        insect_temp_factor = max(0.0, min(1.0, (T - 10.0) / 20.0) if T < 30 else max(0.0, 1.0 - (T - 30.0) / 15.0))
        insect_humi_factor = 0.6 + 0.4 * (RH / 100.0)
        insect_mold_factor = 1.0 + 0.5 * mold_risk_index
        insect_risk_index = min(1.0, 0.28 * insect_temp_factor * insect_humi_factor * insect_mold_factor * (0.5 + 0.5 * min(1.0, spores / 2000.0)))

        susceptible = [s["spec"]["zh"] for s in top_species if s["combined"] > 0.15]
        if not susceptible and (spores > 200 or active):
            susceptible = [s["spec"]["zh"] for s in top_species]

        return MoldGrowthResult(
            mold_risk_index=round(mold_risk_index, 4),
            mold_growth_rate=round(mold_growth_rate, 4),
            germination_likelihood=round(germination_likelihood, 4),
            mycelium_coverage_days=round(mycelium_coverage_days, 1),
            spore_production_risk=round(spore_production_risk, 4),
            active_mold_risk=round(active_mold_risk, 4),
            insect_risk_index=round(insect_risk_index, 4),
            mold_species=susceptible,
        )


mold_growth_model = MoldGrowthModel()
