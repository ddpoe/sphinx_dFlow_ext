"""
Main Sphinx extension entry point.

This module registers all event handlers, directives, and configuration
for the workflow documentation extension.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import inspect

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.util import logging as sphinx_logging

from .rst_generator import WorkflowRSTGenerator
from .directives import WorkflowDirective, WorkflowNotebookDirective, WorkflowIndexDirective
from .directives_db import WorkflowDBDirective, WorkflowIndexDBDirective
from .roles import workflow_step_role
from .source_link_role import source_link_role, source_line_role, step_source_role
from .source_generator import generate_all_source_pages

logger = sphinx_logging.getLogger(__name__)


def _build_step_line_map(steps: List[Any]) -> Dict[str, int]:
    """
    Build mapping of step IDs to line numbers for source linking.
    
    Args:
        steps: List of StepInfo objects
    
    Returns:
        Dictionary mapping step IDs (e.g., 'step-1', 'step-1-1') to line numbers
    """
    step_line_map = {}
    
    for step in steps:
        # Get step number (could be int or string)
        step_num = getattr(step, 'hierarchical_number', getattr(step, 'number', ''))
        
        # Get line number from various possible attributes
        line_num = getattr(step, 'source_line', None) or getattr(step, 'cell_number', None)
        
        if step_num and line_num:
            # Convert step number to anchor format: 1.1 -> step-1-1
            step_id = f"step-{str(step_num).replace('.', '-')}"
            step_line_map[step_id] = line_num
        
        # Process sub-steps recursively
        sub_steps = getattr(step, 'sub_steps', [])
        if sub_steps:
            sub_map = _build_step_line_map(sub_steps)
            step_line_map.update(sub_map)
    
    return step_line_map


def get_workflow_config(app: Sphinx) -> Dict[str, Any]:
    """
    Get workflow configuration from Sphinx config.
    
    Args:
        app: Sphinx application
    
    Returns:
        Configuration dictionary with defaults
    """
    default_config = {
        'show_diagrams': True,
        'default_tier': 'overview',
        'collapse_substeps': True,
        'show_function_calls': True,
        'exclude_patterns': [],
        'include_only': None,
        'max_substep_depth': 3,
        'max_output_lines': 100,
        'protocol_version': '1.0',
        'author': None,
    }
    
    # Merge with user config
    user_config = getattr(app.config, 'workflow_config', {})
    return {**default_config, **user_config}


def should_process_module(module_name: str, config: Dict[str, Any]) -> bool:
    """
    Check if module should be processed based on include/exclude patterns.
    
    Args:
        module_name: Fully qualified module name
        config: Workflow configuration
    
    Returns:
        True if module should be processed
    """
    import fnmatch
    
    # Check exclude patterns
    for pattern in config['exclude_patterns']:
        if fnmatch.fnmatch(module_name, pattern):
            return False
    
    # Check include patterns (if specified)
    if config['include_only']:
        for pattern in config['include_only']:
            if fnmatch.fnmatch(module_name, pattern):
                return True
        return False
    
    return True


def process_workflow_docstring(
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    options: Dict,
    lines: List[str]
) -> None:
    """
    Process docstrings to inject workflow documentation.
    
    This is the main hook that Sphinx calls for every docstring it encounters.
    We intercept module docstrings and inject workflow documentation.
    
    Args:
        app: Sphinx application object
        what: Type of object ('module', 'class', 'function', etc.)
        name: Fully qualified name (e.g., 'elastic_net_modules.model_selection')
        obj: The actual Python object
        options: Autodoc options
        lines: Docstring lines (list we can modify in-place!)
    """
    # Only process modules
    if what != 'module':
        return
    
    # Get configuration
    config = get_workflow_config(app)
    
    # Check if we should process this module
    if not should_process_module(name, config):
        logger.debug(f"Skipping module {name} (excluded by config)")
        return
    
    # Try to get source code
    try:
        source = inspect.getsource(obj)
    except (TypeError, OSError):
        logger.debug(f"Could not get source for {name}")
        return
    
    # Check if module has workflow markers
    if '# WORKFLOW_TIER:' not in source and '# Step ' not in source:
        logger.debug(f"No workflow markers found in {name}")
        return
    
    logger.info(f"Extracting workflow documentation from {name}")
    
    # Get module file path (for multi-tier extraction)
    try:
        module_file = Path(inspect.getfile(obj))
    except (TypeError, OSError):
        logger.warning(f"Could not determine file path for {name}")
        return
    
    # Import extractor (from local package copy)
    try:
        # Extractors are now bundled inside sphinx_workflow_ext package
        from .extractors.multi_tier_module_extractor import MultiTierModuleExtractor
        from .core import ExtractorConfig
        
    except ImportError as e:
        logger.error(f"Failed to import workflow extractor: {e}")
        logger.error("Make sure generate_workflow_docs is installed")
        return
    
    # Create extractor
    extractor_config = ExtractorConfig(
        verbose=config.get('verbose', False),
        debug=config.get('debug', False),
    )
    
    # Use a simple logger for the extractor
    extractor_logger = logging.getLogger('workflow_extractor')
    extractor_logger.setLevel(logging.WARNING)  # Quiet during Sphinx build
    
    try:
        extractor = MultiTierModuleExtractor(
            module_file,
            extractor_config,
            extractor_logger
        )
        
        # Load module
        load_result = extractor.load()
        if not load_result.success:
            logger.warning(f"Failed to load workflow from {name}")
            return
        
        # Determine which tier to use
        tier = config['default_tier']
        
        # Extract workflow for this tier
        workflow_doc = extractor.extract_workflow_for_tier(tier)
        
        # Extract all functions for hierarchical documentation
        all_functions = extractor.extract_all_function_steps(tier)
        
        # Build step-to-line mapping for source generation
        step_line_map = _build_step_line_map(workflow_doc['steps'])
        
        # Convert to new format with full step data
        step_data = {
            f"step-{str(sid).replace('.', '-')}": {
                'line': line,
                'name': '',
                'number': sid,
                'module': name
            }
            for sid, line in step_line_map.items()
        }
        
        # Store source mapping in environment for later source generation
        env = app.env
        if not hasattr(env, 'workflow_source_mappings'):
            env.workflow_source_mappings = {}
        
        env.workflow_source_mappings[name] = {
            'source_path': str(module_file),
            'steps': step_data
        }
        
        # Generate RST documentation
        generator = WorkflowRSTGenerator(config)
        rst_lines = generator.generate_module_rst(
            module_name=name,
            metadata=workflow_doc['metadata'],
            steps=workflow_doc['steps'],
            all_functions=all_functions
        )
        
        # Replace docstring lines with generated RST
        lines[:] = rst_lines
        
        logger.info(f"Injected workflow documentation for {name} ({len(rst_lines)} lines)")
        
    except Exception as e:
        logger.error(f"Error extracting workflow from {name}: {e}")
        if config.get('debug'):
            import traceback
            logger.debug(traceback.format_exc())


def add_static_files(app: Sphinx, config: Any) -> None:
    """
    Add custom CSS and JavaScript files.
    
    Args:
        app: Sphinx application
        config: Sphinx config object
    """
    # Add CSS file
    app.add_css_file('workflow.css')
    
    # Add JavaScript file
    app.add_js_file('workflow.js')


def copy_static_files(app: Sphinx, exception: Optional[Exception]) -> None:
    """
    Copy static files to build directory.
    
    Args:
        app: Sphinx application
        exception: Exception if build failed
    """
    if exception:
        return
    
    import shutil
    
    # Get static directory
    static_dir = Path(__file__).parent / 'static'
    if not static_dir.exists():
        return
    
    # Get build static directory
    build_static = Path(app.outdir) / '_static'
    build_static.mkdir(parents=True, exist_ok=True)
    
    # Copy CSS
    css_source = static_dir / 'workflow.css'
    if css_source.exists():
        shutil.copy(css_source, build_static / 'workflow.css')
    
    # Copy JS
    js_source = static_dir / 'workflow.js'
    if js_source.exists():
        shutil.copy(js_source, build_static / 'workflow.js')


def setup(app: Sphinx) -> Dict[str, Any]:
    """
    Sphinx extension setup function.
    
    This is the entry point that Sphinx calls when loading the extension.
    Here we register all event handlers, directives, and configuration.
    
    Args:
        app: Sphinx application object
    
    Returns:
        Extension metadata
    """
    # Add configuration values
    app.add_config_value('workflow_config', {}, 'html')
    app.add_config_value('workflow_db_path', None, 'html')  # Path to workflow database
    
    # Auto-discovery configuration
    app.add_config_value('workflow_search_paths', [], 'html')
    app.add_config_value('workflow_exclude_patterns', ['test_*', '_*', '.*', '*_test.py'], 'html')
    app.add_config_value('workflow_verbose', False, 'html')
    
    # Register event handlers
    app.connect('autodoc-process-docstring', process_workflow_docstring)
    app.connect('config-inited', add_static_files)
    app.connect('build-finished', copy_static_files)
    app.connect('build-finished', generate_all_source_pages)
    
    # Register custom directives (source-based, legacy)
    app.add_directive('workflow', WorkflowDirective)
    app.add_directive('workflow-notebook', WorkflowNotebookDirective)
    app.add_directive('workflow-index', WorkflowIndexDirective)
    
    # Register database-backed directives (recommended)
    app.add_directive('workflow-db', WorkflowDBDirective)
    app.add_directive('workflow-index-db', WorkflowIndexDBDirective)
    
    # Register custom roles
    app.add_role('workflow-step', workflow_step_role)
    app.add_role('source-link', source_link_role)
    app.add_role('source-line', source_line_role)
    app.add_role('step-source', step_source_role)
    
    # Add static path
    static_path = Path(__file__).parent / 'static'
    if static_path.exists():
        app.config.html_static_path.append(str(static_path))
    
    return {
        'version': '0.2.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
