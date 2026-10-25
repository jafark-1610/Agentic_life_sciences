"""Trusted verifier: real offline namespace, artifact coverage, and scientific replay.

Linux bubblewrap is a verifier dependency, not an oracle Python dependency.
No user namespace capability means BLOCKED, never a solver failure.
"""
import argparse,json,os,shutil,subprocess,sys,tempfile,time,hashlib,ast,platform,importlib.metadata
from pathlib import Path
from score_rubric import evaluate,strict_read
from regenerated_data import regenerate,truth_answer
HERE=Path(__file__).resolve().parent

def command(stage,argv):
 prefix=Path(sys.prefix).resolve();cmd=['bwrap','--die-with-parent','--unshare-all','--new-session','--clearenv']
 for path in ['/usr','/lib','/lib64',str(prefix)]:
  if Path(path).exists():cmd+=['--ro-bind',path,path]
 if Path('/etc/ld.so.cache').exists():cmd+=['--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache']
 cmd+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(stage/'task'),'/task','--bind',str(stage/'solver'),'/solver','--bind',str(stage/'results'),'/results','--chdir','/solver']
 for k,v in {'PATH':str(prefix/'bin')+':/usr/bin','HOME':'/tmp','TMPDIR':'/tmp','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}.items():cmd+=['--setenv',k,v]
 return cmd+[sys.executable]+argv

def stage_solver(solver,stage,data):
 shutil.copytree(HERE.parent/'task',stage/'task',ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.rmtree(stage/'task/data');shutil.copytree(data,stage/'task/data');(stage/'results').mkdir()
 for p in Path(solver).rglob('*'):
  if p.is_symlink():raise ValueError('solver symlinks are not accepted for isolation staging')
 if Path(solver).resolve()==HERE.resolve():
  # The positive control stages only its computational submission, never evaluator assets.
  (stage/'solver').mkdir()
  for name in ['run_pipeline.py','expert_solution.py','mechanism.py','artifacts.py','requirements.txt']:shutil.copy2(HERE/name,stage/'solver'/name)
  shutil.copytree(HERE/'config',stage/'solver/config')
 else:
  shutil.copytree(solver,stage/'solver',ignore=shutil.ignore_patterns('results','__pycache__','*.pyc','.git'))

def requirement_error(solver):
 try:
  req=(Path(solver)/'requirements.txt').read_text().lower();need=set()
  for p in Path(solver).rglob('*.py'):
   for node in ast.walk(ast.parse(p.read_text())):
    names=[node.module] if isinstance(node,ast.ImportFrom) else [n.name for n in node.names] if isinstance(node,ast.Import) else []
    for name in names:
     if name and name.split('.')[0] in ['numpy','scipy','jsonschema']:need.add(name.split('.')[0])
  return sorted(p for p in need if p not in req)
 except (OSError,SyntaxError):return ['requirements declaration missing or source invalid']

def run(solver,data,out,seed=49173,timeout=900,replay_control=False):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);data=Path(data).resolve();solver=Path(solver).resolve();truth=strict_read(HERE/'private/generation_truth.json');base_ref=strict_read(HERE/'final_answer.json')
 result={'role':'full_submission_verification','case_id':base_ref['case_id'],'seed':seed,'runtime':{'python':platform.python_version(),'dependencies':{n:importlib.metadata.version(n) for n in ['numpy','scipy','jsonschema']}},'status':'blocked','isolation':{},'runs':[],'passed':False}
 if not shutil.which('bwrap'):
  result['blocker']='bubblewrap executable unavailable';return save(out,result)
 with tempfile.TemporaryDirectory(prefix='tmdd-verifier-') as tmp:
  work=Path(tmp);base=work/'base';base.mkdir();stage_solver(solver,base,data)
  canary=work/'private_canary.txt';canary.write_text('private grading canary: never mounted')
  probe="""import os,socket,json,pathlib
paths=__PATHS__
denied=[]
for p in paths:
 try:pathlib.Path(p).read_bytes();denied.append(False)
 except OSError:denied.append(True)
readonly=False
try:pathlib.Path('/task/data/forbidden_write').write_text('bad')
except OSError:readonly=True
s=socket.socket();s.settimeout(.5)
try:s.connect(('1.1.1.1',443));offline=False
except OSError:offline=True
print(json.dumps({'uid':os.getuid(),'private_paths_denied':all(denied),'task_readable':pathlib.Path('/task/data/model_spec.json').is_file(),'task_read_only':readonly,'network_connection_blocked':offline}))
""".replace('__PATHS__',repr([str(canary),str(HERE/'final_answer.json'),str(HERE/'private/generation_truth.json')]))
  (base/'solver/isolation_probe.py').write_text(probe)
  probe_run=subprocess.run(command(base,['isolation_probe.py']),capture_output=True,text=True,timeout=15)
  if probe_run.returncode:
   result['blocker']='namespace setup unavailable: '+probe_run.stderr.strip();return save(out,result)
  isolation=json.loads(probe_run.stdout);result['isolation']=dict(isolation,mounts={'/task':'read-only task data only','/solver':'submitted source/config only, writable','/results':'writable fresh output','/tmp':'fresh tmpfs','runtime':'read-only Python prefix and system libraries','network':'separate namespace, no external interface'},command='python /solver/run_pipeline.py --data /task/data --output-dir /results')
  if not all(isolation[k] for k in ['private_paths_denied','task_readable','task_read_only','network_connection_blocked']):result['blocker']='isolation probe failed';return save(out,result)
  mutant=work/'regenerated_data';newtruth=regenerate(data,mutant,truth,seed);expected=truth_answer(mutant,newtruth)
  for name,source,reference in [('base',data,base_ref),('regenerated',mutant,expected)]:
   stage=work/name
   if name!='base':stage.mkdir();stage_solver(solver,stage,source)
   started=time.monotonic()
   try:proc=subprocess.run(command(stage,['run_pipeline.py','--data','/task/data','--output-dir','/results']),capture_output=True,text=True,timeout=timeout);status=proc.returncode;log=proc.stdout+proc.stderr
   except subprocess.TimeoutExpired:status=124;log='execution timeout'
   grade=evaluate(stage/'results/final_answer.json',source,stage/'results',reference) if status==0 else {'final_score':0,'passed':False,'automatic_zero':'pipeline failed or timed out'}
   req=requirement_error(stage/'solver');delivery=grade.get('delivery',{});extra=min(2*bool(req),max(0,10-delivery.get('deduction',0)));grade['requirements_errors']=req;grade['final_score']=max(0,grade['final_score']-extra);grade['passed']=grade['final_score']>=80
   result['runs'].append({'dataset':name,'exit_code':status,'elapsed_seconds':round(time.monotonic()-started,3),'grade':grade,'output_files':sorted(p.name for p in (stage/'results').iterdir() if p.is_file()),'stdout_stderr':log[-4000:]})
  result['status']='success' if all(r['grade']['passed'] and r['exit_code']==0 for r in result['runs']) else 'fail';result['passed']=result['status']=='success';result['final_score']=min(r['grade']['final_score'] for r in result['runs'])
  if not result['passed']:result['final_score']=min(result['final_score'],79)
  if replay_control:
   # Run a stored-answer pipeline inside the same isolated runtime; refresh hashes honestly.
   frozen=work/'replay_source';frozen.mkdir()
   for name in ['artifacts.py','expert_solution.py','mechanism.py','requirements.txt']:shutil.copy2(HERE/name,frozen/name)
   (frozen/'frozen_answer.json').write_text(json.dumps(base_ref))
   replay_code="import argparse,json\nfrom pathlib import Path\nfrom artifacts import write_outputs\nfrom expert_solution import load\np=argparse.ArgumentParser();p.add_argument('--data');p.add_argument('--output-dir');a=p.parse_args()\nanswer=json.loads(Path('frozen_answer.json').read_text());write_outputs(answer,load(a.data),a.data,a.output_dir,0.)\n"
   (frozen/'run_pipeline.py').write_text(replay_code)
   controls=[]
   for name,source,reference in [('base',data,base_ref),('regenerated',mutant,expected)]:
    stage=work/('replay_'+name);stage.mkdir();stage_solver(frozen,stage,source)
    proc=subprocess.run(command(stage,['run_pipeline.py','--data','/task/data','--output-dir','/results']),capture_output=True,text=True,timeout=30)
    bad=evaluate(stage/'results/final_answer.json',source,stage/'results',reference) if proc.returncode==0 else {'passed':False,'final_score':0,'error':'replay pipeline failed'}
    controls.append({'dataset':name,'exit_code':proc.returncode,'grade':bad})
   rejected=controls[0]['exit_code']==0 and controls[0]['grade']['passed'] and controls[1]['exit_code']==0 and not controls[1]['grade']['passed']
   result['stored_answer_replay_control']={'runs':controls,'rejected':rejected,'hashes_refreshed':True,'isolated_execution':True}
   if not rejected:result['passed']=False;result['status']='fail'

 return save(out,result)

def save(out,result):
 (Path(out)/'verification_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'status':result['status'],'passed':result['passed'],'runs':[(r['dataset'],r['grade']['final_score']) for r in result['runs']],'blocker':result.get('blocker')},indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--solver',required=True,type=Path);p.add_argument('--data',type=Path,default=HERE.parent/'task/data');p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--seed',type=int,default=49173);p.add_argument('--timeout',type=int,default=900);p.add_argument('--replay-control',action='store_true');a=p.parse_args();r=run(a.solver,a.data,a.output_dir,a.seed,a.timeout,a.replay_control);sys.exit(0 if r['passed'] else 2 if r['status']=='blocked' else 1)
