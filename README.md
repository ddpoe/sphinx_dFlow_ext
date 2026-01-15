# Sphinx Workflow Extension

Sphinx extension for automatic workflow protocol documentation from annotated Python modules and Jupyter notebooks.

## Architecture

This extension works with the `generate_workflow_docs` package:

```
Source Code → generate_workflow_docs (scan) → Database
Database → sphinx_workflow_ext (directives) → RST/HTML
```

**Recommended workflow:**
1. Annotate your code with step markers
2. Run `workflow-steps scan` to populate the database
3. Use `.. workflow-db::` directives in your RST files
4. Build with Sphinx

## Features

- **Database-backed**: Reads from pre-extracted workflow database (recommended)
- **Source-backed**: Direct extraction from source (legacy, still supported)
- **Auto-discovery**: Scan directories to find all workflow modules
- **Multi-tier support**: Generates overview, detailed, and full documentation tiers
- **Interactive UI**: Collapsible sections, step navigation, function call hierarchies
- **Diagram generation**: Automatic Mermaid flowcharts

## Installation

```bash
pip install -e ./sphinx_workflow_ext
```

## Quick Start

**1. Populate the database:**
```bash
cd your_project
workflow-steps scan src/ protocols/
```

**2. Enable in conf.py:**
```python
# docs/conf.py
extensions = [
    'sphinx.ext.autodoc',
    'sphinx_workflow_ext',
]

workflow_config = {
    'show_diagrams': True,
    'default_tier': 'detailed',
}
```

**3. Use database-backed directives in RST:**
```rst
CLI Commands
============

scan
----

.. workflow-db:: src/cli.py:cmd_scan
   :tier: detailed
   :show-diagram: true

This shows the step-by-step workflow for the scan command.
```

**4. Or use the auto-index:**
```rst
All Workflows
=============

.. workflow-index-db::
   :group-by: module
   :show-step-counts: true
```

## Database-Backed Directives (Recommended)

### `.. workflow-db::`
Render workflow from the database. **This is the recommended approach.**

**Target formats:**
- `src/cli.py` - Module path (shows all functions with steps)
- `src.cli:cmd_scan` - Specific function
- `cmd_scan` - Function name (searches all modules)

**Options:**
- `:tier:` - Display tier (overview, detailed, full) - default: detailed
- `:show-diagram:` / `:no-diagram:` - Show Mermaid flowchart - default: true
- `:collapse-substeps:` - Collapse sub-steps by default - default: false
- `:show-source-links:` - Link steps to source code - default: true

**Example:**
```rst
.. workflow-db:: src.cli:cmd_scan
   :tier: detailed
   
.. workflow-db:: elastic_net_modules/model_selection.py
   :tier: overview
   :no-diagram:
```

### `.. workflow-index-db::`
Auto-generated index of all workflows in the database.

**Options:**
- `:group-by:` - How to group (module, package, none) - default: module
- `:show-step-counts:` / `:hide-step-counts:` - Show step counts - default: true

**Example:**
```rst
.. workflow-index-db::
   :group-by: module
```

## Legacy Directives (Source-Based)

These directives extract directly from source files. They still work but
the database-backed approach is recommended for better performance and
integration with the verification system.

### `.. workflow::`
Extract and render workflow from a Python module.

**Options:**
- `:tier:` - Workflow tier (overview, detailed, full)
- `:show-diagram:` - Show Mermaid flowchart (true/false)
- `:collapse-substeps:` - Collapse sub-steps by default (true/false)
- `:show-function-calls:` - Show function call hierarchy (true/false)

**Example:**
```rst
.. workflow:: elastic_net_modules/model_selection.py
   :tier: detailed
   :show-diagram: true
```

### `.. workflow-notebook::`
Extract and render workflow from a Jupyter notebook.

**Options:**
- `:show-outputs:` - Include output artifacts section (true/false)
- `:max-output-lines:` - Limit output display (integer)
- `:show-issues:` - Include common issues section (true/false)

**Example:**
```rst
.. workflow-notebook:: notebooks/nested_cv_analysis.ipynb
   :show-outputs: true
   :max-output-lines: 50
```

### `.. workflow-step::`
Reference a specific workflow step inline.

**Example:**
```rst
The calibration happens in :workflow-step:`model_selection:Step 3.2`.
```

## Configuration Reference

All configuration in `conf.py`:

```python
# Auto-discovery settings (NEW!)
workflow_search_paths = [
    'protocols/',           # Directories to scan for workflow modules
    'elastic_net_modules/',
]

workflow_exclude_patterns = [
    'test_*',              # Exclude test files
    '_*',                  # Exclude private modules
    '.*',                  # Exclude hidden files
    '*_test.py',           # Exclude test modules
    'conftest.py',         # Exclude pytest config
]

workflow_verbose = False   # Enable verbose discovery logging

# Workflow rendering config
workflow_config = {
    # Display options
    'show_diagrams': True,              # Generate Mermaid diagrams
    'default_tier': 'overview',         # Default tier for automodule
    'collapse_substeps': True,          # Collapse sub-steps by default
    'show_function_calls': True,        # Show function call hierarchies
    
    # Filtering
    'exclude_patterns': [],             # Patterns to exclude from processing
    'include_only': None,               # Only process these patterns
    
    # Rendering
    'max_substep_depth': 3,            # Max sub-step nesting level
    'max_output_lines': 100,           # Max lines for notebook outputs
    
    # Metadata
    'protocol_version': '1.0',         # Protocol version
    'author': 'Your Name',             # Default author
}
```

## Workflow Markers Reference

### Module-level (in docstring)
```python
"""
My analysis module.

# WORKFLOWS: overview, detailed, full
"""
```

### Function-level
```python
# DOCUMENT_WORKFLOW: overview, detailed, full
def run_analysis():
    """Entry point for workflow tiers."""
    # Step 1: Load data
    data = load_data()
    
    # Step 2: Process data
    process(data)

# WORKFLOW_EXCLUDE: overview
def load_data():
    """Only in detailed/full tiers."""
    # Sub-step 1.1: Read files
    ...
```

## How It Works

1. **Hook into Sphinx**: Uses `autodoc-process-docstring` to intercept module processing
2. **Auto-discovery**: Scans configured paths for `# WORKFLOWS:` markers
3. **Reuse existing parser**: Leverages your `MultiTierModuleExtractor` 
4. **Convert to RST**: Transforms workflow structure to Sphinx-compatible RST
5. **Inject into docstring**: Replaces module docstring with rich workflow docs
6. **Add interactivity**: Injects JavaScript for collapsible sections and navigation

## Architecture

```
sphinx_workflow_ext/
├── __init__.py           # Package entry point & exports
├── extension.py          # Sphinx setup() and event handlers
├── discovery.py          # Auto-discovery system (NEW!)
├── toc_generator.py      # Sidebar TOC generation (NEW!)
├── rst_generator.py      # Workflow → RST conversion
├── directives.py         # Custom RST directives
├── roles.py              # Custom inline roles
├── static/
│   ├── workflow.css     # Styling for workflow docs
│   └── workflow.js      # Interactive features
└── templates/
    └── workflow.html     # Jinja2 template (optional)
```

## Examples

See `examples/` directory for complete working examples:
- `workflow_index.rst` - Auto-discovery index example
- `simple_module/` - Basic Python module with workflows
- `nested_cv/` - Complex multi-tier protocol
- `notebook_workflow/` - Jupyter notebook example
