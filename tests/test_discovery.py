"""
Test suite for the auto-discovery system.

Run with:
    pytest tests/test_discovery.py -v
    
Or run syntax checks only:
    python -m pytest tests/test_discovery.py::TestSyntaxAndImports -v
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch
import tempfile
import textwrap


# =============================================================================
# SYNTAX AND IMPORT TESTS
# =============================================================================

class TestSyntaxAndImports:
    """Test that all new modules can be imported without syntax errors."""
    
    def test_import_discovery_module(self):
        """Test discovery.py imports without errors."""
        from sphinx_workflow_ext import discovery
        assert hasattr(discovery, 'WorkflowDiscovery')
        assert hasattr(discovery, 'DiscoveredWorkflow')
        assert hasattr(discovery, 'DiscoveryResult')
        assert hasattr(discovery, 'discover_workflows')
    
    def test_import_toc_generator_module(self):
        """Test toc_generator.py imports without errors."""
        from sphinx_workflow_ext import toc_generator
        assert hasattr(toc_generator, 'WorkflowTOCGenerator')
        assert hasattr(toc_generator, 'WorkflowIndexBuilder')
        assert hasattr(toc_generator, 'get_toc_css')
        assert hasattr(toc_generator, 'get_toc_javascript')
    
    def test_import_from_package_init(self):
        """Test all exports from __init__.py work."""
        from sphinx_workflow_ext import (
            setup,
            WorkflowDiscovery,
            DiscoveredWorkflow,
            DiscoveryResult,
            discover_workflows,
            build_workflow_registry,
            WorkflowTOCGenerator,
            WorkflowIndexBuilder,
            get_toc_css,
            get_toc_javascript,
        )
        # Just checking imports work
        assert callable(setup)
        assert callable(discover_workflows)
    
    def test_import_directives_with_index(self):
        """Test directives.py includes WorkflowIndexDirective."""
        from sphinx_workflow_ext.directives import (
            WorkflowDirective,
            WorkflowNotebookDirective,
            WorkflowIndexDirective,
        )
        assert WorkflowIndexDirective is not None
    
    def test_extension_setup_imports(self):
        """Test extension.py imports all needed components."""
        from sphinx_workflow_ext import extension
        # Check WorkflowIndexDirective is imported
        assert hasattr(extension, 'WorkflowIndexDirective')


# =============================================================================
# DISCOVERY MODULE TESTS
# =============================================================================

class TestDiscoveredWorkflow:
    """Test the DiscoveredWorkflow dataclass."""
    
    def test_display_name_with_package(self):
        """Test display_name when package_name is set."""
        from sphinx_workflow_ext.discovery import DiscoveredWorkflow
        
        workflow = DiscoveredWorkflow(
            module_path=Path('/path/to/module.py'),
            module_name='module',
            package_name='mypackage',
            declared_tiers=['overview', 'detailed'],
        )
        assert workflow.display_name == 'mypackage.module'
    
    def test_display_name_without_package(self):
        """Test display_name when package_name is None."""
        from sphinx_workflow_ext.discovery import DiscoveredWorkflow
        
        workflow = DiscoveredWorkflow(
            module_path=Path('/path/to/module.py'),
            module_name='module',
            package_name=None,
            declared_tiers=['overview'],
        )
        assert workflow.display_name == 'module'
    
    def test_has_tiers_true(self):
        """Test has_tiers returns True when tiers exist."""
        from sphinx_workflow_ext.discovery import DiscoveredWorkflow
        
        workflow = DiscoveredWorkflow(
            module_path=Path('/path/to/module.py'),
            module_name='module',
            package_name=None,
            declared_tiers=['overview', 'detailed'],
        )
        assert workflow.has_tiers is True
    
    def test_has_tiers_false(self):
        """Test has_tiers returns False when no tiers."""
        from sphinx_workflow_ext.discovery import DiscoveredWorkflow
        
        workflow = DiscoveredWorkflow(
            module_path=Path('/path/to/module.py'),
            module_name='module',
            package_name=None,
            declared_tiers=[],
        )
        assert workflow.has_tiers is False


class TestDiscoveryResult:
    """Test the DiscoveryResult dataclass."""
    
    def test_modules_by_package_grouping(self):
        """Test modules are grouped by package correctly."""
        from sphinx_workflow_ext.discovery import DiscoveredWorkflow, DiscoveryResult
        
        w1 = DiscoveredWorkflow(
            module_path=Path('/pkg1/a.py'),
            module_name='a',
            package_name='pkg1',
            declared_tiers=['overview'],
        )
        w2 = DiscoveredWorkflow(
            module_path=Path('/pkg1/b.py'),
            module_name='b',
            package_name='pkg1',
            declared_tiers=['detailed'],
        )
        w3 = DiscoveredWorkflow(
            module_path=Path('/pkg2/c.py'),
            module_name='c',
            package_name='pkg2',
            declared_tiers=['full'],
        )
        
        result = DiscoveryResult(
            workflows={
                '/pkg1/a.py': w1,
                '/pkg1/b.py': w2,
                '/pkg2/c.py': w3,
            }
        )
        
        by_package = result.modules_by_package
        assert 'pkg1' in by_package
        assert 'pkg2' in by_package
        assert len(by_package['pkg1']) == 2
        assert len(by_package['pkg2']) == 1
    
    def test_get_all_tiers(self):
        """Test get_all_tiers collects unique tiers."""
        from sphinx_workflow_ext.discovery import DiscoveredWorkflow, DiscoveryResult
        
        w1 = DiscoveredWorkflow(
            module_path=Path('/a.py'),
            module_name='a',
            package_name=None,
            declared_tiers=['overview', 'detailed'],
        )
        w2 = DiscoveredWorkflow(
            module_path=Path('/b.py'),
            module_name='b',
            package_name=None,
            declared_tiers=['detailed', 'full'],
        )
        
        result = DiscoveryResult(workflows={'/a.py': w1, '/b.py': w2})
        
        all_tiers = result.get_all_tiers()
        assert all_tiers == {'overview', 'detailed', 'full'}


class TestWorkflowDiscovery:
    """Test the WorkflowDiscovery class."""
    
    def test_exclude_patterns_default(self):
        """Test default exclude patterns are set."""
        from sphinx_workflow_ext.discovery import WorkflowDiscovery
        
        discovery = WorkflowDiscovery()
        assert 'test_*' in discovery.exclude_patterns
        assert '_*' in discovery.exclude_patterns
    
    def test_should_exclude_test_files(self):
        """Test test files are excluded."""
        from sphinx_workflow_ext.discovery import WorkflowDiscovery
        
        discovery = WorkflowDiscovery()
        assert discovery._should_exclude(Path('test_module.py')) is True
        assert discovery._should_exclude(Path('_private.py')) is True
        assert discovery._should_exclude(Path('.hidden.py')) is True
    
    def test_should_include_python_files(self):
        """Test Python files are included."""
        from sphinx_workflow_ext.discovery import WorkflowDiscovery
        
        discovery = WorkflowDiscovery()
        assert discovery._should_include(Path('module.py')) is True
        assert discovery._should_include(Path('module.txt')) is False
    
    def test_discover_with_temp_file(self):
        """Test discovery finds workflow markers in temp file."""
        from sphinx_workflow_ext.discovery import WorkflowDiscovery
        
        # Create temp directory with a workflow file
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create a module with workflow markers
            module_content = textwrap.dedent('''
                """
                Test module.
                
                # WORKFLOWS: overview, detailed
                """
                
                # DOCUMENT_WORKFLOW: overview, detailed
                def run_analysis():
                    """Entry point."""
                    # Step 1: Load data
                    pass
            ''')
            
            module_file = tmppath / 'test_workflow_module.py'
            # Note: file starts with test_ but let's rename to avoid exclusion
            module_file = tmppath / 'workflow_module.py'
            module_file.write_text(module_content)
            
            # Run discovery
            discovery = WorkflowDiscovery(base_path=tmppath)
            result = discovery.discover(['.'])
            
            # Should find the module
            assert len(result.workflows) == 1
            workflow = list(result.workflows.values())[0]
            assert workflow.module_name == 'workflow_module'
            assert 'overview' in workflow.declared_tiers
            assert 'detailed' in workflow.declared_tiers
    
    def test_discover_extracts_docstring(self):
        """Test discovery extracts first line of docstring."""
        from sphinx_workflow_ext.discovery import WorkflowDiscovery
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            module_content = textwrap.dedent('''
                """This is my module summary.
                
                More details here.
                
                # WORKFLOWS: overview
                """
            ''')
            
            module_file = tmppath / 'my_module.py'
            module_file.write_text(module_content)
            
            discovery = WorkflowDiscovery(base_path=tmppath)
            result = discovery.discover(['.'])
            
            assert len(result.workflows) == 1
            workflow = list(result.workflows.values())[0]
            assert workflow.docstring == 'This is my module summary.'
    
    def test_discover_extracts_entry_points(self):
        """Test discovery extracts function entry points."""
        from sphinx_workflow_ext.discovery import WorkflowDiscovery
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            module_content = textwrap.dedent('''
                """
                # WORKFLOWS: overview, detailed
                """
                
                # DOCUMENT_WORKFLOW: overview
                def run_overview():
                    pass
                
                # DOCUMENT_WORKFLOW: detailed
                def run_detailed():
                    pass
            ''')
            
            module_file = tmppath / 'entry_module.py'
            module_file.write_text(module_content)
            
            discovery = WorkflowDiscovery(base_path=tmppath)
            result = discovery.discover(['.'])
            
            workflow = list(result.workflows.values())[0]
            assert workflow.entry_points.get('overview') == 'run_overview'
            assert workflow.entry_points.get('detailed') == 'run_detailed'
    
    def test_discover_nonexistent_path(self):
        """Test discovery handles nonexistent paths gracefully."""
        from sphinx_workflow_ext.discovery import WorkflowDiscovery
        
        discovery = WorkflowDiscovery()
        result = discovery.discover(['/nonexistent/path/12345'])
        
        assert len(result.workflows) == 0
        assert len(result.errors) > 0


class TestDiscoverWorkflowsFunction:
    """Test the convenience function."""
    
    def test_discover_workflows_function(self):
        """Test discover_workflows convenience function."""
        from sphinx_workflow_ext.discovery import discover_workflows
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            module_content = '"""\n# WORKFLOWS: test_tier\n"""'
            (tmppath / 'mod.py').write_text(module_content)
            
            result = discover_workflows(['.'], base_path=tmppath)
            
            assert len(result.workflows) == 1


