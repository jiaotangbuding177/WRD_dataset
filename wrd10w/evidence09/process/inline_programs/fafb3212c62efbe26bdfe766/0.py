from PIL import Image
im = Image.open('/workspace/inputs/materials/conv_e785906dc669/7_麦角硫因产品1.jpeg').convert('RGB')
print('size:', im.size)
w,h = im.size
# sample regions: top, middle, bottom, corners
import collections
def avg(box):
    region = im.crop(box).resize((1,1), Image.LANCZOS)
    return '#%02x%02x%02x' % region.getpixel((0,0))
print('top:', avg((0,0,w,h//8)))
print('upper-mid:', avg((0,h//8,w,h//3)))
print('mid:', avg((0,h//3,w,2*h//3)))
print('bottom-mid:', avg((0,2*h//3,w,7*h//8)))
print('bottom:', avg((0,7*h//8,w,h)))
# dominant colors quantized
q = im.resize((100,100)).quantize(colors=8)
pal = q.getpalette()
counts = sorted(q.getcolors(), reverse=True)
for c,i in counts[:8]:
    print('dominant:', '#%02x%02x%02x' % tuple(pal[i*3:i*3+3]), c)
