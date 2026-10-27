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
import numpy as np
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


def equivalent_scientific_results(a,b,key=''):
    if key=='class':return a in ['INCREASED','DECREASED','EQUIVALENT','UNRESOLVED','NOT_ESTIMABLE'] and b in ['INCREASED','DECREASED','EQUIVALENT','UNRESOLVED','NOT_ESTIMABLE']
    if isinstance(a,dict) and isinstance(b,dict):return set(a)==set(b) and all(equivalent_scientific_results(a[k],b[k],k) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(equivalent_scientific_results(x,y,key) for x,y in zip(a,b))
    if isinstance(a,(float,int)) and isinstance(b,(float,int)):
        if key in ['vehicle_rate','perturbed_rate']:return a>0 and b>0 and abs(np.log2(a/b))<=.0001
        return abs(a-b)<=.0001
    return a==b


def verify(solver,out,timeout=600,replay_control=False):
    solver,out=Path(solver).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    result=dict(case_id='ALS_RNA_TRANSPORT_006',role='isolated_source_verification',status='blocked',passed=False,
                required_deliverables=['run_pipeline.py','final_answer.json','analysis.md'],
                runtime={'python':platform.python_version(),'dependencies':{p:importlib.metadata.version(p) for p in ['numpy','scipy','jsonschema']}},runs=[])
    result['identity']={'scientific_snapshot_sha256':hashlib.sha256((HERE/'freeze_manifest.json').read_bytes()).hexdigest(),'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'grader_sha256':hashlib.sha256((HERE/'score_rubric.py').read_bytes()).hexdigest(),'configuration_sha256':hashlib.sha256((HERE/'config/parameters.yaml').read_bytes()).hexdigest(),'rubric_sha256':hashlib.sha256((HERE/'rubric.json').read_bytes()).hexdigest(),'submitted_source_sha256':hashlib.sha256((solver/'run_pipeline.py').read_bytes()).hexdigest() if (solver/'run_pipeline.py').is_file() else None,'python_executable_sha256':hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),'host_euid':os.geteuid(),'host_egid':os.getegid(),'verification_scope':'local disposable runtime; delivery-owner/L2 attestation remains external'}
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
        leak=work/'canary_source';leak.mkdir()
        leak_code="import pathlib,subprocess,json,os\npaths="+repr(private)+"\npython_denied=[];child_denied=[]\nfor p in paths:\n try:pathlib.Path(p).read_bytes();python_denied.append(False)\n except OSError:python_denied.append(True)\n child_denied.append(subprocess.run(['/usr/bin/cat',p],capture_output=True).returncode!=0)\nprint(json.dumps({'python_reads_denied':all(python_denied),'child_reads_denied':all(child_denied),'euid':os.geteuid(),'egid':os.getegid(),'groups':os.getgroups(),'mountinfo':pathlib.Path('/proc/self/mountinfo').read_text(),'user_namespace':os.readlink('/proc/self/ns/user'),'mount_namespace':os.readlink('/proc/self/ns/mnt')}))\n"
        (leak/'run_pipeline.py').write_text(leak_code);leakstage=work/'canary_runtime';stage(leakstage,leak,HERE.parent/'task')
        leakrun=subprocess.run(command(leakstage,['run_pipeline.py']),capture_output=True,text=True,timeout=30)
        if leakrun.returncode:result['blocker']='submitted-code canary failed to execute: '+leakrun.stderr[-1000:];return save()
        access=json.loads(leakrun.stdout);result['submitted_code_canary']={'source_sha256':hashlib.sha256(leak_code.encode()).hexdigest(),'exit_code':leakrun.returncode,'identity_and_permissions':access,'invocation':command(leakstage,['run_pipeline.py'])}
        if not access['python_reads_denied'] or not access['child_reads_denied']:result['blocker']='private canary was readable';return save()
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
              source_sha256=hashlib.sha256((path/'solver/run_pipeline.py').read_bytes()).hexdigest(),invocation=command(path,['run_pipeline.py','--data','/task/data','--output-dir','/results']),
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
        # Identity-matched delivered report/comment controls, using the same runtime and grader.
        delivered=[]
        original=(solver/'run_pipeline.py').read_text()
        for name,suffix,wanted in [('missing_report',"\nfrom pathlib import Path as _P\nimport sys as _S\n(_P(_S.argv[_S.argv.index('--output-dir')+1])/'analysis.md').unlink(missing_ok=True)\n",95),('harmless_comment',"\n# Documentation only: expert_solution/private is not read.\n",100)]:
            src=work/name;src.mkdir();code=original+suffix;(src/'run_pipeline.py').write_text(code);path=work/(name+'_runtime');stage(path,src,HERE.parent/'task')
            proc=subprocess.run(command(path,['run_pipeline.py','--data','/task/data','--output-dir','/results']),capture_output=True,text=True,timeout=timeout)
            grade=evaluate(path/'results/final_answer.json',HERE.parent/'task/data',path/'results/analysis.md') if proc.returncode==0 else {'final_score':0,'passed':False}
            delivered.append({'control':name,'source_sha256':hashlib.sha256(code.encode()).hexdigest(),'exit_code':proc.returncode,'score':grade['final_score'],'expected_score':wanted,'scientific_failures':grade.get('failed_gates',[]),'invocation':command(path,['run_pipeline.py','--data','/task/data','--output-dir','/results'])})
        result['delivered_controls']=delivered
        if not all(c['exit_code']==0 and c['score']==c['expected_score'] and not c['scientific_failures'] for c in delivered):result.update(status='fail',passed=False)
        # Change only parent 5 measurements while keeping metadata bytes identical.
        altered=work/'measurement_task';shutil.copytree(HERE.parent/'task',altered)
        with np.load(altered/'data/hybridization.npz',allow_pickle=False) as z:changed={k:z[k].copy() for k in z.files}
        with np.load(mutant/'task/data/hybridization.npz',allow_pickle=False) as z:new={k:z[k].copy() for k in z.files}
        changed['observed'][:,5]=new['observed'][:,5]
        for key in ['spike_observed','cell_counts','pre_growth','run_on','limits']:changed[key][5]=new[key][5]
        np.savez_compressed(altered/'data/hybridization.npz',**changed)
        from generate_data import update_manifest
        update_manifest(altered/'data')
        assert (altered/'data/study_metadata.json').read_bytes()==(HERE.parent/'task/data/study_metadata.json').read_bytes()
        altered_expected_path=work/'measurement_expected.json'
        proc=subprocess.run([sys.executable,str(HERE/'compute_expected.py'),'--data',str(altered/'data'),'--output',str(altered_expected_path)],capture_output=True,text=True,timeout=timeout,env=env)
        if proc.returncode:result['blocker']='altered-measurement target failed';result['status']='blocked';return save()
        altered_expected=json.loads(altered_expected_path.read_text());path=work/'positive_measurements';stage(path,solver,altered)
        proc=subprocess.run(command(path,['run_pipeline.py','--data','/task/data','--output-dir','/results']),capture_output=True,text=True,timeout=timeout)
        grade=evaluate(path/'results/final_answer.json',altered/'data',path/'results/analysis.md',expected=altered_expected) if proc.returncode==0 else {'final_score':0,'passed':False}
        positive=json.loads((path/'results/final_answer.json').read_text()) if proc.returncode==0 else {}
        baseline=json.loads((base/'results/final_answer.json').read_text());invariant=False;responsive=False
        if positive:
            invariant=all(equivalent_scientific_results(positive['analyses']['leave_parent_out'][k],baseline['analyses']['leave_parent_out'][k]) for k in ['genes','group_contrasts'])
            responsive=positive['analyses']['base']['genes']!=baseline['analyses']['base']['genes']
        result['parent_exclusion_response']={'exit_code':proc.returncode,'score':grade['final_score'],'source_sha256':hashlib.sha256((path/'solver/run_pipeline.py').read_bytes()).hexdigest(),'metadata_unchanged':True,'changed_parent_indices':[5],'base_responded':responsive,'leave_parent_out_invariant':invariant,'invocation':command(path,['run_pipeline.py','--data','/task/data','--output-dir','/results'])}
        if not (grade['passed'] and invariant and responsive):result.update(status='fail',passed=False)
        # A metadata-keyed replay knows the original fixture, but cannot distinguish changed measurements with identical metadata.
        keyed=work/'keyed_replay';keyed.mkdir();cache={}
        for path0,task0 in [(base,HERE.parent/'task')]:
            key=hashlib.sha256((task0/'data/study_metadata.json').read_bytes()).hexdigest();cache[key]={'answer':(path0/'results/final_answer.json').read_text(),'report':(path0/'results/analysis.md').read_text()}
        keyed_code="import argparse,json,hashlib\nfrom pathlib import Path\np=argparse.ArgumentParser();p.add_argument('--data');p.add_argument('--output-dir');a=p.parse_args();cache="+repr(cache)+"\nk=hashlib.sha256((Path(a.data)/'study_metadata.json').read_bytes()).hexdigest();v=cache[k];o=Path(a.output_dir);o.mkdir(exist_ok=True);(o/'final_answer.json').write_text(v['answer']);(o/'analysis.md').write_text(v['report'])\n"
        (keyed/'run_pipeline.py').write_text(keyed_code);controls=[]
        for name,task0,target0 in [('base',HERE.parent/'task',None),('altered_measurements',altered,altered_expected)]:
            path=work/('keyed_'+name);stage(path,keyed,task0);proc=subprocess.run(command(path,['run_pipeline.py','--data','/task/data','--output-dir','/results']),capture_output=True,text=True,timeout=30)
            grade=evaluate(path/'results/final_answer.json',task0/'data',path/'results/analysis.md',expected=target0) if proc.returncode==0 else {'final_score':0,'passed':False}
            controls.append({'dataset':name,'exit_code':proc.returncode,'score':grade['final_score'],'passed':grade['passed']})
        rejected=all(c['exit_code']==0 for c in controls) and controls[0]['passed'] and not controls[1]['passed']
        result['metadata_keyed_replay']={'source_sha256':hashlib.sha256(keyed_code.encode()).hexdigest(),'runs':controls,'rejected':rejected}
        if not rejected:result.update(status='fail',passed=False)
    return save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--solver',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--timeout',type=int,default=600);p.add_argument('--replay-control',action='store_true');a=p.parse_args()
    r=verify(a.solver,a.output_dir,a.timeout,a.replay_control);sys.exit(0 if r['passed'] else 2 if r['status']=='blocked' else 1)
