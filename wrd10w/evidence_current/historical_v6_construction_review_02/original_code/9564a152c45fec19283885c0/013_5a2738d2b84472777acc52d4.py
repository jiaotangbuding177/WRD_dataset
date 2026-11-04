import openpyxl
wi = openpyxl.load_workbook('inputs/dev_input.xlsx')
wo = openpyxl.load_workbook('outputs/development_delivery/dev_outputs/masked.xlsx')
a = wi['待脱敏记录']['A1']; b = wo['待脱敏记录']['A1']
for attr in ['font','fill','border','alignment','number_format']:
    sa, sb = getattr(a,attr), getattr(b,attr)
    if sa != sb:
        print('==', attr)
        da = dict(sa.__dict__) if hasattr(sa,'__dict__') else {}
        db = dict(sb.__dict__) if hasattr(sb,'__dict__') else {}
        keys = set(da) | set(db)
        for k in sorted(keys):
            va, vb = da.get(k,'<missing>'), db.get(k,'<missing>')
            if va != vb:
                print('  ', k, ':', repr(va), '->', repr(vb))
                if hasattr(va,'__dict__'):
                    print('      sub:', dict(va.__dict__))
                    print('      sub:', dict(vb.__dict__))