import json,hashlib,argparse
from pathlib import Path
HERE=Path(__file__).resolve().parent
def build():
 data=HERE.parent/'task/data';contract=json.loads((data/'grading_contract.json').read_text());expected=json.loads((HERE/'private/expected_answer.json').read_text());r=dict(contract,case_id='ALS_RNA_TRANSPORT_006',expected=expected,comparison_policy='task/prompt.md Scientific assessment; broad interval- and share-based comparisons',expected_sha256=hashlib.sha256((HERE/'private/expected_answer.json').read_bytes()).hexdigest());text='# RNA transport statistical rubric\n\nGenerated from the public contract and computed statistical benchmark.\n\n';text+='| Group | Points |\n|---|---:|\n'+''.join('|'+k+'|'+str(v)+'|\n' for k,v in contract['groups'].items());text+='\nReport: five points. Scientific failures cap at 79; pass threshold 80. The numerical and class-zone rules are published in task/prompt.md. The machine rubric embeds all expected results; nearby methods within the published allowances receive credit. Artifact grading does not establish pipeline execution.\n';return json.dumps(r,indent=2)+'\n',text
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
 for name,text in zip(['rubric.json','rubric.md'],build()):
  path=HERE/name
  if a.check:assert path.read_text()==text
  else:path.write_text(text)
