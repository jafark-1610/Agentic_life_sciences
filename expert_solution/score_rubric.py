import os,sys
sys.dont_write_bytecode=True
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,json,re,copy,hashlib
from decimal import Decimal, InvalidOperation
from scipy.stats import t
from pathlib import Path
import numpy as np
from artifacts import counts
HERE=Path(__file__).resolve().parent
def normalize_numbers(a):
 a=copy.deepcopy(a)
 for b in a.get('analyses',{}).values():
  trace=b.get('inference_trace')
  if isinstance(trace,dict):
   for key in ['parent_indices','time_indices']:
    if isinstance(trace.get(key),list):
     converted=[]
     for value in trace[key]:
      try:converted.append(int(float(value)) if isinstance(value,str) and float(value).is_integer() else value)
      except (ValueError,OverflowError):converted.append(value)
     trace[key]=converted
  for g in b.get('genes',[]):
   for e in g.get('effects',{}).values():
    for key in ['vehicle_rate','perturbed_rate','log2_ratio']:
     if isinstance(e.get(key),str):
      try:e[key]=float(e[key])
      except ValueError:pass
    for key in ['interval','equivalence_interval']:
     if isinstance(e.get(key),list):
      try:e[key]=[float(x) for x in e[key]]
      except (ValueError,TypeError):pass
  for row in b.get('group_contrasts',[]):
   try:
    row['estimate']=float(row['estimate']);row['interval']=[float(x) for x in row['interval']]
   except (ValueError,TypeError,KeyError):pass
 return a

def summary_rounding(value):
 try:return float(Decimal(1).scaleb(Decimal(str(value)).as_tuple().exponent)/2)
 except (ValueError,TypeError,OverflowError,InvalidOperation):return 0.

def trace_and_decisions(body,metadata,setting):
 parents=list(range(5 if setting=='leave_parent_out' else 6));times=list(range(7 if setting=='early_window' else 9));problems=[];bad=[]
 try:
  trace=body['inference_trace'];assert trace['parent_indices']==parents and trace['time_indices']==times,'parent/time inclusion'
  assert trace['input_sha256']==metadata['_actual_data_sha256'],'input binding'
  rates=np.asarray(trace['log2_rates'],float);assert rates.shape==(600,len(parents),2,3),'trace shape'
  rows={g['id']:g for g in body['genes']};raw=[];records=[]
  for j,gid in enumerate(metadata['genes']):
   for k,param in enumerate(metadata['parameters']):
    e=rows[gid]['effects'][param];r=rates[j,:,:,k]
    if e.get('class')=='NOT_ESTIMABLE' and e.get('log2_ratio') is None:
     assert np.isnan(r).all(),'missing estimate trace';continue
    assert np.isfinite(r).all(),'nonfinite rates'
    diff=r[:,1]-r[:,0];mean=float(diff.mean());se=max(float(diff.std(ddof=1)/np.sqrt(len(parents))),.015)
    assert abs(float(e['log2_ratio'])-mean)<=.0001+summary_rounding(e['log2_ratio']),'contrast does not follow trace'
    for arm,key in enumerate(['vehicle_rate','perturbed_rate']):
     value=float(e[key]);rounding=summary_rounding(e[key]);lower=max(np.finfo(float).tiny,value-rounding);upper=value+rounding;assert np.log2(lower)-.0001<=r[:,arm].mean()<=np.log2(upper)+.0001,'rate does not follow trace'
    raw.append(float(t.sf((abs(mean)-metadata['material_log2'])/se,len(parents)-1)));records.append((gid,param,e,mean))
  order=np.argsort(raw);q=np.empty(len(raw));q[order]=np.minimum(1,np.minimum.accumulate((np.array(raw)[order]*len(raw)/np.arange(1,len(raw)+1))[::-1])[::-1])
  for (gid,param,e,mean),adj in zip(records,q):
   eq=np.asarray(e['equivalence_interval'],float);inside=eq[0]>-metadata['material_log2'] and eq[1]<metadata['material_log2'];direction='INCREASED' if mean>0 else 'DECREASED';fallback='EQUIVALENT' if inside else 'UNRESOLVED';allowed={direction} if adj<.05-1e-6 else ({fallback} if adj>.05+1e-6 else {direction,fallback})
   if abs(eq[0]+metadata['material_log2'])<=.0001 or abs(eq[1]-metadata['material_log2'])<=.0001:
    if adj>=.05-1e-6:allowed.update(['EQUIVALENT','UNRESOLVED'])
   if e.get('class') not in allowed:bad.append(gid+':'+param)
 except (KeyError,ValueError,TypeError,AssertionError,IndexError,OverflowError) as exc:problems.append(str(exc))
 return not problems,bad,problems

