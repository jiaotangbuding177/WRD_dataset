from docx import Document
d = Document("/workspace/outputs/英语教案.docx")
print("paragraphs:", len(d.paragraphs), "tables:", len(d.tables))
print("stage rows:", len(d.tables[1].rows))
import os
print("size:", os.path.getsize("/workspace/outputs/英语教案.docx"))
