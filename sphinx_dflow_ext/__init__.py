"""
Sphinx extension for workflow protocol documentation.

This extension automatically extracts and renders workflow protocol documentation
from Python modules and Jupyter notebooks annotated with workflow markers.

Usage in conf.py:
    extensions = ['sphinx_dflow_ext']
    
    # Core configuration
    workflow_config = {
        'show_diagrams': True,
        'default_tier': 'overview',
        'protocol_version': '1.0'
    }
    
    # Auto-discovery configuration
    workflow_search_paths = ['protocols/', 'modules/']
    workflow_exclude_patterns = ['test_*', '_*', '.*']
    workflow_verbose = False

Available Directives:
    .. workflow:: path/to/module.py
       :tier: detailed
    
    .. workflow-notebook:: path/to/notebook.ipynb
    
    .. workflow-index::
       :search-paths: protocols/, modules/
       :title: Workflow Documentation
"""

# Import the Sphinx setup function (CRITICAL - this is what Sphinx looks for!)
from .extension import setup

# Import discovery utilities for external use
from .discovery import (
    WorkflowDiscovery,
    DiscoveredWorkflow,
    DiscoveryResult,
    discover_workflows,
    build_workflow_registry,
)

# Import TOC generator for external use
from .toc_generator import (
    WorkflowTOCGenerator,
    WorkflowIndexBuilder,
    get_toc_css,
    get_toc_javascript,
)

# Import database adapter for external use
from .db_adapter import (
    DatabaseAdapter,
    WorkflowData,
    FunctionData,
    StepData,
    ModuleData,
)

__version__ = '0.3.0'
__all__ = [
    'setup',
    # Discovery (legacy, source-based)
    'WorkflowDiscovery',
    'DiscoveredWorkflow', 
    'DiscoveryResult',
    'discover_workflows',
    'build_workflow_registry',
    # TOC Generation
    'WorkflowTOCGenerator',
    'WorkflowIndexBuilder',
    'get_toc_css',
    'get_toc_javascript',
    # Database Adapter (recommended)
    'DatabaseAdapter',
    'WorkflowData',
    'FunctionData',
    'StepData',
    'ModuleData',
]