def report_complete(report,a):
 try:
  blocks=re.findall(r'```json\s*([\s\S]*?)```',report);assert len(blocks)==1 and json.loads(blocks[0])['analysis_counts']==counts(a)
  for heading in ['Methods','Calibration','Censoring','Replication','Group uncertainty','Sensitivity','Limitations','Software']:
   match=re.search(r'^#{1,6}\s*'+re.escape(heading)+r'\s*\n([\s\S]*?)(?=^#{1,6}\s|\Z)',report,re.M|re.I);assert match and len(re.findall(r'\b[\w-]+\b',match[1]))>=8,heading
  assert re.search(r'because|to avoid|so that|since|therefore',report,re.I)
  assert 'synthetic' in report.lower()
  software=re.search(r'^#{1,6}\s*Software\s*\n([\s\S]*?)(?=^#{1,6}\s|\Z)',report,re.M|re.I).group(1).lower()
  assert any(word in software for word in ['numpy','scipy','pandas','statsmodels','scikit-learn','sklearn','jsonschema','standard library','stdlib'])
  return True
 except (ValueError,KeyError,TypeError,AssertionError):return False

def assess(a,expected,metadata,report=''):
 presentation=False
 if isinstance(a,list) and len(a)==1:a=a[0];presentation=True
 if not isinstance(a,dict):return {'final_score':0,'passed':False,'automatic_zero':'unreadable answer'}
 presentation=presentation or set(a)-{'schema','case_id','analyses'}!=set() or a.get('schema')!='rna_transport/1' or a.get('case_id')!=metadata['case_id']
 def numeric_strings(v):
  if isinstance(v,str):
   try:float(v);return True
   except ValueError:return False
  if isinstance(v,dict):return any(numeric_strings(x) for x in v.values())
  if isinstance(v,list):return any(numeric_strings(x) for x in v)
  return False
 presentation=presentation or numeric_strings(a)
 a=normalize_numbers(a)
 metadata=dict(metadata);metadata.setdefault('_actual_data_sha256',expected['analyses']['base']['inference_trace']['input_sha256'])
 gates=[];details={};delta=metadata['material_log2']
 for name,r in expected['analyses'].items():
  b=a.get('analyses',{}).get(name,{});by={x.get('id'):x for x in b.get('genes',[]) if isinstance(x,dict)};rate=[];interval=[];strong=[];equiv=[];forbidden=0;unsupported=0;estimated=0;nest=[]
  for gene in r['genes']:
   for k,z in gene['effects'].items():
    v=by.get(gene['id'],{}).get('effects',{}).get(k,{})
    try:
     x=float(v['log2_ratio']);ci=np.array(v['interval'],float);eq=np.array(v['equivalence_interval'],float);vr=float(v['vehicle_rate']);pr=float(v['perturbed_rate']);assert np.isfinite([x,vr,pr,*ci,*eq]).all() and vr>0 and pr>0 and len(ci)==len(eq)==2
    except (ValueError,TypeError,KeyError,AssertionError,OverflowError):
     if z['interval'][0]>delta+.2 or z['interval'][1]<-delta-.2:strong.append(False)
     if z['equivalence_interval'][0]>-.3*delta and z['equivalence_interval'][1]<.3*delta:equiv.append(False)
     continue
    estimated+=1;half=(z['interval'][1]-z['interval'][0])/2;allow=max(.25,half);rate.extend([abs(x-z['log2_ratio'])<=allow,abs(np.log2(vr/z['vehicle_rate']))<=allow,abs(np.log2(pr/z['perturbed_rate']))<=allow]);width=ci[1]-ci[0];refwidth=z['interval'][1]-z['interval'][0];interval.append(ci[0]<=z['log2_ratio']<=ci[1] and .4<=width/refwidth<=2.5)
    c=v.get('class');nest.append(ci[0]-.0001<=eq[0]<=x+.0001 and x-.0001<=eq[1]<=ci[1]+.0001)
    if z['interval'][0]>delta+.2:strong.append(c=='INCREASED')
    if z['interval'][1]<-delta-.2:strong.append(c=='DECREASED')
    if z['equivalence_interval'][0]>-.3*delta and z['equivalence_interval'][1]<.3*delta:equiv.append(c=='EQUIVALENT')
    forbidden+=int((c=='INCREASED' and z['interval'][1]<delta) or (c=='DECREASED' and z['interval'][0]>-delta))
    unsupported+=int(c=='EQUIVALENT' and (z['interval'][0]>delta or z['interval'][1]<-delta))
    if c=='EQUIVALENT' and not(eq[0]>-delta and eq[1]<delta):unsupported+=1
  n=len(r['genes'])*3;gok=True;gb={x.get('parameter'):x for x in b.get('group_contrasts',[]) if isinstance(x,dict)}
  for z in r['group_contrasts']:
   try:
    v=gb[z['parameter']];width=z['interval'][1]-z['interval'][0];own=v['interval'];gok=gok and abs(v['estimate']-z['estimate'])<=max(.12,width/2) and own[0]<=z['estimate']<=own[1] and .4<=(own[1]-own[0])/width<=2.5
   except (KeyError,TypeError,IndexError):gok=False
  result={'coverage':estimated/n>=.95,'rates_and_effects':bool(rate) and np.mean(rate)>=.90,'intervals':bool(interval) and np.mean(interval)>=.90 and all(nest),'classes':(not strong or np.mean(strong)>=.98) and (not equiv or np.mean(equiv)>=.98) and forbidden<=3 and unsupported<=3,'group_contrasts':bool(gok)}
  trace_ok,decision_errors,trace_errors=trace_and_decisions(b,metadata,name)
  result['classes']=result['classes'] and not decision_errors and trace_ok
  result['trace']=trace_ok
  result={k:bool(v) for k,v in result.items()}
  details[name]={'coverage':estimated/n,'rate_share':float(np.mean(rate)) if rate else 0,'interval_share':float(np.mean(interval)) if interval else 0,'strong_share':float(np.mean(strong)) if strong else 1,'equivalence_share':float(np.mean(equiv)) if equiv else 1,'forbidden':forbidden,'unsupported_equivalence':unsupported,'criteria':result,'decision_errors':decision_errors,'trace_errors':trace_errors};gates.extend(name+':'+k for k,v in result.items() if not v)
 weights={'coverage':5,'rates_and_effects':20,'intervals':20,'classes':20,'group_contrasts':20};score=sum(w for k,w in weights.items() if details['base']['criteria'][k]);score+=10 if all(all(v['criteria'].values()) for k,v in details.items() if k!='base') else 0
 report_ok=report_complete(report,a)
 if report_ok:score+=5
 if gates:score=min(79,score)
 if presentation:score-=5
 return {'final_score':score,'passed':bool(score>=80),'failed_gates':gates,'details':details,'report_points':5 if report_ok else 0,'execution_status':'artifact grading only; isolated rerun required'}
def evaluate(answer_path,data,analysis_path=None,expected=None,truth=None,rubric=None):
 try:a=json.loads(Path(answer_path).read_text())
 except (OSError,ValueError):a=None
 expected=expected or json.loads((HERE/'private/expected_answer.json').read_text());m=json.loads((Path(data)/'study_metadata.json').read_text());m['_actual_data_sha256']=hashlib.sha256((Path(data)/'hybridization.npz').read_bytes()).hexdigest()
 try:report=Path(analysis_path).read_text() if analysis_path else ''
 except OSError:report=''
 return assess(a,expected,m,report)
def write_result(r,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'rubric_results.json').write_text(json.dumps(r,indent=2)+'\n');(out/'rubric_results.md').write_text('# Numerical grading\n\nScore: '+str(r['final_score'])+'; passed: '+str(r['passed'])+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--answer',type=Path,required=True);p.add_argument('--analysis',type=Path);p.add_argument('--data',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();r=evaluate(a.answer,a.data,a.analysis);write_result(r,a.output_dir);print(r['final_score'],r['passed'])
