import os, json, sys
from openpyxl import Workbook, load_workbook

os.makedirs('outputs', exist_ok=True)


def classify(summary):
    s = summary or ''
    if any(k in s for k in ('利息', '收息', '结息', '存款利息')):
        return 'interest'
    if any(k in s for k in ('手续费', '服务费', '工本费', '网银', '网上企业银行')):
        return 'fee'
    if any(k in s for k in ('出资', '投资款', '实收资本', '股东')):
        return 'capital'
    return 'expense'


def read_journal(path):
    """按表头关键字定位列，读取全部数据行（非仅样本）。"""
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    if not rows:
        return []
    header = [('' if h is None else str(h)) for h in rows[0]]

    def find(cols):
        for i, h in enumerate(header):
            if any(c in h for c in cols):
                return i
        return None

    i_date = find(['日期', '时间'])
    i_sum = find(['摘要', '备注', '用途', '说明'])
    i_in = find(['借方', '收入', '进账', '存入'])
    i_out = find(['贷方', '支出', '出账', '付出'])
    if i_sum is None or i_in is None or i_out is None:
        raise ValueError('无法定位必要列，请检查表头: %r' % header)
    out = []
    for r in rows[1:]:
        if r is None or all(v is None or str(v).strip() == '' for v in r):
            continue

        def g(i):
            return r[i] if (i is not None and i < len(r)) else None

        dv = g(i_in)
        cv = g(i_out)
        out.append({
            'date': '' if g(i_date) is None else str(g(i_date)),
            'summary': '' if g(i_sum) is None else str(g(i_sum)),
            'debit': float(dv) if (dv not in (None, '')) else 0.0,
            'credit': float(cv) if (cv not in (None, '')) else 0.0,
        })
    return out


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
        elif amt_out:
            entries = [['管理费用—报销款', amt_out], ['银行存款', -amt_out]]
        else:
            entries = [['银行存款', amt_in], ['其他应付款', -amt_in]]
        vouchers.append({'date': r.get('date'), 'summary': r.get('summary'), 'entries': entries})
    return vouchers


def run_checks(vouchers, rows):
    assert len(vouchers) == len(rows), '凭证数必须等于交易行数'
    for v in vouchers:
        assert abs(sum(e[1] for e in v['entries'])) < 1e-9, '凭证借贷不平衡: %r' % (v,)
    for v in vouchers:
        if classify(v['summary']) == 'interest':
            d = dict(v['entries'])
            assert '银行存款' in d and '财务费用—手续费' in d, v
            assert d['银行存款'] > 0, v
            assert abs(d['财务费用—手续费'] + d['银行存款']) < 1e-9, v
    total = sum(e[1] for v in vouchers for e in v['entries'])
    assert abs(total) < 1e-9, '全局借贷必须净额为0'
    return True


def write_vouchers(vouchers, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(vouchers, f, ensure_ascii=False, indent=2)


def run_pipeline(input_path, output_path):
    rows = read_journal(input_path)
    vs = build_vouchers(rows)
    run_checks(vs, rows)
    write_vouchers(vs, output_path)
    return len(vs)


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        n = run_pipeline(sys.argv[1], sys.argv[2])
        print('CLI_OK', n)
    else:
        wb = Workbook()
        ws = wb.active
        ws.append(['交易日期', '摘要', '借方发生额', '贷方发生额', '余额'])
        for row in [('2025-12-21', '收息', 0.14, 0),
                    ('2026-03-21', '收息', 0.13, 0),
                    ('2025-11-02', '网上企业银行服务费', 0, 25),
                    ('2025-08-07', '收到股东出资款', 30000, 0),
                    ('2025-10-17', '支付李蓉报销款', 0, 300)]:
            ws.append(list(row))
        wb.save('outputs/synthetic_journal.xlsx')
        rows = read_journal('outputs/synthetic_journal.xlsx')
        assert len(rows) == 5, '读入行数应为5'
        vs = build_vouchers(rows)
        run_checks(vs, rows)
        write_vouchers(vs, 'outputs/voucher_selftest.json')
        print('SELFTEST_OK', len(vs))
