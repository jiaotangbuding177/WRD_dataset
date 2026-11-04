import json, os, sys


def compute_valuation(increase_amount, post_stake, pre_registered_capital=None, tol=1e-6):
    """Generic: post-money = increase / post_stake; split increase into registered capital and capital reserve."""
    assert increase_amount > 0, "increase_amount must be positive"
    assert 0.0 < post_stake < 1.0, "post_stake must be a decimal in (0,1)"
    post_money = increase_amount / post_stake
    pre_money = post_money - increase_amount
    assert abs(post_stake * post_money - increase_amount) <= tol * increase_amount, "back-substitution failed"
    out = {
        "increase_amount": increase_amount,
        "post_stake": post_stake,
        "post_money_valuation": post_money,
        "pre_money_valuation": pre_money,
    }
    if pre_registered_capital is not None:
        assert pre_registered_capital > 0, "pre_registered_capital must be positive"
        assert pre_registered_capital <= pre_money + tol, "pre_registered_capital exceeds pre-money valuation -> negative capital reserve"
        price_per_unit = pre_money / pre_registered_capital
        new_registered = increase_amount / price_per_unit
        capital_reserve = increase_amount - new_registered
        assert abs(new_registered + capital_reserve - increase_amount) <= tol * increase_amount, "split does not sum to increase"
        implied = new_registered / (pre_registered_capital + new_registered)
        assert abs(implied - post_stake) <= 1e-6, "implied post stake mismatch"
        out.update({
            "pre_registered_capital": pre_registered_capital,
            "price_per_unit": price_per_unit,
            "new_registered_capital": new_registered,
            "capital_reserve": capital_reserve,
            "implied_post_stake": implied,
        })
    else:
        out["formula"] = {
            "new_registered_capital": "increase_amount * pre_registered_capital / pre_money_valuation",
            "capital_reserve": "increase_amount - new_registered_capital",
            "constraint": "pre_registered_capital <= pre_money_valuation",
        }
    return out


def main():
    import argparse
    p = argparse.ArgumentParser(description="增资估值与注册资本/资本公积拆分")
    p.add_argument("--increase", type=float, required=True)
    p.add_argument("--post-stake", type=float, required=True)
    p.add_argument("--pre-registered", type=float, default=None)
    p.add_argument("--out", default="outputs/valuation_result.json")
    a = p.parse_args()
    r = compute_valuation(a.increase, a.post_stake, a.pre_registered)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if "--increase" in sys.argv:
        main()
    else:
        # self-verification with this episode's parameters (480万 / 14.2012% / 投前注册资本1000万)
        r = compute_valuation(480.0, 0.142012, 1000.0)
        assert abs(r["post_money_valuation"] - 3380.0) < 1.0
        assert abs(r["pre_money_valuation"] - 2900.0) < 1.0
        assert abs(r["new_registered_capital"] - 165.52) < 0.1
        assert abs(r["capital_reserve"] - 314.48) < 0.1
        # missing-parameter branch must not invent a unique split
        r2 = compute_valuation(480.0, 0.142012, None)
        assert "formula" in r2 and "new_registered_capital" not in r2
        os.makedirs("outputs", exist_ok=True)
        with open("outputs/valuation_result.json", "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        print(json.dumps(r, ensure_ascii=False, indent=2))
