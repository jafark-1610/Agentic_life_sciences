"""Bundle the expert computations into the single solver-code submission slot."""
import ast
import argparse
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent


def export(destination):
    modules = ['model.py', 'expert_solution.py', 'artifacts.py', 'run_pipeline.py']
    statements = []
    for name in modules:
        tree = ast.parse((HERE/name).read_text())
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module in ['model', 'expert_solution', 'artifacts']:
                continue
            if name == 'run_pipeline.py' and isinstance(node, ast.FunctionDef) and node.name == 'main':
                class ConfigTransform(ast.NodeTransformer):
                    def visit_Call(self, item):
                        self.generic_visit(item)
                        if isinstance(item.func, ast.Attribute) and item.func.attr == 'add_argument' and item.args and isinstance(item.args[0], ast.Constant) and item.args[0].value == '--config':
                            for kw in item.keywords:
                                if kw.arg == 'default': kw.value = ast.Constant(None)
                        return item
                    def visit_Assign(self, item):
                        self.generic_visit(item)
                        if len(item.targets) == 1 and isinstance(item.targets[0], ast.Name) and item.targets[0].id == 'config':
                            item.value = ast.parse('json.loads(args.config.read_text()) if args.config else DEFAULT_CONFIG', mode='eval').body
                        return item
                node = ConfigTransform().visit(node)
            statements.append(node)
    cfg = json.loads((HERE/'config/parameters.yaml').read_text())
    preamble = ('import sys, os\nsys.dont_write_bytecode = True\n'
                'for _thread_variable in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"]:\n'
                '    os.environ[_thread_variable] = "1"\nDEFAULT_CONFIG = '+repr(cfg)+'\n')
    output = preamble+ast.unparse(ast.fix_missing_locations(ast.Module(body=statements, type_ignores=[])))+'\n'
    ast.parse(output)
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_text(output)
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    export(a.output)
