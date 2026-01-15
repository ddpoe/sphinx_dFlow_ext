#!/usr/bin/env python
"""
Quick validation script for sphinx_workflow_ext.

Run this to check for syntax errors and import issues:

    python validate_syntax.py
    
Or with verbose output:

    python validate_syntax.py -v
"""

import sys
import traceback
from pathlib import Path


def validate_imports(verbose: bool = False) -> bool:
    """
    Validate all modules can be imported without errors.
    
    Returns:
        True if all imports succeed, False otherwise.
    """
    all_passed = True
    
    # List of modules to check
    modules_to_check = [
        ('sphinx_workflow_ext', 'Main package'),
        ('sphinx_workflow_ext.discovery', 'Auto-discovery module'),
        ('sphinx_workflow_ext.toc_generator', 'TOC generator module'),
        ('sphinx_workflow_ext.directives', 'Directives module'),
        ('sphinx_workflow_ext.extension', 'Extension module'),
        ('sphinx_workflow_ext.rst_generator', 'RST generator'),
        ('sphinx_workflow_ext.roles', 'Roles module'),
    ]
    
    print("=" * 60)
    print("SYNTAX AND IMPORT VALIDATION")
    print("=" * 60)
    print()
    
    for module_name, description in modules_to_check:
        try:
            module = __import__(module_name, fromlist=[''])
            print(f"✓ {module_name}")
            if verbose:
                print(f"  └─ {description}")
        except SyntaxError as e:
            print(f"✗ {module_name} - SYNTAX ERROR")
            print(f"  └─ Line {e.lineno}: {e.msg}")
            if e.text:
                print(f"     {e.text.strip()}")
            all_passed = False
        except ImportError as e:
            print(f"✗ {module_name} - IMPORT ERROR")
            print(f"  └─ {e}")
            if verbose:
                traceback.print_exc()
            all_passed = False
        except Exception as e:
            print(f"✗ {module_name} - ERROR")
            print(f"  └─ {type(e).__name__}: {e}")
            if verbose:
                traceback.print_exc()
            all_passed = False
    
    print()
    return all_passed


def validate_exports(verbose: bool = False) -> bool:
    """
    Validate expected exports exist.
    
    Returns:
        True if all exports exist, False otherwise.
    """
    all_passed = True
    
    print("=" * 60)
    print("EXPORT VALIDATION")
    print("=" * 60)
    print()
    
    # Expected exports from main package
    expected_exports = [
        ('sphinx_workflow_ext', 'setup'),
        ('sphinx_workflow_ext', 'WorkflowDiscovery'),
        ('sphinx_workflow_ext', 'DiscoveredWorkflow'),
        ('sphinx_workflow_ext', 'DiscoveryResult'),
        ('sphinx_workflow_ext', 'discover_workflows'),
        ('sphinx_workflow_ext', 'build_workflow_registry'),
        ('sphinx_workflow_ext', 'WorkflowTOCGenerator'),
        ('sphinx_workflow_ext', 'WorkflowIndexBuilder'),
        ('sphinx_workflow_ext', 'get_toc_css'),
        ('sphinx_workflow_ext', 'get_toc_javascript'),
    ]
    
    # Expected exports from submodules
    submodule_exports = [
        ('sphinx_workflow_ext.directives', 'WorkflowDirective'),
        ('sphinx_workflow_ext.directives', 'WorkflowNotebookDirective'),
        ('sphinx_workflow_ext.directives', 'WorkflowIndexDirective'),
        ('sphinx_workflow_ext.discovery', 'WorkflowDiscovery'),
        ('sphinx_workflow_ext.toc_generator', 'WorkflowTOCGenerator'),
    ]
    
    all_exports = expected_exports + submodule_exports
    
    for module_name, export_name in all_exports:
        try:
            module = __import__(module_name, fromlist=[export_name])
            obj = getattr(module, export_name, None)
            if obj is not None:
                print(f"✓ {module_name}.{export_name}")
            else:
                print(f"✗ {module_name}.{export_name} - NOT FOUND")
                all_passed = False
        except Exception as e:
            print(f"✗ {module_name}.{export_name} - ERROR: {e}")
            all_passed = False
    
    print()
    return all_passed


