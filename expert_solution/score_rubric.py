"""Explicit data-derived grading with physical attaining-witness checks."""
import os
import sys
sys.dont_write_bytecode = True
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse
import json
import re
from pathlib import Path
from functools import lru_cache
import numpy as np
from scipy.optimize import linear_sum_assignment
from kinetics import load_data, read_json, candidate_statistics
from artifacts import evidence
from compute_truth import exact_families
from build_rubric_md import comparison_items
HERE=Path(__file__).resolve().parent


def note(findings,value):
    if value not in findings:findings.append(value)


def load_answer(path):
    findings=[]
    def pairs(rows):
        out={}
        for k,v in rows:
            if k in out:note(findings,'duplicate key; last value used')
            out[k]=v
        return out
    try:return json.loads(Path(path).read_text(),object_pairs_hook=pairs),findings,None
    except (OSError,UnicodeError,ValueError,RecursionError) as exc:return None,findings,type(exc).__name__


def numeric(raw,shape,findings):
    def scan(x):
        if isinstance(x,bool):raise ValueError('boolean')
        if isinstance(x,str):note(findings,'numeric string')
        if isinstance(x,list):
            for v in x:scan(v)
    try:
        scan(raw)
        with np.errstate(all='ignore'):a=np.asarray(raw,dtype=float)
        if a.shape==tuple(shape) and np.isfinite(a).all():return a
    except (ValueError,TypeError,OverflowError,RecursionError):pass
    return None


def keyed(raw,known,fields,findings):
    out={}
    if not isinstance(raw,list):return out
    for obj in raw:
        if not isinstance(obj,dict) or not isinstance(obj.get('id'),str):continue
        key=obj['id']
        if key not in known:note(findings,'unknown identifier');continue
        if key in out:note(findings,'repeated identifier; first used');continue
        if set(obj)-set(fields):note(findings,'extra metadata')
        out[key]=obj
    return out


def witness_checks(obj,panel,meta,expected,truth,findings):
    weights,families=exact_families(panel,meta,truth)
    selected=obj.get('selected_policy');lookup={p['id']:i for i,p in enumerate(meta['policies'])}
    if selected not in lookup:return False,{'reason':'invalid selected policy'}
    index=lookup[selected];tol=meta['tolerances'];details={};passed=True
    expected_policy={p['id']:p for p in expected['policies']}[selected]
    for side,column in [('lower',0),('upper',1)]:
        raw=obj.get('net_witnesses',{}).get(side) if isinstance(obj.get('net_witnesses'),dict) else None
        rates=numeric(raw,(meta['subtypes'],meta['modules'],2),findings)
        if rates is None:return False,{'reason':'witness shape or numeric failure'}
        chosen=[];distances=[]
        for h,f in enumerate(families):
            distance=np.max(np.abs(f['models']-rates[h]),axis=(1,2));i=int(np.argmin(distance))
            distances.append(float(distance[i]));chosen.append(dict(exchange=f['exchange'],models=f['models'][[i]]))
        if max(distances)>tol['witness_rates']:passed=False
        stats=[candidate_statistics(f,panel['protocol'],meta['policies']) for f in chosen]
        flux=sum(w*s['flux'][0] for w,s in zip(weights,stats));interval=panel['protocol']['bulk_turnover']
        feasible=interval['lower']-tol['witness_turnover']<=flux<=interval['upper']+tol['witness_turnover']
        den=sum(w*s['d'][0] for w,s in zip(weights,stats));value=sum(w*s['net'][0,index] for w,s in zip(weights,stats))/den
        gap=abs(value-expected_policy['net_bounds'][column]);ok=feasible and gap<=tol['witness_endpoint'] and max(distances)<=tol['witness_rates']
        passed=passed and ok
        details[side]=dict(passed=bool(ok),maximum_rate_error=max(distances),turnover=float(flux),net=float(value),endpoint_error=float(gap))
    return bool(passed),details


