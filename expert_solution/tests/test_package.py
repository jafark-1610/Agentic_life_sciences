import unittest,sys,json,copy,subprocess,tempfile,hashlib
from pathlib import Path
import numpy as np
import jsonschema
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parent;DATA=ROOT/'task/data';sys.path.insert(0,str(HERE));sys.path.insert(0,str(Path(__file__).resolve().parent))
from score_rubric import grade,read_strict
from expert_solution import analyse,load,portfolios,polytope,solve,utility
from independent_oracle import verify,menu,inputs

class PackageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.answer=read_strict(HERE/'final_answer.json');cls.D=load(DATA)
 def test_01_dataset_validation(self):
  subprocess.run([sys.executable,str(DATA/'validate_dataset.py')],check=True,capture_output=True)
 def test_02_full_schema(self):
  jsonschema.validate(self.answer,read_strict(DATA/'output_schema.json'))
 def test_03_oracle_recomputes_answer(self):
  actual=analyse(DATA);self.assertTrue(grade(actual,DATA)['passed'])
 def test_04_independent_science(self):
  result=verify(DATA,self.answer);self.assertGreater(result['lp_checks'],1000);self.assertLess(result['maximum_absolute_error'],1e-6)
 def test_05_canonical_grades_full(self):
  r=grade(self.answer,DATA);self.assertEqual(r['final_score'],100);self.assertFalse(r['scientific_cap_applied'])
 def test_06_wrong_safe_decision_fails(self):
  a=copy.deepcopy(self.answer);winner=a['selection']['modules'];other=next(d for d in a['designs'] if d['modules']!=winner and d['floor']>=self.D['design_rules']['safety_floor']);a['selection']['modules']=other['modules'];self.assertFalse(grade(a,DATA)['checks']['robust_selection'])
 def test_07_infeasible_witness_fails(self):
  a=copy.deepcopy(self.answer);a['selection']['witness']['flux'][0]+=1;self.assertFalse(grade(a,DATA)['checks']['adversarial_witness'])
 def test_08_wrong_regret_fails(self):
  a=copy.deepcopy(self.answer);a['designs'][0]['by_culture'][0]['regret']+=.1;self.assertFalse(grade(a,DATA)['passed'])
 def test_09_wrong_identifiability_fails(self):
  a=copy.deepcopy(self.answer);r=a['cultures'][0]['flux_ranges'][0];r['identifiable']=not r['identifiable'];self.assertFalse(grade(a,DATA)['checks']['flux_ranges'])
 def test_10_format_only_does_not_cap(self):
  a=copy.deepcopy(self.answer);a['schema']='wrong';r=grade(a,DATA);self.assertEqual(r['final_score'],95);self.assertFalse(r['scientific_cap_applied'])
 def test_11_order_invariance(self):
  a=copy.deepcopy(self.answer);a['cultures'].reverse();a['designs'].reverse()
  for d in a['designs']:d['modules'].reverse();d['by_culture'].reverse()
  a['selection']['modules'].reverse();a['selection']['witness']['challenger'].reverse();self.assertEqual(grade(a,DATA)['final_score'],100)
 def test_12_malformed_and_duplicate_ids_fail(self):
  a=copy.deepcopy(self.answer);a['cultures'][0]['flux_ranges'][0]['lower']=None;self.assertFalse(grade(a,DATA)['passed'])
  a=copy.deepcopy(self.answer);a['designs'].append(a['designs'][0]);self.assertFalse(grade(a,DATA)['checks']['utility_envelopes'])
 def test_13_strict_json(self):
  for text in ['{"x":1,"x":2}','{"x":NaN}','{"x":1e999}']:
   with tempfile.TemporaryDirectory() as t:
    p=Path(t)/'a.json';p.write_text(text)
    with self.assertRaises(ValueError):read_strict(p)
 def test_14_generated_rubrics_current(self):
  subprocess.run([sys.executable,str(HERE/'build_rubric_md.py'),'--check'],check=True)
 def test_15_independent_menu(self):
  self.assertEqual(portfolios(self.D['design_rules']),menu(self.D['design_rules']))
 def test_16_unobservable_cycle(self):
  c=self.D['cultures'][0];P=polytope(self.D,c);x=solve(P,np.zeros(36))[1];z=np.zeros(36);z[22:24]=1
  self.assertLess(np.max(np.abs(P['A_eq']@z)),1e-12);self.assertLess(np.max(np.abs(P['A_ub']@z)),1e-12)
 def test_17_missing_group_is_not_pass(self):
  a=copy.deepcopy(self.answer);del a['selection'];r=grade(a,DATA);self.assertFalse(r['passed']);self.assertTrue(r['scientific_cap_applied'])
 def test_18_manifest_corruption_rejected(self):
  import shutil
  with tempfile.TemporaryDirectory() as t:
   d=Path(t)/'data';shutil.copytree(DATA,d);(d/'cultures.json').write_text('[]')
   r=subprocess.run([sys.executable,str(d/'validate_dataset.py')],capture_output=True);self.assertNotEqual(r.returncode,0)
if __name__=='__main__':unittest.main()
