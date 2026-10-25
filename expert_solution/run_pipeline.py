"""Offline oracle entry point. No dependency on any solver artifacts."""
import argparse,json,time,hashlib,platform,subprocess,sys
from pathlib import Path
import jsonschema
from expert_solution import analyse
HERE=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=HERE.parent/'task/data');p.add_argument('--output-dir',type=Path,default=HERE/'results');p.add_argument('--config',type=Path,default=HERE/'config/parameters.yaml');a=p.parse_args()
 config=json.loads(a.config.read_text());assert config=={'method':'polyhedral_minimax_regret','lp_solver':'highs'}
 start=time.monotonic();subprocess.run([sys.executable,str(a.data/'validate_dataset.py'),'--data',str(a.data)],check=True)
 answer=analyse(a.data);jsonschema.validate(answer,json.loads((a.data/'output_schema.json').read_text()))
 a.output_dir.mkdir(parents=True,exist_ok=True)
 text=json.dumps(answer,indent=2,allow_nan=False)+'\n';(a.output_dir/'final_answer.json').write_text(text)
 s=answer['selection'];winning=next((d for d in answer['designs'] if d['modules']==s['modules']),None)
 report=['# Metabolic rescue design analysis','', 'The feasible state includes 32 fluxes and four shared calibration offsets per culture. Linear programs retain mass balance, capacities, standards and all assay intervals jointly. Each flux range is optimized directly. Utility differences use the same feasible state for both designs. Global regret maximizes over culture, challenger and feasible state. Safety is a separate worst-case utility constraint.','', '## Decision',json.dumps({'selection':s['modules'],'metrics':winning},indent=2),'','## Identifiability','The forward and reverse exchange cycles admit large gross-flux ranges. Their interval widths, not a point estimate or assay residual, determine the reported identifiability flags.','', '## Computed diagnostics','All endpoints are LP optima. The selected witness is a feasible adversarial state attaining the global regret. Separate unit tests verify primal feasibility and support-function duality; the robustness workflow tests ordering, units, calibration translation and scientifically wrong decision procedures.','', '## Limitations','This is a synthetic reduced carbon-equivalent network with stipulated affine response surfaces. The assay is a calibrated linear tracer fingerprint, not a nonlinear raw mass-isotopomer model. Bounded errors are deterministic admissibility bounds, not confidence intervals. Findings do not establish clinical efficacy.']
 report.extend(['', '## Numerical identifiability diagnostics', json.dumps([{'culture':c['id'], 'identifiable_count':sum(r['identifiable'] for r in c['flux_ranges']), 'widest_interval':max(r['upper']-r['lower'] for r in c['flux_ranges']), 'widest_reaction':max(c['flux_ranges'],key=lambda r:r['upper']-r['lower'])['reaction']} for c in answer['cultures']],indent=2)])
 (a.output_dir/'analysis.md').write_text('\n'.join(report)+'\n')
 (a.output_dir/'run_summary.json').write_text(json.dumps({'status':'success','exit_code':0,'python':platform.python_version(),'elapsed_seconds':round(time.monotonic()-start,3),'answer_sha256':hashlib.sha256(text.encode()).hexdigest(),'config':config},indent=2)+'\n')
 print('oracle success:',len(answer['cultures']),'cultures;',len(answer['designs']),'designs; seconds',round(time.monotonic()-start,2))
if __name__=='__main__':main()
