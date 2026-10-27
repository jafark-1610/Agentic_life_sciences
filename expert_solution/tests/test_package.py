import os,sys
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import unittest,json,copy
import numpy as np
from scipy.linalg import expm
from analysis_engine import trajectory,load,inference
from score_rubric import assess
from artifacts import counts
from build_rubric_md import build
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.m,cls.D=load(HERE.parent/'task/data');cls.a=json.loads((HERE/'final_answer.json').read_text());cls.report=(HERE/'analysis.md').read_text()
 def test_expert(self):self.assertEqual(assess(self.a,self.a,self.m,self.report)['final_score'],100)
 def test_independent_matrix_exponential_mass_balance(self):
  rng=np.random.default_rng(312);x=rng.uniform([-1,-3,-4,-3],[5,-.2,-.5,-.5],(10,4));dt=np.array([.2,.8,2.]);g=np.array([.05,.025,.01]);q=np.array([.3,.1,.06]);pred=trajectory(x,dt,g,q,.05)
  for i,v in enumerate(x):
   n,e,dn,dc=np.exp(v);state=np.array([n,n*e/(dc+.05),1.]);alpha=(e+dn+.05)*n
   for j,h in enumerate(dt):
    A=np.array([[-e-dn-g[j],0,alpha*q[j]],[e,-dc-g[j],0],[0,0,0]]);state=expm(A*h)@state;np.testing.assert_allclose(state[:2],pred[i,j+1],rtol=1e-12)
 def test_paired_group_counts(self):self.assertEqual(len(self.a['analyses']['base']['genes']),600);self.assertEqual(sum(counts(self.a)['base'].values()),1800)
 def test_interval_nesting(self):
  for a in self.a['analyses'].values():
   for g in a['genes']:
    for e in g['effects'].values():self.assertLessEqual(e['interval'][0],e['equivalence_interval'][0]);self.assertLessEqual(e['equivalence_interval'][1],e['interval'][1])
 def test_fake_equivalence_fails(self):
  a=copy.deepcopy(self.a)
  for b in a['analyses'].values():
   for g in b['genes']:
    for e in g['effects'].values():e['class']='EQUIVALENT'
  self.assertFalse(assess(a,self.a,self.m,self.report)['passed'])
 def test_fake_sensitivity_fails(self):
  a=copy.deepcopy(self.a);a['analyses']['early_window']=copy.deepcopy(a['analyses']['base'])
  for g in a['analyses']['early_window']['genes']:
   for e in g['effects'].values():e['log2_ratio']+=1
  self.assertFalse(assess(a,self.a,self.m,self.report)['passed'])
 def test_report_is_computed(self):self.assertEqual(assess(self.a,self.a,self.m,'all correct')['final_score'],95)
 def test_wrapper_recovers(self):self.assertEqual(assess([self.a],self.a,self.m,self.report)['final_score'],95)
 def test_numeric_strings_cost_only_presentation(self):
  a=copy.deepcopy(self.a);a['analyses']['base']['genes'][0]['effects']['export']['log2_ratio']=str(a['analyses']['base']['genes'][0]['effects']['export']['log2_ratio']);self.assertEqual(assess(a,self.a,self.m,self.report)['final_score'],95)
 def test_omitting_strong_results_is_not_a_correct_class(self):
  a=copy.deepcopy(self.a)
  for g in a['analyses']['base']['genes'][:30]:
   for e in g['effects'].values():
    for k in ['log2_ratio','interval','equivalence_interval','vehicle_rate','perturbed_rate']:e[k]=None
    e['class']='NOT_ESTIMABLE'
  self.assertFalse(assess(a,self.a,self.m,self.report)['details']['base']['criteria']['classes'])
 def test_group_numeric_string_is_only_presentation(self):
  a=copy.deepcopy(self.a);a['analyses']['base']['group_contrasts'][0]['estimate']=str(a['analyses']['base']['group_contrasts'][0]['estimate']);r=assess(a,self.a,self.m,self.report);self.assertEqual(r['final_score'],95);self.assertFalse(r['failed_gates'])
 def test_single_unsupported_direction_fails(self):
  a=copy.deepcopy(self.a);g=a['analyses']['base']['genes'][52];g['effects']['nuclear_decay']['class']='INCREASED';r=assess(a,self.a,self.m,self.report);self.assertFalse(r['passed']);self.assertIn('base:classes',r['failed_gates'])
 def test_mass_unsupported_directions_fail(self):
  a=copy.deepcopy(self.a)
  for b in a['analyses'].values():
   for g in b['genes']:
    for e in g['effects'].values():
     if e['class']=='UNRESOLVED' and e['interval'][0]<0<e['interval'][1]:e['class']='INCREASED'
  self.assertFalse(assess(a,self.a,self.m,self.report)['passed'])
 def test_counts_only_report_loses_report_credit(self):
  report='```json\n'+json.dumps({'analysis_counts':counts(self.a)})+'\n```';r=assess(self.a,self.a,self.m,report);self.assertEqual(r['final_score'],95);self.assertEqual(r['report_points'],0)
 def test_base_copy_is_not_parent_exclusion(self):
  a=copy.deepcopy(self.a);a['analyses']['leave_parent_out']=copy.deepcopy(a['analyses']['base']);r=assess(a,self.a,self.m,self.report);self.assertFalse(r['passed']);self.assertIn('leave_parent_out:trace',r['failed_gates'])
 def test_forged_parent_list_still_needs_recomputed_means(self):
  a=copy.deepcopy(self.a);b=copy.deepcopy(a['analyses']['base']);b['inference_trace']['parent_indices']=list(range(5));b['inference_trace']['log2_rates']=np.asarray(b['inference_trace']['log2_rates'])[:,:5].tolist();a['analyses']['leave_parent_out']=b;r=assess(a,self.a,self.m,self.report);self.assertFalse(r['passed']);self.assertIn('leave_parent_out:trace',r['failed_gates'])
 def test_public_upload_has_no_grade_mechanics(self):
  self.assertFalse((HERE.parent/'task/data/grading_contract.json').exists())
  text=(HERE.parent/'task/prompt.md').read_text().lower()
  for forbidden in ['score at 79','passing requires','five report points','presentation points']:self.assertNotIn(forbidden,text)
 def test_paired_test_near_boundary_accepts_adjacent_decisions(self):
  from scipy.stats import t
  from score_rubric import trace_and_decisions
  b=copy.deepcopy(self.a['analyses']['base']);m=dict(self.m);m['_actual_data_sha256']=b['inference_trace']['input_sha256'];delta=m['material_log2'];se=.1;mean=delta+t.isf(.05,5)*se
  v=np.arange(6,dtype=float);v=(v-v.mean())/v.std(ddof=1)*se*np.sqrt(6)+mean
  rates=np.zeros((600,6,2,3));rates[:,:,1,:]=v[None,:,None];b['inference_trace']['log2_rates']=rates.tolist()
  for g in b['genes']:
   for e in g['effects'].values():e.update(vehicle_rate=1.,perturbed_rate=2**mean,log2_ratio=mean,interval=[mean-t.ppf(.975,5)*se,mean+t.ppf(.975,5)*se],equivalence_interval=[mean-t.ppf(.95,5)*se,mean+t.ppf(.95,5)*se],**{'class':'UNRESOLVED'})
  ok,bad,errors=trace_and_decisions(b,m,'base');self.assertTrue(ok);self.assertFalse(bad)
  for g in b['genes']:
   for e in g['effects'].values():e['class']='INCREASED'
  ok,bad,errors=trace_and_decisions(b,m,'base');self.assertTrue(ok);self.assertFalse(bad)
 def test_report_allows_a_standard_library_implementation(self):
  import re
  from score_rubric import report_complete
  text=re.sub(r'# Software[\s\S]*?```json','# Software\n\nOnly the standard library was used to parse the arrays and compute the models and distributions.\n\n```json',self.report)
  self.assertTrue(report_complete(text,self.a))
 def test_report_requires_each_topic(self):
  import re
  from score_rubric import report_complete
  for heading in ['Methods','Calibration','Censoring','Replication','Group uncertainty','Sensitivity','Limitations','Software']:
   text=re.sub(r'^# '+re.escape(heading)+r'\n[\s\S]*?(?=^# |\Z)','',self.report,flags=re.M)
   self.assertFalse(report_complete(text,self.a),heading)
 def test_numeric_strings_in_audit_indices_are_presentation_only(self):
  a=copy.deepcopy(self.a)
  for b in a['analyses'].values():
   for key in ['parent_indices','time_indices']:b['inference_trace'][key]=[str(x) for x in b['inference_trace'][key]]
  r=assess(a,self.a,self.m,self.report);self.assertEqual(r['final_score'],95);self.assertFalse(r['failed_gates'])
 def test_invalid_numeric_types_do_not_crash_arithmetic_checks(self):
  for value in [True,False,float('inf'),float('nan'),10**400]:
   a=copy.deepcopy(self.a);a['analyses']['base']['genes'][0]['effects']['nuclear_decay']['log2_ratio']=value
   self.assertFalse(assess(a,self.a,self.m,self.report)['passed'])
 def test_required_paths(self):
  for p in ['config/parameters.yaml','results/run_summary.json']:self.assertTrue((HERE/p).is_file())
 def test_rubric_generation(self):
  for name,text in zip(['rubric.json','rubric.md'],build()):self.assertEqual((HERE/name).read_text(),text)
if __name__=='__main__':unittest.main()
