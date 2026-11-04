from pptx import Presentation
from pptx.util import Emu
p = Presentation('/workspace/inputs/materials/conv_fa46a4502e37/2021哈工大机器人智能护理床BP.pptx')
print('slides:', len(p.slides), 'size:', p.slide_width, p.slide_height)
for i, s in enumerate(p.slides):
    print(f'--- slide {i+1} layout={s.slide_layout.name} ---')
    for sh in s.shapes:
        t = ''
        if sh.has_text_frame:
            t = ' | '.join(r.text for para in sh.text_frame.paragraphs for r in para.runs if r.text.strip())[:300]
        print(f'  {sh.shape_type} id={sh.shape_id} name={sh.name!r} text={t[:200]!r}')
