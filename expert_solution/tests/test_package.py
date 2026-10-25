import unittest,json,copy,sys,tempfile,subprocess,hashlib
from pathlib import Path
import numpy as np,jsonschema
HERE=Path(__file__).resolve().parents[1];DATA=HERE.parent/'task/data';sys.path.insert(0,str(HERE));sys.path.insert(0,str(Path(__file__).resolve().parent))
from score_rubric import science,strict_read,delivery
from expert_solution import load,swap
from mechanism import simulate
from artifacts import write_outputs,add_witness,input_hash
from independent_oracle import integrate

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.answer=strict_read(HERE/'final_answer.json');cls.D=load(DATA)
 def test_01_schema(self):jsonschema.validate(self.answer,strict_read(DATA/'output_schema.json'))
 def test_02_data_integrity(self):subprocess.run([sys.executable,str(DATA/'validate_dataset.py')],check=True,capture_output=True)
 def test_03_canonical_full_science(self):self.assertEqual(science(self.answer,DATA)['final_score'],100)
 def test_04_wrapper_recovers_all_science(self):
  r=science([self.answer],DATA);self.assertEqual(r['final_score'],95);self.assertTrue(all(r['checks'].values()));self.assertFalse(r['scientific_cap_applied'])
 def test_05_extra_field_presentation_only(self):
  a=copy.deepcopy(self.answer);a['note']='extra';r=science(a,DATA);self.assertEqual(r['final_score'],95);self.assertFalse(r['scientific_cap_applied'])
 def test_06_order_and_model_index_invariance(self):
  a=copy.deepcopy(self.answer);a['chips'].reverse();a['courses'].reverse()
  for c in a['chips']:c['models'].reverse()
  for c in a['courses']:
   c['cases'].reverse()
   for x in c['cases']:x['model_index']=1-x['model_index']
  w=a['selection']['peak_witness'];w['model_index']=1-w['model_index'];self.assertEqual(science(a,DATA)['final_score'],100)
 def test_07_missing_compatible_model_rejected(self):
  a=copy.deepcopy(self.answer);a['chips'][0]['models'].pop();self.assertFalse(science(a,DATA)['checks']['global_identifiability'])
 def test_08_global_claim_not_local_rank(self):
  a=copy.deepcopy(self.answer);a['chips'][0]['target_capacity_point_identified']=True;self.assertFalse(science(a,DATA)['checks']['global_identifiability'])
 def test_09_wrong_case_prediction_rejected(self):
  a=copy.deepcopy(self.answer);a['courses'][0]['cases'][0]['peak_free']+=.1;self.assertFalse(science(a,DATA)['checks']['counterfactual_predictions'])
 def test_10_wrong_peak_time_rejected(self):
  a=copy.deepcopy(self.answer);a['selection']['peak_witness']['time']=0.;self.assertFalse(science(a,DATA)['checks']['continuous_peak_witness'])
 def test_11_wrong_course_rejected(self):
  a=copy.deepcopy(self.answer);a['selection']['course']='course_001';self.assertFalse(science(a,DATA)['checks']['course_decision'])
 def test_12_diagnostic_artifact_and_hashes(self):
  with tempfile.TemporaryDirectory() as tmp:
   write_outputs(self.answer,self.D,DATA,tmp,0.);self.assertEqual(delivery(self.answer,DATA,tmp)['deduction'],0)
   p=Path(tmp)/'run_summary.json';x=json.loads(p.read_text());x['input_sha256']='bad';p.write_text(json.dumps(x));self.assertEqual(delivery(self.answer,DATA,tmp)['deduction'],5)
 def test_13_unsupported_report_fails(self):
  with tempfile.TemporaryDirectory() as tmp:
   write_outputs(self.answer,self.D,DATA,tmp,0.);(Path(tmp)/'analysis.md').write_text('Everything passed');self.assertEqual(delivery(self.answer,DATA,tmp)['deduction'],5)
 def test_13b_report_order_and_rounding_accepted(self):
  import re
  with tempfile.TemporaryDirectory() as tmp:
   write_outputs(self.answer,self.D,DATA,tmp,0.);p=Path(tmp)/'analysis.md';text=p.read_text();block=re.search(r'```json\s*\n(.*?)\n```',text,re.S);e=json.loads(block[1]);e['chip_diagnostics'].reverse();e['limitations'].reverse()
   for c in e['chip_diagnostics']:c['fit_rmse']=round(c['fit_rmse'],8)
   p.write_text('```json\n'+json.dumps(e)+'\n```\n');self.assertEqual(delivery(self.answer,DATA,tmp)['deduction'],0)
 def test_14_numeric_strings_recovered(self):
  a=copy.deepcopy(self.answer);a['chips'][0]['models'][0]=list(map(str,a['chips'][0]['models'][0]));r=science(a,DATA);self.assertEqual(r['final_score'],95)
 def test_15_strict_json_errors(self):
  for text in ['{"x":NaN}','{"x":1e999}','{"x":1,"x":2}']:
   with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'x';p.write_text(text)
    with self.assertRaises(ValueError):strict_read(p)
 def test_16_independent_forward_equations(self):
  chip=self.D['chips'][0];p=self.answer['chips'][0]['models'][0];course=self.D['courses'][19]
  for scenario in self.D['scenarios']:
   x=simulate(p,chip['known'],course,scenario=scenario['multipliers'],precise=True);y=integrate(p,chip['known'],course,scenario['multipliers'])
   self.assertLess(abs(x['efficacy']-y['efficacy']),1e-6);self.assertLess(abs(x['peak_free']-y['peak_free']),1e-6);self.assertLess(y['mass_error'],1e-8)
 def test_17_observational_symmetry(self):
  chip=self.D['chips'][0];p=self.answer['chips'][0]['models'][0]
  for proto in self.D['protocols']:
   t=[.1,1.,4.,12.,36.];x=simulate(p,chip['known'],proto,t,precise=True)['states'];y=simulate(swap(p),chip['known'],proto,t,precise=True)['states']
   self.assertLess(np.max(abs(x[:,1]-y[:,1])),1e-7);self.assertLess(np.max(abs(x[:,2:5].sum(axis=1)-y[:,2:5].sum(axis=1))),1e-7)
 def test_18_counterfactual_breaks_symmetry(self):
  chip=self.D['chips'][0];p=self.answer['chips'][0]['models'][0];course=self.D['courses'][19]
  x=simulate(p,chip['known'],course,precise=True);y=simulate(swap(p),chip['known'],course,precise=True);self.assertGreater(abs(x['efficacy']-y['efficacy']),.01)
 def test_19_rubric_regeneration(self):subprocess.run([sys.executable,str(HERE/'build_rubric_md.py'),'--check'],check=True)
 def test_20_deliverable_slots_explicit(self):
  m=strict_read(HERE.parent/'task/deliverables.json');self.assertEqual({r['path'] for r in m['required_deliverables']},{'run_pipeline.py','requirements.txt','final_answer.json','analysis.md','run_summary.json'})
 def test_21_empty_scientific_content_is_not_format(self):
  a=copy.deepcopy(self.answer);a['chips']=[];self.assertFalse(science(a,DATA)['passed'])
if __name__=='__main__':unittest.main()
