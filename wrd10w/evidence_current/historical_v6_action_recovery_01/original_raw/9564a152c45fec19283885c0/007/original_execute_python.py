import openpyxl
wb = openpyxl.load_workbook('inputs/dev_input.xlsx')
print('sheets:', wb.sheetnames)
for ws in wb.worksheets:
    print('---', ws.title, 'dims:', ws.dimensions, 'max_row:', ws.max_row, 'max_col:', ws.max_column)
    print('merged:', ws.merged_cells.ranges)
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row,18)):
        vals = [(c.coordinate, repr(c.value)[:40], type(c.value).__name__, c.data_type) for c in row]
        print(vals)