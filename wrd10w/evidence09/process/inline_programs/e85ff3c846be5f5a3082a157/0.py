from PIL import Image
import pathlib
for p in sorted(pathlib.Path('/workspace/outputs').glob('*.png')):
    im = Image.open(p)
    print(p.name, im.size, f'{p.stat().st_size//1024}KB')
