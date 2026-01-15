"""Live test of workflow discovery system."""
import sys
from pathlib import Path

print("Starting discovery test...", flush=True)

# Point to the examples directory
base = Path(r'R:\Dante\pdac\cc_mapping_api\Finalized_Notebooks\Stiotoichemtry_Investigations\Elastic_Net_Analysis\generate_workflow_docs\examples')
search_dir = base / 'multi_file_example'

print(f'Base exists: {base.exists()}', flush=True)
print(f'Search dir exists: {search_dir.exists()}', flush=True)
print(f'Files in search_dir:', flush=True)
for f in search_dir.glob('*.py'):
    print(f'  {f.name}', flush=True)

print(flush=True)
print('=== Testing Discovery ===', flush=True)

from sphinx_workflow_ext.discovery import WorkflowDiscovery

discovery = WorkflowDiscovery(base_path=base, verbose=True)
result = discovery.discover(['multi_file_example/'])

print(f'Found {len(result.workflows)} workflow modules', flush=True)
print(f'Errors: {result.errors}', flush=True)
print(f'Skipped: {len(result.skipped)} files', flush=True)

for path, wf in result.workflows.items():
    print(f'\nModule: {wf.module_name}', flush=True)
    print(f'  Tiers: {wf.declared_tiers}', flush=True)
    print(f'  Entry points: {wf.entry_points}', flush=True)

print("\nDone!", flush=True)
