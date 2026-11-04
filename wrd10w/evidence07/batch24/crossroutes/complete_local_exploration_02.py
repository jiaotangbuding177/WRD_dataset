"""Preserve 01 and declare one new exec title plus authenticated schema wrapper."""
import json
from copy import deepcopy
from recover_crossroutes import R,O,rows,pin,h,can,zr,save

def main():
 schema=R/'output/20261025_wrd_training_dataset/bundle/tools/resources/native_coding_tools_97a0.json'
 provenance=schema.with_suffix('.provenance.json')
 bare=json.loads(schema.read_text(encoding='utf-8'))
 wrapper=O/'NATIVE97A0_SCHEMA_WRAPPER.json'
 wrapped={'schema':'wrd-bare-native97a0-tool-capture-mechanical-wrapper-v1',
  'tools':[{'type':'function','function':x} for x in bare],
  'mechanical_wrapper_not_new_tool_definition':True,'original_bare_capture':pin(schema),'original_provenance':pin(provenance),
  'tools_values_identical_to_bare_capture':True}
 save(wrapper.name,wrapped);assert [x['function'] for x in json.loads(wrapper.read_text(encoding='utf-8'))['tools']]==bare
 original=rows(O/'LOCAL_EXPLORATION.raw.jsonl.gz');out=[];changes=[]
 for v in original:
  row=deepcopy(v);row['tool_schema_provenance']=pin(wrapper)
  row['tool_schema_mechanical_binding']={'bare_capture':pin(schema),'bare_provenance':pin(provenance),'wrapper':pin(wrapper),'registry_exact_values_equal':True}
  c=row['messages'][-1]['tool_calls'][0]
  if c['function']['name']=='exec':
   a=json.loads(c['function']['arguments']);before=a.copy();a['title']='读取路线卡'
   c['function']['arguments']=json.dumps(a,ensure_ascii=False,separators=(',',':'))
   row['annotation_provenance']='NEW_AUTHORED_FUNCTIONAL_STATE_PLUS_EXEC_TITLE_WITH_VERBATIM_ORIGINAL_COMMAND_NOT_ORIGINAL_NATIVE_INPUT_OR_WHOLE_ARGUMENTS'
   row['original_action_was_actually_dispatched']=False
   row['original_command_was_actually_dispatched']=True
   row['argument_field_authorship']={'command':'VERBATIM_ORIGINAL_RECORDED_COMMAND','title':'NEW_AUTHORED_NATIVE_INTERFACE_COMPLETION'}
   row['whole_tool_arguments_are_verbatim_original']=False
   row['evidence']['original_command_sha256']=h(before['command'].encode())
   changes.append({'id':row['id'],'original_arguments':before,'new_arguments':a,'change':'Added title required by native exec description; original command unchanged. No claim whole arguments originally dispatched.'})
  else:
   row['whole_tool_arguments_are_verbatim_original']=True
   row['argument_field_authorship']={'path':'VERBATIM_ORIGINAL_RECORDED_ARGUMENT'}
  out.append(row)
 zr('LOCAL_EXPLORATION_02.raw.jsonl.gz',out)
 save('LOCAL_EXPLORATION_02_COMPLETION.json',{'status':'THREE_NEW_STATE_LOCAL_A_PROJECTIONS_PENDING_ROOT',
  'original01':pin(O/'LOCAL_EXPLORATION.raw.jsonl.gz'),'new02':pin(O/'LOCAL_EXPLORATION_02.raw.jsonl.gz'),
  'raw01_preserved':True,'changes':changes,'schema_wrapper':pin(wrapper),'bare_capture':pin(schema),'bare_provenance':pin(provenance),
  'two_verbatim_read_actions':2,'one_verbatim_command_plus_new_title':1,'original_R':0,
  'training_or_native_executed':False,'script':pin(__file__)})
 print(json.dumps({'new_rows':3,'exec_title_completions':len(changes),'schema_wrapper':pin(wrapper)}))
if __name__=='__main__':main()
