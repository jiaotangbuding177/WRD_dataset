import os, json
os.makedirs('outputs', exist_ok=True)

def classify(summary):
    s = summary or ''
    if '利息' in s or '收息' in s or '结息' in s:
        return 'interest'
    if '手续费' in s or '服务费' in s:
        return 'fee'
    if '出资' in s or '投资款' in s or '实收资本' in s:
        return 'capital'
    return 'expense'

def build_vouchers(rows):
    vouchers = []
    for r in rows:
        amt_in = float(r.get('debit') or 0)
        amt_out = float(r.get('credit') or 0)
        cat = classify(r.get('summary'))
        if cat == 'interest':
            entries = [['银行存款', amt_in], ['财务费用—手续费', -amt_in]]
        elif cat == 'fee':
            entries = [['财务费用—手续费', amt_out], ['银行存款', -amt_out]]
        elif cat == 'capital':
            entries = [['银行存款', amt_in], ['实收资本', -amt_in]]
        else:
            if amt_out:
                entries = [['管理费用—报销款', amt_out], ['银行存款', -amt_out]]
            else:
                entries = [['银行存款', amt_in], ['其他应付款', -amt_in]]
        vouchers.append({'date': r.get('date'), 'summary': r.get('summary'), 'entries': entries})
    return vouchers

def balanced(v):
    return abs(sum(e[1] for e in v['entries'])) < 1e-9

def run_checks(vouchers, rows):
    assert len(vouchers) == len(rows), 'voucher count must equal transaction count'
    for v in vouchers:
        assert balanced(v), 'unbalanced voucher: %r' % (v,)
    for v in vouchers:
        if classify(v['summary']) == 'interest':
            d = dict(v['entries'])
            assert '银行存款' in d and '财务费用—手续费' in d, v
            assert d['财务费用—手续费'] == -d['银行存款'], v
            assert d['银行存款'] > 0, v
    total = sum(e[1] for v in vouchers for e in v['entries'])
    assert abs(total) < 1e-9, 'global debit/credit must net to zero'
    return True

rows = [
    {'date': '2025-12-21', 'summary': '收息', 'debit': 0.14, 'credit': 0},
    {'date': '2026-03-21', 'summary': '收息', 'debit': 0.13, 'credit': 0},
    {'date': '2025-11-02', 'summary': '网上企业银行服务费', 'debit': 0, 'credit': 25},
    {'date': '2025-08-07', 'summary': '收到股东出资款', 'debit': 30000, 'credit': 0},
    {'date': '2025-10-17', 'summary': '支付李蓉报销款', 'debit': 0, 'credit': 300},
]
vs = build_vouchers(rows)
run_checks(vs, rows)
with open('outputs/voucher_selftest.json', 'w', encoding='utf-8') as f:
    json.dump(vs, f, ensure_ascii=False, indent=2)
print('SELFTEST_OK', len(vs))
