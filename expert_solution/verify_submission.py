"""Full isolated submitted-code evaluation and physically consistent replay."""
import argparse,json,os,sys,tempfile,subprocess,shutil,time,hashlib,platform,importlib.metadata
from pathlib import Path
import numpy as np
from score_rubric import evaluate,strict_read
HERE=Path(__file__).resolve().parent

def command(stage,args):
 prefix=Path(sys.prefix).resolve();cmd=['bwrap','--die-with-parent','--unshare-all','--new-session','--clearenv']
 for path in ['/usr','/lib','/lib64',str(prefix)]:
  if Path(path).exists():cmd+=['--ro-bind',path,path]
 if Path('/etc/ld.so.cache').exists():cmd+=['--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache']
 cmd+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(stage/'task'),'/task','--bind',str(stage/'solver'),'/solver','--bind',str(stage/'results'),'/results','--chdir','/solver']
 for k,v in {'PATH':str(prefix/'bin')+':/usr/bin','HOME':'/tmp','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}.items():cmd+=['--setenv',k,v]
 return cmd+[sys.executable]+args

def stage_source(solver,data,stage):
 for p in Path(solver).rglob('*'):
  if p.is_symlink():raise ValueError('Submission symlinks unsupported')
 shutil.copytree(HERE.parent/'task',stage/'task',ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.rmtree(stage/'task/data');shutil.copytree(data,stage/'task/data');(stage/'results').mkdir()
 if Path(solver).resolve()==HERE.resolve():
  (stage/'solver').mkdir()
  for f in ['run_pipeline.py','expert_solution.py','causal_model.py','artifacts.py']:shutil.copy2(HERE/f,stage/'solver'/f)
  shutil.copytree(HERE/'config',stage/'solver/config')
 else:shutil.copytree(solver,stage/'solver',ignore=shutil.ignore_patterns('.git','results','__pycache__','*.pyc'))

def regenerate(data,dst,seed):
 sys.path.insert(0,str(HERE/'source_archive'));from generate_data import write_tables,update_manifest
 shutil.copytree(data,dst);contexts=strict_read(dst/'contexts.json');truth=strict_read(HERE/'private/generation_laws.json');rng=np.random.default_rng(seed)
 for c in contexts:
  law=np.array(truth[c['id']]).reshape(2,-1)*rng.lognormal(0,.5,(2,len(truth[c['id']])//2));law/=law.sum(axis=1)[:,None];truth[c['id']]=law.ravel().tolist()
  c['target_x1']=float(np.clip(c['target_x1']+rng.uniform(-.04,.04),.2,.8))
 (dst/'contexts.json').write_text(json.dumps(contexts,indent=2)+'\n');write_tables(dst,contexts,truth);update_manifest(dst)

def verify(solver,data,out,seed=92031,timeout=1200,replay=False):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);solver=Path(solver).resolve();data=Path(data).resolve()
 result={'role':'full_submission_verification','status':'blocked','passed':False,'seed':seed,'required_deliverables':['run_pipeline.py','final_answer.json','analysis.md'],'runtime':{'python':platform.python_version(),'dependencies':{p:importlib.metadata.version(p) for p in ['numpy','scipy','jsonschema']}},'runs':[]}
 def save():
  (out/'verification_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'status':result['status'],'passed':result['passed'],'runs':[(r['dataset'],r['grade']['final_score']) for r in result['runs']],'blocker':result.get('blocker')},indent=2));return result
 if not shutil.which('bwrap'):result['blocker']='bubblewrap unavailable';return save()
 with tempfile.TemporaryDirectory(prefix='paired-causal-verifier-') as tmp:
  work=Path(tmp);base=work/'base';base.mkdir();stage_source(solver,data,base);canary=work/'private_canary';canary.write_text('unmounted grading canary')
  paths=[str(canary),str(HERE/'final_answer.json'),str(HERE/'private/generation_laws.json')]
  probe="import pathlib,json,os,socket\nblocked=[]\nfor p in "+repr(paths)+":\n try:pathlib.Path(p).read_bytes();blocked.append(False)\n except OSError:blocked.append(True)\nreadonly=False\ntry:pathlib.Path('/task/data/forbidden_write').write_text('x')\nexcept OSError:readonly=True\ns=socket.socket();s.settimeout(.5)\ntry:s.connect(('1.1.1.1',443));offline=False\nexcept OSError:offline=True\nprint(json.dumps({'uid':os.getuid(),'private_reads_denied':all(blocked),'task_read_only':readonly,'network_blocked':offline,'task_readable':pathlib.Path('/task/prompt.md').is_file()}))\n"
  (base/'solver/isolation_probe.py').write_text(probe);p=subprocess.run(command(base,['isolation_probe.py']),capture_output=True,text=True,timeout=20)
  if p.returncode:result['blocker']='namespace unavailable: '+p.stderr.strip();return save()
  result['isolation']=json.loads(p.stdout);result['isolation']['mounts']={'/task':'read-only public task','/solver':'submitted computational source only','/results':'writable output','/tmp':'fresh tmpfs','runtime':'read-only Python prefix and system libraries','network':'isolated namespace'}
  if not all(result['isolation'][k] for k in ['private_reads_denied','task_read_only','network_blocked','task_readable']):result['blocker']='isolation probe failed';return save()
  mutant=work/'regenerated_data';regenerate(data,mutant,seed);expected_dir=work/'trusted_expected';env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
  # Trusted expected regeneration overlaps the base runtime; both derive all bounds from tables.
  expected_process=subprocess.Popen([sys.executable,str(HERE/'run_pipeline.py'),'--data',str(mutant),'--output-dir',str(expected_dir)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
  references={'base':strict_read(HERE/'final_answer.json')}
  for name,src in [('base',data),('regenerated',mutant)]:
   if name=='regenerated':
    stdout,stderr=expected_process.communicate(timeout=timeout)
    if expected_process.returncode:result['blocker']='Trusted regenerated oracle failed: '+stderr[-2000:];return save()
    references[name]=strict_read(expected_dir/'final_answer.json');stage=work/'regenerated';stage.mkdir();stage_source(solver,src,stage)
   else:stage=base
   fingerprints={str(f.relative_to(stage/'solver')):hashlib.sha256(f.read_bytes()).hexdigest() for f in (stage/'solver').rglob('*') if f.is_file() and f.name!='isolation_probe.py'}
   start=time.monotonic()
   try:p=subprocess.run(command(stage,['run_pipeline.py','--data','/task/data','--output-dir','/results']),capture_output=True,text=True,timeout=timeout);code=p.returncode;log=p.stdout+p.stderr
   except subprocess.TimeoutExpired:code=124;log='pipeline execution timeout'
   grade=evaluate(stage/'results/final_answer.json',src,stage/'results',references[name]) if code==0 else {'final_score':0,'passed':False,'automatic_zero':'pipeline failed or timed out'}
   result['runs'].append({'dataset':name,'exit_code':code,'elapsed_seconds':round(time.monotonic()-start,3),'grade':grade,'source_sha256':fingerprints,'outputs':sorted(f.name for f in (stage/'results').iterdir() if f.is_file()),'command':'python /solver/run_pipeline.py --data /task/data --output-dir /results','stdout_stderr':log[-3000:]})
  result['passed']=all(r['exit_code']==0 and r['grade']['passed'] for r in result['runs']);result['status']='success' if result['passed'] else 'fail';result['final_score']=min(r['grade']['final_score'] for r in result['runs'])
  if not result['passed']:result['final_score']=min(79,result['final_score'])
  if replay:
   frozen=work/'replay_source';frozen.mkdir();shutil.copy2(HERE/'artifacts.py',frozen/'artifacts.py');(frozen/'frozen_answer.json').write_text(json.dumps(references['base']))
   (frozen/'run_pipeline.py').write_text("import argparse,json\nfrom pathlib import Path\nfrom artifacts import write_outputs\np=argparse.ArgumentParser();p.add_argument('--data');p.add_argument('--output-dir');a=p.parse_args()\nD={'study_metadata':json.loads((Path(a.data)/'study_metadata.json').read_text())};write_outputs(json.loads(Path('frozen_answer.json').read_text()),D,a.output_dir)\n")
   controls=[]
   for name,src in [('base',data),('regenerated',mutant)]:
    stage=work/('replay_'+name);stage.mkdir();stage_source(frozen,src,stage);p=subprocess.run(command(stage,['run_pipeline.py','--data','/task/data','--output-dir','/results']),capture_output=True,text=True,timeout=30)
    grade=evaluate(stage/'results/final_answer.json',src,stage/'results',references[name]) if p.returncode==0 else {'passed':False,'final_score':0}
    controls.append({'dataset':name,'exit_code':p.returncode,'grade':grade})
   rejected=controls[0]['grade']['passed'] and controls[0]['exit_code']==0 and not controls[1]['grade']['passed'] and controls[1]['exit_code']==0
   result['stored_answer_control']={'isolated_execution':True,'runs':controls,'rejected':rejected}
   if not rejected:result['passed']=False;result['status']='fail'
 return save()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--solver',type=Path,required=True);p.add_argument('--data',type=Path,default=HERE.parent/'task/data');p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--seed',type=int,default=92031);p.add_argument('--timeout',type=int,default=1200);p.add_argument('--replay-control',action='store_true');a=p.parse_args();r=verify(a.solver,a.data,a.output_dir,a.seed,a.timeout,a.replay_control);sys.exit(0 if r['passed'] else 2 if r['status']=='blocked' else 1)
