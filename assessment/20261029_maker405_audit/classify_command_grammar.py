"""Close the no-program finding by checking every actual exec argument."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import shlex
OUT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not(OUT/'COMMAND_GRAMMAR_QA.json').exists();commands=[];programs=Counter();blocks=Counter();tools=Counter();empty=0;native_equal=0;texts=[];grammar=[]
    for p in sorted((OUT/'allowed_targets').glob('*.json')):
        d=json.loads(p.read_text(encoding='utf-8'));m=d['actual_original_target_message'];assert isinstance(m['content'],list);native_equal+=d['provenance']['native_content_equal_old_canonical'];empty+=not m['content']
        assert not isinstance(m.get('reasoning_content'),str)or not m['reasoning_content']
        for block in m['content']:
            blocks[block['type']]+=1
            if block['type']=='text':texts.append(block.get('text',''));assert not any(marker in block.get('text','')for marker in('```','def ','function ','<html','#!/'));continue
            assert block['type']=='toolCall';tools[block['name']]+=1
            if block['name']!='exec':assert block['name']in('read','ls');continue
            args=block['arguments'];assert set(args)=={'command'}and isinstance(args['command'],str);command=args['command']
            # These are the only observed redirects. Removing stderr to stdout
            # or /dev/null cannot hide a generated file. All other redirection
            # operators, substitutions and mutating find predicates are rejected.
            normalized=re.sub(r'\b2\s*>\s*&\s*1|\b2\s*>\s*/dev/null','',command)
            lexer=shlex.shlex(normalized,posix=True,punctuation_chars=';&|<>');lexer.whitespace_split=True;lexer.commenters='';tokens=list(lexer)
            assert '$('not in normalized and '`'not in normalized
            assert not any(t in('>','>>','<<','<','-exec','-execdir','-delete','-fprint','-fprint0','-fprintf')for t in tokens)
            first=True;seen=[]
            for t in tokens:
                if t in(';','&&','||','|','&'):first=True
                elif first:assert t in('cat','head','echo','find','ls'),(d['provenance']['target_id'],t);programs[t]+=1;seen.append(t);first=False
            record={'target_id':d['provenance']['target_id'],'episode_id':d['provenance']['episode_id'],'actual_native_event_line':d['provenance']['source_event_line'],'actual_original_command':command,'utf8_sha256':hashlib.sha256(command.encode()).hexdigest(),'subcommands':seen,'source_scope_status':d['provenance']['scope_status'],'visible_source_ids_current_TRAIN':d['provenance']['source_ids_visible_prefix'],'closed_readonly_shell_grammar':True,'no_substitution_or_file_output_redirect_or_mutating_find':True}
            commands.append(record)
    assert len(commands)==220 and empty==57 and native_equal==405
    with gzip.open(OUT/'ACTUAL_EXEC_COMMANDS_220.jsonl.gz','wt',encoding='utf-8',newline='\n')as f:
        for row in commands:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    unique={r['actual_original_command']for r in commands}
    value={'schema':'wrd-clean-maker405-byte-and-command-grammar-independent-followup-v1','status':'PASS_BOUNDED_NO_PROGRAM_GENERATION_IN_THESE405_TARGETS','allowed_targets':405,'canonical_original_native_content_exact':native_equal,'empty_assistant_positions':empty,'tool_calls':dict(tools),'content_blocks':dict(blocks),'exec_commands_fully_classified':len(commands),'unique_exact_exec_commands':len(unique),'total_exec_command_characters':sum(len(x['actual_original_command'])for x in commands),'shell_subcommand_counts':dict(programs),'visible_text_blocks':len(texts),'visible_text_characters':sum(map(len,texts)),'visible_code_fences_or_program_declarations':0,'direct_native_write_edit_patch_calls':0,'complete_program_creation_or_modification_found':0,'all_commands_only_cat_head_echo_find_ls':True,'only_readonly_stderr_redirections_allowed':True,'python_shell_substitution_or_mutating_find_count':0,'raw_command_payloads':{'path':'ACTUAL_EXEC_COMMANDS_220.jsonl.gz','sha256':digest(OUT/'ACTUAL_EXEC_COMMANDS_220.jsonl.gz')},'finding_scope':'Exactly405 source-admissible early maker prefixes. No conclusion about later protected messages, whole native episodes, other sources or all29skills. File-writeproof absence alone was NOT used to reach this byte-level conclusion.','native_tool_results_not_read_or_assumed_successful':True,'protected_native_message_bodies_decoded':0,'positive_training_targets_created':0,'new_Agent_calls':0,'training_started':False,'ACTIVE_modified':False,'script_sha256':digest(Path(__file__))}
    path=OUT/'COMMAND_GRAMMAR_QA.json';path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(value,ensure_ascii=False))
if __name__=='__main__':main()
