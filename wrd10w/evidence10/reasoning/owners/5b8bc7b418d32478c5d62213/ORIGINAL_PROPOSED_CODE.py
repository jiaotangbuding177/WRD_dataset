import json, os


def compute_valuation(increase_amount, post_stake, pre_registered_capital=None, tol=1e-6):
    """post_money = increase / post_stake; split increase into registered capital and capital reserve."""
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
    # Generality check with a DIFFERENT parameter set than the episode's 480/14.2012%/1000.
    r = compute_valuation(1000.0, 0.25, 2000.0)
    assert abs(r["post_money_valuation"] - 4000.0) < 1e-6, "post-money mismatch on new params"
    assert abs(r["pre_money_valuation"] - 3000.0) < 1e-6, "pre-money mismatch on new params"
    assert abs(r["new_registered_capital"] - 666.6666666667) < 1e-3, "new registered capital mismatch"
    assert abs(r["capital_reserve"] - 333.3333333333) < 1e-3, "capital reserve mismatch"
    assert abs(r["implied_post_stake"] - 0.25) < 1e-9, "implied stake mismatch"
    assert abs(r["new_registered_capital"] + r["capital_reserve"] - 1000.0) < 1e-6, "split not conserved"

    # Missing-parameter branch must return formula only, never a unique split.
    r2 = compute_valuation(1000.0, 0.25, None)
    assert "formula" in r2 and "new_registered_capital" not in r2, "missing-param branch invented a split"

    # Negative case: pre_registered > pre_money must raise, not silently produce negative reserve.
    raised = False
    try:
        compute_valuation(1000.0, 0.25, 3500.0)
    except AssertionError:
        raised = True
    assert raised, "pre_registered > pre_money must raise AssertionError"

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/valuation_generality_check.json", "w", encoding="utf-8") as f:
        json.dump({"case": r, "missing_param_keys": sorted(r2.keys()), "negative_case_raised": raised}, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "post_money": r["post_money_valuation"], "new_registered": r["new_registered_capital"], "capital_reserve": r["capital_reserve"], "negative_raised": raised}, ensure_ascii=False))


if __name__ == "__main__":
    main()