def assess(answer,D,report='',expected=None,rubric=None,truth=None,load_findings=None):
    expected=expected or read_json(HERE/'private/expected_answer.json');rubric=rubric or read_json(HERE/'rubric.json');truth=truth or read_json(HERE/'private/truth.json')
    findings=list(load_findings or []);result=dict(case_id=D['meta']['case_id'],role='numerical_artifact_grading',
      execution_status='unverified by artifact grader; verify_submission.py required',presentation_findings=findings,scientific_gates=[],credit_items=[],report_findings=[])
    if isinstance(answer,list) and len(answer)==1 and isinstance(answer[0],dict):answer=answer[0];note(findings,'one-object wrapper')
    if not isinstance(answer,dict):result.update(final_score=0,passed=False,automatic_zero='unreadable answer object');return result
    if answer.get('schema')!='persistent_cycle/1' or answer.get('case_id')!=D['meta']['case_id']:note(findings,'schema or case_id')
    if set(answer)-{'schema','case_id','preparations'}:note(findings,'extra metadata')
    fields=['id','mixture_weights','exchange_generators','forward_bounds','backward_bounds','candidate_counts','retention_bounds','retained_epr_bounds','policies','selected_policy','net_witnesses']
    by_id=keyed(answer.get('preparations'),{p['id'] for p in D['panels']},fields,findings)
    target={p['id']:p for p in expected['preparations']};meta=D['meta'];normal=[];raw_score=0.
    items_by_id={p['id']:[] for p in D['panels']}
    for item in comparison_items(D['meta'],expected):items_by_id[item['preparation']].append(item)
    for panel in D['panels']:
        pid=panel['id'];obj=by_id.get(pid,{});passed_groups={g['id']:True for g in rubric['groups']}
        # Latent label permutations are presentation, never biological errors.
        fitted=numeric(obj.get('exchange_generators'),(meta['subtypes'],meta['modules'],meta['modules']),findings)
        if fitted is not None:
            known=np.array(target[pid]['exchange_generators'])
            cost=np.max(np.abs(known[:,None]-fitted[None,:]),axis=(2,3))
            rows,cols=linear_sum_assignment(cost)
            if np.max(cost[rows,cols])<=meta['tolerances']['exchange'] and not np.array_equal(cols,np.arange(meta['subtypes'])):
                obj=dict(obj)
                for key in ['mixture_weights','exchange_generators','forward_bounds','backward_bounds','candidate_counts']:
                    raw=obj.get(key)
                    if isinstance(raw,list) and len(raw)==meta['subtypes']:obj[key]=[raw[i] for i in cols]
                if isinstance(obj.get('net_witnesses'),dict):
                    obj['net_witnesses']=dict(obj['net_witnesses'])
                    for side in ['lower','upper']:
                        raw=obj['net_witnesses'].get(side)
                        if isinstance(raw,list) and len(raw)==meta['subtypes']:obj['net_witnesses'][side]=[raw[i] for i in cols]
                note(findings,'consistent subtype permutation recovered')
        polfields=['id','success_bounds','loss_bounds','cost_bounds','gain_bounds','net_bounds']
        pols=keyed(obj.get('policies'),{p['id'] for p in meta['policies']},polfields,findings)
        normalized=dict(obj);normalized['policies']=list(pols.values())
        if isinstance(obj.get('net_witnesses'),dict):
            converted={}
            for side in ['lower','upper']:
                rates=numeric(obj['net_witnesses'].get(side),(meta['subtypes'],meta['modules'],2),findings)
                if rates is not None:converted[side]=rates.tolist()
            normalized['net_witnesses']=converted
        valid=True
        for item in items_by_id[pid]:
            path=item['path'];parts=path.split('.')
            if parts[0]=='policies':value=pols.get(parts[1],{}).get(parts[2])
            else:value=obj.get(path)
            if item['kind']=='allowed_set':
                ok=isinstance(value,str) and value in item['expected'];error=None
            else:
                ref=np.array(item['expected'],dtype=float);a=numeric(value,ref.shape,findings)
                if a is None:ok=False;error=None;valid=False
                else:
                    error=float(np.max(np.abs(a-ref)));ok=error<=item['absolute_tolerance']
                    if len(parts)==1:normalized[path]=a.tolist()
                    else:pols[parts[1]][parts[2]]=a.tolist()
            passed_groups[item['group']]=passed_groups[item['group']] and bool(ok)
            result['scientific_gates'].append(dict(preparation=pid,field=path,group=item['group'],passed=bool(ok),maximum_absolute_error=error,tolerance=item.get('absolute_tolerance')))
        try:witness_ok,witness_detail=witness_checks(obj,panel,meta,target[pid],truth,findings)
        except (ValueError,TypeError,KeyError,IndexError,OverflowError,np.linalg.LinAlgError) as exc:witness_ok=False;witness_detail={'reason':type(exc).__name__}
        passed_groups['attaining_witnesses']=witness_ok
        result['scientific_gates'].append(dict(preparation=pid,field='net_witnesses',group='attaining_witnesses',passed=witness_ok,details=witness_detail))
        for group in rubric['groups']:
            points=group['points']/len(D['panels']) if passed_groups[group['id']] else 0.
            raw_score+=points;result['credit_items'].append(dict(preparation=pid,group=group['id'],points=points,maximum=group['points']/len(D['panels'])))
        if valid:normal.append(normalized)
    report_ok=False
    try:
        blocks=re.findall(r'```json\s*([\s\S]*?)```',report);assert len(blocks)==1
        r=json.loads(blocks[0])['preparations'];assert len(r)==len(D['panels'])
        rows={p['id']:p for p in r};assert len(rows)==len(D['panels']) and len(normal)==len(D['panels'])
        calculated=evidence(dict(preparations=normal),D)
        for p in calculated:
            for key,tol in meta['report_tolerances'].items():
                v=rows[p['id']][key];assert not isinstance(v,bool) and np.isfinite(float(v)) and abs(float(v)-p[key])<=tol,p['id']+':'+key
        report_ok=True
    except (AssertionError,ValueError,TypeError,KeyError,OverflowError,IndexError,np.linalg.LinAlgError) as exc:result['report_findings'].append('Missing or inconsistent calculated evidence: '+str(exc)[:160])
    if report_ok:raw_score+=rubric['report_points']
    failed=[g for g in result['scientific_gates'] if not g['passed']]
    capped=min(raw_score,rubric['scientific_gate_cap']) if failed else raw_score
    final=max(0,capped-(rubric['presentation_deduction'] if findings else 0))
    result.update(raw_score=round(raw_score,6),scientific_cap_applied=bool(failed),report_points=5 if report_ok else 0,
                  failed_gates=[g['preparation']+':'+g['field'] for g in failed],final_score=round(final,6),passed=bool(final>=rubric['pass_threshold']))
    return result


def evaluate(answer_path,data,analysis_path=None,expected=None,truth=None,rubric=None):
    answer,findings,error=load_answer(answer_path);D=load_data(data)
    try:report=Path(analysis_path).read_text() if analysis_path else ''
    except (OSError,UnicodeError):report=''
    result=assess(answer,D,report,expected,rubric,truth,findings)
    if error:result['automatic_zero']=error
    return result


def write_result(result,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'rubric_results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    text='# Persistent-cycle grading\n\nScore: '+str(result['final_score'])+'; passed: '+str(result['passed'])+'.\n\nArtifact grading does not establish execution.\n\n'
    text+='| Preparation | Group | Earned | Maximum |\n|---|---|---:|---:|\n'
    for row in result.get('credit_items',[]):text+='|{preparation}|{group}|{points}|{maximum}|\n'.format(**row)
    (out/'rubric_results.md').write_text(text)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--answer',type=Path,required=True);p.add_argument('--analysis',type=Path);p.add_argument('--data',type=Path,default=HERE.parent/'task/data');p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    r=evaluate(a.answer,a.data,a.analysis);write_result(r,a.output_dir);print(json.dumps({'final_score':r['final_score'],'passed':r['passed'],'failed_gates':len(r.get('failed_gates',[]))}))
