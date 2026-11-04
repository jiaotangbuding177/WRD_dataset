import shutil, os
shutil.rmtree('outputs/candidate/scripts/__pycache__')
print(sorted(os.listdir('outputs/candidate/scripts')))
print(sorted(os.listdir('outputs')))