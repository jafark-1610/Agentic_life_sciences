"""Run one submitted source file with public data only and a new calibrated experiment."""
import os
import sys
sys.dont_write_bytecode=True
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from score_rubric import evaluate
HERE=Path(__file__).resolve().parent


def command(stage,args):
    prefix=Path(sys.prefix).resolve();cmd=['bwrap','--die-with-parent','--unshare-all','--new-session','--clearenv']
    for path in ['/usr','/lib','/lib64',str(prefix)]:
        if Path(path).exists():cmd+=['--ro-bind',path,path]
    if Path('/etc/ld.so.cache').exists():cmd+=['--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache']
    cmd+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(stage/'task'),'/task',
          '--bind',str(stage/'solver'),'/solver','--bind',str(stage/'results'),'/results','--chdir','/solver']
    for k,v in {'PATH':str(prefix/'bin')+':/usr/bin','HOME':'/tmp','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}.items():cmd+=['--setenv',k,v]
    return cmd+[sys.executable]+args


def stage(path,solver,task):
    path.mkdir();shutil.copytree(task,path/'task');(path/'solver').mkdir();(path/'results').mkdir()
    assert not (solver/'run_pipeline.py').is_symlink()
    shutil.copy2(solver/'run_pipeline.py',path/'solver/run_pipeline.py')


def verify(solver,out,timeout=600,replay_control=False):
    solver,out=Path(solver).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    result=dict(case_id='ALS_RNA_TRANSPORT_006',role='isolated_source_verification',status='blocked',passed=False,
                required_deliverables=['run_pipeline.py','final_answer.json','analysis.md'],
                runtime={'python':platform.python_version(),'dependencies':{p:importlib.metadata.version(p) for p in ['numpy','scipy','jsonschema']}},runs=[])
    def save():
        (out/'verification_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k in ['status','passed','blocker','final_score']}));return result
    if not shutil.which('bwrap'):result['blocker']='bubblewrap unavailable';return save()
    if not (solver/'run_pipeline.py').is_file():result.update(status='fail',final_score=0,blocker='missing pipeline');return save()
    with tempfile.TemporaryDirectory(prefix='cycle-isolated-') as tmp:
        work=Path(tmp);base=work/'base';stage(base,solver,HERE.parent/'task')
        canary=work/'private_canary';canary.write_text('unmounted')
        private=[str(canary),str(HERE/'private/truth.npz'),str(HERE/'private/expected_answer.json'),str(HERE/'final_answer.json')]
        probe="import pathlib,json,socket\nblocked=[]\nfor p in "+repr(private)+":\n try:pathlib.Path(p).read_bytes();blocked.append(False)\n except OSError:blocked.append(True)\nro=False\ntry:pathlib.Path('/task/data/forbidden').write_text('x')\nexcept OSError:ro=True\ns=socket.socket();s.settimeout(.5)\ntry:s.connect(('1.1.1.1',443));offline=False\nexcept OSError:offline=True\nprint(json.dumps({'private_reads_denied':all(blocked),'task_read_only':ro,'network_blocked':offline,'task_readable':pathlib.Path('/task/prompt.md').is_file()}))\n"
        (base/'solver/probe.py').write_text(probe);p=subprocess.run(command(base,['probe.py']),capture_output=True,text=True,timeout=20)
        if p.returncode:result['blocker']='namespace unavailable: '+p.stderr.strip();return save()
        result['isolation']=json.loads(p.stdout)
        if not all(result['isolation'].values()):result['blocker']='isolation probe failed';return save()
        result['mounts']={'/task':'read-only public inputs','/solver':'one submitted source file','/results':'writable output','private':'unmounted','network':'isolated namespace'}
        sys.path.insert(0,str(HERE/'source_archive'));from generate_data import generate
        mutant=work/'new_experiment';shutil.copytree(HERE.parent/'task',mutant/'task');generate(mutant,seed=48032)
        truth=None;expected_path=work/'new_expected.json'
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        trusted=subprocess.Popen([sys.executable,str(HERE/'compute_expected.py'),'--data',str(mutant/'task/data'),'--output',str(expected_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
        expected_mutant=None
        for name,task in [('base',HERE.parent/'task'),('regenerated',mutant/'task')]:
            path=base if name=='base' else work/'regenerated'
            if name!='base':
                stdout,stderr=trusted.communicate(timeout=timeout)
                if trusted.returncode:result['blocker']='trusted target regeneration failed: '+stderr[-2000:];return save()
                expected_mutant=json.loads(expected_path.read_text());stage(path,solver,task)
            started=time.monotonic()
            try:
                p=subprocess.run(command(path,['run_pipeline.py','--data','/task/data','--output-dir','/results']),capture_output=True,text=True,timeout=timeout)
                code,log=p.returncode,p.stdout+p.stderr
            except subprocess.TimeoutExpired:code,log=124,'execution timeout'
            grade=evaluate(path/'results/final_answer.json',task/'data',path/'results/analysis.md',expected=expected_mutant if name=='regenerated' else None,truth=truth if name=='regenerated' else None) if code==0 else {'final_score':0,'passed':False,'automatic_zero':'pipeline failed or timed out'}
            result['runs'].append(dict(dataset=name,exit_code=code,seconds=round(time.monotonic()-started,3),grade=grade,
              source_sha256=hashlib.sha256((path/'solver/run_pipeline.py').read_bytes()).hexdigest(),
              data_manifest_sha256=hashlib.sha256((task/'data/data_manifest.json').read_bytes()).hexdigest(),
              outputs=sorted(p.name for p in (path/'results').iterdir()),log=log[-2000:]))
        result['passed']=all(r['exit_code']==0 and r['grade']['passed'] for r in result['runs'])
        result['status']='success' if result['passed'] else 'fail';result['final_score']=min(r['grade']['final_score'] for r in result['runs'])
        if not result['passed']:result['final_score']=min(79,result['final_score'])
        if replay_control:
            saved=work/'saved';saved.mkdir();answer=(base/'results/final_answer.json').read_text();report=(base/'results/analysis.md').read_text()
            (saved/'run_pipeline.py').write_text('import argparse\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument("--data");p.add_argument("--output-dir");a=p.parse_args();o=Path(a.output_dir);o.mkdir(exist_ok=True)\n(o/"final_answer.json").write_text('+repr(answer)+')\n(o/"analysis.md").write_text('+repr(report)+')\n')
            controls=[]
            for name,task in [('base',HERE.parent/'task'),('regenerated',mutant/'task')]:
                path=work/('saved_'+name);stage(path,saved,task);p=subprocess.run(command(path,['run_pipeline.py','--data','/task/data','--output-dir','/results']),capture_output=True,text=True,timeout=30)
                grade=evaluate(path/'results/final_answer.json',task/'data',path/'results/analysis.md',expected=expected_mutant if name=='regenerated' else None,truth=truth if name=='regenerated' else None) if p.returncode==0 else dict(final_score=0,passed=False)
                controls.append(dict(dataset=name,exit_code=p.returncode,score=grade['final_score'],passed=grade['passed']))
            result['stored_answer_control']=dict(runs=controls,rejected=controls[0]['passed'] and not controls[1]['passed'] and all(c['exit_code']==0 for c in controls))
            if not result['stored_answer_control']['rejected']:result.update(status='fail',passed=False)
    return save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--solver',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--timeout',type=int,default=600);p.add_argument('--replay-control',action='store_true');a=p.parse_args()
    r=verify(a.solver,a.output_dir,a.timeout,a.replay_control);sys.exit(0 if r['passed'] else 2 if r['status']=='blocked' else 1)
