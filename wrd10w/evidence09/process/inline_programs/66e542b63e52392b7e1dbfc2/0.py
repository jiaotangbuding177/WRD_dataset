from PIL import Image
from collections import Counter
im = Image.open('/workspace/inputs/materials/conv_e785906dc669/7_麦角硫因产品1.jpeg').convert('RGB')
w,h = im.size
print('size', w, h)
small = im.resize((60, 60))
# overall dominant colors
def hexc(c): return '#%02x%02x%02x' % c
px = list(small.getdata())
cq = Counter((r//24*24, g//24*24, b//24*24) for r,g,b in px)
print('top colors overall:')
for c,n in cq.most_common(8):
    print(hexc(c), n)
# top region / middle / bottom rows average
import statistics
for name, (y0,y1) in [('top',(0,h//6)),('upper-mid',(h//6,h//3)),('middle',(h//3,2*h//3)),('lower',(2*h//3,5*h//6)),('bottom',(5*h//6,h))]:
    box = im.crop((0,int(y0*h) if False else int(y0), w, int(y1)))
    # y0,y1 already pixel-based fractions computed wrong; redo properly
for name, fy0, fy1 in [('top',0,1/6),('upper-mid',1/6,1/3),('middle',1/3,2/3),('lower',2/3,5/6),('bottom',5/6,1)]:
    box = im.crop((0,int(h*fy0), w, int(h*fy1)))
    bs = box.resize((1,1))
    print(name, hexc(bs.getpixel((0,0))))
