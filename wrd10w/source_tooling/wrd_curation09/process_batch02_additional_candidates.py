"""Three additional source-faithful views; exact resource bytes are restored."""
import gzip,json,shutil
from pathlib import Path
from process_batch02_candidates import main as build,OUT,sha,h,dump

SPECS={
'66e542b63e52392b7e1dbfc2':([4],[], '原生read已明确说当前模型不能直接接收图片。使用已给定原图文件，将图片缩至60×60并按24级色阶量化计数，再将五个区域各缩至1像素取得代表色；这不等于原始像素的算术平均。本步仅作本地颜色探针，不声称已分割出背景、完成CSS或检验文字对比度。'),
'34f134a3d93f1405eebd086d':([2],[], '将实际源请求中的Jane、红色285基于1%计算以及汇率未确认因此尚未折美元的意思完整翻译成英文，写入指定纯文本文件；不计算或补造汇率。'),
'3a6ae80e4fedc707aa74773f':([2],[], '将原地址完整翻成英文并写入纯文本，保留2808室、科学之门、中科路1819号、浦东新区、上海市全部要素。本次不验证建筑官方注册英文名或地理位置。'),
}

def main():
    build(SPECS,'SCOPED_ADDITIONAL_CANDIDATES03_v2','CANDIDATE_ADDITIONAL03_v2_BASE_REVIEW.json')
    path=OUT/'SCOPED_ADDITIONAL_CANDIDATES03_v2.jsonl.gz'
    rows=list(map(json.loads,gzip.open(path,'rt',encoding='utf8')))
    src=Path('E:/skillloop_runs/workflow_library/actor__image-editing__conv_e785906dc669_bg_color_optimize__workflow/attempt_1/workspace/inputs/materials/conv_e785906dc669/7_麦角硫因产品1.jpeg')
    dest=OUT/'materials'/'66e542b63e52392b7e1dbfc2'/'7_麦角硫因产品1.jpeg'
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    material={'original_native_path':'/workspace/inputs/materials/conv_e785906dc669/7_麦角硫因产品1.jpeg',
        'actual_historical_workspace_path':str(src),'restored_path':str(dest.resolve()),
        'bytes':src.stat().st_size,'sha256':sha(src),'restored_sha256':sha(dest),
        'source_id':'conv_e785906dc669','episode_id':'ep_051febff7ab47225abe8',
        'source_workspace_provenance':'output/20261025_wrd_training_dataset/bundle/catalog/episodes.jsonl exact episode source_path, workspace/inputs/materials original path'}
    assert material['sha256']==material['restored_sha256']
    for row in rows:
        row['original_recorded_action_owner']=row['owner_id']
        if row['owner_id']=='66e542b63e52392b7e1dbfc2':
            row['execution_material_dependencies']=[material]
            call=row['messages'][2]['tool_calls'][0];command=json.loads(call['function']['arguments'])['command']
            lo=command.index('import statistics\n');hi=command.index("for name, fy0, fy1 in")
            row['target_code_unicode_exclusions']=[{'start':lo,'end':hi,'text':command[lo:hi],'text_sha256':h(command[lo:hi]),
                'reason':'Unused statistics import and first crop loop emit no result; historical comment falsely calls the already pixel-based fractions wrong. Exclude redundant/incorrect-comment section, retain complete exact original code.'}]
            row['target_original_code_sha256']=h(command);row['target_original_command_sha256']=h(command)
            row['target_tool_call_id']=call['id'];row['target_exclusion_argument_name']='command'
            row['exclusion_target_field']='messages[2].tool_calls[0].function.arguments.command'
            row['curator_scope_correction']='PIL resize((1,1)) representative colors are not claimed pixel arithmetic means; original action arguments unchanged.'
    with gzip.open(path,'wt',encoding='utf8')as stream:
        for row in rows:stream.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    dump(OUT/'CANDIDATE_ADDITIONAL03_v2_REVIEW.json',{'status':'PENDING_ROOT_QA_NOT_ADMISSION','count':len(rows),
        'candidate_sha256':sha(path),'material':material,'all_target_args_exact':True,'original_R':0,'new_R':0,
        'exec_command_exclusion':next(r['target_code_unicode_exclusions']for r in rows if r['owner_id']=='66e542b63e52392b7e1dbfc2'),
        'curator_scope_correction':'Representative resized colors, not arithmetic means. Only new state and credit corrected; all original tool argument values retained.',
        'whole_skill_KEEP':0,'business_calls':0,'training_runs':0,'curation_cost':'UNKNOWN_NOT_ZERO','script_sha256':sha(__file__)})
    print('Additional source-faithful candidates',len(rows))
if __name__=='__main__':main()
