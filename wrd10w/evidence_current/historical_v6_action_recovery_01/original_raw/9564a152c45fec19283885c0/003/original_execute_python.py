import json
d = json.load(open('inputs/conversation.json', encoding='utf-8'))
for k in ['session_id','title','task_category','baseline_skill_policy','sequence_basis','native_reply_to_verified','historical_event_identity_verified','schema','original_audit_path','file_references','link_adaptations','user_order_projection']:
    v = d.get(k)
    s = json.dumps(v, ensure_ascii=False)
    print('---', k, ':', s[:600])
print('messages len:', len(d['messages']))
print('turns:', json.dumps(d['turns'], ensure_ascii=False)[:500])