# =============================================================================
# TOC GENERATOR TESTS
# =============================================================================

class TestWorkflowTOCGenerator:
    """Test the WorkflowTOCGenerator class."""
    
    def test_generate_rst_toc_empty(self):
        """Test RST TOC generation with no workflows."""
        from sphinx_workflow_ext.toc_generator import WorkflowTOCGenerator
        from sphinx_workflow_ext.discovery import DiscoveryResult
        
        generator = WorkflowTOCGenerator()
        result = DiscoveryResult()
        
        lines = generator.generate_rst_toc(result)
        assert '*No workflows discovered*' in lines
    
    def test_generate_sidebar_html_empty(self):
        """Test HTML sidebar with no workflows."""
        from sphinx_workflow_ext.toc_generator import WorkflowTOCGenerator
        from sphinx_workflow_ext.discovery import DiscoveryResult
        
        generator = WorkflowTOCGenerator()
        result = DiscoveryResult()
        
        html = generator.generate_sidebar_html(result)
        assert 'workflow-toc-empty' in html
    
    def test_generate_sidebar_html_with_workflows(self):
        """Test HTML sidebar generation with workflows."""
        from sphinx_workflow_ext.toc_generator import WorkflowTOCGenerator
        from sphinx_workflow_ext.discovery import DiscoveredWorkflow, DiscoveryResult
        
        workflow = DiscoveredWorkflow(
            module_path=Path('/pkg/module.py'),
            module_name='module',
            package_name='pkg',
            declared_tiers=['overview', 'detailed'],
        )
        
        result = DiscoveryResult(workflows={'/pkg/module.py': workflow})
        generator = WorkflowTOCGenerator()
        
        html = generator.generate_sidebar_html(result)
        
        assert 'workflow-toc' in html
        assert 'pkg' in html
        assert 'module' in html
    
    def test_get_page_name(self):
        """Test page name generation."""
        from sphinx_workflow_ext.toc_generator import WorkflowTOCGenerator
        from sphinx_workflow_ext.discovery import DiscoveredWorkflow
        
        workflow = DiscoveredWorkflow(
            module_path=Path('/pkg/module.py'),
            module_name='module',
            package_name='pkg',
            declared_tiers=['overview'],
        )
        
        generator = WorkflowTOCGenerator()
        
        # Without tier
        assert generator._get_page_name(workflow) == 'workflows/pkg_module'
        
        # With tier
        assert generator._get_page_name(workflow, 'overview') == 'workflows/pkg_module_overview'