def validate_class_attributes(verbose: bool = False) -> bool:
    """
    Validate classes have expected attributes.
    
    Returns:
        True if all attributes exist, False otherwise.
    """
    all_passed = True
    
    print("=" * 60)
    print("CLASS ATTRIBUTE VALIDATION")
    print("=" * 60)
    print()
    
    try:
        from sphinx_workflow_ext.discovery import WorkflowDiscovery, DiscoveredWorkflow, DiscoveryResult
        from sphinx_workflow_ext.toc_generator import WorkflowTOCGenerator
        from sphinx_workflow_ext.directives import WorkflowIndexDirective
        
        # Check WorkflowDiscovery
        wd = WorkflowDiscovery()
        checks = [
            (wd, 'discover', 'method'),
            (wd, 'exclude_patterns', 'attribute'),
            (wd, 'include_patterns', 'attribute'),
            (wd, '_should_exclude', 'method'),
            (wd, '_should_include', 'method'),
        ]
        
        for obj, attr, attr_type in checks:
            if hasattr(obj, attr):
                print(f"✓ WorkflowDiscovery.{attr} ({attr_type})")
            else:
                print(f"✗ WorkflowDiscovery.{attr} - MISSING")
                all_passed = False
        
        # Check DiscoveredWorkflow
        dw_checks = ['module_path', 'module_name', 'package_name', 'declared_tiers', 
                     'display_name', 'has_tiers']
        for attr in dw_checks:
            # Check it's a valid attribute on the dataclass
            if attr in DiscoveredWorkflow.__dataclass_fields__ or \
               hasattr(DiscoveredWorkflow, attr):
                print(f"✓ DiscoveredWorkflow.{attr}")
            else:
                print(f"✗ DiscoveredWorkflow.{attr} - MISSING")
                all_passed = False
        
        # Check DiscoveryResult
        dr_checks = ['workflows', 'errors', 'skipped', 'modules_by_package', 'get_all_tiers']
        for attr in dr_checks:
            if attr in DiscoveryResult.__dataclass_fields__ or \
               hasattr(DiscoveryResult, attr):
                print(f"✓ DiscoveryResult.{attr}")
            else:
                print(f"✗ DiscoveryResult.{attr} - MISSING")
                all_passed = False
        
        # Check WorkflowIndexDirective
        directive_checks = ['option_spec', 'has_content', 'required_arguments', 'run']
        for attr in directive_checks:
            if hasattr(WorkflowIndexDirective, attr):
                print(f"✓ WorkflowIndexDirective.{attr}")
            else:
                print(f"✗ WorkflowIndexDirective.{attr} - MISSING")
                all_passed = False
        
    except Exception as e:
        print(f"✗ Error during attribute validation: {e}")
        if verbose:
            traceback.print_exc()
        all_passed = False
    
    print()
    return all_passed


def validate_directive_options(verbose: bool = False) -> bool:
    """
    Validate directive option_spec is correct.
    
    Returns:
        True if options are correct, False otherwise.
    """
    all_passed = True
    
    print("=" * 60)
    print("DIRECTIVE OPTION VALIDATION")
    print("=" * 60)
    print()
    
    try:
        from sphinx_workflow_ext.directives import WorkflowIndexDirective
        
        expected_options = [
            'search-paths',
            'exclude-patterns',
            'title',
            'group-by-package',
            'show-descriptions',
            'expand-all',
        ]
        
        actual_options = set(WorkflowIndexDirective.option_spec.keys())
        
        for opt in expected_options:
            if opt in actual_options:
                print(f"✓ Option: {opt}")
            else:
                print(f"✗ Option: {opt} - MISSING")
                all_passed = False
        
        # Check for unexpected options (not an error, just info)
        extra = actual_options - set(expected_options)
        if extra and verbose:
            print(f"\n  Additional options: {extra}")
        
    except Exception as e:
        print(f"✗ Error during option validation: {e}")
        all_passed = False
    
    print()
    return all_passed


def run_quick_functional_test(verbose: bool = False) -> bool:
    """
    Run a quick functional test of discovery.
    
    Returns:
        True if test passes, False otherwise.
    """
    import tempfile
    
    print("=" * 60)
    print("QUICK FUNCTIONAL TEST")
    print("=" * 60)
    print()
    
    try:
        from sphinx_workflow_ext.discovery import discover_workflows
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create test module (named without test_ prefix to avoid exclusion)
            test_content = '''"""
Sample workflow module.

# WORKFLOWS: overview, detailed
"""

# DOCUMENT_WORKFLOW: overview
def main():
    # Step 1: Start
    pass
'''
            (tmppath / 'workflow_module.py').write_text(test_content)
            
            # Run discovery
            result = discover_workflows(['.'], base_path=tmppath)
            
            if len(result.workflows) == 1:
                workflow = list(result.workflows.values())[0]
                if 'overview' in workflow.declared_tiers:
                    print("✓ Discovery found module with correct tiers")
                    print()
                    return True
                else:
                    print("✗ Discovery found module but tiers are wrong")
                    print(f"  Expected: ['overview', 'detailed']")
                    print(f"  Got: {workflow.declared_tiers}")
            else:
                print(f"✗ Discovery found {len(result.workflows)} modules, expected 1")
                if result.errors:
                    print(f"  Errors: {result.errors}")
        
    except Exception as e:
        print(f"✗ Functional test failed: {e}")
        if verbose:
            traceback.print_exc()
    
    print()
    return False


def main():
    """Run all validation checks."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate sphinx_workflow_ext')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    # Add package to path
    package_dir = Path(__file__).parent / 'sphinx_workflow_ext'
    if package_dir.exists():
        sys.path.insert(0, str(Path(__file__).parent))
    
    results = []
    
    results.append(('Imports', validate_imports(args.verbose)))
    results.append(('Exports', validate_exports(args.verbose)))
    results.append(('Class Attributes', validate_class_attributes(args.verbose)))
    results.append(('Directive Options', validate_directive_options(args.verbose)))
    results.append(('Functional Test', run_quick_functional_test(args.verbose)))
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("All validations passed! ✓")
        return 0
    else:
        print("Some validations failed. Check output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
