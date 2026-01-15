# Implementation Guide: Adding Sphinx Documentation to Your Project

This guide walks you through implementing Sphinx documentation with the workflow extension for your Elastic Net Analysis project.

## Phase 1: Install Dependencies

**1. Add Sphinx dependencies to your project:**

```bash
# Using Poetry (recommended based on your project)
poetry add --group dev sphinx sphinx-rtd-theme sphinxcontrib-mermaid

# Or with pip
pip install sphinx sphinx-rtd-theme sphinxcontrib-mermaid
```

**2. Install the workflow extension:**

```bash
# Development install (so changes are reflected immediately)
pip install -e ./generate_workflow_docs/sphinx_workflow_ext

# Or add to pyproject.toml
poetry add --editable ./generate_workflow_docs/sphinx_workflow_ext --group dev
```

## Phase 2: Initialize Sphinx Documentation

**1. Create docs directory:**

```bash
# From your project root
mkdir docs
cd docs
```

**2. Run Sphinx quickstart:**

```bash
sphinx-quickstart
```

When prompted:
- Separate source and build directories? **n** (no)
- Project name: **Elastic Net Analysis**
- Author name: **Your Name**
- Project release: **1.0**
- Project language: **en**

This creates:
```
docs/
├── conf.py          # Configuration file
├── index.rst        # Main page
├── Makefile         # Build commands (Linux/Mac)
└── make.bat         # Build commands (Windows)
```

## Phase 3: Configure Sphinx

**Edit `docs/conf.py` - Replace the entire file with:**

```python
import os
import sys
from pathlib import Path

# -- Path setup --------------------------------------------------------------
# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# -- Project information -----------------------------------------------------
project = 'Elastic Net Analysis'
copyright = '2026, Stallaert Lab'
author = 'Dante'
version = '1.0'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',           # Auto-document from docstrings
    'sphinx.ext.napoleon',          # Support NumPy/Google docstrings
    'sphinx.ext.viewcode',          # Add source code links
    'sphinx.ext.intersphinx',       # Link to other docs
    'sphinxcontrib.mermaid',        # Diagrams
    'sphinx_workflow_ext',          # Your workflow extension!
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
}

# -- Autodoc configuration ---------------------------------------------------
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'undoc-members': True,
    'show-inheritance': True,
}

# -- Napoleon configuration --------------------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# -- Intersphinx configuration -----------------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
    'sklearn': ('https://scikit-learn.org/stable/', None),
}

# -- Mermaid configuration ---------------------------------------------------
mermaid_version = "10.6.0"

# -- Workflow Extension configuration ----------------------------------------
workflow_config = {
    # Display options
    'show_diagrams': True,
    'default_tier': 'overview',        # Start with overview tier
    'collapse_substeps': True,
    'show_function_calls': True,
    
    # Filtering
    'exclude_patterns': [
        '*test*',
        '*__pycache__*',
    ],
    
    # Rendering
    'max_substep_depth': 3,
    'max_output_lines': 100,
    
    # Metadata
    'protocol_version': '1.0',
    'author': 'Dante - Stallaert Lab',
}

# -- Custom setup ------------------------------------------------------------
def setup(app):
    """Custom Sphinx setup."""
    # Create _static directory if it doesn't exist
    static_dir = Path(__file__).parent / '_static'
    static_dir.mkdir(exist_ok=True)
```

## Phase 4: Create Documentation Structure

**1. Create `docs/index.rst` (main page):**

```rst
Elastic Net Analysis - Protocol Documentation
==============================================

Welcome to the workflow documentation for the Elastic Net Analysis project.

This documentation automatically extracts workflow protocols from annotated
Python modules and Jupyter notebooks.

.. toctree::
   :maxdepth: 2
   :caption: Documentation:

   modules/index
   protocols/index
   api/index

Quick Navigation
----------------

* :doc:`modules/index` - Module-level workflow documentation
* :doc:`protocols/index` - Complete analysis protocols
* :doc:`api/index` - API reference

Indices
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```

**2. Create `docs/modules/index.rst`:**

```rst
Module Workflows
================

This section documents the workflow protocols in each Python module.

.. toctree::
   :maxdepth: 2

   model_selection
   data_loading
   preprocessing
   feature_engineering
   nested_cv
   validation
   visualization
```

**3. Create `docs/modules/model_selection.rst`:**

