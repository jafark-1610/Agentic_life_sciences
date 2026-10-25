"""Semantic oracle comparison using the published scientific acceptance rules.

Unlike a recursive exact-float comparison, this checks model equivalence,
identifier ordering, all numeric tolerances, and physical peak witnesses.
"""
import argparse
import json
import sys
from pathlib import Path

from score_rubric import normalize, science, strict_read

HERE = Path(__file__).resolve().parent


def comparison_policy(acceptance):
    def tolerance(absolute, relative=0.0):
        return {'absolute': absolute, 'relative': relative}

    parameter = tolerance(acceptance['parameter_absolute'], acceptance['parameter_relative'])
    return {
        'command': 'python expert_solution/compare_answers.py --actual expert_solution/results/final_answer.json --expected expert_solution/final_answer.json --data task/data',
        'path_syntax': 'JSON Pointer with * matching one array index or object key',
        'path_tolerances': {
            '/chips/*/models/*/*': parameter,
            '/chips/*/target_capacity_interval/*': parameter,
            '/chips/*/calibration/*/*': tolerance(acceptance['calibration_absolute']),
            '/chips/*/fit_rmse': tolerance(acceptance['fit_rmse_max']),
            '/courses/*/minimum_efficacy': tolerance(acceptance['efficacy_absolute']),
            '/courses/*/maximum_peak_free': tolerance(acceptance['peak_absolute']),
            '/courses/*/cases/*/efficacy': tolerance(acceptance['efficacy_absolute']),
            '/courses/*/cases/*/peak_free': tolerance(acceptance['peak_absolute']),
            '/selection/peak_witness/value': tolerance(acceptance['witness_value_absolute']),
        },
        'numeric_rule': 'abs(actual-expected) <= absolute + relative*abs(expected)',
        'exact_fields': 'Case/schema identity, scientific identifiers, Boolean flags, local rank, and resolved model indices.',
        'semantic_rules': {
            'ordering': 'Match chips/courses/cases by identifiers and models by parameter-equivalence mapping.',
            '/selection/peak_witness/time': 'Do not compare to a fixed coordinate. Recompute the physical value at the submitted time and check its agreement with the global peak.',
            'runtime_metadata': 'Validate hashes and schema against the current execution; elapsed time and environment versions are not reference-equality fields.',
        },
        'oracle_serialization': {
            'float_decimal_places': 8,
            'peak_time_decimal_places': 3,
            'peak_value': 'Recomputed at the serialized time using the serialized parameter vector.',
            'scope': 'Oracle reproducibility only; solver decimal precision is unrestricted.',
        },
    }


def compare(actual, expected, data):
    actual_object, _ = normalize(actual)
    metadata = isinstance(actual_object, dict) and all(
        actual_object.get(key) == expected.get(key) for key in ['schema', 'case_id'])
    result = science(actual, data, expected)
    return {
        'role': 'semantic_oracle_comparison',
        'passed': metadata and all(result['checks'].values()),
        'metadata_matches': metadata,
        'scientific_checks': result['checks'],
        'details': result['details'],
        'presentation_deduction': result['presentation_deduction'],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--actual', required=True, type=Path)
    parser.add_argument('--expected', type=Path, default=HERE / 'final_answer.json')
    parser.add_argument('--data', type=Path, default=HERE.parent / 'task/data')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = compare(strict_read(args.actual), strict_read(args.expected), args.data)
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        result = {'role': 'semantic_oracle_comparison', 'passed': False, 'error': str(exc)}
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end='')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
