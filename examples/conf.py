# Sphinx configuration for workflow documentation example
# This file demonstrates how to configure Sphinx with the workflow extension

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath('../../..'))

# -- Project information -----------------------------------------------------
project = 'Elastic Net Analysis - Workflow Documentation'
copyright = '2026, Your Lab'
author = 'Your Name'
version = '1.0'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinxcontrib.mermaid',  # For diagrams
    'sphinx_workflow_ext',     # Our workflow extension!
]

# Templates path
templates_path = ['_templates']

# Exclude patterns
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'  # ReadTheDocs theme
html_static_path = ['_static']

# Theme options
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
}

# -- Extension configuration -------------------------------------------------

# Autodoc configuration
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Napoleon (for Google/NumPy docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# Intersphinx (link to other docs)
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
    'sklearn': ('https://scikit-learn.org/stable/', None),
}

# Mermaid configuration
mermaid_version = "10.6.0"
mermaid_init_js = """
mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
    }
});
"""

# -- Workflow Extension Configuration ----------------------------------------

# Auto-discovery configuration (NEW!)
workflow_search_paths = [
    'multi_file_example/',      # Our example with main_pipeline.py
]

workflow_exclude_patterns = [
    'test_*',
    '_*',
    '.*',
    '*_test.py',
    'conftest.py',
]

workflow_verbose = True  # Enable verbose logging for debugging

workflow_config = {
    # Display options
    'show_diagrams': True,              # Generate Mermaid diagrams
    'default_tier': 'overview',         # Default tier for automodule
    'collapse_substeps': True,          # Collapse sub-steps by default
    'show_function_calls': True,        # Show function call hierarchies
    
    # Filtering (optional)
    'exclude_patterns': [
        '*test*',                       # Exclude test modules
        '*_internal*',                  # Exclude internal modules
    ],
    
    # Only process these patterns (optional - leave empty to process all)
    'include_only': None,               # None = process all
    # Example: ['elastic_net_modules.*']  # Only these modules
    
    # Rendering options
    'max_substep_depth': 3,            # Max sub-step nesting level
    'max_output_lines': 100,           # Max lines for notebook outputs
    
    # Metadata
    'protocol_version': '1.0',         # Protocol version
    'author': 'Your Lab',              # Default author
}

# -- Custom CSS/JS -----------------------------------------------------------

def setup(app):
    """Add custom CSS and JS."""
    # Custom CSS for additional styling
    app.add_css_file('custom.css')
