import json,sys,copy
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'tests'))
from expert_solution import load,select
from mechanism import simulate
from score_rubric import science,strict_read
from artifacts import add_witness
from independent_oracle import integrate

def run():
 data=HERE.parent/'task/data';D=load(data);ref=strict_read(HERE/'final_answer.json');truth=strict_read(HERE/'private/generation_truth.json');checks=[]
 def record(name,observed,criterion,ok):checks.append({'check':name,'observed':observed,'criterion':criterion,'status':'pass' if ok else 'fail'})
 # Check the canonical inference against the generator, allowing chemical-site permutation.
 max_relative=0.
 for chip in ref['chips']:
  p=np.array(truth[chip['id']]['parameters']);error=min(np.max(np.abs(np.array(q)/p-1)) for q in chip['models']);max_relative=max(max_relative,float(error))
 record('generation_truth_recovery',{'max_relative_parameter_error':max_relative},'parameter error < 0.001, providing more than threefold tolerance clearance',max_relative<.001)
 # Independent solver and finer extremum mesh across every selected-course case.
 selected=ref['selection']['course'];course=next(c for c in D['courses'] if c['id']==selected);fitted={c['id']:c for c in ref['chips']};max_e=0.;max_p=0.;mass=0.
 for chip in D['chips']:
  for p in fitted[chip['id']]['models']:
   for s in D['scenarios']:
    x=simulate(p,chip['known'],course,scenario=s['multipliers'],precise=True);y=integrate(p,chip['known'],course,s['multipliers']);max_e=max(max_e,abs(x['efficacy']-y['efficacy']));max_p=max(max_p,abs(x['peak_free']-y['peak_free']));mass=max(mass,y['mass_error'])
 record('independent_radau_and_peak_refinement',{'max_efficacy_difference':max_e,'max_peak_difference':max_p,'max_mass_error':mass},'all differences < 1e-6 and mass error < 1e-7',max(max_e,max_p)<1e-6 and mass<1e-7)
 # These are deliberately wrong scientific baselines, not model trials.
 one=copy.deepcopy(ref)
 chosen={}
 for chip in one['chips']:
  cid=chip['id'];scores=[]
  for i in range(len(chip['models'])):scores.append(np.mean([x['efficacy'] for c in ref['courses'] for x in c['cases'] if x['chip']==cid and x['model_index']==i]))
  chosen[cid]=int(np.argmax(scores));chip['models']=[chip['models'][chosen[cid]]];q=chip['models'][0][9];chip['target_capacity_interval']=[q,q];chip['target_capacity_point_identified']=True
 for c in one['courses']:
  c['cases']=[x for x in c['cases'] if x['model_index']==chosen[x['chip']]]
  for x in c['cases']:x['model_index']=0
  c['minimum_efficacy']=min(x['efficacy'] for x in c['cases']);c['maximum_peak_free']=max(x['peak_free'] for x in c['cases'])
 one['selection']=select(D,one['courses']);add_witness(one,D);r=science(one,data)
 record('single_compatible_fit_baseline',{'selected':one['selection']['course'],'score':r['final_score'],'checks':r['checks'],'all_calibration_and_observation_fits_pass':r['checks']['measurement_fit']},'single-fit baseline must be rejected despite passing observation-fit checks',not r['passed'] and r['checks']['measurement_fit'])
 coarse=copy.deepcopy(ref);grid=[0.,4.,8.,12.,16.,24.,36.];raw={c['id']:c for c in D['courses']};systems={c['id']:c for c in D['chips']};scenarios={s['id']:s for s in D['scenarios']}
 for c in coarse['courses']:
  for x in c['cases']:
   chip=systems[x['chip']];p=fitted[x['chip']]['models'][x['model_index']];Y=simulate(p,chip['known'],raw[c['id']],grid,scenarios[x['scenario']]['multipliers']);x['peak_free']=float(np.max(Y[:,2]))
  c['maximum_peak_free']=max(x['peak_free'] for x in c['cases'])
 coarse['selection']=select(D,coarse['courses']);add_witness(coarse,D);r=science(coarse,data)
 record('sampled_peak_baseline',{'selected':coarse['selection']['course'],'score':r['final_score'],'checks':r['checks'],'max_peak_error':r['details'].get('max_peak_error')},'sampled maxima must fail continuous counterfactual criteria',not r['passed'] and not r['checks']['counterfactual_predictions'])
 # Reference decision is not balanced on a numerical gate.
 row=next(c for c in ref['courses'] if c['id']==selected);limits=D['model_spec']['decision'];acc=D['model_spec']['acceptance'];em=row['minimum_efficacy']-limits['efficacy_floor'];pm=limits['peak_ceiling']-row['maximum_peak_free']
 record('reference_gate_clearance',{'efficacy_margin':em,'peak_margin':pm,'efficacy_tolerance':acc['efficacy_absolute'],'peak_tolerance':acc['peak_absolute']},'selected course clears efficacy and safety gates by >= 3 numerical tolerances',em>=3*acc['efficacy_absolute'] and pm>=3*acc['peak_absolute'])
 r=science([ref],data);record('readable_wrapper_recovery',{'score':r['final_score'],'checks':r['checks']},'wrapper is scientific pass with one presentation deduction',r['final_score']==95 and all(r['checks'].values()))
 report={'role':'local_scientific_robustness_not_model_trials','status':'pass' if all(c['status']=='pass' for c in checks) else 'fail','checks':checks};dest=HERE/'robustness_checks';(dest/'result.json').write_text(json.dumps(report,indent=2)+'\n');(dest/'result.md').write_text('# Robustness evidence\n\n'+'\n'.join(f"* {c['check']}: {c['status']}. {c['criterion']}. Observed: {json.dumps(c['observed'])}" for c in checks)+'\n');print(json.dumps(report,indent=2));return 0 if report['status']=='pass' else 1
if __name__=='__main__':sys.exit(run())
