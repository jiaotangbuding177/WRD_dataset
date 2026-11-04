import os
for root, dirs, files in os.walk('outputs'):
    dirs.sort()
    for f in sorted(files):
        p = os.path.join(root, f)
        print(p, os.path.getsize(p))