class TestTOCCSSAndJS:
    """Test CSS and JavaScript generation."""
    
    def test_get_toc_css(self):
        """Test CSS generation returns valid CSS."""
        from sphinx_workflow_ext.toc_generator import get_toc_css
        
        css = get_toc_css()
        
        assert '.workflow-toc' in css
        assert '.package-header' in css
        assert '.module-list' in css
    
    def test_get_toc_javascript(self):
        """Test JavaScript generation returns valid JS."""
        from sphinx_workflow_ext.toc_generator import get_toc_javascript
        
        js = get_toc_javascript()
        
        assert 'togglePackage' in js
        assert 'toggleModule' in js
        assert 'DOMContentLoaded' in js


# =============================================================================
# DIRECTIVE TESTS
# =============================================================================

class TestWorkflowIndexDirective:
    """Test the WorkflowIndexDirective class."""
    
    def test_directive_has_correct_options(self):
        """Test directive option_spec is correct."""
        from sphinx_workflow_ext.directives import WorkflowIndexDirective
        
        assert 'search-paths' in WorkflowIndexDirective.option_spec
        assert 'exclude-patterns' in WorkflowIndexDirective.option_spec
        assert 'title' in WorkflowIndexDirective.option_spec
        assert 'group-by-package' in WorkflowIndexDirective.option_spec
        assert 'show-descriptions' in WorkflowIndexDirective.option_spec
        assert 'expand-all' in WorkflowIndexDirective.option_spec
    
    def test_directive_allows_content(self):
        """Test directive accepts content."""
        from sphinx_workflow_ext.directives import WorkflowIndexDirective
        
        assert WorkflowIndexDirective.has_content is True
    
    def test_directive_no_required_arguments(self):
        """Test directive requires no arguments."""
        from sphinx_workflow_ext.directives import WorkflowIndexDirective
        
        assert WorkflowIndexDirective.required_arguments == 0


