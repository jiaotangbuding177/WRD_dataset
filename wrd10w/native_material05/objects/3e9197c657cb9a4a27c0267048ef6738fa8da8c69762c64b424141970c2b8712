import pymupdf, pathlib
from fontTools.ttLib import TTFont
from fontTools import subset

FIX = pathlib.Path("/workspace/tmp/fixtures")
SRC = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

texts = [
    ["张三", "12年工作经验 | 人力资源经理", "个人优势：熟悉三支柱，擅长绩效薪酬。",
     "2018.03-至今 某机器人公司 人力资源经理，负责招聘机器人算法工程师30人。"],
    ["李四", "5年工作经验 | 招聘专员", "个人优势：校招经验丰富。无总监经历。"],
]
allchars = set("".join("".join(t) for t in texts) + "0123456789.-| ")

# Subset the SC face of the TTC down to just the needed glyphs.
opts = subset.Options()
ss = subset.Subsetter(options=opts)
ss.populate(unicodes=[ord(c) for c in allchars])
font = TTFont(SRC, fontNumber=2)  # 2 = SC face in Noto CJK ttc
ss.subset(font)
small = FIX / "_subset.ttf"
font.save(small)
print("subset ttf size:", small.stat().st_size)

def make_pdf(path, lines):
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((50, y), line, fontfile=str(small), fontname="cjk", fontsize=11)
        y += 18
    doc.save(path, garbage=4, deflate=True)
    doc.close()

make_pdf(FIX / "synthetic_cv_A.pdf", texts[0])
make_pdf(FIX / "synthetic_cv_B.pdf", texts[1])
print("fixtures done")
