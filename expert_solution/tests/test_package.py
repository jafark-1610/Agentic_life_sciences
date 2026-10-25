import unittest,json,copy,sys,tempfile,subprocess,re
from pathlib import Path
import numpy as np,jsonschema
from scipy import sparse
HERE=Path(__file__).resolve().parents[1];DATA=HERE.parent/'task/data';sys.path.insert(0,str(HERE))
from expert_solution import load
from artifacts import write_outputs,stable
from causal_model import coefficients,REF,N,solve,ratio,observation
from score_rubric import science,delivery,strict_read

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.a=strict_read(HERE/'final_answer.json');cls.D=load(DATA)
 def test_01_data_validation(self):subprocess.run([sys.executable,str(DATA/'validate_dataset.py')],check=True,capture_output=True)
 def test_02_schema(self):jsonschema.validate(self.a,strict_read(DATA/'output_schema.json'))
 def test_03_reference_full_score(self):self.assertEqual(science(self.a,DATA)['final_score'],100)
 def test_04_wrapper_recovery(self):
  r=science([self.a],DATA);self.assertEqual(r['final_score'],95);self.assertTrue(all(r['checks'].values()));self.assertFalse(r['scientific_cap_applied'])
 def test_05_numeric_strings(self):
  a=copy.deepcopy(self.a);a['contexts'][0]['policies'][0]['net_gain_lower']=str(a['contexts'][0]['policies'][0]['net_gain_lower']);self.assertEqual(science(a,DATA)['final_score'],95)
 def test_06_order_invariance(self):
  a=copy.deepcopy(self.a);a['contexts'].reverse();a['global_policies'].reverse()
  for c in a['contexts']:c['policies'].reverse()
  self.assertEqual(science(a,DATA)['final_score'],100)
 def test_07_wrong_bound_rejected(self):
  a=copy.deepcopy(self.a);a['contexts'][0]['policies'][0]['net_gain_lower']+=.1;self.assertFalse(science(a,DATA)['passed'])
 def test_08_point_fit_is_not_identification(self):
  a=copy.deepcopy(self.a);a['contexts'][0]['policies'][0]['point_identified']=not a['contexts'][0]['policies'][0]['point_identified'];self.assertFalse(science(a,DATA)['checks']['identification'])
 def test_09_wrong_policy_rejected(self):
  a=copy.deepcopy(self.a);a['selection']['policy']='policy_02';self.assertFalse(science(a,DATA)['checks']['policy_decision'])
 def test_10_wrong_envelope_rejected(self):
  a=copy.deepcopy(self.a);a['global_policies'][0]['worst_cost']+=.1;self.assertFalse(science(a,DATA)['checks']['global_envelopes'])
 def test_11_delivery_evidence(self):
  with tempfile.TemporaryDirectory() as t:
   write_outputs(self.a,self.D,t);self.assertEqual(delivery(self.a,DATA,t)['deduction'],0);(Path(t)/'analysis.md').write_text('All passed');self.assertEqual(delivery(self.a,DATA,t)['deduction'],5)
 def test_12_delivery_order_and_rounding(self):
  with tempfile.TemporaryDirectory() as t:
   write_outputs(self.a,self.D,t);p=Path(t)/'analysis.md';text=p.read_text();b=json.loads(re.search(r'```json\s*\n(.*?)\n```',text,re.S)[1]);b['context_diagnostics'].reverse();b['context_diagnostics'][0]['largest_net_gain_width']=round(b['context_diagnostics'][0]['largest_net_gain_width'],3);p.write_text('```json\n'+json.dumps(b)+'\n```\n');self.assertEqual(delivery(self.a,DATA,t)['deduction'],0)
 def test_13_strict_json(self):
  for text in ['{"x":NaN}','{"x":1e999}','{"x":1,"x":2}']:
   with tempfile.TemporaryDirectory() as t:
    p=Path(t)/'a';p.write_text(text)
    with self.assertRaises(ValueError):strict_read(p)
 def test_14_extra_field_presentation_only(self):
  a=copy.deepcopy(self.a);a['extra']='note';r=science(a,DATA);self.assertEqual(r['final_score'],95);self.assertFalse(r['scientific_cap_applied'])
 def test_15_duplicate_scientific_ids_rejected(self):
  a=copy.deepcopy(self.a);a['contexts'][0]['policies'].append(a['contexts'][0]['policies'][0]);self.assertFalse(science(a,DATA)['checks']['sharp_bounds'])
 def test_16_fractional_bounds_analytic(self):
  P={'A_ub':sparse.csr_matrix([[1.,0.]]),'b_ub':np.array([1.]),'A_eq':sparse.csr_matrix([[1.,1.]]),'b_eq':np.array([1.]),'bounds':(0,None)};num=np.array([-.1,.4]);den=np.array([.6,1.]);self.assertAlmostEqual(ratio(P,num,den),-1/6,places=8);self.assertAlmostEqual(ratio(P,num,den,True),.4,places=8)
 def test_17_benchmark_identity(self):
  v=coefficients(self.D['contexts'][0],REF);self.assertTrue(np.all(v['gain']==0));self.assertTrue(np.all(v['harm']==0));np.testing.assert_allclose(v['eligibility'],v['survival'])
 def test_18_complete_type_family(self):self.assertEqual(N,3*6*9*2*4)
 def test_19_observation_normalization(self):
  c=self.D['contexts'][0];lab=c['labs'][0]
  for p in ['natural','priming_trial','rescue_trial','sequential_trial']:
   sums=np.asarray(observation(c,lab,p).sum(axis=0)).ravel();np.testing.assert_allclose(sums[:N],1-lab['x1']);np.testing.assert_allclose(sums[N:],lab['x1'])
 def test_20_only_existing_three_slots(self):
  want=['run_pipeline.py','final_answer.json','analysis.md']
  for name in ['deliverables.json','required_deliverables.json']:self.assertEqual(strict_read(DATA.parent/name),want)
  self.assertEqual(strict_read(HERE/'config/parameters.yaml')['required_deliverables'],want)
  self.assertNotIn('run_summary', (DATA.parent/'prompt.md').read_text())
 def test_21_stable_serialization(self):self.assertEqual(stable(self.a),stable(stable(self.a)))
 def test_22_rubric_reproducibility(self):subprocess.run([sys.executable,str(HERE/'build_rubric_md.py'),'--check'],check=True)
 def test_23_missing_scientific_content_rejected(self):
  a=copy.deepcopy(self.a);a['contexts']=[];self.assertFalse(science(a,DATA)['passed'])
 def test_24_compact_and_reordered_json(self):
  a=json.loads(json.dumps(dict(reversed(list(self.a.items()))),separators=(',',':')));self.assertEqual(science(a,DATA)['final_score'],100)
if __name__=='__main__':unittest.main()
