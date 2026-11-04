import os, hashlib, json
base = '.'
for root, dirs, files in os.walk('inputs'):
    for f in files:
        p = os.path.join(root, f)
        print(p, os.path.getsize(p))
print('---outputs---')
print(os.listdir('.') )