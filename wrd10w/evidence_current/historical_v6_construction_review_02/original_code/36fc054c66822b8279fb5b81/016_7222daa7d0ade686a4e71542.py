import shutil, os, json
os.makedirs('outputs', exist_ok=True)
shutil.copytree('inputs/previous_candidate', 'outputs/candidate', dirs_exist_ok=True)
shutil.copy('inputs/previous_learning_evidence.json', 'outputs/learning_evidence.json')
shutil.copy('inputs/previous_candidate_plan.json', 'outputs/candidate_plan.json')
print('copied')
for root,dirs,files in os.walk('outputs'):
    for f in files: print(os.path.join(root,f))