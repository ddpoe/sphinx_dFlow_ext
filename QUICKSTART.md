# Quick Start Guide for Sphinx Workflow Extension

This guide will help you get started with the Sphinx workflow extension in just a few minutes.

## Installation

**Option 1: Development Install (Recommended)**
```bash
# From your project root
pip install -e ./generate_workflow_docs/sphinx_workflow_ext
```

**Option 2: Add to pyproject.toml**
```toml
[tool.poetry.dependencies]
sphinx-workflow-ext = {path = "./generate_workflow_docs/sphinx_workflow_ext", develop = true}
sphinx = "^7.0.0"
sphinx-rtd-theme = "^2.0.0"
sphinxcontrib-mermaid = "^0.9.0"
```

Then run:
```bash
poetry install
```

## Set Up Sphinx Documentation

**1. Initialize Sphinx (if not already done):**
```bash
mkdir docs
cd docs
sphinx-quickstart
```

**2. Edit `docs/conf.py`:**
```python
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Add extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinxcontrib.mermaid',
    'sphinx_workflow_ext',  # Add this!
]

# Configure workflow extension
workflow_config = {
    'show_diagrams': True,
    'default_tier': 'overview',
    'collapse_substeps': True,
}

# Use RTD theme (optional but recommended)
html_theme = 'sphinx_rtd_theme'
```

**3. Create a module documentation file `docs/model_selection.rst`:**
```rst
Model Selection Protocol
=========================

.. automodule:: elastic_net_modules.model_selection
   :members:

The workflow documentation will be automatically extracted!
```

**4. Build the documentation:**
```bash
cd docs
make html
```

**5. View the results:**
```bash
# Open docs/_build/html/index.html in your browser
```

## Usage Examples

### Automatic Extraction with automodule

The extension automatically hooks into `automodule` directives:

```rst
.. automodule:: elastic_net_modules.model_selection
   :members:
```

This will:
1. Extract workflow markers from the module
2. Generate a quick reference table
3. Create a Mermaid diagram
4. Document each step with inputs/outputs
5. Show function call hierarchies

### Manual Workflow Directive

For more control, use the `workflow` directive:

```rst
.. workflow:: elastic_net_modules/model_selection.py
   :tier: detailed
   :show-diagram: true
   :collapse-substeps: false
```

### Notebook Workflows

For Jupyter notebooks:

```rst
.. workflow-notebook:: notebooks/nested_cv_analysis.ipynb
   :show-outputs: true
   :max-output-lines: 50
```

### Inline Step References

Reference specific steps in your text:

```rst
The calibration happens in :workflow-step:`model_selection:Step 3.2`.
```

## Customization

### Change Default Tier

In `conf.py`:
```python
workflow_config = {
    'default_tier': 'detailed',  # Use 'detailed' instead of 'overview'
}
```

### Disable Diagrams

```python
workflow_config = {
    'show_diagrams': False,
}
```

### Filter Modules

```python
workflow_config = {
    'include_only': ['elastic_net_modules.*'],  # Only these modules
    'exclude_patterns': ['*test*', '*_internal*'],  # Exclude these
}
```

## Project Structure

Recommended structure for docs:

```
your_project/
├── elastic_net_modules/
│   ├── model_selection.py  # Has workflow markers
│   └── ...
├── notebooks/
│   └── analysis.ipynb
├── docs/
│   ├── conf.py
│   ├── index.rst
│   ├── modules/
│   │   ├── index.rst
│   │   └── model_selection.rst
│   └── notebooks/
│       └── analysis.rst
└── generate_workflow_docs/
    └── sphinx_workflow_ext/
```

## Troubleshooting

**Problem: Extension not found**
```
Extension error: Could not import extension sphinx_workflow_ext
```

**Solution:**
```bash
# Make sure it's installed
pip install -e ./generate_workflow_docs/sphinx_workflow_ext

# Or with Poetry
poetry install
```

**Problem: No workflow documentation appears**
```
Module documentation appears but no workflow sections
```

**Solution:**
- Check that your module has `# WORKFLOW_TIER:` markers
- Enable debug logging in conf.py:
  ```python
  workflow_config = {'debug': True}
  ```
- Check Sphinx build output for errors

**Problem: Diagrams don't render**
```
Mermaid diagrams show as code blocks
```

**Solution:**
```bash
pip install sphinxcontrib-mermaid
```

Add to conf.py:
```python
extensions = [
    'sphinxcontrib.mermaid',  # Add this before sphinx_workflow_ext
    'sphinx_workflow_ext',
]
```

## Next Steps

1. **Explore the examples**: Check `generate_workflow_docs/sphinx_workflow_ext/examples/`
2. **Customize styling**: Edit `static/workflow.css` to match your brand
3. **Add more modules**: Document all your workflow modules
4. **Deploy docs**: Use Read the Docs, GitHub Pages, or your hosting

## Complete Example

See a complete working example in:
```
generate_workflow_docs/sphinx_workflow_ext/examples/
```

Build it with:
```bash
cd generate_workflow_docs/sphinx_workflow_ext/examples
sphinx-build -b html . _build
```
