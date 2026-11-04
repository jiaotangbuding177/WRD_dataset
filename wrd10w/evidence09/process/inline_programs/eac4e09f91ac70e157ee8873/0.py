import pdfplumber
for name in ["5_【生产运营总监_广州 25-35K】宋先生 4年.pdf", "6_【生产运营总监_广州 25-35K】黄和芳 10年以上.pdf"]:
    path = f"/workspace/inputs/materials/conv_495ce24cf535/{name}"
    print("="*80)
    print("FILE:", name)
    print("="*80)
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"--- page {i+1} ---")
            print(page.extract_text() or "(no text)")
