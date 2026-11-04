"""Bounded synthetic negative tests for the trusted public archive tools.

All fixture bodies are newly authored harmless bytes under delivery/test roots.
No full archive build, real restore, credential config, model or native call.
"""
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
import ast,gzip,hashlib,importlib.util,io,json,os,subprocess,sys,tarfile
sys.dont_write_bytecode=True
ROOT=Path('D:/skillloop');WORK=ROOT/'output/20261031_wrd_curation11';OUT=WORK/'package_review'
TEST=ROOT/'output/20261031_wrd_curation11_delivery/package_negative_tests01'
PACKAGE=ROOT/'research/data_prep/wrd_curation11/package_curriculum11.py'
RESTORE=ROOT/'research/data_prep/wrd_curation11/restore_package11.py'
SCAN=ROOT/'research/data_prep/wrd_curation10/package10.py'
def hs(b):return hashlib.sha256(b).hexdigest()
def pin(p):p=Path(p);return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hs(p.read_bytes())}
def mod(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 output=OUT/'PACKAGE_CODE_QA11.json';assert not output.exists()and not TEST.exists()
 TEST.mkdir(parents=True);before={str(p):pin(p)for p in [PACKAGE,RESTORE,SCAN]}
 pack=mod('trusted_package11_for_unit_review',PACKAGE);restore=mod('trusted_restore11_for_unit_review',RESTORE);scan=mod('trusted_scan10_for_unit_review',SCAN)
 tests=[]
 def positive(label,fn):
  value=fn();tests.append({'test':label,'expected':'PASS','actual':'PASS'});return value
 def negative(label,fn):
  try:fn()
  except (AssertionError,ValueError,TypeError,OSError,tarfile.TarError)as e:
   tests.append({'test':label,'expected':'REJECT','actual':'REJECT','error_type':type(e).__name__});return
  raise AssertionError('NEGATIVE_NOT_REJECTED:'+label)
 # Exact path validation is independent of a real package.
 for name in ['one.txt','nested/one.txt','source/transparent.py']:
  positive('safe_'+name,lambda n=name:restore.safe(TEST/'path_root',n))
 for i,name in enumerate(['../escape','/absolute','C:/drive','a\\b','one.txt:alternate','a//b','./a','a/../b','CON','con.txt','com1.txt','LPT9.bin','trailing.','trailing ','a/dir./x','a?b','a*b','a<b','a>b','a"b','a|b','a\tb','a\x00b','a\x7fb','a\nb']):
  negative('unsafe_path_'+str(i),lambda n=name:restore.safe(TEST/'path_root',n))
 # Restore only a tiny, public synthetic archive. Its Python member is inert.
 def archive(label,refs,members,*,first=True,manifest_raw=None,schema='wrd11-public-curriculum-and-audit-v1'):
  if manifest_raw is None:manifest_raw=(json.dumps({'schema':schema,'files':refs},ensure_ascii=False,indent=2)+'\n').encode()
  p=TEST/(label+'.tar.gz')
  with tarfile.open(p,'w:gz',format=tarfile.PAX_FORMAT)as tf:
   def add(name,body=b'',kind=tarfile.REGTYPE):
    inf=tarfile.TarInfo(name);inf.type=kind;inf.size=len(body)if kind==tarfile.REGTYPE else 0;inf.mode=0o644
    if kind in {tarfile.SYMTYPE,tarfile.LNKTYPE}:inf.linkname='../synthetic_outside'
    tf.addfile(inf,io.BytesIO(body)if kind==tarfile.REGTYPE else None)
   if first:add('PAYLOAD_MANIFEST11.json',manifest_raw)
   for member in members:add(*member)
   if not first:add('PAYLOAD_MANIFEST11.json',manifest_raw)
  return p,hs(p.read_bytes()),hs(manifest_raw)
 def ref(name,b):return {'path':name,'bytes':len(b),'sha256':hs(b),'category':'PURE_SYNTHETIC_UNIT_FIXTURE'}
 plain=b'Only newly authored harmless synthetic content.\n';inert=b'raise RuntimeError("SAVED_SOURCE_MUST_NEVER_EXECUTE")\n'
 valid=archive('valid',[ref('nested/one.txt',plain),ref('source/inert.py',inert)],[('nested/one.txt',plain),('source/inert.py',inert)])
 validroot=TEST/'valid_output';receipt=positive('tiny_archive_roundtrip_no_source_execution',lambda:restore.restore(*valid,validroot))
 assert (validroot/'nested/one.txt').read_bytes()==plain and (validroot/'source/inert.py').read_bytes()==inert
 assert receipt['files_verified']==2 and receipt['payload_source_executed']is False
 negative('new_output_required',lambda:restore.restore(*valid,validroot))
 negative('archive_SHA_wrong',lambda:restore.restore(valid[0],'0'*64,valid[2],TEST/'bad_archive_sha'))
 negative('manifest_SHA_wrong',lambda:restore.restore(valid[0],valid[1],'0'*64,TEST/'bad_manifest_sha'))
 variants=[]
 variants.append(('manifest_not_first',archive('manifest_not_first',[ref('one.txt',plain)],[('one.txt',plain)],first=False)))
 variants.append(('manifest_schema_wrong',archive('schema_wrong',[],[],schema='wrong')))
 dupe=b'{"schema":"wrd11-public-curriculum-and-audit-v1","schema":"wrd11-public-curriculum-and-audit-v1","files":[]}'
 variants.append(('duplicate_manifest_JSON_key',archive('duplicate_json',[],[],manifest_raw=dupe)))
 variants.append(('casefold_reference_alias',archive('casefold_alias',[ref('Case.txt',plain),ref('case.txt',plain)],[('Case.txt',plain),('case.txt',plain)])))
 variants.append(('duplicate_exact_reference',archive('dupe_ref',[ref('one.txt',plain),ref('one.txt',plain)],[('one.txt',plain)])))
 for idx,name in enumerate(['PAYLOAD_MANIFEST11.json','payload_manifest11.json','RESTORE_RECEIPT11.json','restore_receipt11.json']):
  variants.append(('generated_name_reserved_'+str(idx),archive('reserved_'+str(idx),[ref(name,plain)],[(name,plain)])))
 variants.append(('unlisted_member',archive('unlisted',[],[('one.txt',plain)])))
 variants.append(('missing_member',archive('missing',[ref('one.txt',plain)],[])))
 variants.append(('duplicate_member',archive('duplicate_member',[ref('one.txt',plain)],[('one.txt',plain),('one.txt',plain)])))
 badsize=ref('one.txt',plain);badsize['bytes']+=1
 variants.append(('member_size_wrong',archive('wrong_size',[badsize],[('one.txt',plain)])))
 badsha=ref('one.txt',plain);badsha['sha256']='0'*64
 variants.append(('member_body_SHA_wrong',archive('wrong_sha',[badsha],[('one.txt',plain)])))
 for label,kind in [('symbolic_link',tarfile.SYMTYPE),('hard_link',tarfile.LNKTYPE),('directory',tarfile.DIRTYPE),('fifo',tarfile.FIFOTYPE)]:
  variants.append(('reject_'+label,archive('member_'+label,[ref('one.txt',b'')],[('one.txt',b'',kind)])))
 for label,triple in variants:negative(label,lambda x=triple,l=label:restore.restore(*x,TEST/('out_'+l)))
 # Test the actual nested add() body in isolated globals. main() never runs.
 tree=ast.parse(PACKAGE.read_text(encoding='utf-8-sig'));mainfn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main')
 addfn=next(n for n in mainfn.body if isinstance(n,ast.FunctionDef)and n.name=='add')
 root=TEST/'source_scope';root.mkdir();a=root/'one.txt';b=root/'two.txt';a.write_bytes(b'AAAA');b.write_bytes(b'BBBB')
 def add_context(scanner):
  ns=dict(pack.__dict__);ns.update(entries={},folded=set(),aliases=[],scans=Counter(),needles=(),pkg=SimpleNamespace(scan_file=scanner),validator=restore,DEL=TEST/'nominal_delivery')
  exec(compile(ast.Module(body=[addfn],type_ignores=[]),str(PACKAGE),'exec'),ns);return ns
  # The entire real package, business records and private credential config are
  # not accessed by these synthetic calls.
 c=add_context(scan.scan_file);positive('pack_regular_scoped_source',lambda:c['add']('one.txt',a,'QA',root))
 negative('pack_casefold_alias',lambda:c['add']('ONE.TXT',b,'QA',root))
 for n in ['payload_manifest11.json','RESTORE_RECEIPT11.JSON']:
  cc=add_context(scan.scan_file);negative('pack_reserved_'+n,lambda nn=n,ctx=cc:ctx['add'](nn,a,'QA',root))
 negative('source_lexical_scope_escape',lambda:pack.original_guard(b,root/'nested'))
 negative('source_declared_scope_above_workspace',lambda:pack.original_guard(a,Path('D:/')))
 def mutate_after_scan(path,needles):
  # Ordinary A/B byte mutation suffices; no credential-shaped value is needed.
  result=scan.scan_file(path,needles);Path(path).write_bytes(b'CCCC');return result
 c=add_context(mutate_after_scan);negative('scan_to_pin_same_length_mutation',lambda:c['add']('mutated.txt',a,'QA',root));assert not c['entries']
 a.write_bytes(b'AAAA')
 # The inherited scanner is exercised with a harmless exact-match needle.
 needle=b'SYNTHETIC_EXACT_SCAN_NEEDLE_ONLY';clean=TEST/'clean.txt';clean.write_bytes(plain)
 cleanzip=TEST/'clean.txt.gz';cleanzip.write_bytes(gzip.compress(plain))
 dirty=TEST/'ordinary_scan_probe.txt';dirty.write_bytes(b'A'*(1048576-5)+needle+b'B')
 dirtyzip=TEST/'ordinary_scan_probe.txt.gz';dirtyzip.write_bytes(gzip.compress(plain+needle))
 positive('scanner_clean_raw',lambda:scan.scan_file(clean,(needle,)))
 positive('scanner_clean_gzip',lambda:scan.scan_file(cleanzip,(needle,)))
 negative('scanner_exact_needle_across_raw_chunk_boundary',lambda:scan.scan_file(dirty,(needle,)))
 negative('scanner_exact_needle_in_gzip_decoded_body',lambda:scan.scan_file(dirtyzip,(needle,)))
 # Real NTFS junction fixture, entirely under the new synthetic test root.
 # Remove only this exact link; never recurse or remove its real target.
 outside=TEST/'outside_scope';outside.mkdir();target=outside/'target.txt';target.write_bytes(b'Harmless out-of-scope synthetic fixture.\n')
 link=root/'scoped_junction';target_before=pin(target);link_test={'status':'NOT_RUN'}
 command="New-Item -ItemType Junction -Path '"+str(link).replace("'","''")+"' -Target '"+str(outside).replace("'","''")+"' -ErrorAction Stop | Out-Null"
 result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
 if result.returncode==0:
  try:
   assert link.absolute().is_relative_to(TEST.absolute())and link.lstat().st_file_attributes&0x400
   negative('original_source_junction_rejected_before_resolve',lambda:pack.original_guard(link/'target.txt',root))
   link_test={'status':'PASS_REAL_NTFS_JUNCTION_REJECTED','exact_link_path':str(link),'target_was_only_synthetic':True}
  finally:
   assert link.absolute().is_relative_to(TEST.absolute())and link.lstat().st_file_attributes&0x400
   os.rmdir(link)
  assert not link.exists()and pin(target)==target_before
  link_test['exact_link_removed_target_unchanged']=True
 else:
  raise AssertionError('NTFS_JUNCTION_FIXTURE_CREATION_FAILED_NO_REPARSE_TEST_CLAIM')
 # No source reparse link is left in either public WORK or test roots.
 reparses=[]
 for base in [WORK,TEST]:
  for p in base.rglob('*'):
   if p.lstat().st_file_attributes&0x400:reparses.append(str(p))
 assert not reparses
 for p,ref in before.items():assert pin(p)==ref,'TRUSTED_TOOL_CHANGED_DURING_CODE_REVIEW'
 report={'schema':'wrd11-public-package-finite-code-review','status':'PASS_CURRENT_PACKAGE_AND_RESTORE_CODE_FINITE_NEGATIVES_PENDING_REAL_ARCHIVE',
  'source_pins':before,'review_script_pin':pin(__file__),'tests':tests,'test_count':len(tests),
  'rejected_negative_count':sum(x['actual']=='REJECT'for x in tests),'positive_count':sum(x['actual']=='PASS'for x in tests),
  'pre_review_findings_fixed':['Original lexical source/reparse check before resolve and declared-source scope bound.','Source size/SHA before and after raw/gzip scan, with scope recheck.','Casefold archive aliases and both generated root names reserved in pack and restore.','Windows invalid/control path characters explicitly rejected.'],
  'synthetic_junction':link_test,'fixture_location_outside_public_WORK':str(TEST),
  'fixture_bodies':'Only freshly authored ordinary A/B/text and inert Python bytes; harmless exact scan probe; no real enterprise body, real credential, key or model file.',
  'WORK_and_test_roots_reparse_inventory_after_cleanup':reparses,
  'package_scope_static_review':'Only current authored WORK, current research tooling/plans/design snapshots and tokenizer JSON/Jinja/text assets; original205 pool is referenced by metadata, not copied by these trees. Credential config is consulted by the real packager only to obtain comparison needles, never added as a source.',
  'scanner_has_no_url_or_other_exception_argument_in_package_call':True,
  'first_tar_member_manifest_explicit_refs_casefold_paths_regular_members_and_SHA_checked':True,
  'package_full_archive_build_performed_by_this_review':False,'actual_wrd11_public_root_restore_performed':False,
  'tiny_synthetic_restore_scope_only':True,'saved_payload_source_executed':False,
  'remaining_required':['Actual archive build and complete credential scan.','Real new-root restore and all declared source SHA checks.','Both profiles1254 physical views/3762 binaries and existing205 pool four-feature verification.','Actual Git/LFS upload and remote entity verification.'],
  'native_calls':0,'model_or_training':False}
 OUT.mkdir(parents=True,exist_ok=True);output.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({'status':report['status'],'tests':len(tests),'negative_rejections':report['rejected_negative_count'],'QA_sha256':pin(output)['sha256']}))
if __name__=='__main__':main()