# =============================================================================
# EXTENSION SETUP TESTS
# =============================================================================

class TestExtensionSetup:
    """Test extension setup function."""
    
    def test_setup_returns_metadata(self):
        """Test setup returns extension metadata."""
        from sphinx_workflow_ext.extension import setup
        
        # Create mock Sphinx app
        app = MagicMock()
        app.config = MagicMock()
        app.config.html_static_path = []
        
        result = setup(app)
        
        assert 'version' in result
        assert 'parallel_read_safe' in result
        assert 'parallel_write_safe' in result
    
    def test_setup_registers_config_values(self):
        """Test setup registers new config values."""
        from sphinx_workflow_ext.extension import setup
        
        app = MagicMock()
        app.config = MagicMock()
        app.config.html_static_path = []
        
        setup(app)
        
        # Check add_config_value was called for new configs
        config_calls = [call[0][0] for call in app.add_config_value.call_args_list]
        
        assert 'workflow_search_paths' in config_calls
        assert 'workflow_exclude_patterns' in config_calls
        assert 'workflow_verbose' in config_calls
    
    def test_setup_registers_workflow_index_directive(self):
        """Test setup registers workflow-index directive."""
        from sphinx_workflow_ext.extension import setup
        
        app = MagicMock()
        app.config = MagicMock()
        app.config.html_static_path = []
        
        setup(app)
        
        # Check add_directive was called with workflow-index
        directive_calls = [call[0][0] for call in app.add_directive.call_args_list]
        
        assert 'workflow-index' in directive_calls


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