```rst
Model Selection Protocol
=========================

This module implements model selection workflows with nested cross-validation.

Workflow Documentation (Auto-extracted)
----------------------------------------

.. automodule:: elastic_net_modules.model_selection
   :members:
   :undoc-members:
   :show-inheritance:

The workflow documentation above is automatically extracted from the module's
workflow markers!

Detailed View
-------------

For a more detailed view of the workflow:

.. workflow:: elastic_net_modules/model_selection.py
   :tier: detailed
   :show-diagram: true

API Reference
-------------

.. autofunction:: elastic_net_modules.model_selection.evaluate_model_performance
.. autofunction:: elastic_net_modules.model_selection.perform_nested_cv
```

**4. Create similar files for other modules:**

```bash
cd docs/modules
# Create these files (templates below)
touch data_loading.rst
touch preprocessing.rst
touch feature_engineering.rst
touch nested_cv.rst
touch validation.rst
touch visualization.rst
```

**Template for each module file:**
```rst
[Module Name]
=============

Brief description of what this module does.

Workflow Documentation
----------------------

.. automodule:: elastic_net_modules.[module_name]
   :members:
   :undoc-members:
   :show-inheritance:
```

## Phase 5: Build and View Documentation

**1. Build the docs:**

```bash
# On Windows
cd docs
make.bat html

# On Linux/Mac
cd docs
make html

# Or directly with sphinx-build
sphinx-build -b html . _build/html
```

**2. View the results:**

```bash
# Open in browser (Windows)
start _build/html/index.html

# Or navigate to: docs/_build/html/index.html
```

## Phase 6: Test with Your Actual Modules

**Check if workflow docs appear:**

1. Open `http://localhost/docs/_build/html/modules/model_selection.html`
2. You should see:
   - Quick Reference table
   - Workflow diagram (if module has multi-tier markers)
   - Detailed step documentation
   - Function signatures

**If workflow docs don't appear:**

1. Check the build output for errors
2. Verify your module has workflow markers:
   ```python
   # WORKFLOW_TIER: overview
   # WORKFLOW_ENTRY_POINT: evaluate_model_performance
   ```
3. Enable debug mode in conf.py:
   ```python
   workflow_config = {
       'debug': True,
       'verbose': True,
   }
   ```

## Phase 7: Automate Documentation Builds

**Add to your `pyproject.toml`:**

```toml
[tool.poetry.scripts]
docs-build = "sphinx_build:main"
docs-serve = "python -m http.server --directory docs/_build/html"

[tool.poe.tasks]
docs = "sphinx-build -b html docs docs/_build/html"
docs-clean = "rm -rf docs/_build"
docs-watch = "sphinx-autobuild docs docs/_build/html"
```

**Install sphinx-autobuild for live reload:**

```bash
poetry add --group dev sphinx-autobuild

# Then run with live reload
sphinx-autobuild docs docs/_build/html
```

This will auto-rebuild docs when you change files!

## Phase 8: Deploy (Optional)

**Option 1: Read the Docs**
1. Push to GitHub
2. Connect at readthedocs.org
3. RTD auto-builds on every commit

**Option 2: GitHub Pages**
```bash
# In docs/_build/html
git init
git add .
git commit -m "Build docs"
git push -f git@github.com:yourusername/yourrepo.git main:gh-pages
```

**Option 3: Local Server**
```bash
cd docs/_build/html
python -m http.server 8000
# Visit http://localhost:8000
```

## Troubleshooting

**Import errors during build:**
```bash
# Make sure your project is importable
cd project_root
python -c "import elastic_net_modules; print('OK')"
```

**Extension not found:**
```bash
# Reinstall extension
pip install -e ./generate_workflow_docs/sphinx_workflow_ext --force-reinstall
```

**No workflow documentation appears:**
- Check module has `# WORKFLOW_TIER:` markers
- Enable debug in conf.py
- Check Sphinx build output for warnings

## Next Steps

1. ✅ Install dependencies
2. ✅ Initialize Sphinx
3. ✅ Configure extension
4. ✅ Create docs structure
5. ✅ Build and test
6. 📝 Document all modules
7. 🎨 Customize theme/styling
8. 🚀 Deploy to Read the Docs

---

**Quick command reference:**

```bash
# Setup
poetry add --group dev sphinx sphinx-rtd-theme sphinxcontrib-mermaid
pip install -e ./generate_workflow_docs/sphinx_workflow_ext

# Initialize
mkdir docs && cd docs
sphinx-quickstart

# Build
make.bat html  # Windows
make html      # Linux/Mac

# View
start _build/html/index.html  # Windows
open _build/html/index.html   # Mac
```
