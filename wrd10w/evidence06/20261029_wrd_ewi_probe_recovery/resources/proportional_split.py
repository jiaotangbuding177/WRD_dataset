"""A bounded arithmetic model, with the supplied field vocabulary.

Use finite positive numeric I, decimal s in (0,1), and optional C satisfying
0<C<=Pre, where Post=I/s and Pre=Post-I. With C absent return symbolic split
formulas instead of inventing a unique split. C<=Pre is this model's chosen
non-negative-remainder domain, not a general financial or legal requirement.
The unchanged teacher function uses ordinary Python assertions; run without
-O. Validation is basic and not a full input schema or path-safety validator.
The tol argument is supported here only at its default 1e-6. Extreme floating
point inputs are outside the promised range. Units must be consistent and s
must already be converted to a decimal fraction. No percent-string parsing.
CLI entry always parses its required flags; no fixed sample runs implicitly.
"""
import json, os


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
    main()
