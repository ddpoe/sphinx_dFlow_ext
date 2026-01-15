"""
Pytest configuration for sphinx_workflow_ext tests.
"""

import sys
from pathlib import Path

import pytest


# Add the package to path for imports
@pytest.fixture(scope="session", autouse=True)
def setup_path():
    """Add sphinx_workflow_ext to sys.path."""
    package_dir = Path(__file__).parent.parent / 'sphinx_workflow_ext'
    parent_dir = Path(__file__).parent.parent
    
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    yield


@pytest.fixture
def sample_workflow_module_content():
    """Return sample Python module content with workflow markers."""
    return '''"""
Sample module for testing.

# WORKFLOWS: overview, detailed, full
"""

# DOCUMENT_WORKFLOW: overview, detailed, full
def run_analysis():
    """Entry point for all tiers."""
    # Step 1: Load data
    data = load_data()
    
    # Step 2: Process
    result = process(data)
    
    return result

# WORKFLOW_EXCLUDE: overview
def load_data():
    """Load data (excluded from overview)."""
    # Sub-step 1.1: Read files
    return {}

def process(data):
    """Process data."""
    # Sub-step 2.1: Transform
    return data
'''


@pytest.fixture
def sample_single_tier_content():
    """Return sample module with single-tier workflow."""
    return '''"""
Single tier module.
"""

# DOCUMENT_WORKFLOW: default
def main():
    """Entry point."""
    # Step 1: Initialize
    pass
'''


@pytest.fixture
def temp_workflow_project(tmp_path, sample_workflow_module_content):
    """Create a temporary project structure with workflow modules."""
    # Create package structure
    protocols_dir = tmp_path / 'protocols'
    protocols_dir.mkdir()
    
    modules_dir = tmp_path / 'modules'
    modules_dir.mkdir()
    
    # Create __init__.py files
    (protocols_dir / '__init__.py').write_text('')
    (modules_dir / '__init__.py').write_text('')
    
    # Create workflow modules
    (protocols_dir / 'analysis_protocol.py').write_text(sample_workflow_module_content)
    
    (modules_dir / 'data_loader.py').write_text('''"""
Data loading module.

# WORKFLOWS: pipeline
"""

# DOCUMENT_WORKFLOW: pipeline
def load_pipeline():
    # Step 1: Configure
    pass
''')
    
    # Create test file (should be excluded)
    (protocols_dir / 'test_analysis.py').write_text('''"""
Test file - should be excluded.

# WORKFLOWS: test_tier
"""
''')
    
    return tmp_path
