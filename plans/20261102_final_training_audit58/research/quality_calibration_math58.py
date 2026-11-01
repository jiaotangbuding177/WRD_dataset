"""CPU-only evaluation-planning math; no model score is predicted."""
import json
import math
from pathlib import Path


def wilson(k, n, z=1.959963984540054):
    assert n > 0 and 0 <= k <= n
    p = k / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [centre - radius, centre + radius]


result = {
    "schema": "wrd58-evaluation-precision-and-cost-math-not-performance-estimates",
    "normal_approximation_worst_case_p": 0.5,
    "z": 1.959963984540054,
    "approximate_independent_components_for_half_width": {
        str(error): math.ceil(1.959963984540054 ** 2 * 0.25 / error ** 2)
        for error in (0.2, 0.15, 0.1)
    },
    "example_precision_if_exactly_half_succeed_not_a_WRD_prediction": {
        str(n): {"k": n // 2, "wilson95": wilson(n // 2, n)}
        for n in (4, 8, 24, 44, 100)
    },
    "four_stage_chain_rule_sensitivity_only_not_WRD_forecast": [
        {
            "all_four_conditional_final_stage_pass_probabilities_hypothetically_equal": p,
            "overall": p ** 4,
            "conditional_probabilities_include_within_stage_repair": True,
            "independence_assumed": False,
        }
        for p in (0.85, 0.9, 0.95)
    ],
    "cost_formula": "U_m(N)=(T_m/N+c_m)/p_m",
    "model14_is_more_cost_effective_iff": "p14/p8 > (T14/N+c14)/(T8/N+c8)",
    "future_sampling_authorized_by_this_file": False,
    "weights_loaded_or_training_started": False,
}
out = Path(__file__).with_name("QUALITY_CALIBRATION_MATH58.json")
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
