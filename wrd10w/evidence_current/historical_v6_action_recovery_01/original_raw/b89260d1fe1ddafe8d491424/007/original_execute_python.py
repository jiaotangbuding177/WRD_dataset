import json
fb = json.load(open('inputs/validation_feedback.json', encoding='utf-8'))
rev = fb['previous_validation']['learning_evidence_review']
print('passed:', rev.get('passed'))
print(json.dumps(rev.get('findings'), ensure_ascii=False, indent=1)[:4000])
print('--- source_and_policy_assessment ---')
print(json.dumps(rev.get('source_and_policy_assessment'), ensure_ascii=False)[:2500])
print('--- prior_finding_resolutions ---')
print(json.dumps(rev.get('prior_finding_resolutions'), ensure_ascii=False)[:2500])
