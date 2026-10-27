import json,importlib.metadata
from pathlib import Path
LABELS=['INCREASED','DECREASED','EQUIVALENT','UNRESOLVED','NOT_ESTIMABLE']
def counts(answer):
 return {name:{label:sum(e['class']==label for g in a['genes'] for e in g['effects'].values()) for label in LABELS} for name,a in answer['analyses'].items()}
def write_outputs(answer,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'final_answer.json').write_text(json.dumps(answer,allow_nan=False)+'\n')
 sections={
 'Methods':'Joint compartment mass balance is fitted because nuclear disappearance includes both export and destruction. A censored log-normal likelihood and multiple initializations stabilize the kinetic estimates.',
 'Calibration':'Origin-resolved RNA standards identify each sample fractionation and gain matrix. Both physical compartments contribute to each collected fraction, without forcing row normalization.',
 'Censoring':'Signals below the detection limit contribute normal lower-tail probabilities in log space. They are not zero intensities or observations missing at random.',
 'Replication':'Parental populations supply the biological replication. Paired sibling cultures define the treatment contrasts; technical standards, genes and time points do not increase the parent count.',
 'Group uncertainty':'Stress and other transcript means are first contrasted within each parent. Variation among those parental contrasts determines the group interval, preserving shared culture variation.',
 'Sensitivity':'The early window refits the retained sampling times. Parent exclusion uses only indices zero through four, with recomputed paired contrasts and multiplicity adjustment; inference_trace records the actual rate inputs.',
 'Limitations':'The observations are synthetic. First-order destruction, equilibrated baseline pools and well-mixed compartments are assumptions. Six biological parents provide limited precision for small nuclear destruction effects.'}
 text='\n\n'.join('# '+k+'\n\n'+v for k,v in sections.items())
 text+='\n\n# Software\n\n'+', '.join(p+' '+importlib.metadata.version(p) for p in ['numpy','scipy'])+' were used for numerical linear algebra and distribution calculations.\n\n```json\n'+json.dumps({'analysis_counts':counts(answer)},indent=2)+'\n```\n'
 (out/'analysis.md').write_text(text);return answer
