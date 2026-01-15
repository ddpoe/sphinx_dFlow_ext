Auto-Discovery Workflow Index
=============================

This example demonstrates the ``.. workflow-index::`` directive, which 
automatically scans directories for Python modules with workflow markers
and generates a navigable documentation index.

Basic Usage
-----------

Add the following to your RST file:

.. code-block:: rst

    .. workflow-index::
       :search-paths: protocols/, elastic_net_modules/
       :title: All Project Workflows

With Custom Options
-------------------

.. code-block:: rst

    .. workflow-index::
       :search-paths: protocols/, modules/
       :exclude-patterns: test_*, _*, deprecated_*
       :title: API Workflow Documentation
       :group-by-package:
       :show-descriptions:
       :expand-all:
       
       This documentation is auto-generated from workflow markers 
       in the source code. Each module's tiers are extracted and
       rendered with full step hierarchies.

Configuration in conf.py
------------------------

You can also set defaults in your Sphinx ``conf.py``:

.. code-block:: python

    # conf.py
    
    extensions = ['sphinx_workflow_ext']
    
    # Auto-discovery paths (relative to project root)
    workflow_search_paths = [
        'protocols/',
        'elastic_net_modules/',
        'notebooks/',
    ]
    
    # Files to exclude from discovery
    workflow_exclude_patterns = [
        'test_*',      # Test files
        '_*',          # Private modules
        '.*',          # Hidden files
        '*_test.py',   # Test modules
        'conftest.py', # Pytest config
    ]
    
    # Enable verbose logging during discovery
    workflow_verbose = False
    
    # Core workflow config
    workflow_config = {
        'show_diagrams': True,
        'default_tier': 'overview',
        'collapse_substeps': True,
    }

Then in your RST, you can use the directive without specifying paths:

.. code-block:: rst

    .. workflow-index::
       :title: Project Workflows

Live Example
------------

The following uses the ``workflow_search_paths`` from conf.py automatically:

.. workflow-index::
   :title: All Discovered Workflows
   :show-descriptions:

Discovered Workflow Markers
---------------------------

The discovery system looks for these markers in Python files:

**Module-level (in docstring):**

.. code-block:: python

    """
    My analysis module.
    
    # WORKFLOWS: overview, detailed, full
    """

**Function-level:**

.. code-block:: python

    # DOCUMENT_WORKFLOW: overview, detailed, full
    def run_analysis():
        """Entry point for all workflow tiers."""
        # Step 1: Load data
        data = load_data()
        
        # Step 2: Process
        process(data)
    
    # WORKFLOW_EXCLUDE: overview
    def load_data():
        """Only appears in detailed and full tiers."""
        # Sub-step 1.1: Read files
        ...

See Also
--------

- :doc:`index` - Using the ``.. workflow::`` directive
- :doc:`notebooks` - Using the ``.. workflow-notebook::`` directive
