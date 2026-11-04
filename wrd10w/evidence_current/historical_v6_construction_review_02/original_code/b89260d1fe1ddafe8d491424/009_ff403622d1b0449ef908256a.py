import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
rev = fb['independent_public_content_review']
print('FINDINGS:')
print(json.dumps(rev.get('findings'), ensure_ascii=False, indent=1))
print('SUPPORTED OBS:', json.dumps(rev.get('supported_observations'), ensure_ascii=False)[:2000])
print('HARD PATH SCAN:', json.dumps(rev.get('program_hard_path_scan'), ensure_ascii=False)[:1500])
print('COMPLEX EXCEL BOUNDARY:', json.dumps(rev.get('complex_excel_boundary'), ensure_ascii=False)[:1500])
print('README IS CONSUMER:', json.dumps(rev.get('readme_is_consumer_resource'), ensure_ascii=False)[:1500])
print('RESOURCES:', json.dumps(rev.get('resources'), ensure_ascii=False)[:2000])
print('RECOMMENDATION:', json.dumps(rev.get('recommendation'), ensure_ascii=False)[:1500])
