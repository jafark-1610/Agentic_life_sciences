import os,sys
sys.dont_write_bytecode=True
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,json,re
from pathlib import Path
import numpy as np
from artifacts import counts
HERE=Path(__file__).resolve().parent
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
  result={k:bool(v) for k,v in result.items()}
  details[name]={'coverage':estimated/n,'rate_share':float(np.mean(rate)) if rate else 0,'interval_share':float(np.mean(interval)) if interval else 0,'strong_share':float(np.mean(strong)) if strong else 1,'equivalence_share':float(np.mean(equiv)) if equiv else 1,'forbidden':forbidden,'unsupported_equivalence':unsupported,'criteria':result};gates.extend(name+':'+k for k,v in result.items() if not v)
 weights={'coverage':5,'rates_and_effects':20,'intervals':20,'classes':20,'group_contrasts':20};score=sum(w for k,w in weights.items() if details['base']['criteria'][k]);score+=10 if all(all(v['criteria'].values()) for k,v in details.items() if k!='base') else 0
 report_ok=False
 try:
  blocks=re.findall(r'```json\s*([\s\S]*?)```',report);report_ok=len(blocks)==1 and json.loads(blocks[0])['analysis_counts']==counts(a)
 except (ValueError,KeyError,TypeError):pass
 if report_ok:score+=5
 if gates:score=min(79,score)
 if presentation:score-=5
 return {'final_score':score,'passed':bool(score>=80),'failed_gates':gates,'details':details,'report_points':5 if report_ok else 0,'execution_status':'artifact grading only; isolated rerun required'}
def evaluate(answer_path,data,analysis_path=None,expected=None,truth=None,rubric=None):
 try:a=json.loads(Path(answer_path).read_text())
 except (OSError,ValueError):a=None
 expected=expected or json.loads((HERE/'private/expected_answer.json').read_text());m=json.loads((Path(data)/'study_metadata.json').read_text())
 try:report=Path(analysis_path).read_text() if analysis_path else ''
 except OSError:report=''
 return assess(a,expected,m,report)
def write_result(r,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'rubric_results.json').write_text(json.dumps(r,indent=2)+'\n');(out/'rubric_results.md').write_text('# Numerical grading\n\nScore: '+str(r['final_score'])+'; passed: '+str(r['passed'])+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--answer',type=Path,required=True);p.add_argument('--analysis',type=Path);p.add_argument('--data',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();r=evaluate(a.answer,a.data,a.analysis);write_result(r,a.output_dir);print(r['final_score'],r['passed'])
